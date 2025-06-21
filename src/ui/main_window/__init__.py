"""
Pakiet main_window - komponenty refaktoryzacji MainWindow.
ETAP 1: Refaktoryzacja MainWindow na mniejsze komponenty.
"""

from .ui_manager import UIManager
from .progress_manager import ProgressManager

__all__ = ['UIManager', 'ProgressManager'] 