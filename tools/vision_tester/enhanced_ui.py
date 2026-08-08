from __future__ import annotations

import sys
import time
import tkinter as tk
from queue import Empty, SimpleQueue
from tkinter import ttk

import customtkinter as ctk
from pynput.keyboard import Key as KeyboardKey
from pynput.keyboard import Listener as KeyboardListener

from . import modern_ui, preset_ui
from .enhanced_colour_page import EnhancedColourPage


def apply_enhanced_theme() -> None:
    """Apply the light tester palette without runtime method replacement."""
    ctk.set_appearance_mode("light")
    modern_ui.BG = preset_ui.BASIC_BG
    modern_ui.CARD = preset_ui.BASIC_PANEL
    modern_ui.CARD_ALT = preset_ui.BASIC_CONTROL
    modern_ui.BORDER = preset_ui.BASIC_BORDER
    modern_ui.CONTROL_HOVER = "#e6e6e6"
    modern_ui.TEXT = preset_ui.BASIC_TEXT
    modern_ui.MUTED = preset_ui.BASIC_MUTED
    modern_ui.ACCENT = preset_ui.BASIC_BLUE
    modern_ui.ACCENT_HOVER = preset_ui.BASIC_BLUE_HOVER
    modern_ui.ACCENT_SOFT = "#dbeafe"
    modern_ui.GOLD = preset_ui.BASIC_TEXT
    modern_ui.DANGER = preset_ui.BASIC_RED
    modern_ui.SUCCESS = preset_ui.BASIC_GREEN
    modern_ui.VIEW_BG = preset_ui.BASIC_VIEW


class VisionTester(tk.Tk):
    """Unified vision tester assembled from explicit page classes."""

    def __init__(self) -> None:
        apply_enhanced_theme()
        super().__init__()
        self.configure(background=preset_ui.BASIC_BG)
        self.title("RuneScape Two - Unified Vision Tester")
        self.geometry("1180x760")
        self.minsize(980, 650)

        self._hotkey_events: SimpleQueue[str] = SimpleQueue()
        self._hotkey_listener: KeyboardListener | None = None
        self._last_f2_at = 0.0
        self._closing = False
        self.pages: list[object] = []
        self.current_page = None

        self._configure_style()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._start_hotkeys()
        self.after(50, self._poll_hotkeys)
        self.after(120, self._activate_current_page)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        available = style.theme_names()
        if sys.platform == "win32" and "vista" in available:
            style.theme_use("vista")
        style.configure("TNotebook.Tab", padding=(14, 6))

    def _build(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.rowconfigure(1, weight=1)
        root.columnconfigure(0, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(
            header,
            text="Unified Vision Tester",
            font=("Segoe UI", 17, "bold"),
        ).pack(side="left")
        ttk.Label(
            header,
            text="F2 Capture",
            foreground=preset_ui.BASIC_MUTED,
        ).pack(side="right")

        self.tabs = ttk.Notebook(root)
        self.tabs.grid(row=1, column=0, sticky="nsew")

        colour_host = tk.Frame(self.tabs, background=preset_ui.BASIC_BG)
        template_host = tk.Frame(self.tabs, background=preset_ui.BASIC_BG)
        sensor_host = tk.Frame(self.tabs, background=preset_ui.BASIC_BG)
        self.tabs.add(colour_host, text="Colour")
        self.tabs.add(template_host, text="Template")
        self.tabs.add(sensor_host, text="Sensor")

        self.colour_page = EnhancedColourPage(colour_host)
        self.template_page = modern_ui.TemplatePage(template_host)
        self.sensor_page = modern_ui.SensorPage(sensor_host)

        self.pages = [
            self.colour_page,
            self.template_page,
            self.sensor_page,
        ]
        for page in self.pages:
            page.pack(fill="both", expand=True)

        self.tabs.bind("<<NotebookTabChanged>>", self._tab_changed)

    def _selected_page(self):
        try:
            return self.pages[self.tabs.index(self.tabs.select())]
        except (IndexError, tk.TclError):
            return None

    def _activate_current_page(self) -> None:
        page = self._selected_page()
        if page is None:
            return

        if self.current_page is not None and self.current_page is not page:
            self.current_page.deactivate()
        self.current_page = page
        self.current_page.activate()

    def _tab_changed(self, _event=None) -> None:
        self._activate_current_page()

    def _start_hotkeys(self) -> None:
        options = {"on_press": self._global_key_pressed}
        if sys.platform == "win32":
            options["win32_event_filter"] = self._windows_key_filter
        self._hotkey_listener = KeyboardListener(**options)
        self._hotkey_listener.start()

    def _global_key_pressed(self, key) -> None:
        if key == KeyboardKey.f2:
            self._queue_capture_hotkey()

    def _queue_capture_hotkey(self) -> None:
        now = time.monotonic()
        if now - self._last_f2_at < 0.4:
            return
        self._last_f2_at = now
        self._hotkey_events.put("capture")

    def _windows_key_filter(self, message, data):
        if int(data.vkCode) != 0x71:
            return True
        if int(message) in (0x0100, 0x0104):
            self._queue_capture_hotkey()
        if self._hotkey_listener is not None:
            self._hotkey_listener.suppress_event()
        return False

    def _poll_hotkeys(self) -> None:
        if self._closing:
            return
        try:
            while self._hotkey_events.get_nowait() == "capture":
                if self.current_page is not None:
                    self.current_page.capture_hotkey()
        except Empty:
            pass
        self.after(50, self._poll_hotkeys)

    def _close(self) -> None:
        self._closing = True
        if self.current_page is not None:
            self.current_page.deactivate()
        if self._hotkey_listener is not None:
            self._hotkey_listener.stop()
        self.destroy()


def main() -> None:
    VisionTester().mainloop()


__all__ = ["VisionTester", "apply_enhanced_theme", "main"]
