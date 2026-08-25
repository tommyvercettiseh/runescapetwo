import tkinter as tk

import pytest

from tools.vision_tester.area_page import AreaEditorPage
from tools.vision_tester.colour_page import ColourPage
from tools.vision_tester.enhanced_ui import apply_enhanced_theme
from tools.vision_tester.sensor_boolean_badge import EnhancedSensorPage
from tools.vision_tester.template_plus import SearchableTemplatePage


@pytest.mark.parametrize(
    "page_type",
    (
        ColourPage,
        SearchableTemplatePage,
        EnhancedSensorPage,
        AreaEditorPage,
    ),
)
def test_production_vision_page_builds(page_type) -> None:
    apply_enhanced_theme()
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is unavailable on this CI runner: {exc}")
    root.withdraw()
    try:
        page = page_type(root)
        page.pack(fill="both", expand=True)
        root.update_idletasks()
        page.deactivate()
        page.destroy()
    finally:
        root.destroy()
