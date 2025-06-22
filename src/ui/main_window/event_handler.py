"""
EventHandler - obsługa zdarzeń i sygnałów dla MainWindow.
🚀 ETAP 1: Refaktoryzacja MainWindow - komponent obsługi zdarzeń
"""

import logging

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCloseEvent, QResizeEvent
from PyQt6.QtWidgets import QMessageBox

from src.models.file_pair import FilePair


class EventHandler:
    """
    Obsługa zdarzeń i sygnałów dla MainWindow.

    Odpowiedzialności:
    - Obsługa zdarzeń okna (close, resize)
    - Obsługa zdarzeń skanowania (finished, error)
    - Obsługa zdarzeń kafelków (selection, stars, color tags)
    - Obsługa błędów workerów
    """

    def __init__(self, main_window):
        """
        Inicjalizuje EventHandler.

        Args:
            main_window: Referencja do głównego okna MainWindow
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def handle_close_event(self, event: QCloseEvent):
        """
        Obsługuje zdarzenie zamknięcia okna.

        Args:
            event: Zdarzenie zamknięcia okna
        """
        self.logger.info("Zamykanie aplikacji...")

        # Zatrzymaj wszystkie workery przed zamknięciem
        self.main_window.worker_manager.cleanup_threads()

        # Wymuś zapisanie metadanych przed zamknięciem
        self.main_window._force_immediate_metadata_save()

        event.accept()

    def handle_resize_event(self, event: QResizeEvent):
        """
        Obsługuje zdarzenie zmiany rozmiaru okna.

        Args:
            event: Zdarzenie zmiany rozmiaru
        """
        super(type(self.main_window), self.main_window).resizeEvent(event)

        # Opóźnione odświeżenie galerii po zmianie rozmiaru - używaj konfiguracji
        delay = self.main_window.app_config.resize_timer_delay_ms
        self.main_window.resize_timer.start(delay)

    def handle_scan_finished(
        self, found_pairs, unpaired_archives, unpaired_previews, special_folders=None
    ):
        """
        Obsługuje zakończenie skanowania foldera.

        Args:
            found_pairs: Lista znalezionych par plików
            unpaired_archives: Lista nieparowanych archiwów
            unpaired_previews: Lista nieparowanych podglądów
            special_folders: Lista specjalnych folderów
        """
        self.logger.info(f"Skanowanie zakończone: {len(found_pairs)} par znalezionych")

        # Aktualizuj dane w kontrolerze
        self.main_window.controller.current_file_pairs = found_pairs
        self.main_window.controller.unpaired_archives = unpaired_archives
        self.main_window.controller.unpaired_previews = unpaired_previews

        # Aktualizuj listy nieparowanych plików
        self.main_window.unpaired_files_tab.update_lists(
            unpaired_archives, unpaired_previews
        )

        # Utwórz kafelki dla znalezionych par
        if found_pairs:
            self.main_window._create_tile_widgets_batch(found_pairs)
        else:
            # Jeśli nie ma par, od razu ukryj progress i odśwież widoki
            self.main_window.progress_manager.hide_progress()
            self.main_window._update_gallery_view()

    def handle_scan_error(self, error_message: str):
        """
        Obsługuje błąd podczas skanowania.

        Args:
            error_message: Komunikat błędu
        """
        self.logger.error(f"Błąd skanowania: {error_message}")

        # Ukryj progress bar
        self.main_window.progress_manager.hide_progress()

        # Pokaż komunikat błędu
        QMessageBox.critical(
            self.main_window,
            "Błąd skanowania",
            f"Wystąpił błąd podczas skanowania foldera:\n\n{error_message}",
        )

        # Wyczyść dane
        self.main_window._clear_all_data_and_views()

    def handle_tile_selection_changed(self, file_pair: FilePair, is_selected: bool):
        """
        Obsługuje zmianę selekcji kafelka.

        Args:
            file_pair: Para plików
            is_selected: Czy kafelek jest zaznaczony
        """
        # Synchronizuj z oboma managerami
        if is_selected:
            self.main_window.selection_manager.selected_tiles.add(file_pair)
            if hasattr(self.main_window, "controller") and self.main_window.controller:
                self.main_window.controller.selection_manager.selected_tiles.add(
                    file_pair
                )
        else:
            self.main_window.selection_manager.selected_tiles.discard(file_pair)
            if hasattr(self.main_window, "controller") and self.main_window.controller:
                self.main_window.controller.selection_manager.selected_tiles.discard(
                    file_pair
                )

        # Aktualizuj widoczność operacji bulk
        self.main_window._update_bulk_operations_visibility()

        self.logger.debug(
            f"Selekcja zmieniona: {len(self.main_window.selection_manager.selected_tiles)} zaznaczonych"
        )

    def handle_stars_changed(self, file_pair: FilePair, new_star_count: int):
        """
        Obsługuje zmianę liczby gwiazdek.

        Args:
            file_pair: Para plików
            new_star_count: Nowa liczba gwiazdek
        """
        self.logger.debug(
            f"Zmiana gwiazdek dla {file_pair.archive_path}: {new_star_count}"
        )

        # Aktualizuj metadane
        file_pair.star_rating = new_star_count

        # Zaplanuj zapisanie metadanych
        self.main_window._schedule_metadata_save()

    def handle_color_tag_changed(self, file_pair: FilePair, new_color_tag: str):
        """
        Obsługuje zmianę tagu kolorów.

        Args:
            file_pair: Para plików
            new_color_tag: Nowy tag koloru
        """
        self.logger.debug(
            f"Zmiana tagu koloru dla {file_pair.archive_path}: {new_color_tag}"
        )

        # Aktualizuj metadane
        file_pair.color_tag = new_color_tag

        # Zaplanuj zapisanie metadanych
        self.main_window._schedule_metadata_save()

    def handle_worker_error(self, error_message: str):
        """
        Obsługuje błędy workerów.

        Args:
            error_message: Komunikat błędu
        """
        self.logger.error(f"Błąd workera: {error_message}")

        # Ukryj progress bar
        self.main_window.progress_manager.hide_progress()
