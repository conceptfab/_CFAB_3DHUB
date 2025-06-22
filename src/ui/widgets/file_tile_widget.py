"""
Kafelek wyświetlający miniaturę podglądu, nazwę i rozmiar pliku archiwum.
Zrefaktoryzowany z simplified architecture - eliminacja over-engineering.

ETAP 5: SIMPLIFIED ARCHITECTURE
- Konsolidacja komponentów do głównej klasy
- TileState pattern zamiast over-engineered komponentów
- Pooling pattern dla resource management
- Batch UI updates
"""

# Standard library imports
import logging
import threading
import warnings
import weakref
from typing import Optional, Tuple

# Third-party imports
from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget

# Local imports
from src.models.file_pair import FilePair
from src.ui.widgets.metadata_controls_widget import MetadataControlsWidget
from src.ui.widgets.thumbnail_cache import ThumbnailCache

# Import simplified architecture
from src.ui.widgets.tile_config import TileConfig
from src.ui.widgets.tile_styles import (
    TileColorScheme,
    TileSizeConstants,
    TileStylesheet,
)

logger = logging.getLogger(__name__)


class TileState:
    """Lightweight state container dla kafelka."""

    __slots__ = [
        "file_pair",
        "size",
        "selected",
        "stars",
        "color_tag",
        "thumbnail_loaded",
    ]

    def __init__(self, file_pair: Optional[FilePair], size: Tuple[int, int]):
        self.file_pair = file_pair
        self.size = size
        self.selected = False
        self.stars = file_pair.get_stars() if file_pair else 0
        self.color_tag = file_pair.get_color_tag() if file_pair else ""
        self.thumbnail_loaded = False

    def update_from_file_pair(self, file_pair: Optional[FilePair]):
        """Aktualizuje state z file_pair."""
        self.file_pair = file_pair
        if file_pair:
            self.stars = file_pair.get_stars()
            self.color_tag = file_pair.get_color_tag()
        else:
            self.stars = 0
            self.color_tag = ""


class TileResourcePool:
    """Centralized resource management z pooling pattern."""

    _active_tiles = weakref.WeakSet()
    _thumbnail_cache = {}
    _max_active_tiles = 3000
    _lock = threading.RLock()

    @classmethod
    def register(cls, tile):
        """Register tile z automatic cleanup."""
        with cls._lock:
            if len(cls._active_tiles) >= cls._max_active_tiles:
                cls._cleanup_oldest()
            cls._active_tiles.add(tile)
            return True

    @classmethod
    def unregister(cls, tile):
        """Unregister tile."""
        with cls._lock:
            cls._active_tiles.discard(tile)

    @classmethod
    def _cleanup_oldest(cls):
        """LRU cleanup gdy pool jest pełny."""
        # Simple cleanup - remove oldest tiles
        tiles_list = list(cls._active_tiles)
        if tiles_list:
            # WeakSet order is not guaranteed, but simple approach
            oldest_tile = tiles_list[0]
            cls._active_tiles.discard(oldest_tile)

    @classmethod
    def get_thumbnail(cls, path: str, size: Tuple[int, int]) -> Optional[QPixmap]:
        """Centralized thumbnail caching."""
        cache_key = f"{path}:{size}"
        if cache_key not in cls._thumbnail_cache:
            try:
                # Load thumbnail using existing cache
                thumbnail_cache = ThumbnailCache.get_instance()
                cls._thumbnail_cache[cache_key] = thumbnail_cache.get_thumbnail(
                    path, size
                )
            except Exception as e:
                logger.warning(f"Failed to load thumbnail {path}: {e}")
                return None
        return cls._thumbnail_cache[cache_key]


class LegacyAPIBridge:
    """Minimal legacy support bez overhead."""

    def __init__(self, widget):
        self.widget = widget
        self._warning_shown = set()

    def show_deprecation_warning(
        self, old_method_name: str, new_method_name: str = None
    ):
        """Pokazuje ostrzeżenie o przestarzałej metodzie tylko raz."""
        if old_method_name in self._warning_shown:
            return

        if new_method_name:
            message = (
                f"{self.widget.__class__.__name__}.{old_method_name}() is deprecated. "
                f"Use {new_method_name}() instead."
            )
        else:
            message = (
                f"{self.widget.__class__.__name__}.{old_method_name}() is deprecated. "
                f"Use the new API."
            )

        warnings.warn(message, DeprecationWarning, stacklevel=3)
        self._warning_shown.add(old_method_name)

    def update_data(self, file_pair):
        """Legacy method z single warning."""
        self.show_deprecation_warning("update_data", "set_file_pair")
        self.widget.set_file_pair(file_pair)

    def change_thumbnail_size(self, size):
        """Legacy method z single warning."""
        self.show_deprecation_warning("change_thumbnail_size", "set_thumbnail_size")
        self.widget.set_thumbnail_size(size)

    def refresh_thumbnail(self):
        """Legacy method z single warning."""
        self.show_deprecation_warning("refresh_thumbnail", "reload_thumbnail")
        self.widget.reload_thumbnail()

    def get_file_data(self):
        """Legacy method z single warning."""
        self.show_deprecation_warning("get_file_data", "file_pair property")
        return self.widget.file_pair

    def set_selection(self, selected):
        """Legacy method z single warning."""
        self.show_deprecation_warning("set_selection", "set_selected")
        self.widget.set_selected(selected)


class FileTileWidget(QWidget):
    """
    Simplified widget kafelka pary plików.

    Nowa architektura:
    - TileState: Lightweight state container
    - TileResourcePool: Centralized resource management
    - Batch UI updates: Single-pass updates
    - Minimal legacy API: Graceful migration
    """

    # Sygnały dla kompatybilności wstecznej
    archive_open_requested = pyqtSignal(FilePair)
    preview_image_requested = pyqtSignal(FilePair)
    tile_selected = pyqtSignal(FilePair, bool)
    stars_changed = pyqtSignal(FilePair, int)
    color_tag_changed = pyqtSignal(FilePair, str)
    tile_context_menu_requested = pyqtSignal(FilePair, QWidget, object)
    file_pair_updated = pyqtSignal(FilePair)

    # Predefiniowane kolory dla kompatybilności
    PREDEFINED_COLORS = TileColorScheme.PREDEFINED_COLOR_TAGS

    def __init__(
        self,
        file_pair: Optional[FilePair],
        default_thumbnail_size: tuple[
            int, int
        ] = TileSizeConstants.DEFAULT_THUMBNAIL_SIZE,
        parent: Optional[QWidget] = None,
    ):
        """
        Inicjalizuje widget kafelka z simplified architecture.

        Args:
            file_pair: Obiekt pary plików lub None.
            default_thumbnail_size: Rozmiar całego kafelka (szer., wys.) w px.
            parent: Widget nadrzędny lub None.
        """
        super().__init__(parent)

        # Lightweight state object
        self._state = TileState(file_pair, default_thumbnail_size)

        # Podstawowe właściwości
        self.file_pair = file_pair
        self.thumbnail_size = default_thumbnail_size
        self.is_selected = False
        self._is_cleanup_done = False
        self._cleanup_lock = threading.RLock()
        self._cleanup_in_progress = False

        # Resource management - pooling pattern
        self._is_registered = TileResourcePool.register(self)
        if not self._is_registered:
            logger.warning(
                "Failed to register tile in resource pool - tile limit reached"
            )

        # Legacy API bridge
        self._legacy_bridge = LegacyAPIBridge(self)

        # Konfiguracja
        self._config = TileConfig(thumbnail_size=default_thumbnail_size)

        # Setup minimal UI
        self._setup_minimal_ui()

        # Connect signals
        self._connect_signals()

        # Install event filters
        self._install_event_filters()

        # Initial UI update
        if file_pair:
            self._update_ui_batch()

    def _setup_minimal_ui(self):
        """Setup minimal UI elements."""
        # Main layout
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(2, 2, 2, 2)
        self.layout().setSpacing(2)

        # Thumbnail frame
        self.thumbnail_frame = QFrame()
        self.thumbnail_frame.setFrameStyle(QFrame.Shape.Box)
        self.thumbnail_frame.setLineWidth(2)
        self.thumbnail_frame.setStyleSheet(
            TileStylesheet.get_thumbnail_frame_stylesheet("")
        )

        # Thumbnail label
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.thumbnail_label.setMinimumSize(80, 80)
        self.thumbnail_label.setText("?")

        # Filename label
        self.filename_label = QLabel()
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filename_label.setWordWrap(True)
        self.filename_label.setStyleSheet(
            TileStylesheet.get_filename_label_stylesheet(12)
        )

        # Metadata controls
        self.metadata_controls = MetadataControlsWidget()
        self.metadata_controls.setEnabled(False)

        # Layout setup
        self.thumbnail_frame.setLayout(QVBoxLayout())
        self.thumbnail_frame.layout().addWidget(self.thumbnail_label)

        self.layout().addWidget(self.thumbnail_frame)
        self.layout().addWidget(self.filename_label)
        self.layout().addWidget(self.metadata_controls)

        # Set fixed size
        self.setFixedSize(self.thumbnail_size[0], self.thumbnail_size[1])

    def _connect_signals(self):
        """Connect signals dla simplified architecture."""
        # Metadata controls signals
        if hasattr(self.metadata_controls, "stars_changed"):
            self.metadata_controls.stars_changed.connect(self._on_stars_changed)
        if hasattr(self.metadata_controls, "color_tag_changed"):
            self.metadata_controls.color_tag_changed.connect(self._on_color_tag_changed)

    def _install_event_filters(self):
        """Install event filters dla thumbnail i filename labels."""
        self.thumbnail_label.installEventFilter(self)
        self.filename_label.installEventFilter(self)

    def _update_ui_batch(self):
        """Single-pass UI update żeby zapobiec flickering."""
        if not self._state.file_pair:
            self._reset_ui()
            return

        # Collect all updates
        updates = {
            "filename": self._state.file_pair.get_base_name(),
            "stars": self._state.stars,
            "color_tag": self._state.color_tag,
            "enabled": True,
        }

        # Apply all updates in single repaint
        self.setUpdatesEnabled(False)
        self._apply_ui_updates(updates)
        self.setUpdatesEnabled(True)

    def _apply_ui_updates(self, updates: dict):
        """Apply multiple UI updates efficiently."""
        if "filename" in updates:
            self.filename_label.setText(updates["filename"])

        if "enabled" in updates:
            self.metadata_controls.setEnabled(updates["enabled"])
            if updates["enabled"]:
                self.metadata_controls.set_file_pair(self._state.file_pair)

        if "stars" in updates:
            self.metadata_controls.update_stars_display(updates["stars"])

        if "color_tag" in updates:
            self.metadata_controls.update_color_tag_display(updates["color_tag"])
            self._update_thumbnail_border_color(updates["color_tag"])

    def _reset_ui(self):
        """Reset UI state dla None file_pair."""
        self.filename_label.setText("Brak danych")
        self.thumbnail_label.clear()
        self.thumbnail_label.setText("?")
        self.metadata_controls.set_file_pair(None)
        self.metadata_controls.setEnabled(False)
        self._update_thumbnail_border_color("")

    def _update_thumbnail_border_color(self, color_hex: str):
        """Aktualizuje kolor obwódki wokół miniatury."""
        self.thumbnail_frame.setStyleSheet(
            TileStylesheet.get_thumbnail_frame_stylesheet(color_hex)
        )

    def _on_stars_changed(self, stars: int):
        """Callback dla zmian gwiazdek."""
        self._state.stars = stars
        if self.file_pair:
            self.stars_changed.emit(self.file_pair, stars)
            self.file_pair_updated.emit(self.file_pair)

    def _on_color_tag_changed(self, color_hex: str):
        """Callback dla zmian kolorów."""
        self._state.color_tag = color_hex
        self._update_thumbnail_border_color(color_hex)
        if self.file_pair:
            self.color_tag_changed.emit(self.file_pair, color_hex)
            self.file_pair_updated.emit(self.file_pair)

    def _on_thumbnail_loaded(self, pixmap, path, width, height):
        """Obsługuje załadowaną miniaturę - dla TileManager."""
        if pixmap and not pixmap.isNull():
            self.thumbnail_label.setPixmap(pixmap)
            self._state.thumbnail_loaded = True

            if self.file_pair:
                color_tag = self.file_pair.get_color_tag()
                if color_tag and color_tag.strip():
                    self._update_thumbnail_border_color(color_tag)
        else:
            self.thumbnail_label.setText("Błąd ładowania")
            self._state.thumbnail_loaded = False

    def eventFilter(self, obj, event):
        """Obsługuje zdarzenia na etykietach miniatury i nazwy."""
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                if obj == self.thumbnail_label and self.file_pair:
                    self.preview_image_requested.emit(self.file_pair)
                    return True
                elif obj == self.filename_label and self.file_pair:
                    self.archive_open_requested.emit(self.file_pair)
                    return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        """Obsługuje kliknięcie myszy."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_selected(True)
            if self.file_pair:
                self.tile_selected.emit(self.file_pair, True)
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        """Obsługuje menu kontekstowe."""
        if self.file_pair:
            self.tile_context_menu_requested.emit(self.file_pair, self, event)
        else:
            super().contextMenuEvent(event)

    # === PUBLIC API ===

    def set_file_pair(self, file_pair: Optional[FilePair]):
        """Ustawia nowy file_pair i aktualizuje UI."""
        self.file_pair = file_pair
        self._state.update_from_file_pair(file_pair)

        if file_pair and file_pair.preview_path:
            self._load_thumbnail(file_pair.preview_path)

        self._update_ui_batch()

    def set_thumbnail_size(self, new_size):
        """Ustawia nowy rozmiar miniatur."""
        if isinstance(new_size, int):
            new_size = (new_size, new_size)

        self.thumbnail_size = new_size
        self._state.size = new_size
        self.setFixedSize(new_size[0], new_size[1])

        # Update font size
        self._update_font_size()

        # Reload thumbnail if needed
        if self.file_pair and self.file_pair.preview_path:
            self._load_thumbnail(self.file_pair.preview_path)

    def set_selected(self, selected: bool):
        """Ustawia status selekcji kafelka."""
        self.is_selected = self._state.selected = selected
        if self.file_pair:
            self.tile_selected.emit(self.file_pair, selected)

    def reload_thumbnail(self):
        """Odświeża miniaturę."""
        if self.file_pair and self.file_pair.preview_path:
            self._load_thumbnail(self.file_pair.preview_path)

    def _load_thumbnail(self, path: str):
        """Load thumbnail z cache."""
        try:
            thumbnail = TileResourcePool.get_thumbnail(path, self.thumbnail_size)
            if thumbnail and not thumbnail.isNull():
                self.thumbnail_label.setPixmap(thumbnail)
                self._state.thumbnail_loaded = True
            else:
                self.thumbnail_label.setText("Błąd")
                self._state.thumbnail_loaded = False
        except Exception as e:
            logger.warning(f"Failed to load thumbnail {path}: {e}")
            self.thumbnail_label.setText("Błąd")
            self._state.thumbnail_loaded = False

    def _update_font_size(self):
        """Aktualizuje rozmiar czcionki w zależności od rozmiaru kafelka."""
        width = self.thumbnail_size[0]
        base_font_size = max(8, min(18, int(width / 12)))
        self.filename_label.setStyleSheet(
            TileStylesheet.get_filename_label_stylesheet(base_font_size)
        )

    # === LEGACY API COMPATIBILITY ===

    def update_data(self, file_pair: Optional[FilePair]):
        """LEGACY API: Aktualizuje dane kafelka."""
        return self._legacy_bridge.update_data(file_pair)

    def change_thumbnail_size(self, size):
        """LEGACY API: Zmienia rozmiar miniatur."""
        return self._legacy_bridge.change_thumbnail_size(size)

    def refresh_thumbnail(self):
        """LEGACY API: Odświeża miniaturę."""
        return self._legacy_bridge.refresh_thumbnail()

    def get_file_data(self):
        """LEGACY API: Pobiera dane pliku."""
        return self._legacy_bridge.get_file_data()

    def set_selection(self, selected: bool):
        """LEGACY API: Ustawia status selekcji."""
        return self._legacy_bridge.set_selection(selected)

    # === Getters dla kompatybilności ===

    def get_thumbnail_size(self) -> Tuple[int, int]:
        """Zwraca aktualny rozmiar miniatur."""
        return self.thumbnail_size

    def get_file_pair(self) -> Optional[FilePair]:
        """Zwraca obiekt FilePair."""
        return self.file_pair

    def is_tile_selected(self) -> bool:
        """Sprawdza czy kafelek jest zaznaczony."""
        return self.is_selected

    # === LEGACY METHODS DLA KOMPATYBILNOŚCI ===

    def open_file(self):
        """KOMPATYBILNOŚĆ: Otwiera plik archiwum."""
        if self.file_pair:
            self.archive_open_requested.emit(self.file_pair)

    def preview_image(self):
        """KOMPATYBILNOŚĆ: Podgląd obrazu."""
        if self.file_pair:
            self.preview_image_requested.emit(self.file_pair)

    def show_properties(self):
        """KOMPATYBILNOŚĆ: Pokazuje właściwości pliku."""
        logging.info(
            "FileTileWidget: Właściwości pliku - funkcjonalność do implementacji"
        )

    # === Cleanup ===

    def cleanup(self):
        """Cleanup resources."""
        with self._cleanup_lock:
            if self._cleanup_in_progress:
                return
            self._cleanup_in_progress = True

        try:
            # Unregister from resource pool
            TileResourcePool.unregister(self)

            # Clear references
            self.file_pair = None
            self._state = None

            self._is_cleanup_done = True

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        finally:
            self._cleanup_in_progress = False

    def __del__(self):
        """Destructor z cleanup."""
        if not self._is_cleanup_done:
            self.cleanup()
