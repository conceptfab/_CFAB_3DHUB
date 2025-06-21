# 🔧 Fragmenty kodu do poprawek - metadata_io.py

## Poprawka 2.1: File Locking - Dynamic Timeout

### PROBLEM:

```python
# Linie 20-21 w metadata_io.py
LOCK_TIMEOUT = 0.5  # Czas oczekiwania na blokadę w sekundach
```

### ROZWIĄZANIE:

```python
# Dynamic timeout based on file size i system load
def _calculate_lock_timeout(self, file_size: int = 0) -> float:
    """Oblicza dynamic timeout na podstawie rozmiaru pliku i systemu."""
    base_timeout = 0.5

    # Zwiększ timeout dla dużych plików
    if file_size > 1024 * 1024:  # > 1MB
        base_timeout = 2.0
    elif file_size > 100 * 1024:  # > 100KB
        base_timeout = 1.0

    # Sprawdź system operacyjny
    if os.name == "nt":  # Windows - wolniejsze operacje
        base_timeout *= 1.5

    return min(base_timeout, 5.0)  # Max 5 sekund
```

## Poprawka 2.2: Atomic Write - Simplified Logic

### PROBLEM:

```python
# Linie 175-185 w metadata_io.py
# Atomic move (rename)
if os.name == "nt":  # Windows
    if os.path.exists(metadata_path):
        logger.info(f"Zastępuję istniejący plik: {metadata_path}")
        os.replace(temp_file_path, metadata_path)
    else:
        logger.info(f"Tworzę nowy plik: {metadata_path}")
        shutil.move(temp_file_path, metadata_path)
else:  # Unix-like
    logger.info(f"Przenoszę plik: {temp_file_path} -> {metadata_path}")
    os.rename(temp_file_path, metadata_path)
```

### ROZWIĄZANIE:

```python
# Uproszczona logika atomic move z fallback
def _atomic_move_file(self, temp_file_path: str, metadata_path: str) -> bool:
    """Wykonuje atomic move pliku z fallback."""
    try:
        # Próbuj os.replace (Python 3.3+) - działa na wszystkich systemach
        os.replace(temp_file_path, metadata_path)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Atomic move: {temp_file_path} -> {metadata_path}")
        return True
    except OSError:
        try:
            # Fallback: shutil.move
            shutil.move(temp_file_path, metadata_path)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Fallback move: {temp_file_path} -> {metadata_path}")
            return True
        except OSError as e:
            logger.error(f"Błąd podczas przenoszenia pliku: {e}")
            return False
```

## Poprawka 2.3: Validation - Remove Duplication

### PROBLEM:

```python
# Linie 266-344 w metadata_io.py - cała metoda _validate_metadata_structure
def _validate_metadata_structure(self, metadata_content: Dict) -> bool:
    """
    Sprawdza czy struktura metadanych jest poprawna.
    Akceptuje nową strukturę z kluczem __metadata__ dla specjalnych folderów.
    """
    # ... 78 linii duplikowanej walidacji ...
```

### ROZWIĄZANIE:

```python
# Usuń całą metodę _validate_metadata_structure i używaj tylko validator
def load_metadata_from_file(self) -> Dict[str, Any]:
    """
    Wczytuje metadane z pliku z obsługą blokady.
    """
    metadata_path = self.get_metadata_path()
    lock_path = self.get_lock_path()

    default_metadata = {
        "file_pairs": {},
        "unpaired_archives": [],
        "unpaired_previews": [],
        "has_special_folders": False,
    }

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Próba wczytania metadanych z: {metadata_path}")

    if not os.path.exists(metadata_path):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Plik metadanych nie istnieje: {metadata_path}. Zwracam domyślne metadane.")
        return default_metadata

    # Dynamic timeout based on file size
    file_size = os.path.getsize(metadata_path) if os.path.exists(metadata_path) else 0
    lock_timeout = self._calculate_lock_timeout(file_size)
    lock = FileLock(lock_path, timeout=lock_timeout)

    try:
        with lock:
            with open(metadata_path, "r", encoding="utf-8") as file:
                metadata = json.load(file)

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Pomyślnie wczytano metadane z {metadata_path}")

            # Użyj tylko metadata_validator.py
            if not self.validator.validate_metadata_structure(metadata):
                logger.warning("Struktura metadanych jest niepoprawna. Zwracam domyślne metadane.")
                return default_metadata

            return metadata

    except Timeout:
        logger.error(f"Nie można uzyskać blokady pliku metadanych {lock_path} w ciągu {lock_timeout}s podczas wczytywania.")
        return default_metadata
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Błąd parsowania JSON metadanych z {metadata_path}: {e}")
        return default_metadata
    except Exception as e:
        logger.error(f"Błąd wczytywania metadanych z {metadata_path}: {e}")
        return default_metadata
```

## Poprawka 2.4: Error Handling - Better Recovery

### PROBLEM:

```python
# Linie 200-210 w metadata_io.py
except Timeout:
    logger.error(
        f"Nie można uzyskać blokady dla {lock_path} w ciągu {LOCK_TIMEOUT}s"
    )
    return False
except Exception as e:
    logger.error(f"Błąd zapisu metadanych: {e}", exc_info=True)
    return False
```

### ROZWIĄZANIE:

```python
# Lepsze error handling z retry logic
def atomic_write(self, metadata_dict: Dict[str, Any]) -> bool:
    """Atomic write z file locking i proper error handling."""
    max_retries = 3
    retry_delay = 0.1

    for attempt in range(max_retries):
        try:
            return self._perform_atomic_write(metadata_dict, attempt + 1)
        except Timeout:
            logger.warning(f"Timeout podczas zapisu (próba {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))
        except (OSError, IOError) as e:
            logger.error(f"Błąd I/O podczas zapisu (próba {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd podczas zapisu (próba {attempt + 1}/{max_retries}): {e}", exc_info=True)
            break

    logger.error("Wszystkie próby zapisu nie powiodły się")
    return False

def _perform_atomic_write(self, metadata_dict: Dict[str, Any], attempt: int) -> bool:
    """Wykonuje pojedynczą próbę atomic write."""
    metadata_path = self.get_metadata_path()
    lock_path = self.get_lock_path()
    metadata_dir = os.path.dirname(metadata_path)

    # Ensure directory exists
    os.makedirs(metadata_dir, exist_ok=True)

    # Dynamic timeout
    file_size = os.path.getsize(metadata_path) if os.path.exists(metadata_path) else 0
    lock_timeout = self._calculate_lock_timeout(file_size)
    lock = FileLock(lock_path, timeout=lock_timeout)
    temp_file_path = None

    try:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Próba zapisu metadanych do {metadata_path} (próba {attempt})")

        # Sprawdź czy mamy dane do zapisu
        if not metadata_dict:
            logger.error("Próba zapisu pustych metadanych!")
            return False

        # Sprawdź czy zawiera wymagane klucze
        required_keys = ["file_pairs", "unpaired_archives", "unpaired_previews", "has_special_folders"]
        for key in required_keys:
            if key not in metadata_dict:
                logger.error(f"Brak wymaganego klucza '{key}' w metadanych do zapisu")
                return False

        with lock:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Uzyskano blokadę dla {lock_path}")

            with tempfile.NamedTemporaryFile(
                mode="w",
                delete=False,
                encoding="utf-8",
                dir=metadata_dir,
                suffix=".tmp",
                prefix="metadata_",
            ) as temp_file:
                json.dump(metadata_dict, temp_file, ensure_ascii=False, indent=2)
                temp_file_path = temp_file.name
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Zapisano tymczasowy plik: {temp_file_path}")

            # Atomic move
            if not self._atomic_move_file(temp_file_path, metadata_path):
                return False

            # Sprawdź czy plik został faktycznie utworzony
            if os.path.exists(metadata_path):
                file_size = os.path.getsize(metadata_path)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Pomyślnie zapisano metadane do {metadata_path} (rozmiar: {file_size} bajtów)")
                return True
            else:
                logger.error(f"Plik metadanych nie istnieje po zapisie: {metadata_path}")
                return False

    except Exception as e:
        logger.error(f"Błąd podczas atomic write (próba {attempt}): {e}")
        raise
    finally:
        self._cleanup_temp_file(temp_file_path)
```

## Poprawka 2.5: Logging - Performance Optimization

### PROBLEM:

```python
# Linie 130-135 w metadata_io.py
logger.info(f"Próba zapisu metadanych do {metadata_path}")
logger.info(f"Uzyskano blokadę dla {lock_path}")
logger.info(f"Zapisano tymczasowy plik: {temp_file_path}")
```

### ROZWIĄZANIE:

```python
# Conditional logging dla lepszej wydajności
if logger.isEnabledFor(logging.DEBUG):
    logger.debug(f"Próba zapisu metadanych do {metadata_path}")
    logger.debug(f"Uzyskano blokadę dla {lock_path}")
    logger.debug(f"Zapisano tymczasowy plik: {temp_file_path}")
```

## Poprawka 2.6: Resource Management - Better Cleanup

### PROBLEM:

```python
# Linie 210-220 w metadata_io.py
finally:
    if temp_file_path and os.path.exists(temp_file_path):
        try:
            os.unlink(temp_file_path)
            logger.debug(f"Usunięto tymczasowy plik: {temp_file_path}")
        except OSError as e:
            logger.warning(
                f"Nie można usunąć tymczasowego pliku {temp_file_path}: {e}"
            )
```

### ROZWIĄZANIE:

```python
# Lepsze zarządzanie zasobami z retry cleanup
def _cleanup_temp_file(self, temp_file_path: str, max_retries: int = 3) -> None:
    """Usuwa tymczasowy plik z retry logic."""
    if not temp_file_path or not os.path.exists(temp_file_path):
        return

    for attempt in range(max_retries):
        try:
            os.unlink(temp_file_path)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Usunięto tymczasowy plik: {temp_file_path}")
            return
        except OSError as e:
            if attempt < max_retries - 1:
                time.sleep(0.1 * (2 ** attempt))
                continue
            else:
                logger.warning(f"Nie można usunąć tymczasowego pliku {temp_file_path} po {max_retries} próbach: {e}")

def _cleanup_temp_files_in_directory(self, directory: str) -> None:
    """Usuwa wszystkie tymczasowe pliki w katalogu."""
    try:
        for filename in os.listdir(directory):
            if filename.startswith("metadata_") and filename.endswith(".tmp"):
                temp_path = os.path.join(directory, filename)
                self._cleanup_temp_file(temp_path)
    except OSError as e:
        logger.warning(f"Błąd podczas czyszczenia tymczasowych plików w {directory}: {e}")
```

## Poprawka 2.7: File Size Optimization

### PROBLEM:

```python
# Linie 225-235 w metadata_io.py
def get_file_size(self) -> int:
    """
    Zwraca rozmiar pliku metadanych w bajtach.

    Returns:
        int: Rozmiar pliku lub 0 jeśli nie istnieje
    """
    metadata_path = self.get_metadata_path()
    try:
        if os.path.exists(metadata_path):
            return os.path.getsize(metadata_path)
        return 0
    except OSError:
        return 0
```

### ROZWIĄZANIE:

```python
# Zoptymalizowane sprawdzanie rozmiaru pliku
def get_file_size(self) -> int:
    """
    Zwraca rozmiar pliku metadanych w bajtach z cache.

    Returns:
        int: Rozmiar pliku lub 0 jeśli nie istnieje
    """
    if not hasattr(self, '_file_size_cache'):
        self._file_size_cache = {}

    metadata_path = self.get_metadata_path()
    current_time = time.time()

    # Sprawdź cache (TTL: 5 sekund)
    if metadata_path in self._file_size_cache:
        cached_size, cached_time = self._file_size_cache[metadata_path]
        if current_time - cached_time < 5.0:
            return cached_size

    try:
        if os.path.exists(metadata_path):
            file_size = os.path.getsize(metadata_path)
            self._file_size_cache[metadata_path] = (file_size, current_time)
            return file_size
        return 0
    except OSError:
        return 0

def _clear_file_size_cache(self) -> None:
    """Czyści cache rozmiaru pliku."""
    if hasattr(self, '_file_size_cache'):
        self._file_size_cache.clear()
```
