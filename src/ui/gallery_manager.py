"""
Manager galerii - zarządzanie wyświetlaniem kafelków.
"""

import logging
import math
import os
from typing import Dict, List, Set

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QWidget

from src import app_config
from src.logic.filter_logic import filter_file_pairs
from src.models.file_pair import FilePair
from src.ui.widgets.file_tile_widget import FileTileWidget


class GalleryManager:
    """
    Klasa zarządzająca galerią kafelków.
    """

    def __init__(self, tiles_container: QWidget, tiles_layout: QGridLayout):
        self.tiles_container = tiles_container
        self.tiles_layout = tiles_layout
        self.gallery_tile_widgets: Dict[str, FileTileWidget] = {}
        self.file_pairs_list: List[FilePair] = []
        # Inicjalizuj current_thumbnail_size jako int, zgodnie z app_config
        self.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
        # Zapisz krotkę rozmiaru dla spójności interfejsu
        self._current_size_tuple = (
            self.current_thumbnail_size,
            self.current_thumbnail_size,
        )

    def clear_gallery(self):
        """
        Czyści galerię kafelków - usuwa wszystkie widgety z pamięci.
        """
        self.tiles_container.setUpdatesEnabled(False)
        try:
            # Usuń wszystkie widgety z layoutu
            while self.tiles_layout.count():
                item = self.tiles_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    # Usuń widget z layoutu, ale nie usuwaj go jeszcze z pamięci,
                    # jeśli jest w self.gallery_tile_widgets
                    widget.setVisible(False)
                    self.tiles_layout.removeWidget(widget)  # Jawne usunięcie

            # Usuń widgety ze słownika i pamięci
            for archive_path in list(
                self.gallery_tile_widgets.keys()
            ):  # Iteruj po kopii kluczy
                tile = self.gallery_tile_widgets.pop(archive_path)
                tile.setParent(None)
                tile.deleteLater()
            self.gallery_tile_widgets.clear()  # Upewnij się, że słownik jest pusty
        finally:
            self.tiles_container.setUpdatesEnabled(True)
            self.tiles_container.update()

    def create_tile_widget_for_pair(self, file_pair: FilePair, parent_widget):
        """
        Tworzy pojedynczy kafelek dla pary plików.
        """
        try:
            # Przekaż _current_size_tuple jako krotkę (width, height)
            tile = FileTileWidget(file_pair, self._current_size_tuple, parent_widget)
            # Ukryj na starcie, update_gallery_view zdecyduje o widoczności
            tile.setVisible(False)
            self.gallery_tile_widgets[file_pair.get_archive_path()] = tile
            return tile
        except Exception as e:
            logging.error(
                f"Błąd tworzenia kafelka dla {file_pair.get_base_name()}: {e}"
            )
            return None

    def update_gallery_view(self):
        """
        Aktualizuje widok galerii, pokazując/ukrywając istniejące kafelki
        i rozmieszczając je w siatce.
        Naprawiona wersja - rozwiązuje problem nakładania się i duplikowania kafelków.
        """
        # Wyłącz aktualizacje na czas przebudowy layoutu
        self.tiles_container.setUpdatesEnabled(False)

        try:
            # Jeśli lista par plików jest pusta, ukryj wszystkie kafelki i zakończ
            if not self.file_pairs_list:
                logging.debug(
                    "Lista par (po filtracji) pusta, ukrywanie wszystkich kafelków."
                )
                for tile_widget in self.gallery_tile_widgets.values():
                    if tile_widget.isVisible():
                        tile_widget.setVisible(False)
                return

            # Utwórz zbiór ścieżek dla szybkiego sprawdzania
            visible_paths = {fp.get_archive_path() for fp in self.file_pairs_list}

            # Identyfikacja i usuwanie zduplikowanych/nieprawidłowych kafelków
            duplicate_keys = []
            for archive_path, tile_widget in list(self.gallery_tile_widgets.items()):
                # Sprawdź czy plik istnieje na dysku, jeśli nie - oznacz do usunięcia
                if not os.path.exists(archive_path):
                    logging.debug(
                        f"Usuwanie kafelka dla nieistniejącego pliku: {archive_path}"
                    )
                    duplicate_keys.append(archive_path)
                # Sprawdź czy są zduplikowane ścieżki w visible_paths (ta sama nazwa pliku w innej ścieżce)
                elif archive_path not in visible_paths and os.path.basename(
                    archive_path
                ) in [os.path.basename(p) for p in visible_paths]:
                    logging.debug(
                        f"Wykryto potencjalny duplikat po przeniesieniu: {archive_path}"
                    )
                    duplicate_keys.append(archive_path)

            # Usuń zduplikowane kafelki z self.gallery_tile_widgets
            for key in duplicate_keys:
                if key in self.gallery_tile_widgets:
                    tile = self.gallery_tile_widgets.pop(key)
                    if tile:
                        tile.setVisible(False)
                        tile.setParent(None)
                        tile.deleteLater()
                        logging.debug(f"Usunięto zduplikowany kafelek: {key}")

            # Ukryj kafelki, których nie ma w obecnie wyświetlanej liście
            for archive_path, tile_widget in self.gallery_tile_widgets.items():
                if archive_path not in visible_paths and tile_widget.isVisible():
                    tile_widget.setVisible(False)

            # Obliczanie układu - liczby kolumn
            container_width = self.tiles_container.width()
            tile_width_with_spacing = (
                self.current_thumbnail_size + self.tiles_layout.spacing() + 10
            )
            cols = max(1, math.floor(container_width / tile_width_with_spacing))

            # 1. Całkowicie czyścimy layout
            while self.tiles_layout.count() > 0:
                item = self.tiles_layout.takeAt(0)
                widget = item.widget() if item else None
                if widget:
                    widget.setVisible(False)

            # 2. Dodajemy widgety do layoutu w kontrolowany sposób
            row, col = 0, 0
            used_positions = set()  # Śledzi zajęte pozycje w układzie

            # Sortowanie listy plików zapewni spójną kolejność wyświetlania
            sorted_file_pairs = sorted(
                self.file_pairs_list, key=lambda fp: fp.get_base_name()
            )

            for file_pair in sorted_file_pairs:
                archive_path = file_pair.get_archive_path()
                tile = self.gallery_tile_widgets.get(archive_path)

                # Sprawdzenie pozycji w siatce
                position = (row, col)
                if position in used_positions:
                    # Znalezienie następnej wolnej pozycji
                    logging.warning(f"Pozycja {position} już zajęta, szukanie nowej.")
                    while position in used_positions:
                        col += 1
                        if col >= cols:
                            col = 0
                            row += 1
                        position = (row, col)

                if tile:
                    # Sprawdź czy kafelek jest w poprawnym stanie
                    if tile.parentWidget() != self.tiles_container:
                        logging.debug(f"Korekta rodzica dla kafelka: {archive_path}")
                        tile.setParent(self.tiles_container)

                    # Aktualizuj widoczność kafelka
                    if not tile.isVisible():
                        tile.setVisible(True)

                    # Dodaj kafelek do layoutu na określonej pozycji
                    self.tiles_layout.addWidget(tile, row, col)
                    used_positions.add(position)

                    # Przejście do następnej pozycji
                    col += 1
                    if col >= cols:
                        col = 0
                        row += 1
                else:
                    # Tworzenie nowego kafelka na żądanie
                    new_tile = self.create_tile_widget_for_pair(
                        file_pair, self.tiles_container
                    )
                    if new_tile:
                        new_tile.setVisible(True)
                        self.tiles_layout.addWidget(new_tile, row, col)
                        used_positions.add(position)

                        # Przejście do następnej pozycji
                        col += 1
                        if col >= cols:
                            col = 0
                            row += 1
                    else:
                        logging.warning(
                            f"Nie udało się utworzyć kafelka dla {file_pair.get_archive_path()}"
                        )
        finally:
            # Włącz aktualizacje i odśwież kontener
            self.tiles_container.setUpdatesEnabled(True)
            self.tiles_container.update()

    def apply_filters_and_update_view(
        self, all_file_pairs: List[FilePair], filter_criteria: dict
    ):
        """
        Filtruje pary plików i aktualizuje widok galerii.
        """
        if not all_file_pairs:
            self.file_pairs_list = []
            self.update_gallery_view()
            return

        self.file_pairs_list = filter_file_pairs(all_file_pairs, filter_criteria)
        self.update_gallery_view()

    def update_thumbnail_size(self, new_size: tuple):
        """
        Aktualizuje rozmiar miniatur i przerenderowuje galerię.
        new_size to krotka (width, height) z main_window.

        Zoptymalizowana wersja - aktualizuje tylko widoczne kafelki.
        """
        # current_thumbnail_size w GalleryManager powinien być int (szerokość)
        # Zakładamy, że new_size[0] to nowa szerokość
        self.current_thumbnail_size = new_size[0]
        self._current_size_tuple = new_size

        # Zaktualizuj rozmiar w kafelkach - tylko dla widocznych kafelków
        for tile in self.gallery_tile_widgets.values():
            if tile.isVisible():
                # FileTileWidget.set_thumbnail_size oczekuje krotki (width, height)
                tile.set_thumbnail_size(new_size)

        # Przerenderuj galerię z nowymi rozmiarami
        self.update_gallery_view()

    def get_all_tile_widgets(self) -> List[FileTileWidget]:
        """
        Zwraca listę wszystkich widgetów kafelków w galerii.
        Używane do operacji zbiorczych (zaznaczanie wszystkich, operacje na zaznaczonych).

        Returns:
            List[FileTileWidget]: Lista wszystkich widgetów kafelków
        """
        return list(self.gallery_tile_widgets.values())

    def get_visible_tile_widgets(self) -> List[FileTileWidget]:
        """
        Zwraca listę tylko widocznych widgetów kafelków.
        Optymalizacja dla operacji na widocznych kafelkach.

        Returns:
            List[FileTileWidget]: Lista widocznych widgetów kafelków
        """
        return [tile for tile in self.gallery_tile_widgets.values() if tile.isVisible()]

    def get_tile_for_path(self, archive_path: str) -> FileTileWidget:
        """
        Pobiera kafelek dla określonej ścieżki archiwum.
        Zwraca None, jeśli kafelek nie istnieje.

        Args:
            archive_path: Ścieżka do pliku archiwum

        Returns:
            FileTileWidget: Znaleziony widget kafelka lub None
        """
        return self.gallery_tile_widgets.get(archive_path)
