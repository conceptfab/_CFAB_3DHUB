"""
Moduł odpowiedzialny za skanowanie folderów i parowanie plików.

Ten moduł zawiera funkcje do skanowania katalogów w poszukiwaniu plików
oraz ich łączenia w pary (archiwa + podglądy).
"""

import logging
import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Callable, Dict, List, Optional, Set, Tuple, Union

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot

from src import app_config  # Importujemy moduł konfiguracji
from src.models.file_pair import FilePair
from src.utils.path_utils import is_path_valid, normalize_path, path_exists

# Konfiguracja loggera
logger = logging.getLogger(__name__)

# Używamy definicji rozszerzeń z centralnego pliku konfiguracyjnego
ARCHIVE_EXTENSIONS = set(app_config.SUPPORTED_ARCHIVE_EXTENSIONS)
PREVIEW_EXTENSIONS = set(app_config.SUPPORTED_PREVIEW_EXTENSIONS)

# Parametry cache z centralnego pliku konfiguracyjnego
MAX_CACHE_ENTRIES = app_config.SCANNER_MAX_CACHE_ENTRIES
MAX_CACHE_AGE_SECONDS = app_config.SCANNER_MAX_CACHE_AGE_SECONDS


@dataclass
class ScanStatistics:
    """Statystyki skanowania folderów."""

    total_folders_scanned: int = 0
    total_files_found: int = 0
    scan_duration: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass
class ScanCacheEntry:
    """Wpis w zjednoczonym cache skanowania."""

    timestamp: float
    directory_mtime: float
    file_map: Dict[str, List[str]]
    scan_results: Dict[str, Tuple[List[FilePair], List[str], List[str]]]  # per strategy

    def is_valid(self, current_mtime: float) -> bool:
        """Sprawdza czy wpis cache jest aktualny."""
        current_time = time.time()
        # Sprawdzamy wiek i modyfikację katalogu
        return (
            current_time - self.timestamp <= MAX_CACHE_AGE_SECONDS
            and current_mtime <= self.directory_mtime
        )


class ThreadSafeCache:
    """Thread-safe cache dla wyników skanowania."""

    def __init__(self):
        self._cache: Dict[str, ScanCacheEntry] = {}
        self._lock = RLock()
        self._stats = ScanStatistics()

    def get_cache_entry(self, directory: str) -> Optional[ScanCacheEntry]:
        """Pobiera wpis cache dla katalogu."""
        normalized_dir = normalize_path(directory)
        with self._lock:
            return self._cache.get(normalized_dir)

    def get_scan_result(
        self, directory: str, strategy: str
    ) -> Optional[Tuple[List[FilePair], List[str], List[str]]]:
        """Pobiera wynik skanowania dla konkretnej strategii."""
        entry = self.get_cache_entry(directory)
        if entry:
            current_mtime = get_directory_modification_time(directory)
            if entry.is_valid(current_mtime) and strategy in entry.scan_results:
                with self._lock:
                    self._stats.cache_hits += 1
                logger.debug(f"CACHE HIT: {directory} strategia={strategy}")
                return entry.scan_results[strategy]

        with self._lock:
            self._stats.cache_misses += 1
        logger.debug(f"CACHE MISS: {directory} strategia={strategy}")
        return None

    def get_file_map(self, directory: str) -> Optional[Dict[str, List[str]]]:
        """Pobiera mapę plików dla katalogu."""
        entry = self.get_cache_entry(directory)
        if entry:
            current_mtime = get_directory_modification_time(directory)
            if entry.is_valid(current_mtime):
                with self._lock:
                    self._stats.cache_hits += 1
                logger.debug(f"CACHE HIT (file_map): {directory}")
                return entry.file_map

        with self._lock:
            self._stats.cache_misses += 1
        logger.debug(f"CACHE MISS (file_map): {directory}")
        return None

    def store_file_map(self, directory: str, file_map: Dict[str, List[str]]):
        """Zapisuje mapę plików do cache."""
        normalized_dir = normalize_path(directory)
        current_time = time.time()
        current_mtime = get_directory_modification_time(directory)

        with self._lock:
            if normalized_dir in self._cache:
                # Aktualizuj istniejący wpis
                entry = self._cache[normalized_dir]
                entry.timestamp = current_time
                entry.directory_mtime = current_mtime
                entry.file_map = file_map
            else:
                # Utwórz nowy wpis
                self._cache[normalized_dir] = ScanCacheEntry(
                    timestamp=current_time,
                    directory_mtime=current_mtime,
                    file_map=file_map,
                    scan_results={},
                )

            self._cleanup_old_entries()

    def store_scan_result(
        self,
        directory: str,
        strategy: str,
        result: Tuple[List[FilePair], List[str], List[str]],
    ):
        """Zapisuje wynik skanowania do cache."""
        normalized_dir = normalize_path(directory)

        with self._lock:
            if normalized_dir in self._cache:
                self._cache[normalized_dir].scan_results[strategy] = result
            else:
                # Nie powinno się zdarzyć - file_map powinno być zapisane wcześniej
                logger.warning(
                    f"Próba zapisania scan_result bez file_map dla {directory}"
                )

    def clear(self):
        """Czyści cały cache."""
        with self._lock:
            self._cache.clear()
            self._stats = ScanStatistics()
        logger.info("Wyczyszczono zjednoczony cache skanowania")

    def remove_entry(self, directory: str):
        """Usuwa konkretny wpis z cache."""
        normalized_dir = normalize_path(directory)
        with self._lock:
            if normalized_dir in self._cache:
                del self._cache[normalized_dir]
                logger.debug(f"Usunięto wpis cache: {directory}")

    def _cleanup_old_entries(self):
        """Usuwa stare wpisy z cache (wywołane pod lockiem)."""
        current_time = time.time()
        to_remove = []

        # Usuwanie na podstawie wieku
        for key, entry in self._cache.items():
            if current_time - entry.timestamp > MAX_CACHE_AGE_SECONDS:
                to_remove.append(key)

        for key in to_remove:
            if key in self._cache:  # Dodatkowe sprawdzenie
                del self._cache[key]
                logger.debug(f"Usunięto stary wpis z cache (wiek): {key}")

        # Usuwanie na podstawie liczby
        if len(self._cache) > MAX_CACHE_ENTRIES:
            # Sortuj od najstarszego do najnowszego
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1].timestamp)
            num_to_remove = len(self._cache) - MAX_CACHE_ENTRIES

            for key, _ in sorted_items[:num_to_remove]:
                if key in self._cache:
                    del self._cache[key]
                    logger.debug(f"Usunięto stary wpis z cache (liczba): {key}")

    def get_statistics(self) -> Dict[str, int]:
        """Zwraca statystyki cache."""
        with self._lock:
            return {
                "cache_entries": len(self._cache),
                "cache_hits": self._stats.cache_hits,
                "cache_misses": self._stats.cache_misses,
                "hit_ratio": (
                    self._stats.cache_hits
                    / max(1, self._stats.cache_hits + self._stats.cache_misses)
                )
                * 100,
            }


# Globalna instancja thread-safe cache - UNIFIED CACHE SYSTEM
_unified_cache = ThreadSafeCache()


class ScanningInterrupted(Exception):
    """Wyjątek rzucany, gdy skanowanie zostało przerwane przez użytkownika."""

    pass


def clear_cache() -> None:
    """
    Czyści bufor wyników skanowania.
    Użyteczne gdy użytkownik chce wymusić ponowne skanowanie.
    """
    _unified_cache.clear()
    logger.info("Wyczyszczono ujednolicony cache skanowania")


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

    ETAP 3 OPTYMALIZACJA: Usunięto podwójne skanowanie - progress jest streamowany
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
        cached_file_map = _unified_cache.get_file_map(normalized_dir)
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

        # ETAP 3 EARLY STOPPING: Sprawdzenie czy należy przerwać skanowanie
        if interrupt_check and interrupt_check():
            logger.warning("Skanowanie przerwane przez użytkownika")
            raise ScanningInterrupted("Skanowanie przerwane przez użytkownika")

        # ETAP 3 EARLY STOPPING: Sprawdzanie co każde 50 plików dla responsywności
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

            # ETAP 3 EARLY STOPPING: Sprawdzenie przerwania po liście folderów
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

                    # ETAP 3 EARLY STOPPING: Sprawdzenie co 10 plików w folderze
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

                    # ETAP 3 EARLY STOPPING: Sprawdzenie co 5 podfolderów
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
    _unified_cache.store_file_map(normalized_dir, result_dict)

    return result_dict



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
            # ETAP 3 OPTYMALIZACJA: Zmieniono z O(n*m) na O(n+m) używając hash maps
            # Stary algorytm miał zagnieżdżone pętle dla każdej pary archiwum-podgląd
            # Nowy algorytm grupuje podglądy według nazw bazowych i używa hashowania

            # Preferowane rozszerzenia podglądu (od najbardziej preferowanego)
            preview_preference = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]

            # Budujemy hash mapę podglądów według nazw bazowych - O(m)
            preview_map = defaultdict(list)
            for preview in preview_files:
                preview_name = os.path.basename(preview)
                preview_base_name = os.path.splitext(preview_name)[0].lower()
                preview_map[preview_base_name].append(preview)

            # Dla każdego archiwum szukamy najlepszego podglądu - O(n)
            for archive in archive_files:
                archive_name = os.path.basename(archive)
                archive_base_name = os.path.splitext(archive_name)[0].lower()
                best_preview = None
                best_score = -1

                # Szukamy kandydatów podglądów - O(1) dzięki hash mapie
                candidates = []

                # 1. Dokładna zgodność nazwy (najlepsze dopasowanie)
                if archive_base_name in preview_map:
                    candidates.extend(
                        [(p, 1000) for p in preview_map[archive_base_name]]
                    )

                # 2. Częściowa zgodność - sprawdzamy tylko prefiksy (optymalizacja)
                for preview_base_name, preview_list in preview_map.items():
                    if preview_base_name != archive_base_name:  # Już sprawdzone wyżej
                        if preview_base_name.startswith(archive_base_name):
                            candidates.extend([(p, 500) for p in preview_list])
                        elif archive_base_name.startswith(preview_base_name):
                            candidates.extend([(p, 500) for p in preview_list])

                # Oceniamy tylko znalezionych kandydatów
                for preview, base_score in candidates:
                    score = base_score
                    preview_ext = os.path.splitext(preview)[1].lower()

                    # Dodajemy punkty za preferowane rozszerzenie
                    if preview_ext in preview_preference:
                        score += (
                            len(preview_preference)
                            - preview_preference.index(preview_ext)
                        ) * 10

                    # Dodajemy mały bonus za nowsze pliki
                    try:
                        mtime = os.path.getmtime(preview)
                        score += mtime / 10000000  # Dodaje mały ułamek do punktacji
                    except (OSError, PermissionError):
                        pass  # Ignorujemy błędy przy sprawdzaniu czasu modyfikacji

                    # Aktualizujemy najlepszy podgląd
                    if score > best_score:
                        best_score = score
                        best_preview = preview

                # Jeśli znaleźliśmy pasujący podgląd, tworzymy parę
                if best_preview and best_score > 0:
                    try:
                        pair = FilePair(archive, best_preview, base_directory)
                        found_pairs.append(pair)
                        processed_files.add(archive)
                        processed_files.add(best_preview)
                    except ValueError as e:
                        logger.error(
                            f"Błąd tworzenia FilePair dla '{archive}' i '{best_preview}': {e}"
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
    progress_callback: Optional[
        Callable[[int, str], None]
    ] = None,  # Nowy parametr do raportowania postępu
) -> Tuple[List[FilePair], List[str], List[str]]:
    """
    Skanuje podany katalog i jego podkatalogi w poszukiwaniu par plików.

    ETAP 3 ZOPTYMALIZOWANE: Używa nowego ujednoliconego cache i streaming skanowania.

    Args:
        directory: Ścieżka do katalogu do przeskanowania
        max_depth: Maksymalna głębokość rekursji, -1 oznacza brak limitu
        use_cache: Czy używać buforowanych wyników jeśli są dostępne
        pair_strategy: Strategia parowania plików (zastępuje pair_all)
        interrupt_check: Opcjonalna funkcja sprawdzająca czy przerwać skanowanie
        force_refresh_cache: Czy wymusić odświeżenie cache plików (przekazywane do collect_files)
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

    # ETAP 3: Sprawdź nowy ujednolicony cache
    if use_cache and not force_refresh_cache:
        cached_result = _unified_cache.get_scan_result(normalized_dir, pair_strategy)
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
        # Krok 1: Zbieranie wszystkich plików (80% całego procesu) - używa nowego streaming
        if progress_callback:
            # Tworzymy wrapper do callback'a, aby skalować postęp z collect_files (0-80%)
            def scaled_progress(percent, message):
                scaled = int(percent * 0.8)  # collect_files to 80% całego procesu
                progress_callback(scaled, message)

            file_map = collect_files_streaming(  # ETAP 3: Używa nowej funkcji streaming
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
        f"Zakończono ETAP 3 skanowanie '{normalized_dir}' w czasie {scan_duration:.2f}s. "
        f"Znaleziono {len(found_pairs)} par, {len(unpaired_archives)} niesparowanych "
        f"archiwów i {len(unpaired_previews)} niesparowanych podglądów."
    )
    logger.info(result_message)

    if progress_callback:
        progress_callback(100, f"Zakończono: {len(found_pairs)} par")

    # Zapisujemy wynik do ujednoliconego cache
    result = (found_pairs, unpaired_archives, unpaired_previews)
    _unified_cache.store_scan_result(
        normalized_dir, pair_strategy, result
    )

    return result


def get_scan_statistics() -> Dict[str, int]:
    """
    Zwraca statystyki dotyczące bieżącego stanu cache skanowania.

    Returns:
        Słownik zawierający statystyki cache
    """
    return _unified_cache.get_statistics()


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
