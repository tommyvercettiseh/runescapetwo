from __future__ import annotations

from tkinter import ttk

from . import unified_plus


class ReplayResetPage(unified_plus.ToleranceColourPage):
    """Add a simple Reset Replay action without clearing the loaded recording."""

    def _add_recording_controls(self) -> None:
        super()._add_recording_controls()
        try:
            toolbar = self.source.master
        except AttributeError:
            return

        controls = ttk.Frame(toolbar)
        controls.grid(row=0, column=4, sticky="e", padx=(0, 8))
        ttk.Button(
            controls,
            text="Reset Replay",
            command=self._reset_replay,
        ).pack(side="left")

    def _reset_replay(self) -> None:
        if not getattr(self, "_replay_frames", None):
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
    unified_plus.ToleranceColourPage = ReplayResetPage


__all__ = ["ReplayResetPage", "install_replay_reset"]
