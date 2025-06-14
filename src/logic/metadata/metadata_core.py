"""
Główny komponent MetadataManager CFAB_3DHUB.
🚀 ETAP 3: Refaktoryzacja MetadataManager - klasa główna
"""

import logging

# Import threading dla worker thread compatibility
import threading
import time
from typing import Any, Dict, List, Optional

# Import normalizacji ścieżek
from src.utils.path_utils import normalize_path

# Import komponentów
from .metadata_cache import MetadataCache
from .metadata_io import MetadataIO
from .metadata_operations import MetadataOperations
from .metadata_validator import MetadataValidator

logger = logging.getLogger(__name__)


class MetadataManager:
    """
    Unified metadata manager - single source of truth.
    Thread-safe metadata management with caching and proper error handling.

    Używa komponentów:
    - MetadataCache: cache z TTL
    - MetadataIO: operacje I/O z atomic write
    - MetadataOperations: operacje biznesowe
    - MetadataValidator: walidacja struktury

    NAPRAWKA CRASH: Dziedziczy po QObject dla thread-safe Qt timers
    """

    _instances = {}  # Singleton pattern per working directory
    _instances_lock = threading.RLock()

    def __init__(self, working_directory: str):
        """
        Inicjalizuje menedżer metadanych.

        Args:
            working_directory (str): Ścieżka do folderu roboczego
        """
        # Nie dziedziczymy po QObject - używamy threading.Timer dla worker thread compatibility
        self.working_directory = normalize_path(working_directory)

        # Inicjalizacja komponentów
        self.cache = MetadataCache(cache_timeout=30.0)
        self.io = MetadataIO(working_directory)
        self.operations = MetadataOperations(working_directory)
        self.validator = MetadataValidator()

        # Thread-safe buffer dla zmian
        self._changes_buffer = {}
        self._buffer_lock = threading.RLock()
        self._last_save_time = 0
        self._save_delay = 2000  # Opóźnienie zapisu w milisekundach (2s)

        self._save_timer = None

    @classmethod
    def get_instance(cls, working_directory: str) -> "MetadataManager":
        """
        Singleton pattern per working directory.

        Args:
            working_directory: Path to working directory

        Returns:
            MetadataManager instance for this directory
        """
        norm_dir = normalize_path(working_directory)

        with cls._instances_lock:
            if norm_dir not in cls._instances:
                cls._instances[norm_dir] = cls(working_directory)
            return cls._instances[norm_dir]

    def get_metadata_path(self) -> str:
        """Zwraca ścieżkę do pliku metadanych."""
        return self.io.get_metadata_path()

    def get_lock_path(self) -> str:
        """Zwraca ścieżkę do pliku blokady."""
        return self.io.get_lock_path()

    def load_metadata(self) -> Dict[str, Any]:
        """
        Wczytuje metadane z pliku z obsługą cache.

        Returns:
            Dict zawierający metadane
        """
        # Sprawdź cache
        cached_metadata = self.cache.get()
        if cached_metadata is not None:
            return cached_metadata

        # Wczytaj z pliku
        metadata = self.io.load_metadata_from_file()

        # Zaktualizuj cache
        self.cache.set(metadata)

        return metadata

    def _invalidate_cache(self):
        """Invaliduje cache metadanych."""
        self.cache.invalidate()

    def _should_save(self) -> bool:
        """Sprawdza czy należy zapisać zmiany."""
        current_time = time.time()
        return (current_time - self._last_save_time) >= (
            self._save_delay / 1000.0
        )  # Konwersja ms na s

    def _flush_changes(self):
        """Thread-safe flush of buffered changes."""
        with self._buffer_lock:
            if not self._changes_buffer:
                logger.debug("_flush_changes: Bufor pusty - nie ma nic do zapisu")
                return

            try:
                # Atomic write with proper error handling
                success = self.io.atomic_write(self._changes_buffer)

                if success:
                    self._changes_buffer.clear()
                    self._last_save_time = time.time()
                    self._invalidate_cache()  # Invalidate cache after write
                    logger.debug("Successfully flushed metadata changes")

            except Exception as e:
                logger.error(f"Failed to flush metadata changes: {e}", exc_info=True)
                # Could add retry logic here

    def save_metadata(
        self,
        file_pairs_list: List,
        unpaired_archives: List[str],
        unpaired_previews: List[str],
    ) -> bool:
        """Thread-safe metadata saving with buffering."""
        with self._buffer_lock:
            try:
                # Przygotuj metadane do zapisu używając operations
                file_pairs_metadata = self.operations.prepare_file_pairs_metadata(
                    file_pairs_list
                )

                unpaired_archives_rel, unpaired_previews_rel = (
                    self.operations.prepare_unpaired_files_metadata(
                        unpaired_archives, unpaired_previews
                    )
                )

                # Dodaj zmiany do bufora
                self._changes_buffer.update(
                    {
                        "file_pairs": file_pairs_metadata,
                        "unpaired_archives": unpaired_archives_rel,
                        "unpaired_previews": unpaired_previews_rel,
                        "timestamp": time.time(),
                    }
                )

                # NAPRAWKA THREAD SAFETY: Anuluj poprzedni timer jeśli jest aktywny
                if self._save_timer:
                    self._save_timer.cancel()

                # Zaplanuj zapis z opóźnieniem używając threading.Timer
                self._save_timer = threading.Timer(
                    self._save_delay / 1000.0,  # Konwersja ms na sekundy
                    self._flush_changes,
                )
                self._save_timer.start()

                return True

            except Exception as e:
                logger.error(f"Error buffering metadata: {e}", exc_info=True)
                return False

    def apply_metadata_to_file_pairs(self, file_pairs_list: List) -> bool:
        """Aplikuje metadane do listy par plików."""
        metadata = self.load_metadata()
        return self.operations.apply_metadata_to_file_pairs(metadata, file_pairs_list)

    def remove_metadata_for_file(self, relative_archive_path: str) -> bool:
        """Usuwa metadane dla pliku z thread-safe access."""
        with self._buffer_lock:
            try:
                current_metadata = self.load_metadata()

                if (
                    "file_pairs" in current_metadata
                    and isinstance(current_metadata.get("file_pairs"), dict)
                    and relative_archive_path in current_metadata["file_pairs"]
                ):
                    file_pairs_metadata = current_metadata["file_pairs"].copy()
                    del file_pairs_metadata[relative_archive_path]

                    # Aktualizuj bufor i zapisz
                    self._changes_buffer.update(
                        {
                            "file_pairs": file_pairs_metadata,
                            "unpaired_archives": current_metadata.get(
                                "unpaired_archives", []
                            ),
                            "unpaired_previews": current_metadata.get(
                                "unpaired_previews", []
                            ),
                            "timestamp": time.time(),
                        }
                    )
                    self._flush_changes()

                    logger.debug(
                        f"Usunięto metadane dla pliku: {relative_archive_path}"
                    )
                    return True
                else:
                    logger.debug(
                        f"Brak metadanych do usunięcia dla pliku: {relative_archive_path}"
                    )
                    return True

            except Exception as e:
                logger.error(
                    f"Błąd podczas usuwania metadanych dla {relative_archive_path}: {e}",
                    exc_info=True,
                )
                return False

    def get_metadata_for_relative_path(
        self, relative_archive_path: str
    ) -> Optional[Dict[str, Any]]:
        """Pobiera metadane dla ścieżki względnej."""
        metadata = self.load_metadata()
        if (
            metadata
            and "file_pairs" in metadata
            and isinstance(metadata.get("file_pairs"), dict)
        ):
            return metadata["file_pairs"].get(relative_archive_path)
        return None

    def save_file_pair_metadata(self, file_pair, working_directory: str = None) -> bool:
        """Zapisuje metadane dla pojedynczej pary plików."""
        # working_directory jest ignorowane - używamy self.working_directory
        try:
            relative_archive_path = self.operations.get_relative_path(
                file_pair.archive_path, self.working_directory
            )
            if relative_archive_path is None:
                logger.warning(
                    f"Nie można uzyskać ścieżki względnej dla {file_pair.archive_path}"
                )
                return False

            # Wczytaj aktualne metadane
            current_metadata = self.load_metadata()

            # Pobierz istniejące metadane par plików
            file_pairs_metadata = current_metadata.get("file_pairs", {})

            # Aktualizuj metadane dla tej konkretnej pary
            file_pairs_metadata[relative_archive_path] = {
                "stars": file_pair.get_stars(),
                "color_tag": file_pair.get_color_tag(),
            }

            # Użyj thread-safe zapisu
            with self._buffer_lock:
                self._changes_buffer.update(
                    {
                        "file_pairs": file_pairs_metadata,
                        "unpaired_archives": current_metadata.get(
                            "unpaired_archives", []
                        ),
                        "unpaired_previews": current_metadata.get(
                            "unpaired_previews", []
                        ),
                        "timestamp": time.time(),
                    }
                )
                self._flush_changes()  # Forcuj natychmiastowy zapis dla pojedynczych par

            logger.debug(f"Zapisano metadane dla pary: {relative_archive_path}")
            return True

        except Exception as e:
            logger.error(
                f"Błąd podczas zapisywania metadanych dla pojedynczej pary: {e}",
                exc_info=True,
            )
            return False

    def force_save(self):
        """Forcuje natychmiastowy zapis bufora."""
        with self._buffer_lock:
            # NAPRAWKA THREAD SAFETY: Zatrzymaj timer jeśli jest aktywny
            if self._save_timer:
                self._save_timer.cancel()
                self._save_timer = None
            self._flush_changes()

    def get_cache_info(self) -> Dict[str, Any]:
        """Zwraca informacje o stanie cache."""
        return self.cache.get_cache_info()

    def backup_metadata(self, backup_suffix: str = ".backup") -> bool:
        """Tworzy kopię zapasową pliku metadanych."""
        return self.io.backup_metadata_file(backup_suffix)
