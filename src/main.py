"""
Główny plik uruchomieniowy aplikacji CFAB_3DHUB.
"""

import logging
import sys

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow
from utils.logging_config import setup_logging


def main():
    """
    Punkt wejścia do aplikacji.
    Inicjalizuje system logowania, tworzy i wyświetla główne okno aplikacji.
    """
    # Konfiguracja systemu logowania
    setup_logging()

    # Tworzenie instancji aplikacji QT
    app = QApplication(sys.argv)

    # Tworzenie i wyświetlanie głównego okna
    window = MainWindow()
    window.show()

    # Uruchomienie pętli zdarzeń aplikacji
    logging.info("Aplikacja CFAB_3DHUB uruchomiona")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
