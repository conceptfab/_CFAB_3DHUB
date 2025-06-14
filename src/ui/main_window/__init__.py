"""
Pakiet main_window - zrefaktoryzowane komponenty głównego okna.
🚀 ETAP 1: Refaktoryzacja MainWindow - podział na komponenty
"""

from .main_window_core import MainWindow
from .ui_manager import UIManager
from .event_handler import EventHandler
from .worker_manager import WorkerManager
from .progress_manager import ProgressManager
from .file_operations_coordinator import FileOperationsCoordinator

__all__ = [
    'MainWindow',
    'UIManager',
    'EventHandler',
    'WorkerManager',
    'ProgressManager',
    'FileOperationsCoordinator',
] 