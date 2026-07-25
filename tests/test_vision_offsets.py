from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

import core
import core.bots as bots
import core.vision.api as api
import core.vision.offsets as offsets


@pytest.fixture(autouse=True)
def reset_active_bot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bots, "_active_bot_id", None)


def test_named_area_uses_bot_two_offset() -> None:
    region = offsets.apply_offset((10, 20, 100, 50), bot_id=2)

    assert region == (968, 20, 100, 50)


def test_screen_area_becomes_selected_bot_window() -> None:
    region = api.get_area("screen", bot_id=2)

    assert region == (958, 0, 1280, 720)


def test_public_get_area_is_bot_aware() -> None:
    assert api.get_area("game", bot_id=2) == (958, 0, 1280, 720)


def test_explicit_offset_overrides_active_bot() -> None:
    bots.set_bot(2)

    region = offsets.apply_offset(
        (10, 20, 100, 50),
        offset=(5, 7),
    )

    assert region == (15, 27, 100, 50)


def test_active_bot_is_used_without_repeating_bot_id() -> None:
    bots.set_bot(2)

    region = offsets.apply_offset((10, 20, 100, 50))

    assert region == (968, 20, 100, 50)


def test_bot_id_and_manual_offset_cannot_conflict() -> None:
    with pytest.raises(ValueError, match="either bot_id or offset"):
        offsets.apply_offset(
            (10, 20, 100, 50),
            bot_id=2,
            offset=(5, 7),
        )


def test_capture_uses_offset_and_returns_absolute_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[tuple[int, int, int, int] | None] = []
    monkeypatch.setattr(
        api,
        "load_settings",
        lambda _name: SimpleNamespace(area="game"),
    )
    monkeypatch.setattr(api, "get_base_area", lambda _name: (10, 20, 100, 50))
    monkeypatch.setattr(
        api,
        "capture_rgb",
        lambda region: captured.append(region) or np.zeros((50, 100, 3)),
    )
    monkeypatch.setattr(
        api,
        "load_template",
        lambda _name: (np.zeros((2, 2, 3)), np.zeros((2, 2))),
    )

    *_, origin = api._capture_for("bank", None, 2, None)

    assert captured == [(968, 20, 100, 50)]
    assert origin == (968, 20)


def test_image_exists_forwards_bot_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: dict = {}

    def fake_find_image(image_name: str, **kwargs):
        received.update(image_name=image_name, **kwargs)
        return object()

    monkeypatch.setattr(api, "find_image", fake_find_image)

    assert api.image_exists("bank", area="game", bot_id=2)
    assert received == {
        "image_name": "bank",
        "area": "game",
        "bot_id": 2,
        "offset": None,
    }


def test_wait_for_image_forwards_bot_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[dict] = []
    monkeypatch.setattr(
        api,
        "get_section",
        lambda _section: {"timeout_s": 0, "poll_interval_s": 0},
    )
    monkeypatch.setattr(
        api,
        "find_image",
        lambda _name, **kwargs: received.append(kwargs) or object(),
    )

    assert api.wait_for_image("bank", bot_id=2) is not None
    assert received == [{"area": None, "bot_id": 2, "offset": None}]


def test_wait_until_gone_forwards_bot_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[dict] = []
    monkeypatch.setattr(
        api,
        "get_section",
        lambda _section: {"timeout_s": 0, "poll_interval_s": 0},
    )
    monkeypatch.setattr(
        api,
        "image_exists",
        lambda _name, **kwargs: received.append(kwargs) or False,
    )

    assert api.wait_until_gone("bank", bot_id=2)
    assert received == [{"area": None, "bot_id": 2, "offset": None}]


def test_click_image_forwards_bot_and_uses_absolute_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[dict] = []
    actions: list[tuple] = []
    hit = SimpleNamespace(random_point=lambda padding: (1000, 200))
    fake_mouse = SimpleNamespace(
        move_to=lambda x, y: actions.append(("move", x, y)),
        click=lambda button: actions.append(("click", button)),
    )
    monkeypatch.setattr(core, "mouse", fake_mouse, raising=False)
    monkeypatch.setattr(
        api,
        "get_section",
        lambda _section: {"click_padding_px": 4},
    )
    monkeypatch.setattr(
        api,
        "find_image",
        lambda _name, **kwargs: received.append(kwargs) or hit,
    )

    assert api.click_image("bank", area="game", bot_id=2)
    assert received == [
        {
            "area": "game",
            "bot_id": 2,
            "offset": None,
        }
    ]
    assert actions == [("move", 1000, 200), ("click", "left")]
