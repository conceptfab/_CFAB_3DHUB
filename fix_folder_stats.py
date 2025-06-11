"""
Ten skrypt aplikuje poprawkę do metody run() w klasie FolderStatisticsWorker w pliku directory_tree_manager.py
"""

import os.path
import re

# Ścieżka do plików
directory_tree_manager_path = r"f:\_CFAB_3DHUB\src\ui\directory_tree_manager.py"
fixed_code_path = r"f:\_CFAB_3DHUB\src\ui\fixed_folder_stats_worker.py"


def apply_fix():
    # Wczytaj naprawiony kod
    with open(fixed_code_path, "r", encoding="utf-8") as f:
        fixed_code = f.read()

    # Wyodrębnij samą funkcję run()
    run_method_match = re.search(
        r"def fixed_run_method\(self\):(.*?)(?=\n\s*except Exception as e:|$)",
        fixed_code,
        re.DOTALL,
    )
    if not run_method_match:
        print(
            "Nie udało się znaleźć poprawionej metody run() w pliku fixed_folder_stats_worker.py"
        )
        return False

    run_method = run_method_match.group(1)
    # Usuń wcięcia z pierwszej linii i dostosuj odpowiednio resztę
    run_method = run_method.strip()

    # Wczytaj oryginalny plik
    with open(directory_tree_manager_path, "r", encoding="utf-8") as f:
        original_code = f.read()

    # Znajdź klasę FolderStatisticsWorker
    worker_class_pattern = r"class FolderStatisticsWorker\(UnifiedBaseWorker\):.*?(?=\n\s*class |\n\s*# ===|$)"
    worker_class_match = re.search(worker_class_pattern, original_code, re.DOTALL)

    if not worker_class_match:
        print(
            "Nie udało się znaleźć klasy FolderStatisticsWorker w pliku directory_tree_manager.py"
        )
        return False

    worker_class = worker_class_match.group(0)

    # Znajdź metodę run() w klasie FolderStatisticsWorker
    run_method_pattern = r"def run\(self\):.*?(?=\s+def |    except Exception as e:|$)"
    run_method_orig_match = re.search(run_method_pattern, worker_class, re.DOTALL)

    if not run_method_orig_match:
        print("Nie udało się znaleźć metody run() w klasie FolderStatisticsWorker")
        return False

    # Przygotuj nową metodę run() z odpowiednim wcięciem
    new_run_method = """    def run(self):
        \"\"\"Oblicza statystyki folderu.\"\"\"
        try:
            stats = FolderStatistics()
            self.emit_progress(0, "Rozpoczynanie obliczania statystyk...")

            if self.check_interruption():
                return

            # Oblicz rozmiar foldera aktualnego (bez przeglądania podfolderów)
            self.emit_progress(25, "Obliczanie rozmiaru folderu...")
            folder_size = 0
            file_count = 0

            # Najpierw oblicz rozmiar tylko dla bieżącego folderu
            try:
                for item in os.listdir(self.folder_path):
                    if self.check_interruption():
                        return
                    
                    item_path = os.path.join(self.folder_path, item)
                    if os.path.isfile(item_path):
                        try:
                            file_size = os.path.getsize(item_path)
                            folder_size += file_size
                            file_count += 1
                        except (OSError, FileNotFoundError):
                            continue
            except (OSError, PermissionError) as e:
                logger.warning(f"Błąd przy dostępie do folderu {self.folder_path}: {e}")
            
            stats.size_gb = folder_size / (1024**3)
            stats.total_files = file_count
            
            # Oblicz liczbę par plików w bieżącym folderze (bez podfolderów)
            self.emit_progress(50, "Obliczanie liczby par plików...")
            if self.check_interruption():
                return

            try:
                # Używamy max_depth=0 aby ograniczyć tylko do bieżącego folderu
                found_pairs, _, _ = scan_folder_for_pairs(
                    self.folder_path, max_depth=0, pair_strategy="first_match"
                )
                stats.pairs_count = len(found_pairs)
            except Exception as e:
                logger.warning(f"Błąd obliczania par plików: {e}")
                stats.pairs_count = 0
            
            # Oblicz statystyki dla podfolderów
            self.emit_progress(75, "Obliczanie statystyk podfolderów...")
            subfolders_size = 0
            subfolders_pairs = 0
            
            try:
                # Uzyskaj listę bezpośrednich podfolderów
                subdirs = [os.path.join(self.folder_path, d) for d in os.listdir(self.folder_path) 
                          if os.path.isdir(os.path.join(self.folder_path, d))]
                
                for subdir in subdirs:
                    if self.check_interruption():
                        return
                    
                    # Oblicz rozmiar podfolderu
                    for root, dirs, files in os.walk(subdir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                subfolders_size += os.path.getsize(file_path)
                            except (OSError, FileNotFoundError):
                                continue
                    
                    # Oblicz pary w podfolderze
                    try:
                        sub_pairs, _, _ = scan_folder_for_pairs(
                            subdir, max_depth=-1, pair_strategy="first_match"
                        )
                        subfolders_pairs += len(sub_pairs)
                    except Exception:
                        pass
            except (OSError, PermissionError) as e:
                logger.warning(f"Błąd przy dostępie do podfolderów {self.folder_path}: {e}")
            
            stats.subfolders_size_gb = subfolders_size / (1024**3)
            stats.subfolders_pairs = subfolders_pairs"""

    # Zamień starą metodę run() na nową
    updated_code = original_code.replace(run_method_orig_match.group(0), new_run_method)

    # Zapisz zmodyfikowany plik
    with open(directory_tree_manager_path, "w", encoding="utf-8") as f:
        f.write(updated_code)

    print("Pomyślnie aplikowano poprawkę w pliku directory_tree_manager.py")
    return True


if __name__ == "__main__":
    apply_fix()
