# 🔧 Fragmenty kodu do poprawek - metadata_operations.py

## Poprawka 3.1: Circular Dependency - Remove Import

### PROBLEM:

```python
# W metodach _load_metadata i _save_metadata:
from src.logic.metadata.metadata_manager import MetadataManager
```

### ROZWIĄZANIE:

```python
# Dependency injection: przekazuj instancję MetadataManager jako argument do metod,
# lub przenieś logikę do wyższego poziomu (np. do managera).
# Przykład:
def _load_metadata(self, directory_path: str, metadata_manager=None) -> Optional[Dict[str, Any]]:
    if metadata_manager is None:
        from src.logic.metadata.metadata_manager import MetadataManager
        metadata_manager = MetadataManager.get_instance(directory_path)
    return metadata_manager.load_metadata()
```

## Poprawka 3.2: Performance - Attribute Checking Optimization

### PROBLEM:

```python
# W wielu miejscach:
if not all(hasattr(file_pair, attr) for attr in [...]):
```

### ROZWIĄZANIE:

```python
# Zamiast sprawdzać za każdym razem, sprawdź raz na początku batcha lub użyj try/except.
def _validate_file_pair(self, file_pair) -> bool:
    required = ["archive_path", "get_stars", "set_stars", "get_color_tag", "set_color_tag"]
    return all(hasattr(file_pair, attr) for attr in required)
# Używaj w pętli:
if not self._validate_file_pair(file_pair):
    continue
```

## Poprawka 3.3: Path Operations - Simplified Logic

### PROBLEM:

```python
# Skomplikowana logika NT/Unix w get_relative_path
```

### ROZWIĄZANIE:

```python
# Uproszczona logika z proper error handling
try:
    relative_path = os.path.relpath(norm_abs_path, norm_base_path)
    return normalize_path(relative_path)
except ValueError as e:
    logger.error("Błąd relpath: %s", e)
    return None
```

## Poprawka 3.4: Batch Processing - Better Performance

### PROBLEM:

```python
# Prosty batch_size, logowanie co batch
```

### ROZWIĄZANIE:

```python
# Użyj generatorów i progress callback (jeśli dostępny)
def apply_metadata_to_file_pairs(self, metadata, file_pairs_list, progress_cb=None):
    for i, file_pair in enumerate(file_pairs_list):
        # ...
        if progress_cb and i % 100 == 0:
            progress_cb(i, len(file_pairs_list))
```

## Poprawka 3.5: Logging - Performance Optimization

### PROBLEM:

```python
# Zbyt wiele logger.debug w pętlach
```

### ROZWIĄZANIE:

```python
# Używaj logger.isEnabledFor(logging.DEBUG) przed logowaniem w batchach
if logger.isEnabledFor(logging.DEBUG) and i % 100 == 0:
    logger.debug("Przetworzono %d/%d", i, total_files)
```

## Poprawka 3.6: Special Folders - Optimized Scanning

### PROBLEM:

```python
# Wielokrotne os.listdir w check_special_folders
```

### ROZWIĄZANIE:

```python
# Zrób jedno os.listdir i użyj list comprehensions
try:
    dir_contents = os.listdir(self.working_directory)
    special_folders = [item for item in dir_contents if os.path.isdir(os.path.join(self.working_directory, item)) and SpecialFolder.is_special_folder(item)]
except Exception as e:
    logger.error("Błąd listowania katalogu: %s", e)
```

## Poprawka 3.7: Error Handling - Better Recovery

### PROBLEM:

```python
# Zbyt ogólne except Exception
```

### ROZWIĄZANIE:

```python
# Rozbij na specyficzne wyjątki (OSError, ValueError, TypeError)
try:
    ...
except (OSError, ValueError) as e:
    logger.error("Błąd operacji: %s", e)
```

## Poprawka 3.8: Memory Usage - Optimization

### PROBLEM:

```python
# Duplikacja list, niepotrzebne kopie
```

### ROZWIĄZANIE:

```python
# Używaj generatorów i comprehensions, nie twórz niepotrzebnych kopii
unpaired_archives_rel = (self.get_relative_path(p, self.working_directory) for p in unpaired_archives)
unpaired_archives_rel = [p for p in unpaired_archives_rel if p is not None]
```
