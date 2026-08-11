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

from core.vision.areas import get_region
from . import modern_ui
from .desktop_preview_overlay import DesktopPreviewOverlay


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

        self.preview_on_game = tk.BooleanVar(value=False)
        self.preview_mode = tk.StringVar(value="Live")
        self._desktop_preview_overlay: DesktopPreviewOverlay | None = None
        self._compact_widgets: dict[tk.Misc, str] = {}

        self._configure_style()
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._start_hotkeys()
        self.after(50, self._poll_hotkeys)
        self.after(120, self._activate_current_page)
        self.after(90, self._poll_desktop_preview)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        available = style.theme_names()
        if sys.platform == "win32" and "vista" in available:
            style.theme_use("vista")
        style.configure("TNotebook.Tab", padding=(14, 6))

    def _build(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.rowconfigure(2, weight=1)
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

        previewbar = ttk.Frame(root, padding=(8, 5))
        previewbar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Checkbutton(
            previewbar,
            text="Preview op gamevenster",
            variable=self.preview_on_game,
            command=self._desktop_preview_changed,
        ).pack(side="left")
        ttk.Label(previewbar, text="Weergave:").pack(side="left", padx=(16, 5))
        preview_mode_box = ttk.Combobox(
            previewbar,
            values=("Live", "Mask", "Isolated"),
            textvariable=self.preview_mode,
            state="readonly",
            width=10,
        )
        preview_mode_box.pack(side="left")
        preview_mode_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._refresh_desktop_preview(),
        )
        ttk.Label(
            previewbar,
            text="Overlay is click-through en wordt niet mee gecaptured.",
            foreground=self._muted_text,
        ).pack(side="left", padx=(14, 0))

        self.tabs = ttk.Notebook(root)
        self.tabs.grid(row=2, column=0, sticky="nsew")

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
        if self.preview_on_game.get():
            self._apply_compact_preview(page)
            self.after_idle(self._refresh_desktop_preview)

    def _tab_changed(self, _event=None) -> None:
        self._activate_current_page()

    def _desktop_preview_changed(self) -> None:
        if self.preview_on_game.get():
            if self._desktop_preview_overlay is None:
                self._desktop_preview_overlay = DesktopPreviewOverlay(self)
            if not self._desktop_preview_overlay.capture_excluded:
                self.preview_on_game.set(False)
                self._desktop_preview_overlay.hide()
                self._set_current_status(
                    "Gamevenster-preview kon niet capture-safe worden gestart op deze Windows-configuratie."
                )
                return
            if self.current_page is not None:
                self._apply_compact_preview(self.current_page)
            self._refresh_desktop_preview()
            return

        if self._desktop_preview_overlay is not None:
            self._desktop_preview_overlay.hide()
        self._restore_compact_preview()

    def _set_current_status(self, message: str) -> None:
        status = getattr(self.current_page, "status", None)
        if status is not None and hasattr(status, "set"):
            status.set(message)

    @staticmethod
    def _grid_managed(widget: tk.Misc) -> bool:
        try:
            return bool(widget.grid_info())
        except tk.TclError:
            return False

    def _compact_targets(self, page) -> list[tk.Misc]:
        # Colour: hide the complete three-panel preview row.
        colour_views = [
            getattr(page, name, None)
            for name in ("capture_view", "mask_view", "isolated_view")
        ]
        if all(view is not None for view in colour_views):
            parents = [view.master for view in colour_views]
            common = getattr(parents[0], "master", None)
            if common is not None and all(getattr(parent, "master", None) is common for parent in parents):
                return [common]

        # Template: the center card is the dedicated live-preview column.
        preview = getattr(page, "preview", None)
        if preview is not None and getattr(preview, "master", None) is not None:
            return [preview.master]

        # Sensor: hide just the two image panels; keep sensor controls/results.
        sensor_views = [
            view
            for view in (
                getattr(page, "live_view", None),
                getattr(page, "detected_view", None),
            )
            if view is not None
        ]
        targets: list[tk.Misc] = []
        for view in sensor_views:
            parent = getattr(view, "master", None)
            if parent is not None and parent not in targets:
                targets.append(parent)
        return targets

    def _apply_compact_preview(self, page) -> None:
        for widget in self._compact_targets(page):
            if widget in self._compact_widgets:
                continue
            if self._grid_managed(widget):
                self._compact_widgets[widget] = "grid"
                try:
                    widget.grid_remove()
                except tk.TclError:
                    self._compact_widgets.pop(widget, None)

    def _restore_compact_preview(self) -> None:
        for widget, manager in list(self._compact_widgets.items()):
            try:
                if manager == "grid":
                    widget.grid()
            except tk.TclError:
                pass
        self._compact_widgets.clear()

    @staticmethod
    def _valid_region(region) -> tuple[int, int, int, int] | None:
        if not isinstance(region, (tuple, list)) or len(region) != 4:
            return None
        try:
            left, top, width, height = map(int, region)
        except (TypeError, ValueError):
            return None
        if width <= 1 or height <= 1:
            return None
        return left, top, width, height

    def _page_region(self, page) -> tuple[int, int, int, int] | None:
        for attribute in ("capture_region", "region"):
            region = self._valid_region(getattr(page, attribute, None))
            if region is not None:
                return region

        source = getattr(page, "source", None)
        if source is not None:
            area_var = getattr(source, "area", None)
            bot_getter = getattr(source, "bot", None)
            if area_var is not None and callable(bot_getter):
                try:
                    return get_region(area_var.get(), bot_id=bot_getter())
                except Exception:
                    pass

        checks = getattr(page, "checks", None)
        sensor_name = getattr(page, "sensor_name", None)
        bot_id = getattr(page, "bot_id", None)
        if isinstance(checks, dict) and sensor_name is not None and bot_id is not None:
            try:
                check = checks.get(sensor_name.get())
                if check is not None:
                    return get_region(check.area, bot_id=int(bot_id.get()))
            except Exception:
                pass
        return None

    @staticmethod
    def _view_rgb(view):
        frame = getattr(view, "_last_rgb", None)
        return frame if frame is not None else None

    def _page_preview_frame(self, page):
        mode = self.preview_mode.get().strip().casefold()

        if mode == "mask":
            frame = self._view_rgb(getattr(page, "mask_view", None))
            if frame is not None:
                return frame
        elif mode == "isolated":
            frame = self._view_rgb(getattr(page, "isolated_view", None))
            if frame is not None:
                return frame

        if mode != "live":
            frame = self._view_rgb(getattr(page, "detected_view", None))
            if frame is not None:
                return frame

        for attribute in ("capture_view", "preview", "live_view", "detected_view"):
            frame = self._view_rgb(getattr(page, attribute, None))
            if frame is not None:
                return frame

        for attribute in ("capture", "screenshot"):
            frame = getattr(page, attribute, None)
            if frame is not None:
                return frame
        return None

    def _refresh_desktop_preview(self) -> None:
        overlay = self._desktop_preview_overlay
        page = self.current_page
        if not self.preview_on_game.get() or overlay is None or page is None:
            if overlay is not None:
                overlay.hide()
            return

        frame = self._page_preview_frame(page)
        region = self._page_region(page)
        if frame is None or region is None:
            overlay.hide()
            return

        try:
            overlay.show_frame(frame, region)
        except (tk.TclError, ValueError, TypeError):
            overlay.hide()

    def _poll_desktop_preview(self) -> None:
        if self._closing:
            return
        if self.preview_on_game.get():
            self._refresh_desktop_preview()
        self.after(90, self._poll_desktop_preview)

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
        self.preview_on_game.set(False)
        if self._desktop_preview_overlay is not None:
            self._desktop_preview_overlay.hide()
        self._restore_compact_preview()
        if self.current_page is not None:
            self.current_page.deactivate()
        if self._hotkey_listener is not None:
            self._hotkey_listener.stop()
        self.destroy()


__all__ = ["VisionTesterShell"]
