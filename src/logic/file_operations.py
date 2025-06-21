"""
Zrefaktoryzowane operacje na plikach - fasada dla nowych klas specjalistycznych.
ETAP 6 KRYTYCZNY: Thread-safe factory pattern, walidacja parametrów, proper error handling.
"""

import logging
import os
import threading
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Union

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
from src.utils.path_utils import is_valid_filename


# Thread-safe factory pattern zamiast globalnych singleton'ów
class FileOperationsFactory:
    """Thread-safe factory dla komponentów operacji na plikach."""

    _instance = None
    _lock = threading.RLock()
    _components: Dict[str, Any] = {}
    _component_locks: Dict[str, threading.RLock] = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def get_file_opener(self) -> FileOpener:
        """Thread-safe dostęp do FileOpener."""
        return self._get_component("file_opener", FileOpener)

    def get_file_system_ops(self) -> FileSystemOperations:
        """Thread-safe dostęp do FileSystemOperations."""
        return self._get_component("file_system_ops", FileSystemOperations)

    def get_file_pair_ops(self) -> FilePairOperations:
        """Thread-safe dostęp do FilePairOperations."""
        return self._get_component("file_pair_ops", FilePairOperations)

    def _get_component(self, name: str, component_class):
        """Thread-safe tworzenie i dostęp do komponentów."""
        if name not in self._component_locks:
            with self._lock:
                if name not in self._component_locks:
                    self._component_locks[name] = threading.RLock()

        with self._component_locks[name]:
            if name not in self._components:
                self._components[name] = component_class()
            return self._components[name]

    def clear_cache(self):
        """Czyści cache komponentów (dla testów)."""
        with self._lock:
            self._components.clear()
            self._component_locks.clear()


# Thread-safe factory instance
_factory = FileOperationsFactory()

# Deprecation warning cache - zapobiega spamowi logów
_deprecation_warnings_shown = set()
_deprecation_lock = threading.RLock()

logger = logging.getLogger(__name__)


# === VALIDATION HELPERS ===


def _validate_path(path: str, name: str = "path") -> None:
    """Waliduje ścieżkę pliku/folderu."""
    if not path or not isinstance(path, str):
        raise ValueError(f"{name} must be a non-empty string")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{name} does not exist: {path}")


def _validate_filename(filename: str, name: str = "filename") -> None:
    """Waliduje nazwę pliku."""
    if not filename or not isinstance(filename, str):
        raise ValueError(f"{name} must be a non-empty string")
    if not is_valid_filename(filename):
        raise ValueError(f"{name} contains invalid characters: {filename}")


def _validate_file_pair(file_pair: FilePair, name: str = "file_pair") -> None:
    """Waliduje obiekt FilePair."""
    if not isinstance(file_pair, FilePair):
        raise TypeError(f"{name} must be a FilePair instance")
    if not file_pair.archive_path or not file_pair.preview_path:
        raise ValueError(f"{name} must have valid archive and preview paths")


def _log_deprecation_warning_once(function_name: str, param_name: str) -> None:
    """Loguje deprecation warning tylko raz per funkcja-parametr."""
    warning_key = f"{function_name}:{param_name}"
    with _deprecation_lock:
        if warning_key not in _deprecation_warnings_shown:
            logger.warning(
                f"Parameter {param_name} in {function_name} is deprecated - using central factory"
            )
            _deprecation_warnings_shown.add(warning_key)


# === ERROR HANDLING CONTEXT MANAGER ===


@contextmanager
def _safe_operation_context(operation_name: str):
    """Context manager dla bezpiecznych operacji z proper error handling."""
    try:
        yield
    except (ValueError, TypeError, FileNotFoundError) as e:
        logger.error(f"{operation_name} failed - validation error: {e}")
        raise
    except OSError as e:
        logger.error(f"{operation_name} failed - system error: {e}")
        raise
    except Exception as e:
        logger.error(f"{operation_name} failed - unexpected error: {e}")
        raise


# === OPERACJE OTWIERANIA PLIKÓW ===


def open_archive_externally(archive_path: str) -> bool:
    """
    Otwiera plik archiwum w domyślnym programie systemowym.
    Thread-safe z walidacją parametrów.

    Args:
        archive_path: Ścieżka do pliku archiwum

    Returns:
        True jeśli operacja się powiodła

    Raises:
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Plik nie istnieje
    """
    with _safe_operation_context("open_archive_externally"):
        _validate_path(archive_path, "archive_path")
        return _factory.get_file_opener().open_archive_externally(archive_path)


def open_file_externally(file_path: str) -> bool:
    """
    Otwiera dowolny plik w domyślnym programie systemowym.
    Thread-safe z walidacją parametrów.

    Args:
        file_path: Ścieżka do pliku

    Returns:
        True jeśli operacja się powiodła

    Raises:
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Plik nie istnieje
    """
    with _safe_operation_context("open_file_externally"):
        _validate_path(file_path, "file_path")
        return _factory.get_file_opener().open_file_externally(file_path)


def open_folder_externally(folder_path: str) -> bool:
    """
    Otwiera folder w eksploratorze plików.
    Thread-safe z walidacją parametrów.

    Args:
        folder_path: Ścieżka do folderu

    Returns:
        True jeśli operacja się powiodła

    Raises:
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Folder nie istnieje
    """
    with _safe_operation_context("open_folder_externally"):
        _validate_path(folder_path, "folder_path")
        return _factory.get_file_opener().open_folder_externally(folder_path)


# === OPERACJE NA SYSTEMIE PLIKÓW ===


def create_folder(
    parent_directory: str, folder_name: str, worker_factory=None
) -> Optional[CreateFolderWorkerInterface]:
    """
    Tworzy nowy folder w podanej lokalizacji.
    Thread-safe z walidacją parametrów.

    Args:
        parent_directory: Ścieżka do katalogu nadrzędnego
        folder_name: Nazwa nowego folderu
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu

    Raises:
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Katalog nadrzędny nie istnieje
    """
    with _safe_operation_context("create_folder"):
        if worker_factory is not None:
            _log_deprecation_warning_once("create_folder", "worker_factory")

        _validate_path(parent_directory, "parent_directory")
        _validate_filename(folder_name, "folder_name")

        return _factory.get_file_system_ops().create_folder(
            parent_directory, folder_name
        )


def rename_folder(
    folder_path: str, new_folder_name: str, worker_factory=None
) -> Optional[RenameFolderWorkerInterface]:
    """
    Zmienia nazwę istniejącego folderu.
    Thread-safe z walidacją parametrów.

    Args:
        folder_path: Aktualna ścieżka do folderu
        new_folder_name: Nowa nazwa folderu
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu

    Raises:
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Folder nie istnieje
    """
    with _safe_operation_context("rename_folder"):
        if worker_factory is not None:
            _log_deprecation_warning_once("rename_folder", "worker_factory")

        _validate_path(folder_path, "folder_path")
        _validate_filename(new_folder_name, "new_folder_name")

        return _factory.get_file_system_ops().rename_folder(
            folder_path, new_folder_name
        )


def delete_folder(
    folder_path: str, delete_content: bool = False, worker_factory=None
) -> Optional[DeleteFolderWorkerInterface]:
    """
    Usuwa folder (opcjonalnie z zawartością).
    Thread-safe z walidacją parametrów.

    Args:
        folder_path: Ścieżka do folderu do usunięcia
        delete_content: Czy usunąć folder z zawartością
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu

    Raises:
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Folder nie istnieje
    """
    with _safe_operation_context("delete_folder"):
        if worker_factory is not None:
            _log_deprecation_warning_once("delete_folder", "worker_factory")

        _validate_path(folder_path, "folder_path")
        if not isinstance(delete_content, bool):
            raise ValueError("delete_content must be a boolean")

        return _factory.get_file_system_ops().delete_folder(folder_path, delete_content)


# === OPERACJE NA PARACH PLIKÓW ===


def manually_pair_files(
    archive_path: str, preview_path: str, working_directory: str, worker_factory=None
) -> Optional[ManuallyPairFilesWorkerInterface]:
    """
    Ręcznie paruje pliki archiwum z plikiem podglądu.
    Thread-safe z walidacją parametrów.

    Args:
        archive_path: Ścieżka do pliku archiwum
        preview_path: Ścieżka do pliku podglądu
        working_directory: Katalog roboczy
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu

    Raises:
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Pliki nie istnieją
    """
    with _safe_operation_context("manually_pair_files"):
        if worker_factory is not None:
            _log_deprecation_warning_once("manually_pair_files", "worker_factory")

        _validate_path(archive_path, "archive_path")
        _validate_path(preview_path, "preview_path")
        _validate_path(working_directory, "working_directory")

        return _factory.get_file_pair_ops().manually_pair_files(
            archive_path, preview_path, working_directory
        )


def create_pair_from_files(
    archive_path: str, preview_path: str, worker_factory=None
) -> Optional[ManuallyPairFilesWorkerInterface]:
    """
    Tworzy parę plików z podanych ścieżek.
    Thread-safe z walidacją parametrów.

    Args:
        archive_path: Ścieżka do pliku archiwum
        preview_path: Ścieżka do pliku podglądu
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu

    Raises:
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Pliki nie istnieją
    """
    with _safe_operation_context("create_pair_from_files"):
        if worker_factory is not None:
            _log_deprecation_warning_once("create_pair_from_files", "worker_factory")

        _validate_path(archive_path, "archive_path")
        _validate_path(preview_path, "preview_path")

        return _factory.get_file_pair_ops().create_pair_from_files(
            archive_path, preview_path
        )


def rename_file_pair(
    file_pair: FilePair, new_base_name: str, working_directory: str, worker_factory=None
) -> Optional[RenameFilePairWorkerInterface]:
    """
    Zmienia nazwę pary plików.
    Thread-safe z walidacją parametrów.

    Args:
        file_pair: Para plików do zmiany nazwy
        new_base_name: Nowa nazwa bazowa
        working_directory: Katalog roboczy
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu

    Raises:
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Pliki nie istnieją
    """
    with _safe_operation_context("rename_file_pair"):
        if worker_factory is not None:
            _log_deprecation_warning_once("rename_file_pair", "worker_factory")

        _validate_file_pair(file_pair, "file_pair")
        _validate_filename(new_base_name, "new_base_name")
        _validate_path(working_directory, "working_directory")

        return _factory.get_file_pair_ops().rename_file_pair(
            file_pair, new_base_name, working_directory
        )


def delete_file_pair(
    file_pair: FilePair, worker_factory=None
) -> Optional[DeleteFilePairWorkerInterface]:
    """
    Usuwa parę plików.
    Thread-safe z walidacją parametrów.

    Args:
        file_pair: Para plików do usunięcia
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu

    Raises:
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Pliki nie istnieją
    """
    with _safe_operation_context("delete_file_pair"):
        if worker_factory is not None:
            _log_deprecation_warning_once("delete_file_pair", "worker_factory")

        _validate_file_pair(file_pair, "file_pair")

        return _factory.get_file_pair_ops().delete_file_pair(file_pair)


def move_file_pair(
    file_pair: FilePair, new_target_directory: str, worker_factory=None
) -> Optional[MoveFilePairWorkerInterface]:
    """
    Przenosi parę plików do nowego katalogu.
    Thread-safe z walidacją parametrów.

    Args:
        file_pair: Para plików do przeniesienia
        new_target_directory: Katalog docelowy
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu

    Raises:
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Pliki lub katalog nie istnieją
    """
    with _safe_operation_context("move_file_pair"):
        if worker_factory is not None:
            _log_deprecation_warning_once("move_file_pair", "worker_factory")

        _validate_file_pair(file_pair, "file_pair")
        _validate_path(new_target_directory, "new_target_directory")

        return _factory.get_file_pair_ops().move_file_pair(
            file_pair, new_target_directory
        )


# === BATCH OPERATIONS SUPPORT ===


class BatchFileOperations:
    """Thread-safe batch operations dla operacji na plikach."""

    def __init__(self):
        self._operations: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def add_create_folder(
        self, parent_directory: str, folder_name: str
    ) -> "BatchFileOperations":
        """Dodaje operację tworzenia folderu do batch."""
        with self._lock:
            self._operations.append(
                {
                    "type": "create_folder",
                    "parent_directory": parent_directory,
                    "folder_name": folder_name,
                }
            )
        return self

    def add_rename_folder(
        self, folder_path: str, new_folder_name: str
    ) -> "BatchFileOperations":
        """Dodaje operację zmiany nazwy folderu do batch."""
        with self._lock:
            self._operations.append(
                {
                    "type": "rename_folder",
                    "folder_path": folder_path,
                    "new_folder_name": new_folder_name,
                }
            )
        return self

    def add_delete_folder(
        self, folder_path: str, delete_content: bool = False
    ) -> "BatchFileOperations":
        """Dodaje operację usuwania folderu do batch."""
        with self._lock:
            self._operations.append(
                {
                    "type": "delete_folder",
                    "folder_path": folder_path,
                    "delete_content": delete_content,
                }
            )
        return self

    def add_manually_pair_files(
        self, archive_path: str, preview_path: str, working_directory: str
    ) -> "BatchFileOperations":
        """Dodaje operację parowania plików do batch."""
        with self._lock:
            self._operations.append(
                {
                    "type": "manually_pair_files",
                    "archive_path": archive_path,
                    "preview_path": preview_path,
                    "working_directory": working_directory,
                }
            )
        return self

    def add_rename_file_pair(
        self, file_pair: FilePair, new_base_name: str, working_directory: str
    ) -> "BatchFileOperations":
        """Dodaje operację zmiany nazwy pary plików do batch."""
        with self._lock:
            self._operations.append(
                {
                    "type": "rename_file_pair",
                    "file_pair": file_pair,
                    "new_base_name": new_base_name,
                    "working_directory": working_directory,
                }
            )
        return self

    def add_delete_file_pair(self, file_pair: FilePair) -> "BatchFileOperations":
        """Dodaje operację usuwania pary plików do batch."""
        with self._lock:
            self._operations.append(
                {"type": "delete_file_pair", "file_pair": file_pair}
            )
        return self

    def add_move_file_pair(
        self, file_pair: FilePair, new_target_directory: str
    ) -> "BatchFileOperations":
        """Dodaje operację przenoszenia pary plików do batch."""
        with self._lock:
            self._operations.append(
                {
                    "type": "move_file_pair",
                    "file_pair": file_pair,
                    "new_target_directory": new_target_directory,
                }
            )
        return self

    def execute(
        self,
    ) -> List[
        Optional[
            Union[
                CreateFolderWorkerInterface,
                RenameFolderWorkerInterface,
                DeleteFolderWorkerInterface,
                ManuallyPairFilesWorkerInterface,
                RenameFilePairWorkerInterface,
                DeleteFilePairWorkerInterface,
                MoveFilePairWorkerInterface,
            ]
        ]
    ]:
        """
        Wykonuje wszystkie operacje w batch.

        Returns:
            Lista worker'ów dla każdej operacji
        """
        with self._lock:
            results = []
            for operation in self._operations:
                try:
                    if operation["type"] == "create_folder":
                        result = create_folder(
                            operation["parent_directory"], operation["folder_name"]
                        )
                    elif operation["type"] == "rename_folder":
                        result = rename_folder(
                            operation["folder_path"], operation["new_folder_name"]
                        )
                    elif operation["type"] == "delete_folder":
                        result = delete_folder(
                            operation["folder_path"], operation["delete_content"]
                        )
                    elif operation["type"] == "manually_pair_files":
                        result = manually_pair_files(
                            operation["archive_path"],
                            operation["preview_path"],
                            operation["working_directory"],
                        )
                    elif operation["type"] == "rename_file_pair":
                        result = rename_file_pair(
                            operation["file_pair"],
                            operation["new_base_name"],
                            operation["working_directory"],
                        )
                    elif operation["type"] == "delete_file_pair":
                        result = delete_file_pair(operation["file_pair"])
                    elif operation["type"] == "move_file_pair":
                        result = move_file_pair(
                            operation["file_pair"], operation["new_target_directory"]
                        )
                    else:
                        logger.error(f"Unknown operation type: {operation['type']}")
                        result = None

                    results.append(result)
                except Exception as e:
                    logger.error(f"Batch operation {operation['type']} failed: {e}")
                    results.append(None)

            # Czyści operacje po wykonaniu
            self._operations.clear()
            return results

    def clear(self):
        """Czyści wszystkie operacje z batch."""
        with self._lock:
            self._operations.clear()

    def count(self) -> int:
        """Zwraca liczbę operacji w batch."""
        with self._lock:
            return len(self._operations)


def create_batch_operations() -> BatchFileOperations:
    """
    Tworzy nowy batch operations builder.

    Returns:
        BatchFileOperations instance
    """
    return BatchFileOperations()


# === BACKWARD COMPATIBILITY ===


# Aliasy dla zachowania kompatybilności z istniejącym kodem
# Dodano deprecation warnings dla lepszej informacji użytkowników
def open_file(file_path: str) -> bool:
    """
    Alias dla open_file_externally.
    DEPRECATED: Użyj open_file_externally() zamiast tego.
    """
    logger.warning("open_file() is deprecated - use open_file_externally() instead")
    return open_file_externally(file_path)


def open_folder(folder_path: str) -> bool:
    """
    Alias dla open_folder_externally.
    DEPRECATED: Użyj open_folder_externally() zamiast tego.
    """
    logger.warning("open_folder() is deprecated - use open_folder_externally() instead")
    return open_folder_externally(folder_path)


# Module initialization - przeniesione na koniec żeby uniknąć logów przy imporcie
def _initialize_module():
    """Inicjalizacja modułu - wywoływana tylko raz."""
    logger.debug("File operations module initialized with thread-safe factory pattern")


# Wywołanie inicjalizacji tylko jeśli moduł jest uruchamiany bezpośrednio
if __name__ == "__main__":
    _initialize_module()
