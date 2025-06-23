# PATCH-CODE DLA: SCANNER_CORE

**Powiązany plik z analizą:** `../corrections/scanner_core_correction.md`
**Zasady ogólne:** `../../_BASE_/refactoring_rules.md`

---

### PATCH 1: THREAD SAFETY FIX - PROGRESS REPORTING

**Problem:** Funkcja `_report_progress_with_throttling()` używa zmiennych `nonlocal` w sposób niebezpieczny dla wątków
**Rozwiązanie:** Wykorzystanie istniejącego `ThreadSafeProgressManager` zamiast lokalnych zmiennych

```python
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
            logger.debug(f"[{session_id}] CACHE HIT: używam buforowanych plików dla {normalized_dir}")
            progress_manager.report_progress(100, f"Używam cache dla {normalized_dir}", force=True)
            return cached_file_map

    if not path_exists(normalized_dir) or not os.path.isdir(normalized_dir):
        logger.warning(f"[{session_id}] Katalog {normalized_dir} nie istnieje lub nie jest katalogiem")
        progress_manager.report_progress(100, f"Katalog {normalized_dir} nie istnieje", force=True)
        return {}

    logger.info(f"[{session_id}] Rozpoczęto streaming zbieranie plików z katalogu: {normalized_dir}")
    progress_manager.report_progress(0, f"Rozpoczynam streaming skanowanie: {normalized_dir}")

    file_map = defaultdict(list)
    total_folders_scanned = 0
    total_files_found = 0
    start_time = time.time()

    # Thread-safe visited directories tracking
    visited_dirs = ThreadSafeVisitedDirs()

    # USUNIĘTO: _report_progress_with_throttling() - używamy progress_manager
    def report_scanning_progress():
        """Thread-safe progress reporting using centralized manager."""
        progress = min(95, int((total_files_found / max(1, total_folders_scanned)) * 10))
        progress_manager.report_progress(
            progress,
            f"Skanowanie: {os.path.basename(normalized_dir)} "
            f"({total_files_found} plików, {total_folders_scanned} folderów)"
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
            progress_manager,  # DODANE: przekazujemy progress_manager
        )

        # Report progress using centralized manager
        report_scanning_progress()

    except ScanningInterrupted:
        raise
    finally:
        visited_dirs.clear()
        logger.debug(f"[{session_id}] Cleaned up visited_dirs cache ({visited_dirs.size()} entries)")

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
```

---

### PATCH 2: THREADAFEVISITEDDIRS SIZE LIMITS

**Problem:** `ThreadSafeVisitedDirs` może rosnąć bez kontroli przy deep directory structures
**Rozwiązanie:** Dodanie size limits z automatic cleanup przy przekroczeniu

```python
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
```

---

### PATCH 3: KONSOLIDACJA PROGRESS REPORTING

**Problem:** Dwie implementacje progress reporting w tym samym pliku
**Rozwiązanie:** Usunięcie redundantnych zmiennych i funkcji, używanie tylko ThreadSafeProgressManager

```python
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
    progress_manager: Optional[ThreadSafeProgressManager] = None,  # DODANE
) -> Tuple[int, int]:
    """Decomposed directory walking function with centralized progress."""
    normalized_current_dir = normalize_path(current_dir)

    _check_interruption(interrupt_check, "przed przetwarzaniem katalogu")

    if max_depth >= 0 and depth > max_depth:
        return total_files_found, total_folders_scanned

    if visited_dirs.add(normalized_current_dir):
        logger.debug(f"[{session_id}] Wykryto pętlę w katalogach: {normalized_current_dir}")
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
            progress_manager,  # DODANE: przekazujemy dalej
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
                progress_manager,  # DODANE: przekazujemy dalej
            )

        # OPCIONAL: Periodic progress updates during deep scanning
        if progress_manager and total_folders_scanned % 100 == 0:
            progress = min(90, int((total_files_found / max(1, total_folders_scanned)) * 10))
            progress_manager.report_progress(
                progress,
                f"Głęboki scan: {total_files_found} plików w {total_folders_scanned} folderach"
            )

        logger.debug(f"[{session_id}] Skanowanie: {current_dir} -> {total_files_found} plików")

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

### PATCH 4: MEMORY MONITORING ENHANCEMENT

**Problem:** Memory cleanup nie raportuje memory usage przed cleanup
**Rozwiązanie:** Enhanced memory monitoring z detailed reporting

```python
def _perform_memory_cleanup(total_files_found: int, session_id: str, progress_manager: Optional[ThreadSafeProgressManager] = None):
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
                        force=True
                    )

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
```

---

### PATCH 5: PARAMETER OPTIMIZATION

**Problem:** Zbyt wiele parametrów w funkcjach helper (8+ parametrów wskazuje na poor cohesion)
**Rozwiązanie:** Dataclass dla grouping related parameters

```python
from dataclasses import dataclass
from typing import Optional, Callable, Dict, List

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

def _process_directory_entries(
    entries: List,
    current_dir: str,
    normalized_current_dir: str,
    file_map: Dict[str, List[str]],
    total_files_found: int,
    scan_context: ScanContext,  # GROUPED PARAMETERS
) -> Tuple[int, bool]:
    """Process directory entries with grouped parameters."""
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
        logger.debug(f"[{scan_context.session_id}] Pomijam folder bez relevant files: {current_dir}")
        return total_files_found, has_relevant_subdirs

    scan_context.check_interruption("smart filtering")

    # Process relevant files
    for entry in relevant_files:
        total_files_found = _handle_file_entry(
            entry,
            normalized_current_dir,
            file_map,
            total_files_found,
            scan_context,  # SIMPLIFIED PARAMETER
        )

    return total_files_found, has_relevant_subdirs

def _handle_file_entry(
    entry,
    normalized_current_dir: str,
    file_map: Dict[str, List[str]],
    total_files_found: int,
    scan_context: ScanContext,  # GROUPED PARAMETERS
) -> int:
    """Process single file entry with grouped parameters."""
    total_files_found += 1

    if total_files_found % 50 == 0:
        scan_context.check_interruption("przetwarzanie plików")

    name = entry.name
    base_name, ext = os.path.splitext(name)

    map_key = os.path.join(normalized_current_dir, base_name.lower())
    full_file_path = os.path.join(normalized_current_dir, name)
    file_map[map_key].append(full_file_path)

    # Memory cleanup with enhanced monitoring
    _perform_memory_cleanup(total_files_found, scan_context.session_id, scan_context.progress_manager)

    return total_files_found
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - `collect_files_streaming()` i `scan_folder_for_pairs()` działają identycznie
- [ ] **API kompatybilność** - wszystkie publiczne funkcje zachowują signature i behavior
- [ ] **Obsługa błędów** - exception handling nie zmieniony, thread safety enhanced
- [ ] **Walidacja danych** - path validation i directory existence checks preserved
- [ ] **Logowanie** - session-based logging z performance metrics maintained
- [ ] **Konfiguracja** - GC_INTERVAL_FILES i memory monitoring config preserved
- [ ] **Cache** - scanner_cache.py integration unchanged
- [ ] **Thread safety** - ThreadSafeProgressManager i ThreadSafeVisitedDirs enhanced
- [ ] **Memory management** - enhanced memory monitoring z size limits
- [ ] **Performance** - progress reporting optimization, parameter passing simplified

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - all imports preserved, added dataclass import
- [ ] **Zależności zewnętrzne** - psutil integration enhanced ale optional
- [ ] **Zależności wewnętrzne** - file_pairing.py, scanner_cache.py, metadata_manager.py unchanged
- [ ] **Cykl zależności** - no new circular dependencies introduced
- [ ] **Backward compatibility** - 100% API compatibility maintained
- [ ] **Interface contracts** - ThreadSafeProgressManager interface preserved
- [ ] **Event handling** - interrupt_check mechanism unchanged
- [ ] **Signal/slot connections** - progress_callback signature preserved
- [ ] **File I/O** - os.scandir usage i path operations unchanged

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - ThreadSafeVisitedDirs size limits, ThreadSafeProgressManager throttling
- [ ] **Test integracyjny** - integration z file_pairing.py, scanner_cache.py
- [ ] **Test regresyjny** - performance benchmark ≥1000 files/sec maintained
- [ ] **Test wydajnościowy** - memory usage <500MB dla large datasets verified

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - pytest scanner_core.py passes 100%
- [ ] **PERFORMANCE BUDGET** - scanning speed ≥1000 files/sec maintained
- [ ] **MEMORY BUDGET** - memory usage <500MB dla 10000+ files target met
- [ ] **THREAD SAFETY** - no race conditions w concurrent scanning operations