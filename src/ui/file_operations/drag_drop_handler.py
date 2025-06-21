"""
Drag Drop Handler - ETAP 4 refaktoryzacji file_operations_ui.py
Zarządza operacjami drag & drop i masowym przenoszeniem plików.
"""

import logging
import os
import shutil
from typing import List

from PyQt6.QtCore import QThreadPool, QTimer
from PyQt6.QtWidgets import QMessageBox

from src.logic.scanner import collect_files, create_file_pairs
from src.models.file_pair import FilePair
from src.ui.delegates.workers import BulkMoveWorker

logger = logging.getLogger(__name__)


class DragDropHandler:
    """
    Manager odpowiedzialny za obsługę drag & drop oraz masowe przenoszenie plików.
    
    Obsługuje upuszczanie plików na foldery, tworzenie par plików,
    przenoszenie pojedynczych plików i masowe operacje na parach.
    """
    
    def __init__(self, parent_window, progress_factory, worker_coordinator, detailed_reporting):
        """
        Initialize drag drop handler.
        
        Args:
            parent_window: Okno nadrzędne dla dialogów
            progress_factory: Factory do tworzenia dialogów postępu
            worker_coordinator: Coordinator dla workerów  
            detailed_reporting: Manager raportowania szczegółowego
        """
        self.parent_window = parent_window
        self.progress_factory = progress_factory
        self.worker_coordinator = worker_coordinator
        self.detailed_reporting = detailed_reporting
        
        logger.debug("DragDropHandler zainicjalizowany")
    
    def handle_drop_on_folder(self, urls: List, target_folder_path: str):
        """
        Obsługuje upuszczenie plików na folder w drzewie.

        Args:
            urls: Lista QUrl obiektów reprezentujących pliki do przeniesienia
            target_folder_path: Ścieżka do folderu docelowego
        """
        file_paths = [url.toLocalFile() for url in urls]
        logger.info(f"Dropped {len(file_paths)} files on folder {target_folder_path}")
        logger.debug(f"Files: {file_paths}")

        # Bezpośrednio rozpocznij przenoszenie bez pytania
        logger.info("Starting file move operation...")
        # Informuj o rozpoczęciu w pasku statusu
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(
                0, f"Przenoszenie {len(file_paths)} plików..."
            )

        try:
            # Zbierz wszystkie pliki z podanych ścieżek
            all_files = []
            for file_path in file_paths:
                if os.path.isfile(file_path):
                    all_files.append(file_path)
                    logger.debug(f"Added file: {file_path}")
                elif os.path.isdir(file_path):
                    logger.debug(f"Found folder, scanning contents: {file_path}")
                    # Jeśli to folder, zbierz pliki z niego
                    dir_file_map = collect_files(file_path, max_depth=1)
                    for files_list in dir_file_map.values():
                        all_files.extend(files_list)
                        logger.debug(f"Added files from folder: {files_list}")
                else:
                    logger.warning(f"Skipped non-existent item: {file_path}")

            logger.info(f"Found total {len(all_files)} files to move")

            if not all_files:
                if hasattr(self.parent_window, "_show_progress"):
                    self.parent_window._show_progress(
                        100, "Nie znaleziono plików do przeniesienia"
                    )
                logger.warning("ERROR - No files found to move")
                return False

            # Utwórz tymczasowy file_map dla algorytmu create_file_pairs
            temp_file_map = {}
            for file_path in all_files:
                dir_path = os.path.dirname(file_path)
                if dir_path not in temp_file_map:
                    temp_file_map[dir_path] = []
                temp_file_map[dir_path].append(file_path)

            logger.debug(f"Created file_map for {len(temp_file_map)} directories")

            # Utwórz pary plików używając strategii "best_match"
            file_pairs, _ = create_file_pairs(
                temp_file_map,
                target_folder_path,  # Użyj target_folder jako base_directory
                pair_strategy="best_match",
            )

            logger.info(f"Created {len(file_pairs)} file pairs")

            if not file_pairs:
                # Jeśli nie udało się utworzyć par, spróbuj przenieść pliki indywidualnie
                # (to może się zdarzyć dla pojedynczych plików bez pary)
                logger.warning("Failed to create file pairs. Moving individual files.")
                self.move_individual_files(all_files, target_folder_path)
                logger.info("SUCCESS - Moved files individually")
                return True

            # Użyj BulkMoveWorker do przeniesienia par plików
            logger.info(f"Starting BulkMoveWorker for {len(file_pairs)} pairs")
            self.move_file_pairs_bulk(file_pairs, target_folder_path)
            logger.info("SUCCESS - Started file pairs move operation")
            return True

        except Exception as e:
            logger.error(f"ERROR during file move operation: {e}", exc_info=True)
            if hasattr(self.parent_window, "_show_progress"):
                self.parent_window._show_progress(100, f"Błąd przenoszenia: {str(e)}")
            return False
    
    def move_individual_files(self, files: list[str], target_folder_path: str):
        """
        Przenosi pojedyncze pliki do folderu docelowego.

        Args:
            files: Lista ścieżek plików do przeniesienia
            target_folder_path: Ścieżka do folderu docelowego
        """
        logger.info(f"Moving {len(files)} individual files")
        logger.debug(f"Target folder: {target_folder_path}")

        try:
            for i, file_path in enumerate(files):
                filename = os.path.basename(file_path)
                destination_path = os.path.join(target_folder_path, filename)

                logger.debug(
                    f"Moving {i+1}/{len(files)}: {file_path} -> {destination_path}"
                )

                # Informuj o postępie w pasku statusu
                if hasattr(self.parent_window, "_show_progress"):
                    progress_percent = int((i / len(files)) * 100)
                    self.parent_window._show_progress(
                        progress_percent, f"Przenoszenie: {filename}"
                    )

                try:
                    shutil.move(file_path, destination_path)
                    logger.debug(f"Moved: {file_path} -> {destination_path}")
                except Exception as e:
                    logger.error(f"Error moving {file_path}: {e}")
                    # Usunięto QMessageBox.warning - błędy tylko w logach            

            # Zakończenie operacji
            if hasattr(self.parent_window, "_show_progress"):
                self.parent_window._show_progress(
                    100, f"Przeniesiono {len(files)} plików"
                )

            logger.info(f"Individual files move completed - moved {len(files)} files")

        except Exception as e:
            logger.error(f"Error during individual files move: {e}")
            if hasattr(self.parent_window, "_show_progress"):
                self.parent_window._show_progress(100, f"Błąd: {str(e)}")

        # NAPRAWKA DRAG&DROP PERFORMANCE: Odśwież widoki tylko jeśli nie ma bulk move
        # Dla bulk move _handle_bulk_move_finished() już obsługuje odświeżanie
        if hasattr(self.parent_window, "refresh_all_views") and callable(
            self.parent_window.refresh_all_views
        ):
            logger.debug("Refreshing views after individual file move")
            self.parent_window.refresh_all_views()
    
    def move_file_pairs_bulk(
        self, file_pairs: list[FilePair], target_folder_path: str
    ):
        """
        Przenosi pary plików używając BulkMoveWorker.

        Args:
            file_pairs: Lista par plików do przeniesienia
            target_folder_path: Ścieżka do folderu docelowego
        """
        if not file_pairs:
            logger.warning("move_file_pairs_bulk called with empty file list")
            return

        logger.info(f"Starting bulk move for {len(file_pairs)} file pairs")
        logger.debug(f"Target folder: {target_folder_path}")

        # Utwórz workera do masowego przenoszenia
        worker = BulkMoveWorker(file_pairs, target_folder_path)

        # Informuj o rozpoczęciu w pasku statusu
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(
                0, f"Przenoszenie {len(file_pairs)} par plików..."
            )

        # Podłącz sygnały workera
        worker.signals.finished.connect(
            lambda result: self._handle_bulk_move_finished(result)
        )
        worker.signals.error.connect(
            lambda err_msg: self._handle_bulk_move_error(err_msg)
        )
        worker.signals.progress.connect(
            lambda percent, msg: self._handle_bulk_move_progress(percent, msg)
        )

        logger.debug("Starting BulkMoveWorker...")
        # Uruchom workera
        QThreadPool.globalInstance().start(worker)
        logger.debug("BulkMoveWorker started successfully")
    
    # === BULK MOVE HANDLERS ===
    
    def _handle_bulk_move_finished(self, result):
        """
        Obsługuje zakończenie masowego przenoszenia par plików.

        Args:
            result: Słownik z wynikami operacji zawierający moved_pairs, detailed_errors, skipped_files i summary
        """
        # Wyciągnij dane z wyniku
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

        logger.info(
            f"Bulk move finished - successfully moved {len(moved_pairs)} file pairs"
        )

        # Informuj o zakończeniu w pasku statusu i ukryj po chwili
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(
                100, f"Przeniesiono {len(moved_pairs)} par plików"
            )
        if hasattr(self.parent_window, "_hide_progress"):
            self.parent_window._hide_progress()

        # Pokaż szczegółowy raport błędów jeśli wystąpiły
        if detailed_errors or skipped_files:
            self.detailed_reporting.show_detailed_move_report(
                moved_pairs, detailed_errors, skipped_files, summary
            )

        # 🔧 NAPRAWKA DRAG&DROP: Usuń przeniesione pary z struktur danych głównego okna
        # i odśwież folder źródłowy żeby usunąć pliki które już nie istnieją na dysku
        if hasattr(self.parent_window, "controller") and moved_pairs:
            # Usuń przeniesione pary z głównej listy
            for file_pair in moved_pairs:
                if file_pair in self.parent_window.controller.current_file_pairs:
                    self.parent_window.controller.current_file_pairs.remove(file_pair)
                # Usuń z zaznaczonych kafelków jeśli istnieje
                if hasattr(self.parent_window, "controller"):
                    self.parent_window.controller.selection_manager.selected_tiles.discard(file_pair)

            logger.debug(f"Removed {len(moved_pairs)} pairs from current_file_pairs")

            # Odśwież folder źródłowy używając tego samego mechanizmu co w głównym oknie
            if hasattr(self.parent_window, "_refresh_source_folder_after_move"):
                logger.debug("Odświeżanie folderu źródłowego po drag&drop")
                self.parent_window._refresh_source_folder_after_move()
            else:
                logger.warning(
                    "🔧 Drag&drop: Brak metody _refresh_source_folder_after_move - używam fallback BEZ resetu drzewa"
                )
                # Fallback - tylko odśwież widok BEZ resetowania drzewa
                if hasattr(self.parent_window, "refresh_all_views"):
                    self.parent_window.refresh_all_views()

        # NAPRAWKA DRAG&DROP PERFORMANCE: NIE wywołuj refresh_all_views() tutaj!
        # _refresh_source_folder_after_move() już odświeża widoki przez change_directory()
        # Podwójne odświeżanie spowalnia drag&drop ekstremalnie po refaktoryzacji MetadataManager
        logger.debug(
            "Pomijam refresh_all_views() - _refresh_source_folder_after_move() już odświeża widoki"
        )

    def _handle_bulk_move_error(self, error_message: str):
        """
        Obsługuje błędy podczas masowego przenoszenia.

        Args:
            error_message: Komunikat błędu
        """
        logger.error(f"Bulk move error: {error_message}")
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(100, f"Błąd: {error_message}")
        if hasattr(self.parent_window, "_hide_progress"):
            self.parent_window._hide_progress()

    def _handle_bulk_move_progress(self, percent: int, message: str):
        """
        Obsługuje postęp masowego przenoszenia.

        Args:
            percent: Procent ukończenia
            message: Komunikat postępu
        """
        logger.debug(f"Bulk move progress {percent}%: {message}")
        if hasattr(self.parent_window, "_show_progress"):
            self.parent_window._show_progress(percent, message) 