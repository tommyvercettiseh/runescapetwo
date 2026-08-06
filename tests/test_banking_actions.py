from __future__ import annotations

import importlib
import os

os.environ.setdefault("PYNPUT_BACKEND", "dummy")

from definitions.inventory.get_inventory_state import InventorySlot


bank_inventory_module = importlib.import_module("actions.bank.bank_inventory")
click_close_module = importlib.import_module("actions.interface.click_close_screen")
click_slot_module = importlib.import_module("actions.inventory.click_inventory_slot")
close_bank_module = importlib.import_module("actions.bank.close_bank")
drop_inventory_module = importlib.import_module("actions.inventory.drop_inventory")


def inventory_state(*occupied: int) -> list[InventorySlot]:
    occupied_set = set(occupied)
    return [
        InventorySlot(
            number=number,
            occupied=number in occupied_set,
            background_percentage=0.0 if number in occupied_set else 1.0,
        )
        for number in range(1, 29)
    ]


def repeating_states(*states: list[InventorySlot]):
    values = list(states)
    index = 0

    def get_state(_bot_id: int = 1) -> list[InventorySlot]:
        nonlocal index
        if index < len(values):
            value = values[index]
            index += 1
            return value
        return values[-1]

    return get_state


def test_bank_inventory_refuses_closed_bank(monkeypatch) -> None:
    clicks = []
    monkeypatch.setattr(bank_inventory_module, "is_bank_open", lambda _bot_id: False)
    monkeypatch.setattr(
        bank_inventory_module,
        "click_inventory_slot",
        lambda *args: clicks.append(args) or True,
    )

    result = bank_inventory_module.bank_inventory()

    assert result.success is False
    assert result.bank_open is False
    assert clicks == []


def test_missing_protected_image_stops_before_click(monkeypatch) -> None:
    clicks = []
    monkeypatch.setattr(bank_inventory_module, "is_bank_open", lambda _bot_id: True)
    monkeypatch.setattr(
        bank_inventory_module,
        "get_inventory_state",
        lambda _bot_id: inventory_state(1, 2),
    )
    monkeypatch.setattr(
        bank_inventory_module,
        "get_inventory_item_slots",
        lambda _image, _bot_id: set(),
    )
    monkeypatch.setattr(
        bank_inventory_module,
        "click_inventory_slot",
        lambda *args: clicks.append(args) or True,
    )

    result = bank_inventory_module.bank_inventory(exclude_images=["Item_Axe"])

    assert result.success is False
    assert result.missing_exclude_images == ("Item_Axe",)
    assert clicks == []


def test_bank_inventory_dry_run_reports_next_slot_without_click(monkeypatch) -> None:
    clicks = []
    monkeypatch.setattr(bank_inventory_module, "is_bank_open", lambda _bot_id: True)
    monkeypatch.setattr(
        bank_inventory_module,
        "get_inventory_state",
        lambda _bot_id: inventory_state(1, 2, 3),
    )
    monkeypatch.setattr(
        bank_inventory_module,
        "get_inventory_item_slots",
        lambda image, _bot_id: {1} if image == "Item_Axe" else set(),
    )
    monkeypatch.setattr(
        bank_inventory_module,
        "click_inventory_slot",
        lambda *args: clicks.append(args) or True,
    )

    result = bank_inventory_module.bank_inventory(
        exclude_images=["Item_Axe"],
        selection="random_slot",
        seed=42,
        dry_run=True,
    )

    assert result.success is True
    assert result.dry_run is True
    assert result.excluded_slots == (1,)
    assert result.remaining_slots == (2, 3)
    assert result.selected_slot in {2, 3}
    assert clicks == []


def test_bank_inventory_repeats_until_only_exclusions_remain(monkeypatch) -> None:
    clicks = []
    monkeypatch.setattr(bank_inventory_module, "is_bank_open", lambda _bot_id: True)
    monkeypatch.setattr(
        bank_inventory_module,
        "get_inventory_state",
        repeating_states(
            inventory_state(1, 2, 3),
            inventory_state(1, 3),
            inventory_state(1, 3),
            inventory_state(1),
            inventory_state(1),
        ),
    )
    monkeypatch.setattr(
        bank_inventory_module,
        "get_inventory_item_slots",
        lambda image, _bot_id: {1} if image == "Item_Axe" else set(),
    )
    monkeypatch.setattr(
        bank_inventory_module,
        "click_inventory_slot",
        lambda slot, _bot_id: clicks.append(slot) or True,
    )
    monkeypatch.setattr(bank_inventory_module.time, "sleep", lambda _seconds: None)

    result = bank_inventory_module.bank_inventory(
        exclude_images=["Item_Axe"],
        selection="random_slot",
        seed=5,
        check_interval_s=0.001,
    )

    assert result.success is True
    assert result.clicks == 2
    assert result.excluded_slots == (1,)
    assert len(clicks) == 2


def test_bank_inventory_stops_when_inventory_does_not_change(monkeypatch) -> None:
    clock = [0.0]
    clicks = []
    monkeypatch.setattr(bank_inventory_module, "is_bank_open", lambda _bot_id: True)
    monkeypatch.setattr(
        bank_inventory_module,
        "get_inventory_state",
        lambda _bot_id: inventory_state(1),
    )
    monkeypatch.setattr(
        bank_inventory_module,
        "click_inventory_slot",
        lambda slot, _bot_id: clicks.append(slot) or True,
    )
    monkeypatch.setattr(bank_inventory_module.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(
        bank_inventory_module.time,
        "sleep",
        lambda seconds: clock.__setitem__(0, clock[0] + seconds),
    )

    result = bank_inventory_module.bank_inventory(
        selection="random_slot",
        change_timeout_s=0.3,
        check_interval_s=0.1,
    )

    assert result.success is False
    assert result.clicks == 1
    assert "All" in result.message
    assert clicks == [1]


def test_bank_inventory_stops_when_bank_closes_after_click(monkeypatch) -> None:
    bank_states = iter((True, True, False))
    monkeypatch.setattr(
        bank_inventory_module,
        "is_bank_open",
        lambda _bot_id: next(bank_states),
    )
    monkeypatch.setattr(
        bank_inventory_module,
        "get_inventory_state",
        lambda _bot_id: inventory_state(1),
    )
    monkeypatch.setattr(
        bank_inventory_module,
        "click_inventory_slot",
        lambda _slot, _bot_id: True,
    )
    monkeypatch.setattr(bank_inventory_module.time, "sleep", lambda _seconds: None)

    result = bank_inventory_module.bank_inventory(
        selection="random_slot",
        check_interval_s=0.001,
    )

    assert result.success is False
    assert result.bank_open is False
    assert result.clicks == 1


def test_optional_missing_exclusion_does_not_block_dry_run(monkeypatch) -> None:
    monkeypatch.setattr(bank_inventory_module, "is_bank_open", lambda _bot_id: True)
    monkeypatch.setattr(
        bank_inventory_module,
        "get_inventory_state",
        lambda _bot_id: inventory_state(1),
    )
    monkeypatch.setattr(
        bank_inventory_module,
        "get_inventory_item_slots",
        lambda _image, _bot_id: set(),
    )

    result = bank_inventory_module.bank_inventory(
        optional_exclude_images=["Optional_Item"],
        selection="random_slot",
        dry_run=True,
    )

    assert result.success is True
    assert result.selected_slot == 1


def test_drop_inventory_missing_protected_image_never_holds_shift(monkeypatch) -> None:
    keyboard_calls = []
    monkeypatch.setattr(
        drop_inventory_module,
        "get_inventory_item_slots",
        lambda _image, _bot_id: set(),
    )
    monkeypatch.setattr(
        drop_inventory_module.keyboard,
        "key_down",
        lambda key: keyboard_calls.append(("down", key)),
    )
    monkeypatch.setattr(
        drop_inventory_module.keyboard,
        "key_up",
        lambda key: keyboard_calls.append(("up", key)),
    )

    result = drop_inventory_module.drop_inventory(
        exclude_images=["Item_Axe"],
    )

    assert result is False
    assert keyboard_calls == []


def test_click_inventory_slot_uses_hardened_mouse_action(monkeypatch) -> None:
    calls = []
    expected = object()
    monkeypatch.setattr(
        click_slot_module.mouse_actions,
        "click_in_area",
        lambda **settings: calls.append(settings) or expected,
    )

    result = click_slot_module.click_inventory_slot(7, bot_id=2)

    assert result is expected
    assert calls == [
        {
            "area_name": "Inventory_Slot_7",
            "bot_id": 2,
            "button": "left",
            "area_edge_padding": 6,
            "require_external_mouse": True,
        }
    ]


def test_close_screen_uses_valid_image_padding(monkeypatch) -> None:
    calls = []
    expected = object()
    monkeypatch.setattr(
        click_close_module.mouse_actions,
        "click_image",
        lambda **settings: calls.append(settings) or expected,
    )

    result = click_close_module.click_close_screen(bot_id=3)

    assert result is expected
    assert calls[0]["image_edge_padding"] == 20


def test_close_bank_confirms_bank_is_no_longer_open(monkeypatch) -> None:
    states = iter((True, False, False, False))
    monkeypatch.setattr(
        close_bank_module,
        "is_bank_open",
        lambda _bot_id: next(states),
    )
    monkeypatch.setattr(close_bank_module, "click_close_screen", lambda _bot_id: True)
    monkeypatch.setattr(close_bank_module.time, "sleep", lambda _seconds: None)

    assert close_bank_module.close_bank() is True
