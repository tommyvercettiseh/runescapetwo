from __future__ import annotations

import cv2
import numpy as np

METHODS = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}


def available_methods() -> tuple[str, ...]:
    return tuple(METHODS)


def _score_map(result: np.ndarray, method_name: str) -> np.ndarray:
    if method_name == "TM_CCOEFF_NORMED":
        return np.clip((result + 1.0) / 2.0, 0.0, 1.0)
    if method_name == "TM_CCORR_NORMED":
        return np.clip(result, 0.0, 1.0)
    if method_name == "TM_SQDIFF_NORMED":
        return np.clip(1.0 - result, 0.0, 1.0)

    normalized = cv2.normalize(result, None, 0.0, 1.0, cv2.NORM_MINMAX)
    if method_name == "TM_SQDIFF":
        normalized = 1.0 - normalized
    return normalized


def match_template(
    screenshot_gray: np.ndarray,
    template_gray: np.ndarray,
    method_name: str,
) -> np.ndarray:
    try:
        method = METHODS[method_name]
    except KeyError as exc:
        raise ValueError(f"Unknown template method: {method_name}") from exc

    result = cv2.matchTemplate(screenshot_gray, template_gray, method)
    return _score_map(result, method_name)


def best_location(score_map: np.ndarray) -> tuple[int, int, float]:
    _, score, _, location = cv2.minMaxLoc(score_map)
    return int(location[0]), int(location[1]), round(float(score * 100.0), 2)


def compare_methods(
    screenshot_gray: np.ndarray,
    template_gray: np.ndarray,
) -> dict[str, tuple[int, int, float]]:
    return {
        method: best_location(match_template(screenshot_gray, template_gray, method))
        for method in METHODS
    }
