from __future__ import annotations

from typing import Any


def create_path(
    start: tuple[int, int],
    target: tuple[int, int],
    steps: int,
    settings: dict[str, Any] | None = None,
) -> list[tuple[int, int]]:
    """Create a simple straight path between two points."""
    start_x, start_y = start
    target_x, target_y = target
    steps = max(1, int(steps))

    return [
        (
            round(start_x + (target_x - start_x) * (step / steps)),
            round(start_y + (target_y - start_y) * (step / steps)),
        )
        for step in range(1, steps + 1)
    ]
