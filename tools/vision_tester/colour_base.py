from __future__ import annotations

from queue import Empty, SimpleQueue
import threading
import time
import tkinter as tk

import customtkinter as ctk
import cv2
import numpy as np

from core import mouse
from core.targeting import (
    colour_blob_target_bounds,
    randomized_target_bounds,
)
from core.vision.colour_analysis import (
    BlobMeasurement,
    filter_mask_by_blob_size,
    isolate_colour,
    measure_mask_blobs,
)
from core.vision.colour_detection import (
    blobs_from_mask,
    build_mask_from_ranges,
    count_mask_pixels,
    hsv_ranges_around,
    sample_hsv,
)
from core.vision.models import ColourBlob
from core.vision.screenshots import capture_area

from . import ui
from .mouse_trace import MouseTraceOverlay
from .preferences import load_preferences, save_preferences


BLOB_BOX_PADDING = 8


class ColourBasePage(ctk.CTkFrame):
    """Shared live colour capture, rendering and mouse-test behaviour."""

    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color="transparent")
        preferences = load_preferences()
        self.live = tk.BooleanVar(value=False)
        self.pipette = False
        self.minimum = tk.StringVar(value="20")
        self.maximum = tk.StringVar(value="0")
        self.auto_resize = tk.BooleanVar(value=bool(preferences["auto_resize"]))
        self.zoom = tk.IntVar(value=int(preferences["zoom_percent"]))
        self.mouse_trace = tk.BooleanVar(value=bool(preferences["mouse_trace"]))
        self.status = tk.StringVar(value="Kies een area en maak een capture.")
        self.blob_live_text = tk.StringVar(value="— PX")
        self.blob_range_text = tk.StringVar(value="MIN —   MAX —")
        self.capture: np.ndarray | None = None
        self.capture_region = (0, 0, 0, 0)
        self.ranges = ()
        self.current_target_blob: ColourBlob | None = None
        self.current_blob_px = 0
        self.observed_min_px: int | None = None
        self.observed_max_px: int | None = None
        self.views: list[ui.ImageView] = []
        self._save_job: str | None = None
        self._mouse_action_running = False
        self._mouse_results: SimpleQueue[tuple[bool, str]] = SimpleQueue()
        self._trace_overlay: MouseTraceOverlay | None = None
        self._resume_live_after_mouse = False
        self._tester_window_state = "normal"
        self._build()
        self.after(100, self._tick)

    def activate(self) -> None:
        self.live.set(True)
        self.status.set("Live capture actief.")
        self.after_idle(self._capture)

    def deactivate(self) -> None:
        self.live.set(False)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        toolbar = ui.card(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 10))
        toolbar.grid_columnconfigure(0, weight=1)
        self.source = ui.SourceControls(toolbar)
        self.source.grid(row=0, column=0, sticky="ew", padx=16, pady=14)

        actions = ctk.CTkFrame(toolbar, fg_color="transparent")
        actions.grid(row=0, column=1, padx=(0, 16), pady=14)
        ctk.CTkSwitch(
            actions,
            text="Live",
            variable=self.live,
            command=self._toggle_live,
            progress_color=ui.ACCENT,
            button_color=ui.TEXT,
            button_hover_color=ui.GOLD,
            text_color=ui.TEXT,
        ).grid(row=0, column=0, padx=(0, 10))
        ui.button(
            actions,
            "Capture",
            self._once,
            primary=True,
            width=105,
        ).grid(row=0, column=1)

        viewbar = ui.card(self)
        viewbar.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        viewbar.grid_columnconfigure(1, weight=1)

        limits = ctk.CTkFrame(viewbar, fg_color="transparent")
        limits.grid(row=0, column=0, padx=(14, 18), pady=10, sticky="w")
        for column, (title, variable) in enumerate(
            (("MIN BLOB PX", self.minimum), ("MAX BLOB PX", self.maximum))
        ):
            group = ctk.CTkFrame(limits, fg_color="transparent")
            group.grid(row=0, column=column, padx=(0, 8))
            ui.label(group, title, muted=True, size=10).pack(anchor="w")
            entry = ctk.CTkEntry(
                group,
                textvariable=variable,
                width=94,
                height=32,
                corner_radius=7,
                fg_color=ui.CARD_ALT,
                border_color=ui.BORDER,
                text_color=ui.TEXT,
            )
            entry.pack(pady=(2, 0))
            entry.bind("<KeyRelease>", lambda _event: self._render())

        tracker = ctk.CTkFrame(viewbar, fg_color="transparent")
        tracker.grid(row=0, column=1, sticky="ew", padx=(0, 18), pady=9)
        tracker.grid_columnconfigure(1, weight=1)
        ui.label(tracker, "LIVE BLOB", muted=True, size=10).grid(
            row=0,
            column=0,
            sticky="w",
        )
        ui.label(
            tracker,
            "",
            textvariable=self.blob_live_text,
            text_color=ui.ACCENT,
            size=13,
            bold=True,
        ).grid(row=0, column=1, sticky="w", padx=(8, 14))
        ui.label(
            tracker,
            "",
            textvariable=self.blob_range_text,
            muted=True,
            size=10,
        ).grid(row=0, column=2, sticky="e", padx=(0, 10))
        ui.button(
            tracker,
            "Reset",
            self._reset_blob_history,
            width=68,
        ).grid(row=0, column=3, rowspan=2)
        self.blob_meter = ctk.CTkProgressBar(
            tracker,
            height=8,
            corner_radius=4,
            fg_color=ui.BORDER,
            progress_color=ui.ACCENT,
        )
        self.blob_meter.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(6, 0),
            padx=(0, 10),
        )
        self.blob_meter.set(0)

        display = ctk.CTkFrame(viewbar, fg_color="transparent")
        display.grid(row=0, column=2, padx=(0, 14), pady=10, sticky="e")
        ui.label(display, "WEERGAVE", muted=True, size=10).grid(
            row=0,
            column=0,
            sticky="w",
        )
        self.auto_switch = ctk.CTkSwitch(
            display,
            text="Auto resize",
            variable=self.auto_resize,
            command=self._view_changed,
            progress_color=ui.ACCENT,
            text_color=ui.TEXT,
        )
        self.auto_switch.grid(row=1, column=0, padx=(0, 12), pady=(3, 0))
        self.zoom_label = ui.label(
            display,
            f"Zoom {self.zoom.get()}%",
            size=10,
            bold=True,
        )
        self.zoom_label.grid(row=1, column=1, padx=(0, 7), pady=(3, 0))
        self.zoom_slider = ctk.CTkSlider(
            display,
            from_=10,
            to=100,
            number_of_steps=90,
            variable=self.zoom,
            command=self._zoom_changed,
            width=150,
            progress_color=ui.ACCENT,
            button_color=ui.ACCENT,
            button_hover_color=ui.ACCENT_HOVER,
            fg_color=ui.BORDER,
        )
        self.zoom_slider.grid(row=1, column=2, pady=(3, 0))
        self._sync_zoom_state()

        previews = ctk.CTkFrame(self, fg_color="transparent")
        previews.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 10))
        previews.grid_rowconfigure(0, weight=1)
        for column in range(3):
            previews.grid_columnconfigure(column, weight=1, uniform="preview")
        specs = (
            ("LIVE AREA", "Klik met het pipet om een kleur te kiezen"),
            ("BINAIR MASKER", "Alleen geldige blobs zijn wit"),
            ("KLEUR GEÏSOLEERD", "Alleen geldige kleurpixels blijven staan"),
        )
        for column, (title, subtitle) in enumerate(specs):
            card = ui.card(previews)
            card.grid(row=0, column=column, sticky="nsew", padx=4)
            heading = ctk.CTkFrame(card, fg_color="transparent")
            heading.pack(fill="x", padx=14, pady=(10, 0))
            ui.label(heading, title, size=12, bold=True).pack(side="left")
            if column == 0:
                mousebar = ctk.CTkFrame(card, fg_color="transparent")
                mousebar.pack(fill="x", padx=14, pady=(7, 5))
                self.pipette_button = ui.button(
                    mousebar,
                    "⌖  Pipet",
                    self._toggle_pipette,
                    width=80,
                )
                self.pipette_button.pack(side="left")
                self.move_colour_button = ui.button(
                    mousebar,
                    "Move kleur",
                    lambda: self._start_colour_mouse_action(click=False),
                    width=84,
                )
                self.move_colour_button.pack(side="left", padx=(7, 0))
                self.click_colour_button = ui.button(
                    mousebar,
                    "Klik kleur",
                    lambda: self._start_colour_mouse_action(click=True),
                    primary=True,
                    width=84,
                )
                self.click_colour_button.pack(side="left", padx=(7, 0))
                self.trace_switch = ctk.CTkSwitch(
                    mousebar,
                    text="Trace",
                    variable=self.mouse_trace,
                    command=self._trace_changed,
                    width=88,
                    progress_color=ui.ACCENT,
                    button_color=ui.TEXT,
                    button_hover_color=ui.GOLD,
                    text_color=ui.MUTED,
                )
                self.trace_switch.pack(side="right")
            else:
                spacer = ctk.CTkFrame(card, fg_color="transparent", height=38)
                spacer.pack(fill="x", padx=14, pady=(7, 5))
                spacer.pack_propagate(False)
            ui.label(card, subtitle, muted=True, size=11).pack(
                anchor="w",
                padx=14,
                pady=(0, 8),
            )
            view = ui.ImageView(
                card,
                auto_resize=self.auto_resize.get(),
                zoom_percent=self.zoom.get(),
            )
            view.pack(fill="both", expand=True, padx=12, pady=(0, 12))
            self.views.append(view)
        self.capture_view, self.mask_view, self.isolated_view = self.views
        self.capture_view.bind("<Button-1>", self._pick)

        status = ui.card(self)
        status.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 12))
        ui.label(status, "", size=11, textvariable=self.status).pack(
            anchor="w",
            padx=14,
            pady=9,
        )

    def _toggle_live(self) -> None:
        self.status.set(
            "Live capture actief." if self.live.get() else "Live capture gepauzeerd."
        )

    def _once(self) -> None:
        self.live.set(False)
        self._capture()

    def capture_hotkey(self) -> None:
        self._once()

    def _tick(self) -> None:
        if self.live.get():
            self._capture()
        self.after(100, self._tick)

    def _capture(self) -> None:
        started = time.perf_counter()
        try:
            self.capture, self.capture_region = capture_area(
                self.source.area.get(),
                bot_id=self.source.bot(),
            )
            self._render(started)
        except Exception as exc:
            self.live.set(False)
            self.current_target_blob = None
            self.status.set(f"Fout: {exc}")

    def _limits(self) -> tuple[int, int | None]:
        minimum = max(1, int(self.minimum.get() or 1))
        maximum = int(self.maximum.get() or 0)
        return minimum, maximum or None

    def _render(self, started: float | None = None) -> None:
        self.current_target_blob = None
        if self.capture is None:
            return
        try:
            minimum, maximum = self._limits()
        except ValueError:
            return
        if not self.ranges:
            self.capture_view.show(self.capture)
            blank = np.zeros(self.capture.shape[:2], dtype=np.uint8)
            self.mask_view.show(cv2.cvtColor(blank, cv2.COLOR_GRAY2RGB))
            self.isolated_view.show(np.zeros_like(self.capture))
            return

        started = time.perf_counter() if started is None else started
        raw_mask = build_mask_from_ranges(self.capture, self.ranges)
        blobs = measure_mask_blobs(raw_mask)
        dominant_blob = blobs[0] if blobs else None
        self._observe_blob(dominant_blob)
        mask, blob_count = filter_mask_by_blob_size(
            raw_mask,
            minimum_area_px=minimum,
            maximum_area_px=maximum,
        )
        valid_blobs = blobs_from_mask(
            mask,
            origin=(self.capture_region[0], self.capture_region[1]),
            minimum_area_px=1,
        )
        self.current_target_blob = valid_blobs[0] if valid_blobs else None

        if self.current_target_blob is None:
            visible_target = None
            visible_safe_bounds = None
        else:
            visible_target = BlobMeasurement(
                x=self.current_target_blob.x - self.capture_region[0],
                y=self.current_target_blob.y - self.capture_region[1],
                width=self.current_target_blob.width,
                height=self.current_target_blob.height,
                area_px=self.current_target_blob.area_px,
            )
            try:
                safe_bounds = colour_blob_target_bounds(
                    self.current_target_blob,
                    blob_edge_padding=20,
                )
                visible_safe_bounds = (
                    safe_bounds[0] - self.capture_region[0],
                    safe_bounds[1] - self.capture_region[1],
                    safe_bounds[2] - self.capture_region[0],
                    safe_bounds[3] - self.capture_region[1],
                )
            except ValueError:
                visible_safe_bounds = None

        self.capture_view.show(
            self._draw_blob_overlay(visible_target, visible_safe_bounds)
        )
        pixels = count_mask_pixels(mask)
        self.mask_view.show(cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB))
        self.isolated_view.show(isolate_colour(self.capture, mask))
        elapsed = (time.perf_counter() - started) * 1000
        self.status.set(
            f"Bot {self.source.bot()}  •  {self.source.area.get()}  •  "
            f"{pixels} px  •  {blob_count} geldige blobs  •  {elapsed:.1f} ms"
        )

    def _observe_blob(self, blob: BlobMeasurement | None) -> None:
        if blob is None:
            self.current_blob_px = 0
            self.blob_live_text.set("— PX")
            self.blob_meter.set(0)
            return

        pixels = blob.area_px
        self.current_blob_px = pixels
        self.observed_min_px = (
            pixels
            if self.observed_min_px is None
            else min(self.observed_min_px, pixels)
        )
        self.observed_max_px = (
            pixels
            if self.observed_max_px is None
            else max(self.observed_max_px, pixels)
        )
        self.blob_live_text.set(f"{ui.format_pixels(pixels)} PX")
        self.blob_range_text.set(
            f"MIN {ui.format_pixels(self.observed_min_px)}   "
            f"MAX {ui.format_pixels(self.observed_max_px)}"
        )
        span = self.observed_max_px - self.observed_min_px
        position = (
            0.5
            if span == 0
            else (pixels - self.observed_min_px) / span
        )
        self.blob_meter.set(position)

    def _reset_blob_history(self) -> None:
        current = self.current_blob_px or None
        self.observed_min_px = current
        self.observed_max_px = current
        if current is None:
            self.blob_range_text.set("MIN —   MAX —")
            self.blob_meter.set(0)
        else:
            formatted = ui.format_pixels(current)
            self.blob_range_text.set(f"MIN {formatted}   MAX {formatted}")
            self.blob_meter.set(0.5)

    def _draw_blob_overlay(
        self,
        blob: BlobMeasurement | None,
        safe_bounds: tuple[int, int, int, int] | None = None,
    ) -> np.ndarray:
        visual = self.capture.copy()
        if blob is None:
            return visual
        height, width = visual.shape[:2]
        left = max(0, blob.x - BLOB_BOX_PADDING)
        top = max(0, blob.y - BLOB_BOX_PADDING)
        right = min(width - 1, blob.x + blob.width - 1 + BLOB_BOX_PADDING)
        bottom = min(height - 1, blob.y + blob.height - 1 + BLOB_BOX_PADDING)
        cv2.rectangle(visual, (left, top), (right, bottom), (142, 198, 63), 2)
        if safe_bounds is not None:
            safe_left, safe_top, safe_right, safe_bottom = safe_bounds
            cv2.rectangle(
                visual,
                (max(0, safe_left), max(0, safe_top)),
                (
                    min(width - 1, safe_right - 1),
                    min(height - 1, safe_bottom - 1),
                ),
                (209, 166, 75),
                2,
            )
        label = f"{ui.format_pixels(blob.area_px)} PX"
        label_above = top >= 24
        label_top = top - 22 if label_above else top
        label_bottom = top if label_above else min(height - 1, top + 22)
        text_y = top - 6 if label_above else min(height - 5, top + 16)
        label_width = max(78, len(label) * 8)
        cv2.rectangle(
            visual,
            (left, label_top),
            (min(width - 1, left + label_width), label_bottom),
            (23, 19, 13),
            -1,
        )
        cv2.putText(
            visual,
            label,
            (left + 5, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (142, 198, 63),
            1,
            cv2.LINE_AA,
        )
        return visual

    def _toggle_pipette(self) -> None:
        self.pipette = not self.pipette
        self.pipette_button.configure(
            fg_color=ui.ACCENT_SOFT if self.pipette else ui.CARD_ALT,
            text_color=ui.ACCENT_HOVER if self.pipette else ui.TEXT,
        )
        self.capture_view.configure(cursor="crosshair" if self.pipette else "")
        self.status.set(
            "Pipet actief. Klik in Live Area."
            if self.pipette
            else "Pipet uitgeschakeld."
        )

    def _pick(self, event) -> None:
        if self.capture is None or not self.pipette:
            return
        point = self.capture_view.image_coordinates(event.x, event.y)
        if point is None:
            return
        x, y = point
        self.ranges = hsv_ranges_around(
            sample_hsv(self.capture, x, y, radius=2),
            hue_tolerance=5,
            saturation_tolerance=40,
            value_tolerance=40,
        )
        self.current_blob_px = 0
        self.observed_min_px = None
        self.observed_max_px = None
        self.blob_range_text.set("MIN —   MAX —")
        self._render()

    def _start_colour_mouse_action(self, *, click: bool) -> None:
        if self._mouse_action_running:
            self.status.set("Er loopt al een muisactie.")
            return
        if not self.ranges:
            self.status.set("Kies eerst een kleur met het pipet.")
            return

        self._resume_live_after_mouse = self.live.get()
        self.live.set(False)
        self._capture()
        blob = self.current_target_blob
        if blob is None:
            self.live.set(self._resume_live_after_mouse)
            self.status.set("Geen geldige kleurblob binnen MIN/MAX BLOB PX.")
            return
        try:
            bounds = randomized_target_bounds(
                colour_blob_target_bounds(blob, blob_edge_padding=20)
            )
        except ValueError as exc:
            self.live.set(self._resume_live_after_mouse)
            self.status.set(f"Geen veilige clickzone: {exc}")
            return

        self._mouse_action_running = True
        self.move_colour_button.configure(state="disabled")
        self.click_colour_button.configure(state="disabled")
        root = self.winfo_toplevel()
        self._tester_window_state = root.state()
        trace_warning = ""
        if self.mouse_trace.get():
            try:
                self._trace_overlay = MouseTraceOverlay(
                    root,
                    cursor_position=mouse.position,
                    target_bounds=bounds,
                )
            except Exception as exc:
                self._trace_overlay = None
                trace_warning = f" Trace niet beschikbaar: {exc}"

        action_name = "Klik kleur" if click else "Move kleur"
        self.status.set(
            f"{action_name} start voor blob van {ui.format_pixels(blob.area_px)} PX."
            f"{trace_warning}"
        )
        root.withdraw()
        self.after(
            140,
            lambda: self._launch_colour_mouse_worker(
                click=click,
                bounds=bounds,
                blob_pixels=blob.area_px,
            ),
        )

    def _launch_colour_mouse_worker(
        self,
        *,
        click: bool,
        bounds: tuple[int, int, int, int],
        blob_pixels: int,
    ) -> None:
        def run() -> None:
            action_name = "Klik kleur" if click else "Move kleur"
            try:
                if click:
                    mouse.move_and_click_target(
                        *bounds,
                        button="left",
                        require_external=True,
                    )
                else:
                    mouse.move_to_target(
                        *bounds,
                        require_external=True,
                        keep_pending_click=False,
                    )
                engine = mouse.last_execution_status().engine
                self._mouse_results.put(
                    (
                        True,
                        f"{action_name} gelukt via {engine} op "
                        f"{ui.format_pixels(blob_pixels)} PX blob.",
                    )
                )
            except Exception as exc:
                self._mouse_results.put(
                    (False, f"{action_name} mislukt: {exc}")
                )

        threading.Thread(
            target=run,
            name="vision-colour-mouse-test",
            daemon=True,
        ).start()
        self.after(25, self._poll_colour_mouse_worker)

    def _poll_colour_mouse_worker(self) -> None:
        try:
            _success, message = self._mouse_results.get_nowait()
        except Empty:
            self.after(25, self._poll_colour_mouse_worker)
            return

        if self._trace_overlay is not None:
            self._trace_overlay.finish()
            restore_delay = 950
        else:
            restore_delay = 0
        self.after(
            restore_delay,
            lambda: self._restore_after_mouse_action(message),
        )

    def _restore_after_mouse_action(self, message: str) -> None:
        root = self.winfo_toplevel()
        root.deiconify()
        try:
            if self._tester_window_state == "zoomed":
                root.state("zoomed")
        except tk.TclError:
            pass
        root.lift()
        self._trace_overlay = None
        self._mouse_action_running = False
        self.move_colour_button.configure(state="normal")
        self.click_colour_button.configure(state="normal")
        self.status.set(message)
        self.live.set(self._resume_live_after_mouse)
        if self.live.get():
            self.after(120, self._capture)

    def _view_changed(self) -> None:
        self._sync_zoom_state()
        self._apply_view()

    def _zoom_changed(self, value) -> None:
        self.zoom.set(round(float(value)))
        self.zoom_label.configure(text=f"Zoom {self.zoom.get()}%")
        if not self.auto_resize.get():
            self._apply_view()

    def _sync_zoom_state(self) -> None:
        self.zoom_slider.configure(
            state="disabled" if self.auto_resize.get() else "normal"
        )

    def _apply_view(self) -> None:
        for view in self.views:
            view.set_view(
                auto_resize=self.auto_resize.get(),
                zoom_percent=self.zoom.get(),
            )
        if self._save_job is not None:
            self.after_cancel(self._save_job)
        self._save_job = self.after(180, self._save_preferences)

    def _trace_changed(self) -> None:
        if self._save_job is not None:
            self.after_cancel(self._save_job)
        self._save_job = self.after(180, self._save_preferences)
        self.status.set(
            "Fading trace staat aan voor testbewegingen."
            if self.mouse_trace.get()
            else "Fading trace staat uit."
        )

    def _save_preferences(self) -> None:
        self._save_job = None
        try:
            save_preferences(
                {
                    "auto_resize": self.auto_resize.get(),
                    "zoom_percent": self.zoom.get(),
                    "mouse_trace": self.mouse_trace.get(),
                }
            )
        except OSError:
            pass


__all__ = ["ColourBasePage"]
