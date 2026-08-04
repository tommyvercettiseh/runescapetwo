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
