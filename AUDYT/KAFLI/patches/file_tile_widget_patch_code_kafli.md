# PATCH-CODE DLA: FILE_TILE_WIDGET - OPTYMALIZACJA KAFLI

**Powiązany plik z analizą:** `../corrections/file_tile_widget_correction_kafli.md`
**Zasady ogólne:** `../../../_BASE_/refactoring_rules.md`

---

### PATCH 1: USUNIĘCIE DUPLIKACJI COMPATIBILITYADAPTER

**Problem:** Klasa CompatibilityAdapter jest zdefiniowana dwa razy - importowana z modułu i redefinowana w pliku (linie 68-113)
**Rozwiązanie:** Usunięcie duplikującej definicji i używanie tylko importowanej wersji

```python
# USUNĄĆ LINIE 68-113 - duplikującą definicję klasy CompatibilityAdapter

# Zachować tylko import na linii 59:
from .file_tile_widget_compatibility import CompatibilityAdapter

# Reszta kodu pozostaje bez zmian
```

---

### PATCH 2: THREAD-SAFE OPTYMALIZACJA SPRAWDZENIA _IS_DESTROYED

**Problem:** Nadmierne sprawdzenie `_is_destroyed` w każdej metodzie callback dodaje overhead przy renderowaniu tysięcy kafli
**Rozwiązanie:** Implementacja thread-safe lazy checking z early return optimization

```python
import threading
from functools import wraps

def _ensure_not_destroyed(func):
    """Decorator dla thread-safe sprawdzenia czy widget nie został zniszczony."""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # Fast path - sprawdź bez lock jeśli już destroyed
        if getattr(self, '_is_destroyed', False):
            return
        
        # Slow path - thread-safe check z RLock
        with getattr(self, '_cleanup_lock', threading.RLock()):
            if getattr(self, '_is_destroyed', False):
                return
            return func(self, *args, **kwargs)
    return wrapper

class FileTileWidget(QWidget):
    def __init__(self, ...):
        # Existing code...
        self._is_destroyed = False
        self._cleanup_lock = threading.RLock()
        # Existing code...

    @_ensure_not_destroyed  
    def _on_thumbnail_component_loaded(self, path: str, pixmap: QPixmap):
        """Callback gdy thumbnail component załadował miniaturę."""
        # USUNĄĆ: if self._is_destroyed: return
        # USUNĄĆ: if not hasattr(self, "thumbnail_label") or self.thumbnail_label is None: return
        
        if pixmap and not pixmap.isNull() and hasattr(self, "thumbnail_label"):
            self.thumbnail_label.setPixmap(pixmap)

    @_ensure_not_destroyed
    def _on_thumbnail_loaded(self, pixmap, path, width, height):
        """Obsługuje załadowaną miniaturę - dla TileManager."""
        # USUNĄĆ: Duplikujące sprawdzenia _is_destroyed i thumbnail_label
        
        if pixmap and not pixmap.isNull():
            if hasattr(self, "thumbnail_label"):
                self.thumbnail_label.setPixmap(pixmap)
            
            if self.file_pair:
                color_tag = self.file_pair.get_color_tag()
                if color_tag and color_tag.strip():
                    self._update_thumbnail_border_color(color_tag)
        else:
            if hasattr(self, "thumbnail_label"):
                self.thumbnail_label.setText("Błąd ładowania")

    @_ensure_not_destroyed
    def _on_metadata_stars_changed(self, stars: int):
        """Callback dla zmian gwiazdek z UI."""
        # USUNĄĆ: if self._is_destroyed: return
        # USUNĄĆ: if hasattr(self, "_metadata_component") and self._metadata_component:
        
        if hasattr(self, "_metadata_component") and self._metadata_component:
            self._metadata_component.set_stars(stars)
        
        # Reszta kodu bez zmian...

    # Zastosować @_ensure_not_destroyed do wszystkich callback methods:
    # _on_metadata_color_changed, _on_tile_selection_changed, _update_thumbnail_border_color
```

---

### PATCH 3: OPTYMALIZACJA _UPDATE_FILENAME_DISPLAY

**Problem:** `_update_filename_display()` wywoływana za każdym razem bez sprawdzenia czy display_name się rzeczywiście zmienił
**Rozwiązanie:** Cache poprzedniej wartości i update tylko przy zmianie

```python
class FileTileWidget(QWidget):
    def __init__(self, ...):
        # Existing code...
        self._cached_display_name = ""  # Cache dla optymalizacji
        # Existing code...

    @_ensure_not_destroyed
    def _update_filename_display(self):
        """Optymalizowana aktualizacja nazwy pliku z cache."""
        # Oblicz nową display_name
        filename = self.file_pair.base_name if self.file_pair else ""
        
        if (hasattr(self, "_tile_number") and hasattr(self, "_tile_total") 
            and self._tile_number and self._tile_total):
            display_name = f"[{self._tile_number}/{self._tile_total}] {filename}"
        else:
            display_name = filename
        
        # Optimization: Update tylko jeśli się zmieniło
        if self._cached_display_name != display_name:
            self._cached_display_name = display_name
            if hasattr(self, "filename_label"):
                self.filename_label.setText(display_name)
                
                # Tooltip = oryginalna ścieżka pliku (dla podglądu)
                if self.file_pair:
                    self.filename_label.setToolTip(self.file_pair.archive_path)
                else:
                    self.filename_label.setToolTip("")

    def set_tile_number(self, number: int, total: int):
        """Optimized tile numbering with cache invalidation."""
        if (getattr(self, '_tile_number', None) != number or 
            getattr(self, '_tile_total', None) != total):
            self._tile_number = number
            self._tile_total = total
            self._cached_display_name = ""  # Invalidate cache
            self._update_filename_display()
```

---

### PATCH 4: WYKORZYSTANIE ASYNC UI MANAGER

**Problem:** Niektóre operacje UI nie używają async UI manager mimo jego dostępności, co może blokować responsywność
**Rozwiązanie:** Delegacja operacji UI update do async manager dla non-blocking updates

```python
class FileTileWidget(QWidget):
    @_ensure_not_destroyed
    def _update_ui_from_file_pair(self):
        """Asynchroniczna aktualizacja UI na podstawie danych z file_pair."""
        if not self.file_pair:
            return

        # Synchronous updates - krytyczne dla UX
        self._update_filename_display()
        
        # Asynchronous updates - non-blocking dla metadata
        if self._async_ui_manager and hasattr(self, "metadata_controls"):
            def _async_metadata_update():
                self.metadata_controls.setEnabled(True)
                self.metadata_controls.set_file_pair(self.file_pair)
                self.metadata_controls.update_selection_display(False)
                self.metadata_controls.update_stars_display(self.file_pair.get_stars())
                
                # Color update
                color_tag = self.file_pair.get_color_tag()
                self.metadata_controls.update_color_tag_display(color_tag)
                self._update_thumbnail_border_color(color_tag)
            
            # Schedule async UI update
            self._async_ui_manager.schedule_ui_update(
                self, _async_metadata_update, priority="normal"
            )
        else:
            # Fallback to synchronous if async manager not available
            if hasattr(self, "metadata_controls"):
                self.metadata_controls.setEnabled(True)
                self.metadata_controls.set_file_pair(self.file_pair)
                # ... rest of metadata updates
```

---

### PATCH 5: THREAD-SAFE CLEANUP ENHANCEMENT

**Problem:** Race condition w cleanup i niepełne śledzenie event filters
**Rozwiązanie:** Enhanced thread-safe cleanup z proper resource tracking

```python
class FileTileWidget(QWidget):
    def cleanup(self):
        """Enhanced thread-safe cleanup dla kafli."""
        # Double-checked locking pattern dla thread safety
        if self._is_destroyed:
            return
            
        with self._cleanup_lock:
            if self._is_destroyed:  # Double check
                return
                
            # Mark as destroyed first
            self._is_destroyed = True
            
            try:
                # Delegate to cleanup manager with enhanced tracking
                if hasattr(self, '_cleanup_manager'):
                    self._cleanup_manager.cleanup()
                
                # Enhanced event filters cleanup
                for filter_widget in getattr(self, '_event_filters', []):
                    try:
                        if filter_widget and hasattr(filter_widget, 'removeEventFilter'):
                            filter_widget.removeEventFilter(self)
                    except RuntimeError:  # Widget already deleted
                        pass
                self._event_filters.clear()
                
                # Resource manager cleanup
                if self._is_registered and hasattr(self, '_resource_manager'):
                    self._resource_manager.unregister_tile(self)
                    self._is_registered = False
                
                # Mark cleanup as done
                self._is_cleanup_done = True
                
                logger.debug(f"FileTileWidget cleanup completed (thread-safe)")
                
            except Exception as e:
                logger.error(f"Error during FileTileWidget cleanup: {e}")
                # Mark as done even if error occurred to prevent infinite loops
                self._is_cleanup_done = True
```

---

### PATCH 6: STRUCTURED LOGGING OPTIMIZATION

**Problem:** Za dużo debug logów w hot path i brak structured logging dla debugging kafli
**Rozwiązanie:** Conditional logging z tile_id i performance-aware logging

```python
import logging

class FileTileWidget(QWidget):
    def __init__(self, ...):
        # Existing code...
        # Tile ID dla structured logging
        self._tile_id = f"tile_{id(self)}"
        
        # Performance-aware logger
        self._logger = logging.getLogger(f"{__name__}.{self._tile_id}")
        self._debug_enabled = self._logger.isEnabledFor(logging.DEBUG)
        # Existing code...

    def _log_tile_event(self, event_type: str, details: dict = None):
        """Structured logging dla tile events."""
        if self._debug_enabled:
            log_data = {
                "tile_id": self._tile_id,
                "event_type": event_type,
                "file_pair": self.file_pair.get_base_name() if self.file_pair else None,
                **(details or {})
            }
            self._logger.debug(f"Tile event: {event_type}", extra=log_data)

    def update_data(self, file_pair: Optional[FilePair]):
        """Optimized logging w update_data."""
        # Existing logic...
        
        # ZAMIENIĆ: logging.debug(f"FileTileWidget: Dane zaktualizowane dla {file_pair.get_base_name()}")
        # NA conditional logging:
        if file_pair and self._debug_enabled:
            self._log_tile_event("data_updated", {
                "base_name": file_pair.get_base_name(),
                "has_preview": bool(file_pair.preview_path)
            })

    def set_thumbnail_size(self, new_size):
        """Performance-aware logging dla size changes."""
        # Existing logic...
        
        # ZAMIENIĆ: logging.debug(f"FileTileWidget: Rozmiar zmieniony z {old_size} na {size_tuple}")
        # NA conditional logging:
        if self._debug_enabled:
            self._log_tile_event("size_changed", {
                "old_size": old_size,
                "new_size": size_tuple,
                "thumbnail_reloaded": bool(self.file_pair and self.file_pair.preview_path)
            })
```

---

## ✅ CHECKLISTA WERYFIKACYJNA KAFLI (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI KAFLI DO WERYFIKACJI:**

- [ ] **Tworzenie kafli** - czy FileTileWidget tworzy się poprawnie z file_pair i bez
- [ ] **Renderowanie miniaturek** - czy thumbnails ładują się w kafli bez błędów
- [ ] **Metadata controls** - czy gwiazdki i color tags działają na kafli
- [ ] **Event handling kafli** - czy mouse clicks, drag&drop działają
- [ ] **Size changes kafli** - czy set_thumbnail_size() działa bez regresji
- [ ] **Batch operations** - czy tysiące kafli tworzy się bez problemów
- [ ] **Virtual scrolling integration** - czy kafle współpracują z GalleryManager
- [ ] **Thread safety kafli** - czy concurrent operations nie powodują crashes
- [ ] **Memory management kafli** - czy brak memory leaks przy cleanup
- [ ] **Performance kafli** - czy renderowanie tysięcy kafli nie degraduje wydajności

#### **ZALEŻNOŚCI KAFLI DO WERYFIKACJI:**

- [ ] **TileResourceManager** - czy registration/unregistration działa
- [ ] **TileEventBus** - czy komunikacja między komponentami kafli działa
- [ ] **Component integration** - czy thumbnail/metadata/interaction components działają
- [ ] **Legacy API compatibility** - czy stare metody działają z deprecation warnings
- [ ] **Signal/slot connections** - czy wszystkie sygnały kafli są emitowane
- [ ] **Event filters** - czy mouse events na labels działają poprawnie
- [ ] **Cleanup managers** - czy wszystkie managery cleanup działają
- [ ] **Performance monitoring** - czy integracja z performance monitor działa
- [ ] **Cache optimization** - czy integracja z cache optimizer działa

#### **TESTY WYDAJNOŚCIOWE KAFLI:**

- [ ] **1000+ kafli creation** - batch creation w <2s bez memory spikes
- [ ] **Virtual scrolling** - płynne przewijanie przez tysiące kafli
- [ ] **Memory usage** - <500MB dla galerii z 1000+ kafli
- [ ] **UI responsiveness** - <100ms response time dla tile interactions
- [ ] **Thread safety stress test** - concurrent tile operations bez race conditions

#### **KRYTERIA SUKCESU KAFLI:**

- [ ] **WSZYSTKIE CHECKLISTY KAFLI ZAZNACZONE** przed wdrożeniem w produkcji
- [ ] **BRAK FAILED TESTS** - wszystkie testy file_tile_widget* przechodzą
- [ ] **GALERIA PERFORMANCE** - tysiące kafli renderują się płynnie
- [ ] **MEMORY LEAK FREE** - długotrwałe użytkowanie bez wycieków pamięci kafli