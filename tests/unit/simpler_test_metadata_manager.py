"""
Uproszczone testy dla modułu metadata_manager, które nie używają PyFakeFS.

Te testy wykorzystują normalne mocki unittest.mock zamiast PyFakeFS,
co rozwiązuje problemy z kompatybilnością.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, mock_open, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.logic import metadata_manager
from src.utils.path_utils import normalize_path


class TestMetadataManager(unittest.TestCase):
    """Testy dla funkcji w module metadata_manager bez używania PyFakeFS."""

    @classmethod
    def setUpClass(cls):
        """Uruchamiane przed wszystkimi testami w klasie."""
        print("\nUruchamianie testów dla metadata_manager.py bez PyFakeFS.")

    @classmethod
    def tearDownClass(cls):
        """Uruchamiane po wszystkich testach w klasie."""
        print("\nZakończono testy dla metadata_manager.py.")

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.working_dir = normalize_path("C:/test/working/dir")
        self.metadata_dir_path = os.path.join(
            self.working_dir, metadata_manager.METADATA_DIR_NAME
        )
        self.metadata_file_path = os.path.join(
            self.metadata_dir_path, metadata_manager.METADATA_FILE_NAME
        )
        self.lock_file_path = os.path.join(
            self.metadata_dir_path, metadata_manager.LOCK_FILE_NAME
        )

    def test_get_metadata_path(self):
        """Test funkcji get_metadata_path."""
        expected_path = os.path.join(
            self.working_dir,
            metadata_manager.METADATA_DIR_NAME,
            metadata_manager.METADATA_FILE_NAME,
        )
        result = metadata_manager.get_metadata_path(self.working_dir)
        self.assertEqual(normalize_path(result), normalize_path(expected_path))

    def test_get_lock_path(self):
        """Test funkcji get_lock_path."""
        expected_path = os.path.join(
            self.working_dir,
            metadata_manager.METADATA_DIR_NAME,
            metadata_manager.LOCK_FILE_NAME,
        )
        result = metadata_manager.get_lock_path(self.working_dir)
        self.assertEqual(normalize_path(result), normalize_path(expected_path))

    def test_get_relative_path(self):
        """Test funkcji get_relative_path."""
        base_path = normalize_path("C:/base/path")
        absolute_path = normalize_path("C:/base/path/to/file.txt")
        expected_relative_path = normalize_path("to/file.txt")
        self.assertEqual(
            metadata_manager.get_relative_path(absolute_path, base_path),
            expected_relative_path,
        )

    @patch("os.path.splitdrive")
    def test_get_relative_path_different_drives(self, mock_splitdrive):
        """Test funkcji get_relative_path dla różnych dysków (Windows)."""
        mock_splitdrive.side_effect = lambda p: (
            ("D:", p[2:]) if "other" in p else ("C:", p[2:])
        )

        base_path = normalize_path("C:/base/path")
        absolute_path_outside = normalize_path("D:/other/path/to/file.txt")

        self.assertIsNone(
            metadata_manager.get_relative_path(absolute_path_outside, base_path)
        )

    def test_get_absolute_path(self):
        """Test funkcji get_absolute_path."""
        base_path = normalize_path("C:/base/path")
        relative_path = normalize_path("to/file.txt")
        expected_absolute_path = normalize_path("C:/base/path/to/file.txt")
        self.assertEqual(
            metadata_manager.get_absolute_path(relative_path, base_path),
            expected_absolute_path,
        )

    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    @patch("filelock.FileLock")
    def test_save_metadata_creates_directory(
        self, mock_file_lock, mock_json_dump, mock_open_file, mock_makedirs, mock_exists
    ):
        """Test czy save_metadata tworzy katalogi, jeśli nie istnieją."""
        mock_exists.return_value = False

        # Symulacja FileLock
        mock_lock_instance = MagicMock()
        mock_file_lock.return_value = mock_lock_instance
        mock_lock_instance.__enter__.return_value = None
        mock_lock_instance.__exit__.return_value = None

        # Mock dla open w trybie zapisu
        mock_file_handle = mock_open_file.return_value.__enter__.return_value

        fp1 = MagicMock()
        fp1.archive_path = "C:/test/working/dir/archive1.zip"
        fp1.is_favorite = True
        fp1.get_stars.return_value = 5
        fp1.get_color_tag.return_value = "red"

        file_pairs = [fp1]
        unpaired_archives = []
        unpaired_previews = []

        result = metadata_manager.save_metadata(
            self.working_dir, file_pairs, unpaired_archives, unpaired_previews
        )

        self.assertTrue(result)
        mock_makedirs.assert_called_with(self.metadata_dir_path, exist_ok=True)
        mock_open_file.assert_called()
        mock_json_dump.assert_called()

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("filelock.FileLock")
    def test_load_metadata_valid_file(
        self, mock_file_lock, mock_json_load, mock_open_file, mock_exists
    ):
        """Test wczytywania poprawnego pliku metadanych."""
        mock_exists.return_value = True

        # Symulacja FileLock
        mock_lock_instance = MagicMock()
        mock_file_lock.return_value = mock_lock_instance
        mock_lock_instance.__enter__.return_value = None
        mock_lock_instance.__exit__.return_value = None

        test_data = {
            "file_pairs": {"archive1.zip": {"is_favorite": True, "stars": 5}},
            "unpaired_archives": ["archive2.zip"],
            "unpaired_previews": ["preview1.jpg"],
        }
        mock_json_load.return_value = test_data

        result = metadata_manager.load_metadata(self.working_dir)

        self.assertEqual(result, test_data)
        mock_open_file.assert_called_with(
            self.metadata_file_path, "r", encoding="utf-8"
        )
        mock_json_load.assert_called_with(
            mock_open_file.return_value.__enter__.return_value
        )

    @patch("os.path.exists")
    def test_load_metadata_no_file(self, mock_exists):
        """Test wczytywania, gdy plik metadanych nie istnieje."""
        mock_exists.return_value = False

        result = metadata_manager.load_metadata(self.working_dir)

        self.assertEqual(result, metadata_manager.DEFAULT_METADATA)

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("filelock.FileLock")
    def test_load_metadata_invalid_json(
        self, mock_file_lock, mock_json_load, mock_open_file, mock_exists
    ):
        """Test wczytywania, gdy plik zawiera niepoprawny JSON."""
        mock_exists.return_value = True

        # Symulacja FileLock
        mock_lock_instance = MagicMock()
        mock_file_lock.return_value = mock_lock_instance
        mock_lock_instance.__enter__.return_value = None
        mock_lock_instance.__exit__.return_value = None

        # Symulacja błędu parsowania JSON
        mock_json_load.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        result = metadata_manager.load_metadata(self.working_dir)

        self.assertEqual(result, metadata_manager.DEFAULT_METADATA)

    def test_validate_metadata_structure(self):
        """Test funkcji _validate_metadata_structure."""
        # Poprawna struktura
        valid_metadata = {
            "file_pairs": {
                "path/to/file.zip": {
                    "is_favorite": True,
                    "stars": 3,
                    "color_tag": "red",
                }
            },
            "unpaired_archives": ["path/to/archive.rar"],
            "unpaired_previews": ["path/to/preview.jpg"],
        }
        self.assertTrue(metadata_manager._validate_metadata_structure(valid_metadata))

        # Brakujący klucz - powinien zostać uzupełniony i zwrócić True
        missing_key_metadata = {"file_pairs": {}}
        self.assertTrue(
            metadata_manager._validate_metadata_structure(missing_key_metadata)
        )
        self.assertIn("unpaired_archives", missing_key_metadata)
        self.assertIn("unpaired_previews", missing_key_metadata)

        # Nieprawidłowy typ dla klucza głównego
        invalid_type_metadata = {
            "file_pairs": "not_a_dict",
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        self.assertFalse(
            metadata_manager._validate_metadata_structure(invalid_type_metadata)
        )

    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load")
    @patch("filelock.FileLock")
    def test_get_all_favorite_relative_paths(
        self, mock_file_lock, mock_json_load, mock_open_file, mock_exists
    ):
        """Test funkcji get_all_favorite_relative_paths."""
        mock_exists.return_value = True

        # Symulacja FileLock
        mock_lock_instance = MagicMock()
        mock_file_lock.return_value = mock_lock_instance
        mock_lock_instance.__enter__.return_value = None
        mock_lock_instance.__exit__.return_value = None

        test_data = {
            "file_pairs": {
                "path/to/file1.zip": {"is_favorite": True, "stars": 5},
                "path/to/file2.zip": {"is_favorite": False, "stars": 1},
                "another/fav.rar": {"is_favorite": True, "stars": 3},
            },
            "unpaired_archives": [],
            "unpaired_previews": [],
        }
        mock_json_load.return_value = test_data

        favorite_paths = metadata_manager.get_all_favorite_relative_paths(
            self.working_dir
        )

        self.assertEqual(len(favorite_paths), 2)
        self.assertIn("path/to/file1.zip", favorite_paths)
        self.assertIn("another/fav.rar", favorite_paths)
        self.assertNotIn("path/to/file2.zip", favorite_paths)


if __name__ == "__main__":
    # Utwórz i uruchom runner dla testów, by wyświetlić podsumowanie testów
    from unittest import TextTestRunner

    suite = unittest.TestLoader().loadTestsFromTestCase(TestMetadataManager)
    print("\n=== Uruchamianie testów dla metadata_manager.py ===\n")
    result = TextTestRunner(verbosity=2).run(suite)
    print(f"\n=== Wyniki testów: ukończono {result.testsRun} testów ===")
    print(f"Błędy: {len(result.errors)}, Niepowodzenia: {len(result.failures)}")
