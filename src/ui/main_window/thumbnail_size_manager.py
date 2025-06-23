"""
ThumbnailSizeManager - zarządzanie rozmiarem miniaturek.
🚀 ETAP 2 REFAKTORYZACJI: Wydzielenie logiki miniaturek z main_window.py
"""

import logging

from PyQt6.QtWidgets import QMainWindow


class ThumbnailSizeManager:
    """
    Manager odpowiedzialny za zarządzanie rozmiarem miniaturek.
    Obsługuje suwak rozmiaru, resize okna i aktualizację miniaturek.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje ThumbnailSizeManager.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def update_thumbnail_size(self):
        """
        Aktualizuje rozmiar miniatur w galerii na podstawie suwaka.
        """
        self.logger.debug("Aktualizacja rozmiaru miniatur z suwaka")
        try:
            # Pobierz wartość z suwaka
            if hasattr(self.main_window, "size_slider"):
                slider_value = self.main_window.size_slider.value()

                # Oblicz nowy rozmiar na podstawie wartości suwaka
                size_range = (
                    self.main_window.max_thumbnail_size
                    - self.main_window.min_thumbnail_size
                )
                if size_range <= 0:
                    self.main_window.current_thumbnail_size = (
                        self.main_window.min_thumbnail_size
                    )
                else:
                    # Oblicz rozmiar proporcjonalnie do pozycji suwaka (0-100%)
                    self.main_window.current_thumbnail_size = (
                        self.main_window.min_thumbnail_size
                        + int((size_range * slider_value) / 100)
                    )

                # Zapisz pozycję suwaka do konfiguracji
                if hasattr(self.main_window, "app_config"):
                    self.main_window.app_config.set_thumbnail_slider_position(
                        slider_value
                    )

                # Uruchom timer do aktualizacji rozmiaru
                if hasattr(self.main_window, "resize_timer"):
                    self.main_window.resize_timer.start()

                self.logger.debug(
                    f"Nowy rozmiar miniatur: {self.main_window.current_thumbnail_size}px "
                    f"(slider: {slider_value}%)"
                )
                self.logger.debug(
                    f"Zakres rozmiarów: {self.main_window.min_thumbnail_size}-"
                    f"{self.main_window.max_thumbnail_size}px"
                )
        except Exception as e:
            self.logger.error(f"Błąd obliczania rozmiaru miniatur: {e}", exc_info=True)

    def handle_resize_event(self, event):
        """
        Obsługuje zdarzenie zmiany rozmiaru okna.

        Args:
            event: QResizeEvent z Qt
        """
        # Wywołaj oryginalną metodę resizeEvent z QMainWindow
        QMainWindow.resizeEvent(self.main_window, event)

        # Uruchom timer resize dla miniaturek
        if hasattr(self.main_window, "resize_timer"):
            self.main_window.resize_timer.start()

    def on_resize_timer_timeout(self):
        """
        Aktualizuje widok galerii po zakończeniu zmiany rozmiaru.
        OPTYMALIZACJA: Używa tylko gallery_manager dla eliminacji redundancji.
        """
        self.logger.debug("Aktualizacja rozmiaru miniatur po timeout")
        try:
            # OPTYMALIZACJA: Używa tylko gallery_manager - eliminuje podwójne wywołania
            # gallery_tab_manager i unpaired_files_tab_manager używają tego samego gallery_manager
            if (
                hasattr(self.main_window, "gallery_manager")
                and self.main_window.gallery_manager
            ):
                self.main_window.gallery_manager.update_thumbnail_size(
                    self.main_window.current_thumbnail_size
                )

            self.logger.debug(
                f"Zaktualizowano rozmiar miniatur: "
                f"{self.main_window.current_thumbnail_size}px"
            )
        except Exception as e:
            self.logger.error(
                f"Błąd aktualizacji rozmiaru miniatur: {e}", exc_info=True
            )
