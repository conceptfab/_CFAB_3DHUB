"""
Testy jednostkowe dla FolderStatisticsManager.
Pokrycie: cache LRU, obliczanie statystyk, worker management.
"""

import pytest
import tempfile
import os
import time
from unittest.mock import Mock, patch, MagicMock

from src.ui.folder_statistics_manager import (
    FolderStatisticsManager,
    FolderStatistics,
    LRUCache,
    FolderStatisticsWorker
)


class TestFolderStatistics:
    """Testy dla dataclass FolderStatistics."""
    
    def test_folder_statistics_creation(self):
        """Test tworzenia FolderStatistics z domyślnymi wartościami."""
        stats = FolderStatistics()
        assert stats.size_gb == 0.0
        assert stats.pairs_count == 0
        assert stats.total_files == 0
        assert stats.total_size_gb == 0.0
        assert stats.total_pairs == 0
    
    def test_folder_statistics_with_values(self):
        """Test tworzenia FolderStatistics z wartościami."""
        stats = FolderStatistics(
            size_gb=1.5,
            pairs_count=10,
            subfolders_size_gb=2.3,
            subfolders_pairs=15,
            total_files=100
        )
        assert stats.size_gb == 1.5
        assert stats.pairs_count == 10
        assert stats.total_files == 100
        assert stats.total_size_gb == 3.8  # 1.5 + 2.3
        assert stats.total_pairs == 25  # 10 + 15


class TestLRUCache:
    """Testy dla klasy LRUCache."""
    
    def test_lru_cache_creation(self):
        """Test tworzenia cache z domyślnymi parametrami."""
        cache = LRUCache()
        assert cache.max_size == 100
        assert cache.ttl_seconds == 300
        assert cache.size() == 0
    
    def test_lru_cache_custom_params(self):
        """Test tworzenia cache z custom parametrami."""
        cache = LRUCache(max_size=50, ttl_seconds=600)
        assert cache.max_size == 50
        assert cache.ttl_seconds == 600
    
    def test_lru_cache_put_get(self):
        """Test podstawowych operacji put/get."""
        cache = LRUCache(max_size=3, ttl_seconds=300)
        
        # Test put/get
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.size() == 1
        
        # Test get nieistniejącego klucza
        assert cache.get("nonexistent") is None
    
    def test_lru_cache_ttl_expiration(self):
        """Test wygaśnięcia TTL."""
        cache = LRUCache(max_size=10, ttl_seconds=1)  # 1 sekunda TTL
        
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Czekaj na wygaśnięcie TTL
        time.sleep(1.1)
        assert cache.get("key1") is None
        assert cache.size() == 0
    
    def test_lru_cache_max_size_eviction(self):
        """Test usuwania najstarszych elementów przy przekroczeniu max_size."""
        cache = LRUCache(max_size=3, ttl_seconds=300)
        
        # Dodaj elementy do limitu
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        assert cache.size() == 3
        
        # Dodaj kolejny element - key1 powinno zostać usunięte
        cache.put("key4", "value4")
        assert cache.size() == 3
        assert cache.get("key1") is None  # Najstarszy usunięty
        assert cache.get("key2") == "value2"
        assert cache.get("key4") == "value4"
    
    def test_lru_cache_invalidate(self):
        """Test invalidacji konkretnego klucza."""
        cache = LRUCache()
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        assert cache.size() == 2
        
        cache.invalidate("key1")
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.size() == 1
    
    def test_lru_cache_clear(self):
        """Test czyszczenia całego cache."""
        cache = LRUCache()
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        assert cache.size() == 2
        
        cache.clear()
        assert cache.size() == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestFolderStatisticsWorker:
    """Testy dla FolderStatisticsWorker."""
    
    def test_worker_creation(self):
        """Test tworzenia workera z prawidłową ścieżką."""
        with tempfile.TemporaryDirectory() as temp_dir:
            worker = FolderStatisticsWorker(temp_dir)
            # Normalizuj ścieżki do porównania (Windows vs Unix)
            import os
            assert os.path.normpath(worker.folder_path) == os.path.normpath(temp_dir)
            assert worker.custom_signals is not None
    
    def test_worker_validation_invalid_path(self):
        """Test walidacji z nieprawidłową ścieżką."""
        worker = FolderStatisticsWorker("/nonexistent/path")
        
        with pytest.raises(ValueError, match="nie istnieje"):
            worker._validate_inputs()
    
    @patch('src.ui.folder_statistics_manager.scan_folder_for_pairs')
    def test_worker_run_success(self, mock_scan):
        """Test pomyślnego uruchomienia workera."""
        # Setup
        mock_scan.return_value = ([Mock(), Mock()], [], [])  # 2 pary plików
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Utwórz test pliki
            test_file1 = os.path.join(temp_dir, "test1.txt")
            test_file2 = os.path.join(temp_dir, "test2.txt")
            with open(test_file1, 'w') as f:
                f.write("test content 1")
            with open(test_file2, 'w') as f:
                f.write("test content 2")
            
            worker = FolderStatisticsWorker(temp_dir)
            
            # Mock emit methods bezpośrednio
            worker.emit_finished = Mock()
            worker.emit_progress = Mock()
            worker.emit_error = Mock()
            
            # Uruchom worker
            worker.run()
            
            # Sprawdź wyniki
            worker.emit_finished.assert_called_once()
            worker.emit_error.assert_not_called()
            
            # Sprawdź argumenty wywołania
            call_args = worker.emit_finished.call_args[0][0]
            assert isinstance(call_args, FolderStatistics)
            assert call_args.total_files == 2
            assert call_args.pairs_count == 2
            assert call_args.size_gb > 0
    
    def test_worker_interruption(self):
        """Test przerwania workera."""
        with tempfile.TemporaryDirectory() as temp_dir:
            worker = FolderStatisticsWorker(temp_dir)
            
            # Przerwij workera przed uruchomieniem
            worker.interrupt()
            
            # Mock sygnałów
            finished_signal = Mock()
            interrupted_signal = Mock()
            
            worker.custom_signals.statistics_calculated.connect(finished_signal)
            worker.custom_signals.interrupted.connect(interrupted_signal)
            
            # Uruchom worker
            worker.run()
            
            # Worker powinien zakończyć się wcześnie
            finished_signal.emit.assert_not_called()


class TestFolderStatisticsManager:
    """Testy dla FolderStatisticsManager."""
    
    def test_manager_creation(self):
        """Test tworzenia managera."""
        with patch('src.ui.folder_statistics_manager.AppConfig') as mock_config:
            mock_config.return_value.get.side_effect = lambda key, default: default
            
            manager = FolderStatisticsManager()
            assert manager.cache is not None
            assert len(manager._active_workers) == 0
    
    def test_cache_operations(self):
        """Test operacji cache w managerze."""
        with patch('src.ui.folder_statistics_manager.AppConfig') as mock_config:
            mock_config.return_value.get.side_effect = lambda key, default: default
            
            manager = FolderStatisticsManager()
            
            # Test cache miss
            assert manager.get_cached_statistics("/test/path") is None
            
            # Test cache put/get
            stats = FolderStatistics(size_gb=1.0, pairs_count=5, total_files=10)
            manager.cache_statistics("/test/path", stats)
            
            cached = manager.get_cached_statistics("/test/path")
            assert cached == stats
    
    @patch('src.ui.folder_statistics_manager.QThreadPool')
    def test_calculate_statistics_async_cache_hit(self, mock_thread_pool):
        """Test asynchronicznego obliczania - cache hit."""
        with patch('src.ui.folder_statistics_manager.AppConfig') as mock_config:
            mock_config.return_value.get.side_effect = lambda key, default: default
            
            manager = FolderStatisticsManager()
            
            # Przygotuj cache
            stats = FolderStatistics(size_gb=1.0, pairs_count=5)
            manager.cache_statistics("/test/path", stats)
            
            # Test callback
            callback = Mock()
            manager.calculate_statistics_async("/test/path", callback)
            
            # Powinien wywołać callback z cache, nie tworzyć workera
            callback.assert_called_once_with(stats)
            mock_thread_pool.globalInstance().start.assert_not_called()
    
    @patch('src.ui.folder_statistics_manager.QThreadPool')
    @patch('src.ui.folder_statistics_manager.FolderStatisticsWorker')
    def test_calculate_statistics_async_cache_miss(self, mock_worker_class, mock_thread_pool):
        """Test asynchronicznego obliczania - cache miss."""
        with patch('src.ui.folder_statistics_manager.AppConfig') as mock_config:
            mock_config.return_value.get.side_effect = lambda key, default: default
            
            manager = FolderStatisticsManager()
            
            # Mock worker
            mock_worker = Mock()
            mock_worker.custom_signals = Mock()
            mock_worker_class.return_value = mock_worker
            
            # Test
            callback = Mock()
            manager.calculate_statistics_async("/test/path", callback)
            
            # Powinien utworzyć i uruchomić workera
            mock_worker_class.assert_called_once_with("/test/path")
            mock_thread_pool.globalInstance().start.assert_called_once_with(mock_worker)
            
            # Sprawdź czy worker jest w active_workers
            assert "/test/path" in manager._active_workers
    
    def test_duplicate_worker_prevention(self):
        """Test zapobiegania duplikacji workerów."""
        with patch('src.ui.folder_statistics_manager.AppConfig') as mock_config:
            mock_config.return_value.get.side_effect = lambda key, default: default
            
            manager = FolderStatisticsManager()
            
            # Dodaj aktywnego workera
            mock_worker = Mock()
            manager._active_workers["/test/path"] = mock_worker
            
            with patch('src.ui.folder_statistics_manager.QThreadPool') as mock_thread_pool:
                # Próbuj uruchomić kolejnego workera dla tej samej ścieżki
                manager.calculate_statistics_async("/test/path")
                
                # Nie powinien utworzyć nowego workera
                mock_thread_pool.globalInstance().start.assert_not_called()
    
    def test_invalidate_cache(self):
        """Test invalidacji cache."""
        with patch('src.ui.folder_statistics_manager.AppConfig') as mock_config:
            mock_config.return_value.get.side_effect = lambda key, default: default
            
            manager = FolderStatisticsManager()
            
            # Dodaj do cache
            stats = FolderStatistics(size_gb=1.0)
            manager.cache_statistics("/test/path", stats)
            assert manager.get_cached_statistics("/test/path") == stats
            
            # Invaliduj
            manager.invalidate_cache("/test/path")
            assert manager.get_cached_statistics("/test/path") is None
    
    def test_clear_cache(self):
        """Test czyszczenia całego cache."""
        with patch('src.ui.folder_statistics_manager.AppConfig') as mock_config:
            mock_config.return_value.get.side_effect = lambda key, default: default
            
            manager = FolderStatisticsManager()
            
            # Dodaj do cache
            manager.cache_statistics("/test/path1", FolderStatistics())
            manager.cache_statistics("/test/path2", FolderStatistics())
            
            # Wyczyść
            manager.clear_cache()
            assert manager.get_cached_statistics("/test/path1") is None
            assert manager.get_cached_statistics("/test/path2") is None
    
    def test_get_cache_info(self):
        """Test pobierania informacji o cache."""
        with patch('src.ui.folder_statistics_manager.AppConfig') as mock_config:
            mock_config.return_value.get.side_effect = lambda key, default: default
            
            manager = FolderStatisticsManager()
            
            info = manager.get_cache_info()
            assert 'size' in info
            assert 'max_size' in info
            assert 'ttl_seconds' in info
            assert 'active_workers' in info
            assert info['active_workers'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 