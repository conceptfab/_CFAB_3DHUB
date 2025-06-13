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
        """
        🚀 OPTYMALIZACJA: Oblicza statystyki folderu w JEDNYM przejściu os.walk
        zamiast dwóch oddzielnych - ~50% szybciej!
        """
        try:
            stats = FolderStatistics()
            self.emit_progress(0, "Rozpoczynanie zoptymalizowanego obliczania statystyk...")

            if self.check_interruption():
                return

            # 🔥 OPTYMALIZACJA: Jednorazowe skanowanie plików z klasyfikacją typów
            self.emit_progress(20, "Skanowanie plików (optymalizowane)...")
            
            # Zbierz statystyki podstawowe w jednym przejściu
            main_folder_size = 0
            subfolders_size = 0
            total_files = 0
            main_folder_files = 0
            
            # Kontenery na pliki według typów (dla szybkiego obliczania par)
            archive_files = []
            preview_files = []
            
            # Rozszerzenia archiwów i podglądów (zgodne z logiką aplikacji)
            archive_extensions = {'.rar', '.zip', '.7z', '.max', '.3ds', '.fbx', '.obj'}
            preview_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}

            for root, dirs, files in os.walk(self.folder_path):
                if self.check_interruption():
                    return

                is_main_folder = root == self.folder_path
                folder_size = 0

                for file in files:
                    file_path = os.path.join(root, file)
                    file_name = file.lower()
                    
                    try:
                        # Oblicz rozmiar
                        file_size = os.path.getsize(file_path)
                        folder_size += file_size
                        total_files += 1
                        
                        if is_main_folder:
                            main_folder_files += 1
                            
                        # Klasyfikuj typ pliku dla obliczania par
                        file_ext = os.path.splitext(file_name)[1].lower()
                        if file_ext in archive_extensions:
                            archive_files.append(file_path)
                        elif file_ext in preview_extensions:
                            preview_files.append(file_path)
                            
                    except (OSError, FileNotFoundError):
                        continue

                if is_main_folder:
                    main_folder_size += folder_size
                else:
                    subfolders_size += folder_size

            # Ustaw podstawowe statystyki
            stats.size_gb = main_folder_size / (1024**3)
            stats.subfolders_size_gb = subfolders_size / (1024**3)
            # NAPRAWKA: total_size_gb to readonly property - usuń przypisanie
            # stats.total_size_gb = (main_folder_size + subfolders_size) / (1024**3)  # BŁĄD - to property!
            stats.total_files = total_files

            self.emit_progress(70, "Obliczanie par plików (szybka metoda)...")
            
            # 🔥 OPTYMALIZACJA: Szybkie obliczanie par bez pełnego skanowania
            if self.check_interruption():
                return
                
            try:
                # Szybka metoda - pary bazowane na nazwach bazowych
                pairs_count = 0
                
                # Utwórz mapę nazw bazowych archiwów
                archive_basenames = {}
                for archive_path in archive_files:
                    basename = os.path.splitext(os.path.basename(archive_path))[0].lower()
                    if basename not in archive_basenames:
                        archive_basenames[basename] = []
                    archive_basenames[basename].append(archive_path)
                
                # Znajdź dopasowania w podglądach
                for preview_path in preview_files:
                    basename = os.path.splitext(os.path.basename(preview_path))[0].lower()
                    if basename in archive_basenames:
                        pairs_count += 1
                
                stats.pairs_count = pairs_count
                # NAPRAWKA: total_pairs to readonly property - usuń przypisanie
                # stats.total_pairs = pairs_count  # BŁĄD - to property!
                stats.subfolders_pairs = 0  # Można rozszerzyć w przyszłości
                
                logger.debug(f"📊 OPTYMALIZOWANE statystyki {os.path.basename(self.folder_path)}: "
                           f"{pairs_count} par, {total_files} plików, {stats.total_size_gb:.2f}GB")
                
            except Exception as e:
                logger.warning(f"Błąd szybkiego obliczania par: {e}")
                stats.pairs_count = 0
                # NAPRAWKA: total_pairs to readonly property - usuń przypisanie
                # stats.total_pairs = 0  # BŁĄD - to property!
                stats.subfolders_pairs = 0

            self.emit_progress(100, "Zakończono zoptymalizowane obliczanie statystyk")
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