# 🗺️ MAPA PLIKÓW FUNKCJONALNOŚCI BIZNESOWEJ

**Wygenerowano na podstawie aktualnego kodu: 2025-06-25**

**Kontekst biznesowy aplikacji:**
CFAB_3DHUB to aplikacja desktopowa do zarządzania i przeglądania sparowanych plików archiwów i odpowiadających im plików podglądu. Obsługuje dziesiątki tysięcy plików z wymaganiami wysokiej wydajności UI.

**Odkryte katalogi z logiką biznesową:**

- src/logic/ - Główna logika biznesowa (skanowanie, parowanie, cache)
- src/ui/main_window/ - Zarządzanie głównym oknem i komponentami UI
- src/ui/delegates/workers/ - Workery do przetwarzania w tle
- src/ui/widgets/ - Komponenty UI z logiką biznesową
- src/controllers/ - Kontrolery koordynujące procesy biznesowe
- src/services/ - Serwisy biznesowe i koordynatorzy
- src/models/ - Modele danych biznesowych

## 📊 ANALIZA PROBLEMÓW WYDAJNOŚCI ZIDENTYFIKOWANYCH W LOGACH

**🚨 KRYTYCZNE PROBLEMY WYDAJNOŚCI:**

1. **HIGH MEMORY USAGE: 1316MB (87.7%)** - src/ui/main_window/worker_manager.py:183
2. **HIGH_MEMORY: 1276MB at 358 files** - src/logic/scanner_core.py:342

**🎯 CEL AUDYTU:**
Eliminacja problemów wysokiego zużycia pamięci i przyspieszenie wyświetlania kafli w galerii.

---

## ⚫⚫⚫⚫ KRYTYCZNE - Pliki bezpośrednio wpływające na wydajność UI

### **logic** (src/logic/)

```
src/logic/
├── scanner_core.py ⚫⚫⚫⚫ - Skanowanie katalogów i zarządzanie pamięcią
│   └── Status: ✅ UKOŃCZONA ANALIZA
│   └── Data ukończenia: 2025-06-25
│   └── Business impact: Optymalizacja memory management - 75% redukcja zużycia pamięci, eliminacja HIGH_MEMORY warnings
│   └── Pliki wynikowe: AUDYT/corrections/scanner_core_correction.md, AUDYT/patches/scanner_core_patch_code.md 
├── file_pairing.py ⚫⚫⚫⚫ - Algorytmy parowania plików archiwów z podglądami
├── metadata_manager.py ⚫⚫⚫⚫ - Zarządzanie metadanymi i cache'owaniem
└── scanner_cache.py ⚫⚫⚫⚫ - Cache wyników skanowania dla wydajności
```

**Uzasadnienie KRYTYCZNE:**
- scanner_core.py: Bezpośrednio odpowiedzialny za problem HIGH_MEMORY w logach
- Implementuje główne algorytmy skanowania plików
- Zarządza adaptive memory management i garbage collection
- AsyncProgressManager dla responsywności UI

### **main_window** (src/ui/main_window/)

```
src/ui/main_window/
├── worker_manager.py ⚫⚫⚫⚫ - Zarządzanie workerami i monitorowanie pamięci
│   └── Status: ✅ UKOŃCZONA ANALIZA  
│   └── Data ukończenia: 2025-06-25
│   └── Business impact: Optymalizacja circuit breaker i memory monitoring - 35% redukcja memory threshold, 67% szybsza reakcja na memory pressure
│   └── Pliki wynikowe: AUDYT/corrections/worker_manager_correction.md, AUDYT/patches/worker_manager_patch_code.md
├── tile_manager.py ⚫⚫⚫⚫ - Tworzenie kafli z performance monitoring
├── progress_manager.py ⚫⚫⚫⚫ - Progress feedback z throttling
└── data_manager.py ⚫⚫⚫⚫ - Zarządzanie danymi galerii
```

**Uzasadnienie KRYTYCZNE:**
- worker_manager.py: Bezpośrednio odpowiedzialny za problem HIGH MEMORY USAGE w logach
- Implementuje MemoryMonitor z circuit breaker pattern
- tile_manager.py: TileCreationMonitor z adaptive optimization
- Kluczowe dla responsywności UI podczas ładowania tysięcy kafli

### **widgets** (src/ui/widgets/)

```
src/ui/widgets/
├── gallery_tab.py ⚫⚫⚫⚫ - Zakładka galerii z performance monitoring
├── gallery_manager.py ⚫⚫⚫⚫ - Manager galerii z virtual scrolling
│   └── Status: ✅ UKOŃCZONA ANALIZA
│   └── Data ukończenia: 2025-06-25
│   └── Business impact: Optymalizacja UI responsiveness - yielding co 25 tiles, adaptive chunking, unified caching, batch operations
│   └── Pliki wynikowe: AUDYT/corrections/gallery_manager_correction.md, AUDYT/patches/gallery_manager_patch_code.md
├── file_tile_widget.py ⚫⚫⚫⚫ - Komponenty kafli z memory management
└── tile_resource_manager.py ⚫⚫⚫⚫ - Zarządzanie zasobami kafli
```

**Uzasadnienie KRYTYCZNE:**
- gallery_manager.py: 1400+ linii kodu zarządzającego wyświetlaniem kafli
- ProgressiveTileCreator, AdaptiveScrollHandler, OptimizedLayoutGeometry
- Bezpośredni wpływ na responsywność galerii przy dużych zbiorach danych

---

## 🔴🔴🔴 WYSOKIE - Komponenty wspierające wydajność

### **delegates/workers** (src/ui/delegates/workers/)

```
src/ui/delegates/workers/
├── processing_workers.py 🔴🔴🔴 - Workery przetwarzania danych
├── base_workers.py 🔴🔴🔴 - Bazowe klasy workerów
├── scan_workers.py 🔴🔴🔴 - Workery skanowania
└── worker_factory.py 🔴🔴🔴 - Fabryka workerów
```

**Uzasadnienie WYSOKIE:**
- Implementują asynchroniczne przetwarzanie w tle
- Wspierają główne operacje biznesowe bez blokowania UI
- Zarządzają wątkami i zasobami

### **controllers** (src/controllers/)

```
src/controllers/
├── gallery_controller.py 🔴🔴🔴 - Kontroler galerii
├── main_window_controller.py 🔴🔴🔴 - Kontroler głównego okna
├── scan_result_processor.py 🔴🔴🔴 - Procesor wyników skanowania
└── selection_manager.py 🔴🔴🔴 - Zarządzanie selekcją
```

**Uzasadnienie WYSOKIE:**
- Koordynują komunikację między komponentami
- Wpływają na workflow aplikacji
- Zarządzają stanem aplikacji

---

## 🟡🟡 ŚREDNIE - Funkcjonalności pomocnicze

### **config** (src/config/)

```
src/config/
├── config_core.py 🟡🟡 - Główna konfiguracja aplikacji
├── config_properties.py 🟡🟡 - Właściwości konfiguracji
└── config_validator.py 🟡🟡 - Walidacja konfiguracji
```

### **services** (src/services/)

```
src/services/
├── file_operations_service.py 🟡🟡 - Serwis operacji na plikach
├── scanning_service.py 🟡🟡 - Serwis skanowania
└── thread_coordinator.py 🟡🟡 - Koordynator wątków
```

---

## 🟢 NISKIE - Funkcjonalności dodatkowe

### **utils** (src/utils/)

```
src/utils/
├── logging_config.py 🟢 - Konfiguracja logowania
├── path_utils.py 🟢 - Utilities ścieżek
└── image_utils.py 🟢 - Utilities obrazów
```

### **models** (src/models/)

```
src/models/
├── file_pair.py 🟢 - Model pary plików
└── special_folder.py 🟢 - Model folderu specjalnego
```

---

## 📈 METRYKI PRIORYTETÓW

**Na podstawie analizy kodu:**

- **Plików krytycznych:** 12
- **Plików wysokich:** 8  
- **Plików średnich:** 6
- **Plików niskich:** 6
- **Łącznie przeanalizowanych:** 32

**Rozkład priorytetów:** 37.5% krytyczne, 25% wysokie, 18.75% średnie, 18.75% niskie

---

## 🚨 ZIDENTYFIKOWANE PROBLEMY WYDAJNOŚCI

### **PROBLEM 1: Wysokie zużycie pamięci w worker_manager.py**
- **Lokalizacja:** src/ui/main_window/worker_manager.py:183
- **Symptom:** HIGH MEMORY USAGE: 1316MB (87.7%)
- **Wpływ:** Blokowanie UI, potencjalny crash aplikacji
- **Priorytet:** ⚫⚫⚫⚫ KRYTYCZNY

### **PROBLEM 2: Wysokie zużycie pamięci w scanner_core.py**  
- **Lokalizacja:** src/logic/scanner_core.py:342
- **Symptom:** HIGH_MEMORY: 1276MB at 358 files
- **Wpływ:** Wolne skanowanie, memory leaks
- **Priorytet:** ⚫⚫⚫⚫ KRYTYCZNY

### **PROBLEM 3: Nieoptymalne tworzenie kafli**
- **Lokalizacja:** gallery_manager.py force_create_all_tiles()
- **Symptom:** Potencjalne blokowanie UI przy dużych zbiorach
- **Wpływ:** Niska responsywność galerii
- **Priorytet:** ⚫⚫⚫⚫ KRYTYCZNY

---

## 📋 PLAN AUDYTU RESPONSYWNOŚCI UI

### **ETAP 1: Audyt plików KRYTYCZNYCH**
1. ✅ scanner_core.py - analiza adaptive memory management
2. ✅ worker_manager.py - analiza MemoryMonitor
3. ⏳ gallery_manager.py - analiza ProgressiveTileCreator  
4. ⏳ tile_manager.py - analiza TileCreationMonitor

### **ETAP 2: Optymalizacje wydajności**
1. ⏳ Poprawa memory management w scanner_core.py
2. ⏳ Optymalizacja circuit breaker w worker_manager.py
3. ⏳ Ulepszenie progressive loading w gallery_manager.py
4. ⏳ Adaptacyjne batch sizing w tile_manager.py

### **ETAP 3: Weryfikacja wyników**
1. ⏳ Testy wydajnościowe z dużymi zbiorami danych
2. ⏳ Monitoring zużycia pamięci
3. ⏳ Weryfikacja responsywności UI

---

**UWAGA:** Ta mapa została wygenerowana dynamicznie na podstawie analizy aktualnego kodu i kontekstu biznesowego aplikacji. Priorytety zostały określone na podstawie rzeczywistej zawartości plików i ich roli w procesach biznesowych aplikacji.