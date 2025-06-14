"""
Główny moduł aplikacji CFAB_3DHUB.
Zawiera funkcję main() inicjalizującą i uruchamiającą aplikację.
Uruchamiany powinien być przez zewnętrzny skrypt (np. run_app.py),
który odpowiednio konfiguruje sys.path.
"""

import logging
import os
import sys
import traceback

# Importy z bibliotek zewnętrznych i standardowych powinny być pierwsze
from PyQt6.QtWidgets import QApplication, QMessageBox

# Importy z własnych modułów projektu (teraz absolutne od 'src')
from src.ui.main_window.main_window import MainWindow
from src.utils.logging_config import setup_logging


# Globalny handler wyjątków niezłapanych
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """
    Handler dla niezłapanych wyjątków, które mogą wystąpić poza blokiem try-except.
    Loguje błąd i wyświetla komunikat użytkownikowi, jeśli to możliwe.

    Args:
        exc_type: Typ wyjątku
        exc_value: Wartość/komunikat wyjątku
        exc_traceback: Traceback wyjątku
    """
    # Formatowanie wyjątku do logu
    exception_str = "".join(
        traceback.format_exception(exc_type, exc_value, exc_traceback)
    )

    # Próba logowania (może być niedostępne, jeśli inicjalizacja logów zawiodła)
    try:
        logging.critical(f"Niezłapany wyjątek: {exception_str}")
    except Exception:
        pass  # Jeśli logging nie jest dostępny, pomijamy

    # Wyświetlenie okna dialogowego z błędem, jeśli QApplication już istnieje
    try:
        if QApplication.instance():
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle("Nieoczekiwany błąd")
            error_dialog.setText("Wystąpił nieoczekiwany błąd w aplikacji.")
            error_dialog.setInformativeText(f"Szczegóły: {str(exc_value)}")
            error_dialog.setDetailedText(exception_str)
            error_dialog.exec()
    except Exception:
        # Jeśli QApplication nie jest dostępne, wyświetlamy w konsoli
        print(f"BŁĄD KRYTYCZNY: {exception_str}")


# Ustawienie globalnego handlera wyjątków
sys.excepthook = global_exception_handler


def main(style_sheet=""):
    """
    Punkt wejścia do aplikacji (wywoływany przez run_app.py).
    Inicjalizuje system logowania, tworzy i wyświetla główne okno aplikacji.

    Args:
        style_sheet (str): Opcjonalny arkusz stylów QSS do zastosowania w aplikacji
    """
    # Konfiguracja systemu logowania
    try:
        setup_logging()

        # Blok globalnej obsługi wyjątków - ochrona głównego cyklu aplikacji
        try:
            # Tworzenie instancji aplikacji QT
            app = QApplication(
                sys.argv
            )  # Zastosowanie przekazanego arkusza stylów QSS (jeśli istnieje)
            if style_sheet:
                logging.info(f"Stosowanie arkusza stylów ({len(style_sheet)} bajtów)")
                app.setStyleSheet(style_sheet)

            try:
                # Tworzenie i wyświetlanie głównego okna
                window = MainWindow()
                window.show()

                # Uruchomienie pętli zdarzeń aplikacji
                logging.info("Aplikacja CFAB_3DHUB uruchomiona poprzez main()")
                return sys.exit(app.exec())
            except Exception as e:
                logging.critical(
                    f"Błąd podczas inicjalizacji głównego okna aplikacji: {str(e)}"
                )
                from PyQt6.QtWidgets import QMessageBox

                error_dialog = QMessageBox()
                error_dialog.setIcon(QMessageBox.Icon.Critical)
                error_dialog.setWindowTitle("Błąd krytyczny")
                error_dialog.setText("Wystąpił błąd podczas uruchamiania aplikacji.")
                error_dialog.setInformativeText(f"Szczegóły: {str(e)}")
                error_dialog.setDetailedText(f"Pełny komunikat błędu:\n{str(e)}")
                error_dialog.exec()
                return sys.exit(1)

        except Exception as e:
            logging.critical(f"Krytyczny błąd inicjalizacji aplikacji Qt: {str(e)}")
            print(f"BŁĄD KRYTYCZNY: Nie można uruchomić aplikacji: {str(e)}")
            return sys.exit(2)

    except Exception as e:
        # W przypadku błędu w setup_logging(), nie możemy użyć logging, więc używamy print
        print(f"BŁĄD KRYTYCZNY: Nie można zainicjalizować systemu logowania: {str(e)}")
        return sys.exit(3)


# Ten blok określa, co powinno się stać, gdy plik jest uruchamiany bezpośrednio
if __name__ == "__main__":
    # Bezpośrednie uruchomienie tego pliku (np. python src/main.py)
    # nie zadziała poprawnie z powodu braku konfiguracji sys.path.
    # Zalecane jest uruchamianie przez run_app.py w głównym katalogu projektu.
    print("BŁĄD: Nie można uruchomić aplikacji bezpośrednio z tego pliku.")
    print("Proszę uruchomić aplikację przez run_app.py z głównego katalogu projektu.")
    print("Przykład: python run_app.py")

    # Sprawdzamy, czy użytkownik mimo wszystko chce kontynuować
    try:
        response = input("Czy mimo to chcesz spróbować uruchomić aplikację? [t/N]: ")
        if response.lower() == "t":
            print("Próba uruchomienia aplikacji... (mogą wystąpić błędy importu)")
            main()
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nPrzerwano uruchamianie.")
        sys.exit(1)
