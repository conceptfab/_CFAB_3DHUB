"""
Główne okno aplikacji - zrefaktoryzowana wersja core.
🚀 ETAP 1: Refaktoryzacja MainWindow - podział na komponenty
"""

import logging
import os

from PyQt6.QtCore import Qt, QThread, QThreadPool, QTimer
from PyQt6.QtWidgets import (
    QMainWindow,
    QStatusBar,
    QProgressBar,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src import app_config
from src.controllers.main_window_controller import MainWindowController
from src.models.file_pair import FilePair
from src.ui.main_window_components.event_bus import get_event_bus
from src.ui.main_window_components.view_refresh_manager import ViewRefreshManager
from src.utils.logging_config import get_main_window_logger

# Nowe komponenty ETAP 1
from .ui_manager import UIManager
from .event_handler import EventHandler
from .worker_manager import WorkerManager
from .progress_manager import ProgressManager
from .file_operations_coordinator import FileOperationsCoordinator


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji CFAB_3DHUB - zrefaktoryzowana wersja.
    🚀 ETAP 1: Podział na wyspecjalizowane komponenty
    """

    def __init__(self):
        """
        Inicjalizuje główne okno aplikacji.
        """
        super().__init__()
        self._init_core_data()
        self._init_components()
        self._init_window_basic()
        self._init_ui_components()
        self._post_init_setup()

        self.logger.info("Główne okno aplikacji zostało zainicjalizowane (ETAP 1)")

    def _init_core_data(self):
        """Inicjalizuje podstawowe dane aplikacji."""
        # Logger
        self.logger = get_main_window_logger()
        
        # KRYTYCZNE: AppConfig musi być pierwsze
        self.app_config = app_config.AppConfig()

        # Event Bus i View Refresh Manager
        self.event_bus = get_event_bus()
        self.view_refresh_manager = ViewRefreshManager(self)

        # MVC Controller
        self.controller = MainWindowController(self)

        # Podstawowe dane wątków
        self.scan_thread = None
        self.scan_worker = None
        self.data_processing_thread = None
        self.data_processing_worker = None

    def _init_components(self):
        """Inicjalizuje wyspecjalizowane komponenty."""
        # 🚀 ETAP 1: Nowe wyspecjalizowane komponenty
        self.ui_manager = UIManager(self)
        self.event_handler = EventHandler(self)
        self.worker_manager = WorkerManager(self)
        self.progress_manager = ProgressManager(self)
        self.file_operations_coordinator = FileOperationsCoordinator(self)

    def _init_window_basic(self):
        """Inicjalizuje podstawowe właściwości okna."""
        # Timer do opóźnienia odświeżania galerii
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._update_gallery_view)

        # Konfiguracja rozmiaru miniatur
        self.min_thumbnail_size = self.app_config.min_thumbnail_size
        self.max_thumbnail_size = self.app_config.max_thumbnail_size
        self.initial_slider_position = 50

        # Oblicz current_thumbnail_size
        size_range = self.max_thumbnail_size - self.min_thumbnail_size
        if size_range <= 0:
            self.current_thumbnail_size = self.min_thumbnail_size
        else:
            self.current_thumbnail_size = self.min_thumbnail_size + int(
                (size_range * self.initial_slider_position) / 100
            )

        # Konfiguracja okna
        self.setWindowTitle("CFAB_3DHUB")
        self.setMinimumSize(
            self.app_config.window_min_width, self.app_config.window_min_height
        )

        # Thread pool
        self.thread_pool = QThreadPool.globalInstance()
        
        # Centralny widget i layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        self.main_layout.setSpacing(3)

    def _init_ui_components(self):
        """Inicjalizuje komponenty UI przez delegowanie do UIManager."""
        self.ui_manager.init_ui()

    def _post_init_setup(self):
        """Wykonuje końcowe ustawienia po inicjalizacji."""
        # Post-inicjalizacja managerów które wymagają już utworzonych komponentów UI
        self.ui_manager._post_init_managers()
        
        # Pokaż preferencje wczytane
        self._show_preferences_loaded_confirmation()
        
        # Zainicjalizuj drzewo katalogów
        default_folder = self.app_config.get("default_working_directory", "")
        if (
            default_folder
            and os.path.exists(default_folder)
            and os.path.isdir(default_folder)
        ):
            self.logger.debug(f"Inicjalizacja drzewa katalogów: {default_folder}")
            self.directory_tree_manager.init_directory_tree_without_expansion(
                default_folder
            )

    def _show_preferences_loaded_confirmation(self):
        """Pokazuje potwierdzenie wczytania preferencji."""
        # Delegowanie do UIManager
        self.ui_manager.show_preferences_loaded_confirmation()

    def _update_gallery_view(self):
        """Aktualizuje widok galerii."""
        # Delegowanie do ViewRefreshManager
        if hasattr(self, 'view_refresh_manager'):
            self.view_refresh_manager._refresh_gallery_view()

    # Delegowanie metod do odpowiednich komponentów
    def closeEvent(self, event):
        """Obsługa zamknięcia okna."""
        self.event_handler.handle_close_event(event)

    def resizeEvent(self, event):
        """Obsługa zmiany rozmiaru okna."""
        self.event_handler.handle_resize_event(event)

    def show_progress(self, percent: int, message: str):
        """Pokazuje postęp."""
        self.progress_manager.show_progress(percent, message)

    def hide_progress(self):
        """Ukrywa postęp."""
        self.progress_manager.hide_progress()

    def start_data_processing_worker(self, file_pairs: list[FilePair]):
        """Uruchamia worker przetwarzania danych."""
        self.worker_manager.start_data_processing_worker(file_pairs)

    def handle_file_drop_on_folder(self, source_file_paths: list[str], target_folder_path: str):
        """Obsługuje przeciągnięcie plików na folder."""
        self.file_operations_coordinator.handle_file_drop_on_folder(
            source_file_paths, target_folder_path
        )

    def perform_bulk_delete(self):
        """Wykonuje masowe usuwanie."""
        self.file_operations_coordinator.perform_bulk_delete()

    def perform_bulk_move(self):
        """Wykonuje masowe przenoszenie."""
        self.file_operations_coordinator.perform_bulk_move()

    # Metody wymagane przez inne komponenty - pozostają w MainWindow
    def refresh_all_views(self, new_selection=None):
        """Odświeża wszystkie widoki."""
        if hasattr(self, 'view_refresh_manager'):
            self.view_refresh_manager.request_refresh_all(force=False)

    def force_full_refresh(self):
        """Wymusza pełne odświeżenie."""
        if hasattr(self, 'view_refresh_manager'):
            self.view_refresh_manager.request_refresh_all(force=True)

    def change_directory(self, folder_path: str):
        """Zmienia katalog roboczy."""
        # Ta metoda pozostaje w MainWindow bo koordynuje wiele komponentów
        self.logger.info(f"Zmiana katalogu na: {folder_path}")
        
        # Delegowanie do odpowiednich komponentów
        if hasattr(self, 'controller'):
            self.controller.change_directory(folder_path) 