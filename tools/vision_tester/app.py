from __future__ import annotations

from .app_shell import VisionTesterShell
from .enhanced_ui import apply_enhanced_theme
from .preset_ui import BASIC_BG, BASIC_MUTED
from .preview_pages import (
    PreviewColourPage,
    PreviewSensorPage,
    PreviewTemplatePage,
)
from .unified_plus import AreaEditorPage


class VisionTester(VisionTesterShell):
    """Production tester composed explicitly from final feature pages."""

    def __init__(self) -> None:
        super().__init__(
            colour_page_type=PreviewColourPage,
            template_page_type=PreviewTemplatePage,
            sensor_page_type=PreviewSensorPage,
            background=BASIC_BG,
            muted_text=BASIC_MUTED,
            theme_setup=apply_enhanced_theme,
        )
        self.area_editor_page = self.add_page("Area Editor", AreaEditorPage)


def main() -> None:
    VisionTester().mainloop()


__all__ = ["VisionTester", "main"]


if __name__ == "__main__":
    main()
