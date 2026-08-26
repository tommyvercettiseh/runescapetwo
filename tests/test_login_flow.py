from __future__ import annotations

import importlib

from definitions.login import state as login_state
from definitions.login.state import LoginState
from tools.unified_tester import action_registry
from tools.unified_tester.action_registry import ActionContext


login_action = importlib.import_module("actions.login.login")


def test_login_state_detects_known_stages(monkeypatch) -> None:
    monkeypatch.setattr(login_state, "is_logged_in", lambda _bot_id: False)

    visible = {login_state.LOGIN_CONNECTING_IMAGE}
    monkeypatch.setattr(
        login_state.vision,
        "image_exists",
        lambda image_name, **_kwargs: image_name in visible,
    )
    assert login_state.get_login_state(2) is LoginState.CONNECTING

    visible.clear()
    visible.add(login_state.LOGIN_DISCONNECTED_IMAGE)
    assert login_state.get_login_state(2) is LoginState.DISCONNECTED

    visible.clear()
    visible.add(login_state.LOGIN_PLAY_NOW_IMAGE)
    assert login_state.get_login_state(2) is LoginState.PLAY_NOW

    visible.clear()
    visible.add(login_state.LOGIN_WORLD_SELECTION_IMAGE)
    assert login_state.get_login_state(2) is LoginState.HOME


def test_login_flow_only_clicks_actionable_stages(monkeypatch) -> None:
    stages = iter(
        (
            LoginState.HOME,
            LoginState.DISCONNECTED,
            LoginState.PLAY_NOW,
            LoginState.CONNECTING,
            LoginState.CLICK_HERE_TO_PLAY,
            LoginState.LOGGED_IN,
        )
    )
    clicks: list[str] = []

    monkeypatch.setattr(login_action, "get_login_state", lambda _bot_id: next(stages))
    monkeypatch.setattr(
        login_action,
        "_click",
        lambda image_name, _bot_id: clicks.append(image_name) or True,
    )
    monkeypatch.setattr(login_action.time, "sleep", lambda _seconds: None)

    assert login_action.login(
        bot_id=3,
        timeout_s=10.0,
        same_state_retry_s=0.0,
    )
    assert clicks == [
        login_state.LOGIN_OK_IMAGE,
        login_state.LOGIN_PLAY_NOW_IMAGE,
        login_state.LOGIN_CLICK_HERE_IMAGE,
    ]


def test_login_does_not_repeat_click_same_state_immediately(monkeypatch) -> None:
    stages = iter(
        (
            LoginState.PLAY_NOW,
            LoginState.PLAY_NOW,
            LoginState.PLAY_NOW,
            LoginState.LOGGED_IN,
        )
    )
    clicks: list[str] = []

    monkeypatch.setattr(login_action, "get_login_state", lambda _bot_id: next(stages))
    monkeypatch.setattr(
        login_action,
        "_click",
        lambda image_name, _bot_id: clicks.append(image_name) or True,
    )
    monkeypatch.setattr(login_action.time, "sleep", lambda _seconds: None)

    assert login_action.login(bot_id=1, timeout_s=10.0, same_state_retry_s=5.0)
    assert clicks == [login_state.LOGIN_PLAY_NOW_IMAGE]


def test_login_action_dry_run_only_reports_state(monkeypatch) -> None:
    monkeypatch.setattr(
        action_registry,
        "get_login_state",
        lambda _bot_id: LoginState.CONNECTING,
    )
    monkeypatch.setattr(
        action_registry,
        "login",
        lambda _bot_id: (_ for _ in ()).throw(AssertionError("login executed")),
    )

    result = action_registry.get_action("Login").execute(
        ActionContext(bot_id=4, dry_run=True)
    )
    assert result == {
        "action": "Login",
        "executed": False,
        "state": "connecting",
        "note": "Dry run. No input sent.",
    }
