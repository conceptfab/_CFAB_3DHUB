**⚠️ KRYTYCZNE: Przed rozpoczęciem pracy zapoznaj się z ogólnymi zasadami refaktoryzacji, poprawek i testowania opisanymi w pliku [refactoring_rules.md](../../_BASE_/refactoring_rules.md).**

---

# 📋 ETAP KAFLI: GALLERY_MANAGER.PY - ANALIZA I REFAKTORYZACJA

**Data analizy:** 2025-06-23

### 📋 Identyfikacja

- **Plik główny:** `src/ui/gallery_manager.py`
- **Plik z kodem (patch):** `../patches/gallery_manager_patch_code_kafli.md`
- **Priorytet:** ⚫⚫⚫⚫ (KRYTYCZNY - główny manager galerii kafli)
- **Zależności:**
  - `src/controllers/gallery_controller.py`
  - `src/models/file_pair.py`
  - `src/models/special_folder.py`
  - `src/ui.widgets.file_tile_widget.py`
  - `src.ui.widgets.special_folder_tile_widget.py`
  - `src.ui.widgets.tile_resource_manager.py`
  - `PyQt6.QtWidgets`, `PyQt6.QtCore`

---

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - **MASSIVE FILE (958 linii):** Plik narusza Single Responsibility Principle - miesza geometrię, memory management, virtual scrolling, widget creation
   - **Complex inheritance chain:** GalleryManager ma zbyt dużo odpowiedzialności (geometry + widgets + virtual scrolling + memory)  
   - **Thread safety issues:** Dostęp do shared state w wielu miejscach bez proper synchronization
   - **Resource leaks w force_create_all_tiles:** Modyfikacja globalnych limitów bez proper cleanup
   - **Import wewnątrz metod (linia 806, 808):** Performance overhead i problemy z imports
   - **Memory pressure na LayoutGeometry:** Cache bez limits może rosnąć bez kontroli

2. **Optymalizacje:**

   - **Redundant geometry calculations:** Multiple places obliczające te same geometry params 
   - **Virtual scrolling complexity:** VirtualScrollingMemoryManager ma mixed responsibilities
   - **Cache inefficiency:** LayoutGeometry cache nie ma size limits
   - **Batch processing hardcoded:** Batch sizes (20, 100) są hardcoded w różnych miejscach
   - **Threading bottlenecks:** Multiple locks (`_widgets_lock`, `_geometry_cache_lock`) mogą powodować deadlocks
   - **Scroll throttling complexity:** Complex scroll handling z multiple timers

3. **Refaktoryzacja:**

   - **Massive class decomposition:** GalleryManager wymaga podziału na 4-5 mniejszych klas
   - **Extract LayoutManager:** Cała logika LayoutGeometry powinna być w separate class
   - **Extract VirtualScrolling:** Virtual scrolling logic w osobnej klasie
   - **Extract WidgetFactory:** Widget creation logic w factory pattern
   - **Extract MemoryManager:** Standalone memory management dla kafli

4. **Logowanie:**
   - **Missing structured logging:** Brak metrics dla performance critical operations
   - **Debug overhead:** Excessive debug logging w hot paths
   - **No performance tracking:** Brak measurementów dla batch operations i scroll performance

---

### 🛠️ PLAN REFAKTORYZACJI

**Typ refaktoryzacji:** MAJOR DECOMPOSITION - Podział na multiple classes/Separation of Concerns

#### KROK 1: PRZYGOTOWANIE 🛡️

- [ ] **BACKUP UTWORZONY:** `gallery_manager_backup_2025-06-23.py` w folderze `AUDYT/KAFLI/backups/`
- [ ] **ANALIZA ZALEŻNOŚCI:** Sprawdzenie wszystkich dependencies i external calls
- [ ] **IDENTYFIKACJA API:** Lista publicznych metod używanych przez main_window i tile_manager
- [ ] **PLAN ETAPOWY:** Podział 958-liniowego pliku na logiczne komponenty

#### KROK 2: IMPLEMENTACJA 🔧

- [ ] **ZMIANA 1:** Extract LayoutGeometryManager jako standalone class z proper caching limits
- [ ] **ZMIANA 2:** Extract VirtualScrollingController z clean interface 
- [ ] **ZMIANA 3:** Extract TileWidgetFactory dla widget creation logic
- [ ] **ZMIANA 4:** Extract GalleryMemoryManager z proper resource tracking
- [ ] **ZMIANA 5:** Refactor GalleryManager jako coordinator z dependency injection
- [ ] **ZMIANA 6:** Implement ConfigurableBatchProcessor dla wszystkich batch operations
- [ ] **ZMIANA 7:** Add PerformanceTracker dla monitoring critical paths
- [ ] **ZACHOWANIE API:** Wszystkie publiczne metody zachowane dla backward compatibility
- [ ] **BACKWARD COMPATIBILITY:** 100% kompatybilność wsteczna z main_window

#### KROK 3: WERYFIKACJA PO KAŻDEJ ZMIANIE 🧪

- [ ] **TESTY AUTOMATYCZNE:** Uruchomienie testów po każdej zmianie
- [ ] **URUCHOMIENIE APLIKACJI:** Sprawdzenie czy aplikacja się uruchamia i galeria działa
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI:** Sprawdzenie czy wszystkie operacje kafli działają

#### KROK 4: INTEGRACJA FINALNA 🔗

- [ ] **TESTY INNYCH PLIKÓW:** Sprawdzenie czy tile_manager i main_window nadal działają
- [ ] **TESTY INTEGRACYJNE:** Pełne testy integracji z wszystkimi komponentami kafli
- [ ] **TESTY WYDAJNOŚCIOWE:** Virtual scrolling i batch processing nie mogą być wolniejsze

#### KRYTERIA SUKCESU REFAKTORYZACJI ✅

- [ ] **WSZYSTKIE TESTY PASS** - 100% testów przechodzi
- [ ] **APLIKACJA URUCHAMIA SIĘ** - bez błędów startowych
- [ ] **FUNKCJONALNOŚĆ ZACHOWANA** - wszystkie operacje galerii działają jak wcześniej
- [ ] **KOMPATYBILNOŚĆ WSTECZNA** - 100% backward compatibility
- [ ] **PERFORMANCE MAINTAINED** - virtual scrolling responsywny przy 1000+ kafli
- [ ] **MEMORY EFFICIENCY** - memory management nie powoduje leaks
- [ ] **CODE DECOMPOSITION** - plik podzielony na logiczne komponenty <300 linii każdy

---

### 🧪 PLAN TESTÓW AUTOMATYCZNYCH

**Test funkcjonalności podstawowej:**

- Test tworzenia kafli przez `create_tile_widget_for_pair`
- Test batch processing przez `force_create_all_tiles`
- Test virtual scrolling przez scroll events
- Test memory management przy dużych zbiorach kafli
- Test geometry calculations dla różnych rozmiarów okna

**Test integracji:**

- Test integracji z tile_manager przy batch creation
- Test integracji z main_window przy resize events  
- Test integracji z resource_manager przy memory limits
- Test integracji z special_folder_widgets

**Test wydajności:**

- Test virtual scrolling performance przy 1000+ kafli
- Test memory usage przy długotrwałym scrolling
- Test responsywności UI podczas batch operations
- Test cache efficiency dla geometry calculations

**Test thread safety:**

- Test concurrent access do gallery_tile_widgets
- Test concurrent geometry calculations
- Test race conditions w virtual scrolling
- Test memory management thread safety

---

### 📊 STATUS TRACKING

- [ ] Backup utworzony
- [ ] Plan refaktoryzacji przygotowany  
- [ ] **PHASE 1: LayoutGeometryManager extracted** (krok po kroku)
- [ ] **PHASE 2: VirtualScrollingController extracted** (krok po kroku)
- [ ] **PHASE 3: TileWidgetFactory extracted** (krok po kroku)
- [ ] **PHASE 4: GalleryMemoryManager extracted** (krok po kroku)
- [ ] **PHASE 5: GalleryManager refactored** (krok po kroku)
- [ ] Testy podstawowe przeprowadzone (PASS)
- [ ] Testy integracji przeprowadzone (PASS)
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI** - ręczne sprawdzenie wszystkich operacji galerii
- [ ] **WERYFIKACJA ZALEŻNOŚCI** - sprawdzenie, czy tile_manager i main_window nadal działają
- [ ] **WERYFIKACJA WYDAJNOŚCI** - porównanie z baseline virtual scrolling
- [ ] **WERYFIKACJA THREAD SAFETY** - testy concurrency dla all components
- [ ] **WERYFIKACJA MEMORY** - brak memory leaks przy długotrwałym użytkowaniu
- [ ] Dokumentacja zaktualizowana
- [ ] **Gotowe do wdrożenia**

---

### 🚨 OBOWIĄZKOWE UZUPEŁNIENIE BUSINESS_LOGIC_MAP_KAFLI.MD

**🚨 KRYTYCZNE: PO ZAKOŃCZENIU WSZYSTKICH POPRAWEK MODEL MUSI OBAWIĄZKOWO UZUPEŁNIĆ PLIK `AUDYT/KAFLI/business_logic_map_kafli.md`!**

#### OBOWIĄZKOWE KROKI PO ZAKOŃCZENIU POPRAWEK:

1. ✅ **Wszystkie poprawki wprowadzone** - kod działa poprawnie
2. ✅ **Wszystkie testy przechodzą** - PASS na wszystkich testach
3. ✅ **Aplikacja uruchamia się** - bez błędów startowych
4. ✅ **OTWÓRZ business_logic_map_kafli.md** - znajdź sekcję z gallery_manager.py
5. ✅ **DODAJ status ukończenia** - zaznacz że analiza została ukończona
6. ✅ **DODAJ datę ukończenia** - aktualna data w formacie YYYY-MM-DD
7. ✅ **DODAJ business impact** - opis wpływu na procesy kafli
8. ✅ **DODAJ ścieżki do plików wynikowych** - correction_kafli.md i patch_code_kafli.md

#### FORMAT UZUPEŁNIENIA W BUSINESS_LOGIC_MAP_KAFLI.MD:

```markdown
### 📄 GALLERY_MANAGER.PY

- **Status:** ✅ UKOŃCZONA ANALIZA KAFLI
- **Data ukończenia:** 2025-06-23
- **Business impact:** MAJOR REFACTORING - decomposition 958-liniowego pliku na logiczne komponenty, eliminacja SRP violations, poprawa thread safety, optymalizacja virtual scrolling i memory management dla tysięcy kafli
- **Pliki wynikowe:**
  - `AUDYT/KAFLI/corrections/gallery_manager_correction_kafli.md`
  - `AUDYT/KAFLI/patches/gallery_manager_patch_code_kafli.md`
```

#### KONTROLA UZUPEŁNIENIA:

- [ ] **OTWARTO business_logic_map_kafli.md** - plik został otwarty i zlokalizowana sekcja
- [ ] **DODANO status ukończenia** - "✅ UKOŃCZONA ANALIZA KAFLI"
- [ ] **DODANO datę ukończenia** - 2025-06-23
- [ ] **DODANO business impact** - konkretny opis MAJOR REFACTORING wpływu na procesy kafli
- [ ] **DODANO ścieżki do plików** - correction_kafli.md i patch_code_kafli.md
- [ ] **ZWERYFIKOWANO poprawność** - wszystkie informacje są prawidłowe

**🚨 MODEL NIE MOŻE ZAPOMNIEĆ O UZUPEŁNIENIU BUSINESS_LOGIC_MAP_KAFLI.MD!**

**🚨 BEZ TEGO KROKU ETAP NIE JEST UKOŃCZONY!**

---