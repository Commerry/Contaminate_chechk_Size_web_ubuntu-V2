# -*- coding: utf-8 -*-
"""Hikvision machine-vision backend (MVS SDK).

Targets GigE/USB3 industrial cameras such as MV-CS016-10GC. Requires Hikvision
MVS runtime + its Python wrapper (`MvCameraControl_class` from MvImport). Until
that SDK is installed `is_available()` returns False and the registry skips
this backend, so importing the module never fails on a machine without MVS.

2D only (no depth) - sizing is pixel-calibration based.
"""
import numpy as np

try:
    # MVS ships MvImport/MvCameraControl_class.py; add it to PYTHONPATH or copy
    # it beside the app. Import is intentionally lazy/guarded.
    from MvCameraControl_class import (  # type: ignore
        MvCamera, MV_CC_DEVICE_INFO_LIST, MV_GIGE_DEVICE, MV_USB_DEVICE,
        MV_ACCESS_Exclusive, MVCC_INTVALUE, MV_FRAME_OUT,
    )
    HAS_MVS = True
except Exception:
    HAS_MVS = False

from .base import CameraBackend


class HikvisionBackend(CameraBackend):
    vendor = "hikvision"

    def __init__(self, system_config=None):
        self._cfg = system_config
        self._cam = None
        self._info = {}
        self._payload_size = 0

    @staticmethod
    def is_available():
        return HAS_MVS

    @staticmethod
    def discover():
        if not HAS_MVS:
            return []
        out = []
        try:
            dev_list = MV_CC_DEVICE_INFO_LIST()
            MvCamera.MV_CC_EnumDevices(MV_GIGE_DEVICE | MV_USB_DEVICE, dev_list)
            for i in range(dev_list.nDeviceNum):
                info = dev_list.pDeviceInfo[i].contents
                # Model/serial extraction differs GigE vs USB; best-effort here.
                try:
                    gige = info.SpecialInfo.stGigEInfo
                    ip = int(gige.nCurrentIp)
                    ip_str = f"{(ip>>24)&0xFF}.{(ip>>16)&0xFF}.{(ip>>8)&0xFF}.{ip&0xFF}"
                    model = bytes(gige.chModelName).partition(b"\x00")[0].decode(errors="ignore")
                    serial = bytes(gige.chSerialNumber).partition(b"\x00")[0].decode(errors="ignore")
                    dev_id = serial or ip_str
                    name = f"{model} ({ip_str})"
                except Exception:
                    usb = info.SpecialInfo.stUsb3VInfo
                    model = bytes(usb.chModelName).partition(b"\x00")[0].decode(errors="ignore")
                    serial = bytes(usb.chSerialNumber).partition(b"\x00")[0].decode(errors="ignore")
                    dev_id = serial
                    name = f"{model} (USB)"
                out.append({"id": dev_id, "name": name, "vendor": "hikvision",
                            "serial": serial, "_index": i})
        except Exception as e:
            print(f"[HIKVISION] discover error: {e}")
        return out

    def open(self, device_id=None, config=None):
        if not HAS_MVS:
            print("[HIKVISION] MVS SDK not available")
            return False
        try:
            dev_list = MV_CC_DEVICE_INFO_LIST()
            MvCamera.MV_CC_EnumDevices(MV_GIGE_DEVICE | MV_USB_DEVICE, dev_list)
            if dev_list.nDeviceNum == 0:
                print("[HIKVISION] no devices found")
                return False

            # Pick device matching serial/id, else first.
            idx = 0
            if device_id:
                for i in range(dev_list.nDeviceNum):
                    d = self.discover()
                    for e in d:
                        if e.get("id") == device_id:
                            idx = e.get("_index", 0)
                            break

            cam = MvCamera()
            cam.MV_CC_CreateHandle(dev_list.pDeviceInfo[idx].contents)
            if cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0) != 0:
                print("[HIKVISION] MV_CC_OpenDevice failed")
                return False

            # Continuous acquisition; set frame rate if requested.
            cam.MV_CC_SetEnumValue("TriggerMode", 0)

            # Let the camera self-adjust brightness/colour (Continuous auto).
            # Values: 0=Off, 1=Once, 2=Continuous. Ignore failures (node names
            # vary slightly by model/firmware).
            for node in ("ExposureAuto", "GainAuto", "BalanceWhiteAuto"):
                try:
                    cam.MV_CC_SetEnumValue(node, 2)
                except Exception:
                    pass

            fps = int((config or {}).get("fps", 0))
            if fps > 0:
                try:
                    cam.MV_CC_SetBoolValue("AcquisitionFrameRateEnable", True)
                    cam.MV_CC_SetFloatValue("AcquisitionFrameRate", float(fps))
                except Exception:
                    pass

            val = MVCC_INTVALUE()
            cam.MV_CC_GetIntValue("PayloadSize", val)
            self._payload_size = val.nCurValue

            if cam.MV_CC_StartGrabbing() != 0:
                print("[HIKVISION] MV_CC_StartGrabbing failed")
                cam.MV_CC_CloseDevice()
                return False

            self._cam = cam
            self._info = {"vendor": "hikvision", "payload": self._payload_size}
            print("[HIKVISION] grabbing started")
            return True
        except Exception as e:
            print(f"[HIKVISION] open error: {e}")
            return False

    def read(self):
        if self._cam is None:
            return None
        try:
            frame_out = MV_FRAME_OUT()
            # 100ms timeout; return None if nothing ready (non-blocking-ish).
            if self._cam.MV_CC_GetImageBuffer(frame_out, 100) != 0:
                return None
            try:
                info = frame_out.stFrameInfo
                buf = (np.ctypeslib.as_array(frame_out.pBufAddr,
                                             shape=(info.nFrameLen,))).copy()
                bgr = self._to_bgr(buf, info)
                return bgr
            finally:
                self._cam.MV_CC_FreeImageBuffer(frame_out)
        except Exception as e:
            print(f"[HIKVISION] read error: {e}")
            return None

    def _to_bgr(self, buf, info):
        """Convert a raw MVS frame to BGR. Handles the common Bayer/Mono cases;
        extend per the exact PixelType of MV-CS016-10GC once measured on-site."""
        import cv2
        h, w = info.nHeight, info.nWidth
        # nFrameLen == w*h -> single channel (mono or bayer); w*h*3 -> already RGB.
        if info.nFrameLen == w * h * 3:
            return cv2.cvtColor(buf.reshape(h, w, 3), cv2.COLOR_RGB2BGR)
        if info.nFrameLen == w * h:
            img = buf.reshape(h, w)
            # Assume BayerRG (common on colour Hik). Adjust if colours look wrong.
            try:
                return cv2.cvtColor(img, cv2.COLOR_BAYER_RG2BGR)
            except Exception:
                return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        # Fallback: let the SDK convert (slower). Not implemented here.
        return None

    def is_connected(self):
        return self._cam is not None

    def close(self):
        if self._cam is not None:
            try:
                self._cam.MV_CC_StopGrabbing()
                self._cam.MV_CC_CloseDevice()
                self._cam.MV_CC_DestroyHandle()
            except Exception:
                pass
            self._cam = None

    def get_info(self):
        return dict(self._info)
