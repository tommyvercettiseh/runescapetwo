from __future__ import annotations

import importlib

import numpy as np
import pytest


state_module = importlib.import_module(
    "definitions.inventory.get_inventory_state"
)


def _slot_region(number: int) -> tuple[int, int, int, int]:
    index = number - 1
    return 100 + index % 4, 200 + index // 4, 1, 1


def test_inventory_state_captures_canonical_area_once_and_returns_28_slots(
    monkeypatch,
) -> None:
    image = np.zeros((7, 4, 3), dtype=np.uint8)
    for number in (1, 5, 28):
        x, y, _width, _height = _slot_region(number)
        image[y - 200, x - 100] = 255

    capture_calls = []
    monkeypatch.setattr(
        state_module,
        "capture_area",
        lambda area, bot_id: (
            capture_calls.append((area, bot_id))
            or (image, (100, 200, 4, 7))
        ),
    )
    monkeypatch.setattr(
        state_module,
        "get_region",
        lambda name, bot_id: _slot_region(int(name.rsplit("_", 1)[1])),
    )
    monkeypatch.setattr(
        state_module,
        "_background_percentage",
        lambda slot_image: 0.20 if int(slot_image[0, 0, 0]) else 0.98,
    )

    result = state_module.get_inventory_state(bot_id=3)

    assert capture_calls == [("Inventory_Area", 3)]
    assert len(result) == 28
    assert tuple(slot.number for slot in result) == tuple(range(1, 29))
    assert tuple(slot.number for slot in result if slot.occupied) == (1, 5, 28)
    assert result[0].status == "OCCUPIED"
    assert result[1].status == "EMPTY"
    assert result[0].foreground_percentage == pytest.approx(0.80)


def test_inventory_state_rejects_slot_outside_capture(monkeypatch) -> None:
    monkeypatch.setattr(
        state_module,
        "capture_area",
        lambda *_args, **_kwargs: (
            np.zeros((7, 4, 3), dtype=np.uint8),
            (100, 200, 4, 7),
        ),
    )

    def region(name: str, bot_id: int):
        number = int(name.rsplit("_", 1)[1])
        if number == 1:
            return 99, 200, 1, 1
        return _slot_region(number)

    monkeypatch.setattr(state_module, "get_region", region)

    with pytest.raises(ValueError, match="slot 1 falls outside"):
        state_module.get_inventory_state()


def test_inventory_state_validates_empty_threshold() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        state_module.get_inventory_state(empty_threshold=1.1)
