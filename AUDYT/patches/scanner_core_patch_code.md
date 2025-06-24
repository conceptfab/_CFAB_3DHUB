# PATCH-CODE DLA: SCANNER_CORE.PY

**Powiązany plik z analizą:** `../corrections/scanner_core_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: UI-AWARE PROGRESS MANAGER Z VIEWPORT TRACKING

**Problem:** ThreadSafeProgressManager nie uwzględnia aktualnego stanu UI i viewport galerii, co prowadzi do nieresponsywnego zachowania
**Rozwiązanie:** Dodanie viewport tracking i UI-aware progress reporting

```python
class UIAwareProgressManager:
    """Enhanced progress manager z UI viewport tracking dla responsywności galerii."""

    def __init__(
        self, 
        progress_callback: Optional[Callable], 
        throttle_interval: float = 0.05,  # Zmniejszone z 0.1s dla lepszej responsywności
        viewport_size: Optional[Tuple[int, int]] = None,
        ui_context: Optional[Dict] = None
    ):
        self.progress_callback = progress_callback
        self.throttle_interval = throttle_interval
        self.viewport_size = viewport_size or (800, 600)  # Default viewport
        self.ui_context = ui_context or {}
        self._lock = RLock()
        self._last_progress_time = 0.0
        self._last_percent = -1
        self._burst_mode = False  # Dla małych katalogów
        
    def set_viewport_size(self, width: int, height: int):
        """Aktualizacja viewport size dla adaptacyjnego progress reporting."""
        with self._lock:
            self.viewport_size = (width, height)
            # Adaptive throttling na podstawie viewport size
            viewport_area = width * height
            if viewport_area < 400000:  # Małe okno
                self.throttle_interval = 0.03  # Częstsze updaty
            else:
                self.throttle_interval = 0.05  # Standardowe
                
    def enable_burst_mode(self, total_files: int):
        """Burst mode dla małych katalogów - częstsze updaty UI."""
        with self._lock:
            self._burst_mode = total_files < 100
            if self._burst_mode:
                self.throttle_interval = 0.02  # Bardzo częste updaty dla małych katalogów

    def report_progress(self, percent: int, message: str, force: bool = False, current_file: Optional[str] = None):
        """UI-aware progress reporting z current file info."""
        if not self.progress_callback:
            return

        current_time = time.time()

        with self._lock:
            # Adaptive throttling
            adaptive_interval = self.throttle_interval
            if self._burst_mode:
                adaptive_interval *= 0.5  # Jeszcze częściej w burst mode
                
            # Throttling check
            if (
                not force
                and current_time - self._last_progress_time < adaptive_interval
                and abs(percent - self._last_percent) < (2 if self._burst_mode else 5)
            ):
                return

            self._last_progress_time = current_time
            self._last_percent = percent

        # Extended callback z UI context
        try:
            callback_data = {
                'percent': percent,
                'message': message,
                'current_file': current_file,
                'viewport_size': self.viewport_size,
                'burst_mode': self._burst_mode,
                'ui_context': self.ui_context
            }
            
            # Support both old and new callback signatures
            if hasattr(self.progress_callback, '__code__') and self.progress_callback.__code__.co_argcount > 2:
                self.progress_callback(percent, message, callback_data)
            else:
                self.progress_callback(percent, message)
                
        except Exception as e:
            logger.warning(f"UI-aware progress callback error: {e}")

    def create_viewport_scaled_callback(self, scale_factor: float = 0.5) -> Optional[Callable]:
        """Tworzy callback ze skalowaniem i viewport awareness."""
        if not self.progress_callback:
            return None

        def viewport_scaled_progress(percent, message, current_file=None):
            scaled_percent = int(percent * scale_factor)
            self.report_progress(scaled_percent, message, current_file=current_file)

        return viewport_scaled_progress
```

---

### PATCH 2: SIMPLIFIED THREAD-SAFE VISITED DIRS Z MEMORY LIMITS

**Problem:** ThreadSafeVisitedDirs zbyt skomplikowane i może prowadzić do memory overflow
**Rozwiązanie:** Uproszczenie z lepszym memory management

```python
class SimplifiedVisitedDirs:
    """Uproszczona wersja visited directories tracking z predictable memory usage."""

    def __init__(self, max_size: int = 10000):  # Zmniejszone z 50000
        self._visited = set()
        self._lock = RLock()
        self._max_size = max_size
        self._cleanup_counter = 0
        
    def add(self, directory: str) -> bool:
        """Add directory, return True if already visited. Memory-safe."""
        with self._lock:
            if directory in self._visited:
                return True
            
            # Simple size-based cleanup
            if len(self._visited) >= self._max_size:
                self._simple_cleanup()
            
            self._visited.add(directory)
            return False

    def _simple_cleanup(self):
        """Simple FIFO-like cleanup - remove random 40% of entries."""
        old_size = len(self._visited)
        # Convert to list, keep first 60%
        visited_list = list(self._visited)
        keep_count = int(len(visited_list) * 0.6)
        self._visited = set(visited_list[:keep_count])
        
        logger.debug(f"SimplifiedVisitedDirs cleanup: {old_size} -> {len(self._visited)} entries")

    def clear(self):
        """Clear all visited directories."""
        with self._lock:
            self._visited.clear()

    def size(self) -> int:
        """Get number of visited directories."""
        with self._lock:
            return len(self._visited)
```

---

### PATCH 3: ADAPTIVE PROGRESS REPORTING Z UI FEEDBACK

**Problem:** Progress reporting nie dostosowuje się do aktualnego stanu UI galerii
**Rozwiązanie:** Implementacja adaptive reporting z UI feedback

```python
def _handle_file_entry_ui_aware(
    entry,
    normalized_current_dir: str,
    file_map: Dict[str, List[str]],
    total_files_found: int,
    ui_progress_manager: UIAwareProgressManager,
    scan_context: ScanContext,
) -> int:
    """Enhanced file entry processing z UI awareness."""
    total_files_found += 1
    
    # Adaptive interruption check frequency
    check_frequency = 25 if ui_progress_manager._burst_mode else 50
    if total_files_found % check_frequency == 0:
        scan_context.check_interruption("UI-aware file processing")

    name = entry.name
    base_name, ext = os.path.splitext(name)

    # Optimized key generation (unchanged)
    map_key = os.path.join(normalized_current_dir, base_name.lower())
    full_file_path = os.path.join(normalized_current_dir, name)
    file_map[map_key].append(full_file_path)

    # UI-aware progress reporting
    if total_files_found % (10 if ui_progress_manager._burst_mode else 50) == 0:
        ui_progress_manager.report_progress(
            percent=min(90, int((total_files_found / 100) * 5)),  # Adaptive scaling
            message=f"Przetwarzanie: {os.path.basename(name)}",
            current_file=name
        )

    # Adaptive memory cleanup
    _perform_adaptive_memory_cleanup(total_files_found, scan_context.session_id, ui_progress_manager)

    return total_files_found


def _perform_adaptive_memory_cleanup(
    total_files_found: int, 
    session_id: str, 
    ui_progress_manager: UIAwareProgressManager
):
    """Adaptive memory cleanup na podstawie viewport size i UI state."""
    # Adaptive GC interval na podstawie viewport i burst mode
    viewport_area = ui_progress_manager.viewport_size[0] * ui_progress_manager.viewport_size[1]
    
    if viewport_area < 400000:  # Małe okno
        gc_interval = 500  # Częściej dla małych okien
    elif ui_progress_manager._burst_mode:
        gc_interval = 200  # Bardzo często dla małych katalogów
    else:
        gc_interval = 1000  # Standard
    
    if total_files_found % gc_interval == 0:
        initial_memory = _get_memory_usage()
        collected = gc.collect()
        final_memory = _get_memory_usage()
        
        if initial_memory > 0:
            memory_freed = initial_memory - final_memory
            logger.debug(
                f"[{session_id}] Adaptive memory cleanup at {total_files_found} files: "
                f"RAM: {initial_memory}MB -> {final_memory}MB (freed: {memory_freed}MB) | "
                f"Viewport: {ui_progress_manager.viewport_size} | "
                f"Burst mode: {ui_progress_manager._burst_mode}"
            )
            
            # UI feedback dla high memory usage
            if final_memory > 300:  # Niższy próg dla UI feedback
                ui_progress_manager.report_progress(
                    percent=-1,  # Special value for memory warnings
                    message=f"Optymalizacja pamięci: {final_memory}MB",
                    force=True
                )
```

---

### PATCH 4: ENHANCED SCAN_FOLDER_FOR_PAIRS Z UI AWARENESS

**Problem:** Główna funkcja skanowania nie uwzględnia stanu UI
**Rozwiązanie:** UI-aware scanning z viewport i responsywność

```python
def scan_folder_for_pairs_ui_aware(
    directory: str,
    max_depth: int = -1,
    use_cache: bool = True,
    pair_strategy: str = "first_match",
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh_cache: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    viewport_size: Optional[Tuple[int, int]] = None,
    ui_context: Optional[Dict] = None,
) -> Tuple[List[FilePair], List[str], List[str], List[SpecialFolder]]:
    """
    UI-AWARE scanning z viewport tracking i responsive progress.
    
    Args:
        viewport_size: (width, height) aktualnego viewport galerii
        ui_context: Dodatkowy context z UI (np. visible_files, gallery_state)
    """
    normalized_dir = normalize_path(directory)
    
    # UI-aware progress manager
    ui_progress_manager = UIAwareProgressManager(
        progress_callback=progress_callback,
        viewport_size=viewport_size,
        ui_context=ui_context
    )

    # Quick estimation dla burst mode
    try:
        quick_count = sum(1 for _ in os.scandir(normalized_dir) if _.is_file())
        ui_progress_manager.enable_burst_mode(quick_count)
    except:
        pass  # Fallback to normal mode

    # 1. Check cache z UI feedback
    cached_result = _get_cached_scan_result(
        normalized_dir, pair_strategy, use_cache, force_refresh_cache, ui_progress_manager
    )
    if cached_result:
        return cached_result

    # 2. Validate directory z UI feedback
    if not path_exists(normalized_dir) or not os.path.isdir(normalized_dir):
        logger.warning(f"Katalog {normalized_dir} nie istnieje")
        ui_progress_manager.report_progress(100, "Katalog nie istnieje", force=True)
        return [], [], [], []

    # 3. UI-aware file collection
    ui_progress_manager.report_progress(5, "Rozpoczynam skanowanie plików...")
    
    # Enhanced collect_files_streaming z UI awareness
    file_map = collect_files_streaming_ui_aware(
        normalized_dir,
        max_depth,
        interrupt_check,
        force_refresh_cache,
        ui_progress_manager
    )

    # 4. Create file pairs z progress
    ui_progress_manager.report_progress(50, "Tworzenie par plików...")
    file_pairs, processed_files = create_file_pairs(
        file_map, base_directory=normalized_dir, pair_strategy=pair_strategy
    )

    # 5. Identify unpaired files z progress
    ui_progress_manager.report_progress(70, "Identyfikacja nieparowanych plików...")
    unpaired_archives, unpaired_previews = identify_unpaired_files(
        file_map, processed_files
    )

    # 6. Handle special folders z progress
    ui_progress_manager.report_progress(85, "Obsługa folderów specjalnych...")
    special_folders = _handle_special_folders_simple(normalized_dir)

    # 7. Final result z UI feedback
    result = (file_pairs, unpaired_archives, unpaired_previews, special_folders)
    _save_scan_result(normalized_dir, pair_strategy, result, use_cache)

    ui_progress_manager.report_progress(
        100, 
        f"Ukończono: {len(file_pairs)} par, viewport: {viewport_size}", 
        force=True
    )
    
    logger.info(
        f"UI-aware scanning completed for {normalized_dir}. "
        f"Found {len(file_pairs)} pairs. Viewport: {viewport_size}"
    )

    return result


def collect_files_streaming_ui_aware(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    ui_progress_manager: UIAwareProgressManager = None,
) -> Dict[str, List[str]]:
    """UI-aware streaming file collection z responsive progress."""
    session_id = uuid.uuid4().hex[:8]
    normalized_dir = normalize_path(directory)

    # Cache check z UI feedback
    if not force_refresh:
        cached_file_map = cache.get_file_map(normalized_dir)
        if cached_file_map is not None:
            logger.debug(f"[{session_id}] UI-AWARE CACHE HIT for {normalized_dir}")
            ui_progress_manager.report_progress(100, f"Cache hit: {normalized_dir}", force=True)
            return cached_file_map

    logger.info(f"[{session_id}] UI-aware streaming collection: {normalized_dir}")
    ui_progress_manager.report_progress(0, f"UI-aware scan: {normalized_dir}")

    file_map = defaultdict(list)
    total_folders_scanned = 0
    total_files_found = 0
    start_time = time.time()

    # Simplified visited directories
    visited_dirs = SimplifiedVisitedDirs(max_size=5000)  # Smaller for UI responsiveness

    # UI-aware scan context
    scan_context = ScanContext(
        session_id=session_id,
        interrupt_check=interrupt_check,
        progress_manager=ui_progress_manager,
        visited_dirs=visited_dirs
    )

    try:
        total_files_found, total_folders_scanned = _walk_directory_ui_aware(
            normalized_dir,
            0,
            max_depth,
            scan_context,
            file_map,
            total_files_found,
            total_folders_scanned,
        )

    except ScanningInterrupted:
        ui_progress_manager.report_progress(0, "Skanowanie przerwane", force=True)
        raise
    finally:
        visited_dirs.clear()

    elapsed_time = time.time() - start_time
    files_per_second = total_files_found / elapsed_time if elapsed_time > 0 else 0

    logger.info(
        f"[{session_id}] UI-AWARE SCAN COMPLETED: {normalized_dir} | "
        f"files={total_files_found} | time={elapsed_time:.2f}s | "
        f"rate={files_per_second:.1f}files/s | viewport={ui_progress_manager.viewport_size}"
    )

    if not force_refresh:
        cache.set_file_map(normalized_dir, file_map)

    ui_progress_manager.report_progress(100, "UI-aware scanning completed", force=True)
    return file_map


def _walk_directory_ui_aware(
    current_dir: str,
    depth: int,
    max_depth: int,
    scan_context: ScanContext,
    file_map: Dict[str, List[str]],
    total_files_found: int,
    total_folders_scanned: int,
) -> Tuple[int, int]:
    """UI-aware directory walking z responsive progress."""
    normalized_current_dir = normalize_path(current_dir)
    
    scan_context.check_interruption("UI-aware directory processing")

    if max_depth >= 0 and depth > max_depth:
        return total_files_found, total_folders_scanned

    if scan_context.visited_dirs.add(normalized_current_dir):
        logger.debug(f"[{scan_context.session_id}] UI-aware: Skip visited {normalized_current_dir}")
        return total_files_found, total_folders_scanned

    try:
        total_folders_scanned += 1
        entries = list(os.scandir(current_dir))

        # UI-aware file processing
        for entry in entries:
            if entry.is_file():
                _, ext = os.path.splitext(entry.name)
                if ext.lower() in SUPPORTED_EXTENSIONS:
                    total_files_found = _handle_file_entry_ui_aware(
                        entry,
                        normalized_current_dir,
                        file_map,
                        total_files_found,
                        scan_context.progress_manager,
                        scan_context,
                    )

        # UI-aware subdirectory scanning
        for entry in entries:
            if entry.is_dir() and not should_ignore_folder(entry.name):
                new_files, new_folders = _walk_directory_ui_aware(
                    entry.path,
                    depth + 1,
                    max_depth,
                    scan_context,
                    file_map,
                    total_files_found,
                    total_folders_scanned,
                )
                total_files_found = new_files
                total_folders_scanned = new_folders

        # UI-aware periodic progress
        if total_folders_scanned % 50 == 0:  # Częściej dla UI responsiveness
            progress = min(90, int((total_files_found / max(1, total_folders_scanned)) * 5))
            scan_context.progress_manager.report_progress(
                progress,
                f"UI-aware: {total_files_found} plików",
                current_file=os.path.basename(current_dir)
            )

    except (PermissionError, FileNotFoundError, OSError) as e:
        logger.debug(f"[{scan_context.session_id}] UI-aware access error {current_dir}: {e}")
    except ScanningInterrupted:
        raise
    except Exception as e:
        logger.error(f"[{scan_context.session_id}] UI-aware unexpected error {current_dir}: {e}")

    return total_files_found, total_folders_scanned
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - skanowanie katalogów działa poprawnie
- [ ] **API kompatybilność** - scan_folder_for_pairs zachowuje kompatybilność wsteczną
- [ ] **Obsługa błędów** - ScanningInterrupted i inne exceptions działają
- [ ] **Walidacja danych** - sprawdzanie ścieżek i parametrów
- [ ] **Logowanie** - system logowania działa bez spamowania
- [ ] **Konfiguracja** - odczytywanie cache settings i limits
- [ ] **Cache** - mechanizmy cache'owania działają z nową logiką
- [ ] **Thread safety** - UIAwareProgressManager jest thread-safe
- [ ] **Memory management** - adaptive memory cleanup działa
- [ ] **Performance** - wydajność skanowania zachowana lub lepsza

#### **UI RESPONSYWNOŚĆ DO WERYFIKACJI:**

- [ ] **Viewport tracking** - progress manager śledzi rozmiar viewport
- [ ] **Adaptive throttling** - progress updates dostosowują się do UI
- [ ] **Burst mode** - małe katalogi mają częstsze updates
- [ ] **Memory optimization** - GC dostosowuje się do viewport size
- [ ] **Current file reporting** - UI otrzymuje info o aktualnie przetwarzanym pliku
- [ ] **Gallery responsiveness** - galeria nie znika przy resize
- [ ] **Progress smoothness** - progress bar działa płynnie

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - wszystkie imports działają z nową strukturą
- [ ] **file_pairing.py** - integracja z create_file_pairs działa
- [ ] **metadata_manager.py** - MetadataManager.get_instance() działa
- [ ] **scanner_cache.py** - cache operations działają
- [ ] **gallery_tab.py** - integracja z progress callback
- [ ] **file_tile_widget.py** - nowe progress info nie psuje kafli
- [ ] **Thread coordination** - interrupt_check mechanizm działa
- [ ] **UI event loop** - progress callbacks nie blokują UI

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test UI responsiveness** - galeria pozostaje responsywna podczas skanowania dużego katalogu
- [ ] **Test viewport adaptation** - progress dostosowuje się do zmiany rozmiaru okna
- [ ] **Test burst mode** - małe katalogi (<100 plików) używają burst mode
- [ ] **Test memory limits** - adaptive cleanup zapobiega memory overflow
- [ ] **Test interruption** - przerwanie skanowania działa z nową logiką
- [ ] **Test backward compatibility** - stare wywołania scan_folder_for_pairs działają

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - wszystkie testy automatyczne przechodzą
- [ ] **UI RESPONSIVENESS** - galeria nie znika przy resize, progress płynny
- [ ] **PERFORMANCE BUDGET** - skanowanie nie wolniejsze niż 5%
- [ ] **MEMORY BUDGET** - zużycie pamięci nie wyższe o więcej niż 10%
- [ ] **BACKWARD COMPATIBILITY** - 100% kompatybilność z istniejącym API