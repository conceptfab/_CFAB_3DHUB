**⚠️ KRYTYCZNE: Przed rozpoczęciem pracy zapoznaj się z ogólnymi zasadami refaktoryzacji, poprawek i testowania opisanymi w pliku [refactoring_rules.md](../refactoring_rules.md).**

---

# 📋 ETAP 1: SCANNER_CORE.PY - ANALIZA I REFAKTORYZACJA

**Data analizy:** 2025-06-24

### 📋 Identyfikacja

- **Plik główny:** `src/logic/scanner_core.py`
- **Plik z kodem (patch):** `../patches/scanner_core_patch_code.md`
- **Priorytet:** ⚫⚫⚫⚫ (KRYTYCZNE)
- **Zależności:**
  - `src/logic/file_pairing.py`
  - `src/logic/metadata_manager.py`
  - `src/logic/scanner_cache.py`
  - `src/models/file_pair.py`
  - `src/models/special_folder.py`
  - `src/utils/path_utils.py`
  - `src/config/__init__.py`

---

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - **Thread safety issue w ThreadSafeVisitedDirs._perform_cleanup()** - metoda random.shuffle() może powodować nieprzewidywalne zachowanie w środowisku wielowątkowym
   - **Potencjalny memory leak w collect_files_streaming()** - visited_dirs może rosnąć w nieskończoność przy dużych katalogach
   - **Progress callback może blokować UI** - callback jest wywołany z poziomu wątku roboczego, może powodować deadlock
   - **Brak timeout w operacjach I/O** - skanowanie może się zawiesić na nieresponsywnych dyskach sieciowych

2. **Optymalizacje:**

   - **Nieefektywne zarządzanie pamięcią** - GC_INTERVAL_FILES = 1000 może być za rzadki przy dużych folderach
   - **Throttling progress może być za agresywny** - throttle_interval = 0.1s może powodować brak feedback przy długich operacjach
   - **visited_dirs cleanup algorytm** - random shuffling jest nieefektywny, brak LRU policy
   - **Synchroniczne scandir()** - może blokować na wolnych dyskach
   - **Over-monitoring pamięci** - frequent memory checks mogą spowalniać skanowanie

3. **Refaktoryzacja:**

   - **ThreadSafeVisitedDirs potrzebuje LRU cleanup** - zastąpić random shuffling algorytmem LRU
   - **Progress manager potrzebuje async callback** - uniknąć blokowania UI przez callback
   - **_perform_memory_cleanup zbyt verbose** - simplify logging dla production
   - **ScanContext może być rozszerzony** - dodać memory limits i timeout handling

4. **Logowanie:**
   - **Zbyt dużo DEBUG logs** - potencjalnie spowalnia skanowanie w production
   - **Memory monitoring logs** - można przenieść do TRACE level
   - **Progress logging może spamować** - dodać rate limiting do progress logs

---

### 🛠️ PLAN REFAKTORYZACJI

**Typ refaktoryzacji:** Optymalizacja kodu/Thread safety fixes/Memory management enhancement

#### KROK 1: PRZYGOTOWANIE 🛡️

- [ ] **BACKUP UTWORZONY:** `scanner_core_backup_2025-06-24.py` w folderze `AUDYT/backups/`
- [ ] **ANALIZA ZALEŻNOŚCI:** Sprawdzenie wszystkich imports i wywołań przez file_pairing.py, scanning_service.py
- [ ] **IDENTYFIKACJA API:** collect_files_streaming(), scan_folder_for_pairs(), get_scan_statistics()
- [ ] **PLAN ETAPOWY:** Podział refaktoryzacji na małe, weryfikowalne kroki

#### KROK 2: IMPLEMENTACJA 🔧

- [ ] **ZMIANA 1:** Naprawienie thread safety w ThreadSafeVisitedDirs - implementacja LRU cleanup
- [ ] **ZMIANA 2:** Async progress callback wrapper - uniknięcie UI blocking
- [ ] **ZMIANA 3:** Optymalizacja memory cleanup - adaptive GC intervals
- [ ] **ZMIANA 4:** Timeout handling dla I/O operations
- [ ] **ZMIANA 5:** Simplify logging dla production performance
- [ ] **ZACHOWANIE API:** Wszystkie publiczne metody zachowane z backward compatibility
- [ ] **BACKWARD COMPATIBILITY:** 100% kompatybilność wsteczna zachowana

#### KROK 3: WERYFIKACJA PO KAŻDEJ ZMIANIE 🧪

- [ ] **TESTY AUTOMATYCZNE:** Uruchomienie testów po każdej zmianie
- [ ] **URUCHOMIENIE APLIKACJI:** Sprawdzenie czy aplikacja się uruchamia
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI:** Test skanowania folderów z 1000+ plików
- [ ] **THREAD SAFETY TEST:** Test równoczesnego skanowania w wielu wątkach

#### KROK 4: INTEGRACJA FINALNA 🔗

- [ ] **TESTY INNYCH PLIKÓW:** Sprawdzenie scanning_service.py i gallery_manager.py
- [ ] **TESTY INTEGRACYJNE:** Pełne testy skanowania folderów z dziesiątkami tysięcy plików
- [ ] **TESTY WYDAJNOŚCIOWE:** Benchmark 1000+ plików/sek, memory usage <500MB

#### KRYTERIA SUKCESU REFAKTORYZACJI ✅

- [ ] **WSZYSTKIE TESTY PASS** - 100% testów przechodzi
- [ ] **APLIKACJA URUCHAMIA SIĘ** - bez błędów startowych
- [ ] **FUNKCJONALNOŚĆ ZACHOWANA** - skanowanie działa dla dużych folderów
- [ ] **KOMPATYBILNOŚĆ WSTECZNA** - 100% backward compatibility
- [ ] **WYDAJNOŚĆ ZACHOWANA** - 1000+ plików/sek, <500MB RAM

---

### 🧪 PLAN TESTÓW AUTOMATYCZNYCH

**Test funkcjonalności podstawowej:**

- Test skanowania folderu z 100 plikami (benchmark baseline)
- Test skanowania folderu z 10,000 plikami (stress test)
- Test przerywania skanowania (interrupt_check functionality)
- Test cache hit/miss scenarios
- Test progress reporting accuracy

**Test integracji:**

- Test integracji z file_pairing.py - czy pary są tworzone poprawnie
- Test integracji z scanner_cache.py - czy cache działa stabilnie
- Test integracji z metadata_manager.py - czy metadane są obsługiwane

**Test wydajności:**

- Benchmark: skanowanie 10,000 plików w <10 sekund (1000+ plików/sek)
- Memory test: skanowanie 50,000 plików z memory usage <500MB
- Thread safety test: równoczesne skanowanie 3 folderów bez błędów
- Progress callback responsiveness: <100ms latency

**Test stabilności:**

- Long-running test: skanowanie przez 1 godzinę bez memory leaks
- Network timeout test: skanowanie folderów sieciowych z timeout handling
- Large directory test: foldery z >100,000 plików

---

### 📊 STATUS TRACKING

- [ ] Backup utworzony
- [ ] Plan refaktoryzacji przygotowany
- [ ] Thread safety fixes zaimplementowane
- [ ] Memory management optimizations wprowadzone
- [ ] Async progress callback wrapper dodany
- [ ] I/O timeout handling dodany
- [ ] Logging optimizations wprowadzone
- [ ] Testy podstawowe przeprowadzone (PASS)
- [ ] Testy integracji przeprowadzone (PASS)
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI** - test skanowania 10,000+ plików
- [ ] **WERYFIKACJA ZALEŻNOŚCI** - sprawdzenie file_pairing.py, scanning_service.py
- [ ] **WERYFIKACJA WYDAJNOŚCI** - benchmark 1000+ plików/sek, <500MB RAM
- [ ] **WERYFIKACJA THREAD SAFETY** - równoczesne skanowanie bez błędów
- [ ] Dokumentacja zaktualizowana
- [ ] **Gotowe do wdrożenia**

---

### 🚨 OBOWIĄZKOWE UZUPEŁNIENIE BUSINESS_LOGIC_MAP.MD

**🚨 KRYTYCZNE: PO ZAKOŃCZENIU WSZYSTKICH POPRAWEK MODEL MUSI OBAWIĄZKOWO UZUPEŁNIĆ PLIK `AUDYT/business_logic_map.md`!**

#### OBOWIĄZKOWE KROKI PO ZAKOŃCZENIU POPRAWEK:

1. ✅ **Wszystkie poprawki wprowadzone** - kod działa poprawnie z 1000+ plików/sek
2. ✅ **Wszystkie testy przechodzą** - PASS na testach wydajności i thread safety
3. ✅ **Aplikacja uruchamia się** - bez błędów startowych
4. ✅ **OTWÓRZ business_logic_map.md** - znajdź sekcję SCANNER_CORE.PY
5. ✅ **DODAJ status ukończenia** - zaznacz że analiza została ukończona
6. ✅ **DODAJ datę ukończenia** - 2025-06-24
7. ✅ **DODAJ business impact** - Znacznie poprawiona wydajność i stabilność skanowania
8. ✅ **DODAJ ścieżki do plików wynikowych** - correction.md i patch_code.md

#### FORMAT UZUPEŁNIENIA W BUSINESS_LOGIC_MAP.MD:

```markdown
### 📄 SCANNER_CORE.PY

- **Status:** ✅ UKOŃCZONA ANALIZA
- **Data ukończenia:** 2025-06-24
- **Business impact:** Znacznie poprawiona wydajność skanowania (1000+ plików/sek), thread safety, memory management <500MB, timeout handling dla dyskow sieciowych. Kluczowe dla stabilności aplikacji przy pracy z dużymi folderami.
- **Pliki wynikowe:**
  - `AUDYT/corrections/scanner_core_correction.md`
  - `AUDYT/patches/scanner_core_patch_code.md`
```

#### KONTROLA UZUPEŁNIENIA:

- [ ] **OTWARTO business_logic_map.md** - plik został otwarty i zlokalizowana sekcja SCANNER_CORE.PY
- [ ] **DODANO status ukończenia** - "✅ UKOŃCZONA ANALIZA"
- [ ] **DODANO datę ukończenia** - 2025-06-24
- [ ] **DODANO business impact** - znacznie poprawiona wydajność i stabilność
- [ ] **DODANO ścieżki do plików** - scanner_core_correction.md i scanner_core_patch_code.md
- [ ] **ZWERYFIKOWANO poprawność** - wszystkie informacje są prawidłowe

**🚨 MODEL NIE MOŻE ZAPOMNIEĆ O UZUPEŁNIENIU BUSINESS_LOGIC_MAP.MD!**

**🚨 BEZ TEGO KROKU ETAP NIE JEST UKOŃCZONY!**

---