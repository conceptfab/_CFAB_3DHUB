"""
Główne okno aplikacji.
"""

import logging
import os

# from PyQt6.QtCore import Qt # Usunięto nieużywany import
from PyQt6.QtWidgets import (
    QFileDialog,
    QListWidget,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.logic.scanner import scan_folder_for_pairs
from src.models.file_pair import FilePair


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji CFAB_3DHUB.
    """

    def __init__(self):
        """
        Inicjalizuje główne okno aplikacji.
        """
        super().__init__()

        self.current_working_directory = None
        self.file_pairs_list: list[FilePair] = []  # Sparowane pliki

        # Konfiguracja okna
        self.setWindowTitle("CFAB_3DHUB")
        self.setMinimumSize(800, 600)

        # Centralny widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Główny layout
        self.main_layout = QVBoxLayout(self.central_widget)

        # Inicjalizacja interfejsu użytkownika
        self._init_ui()

        logging.info("Główne okno aplikacji zostało zainicjalizowane")

    def _init_ui(self):
        """
        Inicjalizuje elementy interfejsu użytkownika.
        """
        self.select_folder_button = QPushButton("Wybierz Folder Roboczy")
        self.select_folder_button.clicked.connect(self._select_working_directory)
        self.main_layout.addWidget(self.select_folder_button)

        self.file_list_widget = QListWidget()
        self.main_layout.addWidget(self.file_list_widget)

    def _select_working_directory(self):
        """
        Otwiera dialog wyboru folderu i inicjuje skanowanie.
        """
        logging.debug("Dialog wyboru folderu roboczego.")
        if self.current_working_directory:
            initial_dir = self.current_working_directory
        else:
            initial_dir = os.path.expanduser("~")

        directory = QFileDialog.getExistingDirectory(
            self, "Wybierz Folder Roboczy", initial_dir
        )

        if directory:
            self.current_working_directory = directory
            logging.info(f"Wybrano folder: {self.current_working_directory}")
            base_folder_name = os.path.basename(self.current_working_directory)
            self.setWindowTitle(f"CFAB_3DHUB - {base_folder_name}")

            try:
                self.file_pairs_list = scan_folder_for_pairs(
                    self.current_working_directory
                )
                self._update_file_list_widget()
                logging.info(f"Znaleziono par: {len(self.file_pairs_list)}.")
            except Exception as e:
                err_msg = f"Błąd skanowania '{base_folder_name}': {e}"
                logging.error(err_msg)
                self.file_pairs_list = []
                self._update_file_list_widget()
        else:
            logging.info("Anulowano wybór folderu.")

    def _update_file_list_widget(self):
        """
        Aktualizuje QListWidget nazwami bazowymi sparowanych plików.
        """
        self.file_list_widget.clear()
        if not self.file_pairs_list:
            logging.debug("Lista par pusta, QListWidget pusty.")
            return

        for pair in self.file_pairs_list:
            try:
                base_name = pair.get_base_name()
                self.file_list_widget.addItem(base_name)
                logging.debug(f"Dodano do listy: {base_name}")
            except Exception as e:
                arc_path = os.path.basename(pair.get_archive_path())
                prev_path = os.path.basename(pair.get_preview_path())
                logging.error(f"Błąd UI dla: {arc_path}/{prev_path}: {e}")
