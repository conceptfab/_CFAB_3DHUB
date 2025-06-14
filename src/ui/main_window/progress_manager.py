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
        
        # Liczniki dla ładowania miniaturek
        self._thumbnails_with_images_loaded = 0
        self._total_thumbnails_to_load = 0
        self._thumbnails_loaded = 0
        self._batch_processing_started = False
        
    def show_progress(self, percent: int, message: str):
        """
        Aktualizuje pasek postępu i etykietę postępu.

        Args:
            percent: Wartość postępu (0-100)
            message: Wiadomość do wyświetlenia
        """
        self.main_window.progress_bar.setValue(percent)
        self.main_window.progress_label.setText(message)
        self.main_window.progress_bar.setVisible(True)

        # Jeśli osiągnięto 100%, ukryj pasek po krótkim czasie
        if percent >= 100:
            QTimer.singleShot(
                self.main_window.app_config.progress_hide_delay_ms, self.hide_progress
            )

    def hide_progress(self):
        """Ukrywa pasek postępu i resetuje etykietę."""
        self.main_window.progress_bar.setVisible(False)
        self.main_window.progress_label.setText("Gotowy")

    def on_thumbnail_progress(self):
        """
        Wywoływana gdy miniatura zostanie załadowana.
        Aktualizuje progress bar dla ładowania miniaturek.
        """
        self._thumbnails_with_images_loaded += 1
        
        # Progress bar: 0-50% kafelki, 50-100% miniaturki
        if self._total_thumbnails_to_load > 0:
            thumbnail_percent = int(
                (
                    self._thumbnails_with_images_loaded
                    / max(self._total_thumbnails_to_load, 1)
                )
                * 50
            )
            total_percent = 50 + thumbnail_percent  # 50% za kafelki + 50% za miniaturki
            
            self.show_progress(
                total_percent,
                f"Ładowanie miniaturek: {self._thumbnails_with_images_loaded}/{self._total_thumbnails_to_load}...",
            )
            
            # Ukryj progress bar gdy wszystkie miniaturki są załadowane
            if self._thumbnails_with_images_loaded >= self._total_thumbnails_to_load:
                QTimer.singleShot(500, self.hide_progress)  # Ukryj po pół sekundy

    def init_batch_processing(self, total_thumbnails: int):
        """
        Inicjalizuje liczniki dla przetwarzania batch'a miniaturek.
        
        Args:
            total_thumbnails: Całkowita liczba miniaturek do załadowania
        """
        self._total_thumbnails_to_load = total_thumbnails
        self._thumbnails_loaded = 0
        self._thumbnails_with_images_loaded = 0
        self._batch_processing_started = True

    def update_batch_progress(self, loaded_count: int):
        """
        Aktualizuje postęp tworzenia kafelków w batch'u.
        
        Args:
            loaded_count: Liczba załadowanych kafelków
        """
        self._thumbnails_loaded = loaded_count
        
        # Aktualizuj progress bar dla tworzenia kafelków (bez miniaturek)
        percent = int(
            (self._thumbnails_loaded / max(self._total_thumbnails_to_load, 1)) * 50
        )  # 50% dla kafelków
        self.show_progress(
            percent,
            f"Tworzenie kafelków: {self._thumbnails_loaded}/{self._total_thumbnails_to_load}...",
        )

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
        self._thumbnails_with_images_loaded = 0
        self._total_thumbnails_to_load = 0
        self._thumbnails_loaded = 0
        self._batch_processing_started = False

    def is_batch_processing(self) -> bool:
        """
        Sprawdza czy trwa przetwarzanie batch'a.
        
        Returns:
            bool: True jeśli trwa przetwarzanie batch'a
        """
        return self._batch_processing_started

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
        return self._total_thumbnails_to_load 