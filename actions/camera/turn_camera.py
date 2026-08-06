from typing import Literal

from core import keyboard


CameraDirection = Literal["left", "right", "up", "down"]


DEFAULT_TURN_SECONDS = 0.20


def turn_camera(
    direction: CameraDirection,
    seconds: float = DEFAULT_TURN_SECONDS,
) -> None:
    if seconds <= 0:
        raise ValueError("seconds must be greater than 0")

    keyboard.hold(
        direction,
        duration_s=seconds,
    )
