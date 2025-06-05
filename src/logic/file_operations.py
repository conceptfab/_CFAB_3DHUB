"""
Operacje na plikach, takie jak otwieranie zewnętrznym programem, usuwanie, zmiana nazwy, itp.
"""

import logging
import os
import shutil

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from src.models.file_pair import FilePair

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


def manually_pair_files(
    archive_path: str, preview_path: str, working_directory: str
) -> FilePair | None:
    """
    Ręcznie paruje podany plik archiwum z plikiem podglądu.

    Jeśli nazwy bazowe plików (bez rozszerzeń) są różne, zmienia nazwę pliku podglądu,
    aby pasowała do nazwy bazowej pliku archiwum, zachowując oryginalne rozszerzenie podglądu.
    Przed zmianą nazwy sprawdza, czy plik o docelowej nazwie nie istnieje.

    Args:
        archive_path (str): Ścieżka absolutna do pliku archiwum.
        preview_path (str): Ścieżka absolutna do pliku podglądu.
        working_directory (str): Ścieżka do katalogu roboczego (używana do tworzenia FilePair).

    Returns:
        FilePair | None: Obiekt FilePair, jeśli parowanie się powiodło, w przeciwnym razie None.
    """
    logger.info(
        f"Rozpoczęto próbę ręcznego parowania: A='{archive_path}', P='{preview_path}'"
    )

    if not os.path.exists(archive_path):
        logger.error(
            f"Plik archiwum do ręcznego parowania nie istnieje: {archive_path}"
        )
        return None
    if not os.path.exists(preview_path):
        logger.error(
            f"Plik podglądu do ręcznego parowania nie istnieje: {preview_path}"
        )
        return None

    archive_base_name, _ = os.path.splitext(os.path.basename(archive_path))
    preview_base_name, preview_extension = os.path.splitext(
        os.path.basename(preview_path)
    )

    current_preview_path = preview_path

    if archive_base_name.lower() != preview_base_name.lower():
        logger.info(
            f"Nazwy bazowe plików są różne: '{archive_base_name}' vs '{preview_base_name}'. Próba zmiany nazwy podglądu."
        )

        # Nowa nazwa pliku podglądu to nazwa bazowa archiwum + oryginalne rozszerzenie podglądu
        new_preview_filename = archive_base_name + preview_extension
        new_preview_path = os.path.join(
            os.path.dirname(preview_path), new_preview_filename
        )

        if os.path.exists(new_preview_path):
            if new_preview_path.lower() == preview_path.lower():
                # Przypadek, gdy nazwa różni się tylko wielkością liter, a system plików jest case-insensitive
                # lub plik o tej samej nazwie (case-sensitive) już istnieje.
                # W tej sytuacji, jeśli nazwa docelowa jest taka sama jak bieżąca (po normalizacji case), uznajemy to za OK.
                logger.debug(
                    f"Plik podglądu '{preview_path}' ma już docelową nazwę (możliwe różnice wielkości liter)."
                )
                current_preview_path = (
                    new_preview_path  # Użyjemy ścieżki z poprawną wielkością liter
                )
            else:
                logger.error(
                    f"Nie można zmienić nazwy podglądu na '{new_preview_filename}', plik o tej nazwie już istnieje: {new_preview_path}"
                )
                return None
        else:
            try:
                os.rename(preview_path, new_preview_path)
                logger.info(
                    f"Zmieniono nazwę pliku podglądu z '{os.path.basename(preview_path)}' na '{new_preview_filename}'"
                )
                current_preview_path = new_preview_path
            except OSError as e:
                logger.error(
                    f"Nie udało się zmienić nazwy pliku podglądu '{preview_path}' na '{new_preview_path}': {e}"
                )
                return None
    else:
        logger.info(
            f"Nazwy bazowe plików są takie same: '{archive_base_name}'. Nie ma potrzeby zmiany nazwy podglądu."
        )

    try:
        paired_file = FilePair(
            archive_path=archive_path,
            preview_path=current_preview_path,  # Używamy aktualnej ścieżki podglądu
            working_directory=working_directory,
        )
        logger.info(
            f"Pomyślnie ręcznie sparowano: A='{paired_file.get_relative_archive_path()}', P='{paired_file.get_relative_preview_path()}'"
        )
        return paired_file
    except Exception as e:
        logger.error(f"Błąd tworzenia obiektu FilePair podczas ręcznego parowania: {e}")
        return None


# --- Nowe funkcje przeniesione z FilePair ---


def rename_file_pair(
    old_archive_path: str, old_preview_path: str | None, new_base_name: str
) -> tuple[str, str | None] | None:
    """
    Zmienia nazwę bazową dla pary plików (archiwum i podgląd).

    Args:
        old_archive_path (str): Aktualna ścieżka do pliku archiwum.
        old_preview_path (str | None): Aktualna ścieżka do pliku podglądu.
        new_base_name (str): Nowa nazwa bazowa pliku (bez rozszerzenia).

    Returns:
        tuple[str, str | None] | None: Krotka z nowymi ścieżkami (archiwum, podgląd)
                                      lub None w przypadku błędu.
    """
    logger.debug(
        f"Próba zmiany nazwy pary: A='{old_archive_path}', P='{old_preview_path}' na nową nazwę bazową '{new_base_name}'"
    )
    directory = os.path.dirname(old_archive_path)

    # Walidacja nowej nazwy
    forbidden_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]
    if any(char in new_base_name for char in forbidden_chars) or not new_base_name:
        logger.error(f"Nowa nazwa pliku '{new_base_name}' jest nieprawidłowa.")
        return None

    # Przygotowanie nowej ścieżki dla archiwum
    _, archive_ext = os.path.splitext(old_archive_path)
    new_archive_path = os.path.join(directory, new_base_name + archive_ext)

    # Przygotowanie nowej ścieżki dla podglądu, jeśli istnieje
    new_preview_path = None
    if old_preview_path:
        _, preview_ext = os.path.splitext(old_preview_path)
        new_preview_path = os.path.join(directory, new_base_name + preview_ext)

    # Sprawdzenie, czy pliki docelowe już nie istnieją (z wyjątkiem samych siebie)
    if os.path.exists(new_archive_path) and new_archive_path != old_archive_path:
        logger.error(f"Plik o nazwie '{new_archive_path}' już istnieje.")
        return None
    if (
        new_preview_path
        and old_preview_path
        and os.path.exists(new_preview_path)
        and new_preview_path != old_preview_path
    ):
        logger.error(f"Plik o nazwie '{new_preview_path}' już istnieje.")
        return None

    try:
        # Zmiana nazwy musi być bezpieczna: jeśli zmiana podglądu się nie powiedzie,
        # należy przywrócić starą nazwę archiwum.
        # Najpierw zmieniamy nazwę archiwum.
        if new_archive_path != old_archive_path:
            os.rename(old_archive_path, new_archive_path)
            logger.info(
                f"Zmieniono nazwę: '{old_archive_path}' -> '{new_archive_path}'"
            )
        else:
            logger.debug(f"Nazwa archiwum '{old_archive_path}' pozostaje bez zmian.")

        # Następnie zmieniamy nazwę podglądu, jeśli istnieje.
        if (
            old_preview_path
            and new_preview_path
            and new_preview_path != old_preview_path
        ):
            try:
                os.rename(old_preview_path, new_preview_path)
                logger.info(
                    f"Zmieniono nazwę: '{old_preview_path}' -> '{new_preview_path}'"
                )
            except Exception as e_preview:
                logger.error(
                    f"Błąd zmiany nazwy podglądu na '{new_preview_path}': {e_preview}. Przywracanie nazwy archiwum."
                )
                # Przywrócenie starej nazwy archiwum w razie błędu
                if new_archive_path != old_archive_path:
                    os.rename(new_archive_path, old_archive_path)
                return None

        return new_archive_path, new_preview_path
    except Exception as e:
        logger.error(
            f"Błąd podczas zmiany nazwy pliku archiwum na '{new_archive_path}': {e}"
        )
        return None


def delete_file_pair(archive_path: str, preview_path: str | None) -> bool:
    """
    Usuwa parę plików (archiwum i opcjonalnie podgląd).

    Args:
        archive_path (str): Ścieżka do pliku archiwum.
        preview_path (str | None): Ścieżka do pliku podglądu.

    Returns:
        bool: True, jeśli operacja się powiodła (lub pliki nie istniały),
              False w przypadku błędu.
    """
    logger.debug(f"Próba usunięcia pary plików: A='{archive_path}', P='{preview_path}'")
    success = True

    # Usuwanie pliku podglądu
    if preview_path and os.path.exists(preview_path):
        try:
            os.remove(preview_path)
            logger.info(f"Usunięto plik podglądu: {preview_path}")
        except OSError as e:
            logger.error(f"Nie udało się usunąć pliku podglądu '{preview_path}': {e}")
            success = False
            # Kontynuujemy próbę usunięcia archiwum, nawet jeśli podgląd się nie udał

    # Usuwanie pliku archiwum
    if os.path.exists(archive_path):
        try:
            os.remove(archive_path)
            logger.info(f"Usunięto plik archiwum: {archive_path}")
        except OSError as e:
            logger.error(f"Nie udało się usunąć pliku archiwum '{archive_path}': {e}")
            success = False
    else:
        # Jeśli archiwum nie istnieje, a podgląd tak, to logujemy ostrzeżenie,
        # ale operację uznajemy za "udaną" w kontekście usunięcia pary.
        logger.warning(
            f"Plik archiwum '{archive_path}' nie istniał podczas próby usunięcia."
        )

    return success


def move_file_pair(
    old_archive_path: str, old_preview_path: str | None, new_target_directory: str
) -> tuple[str, str | None] | None:
    """
    Przenosi parę plików (archiwum i podgląd) do nowego katalogu.

    Args:
        old_archive_path (str): Aktualna ścieżka do pliku archiwum.
        old_preview_path (str | None): Aktualna ścieżka do pliku podglądu.
        new_target_directory (str): Ścieżka do katalogu docelowego.

    Returns:
        tuple[str, str | None] | None: Krotka z nowymi, absolutnymi ścieżkami
                                      (archiwum, podgląd) lub None w przypadku błędu.
    """
    logger.debug(
        f"Próba przeniesienia pary: A='{old_archive_path}', P='{old_preview_path}' do folderu '{new_target_directory}'"
    )
    if not os.path.isdir(new_target_directory):
        logger.error(f"Katalog docelowy '{new_target_directory}' nie istnieje.")
        return None

    # Przygotowanie nowych ścieżek
    archive_filename = os.path.basename(old_archive_path)
    new_archive_path = os.path.join(new_target_directory, archive_filename)
    new_preview_path = None

    if old_preview_path:
        preview_filename = os.path.basename(old_preview_path)
        new_preview_path = os.path.join(new_target_directory, preview_filename)

    # Sprawdzenie, czy pliki docelowe już nie istnieją
    if os.path.exists(new_archive_path):
        logger.error(f"Plik '{new_archive_path}' już istnieje w lokalizacji docelowej.")
        return None
    if new_preview_path and os.path.exists(new_preview_path):
        logger.error(f"Plik '{new_preview_path}' już istnieje w lokalizacji docelowej.")
        return None

    try:
        # Przenosimy archiwum
        shutil.move(old_archive_path, new_archive_path)
        logger.info(f"Przeniesiono: '{old_archive_path}' -> '{new_archive_path}'")

        # Przenosimy podgląd, jeśli istnieje
        if old_preview_path and new_preview_path:
            try:
                shutil.move(old_preview_path, new_preview_path)
                logger.info(
                    f"Przeniesiono: '{old_preview_path}' -> '{new_preview_path}'"
                )
            except Exception as e_preview:
                logger.error(
                    f"Błąd przenoszenia podglądu '{old_preview_path}': {e_preview}. Przywracanie pozycji archiwum."
                )
                # Przywrócenie archiwum w razie błędu
                shutil.move(new_archive_path, old_archive_path)
                return None

        return new_archive_path, new_preview_path

    except Exception as e:
        logger.error(f"Błąd podczas przenoszenia archiwum '{old_archive_path}': {e}")
        # Jeśli archiwum nie zostało przeniesione, nie musimy nic cofać
        return None


# ... (reszta pliku, jeśli istnieje) ...
