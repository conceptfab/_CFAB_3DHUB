"""
UI Manager dla zakładki niesparowanych plików - ETAP 2 refaktoryzacji.
Wydzielono z unpaired_files_tab.py dla lepszej separacji odpowiedzialności.
"""

import logging
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.tile_styles import TileSizeConstants
from src.ui.widgets.unpaired_archives_list import UnpairedArchivesList
from src.ui.widgets.unpaired_preview_tile import UnpairedPreviewTile
from src.ui.widgets.unpaired_previews_grid import UnpairedPreviewsGrid

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class UnpairedFilesUIManager:
    """
    Zarządza interfejsem użytkownika zakładki niesparowanych plików.
    Odpowiedzialny za tworzenie, aktualizację i czyszczenie UI.
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Inicjalizuje UI Manager.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window

        # Główne komponenty UI
        self.unpaired_files_tab = None
        self.unpaired_files_layout = None
        self.unpaired_splitter = None

        # Komponenty archiwów
        self.unpaired_archives_list = None
        self.unpaired_archives_list_widget = None

        # Komponenty podglądów
        self.unpaired_previews_grid = None
        self.unpaired_previews_list_widget = None
        self.unpaired_previews_layout = None
        self.unpaired_previews_container = None

        # Przyciski
        self.pair_manually_button = None
        self.delete_unpaired_previews_button = None
        self.move_unpaired_button = None

        # Stan UI
        self.preview_tile_widgets = []
        self.current_thumbnail_size = TileSizeConstants.DEFAULT_THUMBNAIL_SIZE

    def create_tab_ui(self) -> QWidget:
        """
        Tworzy kompletny interfejs zakładki niesparowanych plików.

        Returns:
            Widget zakładki niesparowanych plików
        """
        logging.debug("Creating unpaired files tab UI")

        self.unpaired_files_tab = QWidget()
        self.unpaired_files_layout = QVBoxLayout(self.unpaired_files_tab)
        self.unpaired_files_layout.setContentsMargins(5, 5, 5, 5)

        # Splitter dla dwóch list
        self.unpaired_splitter = QSplitter()

        # Utwórz komponenty
        self._create_archives_component()
        self._create_previews_component()
        self._create_buttons_panel()

        self.unpaired_files_layout.addWidget(self.unpaired_splitter)

        logging.debug("Unpaired files tab UI created successfully")
        return self.unpaired_files_tab

    def _create_archives_component(self):
        """Tworzy komponent listy archiwów."""
        self.unpaired_archives_list = UnpairedArchivesList(self.main_window)

        # Zachowaj kompatybilność
        self.unpaired_archives_list_widget = self.unpaired_archives_list.list_widget

        self.unpaired_splitter.addWidget(self.unpaired_archives_list)

    def _create_previews_component(self):
        """Tworzy komponent siatki podglądów."""
        self.unpaired_previews_grid = UnpairedPreviewsGrid(self.main_window)

        # Zachowaj kompatybilność
        self.unpaired_previews_list_widget = (
            self.unpaired_previews_grid.hidden_list_widget
        )
        self.unpaired_previews_layout = self.unpaired_previews_grid.grid_layout
        self.unpaired_previews_container = self.unpaired_previews_grid.container

        self.unpaired_splitter.addWidget(self.unpaired_previews_grid)

    def _create_buttons_panel(self):
        """Tworzy panel przycisków operacji."""
        buttons_panel = QWidget()
        buttons_panel.setFixedHeight(35)
        buttons_layout = QHBoxLayout(buttons_panel)
        buttons_layout.setContentsMargins(5, 2, 5, 2)
        buttons_layout.setSpacing(10)

        # Przycisk parowania
        self.pair_manually_button = QPushButton("✅ Sparuj manualnie")
        self.pair_manually_button.setToolTip(
            "Sparuj zaznaczone archiwum z zaznaczonym podglądem"
        )
        self.pair_manually_button.setMinimumHeight(40)
        self.pair_manually_button.setEnabled(False)
        buttons_layout.addWidget(self.pair_manually_button)

        # Przycisk usuwania podglądów
        self.delete_unpaired_previews_button = QPushButton("🗑️ Usuń podglądy bez pary")
        self.delete_unpaired_previews_button.setToolTip(
            "Usuwa z dysku wszystkie pliki podglądów z tej listy"
        )
        self.delete_unpaired_previews_button.setMinimumHeight(40)
        buttons_layout.addWidget(self.delete_unpaired_previews_button)

        # Przycisk przenoszenia archiwów
        self.move_unpaired_button = QPushButton("🚚 Przenieś archiwa")
        self.move_unpaired_button.setToolTip(
            "Przenosi wszystkie pliki archiwum bez pary do folderu '_bez_pary_'"
        )
        self.move_unpaired_button.setMinimumHeight(40)
        buttons_layout.addWidget(self.move_unpaired_button)

        self.unpaired_files_layout.addWidget(buttons_panel)

    def add_preview_thumbnail(self, preview_path: str):
        """
        Dodaje miniaturkę podglądu do kontenera.

        Args:
            preview_path: Ścieżka do pliku podglądu
        """
        if not os.path.exists(preview_path):
            return

        # Utwórz kafelek podglądu
        preview_tile = UnpairedPreviewTile(
            preview_path, self.unpaired_previews_container
        )
        preview_tile.set_thumbnail_size(self.current_thumbnail_size)

        # Dodaj do layoutu siatki
        row = self.unpaired_previews_layout.rowCount()
        col = 0
        while self.unpaired_previews_layout.itemAtPosition(row, col) is not None:
            col += 1
            if col >= 4:  # Maksymalnie 4 kolumny
                col = 0
                row += 1

        self.unpaired_previews_layout.addWidget(preview_tile, row, col)
        self.preview_tile_widgets.append(preview_tile)

        # Dodaj do ukrytej listy dla kompatybilności
        item = QListWidgetItem(preview_path)
        self.unpaired_previews_list_widget.addItem(item)

        logging.debug(f"Added preview thumbnail: {os.path.basename(preview_path)}")
        return preview_tile

    def clear_all_lists(self):
        """Czyści wszystkie listy i komponenty UI."""
        logging.debug("Clearing unpaired files UI")

        # Wyczyść listę archiwów
        if self.unpaired_archives_list_widget:
            self.unpaired_archives_list_widget.clear()

        # Wyczyść ukrytą listę podglądów
        if self.unpaired_previews_list_widget:
            self.unpaired_previews_list_widget.clear()

        # Usuń wszystkie kafelki podglądów
        for tile in self.preview_tile_widgets:
            tile.setParent(None)
        self.preview_tile_widgets.clear()

        # Wyczyść layout siatki
        if self.unpaired_previews_layout:
            while self.unpaired_previews_layout.count():
                item = self.unpaired_previews_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

        # Zresetuj stan przycisków
        if self.pair_manually_button:
            self.pair_manually_button.setEnabled(False)

        logging.debug("Unpaired files UI cleared")

    def update_archives_list(self, archives_list: list[str]):
        """
        Aktualizuje listę archiwów.

        Args:
            archives_list: Lista ścieżek do archiwów
        """
        # NAPRAWKA: Sprawdź czy UI manager jest w pełni zainicjalizowany
        if (
            not hasattr(self, "unpaired_archives_list")
            or self.unpaired_archives_list is None
        ):
            logging.warning("UI manager not initialized yet - skipping archives update")
            return

        if not self.unpaired_archives_list_widget:
            # Spróbuj ponownie uzyskać referencję
            if hasattr(self.unpaired_archives_list, "list_widget"):
                self.unpaired_archives_list_widget = (
                    self.unpaired_archives_list.list_widget
                )
            else:
                logging.error("Cannot recover unpaired_archives_list_widget")
                return

        self.unpaired_archives_list_widget.clear()

        for archive_path in archives_list:
            if os.path.exists(archive_path):
                filename = os.path.basename(archive_path)
                item = QListWidgetItem(filename)
                item.setData(Qt.ItemDataRole.UserRole, archive_path)
                item.setToolTip(archive_path)
                self.unpaired_archives_list_widget.addItem(item)

    def update_previews_list(self, previews_list: list[str]):
        """
        Aktualizuje listę podglądów.

        Args:
            previews_list: Lista ścieżek do podglądów
        """
        # Wyczyść istniejące podglądy
        for tile in self.preview_tile_widgets:
            tile.setParent(None)
        self.preview_tile_widgets.clear()

        if self.unpaired_previews_list_widget:
            self.unpaired_previews_list_widget.clear()

        # Wyczyść layout siatki
        if self.unpaired_previews_layout:
            while self.unpaired_previews_layout.count():
                item = self.unpaired_previews_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

        # Dodaj nowe podglądy
        for preview_path in previews_list:
            if os.path.exists(preview_path):
                self.add_preview_thumbnail(preview_path)

    def update_thumbnail_sizes(self, new_size: int):
        """
        Aktualizuje rozmiar miniaturek w kafelkach podglądów.

        Args:
            new_size: Nowy rozmiar miniaturek
        """
        self.current_thumbnail_size = new_size

        # Aktualizuj wszystkie istniejące kafelki
        for tile in self.preview_tile_widgets:
            tile.set_thumbnail_size(new_size)

        logging.debug(f"Updated thumbnail size to: {new_size}")

    def remove_preview_tile(self, preview_path: str):
        """
        Usuwa kafelek podglądu z UI.

        Args:
            preview_path: Ścieżka do pliku podglądu
        """
        # Usuń z layoutu siatki
        for i in range(self.unpaired_previews_layout.count()):
            item = self.unpaired_previews_layout.itemAt(i)
            if item and item.widget():
                tile = item.widget()
                if hasattr(tile, "preview_path") and tile.preview_path == preview_path:
                    tile.setParent(None)
                    self.preview_tile_widgets.remove(tile)
                    break

        # Usuń z ukrytej listy
        for i in range(self.unpaired_previews_list_widget.count()):
            item = self.unpaired_previews_list_widget.item(i)
            if item and item.text() == preview_path:
                self.unpaired_previews_list_widget.takeItem(i)
                break

    def get_widgets_dict(self) -> dict:
        """
        Zwraca słownik z głównymi widgetami dla kompatybilności.

        Returns:
            dict: Słownik z widgetami
        """
        return {
            "unpaired_files_tab": self.unpaired_files_tab,
            "pair_manually_button": self.pair_manually_button,
            "unpaired_archives_list_widget": self.unpaired_archives_list_widget,
            "unpaired_previews_list_widget": self.unpaired_previews_list_widget,
            "unpaired_previews_layout": self.unpaired_previews_layout,
        }

    def connect_button_signals(self, callbacks: dict):
        """
        Podłącza sygnały przycisków do callback'ów.

        Args:
            callbacks: Słownik z callback'ami dla przycisków
        """
        if self.pair_manually_button and "manual_pairing" in callbacks:
            self.pair_manually_button.clicked.connect(callbacks["manual_pairing"])

        if self.delete_unpaired_previews_button and "delete_previews" in callbacks:
            self.delete_unpaired_previews_button.clicked.connect(
                callbacks["delete_previews"]
            )

        if self.move_unpaired_button and "move_archives" in callbacks:
            self.move_unpaired_button.clicked.connect(callbacks["move_archives"])

    def connect_component_signals(self, callbacks: dict):
        """
        Podłącza sygnały komponentów do callback'ów.

        Args:
            callbacks: Słownik z callback'ami dla komponentów
        """
        if self.unpaired_archives_list and "selection_changed" in callbacks:
            self.unpaired_archives_list.selection_changed.connect(
                callbacks["selection_changed"]
            )

        if self.unpaired_previews_grid and "selection_changed" in callbacks:
            self.unpaired_previews_grid.selection_changed.connect(
                callbacks["selection_changed"]
            )

        if self.unpaired_previews_grid and "preview_deleted" in callbacks:
            self.unpaired_previews_grid.preview_deleted.connect(
                callbacks["preview_deleted"]
            )
