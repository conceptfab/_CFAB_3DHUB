"""
Manager statystyk folderów - zarządzanie cache'em i obliczaniem statystyk.
Wydzielony z DirectoryTreeManager w ramach refaktoryzacji architektury.
"""

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable, Optional
from threading import RLock

from PyQt6.QtCore import QObject, QThreadPool, pyqtSignal

from src.logic.scanner import scan_folder_for_pairs
from src.logic.scanner_core import should_ignore_folder
from src.ui.delegates.workers import UnifiedBaseWorker, UnifiedWorkerSignals
from src.utils.path_utils import normalize_path
from src.app_config import AppConfig

logger = logging.getLogger(__name__)

# Pobierz konfigurację cache
app_config = AppConfig()


@dataclass
class FolderStatistics:
    """Statystyki folderu - rozmiar i liczba par plików."""

    size_gb: float = 0.0
    pairs_count: int = 0
    subfolders_size_gb: float = 0.0
    subfolders_pairs: int = 0
    total_files: int = 0

    @property
    def total_size_gb(self) -> float:
        return self.size_gb + self.subfolders_size_gb

    @property
    def total_pairs(self) -> int:
        return self.pairs_count + self.subfolders_pairs


class FolderStatisticsSignals(UnifiedWorkerSignals):
    """Sygnały dla workera statystyk folderów - rozszerza BaseWorkerSignals."""
    
    statistics_calculated = pyqtSignal(object)  # FolderStatistics


class FolderStatisticsWorker(UnifiedBaseWorker):
    """Worker do obliczania statystyk folderu w tle - zunifikowany z delegates/workers.py."""

    def __init__(self, folder_path: str):
        super().__init__()
        self.folder_path = normalize_path(folder_path)
        self.custom_signals = FolderStatisticsSignals()

    def _validate_inputs(self):
        """Walidacja parametrów wejściowych."""
        import os
        if not self.folder_path or not os.path.exists(self.folder_path):
            raise ValueError(f"Folder '{self.folder_path}' nie istnieje")

    def run(self):
        """Oblicza statystyki folderu."""
        import os
        try:
            self._validate_inputs()
            stats = FolderStatistics()
            self.emit_progress(0, "Rozpoczynanie obliczania statystyk...")

            if self.check_interruption():
                return

            # Oblicz rozmiar foldera
            self.emit_progress(25, "Obliczanie rozmiaru folderu...")
            total_size = 0
            file_count = 0

            for root, dirs, files in os.walk(self.folder_path):
                if self.check_interruption():
                    return

                # Filtruj ignorowane foldery z listy dirs (modyfikacja in-place)
                dirs[:] = [d for d in dirs if not should_ignore_folder(d)]

                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        total_size += os.path.getsize(file_path)
                        file_count += 1
                    except (OSError, FileNotFoundError):
                        continue

            stats.size_gb = total_size / (1024**3)
            stats.total_files = file_count

            # Oblicz liczbę par plików
            self.emit_progress(75, "Obliczanie liczby par plików...")
            if self.check_interruption():
                return

            try:
                found_pairs, _, _ = scan_folder_for_pairs(
                    self.folder_path, max_depth=0, pair_strategy="first_match"
                )
                stats.pairs_count = len(found_pairs)
            except Exception as e:
                logger.warning(f"Błąd obliczania par plików: {e}")
                stats.pairs_count = 0

            self.emit_progress(100, "Zakończono obliczanie statystyk")
            self.custom_signals.statistics_calculated.emit(stats)
            self.emit_finished(stats)

        except Exception as e:
            error_msg = f"Błąd obliczania statystyk dla {self.folder_path}: {e}"
            logger.error(error_msg)
            self.custom_signals.error.emit(error_msg)
            self.emit_error(error_msg)


class LRUCache:
    """Cache LRU z limitami pamięci i automatycznym czyszczeniem."""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()
        self.timestamps = {}
        self._lock = RLock()
        
    def get(self, key: str) -> Optional[tuple]:
        """Pobiera element z cache z sprawdzeniem TTL."""
        with self._lock:
            current_time = time.time()
            
            if key in self.cache:
                # Sprawdź TTL
                if current_time - self.timestamps[key] < self.ttl_seconds:
                    # Przenieś na koniec (najbardziej używany)
                    self.cache.move_to_end(key)
                    return self.cache[key]
                else:
                    # TTL wygasł - usuń
                    del self.cache[key]
                    del self.timestamps[key]
            
            return None
    
    def put(self, key: str, value: any):
        """Wstawia element do cache z zarządzaniem rozmiarem."""
        with self._lock:
            current_time = time.time()
            
            if key in self.cache:
                # Zaktualizuj istniejący
                self.cache[key] = value
                self.timestamps[key] = current_time
                self.cache.move_to_end(key)
            else:
                # Dodaj nowy
                if len(self.cache) >= self.max_size:
                    # Usuń najstarszy element
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                    del self.timestamps[oldest_key]
                
                self.cache[key] = value
                self.timestamps[key] = current_time
    
    def invalidate(self, key: str):
        """Usuwa element z cache."""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
    
    def clear(self):
        """Czyści cały cache."""
        with self._lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def size(self) -> int:
        """Zwraca aktualny rozmiar cache."""
        with self._lock:
            return len(self.cache)


class FolderStatisticsManager:
    """Manager statystyk folderów z zaawansowanym cache'em."""
    
    def __init__(self):
        self.cache = LRUCache(
            max_size=app_config.get('cache_max_entries', 100),
            ttl_seconds=app_config.get('cache_ttl_seconds', 300)
        )
        self._active_workers = {}  # Słownik aktywnych workerów
        
    def get_cached_statistics(self, folder_path: str) -> Optional[FolderStatistics]:
        """Pobiera statystyki z cache."""
        cache_key = normalize_path(folder_path)
        cached_data = self.cache.get(cache_key)
        
        if cached_data:
            logger.debug(f"Cache HIT dla statystyk: {folder_path}")
            return cached_data
        
        logger.debug(f"Cache MISS dla statystyk: {folder_path}")
        return None
    
    def cache_statistics(self, folder_path: str, stats: FolderStatistics):
        """Zapisuje statystyki do cache."""
        cache_key = normalize_path(folder_path)
        self.cache.put(cache_key, stats)
        logger.debug(f"Zapisano do cache statystyki dla: {folder_path}")
    
    def calculate_statistics_async(self, folder_path: str, callback: Optional[Callable] = None):
        """Oblicza statystyki folderu asynchronicznie z cache."""
        cache_key = normalize_path(folder_path)
        
        # Sprawdź cache
        cached_stats = self.get_cached_statistics(folder_path)
        if cached_stats and callback:
            callback(cached_stats)
            return
        
        # Sprawdź czy worker już działa dla tego folderu
        if cache_key in self._active_workers:
            logger.debug(f"Worker już działa dla: {folder_path}")
            return
        
        # Utwórz worker
        worker = FolderStatisticsWorker(folder_path)
        self._active_workers[cache_key] = worker

        def on_finished(stats):
            # Zapisz do cache
            self.cache_statistics(folder_path, stats)
            # Usuń z aktywnych workerów
            if cache_key in self._active_workers:
                del self._active_workers[cache_key]
            if callback:
                callback(stats)

        def on_error(error_msg):
            logger.error(f"Błąd obliczania statystyk: {error_msg}")
            # Usuń z aktywnych workerów
            if cache_key in self._active_workers:
                del self._active_workers[cache_key]
            if callback:
                # Zwróć puste statystyki w przypadku błędu
                callback(FolderStatistics())

        worker.custom_signals.statistics_calculated.connect(on_finished)
        worker.custom_signals.error.connect(on_error)

        QThreadPool.globalInstance().start(worker)
    
    def invalidate_cache(self, folder_path: str):
        """Usuwa statystyki z cache."""
        cache_key = normalize_path(folder_path)
        self.cache.invalidate(cache_key)
        logger.debug(f"Usunięto z cache statystyki dla: {folder_path}")
    
    def clear_cache(self):
        """Czyści cały cache statystyk."""
        self.cache.clear()
        logger.debug("Wyczyszczono cache statystyk")
    
    def get_cache_info(self) -> dict:
        """Zwraca informacje o cache."""
        return {
            'size': self.cache.size(),
            'max_size': self.cache.max_size,
            'ttl_seconds': self.cache.ttl_seconds,
            'active_workers': len(self._active_workers)
        } 