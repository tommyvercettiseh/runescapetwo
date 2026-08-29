from __future__ import annotations

"""Compatibility facade for the Vision Tester UI.

The implementation now lives in focused modules:
- ui.py: palette and shared widgets
- colour_base.py: shared colour-page behaviour
- template_page.py: template calibration page
- sensor_page.py: sensor page

Keep this module intentionally tiny so older imports continue to work without
reintroducing a second implementation.
"""

from . import ui
from .colour_base import ColourBasePage
from .sensor_page import SensorPage
from .template_page import TemplatePage

ColourPage = ColourBasePage
ImageView = ui.ImageView
SourceControls = ui.SourceControls

_button = ui.button
_card = ui.card
_format_pixels = ui.format_pixels
_label = ui.label

_PALETTE_NAMES = {
    "BG",
    "CARD",
    "CARD_ALT",
    "BORDER",
    "CONTROL_HOVER",
    "TEXT",
    "MUTED",
    "ACCENT",
    "ACCENT_HOVER",
    "ACCENT_SOFT",
    "GOLD",
    "DANGER",
    "SUCCESS",
    "VIEW_BG",
    "DEFAULT_AREA",
}


def __getattr__(name: str):
    if name in _PALETTE_NAMES:
        return getattr(ui, name)
    if name == "VisionTester":
        from .app import VisionTester

        return VisionTester
    raise AttributeError(name)


def main() -> None:
    """Compatibility launcher; production entry point is tools.vision_tester.app."""
    from .app import main as run

    run()


__all__ = [
    "ColourPage",
    "ImageView",
    "SensorPage",
    "SourceControls",
    "TemplatePage",
    "_button",
    "_card",
    "_format_pixels",
    "_label",
    "main",
]


if __name__ == "__main__":
    main()
