#!/usr/bin/env python3
"""
OAK PoE static IP configuration helper.

This is intentionally non-interactive so backend services can repair the
camera network config after an Ubuntu reboot.
"""
from __future__ import annotations

import ipaddress
import time
from typing import Any, Optional


def _get_config_value(config: Any, key: str, default: Any = None) -> Any:
    if hasattr(config, "get"):
        try:
            return config.get(key, default)
        except TypeError:
            pass
    if isinstance(config, dict):
        return config.get(key, default)
    return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return default


def validate_ipv4(value: str, field_name: str = "IPv4") -> str:
    try:
        return str(ipaddress.IPv4Address(value.strip()))
    except Exception as exc:
        raise ValueError(f"{field_name} must be a valid IPv4 address: {value!r}") from exc


def default_gateway_for(ipv4: str) -> str:
    parts = validate_ipv4(ipv4).split(".")
    return ".".join(parts[:3] + ["1"])


def ensure_oak_poe_static_ip(
    config: Any,
    dai_module: Optional[Any] = None,
    *,
    logger=print,
) -> bool:
    """Flash static IPv4 config to a Luxonis OAK PoE device when enabled."""
    target_ip = str(_get_config_value(config, "network_camera_ip", "") or "").strip()
    enabled = _as_bool(
        _get_config_value(config, "oak_ip_config_on_startup", bool(target_ip)),
        default=bool(target_ip),
    )

    if not enabled:
        logger("[OAK IP] Startup IP configuration disabled")
        return False
    if not target_ip:
        logger("[OAK IP] No network_camera_ip configured; skipping PoE IP setup")
        return False

    target_ip = validate_ipv4(target_ip, "network_camera_ip")
    mask = validate_ipv4(
        str(_get_config_value(config, "oak_static_ip_mask", "255.255.255.0") or "255.255.255.0"),
        "oak_static_ip_mask",
    )
    gateway = validate_ipv4(
        str(_get_config_value(config, "oak_static_ip_gateway", "") or default_gateway_for(target_ip)),
        "oak_static_ip_gateway",
    )

    dai = dai_module
    if dai is None:
        import depthai as dai  # type: ignore

    if not hasattr(dai, "DeviceBootloader"):
        logger("[OAK IP] This depthai version does not expose DeviceBootloader; skipping")
        return False

    logger(f"[OAK IP] Checking for OAK bootloader device to set {target_ip}/{mask} via {gateway}")
    try:
        found, info = dai.DeviceBootloader.getFirstAvailableDevice()
    except Exception as exc:
        logger(f"[OAK IP] Bootloader discovery failed: {exc}")
        return False

    if not found:
        logger("[OAK IP] No bootloader device found; will continue normal camera connection")
        return False

    device_name = getattr(info, "name", "unknown")
    logger(f"[OAK IP] Found bootloader device: {device_name}")

    conf = dai.DeviceBootloader.Config()
    conf.setStaticIPv4(target_ip, mask, gateway)

    try:
        with dai.DeviceBootloader(info) as bootloader:
            success, error = bootloader.flashConfig(conf)
    except Exception as exc:
        logger(f"[OAK IP] Flash config failed: {exc}")
        return False

    if not success:
        logger(f"[OAK IP] Flash config failed: {error}")
        return False

    logger(f"[OAK IP] Static IP flashed successfully: {target_ip}, mask {mask}, gateway {gateway}")
    settle_seconds = float(_get_config_value(config, "oak_ip_config_settle_seconds", 5) or 5)
    if settle_seconds > 0:
        logger(f"[OAK IP] Waiting {settle_seconds:.1f}s for camera network restart")
        time.sleep(settle_seconds)
    return True


def main() -> int:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Set Luxonis OAK PoE static IP from JSON config")
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.json")))
    parser.add_argument("--ip", help="Override target IP")
    parser.add_argument("--mask", help="Override subnet mask")
    parser.add_argument("--gateway", help="Override gateway")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = {}
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))

    if args.ip:
        config["network_camera_ip"] = args.ip
    if args.mask:
        config["oak_static_ip_mask"] = args.mask
    if args.gateway:
        config["oak_static_ip_gateway"] = args.gateway
    config["oak_ip_config_on_startup"] = True

    flashed = ensure_oak_poe_static_ip(config)
    return 0 if flashed else 1


if __name__ == "__main__":
    raise SystemExit(main())
