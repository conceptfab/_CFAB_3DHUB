import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QTextEdit, QLabel, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt

class FileNameCleanerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        # --- Konfiguracja okna głównego ---
        self.setWindowTitle("Porządkowanie Nazw Plików")
        self.setGeometry(100, 100, 700, 500)

        # --- Centralny widget i layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Sekcja wyboru folderu ---
        folder_layout = QHBoxLayout()
        folder_label = QLabel("Folder do przeszukania:")
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setPlaceholderText("Wybierz folder...")
        self.select_folder_button = QPushButton("Wybierz...")
        
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.folder_path_edit)
        folder_layout.addWidget(self.select_folder_button)

        # --- Przycisk Start ---
        self.start_button = QPushButton("Rozpocznij porządkowanie")
        self.start_button.setStyleSheet("font-size: 14px; padding: 5px;")

        # --- Okno logów ---
        log_label = QLabel("Log operacji:")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        # --- Dodawanie widgetów do głównego layoutu ---
        main_layout.addLayout(folder_layout)
        main_layout.addWidget(self.start_button)
        main_layout.addWidget(log_label)
        main_layout.addWidget(self.log_output)
        
        # --- Pasek statusu ---
        self.statusBar().showMessage("Gotowy")

        # --- Podłączenie sygnałów do slotów (funkcji) ---
        self.select_folder_button.clicked.connect(self.select_folder)
        self.start_button.clicked.connect(self.start_cleaning)

    def select_folder(self):
        """Otwiera dialog wyboru folderu i ustawia ścieżkę w polu tekstowym."""
        folder_path = QFileDialog.getExistingDirectory(self, "Wybierz folder")
        if folder_path:
            self.folder_path_edit.setText(folder_path)
            self.log_output.clear()
            self.log_output.append(f"Wybrano folder: {folder_path}\n")

    def start_cleaning(self):
        """Główna funkcja, która rozpoczyna proces czyszczenia nazw plików."""
        folder_path = self.folder_path_edit.text()

        # --- Walidacja ---
        if not folder_path or not os.path.isdir(folder_path):
            QMessageBox.warning(self, "Błąd", "Proszę wybrać prawidłowy folder.")
            self.statusBar().showMessage("Błąd: Nie wybrano prawidłowego folderu.")
            return

        # --- Przygotowanie do operacji ---
        self.log_output.clear()
        self.log_output.append(f"Rozpoczynanie skanowania w folderze: {folder_path}\n" + "-"*40)
        self.statusBar().showMessage("Przetwarzanie...")
        self.start_button.setEnabled(False) # Blokada przycisku podczas pracy
        
        # Użycie QApplication.processEvents() pozwala na odświeżenie UI w trakcie pętli
        QApplication.processEvents()

        renamed_count = 0
        processed_count = 0

        # --- Iteracja przez wszystkie pliki i podfoldery ---
        for root, dirs, files in os.walk(folder_path):
            for filename in files:
                processed_count += 1
                
                # Rozdzielenie nazwy pliku i rozszerzenia
                basename, extension = os.path.splitext(filename)

                # Sprawdzenie, czy nazwa przed kropką kończy się spacją
                if basename.endswith(' '):
                    old_path = os.path.join(root, filename)
                    
                    # Usunięcie spacji z końca nazwy
                    new_basename = basename.rstrip()
                    new_filename = new_basename + extension
                    new_path = os.path.join(root, new_filename)
                    
                    try:
                        # Zmiana nazwy pliku
                        os.rename(old_path, new_path)
                        self.log_output.append(f"[ZMIENIONO] '{filename}' -> '{new_filename}'")
                        renamed_count += 1
                    except FileExistsError:
                        self.log_output.append(f"[BŁĄD] Plik o nazwie '{new_filename}' już istnieje. Pomijanie.")
                    except Exception as e:
                        self.log_output.append(f"[BŁĄD] Nie można zmienić nazwy '{filename}': {e}")
                else:
                    # Opcjonalnie można dodać logowanie pominiętych plików
                    # self.log_output.append(f"[POMINIĘTO] '{filename}' - nazwa poprawna.")
                    pass
                
                # Dajemy UI szansę na odświeżenie się przy dużej liczbie plików
                if processed_count % 100 == 0:
                    QApplication.processEvents()

        # --- Zakończenie operacji ---
        summary_message = f"Zakończono. Przeskanowano {processed_count} plików. Zmieniono nazwę {renamed_count} plików."
        self.log_output.append("\n" + "-"*40 + f"\n{summary_message}")
        self.statusBar().showMessage(summary_message)
        self.start_button.setEnabled(True) # Odblokowanie przycisku


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileNameCleanerApp()
    window.show()
    sys.exit(app.exec())