"""
Główny moduł aplikacji CFAB_3DHUB.
Zawiera funkcję main() inicjalizującą i uruchamiającą aplikację.
Uruchamiany powinien być przez zewnętrzny skrypt (np. run_app.py),
który odpowiednio konfiguruje sys.path.
"""

import logging
import sys

# Importy z bibliotek zewnętrznych i standardowych powinny być pierwsze
from PyQt6.QtWidgets import QApplication

# Importy z własnych modułów projektu (teraz absolutne od 'src')
from src.ui.main_window import MainWindow
from src.utils.logging_config import setup_logging


def main():
    """
    Punkt wejścia do aplikacji (wywoływany przez run_app.py).
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
    logging.info("Aplikacja CFAB_3DHUB uruchomiona poprzez main()")
    sys.exit(app.exec())


# Ten blok jest mniej istotny, gdy używamy run_app.py
# Można go zostawić dla ewentualnych testów lub usunąć.
if __name__ == "__main__":
    # Bezpośrednie uruchomienie tego pliku (np. python src/main.py)
    # prawdopodobnie nie zadziała poprawnie z powodu braku konfiguracji sys.path.
    # Zalecane jest uruchamianie przez run_app.py w głównym katalogu projektu.
    print("UWAGA: Uruchom przez run_app.py z głównego katalogu projektu.")
    print("       Bezpośrednie odpalenie grozi błędami importu.")
    # Na razie zostawiamy tylko ostrzeżenie.
    pass
