"""
Widget do konwersji miniaturek na format WebP - zintegrowany z aplikacją CFAB_3DHUB
"""

import logging
import os
from pathlib import Path
from typing import List, Tuple

from PIL import Image
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.app_config import AppConfig


class WebPConverterWorker(QThread):
    """Worker thread dla konwersji miniaturek na WebP."""

    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal(int, int, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.should_stop = False
        self.converted_files = []
        self.deleted_files = []

    def stop(self):
        """Zatrzymuje worker."""
        self.should_stop = True

    def run(self):
        """Główna logika konwersji plików na WebP."""
        try:
            # Znajdź wszystkie pliki obrazów do konwersji
            image_files = self._find_image_files()
            
            if not image_files:
                self.finished.emit(0, 0, "Nie znaleziono plików obrazów do konwersji.")
                return

            total_files = len(image_files)
            converted_count = 0
            deleted_count = 0

            for i, file_path in enumerate(image_files):
                if self.should_stop:
                    break

                try:
                    # Aktualizuj progress
                    progress = int((i / total_files) * 100)
                    self.progress_updated.emit(
                        progress, f"Konwersja: {os.path.basename(file_path)}"
                    )

                    # Konwertuj plik na WebP
                    webp_path = self._convert_to_webp(file_path)
                    
                    if webp_path:
                        self.converted_files.append((file_path, webp_path))
                        converted_count += 1
                        
                        # KLUCZOWE: Usuń oryginalny plik po udanej konwersji
                        try:
                            os.remove(file_path)
                            self.deleted_files.append(file_path)
                            deleted_count += 1
                            logging.info(f"Usunięto oryginalny plik: {file_path}")
                        except Exception as e:
                            logging.error(f"Błąd usuwania pliku {file_path}: {e}")

                except Exception as e:
                    logging.error(f"Błąd konwersji pliku {file_path}: {e}")
                    continue

            # Zakończ z raportem
            summary = f"Skonwertowano {converted_count} plików, usunięto {deleted_count} oryginalnych plików."
            self.finished.emit(converted_count, deleted_count, summary)

        except Exception as e:
            self.error_occurred.emit(f"Błąd podczas konwersji: {e}")

    def _find_image_files(self) -> List[str]:
        """Znajduje wszystkie pliki obrazów w folderze (bez WebP)."""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']
        image_files = []

        try:
            for file_path in Path(self.folder_path).iterdir():
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in image_extensions:
                        # Sprawdź czy nie ma już wersji WebP
                        webp_path = file_path.with_suffix('.webp')
                        if not webp_path.exists():
                            image_files.append(str(file_path))

        except Exception as e:
            logging.error(f"Błąd skanowania folderu {self.folder_path}: {e}")

        return image_files

    def _convert_to_webp(self, file_path: str) -> str:
        """Konwertuje pojedynczy plik na WebP."""
        try:
            # Otwórz obraz
            with Image.open(file_path) as img:
                # Przygotuj ścieżkę WebP
                webp_path = str(Path(file_path).with_suffix('.webp'))
                
                # Konwertuj na RGB jeśli potrzeba (WebP obsługuje RGBA ale lepiej RGB dla kompatybilności)
                if img.mode in ('RGBA', 'LA'):
                    # Zachowaj przezroczystość dla WebP
                    img.save(webp_path, 'WEBP', quality=85, method=6)
                else:
                    # Konwertuj na RGB dla lepszej kompatybilności
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(webp_path, 'WEBP', quality=85, method=6)

                logging.info(f"Skonwertowano: {file_path} → {webp_path}")
                return webp_path

        except Exception as e:
            logging.error(f"Błąd konwersji {file_path}: {e}")
            return None


class WebPConverterDialog(QDialog):
    """Dialog do konwersji plików na WebP."""

    def __init__(self, folder_path, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.worker = None
        self.converted_count = 0
        self.deleted_count = 0
        
        self.setWindowTitle("Konwerter WebP")
        self.setModal(True)
        self.resize(600, 400)
        
        self._setup_ui()
        self._start_conversion()

    def _setup_ui(self):
        """Konfiguruje interfejs użytkownika."""
        layout = QVBoxLayout(self)

        # Nagłówek
        header_label = QLabel("Konwersja plików obrazów na format WebP")
        header_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        # Ścieżka folderu
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Folder:"))
        self.folder_line_edit = QLineEdit(self.folder_path)
        self.folder_line_edit.setReadOnly(True)
        folder_layout.addWidget(self.folder_line_edit)
        layout.addLayout(folder_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("Przygotowywanie...")
        layout.addWidget(self.status_label)

        # Log area
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Przyciski
        button_layout = QHBoxLayout()
        
        self.cancel_button = QPushButton("Anuluj")
        self.cancel_button.clicked.connect(self._cancel_conversion)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #dc2626;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 80px;
                height: 30px;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
        """)
        
        self.close_button = QPushButton("Zamknij")
        self.close_button.clicked.connect(self.accept)
        self.close_button.setEnabled(False)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #16a34a;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                min-width: 80px;
                height: 30px;
            }
            QPushButton:hover {
                background-color: #15803d;
            }
            QPushButton:disabled {
                background-color: #6b7280;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.close_button)
        layout.addLayout(button_layout)

    def _start_conversion(self):
        """Rozpoczyna konwersję plików."""
        self.worker = WebPConverterWorker(self.folder_path)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.finished.connect(self._on_conversion_finished)
        self.worker.error_occurred.connect(self._on_error_occurred)
        
        self.worker.start()
        self._log("Rozpoczęto konwersję plików na WebP...")

    def _on_progress_updated(self, progress, message):
        """Aktualizuje progress bar i status."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
        self._log(message)

    def _on_conversion_finished(self, converted_count, deleted_count, summary):
        """Obsługuje zakończenie konwersji."""
        self.converted_count = converted_count
        self.deleted_count = deleted_count
        
        self.progress_bar.setValue(100)
        self.status_label.setText("Konwersja zakończona!")
        self._log(f"✅ {summary}")
        
        # Przełącz przyciski
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        
        # Pokaż podsumowanie
        QMessageBox.information(
            self,
            "Konwersja zakończona",
            f"{summary}\n\nPodglądy w aplikacji zostaną automatycznie odświeżone."
        )
        
        # KLUCZOWE: Wyślij sygnał do głównej aplikacji o konieczności odświeżenia
        self._refresh_application_views()

    def _on_error_occurred(self, error_message):
        """Obsługuje błędy konwersji."""
        self.status_label.setText("Błąd konwersji!")
        self._log(f"❌ {error_message}")
        
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        
        QMessageBox.critical(self, "Błąd", error_message)

    def _cancel_conversion(self):
        """Anuluje konwersję."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)  # Czekaj max 3 sekundy
            
        self.reject()

    def _log(self, message):
        """Dodaje wiadomość do logu."""
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def _refresh_application_views(self):
        """Odświeża widoki w głównej aplikacji po konwersji."""
        try:
            # Znajdź główne okno aplikacji
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'refresh_all_views'):
                        # NAPRAWKA CRASH: Thread-safe odświeżenie z większym opóźnieniem
                        # i proper error handling żeby uniknąć zawieszania po konwersji
                        def safe_refresh():
                            try:
                                # Sprawdź czy widget nadal istnieje
                                if widget and hasattr(widget, 'refresh_all_views'):
                                    widget.refresh_all_views()
                                    self._log("✅ Widoki aplikacji odświeżone pomyślnie")
                                else:
                                    self._log("⚠️ Widget już nie istnieje - pomijam odświeżenie")
                            except Exception as refresh_error:
                                self._log(f"❌ Błąd odświeżania: {refresh_error}")
                                logging.error(f"Błąd podczas odświeżania po konwersji: {refresh_error}")
                        
                        # Większe opóźnienie dla stabilności i thread-safe execution
                        QTimer.singleShot(2000, safe_refresh)
                        self._log("🔄 Zaplanowano odświeżanie widoków aplikacji...")
                        break
                        
        except Exception as e:
            logging.error(f"Błąd odświeżania widoków aplikacji: {e}")
            self._log(f"❌ Błąd planowania odświeżenia: {e}")

    def closeEvent(self, event):
        """Obsługuje zamknięcie okna."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        event.accept() 