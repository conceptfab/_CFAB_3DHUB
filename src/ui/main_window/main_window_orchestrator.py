"""
MainWindowOrchestrator - centralne zarządzanie głównym oknem.
🚀 ETAP 2 REFAKTORYZACJI: Wydzielenie logiki koordynacji z main_window.py

Odpowiedzialności:
- Koordynacja sekwencji inicjalizacji
- Zarządzanie lifecycle aplikacji
- Centralne zarządzanie managerami
- Obsługa shutdown i cleanup
"""

from typing import Any, Dict

from src import app_config
from src.controllers.main_window_controller import MainWindowController
from src.services.thread_coordinator import ThreadCoordinator
from src.utils.logging_config import get_main_window_logger


class MainWindowOrchestrator:
    """
    Centralny orchestrator dla MainWindow.
    Zastępuje rozproszenie logiki inicjalizacji i koordynacji w main_window.py.

    ELIMINUJE Z MAIN_WINDOW:
    - Sekwencję inicjalizacji z __init__
    - Część metod _init_data, _init_managers
    - Koordynację między managerami (~50-80 linii)
    """

    def __init__(self, main_window):
        """
        Inicjalizuje orchestrator z referencją do głównego okna.

        Args:
            main_window: Referencja do instancji MainWindow
        """
        self.main_window = main_window
        self.logger = get_main_window_logger()

        # State tracking
        self._initialization_complete = False
        self._shutdown_in_progress = False

        # Core components cache
        self._core_components = {}

        self.logger.debug("MainWindowOrchestrator zainicjalizowany")

    def initialize_application(self) -> bool:
        """
        Główna sekwencja inicjalizacji aplikacji.
        Zastępuje rozproszoną logikę z main_window.__init__

        Returns:
            bool: True jeśli inicjalizacja przebiegła pomyślnie
        """
        try:
            self.logger.info(
                "🚀 Rozpoczynam inicjalizację aplikacji przez Orchestrator"
            )

            # ETAP 1: Podstawowe dane aplikacji
            self._initialize_core_data()

            # ETAP 2: Podstawowe komponenty
            self._initialize_core_components()

            # ETAP 3: Window i UI (delegacja)
            self._initialize_window_and_ui()

            # ETAP 4: Managery podstawowe
            self._initialize_essential_managers()

            # ETAP 5: Finalizacja
            self._finalize_initialization()

            self._initialization_complete = True
            self.logger.info("✅ Inicjalizacja aplikacji ukończona pomyślnie")
            return True

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas inicjalizacji aplikacji: {e}")
            import traceback

            self.logger.error(f"Stack trace: {traceback.format_exc()}")
            return False

    def _initialize_core_data(self):
        """Inicjalizuje podstawowe dane aplikacji."""
        self.logger.debug("Inicjalizacja podstawowych danych...")

        # Dane aplikacji - przeniesione z _init_data
        self.main_window.current_directory = ""
        self.main_window.file_pairs = []
        self.main_window.gallery_tile_widgets = {}
        self.main_window.is_scanning = False
        # NIE ustawiamy thumbnail_size ani current_thumbnail_size tutaj!

        # Flags dla lazy loading
        self.main_window._managers_initialized = False
        self.main_window._core_managers_cache = {}

        self.logger.debug("✅ Podstawowe dane zainicjalizowane")

    def _initialize_core_components(self):
        """Inicjalizuje kluczowe komponenty systemowe."""
        self.logger.debug("Inicjalizacja kluczowych komponentów...")

        # Logger
        self.main_window.logger = get_main_window_logger()
        self._core_components["logger"] = self.main_window.logger

        # App Config
        self.main_window.app_config = app_config.AppConfig()
        self._core_components["app_config"] = self.main_window.app_config

        # Inicjalizacja rozmiaru miniaturek po utworzeniu app_config
        user_default_size = self.main_window.app_config.get("default_thumbnail_size")
        try:
            validated_size = int(user_default_size) if user_default_size is not None else None
        except (ValueError, TypeError):
            validated_size = None

        if validated_size is not None and 20 <= validated_size <= 2000:
            self.main_window.thumbnail_size = validated_size
            self.main_window.current_thumbnail_size = validated_size
            self.logger.info(f"Inicjalizacja z default_thumbnail_size z konfiguracji: {validated_size}px")
        else:
            self.main_window.thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
            self.main_window.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
            self.logger.info(f"Inicjalizacja z domyślnej stałej: {app_config.DEFAULT_THUMBNAIL_SIZE}px")

        # Controller - kluczowy dla wielu innych komponentów
        self.main_window.controller = MainWindowController(self.main_window)
        self._core_components["controller"] = self.main_window.controller

        # Interface delegacji - lazy
        self.main_window._interface = None

        self.logger.debug("✅ Kluczowe komponenty zainicjalizowane")

    def _initialize_window_and_ui(self):
        """Deleguje inicjalizację okna i UI do UIInitializer."""
        self.logger.debug("Inicjalizacja okna i UI...")

        # ETAP 2.2: Delegacja do UIInitializer
        from src.ui.main_window.ui_initializer import UIInitializer

        ui_initializer = UIInitializer(self.main_window)

        # Inicjalizacja okna
        ui_initializer.init_window()

        # Inicjalizacja komponentów UI
        ui_initializer.init_ui_components()

        # Cache UIInitializer dla późniejszego użycia
        self._core_components["ui_initializer"] = ui_initializer

        self.logger.debug("✅ Okno i UI zainicjalizowane przez UIInitializer")

    def _initialize_essential_managers(self):
        """Inicjalizuje tylko niezbędne managery (nie lazy-loaded)."""
        self.logger.debug("Inicjalizacja niezbędnych managerów...")

        # Thread coordinator - podstawowy dla wielu operacji
        self.main_window.thread_coordinator = ThreadCoordinator()
        self._core_components["thread_coordinator"] = (
            self.main_window.thread_coordinator
        )

        # DirectoryTreeManager - wymaga folder_tree z UI
        from src.ui.directory_tree.manager import DirectoryTreeManager

        self.main_window.directory_tree_manager = DirectoryTreeManager(
            self.main_window.folder_tree, self.main_window
        )
        self._core_components["directory_tree_manager"] = (
            self.main_window.directory_tree_manager
        )

        # File Operations UI - używane przez wiele komponentów
        from src.ui.file_operations_ui import FileOperationsUI

        self.main_window.file_operations_ui = FileOperationsUI(self.main_window)
        self._core_components["file_operations_ui"] = (
            self.main_window.file_operations_ui
        )

        self.logger.debug("✅ Niezbędne managery zainicjalizowane")

    def _finalize_initialization(self):
        """Finalizuje inicjalizację - połączenia sygnałów i konfiguracja."""
        self.logger.debug("Finalizacja inicjalizacji...")

        # ETAP 2.2: Użyj UIInitializer dla expand/collapse buttons
        if "ui_initializer" in self._core_components:
            self._core_components["ui_initializer"].init_expand_collapse_buttons()

        # Połączenia sygnałów
        self.main_window._connect_signals()

        # WindowInitializationManager - preferencje i default folder
        self.main_window.window_initialization_manager.show_preferences_loaded_confirmation()
        self.main_window.window_initialization_manager.initialize_default_folder()

        self.logger.debug("✅ Finalizacja zakończona")

    def coordinate_managers(self) -> Dict[str, Any]:
        """
        Koordynuje współpracę między managerami.

        Returns:
            Dict[str, Any]: Status koordinacji managerów
        """
        if not self._initialization_complete:
            self.logger.warning("⚠️ Próba koordynacji przed ukończeniem inicjalizacji")
            return {"status": "not_initialized"}

        status = {
            "core_components": len(self._core_components),
            "lazy_managers_loaded": self._count_loaded_lazy_managers(),
            "coordination_active": True,
        }

        self.logger.debug(f"Koordynacja managerów: {status}")
        return status

    def _count_loaded_lazy_managers(self) -> int:
        """Liczy ile lazy managerów zostało już załadowanych."""
        count = 0
        lazy_managers = [
            "interface",
            "window_initialization_manager",
            "ui_manager",
            "tabs_manager",
            "gallery_manager",
            "metadata_manager",
            "progress_manager",
            "thumbnail_size_manager",
            "tile_manager",
            "scan_results_handler",
            "scan_manager",
            "worker_manager",
            "data_manager",
            "selection_manager",
            "bulk_operations_manager",
        ]

        for manager_name in lazy_managers:
            private_name = f"_{manager_name}"
            if hasattr(self.main_window, private_name):
                count += 1

        return count

    def handle_shutdown(self):
        """
        Obsługuje bezpieczne zamykanie aplikacji.
        Cleanup wszystkich zasobów i managerów.
        """
        if self._shutdown_in_progress:
            self.logger.warning("⚠️ Shutdown już w trakcie")
            return

        self._shutdown_in_progress = True
        self.logger.info("🔄 Rozpoczynam shutdown aplikacji...")

        try:
            # Cleanup core components
            for name, component in self._core_components.items():
                if hasattr(component, "cleanup"):
                    try:
                        component.cleanup()
                        self.logger.debug(f"✅ Cleanup {name}")
                    except Exception as e:
                        self.logger.error(f"❌ Błąd cleanup {name}: {e}")

            # Cleanup lazy managers
            self._cleanup_lazy_managers()

            # Clear caches
            self._core_components.clear()
            if hasattr(self.main_window, "_manager_registry"):
                self.main_window._manager_registry.clear()

            self.logger.info("✅ Shutdown ukończony pomyślnie")

        except Exception as e:
            self.logger.error(f"❌ Błąd podczas shutdown: {e}")

    def _cleanup_lazy_managers(self):
        """Cleanup lazy-loaded managerów."""
        lazy_managers = [
            "_interface",
            "_window_initialization_manager",
            "_ui_manager",
            "_tabs_manager",
            "_gallery_manager",
            "_metadata_manager",
            "_progress_manager",
            "_thumbnail_size_manager",
            "_tile_manager",
            "_scan_results_handler",
            "_scan_manager",
            "_worker_manager",
            "_data_manager",
            "_selection_manager",
            "_bulk_operations_manager",
        ]

        for manager_attr in lazy_managers:
            if hasattr(self.main_window, manager_attr):
                manager = getattr(self.main_window, manager_attr)
                if hasattr(manager, "cleanup"):
                    try:
                        manager.cleanup()
                        self.logger.debug(f"✅ Cleanup lazy manager {manager_attr}")
                    except Exception as e:
                        self.logger.error(
                            f"❌ Błąd cleanup lazy manager {manager_attr}: {e}"
                        )

    def get_initialization_status(self) -> Dict[str, Any]:
        """
        Zwraca status inicjalizacji aplikacji.

        Returns:
            Dict[str, Any]: Szczegółowy status inicjalizacji
        """
        return {
            "initialization_complete": self._initialization_complete,
            "shutdown_in_progress": self._shutdown_in_progress,
            "core_components_count": len(self._core_components),
            "lazy_managers_loaded": self._count_loaded_lazy_managers(),
        }
