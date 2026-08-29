from __future__ import annotations

import threading
import time
import tkinter as tk
from queue import Empty, SimpleQueue
from tkinter import messagebox, ttk
from typing import Any, Callable

from core import mouse_actions
from tools.definition_tester.registry import categories, definitions_for, get_definition
from tools.unified_tester.action_registry import ActionContext, action_names, get_action
from tools.unified_tester.result_utils import format_result, result_success


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
        self.geometry("900x700")
        self.minsize(800, 600)

        self.bot_id_var = tk.IntVar(value=1)
        self.status_var = tk.StringVar(value="Ready.")
        self.sensor_category_var = tk.StringVar()
        self.sensor_var = tk.StringVar()
        self.action_var = tk.StringVar(value=action_names()[0])
        self.action_image_var = tk.StringVar()
        self.exclude_images_var = tk.StringVar()
        self.optional_exclude_images_var = tk.StringVar()
        self.pattern_var = tk.StringVar(value="random_pattern")
        self.selection_var = tk.StringVar(value="nearest")
        self.dry_run_var = tk.BooleanVar(value=True)

        self._running = False
        self._result_bars: dict[tk.Text, tk.Label] = {}
        self._worker_results: SimpleQueue[
            tuple[tk.Text, str, float, Any, Exception | None]
        ] = SimpleQueue()

        self._build_ui()
        self._load_sensor_categories()
        self._update_action_fields()

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
        self.tabs.add(self.sensor_tab, text="Sensors")
        self.tabs.add(self.action_tab, text="Actions")

        self._build_sensor_tab()
        self._build_action_tab()

        ttk.Label(root, textvariable=self.status_var).grid(
            row=2,
            column=0,
            sticky="w",
            pady=(10, 0),
        )

    def _result_box(self, parent: ttk.Frame, row: int) -> tk.Text:
        frame = ttk.LabelFrame(parent, text="Result", padding=8)
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
            "Image",
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

        self.action_image_entry = ttk.Entry(
            self.action_tab,
            textvariable=self.action_image_var,
        )
        self.action_image_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(12, 0),
            pady=5,
        )

        self.exclude_entry = ttk.Entry(
            self.action_tab,
            textvariable=self.exclude_images_var,
        )
        self.exclude_entry.grid(
            row=2,
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
            row=3,
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
            row=4,
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
            row=5,
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
            row=6,
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
            rowspan=7,
            sticky="ns",
            padx=(16, 0),
            pady=5,
        )

        ttk.Label(
            self.action_tab,
            text=(
                "Image is used by image-based actions. Protected images must be found. "
                "Separate protected names with commas."
            ),
            wraplength=720,
        ).grid(
            row=7,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(8, 0),
        )
        self.action_result = self._result_box(self.action_tab, 8)

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

    def _set_result_bar(self, target: tk.Text, text: str, state: str) -> None:
        self._result_bars[target].configure(text=text, bg=BAR_COLOURS[state])

    @staticmethod
    def _set_result(target: tk.Text, value: str) -> None:
        target.configure(state="normal")
        target.delete("1.0", "end")
        target.insert("1.0", value)
        target.configure(state="disabled")

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
        try:
            target, _label, elapsed, result, error = self._worker_results.get_nowait()
        except Empty:
            self.after(25, self._poll_worker)
            return

        if error is not None:
            self._set_result(
                target,
                f"ERROR\n\n{type(error).__name__}: {error}",
            )
            self._set_result_bar(target, "ERROR.", "failure")
            self.status_var.set(f"Failed after {elapsed * 1000:.1f} ms.")
        else:
            self._set_result(target, format_result(result))
            success = result_success(result)
            if success is True:
                self._set_result_bar(target, "TRUE.", "success")
            elif success is False:
                self._set_result_bar(target, "FALSE.", "failure")
            else:
                self._set_result_bar(target, "DONE.", "neutral")
            self.status_var.set(f"Done in {elapsed * 1000:.1f} ms.")

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

        self.action_image_entry.configure(
            state="normal" if spec.uses_image else "disabled"
        )
        inventory_state = "normal" if spec.uses_inventory_options else "disabled"
        self.exclude_entry.configure(state=inventory_state)
        self.optional_exclude_entry.configure(state=inventory_state)
        self.pattern_box.configure(
            state="readonly" if spec.uses_pattern else "disabled"
        )
        self.selection_box.configure(
            state="readonly" if spec.uses_selection else "disabled"
        )

    def _action_context(self) -> ActionContext:
        return ActionContext(
            bot_id=self._bot_id(),
            image_name=self.action_image_var.get().strip(),
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

        self._execute(
            self.action_result,
            spec.name,
            lambda: spec.execute(context),
        )

    def _emergency_stop(self) -> None:
        mouse_actions.emergency_stop()
        self.status_var.set("Emergency stop active.")

    def _reset_emergency_stop(self) -> None:
        mouse_actions.reset_emergency_stop()
        self.status_var.set("Emergency stop reset.")


if __name__ == "__main__":
    UnifiedTester().mainloop()
