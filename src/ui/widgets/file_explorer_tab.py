"""
🚨 ETAP 2 - POPRAWKA 5: FileExplorerTab - Trzecia zakładka
z eksploratorem plików
"""

import logging
import os
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from src import app_config
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class FileExplorerTab(QWidget):
    """
    🚨 NOWA ZAKŁADKA Z TODO.md: Eksplorator plików
    Umożliwia przeglądanie struktury katalogów niezależnie od galerii.
    """

    # Sygnały
    folder_changed = pyqtSignal(str)  # Emitowany przy zmianie folderu
    file_selected = pyqtSignal(str)  # Emitowany przy wybraniu pliku

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.current_path = ""
        self.setStyleSheet("FileExplorerTab { background-color: #252526; }")
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        """Inicjalizuje interfejs eksploratora plików."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Główny splitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.splitter)

        # Drzewo katalogów (lewa strona)
        self._create_directory_tree()

        # Panel plików (prawa strona)
        self._create_files_panel()

        # Ustaw proporcje splittera
        self.splitter.setSizes([300, 500])

    def _create_header_panel(self, parent_layout):
        """NAPRAWKA: Usunięto zbędny header panel - duplikował informacje z panelu narzędzi."""
        # Nie tworzymy header panelu - zbędna duplikacja informacji
        pass

    def _create_directory_tree(self):
        """Tworzy panel narzędzi zamiast drzewa katalogów."""
        tools_widget = QWidget()
        tools_widget.setStyleSheet(
            "QWidget { background-color: #252526; border: none; }"
        )
        tools_layout = QVBoxLayout(tools_widget)
        tools_layout.setContentsMargins(3, 3, 3, 3)
        tools_layout.setSpacing(3)

        # Nagłówek - NAPRAWKA: Bez zbędnych ramek
        tools_label = QLabel("🔧 Narzędzia dla folderu")
        tools_label.setStyleSheet(
            "font-weight: bold; font-size: 16px; color: #CCCCCC; margin-bottom: 8px; padding: 8px; background-color: transparent; border: none;"
        )
        tools_layout.addWidget(tools_label)

        # Przycisk do renumeratora duplikatów
        self.duplicate_renamer_button = QPushButton("🎲 Generator Losowych Nazw")
        self.duplicate_renamer_button.setToolTip(
            "Wygeneruj losowe nazwy dla par plików w aktualnym folderze"
        )
        self.duplicate_renamer_button.clicked.connect(self._launch_duplicate_renamer)
        self.duplicate_renamer_button.setStyleSheet(
            """
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #a93226;
            }
        """
        )
        tools_layout.addWidget(self.duplicate_renamer_button)

        # Przycisk do konwertera WebP
        self.webp_converter_button = QPushButton("🔄 Konwerter WebP")
        self.webp_converter_button.setToolTip(
            "Konwertuje wszystkie obrazy na format WebP i usuwa oryginały"
        )
        self.webp_converter_button.clicked.connect(self._launch_webp_converter)
        self.webp_converter_button.setStyleSheet(
            """
            QPushButton {
                background-color: #16a34a;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                margin: 2px;
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
        tools_layout.addWidget(self.webp_converter_button)

        # Przycisk do zmniejszania obrazów
        self.image_resizer_button = QPushButton("📐 Zmniejsz Obrazy")
        self.image_resizer_button.setToolTip(
            "Zmniejsza obrazy: kwadratowe do 1024×1024px, prostokątne do 2048px max"
        )
        self.image_resizer_button.clicked.connect(self._launch_image_resizer)
        self.image_resizer_button.setStyleSheet(
            """
            QPushButton {
                background-color: #7c3aed;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #6d28d9;
            }
            QPushButton:pressed {
                background-color: #5b21b6;
            }
            QPushButton:disabled {
                background-color: #6b7280;
                color: #9ca3af;
            }
            """
        )
        tools_layout.addWidget(self.image_resizer_button)

        # Przycisk do ekstraktora SBSAR
        self.sbsar_extractor_button = QPushButton("📦 Ekstraktor SBSAR")
        self.sbsar_extractor_button.setToolTip(
            "Ekstraktuje podglądy WebP z plików .sbsar w folderze .alg_meta"
        )
        self.sbsar_extractor_button.clicked.connect(self._launch_sbsar_extractor)
        self.sbsar_extractor_button.setStyleSheet(
            """
            QPushButton {
                background-color: #f59e0b;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 12px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #d97706;
            }
            QPushButton:pressed {
                background-color: #b45309;
            }
            QPushButton:disabled {
                background-color: #6b7280;
                color: #9ca3af;
            }
            """
        )
        tools_layout.addWidget(self.sbsar_extractor_button)

        # Przycisk odświeżania listy plików
        self.refresh_files_button = QPushButton("🔄 Odśwież listę plików")
        self.refresh_files_button.setToolTip(
            "Odśwież listę plików w aktualnym folderze"
        )
        self.refresh_files_button.clicked.connect(self._refresh_view)
        self.refresh_files_button.setStyleSheet(
            """
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 6px 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """
        )
        tools_layout.addWidget(self.refresh_files_button)

        # Dodaj przycisk czyszczenia cache
        self.clear_cache_button = QPushButton("🗑️ Wyczyść Cache")
        self.clear_cache_button.setToolTip("Czyści cache skanowania dla tego folderu")
        self.clear_cache_button.clicked.connect(self._clear_folder_cache)
        self.clear_cache_button.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #B91C1C;
            }
            QPushButton:pressed {
                background-color: #991B1B;
            }
        """)
        
        # Dodaj do layoutu
        tools_layout.addWidget(self.clear_cache_button)

        # Dodaj więcej narzędzi w przyszłości
        tools_layout.addStretch()

        # Info o folderze
        folder_info_widget = QWidget()
        folder_info_layout = QVBoxLayout(folder_info_widget)
        folder_info_layout.setContentsMargins(5, 5, 5, 5)

        info_label = QLabel("📁 Aktualny folder")
        info_label.setStyleSheet(
            "font-weight: bold; color: #CCCCCC; margin-bottom: 6px; font-size: 14px;"
        )
        folder_info_layout.addWidget(info_label)

        self.current_folder_label = QLabel("Nie wybrano folderu")
        self.current_folder_label.setStyleSheet(
            """
            color: #CCCCCC; 
            font-size: 11px; 
            padding: 6px; 
            background-color: #1C1C1C; 
            border: none;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        """
        )
        self.current_folder_label.setWordWrap(True)
        folder_info_layout.addWidget(self.current_folder_label)

        tools_layout.addWidget(folder_info_widget)

        self.splitter.addWidget(tools_widget)

    def _create_files_panel(self):
        """Tworzy panel z listą plików w wybranym katalogu."""
        files_widget = QWidget()
        files_widget.setStyleSheet(
            "QWidget { background-color: #252526; border: none; }"
        )
        files_layout = QVBoxLayout(files_widget)
        files_layout.setContentsMargins(3, 3, 3, 3)
        files_layout.setSpacing(2)

        # Label z informacjami o folderze - NAPRAWKA: Ciemny motyw
        self.folder_info_label = QLabel("Wybierz folder w głównej aplikacji")
        self.folder_info_label.setStyleSheet(
            """
            color: #CCCCCC; 
            font-style: italic; 
            font-size: 13px; 
            padding: 8px; 
            background-color: #3F3F46; 
            border: none;
            border-radius: 4px; 
            margin: 3px;
        """
        )
        files_layout.addWidget(self.folder_info_label)

        # Lista plików - NAPRAWKA: Ciemny motyw zgodny z aplikacją
        self.files_list = QListWidget()
        self.files_list.setAlternatingRowColors(True)
        self.files_list.setStyleSheet(
            """
            QListWidget {
                background-color: #1C1C1C;
                color: #CCCCCC;
                border: 1px solid #3F3F46;
                border-radius: 4px;
                padding: 3px;
                font-size: 12px;
                selection-background-color: #264F78;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #3F3F46;
                margin: 1px;
                border-radius: 3px;
            }
            QListWidget::item:hover {
                background-color: #2A2D2E;
                color: #FFFFFF;
                border-radius: 3px;
            }
            QListWidget::item:selected {
                background-color: #264F78;
                color: #FFFFFF;
                border-radius: 3px;
                border: 1px solid #007ACC;
            }
        """
        )
        files_layout.addWidget(self.files_list)

        self.splitter.addWidget(files_widget)

    def _connect_signals(self):
        """Łączy sygnały z metodami obsługi."""
        # Double-click na plik
        self.files_list.itemDoubleClicked.connect(self._on_file_double_clicked)

    def _update_files_list(self, folder_path):
        """Aktualizuje listę plików dla wybranego folderu."""
        try:
            self.files_list.clear()

            if not os.path.exists(folder_path):
                self.folder_info_label.setText("Folder nie istnieje")
                return

            path_obj = Path(folder_path)
            files = []
            folders = []

            # Zbierz tylko pliki (bez folderów)
            for item in path_obj.iterdir():
                if item.is_file():
                    files.append(item)

            # Posortuj alfabetycznie
            files.sort(key=lambda x: x.name.lower())

            # Dodaj tylko pliki z dodatkowymi informacjami
            for file in files:
                icon = "📄"
                file_info = ""

                # Określ ikonę i zbierz informacje o pliku
                if file.suffix.lower() in [
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".gif",
                    ".bmp",
                    ".webp",
                    ".tiff",
                ]:
                    icon = "🖼️"
                    # Pobierz rozdzielczość obrazu
                    resolution = self._get_image_resolution(str(file))
                    if resolution:
                        file_info = f" [{resolution}]"
                elif file.suffix.lower() in [ext.lower() for ext in app_config.SUPPORTED_ARCHIVE_EXTENSIONS]:
                    icon = "📦"
                elif file.suffix.lower() in [".exe", ".msi"]:
                    icon = "⚙️"
                elif file.suffix.lower() in [".txt", ".md", ".log"]:
                    icon = "📝"

                # Pobierz rozmiar pliku w MB
                file_size_mb = self._get_file_size_mb(str(file))

                # Stwórz tekst elementu z rozmiarem i rozdzielczością
                item_text = f"{icon} {file.name} ({file_size_mb} MB){file_info}"

                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, str(file))
                self.files_list.addItem(item)

            # Aktualizuj info label - NAPRAWKA: Ciemny motyw zgodny z aplikacją
            file_count = len(files)
            if file_count == 0:
                self.folder_info_label.setText("📂 Folder jest pusty")
                self.folder_info_label.setStyleSheet(
                    """
                    color: #CCCCCC; 
                    font-style: italic; 
                    font-size: 13px; 
                    padding: 8px; 
                    background-color: #3F3F46; 
                    border: none;
                    border-radius: 4px; 
                    margin: 3px;
                """
                )
            else:
                # Oblicz łączny rozmiar wszystkich plików
                total_size_mb = sum(
                    self._get_file_size_mb(str(f), return_float=True) for f in files
                )
                self.folder_info_label.setText(
                    f"📄 {file_count} plików (łącznie: {total_size_mb:.1f} MB)"
                )
                self.folder_info_label.setStyleSheet(
                    """
                    color: #FFFFFF; 
                    font-weight: bold; 
                    font-size: 13px; 
                    padding: 8px; 
                    background-color: #264F78; 
                    border: none;
                    border-radius: 4px; 
                    margin: 3px;
                """
                )

        except Exception as e:
            logging.error(f"Error updating files list: {e}")
            self.folder_info_label.setText(f"Błąd: {e}")

    def _update_path_label(self, path):
        """NAPRAWKA: Metoda usunięta - zbędna po usunięciu header panelu."""
        # Nie robimy nic - path_label został usunięty
        pass

    def _on_file_double_clicked(self, item):
        """Obsługuje double-click na plik."""
        if not item:
            return

        file_path = item.data(Qt.ItemDataRole.UserRole)

        if os.path.isfile(file_path):
            # Emituj sygnał wyboru pliku
            self.file_selected.emit(file_path)
            logging.info(f"FileExplorer: File selected: {file_path}")

            # Otwórz plik w systemowym programie
            try:
                import platform
                import subprocess

                if platform.system() == "Windows":
                    os.startfile(file_path)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", file_path])
                else:  # Linux
                    subprocess.run(["xdg-open", file_path])

                logging.info(f"Opened file externally: {file_path}")
            except Exception as e:
                logging.error(f"Error opening file: {e}")

    def _refresh_view(self):
        """Odświeża aktualny widok."""
        if self.current_path and os.path.exists(self.current_path):
            self._update_files_list(self.current_path)
            logging.debug("FileExplorer: View refreshed")
        else:
            self.files_list.clear()
            self.folder_info_label.setText("Wybierz folder w drzewie po lewej")

    def set_root_path(self, path):
        """
        🚨 ETAP 2: Ustawia ścieżkę główną eksploratora.
        Wywoływane z MainWindow gdy zmienia się folder roboczy.
        """
        if not path or not os.path.exists(path):
            logging.warning(f"FileExplorer: Invalid root path: {path}")
            self.current_folder_label.setText("Nieprawidłowa ścieżka")
            return

        try:
            # Ustaw jako aktualny folder
            self.current_path = path

            # Zaktualizuj UI
            self._update_files_list(path)
            self._update_folder_info()  # Dodaj informacje o cache
            # NAPRAWKA: Usunięto _update_path_label - zbędne po usunięciu header panelu

            # Zaktualizuj label z folderem - pokaż pełną ścieżkę
            # Skróć ścieżkę jeśli za długa ale zachowaj strukturę
            if len(path) > 80:
                parts = path.split(os.sep)
                if len(parts) > 3:
                    display_folder = (
                        f"{parts[0]}{os.sep}...{os.sep}{parts[-2]}{os.sep}{parts[-1]}"
                    )
                else:
                    display_folder = path
            else:
                display_folder = path
            self.current_folder_label.setText(display_folder)

            logging.info(f"FileExplorer: Root path set to: {path}")

        except Exception as e:
            logging.error(f"Error setting root path: {e}")
            self.current_folder_label.setText("Błąd ścieżki")

    def get_current_path(self):
        """Zwraca aktualną ścieżkę eksploratora."""
        return self.current_path

    def _launch_duplicate_renamer(self):
        """Uruchamia zintegrowane narzędzie renumeratora duplikatów."""
        try:
            # Sprawdź czy folder jest wybrany
            if not self.current_path or not os.path.exists(self.current_path):
                QMessageBox.warning(
                    self,
                    "Brak folderu",
                    "Nie wybrano folderu roboczego.\nWybierz folder w głównej aplikacji.",
                )
                return

            # Importuj i uruchom zintegrowany dialog
            from .duplicate_renamer_widget import DuplicateRenamerDialog

            dialog = DuplicateRenamerDialog(
                initial_folder=self.current_path, parent=self
            )
            result = dialog.exec()

            # Po zamknięciu dialogu odśwież listę plików
            if result == QDialog.DialogCode.Accepted:
                self._refresh_view()
                logging.info(f"Duplicate renamer completed for: {self.current_path}")

        except Exception as e:
            logging.error(f"Error launching duplicate renamer: {e}")
            QMessageBox.critical(
                self, "Błąd", f"Błąd podczas uruchamiania renumeratora:\n{e}"
            )

    def _launch_webp_converter(self):
        """Uruchamia zintegrowane narzędzie konwertera WebP."""
        try:
            # Sprawdź czy folder jest wybrany
            if not self.current_path or not os.path.exists(self.current_path):
                QMessageBox.warning(
                    self,
                    "Brak folderu",
                    "Nie wybrano folderu roboczego.\nWybierz folder w głównej aplikacji.",
                )
                return

            # Import i uruchomienie konwertera WebP
            from src.ui.widgets.webp_converter_widget import WebPConverterDialog

            dialog = WebPConverterDialog(self.current_path, self)
            dialog.exec()

        except Exception as e:
            logging.error(f"Error launching WebP converter: {e}")
            QMessageBox.critical(
                self, "Błąd", f"Błąd podczas uruchamiania konwertera WebP:\n{e}"
            )

    def _launch_image_resizer(self):
        """Uruchamia zintegrowane narzędzie zmniejszania obrazów."""
        try:
            # Sprawdź czy folder jest wybrany
            if not self.current_path or not os.path.exists(self.current_path):
                QMessageBox.warning(
                    self,
                    "Brak folderu",
                    "Nie wybrano folderu roboczego.\nWybierz folder w głównej aplikacji.",
                )
                return

            # Import i uruchomienie narzędzia zmniejszania obrazów
            from src.ui.widgets.image_resizer_widget import ImageResizerDialog

            dialog = ImageResizerDialog(self.current_path, self)
            dialog.exec()

        except Exception as e:
            logging.error(f"Error launching image resizer: {e}")
            QMessageBox.critical(
                self, "Błąd", f"Błąd podczas uruchamiania narzędzia zmniejszania:\n{e}"
            )

    def _launch_sbsar_extractor(self):
        """Uruchamia zintegrowane narzędzie ekstraktora SBSAR."""
        try:
            # Sprawdź czy folder jest wybrany
            if not self.current_path or not os.path.exists(self.current_path):
                QMessageBox.warning(
                    self,
                    "Brak folderu",
                    "Nie wybrano folderu roboczego.\nWybierz folder w głównej aplikacji.",
                )
                return

            # Import i uruchomienie ekstraktora SBSAR
            from src.ui.widgets.sbsar_extractor_widget import SBSARExtractorDialog

            dialog = SBSARExtractorDialog(self.current_path, self)
            dialog.exec()

        except Exception as e:
            logging.error(f"Error launching SBSAR extractor: {e}")
            QMessageBox.critical(
                self, "Błąd", f"Błąd podczas uruchamiania ekstraktora SBSAR:\n{e}"
            )

    def _get_file_size_mb(self, file_path: str, return_float: bool = False):
        """Pobiera rozmiar pliku w MB."""
        try:
            size_bytes = os.path.getsize(file_path)
            size_mb = size_bytes / (1024 * 1024)

            if return_float:
                return size_mb

            if size_mb < 0.1:
                return "< 0.1"
            elif size_mb < 1:
                return f"{size_mb:.1f}"
            else:
                return f"{size_mb:.1f}"

        except Exception as e:
            logging.error(f"Error getting file size for {file_path}: {e}")
            return "?" if not return_float else 0.0

    def _get_image_resolution(self, file_path: str) -> str:
        """Pobiera rozdzielczość obrazu."""
        try:
            from PIL import Image

            with Image.open(file_path) as img:
                width, height = img.size
                return f"{width}×{height}"
        except Exception as e:
            logging.debug(f"Could not get resolution for {file_path}: {e}")
            return ""

    def _clear_folder_cache(self):
        """Czyści cache skanowania dla tego folderu."""
        if not self.current_path or not os.path.exists(self.current_path):
            QMessageBox.information(self, "Informacja", "Najpierw wybierz folder do wyczyszczenia cache.")
            return
            
        try:
            from src.logic.persistent_cache_manager import get_persistent_cache_manager
            from src.logic.scanner_cache import cache
            
            # Wyczyść persistent cache
            persistent_cache = get_persistent_cache_manager()
            persistent_cache.clear_cache(self.current_path)
            
            # Wyczyść memory cache
            cache.remove_entry(self.current_path, pattern_match=True)
            
            QMessageBox.information(
                self, 
                "Cache wyczyszczony", 
                f"Wyczyszczono cache dla folderu:\n{self.current_path}\n\n"
                "Cache będzie odbudowany przy następnym skanowaniu."
            )
            
            logging.info(f"Wyczyszczono cache dla folderu: {self.current_path}")
            
            # Zaktualizuj informacje o folderze
            self._update_folder_info()
            
        except Exception as e:
            logging.error(f"Błąd czyszczenia cache dla {self.current_path}: {e}")
            QMessageBox.critical(
                self, "Błąd", f"Błąd podczas czyszczenia cache:\n{e}"
            )

    def _update_folder_info(self):
        """Aktualizuje informacje o folderze."""
        if not self.current_path or not os.path.exists(self.current_path):
            self.folder_info_label.setText("Nie wybrano folderu")
            return

        try:
            # Podstawowe informacje o folderze
            folder_name = os.path.basename(self.current_path)
            file_count = len([f for f in os.listdir(self.current_path) if os.path.isfile(os.path.join(self.current_path, f))])
            
            # Informacje o cache
            cache_info = ""
            try:
                from src.logic.persistent_cache_manager import get_persistent_cache_manager
                persistent_cache = get_persistent_cache_manager()
                cache_stats = persistent_cache.get_cache_stats(self.current_path)
                
                if cache_stats.get('exists'):
                    cache_size_mb = cache_stats['cache_size_bytes'] / (1024 * 1024)
                    age_days = cache_stats.get('age_days', 0)
                    pairs_count = cache_stats.get('pairs_count', 0)
                    
                    cache_info = f" | Cache: {cache_size_mb:.1f}MB, {pairs_count} par, {age_days:.1f}d"
                else:
                    cache_info = " | Cache: brak"
            except Exception as e:
                cache_info = f" | Cache: błąd ({e})"
            
            self.folder_info_label.setText(
                f"📁 {folder_name} | {file_count} plików{cache_info}"
            )
            
        except Exception as e:
            self.folder_info_label.setText(f"Błąd: {e}")
            logger.error(f"Błąd aktualizacji informacji o folderze: {e}")
