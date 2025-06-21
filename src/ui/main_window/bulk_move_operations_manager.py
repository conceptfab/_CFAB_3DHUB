"""
Bulk Move Operations Manager - wydzielony z MainWindow.py.
Obsługuje masowe operacje przenoszenia plików.
"""

import logging
import os

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox

from src.logic.scanner import clear_cache


class BulkMoveOperationsManager:
    """
    Manager odpowiedzialny za bulk move operations.
    Przeniesiony z MainWindow dla lepszej separacji odpowiedzialności.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje manager.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def perform_bulk_move(self):
        """
        Wykonuje masową operację przenoszenia zaznaczonych kafelków przy użyciu wątku roboczego.
        Przeniesiona z MainWindow._perform_bulk_move()
        """
        from PyQt6.QtWidgets import QFileDialog

        from src.ui.delegates.workers import BulkMoveWorker

        if not self.main_window.controller.selection_manager.selected_tiles:
            return

        # Pobierz katalog docelowy
        destination = QFileDialog.getExistingDirectory(
            self.main_window,
            "Wybierz folder docelowy",
            self.main_window.controller.current_directory or "",
        )

        if not destination:
            return

        count = len(self.main_window.controller.selection_manager.selected_tiles)

        # Utwórz workera do masowego przenoszenia
        worker = BulkMoveWorker(
            list(self.main_window.controller.selection_manager.selected_tiles), destination
        )

        # Podłącz sygnały
        self.main_window.worker_manager.setup_worker_connections(worker)
        worker.signals.finished.connect(self.on_bulk_move_finished)

        # Uruchom workera
        self.main_window._show_progress(0, f"Przenoszenie {count} par plików...")
        self.main_window.thread_pool.start(worker)

    def on_bulk_move_finished(self, result):
        """
        Slot wywoływany po zakończeniu operacji przenoszenia.
        Przeniesiona z MainWindow._on_bulk_move_finished()

        Args:
            result: Wynik operacji - może być listą par plików (stary format) lub słownikiem z szczegółami (nowy format)
        """
        # Obsługa nowego formatu wyniku
        if isinstance(result, dict):
            moved_pairs = result.get("moved_pairs", [])
            detailed_errors = result.get("detailed_errors", [])
            skipped_files = result.get("skipped_files", [])
            summary = result.get("summary", {})
        else:
            # Fallback dla starych workerów
            moved_pairs = result if isinstance(result, list) else []
            detailed_errors = []
            skipped_files = []
            summary = {}

        if not moved_pairs and not detailed_errors and not skipped_files:
            self.main_window._show_progress(100, "Przenoszenie przerwane lub nieudane")
            return

        # Zapamiętaj oryginalną liczbę zaznaczonych par PRZED ich usunięciem
        original_selected_count = len(self.main_window.controller.selection_manager.selected_tiles)

        # Usuń przeniesione pary z struktur danych
        for file_pair in moved_pairs:
            if file_pair in self.main_window.controller.current_file_pairs:
                self.main_window.controller.current_file_pairs.remove(file_pair)
            self.main_window.controller.selection_manager.selected_tiles.discard(file_pair)

        if self.main_window.controller.current_directory:
            self.logger.debug(
                f"Odświeżanie folderu źródłowego po drag&drop: {self.main_window.controller.current_directory}"
            )
            self.refresh_source_folder_after_move()
        else:
            self.main_window._apply_filters_and_update_view()

        # NAPRAWKA DEADLOCK: Użyj asynchronicznego zapisu metadanych
        # zamiast synchronicznego który może blokować UI
        self.main_window._schedule_metadata_save()

        destination = (
            os.path.dirname(moved_pairs[0].archive_path) if moved_pairs else "nieznany"
        )
        self.main_window._show_progress(
            100, f"Przeniesiono {len(moved_pairs)} par plików"
        )

        # NAPRAWKA DEADLOCK: Opóźnij MessageBox żeby nie blokować UI podczas odświeżania
        def show_completion_message():
            # Pokaż szczegółowy raport błędów jeśli wystąpiły
            if isinstance(result, dict) and (detailed_errors or skipped_files):
                self.main_window._show_detailed_move_report(
                    moved_pairs, detailed_errors, skipped_files, summary
                )
            else:
                QMessageBox.information(
                    self.main_window,
                    "Przenoszenie zakończone",
                    f"Przeniesiono {len(moved_pairs)} z {original_selected_count} zaznaczonych par plików do:\n{destination}",
                )

        # Opóźnij pokazanie MessageBox o 500ms żeby odświeżanie się zakończyło
        QTimer.singleShot(500, show_completion_message)

    def refresh_source_folder_after_move(self):
        """
        Odświeża folder źródłowy po operacji przenoszenia plików przez drag&drop.
        Przeniesiona z MainWindow._refresh_source_folder_after_move()

        Ta metoda ponownie skanuje current_working_directory, aby usunąć z widoku
        pliki które zostały przeniesione i już nie istnieją na dysku.
        """
        if not self.main_window.controller.current_directory or not os.path.exists(
            self.main_window.controller.current_directory
        ):
            logging.warning(
                f"Nie można odświeżyć - folder źródłowy nie istnieje: {self.main_window.controller.current_directory}"
            )
            return

        try:
            # Ponownie przeskanuj folder źródłowy
            self.logger.debug(
                f"Rozpoczynanie ponownego skanowania folderu: {self.main_window.controller.current_directory}"
            )

            clear_cache()

            # NAPRAWKA DEADLOCK: Zamiast change_directory() użyj prostego skanowania
            # change_directory() uruchamia nowe workery co może powodować deadlock
            try:
                # Skanuj tylko bezpośrednie pliki w folderze (max_depth=0)
                scan_result = self.main_window.controller.scan_service.scan_directory(
                    self.main_window.controller.current_directory, max_depth=0
                )

                if scan_result.error_message:
                    logging.error(
                        f"Błąd skanowania po bulk move: {scan_result.error_message}"
                    )
                    # NAPRAWKA DEADLOCK: Nie używaj refresh_all_views() jako fallback
                    # może powodować nieskończoną pętlę lub deadlock
                    logging.warning("Pomijam odświeżanie z powodu błędu skanowania")
                    return

                # Zaktualizuj dane kontrolera
                self.main_window.controller.current_file_pairs = scan_result.file_pairs
                self.main_window.controller.unpaired_archives = (
                    scan_result.unpaired_archives
                )
                self.main_window.controller.unpaired_previews = (
                    scan_result.unpaired_previews
                )
                self.main_window.controller.special_folders = (
                    scan_result.special_folders
                )

                # Odśwież widoki BEZ uruchamiania nowych workerów
                self.main_window._apply_filters_and_update_view()

                # Aktualizuj niesparowane pliki
                if hasattr(self.main_window, "unpaired_files_tab_manager"):
                    self.main_window.unpaired_files_tab_manager.update_unpaired_files_lists()

                self.logger.debug(
                    "Pomyślnie odświeżono folder źródłowy po operacji bez uruchamiania nowych workerów"
                )

            except Exception as e:
                logging.warning(f"Błąd podczas prostego skanowania: {e}")
                # NAPRAWKA DEADLOCK: Nie używaj refresh_all_views() jako fallback
                # może powodować nieskończoną pętlę lub deadlock
                logging.warning("Pomijam odświeżanie z powodu błędu")

        except Exception as e:
            logging.error(f"Błąd podczas odświeżania folderu źródłowego: {e}")
            # NAPRAWKA DEADLOCK: Nie używaj refresh_all_views() jako fallback
            # może powodować nieskończoną pętlę lub deadlock
            logging.warning("Pomijam odświeżanie z powodu błędu")
