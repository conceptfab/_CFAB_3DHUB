"""
Testy wydajnościowe dla modułu file_operations.

Ten moduł zawiera testy wydajnościowe dla operacji na plikach,
mierzące czas wykonania operacji na większej liczbie plików.
"""

import os
import shutil
import tempfile
import time
import unittest

from src.logic import file_operations


class TestFileOperationsPerformance(unittest.TestCase):
    """Testy wydajnościowe modułu file_operations."""

    def setUp(self):
        """Przygotowanie środowiska testowego przed każdym testem."""
        # Tworzenie tymczasowego katalogu roboczego
        self.temp_dir = tempfile.mkdtemp()

        # Tworzenie katalogu docelowego do testów przenoszenia
        self.target_dir = tempfile.mkdtemp()

        # Lista ścieżek do plików testowych
        self.archive_paths = []
        self.preview_paths = []

        # Tworzenie wielu plików do testów wydajnościowych
        self.file_count = 100  # liczba par plików do testów
        for i in range(self.file_count):
            archive_path = os.path.join(self.temp_dir, f"testfile_{i}.zip")
            preview_path = os.path.join(self.temp_dir, f"testfile_{i}.png")

            with open(archive_path, "w") as f:
                f.write(f"test archive content {i}")
            with open(preview_path, "w") as f:
                f.write(f"test preview content {i}")

            self.archive_paths.append(archive_path)
            self.preview_paths.append(preview_path)

    def tearDown(self):
        """Czyszczenie po testach."""
        # Usuwanie tymczasowych katalogów i wszystkich plików w nich
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.target_dir, ignore_errors=True)

    def test_performance_rename_file_pairs(self):
        """Test wydajności zmiany nazw wielu par plików."""
        start_time = time.time()

        # Zmiana nazw wielu par plików
        renamed_count = 0
        for i, (archive_path, preview_path) in enumerate(
            zip(self.archive_paths, self.preview_paths)
        ):
            new_name = f"renamed_{i}"
            result = file_operations.rename_file_pair(
                archive_path, preview_path, new_name
            )
            if result:
                renamed_count += 1

        end_time = time.time()
        elapsed_time = end_time - start_time

        print(
            f"\nCzas zmiany nazw {renamed_count} par plików: {elapsed_time:.4f} sekund"
        )
        print(f"Średni czas na parę: {elapsed_time/renamed_count:.6f} sekund")

        # Sprawdzenie, czy wszystkie pary zostały przemianowane
        self.assertEqual(renamed_count, self.file_count)

    def test_performance_move_file_pairs(self):
        """Test wydajności przenoszenia wielu par plików."""
        start_time = time.time()

        # Przenoszenie wielu par plików
        moved_count = 0
        for i, (archive_path, preview_path) in enumerate(
            zip(self.archive_paths, self.preview_paths)
        ):
            result = file_operations.move_file_pair(
                archive_path, preview_path, self.target_dir
            )
            if result:
                moved_count += 1

        end_time = time.time()
        elapsed_time = end_time - start_time

        print(
            f"\nCzas przenoszenia {moved_count} par plików: {elapsed_time:.4f} sekund"
        )
        print(f"Średni czas na parę: {elapsed_time/moved_count:.6f} sekund")

        # Sprawdzenie, czy wszystkie pary zostały przeniesione
        self.assertEqual(moved_count, self.file_count)

        # Sprawdzenie, czy pliki istnieją w nowej lokalizacji
        for i in range(self.file_count):
            self.assertTrue(
                os.path.exists(os.path.join(self.target_dir, f"testfile_{i}.zip"))
            )
            self.assertTrue(
                os.path.exists(os.path.join(self.target_dir, f"testfile_{i}.png"))
            )

    def test_performance_folder_operations(self):
        """Test wydajności operacji na wielu folderach."""
        # Tworzenie wielu katalogów
        folder_count = 50
        folders = []

        start_time = time.time()

        for i in range(folder_count):
            folder_name = f"test_folder_{i}"
            folder_path = file_operations.create_folder(self.temp_dir, folder_name)
            if folder_path:
                folders.append(folder_path)

        create_time = time.time() - start_time
        print(f"\nCzas tworzenia {len(folders)} folderów: {create_time:.4f} sekund")
        print(f"Średni czas na folder: {create_time/len(folders):.6f} sekund")

        # Zmiana nazw katalogów
        renamed_folders = []
        start_time = time.time()

        for i, folder_path in enumerate(folders):
            new_name = f"renamed_folder_{i}"
            new_path = file_operations.rename_folder(folder_path, new_name)
            if new_path:
                renamed_folders.append(new_path)

        rename_time = time.time() - start_time
        print(
            f"Czas zmiany nazw {len(renamed_folders)} folderów: {rename_time:.4f} sekund"
        )
        print(f"Średni czas na folder: {rename_time/len(renamed_folders):.6f} sekund")

        # Usuwanie katalogów
        start_time = time.time()

        deleted_count = 0
        for folder_path in renamed_folders:
            if file_operations.delete_folder(folder_path):
                deleted_count += 1

        delete_time = time.time() - start_time
        print(f"Czas usuwania {deleted_count} folderów: {delete_time:.4f} sekund")
        print(f"Średni czas na folder: {delete_time/deleted_count:.6f} sekund")

        # Sprawdzenia
        self.assertEqual(len(folders), folder_count)
        self.assertEqual(len(renamed_folders), folder_count)
        self.assertEqual(deleted_count, folder_count)


if __name__ == "__main__":
    unittest.main()
