"""
Testy wydajnościowe dla modułu path_utils.
Sprawdzają szybkość działania funkcji przy dużej liczbie operacji.
"""

import os
import sys
import time
import unittest
from pathlib import Path

# Import testowanego modułu
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.utils.path_utils import (
    get_path_type,
    is_path_valid,
    is_unc_path,
    is_url,
    normalize_path,
    safe_join_paths,
    to_absolute_path,
    to_relative_path,
)


class TestPathUtilsPerformance(unittest.TestCase):
    """Testy wydajnościowe dla modułu path_utils."""

    def setUp(self):
        """Przygotowanie danych do testów wydajnościowych."""
        # Liczba powtórzeń w testach
        self.iterations = 10000

        # Przykładowe ścieżki do testów
        self.test_paths = [
            "C:\\Windows\\System32\\drivers\\etc\\hosts",
            "/usr/local/bin/python3",
            "relative/path/to/file.txt",
            "../parent/path/file.txt",
            "file_with_unicode_żółć.txt",
            "http://example.com/path/to/resource",
            "\\\\server\\share\\file.txt",
            "path/with/multiple/segments/and/a/very/long/name/that/exceeds/typical/length/limits/file.txt",
            "//server/share/path/to/file.txt",
            "./current/directory/file.txt",
        ]

    def test_normalize_path_performance(self):
        """Test wydajności funkcji normalize_path."""
        start_time = time.time()

        for _ in range(self.iterations):
            for path in self.test_paths:
                normalize_path(path)

        elapsed_time = time.time() - start_time
        print(
            f"\nCzas wykonania {self.iterations * len(self.test_paths)} "
            f"normalizacji ścieżek: {elapsed_time:.4f} sekund"
        )

        # Test powinien zakończyć się w rozsądnym czasie
        self.assertLess(elapsed_time, 10.0, "Normalizacja ścieżek trwa zbyt długo")

    def test_is_path_valid_performance(self):
        """Test wydajności funkcji is_path_valid."""
        start_time = time.time()

        for _ in range(self.iterations):
            for path in self.test_paths:
                is_path_valid(path)

        elapsed_time = time.time() - start_time
        print(
            f"\nCzas wykonania {self.iterations * len(self.test_paths)} "
            f"walidacji ścieżek: {elapsed_time:.4f} sekund"
        )

        # Test powinien zakończyć się w rozsądnym czasie
        self.assertLess(elapsed_time, 10.0, "Walidacja ścieżek trwa zbyt długo")

    def test_safe_join_paths_performance(self):
        """Test wydajności funkcji safe_join_paths."""
        start_time = time.time()

        for _ in range(self.iterations):
            for i in range(len(self.test_paths) - 1):
                safe_join_paths(self.test_paths[i], self.test_paths[i + 1])

        elapsed_time = time.time() - start_time
        print(
            f"\nCzas wykonania {self.iterations * (len(self.test_paths)-1)} "
            f"operacji łączenia ścieżek: {elapsed_time:.4f} sekund"
        )

        # Test powinien zakończyć się w rozsądnym czasie
        self.assertLess(elapsed_time, 10.0, "Łączenie ścieżek trwa zbyt długo")

    def test_path_conversion_performance(self):
        """Test wydajności funkcji konwersji ścieżek."""
        start_time = time.time()
        base_path = os.getcwd()

        for _ in range(self.iterations):
            for path in self.test_paths:
                if not path.startswith("http") and not path.startswith("//"):
                    abs_path = to_absolute_path(path, base_path)
                    to_relative_path(abs_path, base_path)

        elapsed_time = time.time() - start_time
        print(
            f"\nCzas wykonania {self.iterations * len(self.test_paths)} "
            f"konwersji ścieżek: {elapsed_time:.4f} sekund"
        )

        # Test powinien zakończyć się w rozsądnym czasie
        self.assertLess(elapsed_time, 10.0, "Konwersja ścieżek trwa zbyt długo")

    def test_path_type_detection_performance(self):
        """Test wydajności funkcji wykrywania typów ścieżek."""
        start_time = time.time()

        for _ in range(self.iterations):
            for path in self.test_paths:
                get_path_type(path)
                is_url(path)
                is_unc_path(path)

        elapsed_time = time.time() - start_time
        print(
            f"\nCzas wykonania {self.iterations * len(self.test_paths) * 3} "
            f"operacji wykrywania typów ścieżek: {elapsed_time:.4f} sekund"
        )

        # Test powinien zakończyć się w rozsądnym czasie
        self.assertLess(elapsed_time, 10.0, "Wykrywanie typów ścieżek trwa zbyt długo")


if __name__ == "__main__":
    unittest.main()
