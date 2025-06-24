# PATCH-CODE DLA: FILE_TILE_WIDGET.PY

**Powiązany plik z analizą:** `../corrections/file_tile_widget_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: THREAD-SAFE RESOURCE MANAGEMENT Z ATOMIC OPERATIONS

**Problem:** Race conditions w _is_destroyed, resource registration nie jest thread-safe
**Rozwiązanie:** Atomic flags i thread-safe resource management

```python
# W __init__ około linii 84-87
# Kod do zmiany:
# self._is_destroyed = False
# self._destroy_lock = threading.RLock()

# Zmienić na:
import threading
import weakref
from threading import Event, RLock
from typing import Optional, Set, Dict, Any
import time

# Thread-safe state management
self._destruction_event = threading.Event()
self._resource_lock = threading.RLock()
self._state_lock = threading.RLock()

# Atomic resource tracking
self._resource_registration_status = threading.Event()
self._component_disposal_status = threading.Event()
self._cleanup_completion_status = threading.Event()

# Thread-safe collections
self._active_operations: Set[str] = set()
self._operation_lock = threading.RLock()

def is_widget_destroyed(self) -> bool:
    """Thread-safe check for destruction status."""
    return self._destruction_event.is_set()

def mark_destroyed(self):
    """Thread-safe marking as destroyed."""
    with self._state_lock:
        if not self._destruction_event.is_set():
            self._destruction_event.set()
            self._notify_destruction()

def _notify_destruction(self):
    """Notify all components about widget destruction."""
    try:
        # Notify components
        if hasattr(self, '_event_bus') and self._event_bus:
            self._event_bus.emit_event(TileEvent.WIDGET_DESTROYING, self)
            
        # Clear active operations
        with self._operation_lock:
            self._active_operations.clear()
            
    except Exception as e:
        logger.warning(f"Error notifying destruction: {e}")

def register_operation(self, operation_name: str) -> bool:
    """Thread-safe registration of ongoing operations."""
    if self.is_widget_destroyed():
        return False
        
    with self._operation_lock:
        if self.is_widget_destroyed():  # Double-check
            return False
        self._active_operations.add(operation_name)
        return True

def unregister_operation(self, operation_name: str):
    """Thread-safe unregistration of operations."""
    with self._operation_lock:
        self._active_operations.discard(operation_name)

def wait_for_operations_completion(self, timeout: float = 5.0) -> bool:
    """Wait for all operations to complete."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        with self._operation_lock:
            if not self._active_operations:
                return True
        time.sleep(0.01)
    return False
```

---

### PATCH 2: ASYNCHRONOUS THUMBNAIL LOADING Z PROGRESS CALLBACKS

**Problem:** Synchronous thumbnail loading blokuje UI przy dużych obrazach
**Rozwiązanie:** Asynchroniczne loading z thread pooling

```python
# Dodać po _initialize_components około linii 152
import concurrent.futures
from PyQt6.QtCore import QTimer, QThread, pyqtSignal

class AsyncThumbnailLoader(QThread):
    """Asynchroniczny loader thumbnail z proper error handling."""
    
    thumbnail_loaded = pyqtSignal(str, object)  # path, pixmap
    thumbnail_error = pyqtSignal(str, str)      # path, error_msg
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks_queue = queue.Queue()
        self._is_running = True
        
    def load_thumbnail_async(self, path: str, size: tuple):
        """Add thumbnail loading task to queue."""
        if not self._is_running:
            return
        self._tasks_queue.put((path, size))
        
    def run(self):
        """Main thread loop for processing thumbnail requests."""
        while self._is_running:
            try:
                path, size = self._tasks_queue.get(timeout=0.1)
                self._process_thumbnail_request(path, size)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in thumbnail loader thread: {e}")
                
    def _process_thumbnail_request(self, path: str, size: tuple):
        """Process single thumbnail request."""
        try:
            if not os.path.exists(path):
                self.thumbnail_error.emit(path, "File not found")
                return
                
            # Load and scale thumbnail
            pixmap = QPixmap(path)
            if pixmap.isNull():
                self.thumbnail_error.emit(path, "Invalid image format")
                return
                
            # Scale to requested size
            scaled_pixmap = pixmap.scaled(
                size[0], size[1],
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.thumbnail_loaded.emit(path, scaled_pixmap)
            
        except Exception as e:
            self.thumbnail_error.emit(path, str(e))
            
    def stop(self):
        """Stop the loader thread."""
        self._is_running = False
        self.wait(1000)  # Wait max 1 second

# W __init__ dodać:
# Async thumbnail loading
self._async_thumbnail_loader = None
self._pending_thumbnail_requests: Dict[str, tuple] = {}
self._thumbnail_request_lock = threading.RLock()

def _setup_async_thumbnail_loading(self):
    """Setup asynchronous thumbnail loading."""
    try:
        self._async_thumbnail_loader = AsyncThumbnailLoader(self)
        self._async_thumbnail_loader.thumbnail_loaded.connect(
            self._on_async_thumbnail_loaded
        )
        self._async_thumbnail_loader.thumbnail_error.connect(
            self._on_async_thumbnail_error
        )
        self._async_thumbnail_loader.start()
    except Exception as e:
        logger.warning(f"Failed to setup async thumbnail loading: {e}")
        self._async_thumbnail_loader = None

def _on_async_thumbnail_loaded(self, path: str, pixmap):
    """Handle asynchronously loaded thumbnail."""
    if self.is_widget_destroyed():
        return
        
    try:
        # Remove from pending requests
        with self._thumbnail_request_lock:
            self._pending_thumbnail_requests.pop(path, None)
            
        # Update UI on main thread
        if hasattr(self, 'thumbnail_label') and self.thumbnail_label:
            self.thumbnail_label.setPixmap(pixmap)
            
        # Update border color if needed
        if self.file_pair:
            color_tag = self.file_pair.get_color_tag()
            if color_tag and color_tag.strip():
                self._update_thumbnail_border_color(color_tag)
                
    except Exception as e:
        logger.warning(f"Error handling async thumbnail: {e}")

def _on_async_thumbnail_error(self, path: str, error_msg: str):
    """Handle thumbnail loading error."""
    if self.is_widget_destroyed():
        return
        
    with self._thumbnail_request_lock:
        self._pending_thumbnail_requests.pop(path, None)
        
    if hasattr(self, 'thumbnail_label') and self.thumbnail_label:
        self.thumbnail_label.setText("Błąd")
        
    if not ("does not exist" in error_msg or "File not found" in error_msg):
        logger.warning(f"Async thumbnail error for {path}: {error_msg}")
```

---

### PATCH 3: OPTIMIZED EVENT HANDLING Z REDUCED OVERHEAD

**Problem:** Event filter overhead, każde mouse event przechodzi przez filtry
**Rozwiązanie:** Lightweight event filtering z early returns

```python
# W eventFilter około linii 612
# Kod do zmiany całej metody:
def eventFilter(self, obj, event):
    """Optimized event filter with early returns."""
    from PyQt6.QtCore import QEvent, Qt
    
    # Early return if widget is destroyed
    if self.is_widget_destroyed():
        return False
        
    event_type = event.type()
    
    # Only handle mouse press events to reduce overhead
    if event_type != QEvent.Type.MouseButtonPress:
        return False
        
    # Only handle left mouse button
    if event.button() != Qt.MouseButton.LeftButton:
        return False
        
    # Check if we have file_pair (avoid processing empty widgets)
    if not self.file_pair:
        return False
        
    # Register operation for thread safety
    if not self.register_operation("event_handling"):
        return False
        
    try:
        handled = False
        
        if obj == getattr(self, 'thumbnail_label', None):
            # Thumbnail click - preview
            self.preview_image_requested.emit(self.file_pair)
            handled = True
        elif obj == getattr(self, 'filename_label', None):
            # Filename click - open archive
            self.archive_open_requested.emit(self.file_pair)
            handled = True
            
        return handled
        
    except Exception as e:
        logger.warning(f"Error in event filter: {e}")
        return False
    finally:
        self.unregister_operation("event_handling")

# Optimized event filter installation
def _install_event_filters(self):
    """Install optimized event filters."""
    try:
        # Only install if labels exist and widget is not destroyed
        if self.is_widget_destroyed():
            return
            
        # Install with error checking
        labels_to_filter = []
        
        if hasattr(self, "thumbnail_label") and self.thumbnail_label:
            labels_to_filter.append(("thumbnail_label", self.thumbnail_label))
            
        if hasattr(self, "filename_label") and self.filename_label:
            labels_to_filter.append(("filename_label", self.filename_label))
            
        # Install filters with tracking
        for label_name, label in labels_to_filter:
            try:
                label.installEventFilter(self)
                self._event_filters.append(label)
                logger.debug(f"Installed event filter for {label_name}")
            except Exception as e:
                logger.warning(f"Failed to install event filter for {label_name}: {e}")
                
    except Exception as e:
        logger.warning(f"Event filters setup failed: {e}")

def _uninstall_event_filters(self):
    """Safely uninstall all event filters."""
    try:
        for label in self._event_filters.copy():
            try:
                if label and hasattr(label, 'removeEventFilter'):
                    label.removeEventFilter(self)
            except Exception as e:
                logger.debug(f"Error removing event filter: {e}")
        self._event_filters.clear()
    except Exception as e:
        logger.warning(f"Error uninstalling event filters: {e}")
```

---

### PATCH 4: STREAMLINED COMPONENT LIFECYCLE MANAGEMENT

**Problem:** Niezgodność lifecycle między widget a komponentami, complex disposal
**Rozwiązanie:** Unified lifecycle management z proper synchronization

```python
# W _initialize_components około linii 152
def _initialize_components(self):
    """Initialize components with proper lifecycle management."""
    try:
        # Early return if destroyed during initialization
        if self.is_widget_destroyed():
            return
            
        # Event bus with weak references to prevent cycles
        self._event_bus = TileEventBus()
        
        # Component initialization with error handling
        self._components: Dict[str, Any] = {}
        self._component_lock = threading.RLock()
        
        # Initialize thumbnail component
        if self._initialize_thumbnail_component():
            logger.debug("Thumbnail component initialized successfully")
        else:
            logger.warning("Failed to initialize thumbnail component")
            
        # Initialize metadata component
        if self._initialize_metadata_component():
            logger.debug("Metadata component initialized successfully")
        else:
            logger.warning("Failed to initialize metadata component")
            
        # Initialize interaction component
        if self._initialize_interaction_component():
            logger.debug("Interaction component initialized successfully")
        else:
            logger.warning("Failed to initialize interaction component")
            
        # Mark components as initialized
        self._component_disposal_status.clear()  # Not disposed yet
        
    except Exception as e:
        logger.error(f"Error initializing components: {e}")
        self._cleanup_partial_initialization()

def _initialize_thumbnail_component(self) -> bool:
    """Initialize thumbnail component with error handling."""
    try:
        if self.is_widget_destroyed():
            return False
            
        component = ThumbnailComponent(
            config=self._config, 
            event_bus=self._event_bus, 
            parent=self
        )
        
        with self._component_lock:
            self._components['thumbnail'] = component
            
        # Register with resource manager if available
        if self._is_registered and self._resource_manager:
            self._resource_manager.register_component("thumbnail", component)
            
        return True
        
    except Exception as e:
        logger.error(f"Error initializing thumbnail component: {e}")
        return False

def _initialize_metadata_component(self) -> bool:
    """Initialize metadata component with error handling."""
    try:
        if self.is_widget_destroyed():
            return False
            
        component = TileMetadataComponent(
            config=self._config, 
            event_bus=self._event_bus
        )
        
        with self._component_lock:
            self._components['metadata'] = component
            
        if self._is_registered and self._resource_manager:
            self._resource_manager.register_component("metadata", component)
            
        return True
        
    except Exception as e:
        logger.error(f"Error initializing metadata component: {e}")
        return False

def _initialize_interaction_component(self) -> bool:
    """Initialize interaction component with error handling."""
    try:
        if self.is_widget_destroyed():
            return False
            
        component = TileInteractionComponent(
            config=self._config, 
            event_bus=self._event_bus, 
            parent_widget=self
        )
        
        with self._component_lock:
            self._components['interaction'] = component
            
        if self._is_registered and self._resource_manager:
            self._resource_manager.register_component("interaction", component)
            
        return True
        
    except Exception as e:
        logger.error(f"Error initializing interaction component: {e}")
        return False

def _cleanup_partial_initialization(self):
    """Cleanup partially initialized components."""
    try:
        with self._component_lock:
            for name, component in self._components.items():
                try:
                    if hasattr(component, 'cleanup'):
                        component.cleanup()
                except Exception as e:
                    logger.debug(f"Error cleaning up component {name}: {e}")
            self._components.clear()
    except Exception as e:
        logger.warning(f"Error in partial cleanup: {e}")

def dispose_components(self):
    """Thread-safe disposal of all components."""
    if self._component_disposal_status.is_set():
        return  # Already disposed
        
    try:
        with self._component_lock:
            # Mark as being disposed
            self._component_disposal_status.set()
            
            # Dispose components in reverse order
            component_names = list(self._components.keys())
            for name in reversed(component_names):
                component = self._components.pop(name, None)
                if component:
                    try:
                        if hasattr(component, 'dispose'):
                            component.dispose()
                        elif hasattr(component, 'cleanup'):
                            component.cleanup()
                    except Exception as e:
                        logger.debug(f"Error disposing component {name}: {e}")
                        
            # Clear event bus
            if hasattr(self, '_event_bus') and self._event_bus:
                try:
                    self._event_bus.clear_all_subscriptions()
                except Exception as e:
                    logger.debug(f"Error clearing event bus: {e}")
                    
    except Exception as e:
        logger.error(f"Error disposing components: {e}")
```

---

### PATCH 5: CLEANUP OF DEPRECATED API Z MIGRATION WARNINGS

**Problem:** Duplikacja API, spam deprecation warnings, complex backward compatibility
**Rozwiązanie:** Streamlined API z intelligent deprecation warnings

```python
# W CompatibilityAdapter - zmienić mechanizm warnings
class DeprecationWarningManager:
    """Manages deprecation warnings to prevent spam."""
    
    def __init__(self):
        self._warning_counts: Dict[str, int] = {}
        self._warning_lock = threading.RLock()
        self._max_warnings_per_method = 3
        
    def should_show_warning(self, method_name: str) -> bool:
        """Check if deprecation warning should be shown."""
        with self._warning_lock:
            count = self._warning_counts.get(method_name, 0)
            if count < self._max_warnings_per_method:
                self._warning_counts[method_name] = count + 1
                return True
            return False
            
    def get_warning_stats(self) -> Dict[str, int]:
        """Get deprecation warning statistics."""
        with self._warning_lock:
            return self._warning_counts.copy()

# W CompatibilityAdapter.__init__
def __init__(self, widget):
    self.widget_ref = weakref.ref(widget)
    self._deprecation_manager = DeprecationWarningManager()
    
def show_deprecation_warning(self, old_method: str, new_method: str):
    """Show deprecation warning with spam prevention."""
    if self._deprecation_manager.should_show_warning(old_method):
        logger.warning(
            f"DeprecationWarning: {old_method}() is deprecated, "
            f"use {new_method}() instead. "
            f"This widget will show this warning max 3 times."
        )

# Optimized legacy API methods
def change_thumbnail_size_legacy(self, size):
    """Legacy API with migration path."""
    widget = self.widget_ref()
    if not widget or widget.is_widget_destroyed():
        return False
        
    self.show_deprecation_warning("change_thumbnail_size", "set_thumbnail_size")
    
    try:
        widget.set_thumbnail_size(size)
        return True
    except Exception as e:
        logger.error(f"Error in legacy change_thumbnail_size: {e}")
        return False

def refresh_thumbnail_legacy(self):
    """Legacy API with optimized implementation."""
    widget = self.widget_ref()
    if not widget or widget.is_widget_destroyed():
        return False
        
    # Only show warning first few times
    self.show_deprecation_warning("refresh_thumbnail", "reload_thumbnail")
    
    try:
        widget.reload_thumbnail()
        return True
    except Exception as e:
        logger.error(f"Error in legacy refresh_thumbnail: {e}")
        return False

def get_file_data_legacy(self):
    """Legacy API with direct delegation."""
    widget = self.widget_ref()
    if not widget or widget.is_widget_destroyed():
        return None
        
    # Less critical API - fewer warnings
    if self._deprecation_manager.should_show_warning("get_file_data"):
        logger.info("get_file_data() is deprecated, use get_file_pair() instead")
    
    return widget.get_file_pair()

def set_selection_legacy(self, selected: bool):
    """Legacy API with modern implementation."""
    widget = self.widget_ref()
    if not widget or widget.is_widget_destroyed():
        return False
        
    self.show_deprecation_warning("set_selection", "set_selected")
    
    try:
        widget.set_selected(selected)
        return True
    except Exception as e:
        logger.error(f"Error in legacy set_selection: {e}")
        return False
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Thread safety** - wszystkie operacje są bezpieczne wielowątkowo
- [ ] **Resource management** - proper registration/cleanup z resource manager
- [ ] **Asynchronous loading** - thumbnail loading nie blokuje UI
- [ ] **Event handling** - optimized event filters z reduced overhead
- [ ] **Component lifecycle** - unified lifecycle management
- [ ] **Memory management** - brak memory leaks w długich sesjach
- [ ] **Error handling** - proper error handling w wszystkich operacjach
- [ ] **Deprecation warnings** - intelligent warning system bez spam
- [ ] **API compatibility** - backward compatibility zachowana
- [ ] **Performance** - responsywność UI zachowana lub poprawiona

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **TileManager integration** - tworzenie kafli z sygnałami działa
- [ ] **GalleryManager compatibility** - virtual scrolling i batch creation
- [ ] **Resource Manager** - registration limits i cleanup działają
- [ ] **Component architecture** - ThumbnailComponent, MetadataComponent integration
- [ ] **Event Bus** - komunikacja między komponentami działa
- [ ] **Threading primitives** - Event, RLock, weak references działają
- [ ] **Qt integration** - sygnały, slots, event filters działają
- [ ] **Legacy API** - wszystkie deprecated methods działają z warnings

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test single widget** - podstawowa funkcjonalność
- [ ] **Test multiple widgets** - thread safety przy many instances
- [ ] **Test resource limits** - zachowanie przy resource manager limits
- [ ] **Test thumbnail loading** - asynchroniczne loading różnych formatów
- [ ] **Test long sessions** - memory usage w długich sesjach
- [ ] **Test component disposal** - proper cleanup przy destruction
- [ ] **Test legacy API** - backward compatibility z deprecation warnings

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - wszystkie testy muszą przejść
- [ ] **THREAD SAFETY** - brak race conditions w stress tests
- [ ] **MEMORY EFFICIENCY** - <2MB per widget, brak leaks w długich sesjach
- [ ] **UI RESPONSIVENESS** - thumbnail loading <100ms response time
- [ ] **DEPRECATION MANAGEMENT** - max 3 warnings per deprecated method per session