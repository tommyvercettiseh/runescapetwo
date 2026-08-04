from core.vision.areas import get_area, get_region


def test_runescape_style_area_name_resolves_to_same_local_area():
    assert get_area("Inventory_Area") == get_area("inventory")


def test_screen_alias_is_the_local_game_area():
    assert get_area("screen") == get_area("game")


def test_get_region_applies_selected_bot_offset_once():
    local = get_area("Inventory_Area")
    absolute = get_region("Inventory_Area", bot_id=4)

    assert absolute == (local[0] + 958, local[1] + 498, local[2], local[3])
