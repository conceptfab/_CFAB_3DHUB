"""
Basic File Operations - ETAP 5 refaktoryzacji file_operations_ui.py
Zarządza podstawowymi operacjami na plikach: rename, delete, move.
"""

import logging
from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox, QProgressDialog, QWidget

from src.models.file_pair import FilePair
from src.ui.file_operations.delete_operations import DeleteOperations
from src.ui.file_operations.rename_operations import RenameOperations

logger = logging.getLogger(__name__)


class BasicFileOperations:
    """
    Manager podstawowych operacji na plikach.
    
    Kombinuje operacje rename, delete i move w jednym miejscu,
    zapewniając spójny interfejs dla FileOperationsUI.
    """
    
    def __init__(self, parent_window, progress_factory, worker_coordinator, controller):
        """
        Initialize basic file operations manager.
        
        Args:
            parent_window: Okno nadrzędne dla dialogów
            progress_factory: Factory do tworzenia dialogów postępu
            worker_coordinator: Coordinator dla workerów
            controller: FileOperationsController
        """
        self.parent_window = parent_window
        self.progress_factory = progress_factory
        self.worker_coordinator = worker_coordinator
        self.controller = controller
        
        # Inicjalizuj podkomponenty
        self.delete_operations = DeleteOperations(parent_window)
        self.rename_operations = RenameOperations(parent_window)
        
        logger.debug("BasicFileOperations manager zainicjalizowany")
    
    def rename_file_pair(self, file_pair: FilePair, widget: QWidget) -> None:
        """
        Deleguje operację rename do RenameOperations, ale używa unified managera.
        
        Args:
            file_pair: Para plików do zmiany nazwy
            widget: Widget wywołujący operację
        """
        logger.debug(f"Rozpoczynanie rename dla {file_pair.get_base_name()}")
        
        # Pobierz nową nazwę od użytkownika
        from PyQt6.QtWidgets import QInputDialog
        current_name = file_pair.get_base_name()
        new_name, ok = QInputDialog.getText(
            self.parent_window,
            "Zmień nazwę",
            "Wprowadź nową nazwę (bez rozszerzenia):",
            text=current_name,
        )

        if ok and new_name and new_name != current_name:
            # Użyj controllera do utworzenia workera
            working_directory = file_pair.working_directory
            worker = self.controller.rename_file_pair(
                file_pair, new_name, working_directory
            )

            if worker:
                # Użyj progress factory
                progress_dialog = self.progress_factory.create_rename_dialog(
                    current_name, new_name
                )

                # Użyj worker coordinator
                self.worker_coordinator.setup_and_start_worker(
                    worker=worker,
                    progress_dialog=progress_dialog,
                    finished_handler=lambda new_fp: self._handle_rename_finished(
                        file_pair, new_fp, progress_dialog
                    ),
                    error_handler=lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd zmiany nazwy pliku", progress_dialog
                    ),
                    progress_handler=lambda percent, msg: self._handle_operation_progress(
                        percent, msg, progress_dialog
                    ),
                    interrupted_handler=lambda: self._handle_operation_interrupted(
                        "Zmiana nazwy pliku przerwana.", progress_dialog
                    )
                )
            else:
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd inicjalizacji",
                    f"Nie można zainicjować operacji zmiany nazwy pliku '{current_name}'. Sprawdź logi.",
                )
    
    def delete_file_pair(self, file_pair: FilePair, widget: QWidget) -> None:
        """
        Deleguje operację delete do DeleteOperations, ale używa unified managera.
        
        Args:
            file_pair: Para plików do usunięcia
            widget: Widget wywołujący operację
        """
        logger.debug(f"Rozpoczynanie delete dla {file_pair.get_base_name()}")
        
        # Potwierdź usunięcie
        confirm = QMessageBox.question(
            self.parent_window,
            "Potwierdź usunięcie",
            f"Czy na pewno chcesz usunąć pliki dla "
            f"'{file_pair.get_base_name()}'?\n\n"
            f"Archiwum: {file_pair.get_archive_path()}\n"
            f"Podgląd: {file_pair.get_preview_path()}\n\n"
            "Ta operacja jest nieodwracalna.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            # Użyj controllera do utworzenia workera
            worker = self.controller.delete_file_pair(file_pair)

            if worker:
                # Użyj progress factory
                progress_dialog = self.progress_factory.create_delete_dialog(
                    file_pair.get_base_name()
                )

                # Użyj worker coordinator
                self.worker_coordinator.setup_and_start_worker(
                    worker=worker,
                    progress_dialog=progress_dialog,
                    finished_handler=lambda deleted_fp: self._handle_delete_finished(
                        deleted_fp, progress_dialog
                    ),
                    error_handler=lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd usuwania pliku", progress_dialog
                    ),
                    progress_handler=lambda percent, msg: self._handle_operation_progress(
                        percent, msg, progress_dialog
                    ),
                    interrupted_handler=lambda: self._handle_operation_interrupted(
                        "Usuwanie pliku przerwane.", progress_dialog
                    )
                )
            else:
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd inicjalizacji",
                    f"Nie można zainicjować operacji usuwania pliku '{file_pair.get_base_name()}'. Sprawdź logi.",
                )
    
    def move_file_pair_ui(
        self, file_pair_to_move: FilePair, target_folder_path: str
    ) -> None:
        """
        Przenosi parę plików do nowego folderu używając unified managera.
        
        Args:
            file_pair_to_move: Para plików do przeniesienia
            target_folder_path: Ścieżka docelowa
        """
        logger.debug(f"Rozpoczynanie move dla {file_pair_to_move.get_base_name()} do {target_folder_path}")
        
        # Sprawdzenie podstawowych parametrów
        if not file_pair_to_move or not target_folder_path:
            logger.warning(
                "Próba przeniesienia nieprawidłowej pary plików lub do nieprawidłowej lokalizacji."
            )
            return

        # Sprawdzenie, czy folder docelowy jest taki sam jak folder źródłowy
        import os
        from src.utils.path_validator import PathValidator
        
        source_folder_path = os.path.dirname(file_pair_to_move.archive_path)
        if PathValidator.normalize_path(source_folder_path) == PathValidator.normalize_path(target_folder_path):
            QMessageBox.information(
                self.parent_window,
                "Informacja",
                "Plik już znajduje się w folderze docelowym.",
            )
            return
        
        # Użyj controllera do utworzenia workera
        worker = self.controller.move_file_pair(file_pair_to_move, target_folder_path)
        
        if worker:
            # Użyj progress factory
            progress_dialog = self.progress_factory.create_move_dialog(
                file_pair_to_move.get_base_name(), target_folder_path
            )

            # Użyj worker coordinator
            self.worker_coordinator.setup_and_start_worker(
                worker=worker,
                progress_dialog=progress_dialog,
                finished_handler=lambda new_fp: self._handle_move_finished(
                    file_pair_to_move, new_fp, target_folder_path, progress_dialog
                ),
                error_handler=lambda err_msg: self._handle_operation_error(
                    err_msg, "Błąd przenoszenia pliku", progress_dialog
                ),
                progress_handler=lambda percent, msg: self._handle_operation_progress(
                    percent, msg, progress_dialog
                ),
                interrupted_handler=lambda: self._handle_operation_interrupted(
                    "Przenoszenie pliku przerwane.", progress_dialog
                )
            )
        else:
            QMessageBox.warning(
                self.parent_window,
                "Błąd inicjalizacji",
                f"Nie można zainicjować operacji przenoszenia pliku '{file_pair_to_move.get_base_name()}'. Sprawdź logi.",
            )
    
    # === HANDLERS ===
    
    def _handle_rename_finished(
        self,
        old_file_pair: FilePair,
        new_file_pair: FilePair,
        progress_dialog: QProgressDialog,
    ):
        """Obsługuje zakończenie operacji rename."""
        logger.info(
            f"Pomyślnie zmieniono nazwę pliku z '{old_file_pair.get_base_name()}' na '{new_file_pair.get_base_name()}'."
        )
        if progress_dialog.isVisible():
            progress_dialog.accept()

        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie zmieniono nazwę pliku '{old_file_pair.get_base_name()}' na '{new_file_pair.get_base_name()}'.",
        )
        self._refresh_views(new_selection=new_file_pair)
    
    def _handle_delete_finished(
        self, deleted_file_pair: FilePair, progress_dialog: QProgressDialog
    ):
        """Obsługuje zakończenie operacji delete."""
        logger.info(
            f"Pomyślnie usunięto pliki dla '{deleted_file_pair.get_base_name()}'."
        )
        if progress_dialog.isVisible():
            progress_dialog.accept()

        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie usunięto pliki dla '{deleted_file_pair.get_base_name()}'.",
        )
        self._refresh_views()
    
    def _handle_move_finished(
        self,
        old_file_pair: FilePair,
        new_file_pair: FilePair,
        target_folder_path: str,
        progress_dialog: QProgressDialog,
    ):
        """Obsługuje zakończenie operacji move."""
        logger.info(
            f"Pomyślnie przeniesiono pliki dla '{old_file_pair.get_base_name()}' do '{target_folder_path}'."
        )
        if progress_dialog.isVisible():
            progress_dialog.accept()

        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie przeniesiono pliki dla '{old_file_pair.get_base_name()}' do nowego folderu.",
        )
        
        # Odświeżenie z małym opóźnieniem dla stabilności
        timer = QTimer()
        timer.singleShot(500, lambda: self._refresh_views(new_selection=new_file_pair))
    
    def _handle_operation_error(
        self, error_message: str, title: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje błędy operacji."""
        logger.error(f"{title}: {error_message}")
        if progress_dialog and progress_dialog.isVisible():
            progress_dialog.reject()
        QMessageBox.critical(self.parent_window, title, error_message)
        self._refresh_views()

    def _handle_operation_progress(
        self, percent: int, message: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje postęp operacji."""
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
        """Obsługuje przerwanie operacji."""
        logger.info(f"Operacja przerwana: {message}")
        if progress_dialog and progress_dialog.isVisible():
            progress_dialog.reject()
        QMessageBox.information(self.parent_window, "Operacja przerwana", message)
        self._refresh_views()
    
    def _refresh_views(self, new_selection: Optional[FilePair] = None):
        """Odświeża widoki w parent window."""
        if hasattr(self.parent_window, "refresh_all_views") and callable(
            self.parent_window.refresh_all_views
        ):
            if new_selection:
                self.parent_window.refresh_all_views(new_selection=new_selection)
            else:
                self.parent_window.refresh_all_views() 