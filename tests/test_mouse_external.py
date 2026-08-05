from __future__ import annotations

import os

os.environ.setdefault("PYNPUT_BACKEND", "dummy")

from core import mouse


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


def complete_plan():
    return {
        "events": [
            {"type": "move", "t_ms": 0.0, "x": 10, "y": 20},
            {"type": "move", "t_ms": 100.0, "x": 200, "y": 300},
            {"type": "button_down", "t_ms": 160.0, "x": 200, "y": 300},
            {"type": "button_up", "t_ms": 240.0, "x": 200, "y": 300},
        ]
    }


def prepare_external(monkeypatch, plan=None):
    controller = FakeController()
    monkeypatch.setattr(mouse, "_controller", controller)
    monkeypatch.setattr(mouse, "_screen_size", lambda: (1920, 1080))
    monkeypatch.setattr(mouse, "_wait_until", lambda deadline: None)
    monkeypatch.setattr(mouse.time, "perf_counter", lambda: 100.0)
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
        lambda *args, **kwargs: plan or complete_plan(),
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
        lambda *args, **kwargs: calls.append((args, kwargs)) or complete_plan(),
    )

    mouse.move_and_click_target(100, 120, 240, 220, padding_px=12)

    assert calls[0][0][1] == {"left": 100, "top": 120, "right": 240, "bottom": 220}
    assert calls[0][1]["padding_px"] == 12
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
