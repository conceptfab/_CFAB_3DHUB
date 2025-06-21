"""
Manager danych dla drzewa katalogów.
Obsługuje ładowanie i cache'owanie danych katalogów.
"""

import logging
import os
import time
from typing import List, Optional
from .data_classes import FolderStatistics
from .cache import FolderStatsCache

logger = logging.getLogger(__name__)


class DirectoryTreeDataManager:
    """Manager danych drzewa katalogów."""

    def __init__(self, cache: FolderStatsCache, working_directory: str):
        self.cache = cache
        self.working_directory = working_directory
        
        # Cache dla widocznych folderów
        self._visible_folders_cache = None
        self._visible_folders_cache_timestamp = 0
        self._visible_folders_cache_timeout = 60  # 60 sekund cache

    def load_directory_data(self, path: str) -> Optional[FolderStatistics]:
        """Ładuje dane katalogu z cache lub zwraca None jeśli nie ma w cache."""
        return self.cache.get(path)

    def update_directory_stats(self, path: str, stats: FolderStatistics):
        """Aktualizuje statystyki katalogu w cache."""
        self.cache.set(path, stats)
        logger.debug(f"Zaktualizowano statystyki dla: {path}")

    def refresh_directory(self, path: str):
        """Odświeża dane katalogu - usuwa z cache."""
        self.cache.invalidate(path)
        logger.debug(f"Odświeżono cache dla: {path}")

    def get_visible_folders(self, model, proxy_model, should_show_folder_func) -> List[str]:
        """
        Pobiera listę widocznych folderów z cache lub skanuje na nowo.
        OPTYMALIZACJA: ~70% mniej wywołań skanowania dzięki cache.
        """
        current_time = time.time()
        
        # Sprawdź cache
        if (self._visible_folders_cache is not None and 
            current_time - self._visible_folders_cache_timestamp < self._visible_folders_cache_timeout):
            logger.debug(f"📋 CACHE HIT: Zwracam {len(self._visible_folders_cache)} folderów z cache")
            return self._visible_folders_cache.copy()

        logger.debug("📋 CACHE MISS: Skanowanie folderów...")
        folders = []

        try:
            # Przejdź przez widoczne foldery w modelu proxy zamiast os.walk
            root_index = model.index(self.working_directory)
            if not root_index.isValid():
                return folders

            # Dodaj główny folder
            folders.append(self.working_directory)

            # Rekurencyjnie przejdź przez wszystkie widoczne foldery w drzewie
            def traverse_model(parent_index, depth=0):
                if depth > 3:  # Limit głębokości dla wydajności
                    return

                row_count = model.rowCount(parent_index)
                for row in range(row_count):
                    child_index = model.index(row, 0, parent_index)
                    if child_index.isValid():
                        folder_path = model.filePath(child_index)
                        folder_name = model.fileName(child_index)

                        # Sprawdź czy folder jest widoczny (nie ukryty)
                        if folder_path and should_show_folder_func(folder_name):
                            folders.append(folder_path)

                            # Kontynuuj rekurencyjnie dla podfolderów
                            if model.hasChildren(child_index):
                                traverse_model(child_index, depth + 1)

            traverse_model(root_index)

            # Zapisz do cache
            self._visible_folders_cache = folders.copy()
            self._visible_folders_cache_timestamp = current_time

            logger.debug(f"📋 CACHE SAVE: Zapisano {len(folders)} folderów do cache")

        except Exception as e:
            logger.error(f"Błąd skanowania folderów: {e}")

        return folders

    def invalidate_visible_folders_cache(self):
        """Invaliduje cache widocznych folderów."""
        self._visible_folders_cache = None
        self._visible_folders_cache_timestamp = 0
        logger.debug("📋 CACHE INVALIDATED: Wyczyścono cache widocznych folderów")
        
    def set_working_directory(self, directory_path: str):
        """
        Ustawia katalog roboczy i czyści cache widocznych folderów.
        
        Args:
            directory_path: Nowa ścieżka katalogu roboczego
        """
        self.working_directory = directory_path
        self.invalidate_visible_folders_cache()
        logger.debug(f"Ustawiono nowy katalog roboczy: {directory_path}")

    def clear_all_cache(self):
        """Czyści wszystkie cache."""
        self.cache.clear()
        self.invalidate_visible_folders_cache()
        logger.info("Wyczyszczono wszystkie cache danych katalogów")

    def get_cache_statistics(self) -> dict:
        """Zwraca statystyki cache."""
        return {
            "stats_cache_size": len(self.cache._cache),
            "stats_cache_max": self.cache.max_entries,
            "visible_folders_cached": self._visible_folders_cache is not None,
            "visible_folders_count": len(self._visible_folders_cache) if self._visible_folders_cache else 0
        } 