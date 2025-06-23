# PATCH-CODE DLA: TILE_RESOURCE_MANAGER_KAFLI

**Powiązany plik z analizą:** `../corrections/tile_resource_manager_correction_kafli.md`
**Zasady ogólne:** `../../../_BASE_/refactoring_rules.md`

---

### PATCH 1: THREAD-SAFE SINGLETON IMPLEMENTATION

**Problem:** Singleton race condition w `get_resource_manager()` może prowadzić do multiple instances
**Rozwiązanie:** Double-checked locking pattern z proper thread safety

```python
# ZMIANA W LINII 587-600: Thread-safe singleton implementation
_resource_manager_instance: Optional[TileResourceManager] = None
_resource_manager_lock = threading.RLock()  # ZMIENIONE na RLock dla reentrant access

def get_resource_manager(
    limits: Optional[ResourceLimits] = None,
) -> TileResourceManager:
    """Thread-safe singleton access do TileResourceManager."""
    global _resource_manager_instance
    
    # First check (unlocked) - common case optimization
    if _resource_manager_instance is not None:
        return _resource_manager_instance
    
    # Double-checked locking pattern
    with _resource_manager_lock:
        # Second check (locked) - ensure thread safety
        if _resource_manager_instance is None:
            logger.debug("Creating new TileResourceManager instance")
            _resource_manager_instance = TileResourceManager(limits)
            logger.info("TileResourceManager singleton instance created")
        else:
            logger.debug("Using existing TileResourceManager instance")
            
        return _resource_manager_instance

def cleanup_resource_manager():
    """Thread-safe cleanup singleton instance."""
    global _resource_manager_instance
    
    with _resource_manager_lock:
        if _resource_manager_instance is not None:
            logger.info("Cleaning up TileResourceManager singleton")
            try:
                _resource_manager_instance.cleanup()
            except Exception as e:
                logger.error(f"Error during resource manager cleanup: {e}")
            finally:
                _resource_manager_instance = None
                logger.debug("TileResourceManager singleton instance cleared")
```

---

### PATCH 2: ENHANCED PERFORMANCE COMPONENTS ERROR HANDLING

**Problem:** Performance components initialization może się nie powieść ale error handling jest insufficient
**Rozwiązanie:** Retry mechanism z fallback strategies i detailed error reporting

```python
# ZMIANA W LINII 249-298: Enhanced performance components initialization
def _initialize_performance_components(self):
    """Inicjalizuje komponenty performance optimization z enhanced error handling."""
    if not self._performance_enabled:
        logger.debug("Performance optimization disabled, skipping component initialization")
        return

    initialization_attempts = 3
    component_status = {
        'performance_monitor': False,
        'cache_optimizer': False, 
        'async_ui_manager': False
    }

    for attempt in range(initialization_attempts):
        try:
            logger.debug(f"Performance components initialization attempt {attempt + 1}/{initialization_attempts}")
            
            # Try to initialize each component independently
            if not component_status['performance_monitor']:
                component_status['performance_monitor'] = self._init_performance_monitor()
                
            if not component_status['cache_optimizer']:
                component_status['cache_optimizer'] = self._init_cache_optimizer()
                
            if not component_status['async_ui_manager']:
                component_status['async_ui_manager'] = self._init_async_ui_manager()

            # Check if all components initialized successfully
            if all(component_status.values()):
                logger.info("All performance optimization components initialized successfully")
                self._connect_performance_signals()
                return
                
        except ImportError as e:
            logger.warning(f"Performance components not available (attempt {attempt + 1}): {e}")
            if attempt == initialization_attempts - 1:
                logger.warning("Performance components will remain disabled due to import failures")
                self._performance_enabled = False
                return
        except Exception as e:
            logger.error(f"Performance components initialization error (attempt {attempt + 1}): {e}")
            if attempt < initialization_attempts - 1:
                time.sleep(0.1 * (attempt + 1))  # Progressive delay
                
    # Partial success handling
    success_count = sum(component_status.values())
    logger.warning(f"Performance components partially initialized: {success_count}/3 components ready")
    
    if success_count > 0:
        logger.info("Continuing with partial performance optimization")
        self._connect_performance_signals()
    else:
        logger.warning("No performance components available - disabling performance optimization")
        self._performance_enabled = False

def _init_performance_monitor(self) -> bool:
    """DODANA: Initialize performance monitor z error handling."""
    try:
        from .tile_performance_monitor import get_performance_monitor
        self._performance_monitor = get_performance_monitor(enable_monitoring=True)
        logger.debug("Performance monitor initialized successfully")
        return True
    except Exception as e:
        logger.debug(f"Performance monitor initialization failed: {e}")
        self._performance_monitor = None
        return False

def _init_cache_optimizer(self) -> bool:
    """DODANA: Initialize cache optimizer z error handling."""
    try:
        from .tile_cache_optimizer import get_cache_optimizer
        cache_size_mb = max(100, self.limits.max_memory_mb * 0.3)  # At least 100MB
        self._cache_optimizer = get_cache_optimizer(max_size_mb=cache_size_mb)
        logger.debug(f"Cache optimizer initialized with {cache_size_mb}MB limit")
        return True
    except Exception as e:
        logger.debug(f"Cache optimizer initialization failed: {e}")
        self._cache_optimizer = None
        return False

def _init_async_ui_manager(self) -> bool:
    """DODANA: Initialize async UI manager z error handling."""
    try:
        from .tile_async_ui_manager import get_async_ui_manager
        max_tasks = min(16, max(4, self.limits.max_concurrent_workers))  # Reasonable range
        self._async_ui_manager = get_async_ui_manager(max_concurrent_tasks=max_tasks)
        logger.debug(f"Async UI manager initialized with {max_tasks} max concurrent tasks")
        return True
    except Exception as e:
        logger.debug(f"Async UI manager initialization failed: {e}")
        self._async_ui_manager = None
        return False

def _connect_performance_signals(self):
    """DODANA: Connect performance component signals safely."""
    try:
        # Connect performance monitor signals
        if self._performance_monitor and hasattr(self._performance_monitor, 'performance_alert'):
            self._performance_monitor.performance_alert.connect(
                lambda metric, value: self.resource_warning.emit(
                    f"Performance alert: {metric} = {value}"
                )
            )
            logger.debug("Performance monitor signals connected")

        # Connect cache optimizer signals
        if self._cache_optimizer and hasattr(self._cache_optimizer, 'memory_pressure_detected'):
            self._cache_optimizer.memory_pressure_detected.connect(
                lambda usage_mb: self._on_memory_warning(
                    f"Cache memory pressure", usage_mb
                )
            )
            logger.debug("Cache optimizer signals connected")

        # Connect async UI manager signals
        if self._async_ui_manager and hasattr(self._async_ui_manager, 'performance_warning'):
            self._async_ui_manager.performance_warning.connect(
                lambda warning_type, value: self.resource_warning.emit(
                    f"UI performance: {warning_type} = {value}"
                )
            )
            logger.debug("Async UI manager signals connected")
            
    except Exception as e:
        logger.warning(f"Error connecting performance signals: {e}")
```

---

### PATCH 3: OPTIMIZED MEMORY MONITORING WITH ADAPTIVE INTERVALS

**Problem:** Memory checking przy każdym timer tick może być kosztowne, brak adaptive timing
**Rozwiązanie:** Adaptive check intervals z caching i performance optimization

```python
# ZMIANA W LINII 51-131: Optimized MemoryMonitor class
class MemoryMonitor(QObject):
    """Monitor użycia pamięci z adaptive checking i caching."""

    # Sygnały
    memory_warning = pyqtSignal(str, float)
    memory_critical = pyqtSignal(str, float)
    cleanup_needed = pyqtSignal()

    def __init__(self, limits: ResourceLimits):
        super().__init__()
        self.limits = limits
        self._last_check_time = 0
        self._cached_memory_mb = 0.0  # DODANE caching
        self._cache_valid_until = 0.0  # DODANE cache expiration
        self._cache_duration = 5.0  # DODANE 5 second cache
        self._memory_history: List[float] = []
        self._max_history = 100
        self._consecutive_high_memory = 0  # DODANE dla adaptive timing
        self._base_check_interval = limits.memory_check_interval_seconds

        # Adaptive timer dla periodic checks
        self._check_timer = QTimer()
        self._check_timer.timeout.connect(self._check_memory_usage)
        self._check_timer.start(self._base_check_interval * 1000)
        
        # Import psutil once at startup
        self._psutil_available = self._check_psutil_availability()

        logger.debug(f"MemoryMonitor initialized with adaptive checking, psutil available: {self._psutil_available}")

    def _check_psutil_availability(self) -> bool:
        """DODANA: Check psutil availability once at startup."""
        try:
            import psutil
            # Test if we can actually use it
            psutil.Process().memory_info()
            return True
        except ImportError:
            logger.warning("psutil not available - memory monitoring will be limited")
            return False
        except Exception as e:
            logger.warning(f"psutil available but not functional: {e}")
            return False

    def get_current_memory_mb(self) -> float:
        """Zwraca aktuelne usage w MB z caching."""
        current_time = time.time()
        
        # Check cache validity
        if current_time < self._cache_valid_until:
            return self._cached_memory_mb
            
        # Update cache
        if self._psutil_available:
            try:
                import psutil
                process = psutil.Process()
                self._cached_memory_mb = process.memory_info().rss / 1024 / 1024
                self._cache_valid_until = current_time + self._cache_duration
            except Exception as e:
                logger.debug(f"Memory check error: {e}")
                # Fallback to previous cached value or 0
                if self._cached_memory_mb == 0.0:
                    self._cached_memory_mb = 0.0
        else:
            self._cached_memory_mb = 0.0
            self._cache_valid_until = current_time + self._cache_duration
            
        return self._cached_memory_mb

    def _check_memory_usage(self):
        """Sprawdza aktuelne usage z adaptive timing."""
        try:
            memory_mb = self.get_current_memory_mb()
            
            if memory_mb == 0.0:  # No psutil or error
                return

            # Dodaj do historii
            self._memory_history.append(memory_mb)
            if len(self._memory_history) > self._max_history:
                self._memory_history.pop(0)

            # Sprawdź limity z proper thresholds
            warning_threshold = self.limits.max_memory_mb * 0.75  # Warning przy 75%
            critical_threshold = self.limits.max_memory_mb * 0.90  # Critical przy 90%

            # Adaptive timing based on memory level
            if memory_mb > critical_threshold:
                self._consecutive_high_memory += 1
                self._adjust_check_frequency(high_memory=True)
                
                self.memory_critical.emit(
                    f"Critical memory usage: {memory_mb:.1f}MB", memory_mb
                )
                self.cleanup_needed.emit()
                
            elif memory_mb > warning_threshold:
                self._consecutive_high_memory += 1
                self._adjust_check_frequency(high_memory=True)
                
                self.memory_warning.emit(
                    f"High memory usage: {memory_mb:.1f}MB", memory_mb
                )
            else:
                # Memory is normal
                if self._consecutive_high_memory > 0:
                    self._consecutive_high_memory = max(0, self._consecutive_high_memory - 1)
                    self._adjust_check_frequency(high_memory=False)

            self._last_check_time = time.time()

        except Exception as e:
            logger.error(f"Memory check error: {e}")

    def _adjust_check_frequency(self, high_memory: bool):
        """DODANA: Adjust check frequency based on memory pressure."""
        if high_memory:
            # Increase frequency when memory is high
            new_interval = max(5, self._base_check_interval // 2)  # Min 5 seconds
        else:
            # Decrease frequency when memory is normal
            new_interval = min(120, self._base_check_interval * 2)  # Max 2 minutes
            
        current_interval = self._check_timer.interval() // 1000
        if current_interval != new_interval:
            self._check_timer.setInterval(new_interval * 1000)
            logger.debug(f"Adjusted memory check interval to {new_interval}s (was {current_interval}s)")
    
    def cleanup(self):
        """DODANA: Proper cleanup for MemoryMonitor."""
        if hasattr(self, '_check_timer'):
            self._check_timer.stop()
            logger.debug("MemoryMonitor timer stopped")
```

---

### PATCH 4: SAFE EMERGENCY CLEANUP PROCEDURE

**Problem:** Emergency cleanup za agresywny, może usuwać aktywne Qt obiekty prowadząc do crashes
**Rozwiązanie:** Multi-tier cleanup strategy z safe Qt object handling

```python
# ZMIANA W LINII 411-447: Safe emergency cleanup implementation  
def perform_emergency_cleanup(self):
    """Wykonuje safe emergency cleanup w multiple tiers."""
    logger.warning("Performing emergency cleanup due to high memory usage")
    
    with self._lock:
        cleanup_start_time = time.time()
        
        # TIER 1: Non-destructive cleanup (safest)
        logger.debug("Emergency cleanup tier 1: Non-destructive operations")
        self._emergency_cleanup_tier1()
        
        # Check if we need more aggressive cleanup
        memory_mb = self._memory_monitor.get_current_memory_mb()
        critical_threshold = self.limits.max_memory_mb * 0.85
        
        if memory_mb > critical_threshold:
            logger.debug("Emergency cleanup tier 2: Cache clearing")
            self._emergency_cleanup_tier2()
            
            # Check again
            memory_mb = self._memory_monitor.get_current_memory_mb()
            if memory_mb > critical_threshold:
                logger.debug("Emergency cleanup tier 3: Component cleanup")
                self._emergency_cleanup_tier3()
        
        cleanup_time = time.time() - cleanup_start_time
        final_memory = self._memory_monitor.get_current_memory_mb()
        
        logger.warning(
            f"Emergency cleanup completed in {cleanup_time:.3f}s, "
            f"memory: {memory_mb:.1f}MB → {final_memory:.1f}MB"
        )

def _emergency_cleanup_tier1(self):
    """DODANA: Tier 1 - Safest cleanup operations."""
    try:
        # Force garbage collection (multiple passes)
        collected_total = 0
        for _ in range(5):
            collected = gc.collect()
            collected_total += collected
            if collected == 0:
                break
                
        if collected_total > 0:
            logger.debug(f"Tier 1: Collected {collected_total} objects via GC")
            
        # Worker pool cleanup (safe)
        self._worker_pool.force_cleanup()
        
        # Update statistics to refresh WeakSet references
        self._update_statistics()
        
    except Exception as e:
        logger.error(f"Tier 1 cleanup error: {e}")

def _emergency_cleanup_tier2(self):
    """DODANA: Tier 2 - Cache clearing operations."""
    try:
        # Clear performance component caches (safe)
        if self._performance_enabled and self._cache_optimizer:
            cache_cleared_mb = self._cache_optimizer.emergency_clear()
            logger.debug(f"Tier 2: Cleared {cache_cleared_mb:.1f}MB from cache")
            
        # Clear statistics history (safe)
        old_count = len(self._stats_history)
        self._stats_history = self._stats_history[-10:]  # Keep only last 10 entries
        logger.debug(f"Tier 2: Cleared {old_count - len(self._stats_history)} statistics entries")
        
        # Clear memory history (safe)
        old_memory_count = len(self._memory_monitor._memory_history)
        self._memory_monitor._memory_history = self._memory_monitor._memory_history[-20:]
        logger.debug(f"Tier 2: Cleared {old_memory_count - len(self._memory_monitor._memory_history)} memory history entries")
        
    except Exception as e:
        logger.error(f"Tier 2 cleanup error: {e}")

def _emergency_cleanup_tier3(self):
    """DODANA: Tier 3 - Component cleanup (most aggressive but safe)."""
    try:
        # Safe component cleanup - tylko komponenty które mają explicit cleanup methods
        components_cleaned = 0
        
        for component_type, component_set in self._active_components.items():
            # Create safe copy to iterate over
            component_list = []
            try:
                component_list = list(component_set)
            except RuntimeError:
                # WeakSet changed during iteration - skip this type
                logger.debug(f"Tier 3: Skipping {component_type} due to WeakSet changes")
                continue
                
            for component in component_list:
                try:
                    # Only cleanup components that are explicitly marked as cleanable
                    if (hasattr(component, '_emergency_cleanable') and 
                        hasattr(component, 'emergency_cleanup')):
                        component.emergency_cleanup()
                        components_cleaned += 1
                    elif (hasattr(component, 'clear_cache') and 
                          not hasattr(component, '_is_qt_widget')):
                        # Safe cache clearing for non-Qt components
                        component.clear_cache()
                        components_cleaned += 1
                        
                except Exception as e:
                    logger.debug(f"Tier 3: Component cleanup error: {e}")
                    
        logger.debug(f"Tier 3: Cleaned {components_cleaned} components")
        
        # Final aggressive garbage collection
        for _ in range(3):
            collected = gc.collect()
            if collected == 0:
                break
                
    except Exception as e:
        logger.error(f"Tier 3 cleanup error: {e}")

# ZMIANA W LINII 379-409: Enhanced regular cleanup
def perform_cleanup(self):
    """Wykonuje regular cleanup z performance optimization."""
    with self._lock:
        start_time = time.time()
        cleaned_count = 0

        # Pre-cleanup memory check
        initial_memory = self._memory_monitor.get_current_memory_mb()

        # Safe garbage collection
        collected = gc.collect()
        if collected > 0:
            cleaned_count += collected
            logger.debug(f"Regular cleanup: Collected {collected} objects via GC")

        # Safe component maintenance - tylko cache clearing
        for component_type, component_set in self._active_components.items():
            try:
                component_list = list(component_set)  # Safe copy
                for component in component_list:
                    if hasattr(component, 'maintenance_cleanup'):
                        try:
                            component.maintenance_cleanup()
                        except Exception as e:
                            logger.debug(f"Component maintenance error: {e}")
            except RuntimeError:
                # WeakSet changed during iteration - not critical for regular cleanup
                logger.debug(f"Skipping {component_type} maintenance due to WeakSet changes")

        # Update stats and check improvement
        self._update_statistics()
        final_memory = self._memory_monitor.get_current_memory_mb()

        cleanup_time = time.time() - start_time
        self._last_cleanup_time = time.time()

        logger.debug(
            f"Regular cleanup completed in {cleanup_time:.3f}s, "
            f"memory: {initial_memory:.1f}MB → {final_memory:.1f}MB, "
            f"cleaned: {cleaned_count} objects"
        )
        self.cleanup_performed.emit(cleaned_count)
```

---

### PATCH 5: PERFORMANCE OPTIMIZATION FOR STATISTICS AND OPERATIONS

**Problem:** Statistics calculation za często bez caching, component operations mogą być slow
**Rozwiązanie:** Smart caching z batching operations i performance monitoring

```python
# ZMIANA W LINII 449-490: Optimized statistics calculation
def _update_statistics(self, force_update: bool = False):
    """Aktualizuje statystyki z smart caching."""
    current_time = time.time()
    
    # Smart caching - don't update too frequently unless forced
    if not force_update and hasattr(self, '_last_stats_update'):
        time_since_update = current_time - self._last_stats_update
        min_update_interval = 2.0  # Don't update more than every 2 seconds
        
        if time_since_update < min_update_interval:
            logger.debug(f"Skipping stats update (too frequent: {time_since_update:.1f}s)")
            return
    
    stats = MemoryUsageStats()
    stats.timestamp = current_time
    
    calculation_start = time.time()

    with self._lock:
        # Fast operations first
        stats.total_tiles = len(self._active_tiles)
        stats.active_tiles = stats.total_tiles
        stats.worker_count = self._worker_pool.get_active_count()

        # Expensive memory operation with caching
        stats.total_memory_mb = self._memory_monitor.get_current_memory_mb()
        if stats.total_tiles > 0:
            stats.memory_per_tile_mb = stats.total_memory_mb / stats.total_tiles

        # Cache stats z performance optimization i error handling
        if self._cache_optimizer:
            stats = self._update_cache_stats_optimized(stats)
        else:
            stats.cache_hits = 0
            stats.cache_misses = 0
            stats.cache_hit_ratio = 0.0

    # Performance tracking
    calculation_time = time.time() - calculation_start
    if calculation_time > 0.1:  # Log slow calculations
        logger.warning(f"Slow statistics calculation: {calculation_time:.3f}s")

    # Dodaj do historii z size limit
    self._stats_history.append(stats)
    if len(self._stats_history) > 50:  # Reduced from 100 for memory efficiency
        self._stats_history.pop(0)

    self._last_stats_update = current_time
    self.stats_updated.emit(stats)

def _update_cache_stats_optimized(self, stats: MemoryUsageStats) -> MemoryUsageStats:
    """DODANA: Optimized cache stats update z error handling."""
    try:
        # Use cached stats if available
        if hasattr(self._cache_optimizer, 'get_cached_performance_summary'):
            cache_stats = self._cache_optimizer.get_cached_performance_summary()
        else:
            cache_stats = self._cache_optimizer.get_performance_summary()
            
        if cache_stats:
            stats.cache_hit_ratio = cache_stats.get("overall_hit_rate", 0.0)
            
            # More accurate hit/miss calculation
            total_requests = cache_stats.get("total_requests", 0)
            if total_requests > 0:
                stats.cache_hits = int(total_requests * stats.cache_hit_ratio / 100)
                stats.cache_misses = total_requests - stats.cache_hits
            else:
                stats.cache_hits = 0
                stats.cache_misses = 0
        else:
            stats.cache_hits = 0
            stats.cache_misses = 0
            stats.cache_hit_ratio = 0.0
            
    except Exception as e:
        logger.debug(f"Cache stats update error: {e}")
        stats.cache_hits = 0
        stats.cache_misses = 0
        stats.cache_hit_ratio = 0.0
        
    return stats

# ZMIANA W LINII 333-356: Batched component registration
def register_components_batch(self, components: List[Tuple[str, object]]) -> Dict[str, bool]:
    """DODANA: Batch registration dla multiple components."""
    results = {}
    
    with self._lock:
        for component_type, component in components:
            if component_type not in self._active_components:
                logger.error(f"Unknown component type: {component_type}")
                results[f"{component_type}_{id(component)}"] = False
                continue
                
            try:
                self._active_components[component_type].add(component)
                results[f"{component_type}_{id(component)}"] = True
                logger.debug(f"Batch registered {component_type} component")
            except Exception as e:
                logger.error(f"Batch registration error for {component_type}: {e}")
                results[f"{component_type}_{id(component)}"] = False
    
    return results

# ZMIANA W LINII 536-549: Optimized debug info generation
def get_debug_info(self) -> Dict:
    """Zwraca cached debug info o resource manager."""
    # Use cached stats to avoid duplicate calculation
    if self._stats_history:
        stats = self._stats_history[-1]
    else:
        # Only calculate if no cached stats available
        stats = self.get_statistics()
    
    return {
        "limits": {
            "max_tiles": self.limits.max_tiles,
            "max_memory_mb": self.limits.max_memory_mb,
            "max_concurrent_workers": self.limits.max_concurrent_workers,
        },
        "current_stats": {
            "total_tiles": stats.total_tiles,
            "total_memory_mb": stats.total_memory_mb,
            "memory_per_tile_mb": stats.memory_per_tile_mb,
            "cache_hit_ratio": stats.cache_hit_ratio,
            "worker_count": stats.worker_count,
        },
        "memory_trend": self.get_memory_trend(),
        "component_counts": {
            name: len(comp_set)
            for name, comp_set in self._active_components.items()
        },
        "last_cleanup_ago_seconds": time.time() - self._last_cleanup_time,
        "worker_pool_active": self._worker_pool.get_active_count(),
        "performance_optimization_enabled": self._performance_enabled,
    }
```

---

### PATCH 6: ENHANCED RESOURCE LIMITS VALIDATION

**Problem:** Brak validation czy ResourceLimits mają sensowne wartości
**Rozwiązanie:** Comprehensive validation z auto-correction i warnings

```python
# ZMIANA W LINII 38-49: Enhanced ResourceLimits with validation
@dataclass
class ResourceLimits:
    """Limity zasobów dla systemu z validation."""

    max_tiles: int = 1000
    max_memory_mb: int = 4000
    max_memory_per_tile_mb: int = 10
    max_concurrent_workers: int = 8
    cleanup_interval_seconds: int = 180
    memory_check_interval_seconds: int = 30
    cache_cleanup_threshold_ratio: float = 0.7

    def __post_init__(self):
        """Validate and auto-correct resource limits."""
        self._validate_and_correct()

    def _validate_and_correct(self):
        """DODANA: Validate resource limits i auto-correct invalid values."""
        corrections = []
        
        # Validate max_tiles
        if self.max_tiles <= 0:
            corrections.append(f"max_tiles corrected: {self.max_tiles} → 100")
            self.max_tiles = 100
        elif self.max_tiles > 10000:
            corrections.append(f"max_tiles corrected: {self.max_tiles} → 10000")
            self.max_tiles = 10000
            
        # Validate max_memory_mb
        if self.max_memory_mb <= 0:
            corrections.append(f"max_memory_mb corrected: {self.max_memory_mb} → 1000")
            self.max_memory_mb = 1000
        elif self.max_memory_mb < 500:
            corrections.append(f"max_memory_mb corrected: {self.max_memory_mb} → 500 (minimum)")
            self.max_memory_mb = 500
            
        # Validate max_memory_per_tile_mb
        if self.max_memory_per_tile_mb <= 0:
            corrections.append(f"max_memory_per_tile_mb corrected: {self.max_memory_per_tile_mb} → 5")
            self.max_memory_per_tile_mb = 5
        elif self.max_memory_per_tile_mb > 100:
            corrections.append(f"max_memory_per_tile_mb corrected: {self.max_memory_per_tile_mb} → 100")
            self.max_memory_per_tile_mb = 100
            
        # Validate max_concurrent_workers
        if self.max_concurrent_workers <= 0:
            corrections.append(f"max_concurrent_workers corrected: {self.max_concurrent_workers} → 4")
            self.max_concurrent_workers = 4
        elif self.max_concurrent_workers > 32:
            corrections.append(f"max_concurrent_workers corrected: {self.max_concurrent_workers} → 32")
            self.max_concurrent_workers = 32
            
        # Validate cleanup_interval_seconds
        if self.cleanup_interval_seconds < 30:
            corrections.append(f"cleanup_interval_seconds corrected: {self.cleanup_interval_seconds} → 30")
            self.cleanup_interval_seconds = 30
        elif self.cleanup_interval_seconds > 3600:
            corrections.append(f"cleanup_interval_seconds corrected: {self.cleanup_interval_seconds} → 3600")
            self.cleanup_interval_seconds = 3600
            
        # Validate memory_check_interval_seconds
        if self.memory_check_interval_seconds < 5:
            corrections.append(f"memory_check_interval_seconds corrected: {self.memory_check_interval_seconds} → 5")
            self.memory_check_interval_seconds = 5
        elif self.memory_check_interval_seconds > 300:
            corrections.append(f"memory_check_interval_seconds corrected: {self.memory_check_interval_seconds} → 300")
            self.memory_check_interval_seconds = 300
            
        # Validate cache_cleanup_threshold_ratio
        if self.cache_cleanup_threshold_ratio <= 0 or self.cache_cleanup_threshold_ratio >= 1:
            corrections.append(f"cache_cleanup_threshold_ratio corrected: {self.cache_cleanup_threshold_ratio} → 0.7")
            self.cache_cleanup_threshold_ratio = 0.7
            
        # Logical validations
        total_memory_estimate = self.max_tiles * self.max_memory_per_tile_mb
        if total_memory_estimate > self.max_memory_mb * 2:
            # Per-tile limit would allow too much total memory
            corrected_per_tile = max(1, self.max_memory_mb // self.max_tiles)
            corrections.append(
                f"max_memory_per_tile_mb corrected for consistency: "
                f"{self.max_memory_per_tile_mb} → {corrected_per_tile}"
            )
            self.max_memory_per_tile_mb = corrected_per_tile
            
        # Log corrections
        if corrections:
            logger.warning("Resource limits auto-corrected:")
            for correction in corrections:
                logger.warning(f"  - {correction}")

    def get_memory_warning_threshold(self) -> float:
        """DODANA: Get warning threshold based on limits."""
        return self.max_memory_mb * 0.75
        
    def get_memory_critical_threshold(self) -> float:
        """DODANA: Get critical threshold based on limits."""
        return self.max_memory_mb * 0.90

# ZMIANA W LINII 201-242: Enhanced TileResourceManager initialization
def __init__(self, limits: Optional[ResourceLimits] = None):
    super().__init__()

    # Validate and set limits
    if limits is None:
        self.limits = ResourceLimits()
        logger.debug("Using default ResourceLimits")
    else:
        self.limits = limits
        # Validation already done in __post_init__
        
    # Log final limits for debugging
    logger.info(
        f"TileResourceManager limits: {self.limits.max_tiles} tiles, "
        f"{self.limits.max_memory_mb}MB memory, "
        f"{self.limits.max_concurrent_workers} workers"
    )
    
    # ... rest of initialization unchanged ...
```

---

## ✅ CHECKLISTA WERYFIKACYJNA RESOURCE MANAGER KAFLI (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI RESOURCE MANAGER DO WERYFIKACJI:**

- [ ] **Singleton functionality** - czy thread-safe singleton działa poprawnie
- [ ] **Tile registration** - czy rejestracja kafli respektuje limits i działa concurrent
- [ ] **Memory monitoring** - czy adaptive memory checking działa bez performance impact
- [ ] **Emergency cleanup** - czy safe tier-based cleanup nie powoduje crashes Qt objects
- [ ] **Performance components** - czy initialization z retry mechanism działa
- [ ] **Statistics calculation** - czy smart caching poprawia performance
- [ ] **Resource limits validation** - czy auto-correction invalid values działa
- [ ] **Worker pool management** - czy limits enforcement i cleanup działają

#### **ZALEŻNOŚCI RESOURCE MANAGER DO WERYFIKACJI:**

- [ ] **FileTileWidget integration** - czy tile registration podczas tworzenia kafli działa
- [ ] **Performance components integration** - czy lazy loading i error handling działają
- [ ] **Memory monitoring z psutil** - czy fallback gdy psutil niedostępne działa
- [ ] **QTimer cleanup** - czy timers są properly stopped podczas cleanup
- [ ] **WeakSet thread safety** - czy concurrent iteration nie powoduje RuntimeError
- [ ] **Signal connections** - czy performance component signals są properly connected
- [ ] **Emergency procedures** - czy tier-based cleanup reaguje na memory pressure

#### **TESTY WERYFIKACYJNE RESOURCE MANAGER:**

- [ ] **Test singleton thread safety** - concurrent access do get_resource_manager()
- [ ] **Test memory monitoring accuracy** - porównanie z system memory usage
- [ ] **Test emergency cleanup effectiveness** - memory reduction w critical situations
- [ ] **Test performance components resilience** - behavior podczas component failures  
- [ ] **Test resource limits enforcement** - czy limits są respektowane przy load
- [ ] **Test statistics performance** - czy smart caching redukuje overhead
- [ ] **Test adaptive timing** - czy memory check frequency adjust based na pressure

#### **KRYTERIA SUKCESU RESOURCE MANAGER:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - wszystkie testy resource manager przechodzą
- [ ] **SINGLETON THREAD SAFETY** - brak race conditions w concurrent access
- [ ] **MEMORY MONITORING EFFICIENCY** - monitoring overhead <1% CPU usage
- [ ] **EMERGENCY CLEANUP SAFETY** - brak crashes Qt objects podczas cleanup
- [ ] **PERFORMANCE COMPONENTS RESILIENCE** - graceful degradation przy failures
- [ ] **RESOURCE LIMITS EFFECTIVENESS** - proper enforcement przy high load galerii kafli