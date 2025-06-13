"""
Główne okno aplikacji - zrefaktoryzowana wersja.
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
from src.ui.widgets.filter_panel import FilterPanel
from src.ui.widgets.gallery_tab import GalleryTab
from src.ui.widgets.preview_dialog import PreviewDialog
from src.ui.widgets.unpaired_files_tab import UnpairedFilesTab
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
        if default_folder and os.path.exists(default_folder) and os.path.isdir(default_folder):
            logging.debug(f"Inicjalizacja drzewa katalogów: {default_folder}")
            self.directory_tree_manager.init_directory_tree_without_expansion(default_folder)

        logging.info("Główne okno aplikacji zostało zainicjalizowane")

    def _init_data(self):
        """Inicjalizuje dane aplikacji."""
        # KRYTYCZNE: AppConfig musi być pierwsze - inne komponenty go używają!
        self.app_config = app_config.AppConfig()

        # ETAP 2 FINAL: MVC Controller - centralna logika biznesowa
        self.controller = MainWindowController(self)

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

        # Główny layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

    def _init_ui(self):
        """
        Inicjalizuje elementy interfejsu użytkownika.
        """
        # Najpierw tworzymy menu bar
        self.setup_menu_bar()

        # Panel górny
        self._create_top_panel()

        # Panel filtrów
        self.filter_panel = FilterPanel()
        self.filter_panel.setVisible(True)  # Zawsze widoczny
        self.filter_panel.setEnabled(False)  # Ale zablokowany na start
        self.filter_panel.connect_signals(self._apply_filters_and_update_view)
        self.main_layout.addWidget(self.filter_panel)

        # Bulk operations panel
        self._create_bulk_operations_panel()

        # TabWidget jako główny kontener widoków
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # Inicjalizacja managerów zakładek
        self.gallery_tab_manager = GalleryTab(self)
        self.unpaired_files_tab_manager = UnpairedFilesTab(self)

        # Zakładka galerii
        gallery_widget = self.gallery_tab_manager.create_gallery_tab()
        self.tab_widget.addTab(gallery_widget, "Galeria")

        # Zakładka niesparowanych plików
        unpaired_widget = self.unpaired_files_tab_manager.create_unpaired_files_tab()
        self.tab_widget.addTab(unpaired_widget, "Parowanie Plików")

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
        tools_menu.addAction(
            "🗑️ Usuń wszystkie foldery .app_metadata", self.remove_all_metadata_folders
        )
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
        try:
            # Import tylko jeśli nie jest jeszcze zaimportowany
            if not hasattr(self, "_preferences_dialog_class"):
                from src.ui.widgets.preferences_dialog import PreferencesDialog

                self._preferences_dialog_class = PreferencesDialog

            dialog = self._preferences_dialog_class(self)
            # Połącz sygnał zmiany preferencji
            dialog.preferences_changed.connect(self._handle_preferences_changed)
            result = dialog.exec()

            if result == QDialog.DialogCode.Accepted:
                logging.info("Okno preferencji zamknięte - zmiany zaakceptowane")
            else:
                logging.info("Okno preferencji anulowane")

        except ImportError:
            QMessageBox.information(
                self,
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
            self.app_config.reload()

            # Zastosuj nowe ustawienia do UI
            if hasattr(self, "gallery_manager"):
                # Odśwież cache miniaturek jeśli zmienił się rozmiar
                if hasattr(self.gallery_manager, "thumbnail_cache"):
                    max_entries = self.app_config.get(
                        "thumbnail_cache_max_entries", 500
                    )
                    max_memory = self.app_config.get(
                        "thumbnail_cache_max_memory_mb", 100
                    )
                    self.gallery_manager.thumbnail_cache.update_limits(
                        max_entries, max_memory
                    )

            # Odśwież slider miniatur
            if hasattr(self, "size_slider"):
                saved_position = self.app_config.get_thumbnail_slider_position()
                if saved_position != self.size_slider.value():
                    self.size_slider.setValue(saved_position)
                    self._update_thumbnail_size()

            # Odśwież widok jeśli jest otwarty folder
            if self.controller.current_directory:
                self.refresh_all_views()

            logging.info("Nowe ustawienia preferencji zostały zastosowane")

        except Exception as e:
            logging.error(f"Błąd podczas aplikowania nowych preferencji: {e}")
            QMessageBox.warning(
                self,
                "Ostrzeżenie",
                "Niektóre nowe ustawienia mogą wymagać ponownego uruchomienia aplikacji.",
            )

    def remove_all_metadata_folders(self):
        """Usuwa wszystkie foldery .app_metadata z folderu roboczego."""
        if not self.controller.current_directory:
            QMessageBox.warning(self, "Uwaga", "Nie wybrano folderu roboczego.")
            return

        reply = QMessageBox.question(
            self,
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
            self._show_progress(0, "Szukanie folderów .app_metadata...")

            # Znajdź wszystkie foldery .app_metadata
            metadata_folders = []
            root_path = Path(self.controller.current_directory)

            for folder in root_path.rglob(".app_metadata"):
                if folder.is_dir():
                    metadata_folders.append(folder)

            if not metadata_folders:
                QMessageBox.information(
                    self, "Informacja", "Nie znaleziono folderów .app_metadata."
                )
                self._hide_progress()
                return

            total_folders = len(metadata_folders)
            self._show_progress(
                10, f"Znaleziono {total_folders} folderów do usunięcia..."
            )

            # Usuń foldery
            deleted_count = 0
            for i, folder in enumerate(metadata_folders):
                try:
                    shutil.rmtree(folder)
                    deleted_count += 1
                    progress = 10 + int((i + 1) / total_folders * 80)
                    self._show_progress(progress, f"Usuwanie {i+1}/{total_folders}...")
                except Exception as e:
                    logging.error(f"Błąd podczas usuwania {folder}: {e}")

            self._show_progress(100, f"Usunięto {deleted_count} folderów")
            QMessageBox.information(
                self,
                "Zakończono",
                f"Usunięto {deleted_count} z {total_folders} folderów .app_metadata",
            )

        except Exception as e:
            error_msg = f"Błąd podczas czyszczenia metadanych: {e}"
            logging.error(error_msg)
            QMessageBox.critical(self, "Błąd", error_msg)
            self._hide_progress()

    def show_about(self):
        """Wyświetla informacje o programie."""
        QMessageBox.about(
            self,
            "O programie",
            "CFAB_3DHUB v1.0\n\n"
            "Aplikacja do zarządzania parami plików archiwum-podgląd\n\n"
            "Funkcje:\n"
            "• Automatyczne parowanie plików\n"
            "• Zarządzanie metadanymi\n"
            "• Operacje masowe na plikach\n"
            "• Zaawansowane filtrowanie",
        )

    def _create_top_panel(self):
        """
        Tworzy panel górny z przyciskami i kontrolkami.
        """
        self.top_panel = QWidget()
        self.top_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.top_layout = QHBoxLayout(self.top_panel)
        self.top_layout.setContentsMargins(0, 0, 0, 0)

        # Przycisk wyboru folderu
        self.select_folder_button = QPushButton("Wybierz Folder Roboczy")
        self.select_folder_button.clicked.connect(self._select_working_directory)
        self.top_layout.addWidget(self.select_folder_button)

        # Przycisk czyszczenia cache
        self.clear_cache_button = QPushButton("Odśwież (Wyczyść Cache)")
        self.clear_cache_button.clicked.connect(self._force_refresh)
        self.clear_cache_button.setVisible(False)
        self.top_layout.addWidget(self.clear_cache_button)

        # Panel kontroli rozmiaru
        self._create_size_control_panel()

        self.main_layout.addWidget(self.top_panel)

    def _create_size_control_panel(self):
        """
        Tworzy panel kontroli rozmiaru miniatur.
        """
        self.size_control_panel = QWidget()
        self.size_control_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.size_control_layout = QHBoxLayout(self.size_control_panel)
        self.size_control_layout.setContentsMargins(0, 0, 0, 0)

        # Label dla suwaka
        self.size_label = QLabel("Rozmiar miniatur:")
        self.size_control_layout.addWidget(self.size_label)

        # Suwak rozmiaru miniatur
        self.size_slider = QSlider()
        self.size_slider.setOrientation(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(0)
        self.size_slider.setMaximum(100)

        # Ustawienie wartości początkowej suwaka na wymuszone 50%
        self.size_slider.setValue(self.initial_slider_position)

        self.size_slider.sliderReleased.connect(self._update_thumbnail_size)
        self.size_control_layout.addWidget(self.size_slider)

        self.top_layout.addStretch(1)
        self.top_layout.addWidget(self.size_control_panel)

    def _create_bulk_operations_panel(self):
        """
        Creates the bulk operations panel for selected tiles.
        """
        self.bulk_operations_panel = QWidget()
        self.bulk_operations_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.bulk_operations_panel.setVisible(False)  # Hidden by default

        # Apply styling for better visibility
        self.bulk_operations_panel.setStyleSheet(
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

        bulk_layout = QHBoxLayout(self.bulk_operations_panel)
        bulk_layout.setContentsMargins(10, 5, 10, 5)

        # Selected count label
        self.selected_count_label = QLabel("Zaznaczone: 0")
        bulk_layout.addWidget(self.selected_count_label)

        bulk_layout.addStretch(1)

        # Select all button
        self.select_all_button = QPushButton("Zaznacz wszystkie")
        self.select_all_button.clicked.connect(self._select_all_tiles)
        bulk_layout.addWidget(self.select_all_button)

        # Clear selection button
        self.clear_selection_button = QPushButton("Wyczyść zaznaczenie")
        self.clear_selection_button.clicked.connect(self._clear_all_selections)
        bulk_layout.addWidget(self.clear_selection_button)

        # Separator
        separator = QLabel("|")
        separator.setStyleSheet("color: #999; margin: 0 10px;")
        bulk_layout.addWidget(separator)

        # Bulk move button
        self.bulk_move_button = QPushButton("Przenieś zaznaczone")
        self.bulk_move_button.clicked.connect(self._perform_bulk_move)
        bulk_layout.addWidget(self.bulk_move_button)

        # Bulk delete button
        self.bulk_delete_button = QPushButton("Usuń zaznaczone")
        self.bulk_delete_button.setStyleSheet(
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
        self.bulk_delete_button.clicked.connect(self._perform_bulk_delete)
        bulk_layout.addWidget(self.bulk_delete_button)

        self.main_layout.addWidget(self.bulk_operations_panel)

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
                logging.debug("✅ Dodano kontrolki expand/collapse do UI")

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
            logging.info("⚙️ Auto-load ostatniego folderu WYŁĄCZONE w preferencjach")
            return

        last_folder = self.app_config.get("default_working_directory", "")
        if not last_folder:
            logging.debug("Brak zapisanego folderu roboczego")
            return

        import os

        if not os.path.exists(last_folder) or not os.path.isdir(last_folder):
            logging.warning(f"❌ Zapisany folder roboczy nie istnieje: {last_folder}")
            return

        try:
            logging.info(f"🔄 Auto-loading ostatniego folderu: {last_folder}")
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
        self.progress_label.setText("✅ Preferencje wczytane")
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
        self._cleanup_threads()
        event.accept()

    def _cleanup_threads(self):
        """
        Czyści wszystkie aktywne wątki - Problem #3: używa ThreadCoordinator.
        """
        # Użyj ThreadCoordinator zamiast ręcznego zarządzania
        if hasattr(self, "thread_coordinator"):
            self.thread_coordinator.cleanup_all_threads()
        else:
            # Fallback - stary sposób dla kompatybilności
            if self.scan_thread and self.scan_thread.isRunning():
                logging.info("Kończenie wątku skanowania przy zamykaniu aplikacji...")
                self.scan_thread.quit()
                if not self.scan_thread.wait(self.app_config.thread_wait_timeout_ms):
                    logging.warning("Wątek skanowania nie zakończył się, wymuszam...")
                    self.scan_thread.terminate()
                    self.scan_thread.wait()

            if self.data_processing_thread and self.data_processing_thread.isRunning():
                logging.info(
                    "Kończenie wątku przetwarzania przy zamykaniu aplikacji..."
                )
                self.data_processing_thread.quit()
                if not self.data_processing_thread.wait(
                    self.app_config.thread_wait_timeout_ms
                ):
                    logging.warning(
                        "Wątek przetwarzania nie zakończył się, wymuszam..."
                    )
                    self.data_processing_thread.terminate()
                    self.data_processing_thread.wait()

    def _select_working_directory(self, directory_path=None):
        """
        Otwiera dialog wyboru folderu lub używa podanej ścieżki.
        Problem #4: Dodano walidację danych wejściowych.
        """
        # Przerwanie poprzedniego skanowania jeśli aktywne
        self._stop_current_scanning()

        if directory_path:
            path = directory_path
        else:
            path = QFileDialog.getExistingDirectory(self, "Wybierz Folder Roboczy")

        if not path:
            logging.debug("Nie wybrano folderu.")
            return

        # Problem #4: Walidacja ścieżki
        if not self._validate_directory_path(path):
            return

        # Ustaw nowy folder roboczy przez kontroler
        normalized_path = normalize_path(path)
        base_folder_name = os.path.basename(normalized_path)
        self.setWindowTitle(f"CFAB_3DHUB - {base_folder_name}")

        # NIGDY NIE NADPISUJ DOMYŚLNEGO FOLDERU AUTOMATYCZNIE!
        # To jest NIEDOPUSZCZALNE zachowanie!
        if not hasattr(self, "_is_auto_loading"):
            logging.info(f"📂 Folder wybrany ręcznie ale NIE nadpisuję domyślnego!")
        else:
            logging.info(f"🔄 Auto-loading z domyślnego folderu")

        logging.info("Wybrano folder roboczy: %s", normalized_path)

        # Wyczyść dane i rozpocznij skanowanie
        self._clear_all_data_and_views()
        self._start_folder_scanning(normalized_path)

    def _validate_directory_path(self, path: str) -> bool:
        """
        Waliduje ścieżkę do folderu - Problem #4.

        Args:
            path: Ścieżka do walidacji

        Returns:
            True jeśli ścieżka jest poprawna
        """
        if not path or not isinstance(path, str):
            QMessageBox.warning(self, "Błąd", "Nieprawidłowa ścieżka do folderu.")
            return False

        if not os.path.exists(path):
            QMessageBox.warning(self, "Błąd", f"Folder nie istnieje:\n{path}")
            return False

        if not os.path.isdir(path):
            QMessageBox.warning(
                self, "Błąd", f"Ścieżka nie wskazuje na folder:\n{path}"
            )
            return False

        if not os.access(path, os.R_OK):
            QMessageBox.warning(
                self, "Błąd", f"Brak uprawnień do odczytu folderu:\n{path}"
            )
            return False

        return True

    def _stop_current_scanning(self):
        """
        Przerywa aktualnie działające skanowanie.
        """
        if self.scan_thread and self.scan_thread.isRunning():
            logging.warning(
                "Nowe skanowanie żądane, gdy poprzednie jest aktywne. "
                "Przerywam stary wątek i uruchamiam nowy."
            )
            if self.scan_worker:
                self.scan_worker.stop()
            try:
                self.scan_worker.finished.disconnect()
                self.scan_worker.error.disconnect()
            except (TypeError, AttributeError):
                logging.debug("Nie można było odłączyć sygnałów od starego workera.")
            self.scan_thread.quit()
            self.scan_thread.wait(self.app_config.thread_wait_timeout_ms // 2)

    def _start_folder_scanning(self, directory_path: str):
        """
        ETAP 2 FINAL: Delegacja skanowania do MainWindowController (MVC).
        """
        # UI Feedback
        self.select_folder_button.setText("Skanowanie...")
        self.select_folder_button.setEnabled(False)

        # DELEGACJA DO KONTROLERA - NO MORE WORKER THREADS!
        success = self.controller.handle_folder_selection(directory_path)

        # Przywróć UI state
        self.select_folder_button.setText("Wybierz Folder")
        self.select_folder_button.setEnabled(True)

        if success:
            logging.info(f"Controller scan SUCCESS: {directory_path}")
        else:
            logging.warning(f"Controller scan FAILED: {directory_path}")

    def _on_scan_thread_finished(self):
        """
        Slot wywoływany po zakończeniu pracy wątku skanującego.
        """
        # Przywróć przycisk skanowania
        self.select_folder_button.setText("Wybierz Folder")
        self.select_folder_button.setEnabled(True)

        # Wyczyść referencje do wątku
        if self.scan_thread:
            self.scan_thread.deleteLater()
            self.scan_thread = None
        if self.scan_worker:
            self.scan_worker.deleteLater()
            self.scan_worker = None
        logging.debug("Wątek skanujący i worker zostały bezpiecznie wyczyszczone.")

    def _force_refresh(self):
        """
        Wymusza ponowne skanowanie poprzez czyszczenie cache.
        """
        if self.controller.current_directory:
            from src.logic.scanner import clear_cache

            clear_cache()
            logging.info("Cache wyczyszczony - wymuszono ponowne skanowanie")
            self._select_working_directory(self.controller.current_directory)

    def _clear_all_data_and_views(self):
        """
        Czyści wszystkie dane plików i odpowiednie widoki.
        """
        self.controller.clear_all_data_and_views()

    def _clear_unpaired_files_lists(self):
        """
        Czyści listy niesparowanych plików w interfejsie użytkownika.
        """
        self.unpaired_archives_list_widget.clear()
        self.unpaired_previews_list_widget.clear()

        # Wyczyść kontener miniaturek
        while self.unpaired_previews_layout.count():
            widget_to_remove = self.unpaired_previews_layout.itemAt(0).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)
                self.unpaired_previews_layout.removeWidget(widget_to_remove)

        # NAPRAWKA: Sortuj alfabetycznie przed wyświetleniem
        sorted_archives = sorted(self.controller.unpaired_archives, 
                                key=lambda x: os.path.basename(x).lower())
        sorted_previews = sorted(self.controller.unpaired_previews, 
                                key=lambda x: os.path.basename(x).lower())

        # Aktualizuj listę archiwów (posortowane)
        for archive_path in sorted_archives:
            item = QListWidgetItem(os.path.basename(archive_path))
            item.setData(Qt.ItemDataRole.UserRole, archive_path)
            self.unpaired_archives_list_widget.addItem(item)

        # Aktualizuj miniaturki podglądów (posortowane)
        for preview_path in sorted_previews:
            # Dodaj do ukrytego QListWidget dla kompatybilności
            item = QListWidgetItem(os.path.basename(preview_path))
            item.setData(Qt.ItemDataRole.UserRole, preview_path)
            self.unpaired_previews_list_widget.addItem(item)

            # Dodaj miniaturkę przez manager unpaired files
            if hasattr(self, "unpaired_files_tab_manager"):
                self.unpaired_files_tab_manager._add_preview_thumbnail(preview_path)

        logging.debug(
            f"Zaktualizowano listy niesparowanych: "
            f"{len(self.controller.unpaired_archives)} archiwów, "
            f"{len(self.controller.unpaired_previews)} podglądów."
        )
        # Deleguj update przycisku parowania do managera unpaired files
        if hasattr(self, "unpaired_files_tab_manager"):
            logging.info(
                "🔍 Sprawdzam stan unpaired_files_tab_manager w _on_tile_loading_finished..."
            )
            logging.info(
                f"📋 unpaired_archives_list_widget: {hasattr(self.unpaired_files_tab_manager, 'unpaired_archives_list_widget')}"
            )
            if hasattr(
                self.unpaired_files_tab_manager, "unpaired_archives_list_widget"
            ):
                logging.info(
                    f"📋 unpaired_archives_list_widget value: {self.unpaired_files_tab_manager.unpaired_archives_list_widget}"
                )
            logging.info(
                f"📋 unpaired_previews_list_widget: {hasattr(self.unpaired_files_tab_manager, 'unpaired_previews_list_widget')}"
            )

            # BEZPOŚREDNIA AKTUALIZACJA jako FALLBACK
            logging.debug("FALLBACK: Bezpośrednia aktualizacja unpaired")
            self._update_unpaired_files_direct()

    def _update_unpaired_files_direct(self):
        """
        FALLBACK: Bezpośrednia aktualizacja niesparowanych plików.
        Używana gdy manager nie działa poprawnie.
        """
        try:
            logging.debug("FALLBACK: Rozpoczynam aktualizację unpaired")

            # Sprawdź czy mamy widgety przypisane do main_window
            if (
                not hasattr(self, "unpaired_archives_list_widget")
                or not self.unpaired_archives_list_widget
            ):
                logging.warning(
                    "⚠️ FALLBACK: Brak widgetów w main_window - pomijam aktualizację"
                )
                return

            # Wyczyść stare dane
            self.unpaired_archives_list_widget.clear()
            self.unpaired_previews_list_widget.clear()

            # NAPRAWKA FALLBACK: Sortuj alfabetycznie przed wyświetleniem
            sorted_archives = sorted(self.controller.unpaired_archives, 
                                    key=lambda x: os.path.basename(x).lower())
            sorted_previews = sorted(self.controller.unpaired_previews, 
                                    key=lambda x: os.path.basename(x).lower())

            # Dodaj archiwa (posortowane)
            archives_added = 0
            for archive_path in sorted_archives:
                item = QListWidgetItem(os.path.basename(archive_path))
                item.setData(Qt.ItemDataRole.UserRole, archive_path)
                self.unpaired_archives_list_widget.addItem(item)
                archives_added += 1
                # Spam logów wyeliminowany - każdy plik nie potrzebuje osobnego loga

            # Dodaj podglądy (posortowane)
            previews_added = 0
            for preview_path in sorted_previews:
                item = QListWidgetItem(os.path.basename(preview_path))
                item.setData(Qt.ItemDataRole.UserRole, preview_path)
                self.unpaired_previews_list_widget.addItem(item)
                previews_added += 1
                # Spam logów wyeliminowany - każdy plik nie potrzebuje osobnego loga

            logging.debug(f"FALLBACK: Dodano {archives_added} archiwów, {previews_added} podglądów")

        except Exception as e:
            logging.error(f"❌ FALLBACK ERROR: {e}")

            self.unpaired_files_tab_manager.update_unpaired_files_lists()

    def _handle_scan_finished(self, found_pairs, unpaired_archives, unpaired_previews):
        """
        Obsługuje wyniki pomyślnie zakończonego skanowania folderu.
        """
        logging.info(
            f"Skanowanie folderu {self.controller.current_directory} "
            f"zakończone pomyślnie."
        )

        self.controller.handle_scan_finished(
            found_pairs, unpaired_archives, unpaired_previews
        )

        # Wyczyść poprzednie widgety kafelków
        self.gallery_manager.clear_gallery()

        # Uruchom workera do tworzenia kafelków w tle
        if found_pairs:
            self._start_data_processing_worker(found_pairs)
        else:
            self._on_tile_loading_finished()

    def _start_data_processing_worker(self, file_pairs: list[FilePair]):
        """
        Inicjalizuje i uruchamia workera do przetwarzania danych.
        """
        # NAPRAWKA: Resetuj liczniki progress bara na początku operacji
        if hasattr(self, '_batch_processing_started'):
            delattr(self, '_batch_processing_started')
        
        # NAPRAWKA: Prawidłowo zakończ poprzedni worker jeśli nadal działa
        if self.data_processing_thread and self.data_processing_thread.isRunning():
            logging.warning(
                "Poprzedni worker przetwarzania nadal działa - przerywam go i uruchamiam nowy"
            )
            # Przerwij poprzedni worker
            if self.data_processing_worker:
                try:
                    self.data_processing_worker.finished.disconnect()
                except (TypeError, AttributeError):
                    pass  # Sygnał może być już odłączony
                self.data_processing_worker.stop()

            # Zakończ poprzedni wątek
            self.data_processing_thread.quit()
            if not self.data_processing_thread.wait(
                self.app_config.thread_wait_timeout_ms
            ):  # Czekaj maksymalnie według konfiguracji
                logging.warning("Wymuszenie zakończenia poprzedniego workera")
                self.data_processing_thread.terminate()
                self.data_processing_thread.wait()

        self.data_processing_thread = QThread()
        self.data_processing_worker = DataProcessingWorker(
            self.controller.current_directory, file_pairs
        )
        self.data_processing_worker.moveToThread(self.data_processing_thread)

        # Podłączenie sygnałów
        self.data_processing_worker.tile_data_ready.connect(
            self._create_tile_widget_for_pair
        )
        # NOWY: obsługa batch processing kafelków
        self.data_processing_worker.tiles_batch_ready.connect(
            self._create_tile_widgets_batch
        )
        self.data_processing_worker.finished.connect(self._on_tile_loading_finished)
        # NAPRAWKA: Podłącz sygnały postępu do pasków postępu
        self.data_processing_worker.progress.connect(self._show_progress)
        self.data_processing_worker.error.connect(self._handle_worker_error)
        self.data_processing_thread.started.connect(self.data_processing_worker.run)

        self.data_processing_thread.start()
        logging.info(
            f"Uruchomiono nowy worker do przetwarzania {len(file_pairs)} par plików"
        )

    def _start_data_processing_worker_without_tree_reset(self, file_pairs: list[FilePair]):
        """
        Inicjalizuje i uruchamia workera do przetwarzania danych BEZ resetowania drzewa katalogów.
        Używane przy zmianie folderu z drzewa aby zachować strukturę.
        """
        # NAPRAWKA: Resetuj liczniki progress bara na początku operacji
        if hasattr(self, '_batch_processing_started'):
            delattr(self, '_batch_processing_started')
            
        # NAPRAWKA: Prawidłowo zakończ poprzedni worker jeśli nadal działa
        if self.data_processing_thread and self.data_processing_thread.isRunning():
            logging.warning(
                "Poprzedni worker przetwarzania nadal działa - przerywam go i uruchamiam nowy (bez resetowania drzewa)"
            )
            # Przerwij poprzedni worker
            if self.data_processing_worker:
                try:
                    self.data_processing_worker.finished.disconnect()
                except (TypeError, AttributeError):
                    pass  # Sygnał może być już odłączony
                self.data_processing_worker.stop()

            # Zakończ poprzedni wątek
            self.data_processing_thread.quit()
            if not self.data_processing_thread.wait(
                self.app_config.thread_wait_timeout_ms
            ):  # Czekaj maksymalnie według konfiguracji
                logging.warning("Wymuszenie zakończenia poprzedniego workera")
                self.data_processing_thread.terminate()
                self.data_processing_thread.wait()

        self.data_processing_thread = QThread()
        self.data_processing_worker = DataProcessingWorker(
            self.controller.current_directory, file_pairs
        )
        self.data_processing_worker.moveToThread(self.data_processing_thread)

        # Podłączenie sygnałów
        self.data_processing_worker.tile_data_ready.connect(
            self._create_tile_widget_for_pair
        )
        # NOWY: obsługa batch processing kafelków
        self.data_processing_worker.tiles_batch_ready.connect(
            self._create_tile_widgets_batch
        )
        # RÓŻNICA: Podłącz do metody BEZ resetowania drzewa (wrapper ignoruje listę)
        self.data_processing_worker.finished.connect(lambda processed_pairs: self._finish_folder_change_without_tree_reset())
        # NAPRAWKA: Podłącz sygnały postępu do pasków postępu
        self.data_processing_worker.progress.connect(self._show_progress)
        self.data_processing_worker.error.connect(self._handle_worker_error)
        self.data_processing_thread.started.connect(self.data_processing_worker.run)

        self.data_processing_thread.start()
        logging.info(
            f"Uruchomiono nowy worker do przetwarzania {len(file_pairs)} par plików (bez resetowania drzewa)"
        )

    def _create_tile_widget_for_pair(self, file_pair: FilePair):
        """
        Tworzy pojedynczy kafelek dla pary plików.
        """
        # Walidacja danych wejściowych - Problem #4
        if not file_pair:
            logging.warning("Otrzymano None zamiast FilePair")
            return None

        if not hasattr(file_pair, "archive_path") or not file_pair.archive_path:
            logging.error(f"Nieprawidłowy FilePair - brak archive_path: {file_pair}")
            return None

        tile = self.gallery_manager.create_tile_widget_for_pair(file_pair, self)
        if tile:
            # Podłącz sygnały kafelka
            tile.archive_open_requested.connect(self.open_archive)
            tile.preview_image_requested.connect(self._show_preview_dialog)
            tile.tile_selected.connect(self._handle_tile_selection_changed)
            tile.stars_changed.connect(self._handle_stars_changed)
            tile.color_tag_changed.connect(self._handle_color_tag_changed)
            tile.tile_context_menu_requested.connect(self._show_file_context_menu)
            
            # NAPRAWKA: Podłącz callback do śledzenia ładowania miniaturek
            original_on_thumbnail_loaded = tile._on_thumbnail_loaded
            def thumbnail_loaded_callback(*args, **kwargs):
                result = original_on_thumbnail_loaded(*args, **kwargs)
                self._on_thumbnail_progress()
                return result
            tile._on_thumbnail_loaded = thumbnail_loaded_callback

        return tile

    def _on_thumbnail_progress(self):
        """
        Wywoływana gdy miniatura zostanie załadowana.
        Aktualizuje progress bar dla ładowania miniaturek.
        """
        if not hasattr(self, '_thumbnails_with_images_loaded'):
            self._thumbnails_with_images_loaded = 0
            
        self._thumbnails_with_images_loaded += 1
        
        # Progress bar: 0-50% kafelki, 50-100% miniaturki
        if hasattr(self, '_total_thumbnails_to_load'):
            thumbnail_percent = int((self._thumbnails_with_images_loaded / max(self._total_thumbnails_to_load, 1)) * 50)
            total_percent = 50 + thumbnail_percent  # 50% za kafelki + 50% za miniaturki
            
            self._show_progress(total_percent, f"Ładowanie miniaturek: {self._thumbnails_with_images_loaded}/{self._total_thumbnails_to_load}...")
            
            # Ukryj progress bar gdy wszystkie miniaturki są załadowane
            if self._thumbnails_with_images_loaded >= self._total_thumbnails_to_load:
                QTimer.singleShot(500, self._hide_progress)  # Ukryj po pół sekundy

    def _create_tile_widgets_batch(self, file_pairs_batch: list):
        """
        Tworzy kafelki dla batch'a par plików - OPTYMALIZACJA dla wydajności.
        Zamiast tworzyć po jednym kafelku, tworzy je grupami aby zmniejszyć obciążenie UI.

        Args:
            file_pairs_batch: Lista obiektów FilePair do przetworzenia w tym batch'u
        """
        # Resetuj liczniki na początku nowej operacji ładowania
        if not hasattr(self, '_batch_processing_started'):
            self._total_thumbnails_to_load = len(self.controller.current_file_pairs)
            self._thumbnails_loaded = 0
            self._thumbnails_with_images_loaded = 0
            self._batch_processing_started = True
        
        batch_size = len(file_pairs_batch)
        
        # Aktualizuj progress bar dla tworzenia kafelków (bez miniaturek)
        percent = int((self._thumbnails_loaded / max(self._total_thumbnails_to_load, 1)) * 50)  # 50% dla kafelków
        self._show_progress(percent, f"Tworzenie kafelków: {self._thumbnails_loaded}/{self._total_thumbnails_to_load}...")

        # Czasowo wyłącz aktualizacje UI dla lepszej wydajności
        self.gallery_manager.tiles_container.setUpdatesEnabled(False)

        try:
            created_count = 0
            for file_pair in file_pairs_batch:
                tile = self._create_tile_widget_for_pair(file_pair)
                if tile:
                    created_count += 1
                    self._thumbnails_loaded += 1
                    
                    # Aktualizuj progress co 5 kafelków
                    if self._thumbnails_loaded % 5 == 0 or self._thumbnails_loaded >= self._total_thumbnails_to_load:
                        percent = int((self._thumbnails_loaded / max(self._total_thumbnails_to_load, 1)) * 50)
                        self._show_progress(percent, f"Tworzenie kafelków: {self._thumbnails_loaded}/{self._total_thumbnails_to_load}...")

        finally:
            # Przywróć aktualizacje UI
            self.gallery_manager.tiles_container.setUpdatesEnabled(True)
            self.gallery_manager.tiles_container.update()  # Wymuś odświeżenie

    def _on_tile_loading_finished(self):
        """
        Wywoływane po zakończeniu tworzenia wszystkich kafelków.
        """
        logging.info("Zakończono tworzenie wszystkich kafelków.")

        # Zastosuj filtry i odśwież widok
        self._apply_filters_and_update_view()
        # Delegacja do managera zamiast wywołania nieistniejącej metody
        if hasattr(self, "unpaired_files_tab_manager"):
            self.unpaired_files_tab_manager.update_unpaired_files_lists()

        # Pokaż interfejs
        self.filter_panel.setEnabled(True)  # Odblokuj panel filtrów
        is_gallery_populated = bool(self.gallery_manager.file_pairs_list)
        self.size_control_panel.setVisible(is_gallery_populated)
        # Zakładka parowania zawsze widoczna

        # Inicjalizacja drzewa katalogów - TYLKO ustawienie root path, BEZ automatycznego rozwijania
        if self.controller.current_directory:
            self.directory_tree_manager.init_directory_tree_without_expansion(
                self.controller.current_directory
            )

        # Upewnij się że drzewo folderów jest widoczne
        if hasattr(self, "folder_tree"):
            self.folder_tree.setVisible(True)
            logging.debug(f"Drzewo folderów widoczne: {self.folder_tree.isVisible()}")
            logging.debug(f"Splitter rozmiary: {self.splitter.sizes()}")

        # Przywróć przycisk
        self.select_folder_button.setText("Wybierz Folder Roboczy")
        self.select_folder_button.setEnabled(True)

        # Pokaż przycisk odświeżania cache
        self.clear_cache_button.setVisible(True)

        # Zapisz metadane
        self._save_metadata()

        logging.info(
            f"Widok zaktualizowany. Wyświetlono po filtracji: "
            f"{len(self.gallery_manager.file_pairs_list)}."
        )

    def _handle_scan_error(self, error_message: str):
        """
        Obsługuje błędy występujące podczas skanowania folderu.
        """
        logging.error(f"Błąd skanowania: {error_message}")
        QMessageBox.critical(
            self,
            "Błąd Skanowania",
            "Wystąpił błąd podczas skanowania folderu:\n" f"{error_message}",
        )

        self._clear_all_data_and_views()

        # Przywróć przycisk
        self.select_folder_button.setText("Wybierz Folder Roboczy")
        self.select_folder_button.setEnabled(True)
        self.filter_panel.setEnabled(False)  # Zablokuj przy błędzie

    def _apply_filters_and_update_view(self):
        """
        Zbiera kryteria, filtruje pary i aktualizuje galerię.
        """
        # Deleguj do gallery_tab_manager
        self.gallery_tab_manager.apply_filters_and_update_view()

    def _update_gallery_view(self):
        """
        Aktualizuje widok galerii.
        """
        self.gallery_tab_manager.update_gallery_view()

    def refresh_all_views(self, new_selection=None):
        """
        Inteligentne odświeżanie widoków - Problem #5.
        Unika pełnego ponownego skanowania gdy nie jest konieczne.

        Args:
            new_selection: FilePair do zaznaczenia po odświeżeniu (opcjonalne)
        """
        if not self.controller.current_directory:
            return

        # Zapobiegnij duplikowaniu operacji skanowania
        if (
            hasattr(self, "scan_thread")
            and self.scan_thread
            and self.scan_thread.isRunning()
        ):
            logging.info("Skanowanie już w toku - pomijanie refresh_all_views")
            return

        logging.info("Inteligentne odświeżanie widoków po operacji na plikach")

        # Zapisz zaznaczenie do przywrócenia po odświeżeniu
        if new_selection:
            self._pending_selection = new_selection

        # Zamiast pełnego skanowania, odśwież tylko UI z istniejącymi danymi
        self._apply_filters_and_update_view()
        # Delegacja do managera zamiast wywołania nieistniejącej metody
        if hasattr(self, "unpaired_files_tab_manager"):
            self.unpaired_files_tab_manager.update_unpaired_files_lists()

        # Zapisz metadane bez ponownego skanowania
        self._save_metadata()

        logging.info("Odświeżanie zakończone - bez ponownego skanowania")

    def force_full_refresh(self):
        """
        Wymusza pełne ponowne skanowanie bieżącego katalogu i odświeżenie
        wszystkich widoków.
        """
        current_folder = self.controller.current_directory
        if current_folder and os.path.isdir(current_folder):
            logging.info(f"Wymuszanie pełnego odświeżenia dla: {current_folder}")
            # Użyj istniejącej metody do ponownego wybrania folderu,
            # co uruchomi cały proces od nowa.
            self._select_working_directory(current_folder)
        else:
            logging.warning(
                "Nie można wymusić odświeżenia - brak bieżącego " "katalogu roboczego."
            )

    def _update_thumbnail_size(self):
        """
        Aktualizuje rozmiar miniatur na podstawie wartości suwaka.
        """
        # Deleguj do gallery_tab_manager
        self.gallery_tab_manager.update_thumbnail_size()
        
        # NAPRAWKA: Deleguj również do unpaired_files_tab_manager dla skalowania
        if hasattr(self, 'unpaired_files_tab_manager') and self.unpaired_files_tab_manager:
            # Pobierz aktualny rozmiar z gallery managera
            if hasattr(self, 'gallery_manager') and self.gallery_manager:
                current_size = self.gallery_manager._current_size_tuple
                self.unpaired_files_tab_manager.update_thumbnail_size(current_size)

    def resizeEvent(self, event):
        """
        Obsługuje zmianę rozmiaru okna.
        """  # Opóźnienie przerenderowania galerii
        self.resize_timer.start(self.app_config.resize_timer_delay_ms)
        super().resizeEvent(event)

    def _save_metadata(self):
        """
        Zapisuje metadane dla wszystkich par plików w osobnym wątku.
        Używa buforowania zmian.
        """
        if not self.controller.current_directory:
            logging.debug("Brak folderu roboczego lub par plików do zapisu metadanych.")
            return

        # Utwórz workera do zapisu metadanych używając fabryki
        worker = WorkerFactory.create_save_metadata_worker(
            self.controller.current_directory,
            self.controller.current_file_pairs,
            self.controller.unpaired_archives,
            self.controller.unpaired_previews,
        )

        # Podłącz sygnały
        self._setup_worker_connections(worker)
        worker.signals.finished.connect(self._on_metadata_saved)

        # Uruchom workera
        self._show_progress(
            0,
            f"Zapisywanie metadanych dla {len(self.controller.current_file_pairs)} par plików...",
        )
        self.thread_pool.start(worker)

    def _schedule_metadata_save(self):
        """Planuje zapis metadanych z opóźnieniem."""
        if not hasattr(self, "_metadata_save_timer"):
            self._metadata_save_timer = QTimer()
            self._metadata_save_timer.setSingleShot(True)
            self._metadata_save_timer.timeout.connect(self._save_metadata)

        # Zatrzymaj poprzedni timer jeśli istnieje
        self._metadata_save_timer.stop()
        # Uruchom nowy timer
        self._metadata_save_timer.start(2000)  # 2 sekundy opóźnienia

    def _on_metadata_saved(self, success):
        """
        Slot wywoływany po zakończeniu zapisu metadanych.

        Args:
            success: True jeśli metadane zostały zapisane pomyślnie
        """
        if success:
            self._show_progress(100, "Metadane zapisane pomyślnie")
            logging.debug("Metadane zapisane")
        else:
            self._show_progress(100, "Nie udało się zapisać metadanych")
            logging.error("❌ Nie udało się zapisać metadanych.")

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
        """ETAP 2 FINAL: Delegacja tile selection do MainWindowController (MVC)."""
        logging.info(
            f"✅ Controller tile selection: {file_pair.get_base_name()} -> {is_selected}"
        )

        # DELEGACJA DO KONTROLERA
        self.controller.handle_tile_selection(file_pair, is_selected)

        # LEGACY: Aktualizuj lokalny stan (stopniowo usuwane)
        if is_selected:
            self.controller.selected_tiles.add(file_pair)
        else:
            self.controller.selected_tiles.discard(file_pair)

        # Update bulk operations UI visibility
        self._update_bulk_operations_visibility()

        logging.debug(f"Total selected tiles: {len(self.controller.selected_tiles)}")

    def _update_bulk_operations_visibility(self):
        """Updates visibility of bulk operations controls based on selection count."""
        has_selection = len(self.controller.selected_tiles) > 0
        if hasattr(self, "bulk_operations_panel"):
            self.bulk_operations_panel.setVisible(has_selection)
            if hasattr(self, "selected_count_label"):
                count = len(self.controller.selected_tiles)
                self.selected_count_label.setText(f"Zaznaczone: {count}")

    def _clear_all_selections(self):
        """Clears all tile selections."""
        self.controller.selected_tiles.clear()  # Update all visible tiles to reflect cleared selection
        if hasattr(self, "gallery_manager") and self.gallery_manager:
            for tile_widget in self.gallery_manager.get_all_tile_widgets():
                if hasattr(tile_widget, "metadata_controls"):
                    tile_widget.metadata_controls.update_selection_display(False)

        self._update_bulk_operations_visibility()
        logging.debug("Cleared all tile selections")

    def _select_all_tiles(self):
        """Selects all currently visible tiles."""
        if hasattr(self, "gallery_manager") and self.gallery_manager:
            for tile_widget in self.gallery_manager.get_all_tile_widgets():
                if hasattr(tile_widget, "file_pair") and tile_widget.file_pair:
                    self.controller.selected_tiles.add(tile_widget.file_pair)
                    if hasattr(tile_widget, "metadata_controls"):
                        tile_widget.metadata_controls.update_selection_display(True)

            self._update_bulk_operations_visibility()
            logging.debug(
                f"Selected all {len(self.controller.selected_tiles)} visible tiles"
            )

    def _perform_bulk_delete(self):
        """ETAP 2 FINAL: Delegacja bulk delete do MainWindowController (MVC)."""
        if not self.controller.selected_tiles:
            return

        # DELEGACJA DO KONTROLERA - NO MORE DIRECT UI LOGIC!
        success = self.controller.handle_bulk_delete(
            list(self.controller.selected_tiles)
        )

        if success:
            # Wyczyść selekcję po pomyślnej operacji
            self.controller.selected_tiles.clear()
            self._update_bulk_operations_visibility()
            logging.info("Controller bulk delete SUCCESS")
        else:
            logging.warning("Controller bulk delete FAILED or CANCELLED")

    def _on_bulk_delete_finished(self, deleted_pairs):
        """
        Slot wywoływany po zakończeniu masowego usuwania plików.

        Args:
            deleted_pairs: Lista pomyślnie usuniętych par plików
        """
        if not deleted_pairs:
            self._show_progress(100, "Usuwanie przerwane lub nieudane")
            return

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
        self._show_progress(100, f"Usunięto {len(deleted_pairs)} plików")
        QMessageBox.information(
            self,
            "Usuwanie zakończone",
            f"Usunięto {len(deleted_pairs)} z {len(self.controller.selected_tiles) + len(deleted_pairs)} zaznaczonych plików.",
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
        self._setup_worker_connections(worker)
        worker.signals.finished.connect(self._on_bulk_move_finished)

        # Uruchom workera
        self._show_progress(0, f"Przenoszenie {count} plików...")
        self.thread_pool.start(worker)

    def _on_bulk_move_finished(self, moved_pairs):
        """
        Slot wywoływany po zakończeniu operacji przenoszenia.

        Args:
            moved_pairs: Lista pomyślnie przeniesionych par plików
        """
        if not moved_pairs:
            self._show_progress(100, "Przenoszenie przerwane lub nieudane")
            return

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

        # Odśwież widok
        self._apply_filters_and_update_view()
        self._save_metadata()

        destination = (
            os.path.dirname(moved_pairs[0].archive_path) if moved_pairs else "nieznany"
        )
        self._show_progress(100, f"Przeniesiono {len(moved_pairs)} plików")

        QMessageBox.information(
            self,
            "Przenoszenie zakończone",
            f"Przeniesiono {len(moved_pairs)} z {len(self.controller.selected_tiles) + len(moved_pairs)} zaznaczonych plików do:\n{destination}",
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
        """
        Obsługuje zmianę liczby gwiazdek dla pary plików.
        """
        logging.info(
            f"⭐ _handle_stars_changed wywołane: {file_pair.get_base_name()} -> {new_star_count} gwiazdek"
        )
        if file_pair:
            file_pair.set_stars(new_star_count)
            self._schedule_metadata_save()
            logging.debug(
                f"Zmieniono liczbę gwiazdek dla "
                f"{file_pair.get_base_name()} na {new_star_count}."
            )

    def _handle_color_tag_changed(self, file_pair: FilePair, new_color_tag: str):
        """
        Obsługuje zmianę tagu koloru dla pary plików.
        """
        logging.info(
            f"🎨 _handle_color_tag_changed wywołane: {file_pair.get_base_name()} -> {new_color_tag}"
        )
        if file_pair:
            file_pair.set_color_tag(new_color_tag)
            self._schedule_metadata_save()
            logging.debug(
                f"Zmieniono tag koloru dla {file_pair.get_base_name()} "
                f"na {new_color_tag}."
            )

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
        """
        Aktualizuje pasek postępu i etykietę postępu.

        Args:
            percent: Wartość postępu (0-100)
            message: Wiadomość do wyświetlenia
        """
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)
        self.progress_bar.setVisible(True)

        # Jeśli osiągnięto 100%, ukryj pasek po krótkim czasie
        if percent >= 100:
            QTimer.singleShot(
                self.app_config.progress_hide_delay_ms, self._hide_progress
            )

    def _hide_progress(self):
        """Ukrywa pasek postępu i resetuje etykietę."""
        self.progress_bar.setVisible(False)
        self.progress_label.setText("Gotowy")

    def _setup_worker_connections(self, worker: UnifiedBaseWorker):
        """
        Konfiguruje połączenia sygnałów dla workera.

        Args:
            worker: Instancja UnifiedBaseWorker do skonfigurowania
        """
        worker.signals.progress.connect(self._show_progress)
        worker.signals.error.connect(self._handle_worker_error)

    def _handle_worker_error(self, error_message: str):
        """
        Obsługuje błędy zgłaszane przez workery.

        Args:
            error_message: Komunikat o błędzie
        """
        QMessageBox.critical(self, "Błąd", error_message)
        self._hide_progress()

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
            self._start_data_processing_worker(scan_result.file_pairs)
        else:
            self._on_tile_loading_finished()

        # UWAGA: update_unpaired_files_lists() jest już wywoływana w _on_tile_loading_finished()
        # Nie wywołujemy tutaj aby uniknąć błędów z niezainicjalizowanymi widgetami

    def confirm_bulk_delete(self, count: int) -> bool:
        """Potwierdza operację bulk delete z użytkownikiem."""
        reply = QMessageBox.question(
            self,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć {count} par plików?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

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
        """Aktualizuje widoczność operacji bulk."""
        self._update_bulk_operations_visibility()

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
        """Żąda zapisu metadanych - używane przez tile widgety."""
        self._schedule_metadata_save()

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
                scan_result = self.controller.scan_service.scan_directory(normalized_path, max_depth=0)
                
                if scan_result.error_message:
                    self.show_error_message("Błąd skanowania", scan_result.error_message)
                    return
                
                # Zaktualizuj stan kontrolera ręcznie
                self.controller.current_directory = normalized_path
                self.controller.current_file_pairs = scan_result.file_pairs
                self.controller.unpaired_archives = scan_result.unpaired_archives
                self.controller.unpaired_previews = scan_result.unpaired_previews
                
                # Utwórz kafelki BEZ resetowania drzewa
                if scan_result.file_pairs:
                    self._start_data_processing_worker_without_tree_reset(scan_result.file_pairs)
                else:
                    # Wywołaj końcowe akcje BEZ init_directory_tree
                    self._finish_folder_change_without_tree_reset()
                
                logging.info(f"Folder change SUCCESS: {normalized_path}, {len(scan_result.file_pairs)} par")
                
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
        if hasattr(self, 'directory_tree_manager'):
            QTimer.singleShot(1000, self.directory_tree_manager.start_background_stats_calculation)

        logging.info(
            f"Widok zaktualizowany bez resetowania drzewa. Wyświetlono po filtracji: "
            f"{len(self.gallery_manager.file_pairs_list)}."
        )
