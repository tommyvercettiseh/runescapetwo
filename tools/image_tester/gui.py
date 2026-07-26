from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from .analyzer import analyze_template
from .storage import save_template_settings
from core.vision.areas import load_areas

ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "assets" / "images"
BG = "#080d18"
PANEL = "#111827"
TEXT = "#f6f7fb"
MUTED = "#9aa6bd"
BLUE = "#2f7df6"
GREEN = "#2bbf6a"


class ImageTesterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("RuneScape Two - Image Tester")
        root.geometry("880x640")
        root.configure(bg=BG)

        self.image = tk.StringVar()
        self.area = tk.StringVar(value="game")
        self.bot_id = tk.IntVar(value=int(os.getenv("BOT_ID", "1")))
        self.results: list[dict] = []
        self._build()

    def _build(self) -> None:
        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True, padx=18, pady=16)
        tk.Label(shell, text="Image Tester", bg=BG, fg=TEXT, font=("Segoe UI", 24, "bold")).pack(anchor="w")
        tk.Label(shell, text="Vergelijk alle template-methodes en sla de beste instellingen op.", bg=BG, fg=MUTED).pack(anchor="w", pady=(2, 14))

        controls = tk.Frame(shell, bg=PANEL)
        controls.pack(fill="x")
        tk.Label(controls, text="Template", bg=PANEL, fg=MUTED).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 4))
        self.image_box = ttk.Combobox(controls, textvariable=self.image, values=self._images(), state="readonly")
        self.image_box.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))
        tk.Label(controls, text="Area", bg=PANEL, fg=MUTED).grid(row=0, column=1, sticky="w", padx=12, pady=(12, 4))
        ttk.Combobox(controls, textvariable=self.area, values=self._areas(), state="readonly").grid(row=1, column=1, sticky="ew", padx=12, pady=(0, 12))
        tk.Label(controls, text="Bot", bg=PANEL, fg=MUTED).grid(row=0, column=2, sticky="w", padx=12, pady=(12, 4))
        ttk.Combobox(controls, textvariable=self.bot_id, values=(1, 2, 3, 4), state="readonly", width=6).grid(row=1, column=2, sticky="ew", padx=12, pady=(0, 12))
        tk.Button(controls, text="Analyseer", command=self.analyze, bg=BLUE, fg=TEXT, relief="flat", padx=20, pady=8).grid(row=1, column=3, padx=12, pady=(0, 12))
        controls.grid_columnconfigure(0, weight=1)
        controls.grid_columnconfigure(1, weight=1)

        columns = ("method", "shape", "color", "x", "y")
        self.tree = ttk.Treeview(shell, columns=columns, show="headings", height=15)
        for key, title, width in (("method", "Methode", 190), ("shape", "Vorm", 90), ("color", "Kleur", 90), ("x", "Abs. X", 80), ("y", "Abs. Y", 80)):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=14)

        row = tk.Frame(shell, bg=BG)
        row.pack(fill="x")
        self.status = tk.Label(row, text="Klaar", bg=BG, fg=MUTED)
        self.status.pack(side="left")
        tk.Button(row, text="Beste instellingen opslaan", command=self.save_best, bg=GREEN, fg=TEXT, relief="flat", padx=18, pady=9).pack(side="right")

    def _images(self) -> list[str]:
        return sorted(path.name for path in IMAGES.glob("*.png")) if IMAGES.exists() else []

    def _areas(self) -> list[str]:
        return [name for name, value in load_areas().items() if isinstance(value, dict)]

    def analyze(self) -> None:
        if not self.image.get():
            messagebox.showerror("Image Tester", "Kies eerst een template.")
            return
        try:
            self.results = analyze_template(self.image.get(), self.area.get() or None, bot_id=self.bot_id.get())
        except Exception as exc:
            messagebox.showerror("Image Tester", str(exc))
            return
        self.tree.delete(*self.tree.get_children())
        for row in self.results:
            self.tree.insert("", "end", values=(row["method"], f'{row["shape_score"]:.2f}', f'{row["color_score"]:.2f}', row["x"], row["y"]))
        region = self.results[0]["region"] if self.results else None
        self.status.config(text=f"{len(self.results)} methodes getest | bot {self.bot_id.get()} | region {region}")

    def save_best(self) -> None:
        if not self.results:
            messagebox.showerror("Image Tester", "Voer eerst een analyse uit.")
            return
        best = self.results[0]
        save_template_settings(
            self.image.get(),
            method=best["method"],
            min_shape=max(0.0, best["shape_score"] - 3.0),
            min_color=max(0.0, best["color_score"] - 5.0),
            area=self.area.get() or None,
        )
        messagebox.showinfo("Image Tester", "Beste instellingen opgeslagen.")


def main() -> None:
    root = tk.Tk()
    ImageTesterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
