from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog, ttk

import customtkinter as ctk

from core.vision.colour_preset_meta import (
    delete_colour_preset_meta,
    restore_colour_preset_meta,
    snapshot_colour_preset_meta,
)
from core.vision.colour_presets import (
    delete_colour_preset,
    list_colour_presets,
    load_colour_preset,
    normalize_colour_name,
    save_colour_preset,
)

from . import modern_ui
from .colour_browser import BrowserToleranceColourPage
from .colour_replay import ColourReplayController, REPLAY_SPEEDS
from .stoplight_panel import StoplightPanel
from .unified_plus import DEFAULT_TOLERANCE


class ColourPage(BrowserToleranceColourPage):
    """Production colour workspace with explicit editing, replay and sensor composition."""

    def __init__(self, parent) -> None:
        self._deleted_colour_snapshot: dict[str, object] | None = None
        self._colour_trash_hide_job: str | None = None
        self.stoplight_panel: StoplightPanel | None = None
        self.replay: ColourReplayController | None = None
        super().__init__(parent)

        self.replay = ColourReplayController(
            self,
            capture_getter=lambda: self.capture,
            capture_setter=self._set_replay_capture,
            area_getter=lambda: self.source.area.get(),
            bot_id_getter=self.source.bot,
            live_setter=self.live.set,
            status_setter=self.status.set,
            render=self._render,
        )
        self._add_recording_controls()

    def _build(self) -> None:
        super()._build()
        self._add_stoplight_panel()

    # Colour editing -----------------------------------------------------

    def _build_colour_browser(self) -> None:
        super()._build_colour_browser()
        self.new_colour_button.configure(
            text="Add new colour",
            command=self._new_colour_from_browser,
        )

        sidebar = self.new_colour_button.master
        for child in list(sidebar.grid_slaves()):
            if child is self.new_colour_button:
                continue
            info = child.grid_info()
            row = int(info.get("row", 0))
            if row >= 3:
                child.grid_configure(row=row + 1)

        sidebar.grid_rowconfigure(3, weight=0)
        sidebar.grid_rowconfigure(4, weight=1)

        self.save_colour_button = ctk.CTkButton(
            sidebar,
            text="Save updated colour",
            command=self._save_colour_from_browser,
            height=34,
            corner_radius=7,
            fg_color=modern_ui.CARD_ALT,
            hover_color=modern_ui.ACCENT_SOFT,
            text_color=modern_ui.TEXT,
        )
        self.save_colour_button.grid(
            row=3,
            column=0,
            sticky="ew",
            padx=14,
            pady=(0, 9),
        )

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

    def _new_colour_from_browser(self) -> None:
        name = simpledialog.askstring(
            "Add new colour",
            "Naam van de colour:",
            parent=self.winfo_toplevel(),
        )
        if name is None:
            return

        try:
            name = normalize_colour_name(name)
        except ValueError:
            self.status.set("Colour niet aangemaakt: naam ontbreekt.")
            return

        if name in set(list_colour_presets()):
            self._active_colour_names = {name}
            self.current_preset.set(name)
            self._load_current_preset()
            self._draw_colour_browser()
            self.status.set(f"Colour '{name}' bestaat al en is geselecteerd.")
            return

        self.current_preset.set(name)
        self.base_colours = []
        self.colour_tolerance.set(DEFAULT_TOLERANCE)
        self._active_colour_names = {name}
        self._rebuild_ranges()

        if not self.pipette:
            self._toggle_pipette()

        self.status.set(
            f"Nieuwe colour '{name}' klaar. "
            "Klik kleur(en) met het pipet en daarna Save updated colour."
        )

    def _autosave_after_pick(self) -> bool:
        """Production editing is explicit; picking never persists automatically."""
        return False

    def _save_colour_from_browser(self) -> None:
        active = set(self._active_colour_names)
        if len(active) != 1:
            self.status.set(
                "Selecteer precies één colour om op te slaan of te updaten."
                if active
                else "Selecteer eerst één colour om op te slaan of te updaten."
            )
            return

        name = normalize_colour_name(next(iter(active)))
        if not self.base_colours:
            self.status.set(
                f"Colour '{name}' heeft nog geen gepipette kleur; niets opgeslagen."
            )
            return

        self.current_preset.set(name)
        super()._save_current_preset()
        self._active_colour_names = {name}
        self._draw_colour_browser()
        self.status.set(
            f"Colour '{name}' bijgewerkt · {len(self.base_colours)} kleur(en) · "
            f"tolerance {self.colour_tolerance.get()}%."
        )

    # Delete and undo ----------------------------------------------------

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
                text_color=modern_ui.ACCENT_HOVER if selected else modern_ui.TEXT,
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

    def _delete_colour_from_browser(self, name: str) -> None:
        try:
            preset = load_colour_preset(name)
        except (KeyError, ValueError):
            self.status.set(f"Colour '{name}' kon niet worden geladen.")
            return

        self._deleted_colour_snapshot = {
            "name": name,
            "ranges": tuple(preset.ranges),
            "meta": snapshot_colour_preset_meta(name),
        }

        if not delete_colour_preset(name):
            self.status.set(f"Colour '{name}' kon niet worden verwijderd.")
            return

        try:
            delete_colour_preset_meta(name)
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

        name = str(snapshot["name"])
        save_colour_preset(name, snapshot["ranges"])

        meta = snapshot.get("meta")
        if isinstance(meta, dict):
            try:
                restore_colour_preset_meta(name, meta)
            except OSError:
                pass

        self._deleted_colour_snapshot = None
        self.colour_undo_button.grid_remove()
        self._active_colour_names = {name}
        self.current_preset.set(name)
        self._load_current_preset()
        self._draw_colour_browser()
        self.status.set(f"Colour '{name}' hersteld.")

    # Replay -------------------------------------------------------------

    def _add_recording_controls(self) -> None:
        replay = self.replay
        if replay is None:
            return

        toolbar = self.source.master
        controls = ttk.Frame(toolbar)
        controls.grid(row=0, column=3, sticky="e", padx=(12, 8))

        ttk.Button(
            controls,
            textvariable=replay.record_text,
            command=replay.toggle_recording,
        ).pack(side="left")
        ttk.Button(
            controls,
            textvariable=replay.play_text,
            command=replay.play_or_pause,
        ).pack(side="left", padx=(6, 0))
        ttk.Combobox(
            controls,
            values=REPLAY_SPEEDS,
            textvariable=replay.replay_speed,
            state="readonly",
            width=5,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            controls,
            text="Reset Replay",
            command=replay.reset_replay,
        ).pack(side="left", padx=(6, 0))
        ttk.Label(controls, textvariable=replay.replay_info).pack(
            side="left",
            padx=(8, 0),
        )

    def _set_replay_capture(
        self,
        capture,
        region: tuple[int, int, int, int],
    ) -> None:
        self.capture = capture
        self.capture_region = region

    # Sensor composition ------------------------------------------------

    def _add_stoplight_panel(self) -> None:
        toolbar = self.source.master
        self.stoplight_panel = StoplightPanel(toolbar)
        self.stoplight_panel.grid(
            row=5,
            column=0,
            columnspan=7,
            sticky="ew",
            padx=8,
            pady=(5, 0),
        )

    def _render(self, started=None) -> None:
        super()._render(started)
        if self.stoplight_panel is not None:
            self.stoplight_panel.update_readings(
                self.capture,
                current_area=self.source.area.get().strip(),
            )

    # Lifecycle ---------------------------------------------------------

    def _capture(self) -> None:
        if self.replay is not None and self.replay.replay_active:
            return
        super()._capture()
        if self.replay is not None:
            self.replay.capture_frame()

    def deactivate(self) -> None:
        if self.replay is not None:
            self.replay.deactivate()
        super().deactivate()


__all__ = ["ColourPage"]
