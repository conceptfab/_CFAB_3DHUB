"""
Testy jednostkowe dla modułu scanner.py - ETAP 3 ZAKTUALIZOWANE
Zawiera testy dla nowego ThreadSafeCache i optymalizacji
"""

import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import pytest

from src.logic.scanner import (
    ScanCacheEntry,
    ScanningInterrupted,
    ScanStatistics,
    ThreadSafeCache,
    _cleanup_old_cache_entries,
    _files_cache,
    _scan_cache,
    _unified_cache,
    clear_cache,
    collect_files,
    collect_files_streaming,
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

        # Czyszczenie cache przed każdym testem (legacy + nowy)
        clear_cache()  # Czyści zarówno legacy jak i nowy cache

    def tearDown(self):
        """Czyszczenie po testach."""
        # Usuwanie tymczasowego katalogu
        self.temp_dir.cleanup()
        # Czyszczenie cache po każdym teście (legacy + nowy)
        clear_cache()  # Czyści zarówno legacy jak i nowy cache

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
        self.assertEqual(mod_time, 0)  # Test dla błędu dostępu
        with mock.patch("os.scandir", side_effect=PermissionError("Access denied")):
            mod_time = get_directory_modification_time(self.test_dir)
            self.assertGreaterEqual(mod_time, 0)

    def test_is_cache_valid(self):
        """Test funkcji is_cache_valid."""
        clear_cache()  # Upewniamy się, że cache jest pusty

        # Gdy jeszcze nie ma wpisów w cache, powinno zwrócić False
        self.assertFalse(is_cache_valid(self.test_dir))

        # Wykonujemy collect_files aby zapełnić cache
        collect_files(self.test_dir)

        # Sprawdź, że cache został wypełniony - używamy normalize_path z modułu
        from src.utils.path_utils import normalize_path

        normalized_dir = normalize_path(self.test_dir)
        self.assertTrue(normalized_dir in _files_cache)

        # Teraz is_cache_valid powinno zwrócić True
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


class TestEtap3NewFeatures(unittest.TestCase):
    """ETAP 3: Testy nowych funkcjonalności - ThreadSafeCache, streaming, optymalizacje."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = self.temp_dir.name
        self.create_test_files()
        clear_cache()

    def tearDown(self):
        """Czyszczenie po testach."""
        self.temp_dir.cleanup()
        clear_cache()

    def create_test_files(self):
        """Tworzy strukturę plików do testów ETAP 3."""
        # Większa struktura do testów wydajności
        for i in range(10):
            self._create_file_pair(f"model_{i:03d}", ".zip", ".jpg", self.test_dir)

        # Podfoldery z plikami
        for folder_idx in range(3):
            subfolder = os.path.join(self.test_dir, f"subfolder_{folder_idx}")
            os.makedirs(subfolder, exist_ok=True)
            for file_idx in range(5):
                self._create_file_pair(
                    f"sub_model_{file_idx:02d}", ".zip", ".png", subfolder
                )

    def _create_file_pair(self, base_name, archive_ext, preview_ext, directory):
        """Tworzy parę plików dla testów."""
        os.makedirs(directory, exist_ok=True)

        archive_path = os.path.join(directory, f"{base_name}{archive_ext}")
        with open(archive_path, "w") as f:
            f.write(f"Archive content {base_name}")

        preview_path = os.path.join(directory, f"{base_name}{preview_ext}")
        with open(preview_path, "w") as f:
            f.write(f"Preview content {base_name}")

        return archive_path, preview_path

    def test_thread_safe_cache_basic_operations(self):
        """Test podstawowych operacji ThreadSafeCache."""
        cache = ThreadSafeCache()

        # Test pustego cache
        self.assertIsNone(cache.get_file_map(self.test_dir))
        self.assertIsNone(cache.get_scan_result(self.test_dir, "first_match"))

        # Test zapisywania file_map
        test_file_map = {"test_key": ["file1.zip", "file1.jpg"]}
        cache.store_file_map(self.test_dir, test_file_map)

        # Test odczytu file_map
        retrieved_map = cache.get_file_map(self.test_dir)
        self.assertEqual(retrieved_map, test_file_map)

        # Test zapisywania scan result
        test_result = ([], ["archive1.zip"], ["preview1.jpg"])
        cache.store_scan_result(self.test_dir, "first_match", test_result)

        # Test odczytu scan result
        retrieved_result = cache.get_scan_result(self.test_dir, "first_match")
        self.assertEqual(retrieved_result, test_result)

    def test_thread_safe_cache_statistics(self):
        """Test statystyk ThreadSafeCache."""
        cache = ThreadSafeCache()

        # Początkowo brak statystyk
        stats = cache.get_statistics()
        self.assertEqual(stats["cache_entries"], 0)
        self.assertEqual(stats["cache_hits"], 0)
        self.assertEqual(stats["cache_misses"], 0)

        # Po miss
        cache.get_file_map("nonexistent")
        stats = cache.get_statistics()
        self.assertEqual(stats["cache_misses"], 1)

        # Po hit
        test_map = {"key": ["value"]}
        cache.store_file_map(self.test_dir, test_map)
        cache.get_file_map(self.test_dir)

        stats = cache.get_statistics()
        self.assertEqual(stats["cache_hits"], 1)
        self.assertGreater(stats["hit_ratio"], 0)

    def test_thread_safe_cache_cleanup(self):
        """Test automatycznego czyszczenia ThreadSafeCache."""
        cache = ThreadSafeCache()

        # Zapisz wiele wpisów
        for i in range(150):  # Powyżej MAX_CACHE_ENTRIES
            cache.store_file_map(f"test_dir_{i}", {"test": ["file"]})

        stats = cache.get_statistics()
        # Cache powinien się automatycznie wyczyścić
        self.assertLessEqual(stats["cache_entries"], 100)  # MAX_CACHE_ENTRIES z config

    def test_collect_files_streaming(self):
        """Test nowej funkcji collect_files_streaming (bez estimation phase)."""
        # Test podstawowy
        files = collect_files_streaming(self.test_dir, max_depth=0)
        self.assertIsInstance(files, dict)
        self.assertGreater(len(files), 0)

        # Test z głębszym skanowaniem
        files_deep = collect_files_streaming(self.test_dir, max_depth=-1)
        self.assertGreaterEqual(len(files_deep), len(files))

        # Test z progress callback
        progress_calls = []

        def progress_callback(progress, message):
            progress_calls.append((progress, message))

        collect_files_streaming(self.test_dir, progress_callback=progress_callback)

        # Sprawdź czy progress był wywoływany
        self.assertGreater(len(progress_calls), 0)
        # Sprawdź czy ostatni progress to 100%
        last_progress = progress_calls[-1][0]
        self.assertEqual(last_progress, 100)

    def test_collect_files_streaming_vs_legacy(self):
        """Test porównania collect_files_streaming z legacy collect_files."""
        # Oba powinny zwracać identyczne wyniki
        result_streaming = collect_files_streaming(self.test_dir, max_depth=-1)
        result_legacy = collect_files(self.test_dir, max_depth=-1)

        # Porównanie kluczy (nazw bazowych plików)
        self.assertEqual(set(result_streaming.keys()), set(result_legacy.keys()))

        # Porównanie wartości (ścieżek plików)
        for key in result_streaming:
            self.assertEqual(set(result_streaming[key]), set(result_legacy[key]))

    def test_unified_cache_integration(self):
        """Test integracji nowego unified cache z istniejącymi funkcjami."""
        # Pierwsze skanowanie powinno zapełnić unified cache
        result1 = collect_files_streaming(self.test_dir)

        # Sprawdź czy unified cache ma wpis
        cached_result = _unified_cache.get_file_map(self.test_dir)
        self.assertIsNotNone(cached_result)
        self.assertEqual(result1, cached_result)

        # Drugie skanowanie powinno użyć cache
        with mock.patch("os.walk") as mock_walk:
            result2 = collect_files_streaming(self.test_dir)
            # os.walk nie powinno być wywołane (używa cache)
            mock_walk.assert_not_called()
            self.assertEqual(result1, result2)

    def test_optimized_best_match_algorithm(self):
        """Test zoptymalizowanego algorytmu best_match O(n+m)."""
        # Utwórz file_map z wieloma plikami do testów wydajności
        file_map = collect_files_streaming(self.test_dir, max_depth=-1)

        # Test wydajności algorytmu best_match
        start_time = time.time()
        pairs, processed = create_file_pairs(
            file_map, self.test_dir, pair_strategy="best_match"
        )
        execution_time = time.time() - start_time

        # Sprawdź poprawność wyników
        self.assertIsInstance(pairs, list)
        self.assertGreater(len(pairs), 0)

        # Sprawdź czy algorytm działa szybko (powinien być < 1s dla małych zbiorów)
        self.assertLess(execution_time, 1.0)

        # Test jakości dopasowań - każda para powinna mieć identyczne nazwy bazowe
        for pair in pairs:
            archive_base = os.path.splitext(os.path.basename(pair.archive_path))[0]
            preview_base = os.path.splitext(os.path.basename(pair.preview_path))[0]
            self.assertEqual(archive_base.lower(), preview_base.lower())

    def test_scan_statistics_dataclass(self):
        """Test dataclass ScanStatistics."""
        stats = ScanStatistics()

        # Test domyślnych wartości
        self.assertEqual(stats.total_folders_scanned, 0)
        self.assertEqual(stats.total_files_found, 0)
        self.assertEqual(stats.scan_duration, 0.0)
        self.assertEqual(stats.cache_hits, 0)
        self.assertEqual(stats.cache_misses, 0)

        # Test aktualizacji wartości
        stats.total_folders_scanned = 10
        stats.cache_hits = 5
        self.assertEqual(stats.total_folders_scanned, 10)
        self.assertEqual(stats.cache_hits, 5)

    def test_scan_cache_entry_validation(self):
        """Test walidacji ScanCacheEntry."""
        current_time = time.time()
        current_mtime = current_time - 100  # Czas modyfikacji 100s temu

        # Utwórz wpis cache
        entry = ScanCacheEntry(
            timestamp=current_time,
            directory_mtime=current_mtime,
            file_map={"test": ["file1.zip"]},
            scan_results={},
        )

        # Test walidacji - świeży wpis powinien być ważny
        self.assertTrue(entry.is_valid(current_mtime))

        # Test walidacji - jeśli folder się zmienił, wpis nieważny
        newer_mtime = current_time + 100
        self.assertFalse(entry.is_valid(newer_mtime))

    def test_backwards_compatibility(self):
        """Test kompatybilności wstecznej z legacy funkcjami."""
        # collect_files powinno teraz delegować do collect_files_streaming
        with mock.patch("src.logic.scanner.collect_files_streaming") as mock_streaming:
            mock_streaming.return_value = {"test": ["files"]}

            result = collect_files(self.test_dir)

            # Sprawdź czy została wywołana nowa funkcja
            mock_streaming.assert_called_once()
            self.assertEqual(result, {"test": ["files"]})

    def test_interrupt_functionality_streaming(self):
        """Test przerwania w collect_files_streaming."""
        interrupt_count = 0

        def interrupt_check():
            nonlocal interrupt_count
            interrupt_count += 1
            return interrupt_count > 2  # Przerwij po 2 wywołaniach

        # Powinno rzucić ScanningInterrupted
        with self.assertRaises(ScanningInterrupted):
            collect_files_streaming(self.test_dir, interrupt_check=interrupt_check)

    def test_concurrent_cache_access(self):
        """Test thread-safety cache (symulacja concurrent access)."""
        import threading

        results = []
        errors = []

        def cache_worker(worker_id):
            try:
                # Każdy worker próbuje zapisać i odczytać z cache
                test_data = {f"key_{worker_id}": [f"file_{worker_id}.zip"]}
                _unified_cache.store_file_map(f"test_dir_{worker_id}", test_data)

                retrieved = _unified_cache.get_file_map(f"test_dir_{worker_id}")
                results.append((worker_id, retrieved))
            except Exception as e:
                errors.append((worker_id, str(e)))

        # Uruchom wiele workerów jednocześnie
        threads = []
        for i in range(10):
            thread = threading.Thread(target=cache_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Poczekaj na zakończenie wszystkich wątków
        for thread in threads:
            thread.join()

        # Sprawdź wyniki
        self.assertEqual(len(errors), 0, f"Błędy w wątkach: {errors}")
        self.assertEqual(len(results), 10)

        # Sprawdź czy każdy worker dostał swoje dane
        for worker_id, data in results:
            expected_data = {f"key_{worker_id}": [f"file_{worker_id}.zip"]}
            self.assertEqual(data, expected_data)


if __name__ == "__main__":
    unittest.main()
