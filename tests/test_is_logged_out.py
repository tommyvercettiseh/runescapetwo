from definitions.login import is_logged_out as logout_module


def test_is_logged_out_true_when_disconnected_visible(monkeypatch):
    monkeypatch.setattr(
        logout_module.vision,
        "image_exists",
        lambda image_name, **_kwargs: image_name == logout_module.LOGIN_DISCONNECTED_IMAGE,
    )
    assert logout_module.is_logged_out() is True


def test_is_logged_out_true_when_world_selection_visible(monkeypatch):
    monkeypatch.setattr(
        logout_module.vision,
        "image_exists",
        lambda image_name, **_kwargs: image_name == logout_module.LOGIN_WORLD_SELECTION_IMAGE,
    )
    assert logout_module.is_logged_out() is True


def test_is_logged_out_true_when_both_visible(monkeypatch):
    monkeypatch.setattr(logout_module.vision, "image_exists", lambda *_args, **_kwargs: True)
    assert logout_module.is_logged_out() is True


def test_is_logged_out_false_when_neither_visible(monkeypatch):
    monkeypatch.setattr(logout_module.vision, "image_exists", lambda *_args, **_kwargs: False)
    assert logout_module.is_logged_out() is False
