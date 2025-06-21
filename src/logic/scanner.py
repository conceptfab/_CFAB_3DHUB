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
import os
import threading
import warnings
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

# Thread safety dla dekoratora logowania
_log_lock = threading.RLock()


def _validate_directory(directory: str) -> None:
    """Waliduje ścieżkę katalogu."""
    if not directory:
        raise ValueError("Ścieżka katalogu nie może być pusta")
    if not os.path.exists(directory):
        raise FileNotFoundError(f"Katalog nie istnieje: {directory}")
    if not os.path.isdir(directory):
        raise NotADirectoryError(f"Ścieżka nie jest katalogiem: {directory}")


def _validate_max_depth(max_depth: int) -> None:
    """Waliduje parametr max_depth."""
    if not isinstance(max_depth, int):
        raise TypeError("max_depth musi być liczbą całkowitą")
    if max_depth < -1:
        raise ValueError("max_depth musi być >= -1")


def _validate_callback(callback: Optional[Callable], name: str) -> None:
    """Waliduje callback pod kątem thread safety."""
    if callback is not None and not callable(callback):
        raise TypeError(f"{name} musi być callable lub None")


def _log_scanner_operation(operation_name: str):
    """Dekorator do logowania operacji skanera z thread safety."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Thread-safe logowanie
            with _log_lock:
                logger.debug(f"Rozpoczęto {operation_name}: {func.__name__}")

            try:
                result = func(*args, **kwargs)

                # Thread-safe logowanie sukcesu
                with _log_lock:
                    logger.debug(f"Zakończono {operation_name}: {func.__name__}")
                return result

            except ScanningInterrupted:
                # Thread-safe logowanie przerwania
                with _log_lock:
                    logger.info(f"Przerwano {operation_name}: {func.__name__}")
                raise
            except Exception as e:
                # Thread-safe logowanie błędu z kontekstem
                with _log_lock:
                    logger.error(
                        f"Błąd w {operation_name} {func.__name__}: {e}", exc_info=True
                    )
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
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Katalog nie istnieje
        NotADirectoryError: Ścieżka nie jest katalogiem
        ScanningInterrupted: Gdy skanowanie zostało przerwane
        OSError: Problemy z dostępem do systemu plików
    """
    # Walidacja parametrów wejściowych
    _validate_directory(directory)
    _validate_max_depth(max_depth)
    _validate_callback(interrupt_check, "interrupt_check")
    _validate_callback(progress_callback, "progress_callback")

    return _collect_files_streaming(
        directory=directory,
        max_depth=max_depth,
        interrupt_check=interrupt_check,
        force_refresh=force_refresh,
        progress_callback=progress_callback,
    )


def collect_files(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, List[str]]:
    """
    Alias dla collect_files_streaming - DEPRECATED.

    Użyj collect_files_streaming zamiast tej funkcji.
    """
    warnings.warn(
        "collect_files jest deprecated. Użyj collect_files_streaming.",
        DeprecationWarning,
        stacklevel=2,
    )
    return collect_files_streaming(
        directory=directory,
        max_depth=max_depth,
        interrupt_check=interrupt_check,
        force_refresh=force_refresh,
        progress_callback=progress_callback,
    )


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
        ValueError: Nieprawidłowa strategia parowania lub parametry
    """
    # Walidacja parametrów
    if not isinstance(file_map, dict):
        raise ValueError("file_map musi być słownikiem")
    if not base_directory:
        raise ValueError("base_directory nie może być puste")
    if pair_strategy not in ["first_match", "best_match"]:
        raise ValueError(f"Nieprawidłowa strategia parowania: {pair_strategy}")

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

    Raises:
        ValueError: Nieprawidłowe parametry
    """
    # Walidacja parametrów
    if not isinstance(file_map, dict):
        raise ValueError("file_map musi być słownikiem")
    if not isinstance(processed_files, set):
        raise ValueError("processed_files musi być zestawem")

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
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Katalog nie istnieje
        NotADirectoryError: Ścieżka nie jest katalogiem
        ScanningInterrupted: Gdy skanowanie zostało przerwane
        OSError: Problemy z dostępem do systemu plików
    """
    # Walidacja parametrów wejściowych
    _validate_directory(directory)
    _validate_max_depth(max_depth)
    _validate_callback(interrupt_check, "interrupt_check")
    _validate_callback(progress_callback, "progress_callback")

    if pair_strategy not in ["first_match", "best_match"]:
        raise ValueError(f"Nieprawidłowa strategia parowania: {pair_strategy}")

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
    try:
        _clear_cache()
        logger.info("Wyczyszczono bufor wyników skanowania")
    except Exception as e:
        logger.error(f"Błąd podczas czyszczenia cache: {e}", exc_info=True)
        raise


@_log_scanner_operation("pobieranie statystyk")
def get_scan_statistics() -> Dict[str, float]:
    """
    Zwraca statystyki dotyczące bieżącego stanu cache.

    Returns:
        Dict[str, float]: Statystyki cache

    Raises:
        OSError: Problemy z dostępem do cache
    """
    try:
        return _get_scan_statistics()
    except Exception as e:
        logger.error(f"Błąd podczas pobierania statystyk: {e}", exc_info=True)
        raise
