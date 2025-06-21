# 🔄 MIGRATION GUIDE - FILE TILE WIDGET

## 🎯 Przegląd

Ten przewodnik pomoże Ci migrować z legacy `FileTileWidget` API na nową architekturę komponentową. Wszystkie zmiany zachowują backward compatibility.

## 📋 Checklista Migracji

### ✅ Etap 1: Przygotowanie
- [ ] Backup istniejącego kodu
- [ ] Zidentyfikuj wszystkie użycia FileTileWidget
- [ ] Sprawdź deprecated warnings w logach

### ✅ Etap 2: Podstawowa Migracja
- [ ] Zastąp deprecated metody
- [ ] Zaktualizuj importy
- [ ] Przetestuj funkcjonalność

### ✅ Etap 3: Optymalizacja
- [ ] Wykorzystaj nowe komponenty
- [ ] Dodaj event handling
- [ ] Zoptymalizuj performance

### ✅ Etap 4: Testowanie
- [ ] Uruchom testy
- [ ] Sprawdź memory usage
- [ ] Weryfikuj UI responsiveness

## 🔧 SZCZEGÓŁOWA MIGRACJA

### 1. Importy

**Przed:**
```python
from src.ui.widgets.file_tile_widget import FileTileWidget
```

**Po:**
```python
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.ui.widgets.tile_config import TileConfig
from src.ui.widgets.tile_event_bus import TileEvent, TileEventBus
from src.ui.widgets.tile_resource_manager import TileResourceManager
```

### 2. Tworzenie Widgetu

**Przed:**
```python
# Podstawowe tworzenie
tile = FileTileWidget(file_pair)

# Z custom rozmiarem
tile = FileTileWidget(file_pair)
tile.change_thumbnail_size((300, 300))
```

**Po:**
```python
# Podstawowe tworzenie (bez zmian)
tile = FileTileWidget(file_pair)

# Z konfiguracją (zalecane)
config = TileConfig(thumbnail_size=(300, 300))
tile = FileTileWidget(file_pair, config=config)

# Lub predefiniowane konfiguracje
config = TileConfig.small()   # 150x150
config = TileConfig.large()   # 350x350
tile = FileTileWidget(file_pair, config=config)
```

### 3. Zarządzanie Danymi

**Przed:**
```python
# Aktualizacja danych
tile.update_data(new_file_pair)

# Pobieranie danych
file_pair = tile.get_file_data()
```

**Po:**
```python
# Aktualizacja danych (nowe API)
tile.set_file_pair(new_file_pair)

# Pobieranie danych (property)
file_pair = tile.file_pair

# Legacy API nadal działa (z deprecation warning)
tile.update_data(new_file_pair)  # ⚠️ DEPRECATED
file_pair = tile.get_file_data()  # ⚠️ DEPRECATED
```

### 4. Zarządzanie Miniaturkami

**Przed:**
```python
# Zmiana rozmiaru
tile.change_thumbnail_size((250, 250))

# Przeładowanie
tile.refresh_thumbnail()
```

**Po:**
```python
# Zmiana rozmiaru (nowe API)
tile.set_thumbnail_size((250, 250))

# Przeładowanie (nowe API)
tile.reload_thumbnail()

# Legacy API nadal działa
tile.change_thumbnail_size((250, 250))  # ⚠️ DEPRECATED
tile.refresh_thumbnail()  # ⚠️ DEPRECATED
```

### 5. Zarządzanie Selekcją

**Przed:**
```python
# Ustawienie selekcji
tile.set_selection(True)

# Sprawdzenie selekcji
is_selected = tile.is_selected()
```

**Po:**
```python
# Ustawienie selekcji (nowe API)
tile.set_selected(True)

# Sprawdzenie selekcji (property)
is_selected = tile.is_selected

# Legacy API nadal działa
tile.set_selection(True)  # ⚠️ DEPRECATED
```

### 6. Metadane (Nowa Funkcjonalność)

**Przed:**
```python
# Brak bezpośredniego API dla metadanych
# Metadane były zarządzane przez zewnętrzne komponenty
```

**Po:**
```python
# Bezpośredni dostęp do metadanych
metadata = tile._metadata_component

# Gwiazdki (0-5)
metadata.set_stars(4)
stars = metadata.stars

# Tagi kolorów (hex string)
metadata.set_color_tag("#FF0000")
color = metadata.color_tag

# Selekcja
metadata.set_selected(True)
is_selected = metadata.is_selected

# Snapshot metadanych
snapshot = metadata.get_metadata_snapshot()
```

### 7. Event Handling (Nowa Funkcjonalność)

**Przed:**
```python
# Brak centralnego event systemu
# Eventy były obsługiwane przez sygnały Qt
tile.thumbnail_clicked.connect(callback)
```

**Po:**
```python
# Event bus dla komunikacji między komponentami
event_bus = tile.event_bus

# Subskrypcja eventów
def on_thumbnail_loaded(path: str, pixmap: QPixmap):
    print(f"Thumbnail loaded: {path}")

event_bus.subscribe(TileEvent.THUMBNAIL_LOADED, on_thumbnail_loaded)
event_bus.subscribe(TileEvent.DATA_UPDATED, on_data_updated)
event_bus.subscribe(TileEvent.STATE_CHANGED, on_state_changed)

# Emisja eventów
event_bus.emit_event(TileEvent.USER_INTERACTION, "click")

# Legacy sygnały Qt nadal działają
tile.thumbnail_clicked.connect(callback)
```

### 8. Resource Management (Nowa Funkcjonalność)

**Przed:**
```python
# Brak centralnego zarządzania zasobami
# Każdy widget zarządzał swoimi zasobami
```

**Po:**
```python
# Centralne zarządzanie zasobami
resource_manager = TileResourceManager.get_instance()

# Rejestracja kafelka
resource_manager.register_tile(tile)

# Sprawdzenie użycia pamięci
stats = resource_manager.get_memory_usage()
print(f"Memory: {stats.current_mb:.2f} MB")

# Automatyczny cleanup
resource_manager.perform_cleanup()

# Custom limity
from src.ui.widgets.tile_resource_manager import ResourceLimits
limits = ResourceLimits(max_tiles=500, max_memory_mb=200)
manager = TileResourceManager.get_instance(limits)
```

## 🚀 ZAAWANSOWANE FUNKCJONALNOŚCI

### 1. Asynchroniczne Operacje UI

```python
# Dostęp do async UI manager
async_ui_manager = tile._async_ui_manager

# Debouncing operacji
def update_ui():
    tile.reload_thumbnail()

async_ui_manager.debounce_manager.debounce(
    "thumbnail_update", 
    update_ui, 
    delay_ms=100
)

# Batch updates
def update_function():
    tile.set_thumbnail_size((200, 200))

async_ui_manager.batch_updater.add_update(update_function)
async_ui_manager.batch_updater.flush()
```

### 2. Performance Monitoring

```python
# Dostęp do performance monitor
performance_monitor = tile._performance_monitor

# Sprawdzenie metryk
metrics = performance_monitor.get_metrics()
print(f"Render time: {metrics.render_time_ms:.2f} ms")
print(f"Memory usage: {metrics.memory_usage_mb:.2f} MB")

# Cache optimization
cache_optimizer = tile._cache_optimizer
cache_stats = cache_optimizer.get_cache_stats()
print(f"Cache hit rate: {cache_stats.hit_rate:.1%}")
```

### 3. Custom Konfiguracja

```python
# Pełna custom konfiguracja
config = TileConfig(
    thumbnail_size=(400, 400),
    padding=24,
    filename_height=80,
    metadata_height=30,
    font_size_range=(10, 22),
    font_scale_factor=10
)

tile = FileTileWidget(file_pair, config=config)
```

## ⚠️ DEPRECATED API - DO USUNIĘCIA

### Metody które zostaną usunięte w przyszłych wersjach:

```python
# ⚠️ DEPRECATED - zastąp set_file_pair()
widget.update_data(file_pair)

# ⚠️ DEPRECATED - zastąp file_pair property
widget.get_file_data()

# ⚠️ DEPRECATED - zastąp set_thumbnail_size()
widget.change_thumbnail_size(size)

# ⚠️ DEPRECATED - zastąp reload_thumbnail()
widget.refresh_thumbnail()

# ⚠️ DEPRECATED - zastąp set_selected()
widget.set_selection(selected)
```

### Deprecation Warnings

Wszystkie deprecated metody pokazują warning przy pierwszym użyciu:

```
DeprecationWarning: FileTileWidget.update_data() is deprecated. Use set_file_pair() instead.
```

## 📊 PRZYKŁADY MIGRACJI

### Przykład 1: Podstawowy Widget

**Przed:**
```python
from src.ui.widgets.file_tile_widget import FileTileWidget

# Tworzenie
tile = FileTileWidget(file_pair)

# Aktualizacja danych
tile.update_data(new_file_pair)

# Zmiana rozmiaru
tile.change_thumbnail_size((250, 250))

# Selekcja
tile.set_selection(True)

# Event handling
tile.thumbnail_clicked.connect(on_click)
```

**Po:**
```python
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.ui.widgets.tile_config import TileConfig

# Tworzenie z konfiguracją
config = TileConfig(thumbnail_size=(250, 250))
tile = FileTileWidget(file_pair, config=config)

# Aktualizacja danych
tile.set_file_pair(new_file_pair)

# Zmiana rozmiaru
tile.set_thumbnail_size((250, 250))

# Selekcja
tile.set_selected(True)

# Event handling (legacy + nowe)
tile.thumbnail_clicked.connect(on_click)  # Legacy Qt signals
tile.event_bus.subscribe(TileEvent.THUMBNAIL_LOADED, on_loaded)  # Nowe events
```

### Przykład 2: Zaawansowany Widget

**Przed:**
```python
from src.ui.widgets.file_tile_widget import FileTileWidget

class CustomTileWidget(FileTileWidget):
    def __init__(self, file_pair):
        super().__init__(file_pair)
        self.setup_custom_behavior()
    
    def setup_custom_behavior(self):
        self.change_thumbnail_size((300, 300))
        self.set_selection(False)
    
    def update_tile_data(self, new_data):
        self.update_data(new_data)
        self.refresh_thumbnail()
```

**Po:**
```python
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.ui.widgets.tile_config import TileConfig
from src.ui.widgets.tile_event_bus import TileEvent

class CustomTileWidget(FileTileWidget):
    def __init__(self, file_pair):
        # Custom konfiguracja
        config = TileConfig(thumbnail_size=(300, 300))
        super().__init__(file_pair, config=config)
        
        self.setup_custom_behavior()
    
    def setup_custom_behavior(self):
        # Metadane przez komponent
        self._metadata_component.set_selected(False)
        
        # Event subscription
        self.event_bus.subscribe(TileEvent.DATA_UPDATED, self.on_data_updated)
    
    def update_tile_data(self, new_data):
        # Nowe API
        self.set_file_pair(new_data)
        self.reload_thumbnail()
    
    def on_data_updated(self, file_pair):
        # Custom logic po aktualizacji danych
        print(f"Data updated: {file_pair.get_base_name()}")
```

### Przykład 3: Batch Operations

**Przed:**
```python
# Brak batch operations
for file_pair in file_pairs:
    tile = FileTileWidget(file_pair)
    tile.change_thumbnail_size((200, 200))
    tile.set_selection(False)
```

**Po:**
```python
from src.ui.widgets.tile_resource_manager import TileResourceManager

# Resource management
resource_manager = TileResourceManager.get_instance()

# Batch operations
for file_pair in file_pairs:
    tile = FileTileWidget(file_pair)
    
    # Rejestracja w resource manager
    resource_manager.register_tile(tile)
    
    # Batch updates przez async UI manager
    async_ui_manager = tile._async_ui_manager
    async_ui_manager.batch_updater.add_update(
        lambda t=tile: t.set_thumbnail_size((200, 200))
    )
    async_ui_manager.batch_updater.add_update(
        lambda t=tile: t.set_selected(False)
    )

# Flush wszystkich updates
async_ui_manager.batch_updater.flush()
```

## 🔧 TROUBLESHOOTING

### Problem: Deprecation warnings w logach

**Objawy:**
```
DeprecationWarning: FileTileWidget.update_data() is deprecated
```

**Rozwiązanie:**
```python
# Przed
tile.update_data(file_pair)

# Po
tile.set_file_pair(file_pair)
```

### Problem: Memory leaks

**Objawy:** Rosnące użycie pamięci przy wielu kafelkach

**Rozwiązanie:**
```python
# Dodaj resource management
resource_manager = TileResourceManager.get_instance()
resource_manager.register_tile(tile)

# Sprawdź memory usage
stats = resource_manager.get_memory_usage()
if stats.current_mb > 100:  # 100MB limit
    resource_manager.perform_cleanup()
```

### Problem: Slow thumbnail loading

**Objawy:** Wolne ładowanie miniaturek

**Rozwiązanie:**
```python
# Użyj async UI manager
async_ui_manager = tile._async_ui_manager

# Debounce thumbnail updates
async_ui_manager.debounce_manager.debounce(
    "thumbnail_load", 
    tile.reload_thumbnail, 
    delay_ms=200
)
```

### Problem: Event not firing

**Objawy:** Callback nie jest wywoływany

**Rozwiązanie:**
```python
# Sprawdź czy callback jest zarejestrowany
def on_event(data):
    print(f"Event received: {data}")

# Subskrybuj się na event
tile.event_bus.subscribe(TileEvent.DATA_UPDATED, on_event)

# Sprawdź czy event jest emitowany
tile.event_bus.emit_event(TileEvent.DATA_UPDATED, "test_data")
```

## 📈 PERFORMANCE OPTIMIZATION

### 1. Memory Optimization

```python
# Użyj predefiniowanych konfiguracji
config = TileConfig.small()  # Mniejsze miniaturki = mniej pamięci

# Resource management
resource_manager = TileResourceManager.get_instance()
resource_manager.register_tile(tile)

# Periodic cleanup
import threading
import time

def periodic_cleanup():
    while True:
        time.sleep(300)  # Co 5 minut
        resource_manager.perform_cleanup()

cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()
```

### 2. UI Responsiveness

```python
# Async UI operations
async_ui_manager = tile._async_ui_manager

# Batch updates dla lepszej wydajności
def update_multiple_tiles(tiles):
    for tile in tiles:
        async_ui_manager.batch_updater.add_update(
            lambda t=tile: t.set_thumbnail_size((200, 200))
        )
    async_ui_manager.batch_updater.flush()
```

### 3. Cache Optimization

```python
# Dostęp do cache optimizer
cache_optimizer = tile._cache_optimizer

# Sprawdź cache performance
stats = cache_optimizer.get_cache_stats()
if stats.hit_rate < 0.8:  # <80% hit rate
    cache_optimizer.optimize_cache()
```

## ✅ TESTING MIGRACJI

### 1. Unit Tests

```python
import pytest
from src.ui.widgets.file_tile_widget import FileTileWidget

def test_new_api():
    tile = FileTileWidget(file_pair)
    
    # Test nowego API
    tile.set_file_pair(new_file_pair)
    assert tile.file_pair == new_file_pair
    
    tile.set_thumbnail_size((200, 200))
    tile.reload_thumbnail()
    
    tile.set_selected(True)
    assert tile.is_selected == True

def test_legacy_api_compatibility():
    tile = FileTileWidget(file_pair)
    
    # Legacy API nadal działa
    tile.update_data(new_file_pair)  # ⚠️ DEPRECATED
    tile.change_thumbnail_size((200, 200))  # ⚠️ DEPRECATED
    tile.set_selection(True)  # ⚠️ DEPRECATED
```

### 2. Integration Tests

```python
def test_component_integration():
    tile = FileTileWidget(file_pair)
    
    # Test komponentów
    assert tile._thumbnail_component is not None
    assert tile._metadata_component is not None
    assert tile._interaction_component is not None
    assert tile.event_bus is not None

def test_event_bus():
    tile = FileTileWidget(file_pair)
    
    events_received = []
    
    def on_event(data):
        events_received.append(data)
    
    tile.event_bus.subscribe(TileEvent.DATA_UPDATED, on_event)
    tile.event_bus.emit_event(TileEvent.DATA_UPDATED, "test")
    
    assert len(events_received) == 1
    assert events_received[0] == "test"
```

### 3. Performance Tests

```python
import time
import psutil

def test_memory_usage():
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    tiles = []
    for i in range(100):
        tile = FileTileWidget(file_pair)
        tiles.append(tile)
    
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_per_tile = (final_memory - initial_memory) / 100
    
    assert memory_per_tile < 10  # <10MB per tile
```

## 🎯 PODSUMOWANIE

### Co zostało zmienione:

1. **API Methods**: `update_data()` → `set_file_pair()`, `change_thumbnail_size()` → `set_thumbnail_size()`
2. **Properties**: `get_file_data()` → `file_pair` property, `is_selected()` → `is_selected` property
3. **Architecture**: Monolityczna klasa → Component-based architecture
4. **Event System**: Qt signals → Event bus + Qt signals
5. **Resource Management**: Manual → Automatic przez TileResourceManager

### Co zostało zachowane:

1. **Backward Compatibility**: Wszystkie legacy API nadal działa
2. **Qt Signals**: Wszystkie istniejące sygnały Qt działają
3. **External API**: Integracja z GalleryManager i innymi komponentami
4. **Functionality**: Wszystkie funkcjonalności zachowane

### Co zostało dodane:

1. **Component Architecture**: Separacja concerns na komponenty
2. **Event Bus**: Centralna komunikacja między komponentami
3. **Resource Management**: Automatyczne zarządzanie zasobami
4. **Performance Optimization**: Async operations, caching, batching
5. **Configuration System**: Flexible configuration przez TileConfig

---

**Wersja przewodnika:** 1.0  
**Data aktualizacji:** 2025-01-27  
**Kompatybilność:** FileTileWidget v2.0+ 