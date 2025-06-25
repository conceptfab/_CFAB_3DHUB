# PATCH-CODE DLA: SCANNER_CORE.PY

**Powiązany plik z analizą:** `../corrections/scanner_core_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: OPTYMALIZACJA ADAPTIVE MEMORY MANAGER

**Problem:** memory_threshold_mb=400 zbyt niski, powoduje HIGH_MEMORY warnings przy normalnym użyciu
**Rozwiązanie:** Zwiększenie thresholds i dodanie adaptive scaling

```python
# PRZED (line 288-298):
class AdaptiveMemoryManager:
    def __init__(self):
        self.base_gc_interval = 1000
        self.max_gc_interval = 5000
        self.min_gc_interval = 100
        self.memory_threshold_mb = 400  # ← PROBLEM: Za niski threshold
        self.last_gc_files = 0
        self.last_memory_usage = 0

# PO:
class AdaptiveMemoryManager:
    def __init__(self):
        self.base_gc_interval = 500  # Zmniejszono z 1000
        self.max_gc_interval = 3000  # Zmniejszono z 5000
        self.min_gc_interval = 50   # Zmniejszono z 100
        self.memory_threshold_mb = 800  # ZWIĘKSZONO z 400 do 800MB
        self.critical_threshold_mb = 1200  # NOWY: Critical threshold
        self.last_gc_files = 0
        self.last_memory_usage = 0
        # NOWY: Adaptive scaling based on system memory
        try:
            import psutil
            total_memory_gb = psutil.virtual_memory().total / (1024**3)
            if total_memory_gb >= 16:
                self.memory_threshold_mb = 1000
                self.critical_threshold_mb = 1500
            elif total_memory_gb >= 8:
                self.memory_threshold_mb = 800
                self.critical_threshold_mb = 1200
            else:
                self.memory_threshold_mb = 600
                self.critical_threshold_mb = 900
        except:
            pass  # Fallback to default values
```

---

### PATCH 2: ULEPSZENIE THREADSAFE VISITED DIRS

**Problem:** max_size=50000 powoduje memory overhead ~100MB, LRU algorithm nieefektywny
**Rozwiązanie:** Zmniejszenie rozmiaru i optymalizacja LRU

```python
# PRZED (line 226-235):
class ThreadSafeVisitedDirs:
    def __init__(self, max_size: int = 50000):  # ← PROBLEM: Za duży rozmiar
        self._visited = {}
        self._access_counter = 0
        self._lock = RLock()
        self._max_size = max_size
        self._cleanup_threshold = int(max_size * 0.8)

# PO:
class ThreadSafeVisitedDirs:
    def __init__(self, max_size: int = 10000):  # ZMNIEJSZONO z 50000 do 10000
        self._visited = {}
        self._access_counter = 0
        self._lock = RLock()
        self._max_size = max_size
        self._cleanup_threshold = int(max_size * 0.7)  # ZMIENIONO z 0.8 do 0.7
        # NOWY: Track access frequency for better LRU
        self._access_frequency = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 30.0  # Cleanup co 30 sekund

    def _perform_lru_cleanup(self):
        """Enhanced LRU cleanup with frequency tracking."""
        current_time = time.time()
        
        # Combine access counter with frequency for better LRU
        scored_items = []
        for path, access_counter in self._visited.items():
            frequency = self._access_frequency.get(path, 1)
            # Score = recent access + frequency bonus
            score = access_counter + (frequency * 1000)
            scored_items.append((path, score))
        
        # Sort by score (higher = more recently/frequently used)
        scored_items.sort(key=lambda x: x[1], reverse=True)
        
        # Keep top 60% 
        keep_count = int(len(scored_items) * 0.6)
        new_visited = {}
        new_frequency = {}
        
        for path, score in scored_items[:keep_count]:
            new_visited[path] = self._visited[path]
            new_frequency[path] = self._access_frequency.get(path, 1)
        
        self._visited = new_visited
        self._access_frequency = new_frequency
        self._last_cleanup = current_time
        
        logger.debug(
            f"Enhanced LRU cleanup: {len(scored_items)} → {len(new_visited)} entries"
        )

    def add(self, directory: str) -> bool:
        """Enhanced add with frequency tracking."""
        with self._lock:
            current_time = time.time()
            
            if directory in self._visited:
                # Update access counter and frequency
                self._access_counter += 1
                self._visited[directory] = self._access_counter
                self._access_frequency[directory] = self._access_frequency.get(directory, 0) + 1
                return True

            # Cleanup if needed
            if (len(self._visited) >= self._max_size or 
                current_time - self._last_cleanup > self._cleanup_interval):
                self._perform_lru_cleanup()

            self._access_counter += 1
            self._visited[directory] = self._access_counter
            self._access_frequency[directory] = 1
            return False
```

---

### PATCH 3: OPTYMALIZACJA ASYNC PROGRESS MANAGER

**Problem:** queue.Queue(maxsize=10) powoduje dropped updates, brak backpressure handling
**Rozwiązanie:** Adaptive queue sizing i lepsze throttling

```python
# PRZED (line 120-142):
class AsyncProgressManager:
    def __init__(
        self, progress_callback: Optional[Callable], throttle_interval: float = 0.1
    ):
        self.original_callback = progress_callback
        self.throttle_interval = throttle_interval
        self._lock = RLock()
        self._last_progress_time = 0.0
        self._last_percent = -1

        # Async callback queue
        self._callback_queue = queue.Queue(maxsize=10)  # ← PROBLEM: Za mały queue

# PO:
class AsyncProgressManager:
    def __init__(
        self, progress_callback: Optional[Callable], throttle_interval: float = 0.1
    ):
        self.original_callback = progress_callback
        self.throttle_interval = throttle_interval
        self._lock = RLock()
        self._last_progress_time = 0.0
        self._last_percent = -1

        # ADAPTIVE queue sizing based on expected load
        base_queue_size = 50  # Zwiększono z 10 do 50
        self._callback_queue = queue.Queue(maxsize=base_queue_size)
        
        # NOWY: Backpressure monitoring
        self._dropped_updates = 0
        self._total_updates = 0
        self._last_stats_log = time.time()
        
        # NOWY: Adaptive throttling
        self._dynamic_throttle = throttle_interval
        self._performance_samples = []
        self._max_samples = 10

    def report_progress(self, percent: int, message: str, force: bool = False):
        """Enhanced progress reporting with backpressure handling."""
        if not self.original_callback:
            return

        current_time = time.time()
        self._total_updates += 1

        with self._lock:
            # NOWY: Adaptive throttling based on queue pressure
            queue_pressure = self._callback_queue.qsize() / self._callback_queue.maxsize
            if queue_pressure > 0.8:
                # High pressure - increase throttling
                self._dynamic_throttle = min(self.throttle_interval * 2, 0.5)
            elif queue_pressure < 0.3:
                # Low pressure - decrease throttling
                self._dynamic_throttle = max(self.throttle_interval * 0.5, 0.02)
            else:
                # Normal pressure - default throttling
                self._dynamic_throttle = self.throttle_interval

            if (
                not force
                and current_time - self._last_progress_time < self._dynamic_throttle
                and abs(percent - self._last_percent) < 3  # Zmniejszono z 5 do 3
            ):
                return

            self._last_progress_time = current_time
            self._last_percent = percent

        # ULEPSZONY: Non-blocking queue put with overflow handling
        try:
            self._callback_queue.put_nowait((percent, message))
        except queue.Full:
            # NOWY: Smart overflow handling
            self._dropped_updates += 1
            if percent >= 95 or force:  # Always send final updates
                try:
                    # Remove old update and add new one
                    self._callback_queue.get_nowait()
                    self._callback_queue.put_nowait((percent, message))
                except queue.Empty:
                    pass
            
            # NOWY: Log statistics periodically
            if current_time - self._last_stats_log > 10.0:  # Every 10 seconds
                drop_rate = self._dropped_updates / self._total_updates * 100
                logger.debug(f"Progress queue stats: {drop_rate:.1f}% dropped, queue_size: {self._callback_queue.qsize()}")
                self._last_stats_log = current_time
```

---

### PATCH 4: ULEPSZENIE MEMORY CLEANUP PERFORMANCE

**Problem:** Aggressive GC intervals i brak critical memory handling
**Rozwiązanie:** Lepsze timing i emergency procedures

```python
# PRZED (line 299-319):
def should_perform_gc(self, total_files_found: int) -> bool:
    current_memory = self._get_memory_usage()
    files_since_gc = total_files_found - self.last_gc_files

    # Force GC if memory usage is high
    if current_memory > self.memory_threshold_mb:
        return True

# PO:
def should_perform_gc(self, total_files_found: int) -> bool:
    current_memory = self._get_memory_usage()
    files_since_gc = total_files_found - self.last_gc_files

    # NOWY: Emergency GC for critical memory usage
    if current_memory > self.critical_threshold_mb:
        logger.warning(f"CRITICAL MEMORY: {current_memory}MB - emergency GC")
        return True

    # NOWY: Predictive GC based on memory growth rate
    memory_growth = current_memory - self.last_memory_usage
    if memory_growth > 50 and current_memory > self.memory_threshold_mb * 0.8:
        logger.info(f"PREDICTIVE GC: {current_memory}MB (growth: +{memory_growth}MB)")
        return True

    # Original logic but with updated threshold
    if current_memory > self.memory_threshold_mb:
        return True

def perform_cleanup(
    self,
    total_files_found: int,
    session_id: str,
    progress_manager: Optional[AsyncProgressManager] = None,
):
    """Enhanced memory cleanup with emergency procedures."""
    if not self.should_perform_gc(total_files_found):
        return

    initial_memory = self._get_memory_usage()
    is_critical = initial_memory > self.critical_threshold_mb
    
    # NOWY: Emergency cleanup for critical memory
    if is_critical:
        logger.error(f"[{session_id}] EMERGENCY CLEANUP: {initial_memory}MB")
        # Force aggressive cleanup
        import gc
        gc.collect()
        gc.collect()  # Double collection for critical situations
        
        # NOWY: Clear additional caches if available
        if hasattr(self, '_clear_emergency_caches'):
            self._clear_emergency_caches()
    else:
        # Normal cleanup
        collected = gc.collect()

    final_memory = self._get_memory_usage()
    memory_freed = initial_memory - final_memory
    
    # Update tracking
    self.last_gc_files = total_files_found
    self.last_memory_usage = final_memory

    # ULEPSZONY: Conditional logging based on severity
    if is_critical or final_memory > 800:
        logger.warning(
            f"[{session_id}] MEMORY_CLEANUP: {initial_memory}MB→{final_memory}MB "
            f"(freed: {memory_freed}MB) at {total_files_found} files"
        )
    elif final_memory > 500:
        logger.info(
            f"[{session_id}] GC: {final_memory}MB at {total_files_found} files"
        )
    else:
        # Only debug logging for normal operation
        rate_limited_logger.debug_throttled(
            f"[{session_id}] GC: {initial_memory}MB→{final_memory}MB, files={total_files_found}",
            key=f"gc_debug_{session_id}",
        )
```

---

## ✅ CHECKLISTA WERYFIKACYJNA

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Skanowanie małych folderów (10-50 plików)** - czas <5s, memory <100MB
- [ ] **Skanowanie średnich folderów (100-500 plików)** - czas <30s, memory <300MB  
- [ ] **Skanowanie dużych folderów (1000+ plików)** - czas <120s, memory <800MB
- [ ] **Progress reporting** - UI aktualizowane bez lagów, <100ms delay
- [ ] **Memory management** - brak HIGH_MEMORY warnings przy normalnym użyciu
- [ ] **Thread safety** - stabilne działanie w środowisku wielowątkowym
- [ ] **Cache efficiency** - visited dirs nie przekraczają 20MB
- [ ] **Error handling** - graceful handling critical memory situations
- [ ] **Performance** - 75% reduction w memory per file ratio

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **MetadataManager integration** - cache poprawnie zapisywany/odczytywany
- [ ] **file_pairing compatibility** - pary plików prawidłowo generowane
- [ ] **worker_manager cooperation** - współpraca z MemoryMonitor
- [ ] **gallery_manager integration** - smooth data flow do UI
- [ ] **Progress callbacks** - responsywne UI updates
- [ ] **Error propagation** - błędy poprawnie przekazywane do UI

#### **TESTY WERYFIKACYJNE:**

- [ ] **Memory leak test** - długotrwałe skanowanie bez wzrostu pamięci
- [ ] **Performance benchmark** - porównanie z baseline
- [ ] **Stress test** - folder z 5000+ plików
- [ ] **Regression test** - wszystkie istniejące funkcjonalności działają

#### **KRYTERIA SUKCESU:**

- [ ] **MEMORY USAGE <800MB** przy 1000+ plików
- [ ] **NO HIGH_MEMORY WARNINGS** przy normalnym użyciu  
- [ ] **UI RESPONSIVENESS** - progress updates <100ms
- [ ] **RELIABILITY** - brak crashes związanych z pamięcią