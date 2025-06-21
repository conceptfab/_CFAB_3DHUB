"""
Event Manager dla FileTileWidget.

Zarządza wszystkimi operacjami event handling.
"""

import logging
from typing import TYPE_CHECKING

from src.ui.widgets.tile_config import TileEvent

if TYPE_CHECKING:
    from .file_tile_widget import FileTileWidget


class FileTileWidgetEventManager:
    """Zarządza wszystkimi operacjami event handling dla FileTileWidget."""

    def __init__(self, widget: "FileTileWidget"):
        self.widget = widget
        self.logger = logging.getLogger(__name__)

    def connect_signals(self):
        """Enhanced signal connection z tracking dla memory leak prevention."""
        try:
            self.connect_event_bus_signals()
            self.connect_component_signals()
        except Exception as e:
            self.logger.error(f"Signal connection error: {e}", exc_info=True)

    def connect_event_bus_signals(self):
        """Łączy sygnały event bus z tracking."""
        if not self.widget._event_bus:
            return

        event_mappings = [
            (TileEvent.THUMBNAIL_LOADED, self.widget._on_thumbnail_loaded_event),
            (TileEvent.METADATA_CHANGED, self.widget._on_metadata_changed_event),
            (TileEvent.USER_INTERACTION, self.widget._on_user_interaction_event),
            (TileEvent.SIZE_CHANGED, self.widget._on_size_changed_event),
        ]

        for event_type, handler in event_mappings:
            try:
                self.widget._event_bus.subscribe(event_type, handler)
                self.widget._event_subscriptions.append((event_type, handler))
            except Exception as e:
                self.logger.warning(f"Event subscription failed {event_type}: {e}")

    def connect_component_signals(self):
        """Łączy sygnały komponentów z tracking."""
        try:
            if hasattr(self.widget._metadata_component, "stars_changed"):
                connection = self.widget._metadata_component.stars_changed.connect(
                    self.widget._on_stars_changed
                )
                self.widget._signal_connections.append(
                    (self.widget._metadata_component, "stars_changed", connection)
                )

            if hasattr(self.widget._metadata_component, "color_tag_changed"):
                connection = self.widget._metadata_component.color_tag_changed.connect(
                    self.widget._on_color_tag_changed
                )
                self.widget._signal_connections.append(
                    (self.widget._metadata_component, "color_tag_changed", connection)
                )

            if hasattr(self.widget._interaction_component, "filename_clicked"):
                connection = (
                    self.widget._interaction_component.filename_clicked.connect(
                        self.widget.archive_open_requested.emit
                    )
                )
                self.widget._signal_connections.append(
                    (self.widget._interaction_component, "filename_clicked", connection)
                )

            if hasattr(self.widget._interaction_component, "thumbnail_clicked"):
                connection = (
                    self.widget._interaction_component.thumbnail_clicked.connect(
                        self.widget.preview_image_requested.emit
                    )
                )
                self.widget._signal_connections.append(
                    (
                        self.widget._interaction_component,
                        "thumbnail_clicked",
                        connection,
                    )
                )

            if hasattr(self.widget._interaction_component, "context_menu_requested"):
                connection = (
                    self.widget._interaction_component.context_menu_requested.connect(
                        self.widget._on_context_menu_requested
                    )
                )
                self.widget._signal_connections.append(
                    (
                        self.widget._interaction_component,
                        "context_menu_requested",
                        connection,
                    )
                )

        except Exception as e:
            self.logger.warning(f"Component signal connection failed: {e}")

    def install_event_filters(self):
        """Enhanced event filter installation z tracking."""
        try:
            filter_targets = [
                ("thumbnail_label", "thumbnail label"),
                ("filename_label", "filename label"),
            ]

            for widget_attr, description in filter_targets:
                if hasattr(self.widget, widget_attr):
                    widget = getattr(self.widget, widget_attr)
                    if widget:
                        try:
                            widget.installEventFilter(self.widget)
                            self.widget._event_filters.append(widget)
                        except Exception as e:
                            self.logger.warning(f"Event filter install failed: {e}")

        except Exception as e:
            self.logger.error(f"Event filters setup failed: {e}")

    # Event handlers with flexible arguments
    def on_thumbnail_loaded_event(self, *args, **kwargs):
        """Obsługuje zdarzenie załadowania miniatury z flexible args."""
        try:
            thumbnail_data = (
                args[0] if args else kwargs.get("thumbnail_data", "unknown")
            )
        except Exception as e:
            self.logger.warning(f"Event handler error: {e}")

    def on_metadata_changed_event(self, *args, **kwargs):
        """Obsługuje zdarzenie zmiany metadanych z flexible args."""
        try:
            metadata_data = args[0] if args else kwargs.get("metadata_data", "unknown")
        except Exception as e:
            self.logger.warning(f"Event handler error: {e}")

    def on_user_interaction_event(self, *args, **kwargs):
        """Obsługuje zdarzenie interakcji użytkownika z flexible args."""
        try:
            interaction_data = (
                args[0] if args else kwargs.get("interaction_data", "unknown")
            )
        except Exception as e:
            self.logger.warning(f"Event handler error: {e}")

    def on_size_changed_event(self, *args, **kwargs):
        """Obsługuje zdarzenie zmiany rozmiaru z flexible args."""
        try:
            size_data = args[0] if args else kwargs.get("size_data", "unknown")
            if hasattr(self.widget, "_ui_manager"):
                self.widget._ui_manager.update_font_size()
        except Exception as e:
            self.logger.warning(f"Event handler error: {e}")
