"""
Manager drzewa katalogów - zarządzanie folderami i drzewem nawigacji.
"""

import logging
import os  # Dodano brakujący import os
from typing import List

from PyQt6.QtCore import (
    QDir,
    QEvent,
    QMimeData,
    QModelIndex,
    Qt,
    QThreadPool,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QDragEnterEvent,
    QDragLeaveEvent,
    QDragMoveEvent,
    QDropEvent,
    QFileSystemModel,
    QMouseEvent,
)
from PyQt6.QtWidgets import QProgressDialog  # Dodano QProgressDialog
from PyQt6.QtWidgets import (
    QApplication,
    QInputDialog,
    QMenu,
    QMessageBox,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeView,
)

from src.logic import file_operations

# Dodajemy importy workerów
from src.logic.file_operations import (
    CreateFolderWorker,
    DeleteFolderWorker,
    RenameFolderWorker,
)
from src.logic.scanner import scan_folder_for_pairs
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)  # Dodano inicjalizację loggera


# Definicja delegata do podświetlania celu upuszczenia
class DropHighlightDelegate(QStyledItemDelegate):  # Definicja klasy
    def __init__(self, directory_tree_manager, parent=None):
        super().__init__(parent)
        self.directory_tree_manager = directory_tree_manager

    def paint(self, painter, option, index):
        # Najpierw rysuj element standardowo
        super().paint(painter, option, index)

        # Jeśli ten indeks jest aktualnym celem upuszczenia, narysuj podświetlenie
        if (
            self.directory_tree_manager.highlighted_drop_index.isValid()
            and index == self.directory_tree_manager.highlighted_drop_index
        ):
            # Użyj półprzezroczystego koloru do podświetlenia
            # Nie przesłaniaj całkowicie podświetlenia zaznaczenia, jeśli element jest również zaznaczony
            highlight_color = QColor(
                0, 120, 215, 70
            )  # Półprzezroczysty niebieski (np. styl VS Code)
            painter.fillRect(option.rect, highlight_color)


class DirectoryTreeManager:
    """
    Klasa zarządzająca drzewem katalogów i operacjami na folderach.
    """

    def __init__(self, folder_tree: QTreeView, parent_window):
        self.folder_tree = folder_tree
        self.parent_window = parent_window
        self.model = QFileSystemModel()
        self.model.setRootPath(QDir.rootPath())
        # Filtrowanie, aby pokazywać tylko katalogi
        self.model.setFilter(QDir.Filter.AllDirs | QDir.Filter.NoDotAndDotDot)

        self.folder_tree.setModel(self.model)
        self.folder_tree.setRootIndex(self.model.index(QDir.currentPath()))
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(
            self.show_folder_context_menu
        )

        # Ustawienia Drag and Drop
        self.folder_tree.setDragEnabled(False)  # Drzewo samo nie inicjuje przeciągania
        self.folder_tree.setAcceptDrops(True)
        self.folder_tree.setDropIndicatorShown(True)  # Standardowy wskaźnik linii

        # Podłączanie eventów drag and drop do niestandardowych slotów
        self.folder_tree.dragEnterEvent = self._drag_enter_event
        self.folder_tree.dragMoveEvent = self._drag_move_event
        self.folder_tree.dropEvent = self._drop_event
        self.folder_tree.dragLeaveEvent = (
            self._drag_leave_event
        )  # Dodano obsługę dragLeaveEvent

        # Inicjalizacja dla podświetlania celu upuszczania
        self.highlighted_drop_index = QModelIndex()
        self.drop_delegate = DropHighlightDelegate(
            self, self.folder_tree
        )  # Przekazanie self (DirectoryTreeManager)
        self.folder_tree.setItemDelegate(self.drop_delegate)

        # Włączanie obsługi drag and drop dla drzewa folderów
        self.folder_tree.setAcceptDrops(True)
        self.folder_tree.setDropIndicatorShown(True)

        self.current_scan_path: str | None = None
        self._main_working_directory = None
        # Podłączenie event handlerów dla drag and drop
        self.folder_tree.dragEnterEvent = self._drag_enter_event
        self.folder_tree.dragMoveEvent = (
            self._drag_move_event
        )  # dragMoveEvent nie wymaga specjalnego typu, QEvent wystarczy
        self.folder_tree.dropEvent = self._drop_event

    def _update_highlight(self, new_index: QModelIndex):
        """Aktualizuje podświetlony element docelowy upuszczania."""
        if self.highlighted_drop_index == new_index:
            return  # Bez zmian

        old_highlight = self.highlighted_drop_index
        self.highlighted_drop_index = new_index

        if old_highlight.isValid():
            self.folder_tree.update(old_highlight)  # Odśwież stary element
        if self.highlighted_drop_index.isValid():
            self.folder_tree.update(self.highlighted_drop_index)  # Odśwież nowy element

    def _clear_highlight(self):
        """Czyści podświetlenie elementu docelowego upuszczania."""
        self._update_highlight(QModelIndex())

    def _drag_enter_event(self, event: QDragEnterEvent):
        # Sprawdzamy, czy przeciągane dane zawierają URL-e (pliki)
        if event.mimeData().hasUrls():
            # Sprawdź, czy przeciągane są pliki (a nie np. tekst)
            # Ta walidacja może być bardziej szczegółowa w _drag_move_event
            event.acceptProposedAction()
        else:
            event.ignore()  # Ignorujemy w przeciwnym razie

    def _drag_move_event(self, event: QDragMoveEvent):
        if not event.mimeData().hasUrls():
            event.ignore()
            self._update_highlight(
                QModelIndex()
            )  # Wyczyść podświetlenie, jeśli dane są nieprawidłowe
            return

        index_under_mouse = self.folder_tree.indexAt(event.position().toPoint())
        is_valid_target_folder = False

        if index_under_mouse.isValid() and self.model.isDir(index_under_mouse):
            # Sprawdź, czy to katalog (już sprawdzone przez isDir)
            # Można dodać dodatkowe warunki, np. czy folder jest zapisywalny
            is_valid_target_folder = True

        if is_valid_target_folder:
            event.acceptProposedAction()
            self._update_highlight(index_under_mouse)
        else:
            event.ignore()
            self._update_highlight(
                QModelIndex()
            )  # Wyczyść podświetlenie, jeśli nie jest to prawidłowy cel

    def _drag_leave_event(self, event: QDragLeaveEvent):  # Poprawiono typ eventu
        """Obsługuje zdarzenie opuszczenia obszaru przeciągania przez kursor."""
        self._clear_highlight()
        event.accept()  # Zaakceptuj zdarzenie

    def _drop_event(self, event: QDropEvent):
        # Na końcu, po przetworzeniu upuszczenia lub w bloku finally, jeśli istnieje ryzyko wyjątku
        self._clear_highlight()

        if not event.mimeData().hasUrls():
            self._clear_highlight()  # Dodatkowe czyszczenie na wszelki wypadek
            event.ignore()
            return

        index = self.folder_tree.indexAt(event.position().toPoint())
        if not index.isValid() or not self.model.isDir(index):
            self._clear_highlight()  # Dodatkowe czyszczenie
            event.ignore()
            return

        target_folder_path = self.model.filePath(index)
        source_file_paths = [url.toLocalFile() for url in event.mimeData().urls()]

        valid_files_dragged = True
        for path in source_file_paths:
            # Używamy os.path.isfile() do sprawdzania czy to plik
            if not os.path.isfile(path):
                valid_files_dragged = False
                break

        if not valid_files_dragged:
            self._clear_highlight()
            event.ignore()
            logger.debug(
                "Upuszczono nieprawidłowe dane (nie pliki lub foldery). Ignorowanie."
            )
            return

        logger.info(
            f"Upuszczono pliki: {source_file_paths} na folder: {target_folder_path}"
        )

        # Wywołanie metody w MainWindow do obsługi logiki przenoszenia
        if self.parent_window and hasattr(
            self.parent_window, "handle_file_drop_on_folder"
        ):
            self.parent_window.handle_file_drop_on_folder(
                source_file_paths, target_folder_path
            )
            event.acceptProposedAction()
        else:
            logger.warning(
                "Nie znaleziono metody handle_file_drop_on_folder w oknie nadrzędnym."
            )
            event.ignore()

        self._clear_highlight()  # Ostateczne czyszczenie

    def init_directory_tree(self, current_working_directory: str):
        """
        Inicjalizuje i konfiguruje model drzewa katalogów.
        """
        if not current_working_directory:
            return

        # Sprawdź czy to pierwszy wybór folderu roboczego
        if not self._main_working_directory:
            # Pierwsze uruchomienie - ustaw główny folder roboczy jako root
            self._main_working_directory = current_working_directory

            # Przeskanuj wszystkie podfoldery z plikami
            folders_with_files = self._scan_folders_with_files(
                self._main_working_directory
            )

            # Ustaw główny folder roboczy jako root
            root_index = self.model.setRootPath(self._main_working_directory)
            self.folder_tree.setRootIndex(root_index)

            # Rozwiń automatycznie wszystkie foldery które zawierają pliki
            QTimer.singleShot(
                100, lambda: self._expand_folders_with_files(folders_with_files)
            )

            logging.info(
                "Drzewo katalogów zainicjalizowane - główny folder: %s, "
                "foldery z plikami: %d",
                self._main_working_directory,
                len(folders_with_files),
            )
        elif not current_working_directory.startswith(self._main_working_directory):
            # Jeśli wybrano folder poza głównym folderem roboczym
            self._main_working_directory = current_working_directory

            # Przeskanuj wszystkie podfoldery z plikami
            folders_with_files = self._scan_folders_with_files(
                self._main_working_directory
            )

            # Ustaw główny folder roboczy jako root
            root_index = self.model.setRootPath(self._main_working_directory)
            self.folder_tree.setRootIndex(root_index)

            # Rozwiń automatycznie wszystkie foldery które zawierają pliki
            QTimer.singleShot(
                100, lambda: self._expand_folders_with_files(folders_with_files)
            )

            logging.info(
                "Zmieniono root drzewa - główny folder: %s, " "foldery z plikami: %d",
                self._main_working_directory,
                len(folders_with_files),
            )

        # Zawsze zaznacz aktualny folder w drzewie
        current_index = self.model.index(current_working_directory)
        if current_index.isValid():
            # Rozwiń ścieżkę do aktualnego folderu PRZED zaznaczeniem
            parent = current_index.parent()
            while parent.isValid():
                self.folder_tree.expand(parent)
                parent = parent.parent()

            # Teraz zaznacz folder
            self.folder_tree.setCurrentIndex(current_index)
            self.folder_tree.scrollTo(current_index)

            logging.info(
                "Zaznaczono aktualny folder w drzewie: %s",
                current_working_directory,
            )
        else:
            logging.warning(
                "Nie można zaznaczyć folderu w drzewie - " "nieprawidłowy indeks: %s",
                current_working_directory,
            )

    def _scan_folders_with_files(self, root_folder: str) -> List[str]:
        """
        Skanuje rekursywnie folder roboczy i zwraca listę wszystkich
        podfolderów które zawierają min. 1 plik.
        """
        folders_with_files = []

        try:
            for root, dirs, files in os.walk(root_folder):
                # Pomiń ukryte foldery (zaczynające się od .)
                dirs[:] = [d for d in dirs if not d.startswith(".")]

                # Jeśli folder ma pliki, dodaj go do listy
                if files:
                    folders_with_files.append(root)

            logging.info(
                "Znaleziono %d folderów z plikami w: %s",
                len(folders_with_files),
                root_folder,
            )

        except Exception as e:
            logging.error("Błąd podczas skanowania folderów: %s", str(e))

        return folders_with_files

    def _expand_folders_with_files(self, folders_with_files: List[str]):
        """
        Rozwijaj foldery w drzewie które zawierają pliki.
        """
        try:
            for folder_path in folders_with_files:
                folder_index = self.model.index(folder_path)
                if folder_index.isValid():
                    # Rozwiń ścieżkę do tego folderu
                    parent = folder_index.parent()
                    while parent.isValid():
                        self.folder_tree.expand(parent)
                        parent = parent.parent()

            logging.debug("Rozwinięto %d folderów z plikami", len(folders_with_files))

        except Exception as e:
            logging.error("Błąd podczas rozwijania folderów: %s", str(e))

    def show_folder_context_menu(self, position):
        """
        Wyświetla menu kontekstowe dla drzewa folderów.
        """
        # Pobierz indeks wybranego elementu
        index = self.folder_tree.indexAt(position)
        if not index.isValid():
            return

        # Pobierz ścieżkę do wybranego folderu
        folder_path = self.model.filePath(index)

        # Tworzenie menu kontekstowego
        context_menu = QMenu()

        # Dodanie akcji do menu
        create_folder_action = context_menu.addAction("Nowy folder")
        rename_folder_action = context_menu.addAction("Zmień nazwę")
        delete_folder_action = context_menu.addAction(
            "Usuń folder"
        )  # Połączenie akcji z metodami
        create_folder_action.triggered.connect(lambda: self.create_folder(folder_path))
        rename_folder_action.triggered.connect(lambda: self.rename_folder(folder_path))
        delete_folder_action.triggered.connect(
            lambda: self.delete_folder(
                folder_path, self.parent_window.current_working_directory
            )
        )

        # Wyświetlenie menu
        context_menu.exec(self.folder_tree.mapToGlobal(position))

    def create_folder(self, parent_folder_path: str):
        """
        Tworzy nowy folder w wybranej lokalizacji przy użyciu workera.
        """
        folder_name, ok = QInputDialog.getText(
            self.parent_window, "Nowy folder", "Podaj nazwę folderu:"
        )

        if ok and folder_name:
            # Normalizacja ścieżki i nazwy folderu
            parent_folder_path_norm = normalize_path(parent_folder_path)

            worker = file_operations.create_folder(parent_folder_path_norm, folder_name)

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
                progress_dialog.setAutoClose(
                    True
                )  # Zamknie się automatycznie po zakończeniu
                progress_dialog.setAutoReset(True)  # Zresetuje się po zakończeniu
                progress_dialog.setValue(0)  # Pokaż pasek jako zajęty

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
                        "Tworzenie folderu przerwane.", progress_dialog
                    )
                )

                # Połączenie sygnału anulowania z okna dialogowego z metodą interrupt workera
                progress_dialog.canceled.connect(worker.interrupt)

                # Uruchomienie workera
                QThreadPool.globalInstance().start(worker)
                progress_dialog.show()
            else:
                # Błąd walidacji przed utworzeniem workera (np. zła nazwa, folder nadrzędny nie istnieje)
                # Komunikat powinien być już zalogowany przez file_operations.create_folder
                # Możemy tu wyświetlić ogólny komunikat, jeśli file_operations nie wyświetla własnego
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd inicjalizacji",
                    f"Nie można zainicjować operacji tworzenia folderu '{folder_name}'. Sprawdź logi po szczegóły.",
                    QMessageBox.StandardButton.Ok,
                )

    def _handle_create_folder_finished(
        self, created_folder_path: str, progress_dialog: QProgressDialog
    ):
        logger.info(f"Pomyślnie utworzono folder: {created_folder_path}")
        progress_dialog.accept()  # Zamknij okno dialogowe
        self.model.refresh()  # Odśwież model drzewa
        # Opcjonalnie: zaznacz nowo utworzony folder
        new_index = self.model.index(created_folder_path)
        if new_index.isValid():
            self.folder_tree.setCurrentIndex(new_index)
            self.folder_tree.scrollTo(new_index)
        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie utworzono folder '{os.path.basename(created_folder_path)}'.",
        )

    def _handle_operation_error(
        self, error_message: str, title: str, progress_dialog: QProgressDialog
    ):
        logger.error(f"{title}: {error_message}")
        if progress_dialog.isVisible():
            progress_dialog.reject()  # Zamknij okno dialogowe
        QMessageBox.critical(self.parent_window, title, error_message)
        self.model.refresh()  # Odśwież model na wszelki wypadek

    def _handle_operation_progress(
        self, percent: int, message: str, progress_dialog: QProgressDialog
    ):
        logger.debug(f"Postęp operacji: {percent}% - {message}")
        if progress_dialog.isVisible():
            if progress_dialog.maximum() == 0:  # Jeśli pasek jest nieokreślony
                progress_dialog.setLabelText(message)
            else:
                progress_dialog.setValue(percent)
                progress_dialog.setLabelText(message)

    def _handle_operation_interrupted(
        self, message: str, progress_dialog: QProgressDialog
    ):
        logger.info(f"Operacja przerwana: {message}")
        if progress_dialog.isVisible():
            progress_dialog.reject()  # Zamknij okno dialogowe
        QMessageBox.information(self.parent_window, "Operacja przerwana", message)
        self.model.refresh()  # Odśwież model, aby odzwierciedlić ewentualne częściowe zmiany

    def _handle_rename_folder_finished(
        self, old_path: str, new_path: str, progress_dialog: QProgressDialog
    ):
        logger.info(f"Pomyślnie zmieniono nazwę folderu z '{old_path}' na '{new_path}'")
        progress_dialog.accept()
        self.model.refresh()
        new_index = self.model.index(new_path)
        if new_index.isValid():
            self.folder_tree.setCurrentIndex(new_index)
            self.folder_tree.scrollTo(new_index)
        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie zmieniono nazwę folderu '{os.path.basename(old_path)}' na '{os.path.basename(new_path)}'.",
        )

    def _handle_delete_folder_finished(
        self, deleted_folder_path: str, progress_dialog: QProgressDialog
    ):
        logger.info(f"Pomyślnie usunięto folder: {deleted_folder_path}")
        progress_dialog.accept()
        self.model.refresh()
        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie usunięto folder '{os.path.basename(deleted_folder_path)}'.",
        )
        # Sprawdź, czy current_working_directory w MainWindow nie wskazuje na usunięty folder
        # lub jego podfolder. Jeśli tak, zresetuj current_working_directory.
        if (
            self.parent_window
            and hasattr(self.parent_window, "current_working_directory")
            and self.parent_window.current_working_directory
            and (
                normalize_path(self.parent_window.current_working_directory)
                == normalize_path(deleted_folder_path)
                or normalize_path(
                    self.parent_window.current_working_directory
                ).startswith(normalize_path(deleted_folder_path) + os.sep)
            )
        ):
            logger.info(
                f"Obecny folder roboczy '{self.parent_window.current_working_directory}' znajdował się w usuniętym folderze. Resetowanie."
            )
            # Można ustawić na folder nadrzędny usuniętego folderu lub na root drzewa
            parent_of_deleted = os.path.dirname(deleted_folder_path)
            if (
                os.path.exists(parent_of_deleted)
                and parent_of_deleted != self._main_working_directory
                and parent_of_deleted.startswith(self._main_working_directory)
            ):
                self.parent_window.select_folder(
                    parent_of_deleted
                )  # Metoda w MainWindow do zmiany folderu
            elif self._main_working_directory and os.path.exists(
                self._main_working_directory
            ):
                self.parent_window.select_folder(self._main_working_directory)
            else:  # Fallback, jeśli nawet _main_working_directory nie istnieje
                self.parent_window.select_folder(self.model.rootPath())

    def rename_folder(self, folder_path: str):
        """
        Zmienia nazwę wybranego folderu przy użyciu workera.
        """
        old_name = os.path.basename(folder_path)
        new_name, ok = QInputDialog.getText(
            self.parent_window,
            "Zmień nazwę folderu",
            "Podaj nową nazwę folderu:",
            text=old_name,
        )

        if ok and new_name and new_name != old_name:
            # Normalizacja ścieżki
            folder_path_norm = normalize_path(folder_path)

            worker = file_operations.rename_folder(folder_path_norm, new_name)

            if worker:
                progress_dialog = QProgressDialog(
                    f"Zmiana nazwy folderu '{old_name}' na '{new_name}'...",
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
                    lambda old, new: self._handle_rename_folder_finished(
                        old, new, progress_dialog
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
                worker.signals.interrupted.connect(
                    lambda: self._handle_operation_interrupted(
                        "Zmiana nazwy folderu przerwana.", progress_dialog
                    )
                )
                progress_dialog.canceled.connect(worker.interrupt)

                QThreadPool.globalInstance().start(worker)
                progress_dialog.show()
            else:
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd inicjalizacji",
                    f"Nie można zainicjować operacji zmiany nazwy folderu '{old_name}'. Sprawdź logi po szczegóły.",
                    QMessageBox.StandardButton.Ok,
                )

    def delete_folder(self, folder_path: str, current_working_directory: str):
        """
        Usuwa wybrany folder po potwierdzeniu przez użytkownika, używając workera.
        """
        folder_name = os.path.basename(folder_path)
        folder_path_norm = normalize_path(folder_path)
        current_working_directory_norm = normalize_path(current_working_directory)

        if folder_path_norm == current_working_directory_norm:
            QMessageBox.warning(
                self.parent_window,
                "Nie można usunąć folderu",
                "Nie można usunąć bieżącego folderu roboczego.",
                QMessageBox.StandardButton.Ok,
            )
            return

        if self._main_working_directory and folder_path_norm == normalize_path(
            self._main_working_directory
        ):
            QMessageBox.warning(
                self.parent_window,
                "Nie można usunąć folderu",
                "Nie można usunąć głównego folderu roboczego aplikacji. Zmień najpierw główny folder roboczy.",
                QMessageBox.StandardButton.Ok,
            )
            return

        try:
            has_content = len(os.listdir(folder_path_norm)) > 0
        except OSError as e:
            logger.error(f"Błąd odczytu zawartości folderu {folder_path_norm}: {e}")
            QMessageBox.critical(
                self.parent_window,
                "Błąd odczytu folderu",
                f"Nie można odczytać zawartości folderu '{folder_name}'. Sprawdź uprawnienia i czy folder istnieje.",
            )
            return

        message = (
            f"Czy na pewno chcesz usunąć folder '{folder_name}' "
            f"i całą jego zawartość?\n\nTa operacja jest nieodwracalna!"
            if has_content
            else f"Czy na pewno chcesz usunąć pusty folder '{folder_name}'?"
        )

        reply = QMessageBox.question(
            self.parent_window,
            "Potwierdź usunięcie",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            worker = file_operations.delete_folder(folder_path_norm, has_content)

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
                    lambda path: self._handle_delete_folder_finished(
                        path, progress_dialog
                    )
                )
                worker.signals.error.connect(
                    lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd usuwania folderu", progress_dialog
                    )
                )
                worker.signals.progress.connect(
                    lambda percent, msg: self._handle_operation_progress(
                        percent, msg, progress_dialog
                    )
                )
                worker.signals.interrupted.connect(
                    lambda: self._handle_operation_interrupted(
                        "Usuwanie folderu przerwane.", progress_dialog
                    )
                )
                progress_dialog.canceled.connect(worker.interrupt)

                QThreadPool.globalInstance().start(worker)
                progress_dialog.show()
            else:
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd inicjalizacji",
                    f"Nie można zainicjować operacji usuwania folderu '{folder_name}'. Sprawdź logi po szczegóły.",
                    QMessageBox.StandardButton.Ok,
                )

    def refresh_file_pairs_after_folder_operation(self, current_working_directory: str):
        """
        Odświeża listę par plików po operacjach na folderach.
        """
        if not current_working_directory:
            logging.warning("Brak bieżącego folderu roboczego do odświeżenia.")
            return None

        # Skanuj folder na nowo
        found_pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
            current_working_directory, max_depth=0, pair_strategy="first_match"
        )

        logging.info(f"Odświeżono: {len(found_pairs)} sparowanych plików.")
        logging.info(
            f"Niesparowane: {len(unpaired_archives)} archiwów, "
            f"{len(unpaired_previews)} podglądów."
        )

        return found_pairs, unpaired_archives, unpaired_previews

    def folder_tree_item_clicked(self, index, current_working_directory: str):
        """
        Obsługuje kliknięcie elementu w drzewie folderów.
        """
        folder_path = self.model.filePath(index)
        if folder_path and os.path.isdir(folder_path):
            # Sprawdź, czy nie kliknięto tego samego folderu
            if normalize_path(folder_path) == normalize_path(current_working_directory):
                logging.debug("Kliknięto ten sam folder. Brak akcji.")
                return None

            logging.info(f"Wybrano nowy folder z drzewa: {folder_path}")
            return folder_path
        return None
