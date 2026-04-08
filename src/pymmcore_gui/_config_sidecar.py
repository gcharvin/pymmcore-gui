from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pymmcore_plus import CMMCorePlus

logger = logging.getLogger("pymmcore_gui")

SIDECAR_SUFFIX = ".pymmcore-gui.json"
NIKON_PROFILE = "nikon_tieclipse"
NIKON_SETTINGS = (
    ("AnalogIO", "Volts"),
    ("DA Shutter", "DA Device"),
    ("Core", "TimeoutMs"),
    ("TIXYDrive", "SpeedX"),
    ("TIXYDrive", "SpeedY"),
    ("Core", "ChannelGroup"),
)
NIKON_DEFAULTS: dict[str, dict[str, str]] = {"Core": {"TimeoutMs": "20000"}}
NIKON_FORCED_VALUES: dict[str, dict[str, str]] = {"Core": {"AutoShutter": "1"}}


def sidecar_path(cfg_path: str | Path) -> Path:
    path = Path(cfg_path)
    return path.with_name(f"{path.name}{SIDECAR_SUFFIX}")


def is_nikon_scope(mmc: CMMCorePlus, cfg_path: str | Path | None = None) -> bool:
    try:
        loaded = {str(x) for x in mmc.getLoadedDevices()}
    except Exception:
        loaded = set()
    if {"TIScope", "TIXYDrive"} & loaded:
        return True

    if cfg_path:
        try:
            text = Path(cfg_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return False
        return "Device,TIScope,NikonTI,TIScope" in text

    return False


def _get_property(mmc: CMMCorePlus, device: str, prop: str) -> str | None:
    try:
        return str(mmc.getProperty(device, prop))
    except Exception:
        return None


def save_nikon_sidecar(mmc: CMMCorePlus, cfg_path: str | Path) -> Path | None:
    if not is_nikon_scope(mmc, cfg_path):
        return None

    values: dict[str, dict[str, str]] = {}
    for device, prop in NIKON_SETTINGS:
        if value := _get_property(mmc, device, prop):
            values.setdefault(device, {})[prop] = value
    for device, props in NIKON_FORCED_VALUES.items():
        values.setdefault(device, {}).update(props)

    if not values:
        return None

    path = sidecar_path(cfg_path)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "profile": NIKON_PROFILE,
        "values": values,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def apply_nikon_sidecar(mmc: CMMCorePlus, cfg_path: str | Path) -> bool:
    if not is_nikon_scope(mmc, cfg_path):
        return False

    path = sidecar_path(cfg_path)
    if not path.exists():
        return False

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("Failed to read config sidecar: %s", path)
        return False

    if payload.get("profile") != NIKON_PROFILE:
        return False

    values = payload.get("values", {})
    merged_values: dict[str, dict[str, str]] = {
        dev: props.copy() for dev, props in NIKON_DEFAULTS.items()
    }
    if isinstance(values, dict):
        for device, props in values.items():
            if isinstance(props, dict):
                merged_values.setdefault(device, {}).update(
                    {str(prop): str(value) for prop, value in props.items()}
                )
    for device, props in NIKON_FORCED_VALUES.items():
        merged_values.setdefault(device, {}).update(props)

    applied = False
    for device, props in merged_values.items():
        for prop, value in props.items():
            try:
                mmc.setProperty(device, prop, str(value))
            except Exception:
                logger.exception("Failed to restore %s-%s from %s", device, prop, path)
            else:
                applied = True

    if applied:
        try:
            mmc.waitForSystem()
        except Exception:
            logger.exception("Failed while waiting after applying sidecar: %s", path)
    return applied
