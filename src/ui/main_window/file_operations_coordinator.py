"""
FileOperationsCoordinator - koordynacja operacji na plikach.
🚀 ETAP 1: Refaktoryzacja MainWindow - komponent operacji na plikach
"""

import logging
import os
from typing import List

from PyQt6.QtWidgets import QMessageBox, QFileDialog

from src.ui.delegates.workers import BulkMoveWorker
from src.ui.file_operations_ui import FileOperationsUI


class FileOperationsCoordinator:
    """
    Koordynacja operacji na plikach.
    🚀 ETAP 1: Wydzielony z MainWindow
    """

    def __init__(self, main_window):
        """
        Inicjalizuje FileOperationsCoordinator.
        
        Args:
            main_window: Referencja do głównego okna
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
        # FileOperationsUI dla operacji na plikach
        self.file_operations_ui = None

    def _ensure_file_operations_ui(self):
        """Zapewnia że FileOperationsUI jest zainicjalizowane."""
        if self.file_operations_ui is None:
            self.file_operations_ui = FileOperationsUI(self.main_window)

    def perform_bulk_delete(self):
        """Wykonuje masowe usuwanie zaznaczonych plików."""
        try:
            # Pobierz zaznaczone pary plików
            selected_pairs = self._get_selected_file_pairs()
            
            if not selected_pairs:
                QMessageBox.information(
                    self.main_window,
                    "Brak zaznaczenia",
                    "Nie zaznaczono żadnych plików do usunięcia."
                )
                return
            
            # Potwierdź operację
            if not self._confirm_bulk_delete(len(selected_pairs)):
                return
            
            self.logger.info(f"Rozpoczynanie masowego usuwania {len(selected_pairs)} par plików")
            
            # Pokaż postęp
            if hasattr(self.main_window, 'progress_manager'):
                self.main_window.progress_manager.show_processing_progress(
                    "Usuwanie plików", 0, len(selected_pairs)
                )
            
            # Deleguj do FileOperationsUI
            self._ensure_file_operations_ui()
            self.file_operations_ui.start_delete_operation(selected_pairs)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas masowego usuwania: {e}")
            QMessageBox.critical(
                self.main_window,
                "Błąd usuwania",
                f"Wystąpił błąd podczas usuwania plików:\n\n{str(e)}"
            )

    def perform_bulk_move(self):
        """Wykonuje masowe przenoszenie zaznaczonych plików."""
        try:
            # Pobierz zaznaczone pary plików
            selected_pairs = self._get_selected_file_pairs()
            
            if not selected_pairs:
                QMessageBox.information(
                    self.main_window,
                    "Brak zaznaczenia",
                    "Nie zaznaczono żadnych plików do przeniesienia."
                )
                return
            
            # Wybierz folder docelowy
            target_folder = self._select_target_folder()
            if not target_folder:
                return
            
            self.logger.info(f"Rozpoczynanie masowego przenoszenia {len(selected_pairs)} par plików do {target_folder}")
            
            # Pokaż postęp
            if hasattr(self.main_window, 'progress_manager'):
                self.main_window.progress_manager.show_processing_progress(
                    "Przenoszenie plików", 0, len(selected_pairs)
                )
            
            # Deleguj do FileOperationsUI
            self._ensure_file_operations_ui()
            self.file_operations_ui.start_move_operation(selected_pairs, target_folder)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas masowego przenoszenia: {e}")
            QMessageBox.critical(
                self.main_window,
                "Błąd przenoszenia",
                f"Wystąpił błąd podczas przenoszenia plików:\n\n{str(e)}"
            )

    def handle_file_drop_on_folder(self, source_file_paths: List[str], target_folder_path: str):
        """
        Obsługuje przeciągnięcie plików na folder.
        
        Args:
            source_file_paths: Lista ścieżek plików źródłowych
            target_folder_path: Ścieżka folderu docelowego
        """
        try:
            if not source_file_paths:
                return
            
            self.logger.info(f"Przeciągnięto {len(source_file_paths)} plików na folder {target_folder_path}")
            
            # Sprawdź czy folder docelowy istnieje
            if not os.path.exists(target_folder_path) or not os.path.isdir(target_folder_path):
                QMessageBox.warning(
                    self.main_window,
                    "Błąd folderu",
                    f"Folder docelowy nie istnieje:\n{target_folder_path}"
                )
                return
            
            # Potwierdź operację
            reply = QMessageBox.question(
                self.main_window,
                "Potwierdź przeniesienie",
                f"Czy chcesz przenieść {len(source_file_paths)} plików do folderu:\n{target_folder_path}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Pokaż postęp
            if hasattr(self.main_window, 'progress_manager'):
                self.main_window.progress_manager.show_processing_progress(
                    "Przenoszenie plików", 0, len(source_file_paths)
                )
            
            # Utwórz worker do przenoszenia
            self._create_move_worker(source_file_paths, target_folder_path)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi przeciągnięcia plików: {e}")
            QMessageBox.critical(
                self.main_window,
                "Błąd operacji",
                f"Wystąpił błąd podczas przenoszenia plików:\n\n{str(e)}"
            )

    def _get_selected_file_pairs(self):
        """
        Pobiera listę zaznaczonych par plików.
        
        Returns:
            Lista zaznaczonych par plików
        """
        try:
            selected_pairs = []
            
            # Sprawdź w galerii
            if hasattr(self.main_window, 'gallery_tab') and hasattr(self.main_window.gallery_tab, 'get_selected_pairs'):
                gallery_selected = self.main_window.gallery_tab.get_selected_pairs()
                if gallery_selected:
                    selected_pairs.extend(gallery_selected)
            
            return selected_pairs
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania zaznaczonych par: {e}")
            return []

    def _confirm_bulk_delete(self, count: int) -> bool:
        """
        Potwierdza masowe usuwanie.
        
        Args:
            count: Liczba plików do usunięcia
            
        Returns:
            True jeśli użytkownik potwierdził
        """
        try:
            reply = QMessageBox.question(
                self.main_window,
                "Potwierdź usunięcie",
                f"Czy na pewno chcesz usunąć {count} par plików?\n\n"
                "Ta operacja jest nieodwracalna!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            return reply == QMessageBox.StandardButton.Yes
            
        except Exception as e:
            self.logger.error(f"Błąd podczas potwierdzania usunięcia: {e}")
            return False

    def _select_target_folder(self) -> str:
        """
        Wybiera folder docelowy dla operacji przenoszenia.
        
        Returns:
            Ścieżka wybranego folderu lub pusty string
        """
        try:
            # Pobierz aktualny katalog roboczy jako domyślny
            default_dir = ""
            if hasattr(self.main_window, 'app_config'):
                default_dir = self.main_window.app_config.get("default_working_directory", "")
            
            folder = QFileDialog.getExistingDirectory(
                self.main_window,
                "Wybierz folder docelowy",
                default_dir
            )
            
            return folder
            
        except Exception as e:
            self.logger.error(f"Błąd podczas wyboru folderu docelowego: {e}")
            return ""

    def _create_move_worker(self, source_paths: List[str], target_folder: str):
        """
        Tworzy worker do przenoszenia plików.
        
        Args:
            source_paths: Lista ścieżek plików źródłowych
            target_folder: Folder docelowy
        """
        try:
            # Utwórz worker
            worker = BulkMoveWorker(source_paths, target_folder)
            
            # Połącz sygnały
            worker.progress.connect(self._handle_move_progress)
            worker.finished.connect(self._handle_move_finished)
            worker.error.connect(self._handle_move_error)
            
            # Uruchom w thread pool
            if hasattr(self.main_window, 'worker_manager'):
                self.main_window.worker_manager.run_worker_in_thread_pool(worker)
            elif hasattr(self.main_window, 'thread_pool'):
                self.main_window.thread_pool.start(worker)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas tworzenia workera przenoszenia: {e}")

    def _handle_move_progress(self, percent: int):
        """Obsługuje postęp przenoszenia."""
        try:
            if hasattr(self.main_window, 'progress_manager'):
                self.main_window.progress_manager.update_progress(percent)
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi postępu przenoszenia: {e}")

    def _handle_move_finished(self, result):
        """Obsługuje zakończenie przenoszenia."""
        try:
            if hasattr(self.main_window, 'progress_manager'):
                self.main_window.progress_manager.hide_progress()
            
            # Pokaż wyniki
            if isinstance(result, dict):
                moved_count = result.get('moved_count', 0)
                error_count = result.get('error_count', 0)
                
                if error_count > 0:
                    QMessageBox.warning(
                        self.main_window,
                        "Przenoszenie zakończone z błędami",
                        f"Przeniesiono: {moved_count} plików\n"
                        f"Błędy: {error_count} plików"
                    )
                else:
                    QMessageBox.information(
                        self.main_window,
                        "Przenoszenie zakończone",
                        f"Pomyślnie przeniesiono {moved_count} plików"
                    )
            
            # Odśwież widoki
            if hasattr(self.main_window, 'refresh_all_views'):
                self.main_window.refresh_all_views()
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi zakończenia przenoszenia: {e}")

    def _handle_move_error(self, error_message: str):
        """Obsługuje błąd przenoszenia."""
        try:
            if hasattr(self.main_window, 'progress_manager'):
                self.main_window.progress_manager.hide_progress()
            
            QMessageBox.critical(
                self.main_window,
                "Błąd przenoszenia",
                f"Wystąpił błąd podczas przenoszenia plików:\n\n{error_message}"
            )
            
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi błędu przenoszenia: {e}")

    def get_operations_status(self) -> dict:
        """
        Zwraca status operacji na plikach.
        
        Returns:
            Słownik ze statusem operacji
        """
        try:
            status = {
                'active_operations': 0,
                'file_operations_ui_initialized': self.file_operations_ui is not None
            }
            
            # Sprawdź aktywne operacje
            if hasattr(self.main_window, 'worker_manager'):
                status['active_operations'] = self.main_window.worker_manager.get_active_workers_count()
            
            return status
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pobierania statusu operacji: {e}")
            return {'active_operations': 0, 'file_operations_ui_initialized': False} 