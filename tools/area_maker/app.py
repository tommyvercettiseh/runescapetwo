from __future__ import annotations

import tkinter as tk
from dataclasses import replace
from tkinter import messagebox, simpledialog, ttk

from core.vision.offsets import get_bot_offset

from .store import EditableArea, load_editable_areas, save_editable_areas

HANDLE = 18
EDGE_HIT = 14
MIN_SIZE = 6


class AreaMaker(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("RuneScape Two - Area Maker")
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(bg="black")
        try:
            self.attributes("-transparentcolor", "black")
        except tk.TclError:
            pass

        self.areas = load_editable_areas()
        self.bot_id = tk.IntVar(value=1)
        self.selected: str | None = None
        self.mode: str | None = None
        self.anchor = (0, 0)
        self.start_area: EditableArea | None = None
        self.new_rect: int | None = None

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self._down)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._up)
        self.canvas.bind("<Motion>", self._motion)
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Delete>", lambda _event: self._delete())

        self._build_panel()
        self._draw()

    def _build_panel(self) -> None:
        panel = tk.Toplevel(self)
        panel.title("Areas")
        panel.geometry(f"420x650+{max(20, self.winfo_screenwidth() - 450)}+40")
        panel.attributes("-topmost", True)
        panel.protocol("WM_DELETE_WINDOW", self.destroy)
        self.panel = panel

        top = ttk.Frame(panel, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Bot").pack(side="left")
        bot_box = ttk.Combobox(top, textvariable=self.bot_id, values=(1, 2, 3, 4), state="readonly", width=5)
        bot_box.pack(side="left", padx=(6, 12))
        bot_box.bind("<<ComboboxSelected>>", lambda _event: self._draw())
        ttk.Button(top, text="Nieuwe area", command=self._start_new).pack(side="left", padx=3)
        ttk.Button(top, text="Opslaan", command=self._save).pack(side="left", padx=3)

        self.tree = ttk.Treeview(panel, columns=("group", "size"), show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Naam")
        self.tree.heading("group", text="Groep")
        self.tree.heading("size", text="Formaat")
        self.tree.column("#0", width=180)
        self.tree.column("group", width=100)
        self.tree.column("size", width=90)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", self._tree_select)

        buttons = ttk.Frame(panel, padding=(10, 0, 10, 8))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Hernoemen", command=self._rename).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(buttons, text="Dupliceren", command=self._duplicate).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(buttons, text="Verwijderen", command=self._delete).pack(side="left", fill="x", expand=True, padx=(4, 0))

        help_text = (
            "Klik in een area om te verplaatsen. Sleep een dikke rand om één zijde te resizen. "
            "Sleep een groot hoekblok voor twee zijden tegelijk. Alleen de geselecteerde area toont handles."
        )
        ttk.Label(panel, text=help_text, wraplength=390, justify="left", padding=10).pack(fill="x")
        self.status = tk.StringVar(value="Kies een area of maak een nieuwe.")
        ttk.Label(panel, textvariable=self.status, padding=(10, 0, 10, 10)).pack(fill="x")
        self._refresh_tree()

    def _offset(self) -> tuple[int, int]:
        return get_bot_offset(self.bot_id.get())

    def _screen_bounds(self, area: EditableArea) -> tuple[int, int, int, int]:
        ox, oy = self._offset()
        return area.x + ox, area.y + oy, area.x + area.width + ox, area.y + area.height + oy

    def _draw(self) -> None:
        self.canvas.delete("area")
        for name, area in self.areas.items():
            x1, y1, x2, y2 = self._screen_bounds(area)
            selected = name == self.selected
            width = 3 if selected else 2
            colour = "#00e5ff" if selected else "#ffd54f"
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=colour, width=width, tags=("area",))
            self.canvas.create_text(x1 + 4, y1 - 8, text=name, fill=colour, anchor="sw", tags=("area",))
            if selected:
                self._draw_handles(x1, y1, x2, y2)

    def _draw_handles(self, x1: int, y1: int, x2: int, y2: int) -> None:
        half = HANDLE // 2
        for x, y in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
            self.canvas.create_rectangle(x - half, y - half, x + half, y + half, fill="#ffffff", outline="#222222", tags=("area",))
        self.canvas.create_line(x1, y1, x2, y1, fill="#00e5ff", width=EDGE_HIT, stipple="gray50", tags=("area",))
        self.canvas.create_line(x1, y2, x2, y2, fill="#00e5ff", width=EDGE_HIT, stipple="gray50", tags=("area",))
        self.canvas.create_line(x1, y1, x1, y2, fill="#00e5ff", width=EDGE_HIT, stipple="gray50", tags=("area",))
        self.canvas.create_line(x2, y1, x2, y2, fill="#00e5ff", width=EDGE_HIT, stipple="gray50", tags=("area",))

    def _hit(self, x: int, y: int) -> tuple[str | None, str | None]:
        names = [self.selected] if self.selected else []
        names += [name for name in reversed(list(self.areas)) if name != self.selected]
        for name in names:
            if name is None:
                continue
            area = self.areas[name]
            x1, y1, x2, y2 = self._screen_bounds(area)
            if not (x1 - HANDLE <= x <= x2 + HANDLE and y1 - HANDLE <= y <= y2 + HANDLE):
                continue
            near_left, near_right = abs(x - x1) <= HANDLE, abs(x - x2) <= HANDLE
            near_top, near_bottom = abs(y - y1) <= HANDLE, abs(y - y2) <= HANDLE
            if near_left and near_top: return name, "nw"
            if near_right and near_top: return name, "ne"
            if near_left and near_bottom: return name, "sw"
            if near_right and near_bottom: return name, "se"
            if x1 <= x <= x2 and abs(y - y1) <= EDGE_HIT: return name, "n"
            if x1 <= x <= x2 and abs(y - y2) <= EDGE_HIT: return name, "s"
            if y1 <= y <= y2 and abs(x - x1) <= EDGE_HIT: return name, "w"
            if y1 <= y <= y2 and abs(x - x2) <= EDGE_HIT: return name, "e"
            if x1 < x < x2 and y1 < y < y2: return name, "move"
        return None, None

    def _motion(self, event) -> None:
        _name, mode = self._hit(event.x, event.y)
        cursors = {"move": "fleur", "n": "sb_v_double_arrow", "s": "sb_v_double_arrow", "e": "sb_h_double_arrow", "w": "sb_h_double_arrow", "nw": "top_left_corner", "se": "bottom_right_corner", "ne": "top_right_corner", "sw": "bottom_left_corner"}
        self.canvas.configure(cursor=cursors.get(mode, "crosshair"))

    def _down(self, event) -> None:
        if self.mode == "new":
            self.anchor = (event.x, event.y)
            self.new_rect = self.canvas.create_rectangle(event.x, event.y, event.x, event.y, outline="#00ff88", width=3)
            return
        name, mode = self._hit(event.x, event.y)
        if name is None:
            self.selected = None
            self._draw()
            return
        self.selected, self.mode = name, mode
        self.anchor = (event.x, event.y)
        self.start_area = self.areas[name]
        self.tree.selection_set(name)
        self.tree.see(name)
        self._draw()

    def _drag(self, event) -> None:
        if self.mode == "new" and self.new_rect is not None:
            self.canvas.coords(self.new_rect, self.anchor[0], self.anchor[1], event.x, event.y)
            return
        if not self.selected or not self.mode or self.start_area is None:
            return
        dx, dy = event.x - self.anchor[0], event.y - self.anchor[1]
        a = self.start_area
        x, y, width, height = a.x, a.y, a.width, a.height
        if self.mode == "move": x, y = x + dx, y + dy
        if "w" in self.mode: x, width = x + dx, width - dx
        if "e" in self.mode: width = width + dx
        if "n" in self.mode: y, height = y + dy, height - dy
        if "s" in self.mode: height = height + dy
        if width < MIN_SIZE or height < MIN_SIZE:
            return
        self.areas[self.selected] = replace(a, x=x, y=y, width=width, height=height)
        self._draw()

    def _up(self, event) -> None:
        if self.mode == "new":
            ox, oy = self._offset()
            x1, x2 = sorted((self.anchor[0] - ox, event.x - ox))
            y1, y2 = sorted((self.anchor[1] - oy, event.y - oy))
            if self.new_rect is not None:
                self.canvas.delete(self.new_rect)
            self.new_rect = None
            self.mode = None
            if x2 - x1 < MIN_SIZE or y2 - y1 < MIN_SIZE:
                self.status.set("Area te klein; probeer opnieuw.")
                return
            name = simpledialog.askstring("Nieuwe area", "Naam:", parent=self.panel)
            if not name:
                self._draw(); return
            name = name.strip()
            if name in self.areas:
                messagebox.showerror("Area", "Deze naam bestaat al.", parent=self.panel)
                self._draw(); return
            self.areas[name] = EditableArea(name, x1, y1, x2 - x1, y2 - y1)
            self.selected = name
            self._refresh_tree(); self._draw(); self._save()
            return
        if self.selected and self.mode:
            self._save()
        self.mode = None
        self.start_area = None
        self._refresh_tree()

    def _start_new(self) -> None:
        self.mode = "new"
        self.selected = None
        self.status.set("Sleep op het scherm om een nieuwe area te tekenen.")
        self._draw()

    def _tree_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if selection:
            self.selected = selection[0]
            self._draw()

    def _refresh_tree(self) -> None:
        selected = self.selected
        self.tree.delete(*self.tree.get_children())
        for name, area in sorted(self.areas.items(), key=lambda item: item[0].lower()):
            self.tree.insert("", "end", iid=name, text=name, values=(area.group, f"{area.width}×{area.height}"))
        if selected in self.areas:
            self.tree.selection_set(selected)

    def _save(self) -> None:
        save_editable_areas(self.areas)
        self.status.set(f"{len(self.areas)} area(s) opgeslagen.")

    def _rename(self) -> None:
        if not self.selected: return
        new = simpledialog.askstring("Hernoemen", "Nieuwe naam:", initialvalue=self.selected, parent=self.panel)
        if not new or new.strip() == self.selected: return
        new = new.strip()
        if new in self.areas:
            messagebox.showerror("Area", "Deze naam bestaat al.", parent=self.panel); return
        old = self.selected
        area = self.areas.pop(old)
        self.areas[new] = replace(area, name=new)
        self.selected = new
        self._save(); self._refresh_tree(); self._draw()

    def _duplicate(self) -> None:
        if not self.selected: return
        source = self.areas[self.selected]
        name = simpledialog.askstring("Dupliceren", "Naam kopie:", initialvalue=f"{source.name}_copy", parent=self.panel)
        if not name or name.strip() in self.areas: return
        name = name.strip()
        self.areas[name] = replace(source, name=name, x=source.x + 12, y=source.y + 12)
        self.selected = name
        self._save(); self._refresh_tree(); self._draw()

    def _delete(self) -> None:
        if not self.selected: return
        if not messagebox.askyesno("Verwijderen", f"'{self.selected}' verwijderen?", parent=self.panel): return
        del self.areas[self.selected]
        self.selected = None
        self._save(); self._refresh_tree(); self._draw()


def main() -> None:
    AreaMaker().mainloop()


if __name__ == "__main__":
    main()
