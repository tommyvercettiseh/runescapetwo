from __future__ import annotations

from types import SimpleNamespace

import pytest

import core.mouse as mouse


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


@pytest.mark.parametrize("amount", (True, 1.5, "2"))
def test_scroll_rejects_non_integer_amount(amount: object) -> None:
    with pytest.raises(ValueError, match="integer"):
        mouse.scroll(amount)  # type: ignore[arg-type]
