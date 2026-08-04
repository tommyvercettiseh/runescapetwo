from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

from core.vision.areas import load_areas
from core.vision.colour_detection import (
    blobs_from_mask,
    build_mask_from_ranges,
    count_mask_components,
    count_mask_pixels,
    hsv_ranges_around,
    sample_hsv,
)
from core.vision.colour_presets import (
    HSVRange,
    delete_colour_preset,
    list_colour_presets,
    load_colour_preset,
    save_colour_preset,
)
from core.vision.screenshots import capture_area


class ColourTester(tk.Tk):
    """Pipette-driven live colour calibration using the production engine."""

    def __init__(self) -> None:
        super().__init__()
        self.title("RuneScape Two - Live Colour Tester")
        self.geometry("1360x860")
        self.minsize(1020, 680)

        self.running = True
        self.pipette_active = False
        self.ranges: tuple[HSVRange, ...] = ()
        self.sample: tuple[int, int, int] | None = None
        self.last_capture: np.ndarray | None = None
        self.last_region: tuple[int, int, int, int] | None = None
        self.photos: dict[str, ImageTk.PhotoImage] = {}
        self.capture_scale = 1.0

        self.name = tk.StringVar()
        self.area = tk.StringVar(value="game")
        self.bot_id = tk.IntVar(value=1)
        self.min_blob = tk.IntVar(value=20)
        self.max_blob = tk.IntVar(value=0)
        self.h_tol = tk.IntVar(value=5)
        self.s_tol = tk.IntVar(value=40)
        self.v_tol = tk.IntVar(value=40)
        self.sample_radius = tk.IntVar(value=2)
        self.info = tk.StringVar(value="Activeer het pipet en klik op een opvallende kleur.")
        self.range_info = tk.StringVar(value="Nog geen kleur geselecteerd")

        self._build()
        self._refresh_sources()
        for variable in (
            self.min_blob,
            self.max_blob,
            self.h_tol,
            self.s_tol,
            self.v_tol,
            self.sample_radius,
        ):
            variable.trace_add("write", self._settings_changed)

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._tick)

    def _build(self) -> None:
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Preset").grid(row=0, column=0, sticky="w")
        self.preset_box = ttk.Combobox(top, textvariable=self.name, width=28)
        self.preset_box.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.preset_box.bind("<<ComboboxSelected>>", lambda _event: self._load())

        for column, (text, command) in enumerate(
            (("Laden", self._load), ("Opslaan", self._save), ("Verwijderen", self._delete)),
            start=1,
        ):
            ttk.Button(top, text=text, command=command).grid(
                row=1, column=column, padx=(0, 6)
            )

        ttk.Label(top, text="Area").grid(row=0, column=4, sticky="w")
        self.area_box = ttk.Combobox(
            top,
            textvariable=self.area,
            state="readonly",
            width=26,
        )
        self.area_box.grid(row=1, column=4, sticky="ew", padx=(8, 6))

        ttk.Label(top, text="Bot").grid(row=0, column=5, sticky="w")
        ttk.Combobox(
            top,
            textvariable=self.bot_id,
            values=(1, 2, 3, 4),
            state="readonly",
            width=5,
        ).grid(row=1, column=5, padx=(0, 6))

        self.pipette_button = ttk.Button(
            top,
            text="Pipet activeren",
            command=self._toggle_pipette,
        )
        self.pipette_button.grid(row=1, column=6, padx=(0, 6))
        self.live_button = ttk.Button(top, text="Pauze", command=self._toggle_live)
        self.live_button.grid(row=1, column=7)

        top.columnconfigure(0, weight=1)
        top.columnconfigure(4, weight=1)

        settings = ttk.LabelFrame(self, text="Live filters", padding=8)
        settings.pack(fill="x", padx=8, pady=(0, 8))
        fields = (
            ("Min blobpixels", self.min_blob, 1, 50000),
            ("Max blobpixels (0 = uit)", self.max_blob, 0, 100000),
            ("Hue tolerantie", self.h_tol, 0, 40),
            ("Saturation tolerantie", self.s_tol, 0, 255),
            ("Value tolerantie", self.v_tol, 0, 255),
            ("Pipet radius", self.sample_radius, 0, 8),
        )
        for column, (label, variable, low, high) in enumerate(fields):
            ttk.Label(settings, text=label).grid(row=0, column=column, sticky="w", padx=4)
            ttk.Spinbox(
                settings,
                from_=low,
                to=high,
                textvariable=variable,
                width=12,
            ).grid(row=1, column=column, sticky="ew", padx=4)
            settings.columnconfigure(column, weight=1)

        ttk.Label(settings, textvariable=self.range_info).grid(
            row=2,
            column=0,
            columnspan=len(fields),
            sticky="w",
            pady=(8, 0),
        )

        previews = ttk.Frame(self, padding=(8, 0, 8, 8))
        previews.pack(fill="both", expand=True)
        self.capture_label = self._panel(
            previews,
            "LIVE CAPTURE — klik hier met het pipet",
            0,
            0,
        )
        self.mask_label = self._panel(previews, "MASK", 0, 1)
        self.overlay_label = self._panel(
            previews,
            "GELDIGE BLOBS + EXACTE PIXELTELLING",
            1,
            0,
            columnspan=2,
        )
        self.capture_label.bind("<Button-1>", self._pick)

        for row in range(2):
            previews.rowconfigure(row, weight=1)
        for column in range(2):
            previews.columnconfigure(column, weight=1)

        ttk.Label(self, textvariable=self.info, padding=(10, 5)).pack(fill="x")

    @staticmethod
    def _panel(parent, title: str, row: int, column: int, *, columnspan: int = 1):
        frame = ttk.LabelFrame(parent, text=title, padding=5)
        frame.grid(
            row=row,
            column=column,
            columnspan=columnspan,
            sticky="nsew",
            padx=4,
            pady=4,
        )
        label = ttk.Label(frame, anchor="nw")
        label.pack(fill="both", expand=True)
        return label

    def _refresh_sources(self) -> None:
        self.preset_box["values"] = list_colour_presets()
        areas = sorted(load_areas())
        self.area_box["values"] = areas
        if areas and self.area.get() not in areas:
            self.area.set("game" if "game" in areas else areas[0])

    def _load(self) -> None:
        try:
            preset = load_colour_preset(self.name.get())
        except Exception as exc:
            self.info.set(str(exc))
            return
        self.name.set(preset.name)
        self.ranges = preset.ranges
        self.sample = None
        self._show_ranges()
        self._rerender()
        self.info.set(f"Preset '{preset.name}' geladen.")

    def _save(self) -> None:
        if not self.name.get().strip():
            messagebox.showerror("Preset", "Geef de kleur een naam.")
            return
        if not self.ranges:
            messagebox.showerror("Preset", "Gebruik eerst het pipet.")
            return
        try:
            save_colour_preset(self.name.get(), self.ranges)
            self.name.set(self.name.get().strip().lower())
            self._refresh_sources()
            self.info.set(f"Preset '{self.name.get()}' opgeslagen.")
        except Exception as exc:
            messagebox.showerror("Preset", str(exc))

    def _delete(self) -> None:
        name = self.name.get().strip()
        if not name or not messagebox.askyesno("Preset", f"Preset '{name}' verwijderen?"):
            return
        try:
            if delete_colour_preset(name):
                self.name.set("")
                self.ranges = ()
                self.sample = None
                self._refresh_sources()
                self._show_ranges()
                self._rerender()
        except Exception as exc:
            messagebox.showerror("Preset", str(exc))

    def _toggle_pipette(self) -> None:
        self.pipette_active = not self.pipette_active
        self.pipette_button.configure(
            text="Pipet actief — klik beeld" if self.pipette_active else "Pipet activeren"
        )
        self.capture_label.configure(cursor="crosshair" if self.pipette_active else "")

    def _pick(self, event) -> None:
        if not self.pipette_active or self.last_capture is None:
            return

        x = int(event.x / max(self.capture_scale, 1e-9))
        y = int(event.y / max(self.capture_scale, 1e-9))
        height, width = self.last_capture.shape[:2]
        if not 0 <= x < width or not 0 <= y < height:
            return

        self.sample = sample_hsv(
            self.last_capture,
            x,
            y,
            radius=self.sample_radius.get(),
        )
        self._rebuild_ranges()
        self.pipette_active = False
        self.pipette_button.configure(text="Pipet activeren")
        self.capture_label.configure(cursor="")
        self._rerender()

    def _settings_changed(self, *_args) -> None:
        if self.sample is not None:
            self._rebuild_ranges()
        self._rerender()

    def _rebuild_ranges(self) -> None:
        if self.sample is None:
            return
        self.ranges = hsv_ranges_around(
            self.sample,
            hue_tolerance=self.h_tol.get(),
            saturation_tolerance=self.s_tol.get(),
            value_tolerance=self.v_tol.get(),
        )
        self._show_ranges()

    def _show_ranges(self) -> None:
        if not self.ranges:
            self.range_info.set("Nog geen kleur geselecteerd")
            return
        prefix = f"Sample HSV {self.sample} | " if self.sample else ""
        ranges = " + ".join(f"{low} → {high}" for low, high in self.ranges)
        self.range_info.set(prefix + ranges)

    def _toggle_live(self) -> None:
        self.running = not self.running
        self.live_button.configure(text="Pauze" if self.running else "Live")

    def _tick(self) -> None:
        if self.running:
            self._capture()
        self.after(100, self._tick)

    def _capture(self) -> None:
        if not self.area.get():
            return
        started = time.perf_counter()
        try:
            self.last_capture, self.last_region = capture_area(
                self.area.get(),
                bot_id=self.bot_id.get(),
            )
            self._show(self.capture_label, self.last_capture, "capture")
            self._render(started)
        except Exception as exc:
            self.running = False
            self.live_button.configure(text="Live")
            self.info.set(f"Fout: {exc}")

    def _rerender(self) -> None:
        if self.last_capture is not None:
            self._render(time.perf_counter())

    def _render(self, started: float) -> None:
        assert self.last_capture is not None
        screenshot = self.last_capture
        region = self.last_region or (0, 0, screenshot.shape[1], screenshot.shape[0])

        if not self.ranges:
            blank = np.zeros(screenshot.shape[:2], dtype=np.uint8)
            self._show(self.mask_label, cv2.cvtColor(blank, cv2.COLOR_GRAY2RGB), "mask")
            self._show(self.overlay_label, screenshot, "overlay")
            return

        mask = build_mask_from_ranges(screenshot, self.ranges)
        maximum = self.max_blob.get() or None
        blobs = blobs_from_mask(
            mask,
            origin=(region[0], region[1]),
            minimum_area_px=self.min_blob.get(),
            maximum_area_px=maximum,
        )

        overlay = screenshot.copy()
        for index, blob in enumerate(blobs, start=1):
            x1, y1 = blob.x - region[0], blob.y - region[1]
            x2, y2 = x1 + blob.width, y1 + blob.height
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (40, 220, 90), 2)
            cv2.putText(
                overlay,
                f"#{index}  {blob.area_px} px",
                (x1, max(16, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (40, 220, 90),
                1,
                cv2.LINE_AA,
            )
            safe_x, safe_y = blob.safe_point
            cv2.drawMarker(
                overlay,
                (safe_x - region[0], safe_y - region[1]),
                (255, 80, 180),
                cv2.MARKER_CROSS,
                12,
                1,
            )

        self._show(
            self.mask_label,
            cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB),
            "mask",
        )
        self._show(self.overlay_label, overlay, "overlay")

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        self.info.set(
            f"Bot {self.bot_id.get()} | {self.area.get()} | "
            f"kleurpixels {count_mask_pixels(mask)} | "
            f"componenten {count_mask_components(mask)} | geldig {len(blobs)} | "
            f"{elapsed_ms:.1f} ms | {1000.0 / max(elapsed_ms, 0.001):.1f} FPS"
        )

    def _show(self, label: ttk.Label, rgb: np.ndarray, key: str) -> None:
        height, width = rgb.shape[:2]
        target_width = max(300, label.winfo_width() or 620)
        target_height = max(180, label.winfo_height() or 360)
        scale = min(1.0, target_width / width, target_height / height)
        resized = cv2.resize(
            rgb,
            (max(1, int(width * scale)), max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_NEAREST,
        )
        photo = ImageTk.PhotoImage(Image.fromarray(resized))
        self.photos[key] = photo
        label.configure(image=photo)
        if key == "capture":
            self.capture_scale = scale

    def _close(self) -> None:
        self.running = False
        self.destroy()


def main() -> None:
    ColourTester().mainloop()


if __name__ == "__main__":
    main()
