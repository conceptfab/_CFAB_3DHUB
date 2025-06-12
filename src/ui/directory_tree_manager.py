"""
Manager drzewa katalogów - zarządzanie folderami i drzewem nawigacji.
ETAP: ZAKTUALIZOWANY - Dodano nowe funkcjonalności wymagane w analizie.
"""

import logging
import os
import subprocess
import time
from dataclasses import dataclass
from typing import List, Optional

from PyQt6.QtCore import (
    QDir,
    QEvent,
    QMimeData,
    QModelIndex,
    QObject,
    QRunnable,
    QSortFilterProxyModel,
    Qt,
    QThreadPool,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QFileSystemModel,
    QMouseEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QStyledItemDelegate,
    QStyleOptionViewItem,
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
from src.logic.scanner import scan_folder_for_pairs
from src.ui.delegates.workers import BaseWorkerSignals, UnifiedBaseWorker
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


# ==================== NOWE KLASY POMOCNICZE ====================


@dataclass
class FolderStatistics:
    """Statystyki folderu - rozmiar i liczba par plików."""

    size_gb: float = 0.0
    pairs_count: int = 0
    subfolders_size_gb: float = 0.0
    subfolders_pairs: int = 0
    total_files: int = 0

    @property
    def total_size_gb(self) -> float:
        return self.size_gb + self.subfolders_size_gb

    @property
    def total_pairs(self) -> int:
        return self.pairs_count + self.subfolders_pairs


class FolderStatisticsSignals(QObject):
    """Sygnały dla workera statystyk folderów."""

    finished = pyqtSignal(object)  # FolderStatistics
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    interrupted = pyqtSignal()


class FolderStatisticsWorker(UnifiedBaseWorker):
    """Worker do obliczania statystyk folderu w tle."""

    def __init__(self, folder_path: str):
        super().__init__()
        self.folder_path = normalize_path(folder_path)
        self.custom_signals = FolderStatisticsSignals()

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        if not self.folder_path or not os.path.exists(self.folder_path):
            raise ValueError(f"Folder '{self.folder_path}' nie istnieje")

    def run(self):
        """Oblicza statystyki folderu."""
        try:
            stats = FolderStatistics()
            self.emit_progress(0, "Rozpoczynanie obliczania statystyk...")

            if self.check_interruption():
                return

            # Oblicz rozmiar foldera
            self.emit_progress(25, "Obliczanie rozmiaru folderu...")
            total_size = 0
            file_count = 0

            for root, dirs, files in os.walk(self.folder_path):
                if self.check_interruption():
                    return

                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                    except (OSError, FileNotFoundError):
                        continue

            stats.size_gb = total_size / (1024**3)
            stats.total_files = file_count

            # Oblicz liczbę par plików
            self.emit_progress(75, "Obliczanie liczby par plików...")
            if self.check_interruption():
                return

            try:
                found_pairs, _, _ = scan_folder_for_pairs(
                    self.folder_path, max_depth=0, pair_strategy="first_match"
                )
                stats.pairs_count = len(found_pairs)
            except Exception as e:
                logger.warning(f"Błąd obliczania par plików: {e}")
                stats.pairs_count = 0

            self.emit_progress(100, "Zakończono obliczanie statystyk")
            self.custom_signals.finished.emit(stats)
            self.emit_finished(stats)

        except Exception as e:
            error_msg = f"Błąd obliczania statystyk dla {self.folder_path}: {e}"
            logger.error(error_msg)
            self.custom_signals.error.emit(error_msg)
            self.emit_error(error_msg)


class FolderScanSignals(QObject):
    """Sygnały dla workera skanowania folderów."""

    finished = pyqtSignal(list)  # Lista folderów z plikami
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    interrupted = pyqtSignal()


class FolderScanWorker(UnifiedBaseWorker):
    """Worker do asynchronicznego skanowania folderów."""

    def __init__(self, root_folder: str):
        super().__init__()
        self.root_folder = normalize_path(root_folder)
        self.custom_signals = FolderScanSignals()

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        if not self.root_folder or not os.path.exists(self.root_folder):
            raise ValueError(f"Folder '{self.root_folder}' nie istnieje")

    def run(self):
        """Skanuje foldery w poszukiwaniu tych z plikami."""
        try:
            folders_with_files = []
            self.emit_progress(0, "Rozpoczynanie skanowania folderów...")

            total_folders = 0
            processed_folders = 0

            # Najpierw policz foldery
            for root, dirs, files in os.walk(self.root_folder):
                dirs[:] = [d for d in dirs if not d.startswith(".")]
                total_folders += len(dirs)

            # Teraz skanuj
            for root, dirs, files in os.walk(self.root_folder):
                if self.check_interruption():
                    return

                # Pomiń ukryte foldery
                dirs[:] = [d for d in dirs if not d.startswith(".")]

                # Jeśli folder ma pliki, dodaj go do listy
                if files:
                    folders_with_files.append(root)

                processed_folders += 1
                if total_folders > 0:
                    progress = int((processed_folders / total_folders) * 100)
                    self.emit_progress(
                        progress, f"Skanowanie: {processed_folders}/{total_folders}"
                    )

            self.emit_progress(
                100, f"Znaleziono {len(folders_with_files)} folderów z plikami"
            )
            self.custom_signals.finished.emit(folders_with_files)
            self.emit_finished(folders_with_files)

        except Exception as e:
            error_msg = f"Błąd podczas skanowania folderów: {e}"
            logger.error(error_msg)
            self.custom_signals.error.emit(error_msg)
            self.emit_error(error_msg)


# ==================== DELEGATY I POMOCNICZE ====================


# Definicja delegata do wyświetlania statystyk folderów
class FolderStatsDelegate(QStyledItemDelegate):
    """Delegate do wyświetlania statystyk folderów bezpośrednio w drzewie."""

    def __init__(self, directory_tree_manager, parent=None):
        super().__init__(parent)
        self.directory_tree_manager = directory_tree_manager

    def displayText(self, value, locale):
        """Formatuje tekst wyświetlany dla folderu z statystykami."""
        # Sprawdź czy to już sformatowany tekst ze statystykami
        if isinstance(value, str) and (" GB, " in value or "(... GB" in value):
            return value

        # Zwróć oryginalną wartość
        return super().displayText(value, locale)


class StatsProxyModel(QSortFilterProxyModel):
    """Proxy model który dodaje statystyki do nazw folderów."""

    def __init__(self, directory_tree_manager, parent=None):
        super().__init__(parent)
        self.directory_tree_manager = directory_tree_manager
        self._filter_function = None
        logger.info("StatsProxyModel zainicjalizowany!")

    def setSourceModel(self, sourceModel):
        """Override setSourceModel aby zalogować co się dzieje."""
        logger.info(f"StatsProxyModel.setSourceModel wywoływane z: {type(sourceModel)}")
        super().setSourceModel(sourceModel)
        logger.info(
            f"StatsProxyModel.setSourceModel ukończone, sourceModel: {self.sourceModel()}"
        )

    def set_filter_function(self, filter_func):
        """Ustawia funkcję filtrującą."""
        self._filter_function = filter_func
        logger.debug("Ustawiono funkcję filtrującą w StatsProxyModel")

    def filterAcceptsRow(self, source_row, source_parent):
        """Filtruje wiersze na podstawie ustawionej funkcji."""
        if self._filter_function:
            return self._filter_function(source_row, source_parent)
        return super().filterAcceptsRow(source_row, source_parent)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """Zwraca dane z dodanymi statystykami."""
        logger.debug(
            f"StatsProxyModel.data() wywoływane - role: {role}, index: {index.isValid()}"
        )

        if role == Qt.ItemDataRole.DisplayRole:
            logger.debug("StatsProxyModel.data() - przetwarzam DisplayRole")
            # Pobierz source index
            source_index = self.mapToSource(index)
            if not source_index.isValid():
                logger.debug("StatsProxyModel.data() - source_index nieważny")
                return super().data(index, role)

            # Pobierz ścieżkę i nazwę folderu
            folder_path = self.sourceModel().filePath(source_index)
            folder_name = self.sourceModel().fileName(source_index)

            logger.debug(
                f"StatsProxyModel.data() - folder: {folder_name} ({folder_path})"
            )

            if not folder_path or not os.path.isdir(folder_path):
                logger.debug("StatsProxyModel.data() - nie jest katalogiem")
                return super().data(index, role)

            # Sprawdź cache statystyk
            stats = self.directory_tree_manager.get_cached_folder_statistics(
                folder_path
            )
            if stats:
                # Zwróć nazwę ze statystykami
                display_text = (
                    f"{folder_name} ({stats.size_gb:.1f} GB, {stats.pairs_count} par)"
                )
                logger.info(f"StatsProxyModel: Zwracam ze statystykami: {display_text}")
                return display_text
            else:
                # Zwróć nazwę z placeholder
                display_text = f"{folder_name} (... GB, ... par)"
                logger.info(f"StatsProxyModel: Zwracam placeholder dla: {folder_name}")
                return display_text

        # Dla innych ról zwróć standardowe dane
        return super().data(index, role)


# Definicja delegata do podświetlania celu upuszczenia
class DropHighlightDelegate(QStyledItemDelegate):
    """Delegate do podświetlania celu upuszczenia plików."""

    def __init__(self, directory_tree_manager, parent=None):
        super().__init__(parent)
        self.directory_tree_manager = directory_tree_manager

    def paint(self, painter, option, index):
        # Najpierw rysuj element standardowo
        super().paint(painter, option, index)

        # Jeśli ten indeks jest aktualnym celem upuszczenia, narysuj podświetlenie
        if (
            self.directory_tree_manager.highlighted_drop_index.isValid()
            and index == self.directory_tree_manager.highlighted_drop_index
        ):
            # Użyj wyraźnego koloru do podświetlenia
            painter.save()

            # Podświetlenie z ramką
            highlight_color = QColor(
                255, 165, 0, 100
            )  # Pomarańczowy z przezroczystością
            border_color = QColor(255, 140, 0, 200)  # Ciemniejszy pomarańczowy

            # Wypełnienie
            painter.fillRect(option.rect, highlight_color)

            # Ramka
            painter.setPen(border_color)
            painter.drawRect(option.rect.adjusted(0, 0, -1, -1))

            painter.restore()
            logger.debug(f"Podświetlono folder dla drop: {index.data()}")


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
        # Cache statystyk folderów
        self._folder_stats_cache = {}  # Cache statystyk
        self._stats_cache_timeout = 300  # 5 minut w sekundach

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

        # Inicjalizacja dla podświetlania celu upuszczania
        self.highlighted_drop_index = QModelIndex()

        # WŁĄCZ DropHighlightDelegate dla podświetlania podczas drag and drop
        self.drop_highlight_delegate = DropHighlightDelegate(self, self.folder_tree)
        self.folder_tree.setItemDelegate(self.drop_highlight_delegate)

        self.current_scan_path: str | None = None
        self._main_working_directory = None

        # ==================== DRAG AND DROP METHODS ====================

        self.setup_drag_and_drop_handlers()

    # ==================== NOWE METODY - FILTORY I FUNKCJONALNOŚCI ====================

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

        # Rozpocznij obliczanie statystyk dla folderów, które nie mają cache
        for folder_path in visible_folders:
            if not self.get_cached_folder_statistics(folder_path):
                self._calculate_stats_async_silent(folder_path)

    def _get_visible_folders(self) -> List[str]:
        """Pobiera listę wszystkich widocznych folderów w drzewie."""
        folders = []
        if not self._main_working_directory:
            return folders

        try:
            for root, dirs, files in os.walk(self._main_working_directory):
                # Filtruj ukryte foldery
                dirs[:] = [d for d in dirs if self.should_show_folder(d)]
                folders.append(root)

                # Ogranicz do pierwszych 20 folderów aby nie przeciążać
                if len(folders) >= 20:
                    break

        except Exception as e:
            logger.error(f"Błąd skanowania folderów: {e}")

        return folders

    def _calculate_stats_async_silent(self, folder_path: str):
        """Oblicza statystyki w tle bez interfejsu użytkownika."""

        def on_finished(stats):
            # Zapisz do cache i odśwież widok
            self.cache_folder_statistics(folder_path, stats)
            self._refresh_folder_display(folder_path)

        def on_error(error_msg):
            # Ciche ignorowanie błędów dla obliczeń w tle
            logger.debug(f"Błąd obliczeń w tle dla {folder_path}: {error_msg}")

        worker = FolderStatisticsWorker(folder_path)
        worker.custom_signals.finished.connect(on_finished)
        worker.custom_signals.error.connect(on_error)

        QThreadPool.globalInstance().start(worker)

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
            logging.info(f"🗂️ EKSPLORATOR: Próba otwarcia folderu: '{folder_path}'")

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
            logging.info(f"🗂️ EKSPLORATOR: Znormalizowana ścieżka: '{normalized_path}'")

            logging.info(f"🗂️ EKSPLORATOR: Otwieranie folderu w eksploratorze...")

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
                    logging.warning(f"🗂️ EKSPLORATOR: os.startfile nie zadziałało: {e1}")

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
            logging.error(f"🗂️ EKSPLORATOR: BŁĄD KRYTYCZNY otwierania eksploratora: {e}")
            QMessageBox.warning(
                self.parent_window,
                "Błąd",
                f"Nie można otworzyć folderu w eksploratorze:\n{e}",
            )

    def get_cached_folder_statistics(
        self, folder_path: str
    ) -> Optional[FolderStatistics]:
        """Pobiera statystyki z cache lub oblicza nowe."""
        cache_key = normalize_path(folder_path)
        current_time = time.time()

        # Sprawdź cache
        if cache_key in self._folder_stats_cache:
            cached_stats, cached_time = self._folder_stats_cache[cache_key]
            if (current_time - cached_time) < self._stats_cache_timeout:
                logger.debug(f"Cache HIT dla statystyk: {folder_path}")
                return cached_stats

        logger.debug(f"Cache MISS dla statystyk: {folder_path}")
        return None

    def cache_folder_statistics(self, folder_path: str, stats: FolderStatistics):
        """Zapisuje statystyki do cache."""
        cache_key = normalize_path(folder_path)
        self._folder_stats_cache[cache_key] = (stats, time.time())
        logger.debug(f"Zapisano do cache statystyki dla: {folder_path}")

    def calculate_folder_statistics_async(self, folder_path: str, callback=None):
        """Oblicza statystyki folderu asynchronicznie."""
        # Sprawdź cache
        cached_stats = self.get_cached_folder_statistics(folder_path)
        if cached_stats and callback:
            callback(cached_stats)
            return

        # Utwórz worker
        worker = FolderStatisticsWorker(folder_path)

        def on_finished(stats):
            # Zapisz do cache
            self.cache_folder_statistics(folder_path, stats)
            if callback:
                callback(stats)

        def on_error(error_msg):
            logger.error(f"Błąd obliczania statystyk: {error_msg}")
            if callback:
                # Zwróć puste statystyki w przypadku błędu
                callback(FolderStatistics())

        worker.custom_signals.finished.connect(on_finished)
        worker.custom_signals.error.connect(on_error)

        QThreadPool.globalInstance().start(worker)

    def refresh_folder_only(self, folder_path: str):
        """Odświeża tylko konkretny folder zamiast całego drzewa."""
        try:
            # Używając proxy model
            source_index = self.model.index(folder_path)
            if source_index.isValid():
                proxy_index = self.proxy_model.mapFromSource(source_index)
                if proxy_index.isValid():
                    # Trigger refresh tylko dla tego węzła
                    self.proxy_model.invalidate()
                    logger.debug(f"Odświeżono folder: {folder_path}")
                    return

            # Fallback - pełne odświeżenie tylko jeśli selektywne nie działa
            self.model.refresh()
            logger.debug("Fallback - pełne odświeżenie drzewa")
        except Exception as e:
            logger.error(f"Błąd odświeżania folderu {folder_path}: {e}")
            self.model.refresh()

    def init_directory_tree_async(self, current_working_directory: str):
        """Asynchroniczna wersja inicjalizacji drzewa katalogów."""
        if not current_working_directory:
            logger.warning("Brak current_working_directory - pomijam inicjalizację")
            return

        logger.debug(
            f"Asynchroniczna inicjalizacja drzewa dla: {current_working_directory}"
        )

        if not self._main_working_directory:
            self._main_working_directory = current_working_directory

            # Utwórz worker do skanowania folderów
            worker = FolderScanWorker(self._main_working_directory)

            def on_folders_scanned(folders_with_files):
                # Ustaw główny folder roboczy jako root
                source_root_index = self.model.setRootPath(self._main_working_directory)
                proxy_root_index = self.proxy_model.mapFromSource(source_root_index)
                self.folder_tree.setRootIndex(proxy_root_index)

                # Rozwiń foldery z plikami
                QTimer.singleShot(
                    100, lambda: self._expand_folders_with_files(folders_with_files)
                )

                # Rozpocznij obliczanie statystyk w tle po asynchronicznej inicjalizacji
                QTimer.singleShot(
                    500, lambda: self.start_background_stats_calculation()
                )

                logger.info(
                    f"Drzewo zainicjalizowane asynchronicznie - foldery z plikami: {len(folders_with_files)}"
                )

            def on_scan_error(error_msg):
                logger.error(f"Błąd skanowania folderów: {error_msg}")
                # Fallback - użyj synchronicznej metody
                self.init_directory_tree(current_working_directory)

            worker.custom_signals.finished.connect(on_folders_scanned)
            worker.custom_signals.error.connect(on_scan_error)

            QThreadPool.globalInstance().start(worker)
        else:
            # Dla kolejnych wywołań użyj standardowej metody
            self.init_directory_tree(current_working_directory)

    def refresh_folder_only(self, folder_path: str) -> None:
        """Odświeża tylko konkretny folder zamiast całego modelu."""
        try:
            normalized_path = normalize_path(folder_path)
            source_index = self.model.index(normalized_path)
            if source_index.isValid():
                # Wymuś odświeżenie konkretnego folderu
                self.model.setRootPath("")
                self.model.setRootPath(self._main_working_directory)

                # Invaliduj cache dla tego folderu i jego rodzica
                self.invalidate_folder_cache(normalized_path)
                parent_path = os.path.dirname(normalized_path)
                if parent_path:
                    self.invalidate_folder_cache(parent_path)

                logger.debug(f"Odświeżono folder: {normalized_path}")
            else:
                logger.warning(
                    f"Nie można znaleźć folderu do odświeżenia: {normalized_path}"
                )
        except Exception as e:
            logger.error(f"Błąd podczas odświeżania folderu {folder_path}: {e}")
            # Fallback do pełnego odświeżenia
            self.model.refresh()

    def init_directory_tree(self, current_working_directory: str):
        """
        Inicjalizuje i konfiguruje model drzewa katalogów.
        """
        logger.info(f"INIT_DIRECTORY_TREE wywołane dla: {current_working_directory}")

        if not current_working_directory:
            logging.warning("Brak current_working_directory - pomijam inicjalizację")
            return

        logging.debug(f"Inicjalizacja drzewa folderów dla: {current_working_directory}")
        logging.debug(f"Model root path przed: {self.model.rootPath()}")
        logging.debug(f"Folder tree visible: {self.folder_tree.isVisible()}")

        # Sprawdź czy to pierwszy wybór folderu roboczego
        if not self._main_working_directory:
            # Pierwsze uruchomienie - ustaw główny folder roboczy jako root
            self._main_working_directory = current_working_directory

            # Przeskanuj wszystkie podfoldery z plikami
            folders_with_files = self._scan_folders_with_files(
                self._main_working_directory
            )

            # Ustaw główny folder roboczy jako root
            self.model.setRootPath(self._main_working_directory)

            # Pobierz indeks konkretnego folderu (nie root systemu)
            source_folder_index = self.model.index(self._main_working_directory)
            proxy_folder_index = self.get_proxy_index_from_source(source_folder_index)
            self.folder_tree.setRootIndex(proxy_folder_index)

            # Rozwiń automatycznie wszystkie foldery które zawierają pliki
            QTimer.singleShot(
                100, lambda: self._expand_folders_with_files(folders_with_files)
            )

            # Rozpocznij obliczanie statystyk w tle po inicjalizacji
            QTimer.singleShot(500, lambda: self.start_background_stats_calculation())

            logging.info(
                "Drzewo katalogów zainicjalizowane - główny folder: %s, "
                "foldery z plikami: %d",
                self._main_working_directory,
                len(folders_with_files),
            )
        elif not current_working_directory.startswith(self._main_working_directory):
            # Jeśli wybrano folder poza głównym folderem roboczym
            self._main_working_directory = current_working_directory

            # Przeskanuj wszystkie podfoldery z plikami
            folders_with_files = self._scan_folders_with_files(
                self._main_working_directory
            )

            # Ustaw główny folder roboczy jako root
            self.model.setRootPath(self._main_working_directory)

            # Pobierz indeks konkretnego folderu (nie root systemu)
            source_folder_index = self.model.index(self._main_working_directory)
            proxy_folder_index = self.get_proxy_index_from_source(source_folder_index)
            self.folder_tree.setRootIndex(proxy_folder_index)

            # Rozwiń automatycznie wszystkie foldery które zawierają pliki
            QTimer.singleShot(
                100, lambda: self._expand_folders_with_files(folders_with_files)
            )

            # Rozpocznij obliczanie statystyk w tle po zmianie roota
            QTimer.singleShot(500, lambda: self.start_background_stats_calculation())

            logging.info(
                "Zmieniono root drzewa - główny folder: %s, " "foldery z plikami: %d",
                self._main_working_directory,
                len(folders_with_files),
            )

        # Zawsze zaznacz aktualny folder w drzewie
        source_index = self.model.index(current_working_directory)
        if source_index.isValid():
            proxy_index = self.get_proxy_index_from_source(source_index)
            if proxy_index.isValid():
                # Rozwiń ścieżkę do aktualnego folderu PRZED zaznaczeniem
                parent_proxy = proxy_index.parent()
                while parent_proxy.isValid():
                    self.folder_tree.expand(parent_proxy)
                    parent_proxy = parent_proxy.parent()

                # Teraz zaznacz folder
                self.folder_tree.setCurrentIndex(proxy_index)
                self.folder_tree.scrollTo(proxy_index)

                logging.info(
                    "Zaznaczono aktualny folder w drzewie: %s",
                    current_working_directory,
                )
            else:
                logging.warning(
                    "Nie można skonwertować source index na proxy index dla: %s",
                    current_working_directory,
                )
        else:
            logging.warning(
                "Nie można zaznaczyć folderu w drzewie - " "nieprawidłowy indeks: %s",
                current_working_directory,
            )

    def _scan_folders_with_files(self, root_folder: str) -> List[str]:
        """
        Skanuje rekursywnie folder roboczy i zwraca listę wszystkich
        podfolderów które zawierają min. 1 plik.
        """
        folders_with_files = []

        try:
            for root, dirs, files in os.walk(root_folder):
                # Pomiń ukryte foldery (zaczynające się od .)
                dirs[:] = [d for d in dirs if not d.startswith(".")]

                # Jeśli folder ma pliki, dodaj go do listy
                if files:
                    folders_with_files.append(root)

            logging.info(
                "Znaleziono %d folderów z plikami w: %s",
                len(folders_with_files),
                root_folder,
            )

        except Exception as e:
            logging.error("Błąd podczas skanowania folderów: %s", str(e))

        return folders_with_files

    def _expand_folders_with_files(self, folders_with_files: List[str]):
        """
        Rozwijaj foldery w drzewie które zawierają pliki.
        Zaktualizowano do pracy z proxy model.
        """
        try:
            for folder_path in folders_with_files:
                source_index = self.model.index(folder_path)
                if source_index.isValid():
                    # Konwertuj na proxy index
                    proxy_index = self.get_proxy_index_from_source(source_index)
                    if proxy_index.isValid():
                        # Rozwiń ścieżkę do tego folderu
                        parent_proxy = proxy_index.parent()
                        while parent_proxy.isValid():
                            self.folder_tree.expand(parent_proxy)
                            parent_proxy = parent_proxy.parent()

            logging.debug("Rozwinięto %d folderów z plikami", len(folders_with_files))

        except Exception as e:
            logging.error("Błąd podczas rozwijania folderów: %s", str(e))

    def show_folder_context_menu(self, position):
        """
        Wyświetla rozszerzone menu kontekstowe dla drzewa folderów.
        """
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

        logging.info(f"🗂️ MENU_KONTEKSTOWE: Proxy index jest prawidłowy: {proxy_index}")

        # Mapuj z proxy na źródłowy model
        source_index = self.proxy_model.mapToSource(proxy_index)
        if not source_index.isValid():
            logging.warning(
                f"🗂️ MENU_KONTEKSTOWE: BŁĄD - Nieprawidłowy source_index dla proxy: {proxy_index}"
            )
            return

        logging.info(
            f"🗂️ MENU_KONTEKSTOWE: Source index jest prawidłowy: {source_index}"
        )

        # Pobierz ścieżkę do wybranego folderu
        folder_path = self.model.filePath(source_index)

        logging.info(f"🗂️ MENU_KONTEKSTOWE: Pobrana ścieżka folderu: '{folder_path}'")

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

        logging.info(
            f"🗂️ MENU_KONTEKSTOWE: Folder zweryfikowany pomyślnie: '{folder_path}'"
        )

        # Tworzenie menu kontekstowego
        context_menu = QMenu()

        # ==================== NOWE FUNKCJONALNOŚCI ====================
        # NOWA FUNKCJONALNOŚĆ: Otwórz w eksploratorze
        open_explorer_action = context_menu.addAction("🗂️ Otwórz w eksploratorze")
        open_explorer_action.triggered.connect(
            lambda: self.open_folder_in_explorer(folder_path)
        )

        context_menu.addSeparator()

        # NOWA FUNKCJONALNOŚĆ: Statystyki folderu
        stats_action = context_menu.addAction("📊 Pokaż statystyki")
        stats_action.triggered.connect(lambda: self.show_folder_statistics(folder_path))

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

        QThreadPool.globalInstance().start(worker)
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
        """
        Tworzy nowy folder w wybranej lokalizacji przy użyciu workera.
        """
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
                progress_dialog.setAutoClose(
                    True
                )  # Zamknie się automatycznie po zakończeniu
                progress_dialog.setAutoReset(True)  # Zresetuje się po zakończeniu
                progress_dialog.setValue(0)  # Pokaż pasek jako zajęty

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
                        "Tworzenie folderu przerwane.", progress_dialog
                    )
                )

                # Połączenie sygnału anulowania z okna dialogowego z metodą interrupt workera
                progress_dialog.canceled.connect(worker.interrupt)

                # Uruchomienie workera
                QThreadPool.globalInstance().start(worker)
                progress_dialog.show()
            else:
                # Błąd walidacji przed utworzeniem workera (np. zła nazwa, folder nadrzędny nie istnieje)
                # Komunikat powinien być już zalogowany przez file_operations.create_folder
                # Możemy tu wyświetlić ogólny komunikat, jeśli file_operations nie wyświetla własnego
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd inicjalizacji",
                    f"Nie można zainicjować operacji tworzenia folderu '{folder_name}'. Sprawdź logi po szczegóły.",
                    QMessageBox.StandardButton.Ok,
                )

    def _handle_create_folder_finished(
        self, created_folder_path: str, progress_dialog: QProgressDialog
    ):
        logger.info(f"Pomyślnie utworzono folder: {created_folder_path}")
        progress_dialog.accept()  # Zamknij okno dialogowe

        # Użyj wydajniejszego odświeżenia tylko folderu nadrzędnego
        parent_folder = os.path.dirname(created_folder_path)
        self.refresh_folder_only(parent_folder)

        # Opcjonalnie: zaznacz nowo utworzony folder
        source_index = self.model.index(created_folder_path)
        if source_index.isValid():
            proxy_index = self.get_proxy_index_from_source(source_index)
            if proxy_index.isValid():
                self.folder_tree.setCurrentIndex(proxy_index)
                self.folder_tree.scrollTo(proxy_index)

        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie utworzono folder '{os.path.basename(created_folder_path)}'.",
        )

    def _handle_operation_error(
        self, error_message: str, title: str, progress_dialog: QProgressDialog
    ):
        logger.error(f"{title}: {error_message}")
        if progress_dialog.isVisible():
            progress_dialog.reject()  # Zamknij okno dialogowe
        QMessageBox.critical(self.parent_window, title, error_message)
        # Użyj delikatniejszego odświeżenia tylko w przypadku błędu
        if self._main_working_directory:
            self.refresh_folder_only(self._main_working_directory)

    def _handle_operation_progress(
        self, percent: int, message: str, progress_dialog: QProgressDialog
    ):
        logger.debug(f"Postęp operacji: {percent}% - {message}")
        if progress_dialog.isVisible():
            if progress_dialog.maximum() == 0:  # Jeśli pasek jest nieokreślony
                progress_dialog.setLabelText(message)
            else:
                progress_dialog.setValue(percent)
                progress_dialog.setLabelText(message)

    def _handle_operation_interrupted(
        self, message: str, progress_dialog: QProgressDialog
    ):
        logger.info(f"Operacja przerwana: {message}")
        if progress_dialog.isVisible():
            progress_dialog.reject()  # Zamknij okno dialogowe
        QMessageBox.information(self.parent_window, "Operacja przerwana", message)
        # Użyj delikatniejszego odświeżenia po przerwaniu
        if self._main_working_directory:
            self.refresh_folder_only(self._main_working_directory)

    def _handle_rename_folder_finished(
        self, old_path: str, new_path: str, progress_dialog: QProgressDialog
    ):
        logger.info(f"Pomyślnie zmieniono nazwę folderu z '{old_path}' na '{new_path}'")
        progress_dialog.accept()

        # Odśwież folder nadrzędny i invaliduj cache
        parent_folder = os.path.dirname(new_path)
        self.refresh_folder_only(parent_folder)
        self.invalidate_folder_cache(old_path)
        self.invalidate_folder_cache(new_path)

        # Zaznacz nowy folder
        source_index = self.model.index(new_path)
        if source_index.isValid():
            proxy_index = self.get_proxy_index_from_source(source_index)
            if proxy_index.isValid():
                self.folder_tree.setCurrentIndex(proxy_index)
                self.folder_tree.scrollTo(proxy_index)

        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie zmieniono nazwę folderu '{os.path.basename(old_path)}' na '{os.path.basename(new_path)}'.",
        )

    def _handle_delete_folder_finished(
        self, deleted_folder_path: str, progress_dialog: QProgressDialog
    ):
        logger.info(f"Pomyślnie usunięto folder: {deleted_folder_path}")
        progress_dialog.accept()

        # Invaliduj cache usuniętego folderu i odśwież folder nadrzędny
        self.invalidate_folder_cache(deleted_folder_path)
        parent_path = os.path.dirname(deleted_folder_path)
        if parent_path:
            self.refresh_folder_only(parent_path)
            # Ustaw indeks na folder nadrzędny
            source_index = self.model.index(parent_path)
            if source_index.isValid():
                proxy_index = self.get_proxy_index_from_source(source_index)
                if proxy_index.isValid():
                    self.folder_tree.setRootIndex(proxy_index)
        else:
            # Jeśli nie ma ścieżki nadrzędnej, odśwież cały model
            self.model.setRootPath("")
            root_index = self.model.setRootPath(self._main_working_directory or "")
            if root_index.isValid():
                proxy_root = self.get_proxy_index_from_source(root_index)
                if proxy_root.isValid():
                    self.folder_tree.setRootIndex(proxy_root)

        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie usunięto folder '{os.path.basename(deleted_folder_path)}'.",
        )

        # Sprawdź, czy current_working_directory w MainWindow nie wskazuje na usunięty folder
        # lub jego podfolder. Jeśli tak, zresetuj current_working_directory.
        if (
            self.parent_window
            and hasattr(self.parent_window, "current_working_directory")
            and self.parent_window.current_working_directory
            and (
                normalize_path(self.parent_window.current_working_directory)
                == normalize_path(deleted_folder_path)
                or normalize_path(
                    self.parent_window.current_working_directory
                ).startswith(normalize_path(deleted_folder_path) + os.sep)
            )
        ):
            logger.info(
                f"Obecny folder roboczy '{self.parent_window.current_working_directory}' znajdował się w usuniętym folderze. Resetowanie."
            )
            # Można ustawić na folder nadrzędny usuniętego folderu lub na root drzewa
            parent_of_deleted = os.path.dirname(deleted_folder_path)
            if (
                os.path.exists(parent_of_deleted)
                and parent_of_deleted != self._main_working_directory
                and parent_of_deleted.startswith(self._main_working_directory)
            ):
                self.parent_window.select_folder(
                    parent_of_deleted
                )  # Metoda w MainWindow do zmiany folderu
            elif self._main_working_directory and os.path.exists(
                self._main_working_directory
            ):
                self.parent_window.select_folder(self._main_working_directory)
            else:  # Fallback, jeśli nawet _main_working_directory nie istnieje
                self.parent_window.select_folder(self.model.rootPath())

    def rename_folder(self, folder_path: str):
        """
        Zmienia nazwę wybranego folderu przy użyciu workera.
        """
        old_name = os.path.basename(folder_path)
        new_name, ok = QInputDialog.getText(
            self.parent_window,
            "Zmień nazwę folderu",
            "Podaj nową nazwę folderu:",
            text=old_name,
        )

        if ok and new_name and new_name != old_name:
            # Normalizacja ścieżki
            folder_path_norm = normalize_path(folder_path)

            worker = file_operations.rename_folder(folder_path_norm, new_name)

            if worker:
                progress_dialog = QProgressDialog(
                    f"Zmiana nazwy folderu '{old_name}' na '{new_name}'...",
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
                    lambda old, new: self._handle_rename_folder_finished(
                        old, new, progress_dialog
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
                worker.signals.interrupted.connect(
                    lambda: self._handle_operation_interrupted(
                        "Zmiana nazwy folderu przerwana.", progress_dialog
                    )
                )
                progress_dialog.canceled.connect(worker.interrupt)

                QThreadPool.globalInstance().start(worker)
                progress_dialog.show()
            else:
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd inicjalizacji",
                    f"Nie można zainicjować operacji zmiany nazwy folderu '{old_name}'. Sprawdź logi po szczegóły.",
                    QMessageBox.StandardButton.Ok,
                )

    def delete_folder(self, folder_path: str, current_working_directory: str):
        """
        Usuwa wybrany folder po potwierdzeniu przez użytkownika, używając workera.
        """
        folder_name = os.path.basename(folder_path)
        folder_path_norm = normalize_path(folder_path)
        current_working_directory_norm = normalize_path(current_working_directory)

        if folder_path_norm == current_working_directory_norm:
            QMessageBox.warning(
                self.parent_window,
                "Nie można usunąć folderu",
                "Nie można usunąć bieżącego folderu roboczego.",
                QMessageBox.StandardButton.Ok,
            )
            return

        if self._main_working_directory and folder_path_norm == normalize_path(
            self._main_working_directory
        ):
            QMessageBox.warning(
                self.parent_window,
                "Nie można usunąć folderu",
                "Nie można usunąć głównego folderu roboczego aplikacji. Zmień najpierw główny folder roboczy.",
                QMessageBox.StandardButton.Ok,
            )
            return

        try:
            has_content = len(os.listdir(folder_path_norm)) > 0
        except OSError as e:
            logger.error(f"Błąd odczytu zawartości folderu {folder_path_norm}: {e}")
            QMessageBox.critical(
                self.parent_window,
                "Błąd odczytu folderu",
                f"Nie można odczytać zawartości folderu '{folder_name}'. Sprawdź uprawnienia i czy folder istnieje.",
            )
            return

        message = (
            f"Czy na pewno chcesz usunąć folder '{folder_name}' "
            f"i całą jego zawartość?\n\nTa operacja jest nieodwracalna!"
            if has_content
            else f"Czy na pewno chcesz usunąć pusty folder '{folder_name}'?"
        )

        reply = QMessageBox.question(
            self.parent_window,
            "Potwierdź usunięcie",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            worker = file_operations.delete_folder(folder_path_norm, has_content)

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
                    lambda path: self._handle_delete_folder_finished(
                        path, progress_dialog
                    )
                )
                worker.signals.error.connect(
                    lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd usuwania folderu", progress_dialog
                    )
                )
                worker.signals.progress.connect(
                    lambda percent, msg: self._handle_operation_progress(
                        percent, msg, progress_dialog
                    )
                )
                worker.signals.interrupted.connect(
                    lambda: self._handle_operation_interrupted(
                        "Usuwanie folderu przerwane.", progress_dialog
                    )
                )
                progress_dialog.canceled.connect(worker.interrupt)

                QThreadPool.globalInstance().start(worker)
                progress_dialog.show()
            else:
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd inicjalizacji",
                    f"Nie można zainicjować operacji usuwania folderu '{folder_name}'. Sprawdź logi po szczegóły.",
                    QMessageBox.StandardButton.Ok,
                )

    def refresh_file_pairs_after_folder_operation(self, current_working_directory: str):
        """
        Odświeża listę par plików po operacjach na folderach.
        """
        if not current_working_directory:
            logging.warning("Brak bieżącego folderu roboczego do odświeżenia.")
            return None

        # Skanuj folder na nowo
        found_pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
            current_working_directory, max_depth=0, pair_strategy="first_match"
        )

        logging.info(f"Odświeżono: {len(found_pairs)} sparowanych plików.")
        logging.info(
            f"Niesparowane: {len(unpaired_archives)} archiwów, "
            f"{len(unpaired_previews)} podglądów."
        )

        return found_pairs, unpaired_archives, unpaired_previews

    def folder_tree_item_clicked(self, proxy_index, current_working_directory: str):
        """
        Obsługuje kliknięcie elementu w drzewie folderów.
        Teraz używa proxy model - konwertuje na source index.
        """
        if not proxy_index.isValid():
            return None

        # Konwertuj proxy index na source index
        source_index = self.get_source_index_from_proxy(proxy_index)
        if not source_index.isValid():
            return None

        folder_path = self.model.filePath(source_index)
        if folder_path and os.path.isdir(folder_path):
            # Sprawdź, czy nie kliknięto tego samego folderu
            if normalize_path(folder_path) == normalize_path(current_working_directory):
                logging.debug("Kliknięto ten sam folder. Brak akcji.")
                return None

            logging.info(f"Wybrano nowy folder z drzewa: {folder_path}")
            return folder_path
        return None

    # ==================== PROXY MODEL MAPPING METHODS ====================

    def get_source_index_from_proxy(self, proxy_index: QModelIndex) -> QModelIndex:
        """Konwertuje proxy index na source index."""
        if not proxy_index.isValid():
            return QModelIndex()
        return self.proxy_model.mapToSource(proxy_index)

    def get_proxy_index_from_source(self, source_index: QModelIndex) -> QModelIndex:
        """Konwertuje source index na proxy index."""
        if not source_index.isValid():
            return QModelIndex()
        return self.proxy_model.mapFromSource(source_index)

    # ==================== DRAG AND DROP METHODS ====================

    def setup_drag_and_drop_handlers(self):
        """Konfiguruje event handlery dla drag and drop."""
        # Przypisz metody obsługi zdarzeń do drzewa folderów
        self.folder_tree.dragEnterEvent = self._drag_enter_event
        self.folder_tree.dragMoveEvent = self._drag_move_event
        self.folder_tree.dragLeaveEvent = self._drag_leave_event
        self.folder_tree.dropEvent = self._drop_event
        logger.info("Drag and drop handlers skonfigurowane")

    def _drag_enter_event(self, event: QDragEnterEvent):
        """Obsługuje wejście przeciąganego elementu nad drzewem."""
        if event.mimeData().hasUrls():
            # Sprawdź czy to są pliki (nie foldery)
            urls = event.mimeData().urls()
            has_files = any(
                os.path.isfile(url.toLocalFile()) for url in urls if url.isLocalFile()
            )

            if has_files:
                event.acceptProposedAction()
                logger.debug(f"Drag enter: Zaakceptowano {len(urls)} elementów")
            else:
                event.ignore()
                logger.debug("Drag enter: Odrzucono - brak plików")
        else:
            event.ignore()
            logger.debug("Drag enter: Odrzucono - brak URLs")

    def _drag_move_event(self, event: QDragMoveEvent):
        """Obsługuje ruch przeciąganego elementu nad drzewem."""
        if event.mimeData().hasUrls():
            # Pobierz indeks folderu pod kursorem
            index = self.folder_tree.indexAt(event.position().toPoint())

            if index.isValid():
                # Konwertuj z proxy na source index
                source_index = self.get_source_index_from_proxy(index)
                if source_index.isValid():
                    folder_path = self.model.filePath(source_index)
                    if folder_path and os.path.isdir(folder_path):
                        # Podświetl folder jako cel upuszczenia
                        if self.highlighted_drop_index != index:
                            # Usuń stare podświetlenie
                            if self.highlighted_drop_index.isValid():
                                old_index = self.highlighted_drop_index
                                self.folder_tree.update(old_index)

                            # Ustaw nowe podświetlenie
                            self.highlighted_drop_index = index
                            self.folder_tree.update(index)
                            logger.debug(f"Podświetlono folder: {folder_path}")

                        event.acceptProposedAction()
                        return

            # Usuń podświetlenie jeśli nie ma prawidłowego celu
            if self.highlighted_drop_index.isValid():
                old_index = self.highlighted_drop_index
                self.highlighted_drop_index = QModelIndex()
                self.folder_tree.update(old_index)
                logger.debug("Usunięto podświetlenie - brak prawidłowego celu")

            event.ignore()
        else:
            event.ignore()

    def _drag_leave_event(self, event: QDragLeaveEvent):
        """Obsługuje opuszczenie obszaru drzewa przez przeciągany element."""
        # Usuń podświetlenie celu upuszczania
        if self.highlighted_drop_index.isValid():
            old_index = self.highlighted_drop_index
            self.highlighted_drop_index = QModelIndex()
            self.folder_tree.update(old_index)
        event.accept()
        logger.debug("Drag leave: Wyczyszczono podświetlenie")

    def _drop_event(self, event: QDropEvent):
        """Obsługuje upuszczenie plików na folder w drzewie."""
        logger.info("=== DROP EVENT START ===")

        if not event.mimeData().hasUrls():
            event.ignore()
            logger.warning("Drop event: Brak URLs w mimeData")
            return

        # Pobierz indeks folderu docelowego
        drop_index = self.folder_tree.indexAt(event.position().toPoint())
        if not drop_index.isValid():
            event.ignore()
            logger.warning("Drop event: Nieprawidłowy indeks folderu docelowego")
            return

        # Konwertuj z proxy na source index
        source_index = self.get_source_index_from_proxy(drop_index)
        if not source_index.isValid():
            event.ignore()
            logger.warning("Drop event: Nie można skonwertować proxy index")
            return

        target_folder_path = self.model.filePath(source_index)
        if not target_folder_path or not os.path.isdir(target_folder_path):
            event.ignore()
            logger.warning(
                f"Drop event: Nieprawidłowy folder docelowy: {target_folder_path}"
            )
            return

        # Pobierz listę plików do przeniesienia
        urls = event.mimeData().urls()
        file_urls = [
            url
            for url in urls
            if url.isLocalFile() and os.path.isfile(url.toLocalFile())
        ]

        if not file_urls:
            event.ignore()
            logger.warning("Drop event: Brak plików do przeniesienia")
            return

        # Usuń podświetlenie
        if self.highlighted_drop_index.isValid():
            old_index = self.highlighted_drop_index
            self.highlighted_drop_index = QModelIndex()
            self.folder_tree.update(old_index)

        # Zaloguj informację o upuszczeniu
        file_paths = [url.toLocalFile() for url in file_urls]
        logger.info(
            f"Drop event: Upuszczono {len(file_paths)} plików na folder: {target_folder_path}"
        )
        logger.info(f"Drop event: Pliki: {file_paths}")

        # Przekaż obsługę do file_operations_ui jeśli jest dostępne
        if hasattr(self.parent_window, "file_operations_ui"):
            try:
                logger.info(
                    "Drop event: Przekazuję do file_operations_ui.handle_drop_on_folder"
                )
                result = self.parent_window.file_operations_ui.handle_drop_on_folder(
                    file_urls, target_folder_path
                )
                if result:
                    event.acceptProposedAction()
                    logger.info("Drop event: Sukces - akceptuję action")
                else:
                    event.ignore()
                    logger.warning("Drop event: file_operations_ui zwrócił False")
            except Exception as e:
                logger.error(
                    f"Drop event: Błąd podczas przekazywania do file_operations_ui: {e}"
                )
                import traceback

                traceback.print_exc()
                event.ignore()
        else:
            # Fallback - bezpośrednie przeniesienie plików
            logger.warning("Drop event: Brak file_operations_ui, używam fallback")
            event.acceptProposedAction()

        logger.info("=== DROP EVENT END ===")

    def invalidate_folder_cache(self, folder_path: str):
        """Usuwa wpis z cache statystyk dla danego folderu."""
        cache_key = normalize_path(folder_path)
        if cache_key in self._folder_stats_cache:
            del self._folder_stats_cache[cache_key]
            logger.debug(f"Invalidowano cache dla: {folder_path}")
