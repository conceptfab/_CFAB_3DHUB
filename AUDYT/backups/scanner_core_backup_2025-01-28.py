"""
Moduł odpowiedzialny za skanowanie folderów.

Ten moduł zawiera funkcje do skanowania katalogów w poszukiwaniu plików
oraz koordynowania procesu skanowania.
"""

import gc
import logging
import os
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass
from threading import RLock
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

# Memory management configuration
GC_INTERVAL_FILES = 1000  # Garbage collection every 1000 files
MEMORY_MONITORING_ENABLED = True  # Enable memory usage monitoring

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

# Pre-computed set for O(1) lookup optimization
IGNORED_FOLDERS_SET = frozenset(IGNORED_FOLDERS)

# OPTYMALIZACJA PATCH 1: Pre-computed frozenset dla O(1) lookup
SUPPORTED_EXTENSIONS = frozenset(
    ext.lower() for ext in set(ARCHIVE_EXTENSIONS) | set(PREVIEW_EXTENSIONS)
)


# ELIMINATED: ScanConfig dataclass - over-engineered wrapper dla parametrów funkcji


# ELIMINATED: ScanCacheManager - niepotrzebna abstrakcja, replaced by helper functions


class ThreadSafeProgressManager:
    """Thread-safe progress reporting z rate limiting."""

    def __init__(
        self, progress_callback: Optional[Callable], throttle_interval: float = 0.1
    ):
        self.progress_callback = progress_callback
        self.throttle_interval = throttle_interval
        self._lock = RLock()
        self._last_progress_time = 0.0
        self._last_percent = -1

    def report_progress(self, percent: int, message: str, force: bool = False):
        """Thread-safe progress reporting z throttling."""
        if not self.progress_callback:
            return

        current_time = time.time()

        with self._lock:
            # Throttling - raportuj tylko jeśli minął wystarczający czas
            if (
                not force
                and current_time - self._last_progress_time < self.throttle_interval
                and abs(percent - self._last_percent) < 5
            ):
                return

            self._last_progress_time = current_time
            self._last_percent = percent

        # Callback poza lockiem aby uniknąć deadlock
        try:
            self.progress_callback(percent, message)
        except Exception as e:
            logger.warning(f"Progress callback error: {e}")

    def create_scaled_progress_callback(
        self, scale_factor: float = 0.5
    ) -> Optional[Callable]:
        """Tworzy callback ze skalowaniem postępu."""
        if not self.progress_callback:
            return None

        def scaled_progress(percent, message):
            scaled_percent = int(percent * scale_factor)
            self.report_progress(scaled_percent, message)

        return scaled_progress


class ThreadSafeVisitedDirs:
    """Thread-safe visited directories tracking z size limits."""

    def __init__(self, max_size: int = 50000):
        self._visited = set()
        self._lock = RLock()
        self._max_size = max_size
        self._cleanup_threshold = int(max_size * 0.8)  # Cleanup at 80% capacity

    def add(self, directory: str) -> bool:
        """Add directory and return True if it was already visited."""
        with self._lock:
            if directory in self._visited:
                return True

            # Check size limits before adding
            if len(self._visited) >= self._max_size:
                self._perform_cleanup()

            self._visited.add(directory)
            return False

    def _perform_cleanup(self):
        """Remove oldest entries to prevent memory overflow."""
        # Convert to list, sort, keep most recent 60%
        visited_list = list(self._visited)
        # Keep random 60% - approximation since we don't track timestamps
        import random

        keep_count = int(len(visited_list) * 0.6)
        random.shuffle(visited_list)
        self._visited = set(visited_list[:keep_count])

        logger.debug(
            f"ThreadSafeVisitedDirs cleanup: reduced from {len(visited_list)} "
            f"to {len(self._visited)} entries"
        )

    def clear(self):
        """Clear all visited directories."""
        with self._lock:
            self._visited.clear()

    def size(self) -> int:
        """Get number of visited directories."""
        with self._lock:
            return len(self._visited)

    def get_memory_usage(self) -> int:
        """Estimate memory usage in bytes."""
        with self._lock:
            # Approximate: average path length * number of entries * 2 (for Unicode)
            avg_path_length = 100  # Conservative estimate
            return len(self._visited) * avg_path_length * 2


@dataclass
class ScanContext:
    """Container dla scan-related parameters - reduces parameter passing."""

    session_id: str
    interrupt_check: Optional[Callable[[], bool]]
    progress_manager: Optional[ThreadSafeProgressManager]
    visited_dirs: ThreadSafeVisitedDirs

    def check_interruption(self, context: str = ""):
        """Convenience method for interruption checking."""
        _check_interruption(self.interrupt_check, f"{self.session_id}: {context}")


class SpecialFoldersManager:
    """Zarządza wykrywaniem i tworzeniem folderów specjalnych."""

    @staticmethod
    def find_special_folders(directory: str) -> List[SpecialFolder]:
        """Znajduje foldery specjalne na dysku."""
        # USUNIĘTA FUNKCJA - Foldery specjalne są teraz pobierane z metadanych.
        logger.debug("find_special_folders: Funkcja zastąpiona przez metadane")
        return []

    @staticmethod
    def handle_virtual_folders(
        directory: str, special_folders: List[SpecialFolder]
    ) -> List[SpecialFolder]:
        """Obsługuje tworzenie wirtualnych folderów na podstawie metadanych."""
        metadata_manager = MetadataManager.get_instance(directory)
        metadata = metadata_manager.load_metadata()

        if metadata and metadata.get("has_special_folders") and not special_folders:
            logger.info(
                f"Metadane dla '{directory}' wskazują na istnienie folderów "
                f"specjalnych, ale nie znaleziono ich na dysku. "
                f"Tworzę folder wirtualny."
            )

            virtual_folder = SpecialFoldersManager._create_virtual_folder(
                directory, metadata
            )
            if virtual_folder:
                special_folders.append(virtual_folder)
                logger.info(
                    f"Utworzono wirtualny folder: {virtual_folder.get_folder_path()}"
                )

        return special_folders

    @staticmethod
    def _create_virtual_folder(
        directory: str, metadata: dict
    ) -> Optional[SpecialFolder]:
        """Tworzy wirtualny folder na podstawie metadanych."""
        # Użyj nazwy z metadanych, jeśli jest dostępna
        special_folders_from_meta = metadata.get("special_folders")
        if special_folders_from_meta:
            virtual_folder_name = special_folders_from_meta[0]
            logger.debug(
                f"Używam nazwy folderu wirtualnego z metadanych: '{virtual_folder_name}'"
            )
        else:
            # Fallback na starą logikę
            logger.warning(
                f"Brak zdefiniowanych nazw folderów specjalnych w metadanych "
                f"dla '{directory}'. Używam domyślnej nazwy z konfiguracji."
            )
            special_folders_config = AppConfig.get_instance().special_folders
            if special_folders_config:
                virtual_folder_name = special_folders_config[0]
            else:
                logger.error("Brak domyślnych folderów specjalnych w konfiguracji!")
                virtual_folder_name = "special_folder"  # Ostateczny fallback

        virtual_folder_path = os.path.join(directory, virtual_folder_name)
        return SpecialFolder(
            folder_name=virtual_folder_name,
            folder_path=virtual_folder_path,
            is_virtual=True,
        )


# ELIMINATED: ScanOrchestrator - over-engineered pattern, replaced by simplified scan_folder_for_pairs()


def should_ignore_folder(folder_name: str) -> bool:
    """
    Sprawdza czy folder powinien być ignorowany podczas skanowania.
    OPTYMALIZACJA: Używa frozenset dla O(1) lookup zamiast O(n).

    Args:
        folder_name: Nazwa folderu do sprawdzenia

    Returns:
        True jeśli folder powinien być ignorowany
    """
    return folder_name in IGNORED_FOLDERS_SET or folder_name.startswith(".")


class ScanningInterrupted(Exception):
    """Wyjątek rzucany gdy skanowanie zostało przerwane przez użytkownika."""

    pass


def _check_interruption(
    interrupt_check: Optional[Callable[[], bool]], context: str = ""
):
    """Thread-safe interruption check with context logging."""
    if interrupt_check and interrupt_check():
        logger.debug(f"Skanowanie przerwane: {context}")
        raise ScanningInterrupted(f"Skanowanie przerwane: {context}")


def _handle_file_entry(
    entry,
    normalized_current_dir: str,
    file_map: Dict[str, List[str]],
    total_files_found: int,
    interrupt_check: Optional[Callable[[], bool]],
    session_id: str,
    progress_manager: Optional[ThreadSafeProgressManager] = None,
) -> int:
    """Process single file entry and return updated file count."""
    total_files_found += 1

    # Check interruption every 50 files
    if total_files_found % 50 == 0:
        _check_interruption(interrupt_check, "przetwarzanie plików")

    name = entry.name
    base_name, ext = os.path.splitext(name)

    # OPTYMALIZOWANY key generation
    map_key = os.path.join(normalized_current_dir, base_name.lower())
    full_file_path = os.path.join(normalized_current_dir, name)
    file_map[map_key].append(full_file_path)

    # Memory cleanup with monitoring
    _perform_memory_cleanup(total_files_found, session_id, progress_manager)

    return total_files_found


def _process_directory_entries(
    entries: List,
    current_dir: str,
    normalized_current_dir: str,
    file_map: Dict[str, List[str]],
    total_files_found: int,
    interrupt_check: Optional[Callable[[], bool]],
    session_id: str,
    progress_manager: Optional[ThreadSafeProgressManager] = None,
) -> Tuple[int, bool]:
    """Process directory entries and return (updated_file_count, has_relevant_subdirs)."""
    relevant_files = []
    has_relevant_subdirs = False

    for entry in entries:
        if entry.is_file():
            _, ext = os.path.splitext(entry.name)
            if ext.lower() in SUPPORTED_EXTENSIONS:
                relevant_files.append(entry)
        elif entry.is_dir() and not should_ignore_folder(entry.name):
            has_relevant_subdirs = True

    if not relevant_files and not has_relevant_subdirs:
        logger.debug(f"[{session_id}] Pomijam folder bez relevant files: {current_dir}")
        return total_files_found, has_relevant_subdirs

    _check_interruption(interrupt_check, "smart filtering")

    # Process relevant files
    for entry in relevant_files:
        total_files_found = _handle_file_entry(
            entry,
            normalized_current_dir,
            file_map,
            total_files_found,
            interrupt_check,
            session_id,
            progress_manager,
        )

    return total_files_found, has_relevant_subdirs


def _scan_subdirectories(
    entries: List,
    current_dir: str,
    depth: int,
    max_depth: int,
    interrupt_check: Optional[Callable[[], bool]],
    visited_dirs: ThreadSafeVisitedDirs,
    file_map: Dict[str, List[str]],
    total_files_found: int,
    total_folders_scanned: int,
    session_id: str,
    progress_manager: Optional[ThreadSafeProgressManager] = None,
) -> Tuple[int, int]:
    """Scan subdirectories recursively and return (updated_file_count, updated_folder_count)."""
    subfolders_processed = 0

    for entry in entries:
        if entry.is_dir():
            if should_ignore_folder(entry.name):
                logger.debug(f"[{session_id}] Pomijam ignorowany folder: {entry.name}")
                continue

            subfolders_processed += 1

            if subfolders_processed % 20 == 0:
                _check_interruption(
                    interrupt_check, f"rekursywne skanowanie w {current_dir}"
                )

            new_files, new_folders = _walk_directory_streaming(
                entry.path,
                depth + 1,
                max_depth,
                interrupt_check,
                visited_dirs,
                file_map,
                total_files_found,
                total_folders_scanned,
                session_id,
                progress_manager,
            )
            total_files_found = new_files
            total_folders_scanned = new_folders

    return total_files_found, total_folders_scanned


def _walk_directory_streaming(
    current_dir: str,
    depth: int,
    max_depth: int,
    interrupt_check: Optional[Callable[[], bool]],
    visited_dirs: ThreadSafeVisitedDirs,
    file_map: Dict[str, List[str]],
    total_files_found: int,
    total_folders_scanned: int,
    session_id: str,
    progress_manager: Optional[ThreadSafeProgressManager] = None,
) -> Tuple[int, int]:
    """Decomposed directory walking function with centralized progress."""
    normalized_current_dir = normalize_path(current_dir)

    _check_interruption(interrupt_check, "przed przetwarzaniem katalogu")

    if max_depth >= 0 and depth > max_depth:
        return total_files_found, total_folders_scanned

    if visited_dirs.add(normalized_current_dir):
        logger.debug(
            f"[{session_id}] Wykryto pętlę w katalogach: {normalized_current_dir}"
        )
        return total_files_found, total_folders_scanned

    try:
        total_folders_scanned += 1
        entries = list(os.scandir(current_dir))

        total_files_found, has_relevant_subdirs = _process_directory_entries(
            entries,
            current_dir,
            normalized_current_dir,
            file_map,
            total_files_found,
            interrupt_check,
            session_id,
            progress_manager,
        )

        if has_relevant_subdirs:
            total_files_found, total_folders_scanned = _scan_subdirectories(
                entries,
                current_dir,
                depth,
                max_depth,
                interrupt_check,
                visited_dirs,
                file_map,
                total_files_found,
                total_folders_scanned,
                session_id,
                progress_manager,
            )

        # OPCIONAL: Periodic progress updates during deep scanning
        if progress_manager and total_folders_scanned % 100 == 0:
            progress = min(
                90, int((total_files_found / max(1, total_folders_scanned)) * 10)
            )
            progress_manager.report_progress(
                progress,
                f"Głęboki scan: {total_files_found} plików w {total_folders_scanned} folderach",
            )

        logger.debug(
            f"[{session_id}] Skanowanie: {current_dir} -> {total_files_found} plików"
        )

    except (PermissionError, FileNotFoundError, OSError) as e:
        logger.debug(f"[{session_id}] Błąd dostępu do {current_dir}: {e}")
    except MemoryError as e:
        logger.critical(
            f"[{session_id}] Brak pamięci podczas skanowania {current_dir}: {e}"
        )
        raise
    except ScanningInterrupted:
        raise
    except Exception as e:
        logger.error(f"[{session_id}] Nieoczekiwany błąd w katalogu {current_dir}: {e}")

    return total_files_found, total_folders_scanned


def collect_files_streaming(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, List[str]]:
    """
    Zbiera wszystkie pliki w katalogu z thread-safe streaming progress.
    """
    session_id = uuid.uuid4().hex[:8]
    normalized_dir = normalize_path(directory)

    # THREAD-SAFE progress manager - UŻYWAMY KONSYSTENTNIE
    progress_manager = ThreadSafeProgressManager(progress_callback)

    # Cache check
    if not force_refresh:
        cached_file_map = cache.get_file_map(normalized_dir)
        if cached_file_map is not None:
            logger.debug(
                f"[{session_id}] CACHE HIT: używam buforowanych plików dla {normalized_dir}"
            )
            progress_manager.report_progress(
                100, f"Używam cache dla {normalized_dir}", force=True
            )
            return cached_file_map

    if not path_exists(normalized_dir) or not os.path.isdir(normalized_dir):
        logger.warning(
            f"[{session_id}] Katalog {normalized_dir} nie istnieje lub nie jest katalogiem"
        )
        progress_manager.report_progress(
            100, f"Katalog {normalized_dir} nie istnieje", force=True
        )
        return {}

    logger.info(
        f"[{session_id}] Rozpoczęto streaming zbieranie plików z katalogu: {normalized_dir}"
    )
    progress_manager.report_progress(
        0, f"Rozpoczynam streaming skanowanie: {normalized_dir}"
    )

    file_map = defaultdict(list)
    total_folders_scanned = 0
    total_files_found = 0
    start_time = time.time()

    # Thread-safe visited directories tracking
    visited_dirs = ThreadSafeVisitedDirs()

    # USUNIĘTO: _report_progress_with_throttling() - używamy progress_manager
    def report_scanning_progress():
        """Thread-safe progress reporting using centralized manager."""
        progress = min(
            95, int((total_files_found / max(1, total_folders_scanned)) * 10)
        )
        progress_manager.report_progress(
            progress,
            f"Skanowanie: {os.path.basename(normalized_dir)} "
            f"({total_files_found} plików, {total_folders_scanned} folderów)",
        )

    try:
        total_files_found, total_folders_scanned = _walk_directory_streaming(
            normalized_dir,
            0,
            max_depth,
            interrupt_check,
            visited_dirs,
            file_map,
            total_files_found,
            total_folders_scanned,
            session_id,
            progress_manager,
        )

        # Report progress using centralized manager
        report_scanning_progress()

    except ScanningInterrupted:
        raise
    finally:
        visited_dirs.clear()
        logger.debug(
            f"[{session_id}] Cleaned up visited_dirs cache ({visited_dirs.size()} entries)"
        )

    elapsed_time = time.time() - start_time
    files_per_second = total_files_found / elapsed_time if elapsed_time > 0 else 0
    folders_per_second = total_folders_scanned / elapsed_time if elapsed_time > 0 else 0

    logger.info(
        f"[{session_id}] SCAN_COMPLETED: {normalized_dir} | "
        f"files={total_files_found} | folders={total_folders_scanned} | "
        f"time={elapsed_time:.2f}s | "
        f"rate={files_per_second:.1f}files/s, {folders_per_second:.1f}folders/s"
    )

    if files_per_second < 100 and total_files_found > 500:
        logger.warning(
            f"[{session_id}] SLOW_SCAN_DETECTED: {normalized_dir} | "
            f"rate={files_per_second:.1f}files/s (expected >100files/s for large folders)"
        )

    if not force_refresh:
        cache.set_file_map(normalized_dir, file_map)

    progress_manager.report_progress(100, "Zakończono zbieranie plików", force=True)
    return file_map


# UPROSZCZONE HELPER FUNCTIONS zgodnie z PATCH 5


def _get_cached_scan_result(
    directory: str,
    pair_strategy: str,
    use_cache: bool,
    force_refresh: bool,
    progress_manager: ThreadSafeProgressManager,
) -> Optional[Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]]]:
    """Simplified cache retrieval."""
    if use_cache and not force_refresh:
        cached_result = cache.get_scan_result(directory, pair_strategy)
        if cached_result:
            logger.debug(f"CACHE HIT: Zwracam zbuforowany wynik dla {directory}")
            progress_manager.report_progress(
                100, f"Używam cache dla {directory}", force=True
            )
            return cached_result
    return None


def _save_scan_result(
    directory: str,
    pair_strategy: str,
    result: Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]],
    use_cache: bool,
):
    """Simplified cache saving."""
    if use_cache:
        cache.set_scan_result(directory, pair_strategy, result)


def _handle_special_folders_simple(directory: str) -> List[SpecialFolder]:
    """Simplified special folders handling."""
    metadata_manager = MetadataManager.get_instance(directory)
    metadata = metadata_manager.load_metadata()

    special_folders = []
    if metadata and metadata.get("has_special_folders"):
        # Create virtual folder based on metadata
        special_folders_from_meta = metadata.get("special_folders", [])
        if special_folders_from_meta:
            virtual_folder_name = special_folders_from_meta[0]
            virtual_folder_path = os.path.join(directory, virtual_folder_name)
            virtual_folder = SpecialFolder(
                folder_name=virtual_folder_name,
                folder_path=virtual_folder_path,
                is_virtual=True,
            )
            special_folders.append(virtual_folder)
            logger.info(f"Utworzono wirtualny folder: {virtual_folder_path}")

    return special_folders


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
    SIMPLIFIED: Skanuje folder bez over-engineered orchestrator pattern.
    """
    normalized_dir = normalize_path(directory)
    progress_manager = ThreadSafeProgressManager(progress_callback)

    # 1. Check cache
    cached_result = _get_cached_scan_result(
        normalized_dir, pair_strategy, use_cache, force_refresh_cache, progress_manager
    )
    if cached_result:
        return cached_result

    # 2. Validate directory
    if not path_exists(normalized_dir) or not os.path.isdir(normalized_dir):
        logger.warning(f"Katalog {normalized_dir} nie istnieje lub nie jest katalogiem")
        return [], [], [], []

    # 3. Collect files with optimized scanning
    progress_manager.report_progress(5, "Rozpoczynam skanowanie plików...")
    file_map = collect_files_streaming(
        normalized_dir,
        max_depth,
        interrupt_check,
        force_refresh_cache,
        lambda p, m: progress_manager.report_progress(5 + int(p * 0.4), m),  # 5-45%
    )

    # 4. Create file pairs
    progress_manager.report_progress(50, "Tworzenie par plików...")
    file_pairs, processed_files = create_file_pairs(
        file_map, base_directory=normalized_dir, pair_strategy=pair_strategy
    )

    # 5. Identify unpaired files
    progress_manager.report_progress(70, "Identyfikacja nieparowanych plików...")
    unpaired_archives, unpaired_previews = identify_unpaired_files(
        file_map, processed_files
    )

    # 6. Handle special folders
    progress_manager.report_progress(85, "Obsługa folderów specjalnych...")
    special_folders = _handle_special_folders_simple(normalized_dir)

    # 7. Save to cache and return
    result = (file_pairs, unpaired_archives, unpaired_previews, special_folders)
    _save_scan_result(normalized_dir, pair_strategy, result, use_cache)

    progress_manager.report_progress(
        100, f"Skanowanie zakończone: {len(file_pairs)} par", force=True
    )
    logger.info(
        f"Skanowanie zakończone dla {normalized_dir}. Znaleziono {len(file_pairs)} par."
    )

    return result


def get_scan_statistics() -> Dict[str, float]:
    """
    Zwraca statystyki dotyczące bieżącego stanu cache skanowania.

    Returns:
        Słownik zawierający statystyki
    """
    return cache.get_statistics()


# DEAD CODE REMOVED zgodnie z PATCH 6
# Note: find_special_folders() function has been removed as special folders
# are now handled through metadata system. Use _handle_special_folders_simple() instead.


def _get_memory_usage() -> int:
    """Enhanced memory usage reporting."""
    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()
        return memory_info.rss // 1024 // 1024  # Convert to MB
    except ImportError:
        logger.debug("psutil not available - memory monitoring disabled")
        return 0
    except Exception as e:
        logger.debug(f"Error getting memory usage: {e}")
        return 0


def _perform_memory_cleanup(
    total_files_found: int,
    session_id: str,
    progress_manager: Optional[ThreadSafeProgressManager] = None,
):
    """Enhanced memory cleanup z detailed monitoring."""
    if total_files_found % GC_INTERVAL_FILES == 0:
        initial_memory = _get_memory_usage()
        initial_objects = len(gc.get_objects()) if MEMORY_MONITORING_ENABLED else 0

        # Perform garbage collection
        collected = gc.collect()

        final_memory = _get_memory_usage()
        final_objects = len(gc.get_objects()) if MEMORY_MONITORING_ENABLED else 0

        if MEMORY_MONITORING_ENABLED and initial_memory > 0:
            memory_freed = initial_memory - final_memory
            objects_freed = initial_objects - final_objects

            logger.debug(
                f"[{session_id}] Memory cleanup at {total_files_found} files: "
                f"RAM: {initial_memory}MB -> {final_memory}MB (freed: {memory_freed}MB) | "
                f"Objects: {initial_objects} -> {final_objects} (freed: {objects_freed}) | "
                f"GC collected: {collected}"
            )

            # Performance warning dla excessive memory usage
            if final_memory > 500:  # >500MB threshold
                logger.warning(
                    f"[{session_id}] HIGH_MEMORY_USAGE: {final_memory}MB at {total_files_found} files "
                    f"(target: <500MB)"
                )

                # Optional: Report to progress manager
                if progress_manager:
                    progress_manager.report_progress(
                        -1,  # Special value for memory warnings
                        f"Wysokie zużycie pamięci: {final_memory}MB",
                        force=True,
                    )
