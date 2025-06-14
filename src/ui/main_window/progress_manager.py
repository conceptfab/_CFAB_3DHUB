"""
Progress Manager dla MainWindow - zarządzanie paskami postępu i statusem.
Część refaktoryzacji ETAP 1: MainWindow.
"""

import logging

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox


class ProgressManager:
    """
    Zarządzanie paskami postępu i statusem MainWindow.

    Odpowiedzialności:
    - Zarządzanie paskiem postępu
    - Aktualizacja statusu aplikacji
    - Obsługa postępu ładowania miniaturek
    - Zarządzanie komunikatami o błędach
    """

    def __init__(self, main_window):
        """
        Inicjalizuje ProgressManager.

        Args:
            main_window: Referencja do głównego okna MainWindow
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

        self._total_tiles_to_create = 0
        self._tiles_created = 0
        self._thumbnails_loaded = 0
        self._batch_processing_started = False

    def show_progress(self, percent: int, message: str):
        """
        Aktualizuje pasek postępu i etykietę postępu.

        Args:
            percent: Wartość postępu (0-100)
            message: Wiadomość do wyświetlenia
        """
        # NAPRAWKA PROGRESS BAR: Ogranicz percent do zakresu 0-100
        percent = max(0, min(100, percent))

        self.main_window.progress_bar.setValue(percent)
        self.main_window.progress_label.setText(message)
        self.main_window.progress_bar.setVisible(True)

        # Jeśli osiągnięto 100%, ukryj pasek po krótkim czasie
        if percent >= 100:
            delay_ms = self.main_window.app_config.progress_hide_delay_ms
            QTimer.singleShot(delay_ms, self.hide_progress)

    def hide_progress(self):
        """Ukrywa pasek postępu i resetuje etykietę."""
        self.main_window.progress_bar.setVisible(False)
        self.main_window.progress_label.setText("Gotowy")

    def on_thumbnail_progress(self):
        """
        Wywoływana gdy miniatura zostanie załadowana.
        Aktualizuje progress bar dla ładowania miniaturek.
        """
        self._thumbnails_loaded += 1

        # NAPRAWKA PROGRESS BAR: Progress bar dla miniaturek (50-100%)
        if self._total_tiles_to_create > 0:
            thumbnail_percent = int(
                (self._thumbnails_loaded / max(self._total_tiles_to_create, 1)) * 50
            )
            # 50% za kafelki + 50% za miniaturki
            total_percent = 50 + thumbnail_percent

            message = (
                f"Ładowanie miniaturek: "
                f"{self._thumbnails_loaded}/{self._total_tiles_to_create}..."
            )
            self.show_progress(total_percent, message)

            # Ukryj progress bar gdy wszystkie miniaturki są załadowane
            if self._thumbnails_loaded >= self._total_tiles_to_create:
                # Ukryj po pół sekundy
                QTimer.singleShot(500, self.hide_progress)

    def init_batch_processing(self, total_tiles: int):
        """
        Inicjalizuje liczniki dla przetwarzania batch'a kafelków.

        Args:
            total_tiles: Całkowita liczba kafelków do utworzenia
        """
        self._total_tiles_to_create = total_tiles
        self._tiles_created = 0
        self._thumbnails_loaded = 0
        self._batch_processing_started = True
        self.logger.debug(f"Inicjalizacja batch processing: {total_tiles} kafelków")

    def update_tile_creation_progress(self, created_count: int):
        """
        NAPRAWKA PROGRESS BAR: Aktualizuje postęp tworzenia kafelków (0-50%).

        Args:
            created_count: Liczba utworzonych kafelków
        """
        self._tiles_created = created_count

        if self._total_tiles_to_create > 0:
            # Progress bar: 0-50% dla tworzenia kafelków
            percent = int((self._tiles_created / self._total_tiles_to_create) * 50)
            message = (
                f"Tworzenie kafelków: "
                f"{self._tiles_created}/{self._total_tiles_to_create}..."
            )
            self.show_progress(percent, message)

    def update_batch_progress(self, loaded_count: int):
        """
        PRZESTARZAŁE: Zastąpione przez update_tile_creation_progress.
        Zachowane dla kompatybilności wstecznej.

        Args:
            loaded_count: Liczba załadowanych kafelków
        """
        warning_msg = (
            "update_batch_progress jest przestarzałe - "
            "użyj update_tile_creation_progress"
        )
        self.logger.warning(warning_msg)
        self.update_tile_creation_progress(loaded_count)

    def handle_worker_error(self, error_message: str):
        """
        Obsługuje błędy zgłaszane przez workery.

        Args:
            error_message: Komunikat o błędzie
        """
        QMessageBox.critical(self.main_window, "Błąd", error_message)
        self.hide_progress()

    def reset_counters(self):
        """Resetuje wszystkie liczniki postępu."""
        self._tiles_created = 0
        self._total_tiles_to_create = 0
        self._thumbnails_loaded = 0
        self._batch_processing_started = False
        self.logger.debug("Resetowano liczniki progress bara")

    def is_batch_processing(self) -> bool:
        """
        Sprawdza czy trwa przetwarzanie batch'a.

        Returns:
            bool: True jeśli trwa przetwarzanie batch'a
        """
        return self._batch_processing_started

    def get_tiles_created(self) -> int:
        """
        NAPRAWKA PROGRESS BAR: Zwraca liczbę utworzonych kafelków.

        Returns:
            int: Liczba utworzonych kafelków
        """
        return self._tiles_created

    def get_thumbnails_loaded(self) -> int:
        """
        Zwraca liczbę załadowanych miniaturek.

        Returns:
            int: Liczba załadowanych miniaturek
        """
        return self._thumbnails_loaded

    def get_total_thumbnails(self) -> int:
        """
        Zwraca całkowitą liczbę miniaturek do załadowania.

        Returns:
            int: Całkowita liczba miniaturek
        """
        return self._total_tiles_to_create

    def finish_tile_creation(self):
        """
        NAPRAWKA PROGRESS BAR: Oznacza zakończenie tworzenia kafelków
        (50% progress).
        """
        if self._total_tiles_to_create > 0:
            message = (
                f"Kafelki utworzone: {self._tiles_created}/"
                f"{self._total_tiles_to_create}. Ładowanie miniaturek..."
            )
            self.show_progress(50, message)
            self.logger.debug(f"Zakończono tworzenie {self._tiles_created} kafelków")
