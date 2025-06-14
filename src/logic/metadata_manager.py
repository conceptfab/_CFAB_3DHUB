"""
Zarządzanie metadanymi aplikacji, takimi jak "ulubione" oraz inne ustawienia.
Metadane są przechowywane w pliku JSON w folderze `.app_metadata`.
"""

import json
import logging
import os
import shutil
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional

from filelock import FileLock, Timeout

# Import normalizacji ścieżek
from src.utils.path_utils import normalize_path

# Stałe związane z metadanymi
METADATA_DIR_NAME = ".app_metadata"
METADATA_FILE_NAME = "metadata.json"
LOCK_FILE_NAME = "metadata.lock"  # Nazwa pliku blokady
LOCK_TIMEOUT = 0.5  # Czas oczekiwania na blokadę w sekundach (zoptymalizowane)
MIN_THUMBNAIL_WIDTH = 80  # Minimalna szerokość miniaturki dla bezpieczeństwa

# Konfiguracja loggera dla tego modułu
logger = logging.getLogger(__name__)


class MetadataManager:
    """
    Unified metadata manager - single source of truth.
    Thread-safe metadata management with caching and proper error handling.
    """

    _instances = {}  # Singleton pattern per working directory
    _instances_lock = threading.RLock()

    def __init__(self, working_directory: str):
        """
        Inicjalizuje menedżer metadanych.

        Args:
            working_directory (str): Ścieżka do folderu roboczego
        """
        self.working_directory = normalize_path(working_directory)
        self._changes_buffer = {}
        self._buffer_lock = threading.RLock()  # Thread-safe access to buffer
        self._last_save_time = 0
        self._save_delay = 2.0  # Opóźnienie zapisu w sekundach
        self._save_timer = None
        self._metadata_cache = {}
        self._cache_timeout = 30  # 30 sekund cache
        self._cache_timestamp = 0

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
        return get_metadata_path(self.working_directory)

    def get_lock_path(self) -> str:
        """Zwraca ścieżkę do pliku blokady."""
        return get_lock_path(self.working_directory)

    def load_metadata(self) -> Dict[str, Any]:
        """
        Wczytuje metadane z pliku z obsługą cache.

        Returns:
            Dict zawierający metadane
        """
        current_time = time.time()

        # Sprawdź cache
        if (
            self._metadata_cache
            and current_time - self._cache_timestamp < self._cache_timeout
        ):
            return self._metadata_cache.copy()

        # Wczytaj z pliku
        metadata = load_metadata(self.working_directory)

        # Zaktualizuj cache
        self._metadata_cache = metadata.copy()
        self._cache_timestamp = current_time

        return metadata

    def _invalidate_cache(self):
        """Invaliduje cache metadanych."""
        self._metadata_cache.clear()
        self._cache_timestamp = 0

    def _should_save(self) -> bool:
        """Sprawdza czy należy zapisać zmiany."""
        current_time = time.time()
        return (current_time - self._last_save_time) >= self._save_delay

    def _flush_changes(self):
        """Thread-safe flush of buffered changes."""
        with self._buffer_lock:
            if not self._changes_buffer:
                print("🔥 _flush_changes: Bufor pusty - nie ma nic do zapisu")
                return

            try:
                # Atomic write with proper error handling
                success = self._atomic_write(self._changes_buffer)

                if success:
                    self._changes_buffer.clear()
                    self._last_save_time = time.time()
                    self._invalidate_cache()  # Invalidate cache after write
                    logger.debug("Successfully flushed metadata changes")

            except Exception as e:
                logger.error(f"Failed to flush metadata changes: {e}", exc_info=True)
                # Could add retry logic here
            finally:
                self._save_timer = None

    def _atomic_write(self, metadata_dict: Dict[str, Any]) -> bool:
        """
        Atomic write with file locking and proper error handling.

        Args:
            metadata_dict: Dictionary containing metadata to write

        Returns:
            bool: True if successful, False otherwise
        """
        metadata_path = self.get_metadata_path()
        lock_path = self.get_lock_path()
        metadata_dir = os.path.dirname(metadata_path)

        # Ensure directory exists
        os.makedirs(metadata_dir, exist_ok=True)

        # Use file lock with shorter timeout
        lock = FileLock(lock_path, timeout=LOCK_TIMEOUT)
        temp_file_path = None

        try:
            with lock:
                # Create temporary file in same directory for atomic move
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    delete=False,
                    encoding="utf-8",
                    dir=metadata_dir,
                    suffix=".tmp",
                    prefix="metadata_",
                ) as temp_file:
                    json.dump(metadata_dict, temp_file, ensure_ascii=False, indent=2)
                    temp_file_path = temp_file.name

                # Atomic move (rename)
                if os.name == "nt":  # Windows
                    if os.path.exists(metadata_path):
                        os.replace(temp_file_path, metadata_path)
                    else:
                        shutil.move(temp_file_path, metadata_path)
                else:  # Unix-like
                    os.rename(temp_file_path, metadata_path)

                logger.debug(f"Successfully saved metadata to {metadata_path}")
                return True

        except Timeout:
            logger.warning(f"Could not acquire lock for {lock_path} within timeout")
            return False
        except Exception as e:
            logger.error(f"Error writing metadata: {e}", exc_info=True)
            return False
        finally:
            # Cleanup temp file if it still exists
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except OSError as e:
                    logger.warning(f"Could not cleanup temp file {temp_file_path}: {e}")

    def save_metadata(
        self,
        file_pairs_list: List,
        unpaired_archives: List[str],
        unpaired_previews: List[str],
    ) -> bool:
        """Thread-safe metadata saving with buffering."""
        with self._buffer_lock:
            try:
                # Przygotuj metadane do zapisu
                file_pairs_metadata = {}

                for file_pair in file_pairs_list:
                    if not all(
                        hasattr(file_pair, attr)
                        for attr in ["archive_path", "get_stars", "get_color_tag"]
                    ):
                        logger.warning(
                            f"Skipping file_pair with missing attributes: {file_pair}"
                        )
                        continue

                    relative_archive_path = get_relative_path(
                        file_pair.archive_path, self.working_directory
                    )
                    if relative_archive_path is None:
                        logger.warning(
                            f"Cannot get relative path for {file_pair.archive_path}"
                        )
                        continue

                    file_pairs_metadata[relative_archive_path] = {
                        "stars": file_pair.get_stars(),
                        "color_tag": file_pair.get_color_tag(),
                    }

                # Przygotuj listy niesparowanych plików
                unpaired_archives_rel = []
                for p in unpaired_archives:
                    rel_p = get_relative_path(p, self.working_directory)
                    if rel_p is not None:
                        unpaired_archives_rel.append(rel_p)

                unpaired_previews_rel = []
                for p in unpaired_previews:
                    rel_p = get_relative_path(p, self.working_directory)
                    if rel_p is not None:
                        unpaired_previews_rel.append(rel_p)

                # Dodaj zmiany do bufora
                self._changes_buffer.update(
                    {
                        "file_pairs": file_pairs_metadata,
                        "unpaired_archives": unpaired_archives_rel,
                        "unpaired_previews": unpaired_previews_rel,
                        "timestamp": time.time(),
                    }
                )

                # Anuluj poprzedni timer jeśli istnieje
                if self._save_timer:
                    self._save_timer.cancel()

                # Zaplanuj zapis z opóźnieniem
                self._save_timer = threading.Timer(
                    self._save_delay, self._flush_changes
                )
                self._save_timer.start()

                return True

            except Exception as e:
                logger.error(f"Error buffering metadata: {e}", exc_info=True)
                return False

    def apply_metadata_to_file_pairs(self, file_pairs_list: List) -> bool:
        """Aplikuje metadane do listy par plików."""
        metadata = self.load_metadata()
        return _apply_metadata_to_file_pairs_direct(
            metadata, file_pairs_list, self.working_directory
        )

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
            relative_archive_path = get_relative_path(
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
            if self._save_timer:
                self._save_timer.cancel()
            self._flush_changes()


# Legacy functions - delegated to MetadataManager for backward compatibility
def load_metadata(working_directory: str) -> Dict[str, Any]:
    """
    Legacy function: Use MetadataManager.get_instance(dir).load_metadata()
    Maintained for backward compatibility.
    """
    return _load_metadata_direct(working_directory)


def save_metadata(
    working_directory: str,
    file_pairs_list: List,
    unpaired_archives: List[str],
    unpaired_previews: List[str],
) -> bool:
    """
    Legacy function: Use MetadataManager.get_instance(dir).save_metadata()
    Maintained for backward compatibility.
    """
    manager = MetadataManager.get_instance(working_directory)
    return manager.save_metadata(file_pairs_list, unpaired_archives, unpaired_previews)


def get_metadata_path(working_directory: str) -> str:
    """
    Zwraca pełną ścieżkę do pliku metadanych w podanym folderze roboczym.

    Args:
        working_directory (str): Ścieżka do folderu roboczego

    Returns:
        str: Pełna ścieżka do pliku metadanych
    """
    # Normalizujemy ścieżkę katalogu roboczego
    normalized_working_dir = normalize_path(working_directory)
    metadata_dir = os.path.join(normalized_working_dir, METADATA_DIR_NAME)
    return normalize_path(os.path.join(metadata_dir, METADATA_FILE_NAME))


def get_lock_path(working_directory: str) -> str:
    """
    Zwraca pełną ścieżkę do pliku blokady metadanych.

    Args:
        working_directory (str): Ścieżka do folderu roboczego.

    Returns:
        str: Pełna ścieżka do pliku blokady.
    """
    normalized_working_dir = normalize_path(working_directory)
    metadata_dir = os.path.join(normalized_working_dir, METADATA_DIR_NAME)
    return normalize_path(os.path.join(metadata_dir, LOCK_FILE_NAME))


def get_relative_path(absolute_path: str, base_path: str) -> Optional[str]:
    """
    Konwertuje ścieżkę absolutną na względną względem podanej ścieżki bazowej,
    używając znormalizowanych ścieżek.

    Args:
        absolute_path (str): Ścieżka absolutna do konwersji.
        base_path (str): Ścieżka bazowa, względem której tworzona jest ścieżka względna.

    Returns:
        Optional[str]: Ścieżka względna lub None w przypadku błędu (np. różne dyski).
    """
    try:
        # Normalizujemy obie ścieżki przed konwersją
        norm_abs_path = normalize_path(absolute_path)
        norm_base_path = normalize_path(base_path)

        # Upewniamy się, że obie ścieżki są absolutne
        if not os.path.isabs(norm_abs_path):
            logger.warning(f"Ścieżka do konwersji nie jest absolutna: {norm_abs_path}")
            norm_abs_path = normalize_path(os.path.abspath(norm_abs_path))

        if not os.path.isabs(norm_base_path):
            logger.warning(f"Ścieżka bazowa nie jest absolutna: {norm_base_path}")
            norm_base_path = normalize_path(os.path.abspath(norm_base_path))

        # Sprawdzenie, czy ścieżki są na różnych dyskach (tylko Windows)
        if os.name == "nt":
            abs_drive = os.path.splitdrive(norm_abs_path)[0].lower()
            base_drive = os.path.splitdrive(norm_base_path)[0].lower()
            if abs_drive and base_drive and abs_drive != base_drive:
                logger.error(
                    f"Nie można utworzyć ścieżki względnej: ścieżki są na różnych dyskach. "
                    f"Ścieżka: {norm_abs_path}, Baza: {norm_base_path}"
                )
                return None

        # Użycie os.path.relpath do uzyskania ścieżki względnej
        relative_path = os.path.relpath(norm_abs_path, norm_base_path)

        # Normalizujemy wynikową ścieżkę względną
        relative_path_normalized = normalize_path(relative_path)

        logger.debug(
            f"Pomyślnie skonwertowano ścieżkę: {norm_abs_path} -> {relative_path_normalized} "
            f"(względem: {norm_base_path})"
        )
        return relative_path_normalized

    except Exception as e:
        logger.error(
            f"Błąd podczas konwersji ścieżki {absolute_path} względem {base_path}: {e}",
            exc_info=True,
        )
        return None


def get_absolute_path(relative_path: str, base_path: str) -> Optional[str]:
    """
    Konwertuje ścieżkę względną na absolutną względem podanej ścieżki bazowej,
    używając znormalizowanych ścieżek.

    Args:
        relative_path (str): Ścieżka względna do konwersji.
        base_path (str): Ścieżka bazowa, względem której tworzona jest ścieżka absolutna.

    Returns:
        Optional[str]: Ścieżka absolutna lub None w przypadku błędu.
    """
    try:
        # Normalizujemy obie ścieżki przed konwersją
        norm_rel_path = normalize_path(relative_path)
        norm_base_path = normalize_path(base_path)

        # Upewniamy się, że ścieżka bazowa jest absolutna
        if not os.path.isabs(norm_base_path):
            logger.warning(
                f"Ścieżka bazowa nie jest absolutna: {norm_base_path}. Konwertuję na absolutną."
            )
            norm_base_path = normalize_path(os.path.abspath(norm_base_path))

        # Łączymy ścieżki
        absolute_path = os.path.join(norm_base_path, norm_rel_path)

        # Normalizujemy wynikową ścieżkę absolutną
        absolute_path_normalized = normalize_path(absolute_path)

        logger.debug(
            f"Pomyślnie skonwertowano ścieżkę: {norm_rel_path} -> {absolute_path_normalized} "
            f"(względem: {norm_base_path})"
        )
        return absolute_path_normalized

    except Exception as e:
        logger.error(
            f"Błąd podczas konwersji ścieżki {relative_path} względem {base_path}: {e}",
            exc_info=True,
        )
        return None


def _validate_metadata_structure(metadata: Dict[str, Any]) -> bool:
    """
    Sprawdza, czy struktura metadanych jest poprawna.

    Args:
        metadata (Dict[str, Any]): Słownik metadanych do sprawdzenia.

    Returns:
        bool: True jeśli struktura jest poprawna, False w przeciwnym razie.
    """
    try:
        # Sprawdzenie obecności wymaganych kluczy
        required_keys = ["file_pairs", "unpaired_archives", "unpaired_previews"]
        for key in required_keys:
            if key not in metadata:
                logger.warning(f"Brak wymaganego klucza '{key}' w metadanych.")
                return False

        # Sprawdzenie typów danych
        if not isinstance(metadata["file_pairs"], dict):
            logger.warning("Klucz 'file_pairs' nie jest słownikiem.")
            return False

        if not isinstance(metadata["unpaired_archives"], list):
            logger.warning("Klucz 'unpaired_archives' nie jest listą.")
            return False

        if not isinstance(metadata["unpaired_previews"], list):
            logger.warning("Klucz 'unpaired_previews' nie jest listą.")
            return False

        # Sprawdzenie struktury file_pairs
        for relative_path, pair_metadata in metadata["file_pairs"].items():
            if not isinstance(pair_metadata, dict):
                logger.warning(
                    f"Metadane dla '{relative_path}' nie są słownikiem: {pair_metadata}"
                )
                return False

            # Sprawdzenie wymaganych kluczy dla każdej pary
            if "stars" not in pair_metadata or "color_tag" not in pair_metadata:
                logger.warning(
                    f"Metadane dla '{relative_path}' nie zawierają wymaganych kluczy 'stars' lub 'color_tag'."
                )
                return False

            # Sprawdzenie typów wartości
            if not isinstance(pair_metadata["stars"], int):
                logger.warning(
                    f"Wartość 'stars' dla '{relative_path}' nie jest liczbą całkowitą: {pair_metadata['stars']}"
                )
                return False

            if not (
                isinstance(pair_metadata["color_tag"], str)
                or pair_metadata["color_tag"] is None
            ):
                logger.warning(
                    f"Wartość 'color_tag' dla '{relative_path}' nie jest ciągiem znaków ani None: {pair_metadata['color_tag']}"
                )
                return False

        logger.debug("Struktura metadanych jest poprawna.")
        return True

    except Exception as e:
        logger.error(f"Błąd podczas walidacji struktury metadanych: {e}", exc_info=True)
        return False


def _load_metadata_direct(working_directory: str) -> Dict[str, Any]:
    """
    Direct metadata loading without caching - used by legacy load_metadata function.

    Args:
        working_directory (str): Ścieżka do folderu roboczego.

    Returns:
        Dict[str, Any]: Słownik metadanych lub domyślna struktura w przypadku błędu.
    """
    metadata_path = get_metadata_path(working_directory)
    default_metadata = {
        "file_pairs": {},
        "unpaired_archives": [],
        "unpaired_previews": [],
    }

    logger.debug(f"Próba wczytania metadanych z: {metadata_path}")

    if not os.path.exists(metadata_path):
        logger.debug(
            f"Plik metadanych nie istnieje: {metadata_path}. Zwracam domyślne metadane."
        )
        return default_metadata

    lock_path = get_lock_path(working_directory)
    lock = FileLock(lock_path, timeout=LOCK_TIMEOUT)

    try:
        with lock:
            with open(metadata_path, "r", encoding="utf-8") as file:
                metadata = json.load(file)

            logger.debug(f"Pomyślnie wczytano metadane z {metadata_path}")

            # Walidacja struktury
            if not _validate_metadata_structure(metadata):
                logger.warning(
                    "Struktura metadanych jest niepoprawna. Zwracam domyślne metadane."
                )
                return default_metadata

            return metadata

    except Timeout:
        logger.error(
            f"Nie można uzyskać blokady pliku metadanych {lock_path} w ciągu {LOCK_TIMEOUT}s podczas wczytywania.",
            exc_info=True,
        )
        return default_metadata
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(
            f"Błąd parsowania JSON metadanych z {metadata_path}: {e}", exc_info=True
        )
        return default_metadata
    except Exception as e:
        logger.error(
            f"Błąd wczytywania metadanych z {metadata_path}: {e}", exc_info=True
        )
        return default_metadata


def apply_metadata_to_file_pairs(working_directory: str, file_pairs_list: List) -> bool:
    """
    Legacy function: Use MetadataManager.get_instance(dir).apply_metadata_to_file_pairs()
    Maintained for backward compatibility.

    Args:
        working_directory (str): Ścieżka do folderu roboczego.
        file_pairs_list (List): Lista obiektów FilePair do aktualizacji.

    Returns:
        bool: True jeśli aktualizacja przebiegła pomyślnie, False w przypadku błędu.
    """
    manager = MetadataManager.get_instance(working_directory)
    return _apply_metadata_to_file_pairs_direct(
        manager.load_metadata(), file_pairs_list, working_directory
    )


def _apply_metadata_to_file_pairs_direct(
    metadata: Dict[str, Any], file_pairs_list: List, working_directory: str
) -> bool:
    """
    Direct implementation of metadata application - used by legacy function.
    """
    try:
        if not metadata or "file_pairs" not in metadata or not metadata["file_pairs"]:
            logger.debug(
                "Brak metadanych par plików do zastosowania lub błąd wczytywania. "
                f"(Katalog: {working_directory})"
            )
            return True  # Traktujemy to jako "sukces" w sensie braku danych do przetworzenia

        file_pairs_metadata = metadata["file_pairs"]

        logger.debug(
            f"Rozpoczynanie stosowania metadanych do {len(file_pairs_list)} par plików."
        )
        applied_count = 0

        # OPTYMALIZACJA: Cache dla normalizacji ścieżek - unikaj powtarzania
        normalized_working_dir = normalize_path(working_directory)

        # OPTYMALIZACJA: Batch processing z progress reportingiem
        total_files = len(file_pairs_list)
        batch_size = 50  # Przetwarzaj w batches dla lepszego progressu

        for i, file_pair in enumerate(file_pairs_list):
            # Progress reporting co batch_size plików
            if i % batch_size == 0:
                logger.debug(f"Przetwarzanie metadanych: {i}/{total_files} plików...")

            if not all(
                hasattr(file_pair, attr)
                for attr in [
                    "archive_path",
                    "get_stars",
                    "set_stars",
                    "get_color_tag",
                    "set_color_tag",
                    "get_base_name",  # Kluczowe dla identyfikacji
                ]
            ):
                logger.warning(
                    f"Pominięto obiekt w file_pairs_list przy stosowaniu metadanych - brak wymaganych atrybutów: {file_pair}"
                )
                continue

            # OPTYMALIZACJA: Użyj prostszego sposobu na obliczenie ścieżki względnej
            try:
                normalized_archive_path = normalize_path(file_pair.archive_path)
                relative_archive_path = os.path.relpath(
                    normalized_archive_path, normalized_working_dir
                )
                relative_archive_path = normalize_path(relative_archive_path)
            except (ValueError, OSError) as e:
                logger.warning(
                    f"Nie można uzyskać ścieżki względnej dla {file_pair.archive_path} (nazwa bazowa: {file_pair.get_base_name()}) "
                    f"podczas stosowania metadanych: {e}. Pomijam."
                )
                continue

            if relative_archive_path in file_pairs_metadata:
                pair_metadata = file_pairs_metadata[relative_archive_path]
                updated = False

                if "stars" in pair_metadata and isinstance(pair_metadata["stars"], int):
                    if file_pair.get_stars() != pair_metadata["stars"]:
                        file_pair.set_stars(pair_metadata["stars"])
                        updated = True

                if "color_tag" in pair_metadata and (
                    isinstance(pair_metadata["color_tag"], str)
                    or pair_metadata["color_tag"] is None
                ):
                    if file_pair.get_color_tag() != pair_metadata["color_tag"]:
                        file_pair.set_color_tag(pair_metadata["color_tag"])
                        updated = True

                if updated:
                    applied_count += 1
                    # Zmniejsz verbose logging dla lepszej wydajności
                    if applied_count % 10 == 0:  # Log co 10 zaktualizowanych plików
                        logger.debug(
                            f"Zastosowano metadane dla {applied_count} plików (ostatni: '{relative_archive_path}')"
                        )

        logger.info(
            f"Zakończono stosowanie metadanych. Zaktualizowano {applied_count} z {len(file_pairs_list)} par plików."
        )
        return True

    except Exception as e:
        logger.error(f"Błąd stosowania metadanych do par plików: {e}", exc_info=True)
        return False


def save_file_pair_metadata(file_pair, working_directory: str) -> bool:
    """
    Legacy function: Use MetadataManager.get_instance(dir).save_file_pair_metadata()
    Maintained for backward compatibility.

    Args:
        file_pair: Obiekt FilePair do zapisania metadanych
        working_directory: Katalog roboczy

    Returns:
        bool: True jeśli zapisano pomyślnie, False w przypadku błędu
    """
    try:
        manager = MetadataManager.get_instance(working_directory)

        # Pobierz ścieżkę względną dla pliku archiwum
        relative_archive_path = get_relative_path(
            file_pair.archive_path, working_directory
        )
        if relative_archive_path is None:
            logger.warning(
                f"Nie można uzyskać ścieżki względnej dla {file_pair.archive_path}"
            )
            return False

        # Wczytaj aktualne metadane
        current_metadata = manager.load_metadata()

        # Pobierz istniejące metadane par plików
        file_pairs_metadata = current_metadata.get("file_pairs", {})

        # Aktualizuj metadane dla tej konkretnej pary
        file_pairs_metadata[relative_archive_path] = {
            "stars": file_pair.get_stars(),
            "color_tag": file_pair.get_color_tag(),
        }

        # Użyj MetadataManager do zapisu
        with manager._buffer_lock:
            manager._changes_buffer.update(
                {
                    "file_pairs": file_pairs_metadata,
                    "unpaired_archives": current_metadata.get("unpaired_archives", []),
                    "unpaired_previews": current_metadata.get("unpaired_previews", []),
                    "timestamp": time.time(),
                }
            )
            manager._flush_changes()  # Forcuj natychmiastowy zapis dla pojedynczych par

        logger.debug(f"Zapisano metadane dla pary: {relative_archive_path}")
        return True

    except Exception as e:
        logger.error(
            f"Błąd podczas zapisywania metadanych dla pojedynczej pary: {e}",
            exc_info=True,
        )
        return False


# Dodatkowe funkcje pomocnicze, jeśli potrzebne, np. do usuwania metadanych dla konkretnych plików
# lub czyszczenia nieaktualnych wpisów.


def remove_metadata_for_file(
    working_directory: str, relative_archive_path: str
) -> bool:
    """
    Legacy function: Use MetadataManager.get_instance(dir).remove_metadata_for_file()
    Maintained for backward compatibility.
    """
    metadata_path = get_metadata_path(working_directory)
    lock_path = get_lock_path(working_directory)  # Nieużywane, jeśli blokada wyłączona
    # lock = FileLock(lock_path, timeout=LOCK_TIMEOUT) # Blokada wyłączona

    logger.debug(
        f"Próba usunięcia metadanych dla pliku '{relative_archive_path}' w katalogu '{working_directory}'."
    )

    try:
        # with lock: # Blokada wyłączona
        if not os.path.exists(metadata_path):
            logger.debug(
                f"Plik metadanych {metadata_path} nie istnieje. Nic do usunięcia dla '{relative_archive_path}'."
            )
            return True  # Traktujemy jako sukces, bo nie ma czego usuwać

        # Używamy wewnętrznej funkcji do wczytania, aby uniknąć problemów z zagnieżdżonymi blokadami,
        # gdyby load_metadata używało FileLock. Obecnie load_metadata nie używa blokady.
        current_metadata: Dict[str, Any] = {}
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                current_metadata = json.load(f)
            if not _validate_metadata_structure(
                current_metadata
            ):  # Walidacja po wczytaniu
                logger.warning(
                    f"Nieprawidłowa struktura metadanych w {metadata_path} podczas próby usunięcia wpisu. Próba kontynuacji."
                )
                # Jeśli struktura jest zła, możemy nie znaleźć klucza 'file_pairs'
                # lub może on nie być słownikiem. Poniższy kod powinien to obsłużyć.
        except json.JSONDecodeError:
            logger.error(
                f"Błąd dekodowania JSON w {metadata_path} podczas usuwania wpisu dla '{relative_archive_path}'. Nie można kontynuować.",
                exc_info=True,
            )
            return False  # Nie można bezpiecznie zmodyfikować uszkodzonego pliku
        except Exception as e_load:
            logger.error(
                f"Nieoczekiwany błąd wczytywania {metadata_path} podczas usuwania wpisu: {e_load}",
                exc_info=True,
            )
            return False

        if (
            "file_pairs" in current_metadata
            and isinstance(current_metadata.get("file_pairs"), dict)
            and relative_archive_path in current_metadata["file_pairs"]
        ):
            del current_metadata["file_pairs"][relative_archive_path]
            logger.info(
                f"Usunięto metadane dla pliku: {relative_archive_path} z {metadata_path}"
            )

            # Zapisz zmiany (używając logiki z save_metadata, ale uproszczonej, bo modyfikujemy tylko jeden klucz)
            # Bezpieczniej jest zapisać cały obiekt current_metadata.

            temp_file_path = ""  # Inicjalizacja zmiennej
            metadata_dir = os.path.dirname(metadata_path)
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    delete=False,
                    encoding="utf-8",
                    dir=metadata_dir,
                    suffix=".tmp",
                ) as temp_file:
                    json.dump(current_metadata, temp_file, ensure_ascii=False, indent=4)
                    temp_file_path = temp_file.name
                shutil.move(temp_file_path, metadata_path)
                logger.debug(
                    f"Pomyślnie zapisano zmiany w {metadata_path} po usunięciu wpisu."
                )
                return True
            except Exception as e_save:
                logger.error(
                    f"Błąd zapisu metadanych po usunięciu wpisu dla '{relative_archive_path}': {e_save}",
                    exc_info=True,
                )
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.remove(temp_file_path)
                        logger.debug(
                            f"Usunięto tymczasowy plik {temp_file_path} po błędzie zapisu."
                        )
                    except OSError as remove_err:
                        logger.error(
                            f"Nie można usunąć tymczasowego pliku {temp_file_path}: {remove_err}",
                            exc_info=True,
                        )
                return False
        else:
            logger.debug(
                f"Brak metadanych do usunięcia dla pliku: {relative_archive_path} w {metadata_path}"
            )
            return True  # Nic do zrobienia, więc sukces
    except (
        Timeout
    ):  # Ten wyjątek nie powinien wystąpić, jeśli FileLock jest zakomentowany
        logger.error(
            f"Timeout podczas próby usunięcia metadanych dla {relative_archive_path}.",
            exc_info=True,
        )
        return False
    except Exception as e:
        logger.error(
            f"Błąd podczas usuwania metadanych dla {relative_archive_path}: {e}",
            exc_info=True,
        )
        return False


def get_metadata_for_relative_path(
    working_directory: str, relative_archive_path: str
) -> Optional[Dict[str, Any]]:
    """
    Legacy function: Use MetadataManager.get_instance(dir).get_metadata_for_relative_path()
    Maintained for backward compatibility.
    """
    metadata = load_metadata(
        working_directory
    )  # load_metadata obsługuje logowanie błędów
    if (
        metadata
        and "file_pairs" in metadata
        and isinstance(metadata.get("file_pairs"), dict)
    ):
        return metadata["file_pairs"].get(relative_archive_path)
    elif not metadata:
        logger.debug(
            f"Nie udało się wczytać metadanych dla katalogu '{working_directory}' przy próbie pobrania dla '{relative_archive_path}'."
        )
    else:  # metadata istnieje, ale brakuje 'file_pairs' lub ma zły typ
        logger.debug(
            f"Klucz 'file_pairs' nie istnieje lub ma nieprawidłowy typ w metadanych dla '{working_directory}' przy próbie pobrania dla '{relative_archive_path}'."
        )
    return None
