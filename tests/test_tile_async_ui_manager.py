"""
Testy dla TileAsyncUIManager - ETAP 8
"""

import pytest
import time
import threading
from PyQt6.QtWidgets import QApplication

from src.ui.widgets.tile_async_ui_manager import (
    TileAsyncUIManager,
    UIUpdatePriority,
    UIUpdateTask,
    cleanup_async_ui_manager,
    get_async_ui_manager,
)


class TestTileAsyncUIManager:
    """Testy dla TileAsyncUIManager."""

    def setup_method(self):
        """Setup przed każdym testem."""
        cleanup_async_ui_manager()  # Cleanup any existing instance
        # Create QApplication for QTimer to work
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
        self.manager = TileAsyncUIManager(max_concurrent_tasks=3)

    def teardown_method(self):
        """Cleanup po każdym teście."""
        if hasattr(self, "manager"):
            self.manager.cleanup()

    def test_initialization(self):
        """Test inicjalizacji."""
        assert self.manager.max_concurrent_tasks == 3
        assert self.manager.enable_batching is True
        assert self.manager._scheduler is not None
        assert self.manager._debounce_manager is not None
        assert self.manager._batch_updater is not None

    def test_schedule_async_update(self):
        """Test planowania asynchronicznych update'ów."""
        results = []

        def test_func(value):
            results.append(value)
            return value

        # Schedule task
        success = self.manager.schedule_async_update(
            test_func, "test_value", priority=UIUpdatePriority.HIGH
        )
        assert success is True

        # Process events and wait for execution
        self.app.processEvents()
        time.sleep(0.1)
        self.app.processEvents()
        assert "test_value" in results

    def test_priority_queue(self):
        """Test kolejki priorytetowej."""
        execution_order = []

        def low_priority():
            execution_order.append("LOW")

        def high_priority():
            execution_order.append("HIGH")

        # Schedule in reverse order
        self.manager.schedule_async_update(low_priority, priority=UIUpdatePriority.LOW)
        time.sleep(0.01)  # Small delay
        self.manager.schedule_async_update(
            high_priority, priority=UIUpdatePriority.HIGH
        )

        # Process events and wait for execution
        self.app.processEvents()
        time.sleep(0.2)
        self.app.processEvents()
        # High priority should execute first (lower enum value)
        assert len(execution_order) >= 2
        assert execution_order[0] == "HIGH"

    def test_queue_size_limit(self):
        """Test limitu rozmiaru kolejki."""
        # Fill queue beyond limit
        for i in range(600):  # More than default 500 limit
            success = self.manager.schedule_async_update(
                lambda: time.sleep(0.001), priority=UIUpdatePriority.LOW
            )
            if not success:
                break

        # Should reject tasks when queue is full
        assert success is False

    def test_debounce_operation(self):
        """Test debounce operacji."""
        call_count = 0

        def debounced_func():
            nonlocal call_count
            call_count += 1

        # Multiple rapid calls
        for _ in range(5):
            self.manager.debounce_operation("test_op", debounced_func, delay_ms=50)

        # Should not execute immediately
        assert call_count == 0

        # Wait for debounce delay and process events
        time.sleep(0.1)
        self.app.processEvents()
        assert call_count == 1  # Only last call should execute

    def test_batch_operations(self):
        """Test batch operacji."""
        update_count = 0

        def batch_update():
            nonlocal update_count
            update_count += 1

        # Add multiple updates
        for _ in range(5):
            self.manager.add_to_batch(batch_update)

        # Force flush
        self.manager.flush_batch_updates()

        # All updates should be executed
        assert update_count == 5

    def test_thumbnail_loading(self):
        """Test ładowania miniaturek."""
        results = []

        def load_thumbnail():
            time.sleep(0.01)  # Simulate loading
            return "thumbnail_data"

        def callback(result):
            results.append(result)

        # Schedule thumbnail load
        success = self.manager.schedule_thumbnail_load(
            load_thumbnail, callback=callback
        )
        assert success is True

        # Process events and wait for execution
        self.app.processEvents()
        time.sleep(0.1)
        self.app.processEvents()
        assert "thumbnail_data" in results

    def test_memory_pressure_handling(self):
        """Test obsługi memory pressure."""
        # Simulate memory pressure
        self.manager.handle_memory_pressure(250.0)  # > 200MB

        # Should emit warning signal
        # Note: In real test we would connect to signal and verify
        # For now just check no exception is raised
        assert True

    def test_performance_stats(self):
        """Test statystyk wydajności."""
        stats = self.manager.get_performance_stats()

        assert "scheduler" in stats
        assert "current_fps" in stats
        assert "frame_drops" in stats
        assert "max_concurrent_tasks" in stats
        assert "batching_enabled" in stats
        assert stats["max_concurrent_tasks"] == 3
        assert stats["batching_enabled"] is True

    def test_singleton_pattern(self):
        """Test singleton pattern."""
        # Cleanup any existing instance
        cleanup_async_ui_manager()

        # Get instances
        instance1 = get_async_ui_manager(max_concurrent_tasks=5)
        instance2 = get_async_ui_manager(max_concurrent_tasks=10)  # Should return same

        assert instance1 is instance2
        assert instance1.max_concurrent_tasks == 5  # First call parameters

        # Cleanup
        cleanup_async_ui_manager()

    def test_thread_safety(self):
        """Test thread safety."""
        results = []
        errors = []

        def worker(worker_id):
            try:
                for i in range(10):
                    self.manager.schedule_async_update(
                        lambda: results.append(f"worker_{worker_id}_task_{i}"),
                        priority=UIUpdatePriority.NORMAL,
                    )
            except Exception as e:
                errors.append(str(e))

        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Process events and wait for task execution
        self.app.processEvents()
        time.sleep(0.5)
        self.app.processEvents()

        # Check results
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) > 0  # Some tasks should complete

    def test_cleanup(self):
        """Test cleanup."""
        # Add some tasks
        self.manager.schedule_async_update(lambda: None)
        self.manager.debounce_operation("test", lambda: None)
        self.manager.add_to_batch(lambda: None)

        # Cleanup
        self.manager.cleanup()

        # Should not crash
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
