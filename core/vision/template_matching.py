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


def _window_sums(
    image: np.ndarray,
    template_height: int,
    template_width: int,
) -> tuple[np.ndarray, np.ndarray]:
    values = image.astype(np.float64)
    integral = cv2.integral(values)
    squared_integral = cv2.integral(values * values)

    def windows(source: np.ndarray) -> np.ndarray:
        return (
            source[template_height:, template_width:]
            - source[:-template_height, template_width:]
            - source[template_height:, :-template_width]
            + source[:-template_height, :-template_width]
        )

    return windows(integral), windows(squared_integral)


def _raw_denominator(
    screenshot_gray: np.ndarray,
    template_gray: np.ndarray,
    method_name: str,
) -> np.ndarray:
    height, width = template_gray.shape
    pixel_count = height * width
    patch_sum, patch_squared_sum = _window_sums(screenshot_gray, height, width)
    template = template_gray.astype(np.float64)

    if method_name == "TM_CCOEFF":
        template_energy = np.sum((template - np.mean(template)) ** 2)
        patch_energy = patch_squared_sum - (patch_sum * patch_sum / pixel_count)
        return np.sqrt(np.maximum(0.0, template_energy * patch_energy))

    template_squared_sum = float(np.sum(template * template))
    return np.sqrt(np.maximum(0.0, template_squared_sum * patch_squared_sum))


def _score_map(
    result: np.ndarray,
    method_name: str,
    screenshot_gray: np.ndarray | None = None,
    template_gray: np.ndarray | None = None,
) -> np.ndarray:
    if method_name == "TM_CCOEFF_NORMED":
        return np.clip(result, 0.0, 1.0)
    if method_name == "TM_CCORR_NORMED":
        return np.clip(result, 0.0, 1.0)
    if method_name == "TM_SQDIFF_NORMED":
        return np.clip(1.0 - result, 0.0, 1.0)

    if screenshot_gray is None or template_gray is None:
        raise ValueError(f"{method_name} scoring requires screenshot and template data")

    denominator = _raw_denominator(screenshot_gray, template_gray, method_name)
    if method_name == "TM_SQDIFF":
        distance = np.divide(
            result,
            denominator,
            out=np.ones_like(result, dtype=np.float64),
            where=denominator > 0,
        )
        quality = 1.0 - distance
    else:
        quality = np.divide(
            result,
            denominator,
            out=np.zeros_like(result, dtype=np.float64),
            where=denominator > 0,
        )
    return np.clip(quality, 0.0, 1.0).astype(np.float32)


def match_template(
    screenshot_gray: np.ndarray,
    template_gray: np.ndarray,
    method_name: str,
) -> np.ndarray:
    try:
        method = METHODS[method_name]
    except KeyError as exc:
        raise ValueError(f"Unknown template method: {method_name}") from exc

    if screenshot_gray.ndim != 2 or template_gray.ndim != 2:
        raise ValueError("Template matching requires grayscale images")
    if (
        template_gray.shape[0] > screenshot_gray.shape[0]
        or template_gray.shape[1] > screenshot_gray.shape[1]
    ):
        raise ValueError("Template cannot be larger than the screenshot")

    result = cv2.matchTemplate(screenshot_gray, template_gray, method)
    return _score_map(result, method_name, screenshot_gray, template_gray)


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
