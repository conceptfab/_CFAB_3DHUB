#!/usr/bin/env python3
"""
TESTY ETAP 2: TileEventBus
"""

import sys
import unittest
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from PyQt6.QtWidgets import QApplication

    from src.ui.widgets.tile_config import TileEvent
    from src.ui.widgets.tile_event_bus import (
        TileEventBus,
        TileEventSubscriber,
        create_event_bus,
        create_subscriber,
    )
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


class TestTileEventBus(unittest.TestCase):
    """Testy dla TileEventBus - ETAP 2 refaktoryzacji"""

    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication([])

    def setUp(self):
        """Setup dla każdego testu"""
        self.event_bus = create_event_bus(enable_debug=True)
        self.received_events = []

    def tearDown(self):
        """Cleanup po teście"""
        self.event_bus.cleanup()

    def test_event_bus_creation(self):
        """Test tworzenia event bus"""
        bus = create_event_bus()
        self.assertIsNotNone(bus)
        self.assertEqual(bus.get_total_subscribers(), 0)
        print("✅ Event bus creation OK")

    def test_subscribe_unsubscribe(self):
        """Test subscribowania i unsubscribowania"""

        def dummy_callback():
            pass

        # Subscribe
        success = self.event_bus.subscribe(TileEvent.THUMBNAIL_LOADED, dummy_callback)
        self.assertTrue(success)
        self.assertEqual(
            self.event_bus.get_subscriber_count(TileEvent.THUMBNAIL_LOADED), 1
        )

        # Unsubscribe
        success = self.event_bus.unsubscribe(TileEvent.THUMBNAIL_LOADED, dummy_callback)
        self.assertTrue(success)
        self.assertEqual(
            self.event_bus.get_subscriber_count(TileEvent.THUMBNAIL_LOADED), 0
        )

        print("✅ Subscribe/unsubscribe OK")

    def test_event_emission(self):
        """Test emitowania eventów"""

        def callback(*args, **kwargs):
            self.received_events.append(("callback", args, kwargs))

        # Subscribe to event
        self.event_bus.subscribe(TileEvent.DATA_UPDATED, callback)

        # Emit event
        test_data = "test_file_pair"
        notified = self.event_bus.emit_event(TileEvent.DATA_UPDATED, test_data)

        # Check results
        self.assertEqual(notified, 1)
        self.assertEqual(len(self.received_events), 1)
        self.assertEqual(self.received_events[0][1][0], test_data)

        print("✅ Event emission OK")

    def test_multiple_subscribers(self):
        """Test wielu subscribers"""

        def callback1(*args):
            self.received_events.append("callback1")

        def callback2(*args):
            self.received_events.append("callback2")

        # Subscribe multiple callbacks
        self.event_bus.subscribe(TileEvent.STATE_CHANGED, callback1)
        self.event_bus.subscribe(TileEvent.STATE_CHANGED, callback2)

        # Emit event
        notified = self.event_bus.emit_event(TileEvent.STATE_CHANGED, "test_state")

        # Check both callbacks were called
        self.assertEqual(notified, 2)
        self.assertIn("callback1", self.received_events)
        self.assertIn("callback2", self.received_events)

        print("✅ Multiple subscribers OK")

    def test_subscriber_helper(self):
        """Test helper class dla subscriptions"""
        subscriber = create_subscriber(self.event_bus)

        def callback(*args):
            self.received_events.append("helper_callback")

        # Subscribe via helper
        success = subscriber.subscribe(TileEvent.USER_INTERACTION, callback)
        self.assertTrue(success)

        # Emit event
        self.event_bus.emit_event(TileEvent.USER_INTERACTION, "click", {})
        self.assertIn("helper_callback", self.received_events)

        # Cleanup via helper
        subscriber.unsubscribe_all()
        self.assertEqual(
            self.event_bus.get_subscriber_count(TileEvent.USER_INTERACTION), 0
        )

        print("✅ Subscriber helper OK")

    def test_debug_info(self):
        """Test informacji debug"""
        debug_info = self.event_bus.get_debug_info()

        required_keys = [
            "total_events_emitted",
            "total_subscribers",
            "subscriber_counts",
        ]

        for key in required_keys:
            self.assertIn(key, debug_info)

        print(f"✅ Debug info: {debug_info}")

    def test_cleanup(self):
        """Test cleanup event bus"""

        def dummy_callback():
            pass

        # Add some subscribers
        self.event_bus.subscribe(TileEvent.THUMBNAIL_LOADED, dummy_callback)
        self.event_bus.subscribe(TileEvent.DATA_UPDATED, dummy_callback)

        # Verify subscribers exist
        self.assertGreater(self.event_bus.get_total_subscribers(), 0)

        # Cleanup
        self.event_bus.cleanup()

        # Verify cleanup
        self.assertEqual(self.event_bus.get_total_subscribers(), 0)

        print("✅ Cleanup OK")


if __name__ == "__main__":
    print("🧪 TESTING ETAP 2: TileEventBus")
    unittest.main()
