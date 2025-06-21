# 📝 FRAGMENTY KODU DO POPRAWEK - main_window.py

## 🎯 ETAP 2.1: ELIMINACJA OVER-ENGINEERING

### **2.1.1 USUNIĘCIE MANAGERREGISTRY**

**PLIK:** `src/ui/main_window/main_window.py`  
**LINIE:** 25-46  
**AKCJA:** ZASTĄP

```python
def __init__(self, style_sheet=None):
    """
    Inicjalizuje główne okno aplikacji - uproszczona wersja.
    """
    super().__init__()

    # Podstawowe dane aplikacji
    self.current_directory = ""
    self.file_pairs = []
    self.gallery_tile_widgets = {}
    self.is_scanning = False
    self.thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
    self.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE

    # Logger
    self.logger = get_main_window_logger()

    # App Config
    self.app_config = app_config.AppConfig()

    # Controller - kluczowy dla wielu innych komponentów
    self.controller = MainWindowController(self)

    # Thread coordinator - podstawowy dla wielu operacji
    self.thread_coordinator = ThreadCoordinator()

    # Inicjalizacja UI
    self._init_ui()

    # Połączenia sygnałów
    self._connect_signals()

    self.logger.info("Główne okno aplikacji zostało zainicjalizowane")
```

### **2.1.2 USUNIĘCIE 17 @PROPERTY METOD**

**PLIK:** `src/ui/main_window/main_window.py`  
**LINIE:** 47-151  
**AKCJA:** USUŃ CAŁY BLOK

```python
# USUŃ CAŁY BLOK 17 @property metod (linie 47-151)
# Zastąp prostym lazy loading w miejscach użycia
```

### **2.1.3 DODANIE PROSTEGO LAZY LOADING**

**PLIK:** `src/ui/main_window/main_window.py`  
**LINIE:** Po metodzie `__init__`  
**AKCJA:** DODAJ METODĘ

```python
def _get_manager(self, manager_name: str):
    """
    Prosty lazy loading managerów - zastępuje ManagerRegistry.

    Args:
        manager_name: Nazwa managera do pobrania

    Returns:
        Manager instance
    """
    if not hasattr(self, f"_{manager_name}"):
        # Lazy loading - tworzenie na żądanie
        if manager_name == "gallery_manager":
            from src.ui.gallery_manager import GalleryManager
            self._gallery_manager = GalleryManager(self)
        elif manager_name == "metadata_manager":
            from src.ui.main_window.metadata_manager import MetadataManager
            self._metadata_manager = MetadataManager(self)
        elif manager_name == "progress_manager":
            from src.ui.main_window.progress_manager import ProgressManager
            self._progress_manager = ProgressManager(self)
        elif manager_name == "worker_manager":
            from src.ui.main_window.worker_manager import WorkerManager
            self._worker_manager = WorkerManager(self)
        elif manager_name == "data_manager":
            from src.ui.main_window.data_manager import DataManager
            self._data_manager = DataManager(self)
        elif manager_name == "selection_manager":
            from src.ui.main_window.selection_manager import SelectionManager
            self._selection_manager = SelectionManager(self)
        elif manager_name == "tile_manager":
            from src.ui.main_window.tile_manager import TileManager
            self._tile_manager = TileManager(self)
        elif manager_name == "thumbnail_size_manager":
            from src.ui.main_window.thumbnail_size_manager import ThumbnailSizeManager
            self._thumbnail_size_manager = ThumbnailSizeManager(self)
        else:
            raise ValueError(f"Nieznany manager: {manager_name}")

    return getattr(self, f"_{manager_name}")

# Właściwości dla najczęściej używanych managerów
@property
def gallery_manager(self):
    return self._get_manager("gallery_manager")

@property
def metadata_manager(self):
    return self._get_manager("metadata_manager")

@property
def progress_manager(self):
    return self._get_manager("progress_manager")

@property
def worker_manager(self):
    return self._get_manager("worker_manager")

@property
def data_manager(self):
    return self._get_manager("data_manager")
```

## 🎯 ETAP 2.2: UPROSZCZENIE DELEGACJI

### **2.2.1 ELIMINACJA PROSTYCH DELEGACJI**

**PLIK:** `src/ui/main_window/main_window.py`  
**LINIE:** 206-250  
**AKCJA:** ZASTĄP

```python
def _select_working_directory(self, directory_path=None):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.select_working_directory(directory_path)

def _validate_directory_path(self, path: str) -> bool:
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.validate_directory_path(path)

def _stop_current_scanning(self):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.stop_current_scanning()

def _start_folder_scanning(self, directory_path: str):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.start_folder_scanning(directory_path)

def _on_scan_thread_finished(self):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.on_scan_thread_finished()

def _force_refresh(self):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.force_refresh()

def _clear_all_data_and_views(self):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.clear_all_data_and_views()

def _clear_unpaired_files_lists(self):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.clear_unpaired_files_lists()

def _update_unpaired_files_direct(self):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.update_unpaired_files_direct()

def _handle_scan_finished(self, found_pairs, unpaired_archives, unpaired_previews, special_folders=None):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.handle_scan_finished(found_pairs, unpaired_archives, unpaired_previews, special_folders)

def _handle_scan_error(self, error_message: str):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.handle_scan_error(error_message)
```

### **2.2.2 UPROSZCZENIE METOD UI**

**PLIK:** `src/ui/main_window/main_window.py`  
**LINIE:** 334-468  
**AKCJA:** ZASTĄP

```python
def open_archive(self, file_pair: FilePair):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.open_archive(file_pair)

def _show_preview_dialog(self, file_pair: FilePair):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.show_preview_dialog(file_pair)

def _handle_tile_selection_changed(self, file_pair: FilePair, is_selected: bool):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.handle_tile_selection_changed(file_pair, is_selected)

def _update_bulk_operations_visibility(self):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.update_bulk_operations_visibility()

def _show_file_context_menu(self, file_pair: FilePair, widget: QWidget, position):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.show_file_context_menu(file_pair, widget, position)

def handle_file_drop_on_folder(self, source_file_paths: list[str], target_folder_path: str):
    """Bezpośrednia implementacja - delegacja do controller."""
    return self.controller.handle_file_drop_on_folder(source_file_paths, target_folder_path)
```

## 🎯 ETAP 2.3: OPTYMALIZACJA LOGOWANIA

### **2.3.1 ZMIANA POZIOMÓW LOGÓW**

**PLIK:** `src/ui/main_window/main_window.py`  
**LINIE:** 432-463  
**AKCJA:** ZASTĄP

```python
def _handle_stars_changed(self, file_pair: FilePair, new_star_count: int):
    """Direct implementation - zmiana gwiazdek."""
    self.logger.debug(f"Zmiana gwiazdek: {file_pair.get_base_name()} → {new_star_count}")
    try:
        file_pair.set_stars(new_star_count)
        self._schedule_metadata_save()
    except Exception as e:
        self.logger.error(f"Błąd zmiany gwiazdek: {e}")

def _handle_color_tag_changed(self, file_pair: FilePair, new_color_tag: str):
    """Direct implementation - zmiana tagu koloru."""
    try:
        file_pair.set_color_tag(new_color_tag)
        self._schedule_metadata_save()
    except Exception as e:
        self.logger.error(f"Błąd zmiany tagu koloru: {e}")
```

### **2.3.2 KONSOLIDACJA KOMUNIKATÓW BŁĘDÓW**

**PLIK:** `src/ui/main_window/main_window.py`  
**LINIE:** 511-531  
**AKCJA:** ZASTĄP

```python
def show_error_message(self, title: str, message: str):
    """Wyświetla komunikat błędu - asynchroniczna implementacja."""
    from PyQt6.QtWidgets import QMessageBox
    QTimer.singleShot(0, lambda: QMessageBox.critical(self, title, message))

def show_warning_message(self, title: str, message: str):
    """Wyświetla ostrzeżenie - asynchroniczna implementacja."""
    from PyQt6.QtWidgets import QMessageBox
    QTimer.singleShot(0, lambda: QMessageBox.warning(self, title, message))

def show_info_message(self, title: str, message: str):
    """Wyświetla informację - asynchroniczna implementacja."""
    from PyQt6.QtWidgets import QMessageBox
    QTimer.singleShot(0, lambda: QMessageBox.information(self, title, message))
```

## 🎯 ETAP 2.4: UPROSZCZENIE ARCHITEKTURY

### **2.4.1 UPROSZCZENIE METODY \_INIT_UI**

**PLIK:** `src/ui/main_window/main_window.py`  
**LINIE:** Po metodzie `__init__`  
**AKCJA:** DODAJ METODĘ

```python
def _init_ui(self):
    """Inicjalizuje UI - uproszczona wersja bez Orchestrator."""
    # Inicjalizacja okna
    self.setWindowTitle("CFAB_3DHUB - Menedżer plików 3D")
    self.setGeometry(100, 100, 1200, 800)

    # Centralny widget
    central_widget = QWidget()
    self.setCentralWidget(central_widget)

    # Główny layout
    main_layout = QHBoxLayout(central_widget)
    main_layout.setContentsMargins(5, 5, 5, 5)
    main_layout.setSpacing(5)

    # Drzewo katalogów
    from src.ui.directory_tree.manager import DirectoryTreeManager
    self.folder_tree = DirectoryTreeManager.create_tree_widget()
    self.directory_tree_manager = DirectoryTreeManager(self.folder_tree, self)
    main_layout.addWidget(self.folder_tree, 1)

    # Panel główny
    main_panel = QWidget()
    main_panel_layout = QVBoxLayout(main_panel)
    main_panel_layout.setContentsMargins(0, 0, 0, 0)
    main_panel_layout.setSpacing(5)

    # Tabs
    from src.ui.widgets.gallery_tab import GalleryTab
    from src.ui.widgets.unpaired_files_tab import UnpairedFilesTab
    from src.ui.widgets.file_explorer_tab import FileExplorerTab

    self.tab_widget = QTabWidget()

    # Gallery tab
    self.gallery_tab = GalleryTab(self)
    self.tab_widget.addTab(self.gallery_tab.create_gallery_tab(), "Galeria")

    # Unpaired files tab
    self.unpaired_files_tab = UnpairedFilesTab(self)
    self.tab_widget.addTab(self.unpaired_files_tab.create_unpaired_files_tab(), "Niesparowane pliki")

    # File explorer tab
    self.file_explorer_tab = FileExplorerTab(self)
    self.tab_widget.addTab(self.file_explorer_tab.create_file_explorer_tab(), "Eksplorator plików")

    main_panel_layout.addWidget(self.tab_widget)

    # Progress bar
    from src.ui.main_window.progress_manager import ProgressManager
    self._progress_manager = ProgressManager(self)
    main_panel_layout.addWidget(self._progress_manager.progress_bar)

    main_layout.addWidget(main_panel, 4)

    # File operations UI
    from src.ui.file_operations_ui import FileOperationsUI
    self.file_operations_ui = FileOperationsUI(self)
```

### **2.4.2 UPROSZCZENIE METODY CLOSEEVENT**

**PLIK:** `src/ui/main_window/main_window.py`  
**LINIE:** 190-205  
**AKCJA:** ZASTĄP

```python
def closeEvent(self, event):
    """Obsługuje zamykanie aplikacji - uproszczona wersja."""
    try:
        # Cleanup managerów
        self._cleanup_managers()

        # Zamykanie aplikacji
        event.accept()

    except Exception as e:
        self.logger.error(f"Błąd podczas zamykania aplikacji: {e}")
        event.accept()  # Zawsze akceptuj zamknięcie

def _cleanup_managers(self):
    """Cleanup managerów - uproszczona wersja."""
    managers_to_cleanup = [
        "gallery_manager", "metadata_manager", "progress_manager",
        "worker_manager", "data_manager", "selection_manager",
        "tile_manager", "thumbnail_size_manager"
    ]

    for manager_name in managers_to_cleanup:
        if hasattr(self, f"_{manager_name}"):
            manager = getattr(self, f"_{manager_name}")
            if hasattr(manager, "cleanup"):
                try:
                    manager.cleanup()
                except Exception as e:
                    self.logger.warning(f"Błąd cleanup {manager_name}: {e}")
```

## 🎯 ETAP 2.5: KONSOLIDACJA MANAGERÓW

### **2.5.1 NOWY PLIK: main_window_core.py**

**PLIK:** `src/ui/main_window/main_window_core.py`  
**AKCJA:** UTWÓRZ NOWY PLIK

```python
"""
Główna logika MainWindow - wydzielona z main_window.py.
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class MainWindowCore:
    """Główna logika MainWindow."""

    def __init__(self, main_window: "MainWindow"):
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def init_application(self):
        """Inicjalizuje aplikację - uproszczona wersja."""
        self.logger.info("Inicjalizacja aplikacji...")

        # Podstawowe dane
        self.main_window.current_directory = ""
        self.main_window.file_pairs = []
        self.main_window.gallery_tile_widgets = {}
        self.main_window.is_scanning = False
        self.main_window.thumbnail_size = self.main_window.app_config.DEFAULT_THUMBNAIL_SIZE
        self.main_window.current_thumbnail_size = self.main_window.app_config.DEFAULT_THUMBNAIL_SIZE

        # Inicjalizacja UI
        self._init_ui()

        # Połączenia sygnałów
        self._connect_signals()

        self.logger.info("Aplikacja zainicjalizowana")

    def _init_ui(self):
        """Inicjalizuje UI - delegacja do MainWindow."""
        # Implementacja w MainWindow
        pass

    def _connect_signals(self):
        """Podłącza sygnały - uproszczona wersja."""
        if hasattr(self.main_window, "folder_tree") and hasattr(self.main_window, "gallery_tab"):
            self.main_window.folder_tree.clicked.connect(
                self.main_window.gallery_tab.folder_tree_item_clicked
            )

    def cleanup_application(self):
        """Cleanup aplikacji - uproszczona wersja."""
        self.logger.info("Cleanup aplikacji...")

        # Cleanup managerów
        managers = [
            "gallery_manager", "metadata_manager", "progress_manager",
            "worker_manager", "data_manager", "selection_manager"
        ]

        for manager_name in managers:
            if hasattr(self.main_window, f"_{manager_name}"):
                manager = getattr(self.main_window, f"_{manager_name}")
                if hasattr(manager, "cleanup"):
                    try:
                        manager.cleanup()
                    except Exception as e:
                        self.logger.warning(f"Błąd cleanup {manager_name}: {e}")

        self.logger.info("Cleanup zakończony")

    def show_message(self, title: str, message: str, message_type: str = "info"):
        """Wyświetla komunikat - asynchroniczna implementacja."""
        if message_type == "error":
            QTimer.singleShot(0, lambda: QMessageBox.critical(self.main_window, title, message))
        elif message_type == "warning":
            QTimer.singleShot(0, lambda: QMessageBox.warning(self.main_window, title, message))
        else:
            QTimer.singleShot(0, lambda: QMessageBox.information(self.main_window, title, message))
```

### **2.5.2 NOWY PLIK: main_window_operations.py**

**PLIK:** `src/ui/main_window/main_window_operations.py`  
**AKCJA:** UTWÓRZ NOWY PLIK

```python
"""
Operacje MainWindow - wydzielone z main_window.py.
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow
    from src.models.file_pair import FilePair


class MainWindowOperations:
    """Operacje MainWindow."""

    def __init__(self, main_window: "MainWindow"):
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def handle_stars_changed(self, file_pair: "FilePair", new_star_count: int):
        """Obsługuje zmianę gwiazdek."""
        self.logger.debug(f"Zmiana gwiazdek: {file_pair.get_base_name()} → {new_star_count}")
        try:
            file_pair.set_stars(new_star_count)
            self.main_window._schedule_metadata_save()
        except Exception as e:
            self.logger.error(f"Błąd zmiany gwiazdek: {e}")

    def handle_color_tag_changed(self, file_pair: "FilePair", new_color_tag: str):
        """Obsługuje zmianę tagu koloru."""
        try:
            file_pair.set_color_tag(new_color_tag)
            self.main_window._schedule_metadata_save()
        except Exception as e:
            self.logger.error(f"Błąd zmiany tagu koloru: {e}")

    def perform_bulk_delete(self):
        """Wykonuje masowe usuwanie."""
        if hasattr(self.main_window, "controller") and hasattr(
            self.main_window.controller, "selection_manager"
        ):
            selected_count = len(self.main_window.controller.selection_manager.selected_tiles)
            if selected_count > 0 and self.confirm_bulk_delete(selected_count):
                if hasattr(self.main_window, "file_operations_ui"):
                    self.main_window.file_operations_ui.perform_bulk_delete_operation()

    def confirm_bulk_delete(self, count: int) -> bool:
        """Potwierdza masowe usuwanie."""
        reply = QMessageBox.question(
            self.main_window,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć {count} par plików?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def on_bulk_delete_finished(self, deleted_pairs):
        """Obsługuje zakończenie masowego usuwania."""
        if not deleted_pairs:
            self.main_window._show_progress(100, "Usuwanie przerwane")
            return

        original_count = len(self.main_window.controller.selection_manager.selected_tiles)

        # Background processing
        def update_data():
            for file_pair in deleted_pairs:
                if file_pair in self.main_window.controller.current_file_pairs:
                    self.main_window.controller.current_file_pairs.remove(file_pair)
                self.main_window.controller.selection_manager.selected_tiles.discard(file_pair)

        QTimer.singleShot(0, update_data)
        self.main_window._apply_filters_and_update_view()
        self.main_window._schedule_metadata_save()

        # Pokaż wynik asynchronicznie
        QTimer.singleShot(100, lambda: self._show_delete_result(deleted_pairs, original_count))

    def _show_delete_result(self, deleted_pairs, original_count):
        """Pokazuje wynik usuwania."""
        self.main_window._show_progress(100, f"Usunięto {len(deleted_pairs)} par plików")
        QTimer.singleShot(0, lambda: QMessageBox.information(
            self.main_window,
            "Usuwanie zakończone",
            f"Usunięto {len(deleted_pairs)} z {original_count} par plików.",
        ))
```

### **2.5.3 NOWY PLIK: main_window.py (REFACTORED)**

**PLIK:** `src/ui/main_window/main_window.py`  
**AKCJA:** ZASTĄP CAŁY PLIK

```python
"""
Główne okno aplikacji - zrefaktoryzowana wersja.
"""

from PyQt6.QtCore import QThreadPool, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from src import app_config
from src.models.file_pair import FilePair
from src.services.thread_coordinator import ThreadCoordinator
from src.ui.delegates.workers import UnifiedBaseWorker
from src.ui.main_window.main_window_core import MainWindowCore
from src.ui.main_window.main_window_operations import MainWindowOperations
from src.utils.logging_config import get_main_window_logger


class MainWindow(QMainWindow):
    """Główne okno aplikacji CFAB_3DHUB - zrefaktoryzowana wersja."""

    def __init__(self, style_sheet=None):
        """Inicjalizuje główne okno aplikacji."""
        super().__init__()

        # Logger
        self.logger = get_main_window_logger()

        # App Config
        self.app_config = app_config.AppConfig()

        # Controller
        from src.controllers.main_window_controller import MainWindowController
        self.controller = MainWindowController(self)

        # Thread coordinator
        self.thread_coordinator = ThreadCoordinator()

        # Komponenty
        self.core = MainWindowCore(self)
        self.operations = MainWindowOperations(self)

        # Inicjalizacja aplikacji
        self.core.init_application()

        self.logger.info("Główne okno aplikacji zostało zainicjalizowane")

    # Właściwości dla najczęściej używanych managerów
    @property
    def gallery_manager(self):
        return self._get_manager("gallery_manager")

    @property
    def metadata_manager(self):
        return self._get_manager("metadata_manager")

    @property
    def progress_manager(self):
        return self._get_manager("progress_manager")

    @property
    def worker_manager(self):
        return self._get_manager("worker_manager")

    @property
    def data_manager(self):
        return self._get_manager("data_manager")

    def _get_manager(self, manager_name: str):
        """Prosty lazy loading managerów."""
        if not hasattr(self, f"_{manager_name}"):
            if manager_name == "gallery_manager":
                from src.ui.gallery_manager import GalleryManager
                self._gallery_manager = GalleryManager(self)
            elif manager_name == "metadata_manager":
                from src.ui.main_window.metadata_manager import MetadataManager
                self._metadata_manager = MetadataManager(self)
            elif manager_name == "progress_manager":
                from src.ui.main_window.progress_manager import ProgressManager
                self._progress_manager = ProgressManager(self)
            elif manager_name == "worker_manager":
                from src.ui.main_window.worker_manager import WorkerManager
                self._worker_manager = WorkerManager(self)
            elif manager_name == "data_manager":
                from src.ui.main_window.data_manager import DataManager
                self._data_manager = DataManager(self)
            else:
                raise ValueError(f"Nieznany manager: {manager_name}")

        return getattr(self, f"_{manager_name}")

    def show_preferences(self):
        """Wyświetla okno preferencji."""
        from src.ui.widgets.preferences_dialog import PreferencesDialog
        dialog = PreferencesDialog(self)
        dialog.exec()

    def remove_all_metadata_folders(self):
        """Usuwa wszystkie foldery metadanych."""
        self.data_manager.remove_all_metadata_folders()

    def start_metadata_cleanup_worker(self):
        """Uruchamia worker do czyszczenia metadanych."""
        self.data_manager.start_metadata_cleanup_worker()

    def show_about(self):
        """Wyświetla okno informacji o aplikacji."""
        about_text = (
            "CFAB_3DHUB - Menedżer plików 3D\n"
            "Wersja 2.0\n\n"
            "Aplikacja do zarządzania plikami 3D i ich podglądami."
        )
        QMessageBox.about(self, "O programie CFAB_3DHUB", about_text)

    def closeEvent(self, event):
        """Obsługuje zamykanie aplikacji."""
        try:
            self.core.cleanup_application()
            event.accept()
        except Exception as e:
            self.logger.error(f"Błąd podczas zamykania aplikacji: {e}")
            event.accept()

    # Delegacje do controller
    def _select_working_directory(self, directory_path=None):
        return self.controller.select_working_directory(directory_path)

    def _validate_directory_path(self, path: str) -> bool:
        return self.controller.validate_directory_path(path)

    def _stop_current_scanning(self):
        return self.controller.stop_current_scanning()

    def _start_folder_scanning(self, directory_path: str):
        return self.controller.start_folder_scanning(directory_path)

    def _on_scan_thread_finished(self):
        return self.controller.on_scan_thread_finished()

    def _force_refresh(self):
        return self.controller.force_refresh()

    def _clear_all_data_and_views(self):
        return self.controller.clear_all_data_and_views()

    def _clear_unpaired_files_lists(self):
        return self.controller.clear_unpaired_files_lists()

    def _update_unpaired_files_direct(self):
        return self.controller.update_unpaired_files_direct()

    def _handle_scan_finished(self, found_pairs, unpaired_archives, unpaired_previews, special_folders=None):
        return self.controller.handle_scan_finished(found_pairs, unpaired_archives, unpaired_previews, special_folders)

    def _handle_scan_error(self, error_message: str):
        return self.controller.handle_scan_error(error_message)

    def _apply_filters_and_update_view(self):
        """Aplikuje filtry i odświeża widok - asynchroniczna implementacja."""
        def _async_apply_filters():
            try:
                if hasattr(self, "gallery_tab"):
                    self.gallery_tab.apply_filters_and_update_view()
                elif hasattr(self, "gallery_manager"):
                    all_file_pairs = getattr(self.controller, "current_file_pairs", [])
                    filter_criteria = {}
                    self.gallery_manager.apply_filters_and_update_view(all_file_pairs, filter_criteria)
            except Exception as e:
                self.logger.error(f"Błąd podczas aplikacji filtrów: {e}")

        QTimer.singleShot(0, _async_apply_filters)

    def _update_gallery_view(self):
        """Odświeża widok galerii - asynchroniczna implementacja."""
        def _async_update_gallery():
            try:
                if hasattr(self, "gallery_manager"):
                    self.gallery_manager.update_gallery_view()
            except Exception as e:
                self.logger.error(f"Błąd podczas odświeżania galerii: {e}")

        QTimer.singleShot(0, _async_update_gallery)

    def refresh_all_views(self, new_selection=None):
        """Odświeża wszystkie widoki."""
        return self.controller.refresh_all_views(new_selection)

    def force_full_refresh(self):
        """Wymusza pełne odświeżenie."""
        return self.controller.force_full_refresh()

    def _update_thumbnail_size(self):
        """Aktualizuje rozmiar miniaturek."""
        if hasattr(self, "thumbnail_size_manager"):
            self.thumbnail_size_manager.update_thumbnail_size()

    def resizeEvent(self, event):
        """Obsługuje zmianę rozmiaru okna."""
        return self.controller.on_resize_timer_timeout()

    def _save_metadata(self):
        """Zapisuje metadane."""
        if hasattr(self, "metadata_manager") and self.metadata_manager:
            self.metadata_manager.save_metadata()

    def _schedule_metadata_save(self):
        """Planuje opóźnione zapisanie metadanych."""
        if hasattr(self, "metadata_manager") and self.metadata_manager:
            self.metadata_manager.schedule_metadata_save()

    def _force_immediate_metadata_save(self):
        """Wymusza natychmiastowe zapisanie metadanych."""
        if hasattr(self, "current_directory") and self.current_directory:
            from src.logic.metadata.metadata_core import MetadataManager
            metadata_manager = MetadataManager.get_instance(self.current_directory)
            metadata_manager.force_save()

    def _on_metadata_saved(self, success):
        """Obsługuje zakończenie zapisywania metadanych."""
        if success:
            self.logger.debug("Metadane zostały pomyślnie zapisane")
        else:
            self.logger.warning("Błąd podczas zapisywania metadanych")

    # Delegacje do controller
    def open_archive(self, file_pair: FilePair):
        return self.controller.open_archive(file_pair)

    def _show_preview_dialog(self, file_pair: FilePair):
        return self.controller.show_preview_dialog(file_pair)

    def _handle_tile_selection_changed(self, file_pair: FilePair, is_selected: bool):
        return self.controller.handle_tile_selection_changed(file_pair, is_selected)

    def _update_bulk_operations_visibility(self):
        return self.controller.update_bulk_operations_visibility()

    def _clear_all_selections(self):
        """Czyści wszystkie selekcje."""
        if hasattr(self, "controller") and hasattr(self.controller, "selection_manager"):
            self.controller.selection_manager.selected_tiles.clear()
        if hasattr(self, "gallery_manager"):
            self.gallery_manager.clear_all_selections()

    def _select_all_tiles(self):
        """Zaznacza wszystkie kafelki."""
        if hasattr(self, "gallery_manager"):
            self.gallery_manager.select_all_tiles()

    def _perform_bulk_delete(self):
        """Wykonuje masowe usuwanie."""
        self.operations.perform_bulk_delete()

    def _on_bulk_delete_finished(self, deleted_pairs):
        """Obsługuje zakończenie masowego usuwania."""
        self.operations.on_bulk_delete_finished(deleted_pairs)

    def _perform_bulk_move(self):
        """Wykonuje masowe przenoszenie."""
        return self.controller.perform_bulk_move()

    def _on_bulk_move_finished(self, result):
        """Obsługuje zakończenie masowego przenoszenia."""
        return self.controller.on_bulk_move_finished(result)

    def _refresh_source_folder_after_move(self):
        """Odświeża folder źródłowy po przeniesieniu."""
        return self.controller.refresh_source_folder_after_move()

    def _handle_stars_changed(self, file_pair: FilePair, new_star_count: int):
        """Obsługuje zmianę gwiazdek."""
        self.operations.handle_stars_changed(file_pair, new_star_count)

    def _handle_color_tag_changed(self, file_pair: FilePair, new_color_tag: str):
        """Obsługuje zmianę tagu koloru."""
        self.operations.handle_color_tag_changed(file_pair, new_color_tag)

    # Delegacje do controller
    def _show_file_context_menu(self, file_pair: FilePair, widget: QWidget, position):
        return self.controller.show_file_context_menu(file_pair, widget, position)

    def handle_file_drop_on_folder(self, source_file_paths: list[str], target_folder_path: str):
        return self.controller.handle_file_drop_on_folder(source_file_paths, target_folder_path)

    def _show_progress(self, percent: int, message: str):
        """Wyświetla progress bar."""
        if hasattr(self, "progress_manager"):
            self.progress_manager.show_progress(percent, message)

    def _hide_progress(self):
        """Ukrywa progress bar."""
        if hasattr(self, "progress_manager"):
            self.progress_manager.hide_progress()

    def _setup_worker_connections(self, worker: UnifiedBaseWorker):
        """Konfiguruje połączenia sygnałów dla workera."""
        worker.signals.progress.connect(self._show_progress)
        worker.signals.error.connect(self._handle_worker_error)

    def _handle_worker_error(self, error_message: str):
        """Obsługuje błędy workera."""
        return self.controller.handle_worker_error(error_message)

    def _show_detailed_move_report(self, moved_pairs, detailed_errors, skipped_files, summary):
        """Pokazuje szczegółowy raport przeniesienia."""
        return self.controller.show_detailed_move_report(moved_pairs, detailed_errors, skipped_files, summary)

    def show_error_message(self, title: str, message: str):
        """Wyświetla komunikat błędu."""
        self.core.show_message(title, message, "error")

    def show_warning_message(self, title: str, message: str):
        """Wyświetla ostrzeżenie."""
        self.core.show_message(title, message, "warning")

    def show_info_message(self, title: str, message: str):
        """Wyświetla informację."""
        self.core.show_message(title, message, "info")

    def update_scan_results(self, scan_result):
        """Aktualizuje wyniki skanowania."""
        return self.controller.update_scan_results(scan_result)

    def confirm_bulk_delete(self, count: int) -> bool:
        """Potwierdza masowe usuwanie."""
        return self.operations.confirm_bulk_delete(count)

    def update_after_bulk_operation(self, processed_pairs, operation_name: str):
        """Aktualizuje widok po operacji masowej."""
        self._apply_filters_and_update_view()
        self._schedule_metadata_save()

        message = f"Zakończono {operation_name}: {len(processed_pairs)} par plików"
        QTimer.singleShot(100, lambda: self.show_info_message("Operacja zakończona", message))

    def update_bulk_operations_visibility(self, selected_count: int):
        """Aktualizuje widoczność przycisków masowych."""
        if hasattr(self, "controller"):
            self.controller.update_bulk_operations_visibility(selected_count)

    def add_new_pair(self, new_pair):
        """Dodaje nową parę."""
        return self.controller.add_new_pair(new_pair)

    def update_unpaired_lists(self, archives, previews):
        """Aktualizuje listy niesparowanych plików."""
        return self.controller.update_unpaired_lists(archives, previews)

    def request_metadata_save(self):
        """Żąda zapisania metadanych."""
        return self.controller.request_metadata_save()

    def change_directory(self, folder_path: str):
        """Zmienia katalog."""
        return self.controller.change_directory(folder_path)

    def _finish_folder_change_without_tree_reset(self):
        """Kończy zmianę folderu bez resetu drzewa."""
        return self.controller.finish_folder_change_without_tree_reset()

    def on_explorer_folder_changed(self, path: str):
        """Obsługuje zmianę folderu w eksploratorze."""
        return self.controller.on_explorer_folder_changed(path)

    def on_explorer_file_selected(self, file_path: str):
        """Obsługuje wybór pliku w eksploratorze."""
        return self.controller.on_explorer_file_selected(file_path)

    def set_working_directory(self, directory: str):
        """Ustawia katalog roboczy."""
        return self.controller.set_working_directory(directory)

    def _on_resize_timer_timeout(self):
        """Obsługuje timeout timera resize."""
        return self.controller.on_resize_timer_timeout()

    def _on_tile_data_processed(self, processed_pairs):
        """Obsługuje przetworzenie danych kafelków."""
        if hasattr(self, "tile_manager"):
            self.tile_manager.on_tile_loading_finished()

    def _on_tile_loading_finished(self):
        """Obsługuje zakończenie ładowania kafelków."""
        if hasattr(self, "tile_manager"):
            self.tile_manager.on_tile_loading_finished()
```

---

## ✅ CHECKLISTA IMPLEMENTACJI

### **ETAP 2.1: Eliminacja over-engineering**

- [ ] Usunięcie ManagerRegistry
- [ ] Usunięcie MainWindowOrchestrator
- [ ] Konsolidacja managerów
- [ ] Redukcja plików w katalogu main_window

### **ETAP 2.2: Uproszczenie delegacji**

- [ ] Eliminacja 17 @property metod delegacji
- [ ] Bezpośrednie implementacje prostych operacji
- [ ] Zachowanie delegacji tylko dla złożonych operacji

### **ETAP 2.3: Optymalizacja logowania**

- [ ] Zmiana INFO → DEBUG dla operacji rutynowych
- [ ] Usunięcie nadmiarowych logów
- [ ] Konsolidacja komunikatów błędów

### **ETAP 2.4: Uproszczenie architektury**

- [ ] Redukcja zależności
- [ ] Eliminacja fallback code
- [ ] Uproszczenie sprawdzeń hasattr()

### **ETAP 2.5: Testy**

- [ ] Test funkcjonalności podstawowej
- [ ] Test integracji
- [ ] Test wydajności
- [ ] Test regresyjny

---

**STATUS:** 🔄 **GOTOWY DO IMPLEMENTACJI** - Wszystkie fragmenty kodu przygotowane.
