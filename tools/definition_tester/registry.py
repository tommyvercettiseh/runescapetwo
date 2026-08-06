from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from definitions.bank.is_bank_closed import is_bank_closed
from definitions.bank.is_bank_open import is_bank_open
from definitions.bank.is_bank_visible import is_bank_visible
from definitions.interface.is_screen_open import is_screen_open
from definitions.inventory.is_inventory_empty import is_inventory_empty
from definitions.inventory.is_inventory_full import is_inventory_full


DefinitionFunction = Callable[[int], Any]


@dataclass(frozen=True)
class DefinitionEntry:
    category: str
    name: str
    function: DefinitionFunction
    description: str


DEFINITIONS: tuple[DefinitionEntry, ...] = (
    DefinitionEntry(
        category="Bank",
        name="Is bank visible",
        function=is_bank_visible,
        description="Controleert een cyan bankblob binnen de ingestelde pixelgrenzen.",
    ),
    DefinitionEntry(
        category="Bank",
        name="Is bank open",
        function=is_bank_open,
        description="Controleert of Bank_Deposit zichtbaar is in Bot_Area.",
    ),
    DefinitionEntry(
        category="Bank",
        name="Is bank closed",
        function=is_bank_closed,
        description="Controleert of Bank_Deposit niet zichtbaar is in Bot_Area.",
    ),
    DefinitionEntry(
        category="Interface",
        name="Is screen open",
        function=is_screen_open,
        description="Controleert of ScreenCross zichtbaar is in Bot_Area.",
    ),
    DefinitionEntry(
        category="Inventory",
        name="Is inventory full",
        function=is_inventory_full,
        description="Controleert of alle 28 inventory-slots bezet zijn.",
    ),
    DefinitionEntry(
        category="Inventory",
        name="Is inventory empty",
        function=is_inventory_empty,
        description="Controleert of alle 28 inventory-slots leeg zijn.",
    ),
)


def categories() -> list[str]:
    return sorted({entry.category for entry in DEFINITIONS})


def definitions_for(category: str) -> list[DefinitionEntry]:
    return [entry for entry in DEFINITIONS if entry.category == category]


def get_definition(category: str, name: str) -> DefinitionEntry:
    for entry in DEFINITIONS:
        if entry.category == category and entry.name == name:
            return entry
    raise KeyError(f"Definition niet geregistreerd: {category} / {name}")
