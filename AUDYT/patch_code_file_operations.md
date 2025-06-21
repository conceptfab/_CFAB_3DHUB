# 🔧 FRAGMENTY KODU - FILE_OPERATIONS PATCHES

## 1. KRYTYCZNE POPRAWKI

### 1.1 Zastąpienie globalnych singleton'ów thread-safe factory pattern

```python
# ZAMIENIĆ LINIE 29-33
import threading
from typing import Dict, Any, Optional
from contextlib import contextmanager

class FileOperationsManager:
    """
    Thread-safe manager dla operacji na plikach.
    Zastępuje globalne singleton'y.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._local = threading.local()
            self.logger = logging.getLogger(__name__)
    
    def _get_file_opener(self):
        """Pobiera thread-local instancję FileOpener."""
        if not hasattr(self._local, 'file_opener'):
            self._local.file_opener = FileOpener()
        return self._local.file_opener
    
    def _get_file_system_ops(self):
        """Pobiera thread-local instancję FileSystemOperations."""
        if not hasattr(self._local, 'file_system_ops'):
            self._local.file_system_ops = FileSystemOperations()
        return self._local.file_system_ops
    
    def _get_file_pair_ops(self):
        """Pobiera thread-local instancję FilePairOperations."""
        if not hasattr(self._local, 'file_pair_ops'):
            self._local.file_pair_ops = FilePairOperations()
        return self._local.file_pair_ops

# Globalna instancja manager'a
_operations_manager = FileOperationsManager()
```

### 1.2 Dodanie walidacji parametrów

```python
# DODAĆ JAKO NOWE FUNKCJE POMOCNICZE
import os
from pathlib import Path

def _validate_file_path(file_path: str, must_exist: bool = True) -> str:
    """
    Waliduje ścieżkę do pliku.
    
    Args:
        file_path: Ścieżka do pliku
        must_exist: Czy plik musi istnieć
        
    Returns:
        str: Znormalizowana ścieżka
        
    Raises:
        ValueError: Nieprawidłowa ścieżka
        FileNotFoundError: Plik nie istnieje (gdy must_exist=True)
    """
    if not file_path or not isinstance(file_path, (str, Path)):
        raise ValueError(f"Nieprawidłowa ścieżka do pliku: {file_path}")
    
    file_path = str(Path(file_path).resolve())
    
    if must_exist and not os.path.exists(file_path):
        raise FileNotFoundError(f"Plik nie istnieje: {file_path}")
    
    if must_exist and not os.path.isfile(file_path):
        raise ValueError(f"Ścieżka nie wskazuje na plik: {file_path}")
    
    return file_path

def _validate_directory_path(directory_path: str, must_exist: bool = True) -> str:
    """
    Waliduje ścieżkę do katalogu.
    
    Args:
        directory_path: Ścieżka do katalogu
        must_exist: Czy katalog musi istnieć
        
    Returns:
        str: Znormalizowana ścieżka
        
    Raises:
        ValueError: Nieprawidłowa ścieżka
        FileNotFoundError: Katalog nie istnieje (gdy must_exist=True)
    """
    if not directory_path or not isinstance(directory_path, (str, Path)):
        raise ValueError(f"Nieprawidłowa ścieżka do katalogu: {directory_path}")
    
    directory_path = str(Path(directory_path).resolve())
    
    if must_exist and not os.path.exists(directory_path):
        raise FileNotFoundError(f"Katalog nie istnieje: {directory_path}")
    
    if must_exist and not os.path.isdir(directory_path):
        raise ValueError(f"Ścieżka nie wskazuje na katalog: {directory_path}")
    
    return directory_path

def _validate_file_pair(file_pair: Any) -> FilePair:
    """
    Waliduje obiekt FilePair.
    
    Args:
        file_pair: Obiekt do walidacji
        
    Returns:
        FilePair: Zwalidowany obiekt
        
    Raises:
        TypeError: Nieprawidłowy typ
        ValueError: Nieprawidłowy stan obiektu
    """
    if not isinstance(file_pair, FilePair):
        raise TypeError(f"Oczekiwano FilePair, otrzymano: {type(file_pair)}")
    
    if not file_pair.archive_path or not file_pair.preview_path:
        raise ValueError("FilePair musi mieć zdefiniowane archive_path i preview_path")
    
    return file_pair

def _validate_folder_name(folder_name: str) -> str:
    """
    Waliduje nazwę folderu.
    
    Args:
        folder_name: Nazwa folderu
        
    Returns:
        str: Zwalidowana nazwa
        
    Raises:
        ValueError: Nieprawidłowa nazwa
    """
    if not folder_name or not isinstance(folder_name, str):
        raise ValueError(f"Nieprawidłowa nazwa folderu: {folder_name}")
    
    if not is_valid_filename(folder_name):
        raise ValueError(f"Nazwa folderu zawiera niedozwolone znaki: {folder_name}")
    
    return folder_name.strip()
```

### 1.3 Implementacja proper error handling

```python
# DECORATOR DLA ERROR HANDLING
def _handle_file_operation_errors(operation_name: str):
    """
    Dekorator dla obsługi błędów w operacjach na plikach.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                logger.debug(f"Rozpoczynanie operacji: {operation_name}")
                result = func(*args, **kwargs)
                logger.debug(f"Zakończono operację: {operation_name}")
                return result
                
            except (ValueError, TypeError, FileNotFoundError) as e:
                logger.error(f"Błąd walidacji w {operation_name}: {e}")
                raise
                
            except PermissionError as e:
                logger.error(f"Brak uprawnień w {operation_name}: {e}")
                raise
                
            except OSError as e:
                logger.error(f"Błąd systemu plików w {operation_name}: {e}")
                raise
                
            except Exception as e:
                logger.error(f"Nieoczekiwany błąd w {operation_name}: {e}", exc_info=True)
                raise RuntimeError(f"Operacja {operation_name} nie powiodła się: {e}") from e
        
        return wrapper
    return decorator
```

### 1.4 Zrefaktoryzowane funkcje z walidacją i error handling

```python
# ZAMIENIĆ LINIE 40-52
@_handle_file_operation_errors("otwieranie archiwum")
def open_archive_externally(archive_path: str) -> bool:
    """
    Otwiera plik archiwum w domyślnym programie systemowym.
    ZREFAKTORYZOWANY - z walidacją i error handling.

    Args:
        archive_path: Ścieżka do pliku archiwum

    Returns:
        True jeśli operacja się powiodła
        
    Raises:
        ValueError: Nieprawidłowa ścieżka
        FileNotFoundError: Plik nie istnieje
        PermissionError: Brak uprawnień
        RuntimeError: Nieoczekiwany błąd
    """
    archive_path = _validate_file_path(archive_path, must_exist=True)
    file_opener = _operations_manager._get_file_opener()
    return file_opener.open_archive_externally(archive_path)
```

```python
# ZAMIENIĆ LINIE 85-104
@_handle_file_operation_errors("tworzenie folderu")
def create_folder(
    parent_directory: str, folder_name: str, worker_factory=None
) -> Optional[CreateFolderWorkerInterface]:
    """
    Tworzy nowy folder w podanej lokalizacji.
    ZREFAKTORYZOWANY - z walidacją i error handling.

    Args:
        parent_directory: Ścieżka do katalogu nadrzędnego
        folder_name: Nazwa nowego folderu
        worker_factory: DEPRECATED - nie używane (fabryka jest centralna)

    Returns:
        Worker lub None w przypadku błędu
        
    Raises:
        ValueError: Nieprawidłowe parametry
        FileNotFoundError: Katalog nadrzędny nie istnieje
        PermissionError: Brak uprawnień
        RuntimeError: Nieoczekiwany błąd
    """
    parent_directory = _validate_directory_path(parent_directory, must_exist=True)
    folder_name = _validate_folder_name(folder_name)
    
    if worker_factory is not None:
        logger.debug("Parametr worker_factory jest przestarzały - używam centralnej fabryki")

    file_system_ops = _operations_manager._get_file_system_ops()
    return file_system_ops.create_folder(parent_directory, folder_name)
```

## 2. WYSOKIE POPRAWKI

### 2.1 Optymalizacja logowania deprecated warnings

```python
# DODAĆ NA POCZĄTKU PLIKU
import warnings
from functools import lru_cache

@lru_cache(maxsize=100)
def _log_deprecated_parameter_once(function_name: str) -> None:
    """
    Loguje ostrzeżenie o deprecated parametrze tylko raz dla każdej funkcji.
    """
    message = f"Parametr 'worker_factory' w {function_name} jest przestarzały - używam centralnej fabryki"
    logger.debug(message)
    warnings.warn(
        f"worker_factory parameter in {function_name} is deprecated",
        DeprecationWarning,
        stacklevel=3
    )

# ZAMIENIĆ WSZYSTKIE SPRAWDZENIA worker_factory
def _handle_deprecated_worker_factory(worker_factory, function_name: str) -> None:
    """Obsługuje deprecated parametr worker_factory."""
    if worker_factory is not None:
        _log_deprecated_parameter_once(function_name)
```

### 2.2 Dodanie batch operations support

```python
# DODAĆ NOWE FUNKCJE BATCH
from typing import List, Tuple, Callable

def batch_delete_file_pairs(
    file_pairs: List[FilePair],
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[Tuple[FilePair, bool, Optional[str]]]:
    """
    Usuwa wiele par plików w operacji batch.
    
    Args:
        file_pairs: Lista par plików do usunięcia
        progress_callback: Callback dla postępu (current, total)
        
    Returns:
        Lista tupli (file_pair, success, error_message)
    """
    results = []
    total = len(file_pairs)
    
    for i, file_pair in enumerate(file_pairs):
        try:
            file_pair = _validate_file_pair(file_pair)
            worker = delete_file_pair(file_pair)
            results.append((file_pair, worker is not None, None))
        except Exception as e:
            results.append((file_pair, False, str(e)))
        
        if progress_callback:
            progress_callback(i + 1, total)
    
    return results

def batch_move_file_pairs(
    file_pairs: List[FilePair],
    target_directory: str,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[Tuple[FilePair, bool, Optional[str]]]:
    """
    Przenosi wiele par plików w operacji batch.
    
    Args:
        file_pairs: Lista par plików do przeniesienia
        target_directory: Katalog docelowy
        progress_callback: Callback dla postępu (current, total)
        
    Returns:
        Lista tupli (file_pair, success, error_message)
    """
    target_directory = _validate_directory_path(target_directory, must_exist=True)
    results = []
    total = len(file_pairs)
    
    for i, file_pair in enumerate(file_pairs):
        try:
            file_pair = _validate_file_pair(file_pair)
            worker = move_file_pair(file_pair, target_directory)
            results.append((file_pair, worker is not None, None))
        except Exception as e:
            results.append((file_pair, False, str(e)))
        
        if progress_callback:
            progress_callback(i + 1, total)
    
    return results
```

### 2.3 Naprawka module-level logging

```python
# ZAMIENIĆ LINIĘ 265
# Usunąć: logger.info("File operations module refactored - using specialized classes")

# DODAĆ NA KOŃCU PLIKU
def _initialize_module():
    """Inicjalizuje moduł - wywoływane przy pierwszym użyciu."""
    logger.debug("File operations module initialized - using specialized classes")

# Lazy initialization
_module_initialized = False

def _ensure_module_initialized():
    """Zapewnia że moduł jest zainicjalizowany."""
    global _module_initialized
    if not _module_initialized:
        _initialize_module()
        _module_initialized = True

# DODAĆ NA POCZĄTKU KAŻDEJ FUNKCJI PUBLICZNEJ
_ensure_module_initialized()
```

## 3. ŚREDNIE POPRAWKI

### 3.1 Dodanie deprecation warnings dla aliases

```python
# ZAMIENIĆ LINIE 262-263
def open_file(*args, **kwargs):
    """
    PRZESTARZAŁE: Użyj open_file_externally zamiast tej funkcji.
    
    Ta funkcja zostanie usunięta w przyszłej wersji.
    """
    warnings.warn(
        "open_file jest przestarzałe. Użyj open_file_externally.",
        DeprecationWarning,
        stacklevel=2
    )
    return open_file_externally(*args, **kwargs)

def open_folder(*args, **kwargs):
    """
    PRZESTARZAŁE: Użyj open_folder_externally zamiast tej funkcji.
    
    Ta funkcja zostanie usunięta w przyszłej wersji.
    """
    warnings.warn(
        "open_folder jest przestarzałe. Użyj open_folder_externally.",
        DeprecationWarning,
        stacklevel=2
    )
    return open_folder_externally(*args, **kwargs)
```

### 3.2 Context Manager Pattern dla resource management

```python
# DODAĆ NOWĄ KLASĘ
@contextmanager
def file_operations_context():
    """
    Context manager dla operacji na plikach.
    Zapewnia proper cleanup zasobów.
    """
    manager = FileOperationsManager()
    try:
        yield manager
        logger.debug("Operacje na plikach zakończone pomyślnie")
    except Exception as e:
        logger.error(f"Błąd podczas operacji na plikach: {e}")
        raise
    finally:
        # Cleanup resources if needed
        if hasattr(manager._local, 'file_opener'):
            del manager._local.file_opener
        if hasattr(manager._local, 'file_system_ops'):
            del manager._local.file_system_ops
        if hasattr(manager._local, 'file_pair_ops'):
            del manager._local.file_pair_ops

# PRZYKŁAD UŻYCIA
def safe_file_operation(operation_func, *args, **kwargs):
    """
    Bezpieczne wykonanie operacji na plikach z proper resource management.
    """
    with file_operations_context() as ops_manager:
        return operation_func(*args, **kwargs)
```

## 4. ZAKTUALIZOWANY NAGŁÓWEK PLIKU

### 4.1 Nowe importy i definicje

```python
"""
Zrefaktoryzowane operacje na plikach - thread-safe fasada dla klas specjalistycznych.
🚀 ETAP 6: Refaktoryzacja File Operations - thread safety, walidacja, error handling
"""

import logging
import os
import shutil
import threading
import warnings
from contextlib import contextmanager
from functools import wraps, lru_cache
from pathlib import Path
from typing import Optional, List, Tuple, Callable, Any

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from src.interfaces.worker_interface import (
    CreateFolderWorkerInterface,
    DeleteFilePairWorkerInterface,
    DeleteFolderWorkerInterface,
    ManuallyPairFilesWorkerInterface,
    MoveFilePairWorkerInterface,
    RenameFilePairWorkerInterface,
    RenameFolderWorkerInterface,
)
from src.logic.file_ops_components.file_opener import FileOpener
from src.logic.file_ops_components.file_pair_operations import FilePairOperations
from src.logic.file_ops_components.file_system_operations import FileSystemOperations
from src.models.file_pair import FilePair
from src.utils.path_utils import is_valid_filename, normalize_path

logger = logging.getLogger(__name__)
```

### 4.2 Zaktualizowany __all__

```python
__all__ = [
    # Operacje otwierania plików
    'open_archive_externally',
    'open_file_externally', 
    'open_folder_externally',
    
    # Operacje na systemie plików
    'create_folder',
    'rename_folder',
    'delete_folder',
    
    # Operacje na parach plików
    'manually_pair_files',
    'create_pair_from_files',
    'rename_file_pair',
    'delete_file_pair',
    'move_file_pair',
    
    # Batch operations
    'batch_delete_file_pairs',
    'batch_move_file_pairs',
    
    # Context managers
    'file_operations_context',
    
    # Backward compatibility (deprecated)
    'open_file',
    'open_folder',
    
    # Thread-safe manager
    'FileOperationsManager',
]
```

## 5. TESTY JEDNOSTKOWE

### 5.1 Przykład testów dla nowych funkcji

```python
# DODAĆ DO PLIKU TESTOWEGO
import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

def test_thread_safety():
    """Test thread safety manager'a."""
    results = []
    errors = []
    
    def worker(worker_id):
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                result = create_folder(temp_dir, f"test_folder_{worker_id}")
                results.append((worker_id, result is not None))
        except Exception as e:
            errors.append((worker_id, str(e)))
    
    threads = []
    for i in range(10):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    assert len(errors) == 0, f"Błędy w wątkach: {errors}"
    assert len(results) == 10, f"Nie wszystkie wątki się wykonały: {len(results)}"

def test_parameter_validation():
    """Test walidacji parametrów."""
    # Test nieprawidłowej ścieżki
    with pytest.raises(ValueError):
        open_archive_externally("")
    
    with pytest.raises(FileNotFoundError):
        open_archive_externally("/nieistniejacy/plik.zip")
    
    # Test nieprawidłowej nazwy folderu
    with pytest.raises(ValueError):
        create_folder("/tmp", "")
    
    with pytest.raises(ValueError):
        create_folder("/tmp", "folder<>:|")

def test_deprecated_warnings():
    """Test deprecated warnings."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.touch()
            
            # Test deprecated alias
            open_file(str(test_file))
            
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "przestarzałe" in str(w[0].message)

def test_batch_operations():
    """Test operacji batch."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Utwórz test file pairs
        file_pairs = []
        for i in range(3):
            archive = Path(temp_dir) / f"archive_{i}.zip"
            preview = Path(temp_dir) / f"preview_{i}.jpg"
            archive.touch()
            preview.touch()
            
            pair = FilePair(archive_path=str(archive), preview_path=str(preview))
            file_pairs.append(pair)
        
        # Test batch delete
        results = batch_delete_file_pairs(file_pairs)
        
        assert len(results) == 3
        for pair, success, error in results:
            assert isinstance(pair, FilePair)
            assert isinstance(success, bool)
```