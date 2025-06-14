"""
Legacy wrapper dla MetadataManager CFAB_3DHUB.
🚀 ETAP 3: Refaktoryzacja MetadataManager - backward compatibility

Ten plik zapewnia backward compatibility dla istniejącego kodu.
Wszystkie funkcje delegują do nowych komponentów w pakiecie metadata/.
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

# Import nowej implementacji
from .metadata import MetadataManager

# Stałe związane z metadanymi - zachowane dla compatibility
METADATA_DIR_NAME = ".app_metadata"
METADATA_FILE_NAME = "metadata.json"
LOCK_FILE_NAME = "metadata.lock"
LOCK_TIMEOUT = 0.5
MIN_THUMBNAIL_WIDTH = 80

# Konfiguracja loggera dla tego modułu
logger = logging.getLogger(__name__)


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
    Legacy function: Use MetadataOperations.get_relative_path()
    Maintained for backward compatibility.
    """
    manager = MetadataManager.get_instance(base_path)
    return manager.operations.get_relative_path(absolute_path, base_path)


def get_absolute_path(relative_path: str, base_path: str) -> Optional[str]:
    """
    Legacy function: Use MetadataOperations.get_absolute_path()
    Maintained for backward compatibility.
    """
    manager = MetadataManager.get_instance(base_path)
    return manager.operations.get_absolute_path(relative_path, base_path)


def _validate_metadata_structure(metadata: Dict[str, Any]) -> bool:
    """
    Legacy function: Use MetadataValidator.validate_metadata_structure()
    Maintained for backward compatibility.
    """
    from .metadata.metadata_validator import MetadataValidator
    return MetadataValidator.validate_metadata_structure(metadata)


def _load_metadata_direct(working_directory: str) -> Dict[str, Any]:
    """
    Direct metadata loading without caching - used by legacy load_metadata function.

    Args:
        working_directory (str): Ścieżka do folderu roboczego.

    Returns:
        Dict[str, Any]: Słownik metadanych lub domyślna struktura w przypadku błędu.
    """
    manager = MetadataManager.get_instance(working_directory)
    return manager.io.load_metadata_from_file()


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
    return manager.apply_metadata_to_file_pairs(file_pairs_list)


def _apply_metadata_to_file_pairs_direct(
    metadata: Dict[str, Any], file_pairs_list: List, working_directory: str
) -> bool:
    """
    Direct implementation of metadata application - used by legacy function.
    """
    manager = MetadataManager.get_instance(working_directory)
    return manager.operations.apply_metadata_to_file_pairs(metadata, file_pairs_list)


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
    manager = MetadataManager.get_instance(working_directory)
    return manager.save_file_pair_metadata(file_pair, working_directory)


def remove_metadata_for_file(
    working_directory: str, relative_archive_path: str
) -> bool:
    """
    Legacy function: Use MetadataManager.get_instance(dir).remove_metadata_for_file()
    Maintained for backward compatibility.
    """
    manager = MetadataManager.get_instance(working_directory)
    return manager.remove_metadata_for_file(relative_archive_path)


def get_metadata_for_relative_path(
    working_directory: str, relative_archive_path: str
) -> Optional[Dict[str, Any]]:
    """
    Legacy function: Use MetadataManager.get_instance(dir).get_metadata_for_relative_path()
    Maintained for backward compatibility.
    """
    manager = MetadataManager.get_instance(working_directory)
    return manager.get_metadata_for_relative_path(relative_archive_path) 