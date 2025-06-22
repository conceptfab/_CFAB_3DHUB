"""
UI Manager dla FileTileWidget.

Zarządza wszystkimi operacjami UI setup.
"""

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout

from src.ui.widgets.metadata_controls_widget import MetadataControlsWidget
from src.ui.widgets.tile_styles import (
    TileColorScheme,
    TileSizeConstants,
    TileStylesheet,
)

if TYPE_CHECKING:
    from .file_tile_widget import FileTileWidget


class FileTileWidgetUIManager:
    """Zarządza wszystkimi operacjami UI setup dla FileTileWidget."""

    def __init__(self, widget: "FileTileWidget"):
        self.widget = widget

    def setup_ui(self):
        """Konfiguruje interfejs użytkownika."""
        self.widget.setObjectName("FileTileWidget")
        self.widget.setStyleSheet(TileStylesheet.get_file_tile_stylesheet())
        self.widget.setAutoFillBackground(True)

        palette = self.widget.palette()
        palette.setColor(
            self.widget.backgroundRole(), QColor(TileColorScheme.BACKGROUND)
        )
        self.widget.setPalette(palette)
        self.widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.setup_layout()
        self.create_ui_elements()

    def setup_layout(self):
        """Konfiguruje layout główny."""
        self.widget.layout = QVBoxLayout(self.widget)
        margins = TileSizeConstants.LAYOUT_MARGINS
        self.widget.layout.setContentsMargins(
            margins[0], margins[1], margins[2], margins[3]
        )
        self.widget.layout.setSpacing(TileSizeConstants.LAYOUT_SPACING)

    def create_ui_elements(self):
        """Tworzy UI elementy i łączy je z komponentami."""
        self.create_thumbnail_ui()
        self.create_filename_ui()
        self.create_metadata_ui()

        self.widget.layout.addWidget(
            self.widget.thumbnail_frame, 0, Qt.AlignmentFlag.AlignHCenter
        )
        self.widget.layout.addWidget(self.widget.filename_label)
        self.widget.layout.addWidget(self.widget.metadata_controls)

        if hasattr(self.widget, "_interaction_component"):
            self.widget._interaction_component.set_target_widgets(
                thumbnail_widget=self.widget.thumbnail_label,
                filename_widget=self.widget.filename_label,
            )

    def create_thumbnail_ui(self):
        """Tworzy UI dla miniatur i łączy z thumbnail component."""
        self.widget.thumbnail_frame = QFrame(self.widget)
        self.widget.thumbnail_frame.setStyleSheet(
            TileStylesheet.get_thumbnail_frame_stylesheet()
        )

        thumbnail_frame_layout = QVBoxLayout(self.widget.thumbnail_frame)
        thumbnail_frame_layout.setContentsMargins(0, 0, 0, 0)
        thumbnail_frame_layout.setSpacing(0)

        self.widget.thumbnail_label = QLabel(self.widget)
        self.widget.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.widget.thumbnail_label.setMinimumSize(
            TileSizeConstants.MIN_THUMBNAIL_WIDTH,
            TileSizeConstants.MIN_THUMBNAIL_HEIGHT,
        )

        thumb_size = self._calculate_thumbnail_size()
        self.widget.thumbnail_label.setFixedSize(thumb_size, thumb_size)
        self.widget.thumbnail_label.setScaledContents(True)
        self.widget.thumbnail_label.setFrameShape(QFrame.Shape.NoFrame)
        self.widget.thumbnail_label.setStyleSheet(
            TileStylesheet.get_thumbnail_label_stylesheet()
        )

        thumbnail_frame_layout.addWidget(self.widget.thumbnail_label)
        self._connect_thumbnail_component()

    def create_filename_ui(self):
        """Tworzy UI dla nazwy pliku."""
        self.widget.filename_label = QLabel("Ładowanie...", self.widget)
        self.widget.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.widget.filename_label.setWordWrap(True)
        self.widget.filename_label.setMaximumHeight(
            TileSizeConstants.FILENAME_MAX_HEIGHT
        )
        self.widget.filename_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )

        # Ustawienie stylu CSS z efektem hover
        base_font_size = 12  # domyślny rozmiar
        self.widget.filename_label.setStyleSheet(
            TileStylesheet.get_filename_label_stylesheet(base_font_size)
        )

        self.update_font_size()

    def create_metadata_ui(self):
        """Tworzy UI dla metadanych i łączy z metadata component."""
        self.widget.metadata_controls = MetadataControlsWidget(self.widget)
        self.widget.metadata_controls.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.widget.metadata_controls.setMaximumHeight(
            TileSizeConstants.METADATA_MAX_HEIGHT
        )
        self.widget.metadata_controls.setContentsMargins(0, 0, 0, 0)
        self._connect_metadata_component()

    def _calculate_thumbnail_size(self) -> int:
        """Oblicza optymalny rozmiar miniatury."""
        thumb_size = min(
            self.widget.thumbnail_size[0] - TileSizeConstants.TILE_PADDING * 2,
            self.widget.thumbnail_size[1]
            - TileSizeConstants.FILENAME_MAX_HEIGHT
            - TileSizeConstants.METADATA_MAX_HEIGHT,
        )
        return max(thumb_size, TileSizeConstants.MIN_THUMBNAIL_WIDTH)

    def update_font_size(self):
        """Aktualizuje rozmiar czcionki na podstawie rozmiaru kafelka."""
        base_size = min(self.widget.thumbnail_size)
        if base_size < 120:
            font_size = 8
        elif base_size < 150:
            font_size = 9
        elif base_size < 200:
            font_size = 10
        else:
            font_size = 11

        font = self.widget.filename_label.font()
        font.setPointSize(font_size)
        self.widget.filename_label.setFont(font)

    def _connect_thumbnail_component(self):
        """Podłącza sygnały thumbnail component."""
        if self.widget._thumbnail_component:
            self.widget._thumbnail_component.thumbnail_loaded.connect(
                self.widget._on_thumbnail_component_loaded
            )
            self.widget._thumbnail_component.thumbnail_error.connect(
                self.widget._on_thumbnail_component_error
            )

    def _connect_metadata_component(self):
        """Podłącza sygnały metadata component."""
        self.widget.metadata_controls.tile_selected_changed.connect(
            self.widget._on_tile_selection_changed
        )
        self.widget.metadata_controls.stars_value_changed.connect(
            self.widget._on_metadata_stars_changed
        )
        self.widget.metadata_controls.color_tag_value_changed.connect(
            self.widget._on_metadata_color_changed
        )
