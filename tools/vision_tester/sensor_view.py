from __future__ import annotations

from dataclasses import dataclass
import importlib
from pathlib import Path

import cv2
import numpy as np

from core.vision.color_matching import calculate_color_score
from core.vision.colour_detection import blobs_from_mask, build_mask_from_ranges, count_mask_pixels
from core.vision.colour_presets import load_colour_preset
from core.vision.template_matching import iter_candidates, match_template
from core.vision.templates import load_settings, load_template

from .sensor_checks import SensorCheck


@dataclass(frozen=True)
class SensorFrame:
    detected: np.ndarray
    found: int
    required: int
    result: bool
    unit: str


def _analyse_python_sensor(screenshot: np.ndarray, check: SensorCheck) -> SensorFrame:
    module = importlib.import_module(check.value)
    analyser = getattr(module, "analyse_frame", None)
    if not callable(analyser):
        raise ValueError(f"Python sensor '{check.value}' must expose analyse_frame(frame_rgb).")

    data = analyser(screenshot)
    if not isinstance(data, dict):
        raise ValueError(f"Python sensor '{check.value}' returned invalid analysis data.")

    detected = data.get("detected")
    if not isinstance(detected, np.ndarray):
        detected = screenshot.copy()

    return SensorFrame(
        detected=detected,
        found=int(data.get("found", 0)),
        required=max(1, int(data.get("required", 1))),
        result=bool(data.get("result", False)),
        unit=str(data.get("unit", "value")),
    )


def analyse_sensor_frame(
    screenshot: np.ndarray,
    check: SensorCheck,
    *,
    origin: tuple[int, int] = (0, 0),
) -> SensorFrame:
    if check.kind == "python_bool":
        return _analyse_python_sensor(screenshot, check)

    if check.kind in ("colour_exists", "colour_blob"):
        preset = load_colour_preset(check.value)
        mask = build_mask_from_ranges(screenshot, preset.ranges)
        detected = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)

        if check.kind == "colour_exists":
            found = count_mask_pixels(mask)
            return SensorFrame(detected, found, check.threshold, found >= check.threshold, "pixels")

        blobs = blobs_from_mask(
            mask,
            origin=origin,
            minimum_area_px=1,
            maximum_area_px=None,
        )
        found = max((blob.area_px for blob in blobs), default=0)
        return SensorFrame(detected, found, check.threshold, found >= check.threshold, "blob-pixels")

    if check.kind == "image_exists":
        template_rgb, template_gray = load_template(check.value)
        settings = load_settings(check.value)
        screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
        visual = screenshot.copy()
        height, width = template_gray.shape[:2]
        hits = 0

        if screenshot_gray.shape[0] >= height and screenshot_gray.shape[1] >= width:
            scores = match_template(screenshot_gray, template_gray, settings.method)
            for x, y, score in iter_candidates(
                scores,
                settings.min_shape / 100.0,
                width,
                height,
                maximum_candidates=30,
            ):
                patch = screenshot[y : y + height, x : x + width]
                if calculate_color_score(template_rgb, patch) < settings.min_color:
                    continue
                hits += 1
                cv2.rectangle(visual, (x, y), (x + width, y + height), (0, 220, 255), 2)
                cv2.putText(
                    visual,
                    f"{Path(check.value).stem} {score * 100.0:.0f}%",
                    (x, max(16, y - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 220, 255),
                    1,
                    cv2.LINE_AA,
                )
        return SensorFrame(visual, hits, 1, hits >= 1, "matches")

    raise ValueError(f"Niet ondersteund sensortype: {check.kind}")


def sensor_description(check: SensorCheck) -> str:
    if check.kind == "python_bool":
        return f"Python boolean sensor '{check.name}' uit {check.value}. Area: {check.area}."
    if check.kind == "colour_exists":
        return f"Zoekt kleur '{check.value}' in {check.area}."
    if check.kind == "colour_blob":
        return f"Zoekt één aaneengesloten vlak van kleur '{check.value}' in {check.area}."
    if check.kind == "image_exists":
        return f"Zoekt afbeelding '{check.value}' in {check.area}."
    return f"Controleert {check.area}."
