"""
Kafelek wyświetlający miniaturę podglądu, nazwę i rozmiar pliku archiwum.
Zrefaktoryzowany jako controller integrujący komponenty.
"""

# Standard library imports
import logging
import threading
from typing import Optional, Tuple

# Third-party imports
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QWidget

# Local imports
from src.models.file_pair import FilePair

# Import new component architecture
from src.ui.widgets.tile_config import TileConfig, TileEvent, TileState
from src.ui.widgets.tile_event_bus import TileEventBus
from src.ui.widgets.tile_interaction_component import TileInteractionComponent
from src.ui.widgets.tile_metadata_component import TileMetadataComponent
from src.ui.widgets.tile_resource_manager import get_resource_manager
from src.ui.widgets.tile_styles import (
    TileColorScheme,
    TileSizeConstants,
    TileStylesheet,
)
from src.ui.widgets.tile_thumbnail_component import ThumbnailComponent

from .file_tile_widget_cleanup import FileTileWidgetCleanupManager
from .file_tile_widget_compatibility import CompatibilityAdapter
from .file_tile_widget_events import FileTileWidgetEventManager
from .file_tile_widget_thumbnail import ThumbnailOperations
from .file_tile_widget_ui_manager import FileTileWidgetUIManager

logger = logging.getLogger(__name__)


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
            skip_resource_registration: Czy pominąć rejestrację w ResourceManager.
        """
        super().__init__(parent)

        # Thread-safe flaga do sprawdzania czy widget został zniszczony
        self._is_destroyed = False
        self._destroy_lock = threading.RLock()

        # Resource management registration
        self._resource_manager = get_resource_manager()
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
        self._cleanup_lock = threading.RLock()
        self._cleanup_in_progress = False

        # Enhanced event tracking dla memory leak prevention
        self._event_subscriptions = []
        self._signal_connections = []
        self._event_filters = []

        # Konfiguracja komponentu
        self._config = TileConfig()
        self._config.thumbnail_size = default_thumbnail_size

        # Inicjalizacja komponentów
        self._initialize_components()

        # Inicjalizacja wydzielonych modułów
        self._compatibility_adapter = CompatibilityAdapter(self)
        self._thumbnail_ops = ThumbnailOperations(self)
        self._ui_manager = FileTileWidgetUIManager(self)
        self._event_manager = FileTileWidgetEventManager(self)
        self._cleanup_manager = FileTileWidgetCleanupManager(self)

        # Performance optimization integration
        self._setup_performance_optimization()

        # Konfiguracja UI
        self._setup_ui()

        # Połączenie sygnałów
        self._connect_signals()

        # Instalacja event filters
        self._install_event_filters()

        # Aktualizacja danych
        if file_pair:
            self.update_data(file_pair)

    def _is_widget_destroyed(self) -> bool:
        """Thread-safe sprawdzenie czy widget został zniszczony."""
        with self._destroy_lock:
            return self._is_destroyed

    def _quick_destroyed_check(self) -> bool:
        """Thread-safe sprawdzenie destroyed state z lightweight locking."""
        # NAPRAWKA: Thread safety dla hot paths z read lock
        with self._destroy_lock:
            return self._is_destroyed

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
        """Setup performance optimization z bezpieczną walidacją komponentów."""
        try:
            if self._resource_manager:
                # Bezpieczna walidacja komponentów przed użyciem
                perf_monitor = self._resource_manager.get_performance_monitor()
                cache_optimizer = self._resource_manager.get_cache_optimizer()
                async_ui_manager = self._resource_manager.get_async_ui_manager()

                # Walidacja czy komponenty mają wymagane metody
                if perf_monitor and hasattr(perf_monitor, "record_metric"):
                    self._performance_monitor = perf_monitor
                else:
                    self._performance_monitor = None

                if cache_optimizer and hasattr(cache_optimizer, "register_cache_user"):
                    self._cache_optimizer = cache_optimizer
                    self._cache_optimizer.register_cache_user(self)
                else:
                    self._cache_optimizer = None

                if async_ui_manager and hasattr(async_ui_manager, "schedule_ui_update"):
                    self._async_ui_manager = async_ui_manager
                else:
                    self._async_ui_manager = None
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
        if self._is_widget_destroyed():
            return
        if not hasattr(self, "thumbnail_label") or self.thumbnail_label is None:
            return
        if pixmap and not pixmap.isNull():
            self.thumbnail_label.setPixmap(pixmap)

    def _on_thumbnail_loaded(self, pixmap, path, width, height):
        """Obsługuje załadowaną miniaturę - dla TileManager."""
        if self._is_widget_destroyed():
            return
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
        if self._is_widget_destroyed():
            return
        if not hasattr(self, "thumbnail_label") or self.thumbnail_label is None:
            return
        self.thumbnail_label.setText("Błąd")
        if not ("does not exist" in error_msg or "File not found" in error_msg):
            logger.warning(f"Thumbnail error: {error_msg}")

    def _on_metadata_stars_changed(self, stars: int):
        """Callback dla zmian gwiazdek z UI z enhanced error handling."""
        try:
            if self._is_widget_destroyed():
                return
            if hasattr(self, "_metadata_component") and self._metadata_component:
                self._metadata_component.set_stars(stars)

            # Natychmiastowa aktualizacja UI gwiazdek
            if hasattr(self, "metadata_controls") and self.metadata_controls:
                self.metadata_controls.update_stars_display(stars)

            # Emituj główny sygnał dla MainWindow
            if self.file_pair:
                self.stars_changed.emit(self.file_pair, stars)
                self.file_pair_updated.emit(self.file_pair)
        except Exception as e:
            logger.debug(f"Error in _on_metadata_stars_changed: {e}")

    def _on_metadata_color_changed(self, color_hex: str):
        """Callback dla zmian kolorów z UI z enhanced error handling."""
        try:
            if self._is_widget_destroyed():
                return
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
        except Exception as e:
            logger.debug(f"Error in _on_metadata_color_changed: {e}")

    def _on_tile_selection_changed(self, is_selected: bool):
        """Callback dla zmian selekcji kafelka."""
        if self._is_widget_destroyed():
            return
        if hasattr(self, "_metadata_component") and self._metadata_component:
            self._metadata_component.set_selection(is_selected)
        if self.file_pair:
            self.tile_selected.emit(self.file_pair, is_selected)

    def _update_thumbnail_border_color(self, color_hex: str):
        """Aktualizuje kolor obwódki wokół miniatury."""
        if self._is_widget_destroyed():
            return
        if not hasattr(self, "thumbnail_frame") or self.thumbnail_frame is None:
            return
        self.thumbnail_frame.setStyleSheet(
            TileStylesheet.get_thumbnail_frame_stylesheet(color_hex)
        )

    def _connect_signals(self):
        """Signal connection delegate to Event Manager."""
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

    # Event handlers delegate to Event Manager
    def _on_thumbnail_loaded_event(self, *args, **kwargs):
        """Event handler delegate."""
        self._event_manager.on_thumbnail_loaded_event(*args, **kwargs)

    def _on_metadata_changed_event(self, *args, **kwargs):
        """Event handler delegate."""
        self._event_manager.on_metadata_changed_event(*args, **kwargs)

    def _on_user_interaction_event(self, *args, **kwargs):
        """Event handler delegate."""
        self._event_manager.on_user_interaction_event(*args, **kwargs)

    def _on_size_changed_event(self, *args, **kwargs):
        """Event handler delegate."""
        self._event_manager.on_size_changed_event(*args, **kwargs)

    def _on_context_menu_requested(self, file_pair, widget, event):
        """Obsługuje żądanie menu kontekstowego."""
        if file_pair:
            self.tile_context_menu_requested.emit(file_pair, widget, event)

    # === KOMPATYBILNOŚĆ WSTECZNA ===

    def update_data(self, file_pair: Optional[FilePair]):
        """
        Aktualizuje dane kafelka z nowym file_pair.
        """
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
        else:
            # Reset dla None file_pair
            self._reset_ui_state()

    def set_file_pair(self, file_pair: Optional[FilePair]):
        """Alias dla update_data()."""
        if self._is_destroyed:
            return
        self.update_data(file_pair)

    def set_thumbnail_size(self, new_size):
        """
        Ustawia nowy rozmiar kafelka.
        Deleguje do komponentów.
        """
        if self._is_destroyed:
            return
        if (
            not hasattr(self, "_thumbnail_component")
            or self._thumbnail_component is None
        ):
            return
        if getattr(self._thumbnail_component, "_is_disposed", False):
            return
        if (
            getattr(self._thumbnail_component, "get_current_state", lambda: None)()
            == TileState.DISPOSED
        ):
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

    def _update_filename_display(self):
        if self._quick_destroyed_check():
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

        # Optymalizacja: sprawdź czy display_name się zmienił
        if (
            hasattr(self, "_cached_display_name")
            and self._cached_display_name == display_name
        ):
            return

        self._cached_display_name = display_name
        self.filename_label.setText(display_name)
        # Tooltip = oryginalna ścieżka pliku (dla podglądu)
        if self.file_pair:
            self.filename_label.setToolTip(self.file_pair.archive_path)
        else:
            self.filename_label.setToolTip("")

    def _update_ui_from_file_pair(self):
        """Aktualizuje UI na podstawie danych z file_pair z bezpieczną walidacją komponentów."""
        if self._quick_destroyed_check():
            return

        if not self.file_pair:
            return

        # Aktualizacja nazwy pliku
        self._update_filename_display()

        # NAPRAWKA: Bezpieczna walidacja komponentów przed użyciem
        if hasattr(self, "_async_ui_manager") and self._async_ui_manager:
            try:
                # Sprawdź czy async manager ma wymagane metody
                if hasattr(self._async_ui_manager, "schedule_async_update"):
                    self._async_ui_manager.schedule_async_update(
                        lambda: self._update_metadata_controls_async()
                    )
                elif hasattr(self._async_ui_manager, "schedule_ui_update"):
                    self._async_ui_manager.schedule_ui_update(
                        lambda: self._update_metadata_controls_async()
                    )
                else:
                    # Fallback: bezpośrednia aktualizacja
                    self._update_metadata_controls_async()
            except Exception as e:
                logger.warning(f"Async UI update failed: {e}")
                # Fallback: bezpośrednia aktualizacja
                self._update_metadata_controls_async()
        else:
            # Bezpośrednia aktualizacja gdy brak async manager
            self._update_metadata_controls_async()

        # NAPRAWKA: Bezpieczna walidacja thumbnail component
        if hasattr(self, "_thumbnail_component") and self._thumbnail_component:
            try:
                if hasattr(self._thumbnail_component, "update_thumbnail"):
                    self._thumbnail_component.update_thumbnail()
            except Exception as e:
                logger.warning(f"Thumbnail update failed: {e}")

        # NAPRAWKA: Bezpieczna walidacja metadata component
        if hasattr(self, "_metadata_component") and self._metadata_component:
            try:
                if hasattr(self._metadata_component, "update_display"):
                    self._metadata_component.update_display()
            except Exception as e:
                logger.warning(f"Metadata display update failed: {e}")

    def _update_metadata_controls_async(self):
        """Asynchroniczna aktualizacja metadata controls."""
        if self._quick_destroyed_check() or not self.file_pair:
            return

        if hasattr(self, "metadata_controls") and self.metadata_controls:
            self.metadata_controls.setEnabled(True)
            self.metadata_controls.set_file_pair(self.file_pair)
            self.metadata_controls.update_selection_display(False)
            self.metadata_controls.update_stars_display(self.file_pair.get_stars())

            # Aktualizacja koloru
            color_tag = self.file_pair.get_color_tag()
            self.metadata_controls.update_color_tag_display(color_tag)
            self._update_thumbnail_border_color(color_tag)

    def _update_metadata_controls_sync(self):
        """Synchroniczna aktualizacja metadata controls (fallback)."""
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

    # === BACKWARD COMPATIBILITY API ===

    def change_thumbnail_size(self, size):
        """Legacy API: Zmienia rozmiar miniatur."""
        if hasattr(self, "_compatibility_adapter"):
            return self._compatibility_adapter.change_thumbnail_size_legacy(size)

    def refresh_thumbnail(self):
        """Legacy API: Odświeża miniaturę."""
        if hasattr(self, "_compatibility_adapter"):
            return self._compatibility_adapter.refresh_thumbnail_legacy()

    def get_file_data(self):
        """Legacy API: Pobiera dane pliku."""
        if hasattr(self, "_compatibility_adapter"):
            return self._compatibility_adapter.get_file_data_legacy()

    def set_selection(self, selected: bool):
        """Legacy API: Ustawia status selekcji."""
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
        """Odświeża miniaturę."""
        if (
            not hasattr(self, "_thumbnail_component")
            or self._thumbnail_component is None
        ):
            return
        if getattr(self._thumbnail_component, "_is_disposed", False):
            return
        if (
            getattr(self._thumbnail_component, "get_current_state", lambda: None)()
            == TileState.DISPOSED
        ):
            return
        if self.file_pair:
            preview_path = self.file_pair.get_preview_path()
            if preview_path:
                self._thumbnail_component.load_thumbnail(
                    preview_path, self.thumbnail_size
                )

    # === LEGACY METHODS DLA KOMPATYBILNOŚCI ===

    def open_file(self):
        """Otwiera plik archiwum."""
        if self.file_pair:
            self.archive_open_requested.emit(self.file_pair)

    def preview_image(self):
        """Podgląd obrazu."""
        if self.file_pair:
            self.preview_image_requested.emit(self.file_pair)

    def show_properties(self):
        """Pokazuje właściwości pliku."""
        pass  # Placeholder for future implementation

    # === LIFECYCLE MANAGEMENT ===

    def cleanup(self):
        """Cleanup delegate to Cleanup Manager + memory leak prevention."""
        self._is_destroyed = True
        # Memory leak prevention: czyść event subscriptions
        if hasattr(self, "_event_subscriptions"):
            for subscription in self._event_subscriptions[:]:
                try:
                    if hasattr(subscription, "disconnect"):
                        subscription.disconnect()
                    elif hasattr(subscription, "unsubscribe"):
                        subscription.unsubscribe()
                except Exception:
                    pass
            self._event_subscriptions.clear()
        # Czyść signal connections
        if hasattr(self, "_signal_connections"):
            for connection in self._signal_connections[:]:
                try:
                    if hasattr(connection, "disconnect"):
                        connection.disconnect()
                except Exception:
                    pass
            self._signal_connections.clear()
        # Czyść event filters
        if hasattr(self, "_event_filters"):
            for event_filter in self._event_filters[:]:
                try:
                    if hasattr(event_filter, "removeEventFilter"):
                        event_filter.removeEventFilter(self)
                except Exception:
                    pass
            self._event_filters.clear()
        # Deleguj do cleanup managera
        self._cleanup_manager.cleanup()

    def __del__(self):
        """Destruktor - automatyczny cleanup."""
        try:
            self._is_destroyed = True
            if not self._is_cleanup_done:
                self.cleanup()
        except Exception:
            pass

    # === NEW API ===

    def set_selected(self, selected: bool):
        """
        Ustawia status selekcji.

        Args:
            selected: Czy kafelek jest zaznaczony
        """
        if self.is_selected != selected:
            self.is_selected = selected
            if self.file_pair:
                self.tile_selected.emit(self.file_pair, selected)

    def set_tile_number(self, number: int, total: int):
        """Ustawia numerację kafelka."""
        self._tile_number = number
        self._tile_total = total
        self._update_filename_display()
