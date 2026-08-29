"""Compatibility adapter; canonical definition metadata lives in definitions.registry."""

from definitions.registry import (
    DEFINITIONS,
    DefinitionEntry,
    categories,
    definitions_for,
    get_definition,
)

__all__ = [
    "DEFINITIONS",
    "DefinitionEntry",
    "categories",
    "definitions_for",
    "get_definition",
]
