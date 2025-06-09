"""
Testy jednostkowe dla komponentu FileTileWidget.
"""

import os
import sys

import pytest
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QApplication

from src.models.file_pair import FilePair
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.ui.widgets.tile_styles import TileSizeConstants

# Inicjalizacja aplikacji QT niezbędna dla testów
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestFileTileWidget:
    """Testy jednostkowe dla komponentu FileTileWidget."""

    @pytest.fixture
    def mock_file_pair(self, tmp_path):
        """Tworzy atrapy FilePair do testów."""
        archive_path = os.path.join(tmp_path, "test_archive.zip")
        preview_path = os.path.join(tmp_path, "test_preview.jpg")

        # Tworzenie atrap plików
        with open(archive_path, "w") as f:
            f.write("mock archive file")
        with open(preview_path, "w") as f:
            f.write("mock preview file")

        return FilePair(archive_path, preview_path)

    def test_init_with_valid_file_pair(self, mock_file_pair):
        """Test czy widget inicjalizuje się poprawnie z prawidłowym FilePair."""
        widget = FileTileWidget(mock_file_pair)

        assert widget.file_pair == mock_file_pair
        assert widget.filename_label.text() == mock_file_pair.get_base_name()
        assert widget.thumbnail_size == TileSizeConstants.DEFAULT_THUMBNAIL_SIZE

    def test_init_with_none_file_pair(self):
        """Test czy widget inicjalizuje się poprawnie bez FilePair."""
        widget = FileTileWidget(None)

        assert widget.file_pair is None
        assert widget.filename_label.text() == "Brak danych"

    def test_set_thumbnail_size(self, mock_file_pair):
        """Test czy zmiana rozmiaru miniatury działa poprawnie."""
        widget = FileTileWidget(mock_file_pair)
        initial_size = widget.thumbnail_size
        new_size = (200, 200)

        widget.set_thumbnail_size(new_size)

        assert widget.thumbnail_size == new_size
        assert widget.size() == QSize(*new_size)
        assert widget.thumbnail_label.width() <= new_size[0]
        assert widget.thumbnail_label.height() <= new_size[1]

    def test_update_data(self, mock_file_pair):
        """Test aktualizacji danych z nowym FilePair."""
        widget = FileTileWidget(None)  # Inicjalizacja pustym obiektem

        widget.update_data(mock_file_pair)

        assert widget.file_pair == mock_file_pair
        assert widget.filename_label.text() == mock_file_pair.get_base_name()

    def test_update_thumbnail_border_color(self, mock_file_pair):
        """Test aktualizacji koloru obramowania miniatury."""
        widget = FileTileWidget(mock_file_pair)
        color_hex = "#E53935"  # czerwony

        widget._update_thumbnail_border_color(color_hex)

        # Sprawdzenie czy styl zawiera kolor
        assert color_hex in widget.thumbnail_frame.styleSheet()

        # Zmiana na brak koloru
        widget._update_thumbnail_border_color("")
        assert "border: none" in widget.thumbnail_frame.styleSheet()

    def test_signals_connected(self, mock_file_pair):
        """Test czy sygnały są prawidłowo połączone."""
        widget = FileTileWidget(mock_file_pair)

        # Sprawdzenie połączeń sygnałów z MetadataControlsWidget
        assert (
            widget.metadata_controls.tile_selected_changed.receivers(
                widget._on_tile_selection_changed
            )
            == 1
        )
        assert (
            widget.metadata_controls.stars_value_changed.receivers(
                widget._on_stars_changed
            )
            == 1
        )
        assert (
            widget.metadata_controls.color_tag_value_changed.receivers(
                widget._on_color_tag_changed
            )
            == 1
        )
