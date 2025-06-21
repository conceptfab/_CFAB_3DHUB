import os
import shutil
import sys
import zipfile

# <<< ZMIENIONE >>>
from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
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


class BlenderZipper(QMainWindow):
    """
    Główne okno aplikacji do wyszukiwania i pakowania plików Blendera.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blend ZIP Tool")
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
        settings = QSettings("CFAB", "BlendZIPTool")
        last_path = settings.value("last_path", "")
        if last_path:
            self.folder_path.setText(last_path)

    def _save_last_path(self, path: str):
        """Zapisuje ostatnio używaną ścieżkę."""
        settings = QSettings("CFAB", "BlendZIPTool")
        settings.setValue("last_path", path)

    def _browse_folder(self):
        """Otwiera dialog wyboru folderu."""
        last_path = self.folder_path.text() or QDir.homePath()
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder", last_path)
        if folder:
            self.folder_path.setText(folder)
            self._save_last_path(folder)

    def log(self, message):
        self.log_output.append(message)
        QApplication.processEvents()

    def start_processing(self):
        root_path = self.folder_path.text()
        if not root_path or not os.path.isdir(root_path):
            self.status_bar.showMessage("Błąd: Proszę wybrać prawidłowy folder!", 5000)
            return

        should_delete_originals = self.delete_originals_checkbox.isChecked()

        self.browse_button.setEnabled(False)
        self.process_button.setEnabled(False)
        self.log_output.clear()

        self.status_bar.showMessage("Przetwarzanie...")
        self.log("=" * 50)
        self.log(f"Rozpoczynam przeszukiwanie folderu: {root_path}")
        if should_delete_originals:
            self.log("UWAGA: Opcja usuwania oryginalnych plików jest WŁĄCZONA.")
        else:
            self.log("INFO: Opcja usuwania oryginalnych plików jest wyłączona.")
        self.log("=" * 50)

        found_count = 0

        try:
            for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
                if "textures" not in dirnames:
                    continue

                files_by_basename = {}
                for f in filenames:
                    basename, ext = os.path.splitext(f)
                    if basename not in files_by_basename:
                        files_by_basename[basename] = []
                    files_by_basename[basename].append(ext.lower())

                processed_textures_in_dir = False

                for basename, extensions in files_by_basename.items():
                    if ".blend" in extensions and ".png" in extensions:
                        self.log(f"Znaleziono pasujący zestaw w folderze: {dirpath}")
                        self.log(f" -> Plik bazowy: {basename}.blend / .png")

                        blend_file_path = os.path.join(dirpath, f"{basename}.blend")
                        textures_folder_path = os.path.join(dirpath, "textures")
                        zip_file_path = os.path.join(dirpath, f"{basename}.zip")

                        if self.create_zip_archive(
                            zip_file_path, blend_file_path, textures_folder_path
                        ):
                            found_count += 1

                            if should_delete_originals:
                                self.delete_source_files(
                                    blend_file_path, textures_folder_path
                                )
                                processed_textures_in_dir = True

                if processed_textures_in_dir:
                    self.log(
                        f"  -> Aktualizacja pętli: pomijanie usuniętego folderu 'textures' w {dirpath}"
                    )
                    dirnames.remove("textures")

        except Exception as e:
            self.log(f"Wystąpił nieoczekiwany błąd w głównej pętli: {e}")
            self.status_bar.showMessage(f"Błąd: {e}", 10000)

        finally:
            self.log("=" * 50)
            self.log(f"Zakończono proces. Utworzono {found_count} archiwów ZIP.")
            self.status_bar.showMessage("Zakończono!", 5000)
            self.browse_button.setEnabled(True)
            self.process_button.setEnabled(True)

    def create_zip_archive(self, zip_path, blend_file, textures_folder) -> bool:
        try:
            self.log(f"  -> Tworzenie archiwum: {os.path.basename(zip_path)}")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(blend_file, arcname=os.path.basename(blend_file))

                for root, _, files in os.walk(textures_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(
                            file_path, os.path.dirname(textures_folder)
                        )
                        zipf.write(file_path, arcname=arcname)

            self.log(f"  -> Pomyślnie utworzono {os.path.basename(zip_path)}")
            return True
        except Exception as e:
            self.log(
                f"  -> Błąd podczas tworzenia archiwum {os.path.basename(zip_path)}: {e}"
            )
            return False

    def delete_source_files(self, blend_file_path, textures_folder_path):
        """Usuwa plik .blend i folder /textures, pozostawiając plik .png."""
        self.log("  -> Usuwanie oryginalnych plików i folderu...")
        try:
            os.remove(blend_file_path)
            self.log(f"     - Usunięto plik: {os.path.basename(blend_file_path)}")

            shutil.rmtree(textures_folder_path)
            self.log(
                f"     - Usunięto folder: {os.path.basename(textures_folder_path)}"
            )

            self.log("  -> Pomyślnie usunięto źródła. Plik .png został zachowany.")
        except Exception as e:
            self.log(f"  -> Błąd podczas usuwania plików źródłowych: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BlenderZipper()
    window.show()
    sys.exit(app.exec())
