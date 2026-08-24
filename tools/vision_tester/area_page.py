from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tkinter as tk

import customtkinter as ctk

from . import ui


class AreaEditorPage(ctk.CTkFrame):
    """Small launcher page for the shared visual Area Maker."""

    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color=ui.BG)
        self.process: subprocess.Popen | None = None
        self.status = tk.StringVar(master=parent, value="Area Editor ready.")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        workspace.grid_columnconfigure(0, weight=1)

        card = ui.card(workspace)
        card.grid(row=0, column=0, sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        ui.label(card, "Area Editor", size=18, bold=True).grid(
            row=0,
            column=0,
            sticky="w",
            padx=20,
            pady=(20, 4),
        )
        ui.label(
            card,
            (
                "Open the visual Area Maker to move or resize areas, filter by "
                "partial name or group, and save directly to areas.json."
            ),
            muted=True,
            size=11,
            wraplength=760,
            justify="left",
        ).grid(
            row=1,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 16),
        )
        ui.button(
            card,
            "Open visual Area Editor",
            self.open_editor,
            primary=True,
            width=190,
        ).grid(
            row=2,
            column=0,
            sticky="w",
            padx=20,
            pady=(0, 18),
        )

        status_card = ui.card(workspace)
        status_card.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        ui.label(
            status_card,
            "",
            textvariable=self.status,
            muted=True,
            size=10,
        ).pack(anchor="w", padx=14, pady=10)

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
