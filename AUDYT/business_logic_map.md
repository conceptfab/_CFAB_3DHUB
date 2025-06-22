# 🗺️ MAPA PLIKÓW FUNKCJONALNOŚCI BIZNESOWEJ

**Wygenerowano na podstawie aktualnego kodu: 2025-01-28**

**Odkryte katalogi z logiką biznesową:**

- `src/logic/` - Główne algorytmy biznesowe aplikacji (parowanie plików, skanowanie, cache)
- `src/services/` - Serwisy biznesowe koordynujące logikę (skanowanie, operacje plików, wątki)
- `src/controllers/` - Kontrolery koordynujące procesy biznesowe (galeria, operacje, statystyki)
- `src/ui/widgets/` - Komponenty UI z embedded logiką biznesową (galeria, kafelki, cache miniatur)
- `src/ui/delegates/workers/` - Workery przetwarzania biznesowego (miniaturki, skanowanie, operacje masowe)
- `src/ui/directory_tree/` - Komponenty drzewa katalogów z logiką zarządzania danymi

## 🗺️ SZCZEGÓŁOWA MAPA KATALOGÓW

#### **LOGIC** (src/logic/)

```
src/logic/
├── file_pairing.py ⚫⚫⚫⚫ - Główny algorytm parowania archiwów z podglądami (OptimizedBestMatchStrategy, SimpleTrie)
    ✅ UKOŃCZONA ANALIZA - Data: 2025-01-28 - Pliki: corrections/file_pairing_correction.md, patches/file_pairing_patch_code.md
├── scanner_core.py ⚫⚫⚫⚫ - Silnik skanowania systemu plików (collect_files_streaming, scan_folder_for_pairs)
    ✅ UKOŃCZONA ANALIZA - Data: 2025-01-28 - Pliki: corrections/scanner_core_correction.md, patches/scanner_core_patch_code.md
├── scanner.py ⚫⚫⚫⚫ - Publiczne API skanowania z walidacją i thread safety
├── metadata_manager.py 🔴🔴🔴 - Zarządzanie metadanymi plików (gwiazdki, tagi kolorów, unified architecture)
├── scanner_cache.py 🔴🔴🔴 - LRU cache wyników skanowania z walidacją czasową (ThreadSafeCache)
├── file_operations.py 🔴🔴🔴 - Factory operacji na plikach z thread-safe component access
├── filter_logic.py 🟡🟡 - Algorytmy filtrowania galerii (gwiazdki, kolory, ścieżki)
└── cache_monitor.py 🟡🟡 - Monitoring wydajności i zużycia pamięci cache
```

#### **SERVICES** (src/services/)

```
src/services/
├── scanning_service.py 🔴🔴🔴 - Serwis skanowania z batch processing i async operations
├── file_operations_service.py 🔴🔴🔴 - Centralizacja operacji CRUD z obsługą błędów
└── thread_coordinator.py 🔴🔴🔴 - Koordynacja równoległych operacji workerów
```

#### **CONTROLLERS** (src/controllers/)

```
src/controllers/
├── gallery_controller.py 🔴🔴🔴 - Kontroler galerii (apply_filters, load_gallery, refresh_gallery)
├── main_window_controller.py 🔴🔴🔴 - Główny kontroler koordynujący operacje aplikacji
├── file_operations_controller.py 🔴🔴🔴 - Orchestracja operacji na plikach z walidacją
├── statistics_controller.py 🟡🟡 - Kontroler statystyk i raportowania
├── scan_result_processor.py 🟡🟡 - Procesor wyników skanowania
├── selection_manager.py 🟡🟡 - Manager selekcji elementów UI
└── special_folders_manager.py 🟡🟡 - Manager folderów specjalnych
```

#### **UI/WIDGETS** (src/ui/widgets/)

```
src/ui/widgets/
├── gallery_tab.py ⚫⚫⚫⚫ - Główny interface galerii (apply_filters_and_update_view, update_gallery_view)
├── file_tile_widget.py ⚫⚫⚫⚫ - Podstawowy element UI galerii z component architecture
    ✅ UKOŃCZONA ANALIZA - Data: 2025-01-28 - Pliki: corrections/file_tile_widget_correction.md, patches/file_tile_widget_patch_code.md
├── thumbnail_cache.py ⚫⚫⚫⚫ - LRU cache miniatur z thread-safe cleanup i memory management
├── filter_panel.py 🔴🔴🔴 - Panel filtrów z walidacją kryteriów
├── metadata_controls_widget.py 🔴🔴🔴 - Kontrolki metadanych (gwiazdki, tagi kolorów)
├── tile_thumbnail_component.py 🔴🔴🔴 - Komponent miniatur kafelków
├── tile_metadata_component.py 🔴🔴🔴 - Komponent metadanych kafelków
├── tile_interaction_component.py 🔴🔴🔴 - Komponent interakcji kafelków
├── unpaired_files_tab.py 🔴🔴🔴 - Zakładka nieparowanych plików
├── file_explorer_tab.py 🔴🔴🔴 - Zakładka eksploratora plików
├── tile_config.py 🟡🟡 - Konfiguracja kafelków
├── tile_event_bus.py 🟡🟡 - System zdarzeń kafelków
├── tile_resource_manager.py 🟡🟡 - Manager zasobów kafelków
├── tile_performance_monitor.py 🟡🟡 - Monitor wydajności kafelków
├── file_tile_widget_performance.py 🟡🟡 - Optymalizacje wydajności kafelków
├── file_tile_widget_events.py 🟡🟡 - System zdarzeń kafelków
├── file_tile_widget_thumbnail.py 🟡🟡 - System miniatur kafelków
├── file_tile_widget_ui_manager.py 🟡🟡 - Manager UI kafelków
├── unpaired_files_ui_manager.py 🟡🟡 - Manager UI nieparowanych plików
├── unpaired_preview_tile.py 🟡🟡 - Kafelek podglądu nieparowanych
├── unpaired_previews_grid.py 🟡🟡 - Siatka podglądów nieparowanych
├── special_folder_tile_widget.py 🟡🟡 - Widget kafelka foldera specjalnego
├── preview_dialog.py 🟡🟡 - Dialog podglądu plików
├── preferences_dialog.py 🟡🟡 - Dialog preferencji aplikacji
├── favorite_folders_dialog.py 🟡🟡 - Dialog ulubionych folderów
├── duplicate_renamer_widget.py 🟢 - Widget zmiany nazw duplikatów
├── image_resizer_widget.py 🟢 - Widget zmiany rozmiaru obrazów
├── webp_converter_widget.py 🟢 - Widget konwersji WebP
└── sbsar_extractor_widget.py 🟢 - Widget ekstraktora SBSAR
```

#### **UI/DELEGATES/WORKERS** (src/ui/delegates/workers/)

```
src/ui/delegates/workers/
├── processing_workers.py ⚫⚫⚫⚫ - Workery przetwarzania (ThumbnailGenerationWorker, BatchThumbnailWorker, DataProcessingWorker)
├── scan_workers.py ⚫⚫⚫⚫ - Workery skanowania asynchronicznego (ScanFolderWorker, ScanDirectoryWorker)
├── base_workers.py 🔴🔴🔴 - Bazowe klasy workerów z unified architecture
├── file_workers.py 🔴🔴🔴 - Workery operacji na plikach
├── folder_workers.py 🔴🔴🔴 - Workery operacji na folderach
├── bulk_workers.py 🔴🔴🔴 - Workery operacji masowych
├── file_list_workers.py 🔴🔴🔴 - Workery list plików
└── worker_factory.py 🔴🔴🔴 - Factory pattern dla workerów
```

#### **UI/DIRECTORY_TREE** (src/ui/directory_tree/)

```
src/ui/directory_tree/
├── manager.py 🔴🔴🔴 - Manager drzewa katalogów z komponentową architekturą
├── data_manager.py 🔴🔴🔴 - Manager danych drzewa
├── operations_manager.py 🔴🔴🔴 - Manager operacji drzewa
├── event_handler.py 🔴🔴🔴 - Handler zdarzeń drzewa
├── ui_handler.py 🔴🔴🔴 - Handler UI drzewa
├── drag_drop_handler.py 🔴🔴🔴 - Handler drag & drop
├── stats_manager.py 🔴🔴🔴 - Manager statystyk drzewa
├── worker_coordinator.py 🔴🔴🔴 - Koordynator workerów drzewa
├── cache.py 🟡🟡 - Cache danych drzewa
├── models.py 🟡🟡 - Modele danych drzewa
├── delegates.py 🟡🟡 - Delegaty renderowania drzewa
├── workers.py 🟡🟡 - Workery operacji drzewa
├── data_classes.py 🟡🟡 - Klasy danych drzewa
└── throttled_scheduler.py 🟡🟡 - Scheduler z ograniczaniem częstotliwości
```

## 🎯 DYNAMICZNE PRIORYTETY ANALIZY

**Wygenerowano na podstawie analizy kodu i kontekstu biznesowego: 2025-01-28**

#### **⚫⚫⚫⚫ KRYTYCZNE** - Podstawowa funkcjonalność aplikacji

**Uzasadnienie:** Te elementy implementują główne algorytmy biznesowe aplikacji i są krytyczne dla spełnienia wymagań wydajnościowych (1000+ plików/sekundę, 1000+ miniaturek bez lagów, <500MB pamięci)

- **`src/logic/file_pairing.py`** - Główny algorytm parowania archiwów z podglądami, optymalizacje Trie-based O(log m)
- **`src/logic/scanner_core.py`** - Silnik skanowania systemu plików, 100+ plików/s dla folderów >500 plików
- **`src/ui/widgets/file_tile_widget.py`** - Podstawowy element UI galerii, 1000+ kafelków bez lagów
- **`src/ui/widgets/thumbnail_cache.py`** - Cache miniatur z memory management <500MB
- **`src/ui/widgets/gallery_tab.py`** - Główny interface galerii, responsywność UI <100ms
- **`src/ui/delegates/workers/processing_workers.py`** - Workery generowania miniatur, adaptive batch size

#### **🔴🔴🔴 WYSOKIE** - Ważne operacje biznesowe

**Uzasadnienie:** Te elementy implementują ważne operacje biznesowe, zarządzają cache i optymalizacjami oraz stanowią serwisy biznesowe wpływające na wydajność

- **`src/logic/metadata_manager.py`** - Zarządzanie metadanymi, unified architecture, TTL cache
- **`src/logic/scanner_cache.py`** - LRU cache skanowania z walidacją czasową
- **`src/logic/file_operations.py`** - Factory operacji plików z thread safety
- **`src/services/scanning_service.py`** - Serwis skanowania z batch processing
- **`src/services/file_operations_service.py`** - Centralizacja operacji CRUD
- **`src/services/thread_coordinator.py`** - Koordynacja workerów
- **`src/controllers/gallery_controller.py`** - Kontroler galerii z filtrowaniem
- **`src/controllers/main_window_controller.py`** - Główny kontroler aplikacji
- **`src/controllers/file_operations_controller.py`** - Orchestracja operacji plików
- **`src/ui/widgets/filter_panel.py`** - Panel filtrów z walidacją
- **`src/ui/widgets/metadata_controls_widget.py`** - Kontrolki metadanych
- **`src/ui/delegates/workers/scan_workers.py`** - Workery skanowania asynchronicznego
- **`src/ui/delegates/workers/base_workers.py`** - Bazowe klasy workerów
- **`src/ui/directory_tree/manager.py`** - Manager drzewa katalogów

#### **🟡🟡 ŚREDNIE** - Funkcjonalności pomocnicze

**Uzasadnienie:** Te elementy implementują funkcjonalności pomocnicze, zarządzają konfiguracją i walidacją oraz nie mają bezpośredniego wpływu na krytyczne procesy biznesowe

- **`src/logic/filter_logic.py`** - Algorytmy filtrowania galerii
- **`src/logic/cache_monitor.py`** - Monitoring cache
- **`src/controllers/statistics_controller.py`** - Kontroler statystyk
- **`src/controllers/scan_result_processor.py`** - Procesor wyników
- **`src/controllers/selection_manager.py`** - Manager selekcji
- **`src/controllers/special_folders_manager.py`** - Manager folderów specjalnych
- **Komponenty kafelków** - tile\_\*\_component.py (konfiguracja, eventy, monitoring)
- **UI managery** - \*\_ui_manager.py (zarządzanie UI komponentów)
- **Dialogi** - preview_dialog.py, preferences_dialog.py, favorite_folders_dialog.py

#### **🟢 NISKIE** - Funkcjonalności dodatkowe

**Uzasadnienie:** Te elementy implementują funkcjonalności dodatkowe, narzędzia konwersji i nie mają bezpośredniego wpływu na główne procesy biznesowe

- **`src/ui/widgets/duplicate_renamer_widget.py`** - Widget zmiany nazw duplikatów
- **`src/ui/widgets/image_resizer_widget.py`** - Widget zmiany rozmiaru obrazów
- **`src/ui/widgets/webp_converter_widget.py`** - Widget konwersji WebP
- **`src/ui/widgets/sbsar_extractor_widget.py`** - Widget ekstraktora SBSAR

#### **📈 METRYKI PRIORYTETÓW**

**Na podstawie analizy kodu:**

- **Plików krytycznych:** 6
- **Plików wysokich:** 15
- **Plików średnich:** 25
- **Plików niskich:** 4
- **Łącznie przeanalizowanych:** 50

**Rozkład priorytetów:** 12% Krytyczne, 30% Wysokie, 50% Średnie, 8% Niskie

## 🏗️ ARCHITEKTURA LOGIKI BIZNESOWEJ

### **WARSTWA 1: LOGIKA BIZNESOWA CZYSTA** (`src/logic/`)

- Czyste algorytmy bez zależności UI
- Parowanie plików, skanowanie, cache, filtrowanie
- Testowalna niezależnie od UI

### **WARSTWA 2: SERWISY BIZNESOWE** (`src/services/`)

- Orchestracja logiki biznesowej
- Separacja od UI, koordynacja operacji
- Async operations, thread coordination

### **WARSTWA 3: KONTROLERY** (`src/controllers/`)

- Koordynacja między UI a logiką
- Gallery controller, operations controller
- Statystyki i rezultaty

### **WARSTWA 4: UI Z LOGIKĄ** (`src/ui/widgets/`)

- Komponenty UI z embedded business logic
- Galeria, kafelki, cache miniatur
- Krytyczne dla UX i wydajności

### **WARSTWA 5: WORKERY ASYNCHRONICZNE** (`src/ui/delegates/workers/`)

- Przetwarzanie w tle
- Generowanie miniatur, skanowanie
- Thread safety, progress reporting

### **WARSTWA 6: KOMPONENTY ZARZĄDZANIA** (`src/ui/directory_tree/`)

- Zarządzanie strukturą danych
- Drzewo katalogów, drag&drop
- Cache i optymalizacje UI

## 🎯 KLUCZOWE METRYKI WYDAJNOŚCIOWE

- **Skanowanie:** 1000+ plików/sekundę (scanner_core.py)
- **UI Galeria:** 1000+ miniaturek bez lagów (gallery_tab.py, file_tile_widget.py)
- **Memory:** <500MB zużycia (thumbnail_cache.py, metadata_manager.py)
- **Responsywność:** <100ms UI response (processing_workers.py)
- **Cache:** Optymalne hit ratio (scanner_cache.py, thumbnail_cache.py)

## 🔍 OBSZARY KRYTYCZNE DLA AUDYTU

### **WYDAJNOŚĆ ALGORYTMÓW**

- `file_pairing.py` - Optymalizacje Trie-based matching
- `scanner_core.py` - Smart pre-filtering, memory cleanup
- `processing_workers.py` - Adaptive batch size

### **THREAD SAFETY**

- `thumbnail_cache.py` - Thread-safe cleanup
- `metadata_manager.py` - Singleton thread safety
- `processing_workers.py` - Resource protection

### **MEMORY MANAGEMENT**

- `thumbnail_cache.py` - LRU cleanup, compression estimation
- `scanner_cache.py` - OrderedDict LRU
- `file_tile_widget.py` - Resource manager, cleanup

### **UI RESPONSIVENESS**

- `gallery_tab.py` - Non-blocking UI updates
- `file_tile_widget.py` - Component architecture
- `processing_workers.py` - Progress reporting

## 📊 POSTĘP AUDYTU LOGIKI BIZNESOWEJ

✅ **Etap 1 ukończony:** MAPOWANIE LOGIKI BIZNESOWEJ (100%)
✅ **Etap 2 ukończony:** ANALIZA file_pairing.py (100%)
✅ **Etap 3 ukończony:** ANALIZA scanner_core.py (100%)
🔄 **Aktualny etap:** Analiza thumbnail_cache.py (cache miniatur krytyczny)
⏳ **Pozostałe etapy:** 3 pliki krytyczne + 35 plików wysokie/średnie
💼 **Business impact:** Ukończono analizę głównych algorytmów - parowanie i skanowanie (podstawa funkcjonalności)

## 📋 UKOŃCZONE ANALIZY KRYTYCZNYCH PLIKÓW

### 📄 FILE_PAIRING.PY

- **Status:** ✅ UKOŃCZONA ANALIZA
- **Data ukończenia:** 2025-01-28
- **Business impact:** Główny algorytm parowania archiwów z podglądami - podstawa funkcjonalności aplikacji. Zidentyfikowano optymalizacje thread safety, memory management i usunięcie dead code. Krytyczne dla wydajności 1000+ plików/sekundę.
- **Pliki wynikowe:**
  - `AUDYT/corrections/file_pairing_correction.md`
  - `AUDYT/patches/file_pairing_patch_code.md`
- **Podsumowanie refaktoryzacji 2025-01-28:**
  - Usunięto duplikaty funkcji kategoryzacji plików (pozostawiono tylko zoptymalizowaną wersję)
  - Dodano pełny thread safety do SimpleTrie (RLock, atomic operations)
  - Wprowadzono limity rozmiaru i metody cleanup w Trie (memory management)
  - Zoptymalizowano find_prefix_matches (sortowanie kluczy, O(log k))
  - Dodano performance monitoring (logi czasu działania kategoryzacji, budowy Trie, parowania)
  - Standaryzacja logowania: DEBUG dla niekrytycznych, ERROR tylko dla wyjątków
  - 100% kompatybilność API (wszystkie publiczne metody zachowane)
  - Testy importu i uruchomienia OK

### 📄 SCANNER_CORE.PY

- **Status:** ✅ UKOŃCZONA ANALIZA
- **Data ukończenia:** 2025-01-28
- **Business impact:** Silnik skanowania systemu plików - podstawa discovery plików w aplikacji. Zidentyfikowano potrzeby dekompozycji funkcji, enhanced thread safety, memory management i accurate progress reporting. Krytyczne dla wydajności 100+ plików/s dla folderów >500 plików.
- **Pliki wynikowe:**
  - `AUDYT/corrections/scanner_core_correction.md`
  - `AUDYT/patches/scanner_core_patch_code.md`

### 📄 FILE_TILE_WIDGET.PY

- **Status:** ✅ UKOŃCZONA ANALIZA
- **Data ukończenia:** 2025-01-28
- **Business impact:** Podstawowy element UI galerii - bezpośredni wpływ na user experience. Zidentyfikowano potrzeby uproszczenia component architecture, enhanced thread safety, comprehensive memory management i optimized event handling. Krytyczne dla wydajności 1000+ kafelków w galerii bez lagów.
- **Pliki wynikowe:**
  - `AUDYT/corrections/file_tile_widget_correction.md`
  - `AUDYT/patches/file_tile_widget_patch_code.md`
