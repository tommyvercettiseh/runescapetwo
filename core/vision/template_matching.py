from __future__ import annotations

from collections.abc import Iterator

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
    """Convert every OpenCV result to a stable 0..1 score map.

    Normalized methods keep their meaningful fixed range. Non-normalized
    methods use z-score peakiness instead of per-frame min/max normalization,
    which prevents a weak best pixel from being promoted to a perfect score.
    """
    values = result.astype(np.float32, copy=False)

    if method_name == "TM_CCOEFF_NORMED":
        return np.clip((values + 1.0) * 0.5, 0.0, 1.0)
    if method_name == "TM_CCORR_NORMED":
        return np.clip(values, 0.0, 1.0)
    if method_name == "TM_SQDIFF_NORMED":
        return np.clip(1.0 - values, 0.0, 1.0)

    mean = float(values.mean())
    standard_deviation = float(values.std())
    if standard_deviation < 1e-6:
        return np.full(values.shape, 0.5, dtype=np.float32)

    z_score = (values - mean) / standard_deviation
    if method_name == "TM_SQDIFF":
        z_score = -z_score

    z_score = np.clip(z_score, -12.0, 12.0)
    return (1.0 / (1.0 + np.exp(-z_score))).astype(np.float32)


def match_template(
    screenshot_gray: np.ndarray,
    template_gray: np.ndarray,
    method_name: str,
) -> np.ndarray:
    try:
        method = METHODS[method_name]
    except KeyError as exc:
        raise ValueError(f"Unknown template method: {method_name}") from exc

    if (
        screenshot_gray.shape[0] < template_gray.shape[0]
        or screenshot_gray.shape[1] < template_gray.shape[1]
    ):
        raise ValueError("Template is larger than the screenshot area")

    result = cv2.matchTemplate(screenshot_gray, template_gray, method)
    return _score_map(result, method_name)


def best_location(score_map: np.ndarray) -> tuple[int, int, float]:
    _, score, _, location = cv2.minMaxLoc(score_map)
    return int(location[0]), int(location[1]), round(float(score * 100.0), 2)


def iter_candidates(
    score_map: np.ndarray,
    minimum_score: float,
    template_width: int,
    template_height: int,
    *,
    maximum_candidates: int = 50,
    nms_radius: int | None = None,
) -> Iterator[tuple[int, int, float]]:
    """Yield strongest non-overlapping candidates without sorting every pixel."""
    if score_map.size == 0 or maximum_candidates <= 0:
        return

    work = score_map.astype(np.float32, copy=True)
    radius = (
        max(5, int(min(template_width, template_height) * 0.35))
        if nms_radius is None
        else max(1, int(nms_radius))
    )

    for _ in range(int(maximum_candidates)):
        _, score, _, location = cv2.minMaxLoc(work)
        if float(score) < float(minimum_score):
            break

        x, y = int(location[0]), int(location[1])
        yield x, y, float(score)
        cv2.circle(work, (x, y), radius, -1.0, thickness=-1)


def compare_methods(
    screenshot_gray: np.ndarray,
    template_gray: np.ndarray,
) -> dict[str, tuple[int, int, float]]:
    """Compare all methods for the image tester; production uses one preset."""
    return {
        method: best_location(match_template(screenshot_gray, template_gray, method))
        for method in METHODS
    }
