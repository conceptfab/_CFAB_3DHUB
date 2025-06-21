"""
ETAP 2: EVENT BUS - Centralizacja komunikacji między komponentami
System eventów z weak references dla FileTileWidget components.
"""

import logging
import weakref
from typing import Any, Callable, Dict, List, Optional, Set
from weakref import WeakSet

from PyQt6.QtCore import QObject, pyqtSignal

from src.ui.widgets.tile_config import TileEvent

logger = logging.getLogger(__name__)


class TileEventBus(QObject):
    """
    Event Bus dla komunikacji między komponentami kafelka.
    Używa weak references żeby uniknąć memory leaks.
    """

    # Qt signals dla różnych typów eventów
    thumbnail_loaded = pyqtSignal(str, object)  # path, pixmap
    thumbnail_error = pyqtSignal(str, str)  # path, error_message
    data_updated = pyqtSignal(object)  # FilePair data
    state_changed = pyqtSignal(object)  # TileState
    user_interaction = pyqtSignal(str, object)  # action_name, data

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)

        # Weak references do callback functions
        # Key: TileEvent, Value: WeakSet of callbacks
        self._subscribers: Dict[TileEvent, WeakSet] = {
            event: WeakSet() for event in TileEvent
        }

        # Debug tracking
        self._event_count = 0
        self._debug_enabled = False

        logger.debug("TileEventBus created")

    def enable_debug(self, enabled: bool = True):
        """Włącz/wyłącz debug logging dla event bus."""
        self._debug_enabled = enabled
        if enabled:
            logger.debug("TileEventBus debug mode enabled")

    def subscribe(self, event: TileEvent, callback: Callable) -> bool:
        """
        Subscribe do eventów.

        Args:
            event: Typ eventu do którego się subscribujemy
            callback: Funkcja callback (używa weak reference)

        Returns:
            bool: True jeśli subscription successful
        """
        try:
            # Add callback to weak set
            self._subscribers[event].add(callback)

            if self._debug_enabled:
                subscriber_count = len(self._subscribers[event])
                logger.debug(
                    f"Subscribed to {event.name}: {subscriber_count} subscribers"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to subscribe to {event.name}: {e}")
            return False

    def unsubscribe(self, event: TileEvent, callback: Callable) -> bool:
        """
        Unsubscribe od eventów.

        Args:
            event: Typ eventu
            callback: Funkcja callback do usunięcia

        Returns:
            bool: True jeśli unsubscription successful
        """
        try:
            # Remove from weak set
            self._subscribers[event].discard(callback)

            if self._debug_enabled:
                subscriber_count = len(self._subscribers[event])
                logger.debug(
                    f"Unsubscribed from {event.name}: {subscriber_count} subscribers remaining"
                )

            return True

        except Exception as e:
            logger.error(f"Failed to unsubscribe from {event.name}: {e}")
            return False

    def emit_event(self, event: TileEvent, *args, **kwargs) -> int:
        """
        Emituj event do wszystkich subscribers.

        Args:
            event: Typ eventu
            *args: Argumenty dla callbacks
            **kwargs: Keyword argumenty dla callbacks

        Returns:
            int: Liczba powiadomowanych subscribers
        """
        self._event_count += 1

        if self._debug_enabled:
            logger.debug(
                f"Emitting {event.name} (#{self._event_count}) with args={args}, kwargs={kwargs}"
            )

        # Get current subscribers (copy to avoid modification during iteration)
        subscribers = list(self._subscribers[event])
        notified_count = 0

        # Call all subscribers
        for callback in subscribers:
            try:
                callback(*args, **kwargs)
                notified_count += 1

            except Exception as e:
                logger.error(f"Error in subscriber callback for {event.name}: {e}")
                # Continue with other callbacks

        # Also emit appropriate Qt signal
        self._emit_qt_signal(event, *args, **kwargs)

        if self._debug_enabled:
            logger.debug(f"Event {event.name} notified {notified_count} subscribers")

        return notified_count

    def _emit_qt_signal(self, event: TileEvent, *args, **kwargs):
        """Emituj odpowiedni Qt signal na podstawie typu eventu."""
        try:
            if event == TileEvent.THUMBNAIL_LOADED and len(args) >= 2:
                self.thumbnail_loaded.emit(args[0], args[1])  # path, pixmap

            elif event == TileEvent.THUMBNAIL_ERROR and len(args) >= 2:
                self.thumbnail_error.emit(args[0], args[1])  # path, error_msg

            elif event == TileEvent.DATA_UPDATED and len(args) >= 1:
                self.data_updated.emit(args[0])  # FilePair

            elif event == TileEvent.STATE_CHANGED and len(args) >= 1:
                self.state_changed.emit(args[0])  # TileState

            elif event == TileEvent.USER_INTERACTION and len(args) >= 2:
                self.user_interaction.emit(args[0], args[1])  # action, data

        except Exception as e:
            logger.error(f"Error emitting Qt signal for {event.name}: {e}")

    def get_subscriber_count(self, event: TileEvent) -> int:
        """Zwraca liczbę subscribers dla danego eventu."""
        return len(self._subscribers[event])

    def get_total_subscribers(self) -> int:
        """Zwraca całkowitą liczbę subscribers."""
        return sum(len(subscribers) for subscribers in self._subscribers.values())

    def clear_subscribers(self, event: Optional[TileEvent] = None):
        """
        Wyczyść subscribers.

        Args:
            event: Konkretny event (None = all events)
        """
        if event is None:
            # Clear all
            for event_type in TileEvent:
                self._subscribers[event_type].clear()
            logger.debug("Cleared all event subscribers")
        else:
            # Clear specific event
            self._subscribers[event].clear()
            logger.debug(f"Cleared subscribers for {event.name}")

    def get_debug_info(self) -> Dict[str, Any]:
        """Zwraca informacje debug o event bus."""
        subscriber_counts = {
            event.name: len(subscribers)
            for event, subscribers in self._subscribers.items()
        }

        return {
            "total_events_emitted": self._event_count,
            "total_subscribers": self.get_total_subscribers(),
            "subscriber_counts": subscriber_counts,
            "debug_enabled": self._debug_enabled,
        }

    def cleanup(self):
        """Cleanup event bus - usuń wszystkich subscribers."""
        self.clear_subscribers()
        self._event_count = 0
        logger.debug("TileEventBus cleaned up")


class TileEventSubscriber:
    """
    Helper class dla łatwego subscribowania do eventów.
    Automatycznie usuwa subscriptions przy destrukcji.
    """

    def __init__(self, event_bus: TileEventBus):
        self.event_bus = event_bus
        self._subscriptions: List[tuple[TileEvent, Callable]] = []

    def subscribe(self, event: TileEvent, callback: Callable) -> bool:
        """Subscribe i dodaj do listy tracked subscriptions."""
        success = self.event_bus.subscribe(event, callback)
        if success:
            self._subscriptions.append((event, callback))
        return success

    def unsubscribe_all(self):
        """Unsubscribe od wszystkich tracked subscriptions."""
        for event, callback in self._subscriptions:
            self.event_bus.unsubscribe(event, callback)
        self._subscriptions.clear()

    def __del__(self):
        """Automatyczny cleanup przy destrukcji."""
        self.unsubscribe_all()


# === HELPER FUNCTIONS ===


def create_event_bus(enable_debug: bool = False) -> TileEventBus:
    """
    Factory function dla tworzenia event bus.

    Args:
        enable_debug: Czy włączyć debug logging

    Returns:
        TileEventBus: Skonfigurowany event bus
    """
    bus = TileEventBus()
    bus.enable_debug(enable_debug)
    return bus


def create_subscriber(event_bus: TileEventBus) -> TileEventSubscriber:
    """
    Factory function dla tworzenia subscriber helper.

    Args:
        event_bus: Event bus do którego subscriber się podłączy

    Returns:
        TileEventSubscriber: Helper dla subscriptions
    """
    return TileEventSubscriber(event_bus)
