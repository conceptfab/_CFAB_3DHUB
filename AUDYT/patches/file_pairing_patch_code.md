# PATCH-CODE DLA: FILE_PAIRING

**Powiązany plik z analizą:** `../corrections/file_pairing_correction.md`
**Zasady ogólne:** `../../_BASE_/refactoring_rules.md`

---

### PATCH 1: USUNIĘCIE DEAD CODE - STARA FUNKCJA KATEGORYZACJI

**Problem:** Duplikacja funkcji kategoryzacji - `_categorize_files()` nie jest używana, tylko `_categorize_files_optimized()`
**Rozwiązanie:** Usunięcie starej funkcji i refaktoryzacja nazwy zoptymalizowanej wersji

```python
# USUNĄĆ (linie 283-299):
def _categorize_files(files_list: List[str]) -> Tuple[List[str], List[str]]:
    """
    Kategoryzuje pliki na archiwa i podglądy.
    """
    # Pre-compute rozszerzeń dla optymalizacji
    files_with_ext = [(f, os.path.splitext(f)[1].lower()) for f in files_list]

    archive_files = [f for f, ext in files_with_ext if ext in ARCHIVE_EXTENSIONS]
    preview_files = [f for f, ext in files_with_ext if ext in PREVIEW_EXTENSIONS]

    return archive_files, preview_files

# ZMIENIĆ NAZWĘ (linie 38-53):
def _categorize_files_optimized(files_list: List[str]) -> Tuple[List[str], List[str]]:
# NA:
def _categorize_files(files_list: List[str]) -> Tuple[List[str], List[str]]:
    """
    Optimized kategoryzacja plików na archiwa i podglądy.
    Pre-computes file info once instead of parsing extensions multiple times.
    """
    if not files_list:
        return [], []

    # Pre-compute file info once - O(n) instead of O(2n)
    file_infos = [FileInfo(f) for f in files_list]

    # Single pass categorization - O(n) instead of O(2n)
    archive_files = [fi.path for fi in file_infos if fi.is_archive]
    preview_files = [fi.path for fi in file_infos if fi.is_preview]

    return archive_files, preview_files

# ZMIENIĆ WYWOŁANIE (linia 332):
        archive_files, preview_files = _categorize_files_optimized(files_list)
# NA:
        archive_files, preview_files = _categorize_files(files_list)
```

---

### PATCH 2: DODANIE THREAD SAFETY DO SimpleTrie

**Problem:** SimpleTrie nie jest thread-safe - race conditions przy concurrent access
**Rozwiązanie:** Dodanie locks dla thread safety i memory management

```python
import threading
from threading import RLock

class SimpleTrie:
    """Thread-safe Simple Trie dla fast prefix matching z memory management."""

    def __init__(self, max_files_per_key: int = 50):
        self.root = {}
        self.files = {}  # Maps prefix -> list of files
        self._lock = RLock()  # Reentrant lock dla thread safety
        self._max_files_per_key = max_files_per_key
        self._total_entries = 0
        self._max_total_entries = 10000  # Memory limit

    def add(self, key: str, file_path: str):
        """Thread-safe adds file with its prefix key."""
        with self._lock:
            # Memory management - prevent unlimited growth
            if self._total_entries >= self._max_total_entries:
                self._cleanup_old_entries()
            
            node = self.root
            for char in key:
                if char not in node:
                    node[char] = {}
                node = node[char]

            if key not in self.files:
                self.files[key] = []
            
            # Limit files per key to prevent memory bloat
            if len(self.files[key]) < self._max_files_per_key:
                self.files[key].append(file_path)
                self._total_entries += 1

    def find_prefix_matches(self, prefix: str, max_results: int = 20) -> List[str]:
        """Thread-safe finds all keys that match the prefix with O(log k) optimization."""
        with self._lock:
            matches = []

            # Exact match first (highest priority)
            if prefix in self.files:
                matches.extend(self.files[prefix][:max_results])

            if len(matches) >= max_results:
                return matches[:max_results]

            # Optimized prefix matches using sorted keys
            sorted_keys = sorted(self.files.keys())
            remaining_slots = max_results - len(matches)
            
            for key in sorted_keys:
                if len(matches) >= max_results:
                    break
                if key != prefix and (key.startswith(prefix) or prefix.startswith(key)):
                    available_slots = remaining_slots - len(matches)
                    matches.extend(self.files[key][:available_slots])

            return matches[:max_results]
    
    def _cleanup_old_entries(self):
        """Remove least recently used entries to manage memory."""
        if len(self.files) <= 100:  # Keep minimum entries
            return
            
        # Remove entries with fewer files (less important)
        keys_to_remove = []
        for key, file_list in self.files.items():
            if len(file_list) <= 1:  # Remove single-file entries first
                keys_to_remove.append(key)
                if len(keys_to_remove) >= len(self.files) // 4:  # Remove 25%
                    break
        
        for key in keys_to_remove:
            self._total_entries -= len(self.files[key])
            del self.files[key]
    
    def clear(self):
        """Thread-safe clear all entries."""
        with self._lock:
            self.root.clear()
            self.files.clear()
            self._total_entries = 0
```

---

### PATCH 3: OPTYMALIZACJA LOGOWANIA I PERFORMANCE MONITORING

**Problem:** Over-logging błędów może spamować logi, brak performance metrics
**Rozwiązanie:** Standaryzacja logowania i dodanie optional performance tracking

```python
import time
from typing import Optional

# Dodaj na początku pliku:
class PerformanceTracker:
    """Optional performance tracking dla profiling."""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.metrics = {}
    
    def track_operation(self, operation_name: str, file_count: int, duration: float):
        if not self.enabled:
            return
        
        if operation_name not in self.metrics:
            self.metrics[operation_name] = []
        
        self.metrics[operation_name].append({
            'file_count': file_count,
            'duration': duration,
            'files_per_second': file_count / duration if duration > 0 else 0
        })
    
    def get_average_performance(self, operation_name: str) -> Optional[float]:
        if operation_name not in self.metrics or not self.metrics[operation_name]:
            return None
        
        records = self.metrics[operation_name]
        avg_fps = sum(r['files_per_second'] for r in records) / len(records)
        return avg_fps

# Global performance tracker - enabled via config
_performance_tracker = PerformanceTracker(enabled=getattr(app_config, 'ENABLE_PERFORMANCE_TRACKING', False))

# ZMIENIĆ error handling w OptimizedBestMatchStrategy (linie 180-183):
                except ValueError as e:
                    logger.warning(
                        f"Skipping invalid pair {archive} + {best_preview}: {e}"
                    )
# NA:
                except ValueError as e:
                    # Reduced logging to prevent spam - count errors instead
                    if not hasattr(self, '_error_count'):
                        self._error_count = 0
                    self._error_count += 1
                    
                    # Log only first few errors and then periodically
                    if self._error_count <= 3 or self._error_count % 100 == 0:
                        logger.warning(f"Pairing errors encountered: {self._error_count} total")
                        logger.debug(f"Latest error: {archive} + {best_preview}: {e}")

# ZMIENIĆ error handling w FirstMatchStrategy (linie 130-133):
                logger.error(
                    f"Błąd tworzenia FilePair dla '{archive_files[0]}' i '{preview_files[0]}': {e}"
                )
# NA:
                logger.warning(f"Failed to create FilePair: {e}")
                logger.debug(f"Files: {archive_files[0]} + {preview_files[0]}")

# DODAĆ performance tracking do create_file_pairs (po linii 319):
def create_file_pairs(
    file_map: Dict[str, List[str]],
    base_directory: str,
    pair_strategy: str = "first_match",
) -> Tuple[List[FilePair], Set[str]]:
    """
    Tworzy pary plików na podstawie zebranych danych z performance tracking.
    """
    start_time = time.time()
    total_files = sum(len(files) for files in file_map.values())
    
    found_pairs: List[FilePair] = []
    processed_files: Set[str] = set()

    # ... existing code ...
    
    # Performance tracking
    duration = time.time() - start_time
    _performance_tracker.track_operation('create_file_pairs', total_files, duration)
    
    if duration > 0:
        files_per_second = total_files / duration
        logger.info(f"File pairing completed: {len(found_pairs)} pairs created from {total_files} files in {duration:.2f}s ({files_per_second:.1f} files/s)")
    
    return found_pairs, processed_files
```

---

### PATCH 4: MEMORY OPTIMIZATION W IDENTIFY_UNPAIRED_FILES

**Problem:** Funkcja może być zoptymalizowana przez pre-filtrowanie processed_files
**Rozwiązanie:** Early filtering i batch processing optimization

```python
def identify_unpaired_files(
    file_map: Dict[str, List[str]],
    processed_files: Set[str],
) -> Tuple[List[str], List[str]]:
    """
    Memory-efficient identification of unpaired files z pre-filtering optimization.
    """
    if not file_map:
        return [], []

    # Pre-filter processed files by extension dla performance
    processed_archives = {f for f in processed_files 
                         if os.path.splitext(f)[1].lower() in ARCHIVE_EXTENSIONS}
    processed_previews = {f for f in processed_files 
                         if os.path.splitext(f)[1].lower() in PREVIEW_EXTENSIONS}

    unpaired_archives: List[str] = []
    unpaired_previews: List[str] = []

    # Optimized streaming processing
    for files_list in file_map.values():
        # Batch process files from same directory
        archives_batch = []
        previews_batch = []
        
        for file_path in files_list:
            ext_lower = os.path.splitext(file_path)[1].lower()
            
            if ext_lower in ARCHIVE_EXTENSIONS:
                if file_path not in processed_archives:
                    archives_batch.append(file_path)
            elif ext_lower in PREVIEW_EXTENSIONS:
                if file_path not in processed_previews:
                    previews_batch.append(file_path)
        
        # Add batches to results
        unpaired_archives.extend(archives_batch)
        unpaired_previews.extend(previews_batch)

    # Efficient sorting with key function
    unpaired_archives.sort(key=lambda x: os.path.basename(x).lower())
    unpaired_previews.sort(key=lambda x: os.path.basename(x).lower())

    return unpaired_archives, unpaired_previews
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - parowanie plików działa identycznie jak wcześniej
- [ ] **API kompatybilność** - create_file_pairs(), identify_unpaired_files() API unchanged
- [ ] **Obsługa błędów** - mechanizmy error handling nie spamują logów
- [ ] **Walidacja danych** - FilePair validation działa poprawnie
- [ ] **Logowanie** - system logowania nie spamuje, performance logs działają
- [ ] **Konfiguracja** - app_config extensions loading działa
- [ ] **Cache** - SimpleTrie cache działa z memory management
- [ ] **Thread safety** - SimpleTrie jest thread-safe z RLock
- [ ] **Memory management** - Trie cleanup zapobiega memory leaks
- [ ] **Performance** - 1000+ plików/sekundę maintained, memory <500MB

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - wszystkie importy (app_config, FilePair) działają
- [ ] **Zależności zewnętrzne** - threading, time modules used properly
- [ ] **Zależności wewnętrzne** - integration z scanner_core.py maintained
- [ ] **Cykl zależności** - no circular dependencies introduced
- [ ] **Backward compatibility** - wszystkie existing calls działają
- [ ] **Interface contracts** - PairingStrategy interface unchanged
- [ ] **Event handling** - nie dotyczy bezpośrednio
- [ ] **Signal/slot connections** - nie dotyczy bezpośrednio
- [ ] **File I/O** - file path operations działają poprawnie

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - wszystkie funkcje działają w izolacji
- [ ] **Test integracyjny** - integration z scanner pipeline działa
- [ ] **Test regresyjny** - no functionality regressions
- [ ] **Test wydajnościowy** - 1000+ files/s maintained, memory managed

#### **PERFORMANCE KRYTERIA:**

- [ ] **Pairing speed** - 1000+ plików/sekundę maintained
- [ ] **Memory usage** - <100MB per 1000 files, Trie cleanup working
- [ ] **Thread safety** - concurrent access bez race conditions
- [ ] **Error handling** - no log spam, proper error counting

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - wszystkie testy file pairing przechodzą
- [ ] **PERFORMANCE BUDGET** - wydajność nie pogorszona, memory controlled
- [ ] **CODE COVERAGE** - coverage maintained lub improved