"""
Workery do skanowania folderów i zarządzania plikami.
"""

import logging
import os
from PyQt6.QtCore import QThreadPool

from .base_workers import UnifiedBaseWorker
from src.ui.delegates.scanner_worker import ScanFolderWorkerQRunnable
from src.logic.scanner_core import scan_folder_for_pairs
from src.models.file_pair import FilePair
from src.services.scanning_service import ScanResult
from src.ui.directory_tree.data_classes import FolderStatistics

logger = logging.getLogger(__name__)


class ScanFolderWorker(UnifiedBaseWorker):
    """
    Worker do skanowania folderów w celu znalezienia par plików.
    Obudowuje ScanFolderWorkerQRunnable, który wykonuje właściwą pracę.
    """

    def __init__(self, directory_to_scan=None):
        """
        Inicjalizuje worker do skanowania folderów.

        Args:
            directory_to_scan: Katalog do przeskanowania (opcjonalny)
        """
        super().__init__()
        self.directory_to_scan = directory_to_scan
        self._worker = None

    def _validate_inputs(self):
        """
        Waliduje parametry wejściowe.
        
        Brak directory_to_scan jest dozwolony (zostanie użyty ostatni skonfigurowany).
        """
        pass  # Brak wymaganych parametrów

    def _on_worker_finished(self, found_pairs, unpaired_archives, unpaired_previews):
        """Obsługuje sygnał zakończenia skanowania."""
        logger.info(
            f"Skanowanie zakończone. Znaleziono: {len(found_pairs)} par, "
            f"{len(unpaired_archives)} niepowiązanych archiwów, "
            f"{len(unpaired_previews)} niepowiązanych podglądów"
        )
        self.signals.scan_finished.emit(found_pairs, unpaired_archives, unpaired_previews)
        self.emit_finished([found_pairs, unpaired_archives, unpaired_previews])

    def _on_worker_error(self, error_message):
        """Obsługuje sygnał błędu skanowania."""
        self.emit_error(error_message)

    def _on_worker_progress(self, percent, message):
        """Obsługuje sygnał postępu skanowania."""
        self.emit_progress(percent, message)

    def _on_worker_interrupted(self):
        """Obsługuje sygnał przerwania skanowania."""
        self.emit_interrupted()

    def stop(self):
        """Zatrzymuje skanowanie."""
        if self._worker:
            logger.debug("Przerywanie skanowania folderów")
            self._worker.interrupt()

    def run(self):
        """Skanuje folder w poszukiwaniu par plików."""
        try:
            self._validate_inputs()
            
            # Inicjalizacja właściwego workera
            self._worker = ScanFolderWorkerQRunnable(
                directory_to_scan=self.directory_to_scan
            )
            
            # Podłączanie sygnałów
            self._worker.signals.finished.connect(self._on_worker_finished)
            self._worker.signals.error.connect(self._on_worker_error)
            self._worker.signals.progress.connect(self._on_worker_progress)
            self._worker.signals.interrupted.connect(self._on_worker_interrupted)
            
            # Propagacja sygnału przerwania
            if self._interrupted:
                self._worker.interrupt()
            
            # Uruchomienie skanowania
            self._worker.run()
            
        except Exception as e:
            self.emit_error(f"Błąd podczas uruchamiania skanowania: {str(e)}", e)


class ScanDirectoryWorker(UnifiedBaseWorker):
    """Worker do asynchronicznego skanowania katalogu."""

    def __init__(self, directory_path: str, max_depth: int = -1):
        """
        Inicjalizuje worker.

        Args:
            directory_path: Ścieżka do katalogu do przeskanowania.
            max_depth: Maksymalna głębokość skanowania.
        """
        super().__init__()
        self.directory_path = directory_path
        self.max_depth = max_depth
        self.signals.moveToMainThread()

    def _run_implementation(self) -> ScanResult:
        """
        Wykonuje skanowanie w osobnym wątku.
        """
        self.emit_progress(0, f"Skanowanie: {os.path.basename(self.directory_path)}...")
        
        file_pairs, unpaired_archives, unpaired_previews, special_folders = scan_folder_for_pairs(
            directory=self.directory_path,
            max_depth=self.max_depth,
            progress_callback=self.emit_progress,
        )

        scan_result = ScanResult(
            directory_path=self.directory_path,
            file_pairs=file_pairs,
            unpaired_archives=unpaired_archives,
            unpaired_previews=unpaired_previews,
            special_folders=special_folders,
        )

        self.emit_progress(100, f"Znaleziono {len(scan_result.file_pairs)} par")
        return scan_result 