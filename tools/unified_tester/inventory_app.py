from __future__ import annotations

import threading
import time
import tkinter as tk
from queue import Empty, SimpleQueue
from tkinter import messagebox, ttk

from tools.unified_tester.app import UnifiedTester as BaseUnifiedTester
from tools.unified_tester.inventory_checker import (
    InventoryCheckResult,
    check_inventory,
    demo_inventory,
)


BAR_COLOURS = {
    "neutral": "#6B7280",
    "running": "#2563EB",
    "success": "#15803D",
    "failure": "#B91C1C",
}

SLOT_COLOURS = {
    "empty": "#D1D5DB",
    "occupied": "#15803D",
    "image": "#2563EB",
}


class UnifiedTester(BaseUnifiedTester):
    def __init__(self) -> None:
        self.inventory_image_var = tk.StringVar(value="Item_Axe")
        self.inventory_summary_var = tk.StringVar(
            value="Occupied: 0/28. Full: FALSE. Empty: TRUE."
        )
        self.inventory_image_summary_var = tk.StringVar(
            value="Image slots: None."
        )
        self._inventory_slot_labels: dict[int, tk.Label] = {}
        self._inventory_results: SimpleQueue[
            tuple[float, InventoryCheckResult | None, Exception | None]
        ] = SimpleQueue()

        super().__init__()
        self.geometry("900x720")
        self.minsize(800, 620)
        self._add_inventory_tab()
        self._render_inventory(demo_inventory(self.inventory_image_var.get()))

    def _add_inventory_tab(self) -> None:
        self.inventory_tab = ttk.Frame(self.tabs, padding=14)
        self.tabs.insert(1, self.inventory_tab, text="Inventory")
        self.inventory_tab.columnconfigure(1, weight=1)
        self.inventory_tab.rowconfigure(4, weight=1)

        ttk.Label(self.inventory_tab, text="Image name").grid(
            row=0,
            column=0,
            sticky="w",
            pady=5,
        )
        ttk.Entry(
            self.inventory_tab,
            textvariable=self.inventory_image_var,
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(12, 12),
            pady=5,
        )

        buttons = ttk.Frame(self.inventory_tab)
        buttons.grid(row=0, column=2, sticky="e")
        self.inventory_demo_button = ttk.Button(
            buttons,
            text="Load demo",
            command=self._load_inventory_demo,
        )
        self.inventory_demo_button.pack(side="left", padx=(0, 8))
        self.inventory_scan_button = ttk.Button(
            buttons,
            text="Scan inventory",
            command=self._run_inventory_scan,
        )
        self.inventory_scan_button.pack(side="left")

        self.inventory_bar = tk.Label(
            self.inventory_tab,
            text="READY.",
            anchor="w",
            bg=BAR_COLOURS["neutral"],
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
        )
        self.inventory_bar.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(10, 8),
        )

        ttk.Label(
            self.inventory_tab,
            textvariable=self.inventory_summary_var,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=2, column=0, columnspan=3, sticky="w")
        ttk.Label(
            self.inventory_tab,
            textvariable=self.inventory_image_summary_var,
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(2, 8))

        grid_frame = ttk.LabelFrame(
            self.inventory_tab,
            text="Inventory slots",
            padding=10,
        )
        grid_frame.grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="nsew",
        )
        for column in range(4):
            grid_frame.columnconfigure(column, weight=1)
        for row in range(7):
            grid_frame.rowconfigure(row, weight=1)

        for number in range(1, 29):
            row = (number - 1) // 4
            column = (number - 1) % 4
            label = tk.Label(
                grid_frame,
                text=f"{number:02d}\nEMPTY",
                bg=SLOT_COLOURS["empty"],
                fg="black",
                relief="solid",
                borderwidth=1,
                font=("Segoe UI", 10, "bold"),
                padx=8,
                pady=8,
            )
            label.grid(
                row=row,
                column=column,
                sticky="nsew",
                padx=4,
                pady=4,
            )
            self._inventory_slot_labels[number] = label

        legend = ttk.Frame(self.inventory_tab)
        legend.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self._legend_item(legend, "Empty", SLOT_COLOURS["empty"], "black")
        self._legend_item(
            legend,
            "Occupied",
            SLOT_COLOURS["occupied"],
            "white",
        )
        self._legend_item(
            legend,
            "Image match",
            SLOT_COLOURS["image"],
            "white",
        )

    def _legend_item(
        self,
        parent: ttk.Frame,
        text: str,
        background: str,
        foreground: str,
    ) -> None:
        tk.Label(
            parent,
            text=text,
            bg=background,
            fg=foreground,
            padx=8,
            pady=3,
        ).pack(side="left", padx=(0, 8))

    def _set_running(self, running: bool) -> None:
        super()._set_running(running)
        state = "disabled" if running else "normal"
        if hasattr(self, "inventory_scan_button"):
            self.inventory_scan_button.configure(state=state)
        if hasattr(self, "inventory_demo_button"):
            self.inventory_demo_button.configure(state=state)

    def _set_inventory_bar(self, text: str, state: str) -> None:
        self.inventory_bar.configure(text=text, bg=BAR_COLOURS[state])

    def _run_inventory_scan(self) -> None:
        if self._running:
            messagebox.showinfo("Busy", "A test is already running.")
            return

        try:
            bot_id = self._bot_id()
        except Exception as exc:
            messagebox.showerror("Inventory", str(exc))
            return

        image_name = self.inventory_image_var.get()
        self._set_running(True)
        self._set_inventory_bar("RUNNING.", "running")
        self.status_var.set("Running inventory scan.")

        def worker() -> None:
            started = time.perf_counter()
            try:
                result = check_inventory(bot_id, image_name)
            except Exception as exc:
                self._inventory_results.put(
                    (time.perf_counter() - started, None, exc)
                )
            else:
                self._inventory_results.put(
                    (time.perf_counter() - started, result, None)
                )

        threading.Thread(
            target=worker,
            name="inventory-checker-worker",
            daemon=True,
        ).start()
        self.after(25, self._poll_inventory_worker)

    def _poll_inventory_worker(self) -> None:
        try:
            elapsed, result, error = self._inventory_results.get_nowait()
        except Empty:
            self.after(25, self._poll_inventory_worker)
            return

        if error is not None:
            self._set_inventory_bar("ERROR.", "failure")
            self.inventory_summary_var.set(f"{type(error).__name__}: {error}")
            self.inventory_image_summary_var.set("Image slots: Unknown.")
            self.status_var.set(f"Failed after {elapsed * 1000:.1f} ms.")
        elif result is not None:
            self._render_inventory(result)
            self.status_var.set(f"Done in {elapsed * 1000:.1f} ms.")

        self._set_running(False)

    def _load_inventory_demo(self) -> None:
        if self._running:
            messagebox.showinfo("Busy", "A test is already running.")
            return
        self._render_inventory(demo_inventory(self.inventory_image_var.get()))
        self.status_var.set("Demo loaded.")

    def _render_inventory(self, result: InventoryCheckResult) -> None:
        image_slots = set(result.image_slots)

        for slot in result.slots:
            label = self._inventory_slot_labels[slot.number]
            if slot.number in image_slots:
                label.configure(
                    text=f"{slot.number:02d}\nIMAGE",
                    bg=SLOT_COLOURS["image"],
                    fg="white",
                )
            elif slot.occupied:
                label.configure(
                    text=f"{slot.number:02d}\nOCCUPIED",
                    bg=SLOT_COLOURS["occupied"],
                    fg="white",
                )
            else:
                label.configure(
                    text=f"{slot.number:02d}\nEMPTY",
                    bg=SLOT_COLOURS["empty"],
                    fg="black",
                )

        self.inventory_summary_var.set(
            f"Occupied: {result.occupied_count}/28. "
            f"Full: {'TRUE' if result.full else 'FALSE'}. "
            f"Empty: {'TRUE' if result.empty else 'FALSE'}."
        )

        image_slots_text = (
            ", ".join(map(str, result.image_slots))
            if result.image_slots
            else "None"
        )
        prefix = "Demo. " if result.demo else ""
        self.inventory_image_summary_var.set(
            f"{prefix}{result.image_name or 'No image'} slots: "
            f"{image_slots_text}."
        )

        if result.full:
            self._set_inventory_bar("FULL.", "success")
        elif result.empty:
            self._set_inventory_bar("EMPTY.", "neutral")
        else:
            self._set_inventory_bar("PARTIAL.", "running")


if __name__ == "__main__":
    UnifiedTester().mainloop()
