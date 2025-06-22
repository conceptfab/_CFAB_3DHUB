"""
Zakładka galerii - wydzielona z main_window.py.
"""

import logging
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import QDir, QItemSelectionModel, Qt, pyqtSignal
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from src.ui.widgets.filter_panel import FilterPanel

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
        self.filter_panel = None

    def create_gallery_tab(self) -> QWidget:
        """
        Tworzy zakładkę galerii z wbudowanym panelem filtrów.

        Returns:
            Widget zakładki galerii
        """
        self.gallery_tab = QWidget()
        self.gallery_tab_layout = QVBoxLayout(self.gallery_tab)
        self.gallery_tab_layout.setContentsMargins(0, 0, 0, 0)

        # Panel filtrów na górze zakładki
        self._create_filter_panel()

        # Splitter dla drzewa i kafelków
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.gallery_tab_layout.addWidget(self.splitter)

        # Drzewo folderów
        self.folder_tree_container = self._create_folder_tree_panel()
        self.splitter.addWidget(self.folder_tree_container)

        # Scroll area dla kafelków
        self.scroll_area, self.tiles_container, self.tiles_layout = (
            self._create_tiles_area()
        )
        self.splitter.addWidget(self.scroll_area)

        # Ustaw proporcje splitter i zapewnij widoczność drzewa
        self.splitter.setSizes([250, 750])  # Więcej miejsca dla drzewa
        self.splitter.setCollapsible(0, False)  # Nie pozwól na zwijanie drzewa
        self.splitter.setCollapsible(1, False)  # Nie pozwól na zwijanie galerii

        logging.debug(f"Splitter ma {self.splitter.count()} widgetów")

        # Pasek ulubionych folderów na dole
        self._create_favorite_folders_bar()

        return self.gallery_tab

    def _create_filter_panel(self):
        """
        Tworzy panel filtrów wewnątrz zakładki galerii.
        """
        self.filter_panel = FilterPanel(self.main_window)
        self.filter_panel.setVisible(True)  # Zawsze widoczny
        self.filter_panel.setEnabled(False)  # Ale zablokowany na start
        self.filter_panel.connect_signals(self.apply_filters_and_update_view)
        self.gallery_tab_layout.addWidget(self.filter_panel)

        # Przypisz referencję do main_window dla kompatybilności
        self.main_window.filter_panel = self.filter_panel

    def _create_folder_tree_panel(self):
        """Tworzy panel z drzewem folderów."""
        folder_tree_container = QWidget()
        folder_tree_layout = QVBoxLayout(folder_tree_container)
        folder_tree_layout.setContentsMargins(2, 2, 2, 2)  # Minimalne marginesy
        folder_tree_layout.setSpacing(2)  # Minimalna przestrzeń między elementami

        # Utworzenie drzewa folderów
        folder_tree = QTreeView()
        folder_tree.setHeaderHidden(True)
        folder_tree.setMinimumWidth(200)
        folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Konfiguracja modelu plików
        self.file_system_model = QFileSystemModel()
        # Pokaż tylko foldery (bez plików)
        self.file_system_model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot)
        folder_tree.setModel(self.file_system_model)

        # Ukryj wszystkie kolumny poza pierwszą
        for col in range(1, 4):
            folder_tree.setColumnHidden(col, True)

        # Dodanie drzewa do layoutu
        folder_tree_layout.addWidget(folder_tree)

        # Zapisanie referencji do drzewa
        self.folder_tree = folder_tree

        return folder_tree_container

    def _create_tiles_area(self):
        """
        Tworzy obszar z kafelkami.

        Returns:
            tuple: (scroll_area, tiles_container, tiles_layout)
        """
        # Scroll area dla kafelków
        scroll_area = QScrollArea()  # Używamy QScrollArea dla możliwości przewijania
        scroll_area.setWidgetResizable(True)

        # Kontener dla zawartości scroll area
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(2, 2, 2, 2)
        scroll_layout.setSpacing(2)

        # Ustaw widget zawartości dla scroll area
        scroll_area.setWidget(scroll_content)

        # Kontener dla kafelków
        tiles_container = QWidget()
        # Używamy QGridLayout zamiast QHBoxLayout, aby było zgodne z GalleryManager
        tiles_layout = QGridLayout(tiles_container)
        tiles_layout.setContentsMargins(5, 5, 5, 5)
        tiles_layout.setSpacing(10)
        tiles_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        # Dodaj kontener do scroll area
        scroll_layout.addWidget(tiles_container)

        # Nie tworzymy drugiego suwaka w galerii - używamy tylko tego z głównego okna
        # Podłączenie do funkcji zmiany rozmiaru odbywa się w głównym oknie

        return scroll_area, tiles_container, tiles_layout

    def _create_favorite_folders_bar(self):
        """
        Tworzy pasek z przyciskami ulubionych folderów na dole zakładki.
        """

        # Kontener dla paska ulubionych folderów
        self.favorite_folders_bar = QWidget()
        self.favorite_folders_bar.setFixedHeight(18)  # Wysokość 18px
        self.favorite_folders_bar.setStyleSheet(
            """
            QWidget {
                background-color: #252526;
                border-top: 1px solid #3F3F46;
            }
        """
        )

        # Layout poziomy dla przycisków
        self.favorite_folders_layout = QHBoxLayout(self.favorite_folders_bar)
        self.favorite_folders_layout.setContentsMargins(0, 0, 0, 0)
        self.favorite_folders_layout.setSpacing(1)

        # Dodaj przyciski ulubionych folderów
        self._update_favorite_folders_buttons()

        # Dodaj pasek do layoutu zakładki
        self.gallery_tab_layout.addWidget(self.favorite_folders_bar)

    def _update_favorite_folders_buttons(self):
        """
        Aktualizuje przyciski ulubionych folderów na podstawie konfiguracji.
        """
        from src.config.config_core import AppConfig

        # Wyczyść istniejące przyciski
        for i in reversed(range(self.favorite_folders_layout.count())):
            child = self.favorite_folders_layout.itemAt(i).widget()
            if child:
                child.setParent(None)

                # Dodaj przycisk "Domek" na początku
        self._create_home_button()

        # Pobierz konfigurację ulubionych folderów
        app_config = AppConfig.get_instance()
        favorite_folders = app_config.get("favorite_folders", [])

        # Utwórz przyciski dla każdego ulubionego folderu
        for i, folder_config in enumerate(favorite_folders):
            if i >= 4:  # Maksymalnie 4 przyciski
                break

            name = folder_config.get("name", f"Folder {i+1}")
            path = folder_config.get("path", "")
            color = folder_config.get("color", "#007ACC")
            description = folder_config.get("description", "")

            # Utwórz przycisk
            button = QPushButton(name)
            button.setFixedHeight(14)  # Wysokość 14px
            button.setMaximumHeight(14)  # Maksymalna wysokość 14px
            button.setMinimumWidth(80)
            button.setContentsMargins(0, 0, 0, 0)  # Brak marginesów wewnętrznych
            button.setToolTip(
                f"{description}\nŚcieżka: {path}" if path else description
            )

            # Style przycisku z kolorem
            button.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    border-radius: 2px;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 0px;
                    min-height: 14px;
                    max-height: 14px;
                }}
                QPushButton:hover {{
                    background-color: {self._lighten_color(color, 20)};
                }}
                QPushButton:pressed {{
                    background-color: {self._darken_color(color, 20)};
                }}
                QPushButton:disabled {{
                    background-color: #3F3F46;
                    color: #888888;
                }}
            """
            )

            # Podłącz sygnał kliknięcia
            if path:  # Tylko jeśli ścieżka jest ustawiona
                button.clicked.connect(
                    lambda checked, p=path: self._on_favorite_folder_clicked(p)
                )
            else:
                button.setEnabled(False)  # Wyłącz przycisk jeśli brak ścieżki

            # Dodaj przycisk do layoutu
            self.favorite_folders_layout.addWidget(button)

            # Dodaj spacer na końcu
        self.favorite_folders_layout.addStretch()

    def _create_home_button(self):
        """
        Tworzy przycisk "Domek" do przechodzenia do domyślnego folderu roboczego.
        """
        home_button = QPushButton("🏠")
        home_button.setFixedHeight(14)  # Wysokość 14px
        home_button.setMaximumHeight(14)  # Maksymalna wysokość 14px
        home_button.setFixedWidth(28)  # Szerokość 28px dla ikony
        home_button.setContentsMargins(0, 0, 0, 0)  # Brak marginesów
        home_button.setToolTip("Przejdź do domyślnego folderu roboczego")

        # Style przycisku domku
        home_button.setStyleSheet(
            """
            QPushButton {
                background-color: #3F3F46;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 12px;
                font-weight: bold;
                padding: 0px;
                min-height: 14px;
                max-height: 14px;
            }
            QPushButton:hover {
                background-color: #4A4A4F;
            }
            QPushButton:pressed {
                background-color: #2A2A2F;
            }
        """
        )

        # Podłącz sygnał kliknięcia
        home_button.clicked.connect(self._on_home_button_clicked)

        # Dodaj przycisk do layoutu
        self.favorite_folders_layout.addWidget(home_button)

        # Dodaj separator po przycisku domku
        separator = QWidget()
        separator.setFixedWidth(1)
        separator.setStyleSheet("background-color: #3F3F46;")
        self.favorite_folders_layout.addWidget(separator)

    def _on_home_button_clicked(self):
        """
        Obsługuje kliknięcie przycisku domku - przechodzi do domyślnego folderu.
        """
        # Pobierz domyślny folder roboczy z konfiguracji
        from src.config.config_core import AppConfig

        app_config = AppConfig.get_instance()

        # Sprawdź czy jest ustawiony domyślny folder w konfiguracji
        default_folder = app_config.get("default_working_directory", "")

        # Jeśli nie ma ustawionego domyślnego folderu, użyj folderu domowego
        if not default_folder:
            default_folder = os.path.expanduser("~")

        # Jeśli nadal nie ma folderu, spróbuj pierwszy ulubiony folder
        if not os.path.exists(default_folder):
            favorite_folders = app_config.get("favorite_folders", [])
            if favorite_folders and favorite_folders[0].get("path"):
                potential_default = favorite_folders[0]["path"]
                if os.path.exists(potential_default) and os.path.isdir(
                    potential_default
                ):
                    default_folder = potential_default

        # Sprawdź czy folder istnieje
        if not os.path.exists(default_folder) or not os.path.isdir(default_folder):
            QMessageBox.warning(
                self.main_window,
                "Błąd",
                f"Domyślny folder nie istnieje lub nie jest dostępny:\n{default_folder}",
            )
            return

        # Zmień folder roboczy
        self.main_window.set_working_directory(default_folder)

    def _lighten_color(self, color_hex: str, percent: int) -> str:
        """
        Rozjaśnia kolor o określony procent.

        Args:
            color_hex: Kolor w formacie hex (#RRGGBB)
            percent: Procent rozjaśnienia (0-100)

        Returns:
            Rozjaśniony kolor w formacie hex
        """
        try:
            # Usuń # jeśli jest
            color_hex = color_hex.lstrip("#")

            # Konwertuj na RGB
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)

            # Rozjaśnij
            r = min(255, r + int((255 - r) * percent / 100))
            g = min(255, g + int((255 - g) * percent / 100))
            b = min(255, b + int((255 - b) * percent / 100))

            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return color_hex  # Zwróć oryginalny kolor w przypadku błędu

    def _darken_color(self, color_hex: str, percent: int) -> str:
        """
        Przyciemnia kolor o określony procent.

        Args:
            color_hex: Kolor w formacie hex (#RRGGBB)
            percent: Procent przyciemnienia (0-100)

        Returns:
            Przyciemniony kolor w formacie hex
        """
        try:
            # Usuń # jeśli jest
            color_hex = color_hex.lstrip("#")

            # Konwertuj na RGB
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)

            # Przyciemnij
            r = max(0, r - int(r * percent / 100))
            g = max(0, g - int(g * percent / 100))
            b = max(0, b - int(b * percent / 100))

            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return color_hex  # Zwróć oryginalny kolor w przypadku błędu

    def _on_favorite_folder_clicked(self, folder_path: str):
        """
        Obsługuje kliknięcie przycisku ulubionego folderu.

        Args:
            folder_path: Ścieżka do folderu
        """
        import os
        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"Kliknięto ulubiony folder: {folder_path}")

        # Sprawdź czy folder istnieje
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            QMessageBox.warning(
                self.main_window,
                "Błąd",
                f"Folder nie istnieje lub nie jest dostępny:\n{folder_path}",
            )
            return

        # Przełącz na zakładkę galerii
        self.main_window.tab_widget.setCurrentIndex(0)

        # Użyj metody set_working_directory, aby całkowicie zresetować
        # stan aplikacji i drzewo katalogów na nowy folder.
        self.main_window.set_working_directory(folder_path)

    def update_favorite_folders_bar(self):
        """
        Aktualizuje pasek ulubionych folderów (wywoływane po zmianie konfiguracji).
        """
        if hasattr(self, "favorite_folders_bar"):
            self._update_favorite_folders_buttons()

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
            if hasattr(self, "filter_panel"):
                self.filter_panel.setEnabled(False)  # Zablokuj zamiast ukryć
            return

        if not self.main_window.controller.current_file_pairs:
            if hasattr(self.main_window, "gallery_manager"):
                self.main_window.gallery_manager.file_pairs_list = []
            self.update_gallery_view()
            if hasattr(self.main_window, "size_control_panel"):
                self.main_window.size_control_panel.setVisible(False)
            return

        # Pobierz kryteria filtrowania z lokalnego panelu
        filter_criteria = {}
        if hasattr(self, "filter_panel"):
            filter_criteria = self.filter_panel.get_filter_criteria()

        # ZAWSZE zastosuj filtry z aktualną listą par plików z kontrolera
        if hasattr(self.main_window, "gallery_manager"):
            self.main_window.gallery_manager.apply_filters_and_update_view(
                self.main_window.controller.current_file_pairs, filter_criteria
            )

        is_gallery_populated = bool(
            hasattr(self.main_window, "gallery_manager")
            and self.main_window.gallery_manager.file_pairs_list
        )
        if hasattr(self.main_window, "size_control_panel"):
            self.main_window.size_control_panel.setVisible(is_gallery_populated)

        # Włącz panel filtrów gdy są dane do filtrowania
        if hasattr(self, "filter_panel"):
            self.filter_panel.setEnabled(is_gallery_populated)

    def get_widgets_for_main_window(self):
        """
        Zwraca referencje do widgetów potrzebnych w głównym oknie.

        Returns:
            dict: Słownik z referencjami do widgetów.
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

    def update_thumbnail_size(self, new_size=None):
        """
        Aktualizuje rozmiar miniatur i przerenderowuje galerię.

        Args:
            new_size: Opcjonalny nowy rozmiar (width, height) lub int.
                     Jeśli None, oblicza z suwaka.
        """
        # Metoda pozostawiona dla kompatybilności z wywołaniami z main_window.py
        # Przekazujemy żądanie bezpośrednio do gallery_manager

        if new_size is None:
            if not hasattr(self.main_window, "size_slider"):
                return

            # Pobierz wartość z suwaka
            slider_value = self.main_window.size_slider.value()

            # Oblicz nowy rozmiar
            size_range = (
                self.main_window.max_thumbnail_size
                - self.main_window.min_thumbnail_size
            )
            if size_range <= 0:
                new_size = self.main_window.min_thumbnail_size
            else:
                new_size = self.main_window.min_thumbnail_size + int(
                    (size_range * slider_value) / 100
                )

            # Kwadratowe miniatury
            new_size = (new_size, new_size)

        # Zaktualizuj rozmiar w gallery managerze
        if (
            hasattr(self.main_window, "gallery_manager")
            and self.main_window.gallery_manager
        ):
            self.main_window.gallery_manager.update_thumbnail_size(new_size)
