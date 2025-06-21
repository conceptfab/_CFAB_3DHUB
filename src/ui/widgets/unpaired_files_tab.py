"""
Zakładka niesparowanych plików - ETAP 2 refaktoryzacji.
Używa UnpairedFilesUIManager dla separacji odpowiedzialności UI.
"""

import logging
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.ui.delegates.workers.file_list_workers import BulkDeleteFilesWorker
from src.ui.widgets.preview_dialog import PreviewDialog

# Dodaj import stylów z FileTileWidget
from src.ui.widgets.tile_styles import TileSizeConstants
from src.ui.widgets.unpaired_archives_list import UnpairedArchivesList
from src.ui.widgets.unpaired_files_ui_manager import UnpairedFilesUIManager
from src.ui.widgets.unpaired_preview_tile import UnpairedPreviewTile
from src.ui.widgets.unpaired_previews_grid import UnpairedPreviewsGrid

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class UnpairedFilesTab:
    """
    Zarządza zakładką niesparowanych plików - ETAP 2 refaktoryzacji.
    Używa UnpairedFilesUIManager dla zarządzania UI.
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Inicjalizuje zakładkę niesparowanych plików.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window

        # ETAP 2: Deleguj UI do dedykowanego managera
        self.ui_manager = UnpairedFilesUIManager(main_window)

        # Zachowaj kompatybilność z istniejącym API
        self._setup_compatibility_properties()

    def _setup_compatibility_properties(self):
        """Ustawia właściwości dla zachowania kompatybilności API."""
        # Te właściwości będą dostępne po utworzeniu UI
        self.unpaired_files_tab = None
        self.pair_manually_button = None
        self.unpaired_archives_list_widget = None
        self.unpaired_previews_list_widget = None

        # Delegacja do UI managera
        self.preview_tile_widgets = self.ui_manager.preview_tile_widgets
        self.current_thumbnail_size = self.ui_manager.current_thumbnail_size

    def create_unpaired_files_tab(self) -> QWidget:
        """
        Tworzy zakładkę niesparowanych plików.

        Returns:
            Widget zakładki niesparowanych plików
        """
        # ETAP 2: Deleguj tworzenie UI do managera
        self.unpaired_files_tab = self.ui_manager.create_tab_ui()

        # Ustaw właściwości kompatybilności
        self._update_compatibility_properties()

        # Podłącz sygnały
        self._connect_all_signals()

        return self.unpaired_files_tab

    def _update_compatibility_properties(self):
        """Aktualizuje właściwości dla kompatybilności API."""
        self.pair_manually_button = self.ui_manager.pair_manually_button
        self.unpaired_archives_list_widget = (
            self.ui_manager.unpaired_archives_list_widget
        )
        self.unpaired_previews_list_widget = (
            self.ui_manager.unpaired_previews_list_widget
        )

    def _connect_all_signals(self):
        """Podłącza wszystkie sygnały UI do metod biznesowych."""
        # Sygnały przycisków
        button_callbacks = {
            "manual_pairing": self._handle_manual_pairing,
            "delete_previews": self._handle_delete_unpaired_previews,
            "move_archives": self._handle_move_unpaired_archives,
        }
        self.ui_manager.connect_button_signals(button_callbacks)

        # Sygnały komponentów
        component_callbacks = {
            "selection_changed": self._update_pair_button_state,
            "preview_deleted": self._delete_preview_file,
        }
        self.ui_manager.connect_component_signals(component_callbacks)

        # Dodatkowe sygnały dla kafelków podglądów
        self._connect_preview_tile_signals()

    def _connect_preview_tile_signals(self):
        """Podłącza sygnały kafelków podglądów."""
        for tile in self.ui_manager.preview_tile_widgets:
            # Sygnał podglądu obrazu
            tile.preview_image_requested.connect(self._show_preview_dialog)

            # Sygnał zmiany checkbox
            tile.checkbox.stateChanged.connect(
                lambda state, cb=tile.checkbox, path=tile.preview_path: self._on_preview_checkbox_changed(
                    cb, path, state
                )
            )

            # Sygnał usuwania
            tile.delete_button.clicked.connect(
                lambda checked, path=tile.preview_path: self._delete_preview_file(path)
            )

    def clear_unpaired_files_lists(self):
        """Czyści listy niesparowanych plików."""
        # ETAP 2: Deleguj do UI managera
        self.ui_manager.clear_all_lists()

    def update_unpaired_files_lists(self):
        """
        Aktualizuje listy niesparowanych plików na podstawie danych z kontrolera.
        """
        logging.debug("Aktualizacja list niesparowanych plików")

        # Sprawdź czy kontroler istnieje
        if not hasattr(self.main_window, "controller"):
            logging.warning("Kontroler nie istnieje - pomijam aktualizację")
            return

        controller = self.main_window.controller

        # Sprawdź czy dane są dostępne
        if not hasattr(controller, "unpaired_archives") or not hasattr(
            controller, "unpaired_previews"
        ):
            logging.debug("Brak danych o niesparowanych plikach w kontrolerze")
            return

        # ETAP 2: Wyczyść przez UI manager
        self.ui_manager.clear_all_lists()

        # ETAP 2: Aktualizuj przez UI manager
        if controller.unpaired_archives:
            self.ui_manager.update_archives_list(controller.unpaired_archives)

        if controller.unpaired_previews:
            self.ui_manager.update_previews_list(controller.unpaired_previews)
            # Podłącz sygnały dla nowo utworzonych kafelków
            self._connect_preview_tile_signals()

        # Aktualizuj stan przycisków
        self._update_pair_button_state()

        logging.debug(
            f"Zaktualizowano listy: {len(controller.unpaired_archives)} archiwów, "
            f"{len(controller.unpaired_previews)} podglądów"
        )

    def _update_pair_button_state(self):
        """
        Aktualizuje stan przycisku parowania na podstawie wybranych elementów.
        """
        if not self.pair_manually_button:
            return

        # Sprawdź czy archiwum jest wybrane
        archive_selected = (
            self.unpaired_archives_list_widget is not None
            and hasattr(self.unpaired_archives_list_widget, "currentItem")
            and self.unpaired_archives_list_widget.currentItem() is not None
        )

        # Sprawdź czy podgląd jest zaznaczony
        preview_selected = any(
            tile.checkbox.isChecked() for tile in self.preview_tile_widgets
        )

        # Włącz przycisk tylko gdy oba są wybrane
        self.pair_manually_button.setEnabled(archive_selected and preview_selected)

    def update_pair_button_state(self):
        """Publiczna metoda do aktualizacji stanu przycisku parowania."""
        self._update_pair_button_state()

    def _handle_manual_pairing(self):
        """Obsługuje ręczne parowanie wybranego archiwum z podglądem."""
        # Pobierz wybrane archiwum
        current_archive_item = self.unpaired_archives_list_widget.currentItem()
        if not current_archive_item:
            return

        archive_path = current_archive_item.data(Qt.ItemDataRole.UserRole)

        # Pobierz zaznaczony podgląd
        selected_preview = None
        for tile in self.preview_tile_widgets:
            if tile.checkbox.isChecked():
                selected_preview = tile.preview_path
                break

        if not selected_preview:
            return

        # Wykonaj parowanie przez kontroler
        if hasattr(self.main_window, "controller"):
            try:
                # Uruchom worker do ręcznego parowania
                from src.ui.delegates.workers.file_workers import (
                    ManuallyPairFilesWorker,
                )

                self.main_window.worker_manager.run_worker(
                    ManuallyPairFilesWorker,
                    on_finished=self._on_manual_pairing_finished,
                    on_error=self._on_manual_pairing_error,
                    show_progress=True,
                    archive_path=archive_path,
                    preview_path=selected_preview,
                    working_directory=self.main_window.controller.current_directory,
                )

                logging.info(
                    f"Rozpoczęto ręczne parowanie: {archive_path} + {selected_preview}"
                )

            except Exception as e:
                logging.error(f"Błąd podczas ręcznego parowania: {e}")
                QMessageBox.critical(
                    self.main_window,
                    "Błąd parowania",
                    f"Nie można wykonać parowania:\n{str(e)}",
                )

    def _on_manual_pairing_finished(self, result):
        """Obsługuje zakończenie ręcznego parowania."""
        logging.info("Ręczne parowanie zakończone pomyślnie")

        # Odśwież widoki
        self._refresh_unpaired_files()

        # Pokaż komunikat sukcesu
        QMessageBox.information(
            self.main_window,
            "Parowanie zakończone",
            "Pliki zostały pomyślnie sparowane!",
        )

    def _on_manual_pairing_error(self, error_message):
        """Obsługuje błąd podczas ręcznego parowania."""
        logging.error(f"Błąd ręcznego parowania: {error_message}")

        QMessageBox.critical(
            self.main_window,
            "Błąd parowania",
            f"Wystąpił błąd podczas parowania:\n{error_message}",
        )

    def _handle_move_unpaired_archives(self):
        """Obsługuje przenoszenie niesparowanych archiwów do folderu '_bez_pary_'."""
        if not hasattr(self.main_window, "controller"):
            return

        controller = self.main_window.controller
        if (
            not hasattr(controller, "unpaired_archives")
            or not controller.unpaired_archives
        ):
            QMessageBox.information(
                self.main_window,
                "Brak plików",
                "Nie ma niesparowanych archiwów do przeniesienia.",
            )
            return

        # Pokaż dialog potwierdzenia
        reply = QMessageBox.question(
            self.main_window,
            "Potwierdź przeniesienie",
            f"Czy na pewno chcesz przenieść {len(controller.unpaired_archives)} "
            f"niesparowanych archiwów do folderu '_bez_pary_'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Utwórz folder docelowy
            source_dir = controller.current_directory
            target_folder = os.path.join(source_dir, "_bez_pary_")

            try:
                os.makedirs(target_folder, exist_ok=True)

                # Uruchom worker do przenoszenia
                self._start_move_unpaired_worker(
                    controller.unpaired_archives, target_folder
                )

            except Exception as e:
                logging.error(f"Błąd podczas tworzenia folderu docelowego: {e}")
                QMessageBox.critical(
                    self.main_window,
                    "Błąd",
                    f"Nie można utworzyć folderu docelowego:\n{str(e)}",
                )

    def _start_move_unpaired_worker(self, unpaired_archives: list, target_folder: str):
        """
        Uruchamia worker do przenoszenia niesparowanych archiwów.

        Args:
            unpaired_archives: Lista ścieżek do archiwów do przeniesienia
            target_folder: Folder docelowy
        """
        try:
            from src.ui.delegates.workers.bulk_workers import MoveUnpairedArchivesWorker

            # Uruchom worker
            self.main_window.worker_manager.run_worker(
                MoveUnpairedArchivesWorker,
                on_finished=self._on_move_unpaired_finished,
                on_error=self._on_move_unpaired_error,
                show_progress=True,
                unpaired_archives=unpaired_archives,
                target_folder=target_folder,
            )

            logging.info(f"Rozpoczęto przenoszenie {len(unpaired_archives)} archiwów")

        except Exception as e:
            logging.error(f"Błąd podczas uruchamiania worker'a przenoszenia: {e}")
            QMessageBox.critical(
                self.main_window,
                "Błąd",
                f"Nie można uruchomić operacji przenoszenia:\n{str(e)}",
            )

    def _on_move_unpaired_finished(self, result):
        """
        Obsługuje zakończenie przenoszenia niesparowanych archiwów.

        Args:
            result: Wynik operacji przenoszenia
        """
        moved_files = result.get("moved_files", [])
        detailed_errors = result.get("detailed_errors", [])
        summary = result.get("summary", {})

        logging.info(f"Przenoszenie zakończone: {len(moved_files)} plików przeniesiono")

        # Pokaż raport
        self._show_move_unpaired_report(moved_files, detailed_errors, summary)

        # Odśwież widoki
        self._refresh_unpaired_files()

    def _on_move_unpaired_error(self, error_message: str):
        """
        Obsługuje błąd podczas przenoszenia niesparowanych archiwów.

        Args:
            error_message: Opis błędu
        """
        logging.error(f"Błąd przenoszenia archiwów: {error_message}")

        QMessageBox.critical(
            self.main_window,
            "Błąd przenoszenia",
            f"Wystąpił błąd podczas przenoszenia archiwów:\n{error_message}",
        )

    def _show_move_unpaired_report(
        self, moved_files: list, detailed_errors: list, summary: dict
    ):
        """
        Wyświetla raport z operacji przenoszenia niesparowanych archiwów.

        Args:
            moved_files: Lista pomyślnie przeniesionych plików
            detailed_errors: Lista szczegółowych błędów
            summary: Podsumowanie operacji
        """
        total_files = summary.get("total_requested", 0)
        successful_moves = summary.get("successfully_moved", 0)
        failed_moves = summary.get("errors", 0)

        # Przygotuj tekst raportu
        report_text = f"Raport przenoszenia niesparowanych archiwów:\n\n"
        report_text += f"Łącznie plików: {total_files}\n"
        report_text += f"Pomyślnie przeniesiono: {successful_moves}\n"
        report_text += f"Błędy: {failed_moves}\n\n"

        if moved_files:
            report_text += "Przeniesione pliki:\n"
            for file_info in moved_files[:10]:  # Pokaż max 10 plików
                # file_info to tuple (source_path, target_path)
                if isinstance(file_info, tuple) and len(file_info) >= 2:
                    source_path, target_path = file_info[:2]
                    filename = os.path.basename(source_path)
                    report_text += f"• {filename}\n"
                else:
                    # Fallback dla innych formatów
                    report_text += f"• {str(file_info)}\n"
            if len(moved_files) > 10:
                report_text += f"... i {len(moved_files) - 10} więcej\n"
            report_text += "\n"

        if detailed_errors:
            report_text += "Błędy:\n"
            for error in detailed_errors[:5]:  # Pokaż max 5 błędów
                report_text += f"• {error}\n"
            if len(detailed_errors) > 5:
                report_text += f"... i {len(detailed_errors) - 5} więcej błędów\n"

        # Wyświetl dialog z raportem
        msg_box = QMessageBox(self.main_window)
        msg_box.setWindowTitle("Raport przenoszenia")
        msg_box.setText(report_text)

        if failed_moves > 0:
            msg_box.setIcon(QMessageBox.Icon.Warning)
        else:
            msg_box.setIcon(QMessageBox.Icon.Information)

        msg_box.exec()

    def _refresh_unpaired_files(self):
        """Odświeża listy niesparowanych plików."""
        if hasattr(self.main_window, "controller"):
            try:
                # Użyj metody refresh_all_views z głównego okna
                if hasattr(self.main_window, "refresh_all_views"):
                    self.main_window.refresh_all_views()
                else:
                    # Fallback - bezpośrednie odświeżenie kontrolera
                    self.main_window.controller.handle_refresh_request(force_full=False)

            except Exception as e:
                logging.error(f"Błąd podczas odświeżania niesparowanych plików: {e}")

    def get_widgets_for_main_window(self):
        """
        Zwraca słownik z widgetami do użycia w głównym oknie.

        Returns:
            dict: Słownik z widgetami
        """
        return {
            "unpaired_files_tab": self.unpaired_files_tab,
            "pair_manually_button": self.pair_manually_button,
            "unpaired_archives_list_widget": self.unpaired_archives_list_widget,
            "unpaired_previews_list_widget": self.unpaired_previews_list_widget,
        }

    def update_thumbnail_size(self, new_size):
        """
        Aktualizuje rozmiar miniaturek w kafelkach podglądów.

        Args:
            new_size: Nowy rozmiar miniaturek
        """
        self.current_thumbnail_size = new_size

        # Aktualizuj wszystkie istniejące kafelki
        for tile in self.preview_tile_widgets:
            tile.set_thumbnail_size(new_size)

        logging.debug(f"Zaktualizowano rozmiar miniaturek na: {new_size}")

    def _handle_delete_unpaired_previews(self):
        """Obsługuje usuwanie wszystkich niesparowanych podglądów."""
        if not self.preview_tile_widgets:
            QMessageBox.information(
                self.main_window,
                "Brak plików",
                "Nie ma niesparowanych podglądów do usunięcia.",
            )
            return

        # Pokaż dialog potwierdzenia
        reply = QMessageBox.question(
            self.main_window,
            "Potwierdź usunięcie",
            f"Czy na pewno chcesz usunąć {len(self.preview_tile_widgets)} "
            f"niesparowanych podglądów z dysku?\n\n"
            f"Ta operacja jest nieodwracalna!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Zbierz ścieżki do usunięcia
            previews_to_delete = [
                tile.preview_path for tile in self.preview_tile_widgets
            ]

            # Uruchom worker do usuwania
            self._start_delete_unpaired_previews_worker(previews_to_delete)

    def _start_delete_unpaired_previews_worker(self, previews_to_delete: list[str]):
        """
        Uruchamia worker do usuwania niesparowanych podglądów.

        Args:
            previews_to_delete: Lista ścieżek do plików do usunięcia
        """
        try:
            # Uruchom worker
            self.main_window.worker_manager.run_worker(
                BulkDeleteFilesWorker,
                on_finished=self._on_delete_unpaired_previews_finished,
                on_error=self._on_delete_unpaired_previews_error,
                show_progress=True,
                files_to_delete=previews_to_delete,
            )

            logging.info(f"Rozpoczęto usuwanie {len(previews_to_delete)} podglądów")

        except Exception as e:
            logging.error(f"Błąd podczas uruchamiania worker'a usuwania: {e}")
            QMessageBox.critical(
                self.main_window,
                "Błąd",
                f"Nie można uruchomić operacji usuwania:\n{str(e)}",
            )

    def _on_delete_unpaired_previews_finished(self, result: dict):
        """
        Obsługuje zakończenie usuwania niesparowanych podglądów.

        Args:
            result: Wynik operacji usuwania
        """
        deleted_files = result.get("deleted_files", [])
        failed_deletions = result.get("failed_deletions", [])

        logging.info(f"Usuwanie zakończone: {len(deleted_files)} plików usunięto")

        # Wyczyść interfejs
        self.clear_unpaired_files_lists()

        # Pokaż raport
        report_text = f"Usunięto {len(deleted_files)} z {len(deleted_files) + len(failed_deletions)} plików.\n"
        if failed_deletions:
            report_text += f"\nBłędy przy {len(failed_deletions)} plikach."

        QMessageBox.information(self.main_window, "Usuwanie zakończone", report_text)

        # Odśwież widoki
        self._refresh_unpaired_files()

    def _on_delete_unpaired_previews_error(self, error_message: str):
        """
        Obsługuje błąd podczas usuwania niesparowanych podglądów.

        Args:
            error_message: Opis błędu
        """
        logging.error(f"Błąd usuwania podglądów: {error_message}")

        QMessageBox.critical(
            self.main_window,
            "Błąd usuwania",
            f"Wystąpił błąd podczas usuwania podglądów:\n{error_message}",
        )

    def _show_preview_dialog(self, preview_path: str):
        """
        Wyświetla dialog podglądu dla wybranego pliku.

        Args:
            preview_path: Ścieżka do pliku podglądu
        """
        try:
            pixmap = QPixmap(preview_path)
            if pixmap.isNull():
                QMessageBox.warning(
                    self.main_window,
                    "Błąd podglądu",
                    f"Nie można załadować obrazu:\n{preview_path}",
                )
                return

            dialog = PreviewDialog(pixmap, self.main_window)
            dialog.exec()
        except Exception as e:
            logging.error(f"Błąd podczas otwierania podglądu {preview_path}: {e}")
            QMessageBox.warning(
                self.main_window,
                "Błąd podglądu",
                f"Nie można otworzyć podglądu:\n{preview_path}\n\nBłąd: {str(e)}",
            )

    def _on_preview_checkbox_changed(self, checkbox, preview_path, state):
        """
        Obsługuje zmianę stanu checkbox podglądu.
        Zapewnia że tylko jeden podgląd może być zaznaczony jednocześnie.

        Args:
            checkbox: Widget checkbox który został zmieniony
            preview_path: Ścieżka do pliku podglądu
            state: Nowy stan checkbox (Qt.CheckState)
        """
        if state == Qt.CheckState.Checked.value:
            # Odznacz wszystkie inne checkboxy
            for tile in self.ui_manager.preview_tile_widgets:
                if tile.checkbox != checkbox and tile.checkbox.isChecked():
                    tile.checkbox.blockSignals(True)
                    tile.checkbox.setChecked(False)
                    tile.checkbox.blockSignals(False)

            # Ustaw wybrany podgląd
            self._select_preview_for_pairing(preview_path)
        else:
            # Jeśli odznaczono, wyczyść wybór
            self._select_preview_for_pairing(None)

        # Aktualizuj stan przycisków
        self._update_pair_button_state()

    def _select_preview_for_pairing(self, preview_path):
        """
        Ustawia wybrany podgląd do sparowania.

        Args:
            preview_path: Ścieżka do podglądu lub None aby wyczyścić wybór
        """
        if hasattr(self.main_window, "controller"):
            self.main_window.controller.selected_preview_for_pairing = preview_path
            logging.debug(f"Wybrano podgląd do parowania: {preview_path}")

    def _delete_preview_file(self, preview_path):
        """
        Usuwa plik podglądu z dysku i aktualizuje interfejs.

        Args:
            preview_path: Ścieżka do pliku podglądu do usunięcia
        """
        try:
            if os.path.exists(preview_path):
                os.remove(preview_path)
                logging.info(f"Usunięto plik podglądu: {preview_path}")

                # ETAP 2: Usuń przez UI manager
                self.ui_manager.remove_preview_tile(preview_path)

                # Aktualizuj stan przycisków
                self._update_pair_button_state()

                # Odśwież widok
                self._refresh_unpaired_files()

        except Exception as e:
            logging.error(f"Błąd podczas usuwania podglądu {preview_path}: {e}")
            QMessageBox.critical(
                self.main_window,
                "Błąd usuwania",
                f"Nie można usunąć pliku:\n{preview_path}\n\nBłąd: {str(e)}",
            )
