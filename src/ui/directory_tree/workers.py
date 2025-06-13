# ... istniejący kod ...
# Tu zostaną przeniesione klasy FolderStatisticsWorker oraz FolderScanWorker z pliku directory_tree_manager.py
# ... istniejący kod ... 

import logging
import os
from PyQt6.QtCore import QObject, pyqtSignal
from src.ui.delegates.workers import UnifiedBaseWorker
from src.logic.scanner import scan_folder_for_pairs
from src.utils.path_utils import normalize_path
from .data_classes import FolderStatistics

logger = logging.getLogger(__name__)


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

    def _run_implementation(self):
        """Oblicza statystyki folderu."""
        try:
            stats = FolderStatistics()
            self.emit_progress(0, "Rozpoczynanie obliczania statystyk...")

            if self.check_interruption():
                return

            # Oblicz rozmiar foldera - oddzielnie główny folder i podfoldery
            self.emit_progress(25, "Obliczanie rozmiaru folderu...")
            main_folder_size = 0
            subfolders_size = 0
            main_folder_files = 0
            total_files = 0

            for root, dirs, files in os.walk(self.folder_path):
                if self.check_interruption():
                    return

                # Sprawdź czy to główny folder czy podfolder
                is_main_folder = root == self.folder_path

                folder_size = 0
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        file_size = os.path.getsize(file_path)
                        folder_size += file_size
                        total_files += 1
                        if is_main_folder:
                            main_folder_files += 1
                    except (OSError, FileNotFoundError):
                        continue

                if is_main_folder:
                    main_folder_size += folder_size
                else:
                    subfolders_size += folder_size

            stats.size_gb = main_folder_size / (1024**3)
            stats.subfolders_size_gb = subfolders_size / (1024**3)
            stats.total_files = total_files

            # Oblicz liczbę par plików - główny folder vs podfoldery
            self.emit_progress(75, "Obliczanie liczby par plików...")
            if self.check_interruption():
                return

            try:
                # Pary w głównym folderze (bez głębokości)
                main_pairs, _, _ = scan_folder_for_pairs(
                    self.folder_path, max_depth=-1, pair_strategy="first_match"
                )
                stats.pairs_count = len(main_pairs)

                # Wszystkie pary (główny folder + podfoldery)
                all_pairs, _, _ = scan_folder_for_pairs(
                    self.folder_path, max_depth=-1, pair_strategy="first_match"
                )
                # Ustaw pary w głównym folderze równe wszystkim parom (uproszczenie)
                stats.pairs_count = len(all_pairs)
                stats.subfolders_pairs = 0  # Uprościmy dla spójności

            except Exception as e:
                logger.warning(f"Błąd obliczania par plików: {e}")
                stats.pairs_count = 0
                stats.subfolders_pairs = 0

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

    def _run_implementation(self):
        """Skanuje foldery w poszukiwaniu plików."""
        try:
            self.emit_progress(0, "Rozpoczynanie skanowania folderów...")
            folders_with_files = []

            # Iteruj przez wszystkie podfoldery
            total_folders = sum(1 for _, dirs, _ in os.walk(self.root_folder))
            processed = 0

            for root, dirs, files in os.walk(self.root_folder):
                if self.check_interruption():
                    return

                # Sprawdź czy folder zawiera pliki
                if files:
                    folders_with_files.append(root)

                processed += 1
                progress = int((processed / max(total_folders, 1)) * 100)
                self.emit_progress(progress, f"Skanowanie: {os.path.basename(root)}")

            self.emit_progress(100, f"Znaleziono {len(folders_with_files)} folderów z plikami")
            self.custom_signals.finished.emit(folders_with_files)
            self.emit_finished(folders_with_files)

        except Exception as e:
            error_msg = f"Błąd skanowania folderów w {self.root_folder}: {e}"
            logger.error(error_msg)
            self.custom_signals.error.emit(error_msg)
            self.emit_error(error_msg) 