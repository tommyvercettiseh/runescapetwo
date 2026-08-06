from __future__ import annotations

import importlib

import pytest

from definitions.inventory.get_inventory_state import InventorySlot
from tools.unified_tester.inventory_checker import (
    InventoryCheckResult,
    demo_inventory,
)


checker_module = importlib.import_module(
    "tools.unified_tester.inventory_checker"
)


def slots(*occupied: int) -> tuple[InventorySlot, ...]:
    occupied_set = set(occupied)
    return tuple(
        InventorySlot(
            number=number,
            occupied=number in occupied_set,
            background_percentage=(
                0.25 if number in occupied_set else 0.98
            ),
        )
        for number in range(1, 29)
    )


def test_demo_inventory_has_28_slots_and_fake_image_matches() -> None:
    result = demo_inventory("Item_Axe")

    assert len(result.slots) == 28
    assert result.occupied_count == 8
    assert result.empty_count == 20
    assert result.full is False
    assert result.empty is False
    assert result.image_name == "Item_Axe"
    assert result.image_slots == (5, 13)
    assert result.image_found is True
    assert result.image_scan_ok is True
    assert result.demo is True


def test_inventory_result_reports_full() -> None:
    result = InventoryCheckResult(slots=slots(*range(1, 29)))

    assert result.occupied_count == 28
    assert result.empty_count == 0
    assert result.full is True
    assert result.empty is False


def test_inventory_result_reports_empty() -> None:
    result = InventoryCheckResult(slots=slots())

    assert result.occupied_count == 0
    assert result.empty_count == 28
    assert result.full is False
    assert result.empty is True


def test_image_match_is_always_counted_as_occupied() -> None:
    result = InventoryCheckResult(
        slots=slots(1),
        image_name="Item_Axe",
        image_slots=(2,),
    )

    assert result.detected_occupied_slots == (1,)
    assert result.occupied_slots == (1, 2)
    assert result.empty_slots == tuple(range(3, 29))
    assert result.occupied_count == 2
    assert result.slot_status(1) == "OCCUPIED"
    assert result.slot_status(2) == "IMAGE"
    assert result.is_slot_occupied(2) is True


def test_inventory_result_as_dict_contains_per_slot_diagnostics() -> None:
    result = InventoryCheckResult(
        slots=slots(4),
        image_name="Item_Axe",
        image_slots=(7,),
    )

    data = result.as_dict()

    assert data["occupied_count"] == 2
    assert data["occupied_slots"] == [4, 7]
    assert data["image_slots"] == [7]
    assert data["slots"][3]["status"] == "OCCUPIED"
    assert data["slots"][6]["status"] == "IMAGE"
    assert data["slots"][6]["occupied"] is True
    assert data["slots"][6]["image_match"] is True


def test_inventory_result_requires_all_slots_in_order() -> None:
    with pytest.raises(ValueError, match="slots 1 through 28"):
        InventoryCheckResult(slots=slots()[:-1])


def test_check_inventory_uses_state_and_sorted_image_slots(monkeypatch) -> None:
    expected_slots = slots(1, 4, 9)
    calls = []

    monkeypatch.setattr(
        checker_module,
        "get_inventory_state",
        lambda bot_id: calls.append(("state", bot_id)) or list(expected_slots),
    )
    monkeypatch.setattr(
        checker_module,
        "get_inventory_item_slots",
        lambda image_name, bot_id: (
            calls.append(("image", image_name, bot_id)) or {9, 1}
        ),
    )

    result = checker_module.check_inventory(
        bot_id=3,
        image_name="  Item_Axe  ",
    )

    assert result.slots == expected_slots
    assert result.image_name == "Item_Axe"
    assert result.image_slots == (1, 9)
    assert result.image_error == ""
    assert result.demo is False
    assert calls == [
        ("state", 3),
        ("image", "Item_Axe", 3),
    ]


def test_check_inventory_returns_occupancy_when_image_scan_fails(monkeypatch) -> None:
    monkeypatch.setattr(
        checker_module,
        "get_inventory_state",
        lambda _bot_id: list(slots(2, 5)),
    )

    def fail_image_scan(*_args):
        raise FileNotFoundError("Item_Axe template missing")

    monkeypatch.setattr(
        checker_module,
        "get_inventory_item_slots",
        fail_image_scan,
    )

    result = checker_module.check_inventory(image_name="Item_Axe")

    assert result.occupied_slots == (2, 5)
    assert result.occupied_count == 2
    assert result.image_slots == ()
    assert result.image_scan_ok is False
    assert "template missing" in result.image_error


def test_check_inventory_can_make_image_scan_strict(monkeypatch) -> None:
    monkeypatch.setattr(
        checker_module,
        "get_inventory_state",
        lambda _bot_id: list(slots()),
    )
    monkeypatch.setattr(
        checker_module,
        "get_inventory_item_slots",
        lambda *_args: (_ for _ in ()).throw(FileNotFoundError("missing")),
    )

    with pytest.raises(FileNotFoundError, match="missing"):
        checker_module.check_inventory(
            image_name="Item_Axe",
            strict_image=True,
        )


def test_check_inventory_skips_image_scan_when_name_is_empty(monkeypatch) -> None:
    monkeypatch.setattr(
        checker_module,
        "get_inventory_state",
        lambda _bot_id: list(slots(2)),
    )
    monkeypatch.setattr(
        checker_module,
        "get_inventory_item_slots",
        lambda *_args: (_ for _ in ()).throw(AssertionError("not expected")),
    )

    result = checker_module.check_inventory(image_name="   ")

    assert result.image_name == ""
    assert result.image_slots == ()
    assert result.image_error == ""
