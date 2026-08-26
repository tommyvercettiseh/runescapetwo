from __future__ import annotations

import importlib

from definitions.login import logout_state
from definitions.login.logout_state import LogoutState


logout_action = importlib.import_module("actions.login.logout")


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
        lambda image_name, _bot_id: clicks.append(image_name) or True,
    )
    monkeypatch.setattr(logout_action.time, "sleep", lambda _seconds: None)

    assert logout_action.logout(
        bot_id=2,
        timeout_s=10.0,
        same_state_retry_s=5.0,
    )
    assert clicks == [
        logout_state.LOGOUT_DOOR_UNSELECTED_IMAGE,
        logout_state.INTERFACE_SCREEN_CROSS_IMAGE,
        logout_state.LOGOUT_CLICK_HERE_IMAGE,
    ]


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
        lambda image_name, _bot_id: clicks.append(image_name) or True,
    )
    monkeypatch.setattr(logout_action.time, "sleep", lambda _seconds: None)

    assert logout_action.logout(bot_id=1, timeout_s=10.0)
    assert clicks == []
