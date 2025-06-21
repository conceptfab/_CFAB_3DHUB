"""
Widget kafelka dla specjalnych folderów (tex, textures).
"""

import logging
import os
import platform
import subprocess
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class SpecialFolderTileWidget(QWidget):
    """
    Widget reprezentujący folder specjalny w galerii.
    Używa emoji 📁 zamiast pliku PNG.
    """

    # Sygnały
    folder_clicked = pyqtSignal(str)  # Emitowany gdy użytkownik kliknie folder

    def __init__(self, folder_name, folder_path, parent=None):
        """
        Inicjalizuje widget folderu specjalnego.

        Args:
            folder_name (str): Nazwa folderu
            folder_path (str): Ścieżka do folderu
            parent (QWidget, optional): Widget nadrzędny
        """
        super().__init__(parent)

        self.folder_name = folder_name
        self.folder_path = folder_path
        self.thumbnail_size = 128

        # Ustaw nazwę obiektu dla stylizacji
        self.setObjectName("SpecialFolderTileWidget")

        # Włącz obsługę tła przez style
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Inicjalizacja UI
        self._init_ui()

        # Podłącz obsługę kliknięć
        self.installEventFilter(self)

        logger.debug(f"Utworzono widget folderu: {folder_name} ({folder_path})")

    def _init_ui(self):
        """
        Inicjalizuje interfejs użytkownika widgetu.
        """
        # Układ główny
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(2)

        # Etykieta z ikoną folderu
        self.icon_label = QLabel(self)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Próba załadowania ikony z pliku PNG, z fallbackiem na emoji
        icon_path = self._get_icon_path()
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            self.icon_label.setPixmap(pixmap)
        else:
            msg = f"Nie znaleziono ikony folderu w '{icon_path}'. Używam emoji."
            logger.warning(msg)
            font = QFont()
            font.setPointSize(48)  # Duża czcionka dla emoji
            self.icon_label.setFont(font)
            self.icon_label.setText("📁")

        self.icon_label.setMinimumSize(self.thumbnail_size, self.thumbnail_size)

        # Etykieta z nazwą folderu
        self.name_label = QLabel(self.folder_name, self)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)

        # Dodaj etykiety do układu
        self.layout.addWidget(self.icon_label)
        self.layout.addWidget(self.name_label)

        # Ustaw rozmiar widgetu
        self.setMinimumSize(self.thumbnail_size + 10, self.thumbnail_size + 30)
        self.setMaximumSize(self.thumbnail_size + 10, self.thumbnail_size + 60)

    def set_thumbnail_size(self, size):
        """
        Ustawia rozmiar miniatury.

        Args:
            size (int lub tuple): Rozmiar miniatury w pikselach
        """
        # Obsługa różnych typów size dla zgodności z FileTileWidget
        if isinstance(size, tuple):
            # Jeśli size to tuple (width, height), użyj width jako rozmiaru kwadratu
            thumbnail_size = size[0]
        elif isinstance(size, int):
            thumbnail_size = size
        else:
            logging.warning(f"Nieprawidłowy typ rozmiaru miniatury: {type(size)}, value: {size}")
            return
        
        self.thumbnail_size = thumbnail_size
        self.icon_label.setMinimumSize(thumbnail_size, thumbnail_size)

        # Skalowanie pixmapy, jeśli istnieje
        if self.icon_label.pixmap():
            pixmap = self.icon_label.pixmap()
            scaled_pixmap = pixmap.scaled(
                thumbnail_size,
                thumbnail_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.icon_label.setPixmap(scaled_pixmap)

        self.setMinimumSize(thumbnail_size + 10, thumbnail_size + 30)
        self.setMaximumSize(thumbnail_size + 10, thumbnail_size + 60)

    def eventFilter(self, obj, event):
        """
        Filtr zdarzeń do obsługi kliknięć.

        Args:
            obj: Obiekt, który wygenerował zdarzenie
            event: Zdarzenie

        Returns:
            bool: True jeśli zdarzenie zostało obsłużone, False w przeciwnym razie
        """
        if obj == self and event.type() == event.Type.MouseButtonRelease:
            logger.debug(f"Kliknięto folder: {self.folder_name} ({self.folder_path})")
            self.folder_clicked.emit(self.folder_path)
            return True
        return super().eventFilter(obj, event)

    def _on_open_clicked(self):
        """
        Obsługuje kliknięcie przycisku "Otwórz".
        Otwiera folder w eksploratorze systemu.
        """
        logger.debug(f"Otwieranie folderu: {self.folder_path}")
        self._open_file_in_explorer(self.folder_path)

    def _get_icon_path(self) -> Optional[str]:
        """
        Zwraca absolutną ścieżkę do ikony folderu.

        Próbuje zlokalizować plik ikony folder.png w katalogu zasobów.

        Returns:
            Optional[str]: Absolutna ścieżka do ikony lub None, jeśli nie znaleziono.
        """
        try:
            # Ścieżka do bieżącego pliku
            current_file_path = os.path.abspath(__file__)
            # Przejdź w górę do katalogu src
            src_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(current_file_path))
            )
            # Zbuduj ścieżkę do ikony
            icon_path = os.path.join(src_dir, "resources", "img", "folder.png")
            return icon_path
        except Exception:
            logger.error("Błąd podczas budowania ścieżki do ikony.", exc_info=True)
            return None

    def _open_file_in_explorer(self, path: str):
        """
        Otwiera plik lub folder w domyślnym eksploratorze systemu.

        Args:
            path: Ścieżka do pliku lub folderu
        """
        try:
            if platform.system() == "Windows":
                # Windows Explorer
                subprocess.run(["explorer", path], check=False)
            elif platform.system() == "Darwin":
                # macOS Finder
                subprocess.run(["open", path], check=False)
            else:
                # Linux file manager
                subprocess.run(["xdg-open", path], check=False)

            logger.info(f"Otwarto w eksploratorze: {path}")
        except Exception as e:
            msg = f"Błąd otwierania w eksploratorze: {e}"
            logger.error(msg, exc_info=True)
