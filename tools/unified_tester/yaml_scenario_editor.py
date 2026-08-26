from __future__ import annotations

import re
import threading
import tkinter as tk
from pathlib import Path
from queue import Empty, SimpleQueue
from tkinter import messagebox, simpledialog, ttk
from typing import Callable

from core.action_trace import capture_action_trace
from tools.unified_tester.result_utils import format_result
from tools.unified_tester.yaml_scenario_runner import (
    ScenarioError,
    parse_scenario,
    run_scenario_data,
)


ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_ROOT = ROOT / "scenarios"

STARTER_YAML = """name: New scenario
bot_id: 1

steps:
  - if:
      definition:
        category: Login
        name: Logged in.
    else:
      - action: Login
"""


class YamlScenarioEditor(ttk.Frame):
    """Edit, validate and run declarative YAML scenarios."""

    def __init__(
        self,
        parent,
        *,
        bot_id_var: tk.Variable,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, padding=12)
        self._bot_id_var = bot_id_var
        self._status_callback = status_callback
        self._scenario_path: Path | None = None
        self._scenario_files: list[Path] = []
        self._running = False
        self._trace_events: SimpleQueue[str] = SimpleQueue()
        self._worker_results: SimpleQueue[tuple[object | None, Exception | None]] = (
            SimpleQueue()
        )

        self.scenario_query = tk.StringVar()
        self.dry_run_var = tk.BooleanVar(value=True)

        self._build()
        self.refresh()

    def _build(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        sidebar = ttk.LabelFrame(self, text="Scenarios", padding=8)
        sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10))
        sidebar.columnconfigure(0, weight=1)
        sidebar.rowconfigure(1, weight=1)

        search = ttk.Entry(sidebar, textvariable=self.scenario_query, width=26)
        search.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search.bind("<KeyRelease>", lambda _event: self._draw_list())

        self.scenario_list = tk.Listbox(sidebar, width=30, exportselection=False)
        self.scenario_list.grid(row=1, column=0, sticky="nsew")
        self.scenario_list.bind("<<ListboxSelect>>", self._scenario_selected)

        toolbar = ttk.Frame(self)
        toolbar.grid(row=0, column=1, sticky="ew", pady=(0, 8))
        toolbar.columnconfigure(0, weight=1)

        self.path_label = ttk.Label(toolbar, text="Select or create a YAML scenario.")
        self.path_label.grid(row=0, column=0, sticky="w")

        ttk.Button(toolbar, text="New", command=self._new).grid(
            row=0, column=1, padx=(8, 0)
        )
        ttk.Button(toolbar, text="Reload", command=self._reload).grid(
            row=0, column=2, padx=(8, 0)
        )
        ttk.Button(toolbar, text="Save", command=self._save).grid(
            row=0, column=3, padx=(8, 0)
        )
        ttk.Button(toolbar, text="Validate", command=self._validate).grid(
            row=0, column=4, padx=(8, 0)
        )
        ttk.Checkbutton(
            toolbar,
            text="Dry run",
            variable=self.dry_run_var,
        ).grid(row=0, column=5, padx=(12, 0))
        self.run_button = ttk.Button(toolbar, text="Run scenario", command=self._run)
        self.run_button.grid(row=0, column=6, padx=(8, 0))

        main = ttk.Frame(self)
        main.grid(row=1, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=3)
        main.rowconfigure(2, weight=1)

        self.editor = tk.Text(
            main,
            wrap="none",
            undo=True,
            font=("Consolas", 11),
            tabs=(32,),
        )
        self.editor.grid(row=0, column=0, sticky="nsew")

        result_bar = ttk.Frame(main)
        result_bar.grid(row=1, column=0, sticky="ew", pady=(8, 5))
        result_bar.columnconfigure(1, weight=1)
        ttk.Label(result_bar, text="TRACE / RESULT").grid(row=0, column=0, sticky="w")
        self.result_label = tk.Label(
            result_bar,
            text="READY",
            bg="#6B7280",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=5,
        )
        self.result_label.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        self.output = tk.Text(
            main,
            height=10,
            wrap="word",
            state="disabled",
            font=("Consolas", 10),
        )
        self.output.grid(row=2, column=0, sticky="nsew")

    def refresh(self) -> None:
        SCENARIOS_ROOT.mkdir(parents=True, exist_ok=True)
        self._scenario_files = sorted(
            [*SCENARIOS_ROOT.glob("*.yaml"), *SCENARIOS_ROOT.glob("*.yml")],
            key=lambda path: path.name.casefold(),
        )
        self._draw_list()
        if self._scenario_path is None and self._scenario_files:
            self._open(self._scenario_files[0])

    def _draw_list(self) -> None:
        query = self.scenario_query.get().strip().casefold()
        visible = [
            path for path in self._scenario_files if query in path.name.casefold()
        ]
        self.scenario_list.delete(0, "end")
        for path in visible:
            self.scenario_list.insert("end", path.name)

    def _scenario_selected(self, _event=None) -> None:
        selection = self.scenario_list.curselection()
        if not selection:
            return
        name = self.scenario_list.get(selection[0])
        path = SCENARIOS_ROOT / name
        if path.exists():
            self._open(path)

    def _open(self, path: Path) -> None:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Scenario", str(exc), parent=self)
            return
        self._scenario_path = path
        self.path_label.configure(text=str(path.relative_to(ROOT)))
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self._set_result("READY", "#6B7280")
        self._set_output("")

    def _new(self) -> None:
        self._scenario_path = None
        self.path_label.configure(text="New unsaved scenario")
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", STARTER_YAML)
        self._set_result("READY", "#6B7280")
        self._set_output("")

    def _reload(self) -> None:
        if self._scenario_path is None:
            self._new()
            return
        self._open(self._scenario_path)

    def _save(self) -> None:
        path = self._scenario_path
        if path is None:
            name = simpledialog.askstring(
                "Save scenario",
                "File name (without .yaml):",
                parent=self,
            )
            if name is None:
                return
            cleaned = name.strip()
            if re.fullmatch(r"[A-Za-z0-9_-]+", cleaned) is None:
                messagebox.showerror(
                    "Save scenario",
                    "Use only letters, numbers, - and _.",
                    parent=self,
                )
                return
            path = SCENARIOS_ROOT / f"{cleaned}.yaml"
            if path.exists():
                messagebox.showerror("Save scenario", "File already exists.", parent=self)
                return

        text = self.editor.get("1.0", "end-1c")
        try:
            parse_scenario(text)
            path.write_text(text.rstrip() + "\n", encoding="utf-8")
        except (OSError, ScenarioError) as exc:
            messagebox.showerror("Save scenario", str(exc), parent=self)
            return

        self._scenario_path = path
        self.path_label.configure(text=str(path.relative_to(ROOT)))
        self.refresh()
        self._set_status(f"Saved {path.relative_to(ROOT)}")

    def _validate(self) -> None:
        try:
            data = parse_scenario(self.editor.get("1.0", "end-1c"))
        except Exception as exc:
            self._set_result("INVALID", "#B91C1C")
            self._set_output(f"{type(exc).__name__}: {exc}")
            return
        self._set_result("VALID", "#15803D")
        self._set_output(f"Scenario '{data['name']}' is valid.\nNo input was sent.")

    def _run(self) -> None:
        if self._running:
            return
        try:
            data = parse_scenario(self.editor.get("1.0", "end-1c"))
            bot_id = int(self._bot_id_var.get())
            if bot_id < 1:
                raise ValueError("Bot ID must be positive.")
        except Exception as exc:
            messagebox.showerror("Run scenario", str(exc), parent=self)
            return

        dry_run = self.dry_run_var.get()
        if not dry_run and not messagebox.askyesno(
            "Run scenario",
            f"Run '{data['name']}' live on bot {bot_id}?",
            parent=self,
        ):
            return

        self._running = True
        self.run_button.configure(state="disabled")
        self._set_result("RUNNING", "#2563EB")
        self._set_output("")
        self._clear_trace_queue()
        self._set_status(f"Running scenario: {data['name']}")

        def worker() -> None:
            try:
                with capture_action_trace(self._trace_events.put):
                    result = run_scenario_data(data, bot_id=bot_id, dry_run=dry_run)
            except Exception as exc:
                self._worker_results.put((None, exc))
            else:
                self._worker_results.put((result, None))

        threading.Thread(target=worker, name="yaml-scenario", daemon=True).start()
        self.after(25, self._poll_worker)

    def _poll_worker(self) -> None:
        self._drain_trace_queue()
        try:
            result, error = self._worker_results.get_nowait()
        except Empty:
            self.after(25, self._poll_worker)
            return

        self._drain_trace_queue()
        if error is not None:
            self._append_output(f"\nERROR\n{type(error).__name__}: {error}\n")
            self._set_result("ERROR", "#B91C1C")
            self._set_status("Scenario failed.")
        else:
            self._append_output(f"\nFINAL RESULT\n{format_result(result)}\n")
            if getattr(result, "success", False):
                self._set_result("TRUE", "#15803D")
                self._set_status("Scenario completed.")
            else:
                self._set_result("FALSE", "#B91C1C")
                self._set_status("Scenario stopped on failure.")

        self._running = False
        self.run_button.configure(state="normal")

    def _clear_trace_queue(self) -> None:
        while True:
            try:
                self._trace_events.get_nowait()
            except Empty:
                return

    def _drain_trace_queue(self) -> None:
        while True:
            try:
                line = self._trace_events.get_nowait()
            except Empty:
                return
            self._append_output(line + "\n")

    def _set_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def _append_output(self, text: str) -> None:
        self.output.configure(state="normal")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")

    def _set_result(self, text: str, colour: str) -> None:
        self.result_label.configure(text=text, bg=colour)

    def _set_status(self, text: str) -> None:
        if self._status_callback is not None:
            self._status_callback(text)


__all__ = ["YamlScenarioEditor"]
