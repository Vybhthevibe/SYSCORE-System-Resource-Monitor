"""
SYSCORE — Persistent Left Navigation Sidebar
Navigation buttons, brand identity, and engine status indicators.
"""
from typing import Callable, Dict
import customtkinter as ctk
import config


class Sidebar(ctk.CTkFrame):
    """
    Persistent left sidebar providing rapid navigation between application modules,
    branding, and real-time engine activity indicators.
    """
    def __init__(self, master, on_navigate: Callable[[str], None], **kwargs):
        super().__init__(
            master,
            width=230,
            fg_color=config.THEME["bg_sidebar"],
            border_color=config.THEME["border"],
            border_width=1,
            corner_radius=0,
            **kwargs
        )
        self.pack_propagate(False)
        self.on_navigate = on_navigate
        self._buttons: Dict[str, ctk.CTkButton] = {}
        self._current_page = "dashboard"

        # 1. Branding Header
        brand_frame = ctk.CTkFrame(self, fg_color="transparent")
        brand_frame.pack(fill="x", padx=16, pady=(20, 24))

        # Brand icon badge
        icon_box = ctk.CTkFrame(
            brand_frame,
            width=36,
            height=36,
            corner_radius=8,
            fg_color="#1f6feb",
        )
        icon_box.pack(side="left")
        icon_box.pack_propagate(False)

        icon_lbl = ctk.CTkLabel(
            icon_box,
            text="⚡",
            font=ctk.CTkFont(size=18),
            text_color="#ffffff",
        )
        icon_lbl.pack(expand=True)

        title_box = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_box.pack(side="left", padx=(10, 0))

        title_lbl = ctk.CTkLabel(
            title_box,
            text=config.APP_NAME,
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=config.THEME["text_primary"],
        )
        title_lbl.pack(anchor="w")

        sub_lbl = ctk.CTkLabel(
            title_box,
            text=f"v{config.APP_VERSION} • OS Edition",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=config.THEME["text_muted"],
        )
        sub_lbl.pack(anchor="w")

        # Divider
        div = ctk.CTkFrame(self, height=1, fg_color=config.THEME["border"])
        div.pack(fill="x", padx=16, pady=(0, 16))

        # 2. Navigation Items
        nav_items = [
            ("dashboard", "📊  Dashboard"),
            ("processes", "⚙️  Process Monitor"),
            ("analytics", "📈  Resource Analytics"),
            ("system_info", "💻  System Information"),
            ("settings", "🛠️  Settings & Alerts"),
        ]

        self.nav_container = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_container.pack(fill="x", padx=12, expand=True, anchor="n")

        for key, text in nav_items:
            btn = ctk.CTkButton(
                self.nav_container,
                text=text,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                anchor="w",
                height=42,
                corner_radius=8,
                fg_color="transparent",
                text_color=config.THEME["text_secondary"],
                hover_color=config.THEME["bg_card_hover"],
                command=lambda k=key: self._handle_click(k),
            )
            btn.pack(fill="x", pady=3)
            self._buttons[key] = btn

        # Set default active
        self._highlight("dashboard")

        # 3. Bottom Status / Health Card
        self.status_card = ctk.CTkFrame(
            self,
            fg_color=config.THEME["bg_card_inner"],
            border_color=config.THEME["border"],
            border_width=1,
            corner_radius=8,
        )
        self.status_card.pack(fill="x", padx=12, pady=16, side="bottom")

        status_top = ctk.CTkFrame(self.status_card, fg_color="transparent")
        status_top.pack(fill="x", padx=10, pady=(10, 4))

        self.pulse_dot = ctk.CTkFrame(
            status_top,
            width=8,
            height=8,
            corner_radius=4,
            fg_color=config.THEME["status_ok"],
        )
        self.pulse_dot.pack(side="left")

        self.status_text = ctk.CTkLabel(
            status_top,
            text="ENGINE ACTIVE",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=config.THEME["text_primary"],
        )
        self.status_text.pack(side="left", padx=(8, 0))

        self.rate_lbl = ctk.CTkLabel(
            self.status_card,
            text="Sampling: 1.0s • SQLite: ON",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=config.THEME["text_muted"],
            anchor="w",
        )
        self.rate_lbl.pack(fill="x", padx=10, pady=(0, 10))

    def _handle_click(self, page_key: str):
        self._highlight(page_key)
        self.on_navigate(page_key)

    def _highlight(self, page_key: str):
        self._current_page = page_key
        for key, btn in self._buttons.items():
            if key == page_key:
                btn.configure(
                    fg_color=config.THEME["btn_primary"],
                    text_color="#ffffff",
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=config.THEME["text_secondary"],
                )

    def update_engine_status(self, is_running: bool, interval: float, logging_enabled: bool):
        """Update live status panel in sidebar."""
        dot_color = config.THEME["status_ok"] if is_running else config.THEME["swap"]
        text_str = "ENGINE ACTIVE" if is_running else "MONITOR PAUSED"
        self.pulse_dot.configure(fg_color=dot_color)
        self.status_text.configure(text=text_str)

        log_str = "ON" if logging_enabled else "OFF"
        self.rate_lbl.configure(text=f"Sampling: {interval:.1f}s • SQLite: {log_str}")
