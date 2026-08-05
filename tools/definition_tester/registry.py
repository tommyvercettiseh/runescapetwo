from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from definitions.bank.find_bank import find_bank
from definitions.bank.is_bank_open import is_bank_open


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
        name="Find bank",
        function=find_bank,
        description="Zoekt de grootste geldige cyan bankblob in Bot_Area.",
    ),
    DefinitionEntry(
        category="Bank",
        name="Is bank open",
        function=is_bank_open,
        description="Controleert of Bank_Deposit zichtbaar is in Bot_Area.",
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
