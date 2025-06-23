# PATCH-CODE DLA: TILE_MANAGER - OPTYMALIZACJA BATCH PROCESSING KAFLI

**Powiązany plik z analizą:** `../corrections/tile_manager_correction_kafli.md`
**Zasady ogólne:** `../../../_BASE_/refactoring_rules.md`

---

### PATCH 1: TRUE BATCH PROCESSING OPTIMIZATION

**Problem:** create_tile_widgets_batch tworzy kafle indywidualnie zamiast prawdziwego batch processing
**Rozwiązanie:** Implementacja batch creation z deferred UI updates i memory optimization

```python
import threading
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import weakref

class TileManager:
    def __init__(self, main_window):
        """Enhanced initialization z batch processing support."""
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)
        
        # Thread-safe batch processing state
        self._is_creating_tiles = False
        self._batch_lock = threading.RLock()
        
        # Batch processing optimization
        self._batch_size = 50  # Optimal batch size dla UI responsiveness
        self._memory_monitor = None
        
        # Tile pool dla reuse (object pooling pattern)
        self._tile_pool = []
        self._max_pool_size = 100
        
        # Signal multiplexing - jeden bus zamiast 6 sygnałów per tile
        self._signal_bus = None
        self._setup_signal_multiplexing()

    def _setup_signal_multiplexing(self):
        """Setup central signal bus dla wszystkich kafli."""
        from PyQt6.QtCore import QObject, pyqtSignal
        
        class TileSignalBus(QObject):
            # Consolidated signals for all tiles
            archive_open_requested = pyqtSignal(object)  # FilePair
            preview_image_requested = pyqtSignal(object)
            tile_selected = pyqtSignal(object, bool)
            stars_changed = pyqtSignal(object, int)
            color_tag_changed = pyqtSignal(object, str)
            tile_context_menu_requested = pyqtSignal(object, object, object)
            
        self._signal_bus = TileSignalBus()
        
        # Connect to main window once
        self._signal_bus.archive_open_requested.connect(self.main_window.open_archive)
        self._signal_bus.preview_image_requested.connect(self.main_window._show_preview_dialog)
        self._signal_bus.tile_selected.connect(self.main_window._handle_tile_selection_changed)
        self._signal_bus.stars_changed.connect(self.main_window._handle_stars_changed)
        self._signal_bus.color_tag_changed.connect(self.main_window._handle_color_tag_changed)
        self._signal_bus.tile_context_menu_requested.connect(self.main_window._show_file_context_menu)

    def create_tile_widgets_batch(self, file_pairs_batch: List) -> int:
        """
        TRUE BATCH PROCESSING - optymalizacja dla tysięcy kafli.
        Tworzy kafle w prawdziwych batchach z deferred UI updates.
        """
        if not file_pairs_batch:
            return 0
            
        batch_size = len(file_pairs_batch)
        self.logger.info(f"🚀 TRUE BATCH: Creating {batch_size} tiles with optimized batching")
        
        # Memory pressure monitoring
        import psutil
        memory_before = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        
        try:
            # OPTIMIZATION: Disable UI updates podczas batch creation
            gallery_manager = self.main_window.gallery_manager
            gallery_manager.tiles_container.setUpdatesEnabled(False)
            
            # OPTIMIZATION: Pre-calculate layout geometry raz dla całego batchu
            geometry = self._get_cached_batch_geometry(batch_size)
            
            # OPTIMIZATION: Batch tile creation z deferred layout operations
            created_tiles = self._create_tiles_batch_optimized(file_pairs_batch, geometry)
            
            # OPTIMIZATION: Batch layout operations - dodaj wszystkie kafle jednocześnie
            self._add_tiles_to_layout_batch(created_tiles, geometry)
            
            # OPTIMIZATION: Batch signal connections przez signal bus
            self._connect_tiles_to_signal_bus(created_tiles)
            
            # OPTIMIZATION: Batch visibility i numbering updates
            self._finalize_tiles_batch(created_tiles, geometry)
            
            created_count = len(created_tiles)
            
            # Memory monitoring
            memory_after = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            memory_delta = memory_after - memory_before
            
            self.logger.info(f"🚀 BATCH COMPLETE: Created {created_count} tiles, memory delta: {memory_delta:.1f}MB")
            
            # OPTIMIZATION: Update progress raz dla całego batchu
            actual_tiles_count = len(gallery_manager.gallery_tile_widgets)
            self.main_window.progress_manager.update_tile_creation_progress(actual_tiles_count)
            
            return created_count
            
        finally:
            # Re-enable UI updates
            gallery_manager.tiles_container.setUpdatesEnabled(True)
            
            # OPTIMIZATION: Single processEvents call zamiast per-tile
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().processEvents()

    def _get_cached_batch_geometry(self, batch_size: int) -> Dict[str, Any]:
        """Pre-calculate layout geometry dla całego batchu."""
        gallery_manager = self.main_window.gallery_manager
        geometry = gallery_manager._get_cached_geometry()
        
        # Add batch-specific calculations
        current_tile_count = len(gallery_manager.gallery_tile_widgets)
        total_tiles = len(self.main_window.controller.current_file_pairs)
        
        geometry.update({
            'batch_size': batch_size,
            'start_position': current_tile_count,
            'total_tiles': total_tiles,
            'end_position': current_tile_count + batch_size
        })
        
        return geometry

    def _create_tiles_batch_optimized(self, file_pairs_batch: List, geometry: Dict) -> List:
        """Optimized tile creation z object pooling."""
        created_tiles = []
        
        for idx, file_pair in enumerate(file_pairs_batch):
            # OPTIMIZATION: Try to reuse tile from pool
            tile = self._get_tile_from_pool() or self._create_new_tile(file_pair)
            
            if tile:
                # Set data efficiently
                tile.set_file_pair(file_pair)
                created_tiles.append(tile)
                
                # OPTIMIZATION: Calculate position raz
                total_position = geometry['start_position'] + idx
                tile._batch_position = total_position
                tile._batch_geometry = geometry
                
        return created_tiles

    def _add_tiles_to_layout_batch(self, tiles: List, geometry: Dict):
        """Batch layout operations - wszystkie kafle jednocześnie."""
        gallery_manager = self.main_window.gallery_manager
        cols = geometry['cols']
        
        # OPTIMIZATION: Batch layout additions
        for tile in tiles:
            row = tile._batch_position // cols
            col = tile._batch_position % cols
            gallery_manager.tiles_layout.addWidget(tile, row, col)

    def _connect_tiles_to_signal_bus(self, tiles: List):
        """Connect tiles do signal bus zamiast individual signals."""
        for tile in tiles:
            # OPTIMIZATION: Connect do central signal bus
            tile.archive_open_requested.connect(self._signal_bus.archive_open_requested.emit)
            tile.preview_image_requested.connect(self._signal_bus.preview_image_requested.emit)
            tile.tile_selected.connect(self._signal_bus.tile_selected.emit)
            tile.stars_changed.connect(self._signal_bus.stars_changed.emit)
            tile.color_tag_changed.connect(self._signal_bus.color_tag_changed.emit)
            tile.tile_context_menu_requested.connect(self._signal_bus.tile_context_menu_requested.emit)

    def _finalize_tiles_batch(self, tiles: List, geometry: Dict):
        """Batch finalization - visibility i numbering."""
        total_tiles = geometry['total_tiles']
        
        for tile in tiles:
            # Set visibility
            tile.setVisible(True)
            
            # Set tile number
            tile_number = tile._batch_position + 1
            tile.set_tile_number(tile_number, total_tiles)
            
            # Force display update efficiently
            if hasattr(tile, '_update_filename_display'):
                tile._update_filename_display()
```

---

### PATCH 2: THREAD-SAFE BATCH PROCESSING STATE

**Problem:** `_is_creating_tiles` flag nie jest thread-safe, może powodować race conditions
**Rozwiązanie:** Thread-safe state management z proper locking

```python
import threading
from contextlib import contextmanager

class TileManager:
    def __init__(self, main_window):
        # Existing code...
        
        # Thread-safe batch state
        self._batch_state = {
            'is_creating': False,
            'current_batch_id': None,
            'tiles_created': 0,
            'memory_peak': 0
        }
        self._batch_lock = threading.RLock()

    @contextmanager
    def _batch_creation_context(self, batch_id: str = None):
        """Thread-safe context manager for batch creation."""
        batch_id = batch_id or f"batch_{threading.get_ident()}_{id(self)}"
        
        with self._batch_lock:
            if self._batch_state['is_creating']:
                self.logger.warning(f"Batch creation already in progress: {self._batch_state['current_batch_id']}")
                raise RuntimeError("Concurrent batch creation not allowed")
            
            self._batch_state.update({
                'is_creating': True,
                'current_batch_id': batch_id,
                'tiles_created': 0,
                'memory_peak': 0
            })
            
        try:
            self.logger.debug(f"🔒 BATCH START: {batch_id}")
            yield batch_id
            
        finally:
            with self._batch_lock:
                self.logger.debug(f"🔓 BATCH END: {batch_id}, created {self._batch_state['tiles_created']} tiles")
                self._batch_state.update({
                    'is_creating': False,
                    'current_batch_id': None,
                    'tiles_created': 0,
                    'memory_peak': 0
                })

    def start_tile_creation(self, file_pairs: list):
        """Thread-safe batch creation start."""
        try:
            with self._batch_creation_context() as batch_id:
                self.main_window.gallery_manager.tiles_container.setUpdatesEnabled(False)
                self.logger.debug(f"🚀 Batch creation started: {batch_id}")
                
                # Use worker to process data in background
                self.main_window.worker_manager.start_data_processing_worker(file_pairs)
                
        except RuntimeError as e:
            self.logger.warning(f"Failed to start tile creation: {e}")
            return

    def is_batch_creating(self) -> bool:
        """Thread-safe check czy batch creation w toku."""
        with self._batch_lock:
            return self._batch_state['is_creating']

    def get_batch_stats(self) -> Dict[str, Any]:
        """Thread-safe pobieranie statystyk batch."""
        with self._batch_lock:
            return self._batch_state.copy()
```

---

### PATCH 3: MEMORY PRESSURE MONITORING

**Problem:** Brak memory monitoring podczas batch creation tysięcy kafli
**Rozwiązanie:** Real-time memory monitoring z automatic batch size adjustment

```python
import psutil
import gc
from typing import Optional

class MemoryPressureMonitor:
    """Monitor memory pressure podczas batch creation kafli."""
    
    def __init__(self, max_memory_mb: int = 500):
        self.max_memory_mb = max_memory_mb
        self.process = psutil.Process()
        self.baseline_memory = 0
        self.peak_memory = 0
        
    def start_monitoring(self):
        """Start memory monitoring dla batch."""
        self.baseline_memory = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory = self.baseline_memory
        
    def check_memory_pressure(self) -> Dict[str, Any]:
        """Check current memory pressure."""
        current_memory = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory = max(self.peak_memory, current_memory)
        
        delta = current_memory - self.baseline_memory
        pressure_ratio = delta / self.max_memory_mb if self.max_memory_mb > 0 else 0
        
        return {
            'current_mb': current_memory,
            'baseline_mb': self.baseline_memory,
            'delta_mb': delta,
            'peak_mb': self.peak_memory,
            'pressure_ratio': pressure_ratio,
            'is_critical': pressure_ratio > 0.8
        }
        
    def should_trigger_gc(self, pressure_ratio: float = 0.6) -> bool:
        """Determine czy trigger garbage collection."""
        stats = self.check_memory_pressure()
        return stats['pressure_ratio'] > pressure_ratio

class TileManager:
    def __init__(self, main_window):
        # Existing code...
        self._memory_monitor = MemoryPressureMonitor(max_memory_mb=500)
        
    def create_tile_widgets_batch(self, file_pairs_batch: List) -> int:
        """Enhanced batch creation z memory monitoring."""
        if not file_pairs_batch:
            return 0
            
        # Start memory monitoring
        self._memory_monitor.start_monitoring()
        
        try:
            # Adaptive batch sizing based on memory pressure
            effective_batch_size = self._calculate_effective_batch_size(len(file_pairs_batch))
            
            created_count = 0
            for chunk_start in range(0, len(file_pairs_batch), effective_batch_size):
                chunk_end = min(chunk_start + effective_batch_size, len(file_pairs_batch))
                chunk = file_pairs_batch[chunk_start:chunk_end]
                
                # Create chunk z memory monitoring
                chunk_created = self._create_chunk_with_monitoring(chunk)
                created_count += chunk_created
                
                # Check memory pressure po każdym chunk
                memory_stats = self._memory_monitor.check_memory_pressure()
                if memory_stats['is_critical']:
                    self.logger.warning(f"🚨 MEMORY CRITICAL: {memory_stats['current_mb']:.1f}MB, triggering GC")
                    gc.collect()
                    
                    # Re-check after GC
                    memory_stats = self._memory_monitor.check_memory_pressure()
                    if memory_stats['is_critical']:
                        self.logger.error(f"🚨 MEMORY STILL CRITICAL after GC, stopping batch creation")
                        break
                        
            return created_count
            
        finally:
            final_stats = self._memory_monitor.check_memory_pressure()
            self.logger.info(f"🧠 MEMORY STATS: Peak {final_stats['peak_mb']:.1f}MB, Delta {final_stats['delta_mb']:.1f}MB")

    def _calculate_effective_batch_size(self, total_tiles: int) -> int:
        """Calculate optimal batch size based on memory pressure."""
        base_batch_size = self._batch_size
        
        # Adaptive sizing based on total tiles
        if total_tiles > 1000:
            return max(25, base_batch_size // 2)  # Smaller batches for large datasets
        elif total_tiles > 500:
            return max(30, base_batch_size // 1.5)
        else:
            return base_batch_size

    def _create_chunk_with_monitoring(self, chunk: List) -> int:
        """Create chunk z memory monitoring per chunk."""
        pre_chunk_memory = self._memory_monitor.process.memory_info().rss / 1024 / 1024
        
        # Create tiles for chunk
        created_tiles = self._create_tiles_batch_optimized(chunk, self._get_cached_batch_geometry(len(chunk)))
        
        post_chunk_memory = self._memory_monitor.process.memory_info().rss / 1024 / 1024
        chunk_memory_delta = post_chunk_memory - pre_chunk_memory
        
        self.logger.debug(f"📊 CHUNK: {len(created_tiles)} tiles, {chunk_memory_delta:.1f}MB delta")
        
        return len(created_tiles)
```

---

### PATCH 4: DEPENDENCY INJECTION PATTERN

**Problem:** Tight coupling z MainWindow - bezpośrednie referencje zamiast dependency injection
**Rozwiązanie:** Dependency injection pattern dla better testability i loose coupling

```python
from abc import ABC, abstractmethod
from typing import Protocol

# Define interfaces dla dependency injection
class GalleryManagerInterface(Protocol):
    def create_tile_widget_for_pair(self, file_pair, parent): ...
    def get_all_tile_widgets(self): ...
    
class ProgressManagerInterface(Protocol):
    def update_tile_creation_progress(self, count: int): ...
    def finish_tile_creation(self): ...
    
class WorkerManagerInterface(Protocol):
    def start_data_processing_worker(self, file_pairs: list): ...

class TileManagerDependencies:
    """Container dla dependencies TileManager."""
    
    def __init__(self,
                 gallery_manager: GalleryManagerInterface,
                 progress_manager: ProgressManagerInterface,
                 worker_manager: WorkerManagerInterface,
                 logger: logging.Logger = None):
        self.gallery_manager = gallery_manager
        self.progress_manager = progress_manager
        self.worker_manager = worker_manager
        self.logger = logger or logging.getLogger(__name__)

class TileManager:
    """Enhanced TileManager z dependency injection."""
    
    def __init__(self, dependencies: TileManagerDependencies, main_window=None):
        """
        Initialize z dependency injection pattern.
        
        Args:
            dependencies: Container z wszystkimi dependencies
            main_window: Optional reference dla legacy compatibility
        """
        self.deps = dependencies
        self.logger = dependencies.logger
        
        # Legacy compatibility
        self.main_window = main_window
        
        # Enhanced initialization
        self._initialize_batch_processing()
        self._initialize_memory_monitoring()
        self._setup_signal_multiplexing()

    def create_tile_widget_for_pair(self, file_pair: FilePair) -> Optional[object]:
        """Create single tile z dependency injection."""
        if not file_pair or not hasattr(file_pair, "archive_path") or not file_pair.archive_path:
            self.logger.error(f"Invalid FilePair: {file_pair}")
            return None

        # Use injected gallery manager
        tile = self.deps.gallery_manager.create_tile_widget_for_pair(file_pair, self.main_window)
        
        if tile:
            # Connect do signal bus zamiast individual connections
            self._connect_tile_to_signal_bus(tile)
            
            # Enhanced thumbnail callback z dependency injection
            self._setup_enhanced_thumbnail_callback(tile)
            
        return tile

    def start_tile_creation(self, file_pairs: list):
        """Start tile creation z dependency injection."""
        try:
            with self._batch_creation_context() as batch_id:
                # Use injected worker manager
                self.deps.worker_manager.start_data_processing_worker(file_pairs)
                
        except RuntimeError as e:
            self.logger.warning(f"Failed to start tile creation: {e}")

    def _setup_enhanced_thumbnail_callback(self, tile):
        """Enhanced thumbnail callback z error handling."""
        original_callback = getattr(tile, '_on_thumbnail_loaded', None)
        if not original_callback:
            return
            
        def enhanced_callback(*args, **kwargs):
            try:
                if hasattr(tile, "thumbnail_label") and tile.thumbnail_label is not None:
                    # Background execution dla non-blocking operation
                    result = original_callback(*args, **kwargs)
                    
                    # Use injected progress manager
                    self.deps.progress_manager.on_thumbnail_progress()
                    return result
                    
            except RuntimeError:
                self.logger.debug("Thumbnail callback: Widget destroyed")
            except Exception as e:
                self.logger.warning(f"Enhanced thumbnail callback error: {e}")
            return None
            
        tile._on_thumbnail_loaded = enhanced_callback

# Factory dla backward compatibility
def create_tile_manager(main_window) -> TileManager:
    """Factory function dla legacy compatibility."""
    dependencies = TileManagerDependencies(
        gallery_manager=main_window.gallery_manager,
        progress_manager=main_window.progress_manager,
        worker_manager=main_window.worker_manager,
        logger=logging.getLogger(__name__)
    )
    
    return TileManager(dependencies, main_window)
```

---

### PATCH 5: HASH-BASED REFRESH OPTIMIZATION

**Problem:** refresh_existing_tiles iteruje przez wszystkie kafle - O(n) complexity
**Rozwiązanie:** Hash-based lookup dla O(1) refresh operations

```python
from typing import Dict, Set
import weakref

class TileManager:
    def __init__(self, dependencies: TileManagerDependencies, main_window=None):
        # Existing code...
        
        # Hash-based tile tracking dla fast lookups
        self._tile_lookup: Dict[str, weakref.ref] = {}  # archive_path -> tile weakref
        self._tile_update_queue: Set[str] = set()  # Pending updates
        
    def _register_tile_for_lookup(self, tile, file_pair: FilePair):
        """Register tile w hash lookup table."""
        if file_pair and hasattr(file_pair, 'archive_path'):
            archive_path = file_pair.archive_path
            
            # Use weak reference żeby avoid memory leaks
            self._tile_lookup[archive_path] = weakref.ref(tile, 
                                                         lambda ref: self._cleanup_tile_lookup(archive_path))
            
    def _cleanup_tile_lookup(self, archive_path: str):
        """Cleanup dead tile references."""
        self._tile_lookup.pop(archive_path, None)
        self._tile_update_queue.discard(archive_path)

    def refresh_existing_tiles(self, file_pairs_list: list):
        """
        O(1) HASH-BASED refresh zamiast O(n) iteration.
        Optymalizacja dla tysięcy kafli.
        """
        if not file_pairs_list:
            return
            
        self.logger.debug(f"🔄 HASH REFRESH: {len(file_pairs_list)} file pairs")
        
        # Build update map dla batch processing
        update_map = {}
        for file_pair in file_pairs_list:
            if hasattr(file_pair, 'archive_path'):
                archive_path = file_pair.archive_path
                update_map[archive_path] = file_pair
                self._tile_update_queue.add(archive_path)
        
        # O(1) hash-based updates zamiast O(n) iteration
        refreshed_count = 0
        dead_refs = []
        
        for archive_path in self._tile_update_queue.copy():
            tile_ref = self._tile_lookup.get(archive_path)
            if tile_ref:
                tile = tile_ref()  # Get tile from weak reference
                if tile and archive_path in update_map:
                    # Fast hash lookup zamiast linear search
                    updated_file_pair = update_map[archive_path]
                    tile.update_data(updated_file_pair)
                    refreshed_count += 1
                    self._tile_update_queue.discard(archive_path)
                elif not tile:
                    # Dead reference - cleanup
                    dead_refs.append(archive_path)
        
        # Cleanup dead references
        for archive_path in dead_refs:
            self._cleanup_tile_lookup(archive_path)
            
        self.logger.debug(f"🔄 HASH REFRESH COMPLETE: {refreshed_count} tiles updated, {len(dead_refs)} dead refs cleaned")
        
        # Batch UI update zamiast individual updates
        if refreshed_count > 0:
            self._batch_ui_refresh()

    def _batch_ui_refresh(self):
        """Batch UI refresh zamiast individual tile updates."""
        if hasattr(self.deps.gallery_manager, 'tiles_container'):
            # Single UI update dla całego container
            self.deps.gallery_manager.tiles_container.update()
            
        # Process events raz dla wszystkich updates
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().processEvents()

    def create_tile_widget_for_pair(self, file_pair: FilePair) -> Optional[object]:
        """Enhanced tile creation z hash registration."""
        tile = super().create_tile_widget_for_pair(file_pair)
        
        if tile and file_pair:
            # Register w hash lookup dla fast refresh
            self._register_tile_for_lookup(tile, file_pair)
            
        return tile
```

---

### PATCH 6: BACKGROUND THUMBNAIL PROCESSING

**Problem:** Thumbnail callback wykonuje się w UI thread, może blokować responsywność
**Rozwiązanie:** Background thumbnail processing z queue management

```python
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

@dataclass
class ThumbnailEvent:
    tile_id: str
    args: tuple
    kwargs: dict
    timestamp: float

class BackgroundThumbnailProcessor:
    """Background processor dla thumbnail events."""
    
    def __init__(self, max_workers: int = 2):
        self.thumbnail_queue = queue.Queue(maxsize=1000)
        self.executor = ThreadPoolExecutor(max_workers=max_workers, 
                                         thread_name_prefix="ThumbnailProcessor")
        self.is_running = True
        self._stats = {'processed': 0, 'failed': 0, 'queue_size': 0}
        
        # Start background processor
        self.processor_thread = threading.Thread(target=self._process_thumbnails, 
                                               daemon=True)
        self.processor_thread.start()
        
    def submit_thumbnail_event(self, tile_id: str, *args, **kwargs):
        """Submit thumbnail event dla background processing."""
        import time
        event = ThumbnailEvent(tile_id, args, kwargs, time.time())
        
        try:
            self.thumbnail_queue.put_nowait(event)
            self._stats['queue_size'] = self.thumbnail_queue.qsize()
        except queue.Full:
            # Drop oldest events jeśli queue full
            try:
                self.thumbnail_queue.get_nowait()
                self.thumbnail_queue.put_nowait(event)
            except queue.Empty:
                pass
                
    def _process_thumbnails(self):
        """Background thread dla processing thumbnail events."""
        while self.is_running:
            try:
                event = self.thumbnail_queue.get(timeout=1.0)
                
                # Process w thread pool
                future = self.executor.submit(self._handle_thumbnail_event, event)
                
                # Update stats
                self._stats['processed'] += 1
                self._stats['queue_size'] = self.thumbnail_queue.qsize()
                
            except queue.Empty:
                continue
            except Exception as e:
                self._stats['failed'] += 1
                logging.warning(f"Background thumbnail processing error: {e}")

    def _handle_thumbnail_event(self, event: ThumbnailEvent):
        """Handle individual thumbnail event w background."""
        # Process thumbnail event (może być I/O intensive)
        # This runs w background thread, nie blokuje UI
        pass
        
    def shutdown(self):
        """Graceful shutdown background processor."""
        self.is_running = False
        self.executor.shutdown(wait=True)
        
    def get_stats(self) -> dict:
        """Get processing statistics."""
        return self._stats.copy()

class TileManager:
    def __init__(self, dependencies: TileManagerDependencies, main_window=None):
        # Existing code...
        
        # Background thumbnail processing
        self._thumbnail_processor = BackgroundThumbnailProcessor(max_workers=2)
        
    def _setup_enhanced_thumbnail_callback(self, tile):
        """Enhanced thumbnail callback z background processing."""
        original_callback = getattr(tile, '_on_thumbnail_loaded', None)
        if not original_callback:
            return
            
        tile_id = f"tile_{id(tile)}"
        
        def background_thumbnail_callback(*args, **kwargs):
            """Non-blocking thumbnail callback via background processor."""
            try:
                if hasattr(tile, "thumbnail_label") and tile.thumbnail_label is not None:
                    # Check widget validity quickly w UI thread
                    tile.thumbnail_label.isVisible()
                    
                    # Submit do background processing
                    self._thumbnail_processor.submit_thumbnail_event(
                        tile_id, tile, original_callback, args, kwargs
                    )
                    
                    # Quick UI thread update dla progress
                    self.deps.progress_manager.on_thumbnail_progress()
                    
            except RuntimeError:
                # Widget destroyed - no action needed
                pass
            except Exception as e:
                self.logger.warning(f"Background thumbnail callback error: {e}")
                
        tile._on_thumbnail_loaded = background_thumbnail_callback

    def shutdown(self):
        """Graceful shutdown tile manager."""
        if hasattr(self, '_thumbnail_processor'):
            self._thumbnail_processor.shutdown()
            
        # Cleanup hash lookup
        self._tile_lookup.clear()
        self._tile_update_queue.clear()
```

---

## ✅ CHECKLISTA WERYFIKACYJNA KAFLI (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI BATCH PROCESSING KAFLI DO WERYFIKACJI:**

- [ ] **True batch creation** - czy 1000+ kafli tworzy się w <2s zamiast >10s
- [ ] **Memory efficiency** - czy memory usage <500MB dla tysięcy kafli
- [ ] **Thread safety** - czy concurrent batch operations nie powodują race conditions
- [ ] **Signal multiplexing** - czy central signal bus działa dla wszystkich kafli
- [ ] **Layout optimization** - czy batch layout operations są efficient
- [ ] **Progress tracking** - czy batch progress updates działają smooth
- [ ] **Hash-based refresh** - czy O(1) lookup działa dla refresh operations
- [ ] **Background processing** - czy thumbnail processing nie blokuje UI
- [ ] **Memory monitoring** - czy automatic GC triggering działa przy memory pressure
- [ ] **Dependency injection** - czy loose coupling pattern działa poprawnie

#### **ZALEŻNOŚCI BATCH PROCESSING DO WERYFIKACJI:**

- [ ] **GalleryManager integration** - czy batch operations współpracują z virtual scrolling
- [ ] **ProgressManager batching** - czy progress updates nie spamują UI
- [ ] **WorkerManager coordination** - czy background workers koordinują z batch creation
- [ ] **Signal bus connections** - czy wszystkie sygnały kafli działają przez central bus
- [ ] **Memory monitoring alerts** - czy critical memory warnings działają
- [ ] **Thread pool management** - czy background processors nie leakują threads
- [ ] **Hash lookup consistency** - czy weak references cleanup poprawnie
- [ ] **Layout geometry cache** - czy batch geometry calculations są correct
- [ ] **UI responsiveness** - czy batch operations nie blokują UI thread

#### **TESTY WYDAJNOŚCIOWE BATCH PROCESSING KAFLI:**

- [ ] **1000+ kafli creation benchmark** - target <2s vs current >10s
- [ ] **Memory usage during batch** - target <500MB peak podczas creation
- [ ] **Thread safety stress test** - concurrent batch operations bez crashes
- [ ] **Signal multiplexing performance** - czy central bus jest faster than individual signals
- [ ] **Hash refresh performance** - O(1) lookup vs O(n) iteration benchmark
- [ ] **Background thumbnail processing** - czy nie blokuje UI responsiveness
- [ ] **Layout batch operations** - czy geometry calculations są optimized
- [ ] **Memory pressure handling** - czy automatic GC prevents OOM
- [ ] **Dependency injection overhead** - czy performance nie degraduje vs tight coupling

#### **KRYTERIA SUKCESU BATCH PROCESSING KAFLI:**

- [ ] **PERFORMANCE TARGET ACHIEVED** - 1000+ kafli w <2s consistently
- [ ] **MEMORY EFFICIENCY VERIFIED** - <500MB dla galerii z tysiącami kafli
- [ ] **THREAD SAFETY CONFIRMED** - brak race conditions w batch state management
- [ ] **UI RESPONSIVENESS MAINTAINED** - smooth scrolling podczas batch creation