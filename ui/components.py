"""
SYSCORE — Reusable UI Components
Metric cards, progress indicators, alert banners, and modal dialogs.
"""
from typing import Callable, Optional
import customtkinter as ctk
import config


class MetricCard(ctk.CTkFrame):
    """
    Sleek developer-workstation metric card with title, icon, value,
    status accent, and optional progress bar.
    """
    def __init__(
        self,
        master,
        title: str,
        initial_value: str = "--",
        subtitle: str = "",
        accent_color: str = config.THEME["cpu"],
        show_progress: bool = True,
        width: int = 200,
        height: int = 130,
        **kwargs
    ):
        super().__init__(
            master,
            fg_color=config.THEME["bg_card"],
            border_color=config.THEME["border"],
            border_width=1,
            corner_radius=10,
            width=width,
            height=height,
            **kwargs
        )
        self.accent_color = accent_color
        self.show_progress = show_progress

        # Top row: Title and accent pill
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=14, pady=(12, 4))

        self.title_label = ctk.CTkLabel(
            self.top_frame,
            text=title.upper(),
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=config.THEME["text_secondary"],
        )
        self.title_label.pack(side="left")

        self.pill = ctk.CTkFrame(
            self.top_frame,
            width=8,
            height=8,
            corner_radius=4,
            fg_color=self.accent_color,
        )
        self.pill.pack(side="right", padx=(0, 2))

        # Center: Main Value
        self.value_label = ctk.CTkLabel(
            self,
            text=initial_value,
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=config.THEME["text_primary"],
        )
        self.value_label.pack(anchor="w", padx=14, pady=(2, 2))

        # Bottom: Subtitle / breakdown
        self.sub_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=config.THEME["text_muted"],
            anchor="w",
        )
        self.sub_label.pack(anchor="w", padx=14, pady=(0, 6))

        # Optional mini progress bar
        if self.show_progress:
            self.progress_bar = ctk.CTkProgressBar(
                self,
                height=5,
                corner_radius=3,
                fg_color=config.THEME["bg_card_inner"],
                progress_color=self.accent_color,
            )
            self.progress_bar.pack(fill="x", padx=14, pady=(0, 10))
            self.progress_bar.set(0.0)
        else:
            self.progress_bar = None

    def update_data(
        self,
        value: str,
        subtitle: Optional[str] = None,
        progress: Optional[float] = None,
        accent_color: Optional[str] = None,
    ):
        """Update metric card contents."""
        self.value_label.configure(text=value)
        if subtitle is not None:
            self.sub_label.configure(text=subtitle)
        if self.progress_bar and progress is not None:
            clamped = max(0.0, min(1.0, float(progress) / 100.0))
            self.progress_bar.set(clamped)
        if accent_color:
            self.pill.configure(fg_color=accent_color)
            if self.progress_bar:
                self.progress_bar.configure(progress_color=accent_color)


class AlertBanner(ctk.CTkFrame):
    """
    Subtle top alert banner that displays active threshold warnings.
    """
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color="#3a1e1e",
            border_color=config.THEME["status_error"],
            border_width=1,
            corner_radius=8,
            height=36,
            **kwargs
        )
        self.pack_propagate(False)

        self.label = ctk.CTkLabel(
            self,
            text="⚠️ SYSTEM WARNING: Resource usage threshold exceeded!",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#ff7b72",
        )
        self.label.pack(side="left", padx=16, pady=6)

        self.details_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=config.THEME["text_primary"],
        )
        self.details_label.pack(side="left", padx=8, pady=6)

    def set_violations(self, violations: list):
        if violations:
            self.details_label.configure(text=" | ".join(violations))
            self.pack(fill="x", padx=16, pady=(10, 0))
        else:
            self.pack_forget()


class ProcessDetailDialog(ctk.CTkToplevel):
    """
    Modal window presenting deep process inspection attributes.
    """
    def __init__(self, parent, detail: dict):
        super().__init__(parent)
        self.title(f"Process Telemetry — PID {detail.get('pid')}")
        self.geometry("640x520")
        self.resizable(False, False)
        self.configure(fg_color=config.THEME["bg_main"])
        self.grab_set()  # Make modal

        # Header
        head = ctk.CTkFrame(self, fg_color=config.THEME["bg_card"], corner_radius=0, height=65)
        head.pack(fill="x")
        head.pack_propagate(False)

        p_name = detail.get("name", "Unknown")
        pid = detail.get("pid", "Unknown")
        is_prot = detail.get("is_protected", False)

        t_lbl = ctk.CTkLabel(
            head,
            text=f"{p_name} (PID: {pid})",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=config.THEME["text_primary"],
        )
        t_lbl.pack(side="left", padx=20, pady=18)

        if is_prot:
            prot_badge = ctk.CTkLabel(
                head,
                text="SYSTEM PROTECTED",
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                text_color=config.THEME["swap"],
                fg_color="#3a2e12",
                corner_radius=6,
                padx=8,
                pady=2,
            )
            prot_badge.pack(side="right", padx=20, pady=18)

        # Content scroll
        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=14)

        items = [
            ("Process Name", detail.get("name")),
            ("Process ID (PID)", detail.get("pid")),
            ("Parent PID (PPID)", detail.get("ppid")),
            ("Status / State", detail.get("status")),
            ("User / Owner", detail.get("username")),
            ("CPU Utilization", f"{detail.get('cpu_percent')}%"),
            ("Memory RSS (Physical)", f"{detail.get('memory_rss_mb')} MB ({detail.get('memory_percent')}%)"),
            ("Memory VMS (Virtual)", f"{detail.get('memory_vms_mb')} MB"),
            ("Active Threads", detail.get("threads")),
            ("Nice Priority", detail.get("nice")),
            ("Created At", detail.get("create_time")),
            ("Open File Descriptors", detail.get("open_files")),
            ("Network Sockets", detail.get("net_connections")),
            ("Executable Path", detail.get("exe")),
            ("Full Command Line", detail.get("cmdline")),
        ]

        for label, val in items:
            row = ctk.CTkFrame(scroll, fg_color=config.THEME["bg_card"], corner_radius=6)
            row.pack(fill="x", pady=3)

            lbl = ctk.CTkLabel(
                row,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=config.THEME["text_secondary"],
                width=180,
                anchor="w",
            )
            lbl.pack(side="left", padx=12, pady=8)

            val_lbl = ctk.CTkLabel(
                row,
                text=str(val),
                font=ctk.CTkFont(family="Consolas" if "Path" in label or "Command" in label else "Segoe UI", size=11),
                text_color=config.THEME["text_primary"],
                anchor="w",
                justify="left",
                wraplength=380,
            )
            val_lbl.pack(side="left", padx=8, pady=8, fill="x", expand=True)

        # Close button
        btn_close = ctk.CTkButton(
            self,
            text="Close",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=config.THEME["btn_secondary"],
            hover_color=config.THEME["btn_secondary_hover"],
            width=100,
            command=self.destroy,
        )
        btn_close.pack(pady=(4, 14))


class ConfirmTerminateDialog(ctk.CTkToplevel):
    """
    Explicit confirmation dialog before terminating a process.
    Prevents accidental termination.
    """
    def __init__(self, parent, pid: int, proc_name: str, on_confirm: Callable[[int, bool], None]):
        super().__init__(parent)
        self.title("Confirm Process Termination")
        self.geometry("460x240")
        self.resizable(False, False)
        self.configure(fg_color=config.THEME["bg_main"])
        self.grab_set()

        self.pid = pid
        self.on_confirm = on_confirm

        head = ctk.CTkLabel(
            self,
            text="⚠️ Terminate Process?",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=config.THEME["status_error"],
        )
        head.pack(pady=(20, 8))

        msg = (
            f"Are you sure you want to terminate:\n"
            f"'{proc_name}' (PID: {pid})?\n\n"
            f"Terminating an active process may cause unsaved data loss."
        )
        body = ctk.CTkLabel(
            self,
            text=msg,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=config.THEME["text_primary"],
            justify="center",
        )
        body.pack(padx=20, pady=8)

        self.force_var = ctk.BooleanVar(value=False)
        chk = ctk.CTkCheckBox(
            self,
            text="Force kill immediately (SIGKILL)",
            variable=self.force_var,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=config.THEME["text_secondary"],
            fg_color=config.THEME["btn_danger"],
            hover_color=config.THEME["btn_danger_hover"],
        )
        chk.pack(pady=4)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=(12, 16))

        cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            fg_color=config.THEME["btn_secondary"],
            hover_color=config.THEME["btn_secondary_hover"],
            width=110,
            command=self.destroy,
        )
        cancel_btn.pack(side="left", padx=8)

        kill_btn = ctk.CTkButton(
            btn_row,
            text="Terminate",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=config.THEME["btn_danger"],
            hover_color=config.THEME["btn_danger_hover"],
            width=110,
            command=self._do_confirm,
        )
        kill_btn.pack(side="left", padx=8)

    def _do_confirm(self):
        force = self.force_var.get()
        self.destroy()
        self.on_confirm(self.pid, force)
