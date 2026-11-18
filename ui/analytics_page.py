"""
SYSCORE — Module C: Resource Analytics & Historical Trends
SQLite historical query engine, time-range selectors, aggregate statistics,
and CSV export facility.
"""
from datetime import datetime
import os
import queue
import threading
from tkinter import filedialog
from typing import Dict, List, Optional

import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

import config
from core.database import Database
from .components import MetricCard
from utils.helpers import format_bytes, format_rate, format_percent


class AnalyticsPage(ctk.CTkFrame):
    """
    Dedicated analytics page backed by SQLite persistent storage.
    Visualizes historical resource metrics across customizable time intervals
    and computes Min, Max, and Average aggregate statistics.
    Uses queue.Queue for thread-safe UI updates.
    """
    def __init__(self, master, db: Database, **kwargs):
        super().__init__(master, fg_color=config.THEME["bg_main"], corner_radius=0, **kwargs)
        self.db = db
        self._current_range_minutes: Optional[float] = 15.0  # Default 15 minutes
        self._range_buttons: Dict[str, ctk.CTkButton] = {}
        self._analytics_queue = queue.Queue()

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=16)

        # 1. Header & Time Range Selector
        self._build_header()

        # 2. Aggregate Summary Statistics Cards
        self._build_stats_cards()

        # 3. Historical Matplotlib Charts
        self._build_charts()

        # 4. Export & Management Bar
        self._build_export_bar()

        # Start queue poller on main thread
        self.after(50, self._poll_analytics_queue)

        # Load initial historical data
        self.load_analytics()

    def _build_header(self):
        head = ctk.CTkFrame(self.scroll, fg_color="transparent")
        head.pack(fill="x", pady=(4, 12))

        # Title & Subtitle
        tbox = ctk.CTkFrame(head, fg_color="transparent")
        tbox.pack(side="left")

        title = ctk.CTkLabel(
            tbox,
            text="Resource Analytics & Historical Trends",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=config.THEME["text_primary"],
        )
        title.pack(anchor="w")

        self.db_info_label = ctk.CTkLabel(
            tbox,
            text="Persistent Storage: SQLite (syscore.db) | Querying historical trends...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=config.THEME["text_muted"],
        )
        self.db_info_label.pack(anchor="w", pady=(2, 0))

        # Range Selector Toolbar
        rbox = ctk.CTkFrame(head, fg_color="transparent")
        rbox.pack(side="right")

        ranges = [
            ("5m", 5.0, "Last 5m"),
            ("15m", 15.0, "Last 15m"),
            ("1h", 60.0, "Last 1h"),
            ("24h", 1440.0, "Last 24h"),
            ("all", None, "All Time"),
        ]

        for key, minutes, label in ranges:
            btn = ctk.CTkButton(
                rbox,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                width=72,
                height=32,
                corner_radius=6,
                fg_color=config.THEME["btn_primary"] if minutes == self._current_range_minutes else config.THEME["bg_card"],
                hover_color=config.THEME["btn_primary_hover"],
                command=lambda m=minutes, k=key: self._select_range(m, k),
            )
            btn.pack(side="left", padx=3)
            self._range_buttons[key] = btn

    def _select_range(self, minutes: Optional[float], key: str):
        self._current_range_minutes = minutes
        for k, btn in self._range_buttons.items():
            if k == key:
                btn.configure(fg_color=config.THEME["btn_primary"], text_color="#ffffff")
            else:
                btn.configure(fg_color=config.THEME["bg_card"], text_color=config.THEME["text_secondary"])
        self.load_analytics()

    def _build_stats_cards(self):
        """Four summary cards showing Min, Max, and Avg aggregates."""
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, 14))
        row.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="stat_card")

        # CPU Stats
        self.cpu_stat_card = MetricCard(
            row,
            title="CPU Utilization Stats",
            initial_value="--%",
            subtitle="Min: -- | Avg: -- | Max: --",
            accent_color=config.THEME["cpu"],
            show_progress=False,
        )
        self.cpu_stat_card.grid(row=0, column=0, padx=6, pady=4, sticky="nsew")

        # RAM Stats
        self.ram_stat_card = MetricCard(
            row,
            title="Memory Usage Stats",
            initial_value="--%",
            subtitle="Min: -- | Avg: -- | Max: --",
            accent_color=config.THEME["ram"],
            show_progress=False,
        )
        self.ram_stat_card.grid(row=0, column=1, padx=6, pady=4, sticky="nsew")

        # Disk I/O Peak Stats
        self.disk_stat_card = MetricCard(
            row,
            title="Disk I/O Peaks",
            initial_value="-- KB/s",
            subtitle="Peak Read: -- | Peak Write: --",
            accent_color=config.THEME["disk"],
            show_progress=False,
        )
        self.disk_stat_card.grid(row=0, column=2, padx=6, pady=4, sticky="nsew")

        # Network Peak Stats
        self.net_stat_card = MetricCard(
            row,
            title="Network Peaks",
            initial_value="-- KB/s",
            subtitle="Peak Down: -- | Peak Up: --",
            accent_color=config.THEME["net_down"],
            show_progress=False,
        )
        self.net_stat_card.grid(row=0, column=3, padx=6, pady=4, sticky="nsew")

    def _build_charts(self):
        """Construct historical 4-pane Matplotlib charts."""
        chart_box = ctk.CTkFrame(
            self.scroll,
            fg_color=config.THEME["bg_card"],
            border_color=config.THEME["border"],
            border_width=1,
            corner_radius=10,
        )
        chart_box.pack(fill="both", expand=True, pady=(0, 14))

        # Header inside chart frame
        chead = ctk.CTkFrame(chart_box, fg_color="transparent")
        chead.pack(fill="x", padx=16, pady=(12, 6))

        ctitle = ctk.CTkLabel(
            chead,
            text="HISTORICAL UTILIZATION TRENDS",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=config.THEME["text_secondary"],
        )
        ctitle.pack(side="left")

        self.chart_status_lbl = ctk.CTkLabel(
            chead,
            text="Querying database...",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=config.THEME["text_muted"],
        )
        self.chart_status_lbl.pack(side="right")

        # Matplotlib Figure
        self.fig = Figure(figsize=(10, 6.2), dpi=100, facecolor=config.THEME["bg_card"])
        self.fig.subplots_adjust(left=0.06, right=0.96, top=0.92, bottom=0.12, hspace=0.40, wspace=0.18)

        self.ax_cpu = self.fig.add_subplot(2, 2, 1)
        self.ax_mem = self.fig.add_subplot(2, 2, 2)
        self.ax_disk = self.fig.add_subplot(2, 2, 3)
        self.ax_net = self.fig.add_subplot(2, 2, 4)
        self.axes = [self.ax_cpu, self.ax_mem, self.ax_disk, self.ax_net]

        for ax in self.axes:
            self._style_axis(ax)

        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_box)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True, padx=12, pady=(0, 14))

    def _style_axis(self, ax):
        ax.set_facecolor(config.THEME["bg_card_inner"])
        ax.tick_params(colors=config.THEME["text_muted"], labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(config.THEME["border"])
        ax.grid(True, linestyle="--", color="#21262d", alpha=0.6)

    def _build_export_bar(self):
        bar = ctk.CTkFrame(
            self.scroll,
            fg_color=config.THEME["bg_card"],
            border_color=config.THEME["border"],
            border_width=1,
            corner_radius=8,
            height=48,
        )
        bar.pack(fill="x", pady=(0, 10))
        bar.pack_propagate(False)

        info = ctk.CTkLabel(
            bar,
            text="Export historical data to CSV for external OS lab analysis or viva reporting.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=config.THEME["text_secondary"],
        )
        info.pack(side="left", padx=16)

        self.btn_export = ctk.CTkButton(
            bar,
            text="📥  Export to CSV",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=config.THEME["btn_primary"],
            hover_color=config.THEME["btn_primary_hover"],
            height=32,
            width=140,
            command=self._handle_export_csv,
        )
        self.btn_export.pack(side="right", padx=14)

    def load_analytics(self):
        """Asynchronously load database records and statistics via queue."""
        self.chart_status_lbl.configure(text="Querying SQLite database...")

        def worker():
            try:
                rows = self.db.get_history(time_range_minutes=self._current_range_minutes)
                stats = self.db.get_statistics(time_range_minutes=self._current_range_minutes)
                total_db_records = self.db.get_record_count()
                self._analytics_queue.put(("success", rows, stats, total_db_records))
            except Exception as e:
                self._analytics_queue.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_analytics_queue(self):
        try:
            while not self._analytics_queue.empty():
                item = self._analytics_queue.get_nowait()
                if item[0] == "success":
                    _, rows, stats, total_db_records = item
                    self._apply_analytics_data(rows, stats, total_db_records)
                elif item[0] == "error":
                    self.chart_status_lbl.configure(
                        text=f"Database Query Error: {item[1]}",
                        text_color=config.THEME["status_error"],
                    )
        except Exception:
            pass
        finally:
            self.after(50, self._poll_analytics_queue)

    def _apply_analytics_data(self, rows: List[dict], stats: dict, total_records: int):
        count = stats.get("count", 0)
        self.db_info_label.configure(
            text=f"Persistent Storage: SQLite ({total_records} total logged samples) | Viewing {count} in range"
        )
        self.chart_status_lbl.configure(text=f"Rendered {count} data points")

        # Update Summary Cards
        if count > 0:
            avg_cpu = stats.get("avg_cpu", 0.0)
            min_cpu = stats.get("min_cpu", 0.0)
            max_cpu = stats.get("max_cpu", 0.0)
            self.cpu_stat_card.update_data(
                value=f"{avg_cpu:.1f}% Avg",
                subtitle=f"Min: {min_cpu:.1f}% | Max: {max_cpu:.1f}%",
            )

            avg_mem = stats.get("avg_mem", 0.0)
            min_mem = stats.get("min_mem", 0.0)
            max_mem = stats.get("max_mem", 0.0)
            self.ram_stat_card.update_data(
                value=f"{avg_mem:.1f}% Avg",
                subtitle=f"Min: {min_mem:.1f}% | Max: {max_mem:.1f}%",
            )

            max_dr = stats.get("max_disk_read", 0.0)
            max_dw = stats.get("max_disk_write", 0.0)
            self.disk_stat_card.update_data(
                value=f"{max_dr:.0f} KB/s",
                subtitle=f"Peak Read: {max_dr:.0f} | Peak Write: {max_dw:.0f} KB/s",
            )

            max_dn = stats.get("max_net_down", 0.0)
            max_up = stats.get("max_net_up", 0.0)
            self.net_stat_card.update_data(
                value=f"{max_dn:.0f} KB/s",
                subtitle=f"Peak Down: {max_dn:.0f} | Peak Up: {max_up:.0f} KB/s",
            )
        else:
            self.cpu_stat_card.update_data("No Data", "No samples logged in window")
            self.ram_stat_card.update_data("No Data", "No samples logged in window")
            self.disk_stat_card.update_data("No Data", "No samples logged in window")
            self.net_stat_card.update_data("No Data", "No samples logged in window")

        # Clear and redraw axes
        for ax in self.axes:
            ax.clear()
            self._style_axis(ax)

        if not rows:
            self.ax_cpu.set_title("No Logged Historical Data Available", fontsize=10, color=config.THEME["swap"])
            self.canvas.draw_idle()
            return

        # Prepare dates and values
        dates = []
        for r in rows:
            try:
                dates.append(datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S"))
            except Exception:
                dates.append(datetime.fromtimestamp(r.get("epoch_time", 0)))

        cpu_y = [r["cpu_percent"] for r in rows]
        ram_y = [r["mem_percent"] for r in rows]
        swap_y = [r["swap_percent"] for r in rows]
        disk_r_y = [r["disk_read_kbs"] for r in rows]
        disk_w_y = [r["disk_write_kbs"] for r in rows]
        net_d_y = [r["net_down_kbs"] for r in rows]
        net_u_y = [r["net_up_kbs"] for r in rows]

        # 1. CPU Chart
        self.ax_cpu.plot(dates, cpu_y, color=config.THEME["cpu"], linewidth=1.5, label="CPU %")
        self.ax_cpu.set_title("CPU Utilization (%)", fontsize=10, color=config.THEME["text_primary"], weight="bold", pad=6)
        self.ax_cpu.set_ylim(0, 100)

        # 2. Memory Chart
        self.ax_mem.plot(dates, ram_y, color=config.THEME["ram"], linewidth=1.5, label="RAM %")
        self.ax_mem.plot(dates, swap_y, color=config.THEME["swap"], linewidth=1.2, linestyle="--", label="Swap %")
        self.ax_mem.set_title("Memory & Swap (%)", fontsize=10, color=config.THEME["text_primary"], weight="bold", pad=6)
        self.ax_mem.set_ylim(0, 100)
        self.ax_mem.legend(loc="upper left", fontsize=8, facecolor=config.THEME["bg_card"], edgecolor=config.THEME["border"], labelcolor=config.THEME["text_primary"])

        # 3. Disk I/O Chart
        self.ax_disk.plot(dates, disk_r_y, color=config.THEME["disk"], linewidth=1.4, label="Read")
        self.ax_disk.plot(dates, disk_w_y, color=config.THEME["disk_write"], linewidth=1.4, linestyle="--", label="Write")
        self.ax_disk.set_title("Disk I/O Transfer Rate (KB/s)", fontsize=10, color=config.THEME["text_primary"], weight="bold", pad=6)
        self.ax_disk.set_ylim(bottom=0)
        self.ax_disk.legend(loc="upper left", fontsize=8, facecolor=config.THEME["bg_card"], edgecolor=config.THEME["border"], labelcolor=config.THEME["text_primary"])

        # 4. Network Chart
        self.ax_net.plot(dates, net_d_y, color=config.THEME["net_down"], linewidth=1.4, label="Download")
        self.ax_net.plot(dates, net_u_y, color=config.THEME["net_up"], linewidth=1.4, linestyle="--", label="Upload")
        self.ax_net.set_title("Network Bandwidth (KB/s)", fontsize=10, color=config.THEME["text_primary"], weight="bold", pad=6)
        self.ax_net.set_ylim(bottom=0)
        self.ax_net.legend(loc="upper left", fontsize=8, facecolor=config.THEME["bg_card"], edgecolor=config.THEME["border"], labelcolor=config.THEME["text_primary"])

        # Format X-axis timestamps
        for ax in self.axes:
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
            ax.tick_params(axis="x", labelrotation=25, labelsize=7)

        self.canvas.draw_idle()

    def _handle_export_csv(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"syscore_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            title="Export Historical Telemetry to CSV",
        )
        if not filepath:
            return

        def worker():
            try:
                count = self.db.export_to_csv(filepath, time_range_minutes=self._current_range_minutes)
                self._analytics_queue.put(("export_success", count, filepath))
            except Exception as e:
                self._analytics_queue.put(("export_error", str(e)))

        threading.Thread(target=worker, daemon=True).start()
