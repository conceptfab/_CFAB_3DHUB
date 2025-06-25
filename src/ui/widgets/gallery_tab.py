"""
Zakładka galerii - wydzielona z main_window.py.
"""

import concurrent.futures
import logging
import os
import time
import weakref
from functools import wraps
from typing import TYPE_CHECKING

from PyQt6.QtCore import QDir, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.filter_panel import FilterPanel

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


def performance_monitor(operation_name: str):
    """Decorator do monitorowania wydajności operacji UI."""

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            try:
                result = func(self, *args, **kwargs)
                execution_time = time.time() - start_time

                # Log performance metrics
                if execution_time > 0.1:  # Warn if operation takes >100ms
                    logging.warning(
                        f"UI operation '{operation_name}' took {execution_time:.3f}s"
                    )
                else:
                    logging.debug(
                        f"UI operation '{operation_name}' took {execution_time:.3f}s"
                    )

                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logging.error(
                    f"UI operation '{operation_name}' failed after {execution_time:.3f}s: {e}"
                )
                raise

        return wrapper

    return decorator


class FolderValidationWorker(QObject):
    """Worker do asynchronicznej walidacji folderów."""

    validation_finished = pyqtSignal(str, bool, str)  # path, is_valid, error_msg

    def __init__(self):
        super().__init__()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="FolderValidation"
        )

    def validate_folder_async(self, folder_path: str):
        """Asynchroniczna walidacja folderu."""
        future = self._executor.submit(self._validate_folder, folder_path)
        future.add_done_callback(lambda f: self._on_validation_complete(folder_path, f))

    def _validate_folder(self, folder_path: str) -> tuple[bool, str]:
        """Walidacja folderu w worker thread."""
        try:
            if not os.path.exists(folder_path):
                return False, f"Folder nie istnieje: {folder_path}"
            if not os.path.isdir(folder_path):
                return False, f"Ścieżka nie jest folderem: {folder_path}"
            return True, ""
        except Exception as e:
            return False, f"Błąd podczas walidacji: {str(e)}"

    def _on_validation_complete(self, folder_path: str, future):
        """Callback po zakończeniu walidacji."""
        try:
            is_valid, error_msg = future.result()
            self.validation_finished.emit(folder_path, is_valid, error_msg)
        except Exception as e:
            self.validation_finished.emit(
                folder_path, False, f"Błąd walidacji: {str(e)}"
            )


class FilteringWorker(QObject):
    """Worker do asynchronicznego filtrowania z progress feedback."""

    progress_updated = pyqtSignal(int, int)  # current, total
    filtering_finished = pyqtSignal(list)  # filtered_pairs

    def __init__(self):
        super().__init__()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="Filtering"
        )

    def apply_filters_async(self, file_pairs: list, filter_criteria: dict):
        """Asynchroniczne filtrowanie z progress feedback."""
        future = self._executor.submit(
            self._filter_with_progress, file_pairs, filter_criteria
        )
        future.add_done_callback(self._on_filtering_complete)

    def _filter_with_progress(self, file_pairs: list, filter_criteria: dict) -> list:
        """Filtrowanie z progress updates."""
        if not file_pairs:
            return []

        filtered_pairs = []
        total = len(file_pairs)
        batch_size = max(1, total // 20)  # 20 progress updates

        for i, pair in enumerate(file_pairs):
            # Progress update co batch_size elementów
            if i % batch_size == 0:
                self.progress_updated.emit(i, total)

            # Tutaj logika filtrowania - przykład uproszczony
            if self._matches_criteria(pair, filter_criteria):
                filtered_pairs.append(pair)

        self.progress_updated.emit(total, total)  # 100% complete
        return filtered_pairs

    def _matches_criteria(self, pair, criteria) -> bool:
        """Sprawdza czy para spełnia kryteria filtrowania."""
        if not criteria:
            return True

        # Sprawdź gwiazdki
        if "stars" in criteria and criteria["stars"] is not None:
            if getattr(pair, "stars", 0) != criteria["stars"]:
                return False

        # Sprawdź kolor
        if "color" in criteria and criteria["color"] != "ALL":
            pair_color = getattr(pair, "color_tag", None)
            if pair_color != criteria["color"]:
                return False

        return True

    def _on_filtering_complete(self, future):
        """Callback po zakończeniu filtrowania."""
        try:
            filtered_pairs = future.result()
            self.filtering_finished.emit(filtered_pairs)
        except Exception as e:
            logging.error(f"Błąd podczas filtrowania: {e}")
            self.filtering_finished.emit([])


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
        # Użyj weak reference do uniknięcia circular dependencies
        self._main_window_ref = weakref.ref(main_window)

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

        # Dodaj worker do walidacji folderów
        self._folder_validator = FolderValidationWorker()
        self._folder_validator.validation_finished.connect(
            self._on_folder_validation_complete
        )
        self._pending_folder_navigation = None

        # Dodaj worker do filtrowania
        self._filtering_worker = FilteringWorker()
        self._filtering_worker.progress_updated.connect(self._on_filtering_progress)
        self._filtering_worker.filtering_finished.connect(self._on_filtering_finished)
        self._is_filtering = False

        # Performance monitoring cache
        self._ui_cache = {
            "folder_validation": {},
            "layout_geometry": {},
            "widget_states": {},
        }
        self._cache_ttl = 300  # 5 minutes TTL

    @property
    def main_window(self):
        """Zwraca main_window przez weak reference."""
        main_window = self._main_window_ref()
        if main_window is None:
            raise RuntimeError("Main window has been garbage collected")
        return main_window

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
        tiles_layout.setSpacing(20)  # Przerwa między kafelkami 20px
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

        # Dodaj pasek do głównego layoutu
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
        Obsługuje kliknięcie przycisku ulubionego folderu - ASYNC VERSION.

        Args:
            folder_path: Ścieżka do folderu
        """
        logger = logging.getLogger(__name__)
        logger.info(f"Rozpoczęcie asynchronicznej walidacji folderu: {folder_path}")

        # Sprawdź cache walidacji folderów
        is_cached, is_valid, error_msg = self._get_cached_folder_validation(folder_path)
        if is_cached:
            if is_valid:
                self._navigate_to_folder(folder_path)
            else:
                QMessageBox.warning(
                    self.main_window,
                    "Błąd",
                    f"Folder nie jest dostępny:\n{error_msg}",
                )
            return

        # Zapisz pending navigation
        self._pending_folder_navigation = folder_path

        # Rozpocznij asynchroniczną walidację
        self._folder_validator.validate_folder_async(folder_path)

    def _on_folder_validation_complete(
        self, folder_path: str, is_valid: bool, error_msg: str
    ):
        """Callback po zakończeniu walidacji folderu."""
        if folder_path != self._pending_folder_navigation:
            return  # Ignore stale validation results

        self._pending_folder_navigation = None

        # Cache wyniku walidacji
        self._cache_folder_validation(folder_path, is_valid, error_msg)

        if not is_valid:
            QMessageBox.warning(
                self.main_window,
                "Błąd",
                f"Folder nie jest dostępny:\n{error_msg}",
            )
            return

        self._navigate_to_folder(folder_path)

    def _navigate_to_folder(self, folder_path: str):
        """Nawiguje do folderu po udanej walidacji."""
        # Przełącz na zakładkę galerii
        self.main_window.tab_widget.setCurrentIndex(0)

        # Użyj metody set_working_directory
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

    @performance_monitor("update_gallery_view")
    def update_gallery_view(self):
        """
        Aktualizuje widok galerii z performance monitoring.
        """
        if hasattr(self.main_window, "gallery_manager"):
            self.main_window.gallery_manager.update_gallery_view()

    def apply_filters_and_update_view(self):
        """
        Zbiera kryteria, filtruje pary i aktualizuje galerię - ASYNC VERSION.
        """
        # Prevent concurrent filtering
        if self._is_filtering:
            return

        if not self.main_window.controller.current_directory:
            if hasattr(self.main_window, "gallery_manager"):
                self.main_window.gallery_manager.file_pairs_list = []
            self.update_gallery_view()
            if hasattr(self.main_window, "size_control_panel"):
                self.main_window.size_control_panel.setVisible(False)
            if hasattr(self, "filter_panel"):
                self.filter_panel.setEnabled(False)
            return

        if not self.main_window.controller.current_file_pairs:
            if hasattr(self.main_window, "gallery_manager"):
                self.main_window.gallery_manager.file_pairs_list = []
            self.update_gallery_view()
            if hasattr(self.main_window, "size_control_panel"):
                self.main_window.size_control_panel.setVisible(False)
            return

        # Pobierz kryteria filtrowania
        filter_criteria = {}
        if hasattr(self, "filter_panel"):
            filter_criteria = self.filter_panel.get_filter_criteria()

        # Start async filtering
        self._is_filtering = True
        if hasattr(self, "filter_panel"):
            self.filter_panel.setEnabled(False)  # Disable during filtering

        self._filtering_worker.apply_filters_async(
            self.main_window.controller.current_file_pairs, filter_criteria
        )

    def _on_filtering_progress(self, current: int, total: int):
        """Callback dla progress updates podczas filtrowania."""
        # Można dodać progress bar w przyszłości
        progress_percent = (current * 100) // total if total > 0 else 0
        logging.debug(f"Filtering progress: {progress_percent}% ({current}/{total})")

    def _on_filtering_finished(self, filtered_pairs: list):
        """Callback po zakończeniu filtrowania."""
        self._is_filtering = False

        # Update gallery with filtered results
        if hasattr(self.main_window, "gallery_manager"):
            self.main_window.gallery_manager.file_pairs_list = filtered_pairs
            self.main_window.gallery_manager.update_gallery_view()

        # Update UI visibility
        is_gallery_populated = bool(filtered_pairs)
        if hasattr(self.main_window, "size_control_panel"):
            self.main_window.size_control_panel.setVisible(is_gallery_populated)

        if hasattr(self, "filter_panel"):
            self.filter_panel.setEnabled(True)  # Re-enable filter panel

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

        # Cache nowego rozmiaru
        self._ui_cache["widget_states"]["last_thumbnail_size"] = new_size
        self._ui_cache["widget_states"]["last_update_time"] = time.time()

    def _get_cached_folder_validation(self, folder_path: str) -> tuple[bool, str, bool]:
        """
        Sprawdza cache walidacji folderów.

        Returns:
            tuple: (is_cached, is_valid, error_msg)
        """
        cache_key = folder_path
        cache_entry = self._ui_cache["folder_validation"].get(cache_key)

        if cache_entry:
            cached_time, is_valid, error_msg = cache_entry
            if time.time() - cached_time < self._cache_ttl:
                return True, is_valid, error_msg

        return False, False, ""

    def _cache_folder_validation(
        self, folder_path: str, is_valid: bool, error_msg: str
    ):
        """Cache wyniku walidacji folderu."""
        self._ui_cache["folder_validation"][folder_path] = (
            time.time(),
            is_valid,
            error_msg,
        )

    def __del__(self):
        """Cleanup zasobów przy destrukcji."""
        self._cleanup_resources()

    def _cleanup_resources(self):
        """Czyszczenie zasobów i worker threads."""
        try:
            if hasattr(self, "_folder_validator") and self._folder_validator:
                if hasattr(self._folder_validator, "_executor"):
                    self._folder_validator._executor.shutdown(wait=False)

            if hasattr(self, "_filtering_worker") and self._filtering_worker:
                if hasattr(self._filtering_worker, "_executor"):
                    self._filtering_worker._executor.shutdown(wait=False)

            # Clear caches
            if hasattr(self, "_ui_cache"):
                self._ui_cache.clear()

        except Exception as e:
            logging.error(f"Error during GalleryTab cleanup: {e}")
