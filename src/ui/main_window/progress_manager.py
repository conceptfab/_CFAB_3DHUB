"""
ProgressManager - zarządzanie paskami postępu i statusem.
🚀 ETAP 1: Refaktoryzacja MainWindow - komponent postępu
"""

import logging
from PyQt6.QtCore import QTimer


class ProgressManager:
    """
    Zarządzanie paskami postępu i statusem.
    🚀 ETAP 1: Wydzielony z MainWindow
    """

    def __init__(self, main_window):
        """
        Inicjalizuje ProgressManager.
        
        Args:
            main_window: Referencja do głównego okna
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
        # Stan postępu
        self.current_progress = 0
        self.current_status = "Gotowy"
        self.is_progress_visible = False
        
        # Timer do automatycznego ukrywania postępu
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._auto_hide_progress)

    def show_progress(self, percent: int = 0, message: str = "Przetwarzanie..."):
        """
        Pokazuje pasek postępu.
        
        Args:
            percent: Procent postępu (0-100)
            message: Komunikat statusu
        """
        try:
            if not hasattr(self.main_window, 'progress_bar') or not hasattr(self.main_window, 'progress_label'):
                self.logger.warning("Komponenty postępu nie są zainicjalizowane")
                return
            
            # Aktualizuj stan
            self.current_progress = max(0, min(100, percent))
            self.current_status = message
            self.is_progress_visible = True
            
            # Aktualizuj UI
            self.main_window.progress_bar.setValue(self.current_progress)
            self.main_window.progress_label.setText(self.current_status)
            self.main_window.progress_bar.setVisible(True)
            
            # Zatrzymaj timer automatycznego ukrywania
            self.hide_timer.stop()
            
            self.logger.debug(f"Postęp: {self.current_progress}% - {self.current_status}")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pokazywania postępu: {e}")

    def hide_progress(self):
        """Ukrywa pasek postępu."""
        try:
            if not hasattr(self.main_window, 'progress_bar') or not hasattr(self.main_window, 'progress_label'):
                return
            
            # Aktualizuj stan
            self.is_progress_visible = False
            self.current_progress = 0
            self.current_status = "Gotowy"
            
            # Ukryj UI
            self.main_window.progress_bar.setVisible(False)
            self.main_window.progress_label.setText(self.current_status)
            self.main_window.progress_bar.setValue(0)
            
            # Zatrzymaj timer
            self.hide_timer.stop()
            
            self.logger.debug("Postęp ukryty")
            
        except Exception as e:
            self.logger.error(f"Błąd podczas ukrywania postępu: {e}")

    def update_progress(self, percent: int):
        """
        Aktualizuje procent postępu.
        
        Args:
            percent: Nowy procent postępu (0-100)
        """
        try:
            if not self.is_progress_visible:
                self.show_progress(percent)
                return
            
            self.current_progress = max(0, min(100, percent))
            
            if hasattr(self.main_window, 'progress_bar'):
                self.main_window.progress_bar.setValue(self.current_progress)
            
            # Jeśli postęp osiągnął 100%, zaplanuj automatyczne ukrycie
            if self.current_progress >= 100:
                self.hide_timer.start(2000)  # Ukryj po 2 sekundach
                
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji postępu: {e}")

    def update_status(self, message: str):
        """
        Aktualizuje komunikat statusu.
        
        Args:
            message: Nowy komunikat statusu
        """
        try:
            self.current_status = message
            
            if hasattr(self.main_window, 'progress_label'):
                self.main_window.progress_label.setText(self.current_status)
            
            # Jeśli postęp nie jest widoczny, pokaż go
            if not self.is_progress_visible:
                self.show_progress(self.current_progress, message)
                
        except Exception as e:
            self.logger.error(f"Błąd podczas aktualizacji statusu: {e}")

    def set_progress_and_status(self, percent: int, message: str):
        """
        Ustawia jednocześnie postęp i status.
        
        Args:
            percent: Procent postępu (0-100)
            message: Komunikat statusu
        """
        try:
            self.show_progress(percent, message)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas ustawiania postępu i statusu: {e}")

    def _auto_hide_progress(self):
        """Automatycznie ukrywa postęp po zakończeniu."""
        try:
            self.hide_progress()
            
        except Exception as e:
            self.logger.error(f"Błąd podczas automatycznego ukrywania postępu: {e}")

    def show_temporary_status(self, message: str, duration: int = 3000):
        """
        Pokazuje tymczasowy status na określony czas.
        
        Args:
            message: Komunikat do pokazania
            duration: Czas wyświetlania w milisekundach
        """
        try:
            if hasattr(self.main_window, 'status_bar'):
                self.main_window.status_bar.showMessage(message, duration)
            else:
                # Fallback - użyj progress label
                self.update_status(message)
                QTimer.singleShot(duration, lambda: self.update_status("Gotowy"))
                
        except Exception as e:
            self.logger.error(f"Błąd podczas pokazywania tymczasowego statusu: {e}")

    def show_thumbnail_progress(self, current: int, total: int):
        """
        Pokazuje postęp generowania miniatur.
        
        Args:
            current: Aktualna liczba przetworzonych miniatur
            total: Całkowita liczba miniatur do przetworzenia
        """
        try:
            if total <= 0:
                return
            
            percent = int((current / total) * 100)
            message = f"Generowanie miniatur: {current}/{total}"
            
            self.set_progress_and_status(percent, message)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pokazywania postępu miniatur: {e}")

    def show_scan_progress(self, current_folder: str, files_processed: int = 0):
        """
        Pokazuje postęp skanowania.
        
        Args:
            current_folder: Aktualnie skanowany folder
            files_processed: Liczba przetworzonych plików
        """
        try:
            if files_processed > 0:
                message = f"Skanowanie: {current_folder} ({files_processed} plików)"
            else:
                message = f"Skanowanie: {current_folder}"
            
            # Dla skanowania używamy nieokreślonego postępu
            self.show_progress(0, message)
            
            # Animacja nieokreślonego postępu
            if hasattr(self.main_window, 'progress_bar'):
                self.main_window.progress_bar.setRange(0, 0)  # Nieokreślony postęp
                
        except Exception as e:
            self.logger.error(f"Błąd podczas pokazywania postępu skanowania: {e}")

    def show_processing_progress(self, operation: str, current: int, total: int):
        """
        Pokazuje postęp operacji przetwarzania.
        
        Args:
            operation: Nazwa operacji
            current: Aktualna pozycja
            total: Całkowita liczba elementów
        """
        try:
            if total <= 0:
                message = f"{operation}..."
                self.show_progress(0, message)
                return
            
            percent = int((current / total) * 100)
            message = f"{operation}: {current}/{total}"
            
            self.set_progress_and_status(percent, message)
            
        except Exception as e:
            self.logger.error(f"Błąd podczas pokazywania postępu przetwarzania: {e}")

    def reset_progress_range(self):
        """Resetuje zakres paska postępu do normalnego (0-100)."""
        try:
            if hasattr(self.main_window, 'progress_bar'):
                self.main_window.progress_bar.setRange(0, 100)
                
        except Exception as e:
            self.logger.error(f"Błąd podczas resetowania zakresu postępu: {e}")

    def get_current_progress(self) -> dict:
        """
        Zwraca aktualny stan postępu.
        
        Returns:
            Słownik z informacjami o postępie
        """
        return {
            'percent': self.current_progress,
            'status': self.current_status,
            'visible': self.is_progress_visible
        }

    def is_busy(self) -> bool:
        """
        Sprawdza czy aplikacja jest zajęta (postęp widoczny).
        
        Returns:
            True jeśli aplikacja jest zajęta
        """
        return self.is_progress_visible 