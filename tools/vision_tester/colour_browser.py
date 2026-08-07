from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from core.vision.areas import load_areas
from core.vision.colour_presets import list_colour_presets, load_colour_preset

from . import enhanced_ui, unified_plus


CONTROL_MASK = 0x0004


class BrowserToleranceColourPage(unified_plus.ToleranceColourPage):
    """Colour tester with Template-style colour and area browsers."""

    def __init__(self, parent):
        self.colour_filter = tk.StringVar(value="")
        self.area_filter = tk.StringVar(value="")
        self._active_colour_names: set[str] = set()
        self._browser_ready = False
        self._browser_applying = False
        self.colour_scroll: ctk.CTkScrollableFrame | None = None
        self.area_scroll: ctk.CTkScrollableFrame | None = None
        self.colour_rows: dict[str, ctk.CTkButton] = {}
        self.area_rows: dict[str, ctk.CTkButton] = {}
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()

        # Keep the existing Colour tester intact and prepend two Template-style
        # browser columns: Colours | Areas | existing tester.
        existing = list(self.grid_slaves())
        for child in existing:
            info = child.grid_info()
            child.grid_configure(column=int(info.get("column", 0)) + 2)

        self.grid_columnconfigure(0, weight=0, minsize=245)
        self.grid_columnconfigure(1, weight=0, minsize=245)
        self.grid_columnconfigure(2, weight=1)

        self._build_colour_browser()
        self._build_area_browser()
        self._browser_ready = True
        self._draw_colour_browser()
        self._draw_area_browser()

    # ------------------------------------------------------------------
    # Template-style Colour browser
    # ------------------------------------------------------------------
    def _build_colour_browser(self) -> None:
        sidebar = enhanced_ui.modern_ui._card(self, width=245)
        sidebar.grid(
            row=0,
            column=0,
            rowspan=9,
            sticky="nsew",
            padx=(10, 8),
            pady=(5, 8),
        )
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(2, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        enhanced_ui.modern_ui._label(
            sidebar,
            "COLOURS",
            size=12,
            bold=True,
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))

        search = ctk.CTkEntry(
            sidebar,
            textvariable=self.colour_filter,
            placeholder_text="Zoek colour",
            height=38,
            corner_radius=8,
            fg_color=enhanced_ui.modern_ui.CARD_ALT,
            border_color=enhanced_ui.modern_ui.BORDER,
            text_color=enhanced_ui.modern_ui.TEXT,
        )
        search.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        search.bind("<KeyRelease>", self._colour_filter_changed)
        search.bind("<Escape>", self._clear_colour_filter)

        self.colour_scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            scrollbar_button_color=enhanced_ui.modern_ui.BORDER,
            scrollbar_button_hover_color=enhanced_ui.modern_ui.GOLD,
        )
        self.colour_scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.colour_scroll.grid_columnconfigure(0, weight=1)

        enhanced_ui.modern_ui._label(
            sidebar,
            "Klik = 1 colour  •  Ctrl+klik = meerdere",
            muted=True,
            size=10,
            wraplength=210,
            justify="left",
        ).grid(row=3, column=0, sticky="w", padx=14, pady=(0, 12))

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
        if not self._browser_ready or self.colour_scroll is None:
            return
        for child in self.colour_scroll.winfo_children():
            child.destroy()

        self.colour_rows.clear()
        for row, name in enumerate(self._filtered_colour_names()):
            selected = name in self._active_colour_names
            button = ctk.CTkButton(
                self.colour_scroll,
                text=name,
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
            # We handle Button-1 ourselves so the modifier state is available.
            button.configure(command=lambda: None)
            button.bind(
                "<Button-1>",
                lambda event, value=name: self._colour_clicked(event, value),
            )
            button.grid(row=row, column=0, sticky="ew", pady=1)
            self.colour_rows[name] = button

    def _colour_clicked(self, event, name: str):
        ctrl = bool(int(getattr(event, "state", 0)) & CONTROL_MASK)
        if ctrl:
            if name in self._active_colour_names:
                self._active_colour_names.remove(name)
            else:
                self._active_colour_names.add(name)
        else:
            self._active_colour_names = {name}

        self._draw_colour_browser()
        self._apply_active_colours()
        return "break"

    def _colour_filter_changed(self, _event=None) -> None:
        self._draw_colour_browser()

    def _clear_colour_filter(self, _event=None) -> None:
        self.colour_filter.set("")
        self._draw_colour_browser()

    # ------------------------------------------------------------------
    # Template-style Area browser
    # ------------------------------------------------------------------
    def _build_area_browser(self) -> None:
        sidebar = enhanced_ui.modern_ui._card(self, width=245)
        sidebar.grid(
            row=0,
            column=1,
            rowspan=9,
            sticky="nsew",
            padx=(0, 8),
            pady=(5, 8),
        )
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(2, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        enhanced_ui.modern_ui._label(
            sidebar,
            "AREAS",
            size=12,
            bold=True,
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))

        search = ctk.CTkEntry(
            sidebar,
            textvariable=self.area_filter,
            placeholder_text="Zoek area",
            height=38,
            corner_radius=8,
            fg_color=enhanced_ui.modern_ui.CARD_ALT,
            border_color=enhanced_ui.modern_ui.BORDER,
            text_color=enhanced_ui.modern_ui.TEXT,
        )
        search.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        search.bind("<KeyRelease>", self._area_filter_changed)
        search.bind("<Escape>", self._clear_area_filter)

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
            "Klik een area om direct opnieuw te capturen.",
            muted=True,
            size=10,
            wraplength=210,
            justify="left",
        ).grid(row=3, column=0, sticky="w", padx=14, pady=(0, 12))

    def _all_area_names(self) -> list[str]:
        return sorted(load_areas(), key=str.casefold)

    def _filtered_area_names(self) -> list[str]:
        terms = [
            term
            for term in self.area_filter.get().strip().casefold().split()
            if term
        ]
        return [
            name
            for name in self._all_area_names()
            if all(term in name.casefold() for term in terms)
        ]

    def _draw_area_browser(self) -> None:
        if not self._browser_ready or self.area_scroll is None:
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
        self.source.area.set(name)
        try:
            self.source.area_box.configure(values=self._all_area_names())
        except (AttributeError, tk.TclError):
            pass
        self._draw_area_browser()
        self.status.set(f"Area geselecteerd: {name}.")
        self.after_idle(self._capture)

    def _area_filter_changed(self, _event=None) -> None:
        matches = self._filtered_area_names()
        try:
            self.source.area_box.configure(values=matches or self._all_area_names())
        except (AttributeError, tk.TclError):
            pass
        self._draw_area_browser()
        current = self.source.area.get()
        if current and current in matches:
            return
        if len(matches) == 1:
            self._select_area(matches[0])

    def _clear_area_filter(self, _event=None) -> None:
        self.area_filter.set("")
        try:
            self.source.area_box.configure(values=self._all_area_names())
        except (AttributeError, tk.TclError):
            pass
        self._draw_area_browser()

    # ------------------------------------------------------------------
    # Preset combination / persistence
    # ------------------------------------------------------------------
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
            self._rebuild_ranges()
            self.status.set(
                f"{len(names)} colours tegelijk actief: "
                + ", ".join(names)
                + f" · tolerance {self.colour_tolerance.get()}%."
            )
        finally:
            self._browser_applying = False

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
    unified_plus.ToleranceColourPage = BrowserToleranceColourPage


__all__ = ["BrowserToleranceColourPage", "install_colour_browser"]
