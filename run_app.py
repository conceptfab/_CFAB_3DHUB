import argparse
import logging
import os
import sys
import traceback

# --- Modyfikacja sys.path ---
# Ta sekcja musi być wykonana przed próbą importu modułów z pakietu 'src'.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
# --- Koniec modyfikacji sys.path ---

from src.utils.arg_parser import parse_args  # noqa: E402
from src.utils.arg_parser import get_app_version, setup_logging_from_args
from src.utils.style_loader import get_style_path, load_styles  # noqa: E402

# Stałe kodów wyjścia
EXIT_SUCCESS = 0
EXIT_GENERAL_ERROR = 1
EXIT_INITIALIZATION_ERROR = 2
EXIT_KEYBOARD_INTERRUPT = 130


def _load_application_styles(args: argparse.Namespace, project_root: str) -> str:
    """
    Ładuje style aplikacji na podstawie argumentów CLI.

    Args:
        args: Sparsowane argumenty CLI
        project_root: Ścieżka do głównego katalogu projektu

    Returns:
        str: Zawartość stylów lub pusty string
    """
    logger = logging.getLogger(__name__)

    if args.no_style:
        return ""

    try:
        style_path = get_style_path(project_root, args.style)
        if args.style:
            logger.info("Używanie niestandardowego stylu: %s", args.style)

        return load_styles(style_path, verbose=False)

    except Exception as e:
        logger.warning("Błąd ładowania stylów: %s", str(e))
        logger.info("Uruchamianie bez stylów")
        return ""


def run() -> int:
    """
    Uruchamia aplikację z obsługą argumentów linii poleceń i obsługą błędów.

    Returns:
        int: Kod wyjścia (0 - sukces, >0 - błąd)
    """
    logger = None  # Lazy initialization

    try:
        # Szybkie sprawdzenie opcji --version dla optymalizacji startu
        if "--version" in sys.argv:
            version = get_app_version()
            print(f"CFAB_3DHUB wersja {version}")
            return EXIT_SUCCESS

        # Parsowanie argumentów linii poleceń
        args = parse_args()

        # Konfiguracja systemu logowania na podstawie argumentów
        setup_logging_from_args(args)
        logger = logging.getLogger(__name__)

        logger.info("Root projektu: %s", _PROJECT_ROOT)

        # Ładowanie stylów
        style_sheet = _load_application_styles(args, _PROJECT_ROOT)

        # Uruchomienie głównej funkcji aplikacji (z opóźnionym importem)
        from src.main import main

        return main(style_sheet=style_sheet)

    except KeyboardInterrupt:
        print("\nPrzerwano uruchamianie aplikacji.")
        return EXIT_KEYBOARD_INTERRUPT

    except Exception as e:
        # Smart error handling z lazy logger
        if logger:
            logger.critical("Błąd aplikacji: %s", str(e))
            if __debug__:  # Tylko w debug mode
                logger.debug("Szczegóły błędu:", exc_info=True)
        else:
            print(f"KRYTYCZNY BŁĄD: {str(e)}")
            if __debug__:
                traceback.print_exc()

        return EXIT_GENERAL_ERROR


if __name__ == "__main__":
    sys.exit(run())
