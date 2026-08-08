from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from core.vision.colour_presets import (
    delete_colour_preset,
    load_colour_preset,
    save_colour_preset,
)

from . import modern_ui, unified_plus
from .manual_colour_save import ManualColourPage


class DeleteUndoColourPage(ManualColourPage):
    """Manual colour page with hover-delete and one-step undo."""

    def __init__(self, parent) -> None:
        self._deleted_colour_snapshot = None
        self._colour_trash_hide_job: str | None = None
        super().__init__(parent)

    def _build_colour_browser(self) -> None:
        super()._build_colour_browser()
        sidebar = self.colour_scroll.master if self.colour_scroll is not None else None
        if sidebar is None:
            return

        self.colour_undo_button = ctk.CTkButton(
            sidebar,
            text="Undo delete",
            command=self._undo_deleted_colour,
            height=32,
            corner_radius=7,
            fg_color=modern_ui.CARD_ALT,
            hover_color=modern_ui.ACCENT_SOFT,
            text_color=modern_ui.TEXT,
        )
        self.colour_undo_button.grid(
            row=6,
            column=0,
            sticky="ew",
            padx=14,
            pady=(0, 10),
        )
        self.colour_undo_button.grid_remove()

    def _show_colour_trash(self, row, trash) -> None:
        if self._colour_trash_hide_job is not None:
            try:
                self.after_cancel(self._colour_trash_hide_job)
            except tk.TclError:
                pass
            self._colour_trash_hide_job = None
        if trash.winfo_exists():
            trash.pack(side="right", padx=(4, 2), pady=2)

    def _hide_colour_trash_later(self, row, trash) -> None:
        if self._colour_trash_hide_job is not None:
            try:
                self.after_cancel(self._colour_trash_hide_job)
            except tk.TclError:
                pass

        def hide() -> None:
            self._colour_trash_hide_job = None
            try:
                pointer = self.winfo_containing(
                    self.winfo_pointerx(),
                    self.winfo_pointery(),
                )
                if pointer in (row, trash) or (
                    pointer is not None and pointer.master is row
                ):
                    return
                trash.pack_forget()
            except tk.TclError:
                pass

        self._colour_trash_hide_job = self.after(90, hide)

    def _draw_colour_browser(self) -> None:
        if not self._browser_ready or self.colour_scroll is None:
            return

        for child in self.colour_scroll.winfo_children():
            child.destroy()

        self.colour_rows.clear()
        for row_index, name in enumerate(self._filtered_colour_names()):
            selected = name in self._active_colour_names
            row = ctk.CTkFrame(
                self.colour_scroll,
                fg_color="transparent",
                corner_radius=7,
                height=36,
            )
            row.grid(row=row_index, column=0, sticky="ew", pady=1)
            row.grid_columnconfigure(0, weight=1)

            main = ctk.CTkButton(
                row,
                text=name,
                anchor="w",
                height=34,
                corner_radius=7,
                fg_color=modern_ui.ACCENT_SOFT if selected else "transparent",
                hover_color=modern_ui.ACCENT_SOFT,
                text_color=(
                    modern_ui.ACCENT_HOVER if selected else modern_ui.TEXT
                ),
            )
            main.pack(side="left", fill="x", expand=True)
            main.configure(command=lambda: None)
            main.bind(
                "<Button-1>",
                lambda event, value=name: self._colour_clicked(event, value),
            )

            trash = ctk.CTkButton(
                row,
                text="🗑",
                width=34,
                height=30,
                corner_radius=7,
                fg_color="transparent",
                hover_color=modern_ui.ACCENT_SOFT,
                text_color=modern_ui.TEXT,
                command=lambda value=name: self._delete_colour_from_browser(value),
            )
            for widget in (row, main, trash):
                widget.bind(
                    "<Enter>",
                    lambda _event, r=row, t=trash: self._show_colour_trash(r, t),
                    add="+",
                )
                widget.bind(
                    "<Leave>",
                    lambda _event, r=row, t=trash: self._hide_colour_trash_later(r, t),
                    add="+",
                )
            self.colour_rows[name] = main

    def _delete_colour_from_browser(self, name: str) -> None:
        try:
            preset = load_colour_preset(name)
        except (KeyError, ValueError):
            self.status.set(f"Colour '{name}' kon niet worden geladen.")
            return

        meta_all = unified_plus._load_meta()
        self._deleted_colour_snapshot = {
            "name": name,
            "ranges": tuple(preset.ranges),
            "meta": meta_all.get(name),
        }

        if not delete_colour_preset(name):
            self.status.set(f"Colour '{name}' kon niet worden verwijderd.")
            return

        if name in meta_all:
            meta_all.pop(name, None)
            try:
                unified_plus._save_meta(meta_all)
            except OSError:
                pass

        was_active = (
            name in self._active_colour_names
            or self.current_preset.get().strip() == name
        )
        self._active_colour_names.discard(name)
        if self.current_preset.get().strip() == name:
            self.current_preset.set("")

        if was_active:
            self.base_colours = []
            self.ranges = ()
            self._reset_blob_history()
            self._render()

        self._draw_colour_browser()
        self.colour_undo_button.configure(text=f"Undo delete · {name}")
        self.colour_undo_button.grid()
        self.status.set(
            f"Colour '{name}' verwijderd. Klik Undo om hem terug te zetten."
        )

    def _undo_deleted_colour(self) -> None:
        snapshot = self._deleted_colour_snapshot
        if not snapshot:
            return

        name = snapshot["name"]
        save_colour_preset(name, snapshot["ranges"])
        meta = snapshot.get("meta")
        if isinstance(meta, dict):
            meta_all = unified_plus._load_meta()
            meta_all[name] = meta
            try:
                unified_plus._save_meta(meta_all)
            except OSError:
                pass

        self._deleted_colour_snapshot = None
        self.colour_undo_button.grid_remove()
        self._active_colour_names = {name}
        self.current_preset.set(name)
        self._load_current_preset()
        self._draw_colour_browser()
        self.status.set(f"Colour '{name}' hersteld.")


def install_colour_delete_undo() -> None:
    """Compatibility no-op; use DeleteUndoColourPage explicitly."""


__all__ = ["DeleteUndoColourPage", "install_colour_delete_undo"]
