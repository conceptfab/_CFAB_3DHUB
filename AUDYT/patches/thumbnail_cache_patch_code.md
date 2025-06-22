# PATCH-CODE DLA: THUMBNAIL_CACHE

**Powiązany plik z analizą:** `../corrections/thumbnail_cache_correction.md`
**Zasady ogólne:** `../../_BASE_/refactoring_rules.md`

---

### PATCH 1: THREAD-SAFE SINGLETON + OPTIMIZED LRU OPERATIONS

**Problem:** Singleton bez thread-safe initialization, nieefektywny LRU update (O(n) complexity)
**Rozwiązanie:** Thread-safe singleton pattern + OrderedDict.move_to_end() dla O(1) LRU

```python
import threading
from threading import RLock

class ThumbnailCache(QObject):
    _instance = None
    _lock = RLock()  # Thread-safe singleton lock
    _error_icon = None

    def __init__(self):
        super().__init__()
        # Thread-safe cache operations
        self._cache_lock = RLock()
        # Używamy OrderedDict dla mechanizmu LRU
        self._cache = OrderedDict()  # key: (normalized_path, width, height) -> (QPixmap, timestamp, size_bytes)
        # ... reszta inicjalizacji bez zmian ...

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:  # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _update_cache_access(self, cache_key: tuple):
        """OPTYMALIZACJA: O(1) LRU update zamiast O(n) pop+insert."""
        with self._cache_lock:
            if cache_key in self._cache:
                # OrderedDict.move_to_end() jest O(1) - much faster than pop+insert
                self._cache.move_to_end(cache_key)

    def get_thumbnail(self, path: str, width: int, height: int) -> Optional[QPixmap]:
        """Pobiera miniaturę z cache z thread-safe access."""
        cache_key = self._normalize_cache_key(path, width, height)

        with self._cache_lock:
            if cache_key in self._cache:
                # OPTYMALIZACJA: O(1) LRU update
                self._cache.move_to_end(cache_key)
                pixmap, timestamp, size_bytes = self._cache[cache_key]
                # Reduce logging spam - log only every 50th access
                if not hasattr(self, '_access_counter'):
                    self._access_counter = 0
                self._access_counter += 1
                if self._access_counter % 50 == 0:
                    logger.debug(f"Cache stats: {len(self._cache)} entries, {self._access_counter} accesses")
                return pixmap

        return None

    def add_thumbnail(self, path: str, width: int, height: int, pixmap: QPixmap):
        """Dodaje załadowaną miniaturę do cache z thread-safe operations."""
        if not path or not pixmap or pixmap.isNull():
            return

        cache_key = self._normalize_cache_key(path, width, height)
        size_bytes = self._estimate_pixmap_size(pixmap)
        timestamp = time.time()

        with self._cache_lock:
            # Usuń starą wersję jeśli istnieje - thread-safe
            if cache_key in self._cache:
                old_pixmap, old_timestamp, old_size = self._cache[cache_key]
                self._total_memory_bytes -= old_size

            # Dodaj nową miniaturę
            self._cache[cache_key] = (pixmap, timestamp, size_bytes)
            self._total_memory_bytes += size_bytes

        # Schedule cleanup outside of lock to avoid deadlock
        self._schedule_cleanup()
```

---

### PATCH 2: ASYNCHRONOUS THUMBNAIL LOADING WITH WORKER THREADS

**Problem:** Synchroniczne ładowanie blokuje UI thread
**Rozwiązanie:** Async loading z QThread workers + signal/slot communication

```python
from PyQt6.QtCore import QThread, pyqtSignal, QObject

class ThumbnailLoadWorker(QThread):
    """Worker thread for asynchronous thumbnail loading."""
    thumbnail_loaded = pyqtSignal(str, int, int, QPixmap)  # path, width, height, pixmap
    thumbnail_failed = pyqtSignal(str, int, int, str)     # path, width, height, error

    def __init__(self, path: str, width: int, height: int, parent=None):
        super().__init__(parent)
        self.path = path
        self.width = width
        self.height = height
        self._cache_instance = None

    def run(self):
        """Load thumbnail in background thread."""
        try:
            # Safe to create QPixmap in worker thread, but not to use it in UI
            pixmap = self._load_pixmap_safely(self.path, self.width, self.height)
            if pixmap and not pixmap.isNull():
                self.thumbnail_loaded.emit(self.path, self.width, self.height, pixmap)
            else:
                self.thumbnail_failed.emit(self.path, self.width, self.height, "Failed to load pixmap")
        except Exception as e:
            self.thumbnail_failed.emit(self.path, self.width, self.height, str(e))

    def _load_pixmap_safely(self, path: str, width: int, height: int) -> Optional[QPixmap]:
        """Thread-safe pixmap loading."""
        if not os.path.exists(path):
            return None

        try:
            # Use PIL for thread-safe image loading
            if width == height:
                with Image.open(path) as img:
                    cropped_img = crop_to_square(img, width)
                    return pillow_image_to_qpixmap(cropped_img)
            else:
                # Standard loading for non-square
                pixmap = QPixmap()
                if pixmap.load(path):
                    return pixmap.scaled(
                        QSize(width, height),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
        except Exception as e:
            logger.error(f"Worker thread pixmap loading error {path}: {e}")
        return None

# Add to ThumbnailCache class:
class ThumbnailCache(QObject):
    # ... existing code ...
    
    def load_thumbnail_async(self, path: str, width: int, height: int, callback=None):
        """
        Load thumbnail asynchronously - NON-BLOCKING UI.
        
        Args:
            callback: Optional function(path, width, height, pixmap) called when loaded
        """
        # Check cache first
        cached = self.get_thumbnail(path, width, height)
        if cached:
            if callback:
                callback(path, width, height, cached)
            return cached

        # Load asynchronously if not in cache
        worker = ThumbnailLoadWorker(path, width, height, self)
        
        def on_loaded(path, width, height, pixmap):
            self.add_thumbnail(path, width, height, pixmap)
            if callback:
                callback(path, width, height, pixmap)
        
        def on_failed(path, width, height, error):
            logger.warning(f"Async thumbnail loading failed {path}: {error}")
            if callback:
                callback(path, width, height, None)
        
        worker.thumbnail_loaded.connect(on_loaded)
        worker.thumbnail_failed.connect(on_failed)
        worker.finished.connect(worker.deleteLater)  # Cleanup worker
        worker.start()
        
        return None  # Will be loaded asynchronously
```

---

### PATCH 3: ADVANCED MEMORY MANAGEMENT WITH WEAK REFERENCES

**Problem:** Memory leaks z QPixmap cache, brak kontroli nad memory fragmentation
**Rozwiązanie:** Weak references + advanced memory tracking + periodic cleanup

```python
import weakref
import gc
from typing import Dict, Any

class ThumbnailCache(QObject):
    # ... existing code ...
    
    def __init__(self):
        super().__init__()
        self._cache_lock = RLock()
        self._cache = OrderedDict()
        self._total_memory_bytes = 0
        
        # MEMORY MANAGEMENT ENHANCEMENT
        self._weak_refs: Dict[tuple, Any] = {}  # Track weak references
        self._memory_stats = {
            'peak_usage': 0,
            'total_allocated': 0,
            'total_deallocated': 0,
            'gc_collections': 0
        }
        
        # ... rest of initialization ...

    def _estimate_pixmap_size(self, pixmap: QPixmap) -> int:
        """ENHANCED: Better memory estimation with actual Qt format detection."""
        if not pixmap or pixmap.isNull():
            return 0

        # Try Qt6's more accurate size calculation
        try:
            # Qt6 may have sizeInBytes in some versions
            if hasattr(pixmap, 'sizeInBytes'):
                return pixmap.sizeInBytes()
        except Exception:
            pass

        # Enhanced estimation based on format
        width, height = pixmap.width(), pixmap.height()
        
        # Detect pixmap format for better estimation
        format_multiplier = 4  # Default ARGB32
        try:
            # Try to detect format through conversion cost
            test_image = pixmap.toImage()
            if test_image.format() == test_image.Format.Format_RGB32:
                format_multiplier = 4
            elif test_image.format() == test_image.Format.Format_RGB888:
                format_multiplier = 3
            elif test_image.format() == test_image.Format.Format_Grayscale8:
                format_multiplier = 1
        except Exception:
            pass
        
        # Apply compression factor for cached thumbnails (typically compressed)
        compression_factor = 0.4  # More realistic for typical thumbnail cache
        estimated_size = int(width * height * format_multiplier * compression_factor)
        
        return max(estimated_size, 1024)  # Minimum 1KB per thumbnail

    def add_thumbnail(self, path: str, width: int, height: int, pixmap: QPixmap):
        """Enhanced memory management with weak references."""
        if not path or not pixmap or pixmap.isNull():
            return

        cache_key = self._normalize_cache_key(path, width, height)
        size_bytes = self._estimate_pixmap_size(pixmap)
        timestamp = time.time()

        with self._cache_lock:
            # Remove old entry and its weak ref
            if cache_key in self._cache:
                old_pixmap, old_timestamp, old_size = self._cache[cache_key]
                self._total_memory_bytes -= old_size
                self._memory_stats['total_deallocated'] += old_size
                
                # Clean up weak reference
                if cache_key in self._weak_refs:
                    del self._weak_refs[cache_key]

            # Add new entry
            self._cache[cache_key] = (pixmap, timestamp, size_bytes)
            self._total_memory_bytes += size_bytes
            self._memory_stats['total_allocated'] += size_bytes
            
            # Update peak usage
            if self._total_memory_bytes > self._memory_stats['peak_usage']:
                self._memory_stats['peak_usage'] = self._total_memory_bytes
            
            # Create weak reference for memory tracking
            def cleanup_callback(weak_ref):
                # Called when pixmap is garbage collected
                with self._cache_lock:
                    if cache_key in self._weak_refs:
                        del self._weak_refs[cache_key]
            
            try:
                self._weak_refs[cache_key] = weakref.ref(pixmap, cleanup_callback)
            except TypeError:
                # QPixmap might not support weak references in some Qt versions
                pass

        # Periodic garbage collection for large caches
        if len(self._cache) % 100 == 0:
            self._trigger_memory_cleanup()

        self._schedule_cleanup()

    def _trigger_memory_cleanup(self):
        """Trigger garbage collection and cleanup weak references."""
        gc.collect()
        self._memory_stats['gc_collections'] += 1
        
        # Clean up broken weak references
        with self._cache_lock:
            broken_refs = []
            for key, weak_ref in self._weak_refs.items():
                if weak_ref() is None:  # Pixmap was garbage collected
                    broken_refs.append(key)
            
            for key in broken_refs:
                del self._weak_refs[key]
                if key in self._cache:
                    # Pixmap was GC'd but still in cache - remove it
                    pixmap, timestamp, size_bytes = self._cache[key]
                    del self._cache[key]
                    self._total_memory_bytes -= size_bytes

    def get_advanced_memory_stats(self) -> dict:
        """ENHANCED: Advanced memory statistics with fragmentation info."""
        with self._cache_lock:
            stats = self.get_memory_statistics()
            stats.update({
                'peak_usage_mb': self._memory_stats['peak_usage'] / (1024 * 1024),
                'total_allocated_mb': self._memory_stats['total_allocated'] / (1024 * 1024),
                'total_deallocated_mb': self._memory_stats['total_deallocated'] / (1024 * 1024),
                'gc_collections': self._memory_stats['gc_collections'],
                'weak_refs_active': len(self._weak_refs),
                'memory_efficiency': (
                    self._memory_stats['total_deallocated'] / 
                    max(self._memory_stats['total_allocated'], 1)
                ) * 100,
            })
            return stats
```

---

### PATCH 4: INTELLIGENT CACHE KEY GENERATION (FORMAT-AWARE)

**Problem:** Niepełny cache key powoduje false hits dla różnych format/quality settings
**Rozwiązanie:** Comprehensive cache key z wszystkimi parametrami wpływającymi na thumbnail

```python
import hashlib

class ThumbnailCache(QObject):
    # ... existing code ...
    
    def _normalize_cache_key(self, path: str, width: int, height: int) -> tuple:
        """
        ENHANCED: Comprehensive cache key including all parameters affecting thumbnail.
        NAPRAWKA: Fixes false cache hits for different format/quality settings.
        """
        normalized_path = normalize_path(path) if path else ""
        
        # Get comprehensive thumbnail configuration
        try:
            from src.app_config import AppConfig
            config = AppConfig.get_instance()
            
            thumbnail_config = {
                'format': config.get_thumbnail_format(),
                'quality': config.get_thumbnail_quality(),
                'crop_method': getattr(config, 'get_thumbnail_crop_method', lambda: 'square')(),
                'color_space': getattr(config, 'get_thumbnail_color_space', lambda: 'RGB')(),
                'compression': getattr(config, 'get_thumbnail_compression', lambda: 'auto')(),
            }
        except Exception as e:
            logger.debug(f"Could not get full config, using defaults: {e}")
            thumbnail_config = {
                'format': 'WEBP',
                'quality': 80,
                'crop_method': 'square',
                'color_space': 'RGB',
                'compression': 'auto'
            }

        # Create hash of configuration for compact key
        config_str = f"{thumbnail_config['format']}-{thumbnail_config['quality']}-" \
                    f"{thumbnail_config['crop_method']}-{thumbnail_config['color_space']}-" \
                    f"{thumbnail_config['compression']}"
        config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]  # 8 chars sufficient
        
        # File modification time for cache invalidation
        try:
            mtime = os.path.getmtime(normalized_path) if normalized_path and os.path.exists(normalized_path) else 0
            # Round to seconds to avoid float precision issues
            mtime = int(mtime)
        except (OSError, ValueError):
            mtime = 0
        
        # Comprehensive cache key
        return (normalized_path, width, height, config_hash, mtime)

    def invalidate_path(self, path: str):
        """NOWA FUNKCJA: Invalidate all cache entries for given path."""
        normalized_path = normalize_path(path) if path else ""
        
        with self._cache_lock:
            keys_to_remove = []
            for cache_key in self._cache.keys():
                if cache_key[0] == normalized_path:  # path is first element
                    keys_to_remove.append(cache_key)
            
            for key in keys_to_remove:
                pixmap, timestamp, size_bytes = self._cache[key]
                del self._cache[key]
                self._total_memory_bytes -= size_bytes
                
                # Clean up weak reference
                if key in self._weak_refs:
                    del self._weak_refs[key]
            
            if keys_to_remove:
                logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for path: {path}")

    def invalidate_modified_files(self):
        """NOWA FUNKCJA: Remove entries for files that have been modified since caching."""
        with self._cache_lock:
            current_time = time.time()
            keys_to_remove = []
            
            for cache_key in list(self._cache.keys()):
                file_path, width, height, config_hash, cached_mtime = cache_key
                
                try:
                    if file_path and os.path.exists(file_path):
                        current_mtime = int(os.path.getmtime(file_path))
                        if current_mtime > cached_mtime:
                            keys_to_remove.append(cache_key)
                    else:
                        # File doesn't exist anymore
                        keys_to_remove.append(cache_key)
                except (OSError, ValueError):
                    # Error accessing file - remove from cache
                    keys_to_remove.append(cache_key)
            
            # Remove invalid entries
            for key in keys_to_remove:
                pixmap, timestamp, size_bytes = self._cache[key]
                del self._cache[key]
                self._total_memory_bytes -= size_bytes
                
                if key in self._weak_refs:
                    del self._weak_refs[key]
            
            if keys_to_remove:
                logger.info(f"Invalidated {len(keys_to_remove)} cache entries for modified files")
```

---

### PATCH 5: BATCH CLEANUP OPERATIONS + HIT RATIO METRICS

**Problem:** Agresywny pojedynczy cleanup, brak metryk cache efficiency
**Rozwiązanie:** Batch operations + comprehensive metrics tracking

```python
from collections import deque
import statistics

class ThumbnailCache(QObject):
    # ... existing code ...
    
    def __init__(self):
        super().__init__()
        # ... existing initialization ...
        
        # METRICS TRACKING
        self._metrics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'total_requests': 0,
            'cleanup_operations': 0,
            'items_removed_total': 0,
            'average_load_time': deque(maxlen=100),  # Last 100 load times
            'hit_ratio_history': deque(maxlen=50),   # Last 50 hit ratios
        }
        
        # ADAPTIVE CLEANUP THRESHOLDS
        self._adaptive_thresholds = {
            'high_usage': 0.90,  # Start aggressive cleanup
            'target_usage': 0.70,  # Target after cleanup
            'low_usage': 0.50,   # Very conservative cleanup
        }
        
        # ... rest of initialization ...

    def get_thumbnail(self, path: str, width: int, height: int) -> Optional[QPixmap]:
        """Enhanced with metrics tracking."""
        start_time = time.time()
        cache_key = self._normalize_cache_key(path, width, height)
        
        self._metrics['total_requests'] += 1

        with self._cache_lock:
            if cache_key in self._cache:
                self._cache.move_to_end(cache_key)
                pixmap, timestamp, size_bytes = self._cache[cache_key]
                
                # METRICS UPDATE
                self._metrics['cache_hits'] += 1
                load_time = (time.time() - start_time) * 1000  # ms
                self._metrics['average_load_time'].append(load_time)
                
                self._update_hit_ratio_metrics()
                return pixmap

        # Cache miss
        self._metrics['cache_misses'] += 1
        self._update_hit_ratio_metrics()
        return None

    def _update_hit_ratio_metrics(self):
        """Update hit ratio history for adaptive algorithms."""
        if self._metrics['total_requests'] > 0:
            current_ratio = (self._metrics['cache_hits'] / self._metrics['total_requests']) * 100
            self._metrics['hit_ratio_history'].append(current_ratio)
    
    def get_performance_metrics(self) -> dict:
        """NOWA FUNKCJA: Comprehensive performance metrics."""
        hit_ratio = 0
        if self._metrics['total_requests'] > 0:
            hit_ratio = (self._metrics['cache_hits'] / self._metrics['total_requests']) * 100
        
        avg_load_time = 0
        if self._metrics['average_load_time']:
            avg_load_time = statistics.mean(self._metrics['average_load_time'])
        
        return {
            'hit_ratio_percent': hit_ratio,
            'cache_hits': self._metrics['cache_hits'],
            'cache_misses': self._metrics['cache_misses'],
            'total_requests': self._metrics['total_requests'],
            'average_load_time_ms': avg_load_time,
            'cleanup_operations': self._metrics['cleanup_operations'],
            'items_removed_total': self._metrics['items_removed_total'],
            'hit_ratio_trend': list(self._metrics['hit_ratio_history'])[-10:],  # Last 10 ratios
        }

    def _calculate_adaptive_thresholds(self) -> dict:
        """Calculate adaptive cleanup thresholds based on usage patterns."""
        # Analyze hit ratio history to adjust thresholds
        if len(self._metrics['hit_ratio_history']) >= 10:
            recent_hit_ratios = list(self._metrics['hit_ratio_history'])[-10:]
            avg_hit_ratio = statistics.mean(recent_hit_ratios)
            
            # High hit ratio = keep more items (higher thresholds)
            # Low hit ratio = cleanup more aggressively (lower thresholds)
            if avg_hit_ratio > 85:  # Very good hit ratio
                return {
                    'high_usage': 0.95,
                    'target_usage': 0.80,
                    'low_usage': 0.60,
                }
            elif avg_hit_ratio > 70:  # Good hit ratio
                return {
                    'high_usage': 0.90,
                    'target_usage': 0.70,
                    'low_usage': 0.50,
                }
            else:  # Poor hit ratio - more aggressive cleanup
                return {
                    'high_usage': 0.80,
                    'target_usage': 0.60,
                    'low_usage': 0.40,
                }
        
        return self._adaptive_thresholds  # Default

    @pyqtSlot()
    def _perform_cleanup(self):
        """ENHANCED: Batch cleanup with adaptive thresholds."""
        self._cleanup_pending = False
        
        max_memory_bytes = self._max_memory_mb * 1024 * 1024
        
        # Use adaptive thresholds
        thresholds = self._calculate_adaptive_thresholds()
        cleanup_memory_threshold = int(max_memory_bytes * thresholds['high_usage'])
        cleanup_entries_threshold = int(self._max_entries * thresholds['high_usage'])
        
        # Check if cleanup needed
        needs_cleanup = (
            len(self._cache) > cleanup_entries_threshold
            or self._total_memory_bytes > cleanup_memory_threshold
        )

        if not needs_cleanup:
            return

        with self._cache_lock:
            initial_count = len(self._cache)
            initial_memory = self._total_memory_bytes
            
            # Target levels after cleanup
            target_entries = int(self._max_entries * thresholds['target_usage'])
            target_memory = int(max_memory_bytes * thresholds['target_usage'])
            
            # BATCH REMOVAL: Collect items to remove first
            items_to_remove = []
            
            # Strategy 1: Remove oldest items first (LRU)
            for cache_key in list(self._cache.keys()):
                if (len(self._cache) - len(items_to_remove) <= target_entries and
                    self._total_memory_bytes - sum(item[2] for item in items_to_remove) <= target_memory):
                    break
                
                pixmap, timestamp, size_bytes = self._cache[cache_key]
                items_to_remove.append((cache_key, size_bytes))
            
            # BATCH EXECUTION: Remove all items at once
            total_removed_bytes = 0
            for cache_key, size_bytes in items_to_remove:
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    total_removed_bytes += size_bytes
                    
                    # Clean up weak reference
                    if cache_key in self._weak_refs:
                        del self._weak_refs[cache_key]
            
            self._total_memory_bytes -= total_removed_bytes
            
            # Update metrics
            self._metrics['cleanup_operations'] += 1
            self._metrics['items_removed_total'] += len(items_to_remove)
            
            if len(items_to_remove) > 0:
                logger.info(
                    f"Batch cleanup completed: removed {len(items_to_remove)} items, "
                    f"freed {total_removed_bytes//1024//1024}MB. "
                    f"Cache: {initial_count}→{len(self._cache)} entries, "
                    f"Memory: {initial_memory//1024//1024}→{self._total_memory_bytes//1024//1024}MB"
                )
```

---

### PATCH 6: SIMPLIFIED ARCHITECTURE - SEPARATION OF CONCERNS

**Problem:** Mixed responsibilities - klasa robi za dużo, trudno testować
**Rozwiązanie:** Podział na komponenty: Cache, Loader, MetricsCollector, MemoryManager

```python
# New modular architecture with separated concerns

class ThumbnailMemoryManager:
    """Handles memory tracking and cleanup policies."""
    
    def __init__(self, max_memory_mb: int, max_entries: int):
        self.max_memory_mb = max_memory_mb
        self.max_entries = max_entries
        self.current_memory_bytes = 0
        self.weak_refs = {}
        
    def estimate_pixmap_size(self, pixmap: QPixmap) -> int:
        """Memory size estimation logic."""
        # ... implementation from PATCH 3 ...
        
    def should_cleanup(self, cache_size: int) -> bool:
        """Determine if cleanup is needed."""
        memory_threshold = (self.max_memory_mb * 1024 * 1024) * 0.9
        entries_threshold = self.max_entries * 0.9
        
        return (self.current_memory_bytes > memory_threshold or 
                cache_size > entries_threshold)

class ThumbnailMetricsCollector:
    """Handles performance metrics and statistics."""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.load_times = deque(maxlen=100)
        
    def record_hit(self, load_time_ms: float):
        """Record cache hit."""
        self.hits += 1
        self.load_times.append(load_time_ms)
        
    def record_miss(self):
        """Record cache miss."""
        self.misses += 1
        
    def get_hit_ratio(self) -> float:
        """Calculate hit ratio percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0

class ThumbnailAsyncLoader:
    """Handles asynchronous thumbnail loading."""
    
    def __init__(self, parent: QObject):
        self.parent = parent
        self.active_workers = {}  # path -> worker mapping
        
    def load_async(self, path: str, width: int, height: int, callback):
        """Load thumbnail asynchronously."""
        # Implementation from PATCH 2
        # ... worker thread logic ...

class ThumbnailCache(QObject):
    """SIMPLIFIED: Main cache class with separated concerns."""
    
    _instance = None
    _lock = RLock()
    
    def __init__(self):
        super().__init__()
        self._cache_lock = RLock()
        self._cache = OrderedDict()
        
        # SEPARATED COMPONENTS
        self.memory_manager = ThumbnailMemoryManager(
            config.thumbnail_cache_max_memory_mb,
            config.thumbnail_cache_max_entries
        )
        self.metrics = ThumbnailMetricsCollector()
        self.async_loader = ThumbnailAsyncLoader(self)
        
        # Simplified cleanup timer
        self._cleanup_timer = QTimer()
        self._cleanup_timer.setSingleShot(True)
        self._cleanup_timer.timeout.connect(self._perform_cleanup)
        
    @classmethod
    def get_instance(cls):
        """Thread-safe singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def get_thumbnail(self, path: str, width: int, height: int) -> Optional[QPixmap]:
        """SIMPLIFIED: Clean cache access logic."""
        start_time = time.time()
        cache_key = self._normalize_cache_key(path, width, height)
        
        with self._cache_lock:
            if cache_key in self._cache:
                # O(1) LRU update
                self._cache.move_to_end(cache_key)
                pixmap, timestamp, size_bytes = self._cache[cache_key]
                
                # Record metrics
                load_time_ms = (time.time() - start_time) * 1000
                self.metrics.record_hit(load_time_ms)
                
                return pixmap
        
        # Cache miss
        self.metrics.record_miss()
        return None
    
    def add_thumbnail(self, path: str, width: int, height: int, pixmap: QPixmap):
        """SIMPLIFIED: Clean add logic."""
        if not path or not pixmap or pixmap.isNull():
            return
            
        cache_key = self._normalize_cache_key(path, width, height)
        size_bytes = self.memory_manager.estimate_pixmap_size(pixmap)
        timestamp = time.time()
        
        with self._cache_lock:
            # Remove old entry
            if cache_key in self._cache:
                old_pixmap, old_timestamp, old_size = self._cache[cache_key]
                self.memory_manager.current_memory_bytes -= old_size
            
            # Add new entry
            self._cache[cache_key] = (pixmap, timestamp, size_bytes)
            self.memory_manager.current_memory_bytes += size_bytes
        
        # Check cleanup need
        if self.memory_manager.should_cleanup(len(self._cache)):
            self._schedule_cleanup()
    
    def load_thumbnail_async(self, path: str, width: int, height: int, callback=None):
        """SIMPLIFIED: Delegate to async loader."""
        # Check cache first
        cached = self.get_thumbnail(path, width, height)
        if cached and callback:
            callback(path, width, height, cached)
            return cached
        
        # Load asynchronously
        return self.async_loader.load_async(path, width, height, callback)
    
    def get_comprehensive_stats(self) -> dict:
        """SIMPLIFIED: Aggregate stats from all components."""
        return {
            **self.metrics.get_stats(),
            **self.memory_manager.get_stats(),
            'cache_entries': len(self._cache),
        }
    
    def _perform_cleanup(self):
        """SIMPLIFIED: Delegate cleanup logic."""
        with self._cache_lock:
            if not self.memory_manager.should_cleanup(len(self._cache)):
                return
            
            # Simple LRU cleanup - remove 30% of oldest items
            items_to_remove = len(self._cache) // 3
            removed_memory = 0
            
            for _ in range(items_to_remove):
                if not self._cache:
                    break
                    
                cache_key, (pixmap, timestamp, size_bytes) = self._cache.popitem(last=False)
                removed_memory += size_bytes
            
            self.memory_manager.current_memory_bytes -= removed_memory
            logger.info(f"Cleanup: removed {items_to_remove} items, freed {removed_memory//1024//1024}MB")
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - czy cache nadal wykonuje swoją główną funkcję (get/add/clear).
- [ ] **API kompatybilność** - czy wszystkie publiczne metody działają jak wcześniej.
- [ ] **Obsługa błędów** - czy error handling dla błędnych ścieżek/pixmap nadal działa.
- [ ] **Walidacja danych** - czy walidacja pixmap/path działa poprawnie.
- [ ] **Logowanie** - czy system logowania nie spamuje (reduced logging frequency).
- [ ] **Konfiguracja** - czy odczytywanie limitów cache z config działa.
- [ ] **Cache** - czy mechanizmy LRU, cleanup, memory tracking działają poprawnie.
- [ ] **Thread safety** - czy kod jest bezpieczny w środowisku wielowątkowym.
- [ ] **Memory management** - czy nie ma wycieków pamięci, weak refs działają.
- [ ] **Performance** - czy wydajność cache access <1ms, async loading nie blokuje UI.

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - czy wszystkie nowe importy (threading, weakref, gc) działają.
- [ ] **Zależności zewnętrzne** - czy PIL, PyQt6 są używane prawidłowo.
- [ ] **Zależności wewnętrzne** - czy powiązania z config, utils działają.
- [ ] **Cykl zależności** - czy nie wprowadzono cyklicznych zależności.
- [ ] **Backward compatibility** - czy istniejący kod nadal działa z nowym API.
- [ ] **Interface contracts** - czy wszystkie publiczne metody zachowują contracts.
- [ ] **Event handling** - czy Qt events są obsługiwane poprawnie.
- [ ] **Signal/slot connections** - czy nowe sygnały async loader działają.
- [ ] **File I/O** - czy operacje na plikach w worker threads są bezpieczne.

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - czy cache CRUD operations działają w izolacji.
- [ ] **Test integracyjny** - czy integracja z gallery_tab, file_tile_widget działa.
- [ ] **Test regresyjny** - czy nie wprowadzono regresji w UI responsiveness.
- [ ] **Test wydajnościowy** - czy 3000+ thumbnails loading w <5s, memory <100MB.

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem.
- [ ] **BRAK FAILED TESTS** - wszystkie testy muszą przejść.
- [ ] **PERFORMANCE BUDGET** - UI nie może być blokowane >100ms.
- [ ] **MEMORY BUDGET** - cache memory usage <100MB dla 1000 thumbnails.
- [ ] **HIT RATIO TARGET** - cache hit ratio >80% w typowym użytkowaniu.