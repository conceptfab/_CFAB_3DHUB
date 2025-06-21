"""
Manager operacji na plikach w interfejsie użytkownika.
"""

import logging
from typing import List

from PyQt6.QtWidgets import QListWidget, QProgressDialog, QWidget

from src.controllers.file_operations_controller import FileOperationsController
from src.models.file_pair import FilePair
from src.ui.file_operations.progress_dialog_factory import ProgressDialogFactory
from src.ui.file_operations.worker_coordinator import WorkerCoordinator
from src.ui.file_operations.context_menu_manager import ContextMenuManager
from src.ui.file_operations.detailed_reporting import DetailedReporting
from src.ui.file_operations.basic_file_operations import BasicFileOperations
from src.ui.file_operations.drag_drop_handler import DragDropHandler
from src.ui.file_operations.manual_pairing_manager import ManualPairingManager

logger = logging.getLogger(__name__)


class FileOperationsUI:
    """
    Klasa zarządzająca operacjami na plikach w interfejsie użytkownika.
    """

    def __init__(self, parent_window):
        self.parent_window = parent_window
        self.controller = FileOperationsController()
        
        # ETAP 1: Progress Dialog Factory
        self.progress_factory = ProgressDialogFactory(parent_window)
        # ETAP 2: Worker Coordinator
        self.worker_coordinator = WorkerCoordinator()
        # ETAP 3: Context Menu Manager
        self.context_menu_manager = ContextMenuManager(parent_window)
        # ETAP 7: Detailed Reporting
        self.detailed_reporting = DetailedReporting(parent_window)
        
        # ETAP 5: Basic File Operations
        self.basic_operations = BasicFileOperations(
            parent_window, self.progress_factory, self.worker_coordinator, self.controller
        )
        # ETAP 4: Drag & Drop Handler
        self.drag_drop_handler = DragDropHandler(
            parent_window, self.progress_factory, self.worker_coordinator, self.detailed_reporting
        )
        # ETAP 6: Manual Pairing Manager
        self.pairing_manager = ManualPairingManager(
            parent_window, self.progress_factory, self.worker_coordinator, self.controller
        )

    # Wspólne metody obsługi sygnałów workerów (podobne do DirectoryTreeManager)
    def _handle_operation_error(
        self, error_message: str, title: str, progress_dialog: QProgressDialog
    ):
        logger.error(f"{title}: {error_message}")
        if progress_dialog and progress_dialog.isVisible():
            progress_dialog.reject()
        QMessageBox.critical(self.parent_window, title, error_message)
        # Można dodać odświeżanie widoków, jeśli to konieczne
        if hasattr(self.parent_window, "refresh_all_views") and callable(
            self.parent_window.refresh_all_views
        ):
            self.parent_window.refresh_all_views()

    def _handle_operation_progress(
        self, percent: int, message: str, progress_dialog: QProgressDialog
    ):
        logger.debug(f"Postęp operacji: {percent}% - {message}")
        if progress_dialog and progress_dialog.isVisible():
            if progress_dialog.maximum() == 0:  # Nieokreślony
                progress_dialog.setLabelText(message)
            else:
                progress_dialog.setValue(percent)
                progress_dialog.setLabelText(message)

    def _handle_operation_interrupted(
        self, message: str, progress_dialog: QProgressDialog
    ):
        logger.info(f"Operacja przerwana: {message}")
        if progress_dialog and progress_dialog.isVisible():
            progress_dialog.reject()
        QMessageBox.information(self.parent_window, "Operacja przerwana", message)
        if hasattr(self.parent_window, "refresh_all_views") and callable(
            self.parent_window.refresh_all_views
        ):
            self.parent_window.refresh_all_views()

    def show_file_context_menu(self, file_pair: FilePair, widget: QWidget, position):
        """
        Wyświetla menu kontekstowe dla kafelka.
        """
        # ETAP 3: Użycie ContextMenuManager
        # ETAP 5: Delegacja do BasicFileOperations
        self.context_menu_manager.show_file_context_menu(
            file_pair=file_pair,
            widget=widget,
            position=position,
            rename_callback=self.basic_operations.rename_file_pair,
            delete_callback=self.basic_operations.delete_file_pair
        )

    def rename_file_pair(
        self, file_pair: FilePair, widget: QWidget
    ) -> None:
        """
        Deleguje operację rename do BasicFileOperations (ETAP 5).
        """
        # ETAP 5: Delegacja do BasicFileOperations
        self.basic_operations.rename_file_pair(file_pair, widget)



    def delete_file_pair(
        self, file_pair: FilePair, widget: QWidget
    ) -> None:
        """
        Deleguje operację delete do BasicFileOperations (ETAP 5).
        """
        # ETAP 5: Delegacja do BasicFileOperations
        self.basic_operations.delete_file_pair(file_pair, widget)



    def handle_manual_pairing(
        self,
        unpaired_archives_list: QListWidget,
        unpaired_previews_list: QListWidget,
        current_working_directory: str,
    ) -> None:
        """
        Deleguje operację ręcznego parowania do ManualPairingManager (ETAP 6).
        """
        # ETAP 6: Delegacja do ManualPairingManager
        self.pairing_manager.handle_manual_pairing(
            unpaired_archives_list, unpaired_previews_list, current_working_directory
        )



    def handle_drop_on_folder(self, urls: List, target_folder_path: str):
        """
        Deleguje operację drag & drop do DragDropHandler (ETAP 4).
        """
        # ETAP 4: Delegacja do DragDropHandler
        return self.drag_drop_handler.handle_drop_on_folder(urls, target_folder_path)

    def show_unpaired_context_menu(
        self, position, list_widget: QListWidget, list_type: str
    ):
        """
        Wyświetla menu kontekstowe dla listy niesparowanych plików.
        """
        # ETAP 3: Użycie ContextMenuManager
        self.context_menu_manager.show_unpaired_context_menu(
            position=position,
            list_widget=list_widget,
            list_type=list_type
        )

    def move_file_pair_ui(
        self, file_pair_to_move: FilePair, target_folder_path: str
    ) -> None:
        """
        Deleguje operację move do BasicFileOperations (ETAP 5).
        """
        # ETAP 5: Delegacja do BasicFileOperations
        self.basic_operations.move_file_pair_ui(file_pair_to_move, target_folder_path)




