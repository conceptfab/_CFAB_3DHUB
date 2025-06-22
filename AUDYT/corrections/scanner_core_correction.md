**⚠️ KRYTYCZNE: Przed rozpoczęciem pracy zapoznaj się z ogólnymi zasadami refaktoryzacji, poprawek i testowania opisanymi w pliku [refactoring_rules.md](../../_BASE_/refactoring_rules.md).**

---

# 📋 ETAP 3: SCANNER_CORE - ANALIZA I REFAKTORYZACJA

**Data analizy:** 2025-01-28

### 📋 Identyfikacja

- **Plik główny:** `src/logic/scanner_core.py`
- **Plik z kodem (patch):** `../patches/scanner_core_patch_code.md`
- **Priorytet:** ⚫⚫⚫⚫ KRYTYCZNY
- **Zależności:**
  - `src/app_config.py` (konfiguracja cache i rozszerzeń)
  - `src/logic/file_pairing.py` (parowanie plików)
  - `src/logic/metadata_manager.py` (metadane folderów)
  - `src/logic/scanner_cache.py` (cache skanowania)
  - `src/models/file_pair.py` (model par plików)
  - `src/models/special_folder.py` (foldery specjalne)
  - `src/utils/path_utils.py` (operacje na ścieżkach)

---

### 🔍 Analiza problemów

1.  **Błędy krytyczne:**

    - **Potencjalne memory leaks w collect_files_streaming**: Memory cleanup (linie 366-369) jest wykonywany co 1000 plików, ale w przypadku przerwania skanowania może nie zostać wywołany, co prowadzi do memory leaks
    - **Thread safety issue w progress reporting**: Mimo ThreadSafeProgressManager, w funkcji `_walk_directory_streaming` istnieje direct access do `progress_callback` (linie 277-287) bez proper locking
    - **Race condition w visited_dirs**: Set `visited_dirs` (linia 267) nie jest thread-safe i może powodować race conditions przy concurrent access
    - **Incomplete error handling dla critical operations**: Funkcja `collect_files_streaming` nie ma proper recovery dla MemoryError i może crash całą aplikację

2.  **Optymalizacje:**

    - **Inefficient progress calculation**: Aproksymacja progressu (linia 281) używa `total_folders_scanned * 2` co nie odzwierciedla rzeczywistego postępu
    - **Suboptimal batch processing**: Różne batch sizes (50, 20) w różnych miejscach mogą być zoptymalizowane na podstawie performance testing
    - **Cache efficiency**: Smart pre-filtering (linie 316-332) może być dalej zoptymalizowane przez early directory rejection
    - **Memory management**: GC call co 1000 plików (linie 366-369) może być zbyt częste i wpływać na performance

3.  **Refaktoryzacja:**

    - **Complex nested function**: `_walk_directory_streaming` (linie 269-425) jest zbyt długa i complex - potrzebuje dekompozycji
    - **Mixed responsibilities**: Funkcja łączy file scanning, progress reporting, memory management i error handling
    - **Inconsistent logging levels**: Mieszanie DEBUG, INFO, WARNING, ERROR bez clear criteria
    - **Dead code comments**: Komentarze o usuniętych klasach (linie 56, 59, 182, 598-600) powinny być usunięte

4.  **Logowanie:**
    - **Performance logging inconsistency**: Business metrics (linie 441-446) są logged na INFO level, ale performance warnings (linie 449-453) używają WARNING
    - **Excessive debug logging**: Debug logs w critical path mogą wpływać na performance przy dużych zbiorach danych
    - **Missing correlation IDs**: Brak identyfikatorów sesji skanowania dla tracking distributed operations

---

### 🛠️ PLAN REFAKTORYZACJI

**Typ refaktoryzacji:** Podział pliku / Optymalizacja kodu / Poprawa thread safety / Memory management

#### KROK 1: PRZYGOTOWANIE 🛡️

- [ ] **BACKUP UTWORZONY:** `scanner_core_backup_2025_01_28.py` w folderze `AUDYT/backups/`
- [ ] **ANALIZA ZALEŻNOŚCI:** Sprawdzenie wszystkich imports i integration points
- [ ] **IDENTYFIKACJA API:** Lista publicznych funkcji - `collect_files_streaming()`, `scan_folder_for_pairs()`, `get_scan_statistics()`
- [ ] **PLAN ETAPOWY:** Podział na małe, weryfikowalne kroki z preserved functionality

#### KROK 2: IMPLEMENTACJA 🔧

- [ ] **ZMIANA 1:** Dekompozycja `_walk_directory_streaming` na mniejsze, focused functions
- [ ] **ZMIANA 2:** Poprawa thread safety - thread-safe visited_dirs, proper locking for all shared state
- [ ] **ZMIANA 3:** Enhanced memory management - proper cleanup w finally blocks, configurable GC intervals
- [ ] **ZMIANA 4:** Progress calculation optimization - accurate progress based on estimated total files
- [ ] **ZMIANA 5:** Standardization logging levels i dodanie session correlation IDs
- [ ] **ZMIANA 6:** Error handling improvement - comprehensive recovery strategies dla critical errors
- [ ] **ZACHOWANIE API:** Wszystkie public functions zachowane z identycznymi signatures
- [ ] **BACKWARD COMPATIBILITY:** 100% kompatybilność wsteczna zachowana

#### KROK 3: WERYFIKACJA PO KAŻDEJ ZMIANIE 🧪

- [ ] **TESTY AUTOMATYCZNE:** Uruchomienie testów scanner_core po każdej zmianie
- [ ] **URUCHOMIENIE APLIKACJI:** Sprawdzenie czy skanowanie folderów działa
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI:** Test na próbkach 1000+, 10000+ plików

#### KROK 4: INTEGRACJA FINALNA 🔗

- [ ] **TESTY INNYCH PLIKÓW:** Sprawdzenie czy scanning_service.py i UI components działają
- [ ] **TESTY INTEGRACYJNE:** Pełne testy skanowania z cache i metadata management
- [ ] **TESTY WYDAJNOŚCIOWE:** Weryfikacja 100+ plików/s dla folderów >500 plików, memory usage monitoring

#### KRYTERIA SUKCESU REFAKTORYZACJI ✅

- [ ] **WSZYSTKIE TESTY PASS** - 100% testów przechodzi
- [ ] **APLIKACJA URUCHAMIA SIĘ** - bez błędów w skanowaniu
- [ ] **FUNKCJONALNOŚĆ ZACHOWANA** - skanowanie działa identycznie
- [ ] **KOMPATYBILNOŚĆ WSTECZNA** - wszystkie existing integrations działają
- [ ] **PERFORMANCE MAINTAINED** - 100+ plików/s maintained, memory managed
- [ ] **THREAD SAFETY** - zero race conditions w concurrent scanning

---

### 🧪 PLAN TESTÓW AUTOMATYCZNYCH

**Test funkcjonalności podstawowej:**

- Test `collect_files_streaming()` na różnych rozmiarach folderów (100, 1000, 10000 plików)
- Test `scan_folder_for_pairs()` z różnymi strategiami parowania
- Test interrupt mechanism - cancellation podczas skanowania
- Test cache operations - hit/miss scenarios, cache invalidation
- Test special folders handling - virtual folders creation

**Test integracji:**

- Test integracji z file_pairing.py - pipeline collect + create_pairs
- Test integracji z metadata_manager.py - special folders z metadata
- Test integracji z scanner_cache.py - proper cache lifecycle
- Test integracji z path_utils.py - path normalization scenarios

**Test wydajności:**

- Benchmark `collect_files_streaming()` - target 100+ plików/s dla >500 plików
- Memory profiling - monitor memory usage growth podczas long scans
- Progress reporting performance - ensure progress callbacks nie blokują scanning
- Cache performance - hit ratio optimization, cache overhead measurement

**Test thread safety:**

- Concurrent scanning multiple directories simultaneously
- Interrupt handling podczas concurrent operations
- Thread safety visited_dirs i progress reporting
- Memory consistency checks under concurrent load

**Test error handling:**

- PermissionError handling - continue scanning other directories
- FileNotFoundError handling - directory deleted during scan
- MemoryError handling - proper cleanup i recovery
- ScanningInterrupted exception - proper resource cleanup

---

### 📊 STATUS TRACKING

- [ ] Backup utworzony
- [ ] Plan refaktoryzacji przygotowany
- [ ] Kod zaimplementowany (krok po kroku)
- [ ] Testy podstawowe przeprowadzone (PASS)
- [ ] Testy integracji przeprowadzone (PASS)
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI** - test na 10000+ plików, interrupt handling
- [ ] **WERYFIKACJA ZALEŻNOŚCI** - sprawdzenie file_pairing.py, metadata_manager.py integration
- [ ] **WERYFIKACJA WYDAJNOŚCI** - benchmark 100+ plików/s, memory profiling
- [ ] **WERYFIKACJA THREAD SAFETY** - concurrent scanning tests
- [ ] **WERYFIKACJA ERROR HANDLING** - recovery scenarios, resource cleanup
- [ ] Dokumentacja zaktualizowana
- [ ] **Gotowe do wdrożenia**

---

### 🎯 BUSINESS IMPACT

**Krytyczny wpływ na procesy biznesowe:**
- Główny silnik skanowania - podstawa discovery plików w aplikacji
- Wydajność 100+ plików/s dla folderów >500 plików - krytyczna dla user experience
- Thread safety - stabilność podczas concurrent operations
- Memory management - zapewnienie stable operation przy dużych zbiorach danych
- Error handling - robust operation w production environment

**Metryki sukcesu:**
- Czas skanowania 1000 plików: <10 sekund (100+ plików/s)
- Memory usage podczas skanowania: <200MB per 10000 plików
- Thread safety: zero race conditions w concurrent scanning tests
- Error recovery: 100% recovery from non-critical errors (permissions, file access)
- Cache efficiency: >80% cache hit ratio dla repeat scans
- Progress accuracy: <5% deviation between reported i actual progress

**Obszary optymalizacji:**
- Smart pre-filtering: reduce unnecessary directory traversal
- Memory management: efficient cleanup preventing leaks
- Progress calculation: accurate estimation based na directory size estimation
- Batch processing: optimal batch sizes dla different operations
- Error handling: comprehensive recovery strategies for production stability