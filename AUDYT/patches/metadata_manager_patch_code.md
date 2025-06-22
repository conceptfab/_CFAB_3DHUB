# PATCH-CODE DLA: metadata_manager.py

**Powiązany plik z analizą:** `../corrections/metadata_manager_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: CONSOLIDATE SPECIAL FOLDERS LOGIC

**Problem:** add_special_folder używa direct file I/O bypass MetadataManager infrastructure
**Rozwiązanie:** Delegate wszystkie special folders operations do MetadataManager core

```python
# PRZED - linia 244-309 (całe add_special_folder):
def add_special_folder(directory_path: str, folder_name: str) -> bool:
    try:
        # Pobierz instancję managera metadanych
        manager = get_instance()
        
        # Direct file I/O operations...
        metadata_dir = os.path.join(directory_path, METADATA_DIR_NAME)
        # ... 65 lines of direct implementation

# PO - simplified delegation:
def add_special_folder(directory_path: str, folder_name: str) -> bool:
    """
    Dodaje folder specjalny do metadanych dla podanego katalogu.
    REFAKTORYZACJA: Delegated to MetadataManager core dla consistency.
    
    DEPRECATED: Use MetadataManager.get_instance(directory_path).metadata_core.add_special_folder()
    """
    import warnings
    warnings.warn(
        "add_special_folder() is deprecated. Use MetadataManager.get_instance(path).metadata_core.add_special_folder()",
        DeprecationWarning,
        stacklevel=2
    )
    
    try:
        manager = MetadataManager.get_instance(directory_path)
        return manager.metadata_core.add_special_folder(directory_path, folder_name)
    except Exception as e:
        logger.error(f"Error adding special folder '{folder_name}' to '{directory_path}': {e}")
        return False
```

---

### PATCH 2: INSTANCE CACHING OPTIMIZATION

**Problem:** Multiple MetadataManager.get_instance() calls w każdej legacy function
**Rozwiązanie:** Implement smart caching z proper cleanup

```python
# DODAĆ na górze pliku (po linii 38):
# Instance cache dla performance optimization
_instance_cache = {}
_cache_lock = threading.RLock()
_cache_cleanup_time = time.time()
CACHE_CLEANUP_INTERVAL = 300  # 5 minutes

def _get_cached_instance(directory_path: str) -> "MetadataManager":
    """
    Gets cached MetadataManager instance dla performance.
    Implements automatic cleanup dla memory efficiency.
    """
    global _cache_cleanup_time
    
    with _cache_lock:
        current_time = time.time()
        
        # Periodic cache cleanup (every 5 minutes)
        if current_time - _cache_cleanup_time > CACHE_CLEANUP_INTERVAL:
            _cleanup_old_instances()
            _cache_cleanup_time = current_time
        
        # Get or create instance
        normalized_path = normalize_path(directory_path)
        if normalized_path not in _instance_cache:
            _instance_cache[normalized_path] = {
                'instance': MetadataManager.get_instance(directory_path),
                'last_access': current_time
            }
        else:
            _instance_cache[normalized_path]['last_access'] = current_time
            
        return _instance_cache[normalized_path]['instance']

def _cleanup_old_instances():
    """Cleanup instances not accessed w last 10 minutes."""
    current_time = time.time()
    old_keys = []
    
    for path, data in _instance_cache.items():
        if current_time - data['last_access'] > 600:  # 10 minutes
            old_keys.append(path)
    
    for key in old_keys:
        del _instance_cache[key]
        
    if old_keys:
        logger.debug(f"Cleaned up {len(old_keys)} old MetadataManager instances")

# ZAMIENIĆ w legacy functions (np. linia 74):
# PRZED:
    manager = MetadataManager.get_instance(working_directory)
    
# PO:
    manager = _get_cached_instance(working_directory)
```

---

### PATCH 3: DEPRECATION WARNINGS dla wszystkich legacy functions

**Problem:** Brak deprecation warnings - users nie wiedzą że API is deprecated
**Rozwiązanie:** Add consistent deprecation warnings z migration guidance

```python
# DODAĆ na górze pliku (po imports):
import warnings

# PRZYKŁAD dla load_metadata (linia 56):
def load_metadata(working_directory: str) -> Dict[str, Any]:
    """
    Legacy function: Use MetadataManager.get_instance(dir).load_metadata()
    Maintained for backward compatibility.
    
    DEPRECATED: This function will be removed in future version.
    """
    warnings.warn(
        "load_metadata() is deprecated. Use MetadataManager.get_instance(path).io.load_metadata_from_file()",
        DeprecationWarning,
        stacklevel=2
    )
    return _load_metadata_direct(working_directory)

# Podobnie dla wszystkich innych legacy functions:
def save_metadata(
    working_directory: str,
    file_pairs_list: List,
    unpaired_archives: List[str],
    unpaired_previews: List[str],
) -> bool:
    """
    DEPRECATED: Use MetadataManager.get_instance(dir).save_metadata()
    """
    warnings.warn(
        "save_metadata() is deprecated. Use MetadataManager.get_instance(path).save_metadata()",
        DeprecationWarning,
        stacklevel=2
    )
    manager = _get_cached_instance(working_directory)
    return manager.save_metadata(file_pairs_list, unpaired_archives, unpaired_previews)

def get_relative_path(absolute_path: str, base_path: str) -> Optional[str]:
    """
    DEPRECATED: Use MetadataManager.get_instance(dir).operations.get_relative_path()
    """
    warnings.warn(
        "get_relative_path() is deprecated. Use MetadataManager.get_instance(path).operations.get_relative_path()",
        DeprecationWarning,
        stacklevel=2
    )
    manager = _get_cached_instance(base_path)
    return manager.operations.get_relative_path(absolute_path, base_path)
```

---

### PATCH 4: ELIMINATE REDUNDANT PATH NORMALIZATION

**Problem:** normalize_path called multiple times w get_metadata_path/get_lock_path
**Rozwiązanie:** Single normalization i reuse normalized paths

```python
# PRZED - linia 78-91:
def get_metadata_path(working_directory: str) -> str:
    # Normalizujemy ścieżkę katalogu roboczego
    normalized_working_dir = normalize_path(working_directory)
    metadata_dir = os.path.join(normalized_working_dir, METADATA_DIR_NAME)
    return normalize_path(os.path.join(metadata_dir, METADATA_FILE_NAME))

def get_lock_path(working_directory: str) -> str:
    normalized_working_dir = normalize_path(working_directory)
    metadata_dir = os.path.join(normalized_working_dir, METADATA_DIR_NAME)
    return normalize_path(os.path.join(metadata_dir, LOCK_FILE_NAME))

# PO - optimized shared implementation:
def _get_metadata_dir(working_directory: str) -> str:
    """
    Helper function to get normalized metadata directory path.
    Eliminates redundant path normalization.
    """
    normalized_working_dir = normalize_path(working_directory)
    return os.path.join(normalized_working_dir, METADATA_DIR_NAME)

def get_metadata_path(working_directory: str) -> str:
    """
    Zwraca pełną ścieżkę do pliku metadanych w podanym folderze roboczym.
    OPTYMALIZACJA: Reduced path normalization calls.
    """
    metadata_dir = _get_metadata_dir(working_directory)
    return os.path.join(metadata_dir, METADATA_FILE_NAME)

def get_lock_path(working_directory: str) -> str:
    """
    Zwraca pełną ścieżkę do pliku blokady metadanych.
    OPTYMALIZACJA: Reduced path normalization calls.
    """
    metadata_dir = _get_metadata_dir(working_directory)
    return os.path.join(metadata_dir, LOCK_FILE_NAME)
```

---

### PATCH 5: IMPROVED SINGLETON THREAD SAFETY

**Problem:** Global singleton management może być problematic w multi-threaded env
**Rozwiązanie:** Better thread safety z proper cleanup

```python
# PRZED - linia 36-52:
# Singleton instance
_instance = None
_instance_lock = threading.RLock()

def get_instance() -> "MetadataManager":
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = MetadataManager(working_directory=".")
        return _instance

# PO - improved singleton z cleanup capability:
# Singleton instance z better management
_global_instance = None
_global_instance_lock = threading.RLock()
_instance_creation_time = None

def get_instance() -> "MetadataManager":
    """
    Zwraca instancję singleton MetadataManager.
    UWAGA: This is legacy global singleton. 
    Prefer MetadataManager.get_instance(directory) dla better isolation.
    
    Returns:
        MetadataManager: Instancja singleton.
    """
    global _global_instance, _instance_creation_time
    
    warnings.warn(
        "Global get_instance() is deprecated. Use MetadataManager.get_instance(directory_path)",
        DeprecationWarning,
        stacklevel=2
    )
    
    with _global_instance_lock:
        if _global_instance is None:
            _global_instance = MetadataManager(working_directory=".")
            _instance_creation_time = time.time()
            logger.debug("Created global MetadataManager singleton instance")
        return _global_instance

def cleanup_global_instance():
    """
    Cleanup global singleton instance dla proper shutdown.
    Should be called on application exit.
    """
    global _global_instance, _instance_cache
    
    with _global_instance_lock:
        if _global_instance is not None:
            logger.debug("Cleaning up global MetadataManager singleton")
            _global_instance = None
    
    with _cache_lock:
        _instance_cache.clear()
        logger.debug("Cleared MetadataManager instance cache")
```

---

### PATCH 6: STRUCTURED BUSINESS LOGGING

**Problem:** Inconsistent logging i brak business metrics
**Rozwiązanie:** Structured logging z metadata operation metrics

```python
# DODAĆ w legacy functions structured logging:

# W save_metadata function (po successful save):
    start_time = time.time()
    manager = _get_cached_instance(working_directory)
    result = manager.save_metadata(file_pairs_list, unpaired_archives, unpaired_previews)
    elapsed_time = time.time() - start_time
    
    # Business metrics logging
    total_items = len(file_pairs_list) + len(unpaired_archives) + len(unpaired_previews)
    logger.info(
        f"METADATA_SAVE: path={os.path.basename(working_directory)} | "
        f"pairs={len(file_pairs_list)} | unpaired_archives={len(unpaired_archives)} | "
        f"unpaired_previews={len(unpaired_previews)} | total_items={total_items} | "
        f"time={elapsed_time:.3f}s | success={result}"
    )
    
    if elapsed_time > 1.0:  # Slow save warning
        logger.warning(
            f"SLOW_METADATA_SAVE: {elapsed_time:.3f}s dla {total_items} items. "
            f"Consider metadata optimization."
        )
    
    return result

# W load_metadata function:
    start_time = time.time()
    result = _load_metadata_direct(working_directory)
    elapsed_time = time.time() - start_time
    
    # Business metrics
    items_loaded = len(result.get('file_pairs', [])) + len(result.get('unpaired_archives', [])) + len(result.get('unpaired_previews', []))
    
    logger.info(
        f"METADATA_LOAD: path={os.path.basename(working_directory)} | "
        f"items_loaded={items_loaded} | time={elapsed_time:.3f}s"
    )
    
    return result
```

---

### PATCH 7: ERROR HANDLING IMPROVEMENT

**Problem:** Silent errors w try/catch blocks mogą ukrywać critical issues
**Rozwiązanie:** Better error context i recovery strategies

```python
# ZMIENIĆ error handling w legacy functions:

def apply_metadata_to_file_pairs(working_directory: str, file_pairs_list: List) -> bool:
    """
    Legacy function z improved error handling.
    """
    warnings.warn(
        "apply_metadata_to_file_pairs() is deprecated. Use MetadataManager.get_instance(path).apply_metadata_to_file_pairs()",
        DeprecationWarning,
        stacklevel=2
    )
    
    try:
        manager = _get_cached_instance(working_directory)
        return manager.apply_metadata_to_file_pairs(file_pairs_list)
    except FileNotFoundError as e:
        logger.warning(f"Metadata file not found dla {working_directory}: {e}")
        return False  # Graceful degradation
    except PermissionError as e:
        logger.error(f"Permission denied accessing metadata w {working_directory}: {e}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Corrupted metadata file w {working_directory}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error applying metadata w {working_directory}: {e}", exc_info=True)
        return False

# Podobnie dla innych functions...
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - wszystkie legacy functions działają identycznie
- [ ] **API kompatybilność** - zero breaking changes dla existing code
- [ ] **Deprecation warnings** - appropriate warnings dla wszystkich legacy functions
- [ ] **Error handling** - graceful handling all metadata operation errors
- [ ] **Special folders** - add/remove/get operations działają correctly
- [ ] **Thread safety** - concurrent metadata operations są safe
- [ ] **Singleton behavior** - global instance behavior preserved
- [ ] **Instance caching** - performance improvement through caching
- [ ] **Path operations** - get_metadata_path/get_lock_path działa correctly
- [ ] **Memory management** - cache cleanup prevents memory leaks

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **MetadataManager integration** - new core MetadataManager API used correctly
- [ ] **scanner_core.py** - metadata loading integration works
- [ ] **filelock dependency** - external lock operations work
- [ ] **path_utils** - path normalization integration works
- [ ] **Backward compatibility** - all existing callers work unchanged
- [ ] **Migration path** - clear upgrade path dla developers
- [ ] **Threading** - concurrent access from multiple components safe
- [ ] **File I/O** - metadata file operations handle all edge cases

#### **TESTY WERYFIKACYJNE:**

- [ ] **Unit tests** - każda legacy function działa w izolacji
- [ ] **Integration tests** - end-to-end metadata operations work
- [ ] **Thread safety tests** - concurrent operations nie cause issues
- [ ] **Performance tests** - operations są faster lub same speed
- [ ] **Memory tests** - cache cleanup prevents memory leaks
- [ ] **Migration tests** - deprecation warnings guide developers correctly
- [ ] **Error handling tests** - all error scenarios handled gracefully

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **ZERO BREAKING CHANGES** - wszystkie existing calls work
- [ ] **DEPRECATION STRATEGY** - clear migration path provided
- [ ] **PERFORMANCE MAINTAINED** - operations nie są slower
- [ ] **MEMORY EFFICIENCY** - cache management prevents leaks

---