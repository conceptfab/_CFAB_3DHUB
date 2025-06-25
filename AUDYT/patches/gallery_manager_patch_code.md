# PATCH-CODE DLA: GALLERY_MANAGER.PY

**Powiązany plik z analizą:** `../corrections/gallery_manager_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: OPTYMALIZACJA FORCE_CREATE_ALL_TILES

**Problem:** Synchroniczne tworzenie tysięcy kafli blokuje UI bez yielding
**Rozwiązanie:** Częstsze yielding i progress indication

```python
# PRZED (line 1337-1344):
# Twórz kafelki w batchach - większe batche dla szybkości
batch_size = 100  # Zwiększono z 20 na 100 dla szybkości SBSAR
total_batches = (len(all_items) + batch_size - 1) // batch_size

# Rzadsze processEvents - tylko co 5 batchów zamiast każdy
if (batch_num + 1) % 5 == 0:  # Co 5 batchów zamiast każdy

# PO:
# ULEPSZONY: Optymalne batche z częstszym yielding
batch_size = 50  # ZMNIEJSZONO z 100 do 50 dla lepszej responsywności
total_batches = (len(all_items) + batch_size - 1) // batch_size

# ULEPSZONY: Częstsze processEvents dla smooth UI
if (batch_num + 1) % 2 == 0:  # ZMIENIONO z 5 do 2 - co 2 batche

# NOWY: Progress indication dla długich operacji
if len(all_items) > 500:  # Show progress for large datasets
    progress_percent = (batch_num + 1) * 100 // total_batches
    if hasattr(self.main_window, 'progress_manager'):
        self.main_window.progress_manager.show_progress(
            progress_percent, f"Tworzenie kafli: {batch_num + 1}/{total_batches}"
        )

# NOWY: Adaptive yielding based on performance
batch_start_time = time.time()
# ... existing tile creation code ...
batch_duration = time.time() - batch_start_time

# If batch takes too long, yield more frequently next time
if batch_duration > 0.1:  # >100ms batch duration
    if batch_size > 25:
        batch_size = max(25, batch_size - 10)  # Reduce batch size
    
    # Force immediate UI update for long batches
    from PyQt6.QtWidgets import QApplication
    QApplication.processEvents()
    time.sleep(0.005)  # 5ms pause to let UI catch up
```

---

### PATCH 2: ULEPSZENIE PROGRESSIVE TILE CREATOR

**Problem:** Static chunk sizing nie uwzględnia actual performance characteristics
**Rozwiązanie:** Dynamic adaptive chunking z performance monitoring

```python
# PRZED (line 56-83):
def _configure_adaptive_settings(self):
    try:
        if psutil:
            cpu_count = psutil.cpu_count(logical=True)
            memory_gb = psutil.virtual_memory().total / (1024**3)

            if memory_gb >= 16 and cpu_count >= 8:
                self.chunk_size = 150  # ← PROBLEM: Static values
                self.process_events_interval = 3
            elif memory_gb >= 8 and cpu_count >= 4:
                self.chunk_size = 100
                self.process_events_interval = 2
            else:
                self.chunk_size = 50
                self.process_events_interval = 1

# PO:
def _configure_adaptive_settings(self):
    """Enhanced adaptive configuration with performance monitoring."""
    # NOWY: Performance tracking for dynamic adjustment
    self._performance_history = []
    self._max_performance_samples = 5
    self._target_chunk_time = 0.05  # Target: 50ms per chunk
    
    try:
        if psutil:
            cpu_count = psutil.cpu_count(logical=True)
            memory_gb = psutil.virtual_memory().total / (1024**3)

            # ULEPSZONY: More conservative initial sizing
            if memory_gb >= 16 and cpu_count >= 8:
                self.chunk_size = 100  # ZMNIEJSZONO z 150 do 100
                self.process_events_interval = 2  # ZMNIEJSZONO z 3 do 2
            elif memory_gb >= 8 and cpu_count >= 4:
                self.chunk_size = 75   # ZMNIEJSZONO z 100 do 75
                self.process_events_interval = 2
            else:
                self.chunk_size = 40   # ZMNIEJSZONO z 50 do 40
                self.process_events_interval = 1
                
            # NOWY: Memory pressure adjustment
            try:
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 80:  # High memory usage
                    self.chunk_size = int(self.chunk_size * 0.7)  # 30% reduction
                    self.process_events_interval = max(1, self.process_events_interval - 1)
            except:
                pass
                
        else:
            # ULEPSZONY: More conservative fallback
            self.chunk_size = 50  # ZMNIEJSZONO z 75 do 50
            self.process_events_interval = 2

    except Exception:
        # ULEPSZONY: Safe fallback values
        self.chunk_size = 40
        self.process_events_interval = 1

def _create_chunk_widgets(self, chunk_items: list, start_index: int) -> list:
    """Enhanced chunk widget creation with adaptive performance tuning."""
    widgets = []
    chunk_start_time = time.time()
    
    for i, item in enumerate(chunk_items):
        # ... existing widget creation code ...
        
        # NOWY: Track per-widget performance
        widget_start_time = time.time()
        # ... widget creation ...
        widget_creation_time = time.time() - widget_start_time
        
        if widget_creation_time > 0.02:  # >20ms per widget is slow
            logging.debug(f"Slow widget creation: {widget_creation_time:.3f}s for item {i}")

    # NOWY: Adaptive chunk size adjustment
    chunk_duration = time.time() - chunk_start_time
    self._performance_history.append(chunk_duration)
    
    if len(self._performance_history) > self._max_performance_samples:
        self._performance_history.pop(0)
    
    # Adjust chunk size based on recent performance
    if len(self._performance_history) >= 3:
        avg_chunk_time = sum(self._performance_history) / len(self._performance_history)
        
        if avg_chunk_time > self._target_chunk_time * 1.5:  # Too slow
            self.chunk_size = max(20, int(self.chunk_size * 0.8))  # Reduce by 20%
            logging.debug(f"Reducing chunk size to {self.chunk_size} (avg time: {avg_chunk_time:.3f}s)")
        elif avg_chunk_time < self._target_chunk_time * 0.5:  # Can increase
            self.chunk_size = min(200, int(self.chunk_size * 1.1))  # Increase by 10%
            logging.debug(f"Increasing chunk size to {self.chunk_size} (avg time: {avg_chunk_time:.3f}s)")

    return widgets
```

---

### PATCH 3: SIMPLIFIKACJA CACHE STRATEGY

**Problem:** Duplikacja między OptimizedLayoutGeometry i LayoutGeometry
**Rozwiązanie:** Konsolidacja do unified optimized caching

```python
# PRZED: Dwie osobne klasy cache (lines 301-544)
class OptimizedLayoutGeometry:
    # Complex caching implementation...

class LayoutGeometry:
    # Similar caching implementation...

# PO: Unified optimized cache strategy
class UnifiedLayoutGeometry:
    """Unified layout geometry cache with optimal performance."""
    
    def __init__(self, scroll_area, tiles_layout):
        self.scroll_area = scroll_area
        self.tiles_layout = tiles_layout
        
        # SIMPLIFIED: Single cache strategy
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_lock = threading.RLock()
        self._cache_ttl = 5.0
        
        # OPTIMIZED: Performance tracking
        self._stats = {"hits": 0, "misses": 0, "computations": 0}
        self._last_cleanup = time.time()
        self._cleanup_interval = 30.0

    def get_layout_params(self, thumbnail_size: int) -> dict:
        """Optimized layout parameters calculation with smart caching."""
        current_time = time.time()
        cache_key = (
            self.scroll_area.width(),
            self.scroll_area.height(), 
            thumbnail_size,
        )

        # OPTIMIZED: Fast cache lookup without locking unless necessary
        cache_entry = self._cache.get(cache_key)
        cache_timestamp = self._cache_timestamps.get(cache_key, 0)
        
        if cache_entry and (current_time - cache_timestamp) < self._cache_ttl:
            self._stats["hits"] += 1
            return cache_entry.copy()

        # SIMPLIFIED: Cache miss - compute new params
        with self._cache_lock:
            # Double-check pattern
            cache_entry = self._cache.get(cache_key)
            cache_timestamp = self._cache_timestamps.get(cache_key, 0)
            
            if cache_entry and (current_time - cache_timestamp) < self._cache_ttl:
                self._stats["hits"] += 1
                return cache_entry.copy()

            self._stats["misses"] += 1
            self._stats["computations"] += 1

            # OPTIMIZED: Efficient parameter calculation
            container_width = (
                self.scroll_area.width() - 
                self.scroll_area.verticalScrollBar().width()
            )
            
            # SIMPLIFIED: Clear calculation without over-optimization
            tile_spacing = self.tiles_layout.spacing()
            tile_total_width = thumbnail_size + tile_spacing + 10
            tile_total_height = thumbnail_size + tile_spacing + 40
            cols = max(1, container_width // tile_total_width)

            params = {
                "container_width": container_width,
                "cols": cols,
                "tile_width_spacing": tile_total_width,
                "tile_height_spacing": tile_total_height,
                "thumbnail_size": thumbnail_size,
                "calculated_at": current_time,
            }

            # ATOMIC: Cache update
            self._cache[cache_key] = params
            self._cache_timestamps[cache_key] = current_time

            # MAINTENANCE: Periodic cleanup
            if current_time - self._last_cleanup > self._cleanup_interval:
                self._cleanup_expired_entries(current_time)

            return params.copy()

    def _cleanup_expired_entries(self, current_time: float):
        """Efficient cache cleanup."""
        self._last_cleanup = current_time
        
        expired_keys = [
            key for key, timestamp in self._cache_timestamps.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        
        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
            
        if expired_keys:
            logging.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")

# UPDATE: Use unified cache in GalleryManager
def __init__(self, ...):
    # ... existing code ...
    
    # SIMPLIFIED: Single unified cache strategy
    self._geometry = UnifiedLayoutGeometry(self.scroll_area, self.tiles_layout)
    # Remove duplicate LayoutGeometry initialization
```

---

### PATCH 4: OPTYMALIZACJA CLEAR_GALLERY

**Problem:** Sequential deletion może być bardzo wolna przy tysiącach kafli
**Rozwiązanie:** Batch deletion z progress indication

```python
# PRZED (line 924-962):
def clear_gallery(self):
    self.tiles_container.setUpdatesEnabled(False)
    try:
        # Usuń wszystkie widgety z layoutu
        while self.tiles_layout.count():
            item = self.tiles_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setVisible(False)
                self.tiles_layout.removeWidget(widget)

        # Thread-safe czyszczenie słowników
        with self._widgets_lock:
            # Sequential deletion of all widgets
            for archive_path in list(self.gallery_tile_widgets.keys()):
                tile = self.gallery_tile_widgets.pop(archive_path)
                tile.setParent(None)
                tile.deleteLater()

# PO:
def clear_gallery(self):
    """Enhanced gallery clearing with batch processing and progress indication."""
    total_widgets = self.tiles_layout.count() + len(self.gallery_tile_widgets) + len(self.special_folder_widgets)
    
    # Show progress for large galleries
    show_progress = total_widgets > 200
    if show_progress and hasattr(self.main_window, 'progress_manager'):
        self.main_window.progress_manager.show_progress(0, "Czyszczenie galerii...")

    self.tiles_container.setUpdatesEnabled(False)
    try:
        processed_widgets = 0
        
        # OPTIMIZED: Batch layout clearing
        layout_items = []
        while self.tiles_layout.count():
            layout_items.append(self.tiles_layout.takeAt(0))
            
        # Process layout items in batches
        batch_size = 50
        for i in range(0, len(layout_items), batch_size):
            batch = layout_items[i:i + batch_size]
            for item in batch:
                widget = item.widget()
                if widget:
                    widget.setVisible(False)
                    # Don't call removeWidget since we already took items
                    
            processed_widgets += len(batch)
            
            # NOWY: Progress update and UI yielding
            if show_progress and processed_widgets % 100 == 0:
                progress_percent = min(50, (processed_widgets * 50) // total_widgets)
                self.main_window.progress_manager.show_progress(
                    progress_percent, f"Czyszczenie layoutu: {processed_widgets}/{total_widgets}"
                )
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()

        # OPTIMIZED: Batch widget deletion
        with self._widgets_lock:
            # Collect all widgets for batch processing
            all_tile_widgets = list(self.gallery_tile_widgets.values())
            all_folder_widgets = list(self.special_folder_widgets.values())
            
            # Clear dictionaries first for immediate effect
            self.gallery_tile_widgets.clear()
            self.special_folder_widgets.clear()
            
            # OPTIMIZED: Batch deletion of tile widgets
            for i in range(0, len(all_tile_widgets), batch_size):
                batch = all_tile_widgets[i:i + batch_size]
                for tile in batch:
                    try:
                        tile.setParent(None)
                        tile.deleteLater()
                    except RuntimeError:
                        # Widget already deleted
                        pass
                        
                processed_widgets += len(batch)
                
                # Progress update
                if show_progress and i % (batch_size * 2) == 0:  # Every 2 batches
                    progress_percent = 50 + min(40, (processed_widgets * 40) // total_widgets)
                    self.main_window.progress_manager.show_progress(
                        progress_percent, f"Usuwanie kafli: {processed_widgets}/{total_widgets}"
                    )
                    from PyQt6.QtWidgets import QApplication
                    QApplication.processEvents()
                    
                    # NOWY: Memory cleanup during deletion
                    if i % (batch_size * 5) == 0:  # Every 5 batches
                        import gc
                        gc.collect()

            # OPTIMIZED: Batch deletion of folder widgets  
            for i in range(0, len(all_folder_widgets), batch_size):
                batch = all_folder_widgets[i:i + batch_size]
                for folder_widget in batch:
                    try:
                        folder_widget.setParent(None)
                        folder_widget.deleteLater()
                    except RuntimeError:
                        pass
                        
                processed_widgets += len(batch)

    finally:
        self.tiles_container.setUpdatesEnabled(True)
        self.tiles_container.update()
        
        # NOWY: Final cleanup and progress completion
        if show_progress:
            self.main_window.progress_manager.show_progress(100, "Galeria wyczyszczona")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1000, self.main_window.progress_manager.hide_progress)
        
        # NOWY: Force garbage collection after major cleanup
        import gc
        gc.collect()
        
        logging.info(f"Gallery cleared: {total_widgets} widgets processed")
```

---

## ✅ CHECKLISTA WERYFIKACYJNA

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **force_create_all_tiles responsiveness** - yielding co 25 tiles, progress indication
- [ ] **Progressive tile creation** - adaptive chunk sizing based na performance
- [ ] **Gallery clearing** - batch deletion z progress dla >200 widgets
- [ ] **Cache efficiency** - unified geometry caching bez duplikacji
- [ ] **Memory management** - stable usage podczas tile operations
- [ ] **UI responsiveness** - no blocking >50ms during operations
- [ ] **Progress indication** - user feedback dla long operations
- [ ] **Error handling** - graceful handling podczas widget creation/deletion

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **TileManager integration** - coordinated tile creation
- [ ] **WorkerManager cooperation** - memory pressure awareness  
- [ ] **FileTileWidget compatibility** - proper widget lifecycle management
- [ ] **GalleryController coordination** - state management consistency
- [ ] **Resource manager integration** - proper resource allocation/cleanup

#### **TESTY WERYFIKACYJNE:**

- [ ] **Large dataset test** - 2000+ tiles creation performance
- [ ] **Memory stability test** - no leaks podczas multiple clear/create cycles
- [ ] **UI responsiveness test** - max 50ms blocking during any operation
- [ ] **Progress indication test** - accurate feedback dla long operations

#### **KRYTERIA SUKCESU:**

- [ ] **UI RESPONSIVE** - no blocking >50ms podczas tile operations
- [ ] **MEMORY STABLE** - predictable usage regardless of dataset size
- [ ] **PROGRESS INDICATION** - clear feedback dla operations >2s
- [ ] **PERFORMANCE OPTIMIZED** - adaptive sizing based na system capabilities