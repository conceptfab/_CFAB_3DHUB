# PATCH-CODE DLA: SCANNER_CORE

**Powiązany plik z analizą:** `../corrections/scanner_core_correction.md`
**Zasady ogólne:** `../../_BASE_/refactoring_rules.md`

---

### PATCH 1: POPRAWA THREAD SAFETY I MEMORY MANAGEMENT

**Problem:** Race conditions w visited_dirs, memory leaks przy interrupted scans, thread safety issues
**Rozwiązanie:** Thread-safe collections, proper cleanup w finally blocks, enhanced memory management

```python
import threading
from threading import RLock
from collections import defaultdict
import weakref
import uuid

# Dodaj na początku pliku:
class ThreadSafeScanSession:
    """Thread-safe session for scanning operations z proper resource management."""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self._visited_dirs = set()
        self._lock = RLock()
        self._total_files = 0
        self._total_folders = 0
        self._start_time = None
        
    def add_visited_dir(self, directory: str) -> bool:
        """Thread-safe add directory, returns False if already visited."""
        with self._lock:
            if directory in self._visited_dirs:
                return False
            self._visited_dirs.add(directory)
            return True
    
    def increment_counters(self, files: int = 0, folders: int = 0):
        """Thread-safe increment counters."""
        with self._lock:
            self._total_files += files
            self._total_folders += folders
    
    def get_stats(self) -> tuple:
        """Thread-safe get statistics."""
        with self._lock:
            return self._total_files, self._total_folders
    
    def cleanup(self):
        """Cleanup resources."""
        with self._lock:
            self._visited_dirs.clear()
            logger.debug(f"Session {self.session_id}: Cleaned up visited_dirs")

# ZMIENIĆ collect_files_streaming signature i implementation:
def collect_files_streaming(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, List[str]]:
    """
    Thread-safe zbiera wszystkie pliki w katalogu z enhanced memory management.
    """
    normalized_dir = normalize_path(directory)
    
    # Create thread-safe session
    session = ThreadSafeScanSession()
    logger.info(f"Starting scan session {session.session_id} for: {normalized_dir}")
    
    # THREAD-SAFE progress manager
    progress_manager = ThreadSafeProgressManager(progress_callback)
    
    # Cache check
    if not force_refresh:
        cached_file_map = cache.get_file_map(normalized_dir)
        if cached_file_map is not None:
            logger.debug(f"Session {session.session_id}: CACHE HIT for {normalized_dir}")
            progress_manager.report_progress(
                100, f"Używam cache dla {normalized_dir}", force=True
            )
            return cached_file_map

    # Validation
    if not path_exists(normalized_dir) or not os.path.isdir(normalized_dir):
        logger.warning(f"Session {session.session_id}: Directory {normalized_dir} nie istnieje")
        return {}

    file_map = defaultdict(list)
    session._start_time = time.time()
    
    try:
        # Enhanced memory management configuration
        memory_config = {
            'gc_interval': getattr(app_config, 'SCANNER_GC_INTERVAL', 1000),
            'progress_batch': getattr(app_config, 'SCANNER_PROGRESS_BATCH', 50),
            'subfolder_batch': getattr(app_config, 'SCANNER_SUBFOLDER_BATCH', 20)
        }
        
        _scan_directory_recursive(
            normalized_dir, 
            file_map, 
            session, 
            progress_manager,
            memory_config,
            max_depth, 
            interrupt_check
        )
        
    except ScanningInterrupted:
        logger.warning(f"Session {session.session_id}: Scanning interrupted by user")
        raise
    except MemoryError as e:
        logger.critical(f"Session {session.session_id}: Memory error during scanning: {e}")
        # Force garbage collection and re-raise
        import gc
        gc.collect()
        raise
    except Exception as e:
        logger.error(f"Session {session.session_id}: Unexpected error during scanning: {e}")
        raise
    finally:
        # CRITICAL: Always cleanup session resources
        session.cleanup()
        import gc
        gc.collect()  # Final cleanup
    
    # Final statistics and caching
    total_files, total_folders = session.get_stats()
    elapsed_time = time.time() - session._start_time
    
    _log_scan_completion(session.session_id, normalized_dir, total_files, total_folders, elapsed_time)
    
    # Save to cache
    if not force_refresh:
        cache.set_file_map(normalized_dir, file_map)
    
    progress_manager.report_progress(100, "Zakończono zbieranie plików", force=True)
    return file_map

# NOWA FUNKCJA: Dekompozycja _walk_directory_streaming
def _scan_directory_recursive(
    directory: str,
    file_map: Dict[str, List[str]],
    session: ThreadSafeScanSession,
    progress_manager: ThreadSafeProgressManager,
    memory_config: dict,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    depth: int = 0
):
    """Recursive directory scanning z proper error handling i memory management."""
    
    # Depth limit check
    if max_depth >= 0 and depth > max_depth:
        return
    
    # Thread-safe visited directory check
    normalized_dir = normalize_path(directory)
    if not session.add_visited_dir(normalized_dir):
        logger.warning(f"Session {session.session_id}: Loop detected in {normalized_dir}")
        return
    
    # Interrupt check
    if interrupt_check and interrupt_check():
        raise ScanningInterrupted(f"Scanning interrupted at {directory}")
    
    try:
        entries = list(os.scandir(directory))
        session.increment_counters(folders=1)
        
        # Smart pre-filtering
        relevant_files, relevant_subdirs = _filter_directory_entries(entries)
        
        # Process files
        files_processed = _process_directory_files(
            directory, relevant_files, file_map, session, 
            memory_config, interrupt_check
        )
        
        # Report progress
        total_files, total_folders = session.get_stats()
        progress_manager.report_progress(
            min(95, total_folders * 2),  # Improved progress calculation
            f"Skanowanie: {os.path.basename(directory)} "
            f"({total_files} plików, {total_folders} folderów)"
        )
        
        # Recursive scanning of subdirectories
        if relevant_subdirs:
            _scan_subdirectories(
                relevant_subdirs, file_map, session, progress_manager,
                memory_config, max_depth, interrupt_check, depth
            )
            
    except PermissionError as e:
        logger.warning(f"Session {session.session_id}: Permission denied {directory}: {e}")
    except FileNotFoundError as e:
        logger.warning(f"Session {session.session_id}: Directory removed during scan {directory}: {e}")
    except OSError as e:
        logger.error(f"Session {session.session_id}: I/O error accessing {directory}: {e}")
        # Continue with other directories
    except ScanningInterrupted:
        raise  # Propagate interruption
    except Exception as e:
        logger.error(f"Session {session.session_id}: Unexpected error in {directory}: {e}")
        # Continue scanning other directories

def _filter_directory_entries(entries) -> Tuple[List, List]:
    """Smart filtering of directory entries z early rejection."""
    relevant_files = []
    relevant_subdirs = []
    
    for entry in entries:
        if entry.is_file():
            _, ext = os.path.splitext(entry.name)
            if ext.lower() in SUPPORTED_EXTENSIONS:
                relevant_files.append(entry)
        elif entry.is_dir() and not should_ignore_folder(entry.name):
            relevant_subdirs.append(entry)
    
    return relevant_files, relevant_subdirs

def _process_directory_files(
    directory: str,
    relevant_files: List,
    file_map: Dict[str, List[str]],
    session: ThreadSafeScanSession,
    memory_config: dict,
    interrupt_check: Optional[Callable[[], bool]] = None
) -> int:
    """Process files w directory z memory management."""
    files_processed = 0
    
    for entry in relevant_files:
        # Batch interrupt checking
        if (files_processed % memory_config['progress_batch'] == 0 
            and interrupt_check and interrupt_check()):
            raise ScanningInterrupted(f"Interrupted while processing files in {directory}")
        
        # Process file
        name = entry.name
        base_name, ext = os.path.splitext(name)
        normalized_dir = normalize_path(directory)
        
        map_key = os.path.join(normalized_dir, base_name.lower())
        full_file_path = os.path.join(normalized_dir, name)
        file_map[map_key].append(full_file_path)
        
        files_processed += 1
        
        # Memory management
        if files_processed % memory_config['gc_interval'] == 0:
            import gc
            gc.collect()
    
    session.increment_counters(files=files_processed)
    return files_processed

def _scan_subdirectories(
    subdirs: List,
    file_map: Dict[str, List[str]],
    session: ThreadSafeScanSession,
    progress_manager: ThreadSafeProgressManager,
    memory_config: dict,
    max_depth: int,
    interrupt_check: Optional[Callable[[], bool]],
    depth: int
):
    """Scan subdirectories z batch interrupt checking."""
    subfolders_processed = 0
    
    for entry in subdirs:
        # Batch interrupt checking
        if (subfolders_processed % memory_config['subfolder_batch'] == 0
            and interrupt_check and interrupt_check()):
            raise ScanningInterrupted(f"Interrupted while scanning subdirectories")
        
        _scan_directory_recursive(
            entry.path, file_map, session, progress_manager,
            memory_config, max_depth, interrupt_check, depth + 1
        )
        
        subfolders_processed += 1

def _log_scan_completion(session_id: str, directory: str, total_files: int, total_folders: int, elapsed_time: float):
    """Standardized completion logging z performance metrics."""
    files_per_second = total_files / elapsed_time if elapsed_time > 0 else 0
    folders_per_second = total_folders / elapsed_time if elapsed_time > 0 else 0
    
    logger.info(
        f"SCAN_COMPLETED: Session {session_id} | {directory} | "
        f"files={total_files} | folders={total_folders} | "
        f"time={elapsed_time:.2f}s | "
        f"rate={files_per_second:.1f}files/s, {folders_per_second:.1f}folders/s"
    )
    
    # Performance warning dla slow scans
    if files_per_second < 100 and total_files > 500:
        logger.warning(
            f"SLOW_SCAN: Session {session_id} | {directory} | "
            f"rate={files_per_second:.1f}files/s (expected >100files/s for large folders)"
        )
```

---

### PATCH 2: ENHANCED PROGRESS CALCULATION I ACCURACY

**Problem:** Inaccurate progress calculation, aproksymacja nie odzwierciedla real progress
**Rozwiązanie:** Directory size estimation, accurate progress calculation based na estimated totals

```python
class ProgressEstimator:
    """Enhanced progress estimation based na directory analysis."""
    
    def __init__(self):
        self._estimated_total_files = 0
        self._estimated_total_folders = 0
        self._estimation_complete = False
    
    def quick_estimate(self, directory: str, max_sample_folders: int = 10) -> tuple:
        """Quick estimation of total files/folders by sampling."""
        if not os.path.isdir(directory):
            return 0, 0
        
        try:
            # Sample first few folders dla estimation
            sample_files = 0
            sample_folders = 0
            folders_sampled = 0
            
            for root, dirs, files in os.walk(directory):
                if folders_sampled >= max_sample_folders:
                    break
                
                # Filter relevant files
                relevant_files = [f for f in files 
                                if os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS]
                sample_files += len(relevant_files)
                sample_folders += 1
                folders_sampled += 1
                
                # Remove ignored folders from dirs to prevent os.walk from visiting them
                dirs[:] = [d for d in dirs if not should_ignore_folder(d)]
            
            # Estimate total based na sample
            if folders_sampled > 0:
                # Estimate total folders by extrapolating from sample
                try:
                    total_subdirs = sum(len(dirs) for _, dirs, _ in os.walk(directory))
                    avg_files_per_folder = sample_files / folders_sampled
                    estimated_files = int(avg_files_per_folder * total_subdirs)
                    estimated_folders = total_subdirs
                except:
                    # Fallback estimation
                    estimated_files = sample_files * 10  # Conservative estimate
                    estimated_folders = sample_folders * 10
            else:
                estimated_files = estimated_folders = 0
            
            self._estimated_total_files = estimated_files
            self._estimated_total_folders = estimated_folders
            self._estimation_complete = True
            
            logger.debug(
                f"Progress estimation: ~{estimated_files} files, ~{estimated_folders} folders"
            )
            
            return estimated_files, estimated_folders
            
        except Exception as e:
            logger.warning(f"Progress estimation failed: {e}")
            return 0, 0
    
    def calculate_progress(self, current_files: int, current_folders: int) -> int:
        """Calculate accurate progress percentage."""
        if not self._estimation_complete or self._estimated_total_files == 0:
            # Fallback to simple calculation
            return min(95, current_folders * 2)
        
        # Weight files more heavily than folders (files are primary goal)
        file_progress = (current_files / self._estimated_total_files) * 0.8
        folder_progress = (current_folders / self._estimated_total_folders) * 0.2
        
        total_progress = (file_progress + folder_progress) * 100
        return min(95, int(total_progress))  # Cap at 95% until completion

# MODYFIKACJA ThreadSafeProgressManager:
class EnhancedThreadSafeProgressManager(ThreadSafeProgressManager):
    """Enhanced progress manager z accurate calculation."""
    
    def __init__(self, progress_callback: Optional[Callable], throttle_interval: float = 0.1):
        super().__init__(progress_callback, throttle_interval)
        self.estimator = ProgressEstimator()
    
    def set_estimation(self, directory: str):
        """Initialize progress estimation dla directory."""
        self.estimator.quick_estimate(directory)
    
    def report_accurate_progress(self, current_files: int, current_folders: int, message: str):
        """Report progress z accurate calculation."""
        progress = self.estimator.calculate_progress(current_files, current_folders)
        self.report_progress(progress, message)

# ZMIENIĆ w collect_files_streaming:
def collect_files_streaming(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, List[str]]:
    """Enhanced collect_files_streaming z accurate progress estimation."""
    # ... existing code ...
    
    # Use enhanced progress manager
    progress_manager = EnhancedThreadSafeProgressManager(progress_callback)
    progress_manager.set_estimation(normalized_dir)  # Initialize estimation
    
    # ... rest of the function ...
    
    # W _scan_directory_recursive zmienić progress reporting:
    def _scan_directory_recursive(...):
        # ... existing code ...
        
        # Enhanced progress reporting
        total_files, total_folders = session.get_stats()
        progress_manager.report_accurate_progress(
            total_files, total_folders,
            f"Skanowanie: {os.path.basename(directory)} "
            f"({total_files} plików, {total_folders} folderów)"
        )
```

---

### PATCH 3: USUNIĘCIE DEAD CODE I CLEANUP COMMENTS

**Problem:** Dead code comments, outdated references, cleanup needed
**Rozwiązanie:** Remove comments about eliminated classes, cleanup obsolete references

```python
# USUNĄĆ następujące linie i komentarze:

# LINIA 56: USUNĄĆ
# ELIMINATED: ScanConfig dataclass - over-engineered wrapper dla parametrów funkcji

# LINIA 59: USUNĄĆ  
# ELIMINATED: ScanCacheManager - niepotrzebna abstrakcja, replaced by helper functions

# LINIA 182: USUNĄĆ
# ELIMINATED: ScanOrchestrator - over-engineered pattern, replaced by simplified scan_folder_for_pairs()

# LINIE 598-600: USUNĄĆ
# DEAD CODE REMOVED zgodnie z PATCH 6
# Note: find_special_folders() function has been removed as special folders
# are now handled through metadata system. Use _handle_special_folders_simple() instead.

# DODAĆ na początku pliku po imports:
"""
Enhanced scanner core module z optimized performance, thread safety, i accurate progress reporting.

Key optimizations:
- Thread-safe scanning sessions z proper resource management
- Accurate progress estimation based na directory sampling
- Enhanced memory management z configurable cleanup intervals
- Comprehensive error handling z recovery strategies
- Performance monitoring z business metrics

Performance targets:
- 100+ files/second dla folders >500 files
- <200MB memory usage per 10,000 files
- Thread-safe concurrent operations
- <5% progress calculation deviation
"""
```

---

### PATCH 4: ENHANCED ERROR HANDLING I LOGGING

**Problem:** Inconsistent logging levels, missing correlation, incomplete error recovery
**Rozwiązanie:** Standardized logging z session correlation, comprehensive error handling

```python
import sys
from enum import Enum

class ScanLogLevel(Enum):
    """Standardized logging levels dla scan operations."""
    TRACE = "TRACE"      # Bardzo szczegółowe debug info
    DEBUG = "DEBUG"      # Debugging info  
    INFO = "INFO"        # Normal operations
    WARNING = "WARNING"  # Recoverable errors
    ERROR = "ERROR"      # Serious errors
    CRITICAL = "CRITICAL" # Critical errors requiring attention

class ScanLogger:
    """Enhanced logger z session correlation i structured logging."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = logging.getLogger(__name__)
    
    def log(self, level: ScanLogLevel, message: str, **kwargs):
        """Log message z session correlation."""
        formatted_msg = f"[Session {self.session_id}] {message}"
        
        if kwargs:
            # Add structured data
            structured_data = " | ".join(f"{k}={v}" for k, v in kwargs.items())
            formatted_msg += f" | {structured_data}"
        
        log_method = getattr(self.logger, level.value.lower())
        log_method(formatted_msg)
    
    def trace(self, message: str, **kwargs):
        if self.logger.isEnabledFor(logging.DEBUG):  # Trace only w debug mode
            self.log(ScanLogLevel.TRACE, message, **kwargs)
    
    def performance(self, operation: str, duration: float, **metrics):
        """Log performance metrics."""
        self.log(ScanLogLevel.INFO, f"PERFORMANCE: {operation}", 
                duration=f"{duration:.2f}s", **metrics)
    
    def error_with_recovery(self, error: Exception, recovery_action: str, **context):
        """Log error z recovery information."""
        self.log(ScanLogLevel.ERROR, 
                f"Error: {str(error)} | Recovery: {recovery_action}", 
                error_type=type(error).__name__, **context)

# ZMIENIĆ ThreadSafeScanSession aby używał ScanLogger:
class ThreadSafeScanSession:
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.logger = ScanLogger(self.session_id)
        # ... rest of initialization ...
    
    def cleanup(self):
        """Enhanced cleanup z logging."""
        with self._lock:
            entries_cleaned = len(self._visited_dirs)
            self._visited_dirs.clear()
            self.logger.trace("Session cleanup completed", 
                            visited_dirs_cleaned=entries_cleaned)

# ZMIENIĆ error handling w _scan_directory_recursive:
def _scan_directory_recursive(...):
    session_logger = session.logger
    
    try:
        # ... existing scanning logic ...
        
    except PermissionError as e:
        session_logger.error_with_recovery(
            e, "Continue scanning other directories",
            directory=directory, depth=depth
        )
    except FileNotFoundError as e:
        session_logger.error_with_recovery(
            e, "Directory removed during scan, continuing",
            directory=directory, scan_time=time.time()
        )
    except OSError as e:
        session_logger.error_with_recovery(
            e, "I/O error, attempting to continue",
            directory=directory, error_code=getattr(e, 'errno', 'unknown')
        )
    except MemoryError as e:
        # Critical error - force cleanup and re-raise
        session_logger.log(ScanLogLevel.CRITICAL, 
                          "Memory exhausted during scanning",
                          directory=directory, 
                          memory_usage=_get_memory_usage())
        import gc
        gc.collect()
        raise
    except ScanningInterrupted:
        session_logger.log(ScanLogLevel.WARNING, "Scanning interrupted by user")
        raise
    except Exception as e:
        session_logger.error_with_recovery(
            e, "Unexpected error, continuing with other directories",
            directory=directory, depth=depth
        )

def _get_memory_usage() -> str:
    """Get current memory usage dla logging."""
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        return f"{memory_mb:.1f}MB"
    except ImportError:
        return "unavailable"
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - skanowanie folderów działa identycznie jak wcześniej
- [ ] **API kompatybilność** - collect_files_streaming(), scan_folder_for_pairs() API unchanged
- [ ] **Obsługa błędów** - comprehensive error handling z recovery strategies
- [ ] **Walidacja danych** - path validation i directory checks działają
- [ ] **Logowanie** - structured logging z session correlation nie spamuje
- [ ] **Konfiguracja** - app_config integration dla memory management settings
- [ ] **Cache** - scanner_cache integration maintained z proper lifecycle
- [ ] **Thread safety** - ThreadSafeScanSession eliminuje race conditions
- [ ] **Memory management** - configurable cleanup intervals, proper resource cleanup
- [ ] **Performance** - 100+ plików/s maintained, accurate progress reporting

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - wszystkie imports (file_pairing, metadata_manager, cache) działają
- [ ] **Zależności zewnętrzne** - threading, uuid, weakref used properly
- [ ] **Zależności wewnętrzne** - integration z scanning_service.py maintained
- [ ] **Cykl zależności** - no circular dependencies introduced
- [ ] **Backward compatibility** - wszystkie existing integrations działają
- [ ] **Interface contracts** - public function signatures unchanged
- [ ] **Event handling** - progress callbacks work properly
- [ ] **Signal/slot connections** - interrupt mechanism works
- [ ] **File I/O** - file system operations robust z error handling

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - wszystkie functions działają w izolacji
- [ ] **Test integracyjny** - integration z file pairing pipeline działa
- [ ] **Test regresyjny** - no functionality regressions
- [ ] **Test wydajnościowy** - 100+ files/s maintained, memory managed
- [ ] **Test thread safety** - concurrent scanning bez race conditions
- [ ] **Test error handling** - recovery z various error scenarios

#### **PERFORMANCE KRYTERIA:**

- [ ] **Scanning speed** - 100+ plików/s dla folders >500 files
- [ ] **Memory usage** - <200MB per 10,000 files, proper cleanup
- [ ] **Progress accuracy** - <5% deviation between reported i actual progress
- [ ] **Thread safety** - zero race conditions w concurrent operations
- [ ] **Error recovery** - 100% recovery from non-critical errors

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - wszystkie testy scanner core przechodzą
- [ ] **PERFORMANCE BUDGET** - wydajność maintained, memory managed
- [ ] **CODE COVERAGE** - coverage maintained lub improved
- [ ] **THREAD SAFETY** - concurrent scanning tests pass
- [ ] **ERROR HANDLING** - comprehensive recovery strategy tests pass