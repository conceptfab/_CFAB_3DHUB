**⚠️ KRYTYCZNE: Przed rozpoczęciem pracy zapoznaj się z ogólnymi zasadami refaktoryzacji, poprawek i testowania opisanymi w pliku [refactoring_rules.md](refactoring_rules.md).**

---

# 📋 ETAP 1: SCANNER_CORE.PY - ANALIZA I REFAKTORYZACJA

**Data analizy:** 2025-01-24

### 📋 Identyfikacja

- **Plik główny:** `src/logic/scanner_core.py`
- **Plik z kodem (patch):** `../patches/scanner_core_patch_code.md`
- **Priorytet:** ⚫⚫⚫⚫
- **Zależności:**
  - `src/logic/file_pairing.py`
  - `src/logic/metadata_manager.py`
  - `src/logic/scanner_cache.py`
  - `src/models/file_pair.py`
  - `src/models/special_folder.py`
  - `src/utils/path_utils.py`

---

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - **Thread safety issue w ThreadSafeProgressManager:** `self.progress_callback(percent, message)` wywoływane poza lockiem może prowadzić do race conditions
   - **Memory overflow w ThreadSafeVisitedDirs:** Brak limitu rozmiaru może prowadzić do memory leak przy dużych katalogach
   - **Potencjalny deadlock:** Wywołanie `progress_callback` może blokować wątek jeśli callback jest synchroniczny
   - **Race condition w `_perform_memory_cleanup`:** Funkcja może być wywoływana przez wiele wątków jednocześnie

2. **Optymalizacje responsywności UI:**

   - **Progress throttling zbyt agresywne:** Interwał 0.1s może być za długi dla responsywnego UI
   - **Brak adaptacji do rozmiaru okna:** Scanner nie uwzględnia aktualnych rozmiarów galerii przy raportowaniu postępu
   - **Sztywne progi memory cleanup:** GC_INTERVAL_FILES=1000 może być nieoptymalne dla różnych rozmiarów katalogów
   - **Brak priorytetyzacji skanowania:** Wszystkie pliki traktowane równo, bez uwzględnienia widoczności w UI

3. **Refaktoryzacja:**

   - **Monolityczna funkcja `_walk_directory_streaming`:** 100+ linii kodu, zbyt złożona
   - **Duplikat logiki progress reporting:** Rozrzucona w wielu miejscach
   - **Over-engineered ThreadSafeVisitedDirs:** Zbyt skomplikowane jak na swoją funkcję
   - **Niepotrzebna kompleksowość w memory monitoring:** Zbyt szczegółowe logowanie memory usage

4. **Responsywność UI:**
   - **Brak real-time feedback dla UI:** Progress callback nie zawiera informacji o aktualnie przetwarzanych plikach
   - **Brak adaptacji do viewport:** Scanner nie wie które pliki są aktualnie widoczne w galerii
   - **Sztywny algorytm skanowania:** Nie dostosowuje się do aktualnego stanu UI

---

### 🛠️ PLAN REFAKTORYZACJI

**Typ refaktoryzacji:** Optymalizacja responsywności UI + Thread safety improvements

#### KROK 1: PRZYGOTOWANIE 🛡️

- [ ] **BACKUP UTWORZONY:** `scanner_core_backup_2025-01-24.py` w folderze `AUDYT/backups/`
- [ ] **ANALIZA ZALEŻNOŚCI:** Sprawdzenie wszystkich imports i wywołań
- [ ] **IDENTYFIKACJA API:** Lista publicznych metod używanych przez inne pliki
- [ ] **PLAN ETAPOWY:** Podział refaktoryzacji na małe, weryfikowalne kroki

#### KROK 2: IMPLEMENTACJA 🔧

- [ ] **ZMIANA 1:** Wprowadzenie UI-aware progress reporting z viewport tracking
- [ ] **ZMIANA 2:** Optymalizacja ThreadSafeProgressManager dla responsywności UI
- [ ] **ZMIANA 3:** Uproszczenie ThreadSafeVisitedDirs z lepszym memory management
- [ ] **ZMIANA 4:** Wprowadzenie adaptacyjnego skanowania priorytetowego
- [ ] **ZACHOWANIE API:** Wszystkie publiczne metody zachowane lub z deprecation warnings
- [ ] **BACKWARD COMPATIBILITY:** 100% kompatybilność wsteczna zachowana

#### KROK 3: WERYFIKACJA PO KAŻDEJ ZMIANIE 🧪

- [ ] **TESTY AUTOMATYCZNE:** Uruchomienie testów po każdej zmianie
- [ ] **URUCHOMIENIE APLIKACJI:** Sprawdzenie czy aplikacja się uruchamia
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI:** Sprawdzenie czy wszystkie funkcje działają
- [ ] **TEST RESPONSYWNOŚCI:** Sprawdzenie czy UI pozostaje responsywne podczas skanowania

#### KROK 4: INTEGRACJA FINALNA 🔗

- [ ] **TESTY INNYCH PLIKÓW:** Sprawdzenie czy inne moduły nadal działają
- [ ] **TESTY INTEGRACYJNE:** Pełne testy integracji z całą aplikacją
- [ ] **TESTY WYDAJNOŚCIOWE:** Wydajność nie pogorszona o więcej niż 5%
- [ ] **TEST UI RESPONSIVENESS:** Sprawdzenie czy galeria nie znika przy resize

#### KRYTERIA SUKCESU REFAKTORYZACJI ✅

- [ ] **WSZYSTKIE TESTY PASS** - 100% testów przechodzi
- [ ] **APLIKACJA URUCHAMIA SIĘ** - bez błędów startowych
- [ ] **FUNKCJONALNOŚĆ ZACHOWANA** - wszystkie funkcje działają jak wcześniej
- [ ] **KOMPATYBILNOŚĆ WSTECZNA** - 100% backward compatibility
- [ ] **UI RESPONSYWNOŚĆ** - galeria pozostaje responsywna podczas skanowania
- [ ] **ADAPTACJA DO VIEWPORT** - skanowanie priorytetyzuje widoczne elementy

---

### 🧪 PLAN TESTÓW AUTOMATYCZNYCH

**Test funkcjonalności podstawowej:**

- Test skanowania małego katalogu (100 plików) z weryfikacją wszystkich znalezionych par
- Test skanowania dużego katalogu (10000+ plików) z monitowaniem memory usage
- Test przerwania skanowania przez użytkownika (interrupt_check)
- Test thread safety przy równoczesnych wywołaniach scan_folder_for_pairs
- Test cache hit/miss scenarios z różnymi parametrami

**Test integracji:**

- Test integracji z gallery_tab.py - sprawdzenie czy progress callback działa poprawnie
- Test integracji z file_tile_widget.py - weryfikacja czy kafle są tworzone prawidłowo
- Test integracji z metadata_manager.py - sprawdzenie cache'owania metadanych

**Test responsywności UI:**

- Test responsywności galerii podczas skanowania dużego katalogu
- Test adaptacji liczby kolumn przy zmianie rozmiaru okna podczas skanowania
- Test braku znikania galerii przy resize podczas skanowania
- Test priorytetowego ładowania widocznych kafli

**Test wydajności:**

- Benchmark skanowania 1000+ plików/sekundę
- Test memory usage <500MB dla dużych katalogów
- Test UI responsiveness <100ms podczas skanowania
- Test throttling progress callbacks dla płynności UI

---

### 📊 STATUS TRACKING

- [ ] Backup utworzony
- [ ] Plan refaktoryzacji przygotowany
- [ ] Kod zaimplementowany (krok po kroku)
- [ ] Testy podstawowe przeprowadzone (PASS)
- [ ] Testy integracji przeprowadzone (PASS)
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI** - ręczne sprawdzenie kluczowych funkcji
- [ ] **WERYFIKACJA ZALEŻNOŚCI** - sprawdzenie, czy nie zepsuto innych modułów
- [ ] **WERYFIKACJA WYDAJNOŚCI** - porównanie z baseline
- [ ] **WERYFIKACJA UI RESPONSYWNOŚCI** - sprawdzenie responsywności galerii
- [ ] Dokumentacja zaktualizowana
- [ ] **Gotowe do wdrożenia**

---

### 🎯 SPECYFICZNE POPRAWKI RESPONSYWNOŚCI UI

#### 1. **UI-Aware Progress Manager**
- Wprowadzenie callback'a z informacją o aktualnie przetwarzanych plikach
- Dodanie parametru viewport_size dla adaptacji progress reporting
- Implementacja priority-based progress updates

#### 2. **Viewport-Aware Scanning**
- Dodanie parametru visible_area dla priorytetowego skanowania widocznych plików
- Implementacja adaptive scanning strategy
- Optymalizacja memory usage na podstawie wielkości viewport

#### 3. **Responsive Progress Throttling**
- Zmiana throttle_interval z 0.1s na 0.05s dla lepszej responsywności
- Wprowadzenie adaptive throttling w zależności od wielkości katalogu
- Dodanie burst mode dla małych katalogów

#### 4. **Adaptive Memory Management**
- Dynamiczny GC_INTERVAL_FILES w zależności od memory pressure
- Memory cleanup trigger na podstawie viewport size
- Responsive memory monitoring z UI feedback

---

### 🚨 OBOWIĄZKOWE UZUPEŁNIENIE BUSINESS_LOGIC_MAP.MD

**🚨 KRYTYCZNE: PO ZAKOŃCZENIU WSZYSTKICH POPRAWEK MODEL MUSI OBAWIĄZKOWO UZUPEŁNIĆ PLIK `AUDYT/business_logic_map.md`!**

#### OBOWIĄZKOWE KROKI PO ZAKOŃCZENIU POPRAWEK:

1. ✅ **Wszystkie poprawki wprowadzone** - kod działa poprawnie
2. ✅ **Wszystkie testy przechodzą** - PASS na wszystkich testach
3. ✅ **Aplikacja uruchamia się** - bez błędów startowych
4. ✅ **UI responsywność zweryfikowana** - galeria nie znika przy resize
5. ✅ **OTWÓRZ business_logic_map.md** - znajdź sekcję z analizowanym plikiem
6. ✅ **DODAJ status ukończenia** - zaznacz że analiza została ukończona
7. ✅ **DODAJ datę ukończenia** - aktualna data w formacie YYYY-MM-DD
8. ✅ **DODAJ business impact** - opis wpływu na procesy biznesowe
9. ✅ **DODAJ ścieżki do plików wynikowych** - correction.md i patch_code.md

#### FORMAT UZUPEŁNIENIA W BUSINESS_LOGIC_MAP.MD:

```markdown
### 📄 SCANNER_CORE.PY

- **Status:** ✅ UKOŃCZONA ANALIZA
- **Data ukończenia:** 2025-01-24
- **Business impact:** Zwiększona responsywność UI galerii, eliminacja znikania galerii przy resize, priorytetowe skanowanie widocznych elementów, optymalizacja memory usage dla dużych katalogów
- **Pliki wynikowe:**
  - `AUDYT/corrections/scanner_core_correction.md`
  - `AUDYT/patches/scanner_core_patch_code.md`
```

#### KONTROLA UZUPEŁNIENIA:

- [ ] **OTWARTO business_logic_map.md** - plik został otwarty i zlokalizowana sekcja
- [ ] **DODANO status ukończenia** - "✅ UKOŃCZONA ANALIZA"
- [ ] **DODANO datę ukończenia** - aktualna data w formacie YYYY-MM-DD
- [ ] **DODANO business impact** - konkretny opis wpływu na procesy biznesowe
- [ ] **DODANO ścieżki do plików** - correction.md i patch_code.md
- [ ] **ZWERYFIKOWANO poprawność** - wszystkie informacje są prawidłowe

**🚨 MODEL NIE MOŻE ZAPOMNIEĆ O UZUPEŁNIENIU BUSINESS_LOGIC_MAP.MD!**

**🚨 BEZ TEGO KROKU ETAP NIE JEST UKOŃCZONY!**

---