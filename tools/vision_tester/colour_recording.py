from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from queue import Empty, Queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk

import cv2
import numpy as np

from core.vision.colour_detection import build_mask_from_ranges, count_mask_pixels, hsv_ranges_around

from . import unified_plus


ROOT = Path(__file__).resolve().parents[2]
RECORDINGS_DIR = ROOT / "recordings" / "colour"
REPLAY_SPEEDS = ("0.25x", "0.5x", "1x", "2x", "4x", "8x")
STATE_MIN_PIXELS = 3
STATE_AMBIGUITY_RATIO = 0.85


class RecordedColourPage(unified_plus.ToleranceColourPage):
    """Add lossless area recording/replay and explicit colour-state analysis."""

    def __init__(self, parent):
        self._recording = False
        self._record_dir: Path | None = None
        self._record_queue: Queue[tuple[int, np.ndarray] | None] = Queue(maxsize=120)
        self._record_thread: threading.Thread | None = None
        self._record_frame_index = 0
        self._recorded_frames = 0

        self._replay_frames: list[Path] = []
        self._replay_index = 0
        self._replay_job: str | None = None
        self._replay_playing = False
        self._replay_active = False

        self.replay_speed = tk.StringVar(value="1x")
        self.record_text = tk.StringVar(value="Record")
        self.replay_text = tk.StringVar(value="Play")
        self.state_text = tk.StringVar(value="STATE: UNKNOWN")
        self.state_detail_text = tk.StringVar(value="Selecteer colours om iedere frame expliciet te classificeren.")
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()
        self._add_recording_controls()

    def _add_recording_controls(self) -> None:
        try:
            toolbar = self.source.master
        except AttributeError:
            return

        controls = ttk.Frame(toolbar)
        controls.grid(row=0, column=3, sticky="e", padx=(12, 8))

        ttk.Button(controls, textvariable=self.record_text, command=self._toggle_recording).pack(side="left")
        ttk.Button(controls, text="Load replay", command=self._load_replay).pack(side="left", padx=(6, 0))
        ttk.Button(controls, textvariable=self.replay_text, command=self._toggle_replay).pack(side="left", padx=(6, 0))
        ttk.Combobox(
            controls,
            values=REPLAY_SPEEDS,
            textvariable=self.replay_speed,
            state="readonly",
            width=6,
        ).pack(side="left", padx=(6, 0))

        state = ttk.Frame(toolbar)
        state.grid(row=1, column=0, columnspan=5, sticky="ew", padx=8, pady=(4, 0))
        ttk.Label(state, textvariable=self.state_text, font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Label(state, textvariable=self.state_detail_text).pack(side="left", padx=(12, 0))

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def _toggle_recording(self) -> None:
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        if self._replay_active:
            self.status.set("Stop eerst de replay voordat je een nieuwe opname maakt.")
            return
        area = self.source.area.get().strip()
        if not area:
            self.status.set("Kies eerst een area om op te nemen.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_area = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in area)
        self._record_dir = RECORDINGS_DIR / f"{timestamp}_{safe_area}"
        (self._record_dir / "frames").mkdir(parents=True, exist_ok=True)
        self._record_frame_index = 0
        self._recorded_frames = 0
        self._recording = True
        self.record_text.set("Stop recording")
        self.live.set(True)

        metadata = {
            "format": 1,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "area": area,
            "bot_id": self.source.bot(),
            "nominal_fps": 10,
            "colour_presets": sorted(getattr(self, "_active_colour_names", []), key=str.casefold),
            "lossless": True,
            "frame_count": 0,
        }
        (self._record_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        self._record_thread = threading.Thread(target=self._record_writer, daemon=True)
        self._record_thread.start()
        self.status.set(f"Recording gestart: {self._record_dir.name} · lossless PNG frames.")

    def _record_writer(self) -> None:
        while True:
            item = self._record_queue.get()
            if item is None:
                return
            index, rgb = item
            record_dir = self._record_dir
            if record_dir is None:
                continue
            target = record_dir / "frames" / f"{index:06d}.png"
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(target), bgr, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            self._recorded_frames = max(self._recorded_frames, index + 1)

    def _queue_record_frame(self) -> None:
        if not self._recording or self.capture is None:
            return
        index = self._record_frame_index
        self._record_frame_index += 1
        try:
            self._record_queue.put_nowait((index, self.capture.copy()))
        except Exception:
            # Never stall live capture because disk writing is briefly behind.
            self.status.set("Recording writer loopt achter; frame overgeslagen.")

    def _stop_recording(self) -> None:
        if not self._recording:
            return
        self._recording = False
        self.record_text.set("Record")
        try:
            self._record_queue.put_nowait(None)
        except Exception:
            pass

        record_dir = self._record_dir
        if record_dir is not None:
            metadata_path = record_dir / "metadata.json"
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                metadata = {}
            metadata["frame_count"] = self._record_frame_index
            metadata["stopped_at"] = datetime.now().isoformat(timespec="seconds")
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            self.status.set(
                f"Recording bewaard: {record_dir.name} · {self._record_frame_index} frames."
            )

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------
    def _load_replay(self) -> None:
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        selected = filedialog.askdirectory(
            title="Kies colour recording",
            initialdir=str(RECORDINGS_DIR),
            parent=self.winfo_toplevel(),
        )
        if not selected:
            return
        folder = Path(selected)
        frames = sorted((folder / "frames").glob("*.png"))
        if not frames:
            self.status.set("Deze recording bevat geen PNG frames.")
            return

        self._stop_replay()
        self._replay_frames = frames
        self._replay_index = 0
        self._replay_active = True
        self.live.set(False)
        self._show_replay_frame(0)
        self.status.set(f"Replay geladen: {folder.name} · {len(frames)} frames.")

    def _toggle_replay(self) -> None:
        if not self._replay_frames:
            self._load_replay()
            if not self._replay_frames:
                return
        if self._replay_playing:
            self._pause_replay()
        else:
            self._replay_playing = True
            self.replay_text.set("Pause")
            self._schedule_next_replay_frame(immediate=True)

    def _pause_replay(self) -> None:
        self._replay_playing = False
        self.replay_text.set("Play")
        if self._replay_job is not None:
            try:
                self.after_cancel(self._replay_job)
            except tk.TclError:
                pass
            self._replay_job = None

    def _stop_replay(self) -> None:
        self._pause_replay()
        self._replay_active = False
        self._replay_frames = []
        self._replay_index = 0

    def _speed_multiplier(self) -> float:
        value = self.replay_speed.get().strip().lower().rstrip("x")
        try:
            return max(0.25, min(8.0, float(value)))
        except ValueError:
            return 1.0

    def _schedule_next_replay_frame(self, *, immediate: bool = False) -> None:
        if not self._replay_playing or not self._replay_frames:
            return
        delay = 1 if immediate else max(1, round(100 / self._speed_multiplier()))
        self._replay_job = self.after(delay, self._advance_replay)

    def _advance_replay(self) -> None:
        self._replay_job = None
        if not self._replay_playing or not self._replay_frames:
            return
        self._replay_index += 1
        if self._replay_index >= len(self._replay_frames):
            self._replay_index = 0
        self._show_replay_frame(self._replay_index)
        self._schedule_next_replay_frame()

    def _show_replay_frame(self, index: int) -> None:
        path = self._replay_frames[index]
        bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if bgr is None:
            return
        self.capture = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        height, width = self.capture.shape[:2]
        self.capture_region = (0, 0, width, height)
        self._render()
        self._analyse_colour_state()

    # ------------------------------------------------------------------
    # Explicit state analysis
    # ------------------------------------------------------------------
    def _ranges_for_name(self, name: str):
        try:
            bases = self._bases_for_preset(name)
        except Exception:
            return ()
        hue, saturation, brightness = unified_plus.tolerance_values(self.colour_tolerance.get())
        combined = []
        for hsv in bases:
            combined.extend(
                hsv_ranges_around(
                    hsv,
                    hue_tolerance=hue,
                    saturation_tolerance=saturation,
                    value_tolerance=brightness,
                )
            )
        return tuple(combined)

    def _analyse_colour_state(self) -> None:
        if self.capture is None:
            self.state_text.set("STATE: UNKNOWN")
            self.state_detail_text.set("Geen frame beschikbaar.")
            return

        names = sorted(getattr(self, "_active_colour_names", []), key=str.casefold)
        if not names:
            self.state_text.set("STATE: UNKNOWN")
            self.state_detail_text.set("Geen colour-states geselecteerd.")
            return

        scores: list[tuple[str, int]] = []
        for name in names:
            ranges = self._ranges_for_name(name)
            if not ranges:
                scores.append((name, 0))
                continue
            mask = build_mask_from_ranges(self.capture, ranges)
            scores.append((name, count_mask_pixels(mask)))
        scores.sort(key=lambda item: item[1], reverse=True)

        winner, winner_pixels = scores[0]
        runner_pixels = scores[1][1] if len(scores) > 1 else 0
        ambiguous = winner_pixels > 0 and runner_pixels >= winner_pixels * STATE_AMBIGUITY_RATIO

        if winner_pixels < STATE_MIN_PIXELS:
            state = "UNKNOWN"
            reason = f"geen colour haalt {STATE_MIN_PIXELS} px"
        elif ambiguous:
            state = "UNKNOWN"
            reason = "te weinig verschil tussen beste twee colours"
        else:
            state = winner.upper()
            reason = f"winnaar {winner_pixels} px"

        self.state_text.set(f"STATE: {state}")
        details = " · ".join(f"{name} {pixels}px" for name, pixels in scores[:5])
        self.state_detail_text.set(f"{reason} · {details}")

    def _capture(self) -> None:
        if self._replay_active:
            return
        super()._capture()
        if self.capture is not None:
            self._queue_record_frame()
            self._analyse_colour_state()

    def _render(self, started=None) -> None:
        super()._render(started)
        if hasattr(self, "state_text") and self.capture is not None:
            self._analyse_colour_state()

    def deactivate(self) -> None:
        self._pause_replay()
        super().deactivate()


def install_colour_recording() -> None:
    unified_plus.ToleranceColourPage = RecordedColourPage


__all__ = ["RecordedColourPage", "install_colour_recording"]
