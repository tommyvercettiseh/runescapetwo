import json

from tools.area_maker.store import EditableArea, load_editable_areas, save_editable_areas


def test_area_maker_loads_old_and_new_formats(tmp_path) -> None:
    path = tmp_path / "areas.json"
    path.write_text(
        json.dumps(
            {
                "HP_Area": {"coords": [10, 20, 40, 50], "group": "state"},
                "Inventory_Area": {"x": 100, "y": 200, "width": 80, "height": 120},
                "Legacy": [1, 2, 11, 22],
                "screen": None,
            }
        ),
        encoding="utf-8",
    )

    areas = load_editable_areas(path)

    assert areas["HP_Area"] == EditableArea("HP_Area", 10, 20, 30, 30, "state")
    assert areas["Inventory_Area"] == EditableArea("Inventory_Area", 100, 200, 80, 120)
    assert areas["Legacy"] == EditableArea("Legacy", 1, 2, 10, 20)
    assert "screen" not in areas


def test_area_maker_saves_canonical_regions(tmp_path) -> None:
    path = tmp_path / "areas.json"
    areas = {
        "HP_Area": EditableArea("HP_Area", 10, 20, 30, 40, "state"),
    }

    save_editable_areas(areas, path)
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert saved == {
        "HP_Area": {
            "x": 10,
            "y": 20,
            "width": 30,
            "height": 40,
            "group": "state",
        }
    }
