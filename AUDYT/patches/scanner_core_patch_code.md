# PATCH-CODE DLA: SCANNER_CORE.PY

**Powiązany plik z analizą:** `../corrections/scanner_core_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: Thread Safety Fix w ThreadSafeVisitedDirs

**Problem:** random.shuffle() w _perform_cleanup() nie jest thread-safe i może powodować nieprzewidywalne zachowanie
**Rozwiązanie:** Implementacja LRU-based cleanup z thread-safe ordenowaniem

```python
class ThreadSafeVisitedDirs:
    """Thread-safe visited directories tracking z size limits."""

    def __init__(self, max_size: int = 50000):
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
```

---

### PATCH 2: Async Progress Callback Wrapper

**Problem:** Progress callback może blokować UI gdy wywoływany z wątku roboczego
**Rozwiązanie:** Non-blocking callback wrapper z queue-based communication

```python
import queue
import threading
from typing import Callable, Optional

class AsyncProgressManager:
    """Non-blocking progress manager with async callback."""
    
    def __init__(self, progress_callback: Optional[Callable], throttle_interval: float = 0.1):
        self.original_callback = progress_callback
        self.throttle_interval = throttle_interval
        self._lock = RLock()
        self._last_progress_time = 0.0
        self._last_percent = -1
        
        # Async callback queue
        self._callback_queue = queue.Queue(maxsize=10)  # Limit queue size
        self._stop_event = threading.Event()
        
        if progress_callback:
            self._callback_thread = threading.Thread(
                target=self._callback_worker, 
                daemon=True
            )
            self._callback_thread.start()

    def _callback_worker(self):
        """Background thread for non-blocking callback execution."""
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
        """Non-blocking progress reporting."""
        if not self.original_callback:
            return

        current_time = time.time()

        with self._lock:
            if (
                not force
                and current_time - self._last_progress_time < self.throttle_interval
                and abs(percent - self._last_percent) < 5
            ):
                return

            self._last_progress_time = current_time
            self._last_percent = percent

        # Non-blocking queue put
        try:
            self._callback_queue.put_nowait((percent, message))
        except queue.Full:
            # Drop progress update if queue is full to prevent blocking
            logger.debug("Progress queue full, dropping update")

    def shutdown(self):
        """Cleanup async callback thread."""
        if hasattr(self, '_stop_event'):
            self._stop_event.set()
        if hasattr(self, '_callback_thread'):
            self._callback_thread.join(timeout=1.0)
```

---

### PATCH 3: Adaptive Memory Cleanup

**Problem:** Fixed GC_INTERVAL_FILES = 1000 może być nieefektywny dla różnych rozmiarów folderów
**Rozwiązanie:** Adaptive GC intervals based on memory usage and file count

```python
class AdaptiveMemoryManager:
    """Adaptive memory management with smart GC intervals."""
    
    def __init__(self):
        self.base_gc_interval = 1000
        self.max_gc_interval = 5000
        self.min_gc_interval = 100
        self.memory_threshold_mb = 400
        self.last_gc_files = 0
        self.last_memory_usage = 0

    def should_perform_gc(self, total_files_found: int) -> bool:
        """Determine if GC should be performed based on adaptive criteria."""
        current_memory = self._get_memory_usage()
        files_since_gc = total_files_found - self.last_gc_files
        
        # Force GC if memory usage is high
        if current_memory > self.memory_threshold_mb:
            return True
            
        # Calculate adaptive interval based on memory growth rate
        memory_growth = current_memory - self.last_memory_usage
        if memory_growth > 0:
            # More frequent GC if memory is growing fast
            adaptive_interval = max(
                self.min_gc_interval,
                self.base_gc_interval - (memory_growth * 10)
            )
        else:
            # Less frequent GC if memory is stable
            adaptive_interval = min(self.max_gc_interval, self.base_gc_interval * 1.5)
        
        return files_since_gc >= adaptive_interval

    def perform_cleanup(self, total_files_found: int, session_id: str, 
                       progress_manager: Optional[AsyncProgressManager] = None):
        """Enhanced memory cleanup with adaptive intervals."""
        if not self.should_perform_gc(total_files_found):
            return
            
        initial_memory = self._get_memory_usage()
        collected = gc.collect()
        final_memory = self._get_memory_usage()
        
        # Update tracking
        self.last_gc_files = total_files_found
        self.last_memory_usage = final_memory
        
        # Simplified logging for production
        if final_memory > 500:  # Only log warnings
            logger.warning(
                f"[{session_id}] HIGH_MEMORY: {final_memory}MB at {total_files_found} files"
            )
        else:
            logger.debug(
                f"[{session_id}] GC: {initial_memory}MB->{final_memory}MB, "
                f"collected={collected}, files={total_files_found}"
            )

# Global adaptive memory manager instance
_adaptive_memory_manager = AdaptiveMemoryManager()

def _perform_memory_cleanup(total_files_found: int, session_id: str, 
                           progress_manager: Optional[AsyncProgressManager] = None):
    """Use adaptive memory manager instead of fixed intervals."""
    _adaptive_memory_manager.perform_cleanup(total_files_found, session_id, progress_manager)
```

---

### PATCH 4: I/O Timeout Handling

**Problem:** Brak timeout w operacjach I/O może powodować zawieszanie na wolnych dyskach
**Rozwiązanie:** Timeout wrapper dla scandir operations

```python
import signal
from contextlib import contextmanager

@contextmanager
def io_timeout(timeout_seconds: int = 30):
    """Context manager for I/O operations with timeout."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"I/O operation timed out after {timeout_seconds} seconds")
    
    # Set the signal handler and a timeout alarm
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        yield
    finally:
        # Disable the alarm
        signal.alarm(0)
        # Restore the old signal handler
        signal.signal(signal.SIGALRM, old_handler)

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
        logger.debug(f"[{session_id}] Wykryto pętlę w katalogach: {normalized_current_dir}")
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
        
        # ... rest of the function remains the same ...
        
    except (PermissionError, FileNotFoundError, OSError) as e:
        logger.debug(f"[{session_id}] Błąd dostępu do {current_dir}: {e}")
    except MemoryError as e:
        logger.critical(f"[{session_id}] Brak pamięci podczas skanowania {current_dir}: {e}")
        raise
    except ScanningInterrupted:
        raise
    except Exception as e:
        logger.error(f"[{session_id}] Nieoczekiwany błąd w katalogu {current_dir}: {e}")

    return total_files_found, total_folders_scanned
```

---

### PATCH 5: Production Logging Optimization

**Problem:** Zbyt dużo DEBUG logs może spowalniać skanowanie w production
**Rozwiązanie:** Smart logging z rate limiting i poziom-aware messaging

```python
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

# Create rate-limited logger instance
rate_limited_logger = RateLimitedLogger(logger, rate_limit_seconds=2.0)

# Replace debug logging calls in scanning functions
def _walk_directory_streaming(
    # ... parameters ...
) -> Tuple[int, int]:
    """Enhanced directory walking with optimized logging."""
    # Replace:
    # logger.debug(f"[{session_id}] Skanowanie: {current_dir} -> {total_files_found} plików")
    # With:
    rate_limited_logger.debug_throttled(
        f"[{session_id}] Skanowanie: {current_dir} -> {total_files_found} plików",
        key=f"scan_progress_{session_id}"
    )
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - skanowanie folderów działa dla 10,000+ plików
- [ ] **API kompatybilność** - collect_files_streaming(), scan_folder_for_pairs() zachowują interfejs
- [ ] **Obsługa błędów** - timeout handling, memory errors, permission errors
- [ ] **Walidacja danych** - path validation, directory existence checks
- [ ] **Logowanie** - rate-limited logging nie spamuje w production
- [ ] **Konfiguracja** - cache configuration, memory limits działają
- [ ] **Cache** - scanner_cache integration działa poprawnie
- [ ] **Thread safety** - ThreadSafeVisitedDirs z LRU cleanup jest thread-safe
- [ ] **Memory management** - adaptive GC prevents memory leaks <500MB
- [ ] **Performance** - 1000+ plików/sek zachowane lub poprawione

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - wszystkie importy działają (queue, threading, signal)
- [ ] **Zależności zewnętrzne** - psutil optional dependency
- [ ] **Zależności wewnętrzne** - file_pairing.py, scanner_cache.py integration
- [ ] **Cykl zależności** - brak cyklicznych importów
- [ ] **Backward compatibility** - 100% kompatybilność API
- [ ] **Interface contracts** - progress_callback signature zachowany
- [ ] **Event handling** - interrupt_check funkcjonalność zachowana
- [ ] **Signal/slot connections** - async progress nie blokuje UI
- [ ] **File I/O** - I/O timeout protection działa

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - ThreadSafeVisitedDirs, AsyncProgressManager
- [ ] **Test integracyjny** - skanowanie z file_pairing.py
- [ ] **Test regresyjny** - benchmark względem oryginalnej wersji
- [ ] **Test wydajnościowy** - 10,000 plików w <10 sekund
- [ ] **Test thread safety** - równoczesne skanowanie 3 folderów
- [ ] **Test memory** - <500MB dla 50,000 plików
- [ ] **Test timeout** - skanowanie folderów sieciowych z timeout

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - wszystkie testy muszą przejść
- [ ] **PERFORMANCE BUDGET** - 1000+ plików/sek, <500MB RAM
- [ ] **CODE COVERAGE** - pokrycie kodu nie spadło poniżej 80%
- [ ] **THREAD SAFETY** - brak race conditions w multi-threaded environment
- [ ] **UI RESPONSIVENESS** - progress callback nie blokuje UI