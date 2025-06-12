"""
Definicje bazowe dla workerów - klasy abstrakcyjne i pomocnicze.
"""

import logging
import time
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal
from PyQt6.QtGui import QPixmap

logger = logging.getLogger(__name__)


class UnifiedWorkerSignals(QObject):
    """
    ZUNIFIKOWANE sygnały dla wszystkich workerów.
    Obsługuje zarówno standardowe workery jak i thumbnail workery.
    """
    
    # Standardowe sygnały dla wszystkich workerów
    finished = pyqtSignal(object)  # uniwersalny typ wyniku
    error = pyqtSignal(str)  # komunikat błędu
    progress = pyqtSignal(int, str)  # procent, wiadomość
    interrupted = pyqtSignal()  # sygnał przerwania
    
    # Rozszerzone sygnały dla thumbnail workerów
    thumbnail_finished = pyqtSignal(QPixmap, str, int, int)  # pixmap, path, width, height
    thumbnail_error = pyqtSignal(str, str, int, int)  # error_message, path, width, height
    
    # Rozszerzone sygnały dla scan workerów 
    scan_finished = pyqtSignal(list, list, list)  # found_pairs, unpaired_archives, unpaired_previews


class UnifiedBaseWorker(QRunnable):
    """
    Zunifikowana klasa bazowa dla wszystkich workerów.

    Dodaje funkcjonalności:
    - Walidacja parametrów wejściowych w konstruktorze
    - Batching sygnałów postępu
    - Rozszerzone logowanie
    """

    def __init__(self):
        super().__init__()
        self.signals = UnifiedWorkerSignals()  # ZUNIFIKOWANE sygnały
        self._interrupted = False
        self._worker_name = self.__class__.__name__
        self._last_progress_time = 0
        self._progress_interval_ms = 100  # Minimalny odstęp między sygnałami (ms)
        # Walidacja w konstruktorze została przeniesiona do metody run

    def _validate_inputs(self):
        """Override w klasach pochodnych dla walidacji."""
        pass

    def check_interruption(self) -> bool:
        """
        Sprawdza czy worker został przerwany.

        Returns:
            True jeśli przerwano, False w przeciwnym razie
        """
        if self._interrupted:
            logger.debug(f"{self._worker_name}: Operacja przerwana")
            self.signals.interrupted.emit()
            return True
        return False

    def interrupt(self):
        """Przerywa wykonywanie workera."""
        self._interrupted = True
        logger.debug(f"{self._worker_name}: Otrzymano żądanie przerwania")

    def emit_progress(self, percent: int, message: str):
        """Emituje sygnał postępu z logowaniem."""
        logger.debug(f"{self._worker_name}: Postęp {percent}% - {message}")
        self.signals.progress.emit(percent, message)

    def emit_progress_batched(self, current: int, total: int, message: str):
        """Emituje sygnał postępu z limitem częstotliwości."""
        current_time = time.time() * 1000  # Czas w milisekundach

        # Zawsze emituj pierwszy (0%) i ostatni (100%) progress oraz co _progress_interval_ms
        percent = int((current / max(total, 1)) * 100)
        is_first = current == 0
        is_last = current >= total

        if (
            is_first
            or is_last
            or (current_time - self._last_progress_time) >= self._progress_interval_ms
        ):
            self.emit_progress(percent, message)
            self._last_progress_time = current_time

    def emit_error(self, message: str, exception: Exception = None):
        """Emituje sygnał błędu z logowaniem."""
        if exception:
            logger.error(f"{self._worker_name}: {message}", exc_info=True)
        else:
            logger.error(f"{self._worker_name}: {message}")
        self.signals.error.emit(message)

    def emit_finished(self, result=None):
        """Emituje sygnał zakończenia z logowaniem."""
        logger.info(f"{self._worker_name}: Zakończono pomyślnie")
        self.signals.finished.emit(result)

    def emit_interrupted(self):
        """Emituje sygnał przerwania z logowaniem."""
        logger.info(f"{self._worker_name}: Operacja przerwana")
        self.signals.interrupted.emit()

    def run(self):
        """
        Główna metoda workera - do implementacji w klasach pochodnych.

        Powinny używać metod check_interruption(), emit_progress(), emit_error(), emit_finished()
        """
        raise NotImplementedError(
            "Metoda run() musi być zaimplementowana w klasie pochodnej"
        )


class TransactionalWorker(UnifiedBaseWorker):
    """
    Worker z możliwością wykonywania operacji z automatycznym rollbackiem.

    Pozwala na bezpieczne wykonanie sekwencji operacji z gwarancją, że w przypadku
    błędu wszystkie wykonane wcześniej operacje zostaną cofnięte w odwrotnej kolejności.
    """

    def __init__(self):
        super().__init__()
        self._operations_log = []  # Log wykonanych operacji

    def execute_with_rollback(self, operation_func, rollback_func, *args, **kwargs):
        """
        Wykonuje operację z możliwością cofnięcia.

        Args:
            operation_func: Funkcja wykonująca operację
            rollback_func: Funkcja cofająca operację
            *args, **kwargs: Argumenty przekazywane do operation_func

        Returns:
            Wynik działania operation_func

        Raises:
            Exception: Gdy operation_func rzuci wyjątek, po wykonaniu rollbacku
        """
        try:
            result = operation_func(*args, **kwargs)
            self._operations_log.append(
                (operation_func, rollback_func, args, kwargs, result)
            )
            return result
        except Exception as e:
            logger.error(f"Błąd podczas wykonywania operacji: {e}", exc_info=True)
            self._rollback_operations()
            raise e

    def _rollback_operations(self):
        """Cofa wykonane operacje w odwrotnej kolejności."""
        logger.info(f"Rozpoczęcie wycofywania {len(self._operations_log)} operacji")

        for i, (op_func, rollback_func, args, kwargs, result) in enumerate(
            reversed(self._operations_log)
        ):
            try:
                logger.debug(
                    f"Wycofywanie operacji {len(self._operations_log)-i}/{len(self._operations_log)}"
                )
                rollback_func(result, *args, **kwargs)
            except Exception as e:
                logger.error(f"Błąd podczas cofania operacji: {e}", exc_info=True)
                # Kontynuuj próby rollbacku dla pozostałych operacji

        # Wyczyść log po rollbacku
        self._operations_log.clear()
        logger.info("Zakończono wycofywanie operacji")


class WorkerPriority:
    """Priorytety dla workerów."""

    LOW = 0
    NORMAL = 1
    HIGH = 2 