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

from src.utils.arg_parser import (
    get_app_version,
    parse_args,  # noqa: E402
    setup_logging_from_args,
)
from src.utils.style_loader import get_style_path, load_styles  # noqa: E402

# Stałe kodów wyjścia
EXIT_SUCCESS = 0
EXIT_GENERAL_ERROR = 1
EXIT_INITIALIZATION_ERROR = 2
EXIT_KEYBOARD_INTERRUPT = 130


def _load_application_styles(args, project_root):
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
            logger.info("Niestandardowy styl: %s", args.style)

        logger.info(f"Wczytywanie stylów z: {style_path}")
        return load_styles(style_path, verbose=True)

    except Exception as e:
        logger.warning(f"Błąd podczas ładowania stylów: {str(e)}")
        logger.warning("Aplikacja zostanie uruchomiona bez stylów.")
        return ""


def run():
    """
    Uruchamia aplikację z obsługą argumentów linii poleceń i obsługą błędów.

    Returns:
        int: Kod wyjścia (0 - sukces, >0 - błąd)
    """
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

        logger.info(f"Root projektu: {_PROJECT_ROOT}")

        # Ładowanie stylów
        style_sheet = _load_application_styles(args, _PROJECT_ROOT)

        # Uruchomienie głównej funkcji aplikacji (z opóźnionym importem)
        from src.main import main

        try:
            return main(style_sheet=style_sheet or "")
        except Exception as e:
            logger.critical("Błąd przy uruchamianiu: %s", str(e))
            logger.debug("Szczegóły błędu:", exc_info=True)
            return EXIT_GENERAL_ERROR

    except KeyboardInterrupt:
        print("\nPrzerwano uruchamianie aplikacji.")
        return EXIT_KEYBOARD_INTERRUPT
    except Exception as e:
        # W tym miejscu logger może nie być jeszcze skonfigurowany
        print(f"KRYTYCZNY BŁĄD: Błąd inicjalizacji: {str(e)}")
        traceback.print_exc()
        return EXIT_INITIALIZATION_ERROR


if __name__ == "__main__":
    sys.exit(run())
