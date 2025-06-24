"""
ETAP 8: PERFORMANCE OPTIMIZATION - TileAsyncUIManager
Asynchroniczne operacje UI dla maksymalnej responsywności.
"""

import time
import threading
import concurrent.futures
from collections import deque, defaultdict
from dataclasses import dataclass
from typing import Callable, Any, Optional, Dict, List
from enum import Enum, auto

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread, QMetaObject, Qt
from PyQt6.QtWidgets import QApplication

import logging
logger = logging.getLogger(__name__)


class UIUpdatePriority(Enum):
    """Priorytety dla UI updates."""
    CRITICAL = 0    # Immediate - user interaction
    HIGH = 1        # User visible changes  
    NORMAL = 2      # Regular updates
    LOW = 3         # Background updates
    BACKGROUND = 4  # Lowest priority


@dataclass
class UIUpdateTask:
    """Zadanie UI update."""
    func: Callable
    args: tuple
    kwargs: dict
    priority: UIUpdatePriority
    created_time: float
    callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    
    def __post_init__(self):
        if self.created_time == 0:
            self.created_time = time.time()
    
    def execute(self) -> Any:
        """Wykonuje zadanie."""
        try:
            result = self.func(*self.args, **self.kwargs)
            if self.callback:
                self.callback(result)
            return result
        except Exception as e:
            logger.error(f"UI update task error: {e}")
            if self.error_callback:
                self.error_callback(e)
            raise


class UIUpdateScheduler(QObject):
    """Scheduler dla UI updates z priorytetami."""
    
    task_scheduled = pyqtSignal(str)
    task_completed = pyqtSignal(str, float)
    
    def __init__(self, max_concurrent: int = 3):
        super().__init__()
        self.max_concurrent = max_concurrent
        self._task_queue = deque()
        self._active_tasks = set()
        self._lock = threading.RLock()
        self._running = True
        
        # Use threading timer instead of QTimer for better test compatibility
        self._start_processing()
        
    def _start_processing(self):
        """Start background processing."""
        if self._running:
            self.process_tasks()
            # Schedule next processing
            timer = threading.Timer(0.01, self._start_processing)  # 10ms interval
            timer.daemon = True
            timer.start()
        
    def schedule_task(self, task: UIUpdateTask) -> bool:
        """Planuje zadanie UI update."""
        with self._lock:
            # Sort by priority (lower enum value = higher priority)
            inserted = False
            for i, existing_task in enumerate(self._task_queue):
                if task.priority.value < existing_task.priority.value:
                    self._task_queue.insert(i, task)
                    inserted = True
                    break
            
            if not inserted:
                self._task_queue.append(task)
                
            self.task_scheduled.emit(f"Priority_{task.priority.name}")
            return True
    
    def process_tasks(self):
        """Przetwarza zadania z kolejki."""
        with self._lock:
            while self._task_queue and len(self._active_tasks) < self.max_concurrent:
                task = self._task_queue.popleft()
                task_id = id(task)
                self._active_tasks.add(task_id)
                
                start_time = time.time()
                try:
                    task.execute()
                    duration = time.time() - start_time
                    self.task_completed.emit(f"Priority_{task.priority.name}", duration)
                except Exception as e:
                    logger.error(f"Task execution error: {e}")
                finally:
                    self._active_tasks.discard(task_id)
    
    def cleanup(self):
        """Cleanup scheduler."""
        self._running = False


class DebounceManager(QObject):
    """Manager dla debounce operacji."""
    
    def __init__(self):
        super().__init__()
        self._timers: Dict[str, threading.Timer] = {}
        self._pending_operations: Dict[str, tuple] = {}
        self._lock = threading.RLock()
    
    def debounce(self, operation_id: str, func: Callable, delay_ms: int = 100, 
                *args, **kwargs):
        """Debounce operację."""
        with self._lock:
            # Store the operation
            self._pending_operations[operation_id] = (func, args, kwargs)
            
            # Cancel existing timer
            if operation_id in self._timers:
                self._timers[operation_id].cancel()
                del self._timers[operation_id]
            
            # Create new timer
            delay_seconds = delay_ms / 1000.0
            timer = threading.Timer(delay_seconds, self._execute_debounced, [operation_id])
            timer.daemon = True
            timer.start()
            
            self._timers[operation_id] = timer
    
    def _execute_debounced(self, operation_id: str):
        """Wykonuje debounced operację."""
        with self._lock:
            if operation_id not in self._pending_operations:
                return
                
            func, args, kwargs = self._pending_operations[operation_id]
            del self._pending_operations[operation_id]
            
            # Clean up timer
            if operation_id in self._timers:
                del self._timers[operation_id]
        
        try:
            # Handle case when single tuple argument is passed
            if len(args) == 1 and isinstance(args[0], tuple):
                func(*args[0], **kwargs)
            else:
                func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Debounced operation error: {e}")
    
    def cleanup(self):
        """Cleanup all timers."""
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()
            self._pending_operations.clear()


class BatchUIUpdater(QObject):
    """Batch UI updates dla wydajności."""
    
    batch_executed = pyqtSignal(int)  # number of updates
    
    def __init__(self, batch_size: int = 10, timeout_ms: int = 100):
        super().__init__()
        self.batch_size = batch_size
        self.timeout_ms = timeout_ms
        self._batch_queue: List[Callable] = []
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._flush_batch)
        self._lock = threading.RLock()
    
    def add_update(self, update_func: Callable):
        """Dodaje update do batch."""
        with self._lock:
            self._batch_queue.append(update_func)
            
            # Start timer if first update
            if len(self._batch_queue) == 1:
                self._timer.start(self.timeout_ms)
            
            # Flush if batch is full
            if len(self._batch_queue) >= self.batch_size:
                self._flush_batch()
    
    def _flush_batch(self):
        """Wykonuje wszystkie updates w batch."""
        with self._lock:
            if not self._batch_queue:
                return
                
            updates_to_process = self._batch_queue[:]
            self._batch_queue.clear()
            self._timer.stop()
        
        # Execute updates
        executed_count = 0
        for update_func in updates_to_process:
            try:
                update_func()
                executed_count += 1
            except Exception as e:
                logger.error(f"Batch update error: {e}")
        
        self.batch_executed.emit(executed_count)
    
    def force_flush(self):
        """Wymusza flush batch."""
        self._flush_batch()
    
    def cleanup(self):
        """Cleanup batch updater."""
        self._timer.stop()
        with self._lock:
            self._batch_queue.clear()


class TileAsyncUIManager(QObject):
    """
    Asynchroniczny manager UI dla FileTileWidget ecosystem.
    
    Features:
    - Priority-based task scheduling
    - Debouncing dla częstych updates
    - Memory pressure handling
    """
    
    # Sygnały
    task_scheduled = pyqtSignal(str, int)  # task_type, priority
    performance_warning = pyqtSignal(str, float)  # warning_type, value
    
    def __init__(self, max_concurrent_tasks: int = 5, enable_batching: bool = True):
        super().__init__()
        
        self.max_concurrent_tasks = max_concurrent_tasks
        self.enable_batching = enable_batching
        self._current_fps = 60.0
        self._frame_drops = 0
        
        # Initialize components
        self._scheduler = UIUpdateScheduler(max_concurrent_tasks)
        self._debounce_manager = DebounceManager()
        self._batch_updater = BatchUIUpdater() if enable_batching else None
        
        # Connect signals
        self._scheduler.task_scheduled.connect(
            lambda task_type: self.task_scheduled.emit(task_type, 0)
        )
        
        logger.info(f"TileAsyncUIManager initialized (concurrent_tasks: {max_concurrent_tasks}, batching: {enable_batching})")
    
    def schedule_async_update(self, 
                            func: Callable, 
                            *args,
                            priority: UIUpdatePriority = UIUpdatePriority.NORMAL,
                            callback: Optional[Callable] = None,
                            **kwargs):
        """Planuje asynchroniczny UI update."""
        task = UIUpdateTask(
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            created_time=time.time(),
            callback=callback
        )
        return self._scheduler.schedule_task(task)
    
    def schedule_thumbnail_load(self, 
                              load_func: Callable,
                              *args,
                              callback: Optional[Callable] = None,
                              **kwargs):
        """Planuje ładowanie miniaturki."""
        return self.schedule_async_update(
            load_func, *args,
            priority=UIUpdatePriority.HIGH,
            callback=callback,
            **kwargs
        )
    
    def debounce_operation(self, 
                          operation_id: str,
                          func: Callable,
                          delay_ms: int = 100,
                          *args,
                          **kwargs):
        """Debounce częste operacje."""
        self._debounce_manager.debounce(operation_id, func, delay_ms, *args, **kwargs)
    
    def add_to_batch(self, update_func: Callable):
        """Dodaje update do batch."""
        if self._batch_updater:
            self._batch_updater.add_update(update_func)
        else:
            # Execute immediately if batching disabled
            try:
                update_func()
            except Exception as e:
                logger.error(f"Immediate update error: {e}")
    
    def flush_batch_updates(self):
        """Wymusza przetworzenie batch updates."""
        if self._batch_updater:
            self._batch_updater.force_flush()
    
    def handle_memory_pressure(self, memory_usage_mb: float):
        """Obsługuje memory pressure."""
        if memory_usage_mb > 1000:
            self.performance_warning.emit("HIGH_MEMORY_USAGE", memory_usage_mb)
            logger.warning(f"Memory pressure detected: {memory_usage_mb:.1f}MB")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Zwraca performance statistics."""
        return {
            'scheduler': {
                'queue_size': len(self._scheduler._task_queue),
                'active_tasks': len(self._scheduler._active_tasks),
                'max_concurrent': self._scheduler.max_concurrent,
            },
            'current_fps': self._current_fps,
            'frame_drops': self._frame_drops,
            'max_concurrent_tasks': self.max_concurrent_tasks,
            'batching_enabled': self.enable_batching,
            'scheduler_queue_size': len(self._scheduler._task_queue),
            'batch_queue_size': len(self._batch_updater._batch_queue) if self._batch_updater else 0,
        }
    
    def cleanup(self):
        """Cleanup async UI manager."""
        self._scheduler.cleanup()
        self._scheduler.deleteLater()
        self._debounce_manager.cleanup()
        if self._batch_updater:
            self._batch_updater.cleanup()
        logger.info("TileAsyncUIManager cleaned up")


# === GLOBAL INSTANCE ===

_async_ui_manager_instance: Optional[TileAsyncUIManager] = None
_async_ui_manager_lock = threading.Lock()


def get_async_ui_manager(max_concurrent_tasks: int = 5) -> TileAsyncUIManager:
    """Singleton access do TileAsyncUIManager."""
    global _async_ui_manager_instance
    
    with _async_ui_manager_lock:
        if _async_ui_manager_instance is None:
            _async_ui_manager_instance = TileAsyncUIManager(max_concurrent_tasks)
        return _async_ui_manager_instance


def cleanup_async_ui_manager():
    """Cleanup singleton instance."""
    global _async_ui_manager_instance
    
    with _async_ui_manager_lock:
        if _async_ui_manager_instance is not None:
            _async_ui_manager_instance.cleanup()
            _async_ui_manager_instance = None 