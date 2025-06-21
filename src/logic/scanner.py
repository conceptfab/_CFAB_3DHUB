"""
Moduł odpowiedzialny za skanowanie folderów i parowanie plików.

Ten moduł zawiera publiczne API do skanowania katalogów w poszukiwaniu plików
oraz ich łączenia w pary (archiwa + podglądy).

UWAGA: Ten moduł jest fasadą publicznego API. Implementacja podzielona na:
- scanner_core.py - podstawowe funkcje skanowania
- scanner_cache.py - zarządzanie cache
- file_pairing.py - logika parowania plików
"""

import logging
from functools import wraps
from typing import Callable, Dict, List, Optional, Set, Tuple

from src.logic.file_pairing import ARCHIVE_EXTENSIONS, PREVIEW_EXTENSIONS
from src.logic.file_pairing import create_file_pairs as _create_file_pairs
from src.logic.file_pairing import identify_unpaired_files as _identify_unpaired_files
from src.logic.scanner_cache import clear_cache as _clear_cache
from src.logic.scanner_core import ScanningInterrupted
from src.logic.scanner_core import collect_files_streaming as _collect_files_streaming
from src.logic.scanner_core import get_scan_statistics as _get_scan_statistics
from src.logic.scanner_core import scan_folder_for_pairs as _scan_folder_for_pairs
from src.models.file_pair import FilePair

__all__ = [
    "collect_files_streaming",
    "collect_files",
    "create_file_pairs",
    "identify_unpaired_files",
    "scan_folder_for_pairs",
    "clear_cache",
    "get_scan_statistics",
    "ARCHIVE_EXTENSIONS",
    "PREVIEW_EXTENSIONS",
    "ScanningInterrupted",
]

logger = logging.getLogger(__name__)


def _log_scanner_operation(operation_name: str):
    """Dekorator do logowania operacji skanera."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug(f"Wywołanie {operation_name}: {func.__name__}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Zakończono {operation_name}: {func.__name__}")
                return result
            except Exception as e:
                logger.error(f"Błąd w {operation_name}: {e}")
                raise

        return wrapper

    return decorator


@_log_scanner_operation("skanowanie plików")
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
        max_depth: Maksymalna głębokość skanowania (-1 = bez limitu)
        interrupt_check: Funkcja sprawdzająca czy przerwać skanowanie
        force_refresh: Czy wymusić odświeżenie cache
        progress_callback: Callback dla raportowania postępu

    Returns:
        Dict[str, List[str]]: Mapa rozszerzeń na listy plików

    Raises:
        ScanningInterrupted: Gdy skanowanie zostało przerwane
        OSError: Problemy z dostępem do systemu plików
    """
    return _collect_files_streaming(
        directory=directory,
        max_depth=max_depth,
        interrupt_check=interrupt_check,
        force_refresh=force_refresh,
        progress_callback=progress_callback,
    )


# Alias dla kompatybilności wstecznej - NIE UŻYWAĆ w nowym kodzie
collect_files = collect_files_streaming


@_log_scanner_operation("tworzenie par plików")
def create_file_pairs(
    file_map: Dict[str, List[str]],
    base_directory: str,
    pair_strategy: str = "first_match",
) -> Tuple[List[FilePair], Set[str]]:
    """
    Tworzy pary plików na podstawie zebranych danych.

    Args:
        file_map: Mapa rozszerzeń na listy plików
        base_directory: Bazowy katalog dla par
        pair_strategy: Strategia parowania ("first_match", "best_match")

    Returns:
        Tuple[List[FilePair], Set[str]]: Pary plików i zestaw przetworzonych plików

    Raises:
        ValueError: Nieprawidłowa strategia parowania
    """
    return _create_file_pairs(
        file_map=file_map,
        base_directory=base_directory,
        pair_strategy=pair_strategy,
    )


@_log_scanner_operation("identyfikacja niesparowanych plików")
def identify_unpaired_files(
    file_map: Dict[str, List[str]],
    processed_files: Set[str],
) -> Tuple[List[str], List[str]]:
    """
    Identyfikuje niesparowane pliki.

    Args:
        file_map: Mapa rozszerzeń na listy plików
        processed_files: Zestaw już przetworzonych plików

    Returns:
        Tuple[List[str], List[str]]: Niesparowane archiwa i podglądy
    """
    return _identify_unpaired_files(file_map, processed_files)


@_log_scanner_operation("pełne skanowanie z parowaniem")
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
        max_depth: Maksymalna głębokość skanowania
        use_cache: Czy używać cache
        pair_strategy: Strategia parowania plików
        interrupt_check: Funkcja sprawdzająca przerwanie
        force_refresh_cache: Czy wymusić odświeżenie cache
        progress_callback: Callback postępu

    Returns:
        Tuple: Pary, niesparowane archiwa, niesparowane podglądy

    Raises:
        ScanningInterrupted: Gdy skanowanie zostało przerwane
        OSError: Problemy z dostępem do systemu plików
    """
    return _scan_folder_for_pairs(
        directory=directory,
        max_depth=max_depth,
        use_cache=use_cache,
        pair_strategy=pair_strategy,
        interrupt_check=interrupt_check,
        force_refresh_cache=force_refresh_cache,
        progress_callback=progress_callback,
    )


def clear_cache() -> None:
    """
    Czyści bufor wyników skanowania.
    """
    _clear_cache()
    logger.info("Wyczyszczono bufor wyników skanowania")


@_log_scanner_operation("pobieranie statystyk")
def get_scan_statistics() -> Dict[str, float]:
    """
    Zwraca statystyki dotyczące bieżącego stanu cache.
    """
    return _get_scan_statistics()
