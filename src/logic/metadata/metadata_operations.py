"""
Komponent operacji na metadanych CFAB_3DHUB.
🚀 ETAP 3: Refaktoryzacja MetadataManager - operacje na metadanych
"""

import logging
import os
from typing import Any, Dict, List, Optional

# Import normalizacji ścieżek
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class MetadataOperations:
    """
    Operacje na metadanych.
    Obsługuje aplikowanie metadanych do par plików i inne operacje biznesowe.
    """

    def __init__(self, working_directory: str):
        """
        Inicjalizuje komponent operacji.

        Args:
            working_directory: Ścieżka do folderu roboczego
        """
        self.working_directory = normalize_path(working_directory)

    def apply_metadata_to_file_pairs(
        self, metadata: Dict[str, Any], file_pairs_list: List
    ) -> bool:
        """
        Aplikuje metadane do listy par plików.

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

            logger.debug(
                "Rozpoczynanie stosowania metadanych do %s par plików.",
                len(file_pairs_list),
            )
            applied_count = 0

            normalized_working_dir = normalize_path(self.working_directory)

            total_files = len(file_pairs_list)
            batch_size = 50

            for i, file_pair in enumerate(file_pairs_list):
                if i % batch_size == 0:
                    logger.debug(
                        "Przetwarzanie metadanych: %s/%s plików...",
                        i,
                        total_files,
                    )

                if not all(
                    hasattr(file_pair, attr)
                    for attr in [
                        "archive_path",
                        "get_stars",
                        "set_stars",
                        "get_color_tag",
                        "set_color_tag",
                        "get_base_name",
                    ]
                ):
                    logger.warning(
                        "Skipping file_pair with missing attributes: %s",
                        file_pair,
                    )
                    continue

                relative_archive_path = self.get_relative_path(
                    file_pair.archive_path, normalized_working_dir
                )
                if relative_archive_path is None:
                    logger.warning(
                        "Cannot get relative path for %s",
                        file_pair.archive_path,
                    )
                    continue

                if relative_archive_path in file_pairs_metadata:
                    pair_metadata = file_pairs_metadata[relative_archive_path]

                    if "stars" in pair_metadata:
                        try:
                            stars_value = int(pair_metadata["stars"])
                            file_pair.set_stars(stars_value)
                            logger.debug(
                                "Ustawiono %s gwiazdek dla %s",
                                stars_value,
                                relative_archive_path,
                            )
                        except (ValueError, TypeError) as e:
                            logger.warning(
                                "Invalid stars value for %s: %s - %s",
                                relative_archive_path,
                                pair_metadata["stars"],
                                e,
                            )

                    if "color_tag" in pair_metadata:
                        color_tag = pair_metadata["color_tag"]
                        file_pair.set_color_tag(color_tag)
                        logger.debug(
                            "Ustawiono tag koloru '%s' dla %s",
                            color_tag,
                            relative_archive_path,
                        )

                    applied_count += 1

            logger.debug(
                "Pomyślnie zastosowano metadane do %s/%s par plików.",
                applied_count,
                len(file_pairs_list),
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
        """
        special_folders = self.check_special_folders()
        special_folders_exist = len(special_folders) > 0

        file_pairs_metadata = {}
        for file_pair in file_pairs_list:
            if not all(
                hasattr(file_pair, attr)
                for attr in ["archive_path", "get_stars", "get_color_tag"]
            ):
                logger.warning(
                    "Pomijam parę plików z brakującymi atrybutami: %s",
                    file_pair,
                )
                continue

            relative_archive_path = self.get_relative_path(
                file_pair.archive_path, self.working_directory
            )
            if relative_archive_path is None:
                logger.warning(
                    "Nie można uzyskać ścieżki względnej dla %s",
                    file_pair.archive_path,
                )
                continue

            file_pairs_metadata[relative_archive_path] = {
                "stars": file_pair.get_stars(),
                "color_tag": file_pair.get_color_tag(),
            }

        metadata_to_save = {
            "file_pairs": file_pairs_metadata,
            "unpaired_archives": unpaired_archives,
            "unpaired_previews": unpaired_previews,
            "has_special_folders": special_folders_exist,
            "special_folders": special_folders,
        }

        logger.debug(
            "Przygotowano metadane do zapisu. has_special_folders: %s, folders: %s",
            special_folders_exist,
            special_folders,
        )

        return metadata_to_save

    def prepare_file_pairs_metadata(
        self, file_pairs_list: List
    ) -> Dict[str, Dict[str, Any]]:
        """
        Przygotowuje metadane par plików do zapisu.

        Args:
            file_pairs_list: Lista obiektów FilePair

        Returns:
            Dict z metadanymi par plików
        """
        file_pairs_metadata = {}

        for file_pair in file_pairs_list:
            if not all(
                hasattr(file_pair, attr)
                for attr in ["archive_path", "get_stars", "get_color_tag"]
            ):
                logger.warning(
                    "Skipping file_pair with missing attributes: %s",
                    file_pair,
                )
                continue

            relative_archive_path = self.get_relative_path(
                file_pair.archive_path, self.working_directory
            )
            if relative_archive_path is None:
                logger.warning(
                    "Cannot get relative path for %s",
                    file_pair.archive_path,
                )
                continue

            file_pairs_metadata[relative_archive_path] = {
                "stars": file_pair.get_stars(),
                "color_tag": file_pair.get_color_tag(),
            }

        special_folders = self.check_special_folders()

        file_pairs_metadata["__metadata__"] = {
            "has_special_folders": len(special_folders) > 0,
            "special_folders": special_folders,
        }

        logger.info(
            "Dodano informację o specjalnych folderach do metadanych: %s",
            special_folders,
        )

        return file_pairs_metadata

    def check_special_folders(self) -> List[str]:
        """
        Sprawdza czy w katalogu roboczym znajdują się specjalne foldery.

        Returns:
            Lista nazw znalezionych specjalnych folderów
        """
        from src.models.special_folder import SpecialFolder

        special_folders = []
        try:
            logger.debug("Sprawdzam specjalne foldery w: %s", self.working_directory)

            if not os.path.exists(self.working_directory):
                logger.error("Katalog roboczy nie istnieje: %s", self.working_directory)
                return special_folders

            if not os.path.isdir(self.working_directory):
                logger.error("Ścieżka nie jest katalogiem: %s", self.working_directory)
                return special_folders

            try:
                dir_contents = os.listdir(self.working_directory)
                logger.debug(
                    "Zawartość katalogu (%s elementów): %s",
                    len(dir_contents),
                    self.working_directory,
                )
                for item in dir_contents[:10]:
                    item_path = os.path.join(self.working_directory, item)
                    is_dir = os.path.isdir(item_path)
                    logger.debug("  - %s %s", item, "[FOLDER]" if is_dir else "[PLIK]")
                if len(dir_contents) > 10:
                    logger.debug(
                        "  ... i %s więcej elementów",
                        len(dir_contents) - 10,
                    )
            except Exception as e:
                logger.error("Błąd listowania katalogu: %s", e)

            for item in os.listdir(self.working_directory):
                item_path = os.path.join(self.working_directory, item)
                if os.path.isdir(item_path):
                    logger.debug("Sprawdzam folder: %s", item)
                    if SpecialFolder.is_special_folder(item):
                        special_folders.append(item)
                        logger.debug(
                            "Znaleziono specjalny folder w metadanych: %s",
                            item,
                        )

            logger.debug(
                "Znaleziono %s specjalnych folderów: %s",
                len(special_folders),
                special_folders,
            )

        except (PermissionError, OSError) as e:
            logger.error(
                "Błąd skanowania folderów specjalnych w %s: %s",
                self.working_directory,
                e,
            )

        return special_folders

    def prepare_unpaired_files_metadata(
        self, unpaired_archives: List[str], unpaired_previews: List[str]
    ) -> tuple[List[str], List[str]]:
        """
        Przygotowuje metadane niesparowanych plików do zapisu.

        Args:
            unpaired_archives: Lista ścieżek archiwów
            unpaired_previews: Lista ścieżek podglądów

        Returns:
            Tuple z listami względnych ścieżek
        """
        unpaired_archives_rel = []
        for p in unpaired_archives:
            rel_p = self.get_relative_path(p, self.working_directory)
            if rel_p is not None:
                unpaired_archives_rel.append(rel_p)

        unpaired_previews_rel = []
        for p in unpaired_previews:
            rel_p = self.get_relative_path(p, self.working_directory)
            if rel_p is not None:
                unpaired_previews_rel.append(rel_p)

        return unpaired_archives_rel, unpaired_previews_rel

    def get_relative_path(self, absolute_path: str, base_path: str) -> Optional[str]:
        """
        Konwertuje ścieżkę absolutną na względną względem podanej ścieżki bazowej.

        Args:
            absolute_path: Ścieżka absolutna do konwersji
            base_path: Ścieżka bazowa

        Returns:
            Ścieżka względna lub None w przypadku błędu
        """
        try:
            norm_abs_path = normalize_path(absolute_path)
            norm_base_path = normalize_path(base_path)

            if not os.path.isabs(norm_abs_path):
                logger.warning(
                    "Ścieżka do konwersji nie jest absolutna: %s",
                    norm_abs_path,
                )
                norm_abs_path = normalize_path(os.path.abspath(norm_abs_path))

            if not os.path.isabs(norm_base_path):
                logger.warning("Ścieżka bazowa nie jest absolutna: %s", norm_base_path)
                norm_base_path = normalize_path(os.path.abspath(norm_base_path))

            if os.name == "nt":
                abs_drive = os.path.splitdrive(norm_abs_path)[0].lower()
                base_drive = os.path.splitdrive(norm_base_path)[0].lower()
                if abs_drive and base_drive and abs_drive != base_drive:
                    logger.error(
                        "Nie można utworzyć ścieżki względnej: ścieżki są na "
                        "różnych dyskach. Ścieżka: %s, Baza: %s",
                        norm_abs_path,
                        norm_base_path,
                    )
                    return None

            relative_path = os.path.relpath(norm_abs_path, norm_base_path)

            relative_path_normalized = normalize_path(relative_path)

            logger.debug(
                "Pomyślnie skonwertowano ścieżkę: %s -> %s (względem: %s)",
                norm_abs_path,
                relative_path_normalized,
                norm_base_path,
            )
            return relative_path_normalized

        except Exception as e:
            logger.error(
                "Błąd podczas konwersji ścieżki %s względem %s: %s",
                absolute_path,
                base_path,
                e,
                exc_info=True,
            )
            return None

    def get_absolute_path(self, relative_path: str, base_path: str) -> Optional[str]:
        """
        Konwertuje ścieżkę względną na absolutną względem podanej ścieżki bazowej.

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
                logger.warning(
                    "Ścieżka bazowa nie jest absolutna: %s. Konwertuję.",
                    norm_base_path,
                )
                norm_base_path = normalize_path(os.path.abspath(norm_base_path))

            absolute_path = os.path.join(norm_base_path, norm_rel_path)

            absolute_path_normalized = normalize_path(absolute_path)

            logger.debug(
                "Pomyślnie skonwertowano ścieżkę: %s -> %s (względem: %s)",
                norm_rel_path,
                absolute_path_normalized,
                norm_base_path,
            )
            return absolute_path_normalized

        except Exception as e:
            logger.error(
                "Błąd podczas konwersji ścieżki %s względem %s: %s",
                relative_path,
                base_path,
                e,
                exc_info=True,
            )
            return None

    def get_special_folders(self, directory_path: str) -> List[str]:
        """
        Pobiera listę specjalnych folderów z metadanych dla danego katalogu.

        Args:
            directory_path: Ścieżka do katalogu, dla którego chcemy pobrać
                            specjalne foldery

        Returns:
            Lista nazw specjalnych folderów lub pusta lista jeśli nie znaleziono
        """
        metadata = self._load_metadata(directory_path)
        if not metadata:
            logging.debug("Brak metadanych dla katalogu: %s", directory_path)
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
                        logging.info(
                            "Znaleziono %s specjalnych folderów w metadanych",
                            len(special_folders),
                        )
                        return special_folders

        return []

    def save_special_folders(
        self, directory_path: str, special_folders: List[str]
    ) -> bool:
        """
        Zapisuje listę specjalnych folderów do metadanych.

        Args:
            directory_path: Ścieżka do katalogu, dla którego zapisujemy
                            specjalne foldery
            special_folders: Lista nazw specjalnych folderów

        Returns:
            True jeśli zapis się powiódł, False w przeciwnym przypadku
        """
        metadata = self._load_metadata(directory_path)
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

        return self._save_metadata(directory_path, metadata)

    def add_special_folder(self, directory_path: str, folder_name: str) -> bool:
        """
        Dodaje specjalny folder do metadanych dla danego katalogu.

        Args:
            directory_path: Ścieżka do katalogu
            folder_name: Nazwa specjalnego folderu do dodania

        Returns:
            True jeśli operacja się powiodła, False w przeciwnym przypadku
        """
        special_folders = self.get_special_folders(directory_path)
        if folder_name not in special_folders:
            special_folders.append(folder_name)
            return self.save_special_folders(directory_path, special_folders)
        return True

    def remove_special_folder(self, directory_path: str, folder_name: str) -> bool:
        """
        Usuwa specjalny folder z metadanych dla danego katalogu.

        Args:
            directory_path: Ścieżka do katalogu
            folder_name: Nazwa specjalnego folderu do usunięcia

        Returns:
            True jeśli operacja się powiodła, False w przeciwnym przypadku
        """
        special_folders = self.get_special_folders(directory_path)
        if folder_name in special_folders:
            special_folders.remove(folder_name)
            return self.save_special_folders(directory_path, special_folders)
        return True

    def _load_metadata(self, directory_path: str) -> Optional[Dict[str, Any]]:
        """
        Prywatna metoda do ładowania metadanych.
        """
        from src.logic.metadata.metadata_manager import MetadataManager

        metadata_manager = MetadataManager.get_instance(directory_path)
        return metadata_manager.load_metadata()

    def _save_metadata(self, directory_path: str, metadata: Dict[str, Any]) -> bool:
        """
        Prywatna metoda do zapisywania metadanych.
        """
        from src.logic.metadata.metadata_manager import MetadataManager

        metadata_manager = MetadataManager.get_instance(directory_path)
        return metadata_manager.save_metadata(metadata)
