import logging
import os

from PIL import Image, UnidentifiedImageError

from src.utils.image_utils import create_placeholder_pixmap, pillow_image_to_qpixmap


class FilePair:
    def __init__(self, archive_path, preview_path):
        self.archive_path = archive_path
        self.preview_path = preview_path
        self.preview_thumbnail = None
        self.archive_size_bytes = None
        self.is_favorite = False  # Domyślnie plik nie jest "ulubionym"
        self.stars = 0  # Domyślnie 0 gwiazdek
        self.color_tag = ""  # Domyślnie brak tagu kolorystycznego
        logging.debug(f"Utworzono FilePair: {self.get_base_name()}")

    def get_base_name(self):
        return os.path.splitext(os.path.basename(self.archive_path))[0]

    def get_archive_path(self):
        return self.archive_path

    def get_preview_path(self):
        return self.preview_path

    def load_preview_thumbnail(self, target_size_wh):
        """
        Wczytuje plik podglądu i tworzy z niego miniaturę o zadanym rozmiarze.

        Args:
            target_size_wh (tuple): Docelowy rozmiar miniatury (szerokość,
                                    wysokość) w pikselach

        Returns:
            QPixmap: Utworzona miniatura jako obiekt QPixmap
        """
        width, height = target_size_wh
        try:
            # Wczytanie obrazu przy użyciu Pillow
            with Image.open(self.preview_path) as img:
                # Utworzenie kopii obrazu do skalowania (thumbnail modyfikuje oryginalny obraz)
                thumbnail = img.copy()
                # Skalowanie z zachowaniem proporcji
                thumbnail.thumbnail(target_size_wh, Image.LANCZOS)

                # Konwersja na QPixmap
                self.preview_thumbnail = pillow_image_to_qpixmap(thumbnail)

                if self.preview_thumbnail.isNull():
                    raise ValueError("Konwersja do QPixmap dała pusty wynik")

                return self.preview_thumbnail

        except FileNotFoundError:
            logging.error(f"Nie znaleziono pliku podglądu: {self.preview_path}")
            self.preview_thumbnail = create_placeholder_pixmap(
                width, height, text="Brak pliku"
            )
        except UnidentifiedImageError:
            logging.error(f"Nieprawidłowy format pliku: {self.preview_path}")
            self.preview_thumbnail = create_placeholder_pixmap(
                width, height, text="Błąd formatu"
            )
        except Exception as e:
            logging.error(f"Błąd wczytywania podglądu {self.preview_path}: {e}")
            self.preview_thumbnail = create_placeholder_pixmap(
                width, height, text="Błąd"
            )

        return self.preview_thumbnail

    def get_archive_size(self):
        """
        Pobiera rozmiar pliku archiwum w bajtach.

        Returns:
            int: Rozmiar pliku archiwum w bajtach lub 0 w przypadku błędu
        """
        try:
            self.archive_size_bytes = os.path.getsize(self.archive_path)
            return self.archive_size_bytes
        except FileNotFoundError:
            logging.error(f"Nie znaleziono pliku archiwum: {self.archive_path}")
            self.archive_size_bytes = 0
        except Exception as e:
            logging.error(f"Błąd pobierania rozmiaru archiwum {self.archive_path}: {e}")
            self.archive_size_bytes = 0

        return self.archive_size_bytes

    def get_formatted_archive_size(self):
        """
        Zwraca sformatowany rozmiar pliku archiwum w czytelnej postaci
        (B, KB, MB, GB).

        Jeśli rozmiar nie został jeszcze pobrany, wywołuje get_archive_size().

        Returns:
            str: Sformatowany rozmiar pliku z jednostką
        """
        if self.archive_size_bytes is None:
            self.get_archive_size()

        # Obsługa przypadku, gdy rozmiar nadal jest None lub 0
        if self.archive_size_bytes is None or self.archive_size_bytes == 0:
            return "0 B"

        # Konwersja na czytelny format z odpowiednią jednostką
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
            formatted_size = (
                f"{size:.2f}".rstrip("0").rstrip(".")
                if "." in f"{size:.2f}"
                else f"{int(size)}"
            )

        return f"{formatted_size} {units[unit_index]}"

    def toggle_favorite(self):
        """
        Przełącza status "ulubiony" dla danego pliku.

        Returns:
            bool: Nowy stan flagi is_favorite
        """
        self.is_favorite = not self.is_favorite
        logging.debug(
            f"Przełączono status 'ulubiony' dla {self.get_base_name()}: "
            f"{self.is_favorite}"
        )
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

    def set_stars(self, num_stars: int) -> int:
        """
        Ustawia liczbę gwiazdek dla pliku.

        Args:
            num_stars (int): Liczba gwiazdek (0-5).

        Returns:
            int: Ustawiona liczba gwiazdek.
        """
        if not isinstance(num_stars, int) or not (0 <= num_stars <= 5):
            logging.warning(
                f"Nieprawidłowa liczba gwiazdek ({num_stars}) "
                f"dla {self.get_base_name()}. Ustawiono 0."
            )
            self.stars = 0
        else:
            self.stars = num_stars
        logging.debug(f"Ustawiono gwiazdki dla {self.get_base_name()} na: {self.stars}")
        return self.stars

    def get_stars(self) -> int:
        """
        Zwraca liczbę gwiazdek przypisanych do pliku.

        Returns:
            int: Liczba gwiazdek (0-5).
        """
        return self.stars

    def set_color_tag(self, color: str) -> str:
        """
        Ustawia tag kolorystyczny dla pliku.

        Args:
            color (str): Nazwa koloru lub kod hex. Pusty string
                         oznacza brak koloru.

        Returns:
            str: Ustawiony tag kolorystyczny.
        """
        self.color_tag = str(color) if color is not None else ""
        logging.debug(
            f"Ustawiono tag koloru dla {self.get_base_name()} na: "
            f"'{self.color_tag}'"
        )
        return self.color_tag

    def get_color_tag(self) -> str:
        """
        Zwraca tag kolorystyczny przypisany do pliku.

        Returns:
            str: Tag kolorystyczny (może być pusty).
        """
        return self.color_tag
