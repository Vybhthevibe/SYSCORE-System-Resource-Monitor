"""
SYSCORE — Module E: Settings & Resource Management
Sampling configuration, threshold alert sliders, data retention pruning, and exports.
"""
import os
import queue
import threading
from tkinter import filedialog
from typing import Callable, Optional

import customtkinter as ctk

import config
from core.database import Database
from core.monitoring_engine import MonitoringEngine
from utils.helpers import format_bytes


class SettingsPage(ctk.CTkFrame):
    """
    Settings and management interface for adjusting monitoring rates,
    threshold alerts, database retention, and storage exports.
    Uses queue.Queue for safe inter-thread notifications.
    """
    def __init__(self, master, engine: MonitoringEngine, db: Database, **kwargs):
        super().__init__(master, fg_color=config.THEME["bg_main"], corner_radius=0, **kwargs)
        self.engine = engine
        self.db = db
        self._prune_queue = queue.Queue()

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=16)

        # 1. Header
        self._build_header()

        # 2. Engine Sampling Controls
        self._build_sampling_card()

        # 3. Alert Thresholds Card
        self._build_thresholds_card()

        # 4. Storage & Retention Card
        self._build_storage_card()

        # Start queue poller on main thread
        self.after(50, self._poll_prune_queue)

    def _build_header(self):
        head = ctk.CTkFrame(self.scroll, fg_color="transparent")
        head.pack(fill="x", pady=(4, 16))

        title = ctk.CTkLabel(
            head,
            text="Settings & Alert Management",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=config.THEME["text_primary"],
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            head,
            text="Configure hardware sampling frequency, warning thresholds, and SQLite retention.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=config.THEME["text_muted"],
        )
        subtitle.pack(anchor="w", pady=(2, 0))

    def _build_sampling_card(self):
        card = self._create_card("MONITORING ENGINE CONFIGURATION", config.THEME["cpu"])

        # Sampling Interval Slider
        row1 = ctk.CTkFrame(card, fg_color=config.THEME["bg_card_inner"], corner_radius=6)
        row1.pack(fill="x", padx=16, pady=6)

        lbl1 = ctk.CTkLabel(
            row1,
            text="Sampling Refresh Interval",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=config.THEME["text_primary"],
            width=220,
            anchor="w",
        )
        lbl1.pack(side="left", padx=14, pady=12)

        self.interval_slider = ctk.CTkSlider(
            row1,
            from_=0.5,
            to=5.0,
            number_of_steps=9,
            width=220,
            command=self._on_interval_slider,
        )
        self.interval_slider.set(self.engine.sample_interval)
        self.interval_slider.pack(side="left", padx=12)

        self.interval_val_lbl = ctk.CTkLabel(
            row1,
            text=f"{self.engine.sample_interval:.1f} seconds",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=config.THEME["cpu"],
            width=90,
            anchor="w",
        )
        self.interval_val_lbl.pack(side="left", padx=8)

        # SQLite Logging Toggle
        row2 = ctk.CTkFrame(card, fg_color=config.THEME["bg_card_inner"], corner_radius=6)
        row2.pack(fill="x", padx=16, pady=6)

        lbl2 = ctk.CTkLabel(
            row2,
            text="Persistent SQLite History Logging",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=config.THEME["text_primary"],
            width=220,
            anchor="w",
        )
        lbl2.pack(side="left", padx=14, pady=12)

        self.log_var = ctk.BooleanVar(value=self.engine.is_logging_enabled)
        self.log_switch = ctk.CTkSwitch(
            row2,
            text="Enabled" if self.log_var.get() else "Disabled",
            variable=self.log_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=config.THEME["text_secondary"],
            fg_color=config.THEME["border"],
            progress_color=config.THEME["btn_primary"],
            command=self._on_toggle_logging,
        )
        self.log_switch.pack(side="left", padx=12)

        # Padding
        ctk.CTkFrame(card, height=6, fg_color="transparent").pack()

    def _build_thresholds_card(self):
        card = self._create_card("RESOURCE WARNING THRESHOLDS", config.THEME["swap"])

        # CPU Threshold
        self.cpu_thresh_lbl, self.cpu_slider = self._add_threshold_row(
            card=card,
            label="CPU Alert Threshold",
            initial_val=self.engine.alert_manager.cpu_threshold,
            color=config.THEME["cpu"],
            on_change=lambda val: self._update_threshold("cpu", val),
        )

        # RAM Threshold
        self.ram_thresh_lbl, self.ram_slider = self._add_threshold_row(
            card=card,
            label="RAM Alert Threshold",
            initial_val=self.engine.alert_manager.ram_threshold,
            color=config.THEME["ram"],
            on_change=lambda val: self._update_threshold("ram", val),
        )

        # Disk Threshold
        self.disk_thresh_lbl, self.disk_slider = self._add_threshold_row(
            card=card,
            label="Disk Alert Threshold",
            initial_val=self.engine.alert_manager.disk_threshold,
            color=config.THEME["disk"],
            on_change=lambda val: self._update_threshold("disk", val),
        )

        # Padding
        ctk.CTkFrame(card, height=6, fg_color="transparent").pack()

    def _add_threshold_row(self, card, label: str, initial_val: float, color: str, on_change: Callable):
        row = ctk.CTkFrame(card, fg_color=config.THEME["bg_card_inner"], corner_radius=6)
        row.pack(fill="x", padx=16, pady=4)

        lbl = ctk.CTkLabel(
            row,
            text=label,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=config.THEME["text_primary"],
            width=220,
            anchor="w",
        )
        lbl.pack(side="left", padx=14, pady=10)

        slider = ctk.CTkSlider(
            row,
            from_=50.0,
            to=98.0,
            number_of_steps=48,
            width=220,
            command=on_change,
        )
        slider.set(initial_val)
        slider.pack(side="left", padx=12)

        val_lbl = ctk.CTkLabel(
            row,
            text=f"{initial_val:.0f}%",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=color,
            width=60,
            anchor="w",
        )
        val_lbl.pack(side="left", padx=8)

        return val_lbl, slider

    def _update_threshold(self, metric: str, val: float):
        rounded = round(val)
        if metric == "cpu":
            self.engine.alert_manager.cpu_threshold = float(rounded)
            self.cpu_thresh_lbl.configure(text=f"{rounded}%")
        elif metric == "ram":
            self.engine.alert_manager.ram_threshold = float(rounded)
            self.ram_thresh_lbl.configure(text=f"{rounded}%")
        elif metric == "disk":
            self.engine.alert_manager.disk_threshold = float(rounded)
            self.disk_thresh_lbl.configure(text=f"{rounded}%")

    def _build_storage_card(self):
        card = self._create_card("DATABASE STORAGE & RETENTION MANAGEMENT", config.THEME["ram"])

        # Database File Stats
        row1 = ctk.CTkFrame(card, fg_color=config.THEME["bg_card_inner"], corner_radius=6)
        row1.pack(fill="x", padx=16, pady=6)

        db_size = format_bytes(os.path.getsize(self.db.db_path)) if os.path.exists(self.db.db_path) else "0 B"
        record_count = self.db.get_record_count()

        self.db_status_lbl = ctk.CTkLabel(
            row1,
            text=f"SQLite Database: {os.path.basename(self.db.db_path)}  |  Size: {db_size}  |  Records: {record_count}",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=config.THEME["text_primary"],
            anchor="w",
        )
        self.db_status_lbl.pack(side="left", padx=14, pady=12)

        # Retention Prune Controls
        row2 = ctk.CTkFrame(card, fg_color=config.THEME["bg_card_inner"], corner_radius=6)
        row2.pack(fill="x", padx=16, pady=6)

        lbl2 = ctk.CTkLabel(
            row2,
            text="Data Retention Policy",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=config.THEME["text_primary"],
            width=220,
            anchor="w",
        )
        lbl2.pack(side="left", padx=14, pady=12)

        self.retention_menu = ctk.CTkOptionMenu(
            row2,
            values=["1 Day", "7 Days", "30 Days", "Keep All"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=config.THEME["bg_card"],
            button_color=config.THEME["border"],
            text_color=config.THEME["text_primary"],
            width=120,
        )
        self.retention_menu.set("7 Days")
        self.retention_menu.pack(side="left", padx=12)

        btn_prune = ctk.CTkButton(
            row2,
            text="🧹  Prune Old Records",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=config.THEME["btn_secondary"],
            hover_color=config.THEME["btn_secondary_hover"],
            height=32,
            command=self._handle_prune,
        )
        btn_prune.pack(side="left", padx=8)

        # Padding
        ctk.CTkFrame(card, height=6, fg_color="transparent").pack()

    def _create_card(self, title: str, accent_color: str) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            self.scroll,
            fg_color=config.THEME["bg_card"],
            border_color=config.THEME["border"],
            border_width=1,
            corner_radius=10,
        )
        card.pack(fill="x", pady=(0, 14))

        head = ctk.CTkFrame(card, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(12, 8))

        pill = ctk.CTkFrame(head, width=8, height=8, corner_radius=4, fg_color=accent_color)
        pill.pack(side="left", padx=(0, 8))

        lbl = ctk.CTkLabel(
            head,
            text=title,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=config.THEME["text_secondary"],
        )
        lbl.pack(side="left")
        return card

    def _on_interval_slider(self, val: float):
        rounded = round(val, 1)
        self.interval_val_lbl.configure(text=f"{rounded:.1f} seconds")
        self.engine.set_interval(rounded)

    def _on_toggle_logging(self):
        enabled = self.log_var.get()
        self.log_switch.configure(text="Enabled" if enabled else "Disabled")
        self.engine.set_logging(enabled)

    def _handle_prune(self):
        choice = self.retention_menu.get()
        days_map = {"1 Day": 1, "7 Days": 7, "30 Days": 30, "Keep All": 0}
        days = days_map.get(choice, 7)

        def worker():
            try:
                deleted = self.db.cleanup_old_records(retention_days=days)
                db_size = format_bytes(os.path.getsize(self.db.db_path)) if os.path.exists(self.db.db_path) else "0 B"
                record_count = self.db.get_record_count()
                self._prune_queue.put(("success", deleted, record_count, db_size))
            except Exception as e:
                self._prune_queue.put(("error", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_prune_queue(self):
        try:
            while not self._prune_queue.empty():
                item = self._prune_queue.get_nowait()
                if item[0] == "success":
                    _, deleted, record_count, db_size = item
                    msg = f"Pruned {deleted} records. Remaining: {record_count} ({db_size})"
                    self.db_status_lbl.configure(text=msg, text_color=config.THEME["status_ok"])
                elif item[0] == "error":
                    self.db_status_lbl.configure(text=f"Prune error: {item[1]}", text_color=config.THEME["status_error"])
        except Exception:
            pass
        finally:
            self.after(50, self._poll_prune_queue)
