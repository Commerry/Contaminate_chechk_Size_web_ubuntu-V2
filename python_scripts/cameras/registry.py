# -*- coding: utf-8 -*-
"""Camera backend registry: discovery across vendors + backend construction."""
from .luxonis_backend import LuxonisBackend
from .hikvision_backend import HikvisionBackend

# Order = auto-select preference when no vendor is pinned.
BACKENDS = [LuxonisBackend, HikvisionBackend]

_BY_VENDOR = {B.vendor: B for B in BACKENDS}


def available_vendors():
    """Vendors whose SDK is importable on this host."""
    return [B.vendor for B in BACKENDS if B.is_available()]


def scan_all():
    """Discover every connected camera across all available vendors.

    Each vendor's SDK is probed independently; a missing/failing SDK is skipped,
    never fatal. Returns a flat list of device dicts (see CameraBackend.discover).
    """
    found = []
    for B in BACKENDS:
        try:
            if B.is_available():
                found.extend(B.discover())
        except Exception as e:
            print(f"[registry] {B.vendor} discover skipped: {e}")
    return found


def create_backend(vendor, system_config=None):
    """Instantiate a backend for the given vendor id, or None if unknown."""
    B = _BY_VENDOR.get((vendor or "").lower())
    if B is None:
        return None
    return B(system_config=system_config)


def auto_backend(system_config=None):
    """Pick the first available backend that has a device connected.

    Falls back to the first available backend even if discovery is empty (the
    device may appear by the time open() runs, e.g. a PoE camera still booting).
    """
    for B in BACKENDS:
        if not B.is_available():
            continue
        try:
            if B.discover():
                return B(system_config=system_config)
        except Exception:
            pass
    for B in BACKENDS:
        if B.is_available():
            return B(system_config=system_config)
    return None
