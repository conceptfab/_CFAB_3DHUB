import os
import sys
import random
import string
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog, QLabel, QLineEdit, QMessageBox
)

class FileRenamerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Renumerator Duplikatów Plików")
        self.setGeometry(200, 200, 400, 200)

        layout = QVBoxLayout()

        self.folder_label = QLabel("Wybierz folder:")
        layout.addWidget(self.folder_label)

        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setReadOnly(True)
        layout.addWidget(self.folder_path_edit)

        self.browse_button = QPushButton("Przeglądaj...")
        self.browse_button.clicked.connect(self.browse_folder)
        layout.addWidget(self.browse_button)

        self.rename_button = QPushButton("Znajdź i Renumeruj Duplikaty")
        self.rename_button.clicked.connect(self.find_and_rename_duplicates)
        layout.addWidget(self.rename_button)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        self.selected_folder = ""

    def browse_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Wybierz folder")
        if folder_path:
            self.selected_folder = folder_path
            self.folder_path_edit.setText(self.selected_folder)
            self.status_label.setText("")

    def find_and_rename_duplicates(self):
        if not self.selected_folder:
            QMessageBox.warning(self, "Błąd", "Proszę najpierw wybrać folder.")
            return

        self.status_label.setText("Wyszukiwanie duplikatów...")
        QApplication.processEvents() # Odświeżenie interfejs

        files_by_name = {}
        duplicates_found = []

        try:
            for filename in os.listdir(self.selected_folder):
                file_path = os.path.join(self.selected_folder, filename)
                if os.path.isfile(file_path):
                    base_name, ext = os.path.splitext(filename)
                    base_name_lower = base_name.lower()  # Ignorowanie wielkości liter

                    if base_name_lower not in files_by_name:
                        files_by_name[base_name_lower] = []
                    files_by_name[base_name_lower].append(file_path)

            for base_name, paths in files_by_name.items():
                if len(paths) > 1:
                    duplicates_found.extend(paths)

            if not duplicates_found:
                self.status_label.setText("Nie znaleziono duplikatów plików o tej samej nazwie.")
                QMessageBox.information(self, "Zakończono", "Nie znaleziono duplikatów plików o tej samej nazwie.")
                return

            self.status_label.setText(f"Znaleziono {len(duplicates_found)} plików do renumeracji...")
            QApplication.processEvents() # Odświeżenie interfejs

            renamed_count = 0
            errors_count = 0

            for base_name, paths in files_by_name.items():
                if len(paths) > 1:
                    random_suffix = self.generate_random_suffix(12)
                    for old_path in paths:
                        _, ext = os.path.splitext(os.path.basename(old_path))
                        new_filename = f"{random_suffix}{ext}"
                        new_path = os.path.join(self.selected_folder, new_filename)

                        # Sprawdź, czy nowa nazwa już nie istnieje (mało prawdopodobne, ale bezpieczne)
                        counter = 1
                        while os.path.exists(new_path):
                            new_filename = f"{random_suffix}_{counter}{ext}"
                            new_path = os.path.join(self.selected_folder, new_filename)
                            counter += 1

                        try:
                            os.rename(old_path, new_path)
                            renamed_count += 1
                        except OSError as e:
                            print(f"Błąd podczas zmiany nazwy {old_path} na {new_path}: {e}")
                            errors_count += 1

            self.status_label.setText(f"Zakończono. Zrenumerowano {renamed_count} plików. Wystąpiło {errors_count} błędów.")
            QMessageBox.information(self, "Zakończono", f"Zakończono. Zrenumerowano {renamed_count} plików. Wystąpiło {errors_count} błędów.")

        except OSError as e:
            self.status_label.setText(f"Błąd podczas dostępu do folderu: {e}")
            QMessageBox.critical(self, "Błąd", f"Błąd podczas dostępu do folderu: {e}")
        except Exception as e:
            self.status_label.setText(f"Wystąpił nieznany błąd: {e}")
            QMessageBox.critical(self, "Błąd", f"Wystąpił nieznany błąd: {e}")


    def generate_random_suffix(self, length):
        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FileRenamerApp()
    window.show()
    sys.exit(app.exec())