#!/usr/bin/env python3
"""Camera worker process: connects to OAK via depthai and writes latest frame and depth to disk.
This runs in a separate process so native crashes in depthai don't kill the Flask server.
"""
import os
import sys
import time
import json
import signal
from pathlib import Path
from python_scripts.camera_lock import acquire_lock, release_lock, get_lock_owner
from python_scripts.oak_ip_config import ensure_oak_poe_static_ip
from python_scripts.system_config import system_config
try:
    import depthai as dai
    import cv2
    import numpy as np
except Exception as e:
    print(f"[camera_worker] Missing dependency or import error: {e}")
    raise

BASE = Path(__file__).resolve().parent
RUNTIME_DIR = BASE / 'runtime'
RUNTIME_DIR.mkdir(exist_ok=True)
FRAME_PATH = RUNTIME_DIR / 'latest_frame.jpg'
DEPTH_PATH = RUNTIME_DIR / 'latest_depth.npy'
META_PATH = RUNTIME_DIR / 'latest_meta.json'

def write_meta(**kwargs):
    meta = {'ts': time.time()}
    meta.update(kwargs)
    try:
        with open(META_PATH, 'w', encoding='utf-8') as f:
            json.dump(meta, f)
    except Exception:
        pass

def main():
    print("[camera_worker] Starting camera worker")
    network_camera_ip = str(system_config.get('network_camera_ip', '') or '').strip()
    if network_camera_ip:
        print(f"[camera_worker] Network camera IP configured: {network_camera_ip}")
        ensure_oak_poe_static_ip(system_config, dai_module=dai, logger=lambda msg: print(f"[camera_worker] {msg}"))
    else:
        print("[camera_worker] No network camera IP configured; using auto-detect")
    stop_requested = False

    def _signal_handler(sig, frame):
        nonlocal stop_requested
        print(f"[camera_worker] Received signal {sig}, stopping...")
        stop_requested = True

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    backoff_base = 1.0
    while not stop_requested:
        try:
            pipeline = dai.Pipeline()
            cam_rgb = pipeline.create(dai.node.ColorCamera)
            cam_rgb.setPreviewSize(1280, 720)
            cam_rgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_720_P)
            cam_rgb.setInterleaved(False)
            cam_rgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
            cam_rgb.setFps(15)

            xout_rgb = pipeline.create(dai.node.XLinkOut)
            xout_rgb.setStreamName('rgb')
            cam_rgb.preview.link(xout_rgb.input)

            mono_left = pipeline.create(dai.node.MonoCamera)
            mono_right = pipeline.create(dai.node.MonoCamera)
            stereo = pipeline.create(dai.node.StereoDepth)
            mono_left.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
            mono_right.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
            mono_left.setBoardSocket(dai.CameraBoardSocket.CAM_B)
            mono_right.setBoardSocket(dai.CameraBoardSocket.CAM_C)
            stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)
            mono_left.out.link(stereo.left)
            mono_right.out.link(stereo.right)
            xout_depth = pipeline.create(dai.node.XLinkOut)
            xout_depth.setStreamName('depth')
            stereo.depth.link(xout_depth.input)

            print("[camera_worker] Creating device... attempting to acquire camera lock")

            # Try to acquire lock; if another live owner exists, wait and poll
            locked = acquire_lock(timeout=2.0)
            if not locked:
                owner = get_lock_owner()
                write_meta(status='locked', owner=owner)
                print(f"[camera_worker] Lock held by PID {owner}, will retry...")
                time.sleep(2.0)
                continue

            # We have the lock - try to create device. If device creation fails (no hardware),
            # release lock and retry with backoff so stale locks are not held unnecessarily.
            try:
                if network_camera_ip:
                    device = dai.Device(pipeline, dai.DeviceInfo(network_camera_ip))
                else:
                    device = dai.Device(pipeline)
            except Exception as ex:
                print(f"[camera_worker] Failed to create device: {ex}")
                write_meta(status='error', error=str(ex))
                try:
                    release_lock()
                except Exception:
                    pass
                # Backoff before retrying to give OS/hardware time to settle
                time.sleep(min(backoff_base, 10.0))
                backoff_base = min(backoff_base * 2, 10.0)
                continue
            q_rgb = device.getOutputQueue(name='rgb', maxSize=1, blocking=False)
            q_depth = device.getOutputQueue(name='depth', maxSize=1, blocking=False)

            print("[camera_worker] Device created, entering capture loop")
            write_meta(status='running')
            backoff_base = 1.0
            try:
                while not stop_requested:
                    in_rgb = q_rgb.tryGet()
                    in_depth = q_depth.tryGet()
                    received_frame = False

                    if in_rgb is not None:
                        frame = in_rgb.getCvFrame()
                        # Downscale to reduce disk I/O.
                        h, w = frame.shape[:2]
                        frame_resized = cv2.resize(frame, (int(w * 0.6), int(h * 0.6)), interpolation=cv2.INTER_AREA)
                        try:
                            cv2.imwrite(str(FRAME_PATH), frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 80])
                            received_frame = True
                        except Exception:
                            pass

                    if in_depth is not None:
                        depth = in_depth.getFrame()
                        try:
                            np.save(DEPTH_PATH, depth)
                            received_frame = True
                        except Exception:
                            pass

                    if received_frame:
                        write_meta(status='ok')
                    time.sleep(0.05)

            finally:
                # Ensure device is closed and lock released when capture loop exits
                try:
                    if 'device' in locals() and device is not None:
                        try:
                            device.close()
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    release_lock()
                except Exception:
                    pass

        except Exception as e:
            print(f"[camera_worker] Error: {e}")
            write_meta(status='error', error=str(e))
            try:
                if 'device' in locals() and device is not None:
                    try:
                        device.close()
                    except Exception:
                        pass
            except Exception:
                pass
            try:
                release_lock()
            except Exception:
                pass

            if stop_requested:
                break

            # Exponential backoff on repeated failures
            time.sleep(2)
            print("[camera_worker] Restarting camera worker loop")

    # Final cleanup on exit
    try:
        release_lock()
    except Exception:
        pass
    print("[camera_worker] Exiting")

if __name__ == '__main__':
    main()
