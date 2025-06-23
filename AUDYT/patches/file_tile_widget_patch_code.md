# PATCH-CODE DLA: FILE_TILE_WIDGET

**Powiązany plik z analizą:** `../corrections/file_tile_widget_correction.md`
**Zasady ogólne:** `../../_BASE_/refactoring_rules.md`

---

### PATCH 1: USUNIĘCIE DUPLIKACJI COMPATIBILITYADAPTER I NAMESPACE CLEANUP

**Problem:** CompatibilityAdapter jest zdefiniowana dwukrotnie - w imports i jako klasa
**Rozwiązanie:** Usunięcie duplikacji, cleanup imports, jednoznaczny namespace

```python
# USUNĄĆ Z IMPORTS (linia 60):
from .file_tile_widget_compatibility import CompatibilityAdapter

# ZACHOWAĆ TYLKO JEDNĄ DEFINICJĘ KLASY (linie 69-114):
class CompatibilityAdapter:
    """Adapter dla zachowania kompatybilności wstecznej."""
    # ... existing implementation ...

# DODAĆ na początku po imports:
"""
Simplified file tile widget z optimized component architecture.

Key optimizations:
- Reduced component architecture complexity
- Enhanced thread safety z proper locking
- Comprehensive memory management z resource cleanup
- Optimized event handling z minimal routing overhead
- Consistent error handling z proper fallbacks

Performance targets:
- 1000+ tiles rendered w <5 sekund
- <0.5MB memory per tile średnio
- <100ms UI response time
- Smooth gallery scrolling
- Zero memory leaks w long sessions
"""

# CLEANUP IMPORTS - grupowanie i organizacja:
# Standard library imports
import logging
import os
import threading
import warnings
import weakref
from typing import Optional, Tuple, Dict, Set
from dataclasses import dataclass

# Third-party imports
from PyQt6.QtCore import QEvent, QPoint, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QAction, QColor, QDesktopServices, QDrag, QFont, 
    QPainter, QPixmap
)
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMenu,
    QSizePolicy, QVBoxLayout, QWidget
)

# Local imports - organized by functionality
from src.models.file_pair import FilePair
from src.ui.widgets.metadata_controls_widget import MetadataControlsWidget
from src.ui.widgets.thumbnail_cache import ThumbnailCache

# Tile architecture imports
from src.ui.widgets.tile_config import TileConfig, TileEvent
from src.ui.widgets.tile_event_bus import TileEventBus
from src.ui.widgets.tile_styles import TileColorScheme, TileSizeConstants, TileStylesheet

# Specialized managers imports
from .file_tile_widget_cleanup import FileTileWidgetCleanupManager
from .file_tile_widget_events import FileTileWidgetEventManager
from .file_tile_widget_performance import get_performance_metric
from .file_tile_widget_thumbnail import ThumbnailOperations
from .file_tile_widget_ui_manager import FileTileWidgetUIManager
```

---

### PATCH 2: ENHANCED THREAD SAFETY I MEMORY MANAGEMENT

**Problem:** Incomplete thread safety, potential memory leaks w event tracking
**Rozwiązanie:** Comprehensive locking, atomic operations, complete cleanup tracking

```python
import uuid
from threading import RLock
from contextlib import contextmanager

@dataclass
class TileResourceTracker:
    """Enhanced resource tracking dla comprehensive cleanup."""
    tile_id: str
    event_subscriptions: Set[str]
    signal_connections: Set[object]
    event_filters: Set[object]
    component_resources: Dict[str, object]
    is_cleanup_done: bool = False
    cleanup_error: Optional[str] = None

class ThreadSafeTileManager:
    """Thread-safe manager dla tile resources z atomic operations."""
    
    def __init__(self):
        self._lock = RLock()
        self._resource_trackers: Dict[str, TileResourceTracker] = {}
        self._cleanup_queue: Set[str] = set()
        
    @contextmanager
    def atomic_operation(self, tile_id: str):
        """Atomic operation context dla thread safety."""
        with self._lock:
            yield self._resource_trackers.get(tile_id)
    
    def register_tile(self, tile_id: str) -> TileResourceTracker:
        """Thread-safe tile registration."""
        with self._lock:
            tracker = TileResourceTracker(
                tile_id=tile_id,
                event_subscriptions=set(),
                signal_connections=set(),
                event_filters=set(),
                component_resources={}
            )
            self._resource_trackers[tile_id] = tracker
            return tracker
    
    def cleanup_tile(self, tile_id: str) -> bool:
        """Thread-safe tile cleanup z error handling."""
        with self._lock:
            if tile_id in self._cleanup_queue:
                return False  # Already in cleanup
            
            self._cleanup_queue.add(tile_id)
            
            try:
                tracker = self._resource_trackers.get(tile_id)
                if tracker and not tracker.is_cleanup_done:
                    # Cleanup components
                    for name, component in tracker.component_resources.items():
                        if hasattr(component, 'cleanup'):
                            component.cleanup()
                    
                    # Clear collections
                    tracker.event_subscriptions.clear()
                    tracker.signal_connections.clear()
                    tracker.event_filters.clear()
                    tracker.component_resources.clear()
                    tracker.is_cleanup_done = True
                    
                    return True
            except Exception as e:
                if tracker:
                    tracker.cleanup_error = str(e)
                logger.error(f"Cleanup error for tile {tile_id}: {e}")
                return False
            finally:
                self._cleanup_queue.discard(tile_id)

# Global thread-safe tile manager
_tile_manager = ThreadSafeTileManager()

# ZMODYFIKUJ FileTileWidget initialization:
class FileTileWidget(QWidget):
    def __init__(self, file_pair: Optional[FilePair], default_thumbnail_size: tuple[int, int] = TileSizeConstants.DEFAULT_THUMBNAIL_SIZE, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        # Unique tile ID dla tracking
        self._tile_id = str(uuid.uuid4())[:8]
        
        # Thread-safe resource tracking
        self._resource_tracker = _tile_manager.register_tile(self._tile_id)
        self._resource_lock = RLock()
        
        # Podstawowe właściwości
        self.file_pair = file_pair
        self.thumbnail_size = default_thumbnail_size
        self.is_selected = False
        
        # Enhanced thread-safe state
        self._initialization_complete = False
        self._cleanup_in_progress = False
        
        logger.debug(f"FileTileWidget {self._tile_id} initialized with thread-safe tracking")
        
        # Initialize w atomic operation
        with _tile_manager.atomic_operation(self._tile_id):
            self._initialize_safely()
    
    def _initialize_safely(self):
        """Thread-safe initialization z proper error handling."""
        try:
            # Resource manager registration
            self._resource_manager = get_resource_manager()
            self._is_registered = self._resource_manager.register_tile(self)
            
            if not self._is_registered:
                logger.warning(f"Tile {self._tile_id}: Resource manager registration failed")
                # Continue initialization z fallback behavior
            
            # Konfiguracja komponentu
            self._config = TileConfig(thumbnail_size=self.thumbnail_size)
            
            # Initialize components ATOMICALLY
            self._initialize_components_safely()
            
            # Initialize managers
            self._initialize_managers_safely()
            
            # Setup UI
            self._setup_ui_safely()
            
            # Connect signals
            self._connect_signals_safely()
            
            # Install event filters
            self._install_event_filters_safely()
            
            # Mark initialization complete
            self._initialization_complete = True
            
            # Update data if provided
            if self.file_pair:
                self.update_data(self.file_pair)
                
        except Exception as e:
            logger.error(f"Tile {self._tile_id} initialization failed: {e}")
            # Ensure partial cleanup
            self._cleanup_on_error()
            raise
    
    def _initialize_components_safely(self):
        """Thread-safe component initialization."""
        try:
            # Event bus dla komunikacji
            self._event_bus = TileEventBus()
            self._resource_tracker.component_resources['event_bus'] = self._event_bus
            
            # Components z error handling
            self._thumbnail_component = ThumbnailComponent(
                config=self._config, event_bus=self._event_bus, parent=self
            )
            self._resource_tracker.component_resources['thumbnail'] = self._thumbnail_component
            
            self._metadata_component = TileMetadataComponent(
                config=self._config, event_bus=self._event_bus
            )
            self._resource_tracker.component_resources['metadata'] = self._metadata_component
            
            self._interaction_component = TileInteractionComponent(
                config=self._config, event_bus=self._event_bus, parent_widget=self
            )
            self._resource_tracker.component_resources['interaction'] = self._interaction_component
            
            # Register components with resource manager
            if self._is_registered:
                for name, component in self._resource_tracker.component_resources.items():
                    if name != 'event_bus':  # Skip event bus registration
                        self._resource_manager.register_component(name, component)
                        
        except Exception as e:
            logger.error(f"Tile {self._tile_id} component initialization failed: {e}")
            raise
    
    def _cleanup_on_error(self):
        """Cleanup resources w przypadku error during initialization."""
        with self._resource_lock:
            try:
                _tile_manager.cleanup_tile(self._tile_id)
            except Exception as cleanup_error:
                logger.error(f"Cleanup on error failed for tile {self._tile_id}: {cleanup_error}")
```

---

### PATCH 3: SIMPLIFIED COMPONENT ARCHITECTURE I EVENT HANDLING OPTIMIZATION

**Problem:** Over-engineered component architecture, inefficient event routing
**Rozwiązanie:** Simplified architecture, direct connections gdzie możliwe, reduced overhead

```python
class OptimizedEventHandler:
    """Simplified event handling z direct connections."""
    
    def __init__(self, widget):
        self.widget = widget
        self._direct_connections = {}
        self._event_routing_enabled = True
    
    def enable_direct_mode(self):
        """Enable direct event connections dla performance."""
        self._event_routing_enabled = False
        
        # Direct signal connections instead of routing przez components
        if hasattr(self.widget, 'metadata_controls'):
            # Direct connection instead of component routing
            self.widget.metadata_controls.stars_changed.connect(
                self.widget._on_metadata_stars_changed_direct
            )
            self.widget.metadata_controls.color_changed.connect(
                self.widget._on_metadata_color_changed_direct
            )
    
    def disable_direct_mode(self):
        """Fallback to component routing."""
        self._event_routing_enabled = True
        # Disconnect direct connections and use component routing

class SimplifiedComponentManager:
    """Simplified component management z reduced layers."""
    
    def __init__(self, widget):
        self.widget = widget
        self._core_components = {}
        self._ui_elements = {}
    
    def create_essential_components(self):
        """Create only essential components - merge related functionality."""
        # Merged thumbnail + metadata component
        self._core_components['display'] = DisplayComponent(
            widget=self.widget,
            config=self.widget._config
        )
        
        # Simplified interaction component
        self._core_components['interaction'] = SimplifiedInteractionComponent(
            widget=self.widget
        )
        
        return self._core_components

class DisplayComponent:
    """Merged thumbnail and metadata functionality."""
    
    def __init__(self, widget, config):
        self.widget = widget
        self.config = config
        self._thumbnail_cache = ThumbnailCache.get_instance()
        
    def update_display(self, file_pair):
        """Update both thumbnail and metadata w single operation."""
        if not file_pair:
            self._clear_display()
            return
        
        # Thumbnail update
        self._update_thumbnail(file_pair)
        
        # Metadata update
        self._update_metadata(file_pair)
    
    def _update_thumbnail(self, file_pair):
        """Direct thumbnail update bez component routing."""
        preview_path = file_pair.get_preview_path()
        if preview_path and os.path.exists(preview_path):
            # Direct cache access
            pixmap = self._thumbnail_cache.get_thumbnail(
                preview_path, self.config.thumbnail_size
            )
            if pixmap and not pixmap.isNull():
                self.widget.thumbnail_label.setPixmap(pixmap)
                return
        
        # Fallback display
        self.widget.thumbnail_label.setText("Brak podglądu")
    
    def _update_metadata(self, file_pair):
        """Direct metadata update bez component routing."""
        if hasattr(self.widget, 'metadata_controls'):
            # Direct UI update
            self.widget.metadata_controls.set_file_pair(file_pair)
            
            # Update border color
            color_tag = file_pair.get_color_tag()
            if color_tag:
                self.widget._update_thumbnail_border_color(color_tag)

# ZMODYFIKUJ FileTileWidget aby używał simplified architecture:
def _initialize_components_safely(self):
    """Simplified component initialization."""
    try:
        # Use simplified component manager instead of complex architecture
        self._component_manager = SimplifiedComponentManager(self)
        self._core_components = self._component_manager.create_essential_components()
        
        # Optimized event handler
        self._event_handler = OptimizedEventHandler(self)
        self._event_handler.enable_direct_mode()  # Use direct connections
        
        # Track in resource tracker
        self._resource_tracker.component_resources.update(self._core_components)
        self._resource_tracker.component_resources['event_handler'] = self._event_handler
        
    except Exception as e:
        logger.error(f"Tile {self._tile_id} simplified component init failed: {e}")
        raise

# DODAJ optimized event callbacks:
def _on_metadata_stars_changed_direct(self, stars: int):
    """Direct stars change handling bez component routing."""
    if self.file_pair:
        # Direct UI update
        if hasattr(self, "metadata_controls"):
            self.metadata_controls.update_stars_display(stars)
        
        # Direct signal emission
        self.stars_changed.emit(self.file_pair, stars)
        self.file_pair_updated.emit(self.file_pair)

def _on_metadata_color_changed_direct(self, color_hex: str):
    """Direct color change handling bez component routing."""
    if self.file_pair:
        # Direct UI update
        if hasattr(self, "metadata_controls"):
            self.metadata_controls.update_color_tag_display(color_hex)
        
        # Direct border update
        self._update_thumbnail_border_color(color_hex)
        
        # Direct signal emission
        self.color_tag_changed.emit(self.file_pair, color_hex)
        self.file_pair_updated.emit(self.file_pair)
```

---

### PATCH 4: COMPREHENSIVE CLEANUP I ERROR HANDLING

**Problem:** Incomplete cleanup, inconsistent error handling
**Rozwiązanie:** Complete resource cleanup, standardized error handling z fallbacks

```python
import weakref
from typing import Callable

class ComprehensiveCleanupManager:
    """Enhanced cleanup manager z comprehensive resource tracking."""
    
    def __init__(self, widget):
        self.widget_ref = weakref.ref(widget)
        self._cleanup_callbacks: List[Callable] = []
        self._cleanup_completed = False
        self._cleanup_error = None
    
    def register_cleanup_callback(self, callback: Callable):
        """Register callback dla cleanup operations."""
        self._cleanup_callbacks.append(callback)
    
    def perform_comprehensive_cleanup(self):
        """Perform all cleanup operations z error handling."""
        if self._cleanup_completed:
            return True
        
        widget = self.widget_ref()
        if not widget:
            return True  # Widget already destroyed
        
        cleanup_errors = []
        
        try:
            # Cleanup components
            self._cleanup_components(widget, cleanup_errors)
            
            # Cleanup UI elements
            self._cleanup_ui_elements(widget, cleanup_errors)
            
            # Cleanup event connections
            self._cleanup_event_connections(widget, cleanup_errors)
            
            # Run registered callbacks
            self._run_cleanup_callbacks(cleanup_errors)
            
            # Mark cleanup complete
            self._cleanup_completed = True
            
            if cleanup_errors:
                logger.warning(f"Cleanup completed with {len(cleanup_errors)} warnings")
                return False
            
            return True
            
        except Exception as e:
            self._cleanup_error = str(e)
            logger.error(f"Comprehensive cleanup failed: {e}")
            return False
    
    def _cleanup_components(self, widget, cleanup_errors):
        """Cleanup all components z error handling."""
        if hasattr(widget, '_core_components'):
            for name, component in widget._core_components.items():
                try:
                    if hasattr(component, 'cleanup'):
                        component.cleanup()
                    elif hasattr(component, 'deleteLater'):
                        component.deleteLater()
                except Exception as e:
                    cleanup_errors.append(f"Component {name} cleanup: {e}")
        
        if hasattr(widget, '_component_manager'):
            try:
                widget._component_manager = None
            except Exception as e:
                cleanup_errors.append(f"Component manager cleanup: {e}")
    
    def _cleanup_ui_elements(self, widget, cleanup_errors):
        """Cleanup UI elements z proper Qt cleanup."""
        ui_elements = ['thumbnail_label', 'filename_label', 'metadata_controls', 'thumbnail_frame']
        
        for element_name in ui_elements:
            if hasattr(widget, element_name):
                try:
                    element = getattr(widget, element_name)
                    if element and hasattr(element, 'deleteLater'):
                        element.deleteLater()
                        setattr(widget, element_name, None)
                except Exception as e:
                    cleanup_errors.append(f"UI element {element_name} cleanup: {e}")
    
    def _cleanup_event_connections(self, widget, cleanup_errors):
        """Cleanup all event connections and filters."""
        try:
            # Remove event filters
            if hasattr(widget, '_event_filters'):
                for obj in widget._event_filters:
                    try:
                        if obj:
                            obj.removeEventFilter(widget)
                    except:
                        pass  # Ignore errors - object might be destroyed
            
            # Disconnect signals
            if hasattr(widget, '_signal_connections'):
                for connection in widget._signal_connections:
                    try:
                        if connection:
                            connection.disconnect()
                    except:
                        pass  # Ignore errors - connection might be destroyed
                        
        except Exception as e:
            cleanup_errors.append(f"Event connections cleanup: {e}")
    
    def _run_cleanup_callbacks(self, cleanup_errors):
        """Run all registered cleanup callbacks."""
        for callback in self._cleanup_callbacks:
            try:
                callback()
            except Exception as e:
                cleanup_errors.append(f"Cleanup callback error: {e}")

# ZMODYFIKUJ FileTileWidget cleanup:
def cleanup(self):
    """Comprehensive cleanup z enhanced error handling."""
    with self._resource_lock:
        if self._cleanup_in_progress:
            return  # Already cleaning up
        
        self._cleanup_in_progress = True
        
        try:
            # Use comprehensive cleanup manager
            if not hasattr(self, '_comprehensive_cleanup'):
                self._comprehensive_cleanup = ComprehensiveCleanupManager(self)
            
            success = self._comprehensive_cleanup.perform_comprehensive_cleanup()
            
            # Global tile manager cleanup
            _tile_manager.cleanup_tile(self._tile_id)
            
            # Resource manager cleanup
            if hasattr(self, '_resource_manager') and self._is_registered:
                try:
                    self._resource_manager.unregister_tile(self)
                except Exception as e:
                    logger.warning(f"Resource manager cleanup warning: {e}")
            
            if success:
                logger.debug(f"Tile {self._tile_id} cleanup completed successfully")
            else:
                logger.warning(f"Tile {self._tile_id} cleanup completed with warnings")
                
        except Exception as e:
            logger.error(f"Tile {self._tile_id} cleanup failed: {e}")
        finally:
            self._cleanup_in_progress = False

def __del__(self):
    """Destructor z failsafe cleanup."""
    try:
        if not self._cleanup_in_progress and hasattr(self, '_tile_id'):
            self.cleanup()
    except:
        pass  # Ignore all errors w destructor

# DODAJ standardized error handling dla UI operations:
def _safe_ui_operation(self, operation_name: str, operation_func: Callable, *args, **kwargs):
    """Wrapper dla safe UI operations z error handling."""
    try:
        return operation_func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"Tile {self._tile_id} {operation_name} failed: {e}")
        # Return safe fallback
        return None

def update_data(self, file_pair: FilePair):
    """Thread-safe data update z error handling."""
    with self._resource_lock:
        if self._cleanup_in_progress:
            return
        
        self._safe_ui_operation(
            "data_update",
            self._update_data_internal,
            file_pair
        )

def _update_data_internal(self, file_pair: FilePair):
    """Internal data update implementation."""
    self.file_pair = file_pair
    
    if hasattr(self, '_core_components') and 'display' in self._core_components:
        self._core_components['display'].update_display(file_pair)
    else:
        # Fallback update
        self._fallback_data_update(file_pair)

def _fallback_data_update(self, file_pair: FilePair):
    """Fallback data update w przypadku component errors."""
    try:
        # Basic filename update
        if hasattr(self, 'filename_label'):
            self.filename_label.setText(file_pair.get_base_name())
        
        # Basic metadata update
        if hasattr(self, 'metadata_controls'):
            self.metadata_controls.set_file_pair(file_pair)
            
    except Exception as e:
        logger.error(f"Fallback data update failed: {e}")
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - tile creation, thumbnail display, metadata handling
- [ ] **API kompatybilność** - wszystkie public methods działają z expected behavior
- [ ] **Obsługa błędów** - comprehensive error handling z proper fallbacks
- [ ] **Walidacja danych** - file_pair validation i proper handling of None values
- [ ] **Logowanie** - structured logging nie spamuje, proper log levels
- [ ] **Konfiguracja** - tile configuration i sizing settings działają
- [ ] **Cache** - thumbnail cache integration efficient i proper
- [ ] **Thread safety** - tile operations thread-safe, no race conditions
- [ ] **Memory management** - comprehensive cleanup, no memory leaks
- [ ] **Performance** - 1000+ tiles render w <5 sekund, smooth UI

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - wszystkie imports resolved properly, no circular dependencies
- [ ] **Zależności zewnętrzne** - PyQt6 widgets used properly, proper Qt cleanup
- [ ] **Zależności wewnętrzne** - integration z gallery_tab.py, thumbnail_cache.py maintained
- [ ] **Cykl zależności** - no circular dependencies introduced przez simplified architecture
- [ ] **Backward compatibility** - legacy API calls działają z deprecation warnings
- [ ] **Interface contracts** - tile interface contracts maintained
- [ ] **Event handling** - Qt events i custom events properly handled
- [ ] **Signal/slot connections** - all signal connections work, proper cleanup
- [ ] **File I/O** - thumbnail file operations robust z error handling

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - all tile methods działają w izolacji
- [ ] **Test integracyjny** - integration z gallery works properly
- [ ] **Test regresyjny** - no functionality regressions
- [ ] **Test wydajnościowy** - 1000+ tiles performance benchmark passes
- [ ] **Test UI responsiveness** - gallery scrolling smooth, no lagów
- [ ] **Test thread safety** - concurrent tile operations safe
- [ ] **Test memory management** - no memory leaks w long sessions

#### **PERFORMANCE KRYTERIA:**

- [ ] **Tile rendering** - 1000+ tiles w <5 sekund
- [ ] **Memory usage** - <0.5MB per tile średnio, proper cleanup
- [ ] **UI responsiveness** - <100ms response dla user interactions
- [ ] **Gallery scrolling** - smooth scrolling z 1000+ tiles
- [ ] **Event handling** - <1ms overhead dla event propagation
- [ ] **Component communication** - minimal overhead z simplified architecture

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - wszystkie testy file tile widget przechodzą
- [ ] **PERFORMANCE BUDGET** - tile rendering i UI responsiveness maintained
- [ ] **CODE COVERAGE** - coverage maintained lub improved
- [ ] **MEMORY MANAGEMENT** - comprehensive cleanup tests pass
- [ ] **THREAD SAFETY** - concurrent operations tests pass