from __future__ import annotations

import tkinter as tk

from . import preset_ui


_original_start_hotkeys = preset_ui.VisionTester._start_hotkeys


def _start_hotkeys_reliable(self) -> None:
    # Keep the global pynput listener for when the tester is not focused.
    _original_start_hotkeys(self)

    # Also bind F2 at Tk level. This covers focused widgets/overlays where the
    # OS-level listener may be swallowed or delayed. The existing debounce in
    # _queue_capture_hotkey prevents duplicate captures if both paths fire.
    self.bind_all(
        "<F2>",
        lambda _event: (self._queue_capture_hotkey(), "break")[1],
        add="+",
    )


def _windows_key_filter_no_suppress(self, message, data):
    # Queue F2 globally, but do not suppress the key. Suppression caused
    # inconsistent behaviour with Tk windows and screenshot overlays on Windows.
    if int(data.vkCode) == 0x71 and int(message) in (0x0100, 0x0104):
        self._queue_capture_hotkey()
    return True


def install_hotkey_fix() -> None:
    preset_ui.VisionTester._start_hotkeys = _start_hotkeys_reliable
    preset_ui.VisionTester._windows_key_filter = _windows_key_filter_no_suppress


__all__ = ["install_hotkey_fix"]
