"""
ETAP 7: RESOURCE MANAGEMENT - TileResourceManager
Inteligentne zarządzanie zasobami dla komponentów FileTileWidget.
"""

import gc
import logging
import threading
import time
import weakref
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from weakref import WeakSet

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

# ETAP 8: PERFORMANCE OPTIMIZATION - Integration


@dataclass
class MemoryUsageStats:
    """Statystyki użycia pamięci."""

    total_tiles: int = 0
    active_tiles: int = 0
    memory_per_tile_mb: float = 0.0
    total_memory_mb: float = 0.0
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_ratio: float = 0.0
    worker_count: int = 0
    timestamp: float = 0.0


@dataclass
class ResourceLimits:
    """Limity zasobów dla systemu z enhanced validation."""

    max_tiles: int = 1000
    max_memory_mb: int = 4000
    max_memory_per_tile_mb: int = 10
    max_concurrent_workers: int = 8
    cleanup_interval_seconds: int = 180
    memory_check_interval_seconds: int = 120
    cache_cleanup_threshold_ratio: float = 0.7

    def __post_init__(self):
        """NAPRAWKA: Enhanced validation z sensible defaults."""
        # Validate and correct limits
        if self.max_tiles <= 0:
            logger.warning("Invalid max_tiles, setting to default 1000")
            self.max_tiles = 1000
        elif self.max_tiles > 10000:
            logger.warning("max_tiles too high, capping at 10000")
            self.max_tiles = 10000

        if self.max_memory_mb <= 0:
            logger.warning("Invalid max_memory_mb, setting to default 4000")
            self.max_memory_mb = 4000
        elif self.max_memory_mb > 32000:  # 32GB limit
            logger.warning("max_memory_mb too high, capping at 32000")
            self.max_memory_mb = 32000

        if self.max_memory_per_tile_mb <= 0:
            logger.warning("Invalid max_memory_per_tile_mb, setting to default 10")
            self.max_memory_per_tile_mb = 10
        elif self.max_memory_per_tile_mb > 100:
            logger.warning("max_memory_per_tile_mb too high, capping at 100")
            self.max_memory_per_tile_mb = 100

        if self.max_concurrent_workers <= 0:
            logger.warning("Invalid max_concurrent_workers, setting to default 8")
            self.max_concurrent_workers = 8
        elif self.max_concurrent_workers > 32:
            logger.warning("max_concurrent_workers too high, capping at 32")
            self.max_concurrent_workers = 32

        if self.cleanup_interval_seconds < 30:
            logger.warning("cleanup_interval_seconds too low, setting to minimum 30")
            self.cleanup_interval_seconds = 30
        elif self.cleanup_interval_seconds > 3600:
            logger.warning("cleanup_interval_seconds too high, capping at 3600")
            self.cleanup_interval_seconds = 3600

        if self.memory_check_interval_seconds < 5:
            logger.warning(
                "memory_check_interval_seconds too low, setting to minimum 5"
            )
            self.memory_check_interval_seconds = 5
        elif self.memory_check_interval_seconds > 300:
            logger.warning("memory_check_interval_seconds too high, capping at 300")
            self.memory_check_interval_seconds = 300

        if self.cache_cleanup_threshold_ratio < 0.1:
            logger.warning(
                "cache_cleanup_threshold_ratio too low, setting to minimum 0.1"
            )
            self.cache_cleanup_threshold_ratio = 0.1
        elif self.cache_cleanup_threshold_ratio > 0.9:
            logger.warning("cache_cleanup_threshold_ratio too high, capping at 0.9")
            self.cache_cleanup_threshold_ratio = 0.9

        logger.debug(f"ResourceLimits validated: {self}")


class MemoryMonitor(QObject):
    """Monitor użycia pamięci z alertami i adaptive optimization."""

    # Sygnały
    memory_warning = pyqtSignal(str, float)  # message, usage_mb
    memory_critical = pyqtSignal(str, float)
    cleanup_needed = pyqtSignal()

    def __init__(self, limits: ResourceLimits):
        super().__init__()
        self.limits = limits
        self._last_check_time = 0
        self._memory_history: List[float] = []
        self._max_history = 100

        # NAPRAWKA: Adaptive memory monitoring
        self._check_interval = limits.memory_check_interval_seconds
        self._last_memory_mb = 0.0
        self._memory_trend = "stable"
        self._consecutive_high_usage = 0
        self._adaptive_mode = False

        # Timer dla periodic checks
        self._check_timer = QTimer()
        self._check_timer.timeout.connect(self._check_memory_usage)
        self._check_timer.start(self._check_interval * 1000)

        logger.debug(f"MemoryMonitor initialized with adaptive limits: {limits}")

    def _check_memory_usage(self):
        """Sprawdza aktuelne usage i emituje alerty z adaptive optimization."""
        try:
            import psutil

            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            # NAPRAWKA: Adaptive check interval based on memory trend
            self._update_adaptive_interval(memory_mb)

            # Dodaj do historii
            self._memory_history.append(memory_mb)
            if len(self._memory_history) > self._max_history:
                self._memory_history.pop(0)

            # Sprawdź limity
            warning_threshold = self.limits.max_memory_mb * 0.8  # Warning przy 80%
            critical_threshold = self.limits.max_memory_mb * 0.95  # Critical przy 95%

            if memory_mb > critical_threshold:
                self._consecutive_high_usage += 1
                self.memory_critical.emit(
                    f"Critical memory usage: {memory_mb:.1f}MB", memory_mb
                )
                self.cleanup_needed.emit()
            elif memory_mb > warning_threshold:
                self._consecutive_high_usage += 1
                self.memory_warning.emit(
                    f"High memory usage: {memory_mb:.1f}MB", memory_mb
                )
            else:
                self._consecutive_high_usage = 0

            self._last_memory_mb = memory_mb
            self._last_check_time = time.time()

        except ImportError:
            logger.warning("psutil not available for memory monitoring")
        except Exception as e:
            logger.error(f"Memory check error: {e}")

    def _update_adaptive_interval(self, current_memory_mb: float):
        """NAPRAWKA: Adaptive check interval based on memory pressure."""
        if len(self._memory_history) < 3:
            return

        # Calculate trend
        recent = self._memory_history[-3:]
        if recent[-1] > recent[0] * 1.05:  # 5% increase
            self._memory_trend = "increasing"
        elif recent[-1] < recent[0] * 0.95:  # 5% decrease
            self._memory_trend = "decreasing"
        else:
            self._memory_trend = "stable"

        # Adjust interval based on conditions
        base_interval = self.limits.memory_check_interval_seconds

        if self._consecutive_high_usage >= 3:
            # High pressure - check more frequently
            new_interval = max(5, base_interval // 3)  # Min 5s
            self._adaptive_mode = True
        elif self._memory_trend == "increasing":
            # Memory growing - moderate frequency
            new_interval = max(10, base_interval // 2)  # Min 10s
            self._adaptive_mode = True
        elif self._memory_trend == "stable" and self._adaptive_mode:
            # Return to normal if stable
            new_interval = base_interval
            self._adaptive_mode = False
        else:
            new_interval = base_interval

        # Update timer if interval changed
        if new_interval != self._check_interval:
            self._check_interval = new_interval
            self._check_timer.setInterval(new_interval * 1000)
            logger.debug(f"Memory check interval adjusted to {new_interval}s")

    def cleanup(self):
        """NAPRAWKA: Proper cleanup dla timer leak prevention."""
        if hasattr(self, "_check_timer"):
            self._check_timer.stop()
            self._check_timer.deleteLater()
            logger.debug("MemoryMonitor timer cleaned up")

    def get_memory_trend(self) -> str:
        """Zwraca trend użycia pamięci."""
        return self._memory_trend

    def get_current_memory_mb(self) -> float:
        """Zwraca aktuelne usage w MB."""
        try:
            import psutil

            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
        except Exception:
            return 0.0


class WorkerPoolManager:
    """Zarządzanie pulą workerów dla thumbnail loading."""

    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self._active_workers: Set[int] = set()
        self._worker_counter = 0
        self._lock = threading.RLock()

        logger.debug(f"WorkerPoolManager initialized with max_workers: {max_workers}")

    def can_start_worker(self) -> bool:
        """Sprawdza czy można uruchomić nowego workera."""
        with self._lock:
            return len(self._active_workers) < self.max_workers

    def register_worker(self) -> Optional[int]:
        """Rejestruje nowego workera. Zwraca worker_id lub None jeśli limit."""
        with self._lock:
            if not self.can_start_worker():
                return None

            self._worker_counter += 1
            worker_id = self._worker_counter
            self._active_workers.add(worker_id)

            logger.debug(
                f"Registered worker {worker_id}, active: {len(self._active_workers)}"
            )
            return worker_id

    def unregister_worker(self, worker_id: int):
        """Wyrejestrowuje workera."""
        with self._lock:
            self._active_workers.discard(worker_id)
            logger.debug(
                f"Unregistered worker {worker_id}, active: {len(self._active_workers)}"
            )

    def get_active_count(self) -> int:
        """Zwraca liczbę aktywnych workerów."""
        with self._lock:
            return len(self._active_workers)

    def force_cleanup(self):
        """Wymuś cleanup wszystkich workerów."""
        with self._lock:
            logger.warning(f"Force cleanup of {len(self._active_workers)} workers")
            self._active_workers.clear()


class TileResourceManager(QObject):
    """
    Centralny manager zasobów dla FileTileWidget komponentów.

    Odpowiedzialności:
    - Śledzenie aktywnych tiles i komponentów
    - Memory monitoring i automatic cleanup
    - Worker pool management
    - Cache coordination
    - Resource limits enforcement
    """

    # Sygnały
    resource_warning = pyqtSignal(str)
    cleanup_performed = pyqtSignal(int)  # liczba wyczyszczonych elementów
    stats_updated = pyqtSignal(object)  # MemoryUsageStats

    def __init__(self, limits: Optional[ResourceLimits] = None):
        super().__init__()

        self.limits = limits or ResourceLimits()

        # ETAP 8: Performance optimization components
        self._performance_monitor = None
        self._cache_optimizer = None
        self._async_ui_manager = None
        self._performance_enabled = True

        # Aktywne tile'y i komponenty (weak references)
        self._active_tiles: WeakSet = WeakSet()
        self._active_components: Dict[str, WeakSet] = {
            "thumbnail": WeakSet(),
            "metadata": WeakSet(),
            "interaction": WeakSet(),
            "event_bus": WeakSet(),
        }

        # Managers
        self._memory_monitor = MemoryMonitor(self.limits)
        self._worker_pool = WorkerPoolManager(self.limits.max_concurrent_workers)

        # Threading
        self._lock = threading.RLock()

        # Cleanup timer
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self.perform_cleanup)
        self._cleanup_timer.start(self.limits.cleanup_interval_seconds * 1000)

        # Statystyki
        self._stats_history: List[MemoryUsageStats] = []
        self._last_cleanup_time = time.time()

        # Sygnały memory monitor
        self._memory_monitor.memory_warning.connect(self._on_memory_warning)
        self._memory_monitor.memory_critical.connect(self._on_memory_critical)
        self._memory_monitor.cleanup_needed.connect(self.perform_emergency_cleanup)

        logger.info(f"TileResourceManager initialized with limits: {self.limits}")

        # Initialize performance components
        self._initialize_performance_components()

    # === PERFORMANCE OPTIMIZATION ===

    def _initialize_performance_components(self):
        """Inicjalizuje komponenty performance optimization z enhanced error handling."""
        if not self._performance_enabled:
            return

        # NAPRAWKA: Enhanced error handling z retry mechanisms
        max_retries = 3
        retry_delay = 0.1  # 100ms

        for attempt in range(max_retries):
            try:
                # Import performance components (lazy loading)
                from .tile_async_ui_manager import get_async_ui_manager
                from .tile_cache_optimizer import get_cache_optimizer
                from .tile_performance_monitor import get_performance_monitor

                # Initialize components z proper error handling
                self._performance_monitor = get_performance_monitor()
                self._cache_optimizer = get_cache_optimizer()
                self._async_ui_manager = get_async_ui_manager()

                logger.debug("Performance components initialized successfully")
                break  # Success - exit retry loop

            except ImportError as e:
                logger.warning(
                    f"Performance component import failed (attempt {attempt + 1}): {e}"
                )
                if attempt == max_retries - 1:
                    logger.error("Failed to import performance components - disabling")
                    self._performance_enabled = False
                else:
                    time.sleep(retry_delay)

            except Exception as e:
                logger.error(
                    f"Performance component initialization error (attempt {attempt + 1}): {e}"
                )
                if attempt == max_retries - 1:
                    logger.error(
                        "Failed to initialize performance components - disabling"
                    )
                    self._performance_enabled = False
                else:
                    time.sleep(retry_delay)

    def get_performance_monitor(self):
        """Zwraca performance monitor."""
        return self._performance_monitor

    def get_cache_optimizer(self):
        """Zwraca cache optimizer."""
        return self._cache_optimizer

    def get_async_ui_manager(self):
        """Zwraca async UI manager."""
        return self._async_ui_manager

    def enable_performance_optimization(self, enabled: bool = True):
        """Włącza/wyłącza performance optimization."""
        self._performance_enabled = enabled

        if enabled and not (
            self._performance_monitor
            and self._cache_optimizer
            and self._async_ui_manager
        ):
            self._initialize_performance_components()
        elif not enabled:
            # Cleanup performance components
            if self._performance_monitor:
                self._performance_monitor.enable_monitoring(False)
            if self._async_ui_manager:
                self._async_ui_manager.cleanup()

        logger.info(f"Performance optimization {'enabled' if enabled else 'disabled'}")

    # === REGISTRATION ===

    def register_tile(self, tile) -> bool:
        """Rejestruje nowy tile widget."""
        with self._lock:
            if len(self._active_tiles) >= self.limits.max_tiles:
                logger.warning(f"Tile limit reached: {self.limits.max_tiles}")
                self.resource_warning.emit(
                    f"Tile limit reached: {self.limits.max_tiles}"
                )
                return False

            self._active_tiles.add(tile)
            logger.debug(f"Registered tile, active count: {len(self._active_tiles)}")
            return True

    def register_component(self, component_type: str, component) -> bool:
        """Rejestruje komponent."""
        if component_type not in self._active_components:
            logger.error(f"Unknown component type: {component_type}")
            return False

        with self._lock:
            self._active_components[component_type].add(component)
            logger.debug(f"Registered {component_type} component")
            return True

    def unregister_tile(self, tile):
        """Wyrejestrowuje tile (automatyczne przez weak reference)."""
        # WeakSet automatycznie usuwa gdy tile zostanie usunięty
        pass

    # === WORKER MANAGEMENT ===

    def can_start_worker(self) -> bool:
        """Sprawdza czy można uruchomić workera."""
        return self._worker_pool.can_start_worker()

    def register_worker(self) -> Optional[int]:
        """Rejestruje nowego workera."""
        return self._worker_pool.register_worker()

    def unregister_worker(self, worker_id: int):
        """Wyrejestrowuje workera."""
        self._worker_pool.unregister_worker(worker_id)

    # === CLEANUP & MONITORING ===

    def perform_cleanup(self):
        """Wykonuje periodic cleanup."""
        with self._lock:
            start_time = time.time()
            cleaned_count = 0

            # Force garbage collection
            collected = gc.collect()
            if collected > 0:
                cleaned_count += collected
                logger.debug(f"Garbage collected {collected} objects")

            # Wymuś cleanup komponentów
            for component_type, component_set in self._active_components.items():
                for component in list(component_set):
                    if hasattr(component, "cleanup"):
                        try:
                            component.cleanup()
                        except Exception as e:
                            logger.warning(f"Component cleanup error: {e}")

            # Update stats
            self._update_statistics()

            cleanup_time = time.time() - start_time
            self._last_cleanup_time = time.time()

            logger.debug(
                f"Cleanup completed in {cleanup_time:.3f}s, cleaned: {cleaned_count}"
            )
            self.cleanup_performed.emit(cleaned_count)

    def perform_emergency_cleanup(self):
        """Wykonuje emergency cleanup przy krytycznym usage - BEZPIECZNY."""
        logger.warning("Performing emergency cleanup due to high memory usage")

        with self._lock:
            start_time = time.time()
            cleaned_count = 0

            # NAPRAWKA: Safe emergency cleanup - nie usuwaj Qt obiektów bezpośrednio
            # Step 1: Regular cleanup first
            self.perform_cleanup()

            # Step 2: Worker pool cleanup
            self._worker_pool.force_cleanup()

            # Step 3: NAPRAWKA: Safe component cleanup bez Qt object removal
            for component_type, component_set in self._active_components.items():
                # NAPRAWKA: Safe iteration over WeakSet
                components_to_cleanup = []
                try:
                    components_to_cleanup = list(component_set)
                except RuntimeError:
                    logger.warning(f"WeakSet iteration failed for {component_type}")
                    continue

                for component in components_to_cleanup:
                    if component is None:
                        continue

                    # NAPRAWKA: Safe cleanup - tylko clear cache, nie usuwaj Qt obiektów
                    try:
                        if hasattr(component, "clear_cache"):
                            component.clear_cache()
                        elif hasattr(component, "clear"):
                            component.clear()
                        # NIE wywołuj component.cleanup() - może usunąć Qt obiekty!
                    except Exception as e:
                        logger.debug(f"Safe component cleanup error: {e}")

            # Step 4: NAPRAWKA: Aggressive garbage collection
            for _ in range(10):  # Zwiększone z 8 na 10
                collected = gc.collect()
                if collected == 0:
                    break  # Brak więcej do zebrania

            # Step 5: NAPRAWKA: Safe performance components cleanup
            if self._performance_enabled:
                try:
                    if self._cache_optimizer:
                        # Tylko clear cache, nie cleanup()
                        if hasattr(self._cache_optimizer, "clear_cache"):
                            self._cache_optimizer.clear_cache()
                        elif hasattr(self._cache_optimizer, "clear"):
                            self._cache_optimizer.clear()

                    if self._async_ui_manager:
                        # Tylko cancel pending tasks, nie cleanup()
                        if hasattr(self._async_ui_manager, "cancel_pending_tasks"):
                            self._async_ui_manager.cancel_pending_tasks()
                except Exception as e:
                    logger.error(f"Performance components safe cleanup error: {e}")

            cleanup_time = time.time() - start_time
            logger.warning(f"Emergency cleanup completed in {cleanup_time:.3f}s")

    def _update_statistics(self):
        """Aktualizuje statystyki użycia z performance optimization."""
        # NAPRAWKA: Performance optimization - cache statistics
        current_time = time.time()

        # Check if we need to update (avoid too frequent updates)
        if (
            hasattr(self, "_last_stats_update")
            and current_time - self._last_stats_update < 2.0
        ):  # Min 2s between updates
            return

        stats = MemoryUsageStats()
        stats.timestamp = current_time

        with self._lock:
            stats.total_tiles = len(self._active_tiles)
            stats.active_tiles = stats.total_tiles  # Wszystkie są aktywne w WeakSet
            stats.worker_count = self._worker_pool.get_active_count()

            # NAPRAWKA: Cached memory stats
            if (
                not hasattr(self, "_cached_memory_mb")
                or current_time - getattr(self, "_last_memory_check", 0) > 5.0
            ):
                stats.total_memory_mb = self._memory_monitor.get_current_memory_mb()
                self._cached_memory_mb = stats.total_memory_mb
                self._last_memory_check = current_time
            else:
                stats.total_memory_mb = self._cached_memory_mb

            if stats.total_tiles > 0:
                stats.memory_per_tile_mb = stats.total_memory_mb / stats.total_tiles

            # NAPRAWKA: Optimized cache stats calculation
            if self._cache_optimizer:
                try:
                    # NAPRAWKA: Cache cache stats to avoid frequent calls
                    if (
                        not hasattr(self, "_cached_cache_stats")
                        or current_time - getattr(self, "_last_cache_check", 0) > 10.0
                    ):

                        cache_stats = self._cache_optimizer.get_performance_summary()
                        self._cached_cache_stats = cache_stats
                        self._last_cache_check = current_time
                    else:
                        cache_stats = self._cached_cache_stats

                    stats.cache_hit_ratio = cache_stats.get("overall_hit_rate", 0.0)
                    # Estimate hits/misses z hit rate
                    total_operations = 100  # Base na recent activity
                    stats.cache_hits = int(
                        total_operations * stats.cache_hit_ratio / 100
                    )
                    stats.cache_misses = total_operations - stats.cache_hits
                except Exception as e:
                    logger.debug(f"Error getting cache stats: {e}")
                    stats.cache_hits = 0
                    stats.cache_misses = 0
                    stats.cache_hit_ratio = 0.0
            else:
                stats.cache_hits = 0
                stats.cache_misses = 0
                stats.cache_hit_ratio = 0.0

        # NAPRAWKA: Optimized history management
        self._stats_history.append(stats)
        if len(self._stats_history) > 50:  # Reduced from 100 to 50
            self._stats_history.pop(0)

        self._last_stats_update = current_time
        self.stats_updated.emit(stats)

    def _on_memory_warning(self, message: str, usage_mb: float):
        """Callback dla memory warning."""
        logger.warning(f"Memory warning: {message}")
        self.resource_warning.emit(message)

    def _on_memory_critical(self, message: str, usage_mb: float):
        """Callback dla critical memory usage."""
        logger.error(f"Critical memory: {message}")
        self.resource_warning.emit(f"CRITICAL: {message}")

    # === PUBLIC API ===

    def get_statistics(self) -> MemoryUsageStats:
        """Zwraca aktualne statystyki."""
        if self._stats_history:
            return self._stats_history[-1]
        else:
            self._update_statistics()
            return (
                self._stats_history[-1] if self._stats_history else MemoryUsageStats()
            )

    def get_active_tile_count(self) -> int:
        """Zwraca liczbę aktywnych tiles."""
        with self._lock:
            return len(self._active_tiles)

    def get_memory_trend(self) -> str:
        """Zwraca trend użycia pamięci."""
        return self._memory_monitor.get_memory_trend()

    def is_resource_limit_reached(self) -> bool:
        """Sprawdza czy osiągnięto limity zasobów."""
        stats = self.get_statistics()
        return (
            stats.total_tiles >= self.limits.max_tiles
            or stats.total_memory_mb >= self.limits.max_memory_mb
            or stats.memory_per_tile_mb >= self.limits.max_memory_per_tile_mb
        )

    def force_cleanup_now(self):
        """Wymuś immediate cleanup."""
        self.perform_cleanup()

    def get_debug_info(self) -> Dict:
        """Zwraca debug info o resource manager."""
        stats = self.get_statistics()
        return {
            "limits": self.limits,
            "current_stats": stats,
            "memory_trend": self.get_memory_trend(),
            "component_counts": {
                name: len(comp_set)
                for name, comp_set in self._active_components.items()
            },
            "last_cleanup_ago_seconds": time.time() - self._last_cleanup_time,
            "worker_pool_active": self._worker_pool.get_active_count(),
        }

    def cleanup(self):
        """Cleanup resource manager z proper timer cleanup."""
        logger.info("Cleaning up TileResourceManager...")

        # NAPRAWKA: Proper timer cleanup dla MemoryMonitor
        if hasattr(self, "_cleanup_timer"):
            self._cleanup_timer.stop()
            self._cleanup_timer.deleteLater()

        if hasattr(self, "_memory_monitor"):
            self._memory_monitor.cleanup()  # NAPRAWKA: Proper MemoryMonitor cleanup

        # Cleanup performance components
        if self._performance_enabled:
            try:
                if self._performance_monitor:
                    self._performance_monitor.cleanup()
                if self._cache_optimizer:
                    self._cache_optimizer.cleanup()
                if self._async_ui_manager:
                    self._async_ui_manager.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up performance components: {e}")

        # Final cleanup
        self.perform_cleanup()

        # Clear references
        with self._lock:
            self._active_tiles.clear()
            for component_set in self._active_components.values():
                component_set.clear()

        logger.info("TileResourceManager cleanup completed")


# === SINGLETON INSTANCE ===

_resource_manager_instance: Optional[TileResourceManager] = None
_resource_manager_lock = threading.Lock()


def get_resource_manager(
    limits: Optional[ResourceLimits] = None,
) -> TileResourceManager:
    """Singleton access do TileResourceManager z proper double-checked locking."""
    global _resource_manager_instance

    # NAPRAWKA: Proper double-checked locking dla thread safety
    if _resource_manager_instance is None:
        with _resource_manager_lock:
            # Double-check po acquire lock
            if _resource_manager_instance is None:
                _resource_manager_instance = TileResourceManager(limits)
                logger.debug("TileResourceManager singleton instance created")

    return _resource_manager_instance


def cleanup_resource_manager():
    """Cleanup singleton instance."""
    global _resource_manager_instance

    with _resource_manager_lock:
        if _resource_manager_instance is not None:
            _resource_manager_instance.cleanup()
            _resource_manager_instance = None


# === DECORATORS ===


def with_resource_management(component_type: str = "tile"):
    """Decorator dla automatycznej rejestracji w resource manager."""

    def decorator(cls):
        original_init = cls.__init__
        original_cleanup = getattr(cls, "cleanup", lambda self: None)

        def __init__(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            # Auto-register w resource manager
            resource_manager = get_resource_manager()
            if component_type == "tile":
                resource_manager.register_tile(self)
            else:
                resource_manager.register_component(component_type, self)

        def cleanup(self):
            original_cleanup(self)
            # Auto cleanup

        cls.__init__ = __init__
        cls.cleanup = cleanup
        return cls

    return decorator
