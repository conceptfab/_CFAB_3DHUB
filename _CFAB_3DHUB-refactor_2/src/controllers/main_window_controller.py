"""
MainWindowController - centralny kontroler dla głównego okna aplikacji.
Implementacja wzorca MVC - separacja logiki biznesowej od UI.
Problem #1 Etap 2 - dokończenie refaktoryzacji.
"""

import logging
from typing import List, Optional

from PyQt6.QtWidgets import QMessageBox

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

        # Stan aplikacji
        self.current_directory: Optional[str] = None
        self.current_file_pairs: List[FilePair] = []
        self.selected_tiles: set[FilePair] = set()
        self.unpaired_archives: List[str] = []
        self.unpaired_previews: List[str] = []

    def handle_folder_selection(self, directory_path: str) -> bool:
        """
        Obsługuje wybór folderu roboczego.

        Args:
            directory_path: Ścieżka do wybranego folderu

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            # Walidacja ścieżki
            errors = self.scan_service.validate_directory_path(directory_path)
            if errors:
                error_msg = "Błędy walidacji folderu:\n" + "\n".join(errors)
                self.view.show_error_message("Błąd folderu", error_msg)
                return False

            # Informuj UI o rozpoczęciu skanowania
            self.view._show_progress(0, f"Skanowanie: {directory_path}")

            # Wykonaj skanowanie przez serwis
            scan_result = self.scan_service.scan_directory(directory_path)

            if scan_result.error_message:
                self.view.show_error_message(
                    "Błąd skanowania", scan_result.error_message
                )
                self.view._hide_progress()
                return False

            # Zaktualizuj stan aplikacji
            self.current_directory = directory_path
            self.current_file_pairs = scan_result.file_pairs
            self.unpaired_archives = scan_result.unpaired_archives
            self.unpaired_previews = scan_result.unpaired_previews

            # Powiadom UI o wynikach
            self.view.update_scan_results(scan_result)
            self.view._show_progress(
                100, f"Znaleziono {len(scan_result.file_pairs)} par"
            )

            self.logger.info(
                f"Skanowanie ukończone: {len(scan_result.file_pairs)} par, "
                f"{len(scan_result.unpaired_archives)} archiwów, "
                f"{len(scan_result.unpaired_previews)} podglądów"
            )

            return True

        except Exception as e:
            error_msg = f"Nieoczekiwany błąd skanowania: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error_message("Błąd", error_msg)
            self.view._hide_progress()
            return False

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
            self.view._show_progress(0, f"Usuwanie {len(selected_pairs)} plików...")

            # Deleguj do serwisu
            deleted_pairs, errors = self.file_service.bulk_delete(selected_pairs)

            # Aktualizuj stan
            self._remove_pairs_from_state(deleted_pairs)

            # Powiadom UI
            self.view.update_after_bulk_operation(deleted_pairs, "usunięto")
            self.view._show_progress(100, f"Usunięto {len(deleted_pairs)} plików")

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
            self.view._show_progress(0, f"Przenoszenie {len(selected_pairs)} plików...")

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
            self.view._show_progress(100, f"Przeniesiono {len(moved_pairs)} plików")

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
            archive_path: Ścieżka do archiwum
            preview_path: Ścieżka do podglądu

        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            # Deleguj do serwisu
            new_pair = self.file_service.manual_pair(archive_path, preview_path)

            if not new_pair:
                self.view.show_error_message("Błąd", "Nie można utworzyć pary plików")
                return False

            # Dodaj do stanu
            self.current_file_pairs.append(new_pair)

            # Usuń z niesparowanych
            if archive_path in self.unpaired_archives:
                self.unpaired_archives.remove(archive_path)
            if preview_path in self.unpaired_previews:
                self.unpaired_previews.remove(preview_path)

            # Powiadom UI
            self.view.add_new_pair(new_pair)
            self.view.update_unpaired_lists(
                self.unpaired_archives, self.unpaired_previews
            )

            self.logger.info(f"Ręczne parowanie: {new_pair.name}")
            return True

        except Exception as e:
            error_msg = f"Błąd ręcznego parowania: {str(e)}"
            self.logger.error(error_msg)
            self.view.show_error_message("Błąd parowania", error_msg)
            return False

    def handle_tile_selection(self, file_pair: FilePair, is_selected: bool):
        """
        Obsługuje zmianę selekcji kafelka.

        Args:
            file_pair: Para plików
            is_selected: Czy kafelek jest zaznaczony
        """
        if is_selected:
            self.selected_tiles.add(file_pair)
        else:
            self.selected_tiles.discard(file_pair)

        # Powiadom UI o zmianie selekcji
        self.view.update_bulk_operations_visibility(len(self.selected_tiles))

        self.logger.debug(f"Selekcja: {len(self.selected_tiles)} kafelków")

    def handle_refresh_request(self, force_full: bool = False):
        """
        Obsługuje żądanie odświeżenia widoku.

        Args:
            force_full: Czy wymusić pełne ponowne skanowanie
        """
        if not self.current_directory:
            return

        if force_full:
            # Wyczyść cache i przeskanuj ponownie
            self.scan_service.clear_all_caches()

        # Ponowne skanowanie
        self.handle_folder_selection(self.current_directory)

    def handle_metadata_change(self, file_pair: FilePair, field: str, value):
        """
        Obsługuje zmianę metadanych pary plików.

        Args:
            file_pair: Para plików
            field: Nazwa pola (rating, color, description)
            value: Nowa wartość
        """
        try:
            if field == "rating":
                file_pair.set_stars(value)
            elif field == "color":
                file_pair.set_color_tag(value)
            elif field == "description":
                file_pair.description = value

            # Powiadom UI o potrzebie zapisu metadanych
            self.view.request_metadata_save()

            self.logger.debug(f"Metadane: {file_pair.name} - {field} = {value}")

        except Exception as e:
            self.logger.error(f"Błąd zmiany metadanych: {str(e)}")

    def get_scan_statistics(self) -> dict:
        """
        Zwraca statystyki skanowania.

        Returns:
            dict: Statystyki
        """
        return {
            "current_directory": self.current_directory,
            "total_pairs": len(self.current_file_pairs),
            "selected_pairs": len(self.selected_tiles),
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
            self.selected_tiles.discard(pair)

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
