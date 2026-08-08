from __future__ import annotations

from tkinter import ttk

from .colour_recording import RecordedColourPage


class ReplayResetPage(RecordedColourPage):
    """Recorded colour page with a replay reset action."""

    def _add_recording_controls(self) -> None:
        super()._add_recording_controls()
        toolbar = self.source.master
        controls = ttk.Frame(toolbar)
        controls.grid(row=0, column=4, sticky="e", padx=(0, 8))
        ttk.Button(
            controls,
            text="Reset Replay",
            command=self._reset_replay,
        ).pack(side="left")

    def _reset_replay(self) -> None:
        if not self._replay_frames:
            self.status.set("Geen replay geladen om te resetten.")
            return

        self._pause_replay()
        self._replay_active = True
        self._replay_index = 0
        self.live.set(False)
        self._show_replay_frame(0)
        self._update_replay_info()
        self.status.set("Replay gereset naar frame 1 en gepauzeerd.")


def install_replay_reset() -> None:
    """Compatibility no-op; use ReplayResetPage explicitly."""


__all__ = ["ReplayResetPage", "install_replay_reset"]
