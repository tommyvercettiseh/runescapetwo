from __future__ import annotations

from dataclasses import dataclass

import pytest

from core import mouse_actions


@dataclass(frozen=True)
class FakeHit:
    x: int = 100
    y: int = 200
    width: int = 100
    height: int = 40


def test_move_to_image_uses_named_area_and_safe_image_bounds(monkeypatch) -> None:
    finds = []
    moves = []
    monkeypatch.setattr(
        mouse_actions,
        "find_image",
        lambda image_name, **settings: finds.append((image_name, settings)) or FakeHit(),
    )
    monkeypatch.setattr(
        mouse_actions.mouse,
        "move_to_target",
        lambda left, top, right, bottom: moves.append((left, top, right, bottom)),
    )

    found = mouse_actions.move_to_image(
        "Logs",
        area_name="Bot_Area_Full",
        bot_id=2,
        image_edge_padding=20,
    )

    assert found is True
    assert finds == [("Logs", {"area": "Bot_Area_Full", "bot_id": 2})]
    assert moves == [(120, 200, 180, 240)]


def test_click_image_supports_right_click_without_duplicate_function(monkeypatch) -> None:
    clicks = []
    monkeypatch.setattr(mouse_actions, "find_image", lambda *values, **settings: FakeHit())
    monkeypatch.setattr(
        mouse_actions.mouse,
        "move_and_click_target",
        lambda left, top, right, bottom, *, button: clicks.append(
            (left, top, right, bottom, button)
        ),
    )

    found = mouse_actions.click_image("Logs", button="right")

    assert found is True
    assert clicks == [(120, 200, 180, 240, "right")]


def test_image_action_returns_false_when_image_is_absent(monkeypatch) -> None:
    monkeypatch.setattr(mouse_actions, "find_image", lambda *values, **settings: None)

    assert mouse_actions.move_to_image("Missing") is False


def test_wait_uses_readable_timeout_name(monkeypatch) -> None:
    waits = []
    moves = []
    monkeypatch.setattr(
        mouse_actions,
        "wait_for_image",
        lambda image_name, **settings: waits.append((image_name, settings)) or FakeHit(),
    )
    monkeypatch.setattr(
        mouse_actions.mouse,
        "move_to_target",
        lambda left, top, right, bottom: moves.append((left, top, right, bottom)),
    )

    assert mouse_actions.move_to_image("Logs", wait=True, timeout_seconds=8.5)
    assert waits == [
        (
            "Logs",
            {"area": "Bot_Area_Full", "bot_id": 1, "timeout_s": 8.5},
        )
    ]


def test_click_in_area_applies_absolute_bot_region_and_pixel_padding(monkeypatch) -> None:
    clicks = []
    monkeypatch.setattr(
        mouse_actions,
        "get_region",
        lambda area_name, *, bot_id: (1000, 200, 250, 420),
    )
    monkeypatch.setattr(
        mouse_actions.mouse,
        "move_and_click_target",
        lambda left, top, right, bottom, *, button: clicks.append(
            (left, top, right, bottom, button)
        ),
    )

    result = mouse_actions.click_in_area(
        "Inventory_Area",
        bot_id=3,
        button="left",
        area_edge_padding=10,
    )
    assert result is None
    assert clicks == [(1010, 210, 1240, 610, "left")]


def test_invalid_mouse_button_is_rejected() -> None:
    with pytest.raises(ValueError, match="left.*right"):
        mouse_actions.click_image("Logs", button="middle")


def test_invalid_timeout_is_rejected_before_detection() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        mouse_actions.move_to_image("Logs", wait=True, timeout_seconds=0)
