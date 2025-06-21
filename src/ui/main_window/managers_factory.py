"""
Managers Factory - fabryka do tworzenia managerów MainWindow.
Wydzielona z MainWindow dla lepszej organizacji i testowania.
"""

from src import app_config
from src.controllers.main_window_controller import MainWindowController
from src.services.thread_coordinator import ThreadCoordinator
from src.ui.directory_tree.manager import DirectoryTreeManager
from src.ui.file_operations_ui import FileOperationsUI
from src.ui.gallery_manager import GalleryManager
from src.ui.main_window.bulk_move_operations_manager import BulkMoveOperationsManager
from src.ui.main_window.bulk_operations_manager import BulkOperationsManager
from src.ui.main_window.controller_interface_manager import ControllerInterfaceManager
from src.ui.main_window.data_manager import DataManager
from src.ui.main_window.dialog_manager import DialogManager
from src.ui.main_window.event_handler import EventHandler
from src.ui.main_window.file_operations_coordinator import FileOperationsCoordinator
from src.ui.main_window.file_operations_handler import FileOperationsHandler
from src.ui.main_window.metadata_manager import MetadataManager
from src.ui.main_window.progress_manager import ProgressManager
from src.ui.main_window.scan_manager import ScanManager
from src.ui.main_window.scan_results_handler import ScanResultsHandler
from src.ui.main_window.selection_manager import SelectionManager
from src.ui.main_window.tabs_manager import TabsManager
from src.ui.main_window.thumbnail_size_manager import ThumbnailSizeManager
from src.ui.main_window.tile_manager import TileManager
from src.ui.main_window.ui_manager import UIManager
from src.ui.main_window.window_initialization_manager import WindowInitializationManager
from src.ui.main_window.worker_manager import WorkerManager
from src.ui.main_window_components.event_bus import get_event_bus
from src.ui.main_window_components.view_refresh_manager import ViewRefreshManager
from src.utils.logging_config import get_main_window_logger


class ManagersFactory:
    """
    Factory pattern dla tworzenia managerów MainWindow.
    Organizuje inicjalizację w logiczne grupy.
    """

    @staticmethod
    def create_core_managers(main_window):
        """
        Tworzy podstawowe managery wymagane do inicjalizacji.

        Args:
            main_window: Referencja do głównego okna aplikacji

        Returns:
            dict: Słownik z podstawowymi managerami
        """
        return {
            "logger": get_main_window_logger(),
            "app_config": app_config.AppConfig(),
            "event_bus": get_event_bus(),
            "controller": MainWindowController(main_window),
            "thread_coordinator": ThreadCoordinator(),
        }

    @staticmethod
    def create_ui_managers(main_window):
        """
        Tworzy managery UI po inicjalizacji podstawowych komponentów.

        Args:
            main_window: Referencja do głównego okna aplikacji

        Returns:
            dict: Słownik z managerami UI
        """
        return {
            "ui_manager": UIManager(main_window),
            "progress_manager": ProgressManager(main_window),
            "worker_manager": WorkerManager(main_window),
            "event_handler": EventHandler(main_window),
            "dialog_manager": DialogManager(main_window),
            "tabs_manager": TabsManager(main_window),
            "window_initialization_manager": WindowInitializationManager(main_window),
        }

    @staticmethod
    def create_operation_managers(main_window):
        """
        Tworzy managery operacji biznesowych.

        Args:
            main_window: Referencja do głównego okna aplikacji

        Returns:
            dict: Słownik z managerami operacji
        """
        return {
            "data_manager": DataManager(main_window),
            "scan_manager": ScanManager(main_window),
            "metadata_manager": MetadataManager(main_window),
            "selection_manager": SelectionManager(main_window),
            "bulk_operations_manager": BulkOperationsManager(main_window),
            "bulk_move_operations_manager": BulkMoveOperationsManager(main_window),
            "file_operations_coordinator": FileOperationsCoordinator(main_window),
            "file_operations_handler": FileOperationsHandler(main_window),
            "scan_results_handler": ScanResultsHandler(main_window),
            "thumbnail_size_manager": ThumbnailSizeManager(main_window),
            "tile_manager": TileManager(main_window),
            "controller_interface_manager": ControllerInterfaceManager(main_window),
        }

    @staticmethod
    def create_specialized_managers(main_window):
        """
        Tworzy wyspecjalizowane managery które wymagają już zainicjalizowanych UI.

        Args:
            main_window: Referencja do głównego okna aplikacji

        Returns:
            dict: Słownik z wyspecjalizowanymi managerami
        """
        return {
            "view_refresh_manager": ViewRefreshManager(main_window),
            "directory_tree_manager": DirectoryTreeManager(
                main_window.folder_tree, main_window
            ),
            "gallery_manager": GalleryManager(
                main_window,
                main_window.tiles_container,
                main_window.tiles_layout,
                main_window.scroll_area,
            ),
            "file_operations_ui": FileOperationsUI(main_window),
        }

    @staticmethod
    def initialize_all_managers(main_window):
        """
        Inicjalizuje wszystkie managery w odpowiedniej kolejności.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        # Core managers (podstawowe)
        core_managers = ManagersFactory.create_core_managers(main_window)
        for name, manager in core_managers.items():
            setattr(main_window, name, manager)

        # UI managers
        ui_managers = ManagersFactory.create_ui_managers(main_window)
        for name, manager in ui_managers.items():
            setattr(main_window, name, manager)

        # Operation managers
        operation_managers = ManagersFactory.create_operation_managers(main_window)
        for name, manager in operation_managers.items():
            setattr(main_window, name, manager)

    @staticmethod
    def initialize_specialized_managers_after_ui(main_window):
        """
        Inicjalizuje wyspecjalizowane managery po utworzeniu UI.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        specialized_managers = ManagersFactory.create_specialized_managers(main_window)
        for name, manager in specialized_managers.items():
            setattr(main_window, name, manager)
