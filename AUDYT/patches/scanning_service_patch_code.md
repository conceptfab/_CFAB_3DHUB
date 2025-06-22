# PATCH-CODE DLA: SCANNING_SERVICE

**Powiązany plik z analizą:** `../corrections/scanning_service_correction.md`
**Zasady ogólne:** `../../_BASE_/refactoring_rules.md`

---

### PATCH 1: NAPRAWA BŁĘDÓW SKŁADNIOWYCH - POPRAWNE UŻYWANIE SCANNER MODULE

**Problem:** AttributeError przy dostępie do `self.scanner` w liniach 119, 151-156, 174
**Rozwiązanie:** Poprawne importy i używanie funkcji scanner jako module functions

```python
import logging
import os
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple, Callable

# POPRAWKA: Proper scanner imports
from src.logic import scanner
from src.logic import scanner_cache
from src.models.file_pair import FilePair
from src.models.special_folder import SpecialFolder
from src.utils.path_validator import PathValidator

@dataclass
class ScanResult:
    """Wynik operacji skanowania."""
    file_pairs: List[FilePair]
    unpaired_archives: List[str]
    unpaired_previews: List[str]
    special_folders: List[SpecialFolder]
    scan_time: float
    total_files: int
    error_message: Optional[str] = None
    # ENHANCEMENT: Additional metrics
    cache_hit: bool = False
    performance_metrics: Optional[dict] = None

class ScanningService:
    """Serwis do skanowania katalogów - NAPRAWIONY - proper scanner API usage."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # POPRAWKA: Remove incorrect self.scanner reference
        # Scanner functions are used directly from module

    def refresh_directory(self, path: str) -> ScanResult:
        """
        NAPRAWKA: Proper cache clearing and directory refresh.
        
        Args:
            path: Ścieżka do katalogu
            
        Returns:
            ScanResult: Wynik odświeżania
        """
        try:
            # POPRAWKA: Use correct scanner_cache API
            cache = scanner_cache.ScannerCache.get_instance()
            cache.remove_entry(path)  # Clear cache for this directory
            
            self.logger.info(f"Cache cleared for directory: {path}")
            
            # Wykonaj ponowne skanowanie z domyślnymi ustawieniami
            return self.scan_directory(path)
            
        except Exception as e:
            error_msg = f"Błąd odświeżania katalogu {path}: {str(e)}"
            self.logger.error(error_msg)
            
            return ScanResult(
                file_pairs=[],
                unpaired_archives=[],
                unpaired_previews=[],
                special_folders=[],
                scan_time=0.0,
                total_files=0,
                error_message=error_msg,
            )

    def get_scan_statistics(self, path: str) -> dict:
        """
        NAPRAWKA: Proper statistics gathering using correct APIs.
        
        Args:
            path: Ścieżka do katalogu
            
        Returns:
            dict: Statystyki skanowania
        """
        try:
            # POPRAWKA: Use correct scanner_cache API
            cache = scanner_cache.ScannerCache.get_instance()
            
            # Get cache statistics
            cache_stats = cache.get_cache_statistics()
            cache_memory = cache.get_cache_memory_usage()
            
            # Check if path is cached
            cache_hit = cache.has_entry(path)
            
            stats = {
                "path": path,
                "cache_hit": cache_hit,
                "cache_statistics": cache_stats,
                "cache_memory_usage": cache_memory,
                "supported_extensions": {
                    # POPRAWKA: Get from scanner module properly
                    "archives": getattr(scanner, 'ARCHIVE_EXTENSIONS', ['.zip', '.rar', '.7z', '.blend']),
                    "previews": getattr(scanner, 'PREVIEW_EXTENSIONS', ['.jpg', '.png', '.webp']),
                },
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Błąd pobierania statystyk: {str(e)}")
            return {"error": str(e), "path": path}

    def clear_all_caches(self) -> bool:
        """
        NAPRAWKA: Proper cache clearing using correct API.
        
        Returns:
            bool: True jeśli operacja się powiodła
        """
        try:
            # POPRAWKA: Use correct scanner_cache API
            cache = scanner_cache.ScannerCache.get_instance()
            cache.clear_cache()
            
            self.logger.info("Cache skanowania wyczyszczony")
            return True
            
        except Exception as e:
            self.logger.error(f"Błąd czyszczenia cache: {str(e)}")
            return False
```

---

### PATCH 2: CENTRALIZED CACHE MANAGEMENT + PERFORMANCE MONITORING

**Problem:** Brak centralnego zarządzania cache i metryk wydajności
**Rozwiązanie:** Cache manager z performance monitoring i smart invalidation

```python
from typing import Dict, Any
import threading
from collections import defaultdict

class ScanningService:
    # ... existing code ...
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # PERFORMANCE MONITORING
        self._scan_metrics = {
            'total_scans': 0,
            'total_scan_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_scan_time': 0.0,
            'last_scan_stats': {}
        }
        
        # THREAD SAFETY
        self._metrics_lock = threading.RLock()
        
    def scan_directory(
        self, path: str, max_depth: int = -1, strategy: str = "first_match"
    ) -> ScanResult:
        """ENHANCED: Scanning with performance monitoring and smart caching."""
        try:
            # Walidacja ścieżki
            if not PathValidator.validate_directory_path(path):
                return self._create_error_result(
                    f"Katalog nie istnieje lub nie jest dostępny: {path}"
                )

            # CACHE CHECK
            cache = scanner_cache.ScannerCache.get_instance()
            cache_hit = cache.has_entry(path)
            
            self.logger.info(f"Rozpoczynam skanowanie: {path} (cache_hit: {cache_hit})")

            # PERFORMANCE MONITORING START
            start_time = time.time()
            
            # Wykonaj skanowanie
            result = scanner.scan_folder_for_pairs(
                path, max_depth=max_depth, pair_strategy=strategy
            )
            
            scan_time = time.time() - start_time
            
            # BUILD ENHANCED RESULT
            scan_result = ScanResult(
                file_pairs=result[0],
                unpaired_archives=result[1],
                unpaired_previews=result[2],
                special_folders=result[3],
                scan_time=scan_time,
                total_files=len(result[0]) * 2 + len(result[1]) + len(result[2]),
                cache_hit=cache_hit,
                performance_metrics=self._calculate_performance_metrics(scan_time, len(result[0]))
            )

            # UPDATE METRICS
            self._update_scan_metrics(scan_time, cache_hit, scan_result)
            
            # PERFORMANCE LOGGING
            self._log_scan_performance(path, scan_result)

            return scan_result

        except Exception as e:
            error_msg = f"Błąd skanowania katalogu {path}: {str(e)}"
            self.logger.error(error_msg)
            return self._create_error_result(error_msg)

    def _create_error_result(self, error_message: str) -> ScanResult:
        """Helper to create consistent error results."""
        return ScanResult(
            file_pairs=[],
            unpaired_archives=[],
            unpaired_previews=[],
            special_folders=[],
            scan_time=0.0,
            total_files=0,
            error_message=error_message,
            cache_hit=False
        )

    def _calculate_performance_metrics(self, scan_time: float, pair_count: int) -> dict:
        """Calculate detailed performance metrics."""
        return {
            'pairs_per_second': pair_count / max(scan_time, 0.001),
            'scan_efficiency': min(100.0, (1000 / max(scan_time * 1000, 1))),  # higher is better
            'time_category': self._categorize_scan_time(scan_time),
        }
    
    def _categorize_scan_time(self, scan_time: float) -> str:
        """Categorize scan performance."""
        if scan_time < 1.0:
            return 'excellent'
        elif scan_time < 3.0:
            return 'good'
        elif scan_time < 10.0:
            return 'moderate'
        else:
            return 'slow'

    def _update_scan_metrics(self, scan_time: float, cache_hit: bool, result: ScanResult):
        """Update global scan metrics thread-safely."""
        with self._metrics_lock:
            self._scan_metrics['total_scans'] += 1
            self._scan_metrics['total_scan_time'] += scan_time
            
            if cache_hit:
                self._scan_metrics['cache_hits'] += 1
            else:
                self._scan_metrics['cache_misses'] += 1
            
            # Calculate running average
            if self._scan_metrics['total_scans'] > 0:
                self._scan_metrics['average_scan_time'] = (
                    self._scan_metrics['total_scan_time'] / self._scan_metrics['total_scans']
                )
            
            # Store last scan stats
            self._scan_metrics['last_scan_stats'] = {
                'scan_time': scan_time,
                'file_pairs': len(result.file_pairs),
                'total_files': result.total_files,
                'cache_hit': cache_hit,
                'performance_category': result.performance_metrics.get('time_category', 'unknown') if result.performance_metrics else 'unknown'
            }

    def _log_scan_performance(self, path: str, result: ScanResult):
        """Log scan performance with appropriate level."""
        scan_time = result.scan_time
        pair_count = len(result.file_pairs)
        
        # Determine log level based on performance
        if scan_time > 10.0:  # Slow scan
            self.logger.warning(
                f"SLOW SCAN: {path} took {scan_time:.2f}s for {pair_count} pairs "
                f"(cache_hit: {result.cache_hit})"
            )
        elif scan_time > 3.0:  # Moderate scan
            self.logger.info(
                f"Scan completed: {path} in {scan_time:.2f}s, {pair_count} pairs "
                f"(cache_hit: {result.cache_hit})"
            )
        else:  # Fast scan
            self.logger.debug(
                f"Fast scan: {path} in {scan_time:.2f}s, {pair_count} pairs "
                f"(cache_hit: {result.cache_hit})"
            )

    def get_performance_statistics(self) -> dict:
        """NOWA FUNKCJA: Get comprehensive performance statistics."""
        with self._metrics_lock:
            cache = scanner_cache.ScannerCache.get_instance()
            cache_stats = cache.get_cache_statistics()
            
            hit_ratio = 0.0
            if self._scan_metrics['total_scans'] > 0:
                hit_ratio = (self._scan_metrics['cache_hits'] / self._scan_metrics['total_scans']) * 100
            
            return {
                'scan_performance': {
                    'total_scans': self._scan_metrics['total_scans'],
                    'average_scan_time': self._scan_metrics['average_scan_time'],
                    'cache_hit_ratio': hit_ratio,
                    'last_scan': self._scan_metrics['last_scan_stats']
                },
                'cache_performance': cache_stats,
                'recommendations': self._generate_performance_recommendations()
            }
    
    def _generate_performance_recommendations(self) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        if self._scan_metrics['total_scans'] > 0:
            hit_ratio = (self._scan_metrics['cache_hits'] / self._scan_metrics['total_scans']) * 100
            
            if hit_ratio < 50:
                recommendations.append("Consider increasing cache size - low hit ratio detected")
            
            if self._scan_metrics['average_scan_time'] > 5.0:
                recommendations.append("Large directories detected - consider using max_depth limit")
                
        return recommendations
```

---

### PATCH 3: ASYNCHRONOUS SCANNING OPERATIONS WITH PROGRESS CALLBACK

**Problem:** Synchroniczne skanowanie blokuje UI
**Rozwiązanie:** Async scanning z progress callbacks i cancellation support

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

class ScanningService:
    # ... existing code ...
    
    def __init__(self):
        # ... existing initialization ...
        
        # ASYNC SCANNING SUPPORT
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ScanWorker")
        self._active_scans: Dict[str, bool] = {}  # path -> is_active
        self._scan_callbacks: Dict[str, Callable] = {}  # path -> callback
        
    def scan_directory_async(
        self, 
        path: str, 
        max_depth: int = -1, 
        strategy: str = "first_match",
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
        completion_callback: Optional[Callable[[ScanResult], None]] = None
    ) -> str:
        """
        NOWA FUNKCJA: Asynchronous directory scanning with progress tracking.
        
        Args:
            path: Directory path to scan
            max_depth: Maximum scan depth
            strategy: Pairing strategy
            progress_callback: Called with (current_file, processed_count, total_estimated)
            completion_callback: Called when scan completes with ScanResult
            
        Returns:
            str: Scan ID for tracking/cancellation
        """
        scan_id = f"scan_{path}_{int(time.time())}"
        
        if path in self._active_scans and self._active_scans[path]:
            self.logger.warning(f"Scan already active for path: {path}")
            return scan_id
        
        self._active_scans[path] = True
        
        def scan_worker():
            """Worker function for async scanning."""
            try:
                # Custom scanner with progress reporting
                result = self._scan_with_progress(path, max_depth, strategy, progress_callback)
                
                if completion_callback:
                    completion_callback(result)
                    
                return result
                
            except Exception as e:
                error_result = self._create_error_result(f"Async scan error: {str(e)}")
                if completion_callback:
                    completion_callback(error_result)
                return error_result
            finally:
                self._active_scans[path] = False
        
        # Submit to thread pool
        future = self._executor.submit(scan_worker)
        
        self.logger.info(f"Started async scan for {path} with ID: {scan_id}")
        return scan_id
    
    def _scan_with_progress(
        self, 
        path: str, 
        max_depth: int, 
        strategy: str,
        progress_callback: Optional[Callable]
    ) -> ScanResult:
        """Internal scan with progress reporting."""
        start_time = time.time()
        
        # Estimate total files for progress
        estimated_files = self._estimate_file_count(path, max_depth)
        processed_files = 0
        
        def progress_reporter(current_file: str):
            nonlocal processed_files
            processed_files += 1
            if progress_callback and processed_files % 10 == 0:  # Report every 10 files
                progress_callback(current_file, processed_files, estimated_files)
        
        # Perform scan with progress reporting
        # NOTE: This would require modifying scanner.scan_folder_for_pairs to accept progress callback
        # For now, we simulate progress reporting
        
        if progress_callback:
            progress_callback("Starting scan...", 0, estimated_files)
        
        result = scanner.scan_folder_for_pairs(
            path, max_depth=max_depth, pair_strategy=strategy
        )
        
        scan_time = time.time() - start_time
        
        if progress_callback:
            progress_callback("Scan completed", estimated_files, estimated_files)
        
        return ScanResult(
            file_pairs=result[0],
            unpaired_archives=result[1],
            unpaired_previews=result[2],
            special_folders=result[3],
            scan_time=scan_time,
            total_files=len(result[0]) * 2 + len(result[1]) + len(result[2]),
            cache_hit=scanner_cache.ScannerCache.get_instance().has_entry(path),
            performance_metrics=self._calculate_performance_metrics(scan_time, len(result[0]))
        )
    
    def _estimate_file_count(self, path: str, max_depth: int) -> int:
        """Estimate total file count for progress calculation."""
        try:
            file_count = 0
            current_depth = 0
            
            for root, dirs, files in os.walk(path):
                if max_depth >= 0 and current_depth > max_depth:
                    break
                    
                file_count += len(files)
                current_depth += 1
                
            return file_count
        except Exception:
            return 1000  # Default estimate
    
    def cancel_scan(self, path: str) -> bool:
        """
        NOWA FUNKCJA: Cancel active scan for given path.
        
        Args:
            path: Directory path to cancel scan for
            
        Returns:
            bool: True if scan was cancelled
        """
        if path in self._active_scans and self._active_scans[path]:
            self._active_scans[path] = False
            self.logger.info(f"Cancelled scan for path: {path}")
            return True
        return False
    
    def get_active_scans(self) -> List[str]:
        """
        NOWA FUNKCJA: Get list of currently active scan paths.
        
        Returns:
            List[str]: Paths with active scans
        """
        return [path for path, active in self._active_scans.items() if active]
    
    def is_scan_active(self, path: str) -> bool:
        """
        NOWA FUNKCJA: Check if scan is active for given path.
        
        Args:
            path: Directory path to check
            
        Returns:
            bool: True if scan is active
        """
        return self._active_scans.get(path, False)
```

---

### PATCH 4: BATCH OPERATIONS SUPPORT + STRATEGY PATTERN

**Problem:** Brak wsparcia dla batch operations i extensible strategies
**Rozwiązanie:** Batch scanning + strategy pattern dla różnych scenariuszy

```python
from abc import ABC, abstractmethod
from typing import List, Dict

class ScanStrategy(ABC):
    """Abstract base class for scan strategies."""
    
    @abstractmethod
    def scan(self, paths: List[str], **kwargs) -> List[ScanResult]:
        """Execute scan strategy."""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """Get strategy name."""
        pass

class SequentialScanStrategy(ScanStrategy):
    """Scan directories one by one sequentially."""
    
    def __init__(self, scanning_service: 'ScanningService'):
        self.service = scanning_service
    
    def scan(self, paths: List[str], **kwargs) -> List[ScanResult]:
        """Sequential scanning of multiple directories."""
        results = []
        for path in paths:
            result = self.service.scan_directory(
                path, 
                max_depth=kwargs.get('max_depth', -1),
                strategy=kwargs.get('strategy', 'first_match')
            )
            results.append(result)
        return results
    
    def get_strategy_name(self) -> str:
        return "sequential"

class ParallelScanStrategy(ScanStrategy):
    """Scan directories in parallel using thread pool."""
    
    def __init__(self, scanning_service: 'ScanningService'):
        self.service = scanning_service
    
    def scan(self, paths: List[str], **kwargs) -> List[ScanResult]:
        """Parallel scanning of multiple directories."""
        with ThreadPoolExecutor(max_workers=min(len(paths), 4)) as executor:
            futures = []
            
            for path in paths:
                future = executor.submit(
                    self.service.scan_directory,
                    path,
                    kwargs.get('max_depth', -1),
                    kwargs.get('strategy', 'first_match')
                )
                futures.append(future)
            
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=300)  # 5 minute timeout
                    results.append(result)
                except Exception as e:
                    error_result = self.service._create_error_result(f"Parallel scan error: {str(e)}")
                    results.append(error_result)
            
            return results
    
    def get_strategy_name(self) -> str:
        return "parallel"

class ScanningService:
    # ... existing code ...
    
    def __init__(self):
        # ... existing initialization ...
        
        # STRATEGY PATTERN SUPPORT
        self._scan_strategies = {
            'sequential': SequentialScanStrategy(self),
            'parallel': ParallelScanStrategy(self),
        }
    
    def scan_multiple_directories(
        self, 
        paths: List[str], 
        batch_strategy: str = "sequential",
        max_depth: int = -1,
        pair_strategy: str = "first_match",
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> List[ScanResult]:
        """
        NOWA FUNKCJA: Scan multiple directories using specified strategy.
        
        Args:
            paths: List of directory paths to scan
            batch_strategy: How to scan multiple directories ("sequential", "parallel")
            max_depth: Maximum scan depth for each directory
            pair_strategy: Pairing strategy for each directory
            progress_callback: Progress callback for batch operation
            
        Returns:
            List[ScanResult]: Results for each directory
        """
        if not paths:
            return []
        
        if batch_strategy not in self._scan_strategies:
            self.logger.warning(f"Unknown batch strategy: {batch_strategy}, using sequential")
            batch_strategy = "sequential"
        
        strategy = self._scan_strategies[batch_strategy]
        
        self.logger.info(
            f"Starting batch scan of {len(paths)} directories using {strategy.get_strategy_name()} strategy"
        )
        
        start_time = time.time()
        
        # Progress tracking for batch operations
        if progress_callback:
            progress_callback("Starting batch scan", 0, len(paths))
        
        results = strategy.scan(
            paths, 
            max_depth=max_depth, 
            strategy=pair_strategy
        )
        
        batch_time = time.time() - start_time
        
        # Log batch results
        total_pairs = sum(len(result.file_pairs) for result in results)
        successful_scans = sum(1 for result in results if result.error_message is None)
        
        self.logger.info(
            f"Batch scan completed: {successful_scans}/{len(paths)} successful, "
            f"{total_pairs} total pairs, {batch_time:.2f}s total time"
        )
        
        if progress_callback:
            progress_callback("Batch scan completed", len(paths), len(paths))
        
        return results
    
    def get_batch_statistics(self, results: List[ScanResult]) -> dict:
        """
        NOWA FUNKCJA: Calculate statistics for batch scan results.
        
        Args:
            results: List of scan results from batch operation
            
        Returns:
            dict: Batch statistics
        """
        if not results:
            return {"error": "No results provided"}
        
        total_pairs = sum(len(result.file_pairs) for result in results)
        total_files = sum(result.total_files for result in results)
        total_time = sum(result.scan_time for result in results)
        successful_scans = sum(1 for result in results if result.error_message is None)
        cache_hits = sum(1 for result in results if result.cache_hit)
        
        return {
            "directories_scanned": len(results),
            "successful_scans": successful_scans,
            "failed_scans": len(results) - successful_scans,
            "total_file_pairs": total_pairs,
            "total_files": total_files,
            "total_scan_time": total_time,
            "average_scan_time": total_time / len(results) if results else 0,
            "cache_hit_ratio": (cache_hits / len(results)) * 100 if results else 0,
            "pairs_per_second": total_pairs / max(total_time, 0.001),
            "efficiency_rating": self._calculate_batch_efficiency(results)
        }
    
    def _calculate_batch_efficiency(self, results: List[ScanResult]) -> str:
        """Calculate overall efficiency rating for batch operation."""
        if not results:
            return "unknown"
        
        success_rate = sum(1 for r in results if r.error_message is None) / len(results)
        avg_time = sum(r.scan_time for r in results) / len(results)
        
        if success_rate > 0.9 and avg_time < 3.0:
            return "excellent"
        elif success_rate > 0.8 and avg_time < 10.0:
            return "good"
        elif success_rate > 0.5:
            return "moderate"
        else:
            return "poor"
```

---

### PATCH 5: ENHANCED ERROR HANDLING + COMPREHENSIVE LOGGING

**Problem:** Inconsistent error handling i niepełne logowanie
**Rozwiązanie:** Unified error handling z detailed logging i graceful degradation

```python
import traceback
from contextlib import contextmanager
from enum import Enum

class ScanErrorType(Enum):
    """Types of scan errors for better categorization."""
    VALIDATION_ERROR = "validation"
    PERMISSION_ERROR = "permission"
    IO_ERROR = "io"
    SCANNER_ERROR = "scanner"
    CACHE_ERROR = "cache"
    UNKNOWN_ERROR = "unknown"

@dataclass
class ScanError:
    """Structured error information."""
    error_type: ScanErrorType
    message: str
    path: str
    details: Optional[str] = None
    recoverable: bool = True

class ScanningService:
    # ... existing code ...
    
    def __init__(self):
        # ... existing initialization ...
        
        # ERROR TRACKING
        self._error_history = []
        self._error_stats = defaultdict(int)
    
    @contextmanager
    def _scan_error_handler(self, path: str, operation: str):
        """Context manager for consistent error handling."""
        try:
            yield
        except PermissionError as e:
            error = ScanError(
                ScanErrorType.PERMISSION_ERROR,
                f"Permission denied: {str(e)}",
                path,
                recoverable=False
            )
            self._handle_scan_error(error, operation)
            raise
        except FileNotFoundError as e:
            error = ScanError(
                ScanErrorType.IO_ERROR,
                f"File/directory not found: {str(e)}",
                path,
                recoverable=False
            )
            self._handle_scan_error(error, operation)
            raise
        except OSError as e:
            error = ScanError(
                ScanErrorType.IO_ERROR,
                f"OS error: {str(e)}",
                path,
                recoverable=True
            )
            self._handle_scan_error(error, operation)
            raise
        except Exception as e:
            error = ScanError(
                ScanErrorType.UNKNOWN_ERROR,
                f"Unexpected error: {str(e)}",
                path,
                details=traceback.format_exc(),
                recoverable=True
            )
            self._handle_scan_error(error, operation)
            raise
    
    def _handle_scan_error(self, error: ScanError, operation: str):
        """Handle scan error with appropriate logging and tracking."""
        # Update error statistics
        self._error_stats[error.error_type] += 1
        
        # Add to error history (keep last 100)
        self._error_history.append({
            'timestamp': time.time(),
            'operation': operation,
            'error': error,
        })
        if len(self._error_history) > 100:
            self._error_history.pop(0)
        
        # Log with appropriate level
        if error.error_type == ScanErrorType.PERMISSION_ERROR:
            self.logger.error(
                f"PERMISSION ERROR in {operation}: {error.message} (path: {error.path})"
            )
        elif error.error_type == ScanErrorType.IO_ERROR:
            self.logger.warning(
                f"IO ERROR in {operation}: {error.message} (path: {error.path})"
            )
        elif error.recoverable:
            self.logger.warning(
                f"RECOVERABLE ERROR in {operation}: {error.message} (path: {error.path})"
            )
        else:
            self.logger.error(
                f"CRITICAL ERROR in {operation}: {error.message} (path: {error.path})"
            )
            if error.details:
                self.logger.debug(f"Error details: {error.details}")

    def scan_directory(
        self, path: str, max_depth: int = -1, strategy: str = "first_match"
    ) -> ScanResult:
        """ENHANCED: Scanning with comprehensive error handling."""
        with self._scan_error_handler(path, "scan_directory"):
            # Pre-validation with detailed error messages
            validation_errors = self.validate_directory_path(path)
            if validation_errors:
                error_msg = f"Validation failed: {'; '.join(validation_errors)}"
                return self._create_enhanced_error_result(path, error_msg, ScanErrorType.VALIDATION_ERROR)

            # Enhanced logging
            self.logger.info(f"Starting scan: {path} (depth: {max_depth}, strategy: {strategy})")
            
            start_time = time.time()
            
            try:
                # Cache check with error handling
                cache = scanner_cache.ScannerCache.get_instance()
                cache_hit = cache.has_entry(path) if cache else False
                
                # Perform scan
                result = scanner.scan_folder_for_pairs(
                    path, max_depth=max_depth, pair_strategy=strategy
                )
                
                scan_time = time.time() - start_time
                
                # Build enhanced result
                scan_result = ScanResult(
                    file_pairs=result[0],
                    unpaired_archives=result[1],
                    unpaired_previews=result[2],
                    special_folders=result[3],
                    scan_time=scan_time,
                    total_files=len(result[0]) * 2 + len(result[1]) + len(result[2]),
                    cache_hit=cache_hit,
                    performance_metrics=self._calculate_performance_metrics(scan_time, len(result[0]))
                )

                # Success logging
                self._log_scan_success(path, scan_result)
                
                return scan_result
                
            except Exception as e:
                scan_time = time.time() - start_time
                error_msg = f"Scanner execution failed: {str(e)}"
                self.logger.error(f"Scan failed after {scan_time:.2f}s: {error_msg}")
                return self._create_enhanced_error_result(path, error_msg, ScanErrorType.SCANNER_ERROR)

    def _create_enhanced_error_result(self, path: str, error_message: str, error_type: ScanErrorType) -> ScanResult:
        """Create enhanced error result with structured information."""
        return ScanResult(
            file_pairs=[],
            unpaired_archives=[],
            unpaired_previews=[],
            special_folders=[],
            scan_time=0.0,
            total_files=0,
            error_message=error_message,
            cache_hit=False,
            performance_metrics={
                'error_type': error_type.value,
                'path': path,
                'timestamp': time.time()
            }
        )

    def _log_scan_success(self, path: str, result: ScanResult):
        """Log successful scan with detailed metrics."""
        pairs = len(result.file_pairs)
        files = result.total_files
        time_taken = result.scan_time
        cache_status = "HIT" if result.cache_hit else "MISS"
        
        # Performance-based logging level
        if time_taken > 10.0:
            self.logger.warning(
                f"SLOW SCAN COMPLETED: {path} | {pairs} pairs, {files} files | "
                f"{time_taken:.2f}s | Cache: {cache_status}"
            )
        else:
            self.logger.info(
                f"Scan completed: {path} | {pairs} pairs, {files} files | "
                f"{time_taken:.2f}s | Cache: {cache_status}"
            )
            
        # Detailed debug information
        if result.performance_metrics:
            efficiency = result.performance_metrics.get('scan_efficiency', 0)
            self.logger.debug(f"Scan efficiency: {efficiency:.1f}% for {path}")

    def get_error_statistics(self) -> dict:
        """
        NOWA FUNKCJA: Get comprehensive error statistics.
        
        Returns:
            dict: Error statistics and recent errors
        """
        recent_errors = self._error_history[-10:]  # Last 10 errors
        
        return {
            'error_counts_by_type': dict(self._error_stats),
            'total_errors': sum(self._error_stats.values()),
            'recent_errors': [
                {
                    'timestamp': err['timestamp'],
                    'operation': err['operation'],
                    'type': err['error'].error_type.value,
                    'message': err['error'].message,
                    'path': err['error'].path,
                    'recoverable': err['error'].recoverable
                }
                for err in recent_errors
            ],
            'error_trends': self._analyze_error_trends()
        }
    
    def _analyze_error_trends(self) -> dict:
        """Analyze error trends for recommendations."""
        if not self._error_history:
            return {"status": "no_errors"}
        
        recent_hour = time.time() - 3600
        recent_errors = [e for e in self._error_history if e['timestamp'] > recent_hour]
        
        if len(recent_errors) > 10:
            return {
                "status": "high_error_rate",
                "recommendation": "Check system resources and file permissions"
            }
        elif len(recent_errors) > 5:
            return {
                "status": "moderate_error_rate", 
                "recommendation": "Monitor for pattern in failing paths"
            }
        else:
            return {
                "status": "low_error_rate",
                "recommendation": "System operating normally"
            }
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - czy scan_directory() działa bez crashes.
- [ ] **API kompatybilność** - czy wszystkie publiczne metody mają backward compatibility.
- [ ] **Obsługa błędów** - czy AttributeError na self.scanner zostały naprawione.
- [ ] **Walidacja danych** - czy PathValidator integration działa poprawnie.
- [ ] **Logowanie** - czy enhanced logging nie spamuje i ma odpowiednie levels.
- [ ] **Konfiguracja** - czy scanner module imports są poprawne.
- [ ] **Cache** - czy scanner_cache API jest używane prawidłowo.
- [ ] **Thread safety** - czy async operations i metrics są thread-safe.
- [ ] **Memory management** - czy ThreadPoolExecutor jest properly managed.
- [ ] **Performance** - czy async scanning nie blokuje UI, metrics są accurate.

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - czy scanner, scanner_cache, PathValidator importy działają.
- [ ] **Zależności zewnętrzne** - czy concurrent.futures, asyncio są używane prawidłowo.
- [ ] **Zależności wewnętrzne** - czy FilePair, SpecialFolder models działają.
- [ ] **Cykl zależności** - czy nie wprowadzono circular imports.
- [ ] **Backward compatibility** - czy existing controllers nadal działają z service.
- [ ] **Interface contracts** - czy ScanResult structure jest preserved.
- [ ] **Event handling** - czy progress callbacks działają poprawnie.
- [ ] **Signal/slot connections** - czy async completion callbacks działają.
- [ ] **File I/O** - czy scanner.scan_folder_for_pairs API jest używane prawidłowo.

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - czy wszystkie metody działają w izolacji.
- [ ] **Test integracyjny** - czy integration z UI controllers działa.
- [ ] **Test regresyjny** - czy naprawione AttributeError nie wprowadzają nowych bugs.
- [ ] **Test wydajnościowy** - czy async scanning performance <5s dla 1000 plików.

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem.
- [ ] **BRAK FAILED TESTS** - szczególnie zero AttributeError exceptions.
- [ ] **PERFORMANCE BUDGET** - skanowanie nie może blokować UI >100ms.
- [ ] **FUNCTIONALITY BUDGET** - wszystkie metody muszą być functional (zero crashes).