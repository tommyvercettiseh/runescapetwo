from __future__ import annotations

from dataclasses import dataclass

from core import vision
from core.vision.colour_detection import build_mask_from_ranges, count_mask_pixels
from core.vision.colour_presets import load_colour_preset
from core.vision.screenshots import capture_area

from .sensor_checks import SensorCheck


@dataclass(frozen=True)
class SensorExplanation:
    result: bool
    title: str
    summary: str
    details: tuple[tuple[str, str], ...]


def _count_colour_pixels(colour: str, *, area: str, bot_id: int) -> int:
    preset = load_colour_preset(colour)
    screenshot, _ = capture_area(area, bot_id=bot_id)
    mask = build_mask_from_ranges(screenshot, preset.ranges)
    return count_mask_pixels(mask)


def explain_sensor(check: SensorCheck, *, bot_id: int) -> SensorExplanation:
    if check.kind == "colour_exists":
        pixels = _count_colour_pixels(check.value, area=check.area, bot_id=bot_id)
        result = pixels >= check.threshold
        return SensorExplanation(
            result=result,
            title=check.name,
            summary=f"{pixels} kleurpixels gevonden; minimaal {check.threshold} nodig.",
            details=(
                ("Resultaat", "TRUE" if result else "FALSE"),
                ("Bot", str(bot_id)),
                ("Area", check.area),
                ("Kleur", check.value),
                ("Gevonden pixels", str(pixels)),
                ("Benodigd", str(check.threshold)),
                ("Verschil", f"{pixels - check.threshold:+d}"),
            ),
        )

    if check.kind == "colour_blob":
        blobs = vision.find_colour_blobs(
            check.value,
            area=check.area,
            bot_id=bot_id,
            minimum_area_px=1,
            maximum_area_px=None,
        )
        largest = max((blob.area_px for blob in blobs), default=0)
        valid = [blob for blob in blobs if blob.area_px >= check.threshold]
        result = bool(valid)
        details = [
            ("Resultaat", "TRUE" if result else "FALSE"),
            ("Bot", str(bot_id)),
            ("Area", check.area),
            ("Kleur", check.value),
            ("Alle blobs", str(len(blobs))),
            ("Geldige blobs", str(len(valid))),
            ("Grootste blob", f"{largest} px"),
            ("Minimum", f"{check.threshold} px"),
            ("Verschil", f"{largest - check.threshold:+d} px"),
        ]
        if valid:
            blob = max(valid, key=lambda item: item.area_px)
            details.extend(
                (
                    ("Locatie", f"({blob.x}, {blob.y})"),
                    ("Formaat", f"{blob.width} × {blob.height}"),
                    ("Veilig punt", str(blob.safe_point)),
                )
            )
        return SensorExplanation(
            result=result,
            title=check.name,
            summary=(
                f"{len(valid)} geldige blob(s); grootste is {largest} px, "
                f"minimum is {check.threshold} px."
            ),
            details=tuple(details),
        )

    if check.kind == "image_exists":
        hit = vision.find_image(check.value, area=check.area, bot_id=bot_id)
        result = hit is not None
        details = [
            ("Resultaat", "TRUE" if result else "FALSE"),
            ("Bot", str(bot_id)),
            ("Area", check.area),
            ("Template", check.value),
        ]
        if hit is None:
            details.append(("Reden", "Geen kandidaat haalde shape én colour threshold"))
            summary = "Geen geldige image match gevonden."
        else:
            details.extend(
                (
                    ("Shape score", f"{hit.shape_score:.1f}%"),
                    ("Colour score", f"{hit.color_score:.1f}%"),
                    ("Methode", hit.method),
                    ("Locatie", f"({hit.x}, {hit.y})"),
                    ("Formaat", f"{hit.width} × {hit.height}"),
                )
            )
            summary = (
                f"Match gevonden met shape {hit.shape_score:.1f}% en "
                f"colour {hit.color_score:.1f}%."
            )
        return SensorExplanation(
            result=result,
            title=check.name,
            summary=summary,
            details=tuple(details),
        )

    raise ValueError(f"Unsupported sensor kind: {check.kind}")
