"""
Moduł główny skanowania folderów i parowania plików.

Ten moduł służy jako koordynator między modułami:
- scanner_core: podstawowe funkcje skanowania
- file_pairing: algorytmy parowania plików  
- scan_cache: zarządzanie cache
"""

import logging
import time
from typing import Callable, Dict, List, Optional, Tuple

from src.models.file_pair import FilePair
from src.utils.path_utils import normalize_path, path_exists

from .file_pairing import create_file_pairs, identify_unpaired_files
from .scan_cache import clear_cache, get_scan_statistics, unified_cache
from .scanner_core import ScanningInterrupted, collect_files_streaming

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Re-eksportujemy główne funkcje dla kompatybilności wstecznej
__all__ = [
    'scan_folder_for_pairs',
    'collect_files_streaming', 
    'clear_cache',
    'get_scan_statistics',
    'ScanningInterrupted'
]


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

    ZOPTYMALIZOWANE: Używa ujednoliconego cache i streaming skanowania.

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

    # Sprawdź ujednolicony cache
    if use_cache and not force_refresh_cache:
        cached_result = unified_cache.get_scan_result(normalized_dir, pair_strategy)
        if cached_result is not None:
            logger.info(
                f"CACHE HIT (unified): Używam buforowanych wyników dla {normalized_dir} ze strategią {pair_strategy}"
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
        # Krok 1: Zbieranie wszystkich plików (80% całego procesu) - używa streaming
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

        # Krok 2: Tworzenie par plików (używa zoptymalizowanego algorytmu best_match)
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

    # Zapisujemy wynik do ujednoliconego cache
    result = (found_pairs, unpaired_archives, unpaired_previews)
    unified_cache.store_scan_result(
        normalized_dir, pair_strategy, result
    )

    return result


if __name__ == "__main__":
    # Ten blok jest przeznaczony do prostych testów manualnych.
    # Aby go użyć, dostosuj ścieżkę `test_dir` i uruchom moduł bezpośrednio.

    # Konfiguracja logowania dla testów
    logging.basicConfig(level=logging.DEBUG)

    # test_dir = "C:/przykładowy/katalog/testowy"
    # print(f"Testowanie skanowania katalogu: {test_dir}")
    # pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(test_dir)
    # print(f"Znaleziono {len(pairs)} par")
    # print(f"Niesparowane archiwa: {len(unpaired_archives)}")
    # print(f"Niesparowane podglądy: {len(unpaired_previews)}")

    print("Uruchom test_scanner.py aby przetestować moduł skanera.")
