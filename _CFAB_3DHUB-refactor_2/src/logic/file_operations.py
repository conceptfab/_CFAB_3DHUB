"""
Operacje na plikach, takie jak otwieranie zewnętrznym programem, usuwanie, zmiana nazwy, itp.
"""

import logging
import os
import shutil

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from src.models.file_pair import FilePair
from src.ui.delegates.workers import (
    CreateFolderWorker,
    DeleteFilePairWorker,
    DeleteFolderWorker,
    ManuallyPairFilesWorker,
    MoveFilePairWorker,
    RenameFilePairWorker,
    RenameFolderWorker,
)
from src.utils.path_utils import is_valid_filename, normalize_path

logger = logging.getLogger(__name__)


def open_archive_externally(archive_path: str) -> bool:
    """Otwiera plik archiwum w domyślnym programie systemowym."""
    # Normalizacja ścieżki dla spójności
    archive_path = normalize_path(archive_path)

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


def create_folder(parent_directory: str, folder_name: str) -> CreateFolderWorker | None:
    """
    Inicjuje operację tworzenia nowego folderu w podanej lokalizacji w osobnym wątku.

    Args:
        parent_directory: Ścieżka do katalogu nadrzędnego.
        folder_name: Nazwa nowego folderu.

    Returns:
        Instancja CreateFolderWorker, jeśli walidacja wstępna przebiegła pomyślnie,
        w przeciwnym razie None. UI powinno podłączyć się do sygnałów workera,
        aby otrzymać wynik operacji lub informację o błędzie.
    """
    # Normalizacja ścieżki katalogu nadrzędnego
    parent_dir_normalized = normalize_path(parent_directory)

    # Szybka walidacja przed utworzeniem workera
    if not os.path.isdir(parent_dir_normalized):
        logger.error(f"Katalog nadrzędny '{parent_dir_normalized}' nie istnieje.")
        # W tym przypadku możemy od razu zwrócić None, bo błąd jest natychmiastowy
        # i nie ma sensu tworzyć workera.
        # Alternatywnie, worker mógłby emitować ten błąd, ale to mniej wydajne.
        return None

    if not is_valid_filename(folder_name):
        logger.error(f"Nazwa folderu '{folder_name}' jest nieprawidłowa lub pusta.")
        return None

    # Utworzenie i zwrócenie workera.
    # UI będzie odpowiedzialne za uruchomienie go w QThreadPool i obsługę sygnałów.
    worker = CreateFolderWorker(
        parent_directory=parent_dir_normalized, folder_name=folder_name
    )
    logger.debug(
        f"Utworzono CreateFolderWorker dla: {parent_dir_normalized} / {folder_name}"
    )
    return worker


def rename_folder(folder_path: str, new_folder_name: str) -> RenameFolderWorker | None:
    """
    Inicjuje operację zmiany nazwy folderu w osobnym wątku.

    Args:
        folder_path: Aktualna ścieżka do folderu.
        new_folder_name: Nowa nazwa dla folderu.

    Returns:
        Instancja RenameFolderWorker, jeśli walidacja wstępna przebiegła pomyślnie,
        w przeciwnym razie None. UI powinno podłączyć się do sygnałów workera,
        aby otrzymać wynik operacji lub informację o błędzie.
    """
    # Normalizacja ścieżki folderu
    folder_path_normalized = normalize_path(folder_path)

    # Szybka walidacja przed utworzeniem workera
    if not os.path.isdir(folder_path_normalized):
        logger.error(
            f"Folder '{folder_path_normalized}' nie istnieje lub nie jest folderem."
        )
        return None

    if not is_valid_filename(new_folder_name):
        logger.error(
            f"Nowa nazwa folderu '{new_folder_name}' jest nieprawidłowa lub pusta."
        )
        return None

    parent_dir = os.path.dirname(folder_path_normalized)
    new_folder_path_check = normalize_path(os.path.join(parent_dir, new_folder_name))

    if os.path.exists(new_folder_path_check):
        logger.error(f"Folder o nazwie '{new_folder_path_check}' już istnieje.")
        return None

    # Utworzenie i zwrócenie workera.
    worker = RenameFolderWorker(
        folder_path=folder_path_normalized, new_folder_name=new_folder_name
    )
    logger.debug(
        f"Utworzono RenameFolderWorker dla: {folder_path_normalized} -> {new_folder_name}"
    )
    return worker


def delete_folder(
    folder_path: str, delete_content: bool = False
) -> DeleteFolderWorker | None:
    """
    Inicjuje operację usuwania folderu w osobnym wątku.

    Args:
        folder_path: Ścieżka do folderu, który ma zostać usunięty.
        delete_content: Jeśli True, usuwa folder wraz z zawartością.
                        W przeciwnym razie usuwa tylko pusty folder.

    Returns:
        Instancja DeleteFolderWorker, jeśli walidacja wstępna przebiegła pomyślnie,
        w przeciwnym razie None. UI powinno podłączyć się do sygnałów workera,
        aby otrzymać wynik operacji lub informację o błędzie.
    """
    folder_path_normalized = normalize_path(folder_path)

    # Szybka walidacja przed utworzeniem workera
    # Nie sprawdzamy tutaj, czy folder istnieje, bo worker to obsłuży
    # i może to być pożądane (np. jeśli folder został usunięty międzyczasie).
    # Wystarczy, że ścieżka jest w ogóle sensowna (choć normalize_path już to trochę robi).

    # Możemy dodać walidację, czy ścieżka nie jest np. rootem dysku, dla bezpieczeństwa.
    # if folder_path_normalized == os.path.abspath(os.sep): # Prosty przykład dla roota
    #     logger.error(f"Próba usunięcia katalogu głównego: {folder_path_normalized}")
    #     return None

    worker = DeleteFolderWorker(
        folder_path=folder_path_normalized, delete_content=delete_content
    )
    logger.debug(
        f"Utworzono DeleteFolderWorker dla: {folder_path_normalized}, delete_content={delete_content}"
    )
    return worker


def manually_pair_files(
    archive_path: str, preview_path: str, working_directory: str
) -> ManuallyPairFilesWorker | None:
    """
    Inicjuje operację ręcznego parowania plików archiwum z plikiem podglądu w osobnym wątku.

    Jeśli nazwy bazowe plików (bez rozszerzeń) są różne, worker spróbuje zmienić nazwę pliku podglądu,
    aby pasowała do nazwy bazowej pliku archiwum, zachowując oryginalne rozszerzenie podglądu.
    Operacja uwzględnia problem wielkości liter w nazwach plików.

    Args:
        archive_path (str): Ścieżka absolutna do pliku archiwum.
        preview_path (str): Ścieżka absolutna do pliku podglądu.
        working_directory (str): Ścieżka do katalogu roboczego (używana do tworzenia FilePair).

    Returns:
        ManuallyPairFilesWorker | None: Instancja workera lub None, jeśli wstępna walidacja się nie powiedzie.
                                        UI powinno podłączyć się do sygnałów workera.
    """
    # Podstawowa walidacja przed utworzeniem workera
    if not archive_path or not preview_path or not working_directory:
        logger.error(
            "Ścieżki do archiwum, podglądu lub katalogu roboczego nie mogą być puste."
        )
        return None

    # Normalizacja nie jest tu konieczna, worker to zrobi.
    # Sprawdzenie istnienia plików również zrobi worker, bo może to być część logiki (np. emitowanie błędu)

    worker = ManuallyPairFilesWorker(
        archive_path=archive_path,
        preview_path=preview_path,
        working_directory=working_directory,
    )
    logger.debug(
        f"Utworzono ManuallyPairFilesWorker dla: A='{archive_path}', P='{preview_path}'"
    )
    return worker


def rename_file_pair(
    file_pair: FilePair, new_base_name: str, working_directory: str
) -> RenameFilePairWorker | None:
    """Przygotowuje i zwraca worker do zmiany nazwy pary plików."""
    logger.info(
        f"Żądanie zmiany nazwy pary plików: '{file_pair.base_name}' na '{new_base_name}' w katalogu '{working_directory}'"
    )

    if not file_pair or not file_pair.archive_path or not file_pair.preview_path:
        logger.warning("Nieprawidłowy obiekt FilePair lub brakujące ścieżki.")
        # W przyszłości można rozważyć rzucenie wyjątku zamiast zwracania None
        return None

    if not new_base_name or not new_base_name.strip():
        logger.warning("Nowa nazwa bazowa nie może być pusta.")
        return None

    # Sprawdzenie, czy pliki oryginalne istnieją
    if not os.path.exists(file_pair.archive_path):
        logger.error(f"Plik archiwum '{file_pair.archive_path}' nie istnieje.")
        # Można by tu zgłosić błąd do UI inaczej niż przez worker
        return None

    if not os.path.exists(file_pair.preview_path):
        logger.error(f"Plik podglądu '{file_pair.preview_path}' nie istnieje.")
        return None

    # Walidacja nowej nazwy (np. pod kątem niedozwolonych znaków) - pominięto dla uproszczenia,
    # ale worker powinien to obsłużyć i zgłosić błąd przez sygnał.

    # Sprawdzenie, czy nowe nazwy plików nie kolidują z istniejącymi plikami
    # (chyba że to te same pliki - co jest dozwolone jeśli np. zmienia się tylko wielkość liter)
    # Tę logikę dokładniej obsłuży worker.

    try:
        worker = RenameFilePairWorker(file_pair, new_base_name, working_directory)
        logger.debug(
            f"Utworzono RenameFilePairWorker dla '{file_pair.base_name}' -> '{new_base_name}'"
        )
        return worker
    except Exception as e:
        logger.error(f"Nie udało się utworzyć RenameFilePairWorker: {e}", exc_info=True)
        return None


# --- Nowe funkcje przeniesione z FilePair ---


def delete_file_pair(file_pair: FilePair) -> DeleteFilePairWorker | None:
    """Przygotowuje i zwraca worker do usuwania pary plików."""
    logger.info(
        f"Żądanie usunięcia pary plików: '{file_pair.base_name}' (A: '{file_pair.archive_path}', P: '{file_pair.preview_path}')"
    )

    if not file_pair or not file_pair.archive_path or not file_pair.preview_path:
        logger.warning(
            "Nieprawidłowy obiekt FilePair lub brakujące ścieżki do usunięcia."
        )
        return None

    # Sprawdzenie, czy pliki istnieją - worker to obsłuży i może zgłosić postęp/sukces nawet jeśli nie istnieją
    # if not os.path.exists(file_pair.archive_path) and not os.path.exists(file_pair.preview_path):
    #     logger.info(f"Żaden z plików pary '{file_pair.base_name}' nie istnieje. Operacja pominięta.")
    #     # Można by zwrócić specjalny worker, który od razu emituje finished, lub None
    #     return None

    try:
        worker = DeleteFilePairWorker(file_pair)
        logger.debug(f"Utworzono DeleteFilePairWorker dla '{file_pair.base_name}'")
        return worker
    except Exception as e:
        logger.error(f"Nie udało się utworzyć DeleteFilePairWorker: {e}", exc_info=True)
        return None


def move_file_pair(
    file_pair: FilePair, new_target_directory: str
) -> MoveFilePairWorker | None:
    """
    Przygotowuje i zwraca worker do przenoszenia pary plików do nowego katalogu.
    """
    logger.info(
        f"Żądanie przeniesienia pary plików '{file_pair.base_name}' do katalogu '{new_target_directory}'"
    )

    if not file_pair or not file_pair.archive_path:
        logger.warning("Nieprawidłowy obiekt FilePair lub brak ścieżki do archiwum.")
        return None

    # Preview path jest opcjonalny, więc nie sprawdzamy go tutaj krytycznie

    if not new_target_directory or not new_target_directory.strip():
        logger.warning("Docelowy katalog nie może być pusty.")
        return None

    normalized_target_dir = normalize_path(new_target_directory)

    if not os.path.isdir(normalized_target_dir):
        logger.error(
            f"Katalog docelowy '{normalized_target_dir}' nie istnieje lub nie jest katalogiem."
        )
        return None

    # Dalszą, bardziej szczegółową walidację (np. istnienie plików źródłowych, konflikty w miejscu docelowym)
    # przeprowadzi worker, aby móc emitować odpowiednie sygnały o błędach.

    try:
        worker = MoveFilePairWorker(file_pair, normalized_target_dir)
        logger.debug(
            f"Utworzono MoveFilePairWorker dla '{file_pair.base_name}' -> '{normalized_target_dir}'"
        )
        return worker
    except Exception as e:
        logger.error(f"Nie udało się utworzyć MoveFilePairWorker: {e}", exc_info=True)
        return None


def create_pair_from_files(
    archive_path: str, preview_path: str
) -> ManuallyPairFilesWorker | None:
    """
    Wrapper dla manually_pair_files - tworzy parę plików z podanych ścieżek.

    Args:
        archive_path (str): Ścieżka do pliku archiwum.
        preview_path (str): Ścieżka do pliku podglądu.

    Returns:
        FilePair | None: Obiekt FilePair jeśli parowanie się powiodło, None w przypadku błędu.
    """
    # Normaliza ścieżki
    archive_path = normalize_path(archive_path)
    preview_path = normalize_path(preview_path)

    # Określ katalog roboczy na podstawie archiwum
    working_directory = os.path.dirname(archive_path)

    logger.info(f"Tworzenie pary z plików: A='{archive_path}', P='{preview_path}'")

    # Użyj istniejącej funkcji manually_pair_files
    return manually_pair_files(archive_path, preview_path, working_directory)


# ... (reszta pliku, jeśli istnieje) ...
