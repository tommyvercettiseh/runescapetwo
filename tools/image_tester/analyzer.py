from __future__ import annotations

import cv2

from core.vision.areas import get_area
from core.vision.color_matching import calculate_color_score
from core.vision.offsets import apply_offset, get_bot_offset
from core.vision.screenshots import capture_rgb
from core.vision.template_matching import compare_methods
from core.vision.templates import load_template


def analyze_template(
    image_name: str,
    area: str | None = None,
    *,
    bot_id: int = 1,
) -> list[dict]:
    """Analyze all OpenCV methods inside the selected bot's absolute area."""
    local_region = get_area(area)
    region = apply_offset(local_region, get_bot_offset(bot_id))
    screenshot_rgb = capture_rgb(region)
    template_rgb, template_gray = load_template(image_name)
    screenshot_gray = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2GRAY)
    height, width = template_gray.shape[:2]

    if screenshot_gray.shape[0] < height or screenshot_gray.shape[1] < width:
        raise ValueError("Template is groter dan de geselecteerde screenshot-area")

    origin_x, origin_y = (0, 0) if region is None else (region[0], region[1])
    rows: list[dict] = []
    for method, (x, y, shape_score) in compare_methods(screenshot_gray, template_gray).items():
        patch = screenshot_rgb[y : y + height, x : x + width]
        if patch.shape[:2] != (height, width):
            continue
        color_score = calculate_color_score(template_rgb, patch)
        rows.append(
            {
                "method": method,
                "x": origin_x + x,
                "y": origin_y + y,
                "local_x": x,
                "local_y": y,
                "shape_score": shape_score,
                "color_score": color_score,
                "bot_id": bot_id,
                "region": region,
            }
        )

    return sorted(rows, key=lambda row: (row["shape_score"], row["color_score"]), reverse=True)
