# Hikvision MV-CS016-10GC — MVS SDK setup (Phase 3)

The Hikvision backend (`python_scripts/cameras/hikvision_backend.py`) is already
in the app but stays disabled until the MVS SDK's Python wrapper is importable.
Once these steps are done, `GET /api/cameras/scan` lists `hikvision` and the
camera can be picked in **Settings → Camera Source**.

No depth is used anywhere — sizing is `pixel × calibration`, so a 2D GigE camera
is a drop-in.

## 1. Install MVS runtime (Ubuntu server)

Download **MVS** for Linux from Hikvision (machine-vision, "MVS_STD" package).
Install the matching arch (`.deb` or the `setup.sh`). Typical install root:
`/opt/MVS`.

```bash
sudo dpkg -i MVS-*.deb        # or: sudo /opt/MVS/setup.sh
```

The Python wrapper (`MvImport/MvCameraControl_class.py`) ships in the samples,
e.g. `/opt/MVS/Samples/64/Python/MvImport` (path varies by arch: `64`, `aarch64`).

## 2. Put MvImport on the service's PYTHONPATH

The backend imports `MvCameraControl_class` directly, so its folder must be on
`PYTHONPATH` for the systemd unit.

Find it:
```bash
find /opt/MVS -name MvCameraControl_class.py
```

Add to the service (edit `deploy/pse-vision.service` or the installed unit):
```ini
Environment=PYTHONPATH=/opt/MVS/Samples/aarch64/Python/MvImport
Environment=MVCAM_COMMON_RUNENV=/opt/MVS/lib
Environment=LD_LIBRARY_PATH=/opt/MVS/lib/aarch64:/opt/MVS/lib/64
```
(use the arch dir that actually exists on the box).

```bash
sudo systemctl daemon-reload
sudo systemctl restart pse-vision
```

Verify the SDK imports inside the app's venv:
```bash
PYTHONPATH=/opt/MVS/Samples/aarch64/Python/MvImport ./venv/bin/python - <<'PY'
import MvCameraControl_class as m
print("MVS OK", hasattr(m, "MvCamera"))
PY
```

## 3. Network (GigE) — same idea as the OAK PoE

MV-CS016-10GC is GigE. Give the host NIC an IP on the camera's subnet and raise
the MTU (jumbo frames) for full frame rate:
```bash
sudo ip addr add 192.168.2.10/24 dev <nic>
sudo ip link set <nic> mtu 9000
```
Assign the camera a static IP with MVS's IP Configurator, or via the SDK.

## 4. Use it

```bash
curl -s localhost:64021/api/cameras/scan     # should now include vendor "hikvision"
```
Web → **Settings → Camera Source → Scan** → pick the Hikvision camera → **Start Camera**.

Set a higher FPS by passing it through the connect config (default 15) — raise
`config={'fps': N}` in `initialize_oak_camera`, or expose it in settings later.

## 5. Colour / pixel format

`hikvision_backend._to_bgr()` currently assumes BayerRG for single-channel
frames. If the live image looks wrong (swapped colours / greyscale), read the
camera's actual `PixelType` and adjust the `cv2.cvtColor` conversion there:

- BayerRG8  → `cv2.COLOR_BAYER_RG2BGR`
- BayerGB8  → `cv2.COLOR_BAYER_GB2BGR`
- Mono8     → `cv2.COLOR_GRAY2BGR`
- RGB8      → `cv2.COLOR_RGB2BGR`

Or set the camera's PixelFormat to `RGB8`/`BGR8` in MVS so no debayering is
needed on the host.
