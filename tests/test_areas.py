from core.vision.areas import get_area, get_region


def test_inventory_area_uses_canonical_slot_crop():
    assert get_area("Inventory_Area") == get_area("Inventory_Area_Pattern")


def test_legacy_inventory_placeholder_remains_available():
    assert get_area("inventory") != get_area("Inventory_Area")


def test_all_inventory_slots_fit_inside_inventory_area():
    area_x, area_y, area_width, area_height = get_area("Inventory_Area")
    area_right = area_x + area_width
    area_bottom = area_y + area_height

    for slot_number in range(1, 29):
        x, y, width, height = get_area(f"Inventory_Slot_{slot_number}")
        assert area_x <= x < x + width <= area_right
        assert area_y <= y < y + height <= area_bottom


def test_screen_alias_is_the_local_game_area():
    assert get_area("screen") == get_area("game")


def test_get_region_applies_selected_bot_offset_once():
    local = get_area("Inventory_Area")
    absolute = get_region("Inventory_Area", bot_id=4)

    assert absolute == (local[0] + 958, local[1] + 498, local[2], local[3])
