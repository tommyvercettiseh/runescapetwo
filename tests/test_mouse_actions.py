from __future__ import annotations

from dataclasses import dataclass

import pytest

from core import mouse_actions
from core.mouse import MouseExecutionStatus
from core.mouse_engine import MouseEngineUnavailable


@dataclass(frozen=True)
class FakeHit:
    x: int = 100
    y: int = 200
    width: int = 100
    height: int = 40


def prepare_success(monkeypatch, *, position=(150, 220)) -> None:
    monkeypatch.setattr(mouse_actions.mouse, "position", lambda: position)
    monkeypatch.setattr(
        mouse_actions.mouse,
        "last_execution_status",
        lambda: MouseExecutionStatus(engine="external"),
    )


def test_move_to_image_returns_diagnostics_and_prepares_click(monkeypatch) -> None:
    prepare_success(monkeypatch)
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
        lambda left, top, right, bottom, **settings: moves.append(
            ((left, top, right, bottom), settings)
        ),
    )

    result = mouse_actions.move_to_image(
        image_name="Logs",
        area_name="Bot_Area_Full",
        bot_id=2,
        image_edge_padding=20,
    )

    assert result.success is True
    assert bool(result) is True
    assert result.engine == "external"
    assert result.bounds == (120, 200, 180, 240)
    assert finds == [("Logs", {"area": "Bot_Area_Full", "bot_id": 2})]
    assert moves == [
        (
            (120, 200, 180, 240),
            {"require_external": True, "keep_pending_click": True},
        )
    ]


def test_click_image_supports_right_click_without_duplicate_function(monkeypatch) -> None:
    prepare_success(monkeypatch)
    clicks = []
    monkeypatch.setattr(mouse_actions, "find_image", lambda *values, **settings: FakeHit())
    monkeypatch.setattr(
        mouse_actions.mouse,
        "move_and_click_target",
        lambda left, top, right, bottom, **settings: clicks.append(
            ((left, top, right, bottom), settings)
        ),
    )

    result = mouse_actions.click_image(image_name="Logs", button="right")

    assert result.success is True
    assert clicks == [
        (
            (120, 200, 180, 240),
            {"button": "right", "require_external": True},
        )
    ]


def test_image_not_found_returns_readable_failure(monkeypatch) -> None:
    prepare_success(monkeypatch)
    monkeypatch.setattr(mouse_actions, "find_image", lambda *values, **settings: None)

    result = mouse_actions.move_to_image(image_name="Missing")

    assert result.success is False
    assert result.engine == "none"
    assert "niet gevonden" in result.message


def test_wait_uses_readable_timeout_name(monkeypatch) -> None:
    prepare_success(monkeypatch)
    waits = []
    monkeypatch.setattr(
        mouse_actions,
        "wait_for_image",
        lambda image_name, **settings: waits.append((image_name, settings)) or FakeHit(),
    )
    monkeypatch.setattr(mouse_actions.mouse, "move_to_target", lambda *values, **settings: None)

    result = mouse_actions.move_to_image(
        image_name="Logs",
        wait=True,
        timeout_seconds=8.5,
    )

    assert result.success is True
    assert waits == [
        (
            "Logs",
            {"area": "Bot_Area_Full", "bot_id": 1, "timeout_s": 8.5},
        )
    ]


def test_confirm_before_click_refuses_a_large_target_shift(monkeypatch) -> None:
    prepare_success(monkeypatch)
    hits = iter([FakeHit(), FakeHit(x=140)])
    clicks = []
    monkeypatch.setattr(mouse_actions, "find_image", lambda *values, **settings: next(hits))
    monkeypatch.setattr(mouse_actions.mouse, "move_to_target", lambda *values, **settings: None)
    monkeypatch.setattr(
        mouse_actions.mouse,
        "move_and_click_target",
        lambda *values, **settings: clicks.append((values, settings)),
    )

    result = mouse_actions.click_image(
        image_name="Moving",
        confirm_before_click=True,
        maximum_target_shift=12,
    )

    assert result.success is False
    assert "verschoof 40.0px" in result.message
    assert clicks == []


def test_click_in_area_applies_absolute_bot_region_and_pixel_padding(monkeypatch) -> None:
    prepare_success(monkeypatch, position=(1100, 400))
    clicks = []
    monkeypatch.setattr(
        mouse_actions,
        "get_region",
        lambda area_name, *, bot_id: (1000, 200, 250, 420),
    )
    monkeypatch.setattr(
        mouse_actions.mouse,
        "move_and_click_target",
        lambda left, top, right, bottom, **settings: clicks.append(
            ((left, top, right, bottom), settings)
        ),
    )

    result = mouse_actions.click_in_area(
        area_name="Inventory_Area",
        bot_id=3,
        button="left",
        area_edge_padding=10,
    )

    assert result.success is True
    assert clicks == [
        (
            (1010, 210, 1240, 610),
            {"button": "left", "require_external": True},
        )
    ]


def test_separate_click_requires_a_recent_move(monkeypatch) -> None:
    prepare_success(monkeypatch)
    monkeypatch.setattr(mouse_actions.mouse, "has_pending_click", lambda: False)
    clicks = []
    monkeypatch.setattr(
        mouse_actions.mouse,
        "click",
        lambda *values, **settings: clicks.append((values, settings)),
    )

    result = mouse_actions.click(button="left")

    assert result.success is False
    assert "voorbereidende move" in result.message
    assert clicks == []


def test_separate_click_uses_the_prepared_external_timeline(monkeypatch) -> None:
    prepare_success(monkeypatch)
    monkeypatch.setattr(mouse_actions.mouse, "has_pending_click", lambda: True)
    clicks = []
    monkeypatch.setattr(
        mouse_actions.mouse,
        "click",
        lambda button, *, require_pending: clicks.append((button, require_pending)),
    )

    result = mouse_actions.click(button="right")

    assert result.success is True
    assert clicks == [("right", True)]


def test_external_mouse_failure_is_visible_and_does_not_silently_fallback(monkeypatch) -> None:
    monkeypatch.setattr(mouse_actions, "find_image", lambda *values, **settings: FakeHit())
    monkeypatch.setattr(mouse_actions.mouse, "position", lambda: (50, 60))
    monkeypatch.setattr(
        mouse_actions.mouse,
        "last_execution_status",
        lambda: MouseExecutionStatus(
            engine="fallback",
            fallback_used=True,
            error="provider missing",
        ),
    )
    monkeypatch.setattr(
        mouse_actions.mouse,
        "move_to_target",
        lambda *values, **settings: (_ for _ in ()).throw(
            MouseEngineUnavailable("provider missing")
        ),
    )

    result = mouse_actions.move_to_image(image_name="Logs")

    assert result.success is False
    assert result.fallback_used is True
    assert result.error == "provider missing"


def test_invalid_public_parameters_fail_before_mouse_action() -> None:
    with pytest.raises(ValueError, match="left.*right"):
        mouse_actions.click_image(image_name="Logs", button="middle")
    with pytest.raises(ValueError, match="greater than zero"):
        mouse_actions.move_to_image(
            image_name="Logs",
            wait=True,
            timeout_seconds=0,
        )
    with pytest.raises(ValueError, match="non-negative"):
        mouse_actions.click_image(
            image_name="Logs",
            confirm_before_click=True,
            maximum_target_shift=-1,
        )
