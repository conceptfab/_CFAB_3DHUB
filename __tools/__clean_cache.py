import os
import shutil

def remove_python_cache(project_path):
    """
    Usuwa foldery __pycache__ z wszystkich podfolderów w danym projekcie.

    Args:
        project_path (str): Ścieżka do katalogu głównego projektu.
    """
    if not os.path.isdir(project_path):
        print(f"Błąd: Ścieżka '{project_path}' nie jest prawidłowym katalogiem.")
        return

    print(f"Rozpoczynam usuwanie cache'u Python w projekcie: {project_path}")
    removed_count = 0
    error_count = 0

    # Używamy os.path.abspath do upewnienia się, że ścieżka jest absolutna
    project_path = os.path.abspath(project_path)

    for root, dirs, files in os.walk(project_path):
        if '__pycache__' in dirs:
            cache_path = os.path.join(root, '__pycache__')
            try:
                print(f"Usuwam: {cache_path}")
                shutil.rmtree(cache_path)
                removed_count += 1
            except OSError as e:
                print(f"Błąd podczas usuwania {cache_path}: {e}")
                error_count += 1
            # Usuń '__pycache__' z listy dirs, aby os.walk nie wchodził do niego
            dirs.remove('__pycache__')

    print("-" * 30)
    print(f"Zakończono usuwanie cache'u Python.")
    print(f"Usunięto {removed_count} folderów __pycache__.")
    if error_count > 0:
        print(f"Wystąpiło {error_count} błędów podczas usuwania.")
    print("-" * 30)

# Użycie:
# Używamy '.' aby reprezentować bieżący katalog, w którym uruchamiany jest skrypt
PROJECT_ROOT_PATH = '.'

remove_python_cache(PROJECT_ROOT_PATH)