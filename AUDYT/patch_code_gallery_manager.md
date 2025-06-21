# 🔧 FRAGMENTY KODU - POPRAWKI gallery_manager.py

## 1. BŁĘDY KRYTYCZNE

### 1.1 Poprawka nieprawidłowej wirtualizacji widgetów

**Lokalizacja:** `_update_visible_tiles()` linia 227

**Problematyczny kod:**
```python
if self.tiles_layout.itemAtPosition(row, col) != widget:
    self.tiles_layout.addWidget(widget, row, col)
```

**Poprawiony kod:**
```python
# Sprawdź czy pozycja jest pusta lub zawiera inny widget
current_item = self.tiles_layout.itemAtPosition(row, col)
if current_item is None or current_item.widget() != widget:
    # Jeśli pozycja zajęta przez inny widget, usuń go najpierw
    if current_item is not None:
        old_widget = current_item.widget()
        if old_widget != widget:
            self.tiles_layout.removeWidget(old_widget)
            old_widget.setVisible(False)
    self.tiles_layout.addWidget(widget, row, col)
```

### 1.2 Poprawka memory leaks w zarządzaniu widgetami

**Lokalizacja:** `_update_visible_tiles()` linie 234-246

**Problematyczny kod:**
```python
# Usuń niewidoczne kafelki
for path, widget in list(self.gallery_tile_widgets.items()):
    if path not in visible_items_set:
        widget.setVisible(False)
        self.tiles_layout.removeWidget(widget)
        widget.setParent(None)
        # Nie niszczymy widgetu, zostaje w cache (self.gallery_tile_widgets)
```

**Poprawiony kod:**
```python
# Dodaj lekkie zarządzanie cache - usuń najstarsze niewidoczne widgety
MAX_CACHED_WIDGETS = 200
currently_cached = len(self.gallery_tile_widgets)

# Usuń niewidoczne kafelki z layoutu
hidden_widgets = []
for path, widget in list(self.gallery_tile_widgets.items()):
    if path not in visible_items_set:
        widget.setVisible(False)
        self.tiles_layout.removeWidget(widget)
        widget.setParent(None)
        hidden_widgets.append((path, widget))

# Jeśli cache przekracza limit, usuń najstarsze widgety
if currently_cached > MAX_CACHED_WIDGETS:
    widgets_to_remove = currently_cached - MAX_CACHED_WIDGETS
    for i, (path, widget) in enumerate(hidden_widgets):
        if i >= widgets_to_remove:
            break
        self.gallery_tile_widgets.pop(path, None)
        widget.deleteLater()
        logging.debug(f"Usunięto z cache widget dla {path}")
```

### 1.3 Thread safety - dodanie synchronizacji

**Lokalizacja:** Początek klasy + metody modyfikujące słowniki

**Nowy kod na początku klasy:**
```python
import threading
from typing import Dict, List, Optional

class GalleryManager:
    """
    Klasa zarządzająca galerią kafelków z thread safety.
    """
    
    def __init__(self, ...):
        # ... existing code ...
        
        # Thread safety
        self._widgets_lock = threading.RLock()
        self._geometry_cache_lock = threading.Lock()
        
        # Cache dla obliczeń geometrii
        self._geometry_cache = {
            'container_width': 0,
            'cols': 0,
            'tile_width_spacing': 0,
            'tile_height_spacing': 0,
            'last_thumbnail_size': 0
        }
```

**Poprawione metody z synchronizacją:**
```python
def create_tile_widget_for_pair(self, file_pair: FilePair, parent_widget):
    """Tworzy pojedynczy kafelek dla pary plików - thread safe."""
    try:
        tile = FileTileWidget(file_pair, self._current_size_tuple, parent_widget)
        tile.setVisible(False)
        
        # Thread-safe dodanie do słownika
        with self._widgets_lock:
            self.gallery_tile_widgets[file_pair.get_archive_path()] = tile
        
        return tile
    except Exception as e:
        logging.error(f"Błąd tworzenia kafelka dla {file_pair.get_base_name()}: {e}")
        return None

def clear_gallery(self):
    """Czyści galerię kafelków - thread safe."""
    self.tiles_container.setUpdatesEnabled(False)
    try:
        # Thread-safe czyszczenie słowników
        with self._widgets_lock:
            # ... existing clearing logic ...
            self.gallery_tile_widgets.clear()
            self.special_folder_widgets.clear()
    finally:
        self.tiles_container.setUpdatesEnabled(True)
        self.tiles_container.update()
```

### 1.4 Optymalizacja aktualizacji rozmiaru miniatur

**Lokalizacja:** `update_thumbnail_size()` linie 285-291

**Problematyczny kod:**
```python
# Zaktualizuj rozmiar w kafelkach - dla WSZYSTKICH kafelków
for tile in self.gallery_tile_widgets.values():
    tile.set_thumbnail_size(self._current_size_tuple)

# Zaktualizuj rozmiar w widgetach folderów
for folder_widget in self.special_folder_widgets.values():
    folder_widget.set_thumbnail_size(self._current_size_tuple)
```

**Poprawiony kod:**
```python
# Zaktualizuj rozmiar tylko dla widocznych kafelków + cache nowego rozmiaru dla pozostałych
with self._widgets_lock:
    # Natychmiast zaktualizuj widoczne kafelki
    for tile in self.gallery_tile_widgets.values():
        if tile.isVisible():
            tile.set_thumbnail_size(self._current_size_tuple)
    
    for folder_widget in self.special_folder_widgets.values():
        if folder_widget.isVisible():
            folder_widget.set_thumbnail_size(self._current_size_tuple)

# Zaznacz, że niewidoczne kafelki potrzebują aktualizacji
self._pending_size_update = True

# Invalidate geometry cache
with self._geometry_cache_lock:
    self._geometry_cache['last_thumbnail_size'] = 0
```

## 2. OPTYMALIZACJE WYDAJNOŚCI

### 2.1 Cache obliczeń geometrii

**Nowa metoda do cache'owania:**
```python
def _get_cached_geometry(self):
    """Zwraca cache'owane obliczenia geometrii lub oblicza nowe."""
    with self._geometry_cache_lock:
        container_width = (
            self.scroll_area.width() - self.scroll_area.verticalScrollBar().width()
        )
        
        # Sprawdź czy cache jest aktualny
        if (self._geometry_cache['container_width'] == container_width and 
            self._geometry_cache['last_thumbnail_size'] == self.current_thumbnail_size):
            return self._geometry_cache
        
        # Oblicz nowe wartości
        tile_width_spacing = self.current_thumbnail_size + self.tiles_layout.spacing() + 10
        tile_height_spacing = self.current_thumbnail_size + self.tiles_layout.spacing() + 40
        cols = max(1, math.floor(container_width / tile_width_spacing))
        
        # Zaktualizuj cache
        self._geometry_cache.update({
            'container_width': container_width,
            'cols': cols,
            'tile_width_spacing': tile_width_spacing,
            'tile_height_spacing': tile_height_spacing,
            'last_thumbnail_size': self.current_thumbnail_size
        })
        
        return self._geometry_cache
```

**Użycie cache'u w metodach:**
```python
def _update_visible_tiles(self):
    """Używa cache'owanych obliczeń geometrii."""
    geometry = self._get_cached_geometry()
    cols = geometry['cols']
    tile_height_spacing = geometry['tile_height_spacing']
    
    # ... reszta logiki używa cache'owanych wartości ...
```

### 2.2 Lazy loading z aktualizacją rozmiaru

**Poprawiona metoda tworzenia widgetów:**
```python
def _ensure_widget_created(self, item, item_index):
    """Zapewnia że widget jest utworzony i ma poprawny rozmiar."""
    if isinstance(item, SpecialFolder):
        path = item.get_folder_path()
        widget = self.special_folder_widgets.get(path)
        if not widget:
            widget = self.create_folder_widget(item)
            if not widget:
                return None
        
        # Sprawdź czy widget ma aktualny rozmiar
        if hasattr(self, '_pending_size_update') and self._pending_size_update:
            widget.set_thumbnail_size(self._current_size_tuple)
            
    else:  # FilePair
        path = item.get_archive_path()
        widget = self.gallery_tile_widgets.get(path)
        if not widget:
            widget = self.create_tile_widget_for_pair(item, self.tiles_container)
            if not widget:
                return None
        
        # Sprawdź czy widget ma aktualny rozmiar
        if hasattr(self, '_pending_size_update') and self._pending_size_update:
            widget.set_thumbnail_size(self._current_size_tuple)
    
    return widget
```

## 3. REFAKTORYZACJA LOGOWANIA

### 3.1 Zamiana critical na debug z flagą diagnostyczną

**Na początku klasy:**
```python
class GalleryManager:
    """Klasa zarządzająca galerią kafelków."""
    
    # Flaga do włączania diagnostyki
    DIAGNOSTIC_LOGGING = os.getenv('GALLERY_DIAGNOSTIC', 'false').lower() == 'true'
    
    def _log_diagnostic(self, message: str):
        """Logowanie diagnostyczne - tylko gdy włączone."""
        if self.DIAGNOSTIC_LOGGING:
            logger.debug(f"GALLERY_DIAGNOSTIC: {message}")
```

**Poprawione wywołania logowania:**
```python
def create_folder_widget(self, special_folder: SpecialFolder):
    """Tworzy widget dla folderu specjalnego."""
    try:
        folder_name = special_folder.get_folder_name()
        folder_path = special_folder.get_folder_path()
        is_virtual = special_folder.is_virtual

        self._log_diagnostic(
            f"Próba utworzenia widgetu dla {folder_path} (wirtualny: {is_virtual})"
        )

        # ... reszta logiki ...
        
        logging.debug(f"Utworzono widget folderu: {folder_name}")
        return folder_widget
    except Exception as e:
        logging.error(f"Błąd tworzenia widgetu folderu: {e}", exc_info=True)
        return None
```

**Poprawiona metoda prepare_special_folders:**
```python
def prepare_special_folders(self, special_folders: List[SpecialFolder]):
    """Przygotowuje widgety dla folderów specjalnych."""
    self._log_diagnostic(f"Otrzymano {len(special_folders)} folderów")
    
    self.special_folders_list = special_folders

    # Wyczyść poprzednie widgety folderów
    with self._widgets_lock:
        for folder_path in list(self.special_folder_widgets.keys()):
            folder_widget = self.special_folder_widgets.pop(folder_path)
            self._log_diagnostic(f"Usuwam stary widget folderu: {folder_path}")
            folder_widget.setParent(None)
            folder_widget.deleteLater()
        self.special_folder_widgets.clear()

    # Utwórz nowe widgety dla folderów
    for special_folder in special_folders:
        widget = self.create_folder_widget(special_folder)
        self._log_diagnostic(
            f"Utworzono nowy widget: {special_folder.get_folder_path()} -> {widget is not None}"
        )

    logging.info(f"Przygotowano {len(self.special_folder_widgets)} widgetów folderów specjalnych.")
```

## 4. REFAKTORYZACJA STRUKTURALNA

### 4.1 Wydzielenie klasy pomocniczej do geometrii

**Nowa klasa LayoutGeometry:**
```python
class LayoutGeometry:
    """Klasa pomocnicza do obliczeń geometrii layoutu."""
    
    def __init__(self, scroll_area, tiles_layout):
        self.scroll_area = scroll_area
        self.tiles_layout = tiles_layout
        self._cache = {}
        self._cache_lock = threading.Lock()
    
    def get_layout_params(self, thumbnail_size):
        """Zwraca parametry layoutu dla danego rozmiaru miniatur."""
        with self._cache_lock:
            cache_key = (
                self.scroll_area.width(),
                self.scroll_area.height(), 
                thumbnail_size
            )
            
            if cache_key in self._cache:
                return self._cache[cache_key]
            
            container_width = (
                self.scroll_area.width() - self.scroll_area.verticalScrollBar().width()
            )
            tile_width_spacing = thumbnail_size + self.tiles_layout.spacing() + 10
            tile_height_spacing = thumbnail_size + self.tiles_layout.spacing() + 40
            cols = max(1, math.floor(container_width / tile_width_spacing))
            
            params = {
                'container_width': container_width,
                'cols': cols,
                'tile_width_spacing': tile_width_spacing,
                'tile_height_spacing': tile_height_spacing
            }
            
            self._cache[cache_key] = params
            return params
    
    def get_visible_range(self, thumbnail_size, total_items):
        """Oblicza zakres widocznych elementów."""
        params = self.get_layout_params(thumbnail_size)
        
        viewport_height = self.scroll_area.viewport().height()
        scroll_y = self.scroll_area.verticalScrollBar().value()
        
        buffer = viewport_height
        visible_start_y = max(0, scroll_y - buffer)
        visible_end_y = scroll_y + viewport_height + buffer
        
        first_visible_row = max(0, math.floor(visible_start_y / params['tile_height_spacing']))
        last_visible_row = math.ceil(visible_end_y / params['tile_height_spacing'])
        
        first_visible_item = first_visible_row * params['cols']
        last_visible_item = min((last_visible_row + 1) * params['cols'], total_items)
        
        return first_visible_item, last_visible_item, params
```

**Użycie w GalleryManager:**
```python
class GalleryManager:
    def __init__(self, ...):
        # ... existing code ...
        self._geometry = LayoutGeometry(self.scroll_area, self.tiles_layout)
    
    def _update_visible_tiles(self):
        """Uproszczona wersja używająca klasy pomocniczej."""
        total_items = len(self.special_folders_list) + len(self.file_pairs_list)
        if total_items == 0:
            return
            
        first_idx, last_idx, params = self._geometry.get_visible_range(
            self.current_thumbnail_size, total_items
        )
        
        all_items = self.special_folders_list + self.file_pairs_list
        visible_items_set = set()
        
        # Simplified widget management using helper class
        # ... simplified logic ...
```

---

*Wersja: 1.0*
*Data: 2024-06-21*
*Priorytet: ⚫⚫⚫⚫ KRYTYCZNY*