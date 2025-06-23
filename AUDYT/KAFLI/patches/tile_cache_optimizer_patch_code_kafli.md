# PATCH-CODE DLA: TILE_CACHE_OPTIMIZER

**Powiązany plik z analizą:** `../corrections/tile_cache_optimizer_correction_kafli.md`
**Zasady ogólne:** `../_BASE_/refactoring_rules.md`

---

### PATCH 1: ATOMIC STATS UPDATES

**Problem:** Stats updates nie są atomic, mogą prowadzić do race conditions
**Rozwiązanie:** Thread-safe atomic counters z proper synchronization

```python
import threading
from dataclasses import dataclass, field

@dataclass
class CacheStats:
    """Thread-safe cache statistics."""
    hits: int = field(default=0)
    misses: int = field(default=0)
    evictions: int = field(default=0)
    total_size_bytes: int = field(default=0)
    entry_count: int = field(default=0)
    avg_access_time_ms: float = field(default=0.0)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def increment_hits(self):
        with self._lock:
            self.hits += 1
    
    def increment_misses(self):
        with self._lock:
            self.misses += 1
    
    def update_access_time(self, access_time_ms: float):
        with self._lock:
            alpha = 0.1
            self.avg_access_time_ms = (
                alpha * access_time_ms + 
                (1 - alpha) * self.avg_access_time_ms
            )
    
    def update_size(self, size_delta: int):
        with self._lock:
            self.total_size_bytes += size_delta
    
    def update_entry_count(self, count_delta: int):
        with self._lock:
            self.entry_count += count_delta
```

---

### PATCH 2: IMPROVED QPIXMAP CLEANUP

**Problem:** Brak proper cleanup dla cached QPixmap objects
**Rozwiązanie:** Explicit QPixmap cleanup z memory monitoring

```python
def put(self, cache_name: str, key: str, value: Any, 
        size_bytes: Optional[int] = None, ttl_seconds: Optional[float] = None) -> bool:
    """Dodaje wartość do cache z proper cleanup."""
    if size_bytes is None:
        size_bytes = self._estimate_size(value)
    
    with self._lock:
        if cache_name not in self._caches:
            self._caches[cache_name] = {}
        
        cache = self._caches[cache_name]
        
        # Proper cleanup dla existing entry
        if key in cache:
            old_entry = cache[key]
            self._cleanup_cache_value(old_entry.value)
            self._stats[cache_name].update_size(-old_entry.size_bytes)
            self._stats[cache_name].update_entry_count(-1)
        
        # Check if we need eviction
        if self._needs_eviction(cache_name, size_bytes):
            self._perform_eviction(cache_name, size_bytes)
        
        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            size_bytes=size_bytes,
            ttl_seconds=ttl_seconds
        )
        
        cache[key] = entry
        self._stats[cache_name].update_size(size_bytes)
        self._stats[cache_name].update_entry_count(1)
        
        return True

def _cleanup_cache_value(self, value: Any):
    """Proper cleanup dla cached values."""
    if isinstance(value, QPixmap):
        # Force QPixmap cleanup
        if not value.isNull():
            # QPixmap cleanup - detach from shared data
            value = QPixmap()  # Replace with null pixmap
    elif hasattr(value, 'cleanup'):
        # Custom cleanup method
        try:
            value.cleanup()
        except Exception as e:
            logger.warning(f"Error during value cleanup: {e}")
```

---

### PATCH 3: OPTIMIZED EVICTION ALGORITHM

**Problem:** Sorting całego cache podczas eviction jest expensive
**Rozwiązanie:** Heap-based eviction z efficient selection

```python
import heapq
from typing import List, Tuple

class OptimizedLRUEvictionPolicy(EvictionPolicy):
    """Optimized LRU z heap-based selection."""
    
    def select_for_eviction(self, entries: Dict[str, CacheEntry], 
                          target_count: int) -> List[str]:
        if not entries or target_count <= 0:
            return []
        
        # Use heap for efficient selection
        heap: List[Tuple[float, str]] = []
        
        for key, entry in entries.items():
            heapq.heappush(heap, (entry.last_access_time, key))
            
            # Keep heap size manageable
            if len(heap) > target_count * 2:
                # Remove newest entries to keep only oldest
                temp_heap = []
                for _ in range(target_count):
                    if heap:
                        temp_heap.append(heapq.heappop(heap))
                heap = temp_heap
        
        # Extract target_count oldest entries
        result = []
        for _ in range(min(target_count, len(heap))):
            if heap:
                _, key = heapq.heappop(heap)
                result.append(key)
        
        return result

class AdaptiveEvictionPolicy(EvictionPolicy):
    """Enhanced adaptive policy z better pattern recognition."""
    
    def __init__(self):
        self.lru_policy = OptimizedLRUEvictionPolicy()
        self.lfu_policy = LFUEvictionPolicy()
        self.ttl_policy = TTLEvictionPolicy()
        self._pattern_history = []
        self._max_history = 10
    
    def select_for_eviction(self, entries: Dict[str, CacheEntry], 
                          target_count: int) -> List[str]:
        # Analyze patterns over time
        pattern_score = self._analyze_access_patterns(entries)
        self._pattern_history.append(pattern_score)
        
        if len(self._pattern_history) > self._max_history:
            self._pattern_history.pop(0)
        
        avg_pattern = sum(self._pattern_history) / len(self._pattern_history)
        
        # Choose strategy based on historical patterns
        if avg_pattern > 0.7:  # High reuse pattern
            return self.lfu_policy.select_for_eviction(entries, target_count)
        elif avg_pattern < 0.3:  # Low reuse pattern
            return self.lru_policy.select_for_eviction(entries, target_count)
        else:  # Mixed pattern - use TTL first
            return self.ttl_policy.select_for_eviction(entries, target_count)
    
    def _analyze_access_patterns(self, entries: Dict[str, CacheEntry]) -> float:
        """Analyze access patterns and return score 0.0-1.0."""
        if not entries:
            return 0.0
        
        access_counts = [entry.access_count for entry in entries.values()]
        if not access_counts:
            return 0.0
        
        # Calculate pattern diversity
        max_access = max(access_counts)
        if max_access == 0:
            return 0.0
        
        # High variance = diverse access patterns = better for LFU
        # Low variance = uniform access = better for LRU
        variance = sum((count - sum(access_counts)/len(access_counts))**2 
                      for count in access_counts) / len(access_counts)
        
        normalized_variance = min(variance / max_access, 1.0)
        return normalized_variance
```

---

### PATCH 4: ENHANCED MEMORY MANAGEMENT

**Problem:** Brak proactive memory management i pressure detection
**Rozwiązanie:** Smart memory management z predictive cleanup

```python
class TileCacheOptimizer(QObject):
    """Enhanced cache optimizer z smart memory management."""
    
    def __init__(self, 
                 max_size_mb: float = 100.0,
                 max_entries: int = 1000,
                 strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
                 enable_cache_warming: bool = True,
                 memory_pressure_threshold: float = 0.85):
        super().__init__()
        
        # ... existing initialization ...
        
        self.memory_pressure_threshold = memory_pressure_threshold
        self._memory_monitor_timer = QTimer()
        self._memory_monitor_timer.timeout.connect(self._monitor_memory_pressure)
        self._memory_monitor_timer.start(5000)  # Check every 5 seconds
        
        # Performance metrics
        self._performance_history = []
        self._max_performance_history = 50
    
    def _monitor_memory_pressure(self):
        """Proactive memory pressure monitoring."""
        total_size_mb = sum(stats.total_size_bytes for stats in self._stats.values()) / (1024 * 1024)
        max_size_mb = self.max_size_bytes / (1024 * 1024)
        pressure_ratio = total_size_mb / max_size_mb
        
        if pressure_ratio > self.memory_pressure_threshold:
            logger.info(f"Memory pressure detected: {pressure_ratio:.2%}")
            self.memory_pressure_detected.emit(total_size_mb)
            
            # Proactive cleanup
            self._perform_pressure_cleanup(pressure_ratio)
    
    def _perform_pressure_cleanup(self, pressure_ratio: float):
        """Perform cleanup based on memory pressure."""
        if pressure_ratio > 0.95:  # Critical pressure
            cleanup_ratio = 0.3  # Remove 30% of cache
        elif pressure_ratio > 0.9:  # High pressure  
            cleanup_ratio = 0.2  # Remove 20% of cache
        else:  # Medium pressure
            cleanup_ratio = 0.1  # Remove 10% of cache
        
        with self._lock:
            for cache_name, cache in self._caches.items():
                if not cache:
                    continue
                
                target_cleanup = max(1, int(len(cache) * cleanup_ratio))
                policy = self._eviction_policies[self.strategy]
                keys_to_remove = policy.select_for_eviction(cache, target_cleanup)
                
                for key in keys_to_remove:
                    if key in cache:
                        entry = cache[key]
                        self._cleanup_cache_value(entry.value)
                        del cache[key]
                        
                        self._stats[cache_name].update_size(-entry.size_bytes)
                        self._stats[cache_name].update_entry_count(-1)
                        self._stats[cache_name].evictions += 1
        
        logger.info(f"Pressure cleanup completed, removed {cleanup_ratio:.1%} of cache")
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get detailed performance metrics."""
        metrics = {}
        
        for cache_name, stats in self._stats.items():
            total_requests = stats.hits + stats.misses
            if total_requests > 0:
                metrics[f"{cache_name}_hit_rate"] = stats.hits / total_requests
                metrics[f"{cache_name}_avg_access_ms"] = stats.avg_access_time_ms
                metrics[f"{cache_name}_size_mb"] = stats.total_size_bytes / (1024 * 1024)
                metrics[f"{cache_name}_entries"] = stats.entry_count
        
        return metrics
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Cache operations** - get/put/remove działają poprawnie
- [ ] **Eviction strategies** - wszystkie strategie (LRU, LFU, TTL, Adaptive) działają
- [ ] **Memory management** - brak memory leaks, proper cleanup
- [ ] **Thread safety** - concurrent access jest bezpieczny
- [ ] **Performance monitoring** - metrics są accurate
- [ ] **Cache warming** - predictive loading działa
- [ ] **Memory pressure detection** - automatic cleanup triggers
- [ ] **Statistics tracking** - hit rates i access times są poprawne
- [ ] **Signal emissions** - Qt signals są emitted correctly
- [ ] **Singleton pattern** - global instance działa poprawnie

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **PyQt6 integration** - QObject, QTimer, signals działają
- [ ] **Threading** - RLock i thread safety jest maintained
- [ ] **Weak references** - cleanup działa poprawnie
- [ ] **Hashlib** - cache key generation działa
- [ ] **FileTileWidget integration** - cache is used properly
- [ ] **Gallery manager** - bulk operations są supported
- [ ] **Memory monitoring** - system memory tracking działa
- [ ] **Performance metrics** - statistics są accurate

#### **TESTY WERYFIKACYJNE:**

- [ ] **Unit tests** - wszystkie cache operations
- [ ] **Performance tests** - access time < 100ms, hit rate > 80%
- [ ] **Memory tests** - usage under 300MB, no leaks
- [ ] **Concurrency tests** - thread safety z 10+ threads
- [ ] **Integration tests** - z FileTileWidget i gallery_manager
- [ ] **Stress tests** - 1000+ cache entries performance

#### **KRYTERIA SUKCESU:**

- [ ] **CACHE HIT RATE > 80%** - efficient caching
- [ ] **MEMORY USAGE < 300MB** - under memory budget
- [ ] **ACCESS TIME < 100MS** - fast cache operations  
- [ ] **NO MEMORY LEAKS** - proper cleanup verified
- [ ] **THREAD SAFETY** - no race conditions detected
- [ ] **PERFORMANCE MAINTAINED** - no degradation vs baseline

---