from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from tkinter import ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

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


class ZoomImageView(tk.Canvas):
    """Canvas image view with deep zoom, panning and exact source-pixel mapping."""

    def __init__(
        self,
        parent,
        *,
        auto_resize: bool = True,
        zoom_percent: int = 100,
        maximum_upscale: float = 6.0,
    ):
        super().__init__(
            parent,
            background=modern_ui.VIEW_BG,
            borderwidth=0,
            highlightthickness=0,
        )
        self.auto_resize = auto_resize
        self.zoom_percent = int(zoom_percent)
        self.maximum_upscale = maximum_upscale
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
            display_width = max(1, int(width * self.scale))
            display_height = max(1, int(height * self.scale))
            self.display_size = (display_width, display_height)
            self.image_offset = (
                (target_width - display_width) // 2,
                (target_height - display_height) // 2,
            )
            self.source_origin = (0.0, 0.0)
            rendered = cv2.resize(
                rgb,
                self.display_size,
                interpolation=(
                    cv2.INTER_AREA if self.scale < 1.0 else cv2.INTER_NEAREST
                ),
            )
        else:
            self.scale = self.zoom_percent / 100.0
            if self._centre is None:
                self._centre = (width / 2.0, height / 2.0)

            source_width = min(float(width), target_width / self.scale)
            source_height = min(float(height), target_height / self.scale)
            centre_x, centre_y = self._centre
            left = centre_x - source_width / 2.0
            top = centre_y - source_height / 2.0
            left = min(max(0.0, left), max(0.0, width - source_width))
            top = min(max(0.0, top), max(0.0, height - source_height))
            self._centre = (
                left + source_width / 2.0,
                top + source_height / 2.0,
            )

            x0 = max(0, int(np.floor(left)))
            y0 = max(0, int(np.floor(top)))
            x1 = min(width, max(x0 + 1, int(np.ceil(left + source_width))))
            y1 = min(height, max(y0 + 1, int(np.ceil(top + source_height))))
            crop = rgb[y0:y1, x0:x1]
            self.source_origin = (float(x0), float(y0))

            display_width = max(1, int(crop.shape[1] * self.scale))
            display_height = max(1, int(crop.shape[0] * self.scale))
            self.display_size = (display_width, display_height)
            self.image_offset = (
                (target_width - display_width) // 2,
                (target_height - display_height) // 2,
            )
            rendered = cv2.resize(
                crop,
                self.display_size,
                interpolation=(
                    cv2.INTER_AREA if self.scale < 1.0 else cv2.INTER_NEAREST
                ),
            )

        self.delete("all")
        self._photo = ImageTk.PhotoImage(Image.fromarray(rendered))
        offset_x, offset_y = self.image_offset
        self.create_image(offset_x, offset_y, image=self._photo, anchor="nw")
        self._draw_marker()

    def _draw_marker(self) -> None:
        self.delete("pipette_marker")
        if self._marker is None or self._last_rgb is None:
            return

        x, y, sample_size = self._marker
        radius = sample_size // 2
        source_left = x - radius
        source_top = y - radius
        source_right = x + radius + 1
        source_bottom = y + radius + 1
        origin_x, origin_y = self.source_origin

        left = self.image_offset[0] + (source_left - origin_x) * self.scale
        top = self.image_offset[1] + (source_top - origin_y) * self.scale
        right = self.image_offset[0] + (source_right - origin_x) * self.scale
        bottom = self.image_offset[1] + (source_bottom - origin_y) * self.scale

        image_left = self.image_offset[0]
        image_top = self.image_offset[1]
        image_right = image_left + self.display_size[0]
        image_bottom = image_top + self.display_size[1]
        if right <= image_left or bottom <= image_top or left >= image_right or top >= image_bottom:
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
        offset_x, offset_y = self.image_offset
        display_width, display_height = self.display_size
        relative_x = x - offset_x
        relative_y = y - offset_y
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
        if self.auto_resize:
            return
        self._pan_anchor = (event.x, event.y)

    def _pan_move(self, event) -> None:
        if self.auto_resize or self._pan_anchor is None or self._centre is None:
            return
        old_x, old_y = self._pan_anchor
        delta_x = event.x - old_x
        delta_y = event.y - old_y
        centre_x, centre_y = self._centre
        self._centre = (
            centre_x - delta_x / self.scale,
            centre_y - delta_y / self.scale,
        )
        self._pan_anchor = (event.x, event.y)
        self._draw()


class SearchableSourceControls(ttk.Frame):
    """Compact Colour source controls with live partial area filtering."""

    def __init__(self, parent, *, default_area: str = modern_ui.DEFAULT_AREA):
        super().__init__(parent)
        self._areas = sorted(load_areas())
        selected = default_area if default_area in self._areas else (
            self._areas[0] if self._areas else "game"
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
        terms = [part for part in self.area_search.get().lower().split() if part]
        matches = [
            area for area in self._areas
            if all(term in area.lower() for term in terms)
        ]
        self.area_box.configure(values=matches)
        if len(matches) == 1:
            self.area.set(matches[0])

    def bot(self) -> int:
        return int(self.bot_id.get())


class ScreenAreaOverlay:
    """Click-through red/green area guide drawn at the real desktop coordinates."""

    def __init__(self, master: tk.Misc) -> None:
        self.master = master
        self.window = tk.Toplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.configure(bg=TRANSPARENT_KEY)
        self.window.attributes("-topmost", True)
        self.window.attributes("-transparentcolor", TRANSPARENT_KEY)
        self.canvas = tk.Canvas(
            self.window,
            bg=TRANSPARENT_KEY,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self._capture_excluded = False
        self._make_click_through_and_exclude_capture()

    def _window_handle(self) -> int:
        user32 = ctypes.windll.user32
        handle = int(self.window.winfo_id())
        parent = int(user32.GetParent(handle))
        return parent or handle

    def _make_click_through_and_exclude_capture(self) -> None:
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
            self._capture_excluded = bool(user32.SetWindowDisplayAffinity(handle, 0x00000011))
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

    def close(self) -> None:
        try:
            self.window.destroy()
        except tk.TclError:
            pass


def _raw_preview(self, blob, safe_bounds=None) -> np.ndarray:
    """Keep Unified preview completely clean; guides live on the real desktop."""
    return self.capture.copy()


def _selected_sample_size(self) -> int:
    try:
        value = int(self.pipette_sample_size.get())
    except (AttributeError, TypeError, ValueError):
        value = 1
    return value if value in SAMPLE_SIZES else 1


def _pixel_pick(self, event) -> None:
    if self.capture is None or not self.pipette:
        return
    point = self.capture_view.image_coordinates(event.x, event.y)
    if point is None:
        return

    x, y = point
    height, width = self.capture.shape[:2]
    padding = PIPETTE_EDGE_PADDING
    if x < padding or y < padding or x >= width - padding or y >= height - padding:
        self.status.set(
            f"Pipet: kies binnen de groene schermrand ({padding}px padding)."
        )
        return

    sample_size = _selected_sample_size(self)
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
    self.status.set(f"Pipet: bronpixel ({x}, {y}), sample {sample_size}×{sample_size}.")
    self._render()
    self.capture_view.set_marker(x, y, sample_size)


_original_capture = modern_ui.ColourPage._capture
_original_activate = modern_ui.ColourPage.activate
_original_deactivate = modern_ui.ColourPage.deactivate
_original_colour_build = preset_ui.PresetColourPage._build


def _capture_with_desktop_overlay(self) -> None:
    overlay = getattr(self, "_screen_area_overlay", None)
    if overlay is not None and not overlay.capture_excluded:
        overlay.hide()
        self.update_idletasks()

    _original_capture(self)

    if self.capture is None:
        return
    if overlay is None:
        try:
            overlay = ScreenAreaOverlay(self.winfo_toplevel())
            self._screen_area_overlay = overlay
        except Exception:
            overlay = None
    if overlay is not None:
        overlay.show_region(self.capture_region)


def _activate_with_overlay(self) -> None:
    _original_activate(self)


def _deactivate_with_overlay(self) -> None:
    _original_deactivate(self)
    overlay = getattr(self, "_screen_area_overlay", None)
    if overlay is not None:
        overlay.hide()


def _build_with_deep_zoom(self) -> None:
    self.pipette_sample_size = tk.IntVar(value=1)
    _original_colour_build(self)

    self.zoom_slider.configure(
        from_=MIN_ZOOM_PERCENT,
        to=MAX_ZOOM_PERCENT,
    )
    self.zoom_label.configure(text=f"Zoom {self.zoom.get()}%")

    controls = self.pipette_button.master
    for child in controls.grid_slaves():
        info = child.grid_info()
        column = int(info.get("column", 0))
        if column >= 5:
            child.grid_configure(column=column + 2)

    ttk.Label(controls, text="Pipet px").grid(row=0, column=5, padx=(8, 3))
    sample_box = ttk.Combobox(
        controls,
        values=SAMPLE_SIZES,
        textvariable=self.pipette_sample_size,
        state="readonly",
        width=3,
    )
    sample_box.grid(row=0, column=6, padx=(0, 5))


modern_ui.ImageView = ZoomImageView
modern_ui.ColourPage._draw_blob_overlay = _raw_preview
modern_ui.ColourPage._pick = _pixel_pick
modern_ui.ColourPage._capture = _capture_with_desktop_overlay
modern_ui.ColourPage.activate = _activate_with_overlay
modern_ui.ColourPage.deactivate = _deactivate_with_overlay
preset_ui.BasicSourceControls = SearchableSourceControls
preset_ui.PresetColourPage._build = _build_with_deep_zoom

VisionTester = preset_ui.VisionTester


def main() -> None:
    VisionTester().mainloop()


__all__ = ["VisionTester", "main"]
