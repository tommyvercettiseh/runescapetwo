from __future__ import annotations

from collections.abc import Callable
import tkinter as tk

import customtkinter as ctk
import numpy as np

from core.vision.areas import load_areas

from . import modern_ui


ORIGINAL_VALID = np.array((37, 169, 105), dtype=np.uint8)
ORIGINAL_SAFE = np.array((209, 166, 75), dtype=np.uint8)
BRIGHT_VALID = np.array((0, 255, 70), dtype=np.uint8)


class CleanTemplatePreview(modern_ui.ImageView):
    """Template preview that normalizes overlay colours without patching show()."""

    def __init__(self, parent, screenshot: Callable[[], np.ndarray | None]) -> None:
        self._screenshot = screenshot
        super().__init__(parent)

    def show(self, visual: np.ndarray) -> None:
        cleaned = visual.copy()
        screenshot = self._screenshot()
        if screenshot is not None and screenshot.shape == cleaned.shape:
            safe_mask = np.all(cleaned == ORIGINAL_SAFE, axis=2)
            cleaned[safe_mask] = screenshot[safe_mask]
        valid_mask = np.all(cleaned == ORIGINAL_VALID, axis=2)
        cleaned[valid_mask] = BRIGHT_VALID
        super().show(cleaned)


class SearchableTemplatePage(modern_ui.TemplatePage):
    """Template tester with Template and Area browsers as primary navigation."""

    def __init__(self, parent) -> None:
        self.area_query = tk.StringVar(master=parent, value="")
        self.area_scroll: ctk.CTkScrollableFrame | None = None
        self.area_rows: dict[str, ctk.CTkButton] = {}
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()
        self._replace_preview()
        self._simplify_top_toolbar()
        self._add_area_browser()

    def _replace_preview(self) -> None:
        parent = self.preview.master
        self.preview.destroy()
        self.preview = CleanTemplatePreview(parent, lambda: self.screenshot)
        self.preview.grid(row=2, column=0, sticky="nsew", padx=12)

    def _simplify_top_toolbar(self) -> None:
        """The Area sidebar owns area selection; keep only useful actions above."""
        try:
            toolbar = self.source.master
            self.source.grid_remove()
            actions = next(
                (
                    child
                    for child in toolbar.grid_slaves(row=0)
                    if child is not self.source
                ),
                None,
            )
            if actions is not None:
                actions.grid_configure(column=0, sticky="e", padx=16, pady=10)
            toolbar.grid_columnconfigure(0, weight=1)
            toolbar.grid_columnconfigure(1, weight=0)
        except (AttributeError, tk.TclError):
            pass

    @staticmethod
    def _area_names() -> list[str]:
        return sorted(load_areas(), key=str.casefold)

    def _filtered_area_names(self) -> list[str]:
        terms = [
            term
            for term in self.area_query.get().strip().casefold().split()
            if term
        ]
        return [
            name
            for name in self._area_names()
            if all(term in name.casefold() for term in terms)
        ]

    def _add_area_browser(self) -> None:
        content_matches = self.grid_slaves(row=1, column=0)
        if not content_matches:
            return
        content = content_matches[0]

        center = None
        detection = None
        for child in content.grid_slaves(row=0):
            column = int(child.grid_info().get("column", -1))
            if column == 1:
                center = child
            elif column == 2:
                detection = child
        if center is None or detection is None:
            return

        center.grid_configure(column=2, padx=(0, 8))
        detection.grid_configure(column=3)
        content.grid_columnconfigure(0, weight=0)
        content.grid_columnconfigure(1, weight=0)
        content.grid_columnconfigure(2, weight=1)
        content.grid_columnconfigure(3, weight=0)

        sidebar = modern_ui._card(content, width=245)
        sidebar.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(2, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        modern_ui._label(sidebar, "AREAS", size=12, bold=True).grid(
            row=0,
            column=0,
            sticky="w",
            padx=14,
            pady=(14, 8),
        )
        area_search = ctk.CTkEntry(
            sidebar,
            textvariable=self.area_query,
            placeholder_text="Zoek area",
            height=38,
            corner_radius=8,
            fg_color=modern_ui.CARD_ALT,
            border_color=modern_ui.BORDER,
            text_color=modern_ui.TEXT,
        )
        area_search.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        area_search.bind("<KeyRelease>", self._filter_areas)
        area_search.bind("<Escape>", self._clear_area_search)

        self.area_scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            scrollbar_button_color=modern_ui.BORDER,
            scrollbar_button_hover_color=modern_ui.GOLD,
        )
        self.area_scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.area_scroll.grid_columnconfigure(0, weight=1)
        self._draw_areas()

    def _draw_areas(self) -> None:
        if self.area_scroll is None:
            return
        for child in self.area_scroll.winfo_children():
            child.destroy()

        current = self.source.area.get()
        self.area_rows.clear()
        for row, name in enumerate(self._filtered_area_names()):
            selected = name == current
            button = ctk.CTkButton(
                self.area_scroll,
                text=name,
                command=lambda value=name: self._select_area(value),
                anchor="w",
                height=34,
                corner_radius=7,
                fg_color=modern_ui.ACCENT_SOFT if selected else "transparent",
                hover_color=modern_ui.ACCENT_SOFT,
                text_color=modern_ui.ACCENT_HOVER if selected else modern_ui.TEXT,
            )
            button.grid(row=row, column=0, sticky="ew", pady=1)
            self.area_rows[name] = button

    def _select_area(self, name: str) -> None:
        if name == self.source.area.get():
            return
        self.source.area.set(name)
        self._draw_areas()
        self.status.set(f"Area geselecteerd: {name}. Opnieuw analyseren…")
        if self.selected:
            self.after_idle(self._capture)

    def _filter_areas(self, _event=None) -> None:
        matches = self._filtered_area_names()
        try:
            self.source.area_box.configure(values=matches or self._area_names())
        except (AttributeError, tk.TclError):
            pass
        self._draw_areas()
        current = self.source.area.get()
        if current and current in matches:
            return
        if len(matches) == 1:
            self._select_area(matches[0])

    def _clear_area_search(self, _event=None) -> None:
        self.area_query.set("")
        try:
            self.source.area_box.configure(values=self._area_names())
        except (AttributeError, tk.TclError):
            pass
        self._draw_areas()

    def _captured(self, name: str) -> None:
        super()._captured(name)
        self.live.set(True)
        self.status.set(f"Nieuwe template {name} opgeslagen · Live matching actief.")
        self.after_idle(self._capture)


def install_template_plus() -> None:
    """Compatibility no-op; use SearchableTemplatePage explicitly."""


__all__ = [
    "CleanTemplatePreview",
    "SearchableTemplatePage",
    "install_template_plus",
]
