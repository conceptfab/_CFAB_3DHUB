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
    clear_cache,
    collect_files,
    create_file_pairs,
    get_directory_modification_time,
    identify_unpaired_files,
    is_cache_valid,
    scan_folder_for_pairs,
    _cleanup_old_cache_entries,
    _scan_cache,
    _files_cache,
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
    clear_cache,
    collect_files,
    create_file_pairs,
    get_directory_modification_time,
    identify_unpaired_files,
    is_cache_valid,
    scan_folder_for_pairs,
    _walk_directory,
    _cleanup_old_cache_entries,
    _scan_cache,
    _files_cache,
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
        # Struktura katalogów
        os.makedirs(os.path.join(self.test_dir, "subfolder1"))
        os.makedirs(os.path.join(self.test_dir, "subfolder2"))
        os.makedirs(os.path.join(self.test_dir, "subfolder1", "subsubfolder"))

        # Tworzenie par plików
        self._create_file_pair("model1", ".zip", ".jpg", self.test_dir)
        self._create_file_pair("model2", ".rar", ".png", self.test_dir)
        self._create_file_pair("model3", ".7z", ".jpg", os.path.join(self.test_dir, "subfolder1"))
        self._create_file_pair("model4", ".zip", ".png", os.path.join(self.test_dir, "subfolder2"))
        self._create_file_pair("model5", ".zip", ".jpg", os.path.join(self.test_dir, "subfolder1", "subsubfolder"))

        # Dodatkowe pliki bez par
        self._create_file("unpaired_archive", ".zip", self.test_dir)
        self._create_file("unpaired_preview", ".png", self.test_dir)
        self._create_file("other_file", ".txt", self.test_dir)  # Nieobsługiwane rozszerzenie

        # Pliki z wieloma możliwymi podglądami
        self._create_file("multi_preview", ".zip", self.test_dir)
        self._create_file("multi_preview", ".jpg", self.test_dir)
        self._create_file("multi_preview", ".png", self.test_dir)

    def _create_file(self, base_name, ext, directory):
        """Tworzy pojedynczy plik w podanym katalogu."""
        file_path = os.path.join(directory, f"{base_name}{ext}")
        with open(file_path, "w") as f:
            f.write(f"Test content for {base_name}{ext}")
        return file_path

    def _create_file_pair(self, base_name, archive_ext, preview_ext, directory):
        """Tworzy parę plików (archiwum + podgląd) w podanym katalogu."""
        archive_path = self._create_file(base_name, archive_ext, directory)
        preview_path = self._create_file(base_name, preview_ext, directory)
        return archive_path, preview_path

    def test_get_directory_modification_time(self):
        """Test funkcji get_directory_modification_time."""
        # Kiedy katalog istnieje, powinien zwrócić czas modyfikacji
        mtime = get_directory_modification_time(self.test_dir)
        self.assertGreater(mtime, 0)

        # Kiedy katalog nie istnieje, powinien zwrócić 0
        mtime_nonexistent = get_directory_modification_time("/path/that/does/not/exist")
        self.assertEqual(mtime_nonexistent, 0)

        # Test obsługi błędów
        with mock.patch("os.scandir") as mock_scandir:
            mock_scandir.side_effect = PermissionError("Test error")
            # Nawet przy błędzie dostępu, funkcja powinna się nie zawiesić
            # i zwrócić jakiś czas (czas modyfikacji katalogu głównego)
            mtime_with_error = get_directory_modification_time(self.test_dir)
            self.assertGreater(mtime_with_error, 0)

    def test_is_cache_valid(self):
        """Test funkcji is_cache_valid."""
        # Na początku cache jest pusty, więc is_cache_valid powinno zwrócić False
        self.assertFalse(is_cache_valid(self.test_dir))

        # Wykonujemy collect_files aby zapełnić cache
        collect_files(self.test_dir)
        
        # Teraz cache powinien być aktualny
        self.assertTrue(is_cache_valid(self.test_dir))

        # Modyfikacja pliku w katalogu powinna unieważnić cache
        time.sleep(0.1)  # Aby upewnić się, że czas modyfikacji będzie inny
        self._create_file("new_file", ".zip", self.test_dir)
        self.assertFalse(is_cache_valid(self.test_dir))

    def test_collect_files(self):
        """Test funkcji collect_files."""
        # Test podstawowego zbierania plików
        files = collect_files(self.test_dir, max_depth=0)
        
        # Sprawdzamy liczbę znalezionych bazowych nazw plików
        expected_files = {"model1", "model2", "unpaired_archive", 
                          "unpaired_preview", "multi_preview"}
        self.assertEqual(len(files), len(expected_files))
        
        for base_name in expected_files:
            base_path = os.path.join(self.test_dir, base_name).lower().replace("\\", "/")
            self.assertTrue(any(base_path in key for key in files.keys()))

        # Test z max_depth=1 (główny katalog + jeden poziom podkatalogów)
        files_depth1 = collect_files(self.test_dir, max_depth=1)
        # Powinno znaleźć pliki z głównego katalogu + subfolder1 + subfolder2
        self.assertGreater(len(files_depth1), len(files))
        
        # Test z pełną rekursją
        files_full_depth = collect_files(self.test_dir, max_depth=-1)
        # Powinno znaleźć wszystkie pliki, w tym te z subfolder1/subsubfolder
        self.assertGreaterEqual(len(files_full_depth), len(files_depth1))

        # Test z force_refresh=True
        files_before = collect_files(self.test_dir)
        files_after = collect_files(self.test_dir, force_refresh=True)
        # Zawartość powinna być taka sama
        self.assertEqual(len(files_before), len(files_after))

    def test_create_file_pairs_first_match(self):
        """Test funkcji create_file_pairs ze strategią first_match."""
        file_map = collect_files(self.test_dir, max_depth=-1)
        pairs, processed = create_file_pairs(file_map, self.test_dir, pair_strategy="first_match")
        
        # Sprawdzamy czy poprawnie sparowano pliki
        self.assertGreaterEqual(len(pairs), 5)  # Co najmniej 5 par powinno być znalezione
        
        # Sprawdzamy czy multi_preview został sparowany tylko z pierwszym podglądem
        multi_preview_pairs = [p for p in pairs if "multi_preview" in p.archive_path]
        self.assertEqual(len(multi_preview_pairs), 1)

    def test_create_file_pairs_all_combinations(self):
        """Test funkcji create_file_pairs ze strategią all_combinations."""
        file_map = collect_files(self.test_dir, max_depth=-1)
        pairs, processed = create_file_pairs(file_map, self.test_dir, pair_strategy="all_combinations")
        
        # Sprawdzamy czy poprawnie sparowano pliki
        self.assertGreaterEqual(len(pairs), 6)  # Co najmniej 6 par powinno być znalezione
        
        # Sprawdzamy czy multi_preview został sparowany z oboma podglądami
        multi_preview_pairs = [p for p in pairs if "multi_preview" in p.archive_path]
        self.assertEqual(len(multi_preview_pairs), 2)  # Powinny być 2 pary

    def test_create_file_pairs_best_match(self):
        """Test funkcji create_file_pairs ze strategią best_match."""
        file_map = collect_files(self.test_dir, max_depth=-1)
        # Strategia best_match nie jest w pełni zaimplementowana, więc powinna działać jak first_match
        pairs, processed = create_file_pairs(file_map, self.test_dir, pair_strategy="best_match")
        
        # Na razie powinna działać jak first_match
        self.assertGreaterEqual(len(pairs), 5)
        
        # Sprawdzamy czy multi_preview został sparowany z pierwszym podglądem
        multi_preview_pairs = [p for p in pairs if "multi_preview" in p.archive_path]
        self.assertEqual(len(multi_preview_pairs), 1)

    def test_identify_unpaired_files(self):
        """Test funkcji identify_unpaired_files."""
        file_map = collect_files(self.test_dir)
        pairs, processed = create_file_pairs(file_map, self.test_dir)
        unpaired_archives, unpaired_previews = identify_unpaired_files(file_map, processed)
        
        # Powinien znaleźć dokładnie jeden niesparowany archiwum i jeden niesparowany podgląd
        self.assertEqual(len(unpaired_archives), 1)
        self.assertEqual(len(unpaired_previews), 1)
        
        # Sprawdzamy czy są to właściwe pliki
        self.assertTrue(any("unpaired_archive" in path for path in unpaired_archives))
        self.assertTrue(any("unpaired_preview" in path for path in unpaired_previews))

    def test_scan_folder_for_pairs(self):
        """Test funkcji scan_folder_for_pairs."""
        # Podstawowy test skanowania
        pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(self.test_dir)
        
        # Sprawdzamy wyniki
        self.assertGreaterEqual(len(pairs), 3)
        self.assertEqual(len(unpaired_archives), 1)
        self.assertEqual(len(unpaired_previews), 1)
        
        # Test z różnymi wartościami max_depth
        pairs_depth0, _, _ = scan_folder_for_pairs(self.test_dir, max_depth=0)
        pairs_depth1, _, _ = scan_folder_for_pairs(self.test_dir, max_depth=1)
        pairs_depth_full, _, _ = scan_folder_for_pairs(self.test_dir, max_depth=-1)
        
        self.assertLess(len(pairs_depth0), len(pairs_depth1))
        self.assertLessEqual(len(pairs_depth1), len(pairs_depth_full))
        
        # Test użycia cache
        # Pierwsze skanowanie wypełnia cache
        start_time = time.time()
        scan_folder_for_pairs(self.test_dir)
        first_scan_time = time.time() - start_time
        
        # Drugie skanowanie powinno być szybsze dzięki użyciu cache
        start_time = time.time()
        scan_folder_for_pairs(self.test_dir, use_cache=True)
        second_scan_time = time.time() - start_time
        
        # Cache powinien przyspieszyć wykonanie
        self.assertLess(second_scan_time, first_scan_time)
        
        # Test wymuszenia odświeżenia cache
        start_time = time.time()
        scan_folder_for_pairs(self.test_dir, force_refresh_cache=True)
        force_refresh_time = time.time() - start_time
        
        # Wymuszenie odświeżenia powinno zająć podobny czas jak pierwsze skanowanie
        self.assertGreater(force_refresh_time, second_scan_time)

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
            _files_cache[f"test_dir_{i}"] = (time.time() - 3700, {})  # Stare wpisy (starsze niż godzina)
            
        # Dodajemy jeden świeży wpis
        _files_cache["fresh_entry"] = (time.time(), {})
        
        # Wywołanie funkcji czyszczącej
        _cleanup_old_cache_entries()
        
        # Wszystkie stare wpisy powinny być usunięte
        self.assertEqual(len(_files_cache), 1)
        self.assertIn("fresh_entry", _files_cache)
