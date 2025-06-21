"""
Centralny Event Bus dla komunikacji między komponentami MainWindow.
Eliminuje bezpośrednie referencje między komponentami.
"""

import logging
from typing import Callable, Dict, List

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class EventBus(QObject):
    """Centralny Event Bus dla komunikacji między komponentami"""
    
    # Sygnały dla głównych wydarzeń
    folder_selected = pyqtSignal(str)
    files_filtered = pyqtSignal(list)
    metadata_updated = pyqtSignal(str, dict)
    bulk_operation_completed = pyqtSignal(str, int)
    
    # Sygnały dla skanowania
    scan_started = pyqtSignal(str)
    scan_completed = pyqtSignal(str, list)
    scan_progress = pyqtSignal(int, str)
    
    # Sygnały dla operacji na plikach
    file_operation_started = pyqtSignal(str, str)  # operation_type, file_name
    file_operation_completed = pyqtSignal(str, str, bool)  # operation_type, file_name, success
    
    # Sygnały dla UI
    view_refresh_requested = pyqtSignal()
    gallery_refresh_requested = pyqtSignal()
    tree_refresh_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._subscribers: Dict[str, List[Callable]] = {}
        logger.debug("EventBus inicjalizowany")
    
    def subscribe(self, event: str, handler: Callable):
        """
        Subskrybuj wydarzenie.
        
        Args:
            event: Nazwa wydarzenia
            handler: Funkcja obsługująca wydarzenie
        """
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(handler)
        logger.debug(f"Zarejestrowano handler dla wydarzenia: {event}")
    
    def unsubscribe(self, event: str, handler: Callable):
        """
        Anuluj subskrypcję wydarzenia.
        
        Args:
            event: Nazwa wydarzenia
            handler: Funkcja do usunięcia
        """
        if event in self._subscribers and handler in self._subscribers[event]:
            self._subscribers[event].remove(handler)
            logger.debug(f"Usunięto handler dla wydarzenia: {event}")
    
    def emit_event(self, event: str, *args, **kwargs):
        """
        Wyślij wydarzenie do wszystkich subskrybentów.
        
        Args:
            event: Nazwa wydarzenia
            *args: Argumenty pozycyjne
            **kwargs: Argumenty nazwane
        """
        if event in self._subscribers:
            logger.debug(f"Wysyłanie wydarzenia: {event} do {len(self._subscribers[event])} subskrybentów")
            for handler in self._subscribers[event]:
                try:
                    handler(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Błąd podczas obsługi wydarzenia {event}: {e}")
    
    def emit_folder_selected(self, folder_path: str):
        """Emituj wydarzenie wyboru folderu."""
        self.folder_selected.emit(folder_path)
        self.emit_event('folder_selected', folder_path)
    
    def emit_files_filtered(self, files: list):
        """Emituj wydarzenie filtrowania plików."""
        self.files_filtered.emit(files)
        self.emit_event('files_filtered', files)
    
    def emit_metadata_updated(self, file_path: str, metadata: dict):
        """Emituj wydarzenie aktualizacji metadanych."""
        self.metadata_updated.emit(file_path, metadata)
        self.emit_event('metadata_updated', file_path, metadata)
    
    def emit_bulk_operation_completed(self, operation: str, count: int):
        """Emituj wydarzenie zakończenia operacji zbiorczej."""
        self.bulk_operation_completed.emit(operation, count)
        self.emit_event('bulk_operation_completed', operation, count)
    
    def emit_scan_started(self, directory: str):
        """Emituj wydarzenie rozpoczęcia skanowania."""
        self.scan_started.emit(directory)
        self.emit_event('scan_started', directory)
    
    def emit_scan_completed(self, directory: str, files: list):
        """Emituj wydarzenie zakończenia skanowania."""
        self.scan_completed.emit(directory, files)
        self.emit_event('scan_completed', directory, files)
    
    def emit_scan_progress(self, percent: int, message: str):
        """Emituj wydarzenie postępu skanowania."""
        self.scan_progress.emit(percent, message)
        self.emit_event('scan_progress', percent, message)
    
    def emit_file_operation_started(self, operation_type: str, file_name: str):
        """Emituj wydarzenie rozpoczęcia operacji na pliku."""
        self.file_operation_started.emit(operation_type, file_name)
        self.emit_event('file_operation_started', operation_type, file_name)
    
    def emit_file_operation_completed(self, operation_type: str, file_name: str, success: bool):
        """Emituj wydarzenie zakończenia operacji na pliku."""
        self.file_operation_completed.emit(operation_type, file_name, success)
        self.emit_event('file_operation_completed', operation_type, file_name, success)
    
    def emit_view_refresh_requested(self):
        """Emituj żądanie odświeżenia widoku."""
        self.view_refresh_requested.emit()
        self.emit_event('view_refresh_requested')
    
    def emit_gallery_refresh_requested(self):
        """Emituj żądanie odświeżenia galerii."""
        self.gallery_refresh_requested.emit()
        self.emit_event('gallery_refresh_requested')
    
    def emit_tree_refresh_requested(self):
        """Emituj żądanie odświeżenia drzewa."""
        self.tree_refresh_requested.emit()
        self.emit_event('tree_refresh_requested')
    
    def clear_all_subscriptions(self):
        """Wyczyść wszystkie subskrypcje."""
        self._subscribers.clear()
        logger.debug("Wyczyszczono wszystkie subskrypcje EventBus")


# Globalny singleton EventBus
_event_bus_instance = None


def get_event_bus() -> EventBus:
    """
    Zwraca globalną instancję EventBus (singleton).
    
    Returns:
        EventBus: Globalna instancja event bus
    """
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = EventBus()
        logger.debug("Utworzono globalną instancję EventBus")
    return _event_bus_instance


def reset_event_bus():
    """Resetuje globalną instancję EventBus (głównie do testów)."""
    global _event_bus_instance
    if _event_bus_instance:
        _event_bus_instance.clear_all_subscriptions()
    _event_bus_instance = None
    logger.debug("Zresetowano globalną instancję EventBus")