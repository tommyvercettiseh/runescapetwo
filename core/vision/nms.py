from __future__ import annotations

import numpy as np


def find_candidates(
    score_map: np.ndarray,
    minimum_score: float,
    template_width: int,
    template_height: int,
    maximum_hits: int = 50,
) -> list[tuple[int, int, float]]:
    ys, xs = np.where(score_map >= float(minimum_score))
    if len(xs) == 0:
        return []

    order = np.argsort(score_map[ys, xs])[::-1]
    radius = max(5, int(min(template_width, template_height) * 0.5))
    selected: list[tuple[int, int, float]] = []

    for index in order:
        x = int(xs[index])
        y = int(ys[index])
        score = float(score_map[y, x])

        if any((x - px) ** 2 + (y - py) ** 2 <= radius**2 for px, py, _ in selected):
            continue

        selected.append((x, y, score))
        if len(selected) >= int(maximum_hits):
            break

    return selected
