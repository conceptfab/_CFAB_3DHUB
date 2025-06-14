"""
Scan Manager - zarządzanie skanowaniem folderów.
"""

import logging
import os

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from src.utils.path_utils import normalize_path


class ScanManager:
    """Zarządza skanowaniem folderów i walidacją ścieżek."""

    def __init__(self, main_window):
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def select_working_directory(self, directory_path=None):
        """Otwiera dialog wyboru folderu lub używa podanej ścieżki."""
        self.stop_current_scanning()

        if directory_path:
            path = directory_path
        else:
            path = QFileDialog.getExistingDirectory(
                self.main_window, "Wybierz Folder Roboczy"
            )

        if not path:
            logging.debug("Nie wybrano folderu.")
            return

        if not self.validate_directory_path(path):
            return

        normalized_path = normalize_path(path)
        base_folder_name = os.path.basename(normalized_path)
        self.main_window.setWindowTitle(f"CFAB_3DHUB - {base_folder_name}")

        if not hasattr(self.main_window, "_is_auto_loading"):
            logging.info("Folder wybrany ręcznie ale NIE nadpisuję domyślnego!")
        else:
            logging.debug("Auto-loading from default folder")

        logging.info("Wybrano folder roboczy: %s", normalized_path)

        self.main_window.data_manager.clear_all_data_and_views()
        self.start_folder_scanning(normalized_path)

    def validate_directory_path(self, path: str) -> bool:
        """Waliduje ścieżkę do folderu."""
        if not path or not isinstance(path, str):
            QMessageBox.warning(
                self.main_window, "Błąd", "Nieprawidłowa ścieżka do folderu."
            )
            return False

        if not os.path.exists(path):
            QMessageBox.warning(
                self.main_window, "Błąd", f"Folder nie istnieje:\n{path}"
            )
            return False

        if not os.path.isdir(path):
            QMessageBox.warning(
                self.main_window, "Błąd", f"Ścieżka nie wskazuje na folder:\n{path}"
            )
            return False

        if not os.access(path, os.R_OK):
            QMessageBox.warning(
                self.main_window, "Błąd", f"Brak uprawnień do odczytu folderu:\n{path}"
            )
            return False

        return True

    def stop_current_scanning(self):
        """Przerywa aktualnie działające skanowanie."""
        if (
            hasattr(self.main_window, "scan_thread")
            and self.main_window.scan_thread
            and self.main_window.scan_thread.isRunning()
        ):
            logging.warning(
                "Nowe skanowanie żądane, gdy poprzednie jest aktywne. "
                "Przerywam stary wątek i uruchamiam nowy."
            )
            if (
                hasattr(self.main_window, "scan_worker")
                and self.main_window.scan_worker
            ):
                self.main_window.scan_worker.stop()
            try:
                if (
                    hasattr(self.main_window, "scan_worker")
                    and self.main_window.scan_worker
                ):
                    self.main_window.scan_worker.finished.disconnect()
                    self.main_window.scan_worker.error.disconnect()
            except (TypeError, AttributeError):
                logging.debug("Nie można było odłączyć sygnałów od starego workera.")
            self.main_window.scan_thread.quit()
            self.main_window.scan_thread.wait(
                self.main_window.app_config.thread_wait_timeout_ms // 2
            )

    def start_folder_scanning(self, directory_path: str):
        """Delegacja skanowania do MainWindowController (MVC)."""
        self.main_window.select_folder_button.setText("Skanowanie...")
        self.main_window.select_folder_button.setEnabled(False)

        success = self.main_window.controller.handle_folder_selection(directory_path)

        if hasattr(self.main_window, "file_explorer_tab") and success:
            self.main_window.file_explorer_tab.set_root_path(directory_path)

        self.main_window.select_folder_button.setText("Wybierz Folder")
        self.main_window.select_folder_button.setEnabled(True)

        if success:
            logging.info(f"Controller scan SUCCESS: {directory_path}")
        else:
            logging.warning(f"Controller scan FAILED: {directory_path}")

    def on_scan_thread_finished(self):
        """Slot wywoływany po zakończeniu pracy wątku skanującego."""
        self.main_window.select_folder_button.setText("Wybierz Folder")
        self.main_window.select_folder_button.setEnabled(True)

        if hasattr(self.main_window, "scan_thread") and self.main_window.scan_thread:
            self.main_window.scan_thread.deleteLater()
            self.main_window.scan_thread = None
        if hasattr(self.main_window, "scan_worker") and self.main_window.scan_worker:
            self.main_window.scan_worker.deleteLater()
            self.main_window.scan_worker = None
        logging.debug("Wątek skanujący i worker zostały bezpiecznie wyczyszczone.")

    def handle_scan_finished(self, found_pairs, unpaired_archives, unpaired_previews):
        """Obsługuje wyniki pomyślnie zakończonego skanowania folderu."""
        logging.info(
            f"Skanowanie folderu {self.main_window.controller.current_directory} "
            f"zakończone pomyślnie."
        )

        self.main_window.controller.handle_scan_finished(
            found_pairs, unpaired_archives, unpaired_previews
        )

        self.main_window.gallery_manager.clear_gallery()

        if found_pairs:
            self.main_window.worker_manager.start_data_processing_worker(found_pairs)
        else:
            self.main_window.tile_manager.on_tile_loading_finished()

    def change_directory(self, folder_path: str):
        """Zmienia katalog roboczy na wybrany folder i skanuje tylko ten folder."""
        try:
            normalized_path = normalize_path(folder_path)
            base_folder_name = os.path.basename(normalized_path)
            self.main_window.setWindowTitle(f"CFAB_3DHUB - {base_folder_name}")

            logging.info(f"Zmiana katalogu na: {normalized_path}")

            self.main_window.gallery_manager.clear_gallery()
            self.main_window.data_manager.clear_unpaired_files_lists()

            try:
                scan_result = self.main_window.controller.scan_service.scan_directory(
                    normalized_path, max_depth=0
                )

                if scan_result.error_message:
                    self.main_window.show_error_message(
                        "Błąd skanowania", scan_result.error_message
                    )
                    return

                self.main_window.controller.current_directory = normalized_path
                self.main_window.controller.current_file_pairs = scan_result.file_pairs
                self.main_window.controller.unpaired_archives = (
                    scan_result.unpaired_archives
                )
                self.main_window.controller.unpaired_previews = (
                    scan_result.unpaired_previews
                )

                if hasattr(self.main_window, "file_explorer_tab"):
                    self.main_window.file_explorer_tab.set_root_path(normalized_path)
                    logging.info(f"EKSPLORATOR: Ustawiono ścieżkę na {normalized_path}")

                if scan_result.file_pairs:
                    self.main_window.worker_manager.start_data_processing_worker_without_tree_reset(
                        scan_result.file_pairs
                    )
                else:
                    self.finish_folder_change_without_tree_reset()

                logging.info(
                    f"Folder change SUCCESS: {normalized_path}, {len(scan_result.file_pairs)} par"
                )

            except Exception as scan_error:
                error_msg = f"Błąd skanowania folderu: {scan_error}"
                logging.error(error_msg)
                self.main_window.show_error_message("Błąd", error_msg)

        except Exception as e:
            error_msg = f"Błąd zmiany katalogu: {e}"
            logging.error(error_msg)
            self.main_window.show_error_message("Błąd", error_msg)

    def finish_folder_change_without_tree_reset(self):
        """Kończy zmianę folderu bez resetowania drzewa katalogów."""
        logging.debug("Zakończono tworzenie kafelków bez resetowania drzewa")

        self.main_window.data_manager.apply_filters_and_update_view()
        if hasattr(self.main_window, "unpaired_files_tab_manager"):
            self.main_window.unpaired_files_tab_manager.update_unpaired_files_lists()

        self.main_window.filter_panel.setEnabled(True)
        is_gallery_populated = bool(self.main_window.gallery_manager.file_pairs_list)
        self.main_window.size_control_panel.setVisible(is_gallery_populated)

        self.main_window.select_folder_button.setText("Wybierz Folder Roboczy")
        self.main_window.select_folder_button.setEnabled(True)

        self.main_window.clear_cache_button.setVisible(True)

        self.main_window._save_metadata()

        if hasattr(self.main_window, "directory_tree_manager"):
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(
                1000,
                self.main_window.directory_tree_manager.start_background_stats_calculation,
            )

        actual_tiles_count = len(self.main_window.gallery_manager.file_pairs_list)
        self.main_window.progress_manager.show_progress(
            100, f"✅ Załadowano {actual_tiles_count} kafelków!"
        )

        from PyQt6.QtCore import QTimer

        QTimer.singleShot(500, self.main_window.progress_manager.hide_progress)

        logging.info(
            f"Widok zaktualizowany bez resetowania drzewa. Wyświetlono po filtracji: "
            f"{actual_tiles_count}."
        )
