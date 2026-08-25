import tkinter as tk

import pytest

from tools.vision_tester.colour_page import ColourPage
from tools.vision_tester.enhanced_ui import apply_enhanced_theme


def test_production_colour_page_builds() -> None:
    apply_enhanced_theme()
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is unavailable on this CI runner: {exc}")
    root.withdraw()
    try:
        page = ColourPage(root)
        page.pack(fill="both", expand=True)
        root.update_idletasks()
        page.deactivate()
        page.destroy()
    finally:
        root.destroy()
