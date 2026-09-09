from __future__ import annotations

import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import ttk

# Make repository root importable when this file is started directly from scripts/.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from actions.click_object import click_object
from core import vision
from definitions.login.is_logged_in import is_logged_in


BOT_ID = 1

STRENGTH_IMAGE = "Chat_Strength"
STRENGTH_AREA = "Chat_Area"

CRAB_IMAGE = "Gemstone_Crab"
CRAB_AREA = "Bot_Area"

CRAB_OBJECT = "gemrockcrab"
CAVE_OBJECT = "cave"

MAX_ROUTINES = 5
CAVE_WAIT_SECONDS = 20
XP_WAIT_SECONDS = 10
MONITOR_POLL_SECONDS = 1.0


class CrabTestUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Gemstone Crab Test")
        self.root.geometry("620x520")
        self.root.resizable(False, False)

        self.running = False
        self.stop_requested = False

        self.status_var = tk.StringVar(value="IDLE")
        self.routine_var = tk.StringVar(value=f"0 / {MAX_ROUTINES}")
        self.timer_var = tk.StringVar(value="-")

        self._build_ui()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Gemstone Crab Routine", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(main, text="Live status", font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 15))

        info = ttk.Frame(main)
        info.pack(fill="x")
        self._info_row(info, "Status", self.status_var, 0)
        self._info_row(info, "Routine", self.routine_var, 1)
        self._info_row(info, "Timer", self.timer_var, 2)

        ttk.Separator(main).pack(fill="x", pady=14)

        self.log_box = tk.Text(main, height=17, state="disabled", font=("Consolas", 10))
        self.log_box.pack(fill="both", expand=True)

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=(14, 0))

        self.start_button = ttk.Button(buttons, text="START", command=self.start)
        self.start_button.pack(side="left")

        self.stop_button = ttk.Button(buttons, text="STOP", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=8)

        ttk.Button(buttons, text="CLEAR LOG", command=self.clear_log).pack(side="right")

    def _info_row(self, parent, label, variable, row) -> None:
        ttk.Label(parent, text=label, width=12, font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="w", pady=4
        )
        ttk.Label(parent, textvariable=variable, font=("Segoe UI", 10)).grid(
            row=row, column=1, sticky="w", pady=4
        )

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

    def start(self) -> None:
        if self.running:
            return

        self.running = True
        self.stop_requested = False
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

        thread = threading.Thread(target=self.run_routine, daemon=True)
        thread.start()

    def stop(self) -> None:
        self.stop_requested = True
        self.log("STOP aangevraagd")
        self.set_status("STOPPING")

    def finish(self) -> None:
        self.running = False

        def update() -> None:
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")

        self.root.after(0, update)

    def _is_strength_visible(self) -> bool:
        return vision.image_exists(STRENGTH_IMAGE, area=STRENGTH_AREA, bot_id=BOT_ID)

    def _is_crab_visible(self) -> bool:
        return vision.image_exists(CRAB_IMAGE, area=CRAB_AREA, bot_id=BOT_ID)

    def monitor_until_crab_and_xp_gone(self) -> bool:
        """Keep checking while either purple crab or Strength XP is still visible."""
        self.set_status("MONITOR ACTIVE CRAB")
        self.log("[MONITOR] wachten tot PAARS en Strength XP allebei weg zijn")

        started = time.monotonic()
        last_state: tuple[bool, bool] | None = None

        while not self.stop_requested:
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
            self.set_timer(f"Monitor: {minutes:02d}:{seconds:02d}")

            if not crab_visible and not strength_visible:
                self.log("[READY] paars weg + Strength XP weg -> blue cave")
                self.set_timer("-")
                return True

            time.sleep(MONITOR_POLL_SECONDS)

        return False

    def wait_for_crab(self) -> bool:
        deadline = time.monotonic() + CAVE_WAIT_SECONDS

        while time.monotonic() < deadline:
            if self.stop_requested:
                return False

            remaining = int(deadline - time.monotonic())
            self.set_timer(f"Crab zoeken: {remaining}s")

            if self._is_crab_visible():
                self.log("[CRAB] Gemstone_Crab gevonden")
                self.set_timer("-")
                return True

            time.sleep(1)

        self.set_timer("-")
        return False

    def click_cave_and_wait_for_crab(self) -> bool:
        self.set_status("CLICK BLUE CAVE")
        self.log("[CAVE] blue cave klikken")

        if not click_object(CAVE_OBJECT, bot_id=BOT_ID):
            self.log("[FAIL] cave niet gevonden")
            return False

        self.log("[CAVE] geklikt")
        self.set_status("WAIT FOR CRAB")

        if not self.wait_for_crab():
            self.log(f"[FAIL] geen crab binnen {CAVE_WAIT_SECONDS}s")
            return False

        return True

    def click_crab_and_wait_for_xp(self) -> bool:
        self.set_status("CLICK CRAB")
        self.log("[CLICK] gemrockcrab proberen")

        if not click_object(CRAB_OBJECT, bot_id=BOT_ID):
            self.log("[FAIL] gemrockcrab niet klikbaar")
            return False

        self.log("[CLICK] gemrockcrab geklikt")
        self.set_status("WAIT FOR XP")
        self.log(f"[XP] maximaal {XP_WAIT_SECONDS}s wachten")

        hit = vision.wait_for_image(
            STRENGTH_IMAGE,
            area=STRENGTH_AREA,
            bot_id=BOT_ID,
            timeout_s=XP_WAIT_SECONDS,
        )

        if hit is None:
            self.log("[FAIL] geen Strength XP")
            return False

        self.log("[SUCCESS] Strength XP gevonden")
        return True

    def run_routine(self) -> None:
        try:
            for routine in range(1, MAX_ROUTINES + 1):
                if self.stop_requested:
                    break

                self.root.after(0, lambda r=routine: self.routine_var.set(f"{r} / {MAX_ROUTINES}"))
                self.log(f"[ROUTINE] start {routine}/{MAX_ROUTINES}")

                self.set_status("CHECK LOGIN")
                self.log("[LOGIN] controleren")

                if not is_logged_in(bot_id=BOT_ID):
                    self.log("[STOP] niet ingelogd")
                    self.set_status("NOT LOGGED IN")
                    return

                self.log("[LOGIN] ingelogd")

                strength_visible = self._is_strength_visible()
                crab_visible = self._is_crab_visible()
                self.log(
                    f"[STATE] paars={'JA' if crab_visible else 'NEE'} | "
                    f"strength={'JA' if strength_visible else 'NEE'}"
                )

                # If combat/crab is already active, do not assume a fresh 10-minute cooldown.
                # Keep checking live until both signals disappear, even if only 3 minutes remain.
                if strength_visible:
                    if not self.monitor_until_crab_and_xp_gone():
                        return
                    if not self.click_cave_and_wait_for_crab():
                        continue

                # No XP but the crab is already there: click it directly.
                elif crab_visible:
                    self.log("[CRAB] paars zichtbaar zonder Strength XP -> crab klikken")

                # Neither purple nor XP is visible: go through the blue cave.
                else:
                    self.log("[READY] geen paars + geen Strength XP -> blue cave")
                    if not self.click_cave_and_wait_for_crab():
                        continue

                if not self.click_crab_and_wait_for_xp():
                    continue

                # After a successful click, monitor live instead of sleeping a fixed 10 minutes.
                if not self.monitor_until_crab_and_xp_gone():
                    return

            self.log("[STOP] maximaal aantal routines bereikt")
            self.set_status("MAX ROUTINES")

        except Exception as exc:
            self.log(f"[ERROR] {exc}")
            self.set_status("ERROR")

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
