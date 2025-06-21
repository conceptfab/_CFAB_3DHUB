"""
TabsManager - zarządzanie zakładkami aplikacji.
🚀 ETAP 4 REFAKTORYZACJI: Wydzielenie logiki zakładek z main_window.py
"""

import logging

from PyQt6.QtWidgets import QTabWidget

from src.ui.widgets.file_explorer_tab import FileExplorerTab
from src.ui.widgets.gallery_tab import GalleryTab
from src.ui.widgets.unpaired_files_tab import UnpairedFilesTab


class TabsManager:
    """
    Manager odpowiedzialny za zarządzanie zakładkami aplikacji.
    Obsługuje tworzenie, konfigurację i nawigację między zakładkami.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje TabsManager.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

        # Referencje do zakładek
        self.tab_widget = None
        self.gallery_tab_manager = None
        self.unpaired_files_tab_manager = None
        self.file_explorer_tab = None

    def init_tabs(self):
        """
        Inicjalizuje wszystkie zakładki aplikacji.
        """
        self.logger.debug("Inicjalizacja zakładek aplikacji...")

        # Tworzenie głównego widget'u zakładek
        self.tab_widget = QTabWidget()
        self.main_window.main_layout.addWidget(self.tab_widget)

        # Tworzenie managerów zakładek
        self.gallery_tab_manager = GalleryTab(self.main_window)
        self.unpaired_files_tab_manager = UnpairedFilesTab(self.main_window)
        self.file_explorer_tab = FileExplorerTab(self.main_window)

        # Przypisz managery do main_window
        self.main_window.tab_widget = self.tab_widget
        self.main_window.gallery_tab_manager = self.gallery_tab_manager
        self.main_window.unpaired_files_tab_manager = self.unpaired_files_tab_manager
        self.main_window.file_explorer_tab = self.file_explorer_tab

        # Tworzenie i dodawanie zakładek
        self._create_gallery_tab()
        self._create_unpaired_files_tab()
        self._create_file_explorer_tab()

        # Konfiguracja sygnałów
        self._connect_tab_signals()

        self.logger.debug("Zakładki zostały zainicjalizowane pomyślnie")

    def _create_gallery_tab(self):
        """Tworzy zakładkę galerii."""
        gallery_widget = self.gallery_tab_manager.create_gallery_tab()
        self.tab_widget.addTab(gallery_widget, "Galeria")

        # Pobierz widget'y dla main_window
        gallery_widgets = self.gallery_tab_manager.get_widgets_for_main_window()

        # Przypisz widget'y do main_window
        self.main_window.folder_tree = gallery_widgets["folder_tree"]
        self.main_window.folder_tree_container = gallery_widgets[
            "folder_tree_container"
        ]
        self.main_window.file_system_model = gallery_widgets["file_system_model"]
        self.main_window.tiles_container = gallery_widgets["tiles_container"]
        self.main_window.tiles_layout = gallery_widgets["tiles_layout"]
        self.main_window.scroll_area = gallery_widgets["scroll_area"]
        self.main_window.splitter = gallery_widgets["splitter"]

    def _create_unpaired_files_tab(self):
        """Tworzy zakładkę parowania plików."""
        unpaired_widget = self.unpaired_files_tab_manager.create_unpaired_files_tab()
        self.tab_widget.addTab(unpaired_widget, "Parowanie Plików")

        # Pobierz widget'y dla main_window
        unpaired_widgets = self.unpaired_files_tab_manager.get_widgets_for_main_window()

        # Przypisz widget'y do main_window
        self.main_window.unpaired_files_tab = unpaired_widgets["unpaired_files_tab"]
        self.main_window.unpaired_archives_list_widget = unpaired_widgets[
            "unpaired_archives_list_widget"
        ]
        self.main_window.unpaired_previews_list_widget = unpaired_widgets[
            "unpaired_previews_list_widget"
        ]

    def _create_file_explorer_tab(self):
        """Tworzy zakładkę eksploratora plików."""
        self.tab_widget.addTab(self.file_explorer_tab, "Eksplorator plików")

    def _connect_tab_signals(self):
        """Podłącza sygnały zakładek do odpowiednich slotów."""
        # Sygnały z file explorer tab
        self.file_explorer_tab.folder_changed.connect(self.on_explorer_folder_changed)
        self.file_explorer_tab.file_selected.connect(self.on_explorer_file_selected)

    def on_explorer_folder_changed(self, path: str):
        """
        Obsługa zmiany folderu w eksploratorze.

        Args:
            path: Ścieżka do nowego folderu
        """
        self.logger.info(f"Explorer folder changed to: {path}")
        # Opcjonalnie synchronizuj z głównym folderem roboczym
        # W przyszłości można dodać opcję synchronizacji

    def on_explorer_file_selected(self, file_path: str):
        """
        Obsługa wyboru pliku w eksploratorze.

        Args:
            file_path: Ścieżka do wybranego pliku
        """
        self.logger.debug(f"Plik wybrany w eksploratorze: {file_path}")
        # Opcjonalnie otwórz plik lub pokaż podgląd
        # W przyszłości można dodać obsługę podglądu plików

    def get_current_tab_index(self) -> int:
        """
        Zwraca indeks aktualnie aktywnej zakładki.

        Returns:
            Indeks aktywnej zakładki
        """
        return self.tab_widget.currentIndex() if self.tab_widget else -1

    def set_current_tab_index(self, index: int):
        """
        Ustawia aktywną zakładkę.

        Args:
            index: Indeks zakładki do aktywacji
        """
        if self.tab_widget and 0 <= index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(index)

    def get_tab_count(self) -> int:
        """
        Zwraca liczbę zakładek.

        Returns:
            Liczba zakładek
        """
        return self.tab_widget.count() if self.tab_widget else 0

    def get_tab_widget(self) -> QTabWidget:
        """
        Zwraca widget zakładek.

        Returns:
            QTabWidget z zakładkami
        """
        return self.tab_widget
