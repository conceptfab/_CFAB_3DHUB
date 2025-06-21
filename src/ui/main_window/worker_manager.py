"""
WorkerManager - zarządzanie workerami i wątkami.
🚀 ETAP 1: Refaktoryzacja MainWindow - komponenty zarządzania wątkami
"""

import logging
from functools import partial
from typing import List

from PyQt6.QtCore import QThread, QThreadPool

from src.ui.delegates.workers import (
    DataProcessingWorker,
    ManuallyPairFilesWorker,
    SaveMetadataWorker,
    UnifiedBaseWorker,
)
from src.ui.delegates.workers.worker_factory import WorkerFactory


class WorkerManager:
    """
    Zarządzanie workerami i wątkami w aplikacji CFAB_3DHUB.

    Odpowiedzialności:
    - Zarządzanie wątkami skanowania i przetwarzania danych
    - Konfiguracja połączeń sygnałów workerów
    - Bezpieczne zamykanie wątków
    - Obsługa błędów workerów
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
                "Poprzedni worker przetwarzania nadal działa - "
                "przerywam go i uruchamiam nowy"
            )
            # Przerwij poprzedni worker
            if self.data_processing_worker:
                try:
                    self.data_processing_worker.finished.disconnect()
                except (TypeError, AttributeError):
                    pass  # Sygnał może być już odłączony
                self.data_processing_worker.stop()

            # Zakończ poprzedni wątek
            self.data_processing_thread.quit()
            if not self.data_processing_thread.wait(
                self.main_window.app_config.thread_wait_timeout_ms
            ):  # Czekaj maksymalnie według konfiguracji
                self.logger.warning("Wymuszenie zakończenia poprzedniego workera")
                self.data_processing_thread.terminate()
                self.data_processing_thread.wait()

        self.data_processing_thread = QThread()
        self.data_processing_worker = DataProcessingWorker(
            self.main_window.controller.current_directory, file_pairs
        )
        self.data_processing_worker.moveToThread(self.data_processing_thread)

        # Podłączenie sygnałów
        self.data_processing_worker.tile_data_ready.connect(
            self.main_window.gallery_manager.create_tile_widget_for_pair
        )
        # NOWY: obsługa batch processing kafelków
        self.data_processing_worker.tiles_batch_ready.connect(
            self.main_window.tile_manager.create_tile_widgets_batch
        )
        # NOWY: obsługa odświeżania istniejących kafelków po wczytaniu metadanych
        self.data_processing_worker.tiles_refresh_needed.connect(
            self.main_window.tile_manager.refresh_existing_tiles
        )
        self.data_processing_worker.finished.connect(
            self.main_window._on_tile_data_processed
        )
        # NAPRAWKA: Podłącz sygnały postępu do pasków postępu
        self.data_processing_worker.progress.connect(self.main_window._show_progress)
        self.data_processing_worker.error.connect(self.main_window._handle_worker_error)
        self.data_processing_thread.started.connect(self.data_processing_worker.run)

        self.data_processing_thread.start()
        self.logger.info(
            f"Uruchomiono nowy worker do przetwarzania {len(file_pairs)} par plików"
        )

    def start_data_processing_worker_without_tree_reset(self, file_pairs: list):
        """
        Inicjalizuje i uruchamia workera do przetwarzania danych BEZ resetowania drzewa katalogów.
        Używane przy zmianie folderu z drzewa aby zachować strukturę.

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
                "i uruchamiam nowy (bez resetowania drzewa)"
            )
            # Przerwij poprzedni worker
            if self.data_processing_worker:
                try:
                    self.data_processing_worker.finished.disconnect()
                except (TypeError, AttributeError):
                    pass  # Sygnał może być już odłączony
                self.data_processing_worker.stop()

            # Zakończ poprzedni wątek
            self.data_processing_thread.quit()
            if not self.data_processing_thread.wait(
                self.main_window.app_config.thread_wait_timeout_ms
            ):  # Czekaj maksymalnie według konfiguracji
                self.logger.warning("Wymuszenie zakończenia poprzedniego workera")
                self.data_processing_thread.terminate()
                self.data_processing_thread.wait()

        self.data_processing_thread = QThread()
        self.data_processing_worker = DataProcessingWorker(
            self.main_window.controller.current_directory, file_pairs
        )
        self.data_processing_worker.moveToThread(self.data_processing_thread)

        # Podłączenie sygnałów
        self.data_processing_worker.tile_data_ready.connect(
            self.main_window.gallery_manager.create_tile_widget_for_pair
        )
        # NOWY: obsługa batch processing kafelków
        self.data_processing_worker.tiles_batch_ready.connect(
            self.main_window.tile_manager.create_tile_widgets_batch
        )
        # NOWY: obsługa odświeżania istniejących kafelków po wczytaniu metadanych
        self.data_processing_worker.tiles_refresh_needed.connect(
            self.main_window.tile_manager.refresh_existing_tiles
        )
        # RÓŻNICA: Podłącz do metody BEZ resetowania drzewa (wrapper ignoruje listę)
        self.data_processing_worker.finished.connect(
            self.main_window._on_tile_data_processed
        )
        # NAPRAWKA: Podłącz sygnały postępu do pasków postępu
        self.data_processing_worker.progress.connect(self.main_window._show_progress)
        self.data_processing_worker.error.connect(self.main_window._handle_worker_error)
        self.data_processing_thread.started.connect(self.data_processing_worker.run)

        self.data_processing_thread.start()
        self.logger.info(
            f"Uruchomiono nowy worker do przetwarzania {len(file_pairs)} "
            "par plików (bez resetowania drzewa)"
        )

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

        from src.ui.delegates.workers.scan_workers import ScanDirectoryWorker

        # Przerwij stary worker jeśli istnieje
        if self.scan_thread and self.scan_thread.isRunning():
            self.scan_thread.quit()
            self.scan_thread.wait()

        self.scan_thread = QThread()
        self.scan_worker = ScanDirectoryWorker(directory_path)
        self.scan_worker.moveToThread(self.scan_thread)

        # Podłącz sygnały
        self.scan_worker.signals.finished.connect(
            self.main_window.controller._on_scan_worker_finished
        )
        self.scan_worker.signals.progress.connect(self.main_window._show_progress)
        self.scan_worker.signals.error.connect(self.main_window._handle_worker_error)
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)

        self.scan_thread.start()
        self.logger.info(f"Uruchomiono asynchroniczne skanowanie dla: {directory_path}")
