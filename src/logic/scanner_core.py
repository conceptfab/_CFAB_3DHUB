"""
Moduł odpowiedzialny za skanowanie folderów.

Ten moduł zawiera funkcje do skanowania katalogów w poszukiwaniu plików
oraz koordynowania procesu skanowania.
"""

import gc
import logging
import os
import queue
import threading
import time
import uuid
from collections import defaultdict
from contextlib import contextmanager
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
GC_INTERVAL_FILES = 500  # Zmniejszono z 1000 do 500 dla lepszej responsywności
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


# PATCH 4: I/O Timeout Handling (Windows compatible)
@contextmanager
def io_timeout(timeout_seconds: int = 30):
    """Context manager for I/O operations with timeout - Windows compatible."""
    # On Windows, signal.SIGALRM doesn't exist, so we skip timeout
    # This is acceptable as Windows file I/O is generally more reliable
    try:
        yield
    except Exception:
        # Let other exceptions pass through
        raise


# PATCH 5: Production Logging Optimization
class RateLimitedLogger:
    """Logger wrapper with rate limiting for production performance."""

    def __init__(self, logger, rate_limit_seconds: float = 1.0):
        self.logger = logger
        self.rate_limit_seconds = rate_limit_seconds
        self._last_log_times = {}

    def debug_throttled(self, message: str, key: str = None):
        """Debug logging with throttling based on message key."""
        if not self.logger.isEnabledFor(logging.DEBUG):
            return

        log_key = key or message[:50]  # Use first 50 chars as key
        current_time = time.time()

        if log_key in self._last_log_times:
            if current_time - self._last_log_times[log_key] < self.rate_limit_seconds:
                return

        self._last_log_times[log_key] = current_time
        self.logger.debug(message)

    def info(self, message: str):
        """Standard info logging."""
        self.logger.info(message)

    def warning(self, message: str):
        """Standard warning logging."""
        self.logger.warning(message)

    def error(self, message: str):
        """Standard error logging."""
        self.logger.error(message)


# Create rate-limited logger instance with optimized timing
rate_limited_logger = RateLimitedLogger(logger, rate_limit_seconds=1.0)


# PATCH 2: Async Progress Callback Wrapper with Adaptive Queue Sizing
class AsyncProgressManager:
    """Non-blocking progress manager with adaptive queue sizing."""

    def __init__(
        self, progress_callback: Optional[Callable], throttle_interval: float = 0.1
    ):
        self.original_callback = progress_callback
        self.throttle_interval = throttle_interval
        self._lock = RLock()
        self._last_progress_time = 0.0
        self._last_percent = -1

        # Adaptive callback queue sizing based on system load
        base_queue_size = 10
        # Increase queue size for better throughput on faster systems
        adaptive_queue_size = min(50, max(10, base_queue_size * 2))
        self._callback_queue = queue.Queue(maxsize=adaptive_queue_size)
        self._stop_event = threading.Event()
        self._dropped_updates = 0

        if progress_callback:
            self._callback_thread = threading.Thread(
                target=self._callback_worker, daemon=True
            )
            self._callback_thread.start()

    def _callback_worker(self):
        """Background thread for non-blocking callback execution with backpressure handling."""
        while not self._stop_event.is_set():
            try:
                percent, message = self._callback_queue.get(timeout=0.1)
                if self.original_callback:
                    try:
                        self.original_callback(percent, message)
                    except Exception as e:
                        logger.warning(f"Progress callback error: {e}")
                self._callback_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Callback worker error: {e}")

    def report_progress(self, percent: int, message: str, force: bool = False):
        """Non-blocking progress reporting with improved throttling."""
        if not self.original_callback:
            return

        current_time = time.time()

        with self._lock:
            if (
                not force
                and current_time - self._last_progress_time < self.throttle_interval
                and abs(percent - self._last_percent) < 3  # Zmniejszono z 5 do 3 dla smoother updates
            ):
                return

            self._last_progress_time = current_time
            self._last_percent = percent

        # Non-blocking queue put with backpressure handling
        try:
            self._callback_queue.put_nowait((percent, message))
        except queue.Full:
            # Implement backpressure - try to remove old updates and add new one
            try:
                # Remove oldest update if queue is full
                self._callback_queue.get_nowait()
                self._callback_queue.put_nowait((percent, message))
                self._dropped_updates += 1
                if self._dropped_updates % 10 == 0:
                    logger.debug(f"Progress queue full, dropped {self._dropped_updates} updates")
            except (queue.Empty, queue.Full):
                # If still can't add, drop this update
                self._dropped_updates += 1

    def shutdown(self):
        """Cleanup async callback thread."""
        if hasattr(self, "_stop_event"):
            self._stop_event.set()
        if hasattr(self, "_callback_thread"):
            self._callback_thread.join(timeout=1.0)

    def create_scaled_progress_callback(
        self, scale_factor: float = 0.5
    ) -> Optional[Callable]:
        """Tworzy callback ze skalowaniem postępu."""
        if not self.original_callback:
            return None

        def scaled_progress(percent, message):
            scaled_percent = int(percent * scale_factor)
            self.report_progress(scaled_percent, message)

        return scaled_progress


# LEGACY ThreadSafeProgressManager - kept for backward compatibility
class ThreadSafeProgressManager:
    """Legacy thread-safe progress reporting - use AsyncProgressManager for new code."""

    def __init__(
        self, progress_callback: Optional[Callable], throttle_interval: float = 0.1
    ):
        # Delegate to AsyncProgressManager for enhanced functionality
        self._async_manager = AsyncProgressManager(progress_callback, throttle_interval)

    def report_progress(self, percent: int, message: str, force: bool = False):
        """Thread-safe progress reporting z throttling."""
        self._async_manager.report_progress(percent, message, force)

    def create_scaled_progress_callback(
        self, scale_factor: float = 0.5
    ) -> Optional[Callable]:
        """Tworzy callback ze skalowaniem postępu."""
        return self._async_manager.create_scaled_progress_callback(scale_factor)


# PATCH 1: Thread Safety Fix w ThreadSafeVisitedDirs with optimized size
class ThreadSafeVisitedDirs:
    """Thread-safe visited directories tracking with optimized memory usage."""

    def __init__(self, max_size: int = 10000):  # Zmniejszono z 50000 do 10000
        self._visited = {}  # Changed: dict to track access order for LRU
        self._access_counter = 0
        self._lock = RLock()
        self._max_size = max_size
        self._cleanup_threshold = int(max_size * 0.8)

    def add(self, directory: str) -> bool:
        """Add directory and return True if it was already visited."""
        with self._lock:
            if directory in self._visited:
                # Update access order for LRU
                self._access_counter += 1
                self._visited[directory] = self._access_counter
                return True

            if len(self._visited) >= self._max_size:
                self._perform_lru_cleanup()

            self._access_counter += 1
            self._visited[directory] = self._access_counter
            return False

    def _perform_lru_cleanup(self):
        """LRU-based cleanup instead of random shuffling."""
        # Sort by access counter (LRU = lowest counter values)
        sorted_items = sorted(self._visited.items(), key=lambda x: x[1])
        keep_count = int(len(sorted_items) * 0.6)

        # Keep most recently used 60%
        new_visited = dict(sorted_items[-keep_count:])
        self._visited = new_visited

        logger.debug(
            f"ThreadSafeVisitedDirs LRU cleanup: reduced from {len(sorted_items)} "
            f"to {len(self._visited)} entries"
        )

    def clear(self):
        """Clear all visited directories."""
        with self._lock:
            self._visited.clear()
            self._access_counter = 0

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


# PATCH 3: Adaptive Memory Cleanup with increased threshold
class AdaptiveMemoryManager:
    """Adaptive memory management with smart GC intervals and higher thresholds."""

    def __init__(self):
        self.base_gc_interval = 500  # Zmniejszono z 1000 do 500
        self.max_gc_interval = 2500  # Proporcjonalnie zmniejszono
        self.min_gc_interval = 100
        self.memory_threshold_mb = 800  # Zwiększono z 400MB do 800MB
        self.critical_memory_threshold_mb = 1200  # Nowy próg krytyczny
        self.last_gc_files = 0
        self.last_memory_usage = 0

    def should_perform_gc(self, total_files_found: int) -> bool:
        """Determine if GC should be performed based on adaptive criteria with higher thresholds."""
        current_memory = self._get_memory_usage()
        files_since_gc = total_files_found - self.last_gc_files

        # Force GC if critical memory usage is reached
        if current_memory > self.critical_memory_threshold_mb:
            logger.warning(f"CRITICAL_MEMORY: {current_memory}MB - forcing immediate GC")
            return True

        # Force GC if normal threshold is exceeded
        if current_memory > self.memory_threshold_mb:
            return True

        # Calculate adaptive interval based on memory growth rate
        memory_growth = current_memory - self.last_memory_usage
        if memory_growth > 50:  # Significant memory growth (50MB+)
            # More frequent GC if memory is growing fast
            adaptive_interval = max(
                self.min_gc_interval, self.base_gc_interval - (memory_growth * 2)
            )
        else:
            # Less frequent GC if memory is stable
            adaptive_interval = min(self.max_gc_interval, self.base_gc_interval * 1.2)

        return files_since_gc >= adaptive_interval

    def perform_cleanup(
        self,
        total_files_found: int,
        session_id: str,
        progress_manager: Optional[AsyncProgressManager] = None,
    ):
        """Enhanced memory cleanup with adaptive intervals and better logging."""
        if not self.should_perform_gc(total_files_found):
            return

        initial_memory = self._get_memory_usage()
        
        # Report progress for large cleanups
        if progress_manager and initial_memory > self.memory_threshold_mb:
            progress_manager.report_progress(
                -1, f"Optymalizacja pamięci... ({initial_memory}MB)", force=True
            )
        
        collected = gc.collect()
        final_memory = self._get_memory_usage()

        # Update tracking
        self.last_gc_files = total_files_found
        self.last_memory_usage = final_memory

        # Enhanced logging with better thresholds
        if final_memory > self.critical_memory_threshold_mb:
            logger.error(
                f"[{session_id}] CRITICAL_MEMORY: {final_memory}MB at {total_files_found} files - "
                f"system may be unstable"
            )
        elif final_memory > self.memory_threshold_mb:
            logger.debug(
                f"[{session_id}] HIGH_MEMORY: {final_memory}MB at {total_files_found} files"
            )
        else:
            rate_limited_logger.debug_throttled(
                f"[{session_id}] GC: {initial_memory}MB->{final_memory}MB, "
                f"collected={collected}, files={total_files_found}",
                key=f"gc_debug_{session_id}",
            )

    def _get_memory_usage(self) -> int:
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


# Global adaptive memory manager instance
_adaptive_memory_manager = AdaptiveMemoryManager()


@dataclass
class ScanContext:
    """Container dla scan-related parameters - reduces parameter passing."""

    session_id: str
    interrupt_check: Optional[Callable[[], bool]]
    progress_manager: Optional[
        AsyncProgressManager
    ]  # Updated to use AsyncProgressManager
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
    progress_manager: Optional[AsyncProgressManager] = None,
) -> int:
    """Process single file entry and return updated file count - FIXED ALGORITHM."""
    total_files_found += 1

    # Check interruption every 50 files
    if total_files_found % 50 == 0:
        _check_interruption(interrupt_check, "przetwarzanie plików")

    name = entry.name
    base_name, ext = os.path.splitext(name)

    # CRITICAL FIX: Group files by base_name for pairing algorithm
    map_key = os.path.join(normalized_current_dir, base_name.lower())
    full_file_path = os.path.join(normalized_current_dir, name)
    file_map[map_key].append(full_file_path)

    # Enhanced memory management with adaptive cleanup
    _adaptive_memory_manager.perform_cleanup(
        total_files_found, session_id, progress_manager
    )

    return total_files_found


def _process_directory_entries(
    entries: List,
    current_dir: str,
    normalized_current_dir: str,
    file_map: Dict[str, List[str]],
    total_files_found: int,
    interrupt_check: Optional[Callable[[], bool]],
    session_id: str,
    progress_manager: Optional[AsyncProgressManager] = None,
) -> Tuple[int, bool]:
    """Process directory entries and return (updated_file_count, has_relevant_subdirs) - FIXED."""
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
        rate_limited_logger.debug_throttled(
            f"[{session_id}] Pomijam folder bez relevant files: {current_dir}",
            key=f"skip_folder_{session_id}",
        )
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
    progress_manager: Optional[AsyncProgressManager] = None,
) -> Tuple[int, int]:
    """Enhanced subdirectory scanning with timeout protection."""
    for entry in entries:
        _check_interruption(interrupt_check, "podczas skanowania podfolderów")

        if entry.is_dir() and not should_ignore_folder(entry.name):
            subdir_path = os.path.join(current_dir, entry.name)
            total_files_found, total_folders_scanned = (
                _walk_directory_streaming_with_timeout(
                    subdir_path,
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
            )

    return total_files_found, total_folders_scanned


# PATCH 4: Enhanced _walk_directory_streaming with I/O timeout protection
def _walk_directory_streaming_with_timeout(
    current_dir: str,
    depth: int,
    max_depth: int,
    interrupt_check: Optional[Callable[[], bool]],
    visited_dirs: ThreadSafeVisitedDirs,
    file_map: Dict[str, List[str]],
    total_files_found: int,
    total_folders_scanned: int,
    session_id: str,
    progress_manager: Optional[AsyncProgressManager] = None,
    io_timeout_seconds: int = 30,
) -> Tuple[int, int]:
    """Directory walking with I/O timeout protection."""
    normalized_current_dir = normalize_path(current_dir)

    _check_interruption(interrupt_check, "przed przetwarzaniem katalogu")

    if max_depth >= 0 and depth > max_depth:
        return total_files_found, total_folders_scanned

    if visited_dirs.add(normalized_current_dir):
        rate_limited_logger.debug_throttled(
            f"[{session_id}] Wykryto pętlę w katalogach: {normalized_current_dir}",
            key=f"loop_detection_{session_id}",
        )
        return total_files_found, total_folders_scanned

    try:
        total_folders_scanned += 1

        # Protected scandir with timeout
        try:
            with io_timeout(io_timeout_seconds):
                entries = list(os.scandir(current_dir))
        except TimeoutError:
            logger.warning(f"[{session_id}] I/O timeout dla {current_dir}, pomijam")
            return total_files_found, total_folders_scanned

        # Process directory entries
        total_files_found, has_subdirs = _process_directory_entries(
            entries,
            current_dir,
            normalized_current_dir,
            file_map,
            total_files_found,
            interrupt_check,
            session_id,
            progress_manager,
        )

        # Scan subdirectories if they exist
        if has_subdirs:
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

    except (PermissionError, FileNotFoundError, OSError) as e:
        rate_limited_logger.debug_throttled(
            f"[{session_id}] Błąd dostępu do {current_dir}: {e}",
            key=f"access_error_{session_id}",
        )
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


# Legacy wrapper function
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
    progress_manager: Optional[AsyncProgressManager] = None,
) -> Tuple[int, int]:
    """Legacy wrapper that delegates to enhanced version with timeout."""
    return _walk_directory_streaming_with_timeout(
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


def collect_files_streaming(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, List[str]]:
    """Enhanced file collection with async progress management."""
    session_id = str(uuid.uuid4())[:8]
    progress_manager = AsyncProgressManager(progress_callback)

    try:
        normalized_dir = normalize_path(directory)

        if force_refresh:
            cache.clear_cache()

        if not path_exists(normalized_dir) or not os.path.isdir(normalized_dir):
            logger.warning(f"[{session_id}] Katalog {normalized_dir} nie istnieje")
            return {}

        file_map = defaultdict(list)
        visited_dirs = ThreadSafeVisitedDirs()

        rate_limited_logger.info(
            f"[{session_id}] Rozpoczynam skanowanie: {normalized_dir}"
        )

        def report_scanning_progress():
            progress_manager.report_progress(
                min(99, int(len(file_map) / 10)),
                f"Skanowanie: {len(file_map)} katalogów, {sum(len(files) for files in file_map.values())} plików",
            )

        # Enhanced directory walking with timeout protection
        total_files_found, total_folders_scanned = (
            _walk_directory_streaming_with_timeout(
                normalized_dir,
                0,
                max_depth,
                interrupt_check,
                visited_dirs,
                file_map,
                0,
                0,
                session_id,
                progress_manager,
            )
        )

        rate_limited_logger.info(
            f"[{session_id}] Skanowanie zakończone: {total_files_found} plików "
            f"w {total_folders_scanned} katalogach"
        )

        progress_manager.report_progress(100, "Zakończono zbieranie plików", force=True)
        return file_map

    finally:
        # Cleanup async progress manager
        progress_manager.shutdown()


# UPROSZCZONE HELPER FUNCTIONS zgodnie z PATCH 5
def _get_cached_scan_result(
    directory: str,
    pair_strategy: str,
    use_cache: bool,
    force_refresh: bool,
    progress_manager: AsyncProgressManager,
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
    """Enhanced scanning with async progress management."""
    normalized_dir = normalize_path(directory)
    progress_manager = AsyncProgressManager(progress_callback)

    try:
        # 1. Check cache
        cached_result = _get_cached_scan_result(
            normalized_dir,
            pair_strategy,
            use_cache,
            force_refresh_cache,
            progress_manager,
        )
        if cached_result:
            return cached_result

        # 2. Validate directory
        if not path_exists(normalized_dir) or not os.path.isdir(normalized_dir):
            logger.warning(
                f"Katalog {normalized_dir} nie istnieje lub nie jest katalogiem"
            )
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

    finally:
        # Cleanup async progress manager
        progress_manager.shutdown()


def get_scan_statistics() -> Dict[str, float]:
    """
    Zwraca statystyki dotyczące bieżącego stanu cache skanowania.

    Returns:
        Słownik zawierający statystyki
    """
    return cache.get_statistics()


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


# PATCH 3: Use adaptive memory manager instead of fixed intervals
def _perform_memory_cleanup(
    total_files_found: int,
    session_id: str,
    progress_manager: Optional[AsyncProgressManager] = None,
):
    """Use adaptive memory manager instead of fixed intervals."""
    _adaptive_memory_manager.perform_cleanup(
        total_files_found, session_id, progress_manager
    )
