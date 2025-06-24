# PATCH-CODE DLA: GALLERY_MANAGER.PY

**Powiązany plik z analizą:** `../corrections/gallery_manager_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: PROGRESSIVE TILE CREATION Z PROGRESS FEEDBACK

**Problem:** `force_create_all_tiles()` blokuje UI przy tworzeniu tysięcy kafli synchronicznie
**Rozwiązanie:** Implementacja chunked progressive loading z progress feedback i cancel support

```python
# Dodaj na początku pliku po importach
from PyQt6.QtCore import QThread, QObject, pyqtSignal, QMutex, QMutexLocker
import concurrent.futures
import psutil  # Do monitoring system performance

class ProgressiveTileCreator(QObject):
    """Worker do asynchronicznego tworzenia kafli z progress feedback."""
    
    # Signals dla progress feedback
    progress_updated = pyqtSignal(int, int, str)  # current, total, status_text
    chunk_completed = pyqtSignal(int, list)  # chunk_id, widgets_created
    creation_finished = pyqtSignal(bool, str)  # success, error_msg
    
    def __init__(self, gallery_manager):
        super().__init__()
        self.gallery_manager = gallery_manager
        self._cancel_requested = False
        self._mutex = QMutex()
        
        # Adaptive configuration based na system specs
        self._configure_adaptive_settings()
        
    def _configure_adaptive_settings(self):
        """Configure settings based na system performance."""
        try:
            # Get system specs
            cpu_count = psutil.cpu_count(logical=True)
            memory_gb = psutil.virtual_memory().total / (1024**3)
            
            # Adaptive batch sizes
            if memory_gb >= 16 and cpu_count >= 8:
                self.chunk_size = 150  # High-end system
                self.process_events_interval = 3
            elif memory_gb >= 8 and cpu_count >= 4:
                self.chunk_size = 100  # Mid-range system
                self.process_events_interval = 2
            else:
                self.chunk_size = 50   # Low-end system
                self.process_events_interval = 1
                
        except Exception:
            # Fallback values
            self.chunk_size = 75
            self.process_events_interval = 2
    
    def create_tiles_progressive(self, special_folders: list, file_pairs: list):
        """Start progressive tile creation."""
        with QMutexLocker(self._mutex):
            self._cancel_requested = False
        
        try:
            all_items = special_folders + file_pairs
            total_items = len(all_items)
            
            if total_items == 0:
                self.creation_finished.emit(True, "No items to create")
                return
            
            # Calculate chunks
            chunks = []
            for i in range(0, total_items, self.chunk_size):
                chunk_items = all_items[i:i + self.chunk_size]
                chunks.append((i // self.chunk_size, chunk_items, i))
            
            # Process chunks progressively
            created_widgets = []
            for chunk_id, chunk_items, start_index in chunks:
                
                # Check for cancellation
                with QMutexLocker(self._mutex):
                    if self._cancel_requested:
                        self.creation_finished.emit(False, "Operation cancelled by user")
                        return
                
                # Update progress
                progress_text = f"Creating tiles {start_index + 1}-{start_index + len(chunk_items)} of {total_items}"
                self.progress_updated.emit(start_index, total_items, progress_text)
                
                # Create chunk widgets
                chunk_widgets = self._create_chunk_widgets(chunk_items, start_index)
                created_widgets.extend(chunk_widgets)
                
                # Emit chunk completion
                self.chunk_completed.emit(chunk_id, chunk_widgets)
                
                # Process events co X chunks dla UI responsiveness
                if chunk_id % self.process_events_interval == 0:
                    from PyQt6.QtWidgets import QApplication
                    QApplication.processEvents()
                    
                    # Yield control na moment
                    import time
                    time.sleep(0.001)  # 1ms yield
            
            self.creation_finished.emit(True, f"Successfully created {len(created_widgets)} tiles")
            
        except Exception as e:
            self.creation_finished.emit(False, f"Error during tile creation: {str(e)}")
    
    def _create_chunk_widgets(self, chunk_items: list, start_index: int) -> list:
        """Create widgets dla single chunk."""
        widgets = []
        
        for i, item in enumerate(chunk_items):
            try:
                # Check cancellation frequently
                with QMutexLocker(self._mutex):
                    if self._cancel_requested:
                        break
                
                widget = None
                if hasattr(item, 'get_folder_path'):  # SpecialFolder
                    widget = self.gallery_manager.create_folder_widget(item)
                else:  # FilePair
                    widget = self.gallery_manager.create_tile_widget_for_pair(
                        item, self.gallery_manager.tiles_container
                    )
                
                if widget:
                    widgets.append((start_index + i, widget, item))
                    
            except Exception as e:
                logging.error(f"Failed to create widget for item {i}: {e}")
                continue
        
        return widgets
    
    def cancel_creation(self):
        """Cancel ongoing tile creation."""
        with QMutexLocker(self._mutex):
            self._cancel_requested = True

# W klasie GalleryManager dodaj:
def __init__(self, main_window, tiles_container, tiles_layout, scroll_area):
    # ... istniejący kod ...
    
    # Progressive tile creator
    self._progressive_creator = ProgressiveTileCreator(self)
    self._progressive_creator.progress_updated.connect(self._on_tile_creation_progress)
    self._progressive_creator.chunk_completed.connect(self._on_chunk_completed)
    self._progressive_creator.creation_finished.connect(self._on_tile_creation_finished)
    
    # Progress tracking
    self._tile_creation_in_progress = False
    self._created_tiles_buffer = []

def _on_tile_creation_progress(self, current: int, total: int, status: str):
    """Handle progress updates dla tile creation."""
    progress_percent = (current * 100) // total if total > 0 else 0
    logging.info(f"Tile creation progress: {progress_percent}% - {status}")
    
    # Można dodać progress bar w przyszłości
    # if hasattr(self.main_window, 'show_progress'):
    #     self.main_window.show_progress(progress_percent, status)

def _on_chunk_completed(self, chunk_id: int, chunk_widgets: list):
    """Handle completion pojedynczego chunk."""
    # Dodaj widgets do layout w UI thread
    geometry = self._get_cached_geometry()
    cols = geometry["cols"]
    
    for tile_index, widget, item in chunk_widgets:
        if widget:
            # Setup widget connections
            self._setup_widget_connections(widget, item)
            
            # Add to layout
            row = tile_index // cols
            col = tile_index % cols
            self.tiles_layout.addWidget(widget, row, col)
            
            # Store w appropriate dict
            if hasattr(item, 'get_folder_path'):
                self.special_folder_widgets[item.get_folder_path()] = widget
            else:
                self.gallery_tile_widgets[item.get_archive_path()] = widget

def _on_tile_creation_finished(self, success: bool, message: str):
    """Handle completion całego procesu tile creation."""
    self._tile_creation_in_progress = False
    
    if success:
        logging.info(f"Tile creation completed: {message}")
        
        # Finalize layout
        self._finalize_gallery_layout()
        
        # Update UI
        self.tiles_container.setUpdatesEnabled(True)
        self.tiles_container.update()
        
    else:
        logging.error(f"Tile creation failed: {message}")
        # Cleanup partial results if needed

def _setup_widget_connections(self, widget, item):
    """Setup signal connections dla widget."""
    if hasattr(widget, 'archive_open_requested'):
        widget.archive_open_requested.connect(self.main_window.open_archive)
    if hasattr(widget, 'preview_image_requested'):
        widget.preview_image_requested.connect(self.main_window._show_preview_dialog)
    if hasattr(widget, 'tile_selected'):
        widget.tile_selected.connect(self.main_window._handle_tile_selection_changed)
    # ... other connections ...

def _finalize_gallery_layout(self):
    """Finalize gallery layout po tile creation."""
    # Calculate final container height
    all_items = len(self.special_folders_list) + len(self.file_pairs_list)
    geometry = self._get_cached_geometry()
    cols = geometry["cols"]
    
    if all_items > 0:
        rows = math.ceil(all_items / cols)
        total_height = rows * (self.current_thumbnail_size + self.tiles_layout.spacing() + 40)
        
        self.tiles_container.setMinimumHeight(total_height)
        self.tiles_container.adjustSize()
        self.tiles_container.updateGeometry()
```

---

### PATCH 2: OPTIMIZED CACHE SYSTEM Z BETTER LOCK MANAGEMENT

**Problem:** RLock contention w LayoutGeometry przy frequent access
**Rozwiązanie:** Lock-free cache reading z optimistic updates

```python
# Zmodyfikuj klasę LayoutGeometry
import threading
import time
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor

# Cache entry structure
CacheEntry = namedtuple('CacheEntry', ['data', 'timestamp', 'version'])

class OptimizedLayoutGeometry:
    """Lock-free optimized geometry cache z atomic operations."""
    
    def __init__(self, scroll_area, tiles_layout):
        self.scroll_area = scroll_area
        self.tiles_layout = tiles_layout
        
        # Atomic cache z versioning
        self._cache_entries = {}
        self._cache_version = 0
        self._cache_lock = threading.RLock()  # Only dla write operations
        self._cache_ttl = 5.0
        
        # Performance counters
        self._stats = {
            "hits": 0,
            "misses": 0,
            "lock_free_reads": 0,
            "locked_writes": 0
        }
        
        # Background cleanup
        self._cleanup_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="CacheCleanup")
        self._last_cleanup = time.time()
        self._cleanup_interval = 30.0  # 30 seconds
    
    def get_layout_params(self, thumbnail_size: int) -> dict:
        """Lock-free cache read z fallback na locked write."""
        current_time = time.time()
        cache_key = (
            self.scroll_area.width(),
            self.scroll_area.height(), 
            thumbnail_size
        )
        
        # Try lock-free read first
        cache_entry = self._cache_entries.get(cache_key)
        if cache_entry and (current_time - cache_entry.timestamp) < self._cache_ttl:
            self._stats["hits"] += 1
            self._stats["lock_free_reads"] += 1
            return cache_entry.data.copy()
        
        # Cache miss - need locked write
        return self._compute_and_cache_params(cache_key, current_time, thumbnail_size)
    
    def _compute_and_cache_params(self, cache_key: tuple, current_time: float, thumbnail_size: int) -> dict:
        """Compute params z thread-safe caching."""
        with self._cache_lock:
            self._stats["locked_writes"] += 1
            self._stats["misses"] += 1
            
            # Double-check pattern - może ktoś już obliczył
            cache_entry = self._cache_entries.get(cache_key)
            if cache_entry and (current_time - cache_entry.timestamp) < self._cache_ttl:
                return cache_entry.data.copy()
            
            # Calculate new params
            container_width = (
                self.scroll_area.width() - self.scroll_area.verticalScrollBar().width()
            )
            tile_width_spacing = thumbnail_size + self.tiles_layout.spacing() + 10
            tile_height_spacing = thumbnail_size + self.tiles_layout.spacing() + 40
            cols = max(1, math.ceil(container_width / tile_width_spacing))
            
            params = {
                "container_width": container_width,
                "cols": cols,
                "tile_width_spacing": tile_width_spacing,
                "tile_height_spacing": tile_height_spacing,
                "thumbnail_size": thumbnail_size,
                "calculated_at": current_time,
            }
            
            # Atomic cache update
            self._cache_version += 1
            self._cache_entries[cache_key] = CacheEntry(params, current_time, self._cache_version)
            
            # Schedule cleanup if needed
            if current_time - self._last_cleanup > self._cleanup_interval:
                self._schedule_background_cleanup(current_time)
            
            return params.copy()
    
    def _schedule_background_cleanup(self, current_time: float):
        """Schedule background cache cleanup."""
        self._last_cleanup = current_time
        self._cleanup_executor.submit(self._background_cleanup, current_time)
    
    def _background_cleanup(self, cleanup_time: float):
        """Background cleanup expired entries."""
        try:
            with self._cache_lock:
                expired_keys = [
                    key for key, entry in self._cache_entries.items()
                    if cleanup_time - entry.timestamp >= self._cache_ttl
                ]
                
                for key in expired_keys:
                    self._cache_entries.pop(key, None)
                    
                logging.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")
                
        except Exception as e:
            logging.error(f"Cache cleanup error: {e}")

# Replace LayoutGeometry z OptimizedLayoutGeometry w GalleryManager.__init__:
def __init__(self, main_window, tiles_container, tiles_layout, scroll_area):
    # ... existing code ...
    
    # Replace original geometry z optimized version
    self._geometry = OptimizedLayoutGeometry(self.scroll_area, self.tiles_layout)
```

---

### PATCH 3: IMPROVED SCROLL PERFORMANCE Z ADAPTIVE THROTTLING

**Problem:** Fixed 60 FPS scroll throttling może być za wysoka dla słabszych systemów
**Rozwiązanie:** Adaptive throttling based na system performance i scroll speed

```python
# Dodaj adaptive scroll handler
class AdaptiveScrollHandler:
    """Adaptive scroll handling z performance-based throttling."""
    
    def __init__(self, gallery_manager):
        self.gallery_manager = gallery_manager
        
        # Performance monitoring
        self._frame_times = []
        self._max_frame_samples = 10
        self._target_fps = 60
        self._min_fps = 30
        
        # Adaptive throttling
        self._current_throttle_ms = 16  # Start z 60 FPS
        self._scroll_velocity = 0
        self._last_scroll_value = 0
        self._last_scroll_time = 0
        
        # Performance adaptation
        self._performance_level = "high"  # high, medium, low
        self._last_performance_check = 0
        self._performance_check_interval = 5.0  # 5 seconds
    
    def handle_scroll(self, scroll_value: int):
        """Adaptive scroll handling."""
        current_time = time.time()
        
        # Calculate scroll velocity
        if self._last_scroll_time > 0:
            time_delta = current_time - self._last_scroll_time
            value_delta = abs(scroll_value - self._last_scroll_value)
            self._scroll_velocity = value_delta / time_delta if time_delta > 0 else 0
        
        self._last_scroll_value = scroll_value
        self._last_scroll_time = current_time
        
        # Adapt throttling based na velocity i performance
        self._adapt_throttling()
        
        # Check if we should process this scroll event
        current_time_ms = current_time * 1000
        if (current_time_ms - getattr(self, '_last_processed_scroll_ms', 0)) >= self._current_throttle_ms:
            self._last_processed_scroll_ms = current_time_ms
            
            # Process scroll z performance monitoring
            frame_start = time.time()
            self.gallery_manager._process_scroll_optimized(scroll_value)
            frame_time = time.time() - frame_start
            
            # Track frame performance
            self._track_frame_performance(frame_time)
    
    def _adapt_throttling(self):
        """Adapt throttling based na scroll velocity i system performance."""
        # High velocity scrolling = more aggressive throttling
        if self._scroll_velocity > 1000:  # Fast scrolling
            if self._performance_level == "low":
                self._current_throttle_ms = 50  # 20 FPS
            else:
                self._current_throttle_ms = 25  # 40 FPS
        elif self._scroll_velocity > 500:  # Medium scrolling
            if self._performance_level == "low":
                self._current_throttle_ms = 33  # 30 FPS
            else:
                self._current_throttle_ms = 20  # 50 FPS
        else:  # Slow scrolling
            if self._performance_level == "low":
                self._current_throttle_ms = 25  # 40 FPS
            else:
                self._current_throttle_ms = 16  # 60 FPS
    
    def _track_frame_performance(self, frame_time: float):
        """Track frame performance i adapt system performance level."""
        self._frame_times.append(frame_time)
        if len(self._frame_times) > self._max_frame_samples:
            self._frame_times.pop(0)
        
        # Check performance periodically
        current_time = time.time()
        if current_time - self._last_performance_check > self._performance_check_interval:
            self._update_performance_level()
            self._last_performance_check = current_time
    
    def _update_performance_level(self):
        """Update performance level based na recent frame times."""
        if not self._frame_times:
            return
        
        avg_frame_time = sum(self._frame_times) / len(self._frame_times)
        fps_estimate = 1.0 / avg_frame_time if avg_frame_time > 0 else 60
        
        if fps_estimate >= 50:
            self._performance_level = "high"
        elif fps_estimate >= 35:
            self._performance_level = "medium"  
        else:
            self._performance_level = "low"
        
        logging.debug(f"Performance level: {self._performance_level} (Est. FPS: {fps_estimate:.1f})")

# W GalleryManager.__init__ dodaj:
def __init__(self, main_window, tiles_container, tiles_layout, scroll_area):
    # ... existing code ...
    
    # Adaptive scroll handler
    self._scroll_handler = AdaptiveScrollHandler(self)
    
    # Replace existing scroll connection
    if hasattr(self.scroll_area, "verticalScrollBar"):
        # Disconnect old handler
        try:
            self.scroll_area.verticalScrollBar().valueChanged.disconnect(self._on_scroll_throttled)
        except:
            pass
        
        # Connect new adaptive handler
        self.scroll_area.verticalScrollBar().valueChanged.connect(
            self._scroll_handler.handle_scroll
        )

def _process_scroll_optimized(self, scroll_value: int):
    """Optimized scroll processing method."""
    # Only essential operations podczas scroll
    if self._virtualization_enabled:
        self._update_visible_tiles_fast()
    
    # Defer heavy operations
    if self._scroll_timer:
        self._scroll_timer.stop()
        self._scroll_timer.start(100)  # 100ms debounce
```

---

### PATCH 4: PROGRESSIVE FORCE_CREATE_ALL_TILES REPLACEMENT

**Problem:** Monolithic `force_create_all_tiles()` blokuje UI na długi czas
**Rozwiązanie:** Replace z progressive version using new ProgressiveTileCreator

```python
# Replace force_create_all_tiles z progressive version
def create_all_tiles_progressive(self):
    """
    Progressive tile creation - replacement dla force_create_all_tiles().
    Non-blocking z progress feedback.
    """
    if self._tile_creation_in_progress:
        logging.warning("Tile creation already in progress, ignoring request")
        return
    
    self._tile_creation_in_progress = True
    
    # Clear existing tiles
    self.clear_gallery()
    
    # Disable updates during setup
    self.tiles_container.setUpdatesEnabled(False)
    
    # Start progressive creation
    self._progressive_creator.create_tiles_progressive(
        self.special_folders_list,
        self.file_pairs_list
    )

# Update update_gallery_view to use progressive creation dla large datasets
def update_gallery_view(self):
    """
    Aktualizuje widok galerii z intelligent loading strategy.
    """
    total_items = len(self.special_folders_list) + len(self.file_pairs_list)
    
    # Threshold dla progressive loading
    PROGRESSIVE_THRESHOLD = 200
    
    if total_items > PROGRESSIVE_THRESHOLD:
        # Use progressive loading dla large datasets
        self.create_all_tiles_progressive()
    else:
        # Use synchronous creation dla small datasets
        self.force_create_all_tiles()
        
    # Reset virtualization flag
    self._virtualization_enabled = False

# Dodaj method do canceling tile creation
def cancel_tile_creation(self):
    """Cancel ongoing tile creation."""
    if self._tile_creation_in_progress and hasattr(self, '_progressive_creator'):
        self._progressive_creator.cancel_creation()
        self._tile_creation_in_progress = False
        logging.info("Tile creation cancelled by user")
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI RESPONSYWNOŚCI UI:**

- [ ] **Progressive tile creation** - chunks nie blokują UI >200ms
- [ ] **Progress feedback** - użytkownik widzi progress dla długich operacji  
- [ ] **Cancel support** - możliwość anulowania tile creation
- [ ] **Adaptive performance** - automatic adaptation do system capabilities
- [ ] **Cache optimization** - lock-free reads, background cleanup
- [ ] **Scroll smoothness** - adaptive throttling based na performance
- [ ] **Memory efficiency** - progressive loading nie zwiększa memory usage >20%
- [ ] **Error handling** - graceful handling błędów podczas async operations
- [ ] **UI thread safety** - wszystkie UI updates w głównym wątku
- [ ] **Resource cleanup** - proper cleanup worker threads i cache

#### **ZALEŻNOŚCI PERFORMANCE:**

- [ ] **File tile widget compatibility** - tile creation API unchanged
- [ ] **Resource manager integration** - limits respected podczas progressive creation
- [ ] **Main window signals** - widget connections preserved  
- [ ] **Layout geometry** - calculations remain accurate z optimized cache
- [ ] **Scroll event handling** - smooth transition z adaptive throttling
- [ ] **Memory manager integration** - VirtualScrollingMemoryManager compatibility
- [ ] **Timer management** - proper cleanup QTimer instances
- [ ] **Thread lifecycle** - ThreadPoolExecutor proper shutdown

#### **TESTY PERFORMANCE RESPONSYWNOŚCI:**

- [ ] **Large dataset test** - 5000+ tiles creation <10s z progress
- [ ] **UI responsiveness test** - no UI blocking >200ms during any operation
- [ ] **Memory stress test** - stable memory usage durante progressive loading
- [ ] **Scroll performance test** - 60+ FPS scrolling dla 1000+ tiles
- [ ] **Cancel operation test** - clean cancellation bez memory leaks
- [ ] **Cache efficiency test** - >90% hit ratio dla repeated operations
- [ ] **System adaptation test** - proper throttling na słabszych systemach
- [ ] **Concurrent operations test** - multiple gallery operations handling

#### **KRYTERIA SUKCESU RESPONSYWNOŚCI:**

- [ ] **NO UI BLOCKING** - żadna operacja >200ms synchronous UI blocking
- [ ] **PROGRESS VISIBILITY** - wszystkie operacje >1s pokazują progress
- [ ] **SMOOTH SCROLLING** - 60 FPS dla up to 5000 kafli na decent hardware
- [ ] **MEMORY EFFICIENCY** - memory overhead z optimizations <20%
- [ ] **ADAPTIVE PERFORMANCE** - automatic degradation na słabszych systemach