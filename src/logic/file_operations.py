"""
Operacje na plikach, takie jak otwieranie zewnętrznym programem, usuwanie, zmiana nazwy, itp.
"""

import logging
import os
import platform
import shutil

from PyQt6.QtCore import QStandardPaths, QUrl
from PyQt6.QtGui import QDesktopServices

logger = logging.getLogger(__name__)


def open_archive_externally(archive_path: str) -> bool:
    """Otwiera plik archiwum w domyślnym programie systemowym."""
    if not os.path.exists(archive_path):
        logger.error(f"Plik archiwum nie istnieje: {archive_path}")
        return False
    try:
        # QDesktopServices.openUrl jest bardziej przenośne niż os.startfile
        # i działa lepiej z różnymi typami ścieżek (np. UNC na Windows).
        # Tworzymy URL z lokalnej ścieżki pliku.
        url = QUrl.fromLocalFile(archive_path)
        if QDesktopServices.openUrl(url):
            logger.info(f"Pomyślnie zainicjowano otwarcie archiwum: {archive_path}")
            return True
        else:
            logger.error(
                f"Nie udało się otworzyć archiwum (QDesktopServices): {archive_path}"
            )
            # Próba z os.startfile jako fallback dla Windows, jeśli QDesktopServices zawiedzie
            if os.name == "nt":
                try:
                    os.startfile(archive_path)
                    logger.info(
                        f"Pomyślnie zainicjowano otwarcie archiwum (os.startfile): {archive_path}"
                    )
                    return True
                except Exception as e_os:
                    logger.error(
                        f"Nie udało się otworzyć archiwum (os.startfile): {archive_path}. Błąd: {e_os}"
                    )
                    return False
            return False
    except Exception as e:
        logger.error(
            f"Wystąpił nieoczekiwany błąd podczas próby otwarcia archiwum {archive_path}: {e}"
        )
        return False


def create_folder(parent_directory: str, folder_name: str) -> str | None:
    """Tworzy nowy folder w podanej lokalizacji.
    Zwraca pełną ścieżkę do utworzonego folderu lub None w przypadku błędu.
    """
    if not os.path.isdir(parent_directory):
        logger.error(f"Katalog nadrzędny '{parent_directory}' nie istnieje.")
        return None

    # Zabezpieczenie przed niedozwolonymi znakami w nazwie folderu (podstawowe)
    # Można rozbudować o bardziej rygorystyczne walidacje
    forbidden_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
    if any(char in folder_name for char in forbidden_chars) or not folder_name.strip():
        logger.error(f"Nazwa folderu '{folder_name}' jest nieprawidłowa lub pusta.")
        return None

    folder_path = os.path.join(parent_directory, folder_name)
    try:
        os.makedirs(
            folder_path, exist_ok=True
        )  # exist_ok=True - nie rzuca błędu jeśli folder już istnieje
        logger.info(f"Folder '{folder_path}' został utworzony lub już istniał.")
        return folder_path
    except OSError as e:
        logger.error(f"Nie udało się utworzyć folderu '{folder_path}': {e}")
        return None


def rename_folder(folder_path: str, new_folder_name: str) -> str | None:
    """Zmienia nazwę folderu.
    Zwraca nową pełną ścieżkę do folderu lub None w przypadku błędu.
    """
    if not os.path.isdir(folder_path):
        logger.error(f"Folder '{folder_path}' nie istnieje lub nie jest folderem.")
        return None

    forbidden_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
    if (
        any(char in new_folder_name for char in forbidden_chars)
        or not new_folder_name.strip()
    ):
        logger.error(
            f"Nowa nazwa folderu '{new_folder_name}' jest nieprawidłowa lub pusta."
        )
        return None

    parent_dir = os.path.dirname(folder_path)
    new_folder_path = os.path.join(parent_dir, new_folder_name)

    if os.path.exists(new_folder_path):
        logger.error(f"Folder o nazwie '{new_folder_path}' już istnieje.")
        return None

    try:
        os.rename(folder_path, new_folder_path)
        logger.info(
            f"Zmieniono nazwę folderu z '{folder_path}' na '{new_folder_path}'."
        )
        return new_folder_path
    except OSError as e:
        logger.error(f"Nie udało się zmienić nazwy folderu '{folder_path}': {e}")
        return None


def delete_folder(folder_path: str, delete_content: bool = False) -> bool:
    """Usuwa folder. Jeśli delete_content jest True, usuwa folder wraz z zawartością.
    W przeciwnym razie usuwa tylko pusty folder.
    """
    if not os.path.isdir(folder_path):
        logger.warning(f"Folder '{folder_path}' nie istnieje, nie można usunąć.")
        return True  # Uznajemy za sukces, jeśli folderu nie ma

    try:
        if delete_content:
            shutil.rmtree(folder_path)
            logger.info(f"Folder '{folder_path}' i jego zawartość zostały usunięte.")
        else:
            if not os.listdir(folder_path):  # Sprawdź czy folder jest pusty
                os.rmdir(folder_path)
                logger.info(f"Pusty folder '{folder_path}' został usunięty.")
            else:
                logger.error(
                    f"Folder '{folder_path}' nie jest pusty. Aby usunąć, ustaw delete_content=True."
                )
                return False
        return True
    except OSError as e:
        logger.error(f"Nie udało się usunąć folderu '{folder_path}': {e}")
        return False


# ... (reszta pliku, jeśli istnieje) ...
