# 🚀 BEST PRACTICES - FILE TILE WIDGET

## 🎯 Przegląd

Ten przewodnik zawiera najlepsze praktyki dla używania nowej architektury `FileTileWidget`. Zawiera wzorce projektowe, optymalizacje i common pitfalls.

## 🏗️ ARCHITEKTURA

### 1. Component-Based Design

#### ✅ DO: Używaj komponentów dla separacji concerns

```python
# ✅ Dobrze: Dostęp przez komponenty
tile = FileTileWidget(file_pair)

# Thumbnail operations
tile._thumbnail_component.load_thumbnail(path, size)
tile._thumbnail_component.set_thumbnail_size((200, 200))

# Metadata operations
tile._metadata_component.set_stars(4)
tile._metadata_component.set_color_tag("#FF0000")

# Interaction operations
tile._interaction_component.set_drag_enabled(True)
```

#### ❌ DON'T: Bezpośredni dostęp do internal state

```python
# ❌ Źle: Bezpośredni dostęp
tile._thumbnail_pixmap = pixmap  # Internal state
tile._stars = 4  # Internal state
tile._drag_enabled = True  # Internal state
```

### 2. Event-Driven Communication

#### ✅ DO: Używaj event bus dla komunikacji

```python
# ✅ Dobrze: Event-driven communication
def on_thumbnail_loaded(path: str, pixmap: QPixmap):
    print(f"Thumbnail loaded: {path}")

tile.event_bus.subscribe(TileEvent.THUMBNAIL_LOADED, on_thumbnail_loaded)
tile.event_bus.subscribe(TileEvent.DATA_UPDATED, on_data_updated)
```

#### ❌ DON'T: Direct component coupling

```python
# ❌ Źle: Direct coupling między komponentami
tile._thumbnail_component._metadata_component.set_stars(4)  # Tight coupling
```

### 3. Resource Management

#### ✅ DO: Rejestruj tiles w resource manager

```python
# ✅ Dobrze: Centralne zarządzanie zasobami
resource_manager = TileResourceManager.get_instance()
resource_manager.register_tile(tile)

# Sprawdź memory usage
stats = resource_manager.get_memory_usage()
if stats.current_mb > 100:
    resource_manager.perform_cleanup()
```

#### ❌ DON'T: Ignoruj resource management

```python
# ❌ Źle: Brak resource management
tile = FileTileWidget(file_pair)  # Nie zarejestrowany w resource manager
# Memory leaks i performance issues
```

## ⚡ PERFORMANCE OPTIMIZATION

### 1. Configuration Optimization

#### ✅ DO: Używaj predefiniowanych konfiguracji

```python
# ✅ Dobrze: Predefiniowane konfiguracje
config = TileConfig.small()   # 150x150 - dla list view
config = TileConfig.large()   # 350x350 - dla detail view

tile = FileTileWidget(file_pair, config=config)
```

#### ✅ DO: Custom konfiguracja dla specjalnych przypadków

```python
# ✅ Dobrze: Custom konfiguracja
config = TileConfig(
    thumbnail_size=(400, 400),  # Duże miniaturki
    padding=24,                 # Większy padding
    font_size_range=(12, 24),   # Większe czcionki
    font_scale_factor=8         # Szybsze skalowanie
)

tile = FileTileWidget(file_pair, config=config)
```

#### ❌ DON'T: Hardcode magic numbers

```python
# ❌ Źle: Magic numbers
tile.set_thumbnail_size((200, 200))  # Hardcoded size
tile.setMinimumSize(150, 200)        # Hardcoded minimum
```

### 2. Async Operations

#### ✅ DO: Używaj async UI manager

```python
# ✅ Dobrze: Async operations
async_ui_manager = tile._async_ui_manager

# Debounced operations
async_ui_manager.debounce_manager.debounce(
    "thumbnail_update",
    tile.reload_thumbnail,
    delay_ms=100
)

# Batch updates
async_ui_manager.batch_updater.add_update(
    lambda: tile.set_thumbnail_size((200, 200))
)
async_ui_manager.batch_updater.flush()
```

#### ❌ DON'T: Synchroniczne operacje w main thread

```python
# ❌ Źle: Blocking operations
for tile in tiles:
    tile.reload_thumbnail()  # Blocking w main thread
    tile.set_thumbnail_size((200, 200))  # Blocking w main thread
```

### 3. Memory Management

#### ✅ DO: Monitoruj memory usage

```python
# ✅ Dobrze: Memory monitoring
resource_manager = TileResourceManager.get_instance()
stats = resource_manager.get_memory_usage()

if stats.current_mb > stats.limits.max_memory_mb * 0.8:
    logger.warning(f"High memory usage: {stats.current_mb:.2f} MB")
    resource_manager.perform_cleanup()
```

#### ✅ DO: Periodic cleanup

```python
# ✅ Dobrze: Scheduled cleanup
import threading
import time

def periodic_cleanup():
    while True:
        time.sleep(300)  # Co 5 minut
        resource_manager = TileResourceManager.get_instance()
        resource_manager.perform_cleanup()

cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
cleanup_thread.start()
```

#### ❌ DON'T: Ignoruj memory leaks

```python
# ❌ Źle: Brak memory management
for i in range(1000):
    tile = FileTileWidget(file_pair)
    # Brak cleanup - memory leaks
```

## 🔧 API USAGE

### 1. New API vs Legacy API

#### ✅ DO: Używaj nowego API

```python
# ✅ Dobrze: Nowe API
tile.set_file_pair(file_pair)      # Zamiast update_data()
tile.set_thumbnail_size((200, 200)) # Zamiast change_thumbnail_size()
tile.reload_thumbnail()             # Zamiast refresh_thumbnail()
tile.set_selected(True)             # Zamiast set_selection()
file_pair = tile.file_pair          # Zamiast get_file_data()
```

#### ⚠️ WARNING: Legacy API z deprecation warnings

```python
# ⚠️ Warning: Legacy API (deprecated)
tile.update_data(file_pair)         # DeprecationWarning
tile.change_thumbnail_size((200, 200)) # DeprecationWarning
tile.refresh_thumbnail()            # DeprecationWarning
tile.set_selection(True)            # DeprecationWarning
file_pair = tile.get_file_data()    # DeprecationWarning
```

### 2. Metadata Management

#### ✅ DO: Używaj metadata component

```python
# ✅ Dobrze: Metadata przez komponent
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

# Snapshot dla state persistence
snapshot = metadata.get_metadata_snapshot()
```

#### ❌ DON'T: Bezpośredni dostęp do metadata

```python
# ❌ Źle: Bezpośredni dostęp
tile._stars = 4  # Internal state
tile._color_tag = "#FF0000"  # Internal state
```

### 3. Event Handling

#### ✅ DO: Subskrybuj się na eventy

```python
# ✅ Dobrze: Event subscription
def on_thumbnail_loaded(path: str, pixmap: QPixmap):
    print(f"Thumbnail loaded: {path}")

def on_data_updated(file_pair: FilePair):
    print(f"Data updated: {file_pair.get_base_name()}")

def on_state_changed(new_state: str):
    print(f"State changed: {new_state}")

# Subskrypcja eventów
tile.event_bus.subscribe(TileEvent.THUMBNAIL_LOADED, on_thumbnail_loaded)
tile.event_bus.subscribe(TileEvent.DATA_UPDATED, on_data_updated)
tile.event_bus.subscribe(TileEvent.STATE_CHANGED, on_state_changed)
```

#### ✅ DO: Emituj custom events

```python
# ✅ Dobrze: Custom event emission
tile.event_bus.emit_event(TileEvent.USER_INTERACTION, "custom_action")
tile.event_bus.emit_event(TileEvent.STATE_CHANGED, "new_state")
```

#### ❌ DON'T: Ignoruj event system

```python
# ❌ Źle: Brak event handling
tile = FileTileWidget(file_pair)
# Brak event subscription - brak reakcji na zmiany
```

## 🎨 UI/UX PATTERNS

### 1. Responsive Design

#### ✅ DO: Używaj responsive konfiguracji

```python
# ✅ Dobrze: Responsive configuration
def create_responsive_tile(file_pair, container_width):
    if container_width < 300:
        config = TileConfig.small()
    elif container_width < 600:
        config = TileConfig()  # Default
    else:
        config = TileConfig.large()

    return FileTileWidget(file_pair, config=config)
```

#### ✅ DO: Debounce UI updates

```python
# ✅ Dobrze: Debounced UI updates
async_ui_manager = tile._async_ui_manager

# Debounce resize operations
async_ui_manager.debounce_manager.debounce(
    "resize",
    lambda: tile.set_thumbnail_size(new_size),
    delay_ms=150
)
```

#### ❌ DON'T: Rapid UI updates

```python
# ❌ Źle: Rapid updates bez debouncing
for size in [(100, 100), (150, 150), (200, 200)]:
    tile.set_thumbnail_size(size)  # Każdy update powoduje reload
```

### 2. Loading States

#### ✅ DO: Implementuj loading states

```python
# ✅ Dobrze: Loading states
def on_thumbnail_loading_started():
    tile.setEnabled(False)
    tile.setToolTip("Loading thumbnail...")

def on_thumbnail_loaded(path: str, pixmap: QPixmap):
    tile.setEnabled(True)
    tile.setToolTip("")

# Event subscription
tile.event_bus.subscribe(TileEvent.THUMBNAIL_LOADING_STARTED, on_thumbnail_loading_started)
tile.event_bus.subscribe(TileEvent.THUMBNAIL_LOADED, on_thumbnail_loaded)
```

#### ❌ DON'T: Ignoruj loading states

```python
# ❌ Źle: Brak loading feedback
tile.reload_thumbnail()  # Użytkownik nie wie że trwa ładowanie
```

### 3. Error Handling

#### ✅ DO: Obsługuj błędy gracefully

```python
# ✅ Dobrze: Error handling
def on_thumbnail_error(path: str, error: str):
    logger.error(f"Thumbnail error for {path}: {error}")
    tile.setToolTip(f"Error loading thumbnail: {error}")
    # Show fallback image or placeholder

tile.event_bus.subscribe(TileEvent.THUMBNAIL_ERROR, on_thumbnail_error)
```

#### ❌ DON'T: Ignoruj błędy

```python
# ❌ Źle: Brak error handling
tile.reload_thumbnail()  # Błędy nie są obsługiwane
```

## 🔍 DEBUGGING

### 1. Performance Monitoring

#### ✅ DO: Monitoruj performance

```python
# ✅ Dobrze: Performance monitoring
performance_monitor = tile._performance_monitor

# Sprawdź metryki
metrics = performance_monitor.get_metrics()
print(f"Render time: {metrics.render_time_ms:.2f} ms")
print(f"Memory usage: {metrics.memory_usage_mb:.2f} MB")

# Cache statistics
cache_optimizer = tile._cache_optimizer
cache_stats = cache_optimizer.get_cache_stats()
print(f"Cache hit rate: {cache_stats.hit_rate:.1%}")
```

#### ✅ DO: Log performance issues

```python
# ✅ Dobrze: Performance logging
def log_performance_metrics():
    resource_manager = TileResourceManager.get_instance()
    stats = resource_manager.get_memory_usage()

    if stats.current_mb > 100:
        logger.warning(f"High memory usage: {stats.current_mb:.2f} MB")

    performance_monitor = tile._performance_monitor
    metrics = performance_monitor.get_metrics()

    if metrics.render_time_ms > 50:
        logger.warning(f"Slow render time: {metrics.render_time_ms:.2f} ms")
```

### 2. Debug Mode

#### ✅ DO: Włącz debug mode dla development

```python
# ✅ Dobrze: Debug mode
import logging

# Włącz debug logging
logging.getLogger('src.ui.widgets').setLevel(logging.DEBUG)

# Debug event bus
tile.event_bus.enable_debug_logging()

# Debug resource manager
resource_manager = TileResourceManager.get_instance()
resource_manager.enable_debug_logging()
```

#### ❌ DON'T: Debug mode w production

```python
# ❌ Źle: Debug mode w production
logging.getLogger('src.ui.widgets').setLevel(logging.DEBUG)  # Performance impact
```

## 🧪 TESTING

### 1. Unit Testing

#### ✅ DO: Testuj komponenty osobno

```python
# ✅ Dobrze: Component testing
def test_thumbnail_component():
    component = ThumbnailComponent()
    component.load_thumbnail("test.jpg", (200, 200))
    assert component.is_loading == True

def test_metadata_component():
    component = TileMetadataComponent()
    component.set_stars(4)
    assert component.stars == 4

def test_interaction_component():
    component = TileInteractionComponent()
    component.set_drag_enabled(True)
    assert component._drag_enabled == True
```

#### ✅ DO: Testuj integration

```python
# ✅ Dobrze: Integration testing
def test_tile_integration():
    tile = FileTileWidget(file_pair)

    # Test component integration
    assert tile._thumbnail_component is not None
    assert tile._metadata_component is not None
    assert tile._interaction_component is not None
    assert tile.event_bus is not None

    # Test event bus
    events_received = []
    def on_event(data):
        events_received.append(data)

    tile.event_bus.subscribe(TileEvent.DATA_UPDATED, on_event)
    tile.event_bus.emit_event(TileEvent.DATA_UPDATED, "test")

    assert len(events_received) == 1
    assert events_received[0] == "test"
```

### 2. Performance Testing

#### ✅ DO: Testuj memory usage

```python
# ✅ Dobrze: Memory testing
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

#### ✅ DO: Testuj performance

```python
# ✅ Dobrze: Performance testing
import time

def test_thumbnail_loading_performance():
    tile = FileTileWidget(file_pair)

    start_time = time.time()
    tile.reload_thumbnail()
    load_time = time.time() - start_time

    assert load_time < 0.5  # <500ms
```

## 🚀 PRODUCTION DEPLOYMENT

### 1. Gradual Rollout

#### ✅ DO: Używaj feature flags

```python
# ✅ Dobrze: Feature flag deployment
def create_tile_widget(file_pair, config=None):
    if config.get('use_refactored_tile_widget', False):
        return FileTileWidget(file_pair, config=config)
    else:
        return LegacyFileTileWidget(file_pair)
```

#### ✅ DO: Monitoruj deployment

```python
# ✅ Dobrze: Deployment monitoring
def monitor_deployment():
    resource_manager = TileResourceManager.get_instance()
    stats = resource_manager.get_memory_usage()

    # Alert thresholds
    if stats.current_mb > 1000:
        send_alert("High memory usage in new tile widget")

    if stats.current_tiles > 500:
        send_alert("High tile count in new tile widget")
```

### 2. Rollback Strategy

#### ✅ DO: Przygotuj rollback plan

```python
# ✅ Dobrze: Rollback strategy
def rollback_to_legacy():
    config['use_refactored_tile_widget'] = False
    logger.info("Rolled back to legacy tile widget")

    # Cleanup new architecture
    resource_manager = TileResourceManager.get_instance()
    resource_manager.perform_cleanup()
```

## 📚 COMMON PATTERNS

### 1. Gallery Implementation

#### ✅ DO: Implementuj gallery z resource management

```python
# ✅ Dobrze: Gallery implementation
class GalleryWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.tiles = []
        self.resource_manager = TileResourceManager.get_instance()

    def add_tile(self, file_pair):
        tile = FileTileWidget(file_pair)
        self.tiles.append(tile)
        self.resource_manager.register_tile(tile)
        self.layout().addWidget(tile)

    def clear_gallery(self):
        for tile in self.tiles:
            self.layout().removeWidget(tile)
            tile.deleteLater()
        self.tiles.clear()
        self.resource_manager.perform_cleanup()
```

### 2. Batch Operations

#### ✅ DO: Używaj batch operations

```python
# ✅ Dobrze: Batch operations
def update_multiple_tiles(tiles, new_size):
    async_ui_manager = tiles[0]._async_ui_manager

    for tile in tiles:
        async_ui_manager.batch_updater.add_update(
            lambda t=tile: t.set_thumbnail_size(new_size)
        )

    async_ui_manager.batch_updater.flush()
```

### 3. Custom Tile Widgets

#### ✅ DO: Rozszerzaj przez inheritance

```python
# ✅ Dobrze: Custom tile widget
class CustomTileWidget(FileTileWidget):
    def __init__(self, file_pair, custom_config=None):
        # Custom configuration
        if custom_config:
            config = TileConfig(**custom_config)
        else:
            config = TileConfig.large()

        super().__init__(file_pair, config=config)
        self.setup_custom_behavior()

    def setup_custom_behavior(self):
        # Custom event handling
        self.event_bus.subscribe(TileEvent.DATA_UPDATED, self.on_custom_update)

    def on_custom_update(self, file_pair):
        # Custom logic
        print(f"Custom update for: {file_pair.get_base_name()}")
```

## ⚠️ COMMON PITFALLS

### 1. Memory Leaks

#### ❌ DON'T: Zapominaj o cleanup

```python
# ❌ Źle: Memory leaks
tiles = []
for i in range(1000):
    tile = FileTileWidget(file_pair)
    tiles.append(tile)
    # Brak cleanup - memory leaks
```

#### ✅ DO: Proper cleanup

```python
# ✅ Dobrze: Proper cleanup
tiles = []
resource_manager = TileResourceManager.get_instance()

for i in range(1000):
    tile = FileTileWidget(file_pair)
    tiles.append(tile)
    resource_manager.register_tile(tile)

# Cleanup
for tile in tiles:
    tile.deleteLater()
tiles.clear()
resource_manager.perform_cleanup()
```

### 2. Performance Issues

#### ❌ DON'T: Synchroniczne operacje

```python
# ❌ Źle: Blocking operations
for tile in tiles:
    tile.reload_thumbnail()  # Blocking w main thread
```

#### ✅ DO: Async operations

```python
# ✅ Dobrze: Async operations
async_ui_manager = tiles[0]._async_ui_manager

for tile in tiles:
    async_ui_manager.batch_updater.add_update(
        lambda t=tile: t.reload_thumbnail()
    )

async_ui_manager.batch_updater.flush()
```

### 3. Event Handling

#### ❌ DON'T: Ignoruj event system

```python
# ❌ Źle: Brak event handling
tile = FileTileWidget(file_pair)
# Brak event subscription - brak reakcji na zmiany
```

#### ✅ DO: Proper event handling

```python
# ✅ Dobrze: Event handling
def on_thumbnail_loaded(path: str, pixmap: QPixmap):
    print(f"Thumbnail loaded: {path}")

tile.event_bus.subscribe(TileEvent.THUMBNAIL_LOADED, on_thumbnail_loaded)
```

## 📈 OPTIMIZATION TIPS

### 1. Configuration Tuning

```python
# Optimal configuration dla różnych use cases
configs = {
    'list_view': TileConfig.small(),      # 150x150
    'grid_view': TileConfig(),            # 250x250 (default)
    'detail_view': TileConfig.large(),    # 350x350
    'custom': TileConfig(
        thumbnail_size=(400, 400),
        padding=24,
        font_size_range=(12, 24)
    )
}
```

### 2. Resource Management

```python
# Optimal resource limits
limits = ResourceLimits(
    max_tiles=1000,        # Maksymalna liczba kafelków
    max_memory_mb=2000,    # Maksymalne użycie pamięci
    max_concurrent_workers=10  # Maksymalna liczba workerów
)
```

### 3. Performance Monitoring

```python
# Performance monitoring setup
def setup_performance_monitoring():
    resource_manager = TileResourceManager.get_instance()
    resource_manager.enable_monitoring()

    # Alert thresholds
    resource_manager.set_alert_thresholds(
        memory_mb=1000,
        tile_count=500,
        response_time_ms=100
    )
```

---

**Wersja przewodnika:** 1.0  
**Data aktualizacji:** 2025-01-27  
**Kompatybilność:** FileTileWidget v2.0+
