"""
Komponent I/O metadanych CFAB_3DHUB.
🚀 ETAP 3: Refaktoryzacja MetadataManager - operacje I/O
"""

import json
import logging
import os
import shutil
import tempfile
from typing import Any, Dict

from filelock import FileLock, Timeout

# Import normalizacji ścieżek
from src.utils.path_utils import normalize_path

from .metadata_validator import MetadataValidator

# Stałe związane z metadanymi
METADATA_DIR_NAME = ".app_metadata"
METADATA_FILE_NAME = "metadata.json"
LOCK_FILE_NAME = "metadata.lock"
LOCK_TIMEOUT = 0.5  # Czas oczekiwania na blokadę w sekundach

logger = logging.getLogger(__name__)


class MetadataIO:
    """
    Operacje I/O metadanych.
    Obsługuje ładowanie i zapisywanie metadanych z/do pliku z atomic write i file locking.
    """

    def __init__(self, working_directory: str):
        """
        Inicjalizuje komponent I/O.

        Args:
            working_directory: Ścieżka do folderu roboczego
        """
        self.working_directory = normalize_path(working_directory)
        self.validator = MetadataValidator()

    def get_metadata_path(self) -> str:
        """Zwraca ścieżkę do pliku metadanych."""
        metadata_dir = os.path.join(self.working_directory, METADATA_DIR_NAME)
        return normalize_path(os.path.join(metadata_dir, METADATA_FILE_NAME))

    def get_lock_path(self) -> str:
        """Zwraca ścieżkę do pliku blokady."""
        metadata_dir = os.path.join(self.working_directory, METADATA_DIR_NAME)
        return normalize_path(os.path.join(metadata_dir, LOCK_FILE_NAME))

    def load_metadata_from_file(self) -> Dict[str, Any]:
        """
        Wczytuje metadane z pliku z obsługą blokady.

        Returns:
            Dict zawierający metadane lub domyślną strukturę w przypadku błędu
        """
        metadata_path = self.get_metadata_path()
        lock_path = self.get_lock_path()

        default_metadata = {
            "file_pairs": {},
            "unpaired_archives": [],
            "unpaired_previews": [],
            "has_special_folders": False,
        }

        logger.debug(f"Próba wczytania metadanych z: {metadata_path}")

        if not os.path.exists(metadata_path):
            logger.debug(
                f"Plik metadanych nie istnieje: {metadata_path}. Zwracam domyślne metadane."
            )
            return default_metadata

        lock = FileLock(lock_path, timeout=LOCK_TIMEOUT)

        try:
            with lock:
                with open(metadata_path, "r", encoding="utf-8") as file:
                    metadata = json.load(file)

                logger.debug(f"Pomyślnie wczytano metadane z {metadata_path}")

                # Walidacja struktury
                if not self.validator.validate_metadata_structure(metadata):
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

    def atomic_write(self, metadata_dict: Dict[str, Any]) -> bool:
        """
        Atomic write z file locking i proper error handling.

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
            logger.info(f"Próba zapisu metadanych do {metadata_path}")

            # Sprawdź czy mamy dane do zapisu
            if not metadata_dict:
                logger.error("Próba zapisu pustych metadanych!")
                return False

            # Sprawdź czy zawiera wymagane klucze
            required_keys = [
                "file_pairs",
                "unpaired_archives",
                "unpaired_previews",
                "has_special_folders",
            ]
            for key in required_keys:
                if key not in metadata_dict:
                    logger.error(
                        f"Brak wymaganego klucza '{key}' w metadanych do zapisu"
                    )
                    return False

            with lock:
                logger.info(f"Uzyskano blokadę dla {lock_path}")

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
                    logger.info(f"Zapisano tymczasowy plik: {temp_file_path}")

                # Atomic move (rename)
                if os.name == "nt":  # Windows
                    if os.path.exists(metadata_path):
                        logger.info(f"Zastępuję istniejący plik: {metadata_path}")
                        os.replace(temp_file_path, metadata_path)
                    else:
                        logger.info(f"Tworzę nowy plik: {metadata_path}")
                        shutil.move(temp_file_path, metadata_path)
                else:  # Unix-like
                    logger.info(f"Przenoszę plik: {temp_file_path} -> {metadata_path}")
                    os.rename(temp_file_path, metadata_path)

                # Sprawdź czy plik został faktycznie utworzony
                if os.path.exists(metadata_path):
                    file_size = os.path.getsize(metadata_path)
                    logger.info(
                        f"Pomyślnie zapisano metadane do {metadata_path} (rozmiar: {file_size} bajtów)"
                    )
                    return True
                else:
                    logger.error(
                        f"Plik metadanych nie istnieje po zapisie: {metadata_path}"
                    )
                    return False

        except Timeout:
            logger.error(
                f"Nie można uzyskać blokady dla {lock_path} w ciągu {LOCK_TIMEOUT}s"
            )
            return False
        except Exception as e:
            logger.error(f"Błąd zapisu metadanych: {e}", exc_info=True)
            return False
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.debug(f"Usunięto tymczasowy plik: {temp_file_path}")
                except OSError as e:
                    logger.warning(
                        f"Nie można usunąć tymczasowego pliku {temp_file_path}: {e}"
                    )

    def file_exists(self) -> bool:
        """
        Sprawdza czy plik metadanych istnieje.

        Returns:
            bool: True jeśli plik istnieje
        """
        return os.path.exists(self.get_metadata_path())

    def get_file_size(self) -> int:
        """
        Zwraca rozmiar pliku metadanych w bajtach.

        Returns:
            int: Rozmiar pliku lub 0 jeśli nie istnieje
        """
        metadata_path = self.get_metadata_path()
        try:
            if os.path.exists(metadata_path):
                return os.path.getsize(metadata_path)
            return 0
        except OSError:
            return 0

    def backup_metadata_file(self, backup_suffix: str = ".backup") -> bool:
        """
        Tworzy kopię zapasową pliku metadanych.

        Args:
            backup_suffix: Sufiks dla pliku kopii zapasowej

        Returns:
            bool: True jeśli kopia została utworzona pomyślnie
        """
        metadata_path = self.get_metadata_path()

        if not os.path.exists(metadata_path):
            logger.debug("Plik metadanych nie istnieje - brak potrzeby tworzenia kopii")
            return True

        backup_path = metadata_path + backup_suffix

        try:
            shutil.copy2(metadata_path, backup_path)
            logger.debug(f"Utworzono kopię zapasową: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Błąd tworzenia kopii zapasowej: {e}", exc_info=True)
            return False

    def _validate_metadata_structure(self, metadata_content: Dict) -> bool:
        """
        Sprawdza czy struktura metadanych jest poprawna.
        Akceptuje nową strukturę z kluczem __metadata__ dla specjalnych folderów.
        """
        # Sprawdzenie podstawowej struktury
        if not isinstance(metadata_content, dict):
            logging.error("Metadane nie są słownikiem.")
            return False

        # Sprawdzenie wymaganych kluczy głównych
        required_keys = ["file_pairs", "unpaired_archives", "unpaired_previews"]
        for key in required_keys:
            if key not in metadata_content:
                logging.error(f"Brak wymaganego klucza w metadanych: {key}")
                return False

        # Sprawdzenie struktury file_pairs
        file_pairs = metadata_content["file_pairs"]
        if not isinstance(file_pairs, dict):
            logging.error("file_pairs nie jest słownikiem.")
            return False

        # Sprawdzenie każdej pary plików (pomijając klucz __metadata__)
        for key, value in file_pairs.items():
            # Pomijamy specjalny klucz __metadata__ używany dla folderów specjalnych
            if key == "__metadata__":
                # Sprawdzenie struktury __metadata__
                if not isinstance(value, dict):
                    logging.warning("__metadata__ nie jest słownikiem.")
                    continue

                # Sprawdzenie kluczy w __metadata__
                if "has_special_folders" in value and not isinstance(
                    value["has_special_folders"], bool
                ):
                    logging.warning("has_special_folders nie jest wartością logiczną.")

                if "special_folders" in value and not isinstance(
                    value["special_folders"], list
                ):
                    logging.warning("special_folders nie jest listą.")

                continue  # Przejdź do następnego klucza

            # Sprawdzenie pozostałych kluczy (pary plików)
            if not isinstance(value, dict):
                logging.error(f"Wartość dla klucza {key} nie jest słownikiem.")
                return False

            # Sprawdzenie wymaganych pól dla par plików
            required_pair_fields = ["archive_path", "preview_path"]
            for field in required_pair_fields:
                if field not in value:
                    logging.error(f"Brak wymaganego pola {field} dla pary {key}.")
                    return False

            # Sprawdzenie opcjonalnych pól
            if "stars" in value and not isinstance(value["stars"], int):
                logging.warning(f"Pole stars dla pary {key} nie jest liczbą całkowitą.")

            # Sprawdzenie color_tag - może być None LUB string
            if (
                "color_tag" in value
                and value["color_tag"] is not None
                and not isinstance(value["color_tag"], str)
            ):
                logging.warning(
                    f"Pole color_tag dla pary {key} nie jest stringiem ani None."
                )

        # Sprawdzenie list niesparowanych plików
        for list_key in ["unpaired_archives", "unpaired_previews"]:
            if not isinstance(metadata_content[list_key], list):
                logging.error(f"{list_key} nie jest listą.")
                return False

        return True
