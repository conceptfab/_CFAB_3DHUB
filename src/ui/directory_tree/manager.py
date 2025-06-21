"""
Manager drzewa katalogów - zrefaktoryzowany.
ETAP: REFAKTORYZACJA UKOŃCZONA - Podzielony na komponenty.
"""

import logging
import os
import subprocess
import time
from typing import List, Optional

from PyQt6.QtCore import QDir, QModelIndex, Qt, QThreadPool, QTimer, QItemSelectionModel
from PyQt6.QtGui import (
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QFileSystemModel,
)
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QToolBar,
    QTreeView,
    QWidget,
)

from src.factories.worker_factory import UIWorkerFactory
from src.logic import file_operations
from src.utils.path_validator import PathValidator

from .cache import FolderStatsCache
from .data_classes import FolderStatistics
from .data_manager import DirectoryTreeDataManager
from .delegates import DropHighlightDelegate

# Importy refaktoryzowanych komponentów
from .event_handler import DirectoryTreeEventHandler
from .drag_drop_handler import DirectoryTreeDragDropHandler
from .operations_manager import DirectoryTreeOperationsManager
from .stats_manager import DirectoryTreeStatsManager
from .ui_handler import DirectoryTreeUIHandler

# Importy z nowych modułów
from .models import FolderStatsDelegate, StatsProxyModel
from .throttled_scheduler import ThrottledWorkerScheduler
from .worker_coordinator import DirectoryTreeWorkerCoordinator
from .workers import FolderScanWorker, FolderStatisticsWorker

logger = logging.getLogger(__name__)


class DirectoryTreeManager:
    """
    Główny manager drzewa katalogów - zrefaktoryzowany.
    Koordynuje pracę wszystkich komponentów.
    """

    def __init__(self, folder_tree: QTreeView, parent_window):
        self.folder_tree = folder_tree
        self.parent_window = parent_window
        self.worker_factory = UIWorkerFactory()
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        # Filtrowanie, aby pokazywać tylko katalogi
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)

        # ==================== INICJALIZACJA KOMPONENTÓW ====================
        # Cache statystyk folderów
        self._folder_stats_cache = FolderStatsCache(
            max_entries=100, timeout_seconds=300
        )

        # Scheduler dla workerów
        self._worker_scheduler = ThrottledWorkerScheduler(
            max_concurrent_workers=2, base_delay_ms=150
        )

        # Inicjalizacja komponentów refaktoryzacji
        self.data_manager = DirectoryTreeDataManager(
            cache=self._folder_stats_cache, working_directory=""
        )
        self.event_handler = DirectoryTreeEventHandler(self)
        self.worker_coordinator = DirectoryTreeWorkerCoordinator(self._worker_scheduler)
        
        # Inicjalizacja nowych komponentów
        self.drag_drop_handler = DirectoryTreeDragDropHandler(self)
        self.operations_manager = DirectoryTreeOperationsManager(self)
        self.stats_manager = DirectoryTreeStatsManager(self)
        self.ui_handler = DirectoryTreeUIHandler(self)

        # Proxy model do filtrowania ukrytych folderów I wyświetlania statystyk
        self.proxy_model = StatsProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterKeyColumn(0)
        self.setup_folder_filtering()
        logger.debug("DirectoryTreeManager: Utworzono StatsProxyModel")

        # Użyj proxy model zamiast bezpośrednio file system model
        self.folder_tree.setModel(self.proxy_model)
        self.folder_tree.setRootIndex(
            self.proxy_model.mapFromSource(self.model.index(QDir.currentPath()))
        )

        # ==================== KONFIGURACJA UI ====================
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(
            self.show_folder_context_menu
        )

        # Ustawienia Drag and Drop
        self.folder_tree.setDragEnabled(False)  # Drzewo samo nie inicjuje przeciągania
        self.folder_tree.setAcceptDrops(True)
        self.folder_tree.setDropIndicatorShown(True)  # Standardowy wskaźnik linii
        self.folder_tree.setDragDropMode(QTreeView.DragDropMode.DropOnly)

        # Inicjalizacja dla podświetlania celu upuszczania
        self.highlighted_drop_index = QModelIndex()

        # WŁĄCZ DropHighlightDelegate dla podświetlania podczas drag and drop
        self.drop_highlight_delegate = DropHighlightDelegate(self, self.folder_tree)
        self.folder_tree.setItemDelegate(self.drop_highlight_delegate)
        logger.debug(
            f"DELEGATE SETUP: Ustawiono delegate: {self.drop_highlight_delegate}"
        )
        logger.debug(
            f"DELEGATE SETUP: Aktualny delegate: {self.folder_tree.itemDelegate()}"
        )

        self.current_scan_path: str | None = None
        self._main_working_directory = None

        # ==================== POŁĄCZENIE SYGNAŁÓW ====================
        self._connect_signals()
        self.drag_drop_handler.setup_drag_and_drop_handlers()

    def _connect_signals(self):
        """Łączy sygnały Qt z handlerami event_handler."""
        # Obsługa kliknięć przez event handler zamiast bezpośrednio
        self.folder_tree.clicked.connect(self.event_handler.handle_item_clicked)
        # Obsługa rozwijania przez event handler
        self.folder_tree.expanded.connect(self.event_handler.handle_item_expanded)
        # Dodaj obsługę podwójnego kliknięcia
        self.folder_tree.doubleClicked.connect(self.event_handler.handle_double_click)

    # ==================== METODY DELEGUJĄCE DO KOMPONENTÓW ====================

    def get_cached_folder_statistics(
        self, folder_path: str
    ) -> Optional[FolderStatistics]:
        """Pobiera statystyki z cache - deleguje do data_manager."""
        return self.data_manager.load_directory_data(folder_path)

    def cache_folder_statistics(self, folder_path: str, stats: FolderStatistics):
        """Zapisuje statystyki do cache - deleguje do data_manager."""
        self.data_manager.update_directory_stats(folder_path, stats)

    def invalidate_folder_cache(self, folder_path: str):
        """Usuwa statystyki z cache - deleguje do data_manager."""
        self.data_manager.refresh_directory(folder_path)

    def invalidate_visible_folders_cache(self):
        """Invaliduje cache widocznych folderów - deleguje do data_manager."""
        self.data_manager.invalidate_visible_folders_cache()

    # ==================== METODY FUNKCJONALNOŚCI ====================

    def setup_folder_filtering(self):
        """Konfiguruje filtrowanie ukrytych folderów."""

        def filter_folders(source_row: int, source_parent: QModelIndex) -> bool:
            index = self.model.index(source_row, 0, source_parent)
            if not index.isValid():
                return True

            folder_name = self.model.fileName(index)
            return self.should_show_folder(folder_name)

        # Ustaw funkcję filtrującą w naszym custom proxy model
        if hasattr(self.proxy_model, "set_filter_function"):
            self.proxy_model.set_filter_function(filter_folders)
        else:
            # Fallback dla standardowego proxy model
            self.proxy_model.filterAcceptsRow = filter_folders

    def should_show_folder(self, folder_name: str) -> bool:
        """Określa czy folder powinien być widoczny w drzewie."""
        hidden_folders = {
            ".app_metadata",
            "__pycache__",
            ".git",
            ".svn",
            ".hg",
            "node_modules",
            ".alg_meta",
            # BEZPIECZEŃSTWO: Blokada przeglądania folderów tekstur
            "tex",
            "textures",
            "texture",
        }
        return folder_name not in hidden_folders

    def setup_expand_collapse_controls(self) -> QWidget:
        """Dodaje kontrolki zwijania/rozwijania folderów."""
        controls_widget = QWidget()
        layout = QHBoxLayout()

        toolbar = QToolBar()
        expand_all_action = toolbar.addAction("Rozwiń wszystkie")
        collapse_all_action = toolbar.addAction("Zwiń wszystkie")

        expand_all_action.triggered.connect(self.folder_tree.expandAll)
        collapse_all_action.triggered.connect(self.folder_tree.collapseAll)

        layout.addWidget(toolbar)
        controls_widget.setLayout(layout)

        return controls_widget

    def create_expand_collapse_buttons(self):
        """
        Tworzy przyciski do rozwijania i zwijania wszystkich folderów.

        Returns:
            tuple: (przycisk_rozwiń, przycisk_zwiń)
        """
        expand_button = QPushButton("Rozwiń")
        collapse_button = QPushButton("Zwiń")

        expand_button.clicked.connect(self.folder_tree.expandAll)
        collapse_button.clicked.connect(self.folder_tree.collapseAll)

        # Ustaw style dla przycisków - bardziej kompaktowe
        button_style = """
            QPushButton {
                background-color: #2D2D30;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
                padding: 2px 4px;
                font-size: 10px;
                min-height: 20px;
                max-height: 20px;
            }
            QPushButton:hover {
                background-color: #3E3E42;
                border: 1px solid #007ACC;
            }
            QPushButton:pressed {
                background-color: #007ACC;
                color: white;
            }
        """
        expand_button.setStyleSheet(button_style)
        collapse_button.setStyleSheet(button_style)

        # Ustaw kompaktowe rozmiary
        expand_button.setFixedHeight(20)
        collapse_button.setFixedHeight(20)

        return expand_button, collapse_button

    def start_background_stats_calculation(self):
        """Deleguje do stats_manager."""
        return self.stats_manager.start_background_stats_calculation()

    def _get_visible_folders(self) -> List[str]:
        """Deleguje do stats_manager."""
        return self.stats_manager._get_visible_folders()

    def _create_stats_worker(self, folder_path: str):
        """Deleguje do stats_manager."""
        return self.stats_manager._create_stats_worker(folder_path)

    def _calculate_stats_async_silent(self, folder_path: str):
        """Deleguje do stats_manager."""
        return self.stats_manager._calculate_stats_async_silent(folder_path)

    def _refresh_folder_display(self, folder_path: str):
        """Deleguje do stats_manager."""
        return self.stats_manager._refresh_folder_display(folder_path)

    def open_folder_in_explorer(self, folder_path: str):
        """Deleguje do ui_handler."""
        return self.ui_handler.open_folder_in_explorer(folder_path)

    def calculate_folder_statistics_async(self, folder_path: str, callback=None):
        """Deleguje do stats_manager."""
        return self.stats_manager.calculate_folder_statistics_async(folder_path, callback)

    def show_folder_context_menu(self, position):
        """Deleguje do ui_handler."""
        return self.ui_handler.show_folder_context_menu(position)

    def show_folder_statistics(self, folder_path: str):
        """Deleguje do stats_manager."""
        return self.stats_manager.show_folder_statistics(folder_path)

    def _display_folder_statistics(self, stats: FolderStatistics, folder_path: str):
        """Deleguje do stats_manager."""
        return self.stats_manager._display_folder_statistics(stats, folder_path)

    def create_folder(self, parent_folder_path: str):
        """Deleguje do operations_manager."""
        return self.operations_manager.create_folder(parent_folder_path)

    def rename_folder(self, folder_path: str):
        """Deleguje do operations_manager."""
        return self.operations_manager.rename_folder(folder_path)

    def delete_folder(self, folder_path: str, current_working_directory: str):
        """Deleguje do operations_manager."""
        return self.operations_manager.delete_folder(folder_path, current_working_directory)

    # Handle methods przeniesione do operations_manager

    def refresh_entire_tree(self):
        """Odświeża całe drzewo katalogów - używa data_manager do czyszczenia cache."""
        try:
            # Wyczyść cache przez data_manager
            self.data_manager.clear_all_cache()

            # Anuluj wszystkie aktywne workery
            self.worker_coordinator.cancel_all_workers()

            # Odśwież model
            self.model.setRootPath(self.model.rootPath())

            # Przefiltruj na nowo
            self.proxy_model.invalidateFilter()

            logger.info("Odświeżono całe drzewo katalogów z wyczyszczeniem cache")
        except Exception as e:
            logger.error(f"Błąd odświeżania drzewa: {e}")

    def refresh_file_pairs_after_folder_operation(self, current_working_directory: str):
        """Deleguje do ui_handler."""
        return self.ui_handler.refresh_file_pairs_after_folder_operation(current_working_directory)

    def folder_tree_item_clicked(self, proxy_index, current_working_directory: str):
        """Deleguje do ui_handler."""
        return self.ui_handler.folder_tree_item_clicked(proxy_index, current_working_directory)

    def get_source_index_from_proxy(self, proxy_index: QModelIndex) -> QModelIndex:
        """Mapuje proxy index na source index."""
        return self.proxy_model.mapToSource(proxy_index)

    def get_proxy_index_from_source(self, source_index: QModelIndex) -> QModelIndex:
        """Mapuje source index na proxy index."""
        return self.proxy_model.mapFromSource(source_index)
    
    def _start_worker(self, worker):
        """Uruchamia worker w thread pool."""
        QThreadPool.globalInstance().start(worker)

    # Drag and drop methods przeniesione do drag_drop_handler

    def force_calculate_all_stats_async(self):
        """Deleguje do stats_manager."""
        return self.stats_manager.force_calculate_all_stats_async()

    def _force_recalculate_folder_stats(self, folder_path: str):
        """Deleguje do stats_manager."""
        return self.stats_manager._force_recalculate_folder_stats(folder_path)

    def init_directory_tree_async(self, current_working_directory: str):
        """Inicjalizuje drzewo katalogów asynchronicznie."""
        try:
            self._main_working_directory = current_working_directory

            def on_folders_scanned(folders_with_files):
                # Ustaw główny folder roboczy jako root
                self.model.setRootPath(current_working_directory)
                root_index = self.model.index(current_working_directory)
                proxy_root_index = self.proxy_model.mapFromSource(root_index)
                self.folder_tree.setRootIndex(proxy_root_index)

                # Rozwiń foldery z plikami
                self._expand_folders_with_files(folders_with_files)

                # Rozpocznij obliczanie statystyk w tle
                self.start_background_stats_calculation()

                logger.info(
                    f"Zainicjalizowano drzewo katalogów dla: {current_working_directory}"
                )

            def on_scan_error(error_msg):
                logger.error(f"Błąd skanowania folderów: {error_msg}")
                # Fallback - ustaw root bez rozwijania
                self.model.setRootPath(current_working_directory)
                root_index = self.model.index(current_working_directory)
                proxy_root_index = self.proxy_model.mapFromSource(root_index)
                self.folder_tree.setRootIndex(proxy_root_index)

            # Uruchom worker do skanowania folderów
            worker = FolderScanWorker(current_working_directory)
            worker.custom_signals.finished.connect(on_folders_scanned)
            worker.custom_signals.error.connect(on_scan_error)

            self._start_worker(worker)

        except Exception as e:
            logger.error(f"Błąd inicjalizacji drzewa katalogów: {e}")

    def init_directory_tree(self, current_working_directory: str):
        """Inicjalizuje drzewo katalogów synchronicznie."""
        try:
            self._main_working_directory = current_working_directory

            # Ustaw root path
            self.model.setRootPath(current_working_directory)
            root_index = self.model.index(current_working_directory)
            proxy_root_index = self.proxy_model.mapFromSource(root_index)
            self.folder_tree.setRootIndex(proxy_root_index)

            # Skanuj foldery z plikami
            folders_with_files = self._scan_folders_with_files(
                current_working_directory
            )

            # Rozwiń foldery z plikami
            self._expand_folders_with_files(folders_with_files)

            # Rozpocznij obliczanie statystyk w tle
            self.start_background_stats_calculation()

            logger.info(
                f"Zainicjalizowano drzewo katalogów (sync) dla: {current_working_directory}"
            )

        except Exception as e:
            logger.error(f"Błąd inicjalizacji drzewa katalogów: {e}")

    def _scan_folders_with_files(self, root_folder: str) -> List[str]:
        """Skanuje foldery w poszukiwaniu tych zawierających pliki."""
        folders_with_files = []
        try:
            for root, dirs, files in os.walk(root_folder):
                # Pomiń ukryte foldery
                dirs[:] = [
                    d
                    for d in dirs
                    if not d.startswith(".") and self.should_show_folder(d)
                ]

                # Jeśli folder ma pliki, dodaj go do listy
                if files:
                    folders_with_files.append(root)

                # Ogranicz głębokość skanowania
                depth = root[len(root_folder) :].count(os.sep)
                if depth >= 3:
                    dirs.clear()

        except Exception as e:
            logger.error(f"Błąd skanowania folderów: {e}")

        return folders_with_files

    def _expand_folders_with_files(self, folders_with_files: List[str]):
        """Rozwija foldery zawierające pliki w drzewie."""
        try:
            for folder_path in folders_with_files:
                source_index = self.model.index(folder_path)
                if source_index.isValid():
                    proxy_index = self.proxy_model.mapFromSource(source_index)
                    if proxy_index.isValid():
                        self.folder_tree.expand(proxy_index)

        except Exception as e:
            logger.error(f"Błąd rozwijania folderów: {e}")

    def refresh_folder_only(self, folder_path: str) -> None:
        """Odświeża konkretny folder w drzewie katalogów."""
        try:
            normalized_path = PathValidator.normalize_path(folder_path)
            if not os.path.exists(normalized_path):
                logger.warning(f"Folder nie istnieje: {normalized_path}")
                return

            # Invalidate cache for this folder
            self.invalidate_folder_cache(normalized_path)

            # Refresh model
            source_index = self.model.index(normalized_path)
            if source_index.isValid():
                self.model.dataChanged.emit(source_index, source_index)
                logger.debug(f"Odświeżono folder: {normalized_path}")
        except Exception as e:
            logger.error(f"Błąd odświeżania folderu {folder_path}: {e}")

    def init_directory_tree_without_expansion(self, current_working_directory: str):
        """
        Inicjalizuje drzewo katalogów bez automatycznego rozwijania folderów.
        Używane przy starcie aplikacji i zmianie głównego folderu roboczego.

        Args:
            current_working_directory: Ścieżka do katalogu roboczego
        """
        if not current_working_directory or not os.path.isdir(current_working_directory):
            logger.warning(f"Nieprawidłowy katalog: {current_working_directory}")
            return

        # Normalizacja ścieżki
        current_working_directory = PathValidator.normalize_path(current_working_directory)
        self._main_working_directory = current_working_directory
        self.data_manager.set_working_directory(current_working_directory)

        # Ustaw root path w modelu
        source_index = self.model.setRootPath(current_working_directory)
        proxy_index = self.proxy_model.mapFromSource(source_index)
        self.folder_tree.setRootIndex(proxy_index)

        # Pokaż tylko jedną kolumnę z nazwami folderów
        for i in range(1, self.model.columnCount()):
            self.folder_tree.hideColumn(i)

        # Ustaw nagłówek
        self.folder_tree.header().hide()

        # Zapisz ścieżkę jako aktualną
        self.current_scan_path = current_working_directory
        logger.info(f"Ustawiono drzewo katalogów bez rozwijania: {current_working_directory}")

    def set_current_directory(self, directory_path: str):
        """
        Ustawia aktualny katalog bez resetowania całego drzewa.
        Używane przy kliknięciu w ulubiony folder.
        
        Args:
            directory_path: Ścieżka do katalogu
        """
        if not directory_path or not os.path.isdir(directory_path):
            logger.warning(f"Nieprawidłowy katalog: {directory_path}")
            return
            
        # Normalizacja ścieżki
        directory_path = PathValidator.normalize_path(directory_path)
        
        # Ustaw jako bieżący katalog roboczy
        self._main_working_directory = directory_path
        self.data_manager.set_working_directory(directory_path)
        
        try:
            # KLUCZOWE: Upewnij się, że folder jest widoczny w drzewie
            # Znajdź ścieżkę w modelu i rozwiń wszystkie foldery nadrzędne
            
            # 1. Znajdź indeks dla ścieżki w modelu
            source_index = self.model.index(directory_path)
            if not source_index.isValid():
                logger.warning(f"Nie można znaleźć indeksu dla ścieżki: {directory_path}")
                return
                
            # 2. Rozwiń wszystkie foldery nadrzędne
            parent_path = os.path.dirname(directory_path)
            parent_index = self.model.index(parent_path)
            if parent_index.isValid():
                proxy_parent_index = self.proxy_model.mapFromSource(parent_index)
                if proxy_parent_index.isValid():
                    self.folder_tree.expand(proxy_parent_index)
            
            # 3. Mapuj indeks do proxy modelu
            proxy_index = self.proxy_model.mapFromSource(source_index)
            if not proxy_index.isValid():
                logger.warning(f"Nie można zmapować indeksu dla ścieżki: {directory_path}")
                return
                
            # 4. Zaznacz folder w drzewie i przewiń do niego
            self.folder_tree.setCurrentIndex(proxy_index)
            self.folder_tree.scrollTo(proxy_index, QTreeView.ScrollHint.PositionAtCenter)
            
            # 5. Wyraźnie zaznacz folder (wizualnie)
            self.folder_tree.selectionModel().select(
                proxy_index, 
                QItemSelectionModel.SelectionFlag.ClearAndSelect
            )
            
            # 6. Rozwiń folder
            self.folder_tree.expand(proxy_index)
            
            # 7. Zapisz jako aktualną ścieżkę
            self.current_scan_path = directory_path
            logger.info(f"Ustawiono aktualny katalog: {directory_path}")
            
            # 8. Odśwież statystyki dla tego folderu
            self.invalidate_folder_cache(directory_path)
            self._calculate_stats_async_silent(directory_path)
            
            # 9. Odśwież widok drzewa
            self.folder_tree.update()
            
        except Exception as e:
            logger.error(f"Błąd podczas ustawiania katalogu: {e}", exc_info=True)
