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

FILTERS = ("All", "Actions", "Definitions", "Interface", "Tools")


def _all_python_files() -> list[Path]:
    ignored_parts = {".git", ".venv", "__pycache__", "venv", "build", "dist"}
    files: list[Path] = []
    for path in ROOT.rglob("*.py"):
        relative = path.relative_to(ROOT)
        if any(part in ignored_parts for part in relative.parts):
            continue
        files.append(path)
    return sorted(files, key=lambda item: str(item.relative_to(ROOT)).casefold())


def _matches_filter(path: Path, category: str) -> bool:
    relative = path.relative_to(ROOT)
    parts = [part.casefold() for part in relative.parts]
    text = str(relative).replace("\\", "/").casefold()

    if category == "All":
        return True
    if category == "Actions":
        return bool(parts and parts[0] == "actions")
    if category == "Definitions":
        return bool(parts and parts[0] == "definitions")
    if category == "Tools":
        return bool(parts and parts[0] == "tools")
    if category == "Interface":
        return "interface" in text
    return True


def install_scenario_code_editor(tester_class, banking_scenario) -> None:
    original_add_tab = tester_class._add_scenario_tab

    def _add_scenario_tab_with_editor(self) -> None:
        original_add_tab(self)

        self._scenario_source_path: Path | None = None
        self._scenario_source_dirty = False
        self._scenario_source_files = _all_python_files()
        self.scenario_code_filter = tk.StringVar(value="Actions")
        self.scenario_code_query = tk.StringVar(value="")
        self.scenario_code_file = tk.StringVar(value="")

        self._scenario_source_trace = self.scenario_selected_var.trace_add(
            "write", lambda *_args: self._load_selected_step_source()
        )
        self.scenario_code_filter.trace_add("write", lambda *_args: self._refresh_code_browser())
        self.scenario_code_query.trace_add("write", lambda *_args: self._refresh_code_browser())

        # Put the code editor below the scenario table and keep the status bar last.
        self.scenario_summary.grid_configure(row=5)
        self.scenario_tab.rowconfigure(4, weight=0)

        editor = ttk.LabelFrame(self.scenario_tab, text="Code browser · local files", padding=8)
        editor.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        editor.columnconfigure(0, weight=1)

        browser = ttk.Frame(editor)
        browser.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        browser.columnconfigure(4, weight=1)

        ttk.Label(browser, text="Filter").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            browser,
            textvariable=self.scenario_code_filter,
            values=FILTERS,
            state="readonly",
            width=13,
        ).grid(row=0, column=1, padx=(6, 12), sticky="w")

        ttk.Label(browser, text="Search").grid(row=0, column=2, sticky="w")
        ttk.Entry(
            browser,
            textvariable=self.scenario_code_query,
            width=22,
        ).grid(row=0, column=3, padx=(6, 12), sticky="w")

        self.scenario_code_file_box = ttk.Combobox(
            browser,
            textvariable=self.scenario_code_file,
            values=[],
            state="readonly",
        )
        self.scenario_code_file_box.grid(row=0, column=4, sticky="ew")
        self.scenario_code_file_box.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._open_browser_file(),
        )

        top = ttk.Frame(editor)
        top.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        top.columnconfigure(0, weight=1)

        self.scenario_source_label = ttk.Label(top, text="Select a scenario step or browse a file.")
        self.scenario_source_label.grid(row=0, column=0, sticky="w")

        ttk.Button(
            top,
            text="Refresh files",
            command=self._rescan_code_browser,
        ).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(
            top,
            text="Reload file",
            command=self._reload_scenario_source,
        ).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(
            top,
            text="Save local",
            command=self._save_scenario_source_local,
        ).grid(row=0, column=3, padx=(8, 0))

        self.scenario_source_editor = tk.Text(
            editor,
            height=9,
            wrap="none",
            undo=True,
            font=("Consolas", 10),
            tabs=(32,),
        )
        self.scenario_source_editor.grid(row=2, column=0, sticky="ew")
        self.scenario_source_editor.bind("<<Modified>>", self._scenario_source_modified)

        hint = ttk.Label(
            editor,
            text=(
                "Browse all local Python files. Save local writes only to this repository on your PC; "
                "it does not push anything to GitHub."
            ),
        )
        hint.grid(row=3, column=0, sticky="w", pady=(5, 0))

        self._refresh_code_browser()
        self.after_idle(self._load_selected_step_source)

    def _filtered_browser_paths(self) -> list[Path]:
        category = self.scenario_code_filter.get() or "All"
        terms = [term for term in self.scenario_code_query.get().casefold().split() if term]
        paths = [path for path in self._scenario_source_files if _matches_filter(path, category)]
        if terms:
            paths = [
                path
                for path in paths
                if all(term in str(path.relative_to(ROOT)).casefold() for term in terms)
            ]
        return paths

    def _refresh_code_browser(self) -> None:
        if not hasattr(self, "scenario_code_file_box"):
            return
        values = [str(path.relative_to(ROOT)).replace("\\", "/") for path in self._filtered_browser_paths()]
        self.scenario_code_file_box.configure(values=values)
        if self.scenario_code_file.get() not in values:
            self.scenario_code_file.set(values[0] if values else "")

    def _rescan_code_browser(self) -> None:
        self._scenario_source_files = _all_python_files()
        self._refresh_code_browser()
        self.status_var.set(f"Code browser refreshed: {len(self._scenario_source_files)} Python files.")

    def _open_browser_file(self) -> None:
        relative = self.scenario_code_file.get().strip()
        if not relative:
            return
        self._load_source_path(ROOT / relative)

    def _selected_step_source_path(self) -> Path | None:
        try:
            index = int(self.scenario_selected_var.get())
            step = banking_scenario[index]
        except (ValueError, IndexError):
            return None
        relative = STEP_SOURCE_FILES.get(step.key)
        return ROOT / relative if relative else None

    def _load_source_path(self, path: Path, *, force: bool = False) -> None:
        if self._scenario_source_dirty and not force:
            if not messagebox.askyesno(
                "Unsaved local code",
                "Discard the unsaved code changes and open another file?",
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
        relative_text = str(relative).replace("\\", "/")
        self.scenario_source_editor.delete("1.0", "end")
        self.scenario_source_editor.insert("1.0", content)
        self.scenario_source_editor.edit_modified(False)
        self._scenario_source_dirty = False
        self.scenario_source_label.configure(text=relative_text)
        self.scenario_code_file.set(relative_text)
        self.status_var.set(f"Opened local source: {relative_text}")

    def _load_selected_step_source(self, *, force: bool = False) -> None:
        path = self._selected_step_source_path()
        if path is None:
            self._scenario_source_path = None
            self.scenario_source_label.configure(text="No source file mapped for this step.")
            self.scenario_source_editor.delete("1.0", "end")
            return
        self._load_source_path(path, force=force)

    def _reload_scenario_source(self) -> None:
        path = self._scenario_source_path
        if path is None:
            self.status_var.set("No local source file selected.")
            return
        self._load_source_path(path, force=True)

    def _scenario_source_modified(self, _event=None) -> None:
        if not self.scenario_source_editor.edit_modified():
            return
        self._scenario_source_dirty = True
        self.scenario_source_editor.edit_modified(False)
        path = self._scenario_source_path
        if path is not None:
            self.scenario_source_label.configure(
                text=f"{str(path.relative_to(ROOT)).replace(chr(92), '/')}  ·  LOCAL CHANGES"
            )

    def _save_scenario_source_local(self) -> None:
        path = self._scenario_source_path
        if path is None:
            self.status_var.set("No local source file selected.")
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
        relative = str(path.relative_to(ROOT)).replace("\\", "/")
        self.scenario_source_label.configure(text=relative)
        self.status_var.set(f"Saved locally: {relative}")

    tester_class._add_scenario_tab = _add_scenario_tab_with_editor
    tester_class._filtered_browser_paths = _filtered_browser_paths
    tester_class._refresh_code_browser = _refresh_code_browser
    tester_class._rescan_code_browser = _rescan_code_browser
    tester_class._open_browser_file = _open_browser_file
    tester_class._selected_step_source_path = _selected_step_source_path
    tester_class._load_source_path = _load_source_path
    tester_class._load_selected_step_source = _load_selected_step_source
    tester_class._reload_scenario_source = _reload_scenario_source
    tester_class._scenario_source_modified = _scenario_source_modified
    tester_class._save_scenario_source_local = _save_scenario_source_local


__all__ = ["FILTERS", "STEP_SOURCE_FILES", "install_scenario_code_editor"]
