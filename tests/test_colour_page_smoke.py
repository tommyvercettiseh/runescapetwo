import tkinter as tk

from tools.vision_tester.colour_page import ColourPage
from tools.vision_tester.enhanced_ui import apply_enhanced_theme


def test_production_colour_page_builds() -> None:
    apply_enhanced_theme()
    root = tk.Tk()
    root.withdraw()
    try:
        page = ColourPage(root)
        page.pack(fill="both", expand=True)
        root.update_idletasks()
        page.deactivate()
        page.destroy()
    finally:
        root.destroy()
