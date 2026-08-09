from __future__ import annotations

import customtkinter as ctk

from . import modern_ui, preset_ui
from .app_shell import VisionTesterShell
from .deep_zoom import ZoomImageView
from .enhanced_colour_page import EnhancedColourPage
from .screen_overlay import ScreenAreaOverlay
from .source_controls import SearchableSourceControls


def apply_enhanced_theme() -> None:
    """Apply the light tester palette without runtime method replacement."""
    ctk.set_appearance_mode("light")
    modern_ui.BG = preset_ui.BASIC_BG
    modern_ui.CARD = preset_ui.BASIC_PANEL
    modern_ui.CARD_ALT = preset_ui.BASIC_CONTROL
    modern_ui.BORDER = preset_ui.BASIC_BORDER
    modern_ui.CONTROL_HOVER = "#e6e6e6"
    modern_ui.TEXT = preset_ui.BASIC_TEXT
    modern_ui.MUTED = preset_ui.BASIC_MUTED
    modern_ui.ACCENT = preset_ui.BASIC_BLUE
    modern_ui.ACCENT_HOVER = preset_ui.BASIC_BLUE_HOVER
    modern_ui.ACCENT_SOFT = "#dbeafe"
    modern_ui.GOLD = preset_ui.BASIC_TEXT
    modern_ui.DANGER = preset_ui.BASIC_RED
    modern_ui.SUCCESS = preset_ui.BASIC_GREEN
    modern_ui.VIEW_BG = preset_ui.BASIC_VIEW


class VisionTester(VisionTesterShell):
    def __init__(self) -> None:
        super().__init__(
            colour_page_type=EnhancedColourPage,
            background=preset_ui.BASIC_BG,
            muted_text=preset_ui.BASIC_MUTED,
            theme_setup=apply_enhanced_theme,
        )


def main() -> None:
    VisionTester().mainloop()


__all__ = [
    "EnhancedColourPage",
    "ScreenAreaOverlay",
    "SearchableSourceControls",
    "VisionTester",
    "ZoomImageView",
    "apply_enhanced_theme",
    "main",
]
