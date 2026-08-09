from __future__ import annotations

import tkinter as tk

import cv2
import numpy as np
from PIL import Image, ImageTk

from . import modern_ui
from .enhanced_config import (
    MARKER_HEX,
    MAX_ZOOM_PERCENT,
    MIN_ZOOM_PERCENT,
)


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


__all__ = ["ZoomImageView"]
