from __future__ import annotations

import cv2

from core.vision.areas import get_area
from core.vision.color_matching import calculate_color_score
from core.vision.screenshots import capture_rgb
from core.vision.template_matching import compare_methods
from core.vision.templates import load_template


def analyze_template(image_name: str, area: str | None = None) -> list[dict]:
    region = get_area(area)
    screenshot_rgb = capture_rgb(region)
    template_rgb, template_gray = load_template(image_name)
    screenshot_gray = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2GRAY)
    height, width = template_gray.shape[:2]

    rows: list[dict] = []
    for method, (x, y, shape_score) in compare_methods(screenshot_gray, template_gray).items():
        patch = screenshot_rgb[y : y + height, x : x + width]
        color_score = calculate_color_score(template_rgb, patch)
        rows.append(
            {
                "method": method,
                "x": x,
                "y": y,
                "shape_score": shape_score,
                "color_score": color_score,
            }
        )

    return rows
