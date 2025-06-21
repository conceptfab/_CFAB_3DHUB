"""
ScanResultsHandler - obsługa wyników skanowania folderów.
🚀 ETAP 3 REFAKTORYZACJI: Wydzielenie logiki skanowania z main_window.py
"""

import logging
import os

from PyQt6.QtCore import QTimer

# Import clear_cache usunięty bo nieużywany
from src.utils.path_utils import normalize_path


class ScanResultsHandler:
    """
    Manager odpowiedzialny za obsługę wyników skanowania folderów.
    Obsługuje wyniki skanowania, błędy i zmianę katalogów.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje ScanResultsHandler.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def handle_scan_finished(
        self,
        found_pairs,
        unpaired_archives,
        unpaired_previews,
        special_folders=None,
    ):
        """
        Obsługuje wyniki po zakończeniu skanowania w tle.
        Aktualizuje model danych i odświeża widoki.

        Args:
            found_pairs: Lista znalezionych par plików
            unpaired_archives: Lista niesparowanych archiwów
            unpaired_previews: Lista niesparowanych podglądów
            special_folders: Lista specjalnych folderów (opcjonalne)
        """
        if special_folders is None:
            special_folders = []

        # DIAGNOSTYKA
        self.logger.critical(
            f"DIAGNOSTYKA HANDLE_SCAN_FINISHED: Otrzymano "
            f"{len(special_folders)} folderów specjalnych: "
            f"{special_folders}"
        )

        self.logger.debug(
            f"Skanowanie zakończone, otrzymano: {len(found_pairs)} par, "
            f"{len(unpaired_archives)} archiwów, "
            f"{len(unpaired_previews)} podglądów"
        )

        # Zaktualizuj dane kontrolera
        self.main_window.controller.current_file_pairs = found_pairs
        self.main_window.controller.unpaired_archives = unpaired_archives
        self.main_window.controller.unpaired_previews = unpaired_previews
        self.main_window.controller.special_folders = special_folders

        # Odśwież widoki
        self.main_window._apply_filters_and_update_view()

        # Aktualizuj niesparowane pliki
        if hasattr(self.main_window, "unpaired_files_tab_manager"):
            self.main_window.unpaired_files_tab_manager.update_unpaired_files_lists()

        # Pokaż interfejs
        if hasattr(self.main_window, "filter_panel"):
            self.main_window.filter_panel.setEnabled(True)  # Odblokuj panel filtrów

        is_gallery_populated = bool(self.main_window.gallery_manager.file_pairs_list)
        if hasattr(self.main_window, "size_control_panel"):
            self.main_window.size_control_panel.setVisible(is_gallery_populated)

        # Przywróć przycisk
        if hasattr(self.main_window, "select_folder_button"):
            self.main_window.select_folder_button.setText("Wybierz Folder Roboczy")
            self.main_window.select_folder_button.setEnabled(True)

        # Pokaż przycisk odświeżania cache
        if hasattr(self.main_window, "clear_cache_button"):
            self.main_window.clear_cache_button.setVisible(True)

        # Zapisz metadane
        self.main_window._save_metadata()

        # Uruchom obliczanie statystyk folderów
        if hasattr(self.main_window, "directory_tree_manager"):
            QTimer.singleShot(
                1000,
                self.main_window.directory_tree_manager.start_background_stats_calculation,
            )

        # Ustaw progress bar na 100% po zakończeniu
        actual_tiles_count = len(self.main_window.gallery_manager.file_pairs_list)
        self.main_window.progress_manager.show_progress(
            100, f"✅ Załadowano {actual_tiles_count} kafelków!"
        )

        # Krótkie opóźnienie żeby użytkownik zobaczył 100% przed ukryciem
        QTimer.singleShot(500, self.main_window.progress_manager.hide_progress)

        self.logger.debug(
            f"Widok zaktualizowany. Wyświetlono po filtracji: {actual_tiles_count}."
        )

    def handle_scan_error(self, error_message: str):
        """
        Obsługuje błędy występujące podczas skanowania folderu.

        Args:
            error_message: Komunikat błędu do wyświetlenia
        """
        # Delegacja do EventHandler
        self.main_window.event_handler.handle_scan_error(error_message)

        # Przywróć przycisk
        if hasattr(self.main_window, "select_folder_button"):
            self.main_window.select_folder_button.setText("Wybierz Folder Roboczy")
            self.main_window.select_folder_button.setEnabled(True)

        if hasattr(self.main_window, "filter_panel"):
            self.main_window.filter_panel.setEnabled(False)  # Zablokuj przy błędzie

    def change_directory(self, folder_path: str):
        """
        Zmienia bieżący katalog roboczy i rozpoczyna skanowanie.
        Ta metoda jest wywoływana z DirectoryTreeManagera.

        Args:
            folder_path: Ścieżka do nowego katalogu roboczego
        """
        self.logger.info(f"Zmiana katalogu na: {folder_path} (bez resetu drzewa)")
        normalized_path = normalize_path(folder_path)

        if not self.main_window._validate_directory_path(normalized_path):
            return

        try:
            self.logger.debug("Rozpoczynam zmianę katalogu bez resetu drzewa...")
            self.main_window._show_progress(
                0, f"Skanowanie: {os.path.basename(normalized_path)}"
            )
            self.main_window.is_scanning = True

            # Uruchom skanowanie w tle
            scan_result = self.main_window.controller.scan_service.scan_directory(
                normalized_path, max_depth=0
            )
            # DIAGNOSTYKA
            self.logger.critical(
                f"DIAGNOSTYKA CHANGE_DIRECTORY: Otrzymano "
                f"{len(scan_result.special_folders)} folderów specjalnych "
                f"ze skanera: {scan_result.special_folders}"
            )

            # Zatrzymaj spinner/progress bar
            self.main_window.is_scanning = False
            self.main_window._hide_progress()

            # Zaktualizuj stan kontrolera ręcznie
            self.main_window.controller.current_directory = normalized_path
            self.main_window.controller.current_file_pairs = scan_result.file_pairs
            self.main_window.controller.unpaired_archives = (
                scan_result.unpaired_archives
            )
            self.main_window.controller.unpaired_previews = (
                scan_result.unpaired_previews
            )
            self.main_window.controller.special_folders = scan_result.special_folders

            # 🔧 NAPRAWKA: Aktualizuj FileExplorerTab z nowym folderem
            if hasattr(self.main_window, "file_explorer_tab"):
                self.main_window.file_explorer_tab.set_root_path(normalized_path)
                self.logger.debug(
                    f"FileExplorerTab zaktualizowany folderem: {normalized_path}"
                )

            if scan_result.file_pairs:
                self.main_window.worker_manager.start_data_processing_worker_without_tree_reset(
                    scan_result.file_pairs
                )
            else:
                self.finish_folder_change_without_tree_reset()

        except Exception as scan_error:
            error_msg = f"Błąd skanowania folderu: {scan_error}"
            self.logger.error(error_msg)
            self.main_window.show_error_message("Błąd", error_msg)

    def finish_folder_change_without_tree_reset(self):
        """
        Kończy proces zmiany folderu, gdy nie ma par plików do przetworzenia,
        lub po zakończeniu przetwarzania przez workera.
        Odświeża widoki bez resetowania drzewa katalogów.
        """
        self.logger.debug(
            "Finalizowanie zmiany folderu bez resetu drzewa - odświeżanie widoków..."
        )
        self.main_window._hide_progress()

        # Zamiast pobierać listę, po prostu wywołaj metodę, która zrobi wszystko
        self.main_window.data_manager.apply_filters_and_update_view()

        # Upewnij się, że foldery specjalne są przekazywane
        if hasattr(self.main_window.controller, "special_folders"):
            self.main_window.gallery_manager.set_special_folders(
                self.main_window.controller.special_folders
            )
        else:
            self.logger.error(
                "DIAGNOSTYKA FINISH_FOLDER_CHANGE: Kontroler nie ma "
                "atrybutu special_folders!"
            )

        self.main_window._update_unpaired_files_direct()

        # Ukryj progress bar
        self.main_window._hide_progress()
        self.logger.debug("Zakończono finalizowanie zmiany folderu bez resetu drzewa")
