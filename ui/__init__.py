"""
SYSCORE UI Package
"""
from .app import SYSCOREApp
from .sidebar import Sidebar
from .dashboard import DashboardPage
from .process_page import ProcessPage
from .analytics_page import AnalyticsPage
from .system_info_page import SystemInfoPage
from .settings_page import SettingsPage

__all__ = [
    "SYSCOREApp",
    "Sidebar",
    "DashboardPage",
    "ProcessPage",
    "AnalyticsPage",
    "SystemInfoPage",
    "SettingsPage",
]
