"""
SYSCORE — Module A: System Overview Dashboard
Metric cards, live 4-pane Matplotlib performance charts, uptime, and sampling controls.
"""
from collections import deque
from datetime import datetime
import time
from typing import Callable, Optional

import customtkinter as ctk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import config
from .components import MetricCard, AlertBanner
from utils.helpers import format_bytes, format_rate, format_percent, format_uptime


class DashboardPage(ctk.CTkFrame):
    """
    Main overview dashboard displaying real-time telemetry cards and
    live Matplotlib time-series graphs for CPU, Memory, Disk I/O, and Network.
    """
    def __init__(self, master, on_change_interval: Optional[Callable[[float], None]] = None, **kwargs):
        super().__init__(master, fg_color=config.THEME["bg_main"], corner_radius=0, **kwargs)
        self.on_change_interval = on_change_interval
        self.history_window = deque(maxlen=config.LIVE_GRAPH_POINTS)
        self._current_interval = config.DEFAULT_SAMPLE_INTERVAL

        # Main scrollable canvas container to ensure responsive layout on all screen sizes
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=16)

        # 1. Alert Banner
        self.alert_banner = AlertBanner(self.scroll)

        # 2. Header & Controls Bar
        self._build_header()

        # 3. Telemetry Metric Cards
        self._build_cards()

        # 4. Live Charts Area
        self._build_charts()

    def _build_header(self):
        head = ctk.CTkFrame(self.scroll, fg_color="transparent")
        head.pack(fill="x", pady=(8, 12))

        # Title & Subtitle
        tbox = ctk.CTkFrame(head, fg_color="transparent")
        tbox.pack(side="left")

        title = ctk.CTkLabel(
            tbox,
            text="System Overview Dashboard",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=config.THEME["text_primary"],
        )
        title.pack(anchor="w")

        self.uptime_label = ctk.CTkLabel(
            tbox,
            text="System Uptime: -- | Boot Time: --",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=config.THEME["text_muted"],
        )
        self.uptime_label.pack(anchor="w", pady=(2, 0))

        # Control Panel (Right)
        cbox = ctk.CTkFrame(head, fg_color="transparent")
        cbox.pack(side="right")

        int_lbl = ctk.CTkLabel(
            cbox,
            text="Refresh Rate:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=config.THEME["text_secondary"],
        )
        int_lbl.pack(side="left", padx=(0, 6))

        self.interval_var = ctk.StringVar(value="1.0s")
        self.interval_menu = ctk.CTkOptionMenu(
            cbox,
            values=["0.5s", "1.0s", "2.0s", "5.0s"],
            variable=self.interval_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=config.THEME["btn_secondary"],
            button_color=config.THEME["btn_secondary_hover"],
            text_color=config.THEME["text_primary"],
            width=90,
            command=self._on_interval_selected,
        )
        self.interval_menu.pack(side="left")

    def _on_interval_selected(self, val_str: str):
        try:
            val = float(val_str.replace("s", ""))
            self._current_interval = val
            if self.on_change_interval:
                self.on_change_interval(val)
        except Exception:
            pass

    def _build_cards(self):
        """Construct top row metric cards."""
        card_row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        card_row.pack(fill="x", pady=(0, 14))
        card_row.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="card")

        # 1. CPU Card
        self.cpu_card = MetricCard(
            card_row,
            title="CPU Utilization",
            initial_value="0.0%",
            subtitle="Cores: -- | Freq: --",
            accent_color=config.THEME["cpu"],
            show_progress=True,
        )
        self.cpu_card.grid(row=0, column=0, padx=6, pady=4, sticky="nsew")

        # 2. RAM Card
        self.ram_card = MetricCard(
            card_row,
            title="Physical Memory",
            initial_value="0.0%",
            subtitle="Used: -- | Avail: --",
            accent_color=config.THEME["ram"],
            show_progress=True,
        )
        self.ram_card.grid(row=0, column=1, padx=6, pady=4, sticky="nsew")

        # 3. Disk Usage Card
        self.disk_card = MetricCard(
            card_row,
            title="Storage Usage",
            initial_value="0.0%",
            subtitle="Root: -- / -- GB",
            accent_color=config.THEME["disk"],
            show_progress=True,
        )
        self.disk_card.grid(row=0, column=2, padx=6, pady=4, sticky="nsew")

        # 4. Network / I/O Activity Card
        self.io_card = MetricCard(
            card_row,
            title="I/O & Network",
            initial_value="0 KB/s",
            subtitle="Net: ↓ 0 KB/s | ↑ 0 KB/s",
            accent_color=config.THEME["net_down"],
            show_progress=False,
        )
        self.io_card.grid(row=0, column=3, padx=6, pady=4, sticky="nsew")

    def _build_charts(self):
        """Construct embedded 4-panel Matplotlib performance figure."""
        chart_frame = ctk.CTkFrame(
            self.scroll,
            fg_color=config.THEME["bg_card"],
            border_color=config.THEME["border"],
            border_width=1,
            corner_radius=10,
        )
        chart_frame.pack(fill="both", expand=True, pady=(0, 16))

        # Title bar inside chart container
        chart_head = ctk.CTkFrame(chart_frame, fg_color="transparent")
        chart_head.pack(fill="x", padx=16, pady=(12, 6))

        c_title = ctk.CTkLabel(
            chart_head,
            text="REAL-TIME TELEMETRY CHARTS",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=config.THEME["text_secondary"],
        )
        c_title.pack(side="left")

        legend_hint = ctk.CTkLabel(
            chart_head,
            text="Window: 60 Samples • Auto-scaled",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=config.THEME["text_muted"],
        )
        legend_hint.pack(side="right")

        # Matplotlib Figure with 4 subplots (2x2 grid)
        self.fig = Figure(figsize=(10, 6.2), dpi=100, facecolor=config.THEME["bg_card"])
        self.fig.subplots_adjust(left=0.06, right=0.96, top=0.92, bottom=0.10, hspace=0.36, wspace=0.18)

        self.ax_cpu = self.fig.add_subplot(2, 2, 1)
        self.ax_mem = self.fig.add_subplot(2, 2, 2)
        self.ax_disk = self.fig.add_subplot(2, 2, 3)
        self.ax_net = self.fig.add_subplot(2, 2, 4)
        self.axes = [self.ax_cpu, self.ax_mem, self.ax_disk, self.ax_net]

        for ax in self.axes:
            self._style_axis(ax)

        # Pre-create line objects for high-performance blitting/updates
        self.line_cpu, = self.ax_cpu.plot([], [], color=config.THEME["cpu"], linewidth=1.8, label="CPU %")
        self.ax_cpu.set_title("CPU Utilization (%)", fontsize=10, color=config.THEME["text_primary"], weight="bold", pad=6)
        self.ax_cpu.set_ylim(0, 100)

        self.line_ram, = self.ax_mem.plot([], [], color=config.THEME["ram"], linewidth=1.8, label="RAM %")
        self.line_swap, = self.ax_mem.plot([], [], color=config.THEME["swap"], linewidth=1.4, linestyle="--", label="Swap %")
        self.ax_mem.set_title("Memory Utilization (%)", fontsize=10, color=config.THEME["text_primary"], weight="bold", pad=6)
        self.ax_mem.set_ylim(0, 100)
        self.ax_mem.legend(loc="upper left", fontsize=8, facecolor=config.THEME["bg_card"], edgecolor=config.THEME["border"], labelcolor=config.THEME["text_primary"])

        self.line_disk_read, = self.ax_disk.plot([], [], color=config.THEME["disk"], linewidth=1.6, label="Read")
        self.line_disk_write, = self.ax_disk.plot([], [], color=config.THEME["disk_write"], linewidth=1.6, linestyle="--", label="Write")
        self.ax_disk.set_title("Disk I/O Transfer Rate (KB/s)", fontsize=10, color=config.THEME["text_primary"], weight="bold", pad=6)
        self.ax_disk.set_ylim(bottom=0)
        self.ax_disk.legend(loc="upper left", fontsize=8, facecolor=config.THEME["bg_card"], edgecolor=config.THEME["border"], labelcolor=config.THEME["text_primary"])

        self.line_net_down, = self.ax_net.plot([], [], color=config.THEME["net_down"], linewidth=1.6, label="Down")
        self.line_net_up, = self.ax_net.plot([], [], color=config.THEME["net_up"], linewidth=1.6, linestyle="--", label="Up")
        self.ax_net.set_title("Network Bandwidth (KB/s)", fontsize=10, color=config.THEME["text_primary"], weight="bold", pad=6)
        self.ax_net.set_ylim(bottom=0)
        self.ax_net.legend(loc="upper left", fontsize=8, facecolor=config.THEME["bg_card"], edgecolor=config.THEME["border"], labelcolor=config.THEME["text_primary"])

        # Canvas embedding
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True, padx=12, pady=(0, 14))

    def _style_axis(self, ax):
        ax.set_facecolor(config.THEME["bg_card_inner"])
        ax.tick_params(colors=config.THEME["text_muted"], labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(config.THEME["border"])
        ax.grid(True, linestyle="--", color="#21262d", alpha=0.6)

    def update_telemetry(self, sample: dict):
        """
        Called when a new sample is received from the background monitoring engine.
        Updates metric cards and live rolling Matplotlib charts.
        """
        # 1. Update Alert Banner
        violations = sample.get("active_violations", [])
        self.alert_banner.set_violations(violations)

        # 2. Update Header Info
        uptime_str = format_uptime(sample.get("uptime_seconds", 0))
        boot_str = datetime.fromtimestamp(sample.get("epoch_time", time.time()) - sample.get("uptime_seconds", 0)).strftime("%Y-%m-%d %H:%M")
        self.uptime_label.configure(text=f"System Uptime: {uptime_str}  |  Boot Time: {boot_str}")

        # 3. Update Metric Cards
        # CPU
        cpu_pct = sample.get("cpu_percent", 0.0)
        cores_log = sample.get("cpu_count_logical", 1)
        cores_phy = sample.get("cpu_count_physical", 1)
        freq = sample.get("cpu_freq_mhz")
        freq_str = f"{freq:.0f} MHz" if freq else "--"
        cpu_accent = config.THEME["status_error"] if cpu_pct >= 90 else (config.THEME["swap"] if cpu_pct >= 75 else config.THEME["cpu"])
        self.cpu_card.update_data(
            value=format_percent(cpu_pct),
            subtitle=f"{cores_phy}C/{cores_log}T • {freq_str}",
            progress=cpu_pct,
            accent_color=cpu_accent,
        )

        # RAM
        ram_pct = sample.get("mem_percent", 0.0)
        mem_used = sample.get("mem_used_mb", 0.0)
        mem_avail = sample.get("mem_available_mb", 0.0)
        swap_pct = sample.get("swap_percent", 0.0)
        ram_accent = config.THEME["status_error"] if ram_pct >= 90 else (config.THEME["swap"] if ram_pct >= 75 else config.THEME["ram"])
        self.ram_card.update_data(
            value=format_percent(ram_pct),
            subtitle=f"Used: {format_bytes(mem_used*1024*1024)} | Swap: {swap_pct:.0f}%",
            progress=ram_pct,
            accent_color=ram_accent,
        )

        # Disk
        disk_pct = sample.get("disk_usage_percent", 0.0)
        disk_used = sample.get("disk_used_gb", 0.0)
        disk_tot = sample.get("disk_total_gb", 0.0)
        disk_free = sample.get("disk_free_gb", 0.0)
        disk_accent = config.THEME["status_error"] if disk_pct >= 90 else config.THEME["disk"]
        self.disk_card.update_data(
            value=format_percent(disk_pct),
            subtitle=f"Used: {disk_used:.1f} GB / {disk_tot:.1f} GB ({disk_free:.1f} GB free)",
            progress=disk_pct,
            accent_color=disk_accent,
        )

        # I/O & Network
        dr = sample.get("disk_read_kbs", 0.0)
        dw = sample.get("disk_write_kbs", 0.0)
        down = sample.get("net_down_kbs", 0.0)
        up = sample.get("net_up_kbs", 0.0)
        self.io_card.update_data(
            value=f"↓ {format_rate(down)}",
            subtitle=f"Net ↑ {format_rate(up)} | Disk R/W: {dr:.0f}/{dw:.0f} KB/s",
        )

        # 4. Append to rolling graph history and update charts
        self.history_window.append(sample)
        self._update_charts()

    def _update_charts(self):
        n = len(self.history_window)
        if n == 0:
            return

        x = [-(n - 1 - i) * self._current_interval for i in range(n)]

        cpu_y = [s.get("cpu_percent", 0.0) for s in self.history_window]
        ram_y = [s.get("mem_percent", 0.0) for s in self.history_window]
        swap_y = [s.get("swap_percent", 0.0) for s in self.history_window]
        disk_r_y = [s.get("disk_read_kbs", 0.0) for s in self.history_window]
        disk_w_y = [s.get("disk_write_kbs", 0.0) for s in self.history_window]
        net_down_y = [s.get("net_down_kbs", 0.0) for s in self.history_window]
        net_up_y = [s.get("net_up_kbs", 0.0) for s in self.history_window]

        min_x = min(x) if x and min(x) < 0 else -10.0

        # CPU plot
        self.line_cpu.set_data(x, cpu_y)
        self.ax_cpu.set_xlim(min_x, 0)

        # Memory plot
        self.line_ram.set_data(x, ram_y)
        self.line_swap.set_data(x, swap_y)
        self.ax_mem.set_xlim(min_x, 0)

        # Disk I/O plot
        self.line_disk_read.set_data(x, disk_r_y)
        self.line_disk_write.set_data(x, disk_w_y)
        self.ax_disk.set_xlim(min_x, 0)
        max_disk = max(max(disk_r_y + [100.0]), max(disk_w_y + [100.0])) * 1.15
        self.ax_disk.set_ylim(0, max_disk)

        # Network Bandwidth plot
        self.line_net_down.set_data(x, net_down_y)
        self.line_net_up.set_data(x, net_up_y)
        self.ax_net.set_xlim(min_x, 0)
        max_net = max(max(net_down_y + [100.0]), max(net_up_y + [100.0])) * 1.15
        self.ax_net.set_ylim(0, max_net)

        self.canvas.draw_idle()
