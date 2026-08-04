from tools.vision_tester.sensor_checks import SensorCheck
from tools.vision_tester import sensor_explanations


def test_colour_exists_explanation(monkeypatch):
    monkeypatch.setattr(sensor_explanations, "_count_colour_pixels", lambda *args, **kwargs: 6)
    explanation = sensor_explanations.explain_sensor(
        SensorCheck("low_hp", "colour_exists", "red", "HP_Area", 8),
        bot_id=2,
    )
    assert explanation.result is False
    assert ("Gevonden pixels", "6") in explanation.details
    assert ("Verschil", "-2") in explanation.details


def test_colour_blob_explanation(monkeypatch):
    class Blob:
        area_px = 824
        x = 100
        y = 200
        width = 30
        height = 40
        safe_point = (115, 220)

    monkeypatch.setattr(sensor_explanations.vision, "find_colour_blobs", lambda *args, **kwargs: [Blob()])
    explanation = sensor_explanations.explain_sensor(
        SensorCheck("blue_target_found", "colour_blob", "blue", "game", 500),
        bot_id=1,
    )
    assert explanation.result is True
    assert ("Grootste blob", "824 px") in explanation.details


def test_image_explanation_false(monkeypatch):
    monkeypatch.setattr(sensor_explanations.vision, "find_image", lambda *args, **kwargs: None)
    explanation = sensor_explanations.explain_sensor(
        SensorCheck("in_combat", "image_exists", "combat_icon.png", "game", 1),
        bot_id=1,
    )
    assert explanation.result is False
    assert any(label == "Reden" for label, _ in explanation.details)
