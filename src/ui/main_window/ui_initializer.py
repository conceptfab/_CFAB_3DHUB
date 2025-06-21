"""
UIInitializer - wydzielona inicjalizacja UI z MainWindow.
🚀 ETAP 2 REFAKTORYZACJI: Wydzielenie logiki UI z main_window.py

Odpowiedzialności:
- Inicjalizacja okna aplikacji (window configuration)
- Tworzenie elementów interfejsu użytkownika
- Konfiguracja layoutów i widgetów
- Inicjalizacja przycisków expand/collapse
"""

import logging

from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from src.utils.logging_config import get_main_window_logger


class UIInitializer:
    """
    Wydzielona inicjalizacja UI z MainWindow.
    Koncentruje się tylko na tworzeniu elementów interfejsu.

    ELIMINUJE Z MAIN_WINDOW:
    - Metodę _init_window() (~18 linii)
    - Metodę _init_ui() (~15 linii)
    - Metodę _init_expand_collapse_buttons() (~13 linii)
    - Razem: ~46 linii redukcji
    """

    def __init__(self, main_window):
        """
        Inicjalizuje UIInitializer.

        Args:
            main_window: Referencja do instancji MainWindow
        """
        self.main_window = main_window
        self.logger = get_main_window_logger()

        self.logger.debug("UIInitializer zainicjalizowany")

    def init_window(self):
        """
        Inicjalizuje okno aplikacji.
        Przeniesione z MainWindow._init_window()
        """
        self.logger.debug("Inicjalizacja okna przez UIInitializer...")

        # Delegacja konfiguracji okna do WindowInitializationManager
        self.main_window.window_initialization_manager.init_window_configuration()

        # Thread pool konfiguracja
        self._configure_thread_pool()

        # Central widget i main layout
        self._create_central_widget_and_layout()

        self.logger.debug("✅ Okno zainicjalizowane przez UIInitializer")

    def _configure_thread_pool(self):
        """Konfiguruje thread pool dla aplikacji."""
        self.main_window.thread_pool = QThreadPool.globalInstance()
        if self.main_window.thread_pool:
            thread_count = self.main_window.thread_pool.maxThreadCount()
            self.logger.debug(f"Maksymalna liczba wątków: {thread_count}")

    def _create_central_widget_and_layout(self):
        """Tworzy central widget i główny layout."""
        self.main_window.central_widget = QWidget()
        self.main_window.setCentralWidget(self.main_window.central_widget)

        self.main_window.main_layout = QVBoxLayout(self.main_window.central_widget)
        self.main_window.main_layout.setContentsMargins(2, 2, 2, 2)
        self.main_window.main_layout.setSpacing(3)

    def init_ui_components(self):
        """
        Inicjalizuje komponenty interfejsu użytkownika.
        Przeniesione z MainWindow._init_ui()
        """
        self.logger.debug("Inicjalizacja komponentów UI przez UIInitializer...")

        # UI Manager - podstawowe elementy
        self.main_window.ui_manager.init_ui()

        # Tabs Manager - zakładki
        self._initialize_tabs()

        # Unpaired widgets - dodatkowe elementy z unpaired_files_tab
        self._configure_unpaired_widgets()

        self.logger.debug("✅ Komponenty UI zainicjalizowane przez UIInitializer")

    def _initialize_tabs(self):
        """Inicjalizuje system zakładek."""
        self.main_window.tabs_manager.init_tabs()

        # TabsManager automatycznie tworzy i przypisuje referencje:
        # - self.tab_widget
        # - self.gallery_tab_manager
        # - self.unpaired_files_tab_manager
        # - self.file_explorer_tab
        # - wszystkie widget'y z zakładek

    def _configure_unpaired_widgets(self):
        """Konfiguruje dodatkowe widget'y z unpaired_files_tab."""
        try:
            unpaired_widgets = (
                self.main_window.unpaired_files_tab_manager.get_widgets_for_main_window()
            )

            self.main_window.unpaired_previews_layout = unpaired_widgets[
                "unpaired_previews_layout"
            ]
            self.main_window.pair_manually_button = unpaired_widgets[
                "pair_manually_button"
            ]

            self.logger.debug("✅ Unpaired widgets skonfigurowane")

        except Exception as e:
            self.logger.error(f"❌ Błąd konfiguracji unpaired widgets: {e}")

    def init_expand_collapse_buttons(self):
        """
        Inicjalizuje przyciski expand/collapse dla drzewa katalogów.
        Przeniesione z MainWindow._init_expand_collapse_buttons()
        """
        self.logger.debug("Inicjalizacja przycisków expand/collapse...")

        if not hasattr(self.main_window, "directory_tree_manager"):
            self.logger.warning("⚠️ DirectoryTreeManager nie istnieje")
            return

        if not hasattr(
            self.main_window.directory_tree_manager, "create_expand_collapse_buttons"
        ):
            self.logger.warning("⚠️ create_expand_collapse_buttons nie dostępne")
            return

        try:
            # Tworzenie przycisków przez DirectoryTreeManager
            expand_button, collapse_button = (
                self.main_window.directory_tree_manager.create_expand_collapse_buttons()
            )

            # Dodawanie do layoutu jeśli folder_tree_container istnieje
            if hasattr(self.main_window, "folder_tree_container"):
                self._add_buttons_to_container(expand_button, collapse_button)
                self.logger.debug("✅ Przyciski expand/collapse dodane do kontenera")
            else:
                self.logger.warning("⚠️ folder_tree_container nie istnieje")

        except Exception as e:
            self.logger.error(f"❌ Błąd tworzenia przycisków expand/collapse: {e}")

    def _add_buttons_to_container(self, expand_button, collapse_button):
        """Dodaje przyciski expand/collapse do kontenera."""
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(2, 2, 2, 2)
        buttons_layout.setSpacing(2)
        buttons_layout.addWidget(expand_button)
        buttons_layout.addWidget(collapse_button)
        buttons_layout.addStretch(1)

        # Wstawienie layoutu na początek kontenera
        self.main_window.folder_tree_container.layout().insertLayout(0, buttons_layout)

    def get_initialization_status(self):
        """
        Zwraca status inicjalizacji UI.

        Returns:
            dict: Status poszczególnych komponentów UI
        """
        return {
            "window_initialized": hasattr(self.main_window, "central_widget"),
            "thread_pool_configured": hasattr(self.main_window, "thread_pool"),
            "main_layout_created": hasattr(self.main_window, "main_layout"),
            "tabs_initialized": hasattr(self.main_window, "tab_widget"),
            "unpaired_widgets_configured": hasattr(
                self.main_window, "unpaired_previews_layout"
            ),
            "expand_collapse_buttons": hasattr(
                self.main_window, "folder_tree_container"
            ),
        }
