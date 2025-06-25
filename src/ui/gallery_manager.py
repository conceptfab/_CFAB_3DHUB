"""
Manager galerii - zarządzanie wyświetlaniem kafelków.
"""

import concurrent.futures
import logging
import math
import os
import threading
import time
import weakref
from collections import namedtuple
from typing import Any, Dict, List, Optional, Set, Tuple

try:
    import psutil
except ImportError:
    psutil = None

from PyQt6.QtCore import QMutex, QMutexLocker, QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QGridLayout, QSizePolicy, QWidget

from src import app_config
from src.controllers.gallery_controller import GalleryController
from src.models.file_pair import FilePair
from src.models.special_folder import SpecialFolder
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.ui.widgets.special_folder_tile_widget import SpecialFolderTileWidget
from src.ui.widgets.tile_resource_manager import get_resource_manager

logger = logging.getLogger(__name__)


# Cache entry structure dla optimized cache
CacheEntry = namedtuple("CacheEntry", ["data", "timestamp", "version"])


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
        """Configure settings based na system performance z enhanced adaptive logic."""
        try:
            if psutil:
                # Get system specs
                cpu_count = psutil.cpu_count(logical=True)
                memory_gb = psutil.virtual_memory().total / (1024**3)

                # ADAPTIVE CHUNK SIZING z performance considerations dla 128GB systemu
                if memory_gb >= 64 and cpu_count >= 12:
                    # Ultra high-end system (128GB+ RAM)
                    self.chunk_size = 200  # Większe chunki dla powerful systems
                    self.process_events_interval = 5
                    self.yield_time = 0.0005  # Krótsze yielding
                elif memory_gb >= 16 and cpu_count >= 8:
                    # High-end system
                    self.chunk_size = 150
                    self.process_events_interval = 3
                    self.yield_time = 0.001
                elif memory_gb >= 8 and cpu_count >= 4:
                    # Mid-range system
                    self.chunk_size = 100
                    self.process_events_interval = 2
                    self.yield_time = 0.001
                else:
                    # Low-end system
                    self.chunk_size = 50
                    self.process_events_interval = 1
                    self.yield_time = 0.002

                logger.info(f"Adaptive settings: chunk_size={self.chunk_size}, "
                          f"memory={memory_gb:.1f}GB, cpus={cpu_count}")
            else:
                # Fallback gdy psutil nie dostępne
                self.chunk_size = 75
                self.process_events_interval = 2
                self.yield_time = 0.001

        except Exception:
            # Fallback values
            self.chunk_size = 75
            self.process_events_interval = 2
            self.yield_time = 0.001

    def create_tiles_progressive(self, special_folders: list, file_pairs: list):
        """Start progressive tile creation z enhanced performance monitoring."""
        with QMutexLocker(self._mutex):
            self._cancel_requested = False

        try:
            all_items = special_folders + file_pairs
            total_items = len(all_items)

            if total_items == 0:
                self.creation_finished.emit(True, "No items to create")
                return

            # ADAPTIVE CHUNK SIZING based na dataset size i system performance
            if total_items > 2000:
                # Very large dataset - smaller chunks dla better responsiveness
                adjusted_chunk_size = max(25, self.chunk_size // 2)
            elif total_items > 1000:
                # Large dataset - moderate chunks
                adjusted_chunk_size = max(50, int(self.chunk_size * 0.8))
            else:
                # Normal dataset - standard chunks
                adjusted_chunk_size = self.chunk_size

            logger.info(f"Progressive creation: {total_items} items, chunk_size={adjusted_chunk_size}")

            # Calculate chunks
            chunks = []
            for i in range(0, total_items, adjusted_chunk_size):
                chunk_items = all_items[i : i + adjusted_chunk_size]
                chunks.append((i // adjusted_chunk_size, chunk_items, i))

            # PERFORMANCE MONITORING
            start_time = time.time()
            last_yield_time = start_time

            # Process chunks progressively z enhanced monitoring
            for chunk_id, chunk_items, start_index in chunks:

                # Check for cancellation
                with QMutexLocker(self._mutex):
                    if self._cancel_requested:
                        self.creation_finished.emit(
                            False, "Operation cancelled by user"
                        )
                        return

                # Update progress z better messaging
                progress_text = f"Creating tiles {start_index + 1}-{start_index + len(chunk_items)} of {total_items}"
                self.progress_updated.emit(start_index, total_items, progress_text)

                # Create chunk widgets
                chunk_start_time = time.time()
                chunk_widgets = self._create_chunk_widgets(chunk_items, start_index)
                chunk_time = time.time() - chunk_start_time

                # Emit chunk completion
                self.chunk_completed.emit(chunk_id, chunk_widgets)

                # ADAPTIVE YIELDING based na performance
                current_time = time.time()
                
                # Yield more frequently if chunks are taking too long
                if chunk_time > 0.1:  # 100ms threshold
                    # Longer yield for slow chunks
                    time.sleep(self.yield_time * 2)
                    QApplication.processEvents()
                elif (current_time - last_yield_time) > 0.2:  # 200ms since last yield
                    # Regular yield
                    time.sleep(self.yield_time)
                    QApplication.processEvents()
                    last_yield_time = current_time
                elif chunk_id % self.process_events_interval == 0:
                    # Minimal yield
                    QApplication.processEvents()

            total_time = time.time() - start_time
            tiles_per_second = total_items / total_time if total_time > 0 else 0
            logger.info(f"Progressive creation completed: {total_items} tiles in {total_time:.2f}s "
                       f"({tiles_per_second:.1f} tiles/s)")

            self.creation_finished.emit(True, f"Successfully created {total_items} tiles")

        except Exception as e:
            logger.error(f"Error during progressive tile creation: {str(e)}")
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
                absolute_index = start_index + i

                if hasattr(item, "get_folder_path"):  # SpecialFolder
                    widget = self.gallery_manager.create_folder_widget(item)
                    if widget:
                        # Dodaj numerację dla folderów specjalnych
                        total_folders = len(self.gallery_manager.special_folders_list)
                        tooltip = (
                            f"[{absolute_index + 1}/{total_folders}] {item.folder_name}"
                        )
                        widget.setToolTip(tooltip)
                        widget.setObjectName(f"SpecialFolderTile_{absolute_index + 1}")
                else:  # FilePair
                    widget = self.gallery_manager.create_tile_widget_for_pair(
                        item, self.gallery_manager.tiles_container
                    )
                    if widget:
                        # KRYTYCZNE: Dodaj numerację kafelków jak w oryginalnej wersji
                        total_pairs = len(self.gallery_manager.file_pairs_list)
                        file_pair_number = (
                            absolute_index
                            - len(self.gallery_manager.special_folders_list)
                            + 1
                        )

                        if hasattr(widget, "set_tile_number"):
                            widget.set_tile_number(file_pair_number, total_pairs)
                        widget.setObjectName(f"FileTile_{file_pair_number}")

                if widget:
                    widgets.append((absolute_index, widget, item))

            except Exception as e:
                logging.error(f"Failed to create widget for item {i}: {e}")
                continue

        return widgets

    def cancel_creation(self):
        """Cancel ongoing tile creation."""
        with QMutexLocker(self._mutex):
            self._cancel_requested = True


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
        self._last_processed_scroll_ms = 0

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
        if (
            current_time_ms - self._last_processed_scroll_ms
        ) >= self._current_throttle_ms:
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
        if (
            current_time - self._last_performance_check
            > self._performance_check_interval
        ):
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

        logging.debug(
            f"Performance level: {self._performance_level} (Est. FPS: {fps_estimate:.1f})"
        )


class LayoutGeometry:
    """Thread-safe klasa pomocnicza do obliczeń geometrii layoutu."""

    def __init__(self, scroll_area, tiles_layout):
        self.scroll_area = scroll_area
        self.tiles_layout = tiles_layout

        # Thread-safe cache z timestamps
        self._cache: Dict[Tuple, Dict[str, Any]] = {}
        self._cache_lock = threading.RLock()
        self._cache_timestamps: Dict[Tuple, float] = {}
        self._cache_ttl = 5.0  # Cache TTL w sekundach

        # Cache statistics dla monitoring
        self._cache_stats = {"hits": 0, "misses": 0, "invalidations": 0}

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
            if (
                cache_key in self._cache
                and cache_key in self._cache_timestamps
                and current_time - self._cache_timestamps[cache_key] < self._cache_ttl
            ):

                self._cache_stats["hits"] += 1
                # Return copy dla thread safety
                return self._cache[cache_key].copy()

            # Cache miss or expired - calculate new params
            self._cache_stats["misses"] += 1

            container_width = (
                self.scroll_area.width() - self.scroll_area.verticalScrollBar().width()
            )
            tile_width_spacing = thumbnail_size + self.tiles_layout.spacing() + 10
            # Używamy y + x dla spójności z nowym algorytmem wysokości
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

            # Store w cache z timestamp
            self._cache[cache_key] = params
            self._cache_timestamps[cache_key] = current_time

            # Cleanup expired cache entries
            self._cleanup_expired_cache(current_time)

            return params.copy()

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
            return stats

    def get_visible_range(
        self, thumbnail_size: int, total_items: int
    ) -> Tuple[int, int, Dict[str, Any]]:
        """Thread-safe obliczanie zakresu widocznych elementów z buffering."""
        params = self.get_layout_params(thumbnail_size)

        viewport_height = self.scroll_area.viewport().height()
        scroll_y = self.scroll_area.verticalScrollBar().value()

        # Intelligent buffering based on scroll speed
        base_buffer = viewport_height
        buffer = base_buffer

        visible_start_y = max(0, scroll_y - buffer)
        visible_end_y = scroll_y + viewport_height + buffer

        first_visible_row = max(
            0, math.floor(visible_start_y / params["tile_height_spacing"])
        )
        last_visible_row = math.ceil(visible_end_y / params["tile_height_spacing"])

        first_visible_item = first_visible_row * params["cols"]
        last_visible_item = min((last_visible_row + 1) * params["cols"], total_items)

        return first_visible_item, last_visible_item, params


class OptimizedLayoutGeometry:
    """
    DEPRECATED - Usunięte w ramach simplification cache strategy.
    Functionality przeniesiona do LayoutGeometry.
    """
    def __init__(self, scroll_area, tiles_layout):
        # Redirect do unified LayoutGeometry
        self._geometry = LayoutGeometry(scroll_area, tiles_layout)
        logger.warning("OptimizedLayoutGeometry is deprecated, use LayoutGeometry directly")
    
    def get_layout_params(self, thumbnail_size: int) -> dict:
        """Redirect do LayoutGeometry dla backward compatibility."""
        return self._geometry.get_layout_params(thumbnail_size)
    
    def invalidate_cache(self):
        """Redirect do LayoutGeometry dla backward compatibility."""
        return self._geometry.invalidate_cache()
    
    def get_cache_stats(self) -> dict:
        """Redirect do LayoutGeometry dla backward compatibility."""
        return self._geometry.get_cache_stats()


class VirtualScrollingMemoryManager:
    """Memory management dla virtual scrolling kafli z SELECTIVE VIRTUALIZATION."""

    def __init__(self, gallery_manager):
        self.gallery_manager = gallery_manager

        # Widget tracking
        self.active_widgets: Dict[int, weakref.ref] = {}
        self.disposed_widgets: Set[int] = set()

        # ENHANCED MEMORY THRESHOLDS dla 128GB systemu
        try:
            if psutil:
                memory_gb = psutil.virtual_memory().total / (1024**3)
                if memory_gb >= 64:
                    # Ultra high-end system - wyższe limity
                    self.max_active_widgets = 5000
                    self.cleanup_threshold = 4000
                elif memory_gb >= 16:
                    # High-end system
                    self.max_active_widgets = 2000  
                    self.cleanup_threshold = 1500
                else:
                    # Low-end system
                    self.max_active_widgets = 1000
                    self.cleanup_threshold = 800
            else:
                self.max_active_widgets = 1500
                self.cleanup_threshold = 1000
        except:
            self.max_active_widgets = 1500
            self.cleanup_threshold = 1000

        # SELECTIVE VIRTUALIZATION THRESHOLD - WYŻSZY dla 128GB systemu
        try:
            if psutil:
                memory_gb = psutil.virtual_memory().total / (1024**3)
                if memory_gb >= 64:
                    # Ultra high-end system - bardzo wysoki threshold żeby nie włączać niepotrzebnie
                    self.virtualization_threshold = 10000  # Enable tylko dla >10000 tiles
                else:
                    self.virtualization_threshold = 2000  # Enable tylko dla >2000 tiles
            else:
                self.virtualization_threshold = 2000
        except:
            self.virtualization_threshold = 2000

        # Statistics
        self.stats = {"widgets_created": 0, "widgets_disposed": 0, "memory_cleanups": 0}

        logger.info(f"VirtualScrollingMemoryManager: max_widgets={self.max_active_widgets}, "
                   f"cleanup_threshold={self.cleanup_threshold}")

    def should_enable_virtualization(self, total_items: int) -> bool:
        """Determine if virtualization should be enabled based na dataset size."""
        return total_items > self.virtualization_threshold

    def register_widget(self, index: int, widget):
        """Register widget dla tracking z INTELLIGENT CLEANUP."""
        if widget:
            self.active_widgets[index] = weakref.ref(
                widget, lambda ref: self._on_widget_destroyed(index)
            )
            self.stats["widgets_created"] += 1

            # MEMORY PRESSURE DETECTION
            if len(self.active_widgets) > self.cleanup_threshold:
                # Check if virtualization should be active
                total_items = len(self.gallery_manager.file_pairs_list) + len(self.gallery_manager.special_folders_list)
                
                if self.should_enable_virtualization(total_items):
                    self._trigger_memory_cleanup()
                    self.gallery_manager._virtualization_enabled = True
                    logger.debug(f"Virtualization enabled: {total_items} items, {len(self.active_widgets)} widgets")

    def _on_widget_destroyed(self, index: int):
        """Callback gdy widget został zniszczony."""
        self.active_widgets.pop(index, None)
        self.disposed_widgets.add(index)

    def _trigger_memory_cleanup(self):
        """Trigger memory cleanup when threshold reached z ENHANCED ALGORITHM."""
        if not self.gallery_manager._virtualization_enabled:
            return

        # Get visible range
        if (
            hasattr(self.gallery_manager, "file_pairs_list")
            and self.gallery_manager.file_pairs_list
        ):
            total_items = len(self.gallery_manager.file_pairs_list) + len(self.gallery_manager.special_folders_list)
            
            try:
                visible_start, visible_end, _ = (
                    self.gallery_manager._geometry.get_visible_range(
                        self.gallery_manager._current_size_tuple[0], total_items
                    )
                )

                # BUFFER ZONE dla smooth scrolling
                buffer_size = min(50, (visible_end - visible_start) // 2)
                safe_start = max(0, visible_start - buffer_size)
                safe_end = min(total_items, visible_end + buffer_size)

                # Dispose widgets outside safe range
                disposed_count = 0
                for index in list(self.active_widgets.keys()):
                    if index < safe_start or index >= safe_end:
                        if self._dispose_widget_at_index(index):
                            disposed_count += 1

                self.stats["memory_cleanups"] += 1
                self.stats["widgets_disposed"] += disposed_count
                
                logger.debug(f"Memory cleanup: disposed {disposed_count} widgets, "
                           f"active: {len(self.active_widgets)}")

            except Exception as e:
                logger.error(f"Error during memory cleanup: {e}")

    def _dispose_widget_at_index(self, index: int) -> bool:
        """Dispose widget at specific index z SAFE CLEANUP."""
        widget_ref = self.active_widgets.get(index)
        if widget_ref:
            widget = widget_ref()
            if widget:
                try:
                    # Remove z layout
                    if hasattr(self.gallery_manager, "tiles_layout"):
                        self.gallery_manager.tiles_layout.removeWidget(widget)

                    # SAFE CLEANUP
                    widget.setVisible(False)
                    widget.setParent(None)
                    
                    if hasattr(widget, "cleanup"):
                        widget.cleanup()
                    
                    widget.deleteLater()

                    # Remove z tracking
                    self.active_widgets.pop(index, None)
                    self.disposed_widgets.add(index)
                    return True
                except Exception as e:
                    logger.error(f"Error disposing widget at index {index}: {e}")
        return False

    def get_memory_stats(self) -> Dict[str, int]:
        """Get comprehensive memory management statistics."""
        stats = self.stats.copy()
        stats["active_widgets"] = len(self.active_widgets)
        stats["disposed_count"] = len(self.disposed_widgets)
        stats["max_active_widgets"] = self.max_active_widgets
        stats["cleanup_threshold"] = self.cleanup_threshold
        stats["virtualization_threshold"] = self.virtualization_threshold
        return stats


class GalleryManager:
    """
    Klasa zarządzająca galerią kafelków z thread safety.
    """

    VIRTUALIZATION_UPDATE_DELAY = 50  # ms, opóźnienie dla aktualizacji wirtualizacji

    def __init__(
        self,
        main_window,
        tiles_container: QWidget,
        tiles_layout: QGridLayout,
        scroll_area: QWidget,
    ):
        self.main_window = main_window
        self.tiles_container = tiles_container
        self.tiles_layout = tiles_layout
        self.scroll_area = scroll_area
        self.controller = GalleryController()
        self.gallery_tile_widgets: Dict[str, FileTileWidget] = {}
        self.special_folder_widgets: Dict[str, SpecialFolderTileWidget] = {}
        self.file_pairs_list: List[FilePair] = []
        self.special_folders_list: List[SpecialFolder] = []
        # Inicjalizuj current_thumbnail_size jako int, zgodnie z app_config
        self.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
        # Zapisz krotkę rozmiaru dla spójności interfejsu
        self._current_size_tuple = (
            self.current_thumbnail_size,
            self.current_thumbnail_size,
        )

        # Thread safety
        self._widgets_lock = threading.RLock()
        self._geometry_cache_lock = threading.Lock()

        # Cache dla obliczeń geometrii
        self._geometry_cache = {
            "container_width": 0,
            "cols": 0,
            "tile_width_spacing": 0,
            "tile_height_spacing": 0,
            "last_thumbnail_size": 0,
        }

        # Flaga dla pending size update
        self._pending_size_update = False

        # UNIFIED CACHE STRATEGY - tylko LayoutGeometry
        self._geometry = LayoutGeometry(self.scroll_area, self.tiles_layout)

        # ENHANCED MEMORY MANAGEMENT
        self.memory_manager = VirtualScrollingMemoryManager(self)

        # VIRTUALIZATION CONTROL z selective enabling
        self._virtualization_enabled = False  # Disabled by default
        
        # PROGRESSIVE TILE CREATION
        self._progressive_creator = ProgressiveTileCreator(self)
        self._tile_creation_in_progress = False
        
        # Setup progressive tile creation signals
        self._progressive_creator.progress_updated.connect(self._on_tile_creation_progress)
        self._progressive_creator.chunk_completed.connect(self._on_chunk_completed)
        self._progressive_creator.creation_finished.connect(self._on_tile_creation_finished)

        # ADAPTIVE SCROLL HANDLING
        self.scroll_handler = AdaptiveScrollHandler(self)

        # Timer do opóźnionej aktualizacji wirtualizacji
        self._virtualization_timer = QTimer()
        self._virtualization_timer.setSingleShot(True)
        self._virtualization_timer.timeout.connect(self._update_visible_tiles)

        # Throttling scroll events
        self._scroll_timer = None
        self._last_scroll_update = 0
        self._scroll_throttle_ms = 16  # ~60 FPS limit
        self._scroll_debounce_ms = 100  # 100ms debounce dla heavy operations

        # Progressive loading support
        self._loading_lock = threading.RLock()
        self._loading_chunks_queue = []
        self._progressive_loading = False

        if hasattr(self.scroll_area, "verticalScrollBar"):
            # Replace old scroll handler with throttled version
            self.scroll_area.verticalScrollBar().valueChanged.connect(
                self._on_scroll_throttled
            )
            self._setup_scroll_throttling()

    def _setup_scroll_throttling(self):
        """Setup throttled scroll event handling."""
        if self.scroll_area and hasattr(self.scroll_area, "verticalScrollBar"):
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
        # Wyłączono żeby kafle nie znikały
        return

    def _update_geometry_cache_if_needed(self):
        """Update geometry cache jeśli window size się zmienił."""
        if hasattr(self, "_geometry"):
            # Check czy trzeba invalidate cache
            current_size = (self.scroll_area.width(), self.scroll_area.height())
            if (
                not hasattr(self, "_last_window_size")
                or self._last_window_size != current_size
            ):
                self._geometry.invalidate_cache()
                self._last_window_size = current_size

    def _cleanup_hidden_tiles(self):
        """Cleanup tiles które są poza visible range (called by throttled scroll)."""
        if not self._virtualization_enabled:
            return

        # Delegate do memory manager
        if hasattr(self, "memory_manager"):
            self.memory_manager._trigger_memory_cleanup()

    def _trigger_progressive_loading_if_needed(self):
        """Trigger progressive loading jeśli są pending chunks."""
        with self._loading_lock:
            if self._loading_chunks_queue and not self._progressive_loading:
                self._start_progressive_loading()

    def _start_progressive_loading(self):
        """Start progressive loading - placeholder for now."""

    def _on_tile_creation_progress(self, current: int, total: int, status: str):
        """Handle progress updates dla tile creation."""
        progress_percent = (current * 100) // total if total > 0 else 0
        logging.info(f"Tile creation progress: {progress_percent}% - {status}")

    def _on_chunk_completed(self, chunk_id: int, chunk_widgets: list):
        """Handle completion pojedynczego chunk."""
        geometry = self._get_cached_geometry()
        cols = geometry["cols"]

        logger.debug(f"📦 Processing chunk {chunk_id}: {len(chunk_widgets)} widgets, layout cols: {cols}")
        
        widgets_added = 0
        for tile_index, widget, item in chunk_widgets:
            if widget:
                self._setup_widget_connections(widget, item)

                row = tile_index // cols
                col = tile_index % cols
                self.tiles_layout.addWidget(widget, row, col)
                widget.setVisible(True)
                widget.show()
                widgets_added += 1

        # --- DEBUG: Sprawdź ile kafelków jest widocznych po chunku ---
        visible_tiles = len([w for w in self.gallery_tile_widgets.values() if w.isVisible()])
        folder_visible = len([w for w in self.special_folder_widgets.values() if w.isVisible()])
        total_widgets = len(self.gallery_tile_widgets) + len(self.special_folder_widgets)
        logger.info(f"🔍 DEBUG CHUNK {chunk_id}: Visible tiles: {visible_tiles}, folders: {folder_visible}, total: {total_widgets}")

        # --- EMERGENCY FIX: Jeśli mniej niż 10 widocznych, wymuś widoczność na wszystkich ---
        if total_widgets > 0 and (visible_tiles + folder_visible) < 10:
            logger.warning(f"⚠️ EMERGENCY CHUNK {chunk_id}: Only {visible_tiles + folder_visible} visible, forcing visibility!")
            for w in self.gallery_tile_widgets.values():
                w.setVisible(True)
                w.show()
            for w in self.special_folder_widgets.values():
                w.setVisible(True)
                w.show()
            self.tiles_container.update()

    def _on_tile_creation_finished(self, success: bool, message: str):
        """Obsługuje zakończenie progresywnego tworzenia kafelków."""
        logger.info(f"Tile creation finished: {success}, message: {message}")
        # --- WYMUSZ PRZELICZENIE WYSOKOŚCI KONTENERA I RELAYOUT ---
        try:
            all_items = self.special_folders_list + self.file_pairs_list
            geometry = self._get_cached_geometry()
            cols = geometry["cols"]
            n = len(all_items)
            k = cols
            y = self.current_thumbnail_size
            x = self.tiles_layout.spacing()
            logger.info(f"Tiles layout spacing: {x}")
            z = math.ceil(n / k)
            total_height = z * (y + x)
            total_height += y
            logger.info(f"📐 [PROGRESSIVE] Layout calculation: items={n}, cols={k}, rows={z}, tile_size={y}, spacing={x}")
            logger.info(f"📐 [PROGRESSIVE] Container height: {total_height}px, current container size: {self.tiles_container.size()}")
            self.tiles_container.setMinimumHeight(total_height)
            self.tiles_container.setMaximumHeight(total_height)
            from PyQt6.QtWidgets import QSizePolicy
            self.tiles_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            self.tiles_container.adjustSize()
            logger.info(f"📐 [PROGRESSIVE] After adjustSize: container size: {self.tiles_container.size()}")
            self.tiles_container.updateGeometry()
            self.scroll_area.updateGeometry()
            if hasattr(self.scroll_area, "verticalScrollBar"):
                self.scroll_area.verticalScrollBar().setValue(0)
                logger.info(f"📐 [PROGRESSIVE] Scroll reset to top, scrollbar range: 0-{self.scroll_area.verticalScrollBar().maximum()}")
        except Exception as e:
            logger.error(f"[PROGRESSIVE] Error in relayout: {e}")
        # --- KONIEC WYMUSZENIA ---
        # Reszta istniejącej logiki:
        if hasattr(self, "main_window") and hasattr(self.main_window, "progress_manager"):
            self.main_window.progress_manager.finish_tile_creation()
        self.tiles_container.setUpdatesEnabled(True)
        self.tiles_container.update()

    def _setup_widget_connections(self, widget, item):
        """Setup signal connections dla widget."""
        if hasattr(widget, "archive_open_requested"):
            widget.archive_open_requested.connect(self.main_window.open_archive)
        if hasattr(widget, "preview_image_requested"):
            widget.preview_image_requested.connect(
                self.main_window._show_preview_dialog
            )
        if hasattr(widget, "tile_selected"):
            widget.tile_selected.connect(
                self.main_window._handle_tile_selection_changed
            )
        # KRYTYCZNE: Dodaj sygnały metadanych jak w oryginalnej wersji
        if hasattr(widget, "stars_changed"):
            widget.stars_changed.connect(self.main_window._handle_stars_changed)
        if hasattr(widget, "color_tag_changed"):
            widget.color_tag_changed.connect(self.main_window._handle_color_tag_changed)
        if hasattr(widget, "tile_context_menu_requested"):
            widget.tile_context_menu_requested.connect(
                self.main_window._show_file_context_menu
            )

    def _finalize_gallery_layout(self):
        """Finalize gallery layout po tile creation."""
        all_items = len(self.special_folders_list) + len(self.file_pairs_list)
        geometry = self._get_cached_geometry()
        cols = geometry["cols"]

        if all_items > 0:
            rows = math.ceil(all_items / cols)
            total_height = rows * (
                self.current_thumbnail_size + self.tiles_layout.spacing() + 40
            )

            self.tiles_container.setMinimumHeight(total_height)
            self.tiles_container.adjustSize()
            self.tiles_container.updateGeometry()

    def _process_scroll_optimized(self, scroll_value: int):
        """Optimized scroll processing method."""
        if self._virtualization_enabled:
            self._update_visible_tiles_fast()

        if self._scroll_timer:
            self._scroll_timer.stop()
            self._scroll_timer.start(100)
        pass

    def _get_cached_geometry(self):
        """Zwraca cache'owane obliczenia geometrii lub oblicza nowe."""
        with self._geometry_cache_lock:
            container_width = (
                self.scroll_area.width() - self.scroll_area.verticalScrollBar().width()
            )

            # Sprawdź czy cache jest aktualny
            if (
                self._geometry_cache["container_width"] == container_width
                and self._geometry_cache["last_thumbnail_size"]
                == self.current_thumbnail_size
            ):
                return self._geometry_cache

            # Oblicz nowe wartości
            tile_width_spacing = (
                self.current_thumbnail_size + self.tiles_layout.spacing() + 10
            )
            tile_height_spacing = (
                self.current_thumbnail_size + self.tiles_layout.spacing() + 40
            )
            cols = max(1, math.ceil(container_width / tile_width_spacing))

            # Zaktualizuj cache
            self._geometry_cache.update(
                {
                    "container_width": container_width,
                    "cols": cols,
                    "tile_width_spacing": tile_width_spacing,
                    "tile_height_spacing": tile_height_spacing,
                    "last_thumbnail_size": self.current_thumbnail_size,
                }
            )

            return self._geometry_cache

    def _on_scroll(self, value):
        """Wywołuje opóźnioną aktualizację widocznych kafelków."""
        self._virtualization_timer.start(self.VIRTUALIZATION_UPDATE_DELAY)

    def clear_gallery(self):
        """
        Czyści galerię kafelków z OPTIMIZED BATCH DELETION i progress indication.
        """
        try:
            # Get total widget count dla progress
            total_widgets = len(self.gallery_tile_widgets) + len(self.special_folder_widgets)
            
            if total_widgets == 0:
                return
                
            logger.info(f"Clearing gallery: {total_widgets} widgets")
            
            self.tiles_container.setUpdatesEnabled(False)
            
            # BATCH LAYOUT CLEARING - szybsze niż pojedyncze takeAt()
            layout_items = []
            while self.tiles_layout.count():
                item = self.tiles_layout.takeAt(0)
                if item.widget():
                    layout_items.append(item.widget())
            
            # Batch visibility hiding
            for widget in layout_items:
                widget.setVisible(False)

            # Thread-safe czyszczenie słowników z BATCH PROCESSING
            with self._widgets_lock:
                # BATCH DELETION dla tile widgets
                tiles_to_delete = list(self.gallery_tile_widgets.values())
                self.gallery_tile_widgets.clear()
                
                # BATCH DELETION dla folder widgets  
                folders_to_delete = list(self.special_folder_widgets.values())
                self.special_folder_widgets.clear()

            # OPTIMIZED CLEANUP - deleteLater w batch'ach z yielding
            all_widgets = tiles_to_delete + folders_to_delete
            batch_size = 50  # Delete w batch'ach po 50
            
            for i in range(0, len(all_widgets), batch_size):
                batch = all_widgets[i:i + batch_size]
                
                for widget in batch:
                    widget.setParent(None)
                    widget.deleteLater()
                
                # Progress indication dla large galleries
                if total_widgets > 200:
                    progress = min(100, int((i + len(batch)) / len(all_widgets) * 100))
                    logger.debug(f"Gallery cleanup progress: {progress}%")
                
                # Yield co batch dla UI responsiveness
                if i % (batch_size * 2) == 0:  # Co 100 widgets
                    QApplication.processEvents()
                    time.sleep(0.001)  # 1ms yield

            logger.info(f"Gallery cleared: {total_widgets} widgets deleted")
            
        except Exception as e:
            logger.error(f"Error during gallery clearing: {e}")
        finally:
            self.tiles_container.setUpdatesEnabled(True)
            self.tiles_container.update()

    def create_tile_widget_for_pair(self, file_pair: FilePair, parent_widget):
        """
        Tworzy pojedynczy kafelek dla pary plików - thread safe.
        """
        try:
            # Przekaż _current_size_tuple jako krotkę (width, height)
            tile = FileTileWidget(
                file_pair,
                self._current_size_tuple,
                parent_widget,
                skip_resource_registration=True,
            )
            # NIE ukrywaj kafli na starcie
            tile.setVisible(True)  # ZAWSZE widoczne

            # Thread-safe dodanie do słownika
            with self._widgets_lock:
                self.gallery_tile_widgets[file_pair.get_archive_path()] = tile

            return tile
        except Exception as e:
            logger.error(f"Błąd tworzenia kafelka dla {file_pair.get_base_name()}: {e}")
            return None

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
            self.special_folders_list, self.file_pairs_list
        )

    def cancel_tile_creation(self):
        """Cancel ongoing tile creation."""
        if self._tile_creation_in_progress and hasattr(self, "_progressive_creator"):
            self._progressive_creator.cancel_creation()
            self._tile_creation_in_progress = False
            logging.info("Tile creation cancelled by user")

    def update_gallery_view(self):
        """
        Aktualizuje widok galerii z ENHANCED INTELLIGENT LOADING STRATEGY.
        """
        total_items = len(self.special_folders_list) + len(self.file_pairs_list)
        
        logger.info(f"Gallery update: {len(self.special_folders_list)} folders + "
                   f"{len(self.file_pairs_list)} pairs = {total_items} total items")

        # INTELLIGENT LOADING STRATEGY z system specs detection
        try:
            if psutil:
                memory_gb = psutil.virtual_memory().total / (1024**3)
                cpu_count = psutil.cpu_count(logical=True)
                # KRYTYCZNA ZMIANA: Wymuś progresywny tryb dla >100 kafelków
                force_threshold = 100
                progressive_threshold = 1000
            else:
                force_threshold = 100
                progressive_threshold = 1000
        except:
            force_threshold = 100
            progressive_threshold = 1000

        logger.info(f"System specs: {memory_gb:.0f}GB RAM, {cpu_count} CPUs")
        logger.info(f"Thresholds: force≤{force_threshold}, progressive≤{progressive_threshold}")

        # LOADING STRATEGY SELECTION
        if total_items == 0:
            self.clear_gallery()
            logger.info("Gallery cleared - no items to display")
        elif total_items <= force_threshold:
            logger.info(f"Using instant creation for {total_items} items (≤{force_threshold})")
            self.force_create_all_tiles()
        else:
            logger.info(f"Using progressive creation for {total_items} items (>{force_threshold})")
            self.create_all_tiles_progressive()

        # SELECTIVE VIRTUALIZATION based na dataset size - WYŁĄCZ dla mniejszych zbiorów
        virtualization_enabled = self.memory_manager.should_enable_virtualization(total_items)
        if virtualization_enabled != self._virtualization_enabled:
            self._virtualization_enabled = virtualization_enabled
            logger.info(f"Virtualization {'enabled' if virtualization_enabled else 'disabled'} "
                       f"for {total_items} items (threshold: {self.memory_manager.virtualization_threshold})")

        # PERFORMANCE LOGGING dla wszystkich datasets
        if total_items > 100:
            memory_stats = self.memory_manager.get_memory_stats()
            logger.info(f"Gallery loaded: {memory_stats['active_widgets']} active widgets, "
                       f"virtualization: {self._virtualization_enabled}")

        # KRYTYCZNE DEBUG - sprawdź ile kafelków jest rzeczywiście widocznych
        visible_count = len([w for w in self.gallery_tile_widgets.values() if w.isVisible()])
        folder_count = len([w for w in self.special_folder_widgets.values() if w.isVisible()])
        logger.info(f"🔍 DEBUG: Visible tiles: {visible_count}/{len(self.gallery_tile_widgets)}, "
                   f"folders: {folder_count}/{len(self.special_folder_widgets)}")
        
        # EMERGENCY FIX - jeśli są tworzone ale niewidoczne, pokaż je wszystkie
        if len(self.gallery_tile_widgets) > 0 and visible_count < 10:
            logger.warning(f"⚠️ EMERGENCY: Only {visible_count} tiles visible out of {len(self.gallery_tile_widgets)}, forcing visibility!")
            for widget in self.gallery_tile_widgets.values():
                widget.setVisible(True)
            for widget in self.special_folder_widgets.values():
                widget.setVisible(True)
            self.tiles_container.update()

    def _update_visible_tiles(self):
        """Tworzy/usuwa kafelki w zależności od tego, czy są widoczne."""
        # CAŁKOWICIE WYŁĄCZONE - powodowało znikanie kafli
        return

    def apply_filters_and_update_view(
        self, all_file_pairs: List[FilePair], filter_criteria: dict
    ):
        """
        Aplikuje filtry i aktualizuje widok galerii.

        Args:
            all_file_pairs: Lista wszystkich par plików do przefiltrowania
            filter_criteria: Kryteria filtrowania
        """
        try:
            from src.logic.filter_logic import filter_file_pairs

            # Przefiltruj pliki
            filtered_pairs = filter_file_pairs(all_file_pairs, filter_criteria)

            # Ustaw file_pairs_list PRZED wywołaniem update_gallery_view()
            self.file_pairs_list = filtered_pairs

            # Aktualizuj widok
            self.update_gallery_view()

        except Exception as e:
            logger.error(f"Błąd podczas aplikowania filtrów: {e}")
            # Fallback: pokaż wszystkie pliki
            self.file_pairs_list = all_file_pairs
            self.update_gallery_view()

    def update_thumbnail_size(self, new_size):
        """
        Aktualizuje rozmiar miniatur i przerenderowuje galerię.
        new_size może być int lub tuple (width, height).

        Zoptymalizowana wersja - aktualizuje tylko widoczne kafelki.
        """
        # Obsługa różnych formatów new_size
        if isinstance(new_size, int):
            self.current_thumbnail_size = new_size
            self._current_size_tuple = (new_size, new_size)
        else:
            # current_thumbnail_size w GalleryManager powinien być int (szerokość)
            # Zakładamy, że new_size[0] to nowa szerokość
            self.current_thumbnail_size = new_size[0]
            self._current_size_tuple = new_size

        # Zaktualizuj rozmiar tylko dla widocznych kafelków + cache nowego rozmiaru dla pozostałych
        with self._widgets_lock:
            # Natychmiast zaktualizuj widoczne kafelki
            for tile in self.gallery_tile_widgets.values():
                if tile.isVisible():
                    tile.set_thumbnail_size(self._current_size_tuple)

            for folder_widget in self.special_folder_widgets.values():
                if folder_widget.isVisible():
                    folder_widget.set_thumbnail_size(self._current_size_tuple)

        # Zaznacz, że niewidoczne kafelki potrzebują aktualizacji
        self._pending_size_update = True

        # Invalidate geometry cache
        with self._geometry_cache_lock:
            self._geometry_cache["last_thumbnail_size"] = 0

        # Przerenderuj galerię z nowymi rozmiarami
        self.update_gallery_view()

    def get_all_tile_widgets(self) -> List[FileTileWidget]:
        """
        Zwraca listę wszystkich widgetów kafelków w galerii.
        Używane do operacji zbiorczych (zaznaczanie wszystkich, operacje na zaznaczonych).

        Returns:
            List[FileTileWidget]: Lista wszystkich widgetów kafelków
        """
        return list(self.gallery_tile_widgets.values())

    def get_visible_tile_widgets(self) -> List[FileTileWidget]:
        """
        Zwraca listę tylko widocznych widgetów kafelków.
        Optymalizacja dla operacji na widocznych kafelkach.

        Returns:
            List[FileTileWidget]: Lista widocznych widgetów kafelków
        """
        return [tile for tile in self.gallery_tile_widgets.values() if tile.isVisible()]

    def get_tile_for_path(self, archive_path: str) -> FileTileWidget:
        """
        Pobiera kafelek dla określonej ścieżki archiwum.
        Zwraca None, jeśli kafelek nie istnieje.

        Args:
            archive_path: Ścieżka do pliku archiwum

        Returns:
            FileTileWidget: Znaleziony widget kafelka lub None
        """
        return self.gallery_tile_widgets.get(archive_path)

    def create_folder_widget(self, special_folder: SpecialFolder):
        """
        Tworzy widget dla folderu specjalnego.
        """
        try:
            folder_name = special_folder.get_folder_name()
            folder_path = special_folder.get_folder_path()
            is_virtual = special_folder.is_virtual

            # Sprawdź, czy folder fizycznie istnieje, TYLKO jeśli nie jest wirtualny
            if not is_virtual and not os.path.exists(folder_path):
                return None

            folder_widget = SpecialFolderTileWidget(
                folder_name, folder_path, self.tiles_container
            )
            folder_widget.set_thumbnail_size(self.current_thumbnail_size)

            # Podłącz sygnał kliknięcia
            folder_widget.folder_clicked.connect(self._on_folder_clicked)

            # Thread-safe dodanie do słownika
            with self._widgets_lock:
                self.special_folder_widgets[folder_path] = folder_widget

            return folder_widget
        except Exception as e:
            logger.error(f"Błąd tworzenia widgetu folderu: {e}", exc_info=True)
            return None

    def _on_folder_clicked(self, folder_path: str):
        """
        Obsługuje kliknięcie na kafelek folderu specjalnego.
        Otwiera folder w eksploratorze plików systemu.

        Args:
            folder_path (str): Ścieżka do folderu do otwarcia.
        """
        if not folder_path or not os.path.exists(folder_path):
            logger.warning(f"Próba otwarcia nieistniejącego folderu: {folder_path}")
            return

        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
        except Exception as e:
            logger.error(f"Nie udało się otworzyć folderu {folder_path}: {e}")

    def prepare_special_folders(self, special_folders: List[SpecialFolder]):
        """
        Przygotowuje widgety dla folderów specjalnych przed aktualizacją widoku.
        """
        self.special_folders_list = special_folders

        # Wyczyść poprzednie widgety folderów
        with self._widgets_lock:
            for folder_path in list(self.special_folder_widgets.keys()):
                folder_widget = self.special_folder_widgets.pop(folder_path)
                folder_widget.setParent(None)
                folder_widget.deleteLater()
            self.special_folder_widgets.clear()

        # Utwórz nowe widgety dla folderów
        for special_folder in special_folders:
            widget = self.create_folder_widget(special_folder)

    def set_special_folders(self, special_folders: List[SpecialFolder]):
        """
        Ustawia listę specjalnych folderów i OD RAZU odświeża widok.
        """
        # Krok 1: Przygotuj widgety w tle
        self.prepare_special_folders(special_folders)

        # Krok 2: Wymuś aktualizację widoku, aby pokazać nowe foldery
        self.update_gallery_view()

    def _ensure_widget_created(self, item, item_index):
        """Zapewnia że widget jest utworzony i ma poprawny rozmiar."""
        if isinstance(item, SpecialFolder):
            path = item.get_folder_path()
            widget = self.special_folder_widgets.get(path)
            if not widget:
                widget = self.create_folder_widget(item)
                if not widget:
                    return None

            # Sprawdź czy widget ma aktualny rozmiar
            if hasattr(self, "_pending_size_update") and self._pending_size_update:
                widget.set_thumbnail_size(self._current_size_tuple)

        else:  # FilePair
            path = item.get_archive_path()
            widget = self.gallery_tile_widgets.get(path)
            if not widget:
                widget = self.create_tile_widget_for_pair(item, self.tiles_container)
                if not widget:
                    return None

            # Sprawdź czy widget ma aktualny rozmiar
            if hasattr(self, "_pending_size_update") and self._pending_size_update:
                widget.set_thumbnail_size(self._current_size_tuple)

        return widget

    def _on_tile_double_clicked(self, file_pair):
        """Obsługuje podwójne kliknięcie na kafelek pary plików."""
        # ... existing code ...

    def force_create_all_tiles(self):
        """
        Wymusza tworzenie wszystkich kafelków z OPTIMIZED YIELDING i memory monitoring.
        """
        import traceback

        from PyQt6.QtWidgets import QApplication

        logger.info(f"Force creating all tiles: {len(self.special_folders_list)} folders + "
                   f"{len(self.file_pairs_list)} pairs")

        # MEMORY MONITORING dla large operations
        total_items = len(self.special_folders_list) + len(self.file_pairs_list)
        if total_items > 1000:
            try:
                if psutil:
                    initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    logger.info(f"Starting force creation: {initial_memory:.0f}MB memory")
            except:
                pass

        # Wyłącz limit TileResourceManager dla force_create_all_tiles
        original_max_tiles = get_resource_manager().limits.max_tiles
        get_resource_manager().limits.max_tiles = 10000  # Tymczasowo zwiększ limit

        # Wyczyść stare kafelki przed tworzeniem nowych
        self.clear_gallery()

        self.tiles_container.setUpdatesEnabled(False)
        try:
            # Wyczyść layout
            while self.tiles_layout.count() > 0:
                item = self.tiles_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

            all_items = self.special_folders_list + self.file_pairs_list
            geometry = self._get_cached_geometry()
            cols = geometry["cols"]

            # OPTIMIZED BATCH PROCESSING - mniejsze batch'e dla lepszej responsywności
            batch_size = 25  # Zmniejszono z 100 na 25 dla better UI responsiveness
            total_batches = (len(all_items) + batch_size - 1) // batch_size
            
            logger.info(f"Processing {len(all_items)} items in {total_batches} batches of {batch_size}")

            # Inicjalizuj progres bar dla wszystkich kafelków (foldery + pliki)
            if hasattr(self.main_window, "progress_manager"):
                self.main_window.progress_manager.init_batch_processing(total_items)
                created_count = 0

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(all_items))

                for i in range(start_idx, end_idx):
                    if i < len(self.special_folders_list):
                        # Twórz kafelki folderów specjalnych
                        folder = self.special_folders_list[i]
                        widget = SpecialFolderTileWidget(
                            folder.folder_name, folder.get_folder_path(), self.tiles_container
                        )
                        tooltip = f"[{i + 1}/{len(self.special_folders_list)}] {folder.folder_name}"
                        widget.setToolTip(tooltip)
                        widget.setObjectName(f"SpecialFolderTile_{i + 1}")
                        widget.setVisible(True)
                        widget.show()
                        self.special_folder_widgets[folder.get_folder_path()] = widget
                        self.tiles_layout.addWidget(widget, i // cols, i % cols)
                    else:
                        # Twórz kafelki par plików
                        file_pair_idx = i - len(self.special_folders_list)
                        file_pair = self.file_pairs_list[file_pair_idx]
                        logger.info(f"Tworzę kafelek: thumbnail_size={self.current_thumbnail_size}")
                        widget = self.create_tile_widget_for_pair(
                            file_pair, self.tiles_container
                        )
                        if widget:
                            logger.info(f"Widget sizeHint: {widget.sizeHint()}, widget height: {widget.height()}")
                            # Podłącz sygnały do kafelka (jak w tile_manager.py)
                            widget.archive_open_requested.connect(
                                self.main_window.open_archive
                            )
                            widget.preview_image_requested.connect(
                                self.main_window._show_preview_dialog
                            )
                            widget.tile_selected.connect(
                                self.main_window._handle_tile_selection_changed
                            )
                            widget.stars_changed.connect(
                                self.main_window._handle_stars_changed
                            )
                            widget.color_tag_changed.connect(
                                self.main_window._handle_color_tag_changed
                            )
                            widget.tile_context_menu_requested.connect(
                                self.main_window._show_file_context_menu
                            )
                            if hasattr(widget, "set_tile_number"):
                                widget.set_tile_number(
                                    file_pair_idx + 1, len(self.file_pairs_list)
                                )
                            widget.setObjectName(f"FileTile_{file_pair_idx + 1}")
                            widget.setVisible(True)
                            widget.show()
                            self.gallery_tile_widgets[file_pair.archive_path] = widget
                            self.tiles_layout.addWidget(widget, i // cols, i % cols)
                            layout_pos = self.tiles_layout.getItemPosition(self.tiles_layout.indexOf(widget))
                            logger.debug(f"✅ Widget {file_pair_idx + 1} added at layout position: {layout_pos}")
                        else:
                            logger.error(
                                f"Failed to create widget for {file_pair.get_base_name()}"
                            )
                            continue
                    # --- AKTUALIZACJA PROGRESU ---
                    if hasattr(self.main_window, "progress_manager"):
                        created_count += 1
                        self.main_window.progress_manager.update_tile_creation_progress(created_count)

                # ENHANCED YIELDING - częstsze processEvents dla better responsiveness
                if (batch_num + 1) % 2 == 0:  # Co 2 batche zamiast co 5
                    try:
                        QApplication.processEvents()
                        # Progress indication dla large operations
                        if total_batches > 10:
                            progress = int((batch_num + 1) / total_batches * 100)
                            logger.debug(f"Force creation progress: {progress}%")
                    except Exception:
                        pass
                    
                    # Adaptive yield time based na batch size
                    if total_items > 2000:
                        time.sleep(0.002)  # 2ms dla very large datasets
                    elif total_items > 1000:
                        time.sleep(0.001)  # 1ms dla large datasets

            # MEMORY MONITORING po zakończeniu
            if total_items > 1000:
                try:
                    if psutil:
                        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
                        memory_growth = final_memory - initial_memory
                        logger.info(f"Force creation completed: {final_memory:.0f}MB memory "
                                  f"(+{memory_growth:.0f}MB growth)")
                except:
                    pass

            # EXISTING HEIGHT CALCULATION CODE...
            n = len(all_items)  # ilość par w folderze
            k = cols  # ilość kolumn
            y = self.current_thumbnail_size  # wysokość kafla (thumbnail)
            x = self.tiles_layout.spacing()  # Usunięto +40!
            logger.info(f"Tiles layout spacing: {x}")
            z = math.ceil(n / k)
            total_height = z * (y + x)
            total_height += y
            logger.info(f"📐 [PROGRESSIVE] Layout calculation: items={n}, cols={k}, rows={z}, tile_size={y}, spacing={x}")
            logger.info(f"📐 [PROGRESSIVE] Container height: {total_height}px, current container size: {self.tiles_container.size()}")
            
            self.tiles_container.setMinimumHeight(total_height)
            self.tiles_container.setMaximumHeight(total_height)
            self.tiles_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            self.tiles_container.adjustSize()
            logger.info(f"📐 [PROGRESSIVE] After adjustSize: container size: {self.tiles_container.size()}")
            self.tiles_container.updateGeometry()
            self.scroll_area.updateGeometry()
            if hasattr(self.scroll_area, "verticalScrollBar"):
                self.scroll_area.verticalScrollBar().setValue(0)
                logger.info(f"📐 [PROGRESSIVE] Scroll reset to top, scrollbar range: 0-{self.scroll_area.verticalScrollBar().maximum()}")

            # Wymuś pełny relayout i popraw polityki rozmiaru
            self.tiles_layout.invalidate()
            self.tiles_container.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
            )
            self.tiles_container.adjustSize()
            self.tiles_container.updateGeometry()
            if hasattr(self.scroll_area, "widget"):
                self.scroll_area.widget().adjustSize()
            self.scroll_area.updateGeometry()

            # 🚨 KRYTYCZNA NAPRAWKA VISIBILITY - FORCE wszystkie kafelki do widoczności
            visible_tiles = 0
            hidden_tiles = 0
            for widget in self.gallery_tile_widgets.values():
                if widget.isVisible():
                    visible_tiles += 1
                else:
                    widget.setVisible(True)
                    widget.show()  # Explicit show()
                    hidden_tiles += 1
                    
            for widget in self.special_folder_widgets.values():
                if widget.isVisible():
                    visible_tiles += 1
                else:
                    widget.setVisible(True)
                    widget.show()  # Explicit show()
                    hidden_tiles += 1
                    
            if hidden_tiles > 0:
                logger.warning(f"🚨 FORCED VISIBILITY: {hidden_tiles} hidden tiles made visible, total visible: {visible_tiles + hidden_tiles}")
            else:
                logger.info(f"✅ All {visible_tiles} tiles already visible")

        except Exception as e:
            logger.error(f"Error in force_create_all_tiles: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.tiles_container.setUpdatesEnabled(True)
            self.tiles_container.update()

            # Przywróć limit TileResourceManager
            get_resource_manager().limits.max_tiles = original_max_tiles

    def force_memory_cleanup(self):
        """Force memory cleanup - dla debug purposes."""
        if hasattr(self, "memory_manager"):
            self.memory_manager._trigger_memory_cleanup()

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        stats = {}

        if hasattr(self, "memory_manager"):
            stats["memory_manager"] = self.memory_manager.get_memory_stats()

        if hasattr(self, "_geometry"):
            stats["geometry_cache"] = self._geometry.get_cache_stats()

        # Add widget counts
        stats["total_widgets"] = len(getattr(self, "gallery_tile_widgets", []))
        stats["active_widgets"] = len(
            [w for w in getattr(self, "gallery_tile_widgets", []) if w]
        )

        return stats
