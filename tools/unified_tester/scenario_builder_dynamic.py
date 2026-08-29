from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Any

from core import mouse_actions
from tools.definition_tester.registry import get_definition
from tools.unified_tester.action_registry import ActionContext, get_action
from tools.unified_tester.scenario_builder import BuilderStep, ScenarioBuilder


ROOT = Path(__file__).resolve().parents[2]
IMAGES_ROOT = ROOT / "assets" / "images"
AREAS_FILE = ROOT / "config" / "areas.json"


@dataclass
class DynamicBuilderStep(BuilderStep):
    area_name: str = mouse_actions.DEFAULT_AREA_NAME


def _parse_names(text: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            value.strip()
            for value in text.split(",")
            if value.strip()
        )
    )


def _image_names() -> list[str]:
    return sorted(
        path.stem
        for path in IMAGES_ROOT.glob("*.png")
        if path.is_file()
    )


def _area_names() -> list[str]:
    try:
        data = json.loads(AREAS_FILE.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return []
    return sorted(data) if isinstance(data, dict) else []


class DynamicScenarioBuilder(ScenarioBuilder):
    """Scenario builder with editable Image and Area parameters."""

    def _build_settings(self) -> None:
        frame = ttk.LabelFrame(self, text="Step settings", padding=8)
        frame.grid(row=1, column=2, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        self.area_var = tk.StringVar(value=mouse_actions.DEFAULT_AREA_NAME)

        ttk.Label(
            frame,
            textvariable=self.selected_name_var,
            font=("Segoe UI", 10, "bold"),
            wraplength=230,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        ttk.Label(frame, text="Image").grid(row=1, column=0, sticky="w", pady=4)
        self.image_box = ttk.Combobox(
            frame,
            textvariable=self.image_var,
            values=_image_names(),
            width=24,
        )
        self.image_box.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=4)
        self.image_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._save_selected_settings(),
        )
        self.image_box.bind(
            "<FocusOut>",
            lambda _event: self._save_selected_settings(),
        )
        self.image_box.bind(
            "<Return>",
            lambda _event: self._save_selected_settings(),
        )

        ttk.Label(frame, text="Area").grid(row=2, column=0, sticky="w", pady=4)
        self.area_box = ttk.Combobox(
            frame,
            textvariable=self.area_var,
            values=_area_names(),
            width=24,
        )
        self.area_box.grid(row=2, column=1, sticky="ew", padx=(8, 0), pady=4)
        self.area_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._save_selected_settings(),
        )
        self.area_box.bind(
            "<FocusOut>",
            lambda _event: self._save_selected_settings(),
        )
        self.area_box.bind(
            "<Return>",
            lambda _event: self._save_selected_settings(),
        )

        self.setting_entries: dict[str, ttk.Widget] = {
            "Image": self.image_box,
            "Area": self.area_box,
        }

        for row, (label, variable) in enumerate(
            (
                ("Protected", self.protected_var),
                ("Optional", self.optional_var),
            ),
            start=3,
        ):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(frame, textvariable=variable, width=24)
            entry.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=4)
            entry.bind(
                "<FocusOut>",
                lambda _event: self._save_selected_settings(),
            )
            entry.bind(
                "<Return>",
                lambda _event: self._save_selected_settings(),
            )
            self.setting_entries[label] = entry

        ttk.Label(frame, text="Pattern").grid(row=5, column=0, sticky="w", pady=4)
        self.pattern_box = ttk.Combobox(
            frame,
            textvariable=self.pattern_var,
            values=(
                "row",
                "snake",
                "column",
                "column_snake",
                "random",
                "random_pattern",
                "nearest",
            ),
            state="readonly",
            width=22,
        )
        self.pattern_box.grid(row=5, column=1, sticky="ew", padx=(8, 0), pady=4)
        self.pattern_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._save_selected_settings(),
        )

        ttk.Label(frame, text="Selection").grid(row=6, column=0, sticky="w", pady=4)
        self.selection_box = ttk.Combobox(
            frame,
            textvariable=self.selection_var,
            values=("nearest", "random_slot"),
            state="readonly",
            width=22,
        )
        self.selection_box.grid(row=6, column=1, sticky="ew", padx=(8, 0), pady=4)
        self.selection_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._save_selected_settings(),
        )

        ttk.Label(
            frame,
            text=(
                "Click image: choose an Image and Area. "
                "Both fields stay editable, so new names can also be typed directly."
            ),
            wraplength=240,
        ).grid(row=7, column=0, columnspan=2, sticky="w", pady=(14, 0))

        self._set_settings_enabled(False)

    def _add_palette_item(self, item: tuple[str, str, str]) -> None:
        kind, category, name = item
        step = DynamicBuilderStep(
            kind=kind,
            category=category,
            name=name,
        )
        self._steps.append(step)
        index = len(self._steps) - 1
        self._refresh_workflow(select_index=index)
        self._set_status(f"Added {name}")

    def _workflow_selected(self, _event: tk.Event | None = None) -> None:
        index = self._selected_index()
        if index is not None and index < len(self._steps):
            step = self._steps[index]
            self.area_var.set(
                getattr(step, "area_name", mouse_actions.DEFAULT_AREA_NAME)
            )

        super()._workflow_selected(_event)

        index = self._selected_index()
        if index is None or index >= len(self._steps):
            self.area_box.configure(state="disabled")
            return

        step = self._steps[index]
        if step.kind == "sensor":
            self.area_box.configure(state="disabled")
            return

        spec = get_action(step.name)
        self.area_box.configure(
            state="normal" if spec.uses_area else "disabled"
        )

    def _set_settings_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for entry in self.setting_entries.values():
            entry.configure(state=state)
        self.pattern_box.configure(state="readonly" if enabled else "disabled")
        self.selection_box.configure(state="readonly" if enabled else "disabled")

    def _save_selected_settings(self) -> None:
        index = self._selected_index()
        if index is None or index >= len(self._steps):
            return

        step = self._steps[index]
        if step.kind != "action":
            return

        step.image_name = self.image_var.get().strip()
        step.area_name = self.area_var.get().strip() or mouse_actions.DEFAULT_AREA_NAME
        step.protected_images = _parse_names(self.protected_var.get())
        step.optional_images = _parse_names(self.optional_var.get())
        step.pattern = self.pattern_var.get()
        step.selection = self.selection_var.get()
        self._refresh_workflow(select_index=index)

    @staticmethod
    def _execute_step(step: BuilderStep, *, bot_id: int, live: bool) -> Any:
        if step.kind == "sensor":
            entry = get_definition(step.category, step.name)
            return entry.function(bot_id)

        spec = get_action(step.name)
        context = ActionContext(
            bot_id=bot_id,
            image_name=step.image_name,
            area_name=getattr(
                step,
                "area_name",
                mouse_actions.DEFAULT_AREA_NAME,
            ),
            protected_images=step.protected_images,
            optional_images=step.optional_images,
            pattern=step.pattern,
            selection=step.selection,
            dry_run=not live,
        )
        return spec.execute(context)


__all__ = ["DynamicBuilderStep", "DynamicScenarioBuilder"]
