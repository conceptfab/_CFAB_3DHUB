import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class SuffixRemoverApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Usuwanie Suffixów z Nazw Folderów")
        self.setGeometry(100, 100, 600, 400)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        folder_layout = QHBoxLayout()
        folder_label = QLabel("Folder do sprawdzenia:")
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setReadOnly(True)
        browse_button = QPushButton("Przeglądaj...")
        browse_button.clicked.connect(self.select_folder)

        folder_layout.addWidget(self.folder_path_edit)
        folder_layout.addWidget(browse_button)

        main_layout.addWidget(folder_label)
        main_layout.addLayout(folder_layout)

        # --- Sekcja wprowadzania suffixu ---
        suffix_label = QLabel("Suffix do usunięcia:")
        self.suffix_edit = QLineEdit()
        self.suffix_edit.setPlaceholderText("np. _8K, _FINAL, itp.")
        # Domyślna wartość dla ułatwienia
        self.suffix_edit.setText("_8K")

        main_layout.addWidget(suffix_label)
        main_layout.addWidget(self.suffix_edit)

        main_layout.addSpacing(20)

        # --- Przycisk uruchamiający ---
        self.run_button = QPushButton("Znajdź i usuń suffixy")
        self.run_button.setStyleSheet("font-size: 14px; padding: 10px;")
        self.run_button.clicked.connect(self.start_processing)
        main_layout.addWidget(self.run_button)

        main_layout.addSpacing(20)

        # --- Logi operacji ---
        log_label = QLabel("Log operacji:")
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        main_layout.addWidget(log_label)
        main_layout.addWidget(self.log_output)

    def select_folder(self):
        """Otwiera dialog wyboru folderu i ustawia ścieżkę w QLineEdit."""
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder")
        if folder:
            self.folder_path_edit.setText(folder)
            self.log_output.clear()
            self.log_output.appendPlainText(f"Wybrano folder: {folder}")

    def start_processing(self):
        """Rozpoczyna proces sprawdzania i zmiany nazw folderów."""
        folder_path = self.folder_path_edit.text()
        suffix_to_remove = self.suffix_edit.text()

        # Walidacja danych wejściowych
        if not folder_path:
            QMessageBox.warning(self, "Błąd", "Proszę wybrać folder do sprawdzenia.")
            return
        if not suffix_to_remove:
            QMessageBox.warning(self, "Błąd", "Proszę podać suffix do usunięcia.")
            return

        self.log_output.clear()
        self.log_output.appendPlainText(
            f"Rozpoczynam skanowanie folderu: {folder_path}"
        )
        self.log_output.appendPlainText(f"Szukany suffix: '{suffix_to_remove}'")
        self.log_output.appendPlainText("-" * 30)

        QApplication.processEvents()  # Odświeżenie UI przed długą operacją

        changed_count = 0
        try:
            # Iterujemy po wszystkich elementach w podanym folderze
            for item_name in os.listdir(folder_path):
                item_path = os.path.join(folder_path, item_name)

                # Sprawdzamy, czy element jest folderem i czy jego nazwa kończy się suffixem
                if os.path.isdir(item_path) and item_name.endswith(suffix_to_remove):
                    # Tworzymy nową nazwę, usuwając suffix
                    new_name = item_name[: -len(suffix_to_remove)]
                    new_path = os.path.join(folder_path, new_name)

                    self.log_output.appendPlainText(f"Znaleziono folder: '{item_name}'")

                    # Zmiana nazwy z obsługą błędów
                    try:
                        if os.path.exists(new_path):
                            self.log_output.appendPlainText(
                                f"--> [BŁĄD] Folder o nazwie '{new_name}' już istnieje. Pomijam."
                            )
                            continue

                        os.rename(item_path, new_path)
                        self.log_output.appendPlainText(
                            f"--> [SUKCES] Zmieniono nazwę na: '{new_name}'"
                        )
                        changed_count += 1
                    except PermissionError:
                        self.log_output.appendPlainText(
                            f"--> [BŁĄD] Brak uprawnień do zmiany nazwy folderu '{item_name}'."
                        )
                    except Exception as e:
                        self.log_output.appendPlainText(
                            f"--> [BŁĄD KRYTYCZNY] Wystąpił nieoczekiwany błąd: {e}"
                        )

        except FileNotFoundError:
            self.log_output.appendPlainText(
                f"[BŁĄD] Folder '{folder_path}' nie został znaleziony."
            )
        except Exception as e:
            self.log_output.appendPlainText(
                f"[BŁĄD KRYTYCZNY] Wystąpił nieoczekiwany błąd podczas skanowania: {e}"
            )

        self.log_output.appendPlainText("-" * 30)
        self.log_output.appendPlainText(
            f"Zakończono. Zmieniono nazwy {changed_count} folderów."
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SuffixRemoverApp()
    window.show()
    sys.exit(app.exec())
