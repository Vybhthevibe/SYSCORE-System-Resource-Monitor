#!/usr/bin/env python3
"""
SYSCORE — System Resource Monitor & OS Resource Management
Main Application Entry Point.

B.Tech Operating Systems Capstone Project.
Supports both modern CustomTkinter Desktop GUI and lightweight CLI modes.
"""
import argparse
import os
import sys
import time

# --------------------------------------------------------------------------
# Dynamic Linker & Tkinter Library Resolution Bootstrap
# --------------------------------------------------------------------------
def _bootstrap_tk():
    """
    Ensures Tkinter and Matplotlib dependencies resolve on Linux distributions
    where Tk shared objects reside within the local virtual environment.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_lib = os.path.join(base_dir, ".venv", "lib")
    
    # Configure Matplotlib temp cache
    if "MPLCONFIGDIR" not in os.environ:
        os.environ["MPLCONFIGDIR"] = "/tmp/mplconfig"

    if os.path.exists(venv_lib):
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if venv_lib not in current_ld.split(":"):
            os.environ["LD_LIBRARY_PATH"] = f"{venv_lib}:{current_ld}" if current_ld else venv_lib
            os.environ.setdefault("TK_LIBRARY", os.path.join(venv_lib, "tk8.6"))
            os.environ.setdefault("TCL_LIBRARY", os.path.join(venv_lib, "tcl8.6"))
            try:
                # Re-execute process with updated dynamic linker path
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except Exception as e:
                print(f"[Warning] Failed to re-exec with LD_LIBRARY_PATH: {e}")

_bootstrap_tk()

# Now import project modules
import config
from core.database import Database
from core.sampler import Sampler
from utils.helpers import format_bytes, format_rate, format_percent


def run_cli_mode(interval: float, db: Database):
    """
    Terminal text-only monitoring mode.
    Preserves and extends the CLI feature from the original project.
    """
    sampler = Sampler()
    print("=" * 80)
    print(f" {config.APP_NAME} — Command Line Interface")
    print(f" Logging to SQLite: {db.db_path} | Sampling interval: {interval:.1f}s")
    print(" Press Ctrl+C to terminate.")
    print("=" * 80)
    print(
        f"{'TIMESTAMP':19}  {'CPU%':>6}  {'RAM%':>6}  {'SWAP%':>6}  "
        f"{'DISK%':>6}  {'READ KB/s':>10}  {'WRITE KB/s':>10}  "
        f"{'NET↓ KB/s':>10}  {'NET↑ KB/s':>10}"
    )
    print("-" * 88)

    try:
        while True:
            sample = sampler.sample()
            db.insert_sample(sample)

            ts = sample["timestamp"]
            cpu = sample["cpu_percent"]
            ram = sample["mem_percent"]
            swap = sample["swap_percent"]
            disk = sample["disk_usage_percent"]
            dr = sample["disk_read_kbs"]
            dw = sample["disk_write_kbs"]
            nd = sample["net_down_kbs"]
            nu = sample["net_up_kbs"]

            print(
                f"{ts:19}  {cpu:6.1f}  {ram:6.1f}  {swap:6.1f}  "
                f"{disk:6.1f}  {dr:10.1f}  {dw:10.1f}  "
                f"{nd:10.1f}  {nu:10.1f}"
            )
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[SYSCORE CLI] Stopped by user.")


def main():
    parser = argparse.ArgumentParser(
        description=f"{config.APP_NAME} — {config.APP_SUBTITLE}"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=config.DEFAULT_SAMPLE_INTERVAL,
        help="Sampling refresh interval in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--db",
        default=config.DB_PATH,
        help=f"SQLite database file path (default: {config.DB_PATH})",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in text-only terminal CLI mode without GUI",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{config.APP_NAME} v{config.APP_VERSION}",
    )

    args = parser.parse_args()

    # Ensure database directory exists
    db = Database(args.db)

    if args.cli:
        run_cli_mode(interval=args.interval, db=db)
    else:
        # Launch CustomTkinter GUI Desktop Application
        try:
            from ui.app import SYSCOREApp
            app = SYSCOREApp(db_path=args.db, interval=args.interval)
            app.mainloop()
        except Exception as e:
            print(f"[Fatal Startup Error]: {e}")
            print("\nFalling back to CLI mode...")
            run_cli_mode(interval=args.interval, db=db)


if __name__ == "__main__":
    main()
