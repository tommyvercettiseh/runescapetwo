from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from pathlib import Path

import pyautogui

from . import mouse
from .profile import get_section

ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = ROOT / "assets" / "images"
AREAS_FILE = ROOT / "config" / "areas.json"


@dataclass(frozen=True)
class Hit:
    x: int
    y: int
    width: int
    height: int
    confidence: float | None = None

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2

    def random_point(self, padding: int = 0) -> tuple[int, int]:
        padding = max(0, int(padding))
        left = self.x + padding
        top = self.y + padding
        right = self.x + self.width - padding - 1
        bottom = self.y + self.height - padding - 1

        if right < left or bottom < top:
            return self.center

        return random.randint(left, right), random.randint(top, bottom)


def _image_path(image_name: str) -> Path:
    name = image_name if image_name.lower().endswith(".png") else f"{image_name}.png"
    path = IMAGES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    return path


def _load_areas() -> dict:
    if not AREAS_FILE.exists():
        return {"screen": None}
    return json.loads(AREAS_FILE.read_text(encoding="utf-8"))


def get_area(name: str | None = None) -> tuple[int, int, int, int] | None:
    if name is None or name == "screen":
        return None

    area = _load_areas().get(name)
    if not isinstance(area, dict):
        raise KeyError(f"Unknown area: {name}")

    return (
        int(area["x"]),
        int(area["y"]),
        int(area["width"]),
        int(area["height"]),
    )


def find_image(
    image_name: str,
    *,
    area: str | None = None,
    confidence: float | None = None,
    grayscale: bool | None = None,
) -> Hit | None:
    settings = get_section("vision")
    box = pyautogui.locateOnScreen(
        str(_image_path(image_name)),
        region=get_area(area),
        confidence=float(confidence if confidence is not None else settings["confidence"]),
        grayscale=bool(grayscale if grayscale is not None else settings["grayscale"]),
    )

    if box is None:
        return None

    return Hit(int(box.left), int(box.top), int(box.width), int(box.height))


def find_all_images(
    image_name: str,
    *,
    area: str | None = None,
    confidence: float | None = None,
    grayscale: bool | None = None,
) -> list[Hit]:
    settings = get_section("vision")
    boxes = pyautogui.locateAllOnScreen(
        str(_image_path(image_name)),
        region=get_area(area),
        confidence=float(confidence if confidence is not None else settings["confidence"]),
        grayscale=bool(grayscale if grayscale is not None else settings["grayscale"]),
    )

    return [Hit(int(b.left), int(b.top), int(b.width), int(b.height)) for b in boxes]


def image_exists(image_name: str, *, area: str | None = None) -> bool:
    return find_image(image_name, area=area) is not None


def wait_for_image(
    image_name: str,
    *,
    area: str | None = None,
    timeout_s: float | None = None,
) -> Hit | None:
    settings = get_section("vision")
    timeout = float(timeout_s if timeout_s is not None else settings["timeout_s"])
    interval = float(settings["poll_interval_s"])
    deadline = time.monotonic() + timeout

    while time.monotonic() <= deadline:
        hit = find_image(image_name, area=area)
        if hit is not None:
            return hit
        time.sleep(interval)

    return None


def wait_until_gone(
    image_name: str,
    *,
    area: str | None = None,
    timeout_s: float | None = None,
) -> bool:
    settings = get_section("vision")
    timeout = float(timeout_s if timeout_s is not None else settings["timeout_s"])
    interval = float(settings["poll_interval_s"])
    deadline = time.monotonic() + timeout

    while time.monotonic() <= deadline:
        if not image_exists(image_name, area=area):
            return True
        time.sleep(interval)

    return False


def click_image(
    image_name: str,
    *,
    area: str | None = None,
    button: str = "left",
    wait: bool = False,
) -> bool:
    settings = get_section("vision")
    hit = wait_for_image(image_name, area=area) if wait else find_image(image_name, area=area)
    if hit is None:
        return False

    x, y = hit.random_point(int(settings["click_padding_px"]))
    mouse.move_to(x, y)
    mouse.click(button)
    return True
