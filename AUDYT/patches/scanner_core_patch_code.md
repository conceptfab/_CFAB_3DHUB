# PATCH-CODE DLA: scanner_core.py

**Powiązany plik z analizą:** `../corrections/scanner_core_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: USUNIĘCIE DEAD CODE - FUNKCJA find_special_folders

**Problem:** Funkcja `find_special_folders` (linie 575-587) tylko zwraca [] - dead code
**Rozwiązanie:** Całkowite usunięcie funkcji

```python
# USUŃ CAŁĄ FUNKCJĘ (linie 575-587):
# def find_special_folders(folder_path: str) -> List[SpecialFolder]:
#     """
#     USUNIĘTA FUNKCJA - Foldery specjalne są teraz pobierane z metadanych.
#     Ta funkcja pozostaje jako zaślepka dla kompatybilności wstecznej.
#     """
#     logger.debug("find_special_folders: Funkcja zastąpiona przez metadane")
#     return []

# Funkcja całkowicie usunięta - sprawdź czy nie jest używana nigdzie w kodzie
```

---

### PATCH 2: OPTYMALIZACJA PERFORMANCE - REDUKCJA DEBUG LOGÓW W HOT PATH

**Problem:** Debug logi w każdej iteracji spowalniają skanowanie o 20-30%
**Rozwiązanie:** Conditional logging + batch logging

```python
def _walk_directory_streaming(current_dir: str, depth: int = 0):
    nonlocal total_folders_scanned, total_files_found
    
    # ... kod przed linią 466 bez zmian ...
    
    # OPTYMALIZACJA: debug log tylko co 50 folderów zamiast każdy
    if total_folders_scanned % 50 == 0 and logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"Batch progress: {total_folders_scanned} folderów, "
            f"{total_files_found} plików"
        )
    
    # USUNIĘTO: 
    # logger.debug(f"Skanowanie: {current_dir} -> {files_processed_in_folder} plików")
    
    # ... reszta kodu bez zmian ...
```

---

### PATCH 3: PERFORMANCE OPTIMIZATION - BATCH PROGRESS CALLBACKS

**Problem:** Progress callback co folder/plik spowalnia skanowanie
**Rozwiązanie:** Batch progress updates co 25 folderów

```python
def _walk_directory_streaming(current_dir: str, depth: int = 0):
    nonlocal total_folders_scanned, total_files_found
    
    # ... kod przed progress callback ...
    
    # OPTYMALIZACJA: Progress callback co 25 folderów zamiast każdy
    if progress_callback and total_folders_scanned % 25 == 0:
        # Progress oparty na liczbie przeskanowanych folderów
        progress = min(95, total_folders_scanned * 2)
        progress_callback(
            progress,
            f"Skanowanie: {total_files_found} plików, {total_folders_scanned} folderów"
        )
    
    # ... reszta kodu bez zmian ...
```

---

### PATCH 4: REFACTORING - PODZIAŁ collect_files_streaming NA MNIEJSZE FUNKCJE

**Problem:** Funkcja 587 linii ze złożonością C - zbyt kompleksowa
**Rozwiązanie:** Wydzielenie logiki do osobnych funkcji

```python
def _validate_directory_for_scanning(directory: str) -> bool:
    """Waliduje katalog przed skanowaniem."""
    normalized_dir = normalize_path(directory)
    
    if not path_exists(normalized_dir) or not os.path.isdir(normalized_dir):
        logger.warning(f"Katalog {normalized_dir} nie istnieje lub nie jest katalogiem")
        return False
    return True


def _check_cache_for_files(directory: str, force_refresh: bool) -> Optional[Dict[str, List[str]]]:
    """Sprawdza cache dla plików."""
    if not force_refresh:
        cached_file_map = cache.get_file_map(directory)
        if cached_file_map is not None:
            logger.debug(f"CACHE HIT: używam buforowanych plików dla {directory}")
            return cached_file_map
    return None


def _process_single_file(entry, current_dir: str, file_map: defaultdict) -> bool:
    """Przetwarza pojedynczy plik. Returns True jeśli plik został przetworzony."""
    if not entry.is_file():
        return False
    
    name = entry.name
    base_name, ext = os.path.splitext(name)
    ext_lower = ext.lower()

    if ext_lower in ARCHIVE_EXTENSIONS or ext_lower in PREVIEW_EXTENSIONS:
        map_key = os.path.join(normalize_path(current_dir), base_name.lower())
        full_file_path = normalize_path(os.path.join(current_dir, name))
        file_map[map_key].append(full_file_path)
        return True
    return False


def collect_files_streaming(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None,
    force_refresh: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, List[str]]:
    """
    Zbiera wszystkie pliki w katalogu z streaming progress.
    ZREFAKTORYZOWANA WERSJA - podział na mniejsze funkcje.
    """
    normalized_dir = normalize_path(directory)

    # 1. Sprawdź cache
    cached_result = _check_cache_for_files(normalized_dir, force_refresh)
    if cached_result is not None:
        if progress_callback:
            progress_callback(100, f"Używam cache dla {normalized_dir}")
        return cached_result

    # 2. Waliduj katalog
    if not _validate_directory_for_scanning(normalized_dir):
        if progress_callback:
            progress_callback(100, f"Katalog {normalized_dir} nie istnieje")
        return {}

    logger.info(f"Rozpoczęto streaming zbieranie plików z katalogu: {normalized_dir}")
    if progress_callback:
        progress_callback(0, f"Rozpoczynam streaming skanowanie: {normalized_dir}")

    file_map = defaultdict(list)
    total_folders_scanned = 0
    total_files_found = 0
    start_time = time.time()
    visited_dirs = set()

    def _walk_directory_streaming(current_dir: str, depth: int = 0):
        nonlocal total_folders_scanned, total_files_found

        # Sprawdzenie przerwania
        if interrupt_check and interrupt_check():
            logger.warning("Skanowanie przerwane przez użytkownika")
            raise ScanningInterrupted("Skanowanie przerwane przez użytkownika")

        # Limit głębokości
        if max_depth >= 0 and depth > max_depth:
            return

        # Batch progress updates (co 25 folderów)
        if progress_callback and total_folders_scanned % 25 == 0:
            progress = min(95, total_folders_scanned * 2)
            progress_callback(
                progress,
                f"Skanowanie: {total_files_found} plików, {total_folders_scanned} folderów"
            )

        # Zabezpieczenie przed pętlami
        normalized_current = os.path.realpath(current_dir)
        if normalized_current in visited_dirs:
            logger.warning(f"Wykryto pętlę w katalogach: {normalized_current}")
            return
        visited_dirs.add(normalized_current)

        try:
            total_folders_scanned += 1
            entries = list(os.scandir(current_dir))

            if interrupt_check and interrupt_check():
                raise ScanningInterrupted("Skanowanie przerwane podczas odczytu zawartości folderu")

            # Przetwarzanie plików
            files_processed_in_folder = 0
            for entry in entries:
                if _process_single_file(entry, current_dir, file_map):
                    total_files_found += 1
                    files_processed_in_folder += 1

                # Sprawdzenie przerwania co 20 plików (mniej frequent)
                if (files_processed_in_folder % 20 == 0 
                    and interrupt_check and interrupt_check()):
                    raise ScanningInterrupted(f"Skanowanie przerwane w {current_dir}")

            # Batch debug logging (co 50 folderów)
            if total_folders_scanned % 50 == 0 and logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Batch: {total_folders_scanned} folderów, {total_files_found} plików")

            # Rekursywne skanowanie podfolderów (tylko jeśli folder ma pliki)
            if files_processed_in_folder > 0:
                for entry in entries:
                    if entry.is_dir() and not should_ignore_folder(entry.name):
                        _walk_directory_streaming(entry.path, depth + 1)

        except (PermissionError, OSError) as e:
            logger.warning(f"Błąd dostępu do {current_dir}: {e}")
        except ScanningInterrupted:
            raise

    # Wykonaj skanowanie
    try:
        _walk_directory_streaming(normalized_dir)
    except ScanningInterrupted as e:
        logger.info(f"Skanowanie przerwane: {e}")
        # Zwróć częściowe wyniki
    
    # Finalizacja
    scan_duration = time.time() - start_time
    logger.info(
        f"Streaming zakończone dla {normalized_dir}. "
        f"Znaleziono {total_files_found} plików w {total_folders_scanned} folderach "
        f"w {scan_duration:.2f}s"
    )

    if progress_callback:
        progress_callback(100, f"Zakończono: {total_files_found} plików")

    # Cache wynik
    dict_result = dict(file_map)
    cache.set_file_map(normalized_dir, dict_result)

    return dict_result
```

---

### PATCH 5: UPROSZCZENIE OVER-ENGINEERED KLAS

**Problem:** Zbyt skomplikowane klasy dla prostej funkcji skanowania
**Rozwiązanie:** Opcjonalne uproszczenie (po weryfikacji użycia)

```python
# OPCJONALNIE: Uproszczenie ScanConfig jeśli używany tylko wewnętrznie
@dataclass 
class SimpleScanConfig:
    """Uproszczona konfiguracja skanowania."""
    directory: str
    max_depth: int = -1
    use_cache: bool = True
    pair_strategy: str = "first_match"
    
    def __post_init__(self):
        self.directory = normalize_path(self.directory)

# Można zastąpić ScanConfig -> SimpleScanConfig jeśli nie ma external usage
```

---

### PATCH 6: MEMORY OPTIMIZATION - GENERATOR PATTERN

**Problem:** Duże foldery mogą powodować high memory usage
**Rozwiązanie:** Optional generator version dla bardzo dużych folderów

```python
def collect_files_generator(
    directory: str,
    max_depth: int = -1,
    interrupt_check: Optional[Callable[[], bool]] = None
) -> Generator[Tuple[str, str], None, None]:
    """
    Generator version dla bardzo dużych folderów - zwraca (map_key, file_path).
    OPCJONALNE - do użycia dla extreme cases.
    """
    normalized_dir = normalize_path(directory)
    
    if not _validate_directory_for_scanning(normalized_dir):
        return
    
    visited_dirs = set()
    
    def _walk_generator(current_dir: str, depth: int = 0):
        if interrupt_check and interrupt_check():
            return
            
        if max_depth >= 0 and depth > max_depth:
            return
            
        normalized_current = os.path.realpath(current_dir)
        if normalized_current in visited_dirs:
            return
        visited_dirs.add(normalized_current)
        
        try:
            for entry in os.scandir(current_dir):
                if entry.is_file():
                    name = entry.name
                    base_name, ext = os.path.splitext(name)
                    ext_lower = ext.lower()
                    
                    if ext_lower in ARCHIVE_EXTENSIONS or ext_lower in PREVIEW_EXTENSIONS:
                        map_key = os.path.join(normalize_path(current_dir), base_name.lower())
                        full_file_path = normalize_path(os.path.join(current_dir, name))
                        yield (map_key, full_file_path)
                        
                elif entry.is_dir() and not should_ignore_folder(entry.name):
                    yield from _walk_generator(entry.path, depth + 1)
                    
        except (PermissionError, OSError):
            pass
    
    yield from _walk_generator(normalized_dir)
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - skanowanie folderów działa identycznie
- [ ] **API kompatybilność** - funkcje `scan_folder`, `collect_files_streaming` unchanged
- [ ] **Obsługa błędów** - wszystkie error scenarios działają
- [ ] **Walidacja danych** - parametry funkcji poprawnie walidowane
- [ ] **Logowanie** - logi działają ale z lepszą wydajnością
- [ ] **Konfiguracja** - ScanConfig działa jeśli zachowany
- [ ] **Cache** - cache system działa poprawnie
- [ ] **Thread safety** - kod thread-safe (sprawdzić concurrent access)
- [ ] **Memory management** - brak memory leaks w długich skanowaniach
- [ ] **Performance** - **TARGET: 20-30% IMPROVEMENT**

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - wszystkie imports działają
- [ ] **Zależności zewnętrzne** - file_pairing, metadata_manager, scanner_cache
- [ ] **Zależności wewnętrzne** - wszystkie moduły używające scanner_core
- [ ] **Cykl zależności** - brak nowych cykli
- [ ] **Backward compatibility** - API niezmieniony
- [ ] **Interface contracts** - signatures funkcji zachowane
- [ ] **Event handling** - interrupt_check działa
- [ ] **Signal/slot connections** - progress_callback działa
- [ ] **File I/O** - skanowanie różnych typów plików/folderów

#### **TESTY WERYFIKACYJNE - KRYTYCZNE:**

- [ ] **Test jednostkowy** - każda nowa funkcja helper
- [ ] **Test integracyjny** - pełny workflow skanowania
- [ ] **Test regresyjny** - porównanie wyników przed/po
- [ ] **Test wydajnościowy** - **MEASUREMENT MANDATORY**

#### **SPECJALNE TESTY DLA SCANNER_CORE:**

- [ ] **Performance baseline** - pomiar czasu przed zmianami
- [ ] **Performance post-refactor** - pomiar czasu po zmianach
- [ ] **Memory usage test** - sprawdzenie memory consumption
- [ ] **Large folder test** - test na folderze z 1000+ plików
- [ ] **Deep folder test** - test głębokich struktur katalogów
- [ ] **Interrupt test** - test przerwania skanowania
- [ ] **Cache performance test** - hit/miss scenarios
- [ ] **Progress callback test** - sprawdzenie czy callbacks działają

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - skanowanie musi działać w 100% cases
- [ ] **PERFORMANCE BUDGET** - **MANDATORY 20-30% IMPROVEMENT**
- [ ] **MEMORY BUDGET** - brak wzrostu memory usage
- [ ] **API COMPATIBILITY** - 100% backward compatibility

#### **CRITICAL SUCCESS METRICS:**

- [ ] **Scan time improvement: ≥20%** (measured on 1000+ files)
- [ ] **Memory usage: no increase** (measured on large folders)  
- [ ] **API compatibility: 100%** (all existing calls work)
- [ ] **Cache hit rate: unchanged** (cache effectiveness maintained)