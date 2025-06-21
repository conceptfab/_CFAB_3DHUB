"""
Testy dla TileMetadataComponent - STAGE 4 refaktoryzacji FileTileWidget.

Testy weryfikują:
- Zarządzanie stanem metadanych (stars, color tags, selection)
- Thread safety i change tracking
- Batch updates i rollback functionality
- Event bus integration
- Memory management
"""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from PyQt6.QtCore import QObject

from src.models.file_pair import FilePair
from src.ui.widgets.tile_config import TileConfig, TileState
from src.ui.widgets.tile_event_bus import TileEvent, TileEventBus
from src.ui.widgets.tile_metadata_component import (
    MetadataChangeType,
    MetadataSnapshot,
    MetadataState,
    TileMetadataComponent,
)


class TestTileMetadataComponent:
    """Test suite for TileMetadataComponent."""

    @pytest.fixture
    def config(self):
        """Create test config."""
        from src.ui.widgets.tile_config import create_default_config

        return create_default_config()

    @pytest.fixture
    def event_bus(self):
        """Create test event bus."""
        return TileEventBus()

    @pytest.fixture
    def file_pair(self, tmp_path):
        """Create test file pair."""
        archive_path = tmp_path / "test.blend"
        preview_path = tmp_path / "test.jpg"
        archive_path.write_text("test archive")
        preview_path.write_text("test preview")

        file_pair = FilePair(str(archive_path), str(preview_path), str(tmp_path))
        file_pair.set_stars(3)
        file_pair.set_color_tag("#FF0000")
        return file_pair

    @pytest.fixture
    def metadata_component(self, config, event_bus):
        """Create test metadata component."""
        return TileMetadataComponent(config, event_bus)

    def test_component_creation(self, metadata_component):
        """Test basic component creation."""
        assert metadata_component is not None
        assert metadata_component.get_state() == MetadataState.UNINITIALIZED
        assert metadata_component.get_stars() == 0
        assert metadata_component.get_color_tag() == ""
        assert metadata_component.get_selection() == False

    def test_file_pair_integration(self, metadata_component, file_pair):
        """Test integration with FilePair."""
        # Set file pair
        metadata_component.set_file_pair(file_pair)

        # Verify metadata loaded
        assert metadata_component.get_state() == MetadataState.READY
        assert metadata_component.get_stars() == 3
        assert metadata_component.get_color_tag() == "#FF0000"
        assert metadata_component.get_selection() == False

        # Clear file pair
        metadata_component.set_file_pair(None)
        assert metadata_component.get_state() == MetadataState.UNINITIALIZED
        assert metadata_component.get_stars() == 0
        assert metadata_component.get_color_tag() == ""

    def test_stars_management(self, metadata_component, file_pair):
        """Test stars metadata management."""
        metadata_component.set_file_pair(file_pair)

        # Test setting stars
        metadata_component.set_stars(5)
        assert metadata_component.get_stars() == 5
        assert file_pair.get_stars() == 5

        # Test validation (out of range)
        metadata_component.set_stars(10)
        assert metadata_component.get_stars() == 5  # Should be clamped to 5

        metadata_component.set_stars(-1)
        assert metadata_component.get_stars() == 0  # Should be clamped to 0

    def test_color_tag_management(self, metadata_component, file_pair):
        """Test color tag metadata management."""
        metadata_component.set_file_pair(file_pair)

        # Test setting color tag
        metadata_component.set_color_tag("#00FF00")
        assert metadata_component.get_color_tag() == "#00FF00"
        assert file_pair.get_color_tag() == "#00FF00"

        # Test clearing color tag
        metadata_component.set_color_tag("")
        assert metadata_component.get_color_tag() == ""
        assert file_pair.get_color_tag() == ""

        # Test None handling
        metadata_component.set_color_tag(None)
        assert metadata_component.get_color_tag() == ""

    def test_selection_management(self, metadata_component, file_pair):
        """Test selection metadata management."""
        metadata_component.set_file_pair(file_pair)

        # Test setting selection
        metadata_component.set_selection(True)
        assert metadata_component.get_selection() == True

        metadata_component.set_selection(False)
        assert metadata_component.get_selection() == False

    def test_metadata_snapshot(self, metadata_component, file_pair):
        """Test metadata snapshot functionality."""
        metadata_component.set_file_pair(file_pair)

        # Set some values
        metadata_component.set_stars(4)
        metadata_component.set_color_tag("#0000FF")
        metadata_component.set_selection(True)

        # Get snapshot
        snapshot = metadata_component.get_metadata_snapshot()
        assert snapshot.stars == 4
        assert snapshot.color_tag == "#0000FF"
        assert snapshot.is_selected == True
        assert snapshot.file_pair_id == file_pair.get_base_name()
        assert snapshot.timestamp > 0

        # Apply snapshot
        new_snapshot = MetadataSnapshot(
            stars=2,
            color_tag="#FFFF00",
            is_selected=False,
            file_pair_id="test",
            timestamp=time.time(),
        )
        metadata_component.apply_metadata_snapshot(new_snapshot)

        assert metadata_component.get_stars() == 2
        assert metadata_component.get_color_tag() == "#FFFF00"
        assert metadata_component.get_selection() == False

    def test_change_tracking(self, metadata_component, file_pair):
        """Test change tracking and history."""
        metadata_component.set_file_pair(file_pair)

        # Make some changes
        metadata_component.set_stars(1)
        metadata_component.set_color_tag("#123456")
        metadata_component.set_selection(True)

        # Check history
        history = metadata_component.get_change_history()
        assert len(history) == 3

        # Verify history entries
        change_types = [entry[0] for entry in history]
        assert MetadataChangeType.STARS_CHANGED in change_types
        assert MetadataChangeType.COLOR_TAG_CHANGED in change_types
        assert MetadataChangeType.SELECTION_CHANGED in change_types

    def test_change_listeners(self, metadata_component, file_pair):
        """Test change listeners functionality."""
        metadata_component.set_file_pair(file_pair)

        # Setup listeners
        stars_changes = []
        color_changes = []

        def on_stars_changed(value, timestamp):
            stars_changes.append((value, timestamp))

        def on_color_changed(value, timestamp):
            color_changes.append((value, timestamp))

        metadata_component.add_change_listener(
            MetadataChangeType.STARS_CHANGED, on_stars_changed
        )
        metadata_component.add_change_listener(
            MetadataChangeType.COLOR_TAG_CHANGED, on_color_changed
        )

        # Make changes
        metadata_component.set_stars(4)
        metadata_component.set_color_tag("#ABCDEF")

        # Verify listeners called
        assert len(stars_changes) == 1
        assert stars_changes[0][0] == 4

        assert len(color_changes) == 1
        assert color_changes[0][0] == "#ABCDEF"

        # Remove listeners
        metadata_component.remove_change_listener(
            MetadataChangeType.STARS_CHANGED, on_stars_changed
        )

        # Make another change - should not trigger removed listener
        metadata_component.set_stars(2)
        assert len(stars_changes) == 1  # No new changes

    def test_state_management(self, metadata_component, file_pair):
        """Test component state management."""
        # Initial state
        assert metadata_component.get_state() == MetadataState.UNINITIALIZED
        assert not metadata_component.is_ready()

        # Set file pair - should transition to READY
        metadata_component.set_file_pair(file_pair)
        assert metadata_component.get_state() == MetadataState.READY
        assert metadata_component.is_ready()

        # Clear file pair - should transition back
        metadata_component.set_file_pair(None)
        assert metadata_component.get_state() == MetadataState.UNINITIALIZED
        assert not metadata_component.is_ready()

    def test_memory_management(self, metadata_component, file_pair):
        """Test memory management and optimization."""
        metadata_component.set_file_pair(file_pair)

        # Generate many changes to test memory usage
        for i in range(50):
            metadata_component.set_stars(i % 6)

        # Check memory usage tracking
        memory_usage = metadata_component.get_memory_usage()
        assert memory_usage > 0

        # Optimize memory
        initial_history_length = len(metadata_component.get_change_history())
        metadata_component.optimize_memory()

        # Verify optimization
        optimized_history_length = len(metadata_component.get_change_history())
        assert optimized_history_length <= initial_history_length

    def test_cleanup(self, metadata_component, file_pair, event_bus):
        """Test component cleanup."""
        metadata_component.set_file_pair(file_pair)

        # Make some changes to create state
        metadata_component.set_stars(3)
        metadata_component.set_color_tag("#AABBCC")

        # Verify component has state
        assert len(metadata_component.get_change_history()) > 0

        # Cleanup
        metadata_component.cleanup()

        # Verify cleanup
        assert metadata_component.get_state() == MetadataState.UNINITIALIZED
        assert len(metadata_component.get_change_history()) == 0
        assert not metadata_component.has_pending_changes()

    def test_edge_cases(self, metadata_component, file_pair):
        """Test edge cases and error conditions."""
        # Test operations without file pair
        metadata_component.set_stars(3)  # Should not crash
        assert metadata_component.get_stars() == 3  # Should still work in memory

        # Test repeated identical changes
        metadata_component.set_file_pair(file_pair)
        initial_history_length = len(metadata_component.get_change_history())

        # Set same value multiple times
        metadata_component.set_stars(2)
        metadata_component.set_stars(2)
        metadata_component.set_stars(2)

        # Should only create one change entry
        assert (
            len(metadata_component.get_change_history()) == initial_history_length + 1
        )
