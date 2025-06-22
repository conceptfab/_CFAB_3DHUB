"""
Główny moduł aplikacji CFAB_3DHUB.
Zawiera funkcję main() inicjalizującą i uruchamiającą aplikację.
"""

import logging
import sys
import traceback
from typing import TYPE_CHECKING, Optional

from PyQt6.QtWidgets import QApplication, QMessageBox

# Opóźniony import dla lazy loading
# from src.factories.worker_factory import UIWorkerFactory
# from src.logic.file_ops_components import configure_worker_factory
if TYPE_CHECKING:
    from src.ui.main_window.main_window import MainWindow

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
    except (RuntimeError, OSError) as e:
        # Problemy z Qt lub systemem
        logging.error(f"Błąd wyświetlania dialogu: {e}")
        return False
    except Exception as e:
        # Nieoczekiwane błędy - loguj szczegółowo
        logging.error(f"Nieoczekiwany błąd dialogu: {e}", exc_info=True)
        return False


def global_exception_handler(
    exc_type: type, exc_value: BaseException, exc_traceback
) -> None:
    """Handler dla niezłapanych wyjątków."""
    exception_str = "".join(
        traceback.format_exception(exc_type, exc_value, exc_traceback)
    )

    try:
        log_message = f"Niezłapany wyjątek: {exc_type.__name__}: {exc_value}"
        logging.critical(log_message)
        logging.debug("Stack trace:", exc_info=(exc_type, exc_value, exc_traceback))
    except Exception:
        # Ten except jest po to by uniknąć sytuacji, w której logger sam
        # rzuci wyjątkiem i zablokuje wyświetlenie błędu.
        error_msg = (
            "KRYTYCZNY BŁĄD W LOGGERZE PODCZAS OBSŁUGI WYJĄTKU: " f"{exception_str}"
        )
        print(error_msg)

    if not _show_error_dialog(
        "Błąd krytyczny aplikacji",
        "Wystąpił nieoczekiwany błąd.",
        str(exc_value),
    ):
        print(f"BŁĄD KRYTYCZNY: {exception_str}")


def _setup_logging_safe() -> None:
    """
    Bezpieczna konfiguracja logowania z obsługą błędów.

    Raises:
        RuntimeError: Jeśli nie można skonfigurować logowania
    """
    try:
        from src.utils.logging_config import setup_logging

        setup_logging()
        logging.info("System logowania skonfigurowany pomyślnie")
    except (OSError, PermissionError) as e:
        # Problemy z plikami logów
        print(f"BŁĄD: Nie można skonfigurować logowania: {e}")
        raise RuntimeError(f"Błąd konfiguracji logowania: {e}")
    except Exception as e:
        print(f"KRYTYCZNY BŁĄD: Inicjalizacja logów: {e}")
        raise RuntimeError(f"Nieoczekiwany błąd logowania: {e}")


def _setup_worker_factory_safe() -> None:
    """
    Bezpieczna konfiguracja worker factory z obsługą błędów.

    Raises:
        RuntimeError: Jeśli nie można skonfigurować worker factory
    """
    try:
        logging.debug("Inicjalizacja worker factory...")
        from src.factories.worker_factory import UIWorkerFactory
        from src.logic.file_ops_components import configure_worker_factory

        ui_factory = UIWorkerFactory()
        configure_worker_factory(ui_factory)
        logging.debug("Worker factory skonfigurowana pomyślnie")
    except ImportError as e:
        logging.critical("Błąd importu worker factory: %s", e)
        raise RuntimeError(f"Nie można zaimportować worker factory: {e}")
    except Exception as e:
        log_msg = f"Błąd konfiguracji worker factory: {e}"
        logging.critical(log_msg, exc_info=True)
        raise RuntimeError(f"Błąd worker factory: {e}")


def _create_qt_application(style_sheet: str = "") -> "QApplication":
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

        # Ustawienie podstawowych właściwości aplikacji
        app.setApplicationName("CFAB_3DHUB")
        app.setApplicationVersion("1.0.0")  # TODO: pobierać z config

        if style_sheet:
            log_msg = f"Stosowanie stylów (długość: {len(style_sheet)} znaków)"
            logging.info(log_msg)
            app.setStyleSheet(style_sheet)
        else:
            logging.debug("Uruchamianie bez niestandardowych stylów")

        return app

    except (OSError, RuntimeError) as e:
        # Problemy systemowe z Qt
        raise RuntimeError(f"Błąd systemu przy tworzeniu aplikacji Qt: {e}")
    except Exception as e:
        # Inne nieoczekiwane błędy
        logging.error("Nieoczekiwany błąd Qt: %s", e, exc_info=True)
        raise RuntimeError(f"Błąd tworzenia aplikacji Qt: {e}")


def _create_main_window() -> "MainWindow":
    """
    Tworzy główne okno aplikacji.

    Returns:
        MainWindow: Utworzone główne okno

    Raises:
        RuntimeError: Jeśli nie można utworzyć głównego okna
    """
    try:
        from src.ui.main_window.main_window import MainWindow

        window = MainWindow()
        return window
    except Exception as e:
        raise RuntimeError(f"Błąd inicjalizacji głównego okna: {e}")


def _create_and_show_main_window(
    style_sheet: str = "",
) -> tuple["QApplication", "MainWindow"]:
    """
    Tworzy aplikację Qt i główne okno.

    Args:
        style_sheet (str): Arkusz stylów QSS

    Returns:
        tuple: (QApplication, MainWindow)

    Raises:
        RuntimeError: Jeśli nie można utworzyć aplikacji lub okna
    """
    try:
        logging.debug("Tworzenie aplikacji Qt...")
        app = _create_qt_application(style_sheet)  # Przekazanie style_sheet
        logging.debug("Aplikacja Qt utworzona pomyślnie")

        window = _create_main_window()
        window.show()
        logging.info("Główne okno aplikacji utworzone i wyświetlone")

        return app, window

    except RuntimeError:
        raise
    except Exception as e:
        log_msg = f"Nieoczekiwany błąd tworzenia UI: {e}"
        logging.critical(log_msg, exc_info=True)
        raise RuntimeError(f"Błąd tworzenia interfejsu: {e}")


def main(style_sheet: str = "") -> int:
    """
    Punkt wejścia do aplikacji.

    Args:
        style_sheet (str): Opcjonalny arkusz stylów QSS

    Returns:
        int: Kod wyjścia aplikacji
    """
    # Ustawienie global exception handler na początku
    sys.excepthook = global_exception_handler

    # 1. Konfiguracja logowania
    try:
        _setup_logging_safe()
    except RuntimeError:
        return EXIT_LOGGING_ERROR

    # 2. Konfiguracja worker factory
    try:
        _setup_worker_factory_safe()
    except RuntimeError:
        return EXIT_GENERAL_ERROR

    # 3. Tworzenie i uruchomienie aplikacji Qt
    try:
        app, window = _create_and_show_main_window(style_sheet)

        # Uruchomienie głównej pętli aplikacji
        logging.info("Uruchamianie głównej pętli aplikacji")
        return app.exec()

    except RuntimeError as e:
        logging.critical(str(e))
        _show_error_dialog("Błąd krytyczny", "Błąd startu aplikacji.", str(e))
        return EXIT_GENERAL_ERROR


if __name__ == "__main__":
    print("BŁĄD: Nie można uruchomić aplikacji bezpośrednio z tego pliku.")
    print(
        "Proszę uruchomić aplikację przez run_app.py " "z głównego katalogu projektu."
    )
    sys.exit(EXIT_GENERAL_ERROR)
