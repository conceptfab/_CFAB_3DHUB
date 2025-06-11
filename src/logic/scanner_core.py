"""
Podstawowe funkcje skanowania katalogów.
"""

import logging
import os
import time
from collections import defaultdict
from typing import Callable, Dict, List, Optional

from src import app_config
from src.utils.path_utils import normalize_path, path_exists

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Używamy definicji rozszerzeń z centralnego pliku konfiguracyjnego
ARCHIVE_EXTENSIONS = set(app_config.SUPPORTED_ARCHIVE_EXTENSIONS)
PREVIEW_EXTENSIONS = set(app_config.SUPPORTED_PREVIEW_EXTENSIONS)


class ScanningInterrupted(Exception):
    """Wyjątek rzucany, gdy skanowanie zostało przerwane przez użytkownika."""

    pass


def get_directory_modification_time(directory: str) -> float:
    """
    Pobiera maksymalny czas modyfikacji dla katalogu i jego zawartości.

    Args:
        directory: Ścieżka do katalogu

    Returns:
        Znacznik czasu ostatniej modyfikacji (timestamp)
    """
    if not path_exists(directory):
        return 0

    try:
        max_mtime = os.path.getmtime(directory)
    except (PermissionError, OSError) as e:
        logger.warning(
            f"Nie można uzyskać czasu modyfikacji dla katalogu {directory}: {e}"
        )
        return 0

    # Sprawdzamy wszystkie pliki i podfoldery w katalogu (tylko 1 poziom w głąb)
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                try:
                    current_mtime = entry.stat().st_mtime
                    if current_mtime > max_mtime:
                        max_mtime = current_mtime
                except (PermissionError, OSError) as e:
                    logger.warning(
                        f"Nie można uzyskać czasu modyfikacji dla {entry.path}: {e}"
                    )
                    # Kontynuujemy sprawdzanie innych plików/folderów
    except (PermissionError, OSError) as e:
        logger.warning(f"Nie można odczytać zawartości katalogu {directory}: {e}")
        # Zwracamy aktualny max_mtime, aby nie stracić już zebranych informacji

    return max_mtime


def collect_files_streaming(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, List[str]]:
    """
    Zbiera wszystkie pliki w katalogu z streaming progress (bez pre-estimation).

    OPTYMALIZACJA: Usunięto podwójne skanowanie - progress jest streamowany
    w czasie rzeczywistym bez wstępnego oszacowania liczby folderów.

    Args:
        directory: Ścieżka do katalogu do przeskanowania
        max_depth: Maksymalna głębokość rekursji, -1 oznacza brak limitu
        interrupt_check: Opcjonalna funkcja sprawdzająca czy przerwać skanowanie
        force_refresh: Czy wymusić odświeżenie cache (ignoruje cache)
        progress_callback: Opcjonalna funkcja do raportowania postępu (procent, wiadomość)

    Returns:
        Słownik zmapowanych plików, gdzie kluczem jest nazwa bazowa (bez rozszerzenia),
        a wartością lista pełnych ścieżek do plików.

    Raises:
        ScanningInterrupted: Jeśli skanowanie zostało przerwane
    """
    normalized_dir = normalize_path(directory)

    # Sprawdź ujednolicony cache
    if not force_refresh:
        from .scan_cache import unified_cache
        cached_file_map = unified_cache.get_file_map(normalized_dir)
        if cached_file_map is not None:
            logger.debug(
                f"CACHE HIT (unified): używam buforowanych plików dla {normalized_dir}"
            )
            if progress_callback:
                progress_callback(100, f"Używam cache dla {normalized_dir}")
            return cached_file_map

    # Jeśli katalog nie istnieje lub nie jest katalogiem, zwróć pusty słownik
    if not path_exists(normalized_dir) or not os.path.isdir(normalized_dir):
        logger.warning(f"Katalog {normalized_dir} nie istnieje lub nie jest katalogiem")
        if progress_callback:
            progress_callback(100, f"Katalog {normalized_dir} nie istnieje")
        return {}

    logger.info(f"Rozpoczęto STREAMING zbieranie plików z katalogu: {normalized_dir}")
    if progress_callback:
        progress_callback(0, f"Rozpoczynam streaming skanowanie: {normalized_dir}")

    file_map = defaultdict(list)
    total_folders_scanned = 0
    total_files_found = 0
    start_time = time.time()

    # Zestaw odwiedzonych katalogów (do obsługi pętli symbolicznych)
    visited_dirs = set()

    def _walk_directory_streaming(current_dir: str, depth: int = 0):
        nonlocal total_folders_scanned, total_files_found

        # EARLY STOPPING: Sprawdzenie czy należy przerwać skanowanie
        if interrupt_check and interrupt_check():
            logger.warning("Skanowanie przerwane przez użytkownika")
            raise ScanningInterrupted("Skanowanie przerwane przez użytkownika")

        # EARLY STOPPING: Sprawdzanie co każde 50 plików dla responsywności
        if total_files_found % 50 == 0 and interrupt_check and interrupt_check():
            logger.warning(
                "Skanowanie przerwane przez użytkownika podczas przetwarzania plików"
            )
            raise ScanningInterrupted("Skanowanie przerwane przez użytkownika")

        # Obsługa limitu głębokości
        if max_depth >= 0 and depth > max_depth:
            return

        # Streaming progress - raportowanie w czasie rzeczywistym
        if progress_callback:
            # Progress oparty na liczbie przeskanowanych folderów (rosnąco)
            # Skaluje od 0 do 95% w miarę zwiększania się liczby folderów
            progress = min(95, total_folders_scanned * 2)  # Aproksymacja progressu
            progress_callback(
                progress,
                f"Skanowanie: {os.path.basename(current_dir)} ({total_files_found} plików, {total_folders_scanned} folderów)",
            )

        # Zabezpieczenie przed zapętleniem (symlinki)
        normalized_current = os.path.realpath(current_dir)
        if normalized_current in visited_dirs:
            logger.warning(f"Wykryto pętlę w katalogach: {normalized_current}")
            return
        visited_dirs.add(normalized_current)

        # Skanowanie folderu
        try:
            total_folders_scanned += 1
            entries = list(os.scandir(current_dir))

            # EARLY STOPPING: Sprawdzenie przerwania po liście folderów
            if interrupt_check and interrupt_check():
                logger.warning(
                    "Skanowanie przerwane podczas odczytu zawartości folderu"
                )
                raise ScanningInterrupted(
                    "Skanowanie przerwane podczas odczytu zawartości folderu"
                )

            # Najpierw przetwarzamy pliki
            files_processed_in_folder = 0
            for entry in entries:
                if entry.is_file():
                    total_files_found += 1
                    files_processed_in_folder += 1

                    # EARLY STOPPING: Sprawdzenie co 10 plików w folderze
                    if (
                        files_processed_in_folder % 10 == 0
                        and interrupt_check
                        and interrupt_check()
                    ):
                        logger.warning(
                            f"Skanowanie przerwane po przetworzeniu {files_processed_in_folder} plików w {current_dir}"
                        )
                        raise ScanningInterrupted(
                            "Skanowanie przerwane podczas przetwarzania plików"
                        )

                    name = entry.name
                    base_name, ext = os.path.splitext(name)
                    ext_lower = ext.lower()

                    if (
                        ext_lower in ARCHIVE_EXTENSIONS
                        or ext_lower in PREVIEW_EXTENSIONS
                    ):
                        map_key = os.path.join(
                            normalize_path(current_dir), base_name.lower()
                        )
                        full_file_path = normalize_path(os.path.join(current_dir, name))
                        file_map[map_key].append(full_file_path)

            # Potem rekurencyjnie przetwarzamy podfoldery
            subfolders_processed = 0
            for entry in entries:
                if entry.is_dir():
                    subfolders_processed += 1

                    # EARLY STOPPING: Sprawdzenie co 5 podfolderów
                    if (
                        subfolders_processed % 5 == 0
                        and interrupt_check
                        and interrupt_check()
                    ):
                        logger.warning(
                            f"Skanowanie przerwane po przetworzeniu {subfolders_processed} podfolderów w {current_dir}"
                        )
                        raise ScanningInterrupted(
                            "Skanowanie przerwane podczas rekursywnego skanowania"
                        )

                    _walk_directory_streaming(entry.path, depth + 1)

        except (PermissionError, OSError) as e:
            logger.warning(f"Błąd dostępu do katalogu {current_dir}: {e}")
        except ScanningInterrupted:
            # Przepuszczamy wyjątek przerwania wyżej
            raise

    try:
        _walk_directory_streaming(normalized_dir)
    except ScanningInterrupted:
        raise

    elapsed_time = time.time() - start_time
    logger.info(
        f"Zakończono STREAMING zbieranie plików. Przeskanowano {total_folders_scanned} folderów, "
        f"znaleziono {total_files_found} plików w czasie {elapsed_time:.2f}s"
    )

    # Zapisujemy wynik do ujednoliconego cache
    result_dict = dict(file_map)
    from .scan_cache import unified_cache
    unified_cache.store_file_map(normalized_dir, result_dict)

    return result_dict
