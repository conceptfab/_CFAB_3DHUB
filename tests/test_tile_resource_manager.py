"""
ETAP 7: RESOURCE MANAGEMENT - Testy dla TileResourceManager
"""

import gc
import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget, QApplication

from src.ui.widgets.tile_resource_manager import (
    TileResourceManager,
    MemoryMonitor,
    WorkerPoolManager,
    MemoryUsageStats,
    ResourceLimits,
    get_resource_manager,
    cleanup_resource_manager,
    with_resource_management
)


@pytest.fixture
def app():
    """Create QApplication for tests."""
    if not QApplication.instance():
        app = QApplication([])
        yield app
        app.quit()
    else:
        yield QApplication.instance()


@pytest.fixture
def resource_limits():
    """Test resource limits."""
    return ResourceLimits(
        max_tiles=10,
        max_memory_mb=100,
        max_memory_per_tile_mb=2,
        max_concurrent_workers=3,
        cleanup_interval_seconds=1,
        memory_check_interval_seconds=1
    )


@pytest.fixture
def resource_manager(app, resource_limits):
    """Create TileResourceManager for testing."""
    manager = TileResourceManager(resource_limits)
    yield manager
    manager.cleanup()


@pytest.fixture
def mock_tile():
    """Mock tile widget."""
    tile = Mock()
    tile.cleanup = Mock()
    return tile


@pytest.fixture
def mock_component():
    """Mock component."""
    component = Mock()
    component.cleanup = Mock()
    return component


class TestResourceLimits:
    """Test ResourceLimits dataclass."""
    
    def test_default_limits(self):
        """Test default resource limits."""
        limits = ResourceLimits()
        
        assert limits.max_tiles == 1000
        assert limits.max_memory_mb == 4000
        assert limits.max_memory_per_tile_mb == 10
        assert limits.max_concurrent_workers == 8
        assert limits.cleanup_interval_seconds == 180
        assert limits.memory_check_interval_seconds == 30
        assert limits.cache_cleanup_threshold_ratio == 0.7
    
    def test_custom_limits(self):
        """Test custom resource limits."""
        limits = ResourceLimits(
            max_tiles=50,
            max_memory_mb=200,
            max_concurrent_workers=5
        )
        
        assert limits.max_tiles == 50
        assert limits.max_memory_mb == 200
        assert limits.max_concurrent_workers == 5
        # Defaults preserved
        assert limits.max_memory_per_tile_mb == 5


class TestMemoryUsageStats:
    """Test MemoryUsageStats dataclass."""
    
    def test_default_stats(self):
        """Test default stats values."""
        stats = MemoryUsageStats()
        
        assert stats.total_tiles == 0
        assert stats.active_tiles == 0
        assert stats.memory_per_tile_mb == 0.0
        assert stats.total_memory_mb == 0.0
        assert stats.cache_hits == 0
        assert stats.cache_misses == 0
        assert stats.cache_hit_ratio == 0.0
        assert stats.worker_count == 0
        assert stats.timestamp == 0.0
    
    def test_stats_with_values(self):
        """Test stats with actual values."""
        stats = MemoryUsageStats(
            total_tiles=100,
            active_tiles=95,
            memory_per_tile_mb=2.5,
            total_memory_mb=250.0,
            cache_hits=80,
            cache_misses=20,
            worker_count=5,
            timestamp=time.time()
        )
        
        assert stats.total_tiles == 100
        assert stats.active_tiles == 95
        assert stats.memory_per_tile_mb == 2.5
        assert stats.total_memory_mb == 250.0
        assert stats.cache_hits == 80
        assert stats.cache_misses == 20
        assert stats.worker_count == 5
        assert stats.timestamp > 0


class TestMemoryMonitor:
    """Test MemoryMonitor class."""
    
    def test_memory_monitor_initialization(self, app, resource_limits):
        """Test memory monitor initialization."""
        monitor = MemoryMonitor(resource_limits)
        
        assert monitor.limits == resource_limits
        assert monitor._last_check_time == 0
        assert len(monitor._memory_history) == 0
        assert monitor._max_history == 100
        assert monitor._check_timer.isActive()
        
        monitor._check_timer.stop()
    
    def test_memory_trend_insufficient_data(self, app, resource_limits):
        """Test memory trend with insufficient data."""
        monitor = MemoryMonitor(resource_limits)
        
        trend = monitor.get_memory_trend()
        assert trend == "insufficient_data"
        
        monitor._check_timer.stop()
    
    def test_memory_trend_increasing(self, app, resource_limits):
        """Test increasing memory trend."""
        monitor = MemoryMonitor(resource_limits)
        monitor._memory_history = [100.0, 105.0, 120.0]  # 20% increase
        
        trend = monitor.get_memory_trend()
        assert trend == "increasing"
        
        monitor._check_timer.stop()
    
    def test_memory_trend_decreasing(self, app, resource_limits):
        """Test decreasing memory trend."""
        monitor = MemoryMonitor(resource_limits)
        monitor._memory_history = [120.0, 105.0, 100.0]  # 17% decrease
        
        trend = monitor.get_memory_trend()
        assert trend == "decreasing"
        
        monitor._check_timer.stop()
    
    def test_memory_trend_stable(self, app, resource_limits):
        """Test stable memory trend."""
        monitor = MemoryMonitor(resource_limits)
        monitor._memory_history = [100.0, 102.0, 103.0]  # 3% increase
        
        trend = monitor.get_memory_trend()
        assert trend == "stable"
        
        monitor._check_timer.stop()
    
    @patch('src.ui.widgets.tile_resource_manager.psutil')
    def test_memory_check_with_psutil(self, mock_psutil, app, resource_limits):
        """Test memory check with psutil available."""
        # Mock psutil
        mock_process = Mock()
        mock_process.memory_info.return_value.rss = 50 * 1024 * 1024  # 50MB
        mock_psutil.Process.return_value = mock_process
        
        monitor = MemoryMonitor(resource_limits)
        monitor._check_memory_usage()
        
        assert len(monitor._memory_history) == 1
        assert monitor._memory_history[0] == 50.0
        assert monitor._last_check_time > 0
        
        monitor._check_timer.stop()
    
    @patch('src.ui.widgets.tile_resource_manager.psutil', side_effect=ImportError)
    def test_memory_check_without_psutil(self, mock_psutil, app, resource_limits):
        """Test memory check without psutil."""
        monitor = MemoryMonitor(resource_limits)
        
        # Should not raise exception
        monitor._check_memory_usage()
        
        assert len(monitor._memory_history) == 0
        
        monitor._check_timer.stop()


class TestWorkerPoolManager:
    """Test WorkerPoolManager class."""
    
    def test_worker_pool_initialization(self):
        """Test worker pool initialization."""
        pool = WorkerPoolManager(max_workers=5)
        
        assert pool.max_workers == 5
        assert len(pool._active_workers) == 0
        assert pool._worker_counter == 0
        assert pool.get_active_count() == 0
    
    def test_register_worker_success(self):
        """Test successful worker registration."""
        pool = WorkerPoolManager(max_workers=3)
        
        # Register first worker
        worker_id1 = pool.register_worker()
        assert worker_id1 == 1
        assert pool.get_active_count() == 1
        assert pool.can_start_worker() is True
        
        # Register second worker
        worker_id2 = pool.register_worker()
        assert worker_id2 == 2
        assert pool.get_active_count() == 2
        assert pool.can_start_worker() is True
        
        # Register third worker
        worker_id3 = pool.register_worker()
        assert worker_id3 == 3
        assert pool.get_active_count() == 3
        assert pool.can_start_worker() is False
    
    def test_register_worker_limit_reached(self):
        """Test worker registration when limit reached."""
        pool = WorkerPoolManager(max_workers=1)
        
        # Register first worker (should succeed)
        worker_id1 = pool.register_worker()
        assert worker_id1 == 1
        
        # Try to register second worker (should fail)
        worker_id2 = pool.register_worker()
        assert worker_id2 is None
        assert pool.get_active_count() == 1
    
    def test_unregister_worker(self):
        """Test worker unregistration."""
        pool = WorkerPoolManager(max_workers=3)
        
        # Register workers
        worker_id1 = pool.register_worker()
        worker_id2 = pool.register_worker()
        assert pool.get_active_count() == 2
        
        # Unregister first worker
        pool.unregister_worker(worker_id1)
        assert pool.get_active_count() == 1
        assert pool.can_start_worker() is True
        
        # Unregister second worker
        pool.unregister_worker(worker_id2)
        assert pool.get_active_count() == 0
    
    def test_unregister_nonexistent_worker(self):
        """Test unregistering non-existent worker."""
        pool = WorkerPoolManager(max_workers=3)
        
        # Should not raise exception
        pool.unregister_worker(999)
        assert pool.get_active_count() == 0
    
    def test_force_cleanup(self):
        """Test force cleanup of all workers."""
        pool = WorkerPoolManager(max_workers=3)
        
        # Register workers
        pool.register_worker()
        pool.register_worker()
        assert pool.get_active_count() == 2
        
        # Force cleanup
        pool.force_cleanup()
        assert pool.get_active_count() == 0
        assert pool.can_start_worker() is True


class TestTileResourceManager:
    """Test TileResourceManager class."""
    
    def test_initialization(self, resource_manager):
        """Test resource manager initialization."""
        assert resource_manager.limits is not None
        assert len(resource_manager._active_tiles) == 0
        assert len(resource_manager._active_components) == 4
        assert resource_manager._memory_monitor is not None
        assert resource_manager._worker_pool is not None
        assert resource_manager._cleanup_timer.isActive()
    
    def test_register_tile_success(self, resource_manager, mock_tile):
        """Test successful tile registration."""
        result = resource_manager.register_tile(mock_tile)
        
        assert result is True
        assert resource_manager.get_active_tile_count() == 1
    
    def test_register_tile_limit_reached(self, resource_manager):
        """Test tile registration when limit reached."""
        # Register tiles up to limit (10)
        tiles = []
        for i in range(10):
            tile = Mock()
            result = resource_manager.register_tile(tile)
            assert result is True
            tiles.append(tile)
        
        # Try to register one more (should fail)
        extra_tile = Mock()
        result = resource_manager.register_tile(extra_tile)
        assert result is False
        assert resource_manager.get_active_tile_count() == 10
    
    def test_register_component_success(self, resource_manager, mock_component):
        """Test successful component registration."""
        result = resource_manager.register_component("thumbnail", mock_component)
        assert result is True
    
    def test_register_component_invalid_type(self, resource_manager, mock_component):
        """Test component registration with invalid type."""
        result = resource_manager.register_component("invalid_type", mock_component)
        assert result is False
    
    def test_worker_management(self, resource_manager):
        """Test worker management methods."""
        # Should be able to start workers initially
        assert resource_manager.can_start_worker() is True
        
        # Register workers up to limit
        worker_ids = []
        for i in range(3):  # limit is 3
            worker_id = resource_manager.register_worker()
            assert worker_id is not None
            worker_ids.append(worker_id)
        
        # Should not be able to start more workers
        assert resource_manager.can_start_worker() is False
        
        # Unregister a worker
        resource_manager.unregister_worker(worker_ids[0])
        assert resource_manager.can_start_worker() is True
    
    def test_get_statistics(self, resource_manager, mock_tile):
        """Test statistics retrieval."""
        # Register a tile
        resource_manager.register_tile(mock_tile)
        
        # Get statistics
        stats = resource_manager.get_statistics()
        
        assert isinstance(stats, MemoryUsageStats)
        assert stats.total_tiles == 1
        assert stats.active_tiles == 1
        assert stats.timestamp > 0
    
    def test_cleanup_performance(self, resource_manager):
        """Test cleanup execution."""
        # Spy on cleanup_performed signal
        cleanup_count = None
        
        def on_cleanup(count):
            nonlocal cleanup_count
            cleanup_count = count
        
        resource_manager.cleanup_performed.connect(on_cleanup)
        
        # Perform cleanup
        resource_manager.perform_cleanup()
        
        # Cleanup should have been performed
        assert cleanup_count is not None
    
    def test_emergency_cleanup(self, resource_manager, mock_tile):
        """Test emergency cleanup."""
        # Register tile with cleanup method
        mock_tile.cleanup = Mock()
        resource_manager.register_tile(mock_tile)
        
        # Perform emergency cleanup
        resource_manager.perform_emergency_cleanup()
        
        # Tile cleanup should have been called
        mock_tile.cleanup.assert_called_once()
    
    def test_memory_trend(self, resource_manager):
        """Test memory trend retrieval."""
        trend = resource_manager.get_memory_trend()
        assert trend in ["insufficient_data", "increasing", "decreasing", "stable"]
    
    def test_resource_limit_check(self, resource_manager):
        """Test resource limit checking."""
        # Initially should not be at limit
        assert resource_manager.is_resource_limit_reached() is False
        
        # Register tiles up to limit
        for i in range(10):
            tile = Mock()
            resource_manager.register_tile(tile)
        
        # Should now be at limit
        assert resource_manager.is_resource_limit_reached() is True
    
    def test_debug_info(self, resource_manager):
        """Test debug info retrieval."""
        debug_info = resource_manager.get_debug_info()
        
        assert isinstance(debug_info, dict)
        assert 'limits' in debug_info
        assert 'current_stats' in debug_info
        assert 'memory_trend' in debug_info
        assert 'component_counts' in debug_info
        assert 'last_cleanup_ago_seconds' in debug_info
        assert 'worker_pool_active' in debug_info


class TestSingletonManager:
    """Test singleton resource manager."""
    
    def teardown_method(self):
        """Cleanup after each test."""
        cleanup_resource_manager()
    
    def test_singleton_instance(self, app):
        """Test singleton pattern."""
        manager1 = get_resource_manager()
        manager2 = get_resource_manager()
        
        assert manager1 is manager2
    
    def test_singleton_with_custom_limits(self, app):
        """Test singleton with custom limits."""
        limits = ResourceLimits(max_tiles=50)
        manager = get_resource_manager(limits)
        
        assert manager.limits.max_tiles == 50
        
        # Second call should return same instance (limits ignored)
        manager2 = get_resource_manager(ResourceLimits(max_tiles=100))
        assert manager2 is manager
        assert manager2.limits.max_tiles == 50  # Original limits preserved
    
    def test_cleanup_singleton(self, app):
        """Test singleton cleanup."""
        manager = get_resource_manager()
        cleanup_resource_manager()
        
        # Should create new instance after cleanup
        manager2 = get_resource_manager()
        assert manager2 is not manager


class TestResourceManagementDecorator:
    """Test @with_resource_management decorator."""
    
    def teardown_method(self):
        """Cleanup after each test."""
        cleanup_resource_manager()
    
    def test_tile_decorator(self, app):
        """Test decorator for tile registration."""
        @with_resource_management(component_type="tile")
        class TestTile(QWidget):
            def __init__(self):
                super().__init__()
        
        # Create tile - should auto-register
        tile = TestTile()
        
        # Verify registration
        manager = get_resource_manager()
        assert manager.get_active_tile_count() == 1
    
    def test_component_decorator(self, app):
        """Test decorator for component registration."""
        @with_resource_management(component_type="thumbnail")
        class TestComponent(QObject):
            def __init__(self):
                super().__init__()
        
        # Create component - should auto-register  
        component = TestComponent()
        
        # Verify registration (harder to test directly, but should not error)
        manager = get_resource_manager()
        assert manager is not None


class TestThreadSafety:
    """Test thread safety of resource manager."""
    
    def test_concurrent_tile_registration(self, app, resource_limits):
        """Test concurrent tile registration."""
        manager = TileResourceManager(resource_limits)
        results = []
        errors = []
        
        def register_tiles():
            try:
                for i in range(5):
                    tile = Mock()
                    result = manager.register_tile(tile)
                    results.append(result)
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=register_tiles)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Should not have errors
        assert len(errors) == 0
        
        # Should have some successful registrations (up to limit)
        successful = sum(1 for r in results if r is True)
        assert successful <= resource_limits.max_tiles
        
        manager.cleanup()
    
    def test_concurrent_worker_registration(self, app, resource_limits):
        """Test concurrent worker registration."""
        manager = TileResourceManager(resource_limits)
        worker_ids = []
        errors = []
        
        def register_workers():
            try:
                for i in range(2):
                    worker_id = manager.register_worker()
                    if worker_id is not None:
                        worker_ids.append(worker_id)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=register_workers)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Should not have errors
        assert len(errors) == 0
        
        # Should have registered workers up to limit
        assert len(worker_ids) <= resource_limits.max_concurrent_workers
        
        manager.cleanup()


class TestResourceIntegration:
    """Test integration with actual widgets."""
    
    def test_widget_lifecycle(self, app):
        """Test widget creation and cleanup lifecycle."""
        # Simplified integration test - would need actual widgets in real scenario
        manager = get_resource_manager()
        
        # Simulate widget creation
        widget = Mock()
        widget.cleanup = Mock()
        
        # Register
        result = manager.register_tile(widget)
        assert result is True
        assert manager.get_active_tile_count() == 1
        
        # Simulate widget destruction
        widget.cleanup()
        
        # Force cleanup
        manager.perform_cleanup()
        
        cleanup_resource_manager()


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 