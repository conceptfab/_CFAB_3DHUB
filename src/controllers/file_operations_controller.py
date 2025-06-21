"""
Controller zarządzający operacjami na plikach.
Centralny punkt dla wszystkich operacji na plikach w aplikacji.
"""

import logging
import os
from typing import List, Optional

import src.logic.file_operations as file_operations
from src.factories.worker_factory import UIWorkerFactory
from src.logic.scanner import collect_files, create_file_pairs
from src.models.file_pair import FilePair

logger = logging.getLogger(__name__)


class FileOperationsController:
    """Controller obsługujący wszystkie operacje na plikach"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.worker_factory = UIWorkerFactory()

    def rename_file_pair(
        self, file_pair: FilePair, new_name: str, working_directory: str
    ):
        """
        Rozpoczyna proces zmiany nazwy dla pary plików przy użyciu workera.

        Args:
            file_pair: Para plików do zmiany nazwy
            new_name: Nowa nazwa (bez rozszerzenia)
            working_directory: Katalog roboczy

        Returns:
            Worker dla operacji zmiany nazwy lub None w przypadku błędu
        """
        return file_operations.rename_file_pair(
            file_pair, new_name, working_directory, self.worker_factory
        )

    def delete_file_pair(self, file_pair: FilePair):
        """
        Usuwa parę plików przy użyciu workera.

        Args:
            file_pair: Para plików do usunięcia

        Returns:
            Worker dla operacji usuwania lub None w przypadku błędu
        """
        return file_operations.delete_file_pair(file_pair, self.worker_factory)

    def move_file_pair(self, file_pair: FilePair, target_folder_path: str):
        """
        Przenosi parę plików do nowego folderu przy użyciu workera.

        Args:
            file_pair: Para plików do przeniesienia
            target_folder_path: Ścieżka do folderu docelowego

        Returns:
            Worker dla operacji przenoszenia lub None w przypadku błędu
        """
        return file_operations.move_file_pair(
            file_pair, target_folder_path, self.worker_factory
        )

    def manually_pair_files(
        self, archive_path: str, preview_path: str, working_directory: str
    ):
        """
        Ręcznie paruje pliki przy użyciu workera.

        Args:
            archive_path: Ścieżka do pliku archiwum
            preview_path: Ścieżka do pliku podglądu
            working_directory: Katalog roboczy

        Returns:
            Worker dla operacji parowania lub None w przypadku błędu
        """
        return file_operations.manually_pair_files(
            archive_path, preview_path, working_directory, self.worker_factory
        )

    def move_files(self, files: List[str], target_dir: str) -> bool:
        """
        Centralna metoda do przenoszenia plików z automatycznym parowaniem.

        Args:
            files: Lista ścieżek plików do przeniesienia
            target_dir: Katalog docelowy

        Returns:
            True jeśli operacja się powiodła, False w przeciwnym przypadku
        """
        try:
            # Zbierz wszystkie pliki z podanych ścieżek
            all_files = []
            for file_path in files:
                if os.path.isfile(file_path):
                    all_files.append(file_path)
                elif os.path.isdir(file_path):
                    # Zbierz pliki z katalogu
                    dir_file_map = collect_files(file_path, max_depth=1)
                    for files_list in dir_file_map.values():
                        all_files.extend(files_list)

            if not all_files:
                logger.warning("Nie znaleziono plików do przeniesienia")
                return False

            # Utwórz tymczasowy file_map dla algorytmu create_file_pairs
            temp_file_map = {}
            for file_path in all_files:
                dir_path = os.path.dirname(file_path)
                if dir_path not in temp_file_map:
                    temp_file_map[dir_path] = []
                temp_file_map[dir_path].append(file_path)

            # Utwórz pary plików używając strategii "best_match"
            file_pairs, _ = create_file_pairs(
                temp_file_map,
                target_dir,
                pair_strategy="best_match",
            )

            logger.info(f"Utworzono {len(file_pairs)} par plików do przeniesienia")
            return True

        except Exception as e:
            logger.error(f"Błąd podczas przenoszenia plików: {e}")
            return False

    def scan_folder_for_pairs(self, folder_path: str):
        """
        Skanuje folder w poszukiwaniu par plików.

        Args:
            folder_path: Ścieżka do folderu do przeskanowania
        """
        # To będzie delegowane do odpowiedniego serwisu skanowania
        from src.logic.scanner import scan_folder_for_pairs

        return scan_folder_for_pairs(folder_path)
