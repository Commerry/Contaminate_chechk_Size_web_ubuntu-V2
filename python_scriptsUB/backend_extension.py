"""
Backend Extension for Real-time Streaming and Area-based Measurement
เพิ่ม WebSocket support และ configuration management
"""

from flask import jsonify, request
from flask_socketio import SocketIO, emit
import json
import base64
import cv2
import numpy as np
import sys
import os
from datetime import datetime
from pathlib import Path

# Detect if running as PyInstaller bundle or Electron bundled Python
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Running as PyInstaller executable
    BASE_PATH = Path(sys._MEIPASS) / 'python_scripts'
else:
    # Running as normal Python script or Electron bundled Python
    file_path = Path(__file__).resolve()
    BASE_PATH = file_path.parent

# Global variables
configurations = []
active_config = None

# Global variables for machines (file-based storage)
machines = []


def init_socketio(app):
    """Initialize SocketIO with Flask app"""
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection"""
        print(f"[WebSocket] Client connected")
        emit('connection_status', {'status': 'connected', 'timestamp': datetime.now().isoformat()})
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print(f"[WebSocket] Client disconnected")
    
    @socketio.on('request_frame')
    def handle_frame_request():
        """Client requests current frame"""
        # Will be implemented to send current frame
        pass
    
    return socketio


def load_configurations():
    """โหลด configurations จากไฟล์"""
    global configurations
    
    config_file = BASE_PATH / "configurations.json"
    
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            configurations = json.load(f)
    else:
        # สร้าง default configurations
        configurations = [
            {
                "id": 1,
                "name": "Small Object (Area 500-1000 mm²)",
                "target_area_min": 500,
                "target_area_max": 1000,
                "tolerance": 50,
                "enabled": True,
                "created_at": datetime.now().isoformat()
            },
            {
                "id": 2,
                "name": "Medium Object (Area 1000-2500 mm²)",
                "target_area_min": 1000,
                "target_area_max": 2500,
                "tolerance": 100,
                "enabled": True,
                "created_at": datetime.now().isoformat()
            },
            {
                "id": 3,
                "name": "Large Object (Area 2500-5000 mm²)",
                "target_area_min": 2500,
                "target_area_max": 5000,
                "tolerance": 200,
                "enabled": True,
                "created_at": datetime.now().isoformat()
            }
        ]
        save_configurations()
    
    return configurations


def save_configurations():
    """บันทึก configurations ลงไฟล์"""
    config_file = BASE_PATH / "configurations.json"
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(configurations, f, indent=2, ensure_ascii=False)


# =============== Machine Management (File-based) ===============

def load_machines():
    """โหลด machines จากไฟล์"""
    global machines
    
    machines_file = BASE_PATH / "machines.json"
    
    if machines_file.exists():
        with open(machines_file, 'r', encoding='utf-8') as f:
            machines = json.load(f)
    else:
        # เริ่มต้นด้วย list ว่าง
        machines = []
        save_machines()
    
    return machines


def save_machines():
    """บันทึก machines ลงไฟล์"""
    machines_file = BASE_PATH / "machines.json"
    
    with open(machines_file, 'w', encoding='utf-8') as f:
        json.dump(machines, f, indent=2, ensure_ascii=False)


def get_all_machines():
    """ดึงรายการ machines ทั้งหมด"""
    return machines


def add_machine(machine_data):
    """เพิ่ม machine ใหม่ (รวม configuration แบบ inline)"""
    try:
        # ตรวจสอบว่า machine_id ซ้ำหรือไม่
        machine_id = machine_data.get('id')
        if any(m.get('id') == machine_id for m in machines):
            return False, f"Machine ID '{machine_id}' already exists"
        
        # ✅ สร้าง machine object (รวม config)
        new_machine = {
            'id': machine_id,
            'name': machine_data.get('name', ''),
            'location': machine_data.get('location', ''),
            'description': machine_data.get('description', ''),
            'status': machine_data.get('status', 'active'),
            'config': {
                'target_area_min': machine_data.get('target_area_min', 500),
                'target_area_max': machine_data.get('target_area_max', 1000),
                'tolerance': machine_data.get('tolerance', 50)
            },
            'created_at': datetime.now().isoformat()
        }
        
        machines.append(new_machine)
        save_machines()
        
        return True, 'Machine added successfully'
    
    except Exception as e:
        return False, str(e)


def update_machine(machine_id, machine_data):
    """แก้ไขข้อมูล machine (รวม configuration)"""
    try:
        for machine in machines:
            if machine.get('id') == machine_id:
                machine.update({
                    'name': machine_data.get('name', machine.get('name')),
                    'location': machine_data.get('location', machine.get('location')),
                    'description': machine_data.get('description', machine.get('description')),
                    'status': machine_data.get('status', machine.get('status')),
                    'updated_at': datetime.now().isoformat()
                })
                
                # ✅ Update config if provided
                if 'target_area_min' in machine_data or 'target_area_max' in machine_data or 'tolerance' in machine_data:
                    if 'config' not in machine:
                        machine['config'] = {}
                    
                    if 'target_area_min' in machine_data:
                        machine['config']['target_area_min'] = machine_data['target_area_min']
                    if 'target_area_max' in machine_data:
                        machine['config']['target_area_max'] = machine_data['target_area_max']
                    if 'tolerance' in machine_data:
                        machine['config']['tolerance'] = machine_data['tolerance']
                
                save_machines()
                return True, 'Machine updated successfully'
        
        return False, 'Machine not found'
    
    except Exception as e:
        return False, str(e)


def delete_machine(machine_id):
    """ลบ machine"""
    global machines
    
    try:
        initial_count = len(machines)
        machines = [m for m in machines if m.get('id') != machine_id]
        
        if len(machines) < initial_count:
            save_machines()
            return True, 'Machine deleted successfully'
        else:
            return False, 'Machine not found'
    
    except Exception as e:
        return False, str(e)


# =============== Area Calculation & Validation ===============


def calculate_area_from_dimensions(width_mm, height_mm):
    """คำนวณพื้นที่จาก width และ height"""
    return width_mm * height_mm


def validate_area(area_mm2, config):
    """ตรวจสอบว่าพื้นที่อยู่ในช่วงที่กำหนดหรือไม่"""
    if not config:
        return False, "No configuration selected"
    
    min_area = config.get('target_area_min', 0)
    max_area = config.get('target_area_max', float('inf'))
    tolerance = config.get('tolerance', 0)
    
    # Check with tolerance
    if (min_area - tolerance) <= area_mm2 <= (max_area + tolerance):
        return True, "Pass"
    else:
        return False, f"Out of range ({min_area}-{max_area} mm²)"


def calculate_measurements_area_based(detections, calibration_w, calibration_h):
    """
    คำนวณการวัดแบบ area-based
    
    Args:
        detections: list of detected objects with bbox
        calibration_w: calibration factor for width (mm/pixel)
        calibration_h: calibration factor for height (mm/pixel)
    
    Returns:
        list of measurements with area information
    """
    measurements = []
    
    for det in detections:
        if 'bbox' in det:
            x, y, w, h = det['bbox']
            
            # คำนวณขนาดจริงจาก pixels
            width_mm = w * calibration_w
            height_mm = h * calibration_h
            
            # คำนวณพื้นที่
            area_mm2 = calculate_area_from_dimensions(width_mm, height_mm)
            
            # Validate with active config
            is_pass, status_msg = validate_area(area_mm2, active_config)
            
            measurement = {
                'bbox': [x, y, w, h],
                'width_px': w,
                'height_px': h,
                'width_mm': round(width_mm, 2),
                'height_mm': round(height_mm, 2),
                'area_mm2': round(area_mm2, 2),
                'pass': is_pass,
                'status': status_msg,
                'timestamp': datetime.now().isoformat()
            }
            
            if active_config:
                measurement['config_name'] = active_config.get('name', 'Unknown')
                measurement['target_area_min'] = active_config.get('target_area_min', 0)
                measurement['target_area_max'] = active_config.get('target_area_max', 0)
            
            measurements.append(measurement)
    
    return measurements


def broadcast_frame_update(socketio, frame_data, measurements):
    """ส่ง frame update ไปยัง clients ทั้งหมด"""
    try:
        socketio.emit('frame_update', {
            'frame': frame_data,
            'measurements': measurements,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"[WebSocket] Broadcast error: {e}")


def broadcast_roi_update(socketio, roi_list):
    """ส่ง ROI update ไปยัง clients"""
    try:
        socketio.emit('roi_update', {
            'roi_list': roi_list,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"[WebSocket] ROI broadcast error: {e}")


def broadcast_measurement_update(socketio, measurements):
    """ส่ง measurement update ไปยัง clients"""
    try:
        socketio.emit('measurement_update', {
            'measurements': measurements,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        print(f"[WebSocket] Measurement broadcast error: {e}")


# =============== API Routes ===============

def register_routes(app, socketio):
    """Register new API routes for area-based measurement"""
    
    @app.route('/api/configurations', methods=['GET'])
    def get_configurations():
        """ดึงรายการ configurations ทั้งหมด"""
        return jsonify({
            'success': True,
            'configurations': configurations
        })
    
    @app.route('/api/configurations/create', methods=['POST'])
    def create_configuration():
        """สร้าง configuration ใหม่"""
        data = request.json
        
        new_config = {
            'id': max([c['id'] for c in configurations], default=0) + 1,
            'name': data.get('name', 'New Configuration'),
            'target_area_min': data.get('target_area_min', 0),
            'target_area_max': data.get('target_area_max', 1000),
            'tolerance': data.get('tolerance', 50),
            'enabled': data.get('enabled', True),
            'created_at': datetime.now().isoformat()
        }
        
        configurations.append(new_config)
        save_configurations()
        
        return jsonify({
            'success': True,
            'configuration': new_config
        })
    
    @app.route('/api/configurations/<int:config_id>', methods=['PUT'])
    def update_configuration(config_id):
        """แก้ไข configuration"""
        data = request.json
        
        for config in configurations:
            if config['id'] == config_id:
                config.update({
                    'name': data.get('name', config['name']),
                    'target_area_min': data.get('target_area_min', config['target_area_min']),
                    'target_area_max': data.get('target_area_max', config['target_area_max']),
                    'tolerance': data.get('tolerance', config['tolerance']),
                    'enabled': data.get('enabled', config['enabled']),
                    'updated_at': datetime.now().isoformat()
                })
                save_configurations()
                
                return jsonify({
                    'success': True,
                    'configuration': config
                })
        
        return jsonify({
            'success': False,
            'error': 'Configuration not found'
        }), 404
    
    @app.route('/api/configurations/<int:config_id>', methods=['DELETE'])
    def delete_configuration(config_id):
        """ลบ configuration"""
        global configurations
        
        configurations = [c for c in configurations if c['id'] != config_id]
        save_configurations()
        
        return jsonify({
            'success': True,
            'message': 'Configuration deleted'
        })
    
    # NOTE: /api/measurement/start and /api/measurement/stop are handled by
    # start_desktop_measurement() and stop_desktop_measurement() in backend_server.py
    # which set the correct active_measurement_config used by the camera loop.
    # DO NOT register duplicate handlers here.

    @app.route('/api/measurement/current-config', methods=['GET'])
    def get_current_config():
        """ดึง configuration ที่ใช้งานอยู่"""
        return jsonify({
            'success': True,
            'configuration': active_config
        })
    
    @app.route('/api/camera/frame', methods=['GET'])
    def get_current_frame():
        """ดึง frame ปัจจุบันพร้อม measurements"""
        try:
            # Import from backend_server
            import python_scripts.backend_server as backend
            
            with backend.frame_lock:
                if backend.latest_frame is None:
                    return jsonify({
                        'success': False,
                        'error': 'No frame available'
                    })
                
                frame = backend.latest_frame.copy()
            
            # Get current detections
            detections = []
            measurements = []
            
            if backend.contour_detection_active:
                # Get detections from contour detection
                # This will be populated by the contour detection thread
                pass
            
            # Encode frame to base64
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return jsonify({
                'success': True,
                'frame': frame_base64,
                'detections': detections,
                'measurements': measurements,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


# Initialize on module load
load_configurations()
load_machines()
