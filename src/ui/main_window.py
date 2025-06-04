"""
Główne okno aplikacji.
"""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji CFAB_3DHUB.
    """

    def __init__(self):
        """
        Inicjalizuje główne okno aplikacji.
        """
        super().__init__()

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
        Ta metoda będzie rozszerzana w kolejnych etapach.
        """
        # W Etapie 0 okno będzie puste, elementy zostaną dodane w Etapie 1.B
        pass
