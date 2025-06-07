"""
Manager operacji na plikach w interfejsie użytkownika.
"""

import logging
import os
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QInputDialog, QListWidget, QMenu, QMessageBox, QWidget

from src.logic import file_operations
from src.models.file_pair import FilePair

logger = logging.getLogger(__name__)


class FileOperationsUI:
    """
    Klasa zarządzająca operacjami na plikach w interfejsie użytkownika.
    """

    def __init__(self, parent_window):
        self.parent_window = parent_window

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
    ) -> Optional[FilePair]:
        """
        Rozpoczyna proces zmiany nazwy dla pary plików.
        """
        current_name = file_pair.get_base_name()
        new_name, ok = QInputDialog.getText(
            self.parent_window,
            "Zmień nazwę",
            "Wprowadź nową nazwę (bez rozszerzenia):",
            text=current_name,
        )

        if ok and new_name and new_name != current_name:
            try:
                # Sprawdź czy funkcja istnieje przed wywołaniem
                if hasattr(file_operations, "rename_file_pair"):
                    new_file_pair = file_operations.rename_file_pair(
                        file_pair, new_name
                    )
                    logging.info(f"Zmieniono nazwę {current_name} na {new_name}.")
                    return new_file_pair
                else:
                    raise NotImplementedError(
                        "Funkcja rename_file_pair nie została zaimplementowana"
                    )

            except FileExistsError:
                QMessageBox.critical(
                    self.parent_window,
                    "Błąd",
                    f"Plik o nazwie '{new_name}' już istnieje.",
                )
            except Exception as e:
                QMessageBox.critical(
                    self.parent_window,
                    "Błąd zmiany nazwy",
                    f"Wystąpił nieoczekiwany błąd: {e}",
                )
                logging.error(e)
        return None

    def delete_file_pair(self, file_pair: FilePair, widget: QWidget):
        """
        Usuwa parę plików (archiwum i podgląd) po potwierdzeniu.
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
            try:
                # Sprawdź czy funkcja istnieje przed wywołaniem
                if hasattr(file_operations, "delete_file_pair"):
                    file_operations.delete_file_pair(file_pair)
                    logging.info(f"Usunięto pliki dla {file_pair.get_base_name()}.")
                    return True
                else:
                    raise NotImplementedError(
                        "Funkcja delete_file_pair nie została zaimplementowana"
                    )

            except Exception as e:
                QMessageBox.critical(
                    self.parent_window,
                    "Błąd usuwania",
                    f"Wystąpił błąd podczas usuwania plików: {e}",
                )
                logging.error(e)
        return False

    def handle_manual_pairing(
        self, unpaired_archives_list: QListWidget, unpaired_previews_list: QListWidget
    ):
        """
        Obsługuje logikę ręcznego parowania plików zaznaczonych na listach.
        """
        selected_archives = unpaired_archives_list.selectedItems()
        selected_previews = unpaired_previews_list.selectedItems()

        if not (len(selected_archives) == 1 and len(selected_previews) == 1):
            QMessageBox.warning(
                self.parent_window,
                "Błąd parowania",
                "Proszę zaznaczyć dokładnie jeden plik archiwum "
                "i jeden plik podglądu.",
            )
            return None

        archive_item = selected_archives[0]
        preview_item = selected_previews[0]

        archive_path = archive_item.data(Qt.ItemDataRole.UserRole)
        preview_path = preview_item.data(Qt.ItemDataRole.UserRole)

        try:
            # Sprawdź czy funkcja istnieje przed wywołaniem
            if hasattr(file_operations, "create_pair_from_files"):
                new_pair = file_operations.create_pair_from_files(
                    archive_path, preview_path
                )
                logging.info(
                    f"Ręcznie sparowano: {new_pair.get_archive_path()} "
                    f"z {new_pair.get_preview_path()}"
                )

                QMessageBox.information(
                    self.parent_window,
                    "Sukces",
                    f"Pomyślnie sparowano pliki dla " f"'{new_pair.get_base_name()}'.",
                )
                return new_pair
            else:
                raise NotImplementedError(
                    "Funkcja create_pair_from_files nie została " "zaimplementowana"
                )

        except Exception as e:
            error_message = f"Błąd podczas ręcznego parowania: {e}"
            logging.error(error_message)
            QMessageBox.critical(self.parent_window, "Błąd", error_message)

        return None

    def handle_drop_on_folder(self, urls: List, target_folder_path: str):
        """
        Obsługuje upuszczenie plików na folder w drzewie.
        """
        file_paths = [url.toLocalFile() for url in urls]
        logging.debug(f"Upuszczono pliki {file_paths} na folder {target_folder_path}")

        reply = QMessageBox.question(
            self.parent_window,
            "Przenoszenie plików",
            f"Czy chcesz przenieść {len(file_paths)} elementów "
            f"do folderu '{os.path.basename(target_folder_path)}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply == QMessageBox.StandardButton.Yes:
            logging.info("Rozpoczynanie przenoszenia plików...")
            # TODO: Implementacja przenoszenia plików
            return True
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
    ) -> Optional[FilePair]:
        """
        Obsługuje przenoszenie pary plików do nowego folderu z obsługą UI.

        Args:
            file_pair_to_move: Para plików do przeniesienia.
            target_folder_path: Ścieżka do folderu docelowego.

        Returns:
            Nowy obiekt FilePair z zaktualizowanymi ścieżkami po pomyślnym przeniesieniu,
            lub None w przypadku niepowodzenia.
        """
        if not file_pair_to_move or not target_folder_path:
            logger.warning(
                "Próba przeniesienia nieprawidłowej pary plików lub do nieprawidłowej lokalizacji."
            )
            return None

        original_archive_path = file_pair_to_move.archive_path
        original_preview_path = file_pair_to_move.preview_path

        try:
            logger.info(
                f"Próba przeniesienia pary plików: '{file_pair_to_move.base_name}' "
                f"do folderu: '{target_folder_path}'"
            )

            # Sprawdzenie, czy folder docelowy jest taki sam jak folder źródłowy
            source_folder_path = os.path.dirname(file_pair_to_move.archive_path)
            if os.path.abspath(source_folder_path) == os.path.abspath(
                target_folder_path
            ):
                QMessageBox.information(
                    self.parent_window,
                    "Informacja",
                    "Plik już znajduje się w folderze docelowym.",
                )
                return (
                    file_pair_to_move  # Zwracamy oryginalny obiekt, bo nie było zmiany
                )

            new_file_pair = file_operations.move_file_pair(
                file_pair_to_move, target_folder_path
            )

            QMessageBox.information(
                self.parent_window,
                "Sukces",
                f"Pomyślnie przeniesiono '{new_file_pair.base_name}' "
                f"do '{target_folder_path}'.",
            )
            logger.info(
                f"Pomyślnie przeniesiono parę plików. Nowe ścieżki: "
                f"Archiwum: '{new_file_pair.archive_path}', "
                f"Podgląd: '{new_file_pair.preview_path}'"
            )
            return new_file_pair

        except FileExistsError:
            error_msg = (
                f"Plik o tej samej nazwie już istnieje w folderze docelowym: "
                f"'{target_folder_path}'. Przenoszenie nie powiodło się."
            )
            QMessageBox.warning(self.parent_window, "Błąd przenoszenia", error_msg)
            logger.warning(
                f"{error_msg} Oryginalne ścieżki: Archiwum: '{original_archive_path}', Podgląd: '{original_preview_path}'"
            )
            return None
        except OSError as e:
            error_msg = (
                f"Wystąpił błąd systemu plików podczas przenoszenia "
                f"'{file_pair_to_move.base_name}' do '{target_folder_path}':\n{e}"
            )
            QMessageBox.critical(self.parent_window, "Błąd systemu plików", error_msg)
            logger.error(
                f"{error_msg} Oryginalne ścieżki: Archiwum: '{original_archive_path}', Podgląd: '{original_preview_path}'",
                exc_info=True,
            )
            return None
        except Exception as e:
            error_msg = (
                f"Wystąpił nieoczekiwany błąd podczas przenoszenia "
                f"'{file_pair_to_move.base_name}':\n{e}"
            )
            QMessageBox.critical(self.parent_window, "Nieoczekiwany błąd", error_msg)
            logger.error(
                f"{error_msg} Oryginalne ścieżki: Archiwum: '{original_archive_path}', Podgląd: '{original_preview_path}'",
                exc_info=True,
            )
            return None
