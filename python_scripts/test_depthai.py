from python_scripts.camera_lock import acquire_lock, release_lock
import depthai as dai

print('depthai version:', getattr(dai, '__version__', 'unknown'))

try:
    if hasattr(dai.Device, 'getAllAvailableDevices'):
        infos = dai.Device.getAllAvailableDevices()
        print('getAllAvailableDevices ->', infos)
    else:
        print('No getAllAvailableDevices() method on dai.Device')
except Exception as e:
    print('Error listing devices:', e)

ip = '10.2.100.51'
print('Testing network connect to', ip)
if not acquire_lock(timeout=3.0):
    print('Could not acquire camera lock; another process may own the device. Skipping network connect test.')
else:
    try:
        di = dai.Device(dai.DeviceInfo(ip))
        try:
            print('Connected:', di.getMxId(), di.getDeviceName())
        finally:
            di.close()
    except Exception as e:
        print('Network connect failed:', e)
    finally:
        try:
            release_lock()
        except Exception:
            pass
