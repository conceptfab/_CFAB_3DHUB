# PATCH-CODE DLA: GALLERY_MANAGER.PY

**Powiązany plik z analizą:** `../corrections/gallery_manager_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: INTELIGENTNY BATCH PROCESSING Z MONITORING PAMIĘCI

**Problem:** Batch size 100 może blokować UI przy dużych folderach, rzadkie processEvents
**Rozwiązanie:** Dynamiczny batch size z monitoring pamięci i częstsze processEvents

```python
# W force_create_all_tiles() około linii 752
# Kod do zmiany:
# batch_size = 100  # Zwiększono z 20 na 100 dla szybkości SBSAR
# total_batches = (len(all_items) + batch_size - 1) // batch_size

# Zmienić na:
import psutil
import gc

# Dynamiczny batch size na podstawie pamięci
def get_adaptive_batch_size(total_items: int) -> int:
    try:
        memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        if memory_mb > 800:  # High memory usage
            return min(20, total_items)
        elif memory_mb > 400:  # Medium memory usage
            return min(50, total_items)
        else:  # Low memory usage
            return min(100, total_items)  # Max 100 for performance
    except Exception:
        return min(50, total_items)  # Safe fallback

batch_size = get_adaptive_batch_size(len(all_items))
total_batches = (len(all_items) + batch_size - 1) // batch_size

# Zmiana częstości processEvents z co 5 batchów na każdy batch:
# Zmienić linię 812:
# if (batch_num + 1) % 5 == 0:  # Co 5 batchów zamiast każdy

# Na:
if (batch_num + 1) % 2 == 0:  # Co 2 batche dla lepszej responsywności
    try:
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Memory cleanup co 10 batchów
        if (batch_num + 1) % 10 == 0:
            gc.collect()
    except Exception:
        pass
```

---

### PATCH 2: NAPRAWA VIRTUAL SCROLLING Z BEZPIECZNĄ AKTYWACJĄ

**Problem:** Wirtualizacja całkowicie wyłączona, powoduje problem z dużymi folderami
**Rozwiązanie:** Warunkowe włączenie virtual scrolling dla folderów >1000 plików

```python
# W update_gallery_view() około linii 500
# Kod do zmiany:
# total_items = len(self.special_folders_list) + len(self.file_pairs_list)
# # USUNIĘTO SZTYWNY PRÓG 200 - teraz działa tak samo dla wszystkich ilości
# self.force_create_all_tiles()
# # Wyłącz wirtualizację po force_create_all_tiles
# self._virtualization_enabled = False
# return

# Zmienić na:
total_items = len(self.special_folders_list) + len(self.file_pairs_list)

# Inteligentne włączenie wirtualizacji dla dużych folderów
VIRTUALIZATION_THRESHOLD = 1000  # Próg dla bezpiecznej wirtualizacji

if total_items > VIRTUALIZATION_THRESHOLD:
    # Włącz wirtualizację dla dużych folderów
    self._virtualization_enabled = True
    logger.info(f"Włączono wirtualizację dla {total_items} elementów")
    self._update_visible_tiles()
else:
    # Dla małych folderów używaj force_create_all_tiles
    self._virtualization_enabled = False
    self.force_create_all_tiles()
```

---

### PATCH 3: USUNIĘCIE DUPLIKACJI ALGORYTMÓW GEOMETRII

**Problem:** Duplikacja logiki geometrii w _get_cached_geometry() i LayoutGeometry.get_layout_params()
**Rozwiązanie:** Delegacja do LayoutGeometry jako jedynego źródła prawdy

```python
# W _get_cached_geometry() około linii 395
# Kod do usunięcia (cała metoda):
# def _get_cached_geometry(self):
#     """Zwraca cache'owane obliczenia geometrii lub oblicza nowe."""
#     with self._geometry_cache_lock:
#         container_width = (
#             self.scroll_area.width() - self.scroll_area.verticalScrollBar().width()
#         )
#         # ... reszta kodu ...

# Zmienić na:
def _get_cached_geometry(self):
    """Deleguje do LayoutGeometry jako jedynego źródła prawdy."""
    return self._geometry.get_layout_params(self.current_thumbnail_size)

# Usunąć niepotrzebne właściwości cache:
# W __init__ usunąć:
# self._geometry_cache = {
#     "container_width": 0,
#     "cols": 0,
#     "tile_width_spacing": 0,
#     "tile_height_spacing": 0,
#     "last_thumbnail_size": 0,
# }
# self._geometry_cache_lock = threading.Lock()
```

---

### PATCH 4: IMPLEMENTACJA PROGRESSIVE LOADING

**Problem:** Metoda _start_progressive_loading() jest pusta
**Rozwiązanie:** Implementacja progressive loading dla bardzo dużych folderów

```python
# W _start_progressive_loading() około linii 391
# Kod do zmiany:
# def _start_progressive_loading(self):
#     """Start progressive loading - placeholder for now."""
#     pass

# Zmienić na:
def _start_progressive_loading(self):
    """Implementacja progressive loading dla dużych folderów."""
    with self._loading_lock:
        if not self._loading_chunks_queue or self._progressive_loading:
            return
            
        self._progressive_loading = True
        
        # Przetwarzaj chunks w tle
        if self._loading_chunks_queue:
            chunk = self._loading_chunks_queue.pop(0)
            self._process_chunk_async(chunk)

def _process_chunk_async(self, chunk):
    """Asynchroniczne przetwarzanie chunk'a kafli."""
    try:
        # Twórz kafelki w małych batchach
        for batch in chunk:
            self._create_tiles_batch_safe(batch)
            
        # Kontynuuj z następnym chunk'iem
        if self._loading_chunks_queue:
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(50, lambda: self._process_chunk_async(
                self._loading_chunks_queue.pop(0)
            ))
        else:
            self._progressive_loading = False
    except Exception as e:
        logger.error(f"Error in progressive loading: {e}")
        self._progressive_loading = False

def _create_tiles_batch_safe(self, items_batch):
    """Bezpieczne tworzenie batch'a kafli z monitoring pamięci."""
    try:
        memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        if memory_mb > 1000:  # 1GB limit
            gc.collect()
            return
            
        # Twórz kafelki...
        for item in items_batch:
            if isinstance(item, SpecialFolder):
                self.create_folder_widget(item)
            else:
                self.create_tile_widget_for_pair(item, self.tiles_container)
                
    except Exception as e:
        logger.error(f"Error creating tiles batch: {e}")
```

---

### PATCH 5: NAPRAWA VIRTUAL SCROLLING CLEANUP

**Problem:** _update_visible_tiles_fast() zawiera tylko return, nie działa cleanup
**Rozwiązanie:** Implementacja bezpiecznego cleanup kafli poza widokiem

```python
# W _update_visible_tiles_fast() około linii 359
# Kod do zmiany:
# def _update_visible_tiles_fast(self):
#     """Szybka aktualizacja widoczności kafli bez heavy operations."""
#     # Wyłączono żeby kafle nie znikały
#     return

# Zmienić na:
def _update_visible_tiles_fast(self):
    """Szybka aktualizacja widoczności kafli z bezpiecznym cleanup."""
    if not self._virtualization_enabled:
        return
        
    try:
        # Pobierz visible range
        total_items = len(self.file_pairs_list) + len(self.special_folders_list)
        if total_items == 0:
            return
            
        visible_start, visible_end, _ = self._geometry.get_visible_range(
            self.current_thumbnail_size, total_items
        )
        
        # Bezpieczne ukrywanie kafli poza widokiem (nie usuwanie!)
        with self._widgets_lock:
            for i, (path, widget) in enumerate(self.gallery_tile_widgets.items()):
                if widget and hasattr(widget, 'setVisible'):
                    should_be_visible = visible_start <= i < visible_end
                    if widget.isVisible() != should_be_visible:
                        widget.setVisible(should_be_visible)
                        
    except Exception as e:
        logger.warning(f"Error in virtual scrolling update: {e}")
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - tworzenie kafli działa dla wszystkich rozmiarów folderów
- [ ] **API kompatybilność** - wszystkie publiczne metody (update_gallery_view, force_create_all_tiles) działają
- [ ] **Responsywność UI** - brak blokowania UI podczas tworzenia kafli
- [ ] **Dynamic columns** - liczba kolumn adaptuje się do rozmiaru okna
- [ ] **Batch processing** - inteligentny batch size z monitoring pamięci
- [ ] **Virtual scrolling** - działa bezpiecznie dla folderów >1000 plików
- [ ] **Progressive loading** - implementowane dla bardzo dużych folderów
- [ ] **Thread safety** - wszystkie operacje są bezpieczne wielowątkowo
- [ ] **Memory management** - monitoring i cleanup pamięci działa poprawnie
- [ ] **Performance** - nie ma regresji wydajnościowej

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **TileManager integration** - batch processing działa z TileManager
- [ ] **FileTileWidget compatibility** - kafelki są tworzone poprawnie
- [ ] **MainWindow integration** - sygnały i callback'i działają
- [ ] **Resource Manager** - integracja z tile resource manager działa
- [ ] **Event handling** - scroll events i resize events działają
- [ ] **Signal/slot connections** - wszystkie połączenia Qt działają
- [ ] **Memory cleanup** - VirtualScrollingMemoryManager działa poprawnie
- [ ] **Cache management** - LayoutGeometry cache działa poprawnie

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test 10 plików** - szybkie tworzenie bez wirtualizacji
- [ ] **Test 100 plików** - normalne tworzenie bez wirtualizacji
- [ ] **Test 1000 plików** - przejście na wirtualizację
- [ ] **Test 5000+ plików** - progressive loading i memory management
- [ ] **Test resize window** - dynamiczne kolumny działają
- [ ] **Test scroll performance** - płynne przewijanie dużych folderów
- [ ] **Test memory usage** - nie przekracza 1GB dla 5000+ plików

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - wszystkie testy muszą przejść
- [ ] **PERFORMANCE BUDGET** - czas tworzenia kafli nie przekracza 30s dla 5000 plików
- [ ] **MEMORY BUDGET** - memory usage nie przekracza 1GB dla 5000+ plików
- [ ] **UI RESPONSIVENESS** - brak blokowania UI >1s podczas jakiejkolwiek operacji