"""
DirectoryTreeManager - refaktoryzowana wersja z wydzielonymi modułami.
Odpowiedzialności ograniczone do zarządzania UI drzewa folderów.
"""

import logging
import os
from typing import List, Optional

from PyQt6.QtCore import (
    QDir,
    QEvent,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    QTimer,
)
from PyQt6.QtGui import (
    QAction,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QFileSystemModel,
)
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMenu,
    QMessageBox,
    QStyledItemDelegate,
    QToolBar,
    QTreeView,
    QWidget,
)

from src.ui.folder_statistics_manager import FolderStatisticsManager, FolderStatistics
from src.ui.folder_operations_manager import FolderOperationsManager
from src.ui.delegates.workers import ScanFolderWorker
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class FolderStatsDelegate(QStyledItemDelegate):
    """Delegate do wyświetlania statystyk folderów w drzewie."""

    def __init__(self, stats_manager: FolderStatisticsManager, parent=None):
        super().__init__(parent)
        self.stats_manager = stats_manager

    def displayText(self, value, locale):
        """Customowe wyświetlanie statystyk."""
        index = self.parent().currentIndex() if hasattr(self.parent(), 'currentIndex') else None
        if index and index.isValid():
            folder_path = self.parent().model().filePath(index)
            stats = self.stats_manager.get_cached_statistics(folder_path)
            if stats:
                return f"{value} ({stats.total_files} plików, {stats.total_pairs} par)"
        return super().displayText(value, locale)


class StatsProxyModel(QSortFilterProxyModel):
    """Proxy model z filtrowaniem i dodatkowymi danymi statystyk."""

    def __init__(self, stats_manager: FolderStatisticsManager, parent=None):
        super().__init__(parent)
        self.stats_manager = stats_manager
        self._filter_function = None

    def setSourceModel(self, sourceModel):
        """Ustawia model źródłowy."""
        super().setSourceModel(sourceModel)
        if sourceModel:
            sourceModel.directoryLoaded.connect(self.invalidateFilter)

    def set_filter_function(self, filter_func):
        """Ustawia funkcję filtrowania."""
        self._filter_function = filter_func
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        """Filtruje wiersze na podstawie custom funkcji."""
        if self._filter_function:
            return self._filter_function(source_row, source_parent)
        return super().filterAcceptsRow(source_row, source_parent)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Rozszerza dane o statystyki folderów."""
        if role == Qt.ItemDataRole.DisplayRole and index.column() == 0:
            source_index = self.mapToSource(index)
            if source_index.isValid():
                source_model = self.sourceModel()
                folder_path = source_model.filePath(source_index)
                folder_name = source_model.fileName(source_index)
                
                # Pobierz statystyki z cache
                stats = self.stats_manager.get_cached_statistics(folder_path)
                if stats and (stats.total_files > 0 or stats.total_pairs > 0):
                    return f"{folder_name} ({stats.total_files} plików, {stats.total_pairs} par)"
                
                return folder_name
        
        return super().data(index, role)


class DirectoryTreeManager:
    """
    Uproszczony manager drzewa katalogów z wydzielonymi odpowiedzialnościami.
    
    Odpowiedzialności:
    - Zarządzanie UI drzewa folderów
    - Inicjalizacja i konfiguracja modeli
    - Obsługa interakcji użytkownika z drzewem
    - Koordynacja z managerami: statistics i operations
    """

    def __init__(self, folder_tree: QTreeView, parent_window):
        self.folder_tree = folder_tree
        self.parent_window = parent_window
        
        # Managery wydzielonych funkcjonalności
        self.stats_manager = FolderStatisticsManager()
        self.operations_manager = FolderOperationsManager(parent_window)
        
        # Modele Qt
        self.model = QFileSystemModel()
        self.proxy_model = StatsProxyModel(self.stats_manager)
        
        # Stan
        self._main_working_directory = None
        self._expanded_folders = set()
        
        # Inicjalizacja
        self._setup_models()
        self._setup_ui()
        self._setup_context_menu()
        self._setup_drag_and_drop()

    def _setup_models(self):
        """Konfiguruje modele danych."""
        # Konfiguracja model źródłowego
        self.model.setRootPath("")
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)
        
        # Konfiguracja proxy model
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setDynamicSortFilter(True)
        
        # Ustaw model w tree view
        self.folder_tree.setModel(self.proxy_model)
        
        # Ukryj niepotrzebne kolumny
        for i in range(1, self.model.columnCount()):
            self.folder_tree.hideColumn(i)

    def _setup_ui(self):
        """Konfiguruje UI drzewa folderów."""
        # Delegate dla statystyk
        stats_delegate = FolderStatsDelegate(self.stats_manager)
        self.folder_tree.setItemDelegate(stats_delegate)
        
        # Sygnały
        self.folder_tree.clicked.connect(self._on_folder_clicked)
        
        # Filtrowanie folderów
        self._setup_folder_filtering()

    def _setup_folder_filtering(self):
        """Konfiguruje filtrowanie folderów."""
        def filter_folders(source_row: int, source_parent: QModelIndex) -> bool:
            source_index = self.model.index(source_row, 0, source_parent)
            if source_index.isValid():
                folder_name = self.model.fileName(source_index)
                return self.should_show_folder(folder_name)
            return True
        
        self.proxy_model.set_filter_function(filter_folders)

    def should_show_folder(self, folder_name: str) -> bool:
        """Określa czy folder powinien być wyświetlany."""
        # Ukryj foldery zaczynające się od kropki
        if folder_name.startswith('.'):
            return False
        
        # Ukryj niektóre systemowe foldery Windows i foldery aplikacji
        hidden_folders = {
            'System Volume Information', 
            '$RECYCLE.BIN', 
            'Windows',
            '.app_metadata',
            '__pycache__',
            '.git',
            '.svn',
            '.hg',
            'node_modules',
            '.alg_meta',
        }
        return folder_name not in hidden_folders

    def _setup_context_menu(self):
        """Konfiguruje menu kontekstowe."""
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(self._show_context_menu)

    def _setup_drag_and_drop(self):
        """Konfiguruje obsługę drag & drop."""
        self.folder_tree.setDragDropMode(QTreeView.DragDropMode.DropOnly)
        self.folder_tree.setAcceptDrops(True)
        
        # Override events
        original_drag_enter = self.folder_tree.dragEnterEvent
        original_drag_move = self.folder_tree.dragMoveEvent
        original_drop = self.folder_tree.dropEvent
        
        self.folder_tree.dragEnterEvent = self._drag_enter_event
        self.folder_tree.dragMoveEvent = self._drag_move_event
        self.folder_tree.dropEvent = self._drop_event

    def init_directory_tree_async(self, current_working_directory: str):
        """Inicjalizuje drzewo katalogów asynchronicznie."""
        if not current_working_directory:
            logger.warning("Brak current_working_directory - pomijam inicjalizację")
            return

        logger.info(f"Inicjalizacja drzewa dla: {current_working_directory}")
        
        if not self._main_working_directory:
            self._main_working_directory = current_working_directory
            
            # Utwórz worker do skanowania folderów
            worker = ScanFolderWorker(self._main_working_directory)
            
            def on_folders_scanned(found_pairs, unpaired_archives, unpaired_previews):
                # Ustaw root path
                source_root_index = self.model.setRootPath(self._main_working_directory)
                proxy_root_index = self.proxy_model.mapFromSource(source_root_index)
                self.folder_tree.setRootIndex(proxy_root_index)
                
                # Rozpocznij obliczanie statystyk w tle
                QTimer.singleShot(500, self._start_background_stats_calculation)
                
                logger.info(f"Drzewo zainicjalizowane asynchronicznie dla: {self._main_working_directory}")
            
            def on_scan_error(error_msg):
                logger.error(f"Błąd skanowania folderów: {error_msg}")
                # Fallback - ustaw root bezpośrednio
                source_root_index = self.model.setRootPath(self._main_working_directory)
                proxy_root_index = self.proxy_model.mapFromSource(source_root_index)
                self.folder_tree.setRootIndex(proxy_root_index)
            
            worker.custom_signals.finished.connect(on_folders_scanned)
            worker.custom_signals.error.connect(on_scan_error)
            
            from PyQt6.QtCore import QThreadPool
            QThreadPool.globalInstance().start(worker)

    def _start_background_stats_calculation(self):
        """Rozpoczyna obliczanie statystyk dla widocznych folderów."""
        visible_folders = self._get_visible_folders()
        logger.debug(f"Rozpoczynam obliczanie statystyk dla {len(visible_folders)} folderów")
        
        for folder_path in visible_folders:
            self.stats_manager.calculate_statistics_async(
                folder_path, 
                lambda stats, path=folder_path: self._on_stats_calculated(path, stats)
            )

    def _get_visible_folders(self) -> List[str]:
        """Pobiera listę aktualnie widocznych folderów."""
        visible_folders = []
        
        if not self._main_working_directory:
            return visible_folders
        
        try:
            for root, dirs, files in os.walk(self._main_working_directory):
                # Filtruj tylko foldery które powinny być wyświetlane
                dirs[:] = [d for d in dirs if self.should_show_folder(d)]
                
                for folder_name in dirs:
                    folder_path = os.path.join(root, folder_name)
                    visible_folders.append(folder_path)
                
                # Ogranicz głębokość skanowania
                if len(root.split(os.sep)) - len(self._main_working_directory.split(os.sep)) >= 3:
                    dirs.clear()
        
        except Exception as e:
            logger.error(f"Błąd pobierania widocznych folderów: {e}")
        
        return visible_folders

    def _on_stats_calculated(self, folder_path: str, stats: FolderStatistics):
        """Callback po obliczeniu statystyk folderu."""
        if stats and (stats.total_files > 0 or stats.total_pairs > 0):
            # Odśwież wyświetlanie folderu
            self._refresh_folder_display(folder_path)

    def _refresh_folder_display(self, folder_path: str):
        """Odświeża wyświetlanie konkretnego folderu."""
        try:
            source_index = self.model.index(folder_path)
            if source_index.isValid():
                proxy_index = self.proxy_model.mapFromSource(source_index)
                if proxy_index.isValid():
                    self.folder_tree.update(proxy_index)
        except Exception as e:
            logger.error(f"Błąd odświeżania wyświetlania folderu {folder_path}: {e}")

    def _on_folder_clicked(self, proxy_index: QModelIndex):
        """Obsługuje kliknięcie folderu."""
        if proxy_index.isValid():
            source_index = self.proxy_model.mapToSource(proxy_index)
            folder_path = self.model.filePath(source_index)
            
            # Emituj sygnał zmiany folderu (jeśli parent ma odpowiedni callback)
            if hasattr(self.parent_window, 'on_folder_changed'):
                self.parent_window.on_folder_changed(folder_path)

    def _show_context_menu(self, position):
        """Pokazuje menu kontekstowe dla folderu."""
        index = self.folder_tree.indexAt(position)
        if not index.isValid():
            return
        
        source_index = self.proxy_model.mapToSource(index)
        folder_path = self.model.filePath(source_index)
        
        menu = QMenu(self.folder_tree)
        
        # Akcje operacji na folderach
        create_action = QAction("Utwórz nowy folder", menu)
        create_action.triggered.connect(lambda: self.operations_manager.create_folder(
            folder_path, self._on_folder_operation_finished
        ))
        
        rename_action = QAction("Przemianuj folder", menu)
        rename_action.triggered.connect(lambda: self.operations_manager.rename_folder(
            folder_path, self._on_folder_operation_finished
        ))
        
        delete_action = QAction("Usuń folder", menu)
        delete_action.triggered.connect(lambda: self.operations_manager.delete_folder(
            folder_path, self._on_folder_operation_finished
        ))
        
        open_action = QAction("Otwórz w eksploratorze", menu)
        open_action.triggered.connect(lambda: self.operations_manager.open_folder_in_explorer(folder_path))
        
        stats_action = QAction("Pokaż statystyki", menu)
        stats_action.triggered.connect(lambda: self._show_folder_statistics(folder_path))
        
        # Dodaj akcje do menu
        menu.addAction(create_action)
        menu.addAction(rename_action)
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(open_action)
        menu.addAction(stats_action)
        
        menu.exec(self.folder_tree.mapToGlobal(position))

    def _show_folder_statistics(self, folder_path: str):
        """Pokazuje szczegółowe statystyki folderu."""
        def on_stats_ready(stats: FolderStatistics):
            message = (
                f"Statystyki folderu: {os.path.basename(folder_path)}\n\n"
                f"Rozmiar: {stats.total_size_gb:.2f} GB\n"
                f"Liczba plików: {stats.total_files}\n"
                f"Liczba par: {stats.total_pairs}\n"
                f"Pary w folderze: {stats.pairs_count}\n"
                f"Pary w podfolderach: {stats.subfolders_pairs}"
            )
            
            QMessageBox.information(
                self.parent_window,
                "Statystyki folderu",
                message
            )
        
        # Pobierz z cache lub oblicz
        cached_stats = self.stats_manager.get_cached_statistics(folder_path)
        if cached_stats:
            on_stats_ready(cached_stats)
        else:
            self.stats_manager.calculate_statistics_async(folder_path, on_stats_ready)

    def _on_folder_operation_finished(self, *args):
        """Callback po zakończeniu operacji na folderze."""
        # Odśwież drzewo i cache statystyk
        self.refresh_tree()
        
        # Invaliduj cache dla aktualnego folderu i jego rodzica
        if args and len(args) > 0:
            folder_path = args[0] if isinstance(args[0], str) else str(args[0])
            self.stats_manager.invalidate_cache(folder_path)
            parent_path = os.path.dirname(folder_path)
            if parent_path:
                self.stats_manager.invalidate_cache(parent_path)

    def refresh_tree(self):
        """Odświeża całe drzewo folderów."""
        if self._main_working_directory:
            # Invaliduj model
            self.proxy_model.invalidate()
            
            # Ponownie oblicz statystyki dla widocznych folderów
            QTimer.singleShot(100, self._start_background_stats_calculation)

    def invalidate_folder_cache(self, folder_path: str):
        """Invaliduje cache dla konkretnego folderu."""
        self.stats_manager.invalidate_cache(folder_path)

    def get_cache_info(self) -> dict:
        """Zwraca informacje o cache."""
        return self.stats_manager.get_cache_info()

    # Placeholder metody dla drag & drop (do implementacji w przyszłości)
    def _drag_enter_event(self, event: QDragEnterEvent):
        """Obsługuje rozpoczęcie przeciągania."""
        event.accept()

    def _drag_move_event(self, event: QDragMoveEvent):
        """Obsługuje ruch podczas przeciągania."""
        event.accept()

    def _drop_event(self, event: QDropEvent):
        """Obsługuje upuszczenie."""
        event.accept()
        # Implementacja przenoszenia plików - do dodania w przyszłości 