"""
Operacje zmiany nazw plików.
"""

import logging

from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QProgressDialog, QWidget

from src.logic import file_operations
from src.models.file_pair import FilePair

logger = logging.getLogger(__name__)


class RenameOperations:
    """
    Klasa obsługująca operacje zmiany nazw plików.
    """

    def __init__(self, parent_window):
        self.parent_window = parent_window

    def rename_file_pair(self, file_pair: FilePair, widget: QWidget) -> None:
        """
        Rozpoczyna proces zmiany nazwy dla pary plików przy użyciu workera.

        Args:
            file_pair: Para plików do zmiany nazwy
            widget: Widget wywołujący operację
        """
        current_name = file_pair.get_base_name()
        new_name, ok = QInputDialog.getText(
            self.parent_window,
            "Zmień nazwę",
            "Wprowadź nową nazwę (bez rozszerzenia):",
            text=current_name,
        )

        if ok and new_name and new_name != current_name:
            # Pobierz working_directory z file_pair
            working_directory = file_pair.working_directory
            worker = file_operations.rename_file_pair(
                file_pair, new_name, working_directory
            )

            if worker:
                message = f"Zmiana nazwy pliku '{current_name}' " f"na '{new_name}'..."
                progress_dialog = QProgressDialog(
                    message,
                    "Anuluj",
                    0,
                    0,
                    self.parent_window,
                )
                progress_dialog.setWindowTitle("Zmiana nazwy pliku")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.setAutoClose(True)
                progress_dialog.setAutoReset(True)
                progress_dialog.setValue(0)

                worker.signals.finished.connect(
                    lambda old_fp, new_fp: self._handle_rename_finished(
                        old_fp, new_fp, progress_dialog
                    )
                )
                worker.signals.error.connect(
                    lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd zmiany nazwy pliku", progress_dialog
                    )
                )
                worker.signals.progress.connect(
                    lambda percent, msg: self._handle_operation_progress(
                        percent, msg, progress_dialog
                    )
                )
                worker.signals.interrupted.connect(
                    lambda: self._handle_operation_interrupted(
                        "Zmiana nazwy pliku przerwana.", progress_dialog
                    )
                )
                progress_dialog.canceled.connect(worker.interrupt)

                QThreadPool.globalInstance().start(worker)
                progress_dialog.show()
            else:
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd inicjalizacji",
                    f"Nie można zainicjować operacji zmiany nazwy pliku '{current_name}'. Sprawdź logi.",
                )

    def _handle_rename_finished(
        self,
        old_file_pair: FilePair,
        new_file_pair: FilePair,
        progress_dialog: QProgressDialog,
    ):
        """
        Obsługuje zakończenie operacji zmiany nazwy.

        Args:
            old_file_pair: Stara para plików
            new_file_pair: Nowa para plików
            progress_dialog: Dialog postępu
        """
        old_name = old_file_pair.get_base_name()
        new_name = new_file_pair.get_base_name()
        logger.info(f"Pomyślnie zmieniono nazwę pliku z '{old_name}' na '{new_name}'.")
        if progress_dialog.isVisible():
            progress_dialog.accept()

        success_msg = (
            f"Pomyślnie zmieniono nazwę pliku '{old_name}' " f"na '{new_name}'."
        )
        QMessageBox.information(
            self.parent_window,
            "Sukces",
            success_msg,
        )
        # Odśwież widoki w MainWindow
        if hasattr(self.parent_window, "refresh_all_views") and callable(
            self.parent_window.refresh_all_views
        ):
            self.parent_window.refresh_all_views(new_selection=new_file_pair)

    def _handle_operation_error(
        self, error_message: str, title: str, progress_dialog: QProgressDialog
    ):
        """
        Obsługuje błędy operacji.

        Args:
            error_message: Komunikat błędu
            title: Tytuł okna błędu
            progress_dialog: Dialog postępu
        """
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
        """
        Obsługuje postęp operacji.

        Args:
            percent: Procent ukończenia
            message: Komunikat postępu
            progress_dialog: Dialog postępu
        """
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
        """
        Obsługuje przerwanie operacji.

        Args:
            message: Komunikat przerwania
            progress_dialog: Dialog postępu
        """
        logger.info(f"Operacja przerwana: {message}")
        if progress_dialog and progress_dialog.isVisible():
            progress_dialog.reject()
        QMessageBox.information(self.parent_window, "Operacja przerwana", message)
        if hasattr(self.parent_window, "refresh_all_views") and callable(
            self.parent_window.refresh_all_views
        ):
            self.parent_window.refresh_all_views()
