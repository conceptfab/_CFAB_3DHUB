"""
Moduł odpowiedzialny za skanowanie folderów.

Ten moduł zawiera funkcje do skanowania katalogów w poszukiwaniu plików
oraz koordynowania procesu skanowania.
"""

import logging
import os
import time
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple

from src import app_config
from src.config import AppConfig
from src.logic.file_pairing import (
    ARCHIVE_EXTENSIONS,
    PREVIEW_EXTENSIONS,
    create_file_pairs,
    identify_unpaired_files,
)
from src.logic.metadata_manager import MetadataManager
from src.logic.scanner_cache import cache
from src.models.file_pair import FilePair
from src.models.special_folder import SpecialFolder
from src.utils.path_utils import normalize_path, path_exists

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Parametry cache z centralnego pliku konfiguracyjnego
MAX_CACHE_ENTRIES = app_config.SCANNER_MAX_CACHE_ENTRIES
MAX_CACHE_AGE_SECONDS = app_config.SCANNER_MAX_CACHE_AGE_SECONDS

# Foldery ignorowane podczas skanowania
IGNORED_FOLDERS = {
    ".app_metadata",
    "__pycache__",
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    ".alg_meta",
}


def should_ignore_folder(folder_name: str) -> bool:
    """
    Sprawdza czy folder powinien być ignorowany podczas skanowania.

    Args:
        folder_name: Nazwa folderu do sprawdzenia

    Returns:
        True jeśli folder powinien być ignorowany
    """
    return folder_name in IGNORED_FOLDERS or folder_name.startswith(".")


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
                "Skanowanie przerwane przez użytkownika podczas " "przetwarzania plików"
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
                f"Skanowanie: {os.path.basename(current_dir)} "
                f"({total_files_found} plików, {total_folders_scanned} folderów)",
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
                        msg = (
                            "Skanowanie przerwane podczas przetwarzania "
                            f"plików w {current_dir}"
                        )
                        logger.warning(msg)
                        raise ScanningInterrupted(msg)

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
                        # Ignoruj ukryte foldery i foldery systemowe
                        if should_ignore_folder(entry.name):
                            logger.debug(f"Pomijam ignorowany folder: {entry.name}")
                            continue

                        subfolders_processed += 1

                        # Sprawdzenie co 5 podfolderów
                        if (
                            subfolders_processed % 5 == 0
                            and interrupt_check
                            and interrupt_check()
                        ):
                            msg = (
                                "Skanowanie przerwane podczas rekursywnego "
                                f"skanowania w {current_dir}"
                            )
                            logger.warning(msg)
                            raise ScanningInterrupted(msg)

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
        f"Zakończono streaming zbieranie plików w {elapsed_time:.2f}s. Znaleziono {total_files_found} plików w {total_folders_scanned} folderach."
    )

    # Zapisz mapę plików w cache
    if not force_refresh:
        cache.set_file_map(normalized_dir, file_map)

    if progress_callback:
        progress_callback(100, "Zakończono zbieranie plików")

    return file_map


def scan_folder_for_pairs(
    directory: str,
    max_depth: int = -1,
    use_cache: bool = True,
    pair_strategy: str = "first_match",
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh_cache: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]]:
    """
    Skanuje folder, tworzy pary i identyfikuje nieparowane pliki.
    """
    normalized_dir = normalize_path(directory)

    # 1. Sprawdź cache dla pełnego wyniku skanowania
    if use_cache and not force_refresh_cache:
        cached_result = cache.get_scan_result(normalized_dir, pair_strategy)
        if cached_result:
            logger.debug(
                f"CACHE HIT: Zwracam pełny zbuforowany wynik dla {normalized_dir}"
            )
            if progress_callback:
                progress_callback(100, f"Używam cache dla {normalized_dir}")
            return cached_result

    # Jeśli katalog nie istnieje, zwróć puste listy
    if not path_exists(normalized_dir) or not os.path.isdir(normalized_dir):
        logger.warning(
            f"Katalog {normalized_dir} nie istnieje lub nie jest katalogiem. Zwracam pusty wynik."
        )
        return [], [], [], []

    # Definicja funkcji do skalowania postępu
    def scaled_progress(percent, message):
        if progress_callback:
            # Skaluj postęp z collect_files do zakresu 0-50%
            scaled_percent = int(percent * 0.5)
            progress_callback(scaled_percent, message)

    # 2. Zbierz wszystkie pliki (z użyciem cache dla mapy plików)
    file_map = collect_files_streaming(
        normalized_dir, max_depth, interrupt_check, force_refresh_cache, scaled_progress
    )

    # 3. Utwórz pary plików
    if progress_callback:
        progress_callback(55, "Tworzenie par plików...")
    file_pairs, processed_files = create_file_pairs(
        file_map,
        base_directory=normalized_dir,
        pair_strategy=pair_strategy,
    )

    # 4. Identyfikuj nieparowane pliki
    if progress_callback:
        progress_callback(80, "Identyfikacja nieparowanych plików...")

    # Zbierz wszystkie przetworzone pliki z par
    processed_files = set()
    for pair in file_pairs:
        processed_files.add(pair.get_archive_path())
        if pair.get_preview_path():
            processed_files.add(pair.get_preview_path())

    unpaired_archives, unpaired_previews = identify_unpaired_files(
        file_map, processed_files
    )

    # 5. Znajdź specjalne foldery (tex, textures) na dysku
    if progress_callback:
        progress_callback(95, "Szukanie folderów specjalnych...")
    special_folders = find_special_folders(normalized_dir)

    # 6. KRYTYCZNA NAPRAWKA: Sprawdź metadane i utwórz wirtualny folder
    metadata_manager = MetadataManager.get_instance(normalized_dir)
    metadata = metadata_manager.io.load_metadata_from_file()
    if metadata and metadata.get("has_special_folders"):
        # Jeśli metadane mówią, że są foldery, a skanowanie ich nie znalazło
        if not special_folders:
            logger.info(
                f"Metadane dla '{normalized_dir}' wskazują na istnienie folderów "
                f"specjalnych, ale nie znaleziono ich na dysku. "
                f"Tworzę folder wirtualny."
            )

            # Użyj nazwy z metadanych, jeśli jest dostępna
            special_folders_from_meta = metadata.get("special_folders")
            if special_folders_from_meta:
                virtual_folder_name = special_folders_from_meta[0]
                logger.debug(
                    f"Używam nazwy folderu wirtualnego z metadanych: "
                    f"'{virtual_folder_name}'"
                )
            else:
                # Fallback na starą logikę, jeśli w metadanych nie ma nazwy
                logger.warning(
                    f"Brak zdefiniowanych nazw folderów specjalnych w metadanych "
                    f"dla '{normalized_dir}'. Używam domyślnej nazwy z konfiguracji."
                )
                special_folders_config = AppConfig.get_instance().special_folders
                if special_folders_config:
                    virtual_folder_name = special_folders_config[0]
                else:
                    logger.error("Brak domyślnych folderów specjalnych w konfiguracji!")
                    virtual_folder_name = "special_folder"  # Ostateczny fallback

            virtual_folder_path = os.path.join(normalized_dir, virtual_folder_name)
            virtual_folder = SpecialFolder(
                folder_name=virtual_folder_name,
                folder_path=virtual_folder_path,
                is_virtual=True,
            )
            special_folders.append(virtual_folder)
            logger.info(f"Utworzono wirtualny folder: {virtual_folder_path}")

    # 7. Zapisz wynik w cache
    if use_cache:
        cache.set_scan_result(
            normalized_dir,
            pair_strategy,
            (file_pairs, unpaired_archives, unpaired_previews, special_folders),
        )

    logger.info(
        f"Skanowanie zakończone dla {normalized_dir}. Znaleziono {len(file_pairs)} par."
    )
    if progress_callback:
        progress_callback(100, f"Skanowanie zakończone: {len(file_pairs)} par")

    return file_pairs, unpaired_archives, unpaired_previews, special_folders


def get_scan_statistics() -> Dict[str, float]:
    """
    Zwraca statystyki dotyczące bieżącego stanu cache skanowania.

    Returns:
        Słownik zawierający statystyki
    """
    return cache.get_statistics()


def find_special_folders(folder_path: str) -> List[SpecialFolder]:
    """
    USUNIĘTA FUNKCJA - Foldery specjalne są teraz pobierane z metadanych.
    Ta funkcja pozostaje jako zaślepka dla kompatybilności wstecznej.

    Args:
        folder_path: Ścieżka do folderu

    Returns:
        Pusta lista specjalnych folderów
    """
    logger.debug("find_special_folders: Funkcja zastąpiona przez metadane")
    return []
