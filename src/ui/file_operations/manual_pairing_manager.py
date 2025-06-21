"""
Manual Pairing Manager - ETAP 6 refaktoryzacji file_operations_ui.py
Zarządza operacjami ręcznego parowania plików.
"""

import logging
from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QListWidget, QMessageBox, QProgressDialog

from src.models.file_pair import FilePair

logger = logging.getLogger(__name__)


class ManualPairingManager:
    """
    Manager odpowiedzialny za ręczne parowanie plików.
    
    Obsługuje proces łączenia niesparowanych archiwów z podglądami
    oraz odświeżanie interfejsu po operacji.
    """
    
    def __init__(self, parent_window, progress_factory, worker_coordinator, controller):
        """
        Initialize manual pairing manager.
        
        Args:
            parent_window: Okno nadrzędne dla dialogów
            progress_factory: Factory do tworzenia dialogów postępu
            worker_coordinator: Coordinator dla workerów
            controller: FileOperationsController
        """
        self.parent_window = parent_window
        self.progress_factory = progress_factory
        self.worker_coordinator = worker_coordinator
        self.controller = controller
        
        logger.debug("ManualPairingManager zainicjalizowany")
    
    def handle_manual_pairing(
        self,
        unpaired_archives_list: QListWidget,
        unpaired_previews_list: QListWidget,
        current_working_directory: str,
    ) -> None:
        """
        Obsługuje ręczne parowanie wybranych plików.
        
        Args:
            unpaired_archives_list: Lista niesparowanych archiwów
            unpaired_previews_list: Lista niesparowanych podglądów  
            current_working_directory: Aktualny katalog roboczy
        """
        logger.debug("Rozpoczynanie ręcznego parowania plików")
        
        # Pobierz wybrane elementy
        selected_archive_items = unpaired_archives_list.selectedItems()
        selected_preview_items = unpaired_previews_list.selectedItems()

        if not selected_archive_items or not selected_preview_items:
            QMessageBox.information(
                self.parent_window,
                "Informacja",
                "Proszę wybrać archiwum z lewej listy i podgląd z prawej listy.",
            )
            return

        if len(selected_archive_items) > 1 or len(selected_preview_items) > 1:
            QMessageBox.information(
                self.parent_window,
                "Informacja",
                "Proszę wybrać tylko jeden archiwum i jeden podgląd.",
            )
            return

        # Pobierz ścieżki plików
        from PyQt6.QtCore import Qt
        archive_path = selected_archive_items[0].data(Qt.ItemDataRole.UserRole)
        preview_path = selected_preview_items[0].data(Qt.ItemDataRole.UserRole)

        if not archive_path or not preview_path:
            QMessageBox.warning(
                self.parent_window,
                "Błąd",
                "Nie można pobrać ścieżek wybranych plików.",
            )
            return

        logger.info(f"Parowanie: {archive_path} z {preview_path}")

        # Użyj controllera do utworzenia workera parowania
        worker = self.controller.manually_pair_files(
            archive_path, preview_path, current_working_directory
        )

        if worker:
            import os
            base_archive_name = os.path.basename(archive_path)
            base_preview_name = os.path.basename(preview_path)
            # Użyj progress factory
            progress_dialog = self.progress_factory.create_pairing_dialog(
                base_archive_name, base_preview_name
            )

            # Użyj worker coordinator
            self.worker_coordinator.setup_and_start_worker(
                worker=worker,
                progress_dialog=progress_dialog,
                finished_handler=lambda new_fp: self._handle_manual_pairing_finished(
                    new_fp, progress_dialog
                ),
                error_handler=lambda err_msg: self._handle_operation_error(
                    err_msg, "Błąd parowania plików", progress_dialog
                ),
                progress_handler=lambda percent, msg: self._handle_operation_progress(
                    percent, msg, progress_dialog
                ),
                interrupted_handler=lambda: self._handle_operation_interrupted(
                    "Parowanie plików przerwane.", progress_dialog
                )
            )
        else:
            QMessageBox.warning(
                self.parent_window,
                "Błąd inicjalizacji",
                "Nie można zainicjować operacji parowania plików. Sprawdź logi.",
            )
    
    def _handle_manual_pairing_finished(
        self, new_file_pair: FilePair, progress_dialog: QProgressDialog
    ):
        """
        Obsługuje zakończenie operacji ręcznego parowania.
        
        Args:
            new_file_pair: Nowo utworzona para plików
            progress_dialog: Dialog postępu
        """
        logger.info(
            f"Pomyślnie sparowano pliki. Nowa para: '{new_file_pair.get_base_name()}'"
        )
        
        if progress_dialog.isVisible():
            progress_dialog.accept()

        QMessageBox.information(
            self.parent_window,
            "Sukces",
            f"Pomyślnie sparowano pliki w parę '{new_file_pair.get_base_name()}'.",
        )

        # Thread-safe opóźnione odświeżenie
        self._delayed_refresh_after_pairing(new_file_pair)
    
    def _delayed_refresh_after_pairing(self, new_file_pair: FilePair):
        """
        Wykonuje opóźnione odświeżenie interfejsu po parowaniu w thread-safe sposób.
        
        Args:
            new_file_pair: Nowo utworzona para plików
        """
        logger.debug("Planowanie opóźnionego odświeżenia po parowaniu")
        
        # Użyj QTimer dla thread safety - wykonanie w main UI thread
        QTimer.singleShot(100, lambda: self._refresh_views_after_pairing(new_file_pair))
    
    def _refresh_views_after_pairing(self, new_file_pair: Optional[FilePair] = None):
        """
        Odświeża widoki po operacji parowania.
        
        Args:
            new_file_pair: Opcjonalna nowa para do zaznaczenia
        """
        logger.debug("Odświeżanie widoków po ręcznym parowaniu")
        
        try:
            # Dodaj nową parę do kontrolera jeśli istnieje
            if new_file_pair and hasattr(self.parent_window, "controller") and self.parent_window.controller:
                # Dodaj nową parę do listy sparowanych
                self.parent_window.controller.current_file_pairs.append(new_file_pair)
                
                # Usuń pliki z list niesparowanych
                archive_path = new_file_pair.archive_path
                preview_path = new_file_pair.preview_path
                
                try:
                    if archive_path in self.parent_window.controller.unpaired_archives:
                        self.parent_window.controller.unpaired_archives.remove(archive_path)
                except ValueError:
                    logger.debug(f"Archive już usunięte z unpaired: {archive_path}")
                
                try:
                    if preview_path in self.parent_window.controller.unpaired_previews:
                        self.parent_window.controller.unpaired_previews.remove(preview_path)
                except ValueError:
                    logger.debug(f"Preview już usunięte z unpaired: {preview_path}")
            
            # Odśwież wszystkie widoki
            if hasattr(self.parent_window, "refresh_all_views") and callable(
                self.parent_window.refresh_all_views
            ):
                try:
                    # NAPRAWKA: Nie przekazuj new_file_pair do refresh_all_views - może powodować crash
                    # Zamiast tego użyj prostego odświeżenia bez selekcji
                    self.parent_window.refresh_all_views()
                    logger.debug("Odświeżenie po parowaniu zakończone pomyślnie")
                except Exception as e:
                    logger.error(f"Błąd podczas odświeżania widoków: {e}")
                    # Fallback - spróbuj podstawowego odświeżenia
                    try:
                        if hasattr(self.parent_window, "_update_gallery_view"):
                            self.parent_window._update_gallery_view()
                        if hasattr(self.parent_window, "_update_unpaired_files_direct"):
                            self.parent_window._update_unpaired_files_direct()
                        logger.debug("Użyto fallback odświeżenia")
                    except Exception as fallback_error:
                        logger.error(f"Również fallback odświeżenie crashuje: {fallback_error}")
            else:
                logger.warning("Brak metody refresh_all_views w parent_window")
                
        except Exception as e:
            logger.error(f"KRYTYCZNY BŁĄD podczas finalizacji parowania: {e}")
            logger.warning("Pomijam refresh_all_views z powodu błędu - aplikacja powinna zostać stabilna")
    
    # === HANDLERS ===
    
    def _handle_operation_error(
        self, error_message: str, title: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje błędy operacji."""
        logger.error(f"{title}: {error_message}")
        if progress_dialog and progress_dialog.isVisible():
            progress_dialog.reject()
        QMessageBox.critical(self.parent_window, title, error_message)
        self._refresh_views_after_pairing()

    def _handle_operation_progress(
        self, percent: int, message: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje postęp operacji."""
        logger.debug(f"Postęp parowania: {percent}% - {message}")
        if progress_dialog and progress_dialog.isVisible():
            if progress_dialog.maximum() == 0:  # Nieokreślony
                progress_dialog.setLabelText(message)
            else:
                progress_dialog.setValue(percent)
                progress_dialog.setLabelText(message)

    def _handle_operation_interrupted(
        self, message: str, progress_dialog: QProgressDialog
    ):
        """Obsługuje przerwanie operacji."""
        logger.info(f"Operacja przerwana: {message}")
        if progress_dialog and progress_dialog.isVisible():
            progress_dialog.reject()
        QMessageBox.information(self.parent_window, "Operacja przerwana", message)
        self._refresh_views_after_pairing() 