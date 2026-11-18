"""
SYSCORE — Utility Functions and Helpers
Unit formatting, calculations, and state-based alert management.
"""
from dataclasses import dataclass
from datetime import datetime
import time
from typing import Dict, List, Optional


def format_bytes(bytes_value: float, precision: int = 1) -> str:
    """
    Format a byte count into human-readable representation (B, KB, MB, GB, TB).
    """
    if bytes_value is None or bytes_value < 0:
        return "0.0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    value = float(bytes_value)
    idx = 0
    while value >= 1024.0 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    return f"{value:.{precision}f} {units[idx]}"


def format_rate(kbs_value: float, precision: int = 1) -> str:
    """
    Format a transfer rate given in KB/s into KB/s or MB/s.
    """
    if kbs_value is None or kbs_value < 0:
        return "0.0 KB/s"
    if kbs_value >= 1024.0:
        return f"{kbs_value / 1024.0:.{precision}f} MB/s"
    return f"{kbs_value:.{precision}f} KB/s"


def format_percent(pct: float, precision: int = 1) -> str:
    """Format percentage value with symbol."""
    if pct is None:
        return "0.0%"
    return f"{pct:.{precision}f}%"


def format_uptime(seconds: float) -> str:
    """Format total seconds into human-readable uptime string."""
    if not seconds or seconds < 0:
        return "0s"
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts[:3])


def format_timestamp(ts: Optional[datetime] = None) -> str:
    """Return formatted timestamp."""
    if ts is None:
        ts = datetime.now()
    return ts.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class AlertEvent:
    metric: str
    current_value: float
    threshold: float
    message: str
    severity: str  # "warning" or "critical"
    timestamp: str


class AlertManager:
    """
    Manages threshold monitoring with cooldown and state tracking
    to prevent repetitive alert spamming during continuous threshold violations.
    """
    def __init__(
        self,
        cpu_threshold: float = 85.0,
        ram_threshold: float = 85.0,
        disk_threshold: float = 90.0,
        cooldown_seconds: float = 30.0,
    ):
        self.cpu_threshold = cpu_threshold
        self.ram_threshold = ram_threshold
        self.disk_threshold = disk_threshold
        self.cooldown_seconds = cooldown_seconds

        # Last time an alert fired per metric
        self._last_alert_time: Dict[str, float] = {}
        # Active warning status per metric
        self._active_status: Dict[str, bool] = {
            "cpu": False,
            "ram": False,
            "disk": False,
        }

    def check_thresholds(self, sample: dict) -> List[AlertEvent]:
        """
        Evaluate a resource sample against configured thresholds.
        Returns newly triggered alert events adhering to cooldown.
        """
        now = time.time()
        new_alerts: List[AlertEvent] = []

        metrics = [
            ("cpu", sample.get("cpu_percent", 0.0), self.cpu_threshold, "CPU"),
            ("ram", sample.get("mem_percent", 0.0), self.ram_threshold, "RAM"),
            ("disk", sample.get("disk_usage_percent", 0.0), self.disk_threshold, "Disk"),
        ]

        for key, val, threshold, label in metrics:
            is_violating = val >= threshold
            last_fired = self._last_alert_time.get(key, 0.0)
            in_cooldown = (now - last_fired) < self.cooldown_seconds

            if is_violating:
                # Trigger if newly violated or cooldown elapsed
                if not self._active_status[key] or not in_cooldown:
                    severity = "critical" if val >= (threshold + 10.0) else "warning"
                    event = AlertEvent(
                        metric=key,
                        current_value=val,
                        threshold=threshold,
                        message=f"{label} usage at {val:.1f}% exceeded threshold of {threshold:.0f}%",
                        severity=severity,
                        timestamp=datetime.now().strftime("%H:%M:%S"),
                    )
                    new_alerts.append(event)
                    self._last_alert_time[key] = now
                self._active_status[key] = True
            else:
                self._active_status[key] = False

        return new_alerts

    def get_active_violations(self, sample: dict) -> List[str]:
        """
        Return immediate list of current metrics exceeding threshold
        for persistent UI warning banners.
        """
        active = []
        cpu = sample.get("cpu_percent", 0.0)
        if cpu >= self.cpu_threshold:
            active.append(f"High CPU: {cpu:.1f}% (limit {self.cpu_threshold:.0f}%)")
        ram = sample.get("mem_percent", 0.0)
        if ram >= self.ram_threshold:
            active.append(f"High RAM: {ram:.1f}% (limit {self.ram_threshold:.0f}%)")
        disk = sample.get("disk_usage_percent", 0.0)
        if disk >= self.disk_threshold:
            active.append(f"High Disk: {disk:.1f}% (limit {self.disk_threshold:.0f}%)")
        return active
