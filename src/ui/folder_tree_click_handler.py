"""
Funkcja obsługująca kliknięcie folderu w drzewie katalogów.
"""

import logging

from src.logic import metadata_manager
from src.logic.scanner import scan_folder_for_pairs


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
