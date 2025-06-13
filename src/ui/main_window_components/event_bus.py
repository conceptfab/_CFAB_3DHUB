"""
🚀 OPTYMALIZACJA: Event Bus - eliminuje tight coupling w MainWindow
Centralny system zdarzeń dla aplikacji zamiast bezpośrednich wywołań.
"""

import logging
from typing import Dict, List, Callable, Any
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class EventBus(QObject):
    """
    Centralny system zdarzeń dla aplikacji.
    Eliminuje tight coupling między komponentami MainWindow.
    """

    # Sygnały dla różnych typów zdarzeń
    folder_selected = pyqtSignal(str)  # Wybrano folder
    file_pair_selected = pyqtSignal(object)  # Wybrano parę plików
    metadata_changed = pyqtSignal(object, str, object)  # Zmieniono metadane
    scan_started = pyqtSignal(str)  # Rozpoczęto skanowanie
    scan_finished = pyqtSignal(list)  # Zakończono skanowanie
    view_refresh_requested = pyqtSignal(str)  # Żądanie odświeżenia widoku
    thumbnail_size_changed = pyqtSignal(int)  # Zmieniono rozmiar miniaturek
    filter_changed = pyqtSignal(object)  # Zmieniono filtr
    
    # Sygnały dla operacji bulk
    bulk_operation_started = pyqtSignal(str, int)  # Typ operacji, liczba elementów
    bulk_operation_progress = pyqtSignal(int, int)  # Postęp, całość
    bulk_operation_finished = pyqtSignal(str, bool)  # Typ operacji, sukces
    
    # Sygnały dla drag&drop
    files_dropped = pyqtSignal(list, str)  # Lista plików, folder docelowy
    
    # Sygnały dla zakładek
    tab_changed = pyqtSignal(int)  # Indeks aktywnej zakładki

    def __init__(self):
        super().__init__()
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[Dict[str, Any]] = []
        self._max_history = 100

    def subscribe(self, event_type: str, callback: Callable):
        """
        Subskrybuje zdarzenie.
        
        Args:
            event_type: Typ zdarzenia (nazwa sygnału)
            callback: Funkcja callback do wywołania
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            logger.debug(f"Subskrybowano {event_type} -> {callback.__name__}")

    def unsubscribe(self, event_type: str, callback: Callable):
        """Usuwa subskrypcję zdarzenia."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"Usunięto subskrypcję {event_type} -> {callback.__name__}")
            except ValueError:
                pass

    def emit_event(self, event_type: str, *args, **kwargs):
        """
        Emituje zdarzenie do wszystkich subskrybentów.
        
        Args:
            event_type: Typ zdarzenia
            *args: Argumenty pozycyjne
            **kwargs: Argumenty nazwane
        """
        # Zapisz w historii
        self._record_event(event_type, args, kwargs)
        
        # Emituj sygnał PyQt
        if hasattr(self, event_type):
            signal = getattr(self, event_type)
            try:
                if args:
                    signal.emit(*args)
                else:
                    signal.emit()
            except Exception as e:
                logger.error(f"Błąd emitowania sygnału {event_type}: {e}")
        
        # Wywołaj callback subskrybentów
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Błąd w callback {callback.__name__} dla {event_type}: {e}")

    def _record_event(self, event_type: str, args: tuple, kwargs: dict):
        """Zapisuje zdarzenie w historii."""
        event_record = {
            "type": event_type,
            "args": args,
            "kwargs": kwargs,
            "timestamp": self.sender()  # Używamy timestamp z PyQt
        }
        
        self._event_history.append(event_record)
        
        # Ogranicz rozmiar historii
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

    def get_event_history(self, event_type: str = None) -> List[Dict[str, Any]]:
        """Zwraca historię zdarzeń."""
        if event_type:
            return [e for e in self._event_history if e["type"] == event_type]
        return self._event_history.copy()

    def clear_history(self):
        """Czyści historię zdarzeń."""
        self._event_history.clear()
        logger.debug("Wyczyszczono historię zdarzeń")

    def get_subscribers_count(self, event_type: str) -> int:
        """Zwraca liczbę subskrybentów dla danego typu zdarzenia."""
        return len(self._subscribers.get(event_type, []))

    def list_subscribers(self) -> Dict[str, List[str]]:
        """Zwraca mapę subskrybentów (do debugowania)."""
        result = {}
        for event_type, callbacks in self._subscribers.items():
            result[event_type] = [callback.__name__ for callback in callbacks]
        return result


# Singleton instance
_event_bus_instance = None


def get_event_bus() -> EventBus:
    """Zwraca singleton instance Event Bus."""
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBus()
    return _event_bus_instance 