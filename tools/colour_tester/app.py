from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk

from core.vision.areas import AREAS_FILE, get_area, load_areas
from core.vision.colour_detection import blobs_from_mask
from core.vision.offsets import apply_offset, get_bot_offset
from core.vision.screenshots import capture_rgb

BG = "#080d18"
PANEL = "#111827"
PANEL_2 = "#172033"
TEXT = "#f6f7fb"
MUTED = "#9aa6bd"
BLUE = "#2f7df6"
GREEN = "#2bbf6a"
PURPLE = "#8b45e6"
BORDER = "#29354c"


class ColourTesterApp:
    """Live HSV tester using the same area and offset model as core.vision."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("RuneScape Two - Colour Tester")
        self.root.geometry("1450x900")
        self.root.minsize(1150, 720)
        self.root.configure(bg=BG)

        self.bot_id = tk.IntVar(value=1)
        self.area_name = tk.StringVar(value="game")
        self.selected_colour = tk.StringVar(value="custom")
        self.live = tk.BooleanVar(value=True)
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.mask_photo: ImageTk.PhotoImage | None = None
        self.overlay_photo: ImageTk.PhotoImage | None = None
        self.last_capture: np.ndarray | None = None
        self.last_mask: np.ndarray | None = None
        self.last_blobs = []

        self.h_min = tk.IntVar(value=135)
        self.h_max = tk.IntVar(value=169)
        self.s_min = tk.IntVar(value=50)
        self.s_max = tk.IntVar(value=255)
        self.v_min = tk.IntVar(value=40)
        self.v_max = tk.IntVar(value=255)
        self.erode = tk.IntVar(value=0)
        self.dilate = tk.IntVar(value=0)
        self.min_area = tk.IntVar(value=20)
        self.max_area = tk.IntVar(value=10000)
        self.click_padding = tk.IntVar(value=3)

        self.x_var = tk.IntVar(value=0)
        self.y_var = tk.IntVar(value=0)
        self.w_var = tk.IntVar(value=640)
        self.h_var = tk.IntVar(value=480)

        self._build()
        self._load_area_into_editor()
        self.root.after(100, self._tick)

    def _button(self, parent, text, command, bg=PANEL_2, **kwargs):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=TEXT,
            activebackground=bg,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            **kwargs,
        )

    def _build(self) -> None:
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=14, pady=12)

        header = tk.Frame(shell, bg=BG)
        header.pack(fill="x", pady=(0, 10))
        tk.Label(header, text="Colour Tester", bg=BG, fg=TEXT, font=("Segoe UI", 24, "bold")).pack(side="left")
        tk.Checkbutton(
            header,
            text="Live vernieuwen",
            variable=self.live,
            bg=BG,
            fg=TEXT,
            selectcolor=PANEL,
            activebackground=BG,
        ).pack(side="right")

        body = tk.Frame(shell, bg=BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = tk.Frame(body, bg=PANEL, width=260, highlightbackground=BORDER, highlightthickness=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_propagate(False)
        center = tk.Frame(body, bg=BG)
        center.grid(row=0, column=1, sticky="nsew", padx=8)
        center.grid_columnconfigure(0, weight=1)
        center.grid_rowconfigure(0, weight=3)
        center.grid_rowconfigure(1, weight=2)
        right = tk.Frame(body, bg=PANEL, width=320, highlightbackground=BORDER, highlightthickness=1)
        right.grid(row=0, column=2, sticky="nsew", padx=(8, 0))
        right.grid_propagate(False)

        self._build_left(left)
        self._build_center(center)
        self._build_right(right)

    def _build_left(self, parent) -> None:
        tk.Label(parent, text="BOT", bg=PANEL, fg=BLUE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(14, 8))
        bot_row = tk.Frame(parent, bg=PANEL)
        bot_row.pack(fill="x", padx=12)
        for bot_id in range(1, 5):
            tk.Radiobutton(
                bot_row,
                text=str(bot_id),
                variable=self.bot_id,
                value=bot_id,
                command=self.refresh,
                indicatoron=False,
                width=4,
                bg=PANEL_2,
                fg=TEXT,
                selectcolor=GREEN,
                activebackground=PANEL_2,
            ).pack(side="left", padx=2)

        tk.Label(parent, text="AREA", bg=PANEL, fg=BLUE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(18, 8))
        self.area_box = ttk.Combobox(parent, textvariable=self.area_name, values=self._area_names(), state="readonly")
        self.area_box.pack(fill="x", padx=14)
        self.area_box.bind("<<ComboboxSelected>>", lambda _e: self._area_changed())

        form = tk.Frame(parent, bg=PANEL)
        form.pack(fill="x", padx=14, pady=12)
        for index, (label, variable) in enumerate((('X', self.x_var), ('Y', self.y_var), ('W', self.w_var), ('H', self.h_var))):
            box = tk.Frame(form, bg=PANEL)
            box.grid(row=index // 2, column=index % 2, sticky="ew", padx=3, pady=3)
            tk.Label(box, text=label, bg=PANEL, fg=MUTED).pack(anchor="w")
            tk.Entry(box, textvariable=variable, bg=PANEL_2, fg=TEXT, insertbackground=TEXT, relief="flat", width=9).pack(fill="x")
        form.grid_columnconfigure(0, weight=1)
        form.grid_columnconfigure(1, weight=1)

        self._button(parent, "Area opslaan", self.save_area, bg=GREEN, pady=9).pack(fill="x", padx=14, pady=(0, 6))
        self._button(parent, "Capture vernieuwen", self.refresh, bg=BLUE, pady=9).pack(fill="x", padx=14)

        tk.Label(parent, text="INFO", bg=PANEL, fg=BLUE, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=14, pady=(20, 8))
        self.info_label = tk.Label(parent, text="", bg=PANEL, fg=MUTED, justify="left", anchor="nw", wraplength=225)
        self.info_label.pack(fill="x", padx=14)

    def _build_center(self, parent) -> None:
        capture_panel = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        capture_panel.grid(row=0, column=0, sticky="nsew")
        tk.Label(capture_panel, text="LIVE CAPTURE", bg=PANEL, fg=TEXT, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 4))
        self.capture_label = tk.Label(capture_panel, bg="#050914")
        self.capture_label.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        previews = tk.Frame(parent, bg=BG)
        previews.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        previews.grid_columnconfigure((0, 1), weight=1)
        previews.grid_rowconfigure(0, weight=1)
        self.mask_label = self._preview_panel(previews, "MASK", 0)
        self.overlay_label = self._preview_panel(previews, "BLOBS + KLIKPUNT", 1)

    def _preview_panel(self, parent, title: str, column: int):
        panel = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        panel.grid(row=0, column=column, sticky="nsew", padx=(0, 5) if column == 0 else (5, 0))
        tk.Label(panel, text=title, bg=PANEL, fg=TEXT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(8, 3))
        label = tk.Label(panel, bg="#050914")
        label.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        return label

    def _build_right(self, parent) -> None:
        tk.Label(parent, text="HSV RANGE", bg=PANEL, fg=PURPLE, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(14, 8))
        for label, variable, maximum in (
            ("Hue min", self.h_min, 179), ("Hue max", self.h_max, 179),
            ("Saturation min", self.s_min, 255), ("Saturation max", self.s_max, 255),
            ("Value min", self.v_min, 255), ("Value max", self.v_max, 255),
        ):
            row = tk.Frame(parent, bg=PANEL)
            row.pack(fill="x", padx=14, pady=2)
            tk.Label(row, text=label, bg=PANEL, fg=MUTED, width=16, anchor="w").pack(side="left")
            tk.Scale(row, from_=0, to=maximum, orient="horizontal", variable=variable, command=lambda _v: self.refresh(), bg=PANEL, fg=TEXT, troughcolor=PANEL_2, highlightthickness=0, length=130).pack(side="right")

        tk.Label(parent, text="BLOB FILTERS", bg=PANEL, fg=PURPLE, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(16, 8))
        for label, variable, low, high in (
            ("Erode", self.erode, 0, 8), ("Dilate", self.dilate, 0, 8),
            ("Min area", self.min_area, 0, 5000), ("Max area", self.max_area, 10, 50000),
            ("Click padding", self.click_padding, 0, 30),
        ):
            row = tk.Frame(parent, bg=PANEL)
            row.pack(fill="x", padx=14, pady=2)
            tk.Label(row, text=label, bg=PANEL, fg=MUTED, width=14, anchor="w").pack(side="left")
            tk.Spinbox(row, from_=low, to=high, textvariable=variable, width=8, command=self.refresh, bg=PANEL_2, fg=TEXT, buttonbackground=PANEL_2, relief="flat").pack(side="right")

        self._button(parent, "Detect colour", self.refresh, bg=GREEN, pady=10).pack(fill="x", padx=14, pady=(18, 6))
        self._button(parent, "Preset opslaan", self.save_preset, bg=PURPLE, pady=10).pack(fill="x", padx=14)

        tk.Label(parent, text="RESULTAAT", bg=PANEL, fg=PURPLE, font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=14, pady=(18, 8))
        self.result_label = tk.Label(parent, text="Nog niet gedetecteerd", bg=PANEL, fg=MUTED, justify="left", anchor="nw", wraplength=285)
        self.result_label.pack(fill="x", padx=14)

    def _area_names(self) -> list[str]:
        return [name for name, value in load_areas().items() if isinstance(value, dict)]

    def _area_changed(self) -> None:
        self._load_area_into_editor()
        self.refresh()

    def _load_area_into_editor(self) -> None:
        try:
            area = get_area(self.area_name.get())
        except Exception:
            return
        if area:
            self.x_var.set(area[0]); self.y_var.set(area[1]); self.w_var.set(area[2]); self.h_var.set(area[3])

    def _current_region(self):
        local = (self.x_var.get(), self.y_var.get(), self.w_var.get(), self.h_var.get())
        return apply_offset(local, get_bot_offset(self.bot_id.get()))

    def _make_mask(self, rgb: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        lower = np.array((self.h_min.get(), self.s_min.get(), self.v_min.get()), dtype=np.uint8)
        upper = np.array((self.h_max.get(), self.s_max.get(), self.v_max.get()), dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)
        if self.erode.get() > 0:
            k = self.erode.get() * 2 + 1
            mask = cv2.erode(mask, np.ones((k, k), np.uint8), iterations=1)
        if self.dilate.get() > 0:
            k = self.dilate.get() * 2 + 1
            mask = cv2.dilate(mask, np.ones((k, k), np.uint8), iterations=1)
        return mask

    def refresh(self) -> None:
        try:
            region = self._current_region()
            rgb = capture_rgb(region)
            mask = self._make_mask(rgb)
            origin = (region[0], region[1])
            blobs = blobs_from_mask(mask, origin=origin, minimum_area_px=self.min_area.get(), maximum_area_px=self.max_area.get())
            overlay = rgb.copy()
            for index, blob in enumerate(blobs):
                x1, y1 = blob.x - origin[0], blob.y - origin[1]
                x2, y2 = x1 + blob.width, y1 + blob.height
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (40, 220, 90), 2)
                cv2.putText(overlay, str(index + 1), (x1, max(14, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
            click_point = None
            if blobs:
                click_point = blobs[0].random_point(self.click_padding.get())
                cx, cy = click_point[0] - origin[0], click_point[1] - origin[1]
                cv2.drawMarker(overlay, (cx, cy), (255, 80, 180), cv2.MARKER_CROSS, 18, 2)

            self.last_capture, self.last_mask, self.last_blobs = rgb, mask, blobs
            self._show(self.capture_label, rgb, "preview_photo")
            self._show(self.mask_label, cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB), "mask_photo")
            self._show(self.overlay_label, overlay, "overlay_photo")
            offset = get_bot_offset(self.bot_id.get())
            self.info_label.config(text=f"Bot: {self.bot_id.get()}\nOffset: {offset}\nLokale area: {(self.x_var.get(), self.y_var.get(), self.w_var.get(), self.h_var.get())}\nAbsolute area: {region}")
            best = blobs[0] if blobs else None
            self.result_label.config(text=(f"Blobs: {len(blobs)}\nBeste area: {best.area_px:.0f}px\nCentroid: {best.center}\nKlikpunt: {click_point}" if best else "Geen geldige blobs gevonden"))
        except Exception as exc:
            self.result_label.config(text=f"Fout: {exc}")

    def _show(self, label: tk.Label, rgb: np.ndarray, attr: str) -> None:
        max_w = max(240, label.winfo_width() or 640)
        max_h = max(160, label.winfo_height() or 360)
        image = Image.fromarray(rgb)
        image.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        setattr(self, attr, photo)
        label.config(image=photo)

    def save_area(self) -> None:
        name = self.area_name.get().strip()
        if not name:
            messagebox.showerror("Area", "Kies een area.")
            return
        data = load_areas()
        data[name] = {"x": self.x_var.get(), "y": self.y_var.get(), "width": self.w_var.get(), "height": self.h_var.get()}
        AREAS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        messagebox.showinfo("Area", f"Area '{name}' opgeslagen.")

    def save_preset(self) -> None:
        path = Path(__file__).resolve().parents[2] / "config" / "colour_presets.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        name = self.selected_colour.get().strip() or "custom"
        data[name] = {
            "lower": [self.h_min.get(), self.s_min.get(), self.v_min.get()],
            "upper": [self.h_max.get(), self.s_max.get(), self.v_max.get()],
            "erode_px": self.erode.get(), "dilate_px": self.dilate.get(),
            "minimum_area_px": self.min_area.get(), "maximum_area_px": self.max_area.get(),
            "click_padding_px": self.click_padding.get(),
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        messagebox.showinfo("Preset", f"Preset '{name}' opgeslagen.")

    def _tick(self) -> None:
        if self.live.get():
            self.refresh()
        self.root.after(500, self._tick)


def main() -> None:
    root = tk.Tk()
    ColourTesterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
