# PATCH-CODE DLA: FILE_TILE_WIDGET_KAFLI

**Powiązany plik z analizą:** `../corrections/file_tile_widget_correction_kafli.md`
**Zasady ogólne:** `../../../_BASE_/refactoring_rules.md`

---

### PATCH 1: THREAD-SAFE DESTROYED CHECKING

**Problem:** `_quick_destroyed_check()` bez lock może prowadzić do race conditions w środowisku wielowątkowym kafli
**Rozwiązanie:** Implementacja atomic flag z proper locking dla thread-safe access

```python
# ZMIANA W LINII 8-9: Dodanie atomic import
import logging
import threading
from typing import Optional, Tuple
from threading import RLock  # DODANE
import weakref  # DODANE dla memory-safe references

# ZMIANA W LINII 84-86: Enhanced thread safety
class FileTileWidget(QWidget):
    def __init__(self, ...):
        super().__init__(parent)
        
        # Thread-safe flagi z proper locking
        self._destroy_lock = RLock()  # ZMIENIONE z threading.RLock()
        self._is_destroyed = threading.Event()  # ZMIENIONE na Event dla atomic operations
        self._component_state_cache = {}  # DODANE dla performance optimization
        self._last_state_check = 0  # DODANE timestamp cache
        
    def _is_widget_destroyed(self) -> bool:
        """Thread-safe sprawdzenie czy widget został zniszczony."""
        return self._is_destroyed.is_set()  # ZMIENIONE na atomic operation
        
    def _quick_destroyed_check(self) -> bool:
        """Thread-safe szybkie sprawdzenie destroyed state."""
        return self._is_destroyed.is_set()  # ZMIENIONE na atomic operation bez lock
        
    def _mark_as_destroyed(self):
        """Thread-safe oznaczenie jako zniszczony."""
        self._is_destroyed.set()  # DODANE atomic set
```

---

### PATCH 2: ENHANCED RESOURCE MANAGER INTEGRATION

**Problem:** Component registration może się nie powieść silently, performance optimization setup może failować
**Rozwiązanie:** Retry mechanism z graceful degradation i proper error handling

```python
# ZMIANA W LINII 88-98: Enhanced resource registration
def __init__(self, ...):
    # Resource management registration z retry mechanism
    self._resource_manager = get_resource_manager()
    self._registration_attempts = 0
    self._max_registration_attempts = 3  # DODANE
    
    self._is_registered = self._attempt_resource_registration(skip_resource_registration)
    if not self._is_registered and not skip_resource_registration:
        logger.warning(
            f"Failed to register tile after {self._max_registration_attempts} attempts - "
            f"continuing with degraded performance"  # ZMIENIONE message
        )

def _attempt_resource_registration(self, skip_registration: bool) -> bool:
    """DODANA: Attempt resource registration z retry mechanism."""
    if skip_registration:
        return False
        
    for attempt in range(self._max_registration_attempts):
        try:
            if self._resource_manager and self._resource_manager.register_tile(self):
                logger.debug(f"Tile registered successfully on attempt {attempt + 1}")
                return True
            else:
                logger.debug(f"Registration attempt {attempt + 1} failed - retrying")
                if attempt < self._max_registration_attempts - 1:
                    threading.Event().wait(0.01)  # Short delay before retry
        except Exception as e:
            logger.warning(f"Registration attempt {attempt + 1} error: {e}")
    
    return False

# ZMIANA W LINII 184-205: Enhanced performance optimization setup
def _setup_performance_optimization(self):
    """Setup performance optimization z proper error handling."""
    self._performance_components_ready = False  # DODANE status flag
    
    try:
        if not self._resource_manager:
            logger.debug("No resource manager available - using fallback components")
            self._setup_fallback_components()
            return
            
        # Try to get components z proper error handling
        components = self._get_performance_components_safely()
        
        if all(components.values()):
            self._performance_monitor = components['monitor']
            self._cache_optimizer = components['cache']
            self._async_ui_manager = components['async_ui']
            self._performance_components_ready = True
            
            # Register with cache optimizer safely
            if self._cache_optimizer:
                try:
                    self._cache_optimizer.register_cache_user(self)
                except Exception as e:
                    logger.debug(f"Cache optimizer registration failed: {e}")
        else:
            logger.debug("Performance components partially unavailable - using fallbacks")
            self._setup_fallback_components()
            
    except Exception as e:
        logger.warning(f"Performance optimization setup failed: {e}")
        self._setup_fallback_components()

def _get_performance_components_safely(self) -> dict:
    """DODANA: Safely get performance components."""
    components = {
        'monitor': None,
        'cache': None, 
        'async_ui': None
    }
    
    try:
        components['monitor'] = self._resource_manager.get_performance_monitor()
    except Exception as e:
        logger.debug(f"Performance monitor unavailable: {e}")
        
    try:
        components['cache'] = self._resource_manager.get_cache_optimizer()
    except Exception as e:
        logger.debug(f"Cache optimizer unavailable: {e}")
        
    try:
        components['async_ui'] = self._resource_manager.get_async_ui_manager()
    except Exception as e:
        logger.debug(f"Async UI manager unavailable: {e}")
        
    return components

def _setup_fallback_components(self):
    """DODANA: Setup fallback components gdy performance components unavailable."""
    self._performance_monitor = None
    self._cache_optimizer = None
    self._async_ui_manager = None
    self._performance_components_ready = False
```

---

### PATCH 3: COMPONENT STATE CACHING OPTIMIZATION

**Problem:** Powtarzające się sprawdzenia stanu komponentów (`hasattr`, disposed checks) spowalniają kafle
**Rozwiązanie:** Caching component state z timestamp-based invalidation

```python
# ZMIANA W LINII 394-404: Optimized component state validation
def set_thumbnail_size(self, new_size):
    """Ustawia nowy rozmiar kafelka z cached component validation."""
    if self._quick_destroyed_check():
        return
        
    # Use cached component state for performance
    if not self._is_thumbnail_component_ready():
        return
        
    # ... rest of method unchanged ...

def _is_thumbnail_component_ready(self) -> bool:
    """DODANA: Cached check for thumbnail component readiness."""
    current_time = time.time()
    cache_key = 'thumbnail_component_ready'
    
    # Check cache validity (cache for 1 second)
    if (cache_key in self._component_state_cache and 
        current_time - self._last_state_check < 1.0):
        return self._component_state_cache[cache_key]
    
    # Perform actual check and cache result
    is_ready = (
        hasattr(self, "_thumbnail_component") and
        self._thumbnail_component is not None and
        not getattr(self._thumbnail_component, "_is_disposed", False) and
        getattr(self._thumbnail_component, "get_current_state", lambda: None)() != TileState.DISPOSED
    )
    
    self._component_state_cache[cache_key] = is_ready
    self._last_state_check = current_time
    
    return is_ready

# ZMIANA W LINII 486-502: Optimized UI update scheduling
def _update_ui_from_file_pair(self):
    """Aktualizuje UI z optimized async scheduling."""
    if self._quick_destroyed_check() or not self.file_pair:
        return

    # Aktualizacja nazwy pliku (synchroniczna, szybka)
    self._update_filename_display()

    # Async updates tylko gdy komponenty są gotowe
    if self._performance_components_ready and self._async_ui_manager:
        self._schedule_async_metadata_update()
    else:
        # Fallback to sync update
        self._update_metadata_controls_sync()

def _schedule_async_metadata_update(self):
    """DODANA: Optimized async metadata update scheduling."""
    try:
        # Try new API first, fallback to old API
        if hasattr(self._async_ui_manager, "schedule_async_update"):
            self._async_ui_manager.schedule_async_update(
                self._update_metadata_controls_async,
                priority='normal',  # DODANE priority
                debounce_key=f'metadata_update_{id(self)}'  # DODANE debouncing
            )
        elif hasattr(self._async_ui_manager, "schedule_ui_update"):
            self._async_ui_manager.schedule_ui_update(
                self._update_metadata_controls_async
            )
        else:
            # No async capability, use sync
            self._update_metadata_controls_sync()
    except Exception as e:
        logger.debug(f"Async scheduling failed, using sync: {e}")
        self._update_metadata_controls_sync()
```

---

### PATCH 4: MEMORY LEAK PREVENTION

**Problem:** Event subscriptions, signal connections i event filters nie są properly cleanup
**Rozwiązanie:** Enhanced cleanup tracking z proper resource deallocation

```python
# ZMIANA W LINII 108-111: Enhanced tracking structures
def __init__(self, ...):
    # Enhanced event tracking dla memory leak prevention
    self._event_subscriptions = weakref.WeakSet()  # ZMIENIONE na WeakSet
    self._signal_connections = []  # Kept as list for proper disconnection
    self._event_filters = weakref.WeakSet()  # ZMIENIONE na WeakSet
    self._cleanup_callbacks = []  # DODANE for custom cleanup functions

# ZMIANA W LINII 304-318: Enhanced event filter installation
def _install_event_filters(self):
    """Instaluje event filters z proper tracking."""
    try:
        # Install and track event filters
        for widget_attr in ['thumbnail_label', 'filename_label']:
            widget = getattr(self, widget_attr, None)
            if widget:
                widget.installEventFilter(self)
                self._event_filters.add(widget)  # WeakSet automatically handles cleanup
                
    except Exception as e:
        logger.warning(f"Event filters setup failed: {e}")

# ZMIANA W LINII 704-708: Enhanced cleanup method
def cleanup(self):
    """Enhanced cleanup z comprehensive resource deallocation."""
    with self._destroy_lock:
        if self._is_destroyed.is_set():
            return
            
        self._mark_as_destroyed()
        
        # Cleanup tracking structures
        self._cleanup_event_subscriptions()
        self._cleanup_signal_connections() 
        self._cleanup_event_filters()
        self._cleanup_performance_components()
        self._run_cleanup_callbacks()
        
        # Delegate to cleanup manager
        if hasattr(self, '_cleanup_manager'):
            self._cleanup_manager.cleanup()
            
        self._is_cleanup_done = True

def _cleanup_event_subscriptions(self):
    """DODANA: Cleanup event subscriptions."""
    try:
        if hasattr(self, '_event_bus') and self._event_bus:
            self._event_bus.unsubscribe_all(self)
    except Exception as e:
        logger.debug(f"Event subscription cleanup failed: {e}")

def _cleanup_signal_connections(self):
    """DODANA: Cleanup signal connections."""
    for connection in self._signal_connections:
        try:
            connection.disconnect()
        except Exception as e:
            logger.debug(f"Signal disconnection failed: {e}")
    self._signal_connections.clear()

def _cleanup_event_filters(self):
    """DODANA: Cleanup event filters."""
    # WeakSet automatically handles most cleanup, but ensure removal
    try:
        for widget in list(self._event_filters):  # Create list to avoid mutation during iteration
            if widget:
                widget.removeEventFilter(self)
    except Exception as e:
        logger.debug(f"Event filter cleanup failed: {e}")

def _cleanup_performance_components(self):
    """DODANA: Cleanup performance components."""
    try:
        if self._cache_optimizer:
            self._cache_optimizer.unregister_cache_user(self)
    except Exception as e:
        logger.debug(f"Performance component cleanup failed: {e}")
        
    # Clear component references
    self._performance_monitor = None
    self._cache_optimizer = None
    self._async_ui_manager = None
    self._performance_components_ready = False

def _run_cleanup_callbacks(self):
    """DODANA: Run registered cleanup callbacks."""
    for callback in self._cleanup_callbacks:
        try:
            callback()
        except Exception as e:
            logger.debug(f"Cleanup callback failed: {e}")
    self._cleanup_callbacks.clear()
```

---

### PATCH 5: ENHANCED ERROR HANDLING WITH GRACEFUL DEGRADATION

**Problem:** Słabe error handling może prowadzić do crashes w środowisku produkcyjnym z tysiącami kafli
**Rozwiązanie:** Comprehensive error handling z metrics i graceful degradation

```python
# DODANA: Error handling mixin na początku pliku
class TileErrorHandler:
    """Mixin for enhanced error handling in tile widgets."""
    
    def __init__(self):
        self._error_count = 0
        self._max_errors = 10  # Circuit breaker threshold
        self._error_timestamps = []
        
    def _handle_tile_error(self, operation: str, error: Exception, fallback_fn=None):
        """Centralized error handling z circuit breaker pattern."""
        self._error_count += 1
        current_time = time.time()
        self._error_timestamps.append(current_time)
        
        # Remove old timestamps (older than 1 minute)
        self._error_timestamps = [
            ts for ts in self._error_timestamps 
            if current_time - ts < 60
        ]
        
        # Check if we're in error storm (more than max_errors in 1 minute)
        if len(self._error_timestamps) > self._max_errors:
            logger.error(f"Tile error storm detected in {operation} - entering degraded mode")
            return self._enter_degraded_mode()
            
        # Log error appropriately
        if self._error_count <= 3:
            logger.warning(f"Tile operation '{operation}' failed: {error}")
        else:
            logger.debug(f"Tile operation '{operation}' failed (error #{self._error_count}): {error}")
            
        # Try fallback if provided
        if fallback_fn:
            try:
                return fallback_fn()
            except Exception as fallback_error:
                logger.debug(f"Fallback for '{operation}' also failed: {fallback_error}")
                
        return None
        
    def _enter_degraded_mode(self):
        """Enter degraded mode when too many errors occur."""
        logger.warning("Tile entering degraded mode due to error storm")
        # Disable non-essential features
        self._performance_components_ready = False
        # Return basic functionality
        return True

# ZMIANA: FileTileWidget dziedziczy z error handler
class FileTileWidget(QWidget, TileErrorHandler):
    def __init__(self, ...):
        QWidget.__init__(self, parent)
        TileErrorHandler.__init__(self)  # Initialize error handling
        
        # ... rest of init ...

# ZMIANA W METODACH: Wrap critical operations in error handling
def _on_thumbnail_loaded(self, pixmap, path, width, height):
    """Obsługuje załadowaną miniaturę z error handling."""
    try:
        if self._quick_destroyed_check():
            return
            
        if not hasattr(self, "thumbnail_label") or self.thumbnail_label is None:
            return
            
        if pixmap and not pixmap.isNull():
            self.thumbnail_label.setPixmap(pixmap)
            
            if self.file_pair:
                color_tag = self.file_pair.get_color_tag()
                if color_tag and color_tag.strip():
                    self._update_thumbnail_border_color(color_tag)
        else:
            if hasattr(self, "thumbnail_label"):
                self.thumbnail_label.setText("Błąd ładowania")
                
    except Exception as e:
        self._handle_tile_error(
            "thumbnail_loading", 
            e, 
            lambda: self._fallback_thumbnail_display()
        )

def _fallback_thumbnail_display(self):
    """DODANA: Fallback thumbnail display when loading fails."""
    if hasattr(self, "thumbnail_label"):
        self.thumbnail_label.setText("!")
        self.thumbnail_label.setToolTip("Miniatura niedostępna")
```

---

## ✅ CHECKLISTA WERYFIKACYJNA KAFLI (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI KAFLI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa kafli** - czy kafelek nadal wyświetla miniaturę, nazwę i metadata
- [ ] **API kompatybilność kafli** - czy wszystkie 27 publicznych metod działają dla TileManager
- [ ] **Obsługa błędów kafli** - czy mechanizmy error handling z graceful degradation działają
- [ ] **Thread safety kafli** - czy destroyed checking i component access są thread-safe
- [ ] **Logowanie kafli** - czy system logowania nie spamuje przy błędach komponentów
- [ ] **Cache kafli** - czy cache'owanie component state działa poprawnie
- [ ] **Memory management kafli** - czy nie ma wycieków pamięci przy cleanup kafli
- [ ] **Performance kafli** - czy tworzenie 1000+ kafli nie zostało spowolnione

#### **ZALEŻNOŚCI KAFLI DO WERYFIKACJI:**

- [ ] **Importy kafli** - czy wszystkie importy komponentów kafli działają
- [ ] **Resource Manager integration** - czy rejestracja kafli z retry mechanism działa
- [ ] **Component communication** - czy EventBus między komponentami kafli działa
- [ ] **TileManager compatibility** - czy TileManager może tworzyć kafle bez błędów
- [ ] **GalleryManager compatibility** - czy galeria może renderować tysiące kafli
- [ ] **Backward compatibility kafli** - czy legacy API dla kafli jest zachowane
- [ ] **Signal/slot connections kafli** - czy połączenia Qt między komponentami działają
- [ ] **Performance components kafli** - czy integracja z monitoring/cache/async UI działa

#### **TESTY WERYFIKACYJNE KAFLI:**

- [ ] **Test jednostkowy kafli** - czy wszystkie metody kafli działają w izolacji
- [ ] **Test integracyjny kafli** - czy integracja z ResourceManager i komponentami działa
- [ ] **Test regresyjny kafli** - czy nie wprowadzono regresji w galerii kafli
- [ ] **Test wydajnościowy kafli** - czy czas tworzenia 1000 kafli jest akceptowalny
- [ ] **Test thread safety kafli** - czy concurrent access do kafli nie powoduje crashes
- [ ] **Test memory leaks kafli** - czy długotrwałe używanie kafli nie powoduje wycieków
- [ ] **Test error handling kafli** - czy graceful degradation działa przy błędach komponentów
- [ ] **Test resource limits kafli** - czy kafle respektują limity ResourceManager

#### **KRYTERIA SUKCESU KAFLI:**

- [ ] **WSZYSTKIE CHECKLISTY KAFLI MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS KAFLI** - wszystkie testy kafli muszą przejść
- [ ] **PERFORMANCE BUDGET KAFLI** - tworzenie kafli nie spowolnione o więcej niż 5%
- [ ] **MEMORY BUDGET KAFLI** - zużycie pamięci kafli nie zwiększone o więcej niż 10%
- [ ] **GALERIA RESPONSYWNOŚĆ** - przewijanie tysięcy kafli nadal płynne
- [ ] **THREAD SAFETY VERIFIED** - brak race conditions w środowisku wielowątkowym kafli