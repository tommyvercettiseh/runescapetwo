from __future__ import annotations

import csv
import json
import math
import statistics
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

# Make repository root importable when this file is started directly from scripts/.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from actions.click_object import click_object
from core import mouse, vision
from core.vision.object_presets import list_object_presets
from tools.vision_tester.sensor_checks import evaluate_sensor, load_sensor_checks


BOT_ID = 1

STRENGTH_IMAGE = "Chat_Strength"
STRENGTH_AREA = "Chat_Area"

CRAB_IMAGE = "Gemstone_Crab"
CRAB_AREA = "Bot_Area"

DEFAULT_CRAB_OBJECT = "gemrockcrab"
DEFAULT_CAVE_OBJECT = "cave"

MAX_ROUTINES = 5
CAVE_WAIT_SECONDS = 20
XP_WAIT_SECONDS = 10
MONITOR_POLL_SECONDS = 1.0

MOUSE_SAMPLE_SECONDS = 0.008
MOUSE_LOG_DIR = ROOT / "logs" / "mouse_movements"
MOUSE_SUMMARY_PATH = MOUSE_LOG_DIR / "summary.jsonl"


class MouseTrace:
    """Sample the real Windows cursor during one object click and persist the path."""

    def __init__(self, action: str, object_name: str) -> None:
        self.action = action
        self.object_name = object_name
        self.started_at = time.perf_counter()
        self.started_wall = datetime.now()
        self.points: list[tuple[float, int, int]] = []
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)

    def start(self) -> None:
        MOUSE_LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._capture()
        self._thread.start()

    def _capture(self) -> None:
        try:
            x, y = mouse.position()
            self.points.append((time.perf_counter() - self.started_at, int(x), int(y)))
        except Exception:
            pass

    def _sample_loop(self) -> None:
        while not self._stop_event.wait(MOUSE_SAMPLE_SECONDS):
            self._capture()

    @staticmethod
    def _path_distance(points: list[tuple[float, int, int]]) -> float:
        return sum(
            math.hypot(b[1] - a[1], b[2] - a[2])
            for a, b in zip(points, points[1:])
        )

    @staticmethod
    def _direction_changes(points: list[tuple[float, int, int]]) -> int:
        vectors: list[tuple[float, float]] = []
        for a, b in zip(points, points[1:]):
            dx = b[1] - a[1]
            dy = b[2] - a[2]
            if dx or dy:
                vectors.append((dx, dy))

        if len(vectors) < 2:
            return 0

        changes = 0
        previous_angle = math.atan2(vectors[0][1], vectors[0][0])
        for dx, dy in vectors[1:]:
            angle = math.atan2(dy, dx)
            delta = abs((angle - previous_angle + math.pi) % (2 * math.pi) - math.pi)
            if delta >= math.radians(18):
                changes += 1
            previous_angle = angle
        return changes

    def stop(self, result=None, error: str | None = None) -> dict:
        self._stop_event.set()
        self._thread.join(timeout=0.25)
        self._capture()

        duration = max(0.0, time.perf_counter() - self.started_at)
        points = self.points[:]

        if points:
            start = (points[0][1], points[0][2])
            end = (points[-1][1], points[-1][2])
            straight = math.hypot(end[0] - start[0], end[1] - start[1])
            xs = [point[1] for point in points]
            ys = [point[2] for point in points]
            bbox = [min(xs), min(ys), max(xs), max(ys)]
        else:
            start = end = None
            straight = 0.0
            bbox = None

        distance = self._path_distance(points)
        ratio = distance / straight if straight >= 1.0 else (1.0 if distance < 1.0 else 0.0)
        unique_points = len({(point[1], point[2]) for point in points})
        direction_changes = self._direction_changes(points)

        engine = getattr(result, "engine", "unknown") if result is not None else "unknown"
        fallback_used = bool(getattr(result, "fallback_used", False)) if result is not None else False
        success = bool(result) if result is not None else False

        stamp = self.started_wall.strftime("%Y%m%d_%H%M%S_%f")
        safe_object = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in self.object_name)
        csv_path = MOUSE_LOG_DIR / f"{stamp}_{self.action.lower()}_{safe_object}.csv"

        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["t_ms", "x", "y"])
            for elapsed, x, y in points:
                writer.writerow([round(elapsed * 1000.0, 3), x, y])

        summary = {
            "timestamp": self.started_wall.isoformat(timespec="milliseconds"),
            "action": self.action,
            "object": self.object_name,
            "success": success,
            "engine": engine,
            "fallback_used": fallback_used,
            "error": error or getattr(result, "error", None),
            "duration_ms": round(duration * 1000.0, 1),
            "samples": len(points),
            "unique_points": unique_points,
            "start": start,
            "end": end,
            "path_distance_px": round(distance, 1),
            "straight_distance_px": round(straight, 1),
            "path_ratio": round(ratio, 3),
            "direction_changes": direction_changes,
            "bbox": bbox,
            "csv": str(csv_path.relative_to(ROOT)),
        }

        with MOUSE_SUMMARY_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(summary, ensure_ascii=False) + "\n")

        return {"summary": summary, "points": points}


class CrabTestUI:
    BG = "#0d1117"
    CARD = "#161b22"
    CARD_2 = "#1c2128"
    BORDER = "#30363d"
    TEXT = "#f0f6fc"
    MUTED = "#8b949e"
    BLUE = "#58a6ff"
    GREEN = "#3fb950"
    RED = "#f85149"
    AMBER = "#d29922"
    PURPLE = "#bc8cff"

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Gemstone Crab Lab")
        self.root.geometry("980x760")
        self.root.minsize(900, 700)
        self.root.configure(bg=self.BG)

        self.running = False
        self.paused = False
        self.stop_requested = False
        self.run_event = threading.Event()
        self.run_event.set()
        self.mouse_history: list[dict] = []

        self.status_var = tk.StringVar(value="IDLE")
        self.routine_var = tk.StringVar(value=f"0 / {MAX_ROUTINES}")
        self.timer_var = tk.StringVar(value="-")
        self.mouse_metrics_var = tk.StringVar(value="Nog geen movement")
        self.mouse_file_var = tk.StringVar(value="-")

        self.crab_object_var = tk.StringVar(value=DEFAULT_CRAB_OBJECT)
        self.cave_object_var = tk.StringVar(value=DEFAULT_CAVE_OBJECT)

        self.pill_values: dict[str, tk.Label] = {}

        self._configure_styles()
        self._build_ui()
        self.refresh_object_presets(log=False)
        self.sensor_checks = load_sensor_checks()

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Modern.TCombobox",
            fieldbackground=self.CARD_2,
            background=self.CARD_2,
            foreground=self.TEXT,
            arrowcolor=self.TEXT,
            bordercolor=self.BORDER,
            lightcolor=self.BORDER,
            darkcolor=self.BORDER,
            padding=7,
        )
        style.map(
            "Modern.TCombobox",
            fieldbackground=[("readonly", self.CARD_2), ("disabled", self.CARD)],
            foreground=[("readonly", self.TEXT), ("disabled", self.MUTED)],
        )
        style.configure(
            "Modern.TButton",
            background=self.CARD_2,
            foreground=self.TEXT,
            borderwidth=0,
            padding=(12, 8),
            font=("Segoe UI Semibold", 9),
        )
        style.map("Modern.TButton", background=[("active", "#262c36")])

    def _build_ui(self) -> None:
        outer = tk.Frame(self.root, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=18, pady=16)

        header = tk.Frame(outer, bg=self.BG)
        header.pack(fill="x")
        tk.Label(
            header,
            text="Gemstone Crab Lab",
            bg=self.BG,
            fg=self.TEXT,
            font=("Segoe UI Semibold", 22),
        ).pack(side="left")
        tk.Label(
            header,
            text="live routine + mouse telemetry",
            bg=self.BG,
            fg=self.MUTED,
            font=("Segoe UI", 10),
        ).pack(side="left", padx=(12, 0), pady=(8, 0))

        pills = tk.Frame(outer, bg=self.BG)
        pills.pack(fill="x", pady=(14, 12))
        self._make_pill(pills, "MODE", "IDLE", self.MUTED)
        self._make_pill(pills, "LOGIN", "WAIT", self.MUTED)
        self._make_pill(pills, "CRAB", "WAIT", self.MUTED)
        self._make_pill(pills, "XP", "WAIT", self.MUTED)
        self._make_pill(pills, "ACTION", "IDLE", self.MUTED)
        self._make_pill(pills, "MOUSE", "IDLE", self.MUTED)

        top_grid = tk.Frame(outer, bg=self.BG)
        top_grid.pack(fill="x")
        top_grid.columnconfigure(0, weight=1)
        top_grid.columnconfigure(1, weight=1)

        routine_card = self._card(top_grid, "Routine")
        routine_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))

        rows = [
            ("Status", self.status_var),
            ("Routine", self.routine_var),
            ("Timer", self.timer_var),
        ]
        for index, (label, variable) in enumerate(rows):
            tk.Label(
                routine_card,
                text=label.upper(),
                bg=self.CARD,
                fg=self.MUTED,
                font=("Segoe UI Semibold", 8),
            ).grid(row=index + 1, column=0, sticky="w", pady=5)
            tk.Label(
                routine_card,
                textvariable=variable,
                bg=self.CARD,
                fg=self.TEXT,
                font=("Segoe UI Semibold", 10),
            ).grid(row=index + 1, column=1, sticky="w", padx=(14, 0), pady=5)

        object_card = self._card(top_grid, "Object routing")
        object_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        object_card.columnconfigure(1, weight=1)

        self.crab_combo = self._object_row(
            object_card,
            row=1,
            label="Crab",
            variable=self.crab_object_var,
            test_label="CRAB",
        )
        self.cave_combo = self._object_row(
            object_card,
            row=2,
            label="Cave",
            variable=self.cave_object_var,
            test_label="CAVE",
        )
        ttk.Button(
            object_card,
            text="Refresh presets",
            style="Modern.TButton",
            command=self.refresh_object_presets,
        ).grid(row=3, column=1, sticky="w", pady=(10, 0))

        controls = tk.Frame(outer, bg=self.BG)
        controls.pack(fill="x", pady=(0, 14))

        self.start_button = ttk.Button(
            controls,
            text="RUN",
            style="Modern.TButton",
            command=self.start,
        )
        self.start_button.pack(side="left")

        self.pause_button = ttk.Button(
            controls,
            text="PAUSE",
            style="Modern.TButton",
            command=self.pause,
            state="disabled",
        )
        self.pause_button.pack(side="left", padx=(8, 0))

        self.stop_button = ttk.Button(
            controls,
            text="STOP",
            style="Modern.TButton",
            command=self.stop,
            state="disabled",
        )
        self.stop_button.pack(side="left", padx=8)

        ttk.Button(
            controls,
            text="CLEAR LOG",
            style="Modern.TButton",
            command=self.clear_log,
        ).pack(side="right")

        middle = tk.Frame(outer, bg=self.BG)
        middle.pack(fill="both", expand=True, pady=(14, 0))
        middle.columnconfigure(0, weight=3)
        middle.columnconfigure(1, weight=2)
        middle.rowconfigure(0, weight=1)

        log_card = self._card(middle, "Activity log")
        log_card.grid(row=0, column=0, sticky="nsew", padx=(0, 7))
        log_card.rowconfigure(1, weight=1)
        log_card.columnconfigure(0, weight=1)

        self.log_box = tk.Text(
            log_card,
            bg="#0b0f14",
            fg="#c9d1d9",
            insertbackground=self.TEXT,
            relief="flat",
            borderwidth=0,
            font=("Cascadia Mono", 9),
            padx=10,
            pady=8,
            state="disabled",
        )
        self.log_box.grid(row=1, column=0, sticky="nsew")

        mouse_card = self._card(middle, "Mouse movement")
        mouse_card.grid(row=0, column=1, sticky="nsew", padx=(7, 0))
        mouse_card.columnconfigure(0, weight=1)
        mouse_card.rowconfigure(2, weight=1)

        tk.Label(
            mouse_card,
            textvariable=self.mouse_metrics_var,
            bg=self.CARD,
            fg=self.TEXT,
            justify="left",
            anchor="w",
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self.path_canvas = tk.Canvas(
            mouse_card,
            bg="#0b0f14",
            highlightthickness=1,
            highlightbackground=self.BORDER,
            height=250,
        )
        self.path_canvas.grid(row=2, column=0, sticky="nsew")

        tk.Label(
            mouse_card,
            textvariable=self.mouse_file_var,
            bg=self.CARD,
            fg=self.MUTED,
            justify="left",
            anchor="w",
            wraplength=340,
            font=("Segoe UI", 8),
        ).grid(row=3, column=0, sticky="ew", pady=(8, 0))


    def _card(self, parent, title: str) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg=self.CARD,
            highlightthickness=1,
            highlightbackground=self.BORDER,
            padx=14,
            pady=12,
        )
        tk.Label(
            frame,
            text=title,
            bg=self.CARD,
            fg=self.TEXT,
            font=("Segoe UI Semibold", 11),
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))
        return frame

    def _make_pill(self, parent, key: str, value: str, colour: str) -> None:
        wrap = tk.Frame(parent, bg=self.CARD_2, padx=9, pady=5)
        wrap.pack(side="left", padx=(0, 8))
        tk.Label(
            wrap,
            text=key,
            bg=self.CARD_2,
            fg=self.MUTED,
            font=("Segoe UI Semibold", 8),
        ).pack(side="left")
        value_label = tk.Label(
            wrap,
            text=value,
            bg=self.CARD_2,
            fg=colour,
            font=("Segoe UI Semibold", 8),
        )
        value_label.pack(side="left", padx=(6, 0))
        self.pill_values[key] = value_label

    def set_pill(self, key: str, value: str, colour: str | None = None) -> None:
        def update() -> None:
            label = self.pill_values.get(key)
            if label is not None:
                label.configure(text=value, fg=colour or self.TEXT)

        self.root.after(0, update)

    def _object_row(
        self,
        parent,
        *,
        row: int,
        label: str,
        variable: tk.StringVar,
        test_label: str,
    ) -> ttk.Combobox:
        tk.Label(
            parent,
            text=label.upper(),
            bg=self.CARD,
            fg=self.MUTED,
            font=("Segoe UI Semibold", 8),
        ).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=5)

        combo = ttk.Combobox(
            parent,
            textvariable=variable,
            state="readonly",
            style="Modern.TCombobox",
            width=22,
        )
        combo.grid(row=row, column=1, sticky="ew", pady=5)

        ttk.Button(
            parent,
            text="Test",
            style="Modern.TButton",
            command=lambda: self.test_object_click(test_label, variable.get()),
        ).grid(row=row, column=2, padx=(8, 0), pady=5)
        return combo

    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")

        def update() -> None:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", f"{timestamp} | {message}\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")

        self.root.after(0, update)

    def set_status(self, status: str) -> None:
        self.root.after(0, lambda: self.status_var.set(status))

    def set_timer(self, text: str) -> None:
        self.root.after(0, lambda: self.timer_var.set(text))

    def refresh_object_presets(self, log: bool = True) -> None:
        try:
            presets = list(list_object_presets())
        except Exception as exc:
            if log:
                self.log(f"[OBJECTS] presets laden mislukt: {exc}")
            return

        self.crab_combo["values"] = presets
        self.cave_combo["values"] = presets

        if self.crab_object_var.get() not in presets:
            self.crab_object_var.set(
                DEFAULT_CRAB_OBJECT
                if DEFAULT_CRAB_OBJECT in presets
                else (presets[0] if presets else "")
            )

        if self.cave_object_var.get() not in presets:
            self.cave_object_var.set(
                DEFAULT_CAVE_OBJECT
                if DEFAULT_CAVE_OBJECT in presets
                else (presets[0] if presets else "")
            )

        if log:
            self.log(f"[OBJECTS] {len(presets)} presets geladen")
            self.log(
                f"[OBJECTS] crab={self.crab_object_var.get() or '-'} | "
                f"cave={self.cave_object_var.get() or '-'}"
            )

    def _perform_logged_click(self, label: str, object_name: str):
        trace = MouseTrace(label, object_name)
        trace.start()
        result = None
        error = None
        try:
            result = click_object(object_name, bot_id=BOT_ID)
            return result
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            telemetry = trace.stop(result=result, error=error)
            self._handle_mouse_telemetry(telemetry)

    def _variation_label(self) -> str:
        successful = [item for item in self.mouse_history if item.get("success")]
        if len(successful) < 3:
            return "nog te weinig data"

        recent = successful[-10:]
        durations = [float(item["duration_ms"]) for item in recent]
        ratios = [float(item["path_ratio"]) for item in recent if float(item["path_ratio"]) > 0]

        duration_mean = statistics.fmean(durations)
        duration_cv = statistics.pstdev(durations) / duration_mean if duration_mean else 0.0
        ratio_cv = (
            statistics.pstdev(ratios) / statistics.fmean(ratios)
            if len(ratios) >= 2 and statistics.fmean(ratios)
            else 0.0
        )
        combined = (duration_cv + ratio_cv) / 2.0

        if combined < 0.08:
            return "lage variatie"
        if combined < 0.20:
            return "normale variatie"
        return "hoge variatie"

    def _handle_mouse_telemetry(self, telemetry: dict) -> None:
        summary = telemetry["summary"]
        points = telemetry["points"]
        self.mouse_history.append(summary)

        ratio = float(summary["path_ratio"])
        ratio_text = "-" if ratio <= 0 else f"{ratio:.2f}x"
        metrics = (
            f"{summary['action']} · {summary['object']}\n"
            f"{summary['duration_ms']:.0f} ms · {summary['samples']} samples · "
            f"{summary['unique_points']} unique\n"
            f"path {summary['path_distance_px']:.0f}px · straight "
            f"{summary['straight_distance_px']:.0f}px · ratio {ratio_text}\n"
            f"turns {summary['direction_changes']} · {self._variation_label()} · "
            f"engine {summary['engine']}"
        )

        def update() -> None:
            self.mouse_metrics_var.set(metrics)
            self.mouse_file_var.set(f"Saved: {summary['csv']}")
            self._draw_mouse_path(points)

        self.root.after(0, update)

        if summary["success"]:
            self.set_pill("MOUSE", f"{summary['duration_ms']:.0f}ms", self.GREEN)
        else:
            self.set_pill("MOUSE", "FAIL", self.RED)

        self.log(
            f"[MOUSE] {summary['duration_ms']:.0f}ms | "
            f"path={summary['path_distance_px']:.0f}px | "
            f"ratio={ratio_text} | turns={summary['direction_changes']} | "
            f"samples={summary['samples']}"
        )
        self.log(f"[MOUSE] opgeslagen: {summary['csv']}")

    def _draw_mouse_path(self, points: list[tuple[float, int, int]]) -> None:
        canvas = self.path_canvas
        canvas.delete("all")

        width = max(20, canvas.winfo_width())
        height = max(20, canvas.winfo_height())
        pad = 18

        if len(points) < 2:
            canvas.create_text(
                width / 2,
                height / 2,
                text="Nog geen bruikbaar pad",
                fill=self.MUTED,
                font=("Segoe UI", 10),
            )
            return

        xs = [point[1] for point in points]
        ys = [point[2] for point in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        range_x = max(1, max_x - min_x)
        range_y = max(1, max_y - min_y)

        scale = min(
            (width - 2 * pad) / range_x,
            (height - 2 * pad) / range_y,
        )

        offset_x = (width - range_x * scale) / 2
        offset_y = (height - range_y * scale) / 2

        drawn: list[float] = []
        for _, x, y in points:
            drawn.extend(
                [
                    offset_x + (x - min_x) * scale,
                    offset_y + (y - min_y) * scale,
                ]
            )

        if len(drawn) >= 4:
            canvas.create_line(*drawn, fill=self.BLUE, width=2, smooth=True)

        sx, sy = drawn[0], drawn[1]
        ex, ey = drawn[-2], drawn[-1]
        canvas.create_oval(sx - 4, sy - 4, sx + 4, sy + 4, fill=self.GREEN, outline="")
        canvas.create_oval(ex - 5, ey - 5, ex + 5, ey + 5, fill=self.PURPLE, outline="")
        canvas.create_text(12, 12, anchor="nw", text="start", fill=self.GREEN, font=("Segoe UI", 8))
        canvas.create_text(12, 28, anchor="nw", text="end", fill=self.PURPLE, font=("Segoe UI", 8))

    def test_object_click(self, label: str, object_name: str) -> None:
        if not object_name:
            self.log(f"[{label}] geen object geselecteerd")
            return

        def worker() -> None:
            self.set_pill("ACTION", f"TEST {label}", self.AMBER)
            self.log(f"[{label}] test click: {object_name}")
            try:
                result = self._perform_logged_click(label, object_name)
                if result:
                    self.log(f"[{label}] klik OK: {object_name}")
                    self.set_pill("ACTION", "CLICK OK", self.GREEN)
                else:
                    message = getattr(result, "message", "niet klikbaar")
                    self.log(f"[{label}] klik FAIL: {message}")
                    self.set_pill("ACTION", "CLICK FAIL", self.RED)
            except Exception as exc:
                self.log(f"[{label}] ERROR: {exc}")
                self.set_pill("ACTION", "ERROR", self.RED)

        threading.Thread(target=worker, daemon=True).start()

    def start(self) -> None:
        # RUN doubles as resume after PAUSE.
        if self.running:
            if self.paused:
                self.paused = False
                self.run_event.set()
                self.set_status("RUNNING")
                self.set_pill("MODE", "RUNNING", self.GREEN)
                self.set_pill("ACTION", "RESUMED", self.BLUE)
                self.log("[RUN] hervat")
                self.start_button.configure(state="disabled")
                self.pause_button.configure(state="normal")
            return

        crab_object = self.crab_object_var.get().strip()
        cave_object = self.cave_object_var.get().strip()
        if not crab_object or not cave_object:
            self.log("[START] selecteer eerst Crab object en Cave object")
            return

        self.running = True
        self.paused = False
        self.stop_requested = False
        self.run_event.set()
        self.start_button.configure(state="disabled")
        self.pause_button.configure(state="normal")
        self.stop_button.configure(state="normal")
        self.crab_combo.configure(state="disabled")
        self.cave_combo.configure(state="disabled")

        self.set_status("RUNNING")
        self.set_pill("MODE", "RUNNING", self.GREEN)
        self.set_pill("ACTION", "START", self.BLUE)
        self.log(f"[RUN] crab object={crab_object} | cave object={cave_object}")

        threading.Thread(target=self.run_routine, daemon=True).start()

    def pause(self) -> None:
        if not self.running or self.paused:
            return
        self.paused = True
        self.run_event.clear()
        self.set_status("PAUSED")
        self.set_pill("MODE", "PAUSED", self.AMBER)
        self.set_pill("ACTION", "PAUSED", self.AMBER)
        self.log("[PAUSE] routine gepauzeerd")
        self.start_button.configure(state="normal")
        self.pause_button.configure(state="disabled")

    def stop(self) -> None:
        self.stop_requested = True
        self.paused = False
        self.run_event.set()
        self.log("[STOP] aangevraagd")
        self.set_status("STOPPING")
        self.set_pill("MODE", "STOPPING", self.AMBER)
        self.set_pill("ACTION", "STOPPING", self.AMBER)

    def finish(self) -> None:
        self.running = False
        self.paused = False
        self.run_event.set()

        def update() -> None:
            self.start_button.configure(state="normal")
            self.pause_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")
            self.crab_combo.configure(state="readonly")
            self.cave_combo.configure(state="readonly")

        self.root.after(0, update)

    def _wait_if_paused(self) -> bool:
        while self.paused and not self.stop_requested:
            self.run_event.wait(timeout=0.2)
        return not self.stop_requested

    def _sensor_value(self, name: str) -> bool:
        check = self.sensor_checks.get(name)
        if check is None:
            raise KeyError(f"Sensor niet gevonden: {name}")
        if not check.enabled:
            raise ValueError(f"Sensor uitgeschakeld: {name}")
        return evaluate_sensor(check, bot_id=BOT_ID)

    def _is_logged_in_sensor(self) -> bool:
        value = self._sensor_value("is_logged_in")
        self.set_pill("LOGIN", "ONLINE" if value else "OFFLINE", self.GREEN if value else self.RED)
        return value

    def _is_strength_visible(self) -> bool:
        visible = vision.image_exists(
            STRENGTH_IMAGE,
            area=STRENGTH_AREA,
            bot_id=BOT_ID,
        )
        self.set_pill("XP", "ACTIVE" if visible else "CLEAR", self.GREEN if visible else self.MUTED)
        return visible

    def _is_crab_visible(self) -> bool:
        visible = vision.image_exists(
            CRAB_IMAGE,
            area=CRAB_AREA,
            bot_id=BOT_ID,
        )
        self.set_pill("CRAB", "VISIBLE" if visible else "GONE", self.PURPLE if visible else self.MUTED)
        return visible

    def monitor_until_crab_and_xp_gone(self) -> bool:
        self.set_status("MONITOR ACTIVE CRAB")
        self.set_pill("ACTION", "MONITOR", self.BLUE)
        self.log("[MONITOR] wachten tot PAARS en Strength XP allebei weg zijn")

        started = time.monotonic()
        last_state: tuple[bool, bool] | None = None

        while not self.stop_requested:
            if not self._wait_if_paused():
                return False

            crab_visible = self._is_crab_visible()
            strength_visible = self._is_strength_visible()
            state = (crab_visible, strength_visible)

            if state != last_state:
                self.log(
                    f"[MONITOR] paars={'JA' if crab_visible else 'NEE'} | "
                    f"strength={'JA' if strength_visible else 'NEE'}"
                )
                last_state = state

            elapsed = int(time.monotonic() - started)
            minutes, seconds = divmod(elapsed, 60)
            self.set_timer(f"Monitor {minutes:02d}:{seconds:02d}")

            if not crab_visible and not strength_visible:
                self.log("[READY] paars weg + Strength XP weg -> cave")
                self.set_timer("-")
                self.set_pill("ACTION", "CAVE READY", self.AMBER)
                return True

            time.sleep(MONITOR_POLL_SECONDS)

        return False

    def wait_for_crab(self) -> bool:
        deadline = time.monotonic() + CAVE_WAIT_SECONDS
        self.set_pill("ACTION", "WAIT CRAB", self.BLUE)

        while time.monotonic() < deadline:
            if self.stop_requested:
                return False
            if not self._wait_if_paused():
                return False

            remaining = int(deadline - time.monotonic())
            self.set_timer(f"Crab zoeken {remaining}s")

            if self._is_crab_visible():
                self.log("[CRAB] Gemstone_Crab gevonden")
                self.set_timer("-")
                return True

            time.sleep(1)

        self.set_timer("-")
        return False

    def click_cave_and_wait_for_crab(self) -> bool:
        if not self._wait_if_paused():
            return False
        object_name = self.cave_object_var.get().strip()
        self.set_status("CLICK CAVE")
        self.set_pill("ACTION", "CLICK CAVE", self.AMBER)
        self.log(f"[CAVE] object klikken: {object_name}")

        result = self._perform_logged_click("CAVE", object_name)
        if not result:
            message = getattr(result, "message", "niet klikbaar")
            self.log(f"[FAIL] cave click: {message}")
            self.set_pill("ACTION", "CAVE FAIL", self.RED)
            return False

        self.log(f"[CAVE] geklikt: {object_name}")
        self.set_status("WAIT FOR CRAB")

        if not self.wait_for_crab():
            self.log(f"[FAIL] geen crab binnen {CAVE_WAIT_SECONDS}s")
            self.set_pill("ACTION", "CRAB TIMEOUT", self.RED)
            return False

        return True

    def click_crab_and_wait_for_xp(self) -> bool:
        if not self._wait_if_paused():
            return False
        object_name = self.crab_object_var.get().strip()
        self.set_status("CLICK CRAB")
        self.set_pill("ACTION", "CLICK CRAB", self.PURPLE)
        self.log(f"[CLICK] crab object proberen: {object_name}")

        result = self._perform_logged_click("CRAB", object_name)
        if not result:
            message = getattr(result, "message", "niet klikbaar")
            self.log(f"[FAIL] crab click: {message}")
            self.set_pill("ACTION", "CRAB FAIL", self.RED)
            return False

        self.log(f"[CLICK] crab geklikt: {object_name}")
        self.set_status("WAIT FOR XP")
        self.set_pill("ACTION", "WAIT XP", self.BLUE)
        self.log(f"[XP] maximaal {XP_WAIT_SECONDS}s wachten")

        deadline = time.monotonic() + XP_WAIT_SECONDS
        hit_found = False
        while time.monotonic() < deadline:
            if not self._wait_if_paused():
                return False
            if self._is_strength_visible():
                hit_found = True
                break
            remaining = max(0, int(deadline - time.monotonic()))
            self.set_timer(f"XP zoeken {remaining}s")
            time.sleep(0.5)

        self.set_timer("-")
        if not hit_found:
            self.log("[FAIL] geen Strength XP")
            self.set_pill("XP", "NO HIT", self.RED)
            return False

        self.log("[SUCCESS] Strength XP gevonden")
        self.set_pill("XP", "ACTIVE", self.GREEN)
        self.set_pill("ACTION", "SUCCESS", self.GREEN)
        return True

    def run_routine(self) -> None:
        try:
            for routine in range(1, MAX_ROUTINES + 1):
                if self.stop_requested:
                    break
                if not self._wait_if_paused():
                    return

                self.root.after(
                    0,
                    lambda r=routine: self.routine_var.set(f"{r} / {MAX_ROUTINES}"),
                )
                self.log(f"[ROUTINE] start {routine}/{MAX_ROUTINES}")

                self.set_status("CHECK LOGIN")
                self.set_pill("ACTION", "CHECK LOGIN", self.BLUE)
                self.log("[LOGIN] controleren")

                logged_in = self._is_logged_in_sensor()
                self.log(f"[LOGIN] sensor is_logged_in={'TRUE' if logged_in else 'FALSE'}")

                if not logged_in:
                    self.log("[STOP] is_logged_in sensor is FALSE")
                    self.set_status("NOT LOGGED IN")
                    self.set_pill("ACTION", "STOPPED", self.RED)
                    return

                self.log("[LOGIN] sensor TRUE")

                strength_visible = self._is_strength_visible()
                crab_visible = self._is_crab_visible()
                self.log(
                    f"[STATE] paars={'JA' if crab_visible else 'NEE'} | "
                    f"strength={'JA' if strength_visible else 'NEE'}"
                )

                if strength_visible:
                    if not self.monitor_until_crab_and_xp_gone():
                        return
                    if not self.click_cave_and_wait_for_crab():
                        continue

                elif crab_visible:
                    self.log(
                        "[CRAB] paars zichtbaar zonder Strength XP -> "
                        "geselecteerd crab object klikken"
                    )

                else:
                    self.log(
                        "[READY] geen paars + geen Strength XP -> "
                        "geselecteerd cave object"
                    )
                    if not self.click_cave_and_wait_for_crab():
                        continue

                if not self.click_crab_and_wait_for_xp():
                    continue

                if not self.monitor_until_crab_and_xp_gone():
                    return

            if not self.stop_requested:
                self.log("[STOP] maximaal aantal routines bereikt")
                self.set_status("MAX ROUTINES")
                self.set_pill("MODE", "DONE", self.GREEN)
                self.set_pill("ACTION", "DONE", self.GREEN)

        except Exception as exc:
            self.log(f"[ERROR] {exc}")
            self.set_status("ERROR")
            self.set_pill("ACTION", "ERROR", self.RED)

        finally:
            self.set_timer("-")
            self.finish()

    def clear_log(self) -> None:
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    CrabTestUI().run()
