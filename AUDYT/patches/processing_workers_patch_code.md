# PATCH-CODE DLA: PROCESSING_WORKERS

**Powiązany plik z analizą:** `../corrections/processing_workers_correction.md`
**Zasady ogólne:** `../../_BASE_/refactoring_rules.md`

---

### PATCH 1: UNIFIED WORKER ARCHITECTURE

**Problem:** Mixed architecture - legacy QObject workers vs UnifiedBaseWorker
**Rozwiązanie:** Unifikacja wszystkich workers na UnifiedBaseWorker base class

```python
from .base_workers import UnifiedBaseWorker, AsyncUnifiedBaseWorker, WorkerPriority
from typing import List, Tuple, Optional, Dict, Any
import logging
import os
import time
from collections import deque

logger = logging.getLogger(__name__)

class ThumbnailGenerationWorker(UnifiedBaseWorker):
    """
    UNIFIED: Worker do generowania miniaturek z simplified architecture.
    """
    
    def __init__(self, path: str, width: int, height: int, priority: int = WorkerPriority.NORMAL):
        super().__init__(timeout_seconds=30, priority=priority)
        self.path = path
        self.width = width
        self.height = height
        # Pre-validate inputs in constructor for fail-fast behavior
        self._validate_inputs()

    def _validate_inputs(self):
        """Enhanced validation with detailed error messages."""
        if not self.path:
            raise ValueError("Path cannot be empty")
        if not os.path.exists(self.path):
            raise ValueError(f"File does not exist: {self.path}")
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"Invalid dimensions: {self.width}x{self.height}")
        
        # Check file size for large files (>50MB)
        try:
            file_size = os.path.getsize(self.path)
            if file_size > 50 * 1024 * 1024:  # 50MB
                logger.warning(f"Large file detected: {file_size//1024//1024}MB - {self.path}")
        except OSError:
            pass

    def _run_implementation(self):
        """OPTIMIZED: Single cache check pattern."""
        from src.ui.widgets.thumbnail_cache import ThumbnailCache
        from src.utils.image_utils import create_thumbnail_from_file
        
        cache = ThumbnailCache.get_instance()
        
        # SINGLE CACHE CHECK - reduce overhead
        cached_pixmap = cache.get_thumbnail(self.path, self.width, self.height)
        if cached_pixmap is not None:
            self.signals.thumbnail_finished.emit(cached_pixmap, self.path, self.width, self.height)
            return
        
        # Generate thumbnail with progress reporting
        self.emit_progress(25, f"Loading {os.path.basename(self.path)}...")
        
        try:
            pixmap = create_thumbnail_from_file(self.path, self.width, self.height)
            
            if pixmap.isNull():
                raise ValueError("Failed to create thumbnail - invalid image")
            
            # Add to cache atomically
            cache.add_thumbnail(self.path, self.width, self.height, pixmap)
            
            self.emit_progress(100, "Thumbnail generated successfully")
            self.signals.thumbnail_finished.emit(pixmap, self.path, self.width, self.height)
            
        except Exception as e:
            error_msg = f"Thumbnail generation failed: {str(e)}"
            self.signals.thumbnail_error.emit(error_msg, self.path, self.width, self.height)
            raise

class DataProcessingWorker(UnifiedBaseWorker):
    """
    UNIFIED: Data processing worker converted to UnifiedBaseWorker.
    Eliminates QObject moveToThread pattern for better performance.
    """
    
    # Custom signals for data processing
    tile_data_ready = pyqtSignal(object)  # FilePair
    tiles_batch_ready = pyqtSignal(list)
    tiles_refresh_needed = pyqtSignal(list)
    
    def __init__(self, working_directory: str, file_pairs: List, timeout_seconds: int = 300):
        # Reduced timeout from 1800s to 300s (5 minutes)
        super().__init__(timeout_seconds=timeout_seconds, priority=WorkerPriority.HIGH)
        self.working_directory = working_directory
        self.file_pairs = file_pairs or []
        self._metadata_loaded = False

    def _validate_inputs(self):
        """Validate processing parameters."""
        if not self.working_directory:
            raise ValueError("Working directory cannot be empty")
        if not self.file_pairs:
            raise ValueError("File pairs list cannot be empty")

    def _run_implementation(self):
        """OPTIMIZED: Async metadata loading with batch processing."""
        total_pairs = len(self.file_pairs)
        
        # Calculate adaptive batch size based on folder size
        batch_size = self._calculate_adaptive_batch_size(total_pairs)
        
        self.emit_progress(0, f"Processing {total_pairs} file pairs...")
        
        # Process in batches for better memory management
        processed_pairs = []
        current_batch = []
        
        for i, file_pair in enumerate(self.file_pairs):
            if self.check_interruption():
                return
            
            current_batch.append(file_pair)
            processed_pairs.append(file_pair)
            
            # Emit batch when ready
            if len(current_batch) >= batch_size:
                self._emit_batch_with_metadata(current_batch.copy())
                current_batch.clear()
                
                # Progressive progress reporting
                progress = int((i / total_pairs) * 90)  # Reserve 10% for final steps
                self.emit_progress(progress, f"Processed {i+1}/{total_pairs} pairs")
        
        # Process remaining items
        if current_batch:
            self._emit_batch_with_metadata(current_batch)
        
        self.emit_progress(100, f"Completed processing {total_pairs} file pairs")
        self.signals.finished.emit(processed_pairs)

    def _calculate_adaptive_batch_size(self, total_pairs: int) -> int:
        """Calculate optimal batch size based on data size."""
        if total_pairs <= 50:
            return 5  # Small folders - frequent updates
        elif total_pairs <= 500:
            return 20  # Medium folders - balanced
        elif total_pairs <= 2000:
            return 50  # Large folders - efficient batching
        else:
            return 100  # Very large folders - minimize overhead

    def _emit_batch_with_metadata(self, batch: List):
        """Emit batch with async metadata loading."""
        # Emit batch immediately for fast UI response
        self.tiles_batch_ready.emit(batch)
        
        # Load metadata asynchronously in background
        self._load_metadata_async(batch)

    def _load_metadata_async(self, file_pairs: List):
        """NON-BLOCKING: Async metadata loading."""
        try:
            from src.logic.metadata_manager import MetadataManager
            
            metadata_manager = MetadataManager.get_instance(self.working_directory)
            
            # Apply metadata to batch
            metadata_applied = metadata_manager.apply_metadata_to_file_pairs(file_pairs)
            
            if metadata_applied:
                # Emit refresh signal for UI update
                self.tiles_refresh_needed.emit(file_pairs)
                
        except Exception as e:
            logger.error(f"Async metadata loading failed: {e}")
```

---

### PATCH 2: ASYNC METADATA STREAMING

**Problem:** Synchronous metadata loading blokuje UI thread
**Rozwiązanie:** Streaming metadata loading z progressive UI updates

```python
class StreamingMetadataWorker(AsyncUnifiedBaseWorker):
    """
    NEW: Streaming metadata worker for non-blocking metadata operations.
    """
    
    metadata_chunk_ready = pyqtSignal(list, dict)  # file_pairs, metadata_dict
    metadata_streaming_finished = pyqtSignal(int)  # total_processed
    
    def __init__(self, working_directory: str, file_pairs: List, chunk_size: int = 50):
        super().__init__(timeout_seconds=180, priority=WorkerPriority.NORMAL)
        self.working_directory = working_directory
        self.file_pairs = file_pairs
        self.chunk_size = chunk_size

    def _validate_inputs(self):
        if not self.working_directory or not self.file_pairs:
            raise ValueError("Invalid metadata streaming parameters")

    async def _run_implementation(self):
        """Stream metadata loading in chunks."""
        from src.logic.metadata_manager import MetadataManager
        
        metadata_manager = MetadataManager.get_instance(self.working_directory)
        total_pairs = len(self.file_pairs)
        processed_count = 0
        
        # Process metadata in chunks
        for i in range(0, total_pairs, self.chunk_size):
            if self.check_interruption():
                return
            
            chunk = self.file_pairs[i:i + self.chunk_size]
            
            try:
                # Load metadata for chunk
                metadata_dict = {}
                for file_pair in chunk:
                    base_name = file_pair.get_base_name()
                    stars = metadata_manager.get_stars(base_name)
                    color = metadata_manager.get_color_tag(base_name)
                    
                    if stars > 0 or color:
                        metadata_dict[base_name] = {
                            'stars': stars,
                            'color': color
                        }
                        file_pair.set_stars(stars)
                        file_pair.set_color_tag(color)
                
                # Emit chunk with metadata
                if metadata_dict:
                    self.metadata_chunk_ready.emit(chunk, metadata_dict)
                
                processed_count += len(chunk)
                progress = int((processed_count / total_pairs) * 100)
                self.emit_progress(progress, f"Loaded metadata: {processed_count}/{total_pairs}")
                
                # Small delay to prevent UI flooding
                await asyncio.sleep(0.01)
                
            except Exception as e:
                logger.error(f"Metadata chunk processing failed: {e}")
        
        self.metadata_streaming_finished.emit(processed_count)

class MetadataSaveWorker(AsyncUnifiedBaseWorker):
    """
    ENHANCED: Async metadata saving with batch optimization.
    """
    
    def __init__(self, working_directory: str, file_pairs: List, 
                 unpaired_archives: List = None, unpaired_previews: List = None):
        super().__init__(timeout_seconds=120, priority=WorkerPriority.HIGH)
        self.working_directory = working_directory
        self.file_pairs = file_pairs or []
        self.unpaired_archives = unpaired_archives or []
        self.unpaired_previews = unpaired_previews or []

    async def _run_implementation(self):
        """Optimized async metadata saving."""
        from src.logic.metadata_manager import MetadataManager
        
        metadata_manager = MetadataManager.get_instance(self.working_directory)
        
        self.emit_progress(0, "Preparing metadata for save...")
        
        # Batch metadata changes for efficiency
        changes_count = 0
        for file_pair in self.file_pairs:
            if file_pair.get_stars() > 0 or file_pair.get_color_tag():
                changes_count += 1
        
        if changes_count == 0:
            self.emit_progress(100, "No metadata changes to save")
            self.signals.finished.emit("No changes to save")
            return
        
        self.emit_progress(50, f"Saving {changes_count} metadata changes...")
        
        try:
            # Use buffered save for performance
            metadata_manager.save_metadata(
                self.file_pairs, 
                self.unpaired_archives, 
                self.unpaired_previews
            )
            
            # Force immediate write to disk
            metadata_manager.force_save()
            
            self.emit_progress(100, f"Saved {changes_count} metadata changes")
            self.signals.finished.emit(f"Saved {changes_count} changes successfully")
            
        except Exception as e:
            error_msg = f"Metadata save failed: {str(e)}"
            self.signals.error.emit(error_msg)
            raise
```

---

### PATCH 3: ADVANCED BATCH PROCESSING

**Problem:** Fixed batch sizes nie uwzględniają memory usage
**Rozwiązanie:** Memory-aware adaptive batching z monitoring

```python
import psutil
from typing import NamedTuple

class BatchMetrics(NamedTuple):
    """Metrics for batch processing optimization."""
    batch_size: int
    memory_usage_mb: int
    processing_time_ms: float
    success_rate: float

class MemoryAwareBatchProcessor:
    """
    Advanced batch processor with memory monitoring and adaptive sizing.
    """
    
    def __init__(self, initial_batch_size: int = 20, max_memory_mb: int = 1024):
        self.current_batch_size = initial_batch_size
        self.max_memory_mb = max_memory_mb
        self.metrics_history = deque(maxlen=10)
        self.memory_threshold = 0.8  # 80% of max memory
        
    def get_optimal_batch_size(self, total_items: int, current_memory_mb: float) -> int:
        """Calculate optimal batch size based on current conditions."""
        
        # Memory-based adjustment
        memory_ratio = current_memory_mb / self.max_memory_mb
        
        if memory_ratio > self.memory_threshold:
            # High memory usage - reduce batch size
            adjustment_factor = 0.5
        elif memory_ratio < 0.3:
            # Low memory usage - can increase batch size
            adjustment_factor = 1.5
        else:
            # Normal memory usage
            adjustment_factor = 1.0
        
        # Calculate base batch size by total items
        if total_items <= 100:
            base_size = 10
        elif total_items <= 1000:
            base_size = 25
        elif total_items <= 5000:
            base_size = 50
        else:
            base_size = 100
        
        # Apply memory adjustment
        optimal_size = int(base_size * adjustment_factor)
        
        # Apply historical learning
        if self.metrics_history:
            avg_success_rate = sum(m.success_rate for m in self.metrics_history) / len(self.metrics_history)
            if avg_success_rate < 0.8:  # Low success rate
                optimal_size = max(5, optimal_size // 2)  # Reduce batch size
        
        return max(5, min(optimal_size, 200))  # Bounds: 5-200

    def record_batch_metrics(self, batch_size: int, memory_mb: float, 
                           processing_time_ms: float, success_count: int, total_count: int):
        """Record metrics for adaptive learning."""
        success_rate = success_count / max(total_count, 1)
        metrics = BatchMetrics(batch_size, int(memory_mb), processing_time_ms, success_rate)
        self.metrics_history.append(metrics)

class AdvancedBatchThumbnailWorker(UnifiedBaseWorker):
    """
    ENHANCED: Memory-aware batch thumbnail generation.
    """
    
    batch_completed = pyqtSignal(list, dict)  # thumbnails, metrics
    
    def __init__(self, thumbnail_requests: List[Tuple[str, int, int]], 
                 max_memory_mb: int = 1024):
        super().__init__(timeout_seconds=600, priority=WorkerPriority.HIGH)
        self.thumbnail_requests = thumbnail_requests
        self.batch_processor = MemoryAwareBatchProcessor(max_memory_mb=max_memory_mb)
        self.generated_thumbnails = {}
        self.failed_requests = []

    def _run_implementation(self):
        """Process thumbnails with adaptive batching."""
        from src.ui.widgets.thumbnail_cache import ThumbnailCache
        from src.utils.image_utils import create_thumbnail_from_file
        
        cache = ThumbnailCache.get_instance()
        total_requests = len(self.thumbnail_requests)
        processed_count = 0
        
        self.emit_progress(0, f"Starting batch thumbnail generation: {total_requests} items")
        
        while processed_count < total_requests:
            if self.check_interruption():
                return
            
            # Get current memory usage
            current_memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
            
            # Calculate optimal batch size
            remaining_items = total_requests - processed_count
            batch_size = self.batch_processor.get_optimal_batch_size(
                remaining_items, current_memory_mb
            )
            
            # Process batch
            batch_start_time = time.time()
            batch_start_memory = current_memory_mb
            
            batch = self.thumbnail_requests[processed_count:processed_count + batch_size]
            batch_results = self._process_thumbnail_batch(batch, cache)
            
            # Record metrics
            batch_end_time = time.time()
            processing_time_ms = (batch_end_time - batch_start_time) * 1000
            success_count = len([r for r in batch_results if r['success']])
            
            self.batch_processor.record_batch_metrics(
                batch_size, current_memory_mb, processing_time_ms, 
                success_count, len(batch)
            )
            
            processed_count += len(batch)
            progress = int((processed_count / total_requests) * 100)
            
            self.emit_progress(
                progress, 
                f"Processed {processed_count}/{total_requests} thumbnails "
                f"(batch: {batch_size}, memory: {current_memory_mb:.1f}MB)"
            )
            
            # Emit batch results
            self.batch_completed.emit(batch_results, {
                'batch_size': batch_size,
                'memory_mb': current_memory_mb,
                'processing_time_ms': processing_time_ms,
                'success_rate': success_count / len(batch)
            })

    def _process_thumbnail_batch(self, batch: List[Tuple[str, int, int]], 
                                cache) -> List[Dict[str, Any]]:
        """Process single batch of thumbnails."""
        results = []
        
        for path, width, height in batch:
            try:
                # Check cache first
                cached_pixmap = cache.get_thumbnail(path, width, height)
                if cached_pixmap:
                    results.append({
                        'path': path,
                        'width': width,
                        'height': height,
                        'pixmap': cached_pixmap,
                        'success': True,
                        'source': 'cache'
                    })
                    continue
                
                # Generate thumbnail
                pixmap = create_thumbnail_from_file(path, width, height)
                if not pixmap.isNull():
                    cache.add_thumbnail(path, width, height, pixmap)
                    results.append({
                        'path': path,
                        'width': width,
                        'height': height,
                        'pixmap': pixmap,
                        'success': True,
                        'source': 'generated'
                    })
                else:
                    results.append({
                        'path': path,
                        'width': width,
                        'height': height,
                        'pixmap': None,
                        'success': False,
                        'error': 'Failed to generate thumbnail'
                    })
                    
            except Exception as e:
                results.append({
                    'path': path,
                    'width': width,
                    'height': height,
                    'pixmap': None,
                    'success': False,
                    'error': str(e)
                })
        
        return results
```

---

### PATCH 4: RESOURCE-AWARE CACHE MANAGEMENT

**Problem:** Duplicate cache operations i resource contention
**Rozwiązanie:** Unified cache access pattern z resource protection

```python
import threading
from contextlib import contextmanager

class ResourceAwareCacheManager:
    """
    Centralized cache management with resource protection and optimization.
    """
    
    def __init__(self):
        self._cache_lock = threading.RLock()
        self._access_stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'total_requests': 0
        }
        self._last_stats_log = time.time()

    @contextmanager
    def cache_operation(self):
        """Context manager for safe cache operations."""
        try:
            with self._cache_lock:
                yield
        except Exception as e:
            self._access_stats['errors'] += 1
            logger.error(f"Cache operation failed: {e}")
            raise

    def get_thumbnail_safe(self, cache, path: str, width: int, height: int):
        """Thread-safe thumbnail retrieval with stats."""
        with self.cache_operation():
            self._access_stats['total_requests'] += 1
            
            pixmap = cache.get_thumbnail(path, width, height)
            
            if pixmap:
                self._access_stats['hits'] += 1
                self._log_stats_periodic()
                return pixmap
            else:
                self._access_stats['misses'] += 1
                return None

    def add_thumbnail_safe(self, cache, path: str, width: int, height: int, pixmap):
        """Thread-safe thumbnail addition."""
        with self.cache_operation():
            cache.add_thumbnail(path, width, height, pixmap)

    def _log_stats_periodic(self):
        """Log cache statistics periodically."""
        current_time = time.time()
        if current_time - self._last_stats_log > 30:  # Every 30 seconds
            total = self._access_stats['total_requests']
            hits = self._access_stats['hits']
            hit_ratio = (hits / total * 100) if total > 0 else 0
            
            logger.info(
                f"Cache stats: {hit_ratio:.1f}% hit ratio "
                f"({hits}/{total} requests, {self._access_stats['errors']} errors)"
            )
            
            self._last_stats_log = current_time

# Global cache manager instance
_cache_manager = ResourceAwareCacheManager()

class OptimizedThumbnailWorker(UnifiedBaseWorker):
    """
    OPTIMIZED: Thumbnail worker with resource-aware cache management.
    """
    
    def __init__(self, path: str, width: int, height: int):
        super().__init__(timeout_seconds=30, priority=WorkerPriority.NORMAL)
        self.path = path
        self.width = width
        self.height = height

    def _run_implementation(self):
        """Single-pass cache operation with resource protection."""
        from src.ui.widgets.thumbnail_cache import ThumbnailCache
        from src.utils.image_utils import create_thumbnail_from_file
        
        cache = ThumbnailCache.get_instance()
        
        # Single cache check with resource protection
        cached_pixmap = _cache_manager.get_thumbnail_safe(
            cache, self.path, self.width, self.height
        )
        
        if cached_pixmap:
            # Cache hit - immediate return
            self.signals.thumbnail_finished.emit(
                cached_pixmap, self.path, self.width, self.height
            )
            return
        
        # Cache miss - generate thumbnail
        try:
            self.emit_progress(50, f"Generating thumbnail for {os.path.basename(self.path)}")
            
            pixmap = create_thumbnail_from_file(self.path, self.width, self.height)
            
            if pixmap.isNull():
                raise ValueError("Generated pixmap is null")
            
            # Add to cache with resource protection
            _cache_manager.add_thumbnail_safe(
                cache, self.path, self.width, self.height, pixmap
            )
            
            self.emit_progress(100, "Thumbnail generated and cached")
            self.signals.thumbnail_finished.emit(
                pixmap, self.path, self.width, self.height
            )
            
        except Exception as e:
            error_msg = f"Thumbnail generation failed: {str(e)}"
            self.signals.thumbnail_error.emit(
                error_msg, self.path, self.width, self.height
            )
            raise
```

---

### PATCH 5: INTELLIGENT PROGRESS REPORTING

**Problem:** Signal flooding przeciąża UI thread
**Rozwiązanie:** Smart throttling z UI responsiveness optimization

```python
import time
from collections import namedtuple

ProgressState = namedtuple('ProgressState', ['percent', 'message', 'timestamp'])

class IntelligentProgressReporter:
    """
    Smart progress reporting with UI responsiveness optimization.
    """
    
    def __init__(self, min_interval_ms: int = 50, max_interval_ms: int = 500):
        self.min_interval_ms = min_interval_ms
        self.max_interval_ms = max_interval_ms
        self.last_emit_time = 0
        self.last_progress_state = None
        self.progress_history = deque(maxlen=20)
        
    def should_emit_progress(self, current_percent: int, force: bool = False) -> bool:
        """Determine if progress should be emitted based on intelligent throttling."""
        current_time = time.time() * 1000  # milliseconds
        
        if force:
            return True
            
        # Always emit first and last progress
        if current_percent == 0 or current_percent == 100:
            return True
            
        # Check minimum interval
        time_since_last = current_time - self.last_emit_time
        if time_since_last < self.min_interval_ms:
            return False
            
        # For large operations, use adaptive intervals
        if len(self.progress_history) > 5:
            recent_rate = self._calculate_progress_rate()
            
            # Fast progress - less frequent updates
            if recent_rate > 10:  # >10% per second
                required_interval = self.max_interval_ms
            # Slow progress - more frequent updates
            elif recent_rate < 1:  # <1% per second
                required_interval = self.min_interval_ms
            else:
                # Adaptive interval based on rate
                required_interval = int(self.max_interval_ms / (recent_rate / 2))
                
            if time_since_last < required_interval:
                return False
        
        # Significant progress change (>5%)
        if self.last_progress_state:
            progress_diff = abs(current_percent - self.last_progress_state.percent)
            if progress_diff >= 5:
                return True
        
        # Default interval check
        return time_since_last >= self.min_interval_ms
    
    def emit_progress(self, worker, percent: int, message: str, force: bool = False):
        """Emit progress with intelligent throttling."""
        if self.should_emit_progress(percent, force):
            current_time = time.time() * 1000
            
            # Record progress state
            state = ProgressState(percent, message, current_time)
            self.progress_history.append(state)
            self.last_progress_state = state
            self.last_emit_time = current_time
            
            # Emit the signal
            worker.signals.progress.emit(percent, message)
    
    def _calculate_progress_rate(self) -> float:
        """Calculate recent progress rate in percent per second."""
        if len(self.progress_history) < 2:
            return 1.0
            
        recent_states = list(self.progress_history)[-5:]  # Last 5 states
        
        if len(recent_states) < 2:
            return 1.0
            
        first_state = recent_states[0]
        last_state = recent_states[-1]
        
        time_diff = (last_state.timestamp - first_state.timestamp) / 1000  # seconds
        progress_diff = last_state.percent - first_state.percent
        
        if time_diff <= 0:
            return 1.0
            
        return progress_diff / time_diff

class ProgressOptimizedWorker(UnifiedBaseWorker):
    """
    Base worker class with intelligent progress reporting.
    """
    
    def __init__(self, timeout_seconds: int = 300, priority: int = WorkerPriority.NORMAL):
        super().__init__(timeout_seconds, priority)
        self.progress_reporter = IntelligentProgressReporter()
    
    def emit_progress_smart(self, percent: int, message: str, force: bool = False):
        """Emit progress using intelligent throttling."""
        self.progress_reporter.emit_progress(self, percent, message, force)

class OptimizedDataProcessingWorker(ProgressOptimizedWorker):
    """
    Data processing worker with optimized progress reporting.
    """
    
    def _run_implementation(self):
        """Process data with smart progress updates."""
        total_pairs = len(self.file_pairs)
        
        # Force emit start
        self.emit_progress_smart(0, f"Starting to process {total_pairs} file pairs", force=True)
        
        batch_size = self._calculate_adaptive_batch_size(total_pairs)
        processed_count = 0
        
        for i in range(0, total_pairs, batch_size):
            if self.check_interruption():
                return
                
            batch = self.file_pairs[i:i + batch_size]
            
            # Process batch
            self._process_batch(batch)
            
            processed_count += len(batch)
            progress = int((processed_count / total_pairs) * 100)
            
            # Smart progress emission
            self.emit_progress_smart(
                progress, 
                f"Processed {processed_count}/{total_pairs} file pairs"
            )
        
        # Force emit completion
        self.emit_progress_smart(100, f"Completed processing {total_pairs} file pairs", force=True)
```

---

### PATCH 6: SIGNAL ARCHITECTURE CONSOLIDATION

**Problem:** Nadmierne sygnały przeciążają UI thread
**Rozwiązanie:** Consolidated signals z batch operations

```python
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class BatchUpdateData:
    """Consolidated data for batch UI updates."""
    thumbnail_updates: List[Dict[str, Any]]
    metadata_updates: List[Dict[str, Any]]
    progress_update: Dict[str, Any]
    error_updates: List[Dict[str, Any]]

class ConsolidatedSignalManager:
    """
    Manages signal consolidation to reduce UI thread load.
    """
    
    def __init__(self, consolidation_interval_ms: int = 100):
        self.consolidation_interval_ms = consolidation_interval_ms
        self.pending_updates = BatchUpdateData([], [], {}, [])
        self.last_emit_time = 0
        self.consolidation_timer = None
    
    def add_thumbnail_update(self, path: str, width: int, height: int, pixmap, source: str = 'generated'):
        """Add thumbnail update to pending batch."""
        self.pending_updates.thumbnail_updates.append({
            'path': path,
            'width': width,
            'height': height,
            'pixmap': pixmap,
            'source': source,
            'timestamp': time.time()
        })
        self._schedule_emit()
    
    def add_metadata_update(self, file_pairs: List, metadata_dict: Dict):
        """Add metadata update to pending batch."""
        self.pending_updates.metadata_updates.append({
            'file_pairs': file_pairs,
            'metadata': metadata_dict,
            'timestamp': time.time()
        })
        self._schedule_emit()
    
    def add_progress_update(self, percent: int, message: str):
        """Update progress (only latest is kept)."""
        self.pending_updates.progress_update = {
            'percent': percent,
            'message': message,
            'timestamp': time.time()
        }
        self._schedule_emit()
    
    def add_error_update(self, error_message: str, context: Dict = None):
        """Add error update to pending batch."""
        self.pending_updates.error_updates.append({
            'message': error_message,
            'context': context or {},
            'timestamp': time.time()
        })
        self._schedule_emit()
    
    def _schedule_emit(self):
        """Schedule consolidated emit if not already scheduled."""
        current_time = time.time() * 1000
        
        if self.consolidation_timer is None:
            # Calculate delay until next emit
            time_since_last = current_time - self.last_emit_time
            delay = max(0, self.consolidation_interval_ms - time_since_last)
            
            # Schedule emit
            from PyQt6.QtCore import QTimer
            self.consolidation_timer = QTimer()
            self.consolidation_timer.setSingleShot(True)
            self.consolidation_timer.timeout.connect(self._emit_consolidated)
            self.consolidation_timer.start(int(delay))
    
    def _emit_consolidated(self):
        """Emit all pending updates in a single batch."""
        if self._has_pending_updates():
            # Emit consolidated batch update signal
            self.batch_update_ready.emit(self.pending_updates)
            
            # Clear pending updates
            self.pending_updates = BatchUpdateData([], [], {}, [])
            self.last_emit_time = time.time() * 1000
        
        # Reset timer
        self.consolidation_timer = None
    
    def _has_pending_updates(self) -> bool:
        """Check if there are any pending updates."""
        return (
            len(self.pending_updates.thumbnail_updates) > 0 or
            len(self.pending_updates.metadata_updates) > 0 or
            len(self.pending_updates.progress_update) > 0 or
            len(self.pending_updates.error_updates) > 0
        )

class ConsolidatedProcessingWorker(UnifiedBaseWorker):
    """
    Processing worker with consolidated signal architecture.
    """
    
    # Single consolidated signal for all updates
    batch_update_ready = pyqtSignal(object)  # BatchUpdateData
    
    def __init__(self, file_pairs: List, working_directory: str):
        super().__init__(timeout_seconds=300, priority=WorkerPriority.HIGH)
        self.file_pairs = file_pairs
        self.working_directory = working_directory
        self.signal_manager = ConsolidatedSignalManager()
        
        # Connect signal manager to worker signal
        self.signal_manager.batch_update_ready = self.batch_update_ready
    
    def _run_implementation(self):
        """Process with consolidated signaling."""
        from src.ui.widgets.thumbnail_cache import ThumbnailCache
        from src.logic.metadata_manager import MetadataManager
        
        cache = ThumbnailCache.get_instance()
        metadata_manager = MetadataManager.get_instance(self.working_directory)
        
        total_pairs = len(self.file_pairs)
        
        # Initial progress
        self.signal_manager.add_progress_update(0, f"Starting processing {total_pairs} items")
        
        for i, file_pair in enumerate(self.file_pairs):
            if self.check_interruption():
                return
            
            try:
                # Process thumbnail (if needed)
                self._process_file_pair_thumbnail(file_pair, cache)
                
                # Process metadata (if needed)
                self._process_file_pair_metadata(file_pair, metadata_manager)
                
                # Update progress periodically
                if i % 10 == 0 or i == total_pairs - 1:
                    progress = int((i + 1) / total_pairs * 100)
                    self.signal_manager.add_progress_update(
                        progress, f"Processed {i + 1}/{total_pairs} items"
                    )
                
            except Exception as e:
                self.signal_manager.add_error_update(
                    f"Failed to process file pair: {str(e)}",
                    {'file_pair': file_pair.get_base_name(), 'index': i}
                )
        
        # Force final emit
        self.signal_manager._emit_consolidated()
        self.signals.finished.emit(f"Processed {total_pairs} file pairs")
    
    def _process_file_pair_thumbnail(self, file_pair, cache):
        """Process thumbnail for file pair."""
        # Check if thumbnail exists in cache
        preview_path = file_pair.get_preview_path()
        if preview_path:
            cached = cache.get_thumbnail(preview_path, 150, 150)
            if not cached:
                # Generate thumbnail
                try:
                    from src.utils.image_utils import create_thumbnail_from_file
                    pixmap = create_thumbnail_from_file(preview_path, 150, 150)
                    
                    if not pixmap.isNull():
                        cache.add_thumbnail(preview_path, 150, 150, pixmap)
                        self.signal_manager.add_thumbnail_update(
                            preview_path, 150, 150, pixmap, 'generated'
                        )
                except Exception as e:
                    self.signal_manager.add_error_update(
                        f"Thumbnail generation failed: {str(e)}",
                        {'path': preview_path}
                    )
    
    def _process_file_pair_metadata(self, file_pair, metadata_manager):
        """Process metadata for file pair."""
        base_name = file_pair.get_base_name()
        
        # Load metadata
        stars = metadata_manager.get_stars(base_name)
        color = metadata_manager.get_color_tag(base_name)
        
        if stars > 0 or color:
            file_pair.set_stars(stars)
            file_pair.set_color_tag(color)
            
            self.signal_manager.add_metadata_update(
                [file_pair],
                {base_name: {'stars': stars, 'color': color}}
            )
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Worker lifecycle** - czy wszystkie workers starują, emitują progress i kończą poprawnie
- [ ] **Signal emission** - czy wszystkie sygnały są emitowane w odpowiednim czasie
- [ ] **Batch processing** - czy batch operations działają poprawnie dla różnych rozmiarów folderów
- [ ] **Cache integration** - czy thumbnail cache jest używany efektywnie
- [ ] **Metadata operations** - czy async loading/saving metadanych działa poprawnie
- [ ] **Progress reporting** - czy progress bar jest smooth i accurate
- [ ] **Error handling** - czy błędy są properly handled i reported
- [ ] **Resource management** - czy memory usage jest pod kontrolą
- [ ] **Thread safety** - czy concurrent operations są bezpieczne
- [ ] **UI responsiveness** - czy UI nie blokuje podczas processing

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Base workers** - czy UnifiedBaseWorker integration działa poprawnie
- [ ] **ThumbnailCache** - czy lazy import i cache operations działają
- [ ] **MetadataManager** - czy async metadata operations są stabilne
- [ ] **Image utils** - czy thumbnail generation działa z nową architekturą
- [ ] **File pair model** - czy operacje na FilePair są kompatybilne
- [ ] **Qt signals** - czy sygnały są properly connected i emitted
- [ ] **Gallery tab** - czy integration z gallery UI działa
- [ ] **Main window** - czy worker management jest kompatybilny

#### **TESTY WERYFIKACYJNE:**

- [ ] **Small folder test** - <100 plików processing
- [ ] **Medium folder test** - 100-1000 plików processing
- [ ] **Large folder test** - 3000+ plików processing
- [ ] **Memory stress test** - monitoring memory usage podczas batch operations
- [ ] **Concurrent workers test** - multiple workers running simultaneously
- [ ] **Error scenarios test** - corrupted files, missing permissions, network issues

#### **KRYTERIA SUKCESU:**

- [ ] **Gallery loading <5s** dla 3000+ plików
- [ ] **Memory usage <1GB** podczas large folder processing
- [ ] **UI responsive** - no freezes >100ms
- [ ] **Progress bar smooth** - accurate progress reporting
- [ ] **Error recovery** - graceful handling błędów
- [ ] **Resource cleanup** - proper cleanup po zakończeniu workers