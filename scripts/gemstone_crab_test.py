from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import ttk

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
SUCCESS_SLEEP_SECONDS = 10 * 60


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

    def interruptible_sleep(self, seconds: int, label: str) -> bool:
        end_time = time.monotonic() + seconds

        while time.monotonic() < end_time:
            if self.stop_requested:
                return False

            remaining = int(end_time - time.monotonic())
            self.set_timer(f"{label}: {remaining}s")
            time.sleep(1)

        self.set_timer("-")
        return True

    def wait_for_crab(self) -> bool:
        deadline = time.monotonic() + CAVE_WAIT_SECONDS

        while time.monotonic() < deadline:
            if self.stop_requested:
                return False

            remaining = int(deadline - time.monotonic())
            self.set_timer(f"Crab zoeken: {remaining}s")

            if vision.image_exists(CRAB_IMAGE, area=CRAB_AREA, bot_id=BOT_ID):
                self.log("[CRAB] Gemstone_Crab gevonden")
                self.set_timer("-")
                return True

            time.sleep(1)

        self.set_timer("-")
        return False

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

                self.set_status("CHECK STRENGTH XP")
                self.log("[XP] controleren")

                if vision.image_exists(STRENGTH_IMAGE, area=STRENGTH_AREA, bot_id=BOT_ID):
                    self.log("[XP] Strength XP nog zichtbaar")
                    self.set_status("XP ACTIVE")

                    if not self.interruptible_sleep(SUCCESS_SLEEP_SECONDS, "XP cooldown"):
                        return

                    continue

                self.log("[XP] geen Strength XP gevonden")

                self.set_status("CHECK CRAB")
                self.log("[CRAB] afbeelding controleren")

                crab_found = vision.image_exists(CRAB_IMAGE, area=CRAB_AREA, bot_id=BOT_ID)

                if not crab_found:
                    self.set_status("CLICK CAVE")
                    self.log("[CRAB] niet zichtbaar")
                    self.log("[CAVE] cave zoeken")

                    if not click_object(CAVE_OBJECT, bot_id=BOT_ID):
                        self.log("[FAIL] cave niet gevonden")
                        continue

                    self.log("[CAVE] geklikt")
                    self.set_status("WAIT FOR CRAB")

                    if not self.wait_for_crab():
                        self.log(f"[FAIL] geen crab binnen {CAVE_WAIT_SECONDS}s")
                        continue

                self.set_status("CLICK CRAB")
                self.log("[CLICK] gemrockcrab proberen")

                if not click_object(CRAB_OBJECT, bot_id=BOT_ID):
                    self.log("[FAIL] gemrockcrab niet klikbaar")
                    continue

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
                    continue

                self.log("[SUCCESS] Strength XP gevonden")
                self.set_status("SUCCESS")
                self.log("[SLEEP] 10 minuten niets doen")

                if not self.interruptible_sleep(SUCCESS_SLEEP_SECONDS, "Cooldown"):
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
