from __future__ import annotations

from pathlib import Path
import tkinter as tk

from core.vision.areas import get_region
from core.vision.templates import load_template

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
        "AANBEVOLEN · Template: groen en goud worden fysiek over het echte gamevenster getekend.",
    ),
)

SENSOR_MODES = (
    PreviewMode(
        "result",
        "Sensor resultaat",
        "AANBEVOLEN · Sensor kiest automatisch de juiste live- of detectieweergave.",
    ),
)


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
    """Template page draws target annotations over the actual RuneLite pixels."""

    def desktop_preview_modes(self) -> tuple[PreviewMode, ...]:
        return TEMPLATE_MODES

    def desktop_preview_default_mode(self) -> str:
        return "matches"

    def desktop_preview_snapshot(self, mode_key: str) -> PreviewSnapshot | None:
        if mode_key != "matches" or not self.selected:
            return None

        region = _valid_region(self.region)
        if region is None:
            try:
                region = get_region(self.source.area.get(), bot_id=self.source.bot())
            except Exception:
                return None

        safe = self.best_valid_bounds
        if safe is None:
            return PreviewSnapshot(region=region)

        try:
            _template_rgb, template_gray = load_template(self.selected)
            template_height, template_width = template_gray.shape[:2]
            padding_percent = self._x_padding_percent()
        except Exception:
            return None

        region_left, region_top, _region_width, _region_height = region
        safe_left, safe_top, safe_right, safe_bottom = map(int, safe)
        margin = max(1, int(round(template_width * padding_percent / 100.0)))

        target_left = safe_left - margin
        target_right = safe_right + margin
        target_top = safe_top
        target_bottom = safe_bottom

        green_local = (
            target_left - region_left,
            target_top - region_top,
            target_right - region_left,
            target_bottom - region_top,
        )
        gold_local = (
            safe_left - region_left,
            safe_top - region_top,
            safe_right - region_left,
            safe_bottom - region_top,
        )

        label = Path(self.selected).stem
        boxes = (
            PreviewBox(green_local, "#25a969", width=2, label=label),
            PreviewBox(gold_local, "#d1a64b", width=1, label="safe"),
        )
        return PreviewSnapshot(region=region, boxes=boxes)

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
