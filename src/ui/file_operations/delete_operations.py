"""
Operacje usuwania plików.
"""

import logging

from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtWidgets import QMessageBox, QProgressDialog, QWidget

from src.logic import file_operations
from src.models.file_pair import FilePair

logger = logging.getLogger(__name__)


class DeleteOperations:
    """
    Klasa obsługująca operacje usuwania plików.
    """

    def __init__(self, parent_window):
        self.parent_window = parent_window

    def delete_file_pair(self, file_pair: FilePair, widget: QWidget) -> None:
        """
        Usuwa parę plików (archiwum i podgląd) po potwierdzeniu, używając workera.

        Args:
            file_pair: Para plików do usunięcia
            widget: Widget wywołujący operację
        """
        confirm = QMessageBox.question(
            self.parent_window,
            "Potwierdź usunięcie",
            f"Czy na pewno chcesz usunąć pliki dla "
            f"'{file_pair.get_base_name()}'?\n\n"
            f"Archiwum: {file_pair.get_archive_path()}\n"
            f"Podgląd: {file_pair.get_preview_path()}\n\n"
            f"Ta operacja jest nieodwracalna!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            worker = file_operations.delete_file_pair(file_pair)

            if worker:
                progress_dialog = QProgressDialog(
                    f"Usuwanie plików dla '{file_pair.get_base_name()}'...",
                    "Anuluj",
                    0,
                    0,
                    self.parent_window,
                )
                progress_dialog.setWindowTitle("Usuwanie plików")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.setAutoClose(True)
                progress_dialog.setAutoReset(True)
                progress_dialog.setValue(0)

                worker.signals.finished.connect(
                    lambda deleted_fp: self._handle_delete_finished(
                        deleted_fp, progress_dialog
                    )
                )
                worker.signals.error.connect(
                    lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd usuwania pliku", progress_dialog
                    )
                )
                worker.signals.progress.connect(
                    lambda percent, msg: self._handle_operation_progress(
                        percent, msg, progress_dialog
                    )
                )
                worker.signals.interrupted.connect(
                    lambda: self._handle_operation_interrupted(
                        "Usuwanie pliku przerwane.", progress_dialog
                    )
                )
                progress_dialog.canceled.connect(worker.interrupt)

                QThreadPool.globalInstance().start(worker)
                progress_dialog.show()
            else:
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd inicjalizacji",
                    f"Nie można zainicjować operacji usuwania pliku '{file_pair.get_base_name()}'. Sprawdź logi.",
                )

    def _handle_delete_finished(
        self, deleted_file_pair: FilePair, progress_dialog: QProgressDialog
    ):
        """
        Obsługuje zakończenie operacji usuwania.

        Args:
            deleted_file_pair: Usunięta para plików
            progress_dialog: Dialog postępu
        """
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
        # Odśwież widoki w MainWindow
        if hasattr(self.parent_window, "refresh_all_views") and callable(
            self.parent_window.refresh_all_views
        ):
            self.parent_window.refresh_all_views()

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
