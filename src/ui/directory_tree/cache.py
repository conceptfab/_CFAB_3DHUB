import time
from typing import Optional
from .data_classes import FolderStatistics

class FolderStatsCache:
    """Zarządzanie cache statystyk folderów z automatycznym czyszczeniem."""

    def __init__(self, max_entries: int = 100, timeout_seconds: int = 300):
        self._cache = {}
        self._access_times = {}
        self._max_entries = max_entries
        self._timeout = timeout_seconds

    def get(self, folder_path: str) -> Optional[FolderStatistics]:
        """Pobiera statystyki z cache z sprawdzeniem ważności."""
        if folder_path not in self._cache:
            return None

        # Sprawdź czy nie wygasł
        if time.time() - self._access_times[folder_path] > self._timeout:
            self.invalidate(folder_path)
            return None

        self._access_times[folder_path] = time.time()
        return self._cache[folder_path]

    def set(self, folder_path: str, stats: FolderStatistics):
        """Zapisuje statystyki do cache z automatycznym czyszczeniem."""
        # Wyczyść stare wpisy jeśli przekroczono limit
        if len(self._cache) >= self._max_entries:
            self._cleanup_old_entries()

        self._cache[folder_path] = stats
        self._access_times[folder_path] = time.time()

    def invalidate(self, folder_path: str):
        """Usuwa wpis z cache."""
        if folder_path in self._cache:
            del self._cache[folder_path]
            del self._access_times[folder_path]

    def _cleanup_old_entries(self):
        """Usuwa najstarsze wpisy z cache."""
        if not self._access_times:
            return

        # Sortuj według czasu dostępu i usuń najstarsze
        sorted_items = sorted(self._access_times.items(), key=lambda x: x[1])
        to_remove = len(sorted_items) // 4  # Usuń 25% najstarszych

        for folder_path, _ in sorted_items[:to_remove]:
            self.invalidate(folder_path) 