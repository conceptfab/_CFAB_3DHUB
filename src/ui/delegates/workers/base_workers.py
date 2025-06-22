"""
Definicje bazowe dla workerów - klasy abstrakcyjne i pomocnicze.
"""

import logging
import threading
import time
from typing import Any, Callable, Optional

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal
from PyQt6.QtGui import QPixmap

from src.models.file_pair import FilePair

logger = logging.getLogger(__name__)

# Globalne locki dla shared resources
_metadata_manager_lock = threading.RLock()
_thumbnail_cache_lock = threading.RLock()
_file_operations_lock = threading.RLock()


class WorkerPriority:
    """Priorytety dla workerów."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3  # Nowy priorytet dla krytycznych operacji


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
    timeout = pyqtSignal(str)  # sygnał timeout z opisem

    # Rozszerzone sygnały dla thumbnail workerów
    thumbnail_finished = pyqtSignal(
        QPixmap, str, int, int
    )  # pixmap, path, width, height
    thumbnail_error = pyqtSignal(
        str, str, int, int
    )  # error_message, path, width, height

    # Rozszerzone sygnały dla scan workerów
    scan_finished = pyqtSignal(
        list, list, list
    )  # found_pairs, unpaired_archives, unpaired_previews

    # Rozszerzone sygnały dla DataProcessingWorker
    tile_data_ready = pyqtSignal(FilePair)  # pojedynczy FilePair
    tiles_batch_ready = pyqtSignal(list)  # lista FilePair
    tiles_refresh_needed = pyqtSignal(list)  # lista FilePair do odświeżenia


class UnifiedBaseWorker(QRunnable):
    """
    Zunifikowana klasa bazowa dla wszystkich workerów.

    Dodaje funkcjonalności:
    - Walidacja parametrów wejściowych w konstruktorze
    - Batching sygnałów postępu
    - Rozszerzone logowanie
    - Timeout handling
    - Resource protection
    - Priorytetyzacja
    """

    def __init__(
        self,
        timeout_seconds: Optional[int] = None,
        priority: int = WorkerPriority.NORMAL,
    ):
        super().__init__()
        self.signals = UnifiedWorkerSignals()  # ZUNIFIKOWANE sygnały
        self._interrupted = False
        self._worker_name = self.__class__.__name__
        self._last_progress_time = 0
        self._progress_interval_ms = 100  # Minimalny odstęp między sygnałami (ms)
        self._start_time = None
        self._timeout_seconds = timeout_seconds
        self._priority = priority

        # Ustaw priorytet QRunnable
        if priority == WorkerPriority.HIGH:
            self.setAutoDelete(True)
        elif priority == WorkerPriority.LOW:
            self.setAutoDelete(True)

    def _validate_inputs(self):
        """Override w klasach pochodnych dla walidacji."""
        pass

    def check_interruption(self) -> bool:
        """
        Sprawdza czy worker został przerwany lub przekroczył timeout.

        Returns:
            True jeśli przerwano lub timeout, False w przeciwnym razie
        """
        if self._interrupted:
            logger.debug(f"{self._worker_name}: Operacja przerwana")
            self.signals.interrupted.emit()
            return True

        # Sprawdź timeout
        if self._timeout_seconds and self._start_time:
            elapsed = time.time() - self._start_time
            if elapsed > self._timeout_seconds:
                logger.warning(
                    f"{self._worker_name}: Przekroczono timeout "
                    f"({self._timeout_seconds}s)"
                )
                self.signals.timeout.emit(
                    f"Operacja przekroczyła limit czasu ({self._timeout_seconds}s)"
                )
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
        if self._start_time:
            elapsed = time.time() - self._start_time
            logger.debug(f"{self._worker_name}: OK w {elapsed:.2f}s")
        else:
            logger.debug(f"{self._worker_name}: OK")
        self.signals.finished.emit(result)

    def emit_interrupted(self):
        """Emituje sygnał przerwania z logowaniem."""
        logger.info(f"{self._worker_name}: Operacja przerwana")
        self.signals.interrupted.emit()

    def with_metadata_lock(self, func: Callable, *args, **kwargs) -> Any:
        """Wykonuje funkcję z lockiem na metadata_manager."""
        with _metadata_manager_lock:
            return func(*args, **kwargs)

    def with_thumbnail_cache_lock(self, func: Callable, *args, **kwargs) -> Any:
        """Wykonuje funkcję z lockiem na thumbnail_cache."""
        with _thumbnail_cache_lock:
            return func(*args, **kwargs)

    def with_file_operations_lock(self, func: Callable, *args, **kwargs) -> Any:
        """Wykonuje funkcję z lockiem na file operations."""
        with _file_operations_lock:
            return func(*args, **kwargs)

    def run(self):
        """
        Główna metoda workera - do implementacji w klasach pochodnych.

        Powinny używać metod check_interruption(), emit_progress(),
        emit_error(), emit_finished()
        """
        self._start_time = time.time()
        logger.debug(f"{self._worker_name}: Start (priorytet: {self._priority})")

        try:
            self._run_implementation()
        except Exception as e:
            self.emit_error(f"Nieoczekiwany błąd: {str(e)}", e)
        finally:
            if self._start_time:
                elapsed = time.time() - self._start_time
                logger.debug(
                    f"{self._worker_name}: Całkowity czas wykonania: " f"{elapsed:.2f}s"
                )

    def _run_implementation(self):
        """
        Implementacja konkretnego workera - do override w klasach pochodnych.
        """
        raise NotImplementedError(
            "Metoda _run_implementation() musi być zaimplementowana "
            "w klasie pochodnej"
        )


class AsyncUnifiedBaseWorker(UnifiedBaseWorker):
    """
    Rozszerzona wersja UnifiedBaseWorker z obsługą operacji asynchronicznych.
    """

    def __init__(
        self,
        timeout_seconds: Optional[int] = None,
        priority: int = WorkerPriority.NORMAL,
    ):
        super().__init__(timeout_seconds, priority)
        self._async_operations = []

    async def run_async_operation(
        self, operation_func: Callable, *args, **kwargs
    ) -> Any:
        """
        Wykonuje operację asynchroniczną z obsługą timeout i przerwania.
        """
        import asyncio

        try:
            if self._timeout_seconds:
                result = await asyncio.wait_for(
                    operation_func(*args, **kwargs), timeout=self._timeout_seconds
                )
            else:
                result = await operation_func(*args, **kwargs)
            return result
        except asyncio.TimeoutError:
            self.signals.timeout.emit(
                f"Operacja asynchroniczna przekroczyła timeout "
                f"({self._timeout_seconds}s)"
            )
            raise
        except Exception as e:
            self.emit_error(f"Błąd operacji asynchronicznej: {str(e)}", e)
            raise


class TransactionalWorker(UnifiedBaseWorker):
    """
    Worker z możliwością wykonywania operacji z automatycznym rollbackiem.

    Pozwala na bezpieczne wykonanie sekwencji operacji z gwarancją, że w przypadku
    błędu wszystkie wykonane wcześniej operacje zostaną cofnięte w odwrotnej kolejności.
    """

    def __init__(
        self,
        timeout_seconds: Optional[int] = None,
        priority: int = WorkerPriority.NORMAL,
    ):
        super().__init__(timeout_seconds, priority)
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
                    f"Wycofywanie operacji "
                    f"{len(self._operations_log)-i}/{len(self._operations_log)}"
                )
                rollback_func(result, *args, **kwargs)
            except Exception as e:
                logger.error(f"Błąd podczas cofania operacji: {e}", exc_info=True)
                # Kontynuuj próby rollbacku dla pozostałych operacji

        # Wyczyść log po rollbacku
        self._operations_log.clear()
        logger.info("Zakończono wycofywanie operacji")


class BatchOperationMixin:
    """
    Mixin dla workerów wykonujących operacje wsadowe.
    Dodaje funkcjonalności grupowania operacji dla lepszej wydajności.
    """

    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size
        self._current_batch = []

    def add_to_batch(self, operation_data: Any):
        """Dodaje operację do aktualnego batch'a."""
        self._current_batch.append(operation_data)

        if len(self._current_batch) >= self.batch_size:
            self.process_batch()

    def process_batch(self):
        """Przetwarza aktualny batch operacji."""
        if not self._current_batch:
            return

        try:
            self._process_batch_implementation(self._current_batch)
        finally:
            self._current_batch.clear()

    def finalize_batches(self):
        """Przetwarza pozostałe operacje w batch'u."""
        if self._current_batch:
            self.process_batch()

    def _process_batch_implementation(self, batch_data: list):
        """Implementacja przetwarzania batch'a - do override."""
        raise NotImplementedError(
            "Metoda _process_batch_implementation() musi być zaimplementowana"
        )
