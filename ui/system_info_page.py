"""
SYSCORE — Module D: System Information & Architecture
Comprehensive OS, kernel, CPU, memory, and filesystem telemetry.
"""
from datetime import datetime
import os
import platform
import sys
import time
from typing import Any, Dict, List

import customtkinter as ctk
import psutil

import config
from utils.helpers import format_bytes, format_uptime


class SystemInfoPage(ctk.CTkFrame):
    """
    Dedicated system information page presenting kernel telemetry,
    hardware architecture, memory hierarchy, and storage filesystems.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=config.THEME["bg_main"], corner_radius=0, **kwargs)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=20, pady=16)

        # 1. Header
        self._build_header()

        # 2. Information Cards
        self._build_cards()

    def _build_header(self):
        head = ctk.CTkFrame(self.scroll, fg_color="transparent")
        head.pack(fill="x", pady=(4, 16))

        title = ctk.CTkLabel(
            head,
            text="System Information & Architecture",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=config.THEME["text_primary"],
        )
        title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            head,
            text="Operating System kernel parameters, processor architecture, and storage mountpoints.",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=config.THEME["text_muted"],
        )
        subtitle.pack(anchor="w", pady=(2, 0))

    def _build_cards(self):
        # 1. Operating System & Kernel Telemetry
        os_info = self._get_os_info()
        self._create_section_card(
            title="OPERATING SYSTEM & KERNEL TELEMETRY",
            accent_color=config.THEME["cpu"],
            items=os_info,
        )

        # 2. CPU & Processor Architecture
        cpu_info = self._get_cpu_info()
        self._create_section_card(
            title="PROCESSOR & CPU ARCHITECTURE",
            accent_color=config.THEME["ram"],
            items=cpu_info,
        )

        # 3. Memory & Virtual Swap Hierarchy
        mem_info = self._get_mem_info()
        self._create_section_card(
            title="MEMORY HIERARCHY & VIRTUAL SWAP",
            accent_color=config.THEME["swap"],
            items=mem_info,
        )

        # 4. Storage Partitions & Filesystem Mounts
        self._build_partitions_card()

        # 5. System Boot & Runtime
        boot_info = self._get_boot_info()
        self._create_section_card(
            title="SYSTEM BOOT & RUNTIME TELEMETRY",
            accent_color=config.THEME["net_down"],
            items=boot_info,
        )

    def _create_section_card(self, title: str, accent_color: str, items: List[tuple]):
        card = ctk.CTkFrame(
            self.scroll,
            fg_color=config.THEME["bg_card"],
            border_color=config.THEME["border"],
            border_width=1,
            corner_radius=10,
        )
        card.pack(fill="x", pady=(0, 14))

        # Title bar
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

        # Two-column grid of key-value attributes
        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 12))
        grid.grid_columnconfigure((0, 1), weight=1)

        for i, (k, v) in enumerate(items):
            row_idx = i // 2
            col_idx = i % 2

            item_frame = ctk.CTkFrame(grid, fg_color=config.THEME["bg_card_inner"], corner_radius=6)
            item_frame.grid(row=row_idx, column=col_idx, padx=4, pady=4, sticky="nsew")

            k_lbl = ctk.CTkLabel(
                item_frame,
                text=k,
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                text_color=config.THEME["text_secondary"],
                width=160,
                anchor="w",
            )
            k_lbl.pack(side="left", padx=12, pady=8)

            v_lbl = ctk.CTkLabel(
                item_frame,
                text=str(v),
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=config.THEME["text_primary"],
                anchor="w",
            )
            v_lbl.pack(side="left", padx=8, pady=8, fill="x", expand=True)

    def _build_partitions_card(self):
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

        pill = ctk.CTkFrame(head, width=8, height=8, corner_radius=4, fg_color=config.THEME["disk"])
        pill.pack(side="left", padx=(0, 8))

        lbl = ctk.CTkLabel(
            head,
            text="STORAGE FILESYSTEMS & PARTITION MOUNTPOINTS",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=config.THEME["text_secondary"],
        )
        lbl.pack(side="left")

        # Table header
        thead = ctk.CTkFrame(card, fg_color=config.THEME["bg_card_inner"], corner_radius=6, height=30)
        thead.pack(fill="x", padx=16, pady=(0, 4))
        thead.pack_propagate(False)

        cols = [("Device", 140), ("Mountpoint", 160), ("FS Type", 80), ("Total", 90), ("Used", 90), ("Free", 90), ("Usage", 80)]
        for name, width in cols:
            clbl = ctk.CTkLabel(thead, text=name, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=config.THEME["text_secondary"], width=width, anchor="w")
            clbl.pack(side="left", padx=8)

        # Partitions
        try:
            partitions = psutil.disk_partitions(all=False)
        except Exception:
            partitions = []

        seen_mounts = set()
        for idx, part in enumerate(partitions):
            if part.mountpoint in seen_mounts:
                continue
            seen_mounts.add(part.mountpoint)

            try:
                usage = psutil.disk_usage(part.mountpoint)
                tot = format_bytes(usage.total)
                used = format_bytes(usage.used)
                free = format_bytes(usage.free)
                pct = f"{usage.percent:.1f}%"
            except (PermissionError, Exception):
                tot = "--"
                used = "--"
                free = "--"
                pct = "--"

            row = ctk.CTkFrame(
                card,
                fg_color=config.THEME["bg_card_inner"] if idx % 2 == 0 else "transparent",
                corner_radius=4,
                height=28,
            )
            row.pack(fill="x", padx=16, pady=1)
            row.pack_propagate(False)

            dev_lbl = ctk.CTkLabel(row, text=part.device[:20], font=ctk.CTkFont(family="Consolas", size=11), text_color=config.THEME["text_primary"], width=140, anchor="w")
            dev_lbl.pack(side="left", padx=8)

            mnt_lbl = ctk.CTkLabel(row, text=part.mountpoint[:24], font=ctk.CTkFont(family="Consolas", size=11), text_color=config.THEME["text_primary"], width=160, anchor="w")
            mnt_lbl.pack(side="left", padx=8)

            fs_lbl = ctk.CTkLabel(row, text=part.fstype, font=ctk.CTkFont(family="Segoe UI", size=10), text_color=config.THEME["text_muted"], width=80, anchor="w")
            fs_lbl.pack(side="left", padx=8)

            t_lbl = ctk.CTkLabel(row, text=tot, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=config.THEME["text_secondary"], width=90, anchor="w")
            t_lbl.pack(side="left", padx=8)

            u_lbl = ctk.CTkLabel(row, text=used, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=config.THEME["text_secondary"], width=90, anchor="w")
            u_lbl.pack(side="left", padx=8)

            f_lbl = ctk.CTkLabel(row, text=free, font=ctk.CTkFont(family="Segoe UI", size=11), text_color=config.THEME["text_secondary"], width=90, anchor="w")
            f_lbl.pack(side="left", padx=8)

            pct_lbl = ctk.CTkLabel(row, text=pct, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color=config.THEME["disk"], width=80, anchor="w")
            pct_lbl.pack(side="left", padx=8)

        # Padding at bottom
        ctk.CTkFrame(card, height=8, fg_color="transparent").pack()

    def _get_os_info(self) -> List[tuple]:
        distro = "Linux"
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            distro = line.split("=", 1)[1].strip('"\n')
                            break
            except Exception:
                pass

        return [
            ("Operating System", f"{platform.system()} ({distro})"),
            ("Kernel Release", platform.release()),
            ("System Architecture", f"{platform.machine()} ({platform.architecture()[0]})"),
            ("Hostname / Node", platform.node()),
            ("Python Runtime", f"v{platform.python_version()} ({platform.python_implementation()})"),
            ("Platform Details", platform.platform()),
        ]

    def _get_cpu_info(self) -> List[tuple]:
        # Processor Model
        model = platform.processor() or "Generic x86_64"
        if os.path.exists("/proc/cpuinfo"):
            try:
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "model name" in line:
                            model = line.split(":", 1)[1].strip()
                            break
            except Exception:
                pass

        logical_cores = psutil.cpu_count(logical=True) or 1
        physical_cores = psutil.cpu_count(logical=False) or logical_cores

        freq = psutil.cpu_freq()
        cur_freq = f"{freq.current:.1f} MHz" if freq else "Dynamic"
        min_freq = f"{freq.min:.1f} MHz" if freq and freq.min else "--"
        max_freq = f"{freq.max:.1f} MHz" if freq and freq.max else "--"

        return [
            ("Processor Model", model[:36]),
            ("Physical CPU Cores", physical_cores),
            ("Logical Threads", logical_cores),
            ("Current Clock Frequency", cur_freq),
            ("Min Supported Frequency", min_freq),
            ("Max Supported Frequency", max_freq),
        ]

    def _get_mem_info(self) -> List[tuple]:
        try:
            vm = psutil.virtual_memory()
            ram_tot = format_bytes(vm.total)
            ram_avail = format_bytes(vm.available)
            ram_used = format_bytes(vm.used)
            ram_cached = format_bytes(getattr(vm, "cached", 0))
        except Exception:
            ram_tot = ram_avail = ram_used = ram_cached = "--"

        try:
            sm = psutil.swap_memory()
            swap_tot = format_bytes(sm.total)
            swap_used = format_bytes(sm.used)
            swap_free = format_bytes(sm.free)
        except Exception:
            swap_tot = swap_used = swap_free = "--"

        return [
            ("Total Physical RAM", ram_tot),
            ("Available Physical RAM", ram_avail),
            ("Used Physical RAM", ram_used),
            ("Cached / Buffers", ram_cached),
            ("Total Swap Space", swap_tot),
            ("Used Swap Space", swap_used),
            ("Free Swap Space", swap_free),
            ("Virtual Memory Pages", "4 KB Standard Page Size"),
        ]

    def _get_boot_info(self) -> List[tuple]:
        try:
            btime = psutil.boot_time()
            boot_str = datetime.fromtimestamp(btime).strftime("%Y-%m-%d %H:%M:%S")
            uptime_str = format_uptime(time.time() - btime)
        except Exception:
            boot_str = "--"
            uptime_str = "--"

        return [
            ("System Boot Timestamp", boot_str),
            ("Total System Uptime", uptime_str),
            ("Current System Clock", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            ("Timezone", time.tzname[0] if time.tzname else "Local"),
        ]
