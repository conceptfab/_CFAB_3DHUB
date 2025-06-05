"""
Zaawansowane testy modułu file_operations.

Ten moduł zawiera testy dla bardziej złożonych operacji na plikach
zdefiniowanych w module file_operations.py, zwłaszcza operacji na parach plików.
"""

import os
import shutil
import tempfile
import unittest

from src.logic import file_operations


class TestFileOperationsAdvanced(unittest.TestCase):
    """Testy zaawansowanych funkcji modułu file_operations."""

    def setUp(self):
        """Przygotowanie środowiska testowego przed każdym testem."""
        # Tworzenie tymczasowego katalogu roboczego
        self.temp_dir = tempfile.mkdtemp()

        # Tworzenie drugiego katalogu do testów przenoszenia
        self.target_dir = tempfile.mkdtemp()

        # Tworzenie tymczasowych plików do testów
        self.archive_path = os.path.join(self.temp_dir, "testfile.zip")
        self.preview_path = os.path.join(self.temp_dir, "testfile.png")

        # Tworzenie pustych plików
        with open(self.archive_path, "w") as f:
            f.write("test archive content")
        with open(self.preview_path, "w") as f:
            f.write("test preview content")

    def tearDown(self):
        """Czyszczenie po testach."""
        # Usuwanie tymczasowych katalogów i wszystkich plików w nich
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        shutil.rmtree(self.target_dir, ignore_errors=True)

    def test_rename_file_pair(self):
        """Test zmiany nazwy pary plików."""
        # Test zmiany nazwy pary plików na poprawną nazwę
        new_name = "newname"
        result = file_operations.rename_file_pair(
            self.archive_path, self.preview_path, new_name
        )

        self.assertIsNotNone(result)
        new_archive_path, new_preview_path = result

        expected_archive_path = os.path.join(self.temp_dir, f"{new_name}.zip")
        expected_preview_path = os.path.join(self.temp_dir, f"{new_name}.png")

        self.assertEqual(new_archive_path, expected_archive_path)
        self.assertEqual(new_preview_path, expected_preview_path)

        self.assertTrue(os.path.exists(new_archive_path))
        self.assertTrue(os.path.exists(new_preview_path))
        self.assertFalse(os.path.exists(self.archive_path))
        self.assertFalse(os.path.exists(self.preview_path))

        # Test zmiany nazwy pary plików na niepoprawną nazwę
        invalid_name = "new*name"
        result = file_operations.rename_file_pair(
            new_archive_path, new_preview_path, invalid_name
        )

        self.assertIsNone(result)
        # Pliki powinny zachować poprzednie nazwy
        self.assertTrue(os.path.exists(new_archive_path))
        self.assertTrue(os.path.exists(new_preview_path))

        # Test zmiany nazwy bez pliku podglądu
        single_file_path = os.path.join(self.temp_dir, "singlefile.zip")
        with open(single_file_path, "w") as f:
            f.write("test single file content")

        result = file_operations.rename_file_pair(
            single_file_path, None, "newsinglefile"
        )

        self.assertIsNotNone(result)
        new_single_file_path, new_preview_path = result

        expected_path = os.path.join(self.temp_dir, "newsinglefile.zip")
        self.assertEqual(new_single_file_path, expected_path)
        self.assertIsNone(new_preview_path)

        self.assertTrue(os.path.exists(new_single_file_path))
        self.assertFalse(os.path.exists(single_file_path))

    def test_delete_file_pair(self):
        """Test usuwania pary plików."""
        # Test usuwania pary plików
        result = file_operations.delete_file_pair(self.archive_path, self.preview_path)

        self.assertTrue(result)
        self.assertFalse(os.path.exists(self.archive_path))
        self.assertFalse(os.path.exists(self.preview_path))

        # Test usuwania pojedynczego pliku bez podglądu
        single_file_path = os.path.join(self.temp_dir, "singlefile.zip")
        with open(single_file_path, "w") as f:
            f.write("test single file content")

        result = file_operations.delete_file_pair(single_file_path, None)

        self.assertTrue(result)
        self.assertFalse(os.path.exists(single_file_path))

        # Test usuwania nieistniejących plików
        result = file_operations.delete_file_pair(
            os.path.join(self.temp_dir, "non_existent.zip"),
            os.path.join(self.temp_dir, "non_existent.png"),
        )

        self.assertTrue(result)

    def test_move_file_pair(self):
        """Test przenoszenia pary plików do innego katalogu."""
        # Test przenoszenia pary plików do innego katalogu
        result = file_operations.move_file_pair(
            self.archive_path, self.preview_path, self.target_dir
        )

        self.assertIsNotNone(result)
        new_archive_path, new_preview_path = result

        expected_archive_path = os.path.join(self.target_dir, "testfile.zip")
        expected_preview_path = os.path.join(self.target_dir, "testfile.png")

        self.assertEqual(new_archive_path, expected_archive_path)
        self.assertEqual(new_preview_path, expected_preview_path)

        self.assertTrue(os.path.exists(new_archive_path))
        self.assertTrue(os.path.exists(new_preview_path))
        self.assertFalse(os.path.exists(self.archive_path))
        self.assertFalse(os.path.exists(self.preview_path))

        # Test przenoszenia pojedynczego pliku bez podglądu
        single_file_path = os.path.join(self.temp_dir, "singlefile.zip")
        with open(single_file_path, "w") as f:
            f.write("test single file content")

        result = file_operations.move_file_pair(single_file_path, None, self.target_dir)

        self.assertIsNotNone(result)
        new_single_file_path, new_preview_path = result

        expected_path = os.path.join(self.target_dir, "singlefile.zip")
        self.assertEqual(new_single_file_path, expected_path)
        self.assertIsNone(new_preview_path)

        self.assertTrue(os.path.exists(new_single_file_path))
        self.assertFalse(os.path.exists(single_file_path))

        # Test próby przeniesienia pliku do nieistniejącego katalogu
        with open(os.path.join(self.temp_dir, "another.zip"), "w") as f:
            f.write("another test content")

        non_existent_dir = os.path.join(self.temp_dir, "non_existent_dir")
        result = file_operations.move_file_pair(
            os.path.join(self.temp_dir, "another.zip"), None, non_existent_dir
        )

        self.assertIsNone(result)
        # Plik powinien pozostać w oryginalnym miejscu
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "another.zip")))

        # Test próby nadpisania istniejącego pliku
        # Najpierw stwórzmy plik o takiej samej nazwie w katalogu docelowym
        conflict_path = os.path.join(self.target_dir, "conflict.zip")
        original_path = os.path.join(self.temp_dir, "conflict.zip")

        with open(conflict_path, "w") as f:
            f.write("target dir conflict file")
        with open(original_path, "w") as f:
            f.write("source dir conflict file")

        result = file_operations.move_file_pair(original_path, None, self.target_dir)

        self.assertIsNone(result)
        # Plik powinien pozostać w oryginalnym miejscu
        self.assertTrue(os.path.exists(original_path))
        # A plik w katalogu docelowym powinien pozostać niezmieniony
        self.assertTrue(os.path.exists(conflict_path))

        # Sprawdźmy zawartość, aby upewnić się, że nie został nadpisany
        with open(conflict_path, "r") as f:
            content = f.read()
        self.assertEqual(content, "target dir conflict file")


if __name__ == "__main__":
    unittest.main()
