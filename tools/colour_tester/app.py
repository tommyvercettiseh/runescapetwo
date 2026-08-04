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
    """Create colour presets with a pipette and inspect blobs live."""

    def __init__(self) -> None:
        super().__init__()
        self.title("RuneScape Two - Live Colour Tester")
        self.geometry("1380x880")
        self.minsize(1050, 700)

        self.running = True
        self.pipette_active = False
        self.current_ranges: tuple[HSVRange, ...] = ()
        self.sampled_hsv: tuple[int, int, int] | None = None
        self.last_capture: np.ndarray | None = None
        self.last_region: tuple[int, int, int, int] | None = None
        self._photos: dict[str, ImageTk.PhotoImage] = {}
        self._capture_scale = 1.0

        self.preset_name = tk.StringVar()
        self.area_name = tk.StringVar(value="game")
        self.bot_id = tk.IntVar(value=1)
        self.minimum_blob_px = tk.IntVar(value=20)
        self.maximum_blob_px = tk.IntVar(value=0)
        self.hue_tolerance = tk.IntVar(value=5)
        self.saturation_tolerance = tk.IntVar(value=40)
        self.value_tolerance = tk.IntVar(value=40)
        self.sample_radius = tk.IntVar(value=2)
        self.status = tk.StringVar(
            value="Kies een area, activeer het pipetje en klik op de markeerkleur."
        )
        self.range_text = tk.StringVar(value="Nog geen kleur geselecteerd")

        self._build_ui()
        self._refresh_sources()
        self._bind_live_controls()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._tick)

    def _build_ui(self) -> None:
        controls = ttk.Frame(self, padding=8)
        controls.pack(fill="x")

        ttk.Label(controls, text="Kleurpreset").grid(row=0, column=0, sticky="w")
        self.preset_box = ttk.Combobox(
            controls,
            textvariable=self.preset_name,
            width=28,
        )
        self.preset_box.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        self.preset_box.bind("<<ComboboxSelected>>", lambda _event: self._load_preset())

        ttk.Button(controls, text="Laden", command=self._load_preset).grid(
            row=1, column=1, padx=(0, 6)
        )
        ttk.Button(controls, text="Opslaan", command=self._save_preset).grid(
            row=1, column=2, padx=(0, 6)
        )
        ttk.Button(controls, text="Verwijderen", command=self._delete_preset).grid(
            row=1, column=3, padx=(0, 12)
        )

        ttk.Label(controls, text="Area").grid(row=0, column=4, sticky="w")
        self.area_box = ttk.Combobox(
            controls,
            textvariable=self.area_name,
            state="readonly",
            width=26,
        )
        self.area_box.grid(row=1, column=4, sticky="ew", padx=(0, 8))

        ttk.Label(controls, text="Bot").grid(row=0, column=5, sticky="w")
        ttk.Combobox(
            controls,
            textvariable=self.bot_id,
            values=(1, 2, 3, 4),
            state="readonly",
            width=5,
        ).grid(row=1, column=5, sticky="w", padx=(0, 8))

        self.pipette_button = ttk.Button(
            controls,
            text="Pipet activeren",
            command=self._toggle_pipette,
        )
        self.pipette_button.grid(row=1, column=6, padx=(0, 6))

        self.live_button = ttk.Button(
            controls,
            text="Pauze",
            command=self._toggle_live,
        )
        self.live_button.grid(row=1, column=7)

        controls.columnconfigure(0, weight=1)
        controls.columnconfigure(4, weight=1)

        settings = ttk.LabelFrame(self, text="Detectie", padding=8)
        settings.pack(fill="x", padx=8, pady=(0, 8))

        self._add_spinbox(
            settings,
            "Min blobpixels",
            self.minimum_blob_px,
            1,
            50000,
            0,
        )
        self._add_spinbox(
            settings,
            "Max blobpixels (0 = uit)",
            self.maximum_blob_px,
            0,
            100000,
            1,
        )
        self._add_spinbox(settings, "Hue tolerantie", self.hue_tolerance, 0, 40, 2)
        self._add_spinbox(
            settings,
            "Saturation tolerantie",
            self.saturation_tolerance,
            0,
            255,
            3,
        )
        self._add_spinbox(
            settings,
            "Value tolerantie",
            self.value_tolerance,
            0,
            255,
            4,
        )
        self._add_spinbox(settings, "Pipet radius", self.sample_radius, 0, 8, 5)

        ttk.Label(settings, textvariable=self.range_text).grid(
            row=2,
            column=0,
            columnspan=6,
            sticky="w",
            pady=(8, 0),
        )

        previews = ttk.Frame(self, padding=(8, 0, 8, 8))
        previews.pack(fill="both", expand=True)

        self.capture_label = self._preview_panel(
            previews,
            "LIVE CAPTURE — klik hier met het pipet",
            0,
            0,
        )
        self.mask_label = self._preview_panel(previews, "MASK", 0, 1)
        self.overlay_label = self._preview_panel(
            previews,
            "GELDIGE BLOBS + EXACTE PIXELTELLING",
            1,
            0,
            columnspan=2,
        )

        self.capture_label.bind("<Button-1>", self._pick_colour)
        for row in range(2):
            previews.rowconfigure(row, weight=1)
        for column in range(2):
            previews.columnconfigure(column, weight=1)

        ttk.Label(self, textvariable=self.status, padding=(10, 5)).pack(fill="x")

    def _add_spinbox(
        self,
        parent,
        label: str,
        variable: tk.IntVar,
        low: int,
        high: int,
        column: int,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=0, column=column, sticky="w", padx=4)
        ttk.Spinbox(
            parent,
            from_=low,
            to=high,
            textvariable=variable,
            width=12,
        ).grid(row=1, column=column, sticky="ew", padx=4)
        parent.columnconfigure(column, weight=1)

    def _preview_panel(
        self,
        parent,
        title: str,
        row: int,
        column: int,
        *,
        columnspan: int = 1,
    ) -> ttk.Label:
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

    def _bind_live_controls(self) -> None:
        for variable in (
            self.minimum_blob_px,
            self.maximum_blob_px,
            self.hue_tolerance,
            self.saturation_tolerance,
            self.value_tolerance,
            self.sample_radius,
        ):
            variable.trace_add("write", self._control_changed)

    def _control_changed(self, *_args) -> None:
        if self.sampled_hsv is not None:
            self.current_ranges = hsv_ranges_around(
                self.sampled_hsv,
                hue_tolerance=self.hue_tolerance.get(),
                saturation_tolerance=self.saturation_tolerance.get(),
                value_tolerance=self.value_tolerance.get(),
            )
            self._update_range_text()
        if self.last_capture is not None:
            self._render_detection(self.last_capture, self.last_region)

    def _refresh_sources(self) -> None:
        presets = list(list_colour_presets())
        areas = sorted(load_areas())
        self.preset_box["values"] = presets
        self.area_box["values"] = areas

        if areas and self.area_name.get() not in areas:
            self.area_name.set("game" if "game" in areas else areas[0])

    def _load_preset(self) -> None:
        name = self.preset_name.get().strip()
        if not name:
            return
        try:
            preset = load_colour_preset(name)
        except Exception as exc:
            self.status.set(str(exc))
            return

        self.preset_name.set(preset.name)
        self.current_ranges = preset.ranges
        self.sampled_hsv = None
        self._update_range_text()
        self.status.set(f"Preset '{preset.name}' geladen.")
        if self.last_capture is not None:
            self._render_detection(self.last_capture, self.last_region)

    def _save_preset(self) -> None:
        name = self.preset_name.get().strip()
        if not name:
            messagebox.showerror("Kleurpreset", "Geef de kleur een naam.")
            return
        if not self.current_ranges:
            messagebox.showerror(
                "Kleurpreset",
                "Gebruik eerst het pipet of laad een bestaande preset.",
            )
            return
        try:
            save_colour_preset(name, self.current_ranges)
            self.preset_name.set(name.strip().lower())
            self._refresh_sources()
            self.status.set(f"Preset '{self.preset_name.get()}' opgeslagen.")
        except Exception as exc:
            messagebox.showerror("Kleurpreset", str(exc))

    def _delete_preset(self) -> None:
        name = self.preset_name.get().strip()
        if not name:
            return
        if not messagebox.askyesno(
            "Kleurpreset",
            f"Preset '{name}' verwijderen?",
        ):
            return
        try:
            deleted = delete_colour_preset(name)
            if deleted:
                self.current_ranges = ()
                self.sampled_hsv = None
                self.preset_name.set("")
                self._refresh_sources()
                self._update_range_text()
                self.status.set("Preset verwijderd.")
        except Exception as exc:
            messagebox.showerror("Kleurpreset", str(exc))

    def _toggle_pipette(self) -> None:
        self.pipette_active = not self.pipette_active
        self.pipette_button.configure(
            text="Pipet actief — klik beeld"
            if self.pipette_active
            else "Pipet activeren"
        )
        self.capture_label.configure(cursor="crosshair" if self.pipette_active else "")

    def _pick_colour(self, event) -> None:
        if not self.pipette_active or self.last_capture is None:
            return

        x = int(event.x / max(self._capture_scale, 1e-9))
        y = int(event.y / max(self._capture_scale, 1e-9))
        height, width = self.last_capture.shape[:2]
        if not 0 <= x < width or not 0 <= y < height:
            return

        self.sampled_hsv = sample_hsv(
            self.last_capture,
            x,
            y,
            radius=self.sample_radius.get(),
        )
        self.current_ranges = hsv_ranges_around(
            self.sampled_hsv,
            hue_tolerance=self.hue_tolerance.get(),
            saturation_tolerance=self.saturation_tolerance.get(),
            value_tolerance=self.value_tolerance.get(),
        )
        self.pipette_active = False
        self.pipette_button.configure(text="Pipet activeren")
        self.capture_label.configure(cursor="")
        self._update_range_text()
        self._render_detection(self.last_capture, self.last_region)

    def _update_range_text(self) -> None:
        if not self.current_ranges:
            self.range_text.set("Nog geen kleur geselecteerd")
            return
        sample = f"Sample HSV {self.sampled_hsv} | " if self.sampled_hsv else ""
        ranges = " + ".join(
            f"{lower} → {upper}" for lower, upper in self.current_ranges
        )
        self.range_text.set(f"{sample}Ranges: {ranges}")

    def _toggle_live(self) -> None:
        self.running = not self.running
        self.live_button.configure(text="Pauze" if self.running else "Live")

    def _tick(self) -> None:
        if self.running:
            self._capture_and_render()
        self.after(100, self._tick)

    def _capture_and_render(self) -> None:
        area = self.area_name.get()
        if not area:
            return
        started = time.perf_counter()
        try:
            screenshot, region = capture_area(area, bot_id=self.bot_id.get())
            self.last_capture = screenshot
            self.last_region = region
            self._show(self.capture_label, screenshot, "capture")
            self._render_detection(screenshot, region, started=started)
        except Exception as exc:
            self.status.set(f"Fout: {exc}")
            self.running = False
            self.live_button.configure(text="Live")

    def _render_detection(
        self,
        screenshot: np.ndarray,
        region: tuple[int, int, int, int] | None,
        *,
        started: float | None = None,
    ) -> None:
        if not self.current_ranges:
            blank = np.zeros(screenshot.shape[:2], dtype=np.uint8)
            self._show(self.mask_label, cv2.cvtColor(blank, cv2.COLOR_GRAY2RGB), "mask")
            self._show(self.overlay_label, screenshot, "overlay")
            return

        started = time.perf_counter() if started is None else started
        mask = build_mask_from_ranges(screenshot, self.current_ranges)
        minimum = max(1, self.minimum_blob_px.get())
        maximum_value = max(0, self.maximum_blob_px.get())
        maximum = None if maximum_value == 0 else maximum_value
        blobs = blobs_from_mask(
            mask,
            minimum_area_px=minimum,
            maximum_area_px=maximum,
        )
        component_count = count_mask_components(mask)

        overlay = screenshot.copy()
        origin_x = region[0] if region else 0
        origin_y = region[1] if region else 0
        for index, blob in enumerate(blobs, start=1):
            x1 = blob.x - origin_x
            y1 = blob.y - origin_y
            x2 = x1 + blob.width
            y2 = y1 + blob.height
            cv2.rectangle(overlay, (x1, y1), (x2, y2), (40, 220, 90), 2)
            label = f"#{index}  {blob.area_px} px"
            cv2.putText(
                overlay,
                label,
                (x1, max(16, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (40, 220, 90),
                1,
                cv2.LINE_AA,
            )
            safe_x = blob.safe_point[0] - origin_x
            safe_y = blob.safe_point[1] - origin_y
            cv2.drawMarker(
                overlay,
                (safe_x, safe_y),
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
        fps = 1000.0 / elapsed_ms if elapsed_ms > 0 else 0.0
        self.status.set(
            f"Bot {self.bot_id.get()} | {self.area_name.get()} | "
            f"kleurpixels {count_mask_pixels(mask)} | "
            f"componenten {component_count} | geldig {len(blobs)} | "
            f"{elapsed_ms:.1f} ms | {fps:.1f} FPS"
        )

    def _show(self, label: ttk.Label, rgb: np.ndarray, key: str) -> None:
        source_height, source_width = rgb.shape[:2]
        target_width = max(300, label.winfo_width() or 620)
        target_height = max(180, label.winfo_height() or 360)
        scale = min(
            1.0,
            target_width / max(1, source_width),
            target_height / max(1, source_height),
        )
        size = (
            max(1, int(source_width * scale)),
            max(1, int(source_height * scale)),
        )
        resized = cv2.resize(
            rgb,
            size,
            interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_NEAREST,
        )
        photo = ImageTk.PhotoImage(Image.fromarray(resized))
        self._photos[key] = photo
        label.configure(image=photo)
        if key == "capture":
            self._capture_scale = scale

    def _close(self) -> None:
        self.running = False
        self.destroy()


def main() -> None:
    ColourTester().mainloop()


if __name__ == "__main__":
    main()
