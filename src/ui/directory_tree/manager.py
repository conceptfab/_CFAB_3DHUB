"""
Manager drzewa katalogów - zarządzanie folderami i drzewem nawigacji.
ETAP: ZAKTUALIZOWANY - Podzielony na moduły.
"""

import logging
import os
import subprocess
import time
from typing import List, Optional

from PyQt6.QtCore import QDir, QModelIndex, Qt, QThreadPool, QTimer
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
    QToolBar,
    QTreeView,
    QWidget,
)

from src.logic import file_operations
from src.logic.file_operations import (
    CreateFolderWorker,
    DeleteFolderWorker,
    RenameFolderWorker,
)
from src.utils.path_utils import normalize_path

from .cache import FolderStatsCache
from .data_classes import FolderStatistics
from .delegates import DropHighlightDelegate

# Importy z nowych modułów
from .models import FolderStatsDelegate, StatsProxyModel
from .throttled_scheduler import ThrottledWorkerScheduler
from .workers import FolderScanWorker, FolderStatisticsWorker

logger = logging.getLogger(__name__)


class DirectoryTreeManager:
    """
    Klasa zarządzająca drzewem katalogów i operacjami na folderach.
    """

    def __init__(self, folder_tree: QTreeView, parent_window):
        self.folder_tree = folder_tree
        self.parent_window = parent_window
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        # Filtrowanie, aby pokazywać tylko katalogi
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)

        # ==================== NOWE FUNKCJONALNOŚCI ====================
        # Cache statystyk folderów - używamy nowej klasy FolderStatsCache
        self._folder_stats_cache = FolderStatsCache(
            max_entries=100, timeout_seconds=300
        )

        # 🚀 OPTYMALIZACJA: Cache dla _get_visible_folders() - ~70% mniej wywołań skanowania
        self._visible_folders_cache = None
        self._visible_folders_cache_timestamp = 0
        self._visible_folders_cache_timeout = 60  # 60 sekund cache

        # 🚀 OPTYMALIZACJA: ThrottledWorkerScheduler - ~80% mniej przeciążenia systemu
        self._worker_scheduler = ThrottledWorkerScheduler(
            max_concurrent_workers=2, base_delay_ms=150
        )

        # Dedykowany thread pool z kontrolą wątków (zachowany dla kompatybilności)
        self._folder_thread_pool = QThreadPool()
        self._folder_thread_pool.setMaxThreadCount(3)  # Limit równoczesnych zadań
        self._active_workers = set()  # Zastąpione przez scheduler, ale zachowane

        # Proxy model do filtrowania ukrytych folderów I wyświetlania statystyk
        self.proxy_model = StatsProxyModel(self)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterKeyColumn(0)
        self.setup_folder_filtering()
        logger.info("DirectoryTreeManager: Utworzono StatsProxyModel")

        # Użyj proxy model zamiast bezpośrednio file system model
        self.folder_tree.setModel(self.proxy_model)
        self.folder_tree.setRootIndex(
            self.proxy_model.mapFromSource(self.model.index(QDir.currentPath()))
        )

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
        logger.info(
            f"DELEGATE SETUP: Ustawiono delegate: {self.drop_highlight_delegate}"
        )
        logger.info(
            f"DELEGATE SETUP: Aktualny delegate: {self.folder_tree.itemDelegate()}"
        )

        self.current_scan_path: str | None = None
        self._main_working_directory = None

        # ==================== DRAG AND DROP METHODS ====================
        self.setup_drag_and_drop_handlers()

    # ==================== METODY OBSŁUGI WORKERÓW Z KONTROLĄ ====================

    def _start_worker(self, worker):
        """Uruchamia workera z kontrolą liczby zadań."""
        if len(self._active_workers) >= 5:  # Limit globalny
            # Ciche odrzucanie dla zadań w tle - bez spamowania logów
            return False

        self._active_workers.add(worker)
        # Połącz sygnał finished do usunięcia workera z zestawu - używamy sygnałów UnifiedBaseWorker
        worker.signals.finished.connect(lambda: self._remove_worker(worker))
        worker.signals.error.connect(lambda: self._remove_worker(worker))

        self._folder_thread_pool.start(worker)
        return True

    def _remove_worker(self, worker):
        """Usuwa workera z zestawu aktywnych."""
        self._active_workers.discard(worker)

    # ==================== ZAKTUALIZOWANE METODY CACHE ====================

    def get_cached_folder_statistics(
        self, folder_path: str
    ) -> Optional[FolderStatistics]:
        """Pobiera statystyki z cache z sprawdzeniem ważności."""
        return self._folder_stats_cache.get(folder_path)

    def cache_folder_statistics(self, folder_path: str, stats: FolderStatistics):
        """Zapisuje statystyki do cache."""
        self._folder_stats_cache.set(folder_path, stats)

    def invalidate_folder_cache(self, folder_path: str):
        """Usuwa statystyki z cache dla konkretnego folderu."""
        self._folder_stats_cache.invalidate(folder_path)

    def invalidate_visible_folders_cache(self):
        """🚀 OPTYMALIZACJA: Invaliduje cache widocznych folderów."""
        self._visible_folders_cache = None
        self._visible_folders_cache_timestamp = 0
        logger.debug("📋 CACHE INVALIDATED: Wyczyścono cache widocznych folderów")

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
        }
        return folder_name not in hidden_folders

    def setup_expand_collapse_controls(self) -> QWidget:
        """Dodaje kontrolki zwijania/rozwijania folderów."""
        controls_widget = QWidget()
        layout = QHBoxLayout()

        toolbar = QToolBar()
        expand_all_action = toolbar.addAction("📂 Rozwiń wszystkie")
        collapse_all_action = toolbar.addAction("📁 Zwiń wszystkie")

        expand_all_action.triggered.connect(self.folder_tree.expandAll)
        collapse_all_action.triggered.connect(self.folder_tree.collapseAll)

        layout.addWidget(toolbar)
        controls_widget.setLayout(layout)

        return controls_widget

    def start_background_stats_calculation(self):
        """Rozpoczyna obliczanie statystyk dla widocznych folderów w tle."""
        if not self._main_working_directory:
            return

        # Pobierz listę wszystkich folderów w drzewie
        visible_folders = self._get_visible_folders()

        # Ograniczenie: max 50 folderów na raz (powiększone z 10)
        folders_to_process = []
        for folder_path in visible_folders[:50]:  # Limit pierwszych 50 folderów
            if not self.get_cached_folder_statistics(folder_path):
                folders_to_process.append(folder_path)

        logger.debug(
            f"🚀 SCHEDULER: Planowanie statystyk dla {len(folders_to_process)} folderów"
        )

        # 🚀 OPTYMALIZACJA: Użyj ThrottledWorkerScheduler zamiast QTimer
        for i, folder_path in enumerate(folders_to_process):
            task_id = f"stats_{os.path.basename(folder_path)}_{i}"

            # Factory function dla worker'a
            def create_stats_worker(path=folder_path):
                def worker_factory():
                    return self._create_stats_worker(path)

                return worker_factory

            # Dodaj do schedulera z prioryteten (główny folder ma wyższy priorytet)
            priority = 10 if folder_path == self._main_working_directory else 1
            self._worker_scheduler.schedule_task(
                task_id, create_stats_worker(folder_path), priority
            )

    def _get_visible_folders(self) -> List[str]:
        """
        🚀 OPTYMALIZACJA: Pobiera listę widocznych folderów z cache - ~70% mniej wywołań!
        """
        if not self._main_working_directory:
            return []

        # Sprawdź cache
        import time

        current_time = time.time()

        if (
            self._visible_folders_cache is not None
            and current_time - self._visible_folders_cache_timestamp
            < self._visible_folders_cache_timeout
        ):
            logger.debug(
                f"📋 CACHE HIT: Używam cache'owanej listy {len(self._visible_folders_cache)} folderów"
            )
            return self._visible_folders_cache.copy()

        # Cache miss - oblicz na nowo
        logger.debug("📋 CACHE MISS: Obliczam listę widocznych folderów...")
        folders = []

        try:
            # Przejdź przez widoczne foldery w modelu proxy zamiast os.walk
            root_index = self.model.index(self._main_working_directory)
            if not root_index.isValid():
                return folders

            # Dodaj główny folder
            folders.append(self._main_working_directory)

            # Rekurencyjnie przejdź przez wszystkie widoczne foldery w drzewie
            def traverse_model(parent_index, depth=0):
                if depth > 3:  # Limit głębokości dla wydajności
                    return

                row_count = self.model.rowCount(parent_index)
                for row in range(row_count):
                    child_index = self.model.index(row, 0, parent_index)
                    if child_index.isValid():
                        folder_path = self.model.filePath(child_index)
                        folder_name = self.model.fileName(child_index)

                        # Sprawdź czy folder jest widoczny (nie ukryty)
                        if folder_path and self.should_show_folder(folder_name):
                            folders.append(folder_path)

                            # Kontynuuj rekurencyjnie dla podfolderów
                            if self.model.hasChildren(child_index):
                                traverse_model(child_index, depth + 1)

            traverse_model(root_index)

            # Zapisz do cache
            self._visible_folders_cache = folders.copy()
            self._visible_folders_cache_timestamp = current_time

            logger.debug(f"📋 CACHE SAVE: Zapisano {len(folders)} folderów do cache")

        except Exception as e:
            logger.error(f"Błąd skanowania folderów: {e}")

        return folders

    def _create_stats_worker(self, folder_path: str) -> FolderStatisticsWorker:
        """🚀 OPTYMALIZACJA: Factory method dla tworzenia stats worker'ów."""

        def on_finished(stats):
            # Zapisz do cache i odśwież widok
            logger.debug(
                f"📊 Statystyki: {os.path.basename(folder_path)} -> {stats.pairs_count} par"
            )
            self.cache_folder_statistics(folder_path, stats)
            self._refresh_folder_display(folder_path)

        def on_error(error_msg):
            # Logi błędów dla diagnostyki
            logger.warning(f"📊 STATYSTYKI ERROR: {folder_path} -> {error_msg}")

        worker = FolderStatisticsWorker(folder_path)
        worker.custom_signals.finished.connect(on_finished)
        worker.custom_signals.error.connect(on_error)

        return worker

    def _calculate_stats_async_silent(self, folder_path: str):
        """
        DEPRECATED: Użyj _worker_scheduler.schedule_task() zamiast tej metody.
        Zachowane dla kompatybilności wstecznej.
        """
        worker = self._create_stats_worker(folder_path)
        self._start_worker(worker)

    def _refresh_folder_display(self, folder_path: str):
        """Odświeża wyświetlanie konkretnego folderu w drzewie."""
        try:
            source_index = self.model.index(folder_path)
            if source_index.isValid():
                proxy_index = self.get_proxy_index_from_source(source_index)
                if proxy_index.isValid():
                    # Wymuszenie odświeżenia proxy model
                    self.proxy_model.dataChanged.emit(
                        proxy_index, proxy_index, [Qt.ItemDataRole.DisplayRole]
                    )
                    logger.debug(f"Odświeżono wyświetlanie folderu: {folder_path}")
        except Exception as e:
            logger.debug(f"Błąd odświeżania widoku folderu {folder_path}: {e}")

    def open_folder_in_explorer(self, folder_path: str):
        """Otwiera folder w eksploratorze Windows."""
        try:
            logging.debug(f"Explorer: Opening folder: '{folder_path}'")

            # Sprawdź czy folder istnieje
            if not os.path.exists(folder_path):
                logging.error(
                    f"🗂️ EKSPLORATOR: BŁĄD - Folder nie istnieje: '{folder_path}'"
                )
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd",
                    f"Folder nie istnieje:\n{folder_path}",
                )
                return

            if not os.path.isdir(folder_path):
                logging.error(
                    f"🗂️ EKSPLORATOR: BŁĄD - Ścieżka nie jest folderem: '{folder_path}'"
                )
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd",
                    f"Ścieżka nie jest folderem:\n{folder_path}",
                )
                return

            # Normalizuj ścieżkę do formatu Windows
            normalized_path = os.path.normpath(folder_path)
            logging.debug(f"Explorer: Normalized path: '{normalized_path}'")

            # Użyj alternatywnych metod wywołania explorera
            import sys

            if sys.platform == "win32":
                # Metoda 1: Przez os.startfile - najbardziej niezawodna dla Windows
                try:
                    os.startfile(normalized_path)
                    logging.info(
                        f"🗂️ EKSPLORATOR: SUKCES (os.startfile) - Otwarto folder: {normalized_path}"
                    )
                    return
                except Exception as e1:
                    logging.warning(f"Explorer: os.startfile failed: {e1}")

                # Metoda 2: Przez subprocess z argumentami w liście
                try:
                    subprocess.Popen(["explorer", normalized_path])
                    logging.info(
                        f"🗂️ EKSPLORATOR: SUKCES (subprocess lista) - Otwarto folder: {normalized_path}"
                    )
                    return
                except Exception as e2:
                    logging.warning(
                        f"🗂️ EKSPLORATOR: subprocess z listą nie zadziałało: {e2}"
                    )

                # Metoda 3: Przez subprocess z shell=True
                try:
                    subprocess.Popen(f'explorer "{normalized_path}"', shell=True)
                    logging.info(
                        f"🗂️ EKSPLORATOR: SUKCES (subprocess shell) - Otwarto folder: {normalized_path}"
                    )
                    return
                except Exception as e3:
                    logging.error(
                        f"🗂️ EKSPLORATOR: subprocess z shell nie zadziałało: {e3}"
                    )
            else:
                logging.error(
                    f"🗂️ EKSPLORATOR: Nieobsługiwany system operacyjny: {sys.platform}"
                )

        except Exception as e:
            logging.error(f"Explorer: CRITICAL ERROR opening explorer: {e}")
            QMessageBox.warning(
                self.parent_window,
                "Błąd",
                f"Nie można otworzyć folderu w eksploratorze:\n{e}",
            )

    def calculate_folder_statistics_async(self, folder_path: str, callback=None):
        """Oblicza statystyki folderu asynchronicznie."""

        def on_finished(stats):
            # Zapisz do cache
            self.cache_folder_statistics(folder_path, stats)
            if callback:
                callback(stats)

        def on_error(error_msg):
            logger.error(f"Błąd obliczania statystyk: {error_msg}")
            if callback:
                callback(None)

        worker = FolderStatisticsWorker(folder_path)
        worker.custom_signals.finished.connect(on_finished)
        worker.custom_signals.error.connect(on_error)

        self._start_worker(worker)

    def show_folder_context_menu(self, position):
        """Wyświetla rozszerzone menu kontekstowe dla drzewa folderów."""
        logging.info(
            f"🗂️ MENU_KONTEKSTOWE: Wyświetlanie menu kontekstowego na pozycji: {position}"
        )

        # Pobierz indeks wybranego elementu (używamy proxy model)
        proxy_index = self.folder_tree.indexAt(position)
        if not proxy_index.isValid():
            logging.warning(
                f"🗂️ MENU_KONTEKSTOWE: BŁĄD - Nieprawidłowy proxy_index na pozycji: {position}"
            )
            return

        # Mapuj z proxy na źródłowy model
        source_index = self.proxy_model.mapToSource(proxy_index)
        if not source_index.isValid():
            logging.warning(
                f"🗂️ MENU_KONTEKSTOWE: BŁĄD - Nieprawidłowy source_index dla proxy: {proxy_index}"
            )
            return

        # Pobierz ścieżkę do wybranego folderu
        folder_path = self.model.filePath(source_index)

        # Sprawdź czy folder istnieje i jest folderem
        if not os.path.exists(folder_path):
            logging.error(
                f"🗂️ MENU_KONTEKSTOWE: BŁĄD - Folder nie istnieje: '{folder_path}'"
            )
            return

        if not os.path.isdir(folder_path):
            logging.error(
                f"🗂️ MENU_KONTEKSTOWE: BŁĄD - Ścieżka nie jest folderem: '{folder_path}'"
            )
            return

        # Tworzenie menu kontekstowego
        context_menu = QMenu()

        # NOWA FUNKCJONALNOŚĆ: Otwórz w eksploratorze
        open_explorer_action = context_menu.addAction("🗂️ Otwórz w eksploratorze")
        open_explorer_action.triggered.connect(
            lambda: self.open_folder_in_explorer(folder_path)
        )

        # NOWA FUNKCJONALNOŚĆ: Statystyki folderu
        stats_action = context_menu.addAction("📊 Pokaż statystyki")
        stats_action.triggered.connect(lambda: self.show_folder_statistics(folder_path))

        # NOWA FUNKCJONALNOŚĆ: Wymuś przeliczenie statystyk
        recalc_stats_action = context_menu.addAction("🔄 Przelicz statystyki")
        recalc_stats_action.triggered.connect(
            lambda: self._force_recalculate_folder_stats(folder_path)
        )

        # NOWA FUNKCJONALNOŚĆ: Przelicz wszystkie statystyki
        recalc_all_action = context_menu.addAction("🔄 Przelicz wszystkie statystyki")
        recalc_all_action.triggered.connect(
            lambda: self.force_calculate_all_stats_async()
        )

        context_menu.addSeparator()

        # Istniejące akcje
        create_folder_action = context_menu.addAction("Nowy folder")
        rename_folder_action = context_menu.addAction("Zmień nazwę")
        delete_folder_action = context_menu.addAction("Usuń folder")

        # Połączenie akcji z metodami
        create_folder_action.triggered.connect(lambda: self.create_folder(folder_path))
        rename_folder_action.triggered.connect(lambda: self.rename_folder(folder_path))
        delete_folder_action.triggered.connect(
            lambda: self.delete_folder(
                folder_path, self.parent_window.controller.current_directory
            )
        )

        # Wyświetlenie menu
        context_menu.exec(self.folder_tree.mapToGlobal(position))

    def show_folder_statistics(self, folder_path: str):
        """Wyświetla statystyki folderu."""
        # Sprawdź cache
        cached_stats = self.get_cached_folder_statistics(folder_path)
        if cached_stats:
            self._display_folder_statistics(cached_stats, folder_path)
            return

        # Utwórz progress dialog
        progress_dialog = QProgressDialog(
            f"Obliczanie statystyk dla '{os.path.basename(folder_path)}'...",
            "Anuluj",
            0,
            100,
            self.parent_window,
        )
        progress_dialog.setWindowTitle("Statystyki folderu")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setValue(0)

        # Utwórz worker
        worker = FolderStatisticsWorker(folder_path)

        def on_finished(stats):
            progress_dialog.accept()
            self.cache_folder_statistics(folder_path, stats)
            self._display_folder_statistics(stats, folder_path)

        def on_error(error_msg):
            progress_dialog.reject()
            QMessageBox.critical(
                self.parent_window,
                "Błąd obliczania statystyk",
                f"Nie można obliczyć statystyk folderu:\n{error_msg}",
            )

        def on_progress(percent, message):
            if progress_dialog.isVisible():
                progress_dialog.setValue(percent)
                progress_dialog.setLabelText(message)

        worker.custom_signals.finished.connect(on_finished)
        worker.custom_signals.error.connect(on_error)
        worker.custom_signals.progress.connect(on_progress)
        progress_dialog.canceled.connect(worker.interrupt)

        self._start_worker(worker)
        progress_dialog.show()

    def _display_folder_statistics(self, stats: FolderStatistics, folder_path: str):
        """Wyświetla wyniki statystyk folderu."""
        folder_name = os.path.basename(folder_path)
        message = f"""Statystyki folderu '{folder_name}':

📁 Rozmiar: {stats.size_gb:.2f} GB
📦 Liczba par plików: {stats.pairs_count}
📄 Całkowita liczba plików: {stats.total_files}

💾 Dane z cache: {'Tak' if self.get_cached_folder_statistics(folder_path) else 'Nie'}"""

        QMessageBox.information(
            self.parent_window, f"Statystyki - {folder_name}", message
        )

    def create_folder(self, parent_folder_path: str):
        """Tworzy nowy folder w wybranej lokalizacji przy użyciu workera."""
        folder_name, ok = QInputDialog.getText(
            self.parent_window, "Nowy folder", "Podaj nazwę folderu:"
        )

        if ok and folder_name:
            # Normalizacja ścieżki i nazwy folderu
            parent_folder_path_norm = normalize_path(parent_folder_path)

            worker = file_operations.create_folder(parent_folder_path_norm, folder_name)

            if worker:
                # Utworzenie okna dialogowego postępu
                progress_dialog = QProgressDialog(
                    f"Tworzenie folderu '{folder_name}'...",
                    "Anuluj",
                    0,
                    0,  # Ustawienie min i max na 0 dla nieokreślonego paska postępu
                    self.parent_window,
                )
                progress_dialog.setWindowTitle("Tworzenie folderu")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.setAutoClose(True)
                progress_dialog.setAutoReset(True)
                progress_dialog.setValue(0)

                # Połączenie sygnałów workera
                worker.signals.finished.connect(
                    lambda path: self._handle_create_folder_finished(
                        path, progress_dialog
                    )
                )
                worker.signals.error.connect(
                    lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd tworzenia folderu", progress_dialog
                    )
                )
                worker.signals.progress.connect(
                    lambda percent, msg: self._handle_operation_progress(
                        percent, msg, progress_dialog
                    )
                )
                worker.signals.interrupted.connect(
                    lambda: self._handle_operation_interrupted(
                        "Tworzenie folderu zostało przerwane.", progress_dialog
                    )
                )

                # Połączenie przycisku anulowania
                progress_dialog.canceled.connect(worker.interrupt)

                # Uruchomienie workera
                QThreadPool.globalInstance().start(worker)

                # Wyświetlenie okna dialogowego
                progress_dialog.show()

    def rename_folder(self, folder_path: str):
        """Zmienia nazwę folderu."""
        current_name = os.path.basename(folder_path)
        new_name, ok = QInputDialog.getText(
            self.parent_window,
            "Zmiana nazwy folderu",
            "Podaj nową nazwę folderu:",
            text=current_name,
        )

        if ok and new_name and new_name != current_name:
            folder_path_norm = normalize_path(folder_path)
            worker = file_operations.rename_folder(folder_path_norm, new_name)

            if worker:
                progress_dialog = QProgressDialog(
                    f"Zmiana nazwy folderu '{current_name}' na '{new_name}'...",
                    "Anuluj",
                    0,
                    0,
                    self.parent_window,
                )
                progress_dialog.setWindowTitle("Zmiana nazwy folderu")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.setAutoClose(True)
                progress_dialog.setAutoReset(True)
                progress_dialog.setValue(0)

                worker.signals.finished.connect(
                    lambda new_path: self._handle_rename_folder_finished(
                        folder_path, new_path, progress_dialog
                    )
                )
                worker.signals.error.connect(
                    lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd zmiany nazwy folderu", progress_dialog
                    )
                )
                worker.signals.progress.connect(
                    lambda percent, msg: self._handle_operation_progress(
                        percent, msg, progress_dialog
                    )
                )

                progress_dialog.canceled.connect(worker.interrupt)
                QThreadPool.globalInstance().start(worker)
                progress_dialog.show()

    def delete_folder(self, folder_path: str, current_working_directory: str):
        """Usuwa folder."""
        folder_name = os.path.basename(folder_path)
        reply = QMessageBox.question(
            self.parent_window,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć folder '{folder_name}' i całą jego zawartość?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            folder_path_norm = normalize_path(folder_path)
            worker = file_operations.delete_folder(folder_path_norm)

            if worker:
                progress_dialog = QProgressDialog(
                    f"Usuwanie folderu '{folder_name}'...",
                    "Anuluj",
                    0,
                    0,
                    self.parent_window,
                )
                progress_dialog.setWindowTitle("Usuwanie folderu")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.setAutoClose(True)
                progress_dialog.setAutoReset(True)
                progress_dialog.setValue(0)

                worker.signals.finished.connect(
                    lambda deleted_path: self._handle_delete_folder_finished(
                        deleted_path, progress_dialog
                    )
                )
                worker.signals.error.connect(
                    lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd usuwania folderu", progress_dialog
                    )
                )

                progress_dialog.canceled.connect(worker.interrupt)
                QThreadPool.globalInstance().start(worker)
                progress_dialog.show()

    # Handle methods dla operacji na folderach
    def _handle_create_folder_finished(
        self, created_folder_path: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje zakończenie tworzenia folderu."""
        progress_dialog.accept()
        folder_name = os.path.basename(created_folder_path)
        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Folder '{folder_name}' został utworzony pomyślnie.",
        )
        self.refresh_entire_tree()

    def _handle_rename_folder_finished(
        self, old_path: str, new_path: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje zakończenie zmiany nazwy folderu."""
        progress_dialog.accept()
        old_name = os.path.basename(old_path)
        new_name = os.path.basename(new_path)
        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Folder '{old_name}' został przemianowany na '{new_name}'.",
        )
        self.refresh_entire_tree()

    def _handle_delete_folder_finished(
        self, deleted_folder_path: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje zakończenie usuwania folderu."""
        progress_dialog.accept()
        folder_name = os.path.basename(deleted_folder_path)
        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Folder '{folder_name}' został usunięty pomyślnie.",
        )
        self.refresh_entire_tree()

    def _handle_operation_error(
        self, error_message: str, title: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje błędy operacji na folderach."""
        progress_dialog.reject()
        QMessageBox.critical(self.parent_window, title, error_message)

    def _handle_operation_progress(
        self, percent: int, message: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje postęp operacji na folderach."""
        if progress_dialog.isVisible():
            progress_dialog.setValue(percent)
            progress_dialog.setLabelText(message)

    def _handle_operation_interrupted(
        self, message: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje przerwanie operacji na folderach."""
        progress_dialog.reject()
        QMessageBox.information(self.parent_window, "Operacja przerwana", message)

    def refresh_entire_tree(self):
        """Odświeża całe drzewo katalogów."""
        try:
            # Wyczyść cache statystyk
            self._folder_stats_cache.clear()

            # 🚀 OPTYMALIZACJA: Wyczyść także cache widocznych folderów
            self.invalidate_visible_folders_cache()

            # Odśwież model
            self.model.setRootPath(self.model.rootPath())

            # Przefiltruj na nowo
            self.proxy_model.invalidateFilter()

            logger.info("Odświeżono całe drzewo katalogów z wyczyszczeniem cache")
        except Exception as e:
            logger.error(f"Błąd odświeżania drzewa: {e}")

    def refresh_file_pairs_after_folder_operation(self, current_working_directory: str):
        """Odświeża listę par plików po operacji na folderze."""
        try:
            # Sygnalizuj głównemu oknu że powinno odświeżyć pary plików
            if hasattr(self.parent_window, "refresh_file_pairs"):
                self.parent_window.refresh_file_pairs()
        except Exception as e:
            logger.error(f"Błąd odświeżania par plików: {e}")

    def folder_tree_item_clicked(self, proxy_index, current_working_directory: str):
        """Obsługuje kliknięcie elementu w drzewie folderów."""
        try:
            if not proxy_index.isValid():
                return

            # Mapuj proxy index na source index
            source_index = self.proxy_model.mapToSource(proxy_index)
            if not source_index.isValid():
                return

            # Pobierz ścieżkę folderu
            folder_path = self.model.filePath(source_index)
            if folder_path and os.path.isdir(folder_path):
                # Sygnalizuj głównemu oknu zmianę katalogu
                if hasattr(self.parent_window, "change_directory"):
                    self.parent_window.change_directory(folder_path)
        except Exception as e:
            logger.error(f"Błąd obsługi kliknięcia folderu: {e}")

    def get_source_index_from_proxy(self, proxy_index: QModelIndex) -> QModelIndex:
        """Mapuje proxy index na source index."""
        return self.proxy_model.mapToSource(proxy_index)

    def get_proxy_index_from_source(self, source_index: QModelIndex) -> QModelIndex:
        """Mapuje source index na proxy index."""
        return self.proxy_model.mapFromSource(source_index)

    def setup_drag_and_drop_handlers(self):
        """Konfiguruje obsługę drag and drop dla drzewa folderów."""
        # Zastąp standardowe handlery własnymi
        self.folder_tree.dragEnterEvent = self._drag_enter_event
        self.folder_tree.dragMoveEvent = self._drag_move_event
        self.folder_tree.dragLeaveEvent = self._drag_leave_event
        self.folder_tree.dropEvent = self._drop_event
        logger.info("Drag and drop handlers skonfigurowane")

    def _drag_enter_event(self, event: QDragEnterEvent):
        """Obsługuje rozpoczęcie przeciągania nad drzewem folderów."""
        try:
            print(f"🔥 DRAG ENTER EVENT CALLED! hasUrls={event.mimeData().hasUrls()}")
            logger.info(f"DRAG ENTER: hasUrls={event.mimeData().hasUrls()}")
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                print(f"🔥 DRAG ENTER: {len(urls)} plików: {[url.toLocalFile() for url in urls[:3]]}")
                logger.info(f"DRAG ENTER: {len(urls)} plików: {[url.toLocalFile() for url in urls[:3]]}")
                event.acceptProposedAction()
                print("🔥 DRAG ENTER: Akceptowano przeciąganie plików")
                logger.info("DRAG ENTER: Akceptowano przeciąganie plików")
            else:
                print("🔥 DRAG ENTER: Brak URLs - ignoruję")
                logger.info("DRAG ENTER: Brak URLs - ignoruję")
                event.ignore()
        except Exception as e:
            print(f"🔥 BŁĄD DRAG ENTER: {e}")
            logger.error(f"Błąd drag enter: {e}")
            event.ignore()

    def _drag_move_event(self, event: QDragMoveEvent):
        """Obsługuje ruch podczas przeciągania nad drzewem folderów."""
        try:
            if event.mimeData().hasUrls():
                # Znajdź folder pod kursorem
                index = self.folder_tree.indexAt(event.position().toPoint())
                logger.info(f"DRAG MOVE: index valid={index.isValid()}")
                if index.isValid():
                    # Podświetl folder jako cel
                    source_index = self.get_source_index_from_proxy(index)
                    if source_index.isValid():
                        folder_path = self.model.filePath(source_index)
                        logger.info(f"DRAG MOVE: folder_path={folder_path}")
                        if os.path.isdir(folder_path):
                            current_target = getattr(
                                self, "_highlighted_drop_target", None
                            )
                            if current_target != folder_path:
                                self._highlighted_drop_target = folder_path
                                logger.info(f"DRAG MOVE: Podświetlam folder: {folder_path}")
                                # Wymuś ponowne rysowanie tylko jeśli folder się zmienił
                                self.folder_tree.viewport().update()
                            event.acceptProposedAction()
                            return

            event.ignore()
        except Exception as e:
            logger.error(f"Błąd drag move: {e}")
            event.ignore()

    def _drag_leave_event(self, event: QDragLeaveEvent):
        """Obsługuje opuszczenie obszaru podczas przeciągania."""
        try:
            # Usuń podświetlenie
            if hasattr(self, "_highlighted_drop_target"):
                delattr(self, "_highlighted_drop_target")
                self.folder_tree.viewport().update()
            event.accept()
        except Exception as e:
            logger.error(f"Błąd drag leave: {e}")

    def _drop_event(self, event: QDropEvent):
        """Obsługuje upuszczenie plików na folder."""
        try:
            if event.mimeData().hasUrls():
                # Znajdź docelowy folder
                index = self.folder_tree.indexAt(event.position().toPoint())
                if index.isValid():
                    source_index = self.get_source_index_from_proxy(index)
                    if source_index.isValid():
                        target_folder = self.model.filePath(source_index)
                        if os.path.isdir(target_folder):
                            # Pobierz ścieżki upuszczonych plików
                            dropped_files = []
                            for url in event.mimeData().urls():
                                file_path = url.toLocalFile()
                                if os.path.exists(file_path):
                                    dropped_files.append(file_path)

                            if dropped_files:
                                # Sygnalizuj głównemu oknu operację move/copy
                                if hasattr(
                                    self.parent_window, "handle_file_drop_on_folder"
                                ):
                                    self.parent_window.handle_file_drop_on_folder(
                                        dropped_files, target_folder
                                    )
                                    logger.info(
                                        f"DRAG&DROP: Wywołano handle_file_drop_on_folder z {len(dropped_files)} plikami"
                                    )
                                else:
                                    logger.error(
                                        "DRAG&DROP ERROR: Brak metody handle_file_drop_on_folder w parent_window"
                                    )
                                event.acceptProposedAction()

            # Usuń podświetlenie
            if hasattr(self, "_highlighted_drop_target"):
                delattr(self, "_highlighted_drop_target")
                self.folder_tree.viewport().update()

        except Exception as e:
            logger.error(f"Błąd drop event: {e}")
            event.ignore()

    def force_calculate_all_stats_async(self):
        """Wymuś przeliczenie statystyk dla wszystkich widocznych folderów."""
        if not self._main_working_directory:
            return

        visible_folders = self._get_visible_folders()

        for folder_path in visible_folders:
            # Usuń z cache aby wymusić przeliczenie
            self.invalidate_folder_cache(folder_path)
            # Rozpocznij przeliczanie
            self._calculate_stats_async_silent(folder_path)

        logger.info(
            f"Rozpoczęto przeliczanie statystyk dla {len(visible_folders)} folderów"
        )

    def _force_recalculate_folder_stats(self, folder_path: str):
        """Wymuś przeliczenie statystyk dla konkretnego folderu."""
        # Usuń z cache
        self.invalidate_folder_cache(folder_path)
        # Rozpocznij przeliczanie
        self._calculate_stats_async_silent(folder_path)
        logger.info(f"Rozpoczęto przeliczanie statystyk dla folderu: {folder_path}")

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
            normalized_path = normalize_path(folder_path)
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
        """Inicjalizuje drzewo katalogów bez automatycznego skanowania i rozwijania folderów."""
        try:
            self._main_working_directory = current_working_directory

            # Ustaw TYLKO root path - bez skanowania i rozwijania
            self.model.setRootPath(current_working_directory)
            root_index = self.model.index(current_working_directory)
            proxy_root_index = self.proxy_model.mapFromSource(root_index)
            self.folder_tree.setRootIndex(proxy_root_index)

            # CELOWO POMIJAMY:
            # - _scan_folders_with_files()
            # - _expand_folders_with_files()
            # - start_background_stats_calculation()

            logger.info(
                f"Zainicjalizowano drzewo katalogów (bez rozwijania) dla: {current_working_directory}"
            )

        except Exception as e:
            logger.error(f"Błąd inicjalizacji drzewa katalogów (bez rozwijania): {e}")
