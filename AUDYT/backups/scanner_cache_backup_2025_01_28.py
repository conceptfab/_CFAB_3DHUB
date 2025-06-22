"""
Moduł zarządzający cache'em dla skanera plików.

Ten moduł zawiera implementację thread-safe cache dla wyników skanowania
folderów i parowania plików.
"""

import logging
import os
import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Dict, Generic, List, Optional, Tuple, TypeVar

from src import app_config
from src.models.file_pair import FilePair
from src.models.special_folder import SpecialFolder
from src.utils.path_utils import normalize_path

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Parametry cache z centralnego pliku konfiguracyjnego
MAX_CACHE_ENTRIES = app_config.SCANNER_MAX_CACHE_ENTRIES
MAX_CACHE_AGE_SECONDS = app_config.SCANNER_MAX_CACHE_AGE_SECONDS

K = TypeVar("K")
V = TypeVar("V")


@dataclass
class ScanStatistics:
    """Statystyki skanowania folderów."""

    total_folders_scanned: int = 0
    total_files_found: int = 0
    scan_duration: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass
class ScanCacheEntry:
    """Wpis w cache skanowania."""

    timestamp: float
    directory_mtime: float
    file_map: Dict[str, List[str]]
    scan_results: Dict[
        str, Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]]
    ]  # per strategy

    def is_valid(self, current_mtime: float) -> bool:
        """Sprawdza czy wpis cache jest aktualny."""
        current_time = time.time()
        # Sprawdzamy wiek i modyfikację katalogu
        return (
            current_time - self.timestamp <= MAX_CACHE_AGE_SECONDS
            and current_mtime <= self.directory_mtime
        )


def get_directory_modification_time(directory: str) -> float:
    """
    Pobiera maksymalny czas modyfikacji dla katalogu i jego zawartości.

    Args:
        directory: Ścieżka do katalogu

    Returns:
        Znacznik czasu ostatniej modyfikacji (timestamp)
    """
    normalized_dir = normalize_path(directory)
    if not os.path.exists(normalized_dir):
        return 0

    try:
        max_mtime = os.path.getmtime(normalized_dir)
    except (PermissionError, OSError) as e:
        logger.warning(
            f"Nie można uzyskać czasu modyfikacji dla katalogu {directory}: {e}"
        )
        return 0

    # Sprawdzamy wszystkie pliki i podfoldery w katalogu (tylko 1 poziom w głąb)
    try:
        with os.scandir(normalized_dir) as entries:
            for entry in entries:
                try:
                    current_mtime = entry.stat().st_mtime
                    if current_mtime > max_mtime:
                        max_mtime = current_mtime
                except (PermissionError, OSError) as e:
                    logger.warning(
                        f"Nie można uzyskać czasu modyfikacji dla {entry.path}: {e}"
                    )
    except (PermissionError, OSError) as e:
        logger.warning(f"Nie można odczytać zawartości katalogu {directory}: {e}")

    return max_mtime


class Cache(Generic[K, V]):
    """Prosty cache LRU (Least Recently Used) z limitem czasowym."""

    def __init__(self, max_entries: int):
        self.max_entries = max_entries
        self.cache: OrderedDict[K, Tuple[float, V]] = OrderedDict()
        self.lock = RLock()
        # DODANE: liczniki wydajności
        self.cache_hits = 0
        self.cache_misses = 0
        self.total_requests = 0

    def get(self, key: K) -> Optional[V]:
        """Pobiera wartość z cache, aktualizując jej pozycję."""
        with self.lock:
            self.total_requests += 1
            
            if key not in self.cache:
                self.cache_misses += 1
                return None

            timestamp, value = self.cache[key]
            if time.time() - timestamp > MAX_CACHE_AGE_SECONDS:
                # Wpis przeterminowany, usuń go
                del self.cache[key]
                self.cache_misses += 1
                return None

            # Przesuń na koniec, aby oznaczyć jako ostatnio używany
            self.cache.move_to_end(key)
            self.cache_hits += 1
            return value

    def set(self, key: K, value: V):
        """Ustawia wartość w cache, usuwając najstarszy wpis, jeśli to konieczne."""
        with self.lock:
            self.cache[key] = (time.time(), value)
            # Przesuń na koniec, aby oznaczyć jako ostatnio używany
            self.cache.move_to_end(key)
            # Jeśli cache jest za duży, usuń najstarszy wpis
            if len(self.cache) > self.max_entries:
                self.cache.popitem(last=False)

    def clear(self):
        """Czyści cały cache."""
        with self.lock:
            self.cache.clear()


class ThreadSafeCache:
    """Singleton, thread-safe cache."""

    _instance = None
    _lock = RLock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                # Podwójne sprawdzenie, aby uniknąć wyścigu
                if cls._instance is None:
                    cls._instance = super(ThreadSafeCache, cls).__new__(cls)
                    # Inicjalizacja cache'y
                    cls._instance.file_map_cache = Cache(max_entries=MAX_CACHE_ENTRIES)
                    cls._instance.scan_result_cache = Cache(
                        max_entries=MAX_CACHE_ENTRIES
                    )
        return cls._instance

    def _get_cache_key(self, directory: str, strategy: Optional[str] = None) -> str:
        """Tworzy klucz do cache, opcjonalnie uwzględniając strategię."""
        key = normalize_path(directory)
        if strategy:
            key = f"{key}::{strategy}"
        return key

    def get_file_map(self, directory: str) -> Optional[Dict[str, List[str]]]:
        """Pobiera zmapowane pliki z cache."""
        key = self._get_cache_key(directory)
        return self.file_map_cache.get(key)

    def set_file_map(self, directory: str, file_map: Dict[str, List[str]]):
        """Zapisuje zmapowane pliki w cache."""
        key = self._get_cache_key(directory)
        self.file_map_cache.set(key, file_map)

    def get_scan_result(
        self, directory: str, strategy: str
    ) -> Optional[Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]]]:
        """Pobiera pełny wynik skanowania z cache."""
        key = self._get_cache_key(directory, strategy)
        return self.scan_result_cache.get(key)

    def set_scan_result(
        self,
        directory: str,
        strategy: str,
        result: Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]],
    ):
        """Zapisuje pełny wynik skanowania w cache."""
        key = self._get_cache_key(directory, strategy)
        self.scan_result_cache.set(key, result)

    def clear(self):
        """Czyści cały cache."""
        with self._lock:
            self.file_map_cache.clear()
            self.scan_result_cache.clear()
        logger.info("Wyczyszczono cache skanowania")

    def remove_entry(self, directory: str):
        """Usuwa konkretny wpis z cache."""
        normalized_dir = normalize_path(directory)
        with self._lock:
            if normalized_dir in self.file_map_cache.cache:
                del self.file_map_cache.cache[normalized_dir]
                logger.debug(f"Usunięto wpis cache: {directory}")
            if normalized_dir in self.scan_result_cache.cache:
                del self.scan_result_cache.cache[normalized_dir]
                logger.debug(f"Usunięto wpis cache: {directory}")

    def _cleanup_old_entries(self):
        """Usuwa stare wpisy z cache (wywołane pod lockiem) - optymalizacja single pass."""
        current_time = time.time()
        
        # Pojedyncze przejście dla file_map_cache
        self._cleanup_cache_by_age_and_size(
            self.file_map_cache, current_time, "file_map"
        )
        
        # Pojedyncze przejście dla scan_result_cache
        self._cleanup_cache_by_age_and_size(
            self.scan_result_cache, current_time, "scan_result"
        )

    def _cleanup_cache_by_age_and_size(self, cache_obj, current_time, cache_name):
        """Optymalizowane cleanup w jednym przejściu."""
        to_remove = []
        
        # Zbierz wszystkie klucze do usunięcia (wiek + nadmiar)
        for key, (timestamp, _) in cache_obj.cache.items():
            if current_time - timestamp > MAX_CACHE_AGE_SECONDS:
                to_remove.append((key, timestamp, "age"))
        
        # Jeśli nadal za dużo wpisów, dodaj najstarsze
        if len(cache_obj.cache) - len(to_remove) > MAX_CACHE_ENTRIES:
            # Zbierz pozostałe wpisy, posortuj według wieku
            remaining_items = [
                (key, timestamp) for key, (timestamp, _) in cache_obj.cache.items()
                if key not in [item[0] for item in to_remove]
            ]
            remaining_items.sort(key=lambda x: x[1])  # Sortuj według timestamp
            
            # Dodaj najstarsze do usunięcia
            num_to_remove = len(cache_obj.cache) - len(to_remove) - MAX_CACHE_ENTRIES
            for key, timestamp in remaining_items[:num_to_remove]:
                to_remove.append((key, timestamp, "size"))
        
        # Usuń wszystkie wpisy jednocześnie
        for key, _, reason in to_remove:
            if key in cache_obj.cache:
                del cache_obj.cache[key]
                logger.debug(f"Usunięto wpis z {cache_name} cache ({reason}): {key}")

    def get_statistics(self) -> Dict[str, float]:
        """Zwraca statystyki cache z rozszerzonym monitoringiem."""
        with self._lock:
            hit_ratio = 0
            total_requests = self.file_map_cache.cache_hits + self.file_map_cache.cache_misses
            
            if total_requests > 0:
                hit_ratio = (self.file_map_cache.cache_hits / total_requests) * 100

            stats = {
                "cache_entries": len(self.file_map_cache.cache),
                "cache_hits": self.file_map_cache.cache_hits,
                "cache_misses": self.file_map_cache.cache_misses,
                "total_requests": total_requests,
                "hit_ratio": hit_ratio,
                "scan_result_entries": len(self.scan_result_cache.cache),
            }
            
            # Automatyczny monitoring wydajności (jeśli dostępny)
            try:
                from .cache_monitor import monitor_cache_performance
                monitor_cache_performance(self)
            except ImportError:
                pass  # Monitor nie jest wymagany
            
            return stats


# Globalna instancja cache
cache = ThreadSafeCache()


def clear_cache() -> None:
    """
    Czyści bufor wyników skanowania.
    Użyteczne gdy użytkownik chce wymusić ponowne skanowanie.
    """
    cache.clear()
    logger.info("Wyczyszczono bufor wyników skanowania")
