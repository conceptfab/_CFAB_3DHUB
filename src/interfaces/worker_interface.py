"""
Interfejsy dla workerów do eliminacji zależności między warstwami.
"""

from typing import Protocol, runtime_checkable

from src.models.file_pair import FilePair


@runtime_checkable
class WorkerInterface(Protocol):
    """Podstawowy interfejs dla wszystkich workerów"""
    
    def execute(self) -> None:
        """Wykonuje operację"""
        ...


@runtime_checkable
class BulkMoveWorkerInterface(Protocol):
    """Interfejs dla workera masowego przenoszenia plików"""
    
    def execute_bulk_move(self, files, target_dir) -> None:
        """Wykonuje masowe przenoszenie plików"""
        ...


@runtime_checkable
class CreateFolderWorkerInterface(Protocol):
    """Interfejs dla workera tworzenia folderu"""
    
    def execute_create_folder(self, parent_directory: str, folder_name: str) -> str:
        """Tworzy folder i zwraca ścieżkę"""
        ...


@runtime_checkable
class DeleteFilePairWorkerInterface(Protocol):
    """Interfejs dla workera usuwania pary plików"""
    
    def execute_delete_file_pair(self, file_pair: FilePair) -> bool:
        """Usuwa parę plików"""
        ...


@runtime_checkable
class RenameFilePairWorkerInterface(Protocol):
    """Interfejs dla workera zmiany nazwy pary plików"""
    
    def execute_rename_file_pair(
        self, file_pair: FilePair, new_base_name: str, working_directory: str
    ) -> FilePair:
        """Zmienia nazwę pary plików i zwraca nową parę"""
        ...


@runtime_checkable
class MoveFilePairWorkerInterface(Protocol):
    """Interfejs dla workera przenoszenia pary plików"""
    
    def execute_move_file_pair(
        self, file_pair: FilePair, target_directory: str
    ) -> FilePair:
        """Przenosi parę plików i zwraca nową parę"""
        ...


@runtime_checkable
class ManuallyPairFilesWorkerInterface(Protocol):
    """Interfejs dla workera ręcznego parowania plików"""
    
    def execute_manually_pair_files(
        self, archive_path: str, preview_path: str, working_directory: str
    ) -> FilePair:
        """Ręcznie paruje pliki i zwraca nową parę"""
        ...


@runtime_checkable
class DeleteFolderWorkerInterface(Protocol):
    """Interfejs dla workera usuwania folderu"""
    
    def execute_delete_folder(self, folder_path: str, delete_content: bool) -> bool:
        """Usuwa folder"""
        ...


@runtime_checkable
class RenameFolderWorkerInterface(Protocol):
    """Interfejs dla workera zmiany nazwy folderu"""
    
    def execute_rename_folder(self, folder_path: str, new_folder_name: str) -> str:
        """Zmienia nazwę folderu i zwraca nową ścieżkę"""
        ...