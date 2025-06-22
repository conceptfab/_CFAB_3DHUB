"""
SpecialFoldersManager - wydzielony manager do obsługi specjalnych folderów.
Rozdziela odpowiedzialności z MainWindowController.
"""

import logging
import os
from typing import List

from src.logic.metadata_manager import MetadataManager
from src.models.special_folder import SpecialFolder


class SpecialFoldersManager:
    """
    Manager odpowiedzialny za obsługę specjalnych folderów.
    Wydzielony z głównego kontrolera dla lepszej separacji odpowiedzialności.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def get_special_folders_from_metadata(
        self, directory_path: str
    ) -> List[SpecialFolder]:
        """
        Pobiera specjalne foldery z metadanych dla danego katalogu.

        Args:
            directory_path: Ścieżka do katalogu głównego

        Returns:
            Lista obiektów SpecialFolder
        """
        try:
            metadata_manager = MetadataManager.get_instance(directory_path)

            if not metadata_manager.has_special_folders():
                return []

            special_folder_names = metadata_manager.get_special_folders()
            special_folders = []

            for folder_name in special_folder_names:
                folder_path = os.path.join(directory_path, folder_name)
                if os.path.exists(folder_path) and os.path.isdir(folder_path):
                    special_folder = SpecialFolder(folder_path, directory_path)
                    special_folders.append(special_folder)
                else:
                    self.logger.warning(
                        f"Specjalny folder z metadanych nie istnieje fizycznie: "
                        f"{folder_name}"
                    )

            self.logger.debug(
                f"Pobrano {len(special_folders)} specjalnych folderów z metadanych"
            )
            return special_folders

        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania specjalnych folderów: {str(e)}")
            return []

    def ensure_tex_folder_in_metadata(self, directory_path: str) -> List[SpecialFolder]:
        """
        Sprawdza czy folder 'tex' istnieje fizycznie i dodaje go do metadanych jeśli trzeba.
        Tymczasowe rozwiązanie dla kompatybilności.

        Args:
            directory_path: Ścieżka do katalogu głównego

        Returns:
            Lista obiektów SpecialFolder po aktualizacji
        """
        try:
            from src.logic import metadata_manager

            special_folder_names = metadata_manager.get_special_folders(directory_path)
            tex_folder_path = os.path.join(directory_path, "tex")

            # Dodaj folder tex jeśli istnieje fizycznie ale nie ma go w metadanych
            if os.path.isdir(tex_folder_path) and "tex" not in special_folder_names:
                special_folder_names.append("tex")
                metadata_manager.add_special_folder(directory_path, "tex")
                self.logger.debug("Dodano folder tex do metadanych (awaryjnie)")

            # Utwórz obiekty SpecialFolder
            special_folders = []
            for folder_name in special_folder_names:
                folder_path_full = os.path.join(directory_path, folder_name)

                if os.path.isdir(folder_path_full):
                    special_folder = SpecialFolder(folder_name, folder_path_full)
                    special_folders.append(special_folder)
                    self.logger.debug(f"Utworzono obiekt SpecialFolder: {folder_name}")

            return special_folders

        except Exception as e:
            self.logger.error(f"Błąd podczas sprawdzania folderu tex: {str(e)}")
            return []

    def create_special_folders_from_names(
        self, directory_path: str, folder_names: List[str]
    ) -> List[SpecialFolder]:
        """
        Tworzy obiekty SpecialFolder na podstawie listy nazw folderów.

        Args:
            directory_path: Ścieżka do katalogu głównego
            folder_names: Lista nazw folderów

        Returns:
            Lista obiektów SpecialFolder
        """
        special_folders = []

        for folder_name in folder_names:
            folder_path = os.path.join(directory_path, folder_name)
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                special_folder = SpecialFolder(folder_path, directory_path)
                special_folders.append(special_folder)
            else:
                self.logger.warning(f"Folder specjalny nie istnieje: {folder_name}")

        return special_folders
