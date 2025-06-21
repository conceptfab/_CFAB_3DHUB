"""
Komponent walidacji metadanych CFAB_3DHUB.
🚀 ETAP 3: Refaktoryzacja MetadataManager - walidacja struktury
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class MetadataValidator:
    """
    Walidacja struktury metadanych.
    Sprawdza poprawność struktury i typów danych w metadanych.
    """

    @staticmethod
    def validate_metadata_structure(metadata: Dict[str, Any]) -> bool:
        """
        Sprawdza, czy struktura metadanych jest poprawna.

        Args:
            metadata (Dict[str, Any]): Słownik metadanych do sprawdzenia.

        Returns:
            bool: True jeśli struktura jest poprawna, False w przeciwnym razie.
        """
        try:
            # Sprawdzenie obecności wymaganych kluczy
            required_keys = [
                "file_pairs",
                "unpaired_archives",
                "unpaired_previews",
            ]
            for key in required_keys:
                if key not in metadata:
                    logger.warning(f"Brak wymaganego klucza '{key}' w metadanych.")
                    return False

            # Sprawdzenie opcjonalnego klucza
            if "has_special_folders" in metadata and not isinstance(
                metadata["has_special_folders"], bool
            ):
                logger.warning(
                    "Klucz 'has_special_folders' nie jest wartością logiczną (bool)."
                )
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
                # Specjalny klucz __metadata__ może zawierać inne dane
                if relative_path == "__metadata__":
                    if not isinstance(pair_metadata, dict):
                        logger.warning("Klucz '__metadata__' nie jest słownikiem.")
                        return False
                    continue

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
            logger.error(
                f"Błąd podczas walidacji struktury metadanych: {e}", exc_info=True
            )
            return False

    @staticmethod
    def validate_file_pair_metadata(pair_metadata: Dict[str, Any]) -> bool:
        """
        Waliduje metadane pojedynczej pary plików.

        Args:
            pair_metadata: Słownik metadanych pary plików

        Returns:
            bool: True jeśli metadane są poprawne
        """
        try:
            if not isinstance(pair_metadata, dict):
                logger.warning(f"Metadane pary nie są słownikiem: {pair_metadata}")
                return False

            # Sprawdzenie wymaganych kluczy
            if "stars" not in pair_metadata or "color_tag" not in pair_metadata:
                logger.warning(
                    "Metadane pary nie zawierają wymaganych kluczy 'stars' lub 'color_tag'."
                )
                return False

            # Sprawdzenie typów wartości
            if not isinstance(pair_metadata["stars"], int):
                logger.warning(
                    f"Wartość 'stars' nie jest liczbą całkowitą: {pair_metadata['stars']}"
                )
                return False

            if not (
                isinstance(pair_metadata["color_tag"], str)
                or pair_metadata["color_tag"] is None
            ):
                logger.warning(
                    f"Wartość 'color_tag' nie jest ciągiem znaków ani None: {pair_metadata['color_tag']}"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Błąd podczas walidacji metadanych pary: {e}", exc_info=True)
            return False
