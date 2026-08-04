from tools.vision_tester import sensor_checks
from tools.vision_tester.sensor_checks import SensorCheck


def test_sensor_checks_roundtrip(tmp_path, monkeypatch) -> None:
    path = tmp_path / "sensor_checks.json"
    monkeypatch.setattr(sensor_checks, "SENSOR_CHECKS_FILE", path)
    checks = {
        "low_hp": SensorCheck(
            name="low_hp",
            kind="colour_exists",
            value="red",
            area="HP_Area",
            threshold=8,
        ),
        "blue_target_found": SensorCheck(
            name="blue_target_found",
            kind="colour_blob",
            value="blue",
            area="game",
            threshold=500,
        ),
    }

    sensor_checks.save_sensor_checks(checks)
    loaded = sensor_checks.load_sensor_checks()

    assert loaded == checks


def test_sensor_evaluation_uses_expected_vision_calls(monkeypatch) -> None:
    calls = []

    monkeypatch.setattr(
        sensor_checks.vision,
        "colour_exists",
        lambda colour, **kwargs: calls.append(("colour_exists", colour, kwargs)) or True,
    )
    monkeypatch.setattr(
        sensor_checks.vision,
        "find_colour_blobs",
        lambda colour, **kwargs: calls.append(("colour_blob", colour, kwargs)) or [object()],
    )
    monkeypatch.setattr(
        sensor_checks.vision,
        "image_exists",
        lambda template, **kwargs: calls.append(("image_exists", template, kwargs)) or False,
    )

    assert sensor_checks.evaluate_sensor(
        SensorCheck("low_hp", "colour_exists", "red", "HP_Area", 8), bot_id=2
    ) is True
    assert sensor_checks.evaluate_sensor(
        SensorCheck("blue_target_found", "colour_blob", "blue", "game", 500), bot_id=2
    ) is True
    assert sensor_checks.evaluate_sensor(
        SensorCheck("in_combat", "image_exists", "combat_icon.png", "game", 1), bot_id=2
    ) is False

    assert calls[0] == (
        "colour_exists",
        "red",
        {"area": "HP_Area", "bot_id": 2, "minimum_pixels": 8},
    )
    assert calls[1] == (
        "colour_blob",
        "blue",
        {
            "area": "game",
            "bot_id": 2,
            "minimum_area_px": 500,
            "maximum_area_px": None,
        },
    )
    assert calls[2] == (
        "image_exists",
        "combat_icon.png",
        {"area": "game", "bot_id": 2},
    )
