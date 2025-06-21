import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QPushButton, QFileDialog, QTextEdit, QLabel, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PIL import Image

class ImageProcessorApp(QMainWindow):
    """
    Główne okno aplikacji do przetwarzania obrazów w folderach.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Procesor Obrazów i Archiwów ZIP")
        self.setGeometry(100, 100, 700, 500)

        # Zmienna przechowująca wybraną ścieżkę
        self.selected_folder_path = ""

        # Główny widget i layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Etykieta i przycisk do wyboru folderu
        folder_selection_layout = QHBoxLayout()
        self.folder_label = QLabel("Nie wybrano folderu")
        self.folder_label.setStyleSheet("font-style: italic; color: #555;")
        
        select_folder_button = QPushButton("Wybierz folder główny...")
        select_folder_button.clicked.connect(self.select_folder)
        
        folder_selection_layout.addWidget(select_folder_button)
        folder_selection_layout.addWidget(self.folder_label)
        folder_selection_layout.addStretch()

        # Przycisk startowy
        self.start_button = QPushButton("Rozpocznij przetwarzanie")
        self.start_button.clicked.connect(self.start_processing)
        self.start_button.setEnabled(False) # Domyślnie wyłączony

        # Okno logów
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Tutaj pojawią się logi z operacji...")

        # Dodanie widgetów do layoutu
        layout.addLayout(folder_selection_layout)
        layout.addWidget(self.start_button)
        layout.addWidget(QLabel("Logi operacji:"))
        layout.addWidget(self.log_output)

    def log(self, message: str):
        """Dodaje wiadomość do okna logów."""
        self.log_output.append(message)
        QApplication.processEvents() # Odświeża UI, aby logi pojawiały się na bieżąco

    def select_folder(self):
        """Otwiera dialog wyboru folderu i zapisuje ścieżkę."""
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder do przetworzenia")
        if folder:
            self.selected_folder_path = folder
            self.folder_label.setText(f"Wybrano: {folder}")
            self.folder_label.setStyleSheet("font-style: normal; color: #000;")
            self.start_button.setEnabled(True)
            self.log(f"Wybrano folder: {folder}")

    def start_processing(self):
        """Rozpoczyna główny proces iteracji i przetwarzania plików."""
        if not self.selected_folder_path:
            self.log("BŁĄD: Nie wybrano folderu. Proces przerwany.")
            return

        # Zablokowanie przycisków na czas przetwarzania
        self.start_button.setEnabled(False)
        self.log_output.clear()
        self.log("="*40)
        self.log("Rozpoczynam przetwarzanie...")
        self.log("="*40)

        try:
            self.process_directory_tree(self.selected_folder_path)
            self.log("\nPrzetwarzanie zakończone pomyślnie.")
        except Exception as e:
            self.log(f"\nWystąpił nieoczekiwany błąd: {e}")
        finally:
            # Odblokowanie przycisku po zakończeniu
            self.start_button.setEnabled(True)

    def process_directory_tree(self, root_path: str):
        """
        Iteruje przez drzewo folderów i wykonuje logikę zmiany nazw i tworzenia kompozycji.
        """
        for dirpath, _, filenames in os.walk(root_path):
            self.log(f"\nSprawdzam folder: {dirpath}")
            
            # --- ZMIANA W TYM MIEJSCU ---
            # Znajdź pliki ZIP (ignorując te z "_Model" w nazwie) i pliki JPG
            zip_files = [f for f in filenames if f.lower().endswith('.zip') and "_model" not in f.lower()]
            jpg_files = [f for f in filenames if f.lower().endswith(('.jpg', '.jpeg'))]

            # Sprawdzamy, czy w folderze jest dokładnie jeden (przefiltrowany) plik ZIP i co najmniej jeden plik JPG
            if len(zip_files) == 1 and jpg_files:
                zip_filename = zip_files[0]
                base_name = os.path.splitext(zip_filename)[0]
                
                # Przypadek 1: Jeden plik ZIP i jeden plik JPG
                if len(jpg_files) == 1:
                    jpg_filename = jpg_files[0]
                    old_jpg_path = os.path.join(dirpath, jpg_filename)
                    new_name = f"{base_name}.jpg"
                    new_jpg_path = os.path.join(dirpath, new_name)
                    
                    if old_jpg_path != new_jpg_path:
                        try:
                            os.rename(old_jpg_path, new_jpg_path)
                            self.log(f"-> Zmieniono nazwę: '{jpg_filename}' -> '{new_name}'")
                        except Exception as e:
                            self.log(f"-> BŁĄD przy zmianie nazwy pliku {jpg_filename}: {e}")
                    else:
                        self.log(f"-> Plik '{jpg_filename}' ma już poprawną nazwę. Pomijam.")

                # Przypadek 2: Jeden plik ZIP i wiele plików JPG
                elif len(jpg_files) > 1:
                    self.log(f"-> Znaleziono {len(jpg_files)} plików JPG. Tworzę kompozycję...")
                    self.create_composite_image(dirpath, jpg_files, base_name)
            
            elif len(zip_files) > 1:
                 self.log(f"-> Pomijam folder. Znaleziono więcej niż jeden pasujący plik ZIP: {', '.join(zip_files)}")
            else:
                 self.log("-> W folderze brak pasujących plików ZIP lub JPG. Pomijam.")

    def create_composite_image(self, dirpath: str, jpg_files: list, output_base_name: str):
        """
        Tworzy jeden obraz JPG z wielu mniejszych, układając je pionowo.
        """
        images = []
        total_height = 0
        max_width = 0

        try:
            # Wczytaj wszystkie obrazy, aby poznać ich wymiary
            for filename in jpg_files:
                img_path = os.path.join(dirpath, filename)
                try:
                    img = Image.open(img_path)
                    images.append(img)
                    total_height += img.height
                    if img.width > max_width:
                        max_width = img.width
                except Exception as e:
                    self.log(f"  -> BŁĄD: Nie można otworzyć obrazu {filename}: {e}")
                    continue
            
            if not images:
                self.log("  -> BŁĄD: Nie udało się wczytać żadnego obrazu do kompozycji.")
                return

            # Stwórz nowy, pusty obraz (płótno) o odpowiednich wymiarach
            composite_image = Image.new('RGB', (max_width, total_height), (255, 255, 255))
            
            # Wklej obrazy jeden pod drugim
            current_y = 0
            for img in images:
                # Wyśrodkuj obraz, jeśli jest węższy niż maksymalna szerokość
                paste_x = (max_width - img.width) // 2
                composite_image.paste(img, (paste_x, current_y))
                current_y += img.height
                img.close() # Zamknij plik po użyciu

            # Zapisz finalną kompozycję
            output_filename = f"{output_base_name}.jpg"
            output_path = os.path.join(dirpath, output_filename)
            composite_image.save(output_path, 'JPEG')
            self.log(f"  -> Pomyślnie utworzono i zapisano kompozycję jako: '{output_filename}'")

        except Exception as e:
            self.log(f"  -> BŁĄD podczas tworzenia kompozycji: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ImageProcessorApp()
    window.show()
    sys.exit(app.exec())