from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .colour_page import ColourPage
from .image_page import ImagePage
from .sensor_page import SensorPage


class VisionTester(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("RuneScape Two - Unified Vision Tester")
        self.geometry("1440x900")
        self.minsize(1100, 720)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        notebook.add(ColourPage(notebook), text="Colour testing")
        notebook.add(ImagePage(notebook), text="Image testing")
        notebook.add(SensorPage(notebook), text="Sensor checker")


def main() -> None:
    VisionTester().mainloop()


if __name__ == "__main__":
    main()
