"""
ETAP 3: THUMBNAIL COMPONENT - Wydzielenie logiki miniaturek
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap

from src.ui.widgets.tile_config import TileConfig, TileEvent, TileState
from src.ui.widgets.tile_event_bus import TileEventBus

logger = logging.getLogger(__name__)


class ThumbnailComponent(QObject):
    """Komponent zarządzania miniaturkami dla FileTileWidget."""

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
        self._current_state = TileState.INITIALIZING
        self._current_path: Optional[str] = None
        self._current_size: Tuple[int, int] = (0, 0)
        self._pixmap: Optional[QPixmap] = None

        # Debouncing timer
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._on_resize_timer)
        self._pending_size: Optional[Tuple[int, int]] = None

        # Loading state
        self._is_loading = False
        self._current_worker_id = 0

        # Memory tracking
        self._memory_usage_bytes = 0

        logger.debug("ThumbnailComponent created")

    def load_thumbnail(
        self, file_path: str, size: Optional[Tuple[int, int]] = None
    ) -> bool:
        """Ładuj miniaturę pliku."""
        if not file_path or not Path(file_path).exists():
            self._emit_error(f"File does not exist: {file_path}")
            return False

        # Use config size if not provided
        if size is None:
            calculated_size = self.config.get_calculated_thumbnail_dimension()
            size = (calculated_size, calculated_size)

        # Check if already loaded
        if (
            self._current_path == file_path
            and self._current_size == size
            and self._pixmap is not None
        ):
            return True

        # Update state
        self._current_path = file_path
        self._current_size = size
        self._set_state(TileState.LOADING_THUMBNAIL)

        # Load thumbnail
        if self.config.async_loading:
            return self._start_async_loading(file_path, size)
        else:
            return self._start_sync_loading(file_path, size)

    def set_thumbnail_size(self, size: Tuple[int, int], immediate: bool = False):
        """Ustaw nowy rozmiar z debouncing."""
        if size == self._current_size:
            return

        self._pending_size = size

        if immediate:
            self._apply_size_change()
        else:
            self._resize_timer.start(self.config.debounce_interval_ms)

    def _on_resize_timer(self):
        """Callback resize timer."""
        if self._pending_size:
            self._apply_size_change()

    def _apply_size_change(self):
        """Aplikuj zmianę rozmiaru."""
        if not self._pending_size:
            return

        new_size = self._pending_size
        self._pending_size = None

        if self._current_path:
            self.load_thumbnail(self._current_path, new_size)

    def _start_async_loading(self, file_path: str, size: Tuple[int, int]) -> bool:
        """Start async loading."""
        try:
            # Check cache first
            from src.ui.widgets.thumbnail_cache import ThumbnailCache

            cache = ThumbnailCache.get_instance()
            cached_pixmap = cache.get_thumbnail(file_path, size[0], size[1])

            if cached_pixmap:
                self._on_thumbnail_ready(file_path, cached_pixmap)
                return True

            # Start worker loading
            return self._start_worker_loading(file_path, size)

        except Exception as e:
            self._emit_error(f"Async loading failed: {e}")
            return False

    def _start_sync_loading(self, file_path: str, size: Tuple[int, int]) -> bool:
        """Start sync loading."""
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    size[0], size[1], 1, 1  # KeepAspectRatio, SmoothTransformation
                )
                self._on_thumbnail_ready(file_path, scaled_pixmap)
                return True
            else:
                self._emit_error(f"Failed to load: {file_path}")
                return False

        except Exception as e:
            self._emit_error(f"Sync loading failed: {e}")
            return False

    def _start_worker_loading(self, file_path: str, size: Tuple[int, int]) -> bool:
        """Start worker loading."""
        try:
            # Use existing worker system
            from PyQt6.QtCore import QThreadPool

            from src.ui.delegates.workers.processing_workers import (
                ThumbnailGenerationWorker,
            )

            self._current_worker_id += 1
            worker_id = self._current_worker_id

            worker = ThumbnailGenerationWorker(file_path, size[0], size[1])

            # Connect signals
            worker.signals.thumbnail_finished.connect(
                lambda pixmap, path, w, h: self._on_thumbnail_ready(path, pixmap)
            )
            worker.signals.thumbnail_error.connect(
                lambda msg, path, w, h: self._on_worker_error(worker_id, msg)
            )

            QThreadPool.globalInstance().start(worker)
            return True

        except Exception as e:
            self._emit_error(f"Worker failed: {e}")
            return False

    def _on_worker_ready(self, worker_id: int, path: str, pixmap: QPixmap):
        """Worker ready callback."""
        if worker_id != self._current_worker_id:
            return  # Outdated worker

        self._on_thumbnail_ready(path, pixmap)

    def _on_worker_error(self, worker_id: int, error_msg: str):
        """Worker error callback."""
        if worker_id != self._current_worker_id:
            return

        self._emit_error(f"Worker error: {error_msg}")

    def _on_thumbnail_ready(self, path: str, pixmap: QPixmap):
        """Thumbnail ready callback."""
        if path != self._current_path:
            return  # Outdated

        self._pixmap = pixmap

        if pixmap:
            self._memory_usage_bytes = pixmap.width() * pixmap.height() * 4

        self._set_state(TileState.READY)

        # Emit signals
        self.thumbnail_loaded.emit(path, pixmap)

        if self.event_bus:
            self.event_bus.emit_event(TileEvent.THUMBNAIL_LOADED, path, pixmap)

    def _emit_error(self, error_message: str):
        """Emit error."""
        self._set_state(TileState.ERROR)

        self.thumbnail_error.emit(self._current_path or "", error_message)

        if self.event_bus:
            self.event_bus.emit_event(
                TileEvent.THUMBNAIL_ERROR, self._current_path or "", error_message
            )

    def _set_state(self, new_state: TileState):
        """Set new state."""
        if new_state != self._current_state:
            self._current_state = new_state
            self.state_changed.emit(new_state)

            if self.event_bus:
                self.event_bus.emit_event(TileEvent.STATE_CHANGED, new_state)

    # Public API
    def get_current_pixmap(self) -> Optional[QPixmap]:
        """Get current pixmap."""
        return self._pixmap

    def get_current_state(self) -> TileState:
        """Get current state."""
        return self._current_state

    def get_memory_usage_bytes(self) -> int:
        """Get memory usage."""
        return self._memory_usage_bytes

    def cleanup(self):
        """Cleanup component."""
        self._pixmap = None
        self._memory_usage_bytes = 0
        self._current_path = None
        self._current_size = (0, 0)
        self._set_state(TileState.DISPOSED)

        if self._resize_timer.isActive():
            self._resize_timer.stop()


def create_thumbnail_component(
    config: TileConfig, event_bus: TileEventBus, parent: Optional[QObject] = None
) -> ThumbnailComponent:
    """Factory dla thumbnail component."""
    return ThumbnailComponent(config, event_bus, parent)
