"""
Factory do tworzenia workerów - most między logiką a implementacją UI.
"""

from typing import Protocol

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
    """Interfejs factory workerów"""
    
    def create_create_folder_worker(
        self, parent_directory: str, folder_name: str
    ) -> CreateFolderWorkerInterface:
        ...
    
    def create_rename_folder_worker(
        self, folder_path: str, new_folder_name: str
    ) -> RenameFolderWorkerInterface:
        ...
    
    def create_delete_folder_worker(
        self, folder_path: str, delete_content: bool
    ) -> DeleteFolderWorkerInterface:
        ...
    
    def create_manually_pair_files_worker(
        self, archive_path: str, preview_path: str, working_directory: str
    ) -> ManuallyPairFilesWorkerInterface:
        ...
    
    def create_rename_file_pair_worker(
        self, file_pair: FilePair, new_base_name: str, working_directory: str
    ) -> RenameFilePairWorkerInterface:
        ...
    
    def create_delete_file_pair_worker(
        self, file_pair: FilePair
    ) -> DeleteFilePairWorkerInterface:
        ...
    
    def create_move_file_pair_worker(
        self, file_pair: FilePair, target_directory: str
    ) -> MoveFilePairWorkerInterface:
        ...


class UIWorkerFactory:
    """Konkretna implementacja factory workerów używająca UI workerów"""
    
    def create_create_folder_worker(
        self, parent_directory: str, folder_name: str
    ) -> CreateFolderWorkerInterface:
        from src.ui.delegates.workers import CreateFolderWorker
        return CreateFolderWorker(parent_directory, folder_name)
    
    def create_rename_folder_worker(
        self, folder_path: str, new_folder_name: str
    ) -> RenameFolderWorkerInterface:
        from src.ui.delegates.workers import RenameFolderWorker
        return RenameFolderWorker(folder_path, new_folder_name)
    
    def create_delete_folder_worker(
        self, folder_path: str, delete_content: bool
    ) -> DeleteFolderWorkerInterface:
        from src.ui.delegates.workers import DeleteFolderWorker
        return DeleteFolderWorker(folder_path, delete_content)
    
    def create_manually_pair_files_worker(
        self, archive_path: str, preview_path: str, working_directory: str
    ) -> ManuallyPairFilesWorkerInterface:
        from src.ui.delegates.workers import ManuallyPairFilesWorker
        return ManuallyPairFilesWorker(archive_path, preview_path, working_directory)
    
    def create_rename_file_pair_worker(
        self, file_pair: FilePair, new_base_name: str, working_directory: str
    ) -> RenameFilePairWorkerInterface:
        from src.ui.delegates.workers import RenameFilePairWorker
        return RenameFilePairWorker(file_pair, new_base_name, working_directory)
    
    def create_delete_file_pair_worker(
        self, file_pair: FilePair
    ) -> DeleteFilePairWorkerInterface:
        from src.ui.delegates.workers import DeleteFilePairWorker
        return DeleteFilePairWorker(file_pair)
    
    def create_move_file_pair_worker(
        self, file_pair: FilePair, target_directory: str
    ) -> MoveFilePairWorkerInterface:
        from src.ui.delegates.workers import MoveFilePairWorker
        return MoveFilePairWorker(file_pair, target_directory)