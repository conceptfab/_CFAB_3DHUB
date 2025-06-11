"""
Event Handler - obsługa zdarzeń UI.
Refaktoryzacja MainWindow ETAP 2 - wydzielenie obsługi zdarzeń.
"""

import logging
import os
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox

logger = logging.getLogger(__name__)


class EventHandler:
    """
    Handler odpowiedzialny za obsługę zdarzeń UI.
    Wydzielony z MainWindow dla lepszej organizacji kodu.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje Event Handler.
        
        Args:
            main_window: Główne okno aplikacji (MainWindow)
        """
        self.main_window = main_window
        self.app_config = main_window.app_config
        
    def handle_folder_selection(self, directory_path: Optional[str] = None):
        """
        Obsługuje wybór folderu roboczego.
        
        Args:
            directory_path: Ścieżka do folderu (None = otwórz dialog)
        """
        if directory_path is None:
            directory_path = QFileDialog.getExistingDirectory(
                self.main_window,
                "Wybierz folder roboczy",
                self.main_window.app_config.get_default_folder_path(),
            )
            
        if not directory_path:
            return
            
        if not self._validate_directory_path(directory_path):
            return
            
        # Zapisz wybrany folder
        self.main_window.current_working_directory = directory_path
        
        # Zaktualizuj tytuł okna
        base_folder_name = os.path.basename(directory_path)
        self.main_window.setWindowTitle(f"CFAB_3DHUB - {base_folder_name}")
        
        logging.info(f"Wybrano folder roboczy: {directory_path}")
        
        # Wyczyść dane i rozpocznij skanowanie
        self.main_window._clear_all_data_and_views()
        self._start_folder_scanning()
        
    def _validate_directory_path(self, path: str) -> bool:
        """
        Waliduje ścieżkę do katalogu.
        
        Args:
            path: Ścieżka do walidacji
            
        Returns:
            bool: True jeśli ścieżka jest poprawna
        """
        if not os.path.exists(path):
            QMessageBox.warning(
                self.main_window, "Błąd", f"Podany folder nie istnieje:\n{path}"
            )
            return False
            
        if not os.path.isdir(path):
            QMessageBox.warning(
                self.main_window, "Błąd", f"Podana ścieżka nie jest folderem:\n{path}"
            )
            return False
            
        if not os.access(path, os.R_OK):
            QMessageBox.warning(
                self.main_window, "Błąd", f"Brak uprawnień do odczytu folderu:\n{path}"
            )
            return False
            
        return True
        
    def _start_folder_scanning(self):
        """
        Rozpoczyna skanowanie wybranego folderu.
        Deleguje do kontrolera MVC.
        """
        # UI Feedback
        if hasattr(self.main_window, 'select_folder_button'):
            self.main_window.select_folder_button.setText("Skanowanie...")
            self.main_window.select_folder_button.setEnabled(False)
            
        # Delegacja do kontrolera
        success = self.main_window.controller.handle_folder_selection(
            self.main_window.current_working_directory
        )
        
        # Przywróć UI state
        if hasattr(self.main_window, 'select_folder_button'):
            self.main_window.select_folder_button.setText("Wybierz Folder")
            self.main_window.select_folder_button.setEnabled(True)
            
        if success:
            logging.info(f"Controller scan SUCCESS: {self.main_window.current_working_directory}")
        else:
            logging.warning(f"Controller scan FAILED: {self.main_window.current_working_directory}")
            
    def handle_force_refresh(self):
        """
        Obsługuje wymuszenie ponownego skanowania poprzez czyszczenie cache.
        """
        if self.main_window.current_working_directory:
            from src.logic.scanner import clear_cache
            
            clear_cache()
            logging.info("Cache wyczyszczony - wymuszono ponowne skanowanie")
            self.handle_folder_selection(self.main_window.current_working_directory)
            
    def handle_thumbnail_size_update(self):
        """
        Obsługuje aktualizację rozmiaru miniatur.
        """
        if not hasattr(self.main_window, 'size_slider'):
            return
            
        value = self.main_window.size_slider.value()
        size_range = self.main_window.max_thumbnail_size - self.main_window.min_thumbnail_size
        new_size = self.main_window.min_thumbnail_size + int((size_range * value) / 100)
        
        self.main_window.current_thumbnail_size = new_size
        
        logging.debug(f"Aktualizacja rozmiaru miniatur na: {new_size}")
        
        # Zapisz pozycję suwaka do konfiguracji
        self.main_window.app_config.set_thumbnail_slider_position(value)
        
        # Zaktualizuj rozmiar w gallery managerze
        if hasattr(self.main_window, 'gallery_manager'):
            self.main_window.gallery_manager.update_thumbnail_size(new_size)
            
    def handle_bulk_selection_clear(self):
        """
        Obsługuje czyszczenie wszystkich zaznaczeń.
        """
        self.main_window.selected_tiles.clear()
        
        # Zaktualizuj wszystkie widoczne kafelki
        if hasattr(self.main_window, 'gallery_manager') and self.main_window.gallery_manager:
            for tile_widget in self.main_window.gallery_manager.get_all_tile_widgets():
                if hasattr(tile_widget, 'metadata_controls'):
                    tile_widget.metadata_controls.update_selection_display(False)
                    
        self._update_bulk_operations_visibility()
        logging.debug("Wyczyszczono wszystkie zaznaczenia kafelków")
        
    def handle_bulk_selection_all(self):
        """
        Obsługuje zaznaczenie wszystkich widocznych kafelków.
        """
        if hasattr(self.main_window, 'gallery_manager') and self.main_window.gallery_manager:
            for tile_widget in self.main_window.gallery_manager.get_all_tile_widgets():
                if hasattr(tile_widget, 'file_pair') and tile_widget.file_pair:
                    self.main_window.selected_tiles.add(tile_widget.file_pair)
                    if hasattr(tile_widget, 'metadata_controls'):
                        tile_widget.metadata_controls.update_selection_display(True)
                        
            self._update_bulk_operations_visibility()
            logging.debug(f"Zaznaczono wszystkie {len(self.main_window.selected_tiles)} widoczne kafelki")
            
    def handle_bulk_delete(self):
        """
        Obsługuje masowe usuwanie zaznaczonych kafelków.
        Deleguje do kontrolera MVC.
        """
        if not self.main_window.selected_tiles:
            QMessageBox.information(
                self.main_window,
                "Brak zaznaczenia",
                "Nie zaznaczono żadnych plików do usunięcia."
            )
            return
            
        # Potwierdź operację
        reply = QMessageBox.question(
            self.main_window,
            "Potwierdzenie usuwania",
            f"Czy na pewno chcesz usunąć {len(self.main_window.selected_tiles)} zaznaczonych plików?\n\n"
            "Ta operacja jest nieodwracalna!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        # Deleguj do kontrolera
        selected_pairs = list(self.main_window.selected_tiles)
        success = self.main_window.controller.handle_bulk_delete(selected_pairs)
        
        if success:
            # Wyczyść zaznaczenie po pomyślnym usunięciu
            self.main_window.selected_tiles.clear()
            self._update_bulk_operations_visibility()
            
            # Odśwież widok
            self.main_window._apply_filters_and_update_view()
            self.main_window._save_metadata()
            
    def handle_bulk_move(self):
        """
        Obsługuje masowe przenoszenie zaznaczonych kafelków.
        """
        if not self.main_window.selected_tiles:
            QMessageBox.information(
                self.main_window,
                "Brak zaznaczenia",
                "Nie zaznaczono żadnych plików do przeniesienia."
            )
            return
            
        # Wybierz folder docelowy
        target_folder = QFileDialog.getExistingDirectory(
            self.main_window,
            "Wybierz folder docelowy",
            self.main_window.current_working_directory or ""
        )
        
        if not target_folder:
            return
            
        # Deleguj do file operations UI
        if hasattr(self.main_window, 'file_operations_ui'):
            selected_pairs = list(self.main_window.selected_tiles)
            self.main_window.file_operations_ui.move_files_bulk(selected_pairs, target_folder)
        else:
            logging.error("FileOperationsUI nie jest zainicjalizowany")
            
    def _update_bulk_operations_visibility(self):
        """Aktualizuje widoczność panelu operacji masowych."""
        if hasattr(self.main_window, 'ui_manager'):
            self.main_window.ui_manager.update_bulk_operations_visibility()
            
    def handle_close_event(self, event):
        """
        Obsługuje zamykanie aplikacji - kończy wszystkie wątki.
        
        Args:
            event: QCloseEvent
        """
        logging.info("Rozpoczynam zamykanie aplikacji...")
        
        # Wyczyść wątki
        self._cleanup_threads()
        
        # Zakceptuj zdarzenie zamknięcia
        event.accept()
        logging.info("Aplikacja została zamknięta.")
        
    def _cleanup_threads(self):
        """
        Czyści wszystkie aktywne wątki.
        """
        # Użyj ThreadCoordinator jeśli dostępny
        if hasattr(self.main_window, 'thread_coordinator'):
            self.main_window.thread_coordinator.cleanup_all_threads()
        else:
            # Fallback - stary sposób dla kompatybilności
            if hasattr(self.main_window, 'scan_thread') and self.main_window.scan_thread and self.main_window.scan_thread.isRunning():
                logging.info("Kończenie wątku skanowania przy zamykaniu aplikacji...")
                self.main_window.scan_thread.quit()
                if not self.main_window.scan_thread.wait(1000):
                    logging.warning("Wątek skanowania nie zakończył się, wymuszam...")
                    self.main_window.scan_thread.terminate()
                    self.main_window.scan_thread.wait()
                    
            if hasattr(self.main_window, 'data_processing_thread') and self.main_window.data_processing_thread and self.main_window.data_processing_thread.isRunning():
                logging.info("Kończenie wątku przetwarzania przy zamykaniu aplikacji...")
                self.main_window.data_processing_thread.quit()
                if not self.main_window.data_processing_thread.wait(1000):
                    logging.warning("Wątek przetwarzania nie zakończył się, wymuszam...")
                    self.main_window.data_processing_thread.terminate()
                    self.main_window.data_processing_thread.wait()
