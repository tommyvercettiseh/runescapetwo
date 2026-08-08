from tools.vision_tester.enhanced_config import MAX_ZOOM_PERCENT
from tools.vision_tester.preferences import load_preferences, save_preferences


def test_preferences_default_to_auto_resize(tmp_path) -> None:
    values = load_preferences(tmp_path / "missing.json")

    assert values == {
        "auto_resize": True,
        "zoom_percent": 100,
        "mouse_trace": False,
    }


def test_preferences_preserve_valid_deep_zoom(tmp_path) -> None:
    path = tmp_path / "vision.json"
    save_preferences(
        {"auto_resize": False, "zoom_percent": 500, "mouse_trace": True},
        path,
    )

    assert load_preferences(path) == {
        "auto_resize": False,
        "zoom_percent": 500,
        "mouse_trace": True,
    }


def test_preferences_clamp_zoom_to_supported_maximum(tmp_path) -> None:
    path = tmp_path / "vision.json"
    save_preferences({"zoom_percent": MAX_ZOOM_PERCENT * 10}, path)

    assert load_preferences(path)["zoom_percent"] == MAX_ZOOM_PERCENT
