from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from definitions.bank.is_bank_all_selected import is_bank_all_selected
from definitions.bank.is_bank_closed import is_bank_closed
from definitions.bank.is_bank_open import is_bank_open
from definitions.bank.is_bank_visible import is_bank_visible
from definitions.interface.is_screen_open import is_screen_open
from definitions.inventory.is_inventory_empty import is_inventory_empty
from definitions.inventory.is_inventory_full import is_inventory_full
from definitions.login.is_logged_in import is_logged_in
from definitions.login.is_logged_out import is_logged_out
from definitions.skilling.is_skilling import is_skilling


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
        name="Bank visible.",
        function=is_bank_visible,
        description="Detects the bank object.",
    ),
    DefinitionEntry(
        category="Bank",
        name="Bank open.",
        function=is_bank_open,
        description="Detects Bank_Deposit.",
    ),
    DefinitionEntry(
        category="Bank",
        name="Bank All selected.",
        function=is_bank_all_selected,
        description="Detects BankAllSelected.",
    ),
    DefinitionEntry(
        category="Bank",
        name="Bank closed.",
        function=is_bank_closed,
        description="Checks whether the bank is closed.",
    ),
    DefinitionEntry(
        category="Interface",
        name="Screen open.",
        function=is_screen_open,
        description="Detects ScreenCross.",
    ),
    DefinitionEntry(
        category="Inventory",
        name="Inventory full.",
        function=is_inventory_full,
        description="Checks all 28 slots.",
    ),
    DefinitionEntry(
        category="Inventory",
        name="Inventory empty.",
        function=is_inventory_empty,
        description="Checks all 28 slots.",
    ),
    DefinitionEntry(
        category="Login",
        name="Logged in.",
        function=is_logged_in,
        description="Requires both Login_Exp and Login_Globe in Info_Area.",
    ),
    DefinitionEntry(
        category="Login",
        name="Logged out.",
        function=is_logged_out,
        description="Detects Login_Disconnected or Login_World_Selection in Bot_Area.",
    ),
    DefinitionEntry(
        category="Skilling",
        name="Skilling.",
        function=is_skilling,
        description="Green means skilling; red or no indicator means not skilling.",
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
    raise KeyError(f"Definition not registered: {category} / {name}")
