from __future__ import annotations

import numpy as np


def find_candidates(
    score_map: np.ndarray,
    minimum_score: float,
    template_width: int,
    template_height: int,
    maximum_hits: int = 50,
    overlap_threshold: float = 0.3,
) -> list[tuple[int, int, float]]:
    if template_width < 1 or template_height < 1:
        raise ValueError("Template width and height must be at least 1")
    if maximum_hits < 1:
        raise ValueError("maximum_hits must be at least 1")
    if not 0.0 <= overlap_threshold <= 1.0:
        raise ValueError("overlap_threshold must be between 0 and 1")

    ys, xs = np.where(score_map >= float(minimum_score))
    if len(xs) == 0:
        return []

    order = np.argsort(score_map[ys, xs])[::-1]
    selected: list[tuple[int, int, float]] = []
    box_area = template_width * template_height

    def overlaps(x: int, y: int, other_x: int, other_y: int) -> bool:
        overlap_width = max(
            0,
            min(x + template_width, other_x + template_width) - max(x, other_x),
        )
        overlap_height = max(
            0,
            min(y + template_height, other_y + template_height) - max(y, other_y),
        )
        intersection = overlap_width * overlap_height
        union = box_area * 2 - intersection
        return union > 0 and intersection / union > overlap_threshold

    for index in order:
        x = int(xs[index])
        y = int(ys[index])
        score = float(score_map[y, x])

        if any(overlaps(x, y, px, py) for px, py, _ in selected):
            continue

        selected.append((x, y, score))
        if len(selected) >= int(maximum_hits):
            break

    return selected
