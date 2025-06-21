"""
UI Manager dla MainWindow - zarządzanie elementami interfejsu użytkownika.
Część refaktoryzacji ETAP 1: MainWindow.
"""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class UIManager:
    """
    Zarządzanie elementami interfejsu użytkownika MainWindow.

    Odpowiedzialności:
    - Tworzenie menu bar
    - Tworzenie paneli UI (top panel, bulk operations, size control)
    - Zarządzanie layoutami
    - Obsługa preferencji UI
    """

    def __init__(self, main_window):
        """
        Inicjalizuje UIManager.

        Args:
            main_window: Referencja do głównego okna MainWindow
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def setup_menu_bar(self):
        """Tworzy menu bar z pełną funkcjonalnością."""
        menubar = self.main_window.menuBar()

        # Menu Plik
        file_menu = menubar.addMenu("&Plik")
        file_menu.addAction(
            "&Otwórz folder...", self.main_window._select_working_directory
        )
        file_menu.addSeparator()
        file_menu.addAction("&Wyjście", self.main_window.close)

        # Menu Narzędzia
        tools_menu = menubar.addMenu("&Narzędzia")
        tools_menu.addAction(
            "🗑️ Usuń wszystkie foldery .app_metadata",
            self.main_window.remove_all_metadata_folders,
        )
        tools_menu.addSeparator()
        tools_menu.addAction("⚙️ Preferencje...", self.show_preferences)

        # Menu Widok
        view_menu = menubar.addMenu("&Widok")
        view_menu.addAction("🔄 Odśwież", self.main_window.refresh_all_views)

        # Menu Ulubione
        favorites_menu = menubar.addMenu("&Ulubione")
        favorites_menu.addAction(
            "⚙️ Konfiguruj ulubione...", self.show_favorite_folders_config
        )

        # Menu Pomoc
        help_menu = menubar.addMenu("&Pomoc")
        help_menu.addAction("ℹ️ O programie...", self.show_about)

    def show_preferences(self):
        """Wyświetla okno preferencji."""
        try:
            # Import tylko jeśli nie jest jeszcze zaimportowany
            if not hasattr(self.main_window, "_preferences_dialog_class"):
                from src.ui.widgets.preferences_dialog import PreferencesDialog

                self.main_window._preferences_dialog_class = PreferencesDialog

            dialog = self.main_window._preferences_dialog_class(self.main_window)
            # Połącz sygnał zmiany preferencji
            dialog.preferences_changed.connect(self._handle_preferences_changed)
            result = dialog.exec()

            if result == QDialog.DialogCode.Accepted:
                logging.info("Okno preferencji zamknięte - zmiany zaakceptowane")
            else:
                logging.info("Okno preferencji anulowane")

        except ImportError:
            QMessageBox.information(
                self.main_window,
                "Preferencje",
                "Okno preferencji będzie dostępne w przyszłej wersji.",
            )
            logging.warning("PreferencjesDialog nie został jeszcze zaimplementowany")

    def _handle_preferences_changed(self):
        """Obsługuje zmiany w preferencjach aplikacji."""
        try:
            logging.info("Preferencje zostały zmienione - aplikuję nowe ustawienia")

            # UWAGA: NIE tworzymy nowej instancji AppConfig!
            # Tylko przeładowujemy istniejącą konfigurację
            self.main_window.app_config.reload()

            # Zastosuj nowe ustawienia do UI
            if hasattr(self.main_window, "gallery_manager"):
                # Odśwież cache miniaturek jeśli zmienił się rozmiar
                if hasattr(self.main_window.gallery_manager, "thumbnail_cache"):
                    max_entries = self.main_window.app_config.get(
                        "thumbnail_cache_max_entries", 2000
                    )
                    max_memory = self.main_window.app_config.get(
                        "thumbnail_cache_max_memory_mb", 500
                    )
                    self.main_window.gallery_manager.thumbnail_cache.update_limits(
                        max_entries, max_memory
                    )

            # Odśwież slider miniatur
            if hasattr(self.main_window, "size_slider"):
                saved_position = (
                    self.main_window.app_config.get_thumbnail_slider_position()
                )
                if saved_position != self.main_window.size_slider.value():
                    self.main_window.size_slider.setValue(saved_position)
                    self.main_window._update_thumbnail_size()

            # Odśwież widok jeśli jest otwarty folder
            if self.main_window.controller.current_directory:
                self.main_window.refresh_all_views()

            logging.info("Nowe ustawienia preferencji zostały zastosowane")

        except Exception as e:
            logging.error(f"Błąd podczas aplikowania nowych preferencji: {e}")
            QMessageBox.warning(
                self.main_window,
                "Ostrzeżenie",
                "Niektóre nowe ustawienia mogą wymagać ponownego uruchomienia aplikacji.",
            )

    def show_favorite_folders_config(self):
        """Wyświetla dialog konfiguracji ulubionych folderów."""
        try:
            from src.ui.widgets.favorite_folders_dialog import FavoriteFoldersDialog

            dialog = FavoriteFoldersDialog(self.main_window)
            dialog.configuration_saved.connect(self._on_favorite_folders_updated)
            dialog.exec()
        except Exception as e:
            self.logger.error(f"Błąd otwierania dialogu ulubionych folderów: {e}")

    def _on_favorite_folders_updated(self):
        """Obsługuje aktualizację konfiguracji ulubionych folderów."""
        # Odśwież pasek ulubionych folderów w galerii
        if hasattr(self.main_window, "gallery_tab") and self.main_window.gallery_tab:
            if hasattr(self.main_window.gallery_tab, "update_favorite_folders_bar"):
                self.main_window.gallery_tab.update_favorite_folders_bar()

    def show_about(self):
        """Wyświetla informacje o programie."""
        QMessageBox.about(
            self.main_window,
            "O programie",
            "CFAB_3DHUB v1.0\n\n"
            "Aplikacja do zarządzania parami plików archiwum-podgląd\n\n"
            "Funkcje:\n"
            "• Automatyczne parowanie plików\n"
            "• Zarządzanie metadanymi\n"
            "• Operacje masowe na plikach\n"
            "• Zaawansowane filtrowanie",
        )

    def remove_all_metadata_folders(self):
        """Usuwa wszystkie foldery .app_metadata z folderu roboczego."""
        if not self.main_window.controller.current_directory:
            QMessageBox.warning(
                self.main_window, "Uwaga", "Nie wybrano folderu roboczego."
            )
            return

        reply = QMessageBox.question(
            self.main_window,
            "Potwierdzenie",
            "Czy na pewno chcesz usunąć wszystkie foldery .app_metadata?\n"
            "Ta operacja jest nieodwracalna.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.start_metadata_cleanup_worker()

    def start_metadata_cleanup_worker(self):
        """Uruchamia worker do usuwania folderów metadanych."""
        import shutil
        from pathlib import Path

        try:
            self.main_window._show_progress(0, "Szukanie folderów .app_metadata...")

            # Znajdź wszystkie foldery .app_metadata
            metadata_folders = []
            root_path = Path(self.main_window.controller.current_directory)

            for folder in root_path.rglob(".app_metadata"):
                if folder.is_dir():
                    metadata_folders.append(folder)

            if not metadata_folders:
                QMessageBox.information(
                    self.main_window,
                    "Informacja",
                    "Nie znaleziono folderów .app_metadata.",
                )
                self.main_window._hide_progress()
                return

            total_folders = len(metadata_folders)
            self.main_window._show_progress(
                10, f"Znaleziono {total_folders} folderów do usunięcia..."
            )

            # Usuń foldery
            deleted_count = 0
            for i, folder in enumerate(metadata_folders):
                try:
                    shutil.rmtree(folder)
                    deleted_count += 1
                    progress = 10 + int((i + 1) / total_folders * 80)
                    self.main_window._show_progress(
                        progress, f"Usuwanie {i+1}/{total_folders}..."
                    )
                except Exception as e:
                    logging.error(f"Błąd podczas usuwania {folder}: {e}")

            self.main_window._show_progress(100, f"Usunięto {deleted_count} folderów")
            QMessageBox.information(
                self.main_window,
                "Zakończono",
                f"Usunięto {deleted_count} z {total_folders} folderów .app_metadata",
            )

        except Exception as e:
            error_msg = f"Błąd podczas czyszczenia metadanych: {e}"
            logging.error(error_msg)
            QMessageBox.critical(self.main_window, "Błąd", error_msg)
            self.main_window._hide_progress()

    def create_top_panel(self):
        """
        Tworzy panel górny z przyciskami i kontrolkami.
        """
        self.main_window.top_panel = QWidget()
        self.main_window.top_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.main_window.top_layout = QHBoxLayout(self.main_window.top_panel)
        self.main_window.top_layout.setContentsMargins(0, 0, 0, 0)

        # Przycisk wyboru folderu
        self.main_window.select_folder_button = QPushButton("Wybierz Folder Roboczy")
        self.main_window.select_folder_button.clicked.connect(
            self.main_window._select_working_directory
        )
        self.main_window.top_layout.addWidget(self.main_window.select_folder_button)

        # Przycisk czyszczenia cache i metadanych
        self.main_window.clear_cache_button = QPushButton(
            "Odśwież (Wyczyść Cache + Metadane)"
        )
        self.main_window.clear_cache_button.clicked.connect(
            self.main_window._force_refresh
        )
        self.main_window.top_layout.addWidget(self.main_window.clear_cache_button)

        # Panel kontroli rozmiaru
        self.create_size_control_panel()

        # Dodaj panel do głównego layoutu
        self.main_window.main_layout.addWidget(self.main_window.top_panel)

    def create_size_control_panel(self):
        """
        Tworzy panel kontroli rozmiaru miniatur.
        """
        self.main_window.size_control_panel = QWidget()
        self.main_window.size_control_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.main_window.size_control_layout = QHBoxLayout(
            self.main_window.size_control_panel
        )
        self.main_window.size_control_layout.setContentsMargins(0, 0, 0, 0)

        # Label dla suwaka
        self.main_window.size_label = QLabel("Rozmiar miniatur:")
        self.main_window.size_control_layout.addWidget(self.main_window.size_label)

        # Suwak rozmiaru miniatur
        self.main_window.size_slider = QSlider()
        self.main_window.size_slider.setOrientation(Qt.Orientation.Horizontal)
        self.main_window.size_slider.setMinimum(0)
        self.main_window.size_slider.setMaximum(100)

        # Ustawienie wartości początkowej suwaka na wymuszone 50%
        self.main_window.size_slider.setValue(self.main_window.initial_slider_position)

        self.main_window.size_slider.sliderReleased.connect(
            self.main_window._update_thumbnail_size
        )
        self.main_window.size_control_layout.addWidget(self.main_window.size_slider)

        self.main_window.top_layout.addStretch(1)
        self.main_window.top_layout.addWidget(self.main_window.size_control_panel)

    def create_bulk_operations_panel(self):
        """
        Creates the bulk operations panel for selected tiles.
        """
        self.main_window.bulk_operations_panel = QWidget()
        self.main_window.bulk_operations_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.main_window.bulk_operations_panel.setVisible(False)  # Hidden by default

        # Apply styling for better visibility
        self.main_window.bulk_operations_panel.setStyleSheet(
            """
            QWidget {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                margin: 2px;
            }
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
            QPushButton:pressed {
                background-color: #285a9b;
            }
            QLabel {
                color: #333;
                font-weight: bold;
            }
        """
        )

        bulk_layout = QHBoxLayout(self.main_window.bulk_operations_panel)
        bulk_layout.setContentsMargins(5, 3, 5, 3)

        # Selected count label
        self.main_window.selected_count_label = QLabel("Zaznaczone: 0")
        bulk_layout.addWidget(self.main_window.selected_count_label)

        bulk_layout.addStretch(1)

        # Select all button
        self.main_window.select_all_button = QPushButton("Zaznacz wszystkie")
        self.main_window.select_all_button.clicked.connect(
            self.main_window._select_all_tiles
        )
        bulk_layout.addWidget(self.main_window.select_all_button)

        # Clear selection button
        self.main_window.clear_selection_button = QPushButton("Wyczyść zaznaczenie")
        self.main_window.clear_selection_button.clicked.connect(
            self.main_window._clear_all_selections
        )
        bulk_layout.addWidget(self.main_window.clear_selection_button)

        # Separator
        separator = QLabel("|")
        separator.setStyleSheet("color: #999; margin: 0 10px;")
        bulk_layout.addWidget(separator)

        # Bulk move button
        self.main_window.bulk_move_button = QPushButton("Przenieś zaznaczone")
        self.main_window.bulk_move_button.clicked.connect(
            self.main_window._perform_bulk_move
        )
        bulk_layout.addWidget(self.main_window.bulk_move_button)

        # Bulk delete button
        self.main_window.bulk_delete_button = QPushButton("Usuń zaznaczone")
        self.main_window.bulk_delete_button.setStyleSheet(
            """
            QPushButton {
                background-color: #e74c3c;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """
        )
        self.main_window.bulk_delete_button.clicked.connect(
            self.main_window._perform_bulk_delete
        )
        bulk_layout.addWidget(self.main_window.bulk_delete_button)

        self.main_window.main_layout.addWidget(self.main_window.bulk_operations_panel)

    def init_ui(self):
        """
        Inicjalizuje wszystkie elementy interfejsu użytkownika.
        """
        # Najpierw tworzymy menu bar
        self.setup_menu_bar()

        # Panel górny
        self.create_top_panel()

        # Panel filtrów przeniesiony do zakładki galerii
        # self.filter_panel będzie ustawiony przez GalleryTab

        # Bulk operations panel
        self.create_bulk_operations_panel()
