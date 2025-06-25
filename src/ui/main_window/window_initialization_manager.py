"""
WindowInitializationManager - zarządzanie inicjalizacją okna aplikacji.
🚀 ETAP 1 REFAKTORYZACJI: Wydzielenie logiki inicjalizacji z main_window.py
"""

import logging
import os

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QLabel, QProgressBar, QStatusBar


class WindowInitializationManager:
    """
    Manager odpowiedzialny za inicjalizację okna aplikacji.
    Obsługuje konfigurację, preferencje i podstawowe ustawienia okna.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje WindowInitializationManager.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def init_window_configuration(self):
        """
        Inicjalizuje konfigurację okna aplikacji.
        Ustawia timer resize, rozmiary miniaturek, tytuł okna i status bar.
        """
        # Poprawne ustawienie resize_timer z odpowiednią funkcją
        self.main_window.resize_timer = QTimer(self.main_window)
        self.main_window.resize_timer.setSingleShot(True)
        self.main_window.resize_timer.timeout.connect(
            self.main_window._on_resize_timer_timeout
        )
        # Ustawienie opóźnienia - używamy bezpośredniej wartości
        self.main_window.resize_timer.setInterval(50)  # 50ms opóźnienie

        # Konfiguracja rozmiarów miniaturek
        self.main_window.min_thumbnail_size = (
            self.main_window.app_config.min_thumbnail_size
        )
        self.main_window.max_thumbnail_size = (
            self.main_window.app_config.max_thumbnail_size
        )
        self.main_window.initial_slider_position = 50

        # PRIORYTET: default_thumbnail_size z konfiguracji użytkownika
        user_default_size = self.main_window.app_config.get("default_thumbnail_size")
        if user_default_size is not None:
            try:
                validated_size = int(user_default_size)
                if 20 <= validated_size <= 2000:  # Walidacja zakresu
                    self.main_window.current_thumbnail_size = validated_size
                    self.logger.info(f"Użyto default_thumbnail_size z konfiguracji: {validated_size}px")

                    # Opcjonalnie: oblicz pozycję suwaka na podstawie default_thumbnail_size
                    size_range = self.main_window.max_thumbnail_size - self.main_window.min_thumbnail_size
                    if size_range > 0:
                        calculated_position = ((validated_size - self.main_window.min_thumbnail_size) * 100) / size_range
                        self.main_window.initial_slider_position = max(0, min(100, int(calculated_position)))
                        self.logger.debug(f"Obliczona pozycja suwaka dla default_thumbnail_size: {self.main_window.initial_slider_position}%")
                    
                    # Zakończ - nie obliczaj z suwaka
                    self.logger.debug(
                        f"Initial slider position: {self.main_window.initial_slider_position}%, "
                        f"thumbnail size: {self.main_window.current_thumbnail_size}px (z default_thumbnail_size)"
                    )
                    
                    # Pozostała inicjalizacja okna
                    self.main_window.setWindowTitle("CFAB_3DHUB")
                    self.main_window.setMinimumSize(
                        self.main_window.app_config.window_min_width,
                        self.main_window.app_config.window_min_height,
                    )
                    self._setup_status_bar()
                    return
                else:
                    self.logger.warning(f"default_thumbnail_size poza zakresem 20-2000: {validated_size}")
            except (ValueError, TypeError) as e:
                self.logger.error(f"Błędna wartość default_thumbnail_size: {user_default_size} ({e})")

        # FALLBACK: Oblicz z suwaka tylko gdy brak prawidłowego default_thumbnail_size
        size_range = (
            self.main_window.max_thumbnail_size - self.main_window.min_thumbnail_size
        )
        if size_range <= 0:
            self.main_window.current_thumbnail_size = (
                self.main_window.min_thumbnail_size
            )
        else:
            self.main_window.current_thumbnail_size = (
                self.main_window.min_thumbnail_size
                + int((size_range * self.main_window.initial_slider_position) / 100)
            )
            self.logger.debug(f"Obliczono rozmiar z suwaka (brak default_thumbnail_size): {self.main_window.current_thumbnail_size}px")

        self.logger.debug(
            f"Initial slider position: {self.main_window.initial_slider_position}%, "
            f"thumbnail size: {self.main_window.current_thumbnail_size}px"
        )

        # Konfiguracja okna
        self.main_window.setWindowTitle("CFAB_3DHUB")
        self.main_window.setMinimumSize(
            self.main_window.app_config.window_min_width,
            self.main_window.app_config.window_min_height,
        )

        # Konfiguracja status bar
        self._setup_status_bar()

    def _setup_status_bar(self):
        """Konfiguruje status bar z progress bar i etykietą stanu."""
        self.main_window.status_bar = QStatusBar(self.main_window)
        self.main_window.setStatusBar(self.main_window.status_bar)

        # Progress bar
        self.main_window.progress_bar = QProgressBar()
        self.main_window.progress_bar.setFixedHeight(15)
        self.main_window.progress_bar.setRange(0, 100)
        self.main_window.progress_bar.setValue(0)
        self.main_window.progress_bar.setVisible(False)

        # Progress label
        self.main_window.progress_label = QLabel("Gotowy")
        self.main_window.progress_label.setStyleSheet(
            "color: gray; font-style: italic;"
        )

        # Dodaj do status bar
        self.main_window.status_bar.addWidget(self.main_window.progress_label, 1)
        self.main_window.status_bar.addPermanentWidget(self.main_window.progress_bar, 2)

    def show_preferences_loaded_confirmation(self):
        """
        Pokazuje potwierdzenie że preferencje zostały wczytane.
        """
        # Preferencje wczytane - tylko krótki komunikat
        self.logger.debug("Preferencje wczytane")

        # Pokaż w status barze
        self.main_window.progress_label.setText("Preferencje wczytane")
        self.main_window.progress_label.setStyleSheet(
            "color: green; font-weight: bold;"
        )

        # Po czasie z konfiguracji przywróć normalny status
        delay = self.main_window.app_config.preferences_status_display_ms
        QTimer.singleShot(
            delay, lambda: self.main_window.progress_label.setText("Gotowy")
        )
        QTimer.singleShot(
            delay,
            lambda: self.main_window.progress_label.setStyleSheet(
                "color: gray; font-style: italic;"
            ),
        )

    def auto_load_last_folder(self):
        """
        Automatycznie ładuje ostatni folder roboczy jeśli włączone w preferencjach.
        """
        if not self.main_window.app_config.get("auto_load_last_folder", False):
            self.logger.debug("Auto-load of last folder DISABLED in preferences")
            return

        last_folder = self.main_window.app_config.get("default_working_directory", "")
        if not last_folder:
            self.logger.debug("Brak zapisanego folderu roboczego")
            return

        if not os.path.exists(last_folder) or not os.path.isdir(last_folder):
            self.logger.warning(f"Zapisany folder roboczy nie istnieje: {last_folder}")
            return

        try:
            self.logger.debug(f"Auto-loading last folder: {last_folder}")
            # Ustaw flagę że to jest auto-loading (NIE nadpisuj domyślnego!)
            self.main_window._is_auto_loading = True
            self.main_window._select_working_directory(last_folder)
            # Usuń flagę po zakończeniu
            delattr(self.main_window, "_is_auto_loading")
        except Exception as e:
            self.logger.error(f"Błąd podczas auto-loading folderu {last_folder}: {e}")
            # Usuń flagę nawet przy błędzie
            if hasattr(self.main_window, "_is_auto_loading"):
                delattr(self.main_window, "_is_auto_loading")

    def handle_close_event(self, event):
        """
        Obsługuje zamykanie aplikacji - kończy wszystkie wątki.

        Args:
            event: QCloseEvent z Qt
        """
        # Delegacja do EventHandler
        self.main_window.event_handler.handle_close_event(event)

    def initialize_default_folder(self):
        """
        Inicjalizuje drzewo katalogów z domyślnym folderem jeśli ustawiony.
        """
        default_folder = self.main_window.app_config.get(
            "default_working_directory", ""
        )
        if (
            default_folder
            and os.path.exists(default_folder)
            and os.path.isdir(default_folder)
        ):
            self.logger.debug(f"Inicjalizacja drzewa katalogów: {default_folder}")
            self.main_window.directory_tree_manager.init_directory_tree_without_expansion(
                default_folder
            )
