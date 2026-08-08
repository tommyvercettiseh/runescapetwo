from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
import threading
import time
import tkinter as tk
import traceback
from tkinter import messagebox, ttk


ROOT = Path(__file__).resolve().parents[2]
ACTIONS_ROOT = ROOT / "actions"


def install_scenario_code_editor(tester_class, banking_scenario) -> None:
    def _add_simple_action_tester(self) -> None:
        self.scenario_tab = ttk.Frame(self.tabs, padding=12)
        self.tabs.insert(2, self.scenario_tab, text="Scenario")
        self.scenario_tab.columnconfigure(1, weight=1)
        self.scenario_tab.rowconfigure(1, weight=1)

        self._action_path: Path | None = None
        self._action_dirty = False
        self._action_running = False
        self._action_files: list[Path] = []
        self.action_query = tk.StringVar()
        self.action_bot_id = tk.StringVar(value="1")

        sidebar = ttk.LabelFrame(self.scenario_tab, text="Actions", padding=8)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(1, weight=1)

        search = ttk.Entry(sidebar, textvariable=self.action_query, width=28)
        search.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search.bind("<KeyRelease>", lambda _event: self._draw_action_list())

        self.action_list = tk.Listbox(sidebar, width=34, exportselection=False)
        self.action_list.grid(row=1, column=0, sticky="nsew")
        self.action_list.bind("<<ListboxSelect>>", self._action_selected)

        top = ttk.Frame(self.scenario_tab)
        top.grid(row=0, column=1, sticky="ew", pady=(0, 8))
        top.columnconfigure(0, weight=1)

        self.action_path_label = ttk.Label(top, text="Selecteer een action.")
        self.action_path_label.grid(row=0, column=0, sticky="w")

        ttk.Label(top, text="Bot ID").grid(row=0, column=1, padx=(8, 4))
        ttk.Spinbox(top, from_=1, to=4, textvariable=self.action_bot_id, width=4).grid(
            row=0, column=2
        )
        ttk.Button(top, text="Reload", command=self._reload_action).grid(
            row=0, column=3, padx=(8, 0)
        )
        ttk.Button(top, text="Save local", command=self._save_action_local).grid(
            row=0, column=4, padx=(8, 0)
        )
        self.action_run_button = ttk.Button(top, text="Run action", command=self._run_action)
        self.action_run_button.grid(row=0, column=5, padx=(8, 0))

        main = ttk.Frame(self.scenario_tab)
        main.grid(row=1, column=1, sticky="nsew")
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

        self._refresh_actions()

    def _refresh_actions(self) -> None:
        self._action_files = sorted(
            path
            for path in ACTIONS_ROOT.rglob("*.py")
            if path.name != "__init__.py" and "__pycache__" not in path.parts
        )
        self._draw_action_list()

    def _draw_action_list(self) -> None:
        query = self.action_query.get().strip().casefold()
        terms = [term for term in query.split() if term]
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
        if not selection:
            return
        path = self._visible_action_files[int(selection[0])]
        self._open_action_file(path)

    def _open_action_file(self, path: Path, *, force: bool = False) -> None:
        if self._action_dirty and not force:
            if not messagebox.askyesno(
                "Unsaved local code",
                "Lokale wijzigingen weggooien en ander bestand openen?",
                parent=self,
            ):
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
        try:
            if content and not content.endswith("\n"):
                content += "\n"
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

        self._action_running = True
        self.action_run_button.configure(state="disabled")
        self._set_action_result("RUNNING", "#2563EB", str(path.relative_to(ROOT)))
        bot_id = int(self.action_bot_id.get())

        def worker() -> None:
            started = time.perf_counter()
            try:
                module_name = f"_action_test_{path.stem}_{time.time_ns()}"
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    raise RuntimeError(f"Kan module niet laden: {path}")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                function = getattr(module, path.stem, None)
                if not callable(function):
                    raise RuntimeError(
                        f"Verwacht functie '{path.stem}()' in {path.name}."
                    )

                signature = inspect.signature(function)
                kwargs = {}
                missing = []
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

                value = function(**kwargs)
                elapsed = (time.perf_counter() - started) * 1000.0
                if value is False:
                    state, colour = "FAIL", "#B91C1C"
                else:
                    state, colour = "PASS", "#15803D"
                output = f"Return: {value!r}\nTime: {elapsed:.1f} ms"
            except Exception:
                state, colour = "ERROR", "#B91C1C"
                output = traceback.format_exc()
            self.after(0, lambda: self._finish_action_run(state, colour, output))

        threading.Thread(target=worker, name="action-tester", daemon=True).start()

    def _finish_action_run(self, state: str, colour: str, output: str) -> None:
        self._action_running = False
        self.action_run_button.configure(state="normal")
        self._set_action_result(state, colour, output)

    tester_class._add_scenario_tab = _add_simple_action_tester
    tester_class._refresh_actions = _refresh_actions
    tester_class._draw_action_list = _draw_action_list
    tester_class._action_selected = _action_selected
    tester_class._open_action_file = _open_action_file
    tester_class._reload_action = _reload_action
    tester_class._action_modified = _action_modified
    tester_class._save_action_local = _save_action_local
    tester_class._set_action_result = _set_action_result
    tester_class._run_action = _run_action
    tester_class._finish_action_run = _finish_action_run


__all__ = ["install_scenario_code_editor"]
