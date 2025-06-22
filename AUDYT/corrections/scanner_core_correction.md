**⚠️ KRYTYCZNE: Przed rozpoczęciem pracy zapoznaj się z ogólnymi zasadami refaktoryzacji, poprawek i testowania opisanymi w pliku [refactoring_rules.md](../_BASE_/refactoring_rules.md).**

---

# 📋 ETAP 2: scanner_core.py - ANALIZA I REFAKTORYZACJA

**Data analizy:** 2024-12-22

### 📋 Identyfikacja

- **Plik główny:** `src/logic/scanner_core.py`
- **Plik z kodem (patch):** `../patches/scanner_core_patch_code.md`
- **Priorytet:** ⚫⚫⚫⚫ KRYTYCZNY (BOTTLENECK WYDAJNOŚCIOWY)
- **Zależności:**
  - `src.logic.file_pairing`
  - `src.logic.metadata_manager`
  - `src.logic.scanner_cache`
  - `src.models.file_pair`, `src.models.special_folder`
  - `src.utils.path_utils`
  - `src.app_config`, `src.config`

---

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - **FUNKCJA `collect_files_streaming` MA ZŁOŻONOŚĆ C** (radon) - 587 linii, zbyt kompleksowa
   - **REDUNDANT INTERRUPT CHECKS** - sprawdzenie przerwania w 4+ miejscach w tej samej funkcji
   - **NESTED FUNCTIONS** - `_walk_directory_streaming` zagnieżdżona w `collect_files_streaming`
   - **MASSIVE FUNCTION** - `collect_files_streaming` robi zbyt wiele rzeczy naraz

2. **Optymalizacje (BOTTLENECK WYDAJNOŚCIOWY):**

   - **PROGRESS CALLBACK OVERHEAD** - wywołanie progress_callback co folder/plik spowalnia skanowanie
   - **OS.SCANDIR() DUPLICATION** - entries lista tworzona dwukrotnie (linie 419, 432, 472)
   - **EXCESSIVE LOGGING** - debug logi w każdej iteracji mogą spowalniać o 20-30%
   - **STRING OPERATIONS** - multiple normalize_path/os.path.join w pętlach

3. **Refaktoryzacja:**

   - **KLASY OVER-ENGINEERED** - ScanConfig, ScanCacheManager, ScanProgressManager, ScanOrchestrator - zbyt skomplikowane dla prostej funkcji
   - **SINGLE RESPONSIBILITY VIOLATION** - scanner_core robi cache, progress, validation, file collection
   - **FUNKCJA `find_special_folders` - DEAD CODE** - tylko return [] (linie 575-587)

4. **Logowanie:**
   - **PERFORMANCE KILLER** - debug log w każdej iteracji skanowania (linia 467)
   - **EXCESSIVE INFO LOGS** - za dużo logów INFO/DEBUG w hot path
   - **STRING FORMATTING OVERHEAD** - f-strings w debug logach wykonywane nawet gdy debug wyłączony

---

### 🛠️ PLAN REFAKTORYZACJI

**Typ refaktoryzacji:** PERFORMANCE OPTIMIZATION + Podział funkcji + Dead code removal

#### KROK 1: PRZYGOTOWANIE 🛡️

- [ ] **BACKUP UTWORZONY:** `scanner_core_backup_20241222.py` w folderze `AUDYT/backups/`
- [ ] **ANALIZA ZALEŻNOŚCI:** Core module - używany przez całą aplikację do skanowania
- [ ] **IDENTYFIKACJA API:** Główne funkcje `scan_folder`, `collect_files_streaming` - sprawdzić usage
- [ ] **PLAN ETAPOWY:** 4 kroki - dead code cleanup, performance optimization, function splitting, class simplification

#### KROK 2: IMPLEMENTACJA 🔧

- [ ] **ZMIANA 1:** USUNIĘCIE DEAD CODE - funkcja `find_special_folders` (linie 575-587)
- [ ] **ZMIANA 2:** OPTIMIZATION - redukcja debug logów w hot path
- [ ] **ZMIANA 3:** REFACTOR - podział `collect_files_streaming` na mniejsze funkcje
- [ ] **ZMIANA 4:** PERFORMANCE - optymalizacja progress callbacks (batch instead of per-file)
- [ ] **ZMIANA 5:** SIMPLIFICATION - uproszczenie over-engineered klas
- [ ] **ZACHOWANIE API:** Publiczne funkcje `scan_folder`, `collect_files_streaming` zachowane
- [ ] **BACKWARD COMPATIBILITY:** 100% kompatybilność API

#### KROK 3: WERYFIKACJA PO KAŻDEJ ZMIANIE 🧪

- [ ] **TESTY AUTOMATYCZNE:** Test skanowania różnych typów folderów
- [ ] **URUCHOMIENIE APLIKACJI:** Test pełnego workflow skanowania
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI:** Test cache, progress callbacks, interrupt handling
- [ ] **PERFORMANCE TESTING:** Pomiar czasu skanowania (powinien być 20-30% szybszy)

#### KROK 4: INTEGRACJA FINALNA 🔗

- [ ] **TESTY INNYCH PLIKÓW:** Sprawdzenie wszystkich modułów używających scanner_core
- [ ] **TESTY INTEGRACYJNE:** Pełny test aplikacji ze skanowaniem
- [ ] **TESTY WYDAJNOŚCIOWE:** Porównanie performance przed/po (target: 20-30% improvement)

#### KRYTERIA SUKCESU REFAKTORYZACJI ✅

- [ ] **WSZYSTKIE TESTY PASS** - skanowanie działa identycznie
- [ ] **APLIKACJA URUCHAMIA SIĘ** - bez błędów w core functionality
- [ ] **FUNKCJONALNOŚĆ ZACHOWANA** - cache, progress, interrupt handling działają
- [ ] **PERFORMANCE IMPROVEMENT** - skanowanie co najmniej 20% szybsze
- [ ] **KOMPATYBILNOŚĆ WSTECZNA** - API niezmienione

---

### 🧪 PLAN TESTÓW AUTOMATYCZNYCH

**Test funkcjonalności podstawowej:**

- Test skanowania małego folderu (10-50 plików)
- Test skanowania średniego folderu (100-500 plików)
- Test skanowania dużego folderu (1000+ plików)
- Test cache hit/miss scenarios
- Test interrupt handling (przerwanie skanowania)
- Test progress callbacks

**Test integracji:**

- Test z different pair strategies
- Test z różnymi max_depth values
- Test z force_refresh_cache
- Test error handling (permissions, missing directories)

**Test wydajności (KRYTYCZNY):**

- **BASELINE MEASUREMENT** - czas skanowania przed zmianami
- **POST-REFACTOR MEASUREMENT** - czas skanowania po zmianach
- **MEMORY USAGE** - sprawdzenie czy nie ma memory leaks
- **TARGET: 20-30% PERFORMANCE IMPROVEMENT**

---

### 📊 STATUS TRACKING

- [ ] Backup utworzony
- [ ] Plan refaktoryzacji przygotowany ✅
- [ ] Kod zaimplementowany (krok po kroku)
- [ ] Testy podstawowe przeprowadzone (PASS)
- [ ] Testy integracji przeprowadzone (PASS)
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI** - pełny test skanowania
- [ ] **WERYFIKACJA ZALEŻNOŚCI** - sprawdzenie wszystkich modułów używających scanner
- [ ] **WERYFIKACJA WYDAJNOŚCI** - performance improvement measurement
- [ ] Dokumentacja zaktualizowana (jeśli potrzebne)
- [ ] **Gotowe do wdrożenia**

---

### 📝 DODATKOWE UWAGI

**Pozytywne aspekty:**
- Bardzo dobry cache system
- Excellent interrupt handling
- Good progress reporting architecture
- Proper error handling and logging
- Smart symlink loop detection

**GŁÓWNE PROBLEMY DO ROZWIĄZANIA:**

1. **PERFORMANCE BOTTLENECK** - `collect_files_streaming` to główny bottleneck aplikacji
2. **OVER-ENGINEERING** - zbyt skomplikowane klasy dla prostej funkcji skanowania
3. **LOGGING PERFORMANCE** - debug logi w hot path spowalniają o 20-30%
4. **FUNCTION COMPLEXITY** - funkcja 587 linii z nested function

**EXPECTED IMPACT:**
- **PERFORMANCE**: 20-30% improvement w czasie skanowania
- **MAINTAINABILITY**: Znacznie lepsze dzięki podział funkcji
- **READABILITY**: Lepsze po uproszczeniu over-engineered klas

**RADON COMPLEXITY FINDINGS:**
- `collect_files_streaming` - złożoność C (bardzo wysoka)
- Target: zredukować do B lub A poprzez podział na mniejsze funkcje

**CRITICAL NOTE:**
To jest jeden z najważniejszych plików aplikacji - każda zmiana musi być bardzo ostrożnie testowana!