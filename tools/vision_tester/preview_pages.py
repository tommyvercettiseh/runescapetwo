from __future__ import annotations

import math
from pathlib import Path
import tkinter as tk

import customtkinter as ctk

from core.vision.areas import get_region
from core.vision.templates import load_template

from . import modern_ui
from .prayer_stoplight_monitor import PrayerStoplightMonitorPage
from .preview_contract import PreviewBox, PreviewMode, PreviewSnapshot
from .sensor_boolean_badge import EnhancedSensorPage
from .template_plus import SearchableTemplatePage


COLOUR_MODES = (
    PreviewMode(
        "mask",
        "Mask",
        "AANBEVOLEN · Colour: wit = pixels die binnen je gekozen kleurprofiel vallen.",
    ),
    PreviewMode(
        "isolated",
        "Geïsoleerd",
        "Colour debug: alleen de echte RGB-pixels die door het masker heen komen.",
    ),
    PreviewMode(
        "live",
        "Live + blob",
        "Colour debug: normaal area-beeld met de huidige blob/target-markering.",
    ),
)

TEMPLATE_MODES = (
    PreviewMode(
        "matches",
        "Matches",
        "AANBEVOLEN · Template: paars = gekozen area · felgroen = geldige match.",
    ),
)

SENSOR_MODES = (
    PreviewMode(
        "result",
        "Sensor resultaat",
        "AANBEVOLEN · Sensor kiest automatisch de juiste live- of detectieweergave.",
    ),
)

TEMPLATE_AREA_COLOUR = "#e056fd"
TEMPLATE_MATCH_COLOUR = "#39ff14"
TEMPLATE_SAFE_COLOUR = "#d1a64b"
TEMPLATE_OVERLAY_MARGIN = 8


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


def _view_frame(view):
    if view is None:
        return None
    return getattr(view, "_last_rgb", None)


def _set_grid_visible(widget: tk.Misc | None, visible: bool) -> None:
    if widget is None:
        return
    try:
        if visible:
            widget.grid()
        elif widget.grid_info():
            widget.grid_remove()
    except tk.TclError:
        pass


class PreviewColourPage(PrayerStoplightMonitorPage):
    """Colour page with colour-specific desktop preview modes."""

    def desktop_preview_modes(self) -> tuple[PreviewMode, ...]:
        return COLOUR_MODES

    def desktop_preview_default_mode(self) -> str:
        return "mask"

    def desktop_preview_snapshot(self, mode_key: str) -> PreviewSnapshot | None:
        if mode_key == "mask":
            frame = _view_frame(self.mask_view)
        elif mode_key == "isolated":
            frame = _view_frame(self.isolated_view)
        elif mode_key == "live":
            frame = _view_frame(self.capture_view)
        else:
            return None

        region = _valid_region(self.capture_region)
        if region is None:
            try:
                area_name = self.source.area.get().strip()
                if not area_name:
                    return None
                region = get_region(area_name, bot_id=self.source.bot())
            except Exception:
                return None

        if frame is None:
            return None
        return PreviewSnapshot(region=region, frame=frame)

    def set_desktop_preview_compact(self, enabled: bool) -> None:
        parent = getattr(self.capture_view, "master", None)
        container = getattr(parent, "master", None)
        _set_grid_visible(container, not enabled)


class PreviewTemplatePage(SearchableTemplatePage):
    """Template page draws clear target annotations over the real game window."""

    def __init__(self, parent) -> None:
        self.show_safe_zone = tk.BooleanVar(master=parent, value=False)
        self.match_line_width = tk.IntVar(master=parent, value=3)
        self.match_line_width_text = tk.StringVar(master=parent, value="3 px")
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()
        self._add_overlay_controls()

    def _add_overlay_controls(self) -> None:
        """Keep template-only overlay settings on the Template page itself."""
        toolbar = self.source.master
        controls = ctk.CTkFrame(toolbar, fg_color="transparent")
        controls.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 10))
        controls.grid_columnconfigure(3, weight=1)

        modern_ui._label(controls, "OVERLAY", muted=True, size=10).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 10),
        )
        ctk.CTkSwitch(
            controls,
            text="Toon safe zone",
            variable=self.show_safe_zone,
            progress_color=modern_ui.ACCENT,
            button_color=modern_ui.TEXT,
            button_hover_color=modern_ui.GOLD,
            text_color=modern_ui.MUTED,
        ).grid(row=0, column=1, sticky="w", padx=(0, 18))

        modern_ui._label(controls, "MATCH LIJN", muted=True, size=10).grid(
            row=0,
            column=2,
            sticky="w",
            padx=(0, 7),
        )
        slider = ctk.CTkSlider(
            controls,
            from_=1,
            to=6,
            number_of_steps=5,
            variable=self.match_line_width,
            command=self._match_line_width_changed,
            width=150,
            progress_color=modern_ui.ACCENT,
            button_color=modern_ui.ACCENT,
            button_hover_color=modern_ui.ACCENT_HOVER,
            fg_color=modern_ui.BORDER,
        )
        slider.grid(row=0, column=3, sticky="w", padx=(0, 8))
        modern_ui._label(
            controls,
            "",
            textvariable=self.match_line_width_text,
            size=10,
            bold=True,
        ).grid(row=0, column=4, sticky="w")

    def _match_line_width_changed(self, value) -> None:
        width = min(6, max(1, int(round(float(value)))))
        self.match_line_width.set(width)
        self.match_line_width_text.set(f"{width} px")

    def desktop_preview_modes(self) -> tuple[PreviewMode, ...]:
        return TEMPLATE_MODES

    def desktop_preview_default_mode(self) -> str:
        return "matches"

    def desktop_preview_snapshot(self, mode_key: str) -> PreviewSnapshot | None:
        if mode_key != "matches" or not self.selected:
            return None

        area_region = _valid_region(self.region)
        if area_region is None:
            try:
                area_region = get_region(self.source.area.get(), bot_id=self.source.bot())
            except Exception:
                return None

        area_left, area_top, area_width, area_height = area_region
        margin = TEMPLATE_OVERLAY_MARGIN
        overlay_region = (
            area_left - margin,
            area_top - margin,
            area_width + margin * 2,
            area_height + margin * 2,
        )

        # The purple guide is the exact selected area boundary: zero area padding.
        boxes: list[PreviewBox] = [
            PreviewBox(
                (margin, margin, margin + area_width, margin + area_height),
                TEMPLATE_AREA_COLOUR,
                width=2,
                label=self.source.area.get(),
            )
        ]

        safe = self.best_valid_bounds
        if safe is None:
            return PreviewSnapshot(region=overlay_region, boxes=tuple(boxes))

        try:
            _template_rgb, template_gray = load_template(self.selected)
            _template_height, template_width = template_gray.shape[:2]
            padding_percent = self._x_padding_percent()
        except Exception:
            return PreviewSnapshot(region=overlay_region, boxes=tuple(boxes))

        safe_left, safe_top, safe_right, safe_bottom = map(int, safe)
        x_margin = max(1, int(round(template_width * padding_percent / 100.0)))

        # Reconstruct the true template bounds from the safe click zone. The
        # green stroke is then pushed OUTSIDE those bounds so it never covers
        # pixels that belong to the matched image itself.
        target_left = safe_left - x_margin
        target_right = safe_right + x_margin
        target_top = safe_top
        target_bottom = safe_bottom

        line_width = min(6, max(1, int(self.match_line_width.get())))
        outside_offset = math.ceil(line_width / 2) + 1

        green_local = (
            target_left - outside_offset - overlay_region[0],
            target_top - outside_offset - overlay_region[1],
            target_right + outside_offset - overlay_region[0],
            target_bottom + outside_offset - overlay_region[1],
        )
        boxes.append(
            PreviewBox(
                green_local,
                TEMPLATE_MATCH_COLOUR,
                width=line_width,
                label=Path(self.selected).stem,
            )
        )

        if self.show_safe_zone.get():
            safe_local = (
                safe_left - overlay_region[0],
                safe_top - overlay_region[1],
                safe_right - overlay_region[0],
                safe_bottom - overlay_region[1],
            )
            boxes.append(
                PreviewBox(
                    safe_local,
                    TEMPLATE_SAFE_COLOUR,
                    width=1,
                    label="safe",
                )
            )

        return PreviewSnapshot(region=overlay_region, boxes=tuple(boxes))

    def set_desktop_preview_compact(self, enabled: bool) -> None:
        _set_grid_visible(getattr(self.preview, "master", None), not enabled)


class PreviewSensorPage(EnhancedSensorPage):
    """Sensor page chooses the correct visual automatically for each sensor kind."""

    def desktop_preview_modes(self) -> tuple[PreviewMode, ...]:
        return SENSOR_MODES

    def desktop_preview_default_mode(self) -> str:
        return "result"

    def desktop_preview_snapshot(self, mode_key: str) -> PreviewSnapshot | None:
        if mode_key != "result":
            return None

        check = self.checks.get(self.sensor_name.get())
        if check is None:
            return None

        if check.kind == "python_bool":
            frame = _view_frame(self.live_view)
        else:
            frame = _view_frame(self.detected_view)

        try:
            region = get_region(check.area, bot_id=int(self.bot_id.get()))
        except Exception:
            return None

        if frame is None:
            return None
        return PreviewSnapshot(region=region, frame=frame)

    def set_desktop_preview_compact(self, enabled: bool) -> None:
        parents: list[tk.Misc] = []
        for view in (self.live_view, self.detected_view):
            parent = getattr(view, "master", None)
            if parent is not None and parent not in parents:
                parents.append(parent)
        for parent in parents:
            _set_grid_visible(parent, not enabled)


__all__ = [
    "PreviewColourPage",
    "PreviewSensorPage",
    "PreviewTemplatePage",
]
