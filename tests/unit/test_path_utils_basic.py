"""
Testy podstawowe dla modułu path_utils.
Testują podstawowe funkcjonalności związane z normalizacją ścieżek.
"""

import os
import sys
import unittest
from pathlib import Path

# Import testowanego modułu
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.utils.path_utils import (
    is_absolute,
    is_path_valid,
    normalize_path,
    safe_join_paths,
    to_absolute_path,
    to_relative_path,
)


class TestPathUtilsBasic(unittest.TestCase):
    """Testy podstawowych funkcji modułu path_utils."""

    def test_normalize_path_empty(self):
        """Test normalizacji pustej ścieżki."""
        self.assertEqual(normalize_path(""), "")
        self.assertEqual(normalize_path(None), "")

    def test_normalize_path_simple(self):
        """Test normalizacji prostych ścieżek."""
        # Ścieżki Windows
        self.assertEqual(normalize_path("C:\\folder\\file.txt"), "C:/folder/file.txt")
        self.assertEqual(normalize_path("C:/folder/file.txt"), "C:/folder/file.txt")

        # Ścieżki Unix
        self.assertEqual(normalize_path("/usr/local/bin"), "/usr/local/bin")

        # Ścieżki z wieloma separatorami
        self.assertEqual(normalize_path("path///to////file"), "path/to/file")
        self.assertEqual(normalize_path("path\\\\to\\\\\\file"), "path/to/file")

    def test_normalize_path_with_dots(self):
        """Test normalizacji ścieżek z kropkami."""
        self.assertEqual(normalize_path("../folder/file"), "../folder/file")
        self.assertEqual(normalize_path("./folder/file"), "folder/file")
        self.assertEqual(normalize_path("folder/./file"), "folder/file")
        self.assertEqual(normalize_path("folder/../file"), "file")

    def test_is_path_valid(self):
        """Test walidacji poprawności ścieżki."""
        # Poprawne ścieżki
        self.assertTrue(is_path_valid("file.txt"))
        self.assertTrue(is_path_valid("/tmp/file.txt"))
        self.assertTrue(is_path_valid("C:/Windows/System32"))

        # Niepoprawne ścieżki (tylko w Windows)
        if sys.platform == "win32":
            self.assertFalse(is_path_valid("file?.txt"))  # niedozwolony znak ?
            self.assertFalse(is_path_valid("file|txt"))  # niedozwolony znak |
            self.assertFalse(is_path_valid('file"txt'))  # niedozwolony znak "

        # Niepoprawne ścieżki (wszystkie systemy)
        self.assertFalse(is_path_valid(""))
        self.assertFalse(is_path_valid(None))

    def test_safe_join_paths(self):
        """Test bezpiecznego łączenia ścieżek."""
        # Podstawowe łączenie
        self.assertEqual(
            safe_join_paths("folder", "subfolder", "file.txt"),
            "folder/subfolder/file.txt",
        )

        # Łączenie z pustymi elementami
        self.assertEqual(safe_join_paths("folder", "", "file.txt"), "folder/file.txt")

        # Łączenie ścieżek bezwzględnych
        if sys.platform == "win32":
            self.assertEqual(
                safe_join_paths("C:", "folder", "file.txt"), "C:/folder/file.txt"
            )
        else:
            self.assertEqual(safe_join_paths("/usr", "local", "bin"), "/usr/local/bin")

        # Puste wejście
        self.assertEqual(safe_join_paths(), "")
        self.assertEqual(safe_join_paths(""), "")
        self.assertEqual(safe_join_paths("", "", ""), "")

    def test_is_absolute(self):
        """Test sprawdzania czy ścieżka jest absolutna."""
        # Ścieżki absolutne
        if sys.platform == "win32":
            self.assertTrue(is_absolute("C:\\folder\\file.txt"))
            self.assertTrue(is_absolute("C:/folder/file.txt"))
        else:
            self.assertTrue(is_absolute("/usr/local/bin"))

        # Ścieżki względne
        self.assertFalse(is_absolute("folder/file.txt"))
        self.assertFalse(is_absolute("../folder/file.txt"))
        self.assertFalse(is_absolute("./file.txt"))
        self.assertFalse(is_absolute(""))
        self.assertFalse(is_absolute(None))

    def test_to_absolute_path(self):
        """Test konwersji ścieżki względnej na absolutną."""
        # Obecny katalog roboczy jako baza
        cwd = os.getcwd()
        normalized_cwd = normalize_path(cwd)

        # Ścieżka względna z bieżącego katalogu
        self.assertEqual(to_absolute_path("file.txt"), f"{normalized_cwd}/file.txt")

        # Z podaną ścieżką bazową
        base = "C:/base" if sys.platform == "win32" else "/base"
        self.assertEqual(to_absolute_path("file.txt", base), f"{base}/file.txt")

        # Ścieżka już absolutna
        if sys.platform == "win32":
            self.assertEqual(
                to_absolute_path("C:/folder/file.txt"), "C:/folder/file.txt"
            )
        else:
            self.assertEqual(to_absolute_path("/usr/local/bin"), "/usr/local/bin")

        # Puste wejście
        self.assertEqual(to_absolute_path(""), "")

    def test_to_relative_path(self):
        """Test konwersji ścieżki absolutnej na względną."""
        # Standardowa konwersja
        if sys.platform == "win32":
            self.assertEqual(
                to_relative_path("C:/base/folder/file.txt", "C:/base"),
                "folder/file.txt",
            )
        else:
            self.assertEqual(
                to_relative_path("/base/folder/file.txt", "/base"), "folder/file.txt"
            )

        # Ścieżka poza bazową
        if sys.platform == "win32":
            self.assertEqual(
                to_relative_path("C:/other/file.txt", "C:/base"), "../other/file.txt"
            )
        else:
            self.assertEqual(
                to_relative_path("/other/file.txt", "/base"), "../other/file.txt"
            )

        # Identyczne ścieżki
        self.assertEqual(to_relative_path("/same/path", "/same/path"), ".")

        # Puste wejścia
        self.assertEqual(to_relative_path("", "base"), "")
        self.assertEqual(to_relative_path("path", ""), "path")


if __name__ == "__main__":
    unittest.main()
