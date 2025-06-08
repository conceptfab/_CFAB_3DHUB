"""
Manager galerii - zarządzanie wyświetlaniem kafelków.
"""

import logging
import math
from typing import Dict, List

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
        self.current_thumbnail_size = (
            app_config.DEFAULT_THUMBNAIL_SIZE
        )  # Powinien być int

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
            # Przekaż current_thumbnail_size jako int, jeśli FileTileWidget tego oczekuje
            # lub dostosuj FileTileWidget do przyjmowania krotki (width, height)
            # Zakładając, że FileTileWidget oczekuje krotki:
            tile_size_tuple = (self.current_thumbnail_size, self.current_thumbnail_size)
            tile = FileTileWidget(file_pair, tile_size_tuple, parent_widget)
            # Ukryj na starcie, update_gallery_view zdecyduje o widoczności
            tile.setVisible(False)
            self.gallery_tile_widgets[file_pair.get_archive_path()] = tile
            return tile
        except Exception as e:
            logging.error(
                f"Błąd tworzenia kafelka dla " f"{file_pair.get_base_name()}: {e}"
            )
            return None

    def update_gallery_view(self):
        """
        Aktualizuje widok galerii, pokazując/ukrywając istniejące kafelki
        i rozmieszczając je w siatce.
        """
        # Wyłącz aktualizacje na czas przebudowy layoutu
        self.tiles_container.setUpdatesEnabled(False)

        try:
            # Najpierw ukryj wszystkie istniejące widgety w layoucie
            # i usuń je z layoutu, aby móc je dodać w nowej kolejności
            for i in range(self.tiles_layout.count()):
                item = self.tiles_layout.itemAt(i)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.setVisible(False)

            # Usuń wszystkie elementy z layoutu, ale nie widgety z pamięci
            # Widgety zostaną dodane ponownie w odpowiedniej kolejności
            while self.tiles_layout.count():
                item = self.tiles_layout.takeAt(0)
                # Nie usuwamy widgetu (widget.deleteLater()), bo może być ponownie użyty

            if not self.file_pairs_list:
                logging.debug("Lista par (po filtracji) pusta, galeria pusta.")
                # Upewnij się, że wszystkie widgety są ukryte, jeśli lista jest pusta
                for tile_widget in self.gallery_tile_widgets.values():
                    tile_widget.setVisible(False)
                return

            container_width = self.tiles_container.width()
            # Użyj self.current_thumbnail_size bezpośrednio, bo to int
            tile_width_with_spacing = (
                self.current_thumbnail_size + self.tiles_layout.spacing() + 10
            )
            cols = max(1, math.floor(container_width / tile_width_with_spacing))

            row, col = 0, 0
            for file_pair in self.file_pairs_list:
                tile = self.gallery_tile_widgets.get(file_pair.get_archive_path())
                if tile:
                    # Jeśli kafelek jest już zarządzany przez layout, nie trzeba go ponownie dodawać,
                    # wystarczy ustawić widoczność i pozycję.
                    # Jednakże, ponieważ czyścimy layout na początku (takeAt), musimy dodać go ponownie.
                    tile.setVisible(True)
                    self.tiles_layout.addWidget(tile, row, col)
                    col += 1
                    if col >= cols:
                        col = 0
                        row += 1
                else:
                    logging.warning(
                        f"Nie znaleziono widgetu kafelka dla "
                        f"{file_pair.get_archive_path()} w słowniku."
                    )

            # Ukryj widgety, które nie są na liście file_pairs_list
            for archive_path, tile_widget in self.gallery_tile_widgets.items():
                is_on_list = any(
                    fp.get_archive_path() == archive_path for fp in self.file_pairs_list
                )
                if (
                    not is_on_list and tile_widget.isVisible()
                ):  # Ukryj tylko jeśli jest widoczny
                    tile_widget.setVisible(False)
        finally:
            # Włącz aktualizacje i zaplanuj odświeżenie
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
        """
        # current_thumbnail_size w GalleryManager powinien być int (szerokość)
        # Zakładamy, że new_size[0] to nowa szerokość
        self.current_thumbnail_size = new_size[0]

        # Zaktualizuj rozmiar w kafelkach
        for tile in self.gallery_tile_widgets.values():
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
