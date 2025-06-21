"""
Widget do zmniejszania obrazów do standardowych rozmiarów - zintegrowany z aplikacją CFAB_3DHUB
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


class ImageResizerWorker(QThread):
    """Worker thread dla zmniejszania obrazów do standardowych rozmiarów."""

    progress_updated = pyqtSignal(int, str)
    finished = pyqtSignal(int, int, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.should_stop = False
        self.resized_files = []
        self.replaced_files = []

    def stop(self):
        """Zatrzymuje worker."""
        self.should_stop = True

    def run(self):
        """Główna logika zmniejszania obrazów."""
        try:
            # Znajdź wszystkie pliki obrazów do zmniejszenia
            image_files = self._find_image_files()
            
            if not image_files:
                self.finished.emit(0, 0, "Nie znaleziono plików obrazów do zmniejszenia.")
                return

            total_files = len(image_files)
            resized_count = 0
            replaced_count = 0

            for i, file_path in enumerate(image_files):
                if self.should_stop:
                    break

                try:
                    # Aktualizuj progress
                    progress = int((i / total_files) * 100)
                    self.progress_updated.emit(
                        progress, f"Zmniejszanie: {os.path.basename(file_path)}"
                    )

                    # Zmniejsz obraz
                    success = self._resize_image(file_path)
                    
                    if success:
                        self.resized_files.append(file_path)
                        resized_count += 1
                        replaced_count += 1  # Zastępujemy oryginalny plik
                        logging.info(f"Zmniejszono obraz: {file_path}")

                except Exception as e:
                    logging.error(f"Błąd zmniejszania obrazu {file_path}: {e}")
                    continue

            # Zakończ z raportem
            summary = f"Zmniejszono {resized_count} obrazów do standardowych rozmiarów."
            self.finished.emit(resized_count, replaced_count, summary)

        except Exception as e:
            self.error_occurred.emit(f"Błąd podczas zmniejszania obrazów: {e}")

    def _find_image_files(self) -> List[str]:
        """Znajduje wszystkie pliki obrazów w folderze które wymagają zmniejszenia."""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        image_files = []

        try:
            for file_path in Path(self.folder_path).iterdir():
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if ext in image_extensions:
                        # Sprawdź czy obraz wymaga zmniejszenia (większy niż 2048px)
                        if self._needs_resizing(str(file_path)):
                            image_files.append(str(file_path))

        except Exception as e:
            logging.error(f"Błąd skanowania folderu {self.folder_path}: {e}")

        return image_files

    def _needs_resizing(self, file_path: str) -> bool:
        """Sprawdza czy obraz wymaga zmniejszenia."""
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                
                # Różne progi dla różnych typów obrazów
                if width == height:
                    # Kwadratowy - zmniejszaj jeśli większy niż 1024px
                    return width > 1024
                else:
                    # Prostokątny - zmniejszaj jeśli któryś wymiar większy niż 2048px
                    return width > 2048 or height > 2048
                    
        except Exception as e:
            logging.error(f"Błąd sprawdzania rozmiaru {file_path}: {e}")
            return False

    def _resize_image(self, file_path: str) -> bool:
        """Zmniejsza pojedynczy obraz zgodnie z regułami."""
        try:
            with Image.open(file_path) as img:
                original_width, original_height = img.size
                
                # Określ nowy rozmiar zgodnie z regułami
                new_width, new_height = self._calculate_new_size(original_width, original_height)
                
                # Jeśli rozmiar się nie zmienił, pomiń
                if new_width == original_width and new_height == original_height:
                    return False
                
                # Zmniejsz obraz zachowując jakość
                resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Zachowaj oryginalny format i jakość
                save_kwargs = {}
                if img.format == 'JPEG':
                    save_kwargs = {'quality': 95, 'optimize': True}
                elif img.format == 'PNG':
                    save_kwargs = {'optimize': True}
                elif img.format == 'WEBP':
                    save_kwargs = {'quality': 95, 'method': 6}
                
                # Zapisz zmniejszony obraz (zastąp oryginalny)
                resized_img.save(file_path, format=img.format, **save_kwargs)
                
                logging.info(f"Zmniejszono: {original_width}x{original_height} → {new_width}x{new_height}: {file_path}")
                return True

        except Exception as e:
            logging.error(f"Błąd zmniejszania {file_path}: {e}")
            return False

    def _calculate_new_size(self, width: int, height: int) -> Tuple[int, int]:
        """
        Oblicza nowy rozmiar obrazu zgodnie z regułami:
        - Kwadratowy: 1024x1024
        - Wysoki: wysokość 2048, szerokość proporcjonalnie
        - Szeroki: szerokość 2048, wysokość proporcjonalnie
        """
        MAX_SIZE = 2048
        SQUARE_SIZE = 1024
        
        # Określ typ obrazu i oblicz nowy rozmiar
        if width == height:
            # KWADRATOWY - ustaw na 1024x1024
            if width <= SQUARE_SIZE:
                return width, height  # Już odpowiedni rozmiar
            return SQUARE_SIZE, SQUARE_SIZE
        elif height > width:
            # WYSOKI - wysokość 2048, szerokość proporcjonalnie
            if height <= MAX_SIZE:
                return width, height  # Już odpowiedni rozmiar
            ratio = MAX_SIZE / height
            new_width = int(width * ratio)
            return new_width, MAX_SIZE
        else:
            # SZEROKI - szerokość 2048, wysokość proporcjonalnie
            if width <= MAX_SIZE:
                return width, height  # Już odpowiedni rozmiar
            ratio = MAX_SIZE / width
            new_height = int(height * ratio)
            return MAX_SIZE, new_height


class ImageResizerDialog(QDialog):
    """Dialog do zmniejszania obrazów do standardowych rozmiarów."""

    def __init__(self, folder_path, parent=None):
        super().__init__(parent)
        self.folder_path = folder_path
        self.worker = None
        self.resized_count = 0
        self.replaced_count = 0
        
        self.setWindowTitle("Zmniejszanie Obrazów")
        self.setModal(True)
        self.resize(600, 400)
        
        self._setup_ui()
        self._start_resizing()

    def _setup_ui(self):
        """Konfiguruje interfejs użytkownika."""
        layout = QVBoxLayout(self)

        # Nagłówek
        header_label = QLabel("Zmniejszanie obrazów do standardowych rozmiarów")
        header_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header_label)

        # Opis reguł
        rules_label = QLabel(
            "Reguły zmniejszania:\n"
            "• Kwadratowe: 1024×1024 px\n"
            "• Wysokie: wysokość 2048 px, szerokość proporcjonalnie\n"
            "• Szerokie: szerokość 2048 px, wysokość proporcjonalnie"
        )
        rules_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(rules_label)

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
        self.cancel_button.clicked.connect(self._cancel_resizing)
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

    def _start_resizing(self):
        """Rozpoczyna zmniejszanie obrazów."""
        self.worker = ImageResizerWorker(self.folder_path)
        self.worker.progress_updated.connect(self._on_progress_updated)
        self.worker.finished.connect(self._on_resizing_finished)
        self.worker.error_occurred.connect(self._on_error_occurred)
        
        self.worker.start()
        self._log("Rozpoczęto zmniejszanie obrazów do standardowych rozmiarów...")

    def _on_progress_updated(self, progress, message):
        """Aktualizuje progress bar i status."""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)
        self._log(message)

    def _on_resizing_finished(self, resized_count, replaced_count, summary):
        """Obsługuje zakończenie zmniejszania."""
        self.resized_count = resized_count
        self.replaced_count = replaced_count
        
        self.progress_bar.setValue(100)
        self.status_label.setText("Zmniejszanie zakończone!")
        self._log(f"✅ {summary}")
        
        # Przełącz przyciski
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        
        # Pokaż podsumowanie
        if resized_count > 0:
            QMessageBox.information(
                self,
                "Zmniejszanie zakończone",
                f"{summary}\n\nPodglądy w aplikacji zostaną automatycznie odświeżone."
            )
            # Odśwież widoki aplikacji
            self._refresh_application_views()
        else:
            QMessageBox.information(
                self,
                "Zmniejszanie zakończone",
                "Wszystkie obrazy mają już odpowiednie rozmiary.\nNie było potrzeby zmniejszania."
            )

    def _on_error_occurred(self, error_message):
        """Obsługuje błędy zmniejszania."""
        self.status_label.setText("Błąd zmniejszania!")
        self._log(f"❌ {error_message}")
        
        self.cancel_button.setEnabled(False)
        self.close_button.setEnabled(True)
        
        QMessageBox.critical(self, "Błąd", error_message)

    def _cancel_resizing(self):
        """Anuluje zmniejszanie."""
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
        """Odświeża widoki w głównej aplikacji po zmniejszeniu."""
        try:
            # Znajdź główne okno aplikacji
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'refresh_all_views'):
                        # Odśwież widoki z opóźnieniem aby zmienione pliki zostały wykryte
                        QTimer.singleShot(1000, widget.refresh_all_views)
                        self._log("🔄 Odświeżanie widoków aplikacji...")
                        break
                        
        except Exception as e:
            logging.error(f"Błąd odświeżania widoków aplikacji: {e}")

    def closeEvent(self, event):
        """Obsługuje zamknięcie okna."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)
        event.accept() 