from __future__ import annotations

import time
import tkinter as tk
from dataclasses import asdict, is_dataclass
from tkinter import messagebox, ttk
from typing import Any, Callable

from actions.bank.bank_inventory import bank_inventory
from actions.bank.close_bank import close_bank
from actions.inventory.drop_inventory import drop_inventory
from tools.definition_tester.registry import categories, definitions_for, get_definition


def format_result(result: Any) -> str:
    if isinstance(result, bool):
        return f"RESULTAAT: {'TRUE' if result else 'FALSE'}"
    if result is None:
        return "RESULTAAT: None"
    if is_dataclass(result):
        return "\n".join(f"{key}: {value}" for key, value in asdict(result).items())
    if isinstance(result, (list, tuple, set)):
        return "\n".join(map(str, result)) or "Leeg resultaat"
    return repr(result)


def parse_images(text: str) -> list[str]:
    return [value.strip() for value in text.split(",") if value.strip()]


class UnifiedTester(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("RuneScape Two - Unified Tester")
        self.geometry("840x620")
        self.minsize(760, 540)

        self.bot_id_var = tk.IntVar(value=1)
        self.status_var = tk.StringVar(value="Klaar.")
        self.sensor_category_var = tk.StringVar()
        self.sensor_var = tk.StringVar()
        self.action_var = tk.StringVar(value="Bank inventory")
        self.exclude_images_var = tk.StringVar()
        self.pattern_var = tk.StringVar(value="random_pattern")
        self.selection_var = tk.StringVar(value="nearest")
        self.dry_run_var = tk.BooleanVar(value=True)

        self._build_ui()
        self._load_sensor_categories()
        self._update_action_fields()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(header, text="Unified Tester", font=("Segoe UI", 17, "bold")).pack(side="left")
        ttk.Label(header, text="Bot ID").pack(side="left", padx=(28, 8))
        ttk.Spinbox(header, from_=1, to=4, textvariable=self.bot_id_var, width=6).pack(side="left")

        self.tabs = ttk.Notebook(root)
        self.tabs.grid(row=1, column=0, sticky="nsew")
        root.rowconfigure(1, weight=1)

        self.sensor_tab = ttk.Frame(self.tabs, padding=14)
        self.action_tab = ttk.Frame(self.tabs, padding=14)
        self.tabs.add(self.sensor_tab, text="Sensors")
        self.tabs.add(self.action_tab, text="Actions")

        self._build_sensor_tab()
        self._build_action_tab()

        ttk.Label(root, textvariable=self.status_var).grid(row=2, column=0, sticky="w", pady=(10, 0))

    def _result_box(self, parent: ttk.Frame, row: int) -> tk.Text:
        frame = ttk.LabelFrame(parent, text="Resultaat", padding=8)
        frame.grid(row=row, column=0, columnspan=3, sticky="nsew", pady=(14, 0))
        parent.rowconfigure(row, weight=1)
        parent.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        text = tk.Text(frame, wrap="word", state="disabled")
        text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(frame, command=text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=scrollbar.set)
        return text

    def _build_sensor_tab(self) -> None:
        ttk.Label(self.sensor_tab, text="Categorie").grid(row=0, column=0, sticky="w", pady=5)
        self.sensor_category_box = ttk.Combobox(
            self.sensor_tab, textvariable=self.sensor_category_var, state="readonly"
        )
        self.sensor_category_box.grid(row=0, column=1, sticky="ew", padx=(12, 0), pady=5)
        self.sensor_category_box.bind("<<ComboboxSelected>>", self._on_sensor_category)

        ttk.Label(self.sensor_tab, text="Sensor").grid(row=1, column=0, sticky="w", pady=5)
        self.sensor_box = ttk.Combobox(self.sensor_tab, textvariable=self.sensor_var, state="readonly")
        self.sensor_box.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=5)

        ttk.Button(self.sensor_tab, text="Run sensor", command=self._run_sensor).grid(
            row=0, column=2, rowspan=2, sticky="ns", padx=(16, 0), pady=5
        )
        self.sensor_result = self._result_box(self.sensor_tab, 2)

    def _build_action_tab(self) -> None:
        labels = ("Action", "Exclude images", "Pattern", "Selection")
        for row, label in enumerate(labels):
            ttk.Label(self.action_tab, text=label).grid(row=row, column=0, sticky="w", pady=5)

        self.action_box = ttk.Combobox(
            self.action_tab,
            textvariable=self.action_var,
            values=("Bank inventory", "Drop inventory", "Close bank"),
            state="readonly",
        )
        self.action_box.grid(row=0, column=1, sticky="ew", padx=(12, 0), pady=5)
        self.action_box.bind("<<ComboboxSelected>>", lambda _event: self._update_action_fields())

        self.exclude_entry = ttk.Entry(self.action_tab, textvariable=self.exclude_images_var)
        self.exclude_entry.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=5)

        self.pattern_box = ttk.Combobox(
            self.action_tab,
            textvariable=self.pattern_var,
            values=("row", "snake", "column", "column_snake", "random", "random_pattern", "nearest"),
            state="readonly",
        )
        self.pattern_box.grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=5)

        self.selection_box = ttk.Combobox(
            self.action_tab,
            textvariable=self.selection_var,
            values=("nearest", "random_slot"),
            state="readonly",
        )
        self.selection_box.grid(row=3, column=1, sticky="ew", padx=(12, 0), pady=5)

        ttk.Checkbutton(self.action_tab, text="Dry run", variable=self.dry_run_var).grid(
            row=4, column=1, sticky="w", padx=(12, 0), pady=5
        )
        ttk.Button(self.action_tab, text="Run action", command=self._run_action).grid(
            row=0, column=2, rowspan=5, sticky="ns", padx=(16, 0), pady=5
        )
        ttk.Label(
            self.action_tab,
            text="Exclude images komma-gescheiden, bijvoorbeeld: Item_Axe, Item_Tinderbox",
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self.action_result = self._result_box(self.action_tab, 6)

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

    def _set_result(self, target: tk.Text, value: str) -> None:
        target.configure(state="normal")
        target.delete("1.0", "end")
        target.insert("1.0", value)
        target.configure(state="disabled")

    def _bot_id(self) -> int:
        bot_id = int(self.bot_id_var.get())
        if bot_id < 1:
            raise ValueError("Bot ID moet positief zijn")
        return bot_id

    def _execute(self, target: tk.Text, label: str, function: Callable[[], Any]) -> None:
        self.status_var.set(f"Bezig met {label}...")
        self.update_idletasks()
        started = time.perf_counter()
        try:
            result = function()
        except Exception as exc:
            self._set_result(target, f"FOUT\n\n{type(exc).__name__}: {exc}")
            self.status_var.set(f"Mislukt na {(time.perf_counter() - started) * 1000:.1f} ms")
        else:
            self._set_result(target, format_result(result))
            self.status_var.set(f"Klaar in {(time.perf_counter() - started) * 1000:.1f} ms")

    def _run_sensor(self) -> None:
        try:
            bot_id = self._bot_id()
            entry = get_definition(self.sensor_category_var.get(), self.sensor_var.get())
        except Exception as exc:
            messagebox.showerror("Sensor", str(exc))
            return
        self._execute(self.sensor_result, entry.name, lambda: entry.function(bot_id))

    def _update_action_fields(self) -> None:
        action = self.action_var.get()
        self.exclude_entry.configure(state="normal" if action != "Close bank" else "disabled")
        self.pattern_box.configure(state="readonly" if action == "Drop inventory" else "disabled")
        self.selection_box.configure(state="readonly" if action == "Bank inventory" else "disabled")

    def _run_action(self) -> None:
        try:
            bot_id = self._bot_id()
        except Exception as exc:
            messagebox.showerror("Action", str(exc))
            return

        action = self.action_var.get()
        images = parse_images(self.exclude_images_var.get())

        if not self.dry_run_var.get():
            if not messagebox.askyesno("Action uitvoeren", f"Echt uitvoeren: {action}?"):
                return

        if action == "Bank inventory":
            call = lambda: bank_inventory(
                bot_id,
                exclude_images=images,
                selection=self.selection_var.get(),
                dry_run=self.dry_run_var.get(),
            )
        elif action == "Drop inventory":
            call = lambda: drop_inventory(
                bot_id,
                exclude_images=images,
                pattern=self.pattern_var.get(),
                dry_run=self.dry_run_var.get(),
            )
        elif action == "Close bank":
            call = lambda: close_bank(bot_id)
        else:
            messagebox.showerror("Action", "Onbekende action")
            return

        self._execute(self.action_result, action, call)


if __name__ == "__main__":
    UnifiedTester().mainloop()
