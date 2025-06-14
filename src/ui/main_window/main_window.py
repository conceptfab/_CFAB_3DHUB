"""
Główne okno aplikacji - zrefaktoryzowana wersja.
🚀 ETAP 2: Zoptymalizowane z Event Bus, ViewRefreshManager i OptimizedLogger
"""

import logging
import os

from PyQt6.QtCore import Qt, QThread, QThreadPool, QTimer, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src import app_config
from src.controllers.main_window_controller import MainWindowController
from src.logic import file_operations
from src.models.file_pair import FilePair
from src.services.thread_coordinator import ThreadCoordinator
from src.ui.delegates.workers import (
    BulkMoveWorker,
    DataProcessingWorker,
    UnifiedBaseWorker,
    WorkerFactory,
)
from src.ui.directory_tree.manager import DirectoryTreeManager
from src.ui.file_operations_ui import FileOperationsUI
from src.ui.gallery_manager import GalleryManager
from src.ui.main_window.event_handler import EventHandler
from src.ui.main_window.file_operations_coordinator import FileOperationsCoordinator
from src.ui.main_window.progress_manager import ProgressManager

# 🚀 ETAP 1: Refaktoryzacja - nowe komponenty MainWindow
from src.ui.main_window.ui_manager import UIManager
from src.ui.main_window.worker_manager import WorkerManager
from src.ui.main_window_components.event_bus import get_event_bus
from src.ui.main_window_components.view_refresh_manager import ViewRefreshManager
from src.ui.widgets.gallery_tab import GalleryTab
from src.ui.widgets.preview_dialog import PreviewDialog
from src.ui.widgets.unpaired_files_tab import UnpairedFilesTab

# 🚀 ETAP 2: Nowe zoptymalizowane komponenty
from src.utils.logging_config import get_main_window_logger
from src.utils.path_utils import normalize_path


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji CFAB_3DHUB - zrefaktoryzowana wersja.
    """

    def __init__(self):
        """
        Inicjalizuje główne okno aplikacji.
        """
        super().__init__()
        self._init_data()
        self._init_window()
        self._init_ui()
        self._init_managers()

        # WYŁĄCZONO automatyczne ładowanie - użytkownik musi wybrać folder z drzewa
        # self._auto_load_last_folder()  # NIEPRAWIDŁOWE ZACHOWANIE - skanuje cały główny folder

        # Pokaż preferencje wczytane
        self._show_preferences_loaded_confirmation()

        # Zainicjalizuj drzewo katalogów z domyślnym folderem ale BEZ skanowania i rozwijania
        default_folder = self.app_config.get("default_working_directory", "")
        if (
            default_folder
            and os.path.exists(default_folder)
            and os.path.isdir(default_folder)
        ):
            self.logger.debug(f"Inicjalizacja drzewa katalogów: {default_folder}")
            self.directory_tree_manager.init_directory_tree_without_expansion(
                default_folder
            )

        self.logger.info("Główne okno aplikacji zostało zainicjalizowane")

    def _init_data(self):
        """Inicjalizuje dane aplikacji."""
        # 🚀 ETAP 2: Zoptymalizowany logger bez emoji
        self.logger = get_main_window_logger()

        # KRYTYCZNE: AppConfig musi być pierwsze - inne komponenty go używają!
        self.app_config = app_config.AppConfig()

        # 🚀 ETAP 2: Event Bus - eliminuje tight coupling
        self.event_bus = get_event_bus()

        # 🚀 ETAP 2: View Refresh Manager - inteligentne odświeżanie
        self.view_refresh_manager = ViewRefreshManager(self)

        # ETAP 2 FINAL: MVC Controller - centralna logika biznesowa
        self.controller = MainWindowController(self)

        # 🚀 ETAP 1: UI Manager - zarządzanie interfejsem użytkownika
        self.ui_manager = UIManager(self)

        # 🚀 ETAP 1: Progress Manager - zarządzanie postępem
        self.progress_manager = ProgressManager(self)

        # 🚀 ETAP 1: Worker Manager - zarządzanie wątkami
        self.worker_manager = WorkerManager(self)

        # 🚀 ETAP 1: Event Handler - obsługa zdarzeń
        self.event_handler = EventHandler(self)

        # 🚀 ETAP 1: File Operations Coordinator - operacje na plikach
        self.file_operations_coordinator = FileOperationsCoordinator(self)

        # 🚀 REFAKTORYZACJA: Nowe wyspecjalizowane managery
        from src.ui.main_window.bulk_operations_manager import BulkOperationsManager
        from src.ui.main_window.data_manager import DataManager
        from src.ui.main_window.metadata_manager import MetadataManager
        from src.ui.main_window.scan_manager import ScanManager
        from src.ui.main_window.selection_manager import SelectionManager
        from src.ui.main_window.tile_manager import TileManager

        self.data_manager = DataManager(self)
        self.tile_manager = TileManager(self)
        self.scan_manager = ScanManager(self)
        self.metadata_manager = MetadataManager(self)
        self.selection_manager = SelectionManager(self)
        self.bulk_operations_manager = BulkOperationsManager(self)

    def _init_window(self):
        """Inicjalizuje okno aplikacji."""
        # Timer do opóźnienia odświeżania galerii
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._update_gallery_view)

        # Konfiguracja rozmiaru miniatur
        # (AppConfig już zainicjalizowane w _init_data)
        self.min_thumbnail_size = self.app_config.min_thumbnail_size
        self.max_thumbnail_size = self.app_config.max_thumbnail_size

        # Wymuś początkową pozycję suwaka na 50% (środek)
        self.initial_slider_position = 50

        # Oblicz current_thumbnail_size na podstawie wymuszonej pozycji suwaka
        size_range = self.max_thumbnail_size - self.min_thumbnail_size
        if (
            size_range <= 0
        ):  # Zabezpieczenie przed ujemnym zakresem lub dzieleniem przez zero
            self.current_thumbnail_size = self.min_thumbnail_size
        else:
            self.current_thumbnail_size = self.min_thumbnail_size + int(
                (size_range * self.initial_slider_position) / 100
            )

        logging.info(
            f"Initial slider position: {self.initial_slider_position}%, "
            f"thumbnail size: {self.current_thumbnail_size}px"
        )

        # Konfiguracja okna
        self.setWindowTitle("CFAB_3DHUB")
        self.setMinimumSize(
            self.app_config.window_min_width, self.app_config.window_min_height
        )

        # Inicjalizacja paska statusu
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        # Inicjalizacja globalnego paska postępu
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(15)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)  # Początkowy stan - ukryty

        # Etykieta postępu
        self.progress_label = QLabel("Gotowy")
        self.progress_label.setStyleSheet("color: gray; font-style: italic;")

        # Dodanie etykiety i paska postępu do paska statusu
        self.status_bar.addWidget(self.progress_label, 1)
        self.status_bar.addPermanentWidget(self.progress_bar, 2)

        # Inicjalizacja globalnego thread poola dla workerów QRunnable
        self.thread_pool = QThreadPool.globalInstance()
        logging.debug(f"Maksymalna liczba wątków: {self.thread_pool.maxThreadCount()}")

        # Centralny widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Główny layout - NAPRAWKA: Minimalne marginesy dla profesjonalnego wyglądu
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(2, 2, 2, 2)
        self.main_layout.setSpacing(3)

    def _init_ui(self):
        """
        Inicjalizuje elementy interfejsu użytkownika.
        """
        # 🚀 ETAP 1: Delegacja do UI Manager
        self.ui_manager.init_ui()

        # TabWidget jako główny kontener widoków
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # Inicjalizacja managerów zakładek
        self.gallery_tab_manager = GalleryTab(self)
        self.unpaired_files_tab_manager = UnpairedFilesTab(self)

        # 🚨 ETAP 2 - POPRAWKA 5: Nowa zakładka z eksploratorem plików
        from src.ui.widgets.file_explorer_tab import FileExplorerTab

        self.file_explorer_tab = FileExplorerTab(self)

        # Zakładka galerii
        gallery_widget = self.gallery_tab_manager.create_gallery_tab()
        self.tab_widget.addTab(gallery_widget, "Galeria")

        # Zakładka niesparowanych plików
        unpaired_widget = self.unpaired_files_tab_manager.create_unpaired_files_tab()
        self.tab_widget.addTab(unpaired_widget, "Parowanie Plików")

        # 🚨 NOWA ZAKŁADKA: Eksplorator plików
        self.tab_widget.addTab(self.file_explorer_tab, "Eksplorator plików")

        # 🚨 ETAP 2: Połączenie sygnałów eksploratora
        self.file_explorer_tab.folder_changed.connect(self.on_explorer_folder_changed)
        self.file_explorer_tab.file_selected.connect(self.on_explorer_file_selected)

        # Pobierz referencje do widgetów dla kompatybilności
        gallery_widgets = self.gallery_tab_manager.get_widgets_for_main_window()
        unpaired_widgets = self.unpaired_files_tab_manager.get_widgets_for_main_window()

        # Przypisz widgety galerii
        self.folder_tree = gallery_widgets["folder_tree"]
        self.folder_tree_container = gallery_widgets["folder_tree_container"]
        self.file_system_model = gallery_widgets["file_system_model"]
        self.tiles_container = gallery_widgets["tiles_container"]
        self.tiles_layout = gallery_widgets["tiles_layout"]
        self.scroll_area = gallery_widgets["scroll_area"]
        self.splitter = gallery_widgets["splitter"]

        # Przypisz widgety unpaired files
        self.unpaired_files_tab = unpaired_widgets["unpaired_files_tab"]
        self.unpaired_archives_list_widget = unpaired_widgets[
            "unpaired_archives_list_widget"
        ]
        self.unpaired_previews_list_widget = unpaired_widgets[
            "unpaired_previews_list_widget"
        ]
        self.unpaired_previews_layout = unpaired_widgets["unpaired_previews_layout"]
        self.pair_manually_button = unpaired_widgets["pair_manually_button"]

    # 🚀 ETAP 1: Metody UI przeniesione do UIManager - delegacje
    def show_preferences(self):
        """Delegacja do UIManager."""
        return self.ui_manager.show_preferences()

    def remove_all_metadata_folders(self):
        """Delegacja do UIManager."""
        return self.ui_manager.remove_all_metadata_folders()

    def start_metadata_cleanup_worker(self):
        """Delegacja do UIManager."""
        return self.ui_manager.start_metadata_cleanup_worker()

    def show_about(self):
        """Delegacja do UIManager."""
        return self.ui_manager.show_about()

    # 🚀 ETAP 1: Metody UI przeniesione do UIManager
    # _create_top_panel(), _create_size_control_panel(), _create_bulk_operations_panel()
    # są teraz w UIManager

    def _init_managers(self):
        """
        Inicjalizuje managerów UI.
        """
        # AppConfig już zainicjalizowane w _init_data()

        # Problem #3: Centralne zarządzanie wątkami
        self.thread_coordinator = ThreadCoordinator()

        # Inicjalizacja DirectoryTreeManager
        self.directory_tree_manager = DirectoryTreeManager(self.folder_tree, self)

        # ==================== DODANIE KONTROLEK EXPAND/COLLAPSE ====================
        # Dodaj kontrolki expand/collapse nad drzewem folderów
        if hasattr(self, "folder_tree_container"):
            expand_controls = (
                self.directory_tree_manager.setup_expand_collapse_controls()
            )
            # Dodaj kontrolki na górze kontenera (przed drzewem)
            layout = self.folder_tree_container.layout()
            if layout:
                layout.insertWidget(0, expand_controls)
                self.logger.debug("Dodano kontrolki expand/collapse do UI")

        # Inicjalizacja GalleryManager
        self.gallery_manager = GalleryManager(self.tiles_container, self.tiles_layout)

        # File Operations UI
        self.file_operations_ui = FileOperationsUI(self)

        # Podłącz sygnały
        self.folder_tree.clicked.connect(
            self.gallery_tab_manager.folder_tree_item_clicked
        )

    def _auto_load_last_folder(self):
        """
        Automatycznie ładuje ostatni folder roboczy jeśli włączone w preferencjach.
        """
        # POTWIERDZENIE WCZYTANIA PREFERENCJI!
        self._show_preferences_loaded_confirmation()

        if not self.app_config.get("auto_load_last_folder", False):
            logging.debug("Auto-load of last folder DISABLED in preferences")
            return

        last_folder = self.app_config.get("default_working_directory", "")
        if not last_folder:
            logging.debug("Brak zapisanego folderu roboczego")
            return

        import os

        if not os.path.exists(last_folder) or not os.path.isdir(last_folder):
            self.logger.warning(f"Zapisany folder roboczy nie istnieje: {last_folder}")
            return

        try:
            logging.debug(f"Auto-loading last folder: {last_folder}")
            # Ustaw flagę że to jest auto-loading (NIE nadpisuj domyślnego!)
            self._is_auto_loading = True
            self._select_working_directory(last_folder)
            # Usuń flagę po zakończeniu
            delattr(self, "_is_auto_loading")
        except Exception as e:
            logging.error(f"Błąd podczas auto-loading folderu {last_folder}: {e}")
            # Usuń flagę nawet przy błędzie
            if hasattr(self, "_is_auto_loading"):
                delattr(self, "_is_auto_loading")

    def _show_preferences_loaded_confirmation(self):
        """
        Pokazuje potwierdzenie że preferencje zostały wczytane.
        """
        # Preferencje wczytane - tylko krótki komunikat
        logging.debug("Preferencje wczytane")

        # Pokaż w status barze
        self.progress_label.setText("Preferencje wczytane")
        self.progress_label.setStyleSheet("color: green; font-weight: bold;")

        # Po czasie z konfiguracji przywróć normalny status
        delay = self.app_config.preferences_status_display_ms
        QTimer.singleShot(delay, lambda: self.progress_label.setText("Gotowy"))
        QTimer.singleShot(
            delay,
            lambda: self.progress_label.setStyleSheet(
                "color: gray; font-style: italic;"
            ),
        )

    def closeEvent(self, event):
        """
        Obsługuje zamykanie aplikacji - kończy wszystkie wątki.
        """
        # 🚀 ETAP 1: Delegacja do EventHandler
        self.event_handler.handle_close_event(event)

    def _select_working_directory(self, directory_path=None):
        """Delegacja do ScanManager."""
        return self.scan_manager.select_working_directory(directory_path)

    def _validate_directory_path(self, path: str) -> bool:
        """Delegacja do ScanManager."""
        return self.scan_manager.validate_directory_path(path)

    def _stop_current_scanning(self):
        """Delegacja do ScanManager."""
        return self.scan_manager.stop_current_scanning()

    def _start_folder_scanning(self, directory_path: str):
        """Delegacja do ScanManager."""
        return self.scan_manager.start_folder_scanning(directory_path)

    def _on_scan_thread_finished(self):
        """Delegacja do ScanManager."""
        return self.scan_manager.on_scan_thread_finished()

    def _force_refresh(self):
        """Delegacja do DataManager."""
        return self.data_manager.force_refresh()

    def _clear_all_data_and_views(self):
        """Delegacja do DataManager."""
        return self.data_manager.clear_all_data_and_views()

    def _clear_unpaired_files_lists(self):
        """Delegacja do DataManager."""
        return self.data_manager.clear_unpaired_files_lists()

    def _update_unpaired_files_direct(self):
        """Delegacja do DataManager."""
        return self.data_manager.update_unpaired_files_direct()

    def _handle_scan_finished(self, found_pairs, unpaired_archives, unpaired_previews):
        """Delegacja do ScanManager."""
        return self.scan_manager.handle_scan_finished(
            found_pairs, unpaired_archives, unpaired_previews
        )

    def _create_tile_widget_for_pair(self, file_pair: FilePair):
        """Delegacja do TileManager."""
        return self.tile_manager.create_tile_widget_for_pair(file_pair)

    def _on_thumbnail_progress(self):
        """Delegacja do ProgressManager."""
        return self.progress_manager.on_thumbnail_progress()

    def _create_tile_widgets_batch(self, file_pairs_batch: list):
        """Delegacja do TileManager."""
        return self.tile_manager.create_tile_widgets_batch(file_pairs_batch)

    def _on_tile_loading_finished(self):
        """Delegacja do TileManager."""
        return self.tile_manager.on_tile_loading_finished()

    def _handle_scan_error(self, error_message: str):
        """
        Obsługuje błędy występujące podczas skanowania folderu.
        """
        # 🚀 ETAP 1: Delegacja do EventHandler
        self.event_handler.handle_scan_error(error_message)

        # Przywróć przycisk
        self.select_folder_button.setText("Wybierz Folder Roboczy")
        self.select_folder_button.setEnabled(True)
        self.filter_panel.setEnabled(False)  # Zablokuj przy błędzie

    def _apply_filters_and_update_view(self):
        """Delegacja do DataManager."""
        return self.data_manager.apply_filters_and_update_view()

    def _update_gallery_view(self):
        """Delegacja do DataManager."""
        return self.data_manager.update_gallery_view()

    def refresh_all_views(self, new_selection=None):
        """Delegacja do DataManager."""
        return self.data_manager.refresh_all_views(new_selection)

    def force_full_refresh(self):
        """Delegacja do DataManager."""
        return self.data_manager.force_full_refresh()

    def _update_thumbnail_size(self):
        """Delegacja do TileManager."""
        return self.tile_manager.update_thumbnail_size()

    def resizeEvent(self, event):
        """
        Obsługuje zmianę rozmiaru okna.
        """
        # 🚀 ETAP 1: Delegacja do EventHandler
        self.event_handler.handle_resize_event(event)

    def _save_metadata(self):
        """Delegacja do MetadataManager."""
        return self.metadata_manager.save_metadata()

    def _schedule_metadata_save(self):
        """Delegacja do MetadataManager."""
        return self.metadata_manager.schedule_metadata_save()

    def _force_immediate_metadata_save(self):
        """Delegacja do MetadataManager."""
        return self.metadata_manager.force_immediate_metadata_save()

    def _on_metadata_saved(self, success):
        """Delegacja do MetadataManager."""
        return self.metadata_manager.on_metadata_saved(success)

    def open_archive(self, file_pair: FilePair):
        """
        Otwiera plik archiwum w domyślnym programie systemu.
        """
        if file_pair and file_pair.archive_path:
            logging.info(f"Żądanie otwarcia archiwum dla: {file_pair.get_base_name()}")
            file_operations.open_archive_externally(file_pair.archive_path)
        else:
            logging.warning(
                "Próba otwarcia archiwum dla nieprawidłowego FilePair "
                "lub braku ścieżki."
            )

    def _show_preview_dialog(self, file_pair: FilePair):
        """
        Wyświetla okno dialogowe z podglądem obrazu.
        """
        preview_path = file_pair.get_preview_path()
        if not preview_path or not os.path.exists(preview_path):
            QMessageBox.warning(
                self,
                "Brak Podglądu",
                "Plik podglądu dla tego elementu nie istnieje.",
            )
            return

        try:
            pixmap = QPixmap(preview_path)
            if pixmap.isNull():
                raise ValueError("Nie udało się załadować obrazu do QPixmap.")

            dialog = PreviewDialog(pixmap, self)
            dialog.exec()

        except Exception as e:
            error_message = f"Wystąpił błąd podczas ładowania podglądu: {e}"
            logging.error(error_message)
            QMessageBox.critical(self, "Błąd Podglądu", error_message)

    def _handle_tile_selection_changed(self, file_pair: FilePair, is_selected: bool):
        """Delegacja do SelectionManager."""
        return self.selection_manager.handle_tile_selection_changed(
            file_pair, is_selected
        )

    def _update_bulk_operations_visibility(self):
        """Delegacja do SelectionManager."""
        return self.selection_manager.update_bulk_operations_visibility()

    def _clear_all_selections(self):
        """Delegacja do SelectionManager."""
        return self.selection_manager.clear_all_selections()

    def _select_all_tiles(self):
        """Delegacja do SelectionManager."""
        return self.selection_manager.select_all_tiles()

    def _perform_bulk_delete(self):
        """Delegacja do BulkOperationsManager."""
        return self.bulk_operations_manager.perform_bulk_delete()

    def _on_bulk_delete_finished(self, deleted_pairs):
        """
        Slot wywoływany po zakończeniu masowego usuwania plików.

        Args:
            deleted_pairs: Lista pomyślnie usuniętych par plików
        """
        if not deleted_pairs:
            self._show_progress(100, "Usuwanie przerwane lub nieudane")
            return

        # Zapamiętaj oryginalną liczbę zaznaczonych par PRZED ich usunięciem
        original_selected_count = len(self.controller.selected_tiles)

        # Usuń pary z głównej listy i selekcji
        for file_pair in deleted_pairs:
            if file_pair in self.controller.current_file_pairs:
                self.controller.current_file_pairs.remove(file_pair)
            self.controller.selected_tiles.discard(file_pair)

        # Odśwież widok
        self._apply_filters_and_update_view()

        # Zaplanuj zapis metadanych
        self._schedule_metadata_save()

        # Wyświetl podsumowanie
        self._show_progress(100, f"Usunięto {len(deleted_pairs)} par plików")
        QMessageBox.information(
            self,
            "Usuwanie zakończone",
            f"Usunięto {len(deleted_pairs)} z {original_selected_count} zaznaczonych par plików.",
        )

    def _perform_bulk_move(self):
        """Wykonuje masową operację przenoszenia zaznaczonych kafelków przy użyciu wątku roboczego."""
        if not self.controller.selected_tiles:
            return

        # Pobierz katalog docelowy
        destination = QFileDialog.getExistingDirectory(
            self, "Wybierz folder docelowy", self.controller.current_directory or ""
        )

        if not destination:
            return

        count = len(self.controller.selected_tiles)

        # Utwórz workera do masowego przenoszenia
        worker = BulkMoveWorker(list(self.controller.selected_tiles), destination)

        # Podłącz sygnały
        self.worker_manager.setup_worker_connections(worker)
        worker.signals.finished.connect(self._on_bulk_move_finished)

        # Uruchom workera
        self._show_progress(0, f"Przenoszenie {count} par plików...")
        self.thread_pool.start(worker)

    def _on_bulk_move_finished(self, result):
        """
        Slot wywoływany po zakończeniu operacji przenoszenia.

        Args:
            result: Wynik operacji - może być listą par plików (stary format) lub słownikiem z szczegółami (nowy format)
        """
        # Obsługa nowego formatu wyniku
        if isinstance(result, dict):
            moved_pairs = result.get("moved_pairs", [])
            detailed_errors = result.get("detailed_errors", [])
            skipped_files = result.get("skipped_files", [])
            summary = result.get("summary", {})
        else:
            # Fallback dla starych workerów
            moved_pairs = result if isinstance(result, list) else []
            detailed_errors = []
            skipped_files = []
            summary = {}

        if not moved_pairs and not detailed_errors and not skipped_files:
            self._show_progress(100, "Przenoszenie przerwane lub nieudane")
            return

        # Zapamiętaj oryginalną liczbę zaznaczonych par PRZED ich usunięciem
        original_selected_count = len(self.controller.selected_tiles)

        # Usuń przeniesione pary z struktur danych
        for file_pair in moved_pairs:
            if file_pair in self.controller.current_file_pairs:
                self.controller.current_file_pairs.remove(file_pair)
            self.controller.selected_tiles.discard(file_pair)

        # 🔧 NAPRAWKA: Odśwież folder źródłowy po operacji drag&drop
        # Po przeniesieniu plików musimy ponownie przeskanować folder źródłowy,
        # żeby usunąć z widoku pliki które już nie istnieją na dysku
        if self.controller.current_directory:
            logging.info(
                f"Odświeżanie folderu źródłowego po drag&drop: {self.controller.current_directory}"
            )
            self._refresh_source_folder_after_move()
            # NAPRAWKA: NIE wywołuj _apply_filters_and_update_view() tutaj!
            # change_directory() w _refresh_source_folder_after_move() już odświeża widok
        else:
            # Fallback - tylko jeśli nie ma current_directory
            self._apply_filters_and_update_view()

        self._save_metadata()

        destination = (
            os.path.dirname(moved_pairs[0].archive_path) if moved_pairs else "nieznany"
        )
        self._show_progress(100, f"Przeniesiono {len(moved_pairs)} par plików")

        # Pokaż szczegółowy raport błędów jeśli wystąpiły
        if isinstance(result, dict) and (detailed_errors or skipped_files):
            self._show_detailed_move_report(
                moved_pairs, detailed_errors, skipped_files, summary
            )
        else:
            QMessageBox.information(
                self,
                "Przenoszenie zakończone",
                f"Przeniesiono {len(moved_pairs)} z {original_selected_count} zaznaczonych par plików do:\n{destination}",
            )

    def _refresh_source_folder_after_move(self):
        """
        Odświeża folder źródłowy po operacji przenoszenia plików przez drag&drop.

        Ta metoda ponownie skanuje current_working_directory, aby usunąć z widoku
        pliki które zostały przeniesione i już nie istnieją na dysku.
        """
        if not self.controller.current_directory or not os.path.exists(
            self.controller.current_directory
        ):
            logging.warning(
                f"Nie można odświeżyć - folder źródłowy nie istnieje: {self.controller.current_directory}"
            )
            return

        try:
            # Ponownie przeskanuj folder źródłowy
            logging.info(
                f"Rozpoczynanie ponownego skanowania folderu: {self.controller.current_directory}"
            )

            # NAPRAWKA DRAG&DROP: NIE wyczyścićmy cache miniaturek!
            # Scanner cache może zostać wyczyszczony ale thumbnail cache NIE!
            # Miniaturki nie zmieniają się przy przeniesieniu plików do innego folderu
            from src.logic.scanner import clear_cache

            clear_cache()  # Tylko scanner cache dla aktualnych wyników

            # Uruchom ponowne skanowanie BEZ RESETOWANIA DRZEWA
            # Używamy change_directory() zamiast controller.handle_folder_selection()
            # aby zachować drzewo katalogów
            if hasattr(self, "controller") and self.controller:
                try:
                    # Użyj metody która zachowuje drzewo katalogów
                    self.change_directory(self.controller.current_directory)
                    logging.info(
                        "Pomyślnie odświeżono folder źródłowy po operacji bez resetowania drzewa"
                    )
                except Exception as e:
                    logging.warning(f"Błąd podczas odświeżania folderu bez resetu: {e}")
                    # Fallback - ale tylko odśwież widok, nie resetuj drzewa
                    self.refresh_all_views()
            else:
                logging.warning("Kontroler nie jest dostępny - używam fallback")
                # Fallback - tylko odśwież widok
                self.refresh_all_views()

        except Exception as e:
            logging.error(f"Błąd podczas odświeżania folderu źródłowego: {e}")

    def _handle_stars_changed(self, file_pair: FilePair, new_star_count: int):
        """Delegacja do MetadataManager."""
        return self.metadata_manager.handle_stars_changed(file_pair, new_star_count)

    def _handle_color_tag_changed(self, file_pair: FilePair, new_color_tag: str):
        """Delegacja do MetadataManager."""
        return self.metadata_manager.handle_color_tag_changed(file_pair, new_color_tag)

    def _show_file_context_menu(self, file_pair: FilePair, widget: QWidget, position):
        """
        Wyświetla menu kontekstowe dla kafelka.
        """
        self.file_operations_ui.show_file_context_menu(file_pair, widget, position)

    def handle_file_drop_on_folder(
        self, source_file_paths: list[str], target_folder_path: str
    ):
        """
        Obsługuje upuszczenie plików na folder w drzewie katalogów.
        Konwertuje ścieżki na QUrl i przekierowuje do FileOperationsUI.

        Args:
            source_file_paths: Lista ścieżek do plików do przeniesienia
            target_folder_path: Ścieżka do katalogu docelowego
        """

        # Konwertuj ścieżki plików na QUrl
        urls = [QUrl.fromLocalFile(path) for path in source_file_paths]

        # Przekieruj do FileOperationsUI
        if self.file_operations_ui:
            self.file_operations_ui.handle_drop_on_folder(urls, target_folder_path)
        else:
            logging.error("FileOperationsUI nie jest zainicjalizowany")

    # ---- Metody do obsługi operacji asynchronicznych i postępu ----

    def _show_progress(self, percent: int, message: str):
        """Delegacja do ProgressManager."""
        return self.progress_manager.show_progress(percent, message)

    def _hide_progress(self):
        """Delegacja do ProgressManager."""
        return self.progress_manager.hide_progress()

    def _setup_worker_connections(self, worker: UnifiedBaseWorker):
        """
        Konfiguruje połączenia sygnałów dla workera.

        Args:
            worker: Instancja UnifiedBaseWorker do skonfigurowania
        """
        worker.signals.progress.connect(self._show_progress)
        worker.signals.error.connect(self._handle_worker_error)

    def _handle_worker_error(self, error_message: str):
        """Delegacja do ProgressManager."""
        return self.progress_manager.handle_worker_error(error_message)

    def _show_detailed_move_report(
        self, moved_pairs, detailed_errors, skipped_files, summary
    ):
        """
        Wyświetla szczegółowy raport z operacji przenoszenia plików.
        """
        from PyQt6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Raport przenoszenia plików")
        dialog.setMinimumSize(800, 600)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        # Podsumowanie
        summary_text = f"""
<h3>Podsumowanie operacji przenoszenia</h3>
<p><b>Żądano przeniesienia:</b> {summary.get('total_requested', 0)} par plików</p>
<p><b>Pomyślnie przeniesiono:</b> {summary.get('successfully_moved', 0)} par plików</p>
<p><b>Błędy:</b> {summary.get('errors', 0)} plików</p>
<p><b>Pominięto:</b> {summary.get('skipped', 0)} plików</p>
        """

        summary_label = QLabel(summary_text)
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        # Zakładki z szczegółami
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # Zakładka z błędami
        if detailed_errors:
            errors_widget = QWidget()
            errors_layout = QVBoxLayout(errors_widget)

            errors_text = QTextEdit()
            errors_text.setReadOnly(True)

            error_content = "<h4>Szczegółowe błędy:</h4>\n"

            # Grupuj błędy według typu
            error_groups = {}
            for error in detailed_errors:
                error_type = error.get("error_type", "NIEZNANY")
                if error_type not in error_groups:
                    error_groups[error_type] = []
                error_groups[error_type].append(error)

            for error_type, errors in error_groups.items():
                error_content += (
                    f"<h5>{error_type} ({len(errors)} plików):</h5>\n<ul>\n"
                )
                for error in errors:
                    file_pair = error.get("file_pair", "Nieznany")
                    file_type = error.get("file_type", "nieznany")
                    file_path = error.get("file_path", "nieznana ścieżka")
                    error_msg = error.get("error", "nieznany błąd")

                    error_content += f"<li><b>Para:</b> {file_pair} ({file_type})<br/>"
                    error_content += f"<b>Plik:</b> {file_path}<br/>"
                    error_content += f"<b>Błąd:</b> {error_msg}</li>\n"
                error_content += "</ul>\n"

            errors_text.setHtml(error_content)
            errors_layout.addWidget(errors_text)
            tab_widget.addTab(errors_widget, f"Błędy ({len(detailed_errors)})")

        # Zakładka z pominięciami
        if skipped_files:
            skipped_widget = QWidget()
            skipped_layout = QVBoxLayout(skipped_widget)

            skipped_text = QTextEdit()
            skipped_text.setReadOnly(True)

            skipped_content = "<h4>Pominięte pliki:</h4>\n<ul>\n"
            for skipped in skipped_files:
                file_pair = skipped.get("file_pair", "Nieznany")
                file_type = skipped.get("file_type", "nieznany")
                file_path = skipped.get("file_path", "nieznana ścieżka")
                target_path = skipped.get("target_path", "nieznana ścieżka docelowa")
                reason = skipped.get("reason", "nieznany powód")

                skipped_content += f"<li><b>Para:</b> {file_pair} ({file_type})<br/>"
                skipped_content += f"<b>Plik źródłowy:</b> {file_path}<br/>"
                skipped_content += f"<b>Plik docelowy:</b> {target_path}<br/>"
                skipped_content += f"<b>Powód:</b> {reason}</li>\n"
            skipped_content += "</ul>\n"

            skipped_text.setHtml(skipped_content)
            skipped_layout.addWidget(skipped_text)
            tab_widget.addTab(skipped_widget, f"Pominięte ({len(skipped_files)})")

        # Zakładka z sukcesami
        if moved_pairs:
            success_widget = QWidget()
            success_layout = QVBoxLayout(success_widget)

            success_text = QTextEdit()
            success_text.setReadOnly(True)

            success_content = "<h4>Pomyślnie przeniesione pary:</h4>\n<ul>\n"
            for pair in moved_pairs:
                pair_name = (
                    pair.get_base_name()
                    if hasattr(pair, "get_base_name")
                    else "Nieznana para"
                )
                archive_path = getattr(pair, "archive_path", "brak")
                preview_path = getattr(pair, "preview_path", "brak")

                success_content += f"<li><b>Para:</b> {pair_name}<br/>"
                success_content += f"<b>Archiwum:</b> {archive_path}<br/>"
                success_content += f"<b>Podgląd:</b> {preview_path}</li>\n"
            success_content += "</ul>\n"

            success_text.setHtml(success_content)
            success_layout.addWidget(success_text)
            tab_widget.addTab(success_widget, f"Sukces ({len(moved_pairs)})")

        # Przyciski
        button_layout = QHBoxLayout()

        close_button = QPushButton("Zamknij")
        close_button.clicked.connect(dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        dialog.exec()

    # ETAP 2 FINAL: Metody UI dla MainWindowController (MVC)
    def show_error_message(self, title: str, message: str):
        """Pokazuje błąd użytkownikowi - używane przez kontroler."""
        QMessageBox.critical(self, title, message)

    def show_warning_message(self, title: str, message: str):
        """Pokazuje ostrzeżenie użytkownikowi - używane przez kontroler."""
        QMessageBox.warning(self, title, message)

    def show_info_message(self, title: str, message: str):
        """Pokazuje informację użytkownikowi - używane przez kontroler."""
        QMessageBox.information(self, title, message)

    def update_scan_results(self, scan_result):
        """Aktualizuje UI wynikami skanowania z kontrolera."""
        # UWAGA: Controller już zaktualizował swój stan w handle_folder_selection()
        # NIE wywołujemy controller.handle_scan_finished() aby nie nadpisać danych!

        # Wyczyść poprzednie widgety
        self.gallery_manager.clear_gallery()

        # Utwórz nowe kafelki
        if scan_result.file_pairs:
            self.worker_manager.start_data_processing_worker(scan_result.file_pairs)
        else:
            self._on_tile_loading_finished()

        # UWAGA: update_unpaired_files_lists() jest już wywoływana w _on_tile_loading_finished()
        # Nie wywołujemy tutaj aby uniknąć błędów z niezainicjalizowanymi widgetami

    def confirm_bulk_delete(self, count: int) -> bool:
        """Delegacja do BulkOperationsManager."""
        return self.bulk_operations_manager.confirm_bulk_delete(count)

    def update_after_bulk_operation(self, processed_pairs, operation_name: str):
        """Aktualizuje UI po operacji bulk."""
        # Usuń z galerii
        for pair in processed_pairs:
            self.gallery_manager.remove_tile_for_pair(pair)

        # Aktualizuj widok
        self.refresh_all_views()

        # Status bar
        self.status_bar.showMessage(
            f"Operacja {operation_name}: {len(processed_pairs)} plików"
        )

    def update_bulk_operations_visibility(self, selected_count: int):
        """Delegacja do SelectionManager."""
        return self.selection_manager.update_bulk_operations_visibility_with_count(
            selected_count
        )

    def add_new_pair(self, new_pair):
        """Dodaje nową parę do UI."""
        self.controller.current_file_pairs.append(new_pair)
        tile = self._create_tile_widget_for_pair(new_pair)
        if tile:
            self.gallery_manager.add_tile_widget(tile)

    def update_unpaired_lists(self, archives, previews):
        """Aktualizuje listy niesparowanych plików."""
        self.controller.unpaired_archives = archives
        self.controller.unpaired_previews = previews
        # Delegacja do managera zamiast wywołania nieistniejącej metody
        if hasattr(self, "unpaired_files_tab_manager"):
            self.unpaired_files_tab_manager.update_unpaired_files_lists()

    def request_metadata_save(self):
        """Delegacja do MetadataManager."""
        return self.metadata_manager.request_metadata_save()

    def change_directory(self, folder_path: str):
        """
        Zmienia katalog roboczy na wybrany folder i skanuje tylko ten folder.
        Wywoływane po kliknięciu na folder w drzewie.
        ZACHOWUJE drzewo katalogów bez resetowania.
        """
        try:
            normalized_path = normalize_path(folder_path)
            base_folder_name = os.path.basename(normalized_path)
            self.setWindowTitle(f"CFAB_3DHUB - {base_folder_name}")

            logging.info(f"Zmiana katalogu na: {normalized_path}")

            # Wyczyść tylko galerię i dane, ale ZACHOWAJ drzewo katalogów
            self.gallery_manager.clear_gallery()
            self._clear_unpaired_files_lists()

            # Skanuj tylko wybrany folder przez kontroler BEZ resetowania drzewa
            # Używamy bezpośrednio serwisu skanowania zamiast handle_folder_selection
            # aby uniknąć wywołania update_scan_results -> _on_tile_loading_finished -> init_directory_tree
            try:
                # NAPRAWKA: Skanuj TYLKO bezpośrednie pliki w folderze (max_depth=0)
                # zamiast całego drzewa folderów rekurencyjnie
                scan_result = self.controller.scan_service.scan_directory(
                    normalized_path, max_depth=0
                )

                if scan_result.error_message:
                    self.show_error_message(
                        "Błąd skanowania", scan_result.error_message
                    )
                    return

                # Zaktualizuj stan kontrolera ręcznie
                self.controller.current_directory = normalized_path
                self.controller.current_file_pairs = scan_result.file_pairs
                self.controller.unpaired_archives = scan_result.unpaired_archives
                self.controller.unpaired_previews = scan_result.unpaired_previews

                # 🚨 NAPRAWKA: Ustaw ścieżkę w eksploratorze plików!
                if hasattr(self, "file_explorer_tab"):
                    self.file_explorer_tab.set_root_path(normalized_path)
                    logging.info(f"EKSPLORATOR: Ustawiono ścieżkę na {normalized_path}")

                # Utwórz kafelki BEZ resetowania drzewa
                if scan_result.file_pairs:
                    self.worker_manager.start_data_processing_worker_without_tree_reset(
                        scan_result.file_pairs
                    )
                else:
                    # Wywołaj końcowe akcje BEZ init_directory_tree
                    self._finish_folder_change_without_tree_reset()

                logging.info(
                    f"Folder change SUCCESS: {normalized_path}, {len(scan_result.file_pairs)} par"
                )

            except Exception as scan_error:
                error_msg = f"Błąd skanowania folderu: {scan_error}"
                logging.error(error_msg)
                self.show_error_message("Błąd", error_msg)

        except Exception as e:
            error_msg = f"Błąd zmiany katalogu: {e}"
            logging.error(error_msg)
            self.show_error_message("Błąd", error_msg)

    def _finish_folder_change_without_tree_reset(self):
        """
        Kończy zmianę folderu bez resetowania drzewa katalogów.
        Alternatywa dla _on_tile_loading_finished gdy chcemy zachować drzewo.
        """
        logging.debug("Zakończono tworzenie kafelków bez resetowania drzewa")

        # Zastosuj filtry i odśwież widok
        self._apply_filters_and_update_view()
        # Delegacja do managera zamiast wywołania nieistniejącej metody
        if hasattr(self, "unpaired_files_tab_manager"):
            self.unpaired_files_tab_manager.update_unpaired_files_lists()

        # Pokaż interfejs
        self.filter_panel.setEnabled(True)  # Odblokuj panel filtrów
        is_gallery_populated = bool(self.gallery_manager.file_pairs_list)
        self.size_control_panel.setVisible(is_gallery_populated)

        # Przywróć przycisk
        self.select_folder_button.setText("Wybierz Folder Roboczy")
        self.select_folder_button.setEnabled(True)

        # Pokaż przycisk odświeżania cache
        self.clear_cache_button.setVisible(True)

        # Zapisz metadane
        self._save_metadata()

        # NAPRAWKA: Uruchom obliczanie statystyk folderów także w change_directory
        if hasattr(self, "directory_tree_manager"):
            QTimer.singleShot(
                1000, self.directory_tree_manager.start_background_stats_calculation
            )

        # NAPRAWKA PROGRESS BAR: Ustaw na 100% po zakończeniu bez resetowania drzewa
        actual_tiles_count = len(self.gallery_manager.file_pairs_list)
        self.progress_manager.show_progress(
            100, f"✅ Załadowano {actual_tiles_count} kafelków!"
        )

        # Krótkie opóźnienie żeby użytkownik zobaczył 100% przed ukryciem
        QTimer.singleShot(500, self.progress_manager.hide_progress)

        logging.info(
            f"Widok zaktualizowany bez resetowania drzewa. Wyświetlono po filtracji: "
            f"{actual_tiles_count}."
        )

    # 🚨 ETAP 2 - POPRAWKA 5: Obsługa eksploratora plików
    def on_explorer_folder_changed(self, path: str):
        """Obsługa zmiany folderu w eksploratorze."""
        self.logger.info(f"Explorer folder changed to: {path}")
        # Opcjonalnie synchronizuj z głównym folderem roboczym
        # W przyszłości można dodać opcję synchronizacji

    def on_explorer_file_selected(self, file_path: str):
        """Obsługa wyboru pliku w eksploratorze."""
        self.logger.info(f"Explorer file selected: {file_path}")
        # Opcjonalnie otwórz plik lub pokaż podgląd
        # W przyszłości można dodać obsługę podglądu plików

    def set_working_directory(self, directory: str):
        """
        🚨 ETAP 2: Ustawia folder roboczy dla wszystkich zakładek.
        Rozszerzone o synchronizację z eksploratorem plików.
        """
        # Istniejący kod...
        self.controller.current_directory = directory

        # 🚨 NOWE: Ustaw ścieżkę dla eksploratora plików
        if hasattr(self, "file_explorer_tab"):
            self.file_explorer_tab.set_root_path(directory)
