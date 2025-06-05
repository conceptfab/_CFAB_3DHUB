# run_app.py
import os
import sys

# --- Modyfikacja sys.path ---
# Ta sekcja musi być wykonana przed próbą importu modułów z pakietu 'src'.
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
# --- Koniec modyfikacji sys.path ---

# Import głównej funkcji aplikacji teraz, gdy sys.path jest ustawione.
from src.main import main  # noqa: E402


def run():
    """Uruchamia aplikację z dodatkowymi informacjami diagnostycznymi."""
    # Jeszcze krótszy komunikat
    print(f"Root in path: {_PROJECT_ROOT}")

    # Sprawdź, czy użytkownik chce włączyć tryb debugowania
    import sys

    if "--debug" in sys.argv:
        print("TRYB DEBUGOWANIA WŁĄCZONY - szczegółowe logi skanowania")
        # Ustawienie poziomu logowania na DEBUG dla modułu skanowania
        import logging

        logging.getLogger("src.logic.scanner").setLevel(logging.DEBUG)

    main()


if __name__ == "__main__":
    run()
