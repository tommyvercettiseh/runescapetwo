from __future__ import annotations

import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import cv2
from PIL import Image, ImageTk

from core.vision.areas import load_areas
from core.vision.color_matching import calculate_color_score
from core.vision.models import TemplateSettings
from core.vision.screenshots import capture_area
from core.vision.template_matching import available_methods, iter_candidates, match_template
from core.vision.templates import IMAGES_DIR, load_settings, load_template, save_settings


class ImageTester(tk.Tk):
    """Live calibration tool that uses the exact production matching engine."""

    def __init__(self) -> None:
        super().__init__()
        self.title("RuneScape Two - Live Image Tester")
        self.geometry("1320x860")
        self.minsize(1000, 700)

        self.running = False
        self._photos: dict[str, ImageTk.PhotoImage] = {}
        self._preview_labels: dict[str, ttk.Label] = {}
        self._preview_frames: dict[str, ttk.LabelFrame] = {}

        self.template_name = tk.StringVar()
        self.area_name = tk.StringVar(value="game")
        self.bot_id = tk.IntVar(value=1)
        self.shape_threshold = tk.DoubleVar(value=85.0)
        self.color_threshold = tk.DoubleVar(value=60.0)
        self.maximum_hits = tk.IntVar(value=30)
        self.save_method = tk.StringVar(value="TM_CCOEFF_NORMED")
        self.status = tk.StringVar(value="Selecteer een template en druk op Live of Eenmalig")
        self.method_enabled = {
            method: tk.BooleanVar(value=True) for method in available_methods()
        }

        self._build_ui()
        self._refresh_sources()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_ui(self) -> None:
        controls = ttk.Frame(self, padding=8)
        controls.pack(fill="x")

        ttk.Label(controls, text="Template").grid(row=0, column=0, sticky="w")
        self.template_box = ttk.Combobox(
            controls,
            textvariable=self.template_name,
            state="readonly",
            width=32,
        )
        self.template_box.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.template_box.bind("<<ComboboxSelected>>", self._load_template_preset)

        ttk.Label(controls, text="Area").grid(row=0, column=1, sticky="w")
        self.area_box = ttk.Combobox(
            controls,
            textvariable=self.area_name,
            state="readonly",
            width=28,
        )
        self.area_box.grid(row=1, column=1, sticky="ew", padx=(0, 8))

        ttk.Label(controls, text="Bot").grid(row=0, column=2, sticky="w")
        ttk.Combobox(
            controls,
            textvariable=self.bot_id,
            values=(1, 2, 3, 4),
            state="readonly",
            width=5,
        ).grid(row=1, column=2, sticky="w", padx=(0, 8))

        ttk.Label(controls, text="Max hits").grid(row=0, column=3, sticky="w")
        ttk.Spinbox(
            controls,
            from_=1,
            to=100,
            textvariable=self.maximum_hits,
            width=7,
        ).grid(row=1, column=3, sticky="w", padx=(0, 8))

        ttk.Button(controls, text="Eenmalig", command=self._analyze_once).grid(
            row=1, column=4, padx=(0, 6)
        )
        self.live_button = ttk.Button(controls, text="Live", command=self._toggle_live)
        self.live_button.grid(row=1, column=5, padx=(0, 6))
        ttk.Button(controls, text="Vernieuwen", command=self._refresh_sources).grid(
            row=1, column=6
        )

        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(1, weight=1)

        thresholds = ttk.Frame(self, padding=(8, 0, 8, 8))
        thresholds.pack(fill="x")

        ttk.Label(thresholds, text="Shape threshold").grid(row=0, column=0, sticky="w")
        ttk.Scale(
            thresholds,
            from_=0,
            to=100,
            variable=self.shape_threshold,
        ).grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.shape_value = ttk.Label(thresholds, width=7)
        self.shape_value.grid(row=1, column=1, sticky="w")

        ttk.Label(thresholds, text="Colour threshold").grid(row=0, column=2, sticky="w")
        ttk.Scale(
            thresholds,
            from_=0,
            to=100,
            variable=self.color_threshold,
        ).grid(row=1, column=2, sticky="ew", padx=(8, 8))
        self.color_value = ttk.Label(thresholds, width=7)
        self.color_value.grid(row=1, column=3, sticky="w")

        ttk.Label(thresholds, text="Preset-methode").grid(row=0, column=4, sticky="w")
        ttk.Combobox(
            thresholds,
            textvariable=self.save_method,
            values=available_methods(),
            state="readonly",
            width=22,
        ).grid(row=1, column=4, padx=(8, 6))
        ttk.Button(thresholds, text="Preset opslaan", command=self._save_preset).grid(
            row=1, column=5
        )

        thresholds.columnconfigure(0, weight=1)
        thresholds.columnconfigure(2, weight=1)
        self.shape_threshold.trace_add("write", self._update_threshold_labels)
        self.color_threshold.trace_add("write", self._update_threshold_labels)
        self._update_threshold_labels()

        method_bar = ttk.LabelFrame(self, text="Live methodes", padding=6)
        method_bar.pack(fill="x", padx=8, pady=(0, 8))
        for column, method in enumerate(available_methods()):
            ttk.Checkbutton(
                method_bar,
                text=method,
                variable=self.method_enabled[method],
            ).grid(row=0, column=column, sticky="w", padx=5)

        preview = ttk.Frame(self, padding=(8, 0, 8, 8))
        preview.pack(fill="both", expand=True)
        for index, method in enumerate(available_methods()):
            frame = ttk.LabelFrame(preview, text=method, padding=4)
            frame.grid(row=index // 2, column=index % 2, sticky="nsew", padx=4, pady=4)
            label = ttk.Label(frame, anchor="center")
            label.pack(fill="both", expand=True)
            self._preview_frames[method] = frame
            self._preview_labels[method] = label

        for row in range(3):
            preview.rowconfigure(row, weight=1)
        for column in range(2):
            preview.columnconfigure(column, weight=1)

        ttk.Label(self, textvariable=self.status, padding=(10, 4)).pack(fill="x")

    def _update_threshold_labels(self, *_args) -> None:
        self.shape_value.configure(text=f"{self.shape_threshold.get():.1f}%")
        self.color_value.configure(text=f"{self.color_threshold.get():.1f}%")

    def _refresh_sources(self) -> None:
        templates = sorted(path.name for path in Path(IMAGES_DIR).glob("*.png"))
        areas = sorted(load_areas())
        self.template_box["values"] = templates
        self.area_box["values"] = areas

        if templates and self.template_name.get() not in templates:
            self.template_name.set(templates[0])
            self._load_template_preset()
        if areas and self.area_name.get() not in areas:
            self.area_name.set("game" if "game" in areas else areas[0])

    def _load_template_preset(self, _event=None) -> None:
        name = self.template_name.get()
        if not name:
            return
        try:
            settings = load_settings(name)
        except Exception as exc:
            self.status.set(str(exc))
            return

        self.shape_threshold.set(settings.min_shape)
        self.color_threshold.set(settings.min_color)
        self.save_method.set(settings.method)
        if settings.area:
            self.area_name.set(settings.area)

    def _selected_methods(self) -> list[str]:
        return [
            method for method, enabled in self.method_enabled.items() if enabled.get()
        ]

    def _toggle_live(self) -> None:
        self.running = not self.running
        self.live_button.configure(text="Pauze" if self.running else "Live")
        if self.running:
            self._tick()

    def _analyze_once(self) -> None:
        self.running = False
        self.live_button.configure(text="Live")
        self._render_frame()

    def _tick(self) -> None:
        if not self.running:
            return
        self._render_frame()
        self.after(80, self._tick)

    def _render_frame(self) -> None:
        name = self.template_name.get()
        area = self.area_name.get()
        methods = self._selected_methods()
        if not name or not area or not methods:
            self.status.set("Selecteer een template, area en minimaal één methode")
            return

        started = time.perf_counter()
        try:
            screenshot_rgb, region = capture_area(area, bot_id=self.bot_id.get())
            template_rgb, template_gray = load_template(name)
            screenshot_gray = cv2.cvtColor(screenshot_rgb, cv2.COLOR_RGB2GRAY)
            height, width = template_gray.shape[:2]
            if screenshot_gray.shape[0] < height or screenshot_gray.shape[1] < width:
                raise ValueError("Template is groter dan de geselecteerde area")

            shape_limit = self.shape_threshold.get() / 100.0
            color_limit = self.color_threshold.get()
            maximum_hits = max(1, int(self.maximum_hits.get()))

            for method in available_methods():
                label = self._preview_labels[method]
                frame = self._preview_frames[method]
                if method not in methods:
                    label.configure(image="")
                    frame.configure(text=f"{method} - uit")
                    continue

                method_started = time.perf_counter()
                scores = match_template(screenshot_gray, template_gray, method)
                visual = screenshot_rgb.copy()
                valid_hits = 0
                candidates = 0
                best_shape = 0.0
                best_color = 0.0

                for x, y, score in iter_candidates(
                    scores,
                    shape_limit,
                    width,
                    height,
                    maximum_candidates=maximum_hits,
                ):
                    candidates += 1
                    shape_score = score * 100.0
                    patch = screenshot_rgb[y : y + height, x : x + width]
                    color_score = calculate_color_score(template_rgb, patch)
                    valid = color_score >= color_limit
                    valid_hits += int(valid)
                    best_shape = max(best_shape, shape_score)
                    best_color = max(best_color, color_score)

                    box_color = (0, 255, 0) if valid else (255, 0, 0)
                    cv2.rectangle(
                        visual,
                        (x, y),
                        (x + width, y + height),
                        box_color,
                        2,
                    )

                elapsed_ms = (time.perf_counter() - method_started) * 1000.0
                frame.configure(
                    text=(
                        f"{method} | {elapsed_ms:.1f} ms | "
                        f"green {valid_hits}/{candidates} | "
                        f"best {best_shape:.1f}/{best_color:.1f}"
                    )
                )
                self._show_preview(method, visual)

            total_ms = (time.perf_counter() - started) * 1000.0
            fps = 1000.0 / total_ms if total_ms > 0 else 0.0
            self.status.set(
                f"Bot {self.bot_id.get()} | {area} | region={region} | "
                f"{total_ms:.1f} ms | {fps:.1f} FPS"
            )
        except Exception as exc:
            self.status.set(f"Fout: {exc}")
            self.running = False
            self.live_button.configure(text="Live")

    def _show_preview(self, method: str, image_rgb) -> None:
        height, width = image_rgb.shape[:2]
        target_width = 600
        scale = min(1.0, target_width / max(1, width))
        resized = cv2.resize(
            image_rgb,
            (max(1, int(width * scale)), max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
        photo = ImageTk.PhotoImage(Image.fromarray(resized))
        self._photos[method] = photo
        self._preview_labels[method].configure(image=photo)

    def _save_preset(self) -> None:
        name = self.template_name.get()
        area = self.area_name.get()
        method = self.save_method.get()
        if not name or not area or method not in available_methods():
            messagebox.showerror("Preset", "Selecteer een template, area en methode")
            return

        try:
            save_settings(
                name,
                TemplateSettings(
                    method=method,
                    min_shape=self.shape_threshold.get(),
                    min_color=self.color_threshold.get(),
                    area=area,
                ),
            )
            self.status.set(f"Preset opgeslagen voor {name}")
        except Exception as exc:
            messagebox.showerror("Preset", str(exc))

    def _close(self) -> None:
        self.running = False
        self.destroy()


def main() -> None:
    ImageTester().mainloop()


if __name__ == "__main__":
    main()
