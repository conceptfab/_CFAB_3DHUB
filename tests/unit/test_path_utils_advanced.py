"""
Testy zaawansowane dla modułu path_utils.
Testują funkcjonalności związane z URL i ścieżkami UNC.
"""

import os
import sys
import unittest
from pathlib import Path

# Import testowanego modułu
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.utils.path_utils import (
    get_directory_name,
    get_parent_directory,
    get_path_type,
    is_unc_path,
    is_url,
    normalize_path,
    parse_url,
    path_exists,
)


class TestPathUtilsAdvanced(unittest.TestCase):
    """Testy zaawansowanych funkcji modułu path_utils."""

    def test_is_url(self):
        """Test sprawdzania, czy ścieżka jest URL-em."""
        # Poprawne URL-e
        self.assertTrue(is_url("http://example.com"))
        self.assertTrue(is_url("https://example.com/path/to/file"))
        self.assertTrue(is_url("ftp://example.com/file.txt"))

        # Nieprawidłowe URL-e
        self.assertFalse(is_url("example.com"))  # brak protokołu
        self.assertFalse(is_url("http://"))  # brak hosta
        self.assertFalse(is_url("C:/path/to/file"))
        self.assertFalse(is_url("/path/to/file"))
        self.assertFalse(is_url(""))
        self.assertFalse(is_url(None))

    def test_is_unc_path(self):
        """Test sprawdzania, czy ścieżka jest ścieżką UNC."""
        # Na Windows te testy powinny zwrócić True, na innych systemach False
        if sys.platform == "win32":
            self.assertTrue(is_unc_path("\\\\server\\share\\file.txt"))
            self.assertTrue(is_unc_path("//server/share/file.txt"))
        else:
            self.assertFalse(is_unc_path("\\\\server\\share\\file.txt"))
            self.assertFalse(is_unc_path("//server/share/file.txt"))

        # Nieprawidłowe ścieżki UNC (wszystkie systemy)
        self.assertFalse(is_unc_path("C:/path/to/file"))
        self.assertFalse(is_unc_path("/path/to/file"))
        self.assertFalse(is_unc_path(""))
        self.assertFalse(is_unc_path(None))

    def test_get_path_type(self):
        """Test określania typu ścieżki."""
        # URL
        self.assertEqual(get_path_type("http://example.com"), "url")
        self.assertEqual(get_path_type("https://example.com/path"), "url")

        # UNC (tylko Windows)
        if sys.platform == "win32":
            self.assertEqual(get_path_type("\\\\server\\share"), "unc")
            self.assertEqual(get_path_type("//server/share"), "unc")

        # Standardowe ścieżki plików
        self.assertEqual(get_path_type("file.txt"), "file")
        self.assertEqual(get_path_type("/path/to/file"), "file")
        if sys.platform == "win32":
            self.assertEqual(get_path_type("C:/Windows"), "file")

        # Nieprawidłowe ścieżki
        self.assertEqual(get_path_type(""), "invalid")
        self.assertEqual(get_path_type(None), "invalid")
        if sys.platform == "win32":
            self.assertEqual(
                get_path_type("file?txt"), "invalid"
            )  # niedozwolony znak w Windows

    def test_path_exists(self):
        """Test sprawdzania istnienia ścieżki."""
        # Istniejące ścieżki (musimy użyć ścieżki, która na pewno istnieje)
        self.assertTrue(path_exists(os.path.abspath(__file__)))

        # Na pewno nieistniejąca ścieżka
        random_nonexistent = "nonexistent_file_for_testing_12345.xyz"
        self.assertFalse(path_exists(random_nonexistent))

        # URL (zawsze false, nie sprawdzamy)
        self.assertFalse(path_exists("http://example.com"))

        # Puste ścieżki
        self.assertFalse(path_exists(""))
        self.assertFalse(path_exists(None))

    def test_parse_url(self):
        """Test parsowania URL."""
        # Standardowy URL
        self.assertEqual(
            parse_url("http://example.com/path/to/file"),
            ("http", "example.com", "/path/to/file"),
        )

        # URL z parametrami
        self.assertEqual(
            parse_url("https://example.com:8080/path?query=value"),
            ("https", "example.com:8080", "/path"),
        )

        # Niepełny URL
        self.assertEqual(parse_url("http://"), ("http", "", ""))

        # Nieprawidłowy URL
        self.assertEqual(parse_url("not-a-url"), ("", "", ""))

        # Puste wejście
        self.assertEqual(parse_url(""), ("", "", ""))
        self.assertEqual(parse_url(None), ("", "", ""))

    def test_get_directory_name(self):
        """Test pobierania nazwy katalogu."""
        # Standardowe ścieżki
        self.assertEqual(get_directory_name("/path/to/directory"), "directory")
        self.assertEqual(get_directory_name("/path/to/directory/"), "directory")

        # Ścieżki Windows
        if sys.platform == "win32":
            self.assertEqual(get_directory_name("C:\\path\\to\\directory"), "directory")
            self.assertEqual(
                get_directory_name("C:\\path\\to\\directory\\"), "directory"
            )

        # Ścieżka bez katalogu
        self.assertEqual(get_directory_name("filename.txt"), "filename.txt")

        # Puste wejście
        self.assertEqual(get_directory_name(""), "")
        self.assertEqual(get_directory_name(None), "")

    def test_get_parent_directory(self):
        """Test pobierania katalogu nadrzędnego."""
        # Standardowe ścieżki
        self.assertEqual(get_parent_directory("/path/to/file.txt"), "/path/to")
        self.assertEqual(get_parent_directory("/path/to/directory/"), "/path/to")

        # Ścieżki Windows
        if sys.platform == "win32":
            self.assertEqual(
                get_parent_directory("C:\\path\\to\\file.txt"), "C:/path/to"
            )

        # Katalog główny
        if sys.platform == "win32":
            self.assertEqual(get_parent_directory("C:/"), "C:")
        else:
            self.assertEqual(get_parent_directory("/"), "")

        # Puste wejście
        self.assertEqual(get_parent_directory(""), "")
        self.assertEqual(get_parent_directory(None), "")

    def test_normalize_path_unc(self):
        """Test normalizacji ścieżek UNC."""
        # Tylko na Windows
        if sys.platform == "win32":
            # Podstawowy test UNC
            self.assertEqual(
                normalize_path("\\\\server\\share\\file.txt"), "//server/share/file.txt"
            )
            self.assertEqual(
                normalize_path("//server/share/file.txt"), "//server/share/file.txt"
            )

            # UNC z fragmentami '..' i '.'
            self.assertEqual(
                normalize_path("\\\\server\\share\\folder\\.\\file.txt"),
                "//server/share/folder/file.txt",
            )
            self.assertEqual(
                normalize_path("\\\\server\\share\\folder\\..\\file.txt"),
                "//server/share/file.txt",
            )

    def test_normalize_path_unicode(self):
        """Test normalizacji ścieżek Unicode."""
        # Ścieżki z Unicode
        self.assertEqual(
            normalize_path("/użytkownik/dokumenty/plik.txt"),
            "/użytkownik/dokumenty/plik.txt",
        )
        self.assertEqual(normalize_path("/путь/к/файлу.txt"), "/путь/к/файлу.txt")
        self.assertEqual(normalize_path("/路径/到/文件.txt"), "/路径/到/文件.txt")


if __name__ == "__main__":
    unittest.main()
