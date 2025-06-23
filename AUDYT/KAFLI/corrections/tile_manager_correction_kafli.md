**⚠️ KRYTYCZNE: Przed rozpoczęciem pracy zapoznaj się z ogólnymi zasadami refaktoryzacji, poprawek i testowania opisanymi w pliku [refactoring_rules.md](../../../_BASE_/refactoring_rules.md).**

---

# 📋 ETAP 2: TILE_MANAGER - ANALIZA I REFAKTORYZACJA KAFLI

**Data analizy:** 2025-06-23

### 📋 Identyfikacja

- **Plik główny:** `src/ui/main_window/tile_manager.py`
- **Plik z kodem (patch):** `../patches/tile_manager_patch_code_kafli.md`
- **Priorytet:** ⚫⚫⚫⚫ KRYTYCZNE
- **Zależności:**
  - `src/models/file_pair.py`
  - `src/ui/gallery_manager.py`
  - `src/ui/main_window/progress_manager.py`
  - `src/ui/main_window/worker_manager.py`
  - `src/ui/main_window/data_manager.py`
  - `src/ui/widgets/file_tile_widget.py`

---

### 🔍 Analiza problemów

1.  **Błędy krytyczne wydajności kafli:**

    - **Brak batch optimization w create_tile_widgets_batch** - każdy kafelek tworzony indywidualnie zamiast prawdziwego batch processing
    - **Synchroniczne dodawanie do layoutu** - operacje UI wykonywane synchronicznie dla każdego kafla zamiast async batching
    - **Nadmierne wywołania processEvents()** - QApplication.processEvents() po każdym batchu może powodować UI stuttering
    - **Memory spike przy tysiącach kafli** - brak memory pressure monitoring podczas batch creation

2.  **Optymalizacje architektury kafli:**

    - **Tight coupling z MainWindow** - TileManager ma bezpośrednie referencje do wielu komponentów MainWindow zamiast dependency injection
    - **Brak thread safety** - `_is_creating_tiles` flag nie jest thread-safe, może powodować race conditions
    - **Mieszanie responsywności** - callback `thumbnail_loaded_callback` wykonuje się w UI thread zamiast background
    - **Nieoptymalny progress tracking** - progress bar aktualizowany po każdym kaflu zamiast batching

3.  **Refaktoryzacja logiki batch processing:**

    - **Factory pattern bez pool reuse** - każdy kafelek tworzony od zera zamiast object pooling dla często używanych instancji
    - **Brak intelligent cache invalidation** - refresh_existing_tiles iteruje przez wszystkie kafle zamiast używać hash lookup
    - **Layout geometry recalculation** - geometria przeliczana dla każdego kafla zamiast cache dla całego batchu
    - **Signal connection overhead** - 6 sygnałów podłączanych dla każdego kafla bez signal multiplexing

4.  **Logowanie i debugging kafli:**
    - **Nadmierne debug logowanie** - logi dla każdego kafla w hot path batch creation
    - **Brak structured logging** - trudne śledzenie performance batch operations
    - **Inconsistent error handling** - różne mechanizmy error handling w różnych metodach

---

### 🛠️ PLAN REFAKTORYZACJI

**Typ refaktoryzacji:** Optymalizacja wydajności batch processing i refaktoryzacja architektury dla tysięcy kafli

#### KROK 1: PRZYGOTOWANIE 🛡️

- [ ] **BACKUP UTWORZONY:** `tile_manager_backup_2025-06-23.py` w folderze `AUDYT/KAFLI/backups/`
- [ ] **ANALIZA ZALEŻNOŚCI:** Sprawdzenie integration z GalleryManager, ProgressManager, WorkerManager
- [ ] **IDENTYFIKACJA API:** Lista publicznych metod używanych przez MainWindow i workers
- [ ] **PLAN ETAPOWY:** Podział na 4 mini-etapy focused na batch performance

#### KROK 2: IMPLEMENTACJA 🔧

**Mini-etap 2A: Batch Processing Optimization**
- [ ] **ZMIANA 1:** Implementacja true batch processing - tworzenie wielu kafli w jednej operacji UI
- [ ] **ZMIANA 2:** Async layout operations - dodawanie kafli do layoutu w background z UI updates batching
- [ ] **ZMIANA 3:** Memory pressure monitoring - tracking memory usage podczas batch creation tysięcy kafli

**Mini-etap 2B: Thread Safety i Performance**
- [ ] **ZMIANA 4:** Thread-safe `_is_creating_tiles` z proper locking mechanism
- [ ] **ZMIANA 5:** Background thumbnail callback processing - przeniesienie poza UI thread
- [ ] **ZMIANA 6:** Intelligent progress batching - aktualizacja progress co N kafli zamiast po każdym

**Mini-etap 2C: Architecture Cleanup**
- [ ] **ZMIANA 7:** Dependency injection pattern zamiast tight coupling z MainWindow
- [ ] **ZMIANA 8:** Signal multiplexing - jeden signal bus zamiast 6 sygnałów per kafelek
- [ ] **ZMIANA 9:** Object pooling dla tile creation - reuse zamiast recreation

**Mini-etap 2D: Cache i Lookup Optimization**
- [ ] **ZMIANA 10:** Hash-based refresh_existing_tiles - O(1) lookup zamiast O(n) iteration
- [ ] **ZMIANA 11:** Layout geometry cache optimization - calculate once per batch
- [ ] **ZACHOWANIE API:** Wszystkie publiczne metody preserved z performance enhancements

#### KROK 3: WERYFIKACJA PO KAŻDEJ ZMIANIE 🧪

- [ ] **TESTY AUTOMATYCZNE:** `pytest tests/test_tile_manager_*.py` po każdym mini-etapie
- [ ] **URUCHOMIENIE APLIKACJI:** Test batch creation 1000+ kafli w <2s
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI:** Progress bar, signal connections, layout geometry

#### KROK 4: INTEGRACJA FINALNA 🔗

- [ ] **TESTY BATCH PERFORMANCE:** 1000+ kafli creation w <2s z <500MB memory usage
- [ ] **TESTY THREAD SAFETY:** Concurrent tile operations bez race conditions
- [ ] **TESTY MEMORY EFFICIENCY:** Long-running batch operations bez memory leaks

#### KRYTERIA SUKCESU REFAKTORYZACJI ✅

- [ ] **BATCH PERFORMANCE TARGET** - 1000+ kafli w <2s zamiast >10s
- [ ] **MEMORY EFFICIENCY** - <500MB dla galerii z tysiącami kafli
- [ ] **THREAD SAFETY VERIFIED** - brak race conditions w _is_creating_tiles
- [ ] **UI RESPONSIVENESS** - brak stuttering podczas batch creation

---

### 🧪 PLAN TESTÓW AUTOMATYCZNYCH KAFLI

**Test funkcjonalności podstawowej tile managera:**

- Test create_tile_widget_for_pair() z valid i invalid FilePair
- Test signal connections dla wszystkich 6 sygnałów kafla
- Test thumbnail_loaded_callback error handling
- Test progress tracking podczas tile creation
- Test tile numbering w batch operations

**Test integracji batch processing kafli:**

- Test create_tile_widgets_batch() z różnymi rozmiarami batchy (10, 100, 1000+ kafli)
- Test memory usage podczas batch creation tysięcy kafli
- Test layout geometry calculations dla różnych rozmiarów galerii
- Test integration z ProgressManager batch tracking
- Test refresh_existing_tiles performance z hash lookup

**Test wydajności batch operations kafli:**

- Benchmark batch creation 1000 kafli - target <2s vs current >10s
- Memory usage test podczas batch processing - target <500MB peak
- UI responsiveness test - no stuttering podczas batch creation
- Thread safety stress test - concurrent batch operations
- Layout performance test - geometry calculations optimization

---

### 📊 STATUS TRACKING

- [ ] Backup utworzony
- [ ] Plan refaktoryzacji przygotowany
- [ ] **Mini-etap 2A zaimplementowany** (batch processing optimization)
- [ ] **Mini-etap 2B zaimplementowany** (thread safety i performance)
- [ ] **Mini-etap 2C zaimplementowany** (architecture cleanup)
- [ ] **Mini-etap 2D zaimplementowany** (cache i lookup optimization)
- [ ] **Testy podstawowe tile manager PASS** - wszystkie unit testy
- [ ] **Testy batch performance PASS** - 1000+ kafli <2s
- [ ] **WERYFIKACJA MEMORY EFFICIENCY** - <500MB dla tysięcy kafli
- [ ] **WERYFIKACJA THREAD SAFETY** - concurrent operations bez race conditions
- [ ] **WERYFIKACJA UI RESPONSIVENESS** - brak stuttering podczas batch processing
- [ ] **Gotowe do wdrożenia w architekturze kafli**

---

### 🚨 OBOWIĄZKOWE UZUPEŁNIENIE BUSINESS_LOGIC_MAP_KAFLI.MD

**🚨 KRYTYCZNE: PO ZAKOŃCZENIU WSZYSTKICH POPRAWEK MODEL MUSI OBOWIĄZKOWO UZUPEŁNIĆ PLIK `AUDYT/KAFLI/business_logic_map_kafli.md`!**

#### OBOWIĄZKOWE KROKI PO ZAKOŃCZENIU POPRAWEK KAFLI:

1. ✅ **Wszystkie poprawki batch processing kafli wprowadzone** - kod optymalizuje tworzenie tysięcy kafli
2. ✅ **Wszystkie testy tile manager przechodzą** - PASS na wszystkich testach batch operations
3. ✅ **Batch creation kafli działa wydajnie** - 1000+ kafli w <2s bez memory spikes
4. ✅ **OTWÓRZ business_logic_map_kafli.md** - znajdź sekcję tile_manager.py
5. ✅ **DODAJ status ukończenia kafli** - zaznacz że analiza batch processing została ukończona
6. ✅ **DODAJ datę ukończenia** - aktualna data w formacie YYYY-MM-DD
7. ✅ **DODAJ business impact kafli** - wpływ na wydajność batch creation tysięcy kafli
8. ✅ **DODAJ ścieżki do plików wynikowych kafli** - correction_kafli.md i patch_code_kafli.md

#### FORMAT UZUPEŁNIENIA W BUSINESS_LOGIC_MAP_KAFLI.MD:

```markdown
### 📄 tile_manager.py

- **Status:** ✅ UKOŃCZONA ANALIZA KAFLI
- **Data ukończenia:** 2025-06-23
- **Business impact kafli:** Zoptymalizowano batch processing - true batching zamiast individual creation, thread-safe operations, memory pressure monitoring, dependency injection pattern. Dramatyczna poprawa wydajności: 1000+ kafli w <2s zamiast >10s, <500MB memory usage. Kluczowe dla skalowania galerii do tysięcy elementów.
- **Pliki wynikowe:**
  - `AUDYT/KAFLI/corrections/tile_manager_correction_kafli.md`
  - `AUDYT/KAFLI/patches/tile_manager_patch_code_kafli.md`
```

#### KONTROLA UZUPEŁNIENIA KAFLI:

- [ ] **OTWARTO business_logic_map_kafli.md** - plik kafli został otwarty i zlokalizowana sekcja tile_manager.py
- [ ] **DODANO status ukończenia kafli** - "✅ UKOŃCZONA ANALIZA KAFLI"
- [ ] **DODANO datę ukończenia** - 2025-06-23
- [ ] **DODANO business impact kafli** - konkretny opis wpływu na batch performance tysięcy kafli
- [ ] **DODANO ścieżki do plików kafli** - correction_kafli.md i patch_code_kafli.md
- [ ] **ZWERYFIKOWANO poprawność kafli** - wszystkie informacje są prawidłowe dla batch processing kafli

**🚨 MODEL NIE MOŻE ZAPOMNIEĆ O UZUPEŁNIENIU BUSINESS_LOGIC_MAP_KAFLI.MD!**

**🚨 BEZ TEGO KROKU ETAP AUDYTU BATCH PROCESSING KAFLI NIE JEST UKOŃCZONY!**

---