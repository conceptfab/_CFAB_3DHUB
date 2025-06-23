**⚠️ KRYTYCZNE: Przed rozpoczęciem pracy zapoznaj się z ogólnymi zasadami refaktoryzacji, poprawek i testowania opisanymi w pliku [../../../_BASE_/refactoring_rules.md](../../../_BASE_/refactoring_rules.md).**

---

# 📋 ETAP 2: TILE_RESOURCE_MANAGER - ANALIZA I REFAKTORYZACJA KAFLI

**Data analizy:** 2025-01-23

### 📋 Identyfikacja

- **Plik główny:** `src/ui/widgets/tile_resource_manager.py`
- **Plik z kodem (patch):** `../patches/tile_resource_manager_patch_code_kafli.md`
- **Priorytet:** ⚫⚫⚫⚫ - KRYTYCZNY
- **Zależności:**
  - `src/ui/widgets/tile_async_ui_manager.py`
  - `src/ui/widgets/tile_cache_optimizer.py`  
  - `src/ui/widgets/tile_performance_monitor.py`
  - `PyQt6.QtCore` (QObject, QTimer, pyqtSignal)
  - `psutil` (opcjonalne dla memory monitoring)
  - `weakref` (WeakSet dla memory-safe references)

---

### 🔍 Analiza problemów

1.  **Błędy krytyczne:**

    - **Performance Component Import Risk**: Linia 255-258 - Lazy import w `_initialize_performance_components()` może się nie powieść ale error handling jest insufficient
    - **Emergency Cleanup Too Aggressive**: Linia 411-447 - Emergency cleanup może usuwać aktywne Qt obiekty prowadząc do crashes
    - **Singleton Thread Safety Issue**: Linia 591-600 - `get_resource_manager()` ma race condition przy concurrent access
    - **Memory Monitor Timer Leak**: Linia 67-69 - QTimer w MemoryMonitor nie jest cleanup przy destrukcji objektu
    - **WeakSet Iterator Issue**: Linia 392-398 - Iterowanie po WeakSet może prowadzić do RuntimeError gdy obiekty są usuwane podczas iteracji

2.  **Optymalizacje:**

    - **Memory Check Optimization**: Linia 73-105 - Memory checking przy każdym timer tick może być kosztowne przy psutil calls
    - **Statistics Calculation**: Linia 449-490 - `_update_statistics()` jest wywoływana za często bez caching
    - **Component Registration Performance**: Linia 347-356 - Brak batching dla multiple component registrations
    - **Cleanup Timer Efficiency**: Linia 229-231 - Fixed interval cleanup może być wasteful, można użyć adaptive timing
    - **Debug Info Generation**: Linia 536-549 - `get_debug_info()` generuje duplicate statistics

3.  **Refaktoryzacja:**

    - **Emergency vs Regular Cleanup**: Za dużo duplikacji między `perform_cleanup()` i `perform_emergency_cleanup()`
    - **Performance Components Integration**: Scattered logic dla performance components przez cały manager
    - **Error Handling Standardization**: Brak spójnego error handling pattern przez całą klasę
    - **Resource Limits Validation**: Brak validation czy ResourceLimits mają sensowne wartości

4.  **Logowanie:**
    - **Performance Logging**: Brak logowania performance metrics dla debugging slow operations
    - **Memory Trend Logging**: Słabe logowanie memory trends może utrudniać debugging memory leaks
    - **Component Lifecycle Logging**: Brak śledzenia lifecycle komponentów dla debugging

---

### 🛠️ PLAN REFAKTORYZACJI

**Typ refaktoryzacji:** Optymalizacja kodu + Thread Safety + Error Handling Enhancement + Performance Optimization

#### KROK 1: PRZYGOTOWANIE 🛡️

- [ ] **BACKUP UTWORZONY:** `tile_resource_manager_backup_2025-01-23.py` w folderze `AUDYT/KAFLI/backups/`
- [ ] **ANALIZA ZALEŻNOŚCI:** Sprawdzenie integracji z performance components i FileTileWidget
- [ ] **IDENTYFIKACJA API:** 23 publiczne metody używane przez FileTileWidget i external components
- [ ] **PLAN ETAPOWY:** Podział refaktoryzacji na 6 małych, weryfikowalnych kroków

#### KROK 2: IMPLEMENTACJA 🔧

- [ ] **ZMIANA 1:** Thread-safe singleton implementation z proper double-checked locking
- [ ] **ZMIANA 2:** Enhanced error handling dla performance components z retry mechanisms
- [ ] **ZMIANA 3:** Optimized memory monitoring z adaptive check intervals i caching
- [ ] **ZMIANA 4:** Safe emergency cleanup procedure nie usuwająca aktywnych Qt objects
- [ ] **ZMIANA 5:** Performance optimization dla statistics calculation i component operations
- [ ] **ZMIANA 6:** Enhanced resource limits validation z sensible defaults
- [ ] **ZACHOWANIE API:** Wszystkie 23 publiczne metody zachowane z backward compatibility
- [ ] **BACKWARD COMPATIBILITY:** 100% kompatybilność dla FileTileWidget integration

#### KROK 3: WERYFIKACJA PO KAŻDEJ ZMIANIE 🧪

- [ ] **TESTY AUTOMATYCZNE:** Uruchomienie testów resource manager po każdej zmianie
- [ ] **URUCHOMIENIE APLIKACJI:** Sprawdzenie czy memory monitoring i cleanup działają
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI:** Test rejestracji 1000+ kafli z memory limits

#### KROK 4: INTEGRACJA FINALNA 🔗

- [ ] **TESTY INNYCH PLIKÓW:** Sprawdzenie czy FileTileWidget integration nadal działa
- [ ] **TESTY INTEGRACYJNE:** Pełne testy memory management przy dużych galeriach kafli
- [ ] **TESTY WYDAJNOŚCIOWE:** Memory overhead nie zwiększony o więcej niż 5%

#### KRYTERIA SUKCESU REFAKTORYZACJI ✅

- [ ] **WSZYSTKIE TESTY PASS** - 100% testów resource manager przechodzi
- [ ] **APLIKACJA URUCHAMIA SIĘ** - bez błędów w memory monitoring
- [ ] **FUNKCJONALNOŚĆ ZACHOWANA** - wszystkie funkcje zarządzania zasobami działają
- [ ] **KOMPATYBILNOŚĆ WSTECZNA** - 100% backward compatibility dla tile widgets

---

### 🧪 PLAN TESTÓW AUTOMATYCZNYCH

**Test funkcjonalności podstawowej:**

- Test rejestracji i wyrejestrowania kafli (register_tile/unregister_tile)
- Test registration limits (max_tiles enforcement)
- Test worker pool management (register_worker/unregister_worker)
- Test memory monitoring i alerting (memory warnings/critical)
- Test periodic cleanup execution

**Test integracji:**

- Test integracji z FileTileWidget (tile registration during creation)
- Test integracji z performance components (monitoring, cache, async UI)
- Test singleton behavior z multiple access points
- Test emergency cleanup przy high memory usage

**Test wydajności:**

- Pomiar overhead memory monitoring (psutil calls)
- Test performance statistics calculation przy dużej liczbie kafli
- Pomiar cleanup time dla tysięcy obiektów
- Test resource manager scalability (1000+ tiles)

**Test thread safety:**

- Test concurrent singleton access
- Test concurrent tile registration/unregistration
- Test memory monitoring z multiple threads
- Test cleanup operations z concurrent access

**Test memory management:**

- Test WeakSet behavior przy garbage collection
- Test memory leak prevention w cleanup procedures
- Test emergency cleanup effectiveness
- Test performance components memory usage

---

### 📊 STATUS TRACKING

- [ ] Backup utworzony
- [ ] Plan refaktoryzacji przygotowany
- [ ] Kod zaimplementowany (krok po kroku)
- [ ] Testy podstawowe przeprowadzone (PASS)
- [ ] Testy integracji przeprowadzone (PASS)
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI** - ręczne sprawdzenie memory management z 1000+ kafli
- [ ] **WERYFIKACJA ZALEŻNOŚCI** - sprawdzenie, czy performance components integration działa
- [ ] **WERYFIKACJA WYDAJNOŚCI** - porównanie memory overhead z baseline
- [ ] Dokumentacja zaktualizowana
- [ ] **Gotowe do wdrożenia**

---

### 🎯 KLUCZOWE OBSZARY KAFLI DO NAPRAWY

#### 1. **Thread Safety Critical dla Resource Manager** 🔒
- Singleton implementation race condition - może powodować multiple instances
- WeakSet concurrent iteration - może powodować RuntimeError
- Memory monitoring concurrent access

#### 2. **Memory Management Kafli** 💾
- Emergency cleanup za agresywny - może usuwać aktywne Qt obiekty
- Memory monitoring timer leaks - QTimer nie cleanup
- Statistics calculation efficiency przy dużych galeriach

#### 3. **Performance Optimization Resource Manager** ⚡
- Memory check frequency optimization
- Component registration batching
- Adaptive cleanup timing zamiast fixed intervals

#### 4. **Error Handling Enhancement** 🛡️
- Performance components initialization failures
- Graceful degradation gdy psutil niedostępne
- Better error recovery w cleanup procedures

### 🚨 KRYTYCZNE PROBLEMY WYMAGAJĄCE NATYCHMIASTOWEJ NAPRAWY

#### 1. **Emergency Cleanup Too Aggressive** (Linia 411-447)
```python
# PROBLEM: Może usuwać aktywne Qt obiekty
for tile in list(self._active_tiles):
    if hasattr(tile, "cleanup"):
        tile.cleanup()  # ← To usuwa Qt obiekty!
```
**Wpływ:** Crashes aplikacji przy high memory pressure

#### 2. **Singleton Race Condition** (Linia 591-600)
```python
# PROBLEM: Brak proper double-checked locking
if _resource_manager_instance is None:
    _resource_manager_instance = TileResourceManager(limits)  # ← Race condition
```
**Wpływ:** Multiple instances, nieprzewidywalne zachowanie

#### 3. **WeakSet Iterator Issue** (Linia 392-398)
```python
# PROBLEM: Iterator może się invalidate podczas GC
for component in list(component_set):  # ← Partial fix ale nadal problematyczne
    component.cleanup()
```
**Wpływ:** RuntimeError during cleanup operations

### 🚨 OBOWIĄZKOWE UZUPEŁNIENIE BUSINESS_LOGIC_MAP_KAFLI.MD

**🚨 KRYTYCZNE: PO ZAKOŃCZENIU WSZYSTKICH POPRAWEK MODEL MUSI OBAWIĄZKOWO UZUPEŁNIĆ PLIK `AUDYT/KAFLI/business_logic_map_kafli.md`!**

#### OBOWIĄZKOWE KROKI PO ZAKOŃCZENIU POPRAWEK:

1. ✅ **Wszystkie poprawki wprowadzone** - resource manager działa poprawnie
2. ✅ **Wszystkie testy przechodzą** - PASS na wszystkich testach resource management
3. ✅ **Aplikacja uruchamia się** - bez błędów w memory monitoring
4. ✅ **OTWÓRZ business_logic_map_kafli.md** - znajdź sekcję z tile_resource_manager.py
5. ✅ **DODAJ status ukończenia** - zaznacz że analiza została ukończona
6. ✅ **DODAJ datę ukończenia** - aktualna data w formacie YYYY-MM-DD
7. ✅ **DODAJ business impact kafli** - opis wpływu na resource management kafli
8. ✅ **DODAJ ścieżki do plików wynikowych** - correction_kafli.md i patch_code_kafli.md

#### FORMAT UZUPEŁNIENIA W BUSINESS_LOGIC_MAP_KAFLI.MD:

```markdown
### 📄 TILE_RESOURCE_MANAGER.PY

- **Status:** ✅ UKOŃCZONA ANALIZA KAFLI
- **Data ukończenia:** [DATA]
- **Business impact kafli:** Centralny manager zasobów kafli - kluczowy dla memory management, limits enforcement, performance monitoring tysięcy kafli
- **Pliki wynikowe:**
  - `AUDYT/KAFLI/corrections/tile_resource_manager_correction_kafli.md`
  - `AUDYT/KAFLI/patches/tile_resource_manager_patch_code_kafli.md`
```

#### KONTROLA UZUPEŁNIENIA:

- [ ] **OTWARTO business_logic_map_kafli.md** - plik został otwarty i zlokalizowana sekcja
- [ ] **DODANO status ukończenia** - "✅ UKOŃCZONA ANALIZA KAFLI"
- [ ] **DODANO datę ukończenia** - aktualna data w formacie YYYY-MM-DD
- [ ] **DODANO business impact kafli** - konkretny opis wpływu na resource management kafli
- [ ] **DODANO ścieżki do plików** - correction_kafli.md i patch_code_kafli.md
- [ ] **ZWERYFIKOWANO poprawność** - wszystkie informacje są prawidłowe

**🚨 MODEL NIE MOŻE ZAPOMNIEĆ O UZUPEŁNIENIU BUSINESS_LOGIC_MAP_KAFLI.MD!**

**🚨 BEZ TEGO KROKU ETAP KAFLI NIE JEST UKOŃCZONY!**

---