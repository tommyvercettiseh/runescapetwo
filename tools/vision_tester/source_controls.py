from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from core.vision.areas import load_areas
from .ui import DEFAULT_AREA


class SourceState:
    """Small shared source model for pages that render their own controls."""

    def __init__(
        self,
        master,
        *,
        default_area: str = DEFAULT_AREA,
        require_selection: bool = True,
    ) -> None:
        self.areas = sorted(load_areas())
        selected = (
            ""
            if require_selection
            else default_area
            if default_area in self.areas
            else self.areas[0]
            if self.areas
            else "game"
        )
        self.bot_id = tk.StringVar(master=master, value="1")
        self.area = tk.StringVar(master=master, value=selected)
        self.show_area_overlay = tk.BooleanVar(master=master, value=True)

    def bot(self) -> int:
        return int(self.bot_id.get())


class SearchableSourceControls(ttk.Frame):
    """Source controls with deliberate area selection and live partial filtering."""

    def __init__(
        self,
        parent,
        *,
        default_area: str = DEFAULT_AREA,
        require_selection: bool = True,
        overlay_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._overlay_changed = overlay_changed
        self.state = SourceState(
            self,
            default_area=default_area,
            require_selection=require_selection,
        )
        self._areas = self.state.areas
        self.bot_id = self.state.bot_id
        self.area = self.state.area
        self.show_area_overlay = self.state.show_area_overlay
        self.area_search = tk.StringVar(master=self)

        ttk.Label(self, text="Bot ID").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(
            self,
            from_=1,
            to=4,
            textvariable=self.bot_id,
            width=5,
        ).grid(row=0, column=1, sticky="w", padx=(7, 18))

        ttk.Label(self, text="Area search").grid(row=0, column=2, sticky="w")
        search = ttk.Entry(self, textvariable=self.area_search, width=18)
        search.grid(row=0, column=3, sticky="ew", padx=(7, 14))
        search.bind("<KeyRelease>", self._filter_areas)

        ttk.Label(self, text="Area").grid(row=0, column=4, sticky="w")
        self.area_box = ttk.Combobox(
            self,
            values=["", *self._areas] if require_selection else self._areas,
            textvariable=self.area,
            width=30,
            state="readonly",
        )
        self.area_box.grid(row=0, column=5, sticky="ew", padx=(7, 0))
        self.area_box.bind("<<ComboboxSelected>>", self._area_selected)

        ttk.Checkbutton(
            self,
            text="Show area overlay",
            variable=self.show_area_overlay,
            command=self._notify_overlay_changed,
        ).grid(row=0, column=6, sticky="w", padx=(14, 0))

        self.columnconfigure(3, weight=1)
        self.columnconfigure(5, weight=2)

    def _filter_areas(self, _event=None) -> None:
        terms = [
            part
            for part in self.area_search.get().casefold().split()
            if part
        ]
        matches = [
            area
            for area in self._areas
            if all(term in area.casefold() for term in terms)
        ]
        self.area_box.configure(values=["", *matches])
        if len(matches) == 1:
            self.area.set(matches[0])
            self._notify_overlay_changed()

    def _area_selected(self, _event=None) -> None:
        self._notify_overlay_changed()

    def _notify_overlay_changed(self) -> None:
        if self._overlay_changed is not None:
            self._overlay_changed()

    def bot(self) -> int:
        return self.state.bot()


__all__ = ["SearchableSourceControls", "SourceState"]
