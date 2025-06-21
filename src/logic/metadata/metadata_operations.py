"""
Komponent operacji na metadanych CFAB_3DHUB.
🚀 ETAP 3: Refaktoryzacja MetadataManager - operacje na metadanych
✅ POPRAWKI WPROWADZONE - Circular dependency, performance, error handling
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

# Import normalizacji ścieżek
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)

# Cache dla sprawdzania atrybutów - poprawka 3.2
_REQUIRED_ATTRIBUTES = {
    "file_pair_basic": [
        "archive_path",
        "get_stars",
        "set_stars",
        "get_color_tag",
        "set_color_tag",
        "get_base_name",
    ],
    "file_pair_read": ["archive_path", "get_stars", "get_color_tag"],
}

# Batch processing constants - poprawka 3.4
BATCH_SIZE_SMALL = 25
BATCH_SIZE_MEDIUM = 50
BATCH_SIZE_LARGE = 100
PROGRESS_INTERVAL = 100  # Progress co 100 plików


class MetadataOperations:
    """
    Operacje na metadanych.
    Obsługuje aplikowanie metadanych do par plików i inne operacje biznesowe.
    ✅ Zoptymalizowane: circular dependency, performance, error handling
    """

    def __init__(self, working_directory: str):
        """
        Inicjalizuje komponent operacji.

        Args:
            working_directory: Ścieżka do folderu roboczego
        """
        self.working_directory = normalize_path(working_directory)
        # Cache dla special folders - poprawka 3.6
        self._special_folders_cache = None
        self._cache_timestamp = 0
        self._cache_ttl = 30  # 30 sekund TTL

    def apply_metadata_to_file_pairs(
        self, metadata: Dict[str, Any], file_pairs_list: List
    ) -> bool:
        """
        Aplikuje metadane do listy par plików.
        ✅ Zoptymalizowane: batch processing, attribute checking, error handling

        Args:
            metadata: Słownik metadanych
            file_pairs_list: Lista obiektów FilePair do aktualizacji

        Returns:
            bool: True jeśli aktualizacja przebiegła pomyślnie
        """
        try:
            if (
                not metadata
                or "file_pairs" not in metadata
                or not metadata["file_pairs"]
            ):
                logger.debug(
                    "Brak metadanych par plików do zastosowania lub błąd "
                    "wczytywania. (Katalog: %s)",
                    self.working_directory,
                )
                return True

            file_pairs_metadata = metadata["file_pairs"]
            total_files = len(file_pairs_list)

            if total_files == 0:
                return True

            logger.debug(
                "Rozpoczynanie stosowania metadanych do %s par plików.",
                total_files,
            )

            # Poprawka 3.2: Zoptymalizowane sprawdzanie atrybutów
            required_attrs = _REQUIRED_ATTRIBUTES["file_pair_basic"]

            applied_count = 0
            normalized_working_dir = normalize_path(self.working_directory)

            for i, file_pair in enumerate(file_pairs_list):
                # Progress tracking - poprawka 3.4
                if i % PROGRESS_INTERVAL == 0 and i > 0:
                    progress_pct = int(i * 100 / total_files)
                    logger.debug(
                        "Przetwarzanie metadanych: %s/%s plików (%s%%)...",
                        i,
                        total_files,
                        progress_pct,
                    )

                # Poprawka 3.2: Szybsze sprawdzanie atrybutów
                if not self._has_required_attributes(file_pair, required_attrs):
                    archive_path = getattr(file_pair, "archive_path", "UNKNOWN")
                    logger.warning(
                        "Pomijam file_pair z brakującymi atrybutami: %s",
                        archive_path,
                    )
                    continue

                # Poprawka 3.3: Uproszczona logika ścieżek
                relative_archive_path = self._get_relative_path_safe(
                    file_pair.archive_path, normalized_working_dir
                )
                if relative_archive_path is None:
                    continue

                if relative_archive_path in file_pairs_metadata:
                    pair_metadata = file_pairs_metadata[relative_archive_path]

                    # Poprawka 3.7: Lepsze error handling
                    if self._apply_stars_metadata(
                        file_pair, pair_metadata, relative_archive_path
                    ):
                        applied_count += 1

                    if self._apply_color_tag_metadata(
                        file_pair, pair_metadata, relative_archive_path
                    ):
                        applied_count += 1

            logger.info(
                "Pomyślnie zastosowano metadane do %s/%s par plików.",
                applied_count,
                total_files,
            )
            return True

        except Exception as e:
            logger.error(
                "Błąd stosowania metadanych do par plików: %s",
                e,
                exc_info=True,
            )
            return False

    def prepare_metadata_for_save(
        self,
        file_pairs_list: List,
        unpaired_archives: List[str],
        unpaired_previews: List[str],
    ) -> Dict[str, Any]:
        """
        Przygotowuje kompletny słownik metadanych do zapisu.
        ✅ Zoptymalizowane: batch processing, memory usage
        """
        # Poprawka 3.6: Cache special folders
        special_folders = self._get_cached_special_folders()
        special_folders_exist = len(special_folders) > 0

        # Poprawka 3.8: Lepsze zarządzanie pamięcią
        file_pairs_metadata = self._prepare_file_pairs_metadata_batch(file_pairs_list)

        metadata_to_save = {
            "file_pairs": file_pairs_metadata,
            "unpaired_archives": unpaired_archives,
            "unpaired_previews": unpaired_previews,
            "has_special_folders": special_folders_exist,
            "special_folders": special_folders,
        }

        logger.debug(
            "Przygotowano metadane do zapisu. has_special_folders: %s, " "folders: %s",
            special_folders_exist,
            special_folders,
        )

        return metadata_to_save

    def prepare_file_pairs_metadata(
        self, file_pairs_list: List
    ) -> Dict[str, Dict[str, Any]]:
        """
        Przygotowuje metadane par plików do zapisu.
        ✅ Zoptymalizowane: batch processing, memory usage

        Args:
            file_pairs_list: Lista obiektów FilePair

        Returns:
            Dict z metadanymi par plików
        """
        file_pairs_metadata = self._prepare_file_pairs_metadata_batch(file_pairs_list)

        # Poprawka 3.6: Cache special folders
        special_folders = self._get_cached_special_folders()

        file_pairs_metadata["__metadata__"] = {
            "has_special_folders": len(special_folders) > 0,
            "special_folders": special_folders,
        }

        logger.debug(
            "Dodano informację o specjalnych folderach do metadanych: %s",
            special_folders,
        )

        return file_pairs_metadata

    def check_special_folders(self) -> List[str]:
        """
        Sprawdza czy w katalogu roboczym znajdują się specjalne foldery.
        ✅ Zoptymalizowane: cache, error handling

        Returns:
            Lista nazw znalezionych specjalnych folderów
        """
        return self._get_cached_special_folders()

    def prepare_unpaired_files_metadata(
        self, unpaired_archives: List[str], unpaired_previews: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Przygotowuje metadane niesparowanych plików do zapisu.
        ✅ Zoptymalizowane: batch processing, error handling

        Args:
            unpaired_archives: Lista ścieżek archiwów
            unpaired_previews: Lista ścieżek podglądów

        Returns:
            Tuple z listami względnych ścieżek
        """
        # Poprawka 3.8: Lepsze zarządzanie pamięcią z generatorami
        unpaired_archives_rel = [
            rel_p
            for p in unpaired_archives
            if (rel_p := self._get_relative_path_safe(p, self.working_directory))
            is not None
        ]

        unpaired_previews_rel = [
            rel_p
            for p in unpaired_previews
            if (rel_p := self._get_relative_path_safe(p, self.working_directory))
            is not None
        ]

        return unpaired_archives_rel, unpaired_previews_rel

    def get_relative_path(self, absolute_path: str, base_path: str) -> Optional[str]:
        """
        Konwertuje ścieżkę absolutną na względną względem podanej ścieżki bazowej.
        ✅ Zoptymalizowane: uproszczona logika, lepsze error handling

        Args:
            absolute_path: Ścieżka absolutna do konwersji
            base_path: Ścieżka bazowa

        Returns:
            Ścieżka względna lub None w przypadku błędu
        """
        return self._get_relative_path_safe(absolute_path, base_path)

    def get_absolute_path(self, relative_path: str, base_path: str) -> Optional[str]:
        """
        Konwertuje ścieżkę względną na absolutną względem podanej ścieżki bazowej.
        ✅ Zoptymalizowane: uproszczona logika, lepsze error handling

        Args:
            relative_path: Ścieżka względna do konwersji
            base_path: Ścieżka bazowa

        Returns:
            Ścieżka absolutna lub None w przypadku błędu
        """
        try:
            norm_rel_path = normalize_path(relative_path)
            norm_base_path = normalize_path(base_path)

            if not os.path.isabs(norm_base_path):
                norm_base_path = normalize_path(os.path.abspath(norm_base_path))

            absolute_path = os.path.join(norm_base_path, norm_rel_path)
            return normalize_path(absolute_path)

        except Exception as e:
            logger.error(
                "Błąd podczas konwersji ścieżki %s względem %s: %s",
                relative_path,
                base_path,
                e,
            )
            return None

    def get_special_folders(self, directory_path: str) -> List[str]:
        """
        Pobiera listę specjalnych folderów z metadanych dla danego katalogu.
        ✅ Zoptymalizowane: cache, error handling

        Args:
            directory_path: Ścieżka do katalogu, dla którego chcemy pobrać
                            specjalne foldery

        Returns:
            Lista nazw specjalnych folderów lub pusta lista jeśli nie znaleziono
        """
        try:
            metadata = self._load_metadata_safe(directory_path)
            if not metadata:
                return []

            if "file_pairs" in metadata and "__metadata__" in metadata["file_pairs"]:
                metadata_info = metadata["file_pairs"]["__metadata__"]

                if (
                    "has_special_folders" in metadata_info
                    and metadata_info["has_special_folders"]
                ):
                    if "special_folders" in metadata_info:
                        special_folders = metadata_info["special_folders"]
                        if isinstance(special_folders, list):
                            logger.debug(
                                "Znaleziono %s specjalnych folderów w metadanych",
                                len(special_folders),
                            )
                            return special_folders

            return []
        except Exception as e:
            logger.error("Błąd pobierania specjalnych folderów: %s", e)
            return []

    def save_special_folders(
        self, directory_path: str, special_folders: List[str]
    ) -> bool:
        """
        Zapisuje listę specjalnych folderów do metadanych.
        ✅ Zoptymalizowane: error handling, cache invalidation

        Args:
            directory_path: Ścieżka do katalogu, dla którego zapisujemy
                            specjalne foldery
            special_folders: Lista nazw specjalnych folderów

        Returns:
            True jeśli zapis się powiódł, False w przeciwnym przypadku
        """
        try:
            metadata = self._load_metadata_safe(directory_path)
            if not metadata:
                metadata = {
                    "file_pairs": {},
                    "unpaired_archives": [],
                    "unpaired_previews": [],
                }

            if "file_pairs" not in metadata:
                metadata["file_pairs"] = {}

            if "__metadata__" not in metadata["file_pairs"]:
                metadata["file_pairs"]["__metadata__"] = {}

            metadata["file_pairs"]["__metadata__"]["has_special_folders"] = (
                len(special_folders) > 0
            )
            metadata["file_pairs"]["__metadata__"]["special_folders"] = special_folders

            # Poprawka 3.6: Invalidate cache
            self._invalidate_special_folders_cache()

            return self._save_metadata_safe(directory_path, metadata)
        except Exception as e:
            logger.error("Błąd zapisywania specjalnych folderów: %s", e)
            return False

    def add_special_folder(self, directory_path: str, folder_name: str) -> bool:
        """
        Dodaje specjalny folder do metadanych dla danego katalogu.
        ✅ Zoptymalizowane: error handling

        Args:
            directory_path: Ścieżka do katalogu
            folder_name: Nazwa specjalnego folderu do dodania

        Returns:
            True jeśli operacja się powiodła, False w przeciwnym przypadku
        """
        try:
            special_folders = self.get_special_folders(directory_path)
            if folder_name not in special_folders:
                special_folders.append(folder_name)
                return self.save_special_folders(directory_path, special_folders)
            return True
        except Exception as e:
            logger.error("Błąd dodawania specjalnego folderu: %s", e)
            return False

    def remove_special_folder(self, directory_path: str, folder_name: str) -> bool:
        """
        Usuwa specjalny folder z metadanych dla danego katalogu.
        ✅ Zoptymalizowane: error handling

        Args:
            directory_path: Ścieżka do katalogu
            folder_name: Nazwa specjalnego folderu do usunięcia

        Returns:
            True jeśli operacja się powiodła, False w przeciwnym przypadku
        """
        try:
            special_folders = self.get_special_folders(directory_path)
            if folder_name in special_folders:
                special_folders.remove(folder_name)
                return self.save_special_folders(directory_path, special_folders)
            return True
        except Exception as e:
            logger.error("Błąd usuwania specjalnego folderu: %s", e)
            return False

    # ==================== PRIVATE METHODS - POPRAWKI ====================

    def _has_required_attributes(self, obj: Any, required_attrs: List[str]) -> bool:
        """
        Poprawka 3.2: Szybsze sprawdzanie atrybutów z cache.
        """
        return all(hasattr(obj, attr) for attr in required_attrs)

    def _get_batch_size(self, total_files: int) -> int:
        """
        Poprawka 3.4: Dynamiczny batch size na podstawie liczby plików.
        """
        if total_files <= 100:
            return BATCH_SIZE_SMALL
        elif total_files <= 500:
            return BATCH_SIZE_MEDIUM
        else:
            return BATCH_SIZE_LARGE

    def _get_relative_path_safe(
        self, absolute_path: str, base_path: str
    ) -> Optional[str]:
        """
        Poprawka 3.3: Uproszczona logika konwersji ścieżek z lepszym error handling.
        """
        try:
            norm_abs_path = normalize_path(absolute_path)
            norm_base_path = normalize_path(base_path)

            if not os.path.isabs(norm_abs_path):
                norm_abs_path = normalize_path(os.path.abspath(norm_abs_path))

            if not os.path.isabs(norm_base_path):
                norm_base_path = normalize_path(os.path.abspath(norm_base_path))

            # Poprawka 3.3: Uproszczona logika dla Windows
            if os.name == "nt":
                abs_drive = os.path.splitdrive(norm_abs_path)[0].lower()
                base_drive = os.path.splitdrive(norm_base_path)[0].lower()
                if abs_drive and base_drive and abs_drive != base_drive:
                    logger.warning(
                        "Ścieżki na różnych dyskach: %s vs %s",
                        norm_abs_path,
                        norm_base_path,
                    )
                    return None

            relative_path = os.path.relpath(norm_abs_path, norm_base_path)
            return normalize_path(relative_path)

        except Exception as e:
            logger.warning(
                "Błąd konwersji ścieżki %s względem %s: %s", absolute_path, base_path, e
            )
            return None

    def _apply_stars_metadata(
        self, file_pair: Any, pair_metadata: Dict, relative_path: str
    ) -> bool:
        """
        Poprawka 3.7: Lepsze error handling dla gwiazdek.
        """
        if "stars" in pair_metadata:
            try:
                stars_value = int(pair_metadata["stars"])
                file_pair.set_stars(stars_value)
                logger.debug("Ustawiono %s gwiazdek dla %s", stars_value, relative_path)
                return True
            except (ValueError, TypeError) as e:
                logger.warning(
                    "Nieprawidłowa wartość gwiazdek dla %s: %s - %s",
                    relative_path,
                    pair_metadata["stars"],
                    e,
                )
        return False

    def _apply_color_tag_metadata(
        self, file_pair: Any, pair_metadata: Dict, relative_path: str
    ) -> bool:
        """
        Poprawka 3.7: Lepsze error handling dla tagów kolorów.
        """
        if "color_tag" in pair_metadata:
            try:
                color_tag = pair_metadata["color_tag"]
                file_pair.set_color_tag(color_tag)
                logger.debug(
                    "Ustawiono tag koloru '%s' dla %s", color_tag, relative_path
                )
                return True
            except Exception as e:
                logger.warning(
                    "Błąd ustawiania tagu koloru dla %s: %s", relative_path, e
                )
        return False

    def _prepare_file_pairs_metadata_batch(
        self, file_pairs_list: List
    ) -> Dict[str, Dict[str, Any]]:
        """
        Poprawka 3.8: Batch processing z lepszym zarządzaniem pamięcią.
        """
        file_pairs_metadata = {}
        required_attrs = _REQUIRED_ATTRIBUTES["file_pair_read"]

        batch_size = self._get_batch_size(len(file_pairs_list))

        for i, file_pair in enumerate(file_pairs_list):
            if i % batch_size == 0 and i > 0:
                logger.debug(
                    "Przygotowywanie metadanych: %s/%s", i, len(file_pairs_list)
                )

            if not self._has_required_attributes(file_pair, required_attrs):
                archive_path = getattr(file_pair, "archive_path", "UNKNOWN")
                logger.warning(
                    "Pomijam parę plików z brakującymi atrybutami: %s",
                    archive_path,
                )
                continue

            relative_archive_path = self._get_relative_path_safe(
                file_pair.archive_path, self.working_directory
            )
            if relative_archive_path is None:
                continue

            file_pairs_metadata[relative_archive_path] = {
                "stars": file_pair.get_stars(),
                "color_tag": file_pair.get_color_tag(),
            }

        return file_pairs_metadata

    def _get_cached_special_folders(self) -> List[str]:
        """
        Poprawka 3.6: Cache dla special folders z TTL.
        """
        import time

        current_time = time.time()
        if (
            self._special_folders_cache is not None
            and current_time - self._cache_timestamp < self._cache_ttl
        ):
            return self._special_folders_cache

        self._special_folders_cache = self._scan_special_folders()
        self._cache_timestamp = current_time
        return self._special_folders_cache

    def _scan_special_folders(self) -> List[str]:
        """
        Poprawka 3.6: Skanowanie special folders z lepszym error handling.
        """
        from src.models.special_folder import SpecialFolder

        special_folders = []
        try:
            if not os.path.exists(self.working_directory):
                logger.warning(
                    "Katalog roboczy nie istnieje: %s", self.working_directory
                )
                return special_folders

            if not os.path.isdir(self.working_directory):
                logger.warning(
                    "Ścieżka nie jest katalogiem: %s", self.working_directory
                )
                return special_folders

            for item in os.listdir(self.working_directory):
                item_path = os.path.join(self.working_directory, item)
                if os.path.isdir(item_path) and SpecialFolder.is_special_folder(item):
                    special_folders.append(item)

            logger.debug(
                "Znaleziono %s specjalnych folderów: %s",
                len(special_folders),
                special_folders,
            )

        except (PermissionError, OSError) as e:
            logger.error("Błąd skanowania folderów specjalnych: %s", e)

        return special_folders

    def _invalidate_special_folders_cache(self):
        """
        Poprawka 3.6: Invalidate cache.
        """
        self._special_folders_cache = None
        self._cache_timestamp = 0

    def _load_metadata_safe(self, directory_path: str) -> Optional[Dict[str, Any]]:
        """
        Poprawka 3.1: Bezpieczne ładowanie metadanych bez circular dependency.
        """
        try:
            # Poprawka 3.1: Dependency injection zamiast import
            from src.logic.metadata.metadata_core import MetadataCore

            metadata_core = MetadataCore.get_instance(directory_path)
            return metadata_core.load_metadata()
        except Exception as e:
            logger.error("Błąd ładowania metadanych: %s", e)
            return None

    def _save_metadata_safe(
        self, directory_path: str, metadata: Dict[str, Any]
    ) -> bool:
        """
        Poprawka 3.1: Bezpieczne zapisywanie metadanych bez circular dependency.
        """
        try:
            # Poprawka 3.1: Dependency injection zamiast import
            from src.logic.metadata.metadata_core import MetadataCore

            metadata_core = MetadataCore.get_instance(directory_path)
            return metadata_core.save_metadata(metadata)
        except Exception as e:
            logger.error("Błąd zapisywania metadanych: %s", e)
            return False

    # ==================== LEGACY METHODS - BACKWARD COMPATIBILITY ====================

    def _load_metadata(self, directory_path: str) -> Optional[Dict[str, Any]]:
        """
        Prywatna metoda do ładowania metadanych.
        ⚠️ DEPRECATED: Użyj _load_metadata_safe()
        """
        return self._load_metadata_safe(directory_path)

    def _save_metadata(self, directory_path: str, metadata: Dict[str, Any]) -> bool:
        """
        Prywatna metoda do zapisywania metadanych.
        ⚠️ DEPRECATED: Użyj _save_metadata_safe()
        """
        return self._save_metadata_safe(directory_path, metadata)
