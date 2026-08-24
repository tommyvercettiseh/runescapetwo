from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import ttk


class AreaEditorPage(ttk.Frame):
    """Small launcher page for the shared visual Area Maker."""

    def __init__(self, parent) -> None:
        super().__init__(parent, padding=18)
        self.process: subprocess.Popen | None = None
        self.status = tk.StringVar(master=parent, value="Area Editor ready.")
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text="Area Editor", font=("Segoe UI", 16, "bold")).grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(
            self,
            text=(
                "Uses the existing visual Area Maker: drag an area to move it, "
                "drag edges/corners to resize, filter by partial name/group, "
                "and save directly to areas.json."
            ),
            wraplength=820,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 16))
        ttk.Button(
            self,
            text="Open visual Area Editor",
            command=self.open_editor,
        ).grid(row=2, column=0, sticky="w")
        ttk.Label(self, textvariable=self.status).grid(
            row=3,
            column=0,
            sticky="w",
            pady=(12, 0),
        )

    def open_editor(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.status.set("Area Editor is already open.")
            return

        root = Path(__file__).resolve().parents[2]
        try:
            self.process = subprocess.Popen(
                [sys.executable, "-m", "tools.area_maker.app"],
                cwd=root,
            )
        except OSError as exc:
            self.status.set(f"Could not open Area Editor: {exc}")
            return

        self.status.set("Area Editor opened. Changes save to the shared area config.")

    def activate(self) -> None:
        pass

    def deactivate(self) -> None:
        pass

    def capture_hotkey(self) -> None:
        pass


__all__ = ["AreaEditorPage"]
