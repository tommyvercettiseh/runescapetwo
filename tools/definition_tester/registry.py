from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from definitions.bank.is_bank_all_selected import is_bank_all_selected
from definitions.bank.is_bank_closed import is_bank_closed
from definitions.bank.is_bank_open import is_bank_open
from definitions.bank.is_bank_visible import is_bank_visible
from definitions.camera.compass import (
    is_compass_east,
    is_compass_east_missing,
    is_compass_north,
    is_compass_north_missing,
    is_compass_south,
    is_compass_south_missing,
    is_compass_west,
    is_compass_west_missing,
)
from definitions.hp.is_low_hp import is_low_hp
from definitions.interface.is_screen_open import is_screen_open
from definitions.inventory.is_inventory_empty import is_inventory_empty
from definitions.inventory.is_inventory_full import is_inventory_full
from definitions.login.is_logged_in import is_logged_in
from definitions.login.is_logged_out import is_logged_out
from definitions.login.is_not_logged_in import is_not_logged_in
from definitions.prayer.is_low_prayer import is_low_prayer
from definitions.skilling.is_skilling import is_skilling


DefinitionFunction = Callable[[int], Any]


@dataclass(frozen=True)
class DefinitionEntry:
    category: str
    name: str
    function: DefinitionFunction
    description: str


DEFINITIONS: tuple[DefinitionEntry, ...] = (
    DefinitionEntry("Bank", "Bank visible.", is_bank_visible, "Detects the bank object."),
    DefinitionEntry("Bank", "Bank open.", is_bank_open, "Detects Bank_Deposit."),
    DefinitionEntry("Bank", "Bank All selected.", is_bank_all_selected, "Detects BankAllSelected."),
    DefinitionEntry("Bank", "Bank closed.", is_bank_closed, "Checks whether the bank is closed."),
    DefinitionEntry("Camera", "Compass north.", is_compass_north, "Detects Compass_North in Compass_Area."),
    DefinitionEntry("Camera", "Compass north missing.", is_compass_north_missing, "True when Compass_North is not detected."),
    DefinitionEntry("Camera", "Compass east.", is_compass_east, "Detects Compass_East in Compass_Area."),
    DefinitionEntry("Camera", "Compass east missing.", is_compass_east_missing, "True when Compass_East is not detected."),
    DefinitionEntry("Camera", "Compass south.", is_compass_south, "Detects Compass_South in Compass_Area."),
    DefinitionEntry("Camera", "Compass south missing.", is_compass_south_missing, "True when Compass_South is not detected."),
    DefinitionEntry("Camera", "Compass west.", is_compass_west, "Detects Compass_West in Compass_Area."),
    DefinitionEntry("Camera", "Compass west missing.", is_compass_west_missing, "True when Compass_West is not detected."),
    DefinitionEntry("HP", "Low HP.", is_low_hp, "Uses the HP stoplight sensor; orange/red means low HP."),
    DefinitionEntry("Interface", "Screen open.", is_screen_open, "Detects ScreenCross."),
    DefinitionEntry("Inventory", "Inventory full.", is_inventory_full, "Checks all 28 slots."),
    DefinitionEntry("Inventory", "Inventory empty.", is_inventory_empty, "Checks all 28 slots."),
    DefinitionEntry("Login", "Logged in.", is_logged_in, "Requires both Login_Exp and Login_Globe in Info_Area."),
    DefinitionEntry("Login", "Not logged in.", is_not_logged_in, "True whenever the normal logged-in HUD is not detected."),
    DefinitionEntry("Login", "Logged out.", is_logged_out, "Detects Login_Disconnected or Login_World_Selection in Bot_Area."),
    DefinitionEntry("Prayer", "Low prayer.", is_low_prayer, "Uses the prayer stoplight sensor; orange/red means low prayer."),
    DefinitionEntry("Skilling", "Skilling.", is_skilling, "Green means skilling; red or no indicator means not skilling."),
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
