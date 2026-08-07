from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from core.vision.colour_presets import list_colour_presets, load_colour_preset

from . import unified_plus


class BrowserToleranceColourPage(unified_plus.ToleranceColourPage):
    """Colour tester with a visible, searchable multi-select preset browser."""

    def __init__(self, parent):
        self.colour_filter = tk.StringVar(value="")
        self._active_colour_names: set[str] = set()
        self._visible_colour_names: list[str] = []
        self._browser_ready = False
        self._browser_applying = False
        self.colour_list: tk.Listbox | None = None
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()

        # Preserve the existing Unified/Tkinter Colour page exactly, but move it
        # one column to the right so a Template-like browser can sit beside it.
        existing = list(self.grid_slaves())
        for child in existing:
            info = child.grid_info()
            child.grid_configure(column=int(info.get("column", 0)) + 1)

        self.grid_columnconfigure(0, weight=0, minsize=235)
        self.grid_columnconfigure(1, weight=1)

        sidebar = ttk.LabelFrame(self, text="Colours", padding=(10, 8))
        sidebar.grid(
            row=0,
            column=0,
            rowspan=8,
            sticky="nsew",
            padx=(10, 0),
            pady=(5, 8),
        )
        sidebar.configure(width=225)
        sidebar.grid_propagate(False)
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(2, weight=1)

        ttk.Label(sidebar, text="Search").grid(row=0, column=0, sticky="w")
        search = ttk.Entry(sidebar, textvariable=self.colour_filter)
        search.grid(row=1, column=0, sticky="ew", pady=(4, 8))
        search.bind("<KeyRelease>", self._filter_changed)
        search.bind("<Escape>", self._clear_filter)

        list_frame = ttk.Frame(sidebar)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.colour_list = tk.Listbox(
            list_frame,
            selectmode=tk.MULTIPLE,
            exportselection=False,
            activestyle="none",
            borderwidth=1,
            highlightthickness=0,
            font=("Segoe UI", 10),
        )
        self.colour_list.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.colour_list.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.colour_list.configure(yscrollcommand=scrollbar.set)
        self.colour_list.bind("<<ListboxSelect>>", self._browser_selection_changed)

        ttk.Label(
            sidebar,
            text="Klik om kleuren aan/uit te zetten. Meerdere tegelijk is toegestaan.",
            wraplength=200,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(8, 4))
        ttk.Button(
            sidebar,
            text="Clear selection",
            command=self._clear_active_colours,
        ).grid(row=4, column=0, sticky="ew", pady=(4, 0))

        self._browser_ready = True
        self._draw_colour_browser()

    def _all_colour_names(self) -> list[str]:
        return sorted(list_colour_presets(), key=str.casefold)

    def _filtered_colour_names(self) -> list[str]:
        terms = [
            term
            for term in self.colour_filter.get().strip().casefold().split()
            if term
        ]
        return [
            name
            for name in self._all_colour_names()
            if all(term in name.casefold() for term in terms)
        ]

    def _draw_colour_browser(self) -> None:
        if not self._browser_ready or self.colour_list is None:
            return
        names = self._filtered_colour_names()
        self._visible_colour_names = names
        self.colour_list.delete(0, "end")
        for index, name in enumerate(names):
            self.colour_list.insert("end", name)
            if name in self._active_colour_names:
                self.colour_list.selection_set(index)

    def _filter_changed(self, _event=None) -> None:
        self._draw_colour_browser()

    def _clear_filter(self, _event=None) -> None:
        self.colour_filter.set("")
        self._draw_colour_browser()

    def _browser_selection_changed(self, _event=None) -> None:
        if self.colour_list is None or self._browser_applying:
            return

        visible = set(self._visible_colour_names)
        selected_visible = {
            self._visible_colour_names[index]
            for index in self.colour_list.curselection()
            if 0 <= index < len(self._visible_colour_names)
        }
        # A search should not silently disable selected colours that are merely
        # hidden by the filter.
        self._active_colour_names.difference_update(visible)
        self._active_colour_names.update(selected_visible)
        self._apply_active_colours()

    def _bases_for_preset(self, name: str) -> list[tuple[int, int, int]]:
        preset = load_colour_preset(name)
        meta = unified_plus._load_meta().get(name, {})
        colours = meta.get("colours") if isinstance(meta, dict) else None
        if isinstance(colours, list):
            parsed: list[tuple[int, int, int]] = []
            for item in colours:
                if isinstance(item, list) and len(item) == 3:
                    parsed.append(tuple(int(value) for value in item))
            if parsed:
                return parsed
        return unified_plus._infer_base_colours(preset.ranges)

    def _apply_active_colours(self) -> None:
        names = sorted(self._active_colour_names, key=str.casefold)
        if not names:
            self.base_colours = []
            self.ranges = ()
            self._reset_blob_history()
            self._render()
            self.status.set("Geen colour preset actief.")
            return

        self._browser_applying = True
        try:
            if len(names) == 1:
                name = names[0]
                self.current_preset.set(name)
                # Single-preset mode keeps its own saved tolerance metadata.
                super()._load_current_preset()
                self.status.set(f"Colour actief: {name}.")
                return

            merged: list[tuple[int, int, int]] = []
            seen: set[tuple[int, int, int]] = set()
            for name in names:
                for hsv in self._bases_for_preset(name):
                    if hsv not in seen:
                        seen.add(hsv)
                        merged.append(hsv)

            self.base_colours = merged
            # In multi-colour mode the one visible tolerance slider deliberately
            # controls every active base colour in the same way.
            self._rebuild_ranges()
            self.status.set(
                f"{len(names)} colours tegelijk actief: "
                + ", ".join(names)
                + f" · tolerance {self.colour_tolerance.get()}%."
            )
        finally:
            self._browser_applying = False

    def _clear_active_colours(self) -> None:
        self._active_colour_names.clear()
        if self.colour_list is not None:
            self.colour_list.selection_clear(0, "end")
        self._apply_active_colours()

    def _load_current_preset(self) -> None:
        super()._load_current_preset()
        if self._browser_ready and not self._browser_applying:
            name = self.current_preset.get().strip()
            self._active_colour_names = {name} if name else set()
            self._draw_colour_browser()

    def _reload_presets(self, *, selected: str | None = None) -> None:
        super()._reload_presets(selected=selected)
        if self._browser_ready:
            available = set(self._all_colour_names())
            self._active_colour_names.intersection_update(available)
            self._draw_colour_browser()

    def _save_current_preset(self) -> None:
        if len(self._active_colour_names) > 1:
            self.status.set(
                "Meerdere colours zijn actief. Laat één colour actief om die preset te bewerken/op te slaan."
            )
            return
        super()._save_current_preset()
        self._draw_colour_browser()

    def _delete_current_preset(self) -> None:
        name = self.current_preset.get().strip()
        super()._delete_current_preset()
        self._active_colour_names.discard(name)
        self._draw_colour_browser()


def install_colour_browser() -> None:
    """Swap the Colour page class used by Unified without touching its base UI."""
    unified_plus.ToleranceColourPage = BrowserToleranceColourPage


__all__ = ["BrowserToleranceColourPage", "install_colour_browser"]
