from __future__ import annotations

import ctypes
import math
import sys
import time
import tkinter as tk
from collections.abc import Callable


TRANSPARENT_KEY = "#010203"
TRACE_COLOUR = (142, 198, 63)
TRACE_LIFETIME_S = 1.0
FINISH_DELAY_S = 0.9


def _hex_colour(red: int, green: int, blue: int) -> str:
    return f"#{red:02x}{green:02x}{blue:02x}"


def fading_trace_colour(strength: float) -> str:
    """Return a darker colour as a trace segment approaches expiry."""
    strength = min(1.0, max(0.0, float(strength)))
    floor = (18, 24, 12)
    values = tuple(
        round(start + (end - start) * strength)
        for start, end in zip(floor, TRACE_COLOUR)
    )
    return _hex_colour(*values)


def _virtual_screen(master: tk.Misc) -> tuple[int, int, int, int]:
    if sys.platform == "win32":
        user32 = ctypes.windll.user32
        return (
            int(user32.GetSystemMetrics(76)),
            int(user32.GetSystemMetrics(77)),
            int(user32.GetSystemMetrics(78)),
            int(user32.GetSystemMetrics(79)),
        )
    return 0, 0, int(master.winfo_screenwidth()), int(master.winfo_screenheight())


class MouseTraceOverlay:
    """Click-through tester overlay for a fading cursor trail and target ring."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        cursor_position: Callable[[], tuple[int, int]],
        target_bounds: tuple[int, int, int, int],
    ) -> None:
        if sys.platform != "win32":
            raise RuntimeError("Mouse trace overlay is currently available on Windows only")
        self.master = master
        self.cursor_position = cursor_position
        self.target_bounds = target_bounds
        self.origin_x, self.origin_y, width, height = _virtual_screen(master)
        self.points: list[tuple[int, int, float]] = []
        self.finishing_at: float | None = None
        self._job: str | None = None
        self._closed = False

        self.window = tk.Toplevel(master)
        self.window.withdraw()
        self.window.overrideredirect(True)
        self.window.configure(bg=TRANSPARENT_KEY)
        self.window.geometry(
            f"{width}x{height}{self.origin_x:+d}{self.origin_y:+d}"
        )
        self.window.attributes("-topmost", True)
        self.window.attributes("-transparentcolor", TRANSPARENT_KEY)
        self.canvas = tk.Canvas(
            self.window,
            bg=TRANSPARENT_KEY,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.window.update_idletasks()
        self._make_click_through()
        self.window.deiconify()
        self.window.lift()
        self._sample()
        self._job = self.window.after(16, self._tick)

    def _make_click_through(self) -> None:
        user32 = ctypes.windll.user32
        handle = int(self.window.winfo_id())
        parent_handle = int(user32.GetParent(handle))
        if parent_handle:
            handle = parent_handle
        extended_style = int(user32.GetWindowLongW(handle, -20))
        user32.SetWindowLongW(
            handle,
            -20,
            extended_style | 0x00080000 | 0x00000020 | 0x00000080 | 0x08000000,
        )

    def _sample(self) -> None:
        x, y = self.cursor_position()
        now = time.monotonic()
        if not self.points or self.points[-1][:2] != (x, y):
            self.points.append((x, y, now))

    def _tick(self) -> None:
        if self._closed:
            return
        now = time.monotonic()
        try:
            self._sample()
        except Exception:
            self.finish()
        self.points = [
            point for point in self.points if now - point[2] <= TRACE_LIFETIME_S
        ]
        self._draw(now)
        if self.finishing_at is not None and now - self.finishing_at >= FINISH_DELAY_S:
            self.close()
            return
        self._job = self.window.after(16, self._tick)

    def _draw(self, now: float) -> None:
        self.canvas.delete("all")
        left, top, right, bottom = self.target_bounds
        self.canvas.create_rectangle(
            left - self.origin_x,
            top - self.origin_y,
            right - self.origin_x,
            bottom - self.origin_y,
            outline="#d1a64b",
            width=2,
            dash=(5, 4),
        )

        for first, second in zip(self.points, self.points[1:]):
            age = now - second[2]
            strength = max(0.0, 1.0 - age / TRACE_LIFETIME_S)
            self.canvas.create_line(
                first[0] - self.origin_x,
                first[1] - self.origin_y,
                second[0] - self.origin_x,
                second[1] - self.origin_y,
                fill=fading_trace_colour(strength),
                width=max(1, round(1 + strength * 4)),
                capstyle=tk.ROUND,
                smooth=True,
            )

        if not self.points:
            return
        cursor_x = self.points[-1][0] - self.origin_x
        cursor_y = self.points[-1][1] - self.origin_y
        rotation = (now * 220.0) % 360.0
        radius = 17
        for offset, colour in ((0, "#8ec63f"), (120, "#d1a64b"), (240, "#e9dfc8")):
            self.canvas.create_arc(
                cursor_x - radius,
                cursor_y - radius,
                cursor_x + radius,
                cursor_y + radius,
                start=rotation + offset,
                extent=58,
                style=tk.ARC,
                outline=colour,
                width=3,
            )
        pulse = 3.0 * (0.5 + 0.5 * math.sin(now * 8.0))
        outer = radius + 5 + pulse
        self.canvas.create_oval(
            cursor_x - outer,
            cursor_y - outer,
            cursor_x + outer,
            cursor_y + outer,
            outline=fading_trace_colour(0.45),
            width=1,
        )

    def finish(self) -> None:
        if self.finishing_at is None:
            self.finishing_at = time.monotonic()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._job is not None:
            try:
                self.window.after_cancel(self._job)
            except tk.TclError:
                pass
        try:
            self.window.destroy()
        except tk.TclError:
            pass


__all__ = ["MouseTraceOverlay", "fading_trace_colour"]
