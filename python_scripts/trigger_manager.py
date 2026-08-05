# -*- coding: utf-8 -*-
"""Snapshot trigger manager.

Fires a capture callback either on a fixed timer or on a rising edge of a
Siemens PLC signal read over snap7. Random size-checking on a conveyor is a
sampling job: the belt runs continuously, and we grab one frame when the timer
elapses or the PLC says "sample now".

snap7 is optional - if python-snap7 (or the Snap7 native lib) is missing, PLC
mode reports unavailable and timer mode still works.
"""
import threading
import time

try:
    import snap7
    from snap7.util import get_bool
    HAS_SNAP7 = True
except Exception:
    snap7 = None
    HAS_SNAP7 = False


class TriggerManager:
    def __init__(self, on_fire, config_store=None):
        """`on_fire` is called (no args) each time a trigger fires. `config_store`
        is the app system_config (optional) used to persist trigger settings."""
        self._on_fire = on_fire
        self._cfg = config_store

        self._thread = None
        self._running = False
        self._lock = threading.Lock()

        # Settings (overridable via configure()).
        self.mode = "off"          # "off" | "timer" | "plc"
        self.interval_s = 10.0      # timer mode period
        # PLC (snap7) settings
        self.plc_ip = ""
        self.plc_rack = 0
        self.plc_slot = 1
        self.plc_db = 1            # DB number to read
        self.plc_byte = 0          # byte offset of the trigger bit
        self.plc_bit = 0           # bit offset
        self.plc_poll_s = 0.2       # how often to poll the PLC

        # Runtime state
        self._plc = None
        self._plc_connected = False
        self._last_bit = False      # for rising-edge detection
        self._last_fire_ts = 0.0
        self._last_error = ""
        self._fire_count = 0

        if self._cfg is not None:
            self._load_from_config()

    # ---- config ----------------------------------------------------------
    def _load_from_config(self):
        g = self._cfg.get
        self.mode = g("trigger_mode", "off") or "off"
        self.interval_s = float(g("trigger_interval_s", 10) or 10)
        self.plc_ip = g("plc_ip", "") or ""
        self.plc_rack = int(g("plc_rack", 0) or 0)
        self.plc_slot = int(g("plc_slot", 1) or 1)
        self.plc_db = int(g("plc_db", 1) or 1)
        self.plc_byte = int(g("plc_byte", 0) or 0)
        self.plc_bit = int(g("plc_bit", 0) or 0)
        self.plc_poll_s = float(g("plc_poll_s", 0.2) or 0.2)

    def configure(self, **kw):
        """Update settings and persist them. Restarts the worker so changes
        take effect immediately."""
        for k in ("mode", "interval_s", "plc_ip", "plc_rack", "plc_slot",
                  "plc_db", "plc_byte", "plc_bit", "plc_poll_s"):
            if k in kw and kw[k] is not None:
                setattr(self, k, kw[k])
        # normalise types
        self.interval_s = float(self.interval_s)
        self.plc_rack = int(self.plc_rack); self.plc_slot = int(self.plc_slot)
        self.plc_db = int(self.plc_db); self.plc_byte = int(self.plc_byte)
        self.plc_bit = int(self.plc_bit); self.plc_poll_s = float(self.plc_poll_s)

        if self._cfg is not None:
            self._cfg.update({
                "trigger_mode": self.mode,
                "trigger_interval_s": self.interval_s,
                "plc_ip": self.plc_ip,
                "plc_rack": self.plc_rack,
                "plc_slot": self.plc_slot,
                "plc_db": self.plc_db,
                "plc_byte": self.plc_byte,
                "plc_bit": self.plc_bit,
                "plc_poll_s": self.plc_poll_s,
            }, auto_save=True)

        self.restart()

    def status(self):
        return {
            "mode": self.mode,
            "running": self._running,
            "interval_s": self.interval_s,
            "snap7_available": HAS_SNAP7,
            "plc": {
                "ip": self.plc_ip, "rack": self.plc_rack, "slot": self.plc_slot,
                "db": self.plc_db, "byte": self.plc_byte, "bit": self.plc_bit,
                "poll_s": self.plc_poll_s, "connected": self._plc_connected,
            },
            "fire_count": self._fire_count,
            "last_fire_ts": self._last_fire_ts,
            "last_error": self._last_error,
        }

    # ---- lifecycle -------------------------------------------------------
    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._loop, daemon=True, name="trigger")
            self._thread.start()

    def stop(self):
        self._running = False
        self._disconnect_plc()

    def restart(self):
        self.stop()
        time.sleep(0.3)
        if self.mode != "off":
            self.start()

    def fire_now(self, reason="manual"):
        """Fire the capture callback immediately (used by the manual button)."""
        self._fire(reason)

    # ---- internals -------------------------------------------------------
    def _fire(self, reason):
        self._last_fire_ts = time.time()
        self._fire_count += 1
        try:
            self._on_fire()
            print(f"[TRIGGER] fired ({reason}) #{self._fire_count}")
        except Exception as e:
            self._last_error = f"capture error: {e}"
            print(f"[TRIGGER] capture callback error: {e}")

    def _connect_plc(self):
        if not HAS_SNAP7:
            self._last_error = "snap7 not installed"
            return False
        try:
            if self._plc is None:
                self._plc = snap7.client.Client()
            if not self._plc.get_connected():
                self._plc.connect(self.plc_ip, self.plc_rack, self.plc_slot)
            self._plc_connected = self._plc.get_connected()
            if self._plc_connected:
                self._last_error = ""
            return self._plc_connected
        except Exception as e:
            self._plc_connected = False
            self._last_error = f"PLC connect: {e}"
            return False

    def _disconnect_plc(self):
        self._plc_connected = False
        try:
            if self._plc is not None:
                self._plc.disconnect()
        except Exception:
            pass

    def _read_plc_bit(self):
        data = self._plc.db_read(self.plc_db, self.plc_byte, 1)
        return bool(get_bool(data, 0, self.plc_bit))

    def _loop(self):
        print(f"[TRIGGER] worker started (mode={self.mode})")
        last_timer = time.time()
        self._last_bit = False
        while self._running:
            try:
                if self.mode == "timer":
                    if time.time() - last_timer >= self.interval_s:
                        last_timer = time.time()
                        self._fire("timer")
                    time.sleep(0.1)

                elif self.mode == "plc":
                    if not self._plc_connected and not self._connect_plc():
                        time.sleep(1.0)   # back off, keep retrying
                        continue
                    try:
                        bit = self._read_plc_bit()
                    except Exception as e:
                        self._last_error = f"PLC read: {e}"
                        self._disconnect_plc()
                        time.sleep(0.5)
                        continue
                    # Rising edge: fire only on 0 -> 1 transition.
                    if bit and not self._last_bit:
                        self._fire("plc")
                    self._last_bit = bit
                    time.sleep(max(0.05, self.plc_poll_s))

                else:  # off
                    time.sleep(0.3)
            except Exception as e:
                self._last_error = f"loop: {e}"
                time.sleep(1.0)
        print("[TRIGGER] worker stopped")
