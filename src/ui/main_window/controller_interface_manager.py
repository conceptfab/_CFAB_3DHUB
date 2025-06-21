"""
ControllerInterfaceManager - interface komunikacji z kontrolerem.
🚀 ETAP 7 REFAKTORYZACJI: Wydzielenie interface MVC z main_window.py
"""

import logging
from typing import List

from src.models.file_pair import FilePair


class ControllerInterfaceManager:
    """
    Manager odpowiedzialny za standaryzację komunikacji z kontrolerem.
    Implementuje wzorzec MVC - View komunikuje się z Controller przez ten interface.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje ControllerInterfaceManager.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def update_scan_results(self, scan_result):
        """
        Aktualizuje UI wynikami skanowania z kontrolera.

        Args:
            scan_result: Wyniki skanowania z kontrolera
        """
        # UWAGA: Controller już zaktualizował swój stan w handle_folder_selection()
        # NIE wywołujemy controller.handle_scan_finished() aby nie nadpisać danych!

        # Wyczyść poprzednie widgety
        self.main_window.gallery_manager.clear_gallery()

        # Utwórz nowe kafelki
        if scan_result.file_pairs:
            # Użyj nowej, zoptymalizowanej metody z TileManager
            self.main_window.tile_manager.start_tile_creation(scan_result.file_pairs)
        else:
            self.main_window._on_tile_loading_finished()

        # UWAGA: update_unpaired_files_lists() jest już wywoływana w _on_tile_loading_finished()
        # Nie wywołujemy tutaj aby uniknąć błędów z niezainicjalizowanymi widgetami

    def confirm_bulk_delete(self, count: int) -> bool:
        """
        Potwierdza operację masowego usuwania - delegacja do BulkOperationsManager.

        Args:
            count: Liczba elementów do usunięcia

        Returns:
            True jeśli użytkownik potwierdził operację
        """
        return self.main_window.bulk_operations_manager.confirm_bulk_delete(count)

    def update_after_bulk_operation(
        self, processed_pairs: List[FilePair], operation_name: str
    ):
        """
        Aktualizuje UI po operacji bulk.

        Args:
            processed_pairs: Lista przetworzonych par plików
            operation_name: Nazwa operacji (do wyświetlenia)
        """
        # Usuń z galerii
        for pair in processed_pairs:
            self.main_window.gallery_manager.remove_tile_for_pair(pair)

        # Aktualizuj widok
        self.main_window.refresh_all_views()

        # Status bar
        if hasattr(self.main_window, "status_bar"):
            self.main_window.status_bar.showMessage(
                f"Operacja {operation_name}: {len(processed_pairs)} plików"
            )

    def update_bulk_operations_visibility(self, selected_count: int):
        """
        Aktualizuje widoczność operacji bulk w zależności od liczby zaznaczonych elementów.

        Args:
            selected_count: Liczba zaznaczonych elementów
        """
        return self.main_window.selection_manager.update_bulk_operations_visibility_with_count(
            selected_count
        )

    def add_new_pair(self, new_pair: FilePair):
        """
        Dodaje nową parę do widoku po ręcznym parowaniu.

        Args:
            new_pair: Nowa para plików do dodania
        """
        # 1. Dodaj parę do głównej listy w kontrolerze
        self.main_window.controller.current_file_pairs.append(new_pair)

        # 2. Utwórz nowy kafelek
        if hasattr(self.main_window, "gallery_tab_manager") and hasattr(
            self.main_window.gallery_tab_manager, "tiles_container"
        ):
            tile = self.main_window.gallery_manager.create_tile_widget_for_pair(
                new_pair, self.main_window.gallery_tab_manager.tiles_container
            )
            if tile:
                # 3. Dodaj kafelek do galerii i odśwież widok
                self.main_window.gallery_manager.update_gallery_view()
                self.logger.info(
                    f"Dodano nową parę do galerii: {new_pair.get_base_name()}"
                )
        else:
            self.logger.warning("Nie można dodać kafelka - brak tiles_container")

    def update_unpaired_lists(self, archives: List[str], previews: List[str]):
        """
        Aktualizuje listy niesparowanych plików.

        Args:
            archives: Lista ścieżek niesparowanych archiwów
            previews: Lista ścieżek niesparowanych podglądów
        """
        self.main_window.controller.unpaired_archives = archives
        self.main_window.controller.unpaired_previews = previews

        # Delegacja do managera zamiast wywołania nieistniejącej metody
        if hasattr(self.main_window, "unpaired_files_tab_manager"):
            self.main_window.unpaired_files_tab_manager.update_unpaired_files_lists()

    def request_metadata_save(self):
        """
        Żąda zapisu metadanych - delegacja do MetadataManager.
        """
        return self.main_window.metadata_manager.request_metadata_save()

    def set_working_directory(self, directory: str):
        """
        Ustawia główny katalog roboczy i inicjalizuje widoki.

        Args:
            directory: Ścieżka do katalogu roboczego
        """
        import os

        self.logger.info(f"Ustawianie katalogu roboczego na: {directory}")
        if directory and os.path.isdir(directory):
            self.main_window.directory_tree_manager.init_directory_tree_without_expansion(
                directory
            )
        else:
            self.logger.warning(
                f"Próba ustawienia nieistniejącego katalogu: {directory}"
            )

    def handle_controller_update(self, update_type: str, data=None):
        """
        Uniwersalna metoda do obsługi aktualizacji z kontrolera.

        Args:
            update_type: Typ aktualizacji ('scan_complete', 'metadata_changed', etc.)
            data: Dodatkowe dane związane z aktualizacją
        """
        if update_type == "scan_complete":
            self.update_scan_results(data)
        elif update_type == "metadata_changed":
            self.request_metadata_save()
        elif update_type == "selection_changed":
            selected_count = len(data) if data else 0
            self.update_bulk_operations_visibility(selected_count)
        elif update_type == "unpaired_files_updated":
            if data and "archives" in data and "previews" in data:
                self.update_unpaired_lists(data["archives"], data["previews"])
        else:
            self.logger.warning(f"Nieznany typ aktualizacji kontrolera: {update_type}")

    def get_controller_state(self) -> dict:
        """
        Pobiera aktualny stan z kontrolera.

        Returns:
            Słownik z aktualnym stanem kontrolera
        """
        if not hasattr(self.main_window, "controller"):
            return {}

        controller = self.main_window.controller
        return {
            "current_directory": getattr(controller, "current_directory", None),
            "file_pairs_count": len(getattr(controller, "current_file_pairs", [])),
            "unpaired_archives_count": len(
                getattr(controller, "unpaired_archives", [])
            ),
            "unpaired_previews_count": len(
                getattr(controller, "unpaired_previews", [])
            ),
            "selected_tiles_count": len(getattr(controller.selection_manager, "selected_tiles", [])),
            "special_folders_count": len(getattr(controller, "special_folders", [])),
        }

    def validate_controller_state(self) -> bool:
        """
        Waliduje czy kontroler jest w poprawnym stanie.

        Returns:
            True jeśli kontroler jest poprawnie zainicjalizowany
        """
        if not hasattr(self.main_window, "controller"):
            self.logger.error("Brak referencji do kontrolera w MainWindow")
            return False

        controller = self.main_window.controller
        required_attributes = [
            "current_file_pairs",
            "unpaired_archives",
            "unpaired_previews",
            "selected_tiles",
        ]

        for attr in required_attributes:
            if not hasattr(controller, attr):
                self.logger.error(f"Kontroler nie ma wymaganego atrybutu: {attr}")
                return False

        return True

    def log_controller_statistics(self):
        """
        Loguje statystyki kontrolera do debugowania.
        """
        if not self.validate_controller_state():
            return

        state = self.get_controller_state()
        self.logger.debug(
            f"Stan kontrolera: "
            f"folder={state['current_directory']}, "
            f"pary={state['file_pairs_count']}, "
            f"archiwa={state['unpaired_archives_count']}, "
            f"podglądy={state['unpaired_previews_count']}, "
            f"zaznaczone={state['selected_tiles_count']}, "
            f"foldery_spec={state['special_folders_count']}"
        )
