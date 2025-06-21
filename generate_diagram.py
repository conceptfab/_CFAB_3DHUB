# generate_diagram.py
import os
import subprocess
import sys

# --- Konfiguracja ---

# 1. Ścieżka do głównego pliku startowego aplikacji.
#    pydeps potrzebuje konkretnego pliku jako punktu wejścia.
ANALYSIS_PATH = "src"

# 2. Nazwa pliku wyjściowego z diagramem.
OUTPUT_FILENAME = "struktura_projektu"

# 3. Format pliku wyjściowego (svg jest wektorowy, png jest rastrowy).
OUTPUT_FORMAT = "svg"  # Możesz zmienić na "png"

# 4. Lista modułów lub pakietów do wykluczenia z diagramu.
#    WAŻNE: Dodaliśmy ten skrypt, aby nie pojawiał się na diagramie.
EXCLUDE_MODULES = [
    "tests",
    "venv",
    ".venv",
    "env",
    "docs",
    "setup",
    "generate_diagram",  # Wykluczamy sam ten skrypt
]

# 5. Ścieżka do Graphviz (jeśli nie jest w PATH)
GRAPHVIZ_PATH = r"C:\Program Files\Graphviz\bin"

# --- Koniec konfiguracji ---


def find_graphviz():
    """
    Znajduje ścieżkę do Graphviz.
    """
    # Najpierw sprawdź czy jest w PATH
    try:
        result = subprocess.run(
            ["dot", "-V"], capture_output=True, text=True, check=True
        )
        return "dot", result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # Sprawdź w standardowej lokalizacji
    dot_path = os.path.join(GRAPHVIZ_PATH, "dot.exe")
    if os.path.exists(dot_path):
        try:
            result = subprocess.run(
                [dot_path, "-V"], capture_output=True, text=True, check=True
            )
            return dot_path, result.stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

    return None, None


def check_dependencies():
    """
    Sprawdza czy wymagane zależności są zainstalowane.
    """
    print("Sprawdzanie zależności...")

    # Sprawdź pydeps
    try:
        result = subprocess.run(
            ["pydeps", "--version"], capture_output=True, text=True, check=True
        )
        print(f"✅ pydeps: {result.stdout.strip()}")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("❌ pydeps nie jest zainstalowany lub nie działa")
        print("   Zainstaluj: pip install pydeps")
        return False

    # Sprawdź Graphviz
    dot_path, version = find_graphviz()
    if dot_path:
        print(f"✅ Graphviz: {version}")
        return True
    else:
        print("❌ Graphviz nie jest zainstalowany lub nie jest w PATH")
        print("   Pobierz z: https://graphviz.org/download/")
        print("   Lub zainstaluj przez: winget install graphviz")
        return False


def generate_dependency_diagram():
    """
    Generuje diagram zależności projektu za pomocą pydeps.
    """
    # Sprawdź zależności przed uruchomieniem
    if not check_dependencies():
        print("\n❌ Nie można wygenerować diagramu - brak zależności")
        return False

    output_file = f"{OUTPUT_FILENAME}.{OUTPUT_FORMAT}"
    print(f"\nGenerowanie diagramu dla pliku: '{ANALYSIS_PATH}'...")
    print(f"Plik wyjściowy: {output_file}")

    # Sprawdź czy plik startowy istnieje
    if not os.path.exists(ANALYSIS_PATH):
        print(f"❌ Plik startowy '{ANALYSIS_PATH}' nie istnieje!")
        return False

    # Znajdź Graphviz
    dot_path, _ = find_graphviz()
    if not dot_path:
        print("❌ Nie można znaleźć Graphviz!")
        return False

    # Ustaw PATH dla Graphviz jeśli używa pełnej ścieżki
    env = os.environ.copy()
    if dot_path != "dot":
        # Dodaj katalog Graphviz do PATH
        graphviz_dir = os.path.dirname(dot_path)
        if graphviz_dir not in env.get("PATH", ""):
            env["PATH"] = graphviz_dir + os.pathsep + env.get("PATH", "")
            print(f"🔧 Dodano do PATH: {graphviz_dir}")

    # Budowanie polecenia dla pydeps
    command = [
        "pydeps",
        ANALYSIS_PATH,  # Przekazanie konkretnego pliku startowego
        "--cluster",  # Grupuje moduły z pakietu `src`
        "-o",
        output_file,  # Definiuje plik wyjściowy
        "-T",
        OUTPUT_FORMAT,  # Definiuje format wyjściowy
        "--show-dot",  # Pokaż polecenie dot
        "--debug",  # Dodaj debug info
        "--max-bacon=3",  # Głębsza analiza zależności
    ]

    # Dodawanie wykluczeń do polecenia
    for module in EXCLUDE_MODULES:
        command.extend(["-x", module])

    print(f"\nUruchamiam polecenie:\n{' '.join(command)}\n")

    try:
        # Uruchomienie pydeps jako zewnętrznego procesu
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, env=env
        )

        print("✅ Diagram został pomyślnie wygenerowany!")

        # Sprawdź czy plik wyjściowy istnieje i ma rozmiar > 0
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"📁 Plik wyjściowy: {output_file} ({file_size} bajtów)")

            if file_size == 0:
                print("⚠️  UWAGA: Plik wyjściowy jest pusty!")
                print("   To może oznaczać problem z Graphviz")
                return False
        else:
            print(f"❌ Plik wyjściowy {output_file} nie został utworzony!")
            return False

        if result.stdout:
            print("--- Logi pydeps ---")
            print(result.stdout)
            print("-------------------")

        return True

    except FileNotFoundError:
        print("\n❌ BŁĄD: Polecenie 'pydeps' nie zostało znalezione.")
        print("   Upewnij się, że pydeps jest zainstalowany")
        print("   (`pip install pydeps`)")
        print("   oraz że Graphviz jest zainstalowany i dodany do PATH.")
        return False

    except subprocess.CalledProcessError as e:
        print("\n❌ BŁĄD: Wystąpił błąd podczas działania pydeps")
        print(f"   (kod wyjścia: {e.returncode}).")
        print("--- Szczegóły błędu ---")
        print(e.stderr)
        print("------------------------")
        print("Sprawdź, czy Graphviz jest poprawnie zainstalowany")
        print("i czy ścieżki w skrypcie są poprawne.")
        return False

    except Exception as e:
        print(f"\n❌ BŁĄD: Wystąpił nieoczekiwany błąd: {e}")
        return False


if __name__ == "__main__":
    success = generate_dependency_diagram()
    if not success:
        sys.exit(1)
