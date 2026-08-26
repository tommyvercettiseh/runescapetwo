from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tkinter as tk

import customtkinter as ctk
import numpy as np

from core.vision.areas import load_areas
from core.vision.templates import load_template

from . import ui
from .template_page import TemplatePage


ORIGINAL_VALID = np.array((37, 169, 105), dtype=np.uint8)
ORIGINAL_SAFE = np.array((209, 166, 75), dtype=np.uint8)
BRIGHT_VALID = np.array((0, 255, 70), dtype=np.uint8)


class CleanTemplatePreview(ui.ImageView):
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


class TemplateThumbnail(ui.ImageView):
    """Small reusable surface for the exact template currently being searched."""

    def clear(self) -> None:
        if self._job is not None:
            self.after_cancel(self._job)
            self._job = None
        self._last_rgb = None
        self._photo = None
        self.configure(image="")


class SearchableTemplatePage(TemplatePage):
    """Template tester with Template and Area browsers as primary navigation."""

    def __init__(self, parent) -> None:
        self.area_query = tk.StringVar(master=parent, value="")
        self.area_scroll: ctk.CTkScrollableFrame | None = None
        self.area_rows: dict[str, ctk.CTkButton] = {}
        self.template_thumbnail: TemplateThumbnail | None = None
        self.template_thumbnail_name: ctk.CTkLabel | None = None
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()
        self._replace_preview()
        self._add_area_browser()
        self._add_template_actions()
        self._polish_detection_panel()
        self._collapse_top_toolbar()
        self._show_selected_template()

    def _content_frame(self):
        """Return the main three/four-column workspace before or after toolbar collapse."""
        for row in (1, 0):
            matches = self.grid_slaves(row=row, column=0)
            if matches:
                candidate = matches[0]
                if candidate is not getattr(self.source, "master", None):
                    return candidate
        return None

    @staticmethod
    def _column_child(parent, column: int):
        if parent is None:
            return None
        return next(
            (
                child
                for child in parent.grid_slaves(row=0)
                if int(child.grid_info().get("column", -1)) == column
            ),
            None,
        )

    def _replace_preview(self) -> None:
        parent = self.preview.master
        self.preview.destroy()
        self.preview = CleanTemplatePreview(parent, lambda: self.screenshot)
        self.preview.grid(row=2, column=0, sticky="nsew", padx=12)

    def _collapse_top_toolbar(self) -> None:
        """Keep source state alive but reclaim the full toolbar height for previews."""
        try:
            toolbar = self.source.master
            toolbar.grid_remove()
            content_matches = self.grid_slaves(row=1, column=0)
            if content_matches:
                content_matches[0].grid_configure(row=0, pady=(12, 10))
                self.grid_rowconfigure(0, weight=1)
                self.grid_rowconfigure(1, weight=0)
        except (AttributeError, tk.TclError):
            pass

    def _add_template_actions(self) -> None:
        """Give creation controls their own rows so they never overlap the list."""
        content = self._content_frame()
        sidebar = self._column_child(content, 0)
        if sidebar is None:
            return

        # CTkScrollableFrame wraps its visible widget in a parent frame, so call
        # grid() again instead of grid_configure() to move the complete control.
        self.template_scroll.grid(
            row=3,
            column=0,
            sticky="nsew",
            padx=8,
        )
        footer = next(
            (
                child
                for child in sidebar.grid_slaves()
                if child is not self.template_scroll
                and int(child.grid_info().get("row", -1)) == 3
            ),
            None,
        )
        if footer is not None:
            footer.grid_configure(row=4)

        sidebar.grid_rowconfigure(2, weight=0)
        sidebar.grid_rowconfigure(3, weight=1)
        sidebar.grid_rowconfigure(4, weight=0)

        quick_actions = ctk.CTkFrame(sidebar, fg_color="transparent")
        quick_actions.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 10))
        quick_actions.grid_columnconfigure(0, weight=1)
        quick_actions.grid_columnconfigure(1, weight=1)

        ui.button(
            quick_actions,
            "Nieuw",
            self._new_template,
            width=82,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ui.button(
            quick_actions,
            "Capture",
            self._once,
            primary=True,
            width=88,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        live_row = ctk.CTkFrame(quick_actions, fg_color="transparent")
        live_row.grid(row=1, column=0, columnspan=2, sticky="e", pady=(7, 0))
        ctk.CTkSwitch(
            live_row,
            text="Live matching",
            variable=self.live,
            command=self._toggle_live,
            progress_color=ui.ACCENT,
            text_color=ui.MUTED,
            font=ui.font(10),
        ).pack()

    def _polish_detection_panel(self) -> None:
        """Show the exact search target above compact detection controls."""
        content = self._content_frame()
        detection = self._column_child(content, 3)
        if detection is None:
            return

        detection.configure(width=292)
        self.results.configure(height=92)

        target = ctk.CTkFrame(
            detection,
            fg_color=ui.CARD_ALT,
            corner_radius=8,
            border_width=1,
            border_color=ui.BORDER,
        )
        target.pack(
            before=self.method_box,
            fill="x",
            padx=16,
            pady=(2, 14),
        )

        title_row = ctk.CTkFrame(target, fg_color="transparent")
        title_row.pack(fill="x", padx=10, pady=(8, 5))
        ui.label(title_row, "ZOEKTEMPLATE", muted=True, size=10, bold=True).pack(
            side="left"
        )
        self.template_thumbnail_name = ui.label(
            title_row,
            "—",
            size=10,
            bold=True,
        )
        self.template_thumbnail_name.pack(side="right")

        preview_shell = ctk.CTkFrame(
            target,
            height=120,
            fg_color=ui.VIEW_BG,
            corner_radius=6,
        )
        preview_shell.pack(fill="x", padx=10, pady=(0, 10))
        preview_shell.pack_propagate(False)

        self.template_thumbnail = TemplateThumbnail(
            preview_shell,
            maximum_upscale=8.0,
        )
        self.template_thumbnail.pack(fill="both", expand=True, padx=6, pady=6)

    def _show_selected_template(self) -> None:
        if self.template_thumbnail is None or self.template_thumbnail_name is None:
            return
        if not self.selected:
            self.template_thumbnail_name.configure(text="Geen selectie")
            self.template_thumbnail.clear()
            return
        try:
            template_rgb, _template_gray = load_template(self.selected)
            self.template_thumbnail_name.configure(text=Path(self.selected).stem)
            self.template_thumbnail.show(template_rgb)
        except Exception:
            self.template_thumbnail_name.configure(text="Preview niet beschikbaar")
            self.template_thumbnail.clear()

    def _select(self, name: str) -> None:
        super()._select(name)
        self._show_selected_template()

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
                fg_color=ui.ACCENT_SOFT if selected else "transparent",
                hover_color=ui.ACCENT_SOFT,
                text_color=ui.ACCENT_HOVER if selected else ui.TEXT,
                font=ui.font(11),
            )
            button.grid(row=row, column=0, sticky="ew", pady=1)
            self.rows[name] = button

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
        content = self._content_frame()
        if content is None:
            return

        center = self._column_child(content, 1)
        detection = self._column_child(content, 2)
        if center is None or detection is None:
            return

        center.grid_configure(column=2, padx=(0, 8))
        detection.grid_configure(column=3)
        content.grid_columnconfigure(0, weight=0)
        content.grid_columnconfigure(1, weight=0)
        content.grid_columnconfigure(2, weight=1)
        content.grid_columnconfigure(3, weight=0)

        sidebar = ui.card(content, width=245)
        sidebar.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(2, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        ui.label(sidebar, "Areas", size=12, bold=True).grid(
            row=0,
            column=0,
            sticky="w",
            padx=14,
            pady=(14, 8),
        )
        area_search = ctk.CTkEntry(
            sidebar,
            textvariable=self.area_query,
            placeholder_text="Search areas...",
            height=38,
            corner_radius=8,
            fg_color=ui.CARD_ALT,
            border_color=ui.BORDER,
            text_color=ui.TEXT,
            font=ui.font(11),
        )
        area_search.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        area_search.bind("<KeyRelease>", self._filter_areas)
        area_search.bind("<Escape>", self._clear_area_search)

        self.area_scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            scrollbar_button_color=ui.BORDER,
            scrollbar_button_hover_color=ui.ACCENT_HOVER,
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
                fg_color=ui.ACCENT_SOFT if selected else "transparent",
                hover_color=ui.ACCENT_SOFT,
                text_color=ui.ACCENT_HOVER if selected else ui.TEXT,
                font=ui.font(11),
            )
            button.grid(row=row, column=0, sticky="ew", pady=1)
            self.area_rows[name] = button

    def _select_area(self, name: str) -> None:
        if name == self.source.area.get():
            return
        self.source.area.set(name)
        self._draw_areas()
        self.status.set(f"Area selected: {name}. Analysing again…")
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
        self._show_selected_template()
        self.live.set(True)
        self.status.set(f"New template {name} saved · Live matching active.")
        self.after_idle(self._capture)


__all__ = [
    "CleanTemplatePreview",
    "SearchableTemplatePage",
    "TemplateThumbnail",
]
