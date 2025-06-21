"""
SelectionManager - wydzielony manager do zarządzania selekcją kafelków.
Rozdziela odpowiedzialności z MainWindowController.
"""

import logging
from typing import Set

from src.models.file_pair import FilePair


class SelectionManager:
    """
    Manager odpowiedzialny za zarządzanie selekcją kafelków w galerii.
    Wydzielony z głównego kontrolera dla lepszej separacji odpowiedzialności.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.selected_tiles: Set[FilePair] = set()

    def handle_tile_selection(self, file_pair: FilePair, is_selected: bool):
        """
        Obsługuje zaznaczanie/odznaczanie kafelków.

        Args:
            file_pair: Para plików
            is_selected: Czy kafelek ma być zaznaczony
        """
        if is_selected:
            self.selected_tiles.add(file_pair)
            self.logger.debug(f"Zaznaczono kafelek: {file_pair.archive_path}")
        else:
            self.selected_tiles.discard(file_pair)
            self.logger.debug(f"Odznaczono kafelek: {file_pair.archive_path}")

        self.logger.debug(f"Aktualnie zaznaczonych: {len(self.selected_tiles)}")

    def get_selected_pairs(self) -> list[FilePair]:
        """
        Zwraca listę aktualnie zaznaczonych par plików.

        Returns:
            Lista zaznaczonych par plików
        """
        return list(self.selected_tiles)

    def clear_selection(self):
        """
        Czyści całą selekcję.
        """
        self.selected_tiles.clear()
        self.logger.debug("Wyczyszczono selekcję kafelków")

    def get_selection_count(self) -> int:
        """
        Zwraca liczbę zaznaczonych kafelków.

        Returns:
            Liczba zaznaczonych kafelków
        """
        return len(self.selected_tiles)

    def is_selected(self, file_pair: FilePair) -> bool:
        """
        Sprawdza czy dana para plików jest zaznaczona.

        Args:
            file_pair: Para plików do sprawdzenia

        Returns:
            True jeśli para jest zaznaczona
        """
        return file_pair in self.selected_tiles

    def remove_pairs_from_selection(self, pairs_to_remove: list[FilePair]):
        """
        Usuwa określone pary z selekcji (np. po usunięciu plików).

        Args:
            pairs_to_remove: Lista par do usunięcia z selekcji
        """
        for pair in pairs_to_remove:
            self.selected_tiles.discard(pair)

        if pairs_to_remove:
            self.logger.debug(f"Usunięto {len(pairs_to_remove)} par z selekcji")
