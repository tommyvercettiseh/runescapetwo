from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILE = ROOT / "config" / "definitions.json"


class DefinitionEditor(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("RuneScape Two - Definition Editor")
        self.geometry("860x560")
        self.minsize(760, 480)

        self.data: dict[str, Any] = {}
        self.selected_section: str | None = None
        self.selected_definition: str | None = None
        self.entries: dict[str, tk.Entry] = {}

        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(0, weight=1)

        left = ttk.Frame(container)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))

        ttk.Label(left, text="Definitions").pack(anchor="w", pady=(0, 6))
        self.tree = ttk.Treeview(left, show="tree", width=28)
        self.tree.pack(fill="y", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        right = ttk.Frame(container)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(1, weight=1)

        self.title_label = ttk.Label(
            right,
            text="Selecteer een definition",
            font=("Segoe UI", 14, "bold"),
        )
        self.title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        self.form = ttk.Frame(right)
        self.form.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.form.columnconfigure(1, weight=1)

        button_bar = ttk.Frame(right)
        button_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(18, 0))

        ttk.Button(button_bar, text="Opslaan", command=self._save_current).pack(side="left")
        ttk.Button(button_bar, text="Alles herladen", command=self._load).pack(side="left", padx=8)
        ttk.Button(button_bar, text="Open JSON-map", command=self._open_config_folder).pack(side="left")

        self.status = ttk.Label(right, text="")
        self.status.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _load(self) -> None:
        try:
            loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            messagebox.showerror("Fout", f"Kan definitions.json niet laden:\n{exc}")
            return

        if not isinstance(loaded, dict):
            messagebox.showerror("Fout", "definitions.json moet een JSON-object bevatten.")
            return

        self.data = loaded
        self.tree.delete(*self.tree.get_children())

        for section, definitions in sorted(self.data.items()):
            section_id = self.tree.insert("", "end", text=section, open=True)
            if not isinstance(definitions, dict):
                continue
            for name in sorted(definitions):
                self.tree.insert(section_id, "end", text=name, values=(section, name))

        self._clear_form()
        self.status.config(text=f"Geladen: {CONFIG_FILE}")

    def _on_select(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return

        item_id = selection[0]
        parent_id = self.tree.parent(item_id)
        if not parent_id:
            return

        section = self.tree.item(parent_id, "text")
        name = self.tree.item(item_id, "text")
        definition = self.data.get(section, {}).get(name)
        if not isinstance(definition, dict):
            return

        self.selected_section = section
        self.selected_definition = name
        self.title_label.config(text=f"{section}  /  {name}")
        self._build_form(definition)

    def _clear_form(self) -> None:
        for child in self.form.winfo_children():
            child.destroy()
        self.entries.clear()
        self.selected_section = None
        self.selected_definition = None
        self.title_label.config(text="Selecteer een definition")

    def _build_form(self, definition: dict[str, Any]) -> None:
        for child in self.form.winfo_children():
            child.destroy()
        self.entries.clear()

        for row, (key, value) in enumerate(definition.items()):
            ttk.Label(self.form, text=key).grid(
                row=row,
                column=0,
                sticky="w",
                padx=(0, 12),
                pady=5,
            )
            entry = ttk.Entry(self.form)
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            entry.insert(0, str(value))
            self.entries[key] = entry

    @staticmethod
    def _convert_value(original: Any, raw: str) -> Any:
        text = raw.strip()
        if isinstance(original, bool):
            lowered = text.lower()
            if lowered in {"true", "1", "yes", "ja"}:
                return True
            if lowered in {"false", "0", "no", "nee"}:
                return False
            raise ValueError(f"Ongeldige boolean: {raw}")
        if isinstance(original, int) and not isinstance(original, bool):
            return int(text)
        if isinstance(original, float):
            return float(text)
        if original is None and text.lower() in {"none", "null", ""}:
            return None
        return text

    def _save_current(self) -> None:
        if not self.selected_section or not self.selected_definition:
            messagebox.showinfo("Selectie", "Selecteer eerst een definition.")
            return

        definition = self.data[self.selected_section][self.selected_definition]

        try:
            for key, entry in self.entries.items():
                definition[key] = self._convert_value(definition.get(key), entry.get())

            CONFIG_FILE.write_text(
                json.dumps(self.data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except Exception as exc:
            messagebox.showerror("Fout", f"Opslaan mislukt:\n{exc}")
            return

        self.status.config(
            text=f"Opgeslagen: {self.selected_section}.{self.selected_definition}"
        )

    def _open_config_folder(self) -> None:
        try:
            import os

            os.startfile(CONFIG_FILE.parent)  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showerror("Fout", f"Map openen mislukt:\n{exc}")


if __name__ == "__main__":
    DefinitionEditor().mainloop()
