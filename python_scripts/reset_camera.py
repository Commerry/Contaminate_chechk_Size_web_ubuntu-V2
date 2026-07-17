#!/usr/bin/env python3
"""
Reset Camera Script - diagnostic and reset helper that respects camera PID lock.
"""
import sqlite3
import time
from python_scripts.camera_lock import acquire_lock, release_lock
import depthai as dai

print("=" * 60)
print("OAK Camera Reset & Diagnostic Tool")
print("=" * 60)

# Step 1: Reset zoom to 1.0x
print("\n[1] Resetting zoom to 1.0x...")
try:
    conn = sqlite3.connect('system_config.db')
    c = conn.cursor()
    c.execute('UPDATE system_config SET value="1.0" WHERE key="zoom_level"')
    conn.commit()
    conn.close()
    print("    ✅ Zoom reset to 1.0x")
except Exception as e:
    print(f"    ⚠️ Could not reset zoom: {e}")

# Step 2: Check device status
print("\n[2] Checking device status...")
try:
    devices = dai.Device.getAllAvailableDevices()
    print(f"    Devices found: {len(devices)}")
    for i, dev in enumerate(devices):
        print(f"    Device {i+1}: {dev.getMxId()}")
        print(f"    State: {dev.state.name}")
except Exception as e:
    print(f"    ⚠️ Could not query devices: {e}")

if not devices:
    print("\n❌ No camera found!")
    print("Solutions:")
    print("  1. Unplug USB cable")
    print("  2. Wait 10 seconds")
    print("  3. Plug back in")
    print("  4. Run this script again")
    raise SystemExit(1)

# Step 3: Force device reset and test frames
print("\n[3] Attempting device reset and frame test...")
if not acquire_lock(timeout=5.0):
    print("Could not acquire camera lock. Another process may own the device. Exiting.")
    raise SystemExit(1)

try:
    print("    Connecting to device...")
    device = dai.Device()
    print("    ✅ Device connected")

    print("    Closing device...")
    try:
        device.close()
    except Exception:
        pass
    print("    ✅ Device closed cleanly")

    print("    Waiting 3 seconds...")
    time.sleep(3)

    print("    Reconnecting with pipeline to test frames...")
    pipeline = dai.Pipeline()
    cam = pipeline.create(dai.node.ColorCamera)
    cam.setPreviewSize(640, 480)
    cam.setInterleaved(False)
    cam.setFps(30)

    xout = pipeline.create(dai.node.XLinkOut)
    xout.setStreamName("preview")
    cam.preview.link(xout.input)

    device = dai.Device(pipeline)
    queue = device.getOutputQueue(name="preview", maxSize=1, blocking=False)

    print("    Waiting for frames...")
    frame_count = 0
    for i in range(30):  # Try for ~3 seconds
        frame = queue.tryGet()
        if frame is not None:
            frame_count += 1
            if frame_count == 1:
                print(f"    ✅ First frame received!")
        time.sleep(0.1)

    if frame_count > 0:
        print(f"    ✅ Received {frame_count} frames in 3 seconds")
        print("\n" + "=" * 60)
        print("SUCCESS! Camera is working properly")
        print("You can now start the backend server")
        print("=" * 60)
    else:
        print(f"    ❌ No frames received")
        print("\n" + "=" * 60)
        print("PROBLEM: Camera connects but doesn't send frames")
        print("This is likely a bootloader or firmware issue")
        print("=" * 60)

    try:
        device.close()
    except Exception:
        pass

except Exception as e:
    print(f"    ❌ Error: {e}")
    print("\n" + "=" * 60)
    print("FAILED: Could not connect to camera")
    print("=" * 60)
    raise

finally:
    try:
        release_lock()
    except Exception:
        pass
