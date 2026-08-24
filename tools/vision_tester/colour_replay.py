from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import json
from pathlib import Path
from queue import Full, Queue
import threading
import tkinter as tk
from tkinter import filedialog

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
RECORDINGS_DIR = ROOT / "recordings" / "colour"
REPLAY_SPEEDS = ("0.5x", "1x", "2x", "4x", "8x")
NOMINAL_FPS = 10

CaptureGetter = Callable[[], np.ndarray | None]
CaptureSetter = Callable[[np.ndarray, tuple[int, int, int, int]], None]
StringGetter = Callable[[], str]
IntGetter = Callable[[], int]
BoolSetter = Callable[[bool], None]
StatusSetter = Callable[[str], None]
RenderCallback = Callable[[], None]


class ColourReplayController:
    """Own raw recording and replay state without becoming a UI page."""

    def __init__(
        self,
        owner: tk.Misc,
        *,
        capture_getter: CaptureGetter,
        capture_setter: CaptureSetter,
        area_getter: StringGetter,
        bot_id_getter: IntGetter,
        live_setter: BoolSetter,
        status_setter: StatusSetter,
        render: RenderCallback,
    ) -> None:
        self.owner = owner
        self._capture_getter = capture_getter
        self._capture_setter = capture_setter
        self._area_getter = area_getter
        self._bot_id_getter = bot_id_getter
        self._live_setter = live_setter
        self._status_setter = status_setter
        self._render = render

        self.record_text = tk.StringVar(master=owner, value="Record Raw")
        self.play_text = tk.StringVar(master=owner, value="Play Video")
        self.replay_speed = tk.StringVar(master=owner, value="1x")
        self.replay_info = tk.StringVar(master=owner, value="")

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

    @property
    def replay_active(self) -> bool:
        return self._replay_active

    def toggle_recording(self) -> None:
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def play_or_pause(self) -> None:
        if self._replay_playing:
            self._pause_replay()
            return
        if not self._replay_frames and not self._choose_recording():
            return

        self._replay_playing = True
        self.play_text.set("Pause")
        self._live_setter(False)
        self._replay_active = True
        self._schedule_next_frame(immediate=True)

    def reset_replay(self) -> None:
        if not self._replay_frames:
            self._status_setter("Geen replay geladen om te resetten.")
            return

        self._pause_replay()
        self._replay_active = True
        self._replay_index = 0
        self._live_setter(False)
        self._show_replay_frame(0)
        self._update_replay_info()
        self._status_setter("Replay gereset naar frame 1 en gepauzeerd.")

    def capture_frame(self) -> None:
        if not self._recording:
            return

        capture = self._capture_getter()
        if capture is None:
            return

        index = self._record_frame_index
        try:
            self._record_queue.put_nowait((index, capture.copy()))
        except Full:
            self._status_setter(
                "RAW recorder loopt achter; één frame overgeslagen."
            )
            return
        self._record_frame_index += 1

    def deactivate(self) -> None:
        if self._recording:
            self._stop_recording()
        if self._replay_playing:
            self._pause_replay()

    def _start_recording(self) -> None:
        if self._replay_active:
            self._stop_replay(clear=True)

        area = self._area_getter().strip()
        if not area:
            self._status_setter("Kies eerst een area om raw op te nemen.")
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
        self._live_setter(True)

        metadata = {
            "format": 2,
            "type": "raw_colour_area",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "area": area,
            "bot_id": self._bot_id_getter(),
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
        self._status_setter(
            f"RAW recording: {area} · colours zijn niet nodig."
        )

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
        self._status_setter(
            f"RAW bewaard: {record_dir.name} · {frame_count} frames."
        )

    def _choose_recording(self) -> bool:
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
        selected = filedialog.askdirectory(
            title="Kies RAW colour recording",
            initialdir=str(RECORDINGS_DIR),
            parent=self.owner.winfo_toplevel(),
        )
        if not selected:
            return False
        return self._load_recording_folder(Path(selected), autoplay=False)

    def _load_recording_folder(self, folder: Path, *, autoplay: bool) -> bool:
        frames = sorted((folder / "frames").glob("*.png"))
        if not frames:
            self._status_setter("Deze RAW recording bevat geen frames.")
            return False

        self._stop_replay(clear=True)
        self._replay_frames = frames
        self._replay_index = 0
        self._replay_active = True
        self._live_setter(False)
        self._show_replay_frame(0)
        self._update_replay_info()
        self._status_setter(
            "RAW video geladen. Pauzeer op een frame en gebruik de pipet."
        )
        if autoplay:
            self.play_or_pause()
        return True

    def _pause_replay(self) -> None:
        self._replay_playing = False
        self.play_text.set("Play Video")
        if self._replay_job is not None:
            try:
                self.owner.after_cancel(self._replay_job)
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
        self._replay_job = self.owner.after(delay, self._advance_replay)

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

        capture = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        height, width = capture.shape[:2]
        self._capture_setter(capture, (0, 0, width, height))
        self._render()

    def _update_replay_info(self) -> None:
        if not self._replay_frames:
            self.replay_info.set("")
            return
        self.replay_info.set(
            f"{self._replay_index + 1}/{len(self._replay_frames)}"
        )


__all__ = [
    "ColourReplayController",
    "REPLAY_SPEEDS",
]
