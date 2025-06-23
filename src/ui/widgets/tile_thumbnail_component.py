"""
ETAP 3: THUMBNAIL COMPONENT - Wydzielony komponent thumbnail
Separuje logikę ładowania miniaturek od głównej klasy FileTileWidget.
"""

import asyncio
import logging
import weakref
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
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

        # OPTYMALIZACJA: Cache dla różnych rozmiarów tej samej miniaturki
        self._scaled_pixmap_cache: Dict[Tuple[int, int], QPixmap] = {}
        self._original_pixmap: Optional[QPixmap] = None  # Cache oryginalnej miniaturki

        # Worker management
        self._current_worker_id: int = 0
        self._load_worker: Optional[object] = None
        self._resource_manager_worker_id: Optional[int] = None  # Resource management

        # Timers for debouncing
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(self.config.debounce_delay_ms)
        self._resize_timer.timeout.connect(self._on_resize_timer)

        # Setup connections
        self._setup_connections()

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

        if not file_path or not Path(file_path).exists():
            self._emit_error(f"File does not exist: {file_path}")
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

        # Check cache first
        if self._try_load_from_cache(file_path, target_size):
            return True

        # Start loading
        self._set_state(TileState.LOADING)
        self._is_loading = True

        # Choose loading method
        if self.config.async_loading:
            return self._start_async_loading(file_path, target_size)
        else:
            return self._start_sync_loading(file_path, target_size)

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

        if self.config.enable_debug_logging:
            logger.debug(f"Applying size change: {self._current_size} -> {new_size}")

        # OPTYMALIZACJA: Sprawdź czy mamy cached skalowaną wersję
        if new_size in self._scaled_pixmap_cache:
            cached_pixmap = self._scaled_pixmap_cache[new_size]
            self._pixmap = cached_pixmap
            self._current_size = new_size
            self._set_state(TileState.READY)
            self.thumbnail_loaded.emit(self._current_path, cached_pixmap)
            if self.config.enable_debug_logging:
                logger.debug(f"Used cached scaled pixmap for size {new_size}")
            return

        # OPTYMALIZACJA: Jeśli mamy oryginalną miniaturkę, skaluj ją zamiast ładować z dysku
        if self._original_pixmap and not self._original_pixmap.isNull():
            scaled_pixmap = self._original_pixmap.scaled(
                new_size[0],
                new_size[1],
                aspectRatioMode=1,  # KeepAspectRatio
                transformMode=1,  # SmoothTransformation
            )

            # Cache skalowaną wersję
            self._scaled_pixmap_cache[new_size] = scaled_pixmap
            self._pixmap = scaled_pixmap
            self._current_size = new_size
            self._set_state(TileState.READY)
            self.thumbnail_loaded.emit(self._current_path, scaled_pixmap)

            if self.config.enable_debug_logging:
                logger.debug(f"Scaled original pixmap to {new_size}")
            return

        # Fallback: Przeładuj z dysku tylko jeśli nie mamy cache
        if self._current_path:
            self.load_thumbnail(self._current_path, new_size)

    def _start_async_loading(self, file_path: str, size: Tuple[int, int]) -> bool:
        """Start asynchronous thumbnail loading."""
        try:
            # Import thumbnail worker
            from src.ui.widgets.thumbnail_cache import ThumbnailCache

            # Get from cache first
            cache = ThumbnailCache.get_instance()
            cached_pixmap = cache.get_thumbnail(file_path, size[0], size[1])

            if cached_pixmap:
                self._on_thumbnail_ready(file_path, cached_pixmap, from_cache=True)
                return True

            # Start worker for loading
            return self._start_worker_loading(file_path, size)

        except Exception as e:
            self._emit_error(f"Failed to start async loading: {e}")
            return False

    def _start_sync_loading(self, file_path: str, size: Tuple[int, int]) -> bool:
        """Start synchronous thumbnail loading."""
        try:
            # Direct loading for testing/simple cases
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # Scale pixmap
                scaled_pixmap = pixmap.scaled(
                    size[0],
                    size[1],
                    aspectRatioMode=1,  # KeepAspectRatio
                    transformMode=1,  # SmoothTransformation
                )
                self._on_thumbnail_ready(file_path, scaled_pixmap, from_cache=False)
                return True
            else:
                self._emit_error(f"Failed to load pixmap: {file_path}")
                return False

        except Exception as e:
            self._emit_error(f"Sync loading failed: {e}")
            return False

    def _start_worker_loading(self, file_path: str, size: Tuple[int, int]) -> bool:
        """Start worker-based thumbnail loading."""
        try:
            # Import worker classes
            from src.ui.delegates.workers.processing_workers import (
                ThumbnailGenerationWorker,
            )

            # Create worker
            self._current_worker_id += 1
            worker_id = self._current_worker_id

            worker = ThumbnailGenerationWorker(file_path, size[0], size[1])

            # Connect worker signals
            worker.signals.thumbnail_finished.connect(
                lambda pixmap, path, w, h: self._on_worker_thumbnail_ready(
                    worker_id, path, pixmap
                )
            )
            worker.signals.thumbnail_error.connect(
                lambda msg, path, w, h: self._on_worker_thumbnail_error(
                    worker_id, msg, path
                )
            )

            # Store worker reference
            self._load_worker = worker

            # Start worker in thread pool
            from PyQt6.QtCore import QThreadPool

            QThreadPool.globalInstance().start(worker)

            if self.config.enable_debug_logging:
                logger.debug(f"Started worker {worker_id} for {file_path}")

            return True

        except Exception as e:
            self._emit_error(f"Failed to start worker: {e}")
            return False

    def _on_worker_thumbnail_ready(self, worker_id: int, path: str, pixmap: QPixmap):
        """Callback gdy worker završí loading."""
        # NAPRAWKA: Sprawdź czy obiekt Qt nie został usunięty
        if not self._is_object_valid():
            return

        # Check if this is current worker
        if worker_id != self._current_worker_id:
            if self.config.enable_debug_logging:
                logger.debug(f"Ignoring outdated worker {worker_id} result")
            return

        self._on_thumbnail_ready(path, pixmap, from_cache=False)

    def _on_worker_thumbnail_error(self, worker_id: int, error_msg: str, path: str):
        """Callback gdy worker ma błąd."""
        # NAPRAWKA: Sprawdź czy obiekt Qt nie został usunięty
        if not self._is_object_valid():
            return

        # Check if this is current worker
        if worker_id != self._current_worker_id:
            return

        self._emit_error(f"Worker error: {error_msg}")

    def _on_thumbnail_ready(self, path: str, pixmap: QPixmap, from_cache: bool = False):
        """Callback gdy miniatura jest gotowa - z cache optymalizacją."""
        # NAPRAWKA: Sprawdź czy obiekt Qt nie został usunięty
        if not self._is_object_valid():
            return

        if path != self._current_path:
            # Outdated result
            return

        # OPTYMALIZACJA: Cache oryginalną miniaturkę dla przyszłych skalowań
        if not self._original_pixmap or self._original_pixmap.isNull():
            self._original_pixmap = pixmap
            if self.config.enable_debug_logging:
                logger.debug(f"Cached original pixmap for {path}")

        # Store pixmap
        self._pixmap = pixmap

        # OPTYMALIZACJA: Cache obecny rozmiar
        if self._current_size and self._current_size != (0, 0):
            self._scaled_pixmap_cache[self._current_size] = pixmap

        # Calculate memory usage
        if pixmap:
            self._memory_usage_bytes = pixmap.width() * pixmap.height() * 4  # RGBA

        # Update state
        self._set_state(TileState.READY)

        # Emit signals - tylko jeśli obiekt Qt nadal istnieje
        if self._is_object_valid():
            self.thumbnail_loaded.emit(path, pixmap)

        # Emit via event bus
        if self.event_bus:
            self.event_bus.emit_event(TileEvent.THUMBNAIL_LOADED, path, pixmap)

        if self.config.enable_debug_logging:
            cache_status = "cache" if from_cache else "loaded"
            memory_mb = self._memory_usage_bytes / 1024 / 1024
            logger.debug(
                f"Thumbnail ready ({cache_status}): {path}, memory: {memory_mb:.1f}MB"
            )

    def _cancel_current_loading(self):
        """Anuluje obecne ładowanie."""
        if self._is_loading and self._load_worker:
            # Cancel worker
            self._current_worker_id += 1  # Invalidate current worker
            self._load_worker = None

            if self.config.enable_debug_logging:
                logger.debug("Cancelled current loading")

        self._is_loading = False

    def _emit_error(self, error_message: str):
        """Emit error z zabezpieczeniem przed usuniętymi obiektami Qt."""
        # NAPRAWKA: Sprawdź czy obiekt Qt nie został usunięty
        if not self._is_object_valid():
            return

        self._set_state(TileState.ERROR)

        # Emit signals - tylko jeśli obiekt Qt nadal istnieje
        if self._is_object_valid():
            self.thumbnail_error.emit(self._current_path or "", error_message)

        if self.event_bus:
            self.event_bus.emit_event(
                TileEvent.THUMBNAIL_ERROR, self._current_path or "", error_message
            )

        logger.error(f"Thumbnail error: {error_message}")

    def _set_state(self, new_state: TileState):
        """Set new state z zabezpieczeniem przed usuniętymi obiektami Qt."""
        # NAPRAWKA: Sprawdź czy obiekt Qt nie został usunięty
        if not self._is_object_valid():
            return

        if new_state != self._current_state:
            self._current_state = new_state

            # Emit signal - tylko jeśli obiekt Qt nadal istnieje
            if self._is_object_valid():
                self.state_changed.emit(new_state)

            if self.event_bus:
                self.event_bus.emit_event(TileEvent.STATE_CHANGED, new_state)

            if self.config.enable_debug_logging:
                logger.debug(
                    f"State changed: {self._current_state.name} -> {new_state.name}"
                )

    def _on_thumbnail_loaded(self, path: str, pixmap: QPixmap):
        """Callback dla internal thumbnail loaded signal."""
        pass  # Override in subclasses if needed

    def _on_thumbnail_error(self, path: str, error_message: str):
        """Callback dla internal thumbnail error signal."""
        pass  # Override in subclasses if needed

    def _on_external_thumbnail_loaded(self, path: str, pixmap: QPixmap):
        """Callback z external event bus."""
        # NAPRAWKA: Sprawdź czy obiekt Qt nie został usunięty
        if not self._is_object_valid():
            return

        if path == self._current_path and not self._pixmap:
            self._on_thumbnail_ready(path, pixmap, from_cache=True)

    def _on_external_thumbnail_error(self, path: str, error_message: str):
        """Callback z external event bus."""
        # NAPRAWKA: Sprawdź czy obiekt Qt nie został usunięty
        if not self._is_object_valid():
            return

        if path == self._current_path:
            self._emit_error(f"External error: {error_message}")

    def _try_load_from_cache(self, file_path: str, size: Tuple[int, int]) -> bool:
        """
        Próbuje załadować miniaturę z cache.

        Args:
            file_path: Ścieżka do pliku
            size: Rozmiar miniatury

        Returns:
            bool: True jeśli znaleziono w cache
        """
        # Na razie brak cache - można rozszerzyć w przyszłości
        # TODO: Integracja z thumbnail cache system
        return False

    # === PUBLIC API ===

    def get_current_pixmap(self) -> Optional[QPixmap]:
        """Zwraca obecną miniaturę."""
        return self._pixmap

    def get_current_state(self) -> TileState:
        """Zwraca obecny stan komponentu."""
        return self._current_state

    def get_memory_usage_bytes(self) -> int:
        """Zwraca aktalne memory usage w bajtach."""
        return self._memory_usage_bytes

    def is_memory_usage_acceptable(self) -> bool:
        """Sprawdza czy memory usage jest w akceptowalnych granicach."""
        return self.config.is_memory_usage_acceptable(self._memory_usage_bytes)

    def cleanup(self):
        """Cleanup komponentu - usuwa wszystkie zasoby."""
        self._cancel_current_loading()

        # Odłącz sygnały
        try:
            self.thumbnail_loaded.disconnect()
        except Exception:
            pass
        try:
            self.thumbnail_error.disconnect()
        except Exception:
            pass
        try:
            self.state_changed.disconnect()
        except Exception:
            pass
        # Odsubskrybuj z event_bus
        if self.event_bus:
            try:
                self.event_bus.unsubscribe(
                    TileEvent.THUMBNAIL_LOADED, self._on_external_thumbnail_loaded
                )
            except Exception:
                pass
            try:
                self.event_bus.unsubscribe(
                    TileEvent.THUMBNAIL_ERROR, self._on_external_thumbnail_error
                )
            except Exception:
                pass
            try:
                self.event_bus.unsubscribe(TileEvent.STATE_CHANGED, self._set_state)
            except Exception:
                pass

        # Clear pixmap
        self._pixmap = None
        self._memory_usage_bytes = 0

        # Stop timers
        if self._resize_timer.isActive():
            self._resize_timer.stop()

        # Cleanup resource manager worker
        if self._resource_manager_worker_id is not None:
            try:
                from src.ui.widgets.tile_resource_manager import get_resource_manager

                resource_manager = get_resource_manager()
                resource_manager.unregister_worker(self._resource_manager_worker_id)
                self._resource_manager_worker_id = None
                if self.config.enable_debug_logging:
                    logger.debug("Resource manager worker unregistered")
            except Exception as e:
                logger.warning(f"Failed to unregister resource manager worker: {e}")

        # Clear state
        self._current_path = None
        self._current_size = (0, 0)
        self._set_state(TileState.DISPOSED)
        self._is_disposed = True

        if self.config.enable_debug_logging:
            logger.debug("ThumbnailComponent cleaned up")

    def get_debug_info(self) -> Dict[str, Any]:
        """Zwraca informacje debug o komponencie."""
        return {
            "current_state": self._current_state.name,
            "current_path": self._current_path,
            "current_size": self._current_size,
            "memory_usage_mb": self._memory_usage_bytes / 1024 / 1024,
            "memory_acceptable": self.is_memory_usage_acceptable(),
            "is_loading": self._is_loading,
            "worker_id": self._current_worker_id,
            "config_async": self.config.async_loading,
        }

    def _is_object_valid(self) -> bool:
        """Sprawdza czy obiekt Qt nadal istnieje i można z nim komunikować."""
        try:
            # Sprawdź flagę disposed
            if getattr(self, "_is_disposed", False):
                return False

            # NAPRAWKA: Sprawdź czy obiekt Qt nadal istnieje
            try:
                # Spróbuj uzyskać dostęp do basic Qt property
                _ = self.objectName()
                return True
            except RuntimeError as e:
                if "wrapped C/C++ object" in str(e) or "has been deleted" in str(e):
                    # Obiekt Qt został usunięty - mark as disposed
                    self._is_disposed = True
                    return False
                raise  # Inny błąd RuntimeError

        except Exception:
            return False


# === FACTORY FUNCTIONS ===


def create_thumbnail_component(
    config: TileConfig, event_bus: TileEventBus, parent: Optional[QObject] = None
) -> ThumbnailComponent:
    """
    Factory function dla tworzenia thumbnail component.

    Args:
        config: Konfiguracja kafelka
        event_bus: Event bus dla komunikacji
        parent: Parent QObject

    Returns:
        ThumbnailComponent: Skonfigurowany komponent
    """
    return ThumbnailComponent(config, event_bus, parent)
