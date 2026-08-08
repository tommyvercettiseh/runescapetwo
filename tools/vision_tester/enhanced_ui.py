from __future__ import annotations

import ctypes
import sys
import time
import tkinter as tk
from queue import Empty, SimpleQueue
from tkinter import ttk

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk
from pynput.keyboard import Key as KeyboardKey
from pynput.keyboard import Listener as KeyboardListener

from core.vision.areas import load_areas
from core.vision.colour_detection import hsv_ranges_around, sample_hsv
from . import modern_ui, preset_ui


MIN_ZOOM_PERCENT = 25
MAX_ZOOM_PERCENT = 1600
PIPETTE_EDGE_PADDING = 6
AREA_BORDER_HEX = "#dc3737"
SAFE_BORDER_HEX = "#32d25a"
MARKER_HEX = "#ffffff"
TRANSPARENT_KEY = "#010203"
SAMPLE_SIZES = (1, 3, 5, 7)


def apply_enhanced_theme() -> None:
    """Apply the light palette without replacing functions at runtime."""
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


class ZoomImageView(tk.Canvas):
    """Canvas image view with deep zoom, panning and source-pixel mapping."""

    def __init__(
        self,
        parent,
        *,
        auto_resize: bool = True,
        zoom_percent: int = 100,
        maximum_upscale: float = 6.0,
    ) -> None:
        super().__init__(
            parent,
            background=modern_ui.VIEW_BG,
            borderwidth=0,
            highlightthickness=0,
        )
        self.auto_resize = bool(auto_resize)
        self.zoom_percent = int(zoom_percent)
        self.maximum_upscale = float(maximum_upscale)
        self.scale = 1.0
        self.image_offset = (0, 0)
        self.display_size = (0, 0)
        self.source_origin = (0.0, 0.0)
        self._photo: ImageTk.PhotoImage | None = None
        self._last_rgb: np.ndarray | None = None
        self._job: str | None = None
        self._centre: tuple[float, float] | None = None
        self._pan_anchor: tuple[int, int] | None = None
        self._marker: tuple[int, int, int] | None = None

        self.bind("<Configure>", self._schedule)
        self.bind("<ButtonPress-3>", self._pan_start)
        self.bind("<B3-Motion>", self._pan_move)

    def show(self, rgb: np.ndarray) -> None:
        shape_changed = (
            self._last_rgb is None
            or self._last_rgb.shape[:2] != rgb.shape[:2]
        )
        self._last_rgb = rgb
        if shape_changed:
            height, width = rgb.shape[:2]
            self._centre = (width / 2.0, height / 2.0)
        self._draw()

    def set_marker(self, x: int, y: int, sample_size: int = 1) -> None:
        self._marker = (int(x), int(y), max(1, int(sample_size)))
        self._draw_marker()

    def clear_marker(self) -> None:
        self._marker = None
        self.delete("pipette_marker")

    def set_view(self, *, auto_resize: bool, zoom_percent: int) -> None:
        self.auto_resize = bool(auto_resize)
        self.zoom_percent = min(
            MAX_ZOOM_PERCENT,
            max(MIN_ZOOM_PERCENT, int(zoom_percent)),
        )
        self._draw()

    def _schedule(self, _event=None) -> None:
        if self._last_rgb is None:
            return
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(50, self._draw)

    def _draw(self) -> None:
        self._job = None
        if self._last_rgb is None:
            return

        rgb = self._last_rgb
        height, width = rgb.shape[:2]
        target_width = max(1, self.winfo_width())
        target_height = max(1, self.winfo_height())

        if self.auto_resize:
            fit = min(target_width / width, target_height / height)
            self.scale = min(self.maximum_upscale, fit)
            rendered = rgb
            self.source_origin = (0.0, 0.0)
        else:
            self.scale = self.zoom_percent / 100.0
            rendered = self._visible_crop(
                rgb,
                target_width=target_width,
                target_height=target_height,
            )

        display_width = max(1, int(rendered.shape[1] * self.scale))
        display_height = max(1, int(rendered.shape[0] * self.scale))
        self.display_size = (display_width, display_height)
        self.image_offset = (
            (target_width - display_width) // 2,
            (target_height - display_height) // 2,
        )
        resized = cv2.resize(
            rendered,
            self.display_size,
            interpolation=(
                cv2.INTER_AREA if self.scale < 1.0 else cv2.INTER_NEAREST
            ),
        )

        self.delete("all")
        self._photo = ImageTk.PhotoImage(Image.fromarray(resized))
        self.create_image(
            self.image_offset[0],
            self.image_offset[1],
            image=self._photo,
            anchor="nw",
        )
        self._draw_marker()

    def _visible_crop(
        self,
        rgb: np.ndarray,
        *,
        target_width: int,
        target_height: int,
    ) -> np.ndarray:
        height, width = rgb.shape[:2]
        if self._centre is None:
            self._centre = (width / 2.0, height / 2.0)

        source_width = min(float(width), target_width / self.scale)
        source_height = min(float(height), target_height / self.scale)
        centre_x, centre_y = self._centre

        left = min(
            max(0.0, centre_x - source_width / 2.0),
            max(0.0, width - source_width),
        )
        top = min(
            max(0.0, centre_y - source_height / 2.0),
            max(0.0, height - source_height),
        )
        self._centre = (
            left + source_width / 2.0,
            top + source_height / 2.0,
        )

        x0 = max(0, int(np.floor(left)))
        y0 = max(0, int(np.floor(top)))
        x1 = min(width, max(x0 + 1, int(np.ceil(left + source_width))))
        y1 = min(height, max(y0 + 1, int(np.ceil(top + source_height))))
        self.source_origin = (float(x0), float(y0))
        return rgb[y0:y1, x0:x1]

    def _draw_marker(self) -> None:
        self.delete("pipette_marker")
        if self._marker is None or self._last_rgb is None:
            return

        x, y, sample_size = self._marker
        radius = sample_size // 2
        origin_x, origin_y = self.source_origin
        left = self.image_offset[0] + (x - radius - origin_x) * self.scale
        top = self.image_offset[1] + (y - radius - origin_y) * self.scale
        right = self.image_offset[0] + (x + radius + 1 - origin_x) * self.scale
        bottom = self.image_offset[1] + (y + radius + 1 - origin_y) * self.scale

        image_left = self.image_offset[0]
        image_top = self.image_offset[1]
        image_right = image_left + self.display_size[0]
        image_bottom = image_top + self.display_size[1]
        if (
            right <= image_left
            or bottom <= image_top
            or left >= image_right
            or top >= image_bottom
        ):
            return

        self.create_rectangle(
            max(image_left, left),
            max(image_top, top),
            min(image_right, right),
            min(image_bottom, bottom),
            outline=MARKER_HEX,
            width=1,
            tags="pipette_marker",
        )

    def image_coordinates(self, x: int, y: int) -> tuple[int, int] | None:
        if self._last_rgb is None:
            return None

        relative_x = x - self.image_offset[0]
        relative_y = y - self.image_offset[1]
        display_width, display_height = self.display_size
        if not 0 <= relative_x < display_width:
            return None
        if not 0 <= relative_y < display_height:
            return None

        origin_x, origin_y = self.source_origin
        source_x = int(origin_x + relative_x / self.scale)
        source_y = int(origin_y + relative_y / self.scale)
        height, width = self._last_rgb.shape[:2]
        if not 0 <= source_x < width or not 0 <= source_y < height:
            return None
        return source_x, source_y

    def _pan_start(self, event) -> None:
        if not self.auto_resize:
            self._pan_anchor = (event.x, event.y)

    def _pan_move(self, event) -> None:
        if self.auto_resize or self._pan_anchor is None or self._centre is None:
            return
        old_x, old_y = self._pan_anchor
        centre_x, centre_y = self._centre
        self._centre = (
            centre_x - (event.x - old_x) / self.scale,
            centre_y - (event.y - old_y) / self.scale,
        )
        self._pan_anchor = (event.x, event.y)
        self._draw()


class SearchableSourceControls(ttk.Frame):
    """Source controls with live partial area filtering."""

    def __init__(
        self,
        parent,
        *,
        default_area: str = modern_ui.DEFAULT_AREA,
    ) -> None:
        super().__init__(parent)
        self._areas = sorted(load_areas())
        selected = (
            default_area
            if default_area in self._areas
            else self._areas[0]
            if self._areas
            else "game"
        )
        self.bot_id = tk.StringVar(value="1")
        self.area = tk.StringVar(value=selected)
        self.area_search = tk.StringVar()

        ttk.Label(self, text="Bot ID").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            self,
            from_=1,
            to=4,
            textvariable=self.bot_id,
            width=5,
        ).grid(row=0, column=1, sticky="w", padx=(7, 18))

        ttk.Label(self, text="Area search").grid(row=0, column=2, sticky="w")
        search = ttk.Entry(self, textvariable=self.area_search, width=18)
        search.grid(row=0, column=3, sticky="ew", padx=(7, 14))
        search.bind("<KeyRelease>", self._filter_areas)

        ttk.Label(self, text="Area").grid(row=0, column=4, sticky="w")
        self.area_box = ttk.Combobox(
            self,
            values=self._areas,
            textvariable=self.area,
            width=30,
            state="readonly",
        )
        self.area_box.grid(row=0, column=5, sticky="ew", padx=(7, 0))
        self.columnconfigure(3, weight=1)
        self.columnconfigure(5, weight=2)

    def _filter_areas(self, _event=None) -> None:
        terms = [
            part
            for part in self.area_search.get().casefold().split()
            if part
        ]
        matches = [
            area
            for area in self._areas
            if all(term in area.casefold() for term in terms)
        ]
        self.area_box.configure(values=matches)
        if len(matches) == 1:
            self.area.set(matches[0])

    def bot(self) -> int:
        return int(self.bot_id.get())


class ScreenAreaOverlay:
    """Click-through desktop area guide excluded from capture when supported."""

    def __init__(self, master: tk.Misc) -> None:
        self.window = tk.Toplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.configure(bg=TRANSPARENT_KEY)
        self.window.attributes("-topmost", True)
        if sys.platform == "win32":
            self.window.attributes("-transparentcolor", TRANSPARENT_KEY)

        self.canvas = tk.Canvas(
            self.window,
            bg=TRANSPARENT_KEY,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self._capture_excluded = False
        self._configure_windows_overlay()

    def _window_handle(self) -> int:
        user32 = ctypes.windll.user32
        handle = int(self.window.winfo_id())
        parent = int(user32.GetParent(handle))
        return parent or handle

    def _configure_windows_overlay(self) -> None:
        if sys.platform != "win32":
            return

        self.window.update_idletasks()
        user32 = ctypes.windll.user32
        handle = self._window_handle()
        extended_style = int(user32.GetWindowLongW(handle, -20))
        user32.SetWindowLongW(
            handle,
            -20,
            extended_style | 0x00080000 | 0x00000020 | 0x00000080 | 0x08000000,
        )
        try:
            self._capture_excluded = bool(
                user32.SetWindowDisplayAffinity(handle, 0x00000011)
            )
        except Exception:
            self._capture_excluded = False

    @property
    def capture_excluded(self) -> bool:
        return self._capture_excluded

    def hide(self) -> None:
        try:
            self.window.withdraw()
        except tk.TclError:
            pass

    def show_region(self, region: tuple[int, int, int, int]) -> None:
        left, top, width, height = map(int, region)
        if width <= 1 or height <= 1:
            self.hide()
            return

        self.window.geometry(f"{width}x{height}{left:+d}{top:+d}")
        self.canvas.configure(width=width, height=height)
        self.canvas.delete("all")
        self.canvas.create_rectangle(
            1,
            1,
            width - 2,
            height - 2,
            outline=AREA_BORDER_HEX,
            width=2,
        )

        pad = PIPETTE_EDGE_PADDING
        if width > pad * 2 + 2 and height > pad * 2 + 2:
            self.canvas.create_rectangle(
                pad,
                pad,
                width - pad - 1,
                height - pad - 1,
                outline=SAFE_BORDER_HEX,
                width=1,
            )
        self.window.deiconify()
        self.window.lift()


class EnhancedColourPage(preset_ui.PresetColourPage):
    """Preset colour page with deep zoom, safe pipette sampling and desktop guides."""

    def __init__(self, parent) -> None:
        self.pipette_sample_size = tk.IntVar(value=1)
        self._screen_area_overlay: ScreenAreaOverlay | None = None
        self._last_pipette_point: tuple[int, int] | None = None
        super().__init__(parent)

    def _build(self) -> None:
        self.configure(fg_color=preset_ui.BASIC_BG)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        toolbar = ttk.LabelFrame(self, text="Capture", padding=(10, 7))
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 5))
        toolbar.columnconfigure(0, weight=1)

        self.source = SearchableSourceControls(toolbar)
        self.source.grid(row=0, column=0, sticky="ew")

        ttk.Checkbutton(
            toolbar,
            text="Live",
            variable=self.live,
            command=self._toggle_live,
        ).grid(row=0, column=1, padx=(18, 7))
        ttk.Button(toolbar, text="Capture", command=self._once).grid(
            row=0,
            column=2,
        )

        self._build_preset_bar()
        self._build_detection_controls()
        self._build_previews()

        ttk.Label(
            self,
            textvariable=self.status,
            anchor="w",
            relief="sunken",
            padding=(7, 3),
        ).grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 8))

    def _build_preset_bar(self) -> None:
        presetbar = ttk.LabelFrame(self, text="Colour preset", padding=(10, 7))
        presetbar.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        presetbar.columnconfigure(1, weight=1)
        presetbar.columnconfigure(3, weight=1)

        ttk.Label(presetbar, text="Search").grid(row=0, column=0, sticky="w")
        ttk.Entry(presetbar, textvariable=self.preset_search).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(7, 14),
        )
        ttk.Label(presetbar, text="Current preset").grid(
            row=0,
            column=2,
            sticky="w",
        )
        self.preset_box = ttk.Combobox(
            presetbar,
            values=[preset_ui.DEFAULT_PRESET_NAME],
            textvariable=self.current_preset,
            width=24,
        )
        self.preset_box.grid(row=0, column=3, sticky="ew", padx=(7, 14))
        self.preset_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._preset_selected(self.current_preset.get()),
        )

        ttk.Button(
            presetbar,
            text="Load",
            command=self._load_current_preset,
        ).grid(row=0, column=4, padx=(0, 5))
        ttk.Button(
            presetbar,
            text="New",
            command=self._new_preset,
        ).grid(row=0, column=5, padx=5)
        ttk.Button(
            presetbar,
            text="Save current preset",
            command=self._save_current_preset,
        ).grid(row=0, column=6, padx=5)
        ttk.Button(
            presetbar,
            text="Delete",
            command=self._delete_current_preset,
        ).grid(row=0, column=7, padx=(5, 0))

        ttk.Label(
            presetbar,
            textvariable=self.preset_summary,
            foreground=preset_ui.BASIC_MUTED,
        ).grid(
            row=1,
            column=0,
            columnspan=6,
            sticky="w",
            pady=(6, 0),
        )
        ttk.Label(
            presetbar,
            text=preset_ui.PRESETS_PATH_LABEL,
            foreground=preset_ui.BASIC_MUTED,
        ).grid(
            row=1,
            column=6,
            columnspan=2,
            sticky="e",
            pady=(6, 0),
        )

    def _build_detection_controls(self) -> None:
        controls = ttk.LabelFrame(self, text="Detection", padding=(10, 7))
        controls.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        controls.columnconfigure(15, weight=1)

        ttk.Label(controls, text="Min blob px").grid(row=0, column=0)
        minimum_entry = ttk.Entry(
            controls,
            textvariable=self.minimum,
            width=7,
        )
        minimum_entry.grid(row=0, column=1, padx=(5, 10))
        minimum_entry.bind("<KeyRelease>", lambda _event: self._render())

        ttk.Label(controls, text="Max blob px").grid(row=0, column=2)
        maximum_entry = ttk.Entry(
            controls,
            textvariable=self.maximum,
            width=7,
        )
        maximum_entry.grid(row=0, column=3, padx=(5, 12))
        maximum_entry.bind("<KeyRelease>", lambda _event: self._render())

        self.pipette_button = ttk.Button(
            controls,
            text="Pipette",
            command=self._toggle_pipette,
        )
        self.pipette_button.grid(row=0, column=4, padx=(0, 5))

        ttk.Label(controls, text="Pipet px").grid(row=0, column=5, padx=(8, 3))
        ttk.Combobox(
            controls,
            values=SAMPLE_SIZES,
            textvariable=self.pipette_sample_size,
            state="readonly",
            width=3,
        ).grid(row=0, column=6, padx=(0, 5))

        self.move_colour_button = ttk.Button(
            controls,
            text="Move colour",
            command=lambda: self._start_colour_mouse_action(click=False),
        )
        self.move_colour_button.grid(row=0, column=7, padx=5)
        self.click_colour_button = ttk.Button(
            controls,
            text="Click colour",
            command=lambda: self._start_colour_mouse_action(click=True),
        )
        self.click_colour_button.grid(row=0, column=8, padx=5)

        self.trace_switch = ttk.Checkbutton(
            controls,
            text="Trace",
            variable=self.mouse_trace,
            command=self._trace_changed,
        )
        self.trace_switch.grid(row=0, column=9, padx=(10, 5))
        self.auto_switch = ttk.Checkbutton(
            controls,
            text="Auto resize",
            variable=self.auto_resize,
            command=self._view_changed,
        )
        self.auto_switch.grid(row=0, column=10, padx=5)

        self.zoom_label = ttk.Label(
            controls,
            text=f"Zoom {self.zoom.get()}%",
        )
        self.zoom_label.grid(row=0, column=11, padx=(10, 4))
        self.zoom_slider = ttk.Scale(
            controls,
            from_=MIN_ZOOM_PERCENT,
            to=MAX_ZOOM_PERCENT,
            variable=self.zoom,
            command=self._zoom_changed,
            length=105,
        )
        self.zoom_slider.grid(row=0, column=12, padx=(0, 12))

        ttk.Label(controls, text="Live blob").grid(row=0, column=13)
        ttk.Label(
            controls,
            textvariable=self.blob_live_text,
            foreground=preset_ui.BASIC_GREEN,
        ).grid(row=0, column=14, padx=(5, 8))
        ttk.Label(
            controls,
            textvariable=self.blob_range_text,
            foreground=preset_ui.BASIC_MUTED,
        ).grid(row=0, column=15, sticky="e")
        ttk.Button(
            controls,
            text="Reset range",
            command=self._reset_blob_history,
        ).grid(row=0, column=16, padx=(8, 0))

        self.blob_meter = preset_ui.BasicProgressbar(controls)
        self.blob_meter.grid(
            row=1,
            column=0,
            columnspan=17,
            sticky="ew",
            pady=(7, 0),
        )
        self.blob_meter.set(0)
        self._sync_zoom_state()

    def _build_previews(self) -> None:
        previews = ttk.Frame(self)
        previews.grid(row=3, column=0, sticky="nsew", padx=10, pady=(5, 6))
        previews.rowconfigure(0, weight=1)
        previews.columnconfigure(0, weight=3, uniform="preview")
        previews.columnconfigure(1, weight=2, uniform="preview")
        previews.columnconfigure(2, weight=2, uniform="preview")

        specs = (
            ("Live area", "Pick a colour here with the pipette."),
            ("Binary mask", "Valid matching pixels are white."),
            ("Isolated colour", "Only matching colour pixels remain."),
        )
        for column, (title, subtitle) in enumerate(specs):
            frame = ttk.LabelFrame(previews, text=title, padding=5)
            frame.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 4, 0),
            )
            frame.rowconfigure(1, weight=1)
            frame.columnconfigure(0, weight=1)
            ttk.Label(
                frame,
                text=subtitle,
                foreground=preset_ui.BASIC_MUTED,
            ).grid(row=0, column=0, sticky="w", pady=(0, 4))
            view = ZoomImageView(
                frame,
                auto_resize=self.auto_resize.get(),
                zoom_percent=self.zoom.get(),
            )
            view.grid(row=1, column=0, sticky="nsew")
            self.views.append(view)

        self.capture_view, self.mask_view, self.isolated_view = self.views
        self.capture_view.bind("<Button-1>", self._pick)

    def _draw_blob_overlay(self, _blob, _safe_bounds=None) -> np.ndarray:
        return self.capture.copy()

    def _selected_sample_size(self) -> int:
        try:
            value = int(self.pipette_sample_size.get())
        except (TypeError, ValueError):
            return 1
        return value if value in SAMPLE_SIZES else 1

    def _pick(self, event) -> None:
        if self.capture is None or not self.pipette:
            return

        point = self.capture_view.image_coordinates(event.x, event.y)
        if point is None:
            return

        x, y = point
        height, width = self.capture.shape[:2]
        padding = PIPETTE_EDGE_PADDING
        if (
            x < padding
            or y < padding
            or x >= width - padding
            or y >= height - padding
        ):
            self.status.set(
                f"Pipet: kies binnen de groene schermrand ({padding}px padding)."
            )
            return

        sample_size = self._selected_sample_size()
        radius = sample_size // 2
        self.ranges = hsv_ranges_around(
            sample_hsv(self.capture, x, y, radius=radius),
            hue_tolerance=5,
            saturation_tolerance=40,
            value_tolerance=40,
        )
        self.current_blob_px = 0
        self.observed_min_px = None
        self.observed_max_px = None
        self.blob_range_text.set("MIN —   MAX —")
        self._last_pipette_point = (x, y)
        self.capture_view.set_marker(x, y, sample_size)
        self._render()
        self.capture_view.set_marker(x, y, sample_size)
        self._update_preset_summary()
        self.status.set(
            f"Colour sampled for preset: {self.current_preset.get()} "
            f"({sample_size}×{sample_size})."
        )

    def _capture(self) -> None:
        overlay = self._screen_area_overlay
        if overlay is not None and not overlay.capture_excluded:
            overlay.hide()
            self.update_idletasks()

        super()._capture()
        if self.capture is None:
            return

        if overlay is None:
            try:
                overlay = ScreenAreaOverlay(self.winfo_toplevel())
            except (tk.TclError, AttributeError):
                overlay = None
            self._screen_area_overlay = overlay

        if overlay is not None:
            overlay.show_region(self.capture_region)

    def deactivate(self) -> None:
        super().deactivate()
        if self._screen_area_overlay is not None:
            self._screen_area_overlay.hide()


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

        style = ttk.Style(self)
        available = style.theme_names()
        if sys.platform == "win32" and "vista" in available:
            style.theme_use("vista")
        style.configure("TNotebook.Tab", padding=(14, 6))

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

        self.colour_host = tk.Frame(
            self.tabs,
            background=preset_ui.BASIC_BG,
        )
        self.template_host = tk.Frame(
            self.tabs,
            background=preset_ui.BASIC_BG,
        )
        self.sensor_host = tk.Frame(
            self.tabs,
            background=preset_ui.BASIC_BG,
        )
        self.tabs.add(self.colour_host, text="Colour")
        self.tabs.add(self.template_host, text="Template")
        self.tabs.add(self.sensor_host, text="Sensor")

        self.colour_page = EnhancedColourPage(self.colour_host)
        self.template_page = modern_ui.TemplatePage(self.template_host)
        self.sensor_page = modern_ui.SensorPage(self.sensor_host)
        for page in (
            self.colour_page,
            self.template_page,
            self.sensor_page,
        ):
            page.pack(fill="both", expand=True)

        self.pages = [
            self.colour_page,
            self.template_page,
            self.sensor_page,
        ]
        self.tabs.bind("<<NotebookTabChanged>>", self._tab_changed)

        self.protocol("WM_DELETE_WINDOW", self._close)
        self._start_hotkeys()
        self.after(50, self._poll_hotkeys)
        self.after(120, self._activate_current_page)

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


__all__ = [
    "EnhancedColourPage",
    "SearchableSourceControls",
    "ScreenAreaOverlay",
    "VisionTester",
    "ZoomImageView",
    "main",
]
