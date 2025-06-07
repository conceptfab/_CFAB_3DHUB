"""
Testy jednostkowe dla modułu scanner.py
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import pytest

from src.logic.scanner import (
    ScanningInterrupted,
    _cleanup_old_cache_entries,
    _files_cache,
    _scan_cache,
    clear_cache,
    collect_files,
    create_file_pairs,
    get_directory_modification_time,
    identify_unpaired_files,
    is_cache_valid,
    scan_folder_for_pairs,
)
from src.models.file_pair import FilePair


class TestScanner(unittest.TestCase):
    """Testy jednostkowe dla modułu scanner.py"""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Tworzenie tymczasowego katalogu do testów
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = self.temp_dir.name

        # Tworzenie przykładowej struktury plików do testów
        self.create_test_files()

        # Czyszczenie cache przed każdym testem
        clear_cache()

    def tearDown(self):
        """Czyszczenie po testach."""
        # Usuwanie tymczasowego katalogu
        self.temp_dir.cleanup()
        # Czyszczenie cache po każdym teście
        clear_cache()

    def create_test_files(self):
        """Tworzy przykładową strukturę plików do testów."""
        # Podstawowa para plików w katalogu głównym
        self._create_file_pair("model1", ".zip", ".jpg", self.test_dir)
        self._create_file_pair("model2", ".zip", ".jpg", self.test_dir)

        # Para plików w podfolderze
        subfolder = os.path.join(self.test_dir, "subfolder1")
        os.makedirs(subfolder, exist_ok=True)
        self._create_file_pair("model3", ".zip", ".jpg", subfolder)

        # Para plików w podpodfolderze
        subsubfolder = os.path.join(subfolder, "subsubfolder")
        os.makedirs(subsubfolder, exist_ok=True)
        self._create_file_pair("model4", ".zip", ".jpg", subsubfolder)

        # Pliki z różnymi rozszerzeniami
        self._create_file_pair("model5", ".zip", ".png", self.test_dir)

        # Pliki z wieloma możliwymi podglądami
        self._create_file("multi_preview", ".zip", self.test_dir)
        self._create_file("multi_preview", ".jpg", self.test_dir)
        self._create_file("multi_preview", ".png", self.test_dir)

        # Archiwum bez podglądu
        self._create_file("solo_archive", ".zip", self.test_dir)

        # Podgląd bez archiwum
        self._create_file("solo_preview", ".jpg", self.test_dir)

    def _create_file_pair(self, base_name, archive_ext, preview_ext, directory):
        """Tworzy parę plików (archiwum + podgląd) w podanym katalogu."""
        archive_path = self._create_file(base_name, archive_ext, directory)
        preview_path = self._create_file(base_name, preview_ext, directory)
        return archive_path, preview_path

    def _create_file(self, base_name, extension, directory):
        """Tworzy plik w podanym katalogu."""
        os.makedirs(directory, exist_ok=True)
        file_path = os.path.join(directory, f"{base_name}{extension}")
        with open(file_path, "w") as f:
            f.write(f"Test content for {base_name}{extension}")
        return file_path

    def test_get_directory_modification_time(self):
        """Test funkcji get_directory_modification_time."""
        # Test dla istniejącego katalogu
        mod_time = get_directory_modification_time(self.test_dir)
        self.assertIsNotNone(mod_time)
        self.assertGreater(mod_time, 0)

        # Test dla nieistniejącego katalogu
        non_existent_dir = os.path.join(self.test_dir, "non_existent")
        mod_time = get_directory_modification_time(non_existent_dir)
        self.assertEqual(mod_time, 0)

        # Test dla błędu dostępu
        with mock.patch("os.scandir", side_effect=PermissionError("Access denied")):
            mod_time = get_directory_modification_time(self.test_dir)
            self.assertGreaterEqual(mod_time, 0)    def test_is_cache_valid(self):
        """Test funkcji is_cache_valid."""
        clear_cache()  # Upewniamy się, że cache jest pusty
        
        # Gdy jeszcze nie ma wpisów w cache, powinno zwrócić False
        normalized_dir = os.path.normpath(self.test_dir).lower().replace('\\', '/')
        self.assertFalse(normalized_dir in _files_cache)
        self.assertFalse(is_cache_valid(self.test_dir))
        
        # Wykonujemy collect_files aby zapełnić cache
        collect_files(self.test_dir)
        
        # Teraz is_cache_valid powinno zwrócić True
        self.assertTrue(normalized_dir in _files_cache)
        self.assertTrue(is_cache_valid(self.test_dir))

        # Czyszczenie cache i ponowne testowanie
        clear_cache()
        self.assertFalse(is_cache_valid(self.test_dir))

    def test_collect_files(self):
        """Test funkcji collect_files."""
        # Test podstawowy
        files = collect_files(self.test_dir, max_depth=0)
        self.assertIsInstance(files, dict)

        # Test z różnymi wartościami max_depth
        files_depth1 = collect_files(self.test_dir, max_depth=1)
        files_full_depth = collect_files(self.test_dir, max_depth=-1)

        # Głębsze skanowanie powinno znaleźć więcej plików
        self.assertGreaterEqual(len(files_full_depth), len(files_depth1))
        self.assertGreaterEqual(len(files_depth1), len(files))

        # Test z funkcją postępu
        progress_values = []

        def progress_callback(progress, message=None):
            progress_values.append(progress)

        collect_files(self.test_dir, progress_callback=progress_callback)
        self.assertGreater(len(progress_values), 0)
        self.assertEqual(progress_values[-1], 100)  # Ostatnia wartość powinna być 100%

    def test_create_file_pairs(self):
        """Test funkcji create_file_pairs."""
        # Zbieramy pliki
        file_map = collect_files(
            self.test_dir, max_depth=-1
        )  # Użyj max_depth=-1, aby znaleźć wszystkie pliki

        # Tworzymy pary
        pairs, processed = create_file_pairs(file_map, self.test_dir)

        # Sprawdzamy rezultaty
        self.assertIsInstance(pairs, list)
        self.assertGreater(len(pairs), 0)  # Upewnij się, że znaleziono jakieś pary

        # Test z podfolderami
        file_map_depth = collect_files(self.test_dir, max_depth=-1)
        pairs_depth, _ = create_file_pairs(file_map_depth, self.test_dir)
        self.assertGreater(len(pairs_depth), 0)  # Upewnij się, że znaleziono pary

        # Test strategii best_match
        pairs_best_match, _ = create_file_pairs(
            file_map, self.test_dir, pair_strategy="best_match"
        )
        multi_preview_pairs = [
            p for p in pairs_best_match if "multi_preview" in p.archive_path
        ]
        self.assertEqual(len(multi_preview_pairs), 1)  # Powinna być tylko jedna para

    def test_identify_unpaired_files(self):
        """Test funkcji identify_unpaired_files."""
        file_map = collect_files(self.test_dir)
        pairs, processed = create_file_pairs(file_map, self.test_dir)

        # Identyfikujemy niepowiązane pliki
        unpaired_archives, unpaired_previews = identify_unpaired_files(
            file_map, processed
        )

        # Sprawdzamy wyniki
        self.assertGreaterEqual(len(unpaired_archives), 1)  # solo_archive
        self.assertGreaterEqual(len(unpaired_previews), 1)  # co najmniej solo_preview

    def test_scan_folder_for_pairs(self):
        """Test funkcji scan_folder_for_pairs."""
        # Test skanowania katalogu
        pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
            self.test_dir
        )

        # Sprawdź, czy funkcja zwraca wyniki
        self.assertIsInstance(pairs, list)
        self.assertIsInstance(unpaired_archives, list)
        self.assertIsInstance(unpaired_previews, list)

        # Sprawdź, czy znaleziono jakieś pary
        self.assertGreater(len(pairs), 0)

        # Test użycia cache
        # Pierwsze skanowanie wypełnia cache
        start_time = time.time()
        scan_folder_for_pairs(self.test_dir)
        first_scan_time = time.time() - start_time

        # Drugie skanowanie powinno być szybsze dzięki użyciu cache
        start_time = time.time()
        scan_folder_for_pairs(self.test_dir, use_cache=True)
        second_scan_time = time.time() - start_time

        # Drugie skanowanie (z cache) powinno być szybsze
        self.assertLess(second_scan_time, first_scan_time)

        # Test z funkcją postępu
        progress_values = []

        def progress_callback(progress, message=None):
            progress_values.append(progress)

        scan_folder_for_pairs(self.test_dir, progress_callback=progress_callback)
        self.assertGreater(len(progress_values), 0)
        self.assertEqual(progress_values[-1], 100)  # Ostatnia wartość powinna być 100%

    def test_scanning_interrupted(self):
        """Test przerwania skanowania."""
        interrupt_after_count = 2
        count = 0

        def interrupt_check():
            nonlocal count
            count += 1
            return count > interrupt_after_count

        # Powinno rzucić wyjątek ScanningInterrupted
        with self.assertRaises(ScanningInterrupted):
            collect_files(self.test_dir, interrupt_check=interrupt_check)

    def test_clear_cache(self):
        """Test funkcji clear_cache."""
        # Najpierw wypełniamy cache
        scan_folder_for_pairs(self.test_dir)
        self.assertGreater(len(_scan_cache), 0)
        self.assertGreater(len(_files_cache), 0)

        # Czyszczenie cache
        clear_cache()
        self.assertEqual(len(_scan_cache), 0)
        self.assertEqual(len(_files_cache), 0)

    def test_cleanup_old_cache_entries(self):
        """Test funkcji _cleanup_old_cache_entries."""
        # Wypełniamy cache sztucznymi danymi
        for i in range(100):
            _files_cache[f"test_dir_{i}"] = (
                time.time() - 3700,
                {},
            )  # Stare wpisy (starsze niż godzina)

        # Dodajemy jeden świeży wpis
        _files_cache["fresh_entry"] = (time.time(), {})

        # Wywołanie funkcji czyszczącej
        _cleanup_old_cache_entries()

        # Wszystkie stare wpisy powinny być usunięte
        self.assertEqual(len(_files_cache), 1)
        self.assertIn("fresh_entry", _files_cache)
