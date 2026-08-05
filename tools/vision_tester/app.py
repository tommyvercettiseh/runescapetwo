from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .colour_page import ColourPage
from .common import COLOURS, configure_style
from .image_page import ImagePage
from .sensor_page import SensorPage


class VisionTester(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("RuneScape Two - Unified Vision Tester")
        self.geometry("1540x960")
        self.minsize(1180, 760)
        configure_style(self)

        header = ttk.Frame(self, padding=(24, 20, 24, 15))
        header.pack(fill="x")
        heading = ttk.Frame(header)
        heading.pack(side="left")
        ttk.Label(heading, text="Vision Workspace", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            heading,
            text="Calibreer kleur, templates en sensoren in één live omgeving",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(3, 0))
        ttk.Label(
            header,
            text="●  ENGINE READY",
            foreground="#087f95",
            font=("Segoe UI Semibold", 9),
        ).pack(side="right", pady=8)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        notebook.add(ColourPage(notebook), text="01  KLEUR")
        notebook.add(ImagePage(notebook), text="02  TEMPLATE")
        notebook.add(SensorPage(notebook), text="03  SENSOR")


def main() -> None:
    VisionTester().mainloop()


if __name__ == "__main__":
    main()
