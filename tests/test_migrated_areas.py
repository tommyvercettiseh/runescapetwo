from __future__ import annotations

from core.vision.areas import get_area, load_areas


def test_core_legacy_areas_are_available_in_canonical_format() -> None:
    areas = load_areas()

    assert areas["HP_Area"] == {
        "x": 601,
        "y": 77,
        "width": 23,
        "height": 24,
        "group": "Basic",
    }
    assert get_area("HP_Area") == (601, 77, 23, 24)
    assert get_area("Inventory_Area") == get_area("Inventory_Area_Pattern")
    assert get_area("Inventory_Area") != get_area("inventory")
    assert get_area("Inventory_Slot_28") == (777, 462, 24, 20)


def test_all_inventory_slots_were_migrated() -> None:
    areas = load_areas()

    slot_names = {name for name in areas if name.startswith("Inventory_Slot_")}
    assert slot_names == {f"Inventory_Slot_{index}" for index in range(1, 29)}
    assert all(areas[name]["group"] == "Inventory_Slots" for name in slot_names)


def test_temporary_and_duplicate_legacy_areas_were_not_migrated() -> None:
    areas = load_areas()

    assert "Inventory_Area" not in areas
    assert "Inventory_Area_Pattern" in areas
    assert "inventory" in areas
    assert "NieuwGebied_1" not in areas
    assert "NieuwGebied_2" not in areas
    assert "NieuwGebied_3" not in areas
    assert "Offscreen" not in areas
