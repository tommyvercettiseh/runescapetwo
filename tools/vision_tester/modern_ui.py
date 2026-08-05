from __future__ import annotations

import sys
import time
import tkinter as tk
from pathlib import Path
from queue import Empty, SimpleQueue
from tkinter import messagebox, simpledialog

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk
from pynput.keyboard import Key as KeyboardKey
from pynput.keyboard import Listener as KeyboardListener

from core import mouse
from core.targeting import (
    MIN_IMAGE_EDGE_PADDING,
    image_target_bounds,
    normalize_image_edge_padding,
)
from core.vision.areas import load_areas
from core.vision.color_matching import calculate_color_score
from core.vision.colour_detection import (
    build_mask_from_ranges,
    count_mask_pixels,
    hsv_ranges_around,
    sample_hsv,
)
from core.vision.models import TemplateSettings
from core.vision.screenshots import capture_area
from core.vision.template_matching import available_methods, iter_candidates, match_template
from core.vision.templates import (
    IMAGES_DIR,
    delete_template,
    load_settings,
    load_template,
    rename_template,
    save_settings,
)
from .colour_debug import (
    BlobMeasurement,
    filter_mask_by_blob_size,
    isolate_colour,
    measure_mask_blobs,
)
from .preferences import load_preferences, save_preferences
from .sensor_checks import SensorCheck, load_sensor_checks
from .sensor_view import analyse_sensor_frame, sensor_description
from .template_capture import TemplateCaptureOverlay


BG = "#0b0906"
CARD = "#17130d"
CARD_ALT = "#211a11"
BORDER = "#4b3923"
CONTROL_HOVER = "#352818"
TEXT = "#e9dfc8"
MUTED = "#aa9a7b"
ACCENT = "#8ec63f"
ACCENT_HOVER = "#75aa2f"
ACCENT_SOFT = "#29371d"
GOLD = "#d1a64b"
DANGER = "#d06655"
SUCCESS = "#8ec63f"
VIEW_BG = "#040403"
DEFAULT_AREA = "Bot_Area_Full"
BLOB_BOX_PADDING = 8


def _format_pixels(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def _label(parent, text: str, *, muted: bool = False, size: int = 12, bold: bool = False, **kwargs):
    text_color = kwargs.pop("text_color", MUTED if muted else TEXT)
    return ctk.CTkLabel(
        parent,
        text=text,
        text_color=text_color,
        font=ctk.CTkFont(size=size, weight="bold" if bold else "normal"),
        **kwargs,
    )


def _button(parent, text: str, command, *, primary: bool = False, danger: bool = False, width=120):
    if primary:
        fg, hover, colour = ACCENT, ACCENT_HOVER, "#111509"
    elif danger:
        fg, hover, colour = "#321a17", "#45221d", "#ef8a78"
    else:
        fg, hover, colour = CARD_ALT, CONTROL_HOVER, TEXT
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=38,
        corner_radius=7,
        fg_color=fg,
        hover_color=hover,
        text_color=colour,
        font=ctk.CTkFont(size=12, weight="bold"),
        border_width=1,
        border_color=BORDER,
    )


def _card(parent, **kwargs):
    return ctk.CTkFrame(
        parent,
        fg_color=kwargs.pop("fg_color", CARD),
        corner_radius=kwargs.pop("corner_radius", 9),
        border_width=kwargs.pop("border_width", 1),
        border_color=kwargs.pop("border_color", BORDER),
        **kwargs,
    )


class ImageView(tk.Label):
    """Image surface with predictable resizing and source-pixel click mapping."""

    def __init__(
        self,
        parent,
        *,
        auto_resize: bool = True,
        zoom_percent: int = 100,
        maximum_upscale: float = 6.0,
    ):
        super().__init__(parent, background=VIEW_BG, borderwidth=0, anchor="center")
        self.auto_resize = auto_resize
        self.zoom_percent = zoom_percent
        self.maximum_upscale = maximum_upscale
        self.scale = 1.0
        self.image_offset = (0, 0)
        self.display_size = (0, 0)
        self._photo: ImageTk.PhotoImage | None = None
        self._last_rgb: np.ndarray | None = None
        self._job: str | None = None
        self.bind("<Configure>", self._schedule)

    def show(self, rgb: np.ndarray) -> None:
        self._last_rgb = rgb
        self._draw()

    def set_view(self, *, auto_resize: bool, zoom_percent: int) -> None:
        self.auto_resize = auto_resize
        self.zoom_percent = min(100, max(10, int(zoom_percent)))
        self._draw()

    def _schedule(self, _event=None) -> None:
        if self._last_rgb is None:
            return
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(60, self._draw)

    def _draw(self) -> None:
        self._job = None
        if self._last_rgb is None:
            return
        rgb = self._last_rgb
        height, width = rgb.shape[:2]
        target_width = max(1, self.winfo_width())
        target_height = max(1, self.winfo_height())
        fit = min(target_width / width, target_height / height)
        self.scale = min(self.maximum_upscale, fit) if self.auto_resize else min(
            self.zoom_percent / 100.0,
            fit,
        )
        display_width = max(1, int(width * self.scale))
        display_height = max(1, int(height * self.scale))
        self.display_size = (display_width, display_height)
        self.image_offset = (
            max(0, (target_width - display_width) // 2),
            max(0, (target_height - display_height) // 2),
        )
        resized = cv2.resize(
            rgb,
            self.display_size,
            interpolation=cv2.INTER_AREA if self.scale < 1 else cv2.INTER_NEAREST,
        )
        self._photo = ImageTk.PhotoImage(Image.fromarray(resized))
        self.configure(image=self._photo)

    def image_coordinates(self, x: int, y: int) -> tuple[int, int] | None:
        offset_x, offset_y = self.image_offset
        width, height = self.display_size
        relative_x, relative_y = x - offset_x, y - offset_y
        if not 0 <= relative_x < width or not 0 <= relative_y < height:
            return None
        return int(relative_x / self.scale), int(relative_y / self.scale)


class SourceControls(ctk.CTkFrame):
    def __init__(self, parent, *, default_area: str = DEFAULT_AREA):
        super().__init__(parent, fg_color="transparent")
        areas = sorted(load_areas())
        self.bot_id = tk.StringVar(value="1")
        self.area = tk.StringVar(value=default_area if default_area in areas else (areas[0] if areas else "game"))

        _label(self, "BOT ID", muted=True, size=11).grid(row=0, column=0, sticky="w")
        ctk.CTkOptionMenu(
            self,
            values=["1", "2", "3", "4"],
            variable=self.bot_id,
            width=76,
            height=38,
            corner_radius=8,
            fg_color=CARD_ALT,
            button_color=BORDER,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT,
        ).grid(row=1, column=0, padx=(0, 12), pady=(4, 0), sticky="w")
        _label(self, "AREA", muted=True, size=11).grid(row=0, column=1, sticky="w")
        self.area_box = ctk.CTkComboBox(
            self,
            values=areas,
            variable=self.area,
            height=38,
            corner_radius=8,
            fg_color=CARD_ALT,
            border_color=BORDER,
            button_color=BORDER,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT,
        )
        self.area_box.grid(row=1, column=1, pady=(4, 0), sticky="ew")
        self.grid_columnconfigure(1, weight=1)

    def bot(self) -> int:
        return int(self.bot_id.get())


class ColourPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        preferences = load_preferences()
        self.live = tk.BooleanVar(value=False)
        self.pipette = False
        self.minimum = tk.StringVar(value="20")
        self.maximum = tk.StringVar(value="0")
        self.auto_resize = tk.BooleanVar(value=bool(preferences["auto_resize"]))
        self.zoom = tk.IntVar(value=int(preferences["zoom_percent"]))
        self.status = tk.StringVar(value="Kies een area en maak een capture.")
        self.blob_live_text = tk.StringVar(value="— PX")
        self.blob_range_text = tk.StringVar(value="MIN —   MAX —")
        self.capture: np.ndarray | None = None
        self.ranges = ()
        self.current_blob_px = 0
        self.observed_min_px: int | None = None
        self.observed_max_px: int | None = None
        self.views: list[ImageView] = []
        self._save_job: str | None = None
        self._build()
        self.after(100, self._tick)

    def activate(self) -> None:
        self.live.set(True)
        self.status.set("Live capture actief.")
        self.after_idle(self._capture)

    def deactivate(self) -> None:
        self.live.set(False)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        toolbar = _card(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 10))
        toolbar.grid_columnconfigure(0, weight=1)
        self.source = SourceControls(toolbar)
        self.source.grid(row=0, column=0, sticky="ew", padx=16, pady=14)

        actions = ctk.CTkFrame(toolbar, fg_color="transparent")
        actions.grid(row=0, column=1, padx=(0, 16), pady=14)
        ctk.CTkSwitch(
            actions,
            text="Live",
            variable=self.live,
            command=self._toggle_live,
            progress_color=ACCENT,
            button_color=TEXT,
            button_hover_color=GOLD,
            text_color=TEXT,
        ).grid(row=0, column=0, padx=(0, 10))
        _button(actions, "Capture", self._once, primary=True, width=105).grid(row=0, column=1)

        viewbar = _card(self)
        viewbar.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        viewbar.grid_columnconfigure(1, weight=1)

        limits = ctk.CTkFrame(viewbar, fg_color="transparent")
        limits.grid(row=0, column=0, padx=(14, 18), pady=10, sticky="w")
        for column, (title, variable) in enumerate((("MIN BLOB PX", self.minimum), ("MAX BLOB PX", self.maximum))):
            group = ctk.CTkFrame(limits, fg_color="transparent")
            group.grid(row=0, column=column, padx=(0, 8))
            _label(group, title, muted=True, size=10).pack(anchor="w")
            entry = ctk.CTkEntry(
                group,
                textvariable=variable,
                width=94,
                height=32,
                corner_radius=7,
                fg_color=CARD_ALT,
                border_color=BORDER,
                text_color=TEXT,
            )
            entry.pack(pady=(2, 0))
            entry.bind("<KeyRelease>", lambda _event: self._render())

        tracker = ctk.CTkFrame(viewbar, fg_color="transparent")
        tracker.grid(row=0, column=1, sticky="ew", padx=(0, 18), pady=9)
        tracker.grid_columnconfigure(1, weight=1)
        _label(tracker, "LIVE BLOB", muted=True, size=10).grid(row=0, column=0, sticky="w")
        _label(
            tracker,
            "",
            textvariable=self.blob_live_text,
            text_color=ACCENT,
            size=13,
            bold=True,
        ).grid(row=0, column=1, sticky="w", padx=(8, 14))
        _label(tracker, "", textvariable=self.blob_range_text, muted=True, size=10).grid(
            row=0,
            column=2,
            sticky="e",
            padx=(0, 10),
        )
        _button(tracker, "Reset", self._reset_blob_history, width=68).grid(row=0, column=3, rowspan=2)
        self.blob_meter = ctk.CTkProgressBar(
            tracker,
            height=8,
            corner_radius=4,
            fg_color=BORDER,
            progress_color=ACCENT,
        )
        self.blob_meter.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0), padx=(0, 10))
        self.blob_meter.set(0)

        display = ctk.CTkFrame(viewbar, fg_color="transparent")
        display.grid(row=0, column=2, padx=(0, 14), pady=10, sticky="e")
        _label(display, "WEERGAVE", muted=True, size=10).grid(row=0, column=0, sticky="w")
        self.auto_switch = ctk.CTkSwitch(
            display,
            text="Auto resize",
            variable=self.auto_resize,
            command=self._view_changed,
            progress_color=ACCENT,
            text_color=TEXT,
        )
        self.auto_switch.grid(row=1, column=0, padx=(0, 12), pady=(3, 0))
        self.zoom_label = _label(display, f"Zoom {self.zoom.get()}%", size=10, bold=True)
        self.zoom_label.grid(row=1, column=1, padx=(0, 7), pady=(3, 0))
        self.zoom_slider = ctk.CTkSlider(
            display,
            from_=10,
            to=100,
            number_of_steps=90,
            variable=self.zoom,
            command=self._zoom_changed,
            width=150,
            progress_color=ACCENT,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            fg_color=BORDER,
        )
        self.zoom_slider.grid(row=1, column=2, pady=(3, 0))
        self._sync_zoom_state()

        previews = ctk.CTkFrame(self, fg_color="transparent")
        previews.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        previews.grid_rowconfigure(0, weight=1)
        for column in range(3):
            previews.grid_columnconfigure(column, weight=1, uniform="preview")
        specs = (
            ("LIVE AREA", "Klik met het pipet om een kleur te kiezen"),
            ("BINAIR MASKER", "Alleen geldige blobs zijn wit"),
            ("KLEUR GEÏSOLEERD", "Alleen geldige kleurpixels blijven staan"),
        )
        for column, (title, subtitle) in enumerate(specs):
            card = _card(previews)
            card.grid(row=0, column=column, sticky="nsew", padx=4)
            heading = ctk.CTkFrame(card, fg_color="transparent")
            heading.pack(fill="x", padx=14, pady=(10, 0))
            _label(heading, title, size=12, bold=True).pack(side="left")
            if column == 0:
                self.pipette_button = _button(
                    heading,
                    "⌖  Pipet",
                    self._toggle_pipette,
                    width=92,
                )
                self.pipette_button.pack(side="right")
            _label(card, subtitle, muted=True, size=11).pack(anchor="w", padx=14, pady=(0, 10))
            view = ImageView(
                card,
                auto_resize=self.auto_resize.get(),
                zoom_percent=self.zoom.get(),
            )
            view.pack(fill="both", expand=True, padx=12, pady=(0, 12))
            self.views.append(view)
        self.capture_view, self.mask_view, self.isolated_view = self.views
        self.capture_view.bind("<Button-1>", self._pick)

        status = _card(self)
        status.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 12))
        _label(status, "", size=11, textvariable=self.status).pack(anchor="w", padx=14, pady=9)

    def _toggle_live(self) -> None:
        self.status.set("Live capture actief." if self.live.get() else "Live capture gepauzeerd.")

    def _once(self) -> None:
        self.live.set(False)
        self._capture()

    def capture_hotkey(self) -> None:
        self._once()

    def _tick(self) -> None:
        if self.live.get():
            self._capture()
        self.after(100, self._tick)

    def _capture(self) -> None:
        started = time.perf_counter()
        try:
            self.capture, _region = capture_area(self.source.area.get(), bot_id=self.source.bot())
            self._render(started)
        except Exception as exc:
            self.live.set(False)
            self.status.set(f"Fout: {exc}")

    def _limits(self) -> tuple[int, int | None]:
        minimum = max(1, int(self.minimum.get() or 1))
        maximum = int(self.maximum.get() or 0)
        return minimum, maximum or None

    def _render(self, started: float | None = None) -> None:
        if self.capture is None:
            return
        try:
            minimum, maximum = self._limits()
        except ValueError:
            return
        if not self.ranges:
            self.capture_view.show(self.capture)
            blank = np.zeros(self.capture.shape[:2], dtype=np.uint8)
            self.mask_view.show(cv2.cvtColor(blank, cv2.COLOR_GRAY2RGB))
            self.isolated_view.show(np.zeros_like(self.capture))
            return
        started = time.perf_counter() if started is None else started
        raw_mask = build_mask_from_ranges(self.capture, self.ranges)
        blobs = measure_mask_blobs(raw_mask)
        dominant_blob = blobs[0] if blobs else None
        self._observe_blob(dominant_blob)
        self.capture_view.show(self._draw_blob_overlay(dominant_blob))
        mask, blob_count = filter_mask_by_blob_size(
            raw_mask,
            minimum_area_px=minimum,
            maximum_area_px=maximum,
        )
        pixels = count_mask_pixels(mask)
        self.mask_view.show(cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB))
        self.isolated_view.show(isolate_colour(self.capture, mask))
        elapsed = (time.perf_counter() - started) * 1000
        self.status.set(
            f"Bot {self.source.bot()}  •  {self.source.area.get()}  •  "
            f"{pixels} px  •  {blob_count} geldige blobs  •  {elapsed:.1f} ms"
        )

    def _observe_blob(self, blob: BlobMeasurement | None) -> None:
        if blob is None:
            self.current_blob_px = 0
            self.blob_live_text.set("— PX")
            self.blob_meter.set(0)
            return

        pixels = blob.area_px
        self.current_blob_px = pixels
        self.observed_min_px = pixels if self.observed_min_px is None else min(self.observed_min_px, pixels)
        self.observed_max_px = pixels if self.observed_max_px is None else max(self.observed_max_px, pixels)
        self.blob_live_text.set(f"{_format_pixels(pixels)} PX")
        self.blob_range_text.set(
            f"MIN {_format_pixels(self.observed_min_px)}   "
            f"MAX {_format_pixels(self.observed_max_px)}"
        )
        span = self.observed_max_px - self.observed_min_px
        position = 0.5 if span == 0 else (pixels - self.observed_min_px) / span
        self.blob_meter.set(position)

    def _reset_blob_history(self) -> None:
        current = self.current_blob_px or None
        self.observed_min_px = current
        self.observed_max_px = current
        if current is None:
            self.blob_range_text.set("MIN —   MAX —")
            self.blob_meter.set(0)
        else:
            formatted = _format_pixels(current)
            self.blob_range_text.set(f"MIN {formatted}   MAX {formatted}")
            self.blob_meter.set(0.5)

    def _draw_blob_overlay(self, blob: BlobMeasurement | None) -> np.ndarray:
        visual = self.capture.copy()
        if blob is None:
            return visual
        height, width = visual.shape[:2]
        left = max(0, blob.x - BLOB_BOX_PADDING)
        top = max(0, blob.y - BLOB_BOX_PADDING)
        right = min(width - 1, blob.x + blob.width - 1 + BLOB_BOX_PADDING)
        bottom = min(height - 1, blob.y + blob.height - 1 + BLOB_BOX_PADDING)
        cv2.rectangle(visual, (left, top), (right, bottom), (142, 198, 63), 2)
        label = f"{_format_pixels(blob.area_px)} PX"
        label_above = top >= 24
        label_top = top - 22 if label_above else top
        label_bottom = top if label_above else min(height - 1, top + 22)
        text_y = top - 6 if label_above else min(height - 5, top + 16)
        label_width = max(78, len(label) * 8)
        cv2.rectangle(
            visual,
            (left, label_top),
            (min(width - 1, left + label_width), label_bottom),
            (23, 19, 13),
            -1,
        )
        cv2.putText(
            visual,
            label,
            (left + 5, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (142, 198, 63),
            1,
            cv2.LINE_AA,
        )
        return visual

    def _toggle_pipette(self) -> None:
        self.pipette = not self.pipette
        self.pipette_button.configure(
            fg_color=ACCENT_SOFT if self.pipette else CARD_ALT,
            text_color=ACCENT_HOVER if self.pipette else TEXT,
        )
        self.capture_view.configure(cursor="crosshair" if self.pipette else "")
        self.status.set("Pipet actief. Klik in Live Area." if self.pipette else "Pipet uitgeschakeld.")

    def _pick(self, event) -> None:
        if self.capture is None or not self.pipette:
            return
        point = self.capture_view.image_coordinates(event.x, event.y)
        if point is None:
            return
        x, y = point
        self.ranges = hsv_ranges_around(
            sample_hsv(self.capture, x, y, radius=2),
            hue_tolerance=5,
            saturation_tolerance=40,
            value_tolerance=40,
        )
        self.current_blob_px = 0
        self.observed_min_px = None
        self.observed_max_px = None
        self.blob_range_text.set("MIN —   MAX —")
        self._render()

    def _view_changed(self) -> None:
        self._sync_zoom_state()
        self._apply_view()

    def _zoom_changed(self, value) -> None:
        self.zoom.set(round(float(value)))
        self.zoom_label.configure(text=f"Zoom {self.zoom.get()}%")
        if not self.auto_resize.get():
            self._apply_view()

    def _sync_zoom_state(self) -> None:
        self.zoom_slider.configure(state="disabled" if self.auto_resize.get() else "normal")

    def _apply_view(self) -> None:
        for view in self.views:
            view.set_view(auto_resize=self.auto_resize.get(), zoom_percent=self.zoom.get())
        if self._save_job is not None:
            self.after_cancel(self._save_job)
        self._save_job = self.after(180, self._save_preferences)

    def _save_preferences(self) -> None:
        self._save_job = None
        try:
            save_preferences({"auto_resize": self.auto_resize.get(), "zoom_percent": self.zoom.get()})
        except OSError:
            pass


class TemplatePage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.live = tk.BooleanVar(value=False)
        self.query = tk.StringVar()
        self.selected: str | None = None
        self.method = tk.StringVar(value="TM_CCOEFF_NORMED")
        self.shape = tk.DoubleVar(value=85.0)
        self.colour = tk.DoubleVar(value=60.0)
        self.maximum = tk.StringVar(value="30")
        self.x_padding = tk.StringVar(value="20")
        self.status = tk.StringVar(value="Selecteer een template of maak een nieuwe screenshot.")
        self.templates: list[str] = []
        self.rows: dict[str, ctk.CTkButton] = {}
        self.screenshot: np.ndarray | None = None
        self.region = None
        self.best_valid_bounds: tuple[int, int, int, int] | None = None
        self._job: str | None = None
        self._build()
        self.after(100, self._tick)

    def activate(self) -> None:
        self.live.set(True)
        self.status.set("Live matching actief.")
        self.after_idle(self._capture)

    def deactivate(self) -> None:
        self.live.set(False)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        toolbar = _card(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 10))
        toolbar.grid_columnconfigure(0, weight=1)
        self.source = SourceControls(toolbar)
        self.source.grid(row=0, column=0, sticky="ew", padx=16, pady=14)
        actions = ctk.CTkFrame(toolbar, fg_color="transparent")
        actions.grid(row=0, column=1, padx=16, pady=14)
        _button(actions, "Nieuwe template", self._new_template, width=150).grid(row=0, column=0, padx=(0, 10))
        ctk.CTkSwitch(
            actions,
            text="Live",
            variable=self.live,
            command=self._toggle_live,
            progress_color=ACCENT,
            text_color=TEXT,
        ).grid(row=0, column=1, padx=(0, 12))
        _button(actions, "Capture", self._once, primary=True, width=105).grid(row=0, column=2)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)

        sidebar = _card(content, width=270)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(2, weight=1)
        _label(sidebar, "TEMPLATES", size=12, bold=True).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))
        search = ctk.CTkEntry(
            sidebar,
            textvariable=self.query,
            placeholder_text="Zoek template",
            height=38,
            corner_radius=8,
            fg_color=CARD_ALT,
            border_color=BORDER,
            text_color=TEXT,
        )
        search.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        search.bind("<KeyRelease>", lambda _event: self._draw_templates())
        self.template_scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=GOLD,
        )
        self.template_scroll.grid(row=2, column=0, sticky="nsew", padx=8)
        self.template_scroll.grid_columnconfigure(0, weight=1)
        template_actions = ctk.CTkFrame(sidebar, fg_color="transparent")
        template_actions.grid(row=3, column=0, sticky="ew", padx=14, pady=12)
        template_actions.grid_columnconfigure(0, weight=1)
        template_actions.grid_columnconfigure(1, weight=1)
        _button(template_actions, "Hernoem", self._rename, width=108).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        _button(template_actions, "Verwijder", self._delete, danger=True, width=108).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        center = _card(content)
        center.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        center.grid_rowconfigure(2, weight=1)
        center.grid_columnconfigure(0, weight=1)
        _label(center, "LIVE AREA", size=12, bold=True).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 0))
        target_actions = ctk.CTkFrame(center, fg_color="transparent")
        target_actions.grid(row=0, column=0, sticky="e", padx=14, pady=(8, 0))
        _label(target_actions, "X PADDING ≥", muted=True, size=10).grid(row=0, column=0, padx=(0, 5))
        x_padding_entry = ctk.CTkEntry(
            target_actions,
            textvariable=self.x_padding,
            width=48,
            height=34,
            corner_radius=7,
            fg_color=CARD_ALT,
            border_color=BORDER,
            text_color=TEXT,
        )
        x_padding_entry.grid(row=0, column=1, padx=(0, 4))
        x_padding_entry.bind("<KeyRelease>", lambda _event: self._schedule())
        _label(target_actions, "%", muted=True, size=10).grid(row=0, column=2, padx=(0, 8))
        _button(
            target_actions,
            "Muis naar image",
            self._move_to_image,
            width=150,
        ).grid(row=0, column=3)
        _label(center, "Groen geldig · rood faalt · goud is de veilige muiszone", muted=True, size=11).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))
        self.preview = ImageView(center)
        self.preview.grid(row=2, column=0, sticky="nsew", padx=12)
        self.results = ctk.CTkTextbox(
            center,
            height=118,
            corner_radius=8,
            fg_color=CARD_ALT,
            border_color=BORDER,
            border_width=1,
            text_color=TEXT,
            font=ctk.CTkFont(family="Consolas", size=11),
        )
        self.results.grid(row=3, column=0, sticky="ew", padx=12, pady=12)
        self.results.insert("1.0", "Nog geen analyse uitgevoerd.")
        self.results.configure(state="disabled")

        panel = _card(content, width=320)
        panel.grid(row=0, column=2, sticky="nsew")
        panel.grid_propagate(False)
        _label(panel, "DETECTIE INSTELLEN", size=12, bold=True).pack(anchor="w", padx=16, pady=(14, 0))
        _label(panel, "Wijzig live en sla op voor productie.", muted=True, size=11).pack(anchor="w", padx=16, pady=(0, 18))
        _label(panel, "METHODE", muted=True, size=11).pack(anchor="w", padx=16)
        self.method_box = ctk.CTkOptionMenu(
            panel,
            values=list(available_methods()),
            variable=self.method,
            command=lambda _value: self._schedule(),
            height=38,
            corner_radius=8,
            fg_color=CARD_ALT,
            button_color=BORDER,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT,
        )
        self.method_box.pack(fill="x", padx=16, pady=(4, 18))
        self.shape_label, self.shape_slider = self._slider(panel, "SHAPE THRESHOLD", self.shape, self._threshold_changed)
        self.colour_label, self.colour_slider = self._slider(panel, "COLOUR THRESHOLD", self.colour, self._threshold_changed)
        _label(panel, "MAX HITS", muted=True, size=11).pack(anchor="w", padx=16)
        max_entry = ctk.CTkEntry(
            panel,
            textvariable=self.maximum,
            width=100,
            height=38,
            corner_radius=8,
            fg_color=CARD_ALT,
            border_color=BORDER,
            text_color=TEXT,
        )
        max_entry.pack(anchor="w", padx=16, pady=(4, 18))
        max_entry.bind("<KeyRelease>", lambda _event: self._schedule())
        _button(panel, "Instellingen opslaan", self._save, primary=True, width=288).pack(padx=16, fill="x")
        self.summary = _label(panel, "Beste shape —\nKleur daarbij —\nGeldige hits —", muted=True, size=12, justify="left")
        self.summary.pack(anchor="w", padx=16, pady=(20, 0))

        status = _card(self)
        status.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        _label(status, "", textvariable=self.status, muted=True, size=11).pack(anchor="w", padx=14, pady=9)
        self._refresh_templates()

    def _slider(self, parent, title, variable, command):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16)
        _label(row, title, muted=True, size=11).pack(side="left")
        value = _label(row, f"{variable.get():.1f}%", size=11, bold=True)
        value.pack(side="right")
        slider = ctk.CTkSlider(
            parent,
            from_=0,
            to=100,
            number_of_steps=200,
            variable=variable,
            command=command,
            progress_color=ACCENT,
            button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            fg_color=BORDER,
        )
        slider.pack(fill="x", padx=16, pady=(6, 18))
        return value, slider

    def _refresh_templates(self, preferred: str | None = None) -> None:
        self.templates = sorted(path.name for path in Path(IMAGES_DIR).glob("*.png"))
        if preferred in self.templates:
            self.selected = preferred
        elif self.selected not in self.templates:
            self.selected = self.templates[0] if self.templates else None
        self._draw_templates()
        if self.selected:
            self._select(self.selected)

    def _draw_templates(self) -> None:
        for child in self.template_scroll.winfo_children():
            child.destroy()
        query = self.query.get().strip().casefold()
        names = [name for name in self.templates if query in name.casefold()]
        self.rows.clear()
        for row, name in enumerate(names):
            selected = name == self.selected
            button = ctk.CTkButton(
                self.template_scroll,
                text=name,
                command=lambda value=name: self._select(value),
                anchor="w",
                height=34,
                corner_radius=7,
                fg_color=ACCENT_SOFT if selected else "transparent",
                hover_color=ACCENT_SOFT,
                text_color=ACCENT_HOVER if selected else TEXT,
            )
            button.grid(row=row, column=0, sticky="ew", pady=1)
            self.rows[name] = button

    def _select(self, name: str) -> None:
        self.selected = name
        self.best_valid_bounds = None
        self._draw_templates()
        try:
            settings = load_settings(name)
            self.method.set(settings.method)
            self.shape.set(settings.min_shape)
            self.colour.set(settings.min_color)
            self._update_threshold_labels()
            self.status.set(f"{name} geladen. Thresholds zijn live aanpasbaar.")
            self._schedule()
        except Exception as exc:
            self.status.set(f"Fout: {exc}")

    def _toggle_live(self) -> None:
        self.status.set("Live matching actief." if self.live.get() else "Live matching gepauzeerd.")

    def _once(self) -> None:
        self.live.set(False)
        self._capture()

    def capture_hotkey(self) -> None:
        self._once()

    def _tick(self) -> None:
        if self.live.get():
            self._capture()
        self.after(100, self._tick)

    def _capture(self) -> None:
        if not self.selected:
            self.status.set("Selecteer eerst een template.")
            return
        try:
            self.screenshot, self.region = capture_area(self.source.area.get(), bot_id=self.source.bot())
            self._analyse()
        except Exception as exc:
            self.live.set(False)
            self.status.set(f"Fout: {exc}")

    def _threshold_changed(self, _value=None) -> None:
        self._update_threshold_labels()
        self._schedule()

    def _update_threshold_labels(self) -> None:
        self.shape_label.configure(text=f"{self.shape.get():.1f}%")
        self.colour_label.configure(text=f"{self.colour.get():.1f}%")

    def _schedule(self) -> None:
        if self.screenshot is None:
            return
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(70, self._analyse)

    def _analyse(self) -> None:
        self._job = None
        self.best_valid_bounds = None
        if self.screenshot is None or not self.selected:
            return
        started = time.perf_counter()
        try:
            template_rgb, template_gray = load_template(self.selected)
            gray = cv2.cvtColor(self.screenshot, cv2.COLOR_RGB2GRAY)
            height, width = template_gray.shape[:2]
            if gray.shape[0] < height or gray.shape[1] < width:
                raise ValueError("Template is groter dan de geselecteerde area")
            scores = match_template(gray, template_gray, self.method.get())
            _min, best_score, _minloc, best_location = cv2.minMaxLoc(scores)
            visual = self.screenshot.copy()
            rows = []
            valid_count = 0
            maximum = max(1, int(self.maximum.get() or 1))
            for x, y, score in iter_candidates(
                scores,
                self.shape.get() / 100,
                width,
                height,
                maximum_candidates=maximum,
            ):
                patch = self.screenshot[y : y + height, x : x + width]
                colour = calculate_color_score(template_rgb, patch)
                valid = colour >= self.colour.get()
                valid_count += int(valid)
                rows.append((valid, score * 100, colour, x, y))
                cv2.rectangle(
                    visual,
                    (x, y),
                    (x + width, y + height),
                    (37, 169, 105) if valid else (220, 82, 104),
                    2,
                )
            best_x, best_y = best_location
            best_colour = calculate_color_score(
                template_rgb,
                self.screenshot[best_y : best_y + height, best_x : best_x + width],
            )
            valid_rows = [row for row in rows if row[0]]
            if valid_rows:
                _valid, _shape, _colour, target_x, target_y = max(
                    valid_rows,
                    key=lambda row: (row[1], row[2]),
                )
                padding_percent = self._x_padding_percent()
                local_bounds = image_target_bounds(
                    target_x,
                    target_y,
                    target_x + width,
                    target_y + height,
                    image_edge_padding=padding_percent,
                )
                origin_x, origin_y = self.region[0], self.region[1]
                self.best_valid_bounds = (
                    local_bounds[0] + origin_x,
                    local_bounds[1] + origin_y,
                    local_bounds[2] + origin_x,
                    local_bounds[3] + origin_y,
                )
                cv2.rectangle(
                    visual,
                    (local_bounds[0], local_bounds[1]),
                    (local_bounds[2], local_bounds[3]),
                    (209, 166, 75),
                    1,
                )
            self.preview.show(visual)
            lines = ["STATUS         SHAPE    COLOUR      X      Y"]
            lines.extend(
                f"{'GELDIG' if valid else 'KLEUR FAALT':<14} {shape:>5.1f}%   {colour:>5.1f}%   {x:>4}   {y:>4}"
                for valid, shape, colour, x, y in rows
            )
            self.results.configure(state="normal")
            self.results.delete("1.0", "end")
            self.results.insert("1.0", "\n".join(lines))
            self.results.configure(state="disabled")
            self.summary.configure(
                text=(
                    f"Beste shape  {best_score * 100:.1f}%\n"
                    f"Kleur daarbij  {best_colour:.1f}%\n"
                    f"Geldige hits  {valid_count}/{len(rows)}"
                )
            )
            elapsed = (time.perf_counter() - started) * 1000
            self.status.set(
                f"Bot {self.source.bot()}  •  {self.source.area.get()}  •  "
                f"{self.method.get()}  •  {elapsed:.1f} ms"
            )
        except Exception as exc:
            self.live.set(False)
            self.status.set(f"Fout: {exc}")

    def _x_padding_percent(self) -> float:
        try:
            value = float(self.x_padding.get().strip().replace(",", "."))
        except ValueError:
            value = MIN_IMAGE_EDGE_PADDING
        return normalize_image_edge_padding(value)

    def _move_to_image(self) -> None:
        self.live.set(False)
        if self.best_valid_bounds is None:
            self._capture()
        if self.best_valid_bounds is None:
            self.status.set("Geen geldige image gevonden om naartoe te bewegen.")
            return

        padding_percent = self._x_padding_percent()
        self.x_padding.set(f"{padding_percent:g}")
        left, top, right, bottom = self.best_valid_bounds
        try:
            mouse.move_to_target(
                left,
                top,
                right,
                bottom,
                keep_pending_click=False,
            )
            error = mouse.last_engine_error()
            if error:
                self.status.set(f"Muis bewogen via fallback · Mouse Engine: {error}")
            else:
                x, y = mouse.position()
                self.status.set(
                    f"Muis naar {self.selected} bewogen · ({x}, {y}) · "
                    f"X-padding {padding_percent:g}% · niet geklikt"
                )
        except Exception as exc:
            self.status.set(f"Muis bewegen mislukt: {exc}")

    def _save(self) -> None:
        if not self.selected:
            return
        try:
            save_settings(
                self.selected,
                TemplateSettings(
                    self.method.get(),
                    self.shape.get(),
                    self.colour.get(),
                    self.source.area.get() or None,
                ),
            )
            self.status.set(f"Instellingen voor {self.selected} opgeslagen.")
        except Exception as exc:
            messagebox.showerror("Template", str(exc), parent=self)

    def _new_template(self) -> None:
        self.live.set(False)
        TemplateCaptureOverlay(self, self._captured)

    def _captured(self, name: str) -> None:
        save_settings(
            name,
            TemplateSettings(
                self.method.get(),
                self.shape.get(),
                self.colour.get(),
                self.source.area.get() or None,
            ),
        )
        self._refresh_templates(name)
        self.status.set(f"Nieuwe template {name} opgeslagen.")

    def _rename(self) -> None:
        if not self.selected:
            return
        value = simpledialog.askstring(
            "Template hernoemen",
            "Nieuwe naam:",
            initialvalue=Path(self.selected).stem,
            parent=self,
        )
        if not value:
            return
        try:
            self._refresh_templates(rename_template(self.selected, value))
        except Exception as exc:
            messagebox.showerror("Template", str(exc), parent=self)

    def _delete(self) -> None:
        if not self.selected or not messagebox.askyesno(
            "Template verwijderen",
            f"{self.selected} definitief verwijderen?",
            parent=self,
        ):
            return
        try:
            delete_template(self.selected)
            self.selected = None
            self.screenshot = None
            self._refresh_templates()
        except Exception as exc:
            messagebox.showerror("Template", str(exc), parent=self)


class SensorPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self.live = tk.BooleanVar(value=False)
        self.sensor_name = tk.StringVar()
        self.bot_id = tk.StringVar(value="1")
        self.status = tk.StringVar(value="Sensoren worden geladen.")
        self.description = tk.StringVar(value="Kies een sensor.")
        self.checks: dict[str, SensorCheck] = {}
        self._build()
        self._load()
        self.after(150, self._tick)

    def activate(self) -> None:
        self.live.set(True)
        self.status.set("Live sensormeting actief.")
        self.after_idle(self._measure)

    def deactivate(self) -> None:
        self.live.set(False)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        toolbar = _card(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 10))
        toolbar.grid_columnconfigure(0, weight=1)
        group = ctk.CTkFrame(toolbar, fg_color="transparent")
        group.grid(row=0, column=0, sticky="ew", padx=16, pady=14)
        _label(group, "SENSOR", muted=True, size=11).pack(anchor="w")
        self.sensor_box = ctk.CTkComboBox(
            group,
            variable=self.sensor_name,
            values=[],
            command=lambda _value: self._changed(),
            height=38,
            corner_radius=8,
            fg_color=CARD_ALT,
            border_color=BORDER,
            button_color=BORDER,
            button_hover_color=CONTROL_HOVER,
            text_color=TEXT,
        )
        self.sensor_box.pack(fill="x", pady=(4, 0))
        actions = ctk.CTkFrame(toolbar, fg_color="transparent")
        actions.grid(row=0, column=1, padx=16, pady=14)
        ctk.CTkOptionMenu(
            actions,
            values=["1", "2", "3", "4"],
            variable=self.bot_id,
            width=76,
            fg_color=CARD_ALT,
            button_color=BORDER,
            text_color=TEXT,
        ).grid(row=0, column=0, padx=(0, 10))
        ctk.CTkSwitch(
            actions,
            text="Live",
            variable=self.live,
            progress_color=ACCENT,
            text_color=TEXT,
        ).grid(row=0, column=1, padx=(0, 10))
        _button(actions, "Meten", self._once, primary=True, width=100).grid(row=0, column=2)

        desc = _card(self)
        desc.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        _label(desc, "", textvariable=self.description, size=12, wraplength=1200, justify="left").pack(anchor="w", padx=16, pady=12)

        previews = ctk.CTkFrame(self, fg_color="transparent")
        previews.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        previews.grid_rowconfigure(0, weight=1)
        previews.grid_columnconfigure(0, weight=1, uniform="sensor")
        previews.grid_columnconfigure(1, weight=1, uniform="sensor")
        self.views = []
        for column, title in enumerate(("LIVE SENSOR AREA", "WAT DE SENSOR ZIET")):
            card = _card(previews)
            card.grid(row=0, column=column, sticky="nsew", padx=4)
            _label(card, title, size=12, bold=True).pack(anchor="w", padx=14, pady=12)
            view = ImageView(card)
            view.pack(fill="both", expand=True, padx=12, pady=(0, 12))
            self.views.append(view)
        self.live_view, self.detected_view = self.views

        result = _card(self)
        result.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 10))
        self.measurement = _label(result, "Nog niet gemeten", size=13)
        self.measurement.pack(side="left", padx=16, pady=12)
        self.outcome = _label(result, "—", size=20, bold=True)
        self.outcome.pack(side="right", padx=18, pady=10)
        status = _card(self)
        status.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 12))
        _label(status, "", textvariable=self.status, muted=True, size=11).pack(anchor="w", padx=14, pady=9)

    def _load(self) -> None:
        self.checks = {name: check for name, check in load_sensor_checks().items() if check.enabled}
        names = sorted(self.checks)
        self.sensor_box.configure(values=names)
        if names:
            self.sensor_name.set(names[0])
            self._changed()

    def _changed(self) -> None:
        check = self.checks.get(self.sensor_name.get())
        if check:
            self.description.set(sensor_description(check))
            self.status.set(f"Klaar voor meting: {check.name} gebruikt area '{check.area}'.")

    def _once(self) -> None:
        self.live.set(False)
        self._measure()

    def capture_hotkey(self) -> None:
        self._once()

    def _tick(self) -> None:
        if self.live.get():
            self._measure()
        self.after(150, self._tick)

    def _measure(self) -> None:
        check = self.checks.get(self.sensor_name.get())
        if not check:
            return
        started = time.perf_counter()
        try:
            screenshot, region = capture_area(check.area, bot_id=int(self.bot_id.get()))
            frame = analyse_sensor_frame(screenshot, check, origin=(region[0], region[1]))
            self.live_view.show(screenshot)
            self.detected_view.show(frame.detected)
            self.measurement.configure(text=f"Gevonden {frame.found} {frame.unit}  •  Benodigd {frame.required} {frame.unit}")
            self.outcome.configure(
                text="TRUE" if frame.result else "FALSE",
                text_color=SUCCESS if frame.result else DANGER,
            )
            elapsed = (time.perf_counter() - started) * 1000
            self.status.set(f"Bot {self.bot_id.get()}  •  {check.name}  •  {elapsed:.1f} ms")
        except Exception as exc:
            self.live.set(False)
            self.status.set(f"Fout: {exc}")


class VisionTester(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")
        super().__init__(fg_color=BG)
        self.title("RuneScape Two - Unified Vision Tester")
        self.geometry("1500x920")
        self.minsize(1180, 760)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.pages: dict[str, ctk.CTkFrame] = {}
        self.current_page: ctk.CTkFrame | None = None
        self._hotkey_events: SimpleQueue[str] = SimpleQueue()
        self._hotkey_listener: KeyboardListener | None = None
        self._last_f2_at = 0.0
        self._closing = False

        header = _card(self)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 10))
        header.grid_columnconfigure(1, weight=1)
        copy = ctk.CTkFrame(header, fg_color="transparent")
        copy.grid(row=0, column=0, sticky="w", padx=(18, 28), pady=12)
        ctk.CTkLabel(
            copy,
            text="RuneScape Vision",
            text_color=GOLD,
            font=ctk.CTkFont(family="Georgia", size=19, weight="bold"),
        ).pack(anchor="w")
        _label(copy, "Live kalibratie workspace", muted=True, size=11).pack(anchor="w")

        names = ("01  KLEUR", "02  TEMPLATE", "03  SENSOR")
        self.navigation_value = tk.StringVar(value=names[0])
        navigation = ctk.CTkSegmentedButton(
            header,
            values=list(names),
            variable=self.navigation_value,
            command=self._show_page,
            height=36,
            corner_radius=9,
            fg_color=CARD_ALT,
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
            unselected_color=CARD_ALT,
            unselected_hover_color=CONTROL_HOVER,
            text_color=TEXT,
        )
        navigation.grid(row=0, column=1)
        _label(header, "F2 CAPTURE   •   ● LIVE ENGINE", size=11, bold=True, text_color=ACCENT_HOVER).grid(
            row=0,
            column=2,
            sticky="e",
            padx=18,
        )

        page_host = ctk.CTkFrame(self, fg_color="transparent")
        page_host.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        page_host.grid_columnconfigure(0, weight=1)
        page_host.grid_rowconfigure(0, weight=1)
        for name, page_class in (
            ("01  KLEUR", ColourPage),
            ("02  TEMPLATE", TemplatePage),
            ("03  SENSOR", SensorPage),
        ):
            page = page_class(page_host)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = page
        self.after(150, lambda: self._show_page(self.navigation_value.get()))
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._start_hotkeys()
        self.after(50, self._poll_hotkeys)

    def _show_page(self, name: str) -> None:
        page = self.pages.get(name)
        if page is None:
            return
        if self.current_page is not None and self.current_page is not page:
            self.current_page.deactivate()
        page.tkraise()
        self.current_page = page
        page.activate()

    def _start_hotkeys(self) -> None:
        options = {"on_press": self._global_key_pressed}
        if sys.platform == "win32":
            options["win32_event_filter"] = self._windows_key_filter
        self._hotkey_listener = KeyboardListener(**options)
        self._hotkey_listener.start()

    def _global_key_pressed(self, key) -> None:
        if key != KeyboardKey.f2:
            return
        self._queue_capture_hotkey()

    def _queue_capture_hotkey(self) -> None:
        now = time.monotonic()
        if now - self._last_f2_at < 0.4:
            return
        self._last_f2_at = now
        self._hotkey_events.put("capture")

    def _windows_key_filter(self, message, data):
        if int(data.vkCode) != 0x71:  # Windows virtual-key code for F2
            return True
        if int(message) in (0x0100, 0x0104):  # KEYDOWN and SYSKEYDOWN
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
        if self._hotkey_listener is not None:
            self._hotkey_listener.stop()
        self.destroy()


def main() -> None:
    VisionTester().mainloop()
