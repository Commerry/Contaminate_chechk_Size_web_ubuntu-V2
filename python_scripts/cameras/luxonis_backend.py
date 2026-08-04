# -*- coding: utf-8 -*-
"""Luxonis OAK backend (depthai).

RGB only - the stereo/depth path was removed since sizing is pixel-calibration
based. Supports OAK-D-CM4 (CSI), OAK-D (USB) and OAK-*-PoE (Network) by trying
the network IP first (when configured) then USB/CSI auto-detect.
"""
import time

try:
    import depthai as dai
    HAS_DEPTHAI = True
except Exception as _e:  # pragma: no cover - depends on host
    dai = None
    HAS_DEPTHAI = False

from .base import CameraBackend


class LuxonisBackend(CameraBackend):
    vendor = "luxonis"

    def __init__(self, system_config=None):
        # system_config is the app config manager (for auto-focus/exposure flags,
        # network IP...). Optional so the backend can be built standalone.
        self._cfg = system_config
        self._device = None
        self._pipeline = None
        self._queue = None
        self._info = {}

    # ---- discovery -------------------------------------------------------
    @staticmethod
    def is_available():
        return HAS_DEPTHAI

    @staticmethod
    def discover():
        if not HAS_DEPTHAI:
            return []
        out = []
        try:
            for d in dai.Device.getAllAvailableDevices():
                out.append({
                    "id": d.getMxId(),
                    "name": getattr(d, "name", "OAK Camera"),
                    "vendor": "luxonis",
                    "serial": d.getMxId(),
                    "state": d.state.name,
                    "protocol": d.protocol.name,
                })
        except Exception as e:
            print(f"[LUXONIS] discover error: {e}")
        return out

    # ---- lifecycle -------------------------------------------------------
    def _build_pipeline(self, config):
        pipeline = dai.Pipeline()
        try:
            pipeline.setXLinkChunkSize(0)  # PoE-recommended: one chunk, lower latency
        except Exception:
            pass

        cam = pipeline.create(dai.node.ColorCamera)
        cam.setPreviewSize(1280, 720)
        cam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_720_P)
        cam.setInterleaved(False)
        cam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
        cam.setFps(int((config or {}).get("fps", 15)))

        def flag(key, default=1):
            if self._cfg is None:
                return default
            return self._cfg.get(key, default)

        if flag("auto_focus") == 1:
            cam.initialControl.setAutoFocusMode(dai.CameraControl.AutoFocusMode.CONTINUOUS_VIDEO)
        if flag("auto_white_balance") == 1:
            cam.initialControl.setAutoWhiteBalanceMode(dai.CameraControl.AutoWhiteBalanceMode.AUTO)
        if flag("auto_exposure") == 1:
            cam.initialControl.setAutoExposureEnable()
            cam.initialControl.setAutoExposureLock(False)
            cam.initialControl.setAutoExposureRegion(0, 0, 65535, 65535)

        xout = pipeline.create(dai.node.XLinkOut)
        xout.setStreamName("rgb")
        cam.preview.link(xout.input)
        return pipeline

    def open(self, device_id=None, config=None):
        if not HAS_DEPTHAI:
            print("[LUXONIS] depthai not available")
            return False

        network_ip = ""
        if self._cfg is not None:
            network_ip = (self._cfg.get("network_camera_ip", "") or "").strip()
        # An explicit device_id that looks like an IP wins over config.
        if device_id and "." in str(device_id):
            network_ip = str(device_id)

        pipeline = self._build_pipeline(config)

        # Network first when an IP is known - USB scanning first wastes ~25s and
        # can disturb a PoE camera.
        if network_ip:
            methods = [("Network", network_ip), ("Auto", None)]
        else:
            methods = [("Auto", None), ("USB2", "usb2")]

        for name, arg in methods:
            for attempt in range(1, 4):
                try:
                    if name == "Network":
                        dev = dai.Device(pipeline, dai.DeviceInfo(arg))
                    elif name == "USB2":
                        dev = dai.Device(pipeline, dai.UsbSpeed.HIGH)
                    else:
                        dev = dai.Device(pipeline)
                    self._device = dev
                    self._pipeline = pipeline
                    self._queue = dev.getOutputQueue(name="rgb", maxSize=1, blocking=False)
                    try:
                        self._info = {
                            "vendor": "luxonis",
                            "name": dev.getDeviceName(),
                            "mxid": dev.getMxId(),
                            "connection": name,
                        }
                    except Exception:
                        self._info = {"vendor": "luxonis", "connection": name}
                    print(f"[LUXONIS] Connected via {name} ({self._info})")
                    return True
                except Exception as e:
                    print(f"[LUXONIS] {name} attempt {attempt}/3 failed: {str(e)[:60]}")
                    time.sleep(1.5)
        print("[LUXONIS] Could not connect to any OAK device")
        return False

    def read(self):
        if self._queue is None:
            return None
        try:
            pkt = self._queue.tryGet()
            # Drain backlog - latest frame wins.
            try:
                while self._queue.has():
                    pkt = self._queue.tryGet()
            except Exception:
                pass
            if pkt is None:
                return None
            return pkt.getCvFrame()
        except Exception as e:
            print(f"[LUXONIS] read error: {e}")
            return None

    def is_connected(self):
        try:
            return self._device is not None and not self._device.isClosed()
        except Exception:
            return False

    def close(self):
        self._queue = None
        self._pipeline = None
        if self._device is not None:
            try:
                if not self._device.isClosed():
                    self._device.close()
            except Exception:
                pass
            self._device = None

    def get_info(self):
        return dict(self._info)

    # Expose the raw device for code paths that still need it during migration.
    @property
    def device(self):
        return self._device
