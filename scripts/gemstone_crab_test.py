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
from core.vision.object_presets import list_object_presets
from definitions.login.is_logged_in import is_logged_in


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


class CrabTestUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Gemstone Crab Test")
        self.root.geometry("680x650")
        self.root.resizable(False, False)

        self.running = False
        self.stop_requested = False

        self.status_var = tk.StringVar(value="IDLE")
        self.routine_var = tk.StringVar(value=f"0 / {MAX_ROUTINES}")
        self.timer_var = tk.StringVar(value="-")

        self.crab_object_var = tk.StringVar(value=DEFAULT_CRAB_OBJECT)
        self.cave_object_var = tk.StringVar(value=DEFAULT_CAVE_OBJECT)

        self._build_ui()
        self.refresh_object_presets(log=False)

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Gemstone Crab Routine", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(main, text="Live status + handmatige objectkeuze", font=("Segoe UI", 10)).pack(
            anchor="w", pady=(0, 12)
        )

        info = ttk.Frame(main)
        info.pack(fill="x")
        self._info_row(info, "Status", self.status_var, 0)
        self._info_row(info, "Routine", self.routine_var, 1)
        self._info_row(info, "Timer", self.timer_var, 2)

        ttk.Separator(main).pack(fill="x", pady=12)

        object_frame = ttk.LabelFrame(main, text="Object presets", padding=10)
        object_frame.pack(fill="x")

        ttk.Label(object_frame, text="Crab object").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self.crab_combo = ttk.Combobox(
            object_frame,
            textvariable=self.crab_object_var,
            state="readonly",
            width=28,
        )
        self.crab_combo.grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Button(
            object_frame,
            text="TEST CLICK",
            command=lambda: self.test_object_click("CRAB", self.crab_object_var.get()),
        ).grid(row=0, column=2, padx=(8, 0), pady=4)

        ttk.Label(object_frame, text="Cave object").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self.cave_combo = ttk.Combobox(
            object_frame,
            textvariable=self.cave_object_var,
            state="readonly",
            width=28,
        )
        self.cave_combo.grid(row=1, column=1, sticky="ew", pady=4)
        ttk.Button(
            object_frame,
            text="TEST CLICK",
            command=lambda: self.test_object_click("CAVE", self.cave_object_var.get()),
        ).grid(row=1, column=2, padx=(8, 0), pady=4)

        ttk.Button(
            object_frame,
            text="REFRESH PRESETS",
            command=self.refresh_object_presets,
        ).grid(row=2, column=1, sticky="w", pady=(8, 0))

        object_frame.columnconfigure(1, weight=1)

        ttk.Separator(main).pack(fill="x", pady=12)

        self.log_box = tk.Text(main, height=19, state="disabled", font=("Consolas", 10))
        self.log_box.pack(fill="both", expand=True)

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=(12, 0))

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
            self.crab_object_var.set(DEFAULT_CRAB_OBJECT if DEFAULT_CRAB_OBJECT in presets else (presets[0] if presets else ""))

        if self.cave_object_var.get() not in presets:
            self.cave_object_var.set(DEFAULT_CAVE_OBJECT if DEFAULT_CAVE_OBJECT in presets else (presets[0] if presets else ""))

        if log:
            self.log(f"[OBJECTS] {len(presets)} presets geladen")
            self.log(
                f"[OBJECTS] crab={self.crab_object_var.get() or '-'} | "
                f"cave={self.cave_object_var.get() or '-'}"
            )

    def test_object_click(self, label: str, object_name: str) -> None:
        if not object_name:
            self.log(f"[{label}] geen object geselecteerd")
            return

        def worker() -> None:
            self.log(f"[{label}] test click: {object_name}")
            try:
                result = click_object(object_name, bot_id=BOT_ID)
                if result:
                    self.log(f"[{label}] klik OK: {object_name}")
                else:
                    message = getattr(result, "message", "niet klikbaar")
                    self.log(f"[{label}] klik FAIL: {message}")
            except Exception as exc:
                self.log(f"[{label}] ERROR: {exc}")

        threading.Thread(target=worker, daemon=True).start()

    def start(self) -> None:
        if self.running:
            return

        crab_object = self.crab_object_var.get().strip()
        cave_object = self.cave_object_var.get().strip()
        if not crab_object or not cave_object:
            self.log("[START] selecteer eerst Crab object en Cave object")
            return

        self.running = True
        self.stop_requested = False
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.crab_combo.configure(state="disabled")
        self.cave_combo.configure(state="disabled")

        self.log(f"[START] crab object={crab_object} | cave object={cave_object}")

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
            self.crab_combo.configure(state="readonly")
            self.cave_combo.configure(state="readonly")

        self.root.after(0, update)

    def _is_strength_visible(self) -> bool:
        return vision.image_exists(STRENGTH_IMAGE, area=STRENGTH_AREA, bot_id=BOT_ID)

    def _is_crab_visible(self) -> bool:
        return vision.image_exists(CRAB_IMAGE, area=CRAB_AREA, bot_id=BOT_ID)

    def monitor_until_crab_and_xp_gone(self) -> bool:
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
                self.log("[READY] paars weg + Strength XP weg -> cave")
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
        object_name = self.cave_object_var.get().strip()
        self.set_status("CLICK CAVE")
        self.log(f"[CAVE] object klikken: {object_name}")

        result = click_object(object_name, bot_id=BOT_ID)
        if not result:
            message = getattr(result, "message", "niet klikbaar")
            self.log(f"[FAIL] cave click: {message}")
            return False

        self.log(f"[CAVE] geklikt: {object_name}")
        self.set_status("WAIT FOR CRAB")

        if not self.wait_for_crab():
            self.log(f"[FAIL] geen crab binnen {CAVE_WAIT_SECONDS}s")
            return False

        return True

    def click_crab_and_wait_for_xp(self) -> bool:
        object_name = self.crab_object_var.get().strip()
        self.set_status("CLICK CRAB")
        self.log(f"[CLICK] crab object proberen: {object_name}")

        result = click_object(object_name, bot_id=BOT_ID)
        if not result:
            message = getattr(result, "message", "niet klikbaar")
            self.log(f"[FAIL] crab click: {message}")
            return False

        self.log(f"[CLICK] crab geklikt: {object_name}")
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

                if strength_visible:
                    if not self.monitor_until_crab_and_xp_gone():
                        return
                    if not self.click_cave_and_wait_for_crab():
                        continue

                elif crab_visible:
                    self.log("[CRAB] paars zichtbaar zonder Strength XP -> geselecteerd crab object klikken")

                else:
                    self.log("[READY] geen paars + geen Strength XP -> geselecteerd cave object")
                    if not self.click_cave_and_wait_for_crab():
                        continue

                if not self.click_crab_and_wait_for_xp():
                    continue

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
