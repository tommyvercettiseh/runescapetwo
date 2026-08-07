from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from core.vision.areas import load_areas

from . import enhanced_ui


STATUS_WAIT_BG = "#6b7280"
STATUS_FOUND_BG = "#15803d"
STATUS_MISSING_BG = "#b91c1c"
STATUS_FG = "#ffffff"


class SearchableTemplatePage(enhanced_ui.modern_ui.TemplatePage):
    """Keep the existing Template page, adding only clearer match state and area search."""

    def __init__(self, parent):
        self.area_query = tk.StringVar(value="")
        self.match_state_text = tk.StringVar(value="—  WAITING")
        self.match_state_frame: tk.Frame | None = None
        self.match_state_label: tk.Label | None = None
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()
        self._add_area_search()
        self._add_match_status_bar()

    def _add_area_search(self) -> None:
        source = self.source
        source.grid_columnconfigure(1, weight=1)
        source.grid_columnconfigure(2, weight=1)

        enhanced_ui.modern_ui._label(
            source,
            "ZOEK AREA",
            muted=True,
            size=11,
        ).grid(row=0, column=2, sticky="w", padx=(12, 0))

        self.area_search_entry = ctk.CTkEntry(
            source,
            textvariable=self.area_query,
            placeholder_text="Zoek deel van area naam",
            height=38,
            corner_radius=8,
            fg_color=enhanced_ui.modern_ui.CARD_ALT,
            border_color=enhanced_ui.modern_ui.BORDER,
            text_color=enhanced_ui.modern_ui.TEXT,
        )
        self.area_search_entry.grid(
            row=1,
            column=2,
            sticky="ew",
            padx=(12, 0),
            pady=(4, 0),
        )
        self.area_search_entry.bind("<KeyRelease>", self._filter_areas)
        self.area_search_entry.bind("<Escape>", self._clear_area_search)

    def _filter_areas(self, _event=None) -> None:
        areas = sorted(load_areas())
        terms = [term for term in self.area_query.get().strip().casefold().split() if term]
        matches = [
            name
            for name in areas
            if all(term in name.casefold() for term in terms)
        ]
        self.source.area_box.configure(values=matches or areas)

        current = self.source.area.get()
        if matches and current not in matches:
            self.source.area.set(matches[0])
            self._set_match_state(None)
            if self.live.get():
                self.after_idle(self._capture)

    def _clear_area_search(self, _event=None) -> None:
        self.area_query.set("")
        self.source.area_box.configure(values=sorted(load_areas()))

    def _add_match_status_bar(self) -> None:
        toolbar = self.source.master
        toolbar.grid_columnconfigure(0, weight=1)

        self.match_state_frame = tk.Frame(
            toolbar,
            background=STATUS_WAIT_BG,
            height=42,
            bd=0,
            highlightthickness=0,
        )
        self.match_state_frame.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=16,
            pady=(0, 12),
        )
        self.match_state_frame.grid_propagate(False)

        self.match_state_label = tk.Label(
            self.match_state_frame,
            textvariable=self.match_state_text,
            background=STATUS_WAIT_BG,
            foreground=STATUS_FG,
            font=("Segoe UI", 13, "bold"),
            anchor="center",
        )
        self.match_state_label.pack(fill="both", expand=True)

    def _set_match_state(self, found: bool | None) -> None:
        if self.match_state_frame is None or self.match_state_label is None:
            return

        if found is True:
            text = "TRUE  ·  FOUND"
            background = STATUS_FOUND_BG
        elif found is False:
            text = "FALSE  ·  NOT FOUND"
            background = STATUS_MISSING_BG
        else:
            text = "—  WAITING"
            background = STATUS_WAIT_BG

        self.match_state_text.set(text)
        self.match_state_frame.configure(background=background)
        self.match_state_label.configure(background=background)

    def _select(self, name: str) -> None:
        self._set_match_state(None)
        super()._select(name)

    def _capture(self) -> None:
        if not self.selected:
            self._set_match_state(None)
        super()._capture()

    def _analyse(self) -> None:
        super()._analyse()
        if self.screenshot is None or not self.selected:
            self._set_match_state(None)
            return
        self._set_match_state(self.best_valid_bounds is not None)

    def _delete(self) -> None:
        super()._delete()
        if not self.selected:
            self._set_match_state(None)


def install_template_plus() -> None:
    """Install the Template-page enhancement before Unified Vision Tester is built."""
    if enhanced_ui.modern_ui.TemplatePage is not SearchableTemplatePage:
        enhanced_ui.modern_ui.TemplatePage = SearchableTemplatePage


__all__ = ["SearchableTemplatePage", "install_template_plus"]
