"""
ETAP 8: PERFORMANCE OPTIMIZATION - Test Suite
Testy dla performance monitoring, cache optimization i async UI management.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPixmap

# Test imports
from src.ui.widgets.tile_performance_monitor import (
    TilePerformanceMonitor, PerformanceMetric, PerformanceSample, 
    PerformanceStats, FrameTimingStats, BatchOperationOptimizer,
    QtRenderingOptimizer, get_performance_monitor
)
from src.ui.widgets.tile_cache_optimizer import (
    TileCacheOptimizer, CacheStrategy, CacheEntry, CacheStats,
    LRUEvictionPolicy, LFUEvictionPolicy, TTLEvictionPolicy, 
    AdaptiveEvictionPolicy, get_cache_optimizer
)
from src.ui.widgets.tile_async_ui_manager import (
    TileAsyncUIManager, UIUpdatePriority, UIUpdateTask, UIUpdateScheduler,
    DebounceManager, BatchUIUpdater, get_async_ui_manager
)
from src.ui.widgets.tile_resource_manager import (
    TileResourceManager, get_resource_manager
)


class TestPerformanceMonitor:
    """Testy dla TilePerformanceMonitor."""
    
    def test_performance_monitor_initialization(self):
        """Test inicjalizacji performance monitor."""
        monitor = TilePerformanceMonitor(enable_monitoring=True, history_size=500)
        
        assert monitor.enable_monitoring == True
        assert monitor.history_size == 500
        assert monitor._batch_optimizer is not None
        assert monitor._qt_optimizer is not None
        assert len(monitor._metrics_history) == 0
        
        monitor.cleanup()
    
    def test_metric_recording(self):
        """Test rejestrowania metryk."""
        monitor = TilePerformanceMonitor(enable_monitoring=True)
        
        # Record metrics
        monitor.record_metric(PerformanceMetric.RENDER_TIME, 12.5, {"test": "data"})
        monitor.record_metric(PerformanceMetric.MEMORY_USAGE, 1024*1024*5)  # 5MB
        
        # Check metrics były recorded
        assert len(monitor._metrics_history[PerformanceMetric.RENDER_TIME]) == 1
        assert len(monitor._metrics_history[PerformanceMetric.MEMORY_USAGE]) == 1
        
        sample = monitor._metrics_history[PerformanceMetric.RENDER_TIME][0]
        assert sample.value == 12.5
        assert sample.context["test"] == "data"
        
        monitor.cleanup()
    
    def test_measure_operation_context_manager(self):
        """Test context manager dla pomiaru operacji."""
        monitor = TilePerformanceMonitor(enable_monitoring=True)
        
        with monitor.measure_operation(PerformanceMetric.THUMBNAIL_LOAD_TIME):
            time.sleep(0.01)  # Simulate work
        
        # Check metric był recorded
        assert len(monitor._metrics_history[PerformanceMetric.THUMBNAIL_LOAD_TIME]) == 1
        sample = monitor._metrics_history[PerformanceMetric.THUMBNAIL_LOAD_TIME][0]
        assert sample.value > 5  # Should be >5ms
        
        monitor.cleanup()
    
    def test_frame_timing(self):
        """Test frame timing measurement."""
        monitor = TilePerformanceMonitor(enable_monitoring=True)
        
        monitor.start_frame_timing()
        time.sleep(0.02)  # 20ms frame time
        monitor.end_frame_timing()
        
        frame_stats = monitor.get_frame_timing_stats()
        assert frame_stats.frame_count == 1
        assert frame_stats.avg_frame_time_ms > 15  # Should be ~20ms
        assert frame_stats.get_fps() < 60  # Should be lower due to slow frame
        
        monitor.cleanup()
    
    def test_performance_thresholds(self):
        """Test performance alerts przy przekroczeniu thresholds."""
        monitor = TilePerformanceMonitor(enable_monitoring=True)
        
        # Mock signal
        alerts = []
        monitor.performance_alert.connect(lambda metric, value: alerts.append((metric, value)))
        
        # Record high render time (above 16ms threshold)
        monitor.record_metric(PerformanceMetric.RENDER_TIME, 25.0)
        
        # Check alert was emitted
        assert len(alerts) == 1
        assert "RENDER_TIME" in alerts[0][0]
        assert alerts[0][1] == 25.0
        
        monitor.cleanup()
    
    def test_batch_operation_optimizer(self):
        """Test batch operation optimizer."""
        optimizer = BatchOperationOptimizer(max_batch_size=3, batch_timeout_ms=50)
        
        operations_executed = []
        
        def test_operation(value):
            operations_executed.append(value)
        
        # Add operations
        optimizer.add_operation(lambda: test_operation(1))
        optimizer.add_operation(lambda: test_operation(2))
        optimizer.add_operation(lambda: test_operation(3))  # Should trigger batch
        
        # Wait for processing
        time.sleep(0.1)
        
        # Check all operations were executed
        assert len(operations_executed) == 3
        assert set(operations_executed) == {1, 2, 3}
    
    def test_qt_rendering_optimizer(self):
        """Test Qt rendering optimizations."""
        optimizer = QtRenderingOptimizer()
        
        # Test pixmap optimization
        pixmap = QPixmap(100, 100)
        optimized = optimizer.optimize_pixmap_for_display(pixmap, (50, 50))
        
        assert optimized.width() == 50
        assert optimized.height() == 50
    
    def test_performance_stats_calculation(self):
        """Test obliczania performance statistics."""
        monitor = TilePerformanceMonitor(enable_monitoring=True)
        
        # Record multiple metrics
        values = [10.0, 15.0, 20.0, 25.0, 30.0]
        for value in values:
            monitor.record_metric(PerformanceMetric.RENDER_TIME, value)
        
        # Force stats update
        monitor._update_stats()
        
        stats = monitor.get_performance_stats(PerformanceMetric.RENDER_TIME)
        render_stats = stats[PerformanceMetric.RENDER_TIME]
        
        assert render_stats.sample_count == 5
        assert render_stats.min_value == 10.0
        assert render_stats.max_value == 30.0
        assert render_stats.avg_value == 20.0  # (10+15+20+25+30)/5
        assert render_stats.median_value == 20.0
        
        monitor.cleanup()
    
    def test_performance_summary(self):
        """Test performance summary generation."""
        monitor = TilePerformanceMonitor(enable_monitoring=True)
        
        # Add some metrics
        monitor.record_metric(PerformanceMetric.RENDER_TIME, 12.0)
        monitor.record_metric(PerformanceMetric.MEMORY_USAGE, 1024*1024)
        monitor._update_stats()
        
        summary = monitor.get_performance_summary()
        
        assert 'frame_stats' in summary
        assert 'metrics' in summary
        assert 'thresholds_exceeded' in summary
        assert summary['monitoring_enabled'] == True
        
        monitor.cleanup()


class TestCacheOptimizer:
    """Testy dla TileCacheOptimizer."""
    
    def test_cache_optimizer_initialization(self):
        """Test inicjalizacji cache optimizer."""
        optimizer = TileCacheOptimizer(
            max_size_mb=50.0,
            max_entries=500,
            strategy=CacheStrategy.LRU
        )
        
        assert optimizer.max_size_bytes == 50 * 1024 * 1024
        assert optimizer.max_entries == 500
        assert optimizer.strategy == CacheStrategy.LRU
        assert len(optimizer._caches) == 5  # thumbnails, metadata, pixmaps, layout, style
        
        optimizer.cleanup()
    
    def test_cache_put_get_operations(self):
        """Test podstawowych operacji cache."""
        optimizer = TileCacheOptimizer(max_size_mb=10.0, max_entries=100)
        
        # Put values
        success = optimizer.put('thumbnails', 'test_key', 'test_value', size_bytes=1024)
        assert success == True
        
        # Get values
        value = optimizer.get('thumbnails', 'test_key')
        assert value == 'test_value'
        
        # Get non-existent
        value = optimizer.get('thumbnails', 'non_existent')
        assert value is None
        
        optimizer.cleanup()
    
    def test_cache_entry_expiration(self):
        """Test wygasania entries z TTL."""
        optimizer = TileCacheOptimizer()
        
        # Put entry z short TTL
        optimizer.put('metadata', 'expire_key', 'expire_value', ttl_seconds=0.05)  # 50ms
        
        # Should be available immediately
        value = optimizer.get('metadata', 'expire_key')
        assert value == 'expire_value'
        
        # Wait for expiration
        time.sleep(0.1)
        
        # Should be expired
        value = optimizer.get('metadata', 'expire_key')
        assert value is None
        
        optimizer.cleanup()
    
    def test_lru_eviction_policy(self):
        """Test LRU eviction policy."""
        policy = LRUEvictionPolicy()
        
        # Create entries z different access times
        entries = {
            'key1': CacheEntry('key1', 'value1', 100, last_access_time=time.time() - 100),
            'key2': CacheEntry('key2', 'value2', 100, last_access_time=time.time() - 50),
            'key3': CacheEntry('key3', 'value3', 100, last_access_time=time.time() - 10),
        }
        
        keys_to_evict = policy.select_for_eviction(entries, 2)
        
        # Should evict oldest accessed first
        assert 'key1' in keys_to_evict  # Oldest
        assert 'key2' in keys_to_evict  # Second oldest
        assert len(keys_to_evict) == 2
    
    def test_lfu_eviction_policy(self):
        """Test LFU eviction policy."""
        policy = LFUEvictionPolicy()
        
        # Create entries z different access counts
        entries = {
            'key1': CacheEntry('key1', 'value1', 100, access_count=1),
            'key2': CacheEntry('key2', 'value2', 100, access_count=5),
            'key3': CacheEntry('key3', 'value3', 100, access_count=10),
        }
        
        keys_to_evict = policy.select_for_eviction(entries, 1)
        
        # Should evict least frequently used
        assert keys_to_evict == ['key1']
    
    def test_cache_size_limits(self):
        """Test enforcement cache size limits."""
        optimizer = TileCacheOptimizer(max_size_mb=0.001, max_entries=2)  # Very small limits
        
        # Add entries até limit
        optimizer.put('thumbnails', 'key1', 'A' * 500, size_bytes=500)
        optimizer.put('thumbnails', 'key2', 'B' * 500, size_bytes=500)
        
        # Adding third should trigger eviction
        optimizer.put('thumbnails', 'key3', 'C' * 500, size_bytes=500)
        
        # One of the original entries should be evicted
        value1 = optimizer.get('thumbnails', 'key1')
        value2 = optimizer.get('thumbnails', 'key2')
        value3 = optimizer.get('thumbnails', 'key3')
        
        # At least one should be None due do eviction
        available_count = sum(1 for v in [value1, value2, value3] if v is not None)
        assert available_count <= 2
        
        optimizer.cleanup()
    
    def test_cache_warming(self):
        """Test cache warming functionality."""
        optimizer = TileCacheOptimizer(enable_cache_warming=True)
        
        warming_executed = []
        
        def mock_load_func():
            warming_executed.append("loaded")
            return True
        
        # Add to warming queue
        optimizer.add_to_warming_queue(mock_load_func, priority=1)
        
        # Wait for processing
        time.sleep(0.1)
        
        # Should be executed
        assert len(warming_executed) == 1
        
        optimizer.cleanup()
    
    def test_cache_stats(self):
        """Test cache statistics."""
        optimizer = TileCacheOptimizer()
        
        # Perform some operations
        optimizer.put('thumbnails', 'key1', 'value1')
        optimizer.get('thumbnails', 'key1')  # Hit
        optimizer.get('thumbnails', 'non_existent')  # Miss
        
        stats = optimizer.get_cache_stats('thumbnails')
        
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.get_hit_rate() == 50.0  # 1 hit out of 2 operations
        
        optimizer.cleanup()
    
    def test_performance_summary(self):
        """Test performance summary generation."""
        optimizer = TileCacheOptimizer()
        
        # Add some data
        optimizer.put('thumbnails', 'key1', 'value1')
        optimizer.get('thumbnails', 'key1')
        
        summary = optimizer.get_performance_summary()
        
        assert 'overall_hit_rate' in summary
        assert 'total_size_mb' in summary
        assert 'cache_breakdown' in summary
        assert 'strategy' in summary
        assert summary['strategy'] == 'ADAPTIVE'
        
        optimizer.cleanup()


class TestAsyncUIManager:
    """Testy dla TileAsyncUIManager."""
    
    def test_async_ui_manager_initialization(self):
        """Test inicjalizacji async UI manager."""
        manager = TileAsyncUIManager(max_concurrent_tasks=3, enable_batching=True)
        
        assert manager.max_concurrent_tasks == 3
        assert manager.enable_batching == True
        assert manager._scheduler is not None
        assert manager._debounce_manager is not None
        assert manager._batch_updater is not None
        
        manager.cleanup()
    
    def test_task_scheduling(self):
        """Test planowania zadań."""
        manager = TileAsyncUIManager(max_concurrent_tasks=2)
        
        results = []
        
        def test_task(value):
            results.append(value)
            return value * 2
        
        # Schedule tasks
        manager.schedule_async_update(
            test_task, 1,
            priority=UIUpdatePriority.HIGH,
            callback=lambda result: results.append(f"callback_{result}")
        )
        
        # Wait for execution
        time.sleep(0.1)
        
        # Check task was executed
        assert 1 in results
        assert "callback_2" in results
        
        manager.cleanup()
    
    def test_debounce_functionality(self):
        """Test debouncing operacji."""
        manager = TileAsyncUIManager()
        
        executed_count = [0]  # Use list dla mutable reference
        
        def debounced_func():
            executed_count[0] += 1
        
        # Call multiple times rapidly
        for i in range(5):
            manager.debounce_operation('test_op', debounced_func, delay_ms=50)
            time.sleep(0.01)  # Small delay between calls
        
        # Wait for debounce
        time.sleep(0.1)
        
        # Should only execute once
        assert executed_count[0] == 1
        
        manager.cleanup()
    
    def test_batch_ui_updates(self):
        """Test batch UI updates."""
        manager = TileAsyncUIManager(enable_batching=True)
        
        updates_executed = []
        
        def update_func(value):
            updates_executed.append(value)
        
        # Add multiple updates
        for i in range(5):
            manager.add_to_batch(lambda v=i: update_func(v))
        
        # Flush batch
        manager.flush_batch_updates()
        
        # Wait for execution
        time.sleep(0.1)
        
        # All updates should be executed
        assert len(updates_executed) == 5
        assert set(updates_executed) == {0, 1, 2, 3, 4}
        
        manager.cleanup()
    
    def test_priority_scheduling(self):
        """Test priority-based scheduling."""
        manager = TileAsyncUIManager(max_concurrent_tasks=1)  # Single task dla testowania priority
        
        executed_order = []
        
        def task_func(priority_name):
            executed_order.append(priority_name)
            time.sleep(0.01)  # Small delay
        
        # Schedule tasks z different priorities (reverse order)
        manager.schedule_async_update(task_func, "low", priority=UIUpdatePriority.LOW)
        manager.schedule_async_update(task_func, "critical", priority=UIUpdatePriority.CRITICAL)
        manager.schedule_async_update(task_func, "high", priority=UIUpdatePriority.HIGH)
        
        # Wait for execution
        time.sleep(0.2)
        
        # Higher priority tasks should execute first
        assert executed_order[0] == "critical"  # Highest priority first
        
        manager.cleanup()
    
    def test_ui_update_task_creation(self):
        """Test tworzenia UI update tasks."""
        def test_func(a, b, c=None):
            return a + b + (c or 0)
        
        task = UIUpdateTask(
            func=test_func,
            args=(1, 2),
            kwargs={'c': 3},
            priority=UIUpdatePriority.NORMAL,
            created_time=time.time()
        )
        
        result = task.execute()
        assert result == 6  # 1 + 2 + 3
    
    def test_debounce_manager(self):
        """Test debounce manager."""
        debounce_manager = DebounceManager()
        
        executed = []
        
        def test_func(value):
            executed.append(value)
        
        # Multiple rapid calls
        debounce_manager.debounce('test_key', test_func, 50, ('first',))
        debounce_manager.debounce('test_key', test_func, 50, ('second',))
        debounce_manager.debounce('test_key', test_func, 50, ('third',))
        
        # Wait for execution
        time.sleep(0.1)
        
        # Only last call should execute
        assert len(executed) == 1
        assert executed[0] == 'third'
        
        debounce_manager.cleanup()
    
    def test_performance_stats(self):
        """Test performance statistics."""
        manager = TileAsyncUIManager()
        
        # Execute some tasks
        manager.schedule_async_update(lambda: time.sleep(0.01), priority=UIUpdatePriority.HIGH)
        time.sleep(0.1)
        
        stats = manager.get_performance_stats()
        
        assert 'scheduler' in stats
        assert 'current_fps' in stats
        assert 'max_concurrent_tasks' in stats
        assert stats['batching_enabled'] == True
        
        manager.cleanup()


class TestPerformanceIntegration:
    """Testy integracji performance optimization z resource manager."""
    
    def test_resource_manager_performance_integration(self):
        """Test integracji resource manager z performance components."""
        # Create resource manager z performance enabled
        resource_manager = TileResourceManager()
        
        # Performance components should be initialized
        assert resource_manager._performance_enabled == True
        
        # Should have access to performance components
        perf_monitor = resource_manager.get_performance_monitor()
        cache_optimizer = resource_manager.get_cache_optimizer()
        async_ui_manager = resource_manager.get_async_ui_manager()
        
        # Components może być None jeśli import failed (graceful degradation)
        # ale nie powinno crashować
        assert resource_manager._performance_monitor is not None or not resource_manager._performance_enabled
        
        resource_manager.cleanup()
    
    def test_cache_stats_integration(self):
        """Test integracji cache stats z resource manager."""
        resource_manager = TileResourceManager()
        
        # Force stats update
        resource_manager._update_statistics()
        
        stats = resource_manager.get_statistics()
        
        # Should have cache stats
        assert hasattr(stats, 'cache_hit_ratio')
        assert hasattr(stats, 'cache_hits')
        assert hasattr(stats, 'cache_misses')
        
        resource_manager.cleanup()
    
    def test_performance_enable_disable(self):
        """Test włączania/wyłączania performance optimization."""
        resource_manager = TileResourceManager()
        
        # Initially enabled
        assert resource_manager._performance_enabled == True
        
        # Disable performance
        resource_manager.enable_performance_optimization(False)
        assert resource_manager._performance_enabled == False
        
        # Re-enable
        resource_manager.enable_performance_optimization(True)
        assert resource_manager._performance_enabled == True
        
        resource_manager.cleanup()
    
    def test_global_singletons(self):
        """Test globalnych singleton instances."""
        # Test wszystkich singleton getters
        perf_monitor = get_performance_monitor()
        cache_optimizer = get_cache_optimizer()
        async_ui_manager = get_async_ui_manager()
        resource_manager = get_resource_manager()
        
        # Should return same instances na subsequent calls
        assert get_performance_monitor() is perf_monitor
        assert get_cache_optimizer() is cache_optimizer  
        assert get_async_ui_manager() is async_ui_manager
        assert get_resource_manager() is resource_manager
        
        # Cleanup wszystkich singletons
        from src.ui.widgets.tile_performance_monitor import cleanup_performance_monitor
        from src.ui.widgets.tile_cache_optimizer import cleanup_cache_optimizer
        from src.ui.widgets.tile_async_ui_manager import cleanup_async_ui_manager
        from src.ui.widgets.tile_resource_manager import cleanup_resource_manager
        
        cleanup_performance_monitor()
        cleanup_cache_optimizer()
        cleanup_async_ui_manager()
        cleanup_resource_manager()


class TestPerformanceMetrics:
    """Testy dla performance metrics i measurement."""
    
    def test_performance_sample_creation(self):
        """Test tworzenia performance samples."""
        sample = PerformanceSample(
            metric=PerformanceMetric.RENDER_TIME,
            value=15.5,
            timestamp=0,  # Will be auto-set
            context={'test': True}
        )
        
        assert sample.metric == PerformanceMetric.RENDER_TIME
        assert sample.value == 15.5
        assert sample.timestamp > 0  # Should be auto-set
        assert sample.context['test'] == True
    
    def test_performance_stats_calculation(self):
        """Test kalkulacji performance stats."""
        stats = PerformanceStats(PerformanceMetric.MEMORY_USAGE)
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        
        stats.update_from_samples(values)
        
        assert stats.sample_count == 5
        assert stats.min_value == 10.0
        assert stats.max_value == 50.0
        assert stats.avg_value == 30.0
        assert stats.median_value == 30.0
        assert stats.total_time == 150.0
    
    def test_frame_timing_stats(self):
        """Test frame timing statistics."""
        frame_stats = FrameTimingStats(target_fps=60)
        
        # Add frame times
        frame_stats.add_frame_time(10.0)  # Good frame
        frame_stats.add_frame_time(25.0)  # Dropped frame
        frame_stats.add_frame_time(15.0)  # Good frame
        
        assert frame_stats.frame_count == 3
        assert frame_stats.dropped_frames == 1  # Only 25ms frame
        assert frame_stats.get_frame_drop_rate() == 33.33333333333333  # 1/3 * 100
        
        fps = frame_stats.get_fps()
        assert fps > 0
        assert fps < 100  # Reasonable range


if __name__ == '__main__':
    pytest.main([__file__]) 