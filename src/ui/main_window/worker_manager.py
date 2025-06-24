"""
WorkerManager - zarządzanie workerami i wątkami.
🚀 ETAP 1: Refaktoryzacja MainWindow - komponenty zarządzania wątkami
🚨 EMERGENCY BUG FIX: Naprawiono zawieszanie przy 1418+ parach plików
"""

import logging
import threading
import time
from enum import Enum
from functools import partial
from typing import List

from PyQt6.QtCore import QThreadPool, QTimer

from src.ui.delegates.workers import ManuallyPairFilesWorker, SaveMetadataWorker
from src.ui.delegates.workers.base_workers import UnifiedBaseWorker
from src.ui.delegates.workers.worker_factory import WorkerFactory


class WorkerState(Enum):
    """Worker state enumeration for state machine."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    CANCELLING = "cancelling"
    FINISHED = "finished"
    ERROR = "error"


class MemoryMonitor:
    """Memory monitoring with circuit breaker for large operations."""

    def __init__(self, memory_limit_mb=1500):  # 1.5GB limit
        self.memory_limit_mb = memory_limit_mb
        self.high_memory_warnings = 0
        self.circuit_open = False

    def check_memory_status(self) -> dict:
        """Check current memory status and return metrics."""
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            status = {
                "memory_mb": memory_mb,
                "limit_mb": self.memory_limit_mb,
                "usage_percent": (memory_mb / self.memory_limit_mb) * 100,
                "high_usage": memory_mb > (self.memory_limit_mb * 0.8),
                "critical_usage": memory_mb > self.memory_limit_mb,
                "circuit_open": self.circuit_open,
            }

            # Circuit breaker logic
            if status["critical_usage"]:
                self.high_memory_warnings += 1
                if self.high_memory_warnings >= 3:  # 3 strikes rule
                    self.circuit_open = True
                    status["circuit_triggered"] = True
            else:
                # Reset counter if memory usage drops
                if memory_mb < (self.memory_limit_mb * 0.7):
                    self.high_memory_warnings = 0
                    self.circuit_open = False

            return status

        except Exception as e:
            return {"error": str(e), "memory_mb": 0, "circuit_open": False}


class WorkerManager:
    """
    Zarządzanie workerami i wątkami w aplikacji CFAB_3DHUB.

    Odpowiedzialności:
    - Zarządzanie wątkami skanowania i przetwarzania danych
    - Konfiguracja połączeń sygnałów workerów
    - Bezpieczne zamykanie wątków
    - Obsługa błędów workerów
    - EMERGENCY: Adaptive timeout + cancel mechanism dla dużych folderów
    - Memory monitoring z circuit breaker pattern
    """

    def __init__(self, main_window):
        """
        Inicjalizuje WorkerManager.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.thread_pool = QThreadPool.globalInstance()
        self.worker_factory = WorkerFactory(main_window)
        self.active_workers = []  # KRYTYCZNA NAPRAWKA: Przechowuj referencje
        self.logger = logging.getLogger(__name__)

        # Referencje do wątków
        self.scan_thread = None
        self.scan_worker = None
        self.data_processing_thread = None
        self.data_processing_worker = None

        # EMERGENCY: Worker state management
        self._worker_state = WorkerState.IDLE
        self._state_lock = threading.RLock()
        self._worker_metrics = {
            "start_time": None,
            "pairs_processed": 0,
            "memory_peak": 0,
            "errors_count": 0,
        }

        # EMERGENCY: Memory monitoring
        self.memory_monitor = MemoryMonitor(memory_limit_mb=1500)  # 1.5GB limit

        # Start memory monitoring timer
        self._memory_timer = QTimer()
        self._memory_timer.timeout.connect(self._check_memory_pressure)
        self._memory_timer.start(10000)  # Check every 10 seconds

        # EMERGENCY: Processing state tracking
        self._processing_start_time = None
        self._adaptive_timeout = None
        self._processing_cancelled = False

    def _transition_worker_state(self, new_state: WorkerState, reason: str = ""):
        """Thread-safe worker state transition with logging."""
        with self._state_lock:
            old_state = self._worker_state
            self._worker_state = new_state

            self.logger.info(
                f"Worker state: {old_state.value} → {new_state.value}"
                + (f" ({reason})" if reason else "")
            )

            # Reset metrics on new operation
            if new_state == WorkerState.STARTING:
                self._worker_metrics = {
                    "start_time": time.time(),
                    "pairs_processed": 0,
                    "memory_peak": 0,
                    "errors_count": 0,
                }

    def is_worker_busy(self) -> bool:
        """Check if worker is currently busy (thread-safe)."""
        with self._state_lock:
            return self._worker_state in [
                WorkerState.STARTING,
                WorkerState.RUNNING,
                WorkerState.CANCELLING,
            ]

    def _check_memory_pressure(self):
        """Monitor memory pressure and trigger circuit breaker if needed."""
        status = self.memory_monitor.check_memory_status()

        if status.get("circuit_triggered"):
            self.logger.error(
                f"CIRCUIT BREAKER: Memory limit exceeded ({status['memory_mb']:.0f}MB), "
                f"cancelling operation"
            )
            self._emergency_cancel_operation()

            # Show user-friendly message
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self.main_window,
                "Błąd pamięci",
                f"Operacja została anulowana z powodu zbyt wysokiego zużycia pamięci "
                f"({status['memory_mb']:.0f}MB).\n\n"
                f"Spróbuj ponownie z mniejszym folderem lub zamknij inne aplikacje.",
            )

        elif status.get("high_usage"):
            self.logger.warning(
                f"HIGH MEMORY USAGE: {status['memory_mb']:.0f}MB "
                f"({status['usage_percent']:.1f}%)"
            )

            # Trigger aggressive garbage collection
            import gc

            gc.collect()

    def get_performance_metrics(self) -> dict:
        """Get comprehensive performance metrics for debugging."""
        with self._state_lock:
            memory_status = self.memory_monitor.check_memory_status()

            return {
                "worker_state": self._worker_state.value,
                "memory_status": memory_status,
                "worker_metrics": self._worker_metrics.copy(),
                "active_workers": len(self.active_workers),
                "thread_pool_active": QThreadPool.globalInstance().activeThreadCount(),
            }

    def _handle_emergency_cancel(self):
        """EMERGENCY: Handle emergency cancel - NO TIMEOUT."""
        self.logger.warning("EMERGENCY: Manual cancel operation")

        self._processing_cancelled = True

        # Force cancel worker
        if self.data_processing_worker:
            try:
                self.data_processing_worker.emergency_cancel()
            except Exception as e:
                self.logger.error(f"Emergency cancel failed: {e}")

        # Hide progress
        self.main_window.progress_manager.hide_progress()

    def _emergency_cancel_operation(self):
        """User-triggered emergency cancel."""
        self.logger.warning("User triggered emergency cancel")
        self._handle_emergency_cancel()

    def _safe_batch_processing_wrapper(self, original_method):
        """Wrapper for safe batch processing with chunking for large datasets."""

        def chunked_batch_processor(file_pairs_batch):
            num_pairs = len(file_pairs_batch)

            # ADAPTIVE CHUNKING: Smaller chunks for larger datasets
            if num_pairs > 1000:
                chunk_size = 25  # Very small chunks for huge datasets
            elif num_pairs > 500:
                chunk_size = 50  # Medium chunks for large datasets
            else:
                chunk_size = 100  # Original size for normal datasets

            # Process in chunks to prevent UI blocking
            for i in range(0, len(file_pairs_batch), chunk_size):
                if self._processing_cancelled:
                    self.logger.warning("Batch processing cancelled by user")
                    return

                chunk = file_pairs_batch[i : i + chunk_size]

                try:
                    # Call original method with smaller chunk
                    original_method(chunk)

                    # Allow UI to process events after each chunk
                    from PyQt6.QtWidgets import QApplication

                    QApplication.processEvents()

                    # Memory cleanup after every 5 chunks for large datasets
                    if (i // chunk_size) % 5 == 0 and num_pairs > 1000:
                        import gc

                        gc.collect()

                except Exception as e:
                    self.logger.error(
                        f"Chunk processing error at {i}-{i+chunk_size}: {e}"
                    )
                    # Continue with next chunk instead of failing completely
                    continue

                # Brief pause for very large datasets to prevent system overload
                if num_pairs > 2000:
                    time.sleep(0.01)  # 10ms pause

        return chunked_batch_processor

    def _safe_tile_creation_wrapper(self, original_method):
        """Wrapper for safe tile creation with error handling."""

        def safe_tile_creator(*args, **kwargs):
            try:
                if not self._processing_cancelled:
                    original_method(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"Safe tile creation error: {e}")

        return safe_tile_creator

    def _enhanced_progress_handler(self, percent, message):
        """Enhanced progress handling with stall detection."""
        current_time = time.time()

        # Track progress for stall detection
        if not hasattr(self, "_last_progress_time"):
            self._last_progress_time = current_time
            self._last_progress_percent = 0

        # No progress stall detection - let it run indefinitely

        self._last_progress_time = current_time
        self._last_progress_percent = percent

        # Enhanced progress reporting
        if hasattr(self.main_window, "_show_progress"):
            # Add memory usage info for large operations
            if len(getattr(self, "file_pairs", [])) > 1000:
                try:
                    import psutil

                    memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
                    enhanced_message = f"{message} (RAM: {memory_mb:.0f}MB)"
                    self.main_window._show_progress(percent, enhanced_message)
                except:
                    self.main_window._show_progress(percent, message)
            else:
                self.main_window._show_progress(percent, message)

    def _on_worker_finished_with_cleanup(self, processed_pairs):
        """Enhanced worker finished handler with metrics."""
        try:
            with self._state_lock:
                if self._worker_state == WorkerState.CANCELLING:
                    self.logger.info("Worker finished after cancellation")
                    self._transition_worker_state(WorkerState.FINISHED, "cancelled")
                else:
                    self.logger.info(
                        f"Worker completed successfully: {len(processed_pairs)} pairs"
                    )
                    self._transition_worker_state(WorkerState.FINISHED, "success")

                # Log performance metrics
                if self._worker_metrics["start_time"]:
                    duration = time.time() - self._worker_metrics["start_time"]
                    pairs_per_second = (
                        len(processed_pairs) / duration if duration > 0 else 0
                    )

                    self.logger.info(
                        f"Worker performance: {len(processed_pairs)} pairs in {duration:.1f}s "
                        f"({pairs_per_second:.1f} pairs/s)"
                    )

            # Cleanup and call original handler
            self._cleanup_worker_resources()
            self.main_window._on_tile_data_processed(processed_pairs)

        except Exception as e:
            self.logger.error(f"Worker cleanup error: {e}")
            self._transition_worker_state(WorkerState.ERROR, f"cleanup failed: {e}")

    def _cleanup_worker_resources(self):
        """Comprehensive worker resource cleanup."""
        # Stop timeout timer
        if hasattr(self, "_timeout_timer") and self._timeout_timer.isActive():
            self._timeout_timer.stop()

        # Hide cancel button
        if hasattr(self.main_window, "cancel_operation_button"):
            self.main_window.cancel_operation_button.setVisible(False)

        # Reset worker references
        self.data_processing_worker = None
        self.data_processing_thread = None

        # Force garbage collection for memory cleanup
        import gc

        gc.collect()

    def _handle_worker_error_with_recovery(self, error_message):
        """Enhanced error handling with recovery."""
        self.logger.error(f"Worker error with recovery: {error_message}")
        self._transition_worker_state(WorkerState.ERROR, error_message)
        self._cleanup_worker_resources()

        # Call original error handler
        if hasattr(self.main_window, "_handle_worker_error"):
            self.main_window._handle_worker_error(error_message)

    def _on_worker_finished(self, worker):
        """
        Slot wywoływany, gdy worker zakończy pracę.
        Usuwa workera z listy aktywnych, aby zapobiec wyciekom pamięci.
        """
        try:
            self.active_workers.remove(worker)
            self.logger.debug(
                f"Worker {type(worker).__name__} zakończył i został usunięty z listy aktywnych."
            )
        except ValueError:
            self.logger.warning(
                f"Próbowano usunąć workera, którego nie ma na liście: {worker}"
            )

    def run_worker(
        self,
        worker_class,
        on_finished=None,
        on_error=None,
        show_progress=False,
        **kwargs,
    ):
        """
        Tworzy i uruchamia workera w tle, obsługując standardowe sygnały.

        Args:
            worker_class: Klasa workera do utworzenia.
            on_finished: Opcjonalny callback dla sygnału 'finished'.
            on_error: Opcjonalny callback dla sygnału 'error'.
            show_progress: Czy pokazywać pasek postępu.
            **kwargs: Argumenty do przekazania do konstruktora workera.
        """
        try:
            # Przekaż kwargs do fabryki workera
            worker = self.worker_factory.create_worker(worker_class, **kwargs)
            if not worker:
                self.logger.error(
                    f"Nie udało się utworzyć workera klasy {worker_class.__name__}"
                )
                return

            # Podłącz standardowe sygnały za pomocą uniwersalnej metody
            self.setup_worker_connections(
                worker,
                on_finished=on_finished,
                on_error=on_error,
                show_progress=show_progress,
            )

            # Podłącz sygnał finished do metody czyszczącej
            worker.signals.finished.connect(partial(self._on_worker_finished, worker))

            # Dodaj workera do listy aktywnych
            self.active_workers.append(worker)

            self.thread_pool.start(worker)
            self.logger.info(
                f"Uruchomiono nowego workera: {worker_class.__name__} "
                f"(liczba aktywnych: {len(self.active_workers)})"
            )
        except Exception as e:
            self.logger.error(
                f"Błąd podczas uruchamiania workera {worker_class.__name__}: {e}",
                exc_info=True,
            )

    def cleanup_threads(self):
        """Zatrzymuje i czyści wszystkie aktywne wątki."""
        # Ta metoda może wymagać rozbudowy w zależności od potrzeb
        self.main_window.progress_manager.hide_progress()

        # Prawidłowy sposób na wymuszenie zapisu bufora przy zamykaniu
        if (
            self.main_window.controller
            and self.main_window.controller.current_directory
        ):
            from src.logic.metadata_manager import MetadataManager

            metadata_manager = MetadataManager.get_instance(
                self.main_window.controller.current_directory
            )
            metadata_manager.force_save()

    def start_data_processing_worker(self, file_pairs: list):
        """
        Inicjalizuje i uruchamia workera do przetwarzania danych.
        Używane przy zmianie folderu z galerii.

        Args:
            file_pairs: Lista obiektów FilePair do przetworzenia
        """
        # NAPRAWKA PROGRESS BAR: Resetuj progress bar na 0% przed rozpoczęciem
        self.main_window._show_progress(0, "Przygotowywanie...")

        # NAPRAWKA: Resetuj liczniki progress bara na początku operacji
        if hasattr(self.main_window, "_batch_processing_started"):
            delattr(self.main_window, "_batch_processing_started")

        # NAPRAWKA: Prawidłowo zakończ poprzedni worker jeśli nadal działa
        if self.data_processing_thread and self.data_processing_thread.isRunning():
            self.logger.warning(
                "Poprzedni worker przetwarzania nadal działa - przerywam go "
                "i uruchamiam nowy"
            )
            # Przerwij poprzedni worker
            if self.data_processing_worker:
                try:
                    self.data_processing_worker.signals.finished.disconnect()
                except (TypeError, AttributeError):
                    pass  # Sygnał może być już odłączony
                self.data_processing_worker.interrupt()

            # Zakończ poprzedni wątek
            self.data_processing_thread.quit()
            if not self.data_processing_thread.wait(
                self.main_window.app_config.thread_wait_timeout_ms
            ):  # Czekaj maksymalnie według konfiguracji
                self.logger.warning("Wymuszenie zakończenia poprzedniego workera")
                self.data_processing_thread.terminate()
                self.data_processing_thread.wait()

        # UNIFIED: Używamy UnifiedBaseWorker z QThreadPool
        from PyQt6.QtCore import QThreadPool

        from src.ui.delegates.workers.processing_workers import DataProcessingWorker

        self.logger.debug(f"Tworzenie DataProcessingWorker z {len(file_pairs)} parami")

        self.data_processing_worker = DataProcessingWorker(
            self.main_window.controller.current_directory, file_pairs
        )

        self.logger.debug("DataProcessingWorker utworzony, podłączanie sygnałów")

        # Podłączenie sygnałów
        self.data_processing_worker.signals.tile_data_ready.connect(
            self.main_window.gallery_manager.create_tile_widget_for_pair
        )
        # NOWY: obsługa batch processing kafelków
        self.data_processing_worker.signals.tiles_batch_ready.connect(
            self.main_window.tile_manager.create_tile_widgets_batch
        )
        # NOWY: obsługa odświeżania istniejących kafelków po wczytaniu metadanych
        self.data_processing_worker.signals.tiles_refresh_needed.connect(
            self.main_window.tile_manager.refresh_existing_tiles
        )
        self.data_processing_worker.signals.finished.connect(
            self.main_window._on_tile_data_processed
        )
        # NAPRAWKA: Podłącz sygnały postępu do pasków postępu
        self.data_processing_worker.signals.progress.connect(
            self.main_window._show_progress
        )
        self.data_processing_worker.signals.error.connect(
            self.main_window._handle_worker_error
        )

        self.logger.debug("Sygnały podłączone, uruchamianie przez QThreadPool")

        # UNIFIED: Uruchom przez QThreadPool
        QThreadPool.globalInstance().start(self.data_processing_worker)

        self.logger.debug("DataProcessingWorker uruchomiony przez QThreadPool")
        self.logger.info(
            f"Uruchomiono nowy worker do przetwarzania {len(file_pairs)} par plików"
        )

    def start_data_processing_worker_without_tree_reset(self, file_pairs: list):
        """
        EMERGENCY FIX: Adaptive timeout + cancel mechanism dla dużych folderów.
        Inicjalizuje i uruchamia workera do przetwarzania danych BEZ resetowania drzewa katalogów.
        """
        # Prevent multiple concurrent workers
        if self.is_worker_busy():
            self.logger.warning(
                f"Worker already busy ({self._worker_state.value}). "
                f"Cancelling current operation first."
            )
            self._emergency_cancel_operation()

            # Wait up to 5 seconds for cancellation
            timeout = 5.0
            start_wait = time.time()
            while self.is_worker_busy() and (time.time() - start_wait) < timeout:
                time.sleep(0.1)

            if self.is_worker_busy():
                self.logger.error("Failed to cancel previous worker - forcing cleanup")
                self._transition_worker_state(WorkerState.ERROR, "force cleanup")
                return

                # NO TIMEOUT - operacja będzie wykonana do końca
        num_pairs = len(file_pairs)

        # EMERGENCY: Add processing tracking
        self._processing_start_time = time.time()
        self._processing_cancelled = False

        # Transition to starting state
        self._transition_worker_state(WorkerState.STARTING, f"{len(file_pairs)} pairs")

        # NAPRAWKA PROGRESS BAR: Resetuj progress bar na 0% przed rozpoczęciem
        self.main_window._show_progress(0, "Przygotowywanie...")

        # Emergency cleanup poprzedniego workera z force termination
        if self.data_processing_thread and self.data_processing_thread.isRunning():
            self.logger.error(
                f"EMERGENCY: Force terminating previous worker after {adaptive_timeout}s"
            )
            # Set cancel flag for current worker
            if self.data_processing_worker:
                try:
                    self.data_processing_worker.signals.finished.disconnect()
                    self.data_processing_worker.emergency_cancel()  # New method
                except (TypeError, AttributeError):
                    pass

            # Force terminate thread
            self.data_processing_thread.terminate()
            self.data_processing_thread.wait(5000)  # 5s max wait

        # Create worker without timeout
        from src.ui.delegates.workers.processing_workers import DataProcessingWorker

        self.data_processing_worker = DataProcessingWorker(
            self.main_window.controller.current_directory, file_pairs
        )

        # Enhanced signal connections with error handling
        try:
            # Existing connections with emergency wrapper
            self.data_processing_worker.signals.tile_data_ready.connect(
                self._safe_tile_creation_wrapper(
                    self.main_window.gallery_manager.create_tile_widget_for_pair
                )
            )

            # CHUNKED batch processing for large datasets
            self.data_processing_worker.signals.tiles_batch_ready.connect(
                self._safe_batch_processing_wrapper(
                    self.main_window.tile_manager.create_tile_widgets_batch
                )
            )

            # NOWY: obsługa odświeżania istniejących kafelków po wczytaniu metadanych
            self.data_processing_worker.signals.tiles_refresh_needed.connect(
                self.main_window.tile_manager.refresh_existing_tiles
            )

            self.data_processing_worker.signals.finished.connect(
                self._on_worker_finished_with_cleanup
            )

            self.data_processing_worker.signals.progress.connect(
                self._enhanced_progress_handler
            )

            self.data_processing_worker.signals.error.connect(
                self._handle_worker_error_with_recovery
            )

        except Exception as e:
            self.logger.error(f"EMERGENCY: Signal connection failed: {e}")
            self._handle_emergency_cancel()  # Trigger emergency cleanup
            return

        # UNIFIED: Uruchom przez QThreadPool z resource monitoring
        try:
            QThreadPool.globalInstance().start(self.data_processing_worker)

            # Set state to running after successful start
            self._transition_worker_state(WorkerState.RUNNING, "worker started")

            self.logger.info(
                f"STARTED: DataProcessingWorker for {len(file_pairs)} pairs"
            )

            # Enable cancel button in UI
            if hasattr(self.main_window, "cancel_operation_button"):
                self.main_window.cancel_operation_button.setVisible(True)
                self.main_window.cancel_operation_button.clicked.connect(
                    self._emergency_cancel_operation
                )

        except Exception as e:
            self.logger.error(f"EMERGENCY: Failed to start worker: {e}")
            self._transition_worker_state(WorkerState.ERROR, f"start failed: {e}")
            self._handle_emergency_cancel()

    def setup_worker_connections(
        self,
        worker: UnifiedBaseWorker,
        on_finished=None,
        on_error=None,
        show_progress=False,
    ):
        """
        Uniwersalna metoda do konfigurowania połączeń sygnałów dla workera.

        Args:
            worker: Instancja workera (dziedzicząca po UnifiedBaseWorker).
            on_finished: Opcjonalny slot do podłączenia do sygnału 'finished'.
            on_error: Opcjonalny slot do podłączenia do sygnału 'error'.
            show_progress: Czy pokazywać pasek postępu.
        """
        if on_finished:
            worker.signals.finished.connect(on_finished)
        if on_error:
            worker.signals.error.connect(on_error)
        else:
            # Domyślna obsługa błędów, jeśli nie podano własnej
            worker.signals.error.connect(self.main_window._handle_worker_error)

        if show_progress:
            worker.signals.progress.connect(self.main_window._show_progress)
            # Domyślnie ukryj progress bar po zakończeniu
            worker.signals.finished.connect(
                self.main_window.progress_manager.hide_progress
            )
            worker.signals.error.connect(
                self.main_window.progress_manager.hide_progress
            )

    def start_save_metadata_worker(self, file_pair, new_value, value_type):
        """Uruchamia worker do zapisu metadanych."""
        self.run_worker(
            SaveMetadataWorker,
            file_pair=file_pair,
            new_value=new_value,
            value_type=value_type,
        )

    def start_bulk_delete_worker(self, pairs_to_delete):
        """Uruchamia worker do usuwania wielu par plików."""
        from src.ui.delegates.workers.bulk_workers import BulkDeleteWorker

        # Uruchom worker do usuwania
        worker = self.run_worker(
            BulkDeleteWorker,
            pairs_to_delete=pairs_to_delete,
            show_progress=True,
            on_finished=self.main_window._on_bulk_delete_finished,
        )

        # Połączenia dla ManuallyPairFilesWorker (jeśli worker to ten typ)
        if isinstance(worker, ManuallyPairFilesWorker):
            worker.pairing_finished.connect(
                self.main_window.file_operations_coordinator.handle_manual_pairing_finished
            )
            worker.tile_widget_factory = (
                self.main_window.gallery_manager.create_tile_widget_for_pair
            )

    def scan_directory(self, directory: str, reset_tree: bool = True):
        """Uruchamia skanowanie katalogu w tle."""
        # ... existing code ...

    def save_metadata_for_pair(self, file_pair, new_value, value_type):
        """Uruchamia workera do zapisu metadanych dla pojedynczej pary."""
        self.run_worker(
            SaveMetadataWorker,
            file_pair=file_pair,
            new_value=new_value,
            value_type=value_type,
        )

    def force_save_metadata(self):
        """Uruchamia workera, aby wymusić zapis wszystkich buforowanych metadanych."""
        self.run_worker(SaveMetadataWorker, force_save=True)

    def get_active_workers_info(self) -> List[str]:
        """Zwraca informacje o aktywnych workerach (do debugowania)."""
        # ... existing code ...

    def start_directory_scan_worker(self, directory_path: str):
        """
        Uruchamia workera do asynchronicznego skanowania katalogu.
        """
        if self.scan_worker and self.scan_worker.isRunning():
            self.logger.warning("Skanowanie katalogu jest już w toku.")
            return

        from PyQt6.QtCore import QThreadPool

        from src.ui.delegates.workers.scan_workers import ScanDirectoryWorker

        # Przerwij stary worker jeśli istnieje
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.quit()
            self.scan_thread.wait()

        # UNIFIED: Używamy UnifiedBaseWorker z QThreadPool
        self.scan_worker = ScanDirectoryWorker(directory_path)

        # Podłącz sygnały
        self.scan_worker.signals.finished.connect(
            self.main_window.controller._on_scan_worker_finished
        )
        self.scan_worker.signals.progress.connect(self.main_window._show_progress)
        self.scan_worker.signals.error.connect(self.main_window._handle_worker_error)

        # UNIFIED: Uruchom przez QThreadPool
        QThreadPool.globalInstance().start(self.scan_worker)

        self.logger.info(f"Uruchomiono asynchroniczne skanowanie dla: {directory_path}")
