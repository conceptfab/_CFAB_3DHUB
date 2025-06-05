"""
Implementacja funkcji obsługi drzewa katalogów i operacji drag & drop dla plików.
"""

import logging
import os

from PyQt6.QtCore import QDir, QItemSelection, QMimeData, Qt
from PyQt6.QtGui import QDrag, QFileSystemModel
from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMenu, QMessageBox, QTreeView

from src.logic import file_operations, metadata_manager


def init_directory_tree(self):
    """
    Inicjalizuje drzewo katalogów po wyborze folderu roboczego.
    """
    if not self.current_working_directory:
        return

    # Ustaw root dla QFileSystemModel na wybrany folder
    self.file_system_model.setRootPath(self.current_working_directory)

    # Ustaw widoczny folder dla QTreeView
    root_index = self.file_system_model.index(self.current_working_directory)
    self.folder_tree.setRootIndex(root_index)

    # Rozwiń pierwszy poziom drzewa
    self.folder_tree.expandToDepth(0)

    # Włącz akceptowanie drop dla drzewa
    self.folder_tree.setAcceptDrops(True)
    self.folder_tree.setDragDropMode(QTreeView.DragDropMode.DropOnly)


def show_folder_context_menu(self, position):
    """
    Wyświetla menu kontekstowe dla drzewa folderów.
    """
    # Pobierz indeks wybranego elementu
    index = self.folder_tree.indexAt(position)
    if not index.isValid():
        return

    # Pobierz ścieżkę do wybranego folderu
    folder_path = self.file_system_model.filePath(index)

    # Tworzenie menu kontekstowego
    context_menu = QMenu()

    # Dodanie akcji do menu
    create_folder_action = QAction("Nowy folder", self)
    rename_folder_action = QAction("Zmień nazwę", self)
    delete_folder_action = QAction("Usuń folder", self)

    # Dodanie akcji do menu
    context_menu.addAction(create_folder_action)
    context_menu.addAction(rename_folder_action)
    context_menu.addSeparator()
    context_menu.addAction(delete_folder_action)

    # Połączenie akcji z metodami
    create_folder_action.triggered.connect(lambda: self._create_folder(folder_path))
    rename_folder_action.triggered.connect(lambda: self._rename_folder(folder_path))
    delete_folder_action.triggered.connect(lambda: self._delete_folder(folder_path))

    # Wyświetlenie menu
    context_menu.exec(self.folder_tree.mapToGlobal(position))


def create_folder(self, parent_folder_path):
    """
    Tworzy nowy folder w wybranej lokalizacji.
    """
    folder_name, ok = QInputDialog.getText(self, "Nowy folder", "Podaj nazwę folderu:")

    if ok and folder_name:
        created_path = file_operations.create_folder(parent_folder_path, folder_name)
        if created_path:
            logging.info(f"Utworzono folder: {created_path}")
            # Odświeżenie widoku drzewa
            self.file_system_model.refresh()
        else:
            QMessageBox.warning(
                self,
                "Błąd tworzenia folderu",
                f"Nie udało się utworzyć folderu '{folder_name}' w '{parent_folder_path}'.",
            )


def rename_folder(self, folder_path):
    """
    Zmienia nazwę wybranego folderu.
    """
    old_name = os.path.basename(folder_path)
    new_name, ok = QInputDialog.getText(
        self, "Zmień nazwę folderu", "Podaj nową nazwę folderu:", text=old_name
    )

    if ok and new_name and new_name != old_name:
        new_path = file_operations.rename_folder(folder_path, new_name)
        if new_path:
            logging.info(f"Zmieniono nazwę folderu z '{folder_path}' na '{new_path}'")
            # Odświeżenie widoku drzewa
            self.file_system_model.refresh()
        else:
            QMessageBox.warning(
                self,
                "Błąd zmiany nazwy",
                f"Nie udało się zmienić nazwy folderu '{old_name}' na '{new_name}'.",
            )


def delete_folder(self, folder_path):
    """
    Usuwa wybrany folder po potwierdzeniu przez użytkownika.
    """
    folder_name = os.path.basename(folder_path)

    # Sprawdź czy folder nie jest folderem roboczym
    if os.path.samefile(folder_path, self.current_working_directory):
        QMessageBox.warning(
            self,
            "Nie można usunąć folderu",
            "Nie można usunąć głównego folderu roboczego.",
        )
        return

    # Pobierz listę plików w folderze
    try:
        has_content = len(os.listdir(folder_path)) > 0
    except Exception:
        has_content = True  # W przypadku błędu, zakładamy, że folder ma zawartość

    # Treść komunikatu potwierdzenia
    if has_content:
        message = (
            f"Czy na pewno chcesz usunąć folder '{folder_name}' i całą jego zawartość?\n"
            "Ta operacja jest nieodwracalna!"
        )
        delete_content = True
    else:
        message = f"Czy na pewno chcesz usunąć pusty folder '{folder_name}'?"
        delete_content = False

    # Potwierdzenie od użytkownika
    reply = QMessageBox.question(
        self,
        "Potwierdź usunięcie",
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )

    if reply == QMessageBox.StandardButton.Yes:
        success = file_operations.delete_folder(folder_path, delete_content)
        if success:
            logging.info(f"Usunięto folder: {folder_path}")
            # Odświeżenie widoku drzewa
            self.file_system_model.refresh()

            # Jeśli usunęliśmy folder, który miał pliki w naszej kolekcji,
            # należy zaktualizować wszystkie pary i widok
            self._refresh_file_pairs_after_folder_operation()
        else:
            QMessageBox.warning(
                self,
                "Błąd usuwania folderu",
                f"Nie udało się usunąć folderu '{folder_name}'.",
            )


def refresh_file_pairs_after_folder_operation(self):
    """
    Odświeża listę par plików po operacjach na folderach.
    """
    # Zapisz aktualne ustawienia filtrów
    current_filters = (
        self.current_filter_criteria.copy()
        if hasattr(self, "current_filter_criteria")
        else {}
    )

    # Skanuj folder na nowo
    self.all_file_pairs = scan_folder_for_pairs(self.current_working_directory)

    # Załaduj metadane
    metadata_manager.apply_metadata_to_file_pairs(
        self.current_working_directory, self.all_file_pairs
    )

    # Zastosuj filtry i zaktualizuj widok
    if current_filters:
        self.current_filter_criteria = current_filters
        self.file_pairs_list = filter_file_pairs(
            self.all_file_pairs, self.current_filter_criteria
        )
        self._update_gallery_view()
    else:
        self._apply_filters_and_update_view()


def folder_tree_item_clicked(self, index):
    """
    Obsługuje kliknięcie folderu w drzewie katalogów.
    Skanuje wybrany folder i wyświetla jego zawartość w galerii.
    """
    if not index.isValid():
        return

    # Pobierz ścieżkę do wybranego folderu
    folder_path = self.file_system_model.filePath(index)
    logging.info(f"Wybrano folder: {folder_path}")

    # Skanuj wybrany folder w poszukiwaniu par plików
    selected_folder_pairs = scan_folder_for_pairs(folder_path)

    if selected_folder_pairs:
        # Zastosuj metadane do znalezionych par
        metadata_manager.apply_metadata_to_file_pairs(
            self.current_working_directory, selected_folder_pairs
        )

        # Aktualizuj listę par plików do wyświetlenia
        self.file_pairs_list = selected_folder_pairs

        # Pokaż panel kontroli rozmiaru
        self.size_control_panel.setVisible(True)

        # Aktualizuj widok galerii
        self._update_gallery_view()

        logging.info(
            f"Wyświetlono {len(selected_folder_pairs)} par plików z folderu: {folder_path}"
        )
    else:
        # Wyczyść galerię, jeśli folder nie zawiera par plików
        self.file_pairs_list = []
        self._clear_gallery()
        self.size_control_panel.setVisible(False)
        logging.info(f"Folder {folder_path} nie zawiera par plików")


def show_file_context_menu(self, file_pair, widget, position):
    """
    Wyświetla menu kontekstowe dla kafelka pliku.
    """
    context_menu = QMenu()

    # Dodanie akcji do menu
    rename_action = QAction("Zmień nazwę", self)
    delete_action = QAction("Usuń parę plików", self)

    # Dodanie akcji do menu
    context_menu.addAction(rename_action)
    context_menu.addSeparator()
    context_menu.addAction(delete_action)

    # Połączenie akcji z metodami
    rename_action.triggered.connect(lambda: self._rename_file_pair(file_pair, widget))
    delete_action.triggered.connect(lambda: self._delete_file_pair(file_pair, widget))

    # Wyświetlenie menu
    context_menu.exec(widget.mapToGlobal(position))


def rename_file_pair(self, file_pair, widget):
    """
    Zmienia nazwę pary plików.
    """
    old_name = file_pair.get_base_name()
    new_name, ok = QInputDialog.getText(
        self,
        "Zmień nazwę pliku",
        "Podaj nową nazwę dla pary plików (bez rozszerzenia):",
        text=old_name,
    )

    if ok and new_name and new_name != old_name:
        if file_pair.rename(new_name):
            logging.info(f"Zmieniono nazwę pary plików z '{old_name}' na '{new_name}'")

            # Zaktualizuj metadane
            metadata_manager.save_metadata(
                self.current_working_directory, self.all_file_pairs
            )

            # Zaktualizuj widget
            widget.update_data(file_pair)
        else:
            QMessageBox.warning(
                self,
                "Błąd zmiany nazwy",
                f"Nie udało się zmienić nazwy pary plików '{old_name}' na '{new_name}'.",
            )


def delete_file_pair(self, file_pair, widget):
    """
    Usuwa parę plików po potwierdzeniu przez użytkownika.
    """
    file_name = file_pair.get_base_name()
    reply = QMessageBox.question(
        self,
        "Potwierdź usunięcie",
        f"Czy na pewno chcesz usunąć parę plików '{file_name}'?\nTa operacja jest nieodwracalna!",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )

    if reply == QMessageBox.StandardButton.Yes:
        if file_pair.delete():
            logging.info(f"Usunięto parę plików: {file_name}")

            # Usuń parę z list
            if file_pair in self.all_file_pairs:
                self.all_file_pairs.remove(file_pair)
            if file_pair in self.file_pairs_list:
                self.file_pairs_list.remove(file_pair)

            # Zaktualizuj metadane
            metadata_manager.save_metadata(
                self.current_working_directory, self.all_file_pairs
            )

            # Usuń widget z layoutu
            self.tiles_layout.removeWidget(widget)
            widget.deleteLater()
            if widget in self.file_tile_widgets:
                self.file_tile_widgets.remove(widget)
        else:
            QMessageBox.warning(
                self,
                "Błąd usuwania plików",
                f"Nie udało się usunąć pary plików '{file_name}'.",
            )
