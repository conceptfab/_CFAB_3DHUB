"""
ETAP 8: PERFORMANCE OPTIMIZATION - TilePerformanceMonitor
Comprehensive performance monitoring i optimization dla FileTileWidget.
"""

import time
import threading
import statistics
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Deque
from enum import Enum, auto

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QElapsedTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QWidget

import logging
logger = logging.getLogger(__name__)


class PerformanceMetric(Enum):
    """Typy metryk performance."""
    RENDER_TIME = auto()
    MEMORY_USAGE = auto()
    THUMBNAIL_LOAD_TIME = auto()
    UI_UPDATE_TIME = auto()
    CACHE_HIT_RATE = auto()
    COMPONENT_INIT_TIME = auto()
    EVENT_PROCESSING_TIME = auto()
    BATCH_OPERATION_TIME = auto()


@dataclass
class PerformanceSample:
    """Pojedyncza próbka performance."""
    metric: PerformanceMetric
    value: float
    timestamp: float
    context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()


@dataclass
class PerformanceStats:
    """Statystyki performance dla pojedynczej metryki."""
    metric: PerformanceMetric
    sample_count: int = 0
    min_value: float = float('inf')
    max_value: float = 0.0
    avg_value: float = 0.0
    median_value: float = 0.0
    p95_value: float = 0.0  # 95th percentile
    total_time: float = 0.0
    last_updated: float = 0.0
    
    def update_from_samples(self, samples: List[float]):
        """Aktualizuje statystyki na podstawie próbek."""
        if not samples:
            return
        
        self.sample_count = len(samples)
        self.min_value = min(samples)
        self.max_value = max(samples)
        self.avg_value = statistics.mean(samples)
        self.median_value = statistics.median(samples)
        
        # 95th percentile
        if len(samples) >= 20:  # Minimum samples for reliable percentile
            sorted_samples = sorted(samples)
            p95_index = int(0.95 * len(sorted_samples))
            self.p95_value = sorted_samples[p95_index]
        else:
            self.p95_value = self.max_value
        
        self.total_time = sum(samples)
        self.last_updated = time.time()


@dataclass
class FrameTimingStats:
    """Statystyki frame timing dla UI responsiveness."""
    target_fps: int = 60
    target_frame_time_ms: float = 16.67  # 1000ms / 60fps
    
    frame_count: int = 0
    dropped_frames: int = 0
    avg_frame_time_ms: float = 0.0
    frame_time_history: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    
    def add_frame_time(self, frame_time_ms: float):
        """Dodaje nowy frame time."""
        self.frame_count += 1
        self.frame_time_history.append(frame_time_ms)
        
        if frame_time_ms > self.target_frame_time_ms:
            self.dropped_frames += 1
        
        # Update average
        if self.frame_time_history:
            self.avg_frame_time_ms = statistics.mean(self.frame_time_history)
    
    def get_fps(self) -> float:
        """Zwraca aktualną średnią FPS."""
        if self.avg_frame_time_ms > 0:
            return 1000.0 / self.avg_frame_time_ms
        return 0.0
    
    def get_frame_drop_rate(self) -> float:
        """Zwraca procent dropped frames."""
        if self.frame_count > 0:
            return (self.dropped_frames / self.frame_count) * 100.0
        return 0.0


class BatchOperationOptimizer:
    """Optymalizator dla batch operations."""
    
    def __init__(self, max_batch_size: int = 50, batch_timeout_ms: int = 100):
        self.max_batch_size = max_batch_size
        self.batch_timeout_ms = batch_timeout_ms
        self._pending_operations: List[Callable] = []
        self._batch_timer = QTimer()
        self._batch_timer.setSingleShot(True)
        self._batch_timer.timeout.connect(self._process_batch)
        self._lock = threading.RLock()
        
    def add_operation(self, operation: Callable):
        """Dodaje operację do batch."""
        with self._lock:
            self._pending_operations.append(operation)
            
            # Start timer if first operation
            if len(self._pending_operations) == 1:
                self._batch_timer.start(self.batch_timeout_ms)
            
            # Process immediately if batch full
            elif len(self._pending_operations) >= self.max_batch_size:
                self._batch_timer.stop()
                self._process_batch()
    
    def _process_batch(self):
        """Przetwarza batch operacji."""
        with self._lock:
            if not self._pending_operations:
                return
            
            operations = self._pending_operations.copy()
            self._pending_operations.clear()
        
        # Execute batch
        start_time = time.time()
        try:
            for operation in operations:
                operation()
        except Exception as e:
            logger.error(f"Batch operation error: {e}")
        
        execution_time = (time.time() - start_time) * 1000  # ms
        logger.debug(f"Processed batch of {len(operations)} operations in {execution_time:.2f}ms")
    
    def flush(self):
        """Wymusza przetworzenie wszystkich pending operations."""
        self._batch_timer.stop()
        self._process_batch()


class QtRenderingOptimizer:
    """Optymalizator Qt rendering pipeline."""
    
    @staticmethod
    def optimize_pixmap_for_display(pixmap: QPixmap, target_size: tuple) -> QPixmap:
        """Optymalizuje pixmap dla wyświetlania."""
        if pixmap.isNull():
            return pixmap
        
        # Skip optimization jeśli już odpowiedni rozmiar
        if (pixmap.width() == target_size[0] and 
            pixmap.height() == target_size[1]):
            return pixmap
        
        # Smooth scaling dla lepszej jakości
        from PyQt6.QtCore import Qt
        return pixmap.scaled(
            target_size[0], target_size[1],
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
    
    @staticmethod
    def optimize_widget_updates(widget: QWidget):
        """Optymalizuje widget update strategy."""
        if widget is None:
            return
        
        # Enable updates batching
        widget.setUpdatesEnabled(True)
        
        # Optimize paint events
        widget.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        widget.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        
        # Enable style optimizations
        widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)


class TilePerformanceMonitor(QObject):
    """
    Comprehensive performance monitor dla FileTileWidget ecosystem.
    
    Features:
    - Real-time performance metrics collection
    - Frame timing analysis
    - Memory usage tracking  
    - Cache performance monitoring
    - Batch operation optimization
    - Qt rendering optimization
    """
    
    # Sygnały
    performance_alert = pyqtSignal(str, float)  # metric_name, value
    stats_updated = pyqtSignal(object)  # PerformanceStats
    frame_drop_detected = pyqtSignal(float)  # frame_time_ms
    
    def __init__(self, enable_monitoring: bool = True, history_size: int = 1000):
        super().__init__()
        
        self.enable_monitoring = enable_monitoring
        self.history_size = history_size
        
        # Metrics storage
        self._metrics_history: Dict[PerformanceMetric, Deque[PerformanceSample]] = defaultdict(
            lambda: deque(maxlen=history_size)
        )
        self._stats_cache: Dict[PerformanceMetric, PerformanceStats] = {}
        
        # Frame timing
        self._frame_stats = FrameTimingStats()
        self._frame_timer = QElapsedTimer()
        
        # Optimizers
        self._batch_optimizer = BatchOperationOptimizer()
        self._qt_optimizer = QtRenderingOptimizer()
        
        # Threading
        self._lock = threading.RLock()
        
        # Update timer
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_stats)
        if enable_monitoring:
            self._update_timer.start(5000)  # Update every 5 seconds
        
        # Thresholds dla alerts
        self._performance_thresholds = {
            PerformanceMetric.RENDER_TIME: 16.0,  # 16ms for 60fps
            PerformanceMetric.MEMORY_USAGE: 5.0 * 1024 * 1024,  # 5MB
            PerformanceMetric.THUMBNAIL_LOAD_TIME: 200.0,  # 200ms
            PerformanceMetric.UI_UPDATE_TIME: 10.0,  # 10ms
            PerformanceMetric.CACHE_HIT_RATE: 90.0,  # 90%
        }
        
        logger.info(f"TilePerformanceMonitor initialized (monitoring: {enable_monitoring})")
    
    # === METRICS COLLECTION ===
    
    def record_metric(self, metric: PerformanceMetric, value: float, context: Optional[Dict] = None):
        """Rejestruje pojedynczą metrykę."""
        if not self.enable_monitoring:
            return
        
        sample = PerformanceSample(
            metric=metric,
            value=value,
            timestamp=time.time(),
            context=context or {}
        )
        
        with self._lock:
            self._metrics_history[metric].append(sample)
        
        # Check for performance alerts
        self._check_performance_alert(metric, value)
    
    def _check_performance_alert(self, metric: PerformanceMetric, value: float):
        """Sprawdza czy wartość przekracza threshold."""
        if metric not in self._performance_thresholds:
            return
        
        threshold = self._performance_thresholds[metric]
        
        # Different logic dla różnych metryk
        if metric == PerformanceMetric.CACHE_HIT_RATE:
            # Cache hit rate - alert gdy poniżej threshold
            if value < threshold:
                self.performance_alert.emit(f"Low cache hit rate: {value:.1f}%", value)
        else:
            # Inne metryki - alert gdy powyżej threshold  
            if value > threshold:
                self.performance_alert.emit(f"High {metric.name}: {value:.2f}", value)
    
    @contextmanager
    def measure_operation(self, metric: PerformanceMetric, context: Optional[Dict] = None):
        """Context manager dla pomiaru czasu operacji."""
        if not self.enable_monitoring:
            yield
            return
        
        start_time = time.perf_counter()
        try:
            yield
        finally:
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            self.record_metric(metric, duration_ms, context)
    
    def start_frame_timing(self):
        """Rozpoczyna pomiar frame timing."""
        if self.enable_monitoring:
            self._frame_timer.start()
    
    def end_frame_timing(self):
        """Kończy pomiar frame timing."""
        if not self.enable_monitoring or not self._frame_timer.isValid():
            return
        
        frame_time_ms = self._frame_timer.elapsed()
        self._frame_stats.add_frame_time(frame_time_ms)
        
        # Emit alert for dropped frames
        if frame_time_ms > self._frame_stats.target_frame_time_ms:
            self.frame_drop_detected.emit(frame_time_ms)
        
        # Record as metric
        self.record_metric(PerformanceMetric.RENDER_TIME, frame_time_ms)
    
    # === OPTIMIZATION METHODS ===
    
    def optimize_batch_operation(self, operation: Callable):
        """Dodaje operację do batch optimizer."""
        self._batch_optimizer.add_operation(operation)
    
    def flush_batch_operations(self):
        """Wymusza przetworzenie wszystkich batch operations."""
        self._batch_optimizer.flush()
    
    def optimize_pixmap(self, pixmap: QPixmap, target_size: tuple) -> QPixmap:
        """Optymalizuje pixmap używając Qt optimizer."""
        with self.measure_operation(PerformanceMetric.UI_UPDATE_TIME, {"operation": "pixmap_optimization"}):
            return self._qt_optimizer.optimize_pixmap_for_display(pixmap, target_size)
    
    def optimize_widget(self, widget: QWidget):
        """Optymalizuje widget rendering."""
        self._qt_optimizer.optimize_widget_updates(widget)
    
    # === STATS & REPORTING ===
    
    def _update_stats(self):
        """Aktualizuje cached statistics."""
        with self._lock:
            for metric, samples_deque in self._metrics_history.items():
                if not samples_deque:
                    continue
                
                # Extract values from last 100 samples
                recent_samples = list(samples_deque)[-100:]
                values = [sample.value for sample in recent_samples]
                
                # Update stats
                if metric not in self._stats_cache:
                    self._stats_cache[metric] = PerformanceStats(metric)
                
                self._stats_cache[metric].update_from_samples(values)
        
        # Emit updated stats
        if self._stats_cache:
            self.stats_updated.emit(self._stats_cache.copy())
    
    def get_performance_stats(self, metric: Optional[PerformanceMetric] = None) -> Dict[PerformanceMetric, PerformanceStats]:
        """Zwraca performance statistics."""
        if metric:
            return {metric: self._stats_cache.get(metric, PerformanceStats(metric))}
        return self._stats_cache.copy()
    
    def get_frame_timing_stats(self) -> FrameTimingStats:
        """Zwraca frame timing statistics."""
        return self._frame_stats
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Zwraca comprehensive performance summary."""
        summary = {
            'frame_stats': {
                'fps': self._frame_stats.get_fps(),
                'avg_frame_time_ms': self._frame_stats.avg_frame_time_ms,
                'frame_drop_rate': self._frame_stats.get_frame_drop_rate(),
                'total_frames': self._frame_stats.frame_count,
            },
            'metrics': {},
            'thresholds_exceeded': [],
            'monitoring_enabled': self.enable_monitoring,
            'history_size': self.history_size,
        }
        
        # Add metric summaries
        for metric, stats in self._stats_cache.items():
            summary['metrics'][metric.name] = {
                'avg': stats.avg_value,
                'min': stats.min_value,
                'max': stats.max_value,
                'p95': stats.p95_value,
                'sample_count': stats.sample_count,
            }
            
            # Check thresholds
            threshold = self._performance_thresholds.get(metric)
            if threshold and stats.avg_value > threshold:
                summary['thresholds_exceeded'].append({
                    'metric': metric.name,
                    'value': stats.avg_value,
                    'threshold': threshold
                })
        
        return summary
    
    def reset_stats(self):
        """Resetuje wszystkie statistics."""
        with self._lock:
            self._metrics_history.clear()
            self._stats_cache.clear()
            self._frame_stats = FrameTimingStats()
        
        logger.info("Performance stats reset")
    
    def set_performance_threshold(self, metric: PerformanceMetric, threshold: float):
        """Ustawia threshold dla performance alerts."""
        self._performance_thresholds[metric] = threshold
        logger.debug(f"Set threshold for {metric.name}: {threshold}")
    
    def enable_monitoring(self, enabled: bool):
        """Włącza/wyłącza monitoring."""
        self.enable_monitoring = enabled
        
        if enabled:
            self._update_timer.start(5000)
            logger.info("Performance monitoring enabled")
        else:
            self._update_timer.stop()
            logger.info("Performance monitoring disabled")
    
    def cleanup(self):
        """Cleanup performance monitor."""
        self.enable_monitoring = False
        if hasattr(self, '_update_timer'):
            self._update_timer.stop()
        
        self._batch_optimizer.flush()
        self.reset_stats()
        
        logger.info("TilePerformanceMonitor cleaned up")


# === DECORATORS ===

def performance_tracked(metric: PerformanceMetric, context: Optional[Dict] = None):
    """Decorator dla automatycznego śledzenia performance metod."""
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            # Get performance monitor z self lub globalne
            monitor = getattr(self, '_performance_monitor', None)
            if not monitor:
                from src.ui.widgets.tile_resource_manager import get_resource_manager
                resource_manager = get_resource_manager()
                monitor = getattr(resource_manager, '_performance_monitor', None)
            
            if monitor:
                with monitor.measure_operation(metric, context):
                    return func(self, *args, **kwargs)
            else:
                return func(self, *args, **kwargs)
        
        return wrapper
    return decorator


# === GLOBAL INSTANCE ===

_performance_monitor_instance: Optional[TilePerformanceMonitor] = None
_performance_monitor_lock = threading.Lock()


def get_performance_monitor(enable_monitoring: bool = True) -> TilePerformanceMonitor:
    """Singleton access do TilePerformanceMonitor."""
    global _performance_monitor_instance
    
    with _performance_monitor_lock:
        if _performance_monitor_instance is None:
            _performance_monitor_instance = TilePerformanceMonitor(enable_monitoring)
        return _performance_monitor_instance


def cleanup_performance_monitor():
    """Cleanup singleton instance."""
    global _performance_monitor_instance
    
    with _performance_monitor_lock:
        if _performance_monitor_instance is not None:
            _performance_monitor_instance.cleanup()
            _performance_monitor_instance = None 