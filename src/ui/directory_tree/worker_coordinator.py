"""
Koordynator workerów dla drzewa katalogów.
Zarządza wątkami skanowania i aktualizacji.
"""

import logging
from PyQt6.QtCore import QThreadPool
from .throttled_scheduler import ThrottledWorkerScheduler
from .workers import FolderStatisticsWorker, FolderScanWorker

logger = logging.getLogger(__name__)


class DirectoryTreeWorkerCoordinator:
    """Koordynator workerów drzewa katalogów."""

    def __init__(self, scheduler: ThrottledWorkerScheduler):
        self.scheduler = scheduler
        self.active_workers = set()
        
        # Dedykowany thread pool z kontrolą wątków
        self._folder_thread_pool = QThreadPool()
        self._folder_thread_pool.setMaxThreadCount(3)  # Limit równoczesnych zadań

    def start_directory_scan(self, path: str, callback=None, error_callback=None):
        """Rozpoczyna skanowanie katalogu w tle."""
        if len(self.active_workers) >= 5:  # Limit globalny
            logger.debug(f"Przekroczono limit workerów, pomijam skanowanie: {path}")
            return False

        try:
            worker = FolderScanWorker(path)
            
            if callback:
                worker.custom_signals.finished.connect(callback)
            if error_callback:
                worker.custom_signals.error.connect(error_callback)
            
            # Dodaj obsługę zakończenia
            worker.custom_signals.finished.connect(lambda: self._remove_worker(worker))
            worker.custom_signals.error.connect(lambda: self._remove_worker(worker))
            
            self.active_workers.add(worker)
            self._folder_thread_pool.start(worker)
            
            logger.debug(f"Rozpoczęto skanowanie: {path}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd uruchamiania skanowania {path}: {e}")
            return False

    def start_statistics_calculation(self, folder_path: str, data_manager, 
                                   callback=None, error_callback=None, progress_callback=None):
        """Rozpoczyna obliczanie statystyk dla folderu."""
        if len(self.active_workers) >= 5:  # Limit globalny
            logger.debug(f"Przekroczono limit workerów, pomijam statystyki: {folder_path}")
            return False

        try:
            worker = FolderStatisticsWorker(folder_path)
            
            # Konfiguruj callbacki
            def on_finished(stats):
                # Zapisz do cache przez data_manager
                data_manager.update_directory_stats(folder_path, stats)
                if callback:
                    callback(stats)

            def on_error(error_msg):
                logger.error(f"Błąd obliczania statystyk {folder_path}: {error_msg}")
                if error_callback:
                    error_callback(error_msg)

            # Podłącz sygnały
            worker.signals.finished.connect(on_finished)
            worker.signals.error.connect(on_error)
            if progress_callback:
                worker.signals.progress.connect(progress_callback)
            
            # Dodaj obsługę zakończenia
            worker.signals.finished.connect(lambda: self._remove_worker(worker))
            worker.signals.error.connect(lambda: self._remove_worker(worker))
            
            self.active_workers.add(worker)
            self._folder_thread_pool.start(worker)
            
            logger.debug(f"Rozpoczęto obliczanie statystyk: {folder_path}")
            return True
            
        except Exception as e:
            logger.error(f"Błąd uruchamiania statystyk {folder_path}: {e}")
            return False

    def start_background_stats_calculation(self, visible_folders: list, data_manager):
        """Rozpoczyna obliczanie statystyk w tle dla widocznych folderów."""
        stats_calculated = 0
        
        for folder_path in visible_folders:
            # Sprawdź czy statystyki są już w cache
            cached_stats = data_manager.load_directory_data(folder_path)
            if cached_stats:
                continue  # Pomiń - są już w cache
            
            # Użyj scheduler do throttling
            def create_stats_worker(path=folder_path):
                def worker_factory():
                    return self._create_stats_worker_with_manager(path, data_manager)
                return worker_factory

            task_scheduled = self.scheduler.schedule_task(
                f"stats_{folder_path}", 
                create_stats_worker(folder_path)
            )
            
            if task_scheduled:
                stats_calculated += 1
            
            # Ogranicz liczbę równoczesnych obliczeń
            if stats_calculated >= 10:
                break

        if stats_calculated > 0:
            logger.info(f"📊 Zaplanowano obliczanie statystyk dla {stats_calculated} folderów")

    def _create_stats_worker_with_manager(self, folder_path: str, data_manager):
        """Tworzy worker statystyk z integracją z data_manager."""
        worker = FolderStatisticsWorker(folder_path)
        
        def on_finished(stats):
            # Zapisz do cache i odśwież widok
            data_manager.update_directory_stats(folder_path, stats)
            logger.debug(f"📊 Statystyki obliczone dla: {folder_path}")

        def on_error(error_msg):
            # Logi błędów dla diagnostyki
            logger.debug(f"❌ Błąd statystyk {folder_path}: {error_msg}")

        worker.signals.finished.connect(on_finished)
        worker.signals.error.connect(on_error)
        worker.signals.finished.connect(lambda: self._remove_worker(worker))
        worker.signals.error.connect(lambda: self._remove_worker(worker))
        
        self.active_workers.add(worker)
        return worker

    def handle_worker_finished(self, worker_id: str, result):
        """Obsługuje zakończenie pracy workera."""
        logger.debug(f"Worker zakończony: {worker_id}")
        # Implementacja specyficzna dla różnych typów workerów
        pass

    def cancel_all_workers(self):
        """Anuluje wszystkie aktywne workery."""
        try:
            logger.info(f"Anulowanie {len(self.active_workers)} aktywnych workerów")
            
            # Anuluj scheduler
            if hasattr(self.scheduler, 'cancel_all_tasks'):
                self.scheduler.cancel_all_tasks()
            
            # Wyczyść zestawy
            self.active_workers.clear()
            
            # Wyczyść thread pool
            self._folder_thread_pool.clear()
            
            logger.info("Wszystkie workery anulowane")
            
        except Exception as e:
            logger.error(f"Błąd anulowania workerów: {e}")

    def _remove_worker(self, worker):
        """Usuwa workera z zestawu aktywnych."""
        self.active_workers.discard(worker)

    def get_active_workers_count(self) -> int:
        """Zwraca liczbę aktywnych workerów."""
        return len(self.active_workers)

    def is_busy(self) -> bool:
        """Sprawdza czy koordynator ma aktywne workery."""
        return len(self.active_workers) > 0 