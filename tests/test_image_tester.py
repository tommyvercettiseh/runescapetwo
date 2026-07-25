from __future__ import annotations

import numpy as np
import pytest

import tools.image_tester.analyzer as analyzer


def test_analyzer_uses_selected_bot_area(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[tuple[int, int, int, int]] = []
    screenshot = np.zeros((20, 20, 3), dtype=np.uint8)
    template_rgb = np.zeros((2, 2, 3), dtype=np.uint8)
    template_gray = np.zeros((2, 2), dtype=np.uint8)
    monkeypatch.setattr(
        analyzer,
        "get_area",
        lambda area, *, bot_id: (
            received.append((960, 0, 960, 540))
            or (960, 0, 960, 540)
        ),
    )
    monkeypatch.setattr(analyzer, "capture_rgb", lambda _region: screenshot)
    monkeypatch.setattr(
        analyzer,
        "load_template",
        lambda _name: (template_rgb, template_gray),
    )
    monkeypatch.setattr(
        analyzer,
        "compare_methods",
        lambda *_args: {"TM_CCOEFF_NORMED": (3, 4, 95.0)},
    )
    monkeypatch.setattr(
        analyzer,
        "calculate_color_score",
        lambda *_args: 90.0,
    )

    rows = analyzer.analyze_template("bank", "game", bot_id=2)

    assert received == [(960, 0, 960, 540)]
    assert rows == [
        {
            "method": "TM_CCOEFF_NORMED",
            "x": 3,
            "y": 4,
            "shape_score": 95.0,
            "color_score": 90.0,
        }
    ]
