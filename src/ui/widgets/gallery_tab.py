"""
Zakładka galerii - wydzielona z main_window.py.
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QDir
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import (
    QGridLayout,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class GalleryTab:
    """
    Zarządza zakładką galerii z drzewem folderów i kafelkami plików.
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Inicjalizuje zakładkę galerii.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.gallery_tab = None
        self.gallery_tab_layout = None
        self.splitter = None
        self.folder_tree_container = None
        self.folder_tree = None
        self.file_system_model = None
        self.scroll_area = None
        self.tiles_container = None
        self.tiles_layout = None

    def create_gallery_tab(self) -> QWidget:
        """
        Tworzy zakładkę galerii.

        Returns:
            Widget zakładki galerii
        """
        self.gallery_tab = QWidget()
        self.gallery_tab_layout = QVBoxLayout(self.gallery_tab)
        self.gallery_tab_layout.setContentsMargins(0, 0, 0, 0)

        # Splitter dla drzewa i kafelków
        self.splitter = QSplitter()

        # Drzewo folderów
        self._create_folder_tree()

        # Scroll area dla kafelków
        self._create_tiles_area()

        # Ustaw proporcje splitter i zapewnij widoczność drzewa
        self.splitter.setSizes([350, 650])  # Więcej miejsca dla drzewa
        self.splitter.setCollapsible(0, False)  # Nie pozwól na zwijanie drzewa
        self.splitter.setCollapsible(1, False)  # Nie pozwól na zwijanie galerii

        logging.debug(f"Splitter ma {self.splitter.count()} widgetów")

        self.gallery_tab_layout.addWidget(self.splitter)
        return self.gallery_tab

    def _create_folder_tree(self):
        """
        Tworzy drzewo folderów z kontrolkami expand/collapse.
        """
        # Kontener dla drzewa folderów + kontrolek
        self.folder_tree_container = QWidget()
        folder_tree_layout = QVBoxLayout(self.folder_tree_container)
        folder_tree_layout.setContentsMargins(0, 0, 0, 0)
        folder_tree_layout.setSpacing(2)

        # Kontrolki expand/collapse będą dodane po inicjalizacji DirectoryTreeManager
        # (placeholder dla przyszłych kontrolek)

        self.folder_tree = QTreeView()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setMinimumWidth(250)  # Zwiększona minimalna szerokość
        self.folder_tree.setMaximumWidth(400)  # Dodana maksymalna szerokość
        self.folder_tree.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,  # Zmieniono na Preferred
        )

        self.file_system_model = QFileSystemModel()
        # Pokaż tylko foldery (bez plików)
        self.file_system_model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot)
        self.folder_tree.setModel(self.file_system_model)

        # Ukryj wszystkie kolumny poza pierwszą
        for col in range(1, 4):
            self.folder_tree.setColumnHidden(col, True)

        # Dodaj drzewo do kontenera
        folder_tree_layout.addWidget(self.folder_tree)

        # Dodaj debug info
        logging.debug("Dodaję kontener drzewa folderów do splitter")
        self.splitter.addWidget(self.folder_tree_container)

        # Zapewnij widoczność
        self.folder_tree.setVisible(True)
        self.folder_tree.show()

    def _create_tiles_area(self):
        """
        Tworzy obszar dla kafelków galerii.
        """
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.tiles_container = QWidget()
        self.tiles_layout = QGridLayout(self.tiles_container)
        self.tiles_layout.setContentsMargins(10, 10, 10, 10)
        self.tiles_layout.setSpacing(15)

        self.scroll_area.setWidget(self.tiles_container)
        self.splitter.addWidget(self.scroll_area)

    def folder_tree_item_clicked(self, index):
        """
        Obsługuje kliknięcie elementu w drzewie folderów.
        """
        if hasattr(self.main_window, "directory_tree_manager"):
            folder_path = (
                self.main_window.directory_tree_manager.folder_tree_item_clicked(
                    index, self.main_window.controller.current_directory
                )
            )
            if folder_path:
                self.main_window._select_working_directory(folder_path)

    def update_gallery_view(self):
        """
        Aktualizuje widok galerii.
        """
        if hasattr(self.main_window, "gallery_manager"):
            self.main_window.gallery_manager.update_gallery_view()

    def apply_filters_and_update_view(self):
        """
        Zbiera kryteria, filtruje pary i aktualizuje galerię.
        """
        if not self.main_window.controller.current_directory:
            if hasattr(self.main_window, "gallery_manager"):
                self.main_window.gallery_manager.file_pairs_list = []
            self.update_gallery_view()
            if hasattr(self.main_window, "size_control_panel"):
                self.main_window.size_control_panel.setVisible(False)
            if hasattr(self.main_window, "filter_panel"):
                self.main_window.filter_panel.setEnabled(
                    False
                )  # Zablokuj zamiast ukryć
            return

        if not self.main_window.controller.current_file_pairs:
            if hasattr(self.main_window, "gallery_manager"):
                self.main_window.gallery_manager.file_pairs_list = []
            self.update_gallery_view()
            if hasattr(self.main_window, "size_control_panel"):
                self.main_window.size_control_panel.setVisible(False)
            return

        # Pobierz kryteria filtrowania z panelu
        filter_criteria = None
        if hasattr(self.main_window, "filter_panel"):
            filter_criteria = self.main_window.filter_panel.get_filter_criteria()

        # Zastosuj filtry
        if hasattr(self.main_window, "gallery_manager") and filter_criteria:
            self.main_window.gallery_manager.apply_filters_and_update_view(
                self.main_window.controller.current_file_pairs, filter_criteria
            )

        is_gallery_populated = bool(
            hasattr(self.main_window, "gallery_manager")
            and self.main_window.gallery_manager.file_pairs_list
        )
        if hasattr(self.main_window, "size_control_panel"):
            self.main_window.size_control_panel.setVisible(is_gallery_populated)

    def update_thumbnail_size(self):
        """
        Aktualizuje rozmiar miniatur i przerenderowuje galerię.
        """
        if not hasattr(self.main_window, "size_slider"):
            return

        # Pobierz wartość z suwaka
        value = self.main_window.size_slider.value()

        # Oblicz nowy rozmiar
        # Użyj self.min_thumbnail_size i self.max_thumbnail_size, które są teraz int
        size_range = (
            self.main_window.max_thumbnail_size - self.main_window.min_thumbnail_size
        )
        if size_range <= 0:  # Zapobieganie błędom, jeśli min >= max
            new_width = self.main_window.current_thumbnail_size
        else:
            new_width = self.main_window.min_thumbnail_size + int(
                (size_range * value) / 100
            )

        new_height = new_width  # Zakładamy kwadratowe miniatury
        new_size = (new_width, new_height)

        logging.debug(f"Aktualizacja rozmiaru miniatur na: {new_size}")

        # Zapisz pozycję suwaka do konfiguracji
        if hasattr(self.main_window, "app_config"):
            self.main_window.app_config.set_thumbnail_slider_position(value)

        # Zaktualizuj rozmiar w gallery managerze
        if hasattr(self.main_window, "gallery_manager"):
            self.main_window.gallery_manager.update_thumbnail_size(new_size)

    def get_widgets_for_main_window(self):
        """
        Zwraca referencje do widgetów potrzebnych w main_window.

        Returns:
            Dict z referencjami do widgetów
        """
        return {
            "folder_tree": self.folder_tree,
            "folder_tree_container": self.folder_tree_container,
            "file_system_model": self.file_system_model,
            "tiles_container": self.tiles_container,
            "tiles_layout": self.tiles_layout,
            "scroll_area": self.scroll_area,
            "splitter": self.splitter,
        }
