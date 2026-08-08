from __future__ import annotations

from collections.abc import Callable
import sys
import time
import tkinter as tk
from queue import Empty, SimpleQueue
from tkinter import ttk
from typing import Type

from pynput.keyboard import Key as KeyboardKey
from pynput.keyboard import Listener as KeyboardListener

from . import modern_ui


class VisionTesterShell(tk.Tk):
    """Shared notebook shell with explicit page dependencies."""

    def __init__(
        self,
        *,
        colour_page_type: Type,
        background: str,
        muted_text: str,
        theme_setup: Callable[[], None],
        template_page_type: Type = modern_ui.TemplatePage,
        sensor_page_type: Type = modern_ui.SensorPage,
    ) -> None:
        theme_setup()
        super().__init__()
        self.configure(background=background)
        self.title("RuneScape Two - Unified Vision Tester")
        self.geometry("1180x760")
        self.minsize(980, 650)

        self._background = background
        self._muted_text = muted_text
        self._colour_page_type = colour_page_type
        self._template_page_type = template_page_type
        self._sensor_page_type = sensor_page_type
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
            foreground=self._muted_text,
        ).pack(side="right")

        self.tabs = ttk.Notebook(root)
        self.tabs.grid(row=1, column=0, sticky="nsew")

        colour_host = tk.Frame(self.tabs, background=self._background)
        template_host = tk.Frame(self.tabs, background=self._background)
        sensor_host = tk.Frame(self.tabs, background=self._background)
        self.tabs.add(colour_host, text="Colour")
        self.tabs.add(template_host, text="Template")
        self.tabs.add(sensor_host, text="Sensor")

        self.colour_page = self._colour_page_type(colour_host)
        self.template_page = self._template_page_type(template_host)
        self.sensor_page = self._sensor_page_type(sensor_host)

        self.pages = [
            self.colour_page,
            self.template_page,
            self.sensor_page,
        ]
        for page in self.pages:
            page.pack(fill="both", expand=True)

        self.tabs.bind("<<NotebookTabChanged>>", self._tab_changed)

    def add_page(self, title: str, page_type: Type):
        """Add one explicit extra notebook page and include it in lifecycle handling."""
        host = tk.Frame(self.tabs, background=self._background)
        self.tabs.add(host, text=title)
        page = page_type(host)
        page.pack(fill="both", expand=True)
        self.pages.append(page)
        return page

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


__all__ = ["VisionTesterShell"]
