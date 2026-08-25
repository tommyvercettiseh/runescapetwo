from __future__ import annotations

import customtkinter as ctk

from . import ui

DARK_BG = "#10161d"
DARK_CARD = "#171f28"
DARK_CARD_ALT = "#1d2732"
DARK_BORDER = "#2d3946"
DARK_HOVER = "#25313d"
DARK_TEXT = "#f1f5f8"
DARK_MUTED = "#97a5b4"
DARK_ACCENT = "#7de3a0"
DARK_ACCENT_HOVER = "#67cf89"
DARK_ACCENT_SOFT = "#20392c"
DARK_DANGER = "#df7568"
DARK_VIEW = "#0b1015"


def apply_enhanced_theme() -> None:
    """Apply the single dark palette used by the production Vision Tester."""
    ctk.set_appearance_mode("dark")
    ui.set_palette(
        background=DARK_BG,
        card=DARK_CARD,
        card_alt=DARK_CARD_ALT,
        border=DARK_BORDER,
        control_hover=DARK_HOVER,
        text=DARK_TEXT,
        muted=DARK_MUTED,
        accent=DARK_ACCENT,
        accent_hover=DARK_ACCENT_HOVER,
        accent_soft=DARK_ACCENT_SOFT,
        gold=DARK_ACCENT,
        danger=DARK_DANGER,
        success=DARK_ACCENT,
        view_background=DARK_VIEW,
    )


__all__ = [
    "DARK_ACCENT",
    "DARK_ACCENT_HOVER",
    "DARK_ACCENT_SOFT",
    "DARK_BG",
    "DARK_BORDER",
    "DARK_CARD",
    "DARK_CARD_ALT",
    "DARK_DANGER",
    "DARK_HOVER",
    "DARK_MUTED",
    "DARK_TEXT",
    "DARK_VIEW",
    "apply_enhanced_theme",
]
