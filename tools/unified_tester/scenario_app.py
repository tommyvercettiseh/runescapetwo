from __future__ import annotations

import threading
import tkinter as tk
from queue import Empty, SimpleQueue
from tkinter import messagebox, ttk

from core import mouse_actions
from tools.unified_tester.inventory_app import UnifiedTester as InventoryTester
from tools.unified_tester.scenario_runner import (
    BANKING_SCENARIO,
    ScenarioStep,
    ScenarioStepResult,
    execute_scenario_step,
    step_mode,
)


STATUS_COLOURS = {
    "READY.": "#6B7280",
    "RUNNING.": "#2563EB",
    "TRUE.": "#15803D",
    "DONE.": "#15803D",
    "DRY.": "#D97706",
    "FALSE.": "#B91C1C",
    "ERROR.": "#B91C1C",
    "SKIPPED.": "#6B7280",
    "STOPPED.": "#6B7280",
}


class UnifiedTester(InventoryTester):
    def __init__(self) -> None:
        super().__init__()

        self.scenario_image_var = tk.StringVar(value="Item_Axe")
        self.scenario_stop_on_failure_var = tk.BooleanVar(value=True)
        self.scenario_selected_var = tk.IntVar(value=0)
        self._scenario_live_vars: dict[int, tk.BooleanVar] = {}
        self._scenario_mode_labels: dict[int, ttk.Label] = {}
        self._scenario_status_labels: dict[int, tk.Label] = {}
        self._scenario_result_labels: dict[int, ttk.Label] = {}
        self._scenario_time_labels: dict[int, ttk.Label] = {}
        self._scenario_results: SimpleQueue[
            tuple[str, int, ScenarioStepResult | None, Exception | None]
        ] = SimpleQueue()
        self._scenario_stop_requested = threading.Event()

        self.geometry("1000x760")
        self.minsize(900, 680)
        self._add_scenario_tab()

    def _add_scenario_tab(self) -> None:
        self.scenario_tab = ttk.Frame(self.tabs, padding=14)
        self.tabs.insert(2, self.scenario_tab, text="Scenario")
        self.scenario_tab.columnconfigure(0, weight=1)
        self.scenario_tab.rowconfigure(3, weight=1)

        controls = ttk.Frame(self.scenario_tab)
        controls.grid(row=0, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Protected image").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Entry(
            controls,
            textvariable=self.scenario_image_var,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(10, 16),
        )
        ttk.Checkbutton(
            controls,
            text="Stop on failure",
            variable=self.scenario_stop_on_failure_var,
        ).grid(row=0, column=2, sticky="w", padx=(0, 16))

        self.scenario_run_selected_button = ttk.Button(
            controls,
            text="Run selected",
            command=self._run_selected_scenario_step,
        )
        self.scenario_run_selected_button.grid(row=0, column=3, padx=(0, 8))
        self.scenario_run_all_button = ttk.Button(
            controls,
            text="Run all",
            command=self._run_all_scenario_steps,
        )
        self.scenario_run_all_button.grid(row=0, column=4, padx=(0, 8))
        self.scenario_stop_button = ttk.Button(
            controls,
            text="Stop",
            command=self._stop_scenario,
            state="disabled",
        )
        self.scenario_stop_button.grid(row=0, column=5, padx=(0, 8))
        self.scenario_reset_button = ttk.Button(
            controls,
            text="Reset",
            command=self._reset_scenario,
        )
        self.scenario_reset_button.grid(row=0, column=6)

        ttk.Label(
            self.scenario_tab,
            text=(
                "Sensors and checks always read the live screen. "
                "Action steps send input only when Live is enabled."
            ),
        ).grid(row=1, column=0, sticky="w", pady=(10, 8))

        table = ttk.LabelFrame(
            self.scenario_tab,
            text="Banking scenario",
            padding=8,
        )
        table.grid(row=3, column=0, sticky="nsew")
        table.columnconfigure(6, weight=1)

        headers = (
            "",
            "Step",
            "Type",
            "Live",
            "Mode",
            "Status",
            "Result",
            "Time",
        )
        for column, text in enumerate(headers):
            ttk.Label(
                table,
                text=text,
                font=("Segoe UI", 9, "bold"),
            ).grid(
                row=0,
                column=column,
                sticky="w",
                padx=5,
                pady=(0, 6),
            )

        for index, step in enumerate(BANKING_SCENARIO):
            self._build_scenario_row(table, index, step)

        self.scenario_summary = tk.Label(
            self.scenario_tab,
            text="READY.",
            anchor="w",
            bg=STATUS_COLOURS["READY."],
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
        )
        self.scenario_summary.grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )

    def _build_scenario_row(
        self,
        parent: ttk.LabelFrame,
        index: int,
        step: ScenarioStep,
    ) -> None:
        row = index + 1
        ttk.Radiobutton(
            parent,
            variable=self.scenario_selected_var,
            value=index,
        ).grid(row=row, column=0, padx=5, pady=4)

        ttk.Label(parent, text=step.name).grid(
            row=row,
            column=1,
            sticky="w",
            padx=5,
            pady=4,
        )
        ttk.Label(parent, text=step.kind.upper()).grid(
            row=row,
            column=2,
            sticky="w",
            padx=5,
            pady=4,
        )

        live_var = tk.BooleanVar(value=False)
        self._scenario_live_vars[index] = live_var
        live_button = ttk.Checkbutton(
            parent,
            variable=live_var,
            command=lambda current=index: self._update_scenario_mode(current),
        )
        live_button.grid(row=row, column=3, padx=5, pady=4)
        if not step.live_supported:
            live_button.configure(state="disabled")

        mode_label = ttk.Label(
            parent,
            text=step_mode(step, False).upper(),
            width=6,
        )
        mode_label.grid(row=row, column=4, sticky="w", padx=5, pady=4)
        self._scenario_mode_labels[index] = mode_label

        status_label = tk.Label(
            parent,
            text="READY.",
            bg=STATUS_COLOURS["READY."],
            fg="white",
            width=10,
            padx=5,
            pady=3,
        )
        status_label.grid(row=row, column=5, sticky="ew", padx=5, pady=4)
        self._scenario_status_labels[index] = status_label

        result_label = ttk.Label(
            parent,
            text="",
            wraplength=360,
        )
        result_label.grid(
            row=row,
            column=6,
            sticky="w",
            padx=5,
            pady=4,
        )
        self._scenario_result_labels[index] = result_label

        time_label = ttk.Label(parent, text="", width=10)
        time_label.grid(row=row, column=7, sticky="e", padx=5, pady=4)
        self._scenario_time_labels[index] = time_label

    def _update_scenario_mode(self, index: int) -> None:
        step = BANKING_SCENARIO[index]
        mode = step_mode(step, self._scenario_live_vars[index].get())
        self._scenario_mode_labels[index].configure(text=mode.upper())

    def _set_scenario_row(
        self,
        index: int,
        status: str,
        message: str = "",
        elapsed_ms: float | None = None,
    ) -> None:
        colour = STATUS_COLOURS.get(status, STATUS_COLOURS["READY."])
        self._scenario_status_labels[index].configure(
            text=status,
            bg=colour,
        )
        self._scenario_result_labels[index].configure(text=message)
        self._scenario_time_labels[index].configure(
            text="" if elapsed_ms is None else f"{elapsed_ms:.1f} ms"
        )

    def _set_scenario_summary(self, status: str, message: str = "") -> None:
        text = status if not message else f"{status}  {message}"
        self.scenario_summary.configure(
            text=text,
            bg=STATUS_COLOURS.get(status, STATUS_COLOURS["READY."]),
        )

    def _set_running(self, running: bool) -> None:
        super()._set_running(running)
        state = "disabled" if running else "normal"
        for name in (
            "scenario_run_selected_button",
            "scenario_run_all_button",
            "scenario_reset_button",
        ):
            widget = getattr(self, name, None)
            if widget is not None:
                widget.configure(state=state)

        stop_button = getattr(self, "scenario_stop_button", None)
        if stop_button is not None:
            stop_button.configure(state="normal" if running else "disabled")

    def _live_indices(self, indices: list[int]) -> list[int]:
        return [
            index
            for index in indices
            if BANKING_SCENARIO[index].live_supported
            and self._scenario_live_vars[index].get()
        ]

    def _confirm_live(self, indices: list[int]) -> bool:
        live_indices = self._live_indices(indices)
        if not live_indices:
            return True

        names = ", ".join(BANKING_SCENARIO[index].name for index in live_indices)
        return messagebox.askyesno(
            "Run live actions",
            f"These steps will send real input:\n\n{names}\n\nContinue?",
        )

    def _run_selected_scenario_step(self) -> None:
        index = int(self.scenario_selected_var.get())
        self._start_scenario([index])

    def _run_all_scenario_steps(self) -> None:
        self._start_scenario(list(range(len(BANKING_SCENARIO))))

    def _start_scenario(self, indices: list[int]) -> None:
        if self._running:
            messagebox.showinfo("Busy", "A test is already running.")
            return
        if not self._confirm_live(indices):
            return

        try:
            bot_id = self._bot_id()
        except Exception as exc:
            messagebox.showerror("Scenario", str(exc))
            return

        image_name = self.scenario_image_var.get().strip()
        live_flags = {
            index: self._scenario_live_vars[index].get()
            for index in indices
        }
        stop_on_failure = self.scenario_stop_on_failure_var.get()

        self._scenario_stop_requested.clear()
        self._set_running(True)
        self._set_scenario_summary("RUNNING.")
        self.status_var.set("Running scenario.")

        for index in indices:
            self._set_scenario_row(index, "READY.")

        def worker() -> None:
            for position, index in enumerate(indices):
                if self._scenario_stop_requested.is_set():
                    self._scenario_results.put(("stopped", index, None, None))
                    break

                self._scenario_results.put(("running", index, None, None))
                step = BANKING_SCENARIO[index]
                try:
                    result = execute_scenario_step(
                        step,
                        bot_id=bot_id,
                        image_name=image_name,
                        live=live_flags[index],
                    )
                except Exception as exc:
                    self._scenario_results.put(("error", index, None, exc))
                    if stop_on_failure:
                        for skipped in indices[position + 1 :]:
                            self._scenario_results.put(
                                ("skipped", skipped, None, None)
                            )
                        break
                else:
                    self._scenario_results.put(("result", index, result, None))
                    if stop_on_failure and result.blocks_chain():
                        for skipped in indices[position + 1 :]:
                            self._scenario_results.put(
                                ("skipped", skipped, None, None)
                            )
                        break

            self._scenario_results.put(("done", -1, None, None))

        threading.Thread(
            target=worker,
            name="scenario-runner-worker",
            daemon=True,
        ).start()
        self.after(25, self._poll_scenario_worker)

    def _poll_scenario_worker(self) -> None:
        try:
            event, index, result, error = self._scenario_results.get_nowait()
        except Empty:
            self.after(25, self._poll_scenario_worker)
            return

        if event == "running":
            self._set_scenario_row(index, "RUNNING.")
        elif event == "result" and result is not None:
            self._set_scenario_row(
                index,
                result.status,
                result.message,
                result.elapsed_ms,
            )
        elif event == "error" and error is not None:
            self._set_scenario_row(
                index,
                "ERROR.",
                f"{type(error).__name__}: {error}",
            )
        elif event == "skipped":
            self._set_scenario_row(index, "SKIPPED.", "Previous step failed.")
        elif event == "stopped":
            self._set_scenario_row(index, "STOPPED.", "Scenario stopped.")
        elif event == "done":
            self._finish_scenario()
            return

        self.after(25, self._poll_scenario_worker)

    def _finish_scenario(self) -> None:
        statuses = [
            label.cget("text")
            for label in self._scenario_status_labels.values()
        ]
        if "ERROR." in statuses or "FALSE." in statuses:
            self._set_scenario_summary("FALSE.", "Scenario failed.")
        elif "STOPPED." in statuses:
            self._set_scenario_summary("STOPPED.", "Scenario stopped.")
        else:
            self._set_scenario_summary("TRUE.", "Scenario complete.")

        self.status_var.set("Scenario complete.")
        self._set_running(False)

    def _stop_scenario(self) -> None:
        self._scenario_stop_requested.set()
        mouse_actions.emergency_stop()
        self._set_scenario_summary("STOPPED.", "Stop requested.")
        self.status_var.set("Scenario stop requested.")

    def _reset_scenario(self) -> None:
        self._scenario_stop_requested.clear()
        mouse_actions.reset_emergency_stop()
        for index in range(len(BANKING_SCENARIO)):
            self._set_scenario_row(index, "READY.")
        self._set_scenario_summary("READY.")
        self.status_var.set("Ready.")


if __name__ == "__main__":
    UnifiedTester().mainloop()
