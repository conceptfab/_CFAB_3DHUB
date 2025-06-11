"""
Ten skrypt testuje działanie klasy FolderStatisticsWorker po naszych poprawkach.
Sprawdza, czy poprawnie obliczane są statystyki folderów.
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


def test_folder_statistics():
    """Testuje funkcjonalność obliczania statystyk folderu."""
    app = QApplication([])  # Wymagane dla QThreadPool

    # Wybierz folder testowy - może być dowolny folder na dysku
    test_folder = r"f:\_CFAB_3DHUB\src"

    print(f"Testowanie statystyk dla folderu: {test_folder}")

    # Utwórz workera
    worker = FolderStatisticsWorker(test_folder)

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
    QThreadPool.globalInstance().start(worker)

    # Uruchom pętlę zdarzeń
    app.exec()


if __name__ == "__main__":
    test_folder_statistics()
