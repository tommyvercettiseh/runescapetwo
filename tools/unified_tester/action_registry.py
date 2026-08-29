from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from actions.bank.bank_inventory import bank_inventory
from actions.bank.click_bank import click_bank
from actions.bank.close_bank import close_bank
from actions.bank.find_bank import find_bank
from actions.bank.open_bank import open_bank
from actions.inventory.click_inventory_item import click_inventory_item
from actions.inventory.drop_inventory import drop_inventory
from definitions.bank.is_bank_all_selected import is_bank_all_selected
from definitions.bank.is_bank_closed import is_bank_closed
from definitions.bank.is_bank_open import is_bank_open
from definitions.bank.is_bank_visible import is_bank_visible
from definitions.inventory.get_inventory_item_slots import get_inventory_item_slots


@dataclass(frozen=True)
class ActionContext:
    bot_id: int
    image_name: str = ""
    protected_images: tuple[str, ...] = ()
    optional_images: tuple[str, ...] = ()
    pattern: str = "random_pattern"
    selection: str = "nearest"
    dry_run: bool = True


@dataclass(frozen=True)
class ActionSpec:
    name: str
    execute: Callable[[ActionContext], Any]
    uses_image: bool = False
    uses_inventory_options: bool = False
    uses_pattern: bool = False
    uses_selection: bool = False


def _bank_preflight(name: str, context: ActionContext) -> dict[str, object]:
    return {
        "action": name,
        "executed": False,
        "bank_visible": is_bank_visible(context.bot_id),
        "bank_open": is_bank_open(context.bot_id),
        "bank_all_selected": is_bank_all_selected(context.bot_id),
        "bank_closed": is_bank_closed(context.bot_id),
        "note": "Dry run. No input sent.",
    }


def _simple_bank_action(
    name: str,
    function: Callable[[int], Any],
) -> Callable[[ActionContext], Any]:
    def execute(context: ActionContext) -> Any:
        if context.dry_run:
            return _bank_preflight(name, context)
        return function(context.bot_id)

    return execute


def _click_inventory_item(context: ActionContext) -> dict[str, object]:
    image_name = context.image_name.strip()
    if not image_name:
        return {
            "action": "Click inventory item",
            "success": False,
            "executed": False,
            "message": "Image name is required.",
        }

    if context.dry_run:
        slots = tuple(sorted(get_inventory_item_slots(image_name, context.bot_id)))
        return {
            "action": "Click inventory item",
            "success": bool(slots),
            "executed": False,
            "image": image_name,
            "slots": slots,
            "message": (
                "Dry run. Item is available."
                if slots
                else "Dry run. Item not found in inventory."
            ),
        }

    success = click_inventory_item(
        image_name,
        bot_id=context.bot_id,
        selection=context.selection,
    )
    return {
        "action": "Click inventory item",
        "success": success,
        "executed": success,
        "image": image_name,
        "message": "Item clicked." if success else "Item not found.",
    }


def _bank_inventory(context: ActionContext):
    return bank_inventory(
        context.bot_id,
        exclude_images=list(context.protected_images),
        optional_exclude_images=list(context.optional_images),
        selection=context.selection,
        dry_run=context.dry_run,
    )


def _drop_inventory(context: ActionContext):
    return drop_inventory(
        context.bot_id,
        exclude_images=list(context.protected_images),
        optional_exclude_images=list(context.optional_images),
        pattern=context.pattern,
        dry_run=context.dry_run,
    )


ACTION_SPECS: tuple[ActionSpec, ...] = (
    ActionSpec(
        "Bank inventory",
        _bank_inventory,
        uses_inventory_options=True,
        uses_selection=True,
    ),
    ActionSpec("Open bank", _simple_bank_action("Open bank", open_bank)),
    ActionSpec("Close bank", _simple_bank_action("Close bank", close_bank)),
    ActionSpec("Find bank", _simple_bank_action("Find bank", find_bank)),
    ActionSpec("Click bank", _simple_bank_action("Click bank", click_bank)),
    ActionSpec(
        "Click inventory item",
        _click_inventory_item,
        uses_image=True,
        uses_selection=True,
    ),
    ActionSpec(
        "Drop inventory",
        _drop_inventory,
        uses_inventory_options=True,
        uses_pattern=True,
    ),
)

_ACTIONS_BY_NAME = {spec.name: spec for spec in ACTION_SPECS}


def action_names() -> tuple[str, ...]:
    return tuple(spec.name for spec in ACTION_SPECS)


def get_action(name: str) -> ActionSpec:
    try:
        return _ACTIONS_BY_NAME[name]
    except KeyError as exc:
        raise KeyError(f"Unknown action: {name}") from exc


__all__ = [
    "ActionContext",
    "ActionSpec",
    "ACTION_SPECS",
    "action_names",
    "get_action",
]
