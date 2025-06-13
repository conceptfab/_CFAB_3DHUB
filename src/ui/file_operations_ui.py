"""
Manager operacji na plikach w interfejsie użytkownika.
"""

import logging
import os
from typing import List, Optional

from PyQt6.QtCore import QThreadPool  # Dodano QThreadPool
from PyQt6.QtCore import Qt
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
            worker = file_operations.rename_file_pair(file_pair, new_name)

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
                    lambda old_fp, new_fp: self._handle_rename_file_pair_finished(
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
                    lambda fp: self._handle_delete_file_pair_finished(
                        fp, progress_dialog
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
        self, deleted_file_pair: FilePair, progress_dialog: QProgressDialog
    ):
        logger.info(
            f"Pomyślnie usunięto pliki dla {deleted_file_pair.get_base_name()}."
        )
        if progress_dialog.isVisible():
            progress_dialog.accept()

        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie usunięto pliki dla '{deleted_file_pair.get_base_name()}'.",
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

        # NAPRAWKA: Dodaj nową parę do kontrolera i usuń pliki z list niesparowanych
        if hasattr(self.parent_window, 'controller') and self.parent_window.controller:
            # Dodaj nową parę do listy sparowanych
            self.parent_window.controller.current_file_pairs.append(new_file_pair)
            
            # Usuń pliki z list niesparowanych
            archive_path = new_file_pair.archive_path
            preview_path = new_file_pair.preview_path
            
            if archive_path in self.parent_window.controller.unpaired_archives:
                self.parent_window.controller.unpaired_archives.remove(archive_path)
                
            if preview_path in self.parent_window.controller.unpaired_previews:
                self.parent_window.controller.unpaired_previews.remove(preview_path)

        # Wymuś pełne odświeżenie aby przeładować dane
        if hasattr(self.parent_window, "force_full_refresh") and callable(
            self.parent_window.force_full_refresh
        ):
            self.parent_window.force_full_refresh()

    def handle_drop_on_folder(self, urls: List, target_folder_path: str):
        """
        Obsługuje upuszczenie plików na folder w drzewie.

        Args:
            urls: Lista QUrl obiektów reprezentujących pliki do przeniesienia
            target_folder_path: Ścieżka do folderu docelowego
        """
        file_paths = [url.toLocalFile() for url in urls]
        logging.info(
            f"🚀 DRAG&DROP: Upuszczono {len(file_paths)} plików na folder {target_folder_path}"
        )
        logging.info(f"🚀 DRAG&DROP: Pliki: {file_paths}")

        # Bezpośrednio rozpocznij przenoszenie bez pytania
        logging.info("🚀 DRAG&DROP: Rozpoczynanie przenoszenia plików...")
        # Informuj o rozpoczęciu w pasku statusu
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(
                0, f"Przenoszenie {len(file_paths)} elementów..."
            )

        try:
            # Zbierz wszystkie pliki z podanych ścieżek
            all_files = []
            for file_path in file_paths:
                if os.path.isfile(file_path):
                    all_files.append(file_path)
                    logging.debug(f"🚀 DRAG&DROP: Dodano plik: {file_path}")
                elif os.path.isdir(file_path):
                    logging.debug(
                        f"🚀 DRAG&DROP: Znaleziono folder, skanuje zawartość: {file_path}"
                    )
                    # Jeśli to folder, zbierz pliki z niego
                    dir_file_map = collect_files(file_path, max_depth=1)
                    for files_list in dir_file_map.values():
                        all_files.extend(files_list)
                        logging.debug(
                            f"🚀 DRAG&DROP: Dodano pliki z folderu: {files_list}"
                        )
                else:
                    logging.warning(
                        f"🚀 DRAG&DROP: Pominięto nieistniejący element: {file_path}"
                    )

            logging.info(
                f"🚀 DRAG&DROP: Znaleziono łącznie {len(all_files)} plików do przeniesienia"
            )

            if not all_files:
                if hasattr(self.parent_window, "_show_progress"):
                    self.parent_window._show_progress(
                        100, "Nie znaleziono plików do przeniesienia"
                    )
                logging.warning(
                    "🚀 DRAG&DROP: BŁĄD - Nie znaleziono plików do przeniesienia"
                )
                return False

            # Utwórz tymczasowy file_map dla algorytmu create_file_pairs
            temp_file_map = {}
            for file_path in all_files:
                dir_path = os.path.dirname(file_path)
                if dir_path not in temp_file_map:
                    temp_file_map[dir_path] = []
                temp_file_map[dir_path].append(file_path)

            logging.info(
                f"🚀 DRAG&DROP: Utworzono file_map dla {len(temp_file_map)} katalogów"
            )

            # Utwórz pary plików używając strategii "best_match"
            file_pairs, _ = create_file_pairs(
                temp_file_map,
                target_folder_path,  # Użyj target_folder jako base_directory
                pair_strategy="best_match",
            )

            logging.info(f"🚀 DRAG&DROP: Utworzono {len(file_pairs)} par plików")

            if not file_pairs:
                # Jeśli nie udało się utworzyć par, spróbuj przenieść pliki indywidualnie
                # (to może się zdarzyć dla pojedynczych plików bez pary)
                logging.warning(
                    "🚀 DRAG&DROP: Nie udało się utworzyć par plików. Przenoszenie pojedynczych plików."
                )
                self._move_individual_files(all_files, target_folder_path)
                logging.info("🚀 DRAG&DROP: SUKCES - Przeniesiono pliki indywidualnie")
                return True

            # Użyj BulkMoveWorker do przeniesienia par plików
            logging.info(
                f"🚀 DRAG&DROP: Uruchamianie BulkMoveWorker dla {len(file_pairs)} par"
            )
            self._move_file_pairs_bulk(file_pairs, target_folder_path)
            logging.info("🚀 DRAG&DROP: SUKCES - Uruchomiono przenoszenie par plików")
            return True

        except Exception as e:
            logging.error(
                f"🚀 DRAG&DROP: BŁĄD podczas przenoszenia plików: {e}", exc_info=True
            )
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
            # Po przeniesieniu, chcemy odświeżyć widok, ale nowy element może być w innym folderze,
            # więc niekoniecznie chcemy go zaznaczać, chyba że logika aplikacji tego wymaga.
            # Na razie proste odświeżenie.
            self.parent_window.refresh_all_views()
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

        logging.info(
            f"🚀 DRAG&DROP: _move_individual_files uruchomiona dla {len(files)} plików"
        )
        logging.info(f"🚀 DRAG&DROP: Folder docelowy: {target_folder_path}")

        try:
            for i, file_path in enumerate(files):
                filename = os.path.basename(file_path)
                destination_path = os.path.join(target_folder_path, filename)

                logging.debug(
                    f"🚀 DRAG&DROP: Przenoszenie {i+1}/{len(files)}: {file_path} -> {destination_path}"
                )

                # Informuj o postępie w pasku statusu
                if hasattr(self.parent_window, "_show_progress"):
                    progress_percent = int((i / len(files)) * 100)
                    self.parent_window._show_progress(
                        progress_percent, f"Przenoszenie: {filename}"
                    )

                try:
                    shutil.move(file_path, destination_path)
                    logging.debug(
                        f"🚀 DRAG&DROP: Przeniesiono: {file_path} -> {destination_path}"
                    )
                except Exception as e:
                    logging.error(f"🚀 DRAG&DROP: Błąd przenoszenia {file_path}: {e}")
                    # Usunięto QMessageBox.warning - błędy tylko w logach            # Zakończenie operacji
            if hasattr(self.parent_window, "_show_progress"):
                self.parent_window._show_progress(
                    100, f"Przeniesiono {len(files)} plików"
                )

            logging.info(
                f"🚀 DRAG&DROP: _move_individual_files ZAKOŃCZONA - przeniesiono {len(files)} plików"
            )

        except Exception as e:
            logging.error(f"🚀 DRAG&DROP: Błąd podczas przenoszenia plików: {e}")
            if hasattr(self.parent_window, "_show_progress"):
                self.parent_window._show_progress(100, f"Błąd: {str(e)}")

        # Odśwież widoki po przeniesieniu
        if hasattr(self.parent_window, "refresh_all_views") and callable(
            self.parent_window.refresh_all_views
        ):
            logging.info("🚀 DRAG&DROP: Odświeżanie widoków po przeniesieniu plików")
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
            logging.warning(
                "🚀 DRAG&DROP: _move_file_pairs_bulk wywołana z pustą listą plików"
            )
            return

        logging.info(
            f"🚀 DRAG&DROP: _move_file_pairs_bulk uruchomiona dla {len(file_pairs)} par plików"
        )
        logging.info(f"🚀 DRAG&DROP: Folder docelowy: {target_folder_path}")

        # Utwórz workera do masowego przenoszenia
        worker = BulkMoveWorker(file_pairs, target_folder_path)

        # Informuj o rozpoczęciu w pasku statusu
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(
                0, f"Przenoszenie {len(file_pairs)} par plików..."
            )

        # Podłącz sygnały workera
        worker.signals.finished.connect(
            lambda moved_pairs: self._handle_bulk_move_finished(moved_pairs)
        )
        worker.signals.error.connect(
            lambda err_msg: self._handle_bulk_move_error(err_msg)
        )
        worker.signals.progress.connect(
            lambda percent, msg: self._handle_bulk_move_progress(percent, msg)
        )

        logging.info("🚀 DRAG&DROP: BulkMoveWorker uruchamiany...")
        # Uruchom workera
        QThreadPool.globalInstance().start(worker)
        logging.info("🚀 DRAG&DROP: BulkMoveWorker uruchomiony pomyślnie")

    def _handle_bulk_move_finished(self, moved_pairs: list[FilePair]):
        """
        Obsługuje zakończenie masowego przenoszenia par plików.

        Args:
            moved_pairs: Lista pomyślnie przeniesionych par
        """
        logging.info(
            f"🚀 DRAG&DROP: _handle_bulk_move_finished - pomyślnie przeniesiono {len(moved_pairs)} par plików"
        )

        # Informuj o zakończeniu w pasku statusu i ukryj po chwili
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(
                100, f"Przeniesiono {len(moved_pairs)} par plików"
            )
        if hasattr(self.parent_window, "_hide_progress"):
            self.parent_window._hide_progress()

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

            logging.info(
                f"🚀 DRAG&DROP: Usunięto {len(moved_pairs)} par z current_file_pairs"
            )

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

        # Odśwież widoki (ale już po usunięciu przeniesionych plików ze struktury danych)
        if hasattr(self.parent_window, "refresh_all_views") and callable(
            self.parent_window.refresh_all_views
        ):
            self.parent_window.refresh_all_views()

    def _handle_bulk_move_error(self, error_message: str):
        """
        Obsługuje błędy podczas masowego przenoszenia.

        Args:
            error_message: Komunikat błędu
        """
        logging.error(f"🚀 DRAG&DROP: Błąd masowego przenoszenia: {error_message}")
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
        logging.debug(f"🚀 DRAG&DROP: Postęp {percent}%: {message}")
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(percent, message)
