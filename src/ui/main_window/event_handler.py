"""
EventHandler - obsługa zdarzeń i sygnałów.
🚀 ETAP 1: Refaktoryzacja MainWindow - komponent zdarzeń
"""

import logging
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMessageBox


class EventHandler:
    """
    Obsługa zdarzeń i sygnałów.
    🚀 ETAP 1: Wydzielony z MainWindow
    """

    def __init__(self, main_window):
        """
        Inicjalizuje EventHandler.
        
        Args:
            main_window: Referencja do głównego okna
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def handle_close_event(self, event):
        """
        Obsługuje zdarzenie zamknięcia okna.
        
        Args:
            event: Zdarzenie zamknięcia
        """
        self.logger.info("Zamykanie aplikacji...")
        
        try:
            # Wymuś natychmiastowe zapisanie metadanych przed zamknięciem
            if hasattr(self.main_window, '_force_immediate_metadata_save'):
                self.main_window._force_immediate_metadata_save()
            
            # Poczekaj chwilę na zapisanie
            QTimer.singleShot(100, lambda: self._finalize_close(event))
            
        except Exception as e:
            self.logger.error(f"Błąd podczas zamykania aplikacji: {e}")
            event.accept()

    def _finalize_close(self, event):
        """
        Finalizuje zamknięcie aplikacji.
        
        Args:
            event: Zdarzenie zamknięcia
        """
        try:
            # Zatrzymaj wszystkie wątki
            self._cleanup_threads()
            
            # Zapisz konfigurację okna
            self._save_window_state()
            
            self.logger.info("Aplikacja została zamknięta pomyślnie")
            event.accept()
            
        except Exception as e:
            self.logger.error(f"Błąd podczas finalizacji zamknięcia: {e}")
            event.accept()

    def _cleanup_threads(self):
        """Czyści wszystkie wątki."""
        try:
            # Zatrzymaj wątek skanowania
            if (
                hasattr(self.main_window, 'scan_thread') 
                and self.main_window.scan_thread 
                and self.main_window.scan_thread.isRunning()
            ):
                self.logger.debug("Zatrzymywanie wątku skanowania...")
                if hasattr(self.main_window, 'scan_worker') and self.main_window.scan_worker:
                    self.main_window.scan_worker.stop()
                
                self.main_window.scan_thread.quit()
                if not self.main_window.scan_thread.wait(3000):  # 3 sekundy timeout
                    self.logger.warning("Wymuszenie zakończenia wątku skanowania")
                    self.main_window.scan_thread.terminate()
                    self.main_window.scan_thread.wait(1000)

            # Zatrzymaj wątek przetwarzania danych
            if (
                hasattr(self.main_window, 'data_processing_thread') 
                and self.main_window.data_processing_thread 
                and self.main_window.data_processing_thread.isRunning()
            ):
                self.logger.debug("Zatrzymywanie wątku przetwarzania danych...")
                if hasattr(self.main_window, 'data_processing_worker') and self.main_window.data_processing_worker:
                    self.main_window.data_processing_worker.stop()
                
                self.main_window.data_processing_thread.quit()
                if not self.main_window.data_processing_thread.wait(3000):
                    self.logger.warning("Wymuszenie zakończenia wątku przetwarzania danych")
                    self.main_window.data_processing_thread.terminate()
                    self.main_window.data_processing_thread.wait(1000)

            # Zatrzymaj thread pool
            if hasattr(self.main_window, 'thread_pool'):
                self.main_window.thread_pool.waitForDone(3000)

        except Exception as e:
            self.logger.error(f"Błąd podczas czyszczenia wątków: {e}")

    def _save_window_state(self):
        """Zapisuje stan okna."""
        try:
            if hasattr(self.main_window, 'app_config'):
                # Zapisz rozmiar okna
                geometry = self.main_window.geometry()
                self.main_window.app_config.set("window_width", geometry.width())
                self.main_window.app_config.set("window_height", geometry.height())
                self.main_window.app_config.set("window_x", geometry.x())
                self.main_window.app_config.set("window_y", geometry.y())
                
                # Zapisz rozmiar miniatur
                if hasattr(self.main_window, 'current_thumbnail_size'):
                    self.main_window.app_config.set("thumbnail_size", self.main_window.current_thumbnail_size)
                
                self.logger.debug("Stan okna został zapisany")
                
        except Exception as e:
            self.logger.error(f"Błąd podczas zapisywania stanu okna: {e}")

    def handle_resize_event(self, event):
        """
        Obsługuje zdarzenie zmiany rozmiaru okna.
        
        Args:
            event: Zdarzenie zmiany rozmiaru
        """
        try:
            # Wywołaj oryginalną metodę
            super(type(self.main_window), self.main_window).resizeEvent(event)
            
            # Opóźnij odświeżenie galerii aby uniknąć zbyt częstych aktualizacji
            if hasattr(self.main_window, 'resize_timer'):
                self.main_window.resize_timer.start(300)  # 300ms opóźnienia
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi zmiany rozmiaru: {e}")

    def handle_preferences_changed(self):
        """Obsługuje zmianę preferencji."""
        try:
            self.logger.info("Preferencje zostały zmienione")
            
            # Odśwież konfigurację
            if hasattr(self.main_window, 'app_config'):
                self.main_window.app_config.reload_config()
            
            # Odśwież interfejs
            self._refresh_ui_after_preferences_change()
            
            # Pokaż komunikat
            if hasattr(self.main_window, 'status_bar'):
                self.main_window.status_bar.showMessage("Preferencje zostały zaktualizowane", 3000)
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi zmiany preferencji: {e}")

    def _refresh_ui_after_preferences_change(self):
        """Odświeża interfejs po zmianie preferencji."""
        try:
            # Odśwież rozmiary miniatur
            if hasattr(self.main_window, 'app_config'):
                self.main_window.min_thumbnail_size = self.main_window.app_config.min_thumbnail_size
                self.main_window.max_thumbnail_size = self.main_window.app_config.max_thumbnail_size
                
                # Aktualizuj suwak
                if hasattr(self.main_window, 'size_slider'):
                    current_value = self.main_window.size_slider.value()
                    size_range = self.main_window.max_thumbnail_size - self.main_window.min_thumbnail_size
                    if size_range > 0:
                        self.main_window.current_thumbnail_size = self.main_window.min_thumbnail_size + int(
                            (size_range * current_value) / 100
                        )
                        
                        # Aktualizuj etykietę
                        if hasattr(self.main_window, 'size_value_label'):
                            self.main_window.size_value_label.setText(f"{self.main_window.current_thumbnail_size}px")
            
            # Odśwież widoki
            if hasattr(self.main_window, 'refresh_all_views'):
                self.main_window.refresh_all_views()
                
        except Exception as e:
            self.logger.error(f"Błąd podczas odświeżania UI po zmianie preferencji: {e}")

    def handle_scan_finished(self, found_pairs, unpaired_archives, unpaired_previews):
        """
        Obsługuje zakończenie skanowania.
        
        Args:
            found_pairs: Lista znalezionych par plików
            unpaired_archives: Lista nieparowanych archiwów
            unpaired_previews: Lista nieparowanych podglądów
        """
        try:
            self.logger.info(f"Skanowanie zakończone: {len(found_pairs)} par, "
                           f"{len(unpaired_archives)} archiwów, {len(unpaired_previews)} podglądów")
            
            # Delegowanie do głównego okna
            if hasattr(self.main_window, '_handle_scan_finished'):
                self.main_window._handle_scan_finished(found_pairs, unpaired_archives, unpaired_previews)
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi zakończenia skanowania: {e}")

    def handle_scan_error(self, error_message: str):
        """
        Obsługuje błąd skanowania.
        
        Args:
            error_message: Komunikat błędu
        """
        try:
            self.logger.error(f"Błąd skanowania: {error_message}")
            
            # Pokaż komunikat błędu
            QMessageBox.critical(
                self.main_window,
                "Błąd skanowania",
                f"Wystąpił błąd podczas skanowania:\n\n{error_message}"
            )
            
            # Ukryj postęp
            if hasattr(self.main_window, 'hide_progress'):
                self.main_window.hide_progress()
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi błędu skanowania: {e}")

    def handle_worker_error(self, error_message: str):
        """
        Obsługuje błąd workera.
        
        Args:
            error_message: Komunikat błędu
        """
        try:
            self.logger.error(f"Błąd workera: {error_message}")
            
            # Pokaż komunikat błędu
            QMessageBox.warning(
                self.main_window,
                "Błąd operacji",
                f"Wystąpił błąd podczas operacji:\n\n{error_message}"
            )
            
            # Ukryj postęp
            if hasattr(self.main_window, 'hide_progress'):
                self.main_window.hide_progress()
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi błędu workera: {e}")

    def handle_tile_selection_changed(self, file_pair, is_selected: bool):
        """
        Obsługuje zmianę zaznaczenia kafelka.
        
        Args:
            file_pair: Para plików
            is_selected: Czy jest zaznaczona
        """
        try:
            # Delegowanie do głównego okna
            if hasattr(self.main_window, '_handle_tile_selection_changed'):
                self.main_window._handle_tile_selection_changed(file_pair, is_selected)
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi zmiany zaznaczenia: {e}")

    def handle_stars_changed(self, file_pair, new_star_count: int):
        """
        Obsługuje zmianę oceny gwiazdkowej.
        
        Args:
            file_pair: Para plików
            new_star_count: Nowa liczba gwiazdek
        """
        try:
            # Delegowanie do głównego okna
            if hasattr(self.main_window, '_handle_stars_changed'):
                self.main_window._handle_stars_changed(file_pair, new_star_count)
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi zmiany gwiazdek: {e}")

    def handle_color_tag_changed(self, file_pair, new_color_tag: str):
        """
        Obsługuje zmianę tagu kolorów.
        
        Args:
            file_pair: Para plików
            new_color_tag: Nowy tag koloru
        """
        try:
            # Delegowanie do głównego okna
            if hasattr(self.main_window, '_handle_color_tag_changed'):
                self.main_window._handle_color_tag_changed(file_pair, new_color_tag)
                
        except Exception as e:
            self.logger.error(f"Błąd podczas obsługi zmiany tagu koloru: {e}") 