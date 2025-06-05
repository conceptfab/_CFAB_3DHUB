"""
Testy zaawansowane dla modułu scanner.py
"""

import os
import sys
import time
import unittest
import tempfile
import shutil
from threading import Thread, Event
from pathlib import Path

# Import testowanego modułu
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.logic.scanner import (
    collect_files,
    create_file_pairs,
    scan_folder_for_pairs,
    clear_cache,
    ScanningInterrupted,
    get_scan_statistics,
)


class TestScannerAdvanced(unittest.TestCase):
    """Testy zaawansowane dla modułu scanner."""

    def setUp(self):
        """Przygotowanie środowiska testowego."""
        # Tworzymy tymczasowy katalog
        self.test_dir = tempfile.mkdtemp()
        
        # Tworzymy strukturę katalogów
        self.subdir1 = os.path.join(self.test_dir, "subdir1")
        self.subdir2 = os.path.join(self.test_dir, "subdir2")
        self.subdir3 = os.path.join(self.test_dir, "subdir3")
        os.makedirs(self.subdir1)
        os.makedirs(self.subdir2)
        os.makedirs(self.subdir3)
        
        # Tworzymy pliki testowe
        self.create_test_files()
        
        # Czyścimy bufor przed każdym testem
        clear_cache()
    
    def tearDown(self):
        """Sprzątanie po testach."""
        # Usuwamy tymczasowy katalog
        shutil.rmtree(self.test_dir)

    def create_test_files(self):
        """Tworzy zaawansowane pliki testowe."""
        # Para 1 - normalna
        self.file1_archive = os.path.join(self.test_dir, "file1.step")
        self.file1_preview = os.path.join(self.test_dir, "file1.png")
        
        # Para 2 - różne wielkości liter
        self.file_case1 = os.path.join(self.test_dir, "CaseSensitive.step")
        self.file_case2 = os.path.join(self.test_dir, "casesensitive.jpg")
        
        # Para 3 - znaki Unicode
        self.file_unicode_archive = os.path.join(self.test_dir, "zażółć.stl")
        self.file_unicode_preview = os.path.join(self.test_dir, "zażółć.png")
        
        # Wiele plików z tą samą nazwą bazową
        self.multi_archive1 = os.path.join(self.subdir1, "multi.step")
        self.multi_archive2 = os.path.join(self.subdir1, "multi.stl")
        self.multi_preview1 = os.path.join(self.subdir1, "multi.jpg")
        self.multi_preview2 = os.path.join(self.subdir1, "multi.png")
        
        # Długie nazwy plików
        long_name = "very_long_name_" + "x" * 50
        self.long_name_archive = os.path.join(self.subdir2, f"{long_name}.step")
        self.long_name_preview = os.path.join(self.subdir2, f"{long_name}.png")
        
        # Pliki z nietypowymi znakami w nazwie
        self.special_chars_archive = os.path.join(self.subdir3, "file-with_(special)&chars.step")
        self.special_chars_preview = os.path.join(self.subdir3, "file-with_(special)&chars.jpg")
        
        # Tworzymy wszystkie pliki
        for file_path in [
            self.file1_archive, self.file1_preview,
            self.file_case1, self.file_case2,
            self.file_unicode_archive, self.file_unicode_preview,
            self.multi_archive1, self.multi_archive2, self.multi_preview1, self.multi_preview2,
            self.long_name_archive, self.long_name_preview,
            self.special_chars_archive, self.special_chars_preview
        ]:
            with open(file_path, "w") as f:
                f.write("test content")
    
    def test_case_insensitive_pairing(self):
        """Test parowania plików, których nazwy różnią się tylko wielkością liter."""
        # Zbieramy pliki
        file_map = collect_files(self.test_dir)
        
        # Tworzymy pary
        pairs, _ = create_file_pairs(file_map, self.test_dir)
        
        # Szukamy pary z nazwami różniącymi się wielkością liter
        case_pair = next((p for p in pairs if p.archive_path.lower() == self.file_case1.lower()), None)
        
        # Sprawdzamy czy para została utworzona
        self.assertIsNotNone(case_pair)
        self.assertEqual(case_pair.archive_path.lower(), self.file_case1.lower())
        self.assertEqual(case_pair.preview_path.lower(), self.file_case2.lower())
    
    def test_unicode_file_names(self):
        """Test obsługi plików z nazwami zawierającymi znaki Unicode."""
        # Zbieramy pliki
        file_map = collect_files(self.test_dir)
        
        # Tworzymy pary
        pairs, _ = create_file_pairs(file_map, self.test_dir)
        
        # Szukamy pary z nazwami Unicode
        unicode_pair = next((p for p in pairs if p.archive_path.lower() == self.file_unicode_archive.lower()), None)
        
        # Sprawdzamy czy para została utworzona
        self.assertIsNotNone(unicode_pair)
        self.assertEqual(unicode_pair.archive_path.lower(), self.file_unicode_archive.lower())
        self.assertEqual(unicode_pair.preview_path.lower(), self.file_unicode_preview.lower())
    
    def test_multiple_files_same_base_name(self):
        """Test parowania wielu plików z tą samą nazwą bazową."""
        # Skanujemy katalog z opcją pair_all=True (domyślnie)
        pairs, _, _ = scan_folder_for_pairs(self.subdir1)
        
        # Powinny być 4 pary (2 archiwa × 2 podglądy)
        self.assertEqual(len(pairs), 4)
        
        # Skanujemy katalog z opcją pair_all=False
        pairs_not_all, _, _ = scan_folder_for_pairs(self.subdir1, pair_all=False)
        
        # Powinna być tylko 1 para
        self.assertEqual(len(pairs_not_all), 1)
    
    def test_relative_paths_in_file_pair(self):
        """Test tworzenia FilePair z różnymi rodzajami ścieżek."""
        # Zbieramy pliki
        file_map = collect_files(self.test_dir)
        
        # Tworzymy pary z absolutną ścieżką bazową
        pairs_abs, _ = create_file_pairs(file_map, os.path.abspath(self.test_dir))
        
        # Tworzymy pary z względną ścieżką bazową
        # Najpierw zmieniamy katalog roboczy, aby względna ścieżka miała sens
        orig_dir = os.getcwd()
        parent_dir = os.path.dirname(self.test_dir)
        os.chdir(parent_dir)
        
        # Teraz używamy względnej ścieżki
        rel_path = os.path.basename(self.test_dir)
        pairs_rel, _ = create_file_pairs(file_map, rel_path)
        
        # Przywracamy oryginalny katalog roboczy
        os.chdir(orig_dir)
        
        # Sprawdzamy czy pary zostały utworzone
        self.assertEqual(len(pairs_abs), len(pairs_rel))
        
        # Sprawdzamy czy ścieżki bazowe są poprawnie ustawione
        if len(pairs_abs) > 0:
            pair_abs = next(iter(pairs_abs))
            pair_rel = next(iter(pairs_rel))
            
            # Względne ścieżki w FilePair powinny być różne
            self.assertNotEqual(pair_abs.relative_archive_path, pair_rel.relative_archive_path)
            
            # Ale absolutne ścieżki powinny być takie same
            self.assertEqual(pair_abs.archive_path, pair_rel.archive_path)
    
    def test_concurrent_scanning(self):
        """Test równoczesnego skanowania w wielu wątkach."""
        # Tworzymy kilka katalogów do skanowania
        test_dirs = []
        for i in range(3):
            new_dir = os.path.join(self.test_dir, f"concurrent_{i}")
            os.makedirs(new_dir)
            # Tworzymy parę plików w każdym katalogu
            with open(os.path.join(new_dir, "file.step"), "w") as f:
                f.write("test content")
            with open(os.path.join(new_dir, "file.png"), "w") as f:
                f.write("test content")
            test_dirs.append(new_dir)
            
        # Wyniki skanowania
        results = [None] * len(test_dirs)
        
        # Funkcja skanowania dla wątku
        def scan_thread(index):
            try:
                result = scan_folder_for_pairs(test_dirs[index])
                results[index] = result
            except Exception as e:
                results[index] = e
        
        # Uruchamiamy równoczesne skanowanie w wielu wątkach
        threads = []
        for i in range(len(test_dirs)):
            t = Thread(target=scan_thread, args=(i,))
            threads.append(t)
            t.start()
        
        # Czekamy na zakończenie wszystkich wątków
        for t in threads:
            t.join()
        
        # Sprawdzamy wyniki
        for i, result in enumerate(results):
            self.assertIsInstance(result, tuple)
            pairs, _, _ = result
            self.assertEqual(len(pairs), 1, f"Błąd w wątku {i}")
    
    def test_max_depth_scanning(self):
        """Test skanowania z różnymi ograniczeniami głębokości."""
        # Głębokość 0 (tylko główny katalog)
        pairs0, _, _ = scan_folder_for_pairs(self.test_dir, max_depth=0)
        
        # Powinny być 3 pary z głównego katalogu (file1, CaseSensitive, zażółć)
        self.assertEqual(len(pairs0), 3)
        
        # Głębokość 1 (główny katalog + bezpośrednie podkatalogi)
        pairs1, _, _ = scan_folder_for_pairs(self.test_dir, max_depth=1)
        
        # Powinno być więcej par niż tylko z głównego katalogu
        self.assertGreater(len(pairs1), len(pairs0))
        
        # Głębokość 2 (wszystkie katalogi w tym przypadku)
        pairs2, _, _ = scan_folder_for_pairs(self.test_dir, max_depth=2)
        
        # Powinno być tyle samo par co przy braku limitu głębokości
        pairs_all, _, _ = scan_folder_for_pairs(self.test_dir)
        self.assertEqual(len(pairs2), len(pairs_all))
    
    def test_interrupt_scanning(self):
        """Test mechanizmu przerwania skanowania."""
        # Tworzymy katalog z wieloma plikami dla dłuższego skanowania
        large_dir = os.path.join(self.test_dir, "large_dir")
        os.makedirs(large_dir)
        
        # Tworzymy 100 par plików
        for i in range(100):
            with open(os.path.join(large_dir, f"file{i}.step"), "w") as f:
                f.write("test content")
            with open(os.path.join(large_dir, f"file{i}.png"), "w") as f:
                f.write("test content")
        
        # Przerwanie po znalezieniu 10 plików
        files_count = [0]
        
        def interrupt_check():
            files_count[0] += 1
            if files_count[0] >= 10:
                return True
            return False
        
        # Powinno rzucić wyjątek ScanningInterrupted
        with self.assertRaises(ScanningInterrupted):
            collect_files(large_dir, interrupt_check=interrupt_check)
    
    def test_scan_statistics(self):
        """Test statystyk skanowania."""
        # Przed jakimkolwiek skanowaniem statystyki powinny być zerowe
        stats = get_scan_statistics()
        self.assertEqual(stats["scan_cache_entries"], 0)
        self.assertEqual(stats["files_cache_entries"], 0)
        
        # Po skanowaniu statystyki powinny się zmienić
        scan_folder_for_pairs(self.test_dir)
        stats = get_scan_statistics()
        self.assertGreater(stats["scan_cache_entries"], 0)
        self.assertGreater(stats["files_cache_entries"], 0)
        
        # Po wyczyszczeniu bufora statystyki powinny wrócić do zera
        clear_cache()
        stats = get_scan_statistics()
        self.assertEqual(stats["scan_cache_entries"], 0)
        self.assertEqual(stats["files_cache_entries"], 0)


if __name__ == "__main__":
    unittest.main()
