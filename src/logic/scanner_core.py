"""
Moduł odpowiedzialny za skanowanie folderów.

Ten moduł zawiera funkcje do skanowania katalogów w poszukiwaniu plików
oraz koordynowania procesu skanowania.
"""

import logging
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from src import app_config
from src.logic.file_pairing import (
    ARCHIVE_EXTENSIONS,
    PREVIEW_EXTENSIONS,
    create_file_pairs,
    identify_unpaired_files,
)
from src.logic.scanner_cache import cache, get_directory_modification_time
from src.models.file_pair import FilePair
from src.utils.path_utils import normalize_path, path_exists

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Parametry cache z centralnego pliku konfiguracyjnego
MAX_CACHE_ENTRIES = app_config.SCANNER_MAX_CACHE_ENTRIES
MAX_CACHE_AGE_SECONDS = app_config.SCANNER_MAX_CACHE_AGE_SECONDS


class ScanningInterrupted(Exception):
    """Wyjątek rzucany, gdy skanowanie zostało przerwane przez użytkownika."""

    pass


def collect_files_streaming(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, List[str]]:
    """
    Zbiera wszystkie pliki w katalogu z streaming progress.

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

    # Sprawdź cache
    if not force_refresh:
        cached_file_map = cache.get_file_map(normalized_dir)
        if cached_file_map is not None:
            logger.debug(f"CACHE HIT: używam buforowanych plików dla {normalized_dir}")
            if progress_callback:
                progress_callback(100, f"Używam cache dla {normalized_dir}")
            return cached_file_map

    # Jeśli katalog nie istnieje lub nie jest katalogiem, zwróć pusty słownik
    if not path_exists(normalized_dir) or not os.path.isdir(normalized_dir):
        logger.warning(f"Katalog {normalized_dir} nie istnieje lub nie jest katalogiem")
        if progress_callback:
            progress_callback(100, f"Katalog {normalized_dir} nie istnieje")
        return {}

    logger.info(f"Rozpoczęto streaming zbieranie plików z katalogu: {normalized_dir}")
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

        # Sprawdzenie czy należy przerwać skanowanie
        if interrupt_check and interrupt_check():
            logger.warning("Skanowanie przerwane przez użytkownika")
            raise ScanningInterrupted("Skanowanie przerwane przez użytkownika")

        # Sprawdzanie co każde 50 plików dla responsywności
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

            # Sprawdzenie przerwania po liście folderów
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

                    # Sprawdzenie co 10 plików w folderze
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

            should_scan_subfolders = files_processed_in_folder > 0

            logger.debug(
                f"Skanowanie: {current_dir} -> {files_processed_in_folder} plików"
            )

            if should_scan_subfolders:
                subfolders_processed = 0
                for entry in entries:
                    if entry.is_dir():
                        subfolders_processed += 1

                        # Sprawdzenie co 5 podfolderów
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

                        # Normalny rekursywny skan (tylko gdy folder ma pliki)
                        _walk_directory_streaming(entry.path, depth + 1)
            else:
                logger.debug(f"Pomijam podfoldery: {current_dir} (brak plików)")

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
        f"Zakończono streaming zbieranie plików. Przeskanowano {total_folders_scanned} folderów, "
        f"znaleziono {total_files_found} plików w czasie {elapsed_time:.2f}s"
    )

    # Zapisujemy wynik do cache
    result_dict = dict(file_map)
    cache.store_file_map(normalized_dir, result_dict)

    return result_dict


def scan_folder_for_pairs(
    directory: str,
    max_depth: int = -1,
    use_cache: bool = True,
    pair_strategy: str = "first_match",
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh_cache: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Tuple[List[FilePair], List[str], List[str]]:
    """
    Skanuje podany katalog i jego podkatalogi w poszukiwaniu par plików.

    Args:
        directory: Ścieżka do katalogu do przeskanowania
        max_depth: Maksymalna głębokość rekursji, -1 oznacza brak limitu
        use_cache: Czy używać buforowanych wyników jeśli są dostępne
        pair_strategy: Strategia parowania plików
        interrupt_check: Opcjonalna funkcja sprawdzająca czy przerwać skanowanie
        force_refresh_cache: Czy wymusić odświeżenie cache plików
        progress_callback: Opcjonalna funkcja do raportowania postępu (procent, wiadomość)

    Returns:
        Krotka zawierająca listę znalezionych par, listę niesparowanych archiwów
        i listę niesparowanych podglądów.

    Raises:
        ScanningInterrupted: Jeśli skanowanie zostało przerwane
    """
    normalized_dir = normalize_path(directory)

    if not path_exists(normalized_dir):
        logger.error(f"Katalog {normalized_dir} nie istnieje")
        if progress_callback:
            progress_callback(100, f"Błąd: Katalog {normalized_dir} nie istnieje")
        return [], [], []

    # Sprawdź cache
    if use_cache and not force_refresh_cache:
        cached_result = cache.get_scan_result(normalized_dir, pair_strategy)
        if cached_result is not None:
            logger.info(
                f"CACHE HIT: Używam buforowanych wyników dla {normalized_dir} ze strategią {pair_strategy}"
            )
            if progress_callback:
                progress_callback(
                    100, f"Używam buforowanych wyników dla {normalized_dir}"
                )
            return cached_result

    logger.info(
        f"Rozpoczęto skanowanie katalogu: {normalized_dir} ze strategią {pair_strategy}"
    )
    if progress_callback:
        progress_callback(0, f"Rozpoczynam skanowanie: {normalized_dir}")

    scan_start_time = time.time()

    try:
        # Krok 1: Zbieranie wszystkich plików (80% całego procesu)
        if progress_callback:
            # Tworzymy wrapper do callback'a, aby skalować postęp z collect_files (0-80%)
            def scaled_progress(percent, message):
                scaled = int(percent * 0.8)  # collect_files to 80% całego procesu
                progress_callback(scaled, message)

            file_map = collect_files_streaming(
                normalized_dir,
                max_depth,
                interrupt_check,
                force_refresh=force_refresh_cache,
                progress_callback=scaled_progress,
            )
        else:
            file_map = collect_files_streaming(
                normalized_dir,
                max_depth,
                interrupt_check,
                force_refresh=force_refresh_cache,
            )

        if progress_callback:
            progress_callback(85, f"Tworzenie par plików...")

        # Krok 2: Tworzenie par plików
        found_pairs, processed_files = create_file_pairs(
            file_map,
            normalized_dir,
            pair_strategy=pair_strategy,
        )

        if progress_callback:
            progress_callback(90, f"Identyfikacja niesparowanych plików...")

        # Krok 3: Identyfikacja niesparowanych plików
        unpaired_archives, unpaired_previews = identify_unpaired_files(
            file_map, processed_files
        )

    except ScanningInterrupted:
        # W przypadku przerwania zwracamy częściowe wyniki, ale nie buforujemy ich
        logger.warning("Zwracam częściowe wyniki z powodu przerwania skanowania")
        if progress_callback:
            progress_callback(100, "Skanowanie przerwane przez użytkownika")
        raise

    scan_duration = time.time() - scan_start_time
    result_message = (
        f"Zakończono skanowanie '{normalized_dir}' w czasie {scan_duration:.2f}s. "
        f"Znaleziono {len(found_pairs)} par, {len(unpaired_archives)} niesparowanych "
        f"archiwów i {len(unpaired_previews)} niesparowanych podglądów."
    )
    logger.info(result_message)

    if progress_callback:
        progress_callback(100, f"Zakończono: {len(found_pairs)} par")

    # Zapisujemy wynik do cache
    result = (found_pairs, unpaired_archives, unpaired_previews)
    cache.store_scan_result(normalized_dir, pair_strategy, result)

    return result


def get_scan_statistics() -> Dict[str, float]:
    """
    Zwraca statystyki dotyczące bieżącego stanu cache skanowania.

    Returns:
        Słownik zawierający statystyki
    """
    return cache.get_statistics()
