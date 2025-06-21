"""
Facade dla MainWindow - centralny punkt dostępu do wszystkich managerów.
Redukuje liczbę importów w MainWindow z 28 do <10.
"""

import logging
from typing import Optional

from src.controllers.main_window_controller import MainWindowController
from src.ui.directory_tree.manager import DirectoryTreeManager
from src.ui.file_operations_ui import FileOperationsUI
from src.ui.gallery_manager import GalleryManager
from src.ui.main_window.event_handler import EventHandler
from src.ui.main_window.file_operations_coordinator import FileOperationsCoordinator
from src.ui.main_window.progress_manager import ProgressManager
from src.ui.main_window.ui_manager import UIManager
from src.ui.main_window.worker_manager import WorkerManager
from src.ui.main_window_components.view_refresh_manager import ViewRefreshManager

logger = logging.getLogger(__name__)


class MainWindowFacade:
    """
    Facade dla MainWindow - enkapsuluje wszystkie managery i kontrolery.
    """
    
    def __init__(self, main_window=None):
        """
        Inicjalizuje facade z referencją do głównego okna.
        
        Args:
            main_window: Referencja do instancji MainWindow
        """
        self.main_window = main_window
        
        # Inicjalizacja komponentów zostanie wykonana przez setup()
        self.controller: Optional[MainWindowController] = None
        self.ui_manager: Optional[UIManager] = None
        self.event_handler: Optional[EventHandler] = None
        self.worker_manager: Optional[WorkerManager] = None
        self.progress_manager: Optional[ProgressManager] = None
        self.file_operations_coordinator: Optional[FileOperationsCoordinator] = None
        self.view_refresh_manager: Optional[ViewRefreshManager] = None
        
        # Managery UI komponentów
        self.directory_tree_manager: Optional[DirectoryTreeManager] = None
        self.gallery_manager: Optional[GalleryManager] = None
        self.file_operations_ui: Optional[FileOperationsUI] = None
    
    def setup(self, main_window):
        """
        Konfiguruje wszystkie managery po inicjalizacji UI.
        
        Args:
            main_window: Instancja MainWindow z skonfigurowanym UI
        """
        self.main_window = main_window
        
        # Inicjalizacja kontrolera
        self.controller = MainWindowController()
        
        # Inicjalizacja managerów podstawowych
        self.ui_manager = UIManager(main_window)
        self.event_handler = EventHandler(main_window)
        self.worker_manager = WorkerManager(main_window)
        self.progress_manager = ProgressManager(main_window)
        self.file_operations_coordinator = FileOperationsCoordinator(main_window)
        self.view_refresh_manager = ViewRefreshManager(main_window)
        
        # Inicjalizacja managerów UI komponentów
        self._setup_ui_managers(main_window)
        
        logger.debug("MainWindowFacade skonfigurowany pomyślnie")
    
    def _setup_ui_managers(self, main_window):
        """
        Konfiguruje managery komponentów UI.
        
        Args:
            main_window: Instancja MainWindow
        """
        # Directory Tree Manager
        if hasattr(main_window, 'folder_tree_view') and hasattr(main_window, 'folder_scroll_area'):
            self.directory_tree_manager = DirectoryTreeManager(
                main_window.folder_tree_view,
                main_window.folder_scroll_area,
                main_window
            )
        
        # Gallery Manager
        if (hasattr(main_window, 'tiles_container') and 
            hasattr(main_window, 'tiles_layout') and 
            hasattr(main_window, 'gallery_scroll_area')):
            self.gallery_manager = GalleryManager(
                main_window,
                main_window.tiles_container,
                main_window.tiles_layout,
                main_window.gallery_scroll_area
            )
        
        # File Operations UI
        self.file_operations_ui = FileOperationsUI(main_window)
        
        logger.debug("UI managery skonfigurowane")
    
    def get_controller(self) -> MainWindowController:
        """Zwraca kontroler głównego okna."""
        return self.controller
    
    def get_ui_manager(self) -> UIManager:
        """Zwraca manager UI."""
        return self.ui_manager
    
    def get_event_handler(self) -> EventHandler:
        """Zwraca handler zdarzeń."""
        return self.event_handler
    
    def get_worker_manager(self) -> WorkerManager:
        """Zwraca manager workerów."""
        return self.worker_manager
    
    def get_progress_manager(self) -> ProgressManager:
        """Zwraca manager postępu."""
        return self.progress_manager
    
    def get_file_operations_coordinator(self) -> FileOperationsCoordinator:
        """Zwraca koordynator operacji na plikach."""
        return self.file_operations_coordinator
    
    def get_view_refresh_manager(self) -> ViewRefreshManager:
        """Zwraca manager odświeżania widoków."""
        return self.view_refresh_manager
    
    def get_directory_tree_manager(self) -> Optional[DirectoryTreeManager]:
        """Zwraca manager drzewa katalogów."""
        return self.directory_tree_manager
    
    def get_gallery_manager(self) -> Optional[GalleryManager]:
        """Zwraca manager galerii."""
        return self.gallery_manager
    
    def get_file_operations_ui(self) -> FileOperationsUI:
        """Zwraca UI operacji na plikach."""
        return self.file_operations_ui
    
    def cleanup(self):
        """
        Czyści zasoby wszystkich managerów.
        """
        if self.directory_tree_manager:
            # Jeśli manager ma metodę cleanup
            if hasattr(self.directory_tree_manager, 'cleanup'):
                self.directory_tree_manager.cleanup()
        
        if self.gallery_manager:
            self.gallery_manager.clear_gallery()
        
        if self.worker_manager:
            if hasattr(self.worker_manager, 'cleanup'):
                self.worker_manager.cleanup()
        
        logger.debug("MainWindowFacade wyczyszczony")