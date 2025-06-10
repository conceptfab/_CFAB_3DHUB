import os
import sys
import traceback

# --- Modyfikacja sys.path ---
# Ta sekcja musi być wykonana przed próbą importu modułów z pakietu 'src'.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
# --- Koniec modyfikacji sys.path ---

# Import głównej funkcji aplikacji teraz, gdy sys.path jest ustawione.
from src.main import main  # noqa: E402
from src.utils.arg_parser import parse_args  # noqa: E402
from src.utils.arg_parser import get_app_version, setup_logging_from_args
from src.utils.style_loader import get_style_path, load_styles  # noqa: E402


def run():
    """
    Uruchamia aplikację z obsługą argumentów linii poleceń i obsługą błędów.

    Returns:
        int: Kod wyjścia (0 - sukces, >0 - błąd)
    """
    try:
        # Komunikat diagnostyczny
        print(f"Root in path: {_PROJECT_ROOT}")

        # Parsowanie argumentów linii poleceń
        args = parse_args()

        # Obsługa opcji --version
        if args.version:
            version = get_app_version()
            print(f"CFAB_3DHUB wersja {version}")
            return 0

        # Konfiguracja systemu logowania na podstawie argumentów
        setup_logging_from_args(args)

        # Ładowanie stylów
        style_sheet = ""
        if not args.no_style:
            try:
                # Ustalenie ścieżki do pliku stylów
                style_path = get_style_path(_PROJECT_ROOT, args.style)
                if args.style:
                    print(f"Używanie niestandardowego pliku stylów: {args.style}")

                # Ładowanie stylów
                print(f"Wczytywanie stylów z: {style_path}")
                style_sheet = load_styles(style_path, verbose=True)
            except Exception as e:
                print(f"OSTRZEŻENIE: Błąd podczas ładowania stylów: {str(e)}")
                print("Aplikacja zostanie uruchomiona bez stylów.")

        # Uruchomienie głównej funkcji aplikacji
        try:
            # Przekazujemy style do funkcji main
            return main(style_sheet=style_sheet)
        except Exception as e:
            print(
                f"BŁĄD KRYTYCZNY: Wystąpił błąd podczas uruchamiania aplikacji: {str(e)}"
            )
            traceback.print_exc()
            return 1

    except KeyboardInterrupt:
        print("\nPrzerwano uruchamianie aplikacji.")
        return 130  # Standardowy kod wyjścia dla SIGINT
    except Exception as e:
        print(f"BŁĄD KRYTYCZNY: Nieoczekiwany błąd podczas inicjalizacji: {str(e)}")
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(run())
