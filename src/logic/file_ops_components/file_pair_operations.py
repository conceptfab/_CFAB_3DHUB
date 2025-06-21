"""
FilePairOperations - operacje na parach plików.
Wydzielone z file_operations.py dla lepszej separacji odpowiedzialności.
"""

import logging
import os
from typing import Optional

from src.interfaces.worker_interface import (
    DeleteFilePairWorkerInterface,
    ManuallyPairFilesWorkerInterface,
    MoveFilePairWorkerInterface,
    RenameFilePairWorkerInterface,
)
from src.logic.file_ops_components.worker_factory import get_worker_factory
from src.models.file_pair import FilePair
from src.utils.path_utils import normalize_path


class FilePairOperations:
    """
    Klasa odpowiedzialna za operacje na parach plików - parowanie, zmiana nazwy, przenoszenie, usuwanie.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.worker_factory = get_worker_factory()

    def manually_pair_files(
        self, archive_path: str, preview_path: str, working_directory: str
    ) -> Optional[ManuallyPairFilesWorkerInterface]:
        """
        Ręcznie paruje pliki archiwum z plikiem podglądu.

        Args:
            archive_path: Ścieżka do pliku archiwum
            preview_path: Ścieżka do pliku podglądu
            working_directory: Katalog roboczy

        Returns:
            Worker lub None w przypadku błędu walidacji
        """
        self.logger.info("Żądanie ręcznego parowania plików")

        # Podstawowa walidacja parametrów
        if not archive_path or not preview_path or not working_directory:
            self.logger.warning("Brakujące ścieżki dla parowania plików")
            return None

        # Sprawdź czy pliki istnieją
        if not os.path.exists(archive_path):
            self.logger.warning(f"Plik archiwum nie istnieje: {archive_path}")
            return None

        if not os.path.exists(preview_path):
            self.logger.warning(f"Plik podglądu nie istnieje: {preview_path}")
            return None

        # Utwórz worker przez fabrykę
        worker = self.worker_factory.create_manually_pair_files_worker(
            archive_path, preview_path, working_directory
        )

        if worker:
            self.logger.debug("Worker utworzony dla ręcznego parowania")

        return worker

    def create_pair_from_files(
        self, archive_path: str, preview_path: str
    ) -> Optional[ManuallyPairFilesWorkerInterface]:
        """
        Tworzy parę plików z podanych ścieżek (wrapper dla manually_pair_files).

        Args:
            archive_path: Ścieżka do pliku archiwum
            preview_path: Ścieżka do pliku podglądu

        Returns:
            Worker lub None w przypadku błędu
        """
        self.logger.info("Tworzenie pary z plików")

        # Normalizuj ścieżki
        archive_path_norm = normalize_path(archive_path)
        preview_path_norm = normalize_path(preview_path)

        # Określ katalog roboczy na podstawie archiwum
        working_directory = os.path.dirname(archive_path_norm)

        # Deleguj do manually_pair_files
        return self.manually_pair_files(
            archive_path_norm, preview_path_norm, working_directory
        )

    def rename_file_pair(
        self, file_pair: FilePair, new_base_name: str, working_directory: str
    ) -> Optional[RenameFilePairWorkerInterface]:
        """
        Zmienia nazwę pary plików.

        Args:
            file_pair: Para plików do zmiany nazwy
            new_base_name: Nowa nazwa bazowa
            working_directory: Katalog roboczy

        Returns:
            Worker lub None w przypadku błędu walidacji
        """
        self.logger.info(f"Żądanie zmiany nazwy pary: {new_base_name}")

        # Walidacja obiektu FilePair
        if not file_pair or not file_pair.archive_path or not file_pair.preview_path:
            self.logger.warning("Nieprawidłowy obiekt FilePair")
            return None

        # Walidacja nowej nazwy
        if not new_base_name or not new_base_name.strip():
            self.logger.warning("Nowa nazwa bazowa nie może być pusta")
            return None

        # Sprawdź czy pliki istnieją
        if not os.path.exists(file_pair.archive_path):
            self.logger.warning(f"Plik archiwum nie istnieje: {file_pair.archive_path}")
            return None

        if not os.path.exists(file_pair.preview_path):
            self.logger.warning(f"Plik podglądu nie istnieje: {file_pair.preview_path}")
            return None

        # Utwórz worker przez fabrykę
        worker = self.worker_factory.create_rename_file_pair_worker(
            file_pair, new_base_name, working_directory
        )

        if worker:
            self.logger.debug(f"Worker utworzony dla zmiany nazwy: {new_base_name}")

        return worker

    def delete_file_pair(
        self, file_pair: FilePair
    ) -> Optional[DeleteFilePairWorkerInterface]:
        """
        Usuwa parę plików.

        Args:
            file_pair: Para plików do usunięcia

        Returns:
            Worker lub None w przypadku błędu walidacji
        """
        self.logger.info(f"Żądanie usunięcia pary: {file_pair.base_name}")

        # Walidacja obiektu FilePair
        if not file_pair or not file_pair.archive_path or not file_pair.preview_path:
            self.logger.warning("Nieprawidłowy obiekt FilePair do usunięcia")
            return None

        # Utwórz worker przez fabrykę
        worker = self.worker_factory.create_delete_file_pair_worker(file_pair)

        if worker:
            self.logger.debug(f"Worker utworzony dla usunięcia: {file_pair.base_name}")

        return worker

    def move_file_pair(
        self, file_pair: FilePair, new_target_directory: str
    ) -> Optional[MoveFilePairWorkerInterface]:
        """
        Przenosi parę plików do nowego katalogu.

        Args:
            file_pair: Para plików do przeniesienia
            new_target_directory: Katalog docelowy

        Returns:
            Worker lub None w przypadku błędu walidacji
        """
        self.logger.info(f"Żądanie przeniesienia pary do: {new_target_directory}")

        # Walidacja obiektu FilePair
        if not file_pair or not file_pair.archive_path:
            self.logger.warning("Nieprawidłowy obiekt FilePair do przeniesienia")
            return None

        # Walidacja katalogu docelowego
        if not new_target_directory or not new_target_directory.strip():
            self.logger.warning("Katalog docelowy nie może być pusty")
            return None

        normalized_target_dir = normalize_path(new_target_directory)

        if not os.path.isdir(normalized_target_dir):
            self.logger.warning(
                f"Katalog docelowy nie istnieje: {normalized_target_dir}"
            )
            return None

        # Utwórz worker przez fabrykę
        worker = self.worker_factory.create_move_file_pair_worker(
            file_pair, normalized_target_dir
        )

        if worker:
            self.logger.debug("Worker utworzony dla przeniesienia pary")

        return worker
