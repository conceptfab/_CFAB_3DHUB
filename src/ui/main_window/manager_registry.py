"""
ManagerRegistry - centralny rejestr managerów MainWindow.
🚀 ETAP 2 REFAKTORYZACJI: Zastąpienie 17 @property managerów z main_window.py

Odpowiedzialności:
- Lazy loading wszystkich managerów MainWindow
- Walidacja dependencies przed tworzeniem managerów
- Lifecycle management i cleanup
- Centralna konfiguracja managerów
"""

from typing import Any, Dict, Optional, Type

from src.utils.logging_config import get_main_window_logger


class ManagerRegistry:
    """
    Centralny rejestr managerów - zastępuje 17 @property w MainWindow.
    Implementuje lazy loading i lifecycle management.

    ELIMINUJE Z MAIN_WINDOW:
    - 17 @property metod dla managerów (~170 linii)
    - Rozproszoną logikę lazy loading
    - Duplikację patterns tworzenia managerów
    - Problemy z dependencies validation
    """

    def __init__(self, main_window):
        """
        Inicjalizuje ManagerRegistry.

        Args:
            main_window: Referencja do instancji MainWindow
        """
        self.main_window = main_window
        self.logger = get_main_window_logger()

        # Cache loaded managerów
        self._managers: Dict[str, Any] = {}

        # Konfiguracja managerów z dependencies
        self._manager_configs = self._initialize_manager_configs()

        self.logger.debug("ManagerRegistry zainicjalizowany")

    def _initialize_manager_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Inicjalizuje konfigurację wszystkich managerów.

        Returns:
            Dict[str, Dict[str, Any]]: Konfiguracja managerów
        """
        return {
            # UI and Window Management
            "interface": {
                "module": "src.ui.main_window.main_window_interface",
                "class_name": "MainWindowInterface",
                "dependencies": [],
                "special_init": self._init_interface,
            },
            "window_initialization_manager": {
                "module": "src.ui.main_window.window_initialization_manager",
                "class_name": "WindowInitializationManager",
                "dependencies": [],
            },
            "ui_manager": {
                "module": "src.ui.main_window.ui_manager",
                "class_name": "UIManager",
                "dependencies": [],
            },
            "tabs_manager": {
                "module": "src.ui.main_window.tabs_manager",
                "class_name": "TabsManager",
                "dependencies": [],
            },
            # Gallery and Content Management
            "gallery_manager": {
                "module": "src.ui.gallery_manager",
                "class_name": "GalleryManager",
                "dependencies": ["tiles_container", "tiles_layout", "scroll_area"],
                "special_init": self._init_gallery_manager,
            },
            "metadata_manager": {
                "module": "src.ui.main_window.metadata_manager",
                "class_name": "MetadataManager",
                "dependencies": [],
            },
            "tile_manager": {
                "module": "src.ui.main_window.tile_manager",
                "class_name": "TileManager",
                "dependencies": [],
            },
            # Progress and Size Management
            "progress_manager": {
                "module": "src.ui.main_window.progress_manager",
                "class_name": "ProgressManager",
                "dependencies": [],
            },
            "thumbnail_size_manager": {
                "module": "src.ui.main_window.thumbnail_size_manager",
                "class_name": "ThumbnailSizeManager",
                "dependencies": [],
            },
            # Scanning and Results
            "scan_results_handler": {
                "module": "src.ui.main_window.scan_results_handler",
                "class_name": "ScanResultsHandler",
                "dependencies": [],
            },
            "scan_manager": {
                "module": "src.ui.main_window.scan_manager",
                "class_name": "ScanManager",
                "dependencies": [],
            },
            "worker_manager": {
                "module": "src.ui.main_window.worker_manager",
                "class_name": "WorkerManager",
                "dependencies": [],
            },
            # Data and Selection Management
            "data_manager": {
                "module": "src.ui.main_window.data_manager",
                "class_name": "DataManager",
                "dependencies": [],
                "special_init": self._init_data_manager_singleton,
            },
            "selection_manager": {
                "module": "src.ui.main_window.selection_manager",
                "class_name": "SelectionManager",
                "dependencies": [],
            },
            # Operations Management
            "bulk_operations_manager": {
                "module": "src.ui.main_window.bulk_operations_manager",
                "class_name": "BulkOperationsManager",
                "dependencies": [],
            },
            "bulk_move_operations_manager": {
                "module": "src.ui.main_window.bulk_move_operations_manager",
                "class_name": "BulkMoveOperationsManager",
                "dependencies": [],
            },
            "file_operations_handler": {
                "module": "src.ui.main_window.file_operations_handler",
                "class_name": "FileOperationsHandler",
                "dependencies": [],
            },
            "file_operations_coordinator": {
                "module": "src.ui.main_window.file_operations_coordinator",
                "class_name": "FileOperationsCoordinator",
                "dependencies": [],
            },
            # Dialog and Interface Management
            "dialog_manager": {
                "module": "src.ui.main_window.dialog_manager",
                "class_name": "DialogManager",
                "dependencies": [],
            },
            "controller_interface_manager": {
                "module": "src.ui.main_window.controller_interface_manager",
                "class_name": "ControllerInterfaceManager",
                "dependencies": [],
            },
            "event_handler": {
                "module": "src.ui.main_window.event_handler",
                "class_name": "EventHandler",
                "dependencies": [],
            },
        }

    def get_manager(self, manager_name: str) -> Any:
        """
        Lazy loading managera z walidacją dependencies.
        Zastępuje wszystkie @property metody z MainWindow.

        Args:
            manager_name: Nazwa managera do pobrania

        Returns:
            Any: Instancja managera

        Raises:
            ValueError: Jeśli manager_name jest nieznany
            RuntimeError: Jeśli dependencies nie są spełnione
        """
        # Sprawdź czy manager już istnieje
        if manager_name in self._managers:
            return self._managers[manager_name]

        # Sprawdź czy manager jest w konfiguracji
        if manager_name not in self._manager_configs:
            raise ValueError(f"Nieznany manager: {manager_name}")

        config = self._manager_configs[manager_name]

        # Walidacja dependencies
        self._validate_dependencies(manager_name, config.get("dependencies", []))

        # Tworzenie managera
        manager = self._create_manager(manager_name, config)

        # Cache managera
        self._managers[manager_name] = manager

        self.logger.debug(f"✅ Manager '{manager_name}' utworzony i cache'owany")
        return manager

    def _validate_dependencies(self, manager_name: str, dependencies: list):
        """
        Waliduje czy wszystkie dependencies są dostępne.

        Args:
            manager_name: Nazwa managera
            dependencies: Lista wymaganych dependencies

        Raises:
            RuntimeError: Jeśli dependencies nie są spełnione
        """
        if not dependencies:
            return

        missing = []
        for dep in dependencies:
            if not hasattr(self.main_window, dep):
                missing.append(dep)

        if missing:
            raise RuntimeError(f"{manager_name} wymaga: {', '.join(missing)}")

    def _create_manager(self, manager_name: str, config: Dict[str, Any]) -> Any:
        """
        Tworzy instancję managera na podstawie konfiguracji.

        Args:
            manager_name: Nazwa managera
            config: Konfiguracja managera

        Returns:
            Any: Nowa instancja managera
        """
        # Sprawdź czy jest specjalna metoda inicjalizacji
        if "special_init" in config:
            return config["special_init"](manager_name, config)

        # Standardowa inicjalizacja
        module_name = config["module"]
        class_name = config["class_name"]

        # Dynamiczny import modułu
        module = __import__(module_name, fromlist=[class_name])
        manager_class = getattr(module, class_name)

        # Tworzenie instancji z main_window jako argumentem
        return manager_class(self.main_window)

    def _init_interface(self, manager_name: str, config: Dict[str, Any]) -> Any:
        """Specjalna inicjalizacja dla interface managera."""
        from src.ui.main_window.main_window_interface import MainWindowInterface

        return MainWindowInterface(self.main_window)

    def _init_gallery_manager(self, manager_name: str, config: Dict[str, Any]) -> Any:
        """Specjalna inicjalizacja dla GalleryManager z dependencies."""
        from src.ui.gallery_manager import GalleryManager

        return GalleryManager(
            self.main_window,
            self.main_window.tiles_container,
            self.main_window.tiles_layout,
            self.main_window.scroll_area,
        )

    def _init_data_manager_singleton(
        self, manager_name: str, config: Dict[str, Any]
    ) -> Any:
        """Specjalna inicjalizacja dla DataManager z singleton pattern."""
        # Sprawdź czy DataManager już istnieje w starym registry
        if (
            hasattr(self.main_window, "_manager_registry")
            and "data_manager" in self.main_window._manager_registry
        ):
            return self.main_window._manager_registry["data_manager"]

        # Stwórz nowy DataManager
        from src.ui.main_window.data_manager import DataManager

        data_manager = DataManager(self.main_window)

        # Dodaj do starego registry dla backward compatibility
        if not hasattr(self.main_window, "_manager_registry"):
            self.main_window._manager_registry = {}
        self.main_window._manager_registry["data_manager"] = data_manager

        return data_manager

    def has_manager(self, manager_name: str) -> bool:
        """
        Sprawdza czy manager został już załadowany.

        Args:
            manager_name: Nazwa managera

        Returns:
            bool: True jeśli manager został załadowany
        """
        return manager_name in self._managers

    def get_loaded_managers_count(self) -> int:
        """
        Zwraca liczbę załadowanych managerów.

        Returns:
            int: Liczba załadowanych managerów
        """
        return len(self._managers)

    def get_all_manager_names(self) -> list:
        """
        Zwraca listę wszystkich dostępnych managerów.

        Returns:
            list: Lista nazw managerów
        """
        return list(self._manager_configs.keys())

    def cleanup_managers(self):
        """Cleanup wszystkich managerów przy zamykaniu aplikacji."""
        self.logger.info("🔄 Rozpoczynam cleanup managerów...")

        for name, manager in self._managers.items():
            if hasattr(manager, "cleanup"):
                try:
                    manager.cleanup()
                    self.logger.debug(f"✅ Cleanup manager {name}")
                except Exception as e:
                    self.logger.error(f"❌ Błąd cleanup manager {name}: {e}")

        # Wyczyść cache
        self._managers.clear()
        self.logger.info("✅ Cleanup managerów ukończony")

    def get_registry_status(self) -> Dict[str, Any]:
        """
        Zwraca status registry managerów.

        Returns:
            Dict[str, Any]: Status registry
        """
        return {
            "total_managers": len(self._manager_configs),
            "loaded_managers": len(self._managers),
            "loaded_manager_names": list(self._managers.keys()),
            "available_managers": list(self._manager_configs.keys()),
        }
