# SYSCORE — Operating System Concepts Guide

**Technical Implementation & Viva Defense Guide**  
*Course: Operating Systems (B.Tech Computer Science & Engineering)*

---

## Introduction

This document provides a comprehensive mapping between theoretical Operating System concepts and their genuine implementation within **SYSCORE**. Use this guide to prepare for your viva voce, lab demonstrations, and project defense.

---

## 1. Process Management

### Theoretical Foundation
A **process** is an active program in execution, managed by the Operating System kernel via a data structure called the **Process Control Block (PCB)**. The PCB contains:
- **Process Identifier (PID):** Unique integer assigned by the kernel.
- **Process State:** Current execution status (`Running`, `Ready`, `Waiting/Blocked`, `Zombie`, `Terminated`).
- **CPU Registers & Program Counter:** State of processor execution.
- **CPU Scheduling Information:** Priority, nice value, CPU burst time.
- **Memory Management Information:** Page tables, Resident Set Size (RSS), Virtual Memory Size (VMS).
- **I/O & Accounting Information:** Open file descriptors, active network sockets, owner user ID.

Process termination in POSIX operating systems relies on **signals**:
- `SIGTERM` (Signal 15): A polite termination request asking the process to save state, flush file buffers, and exit cleanly.
- `SIGKILL` (Signal 9): An uncatchable kernel signal that immediately destroys the process PCB and frees allocated memory pages without allowing the process to execute cleanup routines.

### Implementation in SYSCORE
- **Where it appears:** `Process Monitor` page (`ui/process_page.py`), `core/process_manager.py`.
- **Key Classes & Methods:**
  - `core.process_manager.ProcessManager.get_processes()`: Queries the Linux `/proc` filesystem via `psutil.process_iter()`, gathering PID, name, state, CPU%, Memory%, threads, and user.
  - `core.process_manager.ProcessManager.get_process_detail(pid)`: Inspects in-depth PCB attributes including Parent PID (PPID), command line, open file descriptors, network connections, and nice values.
  - `core.process_manager.ProcessManager.terminate_process(pid, force=False)`: Implements safe POSIX signal dispatching. When `force=False`, dispatches `SIGTERM` (`proc.terminate()`); when `force=True`, dispatches `SIGKILL` (`proc.kill()`).
  - `core.process_manager.ProcessManager.is_critical_process(pid)`: Safety check protecting PID 1 (`init`/`systemd`), kernel daemons (e.g., `kthreadd`), and the monitoring app itself.

### Why It Matters
Without process inspection, users cannot identify resource-hogging background tasks ("runaway processes") or memory leaks. Moreover, improper process termination can crash the operating system if critical kernel daemons are terminated.

### How to Explain in a Viva
> *"In our project, we interact with the OS kernel's process table through `core/process_manager.py`. When we inspect a process, we read attributes representing its Process Control Block (PCB)—including PID, execution state, priority, and open file descriptors. When terminating a process, we respect POSIX signal architecture: we first issue `SIGTERM` (Signal 15) allowing the program to gracefully release file locks and sockets. If the process is unresponsive, the user can force `SIGKILL` (Signal 9). We also implemented a protection layer that blocks termination requests targeting PID 1 (`systemd`/`init`) or kernel threads to maintain system stability."*

---

## 2. Multithreading

### Theoretical Foundation
A **thread** is the smallest unit of CPU execution within a process, sharing the parent process's address space, code section, data section, and OS resources (such as open files), but maintaining its own private **Program Counter (PC)**, **registers**, and **call stack**.

In graphical user interfaces (GUIs), the main thread is responsible for the **Event Dispatch Loop** (rendering frames, handling mouse clicks, processing keyboard events). If an intensive or blocking operation (such as reading hardware counters, querying a database, or disk I/O) executes on the GUI thread, the event loop stalls, causing the window to freeze, become unresponsive, and trigger OS "Not Responding" warnings.

### Implementation in SYSCORE
- **Where it appears:** Background telemetry collection (`core/monitoring_engine.py`), asynchronous process listing (`ui/process_page.py`), asynchronous analytics querying (`ui/analytics_page.py`).
- **Key Classes & Methods:**
  - `core.monitoring_engine.MonitoringEngine.start()`: Spawns a dedicated background daemon thread (`SyscoreMonitoringWorker` via `threading.Thread`) that loops continuously at the configured sampling interval.
  - Decoupled GUI updates: The background thread never interacts directly with Tkinter/CustomTkinter widgets. Instead, it places collected metrics into a thread-safe `queue.Queue`.
  - The main GUI thread runs `self.after(100, self._process_queues)` on the Tkinter event loop, popping items from the queue and rendering metric cards and charts.
  - Asynchronous worker threads in `ProcessPage` and `AnalyticsPage` handle process enumeration and SQLite queries in the background so navigating pages remains immediate.

### Why It Matters
Hardware sampling requires querying disk and network kernel counters over an elapsed time window $\Delta t$, and database queries involve disk I/O. If executed on the main thread, the interface would freeze every refresh cycle. Multithreading ensures the UI maintains a consistent, buttery-smooth 60 FPS.

### How to Explain in a Viva
> *"We decoupled our application into a multi-threaded architecture. The main thread runs CustomTkinter's event dispatch loop to handle UI rendering and user interactions. We spawned a separate background daemon worker thread (`SyscoreMonitoringWorker`) that handles all psutil hardware sampling and SQLite logging. The worker thread communicates with the main thread using a thread-safe `queue.Queue`. This guarantees that heavy I/O operations or hardware counter calculations never block the GUI thread, eliminating window freezing."*

---

## 3. Thread Synchronization (Lock & Semaphore)

### Theoretical Foundation
When multiple concurrent threads access shared resources, race conditions and data corruption can occur unless proper synchronization primitives are used:
1. **Mutex Lock (`threading.Lock`):** Provides mutual exclusion. Only one thread can hold the lock at any time. Any other thread attempting to acquire the lock blocks until the holding thread releases it. Critical sections (such as modifying shared state or executing SQLite operations) must be protected by a Lock.
2. **Counting Semaphore (`threading.Semaphore`):** A synchronization variable initialized to an integer $K$ representing the number of available shared resource units. When a thread executes $P$ / `acquire()`, the counter decrements. If the counter reaches zero, subsequent threads block until a thread executes $V$ / `release()`. Semaphores are used for **resource throttling** and concurrency limiting.

### Implementation in SYSCORE
- **Where it appears:** `core/database.py`, `core/monitoring_engine.py`.
- **Lock Implementation:**
  - In `core.database.Database`: SQLite connections cannot safely execute concurrent write and read transactions across multiple threads without risk of `OperationalError: database is locked`. We protect every query, insert, and vacuum operation with `self.lock = threading.Lock()`.
  - In `core.monitoring_engine.MonitoringEngine`: `self._state_lock` serializes read and write access to engine configuration flags (pause status, sampling interval, latest cached sample).
- **Semaphore Implementation:**
  - In `core.monitoring_engine.MonitoringEngine`: We implement `self._worker_semaphore = threading.Semaphore(value=2)`. This throttles concurrent heavy OS queries. For example, if the background monitoring thread is sampling hardware while the user simultaneously triggers rapid process table refreshes or database pruning, the semaphore restricts concurrent background resource operations to at most 2, preventing CPU thrashing and system resource starvation.

### Why It Matters
Without the Lock, the background logging thread and the UI analytics query thread would collide on the SQLite database, causing transaction aborts. Without the Semaphore, aggressive user interactions could spawn unrestrained concurrent system scans, causing the monitor itself to consume excessive CPU cycles.

### How to Explain in a Viva
> *"We implemented genuine synchronization primitives rather than theoretical mockups. We use `threading.Lock` in `core/database.py` to serialize database access between the background telemetry writer and the UI analytics reader, eliminating SQLite concurrency collisions. Furthermore, we use a `threading.Semaphore(value=2)` in `MonitoringEngine` to enforce concurrency limits on heavy system operations, ensuring the monitor never exhausts system CPU or I/O bandwidth during high-frequency user actions."*

---

## 4. Memory Management (Physical RAM vs. Virtual Swap)

### Theoretical Foundation
Modern operating systems utilize **Virtual Memory Management**:
- **Physical Memory (RAM):** Hardware dynamic RAM chips offering high-speed, direct access for active instructions and data.
- **Virtual Memory & Swap Space:** Disk-backed storage used when physical memory demands exceed available RAM. The OS memory manager divides memory into fixed-size **pages** (typically 4 KB on x86_64). Inactive or cold pages are transferred to the disk swap partition/file via **page out / paging**.
- **Process Memory Metrics:**
  - **Resident Set Size (RSS):** The portion of a process's memory currently held in physical RAM.
  - **Virtual Memory Size (VMS):** The total address space allocated to the process, including shared libraries, mapped files, and pages swapped to disk.

### Implementation in SYSCORE
- **Where it appears:** `Dashboard` (`ui/dashboard.py`), `System Information` (`ui/system_info_page.py`), `Process Monitor` (`ui/process_page.py`).
- **Key Metrics Captured:**
  - Physical RAM Total, Used, and Available (calculated via `psutil.virtual_memory()`).
  - Swap Space Total, Used, and Free (calculated via `psutil.swap_memory()`).
  - Memory cached/buffers breakdown in `SystemInfoPage`.
  - Process-level RSS (MB) and Memory % in `ProcessPage` and `ProcessDetailDialog`.

### Why It Matters
High physical RAM usage is not necessarily catastrophic if available memory and cached buffers can be freed on demand. However, when the OS begins heavily utilizing Swap space, system performance drops by orders of magnitude due to the latency difference between RAM (~nanoseconds) and NVMe/HDD storage (~microseconds/milliseconds)—a phenomenon known as **thrashing**.

### How to Explain in a Viva
> *"Our project demonstrates the distinction between physical memory and virtual swap memory. In Module A and Module D, we display physical RAM alongside virtual swap utilization. If RAM utilization climbs near 100%, the OS kernel page daemon begins paging out cold pages into the swap partition. In the Process Monitor, we distinguish between a process's Resident Set Size (RSS)—the actual RAM it occupies—and its Virtual Memory Size (VMS), which includes mapped memory and swapped pages."*

---

## 5. Input/Output (I/O) Management

### Theoretical Foundation
Operating systems track I/O activity through cumulative hardware counters maintained in kernel space:
- **Disk I/O:** Total bytes read and written to block devices (`/sys/block/` on Linux).
- **Network Bandwidth:** Total packets and bytes transmitted (`bytes_sent`) and received (`bytes_recv`) across network interfaces (`/proc/net/dev`).

Because the kernel only maintains cumulative byte totals since boot, user-space monitors must calculate **instantaneous transfer rates** by computing the difference between two snapshots divided by the elapsed time $\Delta t$:

$$\text{Rate (KB/s)} = \frac{\text{Bytes}_{\text{current}} - \text{Bytes}_{\text{previous}}}{1024 \times \Delta t}$$

### Implementation in SYSCORE
- **Where it appears:** `core/sampler.py`, `ui/dashboard.py`.
- **Key Implementation Details:**
  - In `core.sampler.Sampler.sample()`: We record the exact system time (`now = time.time()`) and compute $\Delta t = \max(\text{now} - t_{\text{prev}}, 10^{-6})$ to prevent division by zero.
  - Reads cumulative `psutil.disk_io_counters()` and `psutil.net_io_counters()`.
  - Computes read rate (`disk_read_kbs`), write rate (`disk_write_kbs`), download rate (`net_down_kbs`), and upload rate (`net_up_kbs`).
  - Stores rates in SQLite and plots them on dedicated time-series graphs with dynamic axis scaling.

### Why It Matters
A system may show low CPU utilization while still feeling sluggish due to an **I/O bottleneck** (processes stuck in the `D` / uninterruptible disk-sleep state waiting for storage operations to finish). Monitoring transfer rates reveals disk contention and network saturation.

### How to Explain in a Viva
> *"Hardware counters in Linux represent cumulative byte counts since system boot. To display real-time I/O transfer rates in KB/s and MB/s, our `Sampler` class samples the counters at interval $\Delta t$, computes the differential delta between successive samples, and divides by the elapsed time. This allows us to visualize instantaneous storage throughput and network bandwidth on dedicated Matplotlib charts."*

---

## 6. Quick Viva Questions & Answers Reference

| Viva Question | Concise Model Answer |
| :--- | :--- |
| **Q1: Why didn't you update the Tkinter GUI directly from the background thread?** | Tkinter is fundamentally not thread-safe. Calling GUI widget methods from a non-main thread can corrupt Tk internal state and crash the interpreter. We used a thread-safe `queue.Queue` where the worker thread posts data and the main thread consumes it via `root.after()`. |
| **Q2: What is the difference between `SIGTERM` and `SIGKILL` in your process manager?** | `SIGTERM` (Signal 15) is a catchable signal requesting the process to terminate gracefully, allowing cleanup of open files. `SIGKILL` (Signal 9) cannot be caught or ignored; the OS kernel immediately terminates the process and reclaims its resources. |
| **Q3: Why is a Lock necessary if SQLite has its own locking?** | SQLite allows multiple simultaneous readers, but write transactions acquire an exclusive lock. If our background thread writes a new sample while the UI thread queries analytics on the same connection without serialization, SQLite throws `OperationalError: database is locked`. The `threading.Lock` serializes Python-level access to the connection. |
| **Q4: What is the difference between RSS and VMS?** | RSS (Resident Set Size) is the exact amount of physical RAM allocated to a process. VMS (Virtual Memory Size) is the entire virtual address space mapped by the process, including allocated heap, shared libraries, and swapped-out memory pages. |
| **Q5: How does your app prevent CPU throttling or thrashing?** | We employ `threading.Semaphore(2)` to limit concurrent background operations, reuse Matplotlib line objects via `set_data()` to avoid re-rendering axes, and use a 30-second cooldown in `AlertManager` to prevent notification loops. |
