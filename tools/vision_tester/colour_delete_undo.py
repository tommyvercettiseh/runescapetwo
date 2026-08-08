from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from core.vision.colour_presets import (
    delete_colour_preset,
    load_colour_preset,
    save_colour_preset,
)

from . import colour_browser, unified_plus


_BROWSER_CLASS = colour_browser.BrowserToleranceColourPage
_ORIGINAL_BUILD_COLOUR_BROWSER = _BROWSER_CLASS._build_colour_browser


def _build_colour_browser_with_delete(self) -> None:
    self._deleted_colour_snapshot = None
    self._colour_trash_hide_job = None
    _ORIGINAL_BUILD_COLOUR_BROWSER(self)

    sidebar = self.colour_scroll.master if self.colour_scroll is not None else None
    if sidebar is None:
        return

    self.colour_undo_button = ctk.CTkButton(
        sidebar,
        text="Undo delete",
        command=self._undo_deleted_colour,
        height=32,
        corner_radius=7,
        fg_color=unified_plus.enhanced_ui.modern_ui.CARD_ALT,
        hover_color=unified_plus.enhanced_ui.modern_ui.ACCENT_SOFT,
        text_color=unified_plus.enhanced_ui.modern_ui.TEXT,
    )
    self.colour_undo_button.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 10))
    self.colour_undo_button.grid_remove()


def _show_trash(self, row, trash) -> None:
    if self._colour_trash_hide_job is not None:
        try:
            self.after_cancel(self._colour_trash_hide_job)
        except tk.TclError:
            pass
        self._colour_trash_hide_job = None
    if trash.winfo_exists():
        trash.pack(side="right", padx=(4, 2), pady=2)


def _hide_trash_later(self, row, trash) -> None:
    if self._colour_trash_hide_job is not None:
        try:
            self.after_cancel(self._colour_trash_hide_job)
        except tk.TclError:
            pass

    def hide() -> None:
        self._colour_trash_hide_job = None
        try:
            pointer = self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())
            if pointer in (row, trash) or (pointer is not None and pointer.master is row):
                return
            trash.pack_forget()
        except tk.TclError:
            pass

    self._colour_trash_hide_job = self.after(90, hide)


def _draw_colour_browser_with_delete(self) -> None:
    if not self._browser_ready or self.colour_scroll is None:
        return

    for child in self.colour_scroll.winfo_children():
        child.destroy()

    self.colour_rows.clear()
    ui = unified_plus.enhanced_ui.modern_ui

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
            fg_color=ui.ACCENT_SOFT if selected else "transparent",
            hover_color=ui.ACCENT_SOFT,
            text_color=ui.ACCENT_HOVER if selected else ui.TEXT,
        )
        main.pack(side="left", fill="x", expand=True)
        main.configure(command=lambda: None)
        main.bind("<Button-1>", lambda event, value=name: self._colour_clicked(event, value))

        trash = ctk.CTkButton(
            row,
            text="🗑",
            width=34,
            height=30,
            corner_radius=7,
            fg_color="transparent",
            hover_color=ui.ACCENT_SOFT,
            text_color=ui.TEXT,
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
    meta = meta_all.get(name)
    self._deleted_colour_snapshot = {
        "name": name,
        "ranges": tuple(preset.ranges),
        "meta": meta,
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

    was_active = name in self._active_colour_names or self.current_preset.get().strip() == name
    self._active_colour_names.discard(name)

    if self.current_preset.get().strip() == name:
        self.current_preset.set("")

    if was_active:
        self.base_colours = []
        self.ranges = ()
        self._reset_blob_history()
        self._render()

    self._draw_colour_browser()

    button = getattr(self, "colour_undo_button", None)
    if button is not None:
        button.configure(text=f"Undo delete · {name}")
        button.grid()

    self.status.set(f"Colour '{name}' verwijderd. Klik Undo om hem terug te zetten.")


def _undo_deleted_colour(self) -> None:
    snapshot = getattr(self, "_deleted_colour_snapshot", None)
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
    button = getattr(self, "colour_undo_button", None)
    if button is not None:
        button.grid_remove()

    self._active_colour_names = {name}
    self.current_preset.set(name)
    self._load_current_preset()
    self._draw_colour_browser()
    self.status.set(f"Colour '{name}' hersteld.")


def install_colour_delete_undo() -> None:
    _BROWSER_CLASS._build_colour_browser = _build_colour_browser_with_delete
    _BROWSER_CLASS._draw_colour_browser = _draw_colour_browser_with_delete
    _BROWSER_CLASS._show_colour_trash = _show_trash
    _BROWSER_CLASS._hide_colour_trash_later = _hide_trash_later
    _BROWSER_CLASS._delete_colour_from_browser = _delete_colour_from_browser
    _BROWSER_CLASS._undo_deleted_colour = _undo_deleted_colour


__all__ = ["install_colour_delete_undo"]
