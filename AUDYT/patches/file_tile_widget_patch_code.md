# PATCH-CODE DLA: FILE_TILE_WIDGET.PY

**Powiązany plik z analizą:** `../corrections/file_tile_widget_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: RESPONSIVE TILE SIZING Z VIEWPORT AWARENESS

**Problem:** Sztywne `setFixedSize()` uniemożliwia adaptację kafli do viewport galerii
**Rozwiązanie:** Implementacja elastic sizing z viewport awareness

```python
class ResponsiveTileSizing:
    """Responsive sizing manager dla kafli z viewport awareness."""
    
    def __init__(self, tile_widget):
        self.tile_widget = tile_widget
        self.viewport_size = (800, 600)  # Default viewport
        self.gallery_columns = 4  # Default columns
        self.min_tile_size = (80, 80)
        self.max_tile_size = (300, 300)
        self.aspect_ratio = 1.0  # Square tiles by default
        self._adaptive_sizing_enabled = True
        
    def set_viewport_info(self, viewport_size: Tuple[int, int], columns: int):
        """Update viewport information for adaptive sizing."""
        self.viewport_size = viewport_size
        self.gallery_columns = max(1, columns)
        if self._adaptive_sizing_enabled:
            self._recalculate_optimal_size()
            
    def _recalculate_optimal_size(self):
        """Calculate optimal tile size based on viewport and columns."""
        viewport_width, viewport_height = self.viewport_size
        
        # Calculate available width per tile
        available_width = (viewport_width - 40) // self.gallery_columns  # 40px margins
        available_width = max(available_width - 10, self.min_tile_size[0])  # 10px spacing
        
        # Respect min/max constraints
        optimal_width = max(self.min_tile_size[0], 
                           min(self.max_tile_size[0], available_width))
        optimal_height = int(optimal_width * self.aspect_ratio)
        
        # Update tile size if significantly different
        current_size = self.tile_widget.thumbnail_size
        new_size = (optimal_width, optimal_height)
        
        if abs(current_size[0] - new_size[0]) > 10:  # Threshold to avoid micro-adjustments
            self._apply_new_size(new_size)
            
    def _apply_new_size(self, new_size: Tuple[int, int]):
        """Apply new size with smooth transition."""
        old_size = self.tile_widget.thumbnail_size
        self.tile_widget.thumbnail_size = new_size
        
        # Use minimum size policy instead of fixed size
        self.tile_widget.setMinimumSize(new_size[0], new_size[1])
        self.tile_widget.setMaximumSize(new_size[0] + 20, new_size[1] + 20)  # Allow slight flexibility
        
        # Update internal components
        self._update_internal_layout(new_size)
        
        # Emit size change event
        if hasattr(self.tile_widget, '_event_bus'):
            self.tile_widget._event_bus.emit_event(
                TileEvent.SIZE_CHANGED, 
                {"old_size": old_size, "new_size": new_size, "viewport_size": self.viewport_size}
            )
            
    def _update_internal_layout(self, new_size: Tuple[int, int]):
        """Update internal component layouts for new size."""
        if hasattr(self.tile_widget, "thumbnail_label"):
            # Calculate thumbnail area (excluding filename and metadata areas)
            thumb_size = min(
                new_size[0] - 10,  # 10px padding
                new_size[1] - 60   # 60px for filename and metadata
            )
            thumb_size = max(thumb_size, 50)  # Minimum thumbnail size
            self.tile_widget.thumbnail_label.setFixedSize(thumb_size, thumb_size)
            
        # Update font sizes based on new tile size
        self.tile_widget._update_font_size()
        
    def enable_adaptive_sizing(self, enabled: bool = True):
        """Enable/disable adaptive sizing."""
        self._adaptive_sizing_enabled = enabled


# Modyfikacja klasy FileTileWidget
class FileTileWidget(QWidget):
    """Enhanced with responsive sizing capabilities."""
    
    def __init__(self, file_pair, default_thumbnail_size, parent=None, skip_resource_registration=False):
        # ... existing initialization ...
        
        # Initialize responsive sizing
        self._responsive_sizing = ResponsiveTileSizing(self)
        
        # ... rest of existing initialization ...
        
    def set_viewport_info(self, viewport_size: Tuple[int, int], columns: int):
        """Set viewport information for responsive sizing."""
        if hasattr(self, '_responsive_sizing'):
            self._responsive_sizing.set_viewport_info(viewport_size, columns)
            
    def set_thumbnail_size(self, new_size):
        """Enhanced thumbnail size setting with responsive support."""
        if self._is_destroyed:
            return
            
        if isinstance(new_size, int):
            size_tuple = (new_size, new_size)
        else:
            size_tuple = new_size

        if self.thumbnail_size != size_tuple:
            old_size = self.thumbnail_size
            self.thumbnail_size = size_tuple
            
            # Use responsive sizing instead of fixed size
            if hasattr(self, '_responsive_sizing'):
                self._responsive_sizing._apply_new_size(size_tuple)
            else:
                # Fallback to flexible sizing
                self.setMinimumSize(size_tuple[0], size_tuple[1])
                self.setMaximumSize(size_tuple[0] + 20, size_tuple[1] + 20)
                
            # Update configuration
            self._config.thumbnail_size = size_tuple
            
            # Update thumbnail component
            if self.file_pair and self.file_pair.preview_path:
                self._thumbnail_component.set_thumbnail_size(size_tuple, immediate=True)
                
            self._update_font_size()
```

---

### PATCH 2: SIMPLIFIED COMPONENT ARCHITECTURE

**Problem:** Over-engineered component pattern z 6+ komponentami na jeden kafel
**Rozwiązanie:** Consolidacja do 3 core components z simplified architecture

```python
class CoreTileManager:
    """Simplified core manager replacing multiple components."""
    
    def __init__(self, tile_widget):
        self.tile_widget = tile_widget
        self.thumbnail_handler = SimplifiedThumbnailHandler(tile_widget)
        self.interaction_handler = SimplifiedInteractionHandler(tile_widget)
        self.metadata_handler = SimplifiedMetadataHandler(tile_widget)
        
    def update_file_pair(self, file_pair):
        """Coordinated update across all handlers."""
        self.thumbnail_handler.set_file_pair(file_pair)
        self.metadata_handler.set_file_pair(file_pair)
        self.interaction_handler.set_file_pair(file_pair)
        
    def cleanup(self):
        """Coordinated cleanup across all handlers."""
        self.thumbnail_handler.cleanup()
        self.interaction_handler.cleanup() 
        self.metadata_handler.cleanup()


class SimplifiedThumbnailHandler:
    """Simplified thumbnail handling without over-engineering."""
    
    def __init__(self, tile_widget):
        self.tile_widget = tile_widget
        self.current_thumbnail_path = None
        self.is_loading = False
        self._cancel_token = None
        
    def set_file_pair(self, file_pair):
        """Set file pair and load thumbnail if needed."""
        if file_pair and file_pair.preview_path:
            self.load_thumbnail_async(file_pair.preview_path)
        else:
            self.clear_thumbnail()
            
    def load_thumbnail_async(self, path: str):
        """Async thumbnail loading with cancellation support."""
        if self.current_thumbnail_path == path and not self.is_loading:
            return  # Already loaded
            
        # Cancel previous loading
        if self._cancel_token:
            self._cancel_token.cancel()
            
        self.current_thumbnail_path = path
        self.is_loading = True
        
        # Use ThreadPoolExecutor for async loading
        from concurrent.futures import ThreadPoolExecutor
        import threading
        
        self._cancel_token = threading.Event()
        
        def load_worker():
            if self._cancel_token.is_set():
                return
                
            try:
                # Load and scale thumbnail
                pixmap = self._load_and_scale_pixmap(path)
                
                if not self._cancel_token.is_set() and pixmap:
                    # Update UI on main thread
                    from PyQt6.QtCore import QMetaObject, Qt
                    QMetaObject.invokeMethod(
                        self.tile_widget,
                        "_on_thumbnail_loaded_safe",
                        Qt.ConnectionType.QueuedConnection,
                        pixmap
                    )
            except Exception as e:
                if not self._cancel_token.is_set():
                    logger.warning(f"Thumbnail loading error: {e}")
            finally:
                self.is_loading = False
                
        # Submit to thread pool
        if hasattr(self.tile_widget, '_resource_manager'):
            executor = self.tile_widget._resource_manager.get_thread_pool()
            if executor:
                executor.submit(load_worker)
            else:
                load_worker()  # Fallback to sync
        else:
            load_worker()
            
    def _load_and_scale_pixmap(self, path: str) -> Optional[QPixmap]:
        """Load and scale pixmap efficiently."""
        try:
            pixmap = QPixmap(path)
            if pixmap.isNull():
                return None
                
            # Scale to tile size
            tile_size = self.tile_widget.thumbnail_size
            thumb_size = min(tile_size[0] - 10, tile_size[1] - 60)
            
            if pixmap.width() > thumb_size or pixmap.height() > thumb_size:
                pixmap = pixmap.scaled(
                    thumb_size, thumb_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
            return pixmap
        except Exception as e:
            logger.warning(f"Error loading pixmap {path}: {e}")
            return None
            
    def clear_thumbnail(self):
        """Clear current thumbnail."""
        if self._cancel_token:
            self._cancel_token.cancel()
        self.current_thumbnail_path = None
        if hasattr(self.tile_widget, 'thumbnail_label'):
            self.tile_widget.thumbnail_label.clear()
            
    def cleanup(self):
        """Cleanup thumbnail handler."""
        if self._cancel_token:
            self._cancel_token.cancel()


# Enhanced FileTileWidget with simplified architecture
class FileTileWidget(QWidget):
    """Simplified FileTileWidget with core components only."""
    
    def __init__(self, file_pair, default_thumbnail_size, parent=None, skip_resource_registration=False):
        super().__init__(parent)
        
        # Core properties
        self.file_pair = file_pair
        self.thumbnail_size = default_thumbnail_size
        self.is_selected = False
        self._is_destroyed = False
        
        # Simplified architecture - only core manager
        self._core_manager = CoreTileManager(self)
        self._responsive_sizing = ResponsiveTileSizing(self)
        
        # Basic UI setup
        self._setup_basic_ui()
        
        # Set initial data
        if file_pair:
            self._core_manager.update_file_pair(file_pair)
            
    def _setup_basic_ui(self):
        """Simplified UI setup."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Thumbnail label
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        layout.addWidget(self.thumbnail_label)
        
        # Filename label
        self.filename_label = QLabel("No file")
        self.filename_label.setWordWrap(True)
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.filename_label)
        
        # Set responsive sizing
        self._responsive_sizing._apply_new_size(self.thumbnail_size)
        
    def _on_thumbnail_loaded_safe(self, pixmap):
        """Thread-safe thumbnail loading callback."""
        if not self._is_destroyed and hasattr(self, 'thumbnail_label'):
            self.thumbnail_label.setPixmap(pixmap)
```

---

### PATCH 3: EFFICIENT BATCHED UI UPDATES

**Problem:** Redundant UI updates i brak throttling prowadzi do performance issues
**Rozwiązanie:** Batched updates z intelligent throttling

```python
class BatchedUIUpdater:
    """Efficient batched UI updates with throttling."""
    
    def __init__(self, tile_widget):
        self.tile_widget = tile_widget
        self.pending_updates = set()
        self.update_timer = None
        self.throttle_interval = 16  # ~60 FPS
        self._is_updating = False
        
    def schedule_update(self, update_type: str, immediate: bool = False):
        """Schedule UI update with batching."""
        if immediate:
            self._perform_update(update_type)
        else:
            self.pending_updates.add(update_type)
            self._start_timer()
            
    def _start_timer(self):
        """Start throttling timer."""
        if self.update_timer is None:
            from PyQt6.QtCore import QTimer
            self.update_timer = QTimer()
            self.update_timer.setSingleShot(True)
            self.update_timer.timeout.connect(self._process_pending_updates)
            
        if not self.update_timer.isActive():
            self.update_timer.start(self.throttle_interval)
            
    def _process_pending_updates(self):
        """Process all pending updates in batch."""
        if self._is_updating or self.tile_widget._is_destroyed:
            return
            
        self._is_updating = True
        updates = self.pending_updates.copy()
        self.pending_updates.clear()
        
        try:
            # Process updates in priority order
            update_priority = ['thumbnail', 'metadata', 'filename', 'size', 'style']
            for update_type in update_priority:
                if update_type in updates:
                    self._perform_update(update_type)
        finally:
            self._is_updating = False
            
    def _perform_update(self, update_type: str):
        """Perform specific UI update."""
        if self.tile_widget._is_destroyed:
            return
            
        try:
            if update_type == 'thumbnail':
                self._update_thumbnail()
            elif update_type == 'metadata':
                self._update_metadata()
            elif update_type == 'filename':
                self._update_filename()
            elif update_type == 'size':
                self._update_size()
            elif update_type == 'style':
                self._update_style()
        except Exception as e:
            logger.warning(f"UI update error for {update_type}: {e}")
            
    def _update_thumbnail(self):
        """Update thumbnail display."""
        if (hasattr(self.tile_widget, '_core_manager') and 
            hasattr(self.tile_widget._core_manager, 'thumbnail_handler')):
            handler = self.tile_widget._core_manager.thumbnail_handler
            if self.tile_widget.file_pair:
                handler.load_thumbnail_async(self.tile_widget.file_pair.preview_path)
                
    def _update_metadata(self):
        """Update metadata display.""" 
        if (hasattr(self.tile_widget, '_core_manager') and
            hasattr(self.tile_widget._core_manager, 'metadata_handler')):
            handler = self.tile_widget._core_manager.metadata_handler
            handler.update_display()
            
    def _update_filename(self):
        """Update filename display."""
        if hasattr(self.tile_widget, 'filename_label') and self.tile_widget.file_pair:
            filename = self.tile_widget.file_pair.base_name
            self.tile_widget.filename_label.setText(filename)
            
    def _update_size(self):
        """Update size-related UI elements."""
        self.tile_widget._update_font_size()
        
    def _update_style(self):
        """Update visual styles."""
        if self.tile_widget.file_pair:
            color_tag = self.tile_widget.file_pair.get_color_tag()
            if color_tag:
                self.tile_widget._update_thumbnail_border_color(color_tag)


# Enhanced FileTileWidget with batched updates
class FileTileWidget(QWidget):
    """Enhanced with efficient batched UI updates."""
    
    def __init__(self, file_pair, default_thumbnail_size, parent=None, skip_resource_registration=False):
        # ... existing initialization ...
        
        # Initialize batched updater
        self._ui_updater = BatchedUIUpdater(self)
        
        # ... rest of initialization ...
        
    def update_data(self, file_pair: Optional[FilePair]):
        """Enhanced update_data with batched updates."""
        if self._is_destroyed:
            return
            
        old_file_pair = self.file_pair
        self.file_pair = file_pair
        
        if file_pair:
            # Update core manager
            if hasattr(self, '_core_manager'):
                self._core_manager.update_file_pair(file_pair)
                
            # Schedule batched UI updates
            self._ui_updater.schedule_update('filename')
            self._ui_updater.schedule_update('thumbnail')
            self._ui_updater.schedule_update('metadata')
            self._ui_updater.schedule_update('style')
        else:
            self._reset_ui_state()
            
    def set_thumbnail_size(self, new_size):
        """Enhanced with batched size updates."""
        if self._is_destroyed:
            return
            
        if isinstance(new_size, int):
            size_tuple = (new_size, new_size)
        else:
            size_tuple = new_size
            
        if self.thumbnail_size != size_tuple:
            self.thumbnail_size = size_tuple
            
            # Use responsive sizing
            if hasattr(self, '_responsive_sizing'):
                self._responsive_sizing._apply_new_size(size_tuple)
                
            # Schedule batched updates
            self._ui_updater.schedule_update('size')
            self._ui_updater.schedule_update('thumbnail')
```

---

### PATCH 4: VIEWPORT-AWARE RENDERING

**Problem:** Kafle renderują się nawet gdy nie są widoczne w viewport
**Rozwiązanie:** Viewport-aware lazy loading/unloading

```python
class ViewportAwareRenderer:
    """Manages viewport-aware rendering for tiles."""
    
    def __init__(self, tile_widget):
        self.tile_widget = tile_widget
        self.is_visible_in_viewport = False
        self.visibility_threshold = 50  # pixels
        self._visibility_timer = None
        self._last_visibility_check = 0
        
    def update_viewport_visibility(self, viewport_rect, tile_rect):
        """Update visibility based on viewport and tile rectangles."""
        # Check if tile intersects with viewport (with threshold)
        expanded_viewport = viewport_rect.adjusted(
            -self.visibility_threshold, -self.visibility_threshold,
            self.visibility_threshold, self.visibility_threshold
        )
        
        is_visible = expanded_viewport.intersects(tile_rect)
        
        if is_visible != self.is_visible_in_viewport:
            self.is_visible_in_viewport = is_visible
            self._handle_visibility_change(is_visible)
            
    def _handle_visibility_change(self, is_visible: bool):
        """Handle visibility state change."""
        if is_visible:
            self._on_become_visible()
        else:
            self._on_become_hidden()
            
    def _on_become_visible(self):
        """Called when tile becomes visible in viewport."""
        # Ensure tile is fully loaded
        if (hasattr(self.tile_widget, '_core_manager') and
            self.tile_widget.file_pair):
            # Load thumbnail with high priority
            handler = self.tile_widget._core_manager.thumbnail_handler
            handler.load_thumbnail_async(self.tile_widget.file_pair.preview_path)
            
            # Update UI immediately
            if hasattr(self.tile_widget, '_ui_updater'):
                self.tile_widget._ui_updater.schedule_update('filename', immediate=True)
                self.tile_widget._ui_updater.schedule_update('metadata', immediate=True)
                
    def _on_become_hidden(self):
        """Called when tile becomes hidden from viewport."""
        # Optionally unload thumbnail to save memory
        if hasattr(self.tile_widget, '_core_manager'):
            handler = self.tile_widget._core_manager.thumbnail_handler
            # Cancel any pending loads
            if handler._cancel_token:
                handler._cancel_token.cancel()
                
    def should_render_thumbnail(self) -> bool:
        """Check if thumbnail should be rendered."""
        return self.is_visible_in_viewport
        
    def should_update_ui(self) -> bool:
        """Check if UI updates should be processed."""
        return self.is_visible_in_viewport


# Enhanced FileTileWidget with viewport awareness
class FileTileWidget(QWidget):
    """Enhanced with viewport-aware rendering."""
    
    def __init__(self, file_pair, default_thumbnail_size, parent=None, skip_resource_registration=False):
        # ... existing initialization ...
        
        # Initialize viewport renderer
        self._viewport_renderer = ViewportAwareRenderer(self)
        
        # ... rest of initialization ...
        
    def update_viewport_visibility(self, viewport_rect):
        """Update visibility status based on current viewport."""
        if hasattr(self, '_viewport_renderer'):
            tile_rect = self.geometry()
            self._viewport_renderer.update_viewport_visibility(viewport_rect, tile_rect)
            
    def is_visible_in_viewport(self) -> bool:
        """Check if tile is currently visible in viewport."""
        if hasattr(self, '_viewport_renderer'):
            return self._viewport_renderer.is_visible_in_viewport
        return True  # Default to visible
        
    def should_render(self) -> bool:
        """Check if tile should perform rendering operations."""
        return self.is_visible_in_viewport()
        
    # Override update methods to check visibility
    def _update_ui_from_file_pair(self):
        """Enhanced with viewport awareness."""
        if not self.should_render():
            return  # Skip UI updates for non-visible tiles
            
        # Original update logic
        super()._update_ui_from_file_pair()
```

---

### PATCH 5: MEMORY LEAK PREVENTION

**Problem:** Event filters i connections nie są properly cleaned, prowadząc do memory leaks
**Rozwiązanie:** Robust cleanup mechanism z lifecycle management

```python
class RobustCleanupManager:
    """Comprehensive cleanup management for tile widgets."""
    
    def __init__(self, tile_widget):
        self.tile_widget = tile_widget
        self.tracked_connections = []
        self.tracked_timers = []
        self.tracked_threads = []
        self.cleanup_callbacks = []
        self._cleanup_done = False
        
    def track_connection(self, signal, slot):
        """Track signal-slot connection for cleanup."""
        connection = signal.connect(slot)
        self.tracked_connections.append((signal, slot, connection))
        return connection
        
    def track_timer(self, timer):
        """Track QTimer for cleanup."""
        self.tracked_timers.append(timer)
        
    def track_thread(self, thread):
        """Track QThread for cleanup."""
        self.tracked_threads.append(thread)
        
    def add_cleanup_callback(self, callback):
        """Add cleanup callback."""
        self.cleanup_callbacks.append(callback)
        
    def cleanup_all(self):
        """Comprehensive cleanup of all tracked resources."""
        if self._cleanup_done:
            return
            
        self._cleanup_done = True
        
        try:
            # Cleanup callbacks
            for callback in self.cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.warning(f"Cleanup callback error: {e}")
                    
            # Disconnect signals
            for signal, slot, connection in self.tracked_connections:
                try:
                    signal.disconnect(slot)
                except Exception as e:
                    logger.warning(f"Signal disconnect error: {e}")
                    
            # Stop timers
            for timer in self.tracked_timers:
                try:
                    if timer.isActive():
                        timer.stop()
                except Exception as e:
                    logger.warning(f"Timer stop error: {e}")
                    
            # Wait for threads
            for thread in self.tracked_threads:
                try:
                    if thread.isRunning():
                        thread.quit()
                        thread.wait(1000)  # Wait up to 1 second
                except Exception as e:
                    logger.warning(f"Thread cleanup error: {e}")
                    
        except Exception as e:
            logger.error(f"Critical cleanup error: {e}")
            
        # Clear references
        self.tracked_connections.clear()
        self.tracked_timers.clear()
        self.tracked_threads.clear()
        self.cleanup_callbacks.clear()


# Enhanced FileTileWidget with robust cleanup
class FileTileWidget(QWidget):
    """Enhanced with robust cleanup management."""
    
    def __init__(self, file_pair, default_thumbnail_size, parent=None, skip_resource_registration=False):
        # ... existing initialization ...
        
        # Initialize cleanup manager
        self._cleanup_manager = RobustCleanupManager(self)
        
        # Track all resources during initialization
        self._setup_cleanup_tracking()
        
        # ... rest of initialization ...
        
    def _setup_cleanup_tracking(self):
        """Setup cleanup tracking for all resources."""
        
        # Track UI updater timer
        if hasattr(self, '_ui_updater') and hasattr(self._ui_updater, 'update_timer'):
            if self._ui_updater.update_timer:
                self._cleanup_manager.track_timer(self._ui_updater.update_timer)
                
        # Track thumbnail loading cancellation
        def cleanup_thumbnail():
            if hasattr(self, '_core_manager'):
                handler = self._core_manager.thumbnail_handler
                handler.cleanup()
                
        self._cleanup_manager.add_cleanup_callback(cleanup_thumbnail)
        
        # Track responsive sizing
        def cleanup_responsive():
            if hasattr(self, '_responsive_sizing'):
                self._responsive_sizing._adaptive_sizing_enabled = False
                
        self._cleanup_manager.add_cleanup_callback(cleanup_responsive)
        
    def cleanup(self):
        """Enhanced cleanup with comprehensive resource management."""
        self._is_destroyed = True
        
        # Use cleanup manager
        if hasattr(self, '_cleanup_manager'):
            self._cleanup_manager.cleanup_all()
            
        # Cleanup components
        if hasattr(self, '_core_manager'):
            self._core_manager.cleanup()
            
        # Remove from resource manager
        if hasattr(self, '_resource_manager') and self._is_registered:
            try:
                self._resource_manager.unregister_tile(self)
            except Exception as e:
                logger.warning(f"Resource manager cleanup error: {e}")
                
    def __del__(self):
        """Enhanced destructor."""
        try:
            if not self._cleanup_done:
                self.cleanup()
        except Exception:
            pass  # Ignore errors in destructor
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - tworzenie kafli z różnymi rozmiarami działa
- [ ] **API kompatybilność** - wszystkie publiczne metody zachowują kompatybilność
- [ ] **Responsive sizing** - kafle adaptują się do viewport galerii
- [ ] **Thumbnail loading** - async loading z cancellation support działa
- [ ] **Event handling** - click, context menu, drag events działają
- [ ] **Metadata updates** - gwiazdki i color tags aktualizują się
- [ ] **Viewport awareness** - kafle ładują się tylko gdy widoczne
- [ ] **Memory management** - brak memory leaks przy tworzeniu/usuwaniu kafli
- [ ] **Performance** - płynne renderowanie 1000+ kafli

#### **UI RESPONSYWNOŚĆ DO WERYFIKACJI:**

- [ ] **Elastic sizing** - kafle używają min/max size zamiast fixed size
- [ ] **Grid adaptation** - kafle dostosowują się do liczby kolumn galerii
- [ ] **Viewport visibility** - tylko widoczne kafle renderują content
- [ ] **Batched updates** - UI updates są throttled i batched
- [ ] **Smooth resizing** - galeria nie znika przy resize okna
- [ ] **Font scaling** - czcionki skalują się z rozmiarem kafli
- [ ] **Performance monitoring** - tracking UI responsiveness

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **gallery_tab.py** - integracja z viewport info działa
- [ ] **tile_manager.py** - resource management działa z uproszczoną architekturą  
- [ ] **tile_resource_manager.py** - registration/unregistration działa
- [ ] **tile_thumbnail_component.py** - backward compatibility zachowana
- [ ] **metadata_component.py** - simplified metadata handling działa
- [ ] **Main window** - signals i events nadal są emitowane
- [ ] **Event bus** - komunikacja między komponentami działa
- [ ] **File pair model** - wszystkie operacje na file_pair działają

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test responsive layout** - kafle adaptują się do różnych rozmiarów viewport
- [ ] **Test performance** - 1000+ kafli renderuje się <2 sekundy
- [ ] **Test memory usage** - memory usage <50MB dla 1000 kafli
- [ ] **Test viewport scrolling** - smooth scrolling przez dużą liczbę kafli
- [ ] **Test thumbnail loading** - async loading bez blocking UI
- [ ] **Test cleanup** - proper cleanup bez memory leaks

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - wszystkie testy automatyczne przechodzą
- [ ] **RESPONSIVE GALLERY** - galeria adaptuje się do resize bez znikania
- [ ] **PERFORMANCE BUDGET** - renderowanie nie wolniejsze niż 5%
- [ ] **MEMORY BUDGET** - zużycie pamięci nie wyższe o więcej niż 10%
- [ ] **BACKWARD COMPATIBILITY** - 100% kompatybilność z istniejącym API
- [ ] **UI SMOOTHNESS** - 60 FPS podczas scrollowania przez kafle