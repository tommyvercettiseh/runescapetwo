from __future__ import annotations

from dataclasses import dataclass
import random
import time

from core import mouse
from core.vision.areas import get_region
from definitions.bank.is_bank_all_selected import is_bank_all_selected
from definitions.bank.is_bank_open import is_bank_open
from definitions.inventory.get_inventory_item_slots import get_inventory_item_slots
from definitions.inventory.get_inventory_state import InventorySlot, get_inventory_state
from actions.inventory.click_inventory_slot import click_inventory_slot


TOTAL_SLOTS = 28
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


def _validate_slots(slots: set[int]) -> None:
    invalid = sorted(slot for slot in slots if slot < 1 or slot > TOTAL_SLOTS)
    if invalid:
        raise ValueError(f"exclude_slots contains invalid slots: {invalid}")


def _resolve_excluded_slots(
    protected_images: list[str],
    optional_images: list[str],
    explicit_slots: set[int],
    bot_id: int,
) -> tuple[set[int], tuple[str, ...]]:
    excluded = set(explicit_slots)
    missing: list[str] = []

    for image_name in protected_images:
        slots = get_inventory_item_slots(image_name, bot_id)
        if not slots:
            missing.append(image_name)
        excluded.update(slots)

    for image_name in optional_images:
        excluded.update(get_inventory_item_slots(image_name, bot_id))

    return excluded, tuple(missing)


def _occupied_slots(
    state: list[InventorySlot],
    excluded: set[int],
) -> list[int]:
    return [
        slot.number
        for slot in state
        if slot.occupied and slot.number not in excluded
    ]


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
            f"Inventory_Slot_{slot}",
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


def _click_error(result: object) -> str:
    message = getattr(result, "message", None)
    error = getattr(result, "error", None)
    return str(message or error or "Inventory-slot kon niet worden aangeklikt")


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
    _validate_slots(explicit_slots)
    protected_images = list(dict.fromkeys(exclude_images or []))
    optional_images = list(dict.fromkeys(optional_exclude_images or []))
    rng = random.Random(seed)
    clicks = 0

    if not is_bank_open(bot_id):
        return BankInventoryResult(
            success=False,
            message="Bank inventory gestopt: de bank is niet open.",
            bank_open=False,
            dry_run=dry_run,
        )

    if not is_bank_all_selected(bot_id):
        return BankInventoryResult(
            success=False,
            message=(
                "Bank inventory gestopt: bank quantity 'All' is niet geselecteerd "
                "of BankAllSelected kon niet worden gevonden."
            ),
            bank_open=True,
            dry_run=dry_run,
        )

    while True:
        if not is_bank_open(bot_id):
            return BankInventoryResult(
                success=False,
                message="Bank inventory gestopt: de bank sloot tijdens de action.",
                bank_open=False,
                dry_run=dry_run,
                clicks=clicks,
            )

        state = get_inventory_state(bot_id)
        excluded, missing = _resolve_excluded_slots(
            protected_images,
            optional_images,
            explicit_slots,
            bot_id,
        )
        occupied = tuple(
            slot.number
            for slot in state
            if slot.occupied
        )

        if missing:
            return BankInventoryResult(
                success=False,
                message=(
                    "Bank inventory gestopt: niet alle beschermde images zijn "
                    "gevonden. Er is niets verder aangeklikt."
                ),
                bank_open=True,
                dry_run=dry_run,
                clicks=clicks,
                excluded_slots=tuple(sorted(excluded)),
                remaining_slots=occupied,
                missing_exclude_images=missing,
            )

        candidates = _occupied_slots(state, excluded)
        if not candidates:
            return BankInventoryResult(
                success=True,
                message="Inventory bevat alleen nog uitgesloten items.",
                bank_open=True,
                dry_run=dry_run,
                clicks=clicks,
                excluded_slots=tuple(sorted(excluded)),
            )

        selected = _pick_slot(candidates, selection, bot_id, rng)

        if dry_run:
            return BankInventoryResult(
                success=True,
                message="Dry run geslaagd; er is niets aangeklikt.",
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
                message="Bank inventory gestopt: maximaal aantal clicks bereikt.",
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
                message=f"Bank inventory gestopt: {_click_error(click_result)}",
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
                message="Bank inventory gestopt: de bank sloot na de click.",
                bank_open=False,
                clicks=clicks,
                excluded_slots=tuple(sorted(excluded)),
                remaining_slots=tuple(_occupied_slots(changed_state, excluded)),
                selected_slot=selected,
            )

        if status == "timeout":
            return BankInventoryResult(
                success=False,
                message=(
                    "Bank inventory gestopt: de inventory veranderde niet na de "
                    "click. Controleer focus, BankAllSelected en slotdetectie."
                ),
                bank_open=True,
                clicks=clicks,
                excluded_slots=tuple(sorted(excluded)),
                remaining_slots=tuple(_occupied_slots(changed_state, excluded)),
                selected_slot=selected,
            )
