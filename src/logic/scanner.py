"""
Moduł odpowiedzialny za skanowanie folderów i parowanie plików.

Ten moduł zawiera funkcje do skanowania katalogów w poszukiwaniu plików
oraz ich łączenia w pary (archiwa + podglądy).

UWAGA: Ten moduł jest fasadą publicznego API. Implementacja podzielona na:
- scanner_core.py - podstawowe funkcje skanowania
- scanner_cache.py - zarządzanie cache
- file_pairing.py - logika parowania plików
"""

import logging
from typing import Callable, Dict, List, Optional, Set, Tuple

from src.models.file_pair import FilePair
from src.logic.file_pairing import (
    ARCHIVE_EXTENSIONS, 
    PREVIEW_EXTENSIONS,
    create_file_pairs as _create_file_pairs,
    identify_unpaired_files as _identify_unpaired_files
)
from src.logic.scanner_cache import (
    cache as _cache,
    clear_cache as _clear_cache,
    get_directory_modification_time
)
from src.logic.scanner_core import (
    collect_files_streaming as _collect_files_streaming,
    scan_folder_for_pairs as _scan_folder_for_pairs,
    ScanningInterrupted,
    get_scan_statistics as _get_scan_statistics
)

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Eksport publicznych funkcji z zachowaniem nazw interfejsu dla kompatybilności
def collect_files(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, List[str]]:
    """
    Zbiera wszystkie pliki w katalogu. 
    Deleguje do nowej funkcji collect_files_streaming.
    
    Ta funkcja jest utrzymywana dla kompatybilności z istniejącym kodem.
    """
    logger.debug("collect_files() deleguje do collect_files_streaming()")
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
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, List[str]]:
    """
    Zbiera wszystkie pliki w katalogu z streaming progress.
    Deleguje do scanner_core.collect_files_streaming.
    """
    return _collect_files_streaming(
        directory=directory,
        max_depth=max_depth,
        interrupt_check=interrupt_check,
        force_refresh=force_refresh,
        progress_callback=progress_callback,
    )

def create_file_pairs(
    file_map: Dict[str, List[str]],
    base_directory: str,
    pair_strategy: str = "first_match",
) -> Tuple[List[FilePair], Set[str]]:
    """
    Tworzy pary plików na podstawie zebranych danych.
    Deleguje do file_pairing.create_file_pairs.
    """
    return _create_file_pairs(
        file_map=file_map,
        base_directory=base_directory,
        pair_strategy=pair_strategy,
    )

def identify_unpaired_files(
    file_map: Dict[str, List[str]],
    processed_files: Set[str],
) -> Tuple[List[str], List[str]]:
    """
    Identyfikuje niesparowane pliki.
    Deleguje do file_pairing.identify_unpaired_files.
    """
    return _identify_unpaired_files(file_map, processed_files)

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
    Deleguje do scanner_core.scan_folder_for_pairs.
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
    Deleguje do scanner_cache.clear_cache.
    """
    _clear_cache()
    logger.info("Wyczyszczono bufor wyników skanowania")

def get_scan_statistics() -> Dict[str, float]:
    """
    Zwraca statystyki dotyczące bieżącego stanu cache.
    Deleguje do scanner_core.get_scan_statistics.
    """
    return _get_scan_statistics()
