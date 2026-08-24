from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
import cv2
import numpy as np
from PIL import Image, ImageTk

from core.vision.areas import load_areas


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
FONT_FAMILY = "Segoe UI"


def set_palette(
    *,
    background: str,
    card: str,
    card_alt: str,
    border: str,
    control_hover: str,
    text: str,
    muted: str,
    accent: str,
    accent_hover: str,
    accent_soft: str,
    gold: str,
    danger: str,
    success: str,
    view_background: str,
) -> None:
    """Update the shared tester palette without replacing widget factories."""
    global BG, CARD, CARD_ALT, BORDER, CONTROL_HOVER
    global TEXT, MUTED, ACCENT, ACCENT_HOVER, ACCENT_SOFT
    global GOLD, DANGER, SUCCESS, VIEW_BG

    BG = background
    CARD = card
    CARD_ALT = card_alt
    BORDER = border
    CONTROL_HOVER = control_hover
    TEXT = text
    MUTED = muted
    ACCENT = accent
    ACCENT_HOVER = accent_hover
    ACCENT_SOFT = accent_soft
    GOLD = gold
    DANGER = danger
    SUCCESS = success
    VIEW_BG = view_background


def font(size: int = 12, *, bold: bool = False) -> ctk.CTkFont:
    """Return the one typography style used throughout the tester."""
    return ctk.CTkFont(
        family=FONT_FAMILY,
        size=size,
        weight="bold" if bold else "normal",
    )


def format_pixels(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def label(
    parent,
    text: str,
    *,
    muted: bool = False,
    size: int = 12,
    bold: bool = False,
    **kwargs,
):
    text_color = kwargs.pop("text_color", MUTED if muted else TEXT)
    return ctk.CTkLabel(
        parent,
        text=text,
        text_color=text_color,
        font=font(size, bold=bold),
        **kwargs,
    )


def button(
    parent,
    text: str,
    command,
    *,
    primary: bool = False,
    danger: bool = False,
    width: int = 120,
):
    if primary:
        foreground, hover, colour = ACCENT, ACCENT_HOVER, "#111509"
    elif danger:
        foreground, hover, colour = "#321a17", "#45221d", "#ef8a78"
    else:
        foreground, hover, colour = CARD_ALT, CONTROL_HOVER, TEXT
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=38,
        corner_radius=7,
        fg_color=foreground,
        hover_color=hover,
        text_color=colour,
        font=font(12, bold=True),
        border_width=1,
        border_color=BORDER,
    )


def card(parent, **kwargs):
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
    ) -> None:
        super().__init__(
            parent,
            background=VIEW_BG,
            borderwidth=0,
            anchor="center",
        )
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
        self.scale = (
            min(self.maximum_upscale, fit)
            if self.auto_resize
            else min(self.zoom_percent / 100.0, fit)
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
    def __init__(self, parent, *, default_area: str = DEFAULT_AREA) -> None:
        super().__init__(parent, fg_color="transparent")
        areas = sorted(load_areas())
        self.bot_id = tk.StringVar(value="1")
        self.area = tk.StringVar(
            value=(
                default_area
                if default_area in areas
                else areas[0]
                if areas
                else "game"
            )
        )

        label(self, "Bot ID", muted=True, size=11).grid(
            row=0,
            column=0,
            sticky="w",
        )
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
            font=font(11),
            dropdown_font=font(11),
        ).grid(row=1, column=0, padx=(0, 12), pady=(4, 0), sticky="w")

        label(self, "Area", muted=True, size=11).grid(
            row=0,
            column=1,
            sticky="w",
        )
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
            font=font(11),
            dropdown_font=font(11),
        )
        self.area_box.grid(row=1, column=1, pady=(4, 0), sticky="ew")
        self.grid_columnconfigure(1, weight=1)

    def bot(self) -> int:
        return int(self.bot_id.get())


__all__ = [
    "ACCENT",
    "ACCENT_HOVER",
    "ACCENT_SOFT",
    "BG",
    "BORDER",
    "CARD",
    "CARD_ALT",
    "CONTROL_HOVER",
    "DANGER",
    "DEFAULT_AREA",
    "FONT_FAMILY",
    "GOLD",
    "ImageView",
    "MUTED",
    "SUCCESS",
    "SourceControls",
    "TEXT",
    "VIEW_BG",
    "button",
    "card",
    "font",
    "format_pixels",
    "label",
    "set_palette",
]
