import numpy as np

from core.vision import screenshots
from core.vision.areas import get_region


def test_capture_area_uses_one_absolute_region(monkeypatch):
    captured = []

    def fake_capture_rgb(region):
        captured.append(region)
        return np.zeros((region[3], region[2], 3), dtype=np.uint8)

    monkeypatch.setattr(screenshots, "capture_rgb", fake_capture_rgb)

    image, region = screenshots.capture_area("Inventory_Area", bot_id=2)
    expected = get_region("Inventory_Area", bot_id=2)

    assert region == expected
    assert captured == [expected]
    assert image.shape == (expected[3], expected[2], 3)


def test_windows_capture_includes_secondary_monitors(monkeypatch):
    captured = []

    def fake_grab(*, bbox, all_screens):
        captured.append((bbox, all_screens))
        return np.zeros((200, 300, 3), dtype=np.uint8)

    monkeypatch.setattr(screenshots.sys, "platform", "win32")
    monkeypatch.setattr(screenshots.ImageGrab, "grab", fake_grab)

    image = screenshots.capture_rgb((-1200, 100, 300, 200))

    assert captured == [((-1200, 100, -900, 300), True)]
    assert image.shape == (200, 300, 3)
