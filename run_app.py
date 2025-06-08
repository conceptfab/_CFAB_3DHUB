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

    # Wczytaj plik styles.qss i przekaż go do funkcji main
    style_sheet = ""
    style_path = os.path.join(_PROJECT_ROOT, "styles.qss")
    if os.path.exists(style_path):
        print(f"Wczytywanie stylów z: {style_path}")
        try:
            # Próbuj najpierw z UTF-8 (najbardziej powszechne kodowanie)
            with open(style_path, "r", encoding="utf-8") as style_file:
                style_sheet = style_file.read()
                print(f"Załadowano {len(style_sheet)} bajtów stylów (UTF-8)")
        except UnicodeDecodeError:
            # Jeśli UTF-8 nie zadziała, spróbuj z UTF-16
            try:
                with open(style_path, "r", encoding="utf-16") as style_file:
                    style_sheet = style_file.read()
                    print(f"Załadowano {len(style_sheet)} bajtów stylów (UTF-16)")
            except UnicodeDecodeError:
                # Jako ostateczność, spróbuj z Latin-1 (ignoruje błędy kodowania)
                with open(style_path, "r", encoding="latin-1") as style_file:
                    style_sheet = style_file.read()
                    print(f"Załadowano {len(style_sheet)} bajtów stylów (Latin-1)")
                print(
                    "UWAGA: Używanie awaryjnego kodowania Latin-1, mogą wystąpić problemy ze znakami specjalnymi."
                )
    else:
        print(f"UWAGA: Nie znaleziono pliku stylów: {style_path}")

    # Sprawdź, czy użytkownik chce włączyć tryb debugowania
    import sys

    if "--debug" in sys.argv:
        print("TRYB DEBUGOWANIA WŁĄCZONY - szczegółowe logi skanowania")
        # Ustawienie poziomu logowania na DEBUG dla modułu skanowania
        import logging

        logging.getLogger("src.logic.scanner").setLevel(logging.DEBUG)

    # Przekazujemy style do funkcji main
    main(style_sheet=style_sheet)


if __name__ == "__main__":
    run()
