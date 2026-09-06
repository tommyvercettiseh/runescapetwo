from __future__ import annotations

from actions.camera import set_compass as set_compass_module
from definitions.camera import compass as compass_module


class _Result:
    def __init__(self, success: bool = True) -> None:
        self.success = success

    def __bool__(self) -> bool:
        return self.success


def test_is_compass_north_uses_north_check_template(monkeypatch) -> None:
    calls = []

    def fake_find_image(*, image_name, area, bot_id):
        calls.append((image_name, area, bot_id))
        return object()

    monkeypatch.setattr(compass_module.vision, "find_image", fake_find_image)

    assert compass_module.is_compass_north(bot_id=2) is True
    assert calls == [("Compass_NorthCheck", "Compass_Area", 2)]


def test_set_compass_north_uses_left_click_and_rechecks(monkeypatch) -> None:
    checks = iter((False, True))
    clicks = []

    monkeypatch.setattr(
        set_compass_module,
        "is_compass_north",
        lambda *, bot_id: next(checks),
    )

    def fake_click_in_area(**kwargs):
        clicks.append(kwargs)
        return _Result()

    monkeypatch.setattr(
        set_compass_module.mouse_actions,
        "click_in_area",
        fake_click_in_area,
    )

    assert set_compass_module.set_compass("north", bot_id=1) is True
    assert clicks == [
        {
            "area_name": "Compass_Area",
            "bot_id": 1,
            "button": "left",
            "area_edge_padding": 4,
        }
    ]


def test_set_compass_south_uses_right_click_then_menu_image(monkeypatch) -> None:
    area_clicks = []
    image_clicks = []

    monkeypatch.setattr(set_compass_module.time, "sleep", lambda _seconds: None)

    def fake_click_in_area(**kwargs):
        area_clicks.append(kwargs)
        return _Result()

    def fake_click_image(**kwargs):
        image_clicks.append(kwargs)
        return _Result()

    monkeypatch.setattr(
        set_compass_module.mouse_actions,
        "click_in_area",
        fake_click_in_area,
    )
    monkeypatch.setattr(
        set_compass_module.mouse_actions,
        "click_image",
        fake_click_image,
    )

    assert set_compass_module.set_compass("south", bot_id=3) is True
    assert area_clicks[0]["area_name"] == "Compass_Area"
    assert area_clicks[0]["button"] == "right"
    assert image_clicks[0]["image_name"] == "Compass_South"
    assert image_clicks[0]["area_name"] == "Bot_Area_Full"


def test_set_compass_north_can_use_context_menu(monkeypatch) -> None:
    monkeypatch.setattr(set_compass_module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        set_compass_module.mouse_actions,
        "click_in_area",
        lambda **_kwargs: _Result(),
    )
    monkeypatch.setattr(
        set_compass_module.mouse_actions,
        "click_image",
        lambda **kwargs: _Result(kwargs["image_name"] == "Compass_North"),
    )
    monkeypatch.setattr(
        set_compass_module,
        "is_compass_north",
        lambda *, bot_id: True,
    )

    assert set_compass_module.set_compass("north", bot_id=1, via_menu=True) is True
