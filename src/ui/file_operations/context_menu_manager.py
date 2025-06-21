"""
Context Menu Manager dla operacji na plikach.
ETAP 3 refaktoryzacji file_operations_ui.py
"""

import logging
import os
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QListWidget, QMenu, QWidget

from src.models.file_pair import FilePair

logger = logging.getLogger(__name__)


class ContextMenuManager:
    """
    Manager odpowiedzialny za obsługę menu kontekstowych w operacjach na plikach.
    
    Separuje logikę menu kontekstowych z głównej klasy FileOperationsUI
    i zapewnia ujednolicone zachowanie dla różnych typów menu.
    """
    
    def __init__(self, parent_window: QWidget):
        """
        Initialize the manager.
        
        Args:
            parent_window: Okno nadrzędne dla menu kontekstowych
        """
        self.parent_window = parent_window
    
    def show_file_context_menu(
        self, 
        file_pair: FilePair, 
        widget: QWidget, 
        position,
        rename_callback: Callable[[FilePair, QWidget], None],
        delete_callback: Callable[[FilePair, QWidget], None]
    ) -> None:
        """
        Wyświetla menu kontekstowe dla kafelka pary plików.
        
        Args:
            file_pair: Para plików dla której pokazać menu
            widget: Widget na którym wyświetlić menu
            position: Pozycja menu (QContextMenuEvent lub QPoint)
            rename_callback: Callback dla akcji zmiany nazwy
            delete_callback: Callback dla akcji usunięcia
        """
        logger.debug(f"Wyświetlanie menu kontekstowego dla: {file_pair.get_base_name()}")
        
        menu = QMenu(self.parent_window)

        # Akcja zmiany nazwy
        rename_action = menu.addAction("Zmień nazwę")
        rename_action.triggered.connect(
            lambda: rename_callback(file_pair, widget)
        )

        # Akcja usunięcia
        delete_action = menu.addAction("Usuń")
        delete_action.triggered.connect(
            lambda: delete_callback(file_pair, widget)
        )

        # Wyświetlenie menu w odpowiedniej pozycji
        self._show_menu_at_position(menu, widget, position)
        
        logger.debug("Menu kontekstowe wyświetlone")
    
    def show_unpaired_context_menu(
        self, 
        position, 
        list_widget: QListWidget, 
        list_type: str
    ) -> None:
        """
        Wyświetla menu kontekstowe dla listy niesparowanych plików.
        
        Args:
            position: Pozycja menu
            list_widget: Widget listy
            list_type: Typ listy (dla logowania)
        """
        logger.debug(f"Wyświetlanie menu kontekstowego dla {list_type}")
        
        item = list_widget.itemAt(position)
        if not item:
            logger.debug("Brak elementu pod pozycją menu")
            return

        menu = QMenu(self.parent_window)
        open_action = menu.addAction("Otwórz lokalizację pliku")
        action = menu.exec(list_widget.mapToGlobal(position))

        if action == open_action:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            self._open_file_location(file_path)
        
        logger.debug("Menu kontekstowe dla unpaired zakończone")
    
    def _show_menu_at_position(
        self, 
        menu: QMenu, 
        widget: QWidget, 
        position
    ) -> None:
        """
        Wyświetla menu w odpowiedniej pozycji z obsługą różnych typów pozycji.
        
        Args:
            menu: Menu do wyświetlenia
            widget: Widget referencyjny
            position: Pozycja (QContextMenuEvent lub QPoint)
        """
        # Sprawdź czy position to QContextMenuEvent czy QPoint
        if hasattr(position, "pos"):
            # position to QContextMenuEvent
            global_pos = widget.mapToGlobal(position.pos())
        else:
            # position to QPoint
            global_pos = widget.mapToGlobal(position)
        
        menu.exec(global_pos)
        logger.debug(f"Menu wyświetlone na pozycji: {global_pos}")
    
    def _open_file_location(self, file_path: str) -> None:
        """
        Otwiera lokalizację pliku w eksploratorze systemu.
        
        Args:
            file_path: Ścieżka do pliku
        """
        logger.debug(f"Otwieranie lokalizacji pliku: {file_path}")
        
        try:
            # Sprawdź czy funkcja istnieje przed wywołaniem
            from src.logic import file_operations
            if hasattr(file_operations, "open_file_location"):
                file_operations.open_file_location(os.path.dirname(file_path))
                logger.debug("Lokalizacja pliku otwarta pomyślnie")
            else:
                logger.warning("Funkcja open_file_location nie została zaimplementowana")
        except Exception as e:
            logger.error(f"Błąd podczas otwierania lokalizacji pliku: {e}")
    
    def create_file_menu_actions(self) -> dict:
        """
        Tworzy słownik z dostępnymi akcjami menu dla plików.
        
        Returns:
            Słownik z nazwami akcji jako klucze
        """
        return {
            "rename": "Zmień nazwę",
            "delete": "Usuń",
            "open_location": "Otwórz lokalizację pliku"
        }
    
    def create_context_menu_with_actions(
        self, 
        actions: dict, 
        callbacks: dict
    ) -> QMenu:
        """
        Tworzy menu kontekstowe z podanymi akcjami i callbackami.
        
        Args:
            actions: Słownik akcji (klucz: nazwa akcji, wartość: tekst do wyświetlenia)
            callbacks: Słownik callbacków (klucz: nazwa akcji, wartość: funkcja callback)
            
        Returns:
            Skonfigurowane menu kontekstowe
        """
        menu = QMenu(self.parent_window)
        
        for action_key, action_text in actions.items():
            if action_key in callbacks:
                action = menu.addAction(action_text)
                action.triggered.connect(callbacks[action_key])
                logger.debug(f"Dodano akcję do menu: {action_text}")
        
        return menu 