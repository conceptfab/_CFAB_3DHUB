"""
CentralizedWorkerFactory - centralna fabryka workerów dla operacji na plikach.
Eliminuje duplikację kodu i zarządza tworzeniem wszystkich typów workerów.
"""

import logging
from typing import Optional, Protocol

from src.interfaces.worker_interface import (
    CreateFolderWorkerInterface,
    DeleteFilePairWorkerInterface,
    DeleteFolderWorkerInterface,
    ManuallyPairFilesWorkerInterface,
    MoveFilePairWorkerInterface,
    RenameFilePairWorkerInterface,
    RenameFolderWorkerInterface,
)
from src.models.file_pair import FilePair


class WorkerFactoryInterface(Protocol):
    """
    Interface dla fabryki workerów - definiuje wymagane metody.
    Pozwala na dependency injection bez ścisłego sprzężenia.
    """

    def create_folder_worker(
        self, parent_directory: str, folder_name: str
    ) -> CreateFolderWorkerInterface: ...

    def create_rename_folder_worker(
        self, folder_path: str, new_folder_name: str
    ) -> RenameFolderWorkerInterface: ...

    def create_delete_folder_worker(
        self, folder_path: str, delete_content: bool = False
    ) -> DeleteFolderWorkerInterface: ...

    def create_manually_pair_files_worker(
        self, archive_path: str, preview_path: str, working_directory: str
    ) -> ManuallyPairFilesWorkerInterface: ...

    def create_rename_file_pair_worker(
        self, file_pair: FilePair, new_base_name: str, working_directory: str
    ) -> RenameFilePairWorkerInterface: ...

    def create_delete_file_pair_worker(
        self, file_pair: FilePair
    ) -> DeleteFilePairWorkerInterface: ...

    def create_move_file_pair_worker(
        self, file_pair: FilePair, new_target_directory: str
    ) -> MoveFilePairWorkerInterface: ...


class CentralizedWorkerFactory:
    """
    Centralna fabryka workerów dla wszystkich operacji na plikach.
    Zarządza tworzeniem workerów i obsługą błędów w jednym miejscu.
    """

    def __init__(self, delegate_factory: Optional[WorkerFactoryInterface] = None):
        """
        Inicjalizuje fabrykę.

        Args:
            delegate_factory: Zewnętrzna fabryka do której deleguje tworzenie workerów
        """
        self.logger = logging.getLogger(__name__)
        self._delegate_factory = delegate_factory

    def set_delegate_factory(self, factory: WorkerFactoryInterface):
        """
        Ustawia delegat fabryki workerów.

        Args:
            factory: Fabryka do której będą delegowane operacje
        """
        self._delegate_factory = factory
        self.logger.debug("Ustawiono nową fabrykę workerów")

    def _ensure_factory_available(self) -> bool:
        """
        Sprawdza czy fabryka jest dostępna.

        Returns:
            True jeśli fabryka jest dostępna
        """
        if self._delegate_factory is None:
            self.logger.error("Brak skonfigurowanej fabryki workerów")
            return False
        return True

    def create_folder_worker(
        self, parent_directory: str, folder_name: str
    ) -> Optional[CreateFolderWorkerInterface]:
        """
        Tworzy worker do tworzenia folderu.

        Args:
            parent_directory: Katalog nadrzędny
            folder_name: Nazwa nowego folderu

        Returns:
            Worker lub None w przypadku błędu
        """
        if not self._ensure_factory_available():
            return None

        try:
            worker = self._delegate_factory.create_folder_worker(
                parent_directory, folder_name
            )
            self.logger.debug(f"Utworzono CreateFolderWorker: {folder_name}")
            return worker
        except Exception as e:
            self.logger.error(f"Błąd tworzenia CreateFolderWorker: {e}")
            return None

    def create_rename_folder_worker(
        self, folder_path: str, new_folder_name: str
    ) -> Optional[RenameFolderWorkerInterface]:
        """
        Tworzy worker do zmiany nazwy folderu.

        Args:
            folder_path: Ścieżka do folderu
            new_folder_name: Nowa nazwa folderu

        Returns:
            Worker lub None w przypadku błędu
        """
        if not self._ensure_factory_available():
            return None

        try:
            worker = self._delegate_factory.create_rename_folder_worker(
                folder_path, new_folder_name
            )
            self.logger.debug(f"Utworzono RenameFolderWorker: {new_folder_name}")
            return worker
        except Exception as e:
            self.logger.error(f"Błąd tworzenia RenameFolderWorker: {e}")
            return None

    def create_delete_folder_worker(
        self, folder_path: str, delete_content: bool = False
    ) -> Optional[DeleteFolderWorkerInterface]:
        """
        Tworzy worker do usuwania folderu.

        Args:
            folder_path: Ścieżka do folderu
            delete_content: Czy usunąć zawartość

        Returns:
            Worker lub None w przypadku błędu
        """
        if not self._ensure_factory_available():
            return None

        try:
            worker = self._delegate_factory.create_delete_folder_worker(
                folder_path, delete_content
            )
            self.logger.debug(f"Utworzono DeleteFolderWorker")
            return worker
        except Exception as e:
            self.logger.error(f"Błąd tworzenia DeleteFolderWorker: {e}")
            return None

    def create_manually_pair_files_worker(
        self, archive_path: str, preview_path: str, working_directory: str
    ) -> Optional[ManuallyPairFilesWorkerInterface]:
        """
        Tworzy worker do ręcznego parowania plików.

        Args:
            archive_path: Ścieżka do archiwum
            preview_path: Ścieżka do podglądu
            working_directory: Katalog roboczy

        Returns:
            Worker lub None w przypadku błędu
        """
        if not self._ensure_factory_available():
            return None

        try:
            worker = self._delegate_factory.create_manually_pair_files_worker(
                archive_path, preview_path, working_directory
            )
            self.logger.debug("Utworzono ManuallyPairFilesWorker")
            return worker
        except Exception as e:
            self.logger.error(f"Błąd tworzenia ManuallyPairFilesWorker: {e}")
            return None

    def create_rename_file_pair_worker(
        self, file_pair: FilePair, new_base_name: str, working_directory: str
    ) -> Optional[RenameFilePairWorkerInterface]:
        """
        Tworzy worker do zmiany nazwy pary plików.

        Args:
            file_pair: Para plików
            new_base_name: Nowa nazwa bazowa
            working_directory: Katalog roboczy

        Returns:
            Worker lub None w przypadku błędu
        """
        if not self._ensure_factory_available():
            return None

        try:
            worker = self._delegate_factory.create_rename_file_pair_worker(
                file_pair, new_base_name, working_directory
            )
            self.logger.debug(f"Utworzono RenameFilePairWorker: {new_base_name}")
            return worker
        except Exception as e:
            self.logger.error(f"Błąd tworzenia RenameFilePairWorker: {e}")
            return None

    def create_delete_file_pair_worker(
        self, file_pair: FilePair
    ) -> Optional[DeleteFilePairWorkerInterface]:
        """
        Tworzy worker do usuwania pary plików.

        Args:
            file_pair: Para plików do usunięcia

        Returns:
            Worker lub None w przypadku błędu
        """
        if not self._ensure_factory_available():
            return None

        try:
            worker = self._delegate_factory.create_delete_file_pair_worker(file_pair)
            self.logger.debug("Utworzono DeleteFilePairWorker")
            return worker
        except Exception as e:
            self.logger.error(f"Błąd tworzenia DeleteFilePairWorker: {e}")
            return None

    def create_move_file_pair_worker(
        self, file_pair: FilePair, new_target_directory: str
    ) -> Optional[MoveFilePairWorkerInterface]:
        """
        Tworzy worker do przenoszenia pary plików.

        Args:
            file_pair: Para plików
            new_target_directory: Katalog docelowy

        Returns:
            Worker lub None w przypadku błędu
        """
        if not self._ensure_factory_available():
            return None

        try:
            worker = self._delegate_factory.create_move_file_pair_worker(
                file_pair, new_target_directory
            )
            self.logger.debug("Utworzono MoveFilePairWorker")
            return worker
        except Exception as e:
            self.logger.error(f"Błąd tworzenia MoveFilePairWorker: {e}")
            return None


# Globalna instancja fabryki - singleton pattern
_global_factory = CentralizedWorkerFactory()


def get_worker_factory() -> CentralizedWorkerFactory:
    """
    Zwraca globalną instancję fabryki workerów.

    Returns:
        Centralna fabryka workerów
    """
    return _global_factory


def configure_worker_factory(delegate_factory: WorkerFactoryInterface):
    """
    Konfiguruje globalną fabrykę workerów.

    Args:
        delegate_factory: Fabryka do której będą delegowane operacje
    """
    _global_factory.set_delegate_factory(delegate_factory)
