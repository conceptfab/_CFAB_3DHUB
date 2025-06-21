"""
Event handler dla drzewa katalogów.
Obsługuje zdarzenia Qt i interakcje użytkownika.
"""

import logging
import os
from PyQt6.QtCore import QModelIndex, Qt
from PyQt6.QtWidgets import QInputDialog, QMenu, QMessageBox

logger = logging.getLogger(__name__)


class DirectoryTreeEventHandler:
    """Obsługa zdarzeń dla drzewa katalogów."""

    def __init__(self, manager):
        self.manager = manager

    def handle_item_clicked(self, proxy_index: QModelIndex):
        """Obsługa kliknięcia w element drzewa."""
        try:
            if not proxy_index.isValid():
                return

            # Mapuj proxy index na source index
            source_index = self.manager.proxy_model.mapToSource(proxy_index)
            if not source_index.isValid():
                return

            # Pobierz ścieżkę folderu
            folder_path = self.manager.model.filePath(source_index)
            if folder_path and os.path.isdir(folder_path):
                # Sygnalizuj głównemu oknu zmianę katalogu
                if hasattr(self.manager.parent_window, "change_directory"):
                    self.manager.parent_window.change_directory(folder_path)
        except Exception as e:
            logger.error(f"Błąd obsługi kliknięcia folderu: {e}")

    def handle_item_expanded(self, proxy_index: QModelIndex):
        """Obsługa rozwinięcia elementu."""
        try:
            if not proxy_index.isValid():
                return

            source_index = self.manager.proxy_model.mapToSource(proxy_index)
            if not source_index.isValid():
                return

            folder_path = self.manager.model.filePath(source_index)
            if folder_path:
                # Rozpocznij obliczanie statystyk dla rozwiniętego folderu
                self.manager._calculate_stats_async_silent(folder_path)
                
                logger.debug(f"Rozwinięto folder: {folder_path}")
        except Exception as e:
            logger.error(f"Błąd obsługi rozwinięcia folderu: {e}")

    def handle_context_menu(self, position):
        """Obsługa menu kontekstowego."""
        try:
            index = self.manager.folder_tree.indexAt(position)
            if not index.isValid():
                return

            source_index = self.manager.proxy_model.mapToSource(index)
            if not source_index.isValid():
                return

            folder_path = self.manager.model.filePath(source_index)
            if not folder_path:
                return

            # Deleguj do istniejącej metody managera
            self.manager.show_folder_context_menu(position)
            
        except Exception as e:
            logger.error(f"Błąd obsługi menu kontekstowego: {e}")

    def handle_double_click(self, proxy_index: QModelIndex):
        """Obsługa podwójnego kliknięcia - otwiera folder w eksploratorze."""
        try:
            if not proxy_index.isValid():
                return

            source_index = self.manager.proxy_model.mapToSource(proxy_index)
            if not source_index.isValid():
                return

            folder_path = self.manager.model.filePath(source_index)
            if folder_path and os.path.isdir(folder_path):
                self.manager.open_folder_in_explorer(folder_path)
                
        except Exception as e:
            logger.error(f"Błąd obsługi podwójnego kliknięcia: {e}") 