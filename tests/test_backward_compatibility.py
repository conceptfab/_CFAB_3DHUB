"""
ETAP 9: BACKWARD COMPATIBILITY TESTS
Tests dla sprawdzenia czy stare API działa z nowymi komponentami.
"""

import os
import sys
import warnings
from unittest.mock import Mock

# Umieszczenie ścieżki do 'src' na początku, aby moduły były widoczne
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from src.models.file_pair import FilePair
from src.ui.widgets.file_tile_widget import CompatibilityAdapter, FileTileWidget


class TestBackwardCompatibility:
    """Test suite dla backward compatibility."""

    def setup_method(self):
        """Setup przed każdym testem."""
        # Tworzymy prawidłowe ścieżki absolutne dla testów
        base_dir = os.path.abspath(os.path.dirname(__file__))
        archive_path = os.path.join(base_dir, "test_archive.zip")
        preview_path = os.path.join(base_dir, "test_preview.jpg")

        self.mock_file_pair = FilePair(
            archive_path=archive_path,
            preview_path=preview_path,
            working_directory=base_dir,
        )
        # Dodajemy atrybuty, które mogą być używane w teście
        self.mock_file_pair.get_base_name = lambda: "test_file"
        self.mock_file_pair.get_stars = lambda: 3
        self.mock_file_pair.get_color_tag = lambda: "#FF0000"

    def test_file_tile_widget_initialization_with_legacy_params(self, qapp):
        """
        Test: FileTileWidget można zainicjalizować ze starymi parametrami.
        """
        # Legacy style initialization
        tile = FileTileWidget(
            file_pair=self.mock_file_pair,
            default_thumbnail_size=(150, 150),
            parent=None,
        )

        assert tile is not None
        assert tile.file_pair == self.mock_file_pair
        assert tile.thumbnail_size == (150, 150)
        assert hasattr(tile, "_compatibility_adapter")

    def test_compatibility_adapter_initialization(self, qapp):
        """Test: CompatibilityAdapter jest poprawnie zainicjalizowany."""
        tile = FileTileWidget(self.mock_file_pair)

        assert hasattr(tile, "_compatibility_adapter")
        assert isinstance(tile._compatibility_adapter, CompatibilityAdapter)
        assert tile._compatibility_adapter.widget == tile

    def test_legacy_update_data_with_deprecation_warning(self, qapp):
        """Test: update_data() pokazuje deprecation warning."""
        tile = FileTileWidget(None)

        # Test deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            tile.update_data(self.mock_file_pair)

            # Should show deprecation warning
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "update_data() is deprecated" in str(w[0].message)
            assert "set_file_pair" in str(w[0].message)

    def test_legacy_change_thumbnail_size_with_deprecation_warning(self, qapp):
        """Test: change_thumbnail_size() pokazuje deprecation warning."""
        tile = FileTileWidget(None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            tile.change_thumbnail_size(200)

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "change_thumbnail_size() is deprecated" in str(w[0].message)

    def test_legacy_refresh_thumbnail_with_deprecation_warning(self, qapp):
        """Test: refresh_thumbnail() pokazuje deprecation warning."""
        tile = FileTileWidget(None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            tile.refresh_thumbnail()

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "refresh_thumbnail() is deprecated" in str(w[0].message)

    def test_legacy_get_file_data_with_deprecation_warning(self, qapp):
        """Test: get_file_data() pokazuje deprecation warning."""
        tile = FileTileWidget(self.mock_file_pair)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = tile.get_file_data()

            assert result == self.mock_file_pair
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "get_file_data() is deprecated" in str(w[0].message)

    def test_legacy_set_selection_with_deprecation_warning(self, qapp):
        """Test: set_selection() pokazuje deprecation warning."""
        tile = FileTileWidget(None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            tile.set_selection(True)

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "set_selection() is deprecated" in str(w[0].message)

    def test_new_api_methods_no_deprecation_warning(self, qapp):
        """Test: Nowe API metody nie pokazują deprecation warnings."""
        tile = FileTileWidget(None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # New API methods
            tile.set_file_pair(self.mock_file_pair)
            tile.set_thumbnail_size((200, 200))
            tile.reload_thumbnail()
            tile.set_selected(True)

            # No deprecation warnings should be shown
            assert len(w) == 0

    def test_backward_compatibility_getters(self, qapp):
        """Test: Getter methods dla kompatybilności."""
        tile = FileTileWidget(self.mock_file_pair, (150, 150))

        # Test getters
        assert tile.get_thumbnail_size() == (150, 150)
        assert tile.get_file_pair() == self.mock_file_pair
        assert tile.is_tile_selected() is False

    def test_deprecation_warning_shown_only_once(self, qapp):
        """Test: Deprecation warning jest pokazany tylko raz na metodę."""
        tile = FileTileWidget(None)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            # Call same deprecated method multiple times
            tile.get_file_data()
            tile.get_file_data()
            tile.get_file_data()

            # Should show warning only once
            assert len(w) == 1

    def test_legacy_api_delegation_to_new_implementation(self, qapp):
        """Test: Legacy API deleguje do nowej implementacji."""
        tile = FileTileWidget(None)

        # Mock new implementation methods
        tile.set_file_pair = Mock()
        tile.set_thumbnail_size = Mock()
        tile.set_selected = Mock()

        # Call legacy methods (ignore warnings)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            tile.change_thumbnail_size(200)
            tile.set_selection(True)

        # Check that new methods were called
        tile.set_thumbnail_size.assert_called_once_with(200)
        tile.set_selected.assert_called_once_with(True)

    def test_signals_backward_compatibility(self, qapp):
        """Test: Wszystkie sygnały są zachowane dla kompatybilności."""
        tile = FileTileWidget(None)

        # Check that all legacy signals exist
        assert hasattr(tile, "archive_open_requested")
        assert hasattr(tile, "preview_image_requested")
        assert hasattr(tile, "tile_selected")
        assert hasattr(tile, "stars_changed")
        assert hasattr(tile, "color_tag_changed")
        assert hasattr(tile, "tile_context_menu_requested")
        assert hasattr(tile, "file_pair_updated")

    def test_predefined_colors_backward_compatibility(self, qapp):
        """Test: PREDEFINED_COLORS constant jest zachowany."""
        tile = FileTileWidget(None)

        assert hasattr(tile, "PREDEFINED_COLORS")
        assert isinstance(tile.PREDEFINED_COLORS, dict)
        assert len(tile.PREDEFINED_COLORS) > 0

    def test_legacy_methods_basic_functionality(self, qapp):
        """Test: Legacy methods zachowują podstawową funkcjonalność."""
        tile = FileTileWidget(None)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Ignore deprecation warnings

            # Test open_file and preview_image don't crash
            tile.open_file()
            tile.preview_image()
            tile.show_properties()

            # Test get methods return expected types
            size = tile.get_thumbnail_size()
            assert isinstance(size, tuple)
            assert len(size) == 2

            selected = tile.is_tile_selected()
            assert isinstance(selected, bool)


class TestCompatibilityAdapter:
    """Test suite dla CompatibilityAdapter."""

    def setup_method(self):
        """Setup przed każdym testem."""
        self.mock_widget = Mock()
        self.adapter = CompatibilityAdapter(self.mock_widget)

    def test_adapter_initialization(self):
        """Test: CompatibilityAdapter jest poprawnie zainicjalizowany."""
        assert self.adapter.widget == self.mock_widget
        assert hasattr(self.adapter, "_deprecation_warnings_shown")
        assert isinstance(self.adapter._deprecation_warnings_shown, set)

    def test_show_deprecation_warning_basic(self):
        """Test: show_deprecation_warning() generuje warning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            self.adapter.show_deprecation_warning("test_method", "new_method")

            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "test_method() is deprecated" in str(w[0].message)
            assert "new_method()" in str(w[0].message)

    def test_show_deprecation_warning_without_new_method(self):
        """Test: show_deprecation_warning() bez nowej metody."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            self.adapter.show_deprecation_warning("test_method")

            assert len(w) == 1
            assert "test_method() is deprecated" in str(w[0].message)
            assert "Use the new API" in str(w[0].message)

    def test_show_deprecation_warning_only_once_per_method(self):
        """Test: Deprecation warning jest pokazany tylko raz na metodę."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            self.adapter.show_deprecation_warning("test_method_1", "new_1")
            self.adapter.show_deprecation_warning("test_method_1", "new_1")

            assert len(w) == 1

    def test_different_methods_show_different_warnings(self):
        """Test: Różne metody pokazują osobne ostrzeżenia."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            self.adapter.show_deprecation_warning("method_a", "new_a")
            self.adapter.show_deprecation_warning("method_b", "new_b")

            assert len(w) == 2
