**⚠️ KRYTYCZNE: Przed rozpoczęciem pracy zapoznaj się z ogólnymi zasadami refaktoryzacji, poprawek i testowania opisanymi w pliku [refactoring_rules.md](../../_BASE_/refactoring_rules.md).**

---

# 📋 ETAP 1: SCANNER_CORE - ANALIZA I REFAKTORYZACJA

**Data analizy:** 2025-01-23

### 📋 Identyfikacja

- **Plik główny:** `src/logic/scanner_core.py`
- **Plik z kodem (patch):** `../patches/scanner_core_patch_code.md`
- **Priorytet:** ⚫⚫⚫⚫ **KRYTYCZNE**
- **Zależności:**
  - `src/logic/file_pairing.py`
  - `src/logic/scanner_cache.py`
  - `src/logic/metadata_manager.py`
  - `src/models/file_pair.py`
  - `src/models/special_folder.py`
  - `src/utils/path_utils.py`

---

### 🔍 Analiza problemów

#### 1. **Błędy krytyczne:**

- **Thread Safety Gaps:** Funkcje `_report_progress_with_throttling()` i `_perform_memory_cleanup()` używają zmiennych globalnych bez synchronizacji
- **Memory Leak Risk:** `ThreadSafeVisitedDirs` nie ma built-in size limits, może rosnąć bez kontroli przy deep directory structures
- **Resource Management:** Brak `finally` blocks dla cleanup w niektórych exception handlers
- **Inconsistent Error Handling:** Niektóre wyjątki logowane jako debug, inne jako error bez clear criteria

#### 2. **Optymalizacje wydajności:**

- **Memory Management Monitoring:** Excellent memory cleanup z GC_INTERVAL_FILES=1000 i memory monitoring
- **Smart Folder Filtering:** Dobra optymalizacja z frozenset O(1) lookup dla ignored folders
- **Thread-Safe Progress:** ThreadSafeProgressManager z throttling dobrze implementowany
- **Session Correlation IDs:** Dobry debugging support z unique session IDs
- **Cache Optimization:** Effective pre-computed normalized paths

#### 3. **Refaktoryzacja struktury:**

- **Over-Decomposition:** Funkcja `collect_files_streaming()` zbyt rozłożona na małe funkcje (9 helper functions)
- **Redundant Progress Callbacks:** Dwie implementacje progress reporting (`ThreadSafeProgressManager` vs local throttling)
- **Complex Parameter Passing:** Wiele funkcji ma 8+ parametrów, co wskazuje na poor cohesion
- **Eliminated Dead Code:** Dobra cleanup eliminated classes (ScanConfig, ScanCacheManager, ScanOrchestrator)

#### 4. **Logowanie i monitoring:**

- **Performance Metrics:** Excellent business metrics logging (files/sec, folders/sec)
- **Session Tracking:** Dobry correlation ID system dla debugowania
- **Memory Monitoring:** Advanced memory usage tracking z psutil integration
- **Slow Scan Detection:** Smart alerting dla performance issues (<100 files/sec)

---

### 🛠️ PLAN REFAKTORYZACJI

**Typ refaktoryzacji:** Optymalizacja kodu + Thread Safety Fixes + Struktura cleanup

#### KROK 1: PRZYGOTOWANIE 🛡️

- [ ] **BACKUP UTWORZONY:** `scanner_core_backup_2025_01_23.py` w folderze `AUDYT/backups/`
- [ ] **ANALIZA ZALEŻNOŚCI:** file_pairing.py, scanner_cache.py, metadata_manager.py, models/
- [ ] **IDENTYFIKACJA API:** `collect_files_streaming()`, `scan_folder_for_pairs()`, `get_scan_statistics()`
- [ ] **PLAN ETAPOWY:** 4 etapy - Thread Safety → Memory Optimization → Structure Cleanup → Performance

#### KROK 2: IMPLEMENTACJA 🔧

- [ ] **ZMIANA 1:** Fix thread safety w progress reporting (eliminate global variables)
- [ ] **ZMIANA 2:** Add size limits do ThreadSafeVisitedDirs (max 50000 entries)
- [ ] **ZMIANA 3:** Consolidate progress reporting mechanisms (single source of truth)
- [ ] **ZMIANA 4:** Optimize parameter passing z dataclass structures
- [ ] **ZACHOWANIE API:** Wszystkie publiczne funkcje zachowane, 100% backward compatibility
- [ ] **BACKWARD COMPATIBILITY:** ThreadSafeProgressManager interface unchanged

#### KROK 3: WERYFIKACJA PO KAŻDEJ ZMIANIE 🧪

- [ ] **TESTY AUTOMATYCZNE:** pytest src/logic/scanner_core.py
- [ ] **URUCHOMIENIE APLIKACJI:** python src/main.py (startup check)
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI:** Test skanowania katalogu z >1000 plików

#### KROK 4: INTEGRACJA FINALNA 🔗

- [ ] **TESTY INNYCH PLIKÓW:** file_pairing.py, scanning_service.py integration
- [ ] **TESTY INTEGRACYJNE:** End-to-end scan test z UI
- [ ] **TESTY WYDAJNOŚCIOWE:** Verify >1000 files/sec performance target

#### KRYTERIA SUKCESU REFAKTORYZACJI ✅

- [ ] **WSZYSTKIE TESTY PASS** - pytest coverage 100%
- [ ] **APLIKACJA URUCHAMIA SIĘ** - zero startup errors
- [ ] **FUNKCJONALNOŚĆ ZACHOWANA** - scanning performance ≥ baseline
- [ ] **KOMPATYBILNOŚĆ WSTECZNA** - all API calls work unchanged

---

### 🧪 PLAN TESTÓW AUTOMATYCZNYCH

**Test funkcjonalności podstawowej:**

- Test `collect_files_streaming()` z katalogiem zawierającym 1000+ plików mixed formats
- Test `scan_folder_for_pairs()` z different pair strategies (first_match, best_match)
- Test thread safety z concurrent scanning operations
- Test memory cleanup z long-running scans
- Test interruption handling podczas skanowania

**Test integracji:**

- Integration test z file_pairing.py (verify file pairs creation)
- Integration test z scanner_cache.py (verify cache hit/miss scenarios)
- Integration test z metadata_manager.py (special folders handling)
- UI integration test z progress callbacks

**Test wydajności:**

- Performance test: >1000 files/sec na standardowym hardware
- Memory test: <500MB RAM dla 10000+ files
- Cache performance test: <100ms dla cache hits
- Thread safety stress test: 10 concurrent scans

---

### 📊 STATUS TRACKING

- [ ] Backup utworzony
- [ ] Plan refaktoryzacji przygotowany  
- [ ] Thread safety fixes zaimplementowane
- [ ] Memory optimization zaimplementowana
- [ ] Structure cleanup zaimplementowana
- [ ] Testy podstawowe przeprowadzone (PASS)
- [ ] Testy integracji przeprowadzone (PASS)
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI** - scanning performance ≥1000 files/sec
- [ ] **WERYFIKACJA ZALEŻNOŚCI** - file_pairing.py, scanner_cache.py working
- [ ] **WERYFIKACJA WYDAJNOŚCI** - memory usage <500MB dla large datasets
- [ ] Dokumentacja zaktualizowana
- [ ] **Gotowe do wdrożenia**

---

### 🎯 BUSINESS IMPACT ANALYSIS

**Krytyczne znaczenie dla aplikacji CFAB_3DHUB:**

1. **Performance Core:** scanner_core.py to main bottleneck dla target 1000+ files/sec
2. **Memory Management:** Directly impacts <500MB RAM requirement dla large datasets  
3. **Thread Safety:** Foundation dla responsive UI podczas background scanning
4. **Cache Strategy:** Enables intelligent cache management dla repeated scans
5. **User Experience:** Progress reporting wpływa na perceived performance

**Key Performance Indicators po refaktoryzacji:**

- **Scanning Speed:** ≥1000 files/sec (current baseline tracking)
- **Memory Usage:** <500MB dla 10000+ files (z memory monitoring)
- **Thread Safety:** Zero deadlocks/race conditions w concurrent operations
- **Cache Hit Ratio:** >80% dla repeated directory scans
- **UI Responsiveness:** <100ms progress updates, no UI freezing

**Risk Mitigation:**

- Extensive testing plan z performance benchmarks
- Incremental changes z verification po each step
- Full backward compatibility preservation
- Robust error handling z graceful degradation

---

### 🚨 OBOWIĄZKOWE UZUPEŁNIENIE BUSINESS_LOGIC_MAP.MD

**🚨 KRYTYCZNE: PO ZAKOŃCZENIU WSZYSTKICH POPRAWEK MODEL MUSI OBAWIĄZKOWO UZUPEŁNIĆ PLIK `AUDYT/business_logic_map.md`!**

#### OBOWIĄZKOWE KROKI PO ZAKOŃCZENIU POPRAWEK:

1. ✅ **Wszystkie poprawki wprowadzone** - thread safety, memory optimization, structure cleanup
2. ✅ **Wszystkie testy przechodzą** - pytest, integration tests, performance tests PASS
3. ✅ **Aplikacja uruchamia się** - zero startup errors, full functionality
4. ✅ **OTWÓRZ business_logic_map.md** - znajdź sekcję "**LOGIC** (src/logic/)" → "scanner_core.py"
5. ✅ **DODAJ status ukończenia** - "✅ UKOŃCZONA ANALIZA"
6. ✅ **DODAJ datę ukończenia** - 2025-01-23
7. ✅ **DODAJ business impact** - "Zoptymalizowano main scanning algorithm: thread safety fixes, memory optimization, performance monitoring. Maintains >1000 files/sec target."
8. ✅ **DODAJ ścieżki do plików wynikowych** - correction i patch_code paths

#### FORMAT UZUPEŁNIENIA W BUSINESS_LOGIC_MAP.MD:

```markdown
### 📄 SCANNER_CORE.PY

- **Status:** ✅ UKOŃCZONA ANALIZA
- **Data ukończenia:** 2025-01-23
- **Business impact:** Zoptymalizowano główny algorytm skanowania: thread safety fixes, memory optimization <500MB, performance monitoring >1000 files/sec. Enhanced progress reporting i error handling.
- **Pliki wynikowe:**
  - `AUDYT/corrections/scanner_core_correction.md`
  - `AUDYT/patches/scanner_core_patch_code.md`
```

#### KONTROLA UZUPEŁNIENIA:

- [ ] **OTWARTO business_logic_map.md** - zlokalizowano sekcję LOGIC → scanner_core.py
- [ ] **DODANO status ukończenia** - "✅ UKOŃCZONA ANALIZA"  
- [ ] **DODANO datę ukończenia** - 2025-01-23
- [ ] **DODANO business impact** - thread safety, memory optimization, performance details
- [ ] **DODANO ścieżki do plików** - correction.md i patch_code.md paths
- [ ] **ZWERYFIKOWANO poprawność** - wszystkie informacje aktualne i dokładne

**🚨 MODEL NIE MOŻE ZAPOMNIEĆ O UZUPEŁNIENIU BUSINESS_LOGIC_MAP.MD!**

**🚨 BEZ TEGO KROKU ETAP NIE JEST UKOŃCZONY!**

---