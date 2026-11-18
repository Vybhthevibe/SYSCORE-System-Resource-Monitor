"""
SYSCORE — Main Application Controller & Window
Coordinates navigation, UI event loop, background engine queues, and graceful shutdown.
"""
import queue
import time
from typing import Dict

import customtkinter as ctk

import config
from core.database import Database
from core.monitoring_engine import MonitoringEngine
from .sidebar import Sidebar
from .dashboard import DashboardPage
from .process_page import ProcessPage
from .analytics_page import AnalyticsPage
from .system_info_page import SystemInfoPage
from .settings_page import SettingsPage


class SYSCOREApp(ctk.CTk):
    """
    Main Application Window for SYSCORE.
    Implements decoupled inter-thread message processing using queue.Queue
    and Tkinter's event loop (self.after) to avoid GUI freezing.
    """
    def __init__(self, db_path: str = config.DB_PATH, interval: float = config.DEFAULT_SAMPLE_INTERVAL):
        super().__init__()

        # Appearance & Window Configuration
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title(config.APP_WINDOW_TITLE)
        self.geometry("1240x800")
        self.minsize(980, 660)
        self.configure(fg_color=config.THEME["bg_main"])

        # Core Backend Initialization
        self.db = Database(db_path)
        self.engine = MonitoringEngine(self.db, sample_interval=interval)

        # Active page tracking
        self._current_page_name = "dashboard"
        self._pages: Dict[str, ctk.CTkFrame] = {}
        self._last_process_tick = time.time()

        # Build Main Layout
        self._build_layout()

        # Intercept window close for safe worker thread shutdown
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start background monitoring daemon
        self.engine.start()

        # Start periodic GUI queue consumer loop
        self.after(100, self._process_queues)

    def _build_layout(self):
        # 1. Persistent Left Navigation Sidebar
        self.sidebar = Sidebar(self, on_navigate=self.show_page)
        self.sidebar.pack(side="left", fill="y")

        # 2. Main Content Container
        self.content_container = ctk.CTkFrame(self, fg_color=config.THEME["bg_main"], corner_radius=0)
        self.content_container.pack(side="right", fill="both", expand=True)

        # Instantiate View Pages
        self._pages["dashboard"] = DashboardPage(
            self.content_container,
            on_change_interval=self._on_interval_changed,
        )
        self._pages["processes"] = ProcessPage(self.content_container)
        self._pages["analytics"] = AnalyticsPage(self.content_container, db=self.db)
        self._pages["system_info"] = SystemInfoPage(self.content_container)
        self._pages["settings"] = SettingsPage(self.content_container, engine=self.engine, db=self.db)

        # Display initial page
        self.show_page("dashboard")

    def show_page(self, page_name: str):
        """Switch currently visible page in content container."""
        if page_name not in self._pages:
            return

        # Hide all pages
        for name, page in self._pages.items():
            page.pack_forget()

        # Show target page
        target = self._pages[page_name]
        target.pack(fill="both", expand=True)
        self._current_page_name = page_name

        # If switching to analytics, trigger fresh query
        if page_name == "analytics":
            self._pages["analytics"].load_analytics()
        elif page_name == "processes":
            self._pages["processes"].refresh_processes()

    def _on_interval_changed(self, new_interval: float):
        self.engine.set_interval(new_interval)
        self.sidebar.update_engine_status(
            is_running=not self.engine.is_paused,
            interval=new_interval,
            logging_enabled=self.engine.is_logging_enabled,
        )

    def _process_queues(self):
        """
        Periodically runs on the main GUI thread to safely consume data
        delivered by the background monitoring worker thread via thread-safe Queue.
        Avoids cross-thread GUI mutations.
        """
        # Drain all available telemetry samples up to the freshest
        latest_sample = None
        while True:
            try:
                sample = self.engine.data_queue.get_nowait()
                latest_sample = sample
            except queue.Empty:
                break

        if latest_sample:
            # Deliver to dashboard
            dashboard: DashboardPage = self._pages.get("dashboard")
            if dashboard:
                dashboard.update_telemetry(latest_sample)

            # Update sidebar engine status
            self.sidebar.update_engine_status(
                is_running=not self.engine.is_paused,
                interval=self.engine.sample_interval,
                logging_enabled=self.engine.is_logging_enabled,
            )

        # Drain any alerts
        while True:
            try:
                alert = self.engine.alert_queue.get_nowait()
                print(f"[Threshold Alert Fired]: {alert.message}")
            except queue.Empty:
                break

        # If currently on process page, perform periodic tick
        now = time.time()
        if self._current_page_name == "processes" and (now - self._last_process_tick) >= config.PROCESS_REFRESH_INTERVAL:
            self._last_process_tick = now
            proc_page: ProcessPage = self._pages.get("processes")
            if proc_page:
                proc_page.on_tick()

        # Reschedule next consumer tick
        self.after(100, self._process_queues)

    def on_closing(self):
        """
        Graceful shutdown sequence:
        1. Signals background monitoring thread to stop and joins it.
        2. Closes open window and resources.
        """
        print("[SYSCORE] Shutting down monitoring workers...")
        self.engine.stop(timeout=1.5)
        print("[SYSCORE] Engine stopped cleanly. Goodbye.")
        self.destroy()
