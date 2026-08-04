from tools.vision_tester.sensor_checks import SensorCheck
from tools.vision_tester.sensor_view import sensor_description


def test_colour_sensor_description_names_colour_and_area() -> None:
    check = SensorCheck(
        name="low_hp",
        kind="colour_exists",
        value="red",
        area="HP_Area",
        threshold=8,
    )

    assert sensor_description(check) == "Zoekt kleur 'red' in HP_Area."


def test_blob_sensor_description_explains_connected_area() -> None:
    check = SensorCheck(
        name="target",
        kind="colour_blob",
        value="blue",
        area="Bot_Area",
        threshold=20,
    )

    assert "aaneengesloten vlak" in sensor_description(check)


def test_image_sensor_description_names_template_and_area() -> None:
    check = SensorCheck(
        name="have_food",
        kind="image_exists",
        value="shark.png",
        area="inventory",
    )

    assert sensor_description(check) == "Zoekt afbeelding 'shark.png' in inventory."
