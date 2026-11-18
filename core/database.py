"""
SYSCORE — SQLite Database Manager
Thread-safe persistent historical metric storage, analytics querying, and CSV export.
"""
import csv
from datetime import datetime, timedelta
import os
import sqlite3
import threading
import time
from typing import Any, Dict, List, Optional


class Database:
    """
    Manages persistent SQLite storage of resource metrics.
    Demonstrates OS Thread Synchronization: uses threading.Lock to serialize
    access to the shared SQLite connection and prevent database lock contentions
    between the background monitoring thread and the UI analytics thread.
    """
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        # Lock to ensure only one thread performs database operations at any given time
        self.lock = threading.Lock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a connection with appropriate timeouts and row factory."""
        conn = sqlite3.connect(self.db_path, timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize SQLite tables and indexes."""
        with self.lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS resource_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT NOT NULL,
                            epoch_time REAL NOT NULL,
                            cpu_percent REAL NOT NULL,
                            mem_percent REAL NOT NULL,
                            mem_used_mb REAL NOT NULL,
                            mem_available_mb REAL NOT NULL,
                            swap_percent REAL NOT NULL,
                            disk_usage_percent REAL NOT NULL,
                            disk_read_kbs REAL NOT NULL,
                            disk_write_kbs REAL NOT NULL,
                            net_up_kbs REAL NOT NULL,
                            net_down_kbs REAL NOT NULL
                        );
                    """)
                    conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_history_epoch 
                        ON resource_history(epoch_time);
                    """)
            finally:
                conn.close()

    def insert_sample(self, sample: dict) -> bool:
        """
        Insert a sampled metric dictionary into the SQLite database.
        Thread-safe under self.lock.
        """
        sql = """
            INSERT INTO resource_history (
                timestamp, epoch_time, cpu_percent, mem_percent,
                mem_used_mb, mem_available_mb, swap_percent,
                disk_usage_percent, disk_read_kbs, disk_write_kbs,
                net_up_kbs, net_down_kbs
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            sample.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            sample.get("epoch_time", time.time()),
            float(sample.get("cpu_percent", 0.0)),
            float(sample.get("mem_percent", 0.0)),
            float(sample.get("mem_used_mb", 0.0)),
            float(sample.get("mem_available_mb", 0.0)),
            float(sample.get("swap_percent", 0.0)),
            float(sample.get("disk_usage_percent", 0.0)),
            float(sample.get("disk_read_kbs", 0.0)),
            float(sample.get("disk_write_kbs", 0.0)),
            float(sample.get("net_up_kbs", 0.0)),
            float(sample.get("net_down_kbs", 0.0)),
        )

        with self.lock:
            conn = self._get_connection()
            try:
                with conn:
                    conn.execute(sql, params)
                return True
            except sqlite3.Error as e:
                print(f"[Database Error] Insert failed: {e}")
                return False
            finally:
                conn.close()

    def get_history(
        self,
        time_range_minutes: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve historical records.
        If time_range_minutes is specified, filters records within that window.
        Returns ordered chronologically (oldest to newest).
        """
        conditions = []
        params: List[Any] = []

        if time_range_minutes is not None and time_range_minutes > 0:
            cutoff = time.time() - (time_range_minutes * 60.0)
            conditions.append("epoch_time >= ?")
            params.append(cutoff)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        limit_clause = f"LIMIT {int(limit)}" if limit else ""

        sql = f"""
            SELECT * FROM resource_history
            {where_clause}
            ORDER BY epoch_time ASC
            {limit_clause}
        """

        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                rows = [dict(row) for row in cursor.fetchall()]
                return rows
            finally:
                conn.close()

    def get_statistics(self, time_range_minutes: Optional[float] = None) -> Dict[str, Any]:
        """
        Compute Min, Max, and Average aggregate statistics over the chosen time range.
        """
        conditions = []
        params: List[Any] = []

        if time_range_minutes is not None and time_range_minutes > 0:
            cutoff = time.time() - (time_range_minutes * 60.0)
            conditions.append("epoch_time >= ?")
            params.append(cutoff)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        sql = f"""
            SELECT
                COUNT(*) as count,
                MIN(cpu_percent) as min_cpu,
                MAX(cpu_percent) as max_cpu,
                AVG(cpu_percent) as avg_cpu,
                MIN(mem_percent) as min_mem,
                MAX(mem_percent) as max_mem,
                AVG(mem_percent) as avg_mem,
                MIN(swap_percent) as min_swap,
                MAX(swap_percent) as max_swap,
                AVG(swap_percent) as avg_swap,
                MAX(disk_read_kbs) as max_disk_read,
                AVG(disk_read_kbs) as avg_disk_read,
                MAX(disk_write_kbs) as max_disk_write,
                AVG(disk_write_kbs) as avg_disk_write,
                MAX(net_down_kbs) as max_net_down,
                AVG(net_down_kbs) as avg_net_down,
                MAX(net_up_kbs) as max_net_up,
                AVG(net_up_kbs) as avg_net_up
            FROM resource_history
            {where_clause}
        """

        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                row = cursor.fetchone()
                if not row or row["count"] == 0:
                    return {"count": 0}

                return {
                    "count": row["count"],
                    "min_cpu": round(row["min_cpu"] or 0.0, 1),
                    "max_cpu": round(row["max_cpu"] or 0.0, 1),
                    "avg_cpu": round(row["avg_cpu"] or 0.0, 1),
                    "min_mem": round(row["min_mem"] or 0.0, 1),
                    "max_mem": round(row["max_mem"] or 0.0, 1),
                    "avg_mem": round(row["avg_mem"] or 0.0, 1),
                    "min_swap": round(row["min_swap"] or 0.0, 1),
                    "max_swap": round(row["max_swap"] or 0.0, 1),
                    "avg_swap": round(row["avg_swap"] or 0.0, 1),
                    "max_disk_read": round(row["max_disk_read"] or 0.0, 1),
                    "avg_disk_read": round(row["avg_disk_read"] or 0.0, 1),
                    "max_disk_write": round(row["max_disk_write"] or 0.0, 1),
                    "avg_disk_write": round(row["avg_disk_write"] or 0.0, 1),
                    "max_net_down": round(row["max_net_down"] or 0.0, 1),
                    "avg_net_down": round(row["avg_net_down"] or 0.0, 1),
                    "max_net_up": round(row["max_net_up"] or 0.0, 1),
                    "avg_net_up": round(row["avg_net_up"] or 0.0, 1),
                }
            finally:
                conn.close()

    def cleanup_old_records(
        self,
        retention_days: int = 7,
        max_records: int = 50000,
    ) -> int:
        """
        Prune records older than retention_days or beyond max_records to prevent disk bloat.
        Returns number of deleted rows.
        """
        deleted_count = 0
        with self.lock:
            conn = self._get_connection()
            try:
                with conn:
                    # 1. Delete by age
                    if retention_days > 0:
                        cutoff_epoch = time.time() - (retention_days * 86400.0)
                        cur = conn.execute(
                            "DELETE FROM resource_history WHERE epoch_time < ?",
                            (cutoff_epoch,),
                        )
                        deleted_count += cur.rowcount

                    # 2. Delete excess records if still exceeding max_records
                    cur = conn.execute("SELECT COUNT(*) FROM resource_history")
                    total = cur.fetchone()[0]
                    if total > max_records:
                        excess = total - max_records
                        cur = conn.execute(
                            f"""
                            DELETE FROM resource_history WHERE id IN (
                                SELECT id FROM resource_history ORDER BY epoch_time ASC LIMIT {excess}
                            )
                            """
                        )
                        deleted_count += cur.rowcount

                # VACUUM must run outside the transaction block
                if deleted_count > 0:
                    conn.isolation_level = None  # autocommit mode
                    conn.execute("VACUUM")

                return deleted_count
            except sqlite3.Error as e:
                print(f"[Database Cleanup Error]: {e}")
                return 0
            finally:
                conn.close()

    def export_to_csv(self, filepath: str, time_range_minutes: Optional[float] = None) -> int:
        """
        Export historical records into a CSV file.
        Matches the columns from the original monitor:
        FIELDS = ["timestamp", "cpu_percent", "mem_percent", "mem_used_mb",
                  "mem_available_mb", "swap_percent", "disk_usage_percent",
                  "disk_read_kbs", "disk_write_kbs", "net_up_kbs", "net_down_kbs"]
        """
        rows = self.get_history(time_range_minutes=time_range_minutes)
        if not rows:
            return 0

        fields = [
            "timestamp", "cpu_percent", "mem_percent", "mem_used_mb",
            "mem_available_mb", "swap_percent", "disk_usage_percent",
            "disk_read_kbs", "disk_write_kbs", "net_up_kbs", "net_down_kbs"
        ]

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        return len(rows)

    def get_record_count(self) -> int:
        """Return total number of saved records."""
        with self.lock:
            conn = self._get_connection()
            try:
                cur = conn.execute("SELECT COUNT(*) FROM resource_history")
                return cur.fetchone()[0]
            finally:
                conn.close()
