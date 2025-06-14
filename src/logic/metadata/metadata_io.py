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
            with lock:

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

            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except OSError as e:
                    logger.warning(f"Could not cleanup temp file {temp_file_path}: {e}")

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
