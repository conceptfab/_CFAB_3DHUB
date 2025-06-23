# PATCH-CODE DLA: GALLERY_MANAGER.PY

**Powiązany plik z analizą:** `../corrections/gallery_manager_correction_kafli.md`
**Zasady ogólne:** `../../_BASE_/refactoring_rules.md`

---

### PATCH 1: EXTRACT LAYOUT GEOMETRY MANAGER

**Problem:** LayoutGeometry class jest mixed z GalleryManager - brak separation of concerns
**Rozwiązanie:** Extract jako standalone LayoutGeometryManager z dependency injection

```python
"""
Manager galerii - zarządzanie wyświetlaniem kafelków.
MAJOR REFACTORING: Decomposition 958-liniowego pliku na logiczne komponenty.
"""

import logging
import math
import threading
import time
import weakref
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Protocol

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src import app_config
from src.controllers.gallery_controller import GalleryController
from src.models.file_pair import FilePair
from src.models.special_folder import SpecialFolder
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.ui.widgets.special_folder_tile_widget import SpecialFolderTileWidget
from src.ui.widgets.tile_resource_manager import get_resource_manager

logger = logging.getLogger(__name__)


@dataclass
class LayoutParams:
    """Value object dla parametrów layoutu."""
    
    container_width: int
    cols: int
    tile_width_spacing: int
    tile_height_spacing: int
    thumbnail_size: int
    calculated_at: float


@dataclass  
class VisibleRange:
    """Value object dla zakresu widocznych elementów."""
    
    start_item: int
    end_item: int
    start_row: int
    end_row: int
    buffer_size: int


class ScrollAreaProtocol(Protocol):
    """Protocol dla scroll area dependency."""
    
    def width(self) -> int: ...
    def height(self) -> int: ...
    def verticalScrollBar(self): ...
    def viewport(self): ...


class LayoutGeometryManager:
    """
    EXTRACTED: Thread-safe manager dla obliczeń geometrii layoutu.
    Separated from GalleryManager dla better testability i separation of concerns.
    """

    def __init__(self, scroll_area: ScrollAreaProtocol, tiles_layout: QGridLayout, cache_size_limit: int = 50):
        self.scroll_area = scroll_area
        self.tiles_layout = tiles_layout
        
        # Thread-safe cache z size limits
        self._cache: Dict[Tuple, LayoutParams] = {}
        self._cache_lock = threading.RLock()
        self._cache_timestamps: Dict[Tuple, float] = {}
        self._cache_ttl = 5.0  # Cache TTL w sekundach
        self._cache_size_limit = cache_size_limit
        
        # Cache statistics dla monitoring
        self._cache_stats = {"hits": 0, "misses": 0, "invalidations": 0, "evictions": 0}

    def get_layout_params(self, thumbnail_size: int) -> LayoutParams:
        """Thread-safe zwracanie parametrów layoutu z intelligent caching i size limits."""
        current_time = time.time()
        
        cache_key = (
            self.scroll_area.width(),
            self.scroll_area.height(), 
            thumbnail_size,
        )
        
        with self._cache_lock:
            # Check cache validity z TTL
            if (
                cache_key in self._cache
                and cache_key in self._cache_timestamps
                and current_time - self._cache_timestamps[cache_key] < self._cache_ttl
            ):
                self._cache_stats["hits"] += 1
                return self._cache[cache_key]
            
            # Cache miss or expired - calculate new params
            self._cache_stats["misses"] += 1
            
            container_width = (
                self.scroll_area.width() - self.scroll_area.verticalScrollBar().width()
            )
            tile_width_spacing = thumbnail_size + self.tiles_layout.spacing() + 10
            tile_height_spacing = thumbnail_size + self.tiles_layout.spacing() + 40
            cols = max(1, math.ceil(container_width / tile_width_spacing))
            
            params = LayoutParams(
                container_width=container_width,
                cols=cols,
                tile_width_spacing=tile_width_spacing,
                tile_height_spacing=tile_height_spacing,
                thumbnail_size=thumbnail_size,
                calculated_at=current_time,
            )
            
            # Store w cache z timestamp i size limit enforcement
            self._enforce_cache_size_limit()
            self._cache[cache_key] = params
            self._cache_timestamps[cache_key] = current_time
            
            # Cleanup expired cache entries
            self._cleanup_expired_cache(current_time)
            
            return params

    def _enforce_cache_size_limit(self):
        """Enforce cache size limit przez LRU eviction (called with lock held)."""
        if len(self._cache) >= self._cache_size_limit:
            # Find oldest entry dla LRU eviction
            oldest_key = min(self._cache_timestamps.keys(), 
                           key=lambda k: self._cache_timestamps[k])
            
            self._cache.pop(oldest_key, None)
            self._cache_timestamps.pop(oldest_key, None)
            self._cache_stats["evictions"] += 1

    def _cleanup_expired_cache(self, current_time: float):
        """Cleanup expired cache entries (called with lock held)."""
        expired_keys = [
            key
            for key, timestamp in self._cache_timestamps.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        
        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
            self._cache_stats["invalidations"] += 1

    def get_visible_range(self, thumbnail_size: int, total_items: int, buffer_multiplier: float = 1.0) -> VisibleRange:
        """Thread-safe obliczanie zakresu widocznych elementów z configurable buffering."""
        params = self.get_layout_params(thumbnail_size)
        
        viewport_height = self.scroll_area.viewport().height()
        scroll_y = self.scroll_area.verticalScrollBar().value()
        
        # Configurable buffering based on scroll speed i parameter
        base_buffer = viewport_height * buffer_multiplier
        buffer = int(base_buffer)
        
        visible_start_y = max(0, scroll_y - buffer)
        visible_end_y = scroll_y + viewport_height + buffer
        
        first_visible_row = max(0, math.floor(visible_start_y / params.tile_height_spacing))
        last_visible_row = math.ceil(visible_end_y / params.tile_height_spacing)
        
        first_visible_item = first_visible_row * params.cols
        last_visible_item = min((last_visible_row + 1) * params.cols, total_items)
        
        return VisibleRange(
            start_item=first_visible_item,
            end_item=last_visible_item,
            start_row=first_visible_row,
            end_row=last_visible_row,
            buffer_size=buffer,
        )

    def invalidate_cache(self):
        """Force invalidation całego cache (np. przy resize events)."""
        with self._cache_lock:
            cache_size = len(self._cache)
            self._cache.clear()
            self._cache_timestamps.clear()
            self._cache_stats["invalidations"] += cache_size

    def get_cache_stats(self) -> Dict[str, int]:
        """Zwróć cache statistics dla performance monitoring."""
        with self._cache_lock:
            stats = self._cache_stats.copy()
            stats["cache_size"] = len(self._cache)
            stats["cache_limit"] = self._cache_size_limit
            return stats
```

---

### PATCH 2: EXTRACT CONFIGURABLE BATCH PROCESSOR

**Problem:** Hardcoded batch sizes i scattered batch processing logic
**Rozwiązanie:** Unified ConfigurableBatchProcessor dla wszystkich batch operations

```python
@dataclass
class BatchConfig:
    """Konfiguracja dla batch processing."""
    
    default_size: int = 50
    large_batch_size: int = 100
    memory_check_threshold: int = 100
    progress_update_interval: int = 10
    ui_process_events_interval: int = 20


class BatchProcessor:
    """
    EXTRACTED: Configurable batch processor dla wszystkich batch operations.
    Eliminuje hardcoded batch sizes i unified progress tracking.
    """
    
    def __init__(self, config: BatchConfig, logger: logging.Logger):
        self.config = config
        self.logger = logger
        self._processed_count = 0
        self._total_count = 0
        self._batch_stats = {"batches_processed": 0, "items_processed": 0, "errors": 0}
    
    def process_items_in_batches(
        self, 
        items: List[Any], 
        processor_func: callable, 
        progress_callback: Optional[callable] = None,
        memory_check_func: Optional[callable] = None,
        batch_size: Optional[int] = None
    ) -> Dict[str, int]:
        """
        Generic batch processor z configurable parameters.
        
        Args:
            items: Lista elementów do przetworzenia
            processor_func: Funkcja przetwarzająca pojedynczy element (item) -> bool
            progress_callback: Optional callback dla progress updates
            memory_check_func: Optional callback dla memory checks
            batch_size: Optional override default batch size
            
        Returns:
            Dict z statistics batch processing
        """
        if not items:
            return {"processed": 0, "errors": 0, "batches": 0}
        
        effective_batch_size = batch_size or self._determine_batch_size(len(items))
        self._total_count = len(items)
        self._processed_count = 0
        
        total_batches = (len(items) + effective_batch_size - 1) // effective_batch_size
        processed_items = 0
        error_count = 0
        
        self.logger.info(f"Starting batch processing: {len(items)} items in {total_batches} batches (size: {effective_batch_size})")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * effective_batch_size
            end_idx = min(start_idx + effective_batch_size, len(items))
            batch_items = items[start_idx:end_idx]
            
            # Memory check przed large batches
            if (memory_check_func and 
                len(batch_items) > self.config.memory_check_threshold):
                try:
                    memory_check_func()
                except Exception as e:
                    self.logger.warning(f"Memory check failed: {e}")
            
            # Process batch
            batch_processed, batch_errors = self._process_single_batch(
                batch_items, processor_func, start_idx
            )
            
            processed_items += batch_processed
            error_count += batch_errors
            self._processed_count = processed_items
            
            # Progress callback
            if progress_callback and batch_num % self.config.progress_update_interval == 0:
                try:
                    progress_callback(processed_items, self._total_count)
                except Exception as e:
                    self.logger.warning(f"Progress callback failed: {e}")
            
            # UI events processing dla responsywności
            if batch_num % self.config.ui_process_events_interval == 0:
                QApplication.instance().processEvents()
            
            self._batch_stats["batches_processed"] += 1
        
        self._batch_stats["items_processed"] += processed_items
        self._batch_stats["errors"] += error_count
        
        self.logger.info(f"Batch processing completed: {processed_items}/{len(items)} processed, {error_count} errors")
        
        return {
            "processed": processed_items,
            "errors": error_count,
            "batches": total_batches,
            "total_items": len(items)
        }
    
    def _determine_batch_size(self, total_items: int) -> int:
        """Determine optimal batch size based na total items count."""
        if total_items > 1000:
            return self.config.large_batch_size
        elif total_items > 100:
            return self.config.default_size
        else:
            return min(self.config.default_size, total_items)
    
    def _process_single_batch(self, batch_items: List[Any], processor_func: callable, start_idx: int) -> Tuple[int, int]:
        """Process pojedynczy batch i return (processed_count, error_count)."""
        processed = 0
        errors = 0
        
        for i, item in enumerate(batch_items):
            try:
                if processor_func(item, start_idx + i):
                    processed += 1
                else:
                    errors += 1
            except Exception as e:
                self.logger.warning(f"Error processing item {start_idx + i}: {e}")
                errors += 1
        
        return processed, errors
    
    def get_stats(self) -> Dict[str, int]:
        """Zwróć batch processing statistics."""
        stats = self._batch_stats.copy()
        stats["current_progress"] = self._processed_count
        stats["total_items"] = self._total_count
        return stats
```

---

### PATCH 3: EXTRACT VIRTUAL SCROLLING CONTROLLER

**Problem:** Virtual scrolling logic jest mixed z gallery management
**Rozwiązanie:** Standalone VirtualScrollingController z clean interface

```python
class VirtualScrollingController:
    """
    EXTRACTED: Standalone virtual scrolling controller.
    Separated z GalleryManager dla better testability i performance tuning.
    """
    
    def __init__(
        self, 
        scroll_area: ScrollAreaProtocol, 
        layout_manager: LayoutGeometryManager,
        enabled: bool = True,
        update_delay_ms: int = 50,
        throttle_ms: int = 16,
        debounce_ms: int = 100
    ):
        self.scroll_area = scroll_area
        self.layout_manager = layout_manager
        self._enabled = enabled
        
        # Timing configuration
        self._update_delay_ms = update_delay_ms
        self._throttle_ms = throttle_ms
        self._debounce_ms = debounce_ms
        
        # State tracking
        self._last_scroll_update = 0.0
        self._last_visible_range: Optional[VisibleRange] = None
        
        # Timers
        self._virtualization_timer = QTimer()
        self._virtualization_timer.setSingleShot(True)
        self._virtualization_timer.timeout.connect(self._on_virtualization_timer)
        
        self._scroll_timer = QTimer()
        self._scroll_timer.setSingleShot(True)
        
        # Callbacks
        self._visibility_change_callback: Optional[callable] = None
        self._scroll_update_callback: Optional[callable] = None
        
        # Performance tracking
        self._scroll_stats = {"updates": 0, "throttled": 0, "debounced": 0}
        
        self._setup_scroll_handling()
    
    def _setup_scroll_handling(self):
        """Setup throttled i debounced scroll event handling."""
        if self.scroll_area and hasattr(self.scroll_area, "verticalScrollBar"):
            self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll_throttled)
            self._scroll_timer.timeout.connect(self._on_scroll_debounced)
    
    def set_visibility_change_callback(self, callback: callable):
        """Set callback dla visibility changes (visible_range) -> None."""
        self._visibility_change_callback = callback
    
    def set_scroll_update_callback(self, callback: callable):
        """Set callback dla scroll updates (scroll_value) -> None.""" 
        self._scroll_update_callback = callback
    
    def _on_scroll_throttled(self, value: int):
        """Throttled scroll handler - called at max ~60 FPS."""
        if not self._enabled:
            return
            
        current_time = time.time() * 1000  # ms
        
        if current_time - self._last_scroll_update >= self._throttle_ms:
            self._last_scroll_update = current_time
            self._scroll_stats["updates"] += 1
            
            # Fast operations only - visibility updates
            self._update_visible_tiles_fast()
            
            # Schedule debounced heavy operations
            self._scroll_timer.stop()
            self._scroll_timer.start(self._debounce_ms)
            self._scroll_stats["throttled"] += 1
    
    def _on_scroll_debounced(self):
        """Debounced scroll handler dla heavy operations."""
        if not self._enabled:
            return
            
        self._scroll_stats["debounced"] += 1
        
        # Heavy operations - memory cleanup, etc.
        if self._scroll_update_callback:
            try:
                scroll_value = self.scroll_area.verticalScrollBar().value()
                self._scroll_update_callback(scroll_value)
            except Exception as e:
                logger.warning(f"Scroll update callback failed: {e}")
    
    def _update_visible_tiles_fast(self):
        """Fast visibility update - tylko calculation, bez heavy operations."""
        if not self._enabled:
            return
            
        # Start virtualization timer dla delayed update
        self._virtualization_timer.stop()
        self._virtualization_timer.start(self._update_delay_ms)
    
    def _on_virtualization_timer(self):
        """Timer callback dla delayed virtualization update."""
        if not self._enabled or not self._visibility_change_callback:
            return
            
        try:
            self._visibility_change_callback()
        except Exception as e:
            logger.warning(f"Virtualization callback failed: {e}")
    
    def update_visible_range(self, thumbnail_size: int, total_items: int) -> Optional[VisibleRange]:
        """Update visible range i return new range jeśli się zmieniło."""
        if not self._enabled:
            return None
            
        try:
            new_range = self.layout_manager.get_visible_range(thumbnail_size, total_items)
            
            # Check if range actually changed
            if (self._last_visible_range is None or 
                new_range.start_item != self._last_visible_range.start_item or
                new_range.end_item != self._last_visible_range.end_item):
                
                self._last_visible_range = new_range
                return new_range
                
            return None  # No change
            
        except Exception as e:
            logger.warning(f"Error updating visible range: {e}")
            return None
    
    def enable(self):
        """Enable virtual scrolling."""
        self._enabled = True
    
    def disable(self):
        """Disable virtual scrolling."""
        self._enabled = False
        self._virtualization_timer.stop()
        self._scroll_timer.stop()
    
    def force_update(self):
        """Wymusza immediate visibility update."""
        if self._enabled and self._visibility_change_callback:
            self._visibility_change_callback()
    
    def get_stats(self) -> Dict[str, Any]:
        """Zwróć virtual scrolling statistics."""
        stats = self._scroll_stats.copy()
        stats["enabled"] = self._enabled
        stats["last_visible_range"] = self._last_visible_range
        stats["timers_active"] = {
            "virtualization": self._virtualization_timer.isActive(),
            "scroll": self._scroll_timer.isActive(),
        }
        return stats
```

---

### PATCH 4: REFACTORED GALLERY MANAGER AS COORDINATOR

**Problem:** GalleryManager ma zbyt dużo odpowiedzialności - 958 linii
**Rozwiązanie:** Refactor jako coordinator używający extracted components

```python
class GalleryManager:
    """
    REFACTORED: Główny coordinator galerii używający extracted components.
    Reduced z 958 linii do ~200 linii przez separation of concerns.
    """
    
    def __init__(
        self,
        main_window,
        tiles_container: QWidget,
        tiles_layout: QGridLayout,
        scroll_area: QWidget,
        batch_config: Optional[BatchConfig] = None,
    ):
        self.main_window = main_window
        self.tiles_container = tiles_container
        self.tiles_layout = tiles_layout
        self.scroll_area = scroll_area
        
        # Extracted components - dependency injection
        self.layout_manager = LayoutGeometryManager(scroll_area, tiles_layout)
        self.virtual_scrolling = VirtualScrollingController(scroll_area, self.layout_manager)
        self.batch_processor = BatchProcessor(batch_config or BatchConfig(), logger)
        
        # Set up callbacks
        self.virtual_scrolling.set_visibility_change_callback(self._on_visibility_changed)
        self.virtual_scrolling.set_scroll_update_callback(self._on_scroll_updated)
        
        # Gallery state
        self.controller = GalleryController()
        self.gallery_tile_widgets: Dict[str, FileTileWidget] = {}
        self.special_folder_widgets: Dict[str, SpecialFolderTileWidget] = {}
        self.file_pairs_list: List[FilePair] = []
        self.special_folders_list: List[SpecialFolder] = []
        
        # Current size tracking
        self.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
        self._current_size_tuple = (self.current_thumbnail_size, self.current_thumbnail_size)
        
        # Thread safety dla core state
        self._widgets_lock = threading.RLock()
        self._state_lock = threading.RLock()
        
        # Resource management
        self._resource_manager = get_resource_manager()
        
        logger.info("GalleryManager initialized with extracted components")

    def create_tile_widget_for_pair(self, file_pair: FilePair, main_window) -> Optional[FileTileWidget]:
        """
        Tworzy pojedynczy tile widget dla file pair.
        SIMPLIFIED - używa extracted components dla better separation.
        """
        if not file_pair or not hasattr(file_pair, 'archive_path'):
            logger.warning("Invalid file_pair provided to create_tile_widget_for_pair")
            return None
        
        try:
            with self._widgets_lock:
                # Check if widget already exists
                if file_pair.archive_path in self.gallery_tile_widgets:
                    return self.gallery_tile_widgets[file_pair.archive_path]
                
                # Create new tile widget
                tile_widget = FileTileWidget(
                    file_pair, 
                    main_window, 
                    self._current_size_tuple
                )
                
                if tile_widget:
                    self.gallery_tile_widgets[file_pair.archive_path] = tile_widget
                    logger.debug(f"Created tile widget for {file_pair.archive_path}")
                
                return tile_widget
                
        except Exception as e:
            logger.error(f"Error creating tile widget for {file_pair.archive_path}: {e}")
            return None

    def force_create_all_tiles(self):
        """
        SIMPLIFIED: Wymusza tworzenie wszystkich kafelków używając BatchProcessor.
        Eliminuje hardcoded batch logic.
        """
        logger.info("Starting force_create_all_tiles with BatchProcessor")
        
        # Backup original resource limits
        original_max_tiles = self._resource_manager.limits.max_tiles
        
        try:
            # Temporarily increase limits
            self._resource_manager.limits.max_tiles = 10000
            
            # Clear existing tiles
            self.clear_gallery()
            self.tiles_container.setUpdatesEnabled(False)
            
            # Prepare all items dla batch processing
            all_items = self.special_folders_list + self.file_pairs_list
            
            if not all_items:
                logger.warning("No items to create tiles for")
                return
            
            # Use BatchProcessor dla unified processing
            def create_tile_processor(item, index: int) -> bool:
                """Processor function dla BatchProcessor."""
                return self._create_single_tile_item(item, index)
            
            def progress_callback(processed: int, total: int):
                """Progress callback dla UI updates."""
                if hasattr(self.main_window, 'progress_manager'):
                    try:
                        self.main_window.progress_manager.update_tile_creation_progress(processed)
                    except Exception as e:
                        logger.warning(f"Progress update failed: {e}")
            
            def memory_check():
                """Memory check callback."""
                # Could integrate z MemoryMonitor if needed
                pass
            
            # Process all items w batches
            results = self.batch_processor.process_items_in_batches(
                items=all_items,
                processor_func=create_tile_processor,
                progress_callback=progress_callback,
                memory_check_func=memory_check,
                batch_size=None  # Use automatic sizing
            )
            
            logger.info(f"Batch tile creation completed: {results}")
            
        except Exception as e:
            logger.error(f"Error in force_create_all_tiles: {e}")
            raise
        finally:
            # Restore original limits
            self._resource_manager.limits.max_tiles = original_max_tiles
            self.tiles_container.setUpdatesEnabled(True)

    def _create_single_tile_item(self, item, index: int) -> bool:
        """Create pojedynczy tile item - used by BatchProcessor."""
        try:
            layout_params = self.layout_manager.get_layout_params(self.current_thumbnail_size)
            row = index // layout_params.cols
            col = index % layout_params.cols
            
            if isinstance(item, SpecialFolder):
                widget = SpecialFolderTileWidget(item.folder_name, item.folder_path)
                if widget:
                    self.special_folder_widgets[item.folder_path] = widget
                    self.tiles_layout.addWidget(widget, row, col)
                    return True
                    
            elif isinstance(item, FilePair):
                widget = self.create_tile_widget_for_pair(item, self.main_window)
                if widget:
                    self.tiles_layout.addWidget(widget, row, col)
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error creating tile for item {index}: {e}")
            return False

    def _on_visibility_changed(self):
        """Callback z VirtualScrollingController gdy visibility range się zmienia."""
        if not self.virtual_scrolling._enabled:
            return
            
        try:
            visible_range = self.virtual_scrolling.update_visible_range(
                self.current_thumbnail_size, 
                len(self.file_pairs_list)
            )
            
            if visible_range:
                logger.debug(f"Visible range changed: {visible_range.start_item}-{visible_range.end_item}")
                # Here could implement actual virtual scrolling logic if needed
                
        except Exception as e:
            logger.warning(f"Error handling visibility change: {e}")

    def _on_scroll_updated(self, scroll_value: int):
        """Callback z VirtualScrollingController dla scroll updates."""
        # Handle heavy scroll operations here
        pass

    def update_thumbnail_size(self, new_size: int):
        """
        SIMPLIFIED: Aktualizuje rozmiar thumbnails używając extracted components.
        """
        with self._state_lock:
            if new_size == self.current_thumbnail_size:
                return
                
            self.current_thumbnail_size = new_size
            self._current_size_tuple = (new_size, new_size)
            
            # Invalidate layout cache
            self.layout_manager.invalidate_cache()
            
            # Update wszystkich existing widgets
            with self._widgets_lock:
                for widget in self.gallery_tile_widgets.values():
                    try:
                        if hasattr(widget, 'update_thumbnail_size'):
                            widget.update_thumbnail_size(self._current_size_tuple)
                    except Exception as e:
                        logger.warning(f"Error updating widget thumbnail size: {e}")
            
            # Force virtual scrolling update
            self.virtual_scrolling.force_update()
            
            logger.info(f"Updated thumbnail size to {new_size}px")

    def get_all_tile_widgets(self) -> List[FileTileWidget]:
        """Thread-safe zwracanie wszystkich tile widgets."""
        with self._widgets_lock:
            return list(self.gallery_tile_widgets.values())

    def clear_gallery(self):
        """SIMPLIFIED: Czyści galerię używając proper cleanup."""
        with self._widgets_lock:
            # Clear widgets safely
            for widget in list(self.gallery_tile_widgets.values()):
                if hasattr(widget, 'cleanup'):
                    widget.cleanup()
                elif hasattr(widget, 'deleteLater'):
                    widget.deleteLater()
            
            for widget in list(self.special_folder_widgets.values()):
                if hasattr(widget, 'cleanup'):
                    widget.cleanup()
                elif hasattr(widget, 'deleteLater'):
                    widget.deleteLater()
            
            self.gallery_tile_widgets.clear()
            self.special_folder_widgets.clear()
            
            # Clear layout
            while self.tiles_layout.count() > 0:
                item = self.tiles_layout.takeAt(0)
                if item and item.widget():
                    item.widget().setParent(None)
        
        # Invalidate all caches
        self.layout_manager.invalidate_cache()
        
        logger.info("Gallery cleared")

    def get_performance_stats(self) -> Dict[str, Any]:
        """Comprehensive performance statistics z all components."""
        return {
            "layout_cache": self.layout_manager.get_cache_stats(),
            "virtual_scrolling": self.virtual_scrolling.get_stats(),
            "batch_processor": self.batch_processor.get_stats(),
            "widgets": {
                "file_tiles": len(self.gallery_tile_widgets),
                "special_folders": len(self.special_folder_widgets),
                "total_items": len(self.file_pairs_list) + len(self.special_folders_list),
            },
            "current_thumbnail_size": self.current_thumbnail_size,
        }

    # Maintain backward compatibility methods
    def _get_cached_geometry(self) -> Dict[str, Any]:
        """Backward compatibility wrapper."""
        params = self.layout_manager.get_layout_params(self.current_thumbnail_size)
        return {
            "container_width": params.container_width,
            "cols": params.cols,
            "tile_width_spacing": params.tile_width_spacing,
            "tile_height_spacing": params.tile_height_spacing,
        }
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - czy galeria nadal tworzy i wyświetla kafle poprawnie.
- [ ] **API kompatybilność** - czy wszystkie publiczne metody działają jak wcześniej.  
- [ ] **Obsługa błędów** - czy extracted components mają proper error handling.
- [ ] **Walidacja danych** - czy LayoutGeometryManager właściwie waliduje parameters.
- [ ] **Logowanie** - czy system logowania działania bez spamowania i zawiera metrics.
- [ ] **Konfiguracja** - czy BatchConfig i extracted components są konfigurowalne.
- [ ] **Cache** - czy LayoutGeometryManager cache ma proper size limits.
- [ ] **Thread safety** - czy wszystkie extracted components są thread-safe.
- [ ] **Memory management** - czy VirtualScrollingController nie powoduje memory leaks.
- [ ] **Performance** - czy decomposition nie pogorszyła wydajności galerii.

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - czy wszystkie nowe imports (dataclasses, protocols) działają.
- [ ] **Zależności zewnętrzne** - czy PyQt6 integration nadal działa poprawnie.
- [ ] **Zależności wewnętrzne** - czy tile_manager integration z refactored GalleryManager działa.
- [ ] **Cykl zależności** - czy extracted components nie wprowadzają circular dependencies.
- [ ] **Backward compatibility** - czy main_window kod nadal działa z refactored API.
- [ ] **Interface contracts** - czy Protocol interfaces są poprawnie implemented.
- [ ] **Event handling** - czy scroll events i callbacks działają poprawnie.
- [ ] **Signal/slot connections** - czy Qt connections nadal działają.
- [ ] **Resource integration** - czy tile_resource_manager integration działa.

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - czy wszystkie extracted components działają w izolacji.
- [ ] **Test integracyjny** - czy GalleryManager coordinator działa z all components.
- [ ] **Test regresyjny** - czy nie wprowadzono regresji w gallery functionality.
- [ ] **Test wydajnościowy** - czy virtual scrolling i batch processing są wydajne.
- [ ] **Test thread safety** - czy concurrent operations są bezpieczne.
- [ ] **Test memory management** - czy brak memory leaks przy długotrwałym użytkowaniu.

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem.
- [ ] **BRAK FAILED TESTS** - wszystkie testy muszą przejść.
- [ ] **PERFORMANCE BUDGET** - wydajność virtual scrolling nie pogorszona.
- [ ] **CODE COVERAGE** - pokrycie kodu nie spadło poniżej 80%.
- [ ] **FILE SIZE REDUCTION** - main GalleryManager < 300 linii po decomposition.
- [ ] **SEPARATION VERIFIED** - każdy extracted component ma single responsibility.