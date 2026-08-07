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
    """Keep Template clean while adding clear match state and searchable areas."""

    def __init__(self, parent):
        self.area_query = tk.StringVar(value="")
        self.match_state_text = tk.StringVar(value="—  WAITING")
        self.match_state_frame: tk.Frame | None = None
        self.match_state_label: tk.Label | None = None
        self._match_state: bool | None | object = object()
        self.area_scroll: ctk.CTkScrollableFrame | None = None
        self.area_rows: dict[str, ctk.CTkButton] = {}
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()
        self._add_area_search()
        self._add_area_browser()
        self._add_match_status_bar()

    def _area_names(self) -> list[str]:
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

    def _add_area_browser(self) -> None:
        # The original Template layout is:
        # Templates | Live Area | Detection.
        # Insert Areas between Templates and Live Area without redesigning either.
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

        sidebar = enhanced_ui.modern_ui._card(content, width=245)
        sidebar.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(2, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        enhanced_ui.modern_ui._label(
            sidebar,
            "AREAS",
            size=12,
            bold=True,
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))

        area_search = ctk.CTkEntry(
            sidebar,
            textvariable=self.area_query,
            placeholder_text="Zoek area",
            height=38,
            corner_radius=8,
            fg_color=enhanced_ui.modern_ui.CARD_ALT,
            border_color=enhanced_ui.modern_ui.BORDER,
            text_color=enhanced_ui.modern_ui.TEXT,
        )
        area_search.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        area_search.bind("<KeyRelease>", self._filter_areas)
        area_search.bind("<Escape>", self._clear_area_search)

        self.area_scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            scrollbar_button_color=enhanced_ui.modern_ui.BORDER,
            scrollbar_button_hover_color=enhanced_ui.modern_ui.GOLD,
        )
        self.area_scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.area_scroll.grid_columnconfigure(0, weight=1)

        enhanced_ui.modern_ui._label(
            sidebar,
            "Klik een area om direct opnieuw te testen.",
            muted=True,
            size=10,
            wraplength=210,
            justify="left",
        ).grid(row=3, column=0, sticky="w", padx=14, pady=(0, 12))

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
                fg_color=(
                    enhanced_ui.modern_ui.ACCENT_SOFT
                    if selected
                    else "transparent"
                ),
                hover_color=enhanced_ui.modern_ui.ACCENT_SOFT,
                text_color=(
                    enhanced_ui.modern_ui.ACCENT_HOVER
                    if selected
                    else enhanced_ui.modern_ui.TEXT
                ),
            )
            button.grid(row=row, column=0, sticky="ew", pady=1)
            self.area_rows[name] = button

    def _select_area(self, name: str) -> None:
        if name == self.source.area.get():
            return
        self.source.area.set(name)
        self._draw_areas()
        self._set_match_state(None)
        self.status.set(f"Area geselecteerd: {name}. Opnieuw analyseren…")
        if self.selected:
            self.after_idle(self._capture)

    def _filter_areas(self, _event=None) -> None:
        areas = self._area_names()
        matches = self._filtered_area_names()
        self.source.area_box.configure(values=matches or areas)
        self._draw_areas()

        # Keep the current area while it still matches. This avoids jumping to
        # another area merely because the user is typing a partial search.
        current = self.source.area.get()
        if current and current in matches:
            return

        # Do not silently select a broad first result. Only auto-select when the
        # partial search has narrowed the list down to one unambiguous area.
        if len(matches) == 1:
            self._select_area(matches[0])

    def _clear_area_search(self, _event=None) -> None:
        self.area_query.set("")
        self.source.area_box.configure(values=self._area_names())
        self._draw_areas()

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
        self.match_state_frame.pack_propagate(False)

        self.match_state_label = tk.Label(
            self.match_state_frame,
            textvariable=self.match_state_text,
            background=STATUS_WAIT_BG,
            foreground=STATUS_FG,
            font=("Segoe UI", 13, "bold"),
            anchor="center",
            bd=0,
            highlightthickness=0,
        )
        self.match_state_label.pack(fill="both", expand=True)
        self._match_state = None

    def _set_match_state(self, found: bool | None) -> None:
        if self.match_state_frame is None or self.match_state_label is None:
            return

        # Live analysis runs around ten times per second. Reconfiguring the
        # widgets every frame causes visible repaint jitter. Only repaint on a
        # real state transition.
        if found is self._match_state:
            return
        self._match_state = found

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
