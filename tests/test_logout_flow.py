from __future__ import annotations

import importlib

from definitions.login import logout_state
from definitions.login.logout_state import LogoutState


logout_action = importlib.import_module("actions.login.logout")
state_loop = importlib.import_module("actions.login.state_loop")
logged_out_definition = importlib.import_module("definitions.login.is_logged_out")


def test_world_selection_alone_is_not_logged_out(monkeypatch) -> None:
    visible = {logged_out_definition.LOGIN_WORLD_SELECTION_IMAGE}
    monkeypatch.setattr(
        logged_out_definition.vision,
        "image_exists",
        lambda image_name, **_kwargs: image_name in visible,
    )

    assert not logged_out_definition.is_logged_out(1)


def test_world_selection_plus_play_now_is_logged_out(monkeypatch) -> None:
    visible = {
        logged_out_definition.LOGIN_WORLD_SELECTION_IMAGE,
        logged_out_definition.LOGIN_PLAY_NOW_IMAGE,
    }
    monkeypatch.setattr(
        logged_out_definition.vision,
        "image_exists",
        lambda image_name, **_kwargs: image_name in visible,
    )

    assert logged_out_definition.is_logged_out(1)


def test_world_selection_plus_disconnected_is_logged_out(monkeypatch) -> None:
    visible = {
        logged_out_definition.LOGIN_WORLD_SELECTION_IMAGE,
        logged_out_definition.LOGIN_DISCONNECTED_IMAGE,
    }
    monkeypatch.setattr(
        logged_out_definition.vision,
        "image_exists",
        lambda image_name, **_kwargs: image_name in visible,
    )

    assert logged_out_definition.is_logged_out(1)


def test_selected_door_does_not_finish_on_world_selection_alone(monkeypatch) -> None:
    visible = {
        logged_out_definition.LOGIN_WORLD_SELECTION_IMAGE,
        logout_state.LOGOUT_DOOR_SELECTED_IMAGE,
    }
    monkeypatch.setattr(
        logout_state.vision,
        "image_exists",
        lambda image_name, **_kwargs: image_name in visible,
    )

    assert logout_state.get_logout_state(1) is LogoutState.MENU_OPEN


def test_logout_state_detects_blocking_interface(monkeypatch) -> None:
    visible = {
        logout_state.LOGOUT_DOOR_SELECTED_IMAGE,
        logout_state.INTERFACE_SCREEN_CROSS_IMAGE,
    }
    monkeypatch.setattr(
        logout_state.vision,
        "image_exists",
        lambda image_name, **_kwargs: image_name in visible,
    )

    assert logout_state.get_logout_state(1) is LogoutState.BLOCKED_BY_INTERFACE


def test_logout_button_takes_priority_over_blocking_interface(monkeypatch) -> None:
    visible = {
        logout_state.LOGOUT_DOOR_SELECTED_IMAGE,
        logout_state.INTERFACE_SCREEN_CROSS_IMAGE,
        logout_state.LOGOUT_CLICK_HERE_IMAGE,
    }
    monkeypatch.setattr(
        logout_state.vision,
        "image_exists",
        lambda image_name, **_kwargs: image_name in visible,
    )

    assert logout_state.get_logout_state(1) is LogoutState.READY_TO_LOGOUT


def test_logout_flow_closes_interface_then_logs_out(monkeypatch) -> None:
    stages = iter(
        (
            LogoutState.MENU_CLOSED,
            LogoutState.MENU_OPEN,
            LogoutState.BLOCKED_BY_INTERFACE,
            LogoutState.MENU_OPEN,
            LogoutState.READY_TO_LOGOUT,
            LogoutState.MENU_OPEN,
            LogoutState.LOGGED_OUT,
        )
    )
    clicks: list[tuple[str, bool]] = []

    monkeypatch.setattr(
        logout_action,
        "get_logout_state",
        lambda _bot_id: next(stages),
    )
    monkeypatch.setattr(
        logout_action,
        "_click",
        lambda image_name, _bot_id, *, confirm_before_click=True: (
            clicks.append((image_name, confirm_before_click)) or True
        ),
    )
    monkeypatch.setattr(state_loop.time, "sleep", lambda _seconds: None)

    assert logout_action.logout(
        bot_id=2,
        timeout_s=10.0,
        same_state_retry_s=0.0,
    )
    assert clicks == [
        (logout_state.LOGOUT_DOOR_UNSELECTED_IMAGE, False),
        (logout_state.INTERFACE_SCREEN_CROSS_IMAGE, True),
        (logout_state.LOGOUT_CLICK_HERE_IMAGE, False),
    ]


def test_hover_sensitive_logout_targets_skip_reconfirm(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        logout_action.mouse_actions,
        "click_image",
        lambda **kwargs: calls.append(kwargs) or True,
    )

    for image_name in (
        logout_state.LOGOUT_DOOR_UNSELECTED_IMAGE,
        logout_state.LOGOUT_CLICK_HERE_IMAGE,
    ):
        assert logout_action._click(
            image_name,
            3,
            confirm_before_click=False,
        )

    assert [call["confirm_before_click"] for call in calls] == [False, False]


def test_logout_never_exceeds_max_attempts_for_one_state(monkeypatch) -> None:
    stages = iter(
        (
            LogoutState.READY_TO_LOGOUT,
            LogoutState.READY_TO_LOGOUT,
            LogoutState.READY_TO_LOGOUT,
            LogoutState.READY_TO_LOGOUT,
            LogoutState.READY_TO_LOGOUT,
            LogoutState.LOGGED_OUT,
        )
    )
    clicks: list[str] = []

    monkeypatch.setattr(
        logout_action,
        "get_logout_state",
        lambda _bot_id: next(stages),
    )
    monkeypatch.setattr(
        logout_action,
        "_click",
        lambda image_name, _bot_id, **_kwargs: clicks.append(image_name) or True,
    )
    monkeypatch.setattr(state_loop.time, "sleep", lambda _seconds: None)

    assert logout_action.logout(
        bot_id=1,
        timeout_s=10.0,
        same_state_retry_s=0.0,
        max_attempts_per_state=3,
    )
    assert clicks == [logout_state.LOGOUT_CLICK_HERE_IMAGE] * 3


def test_logout_unknown_state_never_clicks(monkeypatch) -> None:
    stages = iter((LogoutState.UNKNOWN, LogoutState.LOGGED_OUT))
    clicks: list[str] = []

    monkeypatch.setattr(
        logout_action,
        "get_logout_state",
        lambda _bot_id: next(stages),
    )
    monkeypatch.setattr(
        logout_action,
        "_click",
        lambda image_name, _bot_id, **_kwargs: clicks.append(image_name) or True,
    )
    monkeypatch.setattr(state_loop.time, "sleep", lambda _seconds: None)

    assert logout_action.logout(bot_id=1, timeout_s=10.0)
    assert clicks == []
