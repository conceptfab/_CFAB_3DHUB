"""
Testy jednostkowe dla modułu scan_cache.
"""

import pytest
import tempfile
import time
from unittest.mock import patch

from src.logic.scan_cache import (
    ThreadSafeCache, 
    ScanCacheEntry, 
    ScanStatistics,
    unified_cache,
    clear_cache,
    get_scan_statistics
)
from src.models.file_pair import FilePair


class TestScanStatistics:
    """Testy dla klasy ScanStatistics."""
    
    def test_scan_statistics_creation(self):
        """Test tworzenia instancji ScanStatistics."""
        stats = ScanStatistics()
        assert stats.total_folders_scanned == 0
        assert stats.total_files_found == 0
        assert stats.scan_duration == 0.0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
    
    def test_scan_statistics_with_values(self):
        """Test tworzenia ScanStatistics z wartościami."""
        stats = ScanStatistics(
            total_folders_scanned=10,
            total_files_found=100,
            scan_duration=5.0,
            cache_hits=50,
            cache_misses=5
        )
        assert stats.total_folders_scanned == 10
        assert stats.total_files_found == 100
        assert stats.scan_duration == 5.0
        assert stats.cache_hits == 50
        assert stats.cache_misses == 5


class TestScanCacheEntry:
    """Testy dla klasy ScanCacheEntry."""
    
    def test_cache_entry_creation(self):
        """Test tworzenia wpisu cache."""
        current_time = time.time()
        entry = ScanCacheEntry(
            timestamp=current_time,
            directory_mtime=current_time,
            file_map={"test": ["file1.jpg"]},
            scan_results={}
        )
        assert entry.timestamp == current_time
        assert entry.directory_mtime == current_time
        assert entry.file_map == {"test": ["file1.jpg"]}
        assert entry.scan_results == {}
    
    def test_cache_entry_is_valid_current(self):
        """Test walidacji aktualnego wpisu cache."""
        current_time = time.time()
        entry = ScanCacheEntry(
            timestamp=current_time,
            directory_mtime=current_time,
            file_map={},
            scan_results={}
        )
        # Wpis jest aktualny
        assert entry.is_valid(current_time) is True
    
    def test_cache_entry_is_valid_expired(self):
        """Test walidacji wygasłego wpisu cache."""
        old_time = time.time() - 10000  # 10000 sekund temu
        entry = ScanCacheEntry(
            timestamp=old_time,
            directory_mtime=old_time,
            file_map={},
            scan_results={}
        )
        # Wpis jest nieaktualny
        assert entry.is_valid(time.time()) is False
    
    def test_cache_entry_is_valid_modified_directory(self):
        """Test walidacji wpisu gdy katalog został zmodyfikowany."""
        old_time = time.time() - 100
        current_time = time.time()
        entry = ScanCacheEntry(
            timestamp=current_time,
            directory_mtime=old_time,
            file_map={},
            scan_results={}
        )
        # Katalog został zmodyfikowany po cache
        assert entry.is_valid(current_time) is False


class TestThreadSafeCache:
    """Testy dla klasy ThreadSafeCache."""
    
    def setup_method(self):
        """Setup przed każdym testem."""
        self.cache = ThreadSafeCache()
    
    def test_cache_creation(self):
        """Test tworzenia instancji cache."""
        assert len(self.cache._cache) == 0
        assert self.cache._stats.cache_hits == 0
        assert self.cache._stats.cache_misses == 0
    
    def test_store_and_get_file_map(self):
        """Test zapisywania i pobierania mapy plików."""
        test_dir = "/test/directory"
        test_map = {"test": ["file1.jpg", "file2.png"]}
        
        # Zapisujemy mapę plików
        with patch('src.logic.scan_cache.get_directory_modification_time', return_value=time.time()):
            self.cache.store_file_map(test_dir, test_map)
        
        # Pobieramy mapę plików
        with patch('src.logic.scan_cache.get_directory_modification_time', return_value=time.time()):
            result = self.cache.get_file_map(test_dir)
        
        assert result == test_map
        assert self.cache._stats.cache_hits == 1
    
    def test_get_file_map_miss(self):
        """Test cache miss dla mapy plików."""
        result = self.cache.get_file_map("/nonexistent/directory")
        assert result is None
        assert self.cache._stats.cache_misses == 1
    
    def test_store_and_get_scan_result(self):
        """Test zapisywania i pobierania wyników skanowania."""
        test_dir = "/test/directory"
        test_map = {"test": ["file1.jpg"]}
        test_result = ([], [], [])  # empty pairs, archives, previews
        
        # Najpierw zapisujemy mapę plików
        with patch('src.logic.scan_cache.get_directory_modification_time', return_value=time.time()):
            self.cache.store_file_map(test_dir, test_map)
            
            # Potem zapisujemy wynik skanowania
            self.cache.store_scan_result(test_dir, "first_match", test_result)
            
            # Pobieramy wynik skanowania
            result = self.cache.get_scan_result(test_dir, "first_match")
        
        assert result == test_result
    
    def test_clear_cache(self):
        """Test czyszczenia cache."""
        test_dir = "/test/directory"
        test_map = {"test": ["file1.jpg"]}
        
        with patch('src.logic.scan_cache.get_directory_modification_time', return_value=time.time()):
            self.cache.store_file_map(test_dir, test_map)
        
        assert len(self.cache._cache) == 1
        
        self.cache.clear()
        
        assert len(self.cache._cache) == 0
        assert self.cache._stats.cache_hits == 0
        assert self.cache._stats.cache_misses == 0
    
    def test_remove_entry(self):
        """Test usuwania konkretnego wpisu z cache."""
        test_dir = "/test/directory"
        test_map = {"test": ["file1.jpg"]}
        
        with patch('src.logic.scan_cache.get_directory_modification_time', return_value=time.time()):
            self.cache.store_file_map(test_dir, test_map)
        
        assert len(self.cache._cache) == 1
        
        self.cache.remove_entry(test_dir)
        
        assert len(self.cache._cache) == 0
    
    def test_get_statistics(self):
        """Test pobierania statystyk cache."""
        # Początkowo brak statystyk
        stats = self.cache.get_statistics()
        assert stats["cache_entries"] == 0
        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["hit_ratio"] == 0.0
        
        # Dodajemy wpis i testujemy hit
        test_dir = "/test/directory"
        test_map = {"test": ["file1.jpg"]}
        
        with patch('src.logic.scan_cache.get_directory_modification_time', return_value=time.time()):
            self.cache.store_file_map(test_dir, test_map)
            self.cache.get_file_map(test_dir)  # cache hit
        
        stats = self.cache.get_statistics()
        assert stats["cache_entries"] == 1
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 0
        assert stats["hit_ratio"] == 100.0
        
        # Testujemy miss
        self.cache.get_file_map("/nonexistent")  # cache miss
        
        stats = self.cache.get_statistics()
        assert stats["cache_hits"] == 1
        assert stats["cache_misses"] == 1
        assert stats["hit_ratio"] == 50.0


class TestModuleFunctions:
    """Testy dla funkcji modułu."""
    
    def test_clear_cache_function(self):
        """Test funkcji clear_cache."""
        # Dodajemy coś do globalnego cache
        test_dir = "/test/directory"
        test_map = {"test": ["file1.jpg"]}
        
        with patch('src.logic.scan_cache.get_directory_modification_time', return_value=time.time()):
            unified_cache.store_file_map(test_dir, test_map)
        
        assert len(unified_cache._cache) == 1
        
        clear_cache()
        
        assert len(unified_cache._cache) == 0
    
    def test_get_scan_statistics_function(self):
        """Test funkcji get_scan_statistics."""
        # Początkowo pusty cache
        stats = get_scan_statistics()
        assert stats["cache_entries"] == 0
        
        # Dodajemy wpis
        test_dir = "/test/directory"
        test_map = {"test": ["file1.jpg"]}
        
        with patch('src.logic.scan_cache.get_directory_modification_time', return_value=time.time()):
            unified_cache.store_file_map(test_dir, test_map)
        
        stats = get_scan_statistics()
        assert stats["cache_entries"] == 1
        
        # Cleanup
        clear_cache()
