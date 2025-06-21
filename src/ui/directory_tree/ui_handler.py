"""
Handler obsługi UI dla drzewa katalogów.
Wydzielony z głównego managera w ramach refaktoryzacji.
"""

import logging
import os
import subprocess
from typing import TYPE_CHECKING

from PyQt6.QtCore import QModelIndex
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMenu,
    QMessageBox,
    QPushButton,
    QToolBar,
    QWidget,
)

if TYPE_CHECKING:
    from .manager import DirectoryTreeManager

logger = logging.getLogger(__name__)


class DirectoryTreeUIHandler:
    """
    Handler obsługi UI dla drzewa katalogów.
    Wydzielony z głównego managera dla lepszej separacji odpowiedzialności.
    """

    def __init__(self, manager: "DirectoryTreeManager"):
        self.manager = manager
        self.parent_window = manager.parent_window
        self.folder_tree = manager.folder_tree

    def setup_expand_collapse_controls(self) -> QWidget:
        """Dodaje kontrolki zwijania/rozwijania folderów."""
        controls_widget = QWidget()
        layout = QHBoxLayout()

        toolbar = QToolBar()
        expand_all_action = toolbar.addAction("Rozwiń wszystkie")
        collapse_all_action = toolbar.addAction("Zwiń wszystkie")

        expand_all_action.triggered.connect(self.folder_tree.expandAll)
        collapse_all_action.triggered.connect(self.folder_tree.collapseAll)

        layout.addWidget(toolbar)
        controls_widget.setLayout(layout)

        return controls_widget

    def create_expand_collapse_buttons(self):
        """
        Tworzy przyciski do rozwijania i zwijania wszystkich folderów.

        Returns:
            tuple: (przycisk_rozwiń, przycisk_zwiń)
        """
        expand_button = QPushButton("Rozwiń")
        collapse_button = QPushButton("Zwiń")

        expand_button.clicked.connect(self.folder_tree.expandAll)
        collapse_button.clicked.connect(self.folder_tree.collapseAll)

        # Ustaw style dla przycisków - bardziej kompaktowe
        button_style = """
            QPushButton {
                background-color: #2D2D30;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
                padding: 2px 4px;
                font-size: 10px;
                min-height: 20px;
                max-height: 20px;
            }
            QPushButton:hover {
                background-color: #3E3E42;
                border: 1px solid #007ACC;
            }
            QPushButton:pressed {
                background-color: #007ACC;
                color: white;
            }
        """
        expand_button.setStyleSheet(button_style)
        collapse_button.setStyleSheet(button_style)

        # Ustaw kompaktowe rozmiary
        expand_button.setFixedHeight(20)
        collapse_button.setFixedHeight(20)

        return expand_button, collapse_button

    def open_folder_in_explorer(self, folder_path: str):
        """Otwiera folder w eksploratorze Windows."""
        try:
            logging.debug(f"Explorer: Opening folder: '{folder_path}'")

            # Sprawdź czy folder istnieje
            if not os.path.exists(folder_path):
                logging.error(
                    f"EKSPLORATOR: BŁĄD - Folder nie istnieje: '{folder_path}'"
                )
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd",
                    f"Folder nie istnieje:\n{folder_path}",
                )
                return

            if not os.path.isdir(folder_path):
                logging.error(
                    f"EKSPLORATOR: BŁĄD - Ścieżka nie jest folderem: '{folder_path}'"
                )
                QMessageBox.warning(
                    self.parent_window,
                    "Błąd",
                    f"Ścieżka nie jest folderem:\n{folder_path}",
                )
                return

            # Normalizuj ścieżkę do formatu Windows
            normalized_path = os.path.normpath(folder_path)
            logging.debug(f"Explorer: Normalized path: '{normalized_path}'")

            # Użyj alternatywnych metod wywołania explorera
            import sys

            if sys.platform == "win32":
                # Metoda 1: Przez os.startfile - najbardziej niezawodna dla Windows
                try:
                    os.startfile(normalized_path)
                    logging.info(
                        f"EKSPLORATOR: SUKCES (os.startfile) - Otwarto folder: {normalized_path}"
                    )
                    return
                except Exception as e1:
                    logging.warning(f"Explorer: os.startfile failed: {e1}")

                # Metoda 2: Przez subprocess z argumentami w liście
                try:
                    subprocess.Popen(["explorer", normalized_path])
                    logging.info(
                        f"EKSPLORATOR: SUKCES (subprocess lista) - Otwarto folder: {normalized_path}"
                    )
                    return
                except Exception as e2:
                    logging.warning(
                        f"EKSPLORATOR: subprocess z listą nie zadziałało: {e2}"
                    )

                # Metoda 3: Przez subprocess z shell=True
                try:
                    subprocess.Popen(f'explorer "{normalized_path}"', shell=True)
                    logging.info(
                        f"EKSPLORATOR: SUKCES (subprocess shell) - Otwarto folder: {normalized_path}"
                    )
                    return
                except Exception as e3:
                    logging.error(
                        f"EKSPLORATOR: subprocess z shell nie zadziałało: {e3}"
                    )
            else:
                logging.error(
                    f"EKSPLORATOR: Nieobsługiwany system operacyjny: {sys.platform}"
                )

        except Exception as e:
            logging.error(f"Explorer: CRITICAL ERROR opening explorer: {e}")
            QMessageBox.warning(
                self.parent_window,
                "Błąd",
                f"Nie można otworzyć folderu w eksploratorze:\n{e}",
            )

    def show_folder_context_menu(self, position):
        """Wyświetla rozszerzone menu kontekstowe dla drzewa folderów."""
        logging.info(
            f"MENU_KONTEKSTOWE: Wyświetlanie menu kontekstowego na pozycji: {position}"
        )

        # Pobierz indeks wybranego elementu (używamy proxy model)
        proxy_index = self.folder_tree.indexAt(position)
        if not proxy_index.isValid():
            logging.warning(
                f"MENU_KONTEKSTOWE: BŁĄD - Nieprawidłowy proxy_index na pozycji: {position}"
            )
            return

        # Mapuj z proxy na źródłowy model
        source_index = self.manager.proxy_model.mapToSource(proxy_index)
        if not source_index.isValid():
            logging.warning(
                f"MENU_KONTEKSTOWE: BŁĄD - Nieprawidłowy source_index dla proxy: {proxy_index}"
            )
            return

        # Pobierz ścieżkę do wybranego folderu
        folder_path = self.manager.model.filePath(source_index)

        # Sprawdź czy folder istnieje i jest folderem
        if not os.path.exists(folder_path):
            logging.error(
                f"MENU_KONTEKSTOWE: BŁĄD - Folder nie istnieje: '{folder_path}'"
            )
            return

        if not os.path.isdir(folder_path):
            logging.error(
                f"MENU_KONTEKSTOWE: BŁĄD - Ścieżka nie jest folderem: '{folder_path}'"
            )
            return

        # Tworzenie menu kontekstowego
        context_menu = QMenu()

        # NOWA FUNKCJONALNOŚĆ: Otwórz w eksploratorze
        open_explorer_action = context_menu.addAction("Otwórz w eksploratorze")
        open_explorer_action.triggered.connect(
            lambda: self.open_folder_in_explorer(folder_path)
        )

        # NOWA FUNKCJONALNOŚĆ: Statystyki folderu
        stats_action = context_menu.addAction("Pokaż statystyki")
        stats_action.triggered.connect(lambda: self.manager.stats_manager.show_folder_statistics(folder_path))

        # NOWA FUNKCJONALNOŚĆ: Wymuś przeliczenie statystyk
        recalc_stats_action = context_menu.addAction("Przelicz statystyki")
        recalc_stats_action.triggered.connect(
            lambda: self.manager.stats_manager._force_recalculate_folder_stats(folder_path)
        )

        # NOWA FUNKCJONALNOŚĆ: Przelicz wszystkie statystyki
        recalc_all_action = context_menu.addAction("Przelicz wszystkie statystyki")
        recalc_all_action.triggered.connect(
            lambda: self.manager.stats_manager.force_calculate_all_stats_async()
        )

        context_menu.addSeparator()

        # Istniejące akcje
        create_folder_action = context_menu.addAction("Nowy folder")
        rename_folder_action = context_menu.addAction("Zmień nazwę")
        delete_folder_action = context_menu.addAction("Usuń folder")

        # Połączenie akcji z metodami
        create_folder_action.triggered.connect(lambda: self.manager.operations_manager.create_folder(folder_path))
        rename_folder_action.triggered.connect(lambda: self.manager.operations_manager.rename_folder(folder_path))
        delete_folder_action.triggered.connect(
            lambda: self.manager.operations_manager.delete_folder(
                folder_path, self.parent_window.controller.current_directory
            )
        )

        # Wyświetlenie menu
        context_menu.exec(self.folder_tree.mapToGlobal(position))

    def folder_tree_item_clicked(self, proxy_index, current_working_directory: str):
        """Obsługuje kliknięcie elementu w drzewie folderów."""
        try:
            if not proxy_index.isValid():
                return

            # Mapuj proxy index na source index
            source_index = self.manager.proxy_model.mapToSource(proxy_index)
            if not source_index.isValid():
                return

            # Pobierz ścieżkę folderu
            folder_path = self.manager.model.filePath(source_index)
            if folder_path and os.path.isdir(folder_path):
                # Sygnalizuj głównemu oknu zmianę katalogu
                if hasattr(self.parent_window, "change_directory"):
                    self.parent_window.change_directory(folder_path)
        except Exception as e:
            logger.error(f"Błąd obsługi kliknięcia folderu: {e}")

    def refresh_file_pairs_after_folder_operation(self, current_working_directory: str):
        """Odświeża listę par plików po operacji na folderze."""
        try:
            # Sygnalizuj głównemu oknu że powinno odświeżyć pary plików
            if hasattr(self.parent_window, "refresh_file_pairs"):
                self.parent_window.refresh_file_pairs()
        except Exception as e:
            logger.error(f"Błąd odświeżania par plików: {e}")