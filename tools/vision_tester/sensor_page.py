from __future__ import annotations

import time
import tkinter as tk
from tkinter import messagebox, ttk

from core.vision.areas import load_areas
from .sensor_checks import (
    SUPPORTED_KINDS,
    SensorCheck,
    evaluate_sensor,
    load_sensor_checks,
    save_sensor_checks,
)


class SensorPage(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.running = False
        self.checks: dict[str, SensorCheck] = {}
        self.bot_id = tk.IntVar(value=1)
        self.name = tk.StringVar()
        self.kind = tk.StringVar(value="colour_exists")
        self.value = tk.StringVar()
        self.area = tk.StringVar(value="game")
        self.threshold = tk.IntVar(value=1)
        self.enabled = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Voeg sensoren toe en druk op Live.")
        self._build()
        self._load_all()
        self.after(500, self._tick)

    def _build(self) -> None:
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="Bot").pack(side="left")
        ttk.Combobox(
            top,
            textvariable=self.bot_id,
            values=(1, 2, 3, 4),
            state="readonly",
            width=6,
        ).pack(side="left", padx=(5, 12))
        self.live_button = ttk.Button(top, text="Live", command=self._toggle)
        self.live_button.pack(side="left", padx=3)
        ttk.Button(top, text="Eenmalig", command=self._once).pack(side="left", padx=3)
        ttk.Button(top, text="Vernieuwen", command=self._load_all).pack(side="left", padx=3)

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        left = ttk.LabelFrame(body, text="Live sensorstatus", padding=6)
        body.add(left, weight=3)
        columns = ("status", "name", "kind", "value", "area", "threshold")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", selectmode="browse")
        headings = {
            "status": "Resultaat",
            "name": "Sensor",
            "kind": "Type",
            "value": "Kleur/template",
            "area": "Area",
            "threshold": "Drempel",
        }
        widths = {"status": 95, "name": 180, "kind": 125, "value": 150, "area": 150, "threshold": 80}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="w")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._select)
        self.tree.tag_configure("true", foreground="#169447")
        self.tree.tag_configure("false", foreground="#c23b3b")
        self.tree.tag_configure("error", foreground="#c27a12")
        self.tree.tag_configure("off", foreground="#777777")

        editor = ttk.LabelFrame(body, text="Sensor toevoegen of aanpassen", padding=10)
        body.add(editor, weight=2)
        fields = (
            ("Naam", self.name),
            ("Waarde", self.value),
            ("Area", self.area),
            ("Drempel", self.threshold),
        )
        for row, (label, variable) in enumerate(fields):
            ttk.Label(editor, text=label).grid(row=row * 2, column=0, sticky="w", pady=(3, 0))
            if label == "Area":
                widget = ttk.Combobox(editor, textvariable=variable, values=sorted(load_areas()), state="readonly")
            elif label == "Drempel":
                widget = ttk.Spinbox(editor, from_=1, to=100000, textvariable=variable)
            else:
                widget = ttk.Entry(editor, textvariable=variable)
            widget.grid(row=row * 2 + 1, column=0, sticky="ew", pady=(0, 5))

        ttk.Label(editor, text="Type").grid(row=8, column=0, sticky="w", pady=(3, 0))
        ttk.Combobox(
            editor,
            textvariable=self.kind,
            values=SUPPORTED_KINDS,
            state="readonly",
        ).grid(row=9, column=0, sticky="ew", pady=(0, 5))
        ttk.Checkbutton(editor, text="Actief", variable=self.enabled).grid(row=10, column=0, sticky="w", pady=6)
        ttk.Button(editor, text="Opslaan", command=self._save).grid(row=11, column=0, sticky="ew", pady=3)
        ttk.Button(editor, text="Nieuwe invoer", command=self._clear_editor).grid(row=12, column=0, sticky="ew", pady=3)
        ttk.Button(editor, text="Verwijderen", command=self._delete).grid(row=13, column=0, sticky="ew", pady=3)
        editor.columnconfigure(0, weight=1)

        help_text = (
            "colour_exists: totaal aantal kleurpixels, bijvoorbeeld low_hp.\n"
            "colour_blob: minimaal één verbonden blob, bijvoorbeeld blue_target_found.\n"
            "image_exists: opgeslagen template gevonden, bijvoorbeeld in_combat."
        )
        ttk.Label(editor, text=help_text, justify="left", wraplength=330).grid(
            row=14, column=0, sticky="ew", pady=(15, 0)
        )
        ttk.Label(self, textvariable=self.status, padding=(10, 5)).pack(fill="x")

    def _load_all(self) -> None:
        try:
            self.checks = load_sensor_checks()
            self._refresh_tree()
            self.status.set(f"{len(self.checks)} sensor(en) geladen.")
        except Exception as exc:
            self.status.set(f"Fout: {exc}")

    def _refresh_tree(self, results: dict[str, tuple[str, str]] | None = None) -> None:
        selected = self.tree.selection()
        selected_name = selected[0] if selected else None
        self.tree.delete(*self.tree.get_children())
        for name, check in sorted(self.checks.items()):
            if results and name in results:
                display, tag = results[name]
            elif not check.enabled:
                display, tag = "UIT", "off"
            else:
                display, tag = "—", "off"
            self.tree.insert(
                "",
                "end",
                iid=name,
                values=(display, name, check.kind, check.value, check.area, check.threshold),
                tags=(tag,),
            )
        if selected_name in self.checks:
            self.tree.selection_set(selected_name)

    def _toggle(self) -> None:
        self.running = not self.running
        self.live_button.configure(text="Pauze" if self.running else "Live")

    def _once(self) -> None:
        self.running = False
        self.live_button.configure(text="Live")
        self._evaluate()

    def _tick(self) -> None:
        if self.running:
            self._evaluate()
        self.after(500, self._tick)

    def _evaluate(self) -> None:
        started = time.perf_counter()
        results: dict[str, tuple[str, str]] = {}
        for name, check in self.checks.items():
            if not check.enabled:
                results[name] = ("UIT", "off")
                continue
            try:
                value = evaluate_sensor(check, bot_id=self.bot_id.get())
                results[name] = (("TRUE" if value else "FALSE"), ("true" if value else "false"))
            except Exception as exc:
                results[name] = (f"ERROR: {str(exc)[:35]}", "error")
        self._refresh_tree(results)
        elapsed = (time.perf_counter() - started) * 1000.0
        self.status.set(f"Bot {self.bot_id.get()} | {len(results)} checks | {elapsed:.1f} ms")

    def _select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        check = self.checks[selected[0]]
        self.name.set(check.name)
        self.kind.set(check.kind)
        self.value.set(check.value)
        self.area.set(check.area)
        self.threshold.set(check.threshold)
        self.enabled.set(check.enabled)

    def _save(self) -> None:
        name = self.name.get().strip()
        if not name or not self.value.get().strip():
            messagebox.showerror("Sensor", "Naam en kleur/template zijn verplicht.")
            return
        try:
            check = SensorCheck(
                name=name,
                kind=self.kind.get(),
                value=self.value.get().strip(),
                area=self.area.get() or "game",
                threshold=max(1, int(self.threshold.get())),
                enabled=self.enabled.get(),
            )
            self.checks[name] = check
            save_sensor_checks(self.checks)
            self._refresh_tree()
            self.status.set(f"Sensor '{name}' opgeslagen.")
        except Exception as exc:
            messagebox.showerror("Sensor", str(exc))

    def _delete(self) -> None:
        name = self.name.get().strip()
        if name in self.checks:
            del self.checks[name]
            save_sensor_checks(self.checks)
            self._clear_editor()
            self._refresh_tree()

    def _clear_editor(self) -> None:
        self.name.set("")
        self.kind.set("colour_exists")
        self.value.set("")
        self.area.set("game")
        self.threshold.set(1)
        self.enabled.set(True)
        self.tree.selection_remove(self.tree.selection())
