"""
Główny moduł aplikacji CFAB_3DHUB.
Zawiera funkcję main() inicjalizującą i uruchamiającą aplikację.
"""

import logging
import sys
import traceback
from typing import Optional

from PyQt6.QtWidgets import QApplication, QMessageBox

from src.factories.worker_factory import UIWorkerFactory

# Konfiguracja centralnej worker factory
from src.logic.file_ops_components import configure_worker_factory
from src.ui.main_window.main_window import MainWindow
from src.utils.logging_config import setup_logging

# Stałe kodów wyjścia
EXIT_SUCCESS = 0
EXIT_GENERAL_ERROR = 1
EXIT_QT_ERROR = 2
EXIT_LOGGING_ERROR = 3


def _show_error_dialog(title: str, message: str, details: Optional[str] = None) -> bool:
    """
    Wyświetla dialog błędu jeśli QApplication jest dostępne.

    Args:
        title (str): Tytuł okna dialogowego
        message (str): Główna wiadomość błędu
        details (str, optional): Szczegółowe informacje o błędzie

    Returns:
        bool: True jeśli dialog został wyświetlony, False w przeciwnym razie
    """
    try:
        if QApplication.instance():
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Icon.Critical)
            error_dialog.setWindowTitle(title)
            error_dialog.setText(message)
            if details:
                error_dialog.setInformativeText(f"Szczegóły: {details}")
                error_dialog.setDetailedText(details)
            error_dialog.exec()
            return True
    except Exception:
        pass
    return False


def global_exception_handler(exc_type: type, exc_value: BaseException, exc_traceback) -> None:
    """Handler dla niezłapanych wyjątków."""
    exception_str = "".join(
        traceback.format_exception(exc_type, exc_value, exc_traceback)
    )

    try:
        logging.critical(f"Niezłapany wyjątek: {exception_str}")
    except Exception:
        pass

    if not _show_error_dialog("Błąd", "Wystąpił nieoczekiwany błąd.", str(exc_value)):
        print(f"BŁĄD KRYTYCZNY: {exception_str}")


def _create_qt_application(style_sheet: str = "") -> 'QApplication':
    """
    Tworzy i konfiguruje aplikację Qt.

    Args:
        style_sheet (str): Arkusz stylów do zastosowania

    Returns:
        QApplication: Skonfigurowana aplikacja Qt

    Raises:
        RuntimeError: Jeśli nie można utworzyć aplikacji Qt
    """
    try:
        app = QApplication(sys.argv)
        if style_sheet:
            logging.debug("Stosowanie stylów (długość: %d)", len(style_sheet))
            app.setStyleSheet(style_sheet)
        return app
    except Exception as e:
        raise RuntimeError(f"Błąd tworzenia aplikacji Qt: {e}")


def _create_main_window() -> 'MainWindow':
    """
    Tworzy główne okno aplikacji.

    Returns:
        MainWindow: Utworzone główne okno

    Raises:
        RuntimeError: Jeśli nie można utworzyć głównego okna
    """
    try:
        window = MainWindow()
        return window
    except Exception as e:
        raise RuntimeError(f"Błąd inicjalizacji głównego okna: {e}")


def main(style_sheet: str = "") -> int:
    """
    Punkt wejścia do aplikacji.

    Args:
        style_sheet (str): Opcjonalny arkusz stylów QSS

    Returns:
        int: Kod wyjścia aplikacji
    """
    # Konfiguracja logowania
    try:
        setup_logging()
    except Exception as e:
        print(f"KRYTYCZNY BŁĄD: Inicjalizacja logów: {e}")
        return EXIT_LOGGING_ERROR

    # Konfiguracja centralnej worker factory
    try:
        logging.debug("Inicjalizacja worker factory...")
        ui_factory = UIWorkerFactory()
        configure_worker_factory(ui_factory)
        logging.debug("Worker factory skonfigurowana pomyślnie")
    except Exception as e:
        logging.critical("Błąd konfiguracji worker factory: %s", e)
        logging.debug("Szczegóły błędu worker factory:", exc_info=True)
        return EXIT_GENERAL_ERROR

    # Tworzenie aplikacji Qt
    try:
        logging.debug("Tworzenie aplikacji Qt...")
        app = _create_qt_application(style_sheet)
        logging.debug("Aplikacja Qt utworzona pomyślnie")
    except RuntimeError as e:
        logging.critical("Błąd tworzenia aplikacji Qt: %s", str(e))
        logging.debug("Szczegóły błędu Qt:", exc_info=True)
        print(f"BŁĄD KRYTYCZNY: {e}")
        return EXIT_QT_ERROR

    # Tworzenie głównego okna
    try:
        window = _create_main_window()
        window.show()

        sys.excepthook = global_exception_handler
        return app.exec()

    except RuntimeError as e:
        logging.critical(str(e))
        _show_error_dialog("Błąd krytyczny", "Błąd startu aplikacji.", str(e))
        return EXIT_GENERAL_ERROR


if __name__ == "__main__":
    print("BŁĄD: Nie można uruchomić aplikacji bezpośrednio z tego pliku.")
    print("Proszę uruchomić aplikację przez run_app.py z głównego katalogu projektu.")
    sys.exit(EXIT_GENERAL_ERROR)
