from __future__ import annotations

import customtkinter as ctk

from . import preset_ui, ui
from .app_shell import VisionTesterShell
from .deep_zoom import ZoomImageView
from .enhanced_colour_page import EnhancedColourPage
from .screen_overlay import ScreenAreaOverlay
from .source_controls import SearchableSourceControls


def apply_enhanced_theme() -> None:
    """Apply the light tester palette through the shared UI foundation."""
    ctk.set_appearance_mode("light")
    ui.set_palette(
        background=preset_ui.BASIC_BG,
        card=preset_ui.BASIC_PANEL,
        card_alt=preset_ui.BASIC_CONTROL,
        border=preset_ui.BASIC_BORDER,
        control_hover="#e6e6e6",
        text=preset_ui.BASIC_TEXT,
        muted=preset_ui.BASIC_MUTED,
        accent=preset_ui.BASIC_BLUE,
        accent_hover=preset_ui.BASIC_BLUE_HOVER,
        accent_soft="#dbeafe",
        gold=preset_ui.BASIC_TEXT,
        danger=preset_ui.BASIC_RED,
        success=preset_ui.BASIC_GREEN,
        view_background=preset_ui.BASIC_VIEW,
    )


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
