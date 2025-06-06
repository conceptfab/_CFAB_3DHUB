"""
Manager operacji na plikach w interfejsie użytkownika.
"""

import logging
import os
from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QInputDialog, QListWidget, QMenu, QMessageBox, QWidget

from src.logic import file_operations
from src.models.file_pair import FilePair


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

    def rename_file_pair(self, file_pair: FilePair, widget: QWidget):
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
