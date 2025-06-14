import os
import sys

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class RenamerWorker(QThread):
    """
    Wątek, który wykonuje operację zmiany nazw plików w tle.
    """

    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)
    file_count_signal = pyqtSignal(int)

    def __init__(self, folder_path, text_to_remove, mode):
        super().__init__()
        self.folder_path = folder_path
        self.text_to_remove = text_to_remove
        self.mode = mode
        self.is_running = True

    def run(self):
        """Główna logika wątku - iteracja i zmiana nazw plików."""
        renamed_count = 0
        processed_count = 0

        try:
            all_files_to_process = [
                os.path.join(root, file)
                for root, _, files in os.walk(self.folder_path)
                for file in files
            ]
            total_files = len(all_files_to_process)
            self.file_count_signal.emit(total_files)
        except Exception as e:
            self.log_signal.emit(f"BŁĄD: Nie można uzyskać dostępu do folderu: {e}")
            self.finished_signal.emit(0)
            return

        if total_files == 0:
            self.log_signal.emit("Nie znaleziono żadnych plików w wybranym folderze.")
            self.finished_signal.emit(0)
            return

        for full_path in all_files_to_process:
            if not self.is_running:
                break

            processed_count += 1
            directory, filename_with_ext = os.path.split(full_path)

            filename_base, file_extension = os.path.splitext(filename_with_ext)
            new_filename_base = None

            if self.mode == "prefix" and filename_base.startswith(self.text_to_remove):
                new_filename_base = filename_base.removeprefix(self.text_to_remove)
            elif self.mode == "suffix" and filename_base.endswith(self.text_to_remove):
                new_filename_base = filename_base.removesuffix(self.text_to_remove)

            if new_filename_base is not None:
                new_full_filename = new_filename_base + file_extension

                old_path = os.path.join(directory, filename_with_ext)
                new_path = os.path.join(directory, new_full_filename)

                try:
                    os.rename(old_path, new_path)
                    self.log_signal.emit(
                        f"Zmieniono: '{filename_with_ext}' -> '{new_full_filename}'"
                    )
                    renamed_count += 1
                except FileExistsError:
                    self.log_signal.emit(
                        f"BŁĄD: Plik o nazwie '{new_full_filename}' już istnieje. Pomijam."
                    )
                except Exception as e:
                    self.log_signal.emit(
                        f"BŁĄD: Nie można zmienić nazwy '{filename_with_ext}'. Powód: {e}"
                    )

            self.progress_signal.emit(processed_count)

        self.finished_signal.emit(renamed_count)

    def stop(self):
        self.is_running = False


class RenamerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Narzędzie do zmiany nazw plików")
        self.setGeometry(100, 100, 700, 500)
        self.worker = None
        self.init_ui()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        settings_group = QGroupBox("Ustawienia")
        main_layout.addWidget(settings_group)

        form_layout = QFormLayout()
        settings_group.setLayout(form_layout)

        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setReadOnly(True)
        self.folder_path_edit.setPlaceholderText("Wybierz folder do przetworzenia...")

        browse_button = QPushButton("Przeglądaj...")
        browse_button.clicked.connect(self.select_folder)

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.folder_path_edit)
        folder_layout.addWidget(browse_button)

        form_layout.addRow(QLabel("Folder:"), folder_layout)

        self.text_to_remove_edit = QLineEdit()
        self.text_to_remove_edit.setPlaceholderText("np. 'kopia_' lub '_1'")
        form_layout.addRow(QLabel("Tekst do usunięcia:"), self.text_to_remove_edit)

        self.prefix_radio = QRadioButton("Usuń prefix (początek nazwy)")
        self.prefix_radio.setChecked(True)
        self.suffix_radio = QRadioButton(
            "Usuń sufix (koniec nazwy, przed rozszerzeniem)"
        )

        radio_layout = QHBoxLayout()
        radio_layout.addWidget(self.prefix_radio)
        radio_layout.addWidget(self.suffix_radio)
        radio_layout.addStretch()

        form_layout.addRow(QLabel("Tryb operacji:"), radio_layout)

        self.start_button = QPushButton("Rozpocznij zmianę nazw")
        self.start_button.setStyleSheet("font-size: 14px; padding: 10px;")
        self.start_button.clicked.connect(self.start_renaming)
        main_layout.addWidget(self.start_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        log_group = QGroupBox("Log operacji")
        main_layout.addWidget(log_group)

        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)

        self.log_widget = QTextEdit()
        self.log_widget.setReadOnly(True)
        log_layout.addWidget(self.log_widget)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder")
        if folder:
            self.folder_path_edit.setText(folder)

    def start_renaming(self):
        folder_path = self.folder_path_edit.text()
        text_to_remove = self.text_to_remove_edit.text()

        if not folder_path:
            QMessageBox.warning(
                self, "Brak folderu", "Proszę wybrać folder do przetworzenia."
            )
            return

        if not text_to_remove:
            QMessageBox.warning(
                self, "Brak tekstu", "Proszę wpisać tekst (prefix/sufix) do usunięcia."
            )
            return

        self.set_ui_enabled(False)
        self.log_widget.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        mode = "prefix" if self.prefix_radio.isChecked() else "suffix"

        self.log_widget.append(f"Rozpoczynam operację w folderze: {folder_path}")
        self.log_widget.append(
            f"Tryb: usuwanie {'prefixu' if mode == 'prefix' else 'sufixu'}: '{text_to_remove}'\n"
        )

        self.worker = RenamerWorker(folder_path, text_to_remove, mode)
        self.worker.log_signal.connect(self.update_log)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.file_count_signal.connect(self.set_progress_max)
        self.worker.finished_signal.connect(self.on_renaming_finished)
        self.worker.start()

    def set_ui_enabled(self, enabled):
        self.start_button.setEnabled(enabled)
        self.text_to_remove_edit.setEnabled(enabled)
        self.folder_path_edit.parent().findChild(QPushButton).setEnabled(enabled)
        self.prefix_radio.setEnabled(enabled)
        self.suffix_radio.setEnabled(enabled)

    def update_log(self, message):
        self.log_widget.append(message)

    def set_progress_max(self, max_value):
        self.progress_bar.setMaximum(max_value)

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_renaming_finished(self, renamed_count):
        self.log_widget.append(f"\n--- Zakończono ---")
        self.log_widget.append(f"Zmieniono nazwę {renamed_count} plików.")
        self.set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        QMessageBox.information(
            self,
            "Zakończono",
            f"Operacja zakończona. Zmieniono nazwę {renamed_count} plików.",
        )
        self.worker = None


# --- Główny blok uruchomieniowy ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RenamerApp()
    window.show()
    sys.exit(app.exec())
