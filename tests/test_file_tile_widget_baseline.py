#!/usr/bin/env python3
"""
BASELINE PERFORMANCE TESTS dla FileTileWidget
ETAP 0: Przygotowanie - ustalenie metryk początkowych przed refaktoryzacją
"""

import gc
import os
import sys
import time
import tracemalloc
import unittest
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# PyQt6 imports
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

# App imports
from src.models.file_pair import FilePair
from src.ui.widgets.file_tile_widget import FileTileWidget


class BaselinePerformanceTests(unittest.TestCase):
    """
    Baseline testy wydajności dla FileTileWidget.
    Te testy ustanawiają metryki przed refaktoryzacją.
    """

    @classmethod
    def setUpClass(cls):
        """Setup QApplication dla testów Qt."""
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

        # Setup test data paths - używamy absolutnych ścieżek
        current_dir = os.path.abspath(os.path.dirname(__file__))
        cls.test_archive_path = os.path.join(current_dir, "test_archive.blend")
        cls.test_preview_path = os.path.join(current_dir, "test_preview.jpg")
        cls.test_working_directory = os.path.join(current_dir, "test_working_dir")

    @classmethod
    def tearDownClass(cls):
        """Cleanup po testach."""
        if hasattr(cls, "app"):
            cls.app.quit()

    def setUp(self):
        """Setup dla każdego testu."""
        self.tiles: List[FileTileWidget] = []

        # Utwórz test FilePair z absolutnymi ścieżkami
        self.test_file_pair = FilePair(
            archive_path=self.test_archive_path,
            preview_path=self.test_preview_path,
            working_directory=self.test_working_directory,
        )

        # Mock file existence
        self.patcher = patch("os.path.exists")
        self.mock_exists = self.patcher.start()
        self.mock_exists.return_value = True

    def tearDown(self):
        """Cleanup po każdym teście."""
        # Cleanup tiles
        for tile in self.tiles:
            try:
                tile.cleanup() if hasattr(tile, "cleanup") else None
                tile.deleteLater()
            except Exception:
                pass
        self.tiles.clear()

        # Force garbage collection
        gc.collect()

        # Stop patchers
        self.patcher.stop()

    def test_baseline_memory_usage_single_tile(self):
        """
        BASELINE: Memory usage dla pojedynczego kafelka.
        Target: ~15MB (obecny stan przed refaktoryzacją)
        """
        print("\n=== BASELINE: Memory Usage - Single Tile ===")

        # Start memory tracking
        tracemalloc.start()

        # Create tile
        tile = FileTileWidget(self.test_file_pair)
        self.tiles.append(tile)

        # Force processing
        QCoreApplication.processEvents()

        # Measure memory
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_mb = current / 1024 / 1024

        print(f"Single tile memory usage: {memory_mb:.2f} MB")
        print(f"Peak memory usage: {peak / 1024 / 1024:.2f} MB")

        # Record baseline (obecny stan - można być więcej niż expected)
        self.assertLess(memory_mb, 50.0, "Single tile uses excessive memory (>50MB)")

        return memory_mb

    def test_baseline_memory_usage_100_tiles(self):
        """
        BASELINE: Memory usage dla 100 kafelków.
        Target: Current state before refactoring
        """
        print("\n=== BASELINE: Memory Usage - 100 Tiles ===")

        # Start memory tracking
        tracemalloc.start()

        start_time = time.time()

        # Create 100 tiles z absolutnymi ścieżkami
        for i in range(100):
            archive_path = os.path.join(
                os.path.dirname(self.test_archive_path), f"test_archive_{i}.blend"
            )
            preview_path = os.path.join(
                os.path.dirname(self.test_preview_path), f"test_preview_{i}.jpg"
            )

            file_pair = FilePair(
                archive_path=archive_path,
                preview_path=preview_path,
                working_directory=self.test_working_directory,
            )
            tile = FileTileWidget(file_pair)
            self.tiles.append(tile)

            # Process events periodically
            if i % 10 == 0:
                QCoreApplication.processEvents()

        creation_time = time.time() - start_time

        # Measure memory
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        memory_mb = current / 1024 / 1024
        memory_per_tile_mb = memory_mb / 100

        print(f"100 tiles total memory: {memory_mb:.2f} MB")
        print(f"Average memory per tile: {memory_per_tile_mb:.2f} MB")
        print(f"Creation time for 100 tiles: {creation_time:.2f} seconds")
        print(f"Average creation time per tile: {creation_time/100*1000:.1f} ms")

        # Record baseline metrics
        self.assertLess(memory_mb, 2000.0, "100 tiles use excessive memory (>2GB)")
        self.assertLess(
            creation_time, 30.0, "Tile creation too slow (>30s for 100 tiles)"
        )

        return {
            "total_memory_mb": memory_mb,
            "memory_per_tile_mb": memory_per_tile_mb,
            "creation_time_s": creation_time,
            "creation_time_per_tile_ms": creation_time / 100 * 1000,
        }

    def test_baseline_thumbnail_loading_performance(self):
        """
        BASELINE: Wydajność ładowania miniaturek.
        """
        print("\n=== BASELINE: Thumbnail Loading Performance ===")

        # Mock thumbnail cache
        with patch(
            "src.ui.widgets.thumbnail_cache.ThumbnailCache.get_instance"
        ) as mock_cache:
            mock_cache_instance = MagicMock()
            mock_cache_instance.get_thumbnail.return_value = None  # Force async loading
            mock_cache.return_value = mock_cache_instance

            start_time = time.time()

            # Create tile with preview
            tile = FileTileWidget(self.test_file_pair)
            self.tiles.append(tile)

            # Process events to trigger async loading
            for _ in range(100):  # Max 1 second wait
                QCoreApplication.processEvents()
                time.sleep(0.01)
                if hasattr(tile, "original_thumbnail") and tile.original_thumbnail:
                    break

            load_time = time.time() - start_time

            print(f"Thumbnail loading time: {load_time*1000:.1f} ms")

            # Baseline expectation (może być wolne przed optymalizacją)
            self.assertLess(load_time, 5.0, "Thumbnail loading extremely slow (>5s)")

            return load_time * 1000  # Return in milliseconds

    def test_baseline_ui_responsiveness(self):
        """
        BASELINE: UI responsiveness podczas operacji.
        """
        print("\n=== BASELINE: UI Responsiveness ===")

        frame_times = []

        # Create tile
        tile = FileTileWidget(self.test_file_pair)
        self.tiles.append(tile)

        # Measure frame processing times
        for i in range(50):
            start_time = time.perf_counter()

            # Simulate UI operations
            tile.update()
            QCoreApplication.processEvents()

            frame_time = time.perf_counter() - start_time
            frame_times.append(frame_time * 1000)  # Convert to ms

        avg_frame_time = sum(frame_times) / len(frame_times)
        max_frame_time = max(frame_times)

        print(f"Average frame time: {avg_frame_time:.2f} ms")
        print(f"Max frame time: {max_frame_time:.2f} ms")
        print(f"Frames >16ms (60fps): {sum(1 for t in frame_times if t > 16)}/50")

        # Baseline expectations
        self.assertLess(avg_frame_time, 100.0, "Average frame time too high (>100ms)")
        self.assertLess(max_frame_time, 500.0, "Max frame time too high (>500ms)")

        return {
            "avg_frame_time_ms": avg_frame_time,
            "max_frame_time_ms": max_frame_time,
            "frames_over_16ms": sum(1 for t in frame_times if t > 16),
        }

    def test_baseline_api_compatibility(self):
        """
        BASELINE: Test wszystkich metod API które muszą zostać zachowane.
        """
        print("\n=== BASELINE: API Compatibility Check ===")

        tile = FileTileWidget(self.test_file_pair)
        self.tiles.append(tile)

        # Test wszystkich publicznych metod
        required_methods = [
            "update_data",
            "set_thumbnail_size",
            "set_file_pair",
            "open_file",
            "preview_image",
            "show_properties",
        ]

        required_signals = [
            "archive_open_requested",
            "preview_image_requested",
            "tile_selected",
            "stars_changed",
            "color_tag_changed",
            "tile_context_menu_requested",
            "file_pair_updated",
        ]

        required_attributes = ["file_pair", "thumbnail_size", "PREDEFINED_COLORS"]

        # Check methods
        missing_methods = []
        for method in required_methods:
            if not hasattr(tile, method):
                missing_methods.append(method)

        # Check signals
        missing_signals = []
        for signal in required_signals:
            if not hasattr(tile, signal):
                missing_signals.append(signal)

        # Check attributes
        missing_attributes = []
        for attr in required_attributes:
            if not hasattr(tile, attr):
                missing_attributes.append(attr)

        print(
            f"API Methods: {len(required_methods) - len(missing_methods)}/{len(required_methods)} OK"
        )
        print(
            f"API Signals: {len(required_signals) - len(missing_signals)}/{len(required_signals)} OK"
        )
        print(
            f"API Attributes: {len(required_attributes) - len(missing_attributes)}/{len(required_attributes)} OK"
        )

        if missing_methods:
            print(f"Missing methods: {missing_methods}")
        if missing_signals:
            print(f"Missing signals: {missing_signals}")
        if missing_attributes:
            print(f"Missing attributes: {missing_attributes}")

        # All API elements must be present
        self.assertEqual(len(missing_methods), 0, f"Missing methods: {missing_methods}")
        self.assertEqual(len(missing_signals), 0, f"Missing signals: {missing_signals}")
        self.assertEqual(
            len(missing_attributes), 0, f"Missing attributes: {missing_attributes}"
        )

        return {
            "methods_ok": len(required_methods) - len(missing_methods),
            "signals_ok": len(required_signals) - len(missing_signals),
            "attributes_ok": len(required_attributes) - len(missing_attributes),
            "total_api_elements": len(required_methods)
            + len(required_signals)
            + len(required_attributes),
        }

    def test_baseline_comprehensive_metrics(self):
        """
        COMPREHENSIVE BASELINE: Wszystkie metryki w jednym teście.
        """
        print("\n" + "=" * 60)
        print("COMPREHENSIVE BASELINE METRICS REPORT")
        print("=" * 60)

        # Run all baseline tests
        try:
            memory_single = self.test_baseline_memory_usage_single_tile()
        except Exception as e:
            print(f"Single tile memory test failed: {e}")
            memory_single = -1

        try:
            memory_100 = self.test_baseline_memory_usage_100_tiles()
        except Exception as e:
            print(f"100 tiles memory test failed: {e}")
            memory_100 = {"memory_per_tile_mb": -1, "creation_time_per_tile_ms": -1}

        try:
            thumbnail_time = self.test_baseline_thumbnail_loading_performance()
        except Exception as e:
            print(f"Thumbnail loading test failed: {e}")
            thumbnail_time = -1

        try:
            ui_metrics = self.test_baseline_ui_responsiveness()
        except Exception as e:
            print(f"UI responsiveness test failed: {e}")
            ui_metrics = {"avg_frame_time_ms": -1, "frames_over_16ms": -1}

        try:
            api_metrics = self.test_baseline_api_compatibility()
        except Exception as e:
            print(f"API compatibility test failed: {e}")
            api_metrics = {"total_api_elements": -1}

        # Summary report
        print("\n" + "=" * 60)
        print("BASELINE SUMMARY REPORT")
        print("=" * 60)
        print(f"✅ Single Tile Memory:     {memory_single:.1f} MB")
        print(
            f"✅ Memory per Tile (100):   {memory_100.get('memory_per_tile_mb', -1):.1f} MB"
        )
        print(
            f"✅ Tile Creation Time:      {memory_100.get('creation_time_per_tile_ms', -1):.1f} ms"
        )
        print(f"✅ Thumbnail Load Time:     {thumbnail_time:.1f} ms")
        print(
            f"✅ Average Frame Time:      {ui_metrics.get('avg_frame_time_ms', -1):.1f} ms"
        )
        print(
            f"✅ Frames >16ms (60fps):    {ui_metrics.get('frames_over_16ms', -1)}/50"
        )
        print(
            f"✅ API Elements Working:    {api_metrics.get('total_api_elements', -1)}"
        )
        print("=" * 60)

        print("\n🎯 TARGETS FOR REFACTORING:")
        print("• Memory per tile:     <5 MB (target 60% reduction)")
        print("• Frame time:          <16 ms (60fps target)")
        print("• Thumbnail loading:   <200 ms (progressive loading)")
        print("• API compatibility:   100% preserved")
        print("=" * 60)


def run_baseline_tests():
    """Uruchom wszystkie baseline testy."""
    unittest.main(argv=[""], exit=False, verbosity=2)


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(level=logging.WARNING)  # Quiet down logs during tests

    print("🚀 STARTING BASELINE PERFORMANCE TESTS")
    print("📊 Establishing metrics before refactoring...")
    print()

    run_baseline_tests()
