from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.vision.areas import load_areas
from . import modern_ui


class SearchableSourceControls(ttk.Frame):
    """Source controls with live partial area filtering."""

    def __init__(
        self,
        parent,
        *,
        default_area: str = modern_ui.DEFAULT_AREA,
    ) -> None:
        super().__init__(parent)
        self._areas = sorted(load_areas())
        selected = (
            default_area
            if default_area in self._areas
            else self._areas[0]
            if self._areas
            else "game"
        )
        self.bot_id = tk.StringVar(value="1")
        self.area = tk.StringVar(value=selected)
        self.area_search = tk.StringVar()

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
            values=self._areas,
            textvariable=self.area,
            width=30,
            state="readonly",
        )
        self.area_box.grid(row=0, column=5, sticky="ew", padx=(7, 0))
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
        self.area_box.configure(values=matches)
        if len(matches) == 1:
            self.area.set(matches[0])

    def bot(self) -> int:
        return int(self.bot_id.get())


__all__ = ["SearchableSourceControls"]
