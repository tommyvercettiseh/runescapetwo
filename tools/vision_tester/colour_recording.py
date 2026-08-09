from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from queue import Full, Queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk

import cv2
import numpy as np

from .colour_delete_undo import DeleteUndoColourPage


ROOT = Path(__file__).resolve().parents[2]
RECORDINGS_DIR = ROOT / "recordings" / "colour"
REPLAY_SPEEDS = ("0.5x", "1x", "2x", "4x", "8x")
NOMINAL_FPS = 10


class RecordedColourPage(DeleteUndoColourPage):
    """Lossless raw-area recording and replay layered on the operator colour page."""

    def __init__(self, parent) -> None:
        self._recording = False
        self._record_dir: Path | None = None
        self._record_queue: Queue[tuple[int, np.ndarray] | None] = Queue(maxsize=180)
        self._record_thread: threading.Thread | None = None
        self._record_frame_index = 0

        self._replay_frames: list[Path] = []
        self._replay_index = 0
        self._replay_job: str | None = None
        self._replay_playing = False
        self._replay_active = False

        self.record_text = tk.StringVar(master=parent, value="Record Raw")
        self.play_text = tk.StringVar(master=parent, value="Play Video")
        self.replay_speed = tk.StringVar(master=parent, value="1x")
        self.replay_info = tk.StringVar(master=parent, value="")
        super().__init__(parent)

    def _build(self) -> None:
        super()._build()
        self._add_recording_controls()

    def _add_recording_controls(self) -> None:
        toolbar = self.source.master
        controls = ttk.Frame(toolbar)
        controls.grid(row=0, column=3, sticky="e", padx=(12, 8))

        ttk.Button(
            controls,
            textvariable=self.record_text,
            command=self._toggle_recording,
        ).pack(side="left")
        ttk.Button(
            controls,
            textvariable=self.play_text,
            command=self._play_video,
        ).pack(side="left", padx=(6, 0))
        ttk.Combobox(
            controls,
            values=REPLAY_SPEEDS,
            textvariable=self.replay_speed,
            state="readonly",
            width=5,
        ).pack(side="left", padx=(6, 0))
        ttk.Label(controls, textvariable=self.replay_info).pack(
            side="left",
            padx=(8, 0),
        )

    def _toggle_recording(self) -> None:
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        if self._replay_active:
            self._stop_replay(clear=True)

        area = self.source.area.get().strip()
        if not area:
            self.status.set("Kies eerst een area om raw op te nemen.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_area = "".join(
            ch if ch.isalnum() or ch in "-_" else "_"
            for ch in area
        )
        record_dir = RECORDINGS_DIR / f"{timestamp}_{safe_area}"
        (record_dir / "frames").mkdir(parents=True, exist_ok=True)

        self._record_dir = record_dir
        self._record_frame_index = 0
        self._recording = True
        self.record_text.set("Stop Raw")
        self.live.set(True)

        metadata = {
            "format": 2,
            "type": "raw_colour_area",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "area": area,
            "bot_id": self.source.bot(),
            "nominal_fps": NOMINAL_FPS,
            "lossless": True,
            "frame_count": 0,
        }
        (record_dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        self._record_queue = Queue(maxsize=180)
        self._record_thread = threading.Thread(
            target=self._record_writer,
            args=(record_dir, self._record_queue),
            daemon=True,
        )
        self._record_thread.start()
        self.status.set(f"RAW recording: {area} · colours zijn niet nodig.")

    @staticmethod
    def _record_writer(record_dir: Path, queue: Queue) -> None:
        while True:
            item = queue.get()
            try:
                if item is None:
                    return
                index, rgb = item
                target = record_dir / "frames" / f"{index:06d}.png"
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                cv2.imwrite(
                    str(target),
                    bgr,
                    [cv2.IMWRITE_PNG_COMPRESSION, 3],
                )
            finally:
                queue.task_done()

    def _queue_record_frame(self) -> None:
        if not self._recording or self.capture is None:
            return
        index = self._record_frame_index
        try:
            self._record_queue.put_nowait((index, self.capture.copy()))
        except Full:
            self.status.set("RAW recorder loopt achter; één frame overgeslagen.")
            return
        self._record_frame_index += 1

    def _stop_recording(self) -> None:
        if not self._recording:
            return

        self._recording = False
        self.record_text.set("Record Raw")
        record_dir = self._record_dir
        frame_count = self._record_frame_index

        try:
            self._record_queue.put_nowait(None)
        except Full:
            threading.Thread(
                target=self._record_queue.put,
                args=(None,),
                daemon=True,
            ).start()

        if record_dir is None:
            return

        metadata_path = record_dir / "metadata.json"
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            metadata = {}
        metadata["frame_count"] = frame_count
        metadata["stopped_at"] = datetime.now().isoformat(timespec="seconds")
        try:
            metadata_path.write_text(
                json.dumps(metadata, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass

        self._load_recording_folder(record_dir, autoplay=False)
        self.status.set(
            f"RAW bewaard: {record_dir.name} · {frame_count} frames."
        )

    def _play_video(self) -> None:
        if self._replay_playing:
            self._pause_replay()
            return
        if not self._replay_frames and not self._choose_recording():
            return

        self._replay_playing = True
        self.play_text.set("Pause")
        self.live.set(False)
        self._replay_active = True
        self._schedule_next_frame(immediate=True)

    def _choose_recording(self) -> bool:
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        selected = filedialog.askdirectory(
            title="Kies RAW colour recording",
            initialdir=str(RECORDINGS_DIR),
            parent=self.winfo_toplevel(),
        )
        if not selected:
            return False
        return self._load_recording_folder(Path(selected), autoplay=False)

    def _load_recording_folder(self, folder: Path, *, autoplay: bool) -> bool:
        frames = sorted((folder / "frames").glob("*.png"))
        if not frames:
            self.status.set("Deze RAW recording bevat geen frames.")
            return False

        self._stop_replay(clear=True)
        self._replay_frames = frames
        self._replay_index = 0
        self._replay_active = True
        self.live.set(False)
        self._show_replay_frame(0)
        self._update_replay_info()
        self.status.set(
            "RAW video geladen. Pauzeer op een frame en gebruik de pipet."
        )
        if autoplay:
            self._play_video()
        return True

    def _pause_replay(self) -> None:
        self._replay_playing = False
        self.play_text.set("Play Video")
        if self._replay_job is not None:
            try:
                self.after_cancel(self._replay_job)
            except tk.TclError:
                pass
            self._replay_job = None

    def _stop_replay(self, *, clear: bool) -> None:
        self._pause_replay()
        self._replay_active = False
        if clear:
            self._replay_frames = []
            self._replay_index = 0
            self.replay_info.set("")

    def _speed_multiplier(self) -> float:
        value = self.replay_speed.get().strip().lower().rstrip("x")
        try:
            return max(0.5, min(8.0, float(value)))
        except ValueError:
            return 1.0

    def _schedule_next_frame(self, *, immediate: bool = False) -> None:
        if not self._replay_playing or not self._replay_frames:
            return
        delay = (
            1
            if immediate
            else max(
                1,
                round((1000 / NOMINAL_FPS) / self._speed_multiplier()),
            )
        )
        self._replay_job = self.after(delay, self._advance_replay)

    def _advance_replay(self) -> None:
        self._replay_job = None
        if not self._replay_playing or not self._replay_frames:
            return

        self._replay_index = (self._replay_index + 1) % len(self._replay_frames)
        self._show_replay_frame(self._replay_index)
        self._update_replay_info()
        self._schedule_next_frame()

    def _show_replay_frame(self, index: int) -> None:
        if not self._replay_frames:
            return
        bgr = cv2.imread(str(self._replay_frames[index]), cv2.IMREAD_COLOR)
        if bgr is None:
            return

        self.capture = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        height, width = self.capture.shape[:2]
        self.capture_region = (0, 0, width, height)
        self._render()

    def _update_replay_info(self) -> None:
        if not self._replay_frames:
            self.replay_info.set("")
            return
        self.replay_info.set(
            f"{self._replay_index + 1}/{len(self._replay_frames)}"
        )

    def _capture(self) -> None:
        if self._replay_active:
            return
        super()._capture()
        self._queue_record_frame()

    def deactivate(self) -> None:
        if self._recording:
            self._stop_recording()
        if self._replay_playing:
            self._pause_replay()
        super().deactivate()


def install_colour_recording() -> None:
    """Compatibility no-op; use RecordedColourPage explicitly."""


__all__ = ["RecordedColourPage", "install_colour_recording"]
