from __future__ import annotations

import inspect
import threading
import time
import tkinter as tk
from queue import Empty, SimpleQueue
from tkinter import messagebox, ttk
from typing import Any, Callable

from core import mouse_actions
from core.action_trace import capture_action_trace, trace
from tools.definition_tester.registry import categories, definitions_for, get_definition
from tools.unified_tester.action_registry import ActionContext, action_names, get_action
from tools.unified_tester.result_utils import format_result, result_success
from tools.unified_tester.target_inspector import TargetInfo, discover_targets


BAR_COLOURS = {
    "neutral": "#6B7280",
    "running": "#2563EB",
    "success": "#15803D",
    "failure": "#B91C1C",
}


def parse_images(text: str) -> list[str]:
    return list(
        dict.fromkeys(
            value.strip()
            for value in text.split(",")
            if value.strip()
        )
    )


class UnifiedTester(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("RuneScape Two - Unified Tester")
        self.geometry("1000x800")
        self.minsize(850, 650)

        self.bot_id_var = tk.IntVar(value=1)
        self.status_var = tk.StringVar(value="Ready.")
        self.sensor_category_var = tk.StringVar()
        self.sensor_var = tk.StringVar()
        self.action_var = tk.StringVar(value=action_names()[0])
        self.action_source_var = tk.StringVar()
        self.exclude_images_var = tk.StringVar()
        self.optional_exclude_images_var = tk.StringVar()
        self.pattern_var = tk.StringVar(value="random_pattern")
        self.selection_var = tk.StringVar(value="nearest")
        self.dry_run_var = tk.BooleanVar(value=True)
        self.target_var = tk.StringVar()
        self.target_source_var = tk.StringVar()

        self._running = False
        self._targets_by_name: dict[str, TargetInfo] = {}
        self._result_bars: dict[tk.Text, tk.Label] = {}
        self._worker_results: SimpleQueue[
            tuple[tk.Text, str, float, Any, Exception | None]
        ] = SimpleQueue()
        self._trace_events: SimpleQueue[str] = SimpleQueue()
        self._trace_target: tk.Text | None = None

        self._build_ui()
        self._load_sensor_categories()
        self._update_action_fields()
        self._load_targets()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(
            header,
            text="Unified Tester",
            font=("Segoe UI", 17, "bold"),
        ).pack(side="left")
        ttk.Label(header, text="Bot ID").pack(side="left", padx=(28, 8))
        ttk.Spinbox(
            header,
            from_=1,
            to=4,
            textvariable=self.bot_id_var,
            width=6,
        ).pack(side="left")

        ttk.Button(
            header,
            text="Emergency stop",
            command=self._emergency_stop,
        ).pack(side="right")
        ttk.Button(
            header,
            text="Reset stop",
            command=self._reset_emergency_stop,
        ).pack(side="right", padx=(0, 8))

        self.tabs = ttk.Notebook(root)
        self.tabs.grid(row=1, column=0, sticky="nsew")

        self.sensor_tab = ttk.Frame(self.tabs, padding=14)
        self.action_tab = ttk.Frame(self.tabs, padding=14)
        self.inspector_tab = ttk.Frame(self.tabs, padding=14)
        self.tabs.add(self.sensor_tab, text="Sensors")
        self.tabs.add(self.action_tab, text="Actions")
        self.tabs.add(self.inspector_tab, text="Inspector")

        self._build_sensor_tab()
        self._build_action_tab()
        self._build_inspector_tab()

        ttk.Label(root, textvariable=self.status_var).grid(
            row=2,
            column=0,
            sticky="w",
            pady=(10, 0),
        )

    def _result_box(self, parent: ttk.Frame, row: int) -> tk.Text:
        frame = ttk.LabelFrame(parent, text="Result / live trace", padding=8)
        frame.grid(
            row=row,
            column=0,
            columnspan=3,
            sticky="nsew",
            pady=(14, 0),
        )
        parent.rowconfigure(row, weight=1)
        parent.columnconfigure(1, weight=1)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        bar = tk.Label(
            frame,
            text="READY.",
            anchor="w",
            bg=BAR_COLOURS["neutral"],
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
        )
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        text = tk.Text(frame, wrap="word", state="disabled")
        text.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, command=text.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        text.configure(yscrollcommand=scrollbar.set)

        self._result_bars[text] = bar
        return text

    def _build_sensor_tab(self) -> None:
        ttk.Label(self.sensor_tab, text="Category").grid(
            row=0,
            column=0,
            sticky="w",
            pady=5,
        )
        self.sensor_category_box = ttk.Combobox(
            self.sensor_tab,
            textvariable=self.sensor_category_var,
            state="readonly",
        )
        self.sensor_category_box.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(12, 0),
            pady=5,
        )
        self.sensor_category_box.bind(
            "<<ComboboxSelected>>",
            self._on_sensor_category,
        )

        ttk.Label(self.sensor_tab, text="Sensor").grid(
            row=1,
            column=0,
            sticky="w",
            pady=5,
        )
        self.sensor_box = ttk.Combobox(
            self.sensor_tab,
            textvariable=self.sensor_var,
            state="readonly",
        )
        self.sensor_box.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(12, 0),
            pady=5,
        )

        self.sensor_run_button = ttk.Button(
            self.sensor_tab,
            text="Run sensor",
            command=self._run_sensor,
        )
        self.sensor_run_button.grid(
            row=0,
            column=2,
            rowspan=2,
            sticky="ns",
            padx=(16, 0),
            pady=5,
        )
        self.sensor_result = self._result_box(self.sensor_tab, 2)

    def _build_action_tab(self) -> None:
        labels = (
            "Action",
            "Protected images",
            "Optional exclusions",
            "Pattern",
            "Selection",
        )
        for row, label in enumerate(labels):
            ttk.Label(self.action_tab, text=label).grid(
                row=row,
                column=0,
                sticky="w",
                pady=5,
            )

        self.action_box = ttk.Combobox(
            self.action_tab,
            textvariable=self.action_var,
            values=action_names(),
            state="readonly",
        )
        self.action_box.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(12, 0),
            pady=5,
        )
        self.action_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._update_action_fields(),
        )

        self.exclude_entry = ttk.Entry(
            self.action_tab,
            textvariable=self.exclude_images_var,
        )
        self.exclude_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(12, 0),
            pady=5,
        )

        self.optional_exclude_entry = ttk.Entry(
            self.action_tab,
            textvariable=self.optional_exclude_images_var,
        )
        self.optional_exclude_entry.grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(12, 0),
            pady=5,
        )

        self.pattern_box = ttk.Combobox(
            self.action_tab,
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
        )
        self.pattern_box.grid(
            row=3,
            column=1,
            sticky="ew",
            padx=(12, 0),
            pady=5,
        )

        self.selection_box = ttk.Combobox(
            self.action_tab,
            textvariable=self.selection_var,
            values=("nearest", "random_slot"),
            state="readonly",
        )
        self.selection_box.grid(
            row=4,
            column=1,
            sticky="ew",
            padx=(12, 0),
            pady=5,
        )

        ttk.Checkbutton(
            self.action_tab,
            text="Dry run",
            variable=self.dry_run_var,
        ).grid(
            row=5,
            column=1,
            sticky="w",
            padx=(12, 0),
            pady=5,
        )

        self.action_run_button = ttk.Button(
            self.action_tab,
            text="Run action",
            command=self._run_action,
        )
        self.action_run_button.grid(
            row=0,
            column=2,
            rowspan=6,
            sticky="ns",
            padx=(16, 0),
            pady=5,
        )

        ttk.Label(
            self.action_tab,
            text=(
                "Protected images must be found. Otherwise, the action stops. "
                "Separate names with commas."
            ),
            wraplength=720,
        ).grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(8, 0),
        )

        source_frame = ttk.LabelFrame(
            self.action_tab,
            text="Production code",
            padding=8,
        )
        source_frame.grid(
            row=7,
            column=0,
            columnspan=3,
            sticky="nsew",
            pady=(12, 0),
        )
        source_frame.columnconfigure(0, weight=1)
        source_frame.rowconfigure(1, weight=1)

        ttk.Label(
            source_frame,
            textvariable=self.action_source_var,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        self.action_source_text = tk.Text(
            source_frame,
            height=10,
            wrap="none",
            state="disabled",
            font=("Consolas", 9),
        )
        self.action_source_text.grid(row=1, column=0, sticky="nsew")

        source_scrollbar = ttk.Scrollbar(
            source_frame,
            command=self.action_source_text.yview,
        )
        source_scrollbar.grid(row=1, column=1, sticky="ns")
        self.action_source_text.configure(yscrollcommand=source_scrollbar.set)

        self.action_result = self._result_box(self.action_tab, 8)

    def _build_inspector_tab(self) -> None:
        self.inspector_tab.columnconfigure(1, weight=1)
        self.inspector_tab.rowconfigure(2, weight=1)

        ttk.Label(self.inspector_tab, text="Production target").grid(
            row=0,
            column=0,
            sticky="w",
            pady=5,
        )
        self.target_box = ttk.Combobox(
            self.inspector_tab,
            textvariable=self.target_var,
            state="readonly",
        )
        self.target_box.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(12, 0),
            pady=5,
        )
        self.target_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._render_target(),
        )

        ttk.Label(self.inspector_tab, text="Source").grid(
            row=1,
            column=0,
            sticky="nw",
            pady=5,
        )
        ttk.Label(
            self.inspector_tab,
            textvariable=self.target_source_var,
        ).grid(
            row=1,
            column=1,
            sticky="w",
            padx=(12, 0),
            pady=5,
        )

        frame = ttk.LabelFrame(
            self.inspector_tab,
            text="Assigned production values",
            padding=8,
        )
        frame.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="nsew",
            pady=(12, 0),
        )
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        self.target_tree = ttk.Treeview(
            frame,
            columns=("setting", "value"),
            show="headings",
        )
        self.target_tree.heading("setting", text="Setting")
        self.target_tree.heading("value", text="Value")
        self.target_tree.column("setting", width=300, anchor="w")
        self.target_tree.column("value", width=420, anchor="w")
        self.target_tree.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.target_tree.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.target_tree.configure(yscrollcommand=scrollbar.set)

        ttk.Label(
            self.inspector_tab,
            text=(
                "Read-only. Values are loaded directly from definitions/*/*_target.py, "
                "so this view cannot drift away from production code."
            ),
            wraplength=760,
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

    def _load_sensor_categories(self) -> None:
        values = categories()
        self.sensor_category_box["values"] = values
        if values:
            self.sensor_category_var.set(values[0])
            self._load_sensors(values[0])

    def _load_sensors(self, category: str) -> None:
        values = [entry.name for entry in definitions_for(category)]
        self.sensor_box["values"] = values
        self.sensor_var.set(values[0] if values else "")

    def _on_sensor_category(self, _event: tk.Event) -> None:
        self._load_sensors(self.sensor_category_var.get())

    def _load_targets(self) -> None:
        targets = discover_targets()
        self._targets_by_name = {target.name: target for target in targets}
        names = tuple(self._targets_by_name)
        self.target_box["values"] = names
        self.target_var.set(names[0] if names else "")
        self._render_target()

    def _render_target(self) -> None:
        for item in self.target_tree.get_children():
            self.target_tree.delete(item)

        target = self._targets_by_name.get(self.target_var.get())
        if target is None:
            self.target_source_var.set("No production target modules found.")
            return

        self.target_source_var.set(target.source_path)
        for name, value in target.values:
            self.target_tree.insert("", "end", values=(name, str(value)))

    def _render_action_source(self) -> None:
        try:
            spec = get_action(self.action_var.get())
            source_path = inspect.getsourcefile(spec.source) or spec.source.__module__
            source = inspect.getsource(spec.source)
        except (KeyError, OSError, TypeError) as exc:
            self.action_source_var.set("Source unavailable")
            source = f"Unable to load source: {exc}"
        else:
            self.action_source_var.set(source_path)

        self.action_source_text.configure(state="normal")
        self.action_source_text.delete("1.0", "end")
        self.action_source_text.insert("1.0", source)
        self.action_source_text.configure(state="disabled")

    def _set_result_bar(self, target: tk.Text, text: str, state: str) -> None:
        self._result_bars[target].configure(text=text, bg=BAR_COLOURS[state])

    @staticmethod
    def _set_result(target: tk.Text, value: str) -> None:
        target.configure(state="normal")
        target.delete("1.0", "end")
        target.insert("1.0", value)
        target.configure(state="disabled")

    @staticmethod
    def _append_result(target: tk.Text, value: str) -> None:
        target.configure(state="normal")
        target.insert("end", value)
        target.see("end")
        target.configure(state="disabled")

    def _clear_trace_events(self) -> None:
        while True:
            try:
                self._trace_events.get_nowait()
            except Empty:
                return

    def _drain_trace_events(self) -> None:
        target = self._trace_target
        if target is None:
            return

        while True:
            try:
                line = self._trace_events.get_nowait()
            except Empty:
                return
            self._append_result(target, f"{line}\n")

    def _bot_id(self) -> int:
        bot_id = int(self.bot_id_var.get())
        if bot_id < 1:
            raise ValueError("Bot ID must be positive.")
        return bot_id

    def _set_running(self, running: bool) -> None:
        self._running = running
        state = "disabled" if running else "normal"
        self.sensor_run_button.configure(state=state)
        self.action_run_button.configure(state=state)

    def _execute(
        self,
        target: tk.Text,
        label: str,
        function: Callable[[], Any],
    ) -> None:
        if self._running:
            messagebox.showinfo("Busy", "A test is already running.")
            return

        self._set_running(True)
        self._set_result_bar(target, "RUNNING.", "running")
        self.status_var.set(f"Running {label}")

        def worker() -> None:
            started = time.perf_counter()
            try:
                result = function()
            except Exception as exc:
                self._worker_results.put(
                    (target, label, time.perf_counter() - started, None, exc)
                )
            else:
                self._worker_results.put(
                    (target, label, time.perf_counter() - started, result, None)
                )

        threading.Thread(
            target=worker,
            name="unified-tester-worker",
            daemon=True,
        ).start()
        self.after(25, self._poll_worker)

    def _poll_worker(self) -> None:
        self._drain_trace_events()
        try:
            target, _label, elapsed, result, error = self._worker_results.get_nowait()
        except Empty:
            self.after(25, self._poll_worker)
            return

        self._drain_trace_events()
        traced_action = target is self.action_result and self._trace_target is target

        if error is not None:
            error_text = f"ERROR\n\n{type(error).__name__}: {error}"
            if traced_action:
                self._append_result(target, f"\nFINAL ERROR\n{error_text}\n")
            else:
                self._set_result(target, error_text)
            self._set_result_bar(target, "ERROR.", "failure")
            self.status_var.set(f"Failed after {elapsed * 1000:.1f} ms.")
        else:
            formatted = format_result(result)
            if traced_action:
                self._append_result(target, f"\nFINAL RESULT\n{formatted}\n")
            else:
                self._set_result(target, formatted)
            success = result_success(result)
            if success is True:
                self._set_result_bar(target, "TRUE.", "success")
            elif success is False:
                self._set_result_bar(target, "FALSE.", "failure")
            else:
                self._set_result_bar(target, "DONE.", "neutral")
            self.status_var.set(f"Done in {elapsed * 1000:.1f} ms.")

        if traced_action:
            self._trace_target = None
        self._set_running(False)

    def _run_sensor(self) -> None:
        try:
            bot_id = self._bot_id()
            entry = get_definition(
                self.sensor_category_var.get(),
                self.sensor_var.get(),
            )
        except Exception as exc:
            messagebox.showerror("Sensor", str(exc))
            return

        self._trace_target = None
        self._execute(
            self.sensor_result,
            entry.name,
            lambda: entry.function(bot_id),
        )

    def _update_action_fields(self) -> None:
        try:
            spec = get_action(self.action_var.get())
        except KeyError:
            return

        inventory_state = "normal" if spec.uses_inventory_options else "disabled"
        self.exclude_entry.configure(state=inventory_state)
        self.optional_exclude_entry.configure(state=inventory_state)
        self.pattern_box.configure(
            state="readonly" if spec.uses_pattern else "disabled"
        )
        self.selection_box.configure(
            state="readonly" if spec.uses_selection else "disabled"
        )
        self._render_action_source()

    def _action_context(self) -> ActionContext:
        return ActionContext(
            bot_id=self._bot_id(),
            protected_images=tuple(parse_images(self.exclude_images_var.get())),
            optional_images=tuple(
                parse_images(self.optional_exclude_images_var.get())
            ),
            pattern=self.pattern_var.get(),
            selection=self.selection_var.get(),
            dry_run=self.dry_run_var.get(),
        )

    def _run_action(self) -> None:
        try:
            spec = get_action(self.action_var.get())
            context = self._action_context()
        except (KeyError, ValueError) as exc:
            messagebox.showerror("Action", str(exc))
            return

        if not context.dry_run:
            if not messagebox.askyesno("Run action", f"Run {spec.name}?"):
                return

        self._clear_trace_events()
        self._trace_target = self.action_result
        self._set_result(self.action_result, "")

        def execute_action() -> Any:
            with capture_action_trace(self._trace_events.put):
                trace(
                    f"[START] {spec.name} bot={context.bot_id} "
                    f"dry_run={context.dry_run}"
                )
                try:
                    result = spec.execute(context)
                except Exception as exc:
                    trace(f"[ERROR] {type(exc).__name__}: {exc}")
                    raise
                trace(f"[DONE] success={result_success(result)}")
                return result

        self._execute(
            self.action_result,
            spec.name,
            execute_action,
        )

    def _emergency_stop(self) -> None:
        mouse_actions.emergency_stop()
        self.status_var.set("Emergency stop active.")

    def _reset_emergency_stop(self) -> None:
        mouse_actions.reset_emergency_stop()
        self.status_var.set("Emergency stop reset.")


if __name__ == "__main__":
    UnifiedTester().mainloop()
