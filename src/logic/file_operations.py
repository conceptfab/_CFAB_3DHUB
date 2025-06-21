"""
Zrefaktoryzowane operacje na plikach - fasada dla nowych klas specjalistycznych.
ETAP 2 KRYTYCZNY: Eliminuje duplikację kodu, centralizuje factory, dzieli odpowiedzialności.
"""

import logging
import os
import shutil
from typing import Optional

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from src.interfaces.worker_interface import (
    CreateFolderWorkerInterface,
    DeleteFilePairWorkerInterface,
    DeleteFolderWorkerInterface,
    ManuallyPairFilesWorkerInterface,
    MoveFilePairWorkerInterface,
    RenameFilePairWorkerInterface,
    RenameFolderWorkerInterface,
)
from src.logic.file_ops_components.file_opener import FileOpener
from src.logic.file_ops_components.file_pair_operations import FilePairOperations
from src.logic.file_ops_components.file_system_operations import FileSystemOperations
from src.models.file_pair import FilePair
from src.utils.path_utils import is_valid_filename, normalize_path

# Globalne instancje klas specjalistycznych - singleton pattern
_file_opener = FileOpener()
_file_system_ops = FileSystemOperations()
_file_pair_ops = FilePairOperations()

logger = logging.getLogger(__name__)


# === OPERACJE OTWIERANIA PLIKÓW ===


def open_archive_externally(archive_path: str) -> bool:
    """
    Otwiera plik archiwum w domyślnym programie systemowym.
    ZREFAKTORYZOWANY - deleguje do FileOpener.

    Args:
        archive_path: Ścieżka do pliku archiwum

    Returns:
        True jeśli operacja się powiodła
    """
    return _file_opener.open_archive_externally(archive_path)


def open_file_externally(file_path: str) -> bool:
    """
    Otwiera dowolny plik w domyślnym programie systemowym.
    NOWA FUNKCJONALNOŚĆ - deleguje do FileOpener.

    Args:
        file_path: Ścieżka do pliku

    Returns:
        True jeśli operacja się powiodła
    """
    return _file_opener.open_file_externally(file_path)


def open_folder_externally(folder_path: str) -> bool:
    """
    Otwiera folder w eksploratorze plików.
    NOWA FUNKCJONALNOŚĆ - deleguje do FileOpener.

    Args:
        folder_path: Ścieżka do folderu

    Returns:
        True jeśli operacja się powiodła
    """
    return _file_opener.open_folder_externally(folder_path)


# === OPERACJE NA SYSTEMIE PLIKÓW ===


def create_folder(
    parent_directory: str, folder_name: str, worker_factory=None
) -> Optional[CreateFolderWorkerInterface]:
    """
    Tworzy nowy folder w podanej lokalizacji.
    ZREFAKTORYZOWANY - deleguje do FileSystemOperations.

    Args:
        parent_directory: Ścieżka do katalogu nadrzędnego
        folder_name: Nazwa nowego folderu
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu
    """
    if worker_factory is not None:
        logger.warning("Parameter worker_factory is deprecated - using central factory")

    return _file_system_ops.create_folder(parent_directory, folder_name)


def rename_folder(
    folder_path: str, new_folder_name: str, worker_factory=None
) -> Optional[RenameFolderWorkerInterface]:
    """
    Zmienia nazwę istniejącego folderu.
    ZREFAKTORYZOWANY - deleguje do FileSystemOperations.

    Args:
        folder_path: Aktualna ścieżka do folderu
        new_folder_name: Nowa nazwa folderu
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu
    """
    if worker_factory is not None:
        logger.warning("Parameter worker_factory is deprecated - using central factory")

    return _file_system_ops.rename_folder(folder_path, new_folder_name)


def delete_folder(
    folder_path: str, delete_content: bool = False, worker_factory=None
) -> Optional[DeleteFolderWorkerInterface]:
    """
    Usuwa folder (opcjonalnie z zawartością).
    ZREFAKTORYZOWANY - deleguje do FileSystemOperations.

    Args:
        folder_path: Ścieżka do folderu do usunięcia
        delete_content: Czy usunąć folder z zawartością
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu
    """
    if worker_factory is not None:
        logger.warning("Parameter worker_factory is deprecated - using central factory")

    return _file_system_ops.delete_folder(folder_path, delete_content)


# === OPERACJE NA PARACH PLIKÓW ===


def manually_pair_files(
    archive_path: str, preview_path: str, working_directory: str, worker_factory=None
) -> Optional[ManuallyPairFilesWorkerInterface]:
    """
    Ręcznie paruje pliki archiwum z plikiem podglądu.
    ZREFAKTORYZOWANY - deleguje do FilePairOperations.

    Args:
        archive_path: Ścieżka do pliku archiwum
        preview_path: Ścieżka do pliku podglądu
        working_directory: Katalog roboczy
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu
    """
    if worker_factory is not None:
        logger.warning("Parameter worker_factory is deprecated - using central factory")

    return _file_pair_ops.manually_pair_files(
        archive_path, preview_path, working_directory
    )


def create_pair_from_files(
    archive_path: str, preview_path: str, worker_factory=None
) -> Optional[ManuallyPairFilesWorkerInterface]:
    """
    Tworzy parę plików z podanych ścieżek.
    ZREFAKTORYZOWANY - deleguje do FilePairOperations.

    Args:
        archive_path: Ścieżka do pliku archiwum
        preview_path: Ścieżka do pliku podglądu
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu
    """
    if worker_factory is not None:
        logger.warning("Parameter worker_factory is deprecated - using central factory")

    return _file_pair_ops.create_pair_from_files(archive_path, preview_path)


def rename_file_pair(
    file_pair: FilePair, new_base_name: str, working_directory: str, worker_factory=None
) -> Optional[RenameFilePairWorkerInterface]:
    """
    Zmienia nazwę pary plików.
    ZREFAKTORYZOWANY - deleguje do FilePairOperations.

    Args:
        file_pair: Para plików do zmiany nazwy
        new_base_name: Nowa nazwa bazowa
        working_directory: Katalog roboczy
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu
    """
    if worker_factory is not None:
        logger.warning("Parameter worker_factory is deprecated - using central factory")

    return _file_pair_ops.rename_file_pair(file_pair, new_base_name, working_directory)


def delete_file_pair(
    file_pair: FilePair, worker_factory=None
) -> Optional[DeleteFilePairWorkerInterface]:
    """
    Usuwa parę plików.
    ZREFAKTORYZOWANY - deleguje do FilePairOperations.

    Args:
        file_pair: Para plików do usunięcia
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu
    """
    if worker_factory is not None:
        logger.warning("Parameter worker_factory is deprecated - using central factory")

    return _file_pair_ops.delete_file_pair(file_pair)


def move_file_pair(
    file_pair: FilePair, new_target_directory: str, worker_factory=None
) -> Optional[MoveFilePairWorkerInterface]:
    """
    Przenosi parę plików do nowego katalogu.
    ZREFAKTORYZOWANY - deleguje do FilePairOperations.

    Args:
        file_pair: Para plików do przeniesienia
        new_target_directory: Katalog docelowy
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu
    """
    if worker_factory is not None:
        logger.warning("Parameter worker_factory is deprecated - using central factory")

    return _file_pair_ops.move_file_pair(file_pair, new_target_directory)


# === BACKWARD COMPATIBILITY ===

# Aliasy dla zachowania kompatybilności z istniejącym kodem
open_file = open_file_externally
open_folder = open_folder_externally

logger.info("File operations module refactored - using specialized classes")
