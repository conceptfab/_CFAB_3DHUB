# 🗺️ MAPA PLIKÓW FUNKCJONALNOŚCI BIZNESOWEJ

**Wygenerowano na podstawie aktualnego kodu: 2025-01-23**

**Kontekst biznesowy aplikacji CFAB_3DHUB:**

- Aplikacja do zarządzania sparowanych plików archiwów (RAR, ZIP) i podglądów (JPEG, PNG)
- Kluczowe wymagania: skanowanie 1000+ plików/sek, <500MB RAM, obsługa dziesiątek tysięcy plików
- Architektura: Scanner Core → File Pairing → UI Gallery z Virtual Scrolling
- Operacje asynchroniczne z thread safety, intelligent caching, batch processing

**Odkryte katalogi z logiką biznesową:**

- **logic/** - Główne algorytmy biznesowe (skanowanie, parowanie, cache)
- **controllers/** - Kontrolery koordynujące procesy biznesowe
- **services/** - Serwisy biznesowe (warstwa abstrakcji)
- **models/** - Modele danych biznesowych
- **ui/** - Komponenty interfejsu z logiką prezentacji
- **config/** - Konfiguracja wpływająca na procesy biznesowe

---

## 📊 DYNAMICZNE PRIORYTETY ANALIZY

**Wygenerowano na podstawie analizy kodu i kontekstu biznesowego: 2025-01-23**

### ⚫⚫⚫⚫ KRYTYCZNE - Podstawowa funkcjonalność aplikacji

**Uzasadnienie:** Te komponenty implementują główne algorytmy biznesowe wpływające bezpośrednio na wydajność aplikacji (target 1000+ files/sec) i zarządzanie pamięcią (<500MB RAM).

- **logic/scanner_core.py** - Główny algorytm skanowania katalogów, thread-safe progress management, memory optimization
- **logic/file_pairing.py** - Algorytmy parowania plików z Trie-based matching, O(n log m) complexity
- **logic/scanner_cache.py** - ThreadSafeCache z LRU+TTL, memory monitoring, singleton pattern

### 🔴🔴🔴 WYSOKIE - Ważne operacje biznesowe

**Uzasadnienie:** Komponenty koordynujące procesy biznesowe, serwisy implementujące główne funkcjonalności aplikacji oraz kluczowe modele danych.

- **services/scanning_service.py** - Service layer nad scanner_core, batch operations, performance metrics
- **controllers/main_window_controller.py** - Centralny kontroler MVC, koordynacja między serwisami
- **services/file_operations_service.py** - File I/O operations, bulk operations, cross-platform support
- **models/file_pair.py** - Core domain model, path handling, thumbnail management
- **logic/metadata_manager.py** - Persistent metadata storage, buffered writes, file locking
- **services/thread_coordinator.py** - Centralized thread management, resource cleanup

### 🟡🟡 ŚREDNIE - Funkcjonalności pomocnicze

**Uzasadnienie:** Komponenty wspierające główne procesy biznesowe, abstraction layers i specialized features.

- **logic/file_operations.py** - Factory pattern dla file operations, batch command pattern
- **controllers/scan_result_processor.py** - Processing separacji, statistics calculation
- **controllers/selection_manager.py** - Management selekcji plików w UI
- **controllers/file_operations_controller.py** - Kontroler operacji na plikach
- **config/config_core.py** - Główna logika konfiguracji aplikacji

### 🟢 NISKIE - Funkcjonalności dodatkowe

**Uzasadnienie:** Specialized features o ograniczonym scope, utility functions, pomocnicze komponenty.

- **models/special_folder.py** - Model dla tex/textures folders, specialized feature
- **controllers/special_folders_manager.py** - Zarządzanie folderami specjalnymi
- **config/properties/** - Definicje właściwości (extensions, thumbnails, colors)
- **utils/** - Utility functions (path_utils, image_utils, logging_config)

### 📈 METRYKI PRIORYTETÓW

**Na podstawie analizy kodu:**

- **Plików krytycznych:** 3
- **Plików wysokich:** 6
- **Plików średnich:** 5
- **Plików niskich:** 4+
- **Łącznie przeanalizowanych:** 18+

**Rozkład priorytetów:** 17% krytyczne, 33% wysokie, 28% średnie, 22% niskie

---

## 🗂️ SZCZEGÓŁOWA MAPA KATALOGÓW

### **LOGIC** (src/logic/)

```
logic/
├── scanner_core.py ⚫⚫⚫⚫ - GŁÓWNY ALGORYTM SKANOWANIA: collect_files_streaming, scan_folder_for_pairs, ThreadSafeProgressManager
├── file_pairing.py ⚫⚫⚫⚫ - ALGORYTMY PAROWANIA: OptimizedBestMatchStrategy, SimpleTrie, create_file_pairs
├── scanner_cache.py ⚫⚫⚫⚫ - CACHE MANAGEMENT: ThreadSafeCache singleton, LRU+TTL, memory monitoring
├── metadata_manager.py 🔴🔴🔴 - METADATA PERSISTENCE: MetadataManager, SimplifiedBufferManager, file locking
├── file_operations.py 🟡🟡 - FILE OPS FACTORY: FileOperationsFactory, BatchFileOperations, validation
├── scanner.py 🟡🟡 - HIGH-LEVEL SCANNER: wrapper nad scanner_core, legacy interface
└── file_ops_components/ 🟡🟡 - COMPONENTS: file_opener, file_pair_operations, file_system_operations
```

### **SERVICES** (src/services/)

```
services/
├── scanning_service.py 🔴🔴🔴 - SCANNING SERVICE: ScanResult, PerformanceMetrics, multi-directory support
├── file_operations_service.py 🔴🔴🔴 - FILE OPS SERVICE: bulk operations, cross-platform trash, manual pairing
└── thread_coordinator.py 🔴🔴🔴 - THREAD MANAGEMENT: ThreadCoordinator, resource cleanup, operation tracking
```

### **CONTROLLERS** (src/controllers/)

```
controllers/
├── main_window_controller.py 🔴🔴🔴 - MAIN CONTROLLER: central MVC controller, service coordination
├── scan_result_processor.py 🟡🟡 - RESULT PROCESSING: statistics calculation, validation helpers
├── selection_manager.py 🟡🟡 - SELECTION MANAGEMENT: file selection logic, state management
├── file_operations_controller.py 🟡🟡 - FILE OPS CONTROLLER: operacje na plikach, bulk operations
└── special_folders_manager.py 🟢 - SPECIAL FOLDERS: zarządzanie folderami specjalnymi
```

### **MODELS** (src/models/)

```
models/
├── file_pair.py 🔴🔴🔴 - CORE DOMAIN MODEL: FilePair, path handling, thumbnail loading
└── special_folder.py 🟢 - SPECIAL FOLDER MODEL: tex/textures folders, file counting
```

### **CONFIG** (src/config/)

```
config/
├── config_core.py 🟡🟡 - MAIN CONFIG: configuration management, settings persistence
├── config_properties.py 🟡🟡 - CONFIG PROPERTIES: application properties, validation
└── properties/
    ├── extension_properties.py 🟢 - FILE EXTENSIONS: supported formats definition
    ├── thumbnail_properties.py 🟢 - THUMBNAIL CONFIG: miniaturek properties
    ├── format_properties.py 🟢 - FORMAT CONFIG: file format properties
    └── color_properties.py 🟢 - COLOR CONFIG: color scheme properties
```

### **UI** (src/ui/) - Komponenty z Logiką Biznesową

```
ui/main_window/
├── main_window.py 🟡🟡 - MAIN WINDOW: główne okno aplikacji, UI state management
├── scan_manager.py 🟡🟡 - SCAN UI MANAGER: UI dla operacji skanowania
├── tile_manager.py 🟡🟡 - TILE MANAGER: zarządzanie kafelkami w galerii
└── worker_manager.py 🟡🟡 - WORKER UI MANAGER: zarządzanie workerami UI

ui/widgets/
├── file_tile_widget.py ⚫⚫⚫⚫ - FILE TILE: widget kafelka pliku, thumbnail rendering, drag&drop, metadata
├── thumbnail_cache.py ⚫⚫⚫⚫ - THUMBNAIL CACHE: centralny cache miniaturek, memory management, async loading
└── unpaired_files_tab.py 🟡🟡 - UNPAIRED FILES: zarządzanie niesparowanymi plikami
```

---

## 🎯 PLAN AUDYTU LOGIKI BIZNESOWEJ

### FAZA 1: KRYTYCZNE ALGORYTMY ⚫⚫⚫⚫

**Priorytet 1:** `logic/scanner_core.py`

- **Status:** ✅ UKOŃCZONA IMPLEMENTACJA
- **Data ukończenia:** 2025-01-28
- **Business impact:** Zoptymalizowano główny algorytm skanowania: thread safety fixes, memory optimization <500MB, performance monitoring >1000 files/sec. Enhanced progress reporting i error handling. ThreadSafeVisitedDirs z size limits (50k entries), enhanced memory monitoring z detailed reporting, dataclass ScanContext dla parameter optimization.
- **Pliki wynikowe:**
  - `AUDYT/corrections/scanner_core_correction.md`
  - `AUDYT/patches/scanner_core_patch_code.md`

**Priorytet 2:** `logic/file_pairing.py`

- **Status:** ⏳ OCZEKUJE NA ANALIZĘ
- **Cel:** Audyt algorytmów parowania, O(n log m) complexity, memory cleanup
- **Metryki:** Weryfikacja target <500MB RAM

**Priorytet 3:** `logic/scanner_cache.py`

- **Status:** ⏳ OCZEKUJE NA ANALIZĘ
- **Cel:** Audyt cache management, thread safety, memory monitoring
- **Metryki:** Cache hit ratio, memory usage optimization

### FAZA 1B: KRYTYCZNE UI KOMPONENTY ⚫⚫⚫⚫

**Priorytet 4:** `ui/widgets/file_tile_widget.py`

- **Status:** ✅ UKOŃCZONA ANALIZA
- **Data ukończenia:** 2025-01-23
- **Business impact:** Zoptymalizowano główny widget galerii par plików: thread safety fixes, architecture simplification, memory optimization <1MB/widget, enhanced performance <16ms rendering. Foundation dla responsive UI z 1000+ tiles.
- **Pliki wynikowe:**
  - `AUDYT/corrections/file_tile_widget_correction.md`
  - `AUDYT/patches/file_tile_widget_patch_code.md`

**Priorytet 5:** `ui/widgets/thumbnail_cache.py`

- **Status:** ✅ UKOŃCZONA ANALIZA
- **Data ukończenia:** 2025-01-23
- **Business impact:** Zoptymalizowano centralny cache miniaturek: thread safety fixes, async loading implementation, memory optimization <200MB, enhanced LRU strategy. Foundation dla responsive thumbnail loading z 1000+ images.
- **Pliki wynikowe:**
  - `AUDYT/corrections/thumbnail_cache_correction.md`
  - `AUDYT/patches/thumbnail_cache_patch_code.md`

### FAZA 2: GŁÓWNE SERWISY 🔴🔴🔴

**Priorytet 6:** `services/scanning_service.py`

- **Status:** ⏳ OCZEKUJE NA ANALIZĘ
- **Cel:** Audyt service layer, batch operations, performance metrics

**Priorytet 7:** `controllers/main_window_controller.py`

- **Status:** ⏳ OCZEKUJE NA ANALIZĘ
- **Cel:** Audyt central controller, service coordination, state management

**Priorytet 8:** `services/file_operations_service.py`

- **Status:** ⏳ OCZEKUJE NA ANALIZĘ
- **Cel:** Audyt file I/O operations, bulk operations, cross-platform support

### FAZA 3: MODELE I KOMPONENTY 🟡🟡

**Priorytet 9:** `models/file_pair.py`

- **Status:** ⏳ OCZEKUJE NA ANALIZĘ
- **Cel:** Audyt core domain model, path handling, thumbnail management

**Priorytet 10:** `logic/metadata_manager.py`

- **Status:** ⏳ OCZEKUJE NA ANALIZĘ
- **Cel:** Audyt metadata persistence, buffered writes, file locking

---

## 📊 PODSUMOWANIE STANU AUDYTU

**Ukończone analizy:** 3/18 (17%)  
**Aktualny etap:** Analiza krytycznych plików UI dla wyświetlania par plików ukończona
**Kolejne etapy:** 15 plików oczekuje na analizę  
**Szacowany czas:** 3-5 dni intensywnej pracy

**Krytyczne obszary wymagające szczególnej uwagi:**

- ✅ Thread safety w scanner_core.py (ThreadSafeProgressManager) - UKOŃCZONE
- ✅ UI architecture w file_tile_widget.py (component simplification) - UKOŃCZONE
- ✅ Memory management w thumbnail_cache.py (async loading, <200MB) - UKOŃCZONE
- Memory management w file_pairing.py (SimpleTrie size limits)
- Cache performance w scanner_cache.py (LRU+TTL optimization)
- Service coordination w main_window_controller.py

**Oczekiwane rezultaty audytu:**

- Zidentyfikowanie bottlenecków wydajnościowych
- Optymalizacja algorytmów biznesowych
- Eliminacja memory leaks
- Poprawa thread safety
- Uproszczenie over-engineered solutions

---

_Mapa wygenerowana automatycznie na podstawie analizy kodu źródłowego aplikacji CFAB_3DHUB_
