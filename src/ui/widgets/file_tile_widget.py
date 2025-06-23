"""
Kafelek wyświetlający miniaturę podglądu, nazwę i rozmiar pliku archiwum.
Zrefaktoryzowany jako controller integrujący komponenty.

ETAP 9: BACKWARD COMPATIBILITY
Zachowanie 100% kompatybilności API z legacy code.
"""

# Standard library imports
import logging
import threading
import warnings
from typing import Optional, Tuple

# Third-party imports
from PyQt6.QtCore import QEvent, QPoint, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QColor,
    QDesktopServices,
    QDrag,
    QFont,
    QPainter,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Local imports
from src.models.file_pair import FilePair
from src.ui.widgets.metadata_controls_widget import MetadataControlsWidget
from src.ui.widgets.thumbnail_cache import ThumbnailCache

# Import new component architecture
from src.ui.widgets.tile_config import TileConfig, TileEvent
from src.ui.widgets.tile_event_bus import TileEventBus
from src.ui.widgets.tile_interaction_component import TileInteractionComponent
from src.ui.widgets.tile_metadata_component import TileMetadataComponent
from src.ui.widgets.tile_resource_manager import (
    get_resource_manager,
    with_resource_management,
)
from src.ui.widgets.tile_styles import (
    TileColorScheme,
    TileSizeConstants,
    TileStylesheet,
)
from src.ui.widgets.tile_thumbnail_component import ThumbnailComponent

from .file_tile_widget_cleanup import FileTileWidgetCleanupManager
from .file_tile_widget_compatibility import CompatibilityAdapter
from .file_tile_widget_events import FileTileWidgetEventManager
from .file_tile_widget_performance import get_performance_metric
from .file_tile_widget_thumbnail import ThumbnailOperations
from .file_tile_widget_ui_manager import FileTileWidgetUIManager

logger = logging.getLogger(__name__)


class CompatibilityAdapter:
    """Adapter dla zachowania kompatybilności wstecznej."""

    def __init__(self, widget):
        self.widget = widget
        self._deprecation_warnings_shown = set()

    def show_deprecation_warning(self, old_method_name, new_method_name=None):
        """Pokazuje ostrzeżenie o przestarzałej metodzie."""
        if old_method_name in self._deprecation_warnings_shown:
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
        self._deprecation_warnings_shown.add(old_method_name)

    def update_data_legacy(self, file_pair):
        self.show_deprecation_warning("update_data", "set_file_pair")
        self.widget.set_file_pair(file_pair)

    def change_thumbnail_size_legacy(self, size):
        self.show_deprecation_warning("change_thumbnail_size", "set_thumbnail_size")
        self.widget.set_thumbnail_size(size)

    def refresh_thumbnail_legacy(self):
        self.show_deprecation_warning("refresh_thumbnail", "reload_thumbnail")
        self.widget.reload_thumbnail()

    def get_file_data_legacy(self):
        self.show_deprecation_warning("get_file_data", "file_pair property")
        return self.widget.file_pair

    def set_selection_legacy(self, selected):
        self.show_deprecation_warning("set_selection", "set_selected")
        self.widget.set_selected(selected)


class FileTileWidget(QWidget):
    """
    Controller widget dla kafelka pary plików.

    Nowa architektura komponentowa:
    - TileThumbnailComponent: zarządzanie miniaturami
    - TileMetadataComponent: zarządzanie metadanymi (gwiazdki, tagi)
    - TileInteractionComponent: obsługa interakcji użytkownika
    - TileEventBus: komunikacja między komponentami
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
        skip_resource_registration: bool = False,
    ):
        """
        Inicjalizuje widget kafelka jako controller komponentów.

        Args:
            file_pair: Obiekt pary plików lub None.
            default_thumbnail_size: Rozmiar całego kafelka (szer., wys.) w px.
            parent: Widget nadrzędny lub None.
            skip_resource_registration: Czy pominąć rejestrację w TileResourceManager.
        """
        super().__init__(parent)

        # Flaga do sprawdzania czy widget został zniszczony
        self._is_destroyed = False

        # Resource management registration
        self._resource_manager = get_resource_manager()
        logging.debug(
            f"FileTileWidget: skip_resource_registration={skip_resource_registration}"
        )
        self._is_registered = (
            self._resource_manager.register_tile(self)
            if not skip_resource_registration
            else False
        )
        if not self._is_registered and not skip_resource_registration:
            logger.warning(
                "Failed to register tile in resource manager - tile limit reached"
            )

        # Podstawowe właściwości
        self.file_pair = file_pair
        self.thumbnail_size = default_thumbnail_size
        self.is_selected = False
        self._is_cleanup_done = False
        self._cleanup_lock = threading.RLock()  # Thread-safe cleanup
        self._cleanup_in_progress = False

        # ETAP 2: Enhanced event tracking dla memory leak prevention
        self._event_subscriptions = []  # Track event bus subscriptions
        self._signal_connections = []  # Track Qt signal connections
        self._event_filters = []  # Track installed event filters

        # Konfiguracja komponentu
        self._config = TileConfig()
        self._config.thumbnail_size = default_thumbnail_size

        # Inicjalizacja komponentów FIRST
        self._initialize_components()

        # ETAP 5: Inicjalizacja WSZYSTKICH wydzielonych modułów - PRZED setup_ui()!
        self._compatibility_adapter = CompatibilityAdapter(self)
        self._thumbnail_ops = ThumbnailOperations(self)
        self._ui_manager = FileTileWidgetUIManager(self)
        self._event_manager = FileTileWidgetEventManager(self)
        self._cleanup_manager = FileTileWidgetCleanupManager(self)

        # ETAP 8: Performance optimization integration
        self._setup_performance_optimization()

        # Konfiguracja UI - AFTER managers are ready
        self._setup_ui()

        # Połączenie sygnałów - AFTER UI is created
        self._connect_signals()

        # Instalacja event filters
        self._install_event_filters()

        # Aktualizacja danych
        if file_pair:
            self.update_data(file_pair)

        logger.debug(
            f"FileTileWidget initialized (resource managed: {self._is_registered})"
        )

    def _initialize_components(self):
        """Inicjalizuje wszystkie komponenty."""
        # Event bus dla komunikacji między komponentami
        self._event_bus = TileEventBus()

        # Komponent miniatur
        self._thumbnail_component = ThumbnailComponent(
            config=self._config, event_bus=self._event_bus, parent=self
        )
        if self._is_registered:
            self._resource_manager.register_component(
                "thumbnail", self._thumbnail_component
            )

        # Komponent metadanych
        self._metadata_component = TileMetadataComponent(
            config=self._config, event_bus=self._event_bus
        )
        if self._is_registered:
            self._resource_manager.register_component(
                "metadata", self._metadata_component
            )

        # Komponent interakcji
        self._interaction_component = TileInteractionComponent(
            config=self._config, event_bus=self._event_bus, parent_widget=self
        )
        if self._is_registered:
            self._resource_manager.register_component(
                "interaction", self._interaction_component
            )

    def _setup_performance_optimization(self):
        """Setup performance optimization."""
        try:
            if self._resource_manager:
                self._performance_monitor = (
                    self._resource_manager.get_performance_monitor()
                )
                self._cache_optimizer = self._resource_manager.get_cache_optimizer()
                self._async_ui_manager = self._resource_manager.get_async_ui_manager()

                if self._cache_optimizer:
                    self._cache_optimizer.register_cache_user(self)
            else:
                self._performance_monitor = None
                self._cache_optimizer = None
                self._async_ui_manager = None

        except Exception as e:
            logger.warning(f"Failed to setup performance optimization: {e}")
            self._performance_monitor = None
            self._cache_optimizer = None
            self._async_ui_manager = None

    def _setup_ui(self):
        """UI setup delegate to UI manager."""
        self._ui_manager.setup_ui()

    def _on_thumbnail_component_loaded(self, path: str, pixmap: QPixmap):
        """Callback gdy thumbnail component załadował miniaturę."""
        # Sprawdź czy widget nie został zniszczony
        if self._is_destroyed:
            return
        # Sprawdź czy widget jeszcze istnieje
        if not hasattr(self, "thumbnail_label") or self.thumbnail_label is None:
            return
        if pixmap and not pixmap.isNull():
            self.thumbnail_label.setPixmap(pixmap)

    def _on_thumbnail_loaded(self, pixmap, path, width, height):
        """Obsługuje załadowaną miniaturę - dla TileManager."""
        # Sprawdź czy widget nie został zniszczony
        if self._is_destroyed:
            return
        # Sprawdź czy widget jeszcze istnieje
        if not hasattr(self, "thumbnail_label") or self.thumbnail_label is None:
            return
        if pixmap and not pixmap.isNull():
            if hasattr(self, "thumbnail_label"):
                self.thumbnail_label.setPixmap(pixmap)

            if self.file_pair:
                color_tag = self.file_pair.get_color_tag()
                if color_tag and color_tag.strip():
                    self._update_thumbnail_border_color(color_tag)
        else:
            if hasattr(self, "thumbnail_label"):
                self.thumbnail_label.setText("Błąd ładowania")

    def _on_thumbnail_component_error(self, path: str, error_msg: str):
        """Obsługa błędów ładowania miniatur."""
        # Sprawdź czy widget nie został zniszczony
        if self._is_destroyed:
            return
        # Sprawdź czy widget jeszcze istnieje
        if not hasattr(self, "thumbnail_label") or self.thumbnail_label is None:
            return
        self.thumbnail_label.setText("Błąd")
        if not ("does not exist" in error_msg or "File not found" in error_msg):
            logger.warning(f"Thumbnail error: {error_msg}")

    def _on_metadata_stars_changed(self, stars: int):
        """Callback dla zmian gwiazdek z UI."""
        # Sprawdź czy widget nie został zniszczony
        if self._is_destroyed:
            return
        # Sprawdź czy komponenty jeszcze istnieją
        if hasattr(self, "_metadata_component") and self._metadata_component:
            self._metadata_component.set_stars(stars)

        # Natychmiastowa aktualizacja UI gwiazdek
        if hasattr(self, "metadata_controls") and self.metadata_controls:
            self.metadata_controls.update_stars_display(stars)

        # Emituj główny sygnał dla MainWindow
        if self.file_pair:
            self.stars_changed.emit(self.file_pair, stars)
            self.file_pair_updated.emit(self.file_pair)
            logging.debug(f"Stars changed: {self.file_pair.get_base_name()} → {stars}")

    def _on_metadata_color_changed(self, color_hex: str):
        """Callback dla zmian kolorów z UI."""
        # Sprawdź czy widget nie został zniszczony
        if self._is_destroyed:
            return
        # Sprawdź czy komponenty jeszcze istnieją
        if hasattr(self, "_metadata_component") and self._metadata_component:
            self._metadata_component.set_color_tag(color_hex)
            self._update_thumbnail_border_color(color_hex)

        # Natychmiastowa aktualizacja UI kolorów
        if hasattr(self, "metadata_controls") and self.metadata_controls:
            self.metadata_controls.update_color_tag_display(color_hex)

        # Emituj główny sygnał dla MainWindow
        if self.file_pair:
            self.color_tag_changed.emit(self.file_pair, color_hex)
            self.file_pair_updated.emit(self.file_pair)
            logging.debug(
                f"Color changed: {self.file_pair.get_base_name()} → {color_hex}"
            )

    def _on_tile_selection_changed(self, is_selected: bool):
        """Callback dla zmian selekcji kafelka."""
        # Sprawdź czy widget nie został zniszczony
        if self._is_destroyed:
            return
        # Sprawdź czy komponenty jeszcze istnieją
        if hasattr(self, "_metadata_component") and self._metadata_component:
            self._metadata_component.set_selection(is_selected)
        if self.file_pair:
            self.tile_selected.emit(self.file_pair, is_selected)

    def _update_thumbnail_border_color(self, color_hex: str):
        """Aktualizuje kolor obwódki wokół miniatury."""
        # Sprawdź czy widget nie został zniszczony
        if self._is_destroyed:
            return
        # Sprawdź czy widget jeszcze istnieje
        if not hasattr(self, "thumbnail_frame") or self.thumbnail_frame is None:
            return
        self.thumbnail_frame.setStyleSheet(
            TileStylesheet.get_thumbnail_frame_stylesheet(color_hex)
        )
        if color_hex and color_hex.strip():
            logging.debug(f"Ustawiono kolor obwódki na: {color_hex}")
        else:
            logging.debug("Usunięto obwódkę - przezroczysta")

    def _connect_signals(self):
        """DELEGACJA: Signal connection przeniesiony do Event Managera."""
        self._event_manager.connect_signals()

    def _install_event_filters(self):
        """Instaluje event filters dla thumbnail_label i filename_label."""
        try:
            # Podłącz eventFilter do thumbnail_label
            if hasattr(self, "thumbnail_label") and self.thumbnail_label:
                self.thumbnail_label.installEventFilter(self)
                self._event_filters.append(self.thumbnail_label)

            # Podłącz eventFilter do filename_label
            if hasattr(self, "filename_label") and self.filename_label:
                self.filename_label.installEventFilter(self)
                self._event_filters.append(self.filename_label)

        except Exception as e:
            logger.warning(f"Event filters setup failed: {e}")

    # Event handlers with delegacja to Event Manager
    def _on_thumbnail_loaded_event(self, *args, **kwargs):
        """DELEGACJA: Event handler w Event Managerze."""
        self._event_manager.on_thumbnail_loaded_event(*args, **kwargs)

    def _on_metadata_changed_event(self, *args, **kwargs):
        """DELEGACJA: Event handler w Event Managerze."""
        self._event_manager.on_metadata_changed_event(*args, **kwargs)

    def _on_user_interaction_event(self, *args, **kwargs):
        """DELEGACJA: Event handler w Event Managerze."""
        self._event_manager.on_user_interaction_event(*args, **kwargs)

    def _on_size_changed_event(self, *args, **kwargs):
        """DELEGACJA: Event handler w Event Managerze."""
        self._event_manager.on_size_changed_event(*args, **kwargs)

    # USUNIĘTE: ~120 linii event handling kodu przeniesione do FileTileWidgetEventManager

    def _on_context_menu_requested(self, file_pair, widget, event):
        """Obsługuje żądanie menu kontekstowego."""
        if file_pair:
            self.tile_context_menu_requested.emit(file_pair, widget, event)

    # === KOMPATYBILNOŚĆ WSTECZNA ===

    def update_data(self, file_pair: Optional[FilePair]):
        """
        Aktualizuje dane kafelka z nowym file_pair.
        ETAP 9: BACKWARD COMPATIBILITY - z deprecation warning.
        """
        # Sprawdź czy widget nie został zniszczony
        if self._is_destroyed:
            return

        # Show deprecation warning only after initialization
        if hasattr(self, "_compatibility_adapter"):
            self._compatibility_adapter.show_deprecation_warning(
                "update_data", "set_file_pair"
            )

        self.file_pair = file_pair

        if file_pair:
            # Delegacja do komponentów
            if hasattr(self, "_thumbnail_component") and file_pair.preview_path:
                self._thumbnail_component.load_thumbnail(file_pair.preview_path)

            if hasattr(self, "_metadata_component"):
                self._metadata_component.set_file_pair(file_pair)

            if hasattr(self, "_interaction_component"):
                self._interaction_component.set_file_pair(file_pair)

            # Event bus notification
            if hasattr(self, "_event_bus"):
                self._event_bus.emit_event(TileEvent.DATA_UPDATED, file_pair)

            # Update display
            self._update_ui_from_file_pair()

            logging.debug(
                f"FileTileWidget: Dane zaktualizowane dla {file_pair.get_base_name()}"
            )
        else:
            # Reset dla None file_pair
            self._reset_ui_state()

    def set_file_pair(self, file_pair: Optional[FilePair]):
        """KOMPATYBILNOŚĆ: Alias dla update_data()."""
        # Sprawdź czy widget nie został zniszczony
        if self._is_destroyed:
            return
        self.update_data(file_pair)

    def set_thumbnail_size(self, new_size):
        """
        KOMPATYBILNOŚĆ: Ustawia nowy rozmiar kafelka.
        Deleguje do komponentów.
        """
        # Sprawdź czy widget nie został zniszczony
        if self._is_destroyed:
            return

        if isinstance(new_size, int):
            size_tuple = (new_size, new_size)
        else:
            size_tuple = new_size

        if self.thumbnail_size != size_tuple:
            old_size = self.thumbnail_size
            self.thumbnail_size = size_tuple

            # Aktualizacja konfiguracji
            self._config.thumbnail_size = size_tuple

            # Aktualizacja UI
            self.setFixedSize(size_tuple[0], size_tuple[1])

            # Aktualizacja rozmiaru thumbnail label
            if hasattr(self, "thumbnail_label"):
                thumb_size = min(
                    size_tuple[0] - TileSizeConstants.TILE_PADDING * 2,
                    size_tuple[1]
                    - TileSizeConstants.FILENAME_MAX_HEIGHT
                    - TileSizeConstants.METADATA_MAX_HEIGHT,
                )
                thumb_size = max(thumb_size, TileSizeConstants.MIN_THUMBNAIL_WIDTH)
                self.thumbnail_label.setFixedSize(thumb_size, thumb_size)

            # Przeładuj miniaturę z nowym rozmiarem
            if self.file_pair and self.file_pair.preview_path:
                self._thumbnail_component.set_thumbnail_size(size_tuple, immediate=True)

            self._update_font_size()

            # Informowanie komponentów o zmianie
            self._event_bus.emit_event(
                TileEvent.SIZE_CHANGED, {"old_size": old_size, "new_size": size_tuple}
            )

            logging.debug(
                f"FileTileWidget: Rozmiar zmieniony z {old_size} na {size_tuple}"
            )

    def _update_filename_display(self):
        # Sprawdź czy widget nie został zniszczony
        if self._is_destroyed:
            return
            
        # Oryginalna nazwa pliku
        filename = self.file_pair.base_name if self.file_pair else ""
        # Dodaj numerację jeśli jest ustawiona
        if (
            hasattr(self, "_tile_number")
            and hasattr(self, "_tile_total")
            and self._tile_number
            and self._tile_total
        ):
            display_name = f"[{self._tile_number}/{self._tile_total}] {filename}"
        else:
            display_name = filename
        self.filename_label.setText(display_name)
        # Tooltip = oryginalna ścieżka pliku (dla podglądu)
        if self.file_pair:
            self.filename_label.setToolTip(self.file_pair.archive_path)
        else:
            self.filename_label.setToolTip("")

    def _update_ui_from_file_pair(self):
        """Aktualizuje UI na podstawie danych z file_pair."""
        # Sprawdź czy widget nie został zniszczony
        if self._is_destroyed:
            return

        if not self.file_pair:
            return

        # Aktualizacja nazwy pliku
        self._update_filename_display()

        # Aktualizacja metadata controls
        if hasattr(self, "metadata_controls"):
            self.metadata_controls.setEnabled(True)
            self.metadata_controls.set_file_pair(self.file_pair)
            self.metadata_controls.update_selection_display(False)
            self.metadata_controls.update_stars_display(self.file_pair.get_stars())

            # Aktualizacja koloru
            color_tag = self.file_pair.get_color_tag()
            self.metadata_controls.update_color_tag_display(color_tag)
            self._update_thumbnail_border_color(color_tag)

    def _reset_ui_state(self):
        """Resetuje stan UI dla None file_pair."""
        # Sprawdź czy widget nie został zniszczony
        if self._is_destroyed:
            return

        if hasattr(self, "filename_label"):
            self.filename_label.setText("Brak danych")
        if hasattr(self, "thumbnail_label"):
            self.thumbnail_label.clear()
            self.thumbnail_label.setText("?")
        if hasattr(self, "metadata_controls"):
            self.metadata_controls.set_file_pair(None)
            self.metadata_controls.setEnabled(False)

        self._update_thumbnail_border_color("")

    def _update_font_size(self):
        """Aktualizuje rozmiar czcionki w zależności od rozmiaru kafelka."""
        if isinstance(self.thumbnail_size, int):
            width = self.thumbnail_size
        else:
            width = self.thumbnail_size[0]

        base_font_size = max(8, min(18, int(width / 12)))

        if hasattr(self, "filename_label"):
            self.filename_label.setStyleSheet(
                TileStylesheet.get_filename_label_stylesheet(base_font_size)
            )

    # === DELEGACJA DO KOMPONENTÓW ===

    def _on_stars_changed(self, stars: int):
        """Deleguje sygnał gwiazdek."""
        if self.file_pair:
            self.stars_changed.emit(self.file_pair, stars)

    def _on_color_tag_changed(self, color_hex: str):
        """Deleguje sygnał tagów kolorów."""
        if self.file_pair:
            self.color_tag_changed.emit(self.file_pair, color_hex)

    # === PRZEKIEROWANIE ZDARZEŃ DO INTERACTION COMPONENT ===

    def mousePressEvent(self, event):
        """Przekierowuje do interaction component."""
        if hasattr(self, "_interaction_component"):
            self._interaction_component.handle_mouse_press(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Przekierowuje do interaction component."""
        if hasattr(self, "_interaction_component"):
            self._interaction_component.handle_mouse_move(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Przekierowuje do interaction component."""
        if hasattr(self, "_interaction_component"):
            self._interaction_component.handle_mouse_release(event)
        else:
            super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        """Obsługuje menu kontekstowe."""
        if self.file_pair:
            self.tile_context_menu_requested.emit(self.file_pair, self, event)
        else:
            super().contextMenuEvent(event)

    def keyPressEvent(self, event):
        """Przekierowuje do interaction component."""
        if hasattr(self, "_interaction_component"):
            self._interaction_component.handle_key_press(event)
        else:
            super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        """Obsługuje zdarzenia na etykietach miniatury i nazwy."""
        from PyQt6.QtCore import QEvent

        if event.type() == QEvent.Type.MouseButtonPress:
            from PyQt6.QtCore import Qt

            if event.button() == Qt.MouseButton.LeftButton:
                if obj == self.thumbnail_label and self.file_pair:
                    self.preview_image_requested.emit(self.file_pair)
                    return True
                elif obj == self.filename_label and self.file_pair:
                    self.archive_open_requested.emit(self.file_pair)
                    return True

        return super().eventFilter(obj, event)

    # === ETAP 9: BACKWARD COMPATIBILITY API ===

    def change_thumbnail_size(self, size):
        """
        LEGACY API: Zmienia rozmiar miniatur.

        Mapowane na set_thumbnail_size() z deprecation warning.

        Args:
            size: Nowy rozmiar (int lub tuple)
        """
        if hasattr(self, "_compatibility_adapter"):
            return self._compatibility_adapter.change_thumbnail_size_legacy(size)

    def refresh_thumbnail(self):
        """
        LEGACY API: Odświeża miniaturę.

        Mapowane na reload_current() z deprecation warning.
        """
        if hasattr(self, "_compatibility_adapter"):
            return self._compatibility_adapter.refresh_thumbnail_legacy()

    def get_file_data(self):
        """
        LEGACY API: Pobiera dane pliku.

        Mapowane na file_pair property z deprecation warning.

        Returns:
            FilePair: Obiekt pary plików
        """
        if hasattr(self, "_compatibility_adapter"):
            return self._compatibility_adapter.get_file_data_legacy()

    def set_selection(self, selected: bool):
        """
        LEGACY API: Ustawia status selekcji.

        Mapowane na set_selected() z deprecation warning.

        Args:
            selected: Czy kafelek jest zaznaczony
        """
        if hasattr(self, "_compatibility_adapter"):
            return self._compatibility_adapter.set_selection_legacy(selected)

    # === Getters/Setters dla kompatybilności ===

    def get_thumbnail_size(self) -> Tuple[int, int]:
        """Zwraca aktualny rozmiar miniatur."""
        return self.thumbnail_size

    def get_file_pair(self) -> Optional[FilePair]:
        """Zwraca obiekt FilePair."""
        return self.file_pair

    def is_tile_selected(self) -> bool:
        """Sprawdza czy kafelek jest zaznaczony."""
        return self.is_selected

    def reload_thumbnail(self):
        """NOWE API: Odświeża miniaturę."""
        if hasattr(self, "_thumbnail_component") and self.file_pair:
            preview_path = self.file_pair.get_preview_path()
            if preview_path:
                self._thumbnail_component.load_thumbnail(
                    preview_path, self.thumbnail_size
                )

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

    # === LIFECYCLE MANAGEMENT ===

    # USUNIĘTE: ~150 linii thumbnail loading kodu przeniesione do ThumbnailOperations

    def cleanup(self):
        """DELEGACJA: Cleanup przeniesiony do Cleanup Managera."""
        # Oznacz widget jako zniszczony
        self._is_destroyed = True
        self._cleanup_manager.cleanup()

    # USUNIĘTE: ~90 linii cleanup kodu przeniesione do FileTileWidgetCleanupManager

    def __del__(self):
        """Destruktor - automatyczny cleanup."""
        try:
            # Oznacz widget jako zniszczony
            self._is_destroyed = True
            if not self._is_cleanup_done:
                self.cleanup()
        except Exception:
            # Ignoruj błędy w destruktorze
            pass

    # --- NOWE API ---

    def set_selected(self, selected: bool):
        """
        NOWE API: Ustawia status selekcji.

        Args:
            selected: Czy kafelek jest zaznaczony
        """
        if self.is_selected != selected:
            self.is_selected = selected
            # Emit sygnał o zmianie selekcji
            if self.file_pair:
                self.tile_selected.emit(self.file_pair, selected)

    def set_tile_number(self, number: int, total: int):
        self._tile_number = number
        self._tile_total = total
        self._update_filename_display()
