from __future__ import annotations

import copy
import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Any, Callable

import yaml

from definitions.registry import categories, definitions_for
from tools.unified_tester.action_registry import action_names


ROOT = Path(__file__).resolve().parents[2]
IMAGES_ROOT = ROOT / "assets" / "images"
AREAS_FILE = ROOT / "config" / "areas.json"

STEP_KINDS = ("IF", "ACTION", "WAIT", "STOP")


def default_scenario_data() -> dict[str, Any]:
    return {
        "name": "New scenario",
        "bot_id": 1,
        "steps": [],
    }


def dump_scenario_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).rstrip() + "\n"


class ScenarioCardBuilder(ttk.Frame):
    """Visual editor for the small declarative scenario YAML model."""

    def __init__(
        self,
        parent,
        *,
        on_change: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_change = on_change
        self._data = default_scenario_data()
        self._definitions = self._load_definitions()
        self._actions = tuple(action_names())
        self._images = self._load_images()
        self._areas = self._load_areas()
        self.name_var = tk.StringVar(value=self._data["name"])
        self.name_var.trace_add("write", self._name_changed)
        self._build()
        self._render()

    @staticmethod
    def _load_definitions() -> dict[str, tuple[str, ...]]:
        return {
            category: tuple(entry.name for entry in definitions_for(category))
            for category in categories()
        }

    @staticmethod
    def _load_images() -> tuple[str, ...]:
        return tuple(
            sorted(
                (path.stem for path in IMAGES_ROOT.glob("*.png") if path.is_file()),
                key=str.casefold,
            )
        )

    @staticmethod
    def _load_areas() -> tuple[str, ...]:
        try:
            data = json.loads(AREAS_FILE.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return ()
        if not isinstance(data, dict):
            return ()
        return tuple(sorted(data, key=str.casefold))

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="Scenario").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.name_var).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(8, 14),
        )

        ttk.Label(top, text="ADD").grid(row=0, column=2, padx=(0, 5))
        for offset, kind in enumerate(STEP_KINDS, start=3):
            ttk.Button(
                top,
                text=f"+ {kind.title()}",
                command=lambda current=kind: self._add_step(
                    self._data.setdefault("steps", []),
                    current,
                ),
            ).grid(row=0, column=offset, padx=(4, 0))

        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(body, highlightthickness=0, borderwidth=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.cards = ttk.Frame(self.canvas, padding=(2, 2, 8, 8))
        self._canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.cards,
            anchor="nw",
        )
        self.cards.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(
                self._canvas_window,
                width=max(1, event.width),
            ),
        )
        self.canvas.bind("<Enter>", lambda _event: self._bind_mousewheel())
        self.canvas.bind("<Leave>", lambda _event: self._unbind_mousewheel())

    def _bind_mousewheel(self) -> None:
        self.canvas.bind_all("<MouseWheel>", self._mousewheel)

    def _unbind_mousewheel(self) -> None:
        self.canvas.unbind_all("<MouseWheel>")

    def _mousewheel(self, event: tk.Event) -> None:
        delta = int(-1 * (event.delta / 120)) if event.delta else 0
        if delta:
            self.canvas.yview_scroll(delta, "units")

    def load_data(self, data: dict[str, Any]) -> None:
        self._data = copy.deepcopy(data)
        self._data.setdefault("bot_id", 1)
        self._data.setdefault("steps", [])
        self.name_var.set(str(self._data.get("name", "New scenario")))
        self._render()

    def data(self) -> dict[str, Any]:
        self._data["name"] = self.name_var.get().strip() or "New scenario"
        return copy.deepcopy(self._data)

    def yaml_text(self) -> str:
        return dump_scenario_yaml(self.data())

    def _name_changed(self, *_args) -> None:
        self._data["name"] = self.name_var.get()
        self._changed()

    def _changed(self, *, render: bool = False) -> None:
        if render:
            self._render()
        if self._on_change is not None:
            self._on_change()

    def _render(self) -> None:
        for child in self.cards.winfo_children():
            child.destroy()

        steps = self._data.setdefault("steps", [])
        if not steps:
            empty = ttk.LabelFrame(self.cards, text="FLOW", padding=18)
            empty.pack(fill="x", pady=(0, 8))
            ttk.Label(
                empty,
                text=(
                    "No steps yet. Add an IF, Action, Wait or Stop card above.\n"
                    "Cards on this level run from top to bottom."
                ),
                justify="left",
            ).pack(anchor="w")
            return

        self._render_steps(self.cards, steps, depth=0)

    def _render_steps(self, parent, steps: list[Any], *, depth: int) -> None:
        for index, step in enumerate(steps):
            if not isinstance(step, dict) or not step:
                continue
            operation = next(iter(step))
            card = ttk.LabelFrame(
                parent,
                text=operation.upper(),
                padding=8,
            )
            card.pack(fill="x", pady=(0, 8), padx=(min(depth * 12, 48), 0))
            card.columnconfigure(0, weight=1)

            controls = ttk.Frame(card)
            controls.grid(row=0, column=1, sticky="ne", padx=(10, 0))
            ttk.Button(
                controls,
                text="↑",
                width=3,
                command=lambda current=index, items=steps: self._move_step(
                    items, current, -1
                ),
            ).pack(side="left")
            ttk.Button(
                controls,
                text="↓",
                width=3,
                command=lambda current=index, items=steps: self._move_step(
                    items, current, 1
                ),
            ).pack(side="left", padx=(4, 0))
            ttk.Button(
                controls,
                text="Delete",
                command=lambda current=index, items=steps: self._delete_step(
                    items, current
                ),
            ).pack(side="left", padx=(8, 0))

            body = ttk.Frame(card)
            body.grid(row=0, column=0, sticky="nsew")
            body.columnconfigure(0, weight=1)

            if operation == "if":
                self._render_if(body, step, depth=depth)
            elif operation == "action":
                self._render_action(body, step)
            elif operation == "wait":
                self._render_wait(body, step)
            elif operation == "stop":
                self._render_stop(body, step)
            else:
                ttk.Label(
                    body,
                    text=f"Unsupported visual card: {operation}. Edit it in YAML.",
                ).grid(row=0, column=0, sticky="w")

    def _render_action(self, parent, step: dict[str, Any]) -> None:
        raw = step.get("action", "")
        if isinstance(raw, dict):
            current = str(raw.get("name", ""))
            has_options = bool(raw.get("with"))
        else:
            current = str(raw)
            has_options = False

        ttk.Label(parent, text="DO").grid(row=0, column=0, sticky="w")
        variable = tk.StringVar(value=current)
        box = ttk.Combobox(
            parent,
            textvariable=variable,
            values=self._actions,
            state="readonly",
            width=34,
        )
        box.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        parent.columnconfigure(1, weight=1)
        box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_action(step, variable.get()),
        )
        if has_options:
            ttk.Label(
                parent,
                text="Advanced options are preserved; edit them in YAML.",
            ).grid(row=1, column=1, sticky="w", pady=(5, 0))

    def _set_action(self, step: dict[str, Any], name: str) -> None:
        raw = step.get("action")
        if isinstance(raw, dict):
            raw["name"] = name
        else:
            step["action"] = name
        self._changed()

    def _render_wait(self, parent, step: dict[str, Any]) -> None:
        ttk.Label(parent, text="WAIT").grid(row=0, column=0, sticky="w")
        variable = tk.StringVar(value=str(step.get("wait", 1)))
        spin = ttk.Spinbox(
            parent,
            from_=0,
            to=300,
            increment=0.1,
            textvariable=variable,
            width=8,
        )
        spin.grid(row=0, column=1, sticky="w", padx=(8, 4))
        ttk.Label(parent, text="seconds").grid(row=0, column=2, sticky="w")

        def save_wait(*_args) -> None:
            try:
                step["wait"] = float(variable.get())
            except ValueError:
                return
            self._changed()

        variable.trace_add("write", save_wait)

    def _render_stop(self, parent, step: dict[str, Any]) -> None:
        ttk.Label(parent, text="FINISH AS").grid(row=0, column=0, sticky="w")
        current = "success" if step.get("stop") in (True, "success") else "failure"
        variable = tk.StringVar(value=current)
        box = ttk.Combobox(
            parent,
            textvariable=variable,
            values=("success", "failure"),
            state="readonly",
            width=14,
        )
        box.grid(row=0, column=1, sticky="w", padx=(8, 0))
        box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_stop(step, variable.get()),
        )

    def _set_stop(self, step: dict[str, Any], value: str) -> None:
        step["stop"] = value
        self._changed()

    def _render_if(self, parent, step: dict[str, Any], *, depth: int) -> None:
        value = step.setdefault("if", {})
        value.setdefault("then", [])
        value.setdefault("else", [])

        row = ttk.Frame(parent)
        row.grid(row=0, column=0, sticky="ew")
        row.columnconfigure(4, weight=1)

        ttk.Label(row, text="IF").grid(row=0, column=0, sticky="w")
        condition_type = tk.StringVar(
            value="Sensor" if "definition" in value else "Image"
        )
        type_box = ttk.Combobox(
            row,
            textvariable=condition_type,
            values=("Sensor", "Image"),
            state="readonly",
            width=10,
        )
        type_box.grid(row=0, column=1, sticky="w", padx=(8, 8))
        type_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._switch_condition(value, condition_type.get()),
        )

        if "definition" in value:
            self._render_definition_condition(row, value)
        else:
            self._render_image_condition(row, value)

        branches = ttk.Frame(parent)
        branches.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        branches.columnconfigure(0, weight=1)
        branches.columnconfigure(1, weight=1)

        self._render_branch(
            branches,
            "THEN / TRUE",
            value["then"],
            column=0,
            depth=depth + 1,
        )
        self._render_branch(
            branches,
            "ELSE / FALSE",
            value["else"],
            column=1,
            depth=depth + 1,
        )

    def _render_definition_condition(self, row, value: dict[str, Any]) -> None:
        definition = value.setdefault("definition", {})
        available_categories = tuple(self._definitions)
        category = str(definition.get("category", ""))
        if category not in self._definitions and available_categories:
            category = available_categories[0]
            definition["category"] = category

        names = self._definitions.get(category, ())
        name = str(definition.get("name", ""))
        if name not in names and names:
            name = names[0]
            definition["name"] = name

        category_var = tk.StringVar(value=category)
        category_box = ttk.Combobox(
            row,
            textvariable=category_var,
            values=available_categories,
            state="readonly",
            width=14,
        )
        category_box.grid(row=0, column=2, sticky="w")
        category_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_definition_category(
                value,
                category_var.get(),
            ),
        )

        name_var = tk.StringVar(value=name)
        name_box = ttk.Combobox(
            row,
            textvariable=name_var,
            values=names,
            state="readonly",
            width=30,
        )
        name_box.grid(row=0, column=3, sticky="ew", padx=(8, 0))
        name_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_definition_name(value, name_var.get()),
        )

    def _render_image_condition(self, row, value: dict[str, Any]) -> None:
        image_exists = value.setdefault("image_exists", {})
        image = str(image_exists.get("image", ""))
        area = str(image_exists.get("area", ""))
        if image not in self._images and self._images:
            image = self._images[0]
            image_exists["image"] = image
        if area not in self._areas and self._areas:
            preferred = "Inventory_Area"
            area = preferred if preferred in self._areas else self._areas[0]
            image_exists["area"] = area

        image_var = tk.StringVar(value=image)
        image_box = ttk.Combobox(
            row,
            textvariable=image_var,
            values=self._images,
            width=30,
        )
        image_box.grid(row=0, column=2, sticky="ew")
        image_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_image_condition(
                value,
                image=image_var.get(),
                area=None,
            ),
        )
        image_box.bind(
            "<FocusOut>",
            lambda _event: self._set_image_condition(
                value,
                image=image_var.get(),
                area=None,
            ),
        )

        area_var = tk.StringVar(value=area)
        area_box = ttk.Combobox(
            row,
            textvariable=area_var,
            values=self._areas,
            state="readonly",
            width=20,
        )
        area_box.grid(row=0, column=3, sticky="ew", padx=(8, 0))
        area_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_image_condition(
                value,
                image=None,
                area=area_var.get(),
            ),
        )

    def _render_branch(
        self,
        parent,
        title: str,
        steps: list[Any],
        *,
        column: int,
        depth: int,
    ) -> None:
        branch = ttk.LabelFrame(parent, text=title, padding=7)
        branch.grid(
            row=0,
            column=column,
            sticky="nsew",
            padx=(0, 5) if column == 0 else (5, 0),
        )
        branch.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(branch)
        toolbar.pack(fill="x", pady=(0, 6))
        for kind in STEP_KINDS:
            ttk.Button(
                toolbar,
                text=f"+ {kind.title()}",
                command=lambda current=kind, items=steps: self._add_step(
                    items,
                    current,
                ),
            ).pack(side="left", padx=(0, 4))

        if steps:
            self._render_steps(branch, steps, depth=depth)
        else:
            ttk.Label(branch, text="No steps").pack(anchor="w", pady=(3, 3))

    def _switch_condition(self, value: dict[str, Any], condition_type: str) -> None:
        then_steps = value.setdefault("then", [])
        else_steps = value.setdefault("else", [])
        value.clear()
        if condition_type == "Sensor":
            category = next(iter(self._definitions), "")
            names = self._definitions.get(category, ())
            value["definition"] = {
                "category": category,
                "name": names[0] if names else "",
            }
        else:
            preferred_area = (
                "Inventory_Area" if "Inventory_Area" in self._areas else ""
            )
            value["image_exists"] = {
                "image": self._images[0] if self._images else "",
                "area": preferred_area or (self._areas[0] if self._areas else ""),
            }
        value["then"] = then_steps
        value["else"] = else_steps
        self._changed(render=True)

    def _set_definition_category(self, value: dict[str, Any], category: str) -> None:
        names = self._definitions.get(category, ())
        value["definition"] = {
            "category": category,
            "name": names[0] if names else "",
        }
        self._changed(render=True)

    def _set_definition_name(self, value: dict[str, Any], name: str) -> None:
        value.setdefault("definition", {})["name"] = name
        self._changed()

    def _set_image_condition(
        self,
        value: dict[str, Any],
        *,
        image: str | None,
        area: str | None,
    ) -> None:
        condition = value.setdefault("image_exists", {})
        if image is not None:
            condition["image"] = image.strip()
        if area is not None:
            condition["area"] = area
        self._changed()

    def _add_step(self, steps: list[Any], kind: str) -> None:
        if kind == "IF":
            category = next(iter(self._definitions), "")
            names = self._definitions.get(category, ())
            step: dict[str, Any] = {
                "if": {
                    "definition": {
                        "category": category,
                        "name": names[0] if names else "",
                    },
                    "then": [],
                    "else": [],
                }
            }
        elif kind == "ACTION":
            step = {"action": self._actions[0] if self._actions else ""}
        elif kind == "WAIT":
            step = {"wait": 1.0}
        else:
            step = {"stop": "success"}
        steps.append(step)
        self._changed(render=True)

    def _delete_step(self, steps: list[Any], index: int) -> None:
        if 0 <= index < len(steps):
            steps.pop(index)
            self._changed(render=True)

    def _move_step(self, steps: list[Any], index: int, direction: int) -> None:
        target = index + direction
        if not (0 <= index < len(steps) and 0 <= target < len(steps)):
            return
        steps[index], steps[target] = steps[target], steps[index]
        self._changed(render=True)


__all__ = [
    "ScenarioCardBuilder",
    "default_scenario_data",
    "dump_scenario_yaml",
]
