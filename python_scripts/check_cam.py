import sys
VENV = '/home/pi/Desktop/Contaminate_chechk_Size-CM4/venv/bin/python3'

try:
    import depthai as dai
    print("depthai OK:", dai.__version__)
    devs = dai.Device.getAllAvailableDevices()
    print("devices found:", devs)
    if devs:
        print(">>> OAK camera DETECTED!")
    else:
        print(">>> No OAK devices found")
except Exception as e:
    print("depthai ERROR:", str(e))

try:
    import flask
    print("flask OK:", flask.__version__)
except Exception as e:
    print("flask ERROR:", str(e))

try:
    import cv2
    print("cv2 OK:", cv2.__version__)
except Exception as e:
    print("cv2 ERROR:", str(e))

try:
    import flask_socketio
    print("flask_socketio OK:", flask_socketio.__version__)
except Exception as e:
    print("flask_socketio ERROR:", str(e))

import subprocess
result = subprocess.run(['lsusb'], capture_output=True, text=True)
print("lsusb output:")
print(result.stdout)
