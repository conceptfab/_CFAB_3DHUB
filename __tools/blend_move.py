import os
import shutil
import sys

from PyQt6.QtCore import QDir, QSettings
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


# --- GŁÓWNA KLASA APLIKACJI ---
class FileMoverApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blend Move Tool")
        self.setMinimumSize(800, 600)

        # Główny layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Panel wyboru folderu
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("Folder:")
        self.folder_path = QLineEdit()
        self.folder_path.setReadOnly(True)
        self.browse_button = QPushButton("Przeglądaj...")
        self.browse_button.clicked.connect(self._browse_folder)

        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(self.folder_path)
        folder_layout.addWidget(self.browse_button)

        # Przycisk startowy
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self._start_processing)

        # Okno logów
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        # Dodanie widgetów do layoutu
        main_layout.addLayout(folder_layout)
        main_layout.addWidget(self.start_button)
        main_layout.addWidget(self.log_output)

        self.setLayout(main_layout)

        # Wczytaj ostatnią ścieżkę
        self._load_last_path()

    def _load_last_path(self):
        """Wczytuje ostatnio używaną ścieżkę."""
        settings = QSettings("CFAB", "BlendMoveTool")
        last_path = settings.value("last_path", "")
        if last_path:
            self.folder_path.setText(last_path)

    def _save_last_path(self, path: str):
        """Zapisuje ostatnio używaną ścieżkę."""
        settings = QSettings("CFAB", "BlendMoveTool")
        settings.setValue("last_path", path)

    def _browse_folder(self):
        """Otwiera dialog wyboru folderu."""
        last_path = self.folder_path.text() or QDir.homePath()
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder", last_path)
        if folder:
            self.folder_path.setText(folder)
            self._save_last_path(folder)

    def log(self, message):
        """Dodaje wiadomość do okna logów i konsoli."""
        print(message)
        self.log_output.append(message)

    def _start_processing(self):
        """Rozpoczyna główną logikę programu."""
        # ### ZMIANA ###: Zmiana nazwy zmiennej dla większej czytelności
        super_folder_path = self.folder_path.text()

        if not super_folder_path:
            self.log("BŁĄD: Nie wybrano folderu nadrzędnego!")
            self.statusBar().showMessage("Błąd: wybierz folder!", 3000)
            return

        self.set_ui_enabled(False)
        self.statusBar().showMessage("Przetwarzanie...")
        self.log_output.clear()
        self.log("=" * 40)
        self.log(f"Rozpoczynam przetwarzanie folderu nadrzędnego: {super_folder_path}")
        self.log("=" * 40)

        QApplication.processEvents()

        self.process_folders(super_folder_path)

        self.log("\nProces zakończony.")
        self.statusBar().showMessage("Zakończono.", 5000)
        self.set_ui_enabled(True)

    def set_ui_enabled(self, enabled):
        """Włącza lub wyłącza elementy interfejsu."""
        self.browse_button.setEnabled(enabled)
        self.start_button.setEnabled(enabled)

    # ### ZMIANA ###: Całkowicie przeredagowana logika przetwarzania folderów
    def process_folders(self, super_folder_path):
        """
        Główna logika: iteruje po folderach, przenosi pliki i usuwa puste podfoldery.
        Struktura: super_folder / folder_0 / folder_1 / folder_2 / plik.txt
        Cel: Przenieść plik.txt do folder_0.
        """
        # Pętla po FOLDERACH 0
        for folder0_name in os.listdir(super_folder_path):
            path_folder0 = os.path.join(super_folder_path, folder0_name)

            if not os.path.isdir(path_folder0):
                continue  # Pomiń pliki w folderze nadrzędnym

            self.log(f"\n--- Przetwarzam 'Folder 0': {path_folder0} ---")

            # Pętla po FOLDERACH 1
            for folder1_name in os.listdir(path_folder0):
                path_folder1 = os.path.join(path_folder0, folder1_name)

                if not os.path.isdir(path_folder1):
                    continue  # Pomiń pliki w 'Folderze 0'

                self.log(f"  -> Sprawdzam 'Folder 1': {path_folder1}")

                # Pętla po FOLDERACH 2
                for folder2_name in os.listdir(path_folder1):
                    path_folder2 = os.path.join(path_folder1, folder2_name)

                    if not os.path.isdir(path_folder2):
                        continue  # Pomiń pliki w 'Folderze 1'

                    self.log(f"    -> Wchodzę do 'Folder 2': {path_folder2}")

                    # Znajdź pliki do przeniesienia
                    files_to_move = [
                        f
                        for f in os.listdir(path_folder2)
                        if os.path.isfile(os.path.join(path_folder2, f))
                    ]

                    if not files_to_move:
                        self.log("      -> Brak plików do przeniesienia.")

                    for filename in files_to_move:
                        source_path = os.path.join(path_folder2, filename)
                        # KLUCZOWA ZMIANA: Miejscem docelowym jest 'path_folder0'
                        destination_path = os.path.join(path_folder0, filename)

                        try:
                            self.log(
                                f"      -> Przenoszę plik '{filename}' do '{path_folder0}'"
                            )
                            shutil.move(source_path, destination_path)
                        except Exception as e:
                            self.log(f"      BŁĄD przy przenoszeniu {filename}: {e}")

                    # Spróbuj usunąć pusty 'Folder 2'
                    try:
                        os.rmdir(path_folder2)
                        self.log(f"    -> Usunięto pusty folder: {path_folder2}")
                    except OSError as e:
                        if "is not empty" in str(e):
                            self.log(
                                f"    -> Folder {path_folder2} nie jest pusty i nie został usunięty."
                            )
                        else:
                            self.log(f"    -> Błąd przy usuwaniu {path_folder2}: {e}")

                # Spróbuj usunąć pusty 'Folder 1'
                try:
                    os.rmdir(path_folder1)
                    self.log(f"  -> Usunięto pusty folder: {path_folder1}")
                except OSError as e:
                    if "is not empty" in str(e):
                        self.log(
                            f"  -> Folder {path_folder1} nie jest pusty i nie został usunięty."
                        )
                    else:
                        self.log(f"  -> Błąd przy usuwaniu {path_folder1}: {e}")

            # Nie usuwamy 'Folderu 0', ponieważ jest on celem dla plików.


# --- URUCHOMIENIE APLIKACJI ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FileMoverApp()
    window.show()
    sys.exit(app.exec())
