"""
Ten skrypt naprawia błędy w metodzie run() klasy FolderStatisticsWorker w pliku directory_tree_manager.py
"""

import os
import re

# Ścieżka do pliku
directory_tree_manager_path = r"f:\_CFAB_3DHUB\src\ui\directory_tree_manager.py"


def fix_broken_run_method():
    """
    Naprawia uszkodzoną metodę run() w klasie FolderStatisticsWorker.
    """
    print("Naprawianie metody run() w klasie FolderStatisticsWorker...")

    # Wczytaj plik
    with open(directory_tree_manager_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Przygotuj poprawną wersję metody run()
    fixed_run_method = """    def run(self):
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
            stats.subfolders_pairs = subfolders_pairs

            self.emit_progress(100, "Zakończono obliczanie statystyk")
            self.custom_signals.finished.emit(stats)
            self.emit_finished(stats)

        except Exception as e:
            error_msg = f"Błąd obliczania statystyk dla {self.folder_path}: {e}"
            logger.error(error_msg)
            self.custom_signals.error.emit(error_msg)
            self.emit_error(error_msg)"""

    # Znajdź wzorzec dla całej klasy FolderStatisticsWorker
    worker_pattern = re.compile(
        r"class FolderStatisticsWorker\(UnifiedBaseWorker\):.*?(?=\n\s*class\s+|$)",
        re.DOTALL,
    )
    worker_match = worker_pattern.search(content)

    if not worker_match:
        print("Nie znaleziono klasy FolderStatisticsWorker!")
        return False

    worker_code = worker_match.group(0)

    # Znajdź początek metody run
    run_pattern = re.compile(r"(\s+def run\(self\):.*?)(?=\s+def\s+|$)", re.DOTALL)
    run_match = run_pattern.search(worker_code)

    if not run_match:
        print("Nie znaleziono metody run() w klasie FolderStatisticsWorker!")
        return False

    # Zastąp metodę run nową implementacją
    new_worker_code = worker_code.replace(run_match.group(1), fixed_run_method)
    new_content = content.replace(worker_code, new_worker_code)

    # Zapisz zmiany
    with open(directory_tree_manager_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("Naprawiono metodę run() w klasie FolderStatisticsWorker.")
    return True


if __name__ == "__main__":
    fix_broken_run_method()
