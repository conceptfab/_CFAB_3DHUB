"""
Testy jednostkowe dla modelu FilePair.
"""

import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from src.models.file_pair import (
    FILE_SIZE_ERROR,
    TRANSFORMATION_FAST,
    TRANSFORMATION_SMOOTH,
    FilePair,
)


class TestFilePair(unittest.TestCase):
    """Testy jednostkowe dla klasy FilePair"""

    def setUp(self):
        """Przygotowanie środowiska testowego przed każdym testem."""
        # Tworzenie ścieżek testowych (nie tworzymy rzeczywistych plików)
        self.working_dir = str(Path("C:/test_working_dir").absolute())
        self.archive_path = str(Path("C:/test_working_dir/test_archive.zip").absolute())
        self.preview_path = str(Path("C:/test_working_dir/test_preview.jpg").absolute())

    def test_init_valid_paths(self):
        """Test inicjalizacji z poprawnymi ścieżkami."""
        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)
        self.assertEqual(pair.archive_path, self.archive_path.replace("\\", "/"))
        self.assertEqual(pair.preview_path, self.preview_path.replace("\\", "/"))
        self.assertEqual(pair.working_directory, self.working_dir.replace("\\", "/"))
        self.assertEqual(pair.base_name, "test_archive")

    def test_init_none_preview(self):
        """Test inicjalizacji z preview=None."""
        pair = FilePair(self.archive_path, None, self.working_dir)
        self.assertEqual(pair.archive_path, self.archive_path.replace("\\", "/"))
        self.assertIsNone(pair.preview_path)
        self.assertEqual(pair.base_name, "test_archive")

    @patch("os.path.isabs")
    def test_init_invalid_paths(self, mock_isabs):
        """Test inicjalizacji z nieprawidłowymi (względnymi) ścieżkami."""
        # Symulujemy, że pierwsza ścieżka nie jest absolutna
        mock_isabs.side_effect = [False, True, True]
        with self.assertRaises(ValueError):
            FilePair(self.archive_path, self.preview_path, self.working_dir)

        # Symulujemy, że druga ścieżka nie jest absolutna
        mock_isabs.side_effect = [True, False, True]
        with self.assertRaises(ValueError):
            FilePair(self.archive_path, self.preview_path, self.working_dir)

        # Symulujemy, że katalog roboczy nie jest absolutną ścieżką
        mock_isabs.side_effect = [True, True, False]
        with self.assertRaises(ValueError):
            FilePair(self.archive_path, self.preview_path, self.working_dir)

    def test_get_archive_path(self):
        """Test metody get_archive_path."""
        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)
        self.assertEqual(pair.get_archive_path(), self.archive_path.replace("\\", "/"))

    def test_get_preview_path(self):
        """Test metody get_preview_path."""
        # Z podaną ścieżką podglądu
        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)
        self.assertEqual(pair.get_preview_path(), self.preview_path.replace("\\", "/"))

        # Z None jako ścieżka podglądu
        pair = FilePair(self.archive_path, None, self.working_dir)
        self.assertIsNone(pair.get_preview_path())

    def test_get_relative_paths(self):
        """Test metod get_relative_*_path."""
        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)

        # Oczekiwane względne ścieżki
        expected_rel_archive = "test_archive.zip"
        expected_rel_preview = "test_preview.jpg"

        self.assertEqual(pair.get_relative_archive_path(), expected_rel_archive)
        self.assertEqual(pair.get_relative_preview_path(), expected_rel_preview)

        # Dla None jako preview_path
        pair = FilePair(self.archive_path, None, self.working_dir)
        self.assertIsNone(pair.get_relative_preview_path())

    def test_get_base_name(self):
        """Test metody get_base_name."""
        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)
        self.assertEqual(pair.get_base_name(), "test_archive")

    @patch("os.path.exists")
    @patch("PyQt6.QtGui.QPixmap")
    def test_load_preview_thumbnail_success(self, mock_qpixmap, mock_exists):
        """Test ładowania miniatury - przypadek sukcesu."""
        mock_exists.return_value = True
        mock_pixmap = MagicMock()
        mock_pixmap.isNull.return_value = False
        mock_qpixmap.return_value = mock_pixmap

        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)
        pair.load_preview_thumbnail(100)

        # Sprawdzamy, czy QPixmap zostało stworzone z odpowiednią ścieżką
        mock_qpixmap.assert_called_once_with(self.preview_path.replace("\\", "/"))
        # Sprawdzamy, czy wywołano skalowanie
        mock_pixmap.scaled.assert_called_once()
        # Sprawdzamy, czy użyto domyślnego trybu transformacji
        _, kwargs = mock_pixmap.scaled.call_args
        self.assertEqual(kwargs["transformMode"], TRANSFORMATION_SMOOTH)

    @patch("os.path.exists")
    @patch("PyQt6.QtGui.QPixmap")
    def test_load_preview_thumbnail_fast_transform(self, mock_qpixmap, mock_exists):
        """Test ładowania miniatury z trybem FAST."""
        mock_exists.return_value = True
        mock_pixmap = MagicMock()
        mock_pixmap.isNull.return_value = False
        mock_qpixmap.return_value = mock_pixmap

        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)
        pair.load_preview_thumbnail(100, TRANSFORMATION_FAST)

        # Sprawdzamy, czy użyto szybkiego trybu transformacji
        _, kwargs = mock_pixmap.scaled.call_args
        self.assertEqual(kwargs["transformMode"], TRANSFORMATION_FAST)

    @patch("os.path.exists")
    @patch("PyQt6.QtGui.QPixmap")
    def test_load_preview_thumbnail_file_not_exists(self, mock_qpixmap, mock_exists):
        """Test ładowania miniatury gdy plik nie istnieje."""
        mock_exists.return_value = False

        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)
        pair.load_preview_thumbnail(100)

        # Sprawdzamy, czy utworzono placeholder
        mock_qpixmap.assert_called_with(100, 100)
        mock_qpixmap.return_value.fill.assert_called_once_with(Qt.GlobalColor.gray)

    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_get_archive_size_success(self, mock_getsize, mock_exists):
        """Test pobierania rozmiaru archiwum - przypadek sukcesu."""
        mock_exists.return_value = True
        mock_getsize.return_value = 1024  # 1 KB

        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)
        size = pair.get_archive_size()

        self.assertEqual(size, 1024)
        mock_getsize.assert_called_once_with(self.archive_path.replace("\\", "/"))

    @patch("os.path.exists")
    def test_get_archive_size_file_not_exists(self, mock_exists):
        """Test pobierania rozmiaru gdy plik nie istnieje."""
        mock_exists.return_value = False

        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)
        size = pair.get_archive_size()

        self.assertEqual(size, FILE_SIZE_ERROR)

    @patch("os.path.exists")
    @patch("os.path.getsize")
    def test_get_archive_size_error(self, mock_getsize, mock_exists):
        """Test pobierania rozmiaru gdy wystąpił błąd."""
        mock_exists.return_value = True
        mock_getsize.side_effect = OSError("Test error")

        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)
        size = pair.get_archive_size()

        self.assertEqual(size, FILE_SIZE_ERROR)

    def test_get_formatted_archive_size(self):
        """Test formatowania rozmiaru pliku."""
        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)

        # Testowanie różnych wielkości
        test_cases = [
            (None, "N/A"),
            (FILE_SIZE_ERROR, "N/A"),
            (0, "N/A"),
            (500, "500 B"),
            (1500, "1.5 KB"),
            (1500000, "1.4 MB"),
            (1500000000, "1.4 GB"),
        ]

        for size, expected in test_cases:
            pair.archive_size_bytes = size
            self.assertEqual(pair.get_formatted_archive_size(), expected)

    def test_set_get_stars(self):
        """Test ustawiania i pobierania liczby gwiazdek."""
        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)

        # Testowanie poprawnych wartości
        for stars in range(6):  # 0-5
            result = pair.set_stars(stars)
            self.assertEqual(result, stars)
            self.assertEqual(pair.get_stars(), stars)

        # Testowanie niepoprawnych wartości
        invalid_values = [-1, 6, 10, "3"]
        for value in invalid_values:
            result = pair.set_stars(value)
            self.assertEqual(result, 0)
            self.assertEqual(pair.get_stars(), 0)

    def test_set_get_color_tag(self):
        """Test ustawiania i pobierania tagu koloru."""
        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)

        # Testowanie różnych wartości
        test_values = [
            "#FF0000",  # czerwony
            "#00FF00",  # zielony
            "",  # pusty string
            None,  # None
        ]

        for value in test_values:
            result = pair.set_color_tag(value)
            self.assertEqual(result, value)
            self.assertEqual(pair.get_color_tag(), value)

    def test_repr(self):
        """Test metody __repr__."""
        pair = FilePair(self.archive_path, self.preview_path, self.working_dir)
        repr_str = repr(pair)

        # Sprawdzamy, czy __repr__ zawiera oczekiwane informacje
        self.assertIn("FilePair", repr_str)
        self.assertIn("test_archive", repr_str)
        self.assertIn("test_archive.zip", repr_str)
        self.assertIn("test_preview.jpg", repr_str)


if __name__ == "__main__":
    unittest.main()
