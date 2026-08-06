from __future__ import annotations

import importlib

from core.vision.models import Hit


item_slots_module = importlib.import_module(
    "definitions.inventory.get_inventory_item_slots"
)


def hit(x: int, y: int, width: int, height: int) -> Hit:
    return Hit(
        x=x,
        y=y,
        width=width,
        height=height,
        shape_score=100.0,
        color_score=100.0,
        method="test",
    )


def test_slot_for_hit_uses_largest_overlap(monkeypatch) -> None:
    regions = {
        1: (0, 0, 10, 10),
        2: (10, 0, 10, 10),
    }
    monkeypatch.setattr(
        item_slots_module,
        "get_region",
        lambda name, bot_id: regions.get(
            int(name.rsplit("_", 1)[1]),
            (1000, 1000, 1, 1),
        ),
    )

    # The hit touches slot 1, but most of its area is inside slot 2.
    assert item_slots_module._slot_for_hit(hit(8, 1, 10, 8), 1) == 2


def test_get_inventory_item_slots_returns_unique_matching_slots(monkeypatch) -> None:
    monkeypatch.setattr(
        item_slots_module,
        "find_all_images",
        lambda image_name, area, bot_id: [
            hit(1, 1, 4, 4),
            hit(2, 2, 4, 4),
            hit(12, 1, 4, 4),
            hit(100, 100, 3, 3),
        ],
    )
    monkeypatch.setattr(
        item_slots_module,
        "get_region",
        lambda name, bot_id: {
            1: (0, 0, 10, 10),
            2: (10, 0, 10, 10),
        }.get(int(name.rsplit("_", 1)[1]), (1000, 1000, 1, 1)),
    )

    result = item_slots_module.get_inventory_item_slots("Item_Axe", bot_id=2)

    assert result == {1, 2}
