"""
UIManager - zarządzanie elementami interfejsu użytkownika.
🚀 ETAP 1: Refaktoryzacja MainWindow - komponent UI
"""

import logging
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenuBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QStatusBar,
    QProgressBar,
    QMessageBox,
    QDialog,
)

from src.ui.directory_tree.manager import DirectoryTreeManager
from src.ui.widgets.gallery_tab import GalleryTab
from src.ui.widgets.unpaired_files_tab import UnpairedFilesTab
from src.ui.widgets.file_explorer_tab import FileExplorerTab
from src.ui.widgets.preferences_dialog import PreferencesDialog


class UIManager:
    """
    Zarządzanie elementami interfejsu użytkownika.
    🚀 ETAP 1: Wydzielony z MainWindow
    """

    def __init__(self, main_window):
        """
        Inicjalizuje UIManager.
        
        Args:
            main_window: Referencja do głównego okna
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def init_ui(self):
        """Inicjalizuje wszystkie elementy UI."""
        self._setup_status_bar()
        self._setup_menu_bar()
        self._create_top_panel()
        self._create_bulk_operations_panel()
        self._setup_tab_widget()
        self._init_managers()

    def _setup_status_bar(self):
        """Konfiguruje pasek statusu."""
        try:
            # Inicjalizacja paska statusu
            self.main_window.status_bar = QStatusBar(self.main_window)
            self.main_window.setStatusBar(self.main_window.status_bar)

            # Inicjalizacja globalnego paska postępu
            self.main_window.progress_bar = QProgressBar()
            self.main_window.progress_bar.setFixedHeight(15)
            self.main_window.progress_bar.setRange(0, 100)
            self.main_window.progress_bar.setValue(0)
            self.main_window.progress_bar.setVisible(False)

            # Etykieta postępu
            self.main_window.progress_label = QLabel("Gotowy")
            self.main_window.progress_label.setStyleSheet("color: gray; font-style: italic;")

            # Dodanie do paska statusu
            self.main_window.status_bar.addWidget(self.main_window.progress_label, 1)
            self.main_window.status_bar.addPermanentWidget(self.main_window.progress_bar, 2)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas konfiguracji paska statusu: {e}")

    def _setup_menu_bar(self):
        """Konfiguruje pasek menu."""
        try:
            menubar = self.main_window.menuBar()

            # Menu Plik
            file_menu = menubar.addMenu("Plik")
            
            # Akcja Preferencje
            preferences_action = QAction("Preferencje", self.main_window)
            preferences_action.triggered.connect(self._show_preferences)
            file_menu.addAction(preferences_action)

            file_menu.addSeparator()

            # Akcja Usuń wszystkie foldery metadanych
            remove_metadata_action = QAction("Usuń wszystkie foldery metadanych", self.main_window)
            remove_metadata_action.triggered.connect(self._remove_all_metadata_folders)
            file_menu.addAction(remove_metadata_action)

            file_menu.addSeparator()

            # Akcja Wyjście
            exit_action = QAction("Wyjście", self.main_window)
            exit_action.triggered.connect(self.main_window.close)
            file_menu.addAction(exit_action)

            # Menu Pomoc
            help_menu = menubar.addMenu("Pomoc")
            
            # Akcja O programie
            about_action = QAction("O programie", self.main_window)
            about_action.triggered.connect(self._show_about)
            help_menu.addAction(about_action)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas konfiguracji paska menu: {e}")

    def _create_top_panel(self):
        """Tworzy górny panel z kontrolkami."""
        # Panel górny
        top_panel = QWidget()
        top_panel_layout = QHBoxLayout(top_panel)
        top_panel_layout.setContentsMargins(5, 5, 5, 5)

        # Przycisk wyboru katalogu
        self.main_window.select_directory_button = QPushButton("Wybierz katalog roboczy")
        self.main_window.select_directory_button.clicked.connect(self._select_working_directory)
        top_panel_layout.addWidget(self.main_window.select_directory_button)

        # Panel kontroli rozmiaru
        self._create_size_control_panel(top_panel_layout)

        # Dodanie do głównego layoutu
        self.main_window.main_layout.addWidget(top_panel)

    def _create_size_control_panel(self, parent_layout):
        """Tworzy panel kontroli rozmiaru miniatur."""
        # Etykieta rozmiaru
        size_label = QLabel("Rozmiar miniatur:")
        parent_layout.addWidget(size_label)

        # Suwak rozmiaru
        self.main_window.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.main_window.size_slider.setRange(0, 100)
        self.main_window.size_slider.setValue(self.main_window.initial_slider_position)
        self.main_window.size_slider.setFixedWidth(200)
        self.main_window.size_slider.valueChanged.connect(self._update_thumbnail_size)
        parent_layout.addWidget(self.main_window.size_slider)

        # Etykieta wartości
        self.main_window.size_value_label = QLabel(f"{self.main_window.current_thumbnail_size}px")
        self.main_window.size_value_label.setFixedWidth(50)
        parent_layout.addWidget(self.main_window.size_value_label)

        # Spacer
        parent_layout.addStretch()

    def _create_bulk_operations_panel(self):
        """Tworzy panel operacji masowych."""
        # Panel operacji masowych
        self.main_window.bulk_operations_panel = QWidget()
        bulk_layout = QHBoxLayout(self.main_window.bulk_operations_panel)
        bulk_layout.setContentsMargins(5, 5, 5, 5)

        # Przycisk Wyczyść zaznaczenia
        clear_selection_button = QPushButton("Wyczyść zaznaczenia")
        clear_selection_button.clicked.connect(self._clear_all_selections)
        bulk_layout.addWidget(clear_selection_button)

        # Przycisk Zaznacz wszystkie
        select_all_button = QPushButton("Zaznacz wszystkie")
        select_all_button.clicked.connect(self._select_all_tiles)
        bulk_layout.addWidget(select_all_button)

        # Przycisk Usuń zaznaczone
        self.main_window.bulk_delete_button = QPushButton("Usuń zaznaczone")
        self.main_window.bulk_delete_button.clicked.connect(self.main_window.perform_bulk_delete)
        bulk_layout.addWidget(self.main_window.bulk_delete_button)

        # Przycisk Przenieś zaznaczone
        self.main_window.bulk_move_button = QPushButton("Przenieś zaznaczone")
        self.main_window.bulk_move_button.clicked.connect(self.main_window.perform_bulk_move)
        bulk_layout.addWidget(self.main_window.bulk_move_button)

        # Spacer
        bulk_layout.addStretch()

        # Panel początkowo ukryty
        self.main_window.bulk_operations_panel.setVisible(False)

        # Dodanie do głównego layoutu
        self.main_window.main_layout.addWidget(self.main_window.bulk_operations_panel)

    def _setup_tab_widget(self):
        """Konfiguruje widget zakładek."""
        # TabWidget jako główny kontener widoków
        self.main_window.tab_widget = QTabWidget()
        
        # Style CSS dla zakładek - kompaktowe
        self.main_window.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3F3F46;
                background-color: #1C1C1C;
                margin: 0px;
                padding: 2px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #252526;
                color: #CCCCCC;
                padding: 6px 12px;
                margin-right: 2px;
                border: 1px solid #3F3F46;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #007ACC;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #264F78;
            }
        """)

        self.main_window.main_layout.addWidget(self.main_window.tab_widget)

    def _init_managers(self):
        """Inicjalizuje managery i zakładki."""
        # Directory Tree Manager - wymaga folder_tree (QTreeView) i parent_window
        # Folder tree będzie utworzony w GalleryTab, więc na razie przekazujemy None
        # i zainicjalizujemy później w _post_init_managers()
        self.main_window.directory_tree_manager = None

        # Zakładka Galerii
        self.main_window.gallery_tab = GalleryTab(self.main_window)
        gallery_widget = self.main_window.gallery_tab.create_gallery_tab()
        self.main_window.tab_widget.addTab(gallery_widget, "Galeria")

        # Zakładka Nieparowanych Plików
        self.main_window.unpaired_files_tab = UnpairedFilesTab(self.main_window)
        unpaired_widget = self.main_window.unpaired_files_tab.create_unpaired_files_tab()
        self.main_window.tab_widget.addTab(unpaired_widget, "Nieparowane pliki")

        # Zakładka File Explorer - FileExplorerTab dziedziczy z QWidget więc używamy go bezpośrednio
        self.main_window.file_explorer_tab = FileExplorerTab(self.main_window)
        self.main_window.tab_widget.addTab(self.main_window.file_explorer_tab, "Eksplorator plików")

    def _post_init_managers(self):
        """Inicjalizuje managery które wymagają już utworzonych komponentów UI."""
        # Directory Tree Manager - teraz możemy go zainicjalizować z folder_tree z GalleryTab
        if hasattr(self.main_window.gallery_tab, 'folder_tree'):
            self.main_window.directory_tree_manager = DirectoryTreeManager(
                self.main_window.gallery_tab.folder_tree, 
                self.main_window
            )
        else:
            self.logger.warning("GalleryTab nie ma atrybutu folder_tree, DirectoryTreeManager nie został zainicjalizowany")

    def show_preferences_loaded_confirmation(self):
        """Pokazuje potwierdzenie wczytania preferencji."""
        self.main_window.status_bar.showMessage("Preferencje zostały wczytane", 3000)

    # Metody obsługi zdarzeń - delegowanie do głównego okna lub odpowiednich komponentów
    def _show_preferences(self):
        """Pokazuje okno preferencji."""
        dialog = PreferencesDialog(self.main_window)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.main_window._handle_preferences_changed()

    def _remove_all_metadata_folders(self):
        """Usuwa wszystkie foldery metadanych."""
        # Delegowanie do głównego okna
        if hasattr(self.main_window, 'remove_all_metadata_folders'):
            self.main_window.remove_all_metadata_folders()

    def _show_about(self):
        """Pokazuje okno o programie."""
        QMessageBox.about(
            self.main_window,
            "O programie CFAB_3DHUB",
            "CFAB_3DHUB v1.0\n\n"
            "Aplikacja do zarządzania plikami 3D i ich podglądami.\n\n"
            "🚀 ETAP 1: Zrefaktoryzowana architektura"
        )

    def _select_working_directory(self):
        """Wybiera katalog roboczy."""
        # Delegowanie do głównego okna
        if hasattr(self.main_window, '_select_working_directory'):
            self.main_window._select_working_directory()

    def _update_thumbnail_size(self):
        """Aktualizuje rozmiar miniatur."""
        # Delegowanie do głównego okna
        if hasattr(self.main_window, '_update_thumbnail_size'):
            self.main_window._update_thumbnail_size()

    def _clear_all_selections(self):
        """Czyści wszystkie zaznaczenia."""
        # Delegowanie do głównego okna
        if hasattr(self.main_window, '_clear_all_selections'):
            self.main_window._clear_all_selections()

    def _select_all_tiles(self):
        """Zaznacza wszystkie kafelki."""
        # Delegowanie do głównego okna
        if hasattr(self.main_window, '_select_all_tiles'):
            self.main_window._select_all_tiles() 