# PATCH-CODE DLA: Business Controllers (main_window_controller.py, gallery_controller.py)

**Powiązany plik z analizą:** `../corrections/business_controllers_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: SPLIT MAINWINDOWCONTROLLER - Separation of Concerns

**Problem:** God Object Anti-Pattern - zbyt wiele odpowiedzialności w jednej klasie
**Rozwiązanie:** Split na BusinessLogicController i UICoordinationController

```python
# NOWA klasa - BusinessLogicController:
class BusinessLogicController:
    """
    Pure business logic controller bez UI dependencies.
    Handles wszystkie business operations w clean way.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Services - only business dependencies
        self.file_service = FileOperationsService()
        self.scan_service = ScanningService()
        
        # Business managers
        self.special_folders_manager = SpecialFoldersManager()
        self.selection_manager = SelectionManager()
        self.scan_processor = ScanResultProcessor()
        
        # Business state only
        self.current_directory: Optional[str] = None
        self.current_file_pairs: List[FilePair] = []
        self.unpaired_archives: List[str] = []
        self.unpaired_previews: List[str] = []
        self.special_folders: List = []
        
        # Business event callbacks
        self._scan_completed_callbacks = []
        self._operation_progress_callbacks = []
        self._error_callbacks = []
    
    def register_scan_completed_callback(self, callback):
        """Register callback dla scan completion events."""
        self._scan_completed_callbacks.append(callback)
    
    def register_progress_callback(self, callback):
        """Register callback dla operation progress events."""
        self._operation_progress_callbacks.append(callback)
    
    def register_error_callback(self, callback):
        """Register callback dla error events."""
        self._error_callbacks.append(callback)
    
    async def execute_directory_scan(self, directory_path: str) -> ScanResult:
        """
        Execute directory scan as business operation.
        Returns ScanResult bez UI side effects.
        """
        try:
            self.logger.debug("Business: Starting directory scan: %s", directory_path)
            
            # Validate directory - pure business rule
            errors = self.scan_service.validate_directory_path(directory_path)
            if errors:
                error_msg = "Directory validation failed:\n" + "\n".join(errors)
                self.logger.warning("Business: %s", error_msg)
                
                # Notify error callbacks
                for callback in self._error_callbacks:
                    callback("Directory Error", error_msg)
                
                return ScanResult(error_message=error_msg)
            
            # Execute scan - business operation
            scan_result = await self.scan_service.scan_directory_async(directory_path)
            
            if scan_result.error_message:
                # Notify error callbacks
                for callback in self._error_callbacks:
                    callback("Scan Error", scan_result.error_message)
                return scan_result
            
            # Process results - pure business logic
            processed_data = self.scan_processor.process_scan_result(scan_result)
            
            # Update business state
            self._update_business_state(processed_data)
            
            # Notify completion callbacks
            for callback in self._scan_completed_callbacks:
                callback(scan_result, processed_data)
            
            self.logger.info(
                f"Business: Scan completed - {len(self.current_file_pairs)} pairs found"
            )
            
            return scan_result
            
        except Exception as e:
            error_msg = f"Unexpected scan error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            # Notify error callbacks
            for callback in self._error_callbacks:
                callback("Critical Error", error_msg)
            
            return ScanResult(error_message=error_msg)
    
    async def execute_bulk_delete(self, selected_pairs: List[FilePair]) -> dict:
        """
        Execute bulk delete as business operation.
        Returns operation result bez UI side effects.
        """
        if not selected_pairs:
            return {"success": False, "error": "No files selected for deletion"}
        
        try:
            # Notify progress start
            for callback in self._operation_progress_callbacks:
                callback(0, f"Deleting {len(selected_pairs)} file pairs...")
            
            # Execute business operation
            deleted_pairs, errors = await self.file_service.bulk_delete_async(selected_pairs)
            
            # Update business state
            self._remove_pairs_from_business_state(deleted_pairs)
            
            # Notify progress completion
            for callback in self._operation_progress_callbacks:
                callback(100, f"Deleted {len(deleted_pairs)} file pairs")
            
            result = {
                "success": True,
                "deleted_pairs": deleted_pairs,
                "errors": errors,
                "deleted_count": len(deleted_pairs)
            }
            
            self.logger.info(f"Business: Bulk delete completed - {len(deleted_pairs)} pairs deleted")
            return result
            
        except Exception as e:
            error_msg = f"Bulk delete error: {str(e)}"
            self.logger.error(error_msg)
            
            # Notify error callbacks
            for callback in self._error_callbacks:
                callback("Delete Error", error_msg)
            
            return {"success": False, "error": error_msg}
    
    def _update_business_state(self, processed_data: dict):
        """Update business state z processed scan data."""
        self.current_directory = processed_data["directory_path"]
        self.current_file_pairs = processed_data["file_pairs"]
        self.unpaired_archives = processed_data["unpaired_archives"]
        self.unpaired_previews = processed_data["unpaired_previews"]
        self.special_folders = processed_data["special_folders"]
        
        # Add metadata special folders
        if self.current_directory:
            metadata_folders = (
                self.special_folders_manager.get_special_folders_from_metadata(
                    self.current_directory
                )
            )
            if metadata_folders:
                self.special_folders.extend(metadata_folders)
    
    def _remove_pairs_from_business_state(self, pairs_to_remove: List[FilePair]):
        """Remove pairs z business state."""
        for pair in pairs_to_remove:
            if pair in self.current_file_pairs:
                self.current_file_pairs.remove(pair)
        
        # Update selection manager
        self.selection_manager.remove_pairs_from_selection(pairs_to_remove)

# MODIFY MainWindowController - keep only UI coordination:
class MainWindowController:
    """
    UI Coordination Controller - handles UI updates i coordination.
    Delegates business logic do BusinessLogicController.
    """
    
    def __init__(self, view):
        self.view = view
        self.logger = logging.getLogger(__name__)
        
        # Business logic controller - separation of concerns
        self.business_controller = BusinessLogicController()
        
        # Register dla business events
        self.business_controller.register_scan_completed_callback(self._on_scan_completed)
        self.business_controller.register_progress_callback(self._on_operation_progress)
        self.business_controller.register_error_callback(self._on_business_error)
    
    async def handle_folder_selection(self, directory_path: str) -> None:
        """Handle folder selection - coordinate UI i business logic."""
        try:
            # Delegate business logic
            await self.business_controller.execute_directory_scan(directory_path)
            
        except Exception as e:
            self.logger.error(f"UI coordination error: {str(e)}")
            self.view.show_error_message("Coordination Error", str(e))
    
    async def handle_bulk_delete(self, selected_pairs: List[FilePair]) -> bool:
        """Handle bulk delete - coordinate UI i business logic."""
        if not selected_pairs:
            self.view.show_info_message("Info", "No files selected for deletion")
            return False
        
        # UI confirmation
        if not self.view.confirm_bulk_delete(len(selected_pairs)):
            return False
        
        try:
            # Delegate to business logic
            result = await self.business_controller.execute_bulk_delete(selected_pairs)
            
            if result["success"]:
                # Update UI
                self.view.update_after_bulk_operation(result["deleted_pairs"], "deleted")
                
                # Show errors if any
                if result.get("errors"):
                    self._show_operation_errors("deletion", result["errors"])
                
                return True
            else:
                self.view.show_error_message("Delete Error", result["error"])
                return False
                
        except Exception as e:
            self.logger.error(f"UI coordination error during delete: {str(e)}")
            self.view.show_error_message("Coordination Error", str(e))
            return False
    
    def _on_scan_completed(self, scan_result: ScanResult, processed_data: dict):
        """Handle scan completion - update UI only."""
        self.view.update_scan_results(scan_result)
        stats = processed_data["statistics"]
        self.view._show_progress(100, f"Found {stats['total_pairs']} pairs")
    
    def _on_operation_progress(self, percent: int, message: str):
        """Handle operation progress - update UI only."""
        self.view._show_progress(percent, message)
    
    def _on_business_error(self, title: str, message: str):
        """Handle business errors - update UI only."""
        self.view.show_error_message(title, message)
        self.view._hide_progress()
    
    # Delegate properties to business controller
    @property
    def current_directory(self) -> Optional[str]:
        return self.business_controller.current_directory
    
    @property
    def current_file_pairs(self) -> List[FilePair]:
        return self.business_controller.current_file_pairs
    
    @property
    def unpaired_archives(self) -> List[str]:
        return self.business_controller.unpaired_archives
    
    @property
    def unpaired_previews(self) -> List[str]:
        return self.business_controller.unpaired_previews
```

---

### PATCH 2: ENHANCED GALLERYCONTROLLER - Complete Business Logic

**Problem:** Underutilized controller - brak kluczowej gallery business logic
**Rozwiązanie:** Implement complete gallery business logic dla performance

```python
# ENHANCED GalleryController:
class GalleryController:
    """
    Enhanced Gallery Controller z complete business logic.
    Handles all gallery-specific business requirements.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scanning_service = ScanningService()
        
        # Gallery business state
        self._all_file_pairs: List[FilePair] = []
        self._filtered_file_pairs: List[FilePair] = []
        self._active_filters: Dict[str, Any] = {}
        self._gallery_metadata: Dict[str, Any] = {}
        
        # Performance management
        self._memory_usage_mb = 0
        self._max_memory_mb = 1000  # 1GB limit dla gallery
        self._performance_metrics = {}
        
        # Virtual scrolling business state
        self._virtual_viewport_range = (0, 50)  # Start z 50 items
        self._items_per_batch = 20
        self._total_items_count = 0
        
        # Thumbnail coordination state
        self._thumbnail_load_queue = []
        self._thumbnail_cache_size_mb = 0
        self._max_thumbnail_cache_mb = 200  # 200MB dla thumbnails
        
        # Business event callbacks
        self._gallery_loaded_callbacks = []
        self._filter_applied_callbacks = []
        self._memory_warning_callbacks = []
        self._performance_callbacks = []
    
    def register_gallery_loaded_callback(self, callback):
        """Register callback dla gallery load events."""
        self._gallery_loaded_callbacks.append(callback)
    
    def register_filter_applied_callback(self, callback):
        """Register callback dla filter application events."""
        self._filter_applied_callbacks.append(callback)
    
    def register_memory_warning_callback(self, callback):
        """Register callback dla memory warning events."""
        self._memory_warning_callbacks.append(callback)
    
    async def load_gallery_data(self, file_pairs: List[FilePair]) -> dict:
        """
        Load gallery data z business logic dla performance.
        Returns gallery load result z performance metrics.
        """
        import time
        start_time = time.time()
        
        try:
            self.logger.info(f"Gallery: Loading {len(file_pairs)} file pairs")
            
            # Business rule: Check memory limits
            estimated_memory = self._estimate_memory_usage(file_pairs)
            if estimated_memory > self._max_memory_mb:
                # Business rule: Use progressive loading dla large datasets
                self._all_file_pairs = file_pairs
                self._filtered_file_pairs = file_pairs[:self._items_per_batch]
                
                for callback in self._memory_warning_callbacks:
                    callback(f"Large dataset detected ({len(file_pairs)} items). Using progressive loading.")
            else:
                # Normal loading dla smaller datasets
                self._all_file_pairs = file_pairs
                self._filtered_file_pairs = file_pairs.copy()
            
            # Update business state
            self._total_items_count = len(file_pairs)
            self._memory_usage_mb = estimated_memory
            
            # Calculate performance metrics
            load_time = time.time() - start_time
            self._performance_metrics.update({
                "load_time_seconds": load_time,
                "items_loaded": len(self._filtered_file_pairs),
                "total_items": len(file_pairs),
                "memory_usage_mb": self._memory_usage_mb,
                "using_progressive_loading": estimated_memory > self._max_memory_mb
            })
            
            # Prepare thumbnail loading queue
            self._prepare_thumbnail_queue()
            
            # Notify callbacks
            for callback in self._gallery_loaded_callbacks:
                callback(self._filtered_file_pairs, self._performance_metrics)
            
            self.logger.info(f"Gallery: Loaded in {load_time:.3f}s, {len(self._filtered_file_pairs)} items visible")
            
            return {
                "success": True,
                "visible_items": self._filtered_file_pairs,
                "total_items": len(file_pairs),
                "performance_metrics": self._performance_metrics,
                "using_progressive_loading": estimated_memory > self._max_memory_mb
            }
            
        except Exception as e:
            self.logger.error(f"Gallery load error: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def apply_intelligent_filters(self, filter_criteria: Dict[str, Any]) -> List[FilePair]:
        """
        Apply filters z intelligent optimization dla performance.
        """
        import time
        start_time = time.time()
        
        try:
            self.logger.debug(f"Gallery: Applying filters to {len(self._all_file_pairs)} items")
            
            # Business logic: Use cached results jeśli filters nie changed
            if self._filters_unchanged(filter_criteria):
                self.logger.debug("Gallery: Using cached filter results")
                return self._filtered_file_pairs
            
            # Apply filters z optimization
            filtered_pairs = self._apply_optimized_filters(filter_criteria)
            
            # Update business state
            self._active_filters = filter_criteria.copy()
            self._filtered_file_pairs = filtered_pairs
            
            # Calculate performance metrics
            filter_time = time.time() - start_time
            self._performance_metrics.update({
                "last_filter_time_seconds": filter_time,
                "filtered_items_count": len(filtered_pairs),
                "filter_efficiency": len(filtered_pairs) / len(self._all_file_pairs) if self._all_file_pairs else 0
            })
            
            # Prepare new thumbnail queue dla filtered results
            self._prepare_thumbnail_queue()
            
            # Notify callbacks
            for callback in self._filter_applied_callbacks:
                callback(filtered_pairs, filter_criteria, self._performance_metrics)
            
            self.logger.debug(f"Gallery: Filtered to {len(filtered_pairs)} items in {filter_time:.3f}s")
            return filtered_pairs
            
        except Exception as e:
            self.logger.error(f"Gallery filter error: {str(e)}")
            return self._all_file_pairs  # Fallback to all items
    
    def get_virtual_viewport_data(self, start_index: int, end_index: int) -> List[FilePair]:
        """
        Get data dla virtual viewport - business logic dla virtual scrolling.
        """
        try:
            # Business rule: Ensure indices są within bounds
            start_index = max(0, start_index)
            end_index = min(len(self._filtered_file_pairs), end_index)
            
            # Update viewport range dla future optimizations
            self._virtual_viewport_range = (start_index, end_index)
            
            # Return slice dla virtual rendering
            viewport_data = self._filtered_file_pairs[start_index:end_index]
            
            self.logger.debug(f"Gallery: Virtual viewport [{start_index}:{end_index}] = {len(viewport_data)} items")
            return viewport_data
            
        except Exception as e:
            self.logger.error(f"Virtual viewport error: {str(e)}")
            return []
    
    def manage_thumbnail_priority(self, visible_indices: List[int]):
        """
        Manage thumbnail loading priority based na visible items.
        Business logic dla intelligent thumbnail loading.
        """
        try:
            # Business rule: Prioritize visible thumbnails
            high_priority_pairs = []
            normal_priority_pairs = []
            
            for index in visible_indices:
                if 0 <= index < len(self._filtered_file_pairs):
                    high_priority_pairs.append(self._filtered_file_pairs[index])
            
            # Add nearby items dla pre-loading (business rule: smooth scrolling)
            buffer_size = 10
            for i in range(max(0, min(visible_indices) - buffer_size),
                          min(len(self._filtered_file_pairs), max(visible_indices) + buffer_size)):
                if i not in visible_indices and 0 <= i < len(self._filtered_file_pairs):
                    normal_priority_pairs.append(self._filtered_file_pairs[i])
            
            # Update thumbnail queue z priorities
            self._thumbnail_load_queue = high_priority_pairs + normal_priority_pairs
            
            self.logger.debug(f"Gallery: Updated thumbnail priority - {len(high_priority_pairs)} high, {len(normal_priority_pairs)} normal")
            
            return {
                "high_priority": high_priority_pairs,
                "normal_priority": normal_priority_pairs
            }
            
        except Exception as e:
            self.logger.error(f"Thumbnail priority error: {str(e)}")
            return {"high_priority": [], "normal_priority": []}
    
    def check_memory_pressure(self) -> dict:
        """
        Check memory pressure i apply business rules dla memory management.
        """
        try:
            current_memory = self._memory_usage_mb + self._thumbnail_cache_size_mb
            memory_pressure_ratio = current_memory / self._max_memory_mb
            
            result = {
                "current_memory_mb": current_memory,
                "max_memory_mb": self._max_memory_mb,
                "pressure_ratio": memory_pressure_ratio,
                "action_needed": False,
                "recommended_action": None
            }
            
            # Business rules dla memory management
            if memory_pressure_ratio > 0.9:
                # Critical memory pressure
                result.update({
                    "action_needed": True,
                    "recommended_action": "reduce_visible_items",
                    "severity": "critical"
                })
                
                # Automatically reduce visible items
                self._filtered_file_pairs = self._filtered_file_pairs[:self._items_per_batch // 2]
                
                for callback in self._memory_warning_callbacks:
                    callback("Critical memory pressure. Reduced visible items.")
                    
            elif memory_pressure_ratio > 0.7:
                # High memory pressure
                result.update({
                    "action_needed": True,
                    "recommended_action": "clear_thumbnail_cache",
                    "severity": "high"
                })
                
                for callback in self._memory_warning_callbacks:
                    callback("High memory pressure. Consider clearing thumbnail cache.")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Memory pressure check error: {str(e)}")
            return {"error": str(e)}
    
    def _estimate_memory_usage(self, file_pairs: List[FilePair]) -> float:
        """Estimate memory usage dla file pairs (business logic)."""
        # Business rule: Estimate based na item count i average thumbnail size
        base_memory_per_item = 0.1  # MB per item (rough estimate)
        thumbnail_memory_per_item = 0.05  # MB per thumbnail
        
        return len(file_pairs) * (base_memory_per_item + thumbnail_memory_per_item)
    
    def _filters_unchanged(self, new_criteria: Dict[str, Any]) -> bool:
        """Check if filters changed (optimization business logic)."""
        return self._active_filters == new_criteria
    
    def _apply_optimized_filters(self, filter_criteria: Dict[str, Any]) -> List[FilePair]:
        """Apply filters z optimization logic."""
        # Use existing filter_logic z optimization
        from src.logic.filter_logic import filter_file_pairs
        return filter_file_pairs(self._all_file_pairs, filter_criteria)
    
    def _prepare_thumbnail_queue(self):
        """Prepare thumbnail loading queue (business logic)."""
        # Business rule: Queue visible items first
        visible_start, visible_end = self._virtual_viewport_range
        self._thumbnail_load_queue = self._filtered_file_pairs[visible_start:visible_end].copy()
    
    def get_performance_metrics(self) -> dict:
        """Get current performance metrics dla monitoring."""
        return self._performance_metrics.copy()
    
    def get_gallery_state(self) -> dict:
        """Get current gallery business state."""
        return {
            "total_items": len(self._all_file_pairs),
            "visible_items": len(self._filtered_file_pairs),
            "active_filters": self._active_filters.copy(),
            "memory_usage_mb": self._memory_usage_mb,
            "thumbnail_cache_mb": self._thumbnail_cache_size_mb,
            "virtual_viewport": self._virtual_viewport_range,
            "performance_metrics": self._performance_metrics.copy()
        }
```

---

### PATCH 3: ASYNC OPERATIONS SUPPORT

**Problem:** Wszystkie operations są synchronous - może blokować UI
**Rozwiązanie:** Add proper async support z cancellation

```python
# DODAĆ w services/scanning_service.py:
import asyncio
from typing import Optional

class ScanningService:
    def __init__(self):
        self._current_scan_task: Optional[asyncio.Task] = None
        self._cancellation_event = asyncio.Event()
    
    async def scan_directory_async(self, directory_path: str) -> ScanResult:
        """
        Async directory scanning z cancellation support.
        """
        try:
            # Reset cancellation event
            self._cancellation_event.clear()
            
            # Create cancellable task
            self._current_scan_task = asyncio.create_task(
                self._perform_scan_with_cancellation(directory_path)
            )
            
            result = await self._current_scan_task
            return result
            
        except asyncio.CancelledError:
            logger.info("Scan cancelled by user")
            return ScanResult(error_message="Scan cancelled by user")
        finally:
            self._current_scan_task = None
    
    async def _perform_scan_with_cancellation(self, directory_path: str) -> ScanResult:
        """Perform scan z periodic cancellation checks."""
        # Use existing scan_folder_for_pairs z cancellation support
        def cancellation_check():
            return self._cancellation_event.is_set()
        
        # Run scan w thread pool dla non-blocking execution
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: scan_folder_for_pairs(
                directory_path,
                interrupt_check=cancellation_check
            )
        )
        
        return ScanResult(
            file_pairs=result[0],
            unpaired_archives=result[1],
            unpaired_previews=result[2],
            special_folders=result[3]
        )
    
    def cancel_current_scan(self):
        """Cancel currently running scan."""
        if self._current_scan_task and not self._current_scan_task.done():
            self._cancellation_event.set()
            self._current_scan_task.cancel()
            logger.info("Scan cancellation requested")

# DODAĆ w services/file_operations_service.py:
class FileOperationsService:
    async def bulk_delete_async(self, file_pairs: List[FilePair]) -> Tuple[List[FilePair], List[str]]:
        """
        Async bulk delete z progress reporting.
        """
        deleted_pairs = []
        errors = []
        
        total_items = len(file_pairs)
        
        for i, file_pair in enumerate(file_pairs):
            try:
                # Perform delete in thread pool
                loop = asyncio.get_event_loop()
                success = await loop.run_in_executor(
                    None,
                    self._delete_single_pair,
                    file_pair
                )
                
                if success:
                    deleted_pairs.append(file_pair)
                else:
                    errors.append(f"Failed to delete {file_pair.get_archive_path()}")
                
                # Small delay dla UI responsiveness
                if i % 10 == 0:  # Every 10th item
                    await asyncio.sleep(0.01)  # 10ms delay
                    
            except Exception as e:
                errors.append(f"Error deleting {file_pair.get_archive_path()}: {str(e)}")
        
        return deleted_pairs, errors
    
    def _delete_single_pair(self, file_pair: FilePair) -> bool:
        """Delete single file pair (runs w thread pool)."""
        try:
            # Implement actual file deletion logic
            archive_path = file_pair.get_archive_path()
            preview_path = file_pair.get_preview_path()
            
            # Delete files
            if os.path.exists(archive_path):
                os.remove(archive_path)
            
            if preview_path and os.path.exists(preview_path):
                os.remove(preview_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting pair: {e}")
            return False
```

---

### PATCH 4: PERFORMANCE MONITORING BUSINESS LOGIC

**Problem:** Brak performance monitoring w business logic
**Rozwiązanie:** Add comprehensive performance monitoring

```python
# DODAĆ performance monitoring class:
class PerformanceMonitor:
    """
    Business logic dla performance monitoring.
    Tracks key performance metrics dla business operations.
    """
    
    def __init__(self):
        self.metrics = {}
        self.thresholds = {
            "scan_time_seconds": 5.0,      # Max 5s dla scan
            "gallery_load_seconds": 2.0,   # Max 2s dla gallery load
            "filter_time_seconds": 0.5,    # Max 500ms dla filtering
            "memory_usage_mb": 1000,       # Max 1GB memory
            "ui_response_ms": 16            # Max 16ms dla 60 FPS
        }
        self._performance_callbacks = []
    
    def register_performance_callback(self, callback):
        """Register callback dla performance events."""
        self._performance_callbacks.append(callback)
    
    def track_operation(self, operation_name: str, duration_seconds: float, metadata: dict = None):
        """Track operation performance."""
        if operation_name not in self.metrics:
            self.metrics[operation_name] = []
        
        metric_data = {
            "duration_seconds": duration_seconds,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        self.metrics[operation_name].append(metric_data)
        
        # Check thresholds
        threshold_key = f"{operation_name}_seconds"
        if threshold_key in self.thresholds:
            if duration_seconds > self.thresholds[threshold_key]:
                self._notify_performance_issue(operation_name, duration_seconds, self.thresholds[threshold_key])
    
    def _notify_performance_issue(self, operation: str, actual: float, threshold: float):
        """Notify about performance issues."""
        issue_data = {
            "operation": operation,
            "actual_time": actual,
            "threshold_time": threshold,
            "severity": "high" if actual > threshold * 2 else "medium"
        }
        
        for callback in self._performance_callbacks:
            callback(issue_data)
    
    def get_performance_summary(self) -> dict:
        """Get performance summary dla business analysis."""
        summary = {}
        
        for operation, metrics_list in self.metrics.items():
            if metrics_list:
                durations = [m["duration_seconds"] for m in metrics_list]
                summary[operation] = {
                    "count": len(durations),
                    "avg_seconds": sum(durations) / len(durations),
                    "max_seconds": max(durations),
                    "min_seconds": min(durations),
                    "last_24h": [m for m in metrics_list if time.time() - m["timestamp"] < 86400]
                }
        
        return summary

# INTEGRATE w controllers:
class EnhancedGalleryController(GalleryController):
    """Gallery controller z performance monitoring."""
    
    def __init__(self):
        super().__init__()
        self.performance_monitor = PerformanceMonitor()
        self.performance_monitor.register_performance_callback(self._on_performance_issue)
    
    async def load_gallery_data(self, file_pairs: List[FilePair]) -> dict:
        """Load gallery z performance tracking."""
        start_time = time.time()
        
        result = await super().load_gallery_data(file_pairs)
        
        # Track performance
        duration = time.time() - start_time
        self.performance_monitor.track_operation("gallery_load", duration, {
            "items_count": len(file_pairs),
            "memory_usage_mb": self._memory_usage_mb
        })
        
        return result
    
    def _on_performance_issue(self, issue_data: dict):
        """Handle performance issues."""
        logger.warning(f"Performance issue detected: {issue_data}")
        
        # Business rules dla performance issues
        if issue_data["operation"] == "gallery_load" and issue_data["severity"] == "high":
            # Automatically enable progressive loading
            self._items_per_batch = min(self._items_per_batch, 10)
            
        elif issue_data["operation"] == "filter" and issue_data["severity"] == "high":
            # Enable filter result caching
            self._enable_aggressive_filter_caching()
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **ARCHITECTURE IMPROVEMENTS:**

- [ ] **Separation of concerns** - business logic separated od UI coordination
- [ ] **BusinessLogicController** - handles pure business operations
- [ ] **Enhanced GalleryController** - complete gallery business logic implemented
- [ ] **Async operations** - all heavy operations są async z cancellation
- [ ] **Event-driven architecture** - proper callbacks dla business events
- [ ] **Clear interfaces** - well-defined interfaces między controllers i services
- [ ] **State management** - proper business state management
- [ ] **Error handling** - comprehensive error handling z recovery options

#### **BUSINESS LOGIC REQUIREMENTS:**

- [ ] **Gallery performance** - supports 3000+ files z <2s loading
- [ ] **Memory management** - business rules dla <1GB memory usage
- [ ] **Virtual data management** - proper virtual scrolling business logic
- [ ] **Progressive loading** - business logic dla large datasets
- [ ] **Filter optimization** - intelligent filter caching i optimization
- [ ] **Thumbnail coordination** - proper thumbnail loading coordination
- [ ] **Performance monitoring** - comprehensive performance tracking
- [ ] **Cancellation support** - all operations can be cancelled properly

#### **PERFORMANCE TARGETS:**

- [ ] **Async operations** - all file operations async z proper cancellation
- [ ] **Gallery loading** - 3000+ files load w <2 seconds
- [ ] **Memory efficiency** - <1GB usage dla 3000+ files
- [ ] **UI responsiveness** - no blocking operations w UI thread
- [ ] **Progress tracking** - proper progress dla operations >500ms
- [ ] **Error recovery** - graceful handling błędów z recovery options
- [ ] **Performance metrics** - comprehensive performance monitoring
- [ ] **Business rules** - all business rules properly implemented

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **ARCHITECTURE CLEAN** - clear separation of concerns achieved
- [ ] **BUSINESS REQUIREMENTS MET** - all gallery performance requirements achieved
- [ ] **NO REGRESSIONS** - wszystkie existing functionality preserved
- [ ] **PERFORMANCE IMPROVED** - demonstrable performance improvements

---