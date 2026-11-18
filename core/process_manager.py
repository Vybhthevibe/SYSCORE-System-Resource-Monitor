"""
SYSCORE — OS Process Management Subsystem
Process enumeration, inspection, sorting, filtering, and safe termination.
"""
from dataclasses import dataclass
from datetime import datetime
import os
import psutil
from typing import Any, Dict, List, Optional, Tuple

import config


@dataclass
class ProcessInfo:
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float
    memory_rss_mb: float
    num_threads: int
    create_time_str: str
    username: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "status": self.status,
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "memory_rss_mb": self.memory_rss_mb,
            "num_threads": self.num_threads,
            "create_time_str": self.create_time_str,
            "username": self.username,
        }


class ProcessManager:
    """
    Interacts with the Operating System Kernel process table via psutil.
    Implements safe process inspection, filtering, and controlled termination.
    Maintains a persistent Process instance cache for accurate CPU % calculations.
    """
    _proc_cache: Dict[int, psutil.Process] = {}

    @classmethod
    def get_processes(
        cls,
        sort_by: str = "cpu",
        reverse: bool = True,
        search_query: Optional[str] = None,
        limit: Optional[int] = 120,
    ) -> List[ProcessInfo]:
        """
        Snapshot active processes from the OS kernel.
        Caches psutil.Process objects across calls to calculate true CPU usage deltas.
        Safely falls back per-attribute on AccessDenied/NoSuchProcess so system processes
        are never dropped from the view.
        """
        procs: List[ProcessInfo] = []
        alive_pids = set()
        query = search_query.strip().lower() if search_query else None

        for proc in psutil.process_iter():
            try:
                pid = proc.pid
                alive_pids.add(pid)

                # Retrieve or initialize persistent Process instance for CPU delta
                if pid in cls._proc_cache:
                    p = cls._proc_cache[pid]
                else:
                    p = proc
                    cls._proc_cache[pid] = p
                    try:
                        p.cpu_percent(None)  # prime first call
                    except Exception:
                        pass

                # Name
                try:
                    name = p.name() or "Unknown"
                except Exception:
                    name = "Unknown"

                # Filter by search query if provided (PID or Name)
                if query:
                    pid_str = str(pid)
                    if query not in name.lower() and query not in pid_str:
                        continue

                # Status
                try:
                    status = p.status() or "unknown"
                except Exception:
                    status = "unknown"

                # CPU % (calculated over elapsed time since last call)
                try:
                    cpu = float(p.cpu_percent(None) or 0.0)
                except Exception:
                    cpu = 0.0

                # Memory RSS & %
                try:
                    mem_info = p.memory_info()
                    rss_mb = round(mem_info.rss / (1024 * 1024), 1) if mem_info else 0.0
                except Exception:
                    rss_mb = 0.0

                try:
                    mem_pct = float(p.memory_percent() or 0.0)
                except Exception:
                    mem_pct = 0.0

                # Threads
                try:
                    threads = p.num_threads() or 1
                except Exception:
                    threads = 1

                # Username
                try:
                    username = p.username() or "system"
                except Exception:
                    username = "system"

                # Creation time
                try:
                    c_time = p.create_time()
                    create_str = datetime.fromtimestamp(c_time).strftime("%H:%M:%S")
                except Exception:
                    create_str = "--"

                pinfo = ProcessInfo(
                    pid=pid,
                    name=name,
                    status=status,
                    cpu_percent=round(cpu, 1),
                    memory_percent=round(mem_pct, 1),
                    memory_rss_mb=rss_mb,
                    num_threads=threads,
                    create_time_str=create_str,
                    username=username,
                )
                procs.append(pinfo)

            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                continue
            except Exception:
                continue

        # Purge dead processes from persistent cache
        for cached_pid in list(cls._proc_cache.keys()):
            if cached_pid not in alive_pids:
                cls._proc_cache.pop(cached_pid, None)

        # Sort processes based on requested column
        sort_keys = {
            "cpu": lambda p: p.cpu_percent,
            "memory": lambda p: p.memory_rss_mb,
            "pid": lambda p: p.pid,
            "name": lambda p: p.name.lower(),
            "threads": lambda p: p.num_threads,
            "created": lambda p: p.create_time_str,
        }
        key_func = sort_keys.get(sort_by, lambda p: p.cpu_percent)
        procs.sort(key=key_func, reverse=reverse)

        if limit and limit > 0:
            return procs[:limit]
        return procs

    @staticmethod
    def get_process_detail(pid: int) -> Tuple[bool, Dict[str, Any]]:
        """
        Perform in-depth inspection of a specific process.
        Extracts each attribute with isolated exception handlers so permission restrictions
        on certain fields (like open files or username) do not abort the entire inspection.
        """
        try:
            p = psutil.Process(pid)
        except psutil.NoSuchProcess:
            return False, {"error": f"Process {pid} has already terminated."}
        except psutil.AccessDenied:
            return False, {"error": f"Access denied by OS when inspecting PID {pid}."}
        except Exception as e:
            return False, {"error": f"Failed to access PID {pid}: {str(e)}"}

        # Safe attribute extractions
        try:
            name = p.name()
        except Exception:
            name = f"Process {pid}"

        try:
            status = p.status()
        except Exception:
            status = "unknown"

        try:
            ppid = p.ppid()
        except Exception:
            ppid = "N/A"

        try:
            cpu_pct = p.cpu_percent(interval=None)
        except Exception:
            cpu_pct = 0.0

        try:
            mem_info = p.memory_info()
            rss_mb = round(mem_info.rss / (1024 * 1024), 2)
            vms_mb = round(mem_info.vms / (1024 * 1024), 2)
        except Exception:
            rss_mb = 0.0
            vms_mb = 0.0

        try:
            mem_pct = p.memory_percent()
        except Exception:
            mem_pct = 0.0

        try:
            threads = p.num_threads()
        except Exception:
            threads = "N/A"

        try:
            create_time = datetime.fromtimestamp(p.create_time()).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            create_time = "--"

        try:
            username = p.username()
        except (psutil.AccessDenied, Exception):
            username = "N/A (Access Denied)"

        try:
            nice = p.nice()
        except (psutil.AccessDenied, Exception):
            nice = "N/A (Access Denied)"

        try:
            cmd = p.cmdline()
            cmdline = " ".join(cmd) if cmd else f"[{name}]"
        except (psutil.AccessDenied, Exception):
            cmdline = "[Access Denied by OS]"

        try:
            exe = p.exe()
        except (psutil.AccessDenied, Exception):
            exe = "[Access Denied by OS]"

        try:
            open_files_count = len(p.open_files())
        except (psutil.AccessDenied, Exception):
            open_files_count = "N/A (Access Denied)"

        try:
            net_conns = len(p.net_connections(kind="all"))
        except (psutil.AccessDenied, Exception):
            net_conns = "N/A (Access Denied)"

        detail = {
            "pid": pid,
            "name": name,
            "ppid": ppid,
            "status": status,
            "cpu_percent": round(cpu_pct, 1),
            "memory_percent": round(mem_pct, 1),
            "memory_rss_mb": rss_mb,
            "memory_vms_mb": vms_mb,
            "threads": threads,
            "create_time": create_time,
            "username": username,
            "nice": nice,
            "exe": exe,
            "cmdline": cmdline,
            "open_files": open_files_count,
            "net_connections": net_conns,
            "is_protected": ProcessManager.is_critical_process(pid, name),
        }
        return True, detail

    @staticmethod
    def is_critical_process(pid: int, name: Optional[str] = None) -> bool:
        """
        Safety check: Detect whether a process is an essential OS system component
        or the monitoring app itself, which must never be terminated.
        """
        if pid in config.PROTECTED_PIDS or pid <= 2:
            return True

        if name:
            base_name = os.path.basename(name).lower()
            if base_name in config.PROTECTED_PROCESS_NAMES:
                return True

        try:
            p = psutil.Process(pid)
            pname = p.name().lower()
            if pname in config.PROTECTED_PROCESS_NAMES:
                return True
        except Exception:
            pass

        return False

    @staticmethod
    def terminate_process(pid: int, force: bool = False) -> Tuple[bool, str]:
        """
        Request process termination from the OS kernel.
        Safely validates that critical processes are not targeted.
        Demonstrates OS Process Management & POSIX signals (SIGTERM vs SIGKILL).
        """
        if ProcessManager.is_critical_process(pid):
            return False, (
                f"Termination Denied: PID {pid} is a critical OS component "
                "or protected system process."
            )

        try:
            proc = psutil.Process(pid)
            proc_name = proc.name()

            if force:
                proc.kill()  # SIGKILL (Signal 9)
                action_str = "Killed (SIGKILL)"
            else:
                proc.terminate()  # SIGTERM (Signal 15)
                action_str = "Terminated (SIGTERM)"

            # Wait briefly to confirm exit
            gone, alive = psutil.wait_procs([proc], timeout=1.0)
            if proc in gone:
                return True, f"Process {proc_name} (PID {pid}) successfully {action_str}."
            else:
                return True, f"Signal sent to {proc_name} (PID {pid}). Process is terminating."

        except psutil.NoSuchProcess:
            return True, f"Process (PID {pid}) already terminated."
        except psutil.AccessDenied:
            return False, (
                f"OS Permission Denied: Unable to terminate PID {pid}. "
                "Elevated administrator (root/sudo) privileges required."
            )
        except Exception as e:
            return False, f"Failed to terminate PID {pid}: {str(e)}"
