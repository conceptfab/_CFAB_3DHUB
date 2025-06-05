"""
Testy podstawowych funkcji modułu file_operations.

Ten moduł zawiera testy dla podstawowych operacji na plikach
zdefiniowanych w module file_operations.py.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QUrl

from src.logic import file_operations
from src.models.file_pair import FilePair


class TestFileOperationsBasic(unittest.TestCase):
    """Testy podstawowych funkcji modułu file_operations."""

    def setUp(self):
        """Przygotowanie środowiska testowego przed każdym testem."""
        # Tworzenie tymczasowego katalogu roboczego
        self.temp_dir = tempfile.mkdtemp()

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
        # Usuwanie tymczasowego katalogu i wszystkich plików w nim
        shutil.rmtree(self.temp_dir)

    @patch("src.logic.file_operations.QDesktopServices")
    def test_open_archive_externally(self, mock_desktop_services):
        """Test otwierania archiwum zewnętrznym programem."""
        # Konfiguracja mocka
        mock_desktop_services.openUrl.return_value = True

        # Wywołanie testowanej funkcji
        result = file_operations.open_archive_externally(self.archive_path)

        # Weryfikacja wyników
        self.assertTrue(result)
        mock_desktop_services.openUrl.assert_called_once()

        # Test dla nieistniejącego pliku
        non_existent_path = os.path.join(self.temp_dir, "non_existent.zip")
        result = file_operations.open_archive_externally(non_existent_path)
        self.assertFalse(result)

    def test_create_folder(self):
        """Test tworzenia nowego folderu."""
        # Test tworzenia folderu z poprawną nazwą
        folder_name = "testfolder"
        result = file_operations.create_folder(self.temp_dir, folder_name)

        expected_path = os.path.join(self.temp_dir, folder_name)
        self.assertEqual(result, expected_path)
        self.assertTrue(os.path.isdir(expected_path))

        # Test tworzenia folderu z niepoprawną nazwą
        invalid_folder_name = "test*folder"
        result = file_operations.create_folder(self.temp_dir, invalid_folder_name)
        self.assertIsNone(result)

        # Test tworzenia folderu w nieistniejącym katalogu
        non_existent_dir = os.path.join(self.temp_dir, "non_existent")
        result = file_operations.create_folder(non_existent_dir, folder_name)
        self.assertIsNone(result)

    def test_rename_folder(self):
        """Test zmiany nazwy folderu."""
        # Tworzenie folderu do zmiany nazwy
        old_folder_name = "old_folder"
        old_folder_path = os.path.join(self.temp_dir, old_folder_name)
        os.makedirs(old_folder_path)

        # Test zmiany nazwy z poprawną nową nazwą
        new_folder_name = "new_folder"
        result = file_operations.rename_folder(old_folder_path, new_folder_name)

        expected_path = os.path.join(self.temp_dir, new_folder_name)
        self.assertEqual(result, expected_path)
        self.assertFalse(os.path.exists(old_folder_path))
        self.assertTrue(os.path.isdir(expected_path))

        # Test zmiany nazwy na niepoprawną nazwę
        invalid_folder_name = "test*folder"
        result = file_operations.rename_folder(expected_path, invalid_folder_name)
        self.assertIsNone(result)

        # Test zmiany nazwy nieistniejącego folderu
        non_existent_folder = os.path.join(self.temp_dir, "non_existent")
        result = file_operations.rename_folder(non_existent_folder, new_folder_name)
        self.assertIsNone(result)

    def test_delete_folder(self):
        """Test usuwania folderu."""
        # Tworzenie pustego folderu
        empty_folder = os.path.join(self.temp_dir, "empty_folder")
        os.makedirs(empty_folder)

        # Test usuwania pustego folderu
        result = file_operations.delete_folder(empty_folder)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(empty_folder))

        # Tworzenie folderu z zawartością
        folder_with_content = os.path.join(self.temp_dir, "folder_with_content")
        os.makedirs(folder_with_content)
        with open(os.path.join(folder_with_content, "testfile.txt"), "w") as f:
            f.write("test content")

        # Test usuwania folderu z zawartością bez delete_content=True
        result = file_operations.delete_folder(folder_with_content)
        self.assertFalse(result)
        self.assertTrue(os.path.exists(folder_with_content))

        # Test usuwania folderu z zawartością z delete_content=True
        result = file_operations.delete_folder(folder_with_content, delete_content=True)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(folder_with_content))

        # Test usuwania nieistniejącego folderu
        result = file_operations.delete_folder(
            os.path.join(self.temp_dir, "non_existent")
        )
        self.assertTrue(result)  # Powinno zwrócić True, gdy folder nie istnieje

    def test_manually_pair_files(self):
        """Test ręcznego parowania plików."""
        # Test parowania plików o identycznych nazwach bazowych
        result = file_operations.manually_pair_files(
            self.archive_path, self.preview_path, self.temp_dir
        )

        self.assertIsInstance(result, FilePair)
        self.assertEqual(result.get_archive_path(), self.archive_path)
        self.assertEqual(result.get_preview_path(), self.preview_path)

        # Test parowania plików o różnych nazwach bazowych
        different_preview_path = os.path.join(self.temp_dir, "different.png")
        with open(different_preview_path, "w") as f:
            f.write("test preview content")

        result = file_operations.manually_pair_files(
            self.archive_path, different_preview_path, self.temp_dir
        )

        self.assertIsInstance(result, FilePair)
        self.assertEqual(result.get_archive_path(), self.archive_path)
        # Podgląd powinien zostać przemianowany
        expected_preview_path = os.path.join(self.temp_dir, "testfile.png")
        self.assertEqual(result.get_preview_path(), expected_preview_path)

        # Sprawdzenie, czy original preview został usunięty
        self.assertFalse(os.path.exists(different_preview_path))

        # Test dla nieistniejących plików
        non_existent_path = os.path.join(self.temp_dir, "non_existent.zip")
        result = file_operations.manually_pair_files(
            non_existent_path, self.preview_path, self.temp_dir
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
