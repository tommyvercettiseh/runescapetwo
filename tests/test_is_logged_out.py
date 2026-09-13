import importlib


logout_module = importlib.import_module("definitions.login.is_logged_out")


def _visible(*names: str):
    visible = set(names)
    return lambda image_name, **_kwargs: image_name in visible


def test_world_selection_alone_is_not_logged_out(monkeypatch):
    monkeypatch.setattr(
        logout_module.vision,
        "image_exists",
        _visible(logout_module.LOGIN_WORLD_SELECTION_IMAGE),
    )
    assert logout_module.is_logged_out() is False


def test_disconnected_alone_is_not_logged_out(monkeypatch):
    monkeypatch.setattr(
        logout_module.vision,
        "image_exists",
        _visible(logout_module.LOGIN_DISCONNECTED_IMAGE),
    )
    assert logout_module.is_logged_out() is False


def test_world_selection_plus_disconnected_is_logged_out(monkeypatch):
    monkeypatch.setattr(
        logout_module.vision,
        "image_exists",
        _visible(
            logout_module.LOGIN_WORLD_SELECTION_IMAGE,
            logout_module.LOGIN_DISCONNECTED_IMAGE,
        ),
    )
    assert logout_module.is_logged_out() is True


def test_world_selection_plus_play_now_is_logged_out(monkeypatch):
    monkeypatch.setattr(
        logout_module.vision,
        "image_exists",
        _visible(
            logout_module.LOGIN_WORLD_SELECTION_IMAGE,
            logout_module.LOGIN_PLAY_NOW_IMAGE,
        ),
    )
    assert logout_module.is_logged_out() is True


def test_no_login_screen_images_is_not_logged_out(monkeypatch):
    monkeypatch.setattr(logout_module.vision, "image_exists", lambda *_args, **_kwargs: False)
    assert logout_module.is_logged_out() is False
