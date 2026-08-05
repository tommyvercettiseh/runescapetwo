from tools.vision_tester.preferences import load_preferences, save_preferences


def test_preferences_default_to_auto_resize(tmp_path) -> None:
    values = load_preferences(tmp_path / "missing.json")

    assert values == {
        "auto_resize": True,
        "zoom_percent": 100,
        "mouse_trace": False,
    }


def test_preferences_are_saved_and_zoom_is_bounded(tmp_path) -> None:
    path = tmp_path / "vision.json"
    save_preferences(
        {"auto_resize": False, "zoom_percent": 500, "mouse_trace": True},
        path,
    )

    assert load_preferences(path) == {
        "auto_resize": False,
        "zoom_percent": 100,
        "mouse_trace": True,
    }
