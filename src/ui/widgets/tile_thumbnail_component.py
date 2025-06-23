"""
ETAP 3: THUMBNAIL COMPONENT - Wydzielony komponent thumbnail
Separuje logikę ładowania miniaturek od głównej klasy FileTileWidget.
"""

import asyncio
import logging
import math
import os
import re
import threading
import time
import uuid
import weakref
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from PyQt6.QtCore import QEventLoop, QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap

from src.ui.widgets.tile_config import TileConfig, TileEvent
from src.ui.widgets.tile_event_bus import TileEventBus

logger = logging.getLogger(__name__)


class TileState(Enum):
    """Stany komponentu thumbnail."""

    EMPTY = auto()
    LOADING = auto()
    READY = auto()
    ERROR = auto()
    DISPOSED = auto()


class BoundedLRUCache:
    """Thread-safe bounded LRU cache dla scaled pixmaps."""

    def __init__(self, max_size: int = 50, max_memory_mb: float = 20.0):
        self.max_size = max_size
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self._cache: OrderedDict[Tuple[int, int], QPixmap] = OrderedDict()
        self._memory_usage = 0
        self._lock = threading.RLock()

    def get(self, key: Tuple[int, int]) -> Optional[QPixmap]:
        """Get pixmap from cache."""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                pixmap = self._cache.pop(key)
                self._cache[key] = pixmap
                return pixmap
            return None

    def put(self, key: Tuple[int, int], pixmap: QPixmap):
        """Put pixmap into cache z eviction."""
        if pixmap.isNull():
            return

        pixmap_size = self._estimate_pixmap_size(pixmap)

        with self._lock:
            # Remove existing entry if present
            if key in self._cache:
                old_pixmap = self._cache[key]
                old_size = self._estimate_pixmap_size(old_pixmap)
                self._memory_usage -= old_size
                del self._cache[key]

            # Evict entries if necessary
            while (
                len(self._cache) >= self.max_size
                or self._memory_usage + pixmap_size > self.max_memory_bytes
            ):
                if not self._cache:
                    break

                # Remove least recently used
                lru_key, lru_pixmap = self._cache.popitem(last=False)
                lru_size = self._estimate_pixmap_size(lru_pixmap)
                self._memory_usage -= lru_size

            # Add new entry
            self._cache[key] = pixmap
            self._memory_usage += pixmap_size

    def clear(self):
        """Clear cache."""
        with self._lock:
            self._cache.clear()
            self._memory_usage = 0

    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "memory_usage_mb": self._memory_usage / (1024 * 1024),
                "max_memory_mb": self.max_memory_bytes / (1024 * 1024),
                "memory_usage_percent": (
                    (self._memory_usage / self.max_memory_bytes) * 100
                    if self.max_memory_bytes > 0
                    else 0
                ),
            }

    def _estimate_pixmap_size(self, pixmap: QPixmap) -> int:
        """Estimate pixmap memory usage."""
        if pixmap.isNull():
            return 0
        return pixmap.width() * pixmap.height() * 4  # RGBA


class PathValidator:
    """Secure path validation dla thumbnail loading."""

    # Allowed file extensions for thumbnails
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}

    # Maximum path length
    MAX_PATH_LENGTH = 260  # Windows limit

    # Suspicious patterns (tylko dla ścieżki, nie nazwy pliku)
    SUSPICIOUS_PATTERNS = [
        r"\.\.[\\/]",  # Path traversal
        r"[\\/]\.\.[\\/]",  # Path traversal in middle
        r"[\x00-\x1f]",  # Control characters
        # r'[<>:"|?*]',  # NIE sprawdzamy na całej ścieżce!
    ]

    @classmethod
    def validate_path(
        cls, file_path: str, base_dir: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Validate file path dla security i correctness.

        Args:
            file_path: Path to validate
            base_dir: Optional base directory for relative path validation

        Returns:
            tuple: (is_valid, error_message)
        """
        if not file_path:
            return False, "Empty file path"

        if len(file_path) > cls.MAX_PATH_LENGTH:
            return False, f"Path too long: {len(file_path)} > {cls.MAX_PATH_LENGTH}"

        # Check for suspicious patterns (tylko na ścieżce)
        for pattern in cls.SUSPICIOUS_PATTERNS:
            if re.search(pattern, file_path):
                return False, f"Suspicious path pattern detected: {pattern}"

        try:
            path = Path(file_path)

            # Check if path exists
            if not path.exists():
                return False, f"File does not exist: {file_path}"

            # Check if it's a file (not directory)
            if not path.is_file():
                return False, f"Path is not a file: {file_path}"

            # Check file extension
            if path.suffix.lower() not in cls.ALLOWED_EXTENSIONS:
                return False, f"Unsupported file extension: {path.suffix}"

            # Check if path is within allowed base directory
            if base_dir:
                base_path = Path(base_dir).resolve()
                resolved_path = path.resolve()

                try:
                    resolved_path.relative_to(base_path)
                except ValueError:
                    return False, f"Path outside allowed directory: {file_path}"

            # Additional security checks
            if not os.access(path, os.R_OK):
                return False, f"No read permission: {file_path}"

            # Sprawdź forbidden chars tylko w nazwie pliku
            forbidden_chars_pattern = r'[<>:"|?*]'
            if re.search(forbidden_chars_pattern, path.name):
                return (
                    False,
                    f'Suspicious filename pattern detected: [<>:"|?*] in {path.name}',
                )

            return True, ""

        except Exception as e:
            return False, f"Path validation error: {e}"


class WorkerManager:
    """Manages thumbnail loading workers z proper cleanup."""

    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._active_futures: Dict[str, Future] = {}
        self._worker_callbacks: Dict[str, tuple] = {}
        self._lock = threading.RLock()

    def submit_work(
        self,
        worker_func: Callable,
        *args,
        success_callback: Optional[Callable] = None,
        error_callback: Optional[Callable] = None,
    ) -> str:
        """Submit work z proper callback management."""
        worker_id = str(uuid.uuid4())

        with self._lock:
            # Submit work to executor
            future = self._executor.submit(worker_func, *args)
            self._active_futures[worker_id] = future
            self._worker_callbacks[worker_id] = (success_callback, error_callback)

            # Add completion callback
            future.add_done_callback(lambda f: self._on_worker_complete(worker_id, f))

        return worker_id

    def cancel_work(self, worker_id: str) -> bool:
        """Cancel specific worker."""
        with self._lock:
            if worker_id in self._active_futures:
                future = self._active_futures[worker_id]
                cancelled = future.cancel()
                if cancelled:
                    self._cleanup_worker(worker_id)
                return cancelled
            return False

    def cancel_all(self):
        """Cancel all active workers."""
        with self._lock:
            for worker_id in list(self._active_futures.keys()):
                self.cancel_work(worker_id)

    def _on_worker_complete(self, worker_id: str, future: Future):
        """Handle worker completion."""
        with self._lock:
            if worker_id not in self._worker_callbacks:
                return

            success_callback, error_callback = self._worker_callbacks[worker_id]

            try:
                if future.cancelled():
                    # Work was cancelled
                    pass
                elif future.exception():
                    # Work had exception
                    if error_callback:
                        error_callback(future.exception())
                else:
                    # Work completed successfully
                    result = future.result()
                    if success_callback:
                        success_callback(result)

            except Exception as e:
                logger.error(f"Error in worker callback: {e}")
            finally:
                self._cleanup_worker(worker_id)

    def _cleanup_worker(self, worker_id: str):
        """Cleanup worker references."""
        with self._lock:
            self._active_futures.pop(worker_id, None)
            self._worker_callbacks.pop(worker_id, None)

    def get_stats(self) -> dict:
        """Get worker statistics."""
        with self._lock:
            return {
                "active_workers": len(self._active_futures),
                "max_workers": self.max_workers,
            }

    def cleanup(self):
        """Cleanup worker manager."""
        self.cancel_all()
        self._executor.shutdown(wait=True)


class ThumbnailComponent(QObject):
    """
    Komponent do zarządzania miniaturkami dla FileTileWidget.
    Separuje logikę ładowania miniaturek od głównej klasy.
    """

    # Signals
    thumbnail_loaded = pyqtSignal(str, object)  # path, pixmap
    thumbnail_error = pyqtSignal(str, str)  # path, error_message
    state_changed = pyqtSignal(object)  # TileState

    def __init__(
        self,
        config: TileConfig,
        event_bus: TileEventBus,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)

        self.config = config
        self.event_bus = event_bus

        # State management
        self._current_state: TileState = TileState.EMPTY
        self._current_path: Optional[str] = None
        self._current_size: Tuple[int, int] = (0, 0)
        self._pending_size: Optional[Tuple[int, int]] = (
            None  # For debounced size changes
        )
        self._pixmap: Optional[QPixmap] = None
        self._memory_usage_bytes: int = 0
        self._is_loading: bool = False
        self._is_disposed: bool = False

        # OPTYMALIZACJA: Bounded LRU cache dla różnych rozmiarów tej samej miniaturki
        self._scaled_pixmap_cache = BoundedLRUCache(
            max_size=getattr(config, "max_scaled_cache_size", 50),
            max_memory_mb=getattr(config, "max_scaled_cache_memory_mb", 20.0),
        )
        self._original_pixmap: Optional[QPixmap] = None  # Cache oryginalnej miniaturki

        # Enhanced worker management
        self._current_worker_id: Optional[str] = None
        self._resource_manager_worker_id: Optional[int] = None  # Resource management

        # Path validation
        self._path_validator = PathValidator()
        self._base_dir = getattr(config, "base_directory", None)

        # Memory pressure monitoring
        self._last_memory_check = time.time()
        self._memory_check_interval = 10.0  # seconds
        self._memory_pressure_level = 0  # 0=normal, 1=warning, 2=critical

        # Timers for debouncing
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(self.config.debounce_delay_ms)
        self._resize_timer.timeout.connect(self._on_resize_timer)

        # Setup connections
        self._setup_connections()
        self._connect_memory_pressure_signals()

        if self.config.enable_debug_logging:
            logger.debug("ThumbnailComponent initialized")

    def _setup_connections(self):
        """Setup internal connections."""
        # Connect internal signals
        self.thumbnail_loaded.connect(self._on_thumbnail_loaded)
        self.thumbnail_error.connect(self._on_thumbnail_error)
        self.state_changed.connect(self._set_state)

        # Subscribe to event bus
        if self.event_bus:
            self.event_bus.subscribe(
                TileEvent.THUMBNAIL_LOADED, self._on_external_thumbnail_loaded
            )
            self.event_bus.subscribe(
                TileEvent.THUMBNAIL_ERROR, self._on_external_thumbnail_error
            )
            self.event_bus.subscribe(TileEvent.STATE_CHANGED, self._set_state)

    def _connect_memory_pressure_signals(self):
        """Connect to memory pressure signals."""
        try:
            from src.ui.widgets.tile_async_ui_manager import get_async_ui_manager
            from src.ui.widgets.tile_cache_optimizer import get_cache_optimizer

            # Connect to cache optimizer memory pressure
            cache_optimizer = get_cache_optimizer()
            cache_optimizer.memory_pressure_detected.connect(self._on_memory_pressure)

            # Connect to async UI manager performance warnings
            async_manager = get_async_ui_manager()
            async_manager.performance_warning.connect(self._on_performance_warning)

        except Exception as e:
            logger.debug(f"Failed to connect memory pressure signals: {e}")

    def _on_memory_pressure(self, memory_usage_mb: float):
        """Handle memory pressure from cache optimizer."""
        if memory_usage_mb > 150:  # High memory usage
            self._memory_pressure_level = 2  # Critical
            self._handle_critical_memory_pressure()
        elif memory_usage_mb > 100:  # Medium memory usage
            self._memory_pressure_level = 1  # Warning
            self._handle_warning_memory_pressure()
        else:
            self._memory_pressure_level = 0  # Normal

    def _on_performance_warning(self, warning_type: str, value: float):
        """Handle performance warnings."""
        if warning_type == "HIGH_MEMORY_USAGE":
            self._on_memory_pressure(value)

    def _handle_critical_memory_pressure(self):
        """Handle critical memory pressure."""
        logger.debug("Critical memory pressure - aggressive cleanup")

        # Clear all local caches
        self._scaled_pixmap_cache.clear()

        # Clear original pixmap
        self._original_pixmap = None

        # Cancel current loading to reduce memory usage
        if self._is_loading:
            self._cancel_current_loading()

        # Force garbage collection
        import gc

        gc.collect()

    def _handle_warning_memory_pressure(self):
        """Handle warning level memory pressure."""
        logger.info("Memory pressure warning - partial cleanup")

        # Get cache stats
        cache_stats = self._scaled_pixmap_cache.get_stats()

        # Clear cache if it's using too much memory
        if cache_stats["memory_usage_percent"] > 80:
            self._scaled_pixmap_cache.clear()
            logger.debug("Cleared scaled pixmap cache due to memory pressure")

    def load_thumbnail(
        self, file_path: str, size: Optional[Tuple[int, int]] = None
    ) -> bool:
        """
        Ładuje miniaturę dla podanego pliku.

        Args:
            file_path: Ścieżka do pliku obrazu
            size: Rozmiar miniatury (width, height), domyślnie z config

        Returns:
            bool: True jeśli ładowanie rozpoczęte, False w przeciwnym razie
        """
        if getattr(self, "_is_disposed", False):
            return False

        # Check memory pressure before loading
        if self._memory_pressure_level >= 2:
            # Under critical memory pressure - defer loading
            logger.debug(
                f"Deferring thumbnail load due to critical memory pressure: {file_path}"
            )
            return False

        # Validate path first
        is_valid, error_msg = self._path_validator.validate_path(
            file_path, self._base_dir
        )
        if not is_valid:
            self._emit_error(f"Invalid path: {error_msg}")
            return False

        # Get target size
        target_size = size or self.config.thumbnail_size

        # Check if already loading this path/size
        if (
            self._current_path == file_path
            and self._current_size == target_size
            and self._is_loading
        ):
            if self.config.enable_debug_logging:
                logger.debug(f"Already loading {file_path} at {target_size}")
            return True

        # Cancel current loading if different
        if self._is_loading:
            self._cancel_current_loading()

        # Store new request
        self._current_path = file_path
        self._current_size = target_size

        # Check cache first - this is still sync but very fast
        if self._try_load_from_cache(file_path, target_size):
            return True

        # ALWAYS use async loading - remove sync option
        self._set_state(TileState.LOADING)
        self._is_loading = True

        return self._start_async_loading(file_path, target_size)

    def load_thumbnail_with_resource_management(
        self, file_path: str, size: Optional[Tuple[int, int]] = None
    ) -> bool:
        """
        Ładuje miniaturę z uwzględnieniem resource management.

        Args:
            file_path: Ścieżka do pliku obrazu
            size: Rozmiar miniatury

        Returns:
            bool: True jeśli ładowanie rozpoczęte
        """
        if getattr(self, "_is_disposed", False):
            return False

        try:
            # Importuj resource manager tutaj żeby uniknąć circular import
            from src.ui.widgets.tile_resource_manager import get_resource_manager

            resource_manager = get_resource_manager()

            # Sprawdź czy można uruchomić workera
            if not resource_manager.can_start_worker():
                if self.config.enable_debug_logging:
                    logger.debug(
                        f"Worker limit reached, deferring thumbnail load: {file_path}"
                    )

                # Można dodać do kolejki lub spróbować ponownie później
                # Na razie po prostu logujemy i zwracamy False
                return False

            # Zarejestruj workera przed rozpoczęciem ładowania
            worker_id = resource_manager.register_worker()
            if worker_id is None:
                logger.warning(
                    "Failed to register worker despite can_start_worker() returning True"
                )
                return False

            # Store worker ID for cleanup
            self._resource_manager_worker_id = worker_id

            # Rozpocznij normalne ładowanie
            result = self.load_thumbnail(file_path, size)

            # Jeśli ładowanie się nie udało, wyrejestruj workera
            if not result:
                resource_manager.unregister_worker(worker_id)
                self._resource_manager_worker_id = None

            return result

        except Exception as e:
            logger.error(f"Error in resource-managed thumbnail loading: {e}")
            return False

    def set_thumbnail_size(self, size: Tuple[int, int], immediate: bool = False):
        """
        Ustaw nowy rozmiar miniatury z debouncing.

        Args:
            size: Nowy rozmiar (width, height)
            immediate: Czy załadować natychmiast bez debouncing
        """
        if getattr(self, "_is_disposed", False):
            return

        if size == self._current_size:
            return

        # Store pending size change
        self._pending_size = size

        if immediate:
            self._apply_size_change()
        else:
            self._resize_timer.start(self.config.debounce_interval_ms)

    def _on_resize_timer(self):
        """Callback dla resize timer - aplikuje pending size change."""
        # NAPRAWKA: Sprawdź czy obiekt Qt nie został usunięty
        if not self._is_object_valid():
            return

        self._apply_size_change()

    def _apply_size_change(self):
        """Aplikuje zmianę rozmiaru miniatury z optymalizacją cache."""
        if not hasattr(self, "_pending_size") or self._pending_size is None:
            return

        new_size = self._pending_size
        self._pending_size = None

        # Update current size
        self._current_size = new_size

        # Try to get from scaled cache first
        cached_pixmap = self._scaled_pixmap_cache.get(new_size)
        if cached_pixmap and not cached_pixmap.isNull():
            self._on_thumbnail_ready(self._current_path, cached_pixmap, from_cache=True)
            return

        # If we have original pixmap, scale it
        if self._original_pixmap and not self._original_pixmap.isNull():
            scaled_pixmap = self._original_pixmap.scaled(
                new_size[0],
                new_size[1],
                self.config.scale_mode,
                self.config.transform_mode,
            )

            # Store in cache
            self._scaled_pixmap_cache.put(new_size, scaled_pixmap)

            # Update current pixmap
            self._pixmap = scaled_pixmap
            self._memory_usage_bytes = self._estimate_pixmap_size(scaled_pixmap)

            # Emit loaded signal
            self.thumbnail_loaded.emit(self._current_path, scaled_pixmap)
            self._set_state(TileState.READY)

        elif self._current_path:
            # Reload with new size
            self.load_thumbnail(self._current_path, new_size)

    def _start_async_loading(self, file_path: str, size: Tuple[int, int]) -> bool:
        """Enhanced async loading z better cache integration."""
        try:
            # First try global cache (TileCacheOptimizer)
            global_pixmap = self._try_get_from_global_cache(file_path, size)
            if global_pixmap:
                self._on_thumbnail_ready(file_path, global_pixmap, from_cache=True)
                return True

            # Then try thumbnail cache
            thumbnail_pixmap = self._try_get_from_thumbnail_cache(file_path, size)
            if thumbnail_pixmap:
                self._on_thumbnail_ready(file_path, thumbnail_pixmap, from_cache=True)
                return True

            # Direct synchronous loading - no more async workers!
            from src.utils.image_utils import create_thumbnail_from_file

            try:
                pixmap = create_thumbnail_from_file(file_path, size[0], size[1])
                if pixmap and not pixmap.isNull():
                    self._on_thumbnail_ready(file_path, pixmap, from_cache=False)
                    return True
                else:
                    self._emit_error(f"Failed to create thumbnail for {file_path}")
                    return False
            except Exception as e:
                self._emit_error(
                    f"Thumbnail generation failed for {file_path}: {str(e)}"
                )
                return False

        except Exception as e:
            self._emit_error(f"Failed to start loading: {e}")
            return False

    def _try_get_from_global_cache(
        self, file_path: str, size: Tuple[int, int]
    ) -> Optional[QPixmap]:
        """Try to get thumbnail from global cache optimizer."""
        try:
            from src.ui.widgets.tile_cache_optimizer import get_cache_optimizer

            cache_optimizer = get_cache_optimizer()
            cache_key = f"{file_path}_{size[0]}x{size[1]}"

            cached_data = cache_optimizer.get("thumbnails", cache_key)
            if cached_data and isinstance(cached_data, QPixmap):
                return cached_data

        except Exception as e:
            logger.debug(f"Failed to get from global cache: {e}")

        return None

    def _try_get_from_thumbnail_cache(
        self, file_path: str, size: Tuple[int, int]
    ) -> Optional[QPixmap]:
        """Try to get thumbnail from local thumbnail cache."""
        try:
            from src.ui.widgets.thumbnail_cache import ThumbnailCache

            cache = ThumbnailCache.get_instance()
            cached_pixmap = cache.get_thumbnail(file_path, size[0], size[1])

            if cached_pixmap and not cached_pixmap.isNull():
                return cached_pixmap

        except Exception as e:
            logger.debug(f"Failed to get from thumbnail cache: {e}")

        return None

    def _on_worker_success(self, file_path: str, result):
        """Handle successful worker completion."""
        if not self._is_object_valid():
            return

        # Extract pixmap from result
        if hasattr(result, "pixmap"):
            pixmap = result.pixmap
        else:
            # Fallback - result might be pixmap directly
            pixmap = result

        if isinstance(pixmap, QPixmap) and not pixmap.isNull():
            self._on_thumbnail_ready(file_path, pixmap, from_cache=False)
        else:
            self._emit_error(f"Invalid worker result for {file_path}")

    def _on_worker_error(self, file_path: str, error_msg: str):
        """Handle worker error."""
        if not self._is_object_valid():
            return

        self._emit_error(f"Worker error for {file_path}: {error_msg}")

    def _on_worker_thumbnail_ready(self, worker_id: int, path: str, pixmap: QPixmap):
        """Handle thumbnail ready from worker."""
        if not self._is_object_valid():
            return

        if worker_id == self._current_worker_id:
            self._on_thumbnail_ready(path, pixmap, from_cache=False)

    def _on_worker_thumbnail_error(self, worker_id: int, error_msg: str, path: str):
        """Handle thumbnail error from worker."""
        if not self._is_object_valid():
            return

        if worker_id == self._current_worker_id:
            self._emit_error(f"Worker error: {error_msg}")

    def _on_thumbnail_ready(self, path: str, pixmap: QPixmap, from_cache: bool = False):
        """Enhanced thumbnail ready z global cache integration."""
        if not self._is_object_valid():
            return

        if not pixmap or pixmap.isNull():
            self._emit_error(f"Invalid pixmap for {path}")
            return

        # Store original pixmap for future scaling
        if not from_cache:
            self._original_pixmap = pixmap

        # Store in global cache for other components
        if not from_cache:
            try:
                from src.ui.widgets.tile_cache_optimizer import get_cache_optimizer

                cache_optimizer = get_cache_optimizer()
                cache_key = f"{path}_{self._current_size[0]}x{self._current_size[1]}"

                # Estimate size for cache
                pixmap_size = pixmap.width() * pixmap.height() * 4  # RGBA
                cache_optimizer.put("thumbnails", cache_key, pixmap, pixmap_size)

            except Exception as e:
                logger.debug(f"Failed to store in global cache: {e}")

        # Store in local bounded cache
        if self._current_size and self._current_size != (0, 0):
            self._scaled_pixmap_cache.put(self._current_size, pixmap)

        # Update current pixmap
        self._pixmap = pixmap
        self._memory_usage_bytes = self._estimate_pixmap_size(pixmap)

        # Update state
        self._is_loading = False
        self._set_state(TileState.READY)

        # Emit signals
        self.thumbnail_loaded.emit(path, pixmap)

        # Resource manager cleanup
        if self._resource_manager_worker_id is not None:
            try:
                from src.ui.widgets.tile_resource_manager import get_resource_manager

                resource_manager = get_resource_manager()
                resource_manager.unregister_worker(self._resource_manager_worker_id)
                self._resource_manager_worker_id = None
            except Exception as e:
                logger.debug(f"Failed to unregister resource manager worker: {e}")

        if self.config.enable_debug_logging:
            logger.debug(
                f"Thumbnail ready: {path} ({pixmap.width()}x{pixmap.height()})"
            )

    def _cancel_current_loading(self):
        """Enhanced cancellation - no more workers."""
        self._is_loading = False

        if self.config.enable_debug_logging:
            logger.debug("Cancelled current loading")

    def _emit_error(self, error_message: str):
        """Emit error signal."""
        if not self._is_object_valid():
            return

        self._is_loading = False
        self._set_state(TileState.ERROR)

        # Resource manager cleanup on error
        if self._resource_manager_worker_id is not None:
            try:
                from src.ui.widgets.tile_resource_manager import get_resource_manager

                resource_manager = get_resource_manager()
                resource_manager.unregister_worker(self._resource_manager_worker_id)
                self._resource_manager_worker_id = None
            except Exception as e:
                logger.debug(
                    f"Failed to unregister resource manager worker on error: {e}"
                )

        self.thumbnail_error.emit(self._current_path or "", error_message)

        if self.config.enable_debug_logging:
            logger.debug(f"Thumbnail error: {error_message}")

    def _set_state(self, new_state: TileState):
        """Set new state and emit signal."""
        if not self._is_object_valid():
            return

        if self._current_state != new_state:
            self._current_state = new_state
            self.state_changed.emit(new_state)

            if self.config.enable_debug_logging:
                logger.debug(f"State changed to: {new_state}")

    def _on_thumbnail_loaded(self, path: str, pixmap: QPixmap):
        """Internal signal handler."""
        pass

    def _on_thumbnail_error(self, path: str, error_message: str):
        """Internal signal handler."""
        pass

    def _on_external_thumbnail_loaded(self, path: str, pixmap: QPixmap):
        """Handle external thumbnail loaded event."""
        if not self._is_object_valid():
            return

        if path == self._current_path:
            self._on_thumbnail_ready(path, pixmap, from_cache=True)

    def _on_external_thumbnail_error(self, path: str, error_message: str):
        """Handle external thumbnail error event."""
        if not self._is_object_valid():
            return

        if path == self._current_path:
            self._emit_error(error_message)

    def _try_load_from_cache(self, file_path: str, size: Tuple[int, int]) -> bool:
        """Try to load from cache."""
        cached_pixmap = self._scaled_pixmap_cache.get(size)
        if cached_pixmap and not cached_pixmap.isNull():
            self._on_thumbnail_ready(file_path, cached_pixmap, from_cache=True)
            return True
        return False

    def get_current_pixmap(self) -> Optional[QPixmap]:
        """Get current pixmap."""
        return self._pixmap

    def get_current_state(self) -> TileState:
        """Get current state."""
        return self._current_state

    def get_memory_usage_bytes(self) -> int:
        """Get memory usage in bytes."""
        return self._memory_usage_bytes

    def is_memory_usage_acceptable(self) -> bool:
        """Check if memory usage is acceptable."""
        return self._memory_usage_bytes < 50 * 1024 * 1024  # 50MB limit

    def cleanup(self):
        """Enhanced cleanup z memory pressure disconnect."""
        if self._is_disposed:
            return

        self._is_disposed = True

        # Disconnect memory pressure signals
        try:
            from src.ui.widgets.tile_async_ui_manager import get_async_ui_manager
            from src.ui.widgets.tile_cache_optimizer import get_cache_optimizer

            cache_optimizer = get_cache_optimizer()
            cache_optimizer.memory_pressure_detected.disconnect(
                self._on_memory_pressure
            )

            async_manager = get_async_ui_manager()
            async_manager.performance_warning.disconnect(self._on_performance_warning)

        except Exception:
            pass

        # Cleanup worker manager
        if hasattr(self, "_worker_manager"):
            self._worker_manager.cleanup()

        # Clear caches
        if hasattr(self, "_scaled_pixmap_cache"):
            self._scaled_pixmap_cache.clear()

        # Cancel current loading
        if self._is_loading:
            self._cancel_current_loading()

        # Resource manager cleanup
        if self._resource_manager_worker_id is not None:
            try:
                from src.ui.widgets.tile_resource_manager import get_resource_manager

                resource_manager = get_resource_manager()
                resource_manager.unregister_worker(self._resource_manager_worker_id)
                self._resource_manager_worker_id = None
            except Exception as e:
                logger.debug(
                    f"Failed to unregister resource manager worker during cleanup: {e}"
                )

        # Clear pixmaps
        self._pixmap = None
        self._original_pixmap = None
        self._memory_usage_bytes = 0

        # Stop timers
        if hasattr(self, "_resize_timer"):
            self._resize_timer.stop()

        # Unsubscribe from event bus
        if self.event_bus:
            self.event_bus.unsubscribe(
                TileEvent.THUMBNAIL_LOADED, self._on_external_thumbnail_loaded
            )
            self.event_bus.unsubscribe(
                TileEvent.THUMBNAIL_ERROR, self._on_external_thumbnail_error
            )
            self.event_bus.unsubscribe(TileEvent.STATE_CHANGED, self._set_state)

        # Set final state
        self._set_state(TileState.DISPOSED)

        if self.config.enable_debug_logging:
            logger.debug("ThumbnailComponent cleaned up")

    def get_debug_info(self) -> Dict[str, Any]:
        """Enhanced debug info z memory pressure data."""
        base_info = {
            "current_state": self._current_state.name,
            "current_path": self._current_path,
            "current_size": self._current_size,
            "is_loading": self._is_loading,
            "is_disposed": self._is_disposed,
            "memory_usage_bytes": self._memory_usage_bytes,
            "has_pixmap": self._pixmap is not None,
            "has_original_pixmap": self._original_pixmap is not None,
        }

        # Add memory pressure info
        cache_stats = self._scaled_pixmap_cache.get_stats()
        worker_stats = self._worker_manager.get_stats()

        base_info.update(
            {
                "memory_pressure_level": self._memory_pressure_level,
                "scaled_cache_stats": cache_stats,
                "worker_stats": worker_stats,
                "original_pixmap_size_mb": (
                    self._estimate_pixmap_size(self._original_pixmap) / (1024 * 1024)
                    if self._original_pixmap
                    else 0
                ),
            }
        )

        return base_info

    def _is_object_valid(self) -> bool:
        """Check if Qt object is still valid."""
        try:
            # Check if object is still valid
            if not self or self._is_disposed:
                return False

            # Check if parent is still valid (if any)
            if self.parent() and not self.parent().isWidgetType():
                return False

            return True

        except Exception:
            return False

    def _estimate_pixmap_size(self, pixmap: Optional[QPixmap]) -> int:
        """Estimate pixmap memory usage."""
        if not pixmap or pixmap.isNull():
            return 0
        return pixmap.width() * pixmap.height() * 4  # RGBA


def create_thumbnail_component(
    config: TileConfig, event_bus: TileEventBus, parent: Optional[QObject] = None
) -> ThumbnailComponent:
    """
    Factory function dla ThumbnailComponent.

    Args:
        config: Konfiguracja komponentu
        event_bus: Event bus dla komunikacji
        parent: Parent Qt object

    Returns:
        ThumbnailComponent: Nowy komponent thumbnail
    """
    return ThumbnailComponent(config, event_bus, parent)
