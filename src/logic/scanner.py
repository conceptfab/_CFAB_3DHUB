"""
Moduł odpowiedzialny za skanowanie folderów i parowanie plików.

Ten moduł zawiera funkcje do skanowania katalogów w poszukiwaniu plików
oraz ich łączenia w pary (archiwa + podglądy).

UWAGA: Ten moduł jest fasadą publicznego API. Implementacja podzielona na:
- scanner_core.py - podstawowe funkcje skanowania
- scanner_cache.py - zarządzanie cache
- file_pairing.py - logika parowania plików
"""

import functools
import inspect
import logging
from typing import Callable, Dict, List, Optional, Set, Tuple

# Importujemy tylko klasy i stałe, nie importujemy funkcji na poziomie modułu
from src.logic.file_pairing import ARCHIVE_EXTENSIONS, PREVIEW_EXTENSIONS
from src.logic.scanner_core import ScanningInterrupted
from src.models.file_pair import FilePair

# Konfiguracja loggera
logger = logging.getLogger(__name__)


# Funkcja pomocnicza do przekazywania argumentów "tak jak są" do funkcji delegowanej
def _pass_through_args(target_function, *args, **kwargs):
    """
    Pomocnicza funkcja wewnętrzna przekazująca argumenty do funkcji docelowej.
    Używana, aby upewnić się, że dokładnie te same obiekty są przekazywane dalej.
    """
    return target_function(*args, **kwargs)


def collect_files(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, List[str]]:
    """
    DEPRECATED: Ta funkcja jest przestarzała, użyj collect_files_streaming zamiast niej.
    Deleguje do collect_files_streaming dla zachowania kompatybilności wstecznej.

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
    logger.warning(
        "Funkcja collect_files jest przestarzała. Użyj collect_files_streaming."
    )
    return collect_files_streaming(
        directory=directory,
        max_depth=max_depth,
        interrupt_check=interrupt_check,
        force_refresh=force_refresh,
        progress_callback=progress_callback,
    )


def collect_files_streaming(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, List[str]]:
    """
    Zbiera wszystkie pliki w katalogu z streaming progress.
    Deleguje do funkcji w scanner_core.

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
    from src.logic.scanner_core import collect_files_streaming as core_func

    # Przekazujemy dokładnie te same obiekty dalej
    return core_func(
        directory=directory,
        max_depth=max_depth,
        interrupt_check=interrupt_check,
        force_refresh=force_refresh,
        progress_callback=progress_callback,
    )


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
    Deleguje do funkcji w scanner_core.

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
    from src.logic.scanner_core import scan_folder_for_pairs as core_func

    # Przekazujemy dokładnie te same obiekty dalej
    return core_func(
        directory=directory,
        max_depth=max_depth,
        use_cache=use_cache,
        pair_strategy=pair_strategy,
        interrupt_check=interrupt_check,
        force_refresh_cache=force_refresh_cache,
        progress_callback=progress_callback,
    )


def create_file_pairs(
    file_map: Dict[str, List[str]],
    base_directory: str,
    pair_strategy: str = "best_match",
) -> Tuple[List[FilePair], Set[str]]:
    """
    Tworzy pary plików z listy plików zgrupowanych po nazwie bazowej.
    Deleguje do funkcji w file_pairing.

    Args:
        file_map: Słownik z listą plików grupowanych po nazwie bazowej
        base_directory: Katalog bazowy dla ścieżek względnych
        pair_strategy: Strategia parowania plików (best_match, first_match)

    Returns:
        Krotka zawierająca listę par plików oraz zbiór przetworzonych plików
    """
    from src.logic.file_pairing import create_file_pairs as core_func

    # Przekazujemy dokładnie te same obiekty dalej
    return core_func(
        file_map=file_map, base_directory=base_directory, pair_strategy=pair_strategy
    )


def identify_unpaired_files(
    file_map: Dict[str, List[str]],
    processed_files: Set[str],
) -> Tuple[List[str], List[str]]:
    """
    Identyfikuje pliki, które nie zostały sparowane.
    Deleguje do funkcji w file_pairing.

    Args:
        file_map: Słownik zawierający znalezione pliki
        processed_files: Zbiór ścieżek plików, które zostały już przetworzone

    Returns:
        Krotka zawierająca listę niesparowanych plików archiwalnych i podglądowych
    """
    from src.logic.file_pairing import identify_unpaired_files as core_func

    # Przekazujemy dokładnie te same obiekty dalej
    return core_func(file_map, processed_files)


def get_scan_statistics() -> Dict[str, float]:
    """
    Zwraca statystyki skanowania.
    Deleguje do funkcji w scanner_core.

    Returns:
        Słownik ze statystykami
    """
    from src.logic.scanner_core import get_scan_statistics as core_func

    # Wywołanie funkcji bez argumentów
    return core_func()


def clear_cache() -> None:
    """
    Czyści pamięć podręczną dla wyników skanowania.
    Deleguje do funkcji w scanner_cache.
    """
    from src.logic.scanner_cache import clear_cache as core_func

    # Wywołanie funkcji bez argumentów
    core_func()
