"""
MainWindowController - centralny kontroler dla głównego okna aplikacji.
Implementacja wzorca MVC - separacja logiki biznesowej od UI.
ZREFAKTORYZOWANY - usunięto problemy z dokumentacją correction_KRYTYCZNY_main_window_controller.md
"""

import logging
import os
from typing import List, Optional

from PyQt6.QtWidgets import QMessageBox

from src.controllers.scan_result_processor import ScanResultProcessor
from src.controllers.selection_manager import SelectionManager
from src.controllers.special_folders_manager import SpecialFoldersManager
from src.models.file_pair import FilePair
from src.services.file_operations_service import FileOperationsService
from src.services.scanning_service import ScanningService, ScanResult


class MainWindowController:
    """
    Kontroler głównego okna - koordynuje logikę biznesową.
    Separacja odpowiedzialności: View -> Controller -> Services.
    """

    def __init__(self, view):
        """
        Inicjalizuje kontroler.

        Args:
            view: MainWindow (widok) - będzie ustawiony po imporcie
        """
        self.view = view  # MainWindow
        self.logger = logging.getLogger(__name__)

        # Serwisy biznesowe
        self.file_service = FileOperationsService()
        self.scan_service = ScanningService()

        # Wydzielone managery (ETAP 1.1: Podział odpowiedzialności)
        self.special_folders_manager = SpecialFoldersManager()
        self.selection_manager = SelectionManager()
        self.scan_processor = ScanResultProcessor()

        # Stan aplikacji
        self.current_directory: Optional[str] = None
        self.current_file_pairs: List[FilePair] = []
        self.unpaired_archives: List[str] = []
        self.unpaired_previews: List[str] = []
        self.special_folders: List = []

    def handle_folder_selection(self, directory_path: str):
        """
        Obsługuje wybór folderu roboczego przez uruchomienie asynchronicznego skanowania.
        """
        try:
            errors = self.scan_service.validate_directory_path(directory_path)
            if errors:
                error_msg = "Błędy walidacji folderu:\n" + "\n".join(errors)
                self.view.show_error_message("Błąd folderu", error_msg)
                return

            self.view.worker_manager.start_directory_scan_worker(directory_path)

        except Exception as e:
            error_msg = f"Nieoczekiwany błąd podczas uruchamiania skanowania: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.view.show_error_message("Błąd Krytyczny", error_msg)
            self.view._hide_progress()

    def _on_scan_worker_finished(self, scan_result: ScanResult):
        """
        Callback wywoływany po zakończeniu pracy przez ScanDirectoryWorker.
        ZREFAKTORYZOWANY - używa nowych managerów.
        """
        if scan_result.error_message:
            self.view.show_error_message("Błąd skanowania", scan_result.error_message)
            self.view._hide_progress()
            return

        # Użyj ScanResultProcessor do przetworzenia wyniku
        processed_data = self.scan_processor.process_scan_result(scan_result)

        # Aktualizuj stan aplikacji
        self.current_directory = processed_data["directory_path"]
        self.current_file_pairs = processed_data["file_pairs"]
        self.unpaired_archives = processed_data["unpaired_archives"]
        self.unpaired_previews = processed_data["unpaired_previews"]
        self.special_folders = processed_data["special_folders"]

        # Integracja ze specjalnymi folderami z metadanych
        if self.current_directory:
            metadata_folders = (
                self.special_folders_manager.get_special_folders_from_metadata(
                    self.current_directory
                )
            )
            if metadata_folders:
                self.special_folders.extend(metadata_folders)

        # Powiadom UI
        self.view.update_scan_results(scan_result)
        stats = processed_data["statistics"]
        self.view._show_progress(100, f"Znaleziono {stats['total_pairs']} par")

        self.logger.info(
            f"Skanowanie ukończone: {stats['total_pairs']} par, "
            f"{stats['unpaired_archives_count']} archiwów, "
            f"{stats['unpaired_previews_count']} podglądów, "
            f"{len(self.special_folders)} specjalnych folderów"
        )

    def handle_bulk_delete(self, selected_pairs: List[FilePair]) -> bool:
        """
        Obsługuje masowe usuwanie plików.

        Args:
            selected_pairs: Lista par plików do usunięcia

        Returns:
            bool: True jeśli operacja się powiodła
        """
        if not selected_pairs:
            self.view.show_info_message("Info", "Nie wybrano plików do usunięcia")
            return False

        # Potwierdzenie od użytkownika
        if not self.view.confirm_bulk_delete(len(selected_pairs)):
            return False

        try:
            self.view._show_progress(0, f"Usuwanie {len(selected_pairs)} par plików...")

            # Deleguj do serwisu
            deleted_pairs, errors = self.file_service.bulk_delete(selected_pairs)

            # Aktualizuj stan
            self._remove_pairs_from_state(deleted_pairs)

            # Powiadom UI
            self.view.update_after_bulk_operation(deleted_pairs, "usunięto")
            self.view._show_progress(100, f"Usunięto {len(deleted_pairs)} par plików")

            # Pokaż błędy jeśli były
            if errors:
                self._show_operation_errors("usuwania", errors)

            self.logger.info(f"Bulk delete: usunięto {len(deleted_pairs)} par")
            return True

        except Exception as e:
            error_msg = f"Błąd masowego usuwania: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error_message("Błąd usuwania", error_msg)
            self.view._hide_progress()
            return False

    def handle_bulk_move(
        self, selected_pairs: List[FilePair], destination: str
    ) -> bool:
        """
        Obsługuje masowe przenoszenie plików.

        Args:
            selected_pairs: Lista par plików do przeniesienia
            destination: Katalog docelowy

        Returns:
            bool: True jeśli operacja się powiodła
        """
        if not selected_pairs:
            self.view.show_info_message("Info", "Nie wybrano plików do przeniesienia")
            return False

        try:
            self.view._show_progress(
                0, f"Przenoszenie {len(selected_pairs)} par plików..."
            )

            # Deleguj do serwisu
            moved_pairs, errors = self.file_service.bulk_move(
                selected_pairs, destination
            )

            # Aktualizuj stan
            self._remove_pairs_from_state(
                [p for p in selected_pairs if p in moved_pairs]
            )

            # Powiadom UI
            self.view.update_after_bulk_operation(moved_pairs, "przeniesiono")
            self.view._show_progress(100, f"Przeniesiono {len(moved_pairs)} par plików")

            # Pokaż błędy jeśli były
            if errors:
                self._show_operation_errors("przenoszenia", errors)

            self.logger.info(
                f"Bulk move: przeniesiono {len(moved_pairs)} par do {destination}"
            )
            return True

        except Exception as e:
            error_msg = f"Błąd masowego przenoszenia: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error_message("Błąd przenoszenia", error_msg)
            self.view._hide_progress()
            return False

    def handle_manual_pairing(self, archive_path: str, preview_path: str) -> bool:
        """
        Obsługuje ręczne parowanie plików.

        Args:
            archive_path: Ścieżka do pliku archiwum
            preview_path: Ścieżka do pliku podglądu

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            # Deleguj do serwisu
            new_pair = self.file_service.create_manual_pair(
                archive_path, preview_path, self.current_directory or ""
            )

            if new_pair:
                # Aktualizuj stan
                self.current_file_pairs.append(new_pair)

                # Usuń z list niesparowanych
                if archive_path in self.unpaired_archives:
                    self.unpaired_archives.remove(archive_path)
                if preview_path in self.unpaired_previews:
                    self.unpaired_previews.remove(preview_path)

                # Powiadom UI
                self.view.update_after_manual_pairing(new_pair)

                self.logger.info(f"Utworzono parę ręcznie: {new_pair}")
                return True

            return False

        except Exception as e:
            error_msg = f"Błąd ręcznego parowania: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error_message("Błąd parowania", error_msg)
            return False

    def handle_tile_selection(self, file_pair: FilePair, is_selected: bool):
        """
        Obsługuje zaznaczanie/odznaczanie kafelków.
        ZREFAKTORYZOWANY - deleguje do SelectionManager.

        Args:
            file_pair: Para plików
            is_selected: Czy kafelek ma być zaznaczony
        """
        self.selection_manager.handle_tile_selection(file_pair, is_selected)

    def handle_refresh_request(self, force_full: bool = False):
        """
        Obsługuje żądanie odświeżenia widoku.

        Args:
            force_full: Czy wykonać pełne odświeżenie
        """
        try:
            if force_full or not self.current_directory:
                self.view.clear_all_data_and_views()
                return

            # Odśwież bieżący katalog
            self.handle_folder_selection(self.current_directory)

        except Exception as e:
            self.logger.error(f"Błąd odświeżania: {str(e)}")
            self.view.show_error_message("Błąd odświeżania", str(e))

    def handle_metadata_change(self, file_pair: FilePair, field: str, value):
        """
        Obsługuje zmianę metadanych par plików.

        Args:
            file_pair: Para plików
            field: Nazwa pola metadanych
            value: Nowa wartość
        """
        try:
            # Aktualizuj pole w obiekcie
            if hasattr(file_pair, field):
                setattr(file_pair, field, value)
                self.logger.debug(f"Zaktualizowano {field} dla {file_pair}")

                # Powiadom UI o zmianie
                self.view.update_metadata_display(file_pair, field, value)
            else:
                self.logger.warning(f"Nieznane pole metadanych: {field}")

        except Exception as e:
            self.logger.error(f"Błąd zmiany metadanych: {str(e)}")

    def get_scan_statistics(self) -> dict:
        """
        Zwraca statystyki aktualnego skanowania.

        Returns:
            dict: Statystyki
        """
        return {
            "current_directory": self.current_directory,
            "total_pairs": len(self.current_file_pairs),
            "selected_pairs": self.selection_manager.get_selection_count(),
            "unpaired_archives": len(self.unpaired_archives),
            "unpaired_previews": len(self.unpaired_previews),
            "scan_service_stats": self.scan_service.get_scan_statistics(
                self.current_directory or ""
            ),
        }

    def _remove_pairs_from_state(self, pairs_to_remove: List[FilePair]):
        """Usuwa pary ze stanu aplikacji."""
        for pair in pairs_to_remove:
            if pair in self.current_file_pairs:
                self.current_file_pairs.remove(pair)

        # Deleguj do SelectionManager
        self.selection_manager.remove_pairs_from_selection(pairs_to_remove)

    def _show_operation_errors(self, operation_name: str, errors: List[str]):
        """Pokazuje błędy operacji użytkownikowi."""
        if not errors:
            return

        error_msg = f"Błędy podczas {operation_name}:\n\n"

        # Pokaż maksymalnie 5 błędów
        shown_errors = errors[:5]
        error_msg += "\n".join(shown_errors)

        if len(errors) > 5:
            error_msg += f"\n\n... i {len(errors) - 5} więcej błędów"

        self.view.show_warning_message(f"Błędy {operation_name}", error_msg)

    def clear_all_data_and_views(self):
        """
        Czyści stan aplikacji i informuje UI o potrzebie odświeżenia.
        """
        self.current_file_pairs = []
        self.unpaired_archives = []
        self.unpaired_previews = []
        self.special_folders = []

        # Wyczyść selekcję przez SelectionManager
        self.selection_manager.clear_selection()

        # Informuj UI o czyszczeniu
        self.view.gallery_manager.clear_gallery()
        self.view.filter_panel.setEnabled(False)
        self.view.setWindowTitle("CFAB_3DHUB")

        self.logger.debug("Stan aplikacji wyczyszczony")

    def scan_folder_for_pairs(self, folder_path: str, max_depth: int = 1) -> ScanResult:
        """
        Skanuje folder w poszukiwaniu par plików.
        ZREFAKTORYZOWANY - używa SpecialFoldersManager.

        Args:
            folder_path: Ścieżka do folderu
            max_depth: Maksymalna głębokość rekurencji

        Returns:
            Wynik skanowania
        """
        self.logger.info(f"Skanowanie folderu: {folder_path} (max_depth={max_depth})")

        try:
            # Skanowanie folderu
            scan_result = self.scan_service.scan_directory(folder_path, max_depth)

            # Użyj SpecialFoldersManager dla obsługi specjalnych folderów
            special_folders = (
                self.special_folders_manager.ensure_tex_folder_in_metadata(folder_path)
            )

            # Zaktualizuj wynik skanowania
            scan_result.special_folders = special_folders

            # Ustaw specjalne foldery w kontrolerze
            self.special_folders = special_folders

            self.logger.info(
                f"Ustawiono {len(special_folders)} specjalnych folderów w kontrolerze"
            )
            return scan_result

        except Exception as e:
            self.logger.error(f"Błąd skanowania folderu: {str(e)}")
            # Zwróć pusty wynik z błędem
            return ScanResult(
                directory_path=folder_path,
                file_pairs=[],
                unpaired_archives=[],
                unpaired_previews=[],
                special_folders=[],
                error_message=str(e),
            )
