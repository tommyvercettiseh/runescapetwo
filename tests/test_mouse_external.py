from __future__ import annotations

import os

import pytest

os.environ.setdefault("PYNPUT_BACKEND", "dummy")

from core import mouse
from core.mouse_engine import MouseEngineUnavailable


class FakeController:
    def __init__(self):
        self._position = (10, 20)
        self.positions = []
        self.pressed = []
        self.released = []

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        self._position = tuple(value)
        self.positions.append(tuple(value))

    def press(self, button):
        self.pressed.append(button)

    def release(self, button):
        self.released.append(button)

    def scroll(self, x, y):
        pass


def complete_plan(target_x=200, target_y=300):
    return {
        "events": [
            {"type": "move", "t_ms": 0.0, "x": 10, "y": 20},
            {"type": "move", "t_ms": 100.0, "x": target_x, "y": target_y},
            {"type": "button_down", "t_ms": 160.0, "x": target_x, "y": target_y},
            {"type": "button_up", "t_ms": 240.0, "x": target_x, "y": target_y},
        ]
    }


def plan_for_target(_start, target, **_settings):
    if isinstance(target, dict):
        target_x = (target["left"] + target["right"]) / 2
        target_y = (target["top"] + target["bottom"]) / 2
    else:
        target_x, target_y = target[:2]
    return complete_plan(target_x, target_y)


def prepare_external(monkeypatch, plan=None):
    controller = FakeController()
    monkeypatch.setattr(mouse, "_controller", controller)
    monkeypatch.setattr(mouse, "_screen_origin", lambda: (0, 0))
    monkeypatch.setattr(mouse, "_screen_size", lambda: (1920, 1080))
    monkeypatch.setattr(mouse, "_wait_until", lambda deadline: None)
    monkeypatch.setattr(mouse.time, "perf_counter", lambda: 100.0)
    mouse.reset_emergency_stop()
    mouse.cancel_pending_click()
    monkeypatch.setattr(
        mouse.mouse_engine,
        "load_settings",
        lambda: {
            "enabled": True,
            "fallback_on_error": True,
            "default_target_radius_px": 6,
        },
    )
    monkeypatch.setattr(
        mouse.mouse_engine,
        "create_plan",
        (lambda *args, **kwargs: plan) if plan is not None else plan_for_target,
    )
    return controller


def test_move_then_click_resumes_one_external_timeline(monkeypatch):
    controller = prepare_external(monkeypatch)

    mouse.move_to(200, 300)
    assert controller.positions == [(10, 20), (200, 300)]
    assert controller.pressed == []

    mouse.click()
    assert len(controller.pressed) == 1
    assert len(controller.released) == 1


def test_move_and_click_executes_complete_external_plan(monkeypatch):
    controller = prepare_external(monkeypatch)

    mouse.move_and_click(200, 300)

    assert controller.positions[-1] == (200, 300)
    assert len(controller.pressed) == 1
    assert len(controller.released) == 1


def test_target_rectangle_and_padding_are_passed_to_provider(monkeypatch):
    calls = []
    controller = prepare_external(monkeypatch)
    monkeypatch.setattr(
        mouse.mouse_engine,
        "create_plan",
        lambda *args, **kwargs: calls.append((args, kwargs))
        or plan_for_target(*args, **kwargs),
    )

    mouse.move_and_click_target(100, 120, 240, 220, padding_px=12)

    assert calls[0][0][1] == {"left": 100, "top": 120, "right": 240, "bottom": 220}
    assert calls[0][1]["padding_px"] == 12
    assert len(controller.pressed) == 1


def test_external_provider_uses_virtual_desktop_coordinates(monkeypatch):
    calls = []
    controller = prepare_external(monkeypatch)
    controller._position = (-1000, 200)
    monkeypatch.setattr(mouse, "_screen_origin", lambda: (-1920, 0))
    monkeypatch.setattr(mouse, "_screen_size", lambda: (3840, 1080))

    def create_virtual_desktop_plan(start, target, **settings):
        calls.append((start, target, settings))
        return {
            "events": [
                {"type": "move", "t_ms": 0, "x": start[0], "y": start[1]},
                {"type": "move", "t_ms": 50, "x": 1120, "y": 350},
                {"type": "button_down", "t_ms": 70, "x": 1120, "y": 350},
                {"type": "button_up", "t_ms": 90, "x": 1120, "y": 350},
            ]
        }

    monkeypatch.setattr(mouse.mouse_engine, "create_plan", create_virtual_desktop_plan)

    mouse.move_and_click_target(
        -900,
        250,
        -700,
        450,
        require_external=True,
    )

    assert calls[0][0] == (920, 200)
    assert calls[0][1] == {
        "left": 1020.0,
        "top": 250.0,
        "right": 1220.0,
        "bottom": 450.0,
    }
    assert calls[0][2]["coordinate_size"] == (3840, 1080)
    assert controller.positions[-1] == (-800, 350)
    assert len(controller.pressed) == 1


def test_external_failure_uses_native_fallback(monkeypatch):
    prepare_external(monkeypatch)
    monkeypatch.setattr(
        mouse.mouse_engine,
        "create_plan",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("provider broke")),
    )
    moved = []
    clicked = []
    monkeypatch.setattr(mouse, "_native_move_to", lambda x, y, method=None: moved.append((x, y)))
    monkeypatch.setattr(mouse, "_native_click", lambda button="left": clicked.append(button))

    mouse.move_and_click(50, 60)

    assert moved == [(50, 60)]
    assert clicked == ["left"]
    assert mouse.last_engine_error() == "provider broke"


def test_required_external_engine_never_falls_back_silently(monkeypatch):
    prepare_external(monkeypatch)
    monkeypatch.setattr(
        mouse.mouse_engine,
        "create_plan",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("provider broke")),
    )
    native_moves = []
    monkeypatch.setattr(
        mouse,
        "_native_move_to",
        lambda *args, **kwargs: native_moves.append((args, kwargs)),
    )

    with pytest.raises(MouseEngineUnavailable, match="provider broke"):
        mouse.move_to(50, 60, require_external=True)

    assert native_moves == []
    assert mouse.last_execution_status().fallback_used is True


def test_unsafe_external_plan_is_rejected_before_mouse_moves(monkeypatch):
    unsafe = complete_plan(target_x=2000, target_y=300)
    controller = prepare_external(monkeypatch, plan=unsafe)

    with pytest.raises(MouseEngineUnavailable, match="unsafe plan"):
        mouse.move_and_click(200, 300, require_external=True)

    assert controller.positions == []
    assert controller.pressed == []


def test_pending_click_expires_instead_of_clicking_a_stale_target(monkeypatch):
    prepare_external(monkeypatch)
    current_time = [100.0]
    monkeypatch.setattr(mouse.time, "perf_counter", lambda: current_time[0])

    mouse.move_to(200, 300)
    assert mouse.has_pending_click() is True

    current_time[0] += mouse.PENDING_CLICK_TIMEOUT_S + 0.1
    assert mouse.has_pending_click() is False
    with pytest.raises(mouse.PendingClickUnavailable):
        mouse.click(require_pending=True)


def test_pending_click_is_cancelled_if_cursor_left_the_target(monkeypatch):
    controller = prepare_external(monkeypatch)

    mouse.move_to(200, 300)
    controller.position = (500, 500)

    assert mouse.has_pending_click() is False
    with pytest.raises(mouse.PendingClickUnavailable):
        mouse.click(require_pending=True)


def test_separate_click_restarts_remaining_provider_timing(monkeypatch):
    controller = prepare_external(monkeypatch)
    current_time = [100.0]
    deadlines = []
    monkeypatch.setattr(mouse.time, "perf_counter", lambda: current_time[0])
    monkeypatch.setattr(mouse, "_wait_until", lambda deadline: deadlines.append(deadline))

    mouse.move_to(200, 300)
    movement_deadlines = list(deadlines)
    current_time[0] = 102.0
    mouse.click(require_pending=True)

    assert movement_deadlines == [100.0, 100.1]
    assert deadlines[-2:] == pytest.approx([102.06, 102.14])
    assert len(controller.pressed) == 1


def test_emergency_stop_releases_a_pressed_button(monkeypatch):
    controller = FakeController()
    monkeypatch.setattr(mouse, "_controller", controller)
    monkeypatch.setattr(mouse, "_wait_until", lambda deadline: None)
    monkeypatch.setattr(mouse, "_timer_resolution", lambda enable: None)
    original_press = controller.press

    def press_and_stop(button):
        original_press(button)
        mouse.request_emergency_stop()

    controller.press = press_and_stop
    mouse.reset_emergency_stop()

    with pytest.raises(mouse.MouseActionCancelled):
        mouse._execute_events(
            [
                {"type": "button_down", "t_ms": 0, "x": 100, "y": 100},
                {"type": "button_up", "t_ms": 10, "x": 100, "y": 100},
            ],
            started_at=0,
        )

    assert len(controller.pressed) == 1
    assert len(controller.released) == 1
    mouse.reset_emergency_stop()
