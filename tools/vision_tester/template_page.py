from __future__ import annotations

from pathlib import Path
import time
import tkinter as tk
from tkinter import messagebox, simpledialog

import customtkinter as ctk
import cv2
import numpy as np

from core import mouse
from core.targeting import (
    MIN_IMAGE_EDGE_PADDING,
    image_target_bounds,
    normalize_image_edge_padding,
)
from core.vision.screenshots import capture_area
from core.vision.template_analysis import analyse_template
from core.vision.template_matching import available_methods
from core.vision.templates import (
    IMAGES_DIR,
    delete_template,
    load_settings,
    load_template,
    rename_template,
    save_settings,
)
from core.vision.models import TemplateSettings

from . import ui
from .template_capture import TemplateCaptureOverlay


class TemplatePage(ctk.CTkFrame):
    """Live template calibration page backed by the canonical vision analysis."""

    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color="transparent")
        self.live = tk.BooleanVar(value=False)
        self.query = tk.StringVar()
        self.selected: str | None = None
        self.method = tk.StringVar(value="TM_CCOEFF_NORMED")
        self.shape = tk.DoubleVar(value=85.0)
        self.colour = tk.DoubleVar(value=60.0)
        self.maximum = tk.StringVar(value="30")
        self.x_padding = tk.StringVar(value="20")
        self.status = tk.StringVar(
            value="Selecteer een template of maak een nieuwe screenshot."
        )
        self.templates: list[str] = []
        self.rows: dict[str, ctk.CTkButton] = {}
        self.screenshot: np.ndarray | None = None
        self.region: tuple[int, int, int, int] | None = None
        self.best_valid_bounds: tuple[int, int, int, int] | None = None
        self._job: str | None = None
        self._build()
        self.after(100, self._tick)

    def activate(self) -> None:
        self.live.set(True)
        self.status.set("Live matching actief.")
        self.after_idle(self._capture)

    def deactivate(self) -> None:
        self.live.set(False)

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        toolbar = ui.card(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 10))
        toolbar.grid_columnconfigure(0, weight=1)
        self.source = ui.SourceControls(toolbar)
        self.source.grid(row=0, column=0, sticky="ew", padx=16, pady=14)

        actions = ctk.CTkFrame(toolbar, fg_color="transparent")
        actions.grid(row=0, column=1, padx=16, pady=14)
        ui.button(
            actions,
            "Nieuwe template",
            self._new_template,
            width=150,
        ).grid(row=0, column=0, padx=(0, 10))
        ctk.CTkSwitch(
            actions,
            text="Live",
            variable=self.live,
            command=self._toggle_live,
            progress_color=ui.ACCENT,
            text_color=ui.TEXT,
        ).grid(row=0, column=1, padx=(0, 12))
        ui.button(
            actions,
            "Capture",
            self._once,
            primary=True,
            width=105,
        ).grid(row=0, column=2)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(1, weight=1)

        sidebar = ui.card(content, width=270)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(2, weight=1)
        ui.label(sidebar, "TEMPLATES", size=12, bold=True).grid(
            row=0,
            column=0,
            sticky="w",
            padx=14,
            pady=(14, 8),
        )
        search = ctk.CTkEntry(
            sidebar,
            textvariable=self.query,
            placeholder_text="Zoek template",
            height=38,
            corner_radius=8,
            fg_color=ui.CARD_ALT,
            border_color=ui.BORDER,
            text_color=ui.TEXT,
        )
        search.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 10))
        search.bind("<KeyRelease>", lambda _event: self._draw_templates())
        self.template_scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            scrollbar_button_color=ui.BORDER,
            scrollbar_button_hover_color=ui.GOLD,
        )
        self.template_scroll.grid(row=2, column=0, sticky="nsew", padx=8)
        self.template_scroll.grid_columnconfigure(0, weight=1)

        template_actions = ctk.CTkFrame(sidebar, fg_color="transparent")
        template_actions.grid(row=3, column=0, sticky="ew", padx=14, pady=12)
        template_actions.grid_columnconfigure(0, weight=1)
        template_actions.grid_columnconfigure(1, weight=1)
        ui.button(
            template_actions,
            "Hernoem",
            self._rename,
            width=108,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ui.button(
            template_actions,
            "Verwijder",
            self._delete,
            danger=True,
            width=108,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        center = ui.card(content)
        center.grid(row=0, column=1, sticky="nsew", padx=(0, 8))
        center.grid_rowconfigure(2, weight=1)
        center.grid_columnconfigure(0, weight=1)
        ui.label(center, "LIVE AREA", size=12, bold=True).grid(
            row=0,
            column=0,
            sticky="w",
            padx=14,
            pady=(14, 0),
        )
        target_actions = ctk.CTkFrame(center, fg_color="transparent")
        target_actions.grid(row=0, column=0, sticky="e", padx=14, pady=(8, 0))
        ui.label(target_actions, "X PADDING ≥", muted=True, size=10).grid(
            row=0,
            column=0,
            padx=(0, 5),
        )
        x_padding_entry = ctk.CTkEntry(
            target_actions,
            textvariable=self.x_padding,
            width=48,
            height=34,
            corner_radius=7,
            fg_color=ui.CARD_ALT,
            border_color=ui.BORDER,
            text_color=ui.TEXT,
        )
        x_padding_entry.grid(row=0, column=1, padx=(0, 4))
        x_padding_entry.bind("<KeyRelease>", lambda _event: self._schedule())
        ui.label(target_actions, "%", muted=True, size=10).grid(
            row=0,
            column=2,
            padx=(0, 8),
        )
        ui.button(
            target_actions,
            "Muis naar image",
            self._move_to_image,
            width=150,
        ).grid(row=0, column=3)
        ui.label(
            center,
            "Groen geldig · rood faalt · goud is de veilige muiszone",
            muted=True,
            size=11,
        ).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 10))

        self.preview = ui.ImageView(center)
        self.preview.grid(row=2, column=0, sticky="nsew", padx=12)
        self.results = ctk.CTkTextbox(
            center,
            height=118,
            corner_radius=8,
            fg_color=ui.CARD_ALT,
            border_color=ui.BORDER,
            border_width=1,
            text_color=ui.TEXT,
            font=ctk.CTkFont(family="Consolas", size=11),
        )
        self.results.grid(row=3, column=0, sticky="ew", padx=12, pady=12)
        self.results.insert("1.0", "Nog geen analyse uitgevoerd.")
        self.results.configure(state="disabled")

        panel = ui.card(content, width=320)
        panel.grid(row=0, column=2, sticky="nsew")
        panel.grid_propagate(False)
        ui.label(panel, "DETECTIE INSTELLEN", size=12, bold=True).pack(
            anchor="w",
            padx=16,
            pady=(14, 0),
        )
        ui.label(
            panel,
            "Wijzig live en sla op voor productie.",
            muted=True,
            size=11,
        ).pack(anchor="w", padx=16, pady=(0, 18))
        ui.label(panel, "METHODE", muted=True, size=11).pack(anchor="w", padx=16)
        self.method_box = ctk.CTkOptionMenu(
            panel,
            values=list(available_methods()),
            variable=self.method,
            command=lambda _value: self._schedule(),
            height=38,
            corner_radius=8,
            fg_color=ui.CARD_ALT,
            button_color=ui.BORDER,
            button_hover_color=ui.CONTROL_HOVER,
            text_color=ui.TEXT,
        )
        self.method_box.pack(fill="x", padx=16, pady=(4, 18))
        self.shape_label, self.shape_slider = self._slider(
            panel,
            "SHAPE THRESHOLD",
            self.shape,
            self._threshold_changed,
        )
        self.colour_label, self.colour_slider = self._slider(
            panel,
            "COLOUR THRESHOLD",
            self.colour,
            self._threshold_changed,
        )
        ui.label(panel, "MAX HITS", muted=True, size=11).pack(anchor="w", padx=16)
        max_entry = ctk.CTkEntry(
            panel,
            textvariable=self.maximum,
            width=100,
            height=38,
            corner_radius=8,
            fg_color=ui.CARD_ALT,
            border_color=ui.BORDER,
            text_color=ui.TEXT,
        )
        max_entry.pack(anchor="w", padx=16, pady=(4, 18))
        max_entry.bind("<KeyRelease>", lambda _event: self._schedule())
        ui.button(
            panel,
            "Instellingen opslaan",
            self._save,
            primary=True,
            width=288,
        ).pack(padx=16, fill="x")
        self.summary = ui.label(
            panel,
            "Beste shape —\nKleur daarbij —\nGeldige hits —",
            muted=True,
            size=12,
            justify="left",
        )
        self.summary.pack(anchor="w", padx=16, pady=(20, 0))

        status = ui.card(self)
        status.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        ui.label(
            status,
            "",
            textvariable=self.status,
            muted=True,
            size=11,
        ).pack(anchor="w", padx=14, pady=9)
        self._refresh_templates()

    def _slider(self, parent, title, variable, command):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16)
        ui.label(row, title, muted=True, size=11).pack(side="left")
        value = ui.label(row, f"{variable.get():.1f}%", size=11, bold=True)
        value.pack(side="right")
        slider = ctk.CTkSlider(
            parent,
            from_=0,
            to=100,
            number_of_steps=200,
            variable=variable,
            command=command,
            progress_color=ui.ACCENT,
            button_color=ui.ACCENT,
            button_hover_color=ui.ACCENT_HOVER,
            fg_color=ui.BORDER,
        )
        slider.pack(fill="x", padx=16, pady=(6, 18))
        return value, slider

    def _refresh_templates(self, preferred: str | None = None) -> None:
        self.templates = sorted(path.name for path in Path(IMAGES_DIR).glob("*.png"))
        if preferred in self.templates:
            self.selected = preferred
        elif self.selected not in self.templates:
            self.selected = self.templates[0] if self.templates else None
        self._draw_templates()
        if self.selected:
            self._select(self.selected)

    def _draw_templates(self) -> None:
        for child in self.template_scroll.winfo_children():
            child.destroy()
        query = self.query.get().strip().casefold()
        names = [name for name in self.templates if query in name.casefold()]
        self.rows.clear()
        for row, name in enumerate(names):
            selected = name == self.selected
            button = ctk.CTkButton(
                self.template_scroll,
                text=name,
                command=lambda value=name: self._select(value),
                anchor="w",
                height=34,
                corner_radius=7,
                fg_color=ui.ACCENT_SOFT if selected else "transparent",
                hover_color=ui.ACCENT_SOFT,
                text_color=ui.ACCENT_HOVER if selected else ui.TEXT,
            )
            button.grid(row=row, column=0, sticky="ew", pady=1)
            self.rows[name] = button

    def _select(self, name: str) -> None:
        self.selected = name
        self.best_valid_bounds = None
        self._draw_templates()
        try:
            settings = load_settings(name)
            self.method.set(settings.method)
            self.shape.set(settings.min_shape)
            self.colour.set(settings.min_color)
            self._update_threshold_labels()
            self.status.set(f"{name} geladen. Thresholds zijn live aanpasbaar.")
            self._schedule()
        except Exception as exc:
            self.status.set(f"Fout: {exc}")

    def _toggle_live(self) -> None:
        self.status.set(
            "Live matching actief." if self.live.get() else "Live matching gepauzeerd."
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
        if not self.selected:
            self.status.set("Selecteer eerst een template.")
            return
        try:
            self.screenshot, self.region = capture_area(
                self.source.area.get(),
                bot_id=self.source.bot(),
            )
            self._analyse()
        except Exception as exc:
            self.live.set(False)
            self.status.set(f"Fout: {exc}")

    def _threshold_changed(self, _value=None) -> None:
        self._update_threshold_labels()
        self._schedule()

    def _update_threshold_labels(self) -> None:
        self.shape_label.configure(text=f"{self.shape.get():.1f}%")
        self.colour_label.configure(text=f"{self.colour.get():.1f}%")

    def _schedule(self) -> None:
        if self.screenshot is None:
            return
        if self._job is not None:
            self.after_cancel(self._job)
        self._job = self.after(70, self._analyse)

    def _analyse(self) -> None:
        self._job = None
        self.best_valid_bounds = None
        if self.screenshot is None or not self.selected or self.region is None:
            return
        started = time.perf_counter()
        try:
            template_rgb, template_gray = load_template(self.selected)
            maximum = max(1, int(self.maximum.get() or 1))
            analysis = analyse_template(
                self.screenshot,
                template_rgb,
                template_gray,
                method=self.method.get(),
                minimum_shape=self.shape.get(),
                maximum_candidates=maximum,
            )

            visual = self.screenshot.copy()
            rows = []
            valid_candidates = []
            for candidate in analysis.candidates:
                valid = candidate.passes_colour(self.colour.get())
                if valid:
                    valid_candidates.append(candidate)
                rows.append(
                    (
                        valid,
                        candidate.shape_score,
                        candidate.color_score,
                        candidate.x,
                        candidate.y,
                    )
                )
                cv2.rectangle(
                    visual,
                    (candidate.x, candidate.y),
                    (candidate.x + candidate.width, candidate.y + candidate.height),
                    (37, 169, 105) if valid else (220, 82, 104),
                    2,
                )

            if valid_candidates:
                target = max(
                    valid_candidates,
                    key=lambda candidate: (
                        candidate.shape_score,
                        candidate.color_score,
                    ),
                )
                local_bounds = image_target_bounds(
                    target.x,
                    target.y,
                    target.x + target.width,
                    target.y + target.height,
                    image_edge_padding=self._x_padding_percent(),
                )
                origin_x, origin_y = self.region[0], self.region[1]
                self.best_valid_bounds = (
                    local_bounds[0] + origin_x,
                    local_bounds[1] + origin_y,
                    local_bounds[2] + origin_x,
                    local_bounds[3] + origin_y,
                )
                cv2.rectangle(
                    visual,
                    (local_bounds[0], local_bounds[1]),
                    (local_bounds[2], local_bounds[3]),
                    (209, 166, 75),
                    1,
                )

            self.preview.show(visual)
            lines = ["STATUS         SHAPE    COLOUR      X      Y"]
            lines.extend(
                f"{'GELDIG' if valid else 'KLEUR FAALT':<14} "
                f"{shape:>5.1f}%   {colour:>5.1f}%   {x:>4}   {y:>4}"
                for valid, shape, colour, x, y in rows
            )
            self.results.configure(state="normal")
            self.results.delete("1.0", "end")
            self.results.insert("1.0", "\n".join(lines))
            self.results.configure(state="disabled")
            self.summary.configure(
                text=(
                    f"Beste shape  {analysis.best_shape_score:.1f}%\n"
                    f"Kleur daarbij  {analysis.best_color_score:.1f}%\n"
                    f"Geldige hits  {len(valid_candidates)}/{len(rows)}"
                )
            )
            elapsed = (time.perf_counter() - started) * 1000
            self.status.set(
                f"Bot {self.source.bot()}  •  {self.source.area.get()}  •  "
                f"{self.method.get()}  •  {elapsed:.1f} ms"
            )
        except Exception as exc:
            self.live.set(False)
            self.status.set(f"Fout: {exc}")

    def _x_padding_percent(self) -> float:
        try:
            value = float(self.x_padding.get().strip().replace(",", "."))
        except ValueError:
            value = MIN_IMAGE_EDGE_PADDING
        return normalize_image_edge_padding(value)

    def _move_to_image(self) -> None:
        self.live.set(False)
        if self.best_valid_bounds is None:
            self._capture()
        if self.best_valid_bounds is None:
            self.status.set("Geen geldige image gevonden om naartoe te bewegen.")
            return

        padding_percent = self._x_padding_percent()
        self.x_padding.set(f"{padding_percent:g}")
        left, top, right, bottom = self.best_valid_bounds
        try:
            mouse.move_to_target(
                left,
                top,
                right,
                bottom,
                keep_pending_click=False,
            )
            error = mouse.last_engine_error()
            if error:
                self.status.set(f"Muis bewogen via fallback · Mouse Engine: {error}")
            else:
                x, y = mouse.position()
                self.status.set(
                    f"Muis naar {self.selected} bewogen · ({x}, {y}) · "
                    f"X-padding {padding_percent:g}% · niet geklikt"
                )
        except Exception as exc:
            self.status.set(f"Muis bewegen mislukt: {exc}")

    def _save(self) -> None:
        if not self.selected:
            return
        try:
            save_settings(
                self.selected,
                TemplateSettings(
                    self.method.get(),
                    self.shape.get(),
                    self.colour.get(),
                    self.source.area.get() or None,
                ),
            )
            self.status.set(f"Instellingen voor {self.selected} opgeslagen.")
        except Exception as exc:
            messagebox.showerror("Template", str(exc), parent=self)

    def _new_template(self) -> None:
        self.live.set(False)
        TemplateCaptureOverlay(self, self._captured)

    def _captured(self, name: str) -> None:
        save_settings(
            name,
            TemplateSettings(
                self.method.get(),
                self.shape.get(),
                self.colour.get(),
                self.source.area.get() or None,
            ),
        )
        self._refresh_templates(name)
        self.status.set(f"Nieuwe template {name} opgeslagen.")

    def _rename(self) -> None:
        if not self.selected:
            return
        value = simpledialog.askstring(
            "Template hernoemen",
            "Nieuwe naam:",
            initialvalue=Path(self.selected).stem,
            parent=self,
        )
        if not value:
            return
        try:
            self._refresh_templates(rename_template(self.selected, value))
        except Exception as exc:
            messagebox.showerror("Template", str(exc), parent=self)

    def _delete(self) -> None:
        if not self.selected or not messagebox.askyesno(
            "Template verwijderen",
            f"{self.selected} definitief verwijderen?",
            parent=self,
        ):
            return
        try:
            delete_template(self.selected)
            self.selected = None
            self.screenshot = None
            self._refresh_templates()
        except Exception as exc:
            messagebox.showerror("Template", str(exc), parent=self)


__all__ = ["TemplatePage"]
