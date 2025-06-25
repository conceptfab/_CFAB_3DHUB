"""
Moduł zawierający klasy modeli danych dla par plików.
"""

import logging
import os
from typing import Optional, Tuple, Union

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from src.utils.path_utils import normalize_path

logger = logging.getLogger(__name__)

# Stałe dla typów transformacji miniatur
TRANSFORMATION_SMOOTH = Qt.TransformationMode.SmoothTransformation
TRANSFORMATION_FAST = Qt.TransformationMode.FastTransformation

# Specjalne wartości dla rozmiaru pliku
FILE_SIZE_ERROR = -1  # Wskazuje błąd przy pobieraniu rozmiaru pliku


class FilePair:
    """
    Reprezentuje parę plików: archiwum i jego podgląd.
    Przechowuje także metadane związane z tą parą.
    """

    def __init__(
        self, archive_path: str, preview_path: Optional[str], working_directory: str
    ):
        """
        Inicjalizuje obiekt pary plików.

        Args:
            archive_path: Absolutna ścieżka do pliku archiwum.
            preview_path: Absolutna ścieżka do pliku podglądu lub None.
            working_directory: Absolutna ścieżka do katalogu roboczego.

        Raises:
            ValueError: Gdy którakolwiek ze ścieżek nie jest absolutna.
        """
        norm_wd = normalize_path(working_directory)
        norm_archive = normalize_path(archive_path)
        norm_preview = normalize_path(preview_path) if preview_path else None

        if not os.path.isabs(norm_archive):
            raise ValueError("Ścieżka do archiwum musi być absolutna.")
        if norm_preview and not os.path.isabs(norm_preview):
            raise ValueError("Ścieżka do podglądu musi być absolutna.")
        if not os.path.isabs(norm_wd):
            raise ValueError("Ścieżka do katalogu roboczego musi być absolutna.")

        self.working_directory = norm_wd
        self.archive_path: str = norm_archive
        self.preview_path: Optional[str] = norm_preview

        # Nazwa bazowa jest pobierana z pliku archiwum
        self.base_name: str = os.path.splitext(os.path.basename(self.archive_path))[0]

        # Inicjalizacja metadanych z domyślnymi wartościami
        self.preview_thumbnail: Optional[QPixmap] = None
        self.archive_size_bytes: Optional[int] = None
        self.stars: int = 0
        self.color_tag: Optional[str] = None

    def __repr__(self) -> str:
        """
        Zwraca tekstową reprezentację obiektu FilePair.

        Returns:
            Tekstowa reprezentacja obiektu.
        """
        return (
            f"FilePair(base='{self.base_name}', "
            f"archive='{self.get_relative_archive_path()}', "
            f"preview='{self.get_relative_preview_path()}')"
        )

    def get_archive_path(self) -> str:
        """
        Zwraca absolutną, znormalizowaną ścieżkę do pliku archiwum.

        Returns:
            Absolutna ścieżka do archiwum.
        """
        return self.archive_path

    def get_preview_path(self) -> Optional[str]:
        """
        Zwraca absolutną, znormalizowaną ścieżkę do pliku podglądu lub None.

        Returns:
            Absolutna ścieżka do podglądu lub None.
        """
        return self.preview_path

    def get_relative_archive_path(self) -> str:
        """
        Zwraca względną, znormalizowaną ścieżkę do pliku archiwum.

        Returns:
            Względna ścieżka do archiwum.
        """
        return os.path.relpath(self.archive_path, self.working_directory).replace(
            "\\", "/"
        )

    def get_relative_preview_path(self) -> Optional[str]:
        """
        Zwraca względną, znormalizowaną ścieżkę do pliku podglądu lub None.

        Returns:
            Względna ścieżka do podglądu lub None.
        """
        if not self.preview_path:
            return None
        return os.path.relpath(self.preview_path, self.working_directory).replace(
            "\\", "/"
        )

    def get_base_name(self) -> str:
        """
        Zwraca nazwę bazową pary plików.

        Returns:
            Nazwa bazowa bez rozszerzenia.
        """
        return self.base_name

    def load_preview_thumbnail(
        self,
        size: int,
        transformation_mode: Qt.TransformationMode = TRANSFORMATION_SMOOTH,
    ) -> None:
        """
        Ładuje miniaturę pliku podglądu.
        Jeśli plik podglądu nie istnieje, tworzy placeholder.

        Args:
            size: Rozmiar miniatury (szerokość i wysokość).
            transformation_mode: Tryb transformacji przy skalowaniu obrazu.
                Domyślnie TRANSFORMATION_SMOOTH dla lepszej jakości, ale
                można użyć TRANSFORMATION_FAST dla lepszej wydajności.
        """
        if self.preview_path and os.path.exists(self.preview_path):
            try:
                pixmap = QPixmap(self.preview_path)
                if not pixmap.isNull():
                    self.preview_thumbnail = pixmap.scaled(
                        size,
                        size,
                        aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                        transformMode=transformation_mode,
                    )
                    return
                else:
                    logger.warning(
                        f"Nie udało się załadować QPixmap dla: {self.preview_path}"
                    )
            except Exception as e:
                logger.error(f"Błąd ładowania miniatury z {self.preview_path}: {e}")
        else:
            logger.debug(
                f"Brak pliku podglądu dla {self.base_name}, tworzenie placeholdera."
            )

        # Tworzenie placeholdera, jeśli nie udało się załadować obrazka
        self.preview_thumbnail = QPixmap(size, size)
        self.preview_thumbnail.fill(Qt.GlobalColor.gray)

    def get_preview_thumbnail(self) -> Optional[QPixmap]:
        """
        Zwraca załadowaną miniaturę.

        Returns:
            Miniatura jako QPixmap lub None, jeśli nie została załadowana.
        """
        return self.preview_thumbnail

    def get_archive_size(self) -> Optional[int]:
        """
        Pobiera i zwraca rozmiar pliku archiwum w bajtach.

        Returns:
            Rozmiar pliku w bajtach, FILE_SIZE_ERROR w przypadku błędu,
            lub None, jeśli rozmiar nie został jeszcze pobrany.
        """
        if self.archive_size_bytes is None:
            try:
                if os.path.exists(self.archive_path):
                    self.archive_size_bytes = os.path.getsize(self.archive_path)
                else:
                    logger.warning(
                        f"Plik archiwum nie istnieje, nie można pobrać rozmiaru: "
                        f"{self.archive_path}"
                    )
                    self.archive_size_bytes = (
                        FILE_SIZE_ERROR  # Wyraźne oznaczenie błędu
                    )
            except OSError as e:
                logger.error(f"Błąd odczytu rozmiaru pliku {self.archive_path}: {e}")
                self.archive_size_bytes = FILE_SIZE_ERROR
        return self.archive_size_bytes

    def get_formatted_archive_size(self) -> str:
        """
        Zwraca sformatowany rozmiar pliku archiwum (np. KB, MB).

        Returns:
            Sformatowany rozmiar pliku jako string lub "N/A" w przypadku błędu.
        """
        size_bytes = self.get_archive_size()
        if size_bytes is None or size_bytes <= 0:
            return "N/A"
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes / 1024**2:.1f} MB"
        else:
            return f"{size_bytes / 1024**3:.1f} GB"

    def set_stars(self, num_stars: int) -> int:
        """
        Ustawia liczbę gwiazdek dla pliku.

        Args:
            num_stars: Liczba gwiazdek (0-5).

        Returns:
            Ustawiona liczba gwiazdek.
        """
        if not isinstance(num_stars, int) or not (0 <= num_stars <= 5):
            log_msg = (
                f"Nieprawidłowa liczba gwiazdek ({num_stars}) "
                f"dla {self.get_base_name()}. Ustawiono 0."
            )
            logger.warning(log_msg)
            self.stars = 0
        else:
            self.stars = num_stars
        logger.debug(f"Ustawiono gwiazdki dla {self.get_base_name()} na: {self.stars}")
        return self.stars

    def get_stars(self) -> int:
        """
        Zwraca liczbę gwiazdek przypisanych do pliku.

        Returns:
            Liczba gwiazdek (0-5).
        """
        return self.stars

    def set_color_tag(self, color: Optional[str]) -> Optional[str]:
        """
        Ustawia tag kolorystyczny dla pliku.

        Args:
            color: Nazwa koloru lub kod hex. None lub pusty string
                  oznacza brak koloru.

        Returns:
            Ustawiony tag kolorystyczny.
        """
        self.color_tag = color
        log_msg = (
            f"Ustawiono tag koloru dla {self.get_base_name()} na: "
            f"'{self.color_tag}'"
        )
        logger.debug(log_msg)
        return self.color_tag

    def get_color_tag(self) -> Optional[str]:
        """
        Zwraca aktualny tag koloru.

        Returns:
            Tag koloru lub None, jeśli nie jest ustawiony.
        """
        return self.color_tag

    def to_dict(self) -> dict:
        """Konwertuje FilePair na słownik do serializacji JSON."""
        return {
            'archive_path': self.archive_path,
            'preview_path': self.preview_path,
            'working_directory': self.working_directory,
            'base_name': self.base_name,
            'archive_size_bytes': self.archive_size_bytes,
            'stars': self.stars,
            'color_tag': self.color_tag
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'FilePair':
        """Tworzy FilePair ze słownika (deserializacja JSON)."""
        file_pair = cls(
            archive_path=data['archive_path'],
            preview_path=data.get('preview_path'),
            working_directory=data['working_directory']
        )
        
        # Przywróć metadane
        file_pair.archive_size_bytes = data.get('archive_size_bytes')
        file_pair.stars = data.get('stars', 0)
        file_pair.color_tag = data.get('color_tag')
        
        return file_pair
