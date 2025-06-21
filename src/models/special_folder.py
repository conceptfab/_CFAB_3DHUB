"""
Model dla specjalnych folderów tex/textures wyświetlanych jako kafelki.
"""

import logging
import os
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap

from src.config import AppConfig
from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)


class SpecialFolder:
    """
    Klasa reprezentująca specjalny folder (tex, textures).
    """

    def __init__(
        self,
        folder_name: str,
        folder_path: str,
        files_count: int = -1,
        is_virtual: bool = False,
    ):
        """
        Inicjalizuje obiekt SpecialFolder.

        Args:
            folder_name: Nazwa folderu (np. "tex")
            folder_path: Pełna ścieżka do folderu
            files_count: Liczba plików w folderze (-1 oznacza, że trzeba policzyć)
            is_virtual: Czy folder jest wirtualny (istnieje tylko w metadanych)
        """
        self.folder_name = folder_name
        self.folder_path = folder_path
        self.is_virtual = is_virtual

        # Policz liczbę plików w folderze, jeśli nie podano
        if files_count == -1 and not self.is_virtual:
            self.files_count = self._count_files()
        else:
            self.files_count = files_count if files_count >= 0 else 0

        logger.debug(
            f"Utworzono obiekt SpecialFolder: {folder_name} ({folder_path}) "
            f"z {self.files_count} plikami (wirtualny: {self.is_virtual})"
        )

    def _count_files(self) -> int:
        """
        Liczy liczbę plików w folderze.

        Returns:
            Liczba plików w folderze
        """
        if self.is_virtual:
            return self.files_count

        try:
            if os.path.exists(self.folder_path):
                files = [
                    f
                    for f in os.listdir(self.folder_path)
                    if os.path.isfile(os.path.join(self.folder_path, f))
                ]
                return len(files)
        except (PermissionError, OSError) as e:
            logger.warning(f"Błąd liczenia plików w folderze {self.folder_path}: {e}")

        return 0

    def get_folder_name(self) -> str:
        """
        Zwraca nazwę folderu.

        Returns:
            Nazwa folderu
        """
        return self.folder_name

    def get_folder_path(self) -> str:
        """
        Zwraca pełną ścieżkę do folderu.

        Returns:
            Pełna ścieżka do folderu
        """
        return self.folder_path

    def get_files_count(self) -> int:
        """
        Zwraca liczbę plików w folderze.

        Returns:
            Liczba plików w folderze
        """
        return self.files_count

    @staticmethod
    def is_special_folder(folder_name: str) -> bool:
        """
        Sprawdza czy nazwa folderu jest nazwą specjalnego folderu.

        Args:
            folder_name: Nazwa folderu do sprawdzenia

        Returns:
            True jeśli folder jest specjalnym folderem, False w przeciwnym przypadku
        """
        # Porównanie case-insensitive
        return folder_name.lower() in [
            name.lower() for name in AppConfig.get_instance().special_folders
        ]

    def __repr__(self) -> str:
        """Tekstowa reprezentacja obiektu."""
        virtual_str = " (virtual)" if self.is_virtual else ""
        return (
            f"SpecialFolder(name='{self.folder_name}', path='{self.get_folder_path()}', "
            f"files={self.files_count}{virtual_str})"
        )

    def to_dict(self) -> dict:
        """Konwertuje obiekt do słownika."""
        return {
            "folder_name": self.folder_name,
            "folder_path": self.folder_path,
            "files_count": self.files_count,
            "is_virtual": self.is_virtual,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SpecialFolder":
        """Tworzy obiekt z słownika."""
        return cls(
            folder_name=data.get("folder_name"),
            folder_path=data.get("folder_path"),
            files_count=data.get("files_count", 0),
            is_virtual=data.get("is_virtual", False),
        )

    def get_relative_path(self) -> str:
        """Zwraca względną ścieżkę do folderu."""
        return os.path.relpath(self.folder_path, self.working_directory).replace(
            "\\", "/"
        )

    def load_folder_thumbnail(self, size: int) -> None:
        """
        Tworzy ikonę folderu jako miniaturę.

        Args:
            size: Rozmiar miniatury (szerokość i wysokość)
        """
        # Tworzymy prostą ikonę folderu
        self.folder_thumbnail = QPixmap(size, size)
        self.folder_thumbnail.fill(Qt.GlobalColor.transparent)

        # TODO: Tu można by narysować ładną ikonę folderu lub użyć gotowej
        # Na razie używamy prostego wypełnienia kolorem
        self.folder_thumbnail.fill(QColor("#FFD700"))  # Złoty kolor dla folderów

    def get_folder_thumbnail(self) -> Optional[QPixmap]:
        """Zwraca miniaturę folderu."""
        return self.folder_thumbnail

    def get_folder_size(self) -> int:
        """
        Pobiera i zwraca rozmiar folderu w bajtach.

        Returns:
            Rozmiar folderu w bajtach
        """
        if self.folder_size_bytes is None:
            try:
                total_size = 0
                if os.path.exists(self.folder_path):
                    for root, dirs, files in os.walk(self.folder_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                total_size += os.path.getsize(file_path)
                            except (PermissionError, OSError):
                                continue
                self.folder_size_bytes = total_size
            except (PermissionError, OSError):
                self.folder_size_bytes = 0

        return self.folder_size_bytes

    def get_formatted_folder_size(self) -> str:
        """
        Zwraca sformatowany rozmiar folderu.

        Returns:
            Rozmiar folderu jako string (np. "15.3 MB")
        """
        size_bytes = self.get_folder_size()

        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def get_icon(self) -> QPixmap:
        """Zwraca ikonę folderu."""
        if not self._icon:
            self._icon = create_placeholder_pixmap(64, 64, color="#007ACC", text="📁")
        return self._icon
