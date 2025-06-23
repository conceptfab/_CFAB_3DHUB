"""
Testy dla TileCacheOptimizer - ETAP 8
"""

import threading
import time

import pytest
from PyQt6.QtGui import QPixmap

from src.ui.widgets.tile_cache_optimizer import (
    AdaptiveEvictionPolicy,
    CacheEntry,
    CacheStrategy,
    LFUEvictionPolicy,
    LRUEvictionPolicy,
    TileCacheOptimizer,
    cleanup_cache_optimizer,
    get_cache_optimizer,
)


class TestTileCacheOptimizer:
    """Testy dla TileCacheOptimizer."""

    def setup_method(self):
        """Setup przed każdym testem."""
        self.optimizer = TileCacheOptimizer(max_size_mb=10.0, max_entries=100)

    def teardown_method(self):
        """Cleanup po każdym teście."""
        if hasattr(self, "optimizer"):
            self.optimizer.cleanup()

    def test_initialization(self):
        """Test inicjalizacji."""
        assert self.optimizer.max_size_bytes == 10 * 1024 * 1024
        assert self.optimizer.max_entries == 100
        assert self.optimizer.strategy == CacheStrategy.ADAPTIVE
        assert "thumbnails" in self.optimizer._caches
        assert "metadata" in self.optimizer._caches

    def test_basic_put_get(self):
        """Test podstawowych operacji put/get."""
        # Put value
        success = self.optimizer.put("test_cache", "key1", "value1", size_bytes=100)
        assert success is True

        # Get value
        value = self.optimizer.get("test_cache", "key1")
        assert value == "value1"

        # Get non-existent key
        value = self.optimizer.get("test_cache", "nonexistent")
        assert value is None

    def test_qpixmap_handling(self):
        """Test obsługi QPixmap z proper cleanup."""
        # Create mock QPixmap
        pixmap = QPixmap(100, 100)

        # Put QPixmap
        success = self.optimizer.put("pixmaps", "pix1", pixmap, size_bytes=40000)
        assert success is True

        # Get QPixmap
        retrieved_pixmap = self.optimizer.get("pixmaps", "pix1")
        assert retrieved_pixmap is not None

        # Test cleanup
        self.optimizer.remove("pixmaps", "pix1")
        value = self.optimizer.get("pixmaps", "pix1")
        assert value is None

    def test_thread_safety(self):
        """Test thread safety."""
        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(10):
                    key = f"key_{worker_id}_{i}"
                    value = f"value_{worker_id}_{i}"

                    # Put value
                    success = self.optimizer.put(
                        "thread_test", key, value, size_bytes=100
                    )
                    assert success is True

                    # Get value
                    retrieved = self.optimizer.get("thread_test", key)
                    assert retrieved == value

                    results.append(f"worker_{worker_id}_iter_{i}")
            except Exception as e:
                errors.append(str(e))

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 50  # 5 workers * 10 iterations

    def test_eviction_policies(self):
        """Test różnych polityk eviction."""
        # Test LRU
        lru_policy = LRUEvictionPolicy()
        entries = {
            "key1": CacheEntry(
                "key1", "value1", 100, last_access_time=time.time() - 10
            ),
            "key2": CacheEntry("key2", "value2", 100, last_access_time=time.time() - 5),
            "key3": CacheEntry("key3", "value3", 100, last_access_time=time.time()),
        }

        keys_to_evict = lru_policy.select_for_eviction(entries, 2)
        assert len(keys_to_evict) == 2
        assert "key1" in keys_to_evict  # Oldest should be first

        # Test LFU
        lfu_policy = LFUEvictionPolicy()
        entries = {
            "key1": CacheEntry("key1", "value1", 100, access_count=5),
            "key2": CacheEntry("key2", "value2", 100, access_count=1),
            "key3": CacheEntry("key3", "value3", 100, access_count=3),
        }

        keys_to_evict = lfu_policy.select_for_eviction(entries, 2)
        assert len(keys_to_evict) == 2
        assert "key2" in keys_to_evict  # Least frequently used

    def test_ttl_expiration(self):
        """Test TTL expiration."""
        # Put value with short TTL
        self.optimizer.put(
            "ttl_test", "key1", "value1", size_bytes=100, ttl_seconds=0.1
        )

        # Value should be available immediately
        value = self.optimizer.get("ttl_test", "key1")
        assert value == "value1"

        # Wait for expiration
        time.sleep(0.2)

        # Value should be expired
        value = self.optimizer.get("ttl_test", "key1")
        assert value is None

    def test_memory_pressure_detection(self):
        """Test wykrywania memory pressure."""
        # Fill cache to trigger memory pressure
        for i in range(50):
            self.optimizer.put(
                "pressure_test", f"key_{i}", f"value_{i}", size_bytes=200000
            )  # 200KB each

        # Check if memory pressure was detected
        stats = self.optimizer.get_cache_stats("pressure_test")
        assert stats.entry_count > 0

        # Force cleanup
        self.optimizer._periodic_cleanup()

    def test_cache_stats(self):
        """Test statystyk cache."""
        # Put and get values
        self.optimizer.put("stats_test", "key1", "value1", size_bytes=100)
        self.optimizer.get("stats_test", "key1")  # Hit
        self.optimizer.get("stats_test", "key2")  # Miss

        stats = self.optimizer.get_cache_stats("stats_test")
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.entry_count == 1
        assert stats.total_size_bytes == 100
        assert stats.get_hit_rate() == 50.0

    def test_performance_summary(self):
        """Test performance summary."""
        # Add some data
        self.optimizer.put("perf_test", "key1", "value1", size_bytes=100)
        self.optimizer.get("perf_test", "key1")

        summary = self.optimizer.get_performance_summary()
        assert "overall_hit_rate" in summary
        assert "total_size_mb" in summary
        assert "strategy" in summary
        assert "cache_breakdown" in summary

    def test_singleton_pattern(self):
        """Test singleton pattern."""
        # Cleanup any existing instance
        cleanup_cache_optimizer()

        # Get instances
        instance1 = get_cache_optimizer(max_size_mb=100.0)
        instance2 = get_cache_optimizer(max_size_mb=200.0)  # Same instance

        assert instance1 is instance2
        # First call parameters
        assert instance1.max_size_bytes == 100 * 1024 * 1024

        # Cleanup
        cleanup_cache_optimizer()

    def test_adaptive_strategy(self):
        """Test adaptive strategy."""
        adaptive_policy = AdaptiveEvictionPolicy()

        # Test with different patterns
        entries = {
            "key1": CacheEntry(
                "key1", "value1", 100, access_count=1, creation_time=time.time() - 400
            ),
            "key2": CacheEntry(
                "key2", "value2", 100, access_count=10, creation_time=time.time()
            ),
            "key3": CacheEntry(
                "key3", "value3", 100, access_count=1, creation_time=time.time()
            ),
        }

        keys_to_evict = adaptive_policy.select_for_eviction(entries, 1)
        assert len(keys_to_evict) == 1

    def test_cleanup_functionality(self):
        """Test funkcjonalności cleanup."""
        # Add some data
        self.optimizer.put("cleanup_test", "key1", "value1", size_bytes=100)
        self.optimizer.put("cleanup_test", "key2", "value2", size_bytes=100)

        # Check data exists
        assert self.optimizer.get("cleanup_test", "key1") == "value1"
        assert self.optimizer.get("cleanup_test", "key2") == "value2"

        # Clear specific cache
        self.optimizer.clear("cleanup_test")

        # Check data is gone
        assert self.optimizer.get("cleanup_test", "key1") is None
        assert self.optimizer.get("cleanup_test", "key2") is None

    def test_size_estimation(self):
        """Test szacowania rozmiaru."""
        # Test QPixmap
        pixmap = QPixmap(50, 50)
        size = self.optimizer._estimate_size(pixmap)
        assert size > 0

        # Test string
        size = self.optimizer._estimate_size("test string")
        assert size == len("test string")

        # Test dict
        test_dict = {"key1": "value1", "key2": "value2"}
        size = self.optimizer._estimate_size(test_dict)
        assert size > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
