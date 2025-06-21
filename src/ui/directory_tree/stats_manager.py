"""
Manager statystyk folderów dla drzewa katalogów.
Wydzielony z głównego managera w ramach refaktoryzacji.
"""

import logging
import os
from typing import TYPE_CHECKING, List, Optional, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox, QProgressDialog

from .data_classes import FolderStatistics
from .workers import FolderStatisticsWorker

if TYPE_CHECKING:
    from .manager import DirectoryTreeManager

logger = logging.getLogger(__name__)


class DirectoryTreeStatsManager:
    """
    Manager statystyk folderów.
    Wydzielony z głównego managera dla lepszej separacji odpowiedzialności.
    """

    def __init__(self, manager: "DirectoryTreeManager"):
        self.manager = manager
        self.parent_window = manager.parent_window
        self.data_manager = manager.data_manager
        self.worker_coordinator = manager.worker_coordinator

    def start_background_stats_calculation(self):
        """Rozpoczyna obliczanie statystyk dla widocznych folderów w tle - deleguje do worker_coordinator."""
        if not self.manager._main_working_directory:
            return

        # Pobierz listę wszystkich folderów w drzewie
        visible_folders = self._get_visible_folders()

        if not visible_folders:
            logger.debug("Brak widocznych folderów do obliczenia statystyk")
            return

        # Deleguj do worker_coordinator
        self.worker_coordinator.start_background_stats_calculation(
            visible_folders=visible_folders, data_manager=self.data_manager
        )

    def _get_visible_folders(self) -> List[str]:
        """
        Pobiera listę widocznych folderów - deleguje do data_manager.
        OPTYMALIZACJA: ~70% mniej wywołań skanowania dzięki cache.
        """
        if not self.manager._main_working_directory:
            return []

        # Aktualizuj working_directory w data_manager jeśli się zmienił
        if self.data_manager.working_directory != self.manager._main_working_directory:
            self.data_manager.working_directory = self.manager._main_working_directory

        return self.data_manager.get_visible_folders(
            model=self.manager.model,
            proxy_model=self.manager.proxy_model,
            should_show_folder_func=self.manager.should_show_folder,
        )

    def _create_stats_worker(self, folder_path: str) -> FolderStatisticsWorker:
        """Factory method dla tworzenia stats workerów."""

        def on_finished(stats):
            # Zapisz do cache i odśwież widok
            logger.debug(
                f"Statystyki: {os.path.basename(folder_path)} -> {stats.pairs_count} par"
            )
            self.manager.cache_folder_statistics(folder_path, stats)
            self._refresh_folder_display(folder_path)

        def on_error(error_msg):
            # Logi błędów dla diagnostyki
            logger.warning(f"STATYSTYKI ERROR: {folder_path} -> {error_msg}")

        worker = FolderStatisticsWorker(folder_path)
        worker.custom_signals.finished.connect(on_finished)
        worker.custom_signals.error.connect(on_error)

        return worker

    def _calculate_stats_async_silent(self, folder_path: str):
        """
        DEPRECATED: Deleguje do worker_coordinator.
        Zachowane dla kompatybilności wstecznej.
        """
        self.worker_coordinator.start_statistics_calculation(
            folder_path=folder_path,
            data_manager=self.data_manager,
            callback=lambda stats: self._refresh_folder_display(folder_path),
        )

    def _refresh_folder_display(self, folder_path: str):
        """Odświeża wyświetlanie konkretnego folderu w drzewie."""
        try:
            source_index = self.manager.model.index(folder_path)
            if source_index.isValid():
                proxy_index = self.manager.get_proxy_index_from_source(source_index)
                if proxy_index.isValid():
                    # Wymuszenie odświeżenia proxy model
                    self.manager.proxy_model.dataChanged.emit(
                        proxy_index, proxy_index, [Qt.ItemDataRole.DisplayRole]
                    )
                    logger.debug(f"Odświeżono wyświetlanie folderu: {folder_path}")
        except Exception as e:
            logger.debug(f"Błąd odświeżania widoku folderu {folder_path}: {e}")

    def calculate_folder_statistics_async(self, folder_path: str, callback=None):
        """Oblicza statystyki folderu asynchronicznie - deleguje do worker_coordinator."""

        def on_error(error_msg):
            logger.error(f"Błąd obliczania statystyk: {error_msg}")
            if callback:
                callback(None)

        self.worker_coordinator.start_statistics_calculation(
            folder_path=folder_path,
            data_manager=self.data_manager,
            callback=callback,
            error_callback=on_error,
        )

    def show_folder_statistics(self, folder_path: str):
        """Wyświetla statystyki folderu."""
        # Sprawdź cache
        cached_stats = self.manager.get_cached_folder_statistics(folder_path)
        if cached_stats:
            self._display_folder_statistics(cached_stats, folder_path)
            return

        # Utwórz progress dialog
        progress_dialog = QProgressDialog(
            f"Obliczanie statystyk dla '{os.path.basename(folder_path)}'...",
            "Anuluj",
            0,
            100,
            self.parent_window,
        )
        progress_dialog.setWindowTitle("Statystyki folderu")
        progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        progress_dialog.setValue(0)

        # Utwórz worker
        worker = FolderStatisticsWorker(folder_path)

        def on_finished(stats):
            progress_dialog.accept()
            self.manager.cache_folder_statistics(folder_path, stats)
            self._display_folder_statistics(stats, folder_path)

        def on_error(error_msg):
            progress_dialog.reject()
            QMessageBox.critical(
                self.parent_window,
                "Błąd obliczania statystyk",
                f"Nie można obliczyć statystyk folderu:\n{error_msg}",
            )

        def on_progress(percent, message):
            if progress_dialog.isVisible():
                progress_dialog.setValue(percent)
                progress_dialog.setLabelText(message)

        worker.custom_signals.finished.connect(on_finished)
        worker.custom_signals.error.connect(on_error)
        worker.custom_signals.progress.connect(on_progress)
        progress_dialog.canceled.connect(worker.interrupt)

        self.manager._start_worker(worker)
        progress_dialog.show()

    def _display_folder_statistics(self, stats: FolderStatistics, folder_path: str):
        """Wyświetla wyniki statystyk folderu."""
        folder_name = os.path.basename(folder_path)
        message = f"""Statystyki folderu '{folder_name}':

Rozmiar: {stats.size_gb:.2f} GB
Liczba par plików: {stats.pairs_count}
Całkowita liczba plików: {stats.total_files}

Dane z cache: {'Tak' if self.manager.get_cached_folder_statistics(folder_path) else 'Nie'}"""

        QMessageBox.information(
            self.parent_window, f"Statystyki - {folder_name}", message
        )

    def force_calculate_all_stats_async(self):
        """Wymuś przeliczenie statystyk dla wszystkich widocznych folderów."""
        if not self.manager._main_working_directory:
            return

        visible_folders = self._get_visible_folders()

        for folder_path in visible_folders:
            # Usuń z cache aby wymusić przeliczenie
            self.manager.invalidate_folder_cache(folder_path)
            # Rozpocznij przeliczanie
            self._calculate_stats_async_silent(folder_path)

        logger.info(
            f"Rozpoczęto przeliczanie statystyk dla {len(visible_folders)} folderów"
        )

    def _force_recalculate_folder_stats(self, folder_path: str):
        """Wymuś przeliczenie statystyk dla konkretnego folderu."""
        # Usuń z cache
        self.manager.invalidate_folder_cache(folder_path)
        # Rozpocznij przeliczanie
        self._calculate_stats_async_silent(folder_path)
        logger.info(f"Rozpoczęto przeliczanie statystyk dla folderu: {folder_path}")