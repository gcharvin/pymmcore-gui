from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pymmcore_gui._config_sidecar import (
    NIKON_PROFILE,
    apply_nikon_sidecar,
    sidecar_path,
)

if TYPE_CHECKING:
    from pathlib import Path


class _FakeCore:
    def __init__(self) -> None:
        self.properties: dict[tuple[str, str], str] = {}
        self.waited = False

    def getLoadedDevices(self) -> list[str]:
        return ["TIScope", "TIXYDrive"]

    def setProperty(self, device: str, prop: str, value: str) -> None:
        self.properties[(device, prop)] = value

    def waitForSystem(self) -> None:
        self.waited = True


def test_nikon_sidecar_forces_autoshutter(tmp_path: Path) -> None:
    cfg = tmp_path / "scope.cfg"
    cfg.write_text("", encoding="utf-8")
    sidecar_path(cfg).write_text(
        json.dumps(
            {
                "schema_version": 1,
                "profile": NIKON_PROFILE,
                "values": {"Core": {"AutoShutter": "0", "TimeoutMs": "1000"}},
            }
        ),
        encoding="utf-8",
    )

    mmc = _FakeCore()
    assert apply_nikon_sidecar(mmc, cfg)

    assert mmc.properties[("Core", "AutoShutter")] == "1"
    assert mmc.properties[("Core", "TimeoutMs")] == "1000"
    assert mmc.waited
