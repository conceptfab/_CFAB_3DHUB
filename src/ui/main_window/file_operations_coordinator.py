"""
FileOperationsCoordinator - koordynacja operacji na plikach dla MainWindow.
🚀 ETAP 1: Refaktoryzacja MainWindow - komponent operacji na plikach
"""

import logging
import os
from typing import List

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QWidget

from src.models.file_pair import FilePair
from src.ui.delegates.workers import BulkMoveWorker, BulkMoveFilesWorker
# Usunięto import nieistniejącej klasy BulkDeleteDialog


class FileOperationsCoordinator:
    """
    Koordynacja operacji na plikach dla MainWindow.
    
    Odpowiedzialności:
    - Operacje bulk delete i bulk move
    - Obsługa drag & drop plików na foldery
    - Callback'i po zakończeniu operacji
    - Pokazywanie raportów operacji
    """

    def __init__(self, main_window):
        """
        Inicjalizuje FileOperationsCoordinator.
        
        Args:
            main_window: Referencja do głównego okna MainWindow
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def perform_bulk_delete(self):
        """
        Wykonuje operację bulk delete na zaznaczonych plikach.
        Deleguje do kontrolera zgodnie z architekturą MVC.
        """
        if not hasattr(self.main_window, 'controller') or not self.main_window.controller:
            self.logger.error("Kontroler nie jest dostępny")
            return

        if not self.main_window.controller.selected_tiles:
            self.logger.warning("Brak zaznaczonych plików do usunięcia")
            return

        selected_count = len(self.main_window.controller.selected_tiles)
        self.logger.info(f"Rozpoczęcie bulk delete dla {selected_count} par plików")

        # Deleguj do kontrolera - używa wbudowanego potwierdzenia
        success = self.main_window.controller.handle_bulk_delete(
            list(self.main_window.controller.selected_tiles)
        )

        if success:
            # Wyczyść selekcję po pomyślnej operacji
            self.main_window.controller.selected_tiles.clear()
            if hasattr(self.main_window, '_update_bulk_operations_visibility'):
                self.main_window._update_bulk_operations_visibility()
            self.logger.info("Bulk delete zakończone pomyślnie")
        else:
            self.logger.warning("Bulk delete anulowane lub nieudane")

    def perform_bulk_move(self):
        """
        Wykonuje operację bulk move na zaznaczonych plikach.
        """
        if not self.main_window.selected_file_pairs:
            self.logger.warning("Brak zaznaczonych plików do przeniesienia")
            return

        selected_count = len(self.main_window.selected_file_pairs)
        self.logger.info(f"Rozpoczęcie bulk move dla {selected_count} par plików")

        # Wybierz folder docelowy
        target_folder = QFileDialog.getExistingDirectory(
            self.main_window,
            "Wybierz folder docelowy",
            self.main_window.app_config.get("default_working_directory", "")
        )

        if not target_folder:
            self.logger.info("Anulowano wybór folderu docelowego")
            return

        # Sprawdź czy folder docelowy istnieje
        if not os.path.exists(target_folder) or not os.path.isdir(target_folder):
            QMessageBox.warning(
                self.main_window,
                "Błąd",
                "Wybrany folder docelowy nie istnieje lub nie jest folderem."
            )
            return

        # Rozpocznij operację przenoszenia
        self.main_window.progress_manager.show_progress(0, f"Przenoszenie {selected_count} par plików...")
        
        # Uruchom worker do przenoszenia plików
        worker = BulkMoveWorker(self.main_window.selected_file_pairs, target_folder)
        self.main_window.worker_manager.setup_worker_connections(worker)
        
        # Podłącz callback po zakończeniu
        worker.finished.connect(lambda result: self.on_bulk_move_finished(result))
        
        # Uruchom worker
        self.main_window.thread_pool.start(worker)

    def handle_file_drop_on_folder(self, source_file_paths: List[str], target_folder_path: str):
        """
        Obsługuje przeciągnięcie plików na folder w drzewie katalogów.
        
        Args:
            source_file_paths: Lista ścieżek plików źródłowych
            target_folder_path: Ścieżka folderu docelowego
        """
        if not source_file_paths or not target_folder_path:
            self.logger.warning("Nieprawidłowe parametry drag & drop")
            return

        self.logger.info(f"Drag & drop: {len(source_file_paths)} plików do {target_folder_path}")

        # Sprawdź czy folder docelowy istnieje
        if not os.path.exists(target_folder_path) or not os.path.isdir(target_folder_path):
            QMessageBox.warning(
                self.main_window,
                "Błąd",
                "Folder docelowy nie istnieje lub nie jest folderem."
            )
            return

        # Pokaż progress
        self.main_window.progress_manager.show_progress(0, f"Przenoszenie {len(source_file_paths)} plików...")

        # Uruchom worker do przenoszenia plików (BulkMoveFilesWorker dla List[str])
        worker = BulkMoveFilesWorker(source_file_paths, target_folder_path)
        self.main_window.worker_manager.setup_worker_connections(worker)
        
        # Podłącz callback po zakończeniu (inny format wyniku dla BulkMoveFilesWorker)
        worker.finished.connect(lambda result: self.on_bulk_move_files_finished(result))
        
        # Uruchom worker
        self.main_window.thread_pool.start(worker)

    def on_bulk_delete_finished(self, deleted_pairs):
        """
        Callback po zakończeniu operacji bulk delete.
        
        Args:
            deleted_pairs: Lista usuniętych par plików
        """
        self.logger.info(f"Bulk delete zakończone: {len(deleted_pairs)} par usuniętych")
        
        # Ukryj progress
        self.main_window.progress_manager.hide_progress()
        
        # Usuń usunięte pary z listy
        for pair in deleted_pairs:
            if pair in self.main_window.file_pairs:
                self.main_window.file_pairs.remove(pair)
            if pair in self.main_window.selected_file_pairs:
                self.main_window.selected_file_pairs.remove(pair)

        # Odśwież widoki
        self.main_window.refresh_all_views()
        
        # Pokaż komunikat o sukcesie
        QMessageBox.information(
            self.main_window,
            "Operacja zakończona",
            f"Pomyślnie usunięto {len(deleted_pairs)} par plików."
        )

    def on_bulk_move_finished(self, result):
        """
        Callback po zakończeniu operacji bulk move (dla FilePair).
        
        Args:
            result: Wynik operacji przenoszenia
        """
        self.logger.info("Bulk move zakończone")
        
        # Ukryj progress
        self.main_window.progress_manager.hide_progress()
        
        # Rozpakuj wynik
        moved_pairs = result.get('moved_pairs', [])
        detailed_errors = result.get('detailed_errors', [])
        skipped_files = result.get('skipped_files', [])
        summary = result.get('summary', {})
        
        # Usuń przeniesione pary z listy
        for pair in moved_pairs:
            if pair in self.main_window.file_pairs:
                self.main_window.file_pairs.remove(pair)
            if pair in self.main_window.selected_file_pairs:
                self.main_window.selected_file_pairs.remove(pair)

        # Odśwież widoki
        self.main_window.refresh_all_views()
        
        # Pokaż szczegółowy raport
        self.show_detailed_move_report(moved_pairs, detailed_errors, skipped_files, summary)
        
        # Odśwież folder źródłowy po przenoszeniu
        self.refresh_source_folder_after_move()

    def on_bulk_move_files_finished(self, result):
        """
        Callback po zakończeniu operacji bulk move files (dla drag&drop).
        
        Args:
            result: Wynik operacji przenoszenia pojedynczych plików
        """
        self.logger.info("Bulk move files zakończone")
        
        # Ukryj progress
        self.main_window.progress_manager.hide_progress()
        
        # Rozpakuj wynik (inny format niż moved_pairs)
        moved_files = result.get('moved_files', [])
        detailed_errors = result.get('detailed_errors', [])
        skipped_files = result.get('skipped_files', [])
        summary = result.get('summary', {})
        
        # Odśwież widoki (nie usuwamy z file_pairs bo to były pojedyncze pliki)
        self.main_window.refresh_all_views()
        
        # Pokaż szczegółowy raport dla pojedynczych plików
        self.show_detailed_files_move_report(moved_files, detailed_errors, skipped_files, summary)
        
        # Odśwież folder źródłowy po przenoszeniu
        self.refresh_source_folder_after_move()

    def show_detailed_move_report(self, moved_pairs, detailed_errors, skipped_files, summary):
        """
        Pokazuje szczegółowy raport operacji przenoszenia.
        
        Args:
            moved_pairs: Lista przeniesionych par
            detailed_errors: Lista szczegółowych błędów
            skipped_files: Lista pominiętych plików
            summary: Podsumowanie operacji
        """
        # Przygotuj treść raportu
        report_lines = []
        
        # Podsumowanie
        report_lines.append("=== RAPORT OPERACJI PRZENOSZENIA ===\n")
        report_lines.append(f"Przeniesiono pomyślnie: {summary.get('moved_count', 0)} par plików")
        report_lines.append(f"Błędy: {summary.get('error_count', 0)}")
        report_lines.append(f"Pominięto: {summary.get('skipped_count', 0)}")
        report_lines.append("")
        
        # Przeniesione pliki
        if moved_pairs:
            report_lines.append("=== PRZENIESIONE PLIKI ===")
            for pair in moved_pairs[:10]:  # Pokaż maksymalnie 10
                report_lines.append(f"✓ {os.path.basename(pair.archive_path)}")
            if len(moved_pairs) > 10:
                report_lines.append(f"... i {len(moved_pairs) - 10} więcej")
            report_lines.append("")
        
        # Błędy
        if detailed_errors:
            report_lines.append("=== BŁĘDY ===")
            for error in detailed_errors[:5]:  # Pokaż maksymalnie 5 błędów
                report_lines.append(f"✗ {error}")
            if len(detailed_errors) > 5:
                report_lines.append(f"... i {len(detailed_errors) - 5} więcej błędów")
            report_lines.append("")
        
        # Pominięte pliki
        if skipped_files:
            report_lines.append("=== POMINIĘTE PLIKI ===")
            for skipped in skipped_files[:5]:  # Pokaż maksymalnie 5
                report_lines.append(f"⚠ {skipped}")
            if len(skipped_files) > 5:
                report_lines.append(f"... i {len(skipped_files) - 5} więcej")
        
        # Pokaż dialog z raportem
        report_text = "\n".join(report_lines)
        
        msg_box = QMessageBox(self.main_window)
        msg_box.setWindowTitle("Raport Operacji Przenoszenia")
        msg_box.setText("Operacja przenoszenia została zakończona.")
        msg_box.setDetailedText(report_text)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()

    def show_detailed_files_move_report(self, moved_files, detailed_errors, skipped_files, summary):
        """
        Pokazuje szczegółowy raport operacji przenoszenia pojedynczych plików.
        
        Args:
            moved_files: Lista przeniesionych plików (tuples: (source, target))
            detailed_errors: Lista szczegółowych błędów
            skipped_files: Lista pominiętych plików
            summary: Podsumowanie operacji
        """
        # Przygotuj treść raportu
        report_lines = []
        
        # Podsumowanie
        report_lines.append("=== RAPORT OPERACJI PRZENOSZENIA PLIKÓW ===\n")
        report_lines.append(f"Przeniesiono pomyślnie: {summary.get('successfully_moved', 0)} plików")
        report_lines.append(f"Błędy: {summary.get('errors', 0)}")
        report_lines.append(f"Pominięto: {summary.get('skipped', 0)}")
        report_lines.append("")
        
        # Przeniesione pliki
        if moved_files:
            report_lines.append("=== PRZENIESIONE PLIKI ===")
            for source_path, target_path in moved_files[:10]:  # Pokaż maksymalnie 10
                report_lines.append(f"✓ {os.path.basename(source_path)}")
            if len(moved_files) > 10:
                report_lines.append(f"... i {len(moved_files) - 10} więcej")
            report_lines.append("")
        
        # Błędy
        if detailed_errors:
            report_lines.append("=== BŁĘDY ===")
            for error in detailed_errors[:5]:  # Pokaż maksymalnie 5 błędów
                file_path = error.get('file_path', 'Nieznany')
                error_msg = error.get('error', 'Nieznany błąd')
                report_lines.append(f"✗ {os.path.basename(file_path)}: {error_msg}")
            if len(detailed_errors) > 5:
                report_lines.append(f"... i {len(detailed_errors) - 5} więcej błędów")
            report_lines.append("")
        
        # Pominięte pliki
        if skipped_files:
            report_lines.append("=== POMINIĘTE PLIKI ===")
            for skipped in skipped_files[:5]:  # Pokaż maksymalnie 5
                file_path = skipped.get('file_path', 'Nieznany')
                reason = skipped.get('reason', 'Nieznany powód')
                report_lines.append(f"⚠ {os.path.basename(file_path)}: {reason}")
            if len(skipped_files) > 5:
                report_lines.append(f"... i {len(skipped_files) - 5} więcej")
        
        # Pokaż dialog z raportem
        report_text = "\n".join(report_lines)
        
        msg_box = QMessageBox(self.main_window)
        msg_box.setWindowTitle("Raport Operacji Przenoszenia Plików")
        msg_box.setText("Operacja przenoszenia plików została zakończona.")
        msg_box.setDetailedText(report_text)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()

    def refresh_source_folder_after_move(self):
        """
        Odświeża folder źródłowy po operacji przenoszenia.
        """
        # Odśwież aktualny folder roboczy
        current_folder = getattr(self.main_window, 'current_working_directory', None)
        if current_folder and os.path.exists(current_folder):
            self.logger.info(f"Odświeżanie folderu źródłowego: {current_folder}")
            
            # Uruchom ponowne skanowanie folderu
            self.main_window._start_folder_scanning(current_folder)
        
        # Odśwież drzewo katalogów
        if hasattr(self.main_window, 'directory_tree_manager'):
            self.main_window.directory_tree_manager.refresh_tree()

    def show_file_context_menu(self, file_pair: FilePair, widget: QWidget, position):
        """
        Pokazuje menu kontekstowe dla pliku.
        
        Args:
            file_pair: Para plików
            widget: Widget na którym pokazać menu
            position: Pozycja menu
        """
        # Ta metoda może być rozszerzona w przyszłości
        # Na razie deleguje do istniejącej implementacji
        pass 