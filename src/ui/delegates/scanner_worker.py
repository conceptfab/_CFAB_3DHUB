"""
Implementacja workera do skanowania folderów w tle.
"""

import logging
from typing import Callable, List, Optional

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from src.logic.scanner import ScanningInterrupted, scan_folder_for_pairs
from src.models.file_pair import FilePair

logger = logging.getLogger(__name__)


class ScanWorkerSignals(QObject):
    """
    Sygnały dla ScanFolderWorkerQRunnable.
    """

    # Sygnały
    progress = pyqtSignal(int, str)  # procent, wiadomość
    finished = pyqtSignal(list, list, list)  # pary, niesparowane archiwa, niesparowane podglądy
    error = pyqtSignal(str)  # komunikat błędu
    interrupted = pyqtSignal()  # sygnał przerwania


class ScanFolderWorkerQRunnable(QRunnable):
    """
    Worker do wykonywania skanowania folderów w tle.
    
    Klasa ta dziedziczy po QRunnable, co pozwala na uruchamianie jej
    przez QThreadPool, zapewniając asynchroniczne wykonanie.
    """

    def __init__(
        self,
        directory: str,
        max_depth: int = -1,
        use_cache: bool = True,
        pair_strategy: str = "first_match",
        force_refresh_cache: bool = False,
    ):
        """
        Inicjalizuje worker do skanowania folderu.
        
        Args:
            directory: Ścieżka do skanowanego katalogu
            max_depth: Maksymalna głębokość rekursji, -1 oznacza brak limitu
            use_cache: Czy używać buforowanych wyników jeśli są dostępne
            pair_strategy: Strategia parowania plików
            force_refresh_cache: Czy wymusić odświeżenie cache
        """
        super().__init__()
        
        # Parametry skanowania
        self.directory = directory
        self.max_depth = max_depth
        self.use_cache = use_cache
        self.pair_strategy = pair_strategy
        self.force_refresh_cache = force_refresh_cache
        
        # Flaga przerwania
        self._should_stop = False
        
        # Sygnały
        self.signals = ScanWorkerSignals()

    def interrupt(self):
        """
        Przerywa wykonywanie skanowania.
        """
        self._should_stop = True
        logger.info("Wysłano żądanie przerwania skanowania")

    def _interrupt_check(self) -> bool:
        """
        Funkcja sprawdzająca, czy skanowanie powinno zostać przerwane.
        
        Returns:
            True, jeśli skanowanie powinno zostać przerwane, False w przeciwnym razie
        """
        return self._should_stop

    @pyqtSlot()
    def run(self):
        """
        Wykonuje skanowanie folderu w tle.
        
        Emituje sygnały:
        - progress: podczas skanowania
        - finished: po zakończeniu
        - error: w przypadku błędu
        - interrupted: jeśli skanowanie zostało przerwane
        """
        try:
            if not self.directory:
                self.signals.error.emit("Nie określono folderu do skanowania.")
                return

            if self._should_stop:
                self.signals.interrupted.emit()
                return

            # Funkcja callback do raportowania postępu
            def report_progress(percent: int, message: str):
                self.signals.progress.emit(percent, message)

            try:
                logger.info(f"Rozpoczynam skanowanie folderu: {self.directory} w wątku.")
                result = scan_folder_for_pairs(
                    directory=self.directory,
                    max_depth=self.max_depth,
                    use_cache=self.use_cache,
                    pair_strategy=self.pair_strategy,
                    interrupt_check=self._interrupt_check,
                    force_refresh_cache=self.force_refresh_cache,
                    progress_callback=report_progress,
                )
                
                if self._should_stop:
                    self.signals.interrupted.emit()
                    return
                    
                found_pairs, unpaired_archives, unpaired_previews = result
                self.signals.finished.emit(found_pairs, unpaired_archives, unpaired_previews)
                
            except ScanningInterrupted:
                logger.warning("Skanowanie zostało przerwane.")
                self.signals.interrupted.emit()
                
            except Exception as e:
                logger.error(f"Błąd podczas skanowania: {e}", exc_info=True)
                self.signals.error.emit(f"Wystąpił błąd podczas skanowania: {str(e)}")
                
        except Exception as e:
            logger.critical(f"Krytyczny błąd w funkcji run workera: {e}", exc_info=True)
            self.signals.error.emit(f"Krytyczny błąd: {str(e)}")
