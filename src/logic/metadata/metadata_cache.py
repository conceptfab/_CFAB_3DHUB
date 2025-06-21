"""
Komponent cache metadanych CFAB_3DHUB.
🚀 ETAP 3: Refaktoryzacja MetadataManager - cache z TTL
"""

import logging
import time
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MetadataCache:
    """
    Cache metadanych z TTL (Time To Live) i thread-safe access.
    Przechowuje metadane w pamięci z automatycznym wygasaniem.
    """

    def __init__(self, cache_timeout: float = 30.0):
        """
        Inicjalizuje cache metadanych.

        Args:
            cache_timeout: Czas życia cache w sekundach (domyślnie 30s)
        """
        self._cache = {}
        self._cache_timeout = cache_timeout
        self._cache_timestamp = 0
        self._cache_lock = threading.RLock()

    def get(self, key: str = "default") -> Optional[Dict[str, Any]]:
        """
        Pobiera metadane z cache jeśli są aktualne.

        Args:
            key: Klucz cache (domyślnie "default")

        Returns:
            Dict z metadanymi lub None jeśli cache wygasł lub jest pusty
        """
        with self._cache_lock:
            current_time = time.time()
            
            # Sprawdź czy cache nie wygasł
            if (
                self._cache
                and key in self._cache
                and current_time - self._cache_timestamp < self._cache_timeout
            ):
                logger.debug(f"Cache hit dla klucza '{key}'")
                return self._cache[key].copy()
            
            logger.debug(f"Cache miss dla klucza '{key}' (wygasł lub pusty)")
            return None

    def set(self, metadata: Dict[str, Any], key: str = "default") -> None:
        """
        Zapisuje metadane do cache.

        Args:
            metadata: Słownik metadanych do zapisania
            key: Klucz cache (domyślnie "default")
        """
        with self._cache_lock:
            self._cache[key] = metadata.copy()
            self._cache_timestamp = time.time()
            logger.debug(f"Cache updated dla klucza '{key}'")

    def invalidate(self, key: Optional[str] = None) -> None:
        """
        Invaliduje cache.

        Args:
            key: Klucz do invalidacji (None = cały cache)
        """
        with self._cache_lock:
            if key is None:
                # Invaliduj cały cache
                self._cache.clear()
                self._cache_timestamp = 0
                logger.debug("Cały cache został invalidowany")
            elif key in self._cache:
                # Invaliduj konkretny klucz
                del self._cache[key]
                logger.debug(f"Cache invalidowany dla klucza '{key}'")

    def is_valid(self, key: str = "default") -> bool:
        """
        Sprawdza czy cache jest aktualny.

        Args:
            key: Klucz cache do sprawdzenia

        Returns:
            bool: True jeśli cache jest aktualny
        """
        with self._cache_lock:
            current_time = time.time()
            return (
                key in self._cache
                and current_time - self._cache_timestamp < self._cache_timeout
            )

    def get_cache_age(self) -> float:
        """
        Zwraca wiek cache w sekundach.

        Returns:
            float: Wiek cache w sekundach
        """
        with self._cache_lock:
            if self._cache_timestamp == 0:
                return float('inf')  # Cache nigdy nie był ustawiony
            return time.time() - self._cache_timestamp

    def get_cache_info(self) -> Dict[str, Any]:
        """
        Zwraca informacje o stanie cache.

        Returns:
            Dict z informacjami o cache
        """
        with self._cache_lock:
            return {
                "keys": list(self._cache.keys()),
                "cache_timeout": self._cache_timeout,
                "cache_age": self.get_cache_age(),
                "is_valid": self.is_valid(),
                "size": len(self._cache)
            } 