from __future__ import annotations

import tkinter as tk

from .area_page import AreaEditorPage
from .app_shell import VisionTesterShell
from .colour_page import ColourPage
from .enhanced_ui import apply_enhanced_theme
from .object_preset_page import ObjectPresetPage
from .preset_ui import BASIC_BG, BASIC_MUTED
from .sensor_boolean_badge import EnhancedSensorPage
from .template_radar import RadarTemplatePage


class VisionTester(VisionTesterShell):
    """Production tester composed explicitly from concrete pages."""

    def __init__(self) -> None:
        super().__init__(
            colour_page_type=ColourPage,
            template_page_type=RadarTemplatePage,
            sensor_page_type=EnhancedSensorPage,
            background=BASIC_BG,
            muted_text=BASIC_MUTED,
            theme_setup=apply_enhanced_theme,
        )

        object_host = tk.Frame(self.tabs, background=BASIC_BG)
        self.tabs.insert(1, object_host, text="Object")
        self.object_page = ObjectPresetPage(object_host)
        self.object_page.pack(fill="both", expand=True)
        self.pages.insert(1, self.object_page)

        self.area_editor_page = self.add_page("Area Editor", AreaEditorPage)


def main() -> None:
    VisionTester().mainloop()


__all__ = ["VisionTester", "main"]


if __name__ == "__main__":
    main()
