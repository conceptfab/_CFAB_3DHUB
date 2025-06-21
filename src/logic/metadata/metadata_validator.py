"""
Komponent walidacji metadanych CFAB_3DHUB.
🚀 ETAP 4: Refaktoryzacja MetadataValidator - poprawki krytyczne
"""

import logging
import os
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MetadataValidator:
    """
    Walidacja struktury metadanych.
    Sprawdza poprawność struktury, typów danych i wartości w metadanych.
    """

    # Konfiguracja walidacji
    MAX_FILENAME_LENGTH = 255
    MAX_PATH_LENGTH = 4096
    MAX_STARS = 5
    MIN_STARS = 0

    # Niedozwolone znaki w nazwach plików (Windows + Unix)
    INVALID_CHARS = r'[<>:"/\\|?*\x00-\x1f]'

    # Cache dla wyników walidacji
    _validation_cache = {}

    @classmethod
    def _validate_stars_range(cls, stars: int, context: str = "") -> bool:
        """
        Waliduje zakres wartości gwiazdek (0-5).

        Args:
            stars: Wartość gwiazdek do sprawdzenia
            context: Kontekst dla logów

        Returns:
            bool: True jeśli wartość jest w prawidłowym zakresie
        """
        if not isinstance(stars, int):
            logger.debug(f"{context}Wartość 'stars' nie jest liczbą całkowitą: {stars}")
            return False

        if not cls.MIN_STARS <= stars <= cls.MAX_STARS:
            logger.debug(
                f"{context}Wartość 'stars' ({stars}) poza zakresem "
                f"[{cls.MIN_STARS}-{cls.MAX_STARS}]"
            )
            return False

        return True

    @classmethod
    def _validate_filename(cls, filename: str, context: str = "") -> bool:
        """
        Waliduje nazwę pliku pod kątem długości i znaków specjalnych.

        Args:
            filename: Nazwa pliku do sprawdzenia
            context: Kontekst dla logów

        Returns:
            bool: True jeśli nazwa jest prawidłowa
        """
        if not isinstance(filename, str):
            logger.debug(f"{context}Nazwa pliku nie jest ciągiem znaków: {filename}")
            return False

        if len(filename) > cls.MAX_FILENAME_LENGTH:
            logger.debug(
                f"{context}Nazwa pliku za długa ({len(filename)} > "
                f"{cls.MAX_FILENAME_LENGTH}): {filename}"
            )
            return False

        if re.search(cls.INVALID_CHARS, filename):
            logger.debug(f"{context}Nazwa pliku zawiera niedozwolone znaki: {filename}")
            return False

        return True

    @classmethod
    def _validate_file_path(cls, file_path: str, context: str = "") -> bool:
        """
        Waliduje ścieżkę pliku pod kątem długości.

        Args:
            file_path: Ścieżka pliku do sprawdzenia
            context: Kontekst dla logów

        Returns:
            bool: True jeśli ścieżka jest prawidłowa
        """
        if not isinstance(file_path, str):
            logger.debug(f"{context}Ścieżka pliku nie jest ciągiem znaków: {file_path}")
            return False

        if len(file_path) > cls.MAX_PATH_LENGTH:
            logger.debug(
                f"{context}Ścieżka pliku za długa ({len(file_path)} > "
                f"{cls.MAX_PATH_LENGTH}): {file_path}"
            )
            return False

        # Sprawdź każdy segment ścieżki
        for segment in file_path.split(os.sep):
            if segment and not cls._validate_filename(
                segment, f"{context}Segment '{segment}': "
            ):
                return False

        return True

    @classmethod
    def _validate_pair_metadata_structure(
        cls, pair_metadata: Dict[str, Any], context: str = ""
    ) -> bool:
        """
        Waliduje strukturę metadanych pojedynczej pary plików.

        Args:
            pair_metadata: Słownik metadanych pary plików
            context: Kontekst dla logów

        Returns:
            bool: True jeśli struktura jest prawidłowa
        """
        if not isinstance(pair_metadata, dict):
            logger.debug(f"{context}Metadane pary nie są słownikiem: {pair_metadata}")
            return False

        # Sprawdzenie wymaganych kluczy
        required_keys = ["stars", "color_tag"]
        for key in required_keys:
            if key not in pair_metadata:
                logger.debug(
                    f"{context}Metadane pary nie zawierają wymaganego klucza '{key}'"
                )
                return False

        # Sprawdzenie typów i wartości
        if not cls._validate_stars_range(
            pair_metadata["stars"], f"{context}Wartość 'stars': "
        ):
            return False

        if not (
            isinstance(pair_metadata["color_tag"], str)
            or pair_metadata["color_tag"] is None
        ):
            logger.debug(
                f"{context}Wartość 'color_tag' nie jest ciągiem znaków ani None: "
                f"{pair_metadata['color_tag']}"
            )
            return False

        return True

    @classmethod
    def _get_cache_key(cls, metadata: Dict[str, Any]) -> str:
        """
        Generuje klucz cache dla metadanych.

        Args:
            metadata: Metadane do cache'owania

        Returns:
            str: Klucz cache
        """
        # Używamy hash struktury dla cache'owania
        return str(hash(str(sorted(metadata.items()))))

    @classmethod
    def validate_metadata_structure(cls, metadata: Dict[str, Any]) -> bool:
        """
        Sprawdza, czy struktura metadanych jest poprawna.

        Args:
            metadata (Dict[str, Any]): Słownik metadanych do sprawdzenia.

        Returns:
            bool: True jeśli struktura jest poprawna, False w przeciwnym razie.
        """
        try:
            # Sprawdzenie cache
            cache_key = cls._get_cache_key(metadata)
            if cache_key in cls._validation_cache:
                logger.debug("Użyto cache'owanego wyniku walidacji")
                return cls._validation_cache[cache_key]

            # Sprawdzenie obecności wymaganych kluczy
            required_keys = [
                "file_pairs",
                "unpaired_archives",
                "unpaired_previews",
            ]
            for key in required_keys:
                if key not in metadata:
                    logger.debug(f"Brak wymaganego klucza '{key}' w metadanych")
                    cls._validation_cache[cache_key] = False
                    return False

            # Sprawdzenie opcjonalnego klucza
            if "has_special_folders" in metadata and not isinstance(
                metadata["has_special_folders"], bool
            ):
                logger.debug(
                    "Klucz 'has_special_folders' nie jest wartością logiczną (bool)"
                )
                cls._validation_cache[cache_key] = False
                return False

            # Sprawdzenie typów danych
            if not isinstance(metadata["file_pairs"], dict):
                logger.debug("Klucz 'file_pairs' nie jest słownikiem")
                cls._validation_cache[cache_key] = False
                return False

            if not isinstance(metadata["unpaired_archives"], list):
                logger.debug("Klucz 'unpaired_archives' nie jest listą")
                cls._validation_cache[cache_key] = False
                return False

            if not isinstance(metadata["unpaired_previews"], list):
                logger.debug("Klucz 'unpaired_previews' nie jest listą")
                cls._validation_cache[cache_key] = False
                return False

            # Sprawdzenie struktury file_pairs
            for relative_path, pair_metadata in metadata["file_pairs"].items():
                # Specjalny klucz __metadata__ może zawierać inne dane
                if relative_path == "__metadata__":
                    if not isinstance(pair_metadata, dict):
                        logger.debug("Klucz '__metadata__' nie jest słownikiem")
                        cls._validation_cache[cache_key] = False
                        return False
                    continue

                # Walidacja ścieżki pliku
                if not cls._validate_file_path(
                    relative_path, f"Ścieżka '{relative_path}': "
                ):
                    cls._validation_cache[cache_key] = False
                    return False

                # Walidacja struktury metadanych pary
                if not cls._validate_pair_metadata_structure(
                    pair_metadata, f"Para '{relative_path}': "
                ):
                    cls._validation_cache[cache_key] = False
                    return False

            # Walidacja list niepowiązanych plików
            for archive_path in metadata["unpaired_archives"]:
                if not cls._validate_file_path(
                    archive_path, f"Archiwum '{archive_path}': "
                ):
                    cls._validation_cache[cache_key] = False
                    return False

            for preview_path in metadata["unpaired_previews"]:
                if not cls._validate_file_path(
                    preview_path, f"Podgląd '{preview_path}': "
                ):
                    cls._validation_cache[cache_key] = False
                    return False

            logger.debug("Struktura metadanych jest poprawna")
            cls._validation_cache[cache_key] = True
            return True

        except Exception as e:
            logger.error(
                f"Błąd podczas walidacji struktury metadanych: {e}", exc_info=True
            )
            return False

    @classmethod
    def validate_file_pair_metadata(cls, pair_metadata: Dict[str, Any]) -> bool:
        """
        Waliduje metadane pojedynczej pary plików.

        Args:
            pair_metadata: Słownik metadanych pary plików

        Returns:
            bool: True jeśli metadane są poprawne
        """
        return cls._validate_pair_metadata_structure(pair_metadata, "Metadane pary: ")

    @classmethod
    def clear_cache(cls) -> None:
        """
        Czyści cache walidacji.
        """
        cls._validation_cache.clear()
        logger.debug("Cache walidacji został wyczyszczony")

    @classmethod
    def get_cache_stats(cls) -> Dict[str, int]:
        """
        Zwraca statystyki cache walidacji.

        Returns:
            Dict[str, int]: Statystyki cache
        """
        return {
            "cache_size": len(cls._validation_cache),
            "cache_hits": getattr(cls, "_cache_hits", 0),
            "cache_misses": getattr(cls, "_cache_misses", 0),
        }
