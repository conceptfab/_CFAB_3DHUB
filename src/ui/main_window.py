"""
Główne okno aplikacji - zrefaktoryzowana wersja ETAP 2.
Podział monolitycznej klasy na komponenty zarządzające.
"""

import logging
import os
from typing import List, Optional

from PyQt6.QtCore import QThread, QThreadPool, QTimer
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from src import app_config
from src.controllers.main_window_controller import MainWindowController
from src.logic import file_operations, metadata_manager
from src.models.file_pair import FilePair
from src.services.file_operations_service import FileOperationsService
from src.services.scanning_service import ScanningService
from src.services.thread_coordinator import ThreadCoordinator
from src.ui.components import EventHandler, TabManager, UIManager
from src.ui.delegates.workers import DataProcessingWorker
from src.ui.directory_tree_manager import DirectoryTreeManager
from src.ui.file_operations_ui import FileOperationsUI
from src.ui.gallery_manager import GalleryManager
from src.ui.widgets.filter_panel import FilterPanel
from src.ui.widgets.preview_dialog import PreviewDialog
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji CFAB_3DHUB - zrefaktoryzowana wersja ETAP 2.
    
    Używa komponentów zarządzających zamiast monolitycznej klasy:
    - UIManager: zarządzanie podstawowymi elementami UI
    - EventHandler: obsługa zdarzeń użytkownika
    - TabManager: zarządzanie zakładkami i ich zawartością
    """

    def __init__(self):
        """
        Inicjalizuje główne okno aplikacji.
        """
        super().__init__()
        self._init_data()
        self._init_window()
        self._init_components()
        self._init_ui()
        self._init_managers()

        # Automatyczne ładowanie ostatniego folderu roboczego
        self._auto_load_last_folder()

        logging.info("Główne okno aplikacji zostało zainicjalizowane (ETAP 2)")

    def _init_data(self):
        """Inicjalizuje dane aplikacji."""
        # KRYTYCZNE: AppConfig musi być pierwsze
        self.app_config = app_config.AppConfig()

        # ETAP 2: MVC Controller - centralna logika biznesowa
        self.controller = MainWindowController(self)

        # LEGACY: Zachowane dla kompatybilności (stopniowe usuwanie)
        self.file_operations_service = FileOperationsService()
        self.scanning_service = ScanningService()

        # Stan aplikacji
        self.current_working_directory = None
        self.all_file_pairs: List[FilePair] = []
        self.unpaired_archives: List[str] = []
        self.unpaired_previews: List[str] = []
        self.selected_tiles: set[FilePair] = set()

        # Wątki
        self.scan_thread = None
        self.scan_worker = None
        self.data_processing_thread = None
        self.data_processing_worker = None

    def _init_window(self):
        """Inicjalizuje okno aplikacji."""
        # Timer do opóźnienia odświeżania galerii
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._update_gallery_view)

        # Konfiguracja rozmiaru miniatur
        self.min_thumbnail_size = self.app_config.min_thumbnail_size
        self.max_thumbnail_size = self.app_config.max_thumbnail_size
        
        # Wymuś początkową pozycję suwaka na 50%
        self.initial_slider_position = 50
        
        # Oblicz current_thumbnail_size
        size_range = self.max_thumbnail_size - self.min_thumbnail_size
        if size_range <= 0:
            self.current_thumbnail_size = self.min_thumbnail_size
        else:
            self.current_thumbnail_size = self.min_thumbnail_size + int(
                (size_range * self.initial_slider_position) / 100
            )

        # Konfiguracja okna
        self.setWindowTitle("CFAB_3DHUB")
        self.setMinimumSize(800, 600)

        # Thread pool
        self.thread_pool = QThreadPool.globalInstance()
        
        # Centralny widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

    def _init_components(self):
        """Inicjalizuje komponenty zarządzające."""
        # ETAP 2: Komponenty zarządzające zamiast monolitycznej klasy
        self.ui_manager = UIManager(self)
        self.event_handler = EventHandler(self)
        self.tab_manager = TabManager(self)

    def _init_ui(self):
        """Inicjalizuje elementy interfejsu użytkownika."""
        # Pasek statusu
        status_bar = self.ui_manager.setup_status_bar()
        self.setStatusBar(status_bar)

        # Menu bar
        self.setup_menu_bar()

        # Panel górny
        top_panel = self.ui_manager.create_top_panel()
        self.main_layout.addWidget(top_panel)

        # Panel filtrów
        self.filter_panel = self.ui_manager.create_filter_panel()
        self.main_layout.addWidget(self.filter_panel)

        # Panel operacji masowych
        bulk_panel = self.ui_manager.create_bulk_operations_panel()
        self.main_layout.addWidget(bulk_panel)

        # TabWidget jako główny kontener
        self.tab_widget = self.ui_manager.create_tab_widget()
        self.main_layout.addWidget(self.tab_widget)

        # Zakładka galerii
        gallery_tab = self.tab_manager.create_gallery_tab()
        self.tab_widget.addTab(gallery_tab, "Galeria")

        # Zakładka niesparowanych plików
        unpaired_tab = self.tab_manager.create_unpaired_files_tab()
        self.tab_widget.addTab(unpaired_tab, "Parowanie Plików")

    def _init_managers(self):
        """Inicjalizuje managerów UI."""
        # Thread coordinator
        self.thread_coordinator = ThreadCoordinator()

        # Directory tree manager
        self.directory_tree_manager = DirectoryTreeManager(self.folder_tree, self)

        # Kontrolki expand/collapse dla drzewa
        if hasattr(self, 'folder_tree_container'):
            expand_controls = self.directory_tree_manager.setup_expand_collapse_controls()
            layout = self.folder_tree_container.layout()
            if layout:
                layout.insertWidget(0, expand_controls)

        # Gallery manager
        self.gallery_manager = GalleryManager(self.tiles_container, self.tiles_layout)

        # File operations UI
        self.file_operations_ui = FileOperationsUI(self)

        # Podłącz sygnały
        if hasattr(self, 'folder_tree'):
            self.folder_tree.clicked.connect(self._folder_tree_item_clicked)

    def setup_menu_bar(self):
        """Tworzy menu bar z pełną funkcjonalnością."""
        menubar = self.menuBar()

        # Menu Plik
        file_menu = menubar.addMenu("&Plik")
        file_menu.addAction("&Otwórz folder...", self._select_working_directory)
        file_menu.addSeparator()
        file_menu.addAction("&Wyjście", self.close)

        # Menu Narzędzia
        tools_menu = menubar.addMenu("&Narzędzia")
        tools_menu.addAction("🗑️ Usuń wszystkie foldery .app_metadata", self.remove_all_metadata_folders)
        tools_menu.addSeparator()
        tools_menu.addAction("⚙️ Preferencje...", self.show_preferences)

        # Menu Widok
        view_menu = menubar.addMenu("&Widok")
        view_menu.addAction("🔄 Odśwież", self.refresh_all_views)

        # Menu Pomoc
        help_menu = menubar.addMenu("&Pomoc")
        help_menu.addAction("ℹ️ O programie...", self.show_about)

    def show_preferences(self):
        """Wyświetla okno preferencji."""
        from src.ui.widgets.preferences_dialog import PreferencesDialog
        
        dialog = PreferencesDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self._handle_preferences_changed()

    def _handle_preferences_changed(self):
        """Obsługuje zmiany w preferencjach aplikacji."""
        from PyQt6.QtWidgets import QMessageBox
        
        logging.info("Preferencje zostały zmienione")
        QMessageBox.information(
            self,
            "Preferencje",
            "Preferencje zostały zapisane.\n\n"
            "Niektóre nowe ustawienia mogą wymagać ponownego uruchomienia aplikacji.",
        )

    def remove_all_metadata_folders(self):
        """Usuwa wszystkie foldery .app_metadata."""
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            "Potwierdzenie usuwania",
            "Czy na pewno chcesz usunąć wszystkie foldery .app_metadata?\n\n"
            "Ta operacja jest nieodwracalna!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                count = metadata_manager.remove_all_metadata_folders(
                    self.current_working_directory or ""
                )
                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Usunięto {count} folderów .app_metadata"
                )
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Błąd",
                    f"Błąd podczas usuwania folderów:\n{str(e)}"
                )

    def show_about(self):
        """Wyświetla informacje o programie."""
        from PyQt6.QtWidgets import QMessageBox
        
        QMessageBox.about(
            self,
            "O programie",
            "CFAB_3DHUB v1.0\n\n"
            "Aplikacja do zarządzania parami plików archiwum-podgląd\n\n"
            "Funkcje:\n"
            "• Automatyczne parowanie plików\n"
            "• Zarządzanie metadanymi\n"            "• Operacje masowe na plikach\n"
            "• Zaawansowane filtrowanie",
        )

    def _auto_load_last_folder(self):
        """Automatycznie ładuje ostatni folder roboczy jeśli włączone w preferencjach."""
        if self.app_config.get("auto_load_last_folder", False):
            last_folder = self.app_config.get("default_folder_path", "")
            if last_folder and os.path.exists(last_folder):
                logging.info(f"Auto-loading ostatniego folderu: {last_folder}")
                self._is_auto_loading = True
                self.event_handler.handle_folder_selection(last_folder)
                delattr(self, '_is_auto_loading')

    # ====================== DELEGACJA DO KOMPONENTÓW ======================

    def _select_working_directory(self, directory_path=None):
        """Deleguje wybór folderu do EventHandler."""
        self.event_handler.handle_folder_selection(directory_path)

    def _force_refresh(self):
        """Deleguje odświeżanie do EventHandler."""
        self.event_handler.handle_force_refresh()

    def _update_thumbnail_size(self):
        """Deleguje aktualizację rozmiaru miniatur do EventHandler."""
        self.event_handler.handle_thumbnail_size_update()

    def _clear_all_selections(self):
        """Deleguje czyszczenie zaznaczeń do EventHandler."""
        self.event_handler.handle_bulk_selection_clear()

    def _select_all_tiles(self):
        """Deleguje zaznaczenie wszystkich do EventHandler."""
        self.event_handler.handle_bulk_selection_all()

    def _perform_bulk_delete(self):
        """Deleguje masowe usuwanie do EventHandler."""
        self.event_handler.handle_bulk_delete()

    def _perform_bulk_move(self):
        """Deleguje masowe przenoszenie do EventHandler."""
        self.event_handler.handle_bulk_move()

    def _update_unpaired_files_lists(self):
        """Deleguje aktualizację list do TabManager."""
        self.tab_manager.update_unpaired_files_lists()

    def _show_progress(self, percent: int, message: str):
        """Deleguje wyświetlanie postępu do UIManager."""
        self.ui_manager.update_progress(percent, message)

    def _hide_progress(self):
        """Deleguje ukrywanie postępu do UIManager."""
        self.ui_manager.hide_progress()

    def _update_bulk_operations_visibility(self):
        """Deleguje aktualizację widoczności do UIManager."""
        self.ui_manager.update_bulk_operations_visibility()

    def closeEvent(self, event):
        """Deleguje zamykanie do EventHandler."""
        self.event_handler.handle_close_event(event)

    # ====================== METODY BIZNESOWE (ZACHOWANE) ======================

    def _clear_all_data_and_views(self):
        """Czyści wszystkie dane plików i odpowiednie widoki."""
        self.all_file_pairs = []
        self.unpaired_archives = []
        self.unpaired_previews = []

        if hasattr(self, 'gallery_manager'):
            self.gallery_manager.clear_gallery()
        if hasattr(self, 'filter_panel'):
            self.filter_panel.setEnabled(False)
            
        self._clear_unpaired_files_lists()
        self.setWindowTitle("CFAB_3DHUB")

    def _clear_unpaired_files_lists(self):
        """Czyści listy niesparowanych plików."""
        if hasattr(self, 'unpaired_archives_list_widget'):
            self.unpaired_archives_list_widget.clear()
        if hasattr(self, 'unpaired_previews_list_widget'):
            self.unpaired_previews_list_widget.clear()

    def _handle_scan_finished(self, found_pairs, unpaired_archives, unpaired_previews):
        """Obsługuje wyniki zakończonego skanowania."""
        logging.info(f"Skanowanie zakończone: {len(found_pairs)} par, "
                    f"{len(unpaired_archives)} archiwów, {len(unpaired_previews)} podglądów")

        # Zapisz wyniki
        self.all_file_pairs = found_pairs
        self.unpaired_archives = unpaired_archives
        self.unpaired_previews = unpaired_previews

        # Wyczyść poprzednie widgety
        if hasattr(self, 'gallery_manager'):
            self.gallery_manager.clear_gallery()

        # Uruchom worker do tworzenia kafelków
        if self.all_file_pairs:
            self._start_data_processing_worker(self.all_file_pairs)
        else:
            self._on_tile_loading_finished()

    def _start_data_processing_worker(self, file_pairs: List[FilePair]):
        """Uruchamia worker do przetwarzania danych."""
        if self.data_processing_thread and self.data_processing_thread.isRunning():
            logging.warning("Worker przetwarzania już działa.")
            return

        self.data_processing_thread = QThread()
        self.data_processing_worker = DataProcessingWorker(
            self.current_working_directory, file_pairs
        )
        self.data_processing_worker.moveToThread(self.data_processing_thread)

        # Podłącz sygnały
        self.data_processing_worker.tile_data_ready.connect(self._create_tile_widget_for_pair)
        self.data_processing_worker.finished.connect(self._on_tile_loading_finished)
        self.data_processing_thread.started.connect(self.data_processing_worker.run)

        self.data_processing_thread.start()

    def _create_tile_widget_for_pair(self, file_pair: FilePair):
        """Tworzy kafelek dla pary plików."""
        if hasattr(self, 'gallery_manager'):
            self.gallery_manager.create_tile_for_pair(
                file_pair, self.current_thumbnail_size, self.selected_tiles
            )

    def _on_tile_loading_finished(self):
        """Wywoływane po zakończeniu tworzenia kafelków."""
        if self.data_processing_thread:
            self.data_processing_thread.quit()
            self.data_processing_thread.wait()
            self.data_processing_thread = None

        # Zastosuj filtry i odśwież widok
        self._apply_filters_and_update_view()
        self._update_unpaired_files_lists()

        # Odblokuj interfejs
        if hasattr(self, 'filter_panel'):
            self.filter_panel.setEnabled(True)
        if hasattr(self, 'size_control_panel'):
            is_gallery_populated = bool(self.gallery_manager.file_pairs_list)
            self.size_control_panel.setVisible(is_gallery_populated)

        # Inicjalizuj drzewo katalogów
        if self.current_working_directory and hasattr(self, 'directory_tree_manager'):
            self.directory_tree_manager.init_directory_tree(self.current_working_directory)

        # Przywróć przycisk i pokaż cache button
        if hasattr(self, 'select_folder_button'):
            self.select_folder_button.setText("Wybierz Folder Roboczy")
            self.select_folder_button.setEnabled(True)
        if hasattr(self, 'clear_cache_button'):
            self.clear_cache_button.setVisible(True)

        # Zapisz metadane
        self._save_metadata()

        logging.info("Widok zaktualizowany - kafelki załadowane")

    def _apply_filters_and_update_view(self):
        """Zbiera kryteria filtrów i aktualizuje galerię."""
        if not hasattr(self, 'filter_panel') or not hasattr(self, 'gallery_manager'):
            return

        criteria = self.filter_panel.get_filter_criteria()
        filtered_pairs = file_operations.apply_filters(self.all_file_pairs, criteria)

        self.gallery_manager.update_displayed_pairs(filtered_pairs)

        # Aktualizuj widoczność panelu rozmiaru
        if hasattr(self, 'size_control_panel'):
            is_gallery_populated = bool(self.gallery_manager.file_pairs_list)
            self.size_control_panel.setVisible(is_gallery_populated)

    def _update_gallery_view(self):
        """Aktualizuje widok galerii."""
        if hasattr(self, 'gallery_manager'):
            self.gallery_manager.update_gallery_view()

    def refresh_all_views(self, new_selection=None):
        """Odświeża wszystkie widoki bez ponownego skanowania."""
        if new_selection:
            self._pending_selection = new_selection

        self._apply_filters_and_update_view()
        self._update_unpaired_files_lists()
        self._save_metadata()

        logging.info("Odświeżenie zakończone - bez ponownego skanowania")

    def _save_metadata(self):
        """Zapisuje metadane do pliku."""
        if hasattr(self, 'all_file_pairs') and self.current_working_directory:
            metadata_manager.save_metadata_to_file(
                self.current_working_directory, self.all_file_pairs
            )

    def _folder_tree_item_clicked(self, index):
        """Obsługuje kliknięcie w drzewo folderów."""
        if hasattr(self, 'directory_tree_manager'):
            self.directory_tree_manager.on_folder_clicked(index)

    def _update_pair_button_state(self):
        """Aktualizuje stan przycisku parowania."""
        if not hasattr(self, 'pair_manually_button'):
            return
            
        selected_archives = []
        selected_previews = []
        
        if hasattr(self, 'unpaired_archives_list_widget'):
            selected_archives = self.unpaired_archives_list_widget.selectedItems()
        if hasattr(self, 'unpaired_previews_list_widget'):
            selected_previews = self.unpaired_previews_list_widget.selectedItems()
            
        self.pair_manually_button.setEnabled(
            len(selected_archives) == 1 and len(selected_previews) == 1
        )

    def _handle_manual_pairing(self):
        """Obsługuje ręczne parowanie plików."""
        # Implementacja ręcznego parowania
        logging.info("Ręczne parowanie plików - funkcjonalność do implementacji")

    def handle_file_drop_on_folder(self, source_file_paths: List[str], target_folder_path: str):
        """Obsługuje drag&drop plików na folder."""
        if hasattr(self, 'file_operations_ui'):
            self.file_operations_ui.handle_file_drop_on_folder(source_file_paths, target_folder_path)
        else:
            logging.error("FileOperationsUI nie jest zainicjalizowany")
