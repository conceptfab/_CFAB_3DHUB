import logging
import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

logger = logging.getLogger(__name__)


def _normalize_path(path: str) -> str:
    """Normalizuje ścieżkę, zamieniając separatory na '/'."""
    if not path:
        return ""
    return os.path.normpath(path).replace("\\", "/")


class FilePair:
    """
    Reprezentuje parę plików: archiwum i jego podgląd.
    Przechowuje także metadane związane z tą parą.
    """

    def __init__(
        self, archive_path: str, preview_path: str | None, working_directory: str
    ):
        """
        Inicjalizuje obiekt pary plików.

        Args:
            archive_path (str): Absolutna ścieżka do pliku archiwum.
            preview_path (str | None): Absolutna ścieżka do pliku podglądu.
            working_directory (str): Absolutna ścieżka do katalogu roboczego.
        """
        norm_wd = _normalize_path(working_directory)
        norm_archive = _normalize_path(archive_path)
        norm_preview = _normalize_path(preview_path) if preview_path else None

        if not os.path.isabs(norm_archive):
            raise ValueError("Ścieżka do archiwum musi być absolutna.")
        if norm_preview and not os.path.isabs(norm_preview):
            raise ValueError("Ścieżka do podglądu musi być absolutna.")
        if not os.path.isabs(norm_wd):
            raise ValueError("Ścieżka do katalogu roboczego musi być absolutna.")

        self.working_directory = norm_wd
        self.archive_path: str = norm_archive
        self.preview_path: str | None = norm_preview

        # Nazwa bazowa jest pobierana z pliku archiwum
        self.base_name: str = os.path.splitext(os.path.basename(self.archive_path))[0]

        # Inicjalizacja metadanych z domyślnymi wartościami
        self.preview_thumbnail: QPixmap | None = None
        self.archive_size_bytes: int | None = None
        self.is_favorite: bool = False
        self.stars: int = 0
        self.color_tag: str | None = None

    def __repr__(self) -> str:
        return (
            f"FilePair(base='{self.base_name}', "
            f"archive='{self.get_relative_archive_path()}', "
            f"preview='{self.get_relative_preview_path()}')"
        )

    def get_archive_path(self) -> str:
        """Zwraca absolutną, znormalizowaną ścieżkę do pliku archiwum."""
        return self.archive_path

    def get_preview_path(self) -> str | None:
        """Zwraca absolutną, znormalizowaną ścieżkę do pliku podglądu lub None."""
        return self.preview_path

    def get_relative_archive_path(self) -> str:
        """Zwraca względną, znormalizowaną ścieżkę do pliku archiwum."""
        return os.path.relpath(self.archive_path, self.working_directory).replace(
            "\\", "/"
        )

    def get_relative_preview_path(self) -> str | None:
        """Zwraca względną, znormalizowaną ścieżkę do pliku podglądu lub None."""
        if not self.preview_path:
            return None
        return os.path.relpath(self.preview_path, self.working_directory).replace(
            "\\", "/"
        )

    def get_base_name(self) -> str:
        """Zwraca nazwę bazową pary plików."""
        return self.base_name

    def load_preview_thumbnail(self, size: int) -> None:
        """
        Ładuje miniaturę pliku podglądu.
        Jeśli plik podglądu nie istnieje, tworzy placeholder.
        """
        if self.preview_path and os.path.exists(self.preview_path):
            try:
                pixmap = QPixmap(self.preview_path)
                if not pixmap.isNull():
                    self.preview_thumbnail = pixmap.scaled(
                        size,
                        size,
                        aspectRatioMode=Qt.AspectRatioMode.KeepAspectRatio,
                        transformMode=Qt.TransformationMode.SmoothTransformation,
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

    def get_preview_thumbnail(self) -> QPixmap | None:
        """Zwraca załadowaną miniaturę."""
        return self.preview_thumbnail

    def get_archive_size(self) -> int | None:
        """Pobiera i zwraca rozmiar pliku archiwum w bajtach."""
        if self.archive_size_bytes is None:
            try:
                if os.path.exists(self.archive_path):
                    self.archive_size_bytes = os.path.getsize(self.archive_path)
                else:
                    logger.warning(
                        f"Plik archiwum nie istnieje, nie można pobrać rozmiaru: "
                        f"{self.archive_path}"
                    )
                    self.archive_size_bytes = 0  # lub inna wartość oznaczająca błąd
            except OSError as e:
                logger.error(f"Błąd odczytu rozmiaru pliku {self.archive_path}: {e}")
                self.archive_size_bytes = 0
        return self.archive_size_bytes

    def get_formatted_archive_size(self) -> str:
        """Zwraca sformatowany rozmiar pliku archiwum (np. KB, MB)."""
        size_bytes = self.get_archive_size()
        if size_bytes is None or size_bytes == 0:
            return "N/A"
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes / 1024**2:.1f} MB"
        else:
            return f"{size_bytes / 1024**3:.1f} GB"

    def toggle_favorite(self) -> None:
        """
        Przełącza status "ulubiony" dla danego pliku.

        Returns:
            bool: Nowy stan flagi is_favorite
        """
        self.is_favorite = not self.is_favorite
        log_msg = (
            f"Przełączono status 'ulubiony' dla {self.get_base_name()}: "
            f"{self.is_favorite}"
        )
        logger.debug(log_msg)
        return self.is_favorite

    def is_favorite_file(self):
        """
        Sprawdza, czy plik jest oznaczony jako "ulubiony".

        Returns:
            bool: True jeśli plik jest oznaczony jako ulubiony,
                  False w przeciwnym wypadku
        """
        return self.is_favorite

    def set_favorite(self, state):
        """
        Ustawia status "ulubiony" dla danego pliku.

        Args:
            state (bool): Nowy stan flagi is_favorite

        Returns:
            bool: Aktualny stan flagi is_favorite
        """
        self.is_favorite = bool(state)
        return self.is_favorite

    def set_stars(self, num_stars: int) -> None:
        """
        Ustawia liczbę gwiazdek dla pliku.

        Args:
            num_stars (int): Liczba gwiazdek (0-5).

        Returns:
            int: Ustawiona liczba gwiazdek.
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
            int: Liczba gwiazdek (0-5).
        """
        return self.stars

    def set_color_tag(self, color: str | None) -> None:
        """
        Ustawia tag kolorystyczny dla pliku.

        Args:
            color (str): Nazwa koloru lub kod hex. Pusty string
                         oznacza brak koloru.

        Returns:
            str: Ustawiony tag kolorystyczny.
        """
        self.color_tag = str(color) if color is not None else ""
        log_msg = (
            f"Ustawiono tag koloru dla {self.get_base_name()} na: "
            f"'{self.color_tag}'"
        )
        logger.debug(log_msg)
        return self.color_tag

    def get_color_tag(self) -> str:
        """
        Zwraca tag kolorystyczny przypisany do pliku.

        Returns:
            str: Tag kolorystyczny (może być pusty).
        """
        return self.color_tag
