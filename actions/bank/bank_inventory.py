from __future__ import annotations

from dataclasses import dataclass
import random
import time

from actions.inventory.click_inventory_slot import click_inventory_slot
from core import mouse
from core.vision.areas import get_region
from definitions.bank.is_bank_all_selected import is_bank_all_selected
from definitions.bank.is_bank_open import is_bank_open
from definitions.inventory.constants import SLOT_PREFIX
from definitions.inventory.exclusions import (
    occupied_slots,
    resolve_inventory_exclusions,
)
from definitions.inventory.get_inventory_state import InventorySlot, get_inventory_state


DEFAULT_CHANGE_TIMEOUT_S = 2.5
DEFAULT_CHECK_INTERVAL_S = 0.10
DEFAULT_MAX_CLICKS = 28


@dataclass(frozen=True)
class BankInventoryResult:
    success: bool
    message: str
    bank_open: bool
    dry_run: bool = False
    clicks: int = 0
    excluded_slots: tuple[int, ...] = ()
    remaining_slots: tuple[int, ...] = ()
    missing_exclude_images: tuple[str, ...] = ()
    selected_slot: int | None = None

    def __bool__(self) -> bool:
        return self.success


def _state_signature(state: list[InventorySlot]) -> tuple[bool, ...]:
    return tuple(slot.occupied for slot in state)


def _pick_slot(
    slots: list[int],
    selection: str,
    bot_id: int,
    rng: random.Random,
) -> int:
    if selection == "random_slot":
        return rng.choice(slots)
    if selection != "nearest":
        raise ValueError("selection must be nearest or random_slot")

    mouse_x, mouse_y = mouse.position()

    def distance(slot: int) -> int:
        x, y, width, height = get_region(
            f"{SLOT_PREFIX}{slot}",
            bot_id=bot_id,
        )
        center_x = x + width // 2
        center_y = y + height // 2
        return (center_x - mouse_x) ** 2 + (center_y - mouse_y) ** 2

    return min(slots, key=distance)


def _wait_for_inventory_change(
    before: list[InventorySlot],
    bot_id: int,
    timeout_s: float,
    check_interval_s: float,
) -> tuple[str, list[InventorySlot]]:
    signature = _state_signature(before)
    current = before
    deadline = time.monotonic() + timeout_s

    while time.monotonic() < deadline:
        time.sleep(check_interval_s)

        if not is_bank_open(bot_id):
            return "bank_closed", current

        current = get_inventory_state(bot_id)
        if _state_signature(current) != signature:
            return "changed", current

    return "timeout", current


def bank_inventory(
    bot_id: int = 1,
    *,
    exclude_slots: set[int] | None = None,
    exclude_images: list[str] | None = None,
    optional_exclude_images: list[str] | None = None,
    selection: str = "nearest",
    seed: int | None = None,
    dry_run: bool = False,
    change_timeout_s: float = DEFAULT_CHANGE_TIMEOUT_S,
    check_interval_s: float = DEFAULT_CHECK_INTERVAL_S,
    max_clicks: int = DEFAULT_MAX_CLICKS,
) -> BankInventoryResult:
    if selection not in {"nearest", "random_slot"}:
        raise ValueError("selection must be nearest or random_slot")
    if change_timeout_s <= 0:
        raise ValueError("change_timeout_s must be greater than 0")
    if check_interval_s <= 0:
        raise ValueError("check_interval_s must be greater than 0")
    if max_clicks < 1:
        raise ValueError("max_clicks must be at least 1")

    explicit_slots = set(exclude_slots or set())
    protected_images = tuple(exclude_images or ())
    optional_images = tuple(optional_exclude_images or ())
    rng = random.Random(seed)
    clicks = 0

    if not is_bank_open(bot_id):
        return BankInventoryResult(
            success=False,
            message="Bank closed.",
            bank_open=False,
            dry_run=dry_run,
        )

    if not is_bank_all_selected(bot_id):
        return BankInventoryResult(
            success=False,
            message="Bank All is not selected.",
            bank_open=True,
            dry_run=dry_run,
        )

    while True:
        if not is_bank_open(bot_id):
            return BankInventoryResult(
                success=False,
                message="Bank closed.",
                bank_open=False,
                dry_run=dry_run,
                clicks=clicks,
            )

        state = get_inventory_state(bot_id)
        excluded, missing = resolve_inventory_exclusions(
            bot_id=bot_id,
            explicit_slots=explicit_slots,
            protected_images=protected_images,
            optional_images=optional_images,
        )
        occupied = tuple(slot.number for slot in state if slot.occupied)

        if missing:
            return BankInventoryResult(
                success=False,
                message="Protected image missing.",
                bank_open=True,
                dry_run=dry_run,
                clicks=clicks,
                excluded_slots=tuple(sorted(excluded)),
                remaining_slots=occupied,
                missing_exclude_images=missing,
            )

        candidates = occupied_slots(state, excluded)
        if not candidates:
            return BankInventoryResult(
                success=True,
                message="Banking complete.",
                bank_open=True,
                dry_run=dry_run,
                clicks=clicks,
                excluded_slots=tuple(sorted(excluded)),
            )

        selected = _pick_slot(candidates, selection, bot_id, rng)

        if dry_run:
            return BankInventoryResult(
                success=True,
                message="Dry run complete.",
                bank_open=True,
                dry_run=True,
                clicks=0,
                excluded_slots=tuple(sorted(excluded)),
                remaining_slots=tuple(candidates),
                selected_slot=selected,
            )

        if clicks >= max_clicks:
            return BankInventoryResult(
                success=False,
                message="Click limit reached.",
                bank_open=True,
                clicks=clicks,
                excluded_slots=tuple(sorted(excluded)),
                remaining_slots=tuple(candidates),
                selected_slot=selected,
            )

        click_result = click_inventory_slot(selected, bot_id)
        if not click_result:
            return BankInventoryResult(
                success=False,
                message="Slot click failed.",
                bank_open=True,
                clicks=clicks,
                excluded_slots=tuple(sorted(excluded)),
                remaining_slots=tuple(candidates),
                selected_slot=selected,
            )

        clicks += 1
        status, changed_state = _wait_for_inventory_change(
            state,
            bot_id,
            change_timeout_s,
            check_interval_s,
        )

        if status == "bank_closed":
            return BankInventoryResult(
                success=False,
                message="Bank closed.",
                bank_open=False,
                clicks=clicks,
                excluded_slots=tuple(sorted(excluded)),
                remaining_slots=tuple(occupied_slots(changed_state, excluded)),
                selected_slot=selected,
            )

        if status == "timeout":
            return BankInventoryResult(
                success=False,
                message="Inventory unchanged. Check All.",
                bank_open=True,
                clicks=clicks,
                excluded_slots=tuple(sorted(excluded)),
                remaining_slots=tuple(occupied_slots(changed_state, excluded)),
                selected_slot=selected,
            )
