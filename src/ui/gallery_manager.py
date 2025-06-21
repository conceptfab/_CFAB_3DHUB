"""
Manager galerii - zarządzanie wyświetlaniem kafelków.
"""

import logging
import math
import os
from typing import Dict, List

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QGridLayout, QWidget

from src import app_config
from src.controllers.gallery_controller import GalleryController
from src.models.file_pair import FilePair
from src.models.special_folder import SpecialFolder
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.ui.widgets.special_folder_tile_widget import SpecialFolderTileWidget

logger = logging.getLogger(__name__)


class GalleryManager:
    """
    Klasa zarządzająca galerią kafelków.
    """

    VIRTUALIZATION_UPDATE_DELAY = 50  # ms, opóźnienie dla aktualizacji wirtualizacji

    def __init__(
        self,
        main_window,
        tiles_container: QWidget,
        tiles_layout: QGridLayout,
        scroll_area: QWidget,
    ):
        self.main_window = main_window
        self.tiles_container = tiles_container
        self.tiles_layout = tiles_layout
        self.scroll_area = scroll_area  # Potrzebne do wirtualizacji
        self.controller = GalleryController()
        self.gallery_tile_widgets: Dict[str, FileTileWidget] = {}
        self.special_folder_widgets: Dict[str, SpecialFolderTileWidget] = {}
        self.file_pairs_list: List[FilePair] = []
        self.special_folders_list: List[SpecialFolder] = []
        # Inicjalizuj current_thumbnail_size jako int, zgodnie z app_config
        self.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
        # Zapisz krotkę rozmiaru dla spójności interfejsu
        self._current_size_tuple = (
            self.current_thumbnail_size,
            self.current_thumbnail_size,
        )

        # Timer do opóźnionej aktualizacji wirtualizacji
        self._virtualization_timer = QTimer()
        self._virtualization_timer.setSingleShot(True)
        self._virtualization_timer.timeout.connect(self._update_visible_tiles)

        # Podłącz sygnał zmiany scrollbara
        self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def _on_scroll(self, value):
        """Wywołuje opóźnioną aktualizację widocznych kafelków."""
        self._virtualization_timer.start(self.VIRTUALIZATION_UPDATE_DELAY)

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
                    # Usuń widget z layoutu, ale nie z pamięci, jeśli
                    # jest w `gallery_tile_widgets` lub
                    # `special_folder_widgets`
                    widget.setVisible(False)
                    self.tiles_layout.removeWidget(widget)  # Jawne usunięcie

            # Usuń widgety par plików ze słownika i pamięci
            for archive_path in list(
                self.gallery_tile_widgets.keys()
            ):  # Iteruj po kopii kluczy
                tile = self.gallery_tile_widgets.pop(archive_path)
                tile.setParent(None)
                tile.deleteLater()
            self.gallery_tile_widgets.clear()

            # Usuń widgety folderów ze słownika i pamięci
            for folder_path in list(
                self.special_folder_widgets.keys()
            ):  # Iteruj po kopii kluczy
                folder_widget = self.special_folder_widgets.pop(folder_path)
                folder_widget.setParent(None)
                folder_widget.deleteLater()
            self.special_folder_widgets.clear()
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
        Aktualizuje widok galerii z WIRTUALIZACJĄ.
        Nie tworzy wszystkich widgetów, tylko oblicza layout i pokazuje pierwszy widok.
        """
        self.tiles_container.setUpdatesEnabled(False)
        try:
            # 1. Wyczyść stare widgety z layoutu, ale ZACHOWAJ je w pamięci
            while self.tiles_layout.count() > 0:
                item = self.tiles_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

            # 2. Oblicz wymiary wirtualnego layoutu
            container_width = (
                self.scroll_area.width() - self.scroll_area.verticalScrollBar().width()
            )
            tile_width_with_spacing = (
                self.current_thumbnail_size + self.tiles_layout.spacing() + 10
            )
            cols = max(1, math.floor(container_width / tile_width_with_spacing))

            total_items = len(self.special_folders_list) + len(self.file_pairs_list)
            if total_items == 0:
                self.tiles_container.setMinimumHeight(0)
                return

            total_rows = math.ceil(total_items / cols)
            tile_height_with_spacing = (
                self.current_thumbnail_size + self.tiles_layout.spacing() + 40
            )
            total_height = total_rows * tile_height_with_spacing

            # 3. Ustaw rozmiar kontenera, aby scrollbary działały poprawnie
            self.tiles_container.setMinimumHeight(total_height)

            # 4. Wywołaj pierwszą aktualizację widocznych kafelków
            self._update_visible_tiles()

        finally:
            self.tiles_container.setUpdatesEnabled(True)

    def _update_visible_tiles(self):
        """Tworzy/usuwa kafelki w zależności od tego, czy są widoczne."""

        container_width = (
            self.scroll_area.width() - self.scroll_area.verticalScrollBar().width()
        )
        tile_width_with_spacing = (
            self.current_thumbnail_size + self.tiles_layout.spacing() + 10
        )
        cols = max(1, math.floor(container_width / tile_width_with_spacing))
        tile_height_with_spacing = (
            self.current_thumbnail_size + self.tiles_layout.spacing() + 40
        )

        # Określ widoczny obszar
        viewport_height = self.scroll_area.viewport().height()
        scroll_y = self.scroll_area.verticalScrollBar().value()

        # Dodaj bufor (np. jeden ekran w górę i w dół)
        buffer = viewport_height
        visible_start_y = max(0, scroll_y - buffer)
        visible_end_y = scroll_y + viewport_height + buffer

        first_visible_row = max(
            0, math.floor(visible_start_y / tile_height_with_spacing)
        )
        last_visible_row = math.ceil(visible_end_y / tile_height_with_spacing)

        # Określ indeksy widocznych itemów
        first_visible_item_idx = first_visible_row * cols
        last_visible_item_idx = (last_visible_row + 1) * cols

        all_items = self.special_folders_list + self.file_pairs_list
        visible_items_set = set()

        # Dodaj widoczne kafelki
        for i in range(
            first_visible_item_idx, min(last_visible_item_idx, len(all_items))
        ):
            item = all_items[i]

            if isinstance(item, SpecialFolder):
                path = item.get_folder_path()
                widget = self.special_folder_widgets.get(path)
                if not widget:
                    widget = self.create_folder_widget(item)
                    if not widget:
                        continue
                visible_items_set.add(path)
            else:  # FilePair
                path = item.get_archive_path()
                widget = self.gallery_tile_widgets.get(path)
                if not widget:
                    widget = self.create_tile_widget_for_pair(
                        item, self.tiles_container
                    )
                    if not widget:
                        continue
                visible_items_set.add(path)

            row = i // cols
            col = i % cols

            if self.tiles_layout.itemAtPosition(row, col) != widget:
                self.tiles_layout.addWidget(widget, row, col)

            if not widget.isVisible():
                widget.setVisible(True)

        # Usuń niewidoczne kafelki
        for path, widget in list(self.gallery_tile_widgets.items()):
            if path not in visible_items_set:
                widget.setVisible(False)
                self.tiles_layout.removeWidget(widget)
                widget.setParent(None)
                # Nie niszczymy widgetu, zostaje w cache (self.gallery_tile_widgets)

        for path, widget in list(self.special_folder_widgets.items()):
            if path not in visible_items_set:
                widget.setVisible(False)
                self.tiles_layout.removeWidget(widget)
                widget.setParent(None)

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

        self.file_pairs_list = self.controller.apply_filters(
            all_file_pairs, filter_criteria
        )
        self.update_gallery_view()

    def update_thumbnail_size(self, new_size):
        """
        Aktualizuje rozmiar miniatur i przerenderowuje galerię.
        new_size może być int lub tuple (width, height).

        Zoptymalizowana wersja - aktualizuje tylko widoczne kafelki.
        """
        # Obsługa różnych formatów new_size
        if isinstance(new_size, int):
            self.current_thumbnail_size = new_size
            self._current_size_tuple = (new_size, new_size)
        else:
            # current_thumbnail_size w GalleryManager powinien być int (szerokość)
            # Zakładamy, że new_size[0] to nowa szerokość
            self.current_thumbnail_size = new_size[0]
            self._current_size_tuple = new_size

        logging.debug(
            f"GalleryManager: Ustawianie nowego rozmiaru: {self._current_size_tuple}"
        )

        # Zaktualizuj rozmiar w kafelkach - dla WSZYSTKICH kafelków
        for tile in self.gallery_tile_widgets.values():
            # FileTileWidget.set_thumbnail_size oczekuje krotki (width, height)
            tile.set_thumbnail_size(self._current_size_tuple)

        # Zaktualizuj rozmiar w widgetach folderów
        for folder_widget in self.special_folder_widgets.values():
            folder_widget.set_thumbnail_size(self._current_size_tuple)

        # Przerenderuj galerię z nowymi rozmiarami
        self.update_gallery_view()

        logging.debug(
            f"GalleryManager: Zaktualizowano rozmiar {len(self.gallery_tile_widgets)} kafli"
        )

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

    def create_folder_widget(self, special_folder: SpecialFolder):
        """
        Tworzy widget dla folderu specjalnego.
        """
        try:
            folder_name = special_folder.get_folder_name()
            folder_path = special_folder.get_folder_path()
            is_virtual = special_folder.is_virtual

            self.main_window.logger.critical(
                f"DIAGNOSTYKA CREATE_FOLDER_WIDGET: Próba utworzenia widgetu dla {folder_path} (wirtualny: {is_virtual})"
            )

            # Sprawdź, czy folder fizycznie istnieje, TYLKO jeśli nie jest wirtualny
            if not is_virtual and not os.path.exists(folder_path):
                self.main_window.logger.error(
                    f"DIAGNOSTYKA CREATE_FOLDER_WIDGET: Fizyczny folder specjalny nie istnieje i nie zostanie utworzony: {folder_path}"
                )
                return None

            folder_widget = SpecialFolderTileWidget(
                folder_name, folder_path, self.tiles_container
            )
            folder_widget.set_thumbnail_size(self.current_thumbnail_size)

            # Podłącz sygnał kliknięcia
            folder_widget.folder_clicked.connect(self._on_folder_clicked)

            self.special_folder_widgets[folder_path] = folder_widget
            logging.debug(f"Utworzono widget folderu: {folder_name}")
            return folder_widget
        except Exception as e:
            logging.error(f"Błąd tworzenia widgetu folderu: {e}", exc_info=True)
            return None

    def _on_folder_clicked(self, folder_path: str):
        """
        Obsługuje kliknięcie na kafelek folderu specjalnego.
        Otwiera folder w eksploratorze plików systemu.

        Args:
            folder_path (str): Ścieżka do folderu do otwarcia.
        """
        if not folder_path or not os.path.exists(folder_path):
            logging.warning(f"Próba otwarcia nieistniejącego folderu: {folder_path}")
            return

        logging.info(f"Otwieranie folderu w eksploratorze: {folder_path}")
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
        except Exception as e:
            logging.error(f"Nie udało się otworzyć folderu {folder_path}: {e}")

    def prepare_special_folders(self, special_folders: List[SpecialFolder]):
        """
        Przygotowuje widgety dla folderów specjalnych przed aktualizacją widoku.
        """
        self.main_window.logger.critical(
            f"🔍 DIAGNOSTYKA PREPARE_SPECIAL_FOLDERS: Otrzymano {len(special_folders)} folderów: {special_folders}"
        )

        self.main_window.logger.critical(
            f"🔍 DIAGNOSTYKA PREPARE_SPECIAL_FOLDERS: Przed czyszczeniem mamy {len(self.special_folder_widgets)} starych widgetów: {list(self.special_folder_widgets.keys())}"
        )

        self.special_folders_list = special_folders

        # Wyczyść poprzednie widgety folderów
        for folder_path in list(self.special_folder_widgets.keys()):
            folder_widget = self.special_folder_widgets.pop(folder_path)
            self.main_window.logger.critical(
                f"🔍 DIAGNOSTYKA: Usuwam stary widget folderu: {folder_path}"
            )
            folder_widget.setParent(None)
            folder_widget.deleteLater()
        self.special_folder_widgets.clear()

        self.main_window.logger.critical(
            f"🔍 DIAGNOSTYKA PREPARE_SPECIAL_FOLDERS: Po wyczyszczeniu mamy {len(self.special_folder_widgets)} widgetów"
        )

        # Utwórz nowe widgety dla folderów i zapisz je w słowniku
        for special_folder in special_folders:
            widget = self.create_folder_widget(special_folder)
            self.main_window.logger.critical(
                f"🔍 DIAGNOSTYKA: Utworzono nowy widget: {special_folder.get_folder_path()} -> {widget is not None}"
            )

        self.main_window.logger.critical(
            f"🔍 DIAGNOSTYKA PREPARE_SPECIAL_FOLDERS: Po utworzeniu nowych mamy {len(self.special_folder_widgets)} widgetów: {list(self.special_folder_widgets.keys())}"
        )

        logging.info(
            f"Przygotowano {len(self.special_folder_widgets)} widgetów folderów specjalnych."
        )

    def set_special_folders(self, special_folders: List[SpecialFolder]):
        """
        Ustawia listę specjalnych folderów i OD RAZU odświeża widok.
        """
        # Krok 1: Przygotuj widgety w tle
        self.prepare_special_folders(special_folders)

        # Krok 2: Wymuś aktualizację widoku, aby pokazać nowe foldery
        self.update_gallery_view()

        logging.info(
            f"Ustawiono i wyświetlono {len(special_folders)} specjalnych folderów"
        )

        # Diagnostyczne logowanie zawartości słownika widgetów folderów
        logging.debug(
            f"DEBUG: Po ustawieniu folderów, mamy {len(self.special_folder_widgets)} widgetów folderów"
        )
        for path, widget in self.special_folder_widgets.items():
            logging.debug(
                f"DEBUG: Widget folderu: {path} (widoczny: {widget.isVisible()})"
            )

    def _on_tile_double_clicked(self, file_pair):
        """Obsługuje podwójne kliknięcie na kafelek pary plików."""
        # ... existing code ...
