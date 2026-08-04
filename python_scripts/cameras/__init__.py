# -*- coding: utf-8 -*-
"""Camera abstraction layer.

One interface (`CameraBackend`) sits between the app and each vendor SDK so the
streaming/detection code never touches a vendor SDK directly. Backends are
discovered and created through `registry`.

Vendors: Luxonis (depthai), Hikvision (MVS SDK), Basler (pypylon).
All backends are 2D/RGB - object sizing comes from pixel*calibration, not depth.
"""
from .base import CameraBackend
from . import registry

__all__ = ["CameraBackend", "registry"]
