"""
BulkOperationsManager - zarządzanie operacjami masowymi.
Przeniesione z main_window.py w ramach refaktoryzacji.
"""

import logging

from PyQt6.QtWidgets import QMessageBox


class BulkOperationsManager:
    """Zarządzanie operacjami masowymi na plikach."""

    def __init__(self, main_window):
        """
        Inicjalizuje BulkOperationsManager.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def perform_bulk_delete(self):
        """
        ETAP 2 FINAL: Delegacja bulk delete do MainWindowController (MVC).
        """
        if not self.main_window.controller.selection_manager.selected_tiles:
            return

        # DELEGACJA DO KONTROLERA - NO MORE DIRECT UI LOGIC!
        success = self.main_window.controller.handle_bulk_delete(
            list(self.main_window.controller.selection_manager.selected_tiles)
        )

        if success:
            # Wyczyść selekcję po pomyślnej operacji
            self.main_window.controller.selection_manager.selected_tiles.clear()
            self.main_window.selection_manager.update_bulk_operations_visibility()
            logging.info("Controller bulk delete SUCCESS")
        else:
            logging.warning("Controller bulk delete FAILED or CANCELLED")

    def on_bulk_delete_finished(self, deleted_pairs):
        """
        Slot wywoływany po zakończeniu masowego usuwania plików.

        Args:
            deleted_pairs: Lista pomyślnie usuniętych par plików
        """
        if not deleted_pairs:
            self.main_window._show_progress(100, "Usuwanie przerwane lub nieudane")
            return

        # Zapamiętaj oryginalną liczbę zaznaczonych par PRZED ich usunięciem
        original_selected_count = len(self.main_window.controller.selection_manager.selected_tiles)

        # Usuń pary z głównej listy i selekcji
        for file_pair in deleted_pairs:
            if file_pair in self.main_window.controller.current_file_pairs:
                self.main_window.controller.current_file_pairs.remove(file_pair)
            if file_pair in self.main_window.controller.selection_manager.selected_tiles:
                self.main_window.controller.selection_manager.selected_tiles.remove(file_pair)

        # Odśwież galerie i listy
        self.main_window.data_manager.refresh_all_views()

        # Pokaż komunikat o sukcesie
        deleted_count = len(deleted_pairs)
        success_message = (
            f"Pomyślnie usunięto {deleted_count} z {original_selected_count} "
            f"zaznaczonych par plików."
        )
        self.main_window._show_progress(100, success_message)

        # Wyczyść selekcję i ukryj panel operacji masowych
        self.main_window.controller.selection_manager.selected_tiles.clear()
        self.main_window.selection_manager.update_bulk_operations_visibility()

        logging.info(f"Bulk delete completed: {deleted_count} pairs deleted")

    def perform_bulk_move(self):
        """
        Wykonuje masowe przenoszenie zaznaczonych par plików.
        """
        if not self.main_window.controller.selection_manager.selected_tiles:
            return

        # Delegacja do FileOperationsCoordinator
        self.main_window.file_operations_coordinator.perform_bulk_move()

    def on_bulk_move_finished(self, result):
        """
        Slot wywoływany po zakończeniu masowego przenoszenia plików.

        Args:
            result: Słownik z wynikami operacji przenoszenia
        """
        moved_pairs = result.get("moved_pairs", [])
        detailed_errors = result.get("detailed_errors", [])
        skipped_files = result.get("skipped_files", [])
        summary = result.get("summary", {})

        if not moved_pairs and not detailed_errors and not skipped_files:
            self.main_window._show_progress(100, "Przenoszenie przerwane")
            return

        # Usuń przeniesione pary z głównej listy i selekcji
        for file_pair in moved_pairs:
            if file_pair in self.main_window.controller.current_file_pairs:
                self.main_window.controller.current_file_pairs.remove(file_pair)
            if file_pair in self.main_window.controller.selection_manager.selected_tiles:
                self.main_window.controller.selection_manager.selected_tiles.remove(file_pair)

        # Odśwież galerie i listy
        self.main_window.data_manager.refresh_all_views()

        # Pokaż szczegółowy raport
        self.show_detailed_move_report(
            moved_pairs, detailed_errors, skipped_files, summary
        )

        # Wyczyść selekcję i ukryj panel operacji masowych
        self.main_window.controller.selection_manager.selected_tiles.clear()
        self.main_window.selection_manager.update_bulk_operations_visibility()

        # Odśwież folder źródłowy po przeniesieniu
        self.refresh_source_folder_after_move()

        logging.info(f"Bulk move completed: {len(moved_pairs)} pairs moved")

    def refresh_source_folder_after_move(self):
        """
        Odświeża folder źródłowy po operacji przenoszenia.
        """
        if not self.main_window.controller.current_directory:
            return

        # Sprawdź czy folder źródłowy nadal istnieje
        import os

        if not os.path.exists(self.main_window.controller.current_directory):
            logging.warning(
                f"Folder źródłowy już nie istnieje: "
                f"{self.main_window.controller.current_directory}"
            )
            return

        # Odśwież drzewo katalogów
        if hasattr(self.main_window, "directory_tree_manager"):
            try:
                self.main_window.directory_tree_manager.refresh_directory_tree()
                logging.debug("Directory tree refreshed after bulk move")
            except Exception as e:
                logging.error(f"Error refreshing directory tree: {e}")

        # Odśwież zakładkę eksploratora plików
        if hasattr(self.main_window, "file_explorer_tab"):
            try:
                current_path = self.main_window.file_explorer_tab.get_current_path()
                if current_path:
                    self.main_window.file_explorer_tab.refresh_current_directory()
                    logging.debug("File explorer refreshed after bulk move")
            except Exception as e:
                logging.error(f"Error refreshing file explorer: {e}")

    def show_detailed_move_report(
        self, moved_pairs, detailed_errors, skipped_files, summary
    ):
        """
        Wyświetla szczegółowy raport z operacji przenoszenia.
        """
        report_lines = []

        # Nagłówek
        report_lines.append("=== RAPORT PRZENOSZENIA PLIKÓW ===\n")

        # Podsumowanie
        if summary:
            report_lines.append("PODSUMOWANIE:")
            for key, value in summary.items():
                if key == "total_files":
                    report_lines.append(f"• Łącznie plików: {value}")
                elif key == "moved_files":
                    report_lines.append(f"• Przeniesione: {value}")
                elif key == "failed_files":
                    report_lines.append(f"• Nieudane: {value}")
                elif key == "skipped_files":
                    report_lines.append(f"• Pominięte: {value}")
            report_lines.append("")

        # Przeniesione pliki
        if moved_pairs:
            report_lines.append(f"✅ PRZENIESIONE ({len(moved_pairs)}):")
            for file_pair in moved_pairs[:10]:  # Pokaż maksymalnie 10
                report_lines.append(f"• {file_pair.get_base_name()}")
            if len(moved_pairs) > 10:
                remaining = len(moved_pairs) - 10
                report_lines.append(f"... i {remaining} więcej")
            report_lines.append("")

        # Błędy
        if detailed_errors:
            report_lines.append(f"❌ BŁĘDY ({len(detailed_errors)}):")
            for error in detailed_errors[:5]:  # Pokaż maksymalnie 5 błędów
                if isinstance(error, dict):
                    file_name = error.get("file", "Nieznany plik")
                    error_msg = error.get("error", "Nieznany błąd")
                    report_lines.append(f"• {file_name}: {error_msg}")
                else:
                    report_lines.append(f"• {error}")
            if len(detailed_errors) > 5:
                remaining = len(detailed_errors) - 5
                report_lines.append(f"... i {remaining} więcej błędów")
            report_lines.append("")

        # Pominięte pliki
        if skipped_files:
            report_lines.append(f"⚠️ POMINIĘTE ({len(skipped_files)}):")
            for skipped in skipped_files[:5]:  # Pokaż maksymalnie 5
                if isinstance(skipped, dict):
                    file_name = skipped.get("file", "Nieznany plik")
                    reason = skipped.get("reason", "Nieznany powód")
                    report_lines.append(f"• {file_name}: {reason}")
                else:
                    report_lines.append(f"• {skipped}")
            if len(skipped_files) > 5:
                remaining = len(skipped_files) - 5
                report_lines.append(f"... i {remaining} więcej pominiętych")

        # Wyświetl raport
        report_text = "\n".join(report_lines)

        msg_box = QMessageBox(self.main_window)
        msg_box.setWindowTitle("Raport Przenoszenia")
        msg_box.setText("Operacja przenoszenia została zakończona.")
        msg_box.setDetailedText(report_text)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()

    def confirm_bulk_delete(self, count: int) -> bool:
        """
        Wyświetla dialog potwierdzenia masowego usuwania.

        Args:
            count: Liczba elementów do usunięcia

        Returns:
            True jeśli użytkownik potwierdził, False w przeciwnym razie
        """
        reply = QMessageBox.question(
            self.main_window,
            "Potwierdzenie usuwania",
            f"Czy na pewno chcesz usunąć {count} zaznaczonych par plików?\n\n"
            "Ta operacja jest nieodwracalna!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def update_after_bulk_operation(self, processed_pairs, operation_name: str):
        """
        Aktualizuje interfejs po operacji masowej.

        Args:
            processed_pairs: Lista przetworzonych par plików
            operation_name: Nazwa operacji (np. "usuwanie", "przenoszenie")
        """
        # Usuń przetworzone pary z głównej listy
        for file_pair in processed_pairs:
            if file_pair in self.main_window.controller.current_file_pairs:
                self.main_window.controller.current_file_pairs.remove(file_pair)

        # Odśwież widoki
        self.main_window.data_manager.refresh_all_views()

        # Wyczyść selekcję
        self.main_window.controller.selection_manager.selected_tiles.clear()
        self.main_window.selection_manager.update_bulk_operations_visibility()

        logging.info(f"Bulk {operation_name} completed: {len(processed_pairs)} pairs")
