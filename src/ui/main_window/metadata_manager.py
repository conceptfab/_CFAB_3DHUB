"""
MetadataManager - zarządzanie metadanami aplikacji.
Przeniesione z main_window.py w ramach refaktoryzacji.
"""

import logging

from PyQt6.QtCore import QTimer

from src.ui.delegates.workers import WorkerFactory


class MetadataManager:
    """Zarządzanie metadanami aplikacji."""

    def __init__(self, main_window):
        """
        Inicjalizuje MetadataManager.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def save_metadata(self):
        """
        Zapisuje metadane dla wszystkich par plików w osobnym wątku.
        Używa buforowania zmian.
        """
        if not self.main_window.controller.current_directory:
            logging.debug("Brak folderu roboczego lub par plików do zapisu metadanych.")
            return

        # Utwórz workera do zapisu metadanych używając fabryki
        worker = WorkerFactory.create_save_metadata_worker(
            self.main_window.controller.current_directory,
            self.main_window.controller.current_file_pairs,
            self.main_window.controller.unpaired_archives,
            self.main_window.controller.unpaired_previews,
        )

        # Podłącz sygnały
        self.main_window.worker_manager.setup_worker_connections(worker)
        worker.signals.finished.connect(self.on_metadata_saved)

        # Uruchom workera
        file_pairs_count = len(self.main_window.controller.current_file_pairs)
        self.main_window._show_progress(
            0,
            f"Zapisywanie metadanych dla {file_pairs_count} par plików...",
        )
        self.main_window.thread_pool.start(worker)

    def schedule_metadata_save(self):
        """Planuje zapis metadanych z opóźnieniem."""
        if not hasattr(self, "_metadata_save_timer"):
            self._metadata_save_timer = QTimer()
            self._metadata_save_timer.setSingleShot(True)
            self._metadata_save_timer.timeout.connect(self.save_metadata)

        # Zatrzymaj poprzedni timer jeśli istnieje
        self._metadata_save_timer.stop()
        # NAPRAWKA PROGRESYWNOŚĆ: Skrócono z 2000ms na 500ms
        self._metadata_save_timer.start(500)  # 500ms opóźnienia

    def force_immediate_metadata_save(self):
        """
        Wymusza natychmiastowy zapis metadanych w osobnym wątku.
        Używany dla gwiazdek i tagów kolorów - NIE BLOKUJE UI!
        """
        if not self.main_window.controller.current_directory:
            logging.debug("Brak folderu roboczego - pomijam zapis metadanych.")
            return

        # Utwórz workera dla natychmiastowego zapisu (bez timer delay)
        worker = WorkerFactory.create_save_metadata_worker(
            self.main_window.controller.current_directory,
            self.main_window.controller.current_file_pairs,
            self.main_window.controller.unpaired_archives,
            self.main_window.controller.unpaired_previews,
        )

        # Podłącz sygnały (ale bez progress bar - to szybka operacja)
        worker.signals.finished.connect(
            lambda success: (
                logging.info("✅ Gwiazdki/tagi zapisane w tle")
                if success
                else logging.error("❌ Błąd zapisu gwiazdek/tagów")
            )
        )
        worker.signals.error.connect(
            lambda error: logging.error(f"❌ Błąd workera zapisu metadanych: {error}")
        )

        # Uruchom w tle - NIE BLOKUJE UI!
        self.main_window.thread_pool.start(worker)
        logging.debug("🚀 Worker zapisu metadanych uruchomiony w tle")

    def on_metadata_saved(self, success):
        """
        Slot wywoływany po zakończeniu zapisu metadanych.

        Args:
            success: True jeśli metadane zostały zapisane pomyślnie
        """
        if success:
            self.main_window._show_progress(100, "Metadane zapisane pomyślnie")
            logging.debug("Metadane zapisane")
        else:
            self.main_window._show_progress(100, "Nie udało się zapisać metadanych")
            self.logger.error("Nie udało się zapisać metadanych.")

    def handle_stars_changed(self, file_pair, new_star_count):
        """Obsługuje zmianę liczby gwiazdek dla pary plików."""
        file_pair.set_stars(new_star_count)
        self.schedule_metadata_save()

    def handle_color_tag_changed(self, file_pair, new_color_tag):
        """Obsługuje zmianę tagu koloru dla pary plików."""
        file_pair.set_color_tag(new_color_tag)
        self.schedule_metadata_save()

    def request_metadata_save(self):
        """Żąda zapisu metadanych - delegacja z publicznego API."""
        self.schedule_metadata_save()
