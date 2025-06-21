# 🔧 Fragmenty kodu do poprawek - metadata_core.py

## Poprawka 1.1: Thread Safety - Timer Management

### PROBLEM:

```python
# Linie 67-69 w metadata_core.py
delay_seconds = self._save_delay / 1000.0
self._save_timer = threading.Timer(delay_seconds, self._flush_now)
self._save_timer.start()
```

### ROZWIĄZANIE:

```python
# Użyj proper thread-safe timer z error handling
try:
    delay_seconds = self._save_delay / 1000.0
    self._save_timer = threading.Timer(delay_seconds, self._flush_now)
    self._save_timer.daemon = True  # Daemon thread dla lepszego cleanup
    self._save_timer.start()
except Exception as e:
    logger.error(f"Błąd podczas uruchamiania timer: {e}")
    # Fallback: immediate flush
    self._flush_now()
```

## Poprawka 1.2: Memory Management - Weak References

### PROBLEM:

```python
# Linie 130-131 w metadata_core.py
cls._instances[norm_dir] = weakref.ref(new_instance, cls._cleanup_callback)
```

### ROZWIĄZANIE:

```python
# Dodaj explicit cleanup i lepsze zarządzanie
try:
    cls._instances[norm_dir] = weakref.ref(new_instance, cls._cleanup_callback)
    logger.debug(f"Utworzono nową instancję MetadataManager dla: {norm_dir}")
except Exception as e:
    logger.error(f"Błąd podczas tworzenia weak reference: {e}")
    # Fallback: direct reference (bez automatic cleanup)
    cls._instances[norm_dir] = lambda: new_instance
```

## Poprawka 1.3: Error Handling - Specific Exceptions

### PROBLEM:

```python
# Linie 82-84 w metadata_core.py
except Exception as e:
    logger.error(f"Błąd podczas flush bufora: {e}", exc_info=True)
```

### ROZWIĄZANIE:

```python
# Specyficzne exception handling
except (IOError, OSError) as e:
    logger.error(f"Błąd I/O podczas flush bufora: {e}")
    # Retry logic
    if retry_count < 3:
        time.sleep(0.1)
        return self._flush_now(retry_count + 1)
except (KeyError, TypeError) as e:
    logger.error(f"Błąd danych podczas flush bufora: {e}")
    # Clear corrupted buffer
    self._changes_buffer.clear()
except Exception as e:
    logger.error(f"Nieoczekiwany błąd podczas flush bufora: {e}", exc_info=True)
```

## Poprawka 1.4: Logging - Performance Optimization

### PROBLEM:

```python
# Linie 58-61 w metadata_core.py
logger.debug(
    "Buffer jest za stary (%dms), wymuszam natychmiastowy zapis", buffer_age
)
```

### ROZWIĄZANIE:

```python
# Conditional logging dla lepszej wydajności
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(
        "Buffer jest za stary (%dms), wymuszam natychmiastowy zapis", buffer_age
    )
```

## Poprawka 1.5: Buffer Management - Performance

### PROBLEM:

```python
# Linie 43-47 w metadata_core.py
def add_changes(self, changes: Dict[str, Any]):
    """Dodaje zmiany do bufora thread-safe."""
    with self._buffer_lock:
        self._changes_buffer.update(changes)
        self._schedule_save()
```

### ROZWIĄZANIE:

```python
# Zoptymalizowany buffer management
def add_changes(self, changes: Dict[str, Any]):
    """Dodaje zmiany do bufora thread-safe z batch optimization."""
    with self._buffer_lock:
        # Batch update dla lepszej wydajności
        if isinstance(changes, dict):
            self._changes_buffer.update(changes)
        else:
            logger.warning("Nieprawidłowy format zmian: %s", type(changes))
            return

        # Schedule save tylko jeśli są znaczące zmiany
        if len(self._changes_buffer) > 0:
            self._schedule_save()
```

## Poprawka 1.6: Cache Strategy - TTL Optimization

### PROBLEM:

```python
# Linie 246-265 w metadata_core.py - load_metadata method
def load_metadata(self) -> Dict[str, Any]:
    # Sprawdź cache
    cached_metadata = self.cache.get()
    if cached_metadata is not None:
        return cached_metadata
```

### ROZWIĄZANIE:

```python
# Zoptymalizowany cache strategy
def load_metadata(self) -> Dict[str, Any]:
    """Wczytuje metadane z cache lub pliku z optymalizacją."""
    # Sprawdź cache z timeout
    cached_metadata = self.cache.get()
    if cached_metadata is not None:
        return cached_metadata

    # Wczytaj z pliku z thread safety i retry
    with self._operation_lock:
        try:
            metadata = self.io.load_metadata_from_file()
            if metadata is not None:
                self.cache.set(metadata)
                return metadata
            else:
                logger.warning("Nie udało się wczytać metadanych z pliku")
                return {}
        except Exception as e:
            logger.error(f"Błąd podczas wczytywania metadanych: {e}")
            return {}
```

## Poprawka 1.7: Atomic Write Callback - Error Recovery

### PROBLEM:

```python
# Linie 218-227 w metadata_core.py
def _atomic_write_callback(self, data: Dict[str, Any]) -> bool:
    """Callback dla buffer manager do wykonywania atomic writes."""
    try:
        success = self.io.atomic_write(data)
        if success:
            self.cache.invalidate()  # Invalidate cache po zapisie
            logger.debug("Pomyślnie zapisano zmiany z bufora")
        return success
    except Exception as e:
        logger.error(f"Błąd atomic write: {e}", exc_info=True)
        return False
```

### ROZWIĄZANIE:

```python
# Ulepszony atomic write z retry logic
def _atomic_write_callback(self, data: Dict[str, Any]) -> bool:
    """Callback dla buffer manager do wykonywania atomic writes z retry."""
    max_retries = 3
    retry_delay = 0.1

    for attempt in range(max_retries):
        try:
            success = self.io.atomic_write(data)
            if success:
                self.cache.invalidate()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Pomyślnie zapisano zmiany z bufora (próba %d)", attempt + 1)
                return True
            else:
                logger.warning("Atomic write nie powiódł się (próba %d)", attempt + 1)
        except (IOError, OSError) as e:
            logger.error(f"Błąd I/O podczas atomic write (próba %d): {e}", attempt + 1)
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd podczas atomic write (próba %d): {e}", attempt + 1, exc_info=True)

        # Retry z exponential backoff
        if attempt < max_retries - 1:
            time.sleep(retry_delay * (2 ** attempt))

    logger.error("Wszystkie próby atomic write nie powiodły się")
    return False
```

## Poprawka 1.8: Cleanup - Resource Management

### PROBLEM:

```python
# Linie 474-488 w metadata_core.py
def cleanup(self):
    """NOWY: Cleanup resources."""
    if hasattr(self, "buffer_manager"):
        self.buffer_manager.cleanup()

def __del__(self):
    """Destructor - cleanup resources."""
    try:
        self.cleanup()
    except:
        pass  # Ignore errors during cleanup
```

### ROZWIĄZANIE:

```python
# Ulepszony cleanup z proper resource management
def cleanup(self):
    """Cleanup resources z proper error handling."""
    try:
        if hasattr(self, "buffer_manager"):
            self.buffer_manager.cleanup()
        if hasattr(self, "cache"):
            self.cache.invalidate()
        logger.debug("MetadataManager cleanup zakończony")
    except Exception as e:
        logger.error(f"Błąd podczas cleanup MetadataManager: {e}")

def __del__(self):
    """Destructor - cleanup resources."""
    try:
        self.cleanup()
    except Exception as e:
        # Log error ale nie rzuć wyjątku w destructor
        pass
```
