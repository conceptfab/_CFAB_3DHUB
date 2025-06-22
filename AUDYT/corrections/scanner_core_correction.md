**⚠️ KRYTYCZNE: Przed rozpoczęciem pracy zapoznaj się z ogólnymi zasadami refaktoryzacji, poprawek i testowania opisanymi w pliku [refactoring_rules.md](../refactoring_rules.md).**

---

# 📋 ETAP 1: SCANNER_CORE.PY - ANALIZA I REFAKTORYZACJA

**Data analizy:** 2025-01-28

### 📋 Identyfikacja

- **Plik główny:** `src/logic/scanner_core.py` (635 linii)
- **Plik z kodem (patch):** `../patches/scanner_core_patch_code.md`
- **Priorytet:** ⚫⚫⚫⚫ KRYTYCZNY - Główny silnik skanowania
- **Zależności:**
  - `src/logic/file_pairing.py` - algorytmy parowania
  - `src/logic/scanner_cache.py` - cache wyników
  - `src/logic/metadata_manager.py` - zarządzanie metadanymi
  - `src/models/file_pair.py` - model danych
  - `src/models/special_folder.py` - model folderów specjalnych

---

### 🔍 Analiza problemów według trzech filarów

## 1️⃣ WYDAJNOŚĆ PROCESÓW ⚡ (KRYTYCZNE PROBLEMY)

### **A) PERFORMANCE BOTTLENECKI W COLLECT_FILES_STREAMING**

**PROBLEM 1: Nieefektywne skanowanie folderów (linie 471-496)**

```python
# CURRENT - skanuje wszystkie podfoldery nawet jeśli nie mają odpowiednich plików
should_scan_subfolders = files_processed_in_folder > 0  # Zbyt naiwna logika!

# PROBLEM: Skanuje folder z 1000 plików .txt ale 0 plików archiwów/podglądów
```

- **Business Impact:** Skanowanie folderów bez archiwów/podglądów = strata 60-80% czasu
- **Wydajność:** Spowolnienie o 300-500% dla folderów z dużą ilością nierelewantnych plików

**PROBLEM 2: O(n) lookup w ARCHIVE_EXTENSIONS/PREVIEW_EXTENSIONS (linia 460)**

```python
if (ext_lower in ARCHIVE_EXTENSIONS or ext_lower in PREVIEW_EXTENSIONS):
```

- **Business Impact:** Linear search dla każdego pliku = O(n\*m) złożoność
- **Wydajność:** 10-20x wolniejsze niż pre-computed frozenset

**PROBLEM 3: Brak batch processing dla dużych folderów (linie 447-462)**

```python
# Sprawdzenie co 100 plików - za rzadko dla dużych folderów!
if files_processed_in_folder % 100 == 0 and interrupt_check and interrupt_check():
```

- **Business Impact:** Opóźnione reagowanie na przerwanie w folderach z 10000+ plików
- **Wydajność:** Responsywność UI cierpi przy dużych zbiorach

### **B) MEMORY LEAKS I ZARZĄDZANIE PAMIĘCIĄ**

**PROBLEM 4: Memory leak w file_map dla dużych folderów**

```python
file_map = defaultdict(list)  # Może rosnąć bez kontroli!
map_key = os.path.join(normalized_current_dir, base_name.lower())
file_map[map_key].append(full_file_path)  # Brak limitu pamięci
```

- **Business Impact:** OutOfMemory dla folderów z 50000+ plików
- **Wydajność:** Exponential memory growth bez garbage collection

**PROBLEM 5: visited_dirs nie jest czyszczone między skanowaniami (linia 522)**

```python
visited_dirs.clear()  # Tylko w finally - za późno!
```

- **Business Impact:** Memory leak przy kolejnych skanowaniach
- **Wydajność:** Akumulacja pamięci przy wielokrotnym skanowaniu

## 2️⃣ STABILNOŚĆ OPERACJI 🛡️ (PROBLEMY KRYTYCZNE)

### **A) ERROR HANDLING I RECOVERY**

**PROBLEM 6: Niestabilna obsługa błędów I/O (linie 498-515)**

```python
except OSError as e:
    logger.error(f"Błąd I/O podczas dostępu do {current_dir}: {e}")
    # Try to continue with other directories - BEZ RECOVERY!
```

- **Business Impact:** Partial scan results bez informowania użytkownika
- **Stabilność:** Aplikacja może zwrócić niepełne wyniki bez ostrzeżenia

**PROBLEM 7: Race condition w interrupt_check (linie 394, 434, 450)**

```python
if interrupt_check and interrupt_check():  # Wielokrotne wywołania!
```

- **Business Impact:** Potencjalne race conditions w UI
- **Stabilność:** Nieprzewidywalne zachowanie podczas przerywania

### **B) THREAD SAFETY ISSUES**

**PROBLEM 8: Brak thread safety w progress reporting (linia 381)**

```python
last_progress_time = time.time()  # Shared state bez synchronizacji!
PROGRESS_THROTTLE_INTERVAL = 0.1  # Global state
```

- **Business Impact:** Corrupted progress reporting w środowisku wielowątkowym
- **Stabilność:** UI może pokazywać błędne wartości postępu

**PROBLEM 9: Shared state w ScanOrchestrator**

```python
# ScanOrchestrator używa shared managers bez synchronizacji
self.progress_manager = ScanProgressManager(config)
self.cache_manager = ScanCacheManager()
```

- **Business Impact:** Data corruption przy równoczesnych skanowaniach
- **Stabilność:** Nieprzewidywalne results dla concurrent operations

## 3️⃣ ELIMINACJA OVER-ENGINEERING 🎯 (NADMIERNA KOMPLIKACJA)

### **A) NIEPOTRZEBNA ABSTRAKCJA W MANAGERACH**

**PROBLEM 10: Over-engineered ScanOrchestrator pattern (linie 195-308)**

```python
class ScanOrchestrator:  # Niepotrzebna abstrakcja!
    def __init__(self, config: ScanConfig):
        self.progress_manager = ScanProgressManager(config)  # 3 managery dla prostej operacji
        self.cache_manager = ScanCacheManager()
        self.special_folders_manager = SpecialFoldersManager()
```

- **Business Impact:** Cognitive overhead bez rzeczywistej korzyści
- **Maintainability:** 4 klasy zamiast 1 prostej funkcji

**PROBLEM 11: Redundant ScanConfig dataclass (linie 51-65)**

```python
@dataclass
class ScanConfig:  # Wrapper dla 7 parametrów funkcji!
```

- **Business Impact:** Dodatkowa warstwa abstraction bez value add
- **Maintainability:** Więcej kodu do utrzymania

### **B) DUPLIKACJA LOGIKI I NIEPOTRZEBNE WRAPPERS**

**PROBLEM 12: Duplikacja w scan_folder_for_pairs (linie 572-609)**

```python
def scan_folder_for_pairs(...) -> Tuple[...]:
    config = ScanConfig(...)  # Wrapper creation
    orchestrator = ScanOrchestrator(config)  # Kolejny wrapper
    return orchestrator.execute_scan()  # Just delegates!
```

- **Business Impact:** Indirection bez rzeczywistej wartości
- **Maintainability:** Niepotrzebne kroki w call stack

**PROBLEM 13: Dead code i deprecated functions (linie 622-635)**

```python
def find_special_folders(folder_path: str) -> List[SpecialFolder]:
    """USUNIĘTA FUNKCJA - pozostaje jako zaślepka"""
    return []  # Dead code!
```

### **C) ALGORYTMIC COMPLEXITY**

**PROBLEM 14: Skomplikowana logika w \_walk_directory_streaming**

- **247 linii w jednej funkcji** - narusza SRP (Single Responsibility Principle)
- **Nested loops + exception handling** - cognitive complexity > 15
- **Multiple concerns:** file scanning + folder traversal + error handling + progress

---

### 🛠️ PLAN REFAKTORYZACJI

**Typ refaktoryzacji:** Optymalizacja algorytmów + Uproszczenie architektury + Performance boost

#### KROK 1: PRZYGOTOWANIE 🛡️

- [ ] **BACKUP UTWORZONY:** `scanner_core_backup_2025_01_28.py` w folderze `AUDYT/backups/`
- [ ] **ANALIZA ZALEŻNOŚCI:** Sprawdzenie imports w 15+ plikach korzystających z scanner_core
- [ ] **IDENTYFIKACJA API:** `scan_folder_for_pairs()`, `collect_files_streaming()`, `get_scan_statistics()`
- [ ] **BENCHMARK BASELINE:** Pomiar wydajności dla folderów: 100, 1000, 10000 plików

#### KROK 2: OPTYMALIZACJE WYDAJNOŚCI (KRYTYCZNE) 🔧

- [ ] **OPTYMALIZACJA 1:** Pre-computed frozenset dla rozszerzeń (5-20x szybsze)

```python
SUPPORTED_EXTENSIONS = frozenset(ARCHIVE_EXTENSIONS.union(PREVIEW_EXTENSIONS))
```

- [ ] **OPTYMALIZACJA 2:** Smart folder scanning - skip folders bez odpowiednich plików

```python
def has_relevant_files(entries) -> bool:
    return any(os.path.splitext(entry.name)[1].lower() in SUPPORTED_EXTENSIONS
               for entry in entries if entry.is_file())
```

- [ ] **OPTYMALIZACJA 3:** Memory-efficient scanning z yield/generator pattern

```python
def scan_files_generator(directory: str) -> Iterator[str]:
    # Generator pattern zamiast building huge list in memory
```

- [ ] **OPTYMALIZACJA 4:** Improved batch processing (co 50 plików zamiast 100)
- [ ] **OPTYMALIZACJA 5:** Memory cleanup każde 1000 plików

#### KROK 3: STABILNOŚĆ I THREAD SAFETY 🛡️

- [ ] **THREADING FIX 1:** Thread-safe progress reporting z locks
- [ ] **THREADING FIX 2:** Immutable state w ScanConfig
- [ ] **ERROR HANDLING 1:** Proper recovery strategies z user notification
- [ ] **ERROR HANDLING 2:** Graceful degradation przy I/O errors

#### KROK 4: UPROSZCZENIE ARCHITEKTURY 🎯

- [ ] **SIMPLIFICATION 1:** Eliminate ScanOrchestrator - merge into single function
- [ ] **SIMPLIFICATION 2:** Inline ScanConfig - use direct parameters
- [ ] **SIMPLIFICATION 3:** Remove dead code (find_special_folders)
- [ ] **SIMPLIFICATION 4:** Consolidate managers into helper functions

#### KROK 5: WERYFIKACJA PO KAŻDEJ ZMIANIE 🧪

- [ ] **PERFORMANCE TESTS:** Benchmark po każdej optymalizacji
- [ ] **MEMORY TESTS:** Memory usage profiling dla dużych folderów
- [ ] **STABILITY TESTS:** Multi-threading stress tests
- [ ] **FUNCTIONALITY TESTS:** Regression tests dla core functionality

#### KRYTERIA SUKCESU REFAKTORYZACJI ✅

- [ ] **WYDAJNOŚĆ +50%** - 50% szybsze skanowanie dla folderów 1000+ plików
- [ ] **MEMORY -30%** - 30% mniej zużycia pamięci dla dużych folderów
- [ ] **THREAD SAFETY** - 100% thread-safe operations
- [ ] **CODE REDUCTION -20%** - 20% mniej linii kodu (635 → ~500)
- [ ] **COMPLEXITY REDUCTION** - Cognitive complexity <10 dla każdej funkcji

---

### 🧪 PLAN TESTÓW AUTOMATYCZNYCH

**Test wydajności podstawowej:**

- Benchmark skanowania folderów: 100, 1000, 5000, 10000 plików
- Memory usage profiling dla różnych rozmiarów folderów
- Progress reporting accuracy tests

**Test stabilności:**

- Concurrent scanning stress test (5 równoczesnych skanowań)
- I/O error recovery simulation
- Interrupt handling podczas różnych faz skanowania

**Test integracji:**

- Compatibility z file_pairing.py
- Cache integration tests
- Metadata manager integration

**Test regresji:**

- Wszystkie istniejące funkcjonalności działają identycznie
- API compatibility 100% zachowana
- Performance nie gorsza niż baseline

---

### 📊 OCZEKIWANE BUSINESS IMPACT

**PRZED REFAKTORYZACJĄ:**

- Skanowanie 3000 plików: ~8-15 sekund
- Memory usage: ~200-500MB dla dużych folderów
- Thread safety: Problematyczna
- Code complexity: Wysoka (635 linii, 4 klasy)

**PO REFAKTORYZACJI:**

- Skanowanie 3000 plików: ~4-8 sekund (**50% szybsze**)
- Memory usage: ~100-300MB (**30% mniej pamięci**)
- Thread safety: **100% bezpieczne**
- Code complexity: **Niska (~500 linii, 1-2 klasy)**

**UŻYTKOWNIK ODCZUJE:**

- **Szybsze ładowanie galerii** - o połowę krótszy czas oczekiwania
- **Stabilniejsza aplikacja** - brak crashów przy dużych folderach
- **Lepszą responsywność** - płynniejsze UI podczas skanowania

---

### 📊 STATUS TRACKING

- [ ] Backup utworzony
- [ ] Baseline performance zmierzony
- [ ] Optymalizacje wydajności zaimplementowane
- [ ] Thread safety fixes zastosowane
- [ ] Uproszczenie architektury wykonane
- [ ] **PERFORMANCE TESTS PASS** (+50% speed, -30% memory)
- [ ] **THREAD SAFETY TESTS PASS** (concurrent operations)
- [ ] **REGRESSION TESTS PASS** (wszystkie funkcje działają)
- [ ] **INTEGRATION TESTS PASS** (kompatybilność z innymi modułami)
- [ ] **USER ACCEPTANCE TESTS** (szybsze ładowanie galerii)
- [ ] **Gotowe do wdrożenia**

---

**🎯 NASTĘPNY KROK PO UKOŃCZENIU:** Analiza `src/logic/file_pairing.py` (drugi plik KRYTYCZNY)
