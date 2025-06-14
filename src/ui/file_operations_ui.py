"""
Manager operacji na plikach w interfejsie użytkownika.
"""

import logging
import os
from typing import List, Optional

from PyQt6.QtCore import Qt, QThreadPool, QTimer  # Dodano QThreadPool i QTimer
from PyQt6.QtWidgets import QProgressDialog  # Dodano QProgressDialog
from PyQt6.QtWidgets import QInputDialog, QListWidget, QMenu, QMessageBox, QWidget

from src.logic import file_operations

# Dodajemy importy workerów z file_operations, jeśli jeszcze nie ma
from src.logic.file_operations import (
    DeleteFilePairWorker,
    ManuallyPairFilesWorker,
    MoveFilePairWorker,
    RenameFilePairWorker,
)
from src.logic.scanner import collect_files, create_file_pairs
from src.models.file_pair import FilePair
from src.ui.delegates.workers import BulkMoveWorker
from src.utils.path_utils import normalize_path  # Dodano import normalize_path

logger = logging.getLogger(__name__)


class FileOperationsUI:
    """
    Klasa zarządzająca operacjami na plikach w interfejsie użytkownika.
    """

    def __init__(self, parent_window):
        self.parent_window = parent_window

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
        menu = QMenu(self.parent_window)

        # Akcja zmiany nazwy
        rename_action = QMenu.addAction(menu, "Zmień nazwę")
        rename_action.triggered.connect(
            lambda: self.rename_file_pair(file_pair, widget)
        )

        # Akcja usunięcia
        delete_action = QMenu.addAction(menu, "Usuń")
        delete_action.triggered.connect(
            lambda: self.delete_file_pair(file_pair, widget)
        )

        # Wyświetlenie menu w odpowiedniej pozycji
        # Sprawdź czy position to QContextMenuEvent czy QPoint
        if hasattr(position, "pos"):
            # position to QContextMenuEvent
            menu.exec(widget.mapToGlobal(position.pos()))
        else:
            # position to QPoint
            menu.exec(widget.mapToGlobal(position))

    def rename_file_pair(
        self, file_pair: FilePair, widget: QWidget
    ) -> None:  # Zmieniono zwracany typ na None, bo worker obsługuje wynik
        """
        Rozpoczyna proces zmiany nazwy dla pary plików przy użyciu workera.
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
                progress_dialog = QProgressDialog(
                    f"Zmiana nazwy pliku '{current_name}' na '{new_name}'...",
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
                    lambda new_fp: self._handle_rename_file_pair_finished(
                        file_pair, new_fp, progress_dialog
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
        # Usunięto return None, metoda nie zwraca już bezpośrednio wyniku

    def _handle_rename_file_pair_finished(
        self,
        old_file_pair: FilePair,
        new_file_pair: FilePair,
        progress_dialog: QProgressDialog,
    ):
        logger.info(
            f"Pomyślnie zmieniono nazwę pliku z '{old_file_pair.get_base_name()}' na '{new_file_pair.get_base_name()}'.",
        )
        if progress_dialog.isVisible():
            progress_dialog.accept()

        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie zmieniono nazwę pliku '{old_file_pair.get_base_name()}' na '{new_file_pair.get_base_name()}'.",
        )
        # Odśwież widoki w MainWindow
        if hasattr(self.parent_window, "refresh_all_views") and callable(
            self.parent_window.refresh_all_views
        ):
            self.parent_window.refresh_all_views(new_selection=new_file_pair)

    def delete_file_pair(
        self, file_pair: FilePair, widget: QWidget
    ) -> None:  # Zmieniono zwracany typ
        """
        Usuwa parę plików (archiwum i podgląd) po potwierdzeniu, używając workera.
        """
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
                    lambda deleted_files: self._handle_delete_file_pair_finished(
                        file_pair, progress_dialog
                    )
                )
                worker.signals.error.connect(
                    lambda err_msg: self._handle_operation_error(
                        err_msg, "Błąd usuwania plików", progress_dialog
                    )
                )
                worker.signals.progress.connect(
                    lambda percent, msg: self._handle_operation_progress(
                        percent, msg, progress_dialog
                    )
                )
                worker.signals.interrupted.connect(
                    lambda: self._handle_operation_interrupted(
                        "Usuwanie plików przerwane.", progress_dialog
                    )
                )
                progress_dialog.canceled.connect(worker.interrupt)

                QThreadPool.globalInstance().start(worker)
                progress_dialog.show()
            else:
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd inicjalizacji",
                    f"Nie można zainicjować operacji usuwania plików dla '{file_pair.get_base_name()}'. Sprawdź logi.",
                )
        # Usunięto return False/True

    def _handle_delete_file_pair_finished(
        self, file_pair: FilePair, progress_dialog: QProgressDialog
    ):
        logger.info(f"Pomyślnie usunięto pliki dla {file_pair.get_base_name()}.")
        if progress_dialog.isVisible():
            progress_dialog.accept()

        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie usunięto pliki dla '{file_pair.get_base_name()}'.",
        )
        if hasattr(self.parent_window, "refresh_all_views") and callable(
            self.parent_window.refresh_all_views
        ):
            self.parent_window.refresh_all_views()

    def handle_manual_pairing(
        self,
        unpaired_archives_list: QListWidget,
        unpaired_previews_list: QListWidget,
        current_working_directory: str,
    ) -> None:  # Zmieniono zwracany typ
        """
        Obsługuje ręczne parowanie plików.
        """
        selected_archives = unpaired_archives_list.selectedItems()
        selected_previews = unpaired_previews_list.selectedItems()

        if not current_working_directory:
            QMessageBox.critical(
                self.parent_window,
                "Błąd konfiguracji",
                "Nie można uzyskać ścieżki bieżącego katalogu roboczego. "
                "Operacja parowania przerwana.",
            )
            return

        if len(selected_archives) != 1 or len(selected_previews) != 1:
            QMessageBox.warning(
                self.parent_window,
                "Wymagane zaznaczenie",
                "Proszę zaznaczyć dokładnie jeden plik archiwum "
                "i jeden plik podglądu.",
            )
            return

        archive_path = selected_archives[0].data(Qt.ItemDataRole.UserRole)
        preview_path = selected_previews[0].data(Qt.ItemDataRole.UserRole)

        worker = file_operations.manually_pair_files(
            archive_path, preview_path, current_working_directory
        )

        if worker:
            base_archive_name = os.path.basename(archive_path)
            base_preview_name = os.path.basename(preview_path)
            progress_dialog = QProgressDialog(
                f"Parowanie '{base_archive_name}' z '{base_preview_name}'...",
                "Anuluj",
                0,
                0,
                self.parent_window,
            )
            progress_dialog.setWindowTitle("Ręczne parowanie plików")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setAutoClose(True)
            progress_dialog.setAutoReset(True)
            progress_dialog.setValue(0)

            worker.signals.finished.connect(
                lambda new_fp: self._handle_manual_pairing_finished(
                    new_fp, progress_dialog
                )
            )
            worker.signals.error.connect(
                lambda err_msg: self._handle_operation_error(
                    err_msg, "Błąd ręcznego parowania", progress_dialog
                )
            )
            worker.signals.progress.connect(
                lambda percent, msg: self._handle_operation_progress(
                    percent, msg, progress_dialog
                )
            )
            worker.signals.interrupted.connect(
                lambda: self._handle_operation_interrupted(
                    "Ręczne parowanie przerwane.", progress_dialog
                )
            )
            progress_dialog.canceled.connect(worker.interrupt)

            QThreadPool.globalInstance().start(worker)
            progress_dialog.show()
        else:
            QMessageBox.warning(
                self.parent_window,
                "Błąd inicjalizacji",
                "Nie można zainicjować operacji ręcznego parowania. Sprawdź logi.",
            )  # Usunięto return None

    def _handle_manual_pairing_finished(
        self, new_file_pair: FilePair, progress_dialog: QProgressDialog
    ):
        logger.info(f"Pomyślnie sparowano pliki: {new_file_pair}")
        if progress_dialog.isVisible():
            progress_dialog.accept()

        QMessageBox.information(
            self.parent_window, "Sukces", f"Pomyślnie sparowano plik: {new_file_pair}"
        )

        try:

            if (
                hasattr(self.parent_window, "controller")
                and self.parent_window.controller
            ):
                # Dodaj nową parę do listy sparowanych w thread-safe sposób
                self.parent_window.controller.current_file_pairs.append(new_file_pair)

                # Usuń pliki z list niesparowanych w thread-safe sposób
                archive_path = new_file_pair.archive_path
                preview_path = new_file_pair.preview_path

                try:
                    if archive_path in self.parent_window.controller.unpaired_archives:
                        self.parent_window.controller.unpaired_archives.remove(
                            archive_path
                        )
                except ValueError:
                    logger.debug(f"Archive już usunięte z unpaired: {archive_path}")

                try:
                    if preview_path in self.parent_window.controller.unpaired_previews:
                        self.parent_window.controller.unpaired_previews.remove(
                            preview_path
                        )
                except ValueError:
                    logger.debug(f"Preview już usunięte z unpaired: {preview_path}")

            # NAPRAWKA CRASH: Użyj QTimer.singleShot dla thread-safe UI update
            # Opóźnij odświeżenie UI aby uniknąć crash podczas worker callback
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(
                100, lambda: self._delayed_refresh_after_pairing(new_file_pair)
            )

        except Exception as e:
            logger.error(f"KRYTYCZNY BŁĄD podczas finalizacji parowania: {e}")
            # Nie wywołuj refresh_all_views w przypadku błędu - może crashować
            logger.warning(
                "Pomijam refresh_all_views z powodu błędu - aplikacja powinna zostać stabilna"
            )

    def _delayed_refresh_after_pairing(self, new_file_pair: FilePair):
        """
        NAPRAWKA CRASH: Thread-safe opóźnione odświeżenie po parowaniu.
        Wykonywaną w głównym wątku UI przez QTimer.singleShot.
        """
        try:
            logger.debug("Rozpoczynam opóźnione odświeżenie po parowaniu")

            # Sprawdź czy aplikacja nadal działa
            if not hasattr(self.parent_window, "refresh_all_views"):
                logger.warning(
                    "Parent window nie ma refresh_all_views - pomijam odświeżenie"
                )
                return

            if not callable(self.parent_window.refresh_all_views):
                logger.warning(
                    "refresh_all_views nie jest wywoływalne - pomijam odświeżenie"
                )
                return

            # NAPRAWKA: Nie przekazuj new_file_pair do refresh_all_views - może powodować crash
            # Zamiast tego użyj prostego odświeżenia bez selekcji
            self.parent_window.refresh_all_views()
            logger.debug("Odświeżenie po parowaniu zakończone pomyślnie")

        except Exception as e:
            logger.error(f"BŁĄD podczas opóźnionego odświeżenia: {e}")
            # Ostatnia deska ratunku - podstawowe odświeżenie
            try:
                if hasattr(self.parent_window, "_update_gallery_view"):
                    self.parent_window._update_gallery_view()
                if hasattr(self.parent_window, "_update_unpaired_files_direct"):
                    self.parent_window._update_unpaired_files_direct()
                logger.debug("Użyto fallback odświeżenia")
            except Exception as fallback_error:
                logger.error(f"Również fallback odświeżenie crashuje: {fallback_error}")

    def handle_drop_on_folder(self, urls: List, target_folder_path: str):
        """
        Obsługuje upuszczenie plików na folder w drzewie.

        Args:
            urls: Lista QUrl obiektów reprezentujących pliki do przeniesienia
            target_folder_path: Ścieżka do folderu docelowego
        """
        file_paths = [url.toLocalFile() for url in urls]
        logging.info(f"Dropped {len(file_paths)} files on folder {target_folder_path}")
        logging.debug(f"Files: {file_paths}")

        # Bezpośrednio rozpocznij przenoszenie bez pytania
        logging.info("Starting file move operation...")
        # Informuj o rozpoczęciu w pasku statusu
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(
                0, f"Przenoszenie {len(file_paths)} plików..."
            )

        try:
            # Zbierz wszystkie pliki z podanych ścieżek
            all_files = []
            for file_path in file_paths:
                if os.path.isfile(file_path):
                    all_files.append(file_path)
                    logging.debug(f"Added file: {file_path}")
                elif os.path.isdir(file_path):
                    logging.debug(f"Found folder, scanning contents: {file_path}")
                    # Jeśli to folder, zbierz pliki z niego
                    dir_file_map = collect_files(file_path, max_depth=1)
                    for files_list in dir_file_map.values():
                        all_files.extend(files_list)
                        logging.debug(f"Added files from folder: {files_list}")
                else:
                    logging.warning(f"Skipped non-existent item: {file_path}")

            logging.info(f"Found total {len(all_files)} files to move")

            if not all_files:
                if hasattr(self.parent_window, "_show_progress"):
                    self.parent_window._show_progress(
                        100, "Nie znaleziono plików do przeniesienia"
                    )
                logging.warning("ERROR - No files found to move")
                return False

            # Utwórz tymczasowy file_map dla algorytmu create_file_pairs
            temp_file_map = {}
            for file_path in all_files:
                dir_path = os.path.dirname(file_path)
                if dir_path not in temp_file_map:
                    temp_file_map[dir_path] = []
                temp_file_map[dir_path].append(file_path)

            logging.debug(f"Created file_map for {len(temp_file_map)} directories")

            # Utwórz pary plików używając strategii "best_match"
            file_pairs, _ = create_file_pairs(
                temp_file_map,
                target_folder_path,  # Użyj target_folder jako base_directory
                pair_strategy="best_match",
            )

            logging.info(f"Created {len(file_pairs)} file pairs")

            if not file_pairs:
                # Jeśli nie udało się utworzyć par, spróbuj przenieść pliki indywidualnie
                # (to może się zdarzyć dla pojedynczych plików bez pary)
                logging.warning("Failed to create file pairs. Moving individual files.")
                self._move_individual_files(all_files, target_folder_path)
                logging.info("SUCCESS - Moved files individually")
                return True

            # Użyj BulkMoveWorker do przeniesienia par plików
            logging.info(f"Starting BulkMoveWorker for {len(file_pairs)} pairs")
            self._move_file_pairs_bulk(file_pairs, target_folder_path)
            logging.info("SUCCESS - Started file pairs move operation")
            return True

        except Exception as e:
            logging.error(f"ERROR during file move operation: {e}", exc_info=True)
            if hasattr(self.parent_window, "_show_progress"):
                self.parent_window._show_progress(100, f"Błąd przenoszenia: {str(e)}")
            return False

    def show_unpaired_context_menu(
        self, position, list_widget: QListWidget, list_type: str
    ):
        """
        Wyświetla menu kontekstowe dla listy niesparowanych plików.
        """
        item = list_widget.itemAt(position)
        if not item:
            return

        menu = QMenu()
        open_action = menu.addAction("Otwórz lokalizację pliku")
        action = menu.exec(list_widget.mapToGlobal(position))

        if action == open_action:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            # Sprawdź czy funkcja istnieje przed wywołaniem
            if hasattr(file_operations, "open_file_location"):
                file_operations.open_file_location(os.path.dirname(file_path))
            else:
                logging.warning(
                    "Funkcja open_file_location nie została zaimplementowana"
                )

    def move_file_pair_ui(
        self, file_pair_to_move: FilePair, target_folder_path: str
    ) -> None:  # Zmieniono zwracany typ
        """
        Obsługuje przenoszenie pary plików do nowego folderu z obsługą UI, używając workera.

        Args:
            file_pair_to_move: Para plików do przeniesienia.
            target_folder_path: Ścieżka do folderu docelowego.

        Returns:
            None, ponieważ operacja jest asynchroniczna.
        """
        if not file_pair_to_move or not target_folder_path:
            logger.warning(
                "Próba przeniesienia nieprawidłowej pary plików lub do nieprawidłowej lokalizacji."
            )
            # Można rozważyć wyświetlenie QMessageBox tutaj, jeśli to błąd użytkownika
            return

        # Sprawdzenie, czy folder docelowy jest taki sam jak folder źródłowy
        source_folder_path = os.path.dirname(file_pair_to_move.archive_path)
        if normalize_path(source_folder_path) == normalize_path(target_folder_path):
            QMessageBox.information(
                self.parent_window,
                "Informacja",
                "Plik już znajduje się w folderze docelowym.",
            )
            return

        worker = file_operations.move_file_pair(file_pair_to_move, target_folder_path)

        if worker:
            base_name = file_pair_to_move.get_base_name()
            target_dir_name = os.path.basename(normalize_path(target_folder_path))
            progress_dialog = QProgressDialog(
                f"Przenoszenie '{base_name}' do folderu '{target_dir_name}'...",
                "Anuluj",
                0,
                0,
                self.parent_window,
            )
            progress_dialog.setWindowTitle("Przenoszenie plików")
            progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
            progress_dialog.setAutoClose(True)
            progress_dialog.setAutoReset(True)
            progress_dialog.setValue(0)

            # Przechwycenie file_pair_to_move dla użycia w lambdzie
            original_file_pair_for_handler = file_pair_to_move
            worker.signals.finished.connect(
                lambda new_fp: self._handle_move_file_pair_finished(  # Poprawiona lambda
                    original_file_pair_for_handler,
                    new_fp,
                    target_folder_path,
                    progress_dialog,
                )
            )
            worker.signals.error.connect(
                lambda err_msg: self._handle_operation_error(
                    err_msg, "Błąd przenoszenia plików", progress_dialog
                )
            )
            worker.signals.progress.connect(
                lambda percent, msg: self._handle_operation_progress(
                    percent, msg, progress_dialog
                )
            )
            worker.signals.interrupted.connect(
                lambda: self._handle_operation_interrupted(
                    "Przenoszenie plików przerwane.", progress_dialog
                )
            )
            progress_dialog.canceled.connect(worker.interrupt)

            QThreadPool.globalInstance().start(worker)
            progress_dialog.show()
        else:
            QMessageBox.warning(
                self.parent_window,
                "Błąd inicjalizacji",
                f"Nie można zainicjować operacji przenoszenia dla '{file_pair_to_move.get_base_name()}'. Sprawdź logi.",
            )

    def _handle_move_file_pair_finished(
        self,
        old_file_pair: FilePair,
        new_file_pair: FilePair,
        target_folder_path: str,
        progress_dialog: QProgressDialog,
    ):
        logger.info(
            f"Pomyślnie przeniesiono parę plików '{old_file_pair.base_name}' do '{target_folder_path}'. "
            f"Nowe ścieżki: Archiwum: '{new_file_pair.archive_path}', Podgląd: '{new_file_pair.preview_path}'"
        )
        if progress_dialog.isVisible():
            progress_dialog.accept()

        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie przeniesiono '{new_file_pair.base_name}' do '{os.path.basename(normalize_path(target_folder_path))}'.",
        )
        if hasattr(self.parent_window, "refresh_all_views") and callable(
            self.parent_window.refresh_all_views
        ):
            # NAPRAWKA DRAG&DROP PERFORMANCE: Użyj opóźnionego odświeżania dla pojedynczych par
            # żeby nie blokować UI podczas drag&drop
            QTimer.singleShot(500, self.parent_window.refresh_all_views)
            # Jeśli MainWindow ma metodę do zmiany folderu i chcemy na niego przejść:
            # self.parent_window.select_folder(target_folder_path)
            # Lub jeśli chcemy zaznaczyć przeniesiony element, jeśli jest w bieżącym widoku:
            # current_view_path = self.parent_window.current_working_directory
            # if normalize_path(os.path.dirname(new_file_pair.archive_path)) == normalize_path(current_view_path):
            #     self.parent_window.refresh_all_views(new_selection=new_file_pair)
            # else:
            #     self.parent_window.refresh_all_views() # Odśwież stary folder
            #     # Można też rozważyć zmianę folderu na docelowy i zaznaczenie tam elementu

    def _move_individual_files(self, files: list[str], target_folder_path: str):
        """
        Przenosi pojedyncze pliki do folderu docelowego.

        Args:
            files: Lista ścieżek plików do przeniesienia
            target_folder_path: Ścieżka do folderu docelowego
        """
        import shutil

        logging.info(f"Moving {len(files)} individual files")
        logging.debug(f"Target folder: {target_folder_path}")

        try:
            for i, file_path in enumerate(files):
                filename = os.path.basename(file_path)
                destination_path = os.path.join(target_folder_path, filename)

                logging.debug(
                    f"Moving {i+1}/{len(files)}: {file_path} -> {destination_path}"
                )

                # Informuj o postępie w pasku statusu
                if hasattr(self.parent_window, "_show_progress"):
                    progress_percent = int((i / len(files)) * 100)
                    self.parent_window._show_progress(
                        progress_percent, f"Przenoszenie: {filename}"
                    )

                try:
                    shutil.move(file_path, destination_path)
                    logging.debug(f"Moved: {file_path} -> {destination_path}")
                except Exception as e:
                    logging.error(f"Error moving {file_path}: {e}")
                    # Usunięto QMessageBox.warning - błędy tylko w logach            # Zakończenie operacji
            if hasattr(self.parent_window, "_show_progress"):
                self.parent_window._show_progress(
                    100, f"Przeniesiono {len(files)} plików"
                )

            logging.info(f"Individual files move completed - moved {len(files)} files")

        except Exception as e:
            logging.error(f"Error during individual files move: {e}")
            if hasattr(self.parent_window, "_show_progress"):
                self.parent_window._show_progress(100, f"Błąd: {str(e)}")

        # NAPRAWKA DRAG&DROP PERFORMANCE: Odśwież widoki tylko jeśli nie ma bulk move
        # Dla bulk move _handle_bulk_move_finished() już obsługuje odświeżanie
        if hasattr(self.parent_window, "refresh_all_views") and callable(
            self.parent_window.refresh_all_views
        ):
            logging.debug("Refreshing views after individual file move")
            self.parent_window.refresh_all_views()

    def _move_file_pairs_bulk(
        self, file_pairs: list[FilePair], target_folder_path: str
    ):
        """
        Przenosi pary plików używając BulkMoveWorker.

        Args:
            file_pairs: Lista par plików do przeniesienia
            target_folder_path: Ścieżka do folderu docelowego
        """
        if not file_pairs:
            logging.warning("move_file_pairs_bulk called with empty file list")
            return

        logging.info(f"Starting bulk move for {len(file_pairs)} file pairs")
        logging.debug(f"Target folder: {target_folder_path}")

        # Utwórz workera do masowego przenoszenia
        worker = BulkMoveWorker(file_pairs, target_folder_path)

        # Informuj o rozpoczęciu w pasku statusu
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(
                0, f"Przenoszenie {len(file_pairs)} par plików..."
            )

        # Podłącz sygnały workera
        worker.signals.finished.connect(
            lambda result: self._handle_bulk_move_finished(result)
        )
        worker.signals.error.connect(
            lambda err_msg: self._handle_bulk_move_error(err_msg)
        )
        worker.signals.progress.connect(
            lambda percent, msg: self._handle_bulk_move_progress(percent, msg)
        )

        logging.debug("Starting BulkMoveWorker...")
        # Uruchom workera
        QThreadPool.globalInstance().start(worker)
        logging.debug("BulkMoveWorker started successfully")

    def _handle_bulk_move_finished(self, result):
        """
        Obsługuje zakończenie masowego przenoszenia par plików.

        Args:
            result: Słownik z wynikami operacji zawierający moved_pairs, detailed_errors, skipped_files i summary
        """
        # Wyciągnij dane z wyniku
        if isinstance(result, dict):
            moved_pairs = result.get("moved_pairs", [])
            detailed_errors = result.get("detailed_errors", [])
            skipped_files = result.get("skipped_files", [])
            summary = result.get("summary", {})
        else:
            # Fallback dla starych workerów
            moved_pairs = result if isinstance(result, list) else []
            detailed_errors = []
            skipped_files = []
            summary = {}

        logging.info(
            f"Bulk move finished - successfully moved {len(moved_pairs)} file pairs"
        )

        # Informuj o zakończeniu w pasku statusu i ukryj po chwili
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(
                100, f"Przeniesiono {len(moved_pairs)} par plików"
            )
        if hasattr(self.parent_window, "_hide_progress"):
            self.parent_window._hide_progress()

        # Pokaż szczegółowy raport błędów jeśli wystąpiły
        if detailed_errors or skipped_files:
            self._show_detailed_move_report(
                moved_pairs, detailed_errors, skipped_files, summary
            )

        # 🔧 NAPRAWKA DRAG&DROP: Usuń przeniesione pary z struktur danych głównego okna
        # i odśwież folder źródłowy żeby usunąć pliki które już nie istnieją na dysku
        if hasattr(self.parent_window, "controller") and moved_pairs:
            # Usuń przeniesione pary z głównej listy
            for file_pair in moved_pairs:
                if file_pair in self.parent_window.controller.current_file_pairs:
                    self.parent_window.controller.current_file_pairs.remove(file_pair)
                # Usuń z zaznaczonych kafelków jeśli istnieje
                if hasattr(self.parent_window, "controller"):
                    self.parent_window.controller.selected_tiles.discard(file_pair)

            logging.debug(f"Removed {len(moved_pairs)} pairs from current_file_pairs")

            # Odśwież folder źródłowy używając tego samego mechanizmu co w głównym oknie
            if hasattr(self.parent_window, "_refresh_source_folder_after_move"):
                logger.debug("Odświeżanie folderu źródłowego po drag&drop")
                self.parent_window._refresh_source_folder_after_move()
            else:
                logger.warning(
                    "🔧 Drag&drop: Brak metody _refresh_source_folder_after_move - używam fallback BEZ resetu drzewa"
                )
                # Fallback - tylko odśwież widok BEZ resetowania drzewa
                if hasattr(self.parent_window, "refresh_all_views"):
                    self.parent_window.refresh_all_views()

        # NAPRAWKA DRAG&DROP PERFORMANCE: NIE wywołuj refresh_all_views() tutaj!
        # _refresh_source_folder_after_move() już odświeża widoki przez change_directory()
        # Podwójne odświeżanie spowalnia drag&drop ekstremalnie po refaktoryzacji MetadataManager
        logger.debug(
            "Pomijam refresh_all_views() - _refresh_source_folder_after_move() już odświeża widoki"
        )

    def _handle_bulk_move_error(self, error_message: str):
        """
        Obsługuje błędy podczas masowego przenoszenia.

        Args:
            error_message: Komunikat błędu
        """
        logging.error(f"Bulk move error: {error_message}")
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(100, f"Błąd: {error_message}")
        if hasattr(self.parent_window, "_hide_progress"):
            self.parent_window._hide_progress()

    def _handle_bulk_move_progress(self, percent: int, message: str):
        """
        Obsługuje postęp masowego przenoszenia.

        Args:
            percent: Procent ukończenia
            message: Komunikat postępu
        """
        logging.debug(f"Bulk move progress {percent}%: {message}")
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(percent, message)

    def _show_detailed_move_report(
        self, moved_pairs, detailed_errors, skipped_files, summary
    ):
        """
        Wyświetla szczegółowy raport z operacji przenoszenia plików.

        Args:
            moved_pairs: Lista pomyślnie przeniesionych par
            detailed_errors: Lista szczegółowych błędów
            skipped_files: Lista pominiętych plików
            summary: Podsumowanie operacji
        """
        from PyQt6.QtWidgets import (
            QDialog,
            QHBoxLayout,
            QLabel,
            QPushButton,
            QTabWidget,
            QTextEdit,
            QVBoxLayout,
            QWidget,
        )

        dialog = QDialog(self.parent_window)
        dialog.setWindowTitle("Raport przenoszenia plików")
        dialog.setMinimumSize(800, 600)
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        # Podsumowanie
        summary_text = f"""
<h3>Podsumowanie operacji przenoszenia</h3>
<p><b>Żądano przeniesienia:</b> {summary.get('total_requested', 0)} par plików</p>
<p><b>Pomyślnie przeniesiono:</b> {summary.get('successfully_moved', 0)} par plików</p>
<p><b>Błędy:</b> {summary.get('errors', 0)} plików</p>
<p><b>Pominięto:</b> {summary.get('skipped', 0)} plików</p>
        """

        summary_label = QLabel(summary_text)
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        # Zakładki z szczegółami
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # Zakładka z błędami
        if detailed_errors:
            errors_widget = QWidget()
            errors_layout = QVBoxLayout(errors_widget)

            errors_text = QTextEdit()
            errors_text.setReadOnly(True)

            error_content = "<h4>Szczegółowe błędy:</h4>\n"

            # Grupuj błędy według typu
            error_groups = {}
            for error in detailed_errors:
                error_type = error.get("error_type", "NIEZNANY")
                if error_type not in error_groups:
                    error_groups[error_type] = []
                error_groups[error_type].append(error)

            for error_type, errors in error_groups.items():
                error_content += (
                    f"<h5>{error_type} ({len(errors)} plików):</h5>\n<ul>\n"
                )
                for error in errors:
                    file_pair = error.get("file_pair", "Nieznany")
                    file_type = error.get("file_type", "nieznany")
                    file_path = error.get("file_path", "nieznana ścieżka")
                    error_msg = error.get("error", "nieznany błąd")

                    error_content += f"<li><b>Para:</b> {file_pair} ({file_type})<br/>"
                    error_content += f"<b>Plik:</b> {file_path}<br/>"
                    error_content += f"<b>Błąd:</b> {error_msg}</li>\n"
                error_content += "</ul>\n"

            errors_text.setHtml(error_content)
            errors_layout.addWidget(errors_text)
            tab_widget.addTab(errors_widget, f"Błędy ({len(detailed_errors)})")

        # Zakładka z pominięciami
        if skipped_files:
            skipped_widget = QWidget()
            skipped_layout = QVBoxLayout(skipped_widget)

            skipped_text = QTextEdit()
            skipped_text.setReadOnly(True)

            skipped_content = "<h4>Pominięte pliki:</h4>\n<ul>\n"
            for skipped in skipped_files:
                file_pair = skipped.get("file_pair", "Nieznany")
                file_type = skipped.get("file_type", "nieznany")
                file_path = skipped.get("file_path", "nieznana ścieżka")
                target_path = skipped.get("target_path", "nieznana ścieżka docelowa")
                reason = skipped.get("reason", "nieznany powód")

                skipped_content += f"<li><b>Para:</b> {file_pair} ({file_type})<br/>"
                skipped_content += f"<b>Plik źródłowy:</b> {file_path}<br/>"
                skipped_content += f"<b>Plik docelowy:</b> {target_path}<br/>"
                skipped_content += f"<b>Powód:</b> {reason}</li>\n"
            skipped_content += "</ul>\n"

            skipped_text.setHtml(skipped_content)
            skipped_layout.addWidget(skipped_text)
            tab_widget.addTab(skipped_widget, f"Pominięte ({len(skipped_files)})")

        # Zakładka z sukcesami
        if moved_pairs:
            success_widget = QWidget()
            success_layout = QVBoxLayout(success_widget)

            success_text = QTextEdit()
            success_text.setReadOnly(True)

            success_content = "<h4>Pomyślnie przeniesione pary:</h4>\n<ul>\n"
            for pair in moved_pairs:
                pair_name = (
                    pair.get_base_name()
                    if hasattr(pair, "get_base_name")
                    else "Nieznana para"
                )
                archive_path = getattr(pair, "archive_path", "brak")
                preview_path = getattr(pair, "preview_path", "brak")

                success_content += f"<li><b>Para:</b> {pair_name}<br/>"
                success_content += f"<b>Archiwum:</b> {archive_path}<br/>"
                success_content += f"<b>Podgląd:</b> {preview_path}</li>\n"
            success_content += "</ul>\n"

            success_text.setHtml(success_content)
            success_layout.addWidget(success_text)
            tab_widget.addTab(success_widget, f"Sukces ({len(moved_pairs)})")

        # Przyciski
        button_layout = QHBoxLayout()

        close_button = QPushButton("Zamknij")
        close_button.clicked.connect(dialog.accept)
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

        # Pokaż dialog
        dialog.exec()
