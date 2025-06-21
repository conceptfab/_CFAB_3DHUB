"""
Manager operacji na folderach - tworzenie, usuwanie, przemianowywanie.
Wydzielony z DirectoryTreeManager w ramach refaktoryzacji architektury.
"""

import logging
import os
import subprocess
from typing import Callable, Optional

from PyQt6.QtCore import QObject, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QInputDialog, QMessageBox, QProgressDialog, QWidget

from src.ui.delegates.workers.folder_workers import (
    CreateFolderWorker,
    DeleteFolderWorker,
    RenameFolderWorker,
)
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class FolderOperationsManager:
    """Manager operacji na folderach z zunifikowanymi workerami."""

    def __init__(self, parent_window: QWidget):
        self.parent_window = parent_window
        self._active_operations = {}  # Słownik aktywnych operacji

    def create_folder(
        self, parent_folder_path: str, callback: Optional[Callable] = None
    ):
        """Tworzy nowy folder z dialog box."""
        folder_name, ok = QInputDialog.getText(
            self.parent_window,
            "Utwórz nowy folder",
            "Nazwa folderu:",
            text="Nowy folder",
        )

        if not ok or not folder_name.strip():
            return

        folder_name = folder_name.strip()
        new_folder_path = os.path.join(parent_folder_path, folder_name)

        # Sprawdź czy folder już istnieje
        if os.path.exists(new_folder_path):
            QMessageBox.warning(
                self.parent_window,
                "Błąd tworzenia folderu",
                f"Folder '{folder_name}' już istnieje!",
            )
            return

        # Utwórz progress dialog
        progress_dialog = self._create_progress_dialog(
            "Tworzenie folderu...", folder_name
        )

        # Utwórz worker
        worker = CreateFolderWorker(new_folder_path)
        operation_id = f"create_{new_folder_path}"
        self._active_operations[operation_id] = worker

        def on_finished(created_path):
            self._cleanup_operation(operation_id, progress_dialog)
            if callback:
                callback(created_path)
            QMessageBox.information(
                self.parent_window,
                "Sukces",
                f"Folder '{folder_name}' został utworzony!",
            )

        def on_error(error_msg):
            self._cleanup_operation(operation_id, progress_dialog)
            QMessageBox.critical(
                self.parent_window,
                "Błąd tworzenia folderu",
                f"Nie można utworzyć folderu:\n{error_msg}",
            )

        def on_progress(percent, message):
            if progress_dialog:
                progress_dialog.setValue(percent)
                progress_dialog.setLabelText(message)

        # Podłącz sygnały
        worker.signals.finished.connect(on_finished)
        worker.signals.error.connect(on_error)
        worker.signals.progress.connect(on_progress)

        # Uruchom worker
        QThreadPool.globalInstance().start(worker)
        progress_dialog.show()

    def rename_folder(self, folder_path: str, callback: Optional[Callable] = None):
        """Przemianowuje folder z dialog box."""
        current_name = os.path.basename(folder_path)
        new_name, ok = QInputDialog.getText(
            self.parent_window, "Przemianuj folder", "Nowa nazwa:", text=current_name
        )

        if not ok or not new_name.strip() or new_name == current_name:
            return

        new_name = new_name.strip()
        parent_dir = os.path.dirname(folder_path)
        new_folder_path = os.path.join(parent_dir, new_name)

        # Sprawdź czy folder o takiej nazwie już istnieje
        if os.path.exists(new_folder_path):
            QMessageBox.warning(
                self.parent_window,
                "Błąd przemianowania",
                f"Folder o nazwie '{new_name}' już istnieje!",
            )
            return

        # Utwórz progress dialog
        progress_dialog = self._create_progress_dialog(
            "Przemianowywanie folderu...", f"{current_name} → {new_name}"
        )

        # Utwórz worker
        worker = RenameFolderWorker(folder_path, new_folder_path)
        operation_id = f"rename_{folder_path}"
        self._active_operations[operation_id] = worker

        def on_finished(old_path, new_path):
            self._cleanup_operation(operation_id, progress_dialog)
            if callback:
                callback(old_path, new_path)
            QMessageBox.information(
                self.parent_window, "Sukces", f"Folder przemianowany na '{new_name}'"
            )

        def on_error(error_msg):
            self._cleanup_operation(operation_id, progress_dialog)
            QMessageBox.critical(
                self.parent_window,
                "Błąd przemianowania",
                f"Nie można przemianować folderu:\n{error_msg}",
            )

        def on_progress(percent, message):
            if progress_dialog:
                progress_dialog.setValue(percent)
                progress_dialog.setLabelText(message)

        # Podłącz sygnały
        worker.signals.finished.connect(
            lambda: on_finished(folder_path, new_folder_path)
        )
        worker.signals.error.connect(on_error)
        worker.signals.progress.connect(on_progress)

        # Uruchom worker
        QThreadPool.globalInstance().start(worker)
        progress_dialog.show()

    def delete_folder(self, folder_path: str, callback: Optional[Callable] = None):
        """Usuwa folder po potwierdzeniu."""
        folder_name = os.path.basename(folder_path)

        # Potwierdzenie usunięcia
        reply = QMessageBox.question(
            self.parent_window,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć folder '{folder_name}'?\n\n"
            "Ta operacja jest nieodwracalna!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Utwórz progress dialog
        progress_dialog = self._create_progress_dialog(
            "Usuwanie folderu...", folder_name
        )

        # Utwórz worker
        worker = DeleteFolderWorker(folder_path)
        operation_id = f"delete_{folder_path}"
        self._active_operations[operation_id] = worker

        def on_finished(deleted_path):
            self._cleanup_operation(operation_id, progress_dialog)
            if callback:
                callback(deleted_path)
            QMessageBox.information(
                self.parent_window, "Sukces", f"Folder '{folder_name}' został usunięty!"
            )

        def on_error(error_msg):
            self._cleanup_operation(operation_id, progress_dialog)
            QMessageBox.critical(
                self.parent_window,
                "Błąd usuwania",
                f"Nie można usunąć folderu:\n{error_msg}",
            )

        def on_progress(percent, message):
            if progress_dialog:
                progress_dialog.setValue(percent)
                progress_dialog.setLabelText(message)

        # Podłącz sygnały
        worker.signals.finished.connect(lambda: on_finished(folder_path))
        worker.signals.error.connect(on_error)
        worker.signals.progress.connect(on_progress)

        # Uruchom worker
        QThreadPool.globalInstance().start(worker)
        progress_dialog.show()

    def open_folder_in_explorer(self, folder_path: str):
        """Otwiera folder w eksploratorze plików."""
        try:
            normalized_path = normalize_path(folder_path)

            if not os.path.exists(normalized_path):
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd",
                    f"Folder nie istnieje:\n{normalized_path}",
                )
                return

            import platform

            system = platform.system()

            if system == "Windows":
                os.startfile(normalized_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", normalized_path])
            else:  # Linux and others
                subprocess.run(["xdg-open", normalized_path])

            logger.info(f"Otwarto folder w eksploratorze: {normalized_path}")

        except Exception as e:
            logger.error(f"Błąd otwierania folderu {folder_path}: {e}")
            QMessageBox.critical(
                self.parent_window, "Błąd", f"Nie można otworzyć folderu:\n{e}"
            )

    def _create_progress_dialog(self, title: str, description: str) -> QProgressDialog:
        """Tworzy dialog postępu dla operacji."""
        progress_dialog = QProgressDialog(self.parent_window)
        progress_dialog.setWindowTitle(title)
        progress_dialog.setLabelText(f"Przetwarzanie: {description}")
        progress_dialog.setRange(0, 100)
        progress_dialog.setAutoClose(True)
        progress_dialog.setAutoReset(True)
        return progress_dialog

    def _cleanup_operation(self, operation_id: str, progress_dialog: QProgressDialog):
        """Czyści po zakończonej operacji."""
        if operation_id in self._active_operations:
            del self._active_operations[operation_id]

        if progress_dialog:
            progress_dialog.close()

    def cancel_all_operations(self):
        """Anuluje wszystkie aktywne operacje."""
        for operation_id, worker in list(self._active_operations.items()):
            try:
                worker.interrupt()
            except:
                pass

        self._active_operations.clear()
        logger.info("Anulowano wszystkie aktywne operacje na folderach")

    def get_active_operations_count(self) -> int:
        """Zwraca liczbę aktywnych operacji."""
        return len(self._active_operations)
