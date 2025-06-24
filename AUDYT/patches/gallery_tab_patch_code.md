# PATCH-CODE DLA: GALLERY_TAB.PY

**Powiązany plik z analizą:** `../corrections/gallery_tab_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: THREAD-SAFE FOLDER VALIDATION

**Problem:** Synchroniczne operacje I/O w `_on_favorite_folder_clicked()` blokują UI thread
**Rozwiązanie:** Implementacja asynchronicznej walidacji folderów z worker thread

```python
# Dodaj na początku pliku po importach
from PyQt6.QtCore import QThread, QObject, pyqtSignal
import concurrent.futures
import weakref

class FolderValidationWorker(QObject):
    """Worker do asynchronicznej walidacji folderów."""
    
    validation_finished = pyqtSignal(str, bool, str)  # path, is_valid, error_msg
    
    def __init__(self):
        super().__init__()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="FolderValidation")
        
    def validate_folder_async(self, folder_path: str):
        """Asynchroniczna walidacja folderu."""
        future = self._executor.submit(self._validate_folder, folder_path)
        future.add_done_callback(lambda f: self._on_validation_complete(folder_path, f))
    
    def _validate_folder(self, folder_path: str) -> tuple[bool, str]:
        """Walidacja folderu w worker thread."""
        try:
            if not os.path.exists(folder_path):
                return False, f"Folder nie istnieje: {folder_path}"
            if not os.path.isdir(folder_path):
                return False, f"Ścieżka nie jest folderem: {folder_path}"
            return True, ""
        except Exception as e:
            return False, f"Błąd podczas walidacji: {str(e)}"
    
    def _on_validation_complete(self, folder_path: str, future):
        """Callback po zakończeniu walidacji."""
        try:
            is_valid, error_msg = future.result()
            self.validation_finished.emit(folder_path, is_valid, error_msg)
        except Exception as e:
            self.validation_finished.emit(folder_path, False, f"Błąd walidacji: {str(e)}")

# W klasie GalleryTab.__init__ dodaj:
def __init__(self, main_window: "MainWindow"):
    # ... istniejący kod ...
    
    # Dodaj worker do walidacji folderów
    self._folder_validator = FolderValidationWorker()
    self._folder_validator.validation_finished.connect(self._on_folder_validation_complete)
    self._pending_folder_navigation = None

# Zmodyfikuj metodę _on_favorite_folder_clicked:
def _on_favorite_folder_clicked(self, folder_path: str):
    """
    Obsługuje kliknięcie przycisku ulubionego folderu - ASYNC VERSION.
    
    Args:
        folder_path: Ścieżka do folderu
    """
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"Rozpoczęcie asynchronicznej walidacji folderu: {folder_path}")
    
    # Zapisz pending navigation
    self._pending_folder_navigation = folder_path
    
    # Rozpocznij asynchroniczną walidację
    self._folder_validator.validate_folder_async(folder_path)

def _on_folder_validation_complete(self, folder_path: str, is_valid: bool, error_msg: str):
    """Callback po zakończeniu walidacji folderu."""
    if folder_path != self._pending_folder_navigation:
        return  # Ignore stale validation results
    
    self._pending_folder_navigation = None
    
    if not is_valid:
        QMessageBox.warning(
            self.main_window,
            "Błąd",
            f"Folder nie jest dostępny:\n{error_msg}",
        )
        return
    
    # Przełącz na zakładkę galerii
    self.main_window.tab_widget.setCurrentIndex(0)
    
    # Użyj metody set_working_directory
    self.main_window.set_working_directory(folder_path)
```

---

### PATCH 2: ASYNC FILTER APPLICATION Z PROGRESS FEEDBACK

**Problem:** `apply_filters_and_update_view()` może blokować UI przy dużych zbiorach danych
**Rozwiązanie:** Implementacja batch processing z progress feedback

```python
# Dodaj na początku klasy GalleryTab
class FilteringWorker(QObject):
    """Worker do asynchronicznego filtrowania z progress feedback."""
    
    progress_updated = pyqtSignal(int, int)  # current, total
    filtering_finished = pyqtSignal(list)  # filtered_pairs
    
    def __init__(self):
        super().__init__()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="Filtering")
    
    def apply_filters_async(self, file_pairs: list, filter_criteria: dict):
        """Asynchroniczne filtrowanie z progress feedback."""
        future = self._executor.submit(self._filter_with_progress, file_pairs, filter_criteria)
        future.add_done_callback(self._on_filtering_complete)
    
    def _filter_with_progress(self, file_pairs: list, filter_criteria: dict) -> list:
        """Filtrowanie z progress updates."""
        if not file_pairs:
            return []
        
        filtered_pairs = []
        total = len(file_pairs)
        batch_size = max(1, total // 20)  # 20 progress updates
        
        for i, pair in enumerate(file_pairs):
            # Progress update co batch_size elementów
            if i % batch_size == 0:
                self.progress_updated.emit(i, total)
            
            # Tutaj logika filtrowania - przykład uproszczony
            if self._matches_criteria(pair, filter_criteria):
                filtered_pairs.append(pair)
        
        self.progress_updated.emit(total, total)  # 100% complete
        return filtered_pairs
    
    def _matches_criteria(self, pair, criteria) -> bool:
        """Sprawdza czy para spełnia kryteria filtrowania."""
        # Implementacja kryteriów filtrowania
        # Tutaj powinna być logika z filter_panel
        return True  # Placeholder
    
    def _on_filtering_complete(self, future):
        """Callback po zakończeniu filtrowania."""
        try:
            filtered_pairs = future.result()
            self.filtering_finished.emit(filtered_pairs)
        except Exception as e:
            logging.error(f"Błąd podczas filtrowania: {e}")
            self.filtering_finished.emit([])

# W __init__ dodaj:
def __init__(self, main_window: "MainWindow"):
    # ... istniejący kod ...
    
    # Dodaj worker do filtrowania
    self._filtering_worker = FilteringWorker()
    self._filtering_worker.progress_updated.connect(self._on_filtering_progress)
    self._filtering_worker.filtering_finished.connect(self._on_filtering_finished)
    self._is_filtering = False

# Zmodyfikuj apply_filters_and_update_view:
def apply_filters_and_update_view(self):
    """
    Zbiera kryteria, filtruje pary i aktualizuje galerię - ASYNC VERSION.
    """
    # Prevent concurrent filtering
    if self._is_filtering:
        return
    
    if not self.main_window.controller.current_directory:
        if hasattr(self.main_window, "gallery_manager"):
            self.main_window.gallery_manager.file_pairs_list = []
        self.update_gallery_view()
        if hasattr(self.main_window, "size_control_panel"):
            self.main_window.size_control_panel.setVisible(False)
        if hasattr(self, "filter_panel"):
            self.filter_panel.setEnabled(False)
        return

    if not self.main_window.controller.current_file_pairs:
        if hasattr(self.main_window, "gallery_manager"):
            self.main_window.gallery_manager.file_pairs_list = []
        self.update_gallery_view()
        if hasattr(self.main_window, "size_control_panel"):
            self.main_window.size_control_panel.setVisible(False)
        return

    # Pobierz kryteria filtrowania
    filter_criteria = {}
    if hasattr(self, "filter_panel"):
        filter_criteria = self.filter_panel.get_filter_criteria()

    # Start async filtering
    self._is_filtering = True
    if hasattr(self, "filter_panel"):
        self.filter_panel.setEnabled(False)  # Disable during filtering
    
    self._filtering_worker.apply_filters_async(
        self.main_window.controller.current_file_pairs, 
        filter_criteria
    )

def _on_filtering_progress(self, current: int, total: int):
    """Callback dla progress updates podczas filtrowania."""
    # Można dodać progress bar w przyszłości
    progress_percent = (current * 100) // total if total > 0 else 0
    logging.debug(f"Filtering progress: {progress_percent}% ({current}/{total})")

def _on_filtering_finished(self, filtered_pairs: list):
    """Callback po zakończeniu filtrowania."""
    self._is_filtering = False
    
    # Update gallery with filtered results
    if hasattr(self.main_window, "gallery_manager"):
        self.main_window.gallery_manager.file_pairs_list = filtered_pairs
        self.main_window.gallery_manager.update_gallery_view()

    # Update UI visibility
    is_gallery_populated = bool(filtered_pairs)
    if hasattr(self.main_window, "size_control_panel"):
        self.main_window.size_control_panel.setVisible(is_gallery_populated)
    
    if hasattr(self, "filter_panel"):
        self.filter_panel.setEnabled(True)  # Re-enable filter panel
```

---

### PATCH 3: PERFORMANCE MONITORING I CACHE OPTIMIZATION

**Problem:** Brak monitoringu wydajności UI operations
**Rozwiązanie:** Dodanie performance monitoring i cache optimization

```python
# Dodaj na początku pliku
import time
from functools import wraps
from collections import defaultdict

def performance_monitor(operation_name: str):
    """Decorator do monitorowania wydajności operacji UI."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            start_time = time.time()
            try:
                result = func(self, *args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log performance metrics
                if execution_time > 0.1:  # Warn if operation takes >100ms
                    logging.warning(f"UI operation '{operation_name}' took {execution_time:.3f}s")
                else:
                    logging.debug(f"UI operation '{operation_name}' took {execution_time:.3f}s")
                
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logging.error(f"UI operation '{operation_name}' failed after {execution_time:.3f}s: {e}")
                raise
        return wrapper
    return decorator

# W klasie GalleryTab dodaj cache system:
def __init__(self, main_window: "MainWindow"):
    # ... istniejący kod ...
    
    # Performance monitoring cache
    self._ui_cache = {
        'folder_validation': {},
        'layout_geometry': {},
        'widget_states': {}
    }
    self._cache_ttl = 300  # 5 minutes TTL

@performance_monitor("update_gallery_view")
def update_gallery_view(self):
    """
    Aktualizuje widok galerii z performance monitoring.
    """
    if hasattr(self.main_window, "gallery_manager"):
        self.main_window.gallery_manager.update_gallery_view()

@performance_monitor("update_thumbnail_size")  
def update_thumbnail_size(self, new_size=None):
    """
    Aktualizuje rozmiar miniatur z performance monitoring.
    """
    # ... istniejący kod bez zmian ...
    
    # Cache nowego rozmiaru
    self._ui_cache['widget_states']['last_thumbnail_size'] = new_size
    self._ui_cache['widget_states']['last_update_time'] = time.time()

def _get_cached_folder_validation(self, folder_path: str) -> tuple[bool, str, bool]:
    """
    Sprawdza cache walidacji folderów.
    
    Returns:
        tuple: (is_cached, is_valid, error_msg)
    """
    cache_key = folder_path
    cache_entry = self._ui_cache['folder_validation'].get(cache_key)
    
    if cache_entry:
        cached_time, is_valid, error_msg = cache_entry
        if time.time() - cached_time < self._cache_ttl:
            return True, is_valid, error_msg
    
    return False, False, ""

def _cache_folder_validation(self, folder_path: str, is_valid: bool, error_msg: str):
    """Cache wyniku walidacji folderu."""
    self._ui_cache['folder_validation'][folder_path] = (time.time(), is_valid, error_msg)
```

---

### PATCH 4: MEMORY LEAK PREVENTION

**Problem:** Potencjalne wycieki pamięci przy długotrwałym używaniu
**Rozwiązanie:** Proper cleanup i weak references

```python
# Dodaj cleanup w destruktorze
def __del__(self):
    """Cleanup zasobów przy destrukcji."""
    self._cleanup_resources()

def _cleanup_resources(self):
    """Czyszczenie zasobów i worker threads."""
    try:
        if hasattr(self, '_folder_validator') and self._folder_validator:
            if hasattr(self._folder_validator, '_executor'):
                self._folder_validator._executor.shutdown(wait=False)
        
        if hasattr(self, '_filtering_worker') and self._filtering_worker:
            if hasattr(self._filtering_worker, '_executor'):
                self._filtering_worker._executor.shutdown(wait=False)
        
        # Clear caches
        if hasattr(self, '_ui_cache'):
            self._ui_cache.clear()
            
    except Exception as e:
        logging.error(f"Error during GalleryTab cleanup: {e}")

# Dodaj weak reference do main_window
def __init__(self, main_window: "MainWindow"):
    # Użyj weak reference do uniknięcia circular dependencies
    self._main_window_ref = weakref.ref(main_window)
    # ... reszta istniejącego kodu ...

@property 
def main_window(self):
    """Zwraca main_window przez weak reference."""
    main_window = self._main_window_ref()
    if main_window is None:
        raise RuntimeError("Main window has been garbage collected")
    return main_window
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Responsywność UI** - czy filtrowanie i folder switching nie blokuje UI
- [ ] **Thread safety** - czy async operations są thread-safe
- [ ] **Memory management** - czy nie ma wycieków pamięci z worker threads
- [ ] **Error handling** - czy async operations obsługują błędy
- [ ] **Cache efficiency** - czy cache poprawia wydajność bez przeciążania pamięci
- [ ] **Performance monitoring** - czy metryki wydajności są rejestrowane
- [ ] **Folder validation** - czy async validation działa poprawnie
- [ ] **Filter operations** - czy async filtering zachowuje funkcjonalność
- [ ] **UI state management** - czy stan UI jest poprawnie zarządzany
- [ ] **Resource cleanup** - czy zasoby są prawidłowo zwalniane

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Main window integration** - czy komunikacja z main_window działa
- [ ] **Filter panel compatibility** - czy współpraca z filter_panel zachowana
- [ ] **Gallery manager integration** - czy gallery_manager otrzymuje filtered data
- [ ] **Worker thread lifecycle** - czy worker threads są poprawnie zarządzane
- [ ] **Qt signal/slot connections** - czy async signals działają poprawnie
- [ ] **Config integration** - czy odczyt konfiguracji nie został zakłócony
- [ ] **Event handling** - czy event handling zachowuje responsywność
- [ ] **Weak references** - czy weak references do main_window działają

#### **TESTY PERFORMANCE RESPONSYWNOŚCI:**

- [ ] **Large dataset filtering** - test z 1000+ plików, czas <2s
- [ ] **Folder switching speed** - async validation <500ms
- [ ] **UI responsiveness** - brak blokowania UI during operations
- [ ] **Memory usage** - memory footprint nie wzrósł >10%
- [ ] **Concurrent operations** - multiple async operations handling
- [ ] **Cache hit ratio** - folder validation cache >80% hit rate

#### **KRYTERIA SUKCESU RESPONSYWNOŚCI UI:**

- [ ] **NO UI BLOCKING** - żadna operacja nie blokuje UI >100ms
- [ ] **ASYNC OPERATIONS** - wszystkie I/O operations asynchroniczne
- [ ] **PERFORMANCE MONITORING** - metrics rejestrowane dla slow operations
- [ ] **MEMORY EFFICIENCY** - proper cleanup i brak wycieków