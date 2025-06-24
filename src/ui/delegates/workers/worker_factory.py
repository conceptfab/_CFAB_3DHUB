"""
Fabryka workerów - umożliwia tworzenie odpowiednich workerów bez bezpośredniego importowania ich klas.
"""

import logging
from typing import Optional

from PyQt6.QtCore import QThreadPool

from src.models.file_pair import FilePair

from .base_workers import TransactionalWorker, UnifiedBaseWorker, WorkerPriority
from .bulk_workers import BulkDeleteWorker, BulkMoveWorker
from .file_workers import (
    DeleteFilePairWorker,
    ManuallyPairFilesWorker,
    MoveFilePairWorker,
    RenameFilePairWorker,
)
from .folder_workers import CreateFolderWorker, DeleteFolderWorker, RenameFolderWorker
from .processing_workers import (
    BatchThumbnailWorker,
    SaveMetadataWorker,
    ThumbnailGenerationWorker,
)
from .scan_workers import ScanFolderWorker

logger = logging.getLogger(__name__)


class WorkerFactory:
    """
    Fabryka do tworzenia różnych workerów z zaawansowanymi opcjami.

    Dostarcza metody tworzące workery z odpowiednimi parametrami,
    obsługuje priorytetyzację, timeout'y i batch operations.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje fabrykę workerów.

        Args:
            main_window: Referencja do głównego okna aplikacji.
        """
        self.main_window = main_window

    @staticmethod
    def create_folder_worker(
        parent_directory: str,
        folder_name: str,
        timeout_seconds: int = 60,
        priority: int = WorkerPriority.NORMAL,
    ) -> UnifiedBaseWorker:
        """Tworzy worker do tworzenia folderów z opcjami timeout i priorytetu."""
        worker = CreateFolderWorker(parent_directory, folder_name)
        worker._timeout_seconds = timeout_seconds
        worker._priority = priority
        return worker

    @staticmethod
    def create_rename_folder_worker(
        folder_path: str,
        new_folder_name: str,
        timeout_seconds: int = 60,
        priority: int = WorkerPriority.NORMAL,
    ) -> UnifiedBaseWorker:
        """Tworzy worker do zmiany nazwy folderu z opcjami timeout i priorytetu."""
        worker = RenameFolderWorker(folder_path, new_folder_name)
        worker._timeout_seconds = timeout_seconds
        worker._priority = priority
        return worker

    @staticmethod
    def create_delete_folder_worker(
        folder_path: str,
        delete_content: bool,
        timeout_seconds: int = 120,
        priority: int = WorkerPriority.NORMAL,
    ) -> UnifiedBaseWorker:
        """Tworzy worker do usuwania folderu z opcjami timeout i priorytetu."""
        worker = DeleteFolderWorker(folder_path, delete_content)
        worker._timeout_seconds = timeout_seconds
        worker._priority = priority
        return worker

    @staticmethod
    def create_manually_pair_files_worker(
        archive_path: str,
        preview_path: str,
        working_directory: str,
        timeout_seconds: int = 30,
        priority: int = WorkerPriority.HIGH,
    ) -> UnifiedBaseWorker:
        """Tworzy worker do ręcznego parowania plików z wysokim priorytetem."""
        worker = ManuallyPairFilesWorker(archive_path, preview_path, working_directory)
        worker._timeout_seconds = timeout_seconds
        worker._priority = priority
        return worker

    @staticmethod
    def create_rename_file_pair_worker(
        file_pair: FilePair,
        new_base_name: str,
        working_directory: str,
        timeout_seconds: int = 60,
        priority: int = WorkerPriority.NORMAL,
    ) -> TransactionalWorker:
        """Tworzy worker do zmiany nazwy pary plików z rollback."""
        worker = RenameFilePairWorker(file_pair, new_base_name, working_directory)
        worker._timeout_seconds = timeout_seconds
        worker._priority = priority
        return worker

    @staticmethod
    def create_delete_file_pair_worker(
        file_pair: FilePair,
        timeout_seconds: int = 30,
        priority: int = WorkerPriority.NORMAL,
    ) -> UnifiedBaseWorker:
        """Tworzy worker do usuwania pary plików."""
        worker = DeleteFilePairWorker(file_pair)
        worker._timeout_seconds = timeout_seconds
        worker._priority = priority
        return worker

    @staticmethod
    def create_move_file_pair_worker(
        file_pair: FilePair,
        new_target_directory: str,
        timeout_seconds: int = 60,
        priority: int = WorkerPriority.NORMAL,
    ) -> TransactionalWorker:
        """Tworzy worker do przenoszenia pary plików z rollback."""
        worker = MoveFilePairWorker(file_pair, new_target_directory)
        worker._timeout_seconds = timeout_seconds
        worker._priority = priority
        return worker

    @staticmethod
    def create_bulk_delete_worker(
        file_pairs: list[FilePair],
        batch_size: int = 20,
        timeout_seconds: int = 300,
        priority: int = WorkerPriority.NORMAL,
    ) -> UnifiedBaseWorker:
        """Tworzy worker do masowego usuwania plików z batch processing."""
        return BulkDeleteWorker(file_pairs, batch_size)

    @staticmethod
    def create_bulk_move_worker(
        file_pairs: list[FilePair],
        destination_dir: str,
        batch_size: int = 15,
        timeout_seconds: int = 600,
        priority: int = WorkerPriority.NORMAL,
    ) -> UnifiedBaseWorker:
        """Tworzy worker do masowego przenoszenia plików z batch processing."""
        return BulkMoveWorker(file_pairs, destination_dir, batch_size)

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
            priority: Priorytet workera (LOW/NORMAL/HIGH/CRITICAL)

        Returns:
            Worker do generowania miniaturek z automatycznym timeout 30s
        """
        worker = ThumbnailGenerationWorker(path, width, height, priority)

        # Ustaw priorytet w QThreadPool
        thread_pool = QThreadPool.globalInstance()

        if priority == WorkerPriority.LOW:
            worker.setAutoDelete(True)
            thread_pool.setExpiryTimeout(10000)  # 10 sekund na usunięcie workerów
        elif priority == WorkerPriority.HIGH:
            # Dla wysokiego priorytetu daj większe szanse na wykonanie
            worker.setAutoDelete(True)
            worker.setProperty("priority", 1)  # Wyższy priorytet
        elif priority == WorkerPriority.CRITICAL:
            # Krytyczny priorytet - natychmiastowe wykonanie
            worker.setAutoDelete(True)
            worker.setProperty("priority", 2)  # Najwyższy priorytet

        return worker

    @staticmethod
    def create_batch_thumbnail_worker(
        thumbnail_requests: list[tuple[str, int, int]],
        priority: int = WorkerPriority.HIGH,
    ) -> BatchThumbnailWorker:
        """
        Tworzy worker do wsadowego generowania miniaturek.

        Args:
            thumbnail_requests: Lista krotek (ścieżka, szerokość, wysokość)
            priority: Priorytet workera (domyślnie HIGH dla batch operations)

        Returns:
            Worker do wsadowego generowania miniaturek z timeout 5 minut
        """
        return BatchThumbnailWorker(thumbnail_requests, priority)

    @staticmethod
    def create_scan_folder_worker(
        directory=None, timeout_seconds: int = 300, priority: int = WorkerPriority.HIGH
    ) -> UnifiedBaseWorker:
        """Tworzy worker do skanowania folderu z wysokim priorytetem."""
        worker = ScanFolderWorker(directory)
        worker._timeout_seconds = timeout_seconds
        worker._priority = priority
        return worker

    @staticmethod
    def create_save_metadata_worker(
        working_directory: str,
        file_pairs: list[FilePair],
        unpaired_archives: list[str] = None,
        unpaired_previews: list[str] = None,
        timeout_seconds: int = 120,
        priority: int = WorkerPriority.HIGH,
    ) -> UnifiedBaseWorker:
        """Tworzy worker do zapisywania metadanych z wysokim priorytetem."""
        return SaveMetadataWorker(
            working_directory, file_pairs, unpaired_archives, unpaired_previews
        )

    @staticmethod
    def get_optimal_batch_size(operation_type: str, item_count: int) -> int:
        """
        Zwraca optymalny rozmiar batch'a dla danego typu operacji.

        Args:
            operation_type: Typ operacji ('delete', 'move', 'thumbnail')
            item_count: Liczba elementów do przetworzenia

        Returns:
            Optymalny rozmiar batch'a
        """
        if operation_type == "delete":
            # Dla usuwania - większe batch'e są szybsze
            if item_count < 50:
                return 10
            elif item_count < 10000:
                return 20
            else:
                return 30

        elif operation_type == "move":
            # Dla przenoszenia - średnie batch'e (I/O intensive)
            if item_count < 30:
                return 5
            elif item_count < 100:
                return 15
            else:
                return 25

        elif operation_type == "thumbnail":
            # Dla miniaturek - małe batch'e (CPU intensive)
            if item_count < 20:
                return 3
            elif item_count < 100:
                return 8
            else:
                return 15

        # Domyślny rozmiar
        return 10

    @staticmethod
    def get_recommended_timeout(operation_type: str, item_count: int) -> int:
        """
        Zwraca rekomendowany timeout dla danego typu operacji.

        Args:
            operation_type: Typ operacji
            item_count: Liczba elementów do przetworzenia

        Returns:
            Timeout w sekundach
        """
        base_timeouts = {
            "thumbnail": 30,  # 30s na miniaturkę
            "delete": 5,  # 5s na usunięcie
            "move": 10,  # 10s na przeniesienie
            "metadata": 60,  # 60s na metadane
            "scan": 120,  # 2 minuty na skanowanie
            "folder_ops": 30,  # 30s na operacje folderowe
        }

        base_timeout = base_timeouts.get(operation_type, 60)

        # Skaluj timeout z liczbą elementów
        if operation_type in ["thumbnail", "delete", "move"]:
            return max(base_timeout, item_count * base_timeout // 10)
        else:
            return base_timeout

    @staticmethod
    def create_optimized_bulk_worker(
        operation_type: str,
        file_pairs: list[FilePair],
        destination_dir: str = None,
        priority: int = WorkerPriority.NORMAL,
    ) -> UnifiedBaseWorker:
        """
        Tworzy zoptymalizowany bulk worker z automatycznym doborem parametrów.

        Args:
            operation_type: 'delete' lub 'move'
            file_pairs: Lista par plików
            destination_dir: Katalog docelowy (dla move)
            priority: Priorytet operacji

        Returns:
            Zoptymalizowany worker
        """
        item_count = len(file_pairs)
        optimal_batch_size = WorkerFactory.get_optimal_batch_size(
            operation_type, item_count
        )
        timeout = WorkerFactory.get_recommended_timeout(operation_type, item_count)

        if operation_type == "delete":
            return BulkDeleteWorker(file_pairs, optimal_batch_size)
        elif operation_type == "move" and destination_dir:
            return BulkMoveWorker(file_pairs, destination_dir, optimal_batch_size)
        else:
            raise ValueError(f"Nieobsługiwany typ operacji: {operation_type}")

    def create_worker(
        self, worker_class, *args, **kwargs
    ) -> Optional[UnifiedBaseWorker]:
        """
        Tworzy instancję workera i ustawia jego zależności.

        Args:
            worker_class: Klasa workera
            *args: Pozycyjne argumenty do przekazania do konstruktora
            **kwargs: Argumenty nazwane do przekazania do konstruktora

        Returns:
            Utworzony worker lub None, jeśli worker nie został utworzony
        """
        try:
            worker = worker_class(*args, **kwargs)
            if isinstance(worker, UnifiedBaseWorker):
                worker._main_window = self.main_window
                return worker
            else:
                logger.warning(
                    f"Worker {worker_class.__name__} nie jest instancją UnifiedBaseWorker"
                )
                return None
        except Exception as e:
            logger.error(f"Błąd podczas tworzenia workera {worker_class.__name__}: {e}")
            return None
