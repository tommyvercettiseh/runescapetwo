from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

import core.mouse as mouse
from core.vision.models import ColourBlob


@pytest.fixture
def controller(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    fake = SimpleNamespace(position=(10, 20))
    monkeypatch.setattr(mouse, "_get_controller", lambda: fake)
    monkeypatch.setattr(mouse.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        mouse,
        "create_path",
        lambda _method, _start, target, _steps, _settings: [target],
    )
    return fake


def test_move_to_uses_absolute_coordinates(
    controller: SimpleNamespace,
) -> None:
    mouse.move_to(100, 200)

    assert controller.position == (100, 200)


def test_move_to_can_use_explicit_bot_relative_coordinates(
    controller: SimpleNamespace,
) -> None:
    mouse.move_to(100, 200, bot_id=2)

    assert controller.position == (1060, 200)


def test_absolute_mouse_target_must_stay_on_screen(
    controller: SimpleNamespace,
) -> None:
    with pytest.raises(ValueError, match="outside"):
        mouse.move_to(1920, 200)


def test_click_at_moves_then_clicks(monkeypatch: pytest.MonkeyPatch) -> None:
    actions: list[tuple] = []
    monkeypatch.setattr(
        mouse,
        "move_and_click",
        lambda x, y, button, *, bot_id: actions.append(
            (x, y, button, bot_id)
        ),
    )

    mouse.click_at(100, 200, "right", bot_id=2)

    assert actions == [(100, 200, "right", 2)]


def test_click_colour_uses_only_supplied_blob_pixels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actions: list[tuple] = []
    blob = ColourBlob(
        x=1000,
        y=100,
        width=10,
        height=10,
        pixel_count=100,
        clickable_points=np.array([[1004, 104], [1005, 105]], dtype=np.int32),
    )
    ignored_blob = ColourBlob(
        x=1100,
        y=100,
        width=10,
        height=10,
        pixel_count=100,
        clickable_points=np.array([[1104, 104]], dtype=np.int32),
    )
    monkeypatch.setattr(mouse.random, "randrange", lambda _total: 1)
    monkeypatch.setattr(
        mouse,
        "move_to",
        lambda x, y: actions.append(("move", x, y)),
    )
    monkeypatch.setattr(
        mouse,
        "click",
        lambda button: actions.append(("click", button)),
    )

    point = mouse.click_colour([blob], "right")

    assert point == (1005, 105)
    assert point not in map(tuple, ignored_blob.clickable_points)
    assert actions == [("move", 1005, 105), ("click", "right")]


def test_click_colour_returns_none_for_no_allowed_blobs() -> None:
    assert mouse.click_colour([]) is None


def test_click_colour_rejects_non_blobs() -> None:
    with pytest.raises(ValueError, match="ColourBlob"):
        mouse.click_colour([(100, 200)])  # type: ignore[list-item]


@pytest.mark.parametrize("amount", (True, 1.5, "2"))
def test_scroll_rejects_non_integer_amount(amount: object) -> None:
    with pytest.raises(ValueError, match="integer"):
        mouse.scroll(amount)  # type: ignore[arg-type]
