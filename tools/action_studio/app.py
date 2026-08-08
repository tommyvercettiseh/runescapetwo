from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw, ImageTk

from core.vision.colour_detection import analyse_colour_image
from core.vision.colour_presets import list_colour_presets
from core.vision.screenshots import capture_area
from tools.action_studio.source_config import EditableField, read_editable_fields, update_literal


ROOT = Path(__file__).resolve().parents[2]
ACTIONS_ROOT = ROOT / "actions"
DEFINITIONS_ROOT = ROOT / "definitions"
SENSORS_ROOT = ROOT / "core" / "sensors"
AREAS_FILE = ROOT / "config" / "areas.json"
IMAGES_ROOT = ROOT / "assets" / "images"


class ActionStudio(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("RuneScape Studio")
        self.geometry("1120x760")
        self.minsize(900, 620)

        self.selected_path: Path | None = None
        self.fields: list[EditableField] = []
        self.inputs: dict[str, tk.Variable] = {}
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.item_paths: list[Path] = []

        self.search_var = tk.StringVar()
        self.bot_var = tk.IntVar(value=1)
        self.status_var = tk.StringVar(value="Kies links een action of sensor.")
        self.live_result_var = tk.StringVar(value="Nog niet gemeten")

        self._build_ui()
        self._refresh_items()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(0, weight=1)

        left = ttk.Frame(outer, padding=(0, 0, 12, 0))
        left.grid(row=0, column=0, sticky="nsew")
        left.rowconfigure(2, weight=1)

        ttk.Label(left, text="Zoeken").grid(row=0, column=0, sticky="w")
        search = ttk.Entry(left, textvariable=self.search_var, width=28)
        search.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        search.bind("<KeyRelease>", lambda _event: self._draw_items())

        self.item_list = tk.Listbox(left, width=34, exportselection=False)
        self.item_list.grid(row=2, column=0, sticky="nsew")
        self.item_list.bind("<<ListboxSelect>>", self._on_select)

        right = ttk.Frame(outer)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        header = ttk.Frame(right)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)

        self.kind_label = ttk.Label(header, text="")
        self.kind_label.grid(row=0, column=0, sticky="w")
        self.title_label = ttk.Label(header, text="Selecteer iets", font=("Segoe UI", 18, "bold"))
        self.title_label.grid(row=1, column=0, sticky="w")

        ttk.Label(header, text="Bot").grid(row=0, column=1, rowspan=2, padx=(8, 4))
        ttk.Spinbox(header, from_=1, to=4, textvariable=self.bot_var, width=4).grid(
            row=0, column=2, rowspan=2
        )

        self.settings_box = ttk.LabelFrame(right, text="Instellingen", padding=12)
        self.settings_box.grid(row=1, column=0, sticky="ew")
        self.settings_box.columnconfigure(1, weight=1)

        self.content = ttk.Frame(right)
        self.content.grid(row=2, column=0, sticky="nsew", pady=(10, 0))
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.live_box = ttk.LabelFrame(self.content, text="Live controleren", padding=12)
        self.live_box.grid(row=0, column=0, sticky="nsew")
        self.live_box.columnconfigure(0, weight=1)
        self.live_box.rowconfigure(1, weight=1)

        live_top = ttk.Frame(self.live_box)
        live_top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        live_top.columnconfigure(1, weight=1)
        self.live_button = ttk.Button(live_top, text="Meet live", command=self._measure_live)
        self.live_button.grid(row=0, column=0, sticky="w")
        ttk.Label(live_top, textvariable=self.live_result_var).grid(
            row=0, column=1, sticky="w", padx=(10, 0)
        )

        preview_wrap = ttk.Frame(self.live_box)
        preview_wrap.grid(row=1, column=0, sticky="nsew")
        preview_wrap.columnconfigure(0, weight=3)
        preview_wrap.columnconfigure(1, weight=1)
        preview_wrap.rowconfigure(0, weight=1)

        self.preview_label = ttk.Label(preview_wrap, anchor="center", text="Preview verschijnt hier")
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        side = ttk.Frame(preview_wrap)
        side.grid(row=0, column=1, sticky="nsew")
        ttk.Label(side, text="Gevonden groottes", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.blob_list = tk.Listbox(side, height=12, exportselection=False)
        self.blob_list.pack(fill="both", expand=True, pady=(6, 8))
        self.use_smallest_button = ttk.Button(
            side,
            text="Gebruik kleinste als minimum",
            command=self._use_smallest,
            state="disabled",
        )
        self.use_smallest_button.pack(fill="x", pady=(0, 5))
        self.use_largest_button = ttk.Button(
            side,
            text="Gebruik grootste als maximum",
            command=self._use_largest,
            state="disabled",
        )
        self.use_largest_button.pack(fill="x")

        footer = ttk.Frame(right)
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        ttk.Button(footer, text="Opnieuw laden", command=self._reload_selected).grid(
            row=0, column=1, padx=(8, 0)
        )
        self.save_button = ttk.Button(footer, text="Opslaan", command=self._save, state="disabled")
        self.save_button.grid(row=0, column=2, padx=(8, 0))

    def _refresh_items(self) -> None:
        paths: list[Path] = []
        for root in (ACTIONS_ROOT, DEFINITIONS_ROOT, SENSORS_ROOT):
            if not root.exists():
                continue
            paths.extend(
                path
                for path in root.rglob("*.py")
                if path.name != "__init__.py" and "__pycache__" not in path.parts
            )
        self.item_paths = sorted(paths, key=lambda p: str(p.relative_to(ROOT)).casefold())
        self._draw_items()

    def _display_name(self, path: Path) -> str:
        relative = path.relative_to(ROOT)
        if relative.parts[0] == "actions":
            icon = "ACTION"
        elif relative.parts[0] == "definitions":
            icon = "SENSOR"
        else:
            icon = "SENSOR"
        group = relative.parent.name.replace("_", " ").upper()
        return f"{group:14}  {path.stem}   [{icon}]"

    def _draw_items(self) -> None:
        query = self.search_var.get().strip().casefold()
        self.item_list.delete(0, "end")
        self.visible_paths: list[Path] = []
        for path in self.item_paths:
            haystack = str(path.relative_to(ROOT)).casefold()
            if query and query not in haystack:
                continue
            self.visible_paths.append(path)
            self.item_list.insert("end", self._display_name(path))

    def _on_select(self, _event=None) -> None:
        selection = self.item_list.curselection()
        if not selection:
            return
        self._load_path(self.visible_paths[int(selection[0])])

    def _load_path(self, path: Path) -> None:
        self.selected_path = path
        try:
            self.fields = read_editable_fields(path)
        except (OSError, SyntaxError) as exc:
            messagebox.showerror("Openen mislukt", str(exc), parent=self)
            return

        relative = path.relative_to(ROOT)
        self.kind_label.configure(text="ACTION" if relative.parts[0] == "actions" else "SENSOR")
        self.title_label.configure(text=path.stem)
        self.status_var.set(str(relative))
        self._draw_settings()
        self._reset_live()

    def _draw_settings(self) -> None:
        for child in self.settings_box.winfo_children():
            child.destroy()
        self.inputs.clear()

        if not self.fields:
            ttk.Label(
                self.settings_box,
                text="Hier zijn nog geen simpele instellingen gevonden. De Python-logica blijft ongemoeid.",
            ).grid(row=0, column=0, columnspan=2, sticky="w")
            self.save_button.configure(state="disabled")
            return

        for row, field in enumerate(self.fields):
            label = field.label + (f" ({field.unit})" if field.unit else "")
            ttk.Label(self.settings_box, text=label).grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=4
            )

            var: tk.Variable
            widget: tk.Widget
            if field.kind == "colour":
                var = tk.StringVar(value=str(field.value))
                widget = ttk.Combobox(
                    self.settings_box,
                    textvariable=var,
                    values=list_colour_presets(),
                    state="readonly",
                )
            elif field.kind == "area":
                var = tk.StringVar(value=str(field.value))
                widget = ttk.Combobox(
                    self.settings_box,
                    textvariable=var,
                    values=self._area_names(),
                    state="readonly",
                )
            elif field.kind == "image":
                var = tk.StringVar(value=str(field.value))
                widget = ttk.Combobox(
                    self.settings_box,
                    textvariable=var,
                    values=self._image_names(),
                )
            elif field.kind == "choice":
                var = tk.StringVar(value=str(field.value))
                widget = ttk.Combobox(
                    self.settings_box,
                    textvariable=var,
                    values=("left", "right"),
                    state="readonly",
                )
            else:
                var = tk.StringVar(value=str(field.value))
                widget = ttk.Entry(self.settings_box, textvariable=var)

            widget.grid(row=row, column=1, sticky="ew", pady=4)
            self.inputs[field.name] = var

        self.save_button.configure(state="normal")

    def _area_names(self) -> tuple[str, ...]:
        try:
            raw = json.loads(AREAS_FILE.read_text(encoding="utf-8-sig"))
            return tuple(sorted(raw)) if isinstance(raw, dict) else ()
        except (OSError, json.JSONDecodeError):
            return ()

    def _image_names(self) -> tuple[str, ...]:
        return tuple(sorted(path.stem for path in IMAGES_ROOT.glob("*.png")))

    def _field_by_kind(self, kind: str) -> EditableField | None:
        return next((field for field in self.fields if field.kind == kind), None)

    def _current_value(self, field: EditableField):
        raw = self.inputs[field.name].get()
        if field.kind == "int":
            return int(raw)
        if field.kind == "float":
            return float(raw)
        return str(raw)

    def _save(self) -> None:
        path = self.selected_path
        if path is None:
            return
        try:
            for field in self.fields:
                value = self._current_value(field)
                update_literal(path, field.name, value)
        except (ValueError, OSError, KeyError) as exc:
            messagebox.showerror("Niet opgeslagen", str(exc), parent=self)
            return
        self.status_var.set(f"Opgeslagen: {path.relative_to(ROOT)}")
        self._load_path(path)

    def _reload_selected(self) -> None:
        if self.selected_path is not None:
            self._load_path(self.selected_path)

    def _reset_live(self) -> None:
        self.live_result_var.set("Nog niet gemeten")
        self.preview_label.configure(image="", text="Klik op ‘Meet live’")
        self.preview_photo = None
        self.blob_list.delete(0, "end")
        self.live_blob_sizes: list[int] = []
        self.use_smallest_button.configure(state="disabled")
        self.use_largest_button.configure(state="disabled")

        has_colour = self._field_by_kind("colour") is not None and self._field_by_kind("area") is not None
        self.live_button.configure(state="normal" if has_colour else "disabled")
        if not has_colour:
            self.live_result_var.set("Live blobmeting is alleen nodig bij kleuracties.")

    def _measure_live(self) -> None:
        colour_field = self._field_by_kind("colour")
        area_field = self._field_by_kind("area")
        if colour_field is None or area_field is None:
            return

        try:
            colour = str(self._current_value(colour_field))
            area = str(self._current_value(area_field))
            screenshot, region = capture_area(area, bot_id=int(self.bot_var.get()))
            mask, all_blobs, total_pixels = analyse_colour_image(
                screenshot,
                colour,
                origin=(region[0], region[1]),
                minimum_area_px=1,
                maximum_area_px=None,
            )
        except Exception as exc:
            messagebox.showerror("Live meten mislukt", str(exc), parent=self)
            return

        min_field = next((f for f in self.fields if f.name.endswith("_MIN_PIXELS")), None)
        max_field = next((f for f in self.fields if f.name.endswith("_MAX_PIXELS")), None)
        minimum = int(self._current_value(min_field)) if min_field else 1
        maximum = int(self._current_value(max_field)) if max_field else None

        valid = [
            blob for blob in all_blobs
            if blob.area_px >= minimum and (maximum is None or blob.area_px <= maximum)
        ]
        self.live_blob_sizes = sorted((blob.area_px for blob in all_blobs))

        self.blob_list.delete(0, "end")
        for blob in sorted(all_blobs, key=lambda b: b.area_px):
            marker = "✓" if blob in valid else "×"
            self.blob_list.insert("end", f"{marker}  {blob.area_px} px")

        self.live_result_var.set(
            f"{len(valid)} geldig · {len(all_blobs)} gevonden · {total_pixels} kleurpixels totaal"
        )
        self._show_preview(screenshot, region, all_blobs, valid)
        state = "normal" if self.live_blob_sizes else "disabled"
        if min_field:
            self.use_smallest_button.configure(state=state)
        if max_field:
            self.use_largest_button.configure(state=state)

    def _show_preview(self, screenshot, region, blobs, valid) -> None:
        image = Image.fromarray(screenshot).convert("RGB")
        draw = ImageDraw.Draw(image)
        valid_ids = {id(blob) for blob in valid}
        origin_x, origin_y = region[0], region[1]

        for blob in blobs:
            x1 = blob.x - origin_x
            y1 = blob.y - origin_y
            x2 = x1 + blob.width
            y2 = y1 + blob.height
            width = 3 if id(blob) in valid_ids else 1
            draw.rectangle((x1, y1, x2, y2), outline="lime" if id(blob) in valid_ids else "white", width=width)
            draw.text((x1 + 3, y1 + 3), f"{blob.area_px}px", fill="lime" if id(blob) in valid_ids else "white")

        max_width, max_height = 720, 430
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(image)
        self.preview_label.configure(image=self.preview_photo, text="")

    def _use_smallest(self) -> None:
        field = next((f for f in self.fields if f.name.endswith("_MIN_PIXELS")), None)
        if field is None or not self.live_blob_sizes:
            return
        self.inputs[field.name].set(str(self.live_blob_sizes[0]))
        self.live_result_var.set("Minimum overgenomen. Meet opnieuw om het effect te zien.")

    def _use_largest(self) -> None:
        field = next((f for f in self.fields if f.name.endswith("_MAX_PIXELS")), None)
        if field is None or not self.live_blob_sizes:
            return
        self.inputs[field.name].set(str(self.live_blob_sizes[-1]))
        self.live_result_var.set("Maximum overgenomen. Meet opnieuw om het effect te zien.")


def main() -> None:
    app = ActionStudio()
    app.mainloop()


if __name__ == "__main__":
    main()
