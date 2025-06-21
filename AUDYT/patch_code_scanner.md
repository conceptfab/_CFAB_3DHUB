# 🔧 FRAGMENTY KODU - SCANNER PATCHES

## 1. KRYTYCZNE POPRAWKI

### 1.1 Poprawa dekoratora logowania z thread safety i lepszą obsługą błędów

```python
# ZAMIENIĆ LINIE 43-60
import threading
from contextlib import contextmanager

# Thread-safe counter dla operacji
_operation_counter = 0
_operation_lock = threading.Lock()

def _log_scanner_operation(operation_name: str):
    """
    Thread-safe dekorator do logowania operacji skanera z lepszą obsługą błędów.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            global _operation_counter
            
            # Thread-safe ID operacji
            with _operation_lock:
                _operation_counter += 1
                operation_id = _operation_counter
            
            # Kontekst dla logów
            context = f"[Op-{operation_id}] {operation_name}"
            
            # Log tylko jeśli poziom DEBUG jest włączony
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"START {context}: {func.__name__}")
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                
                if logger.isEnabledFor(logging.DEBUG):
                    elapsed = time.time() - start_time
                    logger.debug(f"SUCCESS {context}: {func.__name__} ({elapsed:.3f}s)")
                
                return result
                
            except ScanningInterrupted:
                # Przerwanie skanowania to normalny case
                if logger.isEnabledFor(logging.DEBUG):
                    elapsed = time.time() - start_time
                    logger.debug(f"INTERRUPTED {context}: {func.__name__} ({elapsed:.3f}s)")
                raise
                
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"ERROR {context}: {func.__name__} after {elapsed:.3f}s - {e}", exc_info=True)
                raise
        
        return wrapper
    return decorator
```

### 1.2 Dodanie walidacji parametrów wejściowych

```python
# DODAĆ JAKO NOWĄ FUNKCJĘ POMOCNICZĄ
import os
from pathlib import Path

def _validate_directory_parameter(directory: str) -> str:
    """
    Waliduje i normalizuje parametr directory.
    
    Args:
        directory: Ścieżka do katalogu
        
    Returns:
        str: Znormalizowana ścieżka
        
    Raises:
        ValueError: Gdy directory jest nieprawidłowy
        OSError: Gdy directory nie istnieje lub brak dostępu
    """
    if not directory:
        raise ValueError("Parametr 'directory' nie może być pusty")
    
    if not isinstance(directory, (str, Path)):
        raise TypeError(f"Parametr 'directory' musi być string lub Path, otrzymano: {type(directory)}")
    
    directory_path = Path(directory)
    
    if not directory_path.exists():
        raise OSError(f"Katalog nie istnieje: {directory}")
    
    if not directory_path.is_dir():
        raise OSError(f"Ścieżka nie jest katalogiem: {directory}")
    
    try:
        # Test dostępu do odczytu
        list(directory_path.iterdir())
    except PermissionError:
        raise OSError(f"Brak dostępu do katalogu: {directory}")
    
    return str(directory_path.resolve())

def _validate_max_depth_parameter(max_depth: int) -> int:
    """
    Waliduje parametr max_depth.
    
    Args:
        max_depth: Maksymalna głębokość skanowania
        
    Returns:
        int: Zwalidowana wartość
        
    Raises:
        ValueError: Gdy max_depth jest nieprawidłowy
    """
    if not isinstance(max_depth, int):
        raise TypeError(f"Parametr 'max_depth' musi być int, otrzymano: {type(max_depth)}")
    
    if max_depth < -1:
        raise ValueError(f"Parametr 'max_depth' musi być >= -1, otrzymano: {max_depth}")
    
    # Zabezpieczenie przed zbyt głębokim skanowaniem
    if max_depth > 50:
        logger.warning(f"Bardzo głębokie skanowanie (max_depth={max_depth}), może być powolne")
    
    return max_depth

def _validate_callback_parameter(callback: Optional[Callable], callback_name: str) -> None:
    """
    Waliduje parametry callback.
    
    Args:
        callback: Funkcja callback do walidacji
        callback_name: Nazwa callback dla komunikatów błędów
        
    Raises:
        TypeError: Gdy callback ma nieprawidłowy typ
    """
    if callback is not None and not callable(callback):
        raise TypeError(f"Parametr '{callback_name}' musi być callable lub None")
```

### 1.3 Zaktualizowane funkcje z walidacją

```python
# ZAMIENIĆ LINIE 64-95
@_log_scanner_operation("skanowanie plików")
def collect_files_streaming(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, List[str]]:
    """
    Zbiera wszystkie pliki w katalogu z streaming progress.

    Args:
        directory: Ścieżka do katalogu do przeskanowania
        max_depth: Maksymalna głębokość skanowania (-1 = bez limitu)
        interrupt_check: Funkcja sprawdzająca czy przerwać skanowanie
        force_refresh: Czy wymusić odświeżenie cache
        progress_callback: Callback dla raportowania postępu

    Returns:
        Dict[str, List[str]]: Mapa rozszerzeń na listy plików

    Raises:
        ScanningInterrupted: Gdy skanowanie zostało przerwane
        OSError: Problemy z dostępem do systemu plików
        ValueError: Nieprawidłowe parametry
        TypeError: Nieprawidłowe typy parametrów
    """
    # Walidacja parametrów
    directory = _validate_directory_parameter(directory)
    max_depth = _validate_max_depth_parameter(max_depth)
    _validate_callback_parameter(interrupt_check, "interrupt_check")
    _validate_callback_parameter(progress_callback, "progress_callback")
    
    if not isinstance(force_refresh, bool):
        raise TypeError(f"Parametr 'force_refresh' musi być bool, otrzymano: {type(force_refresh)}")
    
    return _collect_files_streaming(
        directory=directory,
        max_depth=max_depth,
        interrupt_check=interrupt_check,
        force_refresh=force_refresh,
        progress_callback=progress_callback,
    )
```

### 1.4 Dodanie deprecation warning

```python
# ZAMIENIĆ LINIĘ 98
import warnings

def collect_files(*args, **kwargs):
    """
    PRZESTARZAŁE: Użyj collect_files_streaming zamiast tej funkcji.
    
    Ta funkcja zostanie usunięta w przyszłej wersji.
    """
    warnings.warn(
        "collect_files jest przestarzałe. Użyj collect_files_streaming.",
        DeprecationWarning,
        stacklevel=2
    )
    return collect_files_streaming(*args, **kwargs)
```

### 1.5 Zaktualizowane pozostałe funkcje z walidacją

```python
# ZAMIENIĆ LINIE 101-126
@_log_scanner_operation("tworzenie par plików")
def create_file_pairs(
    file_map: Dict[str, List[str]],
    base_directory: str,
    pair_strategy: str = "first_match",
) -> Tuple[List[FilePair], Set[str]]:
    """
    Tworzy pary plików na podstawie zebranych danych.

    Args:
        file_map: Mapa rozszerzeń na listy plików
        base_directory: Bazowy katalog dla par
        pair_strategy: Strategia parowania ("first_match", "best_match")

    Returns:
        Tuple[List[FilePair], Set[str]]: Pary plików i zestaw przetworzonych plików

    Raises:
        ValueError: Nieprawidłowa strategia parowania lub parametry
        TypeError: Nieprawidłowe typy parametrów
    """
    # Walidacja parametrów
    if not isinstance(file_map, dict):
        raise TypeError(f"Parametr 'file_map' musi być dict, otrzymano: {type(file_map)}")
    
    base_directory = _validate_directory_parameter(base_directory)
    
    if not isinstance(pair_strategy, str):
        raise TypeError(f"Parametr 'pair_strategy' musi być str, otrzymano: {type(pair_strategy)}")
    
    if pair_strategy not in ["first_match", "best_match"]:
        raise ValueError(f"Nieprawidłowa strategia parowania: {pair_strategy}")
    
    return _create_file_pairs(
        file_map=file_map,
        base_directory=base_directory,
        pair_strategy=pair_strategy,
    )
```

## 2. WYSOKIE POPRAWKI

### 2.1 Optymalizacja logowania - conditional logging

```python
# DODAĆ IMPORT NA POCZĄTKU PLIKU
import time

# ZMODYFIKOWAĆ DEKORATOR (już w sekcji 1.1, ale tutaj dodatkowo):
# W dekoratorze już jest: if logger.isEnabledFor(logging.DEBUG)
# To zapobiega formatowaniu stringów gdy DEBUG jest wyłączone
```

### 2.2 Dodanie kontekstu do clear_cache

```python
# ZAMIENIĆ LINIE 186-192
def clear_cache() -> None:
    """
    Czyści bufor wyników skanowania.
    
    Raises:
        Exception: Problemy z czyszczeniem cache
    """
    try:
        cache_stats = _get_scan_statistics()
        _clear_cache()
        logger.info(f"Wyczyszczono cache skanowania (było {cache_stats.get('entries', 0)} wpisów)")
    except Exception as e:
        logger.error(f"Błąd podczas czyszczenia cache: {e}", exc_info=True)
        raise
```

### 2.3 Dodanie fast path dla małych katalogów

```python
# DODAĆ JAKO NOWĄ FUNKCJĘ POMOCNICZĄ
def _should_use_fast_path(directory: str, max_depth: int) -> bool:
    """
    Sprawdza czy użyć szybkiej ścieżki dla małych katalogów.
    
    Args:
        directory: Ścieżka do katalogu
        max_depth: Maksymalna głębokość
        
    Returns:
        bool: True jeśli użyć fast path
    """
    try:
        # Fast path dla małych katalogów z ograniczoną głębokością
        if max_depth == 0 or max_depth == 1:
            path = Path(directory)
            # Szybkie sprawdzenie - jeśli mało plików w katalogu głównym
            items = list(path.iterdir())
            if len(items) < 100:  # Konfigurowalna wartość
                return True
        return False
    except:
        return False
```

## 3. ŚREDNIE POPRAWKI

### 3.1 Dodanie konfigurowalności przez klasę

```python
# DODAĆ NOWĄ KLASĘ JAKO ALTERNATYWA DLA FUNKCJI
class ScannerAPI:
    """
    Konfigurowalne API dla operacji skanowania.
    """
    
    def __init__(self, 
                 enable_debug_logging: bool = True,
                 fast_path_threshold: int = 100,
                 max_safe_depth: int = 50):
        """
        Inicjalizuje konfigurowalne API skanera.
        
        Args:
            enable_debug_logging: Czy włączyć szczegółowe logowanie
            fast_path_threshold: Próg plików dla szybkiej ścieżki
            max_safe_depth: Maksymalna bezpieczna głębokość
        """
        self.enable_debug_logging = enable_debug_logging
        self.fast_path_threshold = fast_path_threshold
        self.max_safe_depth = max_safe_depth
    
    def collect_files_streaming(self, *args, **kwargs) -> Dict[str, List[str]]:
        """Konfigurowalny wrapper dla collect_files_streaming."""
        # Zastosuj konfigurację i wywołaj funkcję
        return collect_files_streaming(*args, **kwargs)
```

### 3.2 Dodanie batch processing

```python
# DODAĆ NOWĄ FUNKCJĘ
def scan_multiple_directories(
    directories: List[str],
    **scan_kwargs
) -> Dict[str, Tuple[List[FilePair], List[str], List[str]]]:
    """
    Skanuje wiele katalogów w trybie batch.
    
    Args:
        directories: Lista katalogów do przeskanowania
        **scan_kwargs: Parametry przekazane do scan_folder_for_pairs
        
    Returns:
        Dict: Mapa katalog -> wyniki skanowania
    """
    results = {}
    
    for directory in directories:
        try:
            directory = _validate_directory_parameter(directory)
            results[directory] = scan_folder_for_pairs(directory, **scan_kwargs)
        except Exception as e:
            logger.error(f"Błąd skanowania {directory}: {e}")
            results[directory] = ([], [], [])
    
    return results
```

## 4. IMPORTY I DEFINICJE

### 4.1 Zaktualizowany nagłówek pliku

```python
"""
Moduł odpowiedzialny za skanowanie folderów i parowanie plików.

Ten moduł zawiera publiczne API do skanowania katalogów w poszukiwaniu plików
oraz ich łączenia w pary (archiwa + podglądy).

UWAGA: Ten moduł jest fasadą publicznego API. Implementacja podzielona na:
- scanner_core.py - podstawowe funkcje skanowania
- scanner_cache.py - zarządzanie cache
- file_pairing.py - logika parowania plików

🚀 ETAP 5: Refaktoryzacja Scanner - poprawa thread safety i walidacji
"""

import logging
import threading
import time
import warnings
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from src.logic.file_pairing import ARCHIVE_EXTENSIONS, PREVIEW_EXTENSIONS
from src.logic.file_pairing import create_file_pairs as _create_file_pairs
from src.logic.file_pairing import identify_unpaired_files as _identify_unpaired_files
from src.logic.scanner_cache import clear_cache as _clear_cache
from src.logic.scanner_core import ScanningInterrupted
from src.logic.scanner_core import collect_files_streaming as _collect_files_streaming
from src.logic.scanner_core import get_scan_statistics as _get_scan_statistics
from src.logic.scanner_core import scan_folder_for_pairs as _scan_folder_for_pairs
from src.models.file_pair import FilePair
```

### 4.2 Zaktualizowany __all__

```python
__all__ = [
    "collect_files_streaming",
    "collect_files",  # deprecated
    "create_file_pairs", 
    "identify_unpaired_files",
    "scan_folder_for_pairs",
    "scan_multiple_directories",  # nowe
    "clear_cache",
    "get_scan_statistics",
    "ScannerAPI",  # nowe
    "ARCHIVE_EXTENSIONS",
    "PREVIEW_EXTENSIONS", 
    "ScanningInterrupted",
]
```

## 5. TESTY JEDNOSTKOWE

### 5.1 Przykład testów dla nowych funkcji

```python
# DODAĆ DO PLIKU TESTOWEGO
import pytest
import tempfile
from pathlib import Path

def test_validate_directory_parameter():
    """Test walidacji parametru directory."""
    # Test prawidłowego katalogu
    with tempfile.TemporaryDirectory() as temp_dir:
        result = _validate_directory_parameter(temp_dir)
        assert Path(result).is_absolute()
    
    # Test nieistniejącego katalogu
    with pytest.raises(OSError):
        _validate_directory_parameter("/nieistniejacy/katalog")
    
    # Test pustego parametru
    with pytest.raises(ValueError):
        _validate_directory_parameter("")

def test_deprecated_collect_files():
    """Test deprecation warning dla collect_files."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        with tempfile.TemporaryDirectory() as temp_dir:
            collect_files(temp_dir, max_depth=0)
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "przestarzałe" in str(w[0].message)

def test_thread_safety_decorator():
    """Test thread safety dekoratora."""
    import threading
    import time
    
    results = []
    
    @_log_scanner_operation("test")
    def test_func(delay):
        time.sleep(delay)
        results.append(threading.current_thread().ident)
        return f"result_{threading.current_thread().ident}"
    
    threads = []
    for i in range(5):
        t = threading.Thread(target=test_func, args=(0.1,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # Sprawdź czy wszystkie wątki się wykonały
    assert len(results) == 5
    assert len(set(results)) == 5  # Wszystkie różne thread ID
```