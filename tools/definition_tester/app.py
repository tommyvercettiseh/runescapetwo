from __future__ import annotations

import time
import tkinter as tk
from dataclasses import asdict, is_dataclass
from tkinter import messagebox, ttk
from typing import Any

from .registry import categories, definitions_for, get_definition


def format_result(result: Any) -> str:
    if result is None:
        return "NIET GEVONDEN\n\nResultaat: None"

    if isinstance(result, bool):
        return f"RESULTAAT: {'TRUE' if result else 'FALSE'}"

    if is_dataclass(result):
        values = asdict(result)
        lines = ["GEVONDEN", ""]
        for key, value in values.items():
            lines.append(f"{key}: {value}")
        return "\n".join(lines)

    attributes = (
        "x",
        "y",
        "width",
        "height",
        "area_px",
        "centroid_x",
        "centroid_y",
        "safe_x",
        "safe_y",
        "safe_radius",
    )
    found_attributes = [name for name in attributes if hasattr(result, name)]
    if found_attributes:
        lines = ["GEVONDEN", ""]
        for name in found_attributes:
            lines.append(f"{name}: {getattr(result, name)}")
        return "\n".join(lines)

    return f"RESULTAAT\n\n{result!r}"


class DefinitionTester(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("RuneScape Two - Definition Tester")
        self.geometry("760x520")
        self.minsize(680, 460)

        self.category_var = tk.StringVar()
        self.definition_var = tk.StringVar()
        self.bot_id_var = tk.IntVar(value=1)
        self.description_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Klaar om te testen.")

        self._build_ui()
        self._load_categories()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(5, weight=1)

        ttk.Label(root, text="Definition Tester", font=("Segoe UI", 16, "bold")).grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(0, 16),
        )

        ttk.Label(root, text="Categorie").grid(row=1, column=0, sticky="w", pady=5)
        self.category_box = ttk.Combobox(
            root,
            textvariable=self.category_var,
            state="readonly",
        )
        self.category_box.grid(row=1, column=1, sticky="ew", padx=(12, 0), pady=5)
        self.category_box.bind("<<ComboboxSelected>>", self._on_category_changed)

        ttk.Label(root, text="Definition").grid(row=2, column=0, sticky="w", pady=5)
        self.definition_box = ttk.Combobox(
            root,
            textvariable=self.definition_var,
            state="readonly",
        )
        self.definition_box.grid(row=2, column=1, sticky="ew", padx=(12, 0), pady=5)
        self.definition_box.bind("<<ComboboxSelected>>", self._on_definition_changed)

        ttk.Label(root, text="Bot ID").grid(row=3, column=0, sticky="w", pady=5)
        self.bot_id_box = ttk.Spinbox(
            root,
            from_=1,
            to=4,
            textvariable=self.bot_id_var,
            width=8,
        )
        self.bot_id_box.grid(row=3, column=1, sticky="w", padx=(12, 0), pady=5)

        self.run_button = ttk.Button(root, text="Run definition", command=self._run_definition)
        self.run_button.grid(row=1, column=2, rowspan=3, sticky="ns", padx=(16, 0), pady=5)

        ttk.Label(root, textvariable=self.description_var, wraplength=650).grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(12, 10),
        )

        result_frame = ttk.LabelFrame(root, text="Resultaat", padding=10)
        result_frame.grid(row=5, column=0, columnspan=3, sticky="nsew")
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        self.result_text = tk.Text(result_frame, wrap="word", state="disabled")
        self.result_text.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(
            result_frame,
            orient="vertical",
            command=self.result_text.yview,
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.result_text.configure(yscrollcommand=scrollbar.set)

        ttk.Label(root, textvariable=self.status_var).grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="w",
            pady=(10, 0),
        )

    def _load_categories(self) -> None:
        values = categories()
        self.category_box["values"] = values
        if values:
            self.category_var.set(values[0])
            self._load_definitions(values[0])

    def _load_definitions(self, category: str) -> None:
        entries = definitions_for(category)
        names = [entry.name for entry in entries]
        self.definition_box["values"] = names
        if names:
            self.definition_var.set(names[0])
            self._update_description()
        else:
            self.definition_var.set("")
            self.description_var.set("")

    def _on_category_changed(self, _event: tk.Event) -> None:
        self._load_definitions(self.category_var.get())

    def _on_definition_changed(self, _event: tk.Event) -> None:
        self._update_description()

    def _update_description(self) -> None:
        category = self.category_var.get()
        name = self.definition_var.get()
        if not category or not name:
            self.description_var.set("")
            return
        self.description_var.set(get_definition(category, name).description)

    def _set_result(self, text: str) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.configure(state="disabled")

    def _run_definition(self) -> None:
        category = self.category_var.get()
        name = self.definition_var.get()

        if not category or not name:
            messagebox.showinfo("Selectie", "Selecteer eerst een definition.")
            return

        try:
            bot_id = int(self.bot_id_var.get())
            if bot_id < 1:
                raise ValueError
        except (TypeError, ValueError):
            messagebox.showerror("Bot ID", "Bot ID moet een positief geheel getal zijn.")
            return

        entry = get_definition(category, name)
        self.run_button.configure(state="disabled")
        self.status_var.set(f"Bezig met {category} / {name}...")
        self.update_idletasks()

        started = time.perf_counter()
        try:
            result = entry.function(bot_id)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._set_result(
                "FOUT\n\n"
                f"Type: {type(exc).__name__}\n"
                f"Melding: {exc}"
            )
            self.status_var.set(f"Mislukt na {elapsed_ms:.1f} ms")
        else:
            elapsed_ms = (time.perf_counter() - started) * 1000
            self._set_result(format_result(result))
            self.status_var.set(f"Klaar in {elapsed_ms:.1f} ms")
        finally:
            self.run_button.configure(state="normal")


if __name__ == "__main__":
    DefinitionTester().mainloop()
