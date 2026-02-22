from __future__ import annotations
import tkinter as tk
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from interfaces import RobotView, Cell
from config import CFG
from metrics import Metrics

@dataclass
class DrawWorld:
    w: int
    h: int
    blocked: set[Cell]
    stations: Dict[str, Cell]

class WarehouseGUI:
    def __init__(self, world: DrawWorld):
        self.world = world

        self.root = tk.Tk()
        self.root.title("Warehouse Simulation - Member 5 (Tkinter)")

        # Canvas
        canvas_w = CFG.margin_px * 2 + world.w * CFG.cell_px
        canvas_h = CFG.margin_px * 2 + world.h * CFG.cell_px
        self.canvas = tk.Canvas(self.root, width=canvas_w, height=canvas_h, bg="white")
        self.canvas.grid(row=0, column=0, padx=10, pady=10)

        # Sidebar stats
        self.side = tk.Frame(self.root)
        self.side.grid(row=0, column=1, sticky="n", padx=10, pady=10)

        self.labels: Dict[str, tk.Label] = {}
        for key in ["step","robots","moved","waited","conflicts_resolved","deadlocks_resolved"]:
            row = tk.Frame(self.side)
            row.pack(anchor="w", pady=2)
            tk.Label(row, text=f"{key}: ", width=18, anchor="w").pack(side="left")
            val = tk.Label(row, text="0", width=10, anchor="w")
            val.pack(side="left")
            self.labels[key] = val

        self._draw_static()

    def _cell_rect(self, cell: Cell):
        c, r = cell
        x0 = CFG.margin_px + c * CFG.cell_px
        y0 = CFG.margin_px + r * CFG.cell_px
        x1 = x0 + CFG.cell_px
        y1 = y0 + CFG.cell_px
        return x0, y0, x1, y1

    def _draw_static(self):
        # grid
        for c in range(self.world.w + 1):
            x = CFG.margin_px + c * CFG.cell_px
            self.canvas.create_line(x, CFG.margin_px, x, CFG.margin_px + self.world.h * CFG.cell_px, fill="#ddd")
        for r in range(self.world.h + 1):
            y = CFG.margin_px + r * CFG.cell_px
            self.canvas.create_line(CFG.margin_px, y, CFG.margin_px + self.world.w * CFG.cell_px, y, fill="#ddd")

        # blocked cells
        for cell in self.world.blocked:
            x0,y0,x1,y1 = self._cell_rect(cell)
            self.canvas.create_rectangle(x0, y0, x1, y1, fill="#8b6b4a", outline="")

        # stations
        for name, cell in self.world.stations.items():
            x0,y0,x1,y1 = self._cell_rect(cell)
            color = "#4aa3ff" if "PACK" in name.upper() else "#44cc66"
            self.canvas.create_rectangle(x0+4, y0+4, x1-4, y1-4, fill=color, outline="")
            self.canvas.create_text((x0+x1)/2, (y0+y1)/2, text=name, fill="white", font=("Arial", 8, "bold"))

    def update(self, robots: List[RobotView], metrics: Metrics):
        # clear dynamic layer by deleting tagged items
        self.canvas.delete("dyn")

        # draw paths first (optional)
        for rv in robots:
            if rv.path:
                pts = []
                for cell in rv.path[:30]:
                    x0,y0,x1,y1 = self._cell_rect(cell)
                    pts.append(((x0+x1)/2, (y0+y1)/2))
                for i in range(len(pts)-1):
                    self.canvas.create_line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                                            fill="#999", width=2, tags="dyn")

        # draw robots
        for rv in robots:
            x0,y0,x1,y1 = self._cell_rect(rv.cell)
            pad = 6
            color = {"MOVING":"#ff6666","WAITING":"#ffcc66","IDLE":"#cccccc","BACKOFF":"#cc66ff"}.get(rv.status, "#ff6666")
            self.canvas.create_oval(x0+pad, y0+pad, x1-pad, y1-pad, fill=color, outline="#333", tags="dyn")
            self.canvas.create_text((x0+x1)/2, (y0+y1)/2, text=rv.robot_id, fill="black", font=("Arial", 10, "bold"), tags="dyn")
            self.canvas.create_text((x0+x1)/2, y1-10, text=rv.status, fill="black", font=("Arial", 7), tags="dyn")

        moved_total = sum(rs.moved for rs in metrics.robots.values())
        waited_total = sum(rs.waited for rs in metrics.robots.values())

        self.labels["step"].config(text=str(metrics.step))
        self.labels["robots"].config(text=str(len(metrics.robots)))
        self.labels["moved"].config(text=str(moved_total))
        self.labels["waited"].config(text=str(waited_total))
        self.labels["conflicts_resolved"].config(text=str(metrics.conflicts_resolved))
        self.labels["deadlocks_resolved"].config(text=str(metrics.deadlocks_resolved))

        self.root.update_idletasks()
        self.root.update()