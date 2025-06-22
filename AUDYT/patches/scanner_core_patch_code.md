# PATCH-CODE DLA: scanner_core.py

**Powiązany plik z analizą:** `../corrections/scanner_core_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: OPTYMALIZACJA should_ignore_folder - O(1) lookup

**Problem:** Linear search w IGNORED_FOLDERS powoduje O(n) lookup dla każdego folderu
**Rozwiązanie:** Zamiana na set lookup dla O(1) performance

```python
# PRZED - linia 316-317:
def should_ignore_folder(folder_name: str) -> bool:
    return folder_name in IGNORED_FOLDERS or folder_name.startswith(".")

# PO - optymalizacja:
# Dodać na górze pliku (po linii 46):
IGNORED_FOLDERS_SET = frozenset(IGNORED_FOLDERS)  # Pre-computed set for O(1) lookup

def should_ignore_folder(folder_name: str) -> bool:
    """
    Sprawdza czy folder powinien być ignorowany podczas skanowania.
    OPTYMALIZACJA: Używa frozenset dla O(1) lookup zamiast O(n).
    """
    return folder_name in IGNORED_FOLDERS_SET or folder_name.startswith(".")
```

---

### PATCH 2: BATCH PROGRESS REPORTING - redukcja wywołań callback

**Problem:** Zbyt częste wywołania progress_callback (co 10 plików) powoduje UI lag
**Rozwiązanie:** Batch reporting co 100 plików z smart throttling

```python
# PRZED - linia 437-448:
                    # Sprawdzenie co 10 plików w folderze
                    if (
                        files_processed_in_folder % 10 == 0
                        and interrupt_check
                        and interrupt_check()
                    ):

# PO - optymalizacja:
                    # Sprawdzenie co 100 plików w folderze (batch processing)
                    if (
                        files_processed_in_folder % 100 == 0
                        and interrupt_check
                        and interrupt_check()
                    ):

# ORAZ linia 481-492:
                        # Sprawdzenie co 5 podfolderów
                        if (
                            subfolders_processed % 5 == 0

# PO:
                        # Sprawdzenie co 20 podfolderów (batch processing)
                        if (
                            subfolders_processed % 20 == 0
```

---

### PATCH 3: CACHE MAP_KEY OPTIMIZATION - pre-compute paths

**Problem:** Wielokrotne normalize_path i join operations w hot path
**Rozwiązanie:** Pre-compute base directory path i cache key generation

```python
# PRZED - linia 458-462:
                    if (
                        ext_lower in ARCHIVE_EXTENSIONS
                        or ext_lower in PREVIEW_EXTENSIONS
                    ):
                        map_key = os.path.join(
                            normalize_path(current_dir), base_name.lower()
                        )
                        full_file_path = normalize_path(os.path.join(current_dir, name))
                        file_map[map_key].append(full_file_path)

# PO - dodać na początku _walk_directory_streaming:
def _walk_directory_streaming(current_dir: str, depth: int = 0):
    nonlocal total_folders_scanned, total_files_found
    
    # Pre-compute normalized current directory (cache optimization)
    normalized_current_dir = normalize_path(current_dir)

# Następnie w pętli plików:
                    if (
                        ext_lower in ARCHIVE_EXTENSIONS
                        or ext_lower in PREVIEW_EXTENSIONS
                    ):
                        # Optimized key generation - use pre-computed normalized path
                        map_key = os.path.join(normalized_current_dir, base_name.lower())
                        full_file_path = os.path.join(normalized_current_dir, name)
                        file_map[map_key].append(full_file_path)
```

---

### PATCH 4: PROPER ERROR HANDLING z recovery strategies

**Problem:** Brak szczegółowego error handling może powodować awarie skanowania
**Rozwiązanie:** Dodanie specific exception handling z recovery strategies

```python
# PRZED - linia 499-504:
        except (PermissionError, OSError) as e:
            logger.warning(f"Błąd dostępu do katalogu {current_dir}: {e}")
        except ScanningInterrupted:
            # Przepuszczamy wyjątek przerwania wyżej
            raise

# PO - rozszerzenie error handling:
        except PermissionError as e:
            logger.warning(f"Brak uprawnień do katalogu {current_dir}: {e}")
            # Continue scanning other directories
        except FileNotFoundError as e:
            logger.warning(f"Katalog usunięty podczas skanowania {current_dir}: {e}")
            # Directory was deleted during scanning - continue
        except OSError as e:
            logger.error(f"Błąd I/O podczas dostępu do {current_dir}: {e}")
            # Try to continue with other directories
        except MemoryError as e:
            logger.critical(f"Brak pamięci podczas skanowania {current_dir}: {e}")
            # Critical error - should probably stop scanning
            raise
        except ScanningInterrupted:
            # Przepuszczamy wyjątek przerwania wyżej
            raise
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd w katalogu {current_dir}: {e}")
            # Log unexpected errors but continue scanning
```

---

### PATCH 5: VISITED_DIRS CLEANUP - memory leak prevention

**Problem:** visited_dirs set nie jest czyszczone, może akumulować przy wielokrotnych skanowaniach
**Rozwiązanie:** Proper cleanup w finally block

```python
# PRZED - linia 505-508:
    try:
        _walk_directory_streaming(normalized_dir)
    except ScanningInterrupted:
        raise

# PO - dodanie cleanup:
    try:
        _walk_directory_streaming(normalized_dir)
    except ScanningInterrupted:
        raise
    finally:
        # Cleanup to prevent memory leaks on repeated scans
        visited_dirs.clear()
        logger.debug(f"Cleaned up visited_dirs cache ({len(visited_dirs)} entries)")
```

---

### PATCH 6: SMART PROGRESS REPORTING - throttled updates

**Problem:** Progress callback wywołuje się zbyt często, powodując UI freeze
**Rozwiązanie:** Implementacja throttled progress z minimum interval

```python
# DODAĆ na początku collect_files_streaming (po linii 374):
    last_progress_time = time.time()
    PROGRESS_THROTTLE_INTERVAL = 0.1  # Minimum 100ms between progress updates

# ZAMIENIĆ linia 398-408:
        # Streaming progress - raportowanie w czasie rzeczywistym
        if progress_callback:
            # Progress oparty na liczbie przeskanowanych folderów (rosnąco)
            # Skaluje od 0 do 95% w miarę zwiększania się liczby folderów
            progress = min(95, total_folders_scanned * 2)  # Aproksymacja progressu
            progress_callback(
                progress,
                f"Skanowanie: {os.path.basename(current_dir)} "
                f"({total_files_found} plików, {total_folders_scanned} folderów)",
            )

# NA throttled version:
        # Throttled progress reporting to prevent UI freeze
        current_time = time.time()
        if progress_callback and (current_time - last_progress_time) >= PROGRESS_THROTTLE_INTERVAL:
            progress = min(95, total_folders_scanned * 2)  # Aproksymacja progressu
            progress_callback(
                progress,
                f"Skanowanie: {os.path.basename(current_dir)} "
                f"({total_files_found} plików, {total_folders_scanned} folderów)",
            )
            last_progress_time = current_time
```

---

### PATCH 7: STRUCTURED LOGGING - business metrics

**Problem:** Proste stringi w logach, brak business metrics
**Rozwiązanie:** Structured logging z kluczowymi metrykami

```python
# PRZED - linia 511-513:
    logger.info(
        f"Zakończono streaming zbieranie plików w {elapsed_time:.2f}s. Znaleziono {total_files_found} plików w {total_folders_scanned} folderach."
    )

# PO - structured logging:
    # Business metrics logging
    files_per_second = total_files_found / elapsed_time if elapsed_time > 0 else 0
    folders_per_second = total_folders_scanned / elapsed_time if elapsed_time > 0 else 0
    
    logger.info(
        f"SCAN_COMPLETED: {normalized_dir} | "
        f"files={total_files_found} | folders={total_folders_scanned} | "
        f"time={elapsed_time:.2f}s | "
        f"rate={files_per_second:.1f}files/s, {folders_per_second:.1f}folders/s"
    )
    
    # Performance warning for slow scans
    if files_per_second < 100 and total_files_found > 500:
        logger.warning(
            f"SLOW_SCAN_DETECTED: {normalized_dir} | "
            f"rate={files_per_second:.1f}files/s (expected >100files/s for large folders)"
        )
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - skanowanie folderów nadal działa poprawnie
- [ ] **API kompatybilność** - scan_folder_for_pairs i collect_files_streaming zachowują API
- [ ] **Obsługa błędów** - proper handling permission errors, missing directories
- [ ] **Walidacja danych** - directory validation nadal działa
- [ ] **Logowanie** - structured logs bez spamowania
- [ ] **Konfiguracja** - cache settings i ignored folders działają
- [ ] **Cache** - hit/miss scenarios działają poprawnie
- [ ] **Thread safety** - visited_dirs i cache operations są thread-safe
- [ ] **Memory management** - brak memory leaks przy wielokrotnych scanach
- [ ] **Performance** - min. 30% improvement dla folderów 1000+ plików

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - wszystkie imports działają poprawnie
- [ ] **file_pairing.py** - integracja z create_file_pairs działa
- [ ] **metadata_manager.py** - special folders integration działa
- [ ] **scanner_cache.py** - cache operations działają
- [ ] **file_pair.py** - FilePair creation działa
- [ ] **Backward compatibility** - stare API calls nadal działają
- [ ] **Progress callbacks** - UI progress updates działają płynnie
- [ ] **Interrupt handling** - przerwanie skanowania działa
- [ ] **Config integration** - app_config values są używane

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - każda zoptymalizowana funkcja działa w izolacji
- [ ] **Test integracyjny** - skanowanie end-to-end działa
- [ ] **Test regresyjny** - wszystkie poprzednie funkcjonalności działają
- [ ] **Test wydajnościowy** - benchmark 1000+ plików pokazuje improvement
- [ ] **Test memory** - brak memory leaks przy repeated scans
- [ ] **Test error handling** - graceful handling błędów I/O

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - wszystkie testy muszą przejść
- [ ] **PERFORMANCE IMPROVEMENT** - min. 30% szybsze skanowanie
- [ ] **MEMORY EFFICIENCY** - max. 20% większe zużycie pamięci przy 3x performance
- [ ] **UI RESPONSIVENESS** - progress updates bez UI freeze

---