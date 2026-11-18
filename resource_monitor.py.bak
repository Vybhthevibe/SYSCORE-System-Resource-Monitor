#!/usr/bin/env python3
"""
System Resource Monitor  (OS End-Sem Project 3)

Shows current available / utilised CPU, Memory, Disk I/O and Network bandwidth,
logs every sample to a CSV file, and can draw utilisation graphs both live and
from the logged history.

Install:   pip install psutil matplotlib        (tkinter ships with Python)

Usage:
    python resource_monitor.py              # live GUI with graphs + logging
    python resource_monitor.py --cli        # text-only monitor, still logs
    python resource_monitor.py --history    # open graphs of logged history
    python resource_monitor.py --interval 2 --log mylog.csv
"""
import argparse
import csv
import os
import time
from collections import deque
from datetime import datetime, timedelta

import psutil

FIELDS = ["timestamp", "cpu_percent", "mem_percent", "mem_used_mb",
          "mem_available_mb", "swap_percent", "disk_usage_percent",
          "disk_read_kbs", "disk_write_kbs", "net_up_kbs", "net_down_kbs"]


# --------------------------------------------------------------------------
# Sampling: reads the OS counters and turns cumulative counters into rates
# --------------------------------------------------------------------------
class Sampler:
    def __init__(self):
        self.t = time.time()
        self.disk = psutil.disk_io_counters()
        self.net = psutil.net_io_counters()
        psutil.cpu_percent(None)  # prime the CPU counter
        self.root = os.path.abspath(os.sep)

    def sample(self):
        now = time.time()
        dt = max(now - self.t, 1e-6)
        disk, net = psutil.disk_io_counters(), psutil.net_io_counters()
        mem, swap = psutil.virtual_memory(), psutil.swap_memory()

        dr = dw = 0.0
        if disk and self.disk:
            dr = (disk.read_bytes - self.disk.read_bytes) / 1024 / dt
            dw = (disk.write_bytes - self.disk.write_bytes) / 1024 / dt
        up = (net.bytes_sent - self.net.bytes_sent) / 1024 / dt
        down = (net.bytes_recv - self.net.bytes_recv) / 1024 / dt
        self.t, self.disk, self.net = now, disk, net

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cpu_percent": psutil.cpu_percent(None),
            "mem_percent": mem.percent,
            "mem_used_mb": round(mem.used / 2**20, 1),
            "mem_available_mb": round(mem.available / 2**20, 1),
            "swap_percent": swap.percent,
            "disk_usage_percent": psutil.disk_usage(self.root).percent,
            "disk_read_kbs": round(dr, 2),
            "disk_write_kbs": round(dw, 2),
            "net_up_kbs": round(up, 2),
            "net_down_kbs": round(down, 2),
        }


# --------------------------------------------------------------------------
# Logging (CSV) and reading the history back
# --------------------------------------------------------------------------
class Logger:
    def __init__(self, path):
        self.path = path
        self.enabled = True
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            with open(path, "w", newline="") as f:
                csv.DictWriter(f, FIELDS).writeheader()

    def write(self, row):
        if self.enabled:
            with open(self.path, "a", newline="") as f:
                csv.DictWriter(f, FIELDS).writerow(row)


def read_log(path, since_minutes=None):
    rows = []
    if not os.path.exists(path):
        return rows
    cutoff = datetime.now() - timedelta(minutes=since_minutes) if since_minutes else None
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            try:
                ts = datetime.strptime(r["timestamp"], "%Y-%m-%d %H:%M:%S")
                if cutoff and ts < cutoff:
                    continue
                rows.append({"timestamp": ts, **{k: float(r[k]) for k in FIELDS[1:]}})
            except (ValueError, KeyError, TypeError):
                continue  # skip corrupted lines
    return rows


# --------------------------------------------------------------------------
# Graph drawing (shared by the live view and the history view)
# --------------------------------------------------------------------------
def draw_graphs(axes, x, rows, live=False):
    col = lambda k: [r[k] for r in rows]
    ax_cpu, ax_mem, ax_disk, ax_net = axes
    for ax in axes:
        ax.clear()
        ax.grid(True, alpha=0.3)

    ax_cpu.plot(x, col("cpu_percent"), color="tab:red")
    ax_cpu.set_title("CPU utilisation (%)", fontsize=9)
    ax_cpu.set_ylim(0, 100)

    ax_mem.plot(x, col("mem_percent"), color="tab:blue", label="RAM")
    ax_mem.plot(x, col("swap_percent"), color="tab:orange", label="Swap")
    ax_mem.set_title("Memory utilisation (%)", fontsize=9)
    ax_mem.set_ylim(0, 100)
    ax_mem.legend(loc="upper left", fontsize=7)

    ax_disk.plot(x, col("disk_read_kbs"), label="Read", color="tab:green")
    ax_disk.plot(x, col("disk_write_kbs"), label="Write", color="tab:purple")
    ax_disk.set_title("Disk I/O (KB/s)", fontsize=9)
    ax_disk.legend(loc="upper left", fontsize=7)

    ax_net.plot(x, col("net_down_kbs"), label="Download", color="tab:cyan")
    ax_net.plot(x, col("net_up_kbs"), label="Upload", color="tab:brown")
    ax_net.set_title("Network bandwidth (KB/s)", fontsize=9)
    ax_net.legend(loc="upper left", fontsize=7)

    for ax in (ax_disk, ax_net):
        ax.set_ylim(bottom=0)
    if live:
        ax_disk.set_xlabel("seconds ago", fontsize=8)
        ax_net.set_xlabel("seconds ago", fontsize=8)
    else:
        for ax in axes:
            ax.tick_params(axis="x", labelrotation=30, labelsize=7)


# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------
def build_gui(interval, logger):
    import tkinter as tk
    from tkinter import ttk
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    root = tk.Tk()
    root.title("System Resource Monitor")
    sampler = Sampler()
    window = deque(maxlen=60)

    status = tk.StringVar()
    ttk.Label(root, textvariable=status, font=("Consolas", 10), justify="left").pack(
        anchor="w", padx=8, pady=4)

    fig = Figure(figsize=(9, 6), tight_layout=True)
    axes = fig.subplots(2, 2).flatten()
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(fill="both", expand=True)

    bar = ttk.Frame(root)
    bar.pack(fill="x", padx=8, pady=4)
    log_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(bar, text="Log to " + logger.path, variable=log_var,
                    command=lambda: setattr(logger, "enabled", log_var.get())).pack(side="left")
    ttk.Button(bar, text="View history graph",
               command=lambda: open_history(root, logger.path)).pack(side="right")

    def tick():
        s = sampler.sample()
        window.append(s)
        logger.write(s)
        status.set(
            f"CPU: {s['cpu_percent']:5.1f}%   "
            f"RAM: {s['mem_percent']:5.1f}%  (used {s['mem_used_mb']:.0f} MB, "
            f"available {s['mem_available_mb']:.0f} MB)\n"
            f"Disk usage: {s['disk_usage_percent']:.1f}%   "
            f"Disk R/W: {s['disk_read_kbs']:.0f}/{s['disk_write_kbs']:.0f} KB/s   "
            f"Net down/up: {s['net_down_kbs']:.0f}/{s['net_up_kbs']:.0f} KB/s")
        n = len(window)
        x = [-(n - 1 - i) * interval for i in range(n)]
        draw_graphs(axes, x, list(window), live=True)
        canvas.draw_idle()
        root.after(int(interval * 1000), tick)

    tick()
    root.mainloop()


def open_history(parent, path):
    import tkinter as tk
    from tkinter import ttk
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    top = tk.Toplevel(parent) if parent else tk.Tk()
    top.title("Historical resource utilisation")
    fig = Figure(figsize=(10, 6), tight_layout=True)
    axes = fig.subplots(2, 2).flatten()
    canvas = FigureCanvasTkAgg(fig, master=top)

    ranges = {"Last 5 minutes": 5, "Last hour": 60, "Last 24 hours": 1440, "All data": None}
    choice = tk.StringVar(value="All data")

    def refresh(*_):
        rows = read_log(path, ranges[choice.get()])
        if not rows:
            for ax in axes:
                ax.clear()
            axes[0].set_title("No logged data in this range", fontsize=9)
        else:
            draw_graphs(axes, [r["timestamp"] for r in rows], rows)
        canvas.draw_idle()

    top_bar = ttk.Frame(top)
    top_bar.pack(fill="x", padx=8, pady=4)
    ttk.Label(top_bar, text="Range:").pack(side="left")
    box = ttk.Combobox(top_bar, textvariable=choice, values=list(ranges), state="readonly")
    box.pack(side="left", padx=4)
    box.bind("<<ComboboxSelected>>", refresh)
    ttk.Button(top_bar, text="Reload", command=refresh).pack(side="left")
    canvas.get_tk_widget().pack(fill="both", expand=True)
    refresh()
    if not parent:
        top.mainloop()


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def run_cli(interval, logger):
    sampler = Sampler()
    print(f"Logging to {logger.path}. Press Ctrl+C to stop.\n")
    print(f"{'time':19} {'CPU%':>6} {'RAM%':>6} {'avail MB':>9} "
          f"{'diskR KB/s':>11} {'diskW KB/s':>11} {'down KB/s':>10} {'up KB/s':>9}")
    try:
        while True:
            time.sleep(interval)
            s = sampler.sample()
            logger.write(s)
            print(f"{s['timestamp']:19} {s['cpu_percent']:6.1f} {s['mem_percent']:6.1f} "
                  f"{s['mem_available_mb']:9.0f} {s['disk_read_kbs']:11.1f} "
                  f"{s['disk_write_kbs']:11.1f} {s['net_down_kbs']:10.1f} {s['net_up_kbs']:9.1f}")
    except KeyboardInterrupt:
        print("\nStopped.")


def main():
    p = argparse.ArgumentParser(description="System Resource Monitor")
    p.add_argument("--interval", type=float, default=1.0, help="sampling interval (s)")
    p.add_argument("--log", default="resource_log.csv", help="CSV log file")
    p.add_argument("--cli", action="store_true", help="text mode, no GUI")
    p.add_argument("--history", action="store_true", help="show graphs of logged history")
    a = p.parse_args()

    if a.history:
        open_history(None, a.log)
    elif a.cli:
        run_cli(a.interval, Logger(a.log))
    else:
        build_gui(a.interval, Logger(a.log))


if __name__ == "__main__":
    main()
