"""
SYSCORE — Configuration and Theme Definitions
System Resource Monitor & OS Resource Management
"""
import os
import sys

# Base directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ASSETS_DIR, exist_ok=True)

# Application metadata
APP_NAME = "SYSCORE"
APP_SUBTITLE = "System Resource Monitor & OS Resource Management"
APP_VERSION = "2.0.0"
APP_WINDOW_TITLE = f"{APP_NAME} — {APP_SUBTITLE}"

# Database and file paths
DB_PATH = os.path.join(DATA_DIR, "syscore.db")
DEFAULT_CSV_PATH = os.path.join(DATA_DIR, "resource_log.csv")

# Monitoring configuration defaults
DEFAULT_SAMPLE_INTERVAL = 1.0  # seconds
MIN_SAMPLE_INTERVAL = 0.5
MAX_SAMPLE_INTERVAL = 10.0
LIVE_GRAPH_POINTS = 60  # Number of historical points shown on live rolling chart
PROCESS_REFRESH_INTERVAL = 2.0  # seconds

# Data retention defaults
DEFAULT_RETENTION_DAYS = 7
MAX_HISTORICAL_RECORDS = 50000

# Alert Thresholds (percentages)
DEFAULT_CPU_ALERT_THRESHOLD = 85.0
DEFAULT_RAM_ALERT_THRESHOLD = 85.0
DEFAULT_DISK_ALERT_THRESHOLD = 90.0
ALERT_COOLDOWN_SECONDS = 30.0  # Prevent repetitive alert triggers

# Critical system processes that must NEVER be terminated
PROTECTED_PROCESS_NAMES = {
    "systemd", "init", "kthreadd", "systemd-journald", "systemd-udevd",
    "dbus-daemon", "polkitd", "login", "sshd", "Xorg", "Xvfb",
    "kwin_wayland", "gnome-shell", "plasma-workspace", "pipewire",
    "pulseaudio", "bash", "zsh", "fish", "sudo"
}
PROTECTED_PIDS = {0, 1, 2, os.getpid()}
if hasattr(os, "getppid"):
    PROTECTED_PIDS.add(os.getppid())

# UI Theme: Modern Developer Workstation (Dark Deep Navy / Charcoal)
THEME = {
    "bg_main": "#0d1117",         # Deep dark charcoal/navy background
    "bg_sidebar": "#161b22",      # Sidebar panel background
    "bg_card": "#161b22",         # Metric card background
    "bg_card_hover": "#1f242c",   # Metric card on hover
    "bg_card_inner": "#0d1117",   # Inner nested frame
    "border": "#30363d",          # Card & frame border
    "border_highlight": "#58a6ff",# Focused/active border
    
    # Text colors
    "text_primary": "#f0f6fc",    # Main heading and values
    "text_secondary": "#8b949e",  # Subtitles and unit labels
    "text_muted": "#6e7681",      # Inactive / footnote
    
    # Resource accent colors (consistent across cards and charts)
    "cpu": "#58a6ff",             # Electric Blue
    "cpu_light": "#1f6feb",
    "ram": "#3fb950",             # Emerald Green
    "ram_light": "#238636",
    "swap": "#d29922",            # Amber / Warm Gold
    "disk": "#bc8cff",            # Violet / Purple
    "disk_write": "#a371f7",
    "net_down": "#39c5bb",        # Cyan / Turquoise
    "net_up": "#d29922",          # Warm Yellow-Orange
    
    # Status & alerts
    "status_ok": "#3fb950",
    "status_warn": "#d29922",
    "status_error": "#f85149",
    "status_idle": "#8b949e",
    
    # Interactive controls
    "btn_primary": "#1f6feb",
    "btn_primary_hover": "#388bfd",
    "btn_danger": "#da3633",
    "btn_danger_hover": "#f85149",
    "btn_secondary": "#21262d",
    "btn_secondary_hover": "#30363d",
}

# Matplotlib dark style dictionary
MPL_STYLE = {
    "figure.facecolor": THEME["bg_card"],
    "axes.facecolor": THEME["bg_card_inner"],
    "axes.edgecolor": THEME["border"],
    "axes.labelcolor": THEME["text_secondary"],
    "xtick.color": THEME["text_secondary"],
    "ytick.color": THEME["text_secondary"],
    "grid.color": "#21262d",
    "grid.linestyle": "--",
    "grid.alpha": 0.5,
    "legend.facecolor": THEME["bg_card"],
    "legend.edgecolor": THEME["border"],
    "legend.labelcolor": THEME["text_primary"],
    "text.color": THEME["text_primary"],
}


def bootstrap_environment():
    """
    Configure environment variables for cross-platform compatibility,
    including virtual environment library resolution, Tkinter fallback,
    and Matplotlib temporary cache directory.
    """
    # Configure Matplotlib writable cache
    if "MPLCONFIGDIR" not in os.environ:
        mpl_dir = os.path.join(DATA_DIR, ".mplcache")
        try:
            os.makedirs(mpl_dir, exist_ok=True)
            os.environ["MPLCONFIGDIR"] = mpl_dir
        except Exception:
            os.environ["MPLCONFIGDIR"] = "/tmp/mplconfig"

    # Virtual environment lib detection for Tkinter shared libraries
    venv_dir = os.path.join(BASE_DIR, ".venv")
    venv_lib = os.path.join(venv_dir, "lib")
    if os.path.exists(venv_lib):
        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        if venv_lib not in current_ld:
            os.environ["LD_LIBRARY_PATH"] = f"{venv_lib}:{current_ld}" if current_ld else venv_lib
        
        tk_dir = os.path.join(venv_lib, "tk8.6")
        if os.path.exists(tk_dir):
            os.environ.setdefault("TK_LIBRARY", tk_dir)
        tcl_dir = os.path.join(venv_lib, "tcl8.6")
        if os.path.exists(tcl_dir):
            os.environ.setdefault("TCL_LIBRARY", tcl_dir)
