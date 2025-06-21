"""
Komponent I/O metadanych CFAB_3DHUB.
🚀 ETAP 3: Refaktoryzacja MetadataManager - operacje I/O
✅ POPRAWKI WPROWADZONE: Dynamic timeout, simplified atomic write, removed validation duplication
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

# Dynamic timeout based on file size and system load
BASE_LOCK_TIMEOUT = 1.0  # Podstawowy timeout w sekundach
MAX_LOCK_TIMEOUT = 5.0  # Maksymalny timeout w sekundach
FILE_SIZE_THRESHOLD = 1024 * 1024  # 1MB - próg dla zwiększenia timeout

logger = logging.getLogger(__name__)


class MetadataIO:
    """
    Operacje I/O metadanych.
    Obsługuje ładowanie i zapisywanie metadanych z/do pliku z atomic write i file locking.
    ✅ POPRAWKI: Dynamic timeout, simplified atomic write, better error handling
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

    def _calculate_dynamic_timeout(self) -> float:
        """
        Oblicza dynamic timeout na podstawie rozmiaru pliku i obciążenia systemu.

        Returns:
            float: Timeout w sekundach
        """
        metadata_path = self.get_metadata_path()

        try:
            if os.path.exists(metadata_path):
                file_size = os.path.getsize(metadata_path)
                # Zwiększ timeout dla dużych plików
                if file_size > FILE_SIZE_THRESHOLD:
                    timeout = min(BASE_LOCK_TIMEOUT * 2, MAX_LOCK_TIMEOUT)
                    logger.debug(
                        f"Duży plik ({file_size} bajtów) - timeout: {timeout}s"
                    )
                    return timeout
        except OSError:
            pass

        return BASE_LOCK_TIMEOUT

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

        # Dynamic timeout based on file size
        timeout = self._calculate_dynamic_timeout()
        lock = FileLock(lock_path, timeout=timeout)

        try:
            with lock:
                with open(metadata_path, "r", encoding="utf-8") as file:
                    metadata = json.load(file)

                logger.debug(f"Pomyślnie wczytano metadane z {metadata_path}")

                # Użyj tylko metadata_validator.py - usunięto duplikację
                if not self.validator.validate_metadata_structure(metadata):
                    logger.warning(
                        "Struktura metadanych jest niepoprawna. Zwracam domyślne metadane."
                    )
                    return default_metadata

                return metadata

        except Timeout:
            logger.error(
                f"Nie można uzyskać blokady pliku metadanych {lock_path} w ciągu {timeout}s podczas wczytywania.",
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
        ✅ POPRAWKA: Uproszczona logika atomic write z fallback

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

        # Dynamic timeout based on file size
        timeout = self._calculate_dynamic_timeout()
        lock = FileLock(lock_path, timeout=timeout)
        temp_file_path = None

        try:
            logger.debug(f"Próba zapisu metadanych do {metadata_path}")

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
                logger.debug(f"Uzyskano blokadę dla {lock_path}")

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
                    logger.debug(f"Zapisano tymczasowy plik: {temp_file_path}")

                # ✅ POPRAWKA: Uproszczona logika atomic move z fallback
                try:
                    # Próbuj os.rename (najbardziej atomic)
                    os.rename(temp_file_path, metadata_path)
                    logger.debug(f"Atomic move: {temp_file_path} -> {metadata_path}")
                except OSError:
                    # Fallback dla Windows i problemów z rename
                    try:
                        if os.path.exists(metadata_path):
                            os.replace(temp_file_path, metadata_path)
                            logger.debug(
                                f"Replace: {temp_file_path} -> {metadata_path}"
                            )
                        else:
                            shutil.move(temp_file_path, metadata_path)
                            logger.debug(f"Move: {temp_file_path} -> {metadata_path}")
                    except OSError as e:
                        logger.error(f"Błąd atomic move: {e}")
                        raise

                # Sprawdź czy plik został faktycznie utworzony
                if os.path.exists(metadata_path):
                    file_size = os.path.getsize(metadata_path)
                    logger.debug(
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
                f"Nie można uzyskać blokady dla {lock_path} w ciągu {timeout}s"
            )
            return False
        except Exception as e:
            logger.error(f"Błąd zapisu metadanych: {e}", exc_info=True)
            return False
        finally:
            # ✅ POPRAWKA: Lepsze zarządzanie zasobami z retry cleanup
            self._cleanup_temp_file(temp_file_path)

    def _cleanup_temp_file(self, temp_file_path: str, max_retries: int = 3) -> None:
        """
        Usuwa tymczasowy plik z retry logic.

        Args:
            temp_file_path: Ścieżka do tymczasowego pliku
            max_retries: Maksymalna liczba prób usunięcia
        """
        if not temp_file_path or not os.path.exists(temp_file_path):
            return

        for attempt in range(max_retries):
            try:
                os.unlink(temp_file_path)
                logger.debug(f"Usunięto tymczasowy plik: {temp_file_path}")
                return
            except OSError as e:
                if attempt == max_retries - 1:
                    logger.warning(
                        f"Nie można usunąć tymczasowego pliku {temp_file_path} po {max_retries} próbach: {e}"
                    )
                else:
                    logger.debug(
                        f"Próba {attempt + 1} usunięcia tymczasowego pliku nie powiodła się: {e}"
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

    # ✅ POPRAWKA: Usunięto duplikację walidacji - używamy tylko metadata_validator.py
    # Metoda _validate_metadata_structure została usunięta - walidacja jest w MetadataValidator
