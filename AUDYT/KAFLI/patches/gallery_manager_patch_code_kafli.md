# PATCH-CODE DLA: GALLERY_MANAGER - KRYTYCZNY BUGFIX + VIRTUAL SCROLLING KAFLI

**Powiązany plik z analizą:** `../corrections/gallery_manager_correction_kafli.md`
**Zasady ogólne:** `../../../_BASE_/refactoring_rules.md`

---

### PATCH 1: KRYTYCZNY BUGFIX - AttributeError get_archive_name()

**Problem:** Aplikacja crashuje przez `'FilePair' object has no attribute 'get_archive_name'` w linii 887
**Rozwiązanie:** 🚨 ZASTOSOWANO - zmiana na poprawną metodę `get_base_name()`

```python
# 🚨 BUGFIX ALREADY APPLIED - Line 887 fixed:

# PRZED (powodowało crash):
filename_label = QLabel(f"[{file_pair.get_archive_name()}]", widget)

# PO (naprawione):
filename_label = QLabel(f"[{file_pair.get_base_name()}]", widget)

# ✅ Ten bugfix został już zastosowany i aplikacja powinna działać!
```

---

### PATCH 2: THREAD-SAFE GEOMETRY CACHE

**Problem:** LayoutGeometry._cache nie jest thread-safe podczas concurrent access w virtual scrolling
**Rozwiązanie:** Enhanced thread safety z proper locking i cache invalidation

```python
import threading
import time
from typing import Dict, Tuple, Any

class LayoutGeometry:
    """Thread-safe klasa pomocnicza do obliczeń geometrii layoutu."""

    def __init__(self, scroll_area, tiles_layout):
        self.scroll_area = scroll_area
        self.tiles_layout = tiles_layout
        
        # Thread-safe cache z timestamps
        self._cache: Dict[Tuple, Dict[str, Any]] = {}
        self._cache_lock = threading.RLock()  # Reentrant lock dla nested calls
        self._cache_timestamps: Dict[Tuple, float] = {}
        self._cache_ttl = 5.0  # Cache TTL w sekundach
        
        # Cache statistics dla monitoring
        self._cache_stats = {'hits': 0, 'misses': 0, 'invalidations': 0}

    def get_layout_params(self, thumbnail_size: int) -> Dict[str, Any]:
        """Thread-safe zwracanie parametrów layoutu z intelligent caching."""
        current_time = time.time()
        
        cache_key = (
            self.scroll_area.width(),
            self.scroll_area.height(), 
            thumbnail_size,
        )

        with self._cache_lock:
            # Check cache validity z TTL
            if (cache_key in self._cache and 
                cache_key in self._cache_timestamps and
                current_time - self._cache_timestamps[cache_key] < self._cache_ttl):
                
                self._cache_stats['hits'] += 1
                return self._cache[cache_key].copy()  # Return copy dla thread safety

            # Cache miss or expired - calculate new params
            self._cache_stats['misses'] += 1
            
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
                "thumbnail_size": thumbnail_size,  # Store dla debugging
                "calculated_at": current_time
            }

            # Store w cache z timestamp
            self._cache[cache_key] = params
            self._cache_timestamps[cache_key] = current_time
            
            # Cleanup expired cache entries
            self._cleanup_expired_cache(current_time)
            
            return params.copy()

    def _cleanup_expired_cache(self, current_time: float):
        """Cleanup expired cache entries (called with lock held)."""
        expired_keys = [
            key for key, timestamp in self._cache_timestamps.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        
        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
            self._cache_stats['invalidations'] += 1

    def invalidate_cache(self):
        """Force invalidation całego cache (np. przy resize events)."""
        with self._cache_lock:
            cache_size = len(self._cache)
            self._cache.clear()
            self._cache_timestamps.clear()
            self._cache_stats['invalidations'] += cache_size
            
    def get_cache_stats(self) -> Dict[str, int]:
        """Zwróć cache statistics dla performance monitoring."""
        with self._cache_lock:
            stats = self._cache_stats.copy()
            stats['cache_size'] = len(self._cache)
            return stats

    def get_visible_range(self, thumbnail_size: int, total_items: int) -> Tuple[int, int, Dict[str, Any]]:
        """Thread-safe obliczanie zakresu widocznych elementów z buffering."""
        params = self.get_layout_params(thumbnail_size)

        viewport_height = self.scroll_area.viewport().height()
        scroll_y = self.scroll_area.verticalScrollBar().value()

        # Intelligent buffering based on scroll speed
        base_buffer = viewport_height
        # TODO: Można dodać adaptive buffering based na scroll velocity
        buffer = base_buffer
        
        visible_start_y = max(0, scroll_y - buffer)
        visible_end_y = scroll_y + viewport_height + buffer

        first_visible_row = max(0, math.floor(visible_start_y / params["tile_height_spacing"]))
        last_visible_row = math.ceil(visible_end_y / params["tile_height_spacing"])

        first_visible_item = first_visible_row * params["cols"]
        last_visible_item = min((last_visible_row + 1) * params["cols"], total_items)

        return first_visible_item, last_visible_item, params
```

---

### PATCH 3: THROTTLED SCROLL EVENTS

**Problem:** Zbyt częste update_gallery_view() calls podczas scroll powodują performance issues
**Rozwiązanie:** Debouncing i throttling scroll events dla smooth performance

```python
import threading
from PyQt6.QtCore import QTimer
from typing import Optional

class GalleryManager:
    def __init__(self, main_window, tiles_container, tiles_layout, scroll_area):
        # Existing initialization...
        
        # Throttling scroll events
        self._scroll_timer: Optional[QTimer] = None
        self._last_scroll_update = 0
        self._scroll_throttle_ms = 16  # ~60 FPS for smooth scrolling
        self._scroll_debounce_ms = 100  # Debounce dla heavy operations
        
        # Progressive loading state
        self._progressive_loading = False
        self._loading_chunks_queue = []
        self._loading_lock = threading.RLock()

    def _setup_scroll_throttling(self):
        """Setup throttled scroll event handling."""
        if self.scroll_area and hasattr(self.scroll_area, 'verticalScrollBar'):
            # Throttled scroll updates
            self.scroll_area.verticalScrollBar().valueChanged.connect(
                self._on_scroll_throttled
            )
            
            # Setup timer dla debounced operations
            self._scroll_timer = QTimer()
            self._scroll_timer.setSingleShot(True)
            self._scroll_timer.timeout.connect(self._on_scroll_debounced)

    def _on_scroll_throttled(self, value):
        """Throttled scroll handler - called at max ~60 FPS."""
        import time
        current_time = time.time() * 1000  # ms
        
        if current_time - self._last_scroll_update >= self._scroll_throttle_ms:
            self._last_scroll_update = current_time
            
            # Fast operations only - visibility updates
            self._update_visible_tiles_fast()
            
            # Schedule debounced heavy operations
            if self._scroll_timer:
                self._scroll_timer.stop()
                self._scroll_timer.start(self._scroll_debounce_ms)

    def _on_scroll_debounced(self):
        """Debounced scroll handler - heavy operations."""
        # Heavy operations po zakończeniu scroll
        self._update_geometry_cache_if_needed()
        self._cleanup_hidden_tiles()
        self._trigger_progressive_loading_if_needed()

    def _update_visible_tiles_fast(self):
        """Szybka aktualizacja widoczności kafli bez heavy operations."""
        if not hasattr(self, 'file_pairs_list') or not self.file_pairs_list:
            return
            
        total_items = len(self.file_pairs_list)
        first_visible, last_visible, params = self.layout_geometry.get_visible_range(
            self._current_size_tuple[0], total_items
        )
        
        # Fast visibility updates only
        for i, widget in enumerate(self.gallery_tile_widgets):
            if widget and hasattr(widget, 'setVisible'):
                should_be_visible = first_visible <= i < last_visible
                if widget.isVisible() != should_be_visible:
                    widget.setVisible(should_be_visible)

    def _update_geometry_cache_if_needed(self):
        """Update geometry cache jeśli window size się zmienił."""
        if hasattr(self, 'layout_geometry'):
            # Check czy trzeba invalidate cache
            current_size = (self.scroll_area.width(), self.scroll_area.height())
            if not hasattr(self, '_last_window_size') or self._last_window_size != current_size:
                self.layout_geometry.invalidate_cache()
                self._last_window_size = current_size

    def _cleanup_hidden_tiles(self):
        """Cleanup tiles które są poza visible range."""
        if not self.virtualization_enabled:
            return
            
        # TODO: Implement proper tile cleanup for memory management
        # Ten patch focus na throttling, cleanup w kolejnym patch
        pass

    def _trigger_progressive_loading_if_needed(self):
        """Trigger progressive loading jeśli są pending chunks."""
        with self._loading_lock:
            if self._loading_chunks_queue and not self._progressive_loading:
                self._start_progressive_loading()
```

---

### PATCH 4: PROGRESSIVE LOADING OPTIMIZATION

**Problem:** Wszystkie kafle ładowane jednocześnie zamiast progressive chunks
**Rozwiązanie:** Progressive chunk loading dla smooth UX przy tysiącach kafli

```python
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List

@dataclass
class LoadingChunk:
    chunk_id: str
    file_pairs: List
    start_index: int
    priority: int = 0  # Lower = higher priority

class ProgressiveLoader:
    """Progressive loader dla kafli chunks."""
    
    def __init__(self, gallery_manager, chunk_size: int = 50):
        self.gallery_manager = gallery_manager
        self.chunk_size = chunk_size
        
        # Loading queue i state
        self.loading_queue = queue.PriorityQueue()
        self.is_loading = False
        self.loading_lock = threading.RLock()
        
        # Thread pool dla background loading
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ProgressiveLoader")
        
        # Statistics
        self.stats = {'chunks_loaded': 0, 'tiles_loaded': 0, 'load_time': 0}

    def queue_progressive_loading(self, file_pairs: List, visible_range: Tuple[int, int] = None):
        """Queue file_pairs dla progressive loading z priority based na visibility."""
        if not file_pairs:
            return
            
        # Split w chunks
        chunks = []
        for i in range(0, len(file_pairs), self.chunk_size):
            chunk_end = min(i + self.chunk_size, len(file_pairs))
            chunk = file_pairs[i:chunk_end]
            
            # Calculate priority - visible chunks mają wyższy priorytet
            priority = 0
            if visible_range:
                visible_start, visible_end = visible_range
                if i < visible_end and chunk_end > visible_start:
                    priority = -1  # Negative = higher priority
                    
            loading_chunk = LoadingChunk(
                chunk_id=f"chunk_{i}_{chunk_end}",
                file_pairs=chunk,
                start_index=i,
                priority=priority
            )
            chunks.append(loading_chunk)
        
        # Add chunks do queue
        with self.loading_lock:
            for chunk in chunks:
                self.loading_queue.put((chunk.priority, chunk))
                
        # Start loading jeśli nie jest już active
        if not self.is_loading:
            self._start_loading()

    def _start_loading(self):
        """Start progressive loading w background."""
        with self.loading_lock:
            if self.is_loading:
                return
            self.is_loading = True
            
        # Submit loading task do thread pool
        self.executor.submit(self._loading_worker)

    def _loading_worker(self):
        """Background worker dla progressive loading."""
        import time
        
        try:
            while True:
                try:
                    # Get next chunk z timeout
                    priority, chunk = self.loading_queue.get(timeout=1.0)
                    
                    start_time = time.time()
                    
                    # Load chunk on main thread (UI operations)
                    from PyQt6.QtCore import QMetaObject, Qt
                    QMetaObject.invokeMethod(
                        self.gallery_manager,
                        "_load_chunk_on_main_thread",
                        Qt.ConnectionType.QueuedConnection,
                        chunk
                    )
                    
                    # Update statistics
                    load_time = time.time() - start_time
                    self.stats['chunks_loaded'] += 1
                    self.stats['tiles_loaded'] += len(chunk.file_pairs)
                    self.stats['load_time'] += load_time
                    
                    # Mark task as done
                    self.loading_queue.task_done()
                    
                    # Small delay dla UI responsiveness
                    time.sleep(0.01)
                    
                except queue.Empty:
                    # No more chunks - stop loading
                    break
                    
        finally:
            with self.loading_lock:
                self.is_loading = False

class GalleryManager:
    def __init__(self, main_window, tiles_container, tiles_layout, scroll_area):
        # Existing initialization...
        
        # Progressive loading
        self.progressive_loader = ProgressiveLoader(self, chunk_size=50)
        
    def update_gallery_view(self, file_pairs_list: List = None):
        """Enhanced update z progressive loading support."""
        if file_pairs_list is not None:
            self.file_pairs_list = file_pairs_list

        total_items = len(self.file_pairs_list) if self.file_pairs_list else 0
        
        if total_items == 0:
            self._clear_gallery()
            return

        # Determine czy użyć virtualization czy progressive loading
        if total_items > self.VIRTUALIZATION_THRESHOLD:
            self._update_with_virtualization(total_items)
        else:
            self._update_with_progressive_loading()

    def _update_with_progressive_loading(self):
        """Update galerii z progressive loading dla smooth UX."""
        if not self.file_pairs_list:
            return
            
        # Calculate visible range dla prioritization
        total_items = len(self.file_pairs_list)
        visible_range = self.layout_geometry.get_visible_range(
            self._current_size_tuple[0], total_items
        )
        
        # Queue dla progressive loading
        self.progressive_loader.queue_progressive_loading(
            self.file_pairs_list, 
            visible_range[:2]  # (start, end)
        )

    def _load_chunk_on_main_thread(self, chunk: LoadingChunk):
        """Load chunk na main thread (Qt slot)."""
        try:
            # Create tiles dla chunk
            created_tiles = []
            for i, file_pair in enumerate(chunk.file_pairs):
                tile_index = chunk.start_index + i
                tile = self._create_tile_for_index(file_pair, tile_index)
                if tile:
                    created_tiles.append(tile)
                    
                # Yield control co 5 tiles dla responsiveness
                if i % 5 == 0:
                    QApplication.processEvents()
                    
            logger.debug(f"Progressive loaded chunk {chunk.chunk_id}: {len(created_tiles)} tiles")
            
        except Exception as e:
            logger.error(f"Error loading chunk {chunk.chunk_id}: {e}")

    def _create_tile_for_index(self, file_pair, index: int):
        """Create pojedynczy tile w określonym index."""
        # Delegate do tile manager lub create directly
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'tile_manager'):
            tile = self.main_window.tile_manager.create_tile_widget_for_pair(file_pair)
        else:
            tile = self.create_tile_widget_for_pair(file_pair, self.main_window)
            
        if tile:
            # Add do layout
            params = self.layout_geometry.get_layout_params(self._current_size_tuple[0])
            row = index // params['cols']
            col = index % params['cols']
            
            self.tiles_layout.addWidget(tile, row, col)
            tile.setVisible(True)
            
            # Add do tracking
            if hasattr(self, 'gallery_tile_widgets'):
                # Ensure list is large enough
                while len(self.gallery_tile_widgets) <= index:
                    self.gallery_tile_widgets.append(None)
                self.gallery_tile_widgets[index] = tile
                
        return tile
```

---

### PATCH 5: MEMORY MANAGEMENT VIRTUAL SCROLLING

**Problem:** Memory leaks podczas virtual scrolling - brak proper cleanup widgetów
**Rozwiązanie:** Intelligent memory management z widget disposal i resource tracking

```python
import weakref
from typing import Set, Dict

class VirtualScrollingMemoryManager:
    """Memory management dla virtual scrolling kafli."""
    
    def __init__(self, gallery_manager):
        self.gallery_manager = gallery_manager
        
        # Widget tracking
        self.active_widgets: Dict[int, weakref.ref] = {}  # index -> widget weakref
        self.disposed_widgets: Set[int] = set()
        
        # Memory thresholds
        self.max_active_widgets = 200  # Max widgets in memory
        self.cleanup_threshold = 150   # Start cleanup when reached
        
        # Statistics
        self.stats = {
            'widgets_created': 0,
            'widgets_disposed': 0,
            'memory_cleanups': 0
        }

    def register_widget(self, index: int, widget):
        """Register widget dla tracking."""
        if widget:
            self.active_widgets[index] = weakref.ref(
                widget, 
                lambda ref: self._on_widget_destroyed(index)
            )
            self.stats['widgets_created'] += 1
            
            # Check memory pressure
            if len(self.active_widgets) > self.cleanup_threshold:
                self._trigger_memory_cleanup()

    def _on_widget_destroyed(self, index: int):
        """Callback gdy widget został zniszczony."""
        self.active_widgets.pop(index, None)
        self.disposed_widgets.add(index)

    def _trigger_memory_cleanup(self):
        """Trigger memory cleanup when threshold reached."""
        if not self.gallery_manager.virtualization_enabled:
            return
            
        # Get visible range
        if hasattr(self.gallery_manager, 'file_pairs_list') and self.gallery_manager.file_pairs_list:
            total_items = len(self.gallery_manager.file_pairs_list)
            visible_start, visible_end, _ = self.gallery_manager.layout_geometry.get_visible_range(
                self.gallery_manager._current_size_tuple[0], total_items
            )
            
            # Dispose widgets outside visible range
            disposed_count = 0
            for index in list(self.active_widgets.keys()):
                if index < visible_start or index >= visible_end:
                    if self._dispose_widget_at_index(index):
                        disposed_count += 1
                        
            self.stats['memory_cleanups'] += 1
            self.stats['widgets_disposed'] += disposed_count
            
            logger.debug(f"Memory cleanup: disposed {disposed_count} widgets, active: {len(self.active_widgets)}")

    def _dispose_widget_at_index(self, index: int) -> bool:
        """Dispose widget at specific index."""
        widget_ref = self.active_widgets.get(index)
        if widget_ref:
            widget = widget_ref()
            if widget:
                # Remove z layout
                if hasattr(self.gallery_manager, 'tiles_layout'):
                    self.gallery_manager.tiles_layout.removeWidget(widget)
                
                # Cleanup widget
                if hasattr(widget, 'cleanup'):
                    widget.cleanup()
                elif hasattr(widget, 'deleteLater'):
                    widget.deleteLater()
                    
                # Remove z tracking
                self.active_widgets.pop(index, None)
                self.disposed_widgets.add(index)
                return True
        return False

    def get_memory_stats(self) -> Dict[str, int]:
        """Get memory management statistics."""
        stats = self.stats.copy()
        stats['active_widgets'] = len(self.active_widgets)
        stats['disposed_count'] = len(self.disposed_widgets)
        return stats

class GalleryManager:
    def __init__(self, main_window, tiles_container, tiles_layout, scroll_area):
        # Existing initialization...
        
        # Memory management
        self.memory_manager = VirtualScrollingMemoryManager(self)
        
    def create_tile_widget_for_pair(self, file_pair, parent=None, index: int = None):
        """Enhanced tile creation z memory management."""
        # Create tile
        tile = FileTileWidget(file_pair, self._current_size_tuple, parent)
        
        # Register w memory manager
        if index is not None:
            self.memory_manager.register_widget(index, tile)
            
        return tile

    def _cleanup_hidden_tiles(self):
        """Cleanup tiles które są poza visible range (called by throttled scroll)."""
        if not self.virtualization_enabled:
            return
            
        # Delegate do memory manager
        self.memory_manager._trigger_memory_cleanup()

    def force_memory_cleanup(self):
        """Force memory cleanup - dla debug purposes."""
        if hasattr(self, 'memory_manager'):
            self.memory_manager._trigger_memory_cleanup()
            
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        stats = {}
        
        if hasattr(self, 'memory_manager'):
            stats['memory_manager'] = self.memory_manager.get_memory_stats()
            
        if hasattr(self, 'layout_geometry'):
            stats['geometry_cache'] = self.layout_geometry.get_cache_stats()
            
        if hasattr(self, 'progressive_loader'):
            stats['progressive_loader'] = self.progressive_loader.stats.copy()
            
        # Add widget counts
        stats['total_widgets'] = len(getattr(self, 'gallery_tile_widgets', []))
        stats['active_widgets'] = len([w for w in getattr(self, 'gallery_tile_widgets', []) if w])
        
        return stats
```

---

## ✅ CHECKLISTA WERYFIKACYJNA KAFLI (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI VIRTUAL SCROLLING KAFLI DO WERYFIKACJI:**

- [x] **KRYTYCZNY BUGFIX** - czy aplikacja nie crashuje przez get_archive_name() error
- [ ] **Thread-safe geometry cache** - czy concurrent access nie powoduje race conditions
- [ ] **Throttled scroll events** - czy scroll jest płynny przy ~60 FPS
- [ ] **Progressive loading** - czy kafle ładują się chunks zamiast bulk
- [ ] **Memory management** - czy widgets są disposed poza visible range
- [ ] **Visible range calculation** - czy buffering działa poprawnie
- [ ] **Cache invalidation** - czy geometry cache invaliduje się przy resize
- [ ] **Virtual scrolling state** - czy virtualization flags są consistent
- [ ] **Performance monitoring** - czy statistics są tracked poprawnie
- [ ] **Smooth UX** - czy tysiące kafli scroll płynnie bez stuttering

#### **ZALEŻNOŚCI VIRTUAL SCROLLING DO WERYFIKACJI:**

- [ ] **TileManager integration** - czy batch creation współpracuje z virtual scrolling
- [ ] **FileTileWidget compatibility** - czy tiles działają w virtual environment
- [ ] **SpecialFolderTileWidget support** - czy special folders działają w virtual scrolling
- [ ] **Memory pressure coordination** - czy różne managery koordynują memory usage
- [ ] **Thread safety across managers** - czy concurrent operations są safe
- [ ] **Event bus coordination** - czy events działają w virtual environment
- [ ] **Resource manager integration** - czy tile limits są respected
- [ ] **Progress tracking** - czy progress działa z progressive loading
- [ ] **UI responsiveness** - czy main thread nie jest blocked przez operations

#### **TESTY WYDAJNOŚCIOWE VIRTUAL SCROLLING KAFLI:**

- [ ] **Scroll performance** - target <16ms per frame dla smooth 60 FPS
- [ ] **Memory efficiency** - target <500MB podczas scroll tysięcy kafli
- [ ] **Progressive loading speed** - chunks loaded w <100ms per chunk
- [ ] **Cache hit rates** - geometry cache >90% hit rate
- [ ] **Widget disposal efficiency** - memory cleaned w <50ms
- [ ] **Thread safety stress** - concurrent scroll operations bez crashes
- [ ] **Large dataset handling** - 5000+ kafli bez degradacji
- [ ] **Memory leak prevention** - długotrwałe scrolling bez memory growth
- [ ] **Startup performance** - initial load <2s dla 1000 kafli

#### **KRYTERIA SUKCESU VIRTUAL SCROLLING KAFLI:**

- [x] **APLIKACJA DZIAŁA** - brak crashes przez API errors
- [ ] **SMOOTH SCROLLING** - 60 FPS przez tysiące kafli consistently
- [ ] **MEMORY EFFICIENT** - <500MB sustained podczas virtual scrolling
- [ ] **RESPONSIVE UI** - main thread nie blocked podczas operations