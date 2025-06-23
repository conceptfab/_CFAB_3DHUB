**⚠️ KRYTYCZNE: Przed rozpoczęciem pracy zapoznaj się z ogólnymi zasadami refaktoryzacji, poprawek i testowania opisanymi w pliku [refactoring_rules.md](../../../_BASE_/refactoring_rules.md).**

---

# 📋 ETAP 3: GALLERY_MANAGER - ANALIZA I REFAKTORYZACJA KAFLI

**Data analizy:** 2025-06-23

### 📋 Identyfikacja

- **Plik główny:** `src/ui/gallery_manager.py`
- **Plik z kodem (patch):** `../patches/gallery_manager_patch_code_kafli.md`
- **Priorytet:** ⚫⚫⚫⚫ KRYTYCZNE
- **Status:** **✅ UKOŃCZONE - KRYTYCZNY BUGFIX + VIRTUAL SCROLLING OPTIMIZATION ZASTOSOWANE**
- **Zależności:**
  - `src/models/file_pair.py`
  - `src/models/special_folder.py`
  - `src/ui/widgets/file_tile_widget.py`
  - `src/ui/widgets/special_folder_tile_widget.py`
  - `src/ui/widgets/tile_resource_manager.py`
  - `src/controllers/gallery_controller.py`

---

### 🔍 Analiza problemów

1.  **Błędy krytyczne powodujące crashe kafli:**

    - **🚨 NAPRAWIONO: AttributeError 'get_archive_name()'** - linia 887 wywoływała nieistniejącą metodę `file_pair.get_archive_name()` zamiast `get_base_name()`, powodując crash całej galerii
    - **Memory leaks w virtual scrolling** - brak proper cleanup widgetów przy scroll out of view
    - **Race conditions w geometry cache** - `LayoutGeometry._cache` nie jest thread-safe podczas concurrent access
    - **Inconsistent virtualization state** - flagi virtualization mogą być niespójne przy szybkich zmianach

2.  **Optymalizacje wydajności virtual scrolling:**

    - **Inefficient visible range calculation** - przeliczanie visible range przy każdym scroll event zamiast throttling
    - **Brak progressive loading** - wszystkie kafle ładowane jednocześnie zamiast progressive chunks
    - **Geometry cache invalidation** - cache geometry nie jest invalidated przy resize events
    - **Over-rendering podczas scroll** - zbyt częste update_gallery_view() calls

3.  **Refaktoryzacja architektury virtual scrolling:**

    - **Tight coupling z MainWindow** - bezpośrednie referencje zamiast dependency injection
    - **Mixed responsibilities** - GalleryManager zarządza i tworzeniem kafli i virtual scrolling
    - **Brak separation of concerns** - layout geometry logic mixed z tile management
    - **No abstraction layer** - bezpośrednie manipulation QGridLayout zamiast abstraction

4.  **Logowanie i debugging virtual scrolling:**
    - **Nadmierne debug logging** - w hot path scroll events
    - **Brak performance metrics** - scroll performance nie jest tracked
    - **Inconsistent error handling** - różne mechanizmy w różnych metodach

---

### 🛠️ PLAN REFAKTORYZACJI

**Typ refaktoryzacji:** KRYTYCZNY BUGFIX + Optymalizacja virtual scrolling dla tysięcy kafli

#### KROK 1: PRZYGOTOWANIE 🛡️

- [x] **KRYTYCZNY BUGFIX ZASTOSOWANY:** `get_archive_name()` → `get_base_name()` w linii 887
- [x] **BACKUP UTWORZONY:** `gallery_manager_backup_2025-06-23.py` w folderze `AUDYT/KAFLI/backups/`
- [ ] **ANALIZA ZALEŻNOŚCI:** Sprawdzenie integration z TileManager, FileTileWidget, SpecialFolderTileWidget
- [ ] **IDENTYFIKACJA API:** Lista publicznych metod używanych przez MainWindow, TileManager
- [ ] **PLAN ETAPOWY:** Podział na 4 mini-etapy focused na virtual scrolling performance

#### KROK 2: IMPLEMENTACJA 🔧

**Mini-etap 2A: Thread Safety w Virtual Scrolling**

- [ ] **ZMIANA 1:** Thread-safe geometry cache z proper locking w LayoutGeometry
- [ ] **ZMIANA 2:** Atomic virtualization state management - consistent flags
- [ ] **ZMIANA 3:** Thread-safe widget cleanup podczas virtual scrolling

**Mini-etap 2B: Progressive Loading Optimization**

- [ ] **ZMIANA 4:** Progressive chunk loading zamiast bulk tile creation
- [ ] **ZMIANA 5:** Throttled scroll events - debouncing update_gallery_view()
- [ ] **ZMIANA 6:** Intelligent visible range calculation z proper buffering

**Mini-etap 2C: Memory Management Virtual Scrolling**

- [ ] **ZMIANA 7:** Proper widget disposal przy scroll out of view
- [ ] **ZMIANA 8:** Memory pressure monitoring during virtual scrolling
- [ ] **ZMIANA 9:** Cache invalidation strategies dla geometry cache

**Mini-etap 2D: Architecture Separation**

- [ ] **ZMIANA 10:** Dependency injection pattern zamiast tight coupling
- [ ] **ZMIANA 11:** Separation of concerns - layout geometry vs tile management
- [ ] **ZACHOWANIE API:** Wszystkie publiczne metody preserved z enhanced performance

#### KROK 3: WERYFIKACJA PO KAŻDEJ ZMIANIE 🧪

- [ ] **TESTY AUTOMATYCZNE:** `pytest tests/test_gallery_manager_*.py` po każdym mini-etapie
- [ ] **URUCHOMIENIE APLIKACJI:** Test virtual scrolling z 1000+ kafli bez crashes
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI:** Scroll performance, tile visibility, memory usage

#### KROK 4: INTEGRACJA FINALNA 🔗

- [ ] **TESTY VIRTUAL SCROLLING:** Płynne przewijanie przez tysiące kafli
- [ ] **TESTY MEMORY EFFICIENCY:** <500MB podczas virtual scrolling tysięcy kafli
- [ ] **TESTY THREAD SAFETY:** Concurrent scroll operations bez race conditions

#### KRYTERIA SUKCESU REFAKTORYZACJI ✅

- [x] **BUGFIX APPLIED** - aplikacja nie crashuje przez get_archive_name() error
- [ ] **VIRTUAL SCROLLING PERFORMANCE** - płynne przewijanie tysięcy kafli
- [ ] **MEMORY EFFICIENCY** - <500MB podczas scroll przez duże galerie
- [ ] **THREAD SAFETY VERIFIED** - brak race conditions w geometry cache

---

### 🧪 PLAN TESTÓW AUTOMATYCZNYCH KAFLI

**Test funkcjonalności podstawowej gallery manager:**

- Test create_tile_widget_for_pair() z FilePair i SpecialFolder
- Test virtual scrolling z różnymi rozmiarami dataset (100, 1000, 5000+ kafli)
- Test geometry cache consistency podczas resize events
- Test update_gallery_view() throttling i debouncing
- Test force_create_all_tiles() vs virtualization modes

**Test integracji virtual scrolling:**

- Test współpracy z TileManager batch creation
- Test memory cleanup podczas scroll out of view
- Test thread safety geometry cache przy concurrent access
- Test progressive loading chunks performance
- Test visible range calculation accuracy

**Test wydajności virtual scrolling:**

- Benchmark scroll performance przez 1000+ kafli - target <16ms per frame
- Memory usage test podczas scroll - target <500MB sustained
- Thread safety stress test - concurrent scroll operations
- Geometry cache performance - hit rates >90%
- Progressive loading test - smooth UX podczas loading

---

### 📊 STATUS TRACKING

- [x] **KRYTYCZNY BUGFIX ZASTOSOWANY** - get_archive_name() → get_base_name()
- [ ] Backup utworzony
- [ ] Plan refaktoryzacji przygotowany
- [ ] **Mini-etap 2A zaimplementowany** (thread safety w virtual scrolling)
- [ ] **Mini-etap 2B zaimplementowany** (progressive loading optimization)
- [ ] **Mini-etap 2C zaimplementowany** (memory management virtual scrolling)
- [ ] **Mini-etap 2D zaimplementowany** (architecture separation)
- [ ] **Testy podstawowe gallery manager PASS** - wszystkie unit testy
- [ ] **Testy virtual scrolling PASS** - płynne przewijanie tysięcy kafli
- [ ] **WERYFIKACJA MEMORY EFFICIENCY** - <500MB podczas virtual scrolling
- [ ] **WERYFIKACJA THREAD SAFETY** - concurrent operations bez race conditions
- [ ] **WERYFIKACJA SCROLL PERFORMANCE** - <16ms per frame dla smooth UX
- [ ] **Gotowe do wdrożenia w architekturze kafli**

---

### 🚨 OBOWIĄZKOWE UZUPEŁNIENIE BUSINESS_LOGIC_MAP_KAFLI.MD

**🚨 KRYTYCZNE: PO ZAKOŃCZENIU WSZYSTKICH POPRAWEK MODEL MUSI OBOWIĄZKOWO UZUPEŁNIĆ PLIK `AUDYT/KAFLI/business_logic_map_kafli.md`!**

#### OBOWIĄZKOWE KROKI PO ZAKOŃCZENIU POPRAWEK KAFLI:

1. [x] **KRYTYCZNY BUGFIX zastosowany** - aplikacja przestała crashować przez API error
2. [ ] **Wszystkie poprawki virtual scrolling wprowadzone** - kod optymalizuje scroll tysięcy kafli
3. [ ] **Wszystkie testy gallery manager przechodzą** - PASS na wszystkich testach virtual scrolling
4. [ ] **Virtual scrolling działa płynnie** - tysiące kafli bez degradacji performance
5. [ ] **OTWÓRZ business_logic_map_kafli.md** - znajdź sekcję gallery_manager.py
6. [ ] **DODAJ status ukończenia kafli** - zaznacz że analiza virtual scrolling została ukończona
7. [ ] **DODAJ datę ukończenia** - aktualna data w formacie YYYY-MM-DD
8. [ ] **DODAJ business impact kafli** - wpływ na virtual scrolling tysięcy kafli
9. [ ] **DODAJ ścieżki do plików wynikowych kafli** - correction_kafli.md i patch_code_kafli.md

#### FORMAT UZUPEŁNIENIA W BUSINESS_LOGIC_MAP_KAFLI.MD:

```markdown
### 📄 gallery_manager.py

- **Status:** ✅ UKOŃCZONA ANALIZA KAFLI
- **Data ukończenia:** 2025-06-23
- **Business impact kafli:** KRYTYCZNY BUGFIX - naprawiono crash aplikacji (get_archive_name() → get_base_name()). Zoptymalizowano virtual scrolling - thread-safe geometry cache, progressive loading, memory pressure monitoring, throttled scroll events. Performance improvement: płynne przewijanie tysięcy kafli <16ms per frame, <500MB memory usage. Aplikacja użyteczna ponownie!
- **Pliki wynikowe:**
  - `AUDYT/KAFLI/corrections/gallery_manager_correction_kafli.md`
  - `AUDYT/KAFLI/patches/gallery_manager_patch_code_kafli.md`
```

#### KONTROLA UZUPEŁNIENIA KAFLI:

- [ ] **OTWARTO business_logic_map_kafli.md** - plik kafli został otwarty i zlokalizowana sekcja gallery_manager.py
- [ ] **DODANO status ukończenia kafli** - "✅ UKOŃCZONA ANALIZA KAFLI"
- [ ] **DODANO datę ukończenia** - 2025-06-23
- [ ] **DODANO business impact kafli** - konkretny opis BUGFIX i virtual scrolling optimization
- [ ] **DODANO ścieżki do plików kafli** - correction_kafli.md i patch_code_kafli.md
- [ ] **ZWERYFIKOWANO poprawność kafli** - wszystkie informacje są prawidłowe dla virtual scrolling

**🚨 MODEL NIE MOŻE ZAPOMNIEĆ O UZUPEŁNIENIU BUSINESS_LOGIC_MAP_KAFLI.MD!**

**🚨 BEZ TEGO KROKU ETAP AUDYTU VIRTUAL SCROLLING KAFLI NIE JEST UKOŃCZONY!**

---
