"""
Testy podstawowe dla modułu scanner.py
"""

import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Import testowanego modułu
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.logic.scanner import (
    ScanningInterrupted,
    clear_cache,
    collect_files,
    create_file_pairs,
    identify_unpaired_files,
    is_cache_valid,
    scan_folder_for_pairs,
)


class TestScannerBasic(unittest.TestCase):
    """Testy podstawowe dla modułu scanner."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Tworzymy tymczasowy katalog
        self.test_dir = tempfile.mkdtemp()

        # Tworzymy strukturę katalogów i plików do testów
        self.subdir1 = os.path.join(self.test_dir, "subdir1")
        self.subdir2 = os.path.join(self.test_dir, "subdir2")
        os.makedirs(self.subdir1)
        os.makedirs(self.subdir2)

        # Tworzymy pliki testowe
        self.create_test_files()

        # Czyścimy bufor przed każdym testem
        clear_cache()

    def tearDown(self):
        """Sprzątanie po testach."""
        # Usuwamy tymczasowy katalog
        shutil.rmtree(self.test_dir)

    def create_test_files(self):
        """Tworzy pliki testowe w katalogach testowych."""
        # Para 1 w głównym katalogu
        self.file1_archive = os.path.join(self.test_dir, "file1.step")
        self.file1_preview = os.path.join(self.test_dir, "file1.png")

        # Para 2 w podkatalogu 1
        self.file2_archive = os.path.join(self.subdir1, "file2.stl")
        self.file2_preview = os.path.join(self.subdir1, "file2.jpg")

        # Pojedyncze pliki w podkatalogu 2
        self.file3_archive = os.path.join(self.subdir2, "file3.step")
        self.file4_preview = os.path.join(self.subdir2, "file4.png")

        # Tworzymy puste pliki
        for file_path in [
            self.file1_archive,
            self.file1_preview,
            self.file2_archive,
            self.file2_preview,
            self.file3_archive,
            self.file4_preview,
        ]:
            with open(file_path, "w") as f:
                f.write("test content")

    def test_collect_files_basic(self):
        """Test podstawowy zbierania plików."""
        # Zbieramy pliki z głównego katalogu
        file_map = collect_files(self.test_dir)

        # Sprawdzamy czy mamy wszystkie pliki
        self.assertEqual(len(file_map), 5)  # 5 unikalnych nazw bazowych

        # Sprawdzamy pojedynczą parę w głównym katalogu
        base_name = os.path.join(self.test_dir, "file1").lower()
        self.assertIn(base_name, file_map)
        self.assertEqual(len(file_map[base_name]), 2)  # 2 pliki dla tej nazwy bazowej

    def test_collect_files_max_depth(self):
        """Test zbierania plików z ograniczoną głębokością."""
        # Tylko główny katalog (głębokość 0)
        file_map = collect_files(self.test_dir, max_depth=0)
        self.assertEqual(len(file_map), 1)  # Tylko para w głównym katalogu

        # Główny katalog i pierwszy poziom podkatalogów
        file_map = collect_files(self.test_dir, max_depth=1)
        self.assertEqual(len(file_map), 5)  # Wszystkie pliki

    def test_collect_files_interrupt(self):
        """Test przerwania zbierania plików."""

        # Funkcja zawsze przerywająca skanowanie
        def interrupt_always():
            return True

        # Powinno rzucić wyjątek ScanningInterrupted
        with self.assertRaises(ScanningInterrupted):
            collect_files(self.test_dir, interrupt_check=interrupt_always)

    def test_create_file_pairs_basic(self):
        """Test tworzenia par plików."""
        # Najpierw zbieramy pliki
        file_map = collect_files(self.test_dir)

        # Tworzymy pary
        pairs, processed = create_file_pairs(file_map, self.test_dir)

        # Sprawdzamy pary
        self.assertEqual(len(pairs), 2)  # 2 pary (file1 i file2)
        self.assertEqual(len(processed), 4)  # 4 pliki zostały sparowane

        # Sprawdzamy czy pliki file1 są w pierwszej parze
        self.assertTrue(
            any(
                p.archive_path == self.file1_archive
                and p.preview_path == self.file1_preview
                for p in pairs
            )
        )

    def test_create_file_pairs_not_all(self):
        """Test tworzenia tylko pierwszej pary."""
        # Najpierw zbieramy pliki
        file_map = collect_files(self.test_dir)

        # Tworzymy tylko pierwsze pary
        pairs, processed = create_file_pairs(file_map, self.test_dir, pair_all=False)

        # Powinny być maksymalnie 2 pary (jedna dla każdej unikalnej nazwy bazowej)
        self.assertEqual(len(pairs), 2)

    def test_identify_unpaired_files(self):
        """Test identyfikacji niesparowanych plików."""
        # Najpierw zbieramy pliki
        file_map = collect_files(self.test_dir)

        # Symulujemy przetworzenie niektórych plików
        processed = {
            self.file1_archive,
            self.file1_preview,
            self.file2_archive,
            self.file2_preview,
        }

        # Identyfikujemy niesparowane pliki
        unpaired_archives, unpaired_previews = identify_unpaired_files(
            file_map, processed
        )

        # Sprawdzamy wyniki
        self.assertEqual(len(unpaired_archives), 1)  # file3.step
        self.assertEqual(len(unpaired_previews), 1)  # file4.png
        self.assertIn(self.file3_archive, unpaired_archives)
        self.assertIn(self.file4_preview, unpaired_previews)

    def test_scan_folder_for_pairs_basic(self):
        """Test skanowania katalogu w poszukiwaniu par."""
        # Skanujemy katalog
        pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
            self.test_dir
        )

        # Sprawdzamy wyniki
        self.assertEqual(len(pairs), 2)  # file1 i file2
        self.assertEqual(len(unpaired_archives), 1)  # file3.step
        self.assertEqual(len(unpaired_previews), 1)  # file4.png

    def test_scan_folder_for_pairs_max_depth(self):
        """Test skanowania z ograniczoną głębokością."""
        # Skanujemy tylko główny katalog
        pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
            self.test_dir, max_depth=0
        )

        # Sprawdzamy wyniki - tylko para w głównym katalogu
        self.assertEqual(len(pairs), 1)
        self.assertEqual(len(unpaired_archives), 0)
        self.assertEqual(len(unpaired_previews), 0)

    def test_scan_folder_for_pairs_cache(self):
        """Test buforowania wyników skanowania."""
        # Pierwsze skanowanie
        start_time = time.time()
        pairs1, unpaired1_a, unpaired1_p = scan_folder_for_pairs(self.test_dir)
        first_scan_time = time.time() - start_time

        # Drugie skanowanie (powinno być z bufora, więc szybsze)
        start_time = time.time()
        pairs2, unpaired2_a, unpaired2_p = scan_folder_for_pairs(self.test_dir)
        second_scan_time = time.time() - start_time

        # Sprawdzamy czy wyniki są takie same
        self.assertEqual(len(pairs1), len(pairs2))
        self.assertEqual(len(unpaired1_a), len(unpaired2_a))
        self.assertEqual(len(unpaired1_p), len(unpaired2_p))

        # Drugie skanowanie powinno być szybsze (z bufora)
        self.assertLess(second_scan_time, first_scan_time)

        # Wyłączenie bufora - powinno wymusić ponowne skanowanie
        start_time = time.time()
        pairs3, unpaired3_a, unpaired3_p = scan_folder_for_pairs(
            self.test_dir, use_cache=False
        )
        third_scan_time = time.time() - start_time

        # Powinno być wolniejsze niż drugie skanowanie (które było z bufora)
        self.assertGreater(third_scan_time, second_scan_time)

    def test_is_cache_valid(self):
        """Test sprawdzania ważności bufora."""
        # Najpierw zbieramy pliki, aby wypełnić bufor
        collect_files(self.test_dir)

        # Bufor powinien być ważny
        self.assertTrue(is_cache_valid(self.test_dir))

        # Dodajemy nowy plik - bufor powinien być nieważny
        new_file = os.path.join(self.test_dir, "new_file.step")
        with open(new_file, "w") as f:
            f.write("new content")

        # Bufor powinien być nieważny
        self.assertFalse(is_cache_valid(self.test_dir))

    def test_clear_cache(self):
        """Test czyszczenia bufora."""
        # Najpierw zbieramy pliki, aby wypełnić bufor
        collect_files(self.test_dir)

        # Bufor powinien być ważny
        self.assertTrue(is_cache_valid(self.test_dir))

        # Czyścimy bufor
        clear_cache()

        # Bufor powinien być nieważny
        self.assertFalse(is_cache_valid(self.test_dir))


if __name__ == "__main__":
    unittest.main()
