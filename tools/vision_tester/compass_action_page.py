from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from actions.camera.set_compass import set_compass
from definitions.camera.compass import is_compass_north
from . import modern_ui


DIRECTIONS = ("north", "east", "south", "west")


class CompassActionPage(ctk.CTkFrame):
    """Minimal live tester for the high-level compass setter."""

    def __init__(self, parent) -> None:
        super().__init__(parent, fg_color="transparent")
        self.bot_id = tk.StringVar(value="1")
        self.direction = tk.StringVar(value="north")
        self.status = tk.StringVar(value="Kies een richting en klik Set compass.")
        self.result = tk.StringVar(value="—")
        self._build()

    def activate(self) -> None:
        self._refresh_north_check()

    def deactivate(self) -> None:
        pass

    def capture_hotkey(self) -> None:
        self._refresh_north_check()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        card = modern_ui._card(self)
        card.grid(row=0, column=0, sticky="ew", padx=18, pady=18)
        card.grid_columnconfigure(1, weight=1)

        modern_ui._label(card, "COMPASS SETTER", size=14, bold=True).grid(
            row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(16, 10)
        )

        modern_ui._label(card, "BOT", muted=True, size=10).grid(
            row=1, column=0, sticky="w", padx=(16, 8)
        )
        ctk.CTkOptionMenu(
            card,
            values=["1", "2", "3", "4"],
            variable=self.bot_id,
            width=90,
            fg_color=modern_ui.CARD_ALT,
            button_color=modern_ui.BORDER,
            button_hover_color=modern_ui.CONTROL_HOVER,
            text_color=modern_ui.TEXT,
        ).grid(row=2, column=0, sticky="w", padx=(16, 8), pady=(4, 14))

        modern_ui._label(card, "DIRECTION", muted=True, size=10).grid(
            row=1, column=1, sticky="w", padx=8
        )
        ctk.CTkOptionMenu(
            card,
            values=list(DIRECTIONS),
            variable=self.direction,
            width=180,
            fg_color=modern_ui.CARD_ALT,
            button_color=modern_ui.BORDER,
            button_hover_color=modern_ui.CONTROL_HOVER,
            text_color=modern_ui.TEXT,
        ).grid(row=2, column=1, sticky="w", padx=8, pady=(4, 14))

        ctk.CTkButton(
            card,
            text="Set compass",
            command=self._set,
            height=40,
            corner_radius=8,
            fg_color=modern_ui.ACCENT,
            hover_color=modern_ui.ACCENT_HOVER,
            text_color="#111509",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=2, column=2, sticky="e", padx=(8, 16), pady=(4, 14))

        check = modern_ui._card(self)
        check.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))
        check.grid_columnconfigure(1, weight=1)

        modern_ui._label(check, "NORTH CHECK", size=12, bold=True).grid(
            row=0, column=0, sticky="w", padx=16, pady=16
        )
        self.result_label = ctk.CTkLabel(
            check,
            textvariable=self.result,
            width=160,
            height=38,
            corner_radius=8,
            fg_color=modern_ui.BORDER,
            text_color=modern_ui.TEXT,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.result_label.grid(row=0, column=1, sticky="w", padx=8, pady=16)
        ctk.CTkButton(
            check,
            text="Check north",
            command=self._refresh_north_check,
            width=130,
            height=36,
            corner_radius=8,
            fg_color=modern_ui.CARD_ALT,
            hover_color=modern_ui.CONTROL_HOVER,
            text_color=modern_ui.TEXT,
        ).grid(row=0, column=2, sticky="e", padx=16, pady=16)

        modern_ui._label(self, "", textvariable=self.status, muted=True, size=11).grid(
            row=2, column=0, sticky="w", padx=24
        )

    def _refresh_north_check(self) -> bool:
        try:
            value = is_compass_north(bot_id=int(self.bot_id.get()))
        except Exception as exc:
            self.result.set("ERROR")
            self.result_label.configure(fg_color=modern_ui.BORDER)
            self.status.set(f"Compass check fout: {exc}")
            return False

        self.result.set("TRUE" if value else "FALSE")
        self.result_label.configure(
            fg_color=modern_ui.SUCCESS if value else modern_ui.DANGER,
            text_color="white",
        )
        self.status.set("Compass_NorthCheck gevonden." if value else "Compass_NorthCheck niet gevonden.")
        return value

    def _set(self) -> None:
        direction = self.direction.get().strip().lower()
        try:
            success = set_compass(direction, bot_id=int(self.bot_id.get()))
        except Exception as exc:
            self.status.set(f"Set compass fout: {exc}")
            return

        if direction == "north":
            north = self._refresh_north_check()
            self.status.set(
                "North gezet en bevestigd." if success and north else "North kon niet bevestigd worden."
            )
        else:
            self.status.set(
                f"Compass {direction} gezet." if success else f"Compass {direction} zetten mislukt."
            )


__all__ = ["CompassActionPage"]
