"""
Widget ekstraktora SBSAR - ekstraktuje podglądy WebP z plików .sbsar
w folderze .alg_meta i kopiuje je do aktualnego folderu roboczego.
"""

import logging
import os
import shutil
import struct
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)


def extract_webp_from_sbsar(input_filepath, output_dir, logger_func):
    """
    Wyszukuje i wyodrębnia osadzony obraz WebP z pliku .sbsar.
    Zapisuje go w podanym folderze wyjściowym.

    Args:
        input_filepath (str): Ścieżka do pliku .sbsar.
        output_dir (str): Folder, w którym ma być zapisany wynikowy plik .webp.
        logger_func (callable): Funkcja do logowania postępów.
    """
    if not os.path.exists(input_filepath):
        logger_func(f"BŁĄD: Plik '{input_filepath}' nie istnieje.")
        return False

    logger_func(f"-> Przetwarzanie pliku: {os.path.basename(input_filepath)}")

    try:
        with open(input_filepath, 'rb') as f:
            file_data = f.read()
    except Exception as e:
        logger_func(f"BŁĄD: Nie można odczytać pliku. {e}")
        return False

    # Sygnatura pliku WebP: 'RIFF', rozmiar, 'WEBP'
    webp_marker_pos = file_data.find(b'WEBP')

    if webp_marker_pos == -1:
        logger_func("-> Nie znaleziono znacznika 'WEBP' w pliku.")
        return False

    riff_header_pos = webp_marker_pos - 8
    if riff_header_pos < 0 or file_data[riff_header_pos:riff_header_pos+4] != b'RIFF':
        logger_func("-> Znaleziono 'WEBP', ale nie jest to prawidłowy kontener RIFF.")
        return False

    size_bytes = file_data[riff_header_pos+4 : riff_header_pos+8]
    chunk_size = struct.unpack('<I', size_bytes)[0]
    total_webp_size = chunk_size + 8

    webp_data = file_data[riff_header_pos : riff_header_pos + total_webp_size]

    if len(webp_data) < total_webp_size:
        logger_func("BŁĄD: Zadeklarowany rozmiar jest większy niż dostępne dane. Plik może być uszkodzony.")
        return False

    # Tworzymy nazwę pliku wyjściowego
    base_name, _ = os.path.splitext(os.path.basename(input_filepath))
    output_filepath = os.path.join(output_dir, f"{base_name}.webp")

    try:
        with open(output_filepath, 'wb') as f_out:
            f_out.write(webp_data)
        logger_func(f"-> SUKCES! Podgląd zapisano jako: '{os.path.basename(output_filepath)}'")
        return True
    except Exception as e:
        logger_func(f"BŁĄD: Nie można zapisać pliku wyjściowego. {e}")
        return False


class SBSARExtractionWorker(QObject):
    """
    Worker do ekstrakcji WebP z plików SBSAR w folderze .alg_meta
    i kopiowania ich do folderu roboczego.
    """
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    log_message = pyqtSignal(str)

    def __init__(self, working_folder):
        super().__init__()
        self.working_folder = working_folder
        self.alg_meta_folder = os.path.join(working_folder, ".alg_meta")
        self.is_running = True

    def run(self):
        """Główna pętla przetwarzająca pliki SBSAR."""
        try:
            self.log_message.emit(f"Rozpoczynam ekstrakcję z folderu: {self.alg_meta_folder}")
            
            # Sprawdź czy folder .alg_meta istnieje
            if not os.path.exists(self.alg_meta_folder):
                self.log_message.emit("BŁĄD: Folder .alg_meta nie istnieje w aktualnym folderze roboczym.")
                self.finished.emit()
                return
            
            # Znajdź pliki .sbsar w folderze .alg_meta
            sbsar_files = []
            for root, dirs, files in os.walk(self.alg_meta_folder):
                for file in files:
                    if file.lower().endswith('.sbsar'):
                        sbsar_files.append(os.path.join(root, file))
            
            if not sbsar_files:
                self.log_message.emit("Nie znaleziono żadnych plików .sbsar w folderze .alg_meta.")
                self.finished.emit()
                return
                
            total_files = len(sbsar_files)
            self.log_message.emit(f"Znaleziono {total_files} plików .sbsar do przetworzenia.")
            
            extracted_count = 0
            
            for i, sbsar_file_path in enumerate(sbsar_files):
                if not self.is_running:
                    break
                
                # Ekstraktuj WebP do tymczasowego folderu
                temp_output_dir = os.path.join(self.alg_meta_folder, "temp_webp")
                os.makedirs(temp_output_dir, exist_ok=True)
                
                success = extract_webp_from_sbsar(
                    sbsar_file_path, 
                    temp_output_dir, 
                    self.log_message.emit
                )
                
                if success:
                    # Znajdź wyekstraktowany plik WebP
                    base_name = os.path.splitext(os.path.basename(sbsar_file_path))[0]
                    webp_file = os.path.join(temp_output_dir, f"{base_name}.webp")
                    
                    if os.path.exists(webp_file):
                        # Skopiuj do folderu roboczego
                        destination = os.path.join(self.working_folder, f"{base_name}.webp")
                        try:
                            shutil.copy2(webp_file, destination)
                            self.log_message.emit(f"-> Skopiowano do folderu roboczego: {base_name}.webp")
                            extracted_count += 1
                        except Exception as e:
                            self.log_message.emit(f"BŁĄD kopiowania {base_name}.webp: {e}")
                        
                        # Usuń tymczasowy plik
                        try:
                            os.remove(webp_file)
                        except:
                            pass
                
                self.progress.emit(int(((i + 1) / total_files) * 100))
            
            # Usuń tymczasowy folder
            try:
                temp_output_dir = os.path.join(self.alg_meta_folder, "temp_webp")
                if os.path.exists(temp_output_dir):
                    os.rmdir(temp_output_dir)
            except:
                pass
            
            self.log_message.emit(f"\nZakończono ekstrakcję. Wyekstraktowano {extracted_count} z {total_files} plików.")
            self.finished.emit()
            
        except Exception as e:
            self.log_message.emit(f"BŁĄD KRYTYCZNY: {e}")
            logger.error(f"SBSAR extraction error: {e}", exc_info=True)
            self.finished.emit()

    def stop(self):
        self.is_running = False


class SBSARExtractorDialog(QDialog):
    """Dialog ekstraktora SBSAR zintegrowany z aplikacją CFAB_3DHUB."""

    def __init__(self, working_folder, parent=None):
        super().__init__(parent)
        self.working_folder = working_folder
        self.thread = None
        self.worker = None
        self.setWindowTitle('Ekstraktor SBSAR - CFAB_3DHUB')
        self.setGeometry(300, 300, 700, 500)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        """Inicjalizuje interfejs użytkownika."""
        layout = QVBoxLayout(self)

        # Informacje o folderze
        info_layout = QHBoxLayout()
        info_label = QLabel("Folder roboczy:")
        self.folder_label = QLabel(self.working_folder)
        self.folder_label.setStyleSheet("font-weight: bold; color: #007ACC;")
        info_layout.addWidget(info_label)
        info_layout.addWidget(self.folder_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Opis działania
        desc_label = QLabel(
            "Narzędzie przeszuka folder .alg_meta w poszukiwaniu plików .sbsar,\n"
            "wyekstraktuje z nich podglądy WebP i skopiuje je do aktualnego folderu roboczego."
        )
        desc_label.setStyleSheet("color: #CCCCCC; font-style: italic; margin: 10px;")
        layout.addWidget(desc_label)

        # Przycisk startu
        self.start_button = QPushButton("🚀 Rozpocznij ekstrakcję")
        self.start_button.setStyleSheet(
            """
            QPushButton {
                background-color: #16a34a;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #15803d;
            }
            QPushButton:pressed {
                background-color: #166534;
            }
            QPushButton:disabled {
                background-color: #6b7280;
                color: #9ca3af;
            }
            """
        )
        self.start_button.clicked.connect(self._start_extraction)
        layout.addWidget(self.start_button)

        # Pasek postępu
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 1px solid #3F3F46;
                border-radius: 4px;
                text-align: center;
                background-color: #1C1C1C;
                color: #CCCCCC;
            }
            QProgressBar::chunk {
                background-color: #16a34a;
                border-radius: 3px;
            }
            """
        )
        layout.addWidget(self.progress_bar)

        # Logi
        log_label = QLabel("Log ekstrakcji:")
        log_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(log_label)

        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("Tutaj pojawią się informacje o postępie ekstrakcji...")
        self.log_area.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #1C1C1C;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
            """
        )
        layout.addWidget(self.log_area)

        # Przyciski na dole
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.close_button = QPushButton("Zamknij")
        self.close_button.setStyleSheet(
            """
            QPushButton {
                background-color: #6b7280;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
            """
        )
        self.close_button.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_button)

        layout.addLayout(buttons_layout)

    def _start_extraction(self):
        """Uruchamia proces ekstrakcji w osobnym wątku."""
        self._set_ui_enabled(False)
        self.progress_bar.setValue(0)
        self.log_area.clear()

        # Konfiguracja wątku i workera
        self.thread = QThread()
        self.worker = SBSARExtractionWorker(self.working_folder)
        self.worker.moveToThread(self.thread)

        # Podłączenie sygnałów workera
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.log_message.connect(self.log_area.appendPlainText)
        self.worker.progress.connect(self.progress_bar.setValue)
        
        # Obsługa zakończenia wątku
        self.thread.finished.connect(lambda: self._set_ui_enabled(True))
        self.thread.finished.connect(self._on_thread_finished)

        self.thread.start()

    def _set_ui_enabled(self, enabled):
        """Włącza lub wyłącza elementy interfejsu podczas pracy."""
        self.start_button.setEnabled(enabled)
        if enabled:
            self.start_button.setText("🚀 Rozpocznij ekstrakcję")
        else:
            self.start_button.setText("⏳ Trwa ekstrakcja...")

    def _on_thread_finished(self):
        """Obsługuje zakończenie wątku - czyści referencje."""
        try:
            if self.thread:
                self.thread.deleteLater()
                self.thread = None
            self.worker = None
        except Exception as e:
            logger.warning(f"Błąd podczas czyszczenia wątku: {e}")

    def closeEvent(self, event):
        """Zapewnia poprawne zamknięcie wątku przy zamykaniu okna."""
        try:
            if self.thread and hasattr(self.thread, 'isRunning') and self.thread.isRunning():
                if self.worker:
                    self.worker.stop()
                self.thread.quit()
                self.thread.wait(3000)  # Czekaj maksymalnie 3 sekundy
        except RuntimeError:
            # Thread już został usunięty - to normalne
            pass
        except Exception as e:
            logger.warning(f"Błąd podczas zamykania wątku ekstraktora: {e}")
        finally:
            event.accept() 