from __future__ import annotations

from dataclasses import dataclass
import threading
import time
import tkinter as tk
from queue import Empty, SimpleQueue
from tkinter import messagebox, ttk
from typing import Any, Callable, Literal

from core import mouse_actions
from tools.definition_tester.registry import DEFINITIONS, get_definition
from tools.unified_tester.action_registry import ActionContext, ACTION_SPECS, get_action
from tools.unified_tester.result_utils import format_result, result_success


StepKind = Literal["sensor", "action"]
PaletteItem = tuple[StepKind, str, str]

STATUS_COLOURS = {
    "READY": "#6B7280",
    "RUNNING": "#2563EB",
    "TRUE": "#15803D",
    "DONE": "#15803D",
    "DRY": "#D97706",
    "FALSE": "#B91C1C",
    "ERROR": "#B91C1C",
    "SKIPPED": "#6B7280",
    "STOPPED": "#6B7280",
}


@dataclass
class BuilderStep:
    kind: StepKind
    category: str
    name: str
    image_name: str = ""
    protected_images: tuple[str, ...] = ()
    optional_images: tuple[str, ...] = ()
    pattern: str = "random_pattern"
    selection: str = "nearest"
    status: str = "READY"
    detail: str = ""


def _parse_images(text: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            value.strip()
            for value in text.split(",")
            if value.strip()
        )
    )


def _short_result(result: Any) -> str:
    text = format_result(result).replace("\n", " | ")
    return text if len(text) <= 180 else f"{text[:177]}..."


class ScenarioBuilder(ttk.Frame):
    """Small drag-and-drop builder for running registered sensors and actions."""

    def __init__(
        self,
        parent,
        *,
        bot_id_getter: Callable[[], int],
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(parent, padding=12)
        self._bot_id_getter = bot_id_getter
        self._status_callback = status_callback
        self._steps: list[BuilderStep] = []
        self._drag_item: PaletteItem | None = None
        self._running = False
        self._stop_requested = threading.Event()
        self._results: SimpleQueue[
            tuple[str, int, Any, Exception | None, float, bool | None]
        ] = SimpleQueue()

        self.search_var = tk.StringVar()
        self.live_var = tk.BooleanVar(value=False)
        self.stop_on_false_var = tk.BooleanVar(value=True)
        self.selected_name_var = tk.StringVar(value="Select a step.")
        self.image_var = tk.StringVar()
        self.protected_var = tk.StringVar()
        self.optional_var = tk.StringVar()
        self.pattern_var = tk.StringVar(value="random_pattern")
        self.selection_var = tk.StringVar(value="nearest")
        self.summary_var = tk.StringVar(value="Drag a block into the workflow or double-click it.")

        self._palette_items = self._build_palette_items()
        self._visible_palette_items: list[PaletteItem] = []

        self._build()
        self._draw_palette()

    @staticmethod
    def _build_palette_items() -> list[PaletteItem]:
        sensors = [
            ("sensor", entry.category, entry.name)
            for entry in DEFINITIONS
        ]
        actions = [
            ("action", "Action", spec.name)
            for spec in ACTION_SPECS
        ]
        return sensors + actions

    def _build(self) -> None:
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        controls = ttk.Frame(self)
        controls.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        controls.columnconfigure(7, weight=1)

        self.run_selected_button = ttk.Button(
            controls,
            text="Run selected",
            command=self._run_selected,
        )
        self.run_selected_button.grid(row=0, column=0, padx=(0, 8))
        self.run_all_button = ttk.Button(
            controls,
            text="Run all",
            command=self._run_all,
        )
        self.run_all_button.grid(row=0, column=1, padx=(0, 8))
        self.stop_button = ttk.Button(
            controls,
            text="Stop",
            command=self._stop,
            state="disabled",
        )
        self.stop_button.grid(row=0, column=2, padx=(0, 14))

        ttk.Checkbutton(
            controls,
            text="LIVE actions",
            variable=self.live_var,
            command=self._refresh_workflow,
        ).grid(row=0, column=3, padx=(0, 14))
        ttk.Checkbutton(
            controls,
            text="Stop on FALSE",
            variable=self.stop_on_false_var,
        ).grid(row=0, column=4, padx=(0, 14))

        ttk.Label(
            controls,
            text="Sensors always read the live screen. Actions are DRY until LIVE is enabled.",
        ).grid(row=0, column=7, sticky="e")

        self._build_palette()
        self._build_workflow()
        self._build_settings()

        summary = tk.Label(
            self,
            textvariable=self.summary_var,
            anchor="w",
            bg=STATUS_COLOURS["READY"],
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
        )
        summary.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        self.summary_bar = summary

    def _build_palette(self) -> None:
        frame = ttk.LabelFrame(self, text="Blocks", padding=8)
        frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        search = ttk.Entry(frame, textvariable=self.search_var, width=28)
        search.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search.bind("<KeyRelease>", lambda _event: self._draw_palette())

        self.palette = tk.Listbox(frame, width=34, exportselection=False)
        self.palette.grid(row=1, column=0, sticky="nsew")
        self.palette.bind("<Double-Button-1>", self._palette_double_click)
        self.palette.bind("<ButtonPress-1>", self._palette_press)
        self.palette.bind("<ButtonRelease-1>", self._palette_release)

        ttk.Button(frame, text="Add →", command=self._add_selected_palette).grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )

    def _build_workflow(self) -> None:
        frame = ttk.LabelFrame(self, text="Workflow", padding=8)
        frame.grid(row=1, column=1, sticky="nsew", padx=(0, 10))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

        columns = ("number", "kind", "name", "mode", "status", "detail")
        self.workflow = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=16,
        )
        headings = {
            "number": "#",
            "kind": "Type",
            "name": "Step",
            "mode": "Mode",
            "status": "Status",
            "detail": "Result",
        }
        widths = {
            "number": 38,
            "kind": 52,
            "name": 180,
            "mode": 58,
            "status": 70,
            "detail": 260,
        }
        for column in columns:
            self.workflow.heading(column, text=headings[column])
            self.workflow.column(column, width=widths[column], anchor="w")
        self.workflow.column("number", stretch=False)
        self.workflow.column("kind", stretch=False)
        self.workflow.column("mode", stretch=False)
        self.workflow.column("status", stretch=False)
        self.workflow.grid(row=0, column=0, sticky="nsew")
        self.workflow.bind("<<TreeviewSelect>>", self._workflow_selected)

        scrollbar = ttk.Scrollbar(frame, command=self.workflow.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.workflow.configure(yscrollcommand=scrollbar.set)

        buttons = ttk.Frame(frame)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(buttons, text="↑", width=4, command=lambda: self._move(-1)).pack(
            side="left",
            padx=(0, 6),
        )
        ttk.Button(buttons, text="↓", width=4, command=lambda: self._move(1)).pack(
            side="left",
            padx=(0, 10),
        )
        ttk.Button(buttons, text="Remove", command=self._remove_selected).pack(
            side="left"
        )
        ttk.Button(buttons, text="Clear", command=self._clear).pack(side="right")

    def _build_settings(self) -> None:
        frame = ttk.LabelFrame(self, text="Step settings", padding=8)
        frame.grid(row=1, column=2, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        ttk.Label(
            frame,
            textvariable=self.selected_name_var,
            font=("Segoe UI", 10, "bold"),
            wraplength=230,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        labels = (
            ("Image", self.image_var),
            ("Protected", self.protected_var),
            ("Optional", self.optional_var),
        )
        self.setting_entries: dict[str, ttk.Entry] = {}
        for row, (label, variable) in enumerate(labels, start=1):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(frame, textvariable=variable, width=24)
            entry.grid(row=row, column=1, sticky="ew", padx=(8, 0), pady=4)
            entry.bind("<FocusOut>", lambda _event: self._save_selected_settings())
            entry.bind("<Return>", lambda _event: self._save_selected_settings())
            self.setting_entries[label] = entry

        ttk.Label(frame, text="Pattern").grid(row=4, column=0, sticky="w", pady=4)
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
        self.pattern_box.grid(row=4, column=1, sticky="ew", padx=(8, 0), pady=4)
        self.pattern_box.bind("<<ComboboxSelected>>", lambda _event: self._save_selected_settings())

        ttk.Label(frame, text="Selection").grid(row=5, column=0, sticky="w", pady=4)
        self.selection_box = ttk.Combobox(
            frame,
            textvariable=self.selection_var,
            values=("nearest", "random_slot"),
            state="readonly",
            width=22,
        )
        self.selection_box.grid(row=5, column=1, sticky="ew", padx=(8, 0), pady=4)
        self.selection_box.bind("<<ComboboxSelected>>", lambda _event: self._save_selected_settings())

        ttk.Label(
            frame,
            text=(
                "Example: drag 'Bank open.' then 'Click inventory item'. "
                "Set the image on the click step and press Run all."
            ),
            wraplength=240,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(14, 0))

        self._set_settings_enabled(False)

    def _draw_palette(self) -> None:
        query = self.search_var.get().strip().lower()
        self._visible_palette_items = [
            item
            for item in self._palette_items
            if not query
            or query in item[1].lower()
            or query in item[2].lower()
            or query in item[0]
        ]
        self.palette.delete(0, "end")
        for kind, category, name in self._visible_palette_items:
            prefix = "IF" if kind == "sensor" else "DO"
            category_text = f"{category} · " if kind == "sensor" else ""
            self.palette.insert("end", f"{prefix}  {category_text}{name}")

    def _palette_item_at(self, y: int) -> PaletteItem | None:
        if not self._visible_palette_items:
            return None
        index = self.palette.nearest(y)
        if index < 0 or index >= len(self._visible_palette_items):
            return None
        return self._visible_palette_items[index]

    def _palette_press(self, event: tk.Event) -> None:
        if self._running:
            return
        self._drag_item = self._palette_item_at(event.y)
        if self._drag_item is not None:
            self.palette.configure(cursor="hand2")
            self._set_status("Drag the block into the workflow.")

    def _palette_release(self, event: tk.Event) -> None:
        item = self._drag_item
        self._drag_item = None
        self.palette.configure(cursor="")
        if item is None or self._running:
            return

        left = self.workflow.winfo_rootx()
        top = self.workflow.winfo_rooty()
        right = left + self.workflow.winfo_width()
        bottom = top + self.workflow.winfo_height()
        if left <= event.x_root <= right and top <= event.y_root <= bottom:
            self._add_palette_item(item)

    def _palette_double_click(self, event: tk.Event) -> None:
        item = self._palette_item_at(event.y)
        if item is not None:
            self._add_palette_item(item)

    def _add_selected_palette(self) -> None:
        selection = self.palette.curselection()
        if not selection:
            return
        self._add_palette_item(self._visible_palette_items[int(selection[0])])

    def _add_palette_item(self, item: PaletteItem) -> None:
        kind, category, name = item
        step = BuilderStep(kind=kind, category=category, name=name)
        self._steps.append(step)
        index = len(self._steps) - 1
        self._refresh_workflow(select_index=index)
        self._set_status(f"Added {name}")

    def _selected_index(self) -> int | None:
        selection = self.workflow.selection()
        if not selection:
            return None
        try:
            return int(selection[0])
        except (TypeError, ValueError):
            return None

    def _workflow_selected(self, _event: tk.Event | None = None) -> None:
        index = self._selected_index()
        if index is None or index >= len(self._steps):
            self.selected_name_var.set("Select a step.")
            self._set_settings_enabled(False)
            return

        step = self._steps[index]
        prefix = "IF" if step.kind == "sensor" else "DO"
        self.selected_name_var.set(f"{prefix}  {step.name}")
        self.image_var.set(step.image_name)
        self.protected_var.set(", ".join(step.protected_images))
        self.optional_var.set(", ".join(step.optional_images))
        self.pattern_var.set(step.pattern)
        self.selection_var.set(step.selection)

        if step.kind == "sensor":
            self._set_settings_enabled(False)
            return

        spec = get_action(step.name)
        self.setting_entries["Image"].configure(
            state="normal" if spec.uses_image else "disabled"
        )
        inventory_state = "normal" if spec.uses_inventory_options else "disabled"
        self.setting_entries["Protected"].configure(state=inventory_state)
        self.setting_entries["Optional"].configure(state=inventory_state)
        self.pattern_box.configure(
            state="readonly" if spec.uses_pattern else "disabled"
        )
        self.selection_box.configure(
            state="readonly" if spec.uses_selection else "disabled"
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
        step.protected_images = _parse_images(self.protected_var.get())
        step.optional_images = _parse_images(self.optional_var.get())
        step.pattern = self.pattern_var.get()
        step.selection = self.selection_var.get()
        self._refresh_workflow(select_index=index)

    def _mode(self, step: BuilderStep) -> str:
        if step.kind == "sensor":
            return "READ"
        return "LIVE" if self.live_var.get() else "DRY"

    def _refresh_workflow(self, select_index: int | None = None) -> None:
        current = self._selected_index() if select_index is None else select_index
        self.workflow.delete(*self.workflow.get_children())
        for index, step in enumerate(self._steps):
            kind = "IF" if step.kind == "sensor" else "DO"
            self.workflow.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    index + 1,
                    kind,
                    step.name,
                    self._mode(step),
                    step.status,
                    step.detail,
                ),
            )
        if current is not None and 0 <= current < len(self._steps):
            self.workflow.selection_set(str(current))
            self.workflow.focus(str(current))
            self.workflow.see(str(current))
        self._workflow_selected()

    def _move(self, direction: int) -> None:
        if self._running:
            return
        self._save_selected_settings()
        index = self._selected_index()
        if index is None:
            return
        target = index + direction
        if target < 0 or target >= len(self._steps):
            return
        self._steps[index], self._steps[target] = self._steps[target], self._steps[index]
        self._refresh_workflow(select_index=target)

    def _remove_selected(self) -> None:
        if self._running:
            return
        index = self._selected_index()
        if index is None:
            return
        del self._steps[index]
        next_index = min(index, len(self._steps) - 1) if self._steps else None
        self._refresh_workflow(select_index=next_index)

    def _clear(self) -> None:
        if self._running:
            return
        self._steps.clear()
        self._refresh_workflow()
        self._set_summary("READY", "Workflow cleared.")

    def _run_selected(self) -> None:
        self._save_selected_settings()
        index = self._selected_index()
        if index is None:
            messagebox.showinfo("Scenario", "Select a workflow step first.")
            return
        self._start_run([index])

    def _run_all(self) -> None:
        self._save_selected_settings()
        if not self._steps:
            messagebox.showinfo("Scenario", "Add at least one step first.")
            return
        self._start_run(list(range(len(self._steps))))

    def _confirm_live(self, indices: list[int]) -> bool:
        if not self.live_var.get():
            return True
        names = [
            self._steps[index].name
            for index in indices
            if self._steps[index].kind == "action"
        ]
        if not names:
            return True
        return messagebox.askyesno(
            "Run LIVE actions",
            "These actions will send real input:\n\n"
            + "\n".join(f"• {name}" for name in names)
            + "\n\nContinue?",
        )

    def _start_run(self, indices: list[int]) -> None:
        if self._running:
            return
        if not self._confirm_live(indices):
            return
        try:
            bot_id = int(self._bot_id_getter())
        except Exception as exc:
            messagebox.showerror("Scenario", str(exc))
            return

        live = self.live_var.get()
        stop_on_false = self.stop_on_false_var.get()
        self._stop_requested.clear()
        self._set_running(True)
        self._set_summary("RUNNING", "Running workflow.")

        for index in indices:
            self._steps[index].status = "READY"
            self._steps[index].detail = ""
        self._refresh_workflow(select_index=indices[0] if len(indices) == 1 else None)

        def worker() -> None:
            for position, index in enumerate(indices):
                if self._stop_requested.is_set():
                    self._results.put(("stopped", index, None, None, 0.0, None))
                    break

                self._results.put(("running", index, None, None, 0.0, None))
                step = self._steps[index]
                started = time.perf_counter()
                try:
                    result = self._execute_step(step, bot_id=bot_id, live=live)
                except Exception as exc:
                    elapsed = (time.perf_counter() - started) * 1000.0
                    self._results.put(("error", index, None, exc, elapsed, False))
                    if stop_on_false:
                        for skipped in indices[position + 1 :]:
                            self._results.put(("skipped", skipped, None, None, 0.0, None))
                        break
                else:
                    elapsed = (time.perf_counter() - started) * 1000.0
                    success = result_success(result)
                    self._results.put(("result", index, result, None, elapsed, success))
                    if stop_on_false and success is False:
                        for skipped in indices[position + 1 :]:
                            self._results.put(("skipped", skipped, None, None, 0.0, None))
                        break

            self._results.put(("done", -1, None, None, 0.0, None))

        threading.Thread(
            target=worker,
            name="scenario-builder-worker",
            daemon=True,
        ).start()
        self.after(25, self._poll_results)

    @staticmethod
    def _execute_step(step: BuilderStep, *, bot_id: int, live: bool) -> Any:
        if step.kind == "sensor":
            entry = get_definition(step.category, step.name)
            return entry.function(bot_id)

        spec = get_action(step.name)
        context = ActionContext(
            bot_id=bot_id,
            image_name=step.image_name,
            protected_images=step.protected_images,
            optional_images=step.optional_images,
            pattern=step.pattern,
            selection=step.selection,
            dry_run=not live,
        )
        return spec.execute(context)

    def _poll_results(self) -> None:
        try:
            event, index, result, error, elapsed, success = self._results.get_nowait()
        except Empty:
            self.after(25, self._poll_results)
            return

        if event == "running":
            self._steps[index].status = "RUNNING"
            self._steps[index].detail = ""
        elif event == "result":
            step = self._steps[index]
            if step.kind == "action" and not self.live_var.get() and success is not False:
                step.status = "DRY"
            elif success is True:
                step.status = "TRUE"
            elif success is False:
                step.status = "FALSE"
            else:
                step.status = "DONE"
            step.detail = f"{_short_result(result)} ({elapsed:.1f} ms)"
        elif event == "error" and error is not None:
            self._steps[index].status = "ERROR"
            self._steps[index].detail = f"{type(error).__name__}: {error} ({elapsed:.1f} ms)"
        elif event == "skipped":
            self._steps[index].status = "SKIPPED"
            self._steps[index].detail = "Previous step returned FALSE."
        elif event == "stopped":
            self._steps[index].status = "STOPPED"
            self._steps[index].detail = "Stop requested."
        elif event == "done":
            self._finish_run()
            return

        self._refresh_workflow(select_index=self._selected_index())
        self.after(25, self._poll_results)

    def _finish_run(self) -> None:
        statuses = {step.status for step in self._steps}
        if "ERROR" in statuses or "FALSE" in statuses:
            self._set_summary("FALSE", "Workflow stopped on a failed step.")
        elif "STOPPED" in statuses:
            self._set_summary("STOPPED", "Workflow stopped.")
        else:
            self._set_summary("TRUE", "Workflow complete.")
        self._set_running(False)

    def _stop(self) -> None:
        self._stop_requested.set()
        mouse_actions.emergency_stop()
        self._set_summary("STOPPED", "Stop requested. Use Reset stop before new LIVE input.")

    def _set_running(self, running: bool) -> None:
        self._running = running
        state = "disabled" if running else "normal"
        self.run_selected_button.configure(state=state)
        self.run_all_button.configure(state=state)
        self.stop_button.configure(state="normal" if running else "disabled")

    def _set_summary(self, status: str, message: str) -> None:
        self.summary_var.set(f"{status}.  {message}")
        self.summary_bar.configure(bg=STATUS_COLOURS.get(status, STATUS_COLOURS["READY"]))
        self._set_status(message)

    def _set_status(self, message: str) -> None:
        if self._status_callback is not None:
            self._status_callback(message)


__all__ = ["BuilderStep", "ScenarioBuilder"]
