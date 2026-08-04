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
from .common import PreviewLabel, SourceBar


class ImagePage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.running = False
        self.maximum_hits = tk.IntVar(value=30)
        self.status = tk.StringVar(value="Selecteer één of meer templates.")
        self.result_text = tk.StringVar(value="Nog geen analyse uitgevoerd.")
        self._build()
        self.after(100, self._tick)

    def _build(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x")
        self.source = SourceBar(top)
        self.source.pack(side="left", fill="x", expand=True)
        actions = ttk.Frame(top, padding=8)
        actions.pack(side="right")
        ttk.Label(actions, text="Max kandidaten").pack(side="left", padx=(0, 4))
        ttk.Spinbox(actions, from_=1, to=100, textvariable=self.maximum_hits, width=7).pack(
            side="left", padx=(0, 8)
        )
        self.live_button = ttk.Button(actions, text="Live", command=self._toggle)
        self.live_button.pack(side="left", padx=3)
        ttk.Button(actions, text="Eenmalig", command=self._once).pack(side="left", padx=3)
        ttk.Button(actions, text="Vernieuwen", command=self._refresh_templates).pack(side="left", padx=3)

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        sidebar = ttk.LabelFrame(body, text="Templates — Ctrl/Shift voor meerdere", padding=6)
        body.add(sidebar, weight=1)
        self.template_list = tk.Listbox(sidebar, selectmode="extended", exportselection=False)
        scroll = ttk.Scrollbar(sidebar, orient="vertical", command=self.template_list.yview)
        self.template_list.configure(yscrollcommand=scroll.set)
        self.template_list.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self._refresh_templates()

        preview_frame = ttk.LabelFrame(body, text="Live area met geaccepteerde matches", padding=4)
        body.add(preview_frame, weight=4)
        self.preview = PreviewLabel(preview_frame, fallback_width=900, fallback_height=650)
        self.preview.pack(fill="both", expand=True)

        results = ttk.LabelFrame(self, text="Resultaten", padding=8)
        results.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Label(results, textvariable=self.result_text, justify="left").pack(anchor="w")
        ttk.Label(self, textvariable=self.status, padding=(10, 5)).pack(fill="x")

    def _refresh_templates(self) -> None:
        selected = set(self._selected_templates()) if hasattr(self, "template_list") else set()
        if not hasattr(self, "template_list"):
            return
        self.template_list.delete(0, "end")
        templates = sorted(path.name for path in Path(IMAGES_DIR).glob("*.png"))
        for index, name in enumerate(templates):
            self.template_list.insert("end", name)
            if name in selected:
                self.template_list.selection_set(index)

    def _selected_templates(self) -> list[str]:
        return [self.template_list.get(index) for index in self.template_list.curselection()]

    def _toggle(self) -> None:
        self.running = not self.running
        self.live_button.configure(text="Pauze" if self.running else "Live")

    def _once(self) -> None:
        self.running = False
        self.live_button.configure(text="Live")
        self._render()

    def _tick(self) -> None:
        if self.running:
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
            self.running = False
            self.live_button.configure(text="Live")
            self.status.set(f"Fout: {exc}")
