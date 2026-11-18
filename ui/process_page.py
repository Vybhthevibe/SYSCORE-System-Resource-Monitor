"""
SYSCORE — Module B: Process Monitor & OS Process Management
High-performance, searchable, sortable process table, thread inspection,
and safe POSIX signal termination with critical process protection.
"""
import queue
import threading
import time
from tkinter import ttk
from typing import Dict, List, Optional

import customtkinter as ctk

import config
from core.process_manager import ProcessManager, ProcessInfo
from .components import ProcessDetailDialog, ConfirmTerminateDialog


class ProcessPage(ctk.CTkFrame):
    """
    Dedicated process monitoring page.
    Utilizes a dark-styled ttk.Treeview for high-performance process rendering,
    smooth sorting, real-time search, PCB inspection, and safe termination.
    """
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=config.THEME["bg_main"], corner_radius=0, **kwargs)

        self._sort_by = "cpu"
        self._sort_reverse = True
        self._search_query = ""
        self._selected_pid: Optional[int] = None
        self._selected_proc_name: Optional[str] = None
        self._auto_refresh_enabled = True
        self._is_refreshing = False

        self._procs_cache: List[ProcessInfo] = []

        # Thread-safe queue for background sampling
        self._result_queue = queue.Queue()

        # Configure dark Treeview style
        self._setup_treeview_style()

        # 1. Header & Summary Statistics
        self._build_header()

        # 2. Search, Filter & Action Toolbar
        self._build_toolbar()

        # 3. Process Table Container
        self._build_treeview()

        # 4. Status / Notification Footer
        self.footer = ctk.CTkLabel(
            self,
            text="Ready. Click any process to inspect or terminate. Double-click to inspect directly.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=config.THEME["text_muted"],
            anchor="w",
        )
        self.footer.pack(fill="x", padx=24, pady=(4, 10))

        # Start periodic queue consumer on main GUI thread
        self.after(50, self._poll_result_queue)

        # Initial process table population
        self.refresh_processes()

    def _setup_treeview_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Syscore.Treeview",
            background=config.THEME["bg_card"],
            foreground=config.THEME["text_primary"],
            fieldbackground=config.THEME["bg_card"],
            borderwidth=0,
            rowheight=30,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Syscore.Treeview.Heading",
            background=config.THEME["bg_card_inner"],
            foreground=config.THEME["text_secondary"],
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            borderwidth=1,
            padding=(6, 6),
        )
        style.map(
            "Syscore.Treeview",
            background=[("selected", config.THEME["btn_primary"])],
            foreground=[("selected", "#ffffff")],
        )
        style.map(
            "Syscore.Treeview.Heading",
            background=[("active", config.THEME["bg_card_hover"])],
            foreground=[("active", config.THEME["text_primary"])],
        )

    def _build_header(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=20, pady=(16, 8))

        tbox = ctk.CTkFrame(head, fg_color="transparent")
        tbox.pack(side="left")

        title = ctk.CTkLabel(
            tbox,
            text="OS Process Monitor & Task Manager",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=config.THEME["text_primary"],
        )
        title.pack(anchor="w")

        self.summary_label = ctk.CTkLabel(
            tbox,
            text="Active Processes: -- | Total System Threads: --",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=config.THEME["text_muted"],
        )
        self.summary_label.pack(anchor="w", pady=(2, 0))

        # Action Buttons on Right
        btn_box = ctk.CTkFrame(head, fg_color="transparent")
        btn_box.pack(side="right")

        self.btn_inspect = ctk.CTkButton(
            btn_box,
            text="🔍  Inspect Process",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=config.THEME["btn_primary"],
            hover_color=config.THEME["btn_primary_hover"],
            height=34,
            command=self._handle_inspect,
        )
        self.btn_inspect.pack(side="left", padx=6)

        self.btn_term = ctk.CTkButton(
            btn_box,
            text="🛑  End Process",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color=config.THEME["btn_danger"],
            hover_color=config.THEME["btn_danger_hover"],
            height=34,
            command=self._handle_terminate_prompt,
        )
        self.btn_term.pack(side="left", padx=6)

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.pack(fill="x", padx=20, pady=(4, 10))

        # Search Bar
        self.search_entry = ctk.CTkEntry(
            toolbar,
            placeholder_text="Search by Name or PID...",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            width=260,
            height=34,
            fg_color=config.THEME["bg_card"],
            border_color=config.THEME["border"],
            text_color=config.THEME["text_primary"],
        )
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<KeyRelease>", self._on_search_key)
        self.search_entry.bind("<Return>", self._on_search_key)

        # Quick Sort Preset Buttons
        btn_top_cpu = ctk.CTkButton(
            toolbar,
            text="Top CPU",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=config.THEME["btn_secondary"],
            hover_color=config.THEME["btn_secondary_hover"],
            width=80,
            height=32,
            command=lambda: self._set_sort("cpu"),
        )
        btn_top_cpu.pack(side="left", padx=4)

        btn_top_ram = ctk.CTkButton(
            toolbar,
            text="Top Memory",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=config.THEME["btn_secondary"],
            hover_color=config.THEME["btn_secondary_hover"],
            width=90,
            height=32,
            command=lambda: self._set_sort("memory"),
        )
        btn_top_ram.pack(side="left", padx=4)

        # Sort Dropdown
        sort_lbl = ctk.CTkLabel(
            toolbar,
            text="Sort:",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=config.THEME["text_secondary"],
        )
        sort_lbl.pack(side="left", padx=(12, 4))

        self.sort_menu = ctk.CTkOptionMenu(
            toolbar,
            values=["CPU %", "Memory (MB)", "PID", "Process Name", "Threads", "Created"],
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=config.THEME["bg_card"],
            button_color=config.THEME["border"],
            text_color=config.THEME["text_primary"],
            width=130,
            height=32,
            command=self._on_sort_selected,
        )
        self.sort_menu.pack(side="left")

        # Auto Refresh Toggle
        self.auto_refresh_var = ctk.BooleanVar(value=True)
        chk = ctk.CTkCheckBox(
            toolbar,
            text="Auto-refresh",
            variable=self.auto_refresh_var,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=config.THEME["text_secondary"],
            fg_color=config.THEME["btn_primary"],
            hover_color=config.THEME["btn_primary_hover"],
            command=self._toggle_auto_refresh,
        )
        chk.pack(side="right", padx=(10, 0))

        # Manual Refresh Button
        self.btn_refresh = ctk.CTkButton(
            toolbar,
            text="🔄  Refresh",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=config.THEME["bg_card"],
            hover_color=config.THEME["bg_card_hover"],
            border_color=config.THEME["border"],
            border_width=1,
            width=85,
            height=32,
            command=self.refresh_processes,
        )
        self.btn_refresh.pack(side="right")

    def _build_treeview(self):
        """Construct the styled Treeview table with scrollbars."""
        table_container = ctk.CTkFrame(
            self,
            fg_color=config.THEME["bg_card"],
            border_color=config.THEME["border"],
            border_width=1,
            corner_radius=8,
        )
        table_container.pack(fill="both", expand=True, padx=20, pady=(0, 6))

        # Define columns including Process Creation Time
        self._columns = (
            "pid", "name", "status", "cpu", "memory", "threads", "created", "user"
        )
        self._col_titles = {
            "pid": "PID",
            "name": "Process Name",
            "status": "Status",
            "cpu": "CPU %",
            "memory": "Memory (MB)",
            "threads": "Threads",
            "created": "Creation Time",
            "user": "User / Owner",
        }
        self._col_widths = {
            "pid": 75,
            "name": 220,
            "status": 95,
            "cpu": 85,
            "memory": 110,
            "threads": 75,
            "created": 110,
            "user": 110,
        }

        self.tree = ttk.Treeview(
            table_container,
            columns=self._columns,
            show="headings",
            style="Syscore.Treeview",
            selectmode="browse",
        )

        for col in self._columns:
            title = self._col_titles[col]
            self.tree.heading(
                col,
                text=title,
                command=lambda c=col: self._on_header_click(c),
            )
            self.tree.column(
                col,
                width=self._col_widths[col],
                minwidth=60,
                anchor="w" if col in ("name", "user") else "center",
            )

        # Alternating row color tags
        self.tree.tag_configure("even", background=config.THEME["bg_card"])
        self.tree.tag_configure("odd", background="#1c2128")

        # Scrollbar
        scroll_y = ttk.Scrollbar(table_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)

        self.tree.pack(side="left", fill="both", expand=True, padx=(2, 0), pady=2)
        scroll_y.pack(side="right", fill="y", padx=(0, 2), pady=2)

        # Event bindings
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", lambda e: self._handle_inspect())
        self.tree.bind("<Return>", lambda e: self._handle_inspect())

    def _on_header_click(self, col: str):
        """Clicking column header toggles sort order."""
        if self._sort_by == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_by = col
            self._sort_reverse = col in ("cpu", "memory", "threads")

        # Update sort dropdown to match
        mapping = {
            "cpu": "CPU %",
            "memory": "Memory (MB)",
            "pid": "PID",
            "name": "Process Name",
            "threads": "Threads",
            "created": "Created",
        }
        if col in mapping:
            self.sort_menu.set(mapping[col])

        self.refresh_processes()

    def _on_search_key(self, event=None):
        self._search_query = self.search_entry.get().strip()
        self.refresh_processes()

    def _set_sort(self, sort_key: str):
        self._sort_by = sort_key
        self._sort_reverse = True
        mapping = {
            "cpu": "CPU %",
            "memory": "Memory (MB)",
            "pid": "PID",
            "name": "Process Name",
            "threads": "Threads",
            "created": "Created",
        }
        self.sort_menu.set(mapping.get(sort_key, "CPU %"))
        self.refresh_processes()

    def _on_sort_selected(self, val_str: str):
        mapping = {
            "CPU %": "cpu",
            "Memory (MB)": "memory",
            "PID": "pid",
            "Process Name": "name",
            "Threads": "threads",
            "Created": "created",
        }
        self._sort_by = mapping.get(val_str, "cpu")
        self._sort_reverse = self._sort_by in ("cpu", "memory", "threads")
        self.refresh_processes()

    def _toggle_auto_refresh(self):
        self._auto_refresh_enabled = self.auto_refresh_var.get()

    def refresh_processes(self):
        """
        Asynchronously sample process list in a background thread.
        Pushes results into thread-safe Queue to prevent UI freezes.
        """
        if self._is_refreshing:
            return
        self._is_refreshing = True

        def worker():
            try:
                procs = ProcessManager.get_processes(
                    sort_by=self._sort_by,
                    reverse=self._sort_reverse,
                    search_query=self._search_query,
                    limit=150,
                )
                total_threads = sum(p.num_threads for p in procs)
                total_procs = len(procs)
                self._result_queue.put(("success", procs, total_procs, total_threads))
            except Exception as e:
                self._result_queue.put(("error", str(e)))
            finally:
                self._is_refreshing = False

        threading.Thread(target=worker, daemon=True, name="ProcessRefreshWorker").start()

    def _poll_result_queue(self):
        """Consume process results on the main GUI thread."""
        try:
            while not self._result_queue.empty():
                item = self._result_queue.get_nowait()
                if item[0] == "success":
                    _, procs, total_procs, total_threads = item
                    self._apply_process_data(procs, total_procs, total_threads)
                elif item[0] == "error":
                    self.footer.configure(
                        text=f"Error sampling processes: {item[1]}",
                        text_color=config.THEME["status_error"],
                    )
        except Exception:
            pass
        finally:
            self.after(50, self._poll_result_queue)

    def _apply_process_data(self, procs: List[ProcessInfo], total_procs: int, total_threads: int):
        self._procs_cache = procs
        self.summary_label.configure(
            text=f"Displaying {len(procs)} Active Processes  |  Total System Threads: {total_threads}"
        )

        # Remember currently selected PID so selection is not lost during background refresh
        current_selection = self._selected_pid

        # Re-populate Treeview
        self.tree.delete(*self.tree.get_children())

        found_selected = False
        for idx, p in enumerate(procs):
            tag = "even" if idx % 2 == 0 else "odd"
            item_id = str(p.pid)

            values = (
                p.pid,
                p.name,
                p.status,
                f"{p.cpu_percent:4.1f}%",
                f"{p.memory_rss_mb:6.1f} MB",
                p.num_threads,
                p.create_time_str,
                p.username,
            )

            self.tree.insert("", "end", iid=item_id, values=values, tags=(tag,))

            if current_selection and p.pid == current_selection:
                self.tree.selection_set(item_id)
                self.tree.focus(item_id)
                found_selected = True

        if not found_selected and current_selection:
            # Process terminated
            self._selected_pid = None
            self._selected_proc_name = None
            self.footer.configure(
                text="Selected process exited.",
                text_color=config.THEME["text_muted"],
            )

    def _on_tree_select(self, event=None):
        """User clicked a row in Treeview."""
        selected_items = self.tree.selection()
        if not selected_items:
            return

        item_id = selected_items[0]
        try:
            pid = int(item_id)
            values = self.tree.item(item_id, "values")
            proc_name = values[1] if len(values) > 1 else "Unknown"

            self._selected_pid = pid
            self._selected_proc_name = proc_name
            self.footer.configure(
                text=f"Selected Process: {proc_name} (PID: {pid})",
                text_color=config.THEME["text_primary"],
            )
        except Exception:
            pass

    def _handle_inspect(self):
        """Opens deep inspection dialog for the selected process."""
        if not self._selected_pid:
            self.footer.configure(text="Please select a process from the table first.", text_color=config.THEME["swap"])
            return

        ok, detail = ProcessManager.get_process_detail(self._selected_pid)
        if ok:
            ProcessDetailDialog(self, detail)
        else:
            self.footer.configure(
                text=detail.get("error", "Failed to inspect process."),
                text_color=config.THEME["status_error"],
            )

    def _handle_terminate_prompt(self):
        """Prompts confirmation dialog before sending termination signal."""
        if not self._selected_pid:
            self.footer.configure(text="Please select a process to terminate first.", text_color=config.THEME["swap"])
            return

        proc_name = self._selected_proc_name or "Unknown"

        if ProcessManager.is_critical_process(self._selected_pid, proc_name):
            self.footer.configure(
                text=f"Action Denied: PID {self._selected_pid} ({proc_name}) is a critical protected system process.",
                text_color=config.THEME["status_error"],
            )
            return

        ConfirmTerminateDialog(
            parent=self,
            pid=self._selected_pid,
            proc_name=proc_name,
            on_confirm=self._execute_terminate,
        )

    def _execute_terminate(self, pid: int, force: bool):
        """Dispatches termination signal to OS kernel."""
        success, message = ProcessManager.terminate_process(pid, force=force)
        color = config.THEME["status_ok"] if success else config.THEME["status_error"]
        self.footer.configure(text=message, text_color=color)
        self._selected_pid = None
        self._selected_proc_name = None
        # Refresh table after 0.5s to verify exit
        self.after(500, self.refresh_processes)

    def on_tick(self):
        """Called periodically by the main GUI event loop to auto-refresh."""
        if self._auto_refresh_enabled and not self._is_refreshing:
            self.refresh_processes()
