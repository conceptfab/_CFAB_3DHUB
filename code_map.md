# 📊 MAPA KODU PROJEKTU CFAB_3DHUB

## 🎯 WYNIKI ANALIZY STATYCZNEJ

### 📈 STATYSTYKI OGÓLNE
- **Liczba plików Python**: ~150+ plików
- **Główne problemy z vulture**: 200+ nieużywanych funkcji/zmiennych (60% pewności)
- **Problemy z pylint**: Nieużywane importy i zmienne 
- **Problemy z flake8**: 1000+ błędów formatowania i stylu
- **Złożoność cyklomatyczna (radon)**: Wiele funkcji klasy B i C (średnia/wysoka złożoność)

### ⚠️ KLUCZOWE PROBLEMY WYKRYTE
1. **MASOWE DEAD CODE** - setki nieużywanych metod i funkcji
2. **IMPORT HELL** - nieużywane importy w każdym pliku
3. **FORMATOWANIE** - brak spójnego stylu kodu
4. **OVER-ENGINEERING** - nadmiernie skomplikowane wzorce (szczególnie w UI)

---

## 🗂️ MAPA PROJEKTU Z PRIORYTETAMI

### ⚫⚫⚫⚫ KRYTYCZNY PRIORYTET - NATYCHMIASTOWA AKCJA

#### **🏗️ ARCHITEKTURA CORE**
- **`src/main.py`** - Punkt wejścia aplikacji, nieużywana zmienna `window`
- **`run_app.py`** - Główny moduł uruchamiający, wysoka złożoność (B)
- **`src/app_config.py`** - Konfiguracja aplikacji, nieużywane zmienne MIN/MAX_THUMBNAIL_SIZE

#### **💾 ZARZĄDZANIE DANYMI - BOTTLENECK**  
- **`src/logic/scanner_core.py`** - Skanowanie plików, funkcja `collect_files_streaming` (złożoność C)
- **`src/logic/metadata/metadata_core.py`** - Rdzeń metadanych, `_flush_now` (złożoność C)
- **`src/logic/file_operations.py`** - Operacje na plikach, metoda `execute` (złożoność B)

#### **🎨 SYSTEM UI - OVER-ENGINEERED**
- **`src/ui/widgets/file_tile_widget.py`** - Główny widget, masywny plik
- **`src/ui/gallery_manager.py`** - Manager galerii, `_update_visible_tiles` (złożoność C)

### 🔴🔴🔴 WYSOKI PRIORYTET - TYDZIEŃ 1

#### **🔧 KONTROLERY - NIEUŻYWANE METODY**
- **`src/controllers/statistics_controller.py`** - 60% nieużywanych metod, cała klasa StatisticsController
- **`src/controllers/gallery_controller.py`** - Większość metod nieużywana
- **`src/controllers/selection_manager.py`** - Nieużywane metody

#### **🔍 LOGIC LAYER - KOMPLEKSOWOŚĆ**
- **`src/logic/filter_logic.py`** - `filter_file_pairs` (złożoność C)
- **`src/logic/metadata/metadata_operations.py`** - `apply_metadata_to_file_pairs` (złożoność C)
- **`src/logic/metadata/metadata_validator.py`** - `validate_metadata_structure` (złożoność C)

#### **🎭 UI COMPONENTS - TILE HELL**
- **`src/ui/widgets/tile_performance_monitor.py`** - Masywne over-engineering, dziesiątki nieużywanych metod
- **`src/ui/widgets/tile_resource_manager.py`** - Skomplikowany system zarządzania zasobami
- **`src/ui/widgets/tile_cache_optimizer.py`** - Złożony system cache'owania
- **`src/ui/widgets/tile_async_ui_manager.py`** - Asynchroniczny manager UI

### 🟡🟡 ŚREDNI PRIORYTET - TYDZIEŃ 2

#### **⚙️ KONFIGURACJA - CLEAN UP**
- **`src/config/`** - Cały folder, dziesiątki nieużywanych metod w każdym pliku
- **`src/config/properties/`** - System właściwości, masywnie over-engineered

#### **👷 WORKER SYSTEM - DUPLIKACJA**
- **`src/ui/delegates/workers/`** - Cały folder, złożone workery (B/C)
- **`src/factories/worker_factory.py`** - Factory pattern, średnia złożoność

#### **🔧 SERVICES - ANALIZA**
- **`src/services/file_operations_service.py`** - `bulk_move` (złożoność C)
- **`src/services/scanning_service.py`** - Serwis skanowania

### 🟢 NISKI PRIORYTET - TYDZIEŃ 3+

#### **🧪 TESTY - CLEANUP**
- **`tests/`** - Całość, setki nieużywanych importów i zmiennych
- Większość testów ma nieużywane importy i zmienne

#### **🛠️ NARZĘDZIA**
- **`__tools/`** - Narzędzia pomocnicze, nieużywane importy w każdym pliku
  
#### **🎨 UI HELPERS**
- **`src/utils/`** - Narzędzia pomocnicze, niektóre nieużywane funkcje
- **`src/ui/widgets/` (pozostałe)** - Pozostałe widgety

---

## 📋 PLAN KOLEJNOŚCI ANALIZY

### **ETAP 1: CORE CLEANUP (2-3 dni)**
1. `src/main.py` + `run_app.py` - Punkt wejścia
2. `src/app_config.py` - Konfiguracja główna
3. `src/logic/scanner_core.py` - Bottleneck skanowania
4. `src/logic/file_operations.py` - Operacje na plikach

### **ETAP 2: METADATA HELL (3-4 dni)**
1. `src/logic/metadata/` - Cały folder metadata
2. `src/controllers/statistics_controller.py` - Masywny cleanup
3. `src/logic/filter_logic.py` - Filtrowanie

### **ETAP 3: UI OVER-ENGINEERING (5-7 dni)**
1. `src/ui/widgets/file_tile_widget.py` - Główny widget
2. `src/ui/widgets/tile_*` - Cały system tile'ów
3. `src/ui/gallery_manager.py` - Manager galerii

### **ETAP 4: CONTROLLERS CLEANUP (2-3 dni)**
1. `src/controllers/` - Wszystkie kontrolery
2. `src/services/` - Serwisy

### **ETAP 5: CONFIG & TESTS (3-4 dni)**
1. `src/config/` - System konfiguracji
2. `tests/` - Testy
3. `__tools/` - Narzędzia

---

## 🎯 GRUPOWANIE PLIKÓW

### **GRUPA A: CORE SYSTEM (KRYTYCZNE)**
- Pliki podstawowe: main.py, run_app.py, app_config.py
- Logika główna: scanner_core.py, file_operations.py
- **Szacowany czas**: 1 tydzień

### **GRUPA B: METADATA OVER-ENGINEERING** 
- Cały folder `src/logic/metadata/`
- Controllers z masywnym dead code
- **Szacowany czas**: 1-1.5 tygodnia

### **GRUPA C: UI TILE HELL**
- System tile'ów - masywne over-engineering
- Gallery manager
- **Szacowany czas**: 2 tygodnie

### **GRUPA D: SUPPORTING SYSTEMS**
- Config, utils, tests, tools
- **Szacowany czas**: 1 tydzień

---

## 🔍 SZACOWANY ZAKRES ZMIAN

### **USUNIĘCIA (DEAD CODE)**
- **~200+ nieużywanych metod/funkcji** (vulture 60% pewności)
- **~100+ nieużywanych zmiennych**
- **~50+ nieużywanych klas/interfejsów**

### **REFAKTORYZACJA**
- **~30 funkcji o wysokiej złożoności** (B/C w radon)
- **Uproszenie systemu tile'ów** - redukcja o ~50%
- **Konsolidacja metadata system** - redukcja o ~40%

### **FORMATOWANIE**
- **1000+ błędów flake8** do naprawienia
- **Standardyzacja stylu kodu**

### **PRZEWIDYWANE KORZYŚCI**
- **Redukcja LOC o ~30-40%**
- **Poprawa wydajności o ~20-30%**
- **Zwiększenie maintainability o ~50%**

---

## 🎯 NASTĘPNE KROKI

**CZEKAM NA POTWIERDZENIE ROZPOCZĘCIA ETAPU 2**

Pierwszym plikiem do szczegółowej analizy będzie: **`src/main.py`**

---

**📊 POSTĘP AUDYTU:**
```
✅ Ukończone etapy: 1/5 (20%)
🔄 Aktualny etap: ETAP 2 - Szczegółowa analiza
⏳ Następny plik: src/main.py
```