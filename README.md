# SYSCORE — System Resource Monitor & OS Resource Management

**A Professional Desktop Application Demonstrating Operating System Concepts**  
*B.Tech Computer Science & Engineering — Operating Systems Capstone Project*

---

## 1. Project Introduction

**SYSCORE** is a high-performance, modular desktop system resource monitor and operating system telemetry management suite. Built using Python, CustomTkinter, Matplotlib, psutil, and SQLite, SYSCORE bridges theoretical operating system fundamentals with a real-time, production-grade graphical interface.

SYSCORE allows students, developers, and system administrators to monitor their computer's underlying hardware resources in real time, inspect the active kernel process table, safely manage processes, analyze long-term historical telemetry, and understand core operating system principles.

---

## 2. Problem Statement & Objectives

### Problem Statement
Standard operating systems (such as Linux and Windows) run complex schedulers, virtual memory subsystems, and device drivers concurrently. Traditional classroom tools either present dry theoretical simulations or rely on fragmented command-line utilities (`top`, `vmstat`, `iostat`, `free`). Existing GUI monitors often lack educational depth, freeze under heavy I/O loads due to single-threaded designs, or fail to explain the relationship between operating system concepts and user-space performance metrics.

### Project Objectives
1. **Real-Time Telemetry:** Deliver accurate, sub-second telemetry for CPU, Memory, Swap, Disk I/O, and Network without freezing or stuttering the GUI.
2. **Interactive Process Management:** Provide a sortable, searchable process table with deep telemetry inspection and safe termination adhering to POSIX signals.
3. **Historical Storage & Analytics:** Persist performance metrics in SQLite and render historical graphs across multiple configurable time windows with aggregate statistics (Min, Max, Avg) and CSV export.
4. **Demonstrable OS Concepts:** Genuinely implement and document core OS topics: multithreading, thread synchronization with locks and semaphores, memory management, I/O rates, and process safety.
5. **Modern Developer UI/UX:** Provide a dark-themed developer workstation aesthetic with responsive navigation and clean typography.

---

## 3. Technology Stack

| Technology | Purpose in SYSCORE |
| :--- | :--- |
| **Python 3.10+** | Core programming language and runtime |
| **CustomTkinter** | Modern, dark-mode desktop GUI framework with high DPI support |
| **Matplotlib** | Real-time and historical time-series performance graphs |
| **psutil** | Hardware counters, CPU frequency, virtual memory, and kernel process table interface |
| **SQLite3** | Thread-safe embedded relational database for persistent telemetry logging |
| **threading & queue** | Background sampling daemon, thread safety, and inter-thread event communication |

---

## 4. Key Application Modules

```
SYSCORE/
├── 📊 System Overview Dashboard   (Module A)
├── ⚙️ Process Monitor & Control    (Module B)
├── 📈 Resource Analytics & SQLite  (Module C)
├── 💻 System Information           (Module D)
└── 🛠️ Settings & Alerts           (Module E)
```

### Module A: System Overview Dashboard
- **Live Metric Cards:** CPU Utilization %, Physical Memory Used/Available, Virtual Swap %, Root Storage Usage %, Real-time Disk Read/Write rates (KB/s or MB/s), Real-time Network Upload/Download rates.
- **4-Pane Live Charts:** Live updating Matplotlib time-series charts for CPU, Memory (RAM vs Swap), Disk I/O, and Network Bandwidth.
- **Configurable Refresh Rate:** Dropdown selector (0.5s, 1.0s, 2.0s, 5.0s) dynamically adjusting the background sampling frequency.
- **System Uptime Badge:** Shows total elapsed uptime and boot timestamp.
- **Active Alert Banner:** Instantly alerts the user when CPU, RAM, or Disk crosses a warning threshold.

### Module B: Process Monitor
- **Process Table:** Displays PID, Process Name, Kernel Status (`running`, `sleeping`, `zombie`), CPU %, Memory (RSS MB and %), Thread Count, and User.
- **Search & Quick Presets:** Real-time search filter by Name or PID; one-click presets for **Top CPU**, **Top Memory**, and custom sorting.
- **Deep Process Telemetry Dialog:** Inspects Parent PID (PPID), Command Line, Executable Path, Nice Priority, Memory VMS, Open File Descriptors, and Active Network Sockets.
- **Safe Process Termination:**
  - Explicit confirmation modal dialog before issuing termination signals.
  - Option to send standard `SIGTERM` (15) or force `SIGKILL` (9).
  - Protected system process whitelist (PID 1, 2, systemd, current app) preventing accidental system crashes.
  - Graceful handling of OS permission denials (`psutil.AccessDenied`) and disappeared processes (`psutil.NoSuchProcess`).

### Module C: Resource Analytics
- **SQLite Historical Trends:** Persistent storage across application restarts in `data/syscore.db`.
- **Time Range Windows:** Flexible historical analysis: **Last 5 minutes**, **Last 15 minutes**, **Last 1 hour**, **Last 24 hours**, and **All Time**.
- **Statistical Aggregates:** Computes Min, Max, and Average values for CPU, Memory, Disk transfer rates, and Network bandwidth using SQL aggregate queries.
- **CSV Data Export:** One-click export to CSV for lab report submissions and external spreadsheet analysis.

### Module D: System Information
- **OS & Kernel Telemetry:** OS Name, Distribution (e.g., EndeavourOS / Arch / Ubuntu), Kernel Release, Hostname, Python Runtime.
- **CPU Architecture:** Processor model, Physical Cores vs Logical Threads, Current/Min/Max clock frequencies.
- **Memory Hierarchy:** Total physical RAM, Available, Used, Cached/Buffers, Total Swap, and Virtual Page size.
- **Storage Partitions:** Complete table of mounted partitions, device paths, filesystem types (`ext4`, `btrfs`, `ntfs`), total, used, free, and utilization.

### Module E: Settings & Alerts
- **Sampling Frequency Slider:** Smooth slider from 0.5s to 5.0s.
- **Historical Logging Switch:** Toggle SQLite persistence on or off.
- **Configurable Thresholds:** Independent sliders for CPU, RAM, and Disk alert limits (50% to 98%).
- **Database Retention & Pruning:** Automated or manual pruning of records older than 1, 7, or 30 days to prevent disk bloat.

---

## 5. Software Architecture

SYSCORE follows a modular, decoupled architecture where GUI rendering is completely isolated from hardware sampling and database I/O:

```
SYSCORE/
│
├── main.py                     # Application entry point (GUI & CLI modes)
├── run.sh                      # Shell launcher with environment bootstrap
├── config.py                   # Central configuration, colors, and defaults
├── requirements.txt            # Python dependencies
├── README.md                   # Complete project documentation
├── OS_CONCEPTS.md              # Detailed OS viva & conceptual mapping guide
│
├── core/                       # Backend Logic & OS Interfaces
│   ├── __init__.py
│   ├── sampler.py              # Hardware counter reader & rate calculator
│   ├── process_manager.py      # Process inspection & safe termination
│   ├── monitoring_engine.py    # Threaded daemon, queue orchestrator, Lock & Semaphore
│   └── database.py             # Thread-safe SQLite manager & CSV exporter
│
├── ui/                         # CustomTkinter User Interface
│   ├── __init__.py
│   ├── app.py                  # Main application window & event queue consumer
│   ├── sidebar.py              # Persistent navigation & engine status badge
│   ├── dashboard.py            # Module A: Overview cards & live Matplotlib charts
│   ├── process_page.py         # Module B: Searchable process table & inspect dialog
│   ├── analytics_page.py       # Module C: Historical charts & statistical aggregates
│   ├── system_info_page.py     # Module D: OS, Kernel, CPU, and partition cards
│   ├── settings_page.py        # Module E: Sliders, thresholds, and database pruning
│   └── components.py           # Reusable metric cards, banners, and modals
│
├── utils/                      # Helper Utilities
│   ├── __init__.py
│   └── helpers.py              # Formatters (bytes, rate, uptime) & AlertManager
│
├── data/                       # Persistent Data Storage
│   ├── syscore.db              # SQLite historical database
│   └── resource_log.csv        # CSV telemetry export
│
└── tests/                      # Automated Test Suite
    ├── test_units.py           # Unit tests for helpers, alerts, and DB pruning
    └── test_full_app.py        # End-to-end integration test (GUI, queues, worker threads)
```

---

## 6. Installation & Execution

### System Requirements
- Linux (Arch/EndeavourOS, Ubuntu/Debian, Fedora) or Windows 10/11.
- Python 3.10 or newer.

### Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd "/home/vibav/Desktop/OS Project"
   ```

2. **Create a Python Virtual Environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

*(Note for Arch/EndeavourOS: If Tkinter system libraries are needed, ensure `tk` is installed via `sudo pacman -S tk`, or utilize the self-healing bootstrap bundled within the repository).*

### Running SYSCORE

- **Launch Full Desktop GUI Application:**
  ```bash
  ./run.sh
  # Or:
  python3 main.py
  ```

- **Launch Command Line (CLI) Mode (Text-only):**
  ```bash
  ./run.sh --cli
  # Or:
  python3 main.py --cli --interval 1.0
  ```

- **Run Automated Test Suites:**
  ```bash
  python3 tests/test_units.py
  python3 tests/test_full_app.py
  ```

---

## 7. Database Structure (SQLite)

Historical resource data is maintained in `data/syscore.db` using the following schema:

```sql
CREATE TABLE IF NOT EXISTS resource_history (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           TEXT NOT NULL,
    epoch_time          REAL NOT NULL,
    cpu_percent         REAL NOT NULL,
    mem_percent         REAL NOT NULL,
    mem_used_mb         REAL NOT NULL,
    mem_available_mb    REAL NOT NULL,
    swap_percent        REAL NOT NULL,
    disk_usage_percent  REAL NOT NULL,
    disk_read_kbs       REAL NOT NULL,
    disk_write_kbs      REAL NOT NULL,
    net_up_kbs          REAL NOT NULL,
    net_down_kbs        REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_history_epoch 
ON resource_history(epoch_time);
```

**Index Optimization:** The B-tree index on `epoch_time` allows range queries (e.g., "last 15 minutes") to execute in $O(\log N)$ time rather than conducting full-table scans.

---

## 8. Operating System Concepts Overview

| OS Concept | Genuine Implementation in SYSCORE |
| :--- | :--- |
| **Multithreading** | Dedicated background worker daemon (`MonitoringEngine`) isolates heavy sampling from the GUI thread. |
| **Thread Synchronization** | `threading.Lock` serializes SQLite database queries and engine state mutations; `threading.Semaphore` limits concurrent heavy operations to 2. |
| **Inter-Thread Communication** | `queue.Queue` delivers telemetry snapshots from the background worker to the main GUI thread safely. |
| **Process Management** | Retrieves process control block (PCB) telemetry via `psutil`; terminates processes safely using POSIX `SIGTERM`/`SIGKILL` signals. |
| **Virtual Memory & Paging** | Separates physical RAM from virtual swap space; displays process-level RSS vs VMS memory. |
| **I/O Management** | Computes instantaneous throughput rates ($\Delta \text{bytes} / \Delta t$) for disk controllers and network interfaces. |

*(For in-depth explanations and viva question answers, see [OS_CONCEPTS.md](file:///home/vibav/Desktop/OS%20Project/OS_CONCEPTS.md)).*

---

## 9. Known Limitations & Future Enhancements

### Known Limitations
1. **Administrative Privileges for Root Processes:** In Linux, inspecting certain root process parameters (e.g., file descriptors of processes owned by other users) or terminating system services requires elevated privileges (`sudo` / root). SYSCORE gracefully catches `PermissionError` and alerts the user.
2. **Containerized / Virtualized Counters:** In containerized environments, `psutil` reports virtualized disk and network counters for the container namespace rather than bare-metal hardware.

### Future Enhancements
1. **Per-Core CPU Heatmap:** Visual grid representing core frequencies and thermal throttling.
2. **Process Tree Hierarchy:** Visual tree view linking child processes to their parent PPIDs.
3. **Automated Anomaly Detection:** Machine learning alerts for sudden memory leaks or runaway background processes.
