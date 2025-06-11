"""
Moduł zarządzania cache dla skanowania plików.
"""

import logging
import time
from dataclasses import dataclass
from threading import RLock
from typing import Dict, List, Optional, Set, Tuple

from src import app_config
from src.models.file_pair import FilePair
from src.utils.path_utils import normalize_path

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Parametry cache z centralnego pliku konfiguracyjnego
MAX_CACHE_ENTRIES = app_config.SCANNER_MAX_CACHE_ENTRIES
MAX_CACHE_AGE_SECONDS = app_config.SCANNER_MAX_CACHE_AGE_SECONDS


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
    """Wpis w zjednoczonym cache skanowania."""

    timestamp: float
    directory_mtime: float
    file_map: Dict[str, List[str]]
    scan_results: Dict[str, Tuple[List[FilePair], List[str], List[str]]]  # per strategy

    def is_valid(self, current_mtime: float) -> bool:
        """Sprawdza czy wpis cache jest aktualny."""
        current_time = time.time()
        # Sprawdzamy wiek i modyfikację katalogu
        return (
            current_time - self.timestamp <= MAX_CACHE_AGE_SECONDS
            and current_mtime <= self.directory_mtime
        )


class ThreadSafeCache:
    """Thread-safe cache dla wyników skanowania."""

    def __init__(self):
        self._cache: Dict[str, ScanCacheEntry] = {}
        self._lock = RLock()
        self._stats = ScanStatistics()

    def get_cache_entry(self, directory: str) -> Optional[ScanCacheEntry]:
        """Pobiera wpis cache dla katalogu."""
        normalized_dir = normalize_path(directory)
        with self._lock:
            return self._cache.get(normalized_dir)

    def get_scan_result(
        self, directory: str, strategy: str
    ) -> Optional[Tuple[List[FilePair], List[str], List[str]]]:
        """Pobiera wynik skanowania dla konkretnej strategii."""
        entry = self.get_cache_entry(directory)
        if entry:
            from .scanner_core import get_directory_modification_time
            current_mtime = get_directory_modification_time(directory)
            if entry.is_valid(current_mtime) and strategy in entry.scan_results:
                with self._lock:
                    self._stats.cache_hits += 1
                logger.debug(f"CACHE HIT: {directory} strategia={strategy}")
                return entry.scan_results[strategy]

        with self._lock:
            self._stats.cache_misses += 1
        logger.debug(f"CACHE MISS: {directory} strategia={strategy}")
        return None

    def get_file_map(self, directory: str) -> Optional[Dict[str, List[str]]]:
        """Pobiera mapę plików dla katalogu."""
        entry = self.get_cache_entry(directory)
        if entry:
            from .scanner_core import get_directory_modification_time
            current_mtime = get_directory_modification_time(directory)
            if entry.is_valid(current_mtime):
                with self._lock:
                    self._stats.cache_hits += 1
                logger.debug(f"CACHE HIT (file_map): {directory}")
                return entry.file_map

        with self._lock:
            self._stats.cache_misses += 1
        logger.debug(f"CACHE MISS (file_map): {directory}")
        return None

    def store_file_map(self, directory: str, file_map: Dict[str, List[str]]):
        """Zapisuje mapę plików do cache."""
        normalized_dir = normalize_path(directory)
        current_time = time.time()
        from .scanner_core import get_directory_modification_time
        current_mtime = get_directory_modification_time(directory)

        with self._lock:
            if normalized_dir in self._cache:
                # Aktualizuj istniejący wpis
                entry = self._cache[normalized_dir]
                entry.timestamp = current_time
                entry.directory_mtime = current_mtime
                entry.file_map = file_map
            else:
                # Utwórz nowy wpis
                self._cache[normalized_dir] = ScanCacheEntry(
                    timestamp=current_time,
                    directory_mtime=current_mtime,
                    file_map=file_map,
                    scan_results={},
                )

            self._cleanup_old_entries()

    def store_scan_result(
        self,
        directory: str,
        strategy: str,
        result: Tuple[List[FilePair], List[str], List[str]],
    ):
        """Zapisuje wynik skanowania do cache."""
        normalized_dir = normalize_path(directory)

        with self._lock:
            if normalized_dir in self._cache:
                self._cache[normalized_dir].scan_results[strategy] = result
            else:
                # Nie powinno się zdarzyć - file_map powinno być zapisane wcześniej
                logger.warning(
                    f"Próba zapisania scan_result bez file_map dla {directory}"
                )

    def clear(self):
        """Czyści cały cache."""
        with self._lock:
            self._cache.clear()
            self._stats = ScanStatistics()
        logger.info("Wyczyszczono zjednoczony cache skanowania")

    def remove_entry(self, directory: str):
        """Usuwa konkretny wpis z cache."""
        normalized_dir = normalize_path(directory)
        with self._lock:
            if normalized_dir in self._cache:
                del self._cache[normalized_dir]
                logger.debug(f"Usunięto wpis cache: {directory}")

    def _cleanup_old_entries(self):
        """Usuwa stare wpisy z cache (wywołane pod lockiem)."""
        current_time = time.time()
        to_remove = []

        # Usuwanie na podstawie wieku
        for key, entry in self._cache.items():
            if current_time - entry.timestamp > MAX_CACHE_AGE_SECONDS:
                to_remove.append(key)

        for key in to_remove:
            if key in self._cache:  # Dodatkowe sprawdzenie
                del self._cache[key]
                logger.debug(f"Usunięto stary wpis z cache (wiek): {key}")

        # Usuwanie na podstawie liczby
        if len(self._cache) > MAX_CACHE_ENTRIES:
            # Sortuj od najstarszego do najnowszego
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1].timestamp)
            num_to_remove = len(self._cache) - MAX_CACHE_ENTRIES

            for key, _ in sorted_items[:num_to_remove]:
                if key in self._cache:
                    del self._cache[key]
                    logger.debug(f"Usunięto stary wpis z cache (liczba): {key}")

    def get_statistics(self) -> Dict[str, int]:
        """Zwraca statystyki cache."""
        with self._lock:
            return {
                "cache_entries": len(self._cache),
                "cache_hits": self._stats.cache_hits,
                "cache_misses": self._stats.cache_misses,
                "hit_ratio": (
                    self._stats.cache_hits
                    / max(1, self._stats.cache_hits + self._stats.cache_misses)
                )
                * 100,
            }


# Globalna instancja thread-safe cache - UNIFIED CACHE SYSTEM
unified_cache = ThreadSafeCache()


def clear_cache() -> None:
    """
    Czyści bufor wyników skanowania.
    Użyteczne gdy użytkownik chce wymusić ponowne skanowanie.
    """
    unified_cache.clear()
    logger.info("Wyczyszczono ujednolicony cache skanowania")


def get_scan_statistics() -> Dict[str, int]:
    """
    Zwraca statystyki dotyczące bieżącego stanu cache skanowania.

    Returns:
        Słownik zawierający statystyki cache
    """
    return unified_cache.get_statistics()
