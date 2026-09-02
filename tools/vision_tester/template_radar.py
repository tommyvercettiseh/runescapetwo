from __future__ import annotations

import time

import customtkinter as ctk
from PIL import Image, ImageDraw

from core.vision.models import TemplateSettings
from core.vision.screenshots import capture_area
from core.vision.template_analysis import analyse_template
from core.vision.templates import load_settings, load_template

from . import modern_ui
from .template_plus import SearchableTemplatePage


RADAR_STEP_MS = 140
RADAR_MAX_CANDIDATES = 6
DOT_SIZE = 14


class RadarTemplatePage(SearchableTemplatePage):
    """Searchable template page with lightweight live found/not-found indicators."""

    def __init__(self, parent) -> None:
        self._radar_status: dict[str, bool] = {}
        self._radar_index = 0
        self._radar_next_at = 0.0
        self._radar_screenshots: dict[tuple[str, int], object] = {}
        self._radar_icons = {
            False: self._make_dot("#FFFFFF"),
            True: self._make_dot("#22C55E"),
        }
        super().__init__(parent)

    @staticmethod
    def _make_dot(fill: str) -> ctk.CTkImage:
        scale = 3
        size = DOT_SIZE * scale
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((1, 1, size - 2, size - 2), fill="#111111")
        inset = 3 * scale
        draw.ellipse((inset, inset, size - inset - 1, size - inset - 1), fill=fill)
        return ctk.CTkImage(light_image=image, dark_image=image, size=(DOT_SIZE, DOT_SIZE))

    def _refresh_templates(self, preferred: str | None = None) -> None:
        previous = dict(self._radar_status)
        super()._refresh_templates(preferred)
        self._radar_status = {name: previous.get(name, False) for name in self.templates}
        self._radar_index = 0
        self._radar_screenshots.clear()
        self._draw_templates()

    def _draw_templates(self) -> None:
        for child in self.template_scroll.winfo_children():
            child.destroy()

        query = self.query.get().strip().casefold()
        names = [name for name in self.templates if query in name.casefold()]
        self.rows.clear()

        for row, name in enumerate(names):
            selected = name == self.selected
            found = self._radar_status.get(name, False)
            button = ctk.CTkButton(
                self.template_scroll,
                text=name,
                image=self._radar_icons[found],
                compound="left",
                command=lambda value=name: self._select(value),
                anchor="w",
                height=34,
                corner_radius=7,
                fg_color=modern_ui.ACCENT_SOFT if selected else "transparent",
                hover_color=modern_ui.ACCENT_SOFT,
                text_color=modern_ui.ACCENT_HOVER if selected else modern_ui.TEXT,
            )
            button.grid(row=row, column=0, sticky="ew", pady=1)
            self.rows[name] = button

    def _set_radar_status(self, name: str, found: bool) -> None:
        found = bool(found)
        if self._radar_status.get(name) == found:
            return
        self._radar_status[name] = found
        button = self.rows.get(name)
        if button is not None:
            button.configure(image=self._radar_icons[found])

    def _tick(self) -> None:
        if self.live.get():
            self._capture()

        now = time.monotonic()
        if now >= self._radar_next_at:
            self._radar_step()
            self._radar_next_at = now + (RADAR_STEP_MS / 1000.0)

        self.after(100, self._tick)

    def _radar_step(self) -> None:
        if not self.templates:
            return

        if self._radar_index >= len(self.templates):
            self._radar_index = 0
            self._radar_screenshots.clear()

        name = self.templates[self._radar_index]
        self._radar_index += 1

        try:
            settings = load_settings(name)
            area = settings.area or self.source.area.get()
            bot_id = self.source.bot()
            cache_key = (area, bot_id)
            screenshot = self._radar_screenshots.get(cache_key)
            if screenshot is None:
                screenshot, _region = capture_area(area, bot_id=bot_id)
                self._radar_screenshots[cache_key] = screenshot
            found = self._matches(name, screenshot, settings)
        except Exception:
            found = False

        self._set_radar_status(name, found)

    @staticmethod
    def _matches(name: str, screenshot, settings: TemplateSettings) -> bool:
        template_rgb, template_gray = load_template(name)
        analysis = analyse_template(
            screenshot,
            template_rgb,
            template_gray,
            method=settings.method,
            minimum_shape=settings.min_shape,
            maximum_candidates=RADAR_MAX_CANDIDATES,
        )
        return any(candidate.passes_colour(settings.min_color) for candidate in analysis.candidates)


__all__ = ["RadarTemplatePage"]
