#!/usr/bin/env python3
"""
TESTY ETAP 1: TileConfig
"""

import sys
import unittest
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui.widgets.tile_config import (
    TileConfig,
    TileEvent,
    TileState,
    create_default_config,
    create_performance_config,
    create_testing_config,
)


class TestTileConfig(unittest.TestCase):
    """Testy dla TileConfig - ETAP 1 refaktoryzacji"""

    def test_default_config_creation(self):
        """Test tworzenia domyślnej konfiguracji"""
        config = create_default_config()

        # Test podstawowych wartości
        self.assertEqual(config.thumbnail_size, (250, 250))
        self.assertEqual(config.padding, 16)
        self.assertTrue(config.enable_animations)
        self.assertEqual(config.max_memory_per_tile_mb, 5)

        print("✅ Default config creation OK")

    def test_config_validation(self):
        """Test walidacji konfiguracji"""
        # Valid config should not raise
        valid_config = TileConfig(thumbnail_size=(150, 150), max_memory_per_tile_mb=5)
        self.assertIsNotNone(valid_config)

        # Invalid config should raise ValueError
        with self.assertRaises(ValueError):
            TileConfig(thumbnail_size=(50, 50))  # Too small

        print("✅ Config validation OK")

    def test_calculated_thumbnail_dimension(self):
        """Test obliczania wymiarów miniatury"""
        config = TileConfig(
            thumbnail_size=(250, 250),
            padding=16,
            filename_max_height=35,
            metadata_max_height=24,
        )

        dimension = config.get_calculated_thumbnail_dimension()

        # Should be: min(250-32, 250-35-24-32) = min(218, 159) = 159
        expected = 159
        self.assertEqual(dimension, expected)

        print(f"✅ Thumbnail dimension calculation: {dimension}px")

    def test_font_size_calculation(self):
        """Test obliczania rozmiaru czcionki"""
        config = TileConfig(font_size_range=(8, 18), font_scale_factor=12)

        # Test różnych szerokości kafelka
        font_size_120 = config.get_calculated_font_size(120)  # 120/12 = 10
        font_size_60 = config.get_calculated_font_size(60)  # 60/12 = 5 -> min 8
        font_size_300 = config.get_calculated_font_size(300)  # 300/12 = 25 -> max 18

        self.assertEqual(font_size_120, 10)
        self.assertEqual(font_size_60, 8)  # Min limit
        self.assertEqual(font_size_300, 18)  # Max limit

        print("✅ Font size calculations OK")

    def test_memory_calculations(self):
        """Test obliczeń memory usage"""
        config = TileConfig(max_memory_per_tile_mb=5)

        target_bytes = config.calculate_memory_target_bytes()
        expected_bytes = 5 * 1024 * 1024  # 5MB
        self.assertEqual(target_bytes, expected_bytes)

        # Test acceptable memory usage
        self.assertTrue(config.is_memory_usage_acceptable(4 * 1024 * 1024))  # 4MB OK
        self.assertFalse(
            config.is_memory_usage_acceptable(6 * 1024 * 1024)
        )  # 6MB NOT OK

        print("✅ Memory calculations OK")

    def test_predefined_configs(self):
        """Test predefiniowanych konfiguracji"""
        default = create_default_config()
        performance = create_performance_config()
        testing = create_testing_config()

        # Performance config should have lower memory target
        self.assertLess(
            performance.max_memory_per_tile_mb, default.max_memory_per_tile_mb
        )

        # Testing config should have animations disabled
        self.assertFalse(testing.enable_animations)
        self.assertFalse(testing.async_loading)

        print("✅ Predefined configs OK")

    def test_debug_info(self):
        """Test informacji debug"""
        config = create_default_config()
        debug_info = config.get_debug_info()

        required_keys = ["thumbnail_dimension", "memory_target_mb", "async_enabled"]

        for key in required_keys:
            self.assertIn(key, debug_info)

        print(f"✅ Debug info: {debug_info}")

    def test_enums(self):
        """Test enums dla stanów i eventów"""
        # Test TileState
        self.assertEqual(TileState.INITIALIZING.name, "INITIALIZING")
        self.assertEqual(TileState.READY.name, "READY")

        # Test TileEvent
        self.assertEqual(TileEvent.THUMBNAIL_LOADED.name, "THUMBNAIL_LOADED")
        self.assertEqual(TileEvent.USER_INTERACTION.name, "USER_INTERACTION")

        print("✅ Enums OK")


if __name__ == "__main__":
    print("🧪 TESTING ETAP 1: TileConfig")
    unittest.main()
