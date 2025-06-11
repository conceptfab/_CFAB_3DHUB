"""
UI Components - moduły komponentów interfejsu użytkownika.
Refaktoryzacja MainWindow ETAP 2.
"""

from .event_handler import EventHandler
from .tab_manager import TabManager
from .ui_manager import UIManager

__all__ = ['UIManager', 'EventHandler', 'TabManager']
