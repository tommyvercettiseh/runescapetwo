from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "object_presets.json"


@dataclass(frozen=True)
class ObjectPreset:
    name: str
    colour: str
    min_pixels: int
    max_pixels: int | None
    area: str = "Bot_Area"
    edge_padding: float = 20
    button: str = "left"


def normalize_object_name(name: str) -> str:
    cleaned = str(name).strip().lower().replace(" ", "_")
    if not cleaned:
        raise ValueError("Object name is required")
    return cleaned


def _load_raw() -> dict[str, dict[str, object]]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("object_presets.json must contain an object")
    return data


def _save_raw(data: dict[str, dict[str, object]]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_PATH.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    temporary.replace(CONFIG_PATH)


def list_object_presets() -> tuple[str, ...]:
    return tuple(sorted(_load_raw()))


def load_object_preset(name: str) -> ObjectPreset:
    cleaned = normalize_object_name(name)
    raw = _load_raw()
    if cleaned not in raw:
        raise KeyError(f"Unknown object preset: {cleaned}")
    value = raw[cleaned]
    maximum = value.get("max_pixels")
    return ObjectPreset(
        name=cleaned,
        colour=str(value["colour"]),
        min_pixels=max(1, int(value["min_pixels"])),
        max_pixels=None if maximum in (None, 0) else max(1, int(maximum)),
        area=str(value.get("area", "Bot_Area")),
        edge_padding=float(value.get("edge_padding", 20)),
        button=str(value.get("button", "left")),
    )


def save_object_preset(
    name: str,
    *,
    colour: str,
    min_pixels: int,
    max_pixels: int | None,
    area: str = "Bot_Area",
    edge_padding: float = 20,
    button: str = "left",
) -> ObjectPreset:
    cleaned = normalize_object_name(name)
    minimum = max(1, int(min_pixels))
    maximum = None if max_pixels in (None, 0) else max(1, int(max_pixels))
    if maximum is not None and maximum < minimum:
        raise ValueError("max_pixels cannot be smaller than min_pixels")
    if button not in {"left", "right"}:
        raise ValueError("button must be left or right")

    preset = ObjectPreset(
        name=cleaned,
        colour=str(colour).strip(),
        min_pixels=minimum,
        max_pixels=maximum,
        area=str(area).strip() or "Bot_Area",
        edge_padding=float(edge_padding),
        button=button,
    )
    if not preset.colour:
        raise ValueError("Colour is required")

    raw = _load_raw()
    value = asdict(preset)
    value.pop("name")
    raw[cleaned] = value
    _save_raw(raw)
    return preset


def delete_object_preset(name: str) -> bool:
    cleaned = normalize_object_name(name)
    raw = _load_raw()
    if cleaned not in raw:
        return False
    del raw[cleaned]
    _save_raw(raw)
    return True


__all__ = [
    "CONFIG_PATH",
    "ObjectPreset",
    "delete_object_preset",
    "list_object_presets",
    "load_object_preset",
    "normalize_object_name",
    "save_object_preset",
]
