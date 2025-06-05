import logging
import os
import shutil

from PIL import Image, UnidentifiedImageError
from PyQt6.QtGui import QPixmap

from src.utils.image_utils import create_placeholder_pixmap, pillow_image_to_qpixmap

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

    def load_preview_thumbnail(self, target_width: int, target_height: int) -> None:
        if not self.preview_path or not os.path.exists(self.preview_path):
            logger.warning(
                f"Plik podglądu nie istnieje: {self.preview_path}. Tworzenie placeholdera."
            )
            self.preview_thumbnail = create_placeholder_pixmap(
                target_width, target_height, "grey", "Brak podglądu"
            )
            return

        try:
            # Wczytanie obrazu przy użyciu Pillow
            with Image.open(self.preview_path) as img:
                # Utworzenie kopii obrazu do skalowania (thumbnail modyfikuje oryginalny obraz)
                thumbnail = img.copy()
                # Skalowanie z zachowaniem proporcji
                thumbnail.thumbnail((target_width, target_height), Image.LANCZOS)

                # Konwersja na QPixmap
                self.preview_thumbnail = pillow_image_to_qpixmap(thumbnail)

                if self.preview_thumbnail.isNull():
                    raise ValueError("Konwersja do QPixmap dała pusty wynik")

                return self.preview_thumbnail

        except FileNotFoundError:
            logger.error(f"Nie znaleziono pliku podglądu: {self.preview_path}")
            self.preview_thumbnail = create_placeholder_pixmap(
                target_width, target_height, text="Brak pliku"
            )
        except UnidentifiedImageError:
            logger.error(f"Nieprawidłowy format pliku: {self.preview_path}")
            self.preview_thumbnail = create_placeholder_pixmap(
                target_width, target_height, text="Błąd formatu"
            )
        except Exception as e:
            logger.error(f"Błąd wczytywania podglądu {self.preview_path}: {e}")
            self.preview_thumbnail = create_placeholder_pixmap(
                target_width, target_height, text="Błąd"
            )

        return self.preview_thumbnail

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
            logger.error(f"Nie znaleziono pliku archiwum: {self.archive_path}")
            self.archive_size_bytes = 0
        except Exception as e:
            logger.error(f"Błąd pobierania rozmiaru archiwum {self.archive_path}: {e}")
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

    def toggle_favorite(self) -> None:
        """
        Przełącza status "ulubiony" dla danego pliku.

        Returns:
            bool: Nowy stan flagi is_favorite
        """
        self.is_favorite = not self.is_favorite
        logger.debug(
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

    def set_stars(self, num_stars: int) -> None:
        """
        Ustawia liczbę gwiazdek dla pliku.

        Args:
            num_stars (int): Liczba gwiazdek (0-5).

        Returns:
            int: Ustawiona liczba gwiazdek.
        """
        if not isinstance(num_stars, int) or not (0 <= num_stars <= 5):
            logger.warning(
                f"Nieprawidłowa liczba gwiazdek ({num_stars}) "
                f"dla {self.get_base_name()}. Ustawiono 0."
            )
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
        logger.debug(
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

    def rename(self, new_base_name: str) -> bool:
        """
        Zmienia nazwę pliku archiwum i pliku podglądu, zachowując ich oryginalne rozszerzenia.
        Aktualizuje wewnętrzne ścieżki.
        """
        if not new_base_name:
            logger.error("Nowa nazwa bazowa nie może być pusta.")
            return False

        old_archive_path_abs = (
            os.path.join(self.working_directory, self.get_relative_archive_path())
            if not os.path.isabs(self.archive_path)
            else self.archive_path
        )
        archive_dir = os.path.dirname(old_archive_path_abs)
        archive_ext = os.path.splitext(old_archive_path_abs)[1]
        new_archive_path_abs = os.path.join(
            archive_dir, f"{new_base_name}{archive_ext}"
        )

        old_preview_path_abs = None
        new_preview_path_abs = None
        if self.preview_path:
            old_preview_path_abs = (
                os.path.join(self.working_directory, self.get_relative_preview_path())
                if not os.path.isabs(self.preview_path)
                else self.preview_path
            )
            preview_dir = os.path.dirname(old_preview_path_abs)
            preview_ext = os.path.splitext(old_preview_path_abs)[1]
            new_preview_path_abs = os.path.join(
                preview_dir, f"{new_base_name}{preview_ext}"
            )

        try:
            if os.path.exists(new_archive_path_abs):
                logger.error(
                    f"Plik archiwum o nowej nazwie {new_archive_path_abs} już istnieje."
                )
                return False
            if (
                new_preview_path_abs
                and os.path.exists(new_preview_path_abs)
                and old_preview_path_abs != new_preview_path_abs
            ):  # sprawdź czy plik podglądu o nowej nazwie istnieje i czy nie jest to ten sam plik
                logger.error(
                    f"Plik podglądu o nowej nazwie {new_preview_path_abs} już istnieje."
                )
                return False

            logger.info(
                f"Zmiana nazwy archiwum z {old_archive_path_abs} na {new_archive_path_abs}"
            )
            os.rename(old_archive_path_abs, new_archive_path_abs)
            self.archive_path = os.path.relpath(
                new_archive_path_abs, self.working_directory
            )

            if self.preview_path and old_preview_path_abs and new_preview_path_abs:
                logger.info(
                    f"Zmiana nazwy podglądu z {old_preview_path_abs} na {new_preview_path_abs}"
                )
                os.rename(old_preview_path_abs, new_preview_path_abs)
                self.preview_path = os.path.relpath(
                    new_preview_path_abs, self.working_directory
                )

            self.base_name = new_base_name
            logger.info(f"Pomyślnie zmieniono nazwę pary plików na: {new_base_name}")
            return True
        except OSError as e:
            logger.error(
                f"Błąd podczas zmiany nazwy plików dla '{self.base_name}' na '{new_base_name}': {e}"
            )
            # Próba przywrócenia starych nazw w razie częściowego niepowodzenia
            if os.path.exists(new_archive_path_abs) and not os.path.exists(
                old_archive_path_abs
            ):
                os.rename(new_archive_path_abs, old_archive_path_abs)
                logger.info(f"Przywrócono nazwę archiwum: {old_archive_path_abs}")
            if (
                new_preview_path_abs
                and old_preview_path_abs
                and os.path.exists(new_preview_path_abs)
                and not os.path.exists(old_preview_path_abs)
            ):
                os.rename(new_preview_path_abs, old_preview_path_abs)
                logger.info(f"Przywrócono nazwę podglądu: {old_preview_path_abs}")
            return False

    def delete(self) -> bool:
        """
        Usuwa plik archiwum i plik podglądu.
        """
        deleted_archive = False
        deleted_preview = False

        archive_path_abs = (
            os.path.join(self.working_directory, self.get_relative_archive_path())
            if not os.path.isabs(self.archive_path)
            else self.archive_path
        )

        try:
            if os.path.exists(archive_path_abs):
                logger.info(f"Usuwanie pliku archiwum: {archive_path_abs}")
                os.remove(archive_path_abs)
                deleted_archive = True
            else:
                logger.warning(
                    f"Plik archiwum {archive_path_abs} nie istnieje, nie można usunąć."
                )
                # Mimo wszystko uznajemy za sukces, jeśli pliku nie ma
                deleted_archive = True

        except OSError as e:
            logger.error(
                f"Błąd podczas usuwania pliku archiwum {archive_path_abs}: {e}"
            )
            return False  # Jeśli nie udało się usunąć archiwum, to jest to błąd krytyczny dla tej operacji

        if self.preview_path:
            preview_path_abs = (
                os.path.join(self.working_directory, self.get_relative_preview_path())
                if not os.path.isabs(self.preview_path)
                else self.preview_path
            )
            try:
                if os.path.exists(preview_path_abs):
                    logger.info(f"Usuwanie pliku podglądu: {preview_path_abs}")
                    os.remove(preview_path_abs)
                    deleted_preview = True
                else:
                    logger.warning(
                        f"Plik podglądu {preview_path_abs} nie istnieje, nie można usunąć."
                    )
                    deleted_preview = True  # Podobnie, uznajemy za sukces
            except OSError as e:
                logger.error(
                    f"Błąd podczas usuwania pliku podglądu {preview_path_abs}: {e}"
                )
                # Jeśli archiwum zostało usunięte, ale podgląd nie, to nadal jest to częściowy sukces
                # ale logujemy błąd. Można rozważyć, czy to powinno zwracać False.
                # Na razie, jeśli archiwum usunięte, to uznajemy za sukces operacji na parze.
        else:
            deleted_preview = True  # Brak pliku podglądu do usunięcia

        if deleted_archive and deleted_preview:
            logger.info(
                f"Pomyślnie usunięto parę plików dla (byłej) nazwy: {self.base_name}"
            )
            return True

        # Ten przypadek nie powinien wystąpić przy obecnej logice, ale dla pewności:
        logger.error(
            f"Nie udało się w pełni usunąć pary plików dla (byłej) nazwy: {self.base_name}. Archiwum usunięte: {deleted_archive}, Podgląd usunięty: {deleted_preview}"
        )
        return False

    def move(self, new_target_directory_abs: str) -> bool:
        """
        Przenosi plik archiwum i plik podglądu do new_target_directory_abs.
        Aktualizuje wewnętrzne ścieżki.
        """
        if not os.path.isdir(new_target_directory_abs):
            logger.error(
                f"Docelowy folder {new_target_directory_abs} nie istnieje lub nie jest folderem."
            )
            return False

        old_archive_path_abs = (
            os.path.join(self.working_directory, self.get_relative_archive_path())
            if not os.path.isabs(self.archive_path)
            else self.archive_path
        )
        archive_filename = os.path.basename(old_archive_path_abs)
        new_archive_path_abs = os.path.join(new_target_directory_abs, archive_filename)

        old_preview_path_abs = None
        new_preview_path_abs = None
        preview_filename = None
        if self.preview_path:
            old_preview_path_abs = (
                os.path.join(self.working_directory, self.get_relative_preview_path())
                if not os.path.isabs(self.preview_path)
                else self.preview_path
            )
            preview_filename = os.path.basename(old_preview_path_abs)
            new_preview_path_abs = os.path.join(
                new_target_directory_abs, preview_filename
            )

        try:
            if os.path.exists(new_archive_path_abs):
                logger.error(
                    f"Plik archiwum {new_archive_path_abs} już istnieje w folderze docelowym."
                )
                return False
            if new_preview_path_abs and os.path.exists(new_preview_path_abs):
                logger.error(
                    f"Plik podglądu {new_preview_path_abs} już istnieje w folderze docelowym."
                )
                return False

            logger.info(
                f"Przenoszenie archiwum z {old_archive_path_abs} do {new_archive_path_abs}"
            )
            shutil.move(old_archive_path_abs, new_archive_path_abs)
            self.archive_path = os.path.relpath(
                new_archive_path_abs, self.working_directory
            )

            if self.preview_path and old_preview_path_abs and new_preview_path_abs:
                logger.info(
                    f"Przenoszenie podglądu z {old_preview_path_abs} do {new_preview_path_abs}"
                )
                shutil.move(old_preview_path_abs, new_preview_path_abs)
                self.preview_path = os.path.relpath(
                    new_preview_path_abs, self.working_directory
                )

            logger.info(
                f"Pomyślnie przeniesiono parę plików '{self.base_name}' do '{new_target_directory_abs}'"
            )
            return True
        except (OSError, shutil.Error) as e:
            logger.error(
                f"Błąd podczas przenoszenia plików dla '{self.base_name}' do '{new_target_directory_abs}': {e}"
            )
            # Próba przywrócenia, jeśli coś poszło nie tak po przeniesieniu pierwszego pliku
            # To jest skomplikowane, bo shutil.move może nadpisać.
            # Na razie, jeśli wystąpi błąd, zakładamy, że stan może być niespójny.
            # Można by próbować przenieść z powrotem, jeśli pierwszy plik został przeniesiony, a drugi nie.
            # np. if os.path.exists(new_archive_path_abs) and not os.path.exists(old_archive_path_abs):
            # shutil.move(new_archive_path_abs, old_archive_path_abs)
            return False
