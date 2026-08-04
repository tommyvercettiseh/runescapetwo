from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path

from core import vision

ROOT = Path(__file__).resolve().parents[2]
SENSOR_CHECKS_FILE = ROOT / "config" / "sensor_checks.json"
SUPPORTED_KINDS = ("colour_exists", "colour_blob", "image_exists")


@dataclass(frozen=True)
class SensorCheck:
    name: str
    kind: str
    value: str
    area: str
    threshold: int = 1
    enabled: bool = True


def _parse(name: str, raw: object) -> SensorCheck:
    if not isinstance(raw, dict):
        raise ValueError(f"Sensor '{name}' must be an object")
    kind = str(raw.get("kind", "")).strip()
    if kind not in SUPPORTED_KINDS:
        raise ValueError(f"Sensor '{name}' has unsupported kind: {kind}")
    value = str(raw.get("value", "")).strip()
    area = str(raw.get("area", "game")).strip() or "game"
    if not value:
        raise ValueError(f"Sensor '{name}' needs a colour or template value")
    return SensorCheck(
        name=str(name).strip(),
        kind=kind,
        value=value,
        area=area,
        threshold=max(1, int(raw.get("threshold", 1))),
        enabled=bool(raw.get("enabled", True)),
    )


def load_sensor_checks() -> dict[str, SensorCheck]:
    if not SENSOR_CHECKS_FILE.exists():
        return {}
    raw = json.loads(SENSOR_CHECKS_FILE.read_text(encoding="utf-8-sig") or "{}")
    if not isinstance(raw, dict):
        raise ValueError("sensor_checks.json must contain an object")
    return {name: _parse(name, item) for name, item in raw.items()}


def save_sensor_checks(checks: dict[str, SensorCheck]) -> None:
    payload = {
        name: {
            key: value
            for key, value in asdict(check).items()
            if key != "name"
        }
        for name, check in sorted(checks.items())
    }
    SENSOR_CHECKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = SENSOR_CHECKS_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(temporary, SENSOR_CHECKS_FILE)


def evaluate_sensor(check: SensorCheck, *, bot_id: int) -> bool:
    if check.kind == "colour_exists":
        return vision.colour_exists(
            check.value,
            area=check.area,
            bot_id=bot_id,
            minimum_pixels=check.threshold,
        )
    if check.kind == "colour_blob":
        return bool(
            vision.find_colour_blobs(
                check.value,
                area=check.area,
                bot_id=bot_id,
                minimum_area_px=check.threshold,
                maximum_area_px=None,
            )
        )
    if check.kind == "image_exists":
        return vision.image_exists(check.value, area=check.area, bot_id=bot_id)
    raise ValueError(f"Unsupported sensor kind: {check.kind}")
