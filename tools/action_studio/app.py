from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw

from core.vision.api import find_image
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

BG = ("#F4F6F8", "#111418")
CARD = ("#FFFFFF", "#1B2026")
CARD_ALT = ("#F8FAFC", "#20262D")
BORDER = ("#DDE3EA", "#313943")
TEXT = ("#111827", "#F3F4F6")
MUTED = ("#64748B", "#9CA3AF")
ACCENT = "#2563EB"
SUCCESS = "#16A34A"
DANGER = "#DC2626"


class ActionStudio(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title("RuneScape Studio")
        self.geometry("1220x800")
        self.minsize(980, 650)
        self.configure(fg_color=BG)

        self.selected_path: Path | None = None
        self.fields: list[EditableField] = []
        self.inputs: dict[str, tk.Variable] = {}
        self.preview_image: ctk.CTkImage | None = None
        self.item_paths: list[Path] = []
        self.visible_paths: list[Path] = []
        self.live_blob_sizes: list[int] = []
        self.item_buttons: list[ctk.CTkButton] = []
        self.field_widgets: dict[str, object] = {}
        self.combo_values: dict[str, tuple[str, ...]] = {}

        self.search_var = tk.StringVar()
        self.bot_var = tk.IntVar(value=1)
        self.status_var = tk.StringVar(value="Kies links een action of sensor.")
        self.live_result_var = tk.StringVar(value="Nog niet gemeten")

        self._build_ui()
        self._refresh_items()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self,
            width=270,
            corner_radius=0,
            fg_color=CARD,
            border_width=0,
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(3, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="RuneScape Studio",
            font=ctk.CTkFont(size=19, weight="bold"),
            text_color=TEXT,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 4))

        ctk.CTkLabel(
            self.sidebar,
            text="Actions & sensors",
            font=ctk.CTkFont(size=12),
            text_color=MUTED,
            anchor="w",
        ).grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))

        self.search_entry = ctk.CTkEntry(
            self.sidebar,
            textvariable=self.search_var,
            placeholder_text="Zoek bijvoorbeeld bank of click...",
            height=38,
            corner_radius=10,
            border_color=BORDER,
        )
        self.search_entry.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
        self.search_var.trace_add("write", lambda *_: self._draw_items())

        self.item_frame = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            corner_radius=0,
        )
        self.item_frame.grid(row=3, column=0, sticky="nsew", padx=(8, 4), pady=(0, 12))
        self.item_frame.grid_columnconfigure(0, weight=1)

        main = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew", padx=18, pady=16)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        self.kind_label = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=ACCENT,
            anchor="w",
        )
        self.kind_label.grid(row=0, column=0, sticky="w")

        self.title_label = ctk.CTkLabel(
            header,
            text="Selecteer iets",
            font=ctk.CTkFont(size=25, weight="bold"),
            text_color=TEXT,
            anchor="w",
        )
        self.title_label.grid(row=1, column=0, sticky="w", pady=(1, 0))

        bot_wrap = ctk.CTkFrame(header, fg_color=CARD, corner_radius=10, border_width=1, border_color=BORDER)
        bot_wrap.grid(row=0, column=1, rowspan=2, sticky="e")
        ctk.CTkLabel(bot_wrap, text="Bot", text_color=MUTED).pack(side="left", padx=(12, 6), pady=8)
        self.bot_menu = ctk.CTkOptionMenu(
            bot_wrap,
            variable=self.bot_var,
            values=["1", "2", "3", "4"],
            width=64,
            height=30,
            corner_radius=8,
        )
        self.bot_menu.pack(side="left", padx=(0, 8), pady=6)

        self.settings_card = ctk.CTkFrame(
            main,
            fg_color=CARD,
            corner_radius=14,
            border_width=1,
            border_color=BORDER,
        )
        self.settings_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self.settings_card.grid_columnconfigure(0, weight=1)

        settings_head = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        settings_head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        ctk.CTkLabel(
            settings_head,
            text="Instellingen",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=TEXT,
        ).pack(side="left")
        ctk.CTkLabel(
            settings_head,
            text="Pas alleen aan wat je nodig hebt",
            font=ctk.CTkFont(size=12),
            text_color=MUTED,
        ).pack(side="left", padx=(10, 0))

        self.settings_box = ctk.CTkFrame(self.settings_card, fg_color="transparent")
        self.settings_box.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.settings_box.grid_columnconfigure(1, weight=1)

        self.live_card = ctk.CTkFrame(
            main,
            fg_color=CARD,
            corner_radius=14,
            border_width=1,
            border_color=BORDER,
        )
        self.live_card.grid(row=2, column=0, sticky="nsew")
        self.live_card.grid_columnconfigure(0, weight=1)
        self.live_card.grid_rowconfigure(1, weight=1)

        live_head = ctk.CTkFrame(self.live_card, fg_color="transparent")
        live_head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 10))
        live_head.grid_columnconfigure(1, weight=1)

        self.live_button = ctk.CTkButton(
            live_head,
            text="Meet live",
            command=self._measure_live,
            width=105,
            height=34,
            corner_radius=9,
            font=ctk.CTkFont(weight="bold"),
        )
        self.live_button.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            live_head,
            textvariable=self.live_result_var,
            text_color=MUTED,
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", padx=(12, 0))

        live_body = ctk.CTkFrame(self.live_card, fg_color="transparent")
        live_body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
        live_body.grid_columnconfigure(0, weight=3)
        live_body.grid_columnconfigure(1, weight=1)
        live_body.grid_rowconfigure(0, weight=1)

        self.preview_panel = ctk.CTkFrame(
            live_body,
            fg_color=CARD_ALT,
            corner_radius=12,
            border_width=1,
            border_color=BORDER,
        )
        self.preview_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        self.preview_panel.grid_columnconfigure(0, weight=1)
        self.preview_panel.grid_rowconfigure(0, weight=1)

        self.preview_label = ctk.CTkLabel(
            self.preview_panel,
            text="Preview verschijnt hier",
            text_color=MUTED,
            anchor="center",
        )
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        side = ctk.CTkFrame(
            live_body,
            fg_color=CARD_ALT,
            corner_radius=12,
            border_width=1,
            border_color=BORDER,
        )
        side.grid(row=0, column=1, sticky="nsew")
        side.grid_columnconfigure(0, weight=1)
        side.grid_rowconfigure(1, weight=1)

        self.found_title = ctk.CTkLabel(
            side,
            text="Gevonden groottes",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=TEXT,
            anchor="w",
        )
        self.found_title.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 8))

        self.result_text = ctk.CTkTextbox(
            side,
            corner_radius=9,
            border_width=1,
            border_color=BORDER,
            fg_color=CARD,
            wrap="none",
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.result_text.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.result_text.configure(state="disabled")

        self.use_smallest_button = ctk.CTkButton(
            side,
            text="Gebruik kleinste als minimum",
            command=self._use_smallest,
            height=32,
            corner_radius=8,
            state="disabled",
            fg_color=("#E8EEF8", "#293241"),
            text_color=TEXT,
            hover_color=("#DCE6F5", "#344154"),
        )
        self.use_smallest_button.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 6))

        self.use_largest_button = ctk.CTkButton(
            side,
            text="Gebruik grootste als maximum",
            command=self._use_largest,
            height=32,
            corner_radius=8,
            state="disabled",
            fg_color=("#E8EEF8", "#293241"),
            text_color=TEXT,
            hover_color=("#DCE6F5", "#344154"),
        )
        self.use_largest_button.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))

        footer = ctk.CTkFrame(main, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        footer.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            footer,
            textvariable=self.status_var,
            text_color=MUTED,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            footer,
            text="Opnieuw laden",
            command=self._reload_selected,
            width=110,
            height=34,
            corner_radius=9,
            fg_color=("#E5E7EB", "#2A3038"),
            text_color=TEXT,
            hover_color=("#D1D5DB", "#353C46"),
        ).grid(row=0, column=1, padx=(8, 0))

        self.save_button = ctk.CTkButton(
            footer,
            text="Opslaan",
            command=self._save,
            state="disabled",
            width=100,
            height=34,
            corner_radius=9,
            font=ctk.CTkFont(weight="bold"),
        )
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

    def _draw_items(self) -> None:
        for button in self.item_buttons:
            button.destroy()
        self.item_buttons.clear()

        query = self.search_var.get().strip().casefold()
        self.visible_paths = []
        last_group = None
        row = 0

        for path in self.item_paths:
            relative = path.relative_to(ROOT)
            group = relative.parent.name.replace("_", " ").upper()
            kind = "ACTION" if relative.parts[0] == "actions" else "SENSOR"
            haystack = f"{group} {path.stem} {kind} {relative}".casefold()
            if query and query not in haystack:
                continue

            if group != last_group:
                label = ctk.CTkLabel(
                    self.item_frame,
                    text=group,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=MUTED,
                    anchor="w",
                )
                label.grid(row=row, column=0, sticky="ew", padx=8, pady=(10 if row else 2, 4))
                self.item_buttons.append(label)
                row += 1
                last_group = group

            prefix = "●" if kind == "ACTION" else "○"
            button = ctk.CTkButton(
                self.item_frame,
                text=f"{prefix}  {path.stem}",
                command=lambda p=path: self._load_path(p),
                anchor="w",
                height=34,
                corner_radius=8,
                fg_color="transparent",
                text_color=TEXT,
                hover_color=("#E8EEF8", "#293241"),
                font=ctk.CTkFont(size=13),
            )
            button.grid(row=row, column=0, sticky="ew", padx=3, pady=1)
            self.item_buttons.append(button)
            self.visible_paths.append(path)
            row += 1

    def _load_path(self, path: Path) -> None:
        self.selected_path = path
        try:
            self.fields = read_editable_fields(path)
        except (OSError, SyntaxError) as exc:
            messagebox.showerror("Openen mislukt", str(exc), parent=self)
            return

        relative = path.relative_to(ROOT)
        kind = "ACTION" if relative.parts[0] == "actions" else "SENSOR"
        self.kind_label.configure(text=kind)
        self.title_label.configure(text=path.stem)
        self.status_var.set(str(relative))
        self._highlight_selected(path)
        self._draw_settings()
        self._reset_live()

    def _highlight_selected(self, selected: Path) -> None:
        button_index = 0
        for widget in self.item_buttons:
            if not isinstance(widget, ctk.CTkButton):
                continue
            path = self.visible_paths[button_index] if button_index < len(self.visible_paths) else None
            widget.configure(fg_color=("#E8EEF8", "#293241") if path == selected else "transparent")
            button_index += 1

    def _draw_settings(self) -> None:
        for child in self.settings_box.winfo_children():
            child.destroy()
        self.inputs.clear()
        self.field_widgets.clear()
        self.combo_values.clear()

        if not self.fields:
            ctk.CTkLabel(
                self.settings_box,
                text="Geen eenvoudige instellingen om hier aan te passen.",
                text_color=MUTED,
                anchor="w",
            ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=6)
            self.save_button.configure(state="disabled")
            return

        for row, field in enumerate(self.fields):
            label = field.label + (f" ({field.unit})" if field.unit else "")
            ctk.CTkLabel(
                self.settings_box,
                text=label,
                text_color=TEXT,
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=(0, 16), pady=5)

            var = tk.StringVar(value=str(field.value))
            self.inputs[field.name] = var

            if field.kind == "colour":
                values = tuple(list_colour_presets())
                widget = self._searchable_combo(field.name, var, values)
            elif field.kind == "area":
                values = self._area_names()
                widget = self._searchable_combo(field.name, var, values)
            elif field.kind == "image":
                values = self._image_names()
                widget = self._searchable_combo(field.name, var, values)
            elif field.kind == "choice":
                values = ("left", "right")
                widget = self._searchable_combo(field.name, var, values)
            else:
                widget = ctk.CTkEntry(
                    self.settings_box,
                    textvariable=var,
                    height=34,
                    corner_radius=9,
                    border_color=BORDER,
                )

            widget.grid(row=row, column=1, sticky="ew", pady=5)
            self.field_widgets[field.name] = widget

        self.save_button.configure(state="normal")

    def _searchable_combo(
        self,
        field_name: str,
        var: tk.StringVar,
        values: tuple[str, ...],
    ) -> ctk.CTkComboBox:
        self.combo_values[field_name] = values
        combo = ctk.CTkComboBox(
            self.settings_box,
            variable=var,
            values=list(values) or [""],
            height=34,
            corner_radius=9,
            border_color=BORDER,
            button_color=("#E5E7EB", "#303740"),
            button_hover_color=("#D1D5DB", "#3A434E"),
            dropdown_fg_color=CARD,
            dropdown_hover_color=("#E8EEF8", "#293241"),
        )

        def filter_values(*_args) -> None:
            typed = var.get().strip().casefold()
            matches = [value for value in values if typed in value.casefold()] if typed else list(values)
            combo.configure(values=matches or list(values) or [""])

        var.trace_add("write", filter_values)
        return combo

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
                update_literal(path, field.name, self._current_value(field))
        except (ValueError, OSError, KeyError) as exc:
            messagebox.showerror("Niet opgeslagen", str(exc), parent=self)
            return
        self.status_var.set(f"Opgeslagen: {path.relative_to(ROOT)}")
        self._load_path(path)

    def _reload_selected(self) -> None:
        if self.selected_path is not None:
            self._load_path(self.selected_path)

    def _set_results(self, lines: list[str]) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        if lines:
            self.result_text.insert("1.0", "\n".join(lines))
        self.result_text.configure(state="disabled")

    def _reset_live(self) -> None:
        self.live_result_var.set("Nog niet gemeten")
        self.preview_label.configure(image=None, text="Klik op ‘Meet live’")
        self.preview_image = None
        self._set_results([])
        self.live_blob_sizes = []
        self.use_smallest_button.configure(state="disabled")
        self.use_largest_button.configure(state="disabled")

        has_area = self._field_by_kind("area") is not None
        has_target = self._field_by_kind("colour") is not None or self._field_by_kind("image") is not None
        enabled = has_area and has_target
        self.live_button.configure(state="normal" if enabled else "disabled")
        if not enabled:
            self.live_result_var.set("Voor deze action is geen vision-test nodig.")

    def _measure_live(self) -> None:
        if self._field_by_kind("colour") is not None:
            self._measure_colour_live()
        elif self._field_by_kind("image") is not None:
            self._measure_image_live()

    def _measure_colour_live(self) -> None:
        colour_field = self._field_by_kind("colour")
        area_field = self._field_by_kind("area")
        if colour_field is None or area_field is None:
            return

        try:
            colour = str(self._current_value(colour_field))
            area = str(self._current_value(area_field))
            screenshot, region = capture_area(area, bot_id=int(self.bot_var.get()))
            _, all_blobs, total_pixels = analyse_colour_image(
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
        self.live_blob_sizes = sorted(blob.area_px for blob in all_blobs)
        self.found_title.configure(text="Gevonden groottes")

        lines = []
        for blob in sorted(all_blobs, key=lambda b: b.area_px):
            marker = "✓" if blob in valid else "×"
            lines.append(f"{marker}  {blob.area_px} px")
        self._set_results(lines or ["Geen blobs gevonden"])

        self.live_result_var.set(
            f"{len(valid)} geldig · {len(all_blobs)} gevonden · {total_pixels} kleurpixels totaal"
        )
        self._show_colour_preview(screenshot, region, all_blobs, valid)
        state = "normal" if self.live_blob_sizes else "disabled"
        if min_field:
            self.use_smallest_button.configure(state=state)
        if max_field:
            self.use_largest_button.configure(state=state)

    def _measure_image_live(self) -> None:
        image_field = self._field_by_kind("image")
        area_field = self._field_by_kind("area")
        if image_field is None or area_field is None:
            return

        try:
            image_name = str(self._current_value(image_field))
            area = str(self._current_value(area_field))
            screenshot, region = capture_area(area, bot_id=int(self.bot_var.get()))
            hit = find_image(image_name, area=area, bot_id=int(self.bot_var.get()))
        except Exception as exc:
            messagebox.showerror("Live meten mislukt", str(exc), parent=self)
            return

        self.found_title.configure(text="Image match")
        if hit is None:
            self.live_result_var.set("Geen match gevonden")
            self._set_results(["×  Geen match"])
        else:
            self.live_result_var.set("✓ Image gevonden")
            self._set_results(
                [
                    f"✓  Shape   {hit.shape_score:.1%}",
                    f"✓  Colour  {hit.color_score:.1%}",
                    f"   Grootte {hit.width} × {hit.height} px",
                ]
            )
        self._show_image_preview(screenshot, region, hit)

    def _show_colour_preview(self, screenshot, region, blobs, valid) -> None:
        image = Image.fromarray(screenshot).convert("RGB")
        draw = ImageDraw.Draw(image)
        valid_ids = {id(blob) for blob in valid}
        origin_x, origin_y = region[0], region[1]

        for blob in blobs:
            x1 = blob.x - origin_x
            y1 = blob.y - origin_y
            x2 = x1 + blob.width
            y2 = y1 + blob.height
            is_valid = id(blob) in valid_ids
            draw.rectangle(
                (x1, y1, x2, y2),
                outline="lime" if is_valid else "white",
                width=3 if is_valid else 1,
            )
            draw.text((x1 + 3, y1 + 3), f"{blob.area_px}px", fill="lime" if is_valid else "white")
        self._set_preview(image)

    def _show_image_preview(self, screenshot, region, hit) -> None:
        image = Image.fromarray(screenshot).convert("RGB")
        if hit is not None:
            draw = ImageDraw.Draw(image)
            x1 = hit.x - region[0]
            y1 = hit.y - region[1]
            x2 = x1 + hit.width
            y2 = y1 + hit.height
            draw.rectangle((x1, y1, x2, y2), outline="lime", width=3)
            draw.text((x1 + 3, y1 + 3), f"{hit.shape_score:.0%}", fill="lime")
        self._set_preview(image)

    def _set_preview(self, image: Image.Image) -> None:
        max_width = 720
        max_height = 430
        copy = image.copy()
        copy.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        self.preview_image = ctk.CTkImage(
            light_image=copy,
            dark_image=copy,
            size=copy.size,
        )
        self.preview_label.configure(image=self.preview_image, text="")

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
    ActionStudio().mainloop()


if __name__ == "__main__":
    main()
