"""
Factory do tworzenia progress dialogów dla operacji na plikach.
ETAP 1 refaktoryzacji file_operations_ui.py
"""

import logging
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QProgressDialog, QWidget

logger = logging.getLogger(__name__)


class ProgressDialogFactory:
    """
    Factory class odpowiedzialna za tworzenie i konfigurację progress dialogów
    dla różnych operacji na plikach.
    
    Eliminuje powtarzający się kod z file_operations_ui.py poprzez
    centralizację logiki tworzenia progress dialogów.
    """
    
    def __init__(self, parent_window: QWidget):
        """
        Initialize the factory.
        
        Args:
            parent_window: Okno nadrzędne dla dialogów
        """
        self.parent_window = parent_window
    
    def create_progress_dialog(
        self,
        operation_name: str,
        description: str,
        window_title: str,
        min_value: int = 0,
        max_value: int = 0,
        cancel_button_text: str = "Anuluj"
    ) -> QProgressDialog:
        """
        Tworzy i konfiguruje progress dialog dla operacji na plikach.
        
        Args:
            operation_name: Nazwa operacji (np. nazwa pliku)
            description: Opis wykonywanej operacji 
            window_title: Tytuł okna dialogu
            min_value: Minimalna wartość progress (domyślnie 0)
            max_value: Maksymalna wartość progress (domyślnie 0 = nieokreślony)
            cancel_button_text: Tekst przycisku anulowania
            
        Returns:
            Skonfigurowany QProgressDialog
        """
        logger.debug(f"Tworzenie progress dialog dla operacji: {operation_name}")
        
        progress_dialog = QProgressDialog(
            description,
            cancel_button_text,
            min_value,
            max_value,
            self.parent_window,
        )
        
        # Ujednolicona konfiguracja dla wszystkich progress dialogów
        progress_dialog.setWindowTitle(window_title)
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setAutoClose(True)
        progress_dialog.setAutoReset(True)
        progress_dialog.setValue(min_value)
        
        logger.debug(f"Progress dialog utworzony: {window_title}")
        return progress_dialog
    
    def create_rename_dialog(self, old_name: str, new_name: str) -> QProgressDialog:
        """
        Tworzy progress dialog dla operacji zmiany nazwy pliku.
        
        Args:
            old_name: Stara nazwa pliku
            new_name: Nowa nazwa pliku
            
        Returns:
            Skonfigurowany progress dialog
        """
        return self.create_progress_dialog(
            operation_name=old_name,
            description=f"Zmiana nazwy pliku '{old_name}' na '{new_name}'...",
            window_title="Zmiana nazwy pliku"
        )
    
    def create_delete_dialog(self, file_name: str) -> QProgressDialog:
        """
        Tworzy progress dialog dla operacji usuwania pliku.
        
        Args:
            file_name: Nazwa pliku do usunięcia
            
        Returns:
            Skonfigurowany progress dialog
        """
        return self.create_progress_dialog(
            operation_name=file_name,
            description=f"Usuwanie plików dla '{file_name}'...",
            window_title="Usuwanie plików"
        )
    
    def create_pairing_dialog(self, archive_name: str, preview_name: str) -> QProgressDialog:
        """
        Tworzy progress dialog dla operacji ręcznego parowania plików.
        
        Args:
            archive_name: Nazwa pliku archiwum
            preview_name: Nazwa pliku podglądu
            
        Returns:
            Skonfigurowany progress dialog
        """
        return self.create_progress_dialog(
            operation_name=f"{archive_name} + {preview_name}",
            description=f"Parowanie '{archive_name}' z '{preview_name}'...",
            window_title="Ręczne parowanie plików"
        )
    
    def create_move_dialog(self, file_name: str, target_folder: str) -> QProgressDialog:
        """
        Tworzy progress dialog dla operacji przenoszenia pliku.
        
        Args:
            file_name: Nazwa pliku do przeniesienia
            target_folder: Nazwa folderu docelowego
            
        Returns:
            Skonfigurowany progress dialog
        """
        return self.create_progress_dialog(
            operation_name=file_name,
            description=f"Przenoszenie '{file_name}' do folderu '{target_folder}'...",
            window_title="Przenoszenie plików"
        ) 