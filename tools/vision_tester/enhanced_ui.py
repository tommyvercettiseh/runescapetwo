from __future__ import annotations

import tkinter as tk

import cv2
import numpy as np
from PIL import Image, ImageTk

from . import modern_ui, preset_ui


MIN_ZOOM_PERCENT = 25
MAX_ZOOM_PERCENT = 1600
PIPETTE_EDGE_PADDING = 6
AREA_BORDER_COLOUR = (220, 55, 55)
SAFE_BORDER_COLOUR = (50, 210, 90)
PIPETTE_MARKER_COLOUR = (255, 255, 255)


class ZoomImageView(tk.Canvas):
    """Canvas image view with deep zoom, panning and source-pixel mapping."""

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


def _draw_clean_overlay(
    self,
    blob,
    safe_bounds: tuple[int, int, int, int] | None = None,
) -> np.ndarray:
    """Draw guides only; never draw text into the pipette image."""
    visual = self.capture.copy()
    height, width = visual.shape[:2]
    if width <= 0 or height <= 0:
        return visual

    # The red line is the exact captured area boundary. The green line is the
    # safe interior where the pipette may sample without touching the edge.
    cv2.rectangle(
        visual,
        (0, 0),
        (width - 1, height - 1),
        AREA_BORDER_COLOUR,
        1,
    )
    if width > PIPETTE_EDGE_PADDING * 2 and height > PIPETTE_EDGE_PADDING * 2:
        cv2.rectangle(
            visual,
            (PIPETTE_EDGE_PADDING, PIPETTE_EDGE_PADDING),
            (
                width - 1 - PIPETTE_EDGE_PADDING,
                height - 1 - PIPETTE_EDGE_PADDING,
            ),
            SAFE_BORDER_COLOUR,
            1,
        )

    if blob is not None:
        pad = modern_ui.BLOB_BOX_PADDING
        left = max(0, blob.x - pad)
        top = max(0, blob.y - pad)
        right = min(width - 1, blob.x + blob.width - 1 + pad)
        bottom = min(height - 1, blob.y + blob.height - 1 + pad)
        cv2.rectangle(
            visual,
            (left, top),
            (right, bottom),
            AREA_BORDER_COLOUR,
            2,
        )

        if safe_bounds is not None:
            safe_left, safe_top, safe_right, safe_bottom = safe_bounds
            cv2.rectangle(
                visual,
                (max(0, safe_left), max(0, safe_top)),
                (
                    min(width - 1, safe_right - 1),
                    min(height - 1, safe_bottom - 1),
                ),
                SAFE_BORDER_COLOUR,
                2,
            )

    picked = getattr(self, "_last_pipette_point", None)
    if picked is not None:
        x, y = picked
        radius = 3
        cv2.rectangle(
            visual,
            (max(0, x - radius), max(0, y - radius)),
            (min(width - 1, x + radius), min(height - 1, y + radius)),
            PIPETTE_MARKER_COLOUR,
            1,
        )

    return visual


_original_pick = modern_ui.ColourPage._pick


def _safe_pick(self, event) -> None:
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
            f"Pipet: kies binnen het groene kader ({padding}px veilige rand)."
        )
        return

    # Store only the source-pixel location. Sampling itself remains delegated
    # to the original implementation, which reads self.capture (raw pixels),
    # never the displayed overlay.
    self._last_pipette_point = (x, y)
    _original_pick(self, event)


_original_colour_build = preset_ui.PresetColourPage._build


def _build_with_deep_zoom(self) -> None:
    _original_colour_build(self)
    self.zoom_slider.configure(
        from_=MIN_ZOOM_PERCENT,
        to=MAX_ZOOM_PERCENT,
    )
    self.zoom_label.configure(text=f"Zoom {self.zoom.get()}%")


# Install the visual behaviour before the tester creates its pages.
modern_ui.ImageView = ZoomImageView
modern_ui.ColourPage._draw_blob_overlay = _draw_clean_overlay
modern_ui.ColourPage._pick = _safe_pick
preset_ui.PresetColourPage._build = _build_with_deep_zoom

VisionTester = preset_ui.VisionTester


def main() -> None:
    VisionTester().mainloop()


__all__ = ["VisionTester", "main"]
