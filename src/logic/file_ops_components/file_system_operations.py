"""
FileSystemOperations - operacje na systemie plików (foldery).
Wydzielone z file_operations.py dla lepszej separacji odpowiedzialności.
"""

import logging
import os
from typing import Optional

from src.interfaces.worker_interface import (
    CreateFolderWorkerInterface,
    DeleteFolderWorkerInterface,
    RenameFolderWorkerInterface,
)
from src.logic.file_ops_components.worker_factory import get_worker_factory
from src.utils.path_utils import is_valid_filename, normalize_path


class FileSystemOperations:
    """
    Klasa odpowiedzialna za operacje na systemie plików - tworzenie, usuwanie, zmiana nazw folderów.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.worker_factory = get_worker_factory()

    def create_folder(
        self, parent_directory: str, folder_name: str
    ) -> Optional[CreateFolderWorkerInterface]:
        """
        Tworzy nowy folder w podanej lokalizacji.

        Args:
            parent_directory: Ścieżka do katalogu nadrzędnego
            folder_name: Nazwa nowego folderu

        Returns:
            Worker lub None w przypadku błędu walidacji
        """
        self.logger.info(f"Żądanie utworzenia folderu: {folder_name}")

        # Normalizacja ścieżki katalogu nadrzędnego
        parent_dir_normalized = normalize_path(parent_directory)

        # Walidacja katalogu nadrzędnego
        if not os.path.isdir(parent_dir_normalized):
            self.logger.warning(
                f"Katalog nadrzędny nie istnieje: {parent_dir_normalized}"
            )
            return None

        # Walidacja nazwy folderu
        if not is_valid_filename(folder_name):
            self.logger.warning(f"Nieprawidłowa nazwa folderu: {folder_name}")
            return None

        # Sprawdź czy folder już nie istnieje
        new_folder_path = os.path.join(parent_dir_normalized, folder_name)
        if os.path.exists(new_folder_path):
            self.logger.warning(f"Folder już istnieje: {new_folder_path}")
            return None

        # Utwórz worker przez fabrykę
        worker = self.worker_factory.create_folder_worker(
            parent_dir_normalized, folder_name
        )

        if worker:
            self.logger.debug(f"Worker utworzony dla folderu: {folder_name}")

        return worker

    def rename_folder(
        self, folder_path: str, new_folder_name: str
    ) -> Optional[RenameFolderWorkerInterface]:
        """
        Zmienia nazwę istniejącego folderu.

        Args:
            folder_path: Aktualna ścieżka do folderu
            new_folder_name: Nowa nazwa folderu

        Returns:
            Worker lub None w przypadku błędu walidacji
        """
        self.logger.info(f"Żądanie zmiany nazwy folderu: {new_folder_name}")

        # Normalizacja ścieżki folderu
        folder_path_normalized = normalize_path(folder_path)

        # Walidacja istniejącego folderu
        if not os.path.isdir(folder_path_normalized):
            self.logger.warning(f"Folder nie istnieje: {folder_path_normalized}")
            return None

        # Walidacja nowej nazwy
        if not is_valid_filename(new_folder_name):
            self.logger.warning(f"Nieprawidłowa nowa nazwa folderu: {new_folder_name}")
            return None

        # Sprawdź konflikty nazw
        parent_dir = os.path.dirname(folder_path_normalized)
        new_folder_path = normalize_path(os.path.join(parent_dir, new_folder_name))

        if os.path.exists(new_folder_path):
            self.logger.warning(f"Folder o tej nazwie już istnieje: {new_folder_path}")
            return None

        # Utwórz worker przez fabrykę
        worker = self.worker_factory.create_rename_folder_worker(
            folder_path_normalized, new_folder_name
        )

        if worker:
            self.logger.debug(f"Worker utworzony dla zmiany nazwy: {new_folder_name}")

        return worker

    def delete_folder(
        self, folder_path: str, delete_content: bool = False
    ) -> Optional[DeleteFolderWorkerInterface]:
        """
        Usuwa folder (opcjonalnie z zawartością).

        Args:
            folder_path: Ścieżka do folderu do usunięcia
            delete_content: Czy usunąć folder z zawartością

        Returns:
            Worker lub None w przypadku błędu walidacji
        """
        self.logger.info(f"Żądanie usunięcia folderu, z zawartością: {delete_content}")

        folder_path_normalized = normalize_path(folder_path)

        # Podstawowa walidacja bezpieczeństwa - nie usuwamy głównych katalogów
        if self._is_critical_system_path(folder_path_normalized):
            self.logger.error(
                f"Próba usunięcia krytycznego katalogu: {folder_path_normalized}"
            )
            return None

        # Utwórz worker przez fabrykę
        worker = self.worker_factory.create_delete_folder_worker(
            folder_path_normalized, delete_content
        )

        if worker:
            self.logger.debug("Worker utworzony dla usuwania folderu")

        return worker

    def _is_critical_system_path(self, path: str) -> bool:
        """
        Sprawdza czy ścieżka to krytyczny katalog systemowy.

        Args:
            path: Ścieżka do sprawdzenia

        Returns:
            True jeśli to krytyczny katalog systemowy
        """
        # Podstawowe sprawdzenia bezpieczeństwa
        path_abs = os.path.abspath(path)

        # Root dysku Windows (C:\, D:\, etc.)
        if os.name == "nt" and len(path_abs) <= 3 and path_abs.endswith(":\\"):
            return True

        # Root systemu Unix-like (/)
        if os.name != "nt" and path_abs == "/":
            return True

        # Katalogi systemowe Windows
        if os.name == "nt":
            system_dirs = [
                "C:\\Windows",
                "C:\\Program Files",
                "C:\\Program Files (x86)",
            ]
            for sys_dir in system_dirs:
                if path_abs.lower().startswith(sys_dir.lower()):
                    return True

        return False
