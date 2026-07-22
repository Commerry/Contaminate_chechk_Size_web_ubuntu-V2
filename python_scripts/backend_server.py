# -*- coding: utf-8 -*-
"""
Flask Backend API for OAK Camera Object Measurement System
This file provides REST API endpoints for the Vue.js frontend
"""

import os
import signal
import sys

# A PoE camera closes the XLink connection when the host stops servicing it for
# longer than the device watchdog (4s by default). Any hiccup on the host side -
# a slow Socket.IO client, a long detection pass - was enough to make the camera
# "drop" while still answering ping. Give the link more headroom.
os.environ.setdefault('DEPTHAI_WATCHDOG', '10000')

# Set UTF-8 encoding for Windows console BEFORE any print statements
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Detect if running as PyInstaller bundle or Electron bundled Python
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Running as PyInstaller executable
    BASE_PATH = sys._MEIPASS
    IS_PYINSTALLER = True
    IS_ELECTRON_BUNDLED = False
else:
    # Running as normal Python script or Electron bundled Python
    BASE_PATH = os.path.abspath(os.path.dirname(__file__))
    IS_PYINSTALLER = False
    # Check if running in Electron bundled environment
    # (python_scripts is inside resources folder)
    IS_ELECTRON_BUNDLED = 'resources' in BASE_PATH.replace('\\', '/') and 'python_scripts' in BASE_PATH

# Add parent directory to path for imports
if not IS_PYINSTALLER:
    sys.path.insert(0, os.path.join(BASE_PATH, '..'))

print(f"[Startup] BASE_PATH: {BASE_PATH}")
print(f"[Startup] IS_PYINSTALLER: {IS_PYINSTALLER}")
print(f"[Startup] IS_ELECTRON_BUNDLED: {IS_ELECTRON_BUNDLED}")

from flask import Flask, jsonify, request, send_file, send_from_directory, render_template
from flask_cors import CORS
from flask_socketio import SocketIO
import cv2
import numpy as np
import base64
import json
from datetime import datetime
import io
from pathlib import Path
from python_scripts.system_config import system_config  # Import config manager
from python_scripts.oak_ip_config import ensure_oak_poe_static_ip

# Database imports
from python_scripts.database import DatabaseConfig, DatabaseService, MeasurementSession

# Determine frontend path (for serving static files)
# Development: ../frontend/dist (relative to python_scripts/)
# Electron bundled: ../frontend/ (resources/frontend/)
# PyInstaller: _internal/frontend/ (bundled in executable)
if IS_PYINSTALLER:
    FRONTEND_DIST_DEV = os.path.join(BASE_PATH, 'frontend')
    FRONTEND_DIST_PROD = os.path.join(BASE_PATH, 'frontend')
elif IS_ELECTRON_BUNDLED:
    # In Electron bundled, BASE_PATH = resources/python_scripts
    # Frontend is at resources/frontend
    FRONTEND_DIST_DEV = os.path.join(BASE_PATH, '..', 'frontend')
    FRONTEND_DIST_PROD = os.path.join(BASE_PATH, '..', 'frontend')
else:
    # Development mode
    FRONTEND_DIST_DEV = os.path.join(BASE_PATH, '..', 'frontend', 'dist')
    FRONTEND_DIST_PROD = os.path.join(BASE_PATH, '..', 'frontend')

# Check which path exists
if os.path.exists(FRONTEND_DIST_DEV) and os.path.exists(os.path.join(FRONTEND_DIST_DEV, 'index.html')):
    FRONTEND_DIST = FRONTEND_DIST_DEV
    print(f"📁 [Frontend] Using DEV path: {FRONTEND_DIST}")
elif os.path.exists(FRONTEND_DIST_PROD) and os.path.exists(os.path.join(FRONTEND_DIST_PROD, 'index.html')):
    FRONTEND_DIST = FRONTEND_DIST_PROD
    print(f"📁 [Frontend] Using PROD path: {FRONTEND_DIST}")
else:
    # Fallback to dev path
    FRONTEND_DIST = FRONTEND_DIST_DEV
    print(f"⚠️  [Frontend] Path not found, using fallback: {FRONTEND_DIST}")
    print(f"    Checked paths:")
    print(f"      - {FRONTEND_DIST_DEV} (exists: {os.path.exists(FRONTEND_DIST_DEV)})")
    print(f"      - {FRONTEND_DIST_PROD} (exists: {os.path.exists(FRONTEND_DIST_PROD)})")

# Determine desktop app path
if IS_PYINSTALLER:
    DESKTOP_DIST = os.path.join(BASE_PATH, 'user_display', 'dist')
else:
    DESKTOP_DIST = os.path.join(BASE_PATH, '..', 'user_display', 'dist')
    if not os.path.exists(DESKTOP_DIST):
        # In packaged app, check resources
        DESKTOP_DIST = os.path.join(BASE_PATH, '..', 'user_display', 'dist')

desktop_index_exists = os.path.exists(os.path.join(DESKTOP_DIST, 'index.html'))
print(f"📱 [Desktop] Path: {DESKTOP_DIST}")
print(f"   index.html exists: {desktop_index_exists}")

app = Flask(__name__, static_folder=FRONTEND_DIST, static_url_path='')
CORS(app)  # Enable CORS for all routes

# Initialize SocketIO for real-time communication
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Import backend extension for area-based measurement
from python_scripts import backend_extension

# Initialize extension
backend_extension.register_routes(app, socketio)

# โหลด configurations จากไฟล์
backend_extension.load_configurations()
print(f"[Backend] Loaded {len(backend_extension.configurations)} configurations")

# โหลด machines จากไฟล์
backend_extension.load_machines()
print(f"[Backend] Loaded {len(backend_extension.machines)} machines")

# Global state - will be restored from config
camera_active = False
contour_detection_active = False  # Track if contour detection is active
multi_object_detection_active = False  # Track if multi-object detection is active
three_zone_detection_active = False  # Track if 3-zone detection is active
current_zoom = 1.0  # Current zoom level
rubber_type = "black"  # ✅ Rubber type: "black" (dark on white) or "white" (white on dark)

# Database instances
db_config = DatabaseConfig('database/db_config.json')
db_service = None  # Will be initialized when database is enabled
measurement_session = None  # Active measurement session
current_settings = {
    'resolution': '1080p',
    'fpsLimit': 30,
    'showDepthMap': False,
    'measurementUnit': 'mm',
    'minDepth': 300,
    'maxDepth': 3000,
    'autoCapture': True,
    'confidenceThreshold': 0.5,
    'minObjectSize': 50,
    'showBoundingBoxes': True,
    'referenceSize': 100,
    'calibrationFactor': 1.0,  # Default calibration factor (no scaling)
    # ✅ Calibration factors - อัพเดตตามขนาดจริง: W=78mm, H=165mm
    # ✅ Measured (detected): W=218px H=416px → Actual: W=78mm H=165mm
    'calibration_width': 0.6494,   # 78mm / 218 = 0.358 (actual/measured)
    'calibration_height': 0.7154,  # 165mm / 416 = 0.396 (actual/measured)
    'calibration_depth': 0.708,   # 25mm / 141.1mm = 0.177
    'calibration_enabled': True,  # เปิด/ปิด calibration
    'reference_object': {         # ข้อมูลวัตถุอ้างอิง
        'width_mm': 78,
        'height_mm': 165,
        'depth_mm': 55
    },
    # ✅ Calibration settings
    'calibration_width': 0.6494,  # Calibration factor (218px → 78mm)
    'calibration_height': 0.7154, # Calibration factor (416px → 165mm)
    'max_objects': 30             # Maximum objects to detect (default 30)
}

# ⭐ UPDATED CALIBRATION (2026-01-27): Iteration 4 - CORRECTED FORMULA
# Measured (detected): W=218px H=416px → Actual: W=78mm H=165mm
# Formula: calibration_factor = actual_mm / detected_pixel
# Width factor: 78 / 218 = 0.358
# Height factor: 165 / 416 = 0.396
current_settings['calibration_width'] = 0.6494   # Apply immediately
current_settings['calibration_height'] = 0.7154  # Apply immediately

measurement_history = []
calibration_capture = None  # Store calibration capture for verification

# ✅ Active measurement session
active_measurement_config = None  # เก็บ configuration ที่กำลังใช้วัด
active_machine_id = None   # เก็บ machine_id ที่กำลังใช้วัด
active_machine_name = None  # เก็บชื่อเครื่องจักร
active_lot_id = None       # เก็บ lot_id ที่เลือก
active_lot_name = None     # เก็บชื่อ LOT

# � Fallback config (ใช้เมื่อ active_measurement_config เป็น None - โหลดจากไฟล์)
fallback_measurement_config = None  # โหลดจาก configurations.json อัตโนมัติ

# 📊 Global statistics tracking
measurement_statistics = {
    'total': 0,
    'pass': 0,
    'fail': 0,
    'near_pass': 0  # ใกล้เคียงผ่าน (สีเหลือง)
}

# 🔄 Track previous frame detection state for per-event counting
was_detecting = False  # True = objects were detected in previous frame

# 📦 Latest measurements with status (สำหรับใช้ใน capture)
latest_all_measurements = []  # เก็บ measurements ล่าสุดพร้อม status สำหรับ capture

# OAK Camera instance
# depthai is optional: on a desktop without an OAK camera the backend still
# boots so the UI and non-camera APIs work. Camera features guard on HAS_DEPTHAI.
try:
    import depthai as dai
    HAS_DEPTHAI = True
except Exception as _depthai_err:
    dai = None
    HAS_DEPTHAI = False
    print(f"[Startup] ⚠️ depthai not available ({_depthai_err}); running without OAK camera support")
from python_scripts.camera_lock import acquire_lock, release_lock
import threading
import time

oak_pipeline = None
oak_device = None
latest_frame = None
latest_depth = None
latest_annotated_frame = None  # ✅ เก็บภาพที่วาดกรอบแล้ว
latest_contour_mask = None  # เพื่อแสดง contour visualization
tracked_objects = {}  # ✅ เก็บ tracked objects กับ ID {id: {bbox, info}}
track_id_counter = 0  # ✅ counter สำหรับ object ID
frame_lock = threading.Lock()
camera_thread = None
running = False

# ♻️ Camera auto-reconnect coordination
# `camera_should_run` is the persistent INTENT (user pressed Start). The
# watchdog and the status endpoint use it to decide whether to self-heal.
# `recovery_lock` guarantees only one (re)initialization runs at a time, so the
# watchdog, the status endpoint and the camera loop can never double-open the
# device. `recovery_in_progress` lets callers skip instead of blocking.
camera_should_run = False
recovery_lock = threading.Lock()
recovery_in_progress = False
watchdog_thread = None

# 📡 Frame publishing is handed to a dedicated thread. socketio.emit() blocks
# until the payload is queued for every client, which on long-polling clients
# can take seconds - and while the camera thread waits, it is not reading the
# XLink queues, so the device watchdog kills the link. The camera thread now
# only drops the newest payload here (latest-frame-wins) and moves on.
emit_lock = threading.Lock()
pending_frame_payload = None
frame_emit_event = threading.Event()
emitter_thread = None

# How long frames may be missing before the camera counts as broken. As long as
# frames keep arriving the camera is by definition working, so nothing may
# reopen it - a second open of a live device fails with X_LINK and kills the
# stream that was still fine.
CAMERA_FRAME_GRACE = 12.0

# Every camera loop carries the generation it was started with. Re-initializing
# bumps the counter, so an older loop that is no longer tracked by
# `camera_thread` retires itself instead of draining the same queues in
# parallel - duplicate loops are what left a stale thread handle behind and
# made the watchdog reconnect a perfectly healthy camera.
camera_loop_generation = 0

# ✅ Request throttling - ป้องกัน request ซ้ำเร็วเกินไป
last_measurement_request_time = 0
measurement_request_cooldown = 0.5  # ต้องห่างกัน 0.5 วินาที (2 FPS max)

# LAN Camera connection parameters
last_frame_time = time.time()
connection_stable = True
stability_check_interval = 5.0  # ตรวจสอบทุก 5 วินาที
frame_timeout = 30.0  # ถ้าไม่มี frame มา 30 วินาที ถึงจะ recovery

# Object Tracking
tracked_objects = {}  # {id: {'bbox': [x,y,w,h], 'depth': float, 'age': int, 'missed': int}}
next_object_id = 1
max_missing_frames = 30  # เพิ่มเป็น 30 เฟรม (1 วินาที) - ล็อคแน่นมาก!

# Unique colors for each object (HSV-based for better distinction)
def get_object_color(object_index):
    """Generate unique color for each object using HSV color space"""
    colors = [
        (0, 255, 0),      # Green
        (255, 0, 0),      # Blue
        (0, 0, 255),      # Red
        (255, 255, 0),    # Cyan
        (255, 0, 255),    # Magenta
        (0, 255, 255),    # Yellow
        (128, 0, 255),    # Purple
        (255, 128, 0),    # Orange
        (0, 128, 255),    # Sky Blue
        (255, 0, 128),    # Pink
    ]
    return colors[object_index % len(colors)]

def camera_loop(generation=0):
    """Background thread for camera processing (supports LAN/PoE cameras) - runs continuously"""
    global latest_frame, latest_depth, running, oak_device, oak_pipeline, camera_active, last_frame_time
    
    consecutive_errors = 0
    max_consecutive_errors = 100  # ลดลงเพื่อ detect ปัญหาเร็วขึ้น
    max_time_without_frame = 60  # 60 วินาที (ลดจาก 90)
    max_recovery_attempts = 5  # เพิ่มเป็น 5 attempts
    grace_period = 10.0  # ลดลงเป็น 10 วินาที
    recovery_attempts = 0
    total_errors = 0
    frame_count = 0
    last_success_time = time.time()
    last_recovery_time = 0  # เพิ่มเพื่อติดตามเวลา recovery ครั้งสุดท้าย
    last_health_check = time.time()
    health_check_interval = 30  # ตรวจสุขภาพทุก 30 วินาที (ลดการรบกวน LAN)
    lan_keepalive_interval = 10  # เพิ่มเป็น 10 วินาที (ลดความถี่)
    last_keepalive = time.time()
    
    # ⚡ Frame skipping - สมดุลระหว่าง smoothness และ bandwidth
    frame_skip_counter = 0
    frame_skip_rate = 2  # ⚡ ส่งทุก 3 เฟรม (15fps → 5fps effective) = Smooth + Efficient!
    
    # ✅ Cache output queues to avoid recreating them every frame
    cached_device_for_queues = None
    queue_rgb = None
    queue_depth = None

    print("[CAMERA LOOP] ⚡ Starting camera loop thread (BALANCED mode: Smooth + Efficient)...")
    print(f"[CAMERA LOOP] Frame skip rate: {frame_skip_rate} (sending every {frame_skip_rate + 1} frames = ~5 FPS for smooth experience)")
    print(f"[CAMERA LOOP] Recovery settings: max_errors={max_consecutive_errors}, timeout={max_time_without_frame}s, grace={grace_period}s")
    
    while running and generation == camera_loop_generation:
        try:
            # === HEALTH CHECK (ลดความถี่เพื่อไม่รบกวนกล้อง) ===
            current_time = time.time()
            
            # LAN Camera Keepalive - ส่ง control message ทุก 10 วินาที
            if current_time - last_keepalive > lan_keepalive_interval:
                try:
                    if oak_device and not oak_device.isClosed():
                        # Soft keepalive - ใช้ getQueueEvents แทนการส่ง control message
                        # วิธีนี้เบากว่าและไม่รบกวนกล้อง
                        try:
                            oak_device.getQueueEvents()
                        except:
                            pass
                    last_keepalive = current_time
                except Exception as e:
                    if consecutive_errors <= 3:  # Log เฉพาะครั้งแรกๆ
                        print(f"[CAMERA] ⚠️ LAN Keepalive error (harmless): {e}")
            
            if current_time - last_health_check > health_check_interval:
                last_health_check = current_time
                
                # ตรวจสอบ device แบบ soft (ไม่รบกวน LAN camera)
                if oak_device is None:
                    print("[HEALTH] ⚠️ Device is None - waiting for LAN camera...")
                    time.sleep(5)
                    continue
                
                # ไม่ตรวจสอบ isClosed() บ่อยๆ เพราะอาจรบกวน LAN connection
                # ให้ยึดตาม frame acquisition แทน
            
            # === FRAME ACQUISITION ===
            if oak_device and not oak_device.isClosed():
                # ✅ Refresh output queues only when device changes (cache to avoid per-frame overhead)
                if oak_device != cached_device_for_queues:
                    try:
                        queue_rgb = oak_device.getOutputQueue(name="rgb", maxSize=1, blocking=False)
                        queue_depth = oak_device.getOutputQueue(name="depth", maxSize=1, blocking=False)
                        cached_device_for_queues = oak_device
                        print("[CAMERA] ✅ Output queues initialized/refreshed")
                    except Exception as qe:
                        print(f"[CAMERA] ⚠️ Failed to init queues: {qe}")
                        queue_rgb = None
                        queue_depth = None
                
                if queue_rgb is None or queue_depth is None:
                    time.sleep(0.5)
                    continue
                
                # Get RGB frame with maxSize=1 to prevent buffer buildup
                in_rgb = queue_rgb.tryGet()
                
                # Get depth frame with maxSize=1
                in_depth = queue_depth.tryGet()
                
                # ✅ Clear old frames from queue to prevent lag
                # ล้าง queue เพื่อไม่ให้ frame เก่าสะสม
                try:
                    while queue_rgb.has():
                        queue_rgb.tryGet()  # ดึงและทิ้ง
                    while queue_depth.has():
                        queue_depth.tryGet()  # ดึงและทิ้ง
                except:
                    pass
                
                got_frame = False
                
                # ✅ Frame Skipping - ลด network load
                frame_skip_counter += 1
                should_process = (frame_skip_counter % (frame_skip_rate + 1) == 0)
                
                if in_rgb is not None:
                    try:
                        frame = in_rgb.getCvFrame()
                        # อัพเดท frame เฉพาะเมื่อควร process
                        if should_process:
                            # ✅ ลดความละเอียดลง 60% ก่อนเก็บเพื่อลด memory และ bandwidth
                            h, w = frame.shape[:2]
                            frame_resized = cv2.resize(frame, (int(w * 0.6), int(h * 0.6)), interpolation=cv2.INTER_AREA)
                            with frame_lock:
                                # ✅ ลบ frame เก่าก่อนเก็บ frame ใหม่เพื่อ free memory
                                if latest_frame is not None:
                                    del latest_frame
                                latest_frame = frame_resized.copy()
                        # ✅ ลบ frame ชั่วคราวเพื่อ free memory
                        del frame
                        got_frame = True
                    except Exception as e:
                        print(f" Failed to get RGB frame: {e}")
                
                if in_depth is not None:
                    try:
                        depth = in_depth.getFrame()
                        # อัพเดท depth เฉพาะเมื่อควร process
                        if should_process:
                            with frame_lock:
                                # ✅ ลบ depth เก่าก่อนเก็บ depth ใหม่เพื่อ free memory
                                if latest_depth is not None:
                                    del latest_depth
                                latest_depth = depth.copy()
                        # ✅ ลบ depth ชั่วคราวเพื่อ free memory
                        del depth
                        got_frame = True
                    except Exception as e:
                        print(f" Failed to get depth frame: {e}")
                
                if got_frame:
                    consecutive_errors = 0  # Reset on success
                    recovery_attempts = 0  # Reset recovery counter
                    # A frame is proof the camera works. A failed reconnect
                    # attempt may have cleared the flag while this loop kept
                    # streaming; don't leave the API rejecting requests for a
                    # camera that is plainly running.
                    if not camera_active and camera_should_run:
                        camera_active = True
                    if should_process:  # นับเฉพาะเฟรมที่ส่งจริง
                        frame_count += 1
                        
                        # ✅ ตรวจจับวัตถุและส่ง frame พร้อมกรอบ ROI ไปยัง Desktop App
                        try:
                            # เรียก detect_objects() เพื่อตรวจจับและวาดกรอบ
                            detections = detect_objects()
                            
                            # ✅ Log การตรวจจับ
                            if frame_count % 30 == 0:  # Log ทุก 30 เฟรม (~10 วินาที)
                                print(f"[SOCKETIO] Detections: {len(detections)}, Contour Active: {contour_detection_active}")
                            
                            # เตรียม measurements จาก detections
                            all_measurements = []
                            
                            # 🔄 โหลด fallback config ครั้งแรก (ถ้ายังไม่มี)
                            global fallback_measurement_config, latest_all_measurements, active_machine_name, active_lot_id, active_lot_name
                            if fallback_measurement_config is None:
                                try:
                                    config_file = Path(BASE_PATH) / 'configurations.json'
                                    if not config_file.exists():
                                        config_file = Path(BASE_PATH).parent / 'python_scripts' / 'configurations.json'
                                    if config_file.exists():
                                        with open(config_file, 'r', encoding='utf-8') as f:
                                            _configs = json.load(f)
                                        if _configs:
                                            fallback_measurement_config = _configs[0]
                                            print(f"[CONFIG] Loaded fallback config: {fallback_measurement_config['name']}")
                                except Exception as _e:
                                    print(f"[CONFIG] Failed to load fallback: {_e}")
                            
                            # ✅ ใช้ active config หรือ fallback config สำหรับคำนวณ status
                            effective_config = active_measurement_config or fallback_measurement_config
                            
                            # Log which config is being used (every 60 frames)
                            if frame_count % 60 == 0:
                                if active_measurement_config:
                                    print(f"[CONFIG] Using ACTIVE config: '{active_measurement_config['name']}' ({active_measurement_config['target_area_min']}-{active_measurement_config['target_area_max']} mm²)")
                                elif fallback_measurement_config:
                                    print(f"[CONFIG] Using FALLBACK config: '{fallback_measurement_config['name']}' (no measurement session started)")
                                else:
                                    print("[CONFIG] No config loaded - status will be None")
                            
                            for idx, detection in enumerate(detections):
                                if 'bbox' in detection:
                                    width_mm = detection.get('width_mm', 0)
                                    height_mm = detection.get('height_mm', 0)
                                    area_mm2 = width_mm * height_mm if (width_mm > 0 and height_mm > 0) else 0
                                    
                                    # ✅ คำนวณ pass/fail จาก effective_config (active or fallback)
                                    measurement_status = None  # 'pass', 'fail', or None
                                    measurement_pass = None  # backward compatibility
                                    
                                    if effective_config and area_mm2 > 0:
                                        target_min = effective_config.get('target_area_min', 0)
                                        target_max = effective_config.get('target_area_max', 999999)
                                        tolerance = effective_config.get('tolerance', 0)
                                        
                                        # 🎯 2 levels: pass (เขียว), fail (แดง)
                                        # ✅ Pass: อยู่ในช่วง หรือ ห่างจากช่วงไม่เกิน tolerance
                                        # ❌ Fail: ห่างจากช่วงมากกว่า tolerance
                                        if target_min <= area_mm2 <= target_max:
                                            # อยู่ในช่วง target = ผ่าน
                                            measurement_status = 'pass'
                                            measurement_pass = True
                                        else:
                                            # นอกช่วง - คำนวณ deviation จากขอบช่วง
                                            if area_mm2 < target_min:
                                                deviation = target_min - area_mm2
                                            else:  # area_mm2 > target_max
                                                deviation = area_mm2 - target_max
                                            
                                            if deviation <= tolerance:
                                                # ห่างจากช่วงไม่เกิน tolerance = ผ่าน
                                                measurement_status = 'pass'
                                                measurement_pass = True
                                            else:
                                                # ห่างจากช่วงมากกว่า tolerance = ไม่ผ่าน
                                                measurement_status = 'fail'
                                                measurement_pass = False
                                    
                                    measurement = {
                                        'label': detection.get('label', f'Object_{idx+1}'),
                                        'width_mm': round(width_mm, 2),
                                        'height_mm': round(height_mm, 2),
                                        'area_mm2': round(area_mm2, 2),
                                        'bbox': detection['bbox'],
                                        'confidence': detection.get('confidence', 0.95),
                                        'hasObject': True,
                                        'pass': measurement_pass,  # backward compatibility
                                        'status': measurement_status  # 'pass', 'near_pass', 'fail', None
                                    }
                                    all_measurements.append(measurement)
                            
                            # 💾 บันทึก measurements ล่าสุดสำหรับใช้ใน capture
                            latest_all_measurements = all_measurements.copy()
                            
                            # 📊 Calculate CURRENT FRAME statistics (not session accumulation)
                            # Send real-time counts of objects in current frame
                            current_frame_stats = {
                                'total': 0,
                                'pass': 0,
                                'near_pass': 0,
                                'fail': 0
                            }
                            
                            for _m in all_measurements:
                                _status = _m.get('status')
                                if _status and _status in current_frame_stats:
                                    current_frame_stats['total'] += 1
                                    current_frame_stats[_status] += 1
                                elif not _status:
                                    # ถ้าไม่มี status (ไม่มี config) นับเป็น total เฉยๆ
                                    current_frame_stats['total'] += 1
                            
                            # ⚠️ Override global stats with current frame stats (realtime display)
                            measurement_statistics = current_frame_stats.copy()
                            
                            with frame_lock:
                                # ใช้ latest_annotated_frame (มีกรอบ ROI) ถ้ามี ไม่งั้นใช้ latest_frame
                                frame_to_send = latest_annotated_frame if latest_annotated_frame is not None else latest_frame
                                
                                if frame_to_send is not None:
                                    # ⚡ ย่อภาพก่อนส่ง: เฟรมเต็ม 1920x1080 base64 ≈ 300KB ต่อเฟรม
                                    # ซึ่งท่อ Socket.IO ส่งไม่ทัน ทำให้ภาพบนเว็บขาดหาย/กระตุก
                                    stream_max_width = 960
                                    if frame_to_send.shape[1] > stream_max_width:
                                        _scale = stream_max_width / float(frame_to_send.shape[1])
                                        frame_to_send = cv2.resize(
                                            frame_to_send,
                                            (stream_max_width, int(frame_to_send.shape[0] * _scale)),
                                            interpolation=cv2.INTER_AREA
                                        )

                                    # ⚡ เข้ารหัส frame เป็น JPEG base64 (quality 65 = สมดุลระหว่างคุณภาพและขนาด)
                                    _, buffer = cv2.imencode('.jpg', frame_to_send, [cv2.IMWRITE_JPEG_QUALITY, 65])
                                    frame_base64 = base64.b64encode(buffer).decode('utf-8')
                                    
                                    # Debug log
                                    if frame_count % 30 == 0:
                                        print(f"[SOCKETIO] ✅ Emitting frame {frame_count}, size: {len(frame_base64)} bytes, detections: {len(detections)}")
                                    
                                    # ส่งต่อให้ emitter thread (ห้าม emit ตรงนี้ - จะบล็อก XLink)
                                    global pending_frame_payload
                                    with emit_lock:
                                        pending_frame_payload = {
                                            'frame': frame_base64,
                                            'measurements': all_measurements,
                                            'detections_count': len(detections),
                                            'statistics': measurement_statistics.copy(),
                                            'active_setup': {
                                                'machine_id': active_machine_id,
                                                'machine_name': active_machine_name,
                                                'lot_id': active_lot_id,
                                                'lot_name': active_lot_name,
                                                'config': active_measurement_config or fallback_measurement_config
                                            },
                                            'timestamp': datetime.now().isoformat()
                                        }
                                    frame_emit_event.set()
                                else:
                                    if frame_count % 30 == 0:
                                        print(f"[SOCKETIO] ⚠️ frame_to_send is None at frame {frame_count}")
                        except Exception as e:
                            print(f"[SOCKETIO] ❌ Error emitting frame: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    last_success_time = time.time()
                    global last_frame_time
                    last_frame_time = time.time()  # Update global frame timestamp
                    
                    # Log success every 100 frames (~100 seconds ที่ ~3 FPS) พร้อม bandwidth estimate
                    if frame_count % 100 == 0:
                        # ประมาณการ bandwidth (frame size ~30KB ที่ quality 50%, ~3 FPS)
                        estimated_bandwidth_mbps = (30 * 1024 * 8 * 3) / (1024 * 1024)  # ~0.7 Mbps
                        print(f"[CAMERA] ✅ Stable - {frame_count} frames sent, {total_errors} errors, est. bandwidth: {estimated_bandwidth_mbps:.1f} Mbps")
            else:
                print(" ❌ Device is closed unexpectedly!")
                # Reset queue cache so they get re-created after reconnect
                cached_device_for_queues = None
                queue_rgb = None
                queue_depth = None
                # พยายาม reconnect ทันที
                if recovery_attempts < max_recovery_attempts:
                    recovery_attempts += 1
                    print(f" Attempt {recovery_attempts}/{max_recovery_attempts}...")
                    try:
                        time.sleep(0.5)
                        _reinit_camera_serialized()
                        consecutive_errors = 0
                        last_success_time = time.time()
                        continue
                    except Exception as e:
                        print(f" ❌ Failed: {e}")
                        time.sleep(2)
                        consecutive_errors = 0  # Reset และลองใหม่
                else:
                    print("[CAMERA] ⚠️ Max recovery attempts, resetting and continue...")
                    consecutive_errors = 0
                    recovery_attempts = 0
                    time.sleep(10)
                    # ไม่ stop camera - ให้ทำงานต่อ
            
            # ✅ Sleep time ที่สมดุล - ให้ camera ทำงาน smooth
            time.sleep(0.067)  # ⚡ ~15 FPS potential, skip ทุก 3 เฟรม = 5 FPS effective (Smooth + Efficient)
            
        except Exception as e:
            consecutive_errors += 1
            total_errors += 1
            
            # Check if camera has been unresponsive too long
            time_since_success = time.time() - last_success_time
            time_since_recovery = time.time() - last_recovery_time
            
            # Log errors (ลดความถี่สำหรับ LAN camera)
            if consecutive_errors <= 3 or consecutive_errors % 20 == 0:
                print(f" Camera error #{consecutive_errors} (time since success: {time_since_success:.1f}s): {e}")
            
            # === RECOVERY ONLY IF TRULY STUCK AND NOT IN GRACE PERIOD ===
            should_recover = (
                (consecutive_errors >= max_consecutive_errors or time_since_success > max_time_without_frame) and
                time_since_success > grace_period and  # ให้เวลาผ่อนผัน
                time_since_recovery > 20.0  # ลดเหลือ 20 วินาที (จากเดิม 60 วินาที)
            )
            
            if should_recover:
                print(f" ❌ Camera stuck! (errors={consecutive_errors}, timeout={time_since_success:.1f}s)")
                
                last_recovery_time = time.time()  # บันทึกเวลาที่เริ่ม recovery
                
                if recovery_attempts < max_recovery_attempts:
                    recovery_attempts += 1
                    print(f" ♻️ Attempt {recovery_attempts}/{max_recovery_attempts} (LAN camera - be patient)...")
                    
                    try:
                        # Force close and cleanup
                        if oak_device:
                            try:
                                print(" Closing LAN device gracefully...")
                                oak_device.close()
                            except:
                                pass
                        
                        oak_device = None
                        oak_pipeline = None
                        # Reset queue cache
                        cached_device_for_queues = None
                        queue_rgb = None
                        queue_depth = None
                        
                        # Wait longer for LAN camera (network latency)
                        wait_time = min(5.0 * (2 ** (recovery_attempts - 1)), 20.0)  # เพิ่มเป็น 5s-20s สำหรับ LAN
                        print(f" Waiting {wait_time:.1f}s for LAN camera...")
                        time.sleep(wait_time)
                        
                        # Reinitialize
                        print(" Reinitializing LAN camera...")
                        _reinit_camera_serialized()
                        
                        # Verify (รอนานขึ้นสำหรับ LAN)
                        time.sleep(3)
                        if oak_device and not oak_device.isClosed():
                            print(" ✅ LAN camera recovered successfully!")
                            consecutive_errors = 0
                            last_success_time = time.time()
                            recovery_attempts = 0
                            continue
                        else:
                            raise Exception("Device not ready after init")
                    
                    except Exception as recovery_error:
                        print(f" ❌ Attempt {recovery_attempts} failed: {recovery_error}")
                        time.sleep(2)
                        consecutive_errors = 0  # Reset เพื่อให้ลองใหม่
                        continue
                
                # ไม่หยุดกล้อง - ให้ลองต่อ
                print("[CAMERA] ⚠️ Max recovery attempts reached, resetting and continue...")
                consecutive_errors = 0
                recovery_attempts = 0
                time.sleep(10)  # รอนานๆ แล้วลองใหม่
                # ไม่ตั้ง camera_active = False เพื่อให้กล้องทำงานต่อ
            
            time.sleep(0.2)  # Brief wait on error
    
    print(f"[CAMERA LOOP] Exiting camera loop thread (generation {generation})")

def initialize_oak_camera():
    """Initialize Luxonis OAK camera"""
    global oak_pipeline, oak_device, camera_thread, running, camera_active

    # No depthai on this host (e.g. a desktop without an OAK camera):
    # skip cleanly instead of raising / spamming tracebacks.
    if not HAS_DEPTHAI:
        print("[CAMERA] depthai module not available - cannot initialize OAK camera on this host")
        camera_active = False
        return False

    try:
        print("=" * 60)
        print("CAMERA INITIALIZATION START")
        print("=" * 60)
        
        # Stop existing camera if running
        if oak_device is not None:
            print("[STEP 1] Stopping existing camera connection...")
            stop_oak_camera()
            time.sleep(2)
        else:
            print("[STEP 1] No existing camera connection")
        
        # Get Network Camera IP from config (optional)
        print("[STEP 2] Preparing camera connection...")
        network_camera_ip = system_config.get('network_camera_ip', '').strip()
        if network_camera_ip:
            print(f"   Network camera IP configured: {network_camera_ip}")
            pass  # skip bootloader IP-scan (IP already set on camera; scan interferes with PoE connect)
        else:
            print(f"   Auto-detect mode (CSI/USB priority, no network IP configured)")
        
        # Force close any lingering connections
        print("[STEP 2.5] Clearing device resources...")
        try:
            import gc
            gc.collect()
            time.sleep(1)
            print("    Resources cleared")
        except Exception as e:
            print(f"    Resource cleanup: {e}")
        
        # Create pipeline
        print("[STEP 3] Creating depthai pipeline...")
        pipeline = dai.Pipeline()
        # Luxonis' recommended setting for PoE: send data in one chunk instead of
        # splitting it, which lowers latency and keeps the link busy less often.
        try:
            pipeline.setXLinkChunkSize(0)
        except Exception as _e:
            print(f"    (XLink chunk size not applied: {_e})")
        
        # Define source - RGB camera (ใช้ค่าคงที่เพื่อความเสถียร)
        print("[STEP 4] Configuring RGB camera node...")
        cam_rgb = pipeline.create(dai.node.ColorCamera)
        
        # ใช้ 720p เพื่อสมดุลระหว่างคุณภาพและ bandwidth (Sweet Spot!)
        # 1280x720 = เหมาะสมสำหรับ detection ที่แม่นยำ + smooth + ประหยัด bandwidth
        cam_rgb.setPreviewSize(1280, 720)
        cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_720_P)
        cam_rgb.setInterleaved(False)
        cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        
        # ใช้ 15 FPS เพื่อความ smooth ที่ดีและประหยัดพอดี
        fps = 15  # Sweet spot: smooth + efficient
        cam_rgb.setFps(fps)
        
        # Apply zoom from config
        # ⭐ ปิดการซูม - ตรึงไว้ที่ 1.0x เสมอ
        zoom_level = 1.0  # ฟิกไว้ไม่ให้ซูม
        print(f"[STEP 4] Zoom disabled (fixed at 1.0x)")
        
        # Auto Focus - ใช้ CONTINUOUS_VIDEO (เบากว่า CONTINUOUS_PICTURE)
        if system_config.get('auto_focus', 1) == 1:
            cam_rgb.initialControl.setAutoFocusMode(dai.CameraControl.AutoFocusMode.CONTINUOUS_VIDEO)
        
        # Auto White Balance from config
        if system_config.get('auto_white_balance', 1) == 1:
            cam_rgb.initialControl.setAutoWhiteBalanceMode(dai.CameraControl.AutoWhiteBalanceMode.AUTO)
        
        # Auto Exposure from config
        if system_config.get('auto_exposure', 1) == 1:
            cam_rgb.initialControl.setAutoExposureEnable()
            cam_rgb.initialControl.setAutoExposureLock(False)
            cam_rgb.initialControl.setAutoExposureRegion(0, 0, 65535, 65535)
        
        # ISO Sensitivity (ความไวแสง) - Auto
        # OAK-D รองรับ ISO 100-1600 (ยิ่งสูง ยิ่งไวแสง แต่มี noise มากขึ้น)
        # cam_rgb.initialControl.setManualExposure(10000, 400)  # (exposure_us, iso_sensitivity)
        # ปล่อย Auto = ให้กล้องปรับเอง
        
        # Brightness/Contrast (ถ้าต้องการปรับเพิ่ม)
        # cam_rgb.initialControl.setBrightness(0)  # -10 to 10
        # cam_rgb.initialControl.setContrast(0)     # -10 to 10
        # cam_rgb.initialControl.setSaturation(0)   # -10 to 10
        
        print(f"    RGB camera configured: 1280x720 @ {fps}fps with Auto Focus + Auto Exposure (Balanced: Smooth + Efficient)")
        
        # Create stereo depth
        print("[STEP 5] Configuring stereo depth nodes...")
        mono_left = pipeline.create(dai.node.MonoCamera)
        mono_right = pipeline.create(dai.node.MonoCamera)
        stereo = pipeline.create(dai.node.StereoDepth)
        
        mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        mono_left.setBoardSocket(dai.CameraBoardSocket.CAM_B)
        mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
        mono_right.setBoardSocket(dai.CameraBoardSocket.CAM_C)
        
        # ใช้ HIGH_DENSITY แทน HIGH_ACCURACY - เบากว่ามาก
        stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
        stereo.setLeftRightCheck(False)  # ปิด - ลดภาระการคำนวณ
        stereo.setExtendedDisparity(False)
        stereo.setSubpixel(False)  # ปิด subpixel - ลดภาระมาก
        
        # ลด confidence threshold - ยอมรับ depth ที่ confidence ต่ำกว่า
        stereo.initialConfig.setConfidenceThreshold(150)  # ลดจาก 200
        
        # ใช้ median filter เล็กลง - ลดภาระการประมวลผล
        stereo.initialConfig.setMedianFilter(dai.MedianFilter.KERNEL_3x3)
        
        mono_left.out.link(stereo.left)
        mono_right.out.link(stereo.right)
        print("    Stereo depth configured: 400p")
        
        # Create outputs
        print("[STEP 6] Creating output streams...")
        xout_rgb = pipeline.create(dai.node.XLinkOut)
        xout_rgb.setStreamName("rgb")
        cam_rgb.preview.link(xout_rgb.input)
        
        xout_depth = pipeline.create(dai.node.XLinkOut)
        xout_depth.setStreamName("depth")
        stereo.depth.link(xout_depth.input)
        print("    Output streams created: rgb, depth")
        
        # Connect to OAK camera (Universal support for all Luxonis models)
        # Auto-detect CSI/USB first, then Network if configured
        # Supports: OAK-D-CM4 (CSI), OAK-D (USB), OAK-1-PoE (Network), etc.
        print(f"[STEP 7] Connecting to OAK camera...")

        # === Acquire cross-process camera lock ===
        print("[STEP 7.0] Attempting to acquire cross-process camera lock (worker-aware)...")
        locked = acquire_lock(timeout=0.5)
        if not locked:
            print("[STEP 7.0] Camera lock held by another process (worker). Skipping device init.")
            camera_active = False
            try:
                release_lock()
            except Exception:
                pass
            return False
        else:
            print("[STEP 7.0] Acquired camera lock - proceeding to open device")

        # Build connection methods based on configuration
        # If a network camera IP is configured, try it FIRST (fast) so we don't
        # waste ~25s failing USB methods before reaching the PoE camera (and the
        # USB scan can disturb the PoE camera, breaking the later Network attempt).
        if network_camera_ip:
            connection_methods = [
                ('Network', network_camera_ip),
                ('CSI/USB Auto-detect', 'auto'),
            ]
        else:
            connection_methods = [
                ('CSI/USB Auto-detect', 'auto'),
                ('USB2 Fallback', 'usb2'),
            ]

        max_attempts_per_method = 3  # เพิ่มเป็น 3 attempts
        connection_success = False
        connection_delay = 2  # seconds between retries
        connected_method = None
        connected_method_name = None
        
        for method_name, method_config in connection_methods:
            if connection_success:
                break
                
            print(f"\n   Trying {method_name} connection...")
            
            for attempt in range(1, max_attempts_per_method + 1):
                try:
                    print(f"   Attempt {attempt}/{max_attempts_per_method}...", end=" ")
                    
                    if method_name == 'CSI/USB Auto-detect':
                        # Auto-detect any local camera (CSI on Raspberry Pi or USB on any platform)
                        # This works for: OAK-D-CM4, OAK-D, OAK-1, OAK-D-Lite, etc.
                        oak_device = dai.Device(pipeline)
                        
                    elif method_name == 'USB2 Fallback':
                        # Force USB 2.0 mode - more stable on some Windows/USB3 setups
                        oak_device = dai.Device(pipeline, dai.UsbSpeed.HIGH)
                        
                    elif method_name == 'Network':
                        # Connect to Network/PoE camera with specific IP
                        # This works for: OAK-1-PoE, OAK-D-PoE, etc.
                        device_info = dai.DeviceInfo(method_config)
                        oak_device = dai.Device(pipeline, device_info)
                    
                    # Device created successfully
                    oak_pipeline = pipeline
                    connected_method = method_config if method_name == 'Network' else 'auto'
                    connected_method_name = method_name
                    print(f"✓ Connected!")
                    connection_success = True
                    break
                    
                except RuntimeError as e:
                    error_msg = str(e)
                    print(f"✗ Failed ({error_msg[:50]}...)")
                    
                    # If last attempt for this method, skip to next
                    if attempt >= max_attempts_per_method:
                        print(f"   → Skipping to next method...")
                        break
                    
                    # Wait before retry
                    time.sleep(connection_delay)
                    
                except Exception as e:
                    print(f"✗ Error: {str(e)[:50]}")
                    if attempt >= max_attempts_per_method:
                        break
                    time.sleep(connection_delay)
        
        # Check if any connection method succeeded
        if not connection_success:
            print(f"\n{'='*60}")
            print(f" ❌ Cannot connect to OAK camera")
            if network_camera_ip:
                print(f"Tried: CSI/USB Auto-detect and Network ({network_camera_ip})")
            else:
                print(f"Tried: CSI/USB Auto-detect only (no network IP configured)")
            print(f"{'='*60}")
            print(f"\nPossible solutions:")
            print(f"  For CSI camera (Raspberry Pi):")
            print(f"    1. Check CSI ribbon cable connection (contacts facing correct way)")
            print(f"    2. Ensure camera is enabled in raspi-config")
            print(f"    3. Check: 'dmesg | grep imx' to see if sensor detected")
            print(f"  For USB camera (Windows/Linux/Mac):")
            print(f"    4. Check USB cable is properly connected (USB 3.0 port recommended)")
            print(f"    5. Try different USB port or cable")
            print(f"    6. Check: 'lsusb' (Linux) or Device Manager (Windows)")
            if network_camera_ip:
                print(f"  For Network/PoE camera:")
                print(f"    7. Verify camera IP: {network_camera_ip}")
                print(f"    8. Test connection: ping {network_camera_ip}")
                print(f"    9. Ensure camera is on same network/subnet")
                print(f"    10. Check PoE switch is providing power")
            else:
                print(f"  For Network/PoE camera:")
                print(f"    7. Set 'network_camera_ip' in config (e.g., '192.168.1.100')")
            print(f"  General:")
            print(f"    - Restart the camera and try again")
            print(f"    - Close other apps using the camera")
            print(f"    - Check camera has power and LED is on")
            print(f"{'='*60}\n")
            camera_active = False
            # Release the camera lock so the next attempt / watchdog can retry.
            try:
                release_lock()
            except Exception:
                pass
            return False
        
        # Show connection details
        try:
            device_name = oak_device.getDeviceName()
            mxid = oak_device.getMxId()
            
            # Determine connection type and icon
            if connected_method_name == 'CSI/USB Auto-detect':
                # Try to determine if CSI or USB
                if 'CM4' in device_name.upper() or 'CSI' in device_name.upper():
                    conn_type = "CSI Direct (Raspberry Pi)"
                    conn_icon = "📷"
                else:
                    conn_type = "USB Direct"
                    conn_icon = "🔌"
            elif connected_method_name == 'Auto-discovered':
                conn_type = "Auto-discovered Device (LAN/USB)"
                conn_icon = "🌐"
            else:
                conn_type = f"Network/PoE ({connected_method})"
                conn_icon = "🌐"
            
            print(f"\n{'='*60}")
            print(f"   {conn_icon} Camera Connected Successfully!")
            print(f"   Connection Type: {conn_type}")
            print(f"   Device Model: {device_name}")
            print(f"   Device ID: {mxid}")
            print(f"   Compatible: All Luxonis OAK models ✓")
            print(f"{'='*60}\n")
        except Exception as e:
            print(f"   ✓ Camera connected successfully via {method_name}")
            print(f"   Connection method: {connected_method}\n")
        
        # Start camera thread (only if one isn't already running).
        # When called from the camera_loop recovery path, the loop thread is
        # still alive and just needs the freshly-opened device — starting a
        # second thread here would double-drain the queues and emit duplicates.
        print("[STEP 8] Ensuring camera processing thread is running...")
        running = True
        if camera_thread is None or not camera_thread.is_alive() or \
           camera_thread is threading.current_thread():
            if camera_thread is threading.current_thread():
                print("    Re-init from within camera loop - reusing current thread")
            else:
                global camera_loop_generation
                camera_loop_generation += 1
                camera_thread = threading.Thread(
                    target=camera_loop, args=(camera_loop_generation,), daemon=True)
                camera_thread.start()
                print(f"    Camera thread started (generation {camera_loop_generation})")
        else:
            print("    Camera thread already running - reusing it")
        
        # Wait for first frame
        print("[STEP 9] Waiting for first frame...")
        max_wait_time = 10  # Increased from 3 to 10 seconds
        for i in range(max_wait_time * 10):  # Check every 0.1s
            time.sleep(0.1)
            with frame_lock:
                if latest_frame is not None and latest_depth is not None:
                    print(f"    Frames received! RGB: {latest_frame.shape}, Depth: {latest_depth.shape}")
                    break
                elif latest_frame is not None:
                    print(f"    RGB frame received: {latest_frame.shape}")
                    break
        else:
            print(f"    No frame received after {max_wait_time} seconds, but continuing...")
        
        camera_active = True
        print("=" * 60)
        print("[SUCCESS] OAK CAMERA INITIALIZED SUCCESSFULLY!")
        print(f"Camera Thread Alive: {camera_thread.is_alive() if camera_thread else False}")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print("=" * 60)
        print(" CAMERA INITIALIZATION FAILED!")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        camera_active = False
        # Deliberately NOT clearing `running`: a failed (re)connect must not stop
        # a camera loop that is still delivering frames from the live device.
        if oak_device:
            try:
                oak_device.close()
            except:
                pass
        oak_device = None
        try:
            release_lock()
        except Exception:
            pass
        return False

def stop_oak_camera(user_initiated=False):
    """Stop OAK camera with graceful shutdown.

    `user_initiated` marks a real Stop press. A reconnect also passes through
    here, and clearing the contour flag then silently switched detection off
    behind the user's back once the camera came back.
    """
    global oak_device, oak_pipeline, running, camera_thread, camera_active, latest_frame, latest_depth
    global tracked_objects, next_object_id, contour_detection_active
    
    try:
        print(" [STOPPING] Stopping OAK camera...")
        
        # Detect if we're being called from inside the camera loop itself
        # (recovery path). We must NOT signal the loop to stop or join our own
        # thread in that case - only close/reopen the device.
        called_from_loop = (camera_thread is not None and
                            camera_thread is threading.current_thread())

        # Step 1: Signal thread to stop (skip when re-initializing from the loop)
        if not called_from_loop:
            running = False
            camera_active = False
            if user_initiated:
                contour_detection_active = False

        # Step 2: Wait for thread to finish gracefully (never join ourselves)
        if (not called_from_loop and camera_thread is not None
                and camera_thread.is_alive()):
            print(" Waiting for camera thread to finish (max 5s)...")
            camera_thread.join(timeout=5)
            if camera_thread.is_alive():
                print(" Camera thread did not stop cleanly")
            else:
                print("  Camera thread stopped")
            camera_thread = None
        
        # Step 3: Close device with retry
        if oak_device is not None:
            for attempt in range(3):
                try:
                    if not oak_device.isClosed():
                        print(f" Closing OAK device (attempt {attempt + 1}/3)...")
                        oak_device.close()
                        time.sleep(0.5)  # Longer delay for LAN camera
                    print("  OAK device closed")
                    break
                except Exception as e:
                    if attempt < 2:
                        print(f" Close attempt {attempt + 1} failed: {e}, retrying...")
                        time.sleep(0.5)
                    else:
                        print(f" ❌ Failed to close device after 3 attempts: {e}")
            oak_device = None
        
        # Step 4: Clear pipeline
        oak_pipeline = None
        
        # Step 5: Clear frame buffers
        with frame_lock:
            latest_frame = None
            latest_depth = None
        
        # Step 6: Reset tracking
        tracked_objects = {}
        next_object_id = 1
        clear_detection_memory()
        
        print(" ✅ OAK camera stopped successfully")
        try:
            release_lock()
        except Exception:
            pass
        return True
        
    except Exception as e:
        print(f" ❌ Error stopping camera: {e}")
        import traceback
        traceback.print_exc()
        
        # Force cleanup
        camera_active = False
        running = False
        contour_detection_active = False
        oak_device = None
        oak_pipeline = None
        
        return False

def apply_contrast_enhancement(frame, alpha=1.5, beta=30):
    """Apply contrast enhancement using CLAHE (Contrast Limited Adaptive Histogram Equalization)"""
    try:
        # Convert to LAB color space
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel with higher intensity
        clahe = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l)
        
        # Merge channels back
        enhanced_lab = cv2.merge([l_enhanced, a, b])
        enhanced_frame = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        
        # Apply additional brightness/contrast adjustment
        enhanced_frame = cv2.convertScaleAbs(enhanced_frame, alpha=1.2, beta=10)
        
        return enhanced_frame
    except Exception as e:
        print(f"Error applying contrast: {e}")
        return frame

def apply_depth_colormap(depth_normalized, colorscheme='gray'):
    """Apply color mapping to normalized depth frame (expects uint8 0-255)"""
    try:
        # Ensure input is uint8
        if depth_normalized.dtype != np.uint8:
            depth_normalized = depth_normalized.astype(np.uint8)
        
        # Apply colormap based on scheme
        if colorscheme == 'jet':
            colored_depth = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
        elif colorscheme == 'rainbow':
            colored_depth = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_RAINBOW)
        elif colorscheme == 'turbo':
            colored_depth = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_TURBO)
        elif colorscheme == 'hot':
            colored_depth = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_HOT)
        elif colorscheme == 'cool':
            colored_depth = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_COOL)
        else:  # gray (default)
            colored_depth = cv2.cvtColor(depth_normalized, cv2.COLOR_GRAY2BGR)
        
        return colored_depth
    except Exception as e:
        print(f"Error applying depth colormap: {e}")
        # Return grayscale as fallback
        return cv2.cvtColor(depth_normalized, cv2.COLOR_GRAY2BGR)

def get_contrast_preview():
    """
    Get depth-based height visualization preview
    Uses DEPTH CAMERA to measure object height at SAME LOCATION as RGB detection
    This ensures depth measurements are for the SAME objects detected by RGB camera
    """
    global latest_depth, latest_frame
    try:
        with frame_lock:
            if latest_depth is None:
                return None
            depth = latest_depth.copy()
        
        # Depth data is in millimeters (uint16: 0-65535)
        # Clip to reasonable range (300mm to 3000mm = 30cm to 3m)
        depth_clipped = np.clip(depth, 300, 3000)
        
        # Normalize to 0-255 for visualization (closer = red, farther = blue)
        depth_normalized = ((depth_clipped - 300) / (3000 - 300) * 255).astype(np.uint8)
        
        # Apply JET colormap (blue=far, red=close)
        depth_colored = cv2.applyColorMap(depth_normalized, cv2.COLORMAP_JET)
        
        # Get current detections from RGB camera
        detections = detect_objects()
        
        # Draw height measurements for SAME objects as RGB detection
        for detection in detections:
            if 'bbox' not in detection:
                continue
            
            bbox = detection['bbox']
            x, y, w, h = bbox
            
            # Make sure bbox is within depth map bounds
            x = max(0, min(x, depth.shape[1] - 1))
            y = max(0, min(y, depth.shape[0] - 1))
            w = max(1, min(w, depth.shape[1] - x))
            h = max(1, min(h, depth.shape[0] - y))
            
            # Extract depth values at detection location
            object_depth_region = depth[y:y+h, x:x+w]
            valid_depths = object_depth_region[(object_depth_region > 300) & (object_depth_region < 3000)]
            
            if len(valid_depths) > 10:  # Need sufficient data points
                # Calculate height: difference between closest and farthest point
                min_depth = np.percentile(valid_depths, 5)  # 5th percentile (filter outliers)
                max_depth = np.percentile(valid_depths, 95)  # 95th percentile
                avg_depth = np.median(valid_depths)
                object_height_mm = abs(max_depth - min_depth)
                
                # Draw bounding box (SAME as RGB detection)
                cv2.rectangle(depth_colored, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Draw detection label from RGB
                detection_label = detection.get('label', 'Object')
                confidence = detection.get('confidence', 0) * 100
                
                # Draw height and depth info
                label = f"{detection_label} {confidence:.0f}%"
                label2 = f"H:{object_height_mm:.0f}mm D:{avg_depth:.0f}mm"
                
                label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
                cv2.rectangle(depth_colored, (x, y-label_size[1]-25), (x+max(label_size[0], 150), y), (0, 0, 0), -1)
                cv2.putText(depth_colored, label, (x+4, y-15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.putText(depth_colored, label2, (x+4, y-3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        # Add color scale legend
        legend_h = 20
        legend_w = depth_colored.shape[1] - 40
        legend_gradient = np.linspace(0, 255, legend_w, dtype=np.uint8).reshape(1, -1)
        legend_gradient = np.repeat(legend_gradient, legend_h, axis=0)
        legend_colored = cv2.applyColorMap(legend_gradient, cv2.COLORMAP_JET)
        
        # Draw legend on image
        depth_colored[10:10+legend_h, 20:20+legend_w] = legend_colored
        cv2.rectangle(depth_colored, (20, 10), (20+legend_w, 10+legend_h), (255, 255, 255), 2)
        cv2.putText(depth_colored, "CLOSE", (25, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        cv2.putText(depth_colored, "FAR", (20+legend_w-40, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Resize to preview size
        preview_h = 300
        preview_w = int(depth_colored.shape[1] * preview_h / depth_colored.shape[0])
        preview_resized = cv2.resize(depth_colored, (preview_w, preview_h))
        
        # Encode to base64
        _, buffer = cv2.imencode('.jpg', preview_resized, [cv2.IMWRITE_JPEG_QUALITY, 50])  # ✅ ลดเป็น 50%
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{frame_base64}"
    except Exception as e:
        print(f"Error getting contrast preview: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_depth_preview(colorscheme='gray'):
    """Get depth map preview with color scheme (full scene depth visualization)"""
    global latest_depth
    try:
        with frame_lock:
            if latest_depth is None:
                return None
            depth = latest_depth.copy()
        
        # Clip depth to reasonable range (300-3000mm)
        depth_clipped = np.clip(depth, 300, 3000)
        
        # Normalize to 0-255 with better contrast
        depth_normalized = ((depth_clipped - 300) / (3000 - 300) * 255).astype(np.uint8)
        
        # Enhance contrast using histogram equalization
        depth_enhanced = cv2.equalizeHist(depth_normalized)
        
        # Apply selected colormap
        depth_colored = apply_depth_colormap(depth_enhanced, colorscheme)
        
        # Resize to smaller preview size (40% ของเดิม)
        preview_h = 180  # ✅ ลดจาก 300 เป็น 180
        preview_w = int(depth_colored.shape[1] * preview_h / depth_colored.shape[0])
        depth_resized = cv2.resize(depth_colored, (preview_w, preview_h))
        
        # Encode to base64 with LOW quality
        _, buffer = cv2.imencode('.jpg', depth_resized, [cv2.IMWRITE_JPEG_QUALITY, 50])  # ✅ ลดเป็น 50%
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{frame_base64}"
    except Exception as e:
        print(f"Error getting depth preview: {e}")
        return None

def get_camera_frame(enable_contrast=False, depth_colorscheme='gray'):
    """Get current frame from camera with optional contrast and depth colorization"""
    global latest_frame, latest_depth, camera_active, last_frame_time
    
    try:
        # ✅ FIX: ตรวจสอบทั้ง camera_active, oak_device และ device.isClosed()
        device_ok = (oak_device is not None and not oak_device.isClosed()) if oak_device else False
        
        # ตรวจสอบว่า frame ยังสดไหม (ไม่เก่าเกิน 30 วินาที)
        time_since_frame = time.time() - last_frame_time if last_frame_time else 999
        frame_is_fresh = time_since_frame < 30.0
        
        # Check if camera is actually active and connected
        if not camera_active or not device_ok or not frame_is_fresh:
            # Return placeholder for no camera
            frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
            cv2.putText(frame, "Camera Not Connected", (750, 500), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (100, 100, 100), 3)
            cv2.putText(frame, "Please connect an OAK camera and click Start Camera", (550, 580), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 150, 150), 2)
        else:
            with frame_lock:
                # ✅ ใช้ annotated_frame ที่วาดกรอบแล้ว ถ้าไม่มีใช้ latest_frame
                if latest_annotated_frame is not None:
                    frame = latest_annotated_frame.copy()
                elif latest_frame is not None:
                    frame = latest_frame.copy()
                else:
                    # ✅ FIX: แสดง warning เมื่อไม่มี frame (อาจบ่งชี้ปัญหา)
                    frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
                    cv2.putText(frame, "Camera Connected - Waiting for frames...", (650, 500), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 200, 0), 2)
                    cv2.putText(frame, "If this persists, try stopping and restarting camera", (600, 560), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (150, 150, 0), 2)
                
                depth = latest_depth.copy() if latest_depth is not None else None
            
            # Don't modify the main frame - keep it as original RGB with detections
            # Contrast and depth visualizations will be provided separately
            pass
        
        # ✅ ภาพถูก resize แล้วตอนเก็บ (60%) ไม่ต้อง resize อีก
        # Encode to base64 with LOW quality for bandwidth
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])  # ✅ ลดเป็น 50%
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return f"data:image/jpeg;base64,{frame_base64}"
        
    except Exception as e:
        print(f"Error getting frame: {e}")
        # Return error frame
        error_frame = np.zeros((1080, 1920, 3), dtype=np.uint8)
        cv2.putText(error_frame, "Camera Error", (800, 540), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        _, buffer = cv2.imencode('.jpg', error_frame)
        frame_base64 = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{frame_base64}"

def find_object_contour(depth_frame, ground_distance):
    """
    Find object contour for irregular-shaped objects (like clay/putty)
    Uses depth segmentation to separate object from background
    Returns:
    - bbox: [x, y, w, h] - axis-aligned bounding box
    - min_rect: ((cx, cy), (width, height), angle) - minimum area rectangle
    - contour: largest contour points
    - hull: convex hull points
    """
    try:
        # Create mask for object region (closer than ground)
        # Objects are closer to camera (smaller depth values) than ground
        object_threshold = ground_distance - 50  # 50mm tolerance
        object_mask = (depth_frame < object_threshold) & (depth_frame > 300)
        object_mask = object_mask.astype(np.uint8) * 255
        
        # Morphological operations to clean up noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        object_mask = cv2.morphologyEx(object_mask, cv2.MORPH_CLOSE, kernel)
        object_mask = cv2.morphologyEx(object_mask, cv2.MORPH_OPEN, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(object_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return None
        
        # Find largest contour (main object)
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        
        # Filter out small noise (minimum 50 pixels ≈3mm x 3mm)
        if area < 50:
            return None
        
        # 1. Axis-aligned bounding box (เดิม)
        x, y, w, h = cv2.boundingRect(largest_contour)
        bbox = [x, y, w, h]
        
        # 2. Minimum area rectangle (กรอบที่เล็กที่สุด - อาจเอียง)
        # → ได้ width × height ที่แท้จริงของวัตถุ
        min_rect = cv2.minAreaRect(largest_contour)
        # min_rect = ((center_x, center_y), (width, height), angle)
        
        # 3. Convex hull (เส้นรอบนอกสุด)
        # → คำนวณพื้นที่ภายในได้
        hull = cv2.convexHull(largest_contour)
        
        return {
            'bbox': bbox,
            'min_rect': min_rect,
            'contour': largest_contour,
            'hull': hull,
            'area_pixels': area,
            'hull_area_pixels': cv2.contourArea(hull)
        }
        
    except Exception as e:
        print(f"Error finding object contour: {e}")
        return None

def measure_object(bbox=None):
    """Measure object dimensions using depth data with ground plane detection"""
    global latest_depth, latest_frame, camera_active
    
    try:
        print(f"[MEASURE] Starting measurement - bbox={bbox}, camera_active={camera_active}, oak_device={oak_device is not None}")
        
        # Return empty measurement if camera not active
        if not camera_active or oak_device is None:
            print(f"[MEASURE] Skipped - camera_active={camera_active}, oak_device={oak_device is not None}")
            return {
                'width': 0,
                'height': 0,
                'depth': 0,
                'volume': 0,
                'hasObject': False
            }
        
        with frame_lock:
            if latest_depth is None:
                return {
                    'width': 0,
                    'height': 0,
                    'depth': 0,
                    'volume': 0,
                    'hasObject': False
                }
            
            depth = latest_depth.copy()
        
        # Step 1: Detect ground plane distance (bottom 20% of frame)
        h_frame, w_frame = depth.shape
        ground_roi = depth[int(h_frame * 0.8):h_frame, int(w_frame * 0.2):int(w_frame * 0.8)]
        ground_valid = ground_roi[(ground_roi > 300) & (ground_roi < 3000)]
        
        if len(ground_valid) == 0:
            return {
                'width': 0,
                'height': 0,
                'depth': 0,
                'volume': 0,
                'hasObject': False
            }
        
        ground_distance = float(np.median(ground_valid))
        
        # Step 2: Find object using contour detection if no bbox provided
        contour_data = None
        if bbox is None:
            print(f"[MEASURE] No bbox provided, using contour detection")
            result = find_object_contour(depth, ground_distance)
            if result is None:
                print(f"[MEASURE] No object found via contour detection")
                return {
                    'width': 0,
                    'height': 0,
                    'depth': 0,
                    'volume': 0,
                    'hasObject': False
                }
            
            # Check if result is dict (new format) or list (old format)
            if isinstance(result, dict):
                contour_data = result
                bbox = contour_data['bbox']
            else:
                # Backward compatibility: old format returns [x, y, w, h]
                bbox = result
                contour_data = None
        
        # Step 3: Extract object ROI
        x, y, w, h = bbox
        h_depth, w_depth = depth.shape
        
        # **CRITICAL FIX: Convert RGB coordinates to Depth coordinates**
        # RGB frame is 1920x1080 (or config preview size)
        # Depth frame is 640x400 (stereo resolution)
        preview_w = system_config.get('preview_width', 1920)
        preview_h = system_config.get('preview_height', 1080)
        
        scale_x = w_depth / preview_w
        scale_y = h_depth / preview_h
        
        # Scale bbox coordinates
        x = int(x * scale_x)
        y = int(y * scale_y)
        w = int(w * scale_x)
        h = int(h * scale_y)
        
        # Ensure ROI is within bounds
        x = max(0, min(x, w_depth - 1))
        y = max(0, min(y, h_depth - 1))
        w = max(1, min(w, w_depth - x))
        h = max(1, min(h, h_depth - y))
        
        print(f"[MEASURE] Original bbox={bbox}, Scaled bbox=[{x},{y},{w},{h}], Depth shape={depth.shape}")
        
        roi_depth = depth[y:y+h, x:x+w]
        
        # Filter valid depth values in object ROI
        valid_depths = roi_depth[(roi_depth > 300) & (roi_depth < ground_distance)]
        
        print(f"[MEASURE] bbox=[{x},{y},{w},{h}], ground_distance={ground_distance:.1f}mm, valid_depths={len(valid_depths)}")
        
        if len(valid_depths) == 0:
            print(f"[MEASURE] No valid depth values in ROI")
            return {
                'width': 0,
                'height': 0,
                'depth': 0,
                'volume': 0,
                'hasObject': False
            }
        
        # ⭐⭐ CALIBRATED: วัดขนาดจาก BOUNDING BOX พร้อม calibration
        # ตรึงความสูงกล้องไว้ที่ 400mm (ประมาณ 40cm)
        # 
        # 🎯 CALIBRATION: อ้างอิงจากวัตถุจริง W=80mm H=90mm
        # โปรแกรมวัดได้: W=61.6mm H=72.0mm
        # 
        # Scale factors:
        # - WIDTH:  80 / 61.6 = 1.299
        # - HEIGHT: 90 / 72.0 = 1.25
        
        FIXED_CAMERA_HEIGHT = 400.0  # mm - ความสูงกล้องคงที่
        
        # ✅ ใช้ calibration factors จาก current_settings (เหมือนกับ detect_by_contour)
        PIXEL_TO_MM_WIDTH = current_settings['calibration_width']
        PIXEL_TO_MM_HEIGHT = current_settings['calibration_height']
        
        # คำนวณขนาดจริงจาก bounding box pixel พร้อม calibration
        width_mm = w * PIXEL_TO_MM_WIDTH    # ✅ ซ้าย-ขวา (calibrated)
        height_mm = h * PIXEL_TO_MM_HEIGHT  # ✅ บน-ล่าง (calibrated)
        
        # ⛔ คอมเม้น DEPTH - ไม่น่าเชื่อถือ
        # median_depth = np.median(valid_depths)
        # object_top_distance = float(np.percentile(valid_depths, 5))
        # depth_mm = ground_distance - object_top_distance
        depth_mm = 0.0  # ไม่แสดงค่า depth
        
        # Log ค่าที่คำนวณได้
        print(f"[MEASURE] 📐 bbox=[{w}x{h}px], W_scale={PIXEL_TO_MM_WIDTH:.3f}, H_scale={PIXEL_TO_MM_HEIGHT:.3f}, camera_height={FIXED_CAMERA_HEIGHT}mm")
        
        # ⭐ FIXED: แสดงค่าจาก bounding box โดยตรง
        measurements = {
            'width': float(width_mm),   # ✅ จาก bbox width × scale
            'height': float(height_mm), # ✅ จาก bbox height × scale
            'depth': float(depth_mm),   # ⛔ ปิดการใช้งาน (0.0)
            'hasObject': True
        }
        
        # ⛔ Volume ไม่มีความหมายเพราะไม่มี depth
        measurements['volume'] = 0.0
        
        print(f"[MEASURE] ✅ W:{measurements['width']:.1f}mm H:{measurements['height']:.1f}mm (D:disabled)")


        
        # ⭐ NEW: Add surface area and hull area if available
        if contour_data is not None:
            # Convert pixel area to mm²
            pixel_to_mm2 = (median_depth / focal_length_px) ** 2
            measurements['surface_area_mm2'] = float(contour_data['area_pixels'] * pixel_to_mm2)
            measurements['hull_area_mm2'] = float(contour_data['hull_area_pixels'] * pixel_to_mm2)
            measurements['fill_ratio'] = float(contour_data['area_pixels'] / contour_data['hull_area_pixels'])
            
            print(f"[Area] Surface: {measurements['surface_area_mm2']:.0f}mm², Hull: {measurements['hull_area_mm2']:.0f}mm², Fill: {measurements['fill_ratio']*100:.1f}%")
        
        return measurements
        
    except Exception as e:
        print(f"Error measuring object: {e}")
        return {
            'width': 0,
            'height': 0,
            'depth': 0,
            'volume': 0,
            'hasObject': False
        }

def calculate_iou(box1, box2):
    """Calculate Intersection over Union (IOU) between two boxes"""
    # box format: [x, y, w, h]
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    
    # Calculate intersection
    x_left = max(x1, x2)
    y_top = max(y1, y2)
    x_right = min(x1 + w1, x2 + w2)
    y_bottom = min(y1 + h1, y2 + h2)
    
    if x_right < x_left or y_bottom < y_top:
        return 0.0
    
    intersection = (x_right - x_left) * (y_bottom - y_top)
    union = w1 * h1 + w2 * h2 - intersection
    
    return intersection / union if union > 0 else 0.0

def smooth_bbox(old_bbox, new_bbox, alpha=0.7):
    """Smooth bounding box transition using exponential moving average"""
    # alpha: weight for new bbox (0-1), higher = more responsive
    return [
        int(alpha * new_bbox[0] + (1 - alpha) * old_bbox[0]),
        int(alpha * new_bbox[1] + (1 - alpha) * old_bbox[1]),
        int(alpha * new_bbox[2] + (1 - alpha) * old_bbox[2]),
        int(alpha * new_bbox[3] + (1 - alpha) * old_bbox[3])
    ]

def expand_bbox(bbox, frame_w, frame_h, expand_ratio=0.15):
    """Expand bounding box by a ratio to better cover object"""
    x, y, w, h = bbox
    
    # Calculate expansion
    expand_w = int(w * expand_ratio)
    expand_h = int(h * expand_ratio)
    
    # Apply expansion
    new_x = max(0, x - expand_w)
    new_y = max(0, y - expand_h)
    new_w = min(frame_w - new_x, w + 2 * expand_w)
    new_h = min(frame_h - new_y, h + 2 * expand_h)
    
    return [new_x, new_y, new_w, new_h]

def track_objects(detections, frame_w, frame_h):
    """Track objects across frames using IOU matching"""
    global tracked_objects, next_object_id, max_missing_frames
    
    if not detections:
        # ลด age ของ tracked objects ที่ไม่เจอ
        objects_to_remove = []
        for obj_id in tracked_objects:
            tracked_objects[obj_id]['missed'] += 1
            if tracked_objects[obj_id]['missed'] > max_missing_frames:
                objects_to_remove.append(obj_id)
        
        for obj_id in objects_to_remove:
            del tracked_objects[obj_id]
        
        return []
    
    matched_detections = []
    unmatched_detections = []
    matched_tracked = set()
    
    # Match detections to tracked objects using IOU
    for detection in detections:
        best_iou = 0.1  # ลดเหลือ 0.1 เพื่อให้ track ติดแน่นมาก
        best_match_id = None
        best_distance = float('inf')
        
        for obj_id, tracked_obj in tracked_objects.items():
            iou = calculate_iou(detection['bbox'], tracked_obj['bbox'])
            
            # คำนวณระยะห่างของศูนย์กลาง
            det_cx = detection['bbox'][0] + detection['bbox'][2] / 2
            det_cy = detection['bbox'][1] + detection['bbox'][3] / 2
            trk_cx = tracked_obj['bbox'][0] + tracked_obj['bbox'][2] / 2
            trk_cy = tracked_obj['bbox'][1] + tracked_obj['bbox'][3] / 2
            distance = np.sqrt((det_cx - trk_cx)**2 + (det_cy - trk_cy)**2)
            
            # ใช้ทั้ง IOU และระยะห่างในการตัดสินใจ
            if iou > best_iou or (iou > 0.05 and distance < best_distance):
                best_iou = iou
                best_distance = distance
                best_match_id = obj_id
        
        if best_match_id is not None:
            # Update tracked object with smooth transition
            old_bbox = tracked_objects[best_match_id]['bbox']
            new_bbox = detection['bbox']
            # ใช้ alpha ต่ำมากเพื่อให้ smooth และไม่กระตุก
            smoothed_bbox = smooth_bbox(old_bbox, new_bbox, alpha=0.5)
            
            tracked_objects[best_match_id]['bbox'] = smoothed_bbox
            tracked_objects[best_match_id]['depth'] = detection['avgDepth']
            tracked_objects[best_match_id]['age'] += 1
            tracked_objects[best_match_id]['missed'] = 0
            matched_tracked.add(best_match_id)
            
            # Add to result
            x, y, w, h = smoothed_bbox
            matched_detections.append({
                'id': best_match_id,
                'label': f'Object #{best_match_id}',
                'confidence': detection['confidence'],
                'x': int((x / frame_w) * 100),
                'y': int((y / frame_h) * 100),
                'width': int((w / frame_w) * 100),
                'height': int((h / frame_h) * 100),
                'bbox': smoothed_bbox,
                'avgDepth': detection['avgDepth'],
                'minDepth': detection['minDepth'],
                'tracked': True
            })
        else:
            unmatched_detections.append(detection)
    
    # Create new tracked objects for unmatched detections
    for detection in unmatched_detections:
        obj_id = next_object_id
        next_object_id += 1
        
        tracked_objects[obj_id] = {
            'bbox': detection['bbox'],
            'depth': detection['avgDepth'],
            'age': 1,
            'missed': 0
        }
        
        x, y, w, h = detection['bbox']
        matched_detections.append({
            'id': obj_id,
            'label': f'Object #{obj_id}',
            'confidence': detection['confidence'],
            'x': int((x / frame_w) * 100),
            'y': int((y / frame_h) * 100),
            'width': int((w / frame_w) * 100),
            'height': int((h / frame_h) * 100),
            'bbox': detection['bbox'],
            'avgDepth': detection['avgDepth'],
            'minDepth': detection['minDepth'],
            'tracked': True
        })
    
    # Remove old tracked objects that weren't matched
    objects_to_remove = []
    for obj_id in tracked_objects:
        if obj_id not in matched_tracked:
            tracked_objects[obj_id]['missed'] += 1
            if tracked_objects[obj_id]['missed'] > max_missing_frames:
                objects_to_remove.append(obj_id)
    
    for obj_id in objects_to_remove:
        del tracked_objects[obj_id]
    
    return matched_detections

def draw_dimension_lines(img, x, y, w, h, width_mm, height_mm, color=(0, 0, 255)):
    """
    วาดเส้นแสดงขนาดตามแนว (dimension lines) เหมือนในแบบวิศวกรรม
    - เส้นสีแดง + ตัวเลขขนาด (หรือสีที่กำหนด)
    """
    # สีและการตั้งค่า
    thickness = 2
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    font_thickness = 2
    
    # ระยะห่างจากกรอบ
    offset = 20
    arrow_len = 10
    
    # === WIDTH line (ด้านบน) ===
    # เส้นหลัก
    start_x = x
    end_x = x + w
    line_y = y - offset
    cv2.line(img, (start_x, line_y), (end_x, line_y), color, thickness)
    
    # ลูกศรซ้าย
    cv2.line(img, (start_x, line_y), (start_x + arrow_len, line_y - arrow_len//2), color, thickness)
    cv2.line(img, (start_x, line_y), (start_x + arrow_len, line_y + arrow_len//2), color, thickness)
    
    # ลูกศรขวา
    cv2.line(img, (end_x, line_y), (end_x - arrow_len, line_y - arrow_len//2), color, thickness)
    cv2.line(img, (end_x, line_y), (end_x - arrow_len, line_y + arrow_len//2), color, thickness)
    
    # เส้นเชื่อมจากกรอบ
    cv2.line(img, (start_x, y), (start_x, line_y), color, 1)
    cv2.line(img, (end_x, y), (end_x, line_y), color, 1)
    
    # ตัวเลข WIDTH
    text = f"{width_mm:.0f}"
    text_size = cv2.getTextSize(text, font, font_scale, font_thickness)[0]
    text_x = x + w // 2 - text_size[0] // 2
    text_y = line_y - 10
    cv2.putText(img, text, (text_x, text_y), font, font_scale, color, font_thickness)
    
    # === HEIGHT line (ด้านขวา) ===
    # เส้นหลัก
    start_y = y
    end_y = y + h
    line_x = x + w + offset
    cv2.line(img, (line_x, start_y), (line_x, end_y), color, thickness)
    
    # ลูกศรบน
    cv2.line(img, (line_x, start_y), (line_x - arrow_len//2, start_y + arrow_len), color, thickness)
    cv2.line(img, (line_x, start_y), (line_x + arrow_len//2, start_y + arrow_len), color, thickness)
    
    # ลูกศรล่าง
    cv2.line(img, (line_x, end_y), (line_x - arrow_len//2, end_y - arrow_len), color, thickness)
    cv2.line(img, (line_x, end_y), (line_x + arrow_len//2, end_y - arrow_len), color, thickness)
    
    # เส้นเชื่อมจากกรอบ
    cv2.line(img, (x + w, start_y), (line_x, start_y), color, 1)
    cv2.line(img, (x + w, end_y), (line_x, end_y), color, 1)
    
    # ตัวเลข HEIGHT
    text = f"{height_mm:.0f}"
    text_size = cv2.getTextSize(text, font, font_scale, font_thickness)[0]
    text_x = line_x + 10
    text_y = y + h // 2 + text_size[1] // 2
    cv2.putText(img, text, (text_x, text_y), font, font_scale, color, font_thickness)

def detect_objects():
    """
    DETECTION: Contour-based detection only
    
    โหมด:
    1. Contour Detection (contour_detection_active) - แยกพื้นหลังสีขาว
    2. Depth-based fallback - ใช้ความลึก
    """
    global latest_depth, latest_frame, camera_active, contour_detection_active
    
    # Debug: Log state periodically (every 30 calls)
    if not hasattr(detect_objects, 'call_count'):
        detect_objects.call_count = 0
    detect_objects.call_count += 1
    
    try:
        # Check camera is active
        if not camera_active or oak_device is None:
            if detect_objects.call_count % 30 == 0:
                print(f"[DETECTION SKIP] camera_active={camera_active}")
            return []
        
        # Get frames
        with frame_lock:
            if latest_depth is None or latest_frame is None:
                return []
            depth = latest_depth.copy()
            frame = latest_frame.copy()
        
        # === MODE 1: CONTOUR DETECTION ===
        if contour_detection_active:
            if detect_objects.call_count % 30 == 0:
                print(f"[DETECTION] Contour mode active - calling detect_by_contour()")
            return detect_by_contour(frame, depth)
        
        # No detection mode active
        if detect_objects.call_count % 30 == 0:
            print(f"[DETECTION] No detection mode active - contour={contour_detection_active}")
        return []
        
    except Exception as e:
        print(f" detect_objects: {e}")
        return []

def detect_by_contour_zones(frame, depth):
    """ตรวจจับวัตถุใน 3 zones แยกกัน - 1 วัตถุต่อ 1 zone"""
    global latest_contour_mask
    
    try:
        frame_h, frame_w = frame.shape[:2]
        depth_mm = depth.astype(np.float32)
        if depth.shape[:2] != frame.shape[:2]:
            depth_mm = cv2.resize(depth_mm, (frame_w, frame_h), interpolation=cv2.INTER_NEAREST)
        
        # 🎯 แบ่ง frame เป็น 3 zones แนวนอน (ซ้าย-กลาง-ขวา)
        zone_width = frame_w // 3
        zones = [
            {'id': 1, 'name': 'Zone 1', 'x': 0, 'w': zone_width},
            {'id': 2, 'name': 'Zone 2', 'x': zone_width, 'w': zone_width},
            {'id': 3, 'name': 'Zone 3', 'x': zone_width * 2, 'w': frame_w - (zone_width * 2)}
        ]
        
        all_objects = []
        
        # ตรวจจับวัตถุในแต่ละ zone แยกกัน
        for zone in zones:
            zone_x = zone['x']
            zone_w = zone['w']
            
            # ตัด frame และ depth สำหรับ zone นี้
            zone_frame = frame[:, zone_x:zone_x+zone_w]
            zone_depth = depth_mm[:, zone_x:zone_x+zone_w]
            
            # ตรวจจับวัตถุใน zone นี้
            zone_objects = detect_in_single_zone(zone_frame, zone_depth, zone)
            
            if zone_objects:
                # ปรับ bbox coordinates กลับไปที่ full frame
                for obj in zone_objects:
                    x, y, w, h = obj['bbox']
                    original_bbox = obj['bbox'].copy()
                    obj['bbox'] = [x + zone_x, y, w, h]  # เพิ่ม offset x
                    obj['zone_id'] = zone['id']
                    obj['zone_name'] = zone['name']
                    print(f"  [DEBUG] {zone['name']}: bbox before={original_bbox}, after={obj['bbox']}")
                
                all_objects.extend(zone_objects)
        
        print(f"[3-ZONE] Detected {len(all_objects)} objects across 3 zones")
        for obj in all_objects:
            print(f"  [DEBUG] Final object bbox={obj['bbox']}, zone={obj.get('zone_name', 'N/A')}")
        return all_objects
        
    except Exception as e:
        print(f"❌ detect_by_contour_zones: {e}")
        return []

def detect_in_single_zone(zone_frame, zone_depth, zone_info):
    """ตรวจจับวัตถุ 1 ชิ้นใน zone เดียว"""
    try:
        zone_h, zone_w = zone_frame.shape[:2]
        
        # === STEP 1: Convert to grayscale ===
        gray = cv2.cvtColor(zone_frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # === STEP 2: โฟกัสที่วัตถุ (Rubber type dependent) ===
        global rubber_type
        if rubber_type == "white":
            # ยางขาว: พื้นดำ วัตถุขาว (หาพิกเซลสว่าง)
            _, binary_dark = cv2.threshold(blurred, 190, 255, cv2.THRESH_BINARY)
        else:
            # ยางดำ (default): พื้นขาว วัตถุดำ (หาพิกเซลมืด)
            _, binary_dark = cv2.threshold(blurred, 65, 255, cv2.THRESH_BINARY_INV)
        
        # === STEP 3: HSV - เพิ่มวัตถุที่มีสี ===
        hsv = cv2.cvtColor(zone_frame, cv2.COLOR_BGR2HSV)
        h_channel, s_channel, v_channel = cv2.split(hsv)
        
        _, saturation_mask = cv2.threshold(s_channel, 15, 255, cv2.THRESH_BINARY)
        if rubber_type == "white":
            # ยางขาว: หา value สูง (สว่าง)
            _, value_mask = cv2.threshold(v_channel, 200, 255, cv2.THRESH_BINARY)
        else:
            # ยางดำ: หา value ต่ำ (มืด)
            _, value_mask = cv2.threshold(v_channel, 240, 255, cv2.THRESH_BINARY_INV)
        hsv_combined = cv2.bitwise_and(saturation_mask, value_mask)
        
        # === STEP 4: รวม masks ===
        combined_mask = cv2.bitwise_or(binary_dark, hsv_combined)
        
        # === STEP 5: Morphology ===
        kernel_tiny = np.ones((2, 2), np.uint8)
        binary_morphed = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel_tiny, iterations=1)
        binary_final = binary_morphed
        
        # === STEP 6: Find contours ===
        contours, _ = cv2.findContours(binary_final, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        print(f"  [{zone_info['name']}] Found {len(contours)} contours")
        
        objects = []
        min_area = 50   # ✅ ลดเป็น 50 เพื่อรองรับวัตถุเล็กถึง 3x3mm
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            if area < min_area:
                if i < 3:
                    print(f"    Contour {i}: area={area:.0f} < {min_area} (SKIP)")
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            print(f"    Contour {i}: area={area:.0f}, bbox=[{x},{y},{w},{h}]")
            
            # Filter ขนาดขั้นต่ำ (≈3mm)
            if w < 5 or h < 5:
                print(f"      -> SKIP: size too small ({w}x{h})")
                continue
            
            # Aspect Ratio
            aspect_ratio = float(w) / h if h > 0 else 0
            if aspect_ratio < 0.1 or aspect_ratio > 10:
                print(f"      -> SKIP: bad aspect ratio {aspect_ratio:.2f}")
                continue
            
            # Valid Depth Check
            roi_depth = zone_depth[y:y+h, x:x+w]
            valid_depth = roi_depth[(roi_depth > 300) & (roi_depth < 2500)]
            
            valid_depth_ratio = len(valid_depth) / (w * h) if (w * h) > 0 else 0
            if valid_depth_ratio < 0.03:
                print(f"      -> SKIP: not enough valid depth {valid_depth_ratio*100:.1f}%")
                continue
            
            avg_depth = float(np.median(valid_depth)) if len(valid_depth) > 10 else 0
            
            # คำนวณขนาด physical size
            HFOV = 69
            focal_length_px = (zone_w / 2) / np.tan(np.radians(HFOV / 2))
            
            if avg_depth > 0:
                width_mm = (w * avg_depth) / focal_length_px
                height_mm = (h * avg_depth) / focal_length_px
            else:
                width_mm = 0
                height_mm = 0
            
            # คำนวณ Score
            area_score = (area / 10000) * 0.6
            center_x = x + w/2
            center_y = y + h/2
            zone_center_x = zone_w / 2
            zone_center_y = zone_h / 2
            distance_from_center = np.sqrt((center_x - zone_center_x)**2 + (center_y - zone_center_y)**2)
            max_distance = np.sqrt(zone_center_x**2 + zone_center_y**2)
            center_score = (1 - distance_from_center / max_distance) * 0.25
            depth_quality_score = valid_depth_ratio * 0.15
            score = area_score + center_score + depth_quality_score
            
            print(f"      -> ✅ VALID object: score={score:.3f}, size={width_mm:.1f}x{height_mm:.1f}mm")
            
            objects.append({
                'label': f'{zone_info["name"]}',
                'confidence': 0.95,
                'bbox': [int(x), int(y), int(w), int(h)],
                'depth_mm': avg_depth,
                'detection_method': 'zone_contour',
                'valid_depth_ratio': valid_depth_ratio,
                'valid_depth_pixels': len(valid_depth),
                'score': score,
                'width_mm': width_mm,
                'height_mm': height_mm
            })
        
        # เลือกวัตถุที่ดีที่สุด 1 ชิ้น ต่อ zone
        if len(objects) > 0:
            objects.sort(key=lambda obj: obj['score'], reverse=True)
            best_object = objects[0]
            print(f"  [{zone_info['name']}] ✅ Selected BEST: bbox={best_object['bbox']}, size={best_object['width_mm']:.1f}x{best_object['height_mm']:.1f}mm")
            return [best_object]
        
        print(f"  [{zone_info['name']}] ⚠️ No objects found (all filtered out)")
        return []
        
    except Exception as e:
        print(f"❌ detect_in_single_zone: {e}")
        return []

def apply_nms(objects, iou_threshold=0.4):
    """
    Non-Maximum Suppression: กำจัดกรอบซ้ำซ้อน
    เลือกกรอบที่มี score สูงที่สุดเมื่อ overlap เกิน threshold
    """
    if len(objects) == 0:
        return []
    
    # แปลง bbox เป็น numpy array
    boxes = np.array([obj['bbox'] for obj in objects])  # [x, y, w, h]
    scores = np.array([obj['score'] for obj in objects])
    
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 0] + boxes[:, 2]
    y2 = boxes[:, 1] + boxes[:, 3]
    areas = boxes[:, 2] * boxes[:, 3]
    
    # เรียงลำดับ score
    order = scores.argsort()[::-1]
    keep = []
    
    while order.size > 0:
        i = order[0]
        keep.append(i)
        
        # คำนวณ IoU กับกรอบอื่นทั้งหมด
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        intersection = w * h
        
        iou = intersection / (areas[i] + areas[order[1:]] - intersection)
        
        # เก็บกรอบที่ IoU < threshold
        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]
    
    return [objects[i] for i in keep]

# Contour thresholds sit right at the edge for small crumbs, so a piece found in
# one frame can be missed in the next and its box blinks. Remember what was
# detected recently and re-emit anything the current frame lost, so every piece
# stays boxed at the same time instead of taking turns.
DETECTION_MEMORY_FRAMES = 6
_detection_memory = []  # [{'obj': detection, 'ttl': frames_remaining}]


def clear_detection_memory():
    """Forget remembered detections (camera/contour stopped, scene changed)."""
    global _detection_memory
    _detection_memory = []


def merge_with_recent_detections(objects):
    """Add back objects seen in the last few frames but missed in this one."""
    global _detection_memory

    merged = list(objects)
    remembered = []

    for entry in _detection_memory:
        if any(calculate_iou(entry['obj']['bbox'], obj['bbox']) > 0.2 for obj in objects):
            continue  # found again this frame - the fresh detection wins
        entry['ttl'] -= 1
        if entry['ttl'] > 0:
            merged.append(entry['obj'])
            remembered.append(entry)

    for obj in objects:
        remembered.append({'obj': obj, 'ttl': DETECTION_MEMORY_FRAMES})

    _detection_memory = remembered
    return merged


def detect_by_contour(frame, depth):
    """ตรวจจับด้วย Contour (แยกพื้นหลังสีขาว) - พร้อม 8-layer visualization"""
    global latest_contour_mask, three_zone_detection_active
    
    # 🎯 NOTE: ไม่ redirect ไป detect_by_contour_zones อีกต่อไป
    # ให้ตรวจจับวัตถุปกติ แล้วกรองตาม zone ภายหลัง
    
    try:
        frame_h, frame_w = frame.shape[:2]
        depth_mm = depth.astype(np.float32)
        if depth.shape[:2] != frame.shape[:2]:
            depth_mm = cv2.resize(depth_mm, (frame_w, frame_h), interpolation=cv2.INTER_NEAREST)
        
        # === STEP 1: Convert to grayscale ===
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # === STEP 2: Canny edge detection ===
        edges = cv2.Canny(blurred, 30, 100)
        
        # === STEP 3: Threshold สำหรับวัตถุ (Rubber type dependent) ===
        global rubber_type
        if rubber_type == "white":
            # ยางขาว: พื้นดำ วัตถุขาว (หาพิกเซลสว่าง)
            _, binary_dark = cv2.threshold(blurred, 190, 255, cv2.THRESH_BINARY)
        else:
            # ยางดำ (default): พื้นขาว วัตถุดำ (หาพิกเซลมืด)
            _, binary_dark = cv2.threshold(blurred, 65, 255, cv2.THRESH_BINARY_INV)
        
        # === STEP 4: HSV - เพิ่มวัตถุที่มีสี ===
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h_channel, s_channel, v_channel = cv2.split(hsv)
        
        # วัตถุมีสี (Saturation > 15)
        _, saturation_mask = cv2.threshold(s_channel, 15, 255, cv2.THRESH_BINARY)
        if rubber_type == "white":
            # ยางขาว: หา value สูง (สว่าง)
            _, value_mask = cv2.threshold(v_channel, 200, 255, cv2.THRESH_BINARY)
        else:
            # ยางดำ: หา value ต่ำ (มืด)
            _, value_mask = cv2.threshold(v_channel, 240, 255, cv2.THRESH_BINARY_INV)
        hsv_combined = cv2.bitwise_and(saturation_mask, value_mask)

        # === STEP 4.5: Background deviation (catches both polarities) ===
        # The fixed threshold only sees one direction - "black rubber" mode needs
        # gray < 65, so a pale crumb lying on a grey tray, obvious to the eye,
        # produced no contour at all. Measure how far each pixel sits from the
        # background level instead: anything standing out either way is an object.
        background = np.full_like(blurred, int(np.median(blurred)))
        background_noise = float(np.median(cv2.absdiff(blurred, background)))
        deviation_cut = max(18.0, background_noise * 4.0)
        # Brighter than the tray only. A shadow darkens the tray by a little,
        # which is exactly what a two-sided mask picks up - that is how two
        # shadows turned nine crumbs into eleven detections. Genuinely dark
        # rubber is still caught by the absolute threshold above, which a
        # shadow never reaches.
        brighter_than_background = cv2.subtract(blurred, background)
        _, binary_deviation = cv2.threshold(brighter_than_background, deviation_cut, 255, cv2.THRESH_BINARY)

        # === STEP 5: รวม threshold ตายตัวกับ deviation ===
        combined_mask = cv2.bitwise_or(binary_dark, binary_deviation)
        
        # === STEP 6: Morphology - เชื่อมวัตถุที่เป็นชิ้นเดียวกัน ===
        # ✅ เพิ่ม kernel size และ iterations เพื่อเชื่อมส่วนของวัตถุเดียวกันให้ดีขึ้น
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))  # เพิ่มจาก 3x3 → 5x5
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        
        # CLOSE: เชื่อมช่องว่างเล็กๆ ภายในวัตถุ (เพิ่ม iterations 1→3)
        binary_morphed = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel_close, iterations=3)
        # OPEN: ลบ noise เล็กๆ (ลด iterations 2→1)
        binary_morphed = cv2.morphologyEx(binary_morphed, cv2.MORPH_OPEN, kernel_open, iterations=1)
        
        # ❌ ลบ erode ออก - เพราะทำให้วัตถุชิ้นเดียวแยกเป็นหลายชิ้น
        
        binary_final = binary_morphed
        
        # === STEP 7: Find contours ===
        contours, _ = cv2.findContours(binary_final, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # === CREATE VISUALIZATION - เปิดกลับมา ===
        create_visualization = True  # ✅ เปิดเพื่อแสดงผล
        
        if create_visualization:
            # สร้าง visualization layers
            layer1 = cv2.resize(frame, (240, 180))  # Original
            layer2 = cv2.resize(cv2.cvtColor(blurred, cv2.COLOR_GRAY2BGR), (240, 180))  # Blurred
            layer3 = cv2.resize(cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR), (240, 180))  # Edges
            layer4 = cv2.resize(cv2.applyColorMap(binary_dark, cv2.COLORMAP_HOT), (240, 180))  # Dark
            layer5 = cv2.resize(cv2.applyColorMap(binary_deviation, cv2.COLORMAP_HOT), (240, 180))  # Deviation
            layer6 = cv2.resize(cv2.applyColorMap(combined_mask, cv2.COLORMAP_HOT), (240, 180))  # Combined
            layer7 = cv2.resize(cv2.applyColorMap(binary_morphed, cv2.COLORMAP_HOT), (240, 180))  # Morphology
            
            # Layer 8: Contours with bbox
            frame_small = cv2.resize(frame, (240, 180))
            layer8 = cv2.cvtColor(frame_small.copy(), cv2.COLOR_BGR2RGB)
        
        objects = []
        
        # ⭐ Contour detection thresholds (optimized for small objects down to 3mm)
        min_area = 50   # Minimum contour area in pixels (≈3mm x 3mm)
        max_area = frame_w * frame_h * 0.25  # Anything bigger is background
        min_size = 5    # Minimum width/height in pixels (≈3mm)
        # Stereo depth is unreliable on small dark crumbs - it drops to 0% valid
        # pixels on some frames for a piece the contour sees perfectly well, and
        # the piece would blink out. Size comes from the pixel calibration, not
        # from depth, so depth no longer decides whether an object exists.
        min_depth_ratio = 0.0
        print(f"[CONTOUR] Using thresholds: min_area={min_area}px, min_size={min_size}x{min_size}px")
        
        # ✅ DEBUG: Log total contours found
        print(f"[CONTOUR DEBUG] Found {len(contours)} raw contours")
        
        # วาดทุก contours เป็นสีเทาก่อน
        if create_visualization:
            # Scale contours to layer8 size
            scale_x = 240 / frame_w
            scale_y = 180 / frame_h
            scaled_contours = []
            for cnt in contours:
                scaled = cnt.astype(np.float32)
                scaled[:, 0, 0] *= scale_x
                scaled[:, 0, 1] *= scale_y
                scaled_contours.append(scaled.astype(np.int32))
            cv2.drawContours(layer8, scaled_contours, -1, (128, 128, 128), 1)
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            
            # Filter by minimum area
            if area < min_area:
                if i < 5:
                    print(f"  [SKIP] Contour {i}: area={area:.0f}px < {min_area}px")
                continue

            # A blob covering a quarter of the frame is the tray, a shadow or a
            # letterbox band - never a crumb.
            if area > max_area:
                if i < 5:
                    print(f"  [SKIP] Contour {i}: area={area:.0f}px > {max_area:.0f}px (background)")
                continue
            
            # ✅ ใช้ boundingRect โดยตรงกับ contour
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filter by minimum size
            if w < min_size or h < min_size:
                if i < 5:
                    print(f"  [SKIP] Contour {i}: size {w}x{h}px < {min_size}x{min_size}px")
                continue
                
            # Aspect Ratio check
            aspect_ratio = float(w) / h if h > 0 else 0
            if aspect_ratio < 0.05 or aspect_ratio > 20:
                if i < 5:
                    print(f"  [SKIP] Contour {i}: bad aspect ratio {aspect_ratio:.2f}")
                continue

            # A crumb is a compact lump; a shadow or a smear spreads out and
            # fills only part of its own convex hull.
            hull_area = cv2.contourArea(cv2.convexHull(contour))
            solidity = area / hull_area if hull_area > 0 else 0
            if solidity < 0.45:
                if i < 5:
                    print(f"  [SKIP] Contour {i}: diffuse shape, solidity {solidity:.2f} < 0.45")
                continue
            
            # === Valid Depth Check ===
            roi_depth = depth_mm[y:y+h, x:x+w]
            valid_depth = roi_depth[(roi_depth > 300) & (roi_depth < 2500)]
            
            valid_depth_ratio = len(valid_depth) / (w * h) if (w * h) > 0 else 0
            
            # Filter by valid depth ratio (disabled by default, see min_depth_ratio)
            if min_depth_ratio > 0 and valid_depth_ratio < min_depth_ratio:
                if i < 5:
                    print(f"  [SKIP] Contour {i}: not enough valid depth {valid_depth_ratio*100:.1f}% < {min_depth_ratio*100:.1f}%")
                continue

            avg_depth = float(np.median(valid_depth)) if len(valid_depth) > 10 else 0

            # ✅ ใช้ calibration factor ที่ calibrated มาแล้ว (ไม่ใช้ focal_length)
            # Depth is reported for information only - it must not gate the size,
            # otherwise a frame with no usable depth reports 0mm and the object
            # is thrown away by the size filter further down.
            width_mm = w * current_settings['calibration_width']
            height_mm = h * current_settings['calibration_height']
            print(f"  [PASS] Contour {i}: area={area:.0f}px, bbox={w}x{h}px, size={width_mm:.1f}x{height_mm:.1f}mm")
            
            # คำนวณ Score
            area_score = (area / 10000) * 0.6
            center_x = x + w/2
            center_y = y + h/2
            frame_center_x = frame_w / 2
            frame_center_y = frame_h / 2
            distance_from_center = np.sqrt((center_x - frame_center_x)**2 + (center_y - frame_center_y)**2)
            max_distance = np.sqrt(frame_center_x**2 + frame_center_y**2)
            center_score = (1 - distance_from_center / max_distance) * 0.25
            depth_quality_score = valid_depth_ratio * 0.15
            score = area_score + center_score + depth_quality_score
            
            objects.append({
                'label': f'Object_{i+1}',
                'confidence': 0.95,
                'bbox': [int(x), int(y), int(w), int(h)],
                'depth_mm': avg_depth,
                'detection_method': 'contour',
                'valid_depth_ratio': valid_depth_ratio,
                'valid_depth_pixels': len(valid_depth),
                'score': score,
                'width_mm': width_mm,
                'height_mm': height_mm
            })
        
        # === ✅ เลือกวัตถุตามโหมด: 3-Zone / หลายชิ้น / 1 ชิ้น ===
        global multi_object_detection_active, three_zone_detection_active
        
        if len(objects) > 0:
            # เรียงตาม score จากสูงไปต่ำ
            objects.sort(key=lambda obj: obj['score'], reverse=True)
            
            # === ใช้ NMS เพื่อกำจัดกรอบซ้ำซ้อน ===
            # ✅ เพิ่ม threshold จาก 0.05 → 0.3 เพื่อลดการแยกวัตถุที่เป็นชิ้นเดียวกัน
            objects = apply_nms(objects, iou_threshold=0.3)
            
            # ✅ กรองวัตถุที่อยู่ใกล้กันมากเกินไป (กำจัดกรอบซ้อนทับ)
            if len(objects) > 1:
                filtered_objects = []
                for i, obj1 in enumerate(objects):
                    x1, y1, w1, h1 = obj1['bbox']
                    cx1, cy1 = x1 + w1//2, y1 + h1//2
                    
                    is_duplicate = False
                    for j, obj2 in enumerate(filtered_objects):
                        x2, y2, w2, h2 = obj2['bbox']
                        cx2, cy2 = x2 + w2//2, y2 + h2//2
                        
                        # คำนวณระยะห่างระหว่างจุดศูนย์กลาง
                        distance = np.sqrt((cx1-cx2)**2 + (cy1-cy2)**2)
                        
                        # ถ้าวัตถุอยู่ใกล้กันมาก (< 15px ≈ 12mm) ถือว่าซ้ำกัน
                        if distance < 15:
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        filtered_objects.append(obj1)
                
                objects = filtered_objects
            
            # ⭐ กรองตาม area หลัง NMS - รับวัตถุเล็กที่มีขนาดเพียงพอ
            min_bbox_area = 50   # ✅ ลดเป็น 50 เพื่อรองรับวัตถุเล็กถึง 3x3mm
            objects = [obj for obj in objects if (obj['bbox'][2] * obj['bbox'][3]) > min_bbox_area]
            print(f"[AREA FILTER] After area filter (>{min_bbox_area}px): {len(objects)} objects remain")
            
            # ✅ DEBUG: แสดงขนาดของวัตถุทั้งหมดก่อนกรอง
            max_objects = current_settings.get('max_objects', 30)
            if len(objects) > 0:
                print(f"[DEBUG] Objects before size filtering (showing max {min(10, len(objects))}):")
                for i, obj in enumerate(objects[:10]):  # แสดงแค่ 10 อันแรก
                    print(f"  [{i}] width={obj.get('width_mm', 0):.1f}mm, height={obj.get('height_mm', 0):.1f}mm, "
                          f"bbox={obj['bbox']}, area={obj['bbox'][2]*obj['bbox'][3]:.0f}px")
            
            # ✅ กรองตามขนาดและเช็ค in_range: ใช้ area-based measurement
            # Objects รับเฉพาะที่มีขนาดเหมาะสม (>= 3mm)
            min_size = 3   # Minimum object size (width or height) in mm
            objects = [obj for obj in objects 
                      if obj.get('width_mm', 0) >= min_size or obj.get('height_mm', 0) >= min_size]
            
            # Set in_range based on area-based config (ใช้ใน pass/fail logic ที่ line 420)
            for obj in objects:
                obj['in_range'] = None  # Will be calculated by pass/fail logic
            
            print(f"[OBJECT FILTER] Filtered to {len(objects)} objects (>= {min_size}mm)")
            
            # 🎯 ถ้าเปิด 3-Zone mode: กรองวัตถุตาม zone
            if three_zone_detection_active:
                zone_width = frame_w // 3
                zones = [
                    {'id': 1, 'name': 'Zone 1', 'x_start': 0, 'x_end': zone_width},
                    {'id': 2, 'name': 'Zone 2', 'x_start': zone_width, 'x_end': zone_width * 2},
                    {'id': 3, 'name': 'Zone 3', 'x_start': zone_width * 2, 'x_end': frame_w}
                ]
                
                zone_objects = {1: None, 2: None, 3: None}
                
                # หาวัตถุที่ดีที่สุดในแต่ละ zone
                for zone in zones:
                    zone_filtered = []
                    for obj in objects:
                        x, y, w, h = obj['bbox']
                        center_x = x + w // 2
                        # เช็คว่าจุดกลางของวัตถุอยู่ใน zone ไหน
                        if zone['x_start'] <= center_x < zone['x_end']:
                            zone_filtered.append(obj)
                    
                    if zone_filtered:
                        # เลือกวัตถุที่ดีที่สุดใน zone นี้
                        best_in_zone = zone_filtered[0]
                        best_in_zone['zone_id'] = zone['id']
                        best_in_zone['zone_name'] = zone['name']
                        zone_objects[zone['id']] = best_in_zone
                
                # วาดกรอบทุก zone ที่มีวัตถุ
                selected_objects = []
                colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255)]  # เขียว, แดง, น้ำเงิน
                
                for zone_id in [1, 2, 3]:
                    obj = zone_objects[zone_id]
                    if obj:
                        x, y, w, h = obj['bbox']
                        width_mm = obj.get('width_mm', 0)
                        height_mm = obj.get('height_mm', 0)
                        color = colors[zone_id - 1]
                        
                        # ❌ ปิดการวาดบนภาพหลัก - ให้ frontend วาดเอง
                        # cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)
                        # if width_mm > 0 and height_mm > 0:
                        #     label = f"Zone{zone_id} W:{int(width_mm)} H:{int(height_mm)}"
                        #     (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                        #     # พื้นหลังสีดำด้านบนกรอบ
                        #     cv2.rectangle(frame, (x, y-label_h-10), (x+label_w+10, y), (0, 0, 0), -1)
                        #     cv2.putText(frame, label, (x+5, y-5), 
                        #                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                        
                        selected_objects.append(obj)
                
                objects = selected_objects
                print(f"[3-ZONE] ✅ Detected {len(selected_objects)} objects across zones")
                for obj in selected_objects:
                    x, y, w, h = obj['bbox']
                    print(f"  [{obj['zone_name']}] bbox={obj['bbox']}, size={obj['width_mm']:.1f}x{obj['height_mm']:.1f}mm")
            
            elif multi_object_detection_active:
                # โหมดหลายวัตถุ: เลือกตามจำนวนที่ตั้งค่าไว้ (default 30)
                max_objects = current_settings.get('max_objects', 30)
                selected_objects = objects[:max_objects]
                
                print(f"[MULTI MODE] Showing up to {max_objects} objects, selected {len(selected_objects)}")
                
                # วาดกรอบทุกวัตถุที่เลือกบน layer 8 + ภาพหลัก
                for idx, obj in enumerate(selected_objects):
                    x, y, w, h = obj['bbox']
                    width_mm = obj.get('width_mm', 0)
                    height_mm = obj.get('height_mm', 0)
                    
                    # สีแตกต่างกันสำหรับแต่ละวัตถุ
                    colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255)]
                    color = colors[idx % len(colors)]
                    
                    # วาดบน layer8
                    if create_visualization:
                        cv2.rectangle(layer8, (x, y), (x+w, y+h), color, 3)
                        cv2.putText(layer8, f'#{idx+1}', (x+5, y+25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                    
                    # ❌ ปิดการวาดบนภาพหลัก - ให้ frontend วาดเอง
                    # cv2.rectangle(frame, (x, y), (x+w, y+h), color, 3)
                    
                    # ❌ ปิดการวาด label ด้านบนกรอบ - ให้ frontend วาดเอง
                    if width_mm > 0 and height_mm > 0:
                        print(f"[DEBUG DRAW] Multi #{idx+1}: w={w}px, h={h}px, width_mm={width_mm:.1f}mm, height_mm={height_mm:.1f}mm")
                        # label = f"#{idx+1} W:{int(width_mm)} H:{int(height_mm)}"
                        # (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                        # # พื้นหลังสีดำด้านบนกรอบ
                        # cv2.rectangle(frame, (x, y-label_h-10), (x+label_w+10, y), (0, 0, 0), -1)
                        # cv2.putText(frame, label, (x+5, y-5), 
                        #            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                objects = merge_with_recent_detections(selected_objects)[:max_objects]
                if len(objects) > len(selected_objects):
                    print(f"[MULTI MODE] Restored {len(objects) - len(selected_objects)} object(s) missed in this frame")
                selected_objects = objects
                print(f"[CONTOUR MULTI] ✅ Selected {len(selected_objects)} objects (top {len(selected_objects)} by score)")
                for idx, obj in enumerate(selected_objects):
                    x, y, w, h = obj['bbox']
                    print(f"  [{idx+1}] area={w*h:.0f}px, depth={obj['depth_mm']:.0f}mm, "
                          f"score={obj['score']:.2f}, size={obj['width_mm']:.1f}x{obj['height_mm']:.1f}mm")
            else:
                # โหมดเดิม: เลือกแค่ 1 วัตถุที่ดีที่สุด
                best_object = objects[0]
                x, y, w, h = best_object['bbox']
                width_mm = best_object.get('width_mm', 0)
                height_mm = best_object.get('height_mm', 0)
                
                # วาดบน layer8
                if create_visualization:
                    cv2.rectangle(layer8, (x, y), (x+w, y+h), (0, 255, 0), 3)
                    cv2.putText(layer8, 'BEST', (x+5, y+25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
                # ❌ ปิดการวาดบนภาพหลัก - ให้ frontend วาดเอง
                # cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
                # if width_mm > 0 and height_mm > 0:
                #     print(f"[DEBUG DRAW] Single: w={w}px, h={h}px, width_mm={width_mm:.1f}mm, height_mm={height_mm:.1f}mm")
                #     label = f"W:{int(width_mm)} H:{int(height_mm)}"
                #     (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                #     # พื้นหลังสีดำด้านบนกรอบ
                #     cv2.rectangle(frame, (x, y-label_h-10), (x+label_w+10, y), (0, 0, 0), -1)
                #     cv2.putText(frame, label, (x+5, y-5), 
                #                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                objects = [best_object]
                
                print(f"[CONTOUR] ✅ Selected BEST: [{best_object['label']}] "
                      f"area={w*h:.0f}px, depth={best_object['depth_mm']:.0f}mm, "
                      f"score={best_object['score']:.2f}, size={width_mm:.1f}x{height_mm:.1f}mm")
                print(f"[CONTOUR DEBUG] Returning bbox={best_object['bbox']}")
        else:
            print(f"[CONTOUR] ⚠️ No objects detected (found {len(contours)} contours, all filtered out)")
        
        # ✅ เก็บ frame ที่วาดกรอบแล้วเพื่อส่งแสดงผล
        global latest_annotated_frame
        with frame_lock:
            latest_annotated_frame = frame.copy()
        
        # ✅ สร้าง visualization
        if create_visualization:
            # ใช้ frame ที่วาดกรอบแล้วสำหรับ layer1
            layer1 = cv2.resize(frame, (240, 180))
            # รวม 8 เลเยอร์เป็น 2 แถว x 4 คอลัมน์
            top_row = np.hstack([layer1, layer2, layer3, layer4])
            bottom_row = np.hstack([layer5, layer6, layer7, layer8])
            multi_layer_vis = np.vstack([top_row, bottom_row])
            
            # ใส่ label บนแต่ละเลเยอร์
            cv2.putText(multi_layer_vis, "1.Original", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(multi_layer_vis, "2.Blur", (250, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(multi_layer_vis, "3.Edges", (490, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(multi_layer_vis, "4.Dark", (730, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(multi_layer_vis, "5.Deviation", (10, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(multi_layer_vis, "6.Combined", (250, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(multi_layer_vis, "7.Morph", (490, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            cv2.putText(multi_layer_vis, "8.Contours", (730, 205), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # เก็บ multi-layer visualization เพื่อส่งไปแสดงผล
            with frame_lock:
                latest_contour_mask = multi_layer_vis.copy()
        else:
            with frame_lock:
                latest_contour_mask = None
        
        return objects
        
    except Exception as e:
        print(f" detect_by_contour: {e}")
        with frame_lock:
            latest_contour_mask = None
        return []

def detect_by_depth_fallback(frame, depth_mm):
    """Depth-based detection (เดิม)"""
    try:
        frame_h, frame_w = frame.shape[:2]
        
        # Depth preprocessing
        depth_smooth = cv2.medianBlur(depth_mm.astype(np.uint16), 5).astype(np.float32)
        
        # Depth mask - objects in range 500-1200mm
        depth_mask = np.zeros((frame_h, frame_w), dtype=np.uint8)
        depth_mask[(depth_smooth > 500) & (depth_smooth < 1200)] = 255
        
        # Edge detection from RGB
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edges = cv2.dilate(edges, np.ones((3,3), np.uint8), iterations=1)
        
        # Combine depth + edges
        combined_mask = cv2.bitwise_and(depth_mask, edges)
        
        # Morphology
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=3)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_DILATE, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detections = []
        min_area = 50   # ✅ ลดเป็น 50 เพื่อรองรับวัตถุเล็กถึง 3x3mm
        max_area = (frame_w * frame_h) * 0.35
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area or area > max_area:
                continue
            
            x, y, w, h = cv2.boundingRect(contour)
            if w < 5 or h < 5:  # ✅ ลดเป็น 5 pixels (≈3mm)
                continue
            
            aspect_ratio = float(w) / h if h > 0 else 0
            if aspect_ratio < 0.3 or aspect_ratio > 4:
                continue
            
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            if hull_area > 0:
                solidity = area / hull_area
                if solidity < 0.7:
                    continue
            
            # Depth validation
            roi_depth = depth_smooth[y:y+h, x:x+w]
            valid_roi_mask = (roi_depth > 500) & (roi_depth < 1200)
            valid_depth = roi_depth[valid_roi_mask]
            
            if len(valid_depth) < (w * h * 0.5):
                continue
            
            avg_depth = float(np.median(valid_depth))
            min_depth = float(np.min(valid_depth))
            std_depth = float(np.std(valid_depth))
            
            # Depth uniformity
            if std_depth > 50:
                continue
            
            # ขยายกรอบเพิ่ม 8%
            expand = 0.08
            expand_w = int(w * expand)
            expand_h = int(h * expand)
            x = max(0, x - expand_w)
            y = max(0, y - expand_h)
            w = min(frame_w - x, w + 2 * expand_w)
            h = min(frame_h - y, h + 2 * expand_h)
            
            # คำนวณ confidence
            coverage = len(valid_depth) / (w * h) if (w * h) > 0 else 0
            confidence = min(0.95, 0.75 + (coverage * 0.2))
            
            detection = {
                'label': 'Object',
                'confidence': float(confidence),
                'bbox': [int(x), int(y), int(w), int(h)],
                'avgDepth': avg_depth,
                'minDepth': min_depth
            }
            
            detections.append(detection)
        
        return detections
        
    except Exception as e:
        print(f"Error in detect_by_depth_fallback: {e}")
        return []

# API Routes

# ============================================
# Frontend Routes (Serve Admin Web Interface)
# ============================================

@app.route('/')
def serve_index():
    """Serve the main admin web interface"""
    index_path = os.path.join(app.static_folder, 'index.html')
    print(f"[Frontend] Serving index.html from: {index_path}")
    print(f"[Frontend] File exists: {os.path.exists(index_path)}")
    if os.path.exists(index_path):
        return send_from_directory(app.static_folder, 'index.html')
    else:
        return f"<h1>404 - Frontend files not found</h1><pre>Looking for: {index_path}</pre>", 404

@app.route('/<path:path>')
def serve_static_files(path):
    """Serve static files or fallback to index.html for Vue Router"""
    file_path = os.path.join(app.static_folder, path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return send_from_directory(app.static_folder, path)
    else:
        # Fallback to index.html for client-side routing
        index_path = os.path.join(app.static_folder, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, 'index.html')
        else:
            return f"<h1>404 - File not found</h1><pre>Looking for: {file_path}</pre>", 404

# ============================================
# Backend API Routes
# ============================================

camera_init_in_progress = False


def _camera_init_worker():
    """Initialize the OAK camera off the request thread.

    A PoE camera needs to boot and receive the pipeline firmware, which can
    take well over the browser's HTTP timeout. Doing it here keeps
    /api/camera/connect fast and lets the UI follow progress via status
    polling / Socket.IO instead of hanging on the request.
    """
    global camera_init_in_progress
    try:
        print("=== Starting camera initialization (background) ===")
        success = initialize_oak_camera()
        if success:
            print("=== Camera initialized successfully! ===")
            system_config.set('camera_active', 1, auto_save=True)
            socketio.emit('camera_state_changed', {'active': True, 'should_run': camera_should_run})
        else:
            print("=== Camera initialization failed! ===")
            system_config.set('camera_active', 0, auto_save=True)
            network_camera_ip = system_config.get('network_camera_ip', '').strip()
            fail_message = 'No OAK camera detected. Check USB/CSI connection and power.'
            if network_camera_ip:
                fail_message = f"Cannot connect to network camera at {network_camera_ip}. Verify IP/power/network."
            socketio.emit('camera_state_changed', {'active': False, 'should_run': camera_should_run, 'error': fail_message})
    except Exception as e:
        print(f"=== Camera init worker error: {e} ===")
        try:
            system_config.set('camera_active', 0, auto_save=True)
            socketio.emit('camera_state_changed', {'active': False, 'should_run': camera_should_run, 'error': str(e)})
        except Exception:
            pass
    finally:
        camera_init_in_progress = False


@app.route('/api/camera/connect', methods=['POST'])
def connect_camera():
    """Start connecting to the OAK camera (non-blocking)"""
    global camera_active, camera_should_run, camera_init_in_progress
    try:
        # User intends the camera to run: from now on the watchdog will keep it
        # alive / auto-reconnect it until disconnect is called.
        camera_should_run = True

        if camera_active and oak_device is not None:
            return jsonify({'success': True, 'message': 'Camera already connected'})

        if camera_init_in_progress:
            return jsonify({'success': True, 'message': 'Camera is initializing...', 'initializing': True})

        camera_init_in_progress = True
        threading.Thread(target=_camera_init_worker, daemon=True, name='camera-init').start()

        return jsonify({
            'success': True,
            'message': 'Camera is initializing...',
            'initializing': True
        })

    except Exception as e:
        camera_init_in_progress = False
        print(f"=== Camera connect error: {e} ===")
        system_config.set('camera_active', 0, auto_save=True)
        return jsonify({
            'success': False,
            'message': f"Camera connection error: {str(e)}",
            'camera_active': False,
            'connected': False,
            'hasDevice': False
        }), 200

@app.route('/api/camera/disconnect', methods=['POST'])
def disconnect_camera():
    """Disconnect from camera - MUST be called explicitly"""
    global camera_active, camera_should_run
    try:
        # User intends the camera OFF: stop the watchdog from reconnecting it.
        camera_should_run = False
        stop_oak_camera(user_initiated=True)
        camera_active = False

        # Save states to config
        system_config.update({
            'camera_active': 0
        }, auto_save=True)
        
        # Emit Socket.IO event for real-time sync
        socketio.emit('camera_state_changed', {'active': False, 'should_run': False})
        
        print("�� Camera explicitly stopped by user")
        return jsonify({
            'success': True,
            'message': 'Camera disconnected'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

def _camera_health():
    """Return a snapshot of camera health without raising.

    (is_connected, thread_alive, has_frames, frames_fresh, time_since_frame)
    """
    dev = oak_device
    try:
        is_connected = dev is not None and not dev.isClosed()
    except Exception:
        is_connected = False
    thread_alive = camera_thread.is_alive() if camera_thread else False
    has_frames = latest_frame is not None
    time_since_frame = time.time() - last_frame_time if last_frame_time else 999
    frames_fresh = time_since_frame < 45.0
    return is_connected, thread_alive, has_frames, frames_fresh, time_since_frame


def ensure_camera_recovery(reason="unknown", blocking=False):
    """Reopen the camera if it is unhealthy, without ever double-initializing.

    Safe to call from the watchdog, the status endpoint, or anywhere else:
    a single `recovery_lock` serializes all (re)initialization. Returns True if
    a recovery ran and left the device connected. Never raises.
    """
    global recovery_in_progress

    if not HAS_DEPTHAI or not camera_should_run:
        return False

    # Fresh frames prove the camera works, whatever the other signals say. The
    # thread handle in particular goes stale after a reconnect while the loop
    # keeps running, and acting on it reopened a device that was streaming fine
    # - the second open failed with X_LINK and took the healthy stream with it.
    is_connected, thread_alive, has_frames, _, time_since_frame = _camera_health()
    if has_frames and time_since_frame < CAMERA_FRAME_GRACE:
        return False
    if is_connected and thread_alive:
        return False

    # Non-blocking: if a recovery is already running, let it finish.
    acquired = recovery_lock.acquire(blocking=blocking)
    if not acquired:
        return False
    try:
        recovery_in_progress = True
        # Re-check under the lock (another thread may have just fixed it).
        is_connected, thread_alive, has_frames, _, time_since_frame = _camera_health()
        if has_frames and time_since_frame < CAMERA_FRAME_GRACE:
            return False
        if is_connected and thread_alive:
            return False
        print(f"[AUTO-RECOVERY] ♻️ Reconnecting camera (reason={reason})...")
        ok = initialize_oak_camera()
        if ok:
            print("[AUTO-RECOVERY] ✅ Camera reconnected")
        else:
            print("[AUTO-RECOVERY] ⚠️ Reconnect attempt failed, will retry")
        return bool(ok)
    except Exception as e:
        print(f"[AUTO-RECOVERY] ⚠️ Recovery error: {e}, will retry")
        return False
    finally:
        recovery_in_progress = False
        recovery_lock.release()


def _reinit_camera_serialized():
    """initialize_oak_camera() guarded so only one re-init can run at a time.

    The camera loop recovers on its own and the watchdog recovers too; when both
    fired together they opened the device twice and each init closed the other's
    connection, which looked exactly like a camera that keeps dropping.
    """
    if not recovery_lock.acquire(timeout=90):
        print("[CAMERA] ⏭️ Re-init already in progress - skipping duplicate")
        return False
    try:
        return initialize_oak_camera()
    finally:
        recovery_lock.release()


def frame_emitter():
    """Publish the newest frame payload to Socket.IO clients.

    Runs outside the camera thread on purpose: a slow client must never stall
    frame acquisition (see the note on `pending_frame_payload`). Only the latest
    payload is sent - stale frames are dropped rather than queued.
    """
    global pending_frame_payload
    print("[EMITTER] 📡 Frame emitter started")
    while True:
        try:
            frame_emit_event.wait(timeout=1.0)
            frame_emit_event.clear()
            with emit_lock:
                payload = pending_frame_payload
                pending_frame_payload = None
            if payload is None:
                continue
            socketio.emit('frame_update', payload)
        except Exception as e:
            print(f"[EMITTER] ⚠️ emit error: {e}")
            time.sleep(0.5)


def camera_watchdog():
    """Autonomous background thread that keeps the camera alive.

    Independent of any HTTP client: as long as the user intends the camera to
    run (`camera_should_run`), this checks health every few seconds and triggers
    a single, serialized recovery when the thread dies, the device drops, or
    frames go stale. This is what makes reconnection self-healing.
    """
    print("[WATCHDOG] 🐕 Camera watchdog started")
    while True:
        try:
            time.sleep(5)
            if not camera_should_run or not HAS_DEPTHAI:
                continue
            is_connected, thread_alive, has_frames, frames_fresh, tsf = _camera_health()
            # Frames still coming in? Then the camera is fine - never touch it.
            if has_frames and tsf < CAMERA_FRAME_GRACE:
                continue
            # Recover only on hard failures; let camera_loop ride out brief gaps.
            if (not thread_alive) or (not is_connected):
                reason = "thread_died" if not thread_alive else "device_down"
                ensure_camera_recovery(reason=reason, blocking=True)
        except Exception as e:
            print(f"[WATCHDOG] ⚠️ error: {e}")
            time.sleep(5)


@app.route('/api/camera/status', methods=['GET'])
def camera_status():
    """Report camera and contour detection status.

    Recovery itself is handled autonomously by the watchdog thread, so this
    endpoint only reports state (fast, never blocks, safe on any error).
    """
    try:
        is_connected, thread_alive, has_frames, frames_fresh, time_since_frame = _camera_health()

        return jsonify({
            'camera_active': camera_active,
            'active': camera_active,
            'connected': is_connected and frames_fresh,
            'thread_alive': thread_alive,
            'has_frames': has_frames,
            'frames_fresh': frames_fresh,
            'time_since_frame': time_since_frame if last_frame_time else None,
            'contour_detection_active': contour_detection_active,
            'rubber_type': rubber_type,
            'hasDevice': oak_device is not None,
            'should_run': camera_should_run,
            'recovering': recovery_in_progress,
            # kept for frontend backward-compatibility
            'recovery_triggered': recovery_in_progress,
            'recovery_success': is_connected and frames_fresh,
            'recovery_reason': None,
            # 🔄 Measurement session status (for Admin Web sync)
            'measurement_running': active_measurement_config is not None,
            'active_machine_id': active_machine_id,
            'active_machine_name': active_machine_name,
            'active_lot_id': active_lot_id,
            'active_lot_name': active_lot_name,
            'active_config': active_measurement_config
        })
    except Exception as e:
        # Never let the status poll 500 - the frontend relies on it.
        return jsonify({
            'camera_active': camera_active,
            'active': camera_active,
            'connected': False,
            'thread_alive': False,
            'has_frames': False,
            'frames_fresh': False,
            'hasDevice': oak_device is not None,
            'should_run': camera_should_run,
            'recovering': recovery_in_progress,
            'error': str(e)
        })

@app.route('/api/camera/ping', methods=['GET'])
def camera_ping():
    """Simple ping to check if backend is responsive"""
    return jsonify({'status': 'ok'})

@app.route('/api/cameras/list', methods=['GET'])
def list_cameras():
    """List all connected Luxonis (OAK) cameras"""
    if not HAS_DEPTHAI:
        return jsonify({'success': True, 'cameras': [], 'count': 0,
                        'message': 'depthai not available on this host'})
    try:
        import depthai as dai

        # Get all available devices
        devices = dai.Device.getAllAvailableDevices()
        
        camera_list = []
        for device_info in devices:
            camera_data = {
                'mxid': device_info.getMxId(),
                'name': device_info.name if hasattr(device_info, 'name') else 'OAK Camera',
                'state': device_info.state.name,
                'protocol': device_info.protocol.name,
                'platform': device_info.platform.name if hasattr(device_info, 'platform') else 'Unknown',
                'connected': device_info.state.name == 'BOOTLOADER' or device_info.state.name == 'UNBOOTED'
            }
            camera_list.append(camera_data)
        
        # Check if current device is in the list
        current_device_id = None
        if oak_device is not None and not oak_device.isClosed():
            try:
                current_device_id = oak_device.getMxId()
            except:
                pass
        
        return jsonify({
            'success': True,
            'cameras': camera_list,
            'count': len(camera_list),
            'current_device_id': current_device_id,
            'message': f'Found {len(camera_list)} Luxonis camera(s)'
        })
        
    except Exception as e:
        print(f"[CAMERAS LIST] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'cameras': [],
            'count': 0,
            'message': f'Error listing cameras: {str(e)}'
        }), 500

@app.route('/api/depth/measure-point', methods=['GET'])
def measure_depth_point():
    """Measure depth at a specific point/region for calibration and analysis"""
    global latest_depth, latest_frame, camera_active
    
    if not camera_active or latest_depth is None:
        return jsonify({
            'success': False,
            'message': 'Camera not active or no depth data available'
        }), 400
    
    try:
        with frame_lock:
            depth = latest_depth.copy()
            frame = latest_frame.copy() if latest_frame is not None else None
        
        # Get region parameter
        region = request.args.get('region', 'center')  # 'center', 'center-bottom', 'custom'
        
        h, w = depth.shape
        
        # Define ROI based on region
        if region == 'center':
            # Center 20% of frame (for measuring object top)
            roi_w = int(w * 0.2)
            roi_h = int(h * 0.2)
            roi_x = (w - roi_w) // 2
            roi_y = (h - roi_h) // 2
            roi_color = (255, 0, 0)  # Blue for object top
            roi_label = "OBJECT TOP"
        elif region == 'center-bottom':
            # Center-bottom 20% (for measuring ground/floor)
            roi_w = int(w * 0.2)
            roi_h = int(h * 0.15)
            roi_x = (w - roi_w) // 2
            roi_y = h - roi_h - int(h * 0.1)  # 10% from bottom
            roi_color = (0, 255, 0)  # Green for ground
            roi_label = "GROUND/FLOOR"
        else:
            # Default to center
            roi_w = int(w * 0.2)
            roi_h = int(h * 0.2)
            roi_x = (w - roi_w) // 2
            roi_y = (h - roi_h) // 2
            roi_color = (255, 255, 0)  # Cyan
            roi_label = "MEASUREMENT"
        
        # Extract ROI depth values
        roi_depth = depth[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w]
        
        # Filter valid depth values (300-3000mm)
        valid_mask = (roi_depth > 300) & (roi_depth < 3000)
        valid_depths = roi_depth[valid_mask]
        
        if len(valid_depths) < 10:
            return jsonify({
                'success': False,
                'message': 'Insufficient valid depth data in the selected region'
            }), 400
        
        # Calculate statistics
        min_depth = float(np.min(valid_depths))
        max_depth = float(np.max(valid_depths))
        avg_depth = float(np.mean(valid_depths))
        median_depth = float(np.median(valid_depths))
        std_depth = float(np.std(valid_depths))
        
        # Use median as the most reliable measurement (less affected by outliers)
        measured_distance = median_depth
        
        # Create visualization image if frame available
        visualization_image = None
        if frame is not None:
            vis_frame = frame.copy()
            
            # Draw ROI rectangle
            cv2.rectangle(vis_frame, (roi_x, roi_y), (roi_x + roi_w, roi_y + roi_h), roi_color, 3)
            
            # Draw label
            label_bg_height = 40
            cv2.rectangle(vis_frame, (roi_x, roi_y - label_bg_height), 
                         (roi_x + roi_w, roi_y), roi_color, -1)
            cv2.putText(vis_frame, roi_label, (roi_x + 5, roi_y - 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
            cv2.putText(vis_frame, f"{measured_distance:.1f} mm", (roi_x + 5, roi_y - 8), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            
            # Draw depth heatmap overlay on ROI
            roi_depth_normalized = np.clip((roi_depth - 300) / (3000 - 300) * 255, 0, 255).astype(np.uint8)
            roi_depth_colored = cv2.applyColorMap(roi_depth_normalized, cv2.COLORMAP_JET)
            
            # Blend with original frame in ROI area
            alpha = 0.4
            vis_frame[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w] = cv2.addWeighted(
                vis_frame[roi_y:roi_y+roi_h, roi_x:roi_x+roi_w], 1 - alpha,
                roi_depth_colored, alpha, 0
            )
            
            # Add statistics overlay
            stats_y = 30
            cv2.rectangle(vis_frame, (10, 10), (300, 150), (0, 0, 0), -1)
            cv2.rectangle(vis_frame, (10, 10), (300, 150), roi_color, 2)
            cv2.putText(vis_frame, f"Region: {roi_label}", (20, stats_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            cv2.putText(vis_frame, f"Distance: {measured_distance:.1f} mm", (20, stats_y + 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            cv2.putText(vis_frame, f"Range: {min_depth:.0f}-{max_depth:.0f} mm", (20, stats_y + 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(vis_frame, f"Std Dev: {std_depth:.1f} mm", (20, stats_y + 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            cv2.putText(vis_frame, f"Samples: {len(valid_depths)}", (20, stats_y + 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
            
            # Encode to base64
            _, buffer = cv2.imencode('.jpg', vis_frame, [cv2.IMWRITE_JPEG_QUALITY, 50])  # ✅ ลดเป็น 50%
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            visualization_image = f"data:image/jpeg;base64,{img_base64}"
        
        return jsonify({
            'success': True,
            'distance': measured_distance,
            'min_depth': min_depth,
            'max_depth': max_depth,
            'avg_depth': avg_depth,
            'median_depth': median_depth,
            'std_depth': std_depth,
            'sample_count': int(len(valid_depths)),
            'region': region,
            'roi': {
                'x': int(roi_x),
                'y': int(roi_y),
                'width': int(roi_w),
                'height': int(roi_h)
            },
            'visualization': visualization_image
        })
        
    except Exception as e:
        print(f"Error in measure_depth_point: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/camera/contour/start', methods=['POST'])
def start_contour_detection():
    """Start Contour Detection mode (Background Subtraction)"""
    global contour_detection_active
    try:
        print("="*60)
        print("[CONTOUR] Activating contour detection mode...")
        print(f"  Camera Active: {camera_active}")
        print("="*60)
        
        if not camera_active:
            return jsonify({
                'success': False,
                'message': 'Camera is not active. Please start the camera first.'
            }), 400
        
        contour_detection_active = True
        print(f" contour_detection_active = {contour_detection_active}")
        
        # 🔄 Broadcast contour state to sync UI
        socketio.emit('contour_state_changed', {
            'active': True,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': 'Contour detection mode activated',
            'mode': 'contour'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/camera/contour/stop', methods=['POST'])
def stop_contour_detection():
    """Stop Contour Detection mode"""
    global contour_detection_active, latest_contour_mask
    try:
        contour_detection_active = False
        clear_detection_memory()

        # Clear contour mask
        with frame_lock:
            latest_contour_mask = None
        
        # 🔄 Broadcast contour state to sync UI
        socketio.emit('contour_state_changed', {
            'active': False,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': 'Contour detection mode deactivated'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/camera/multi-object/toggle', methods=['POST'])
def toggle_multi_object_detection():
    """Toggle multi-object detection mode"""
    global multi_object_detection_active
    try:
        multi_object_detection_active = not multi_object_detection_active
        
        # 🔄 Broadcast state change
        socketio.emit('multi_object_state_changed', {
            'active': multi_object_detection_active,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'active': multi_object_detection_active,
            'message': f'Multi-object detection {"enabled" if multi_object_detection_active else "disabled"}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/camera/multi-object/start', methods=['POST'])
def start_multi_object_detection():
    """Start multi-object detection mode (for Desktop App measurement)"""
    global multi_object_detection_active
    try:
        multi_object_detection_active = True
        
        print("[MULTI-OBJECT] ✅ Multi-object detection mode activated")
        
        # 🔄 Broadcast state change
        socketio.emit('multi_object_state_changed', {
            'active': True,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'active': True,
            'message': 'Multi-object detection enabled'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/camera/multi-object/stop', methods=['POST'])
def stop_multi_object_detection():
    """Stop multi-object detection mode"""
    global multi_object_detection_active
    try:
        multi_object_detection_active = False
        
        print("[MULTI-OBJECT] ⏹️ Multi-object detection mode deactivated")
        
        # 🔄 Broadcast state change
        socketio.emit('multi_object_state_changed', {
            'active': False,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'active': False,
            'message': 'Multi-object detection disabled'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/camera/multi-object/status', methods=['GET'])
def get_multi_object_status():
    """Get multi-object detection status"""
    global multi_object_detection_active
    try:
        return jsonify({
            'success': True,
            'active': multi_object_detection_active
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/camera/three-zone/toggle', methods=['POST'])
def toggle_three_zone_detection():
    """Toggle 3-zone detection mode"""
    global three_zone_detection_active
    try:
        three_zone_detection_active = not three_zone_detection_active
        
        return jsonify({
            'success': True,
            'active': three_zone_detection_active,
            'message': f'3-Zone detection {"enabled" if three_zone_detection_active else "disabled"}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/camera/three-zone/status', methods=['GET'])
def get_three_zone_status():
    """Get 3-zone detection status"""
    global three_zone_detection_active
    try:
        return jsonify({
            'success': True,
            'active': three_zone_detection_active
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/camera/contour/mask', methods=['GET'])
def get_contour_mask():
    """Get contour visualization mask"""
    global latest_contour_mask
    try:
        with frame_lock:
            if latest_contour_mask is None:
                return jsonify({
                    'success': False,
                    'message': 'No contour mask available'
                }), 404
            
            mask = latest_contour_mask.copy()
        
        # Encode to JPEG
        _, buffer = cv2.imencode('.jpg', mask, [cv2.IMWRITE_JPEG_QUALITY, 50])  # ✅ ลดเป็น 50%
        mask_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'mask': mask_base64
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/measurement/current', methods=['GET'])
def get_current_measurement():
    """Get current frame and measurements with optional contrast and depth colorization"""
    global last_measurement_request_time
    
    # ✅ Request throttling - ป้องกัน request บ่อยเกินไป
    current_time = time.time()
    time_since_last_request = current_time - last_measurement_request_time
    
    if time_since_last_request < measurement_request_cooldown:
        # ส่ง cached response หรือ empty data เพื่อไม่ให้ overload
        return jsonify({
            'frame': {
                'image': None,
                'timestamp': datetime.now().isoformat()
            },
            'contrastFrame': None,
            'depthFrame': None,
            'measurements': {
                'width': 0,
                'height': 0,
                'depth': 0,
                'volume': 0,
                'hasObject': False
            },
            'allMeasurements': [],
            'detections': [],
            'throttled': True  # บอก frontend ว่าถูก throttle
        })
    
    last_measurement_request_time = current_time
    
    # If camera not active, return empty data instead of error
    if not camera_active:
        return jsonify({
            'frame': {
                'image': None,
                'timestamp': datetime.now().isoformat()
            },
            'contrastFrame': None,
            'depthFrame': None,
            'measurements': {
                'width': 0,
                'height': 0,
                'depth': 0,
                'volume': 0,
                'hasObject': False
            },
            'allMeasurements': [],
            'detections': []
        })
    
    try:
        # ✅ เพิ่ม timeout protection
        start_time = time.time()
        timeout_seconds = 5  # 5 วินาที
        
        # Get query parameters for image enhancement
        enable_contrast = request.args.get('contrast', 'false').lower() == 'true'
        depth_colorscheme = request.args.get('colorScheme', 'gray')  # gray, jet, rainbow, turbo, hot, cool
        
        # Get main frame (RGB with detections, no modifications)
        frame = get_camera_frame(enable_contrast=False, depth_colorscheme=depth_colorscheme)
        
        # ✅ Check timeout
        if time.time() - start_time > timeout_seconds:
            print(f"[TIMEOUT] get_camera_frame took too long")
            raise TimeoutError("Frame acquisition timeout")
        
        detections = detect_objects()
        
        # ✅ Check timeout
        if time.time() - start_time > timeout_seconds:
            print(f"[TIMEOUT] detect_objects took too long")
            raise TimeoutError("Detection timeout")
        
        # ⭐ MULTI-OBJECT / 3-ZONE: Measure all detected objects and include measurements in response
        all_measurements = []
        zone_measurements = {1: None, 2: None, 3: None}  # 🎯 แยกตาม zone
        selected_object_index = 0
        
        for idx, detection in enumerate(detections):
            if 'bbox' in detection:
                # ⭐ FIX: ใช้ width_mm และ height_mm จาก detection โดยตรง (คำนวณมาจาก detect_by_contour แล้ว)
                # ไม่ต้องเรียก measure_object() ซึ่งจะคำนวณใหม่และทำให้ค่าไม่ตรงกัน
                detection_width = detection.get('width_mm', 0)
                detection_height = detection.get('height_mm', 0)
                
                # สร้าง measurement จากข้อมูล detection
                measurement = {
                    'width': detection_width,
                    'height': detection_height,
                    'depth': 0.0,  # ไม่ใช้ depth
                    'volume': 0.0,
                    'hasObject': True
                }
                
                # ถ้ายังไม่มีค่า width_mm/height_mm ใน detection ให้คำนวณใหม่
                if detection_width == 0 or detection_height == 0:
                    print(f"[MEASURE] Detection #{idx+1} missing width_mm/height_mm, calculating...")
                    measurement = measure_object(detection['bbox'])
                    detection['width_mm'] = measurement.get('width', 0)
                    detection['height_mm'] = measurement.get('height', 0)
                else:
                    detection['width_mm'] = detection_width
                    detection['height_mm'] = detection_height
                
                # รวม detection info เข้ากับ measurement
                measurement['detection'] = detection
                measurement['object_index'] = idx
                measurement['label'] = detection.get('label', f'Object_{idx+1}')
                
                # ⭐ เพิ่มข้อมูล bbox สำหรับการวาดกรอบใน frontend
                measurement['bbox'] = detection['bbox']
                measurement['width_mm'] = detection['width_mm']
                measurement['height_mm'] = detection['height_mm']
                
                # 🎯 ถ้ามี zone_id ให้เก็บแยกตาม zone
                zone_id = detection.get('zone_id', None)
                if zone_id is not None:
                    measurement['zone_id'] = zone_id
                    measurement['zone_name'] = detection.get('zone_name', f'Zone {zone_id}')
                    zone_measurements[zone_id] = measurement
                
                all_measurements.append(measurement)
        
        # Get primary measurement (largest object or average)
        if all_measurements:
            primary_measurement = max(all_measurements, key=lambda m: m.get('volume', 0) if m.get('volume', 0) > 0 else m.get('width', 0) * m.get('height', 0))
            selected_object_index = primary_measurement.get('object_index', 0)
        else:
            # ✅ FIX: ไม่วัดถ้าไม่มีวัตถุ (ไม่ส่ง full frame)
            primary_measurement = {
                'width': 0,
                'height': 0,
                'depth': 0,
                'volume': 0,
                'hasObject': False
            }
            selected_object_index = -1  # No object selected
        
        # Get contrast preview if enabled
        contrast_frame = None
        if enable_contrast:
            contrast_frame = get_contrast_preview()
            print(f"[DEBUG] Contrast frame generated: {contrast_frame is not None}")
        
        # Get depth preview
        depth_frame = get_depth_preview(depth_colorscheme)
        print(f"[DEBUG] Depth frame generated: {depth_frame is not None}")
        
        return jsonify({
            'frame': {
                'image': frame,
                'timestamp': datetime.now().isoformat()
            },
            'contrastFrame': contrast_frame,
            'depthFrame': depth_frame,
            'measurements': primary_measurement,
            'allMeasurements': all_measurements,
            'zoneMeasurements': zone_measurements,  # 🎯 เพิ่ม zone measurements
            'detections': detections,
            'selectedObjectIndex': selected_object_index,
            'threeZoneMode': three_zone_detection_active  # 🎯 บอก frontend ว่าอยู่โหมด 3-zone หรือไม่
        })
    except Exception as e:
        print(f" get_current_measurement failed: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'frame': {
                'image': None,
                'timestamp': datetime.now().isoformat()
            },
            'contrastFrame': None,
            'depthFrame': None,
            'measurements': {
                'width': 0,
                'height': 0,
                'depth': 0,
                'volume': 0,
                'hasObject': False
            },
            'allMeasurements': [],
            'detections': [],
            'selectedObjectIndex': -1,
            'error': str(e)
        }), 500

@app.route('/api/camera/capture', methods=['POST'])
def capture_image():
    """Capture current camera frame and return as base64"""
    global latest_frame
    
    try:
        if latest_frame is None:
            return jsonify({
                'success': False,
                'message': 'No frame available. Please start camera first.'
            }), 400
        
        # Encode frame to base64
        _, buffer = cv2.imencode('.jpg', latest_frame)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        image_data = f'data:image/jpeg;base64,{image_base64}'
        
        return jsonify({
            'success': True,
            'image': image_data,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/measurement/snapshot', methods=['POST'])
def capture_snapshot():
    """Capture a measurement snapshot"""
    global measurement_history
    
    try:
        measurements = measure_object()
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'measurements': measurements
        }
        measurement_history.append(snapshot)
        
        return jsonify({
            'success': True,
            'measurement': measurements
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/measurement/reset', methods=['POST'])
def reset_measurements():
    """Reset measurement history"""
    global measurement_history
    measurement_history = []
    return jsonify({
        'success': True,
        'message': 'Measurements reset'
    })

@app.route('/api/measurement/start', methods=['POST'])
def start_desktop_measurement():
    """Start measurement session with selected machine and configuration"""
    global active_measurement_config, active_machine_id, active_machine_name, active_lot_id, active_lot_name, measurement_statistics, was_detecting
    
    try:
        data = request.get_json()
        machine_id = data.get('machine_id')
        config_id = data.get('config_id')  # Optional: for backward compatibility
        machine_name_req = data.get('machine_name', '')
        lot_id_req = data.get('lot_id', None)
        lot_name_req = data.get('lot_name', '')
        
        if not machine_id:
            return jsonify({
                'success': False,
                'error': 'Missing machine_id'
            }), 400
        
        selected_config = None
        
        # ✅ Try to get config from machine object (NEW architecture)
        try:
            machines_file = Path(BASE_PATH) / 'machines.json'
            if not machines_file.exists():
                machines_file = Path(BASE_PATH).parent / 'python_scripts' / 'machines.json'
            
            if machines_file.exists():
                with open(machines_file, 'r', encoding='utf-8') as f:
                    machines = json.load(f)
                
                # Find machine by ID
                machine = next((m for m in machines if m['id'] == machine_id), None)
                
                if machine and machine.get('config'):
                    # Machine has inline config - use it!
                    selected_config = machine['config']
                    # Add machine name if not provided
                    if not machine_name_req:
                        machine_name_req = machine.get('name', '')
                    print(f"[MEASUREMENT] Using inline config from machine {machine_id}")
        except Exception as e:
            print(f"[WARNING] Could not load machine config: {e}")
        
        # ❌ Fallback: Get config from configurations.json (OLD architecture)
        if not selected_config:
            if not config_id:
                return jsonify({
                    'success': False,
                    'error': 'Machine has no inline config and config_id not provided'
                }), 400
            
            # โหลด configuration จากไฟล์
            config_file = Path(BASE_PATH) / 'configurations.json'
            if not config_file.exists():
                # Fallback: try parent directory
                config_file = Path(BASE_PATH).parent / 'python_scripts' / 'configurations.json'
            if not config_file.exists():
                return jsonify({
                    'success': False,
                    'error': f'Configuration file not found (looked in {BASE_PATH})'
                }), 404
            
            with open(config_file, 'r', encoding='utf-8') as f:
                configurations = json.load(f)
            
            # หา configuration ที่ตรงกับ config_id
            for config in configurations:
                if config['id'] == config_id:
                    selected_config = config
                    break
            
            if not selected_config:
                return jsonify({
                    'success': False,
                    'error': f'Configuration {config_id} not found'
                }), 404
            
            print(f"[MEASUREMENT] Using config from configurations.json (config_id={config_id})")
        
        # เปิดใช้งาน configuration
        active_measurement_config = selected_config
        active_machine_id = machine_id
        active_machine_name = machine_name_req
        active_lot_id = lot_id_req
        active_lot_name = lot_name_req
        
        # 📊 Reset statistics เมื่อเริ่ม session ใหม่
        measurement_statistics = {
            'total': 0,
            'pass': 0,
            'fail': 0,
            'near_pass': 0
        }
        was_detecting = False  # Reset detection state for fresh event counting
        
        print(f"[MEASUREMENT] Session started - Machine: {machine_id}")
        print(f"[MEASUREMENT] Target: {selected_config.get('target_area_min', 'N/A')}-{selected_config.get('target_area_max', 'N/A')} mm²")
        
        # 🔄 Broadcast state change to all clients (Admin Web + Desktop App)
        socketio.emit('measurement_state_changed', {
            'running': True,
            'machine_id': machine_id,
            'machine_name': machine_name_req,
            'lot_id': lot_id_req,
            'lot_name': lot_name_req,
            'config': selected_config,
            'statistics': measurement_statistics.copy(),
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': 'Measurement session started',
            'machine_id': machine_id,
            'config': selected_config
        })
    
    except Exception as e:
        print(f"[ERROR] start_desktop_measurement: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/measurement/stop', methods=['POST'])
def stop_desktop_measurement():
    """Stop measurement session"""
    global active_measurement_config, active_machine_id, active_machine_name, active_lot_id, active_lot_name, measurement_statistics
    
    try:
        active_measurement_config = None
        active_machine_id = None
        active_machine_name = None
        active_lot_id = None
        active_lot_name = None
        
        # 📊 Reset statistics เมื่อหยุด session
        measurement_statistics = {
            'total': 0,
            'pass': 0,
            'fail': 0,
            'near_pass': 0
        }
        
        print(f"[MEASUREMENT] Session stopped")
        
        # 🔄 Broadcast state change to all clients (Admin Web + Desktop App)
        socketio.emit('measurement_state_changed', {
            'running': False,
            'machine_id': None,
            'config': None,
            'statistics': measurement_statistics.copy(),  # ส่งสถิติที่ reset แล้ว
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': 'Measurement session stopped'
        })
    
    except Exception as e:
        print(f"[ERROR] stop_desktop_measurement: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings"""
    return jsonify(current_settings)

@app.route('/api/settings/update', methods=['POST'])
def update_settings():
    """Update settings"""
    global current_settings
    try:
        new_settings = request.json
        current_settings.update(new_settings)
        return jsonify({
            'success': True,
            'settings': current_settings
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/calibration/start', methods=['POST'])
def start_calibration():
    """Start calibration process"""
    try:
        data = request.json
        reference_size = data.get('referenceSize', 100)
        
        # TODO: Implement actual calibration logic
        print(f"Starting calibration with reference size: {reference_size}mm")
        
        return jsonify({
            'success': True,
            'message': 'Calibration started'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/calibration/capture', methods=['POST'])
def capture_calibration():
    """Capture reference object for calibration"""
    global calibration_capture, latest_frame
    
    try:
        data = request.json
        reference_width = data.get('referenceWidth')
        reference_height = data.get('referenceHeight')
        
        if not reference_width or not reference_height:
            return jsonify({
                'success': False,
                'message': 'Missing reference dimensions'
            }), 400
        
        # Get current frame
        with frame_lock:
            if latest_frame is None:
                return jsonify({
                    'success': False,
                    'message': 'No camera frame available'
                }), 400
            
            frame = latest_frame.copy()
        
        # Simulate object detection and measurement
        # In real implementation, this would use actual depth data
        height, width = frame.shape[:2]
        
        # Simulate detected object bounds (center 30% of frame)
        center_x, center_y = width // 2, height // 2
        box_width, box_height = int(width * 0.3), int(height * 0.3)
        
        detected_width = box_width * 0.8  # Simulated pixel width
        detected_height = box_height * 0.8  # Simulated pixel height
        
        # Store calibration data
        calibration_capture = {
            'referenceWidth': reference_width,
            'referenceHeight': reference_height,
            'detectedWidth': detected_width,
            'detectedHeight': detected_height,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'message': 'Reference object captured',
            'data': {
                'detectedWidth': round(detected_width, 2),
                'detectedHeight': round(detected_height, 2)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/calibration/apply', methods=['POST'])
def apply_calibration():
    """Apply calibration factor"""
    global current_settings, calibration_capture
    
    try:
        if calibration_capture is None:
            return jsonify({
                'success': False,
                'message': 'No calibration data available'
            }), 400
        
        # Calculate calibration factors for width and height
        width_factor = calibration_capture['referenceWidth'] / calibration_capture['detectedWidth']
        height_factor = calibration_capture['referenceHeight'] / calibration_capture['detectedHeight']
        
        # Use average factor for uniform scaling
        calibration_factor = (width_factor + height_factor) / 2
        
        # Update settings
        current_settings['calibrationFactor'] = calibration_factor
        
        return jsonify({
            'success': True,
            'message': 'Calibration applied successfully',
            'calibrationFactor': round(calibration_factor, 4),
            'widthFactor': round(width_factor, 4),
            'heightFactor': round(height_factor, 4)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/calibration/set', methods=['POST'])
def set_calibration():
    """
    ตั้งค่า calibration โดยตรงจากขนาดจริงของวัตถุ
    Body: {
        "measured_width": 47.9,
        "measured_height": 120.0,
        "measured_depth": 64.1,
        "actual_width": 30,
        "actual_height": 35,
        "actual_depth": 25
    }
    """
    global current_settings
    
    try:
        data = request.json
        
        # คำนวณ calibration factors
        calib_width = data['actual_width'] / data['measured_width']
        calib_height = data['actual_height'] / data['measured_height']
        calib_depth = data['actual_depth'] / data['measured_depth']
        
        # อัพเดต settings
        current_settings['calibration_width'] = calib_width
        current_settings['calibration_height'] = calib_height
        current_settings['calibration_depth'] = calib_depth
        current_settings['calibration_enabled'] = False  # ✅ ปิด calibration
        current_settings['reference_object'] = {
            'width_mm': data['actual_width'],
            'height_mm': data['actual_height'],
            'depth_mm': data['actual_depth']
        }
        
        # Save to config
        system_config.update({
            'calibration_width': calib_width,
            'calibration_height': calib_height,
            'calibration_depth': calib_depth,
            'calibration_enabled': False  # ✅ ปิด calibration
        }, auto_save=True)
        
        print(f"[CALIBRATION] ✅ Calibration set:")
        print(f"  Width:  {data['measured_width']:.1f}mm → {data['actual_width']}mm (factor: {calib_width:.3f})")
        print(f"  Height: {data['measured_height']:.1f}mm → {data['actual_height']}mm (factor: {calib_height:.3f})")
        print(f"  Depth:  {data['measured_depth']:.1f}mm → {data['actual_depth']}mm (factor: {calib_depth:.3f})")
        
        return jsonify({
            'success': True,
            'message': 'Calibration applied successfully',
            'calibration_factors': {
                'width': round(calib_width, 4),
                'height': round(calib_height, 4),
                'depth': round(calib_depth, 4)
            }
        })
        
    except Exception as e:
        print(f"[CALIBRATION] ❌ Error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/calibration/preview', methods=['GET'])
def calibration_preview():
    """
    🎥 Real-time preview พร้อม ROI detection สำหรับ calibration
    ใช้ detect_objects() เดียวกับหน้าหลักเพื่อให้แสดงกรอบเหมือนกัน
    """
    global latest_frame
    
    try:
        with frame_lock:
            if latest_frame is None:
                # Return placeholder image
                placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(placeholder, "No Camera Feed", (180, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                _, buffer = cv2.imencode('.jpg', placeholder)
                return buffer.tobytes(), 200, {'Content-Type': 'image/jpeg'}
            
            frame = latest_frame.copy()
        
        # ⭐ ใช้ detect_objects() เดียวกับหน้าหลัก
        detections = detect_objects()
        
        # วาด ROI บนภาพเหมือนหน้าหลัก
        preview_frame = frame.copy()
        
        # วาดกรอบรอบวัตถุทั้งหมดที่ตรวจจับได้
        for idx, detection in enumerate(detections):
            if 'bbox' in detection:
                x, y, w, h = detection['bbox']
                
                # สีของกรอบ (แดงเหมือนหน้าหลัก)
                color = (0, 0, 255)  # สีแดง BGR
                
                # วาดกรอบ
                cv2.rectangle(preview_frame, (x, y), (x + w, y + h), color, 3)
                
                # ดึงข้อมูลขนาดจาก detection
                width_mm = detection.get('width_mm', 0)
                height_mm = detection.get('height_mm', 0)
                
                # Label แสดงขนาด
                label = f"{width_mm:.1f} x {height_mm:.1f} mm"
                
                # วาดพื้นหลังสำหรับ label
                (label_w, label_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(preview_frame, (x, y - label_h - 10), (x + label_w + 8, y), (0, 0, 255), -1)
                cv2.putText(preview_frame, label, (x + 4, y - 6), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
                # แสดงขนาด pixel ด้านล่างกรอบ
                pixel_label = f"{w}x{h}px"
                cv2.putText(preview_frame, pixel_label, (x, y + h + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                # แสดงขนาด pixel ด้านล่างกรอบ
                pixel_label = f"{w}x{h}px"
                cv2.putText(preview_frame, pixel_label, (x, y + h + 20), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        
        # แสดงจำนวนวัตถุที่ตรวจจับได้
        num_detected = len(detections)
        status_text = f"Detected: {num_detected} object(s)"
        status_color = (0, 255, 0) if num_detected >= 2 else (255, 165, 0)
        
        cv2.rectangle(preview_frame, (5, 5), (280, 45), (0, 0, 0), -1)
        cv2.putText(preview_frame, status_text, (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
        # Hint text ถ้าตรวจจับได้น้อยกว่า 2
        if num_detected < 2:
            hint = "Place 50x50mm & 20x20mm objects"
            cv2.putText(preview_frame, hint, (10, 65), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
        
        # Encode to JPEG
        _, buffer = cv2.imencode('.jpg', preview_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        
        return buffer.tobytes(), 200, {'Content-Type': 'image/jpeg'}
        
    except Exception as e:
        print(f"[CALIBRATION PREVIEW] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Return error image
        error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(error_frame, f"Error: {str(e)}", (50, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        _, buffer = cv2.imencode('.jpg', error_frame)
        return buffer.tobytes(), 200, {'Content-Type': 'image/jpeg'}

@app.route('/api/calibration/auto-detect', methods=['POST'])
def auto_detect_calibration():
    """
    Auto-detect two reference objects (50x50mm and 20x20mm) and calculate calibration formula
    ใช้ detect_objects() เดียวกับหน้าหลักเพื่อความสอดคล้อง
    """
    global latest_frame, current_settings
    
    try:
        # Get current frame
        with frame_lock:
            if latest_frame is None:
                return jsonify({
                    'success': False,
                    'message': 'No camera frame available'
                }), 400
            
            frame = latest_frame.copy()
        
        # ⭐ ใช้ detect_objects() เดียวกับหน้าหลัก
        detections = detect_objects()
        
        # ต้องมีอย่างน้อย 2 วัตถุ
        if len(detections) < 2:
            return jsonify({
                'success': False,
                'message': f'Only {len(detections)} object(s) detected. Please place both 50x50mm and 20x20mm reference objects.'
            }), 400
        
        # เรียงตามขนาดพื้นที่ (ใหญ่ที่สุดก่อน)
        sorted_detections = sorted(detections, key=lambda d: d.get('width_mm', 0) * d.get('height_mm', 0), reverse=True)
        
        # เอา 2 ตัวใหญ่สุด
        large_det = sorted_detections[0]
        small_det = sorted_detections[1]
        
        # ดึงข้อมูล
        large_bbox = large_det['bbox']
        small_bbox = small_det['bbox']
        
        large_w_px = large_bbox[2]
        large_h_px = large_bbox[3]
        small_w_px = small_bbox[2]
        small_h_px = small_bbox[3]
        
        # Reference sizes (mm)
        ref_large_mm = 50  # 50x50mm reference
        ref_small_mm = 20  # 20x20mm reference
        
        # Calculate calibration factors using two-point calibration
        # Formula: calibration_factor = (actual_size_1 - actual_size_2) / (pixel_size_1 - pixel_size_2)
        
        # Width calibration
        pixel_diff_w = large_w_px - small_w_px
        actual_diff_w = ref_large_mm - ref_small_mm
        calibration_width = actual_diff_w / pixel_diff_w if pixel_diff_w > 0 else 0
        
        # Height calibration
        pixel_diff_h = large_h_px - small_h_px
        actual_diff_h = ref_large_mm - ref_small_mm
        calibration_height = actual_diff_h / pixel_diff_h if pixel_diff_h > 0 else 0
        
        # Average calibration factor
        calibration_factor = (calibration_width + calibration_height) / 2
        
        # Calculate formula string
        formula_width = f"Width(mm) = Width(px) × {calibration_width:.4f}"
        formula_height = f"Height(mm) = Height(px) × {calibration_height:.4f}"
        formula_avg = f"Size(mm) = Size(px) × {calibration_factor:.4f}"
        
        # Verify calibration by calculating expected sizes with NEW formula
        large_calculated_w = large_w_px * calibration_width
        large_calculated_h = large_h_px * calibration_height
        small_calculated_w = small_w_px * calibration_width
        small_calculated_h = small_h_px * calibration_height
        
        # Calculate accuracy
        large_error_w = abs(large_calculated_w - ref_large_mm) / ref_large_mm * 100
        large_error_h = abs(large_calculated_h - ref_large_mm) / ref_large_mm * 100
        small_error_w = abs(small_calculated_w - ref_small_mm) / ref_small_mm * 100
        small_error_h = abs(small_calculated_h - ref_small_mm) / ref_small_mm * 100
        
        avg_error = (large_error_w + large_error_h + small_error_w + small_error_h) / 4
        accuracy = max(0, 100 - avg_error)
        
        # 🎨 วาด ROI box รอบวัตถุที่ตรวจจับได้ พร้อมแสดงขนาดจาก NEW formula
        result_frame = frame.copy()
        
        # วาดกรอบวัตถุใหญ่ (50x50mm) - สีเขียว
        x, y, w, h = large_bbox
        cv2.rectangle(result_frame, (x, y), (x + w, y + h), (0, 255, 0), 3)
        
        label_top = f"NEW: {large_calculated_w:.1f}x{large_calculated_h:.1f}mm"
        (label_w, label_h), _ = cv2.getTextSize(label_top, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(result_frame, (x, y - label_h - 10), (x + label_w + 8, y), (0, 255, 0), -1)
        cv2.putText(result_frame, label_top, (x + 4, y - 6), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        label_bottom = f"Target: 50x50mm ({w}x{h}px)"
        cv2.putText(result_frame, label_bottom, (x, y + h + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # วาดกรอบวัตถุเล็ก (20x20mm) - สีฟ้า
        x, y, w, h = small_bbox
        cv2.rectangle(result_frame, (x, y), (x + w, y + h), (255, 200, 0), 3)
        
        label_top = f"NEW: {small_calculated_w:.1f}x{small_calculated_h:.1f}mm"
        (label_w, label_h), _ = cv2.getTextSize(label_top, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(result_frame, (x, y - label_h - 10), (x + label_w + 8, y), (255, 200, 0), -1)
        cv2.putText(result_frame, label_top, (x + 4, y - 6), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        label_bottom = f"Target: 20x20mm ({w}x{h}px)"
        cv2.putText(result_frame, label_bottom, (x, y + h + 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 200, 0), 2)
        
        # แปลงภาพเป็น base64 เพื่อส่งกลับไปแสดงผล
        _, buffer = cv2.imencode('.jpg', result_frame)
        result_image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        print(f"[AUTO-CALIBRATION] ✅ Detected 2 reference objects:")
        print(f"  Large (50x50mm): {large_w_px:.1f} × {large_h_px:.1f} px → NEW: {large_calculated_w:.1f} × {large_calculated_h:.1f} mm")
        print(f"  Small (20x20mm): {small_w_px:.1f} × {small_h_px:.1f} px → NEW: {small_calculated_w:.1f} × {small_calculated_h:.1f} mm")
        print(f"  Formula Width:  {formula_width}")
        print(f"  Formula Height: {formula_height}")
        print(f"  Accuracy: {accuracy:.2f}%")
        
        return jsonify({
            'success': True,
            'message': 'Auto-calibration successful',
            'data': {
                'calibration_width': round(calibration_width, 4),
                'calibration_height': round(calibration_height, 4),
                'calibration_factor': round(calibration_factor, 4),
                'formula_width': formula_width,
                'formula_height': formula_height,
                'formula_average': formula_avg,
                'accuracy': round(accuracy, 2),
                'result_image': result_image_base64,  # ภาพพร้อม ROI box และขนาดจาก NEW formula
                'detected_objects': {
                    'large': {
                        'width_px': round(large_w_px, 2),
                        'height_px': round(large_h_px, 2),
                        'width_mm': round(large_calculated_w, 2),
                        'height_mm': round(large_calculated_h, 2),
                        'reference': '50x50mm',
                        'bbox': large_bbox
                    },
                    'small': {
                        'width_px': round(small_w_px, 2),
                        'height_px': round(small_h_px, 2),
                        'width_mm': round(small_calculated_w, 2),
                        'height_mm': round(small_calculated_h, 2),
                        'reference': '20x20mm',
                        'bbox': small_bbox
                    }
                }
            }
        })
        
    except Exception as e:
        print(f"[AUTO-CALIBRATION] ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/calibration/save', methods=['POST'])
def save_calibration():
    """
    Save calibration factors to settings
    Body: {
        "calibration_width": 0.1234,
        "calibration_height": 0.5678,
        "calibration_factor": 0.3456
    }
    """
    global current_settings
    
    try:
        data = request.json
        
        calibration_width = data.get('calibration_width')
        calibration_height = data.get('calibration_height')
        calibration_factor = data.get('calibration_factor')
        
        if not all([calibration_width, calibration_height, calibration_factor]):
            return jsonify({
                'success': False,
                'message': 'Missing calibration parameters'
            }), 400
        
        # Update current settings
        current_settings['calibration_width'] = calibration_width
        current_settings['calibration_height'] = calibration_height
        current_settings['calibrationFactor'] = calibration_factor
        current_settings['calibration_enabled'] = True
        
        # Save to config file
        system_config.update({
            'calibration_width': calibration_width,
            'calibration_height': calibration_height,
            'calibrationFactor': calibration_factor,
            'calibration_enabled': True
        }, auto_save=True)
        
        print(f"[CALIBRATION] ✅ Calibration saved:")
        print(f"  Width Factor:  {calibration_width:.4f}")
        print(f"  Height Factor: {calibration_height:.4f}")
        print(f"  Avg Factor:    {calibration_factor:.4f}")
        
        return jsonify({
            'success': True,
            'message': 'Calibration saved successfully',
            'calibration': {
                'width': round(calibration_width, 4),
                'height': round(calibration_height, 4),
                'factor': round(calibration_factor, 4)
            }
        })
        
    except Exception as e:
        print(f"[CALIBRATION] ❌ Error saving: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/measurement/export', methods=['GET'])
def export_measurements():
    """Export measurement history"""
    try:
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'total_measurements': len(measurement_history),
            'measurements': measurement_history,
            'settings': current_settings
        }
        
        # Create JSON file in memory
        json_str = json.dumps(export_data, indent=2)
        buffer = io.BytesIO(json_str.encode())
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'measurements_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/camera/save-capture', methods=['POST'])
def save_capture():
    """Save captured image to captures folder"""
    try:
        data = request.json
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({
                'success': False,
                'message': 'No image data provided'
            })
        
        # Create captures directory
        captures_dir = Path('captures')
        captures_dir.mkdir(exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'capture_{timestamp}.jpg'
        filepath = captures_dir / filename
        
        # Decode base64 and save
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        img_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        cv2.imwrite(str(filepath), img)
        
        return jsonify({
            'success': True,
            'message': 'Image saved successfully',
            'filepath': str(filepath.absolute()),
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# ============================================================
# CONFIG MANAGEMENT APIs
# ============================================================

@app.route('/api/config/get', methods=['GET'])
def get_config():
    """Get all configuration"""
    return jsonify({
        'success': True,
        'config': system_config.get_all()
    })

@app.route('/api/config/set', methods=['POST'])
def set_config():
    """Update configuration"""
    try:
        data = request.json
        key = data.get('key')
        value = data.get('value')
        
        if not key:
            return jsonify({'success': False, 'message': 'Key is required'})
        
        system_config.set(key, value, auto_save=True)
        
        return jsonify({
            'success': True,
            'message': f'Updated {key} = {value}'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/config/update', methods=['POST'])
def update_config():
    """Update multiple configuration values"""
    try:
        data = request.json
        updates = data.get('updates', {})
        
        system_config.update(updates, auto_save=True)
        
        return jsonify({
            'success': True,
            'message': f'Updated {len(updates)} settings'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/config/reset', methods=['POST'])
def reset_config():
    """Reset configuration to defaults"""
    try:
        system_config.reset()
        return jsonify({
            'success': True,
            'message': 'Configuration reset to defaults'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ============================================================
# ZOOM CONTROL APIs
# ============================================================

@app.route('/api/camera/zoom', methods=['POST'])
def set_zoom():
    """Set camera zoom level - applies in realtime"""
    global current_zoom, oak_device, camera_active
    
    try:
        data = request.json
        zoom_level = float(data.get('zoom', 1.0))
        
        # Clamp zoom between 1.0 and 4.0
        zoom_level = max(1.0, min(4.0, zoom_level))
        current_zoom = zoom_level
        
        # Save to config
        system_config.set('zoom_level', zoom_level, auto_save=True)
        
        print(f"[Zoom] Setting zoom level: {zoom_level}x")
        
        # Apply zoom in realtime if camera is active
        if camera_active and oak_device is not None:
            try:
                # Send control command to camera
                ctrl = dai.CameraControl()
                ctrl.setManualFocus(128)  # Keep current focus
                
                # Set ISP scale for zoom (realtime control)
                numerator = int(zoom_level * 10)
                denominator = 10
                
                # Create input queue for camera control
                if hasattr(oak_device, 'getInputQueue'):
                    control_queue = oak_device.getInputQueue('control')
                    ctrl_packet = dai.ImgFrame()
                    control_queue.send(ctrl)
                
                print(f"[Zoom] ✅ Applied zoom {zoom_level}x in realtime")
                
                return jsonify({
                    'success': True,
                    'zoom': zoom_level,
                    'message': f'Zoom applied: {zoom_level}x',
                    'requires_restart': False
                })
            except Exception as e:
                print(f"[Zoom] ⚠️ Realtime zoom failed: {e}, will apply on next camera start")
                return jsonify({
                    'success': True,
                    'zoom': zoom_level,
                    'message': f'Zoom saved: {zoom_level}x (restart camera to apply)',
                    'requires_restart': True
                })
        else:
            return jsonify({
                'success': True,
                'zoom': zoom_level,
                'message': f'Zoom saved: {zoom_level}x (will apply when camera starts)',
                'requires_restart': False
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/camera/zoom', methods=['GET'])
def get_zoom():
    """Get current zoom level"""
    zoom = system_config.get('zoom_level', 1.0)
    return jsonify({
        'success': True,
        'zoom': zoom
    })


# ==================== RUBBER TYPE APIs ====================

@app.route('/api/rubber/type', methods=['GET'])
def get_rubber_type():
    """
    Get current rubber type setting
    Returns: black (dark on white background) or white (white on dark background)
    """
    return jsonify({
        'success': True,
        'rubber_type': rubber_type
    })

@app.route('/api/rubber/type', methods=['POST'])
def set_rubber_type():
    """
    Set rubber type (black or white)
    Body: { "rubber_type": "black" | "white" }
    """
    global rubber_type
    
    try:
        data = request.get_json()
        new_type = data.get('rubber_type', 'black')
        
        if new_type not in ['black', 'white']:
            return jsonify({
                'success': False,
                'message': 'Invalid rubber type. Must be "black" or "white"'
            }), 400
        
        rubber_type = new_type
        print(f"[RUBBER] Type changed to: {rubber_type}")
        
        # Save to system config
        system_config.set('rubber_type', rubber_type, auto_save=True)
        
        return jsonify({
            'success': True,
            'rubber_type': rubber_type,
            'message': f'Rubber type set to {rubber_type}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/rubber/toggle', methods=['POST'])
def toggle_rubber_type():
    """
    Toggle between black and white rubber types
    """
    global rubber_type
    
    try:
        # Toggle
        rubber_type = 'white' if rubber_type == 'black' else 'black'
        
        print(f"[RUBBER] Toggled to: {rubber_type}")
        
        # Save to system config
        system_config.set('rubber_type', rubber_type, auto_save=True)
        
        return jsonify({
            'success': True,
            'rubber_type': rubber_type,
            'message': f'Rubber type toggled to {rubber_type}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ==================== SETUP WIZARD APIs ====================

@app.route('/api/setup/check', methods=['GET'])
def check_setup_status():
    """ตรวจสอบว่าผ่านการ Setup แล้วหรือไม่"""
    try:
        setup_config_file = Path('setup_config.json')
        if setup_config_file.exists():
            with open(setup_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return jsonify({
                    'setupCompleted': config.get('setupCompleted', False),
                    'mode': config.get('mode', 'local'),
                    'serverUrl': config.get('serverUrl', '')
                })
        return jsonify({'setupCompleted': False, 'mode': 'local', 'serverUrl': ''})
    except Exception as e:
        print(f"Error checking setup status: {e}")
        return jsonify({'setupCompleted': False, 'mode': 'local', 'serverUrl': ''})

@app.route('/api/setup/save', methods=['POST'])
def save_setup_config():
    """บันทึกการตั้งค่า Setup Wizard"""
    try:
        data = request.json
        setup_config_file = Path('setup_config.json')
        
        config = {
            'setupCompleted': data.get('setupCompleted', True),
            'mode': data.get('mode', 'local'),
            'serverUrl': data.get('serverUrl', ''),
            'timestamp': str(datetime.now())
        }
        
        with open(setup_config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"[Setup] Configuration saved: mode={config['mode']}, serverUrl={config.get('serverUrl', 'N/A')}")
        
        return jsonify({'success': True, 'message': 'Setup configuration saved successfully'})
    except Exception as e:
        print(f"Error saving setup config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== DATABASE APIs ====================

@app.route('/api/database/config', methods=['GET'])
def get_database_config():
    """Get current database configuration"""
    try:
        config = db_config.config.copy()
        # Don't send password to frontend (security)
        if config.get('db_type') == 'sqlserver' and 'sqlserver' in config:
            if config['sqlserver'].get('password'):
                config['sqlserver']['password'] = '********'
        
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/database/config/update', methods=['POST'])
def update_database_config():
    """Update database configuration"""
    global db_service, measurement_session
    
    try:
        data = request.get_json()
        db_type = data.get('db_type', 'sqlite')
        
        # Validate based on database type
        if data.get('enabled', False):
            if db_type == 'sqlserver':
                sqlserver = data.get('sqlserver', {})
                required_fields = ['host', 'username', 'password', 'database']
                missing_fields = [f for f in required_fields if not sqlserver.get(f)]
                
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'message': f'Missing SQL Server fields: {", ".join(missing_fields)}'
                    }), 400
            elif db_type == 'sqlite':
                if not data.get('sqlite_path'):
                    return jsonify({
                        'success': False,
                        'message': 'SQLite database path is required'
                    }), 400
        
        # Update configuration
        success = db_config.update(**data)
        
        if not success:
            return jsonify({
                'success': False,
                'message': 'Failed to save configuration'
            }), 500
        
        # Reinitialize database service if enabled
        if data.get('enabled', False):
            db_service = DatabaseService(db_config)
            print(f"[Database] Configuration updated and enabled ({db_type})")
        else:
            db_service = None
            measurement_session = None
            print(f"[Database] Disabled")
        
        return jsonify({
            'success': True,
            'message': 'Database configuration updated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/database/test', methods=['POST'])
def test_database_connection():
    """Test database connection"""
    try:
        if not db_config.get('enabled', False):
            return jsonify({
                'success': False,
                'message': 'Database is not enabled'
            }), 400
        
        success, message = db_config.test_connection()
        
        return jsonify({
            'success': success,
            'message': message
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Connection test failed: {str(e)}'
        }), 500

@app.route('/api/database/session/start', methods=['POST'])
def start_measurement_session():
    """
    Start a new measurement session
    Body: {
        "object_name": "Contaminate_A",
        "lot": "LOT-001",
        "product_type": "TYPE-A",
        "max_triggers": 10  // optional, default from config
    }
    """
    global measurement_session, db_service
    
    try:
        if not db_config.get('enabled', False):
            return jsonify({
                'success': False,
                'message': 'Database is not enabled. Please enable and configure database in settings.'
            }), 400
        
        data = request.get_json()
        object_name = data.get('object_name')
        
        if not object_name:
            return jsonify({
                'success': False,
                'message': 'object_name is required'
            }), 400
        
        # Get max_triggers from request or config
        max_triggers = data.get('max_triggers')
        unlimited_mode = db_config.get('unlimited_mode', False)
        
        if unlimited_mode:
            max_triggers = 999999  # Large number for unlimited mode
        elif max_triggers is None:
            max_triggers = db_config.get('measurement_triggers', 10)
        
        # Initialize database service if not exists
        if db_service is None:
            db_service = DatabaseService(db_config)
        
        # Create new session
        measurement_session = MeasurementSession(max_triggers=max_triggers)
        session_id = measurement_session.start(object_name)
        
        # Store lot and product_type in config for later use
        db_config.config['lot'] = data.get('lot', '')
        db_config.config['product_type'] = data.get('product_type', '')
        db_config.config['session_active'] = True
        
        print(f"[Database] Session {session_id} started for '{object_name}' ({max_triggers} triggers)")
        
        return jsonify({
            'success': True,
            'message': f'Measurement session started',
            'session_id': session_id,
            'object_name': object_name,
            'max_triggers': max_triggers,
            'unlimited_mode': unlimited_mode
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/database/session/add', methods=['POST'])
def add_measurement_to_session():
    """
    Add a measurement to current session
    Body: {
        "object_name": "Contaminate_A",
        "size": 45.5  // in mm
    }
    """
    global measurement_session
    
    try:
        if measurement_session is None or not measurement_session.is_active:
            return jsonify({
                'success': False,
                'message': 'No active measurement session. Please start a session first.'
            }), 400
        
        data = request.get_json()
        object_name = data.get('object_name')
        size = data.get('size')
        
        if not object_name or size is None:
            return jsonify({
                'success': False,
                'message': 'object_name and size are required'
            }), 400
        
        # Add measurement to session
        result = measurement_session.add_measurement(object_name, float(size))
        
        if not result['success']:
            return jsonify(result), 400
        
        print(f"[Database] Measurement added: {object_name} = {size}mm ({result['current_count']}/{measurement_session.max_triggers})")
        
        # Auto-complete if reached max triggers
        if result['is_complete']:
            # Get maximum measurement
            max_data = measurement_session.complete()
            
            if max_data and db_service:
                # Prepare data for database
                db_data = {
                    'lot': db_config.config.get('lot', ''),
                    'product_type': db_config.config.get('product_type', ''),
                    'obj': max_data['obj'],
                    'size': max_data['size']
                }
                
                # Insert to database
                success, message = db_service.insert_measurement(db_data)
                
                if success:
                    print(f"[Database] ✅ Session completed and saved: {max_data['obj']} = {max_data['size']}mm (max of {max_data['measurement_count']} measurements)")
                    
                    # Reset session
                    measurement_session = None
                    db_config.config['session_active'] = False
                    
                    return jsonify({
                        'success': True,
                        'message': 'Session completed and data saved to database',
                        'is_complete': True,
                        'max_measurement': max_data,
                        'db_message': message
                    })
                else:
                    print(f"[Database] ❌ Failed to save: {message}")
                    return jsonify({
                        'success': False,
                        'message': f'Failed to save to database: {message}',
                        'max_measurement': max_data
                    }), 500
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/database/session/complete', methods=['POST'])
def complete_measurement_session():
    """
    Manually complete current session and save maximum value to database
    """
    global measurement_session, db_service
    
    try:
        if measurement_session is None or not measurement_session.is_active:
            return jsonify({
                'success': False,
                'message': 'No active measurement session'
            }), 400
        
        # Complete session
        max_data = measurement_session.complete()
        
        if not max_data:
            return jsonify({
                'success': False,
                'message': f'Insufficient measurements. Need at least {measurement_session.max_triggers} measurements.'
            }), 400
        
        # Save to database
        if db_service:
            db_data = {
                'lot': db_config.config.get('lot', ''),
                'product_type': db_config.config.get('product_type', ''),
                'obj': max_data['obj'],
                'size': max_data['size']
            }
            
            success, message = db_service.insert_measurement(db_data)
            
            if success:
                print(f"[Database] ✅ Manual completion: {max_data['obj']} = {max_data['size']}mm")
                
                # Reset session
                measurement_session = None
                db_config.config['session_active'] = False
                
                return jsonify({
                    'success': True,
                    'message': 'Session completed and data saved',
                    'max_measurement': max_data,
                    'db_message': message
                })
            else:
                return jsonify({
                    'success': False,
                    'message': f'Failed to save: {message}',
                    'max_measurement': max_data
                }), 500
        else:
            return jsonify({
                'success': False,
                'message': 'Database service not initialized'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/database/session/cancel', methods=['POST'])
def cancel_measurement_session():
    """Cancel current measurement session"""
    global measurement_session
    
    try:
        if measurement_session is None:
            return jsonify({
                'success': True,
                'message': 'No active session to cancel'
            })
        
        measurement_session.cancel()
        measurement_session = None
        db_config.config['session_active'] = False
        
        print(f"[Database] Session cancelled")
        
        return jsonify({
            'success': True,
            'message': 'Session cancelled'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/database/session/status', methods=['GET'])
def get_session_status():
    """Get current session status"""
    try:
        if measurement_session is None:
            return jsonify({
                'success': True,
                'active': False,
                'session': None
            })
        
        status = measurement_session.get_status()
        
        return jsonify({
            'success': True,
            'active': measurement_session.is_active,
            'session': status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ============================================================================
# Machine Management API Endpoints
# ============================================================================

@app.route('/api/machines', methods=['GET'])
def get_machines():
    """Get all machines from file (machines.json)"""
    try:
        machines = backend_extension.get_all_machines()
        
        return jsonify({
            'success': True,
            'machines': machines
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/machines', methods=['POST'])
def add_machine():
    """Add a new machine to file (machines.json)"""
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('id'):
            return jsonify({
                'success': False,
                'message': 'Machine ID is required'
            }), 400
        
        if not data.get('name'):
            return jsonify({
                'success': False,
                'message': 'Machine name is required'
            }), 400
        
        # Add machine using file-based storage
        success, message = backend_extension.add_machine(data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/machines/<machine_id>', methods=['PUT'])
def update_machine(machine_id):
    """Update machine information in file (machines.json)"""
    try:
        data = request.json
        
        # Update machine using file-based storage
        success, message = backend_extension.update_machine(machine_id, data)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/machines/<machine_id>', methods=['DELETE'])
def delete_machine(machine_id):
    """Delete a machine from file (machines.json)"""
    try:
        # Delete machine using file-based storage
        success, message = backend_extension.delete_machine(machine_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 404
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# ============================================================
# LOT Management API (File-based: lots.json)
# ============================================================

@app.route('/api/lots', methods=['GET'])
def get_lots():
    """Get all lots from file (lots.json)"""
    try:
        lots_file = Path('lots.json')
        if not lots_file.exists():
            # Create empty lots file if not exists
            with open(lots_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
            return jsonify({
                'success': True,
                'lots': []
            })
        
        with open(lots_file, 'r', encoding='utf-8') as f:
            lots = json.load(f)
        
        return jsonify({
            'success': True,
            'lots': lots
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/lots', methods=['POST'])
def add_lot():
    """Add a new lot to file (lots.json)"""
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('id'):
            return jsonify({
                'success': False,
                'message': 'LOT ID is required'
            }), 400
        
        if not data.get('name'):
            return jsonify({
                'success': False,
                'message': 'LOT name is required'
            }), 400
        
        if not data.get('type'):
            return jsonify({
                'success': False,
                'message': 'LOT type is required'
            }), 400
        
        # Load existing lots
        lots_file = Path('lots.json')
        if lots_file.exists():
            with open(lots_file, 'r', encoding='utf-8') as f:
                lots = json.load(f)
        else:
            lots = []
        
        # Check if lot ID already exists
        if any(lot['id'] == data['id'] for lot in lots):
            return jsonify({
                'success': False,
                'message': f'LOT ID {data["id"]} already exists'
            }), 400
        
        # Add timestamp if not provided
        if 'created_date' not in data:
            data['created_date'] = datetime.now().isoformat()
        
        if 'status' not in data:
            data['status'] = 'active'
        
        # Add new lot
        lots.append(data)
        
        # Save to file
        with open(lots_file, 'w', encoding='utf-8') as f:
            json.dump(lots, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'LOT added successfully'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/lots/<lot_id>', methods=['PUT'])
def update_lot(lot_id):
    """Update lot information in file (lots.json)"""
    try:
        data = request.json
        
        # Load existing lots
        lots_file = Path('lots.json')
        if not lots_file.exists():
            return jsonify({
                'success': False,
                'message': 'Lots file not found'
            }), 404
        
        with open(lots_file, 'r', encoding='utf-8') as f:
            lots = json.load(f)
        
        # Find and update lot
        updated = False
        for i, lot in enumerate(lots):
            if lot['id'] == lot_id:
                # Keep id and created_date, update other fields
                data['id'] = lot_id
                if 'created_date' not in data:
                    data['created_date'] = lot.get('created_date', datetime.now().isoformat())
                
                lots[i] = data
                updated = True
                break
        
        if not updated:
            return jsonify({
                'success': False,
                'message': f'LOT {lot_id} not found'
            }), 404
        
        # Save to file
        with open(lots_file, 'w', encoding='utf-8') as f:
            json.dump(lots, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'LOT updated successfully'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/lots/<lot_id>', methods=['DELETE'])
def delete_lot(lot_id):
    """Delete a lot from file (lots.json)"""
    try:
        # Load existing lots
        lots_file = Path('lots.json')
        if not lots_file.exists():
            return jsonify({
                'success': False,
                'message': 'Lots file not found'
            }), 404
        
        with open(lots_file, 'r', encoding='utf-8') as f:
            lots = json.load(f)
        
        # Find and remove lot
        original_length = len(lots)
        lots = [lot for lot in lots if lot['id'] != lot_id]
        
        if len(lots) == original_length:
            return jsonify({
                'success': False,
                'message': f'LOT {lot_id} not found'
            }), 404
        
        # Save to file
        with open(lots_file, 'w', encoding='utf-8') as f:
            json.dump(lots, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': 'LOT deleted successfully'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# ============================================================
# Image Capture API (with watermark)
# ============================================================

@app.route('/api/capture', methods=['POST'])
def capture_image_with_watermark():
    """Capture current frame with colored ROI boxes and professional watermark"""
    try:
        data = request.json
        
        # Get watermark information
        lot_info = data.get('lot', {})
        machine_info = data.get('machine', {})
        
        # Get current frame — always use raw frame as base so we
        # can draw fresh coloured ROI boxes + banner without double-annotations
        with frame_lock:
            if latest_frame is not None:
                frame = latest_frame.copy()
            elif latest_annotated_frame is not None:
                frame = latest_annotated_frame.copy()
            else:
                return jsonify({
                    'success': False,
                    'message': 'No frame available. Camera may not be running.'
                }), 404
        
        height, width = frame.shape[:2]
        
        # ============================================================
        # STEP 1: Draw colored ROI boxes from latest_all_measurements
        # ============================================================
        measurements_snapshot = latest_all_measurements.copy()
        pass_count = 0
        fail_count = 0
        
        for idx, m in enumerate(measurements_snapshot):
            bbox = m.get('bbox')
            if not bbox or len(bbox) != 4:
                continue
            
            x, y, w, h = bbox
            status = m.get('status')
            width_mm = m.get('width_mm', 0)
            height_mm = m.get('height_mm', 0)
            area_mm2 = m.get('area_mm2', 0)
            label = m.get('label', f'Object_{idx+1}')
            
            # Count statuses (only pass/fail now)
            if status == 'pass':
                pass_count += 1
                box_color = (0, 220, 0)       # Green (BGR)
                text_bg = (0, 180, 0)
            elif status == 'fail':
                fail_count += 1
                box_color = (0, 0, 220)        # Red (BGR)
                text_bg = (0, 0, 180)
            else:
                box_color = (180, 180, 180)    # Gray
                text_bg = (120, 120, 120)
            
            # Draw main bounding box (thick border)
            cv2.rectangle(frame, (x, y), (x + w, y + h), box_color, 2)
            
            # Semi-transparent fill
            overlay = frame.copy()
            cv2.rectangle(overlay, (x, y), (x + w, y + h), box_color, -1)
            cv2.addWeighted(overlay, 0.08, frame, 0.92, 0, frame)
            
            # Draw corner markers (L-shaped corners)
            corner_len = min(15, w // 4, h // 4)
            cv2.line(frame, (x, y), (x + corner_len, y), box_color, 2)
            cv2.line(frame, (x, y), (x, y + corner_len), box_color, 2)
            cv2.line(frame, (x + w, y), (x + w - corner_len, y), box_color, 2)
            cv2.line(frame, (x + w, y), (x + w, y + corner_len), box_color, 2)
            cv2.line(frame, (x, y + h), (x + corner_len, y + h), box_color, 2)
            cv2.line(frame, (x, y + h), (x, y + h - corner_len), box_color, 2)
            cv2.line(frame, (x + w, y + h), (x + w - corner_len, y + h), box_color, 2)
            cv2.line(frame, (x + w, y + h), (x + w, y + h - corner_len), box_color, 2)
            
            # Size label (center of box)
            if width_mm > 0 and height_mm > 0:
                size_text = f'W:{int(width_mm)} H:{int(height_mm)}mm'
                font = cv2.FONT_HERSHEY_SIMPLEX
                (tw, th), _ = cv2.getTextSize(size_text, font, 0.45, 1)
                tx = x + w // 2 - tw // 2
                ty = y + h // 2 + th // 2
                cv2.rectangle(frame, (tx - 4, ty - th - 4), (tx + tw + 4, ty + 4), (0, 0, 0), -1)
                cv2.putText(frame, size_text, (tx, ty), font, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            
            # Status badge (top of bounding box)
            status_text = status.upper() if status else 'N/A'
            badge_text = f'#{idx+1} {status_text}'
            font = cv2.FONT_HERSHEY_SIMPLEX
            (bw, bh), _ = cv2.getTextSize(badge_text, font, 0.42, 1)
            bx = x
            by = max(y - bh - 6, 0)
            cv2.rectangle(frame, (bx, by), (bx + bw + 8, by + bh + 6), text_bg, -1)
            cv2.putText(frame, badge_text, (bx + 4, by + bh + 2), font, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
        
        # ============================================================
        # STEP 2: Add professional bottom banner watermark (90px tall)
        # ============================================================
        banner_height = 90
        banner_y = height - banner_height
        
        # Draw dark banner background (solid)
        cv2.rectangle(frame, (0, banner_y), (width, height), (20, 25, 35), -1)
        
        # Thin light separator line at banner top
        cv2.line(frame, (0, banner_y), (width, banner_y), (70, 80, 100), 1)
        
        # Draw status indicator bar (colored segments, 3px tall)
        total_detected = len(measurements_snapshot)
        bar_y = banner_y + 2
        bar_h = 3
        if total_detected > 0:
            if pass_count > 0:
                seg_w = int((pass_count / total_detected) * width)
                cv2.rectangle(frame, (0, bar_y), (seg_w, bar_y + bar_h), (0, 200, 0), -1)
            if fail_count > 0:
                seg_start = int((pass_count / total_detected) * width)
                cv2.rectangle(frame, (seg_start, bar_y), (width, bar_y + bar_h), (0, 0, 200), -1)
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        small_font = 0.40
        medium_font = 0.48
        white = (240, 240, 240)
        gray_text = (150, 160, 175)
        accent = (120, 160, 220)
        
        # Row positions inside 90px banner
        row1 = banner_y + 22   # primary info
        row2 = banner_y + 44   # secondary info
        row3 = banner_y + 72   # stat boxes row
        
        # Divider X positions (3 equal columns)
        col1_x = 12
        col2_x = width // 3
        col3_x = (width * 2) // 3
        
        # Extract data
        lot_name     = lot_info.get('name', 'N/A')
        lot_type     = lot_info.get('type', 'N/A')
        lot_id_disp  = str(lot_info.get('id', '-'))
        machine_name = machine_info.get('name', 'N/A')
        rubber_type  = data.get('rubber_type', 'black')
        rubber_label = 'Rubber: Black' if rubber_type == 'black' else 'Rubber: White'
        rubber_dot_color = (60, 60, 60) if rubber_type == 'black' else (230, 230, 230)
        timestamp    = datetime.now().strftime('%Y-%m-%d  %H:%M:%S')
        
        # Vertical divider lines between columns
        cv2.line(frame, (col2_x - 10, banner_y + 8), (col2_x - 10, height - 8), (55, 65, 80), 1)
        cv2.line(frame, (col3_x - 10, banner_y + 8), (col3_x - 10, height - 8), (55, 65, 80), 1)
        
        # ── COL 1: LOT ──
        cv2.putText(frame, f'LOT: {lot_name}', (col1_x, row1), font, medium_font, white, 1, cv2.LINE_AA)
        cv2.putText(frame, f'ID: {lot_id_disp}   TYPE: {lot_type}', (col1_x, row2), font, small_font, gray_text, 1, cv2.LINE_AA)
        
        # ── COL 2: Machine + Time ──
        cv2.putText(frame, f'Machine: {machine_name}', (col2_x, row1), font, medium_font, white, 1, cv2.LINE_AA)
        cv2.putText(frame, timestamp, (col2_x, row2), font, small_font, gray_text, 1, cv2.LINE_AA)
        
        # ── COL 3: Detected count + Rubber type ──
        cv2.putText(frame, f'Detected: {total_detected}', (col3_x, row1), font, medium_font, white, 1, cv2.LINE_AA)
        # Rubber dot indicator
        dot_cx = col3_x + 8
        dot_cy = row2 - 5
        cv2.circle(frame, (dot_cx, dot_cy), 6, rubber_dot_color, -1)
        cv2.circle(frame, (dot_cx, dot_cy), 6, (130, 140, 160), 1)
        cv2.putText(frame, rubber_label, (col3_x + 20, row2), font, small_font, (200, 210, 220), 1, cv2.LINE_AA)
        
        # ── ROW 3: Coloured stat boxes spanning right 2/3 ──
        if total_detected > 0:
            pass_pct  = int(pass_count  * 100 // total_detected)
            fail_pct  = int(fail_count  * 100 // total_detected)
        else:
            pass_pct = fail_pct = 0
        
        stat_boxes = [
            (f'PASS: {pass_count} ({pass_pct}%)',       (20, 90, 20),   (160, 230, 160)),
            (f'FAIL: {fail_count} ({fail_pct}%)',        (100, 20, 20),  (230, 150, 150)),
        ]
        box_h = 18
        box_y_top = row3 - box_h
        bx = col1_x  # Start from left edge for stat boxes on row 3
        for (box_text, bg_col, txt_col) in stat_boxes:
            (tw, th), _ = cv2.getTextSize(box_text, font, 0.38, 1)
            box_w = tw + 14
            cv2.rectangle(frame, (bx, box_y_top), (bx + box_w, box_y_top + box_h), bg_col, -1)
            cv2.rectangle(frame, (bx, box_y_top), (bx + box_w, box_y_top + box_h), (90, 90, 90), 1)
            cv2.putText(frame, box_text, (bx + 7, box_y_top + th + 3), font, 0.38, txt_col, 1, cv2.LINE_AA)
            bx += box_w + 6
        
        # PSE Vision label (far right bottom)
        brand_text = 'PSE Vision'
        (bw, bh), _ = cv2.getTextSize(brand_text, font, small_font, 1)
        cv2.putText(frame, brand_text, (width - bw - 12, row3), font, small_font, accent, 1, cv2.LINE_AA)
        
        # ============================================================
        # STEP 3: Save image
        # ============================================================
        captures_dir = Path('captures')
        captures_dir.mkdir(exist_ok=True)
        
        lot_id_safe = str(lot_info.get('id', 'NOLOT')).replace('-', '').replace(' ', '_')
        filename = f"capture_{lot_id_safe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        filepath = captures_dir / filename
        
        # Save with high quality JPEG (90%)
        cv2.imwrite(str(filepath), frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
        
        print(f"[CAPTURE] ✅ Saved: {filepath} - Detections: {total_detected} (PASS:{pass_count} FAIL:{fail_count})")
        
        # ============================================================
        # STEP 4: Save to database if enabled
        # ============================================================
        if db_service:
            try:
                capture_id = f"CAP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                capture_db_data = {
                    'capture_id': capture_id,
                    'machine_id': machine_info.get('id', ''),
                    'machine_name': machine_info.get('name', 'Unknown'),
                    'lot_id': str(lot_info.get('id', '')),
                    'lot_name': lot_info.get('name', ''),
                    'lot_type': lot_info.get('type', ''),
                    'rubber_type': rubber_type,
                    'image_path': str(filepath),
                    'total_detected': total_detected,
                    'pass_count': pass_count,
                    'near_pass_count': 0,  # No longer used (backward compatibility)
                    'fail_count': fail_count
                }
                
                db_success, db_message = db_service.insert_capture_session(capture_db_data)
                if db_success:
                    print(f"[DATABASE] ✅ Capture session saved: {db_message}")
                else:
                    print(f"[DATABASE] ⚠️ Failed to save capture session: {db_message}")
            except Exception as db_err:
                print(f"[DATABASE] ❌ Error saving capture session: {db_err}")
        
        return jsonify({
            'success': True,
            'message': f'Captured {total_detected} objects (PASS:{pass_count} FAIL:{fail_count})',
            'filename': filename,
            'filepath': str(filepath),
            'summary': {
                'total': total_detected,
                'pass': pass_count,
                'near_pass': 0,  # No longer used (backward compatibility)
                'fail': fail_count
            }
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


# ═══════════════════════════════════════════════════════════════════════════
# 🔌 POWER CONTROL API (Wake-on-LAN, Shutdown, Reboot)
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/power/wake', methods=['POST'])
def power_wake_on_lan():
    """
    Wake-on-LAN: ส่ง Magic Packet เพื่อเปิดเครื่องผ่าน MAC address
    
    Request Body:
    {
        "mac_address": "XX:XX:XX:XX:XX:XX" (required),
        "broadcast_ip": "255.255.255.255" (optional, default: 255.255.255.255),
        "port": 9 (optional, default: 9)
    }
    """
    try:
        from python_scripts.power_manager import send_wake_on_lan
        
        data = request.get_json()
        mac_address = data.get('mac_address')
        broadcast_ip = data.get('broadcast_ip', '255.255.255.255')
        port = data.get('port', 9)
        
        if not mac_address:
            return jsonify({
                'success': False,
                'message': 'MAC address is required'
            }), 400
        
        success, message = send_wake_on_lan(mac_address, broadcast_ip, port)
        
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 500
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/power/shutdown', methods=['POST'])
def power_shutdown():
    """
    Shutdown: ปิดเครื่องปัจจุบัน (local machine)
    
    Request Body:
    {
        "delay_seconds": 0 (optional, default: 0)
    }
    """
    try:
        from python_scripts.power_manager import shutdown_local_machine
        
        data = request.get_json() if request.get_json() else {}
        delay_seconds = data.get('delay_seconds', 0)
        
        success, message = shutdown_local_machine(delay_seconds)
        
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 500
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/power/reboot', methods=['POST'])
def power_reboot():
    """
    Reboot: รีบูตเครื่องปัจจุบัน (local machine)
    
    Request Body:
    {
        "delay_seconds": 0 (optional, default: 0)
    }
    """
    try:
        from python_scripts.power_manager import reboot_local_machine
        
        data = request.get_json() if request.get_json() else {}
        delay_seconds = data.get('delay_seconds', 0)
        
        success, message = reboot_local_machine(delay_seconds)
        
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 500
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/power/remote-shutdown', methods=['POST'])
def power_remote_shutdown():
    """
    Remote Shutdown: ปิดเครื่องระยะไกลผ่าน SSH
    
    Request Body:
    {
        "target_ip": "10.4.100.90" (required),
        "username": "adminpse" (required),
        "password": "Abc123**" (optional if using SSH key),
        "ssh_key": "/path/to/key" (optional),
        "delay_seconds": 0 (optional, default: 0)
    }
    """
    try:
        from python_scripts.power_manager import shutdown_remote_machine
        
        data = request.get_json()
        target_ip = data.get('target_ip')
        username = data.get('username')
        password = data.get('password')
        ssh_key = data.get('ssh_key')
        delay_seconds = data.get('delay_seconds', 0)
        
        if not target_ip or not username:
            return jsonify({
                'success': False,
                'message': 'target_ip and username are required'
            }), 400
        
        success, message = shutdown_remote_machine(target_ip, username, password, ssh_key, delay_seconds)
        
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 500
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


# ═══════════════════════════════════════════════════════════════════════════
# � FORCE MACHINE CONFIG CHANGE (Admin Control)
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/admin/force-machine', methods=['POST'])
def force_machine_config():
    """
    Force change machine configuration (Admin only - bypasses Desktop App)
    
    Request Body:
    {
        "machine_id": "No1" (required)
    }
    
    Returns:
        {
            "success": true,
            "machine_id": "No1",
            "machine_name": "HA01",
            "config": {
                "target_area_min": 3500,
                "target_area_max": 3750,
                "tolerance": 50
            }
        }
    """
    global active_measurement_config, active_machine_id, active_machine_name
    
    try:
        data = request.get_json() if request.is_json else {}
        machine_id = data.get('machine_id')
        
        if not machine_id:
            return jsonify({
                'success': False,
                'error': 'Missing machine_id'
            }), 400
        
        # Load machines.json
        machines_file = Path(BASE_PATH) / 'machines.json'
        if not machines_file.exists():
            machines_file = Path(BASE_PATH).parent / 'python_scripts' / 'machines.json'
        
        if not machines_file.exists():
            return jsonify({
                'success': False,
                'error': 'machines.json not found'
            }), 404
        
        with open(machines_file, 'r', encoding='utf-8') as f:
            machines = json.load(f)
        
        # Find machine by ID
        machine = next((m for m in machines if m.get('id') == machine_id), None)
        
        if not machine:
            return jsonify({
                'success': False,
                'error': f'Machine {machine_id} not found'
            }), 404
        
        machine_name = machine.get('name', machine_id)
        machine_config = machine.get('config')
        
        if not machine_config:
            return jsonify({
                'success': False,
                'error': f'Machine {machine_id} has no inline config'
            }), 400
        
        # Force update global variables
        active_machine_id = machine_id
        active_machine_name = machine_name
        active_measurement_config = machine_config
        
        print(f"[ADMIN] 🔧 Force changed machine config:")
        print(f"        Machine: {machine_name} ({machine_id})")
        print(f"        Config: {machine_config['target_area_min']}-{machine_config['target_area_max']} mm² ±{machine_config.get('tolerance', 0)}")
        
        return jsonify({
            'success': True,
            'machine_id': machine_id,
            'machine_name': machine_name,
            'config': machine_config,
            'message': f'Machine changed to {machine_name}'
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ═══════════════════════════════════════════════════════════════════════════
# �💾 DATABASE QUERY APIs (Capture Sessions History)
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/database/captures', methods=['GET'])
def get_capture_sessions_api():
    """
    Get recent capture sessions from database
    
    Query Parameters:
        - limit: int (optional, default: 50)
    
    Returns:
        {
            "success": true,
            "data": [
                {
                    "id": 1,
                    "capture_id": "CAP_20260525_143020",
                    "machine_name": "HA01",
                    "lot_name": "AA",
                    "total_detected": 5,
                    "pass_count": 3,
                    "near_pass_count": 1,
                    "fail_count": 1,
                    "captured_at": "2026-05-25T14:30:20"
                }
            ]
        }
    """
    try:
        if not db_service:
            return jsonify({
                'success': False,
                'message': 'Database service not available'
            }), 503
        
        # Get limit parameter
        limit = request.args.get('limit', 50, type=int)
        limit = min(max(limit, 1), 500)  # Clamp between 1-500
        
        # Query database
        success, result = db_service.get_capture_sessions(limit)
        
        if success:
            return jsonify({
                'success': True,
                'data': result,
                'count': len(result)
            })
        else:
            return jsonify({
                'success': False,
                'message': result
            }), 500
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Error retrieving captures: {str(e)}'
        }), 500


@app.route('/api/database/status', methods=['GET'])
def get_database_status():
    """
    Get database connection status
    
    Returns:
        {
            "success": true,
            "enabled": true,
            "db_type": "sqlite",
            "connected": true,
            "db_path": "data/pse_vision.db"
        }
    """
    try:
        enabled = db_config.get('enabled', False)
        db_type = db_config.get('db_type', 'sqlite')
        db_path = db_config.get('sqlite_path', 'data/pse_vision.db')
        
        connected = db_service is not None
        
        result = {
            'success': True,
            'enabled': enabled,
            'db_type': db_type,
            'connected': connected
        }
        
        if db_type == 'sqlite':
            result['db_path'] = db_path
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


if __name__ == '__main__':
    # Reset global state on startup
    camera_active = False
    oak_device = None
    latest_frame = None
    latest_depth = None
    running = False
    
    # Get port from environment variable or default to 64021
    port = int(os.environ.get('FLASK_PORT', 64021))
    
    print("=" * 60)
    print("OAK Camera Object Measurement System - Backend Server")
    print("Contour Detection Mode")
    print("=" * 60)
    print(f"\nServer starting on http://localhost:{port}")
    print(f"API endpoints available at http://localhost:{port}/api/")
    print("\nDetection: Contour-based background subtraction")
    print("Press CTRL+C to stop the server\n")
    print("=" * 60)
    
    # Check for available OAK devices
    try:
        devices = dai.Device.getAllAvailableDevices()
        if len(devices) > 0:
            print(f" Found {len(devices)} OAK camera device(s) connected")
            for i, device in enumerate(devices):
                print(f"  Device {i+1}: {device.getMxId()}")
        else:
            print(" No OAK camera devices detected")
            print("  Please connect an OAK camera to use measurement features")
    except Exception as e:
        print(f" Error checking for OAK devices: {e}")
    
    print("=" * 60)
    
    # 🔧 Load fallback measurement config (ก่อน camera start)
    # เพื่อให้ระบบนับ statistics ได้แม้กล้องไม่เชื่อมต่อ
    print("\n[Config] Loading fallback measurement config...")
    try:
        config_file = Path(BASE_PATH) / 'configurations.json'
        if not config_file.exists():
            config_file = Path(BASE_PATH).parent / 'python_scripts' / 'configurations.json'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                _configs = json.load(f)
            if _configs:
                fallback_measurement_config = _configs[0]
                print(f"[Config] ✅ Fallback config loaded: {fallback_measurement_config['name']}")
                print(f"         Target: {fallback_measurement_config['target_area_min']}-{fallback_measurement_config['target_area_max']} mm²")
            else:
                print("[Config] ⚠️ No configurations found in configurations.json")
        else:
            print(f"[Config] ⚠️ configurations.json not found in {BASE_PATH}")
    except Exception as _e:
        print(f"[Config] ❌ Failed to load fallback config: {_e}")
    
    # ไม่ auto-start camera ตอน startup
    # ให้ frontend เชื่อมต่อ backend ก่อน แล้วค่อยกด Start Camera
    print("\n[Config] Camera will start when user clicks 'Start Camera' in frontend.")
    camera_active = False
    camera_should_run = False
    system_config.set("camera_active", 0, auto_save=True)

    # ♻️ Start the autonomous camera watchdog (self-healing reconnect).
    # It only acts once the user starts the camera (camera_should_run=True) and
    # then keeps it connected without depending on any browser polling.
    # 📡 Publish frames off the camera thread so a slow client cannot stall it.
    emitter_thread = threading.Thread(target=frame_emitter, daemon=True, name='frame-emitter')
    emitter_thread.start()

    # A PoE camera keeps its session for ~45s when the host disappears without
    # closing it, so every `systemctl restart` was followed by a minute of
    # X_LINK connect failures. Hand the device back on the way out.
    def _shutdown(signum, _frame):
        global camera_should_run
        print(f"[SHUTDOWN] Signal {signum} - releasing camera before exit")
        camera_should_run = False
        try:
            stop_oak_camera(user_initiated=True)
        except Exception as e:
            print(f"[SHUTDOWN] Camera release failed: {e}")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    if HAS_DEPTHAI:
        watchdog_thread = threading.Thread(target=camera_watchdog, daemon=True)
        watchdog_thread.start()
    else:
        print("[WATCHDOG] depthai not available - watchdog idle (no OAK camera on this host)")
    
    # Restore rubber type
    saved_rubber_type = system_config.get('rubber_type', 'black')
    if saved_rubber_type in ['black', 'white']:
        rubber_type = saved_rubber_type
        print(f"[Config] Rubber type: {rubber_type}")
    
    print(f"[Config] Zoom level: {system_config.get('zoom_level')}")
    print(f"[Config] Depth color: {system_config.get('depth_color_scheme')}")
    print(f"[Config] Ground distance: {system_config.get('ground_distance_mm')}mm")
    print("=" * 60)
    
    print(f"\n🌐 Starting Backend + Admin Web Server on http://0.0.0.0:{port}")
    print(f"📁 Serving Admin Web from: {FRONTEND_DIST}")
    print(f"🔗 Access URLs:")
    print(f"   - Local: http://localhost:{port}")
    print(f"   - Network: http://<your-ip>:{port}")
    print("\n" + "=" * 60)
    
    socketio.run(app, host='0.0.0.0', port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
