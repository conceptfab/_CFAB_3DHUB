"""
WorkerManager - zarządzanie workerami i wątkami.
🚀 ETAP 1: Refaktoryzacja MainWindow - komponenty zarządzania wątkami
"""

import logging
from PyQt6.QtCore import QThread
from src.ui.delegates.workers import DataProcessingWorker, UnifiedBaseWorker


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
        self.logger = logging.getLogger(__name__)
        
        # Referencje do wątków
        self.scan_thread = None
        self.scan_worker = None
        self.data_processing_thread = None
        self.data_processing_worker = None

    def cleanup_threads(self):
        """
        Czyści wszystkie aktywne wątki - Problem #3: używa ThreadCoordinator.
        """
        # Użyj ThreadCoordinator zamiast ręcznego zarządzania
        if hasattr(self.main_window, "thread_coordinator"):
            self.main_window.thread_coordinator.cleanup_all_threads()
        else:
            # Fallback - stary sposób dla kompatybilności
            if self.scan_thread and self.scan_thread.isRunning():
                self.logger.info("Kończenie wątku skanowania przy zamykaniu aplikacji...")
                self.scan_thread.quit()
                if not self.scan_thread.wait(self.main_window.app_config.thread_wait_timeout_ms):
                    self.logger.warning("Wątek skanowania nie zakończył się, wymuszam...")
                    self.scan_thread.terminate()
                    self.scan_thread.wait()

            if self.data_processing_thread and self.data_processing_thread.isRunning():
                self.logger.info(
                    "Kończenie wątku przetwarzania przy zamykaniu aplikacji..."
                )
                self.data_processing_thread.quit()
                if not self.data_processing_thread.wait(
                    self.main_window.app_config.thread_wait_timeout_ms
                ):
                    self.logger.warning(
                        "Wątek przetwarzania nie zakończył się, wymuszam..."
                    )
                    self.data_processing_thread.terminate()
                    self.data_processing_thread.wait()

    def start_data_processing_worker(self, file_pairs: list):
        """
        Inicjalizuje i uruchamia workera do przetwarzania danych.
        
        Args:
            file_pairs: Lista obiektów FilePair do przetworzenia
        """
        # NAPRAWKA: Resetuj liczniki progress bara na początku operacji
        if hasattr(self.main_window, "_batch_processing_started"):
            delattr(self.main_window, "_batch_processing_started")
        
        # NAPRAWKA: Prawidłowo zakończ poprzedni worker jeśli nadal działa
        if self.data_processing_thread and self.data_processing_thread.isRunning():
            self.logger.warning(
                "Poprzedni worker przetwarzania nadal działa - przerywam go i uruchamiam nowy"
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
            self.main_window._create_tile_widget_for_pair
        )
        # NOWY: obsługa batch processing kafelków
        self.data_processing_worker.tiles_batch_ready.connect(
            self.main_window._create_tile_widgets_batch
        )
        self.data_processing_worker.finished.connect(self.main_window._on_tile_loading_finished)
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
        # NAPRAWKA: Resetuj liczniki progress bara na początku operacji
        if hasattr(self.main_window, "_batch_processing_started"):
            delattr(self.main_window, "_batch_processing_started")
            
        # NAPRAWKA: Prawidłowo zakończ poprzedni worker jeśli nadal działa
        if self.data_processing_thread and self.data_processing_thread.isRunning():
            self.logger.warning(
                "Poprzedni worker przetwarzania nadal działa - przerywam go i uruchamiam nowy (bez resetowania drzewa)"
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
            self.main_window._create_tile_widget_for_pair
        )
        # NOWY: obsługa batch processing kafelków
        self.data_processing_worker.tiles_batch_ready.connect(
            self.main_window._create_tile_widgets_batch
        )
        # RÓŻNICA: Podłącz do metody BEZ resetowania drzewa (wrapper ignoruje listę)
        self.data_processing_worker.finished.connect(
            lambda processed_pairs: self.main_window._finish_folder_change_without_tree_reset()
        )
        # NAPRAWKA: Podłącz sygnały postępu do pasków postępu
        self.data_processing_worker.progress.connect(self.main_window._show_progress)
        self.data_processing_worker.error.connect(self.main_window._handle_worker_error)
        self.data_processing_thread.started.connect(self.data_processing_worker.run)

        self.data_processing_thread.start()
        self.logger.info(
            f"Uruchomiono nowy worker do przetwarzania {len(file_pairs)} par plików (bez resetowania drzewa)"
        )

    def setup_worker_connections(self, worker: UnifiedBaseWorker):
        """
        Konfiguruje połączenia sygnałów dla workera.

        Args:
            worker: Instancja UnifiedBaseWorker do skonfigurowania
        """
        worker.signals.progress.connect(self.main_window._show_progress)
        worker.signals.error.connect(self.main_window._handle_worker_error) 