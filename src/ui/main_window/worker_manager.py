"""
WorkerManager - zarządzanie workerami i wątkami.
🚀 ETAP 1: Refaktoryzacja MainWindow - komponent workerów
"""

import logging
from PyQt6.QtCore import QThread

from src.models.file_pair import FilePair
from src.ui.delegates.workers import (
    DataProcessingWorker,
    UnifiedBaseWorker,
    WorkerFactory,
)


class WorkerManager:
    """
    Zarządzanie workerami i wątkami.
    🚀 ETAP 1: Wydzielony z MainWindow
    """

    def __init__(self, main_window):
        """
        Inicjalizuje WorkerManager.
        
        Args:
            main_window: Referencja do głównego okna
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def start_data_processing_worker(self, file_pairs: list[FilePair]):
        """
        Uruchamia worker przetwarzania danych.
        
        Args:
            file_pairs: Lista par plików do przetworzenia
        """
        try:
            self.logger.info(f"Uruchamianie workera przetwarzania danych dla {len(file_pairs)} par")
            
            # Zatrzymaj poprzedni worker jeśli działa
            self._stop_data_processing_worker()
            
            # Utwórz nowy wątek i worker
            self.main_window.data_processing_thread = QThread()
            self.main_window.data_processing_worker = DataProcessingWorker(
                file_pairs, 
                self.main_window.app_config
            )
            
            # Przenieś worker do wątku
            self.main_window.data_processing_worker.moveToThread(self.main_window.data_processing_thread)
            
            # Połącz sygnały
            self._setup_data_processing_worker_connections()
            
            # Uruchom wątek
            self.main_window.data_processing_thread.start()
            
        except Exception as e:
            self.logger.error(f"Błąd podczas uruchamiania workera przetwarzania danych: {e}")
            if hasattr(self.main_window, 'hide_progress'):
                self.main_window.hide_progress()

    def _setup_data_processing_worker_connections(self):
        """Konfiguruje połączenia sygnałów dla workera przetwarzania danych."""
        try:
            worker = self.main_window.data_processing_worker
            thread = self.main_window.data_processing_thread
            
            # Połączenia wątku
            thread.started.connect(worker.run)
            worker.finished.connect(thread.quit)
            worker.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            
            # Połączenia postępu
            worker.progress.connect(self._handle_worker_progress)
            worker.status_update.connect(self._handle_worker_status)
            
            # Połączenia wyników
            worker.tile_created.connect(self._handle_tile_created)
            worker.batch_completed.connect(self._handle_batch_completed)
            worker.all_tiles_loaded.connect(self._handle_all_tiles_loaded)
            
            # Połączenia błędów
            worker.error.connect(self._handle_worker_error)
            
            # Czyszczenie po zakończeniu
            thread.finished.connect(self._cleanup_data_processing_worker)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas konfiguracji połączeń workera: {e}")

    def _stop_data_processing_worker(self):
        """Zatrzymuje aktualny worker przetwarzania danych."""
        try:
            if (
                hasattr(self.main_window, 'data_processing_thread') 
                and self.main_window.data_processing_thread 
                and self.main_window.data_processing_thread.isRunning()
            ):
                self.logger.debug("Zatrzymywanie poprzedniego workera przetwarzania danych...")
                
                if hasattr(self.main_window, 'data_processing_worker') and self.main_window.data_processing_worker:
                    self.main_window.data_processing_worker.stop()
                
                self.main_window.data_processing_thread.quit()
                if not self.main_window.data_processing_thread.wait(3000):
                    self.logger.warning("Wymuszenie zakończenia wątku przetwarzania danych")
                    self.main_window.data_processing_thread.terminate()
                    self.main_window.data_processing_thread.wait(1000)
                    
        except Exception as e:
            self.logger.error(f"Błąd podczas zatrzymywania workera przetwarzania danych: {e}")

    def _cleanup_data_processing_worker(self):
        """Czyści referencje do workera przetwarzania danych."""
        try:
            self.main_window.data_processing_thread = None
            self.main_window.data_processing_worker = None
            self.logger.debug("Worker przetwarzania danych został wyczyszczony")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas czyszczenia workera przetwarzania danych: {e}")

    def setup_worker_connections(self, worker: UnifiedBaseWorker):
        """
        Konfiguruje standardowe połączenia dla workera.
        
        Args:
            worker: Worker do skonfigurowania
        """
        try:
            # Podstawowe sygnały
            worker.progress.connect(self._handle_worker_progress)
            worker.status_update.connect(self._handle_worker_status)
            worker.error.connect(self._handle_worker_error)
            worker.finished.connect(self._handle_worker_finished)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas konfiguracji połączeń workera: {e}")

    def create_worker(self, worker_type: str, *args, **kwargs):
        """
        Tworzy workera określonego typu.
        
        Args:
            worker_type: Typ workera do utworzenia
            *args: Argumenty pozycyjne
            **kwargs: Argumenty nazwane
            
        Returns:
            Utworzony worker
        """
        try:
            worker = WorkerFactory.create_worker(worker_type, *args, **kwargs)
            self.setup_worker_connections(worker)
            return worker
            
        except Exception as e:
            self.logger.error(f"Błąd podczas tworzenia workera {worker_type}: {e}")
            return None

    def run_worker_in_thread_pool(self, worker):
        """
        Uruchamia workera w thread pool.
        
        Args:
            worker: Worker do uruchomienia
        """
        try:
            if hasattr(self.main_window, 'thread_pool'):
                self.main_window.thread_pool.start(worker)
            else:
                self.logger.error("Thread pool nie jest dostępny")
                
        except Exception as e:
            self.logger.error(f"Błąd podczas uruchamiania workera w thread pool: {e}")

    # Metody obsługi sygnałów workerów
    def _handle_worker_progress(self, percent: int):
        """Obsługuje sygnał postępu workera."""
        try:
            if hasattr(self.main_window, 'progress_manager'):
                self.main_window.progress_manager.update_progress(percent)
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi postępu workera: {e}")

    def _handle_worker_status(self, message: str):
        """Obsługuje sygnał statusu workera."""
        try:
            if hasattr(self.main_window, 'progress_manager'):
                self.main_window.progress_manager.update_status(message)
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi statusu workera: {e}")

    def _handle_worker_error(self, error_message: str):
        """Obsługuje sygnał błędu workera."""
        try:
            if hasattr(self.main_window, 'event_handler'):
                self.main_window.event_handler.handle_worker_error(error_message)
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi błędu workera: {e}")

    def _handle_worker_finished(self):
        """Obsługuje sygnał zakończenia workera."""
        try:
            if hasattr(self.main_window, 'hide_progress'):
                self.main_window.hide_progress()
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi zakończenia workera: {e}")

    def _handle_tile_created(self, tile_widget):
        """Obsługuje sygnał utworzenia kafelka."""
        try:
            # Delegowanie do głównego okna
            if hasattr(self.main_window, '_handle_tile_created'):
                self.main_window._handle_tile_created(tile_widget)
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi utworzenia kafelka: {e}")

    def _handle_batch_completed(self, batch_info):
        """Obsługuje sygnał zakończenia batch'a."""
        try:
            # Delegowanie do głównego okna
            if hasattr(self.main_window, '_handle_batch_completed'):
                self.main_window._handle_batch_completed(batch_info)
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi zakończenia batch'a: {e}")

    def _handle_all_tiles_loaded(self):
        """Obsługuje sygnał zakończenia ładowania wszystkich kafelków."""
        try:
            # Delegowanie do głównego okna
            if hasattr(self.main_window, '_on_tile_loading_finished'):
                self.main_window._on_tile_loading_finished()
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi zakończenia ładowania kafelków: {e}")

    def get_active_workers_count(self) -> int:
        """
        Zwraca liczbę aktywnych workerów.
        
        Returns:
            Liczba aktywnych workerów
        """
        try:
            count = 0
            
            # Sprawdź worker przetwarzania danych
            if (
                hasattr(self.main_window, 'data_processing_thread') 
                and self.main_window.data_processing_thread 
                and self.main_window.data_processing_thread.isRunning()
            ):
                count += 1
            
            # Sprawdź worker skanowania
            if (
                hasattr(self.main_window, 'scan_thread') 
                and self.main_window.scan_thread 
                and self.main_window.scan_thread.isRunning()
            ):
                count += 1
            
            # Sprawdź thread pool
            if hasattr(self.main_window, 'thread_pool'):
                count += self.main_window.thread_pool.activeThreadCount()
            
            return count
            
        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania liczby aktywnych workerów: {e}")
            return 0

    def stop_all_workers(self):
        """Zatrzymuje wszystkich workerów."""
        try:
            self.logger.info("Zatrzymywanie wszystkich workerów...")
            
            # Zatrzymaj worker przetwarzania danych
            self._stop_data_processing_worker()
            
            # Zatrzymaj worker skanowania
            if hasattr(self.main_window, '_stop_current_scanning'):
                self.main_window._stop_current_scanning()
            
            # Poczekaj na zakończenie thread pool
            if hasattr(self.main_window, 'thread_pool'):
                self.main_window.thread_pool.waitForDone(3000)
            
            self.logger.info("Wszystkie workery zostały zatrzymane")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zatrzymywania workerów: {e}") 