from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import mouse_engine


class MouseEngineSetup(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("RuneScape Two - Mouse Engine Setup")
        self.geometry("820x560")
        self.minsize(720, 500)

        settings = mouse_engine.load_settings()
        self.enabled = tk.BooleanVar(value=bool(settings["enabled"]))
        self.provider = tk.StringVar(value=str(settings["provider"]))
        self.package_url = tk.StringVar(value=str(settings["package_url"]))
        self.profile_path = tk.StringVar(value=str(settings["profile_path"]))
        self.fallback = tk.BooleanVar(value=bool(settings["fallback_on_error"]))
        self.radius = tk.StringVar(value=str(settings["default_target_radius_px"]))
        self.padding = tk.StringVar(value=str(settings["default_padding_px"]))
        self.status = tk.StringVar(value="Klaar om te configureren")
        self._buttons: list[ttk.Button] = []

        self._build()

    def _build(self) -> None:
        root = ttk.Frame(self, padding=24)
        root.pack(fill="both", expand=True)
        root.columnconfigure(1, weight=1)

        ttk.Label(root, text="Mouse Engine", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 6)
        )
        ttk.Label(
            root,
            text="Installeer en activeer een zelfstandige Mouse-GitHub voor RuneScape Two.",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 20))

        ttk.Checkbutton(root, text="Externe Mouse gebruiken", variable=self.enabled).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=6
        )
        self._field(root, 3, "Provider", self.provider)
        self._field(root, 4, "GitHub-package", self.package_url)
        self._field(root, 5, "Persoonlijk profiel", self.profile_path, browse=True)
        self._field(root, 6, "Standaard doelradius", self.radius, width=12)
        self._field(root, 7, "Standaard padding", self.padding, width=12)
        ttk.Checkbutton(
            root,
            text="Bij een fout automatisch de ingebouwde muis gebruiken",
            variable=self.fallback,
        ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(10, 16))

        actions = ttk.Frame(root)
        actions.grid(row=9, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        for column in range(4):
            actions.columnconfigure(column, weight=1)
        for column, (label, command) in enumerate(
            (
                ("Instellingen opslaan", self._save),
                ("Installeren / updaten", self._install),
                ("Verbinding testen", self._test_connection),
                ("Test beweging", self._test_movement),
            )
        ):
            button = ttk.Button(actions, text=label, command=command)
            button.grid(row=0, column=column, sticky="ew", padx=(0 if column == 0 else 6, 0))
            self._buttons.append(button)

        ttk.Separator(root).grid(row=10, column=0, columnspan=3, sticky="ew", pady=8)
        ttk.Label(root, textvariable=self.status, font=("Segoe UI", 10, "bold")).grid(
            row=11, column=0, columnspan=3, sticky="w", pady=(4, 8)
        )
        self.output = tk.Text(root, height=9, wrap="word", font=("Consolas", 9))
        self.output.grid(row=12, column=0, columnspan=3, sticky="nsew")
        root.rowconfigure(12, weight=1)

    def _field(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        *,
        browse: bool = False,
        width: int | None = None,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 16), pady=6)
        entry = ttk.Entry(parent, textvariable=variable, width=width)
        entry.grid(row=row, column=1, sticky="ew" if width is None else "w", pady=6)
        if browse:
            ttk.Button(parent, text="Bladeren", command=self._browse_profile).grid(
                row=row, column=2, padx=(8, 0), pady=6
            )

    def _browse_profile(self) -> None:
        path = filedialog.askopenfilename(
            title="Kies master_profile.json",
            filetypes=(("JSON-profiel", "*.json"), ("Alle bestanden", "*.*")),
        )
        if path:
            self.profile_path.set(path)

    def _collect(self) -> dict:
        try:
            radius = max(1, int(self.radius.get()))
            padding = max(0, int(self.padding.get()))
        except ValueError as exc:
            raise ValueError("Radius en padding moeten gehele getallen zijn") from exc
        return {
            "enabled": self.enabled.get(),
            "provider": self.provider.get().strip(),
            "package_url": self.package_url.get().strip(),
            "profile_path": self.profile_path.get().strip(),
            "fallback_on_error": self.fallback.get(),
            "default_target_radius_px": radius,
            "default_padding_px": padding,
        }

    def _write(self, value: str) -> None:
        self.output.insert("end", value.rstrip() + "\n")
        self.output.see("end")

    def _save(self, *, notify: bool = True) -> dict | None:
        try:
            settings = mouse_engine.save_settings(self._collect())
        except (ValueError, mouse_engine.MouseEngineError) as exc:
            messagebox.showerror("Instellingen", str(exc), parent=self)
            return None
        self.status.set("Instellingen opgeslagen")
        if notify:
            self._write(f"Opgeslagen in {mouse_engine.CONFIG_PATH}")
        return settings

    def _set_busy(self, busy: bool, status: str) -> None:
        self.status.set(status)
        for button in self._buttons:
            button.configure(state="disabled" if busy else "normal")

    def _install(self) -> None:
        settings = self._save(notify=False)
        if settings is None:
            return
        self._set_busy(True, "Mouse-package wordt geïnstalleerd...")
        self._write(f"Installeren: {settings['package_url']}")

        def worker() -> None:
            try:
                result = mouse_engine.install_configured_package(settings)
                output = result.stdout.strip() or "Installatie voltooid."
                self.after(0, lambda: self._install_done(True, output))
            except Exception as exc:
                message = str(exc)
                self.after(0, lambda: self._install_done(False, message))

        threading.Thread(target=worker, daemon=True).start()

    def _install_done(self, success: bool, message: str) -> None:
        self._set_busy(False, "Installatie voltooid" if success else "Installatie mislukt")
        self._write(message)
        if success:
            self._test_connection()
        else:
            messagebox.showerror("Mouse installeren", message, parent=self)

    def _test_connection(self) -> None:
        settings = self._save(notify=False)
        if settings is None:
            return
        status = mouse_engine.provider_status(settings)
        if status.get("ready"):
            manifest = status["manifest"]
            message = (
                f"Gereed: {manifest['name']} {manifest['version']}\n"
                f"Profiel: {status['profile_path']}"
            )
            self.status.set("Mouse Engine is gereed")
            self._write(message)
        else:
            problem = str(status.get("error") or "Persoonlijk profiel niet gevonden")
            self.status.set("Mouse Engine is nog niet gereed")
            self._write(problem)

    def _test_movement(self) -> None:
        settings = self._save(notify=False)
        if settings is None:
            return
        status = mouse_engine.provider_status(settings)
        if not status.get("ready"):
            problem = str(status.get("error") or "Persoonlijk profiel niet gevonden")
            messagebox.showerror("Test beweging", problem, parent=self)
            return

        target = tk.Toplevel(self)
        target.title("Mouse-testdoel")
        target.attributes("-topmost", True)
        width, height = 180, 120
        x = max(20, self.winfo_screenwidth() // 2 - width // 2)
        y = max(20, self.winfo_screenheight() // 2 - height // 2)
        target.geometry(f"{width}x{height}+{x}+{y}")
        button = ttk.Button(
            target,
            text="TESTDOEL\nMouse hoort hier te klikken",
            command=lambda: self._movement_hit(target),
        )
        button.pack(fill="both", expand=True, padx=8, pady=8)
        target.update_idletasks()
        target_x = x + width // 2
        target_y = y + height // 2
        self.status.set("Testbeweging start over één seconde...")

        def worker() -> None:
            try:
                time.sleep(1.0)
                from core import mouse

                mouse.move_and_click(target_x, target_y, target_radius=30)
            except Exception as exc:
                message = str(exc)
                self.after(0, lambda: self._movement_failed(target, message))

        threading.Thread(target=worker, daemon=True).start()

    def _movement_hit(self, target: tk.Toplevel) -> None:
        if target.winfo_exists():
            target.destroy()
        self.status.set("Testbeweging geslaagd")
        self._write("De externe Mouse heeft het testdoel aangeklikt.")

    def _movement_failed(self, target: tk.Toplevel, message: str) -> None:
        if target.winfo_exists():
            target.destroy()
        self.status.set("Testbeweging mislukt")
        self._write(message)
        messagebox.showerror("Test beweging", message, parent=self)


def main() -> None:
    MouseEngineSetup().mainloop()


if __name__ == "__main__":
    main()
