# PATCH-CODE DLA: WORKER_MANAGER.PY

**Powiązany plik z analizą:** `../corrections/worker_manager_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: OPTYMALIZACJA MEMORY MONITOR THRESHOLDS

**Problem:** memory_limit_mb=1500 zbyt wysoki, circuit breaker aktywuje się za późno przy 1316MB
**Rozwiązanie:** Obniżenie thresholds i dodanie adaptive scaling

```python
# PRZED (line 32-38):
class MemoryMonitor:
    def __init__(self, memory_limit_mb=1500):  # ← PROBLEM: Za wysoki limit
        self.memory_limit_mb = memory_limit_mb
        self.high_memory_warnings = 0
        self.circuit_open = False

# PO:
class MemoryMonitor:
    def __init__(self, memory_limit_mb=1000):  # OBNIŻONO z 1500 do 1000MB
        self.memory_limit_mb = memory_limit_mb
        self.high_memory_warnings = 0
        self.circuit_open = False
        
        # NOWY: Adaptive scaling based on system memory
        self._adaptive_scaling_enabled = True
        self._system_memory_gb = self._get_system_memory()
        self._adjust_limits_for_system()
        
        # NOWY: Predictive memory tracking
        self._memory_history = []
        self._max_history = 10
        self._memory_trend = 0

    def _get_system_memory(self) -> float:
        """Get total system memory in GB."""
        try:
            import psutil
            return psutil.virtual_memory().total / (1024**3)
        except:
            return 8.0  # Default assumption: 8GB

    def _adjust_limits_for_system(self):
        """Adjust memory limits based on available system memory."""
        if not self._adaptive_scaling_enabled:
            return
            
        if self._system_memory_gb >= 16:
            # High memory system - more generous limits
            self.memory_limit_mb = 1200
        elif self._system_memory_gb >= 12:
            # Medium-high memory system
            self.memory_limit_mb = 1000  
        elif self._system_memory_gb >= 8:
            # Medium memory system  
            self.memory_limit_mb = 800
        else:
            # Low memory system - conservative limits
            self.memory_limit_mb = 600
            
        logger.info(f"MemoryMonitor adjusted for {self._system_memory_gb:.1f}GB system: limit={self.memory_limit_mb}MB")

    def check_memory_status(self) -> dict:
        """Enhanced memory status check with predictive analysis."""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # NOWY: Track memory history for trend analysis
            self._memory_history.append(memory_mb)
            if len(self._memory_history) > self._max_history:
                self._memory_history.pop(0)
            
            # NOWY: Calculate memory trend
            if len(self._memory_history) >= 3:
                recent_avg = sum(self._memory_history[-3:]) / 3
                older_avg = sum(self._memory_history[:-3]) / max(1, len(self._memory_history) - 3)
                self._memory_trend = recent_avg - older_avg

            # ULEPSZONY: More granular thresholds
            warning_threshold = self.memory_limit_mb * 0.7   # ZMIENIONO z 0.8 do 0.7
            critical_threshold = self.memory_limit_mb * 0.85  # ZMIENIONO z 1.0 do 0.85
            emergency_threshold = self.memory_limit_mb * 0.95 # NOWY: Emergency threshold

            status = {
                "memory_mb": memory_mb,
                "limit_mb": self.memory_limit_mb,
                "usage_percent": (memory_mb / self.memory_limit_mb) * 100,
                "high_usage": memory_mb > warning_threshold,
                "critical_usage": memory_mb > critical_threshold,
                "emergency_usage": memory_mb > emergency_threshold,  # NOWY
                "circuit_open": self.circuit_open,
                "memory_trend": self._memory_trend,  # NOWY
                "trend_warning": self._memory_trend > 50,  # NOWY: Rapid growth warning
            }

            # ULEPSZONY: Predictive circuit breaker logic
            if status["emergency_usage"] or (status["critical_usage"] and self._memory_trend > 30):
                self.high_memory_warnings += 1
                if self.high_memory_warnings >= 2:  # ZMIENIONO z 3 do 2
                    self.circuit_open = True
                    status["circuit_triggered"] = True
                    logger.error(f"CIRCUIT BREAKER TRIGGERED: {memory_mb:.0f}MB (trend: +{self._memory_trend:.1f}MB)")
            else:
                # ULEPSZONY: Faster recovery with hysteresis
                recovery_threshold = self.memory_limit_mb * 0.6  # ZMIENIONO z 0.7 do 0.6
                if memory_mb < recovery_threshold:
                    if self.high_memory_warnings > 0:
                        self.high_memory_warnings = max(0, self.high_memory_warnings - 1)
                    if self.high_memory_warnings == 0:
                        self.circuit_open = False

            return status

        except Exception as e:
            return {"error": str(e), "memory_mb": 0, "circuit_open": False}
```

---

### PATCH 2: ULEPSZENIE MEMORY MONITORING FREQUENCY

**Problem:** 10-sekundowy interval zbyt długi, memory spikes mogą wystąpić między checks
**Rozwiązanie:** Adaptive monitoring frequency based on memory pressure

```python
# PRZED (line 121-124):
# Start memory monitoring timer
self._memory_timer = QTimer()
self._memory_timer.timeout.connect(self._check_memory_pressure)
self._memory_timer.start(10000)  # ← PROBLEM: 10 sekund za długo

# PO:
# NOWY: Adaptive memory monitoring
self._memory_timer = QTimer()
self._memory_timer.timeout.connect(self._check_memory_pressure)
self._base_monitoring_interval = 5000  # ZMIENIONO z 10000 do 5000ms (5s)
self._current_monitoring_interval = self._base_monitoring_interval
self._memory_timer.start(self._current_monitoring_interval)

# NOWY: Memory pressure adaptive intervals
self._pressure_intervals = {
    "normal": 5000,    # 5s for normal operation
    "elevated": 3000,  # 3s when memory usage is elevated
    "high": 1000,      # 1s when memory usage is high
    "critical": 500,   # 0.5s when memory usage is critical
}

def _check_memory_pressure(self):
    """Enhanced memory pressure check with adaptive monitoring."""
    status = self.memory_monitor.check_memory_status()

    # NOWY: Determine monitoring frequency based on memory pressure
    if status.get("emergency_usage", False):
        new_interval = self._pressure_intervals["critical"]
        pressure_level = "CRITICAL"
    elif status.get("critical_usage", False):
        new_interval = self._pressure_intervals["high"] 
        pressure_level = "HIGH"
    elif status.get("high_usage", False):
        new_interval = self._pressure_intervals["elevated"]
        pressure_level = "ELEVATED"
    else:
        new_interval = self._pressure_intervals["normal"]
        pressure_level = "NORMAL"

    # NOWY: Adjust monitoring frequency if needed
    if new_interval != self._current_monitoring_interval:
        self._current_monitoring_interval = new_interval
        self._memory_timer.stop()
        self._memory_timer.start(new_interval)
        logger.debug(f"Memory monitoring adjusted to {new_interval}ms ({pressure_level} pressure)")

    # ULEPSZONY: Enhanced circuit breaker handling
    if status.get("circuit_triggered"):
        self.logger.error(
            f"CIRCUIT BREAKER: Memory limit exceeded ({status['memory_mb']:.0f}MB), "
            f"trend: +{status.get('memory_trend', 0):.1f}MB, cancelling operation"
        )
        self._emergency_cancel_operation()

        # NOWY: Enhanced user notification with trend info
        from PyQt6.QtWidgets import QMessageBox
        trend_info = ""
        if status.get('memory_trend', 0) > 20:
            trend_info = f"\nMemory growth trend: +{status['memory_trend']:.1f}MB"

        QMessageBox.warning(
            self.main_window,
            "Błąd pamięci",
            f"Operacja została anulowana z powodu zbyt wysokiego zużycia pamięci "
            f"({status['memory_mb']:.0f}MB z {status['limit_mb']:.0f}MB limit)."
            f"{trend_info}\n\n"
            f"Spróbuj ponownie z mniejszym folderem lub zamknij inne aplikacje.",
        )

    elif status.get("high_usage") or status.get("trend_warning"):
        # NOWY: Proactive warning for trending memory growth
        trend_msg = f" (trend: +{status.get('memory_trend', 0):.1f}MB)" if status.get('trend_warning') else ""
        self.logger.warning(
            f"MEMORY PRESSURE: {status['memory_mb']:.0f}MB "
            f"({status['usage_percent']:.1f}%){trend_msg}"
        )

        # NOWY: Proactive garbage collection for trending growth
        if status.get('trend_warning'):
            import gc
            collected = gc.collect()
            logger.info(f"Proactive GC: collected {collected} objects due to memory trend")
```

---

### PATCH 3: OPTYMALIZACJA CHUNKED BATCH PROCESSING

**Problem:** Statyczne chunk sizes (25 dla huge datasets) powodują overhead lub UI blocking
**Rozwiązanie:** Dynamic adaptive chunking based on performance metrics

```python
# PRZED (line 227-275):
def _safe_batch_processing_wrapper(self, original_method):
    def chunked_batch_processor(file_pairs_batch):
        num_pairs = len(file_pairs_batch)

        # ADAPTIVE CHUNKING: Smaller chunks for larger datasets
        if num_pairs > 1000:
            chunk_size = 25  # ← PROBLEM: Statyczne wartości
        elif num_pairs > 500:
            chunk_size = 50
        else:
            chunk_size = 100

# PO:
def _safe_batch_processing_wrapper(self, original_method):
    def chunked_batch_processor(file_pairs_batch):
        num_pairs = len(file_pairs_batch)

        # NOWY: Performance-based adaptive chunking
        chunk_size = self._calculate_optimal_chunk_size(num_pairs)
        
        # NOWY: Track processing metrics for optimization
        batch_start_time = time.time()
        chunks_processed = 0
        total_processing_time = 0

        # Process in adaptive chunks
        for i in range(0, len(file_pairs_batch), chunk_size):
            if self._processing_cancelled:
                self.logger.warning("Batch processing cancelled by user")
                return

            chunk = file_pairs_batch[i : i + chunk_size]
            chunk_start_time = time.time()

            try:
                # Call original method with adaptive chunk
                original_method(chunk)
                
                chunk_processing_time = time.time() - chunk_start_time
                total_processing_time += chunk_processing_time
                chunks_processed += 1

                # NOWY: Dynamic chunk size adjustment based on performance
                if chunks_processed % 5 == 0:  # Adjust every 5 chunks
                    avg_chunk_time = total_processing_time / chunks_processed
                    chunk_size = self._adjust_chunk_size_based_on_performance(
                        chunk_size, avg_chunk_time, num_pairs
                    )

                # Allow UI to process events after each chunk
                from PyQt6.QtWidgets import QApplication
                QApplication.processEvents()

                # NOWY: Adaptive memory cleanup frequency
                if chunks_processed % self._get_gc_interval_for_chunk_size(chunk_size) == 0:
                    memory_status = self.memory_monitor.check_memory_status()
                    if memory_status.get("high_usage", False):
                        import gc
                        gc.collect()

            except Exception as e:
                self.logger.error(f"Chunk processing error at {i}-{i+chunk_size}: {e}")
                continue

            # NOWY: Adaptive pause based on system performance
            pause_duration = self._calculate_adaptive_pause(chunk_processing_time, num_pairs)
            if pause_duration > 0:
                time.sleep(pause_duration)

        return chunked_batch_processor

def _calculate_optimal_chunk_size(self, total_pairs: int) -> int:
    """Calculate optimal chunk size based on system capabilities and dataset size."""
    # Base chunk size calculation
    if total_pairs <= 100:
        base_chunk_size = 50
    elif total_pairs <= 500:
        base_chunk_size = 40
    elif total_pairs <= 1000:
        base_chunk_size = 30
    elif total_pairs <= 2000:
        base_chunk_size = 20
    else:
        base_chunk_size = 15

    # NOWY: Adjust based on available memory
    memory_status = self.memory_monitor.check_memory_status()
    memory_factor = 1.0
    
    if memory_status.get("high_usage", False):
        memory_factor = 0.6  # Reduce chunk size under memory pressure
    elif memory_status.get("critical_usage", False):
        memory_factor = 0.4  # Significantly reduce under critical pressure
    elif memory_status.get("emergency_usage", False):
        memory_factor = 0.2  # Minimal chunks under emergency
    
    # NOWY: Adjust based on system performance
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)
        if cpu_percent > 80:
            memory_factor *= 0.8  # Reduce chunk size under high CPU load
    except:
        pass

    optimal_chunk_size = max(5, int(base_chunk_size * memory_factor))
    
    self.logger.debug(f"Calculated optimal chunk size: {optimal_chunk_size} for {total_pairs} pairs (factor: {memory_factor:.2f})")
    return optimal_chunk_size

def _adjust_chunk_size_based_on_performance(self, current_chunk_size: int, avg_chunk_time: float, total_pairs: int) -> int:
    """Dynamically adjust chunk size based on processing performance."""
    target_chunk_time = 0.05  # Target: 50ms per chunk for UI responsiveness
    
    if avg_chunk_time > target_chunk_time * 1.5:  # Too slow
        # Reduce chunk size
        new_chunk_size = max(5, int(current_chunk_size * 0.8))
        self.logger.debug(f"Reducing chunk size: {current_chunk_size} → {new_chunk_size} (avg time: {avg_chunk_time:.3f}s)")
    elif avg_chunk_time < target_chunk_time * 0.5:  # Too fast, can increase
        # Increase chunk size but cap based on memory pressure
        memory_status = self.memory_monitor.check_memory_status()
        if not memory_status.get("high_usage", False):
            max_increase = int(current_chunk_size * 1.2)
            new_chunk_size = min(max_increase, 100)  # Cap at 100
            self.logger.debug(f"Increasing chunk size: {current_chunk_size} → {new_chunk_size} (avg time: {avg_chunk_time:.3f}s)")
        else:
            new_chunk_size = current_chunk_size  # No increase under memory pressure
    else:
        new_chunk_size = current_chunk_size  # Optimal performance

    return new_chunk_size

def _calculate_adaptive_pause(self, chunk_processing_time: float, total_pairs: int) -> float:
    """Calculate adaptive pause duration based on processing performance."""
    if total_pairs <= 1000:
        return 0.0  # No pause for smaller datasets
    
    # Base pause calculation
    base_pause = 0.001  # 1ms base pause
    
    # Longer pause for very large datasets to prevent system overload
    if total_pairs > 5000:
        base_pause = 0.005  # 5ms for huge datasets
    elif total_pairs > 2000:
        base_pause = 0.002  # 2ms for large datasets
    
    # Adjust pause based on chunk processing time
    if chunk_processing_time > 0.1:  # Slow processing
        return base_pause * 2  # Longer pause to let system recover
    elif chunk_processing_time < 0.02:  # Fast processing
        return base_pause * 0.5  # Shorter pause for efficiency
    
    return base_pause

def _get_gc_interval_for_chunk_size(self, chunk_size: int) -> int:
    """Get appropriate GC interval based on chunk size."""
    if chunk_size <= 10:
        return 10  # More frequent GC for small chunks
    elif chunk_size <= 20:
        return 8
    elif chunk_size <= 30:
        return 6
    else:
        return 5   # More frequent GC for larger chunks
```

---

### PATCH 4: ENHANCED PERFORMANCE METRICS

**Problem:** get_performance_metrics może powodować memory overhead, brak predictive insights
**Rozwiązanie:** Lightweight metrics with predictive analysis

```python
# PRZED (line 193-204):
def get_performance_metrics(self) -> dict:
    with self._state_lock:
        memory_status = self.memory_monitor.check_memory_status()

        return {
            "worker_state": self._worker_state.value,
            "memory_status": memory_status,
            "worker_metrics": self._worker_metrics.copy(),  # ← PROBLEM: Potencjalny memory overhead
            "active_workers": len(self.active_workers),
            "thread_pool_active": QThreadPool.globalInstance().activeThreadCount(),
        }

# PO:
def get_performance_metrics(self) -> dict:
    """Enhanced performance metrics with predictive analysis."""
    with self._state_lock:
        memory_status = self.memory_monitor.check_memory_status()
        
        # NOWY: Lightweight metrics calculation
        current_time = time.time()
        
        # NOWY: Calculate processing efficiency
        processing_efficiency = 0.0
        if self._worker_metrics.get("start_time") and self._worker_metrics.get("pairs_processed", 0) > 0:
            elapsed_time = current_time - self._worker_metrics["start_time"]
            if elapsed_time > 0:
                processing_efficiency = self._worker_metrics["pairs_processed"] / elapsed_time

        # NOWY: Predict completion time
        estimated_completion = None
        if (processing_efficiency > 0 and 
            hasattr(self.main_window, 'controller') and 
            self.main_window.controller.current_file_pairs):
            
            total_pairs = len(self.main_window.controller.current_file_pairs)
            remaining_pairs = total_pairs - self._worker_metrics.get("pairs_processed", 0)
            if remaining_pairs > 0:
                estimated_seconds = remaining_pairs / processing_efficiency
                estimated_completion = current_time + estimated_seconds

        # ULEPSZONY: Lightweight metrics object
        metrics = {
            "worker_state": self._worker_state.value,
            "memory_status": {
                "memory_mb": memory_status.get("memory_mb", 0),
                "usage_percent": memory_status.get("usage_percent", 0),
                "high_usage": memory_status.get("high_usage", False),
                "critical_usage": memory_status.get("critical_usage", False),
                "circuit_open": memory_status.get("circuit_open", False),
                "memory_trend": memory_status.get("memory_trend", 0),
            },
            # NOWY: Essential metrics only to reduce memory overhead
            "processing_metrics": {
                "pairs_processed": self._worker_metrics.get("pairs_processed", 0),
                "processing_efficiency": processing_efficiency,
                "estimated_completion": estimated_completion,
                "errors_count": self._worker_metrics.get("errors_count", 0),
            },
            "system_metrics": {
                "active_workers": len(self.active_workers),
                "thread_pool_active": QThreadPool.globalInstance().activeThreadCount(),
                "monitoring_interval": getattr(self, '_current_monitoring_interval', 5000),
            },
            # NOWY: Health indicators
            "health_indicators": {
                "memory_pressure": self._calculate_memory_pressure_level(memory_status),
                "processing_health": self._calculate_processing_health(),
                "system_stability": self._calculate_system_stability(),
            }
        }

        return metrics

def _calculate_memory_pressure_level(self, memory_status: dict) -> str:
    """Calculate memory pressure level for health monitoring."""
    if memory_status.get("emergency_usage", False):
        return "EMERGENCY"
    elif memory_status.get("critical_usage", False):
        return "CRITICAL" 
    elif memory_status.get("high_usage", False):
        return "HIGH"
    elif memory_status.get("memory_trend", 0) > 30:
        return "TRENDING_UP"
    else:
        return "NORMAL"

def _calculate_processing_health(self) -> str:
    """Calculate processing health based on metrics."""
    errors_count = self._worker_metrics.get("errors_count", 0)
    pairs_processed = self._worker_metrics.get("pairs_processed", 0)
    
    if pairs_processed == 0:
        return "STARTING"
    
    error_rate = errors_count / pairs_processed if pairs_processed > 0 else 0
    
    if error_rate > 0.1:  # >10% error rate
        return "DEGRADED"
    elif error_rate > 0.05:  # >5% error rate
        return "WARNING"
    else:
        return "HEALTHY"

def _calculate_system_stability(self) -> str:
    """Calculate overall system stability."""
    memory_pressure = self._calculate_memory_pressure_level(self.memory_monitor.check_memory_status())
    processing_health = self._calculate_processing_health()
    
    if memory_pressure in ["EMERGENCY", "CRITICAL"] or processing_health == "DEGRADED":
        return "UNSTABLE"
    elif memory_pressure in ["HIGH", "TRENDING_UP"] or processing_health == "WARNING":
        return "STRESSED"
    else:
        return "STABLE"
```

---

## ✅ CHECKLISTA WERYFIKACYJNA

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Memory circuit breaker** - aktywacja przy 850MB (85% z 1000MB), recovery przy 600MB
- [ ] **Adaptive monitoring** - frequency adjustment 5s→0.5s based on memory pressure  
- [ ] **Worker management** - graceful handling pod memory pressure
- [ ] **Batch processing** - adaptive chunk sizing, no UI blocking
- [ ] **Performance metrics** - lightweight calculation, predictive insights
- [ ] **Error handling** - graceful degradation under memory constraints
- [ ] **User notifications** - informative memory pressure alerts
- [ ] **Thread safety** - safe operation z adaptive intervals

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **DataProcessingWorker integration** - proper signal handling under memory pressure
- [ ] **TileManager cooperation** - coordinated batch processing optimization
- [ ] **GalleryManager integration** - smooth data flow bez memory spikes
- [ ] **QThreadPool management** - proper resource allocation i cleanup
- [ ] **Scanner core cooperation** - compatible memory management strategies

#### **TESTY WERYFIKACYJNE:**

- [ ] **Memory pressure test** - circuit breaker activation <10s
- [ ] **Adaptive chunking test** - optimal performance across dataset sizes
- [ ] **Recovery test** - graceful recovery po circuit breaker activation
- [ ] **UI responsiveness test** - no blocking during worker operations

#### **KRYTERIA SUKCESU:**

- [ ] **MEMORY CIRCUIT BREAKER <1000MB** - proactive protection
- [ ] **NO HIGH_MEMORY WARNINGS** przy normalnym użyciu <800MB
- [ ] **ADAPTIVE MONITORING EFFECTIVE** - 5s→0.5s frequency adjustment
- [ ] **UI RESPONSIVENESS MAINTAINED** - worker operations nie blokują UI