from core.vision.offsets import apply_offset, get_bot_offset, resolve_offset


def test_default_bot_offsets_cover_four_clients():
    assert get_bot_offset(1) == (0, 0)
    assert get_bot_offset(2) == (958, 0)
    assert get_bot_offset(3) == (0, 498)
    assert get_bot_offset(4) == (958, 498)


def test_apply_offset_preserves_width_and_height():
    area = (100, 50, 250, 120)
    assert apply_offset(area, (958, 498)) == (1058, 548, 250, 120)


def test_manual_offset_has_priority_for_backwards_compatibility():
    assert resolve_offset(bot_id=4, offset=(12, 34)) == (12, 34)
