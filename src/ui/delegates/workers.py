"""
Workers do obsługi zadań w tle.
"""

import logging

from PyQt6.QtCore import QObject, pyqtSignal

from src.logic import metadata_manager
from src.logic.scanner import scan_folder_for_pairs
from src.models.file_pair import FilePair


class ScanFolderWorker(QObject):
    """
    Worker do skanowania folderu w osobnym wątku.
    """

    # Sygnał emitowany po zakończeniu:
    # found_pairs, unpaired_archives, unpaired_previews
    finished = pyqtSignal(list, list, list)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.directory_to_scan = None
        self._should_stop = False

    def run(self):
        """
        Wykonuje skanowanie folderu.
        """
        if not self.directory_to_scan:
            self.error.emit("Nie określono folderu do skanowania.")
            return

        if self._should_stop:
            return

        try:
            logging.debug(
                f"Rozpoczynanie skanowania folderu: "
                f"{self.directory_to_scan} w wątku."
            )
            result = scan_folder_for_pairs(
                self.directory_to_scan, max_depth=0, pair_all=False
            )
            found_pairs, unpaired_archives, unpaired_previews = result
            if not self._should_stop:
                self.finished.emit(found_pairs, unpaired_archives, unpaired_previews)
        except Exception as e:
            if not self._should_stop:
                err_msg = (
                    f"Błąd podczas skanowania folderu "
                    f"'{self.directory_to_scan}' w wątku: {e}"
                )
                logging.error(err_msg)
                self.error.emit(err_msg)

    def stop(self):
        """Przerywa skanowanie."""
        self._should_stop = True


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
