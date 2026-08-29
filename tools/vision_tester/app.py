from __future__ import annotations

from .area_page import AreaEditorPage
from .app_shell import VisionTesterShell
from .colour_page import ColourPage
from .enhanced_ui import DARK_BG, DARK_MUTED, apply_enhanced_theme
from .sensor_boolean_badge import EnhancedSensorPage
from .template_plus import SearchableTemplatePage


class VisionTester(VisionTesterShell):
    """Production tester composed explicitly from four concrete pages."""

    def __init__(self) -> None:
        super().__init__(
            colour_page_type=ColourPage,
            template_page_type=SearchableTemplatePage,
            sensor_page_type=EnhancedSensorPage,
            background=DARK_BG,
            muted_text=DARK_MUTED,
            theme_setup=apply_enhanced_theme,
        )
        self.area_editor_page = self.add_page("Area Editor", AreaEditorPage)


def main() -> None:
    VisionTester().mainloop()


__all__ = ["VisionTester", "main"]


if __name__ == "__main__":
    main()
