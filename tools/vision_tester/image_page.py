from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import cv2

from core.vision.color_matching import calculate_color_score
from core.vision.screenshots import capture_area
from core.vision.template_matching import iter_candidates, match_template
from core.vision.templates import IMAGES_DIR, load_settings, load_template
from .common import COLOURS, LiveToggle, PreviewLabel, SourceBar, filter_options


class ImagePage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.live = tk.BooleanVar(value=False)
        self.maximum_hits = tk.IntVar(value=30)
        self.template_query = tk.StringVar()
        self.all_templates: list[str] = []
        self.template_selection: set[str] = set()
        self._updating_templates = False
        self.status = tk.StringVar(value="Selecteer één of meer templates.")
        self.result_text = tk.StringVar(value="Nog geen analyse uitgevoerd.")
        self._build()
        self.after(100, self._tick)

    def _build(self) -> None:
        top = ttk.Frame(self, style="Surface.TFrame", padding=(14, 12))
        top.pack(fill="x", padx=18, pady=(14, 10))
        self.source = SourceBar(top)
        self.source.pack(side="left", fill="x", expand=True)
        actions = ttk.Frame(top, style="Surface.TFrame")
        actions.pack(side="right")
        ttk.Label(actions, text="MAX KANDIDATEN", style="SurfaceMuted.TLabel").pack(side="left", padx=(0, 6))
        ttk.Spinbox(actions, from_=1, to=100, textvariable=self.maximum_hits, width=7).pack(
            side="left", padx=(0, 8)
        )
        self.live_button = LiveToggle(actions, variable=self.live, command=self._toggle)
        self.live_button.pack(side="left", padx=3)
        ttk.Button(actions, text="Capture", command=self._once, style="Accent.TButton").pack(side="left", padx=(7, 3))
        ttk.Button(actions, text="↻", command=self._refresh_templates, width=3).pack(side="left", padx=3)

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=18, pady=(0, 10))

        sidebar = ttk.LabelFrame(body, text="  Templates  ", padding=10, style="Card.TLabelframe")
        body.add(sidebar, weight=1)
        ttk.Label(sidebar, text="ZOEK OP DEEL VAN NAAM", style="SurfaceMuted.TLabel").pack(anchor="w")
        search = ttk.Entry(sidebar, textvariable=self.template_query)
        search.pack(fill="x", pady=(4, 8))
        search.bind("<KeyRelease>", lambda _event: self._filter_templates())
        ttk.Label(
            sidebar,
            text="Ctrl of Shift om meerdere te selecteren",
            style="SurfaceMuted.TLabel",
        ).pack(anchor="w", pady=(0, 7))
        list_container = ttk.Frame(sidebar, style="Surface.TFrame")
        list_container.pack(fill="both", expand=True)
        self.template_list = tk.Listbox(
            list_container,
            selectmode="extended",
            exportselection=False,
            background=COLOURS["surface_raised"],
            foreground=COLOURS["text"],
            selectbackground=COLOURS["accent_dark"],
            selectforeground=COLOURS["accent"],
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
        self.template_list.bind("<<ListboxSelect>>", self._remember_selection)
        self._refresh_templates()

        preview_frame = ttk.LabelFrame(body, text="  Live area · geaccepteerde matches  ", padding=6, style="Card.TLabelframe")
        body.add(preview_frame, weight=4)
        self.preview = PreviewLabel(preview_frame, fallback_width=900, fallback_height=650)
        self.preview.pack(fill="both", expand=True)

        results = ttk.LabelFrame(self, text="  Resultaten  ", padding=10, style="Card.TLabelframe")
        results.pack(fill="x", padx=18, pady=(0, 8))
        ttk.Label(results, textvariable=self.result_text, justify="left", style="Surface.TLabel").pack(anchor="w")
        ttk.Label(self, textvariable=self.status, padding=(20, 8), style="Muted.TLabel").pack(fill="x")

    def _refresh_templates(self) -> None:
        if not hasattr(self, "template_list"):
            return
        self.template_selection.update(self._visible_selection())
        self.all_templates = sorted(path.name for path in Path(IMAGES_DIR).glob("*.png"))
        self._filter_templates()

    def _filter_templates(self) -> None:
        if not hasattr(self, "template_list"):
            return
        self.template_selection.update(self._visible_selection())
        templates = filter_options(self.all_templates, self.template_query.get())
        self._updating_templates = True
        self.template_list.delete(0, "end")
        for index, name in enumerate(templates):
            self.template_list.insert("end", name)
            if name in self.template_selection:
                self.template_list.selection_set(index)
        self._updating_templates = False

    def _visible_selection(self) -> set[str]:
        return {self.template_list.get(index) for index in self.template_list.curselection()}

    def _remember_selection(self, _event=None) -> None:
        if self._updating_templates:
            return
        visible_names = {self.template_list.get(index) for index in range(self.template_list.size())}
        self.template_selection.difference_update(visible_names)
        self.template_selection.update(self._visible_selection())

    def _selected_templates(self) -> list[str]:
        self._remember_selection()
        return sorted(self.template_selection)

    def _toggle(self) -> None:
        self.status.set("Live matching actief." if self.live.get() else "Live matching gepauzeerd.")

    def _once(self) -> None:
        self.live.set(False)
        self._render()

    def _tick(self) -> None:
        if self.live.get():
            self._render()
        self.after(100, self._tick)

    def _render(self) -> None:
        templates = self._selected_templates()
        if not templates:
            self.status.set("Selecteer minimaal één template.")
            return
        started = time.perf_counter()
        try:
            screenshot, region = capture_area(
                self.source.area.get(), bot_id=self.source.bot_id.get()
            )
            screenshot_gray = cv2.cvtColor(screenshot, cv2.COLOR_RGB2GRAY)
            visual = screenshot.copy()
            lines: list[str] = []
            total_hits = 0
            maximum = max(1, int(self.maximum_hits.get()))

            for name in templates:
                template_rgb, template_gray = load_template(name)
                settings = load_settings(name)
                height, width = template_gray.shape[:2]
                if screenshot_gray.shape[0] < height or screenshot_gray.shape[1] < width:
                    lines.append(f"{name}: template groter dan area")
                    continue
                scores = match_template(screenshot_gray, template_gray, settings.method)
                hits = 0
                best_shape = 0.0
                best_colour = 0.0
                for x, y, score in iter_candidates(
                    scores,
                    settings.min_shape / 100.0,
                    width,
                    height,
                    maximum_candidates=maximum,
                ):
                    patch = screenshot[y : y + height, x : x + width]
                    colour_score = calculate_color_score(template_rgb, patch)
                    best_shape = max(best_shape, score * 100.0)
                    best_colour = max(best_colour, colour_score)
                    if colour_score < settings.min_color:
                        continue
                    hits += 1
                    total_hits += 1
                    cv2.rectangle(visual, (x, y), (x + width, y + height), (0, 220, 255), 2)
                    cv2.putText(
                        visual,
                        f"{Path(name).stem} {score * 100.0:.1f}%",
                        (x, max(16, y - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.45,
                        (0, 220, 255),
                        1,
                        cv2.LINE_AA,
                    )
                lines.append(
                    f"{name}: {hits} match(es) | beste shape {best_shape:.1f}% | colour {best_colour:.1f}%"
                )

            self.preview.show(visual)
            elapsed = (time.perf_counter() - started) * 1000.0
            self.result_text.set("\n".join(lines))
            self.status.set(
                f"Bot {self.source.bot_id.get()} | {self.source.area.get()} | "
                f"templates {len(templates)} | matches {total_hits} | {elapsed:.1f} ms | region={region}"
            )
        except Exception as exc:
            self.live.set(False)
            self.status.set(f"Fout: {exc}")
