"""
Workery do skanowania folderów i zarządzania plikami.
"""

import logging

from .base_workers import UnifiedBaseWorker
from src.ui.delegates.scanner_worker import ScanFolderWorkerQRunnable

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