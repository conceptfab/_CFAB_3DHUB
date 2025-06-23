# PATCH-CODE DLA: TILE_ASYNC_UI_MANAGER

**Powiązany plik z analizą:** `../corrections/tile_async_ui_manager_correction_kafli.md`
**Zasady ogólne:** `../_BASE_/refactoring_rules.md`

---

### PATCH 1: FIX TIMER MEMORY LEAK

**Problem:** Recursive timer creation co 10ms prowadzi do memory leak
**Rozwiązanie:** Replace z proper QTimer implementation

```python
class UIUpdateScheduler(QObject):
    """Thread-safe scheduler z proper timer management."""
    
    def __init__(self, max_concurrent: int = 3):
        super().__init__()
        self.max_concurrent = max_concurrent
        self._task_queue = deque()
        self._active_tasks = set()
        self._lock = threading.RLock()
        self._running = True
        
        # Replace threading.Timer z QTimer
        self._processing_timer = QTimer()
        self._processing_timer.timeout.connect(self.process_tasks)
        self._processing_timer.start(10)  # 10ms interval
        
    def stop_processing(self):
        """Stop timer processing."""
        self._running = False
        if self._processing_timer.isActive():
            self._processing_timer.stop()
    
    def cleanup(self):
        """Proper cleanup."""
        self.stop_processing()
        self._processing_timer.deleteLater()
        
        # Clear remaining tasks
        with self._lock:
            self._task_queue.clear()
            self._active_tasks.clear()
```

---

### PATCH 2: HEAP-BASED PRIORITY QUEUE

**Problem:** O(n) insertion dla task scheduling jest expensive
**Rozwiązanie:** Implement heap-based priority queue dla O(log n) performance

```python
import heapq
from typing import List, Tuple
import time

class PriorityTaskQueue:
    """Thread-safe priority queue z heap implementation."""
    
    def __init__(self, max_size: int = 1000):
        self._heap: List[Tuple[int, float, UIUpdateTask]] = []
        self._max_size = max_size
        self._lock = threading.RLock()
        self._counter = 0  # For stable sorting
    
    def put(self, task: UIUpdateTask) -> bool:
        """Add task to priority queue."""
        with self._lock:
            if len(self._heap) >= self._max_size:
                # Remove lowest priority task if queue full
                if self._heap and self._heap[0][0] < task.priority.value:
                    heapq.heappop(self._heap)
                else:
                    return False  # Task priority too low
            
            # Use negative priority for max-heap behavior (lower enum = higher priority)
            # Add counter for stable sorting
            priority_key = (-task.priority.value, self._counter)
            self._counter += 1
            
            heapq.heappush(self._heap, (priority_key[0], priority_key[1], task))
            return True
    
    def get(self) -> Optional[UIUpdateTask]:
        """Get highest priority task."""
        with self._lock:
            if self._heap:
                _, _, task = heapq.heappop(self._heap)
                return task
            return None
    
    def size(self) -> int:
        """Get queue size."""
        with self._lock:
            return len(self._heap)
    
    def clear(self):
        """Clear queue."""
        with self._lock:
            self._heap.clear()

class UIUpdateScheduler(QObject):
    """Enhanced scheduler z heap-based priority queue."""
    
    def __init__(self, max_concurrent: int = 3, max_queue_size: int = 1000):
        super().__init__()
        self.max_concurrent = max_concurrent
        self._task_queue = PriorityTaskQueue(max_queue_size)
        self._active_tasks = set()
        self._lock = threading.RLock()
        self._running = True
        
        # Performance metrics
        self._tasks_processed = 0
        self._tasks_rejected = 0
        
        # QTimer dla processing
        self._processing_timer = QTimer()
        self._processing_timer.timeout.connect(self.process_tasks)
        self._processing_timer.start(10)  # 10ms
    
    def schedule_task(self, task: UIUpdateTask) -> bool:
        """Schedule task z heap-based priority."""
        success = self._task_queue.put(task)
        
        if success:
            self.task_scheduled.emit(f"Priority_{task.priority.name}")
        else:
            self._tasks_rejected += 1
            logger.warning(f"Task rejected due to queue full: {task.priority.name}")
        
        return success
    
    def process_tasks(self):
        """Process tasks from priority queue."""
        if not self._running:
            return
            
        with self._lock:
            while self._task_queue.size() > 0 and len(self._active_tasks) < self.max_concurrent:
                task = self._task_queue.get()
                if task is None:
                    break
                
                task_id = id(task)
                self._active_tasks.add(task_id)
                
                start_time = time.time()
                try:
                    task.execute()
                    duration = time.time() - start_time
                    self.task_completed.emit(f"Priority_{task.priority.name}", duration)
                    self._tasks_processed += 1
                except Exception as e:
                    logger.error(f"Task execution error: {e}")
                finally:
                    self._active_tasks.discard(task_id)
    
    def get_metrics(self) -> Dict[str, int]:
        """Get scheduler metrics."""
        return {
            'queue_size': self._task_queue.size(),
            'active_tasks': len(self._active_tasks),
            'tasks_processed': self._tasks_processed,
            'tasks_rejected': self._tasks_rejected,
        }
```

---

### PATCH 3: TASK TIMEOUT I CANCELLATION

**Problem:** Brak timeout dla long-running tasks może block scheduler
**Rozwiązanie:** Add timeout i cancellation mechanisms

```python
import signal
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

@dataclass
class UIUpdateTask:
    """Enhanced task z timeout support."""
    func: Callable
    args: tuple
    kwargs: dict
    priority: UIUpdatePriority
    created_time: float
    timeout_seconds: Optional[float] = None
    callback: Optional[Callable] = None
    error_callback: Optional[Callable] = None
    cancel_token: Optional[threading.Event] = None
    
    def __post_init__(self):
        if self.created_time == 0:
            self.created_time = time.time()
        if self.cancel_token is None:
            self.cancel_token = threading.Event()
    
    def execute_with_timeout(self) -> Any:
        """Execute task z timeout."""
        if self.cancel_token.is_set():
            raise RuntimeError("Task was cancelled")
        
        if self.timeout_seconds is None:
            return self.execute()
        
        # Use ThreadPoolExecutor dla timeout
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.execute)
            try:
                result = future.result(timeout=self.timeout_seconds)
                return result
            except FutureTimeoutError:
                logger.warning(f"Task timeout after {self.timeout_seconds}s")
                self.cancel_token.set()
                if self.error_callback:
                    self.error_callback(TimeoutError("Task timeout"))
                raise TimeoutError("Task execution timeout")
    
    def cancel(self):
        """Cancel task execution."""
        self.cancel_token.set()

class UIUpdateScheduler(QObject):
    """Scheduler z timeout support."""
    
    def __init__(self, max_concurrent: int = 3, default_timeout: float = 5.0):
        super().__init__()
        # ... existing initialization ...
        self.default_timeout = default_timeout
        self._cancelled_tasks = set()
    
    def schedule_task(self, task: UIUpdateTask) -> bool:
        """Schedule task z default timeout."""
        if task.timeout_seconds is None:
            task.timeout_seconds = self.default_timeout
        
        return self._task_queue.put(task)
    
    def cancel_task(self, task_id: str):
        """Cancel specific task."""
        # Implementation for task cancellation
        self._cancelled_tasks.add(task_id)
    
    def process_tasks(self):
        """Process tasks z timeout handling."""
        if not self._running:
            return
            
        with self._lock:
            while self._task_queue.size() > 0 and len(self._active_tasks) < self.max_concurrent:
                task = self._task_queue.get()
                if task is None:
                    break
                
                task_id = id(task)
                if task_id in self._cancelled_tasks:
                    self._cancelled_tasks.discard(task_id)
                    continue
                
                self._active_tasks.add(task_id)
                
                start_time = time.time()
                try:
                    # Use timeout execution
                    task.execute_with_timeout()
                    duration = time.time() - start_time
                    self.task_completed.emit(f"Priority_{task.priority.name}", duration)
                    self._tasks_processed += 1
                except (TimeoutError, RuntimeError) as e:
                    logger.warning(f"Task failed: {e}")
                except Exception as e:
                    logger.error(f"Task execution error: {e}")
                finally:
                    self._active_tasks.discard(task_id)
                    self._cancelled_tasks.discard(task_id)
```

---

### PATCH 4: ATOMIC BATCH OPERATIONS

**Problem:** Race condition między copy i clear w batch processing
**Rozwiązanie:** Atomic operations z thread-safe queue management

```python
from queue import Queue, Empty
import threading

class AtomicBatchUpdater(QObject):
    """Thread-safe batch updater z atomic operations."""
    
    batch_executed = pyqtSignal(int)
    
    def __init__(self, batch_size: int = 10, timeout_ms: int = 100):
        super().__init__()
        self.batch_size = batch_size
        self.timeout_ms = timeout_ms
        
        # Use thread-safe Queue instead of list
        self._batch_queue = Queue(maxsize=batch_size * 2)  # Allow some overflow
        self._processing = False
        self._lock = threading.RLock()
        
        # QTimer dla timeout-based flushing
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._flush_batch)
    
    def add_update(self, update_func: Callable) -> bool:
        """Thread-safe add update."""
        try:
            # Non-blocking put with immediate return
            self._batch_queue.put_nowait(update_func)
            
            with self._lock:
                # Start timer on first update
                if self._batch_queue.qsize() == 1 and not self._processing:
                    self._timer.start(self.timeout_ms)
                
                # Flush if batch is full
                if self._batch_queue.qsize() >= self.batch_size:
                    self._flush_batch()
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to add update to batch: {e}")
            # Execute immediately as fallback
            try:
                update_func()
            except Exception as exec_e:
                logger.error(f"Immediate execution fallback failed: {exec_e}")
            return False
    
    def _flush_batch(self):
        """Atomic batch flush."""
        with self._lock:
            if self._processing:
                return  # Already processing
            
            self._processing = True
            self._timer.stop()
        
        # Atomic extraction of all updates
        updates_to_process = []
        try:
            while True:
                try:
                    update = self._batch_queue.get_nowait()
                    updates_to_process.append(update)
                except Empty:
                    break
        except Exception as e:
            logger.error(f"Error extracting batch updates: {e}")
        
        # Execute updates outside lock
        executed_count = 0
        for update_func in updates_to_process:
            try:
                update_func()
                executed_count += 1
            except Exception as e:
                logger.error(f"Batch update error: {e}")
        
        # Reset processing flag
        with self._lock:
            self._processing = False
            
            # Restart timer if more updates arrived
            if not self._batch_queue.empty():
                self._timer.start(self.timeout_ms)
        
        if executed_count > 0:
            self.batch_executed.emit(executed_count)
    
    def force_flush(self):
        """Force immediate flush."""
        self._flush_batch()
    
    def cleanup(self):
        """Cleanup batch updater."""
        self._timer.stop()
        
        # Flush remaining updates
        self._flush_batch()
        
        # Clear queue
        try:
            while not self._batch_queue.empty():
                self._batch_queue.get_nowait()
        except Empty:
            pass
```

---

### PATCH 5: ENHANCED MEMORY PRESSURE HANDLING

**Problem:** Weak memory pressure response - tylko warning
**Rozwiązanie:** Adaptive behavior z automatic task throttling

```python
class AdaptiveMemoryManager:
    """Adaptive memory management dla UI operations."""
    
    def __init__(self, warning_threshold_mb: float = 200.0, critical_threshold_mb: float = 300.0):
        self.warning_threshold = warning_threshold_mb
        self.critical_threshold = critical_threshold_mb
        self._pressure_level = 0  # 0=normal, 1=warning, 2=critical
        self._throttle_factor = 1.0
    
    def update_memory_pressure(self, memory_usage_mb: float) -> Dict[str, Any]:
        """Update memory pressure i return adaptive settings."""
        old_level = self._pressure_level
        
        if memory_usage_mb >= self.critical_threshold:
            self._pressure_level = 2
            self._throttle_factor = 0.3  # Aggressive throttling
        elif memory_usage_mb >= self.warning_threshold:
            self._pressure_level = 1  
            self._throttle_factor = 0.7  # Moderate throttling
        else:
            self._pressure_level = 0
            self._throttle_factor = 1.0  # No throttling
        
        # Return adaptive settings
        return {
            'pressure_level': self._pressure_level,
            'throttle_factor': self._throttle_factor,
            'max_concurrent_tasks': max(1, int(5 * self._throttle_factor)),
            'batch_size': max(1, int(10 * self._throttle_factor)),
            'should_pause_non_critical': self._pressure_level >= 2,
            'level_changed': old_level != self._pressure_level
        }

class TileAsyncUIManager(QObject):
    """Enhanced manager z adaptive memory handling."""
    
    def __init__(self, max_concurrent_tasks: int = 5, enable_batching: bool = True):
        super().__init__()
        # ... existing initialization ...
        
        # Add memory manager
        self._memory_manager = AdaptiveMemoryManager()
        self._original_max_concurrent = max_concurrent_tasks
    
    def handle_memory_pressure(self, memory_usage_mb: float):
        """Enhanced memory pressure handling."""
        settings = self._memory_manager.update_memory_pressure(memory_usage_mb)
        
        if settings['level_changed']:
            logger.info(f"Memory pressure level changed: {settings['pressure_level']}")
        
        # Adaptive throttling
        new_max_concurrent = settings['max_concurrent_tasks']
        if new_max_concurrent != self._scheduler.max_concurrent:
            self._scheduler.max_concurrent = new_max_concurrent
            logger.info(f"Adjusted concurrent tasks: {new_max_concurrent}")
        
        # Pause non-critical tasks if critical pressure
        if settings['should_pause_non_critical']:
            self._pause_non_critical_tasks()
        
        # Adjust batch size
        if self._batch_updater:
            self._batch_updater.batch_size = settings['batch_size']
        
        # Emit performance warning
        if settings['pressure_level'] > 0:
            self.performance_warning.emit("MEMORY_PRESSURE", memory_usage_mb)
    
    def _pause_non_critical_tasks(self):
        """Pause non-critical tasks during memory pressure."""
        # Implementation for pausing LOW i BACKGROUND priority tasks
        logger.info("Pausing non-critical tasks due to memory pressure")
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Task scheduling** - priority-based scheduling działa poprawnie
- [ ] **Timer management** - QTimer replacement eliminuje memory leaks
- [ ] **Priority queue** - heap-based implementation jest efficient
- [ ] **Task timeout** - long-running tasks są cancelled properly
- [ ] **Batch processing** - atomic operations eliminują race conditions
- [ ] **Memory pressure** - adaptive throttling działa poprawnie
- [ ] **Debouncing** - frequent operations są properly debounced
- [ ] **Signal emissions** - Qt signals są emitted correctly
- [ ] **Thread safety** - concurrent access jest bezpieczny
- [ ] **Performance monitoring** - metrics są accurate i up-to-date

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **PyQt6 integration** - QObject, QTimer, signals działają
- [ ] **Threading** - RLock i thread safety jest maintained
- [ ] **Concurrent futures** - timeout handling działa poprawnie
- [ ] **Queue operations** - thread-safe Queue eliminuje race conditions
- [ ] **FileTileWidget integration** - async operations są used properly
- [ ] **Gallery manager** - bulk operations są handled efficiently
- [ ] **Memory monitoring** - pressure detection działa correctly
- [ ] **Performance tracking** - metrics są collected accurately

#### **TESTY WERYFIKACYJNE:**

- [ ] **Unit tests** - wszystkie async operations
- [ ] **Performance tests** - UI responsywność 60 FPS maintained
- [ ] **Memory tests** - no timer leaks, bounded queue growth
- [ ] **Concurrency tests** - thread safety z multiple tasks
- [ ] **Timeout tests** - long-running tasks są cancelled
- [ ] **Pressure tests** - adaptive behavior under memory pressure

#### **KRYTERIA SUKCESU:**

- [ ] **UI RESPONSYWNOŚĆ 60 FPS** - smooth scrolling maintained
- [ ] **NO MEMORY LEAKS** - timer management fixed
- [ ] **EFFICIENT SCHEDULING** - heap-based priority queue performance
- [ ] **BOUNDED MEMORY USAGE** - queue limits enforced
- [ ] **THREAD SAFETY** - no race conditions detected
- [ ] **ADAPTIVE BEHAVIOR** - memory pressure handling works

---