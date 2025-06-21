#!/usr/bin/env python3
"""
TESTY ETAP 3: ThumbnailComponent
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtWidgets import QApplication

    from src.ui.widgets.thumbnail_component import (
        ThumbnailComponent,
        create_thumbnail_component,
    )
    from src.ui.widgets.tile_config import TileConfig, TileState, create_testing_config
    from src.ui.widgets.tile_event_bus import create_event_bus
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


class TestThumbnailComponent(unittest.TestCase):
    """Testy dla ThumbnailComponent - ETAP 3 refaktoryzacji"""

    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication([])

    def setUp(self):
        """Setup dla każdego testu"""
        self.config = create_testing_config()  # Sync loading for tests
        self.event_bus = create_event_bus(enable_debug=True)
        self.component = create_thumbnail_component(self.config, self.event_bus)

        # Mock file path
        self.test_file = str(project_root / "test_image.jpg")

    def tearDown(self):
        """Cleanup po teście"""
        self.component.cleanup()

    def test_component_creation(self):
        """Test tworzenia komponentu"""
        component = create_thumbnail_component(self.config, self.event_bus)

        self.assertIsNotNone(component)
        self.assertEqual(component.get_current_state(), TileState.INITIALIZING)
        self.assertIsNone(component.get_current_pixmap())
        self.assertEqual(component.get_memory_usage_bytes(), 0)

        print("✅ Component creation OK")

    def test_state_management(self):
        """Test zarządzania stanem"""
        # Initial state
        self.assertEqual(self.component.get_current_state(), TileState.INITIALIZING)

        # State changes should be tracked
        initial_state = self.component.get_current_state()
        self.assertEqual(initial_state, TileState.INITIALIZING)

        print("✅ State management OK")

    def test_size_configuration(self):
        """Test konfiguracji rozmiaru"""
        # Test calculated size
        calculated_size = self.config.get_calculated_thumbnail_dimension()
        self.assertGreater(calculated_size, 0)

        # Test size setting with debouncing
        self.component.set_thumbnail_size((150, 150), immediate=True)

        print("✅ Size configuration OK")

    @patch("pathlib.Path.exists")
    def test_load_thumbnail_nonexistent_file(self, mock_exists):
        """Test ładowania nieistniejącego pliku"""
        mock_exists.return_value = False

        result = self.component.load_thumbnail("nonexistent.jpg")

        # Should fail gracefully
        self.assertFalse(result)
        self.assertEqual(self.component.get_current_state(), TileState.ERROR)

        print("✅ Nonexistent file handling OK")

    def test_memory_tracking(self):
        """Test śledzenia pamięci"""
        # Initial memory should be 0
        self.assertEqual(self.component.get_memory_usage_bytes(), 0)

        # Memory tracking should work
        memory_usage = self.component.get_memory_usage_bytes()
        self.assertIsInstance(memory_usage, int)
        self.assertGreaterEqual(memory_usage, 0)

        print("✅ Memory tracking OK")

    def test_debouncing_timer(self):
        """Test debouncing dla resize"""
        # Set size with debouncing (not immediate)
        self.component.set_thumbnail_size((200, 200), immediate=False)

        # Should have pending size
        self.assertIsNotNone(self.component._pending_size)

        # Apply immediately for test
        self.component._apply_size_change()

        print("✅ Debouncing timer OK")

    def test_cleanup(self):
        """Test cleanup komponentu"""
        # Setup some state
        self.component._memory_usage_bytes = 1000

        # Cleanup
        self.component.cleanup()

        # Verify cleanup
        self.assertIsNone(self.component.get_current_pixmap())
        self.assertEqual(self.component.get_memory_usage_bytes(), 0)
        self.assertEqual(self.component.get_current_state(), TileState.DISPOSED)

        print("✅ Cleanup OK")

    def test_event_bus_integration(self):
        """Test integracji z event bus"""
        # Event bus should be connected
        self.assertIsNotNone(self.component.event_bus)

        # Component should be able to emit events
        self.component._emit_error("Test error")

        print("✅ Event bus integration OK")

    def test_config_integration(self):
        """Test integracji z konfiguracją"""
        # Component should use config
        self.assertEqual(self.component.config.async_loading, False)  # Testing config
        self.assertEqual(self.component.config.enable_animations, False)

        # Should calculate sizes from config
        size = self.component.config.get_calculated_thumbnail_dimension()
        self.assertGreater(size, 0)

        print("✅ Config integration OK")


if __name__ == "__main__":
    print("🧪 TESTING ETAP 3: ThumbnailComponent")
    unittest.main()
