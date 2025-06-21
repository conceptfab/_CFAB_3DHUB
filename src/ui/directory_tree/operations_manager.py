"""
Manager operacji na folderach dla drzewa katalogów.
Wydzielony z głównego managera w ramach refaktoryzacji.
"""

import logging
import os
from typing import TYPE_CHECKING, Callable

from PyQt6.QtCore import QThreadPool, Qt
from PyQt6.QtWidgets import (
    QInputDialog,
    QMessageBox,
    QProgressDialog,
)

from src.utils.path_validator import PathValidator

if TYPE_CHECKING:
    from .manager import DirectoryTreeManager

logger = logging.getLogger(__name__)


class DirectoryTreeOperationsManager:
    """
    Manager operacji na folderach (create, rename, delete).
    Wydzielony z głównego managera dla lepszej separacji odpowiedzialności.
    """

    def __init__(self, manager: "DirectoryTreeManager"):
        self.manager = manager
        self.parent_window = manager.parent_window
        self.worker_factory = manager.worker_factory

    def create_folder(self, parent_folder_path: str):
        """Tworzy nowy folder w wybranej lokalizacji przy użyciu workera."""
        folder_name, ok = QInputDialog.getText(
            self.parent_window, "Nowy folder", "Podaj nazwę folderu:"
        )

        if ok and folder_name:
            # Normalizacja ścieżki i nazwy folderu
            parent_folder_path_norm = PathValidator.normalize_path(parent_folder_path)

            worker = self.worker_factory.create_create_folder_worker(parent_folder_path_norm, folder_name)

            if worker:
                # Utworzenie okna dialogowego postępu
                progress_dialog = QProgressDialog(
                    f"Tworzenie folderu '{folder_name}'...",
                    "Anuluj",
                    0,
                    0,  # Ustawienie min i max na 0 dla nieokreślonego paska postępu
                    self.parent_window,
                )
                progress_dialog.setWindowTitle("Tworzenie folderu")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.setAutoClose(True)
                progress_dialog.setAutoReset(True)
                progress_dialog.setValue(0)

                # Połączenie sygnałów workera
                worker.signals.finished.connect(
                    lambda path: self._handle_create_folder_finished(
                        path, progress_dialog
                    )
                )
                worker.signals.error.connect(
                    lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd tworzenia folderu", progress_dialog
                    )
                )
                worker.signals.progress.connect(
                    lambda percent, msg: self._handle_operation_progress(
                        percent, msg, progress_dialog
                    )
                )
                worker.signals.interrupted.connect(
                    lambda: self._handle_operation_interrupted(
                        "Tworzenie folderu zostało przerwane.", progress_dialog
                    )
                )

                # Połączenie przycisku anulowania
                progress_dialog.canceled.connect(worker.interrupt)

                # Uruchomienie workera
                QThreadPool.globalInstance().start(worker)

                # Wyświetlenie okna dialogowego
                progress_dialog.show()

    def rename_folder(self, folder_path: str):
        """Zmienia nazwę folderu."""
        current_name = os.path.basename(folder_path)
        new_name, ok = QInputDialog.getText(
            self.parent_window,
            "Zmiana nazwy folderu",
            "Podaj nową nazwę folderu:",
            text=current_name,
        )

        if ok and new_name and new_name != current_name:
            folder_path_norm = PathValidator.normalize_path(folder_path)
            worker = self.worker_factory.create_rename_folder_worker(folder_path_norm, new_name)

            if worker:
                progress_dialog = QProgressDialog(
                    f"Zmiana nazwy folderu '{current_name}' na '{new_name}'...",
                    "Anuluj",
                    0,
                    0,
                    self.parent_window,
                )
                progress_dialog.setWindowTitle("Zmiana nazwy folderu")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.setAutoClose(True)
                progress_dialog.setAutoReset(True)
                progress_dialog.setValue(0)

                worker.signals.finished.connect(
                    lambda new_path: self._handle_rename_folder_finished(
                        folder_path, new_path, progress_dialog
                    )
                )
                worker.signals.error.connect(
                    lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd zmiany nazwy folderu", progress_dialog
                    )
                )
                worker.signals.progress.connect(
                    lambda percent, msg: self._handle_operation_progress(
                        percent, msg, progress_dialog
                    )
                )

                progress_dialog.canceled.connect(worker.interrupt)
                QThreadPool.globalInstance().start(worker)
                progress_dialog.show()

    def delete_folder(self, folder_path: str, current_working_directory: str):
        """Usuwa folder."""
        folder_name = os.path.basename(folder_path)
        reply = QMessageBox.question(
            self.parent_window,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć folder '{folder_name}' i całą jego zawartość?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            folder_path_norm = PathValidator.normalize_path(folder_path)
            worker = self.worker_factory.create_delete_folder_worker(folder_path_norm, delete_content=False)

            if worker:
                progress_dialog = QProgressDialog(
                    f"Usuwanie folderu '{folder_name}'...",
                    "Anuluj",
                    0,
                    0,
                    self.parent_window,
                )
                progress_dialog.setWindowTitle("Usuwanie folderu")
                progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
                progress_dialog.setAutoClose(True)
                progress_dialog.setAutoReset(True)
                progress_dialog.setValue(0)

                worker.signals.finished.connect(
                    lambda deleted_path: self._handle_delete_folder_finished(
                        deleted_path, progress_dialog
                    )
                )
                worker.signals.error.connect(
                    lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd usuwania folderu", progress_dialog
                    )
                )

                progress_dialog.canceled.connect(worker.interrupt)
                QThreadPool.globalInstance().start(worker)
                progress_dialog.show()

    # Handle methods dla operacji na folderach
    def _handle_create_folder_finished(
        self, created_folder_path: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje zakończenie tworzenia folderu."""
        progress_dialog.accept()
        folder_name = os.path.basename(created_folder_path)
        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Folder '{folder_name}' został utworzony pomyślnie.",
        )
        self.manager.refresh_entire_tree()

    def _handle_rename_folder_finished(
        self, old_path: str, new_path: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje zakończenie zmiany nazwy folderu."""
        progress_dialog.accept()
        old_name = os.path.basename(old_path)
        new_name = os.path.basename(new_path)
        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Folder '{old_name}' został przemianowany na '{new_name}'.",
        )
        self.manager.refresh_entire_tree()

    def _handle_delete_folder_finished(
        self, deleted_folder_path: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje zakończenie usuwania folderu."""
        progress_dialog.accept()
        folder_name = os.path.basename(deleted_folder_path)
        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Folder '{folder_name}' został usunięty pomyślnie.",
        )
        self.manager.refresh_entire_tree()

    def _handle_operation_error(
        self, error_message: str, title: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje błędy operacji na folderach."""
        progress_dialog.reject()
        QMessageBox.critical(self.parent_window, title, error_message)

    def _handle_operation_progress(
        self, percent: int, message: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje postęp operacji na folderach."""
        if progress_dialog.isVisible():
            progress_dialog.setValue(percent)
            progress_dialog.setLabelText(message)

    def _handle_operation_interrupted(
        self, message: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje przerwanie operacji na folderach."""
        progress_dialog.reject()
        QMessageBox.information(self.parent_window, "Operacja przerwana", message)