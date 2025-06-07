"""
Workers do obsługi zadań w tle.
"""

import logging

from PyQt6.QtCore import QObject, QThreadPool, pyqtSignal

from src.logic import metadata_manager
from src.models.file_pair import FilePair
from src.ui.delegates.scanner_worker import ScanFolderWorkerQRunnable


class ScanFolderWorker(QObject):
    """
    Worker do skanowania folderu w osobnym wątku.

    Ta klasa jest kompatybilna wstecz z istniejącym kodem, ale wewnętrznie
    wykorzystuje nową implementację ScanFolderWorkerQRunnable.
    """

    # Sygnały emitowane przez worker
    finished = pyqtSignal(
        list, list, list
    )  # found_pairs, unpaired_archives, unpaired_previews
    error = pyqtSignal(str)  # komunikat błędu
    progress = pyqtSignal(int, str)  # procent, wiadomość
    interrupted = pyqtSignal()  # sygnał przerwania

    def __init__(self, parent=None):
        super().__init__(parent)
        self.directory_to_scan = None
        self._should_stop = False
        self._thread_pool = QThreadPool()
        self._current_worker = None

    def run(self):
        """
        Wykonuje skanowanie folderu.

        Wewnętrznie używa ScanFolderWorkerQRunnable uruchamianego w QThreadPool.
        """
        if not self.directory_to_scan:
            self.error.emit("Nie określono folderu do skanowania.")
            return

        if self._should_stop:
            self.interrupted.emit()
            return

        try:
            logging.debug(
                f"Rozpoczynanie skanowania folderu: "
                f"{self.directory_to_scan} w wątku."
            )

            # Tworzymy i konfigurujemy worker
            self._current_worker = ScanFolderWorkerQRunnable(
                directory=self.directory_to_scan,
                max_depth=0,  # Domyślnie skanujemy tylko bieżący folder
                pair_strategy="first_match",
            )

            # Podłączamy sygnały
            self._current_worker.signals.finished.connect(self._on_worker_finished)
            self._current_worker.signals.error.connect(self._on_worker_error)
            self._current_worker.signals.progress.connect(self._on_worker_progress)
            self._current_worker.signals.interrupted.connect(
                self._on_worker_interrupted
            )

            # Jeśli już ustawiono flagę przerwania, przekazujemy ją do workera
            if self._should_stop:
                self._current_worker.interrupt()

            # Uruchamiamy worker w puli wątków
            self._thread_pool.start(self._current_worker)

        except Exception as e:
            logging.error(f"Błąd podczas uruchamiania skanowania: {e}", exc_info=True)
            self.error.emit(f"Wystąpił błąd podczas uruchamiania skanowania: {str(e)}")

    def _on_worker_finished(self, found_pairs, unpaired_archives, unpaired_previews):
        """Obsługuje sygnał zakończenia pracy workera."""
        if not self._should_stop:
            self.finished.emit(found_pairs, unpaired_archives, unpaired_previews)

    def _on_worker_error(self, error_message):
        """Obsługuje sygnał błędu z workera."""
        self.error.emit(error_message)

    def _on_worker_progress(self, percent, message):
        """Obsługuje sygnał postępu z workera."""
        self.progress.emit(percent, message)

    def _on_worker_interrupted(self):
        """Obsługuje sygnał przerwania z workera."""
        self.interrupted.emit()

    def stop(self):
        """Przerywa wykonywanie skanowania."""
        self._should_stop = True
        if self._current_worker:
            self._current_worker.interrupt()


class DataProcessingWorker(QObject):
    """
    Worker do przetwarzania danych w tle. Odpowiedzialny za:
    1. Zastosowanie metadanych do par plików (operacja I/O).
    2. Emitowanie sygnałów do tworzenia kafelków w głównym wątku.
    """

    tile_data_ready = pyqtSignal(FilePair)
    finished = pyqtSignal()

    def __init__(self, working_directory: str, file_pairs: list[FilePair], parent=None):
        super().__init__(parent)
        self.working_directory = working_directory
        self.file_pairs = file_pairs

    def run(self):
        """Główna metoda workera."""
        try:
            # 1. Zastosuj metadane (ciężka operacja I/O)
            if self.file_pairs:
                logging.info("DataProcessingWorker: Rozpoczynam stosowanie metadanych.")
                metadata_manager.apply_metadata_to_file_pairs(
                    self.working_directory, self.file_pairs
                )
                logging.info("DataProcessingWorker: Zakończono stosowanie metadanych.")

            # 2. Emituj sygnały do tworzenia kafelków
            if self.file_pairs:
                logging.debug(
                    f"DataProcessingWorker: Rozpoczynam przygotowanie "
                    f"{len(self.file_pairs)} kafelków."
                )
                for file_pair in self.file_pairs:
                    self.tile_data_ready.emit(file_pair)
            else:
                logging.debug("DataProcessingWorker: Brak par plików do przetworzenia.")

        except Exception as e:
            logging.error(f"Błąd w DataProcessingWorker: {e}")
        finally:
            self.finished.emit()
