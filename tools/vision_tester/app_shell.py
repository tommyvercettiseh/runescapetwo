from __future__ import annotations

from collections.abc import Callable
import sys
import time
import tkinter as tk
from queue import Empty, SimpleQueue
from typing import Type

import customtkinter as ctk
from pynput.keyboard import Key as KeyboardKey
from pynput.keyboard import Listener as KeyboardListener

from . import ui
from .sensor_page import SensorPage
from .template_page import TemplatePage


class VisionTesterShell(tk.Tk):
    """Shared tester shell with one consistent custom navigation system."""

    def __init__(
        self,
        *,
        colour_page_type: Type,
        background: str,
        muted_text: str,
        theme_setup: Callable[[], None],
        template_page_type: Type = TemplatePage,
        sensor_page_type: Type = SensorPage,
    ) -> None:
        theme_setup()
        super().__init__()
        self.configure(background=background)
        self.title("RuneScape Two - Unified Vision Tester")
        self.geometry("1480x900")
        self.minsize(1080, 700)

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
        self._page_hosts: list[ctk.CTkFrame] = []
        self._nav_buttons: list[ctk.CTkButton] = []
        self._nav_underlines: list[ctk.CTkFrame] = []
        self._selected_index = 0
        self.current_page = None

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._start_hotkeys()
        self.after(50, self._poll_hotkeys)
        self.after(120, self._activate_current_page)

    def _build(self) -> None:
        root = ctk.CTkFrame(self, fg_color=self._background, corner_radius=0)
        root.pack(fill="both", expand=True)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)

        self.nav = ctk.CTkFrame(root, fg_color=self._background, corner_radius=0)
        self.nav.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 6))
        self.nav.grid_columnconfigure(0, weight=0)
        self.nav.grid_columnconfigure(1, weight=1)

        self.nav_items = ctk.CTkFrame(self.nav, fg_color="transparent")
        self.nav_items.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            self.nav,
            text="F2  Capture",
            text_color=ui.MUTED,
            font=ui.font(10),
        ).grid(row=0, column=1, sticky="e", padx=(16, 4))

        self.content = ctk.CTkFrame(
            root,
            fg_color=self._background,
            corner_radius=0,
        )
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

        self.colour_page = self._add_page("Colour", self._colour_page_type)
        self.template_page = self._add_page("Template", self._template_page_type)
        self.sensor_page = self._add_page("Sensor", self._sensor_page_type)
        self._show_host(0)
        self._refresh_navigation()

    def _add_page(self, title: str, page_type: Type):
        index = len(self.pages)

        nav_item = ctk.CTkFrame(self.nav_items, fg_color="transparent")
        nav_item.grid(row=0, column=index, padx=(0, 6))
        button = ctk.CTkButton(
            nav_item,
            text=title,
            command=lambda value=index: self._select_page(value),
            width=max(92, 28 + len(title) * 8),
            height=38,
            corner_radius=8,
            border_width=0,
            fg_color="transparent",
            hover_color=ui.CONTROL_HOVER,
            text_color=ui.MUTED,
            font=ui.font(12, bold=True),
        )
        button.grid(row=0, column=0, sticky="ew")
        underline = ctk.CTkFrame(
            nav_item,
            height=2,
            corner_radius=1,
            fg_color="transparent",
        )
        underline.grid(row=1, column=0, sticky="ew", padx=10, pady=(3, 0))

        host = ctk.CTkFrame(
            self.content,
            fg_color=self._background,
            corner_radius=0,
        )
        host.grid(row=0, column=0, sticky="nsew")
        if index != self._selected_index:
            host.grid_remove()

        page = page_type(host)
        page.pack(fill="both", expand=True)

        self.pages.append(page)
        self._page_hosts.append(host)
        self._nav_buttons.append(button)
        self._nav_underlines.append(underline)
        return page

    def add_page(self, title: str, page_type: Type):
        """Add an extra page and include it in navigation/lifecycle handling."""
        page = self._add_page(title, page_type)
        self._refresh_navigation()
        return page

    def _select_page(self, index: int) -> None:
        if not 0 <= index < len(self.pages):
            return
        if index == self._selected_index and self.current_page is not None:
            return
        self._selected_index = index
        self._show_host(index)
        self._refresh_navigation()
        self._activate_current_page()

    def _show_host(self, selected_index: int) -> None:
        for index, host in enumerate(self._page_hosts):
            if index == selected_index:
                host.grid()
                host.tkraise()
            else:
                host.grid_remove()

    def _refresh_navigation(self) -> None:
        for index, (button, underline) in enumerate(
            zip(self._nav_buttons, self._nav_underlines)
        ):
            selected = index == self._selected_index
            button.configure(
                fg_color=ui.CARD_ALT if selected else "transparent",
                hover_color=ui.CONTROL_HOVER,
                text_color=ui.TEXT if selected else ui.MUTED,
            )
            underline.configure(
                fg_color=ui.ACCENT if selected else "transparent"
            )

    def _selected_page(self):
        try:
            return self.pages[self._selected_index]
        except IndexError:
            return None

    def _activate_current_page(self) -> None:
        page = self._selected_page()
        if page is None:
            return
        if self.current_page is not None and self.current_page is not page:
            self.current_page.deactivate()
        self.current_page = page
        self.current_page.activate()

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
