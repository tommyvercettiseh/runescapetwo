import pytest

from core.vision.offsets import apply_offset, get_bot_offset


def test_default_bot_offsets_cover_four_clients():
    assert get_bot_offset(1) == (0, 0)
    assert get_bot_offset(2) == (958, 0)
    assert get_bot_offset(3) == (0, 498)
    assert get_bot_offset(4) == (958, 498)


def test_apply_offset_uses_bot_id_and_preserves_size():
    area = (100, 50, 250, 120)
    assert apply_offset(area, bot_id=4) == (1058, 548, 250, 120)


def test_unknown_bot_id_fails_loudly():
    with pytest.raises(ValueError, match="Unknown bot_id"):
        get_bot_offset(99)
