# PATCH-CODE DLA: TILE_MANAGER.PY

**Powiązany plik z analizą:** `../corrections/tile_manager_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: ADAPTACYJNY BATCH PROCESSING Z MONITORING PAMIĘCI

**Problem:** Sztywny batch size 50, brak adaptacji do rozmiaru folderu i pamięci
**Rozwiązanie:** Dynamiczny batch size z monitoring pamięci i CPU

```python
# W __init__ około linii 55-57
# Kod do zmiany:
# self._batch_size = 50
# self._memory_threshold_mb = 500

# Zmienić na:
import psutil
import time
from typing import Dict, Any

# Adaptive batch processing properties
self._base_batch_size = 50
self._max_batch_size = 200
self._min_batch_size = 10
self._memory_threshold_mb = 800  # Zwiększony próg
self._cpu_threshold_percent = 80

# Performance monitoring
self._performance_stats = {
    "avg_tile_creation_time": 0.0,
    "avg_memory_usage": 0.0,
    "total_tiles_created": 0,
    "last_batch_time": 0.0
}

def get_adaptive_batch_size(self, total_items: int, current_memory_mb: float) -> int:
    """Oblicza optymalny batch size na podstawie pamięci, CPU i historii."""
    try:
        # Base calculation
        base_size = min(self._base_batch_size, max(self._min_batch_size, total_items // 10))
        
        # Memory adjustment
        if current_memory_mb > self._memory_threshold_mb:
            memory_factor = 0.5  # Reduce batch size
        elif current_memory_mb < self._memory_threshold_mb * 0.6:
            memory_factor = 1.5  # Increase batch size
        else:
            memory_factor = 1.0
            
        # CPU adjustment
        cpu_usage = psutil.cpu_percent(interval=0.1)
        if cpu_usage > self._cpu_threshold_percent:
            cpu_factor = 0.7
        else:
            cpu_factor = 1.0
            
        # Performance history adjustment
        if self._performance_stats["avg_tile_creation_time"] > 0.1:  # 100ms per tile
            perf_factor = 0.8
        else:
            perf_factor = 1.2
            
        # Calculate final batch size
        adaptive_size = int(base_size * memory_factor * cpu_factor * perf_factor)
        return max(self._min_batch_size, min(self._max_batch_size, adaptive_size))
        
    except Exception as e:
        self.logger.warning(f"Error calculating adaptive batch size: {e}")
        return self._base_batch_size
```

---

### PATCH 2: THREAD-SAFE OPERACJE Z ATOMIC COUNTERS

**Problem:** Race conditions w _is_creating_tiles, brak atomic operations
**Rozwiązanie:** Thread-safe counters i proper locking

```python
# W __init__ około linii 49-53
# Kod do zmiany:
# self._is_creating_tiles = False
# self._creation_lock = threading.RLock()

# Zmienić na:
import threading
import queue
from threading import Event, Condition

# Thread-safe state management
self._is_creating_tiles = threading.Event()
self._creation_lock = threading.RLock()
self._tile_creation_condition = threading.Condition(self._creation_lock)

# Atomic counters for statistics
self._tiles_created_counter = 0
self._tiles_failed_counter = 0
self._counter_lock = threading.RLock()

# Thread-safe queue for batch processing
self._batch_queue = queue.Queue()
self._worker_threads = []
self._max_worker_threads = 2  # Limit concurrent threads

def increment_tile_counter(self, success: bool = True):
    """Thread-safe increment of tile creation counters."""
    with self._counter_lock:
        if success:
            self._tiles_created_counter += 1
        else:
            self._tiles_failed_counter += 1

def get_tile_stats(self) -> Dict[str, int]:
    """Thread-safe access to tile creation statistics."""
    with self._counter_lock:
        return {
            "created": self._tiles_created_counter,
            "failed": self._tiles_failed_counter,
            "total": self._tiles_created_counter + self._tiles_failed_counter
        }

# W start_tile_creation około linii 116-127
# Kod do zmiany:
# with self._creation_lock:
#     if self._is_creating_tiles:
#         self.logger.warning("Próba rozpoczęcia tworzenia kafelków, gdy proces już trwa.")
#         return
#     self._is_creating_tiles = True

# Zmienić na:
with self._creation_lock:
    if self._is_creating_tiles.is_set():
        self.logger.warning("Próba rozpoczęcia tworzenia kafelków, gdy proces już trwa.")
        return
    
    # Reset counters
    with self._counter_lock:
        self._tiles_created_counter = 0
        self._tiles_failed_counter = 0
    
    self._is_creating_tiles.set()
```

---

### PATCH 3: ASYNCHRONICZNE PRZETWARZANIE Z PROGRESS THROTTLING

**Problem:** Synchroniczne przetwarzanie blokuje UI, brak throttling progress updates
**Rozwiązanie:** Asynchroniczne batch processing z throttled progress

```python
# Dodać nową metodę po create_tile_widgets_batch
def create_tile_widgets_batch_async(self, file_pairs_batch: list):
    """Asynchroniczne tworzenie kafli z throttled progress updates."""
    import time
    from PyQt6.QtCore import QTimer
    
    batch_start_time = time.time()
    batch_size = len(file_pairs_batch)
    
    # Adaptive batch size based on current conditions
    try:
        memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        optimal_batch_size = self.get_adaptive_batch_size(batch_size, memory_mb)
        
        # Split into smaller chunks if necessary
        if batch_size > optimal_batch_size:
            chunks = [file_pairs_batch[i:i + optimal_batch_size] 
                     for i in range(0, batch_size, optimal_batch_size)]
        else:
            chunks = [file_pairs_batch]
            
        self._process_chunks_async(chunks, batch_start_time)
        
    except Exception as e:
        self.logger.error(f"Error in async batch processing: {e}")
        # Fallback to synchronous processing
        self.create_tile_widgets_batch(file_pairs_batch)

def _process_chunks_async(self, chunks: list, start_time: float):
    """Przetwarza chunks asynchronicznie z opóźnieniami."""
    if not chunks:
        self._finish_async_processing(start_time)
        return
        
    chunk = chunks.pop(0)
    self._process_single_chunk(chunk)
    
    # Schedule next chunk with small delay for UI responsiveness
    if chunks:
        QTimer.singleShot(10, lambda: self._process_chunks_async(chunks, start_time))
    else:
        self._finish_async_processing(start_time)

def _process_single_chunk(self, chunk: list):
    """Przetwarza pojedynczy chunk z proper error handling."""
    created_count = 0
    
    try:
        gallery_manager = self.main_window.gallery_manager
        geometry = gallery_manager._get_cached_geometry()
        cols = geometry["cols"]
        current_tile_count = len(gallery_manager.gallery_tile_widgets)
        
        for idx, file_pair in enumerate(chunk):
            try:
                tile = self.create_tile_widget_for_pair(file_pair)
                if tile:
                    total_position = current_tile_count + idx
                    row = total_position // cols
                    col = total_position % cols
                    
                    gallery_manager.tiles_layout.addWidget(tile, row, col)
                    tile.setVisible(True)
                    
                    # Set tile number
                    tile_number = total_position + 1
                    total_tiles = len(self.main_window.controller.current_file_pairs)
                    tile.set_tile_number(tile_number, total_tiles)
                    
                    if hasattr(tile, "_update_filename_display"):
                        tile._update_filename_display()
                    
                    created_count += 1
                    self.increment_tile_counter(True)
                else:
                    self.increment_tile_counter(False)
                    
            except Exception as e:
                self.logger.error(f"Error creating tile for {file_pair}: {e}")
                self.increment_tile_counter(False)
        
        # Throttled progress update (not for every tile)
        self._update_progress_throttled()
        
    except Exception as e:
        self.logger.error(f"Error processing chunk: {e}")

def _update_progress_throttled(self):
    """Throttled progress update to prevent UI spam."""
    current_time = time.time()
    if not hasattr(self, '_last_progress_update'):
        self._last_progress_update = 0
        
    # Update progress max every 100ms
    if current_time - self._last_progress_update >= 0.1:
        try:
            progress_mgr = self._progress_manager or self.main_window.progress_manager
            gallery_mgr = self._gallery_manager or self.main_window.gallery_manager
            
            actual_tiles_count = len(gallery_mgr.gallery_tile_widgets)
            progress_mgr.update_tile_creation_progress(actual_tiles_count)
            
            self._last_progress_update = current_time
        except Exception as e:
            self.logger.warning(f"Error updating progress: {e}")

def _finish_async_processing(self, start_time: float):
    """Kończy asynchroniczne przetwarzanie z performance stats."""
    processing_time = time.time() - start_time
    stats = self.get_tile_stats()
    
    # Update performance statistics
    if stats["total"] > 0:
        self._performance_stats["avg_tile_creation_time"] = processing_time / stats["total"]
        self._performance_stats["last_batch_time"] = processing_time
        
    self.logger.info(f"Async batch processing completed: {stats['created']} created, "
                    f"{stats['failed']} failed in {processing_time:.2f}s")
    
    # Final UI update
    from PyQt6.QtWidgets import QApplication
    QApplication.instance().processEvents()
```

---

### PATCH 4: MEMORY LEAK PREVENTION W THUMBNAIL CALLBACKS

**Problem:** thumbnail_loaded_callback może powodować memory leaks
**Rozwiązanie:** Weak references i proper cleanup

```python
# W create_tile_widget_for_pair około linii 86-112
# Kod do zmiany całego callback:
# def thumbnail_loaded_callback(*args, **kwargs):
#     try:
#         if (hasattr(tile, "thumbnail_label") and tile.thumbnail_label is not None):
#             # ... existing code ...

# Zmienić na:
import weakref

def create_safe_thumbnail_callback(tile_ref: weakref.ref, original_callback):
    """Tworzy bezpieczny callback używający weak reference."""
    def safe_thumbnail_callback(*args, **kwargs):
        try:
            # Get tile from weak reference
            tile = tile_ref()
            if tile is None:
                # Tile was garbage collected
                return None
                
            # Check if widget is still valid
            if hasattr(tile, 'thumbnail_label') and tile.thumbnail_label is not None:
                try:
                    # Test if widget is still alive
                    tile.thumbnail_label.isVisible()
                    
                    # Call original callback
                    result = original_callback(*args, **kwargs)
                    
                    # Update progress safely
                    try:
                        progress_mgr = (
                            self._progress_manager or 
                            self.main_window.progress_manager
                        )
                        progress_mgr.on_thumbnail_progress()
                    except Exception as pe:
                        self.logger.debug(f"Progress update error: {pe}")
                        
                    return result
                    
                except RuntimeError as re:
                    # Widget was deleted
                    self.logger.debug(f"Widget deleted during callback: {re}")
                    return None
            else:
                return None
                
        except Exception as e:
            self.logger.warning(f"Error in safe thumbnail callback: {e}")
            return None
    
    return safe_thumbnail_callback

# Użyj safe callback:
if tile:
    # ... existing signal connections ...
    
    # Safe thumbnail callback with weak reference
    tile_ref = weakref.ref(tile)
    original_on_thumbnail_loaded = tile._on_thumbnail_loaded
    safe_callback = self.create_safe_thumbnail_callback(tile_ref, original_on_thumbnail_loaded)
    tile._on_thumbnail_loaded = safe_callback
```

---

### PATCH 5: THREAD-SAFE CLEANUP W on_tile_loading_finished

**Problem:** Możliwe race conditions przy zakończeniu ładowania
**Rozwiązanie:** Thread-safe cleanup z proper synchronization

```python
# W on_tile_loading_finished około linii 258-263
# Kod do zmiany:
# with self._creation_lock:
#     self._is_creating_tiles = False

# Zmienić na:
def on_tile_loading_finished(self):
    """Thread-safe zakończenie tworzenia wszystkich kafelków."""
    try:
        with self._creation_lock:
            if not self._is_creating_tiles.is_set():
                self.logger.warning("on_tile_loading_finished called but creation not in progress")
                return
                
            # Clear the creation flag
            self._is_creating_tiles.clear()
            
            # Notify all waiting threads
            self._tile_creation_condition.notify_all()
        
        # Get final statistics
        final_stats = self.get_tile_stats()
        self.logger.info(f"Tile creation finished: {final_stats}")
        
        # Cleanup worker threads
        self._cleanup_worker_threads()
        
        # Enable UI updates with error handling
        try:
            if hasattr(self.main_window, 'gallery_manager'):
                gallery_mgr = self.main_window.gallery_manager
                if hasattr(gallery_mgr, 'tiles_container'):
                    gallery_mgr.tiles_container.setUpdatesEnabled(True)
                    gallery_mgr.tiles_container.update()
        except Exception as e:
            self.logger.error(f"Error enabling UI updates: {e}")
        
        # Rest of the existing method...
        # (Keep all existing functionality but with better error handling)
        
    except Exception as e:
        self.logger.error(f"Error in on_tile_loading_finished: {e}")
        # Ensure we always clear the creation flag
        with self._creation_lock:
            self._is_creating_tiles.clear()

def _cleanup_worker_threads(self):
    """Cleanup any worker threads that were created."""
    try:
        for thread in self._worker_threads:
            if thread.is_alive():
                thread.join(timeout=1.0)  # Wait max 1 second
        self._worker_threads.clear()
    except Exception as e:
        self.logger.warning(f"Error cleaning up worker threads: {e}")

def wait_for_tile_creation_completion(self, timeout: float = 30.0) -> bool:
    """Wait for tile creation to complete with timeout."""
    try:
        with self._tile_creation_condition:
            return self._tile_creation_condition.wait_for(
                lambda: not self._is_creating_tiles.is_set(),
                timeout=timeout
            )
    except Exception as e:
        self.logger.error(f"Error waiting for tile creation: {e}")
        return False
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Batch processing** - adaptacyjny batch size działa dla różnych rozmiarów folderów
- [ ] **Thread safety** - brak race conditions przy równoczesnych operacjach
- [ ] **Memory management** - monitoring pamięci i adaptacja batch size
- [ ] **Progress updates** - throttled updates nie spamują UI
- [ ] **Asynchronous processing** - duże batche nie blokują UI
- [ ] **Error handling** - proper error handling w callback'ach
- [ ] **Resource cleanup** - brak memory leaks w thumbnail callbacks
- [ ] **Performance monitoring** - zbieranie i wykorzystanie statistics
- [ ] **Worker thread management** - proper cleanup worker threads
- [ ] **API compatibility** - wszystkie publiczne metody działają jak wcześniej

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **MainWindow integration** - wszystkie wywołania z MainWindow działają
- [ ] **GalleryManager compatibility** - integracja z force_create_all_tiles
- [ ] **ProgressManager integration** - throttled progress updates działają
- [ ] **WorkerManager compatibility** - start_data_processing_worker działa
- [ ] **FileTileWidget creation** - tworzenie kafli z sygnałami działa
- [ ] **Memory monitoring** - psutil integration działa poprawnie
- [ ] **Threading primitives** - Event, Condition, Queue działają poprawnie
- [ ] **Weak references** - proper cleanup prevent memory leaks

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test 10 plików** - szybkie przetwarzanie bez adaptacji
- [ ] **Test 100 plików** - normalne batch processing
- [ ] **Test 1000 plików** - adaptive batch size optimization
- [ ] **Test 5000+ plików** - asynchroniczne przetwarzanie z chunking
- [ ] **Test równoczesne okienka** - thread safety przy multiple instances
- [ ] **Test memory pressure** - zachowanie przy niskiej pamięci
- [ ] **Test thumbnail callbacks** - brak memory leaks w długich sesjach

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - wszystkie testy muszą przejść
- [ ] **THREAD SAFETY** - brak race conditions w stress tests
- [ ] **MEMORY EFFICIENCY** - brak memory leaks w długich sesjach
- [ ] **UI RESPONSIVENESS** - UI nie blokuje się >100ms podczas batch processing