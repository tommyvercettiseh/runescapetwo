"""Compatibility helpers for the consolidated Colour workspace."""

from .colour_browser import (
    DEFAULT_PRESET_NAME,
    BrowserToleranceColourPage,
    filter_preset_names,
    format_ranges,
)

PresetColourPage = BrowserToleranceColourPage

__all__ = [
    "DEFAULT_PRESET_NAME",
    "PresetColourPage",
    "filter_preset_names",
    "format_ranges",
]
