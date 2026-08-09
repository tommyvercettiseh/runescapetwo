import importlib


login_module = importlib.import_module("definitions.login.is_logged_in")


def test_is_logged_in_requires_both_images(monkeypatch):
    calls = []

    def fake_image_exists(image_name, *, area=None, bot_id=None):
        calls.append((image_name, area, bot_id))
        return True

    monkeypatch.setattr(login_module.vision, "image_exists", fake_image_exists)

    assert login_module.is_logged_in(bot_id=2) is True
    assert calls == [
        (login_module.LOGIN_EXP_IMAGE, login_module.LOGIN_AREA, 2),
        (login_module.LOGIN_GLOBE_IMAGE, login_module.LOGIN_AREA, 2),
    ]


def test_is_logged_in_false_when_exp_missing(monkeypatch):
    monkeypatch.setattr(
        login_module.vision,
        "image_exists",
        lambda image_name, **_kwargs: image_name == login_module.LOGIN_GLOBE_IMAGE,
    )

    assert login_module.is_logged_in() is False


def test_is_logged_in_false_when_globe_missing(monkeypatch):
    monkeypatch.setattr(
        login_module.vision,
        "image_exists",
        lambda image_name, **_kwargs: image_name == login_module.LOGIN_EXP_IMAGE,
    )

    assert login_module.is_logged_in() is False


def test_is_logged_in_false_when_both_missing(monkeypatch):
    monkeypatch.setattr(login_module.vision, "image_exists", lambda *_args, **_kwargs: False)

    assert login_module.is_logged_in() is False
