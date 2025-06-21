"""
Cleanup Manager dla FileTileWidget.

Zarządza wszystkimi operacjami cleanup.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .file_tile_widget import FileTileWidget


class FileTileWidgetCleanupManager:
    """Zarządza wszystkimi operacjami cleanup dla FileTileWidget."""

    def __init__(self, widget: "FileTileWidget"):
        self.widget = widget
        self.logger = logging.getLogger(__name__)

    def cleanup(self):
        """Thread-safe cleanup z protection przed wielokrotnym wywołaniem."""
        with self.widget._cleanup_lock:
            if self.widget._is_cleanup_done or self.widget._cleanup_in_progress:
                return

            self.widget._cleanup_in_progress = True

        try:
            self.cleanup_event_subscriptions()
            self.cleanup_event_filters()
            self.cleanup_components()
            self.cleanup_resources()

        except Exception as e:
            self.logger.error(f"Tile cleanup error: {e}", exc_info=True)
        finally:
            with self.widget._cleanup_lock:
                self.widget._cleanup_in_progress = False
                self.widget._is_cleanup_done = True

    def cleanup_event_subscriptions(self):
        """Enhanced cleanup wszystkich tracked event subscriptions."""
        try:
            if (
                hasattr(self.widget, "_event_subscriptions")
                and self.widget._event_subscriptions
            ):
                for event_type, handler in self.widget._event_subscriptions:
                    try:
                        if hasattr(self.widget._event_bus, "unsubscribe"):
                            self.widget._event_bus.unsubscribe(event_type, handler)
                    except Exception as e:
                        self.logger.warning(f"Event unsubscribe failed: {e}")

                self.widget._event_subscriptions.clear()

            if (
                hasattr(self.widget, "_signal_connections")
                and self.widget._signal_connections
            ):
                for (
                    component,
                    signal_name,
                    connection,
                ) in self.widget._signal_connections:
                    try:
                        if component and hasattr(component, signal_name):
                            signal = getattr(component, signal_name)
                            if hasattr(signal, "disconnect") and connection:
                                signal.disconnect(connection)
                    except Exception as e:
                        self.logger.warning(f"Signal disconnect failed: {e}")

                self.widget._signal_connections.clear()

        except Exception as e:
            self.logger.warning(f"Event subscriptions cleanup error: {e}")

    def cleanup_event_filters(self):
        """Enhanced cleanup wszystkich tracked event filters."""
        try:
            if hasattr(self.widget, "_event_filters") and self.widget._event_filters:
                for widget in self.widget._event_filters:
                    try:
                        if widget:
                            widget.removeEventFilter(self.widget)
                    except Exception:
                        pass

                self.widget._event_filters.clear()

        except Exception as e:
            self.logger.warning(f"Event filters cleanup error: {e}")

    def cleanup_components(self):
        """Czyści komponenty tile."""
        components = [
            "_thumbnail_component",
            "_metadata_component",
            "_interaction_component",
        ]
        for component_name in components:
            if hasattr(self.widget, component_name):
                component = getattr(self.widget, component_name)
                if component and hasattr(component, "cleanup"):
                    try:
                        component.cleanup()
                    except Exception as e:
                        self.logger.warning(
                            f"Component cleanup error {component_name}: {e}"
                        )

    def cleanup_resources(self):
        """Czyści zasoby z resource manager."""
        if hasattr(self.widget, "_resource_manager") and self.widget._resource_manager:
            try:
                if (
                    hasattr(self.widget, "_is_registered")
                    and self.widget._is_registered
                ):
                    self.widget._resource_manager.unregister_tile(self.widget)
                    self.widget._is_registered = False
            except Exception as e:
                self.logger.warning(f"Resource cleanup error: {e}")

        self.widget.file_pair = None
