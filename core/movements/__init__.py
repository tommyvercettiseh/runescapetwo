from __future__ import annotations

from collections.abc import Callable

from .linear import create_path as linear_path

MovementFunction = Callable[
    [tuple[int, int], tuple[int, int], int],
    list[tuple[int, int]],
]

_MOVEMENTS: dict[str, MovementFunction] = {
    "linear": linear_path,
}


def register_movement(name: str, function: MovementFunction) -> None:
    """Register or replace a movement method by name."""
    clean_name = name.strip().lower()
    if not clean_name:
        raise ValueError("Movement name cannot be empty")
    _MOVEMENTS[clean_name] = function


def create_path(
    method: str,
    start: tuple[int, int],
    target: tuple[int, int],
    steps: int,
) -> list[tuple[int, int]]:
    clean_method = method.strip().lower()
    try:
        movement = _MOVEMENTS[clean_method]
    except KeyError as exc:
        available = ", ".join(sorted(_MOVEMENTS))
        raise ValueError(
            f"Unknown movement method '{method}'. Available: {available}"
        ) from exc

    return movement(start, target, steps)


def available_movements() -> tuple[str, ...]:
    return tuple(sorted(_MOVEMENTS))
