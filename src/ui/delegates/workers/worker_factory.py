"""
Fabryka workerów - umożliwia tworzenie odpowiednich workerów bez bezpośredniego importowania ich klas.
"""

import logging
from PyQt6.QtCore import QThreadPool

from .base_workers import UnifiedBaseWorker, TransactionalWorker, WorkerPriority
from .folder_workers import CreateFolderWorker, RenameFolderWorker, DeleteFolderWorker
from .file_workers import (
    ManuallyPairFilesWorker,
    RenameFilePairWorker,
    DeleteFilePairWorker,
    MoveFilePairWorker,
)
from .bulk_workers import BulkDeleteWorker, BulkMoveWorker
from .processing_workers import (
    ThumbnailGenerationWorker,
    BatchThumbnailWorker,
    SaveMetadataWorker,
)
from .scan_workers import ScanFolderWorker

from src.models.file_pair import FilePair

logger = logging.getLogger(__name__)


class WorkerFactory:
    """
    Fabryka do tworzenia różnych workerów.
    
    Dostarcza metody tworzące workery z odpowiednimi parametrami,
    co eliminuje potrzebę bezpośredniego importowania klas workerów.
    """

    @staticmethod
    def create_folder_worker(
        parent_directory: str, folder_name: str
    ) -> UnifiedBaseWorker:
        """Tworzy worker do tworzenia folderów."""
        return CreateFolderWorker(parent_directory, folder_name)

    @staticmethod
    def create_rename_folder_worker(
        folder_path: str, new_folder_name: str
    ) -> UnifiedBaseWorker:
        """Tworzy worker do zmiany nazwy folderu."""
        return RenameFolderWorker(folder_path, new_folder_name)

    @staticmethod
    def create_delete_folder_worker(
        folder_path: str, delete_content: bool
    ) -> UnifiedBaseWorker:
        """Tworzy worker do usuwania folderu."""
        return DeleteFolderWorker(folder_path, delete_content)

    @staticmethod
    def create_manually_pair_files_worker(
        archive_path: str, preview_path: str, working_directory: str
    ) -> UnifiedBaseWorker:
        """Tworzy worker do ręcznego parowania plików."""
        return ManuallyPairFilesWorker(archive_path, preview_path, working_directory)

    @staticmethod
    def create_rename_file_pair_worker(
        file_pair: FilePair, new_base_name: str, working_directory: str
    ) -> TransactionalWorker:
        """Tworzy worker do zmiany nazwy pary plików."""
        return RenameFilePairWorker(file_pair, new_base_name, working_directory)

    @staticmethod
    def create_delete_file_pair_worker(file_pair: FilePair) -> UnifiedBaseWorker:
        """Tworzy worker do usuwania pary plików."""
        return DeleteFilePairWorker(file_pair)

    @staticmethod
    def create_move_file_pair_worker(
        file_pair: FilePair, new_target_directory: str
    ) -> TransactionalWorker:
        """Tworzy worker do przenoszenia pary plików."""
        return MoveFilePairWorker(file_pair, new_target_directory)

    @staticmethod
    def create_bulk_delete_worker(file_pairs: list[FilePair]) -> UnifiedBaseWorker:
        """Tworzy worker do masowego usuwania plików."""
        return BulkDeleteWorker(file_pairs)

    @staticmethod
    def create_bulk_move_worker(
        file_pairs: list[FilePair], destination_dir: str
    ) -> UnifiedBaseWorker:
        """Tworzy worker do masowego przenoszenia plików."""
        return BulkMoveWorker(file_pairs, destination_dir)

    @staticmethod
    def create_thumbnail_worker(
        path: str, width: int, height: int, priority: int = WorkerPriority.NORMAL
    ) -> ThumbnailGenerationWorker:
        """
        Tworzy worker do generowania miniaturek z odpowiednim priorytetem.

        Args:
            path: Ścieżka do pliku
            width: Szerokość miniaturki
            height: Wysokość miniaturki
            priority: Priorytet workera (LOW/NORMAL/HIGH)

        Returns:
            Worker do generowania miniaturek
        """
        worker = ThumbnailGenerationWorker(path, width, height)
        thread_pool = QThreadPool.globalInstance()
        
        # Ustaw priorytet workera
        if priority == WorkerPriority.LOW:
            worker.setAutoDelete(True)
            thread_pool.setExpiryTimeout(10000)  # 10 sekund na usunięcie workerów
        elif priority == WorkerPriority.HIGH:
            # Dla wysokiego priorytetu daj większe szanse na wykonanie
            worker.setAutoDelete(True)
            worker.setProperty("priority", 1)  # Wyższy priorytet
        
        return worker

    @staticmethod
    def create_batch_thumbnail_worker(
        thumbnail_requests: list[tuple[str, int, int]]
    ) -> BatchThumbnailWorker:
        """
        Tworzy worker do wsadowego generowania miniaturek.

        Args:
            thumbnail_requests: Lista krotek (ścieżka, szerokość, wysokość)

        Returns:
            Worker do wsadowego generowania miniaturek
        """
        return BatchThumbnailWorker(thumbnail_requests)

    @staticmethod
    def create_scan_folder_worker(directory=None) -> UnifiedBaseWorker:
        """Tworzy worker do skanowania folderu."""
        return ScanFolderWorker(directory)

    @staticmethod
    def create_save_metadata_worker(
        working_directory: str,
        file_pairs: list[FilePair],
        unpaired_archives: list[str] = None,
        unpaired_previews: list[str] = None,
    ) -> UnifiedBaseWorker:
        """Tworzy worker do zapisywania metadanych."""
        return SaveMetadataWorker(
            working_directory, file_pairs, unpaired_archives, unpaired_previews
        ) 