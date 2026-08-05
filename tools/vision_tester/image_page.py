from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

import cv2
import numpy as np

from core.vision.color_matching import calculate_color_score
from core.vision.models import TemplateSettings
from core.vision.screenshots import capture_area
from core.vision.template_matching import available_methods, iter_candidates, match_template
from core.vision.templates import (
    IMAGES_DIR,
    delete_template,
    load_settings,
    load_template,
    rename_template,
    save_settings,
)
from .common import (
    COLOURS,
    LiveToggle,
    ModernButton,
    PreviewLabel,
    SourceBar,
    filter_options,
)
from .template_capture import TemplateCaptureOverlay


class ImagePage(ttk.Frame):
    """Complete live template calibration and capture workspace."""

    def __init__(self, parent):
        super().__init__(parent)
        self.live = tk.BooleanVar(value=False)
        self.maximum_hits = tk.IntVar(value=30)
        self.template_query = tk.StringVar()
        self.method = tk.StringVar(value="TM_CCOEFF_NORMED")
        self.shape_threshold = tk.DoubleVar(value=85.0)
        self.colour_threshold = tk.DoubleVar(value=60.0)
        self.shape_text = tk.StringVar(value="85.0%")
        self.colour_text = tk.StringVar(value="60.0%")
        self.status = tk.StringVar(value="Selecteer een template of maak een nieuwe screenshot.")
        self.summary = tk.StringVar(value="Nog geen analyse uitgevoerd.")
        self.all_templates: list[str] = []
        self.current_screenshot: np.ndarray | None = None
        self.current_region: tuple[int, int, int, int] | None = None
        self._render_job: str | None = None

        self._build()
        self.shape_threshold.trace_add("write", self._settings_changed)
        self.colour_threshold.trace_add("write", self._settings_changed)
        self.maximum_hits.trace_add("write", self._settings_changed)
        self.after(100, self._tick)

    def _build(self) -> None:
        toolbar = ttk.Frame(self, style="Surface.TFrame", padding=(16, 14))
        toolbar.pack(fill="x", padx=22, pady=(18, 12))
        self.source = SourceBar(toolbar)
        self.source.pack(side="left", fill="x", expand=True, padx=(0, 18))
        actions = ttk.Frame(toolbar, style="Surface.TFrame")
        actions.pack(side="right")
        ModernButton(
            actions,
            text="＋ NIEUWE TEMPLATE",
            command=self._new_template,
            width=166,
        ).pack(
            side="left", padx=(0, 8)
        )
        self.live_button = LiveToggle(actions, variable=self.live, command=self._toggle)
        self.live_button.pack(side="left", padx=(0, 8))
        ModernButton(
            actions,
            text="CAPTURE",
            command=self._once,
            width=112,
            variant="primary",
        ).pack(side="left")

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=22, pady=(0, 12))

        sidebar = ttk.Frame(body, style="Surface.TFrame", padding=(13, 12))
        body.add(sidebar, weight=1)
        ttk.Label(
            sidebar,
            text="TEMPLATES",
            style="Surface.TLabel",
            font=("Segoe UI Semibold", 11),
        ).pack(anchor="w")
        ttk.Label(
            sidebar,
            text="Zoek en selecteer één afbeelding",
            style="SurfaceMuted.TLabel",
        ).pack(anchor="w", pady=(2, 10))
        search = ttk.Entry(sidebar, textvariable=self.template_query)
        search.pack(fill="x", pady=(0, 10))
        search.bind("<KeyRelease>", lambda _event: self._filter_templates())

        list_container = ttk.Frame(sidebar, style="Surface.TFrame")
        list_container.pack(fill="both", expand=True)
        self.template_list = tk.Listbox(
            list_container,
            selectmode="browse",
            exportselection=False,
            background=COLOURS["surface_raised"],
            foreground=COLOURS["text"],
            selectbackground=COLOURS["accent_dark"],
            selectforeground=COLOURS["text"],
            highlightbackground=COLOURS["border"],
            highlightcolor=COLOURS["accent"],
            borderwidth=0,
            highlightthickness=1,
            relief="flat",
            activestyle="none",
            font=("Segoe UI", 10),
        )
        scroll = ttk.Scrollbar(list_container, orient="vertical", command=self.template_list.yview)
        self.template_list.configure(yscrollcommand=scroll.set)
        self.template_list.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.template_list.bind("<<ListboxSelect>>", self._template_selected)

        template_actions = ttk.Frame(sidebar, style="Surface.TFrame")
        template_actions.pack(fill="x", pady=(10, 0))
        ModernButton(
            template_actions,
            text="HERNOEM",
            command=self._rename_template,
            width=116,
        ).pack(
            side="left", fill="x", expand=True, padx=(0, 4)
        )
        ModernButton(
            template_actions,
            text="VERWIJDER",
            command=self._delete_template,
            width=116,
            variant="danger",
        ).pack(
            side="left", fill="x", expand=True, padx=(4, 0)
        )

        thumbnail_card = ttk.Frame(sidebar, style="Raised.TFrame", padding=(9, 9))
        thumbnail_card.pack(fill="x", pady=(12, 0))
        ttk.Label(thumbnail_card, text="TEMPLATE PREVIEW", style="SurfaceMuted.TLabel").pack(
            anchor="w"
        )
        self.thumbnail = PreviewLabel(
            thumbnail_card,
            fallback_width=260,
            fallback_height=120,
            allow_upscale=True,
            maximum_upscale=5,
        )
        self.thumbnail.pack(fill="x", pady=(7, 0))

        workspace = ttk.Frame(body, style="Surface.TFrame", padding=(13, 12))
        body.add(workspace, weight=4)
        ttk.Label(
            workspace,
            text="LIVE AREA",
            style="Surface.TLabel",
            font=("Segoe UI Semibold", 11),
        ).pack(anchor="w")
        ttk.Label(
            workspace,
            text="Groen voldoet aan beide thresholds · rood faalt op kleur",
            style="SurfaceMuted.TLabel",
        ).pack(anchor="w", pady=(2, 10))
        self.preview = PreviewLabel(
            workspace,
            fallback_width=900,
            fallback_height=590,
            allow_upscale=True,
        )
        self.preview.pack(fill="both", expand=True)

        results = ttk.Frame(workspace, style="Surface.TFrame")
        results.pack(fill="x", pady=(10, 0))
        columns = ("status", "shape", "colour", "x", "y")
        self.results = ttk.Treeview(results, columns=columns, show="headings", height=4)
        for key, title, width in (
            ("status", "STATUS", 85),
            ("shape", "SHAPE", 90),
            ("colour", "COLOUR", 90),
            ("x", "X", 70),
            ("y", "Y", 70),
        ):
            self.results.heading(key, text=title)
            self.results.column(key, width=width, anchor="center")
        self.results.pack(fill="x")

        settings = ttk.Frame(body, style="Surface.TFrame", padding=(15, 13))
        body.add(settings, weight=2)
        ttk.Label(
            settings,
            text="DETECTIE INSTELLEN",
            style="Surface.TLabel",
            font=("Segoe UI Semibold", 11),
        ).pack(anchor="w")
        ttk.Label(
            settings,
            text="Wijzig live en sla daarna op als productie-instelling.",
            style="SurfaceMuted.TLabel",
            wraplength=290,
        ).pack(anchor="w", pady=(2, 18))

        ttk.Label(settings, text="METHODE", style="SurfaceMuted.TLabel").pack(anchor="w")
        self.method_box = ttk.Combobox(
            settings,
            textvariable=self.method,
            values=available_methods(),
            state="readonly",
        )
        self.method_box.pack(fill="x", pady=(4, 16))
        self.method_box.bind("<<ComboboxSelected>>", lambda _event: self._schedule_rerender())

        self._build_threshold(
            settings,
            title="SHAPE THRESHOLD",
            variable=self.shape_threshold,
            textvariable=self.shape_text,
        )
        self._build_threshold(
            settings,
            title="COLOUR THRESHOLD",
            variable=self.colour_threshold,
            textvariable=self.colour_text,
        )

        ttk.Label(settings, text="MAX HITS", style="SurfaceMuted.TLabel").pack(
            anchor="w", pady=(3, 0)
        )
        ttk.Spinbox(
            settings,
            from_=1,
            to=100,
            textvariable=self.maximum_hits,
            width=10,
        ).pack(anchor="w", pady=(4, 18))
        ModernButton(
            settings,
            text="INSTELLINGEN OPSLAAN",
            command=self._save_settings,
            width=280,
            variant="primary",
        ).pack(fill="x")
        ttk.Label(
            settings,
            textvariable=self.summary,
            style="SurfaceMuted.TLabel",
            justify="left",
            wraplength=290,
        ).pack(anchor="w", fill="x", pady=(18, 0))

        ttk.Label(self, textvariable=self.status, padding=(24, 9), style="Muted.TLabel").pack(
            fill="x"
        )
        self._refresh_templates()

    def _build_threshold(
        self,
        parent,
        *,
        title: str,
        variable: tk.DoubleVar,
        textvariable: tk.StringVar,
    ) -> None:
        row = ttk.Frame(parent, style="Surface.TFrame")
        row.pack(fill="x")
        ttk.Label(row, text=title, style="SurfaceMuted.TLabel").pack(side="left")
        ttk.Label(
            row,
            textvariable=textvariable,
            style="Surface.TLabel",
            font=("Segoe UI Semibold", 10),
        ).pack(side="right")
        ttk.Scale(
            parent,
            from_=0,
            to=100,
            variable=variable,
            orient="horizontal",
            style="Modern.Horizontal.TScale",
        ).pack(fill="x", pady=(6, 18))

    def _selected_template(self) -> str | None:
        selection = self.template_list.curselection()
        return self.template_list.get(selection[0]) if selection else None

    def _refresh_templates(self, preferred: str | None = None) -> None:
        current = preferred or self._selected_template()
        self.all_templates = sorted(path.name for path in Path(IMAGES_DIR).glob("*.png"))
        self._filter_templates(preferred=current)

    def _filter_templates(self, preferred: str | None = None) -> None:
        current = preferred or self._selected_template()
        visible = filter_options(self.all_templates, self.template_query.get())
        self.template_list.delete(0, "end")
        for name in visible:
            self.template_list.insert("end", name)
        target = current if current in visible else (visible[0] if visible else None)
        if target is not None:
            index = visible.index(target)
            self.template_list.selection_set(index)
            self.template_list.see(index)
            self._template_selected()

    def _template_selected(self, _event=None) -> None:
        name = self._selected_template()
        if not name:
            return
        try:
            settings = load_settings(name)
            template_rgb, _template_gray = load_template(name)
            self.method.set(settings.method)
            self.shape_threshold.set(settings.min_shape)
            self.colour_threshold.set(settings.min_color)
            if settings.area:
                self.source.area.set(settings.area)
            self.thumbnail.show(template_rgb)
            self.status.set(f"{name} geladen. Thresholds zijn nu live aanpasbaar.")
            self._schedule_rerender()
        except Exception as exc:
            self.status.set(f"Fout: {exc}")

    def _toggle(self) -> None:
        self.status.set("Live matching actief." if self.live.get() else "Live matching gepauzeerd.")

    def _once(self) -> None:
        self.live.set(False)
        self._capture_and_analyse()

    def _tick(self) -> None:
        if self.live.get():
            self._capture_and_analyse()
        self.after(100, self._tick)

    def _settings_changed(self, *_args) -> None:
        try:
            self.shape_text.set(f"{self.shape_threshold.get():.1f}%")
            self.colour_text.set(f"{self.colour_threshold.get():.1f}%")
            self.maximum_hits.get()
        except tk.TclError:
            return
        self._schedule_rerender()

    def _schedule_rerender(self) -> None:
        if self.current_screenshot is None:
            return
        if self._render_job is not None:
            self.after_cancel(self._render_job)
        self._render_job = self.after(70, self._rerender)

    def _rerender(self) -> None:
        self._render_job = None
        if self.current_screenshot is not None:
            self._analyse(self.current_screenshot)

    def _capture_and_analyse(self) -> None:
        if not self._selected_template():
            self.status.set("Selecteer eerst een template.")
            return
        try:
            self.current_screenshot, self.current_region = capture_area(
                self.source.area.get(),
                bot_id=self.source.bot_id.get(),
            )
            self._analyse(self.current_screenshot)
        except Exception as exc:
            self.live.set(False)
            self.status.set(f"Fout: {exc}")

    def _analyse(self, screenshot: np.ndarray) -> None:
        name = self._selected_template()
        method = self.method.get()
        if not name or method not in available_methods():
            return
        started = time.perf_counter()
        try:
            shape_limit = self.shape_threshold.get()
            colour_limit = self.colour_threshold.get()
            maximum = max(1, self.maximum_hits.get())
            template_rgb, template_gray = load_template(name)
            screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
            height, width = template_gray.shape[:2]
            if screenshot_gray.shape[0] < height or screenshot_gray.shape[1] < width:
                raise ValueError("Template is groter dan de geselecteerde area")

            scores = match_template(screenshot_gray, template_gray, method)
            _minimum, best_score, _minimum_location, best_location = cv2.minMaxLoc(scores)
            visual = screenshot.copy()
            rows: list[tuple[str, float, float, int, int]] = []
            valid_hits = 0
            for x, y, score in iter_candidates(
                scores,
                shape_limit / 100.0,
                width,
                height,
                maximum_candidates=maximum,
            ):
                patch = screenshot[y : y + height, x : x + width]
                colour_score = calculate_color_score(template_rgb, patch)
                valid = colour_score >= colour_limit
                valid_hits += int(valid)
                rows.append(("GELDIG" if valid else "KLEUR FAALT", score * 100.0, colour_score, x, y))
                box_colour = (43, 191, 106) if valid else (224, 82, 103)
                cv2.rectangle(visual, (x, y), (x + width, y + height), box_colour, 2)

            best_x, best_y = best_location
            best_patch = screenshot[best_y : best_y + height, best_x : best_x + width]
            best_colour = calculate_color_score(template_rgb, best_patch)
            self.preview.show(visual)
            self.results.delete(*self.results.get_children())
            for status, shape, colour, x, y in rows:
                self.results.insert(
                    "",
                    "end",
                    values=(status, f"{shape:.1f}%", f"{colour:.1f}%", x, y),
                )

            elapsed = (time.perf_counter() - started) * 1000.0
            self.summary.set(
                f"Beste shape   {best_score * 100.0:.1f}%\n"
                f"Kleur daarbij  {best_colour:.1f}%\n"
                f"Geldige hits   {valid_hits}/{len(rows)}"
            )
            self.status.set(
                f"Bot {self.source.bot_id.get()}  •  {self.source.area.get()}  •  "
                f"{method}  •  {elapsed:.1f} ms"
            )
        except Exception as exc:
            self.live.set(False)
            self.status.set(f"Fout: {exc}")

    def _save_settings(self) -> None:
        name = self._selected_template()
        if not name:
            messagebox.showerror("Template", "Selecteer eerst een template.")
            return
        try:
            save_settings(
                name,
                TemplateSettings(
                    method=self.method.get(),
                    min_shape=self.shape_threshold.get(),
                    min_color=self.colour_threshold.get(),
                    area=self.source.area.get() or None,
                ),
            )
            self.status.set(f"Productie-instellingen voor {name} opgeslagen.")
        except Exception as exc:
            messagebox.showerror("Template", str(exc))

    def _new_template(self) -> None:
        self.live.set(False)
        TemplateCaptureOverlay(self, self._template_captured)

    def _template_captured(self, name: str) -> None:
        try:
            save_settings(
                name,
                TemplateSettings(
                    method=self.method.get(),
                    min_shape=self.shape_threshold.get(),
                    min_color=self.colour_threshold.get(),
                    area=self.source.area.get() or None,
                ),
            )
            self._refresh_templates(preferred=name)
            self.status.set(f"Nieuwe template {name} opgeslagen en geselecteerd.")
        except Exception as exc:
            messagebox.showerror("Template", str(exc))

    def _rename_template(self) -> None:
        current = self._selected_template()
        if not current:
            return
        value = simpledialog.askstring(
            "Template hernoemen",
            "Nieuwe naam:",
            initialvalue=Path(current).stem,
            parent=self,
        )
        if not value:
            return
        try:
            new_name = rename_template(current, value)
            self._refresh_templates(preferred=new_name)
            self.status.set(f"Template hernoemd naar {new_name}.")
        except Exception as exc:
            messagebox.showerror("Template", str(exc))

    def _delete_template(self) -> None:
        current = self._selected_template()
        if not current or not messagebox.askyesno(
            "Template verwijderen",
            f"{current} definitief verwijderen?",
            parent=self,
        ):
            return
        try:
            delete_template(current)
            self.current_screenshot = None
            self._refresh_templates()
            self.status.set(f"Template {current} verwijderd.")
        except Exception as exc:
            messagebox.showerror("Template", str(exc))
