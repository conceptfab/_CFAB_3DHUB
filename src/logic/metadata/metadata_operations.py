"""
Komponent operacji na metadanych CFAB_3DHUB.
🚀 ETAP 3: Refaktoryzacja MetadataManager - operacje na metadanych
"""

import logging
import os
import time
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
            if not metadata or "file_pairs" not in metadata or not metadata["file_pairs"]:
                logger.debug(
                    "Brak metadanych par plików do zastosowania lub błąd wczytywania. "
                    f"(Katalog: {self.working_directory})"
                )
                return True  # Traktujemy to jako "sukces" w sensie braku danych do przetworzenia

            file_pairs_metadata = metadata["file_pairs"]

            logger.debug(
                f"Rozpoczynanie stosowania metadanych do {len(file_pairs_list)} par plików."
            )
            applied_count = 0

            # OPTYMALIZACJA: Cache dla normalizacji ścieżek - unikaj powtarzania
            normalized_working_dir = normalize_path(self.working_directory)

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
                        f"Skipping file_pair with missing attributes: {file_pair}"
                    )
                    continue

                # Pobierz ścieżkę względną dla pliku archiwum
                relative_archive_path = self.get_relative_path(
                    file_pair.archive_path, normalized_working_dir
                )
                if relative_archive_path is None:
                    logger.warning(
                        f"Cannot get relative path for {file_pair.archive_path}"
                    )
                    continue

                # Sprawdź, czy istnieją metadane dla tej pary
                if relative_archive_path in file_pairs_metadata:
                    pair_metadata = file_pairs_metadata[relative_archive_path]

                    # Aplikuj gwiazdki
                    if "stars" in pair_metadata:
                        try:
                            stars_value = int(pair_metadata["stars"])
                            file_pair.set_stars(stars_value)
                            logger.debug(
                                f"Ustawiono {stars_value} gwiazdek dla {relative_archive_path}"
                            )
                        except (ValueError, TypeError) as e:
                            logger.warning(
                                f"Invalid stars value for {relative_archive_path}: {pair_metadata['stars']} - {e}"
                            )

                    # Aplikuj tag koloru
                    if "color_tag" in pair_metadata:
                        color_tag = pair_metadata["color_tag"]
                        file_pair.set_color_tag(color_tag)
                        logger.debug(
                            f"Ustawiono tag koloru '{color_tag}' dla {relative_archive_path}"
                        )

                    applied_count += 1

            logger.debug(
                f"Pomyślnie zastosowano metadane do {applied_count}/{len(file_pairs_list)} par plików."
            )
            return True

        except Exception as e:
            logger.error(f"Błąd stosowania metadanych do par plików: {e}", exc_info=True)
            return False

    def prepare_file_pairs_metadata(self, file_pairs_list: List) -> Dict[str, Dict[str, Any]]:
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
                    f"Skipping file_pair with missing attributes: {file_pair}"
                )
                continue

            relative_archive_path = self.get_relative_path(
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

        return file_pairs_metadata

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