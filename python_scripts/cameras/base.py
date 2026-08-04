# -*- coding: utf-8 -*-
"""Abstract camera backend interface.

Every vendor backend (Luxonis, Hikvision, Basler, ...) implements this so the
rest of the app can open a camera, pull BGR frames, and close it without caring
which SDK is underneath. There is no depth: sizing is pixel-calibration based.
"""
from abc import ABC, abstractmethod


class CameraBackend(ABC):
    # Subclasses set this to a short lowercase id: "luxonis" | "hikvision" | "basler"
    vendor = "unknown"

    @staticmethod
    @abstractmethod
    def is_available():
        """Return True if this vendor's SDK is importable on this host.

        Used by the registry to skip backends whose SDK is not installed
        instead of raising.
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def discover():
        """Return a list of connected devices for this vendor.

        Each entry is a dict: {id, name, vendor, serial}. `id` is whatever the
        backend needs in open() to select this device (IP, serial, index...).
        Never raises - return [] on any error.
        """
        raise NotImplementedError

    @abstractmethod
    def open(self, device_id=None, config=None):
        """Open the given device (or auto-select if device_id is None).

        `config` is a plain dict of vendor-agnostic hints (fps, resolution).
        Returns True on success, False otherwise. Never raises.
        """
        raise NotImplementedError

    @abstractmethod
    def read(self):
        """Return the newest frame as a BGR numpy array, or None if none ready.

        Must be non-blocking / latest-frame-wins so a slow consumer never stalls
        the device link.
        """
        raise NotImplementedError

    @abstractmethod
    def close(self):
        """Release the device. Safe to call more than once. Never raises."""
        raise NotImplementedError

    def is_connected(self):
        """Return True while the device is open and usable."""
        return False

    def get_info(self):
        """Return a dict describing the open device (model, resolution, fps...)."""
        return {"vendor": self.vendor}
