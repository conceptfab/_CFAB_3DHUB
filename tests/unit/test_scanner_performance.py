"""
Testy wydajnościowe dla modułu scanner.py
"""

import os
import sys
import time
import unittest
import tempfile
import shutil
import random
import string
from pathlib import Path

# Import testowanego modułu
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.logic.scanner import (
    collect_files,
    create_file_pairs,
    scan_folder_for_pairs,
    clear_cache,
)


class TestScannerPerformance(unittest.TestCase):
    """Testy wydajnościowe dla modułu scanner."""

    @classmethod
    def setUpClass(cls):
        """Przygotowanie środowiska testowego dla całej klasy."""
        print("\nTworzenie struktury testowej dla testów wydajnościowych...")
        cls.test_dir = tempfile.mkdtemp()
        
        # Liczba plików do wygenerowania
        cls.num_files = 700  # Całkowita liczba plików
        cls.pairs_ratio = 0.6  # 60% plików będzie miało pary
        
        # Oczekiwana liczba par
        cls.expected_pairs = int((cls.num_files / 2) * cls.pairs_ratio)
        
        # Struktura katalogów - 3 poziomy głębokości
        cls.level1_dirs = 5
        cls.level2_dirs = 3
        cls.level3_dirs = 2
        
        cls._create_test_structure()
        print(f"Utworzona struktura testowa w {cls.test_dir}:")
        print(f"  - {cls.num_files} plików")
        print(f"  - {cls.level1_dirs} katalogów na poziomie 1")
        print(f"  - {cls.level1_dirs * cls.level2_dirs} katalogów na poziomie 2")
        print(f"  - {cls.level1_dirs * cls.level2_dirs * cls.level3_dirs} katalogów na poziomie 3")
        print(f"  - Oczekiwana liczba par: {cls.expected_pairs}")
    
    @classmethod
    def tearDownClass(cls):
        """Sprzątanie po wszystkich testach."""
        shutil.rmtree(cls.test_dir)
    
    def setUp(self):
        """Przygotowanie przed każdym testem."""
        clear_cache()
    
    @classmethod
    def _create_test_structure(cls):
        """Tworzy złożoną strukturę katalogów i plików do testów wydajnościowych."""
        # Tworzenie katalogów
        dirs = [cls.test_dir]  # Poziom 0
        
        # Poziom 1
        level1_dirs = []
        for i in range(cls.level1_dirs):
            dir_path = os.path.join(cls.test_dir, f"dir_l1_{i}")
            os.makedirs(dir_path)
            level1_dirs.append(dir_path)
            dirs.append(dir_path)
        
        # Poziom 2
        level2_dirs = []
        for dir_path in level1_dirs:
            for i in range(cls.level2_dirs):
                subdir_path = os.path.join(dir_path, f"dir_l2_{i}")
                os.makedirs(subdir_path)
                level2_dirs.append(subdir_path)
                dirs.append(subdir_path)
        
        # Poziom 3
        level3_dirs = []
        for dir_path in level2_dirs:
            for i in range(cls.level3_dirs):
                subdir_path = os.path.join(dir_path, f"dir_l3_{i}")
                os.makedirs(subdir_path)
                level3_dirs.append(subdir_path)
                dirs.append(subdir_path)
        
        # Liczba wszystkich katalogów
        total_dirs = len(dirs)
        print(f"Utworzono {total_dirs} katalogów")
        
        # Tworzenie plików
        cls._create_file_pairs(dirs)
    
    @classmethod
    def _create_file_pairs(cls, dirs):
        """Tworzy pary plików w podanych katalogach."""
        # Liczba plików w każdym katalogu
        files_per_dir = cls.num_files // len(dirs)
        if files_per_dir == 0:
            files_per_dir = 1
        
        # Licznik utworzonych plików
        files_created = 0
        
        # Rozszerzenia plików
        archive_exts = ['.step', '.stl', '.obj']
        preview_exts = ['.png', '.jpg', '.jpeg', '.gif']
        
        # Tworzenie plików
        for dir_path in dirs:
            # Liczba plików do utworzenia w tym katalogu
            if files_created + files_per_dir > cls.num_files:
                files_per_dir = cls.num_files - files_created
                if files_per_dir <= 0:
                    break
            
            # Tworzenie plików w tym katalogu
            for i in range(files_per_dir):
                # Losowa nazwa bazowa
                base_name = ''.join(random.choice(string.ascii_lowercase) for _ in range(8))
                
                # Decydujemy czy utworzyć parę czy pojedynczy plik
                create_pair = random.random() < cls.pairs_ratio
                
                if create_pair:
                    # Tworzymy parę plików
                    archive_ext = random.choice(archive_exts)
                    preview_ext = random.choice(preview_exts)
                    
                    archive_path = os.path.join(dir_path, f"{base_name}{archive_ext}")
                    preview_path = os.path.join(dir_path, f"{base_name}{preview_ext}")
                    
                    with open(archive_path, 'w') as f:
                        f.write(f"Test archive content for {base_name}")
                    
                    with open(preview_path, 'w') as f:
                        f.write(f"Test preview content for {base_name}")
                    
                    files_created += 2
                    if files_created >= cls.num_files:
                        break
                else:
                    # Tworzymy pojedynczy plik
                    ext = random.choice(archive_exts + preview_exts)
                    file_path = os.path.join(dir_path, f"{base_name}{ext}")
                    
                    with open(file_path, 'w') as f:
                        f.write(f"Test content for {base_name}")
                    
                    files_created += 1
                    if files_created >= cls.num_files:
                        break
    
    def test_collect_files_performance(self):
        """Test wydajności zbierania plików."""
        # Mierzymy czas
        start_time = time.time()
        file_map = collect_files(self.test_dir)
        elapsed_time = time.time() - start_time
        
        # Wypisujemy wyniki
        print(f"\nWydajność collect_files:")
        print(f"  - Czas wykonania: {elapsed_time:.3f} sekundy")
        print(f"  - Liczba znalezionych unikalnych plików bazowych: {len(file_map)}")
        
        # Asercje wydajnościowe
        # Ustalamy rozsądny limit czasu - zależny od rozmiaru struktury
        time_limit = 2.0  # Sekundy
        self.assertLess(elapsed_time, time_limit)
        
        # Sprawdzamy czy znaleziono odpowiednią liczbę plików
        total_files = sum(len(files) for files in file_map.values())
        self.assertGreaterEqual(total_files, self.num_files * 0.95)  # Tolerancja 5%
    
    def test_create_file_pairs_performance(self):
        """Test wydajności tworzenia par plików."""
        # Najpierw zbieramy pliki
        file_map = collect_files(self.test_dir)
        
        # Mierzymy czas tworzenia par
        start_time = time.time()
        pairs, _ = create_file_pairs(file_map, self.test_dir)
        elapsed_time = time.time() - start_time
        
        # Wypisujemy wyniki
        print(f"\nWydajność create_file_pairs:")
        print(f"  - Czas wykonania: {elapsed_time:.3f} sekundy")
        print(f"  - Liczba utworzonych par: {len(pairs)}")
        
        # Asercje wydajnościowe
        time_limit = 1.0  # Sekundy
        self.assertLess(elapsed_time, time_limit)
        
        # Sprawdzamy czy utworzono odpowiednią liczbę par
        self.assertGreaterEqual(len(pairs), self.expected_pairs * 0.9)  # Tolerancja 10%
    
    def test_scan_folder_performance_first_run(self):
        """Test wydajności pierwszego skanowania (bez bufora)."""
        # Mierzymy czas pierwszego skanowania
        start_time = time.time()
        pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
            self.test_dir, use_cache=False
        )
        elapsed_time = time.time() - start_time
        
        # Wypisujemy wyniki
        print(f"\nWydajność scan_folder_for_pairs (pierwszy przebieg):")
        print(f"  - Czas wykonania: {elapsed_time:.3f} sekundy")
        print(f"  - Liczba znalezionych par: {len(pairs)}")
        print(f"  - Liczba niesparowanych archiwów: {len(unpaired_archives)}")
        print(f"  - Liczba niesparowanych podglądów: {len(unpaired_previews)}")
        
        # Asercje wydajnościowe
        time_limit = 3.0  # Sekundy
        self.assertLess(elapsed_time, time_limit)
        
        # Sprawdzamy poprawność wyników
        self.assertGreaterEqual(len(pairs), self.expected_pairs * 0.9)  # Tolerancja 10%
        
        # Całkowita liczba znalezionych plików powinna być zbliżona do liczby wygenerowanych plików
        total_files = len(pairs) * 2 + len(unpaired_archives) + len(unpaired_previews)
        self.assertGreaterEqual(total_files, self.num_files * 0.95)  # Tolerancja 5%
    
    def test_scan_folder_performance_cached(self):
        """Test wydajności skanowania z buforem."""
        # Pierwsze skanowanie (wypełnia bufor)
        scan_folder_for_pairs(self.test_dir)
        
        # Mierzymy czas drugiego skanowania (z buforem)
        start_time = time.time()
        pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(self.test_dir)
        elapsed_time = time.time() - start_time
        
        # Wypisujemy wyniki
        print(f"\nWydajność scan_folder_for_pairs (z buforem):")
        print(f"  - Czas wykonania: {elapsed_time:.3f} sekundy")
        print(f"  - Liczba znalezionych par: {len(pairs)}")
        
        # Asercje wydajnościowe - buforowane skanowanie powinno być bardzo szybkie
        time_limit = 0.01  # 10 ms
        self.assertLess(elapsed_time, time_limit)
    
    def test_scan_folder_performance_max_depth(self):
        """Test wydajności skanowania z różnymi wartościami max_depth."""
        times = []
        pairs_counts = []
        
        # Testujemy różne wartości max_depth
        for depth in range(4):  # 0, 1, 2, 3
            start_time = time.time()
            pairs, _, _ = scan_folder_for_pairs(
                self.test_dir, max_depth=depth, use_cache=False
            )
            elapsed_time = time.time() - start_time
            times.append(elapsed_time)
            pairs_counts.append(len(pairs))
        
        # Wypisujemy wyniki
        print(f"\nWydajność scan_folder_for_pairs dla różnych max_depth:")
        for depth, elapsed, count in zip(range(4), times, pairs_counts):
            print(f"  - Głębokość {depth}: {elapsed:.3f} sekundy, {count} par")
        
        # Asercje wydajnościowe
        # Im większa głębokość, tym więcej czasu powinno zająć skanowanie
        for i in range(1, len(times)):
            self.assertLessEqual(times[i-1], times[i] * 1.2)  # Dopuszczamy 20% tolerancji ze względu na buforowanie systemu plików
        
        # Im większa głębokość, tym więcej par powinno zostać znalezionych
        for i in range(1, len(pairs_counts)):
            self.assertLessEqual(pairs_counts[i-1], pairs_counts[i])


if __name__ == "__main__":
    unittest.main()
