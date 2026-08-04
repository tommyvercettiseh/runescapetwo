from __future__ import annotations

import json
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

ROOT = Path(__file__).resolve().parents[2]
BG = "#080d18"
PANEL = "#111827"
PANEL_2 = "#172033"
TEXT = "#f6f7fb"
MUTED = "#9aa6bd"
BLUE = "#2f7df6"
PURPLE = "#8b45e6"
GREEN = "#2bbf6a"
ORANGE = "#e58b2b"
BORDER = "#29354c"

TOOLS = (
    ("Unified Vision Tester", "Test kleuren, templates en sensoren in een werkruimte.", "tools.vision_tester.app", GREEN),
    ("Image Tester", "Test template matching en vergelijk OpenCV-methodes.", "tools.image_tester.gui", BLUE),
    ("Colour Tester", "Kalibreer HSV-ranges, areas, blobs en klikpadding live.", "tools.colour_tester.app", PURPLE),
)


class TesterHubApp:
    """Small launcher only; every tester remains an independent Python process."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("RuneScape Two - Tester Hub")
        root.geometry("1120x720")
        root.minsize(900, 620)
        root.configure(bg=BG)
        self.active_bot = tk.IntVar(value=1)
        self.status = tk.StringVar(value="Klaar")
        self._build()

    def _button(self, parent, text, command, bg=PANEL_2, **kwargs):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=TEXT,
                         activebackground=bg, activeforeground=TEXT, relief="flat",
                         bd=0, cursor="hand2", font=("Segoe UI", 10, "bold"), **kwargs)

    def _build(self) -> None:
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=18, pady=16)

        header = tk.Frame(shell, bg=BG)
        header.pack(fill="x", pady=(0, 14))
        tk.Label(header, text="RuneScape Two - Tester Hub", bg=BG, fg=TEXT,
                 font=("Segoe UI", 24, "bold")).pack(side="left")
        self._button(header, "Open repo", self.open_repo, bg=BLUE, padx=16, pady=8).pack(side="right")

        body = tk.Frame(shell, bg=BG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        tools_panel = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        tools_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(tools_panel, text="TESTERS", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 10))

        for name, description, module, colour in TOOLS:
            card = tk.Frame(tools_panel, bg=PANEL_2, highlightbackground=BORDER, highlightthickness=1)
            card.pack(fill="x", padx=14, pady=7)
            tk.Label(card, text=name, bg=PANEL_2, fg=TEXT,
                     font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
            tk.Label(card, text=description, bg=PANEL_2, fg=MUTED, wraplength=430,
                     justify="left").pack(anchor="w", padx=14)
            self._button(card, f"Start {name}", lambda m=module, n=name: self.launch(m, n),
                         bg=colour, pady=9).pack(fill="x", padx=14, pady=12)

        side = tk.Frame(body, bg=PANEL, width=340, highlightbackground=BORDER, highlightthickness=1)
        side.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        side.grid_propagate(False)
        tk.Label(side, text="BOT SELECTOR", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(16, 10))
        bot_row = tk.Frame(side, bg=PANEL)
        bot_row.pack(fill="x", padx=14)
        for bot_id in range(1, 5):
            tk.Radiobutton(bot_row, text=str(bot_id), variable=self.active_bot, value=bot_id,
                           indicatoron=False, width=5, bg=PANEL_2, fg=TEXT,
                           selectcolor=GREEN, activebackground=PANEL_2).pack(side="left", padx=2)

        tk.Label(side, text="PROJECTSTATUS", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(24, 10))
        self.project_info = tk.Label(side, text=self._project_status(), bg=PANEL, fg=MUTED,
                                     justify="left", anchor="nw", wraplength=300)
        self.project_info.pack(fill="x", padx=16)

        tk.Label(side, text="SNELLE ACTIES", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=16, pady=(24, 10))
        self._button(side, "Open configmap", lambda: self.open_path(ROOT / "config"), pady=9).pack(fill="x", padx=14, pady=4)
        self._button(side, "Open imagesmap", lambda: self.open_path(ROOT / "assets" / "images"), pady=9).pack(fill="x", padx=14, pady=4)
        self._button(side, "Open debugmap", lambda: self.open_path(ROOT / "debug"), bg=ORANGE, pady=9).pack(fill="x", padx=14, pady=4)
        self._button(side, "Run pytest", self.run_tests, bg=GREEN, pady=9).pack(fill="x", padx=14, pady=4)

        footer = tk.Frame(shell, bg=BG)
        footer.pack(fill="x", pady=(12, 0))
        tk.Label(footer, textvariable=self.status, bg=BG, fg=MUTED).pack(side="left")
        version = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "dev"
        tk.Label(footer, text=f"v{version}", bg=BG, fg=MUTED).pack(side="right")

    def launch(self, module: str, name: str) -> None:
        env = os.environ.copy()
        env["BOT_ID"] = str(self.active_bot.get())
        try:
            subprocess.Popen([sys.executable, "-m", module], cwd=ROOT, env=env)
        except Exception as exc:
            messagebox.showerror("Tester Hub", f"Kon {name} niet starten:\n{exc}")
            self.status.set(f"Start mislukt: {name}")
            return
        self.status.set(f"Gestart: {name} voor bot {self.active_bot.get()}")

    def run_tests(self) -> None:
        try:
            subprocess.Popen([sys.executable, "-m", "pytest"], cwd=ROOT)
            self.status.set("Pytest gestart in apart proces")
        except Exception as exc:
            messagebox.showerror("Tester Hub", str(exc))

    def open_repo(self) -> None:
        self.open_path(ROOT)

    def open_path(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(path)  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showerror("Tester Hub", str(exc))

    def _project_status(self) -> str:
        areas = self._json_count(ROOT / "config" / "areas.json")
        templates = len(list((ROOT / "assets" / "images").glob("*.png")))
        presets = self._json_count(ROOT / "config" / "colour_presets.json")
        return f"Areas: {areas}\nTemplates: {templates}\nColour presets: {presets}\nPython: {sys.version.split()[0]}"

    @staticmethod
    def _json_count(path: Path) -> int:
        if not path.exists():
            return 0
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            return len(data) if isinstance(data, dict) else 0
        except Exception:
            return 0


def main() -> None:
    root = tk.Tk()
    TesterHubApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
