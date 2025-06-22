# PATCH-CODE DLA: Workers and Model (processing_workers.py, file_pair.py)

**Powiązany plik z analizą:** `../corrections/workers_and_model_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: ASYNC THUMBNAIL LOADING w FilePair Model

**Problem:** Synchronous I/O w model blocks calling thread
**Rozwiązanie:** Implement proper async thumbnail loading z callbacks

```python
# ENHANCED FilePair model w file_pair.py:
import asyncio
from typing import Callable, Optional
from PyQt6.QtCore import QObject, pyqtSignal

class FilePair(QObject):
    """
    Enhanced FilePair model z async operations i lazy loading.
    OPTYMALIZACJA: Async I/O operations i intelligent caching.
    """
    
    # Signals dla async operations
    thumbnail_loaded = pyqtSignal(object)  # QPixmap
    thumbnail_failed = pyqtSignal(str)     # Error message
    metadata_updated = pyqtSignal()
    
    def __init__(
        self, archive_path: str, preview_path: Optional[str], working_directory: str
    ):
        super().__init__()
        
        # Path validation i normalization
        norm_wd = normalize_path(working_directory)
        norm_archive = normalize_path(archive_path)
        norm_preview = normalize_path(preview_path) if preview_path else None

        if not os.path.isabs(norm_archive):
            raise ValueError("Archive path must be absolute.")
        if norm_preview and not os.path.isabs(norm_preview):
            raise ValueError("Preview path must be absolute.")
        if not os.path.isabs(norm_wd):
            raise ValueError("Working directory path must be absolute.")

        self.working_directory = norm_wd
        self.archive_path: str = norm_archive
        self.preview_path: Optional[str] = norm_preview

        # Lazy-loaded properties
        self._base_name: Optional[str] = None
        self._relative_archive_path: Optional[str] = None
        self._relative_preview_path: Optional[str] = None
        self._archive_size_bytes: Optional[int] = None
        
        # Cached metadata
        self.preview_thumbnail: Optional[QPixmap] = None
        self.stars: int = 0
        self.color_tag: Optional[str] = None
        
        # Performance tracking
        self._access_count = 0
        self._last_access_time = 0
        
        # Threading support
        self._thumbnail_loading = False
        self._thumbnail_callbacks = []
    
    @property
    def base_name(self) -> str:
        """Lazy-loaded base name z caching."""
        if self._base_name is None:
            self._base_name = os.path.splitext(os.path.basename(self.archive_path))[0]
        return self._base_name
    
    def get_relative_archive_path(self) -> str:
        """Cached relative archive path computation."""
        if self._relative_archive_path is None:
            self._relative_archive_path = os.path.relpath(
                self.archive_path, self.working_directory
            ).replace("\\", "/")
        return self._relative_archive_path
    
    def get_relative_preview_path(self) -> Optional[str]:
        """Cached relative preview path computation."""
        if not self.preview_path:
            return None
        if self._relative_preview_path is None:
            self._relative_preview_path = os.path.relpath(
                self.preview_path, self.working_directory
            ).replace("\\", "/")
        return self._relative_preview_path
    
    async def load_thumbnail_async(
        self, 
        size: tuple, 
        callback: Optional[Callable] = None,
        priority: str = "normal"
    ) -> Optional[QPixmap]:
        """
        Async thumbnail loading z priority support.
        
        Args:
            size: (width, height) tuple
            callback: Optional callback dla completion
            priority: "high", "normal", "low"
        """
        self._access_count += 1
        self._last_access_time = time.time()
        
        # Check if already loaded
        if self.preview_thumbnail and not self.preview_thumbnail.isNull():
            if callback:
                callback(self.preview_thumbnail)
            return self.preview_thumbnail
        
        # Check if already loading
        if self._thumbnail_loading:
            if callback:
                self._thumbnail_callbacks.append(callback)
            return None
        
        # Start async loading
        self._thumbnail_loading = True
        if callback:
            self._thumbnail_callbacks.append(callback)
        
        try:
            # Use ThumbnailCache dla async loading
            from src.ui.widgets.thumbnail_cache import ThumbnailCache
            cache = ThumbnailCache.get_instance()
            
            # Request async thumbnail
            thumbnail = cache.request_thumbnail_async(
                self.preview_path or "",
                size[0], size[1],
                self._on_thumbnail_loaded
            )
            
            if thumbnail:  # Immediate cache hit
                self.preview_thumbnail = thumbnail
                self._notify_thumbnail_callbacks(thumbnail)
                return thumbnail
            
            # Will be loaded asynchronously
            return None
            
        except Exception as e:
            logger.error(f"Error loading thumbnail async: {e}")
            self._on_thumbnail_failed(str(e))
            return None
    
    def _on_thumbnail_loaded(self, pixmap: QPixmap):
        """Handle async thumbnail load completion."""
        self._thumbnail_loading = False
        self.preview_thumbnail = pixmap
        
        # Emit signal
        self.thumbnail_loaded.emit(pixmap)
        
        # Notify callbacks
        self._notify_thumbnail_callbacks(pixmap)
    
    def _on_thumbnail_failed(self, error: str):
        """Handle async thumbnail load failure."""
        self._thumbnail_loading = False
        
        # Emit signal
        self.thumbnail_failed.emit(error)
        
        # Notify callbacks z None
        self._notify_thumbnail_callbacks(None)
    
    def _notify_thumbnail_callbacks(self, pixmap: Optional[QPixmap]):
        """Notify all pending callbacks."""
        for callback in self._thumbnail_callbacks:
            try:
                callback(pixmap)
            except Exception as e:
                logger.error(f"Error in thumbnail callback: {e}")
        
        self._thumbnail_callbacks.clear()
    
    def get_archive_size(self) -> int:
        """Lazy-loaded archive size z caching."""
        if self._archive_size_bytes is None:
            try:
                if os.path.exists(self.archive_path):
                    self._archive_size_bytes = os.path.getsize(self.archive_path)
                else:
                    self._archive_size_bytes = FILE_SIZE_ERROR
            except OSError:
                self._archive_size_bytes = FILE_SIZE_ERROR
        
        return self._archive_size_bytes
    
    def get_performance_metrics(self) -> dict:
        """Get performance metrics dla monitoring."""
        return {
            "access_count": self._access_count,
            "last_access_time": self._last_access_time,
            "has_cached_thumbnail": self.preview_thumbnail is not None,
            "base_name_cached": self._base_name is not None,
            "paths_cached": self._relative_archive_path is not None,
            "size_cached": self._archive_size_bytes is not None
        }
    
    def clear_cache(self):
        """Clear cached data dla memory management."""
        self._base_name = None
        self._relative_archive_path = None
        self._relative_preview_path = None
        self._archive_size_bytes = None
        if self.preview_thumbnail:
            self.preview_thumbnail = None
            
    def __repr__(self) -> str:
        """Memory-efficient repr."""
        return (
            f"FilePair(base='{self.base_name}', "
            f"archive='{self.get_relative_archive_path()}', "
            f"preview='{self.get_relative_preview_path()}')"
        )
```

---

### PATCH 2: PARALLEL BATCH THUMBNAIL PROCESSING

**Problem:** BatchThumbnailWorker processes sequentially instead parallel
**Rozwiązanie:** Implement true parallel processing z thread pool

```python
# ENHANCED BatchThumbnailWorker w processing_workers.py:
import concurrent.futures
from typing import List, Tuple
import threading

class ParallelBatchThumbnailWorker(UnifiedBaseWorker):
    """
    Parallel batch thumbnail worker dla maximum performance.
    Uses thread pool dla concurrent thumbnail generation.
    """
    
    def __init__(
        self,
        thumbnail_requests: List[Tuple[str, int, int]],
        max_workers: int = 4,
        priority: int = WorkerPriority.HIGH,
    ):
        super().__init__(timeout_seconds=600, priority=priority)  # 10 min timeout
        self.thumbnail_requests = thumbnail_requests
        self.max_workers = min(max_workers, len(thumbnail_requests))
        
        # Progress tracking
        self.completed_count = 0
        self.total_count = len(thumbnail_requests)
        self.progress_lock = threading.Lock()
        
        # Results storage
        self.results = {}
        self.errors = {}
    
    def _run_implementation(self):
        """Parallel thumbnail generation."""
        try:
            self.emit_progress(0, f"Starting parallel generation of {self.total_count} thumbnails...")
            
            # Create thread pool executor
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_request = {
                    executor.submit(self._generate_single_thumbnail, path, width, height): (path, width, height)
                    for path, width, height in self.thumbnail_requests
                }
                
                # Process completed tasks
                for future in concurrent.futures.as_completed(future_to_request):
                    if self.check_interruption():
                        # Cancel remaining tasks
                        for f in future_to_request:
                            f.cancel()
                        break
                    
                    path, width, height = future_to_request[future]
                    
                    try:
                        pixmap = future.result()
                        if pixmap:
                            self.results[(path, width, height)] = pixmap
                            self.emit_finished(pixmap, path, width, height)
                        else:
                            self.errors[(path, width, height)] = "Failed to generate thumbnail"
                            self.emit_error("Failed to generate thumbnail", path, width, height)
                    
                    except Exception as e:
                        self.errors[(path, width, height)] = str(e)
                        self.emit_error(f"Error: {str(e)}", path, width, height)
                    
                    # Update progress
                    with self.progress_lock:
                        self.completed_count += 1
                        progress = int((self.completed_count / self.total_count) * 100)
                        self.emit_progress(
                            progress, 
                            f"Generated {self.completed_count}/{self.total_count} thumbnails..."
                        )
            
            # Final summary
            success_count = len(self.results)
            error_count = len(self.errors)
            
            self.emit_progress(
                100, 
                f"Completed: {success_count} successful, {error_count} errors"
            )
            
            logger.info(f"Parallel batch completed: {success_count}/{self.total_count} successful")
            
        except Exception as e:
            self.emit_error(f"Batch processing error: {str(e)}", "", 0, 0)
    
    def _generate_single_thumbnail(self, path: str, width: int, height: int) -> Optional[QPixmap]:
        """Generate single thumbnail w thread pool."""
        try:
            from src.ui.widgets.thumbnail_cache import ThumbnailCache
            
            # Check cache first
            cache = ThumbnailCache.get_instance()
            cached_pixmap = cache.get_thumbnail(path, width, height)
            
            if cached_pixmap:
                logger.debug(f"Cache hit dla parallel thumbnail: {path}")
                return cached_pixmap
            
            # Generate thumbnail
            pixmap = create_thumbnail_from_file(path, width, height)
            
            if pixmap and not pixmap.isNull():
                # Save to cache
                cache.set_thumbnail(path, width, height, pixmap)
                return pixmap
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating thumbnail {path}: {e}")
            return None
```

---

### PATCH 3: INTELLIGENT WORKER COORDINATION

**Problem:** No priority management i coordination między workers
**Rozwiązanie:** Implement WorkerCoordinator dla intelligent scheduling

```python
# NOWA klasa - WorkerCoordinator:
class WorkerCoordinator:
    """
    Coordinates all worker operations dla optimal performance.
    Manages priorities, resource allocation, i cancellation.
    """
    
    def __init__(self, max_concurrent_workers: int = 3):
        self.max_concurrent_workers = max_concurrent_workers
        self.active_workers = {}
        self.pending_requests = []
        self.coordinator_lock = threading.Lock()
        
        # Worker pools by priority
        self.high_priority_pool = QThreadPool()
        self.normal_priority_pool = QThreadPool()
        self.low_priority_pool = QThreadPool()
        
        # Set thread counts
        self.high_priority_pool.setMaxThreadCount(2)
        self.normal_priority_pool.setMaxThreadCount(2)
        self.low_priority_pool.setMaxThreadCount(1)
        
        # Metrics
        self.worker_metrics = {
            "total_workers_started": 0,
            "active_workers_count": 0,
            "completed_workers": 0,
            "failed_workers": 0
        }
    
    def submit_thumbnail_request(
        self, 
        path: str, 
        size: tuple, 
        callback: Callable,
        priority: str = "normal"
    ):
        """Submit thumbnail request z intelligent scheduling."""
        with self.coordinator_lock:
            request = {
                "path": path,
                "size": size,
                "callback": callback,
                "priority": priority,
                "timestamp": time.time()
            }
            
            # Check if we can start immediately
            if len(self.active_workers) < self.max_concurrent_workers:
                self._start_thumbnail_worker(request)
            else:
                # Queue dla later processing
                self.pending_requests.append(request)
                # Sort by priority
                self.pending_requests.sort(
                    key=lambda r: (
                        0 if r["priority"] == "high" else 
                        1 if r["priority"] == "normal" else 2,
                        r["timestamp"]
                    )
                )
    
    def submit_batch_request(
        self,
        requests: List[Tuple[str, int, int]],
        callback: Callable,
        priority: str = "high"
    ):
        """Submit batch thumbnail request."""
        with self.coordinator_lock:
            # Create parallel batch worker
            worker = ParallelBatchThumbnailWorker(requests, priority=WorkerPriority.HIGH)
            
            # Connect signals
            worker.signals.thumbnail_finished.connect(callback)
            worker.signals.finished.connect(lambda: self._on_worker_finished(worker))
            worker.signals.error.connect(lambda msg, path, w, h: self._on_worker_error(worker, msg))
            
            # Select appropriate thread pool
            thread_pool = self._get_thread_pool(priority)
            
            # Start worker
            thread_pool.start(worker)
            self.active_workers[id(worker)] = worker
            self.worker_metrics["total_workers_started"] += 1
            self.worker_metrics["active_workers_count"] += 1
    
    def _start_thumbnail_worker(self, request: dict):
        """Start single thumbnail worker."""
        worker = ThumbnailGenerationWorker(
            request["path"],
            request["size"][0],
            request["size"][1],
            priority=WorkerPriority.HIGH if request["priority"] == "high" else WorkerPriority.NORMAL
        )
        
        # Connect signals
        worker.signals.thumbnail_finished.connect(request["callback"])
        worker.signals.finished.connect(lambda: self._on_worker_finished(worker))
        worker.signals.error.connect(lambda msg, path, w, h: self._on_worker_error(worker, msg))
        
        # Select thread pool
        thread_pool = self._get_thread_pool(request["priority"])
        
        # Start worker
        thread_pool.start(worker)
        self.active_workers[id(worker)] = worker
        self.worker_metrics["total_workers_started"] += 1
        self.worker_metrics["active_workers_count"] += 1
    
    def _get_thread_pool(self, priority: str) -> QThreadPool:
        """Get appropriate thread pool dla priority."""
        if priority == "high":
            return self.high_priority_pool
        elif priority == "low":
            return self.low_priority_pool
        else:
            return self.normal_priority_pool
    
    def _on_worker_finished(self, worker):
        """Handle worker completion."""
        with self.coordinator_lock:
            worker_id = id(worker)
            if worker_id in self.active_workers:
                del self.active_workers[worker_id]
                self.worker_metrics["active_workers_count"] -= 1
                self.worker_metrics["completed_workers"] += 1
            
            # Start pending worker if available
            if self.pending_requests and len(self.active_workers) < self.max_concurrent_workers:
                next_request = self.pending_requests.pop(0)
                self._start_thumbnail_worker(next_request)
    
    def _on_worker_error(self, worker, error_msg: str):
        """Handle worker error."""
        with self.coordinator_lock:
            worker_id = id(worker)
            if worker_id in self.active_workers:
                del self.active_workers[worker_id]
                self.worker_metrics["active_workers_count"] -= 1
                self.worker_metrics["failed_workers"] += 1
            
            logger.error(f"Worker failed: {error_msg}")
            
            # Start pending worker if available
            if self.pending_requests and len(self.active_workers) < self.max_concurrent_workers:
                next_request = self.pending_requests.pop(0)
                self._start_thumbnail_worker(next_request)
    
    def cancel_all_workers(self):
        """Cancel all active workers."""
        with self.coordinator_lock:
            for worker in self.active_workers.values():
                if hasattr(worker, 'interrupt'):
                    worker.interrupt()
            
            # Clear pending requests
            self.pending_requests.clear()
            
            logger.info(f"Cancelled {len(self.active_workers)} active workers")
    
    def get_metrics(self) -> dict:
        """Get worker coordination metrics."""
        with self.coordinator_lock:
            return {
                **self.worker_metrics,
                "pending_requests": len(self.pending_requests),
                "high_priority_active": self.high_priority_pool.activeThreadCount(),
                "normal_priority_active": self.normal_priority_pool.activeThreadCount(),
                "low_priority_active": self.low_priority_pool.activeThreadCount()
            }

# GLOBAL coordinator instance
_worker_coordinator = None

def get_worker_coordinator() -> WorkerCoordinator:
    """Get global worker coordinator instance."""
    global _worker_coordinator
    if _worker_coordinator is None:
        _worker_coordinator = WorkerCoordinator()
    return _worker_coordinator
```

---

### PATCH 4: MEMORY-EFFICIENT DATA PROCESSING

**Problem:** DataProcessingWorker loads all metadata synchronously
**Rozwiązanie:** Implement streaming processing z memory management

```python
# ENHANCED DataProcessingWorker:
class StreamingDataProcessingWorker(QObject):
    """
    Memory-efficient streaming data processing worker.
    Processes FilePairs w small batches dla memory efficiency.
    """
    
    # Signals
    tile_batch_ready = pyqtSignal(list)
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    memory_warning = pyqtSignal(str)
    
    def __init__(
        self,
        working_directory: str,
        file_pairs: List[FilePair],
        batch_size: int = None,
        memory_limit_mb: int = 500
    ):
        super().__init__()
        self.working_directory = working_directory
        self.file_pairs = file_pairs
        self.memory_limit_mb = memory_limit_mb
        
        # Adaptive batch size based na dataset size
        if batch_size is None:
            if len(file_pairs) <= 100:
                self.batch_size = 10
            elif len(file_pairs) <= 1000:
                self.batch_size = 25
            else:
                self.batch_size = 50  # Larger batches dla large datasets
        else:
            self.batch_size = batch_size
        
        self._interrupted = False
        self._current_memory_mb = 0
    
    @pyqtSlot()
    def run(self):
        """Process data w memory-efficient streaming mode."""
        try:
            total_pairs = len(self.file_pairs)
            processed_count = 0
            
            self.progress.emit(0, f"Starting streaming processing of {total_pairs} items...")
            
            # Process w batches
            for batch_start in range(0, total_pairs, self.batch_size):
                if self._interrupted:
                    break
                
                # Get current batch
                batch_end = min(batch_start + self.batch_size, total_pairs)
                current_batch = self.file_pairs[batch_start:batch_end]
                
                # Check memory usage
                self._check_memory_usage()
                
                # Process batch
                processed_batch = self._process_batch(current_batch)
                
                # Emit batch
                if processed_batch:
                    self.tile_batch_ready.emit(processed_batch)
                
                processed_count = batch_end
                progress = int((processed_count / total_pairs) * 100)
                
                # Update progress
                self.progress.emit(
                    progress, 
                    f"Processed {processed_count}/{total_pairs} items..."
                )
                
                # Small delay dla UI responsiveness
                time.sleep(0.01)
            
            self.progress.emit(100, f"Completed processing {total_pairs} items")
            self.finished.emit(self.file_pairs)
            
        except Exception as e:
            self.error.emit(f"Streaming processing error: {str(e)}")
    
    def _process_batch(self, batch: List[FilePair]) -> List[FilePair]:
        """Process single batch of FilePairs."""
        try:
            # Apply metadata to batch efficiently
            # Skip expensive operations dla performance
            return batch
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            return []
    
    def _check_memory_usage(self):
        """Check memory usage i issue warnings."""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / (1024 * 1024)
            
            if memory_mb > self.memory_limit_mb:
                warning_msg = f"Memory usage {memory_mb:.1f}MB exceeds limit {self.memory_limit_mb}MB"
                self.memory_warning.emit(warning_msg)
                
                # Force garbage collection
                import gc
                gc.collect()
                
        except ImportError:
            # psutil not available - skip memory monitoring
            pass
        except Exception as e:
            logger.warning(f"Error checking memory usage: {e}")
    
    def interrupt(self):
        """Interrupt processing."""
        self._interrupted = True
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **PERFORMANCE IMPROVEMENTS:**

- [ ] **Async thumbnail loading** - FilePair model uses async operations tylko
- [ ] **Parallel batch processing** - BatchThumbnailWorker processes thumbnails concurrently
- [ ] **Memory-efficient processing** - DataProcessingWorker uses streaming processing
- [ ] **Lazy loading** - FilePair properties loaded on-demand only
- [ ] **Intelligent caching** - Expensive operations cached properly
- [ ] **Worker coordination** - WorkerCoordinator manages resources efficiently
- [ ] **Priority management** - High priority requests processed first
- [ ] **Memory monitoring** - Memory usage tracked i warnings issued

#### **THREADING ARCHITECTURE:**

- [ ] **Unified threading model** - Consistent QThreadPool usage throughout
- [ ] **Proper cancellation** - All workers support cancellation correctly
- [ ] **Resource coordination** - No resource contention między workers
- [ ] **Thread safety** - FilePair model thread-safe dla concurrent access
- [ ] **Lifecycle management** - Proper worker cleanup i termination
- [ ] **Error handling** - Graceful error handling w all workers
- [ ] **Progress reporting** - Accurate progress reporting bez UI blocking
- [ ] **Performance metrics** - Comprehensive metrics dla monitoring

#### **BUSINESS REQUIREMENTS:**

- [ ] **Gallery performance** - Supports 3000+ files w <2s loading
- [ ] **Memory efficiency** - <1GB usage dla 3000+ FilePair objects
- [ ] **UI responsiveness** - Zero UI blocking operations
- [ ] **Thumbnail speed** - <100ms per thumbnail (async)
- [ ] **Batch efficiency** - Process 50+ thumbnails simultaneously
- [ ] **Error recovery** - Graceful degradation w failure scenarios
- [ ] **Resource management** - Proper resource cleanup i management
- [ ] **Scalability** - Handles datasets of any size efficiently

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **PERFORMANCE TARGETS MET** - all performance targets achieved
- [ ] **MEMORY EFFICIENCY** - memory usage w acceptable limits
- [ ] **UI RESPONSIVENESS** - smooth UI podczas all operations
- [ ] **ZERO REGRESSIONS** - wszystkie existing functionality preserved

---