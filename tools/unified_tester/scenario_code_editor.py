from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk


ROOT = Path(__file__).resolve().parents[2]

# Scenario step -> the real Python source used by that step.
STEP_SOURCE_FILES: dict[str, str] = {
    "find_bank": "actions/bank/find_bank.py",
    "bank_visible": "definitions/bank/is_bank_visible.py",
    "open_bank": "actions/bank/open_bank.py",
    "bank_open": "definitions/bank/is_bank_open.py",
    "bank_all": "definitions/bank/is_bank_all_selected.py",
    "inventory": "tools/unified_tester/inventory_checker.py",
    "protected_image": "definitions/inventory/get_inventory_item_slots.py",
    "bank_inventory": "actions/bank/bank_inventory.py",
    "close_bank": "actions/bank/close_bank.py",
    "bank_closed": "definitions/bank/is_bank_closed.py",
}


def install_scenario_code_editor(tester_class, banking_scenario) -> None:
    original_add_tab = tester_class._add_scenario_tab

    def _add_scenario_tab_with_editor(self) -> None:
        original_add_tab(self)

        self._scenario_source_path: Path | None = None
        self._scenario_source_dirty = False
        self._scenario_source_trace = self.scenario_selected_var.trace_add(
            "write", lambda *_args: self._load_selected_step_source()
        )

        # Put the code editor below the scenario table and keep the status bar last.
        self.scenario_summary.grid_configure(row=5)
        self.scenario_tab.rowconfigure(4, weight=0)

        editor = ttk.LabelFrame(self.scenario_tab, text="Step code · local file", padding=8)
        editor.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        editor.columnconfigure(0, weight=1)

        top = ttk.Frame(editor)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        top.columnconfigure(0, weight=1)

        self.scenario_source_label = ttk.Label(top, text="Select a scenario step.")
        self.scenario_source_label.grid(row=0, column=0, sticky="w")

        ttk.Button(
            top,
            text="Reload file",
            command=self._reload_scenario_source,
        ).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(
            top,
            text="Save local",
            command=self._save_scenario_source_local,
        ).grid(row=0, column=2, padx=(8, 0))

        self.scenario_source_editor = tk.Text(
            editor,
            height=9,
            wrap="none",
            undo=True,
            font=("Consolas", 10),
            tabs=(32,),
        )
        self.scenario_source_editor.grid(row=1, column=0, sticky="ew")
        self.scenario_source_editor.bind("<<Modified>>", self._scenario_source_modified)

        hint = ttk.Label(
            editor,
            text=(
                "Save local writes only to this repository on your PC. "
                "It does not push anything to GitHub."
            ),
        )
        hint.grid(row=2, column=0, sticky="w", pady=(5, 0))

        self.after_idle(self._load_selected_step_source)

    def _selected_step_source_path(self) -> Path | None:
        try:
            index = int(self.scenario_selected_var.get())
            step = banking_scenario[index]
        except (ValueError, IndexError):
            return None
        relative = STEP_SOURCE_FILES.get(step.key)
        return ROOT / relative if relative else None

    def _load_selected_step_source(self, *, force: bool = False) -> None:
        path = self._selected_step_source_path()
        if path is None:
            self._scenario_source_path = None
            self.scenario_source_label.configure(text="No source file mapped for this step.")
            self.scenario_source_editor.delete("1.0", "end")
            return

        if self._scenario_source_dirty and not force:
            if not messagebox.askyesno(
                "Unsaved local code",
                "Discard the unsaved code changes and open the selected step?",
                parent=self,
            ):
                return

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            self._scenario_source_path = None
            self.scenario_source_label.configure(text=f"Could not open: {path.name}")
            self.status_var.set(f"Could not read {path}: {exc}")
            return

        self._scenario_source_path = path
        relative = path.relative_to(ROOT)
        self.scenario_source_editor.delete("1.0", "end")
        self.scenario_source_editor.insert("1.0", content)
        self.scenario_source_editor.edit_modified(False)
        self._scenario_source_dirty = False
        self.scenario_source_label.configure(text=str(relative))
        self.status_var.set(f"Opened local source: {relative}")

    def _reload_scenario_source(self) -> None:
        self._load_selected_step_source(force=True)

    def _scenario_source_modified(self, _event=None) -> None:
        if not self.scenario_source_editor.edit_modified():
            return
        self._scenario_source_dirty = True
        self.scenario_source_editor.edit_modified(False)
        path = self._scenario_source_path
        if path is not None:
            self.scenario_source_label.configure(
                text=f"{path.relative_to(ROOT)}  ·  LOCAL CHANGES"
            )

    def _save_scenario_source_local(self) -> None:
        path = self._scenario_source_path
        if path is None:
            self.status_var.set("No scenario source file selected.")
            return

        content = self.scenario_source_editor.get("1.0", "end-1c")
        try:
            compile(content, str(path), "exec")
        except SyntaxError as exc:
            messagebox.showerror(
                "Python syntax error",
                f"Not saved. Line {exc.lineno}: {exc.msg}",
                parent=self,
            )
            return

        try:
            path.write_text(content + ("\n" if content and not content.endswith("\n") else ""), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Save local", str(exc), parent=self)
            return

        self._scenario_source_dirty = False
        self.scenario_source_editor.edit_modified(False)
        relative = path.relative_to(ROOT)
        self.scenario_source_label.configure(text=str(relative))
        self.status_var.set(f"Saved locally: {relative}")

    tester_class._add_scenario_tab = _add_scenario_tab_with_editor
    tester_class._selected_step_source_path = _selected_step_source_path
    tester_class._load_selected_step_source = _load_selected_step_source
    tester_class._reload_scenario_source = _reload_scenario_source
    tester_class._scenario_source_modified = _scenario_source_modified
    tester_class._save_scenario_source_local = _save_scenario_source_local


__all__ = ["STEP_SOURCE_FILES", "install_scenario_code_editor"]
