from __future__ import annotations

import tkinter as tk

from core.vision.areas import get_region

from .prayer_stoplight_monitor import PrayerStoplightMonitorPage
from .preview_contract import PreviewMode, PreviewSnapshot
from .sensor_boolean_badge import EnhancedSensorPage
from .template_plus import SearchableTemplatePage


COLOUR_MODES = (
    PreviewMode(
        "mask",
        "Mask",
        "Aanbevolen voor Colour: alleen pixels die binnen het gekozen kleurprofiel vallen.",
    ),
    PreviewMode(
        "isolated",
        "Geïsoleerd",
        "Toont alleen de echte RGB-pixels die door het kleurmasker heen komen.",
    ),
    PreviewMode(
        "live",
        "Live + blob",
        "Normaal area-beeld met de huidige blob/target-markering.",
    ),
)

TEMPLATE_MODES = (
    PreviewMode(
        "matches",
        "Matches",
        "Aanbevolen voor Template: live beeld met template-hits en geldigheidsmarkeringen.",
    ),
)

SENSOR_MODES = (
    PreviewMode(
        "result",
        "Sensor resultaat",
        "Toont alleen de visualisatie die logisch hoort bij de geselecteerde sensor.",
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
        return PreviewSnapshot(frame=frame, region=region)

    def set_desktop_preview_compact(self, enabled: bool) -> None:
        # All three colour preview cards share one explicit preview container.
        parent = getattr(self.capture_view, "master", None)
        container = getattr(parent, "master", None)
        _set_grid_visible(container, not enabled)


class PreviewTemplatePage(SearchableTemplatePage):
    """Template page exposes one unambiguous matches preview."""

    def desktop_preview_modes(self) -> tuple[PreviewMode, ...]:
        return TEMPLATE_MODES

    def desktop_preview_default_mode(self) -> str:
        return "matches"

    def desktop_preview_snapshot(self, mode_key: str) -> PreviewSnapshot | None:
        if mode_key != "matches":
            return None

        frame = _view_frame(self.preview)
        if frame is None:
            frame = self.screenshot

        region = _valid_region(self.region)
        if region is None:
            try:
                region = get_region(self.source.area.get(), bot_id=self.source.bot())
            except Exception:
                return None

        if frame is None:
            return None
        return PreviewSnapshot(frame=frame, region=region)

    def set_desktop_preview_compact(self, enabled: bool) -> None:
        # The center card is the template live/match preview column.
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

        # Python booleans do not have a meaningful pixel mask. Other sensor
        # kinds do, so the processed/detected view is the useful default.
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
        return PreviewSnapshot(frame=frame, region=region)

    def set_desktop_preview_compact(self, enabled: bool) -> None:
        # Sensor keeps controls/results visible and only hides image cards.
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
