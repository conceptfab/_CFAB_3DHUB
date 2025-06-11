"""
Rozszerzony skrypt testowy dla klasy FolderStatisticsWorker.
Umożliwia podanie własnej ścieżki do testowanego folderu jako argument.
"""

import os
import sys
import time

from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QApplication

# Dodaj ścieżkę projektu do PYTHONPATH
sys.path.append(r"f:\_CFAB_3DHUB")

# Importuj potrzebne klasy
from src.ui.directory_tree_manager import FolderStatistics, FolderStatisticsWorker


def test_folder_statistics(folder_path=None):
    """
    Testuje funkcjonalność obliczania statystyk folderu.

    Args:
        folder_path: Opcjonalna ścieżka do folderu testowego.
                    Jeśli nie podano, używa folderu projektu.
    """
    app = QApplication([])  # Wymagane dla QThreadPool

    # Wybierz folder testowy - domyślnie folder projektu lub podany jako argument
    if not folder_path:
        if len(sys.argv) > 1:
            folder_path = sys.argv[1]
        else:
            folder_path = r"f:\_CFAB_3DHUB"

    # Sprawdź czy folder istnieje
    if not os.path.exists(folder_path):
        print(f"BŁĄD: Folder {folder_path} nie istnieje!")
        return

    print(f"Testowanie statystyk dla folderu: {folder_path}")

    # Zlicz pliki i foldery dla informacji
    file_count = 0
    folder_count = 0
    for root, dirs, files in os.walk(folder_path, topdown=True):
        folder_count += len(dirs)
        file_count += len(files)
        # Ogranicz głębokość dla dużych folderów
        if folder_count > 100 and file_count > 1000:
            break

    print(f"Wstępna analiza: {file_count} plików i {folder_count} podfolderów")

    # Utwórz workera
    worker = FolderStatisticsWorker(folder_path)

    # Ustaw funkcje callbackowe
    def on_finished(stats):
        if not isinstance(stats, FolderStatistics):
            print("BŁĄD: Zwrócono nieprawidłowy typ statystyk!")
            return

        print("\nWyniki obliczeń:")
        print(f"Rozmiar folderu: {stats.size_gb:.2f} GB")
        print(f"Liczba plików w folderze: {stats.total_files}")
        print(f"Liczba par w folderze: {stats.pairs_count}")
        print(f"Rozmiar podfolderów: {stats.subfolders_size_gb:.2f} GB")
        print(f"Liczba par w podfolderach: {stats.subfolders_pairs}")
        print(f"CAŁKOWITY rozmiar: {stats.total_size_gb:.2f} GB")
        print(f"CAŁKOWITA liczba par: {stats.total_pairs}")

        app.quit()

    def on_error(error_msg):
        print(f"BŁĄD: {error_msg}")
        app.quit()

    def on_progress(progress, message):
        print(f"Postęp: {progress}% - {message}")

    # Podłącz sygnały
    worker.custom_signals.finished.connect(on_finished)
    worker.custom_signals.error.connect(on_error)
    worker.custom_signals.progress.connect(on_progress)

    # Uruchom workera
    print("Rozpoczynam obliczanie statystyk...")
    start_time = time.time()
    QThreadPool.globalInstance().start(worker)

    # Uruchom pętlę zdarzeń
    app.exec()
    print(f"\nCzas wykonania: {time.time() - start_time:.2f} sekund")


if __name__ == "__main__":
    test_folder_statistics()
