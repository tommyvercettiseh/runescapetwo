import numpy as np

from core.vision import screenshots


def test_capture_area_uses_one_absolute_region(monkeypatch):
    captured = []

    def fake_screenshot(*, region):
        captured.append(region)
        return np.zeros((region[3], region[2], 3), dtype=np.uint8)

    monkeypatch.setattr(screenshots.pyautogui, "screenshot", fake_screenshot)

    image, region = screenshots.capture_area("Inventory_Area", bot_id=2)

    assert region == (1958, 200, 250, 420)
    assert captured == [region]
    assert image.shape == (420, 250, 3)


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
