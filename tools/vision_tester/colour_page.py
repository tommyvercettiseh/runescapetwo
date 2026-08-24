from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog

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

from . import ui
from .colour_browser import (
    BLOB_MAX_LIMIT,
    BLOB_MIN_LIMIT,
    BrowserToleranceColourPage,
)
from .deep_zoom import ZoomImageView
from .enhanced_config import MAX_ZOOM_PERCENT, MIN_ZOOM_PERCENT, SAMPLE_SIZES
from .source_controls import SourceState
from .unified_plus import DEFAULT_TOLERANCE


class _HiddenImageView:
    """Keep the detector mask pipeline intact without rendering a third preview."""

    def show(self, _image) -> None:
        pass

    def set_view(self, *, auto_resize: bool, zoom_percent: int) -> None:
        pass


class ColourPage(BrowserToleranceColourPage):
    """Focused production colour workspace with one purpose-built layout."""

    def __init__(self, parent) -> None:
        self._deleted_colour_snapshot: dict[str, object] | None = None
        self._colour_trash_hide_job: str | None = None
        super().__init__(parent)

    # Layout -------------------------------------------------------------

    def _build(self) -> None:
        self.configure(fg_color=ui.BG)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0, minsize=220)
        self.grid_columnconfigure(1, weight=0, minsize=220)
        self.grid_columnconfigure(2, weight=1)

        self.source = SourceState(self, require_selection=True)
        self._build_colour_browser()
        self._build_area_browser()

        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.grid(
            row=0,
            column=2,
            sticky="nsew",
            padx=(0, 14),
            pady=10,
        )
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(3, weight=1)

        self._build_workspace_header(workspace)
        self._build_detection_panel(workspace)
        self._build_tolerance_panel(workspace)
        self._build_previews(workspace)
        self._build_status_bar(workspace)

        self._browser_ready = True
        self._draw_colour_browser()
        self._draw_area_browser()
        self._sync_zoom_state()

    def _build_workspace_header(self, parent) -> None:
        header = ui.card(parent)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.grid_columnconfigure(1, weight=1)

        ui.label(header, "SELECTED AREA", muted=True, size=10, bold=True).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(16, 10),
            pady=14,
        )
        selected = ui.label(
            header,
            "",
            textvariable=self.source.area,
            size=13,
            bold=True,
        )
        selected.grid(row=0, column=1, sticky="w", pady=14)

        ui.label(header, "BOT ID", muted=True, size=10, bold=True).grid(
            row=0,
            column=2,
            padx=(10, 7),
            pady=14,
        )
        ctk.CTkOptionMenu(
            header,
            values=["1", "2", "3", "4"],
            variable=self.source.bot_id,
            width=72,
            height=34,
            corner_radius=7,
            fg_color=ui.CARD_ALT,
            button_color=ui.BORDER,
            button_hover_color=ui.CONTROL_HOVER,
            text_color=ui.TEXT,
        ).grid(row=0, column=3, padx=(0, 20), pady=10)

        self.live_switch = ctk.CTkSwitch(
            header,
            text="Live",
            variable=self.live,
            command=self._toggle_live,
            progress_color=ui.ACCENT,
            button_color=ui.TEXT,
            button_hover_color=ui.ACCENT_HOVER,
            text_color=ui.TEXT,
        )
        self.live_switch.grid(row=0, column=4, padx=(0, 16), pady=10)

    def _build_detection_panel(self, parent) -> None:
        panel = ui.card(parent)
        panel.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(panel, fg_color="transparent")
        left.grid(row=0, column=0, sticky="ew", padx=16, pady=14)
        left.grid_columnconfigure(0, weight=1)
        left.grid_columnconfigure(1, weight=1)
        ui.label(left, "DETECTION RANGE (PX)", size=11, bold=True).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 10),
        )

        try:
            minimum = max(1, int(self.minimum.get() or 1))
        except ValueError:
            minimum = 20
        try:
            maximum = max(0, int(self.maximum.get() or 0))
        except ValueError:
            maximum = 0

        self.blob_min_slider_value = tk.DoubleVar(
            master=self,
            value=min(BLOB_MIN_LIMIT, minimum),
        )
        self.blob_max_slider_value = tk.DoubleVar(
            master=self,
            value=min(BLOB_MAX_LIMIT, maximum),
        )
        self.blob_min_slider_text = tk.StringVar(
            master=self,
            value=f"Min {minimum} px",
        )
        self.blob_max_slider_text = tk.StringVar(
            master=self,
            value="Max ∞" if maximum == 0 else f"Max {maximum} px",
        )

        self._build_blob_control(
            left,
            column=0,
            title="MIN",
            variable=self.minimum,
            slider_variable=self.blob_min_slider_value,
            from_=1,
            to=BLOB_MIN_LIMIT,
            command=self._blob_min_changed,
            entry_command=self._blob_min_entry_changed,
        )
        self._build_blob_control(
            left,
            column=1,
            title="MAX",
            variable=self.maximum,
            slider_variable=self.blob_max_slider_value,
            from_=0,
            to=BLOB_MAX_LIMIT,
            command=self._blob_max_changed,
            entry_command=self._blob_max_entry_changed,
        )

        right = ctk.CTkFrame(panel, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 16), pady=14)
        right.grid_columnconfigure(0, weight=1)
        ui.label(right, "LIVE BLOB", muted=True, size=10, bold=True).grid(
            row=0,
            column=0,
            sticky="w",
        )
        ui.label(
            right,
            "",
            textvariable=self.blob_live_text,
            text_color=ui.ACCENT,
            size=14,
            bold=True,
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))
        ui.label(
            right,
            "",
            textvariable=self.blob_range_text,
            muted=True,
            size=10,
        ).grid(row=2, column=0, sticky="w", pady=(4, 0))
        ui.button(
            right,
            "Reset observed",
            self._reset_blob_history,
            width=112,
        ).grid(row=1, column=1, rowspan=2, padx=(12, 0))

        self.blob_meter = ctk.CTkProgressBar(
            right,
            height=7,
            corner_radius=4,
            fg_color=ui.BORDER,
            progress_color=ui.ACCENT,
        )
        self.blob_meter.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(10, 0),
        )
        self.blob_meter.set(0)

    def _build_blob_control(
        self,
        parent,
        *,
        column: int,
        title: str,
        variable,
        slider_variable,
        from_: int,
        to: int,
        command,
        entry_command,
    ) -> None:
        group = ctk.CTkFrame(parent, fg_color="transparent")
        group.grid(
            row=1,
            column=column,
            sticky="ew",
            padx=(0, 14) if column == 0 else (8, 0),
        )
        group.grid_columnconfigure(1, weight=1)

        ui.label(group, title, muted=True, size=10, bold=True).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(0, 8),
        )
        entry = ctk.CTkEntry(
            group,
            textvariable=variable,
            width=72,
            height=32,
            corner_radius=7,
            fg_color=ui.CARD_ALT,
            border_color=ui.BORDER,
            text_color=ui.TEXT,
        )
        entry.grid(row=0, column=1, sticky="w")
        entry.bind("<KeyRelease>", entry_command)
        ui.label(group, "px", muted=True, size=10).grid(
            row=0,
            column=2,
            padx=(6, 0),
        )
        ctk.CTkSlider(
            group,
            from_=from_,
            to=to,
            variable=slider_variable,
            command=command,
            height=14,
            progress_color=ui.ACCENT,
            button_color=ui.ACCENT,
            button_hover_color=ui.ACCENT_HOVER,
            fg_color=ui.BORDER,
        ).grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(9, 0),
        )

    def _build_tolerance_panel(self, parent) -> None:
        panel = ui.card(parent)
        panel.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        panel.grid_columnconfigure(1, weight=1)

        ui.label(panel, "COLOUR TOLERANCE", size=11, bold=True).grid(
            row=0,
            column=0,
            sticky="w",
            padx=(16, 14),
            pady=(13, 4),
        )
        value = ctk.CTkLabel(
            panel,
            textvariable=self.tolerance_text,
            width=48,
            height=28,
            corner_radius=7,
            fg_color=ui.ACCENT_SOFT,
            text_color=ui.ACCENT_HOVER,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        value.grid(row=0, column=1, sticky="w", pady=(13, 4))

        actions = ctk.CTkFrame(panel, fg_color="transparent")
        actions.grid(row=0, column=2, rowspan=3, sticky="e", padx=14, pady=10)
        ui.button(
            actions,
            "↶  Remove last",
            self._remove_last_colour,
            width=112,
        ).pack(side="left")
        ui.button(
            actions,
            "Clear colours",
            self._clear_colours,
            width=108,
        ).pack(side="left", padx=(8, 0))

        self.tolerance_slider = ctk.CTkSlider(
            panel,
            from_=0,
            to=100,
            number_of_steps=100,
            variable=self.colour_tolerance,
            command=self._tolerance_changed,
            height=16,
            progress_color=ui.ACCENT,
            button_color=ui.ACCENT,
            button_hover_color=ui.ACCENT_HOVER,
            fg_color=ui.BORDER,
        )
        self.tolerance_slider.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=(16, 20),
            pady=(6, 0),
        )
        ui.label(
            panel,
            "Lower = stricter match   •   Higher = wider colour range",
            muted=True,
            size=10,
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            padx=16,
            pady=(7, 12),
        )

    def _build_previews(self, parent) -> None:
        previews = ctk.CTkFrame(parent, fg_color="transparent")
        previews.grid(row=3, column=0, sticky="nsew")
        previews.grid_rowconfigure(0, weight=1)
        previews.grid_columnconfigure(0, weight=1, uniform="preview")
        previews.grid_columnconfigure(1, weight=1, uniform="preview")

        live_card = ui.card(previews)
        live_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        live_card.grid_rowconfigure(2, weight=1)
        live_card.grid_columnconfigure(0, weight=1)

        live_header = ctk.CTkFrame(live_card, fg_color="transparent")
        live_header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 5))
        live_header.grid_columnconfigure(0, weight=1)
        ui.label(live_header, "LIVE AREA", size=12, bold=True).grid(
            row=0,
            column=0,
            sticky="w",
        )

        tools = ctk.CTkFrame(live_header, fg_color="transparent")
        tools.grid(row=0, column=1, sticky="e")
        self.pipette_button = ui.button(
            tools,
            "✦  Pipette",
            self._toggle_pipette,
            width=96,
        )
        self.pipette_button.pack(side="left")
        self.pipette_size_menu = ctk.CTkOptionMenu(
            tools,
            values=[str(value) for value in SAMPLE_SIZES],
            command=lambda value: self.pipette_sample_size.set(int(value)),
            width=58,
            height=38,
            corner_radius=7,
            fg_color=ui.CARD_ALT,
            button_color=ui.BORDER,
            button_hover_color=ui.CONTROL_HOVER,
            text_color=ui.TEXT,
        )
        self.pipette_size_menu.set(str(self.pipette_sample_size.get()))
        self.pipette_size_menu.pack(side="left", padx=(6, 0))
        self.move_colour_button = ui.button(
            tools,
            "◎  Move colour",
            lambda: self._start_colour_mouse_action(click=False),
            width=112,
        )
        self.move_colour_button.pack(side="left", padx=(6, 0))
        self.click_colour_button = ui.button(
            tools,
            "↖  Click colour",
            lambda: self._start_colour_mouse_action(click=True),
            width=112,
        )
        self.click_colour_button.pack(side="left", padx=(6, 0))

        ui.label(
            live_card,
            "Pick a colour here, then test move/click against the detected blob.",
            muted=True,
            size=10,
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 7))

        self.capture_view = ZoomImageView(
            live_card,
            auto_resize=self.auto_resize.get(),
            zoom_percent=self.zoom.get(),
        )
        self.capture_view.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=12,
            pady=(0, 8),
        )
        self.capture_view.bind("<Button-1>", self._pick)

        view_controls = ctk.CTkFrame(live_card, fg_color="transparent")
        view_controls.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 11))
        self.trace_switch = ctk.CTkCheckBox(
            view_controls,
            text="Trace",
            variable=self.mouse_trace,
            command=self._trace_changed,
            width=76,
            checkbox_width=18,
            checkbox_height=18,
            fg_color=ui.ACCENT,
            hover_color=ui.ACCENT_HOVER,
            border_color=ui.BORDER,
            text_color=ui.MUTED,
        )
        self.trace_switch.pack(side="left")
        self.auto_switch = ctk.CTkCheckBox(
            view_controls,
            text="Auto resize",
            variable=self.auto_resize,
            command=self._view_changed,
            width=104,
            checkbox_width=18,
            checkbox_height=18,
            fg_color=ui.ACCENT,
            hover_color=ui.ACCENT_HOVER,
            border_color=ui.BORDER,
            text_color=ui.MUTED,
        )
        self.auto_switch.pack(side="left", padx=(10, 0))

        self.zoom_label = ui.label(
            view_controls,
            f"Zoom {self.zoom.get()}%",
            muted=True,
            size=10,
        )
        self.zoom_label.pack(side="left", padx=(18, 7))
        self.zoom_slider = ctk.CTkSlider(
            view_controls,
            from_=MIN_ZOOM_PERCENT,
            to=MAX_ZOOM_PERCENT,
            variable=self.zoom,
            command=self._zoom_changed,
            width=130,
            height=14,
            progress_color=ui.ACCENT,
            button_color=ui.ACCENT,
            button_hover_color=ui.ACCENT_HOVER,
            fg_color=ui.BORDER,
        )
        self.zoom_slider.pack(side="left")

        isolated_card = ui.card(previews)
        isolated_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        isolated_card.grid_rowconfigure(2, weight=1)
        isolated_card.grid_columnconfigure(0, weight=1)
        ui.label(isolated_card, "ISOLATED COLOUR", size=12, bold=True).grid(
            row=0,
            column=0,
            sticky="w",
            padx=14,
            pady=(12, 5),
        )
        ui.label(
            isolated_card,
            "Only matching colour pixels remain.",
            muted=True,
            size=10,
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 7))
        self.isolated_view = ZoomImageView(
            isolated_card,
            auto_resize=self.auto_resize.get(),
            zoom_percent=self.zoom.get(),
        )
        self.isolated_view.grid(
            row=2,
            column=0,
            sticky="nsew",
            padx=12,
            pady=(0, 12),
        )

        self.mask_view = _HiddenImageView()
        self.views = [self.capture_view, self.mask_view, self.isolated_view]

    def _build_status_bar(self, parent) -> None:
        bar = ui.card(parent)
        bar.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        bar.grid_columnconfigure(1, weight=1)
        ui.label(
            bar,
            "",
            textvariable=self.colour_count_text,
            muted=True,
            size=10,
            bold=True,
        ).grid(row=0, column=0, sticky="w", padx=(14, 12), pady=9)
        ui.label(
            bar,
            "",
            textvariable=self.status,
            muted=True,
            size=10,
        ).grid(row=0, column=1, sticky="w", pady=9)

    def _blob_min_entry_changed(self, _event=None) -> None:
        try:
            value = max(1, min(BLOB_MIN_LIMIT, int(self.minimum.get())))
        except ValueError:
            return
        self.blob_min_slider_value.set(value)
        self.blob_min_slider_text.set(f"Min {value} px")
        self._schedule_blob_render()

    def _blob_max_entry_changed(self, _event=None) -> None:
        try:
            value = max(0, min(BLOB_MAX_LIMIT, int(self.maximum.get())))
        except ValueError:
            return
        self.blob_max_slider_value.set(value)
        self.blob_max_slider_text.set("Max ∞" if value == 0 else f"Max {value} px")
        self._schedule_blob_render()

    # Browsers ----------------------------------------------------------

    def _build_colour_browser(self) -> None:
        sidebar = ui.card(self, width=220)
        sidebar.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(14, 5),
            pady=10,
        )
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(4, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        ui.label(sidebar, "COLOURS", size=12, bold=True).grid(
            row=0,
            column=0,
            sticky="w",
            padx=14,
            pady=(14, 8),
        )
        search = ctk.CTkEntry(
            sidebar,
            textvariable=self.colour_filter,
            placeholder_text="Search colours...",
            height=36,
            corner_radius=8,
            fg_color=ui.CARD_ALT,
            border_color=ui.BORDER,
            text_color=ui.TEXT,
        )
        search.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        search.bind("<KeyRelease>", self._colour_filter_changed)
        search.bind("<Escape>", self._clear_colour_filter)

        self.new_colour_button = ui.button(
            sidebar,
            "+  Add new colour",
            self._new_colour_from_browser,
            primary=True,
            width=190,
        )
        self.new_colour_button.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 8))

        self.save_colour_button = ui.button(
            sidebar,
            "Save updated colour",
            self._save_colour_from_browser,
            width=190,
        )
        self.save_colour_button.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 8))

        self.colour_scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            scrollbar_button_color=ui.BORDER,
            scrollbar_button_hover_color=ui.ACCENT_HOVER,
        )
        self.colour_scroll.grid(row=4, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.colour_scroll.grid_columnconfigure(0, weight=1)

        ui.label(
            sidebar,
            "Click = one colour  •  Ctrl+click = multiple",
            muted=True,
            size=9,
            wraplength=188,
            justify="left",
        ).grid(row=5, column=0, sticky="w", padx=14, pady=(0, 10))

        self.colour_undo_button = ui.button(
            sidebar,
            "Undo delete",
            self._undo_deleted_colour,
            width=190,
        )
        self.colour_undo_button.grid(row=6, column=0, sticky="ew", padx=14, pady=(0, 12))
        self.colour_undo_button.grid_remove()

    def _build_area_browser(self) -> None:
        sidebar = ui.card(self, width=220)
        sidebar.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=5,
            pady=10,
        )
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(2, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        ui.label(sidebar, "AREAS", size=12, bold=True).grid(
            row=0,
            column=0,
            sticky="w",
            padx=14,
            pady=(14, 8),
        )
        search = ctk.CTkEntry(
            sidebar,
            textvariable=self.area_filter,
            placeholder_text="Search areas...",
            height=36,
            corner_radius=8,
            fg_color=ui.CARD_ALT,
            border_color=ui.BORDER,
            text_color=ui.TEXT,
        )
        search.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))
        search.bind("<KeyRelease>", self._area_filter_changed)
        search.bind("<Escape>", self._clear_area_filter)

        self.area_scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            scrollbar_button_color=ui.BORDER,
            scrollbar_button_hover_color=ui.ACCENT_HOVER,
        )
        self.area_scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.area_scroll.grid_columnconfigure(0, weight=1)

        ui.label(
            sidebar,
            "Select an area to start the live preview.",
            muted=True,
            size=9,
            wraplength=188,
            justify="left",
        ).grid(row=3, column=0, sticky="w", padx=14, pady=(0, 12))

    # Colour editing -----------------------------------------------------

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
                fg_color=ui.ACCENT_SOFT if selected else "transparent",
                hover_color=ui.ACCENT_SOFT,
                text_color=ui.ACCENT_HOVER if selected else ui.TEXT,
            )
            main.pack(side="left", fill="x", expand=True)
            main.configure(command=lambda: None)
            main.bind(
                "<Button-1>",
                lambda event, value=name: self._colour_clicked(event, value),
            )

            trash = ctk.CTkButton(
                row,
                text="×",
                width=30,
                height=30,
                corner_radius=7,
                fg_color="transparent",
                hover_color=ui.ACCENT_SOFT,
                text_color=ui.MUTED,
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


__all__ = ["ColourPage"]
