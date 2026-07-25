from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pytest

import core.vision.screenshots as screenshots


def test_capture_rejects_unexpected_windows_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = SimpleNamespace(size=lambda: (1280, 720))
    monkeypatch.setitem(sys.modules, "pyautogui", fake)
    monkeypatch.setattr(screenshots, "enable_dpi_awareness", lambda: None)

    with pytest.raises(RuntimeError, match="does not match"):
        screenshots.capture_rgb((0, 0, 100, 100))


def test_capture_uses_valid_screen_region(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[tuple[int, int, int, int] | None] = []
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    fake = SimpleNamespace(
        size=lambda: (1920, 1080),
        screenshot=lambda *, region: received.append(region) or image,
    )
    monkeypatch.setitem(sys.modules, "pyautogui", fake)
    monkeypatch.setattr(screenshots, "enable_dpi_awareness", lambda: None)

    result = screenshots.capture_rgb((960, 540, 100, 100))

    assert received == [(960, 540, 100, 100)]
    assert result.shape == (100, 100, 3)
