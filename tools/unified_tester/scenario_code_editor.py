from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
import re
import threading
import time
import tkinter as tk
import traceback
from tkinter import messagebox, ttk
from typing import Callable

from tools.unified_tester.result_utils import result_detail, result_success


ROOT = Path(__file__).resolve().parents[2]
ACTIONS_ROOT = ROOT / "actions"
DEFINITIONS_ROOT = ROOT / "definitions"
IMAGES_ROOT = ROOT / "assets" / "images"
AREAS_FILE = ROOT / "config" / "areas.json"

MAKER_TYPES = ("Click image", "Image exists")


class ScenarioCodeEditor(ttk.Frame):
    """Browse, create, edit and run local actions without mutating tester classes."""

    def __init__(
        self,
        parent,
        *,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, padding=12)
        self._status_callback = status_callback
        self._action_path: Path | None = None
        self._action_dirty = False
        self._action_running = False
        self._action_files: list[Path] = []
        self._visible_action_files: list[Path] = []
        self._maker_images: list[str] = []
        self._maker_areas: list[str] = []

        self.action_query = tk.StringVar()
        self.action_bot_id = tk.StringVar(value="1")
        self.maker_type = tk.StringVar(value=MAKER_TYPES[0])
        self.maker_name = tk.StringVar()
        self.maker_image = tk.StringVar()
        self.maker_area = tk.StringVar(value="Bot_Area")

        self._build()
        self.refresh()

    def _build(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        sidebar = ttk.LabelFrame(self, text="Actions", padding=8)
        sidebar.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 10))
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(1, weight=1)

        search = ttk.Entry(sidebar, textvariable=self.action_query, width=28)
        search.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search.bind("<KeyRelease>", lambda _event: self._draw_action_list())

        self.action_list = tk.Listbox(sidebar, width=34, exportselection=False)
        self.action_list.grid(row=1, column=0, sticky="nsew")
        self.action_list.bind("<<ListboxSelect>>", self._action_selected)

        self._build_maker()
        self._build_editor_toolbar()
        self._build_editor()

    def _build_maker(self) -> None:
        maker = ttk.LabelFrame(self, text="New", padding=8)
        maker.grid(row=0, column=1, sticky="ew", pady=(0, 8))
        for column in (1, 3):
            maker.columnconfigure(column, weight=1)

        ttk.Label(maker, text="MAKE").grid(row=0, column=0, sticky="w", padx=(0, 6))
        ttk.Combobox(
            maker,
            textvariable=self.maker_type,
            values=MAKER_TYPES,
            state="readonly",
            width=14,
        ).grid(row=0, column=1, sticky="ew", padx=(0, 8))
        ttk.Entry(maker, textvariable=self.maker_name).grid(
            row=0,
            column=2,
            columnspan=2,
            sticky="ew",
            padx=(0, 8),
        )
        ttk.Button(maker, text="Create", command=self._create_simple_action).grid(
            row=0,
            column=4,
            sticky="e",
        )

        ttk.Label(maker, text="IMAGE").grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 6),
            pady=(6, 0),
        )
        self.maker_image_box = ttk.Combobox(maker, textvariable=self.maker_image)
        self.maker_image_box.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 8),
            pady=(6, 0),
        )
        self.maker_image_box.bind(
            "<KeyRelease>",
            lambda _event: self._filter_combo(
                self.maker_image_box,
                self.maker_image,
                self._maker_images,
            ),
        )

        ttk.Label(maker, text="AREA").grid(
            row=1,
            column=2,
            sticky="e",
            padx=(0, 6),
            pady=(6, 0),
        )
        self.maker_area_box = ttk.Combobox(maker, textvariable=self.maker_area)
        self.maker_area_box.grid(
            row=1,
            column=3,
            sticky="ew",
            padx=(0, 8),
            pady=(6, 0),
        )
        self.maker_area_box.bind(
            "<KeyRelease>",
            lambda _event: self._filter_combo(
                self.maker_area_box,
                self.maker_area,
                self._maker_areas,
            ),
        )

    def _build_editor_toolbar(self) -> None:
        top = ttk.Frame(self)
        top.grid(row=1, column=1, sticky="ew", pady=(0, 8))
        top.columnconfigure(0, weight=1)

        self.action_path_label = ttk.Label(top, text="Selecteer een action.")
        self.action_path_label.grid(row=0, column=0, sticky="w")

        ttk.Label(top, text="Bot ID").grid(row=0, column=1, padx=(8, 4))
        ttk.Spinbox(
            top,
            from_=1,
            to=4,
            textvariable=self.action_bot_id,
            width=4,
        ).grid(row=0, column=2)
        ttk.Button(top, text="Reload", command=self._reload_action).grid(
            row=0,
            column=3,
            padx=(8, 0),
        )
        ttk.Button(top, text="Save local", command=self._save_action_local).grid(
            row=0,
            column=4,
            padx=(8, 0),
        )
        self.action_run_button = ttk.Button(
            top,
            text="Run action",
            command=self._run_action,
        )
        self.action_run_button.grid(row=0, column=5, padx=(8, 0))

    def _build_editor(self) -> None:
        main = ttk.Frame(self)
        main.grid(row=2, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=4)
        main.rowconfigure(2, weight=1)

        self.action_editor = tk.Text(
            main,
            wrap="none",
            undo=True,
            font=("Consolas", 11),
            tabs=(32,),
        )
        self.action_editor.grid(row=0, column=0, sticky="nsew")
        self.action_editor.bind("<<Modified>>", self._action_modified)

        result_bar = ttk.Frame(main)
        result_bar.grid(row=1, column=0, sticky="ew", pady=(8, 5))
        result_bar.columnconfigure(1, weight=1)
        ttk.Label(result_bar, text="RESULT").grid(row=0, column=0, sticky="w")
        self.action_result = tk.Label(
            result_bar,
            text="READY",
            bg="#6B7280",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=5,
        )
        self.action_result.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self.action_output = tk.Text(
            main,
            height=7,
            wrap="word",
            state="disabled",
            font=("Consolas", 10),
        )
        self.action_output.grid(row=2, column=0, sticky="nsew")

    def refresh(self) -> None:
        self._refresh_maker_choices()
        self._refresh_actions()

    def _set_status(self, message: str) -> None:
        if self._status_callback is not None:
            self._status_callback(message)

    def _refresh_maker_choices(self) -> None:
        self._maker_images = sorted(
            path.stem
            for path in IMAGES_ROOT.glob("*.png")
            if path.is_file()
        )
        self._maker_areas = self._load_area_names()

        self.maker_image_box.configure(values=self._maker_images)
        self.maker_area_box.configure(values=self._maker_areas)

        if not self.maker_image.get() and self._maker_images:
            self.maker_image.set(self._maker_images[0])
        if self.maker_area.get() not in self._maker_areas and self._maker_areas:
            preferred = "Bot_Area"
            self.maker_area.set(
                preferred if preferred in self._maker_areas else self._maker_areas[0]
            )

    @staticmethod
    def _load_area_names() -> list[str]:
        try:
            data = json.loads(AREAS_FILE.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return []
        return sorted(data) if isinstance(data, dict) else []

    @staticmethod
    def _filter_combo(widget, variable: tk.StringVar, values: list[str]) -> None:
        query = variable.get().strip().casefold()
        widget.configure(
            values=[value for value in values if query in value.casefold()]
        )

    def _current_group(self) -> str:
        path = self._action_path
        if path is None:
            return ""
        try:
            parent = path.relative_to(ACTIONS_ROOT).parent
        except ValueError:
            return ""
        return "" if str(parent) == "." else str(parent).replace("\\", "/")

    @staticmethod
    def _safe_function_name(value: str) -> str:
        name = value.strip()
        if name.lower().endswith(".py"):
            name = name[:-3]
        if not name:
            raise ValueError("Vul een naam in, bijvoorbeeld click_bank.")
        if "/" in name or "\\" in name:
            raise ValueError(
                "Gebruik alleen de functienaam; de huidige action-map wordt gebruikt."
            )
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is None:
            raise ValueError("Naam moet een geldige Python functienaam zijn.")
        return name

    def _create_simple_action(self) -> None:
        try:
            function_name = self._safe_function_name(self.maker_name.get())
            image_name = self._existing_choice(
                self.maker_image.get(),
                self._maker_images,
                "Kies een bestaande image.",
            )
            area_name = self._existing_choice(
                self.maker_area.get(),
                self._maker_areas,
                "Kies een bestaande area.",
            )
        except ValueError as exc:
            messagebox.showerror("Create", str(exc), parent=self)
            return

        maker_type = self.maker_type.get()
        group = self._current_group()
        if maker_type == "Click image":
            base = ACTIONS_ROOT / group if group else ACTIONS_ROOT
            content = self._click_image_source(function_name, image_name, area_name)
        elif maker_type == "Image exists":
            base = DEFINITIONS_ROOT / group if group else DEFINITIONS_ROOT
            content = self._image_exists_source(function_name, image_name, area_name)
        else:
            messagebox.showerror("Create", "Onbekend action type.", parent=self)
            return

        path = base / f"{function_name}.py"
        if path.exists():
            messagebox.showerror(
                "Create",
                f"Bestaat al: {path.relative_to(ROOT)}",
                parent=self,
            )
            return

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Create", str(exc), parent=self)
            return

        self._refresh_actions()
        self._open_action_file(path, force=True)
        self.maker_name.set("")
        self._set_status(f"Created locally: {path.relative_to(ROOT)}")

    @staticmethod
    def _existing_choice(value: str, choices: list[str], error: str) -> str:
        cleaned = value.strip()
        if cleaned not in choices:
            raise ValueError(error)
        return cleaned

    @staticmethod
    def _click_image_source(function_name: str, image_name: str, area_name: str) -> str:
        return (
            "from core import mouse_actions\n\n\n"
            f'IMAGE_NAME = "{image_name}"\n'
            f'AREA_NAME = "{area_name}"\n'
            'BUTTON = "left"\n'
            "EDGE_PADDING = 20\n\n\n"
            f"def {function_name}(bot_id: int = 1):\n"
            "    return mouse_actions.click_image(\n"
            "        image_name=IMAGE_NAME,\n"
            "        area_name=AREA_NAME,\n"
            "        bot_id=bot_id,\n"
            "        button=BUTTON,\n"
            "        image_edge_padding=EDGE_PADDING,\n"
            "    )\n"
        )

    @staticmethod
    def _image_exists_source(function_name: str, image_name: str, area_name: str) -> str:
        return (
            "from core import vision\n\n\n"
            f'IMAGE_NAME = "{image_name}"\n'
            f'AREA_NAME = "{area_name}"\n\n\n'
            f"def {function_name}(bot_id: int = 1) -> bool:\n"
            "    return vision.find_image(\n"
            "        image_name=IMAGE_NAME,\n"
            "        area=AREA_NAME,\n"
            "        bot_id=bot_id,\n"
            "    ) is not None\n"
        )

    def _refresh_actions(self) -> None:
        self._action_files = sorted(
            path
            for path in ACTIONS_ROOT.rglob("*.py")
            if path.name != "__init__.py" and "__pycache__" not in path.parts
        )
        self._draw_action_list()

    def _draw_action_list(self) -> None:
        terms = [
            term
            for term in self.action_query.get().strip().casefold().split()
            if term
        ]
        self.action_list.delete(0, "end")
        self._visible_action_files = []

        for path in self._action_files:
            relative = str(path.relative_to(ACTIONS_ROOT)).replace("\\", "/")
            if terms and not all(term in relative.casefold() for term in terms):
                continue
            self._visible_action_files.append(path)
            self.action_list.insert("end", relative)

    def _action_selected(self, _event=None) -> None:
        selection = self.action_list.curselection()
        if selection:
            self._open_action_file(self._visible_action_files[int(selection[0])])

    def _open_action_file(self, path: Path, *, force: bool = False) -> None:
        if self._action_dirty and not force:
            discard = messagebox.askyesno(
                "Unsaved local code",
                "Lokale wijzigingen weggooien en ander bestand openen?",
                parent=self,
            )
            if not discard:
                return

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Open action", str(exc), parent=self)
            return

        self._action_path = path
        self.action_editor.delete("1.0", "end")
        self.action_editor.insert("1.0", content)
        self.action_editor.edit_modified(False)
        self._action_dirty = False
        self.action_path_label.configure(text=str(path.relative_to(ROOT)))
        self._set_action_result("READY", "#6B7280", "")

    def _reload_action(self) -> None:
        if self._action_path is not None:
            self._open_action_file(self._action_path, force=True)

    def _action_modified(self, _event=None) -> None:
        if not self.action_editor.edit_modified():
            return
        self._action_dirty = True
        self.action_editor.edit_modified(False)
        if self._action_path is not None:
            self.action_path_label.configure(
                text=f"{self._action_path.relative_to(ROOT)}  ·  LOCAL CHANGES"
            )

    def _save_action_local(self) -> bool:
        path = self._action_path
        if path is None:
            return False

        content = self.action_editor.get("1.0", "end-1c")
        try:
            compile(content, str(path), "exec")
        except SyntaxError as exc:
            messagebox.showerror(
                "Python syntax error",
                f"Niet opgeslagen. Regel {exc.lineno}: {exc.msg}",
                parent=self,
            )
            return False

        if content and not content.endswith("\n"):
            content += "\n"
        try:
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Save local", str(exc), parent=self)
            return False

        self._action_dirty = False
        self.action_editor.edit_modified(False)
        self.action_path_label.configure(text=str(path.relative_to(ROOT)))
        return True

    def _set_action_result(self, state: str, colour: str, output: str) -> None:
        self.action_result.configure(text=state, bg=colour)
        self.action_output.configure(state="normal")
        self.action_output.delete("1.0", "end")
        self.action_output.insert("1.0", output)
        self.action_output.configure(state="disabled")

    def _run_action(self) -> None:
        path = self._action_path
        if path is None or self._action_running:
            return
        if self._action_dirty and not self._save_action_local():
            return

        try:
            bot_id = int(self.action_bot_id.get())
        except ValueError:
            messagebox.showerror("Run action", "Bot ID moet een getal zijn.", parent=self)
            return

        self._action_running = True
        self.action_run_button.configure(state="disabled")
        self._set_action_result(
            "RUNNING",
            "#2563EB",
            str(path.relative_to(ROOT)),
        )

        threading.Thread(
            target=self._action_worker,
            args=(path, bot_id),
            name="action-tester",
            daemon=True,
        ).start()

    def _action_worker(self, path: Path, bot_id: int) -> None:
        started = time.perf_counter()
        try:
            function = self._load_action_function(path)
            kwargs = self._supported_arguments(function, bot_id)
            value = function(**kwargs)
            elapsed = (time.perf_counter() - started) * 1000.0
            passed = result_success(value)
            state = "PASS" if passed is not False else "FAIL"
            colour = "#15803D" if passed is not False else "#B91C1C"
            output = f"Return: {value!r}\n"
            detail = result_detail(value)
            if detail:
                output += f"Message: {detail}\n"
            output += f"Time: {elapsed:.1f} ms"
        except Exception:
            state = "ERROR"
            colour = "#B91C1C"
            output = traceback.format_exc()

        self.after(
            0,
            lambda: self._finish_action_run(state, colour, output),
        )

    @staticmethod
    def _load_action_function(path: Path):
        module_name = f"_action_test_{path.stem}_{time.time_ns()}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Kan module niet laden: {path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        function = getattr(module, path.stem, None)
        if not callable(function):
            raise RuntimeError(f"Verwacht functie '{path.stem}()' in {path.name}.")
        return function

    @staticmethod
    def _supported_arguments(function, bot_id: int) -> dict[str, object]:
        signature = inspect.signature(function)
        kwargs: dict[str, object] = {}
        missing: list[str] = []

        for name, parameter in signature.parameters.items():
            if name == "bot_id":
                kwargs[name] = bot_id
            elif parameter.default is inspect.Parameter.empty and parameter.kind in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                missing.append(name)

        if missing:
            raise RuntimeError(
                "Action heeft verplichte argumenten nodig: " + ", ".join(missing)
            )
        return kwargs

    def _finish_action_run(self, state: str, colour: str, output: str) -> None:
        self._action_running = False
        self.action_run_button.configure(state="normal")
        self._set_action_result(state, colour, output)


__all__ = ["ScenarioCodeEditor"]
