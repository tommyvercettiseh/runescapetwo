from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog

import customtkinter as ctk

from core.vision.areas import load_areas
from core.vision.colour_detection import hsv_ranges_around, sample_hsv
from core.vision.colour_preset_meta import (
    delete_colour_preset_meta,
    infer_base_colours,
    load_colour_preset_meta,
    save_colour_preset_meta,
)
from core.vision.colour_presets import (
    delete_colour_preset,
    list_colour_presets,
    load_colour_preset,
    normalize_colour_name,
    save_colour_preset,
)

from . import ui
from .colour_base import ColourBasePage
from .enhanced_config import PIPETTE_EDGE_PADDING, SAMPLE_SIZES
from .screen_overlay import ScreenAreaOverlay

CONTROL_MASK = 0x0004
BLOB_MIN_LIMIT = 5000
BLOB_MAX_LIMIT = 10000
DEFAULT_PRESET_NAME = "cyan"
DEFAULT_TOLERANCE = 35


def filter_preset_names(names: list[str], query: str) -> list[str]:
    terms = [term for term in query.strip().casefold().split() if term]
    if not terms:
        return list(names)
    return [name for name in names if all(term in name.casefold() for term in terms)]


def format_ranges(ranges) -> str:
    if not ranges:
        return "No colour selected."
    return " | ".join(
        f"H {lower[0]}-{upper[0]}  S {lower[1]}-{upper[1]}  V {lower[2]}-{upper[2]}"
        for lower, upper in ranges
    )


def tolerance_values(value: int) -> tuple[int, int, int]:
    """Translate the friendly 0..100 slider to HSV tolerances."""
    amount = min(100, max(0, int(value))) / 100.0
    return (
        1 + round(14 * amount),
        8 + round(92 * amount),
        8 + round(92 * amount),
    )


class BrowserToleranceColourPage(ColourBasePage):
    """Single behaviour layer for the production Colour workspace.

    The concrete ColourPage owns layout. This base owns only reusable workspace
    state: presets, tolerance, browser selection, sampling and area-overlay
    lifecycle. No historical UI subclasses are involved anymore.
    """

    def __init__(self, parent) -> None:
        self.preset_search = tk.StringVar(master=parent, value="")
        self.current_preset = tk.StringVar(master=parent, value=DEFAULT_PRESET_NAME)
        self.preset_summary = tk.StringVar(master=parent, value="No colour selected.")
        self._preset_names: list[str] = []
        self.preset_box = None

        self.colour_tolerance = tk.IntVar(master=parent, value=DEFAULT_TOLERANCE)
        self.base_colours: list[tuple[int, int, int]] = []
        self.colour_count_text = tk.StringVar(master=parent, value="0 colours")
        self.tolerance_text = tk.StringVar(master=parent, value=f"{DEFAULT_TOLERANCE}%")

        self.colour_filter = tk.StringVar(master=parent, value="")
        self.area_filter = tk.StringVar(master=parent, value="")
        self._active_colour_names: set[str] = set()
        self._browser_ready = False
        self._browser_applying = False
        self._blob_slider_job: str | None = None
        self.colour_scroll: ctk.CTkScrollableFrame | None = None
        self.area_scroll: ctk.CTkScrollableFrame | None = None
        self.colour_rows: dict[str, ctk.CTkButton] = {}
        self.area_rows: dict[str, ctk.CTkButton] = {}

        self.pipette_sample_size = tk.IntVar(master=parent, value=1)
        self._screen_area_overlay: ScreenAreaOverlay | None = None

        super().__init__(parent)
        self._reload_presets()

    # Blob controls -----------------------------------------------------

    def _schedule_blob_render(self) -> None:
        if self._blob_slider_job is not None:
            try:
                self.after_cancel(self._blob_slider_job)
            except tk.TclError:
                pass
        self._blob_slider_job = self.after(45, self._render)

    def _blob_min_changed(self, value) -> None:
        minimum = max(1, round(float(value)))
        self.minimum.set(str(minimum))
        self.blob_min_slider_text.set(f"Min {minimum} px")
        self._schedule_blob_render()

    def _blob_max_changed(self, value) -> None:
        maximum = max(0, round(float(value)))
        if maximum <= 20:
            maximum = 0
            self.blob_max_slider_text.set("Max ∞")
        else:
            self.blob_max_slider_text.set(f"Max {maximum} px")
        self.maximum.set(str(maximum))
        self._schedule_blob_render()

    # Browser state -----------------------------------------------------

    @staticmethod
    def _all_colour_names() -> list[str]:
        return sorted(list_colour_presets(), key=str.casefold)

    def _filtered_colour_names(self) -> list[str]:
        return filter_preset_names(self._all_colour_names(), self.colour_filter.get())

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

    @staticmethod
    def _all_area_names() -> list[str]:
        return sorted(load_areas(), key=str.casefold)

    def _filtered_area_names(self) -> list[str]:
        terms = [term for term in self.area_filter.get().strip().casefold().split() if term]
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
                fg_color=ui.ACCENT_SOFT if selected else "transparent",
                hover_color=ui.ACCENT_SOFT,
                text_color=ui.ACCENT_HOVER if selected else ui.TEXT,
            )
            button.grid(row=row, column=0, sticky="ew", pady=1)
            self.area_rows[name] = button

    def _select_area(self, name: str) -> None:
        self.source.area.set(name)
        self._draw_area_browser()
        self.status.set(f"Area geselecteerd: {name}.")
        self.after_idle(self._capture)

    def _area_filter_changed(self, _event=None) -> None:
        self._draw_area_browser()
        current = self.source.area.get()
        matches = self._filtered_area_names()
        if current and current in matches:
            return
        if len(matches) == 1:
            self._select_area(matches[0])

    def _clear_area_filter(self, _event=None) -> None:
        self.area_filter.set("")
        self._draw_area_browser()

    def _bases_for_preset(self, name: str) -> list[tuple[int, int, int]]:
        preset = load_colour_preset(name)
        meta = load_colour_preset_meta(name)
        if meta is not None and meta.colours:
            return list(meta.colours)
        return list(infer_base_colours(preset.ranges))

    def _apply_active_colours(self) -> None:
        names = sorted(self._active_colour_names, key=str.casefold)
        if not names:
            self.base_colours = []
            self.ranges = ()
            self._reset_blob_history()
            self._render()
            self.status.set("Geen colour actief.")
            return

        self._browser_applying = True
        try:
            if len(names) == 1:
                name = names[0]
                self.current_preset.set(name)
                self._load_current_preset()
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

    # Tolerance and sampling -------------------------------------------

    def _rebuild_ranges(self) -> None:
        hue, saturation, brightness = tolerance_values(self.colour_tolerance.get())
        combined = []
        for hsv in self.base_colours:
            combined.extend(
                hsv_ranges_around(
                    hsv,
                    hue_tolerance=hue,
                    saturation_tolerance=saturation,
                    value_tolerance=brightness,
                )
            )
        self.ranges = tuple(combined)
        count = len(self.base_colours)
        self.colour_count_text.set(f"{count} colour" if count == 1 else f"{count} colours")
        self.tolerance_text.set(f"{int(self.colour_tolerance.get())}%")
        self._update_preset_summary()
        self._reset_blob_history()
        self._render()

    def _tolerance_changed(self, value) -> None:
        self.colour_tolerance.set(round(float(value)))
        self._rebuild_ranges()

    def _selected_sample_size(self) -> int:
        try:
            value = int(self.pipette_sample_size.get())
        except (TypeError, ValueError):
            return 1
        return value if value in SAMPLE_SIZES else 1

    def _pick(self, event) -> None:
        if self.capture is None or not self.pipette:
            return
        point = self.capture_view.image_coordinates(event.x, event.y)
        if point is None:
            return

        x, y = point
        height, width = self.capture.shape[:2]
        padding = PIPETTE_EDGE_PADDING
        if x < padding or y < padding or x >= width - padding or y >= height - padding:
            self.status.set(
                f"Pipette: choose inside the safe area ({padding}px edge padding)."
            )
            return

        sample_size = self._selected_sample_size()
        hsv = sample_hsv(self.capture, x, y, radius=sample_size // 2)
        if hsv not in self.base_colours:
            self.base_colours.append(hsv)
        self.capture_view.set_marker(x, y, sample_size)
        self._rebuild_ranges()
        self.status.set(
            f"Added colour {hsv} to {self.current_preset.get()} • "
            f"{len(self.base_colours)} base colour(s) • "
            f"tolerance {self.colour_tolerance.get()}%."
        )

        if len(self._active_colour_names) == 1 and self._autosave_after_pick():
            self._save_current_preset()

    def _autosave_after_pick(self) -> bool:
        return True

    def _remove_last_colour(self) -> None:
        if self.base_colours:
            self.base_colours.pop()
            self._rebuild_ranges()
            self.status.set("Last base colour removed.")

    def _clear_colours(self) -> None:
        self.base_colours.clear()
        self.capture_view.clear_marker()
        self._rebuild_ranges()
        self.status.set("Base colours cleared.")

    # Presets -----------------------------------------------------------

    def _refresh_preset_box(self) -> None:
        if self.preset_box is None:
            return
        values = filter_preset_names(self._preset_names, self.preset_search.get())
        self.preset_box.configure(values=values or self._preset_names or [DEFAULT_PRESET_NAME])

    def _reload_presets(self, *, selected: str | None = None) -> None:
        self._preset_names = list(list_colour_presets())
        if selected:
            self.current_preset.set(selected)
        elif self.current_preset.get() not in self._preset_names:
            self.current_preset.set(
                self._preset_names[0] if self._preset_names else DEFAULT_PRESET_NAME
            )
        self._refresh_preset_box()
        if self._browser_ready:
            self._active_colour_names.intersection_update(self._preset_names)
            self._draw_colour_browser()
        if not self._preset_names:
            self.status.set("No presets saved. Pick a colour and save it.")

    def _load_current_preset(self) -> None:
        name = self.current_preset.get().strip()
        if not name:
            messagebox.showerror("Preset", "Preset name is required.")
            return
        try:
            preset = load_colour_preset(name)
        except (KeyError, ValueError) as exc:
            self.status.set(str(exc))
            return

        self.ranges = preset.ranges
        self.current_preset.set(preset.name)
        meta = load_colour_preset_meta(preset.name)
        if meta is not None and meta.colours is not None:
            self.base_colours = list(meta.colours)
        else:
            self.base_colours = list(infer_base_colours(preset.ranges))
        self.colour_tolerance.set(meta.tolerance if meta is not None else DEFAULT_TOLERANCE)
        self._rebuild_ranges()
        self.status.set(f"Preset loaded: {preset.name}.")

        if self._browser_ready and not self._browser_applying:
            self._active_colour_names = {preset.name}
            self._draw_colour_browser()

    def _new_preset(self) -> None:
        self.base_colours = []
        self.colour_tolerance.set(DEFAULT_TOLERANCE)
        self._rebuild_ranges()
        name = simpledialog.askstring("New preset", "Preset name:", parent=self.winfo_toplevel())
        if name is None:
            return
        try:
            normalized = normalize_colour_name(name)
        except ValueError as exc:
            messagebox.showerror("Preset", str(exc))
            return
        self.current_preset.set(normalized)
        self.preset_search.set("")
        self.status.set(f"New preset ready: {normalized}. Pick a colour and save it.")

    def _save_current_preset(self) -> None:
        if len(self._active_colour_names) > 1:
            self.status.set(
                "Meerdere colours zijn actief; deze combinatie wordt niet als één preset opgeslagen."
            )
            return
        self._rebuild_ranges()
        name = self.current_preset.get().strip()
        if not name:
            messagebox.showerror("Preset", "Preset name is required.")
            return
        if not self.ranges:
            messagebox.showerror("Preset", "Pick a colour with the pipette before saving.")
            return
        try:
            normalized = normalize_colour_name(name)
            save_colour_preset(normalized, self.ranges)
            if self.base_colours:
                save_colour_preset_meta(
                    normalized,
                    tolerance=int(self.colour_tolerance.get()),
                    colours=self.base_colours,
                )
        except (OSError, ValueError) as exc:
            messagebox.showerror("Preset", str(exc))
            return

        self._reload_presets(selected=normalized)
        self._update_preset_summary()
        self._draw_colour_browser()
        self.status.set(f"Preset saved: {normalized}.")

    def _delete_current_preset(self) -> None:
        name = self.current_preset.get().strip()
        if not name:
            return
        if not messagebox.askyesno(
            "Delete preset",
            f"Delete preset '{name}'?",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            deleted = delete_colour_preset(name)
            if deleted:
                delete_colour_preset_meta(name)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Preset", str(exc))
            return
        if not deleted:
            self.status.set(f"Preset not found: {name}.")
            return

        self._active_colour_names.discard(name)
        self.base_colours = []
        self.ranges = ()
        self.preset_summary.set("No colour selected.")
        self._reload_presets()
        self._render()
        self._draw_colour_browser()
        self.status.set(f"Preset deleted: {name}.")

    def _update_preset_summary(self) -> None:
        self.preset_summary.set(f"{self.current_preset.get()}: {format_ranges(self.ranges)}")

    # Capture overlay ---------------------------------------------------

    def _draw_blob_overlay(self, _blob, _safe_bounds=None):
        """Keep the in-app live preview clean; desktop overlay owns target guides."""
        return self.capture.copy()

    def _overlay_toggle_changed(self) -> None:
        overlay = self._screen_area_overlay
        if overlay is None:
            return
        if not self.source.show_area_overlay.get():
            overlay.hide()
            return
        if self.source.area.get().strip() and self.capture is not None:
            overlay.show_region(self.capture_region)

    def _capture(self) -> None:
        if not self.source.area.get().strip():
            if self._screen_area_overlay is not None:
                self._screen_area_overlay.hide()
            self.capture = None
            self.status.set("Selecteer eerst een area.")
            return

        overlay = self._screen_area_overlay
        if overlay is not None and not overlay.capture_excluded:
            overlay.hide()
            self.update_idletasks()

        super()._capture()
        if self.capture is None:
            return

        if overlay is None:
            try:
                overlay = ScreenAreaOverlay(self.winfo_toplevel())
            except (tk.TclError, AttributeError):
                overlay = None
            self._screen_area_overlay = overlay
        if overlay is not None:
            overlay.show_region(self.capture_region)
            if not self.source.show_area_overlay.get():
                overlay.hide()

    def deactivate(self) -> None:
        super().deactivate()
        if self._screen_area_overlay is not None:
            self._screen_area_overlay.hide()


__all__ = [
    "BLOB_MAX_LIMIT",
    "BLOB_MIN_LIMIT",
    "BrowserToleranceColourPage",
    "DEFAULT_PRESET_NAME",
    "DEFAULT_TOLERANCE",
    "filter_preset_names",
    "format_ranges",
    "tolerance_values",
]
