"""
Główny komponent MetadataManager CFAB_3DHUB.
🚀 ETAP 3: Refaktoryzacja MetadataManager - WYSOKI priorytet
"""

import logging
import threading
import time
import weakref
from typing import Any, Callable, Dict, List, Optional

# Import normalizacji ścieżek
from src.utils.path_utils import normalize_path

# Import komponentów
from .metadata_cache import MetadataCache
from .metadata_io import MetadataIO
from .metadata_operations import MetadataOperations
from .metadata_validator import MetadataValidator

logger = logging.getLogger(__name__)


class MetadataBufferManager:
    """
    NOWY KOMPONENT: Zarządza buforem zmian metadanych.
    Rozdzielenie odpowiedzialności z głównej klasy MetadataManager.
    """

    def __init__(self, save_delay: int = 500, max_buffer_age: int = 5000):
        self._save_delay = save_delay  # ms
        self._max_buffer_age = max_buffer_age  # ms
        self._last_save_time = 0
        self._changes_buffer = {}
        self._buffer_lock = threading.RLock()
        self._save_timer = None
        self._flush_callback: Optional[Callable] = None
        self._is_shutdown = False

    def set_flush_callback(self, callback: Callable[[Dict], bool]):
        """Ustawia callback do wykonania flush operacji."""
        self._flush_callback = callback

    def add_changes(self, changes: Dict[str, Any]):
        """Dodaje zmiany do bufora thread-safe."""
        if self._is_shutdown:
            logger.warning("Buffer manager jest zamknięty - pomijam zmiany")
            return

        with self._buffer_lock:
            self._changes_buffer.update(changes)
            self._schedule_save()

    def _schedule_save(self):
        """Planuje zapis z uwzględnieniem max_buffer_age."""
        current_time = time.time() * 1000  # ms
        buffer_age = current_time - (self._last_save_time * 1000)

        # Wymuszaj zapis jeśli bufor jest za stary
        if buffer_age >= self._max_buffer_age:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "Buffer jest za stary (%dms), wymuszam natychmiastowy zapis",
                    buffer_age,
                )
            self._flush_now()
            return

        # Anuluj poprzedni timer tylko jeśli bufor nie jest za stary
        if self._save_timer and buffer_age < self._max_buffer_age:
            self._save_timer.cancel()

        # Zaplanuj nowy zapis - POPRAWKA: Thread-safe timer
        delay_seconds = self._save_delay / 1000.0
        self._save_timer = threading.Timer(delay_seconds, self._flush_now)
        self._save_timer.daemon = True  # POPRAWKA: Daemon thread dla bezpieczeństwa
        self._save_timer.start()

    def _flush_now(self):
        """Wykonuje natychmiastowy flush bufora."""
        with self._buffer_lock:
            if not self._changes_buffer or self._is_shutdown:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Buffer pusty lub manager zamknięty - pomijam flush")
                return

            if self._flush_callback:
                try:
                    success = self._flush_callback(self._changes_buffer.copy())
                    if success:
                        self._changes_buffer.clear()
                        self._last_save_time = time.time()
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug("Buffer został pomyślnie opróżniony")
                    else:
                        logger.warning(
                            "Flush callback zwrócił False - zachowuję dane w buforze"
                        )
                except (OSError, IOError) as e:
                    logger.error(f"Błąd I/O podczas flush bufora: {e}", exc_info=True)
                except (ValueError, TypeError) as e:
                    logger.error(
                        f"Błąd walidacji podczas flush bufora: {e}", exc_info=True
                    )
                except Exception as e:
                    logger.error(
                        f"Nieoczekiwany błąd podczas flush bufora: {e}", exc_info=True
                    )

            if self._save_timer:
                self._save_timer.cancel()
                self._save_timer = None

    def force_flush(self):
        """Wymusza natychmiastowy flush bufora."""
        with self._buffer_lock:
            if self._save_timer:
                self._save_timer.cancel()
                self._save_timer = None
            self._flush_now()

    def cleanup(self):
        """Cleanup resources."""
        with self._buffer_lock:
            self._is_shutdown = True
            if self._save_timer:
                self._save_timer.cancel()
                self._save_timer = None
            self._changes_buffer.clear()


class MetadataRegistry:
    """
    NOWY KOMPONENT: Zarządza instancjami MetadataManager.
    Rozdzielenie singleton pattern od business logic.
    """

    _instances: Dict[str, weakref.ReferenceType] = {}
    _instances_lock = threading.RLock()
    _cleanup_timer = None
    _cleanup_interval = 60.0  # POPRAWKA: Konfigurowalny interval

    @classmethod
    def get_instance(cls, working_directory: str) -> "MetadataManager":
        """
        Pobiera instancję MetadataManager dla danego katalogu.
        Używa weak references dla automatic cleanup.
        """
        norm_dir = normalize_path(working_directory)

        with cls._instances_lock:
            # Sprawdź czy istnieje ważna instancja
            if norm_dir in cls._instances:
                instance = cls._instances[norm_dir]()
                if instance is not None:
                    return instance
                else:
                    # Usuń martwe weak reference
                    del cls._instances[norm_dir]
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Usunięto martwe weak reference dla {norm_dir}")

            # Utwórz nową instancję
            new_instance = MetadataManager(working_directory)
            cls._instances[norm_dir] = weakref.ref(new_instance, cls._cleanup_callback)

            # Zaplanuj periodic cleanup
            cls._schedule_cleanup()

            return new_instance

    @classmethod
    def _cleanup_callback(cls, weak_ref):
        """Callback wywoływany gdy instancja jest garbage collected."""
        with cls._instances_lock:
            # Znajdź i usuń martwe weak reference
            to_remove = []
            for key, ref in cls._instances.items():
                if ref is weak_ref or ref() is None:
                    to_remove.append(key)

            for key in to_remove:
                del cls._instances[key]
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Usunięto martwe weak reference dla {key}")

    @classmethod
    def _schedule_cleanup(cls):
        """Planuje periodic cleanup martwych references."""
        if cls._cleanup_timer is None:
            cls._cleanup_timer = threading.Timer(
                cls._cleanup_interval, cls._periodic_cleanup
            )
            cls._cleanup_timer.daemon = True  # POPRAWKA: Daemon thread
            cls._cleanup_timer.start()

    @classmethod
    def _periodic_cleanup(cls):
        """Wykonuje periodic cleanup."""
        with cls._instances_lock:
            cls._cleanup_callback(None)  # Uruchom cleanup
            cls._cleanup_timer = None
            # Zaplanuj następny cleanup jeśli są jakieś instancje
            if cls._instances:
                cls._schedule_cleanup()

    @classmethod
    def cleanup_all(cls):
        """Cleanup wszystkich instancji - dla testów."""
        with cls._instances_lock:
            if cls._cleanup_timer:
                cls._cleanup_timer.cancel()
                cls._cleanup_timer = None

            # POPRAWKA: Explicit cleanup wszystkich instancji
            for key, ref in list(cls._instances.items()):
                instance = ref()
                if instance is not None:
                    try:
                        instance.cleanup()
                    except Exception as e:
                        logger.warning(f"Błąd podczas cleanup instancji {key}: {e}")

            cls._instances.clear()


class MetadataManager:
    """
    REFAKTORYZOWANY: Uproszczony metadata manager.
    Usunięto singleton pattern - zarządzane przez MetadataRegistry.
    Wyciągnięto buffer management do MetadataBufferManager.
    """

    def __init__(self, working_directory: str):
        """
        Inicjalizuje menedżer metadanych.

        Args:
            working_directory (str): Ścieżka do folderu roboczego
        """
        self.working_directory = normalize_path(working_directory)

        # Inicjalizacja komponentów
        self.cache = MetadataCache(cache_timeout=30.0)
        self.io = MetadataIO(working_directory)
        self.operations = MetadataOperations(working_directory)
        self.validator = MetadataValidator()

        # NOWY: Wydzielony buffer manager
        self.buffer_manager = MetadataBufferManager(save_delay=500, max_buffer_age=5000)
        self.buffer_manager.set_flush_callback(self._atomic_write_callback)

        # Thread safety
        self._operation_lock = threading.RLock()

    def _atomic_write_callback(self, data: Dict[str, Any]) -> bool:
        """Callback dla buffer manager do wykonywania atomic writes."""
        try:
            success = self.io.atomic_write(data)
            if success:
                self.cache.invalidate()  # Invalidate cache po zapisie
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Pomyślnie zapisano zmiany z bufora")
            return success
        except (OSError, IOError) as e:
            logger.error(f"Błąd I/O podczas atomic write: {e}", exc_info=True)
            return False
        except (ValueError, TypeError) as e:
            logger.error(f"Błąd walidacji podczas atomic write: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd podczas atomic write: {e}", exc_info=True)
            return False

    @classmethod
    def get_instance(cls, working_directory: str) -> "MetadataManager":
        """
        Factory method - deleguje do MetadataRegistry.
        Zachowana dla backward compatibility.
        """
        return MetadataRegistry.get_instance(working_directory)

    def get_metadata_path(self) -> str:
        """Zwraca ścieżkę do pliku metadanych."""
        return self.io.get_metadata_path()

    def get_lock_path(self) -> str:
        """Zwraca ścieżkę do pliku blokady."""
        return self.io.get_lock_path()

    def load_metadata(self) -> Dict[str, Any]:
        """
        Wczytuje metadane z pliku z obsługą cache.
        OPTYMALIZACJA: Sprawdza czy dane się zmieniły przed reload.

        Returns:
            Dict zawierający metadane
        """
        # Sprawdź cache
        cached_metadata = self.cache.get()
        if cached_metadata is not None:
            return cached_metadata

        # Wczytaj z pliku z thread safety
        with self._operation_lock:
            try:
                metadata = self.io.load_metadata_from_file()
                # Zaktualizuj cache
                self.cache.set(metadata)
                return metadata
            except (OSError, IOError) as e:
                logger.error(
                    f"Błąd I/O podczas ładowania metadanych: {e}", exc_info=True
                )
                return {}
            except (ValueError, TypeError) as e:
                logger.error(
                    f"Błąd walidacji podczas ładowania metadanych: {e}", exc_info=True
                )
                return {}
            except Exception as e:
                logger.error(
                    f"Nieoczekiwany błąd podczas ładowania metadanych: {e}",
                    exc_info=True,
                )
                return {}

    def save_metadata(
        self,
        file_pairs_list: List,
        unpaired_archives: List[str],
        unpaired_previews: List[str],
    ) -> bool:
        """
        OPTYMALIZACJA: Batch save z wykorzystaniem buffer managera.
        Thread-safe metadata saving.
        """
        with self._operation_lock:
            try:
                metadata_to_save = self.operations.prepare_metadata_for_save(
                    file_pairs_list, unpaired_archives, unpaired_previews
                )

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "Dodaję metadane do bufora: %s", self.io.get_metadata_path()
                    )

                # Użyj buffer manager zamiast direct write
                self.buffer_manager.add_changes(metadata_to_save)

                return True

            except (ValueError, TypeError) as e:
                logger.error(
                    "Błąd walidacji podczas prepare metadata: %s", e, exc_info=True
                )
                return False
            except Exception as e:
                logger.error(
                    "Nieoczekiwany błąd podczas prepare metadata: %s", e, exc_info=True
                )
                return False

    def apply_metadata_to_file_pairs(self, file_pairs_list: List) -> bool:
        """Aplikuje metadane do listy par plików."""
        try:
            metadata = self.load_metadata()
            return self.operations.apply_metadata_to_file_pairs(
                metadata, file_pairs_list
            )
        except Exception as e:
            logger.error(f"Błąd podczas aplikowania metadanych: {e}", exc_info=True)
            return False

    def remove_metadata_for_file(self, relative_archive_path: str) -> bool:
        """
        OPTYMALIZACJA: Incremental update zamiast full reload.
        Usuwa metadane dla pliku z thread-safe access.
        """
        with self._operation_lock:
            try:
                current_metadata = self.load_metadata()

                if (
                    "file_pairs" in current_metadata
                    and isinstance(current_metadata.get("file_pairs"), dict)
                    and relative_archive_path in current_metadata["file_pairs"]
                ):
                    # OPTYMALIZACJA: Shallow copy zamiast deep copy
                    file_pairs_metadata = current_metadata["file_pairs"].copy()
                    del file_pairs_metadata[relative_archive_path]

                    # Użyj buffer manager
                    changes = {
                        "file_pairs": file_pairs_metadata,
                        "unpaired_archives": current_metadata.get(
                            "unpaired_archives", []
                        ),
                        "unpaired_previews": current_metadata.get(
                            "unpaired_previews", []
                        ),
                        "has_special_folders": current_metadata.get(
                            "has_special_folders", False
                        ),
                        "special_folders": current_metadata.get("special_folders", []),
                        "timestamp": time.time(),
                    }

                    self.buffer_manager.add_changes(changes)

                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            "Zaplanowano usunięcie metadanych dla: %s",
                            relative_archive_path,
                        )
                    return True
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            "Brak metadanych do usunięcia dla: %s",
                            relative_archive_path,
                        )
                    return True

            except (ValueError, TypeError) as e:
                logger.error(
                    "Błąd walidacji podczas usuwania metadanych dla %s: %s",
                    relative_archive_path,
                    e,
                    exc_info=True,
                )
                return False
            except Exception as e:
                logger.error(
                    "Nieoczekiwany błąd podczas usuwania metadanych dla %s: %s",
                    relative_archive_path,
                    e,
                    exc_info=True,
                )
                return False

    def get_metadata_for_relative_path(
        self, relative_archive_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Pobiera metadane dla określonej ścieżki względnej.

        Args:
            relative_archive_path: Względna ścieżka do pliku archiwum

        Returns:
            Dict z metadanymi dla pliku lub None jeśli nie znaleziono
        """
        try:
            metadata = self.load_metadata()
            if (
                "file_pairs" in metadata
                and isinstance(metadata.get("file_pairs"), dict)
                and relative_archive_path in metadata["file_pairs"]
            ):
                return metadata["file_pairs"][relative_archive_path]
            return None
        except Exception as e:
            logger.error(
                f"Błąd podczas pobierania metadanych dla {relative_archive_path}: {e}",
                exc_info=True,
            )
            return None

    def has_special_folders(self) -> bool:
        """
        Sprawdza czy katalog zawiera specjalne foldery na podstawie metadanych.

        Returns:
            True jeśli katalog zawiera specjalne foldery, False w przeciwnym razie
        """
        try:
            metadata = self.load_metadata()
            if (
                "file_pairs" in metadata
                and isinstance(metadata.get("file_pairs"), dict)
                and "__metadata__" in metadata["file_pairs"]
                and isinstance(metadata["file_pairs"]["__metadata__"], dict)
            ):
                return metadata["file_pairs"]["__metadata__"].get(
                    "has_special_folders", False
                )
            return False
        except Exception as e:
            logger.error(
                f"Błąd podczas sprawdzania specjalnych folderów: {e}", exc_info=True
            )
            return False

    def get_special_folders(self) -> List[str]:
        """
        Pobiera listę specjalnych folderów z metadanych.

        Returns:
            Lista nazw specjalnych folderów lub pusta lista
        """
        try:
            metadata = self.load_metadata()
            if (
                "file_pairs" in metadata
                and isinstance(metadata.get("file_pairs"), dict)
                and "__metadata__" in metadata["file_pairs"]
                and isinstance(metadata["file_pairs"]["__metadata__"], dict)
                and "special_folders" in metadata["file_pairs"]["__metadata__"]
            ):
                return metadata["file_pairs"]["__metadata__"]["special_folders"]
            return []
        except Exception as e:
            logger.error(
                f"Błąd podczas pobierania specjalnych folderów: {e}", exc_info=True
            )
            return []

    def save_file_pair_metadata(self, file_pair, working_directory: str = None) -> bool:
        """
        OPTYMALIZACJA: Single file update przez buffer manager.
        Zapisuje metadane dla pojedynczej pary plików.
        """
        with self._operation_lock:
            try:
                relative_archive_path = self.operations.get_relative_path(
                    file_pair.archive_path, self.working_directory
                )
                if relative_archive_path is None:
                    logger.warning(
                        f"Nie można uzyskać ścieżki względnej dla {file_pair.archive_path}"
                    )
                    return False

                # OPTYMALIZACJA: Incremental update
                current_metadata = self.load_metadata()
                file_pairs_metadata = current_metadata.get("file_pairs", {}).copy()

                # Aktualizuj tylko tę konkretną parę
                file_pairs_metadata[relative_archive_path] = {
                    "stars": file_pair.get_stars(),
                    "color_tag": file_pair.get_color_tag(),
                }

                # Użyj buffer manager
                changes = {
                    "file_pairs": file_pairs_metadata,
                    "unpaired_archives": current_metadata.get("unpaired_archives", []),
                    "unpaired_previews": current_metadata.get("unpaired_previews", []),
                    "timestamp": time.time(),
                }

                self.buffer_manager.add_changes(changes)

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        f"Zaplanowano zapis metadanych dla: {relative_archive_path}"
                    )
                return True

            except (ValueError, TypeError) as e:
                logger.error(
                    f"Błąd walidacji podczas zapisywania metadanych dla pary: {e}",
                    exc_info=True,
                )
                return False
            except Exception as e:
                logger.error(
                    f"Nieoczekiwany błąd podczas zapisywania metadanych dla pary: {e}",
                    exc_info=True,
                )
                return False

    def force_save(self):
        """Wymusza natychmiastowy zapis bufora."""
        self.buffer_manager.force_flush()

    def get_cache_info(self) -> Dict[str, Any]:
        """Zwraca informacje o stanie cache."""
        return self.cache.get_cache_info()

    def backup_metadata(self, backup_suffix: str = ".backup") -> bool:
        """Tworzy kopię zapasową pliku metadanych."""
        try:
            return self.io.backup_metadata_file(backup_suffix)
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia backup: {e}", exc_info=True)
            return False

    def cleanup(self):
        """
        NOWY: Cleanup resources.
        Ważne dla proper resource management.
        """
        try:
            if hasattr(self, "buffer_manager"):
                self.buffer_manager.cleanup()
        except Exception as e:
            logger.warning(f"Błąd podczas cleanup: {e}")

    def __del__(self):
        """Destructor - cleanup resources."""
        try:
            self.cleanup()
        except:
            pass  # Ignore errors during cleanup
