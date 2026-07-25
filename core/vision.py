from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pyautogui

from . import mouse
from .profile import get_section

ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = ROOT / "assets" / "images"
AREAS_FILE = ROOT / "config" / "areas.json"
TEMPLATES_FILE = ROOT / "config" / "templates_meta.json"

METHODS = {
    "TM_CCOEFF": cv2.TM_CCOEFF,
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR": cv2.TM_CCORR,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF": cv2.TM_SQDIFF,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}

_TEMPLATE_CACHE: dict[Path, tuple[np.ndarray, np.ndarray]] = {}


@dataclass(frozen=True)
class Hit:
    x: int
    y: int
    width: int
    height: int
    shape_score: float
    color_score: float
    method: str

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2

    @property
    def confidence(self) -> float:
        return min(self.shape_score, self.color_score) / 100.0

    def random_point(self, padding: int = 0) -> tuple[int, int]:
        padding = max(0, int(padding))
        left = self.x + padding
        top = self.y + padding
        right = self.x + self.width - padding - 1
        bottom = self.y + self.height - padding - 1
        if right < left or bottom < top:
            return self.center
        return random.randint(left, right), random.randint(top, bottom)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _normalize_name(image_name: str) -> str:
    return image_name if image_name.lower().endswith(".png") else f"{image_name}.png"


def _image_path(image_name: str) -> Path:
    path = IMAGES_DIR / _normalize_name(image_name)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    return path


def _template_settings(image_name: str) -> dict:
    metadata = _read_json(TEMPLATES_FILE)
    defaults = metadata.get("_defaults", {})
    name = _normalize_name(image_name)
    specific = metadata.get(name, metadata.get(Path(name).stem, {}))
    settings = {**defaults, **specific}

    method = str(settings.get("method", "TM_CCOEFF_NORMED"))
    if method != "ALL" and method not in METHODS:
        raise ValueError(f"Unknown template method: {method}")

    return {
        "method": method,
        "min_shape": float(settings.get("min_shape", 85.0)),
        "min_color": float(settings.get("min_color", 60.0)),
        "area": settings.get("area"),
    }


def get_area(name: str | None = None) -> tuple[int, int, int, int] | None:
    if name is None or name == "screen":
        return None
    area = _read_json(AREAS_FILE).get(name)
    if not isinstance(area, dict):
        raise KeyError(f"Unknown area: {name}")
    return int(area["x"]), int(area["y"]), int(area["width"]), int(area["height"])


def _read_template(image_name: str) -> tuple[np.ndarray, np.ndarray]:
    path = _image_path(image_name).resolve()
    if path in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[path]

    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Could not read image: {path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _TEMPLATE_CACHE[path] = (rgb, gray)
    return rgb, gray


def _score_map(result: np.ndarray, method: str) -> np.ndarray:
    score = cv2.normalize(result, None, 0.0, 1.0, cv2.NORM_MINMAX)
    return 1.0 - score if method.startswith("TM_SQDIFF") else score


def _color_score(template: np.ndarray, patch: np.ndarray) -> float:
    if patch.shape[:2] != template.shape[:2]:
        return 0.0
    difference = cv2.absdiff(template, patch)
    return float(np.clip(100.0 - np.mean(difference), 0.0, 100.0))


def _capture(area: str | None) -> tuple[np.ndarray, int, int]:
    region = get_area(area)
    if region is None:
        shot = np.array(pyautogui.screenshot())
        return shot, 0, 0
    x, y, width, height = region
    return np.array(pyautogui.screenshot(region=region)), x, y


def _best_match(image_name: str, area: str | None) -> Hit | None:
    settings = _template_settings(image_name)
    selected_area = area if area is not None else settings["area"]
    shot, offset_x, offset_y = _capture(selected_area)
    template_rgb, template_gray = _read_template(image_name)
    shot_gray = cv2.cvtColor(shot, cv2.COLOR_RGB2GRAY)
    height, width = template_gray.shape[:2]

    if shot_gray.shape[0] < height or shot_gray.shape[1] < width:
        return None

    methods = list(METHODS) if settings["method"] == "ALL" else [settings["method"]]
    best: Hit | None = None

    for method in methods:
        result = cv2.matchTemplate(shot_gray, template_gray, METHODS[method])
        score_map = _score_map(result, method)
        _, raw_score, _, location = cv2.minMaxLoc(score_map)
        x, y = map(int, location)
        patch = shot[y:y + height, x:x + width]
        shape_score = float(raw_score * 100.0)
        color_score = _color_score(template_rgb, patch)

        if shape_score < settings["min_shape"] or color_score < settings["min_color"]:
            continue

        hit = Hit(
            x=offset_x + x,
            y=offset_y + y,
            width=width,
            height=height,
            shape_score=round(shape_score, 2),
            color_score=round(color_score, 2),
            method=method,
        )
        if best is None or hit.confidence > best.confidence:
            best = hit

    return best


def find_image(image_name: str, *, area: str | None = None) -> Hit | None:
    """Find an image using its saved method, thresholds and optional area."""
    return _best_match(image_name, area)


def find_all_images(image_name: str, *, area: str | None = None, max_hits: int = 50) -> list[Hit]:
    settings = _template_settings(image_name)
    selected_area = area if area is not None else settings["area"]
    shot, offset_x, offset_y = _capture(selected_area)
    template_rgb, template_gray = _read_template(image_name)
    shot_gray = cv2.cvtColor(shot, cv2.COLOR_RGB2GRAY)
    height, width = template_gray.shape[:2]
    method = settings["method"] if settings["method"] != "ALL" else "TM_CCOEFF_NORMED"

    result = cv2.matchTemplate(shot_gray, template_gray, METHODS[method])
    score_map = _score_map(result, method)
    ys, xs = np.where(score_map >= settings["min_shape"] / 100.0)
    candidates = sorted(zip(xs, ys), key=lambda p: score_map[p[1], p[0]], reverse=True)

    hits: list[Hit] = []
    radius = max(5, min(width, height) // 2)
    for x, y in candidates:
        if any((x - (h.x - offset_x)) ** 2 + (y - (h.y - offset_y)) ** 2 <= radius ** 2 for h in hits):
            continue
        patch = shot[y:y + height, x:x + width]
        color_score = _color_score(template_rgb, patch)
        if color_score < settings["min_color"]:
            continue
        hits.append(Hit(offset_x + int(x), offset_y + int(y), width, height, round(float(score_map[y, x] * 100), 2), round(color_score, 2), method))
        if len(hits) >= max_hits:
            break
    return hits


def image_exists(image_name: str, *, area: str | None = None) -> bool:
    return find_image(image_name, area=area) is not None


def wait_for_image(image_name: str, *, area: str | None = None, timeout_s: float | None = None) -> Hit | None:
    settings = get_section("vision")
    timeout = float(timeout_s if timeout_s is not None else settings["timeout_s"])
    deadline = time.monotonic() + timeout
    while time.monotonic() <= deadline:
        hit = find_image(image_name, area=area)
        if hit is not None:
            return hit
        time.sleep(float(settings["poll_interval_s"]))
    return None


def wait_until_gone(image_name: str, *, area: str | None = None, timeout_s: float | None = None) -> bool:
    settings = get_section("vision")
    timeout = float(timeout_s if timeout_s is not None else settings["timeout_s"])
    deadline = time.monotonic() + timeout
    while time.monotonic() <= deadline:
        if not image_exists(image_name, area=area):
            return True
        time.sleep(float(settings["poll_interval_s"]))
    return False


def click_image(image_name: str, *, area: str | None = None, button: str = "left", wait: bool = False) -> bool:
    settings = get_section("vision")
    hit = wait_for_image(image_name, area=area) if wait else find_image(image_name, area=area)
    if hit is None:
        return False
    x, y = hit.random_point(int(settings["click_padding_px"]))
    mouse.move_to(x, y)
    mouse.click(button)
    return True
