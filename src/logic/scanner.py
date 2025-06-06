"""
Moduł odpowiedzialny za skanowanie folderów i parowanie plików.

Ten moduł zawiera funkcje do skanowania katalogów w poszukiwaniu plików
oraz ich łączenia w pary (archiwa + podglądy).
"""

import logging
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from src import app_config  # Importujemy moduł konfiguracji
from src.models.file_pair import FilePair
from src.utils.path_utils import is_path_valid, normalize_path, path_exists

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Używamy definicji rozszerzeń z centralnego pliku konfiguracyjnego
ARCHIVE_EXTENSIONS = set(app_config.SUPPORTED_ARCHIVE_EXTENSIONS)
PREVIEW_EXTENSIONS = set(app_config.SUPPORTED_PREVIEW_EXTENSIONS)

MAX_CACHE_ENTRIES = 100  # Konfigurowalne
MAX_CACHE_AGE_SECONDS = 3600  # 1 godzina

# Cache dla wyników skanowania, klucz: ścieżka katalogu, wartość: wynik skanowania
_scan_cache: Dict[str, Tuple[List[FilePair], List[str], List[str]]] = {}
# Cache dla listy plików, klucz: ścieżka katalogu, wartość: (czas_modyfikacji, lista_plików)
_files_cache: Dict[str, Tuple[float, Dict[str, List[str]]]] = {}


class ScanningInterrupted(Exception):
    """Wyjątek rzucany, gdy skanowanie zostało przerwane przez użytkownika."""

    pass


def _cleanup_old_cache_entries():
    """Usuwa stare wpisy z _files_cache na podstawie wieku i liczby."""
    current_time = time.time()
    to_remove_by_age = []

    # Usuwanie na podstawie wieku
    for key, (timestamp, _) in list(
        _files_cache.items()
    ):  # Iteracja po kopii dla bezpiecznego usuwania
        if current_time - timestamp > MAX_CACHE_AGE_SECONDS:
            to_remove_by_age.append(key)

    for key in to_remove_by_age:
        if key in _files_cache:  # Sprawdź czy klucz nadal istnieje
            del _files_cache[key]
            logger.debug(f"Usunięto stary wpis z _files_cache (wiek): {key}")

    # Usuwanie na podstawie liczby, jeśli nadal za dużo wpisów
    if len(_files_cache) > MAX_CACHE_ENTRIES:
        # Sortuj od najstarszego do najnowszego
        sorted_items = sorted(list(_files_cache.items()), key=lambda x: x[1][0])
        num_to_remove = len(_files_cache) - MAX_CACHE_ENTRIES

        for key, _ in sorted_items[:num_to_remove]:
            if key in _files_cache:  # Sprawdź czy klucz nadal istnieje
                del _files_cache[key]
                logger.debug(f"Usunięto stary wpis z _files_cache (liczba): {key}")


def clear_cache() -> None:
    """
    Czyści bufor wyników skanowania.
    Użyteczne gdy użytkownik chce wymusić ponowne skanowanie.
    """
    global _scan_cache, _files_cache
    _scan_cache.clear()
    _files_cache.clear()
    logger.info("Wyczyszczono bufor wyników skanowania")


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

    max_mtime = os.path.getmtime(directory)

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
    except (PermissionError, OSError) as e:
        logger.warning(f"Nie można odczytać zawartości katalogu {directory}: {e}")

    return max_mtime


def is_cache_valid(directory: str) -> bool:
    """
    Sprawdza, czy bufor dla danego katalogu jest aktualny.

    Args:
        directory: Ścieżka do katalogu

    Returns:
        True jeśli bufor jest aktualny, False w przeciwnym razie
    """
    normalized_dir = normalize_path(directory)

    # Jeśli nie ma w buforze, to nie jest aktualny
    if normalized_dir not in _files_cache:
        return False

    # Pobieramy czas ostatniej modyfikacji katalogu
    current_mtime = get_directory_modification_time(normalized_dir)
    cached_mtime, _ = _files_cache[normalized_dir]

    # Jeśli czas modyfikacji jest nowszy niż czas z bufora, bufor jest nieaktualny
    return current_mtime <= cached_mtime


def collect_files(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,  # Dodany parametr
) -> Dict[str, List[str]]:
    """
    Zbiera wszystkie pliki w katalogu zgodnie z obsługiwanymi rozszerzeniami.

    Args:
        directory: Ścieżka do katalogu do przeskanowania
        max_depth: Maksymalna głębokość rekursji, -1 oznacza brak limitu
        interrupt_check: Opcjonalna funkcja sprawdzająca czy przerwać skanowanie
        force_refresh: Czy wymusić odświeżenie cache (ignoruje is_cache_valid)

    Returns:
        Słownik zmapowanych plików, gdzie kluczem jest nazwa bazowa (bez rozszerzenia),
        a wartością lista pełnych ścieżek do plików.

    Raises:
        ScanningInterrupted: Jeśli skanowanie zostało przerwane
    """
    normalized_dir = normalize_path(directory)

    # Sprawdź czy mamy w buforze
    if not force_refresh and normalized_dir in _files_cache:  # Zmodyfikowany warunek
        if is_cache_valid(normalized_dir):  # Użycie is_cache_valid
            logger.debug(
                f"Cache jest aktualny dla {normalized_dir}, używam buforowanych plików"
            )
            _, file_map = _files_cache[normalized_dir]
            return file_map
        else:
            logger.debug(f"Cache nieaktualny dla {normalized_dir}, usuwam wpis.")
            del _files_cache[normalized_dir]  # Usuń nieaktualny wpis

    # Jeśli katalog nie istnieje lub nie jest katalogiem, zwróć pusty słownik
    if not path_exists(normalized_dir) or not os.path.isdir(normalized_dir):
        logger.warning(f"Katalog {normalized_dir} nie istnieje lub nie jest katalogiem")
        return {}

    logger.info(f"Rozpoczęto zbieranie plików z katalogu: {normalized_dir}")
    file_map = defaultdict(list)
    total_folders_scanned = 0
    total_files_found = 0
    start_time = time.time()

    # Zestaw odwiedzonych katalogów (do obsługi pętli symbolicznych)
    visited_dirs = set()

    def _walk_directory(current_dir: str, depth: int = 0):
        nonlocal total_folders_scanned, total_files_found

        # Sprawdzenie czy należy przerwać skanowanie
        if interrupt_check and interrupt_check():
            logger.warning("Skanowanie przerwane przez użytkownika")
            raise ScanningInterrupted("Skanowanie przerwane przez użytkownika")

        # Obsługa limitu głębokości
        if max_depth >= 0 and depth > max_depth:
            return

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

            # Najpierw przetwarzamy pliki
            for entry in entries:
                if entry.is_file():
                    total_files_found += 1
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
            for entry in entries:
                if entry.is_dir():
                    _walk_directory(entry.path, depth + 1)

        except (PermissionError, OSError) as e:
            logger.warning(f"Błąd dostępu do katalogu {current_dir}: {e}")

    try:
        _walk_directory(normalized_dir)
    except ScanningInterrupted:
        raise

    elapsed_time = time.time() - start_time
    logger.info(
        f"Zakończono zbieranie plików. Przeskanowano {total_folders_scanned} folderów, "
        f"znaleziono {total_files_found} plików w czasie {elapsed_time:.2f}s"
    )

    # Zapisujemy wynik do bufora
    _files_cache[normalized_dir] = (time.time(), dict(file_map))
    _cleanup_old_cache_entries()  # Wywołanie funkcji czyszczącej po dodaniu nowego wpisu

    return dict(file_map)


def create_file_pairs(
    file_map: Dict[str, List[str]],
    base_directory: str,
    # pair_all: bool = True, # Usunięty parametr
    pair_strategy: str = "first_match",  # Dodany parametr: "first_match", "all_combinations", "best_match"
) -> Tuple[List[FilePair], Set[str]]:
    """
    Tworzy pary plików na podstawie zebranych danych.

    Args:
        file_map: Słownik zmapowanych plików
        base_directory: Katalog bazowy dla względnych ścieżek w FilePair
        pair_strategy: Strategia parowania plików.
                         "first_match": tylko pierwsza znaleziona para.
                         "all_combinations": wszystkie możliwe kombinacje archiwum-podgląd.
                         "best_match": inteligentne parowanie po nazwach (TODO: implementacja).

    Returns:
        Krotka zawierająca listę utworzonych par oraz zbiór przetworzonych plików
    """
    found_pairs: List[FilePair] = []
    processed_files: Set[str] = set()

    for base_path, files_list in file_map.items():
        # Pre-compute rozszerzeń dla optymalizacji
        files_with_ext = [(f, os.path.splitext(f)[1].lower()) for f in files_list]

        archive_files = [f for f, ext in files_with_ext if ext in ARCHIVE_EXTENSIONS]
        preview_files = [f for f, ext in files_with_ext if ext in PREVIEW_EXTENSIONS]

        if not archive_files or not preview_files:
            continue

        if pair_strategy == "first_match":
            # Tylko pierwsza para (odpowiednik pair_all=False)
            try:
                pair = FilePair(archive_files[0], preview_files[0], base_directory)
                found_pairs.append(pair)
                processed_files.add(archive_files[0])
                processed_files.add(preview_files[0])
            except ValueError as e:
                logger.error(
                    f"Błąd tworzenia FilePair dla '{archive_files[0]}' i '{preview_files[0]}': {e}"
                )

        elif pair_strategy == "all_combinations":
            # Wszystkie kombinacje (odpowiednik pair_all=True)
            for archive in archive_files:
                for preview in preview_files:
                    try:
                        pair = FilePair(archive, preview, base_directory)
                        found_pairs.append(pair)
                        processed_files.add(archive)
                        processed_files.add(preview)
                    except ValueError as e:
                        logger.error(
                            f"Błąd tworzenia FilePair dla '{archive}' i '{preview}': {e}"
                        )
        elif pair_strategy == "best_match":
            # TODO: Implementacja inteligentnego parowania po nazwach
            # Na razie działa jak "first_match"
            logger.warning(
                "Strategia 'best_match' nie jest jeszcze w pełni zaimplementowana, używam 'first_match'."
            )
            if archive_files and preview_files:
                try:
                    pair = FilePair(archive_files[0], preview_files[0], base_directory)
                    found_pairs.append(pair)
                    processed_files.add(archive_files[0])
                    processed_files.add(preview_files[0])
                except ValueError as e:
                    logger.error(
                        f"Błąd tworzenia FilePair dla '{archive_files[0]}' i '{preview_files[0]}': {e}"
                    )
        else:
            logger.error(f"Nieznana strategia parowania: {pair_strategy}")

    return found_pairs, processed_files


def identify_unpaired_files(
    file_map: Dict[str, List[str]],
    processed_files: Set[str],
) -> Tuple[List[str], List[str]]:
    """
    Identyfikuje niesparowane pliki na podstawie zebranych danych.

    Args:
        file_map: Słownik zmapowanych plików
        processed_files: Zbiór już przetworzonych (sparowanych) plików

    Returns:
        Krotka zawierająca listy niesparowanych archiwów i podglądów
    """
    unpaired_archives: List[str] = []
    unpaired_previews: List[str] = []

    # Zbieramy wszystkie pliki z mapy
    all_files = {file for files_list in file_map.values() for file in files_list}

    # Identyfikujemy niesparowane pliki
    unpaired_files = all_files - processed_files
    for f in unpaired_files:
        if os.path.splitext(f)[1].lower() in ARCHIVE_EXTENSIONS:
            unpaired_archives.append(f)
        elif os.path.splitext(f)[1].lower() in PREVIEW_EXTENSIONS:
            unpaired_previews.append(f)

    return unpaired_archives, unpaired_previews


def scan_folder_for_pairs(
    directory: str,
    max_depth: int = -1,
    use_cache: bool = True,
    # pair_all: bool = True, # Usunięty parametr
    pair_strategy: str = "first_match",  # Dodany parametr
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh_cache: bool = False,  # Dodany parametr
) -> Tuple[List[FilePair], List[str], List[str]]:
    """
    Skanuje podany katalog i jego podkatalogi w poszukiwaniu par plików.

    Args:
        directory: Ścieżka do katalogu do przeskanowania
        max_depth: Maksymalna głębokość rekursji, -1 oznacza brak limitu
        use_cache: Czy używać buforowanych wyników jeśli są dostępne
        pair_strategy: Strategia parowania plików (zastępuje pair_all)
        interrupt_check: Opcjonalna funkcja sprawdzająca czy przerwać skanowanie
        force_refresh_cache: Czy wymusić odświeżenie cache plików (przekazywane do collect_files)

    Returns:
        Krotka zawierająca listę znalezionych par, listę niesparowanych archiwów
        i listę niesparowanych podglądów.

    Raises:
        ScanningInterrupted: Jeśli skanowanie zostało przerwane
    """
    normalized_dir = normalize_path(directory)

    if not path_exists(normalized_dir):
        logger.error(f"Katalog {normalized_dir} nie istnieje")
        return [], [], []

    cache_key = (
        f"{normalized_dir}_{max_depth}_{pair_strategy}"  # Zaktualizowany klucz cache
    )
    if use_cache and not force_refresh_cache and cache_key in _scan_cache:
        # Dodatkowe sprawdzenie force_refresh_cache dla _scan_cache
        # Jeśli force_refresh_cache jest True, chcemy odświeżyć _files_cache,
        # a to może wpłynąć na wynik _scan_cache, więc też go odświeżamy.
        logger.info(
            f"CACHE HIT: Używam buforowanych wyników dla {normalized_dir} ze strategią {pair_strategy}"
        )
        return _scan_cache[cache_key]

    logger.info(
        f"Rozpoczęto skanowanie katalogu: {normalized_dir} ze strategią {pair_strategy}"
    )
    start_time = time.time()

    try:
        # Krok 1: Zbieranie wszystkich plików
        file_map = collect_files(
            normalized_dir,
            max_depth,
            interrupt_check,
            force_refresh=force_refresh_cache,
        )

        # Krok 2: Tworzenie par plików
        found_pairs, processed_files = create_file_pairs(
            file_map,
            normalized_dir,
            pair_strategy=pair_strategy,  # Użycie nowej strategii
        )

        # Krok 3: Identyfikacja niesparowanych plików
        unpaired_archives, unpaired_previews = identify_unpaired_files(
            file_map, processed_files
        )

    except ScanningInterrupted:
        # W przypadku przerwania zwracamy częściowe wyniki, ale nie buforujemy ich
        logger.warning("Zwracam częściowe wyniki z powodu przerwania skanowania")
        raise

    elapsed_time = time.time() - start_time
    logger.info(
        f"Zakończono skanowanie '{normalized_dir}' w czasie {elapsed_time:.2f}s. "
        f"Znaleziono {len(found_pairs)} par, {len(unpaired_archives)} niesparowanych "
        f"archiwów i {len(unpaired_previews)} niesparowanych podglądów."
    )

    # Zapisujemy wynik do bufora
    result = (found_pairs, unpaired_archives, unpaired_previews)
    _scan_cache[cache_key] = result

    return result


def get_scan_statistics() -> Dict[str, int]:
    """
    Zwraca statystyki dotyczące bieżącego stanu bufora skanowania.

    Returns:
        Słownik zawierający statystyki
    """
    return {
        "scan_cache_entries": len(_scan_cache),
        "files_cache_entries": len(_files_cache),
    }


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
