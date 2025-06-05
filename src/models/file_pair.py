import logging
import os

from PyQt6.QtGui import QPixmap

logger = logging.getLogger(__name__)


class FilePair:
    def __init__(
        self, archive_path: str, preview_path: str | None, working_directory: str
    ):
        self.archive_path = archive_path
        self.preview_path = preview_path
        self.working_directory = (
            working_directory  # Przechowujemy dla operacji na ścieżkach względnych
        )
        self.preview_thumbnail: QPixmap | None = None
        self.archive_size_bytes: int | None = None
        self.is_favorite: bool = False
        self.stars: int = 0
        self.color_tag: str | None = None
        self.base_name = os.path.splitext(os.path.basename(archive_path))[0]

    def get_base_name(self) -> str:
        return self.base_name

    def get_archive_path(self):
        return self.archive_path

    def get_preview_path(self):
        return self.preview_path

    def get_archive_size(self) -> int | None:
        """
        Pobiera rozmiar pliku archiwum w bajtach.

        Returns:
            int: Rozmiar pliku archiwum w bajtach lub 0 w przypadku błędu
        """
        try:
            self.archive_size_bytes = os.path.getsize(self.archive_path)
            return self.archive_size_bytes
        except FileNotFoundError:
            logger.error(f"Nie znaleziono archiwum: {self.archive_path}")
            self.archive_size_bytes = 0
        except Exception as e:
            logger.error(f"Błąd rozmiaru archiwum {self.archive_path}: {e}")
            self.archive_size_bytes = 0

        return self.archive_size_bytes

    def get_formatted_archive_size(self) -> str:
        """
        Zwraca sformatowany rozmiar pliku archiwum w czytelnej postaci
        (B, KB, MB, GB).

        Jeśli rozmiar nie został jeszcze pobrany, wywołuje get_archive_size().

        Returns:
            str: Sformatowany rozmiar pliku z jednostką
        """
        if self.archive_size_bytes is None:
            self.get_archive_size()

        if self.archive_size_bytes is None or self.archive_size_bytes == 0:
            return "0 B"

        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(self.archive_size_bytes)
        unit_index = 0

        while size >= 1024.0 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1

        # Formatowanie liczby: do 2 miejsc po przecinku, usunięcie końcowych zer
        if size.is_integer():
            formatted_size = str(int(size))
        else:
            size_str = f"{size:.2f}"
            if "." in size_str:
                formatted_size = size_str.rstrip("0").rstrip(".")
            else:
                formatted_size = str(int(size))  # Fallback, gdyby rstrip usunął za dużo

        return f"{formatted_size} {units[unit_index]}"

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

    def get_relative_archive_path(self) -> str:
        """Zwraca względną ścieżkę pliku archiwum względem folderu roboczego."""
        if os.path.isabs(self.archive_path):
            return os.path.relpath(self.archive_path, self.working_directory)
        return self.archive_path  # Już jest względna

    def get_relative_preview_path(self) -> str | None:
        """Zwraca względną ścieżkę pliku podglądu względem folderu roboczego, jeśli istnieje."""
        if self.preview_path and os.path.isabs(self.preview_path):
            return os.path.relpath(self.preview_path, self.working_directory)
        return self.preview_path  # Już jest względna lub None
