"""Compatibility aliases for the consolidated Colour workspace."""

from .colour_browser import (
    DEFAULT_TOLERANCE,
    BrowserToleranceColourPage,
    tolerance_values,
)

ToleranceColourPage = BrowserToleranceColourPage

__all__ = [
    "DEFAULT_TOLERANCE",
    "ToleranceColourPage",
    "tolerance_values",
]
