# 📋 MAPA KODU PROJEKTU CFAB_3DHUB

**Data utworzenia:** 2025-06-21  
**Status:** Wstępna analiza ukończona  
**Narzędzia użyte:** vulture, radon, pylint, struktura folderów

---

## 🎯 PODSUMOWANIE ANALIZY

**Całkowita liczba plików Python:** 110+ plików  
**Średnia złożoność cyklomatyczna:** A (2.72) - bardzo dobra  
**Główne problemy:** Dead code, nieużywane importy, over-engineering w architekturze

---

## ⚫⚫⚫⚫ PRIORYTET KRYTYCZNY (Immediate Action Required)

### 1. `src/main.py` ⚫⚫⚫⚫ ✅ [PRZEANALIZOWANO - 2025-06-21]
- **Funkcjonalność:** Punkt wejścia aplikacji, inicjalizacja Qt i głównego okna  
- **Problem:** Błędy importów PyQt6 (false positives), zbyt ogólne try-catch, brak lazy loading
- **Wpływ na wydajność:** ⚡ KRYTYCZNY - punkt startu aplikacji
- **Zależności:** src/ui/main_window/main_window.py, src/utils/*, src/factories/worker_factory.py
- **Refaktoryzacja:** Lepsze error handling, lazy loading worker factory, podział funkcji

### 2. `src/ui/main_window/main_window.py` ⚫⚫⚫⚫ ✅ [PRZEANALIZOWANO - 2025-06-21]
- **Funkcjonalność:** Główne okno aplikacji, centralne zarządzanie UI
- **Problem:** 5x powtarzające się importy QMessageBox, 9x import outside toplevel, over-engineering (20+ managerów)
- **Wpływ na wydajność:** ⚡ KRYTYCZNY - core UI, wpływa na UX i startup time
- **Zależności:** 20+ managerów, orchestrator, ManagerRegistry, MessageBox utilities  
- **Refaktoryzacja:** Konsolidacja importów, MessageBoxHelper utility, manager caching, lepsze error handling

### 3. `src/config/config_core.py` ⚫⚫⚫⚫  
- **Funkcjonalność:** Centralna konfiguracja aplikacji
- **Problem:** Złożoność cyklomatyczna B w __init__, potencjalne problemy z thread safety
- **Wpływ na wydajność:** ⚡ WYSOKI - używane przez całą aplikację
- **Zależności:** config_io.py, config_validator.py, wszystkie properties
- **Refaktoryzacja:** Podział __init__, thread safety, optymalizacja ładowania

---

## 🔴🔴🔴 PRIORYTET WYSOKI (High Priority)

### 4. `src/ui/widgets/file_tile_widget.py` 🔴🔴🔴
- **Funkcjonalność:** Widget dla pojedynczego pliku/folderu w galerii
- **Problem:** Dead code import 'with_resource_management', złożoność eventFilter
- **Wpływ na wydajność:** ⚡ WYSOKI - używany w każdym tile, wpływa na scrolling
- **Zależności:** tile_*_component.py, thumbnail_component.py
- **Refaktoryzacja:** Usunięcie dead code, optymalizacja event handling

### 5. `src/logic/scanner_core.py` 🔴🔴🔴
- **Funkcjonalność:** Główna logika skanowania folderów  
- **Problem:** Funkcja collect_files_streaming ma złożoność C, potencjalny bottleneck
- **Wpływ na wydajność:** ⚡ KRYTYCZNY - skanowanie tysięcy plików
- **Zależności:** scanner.py, scanner_cache.py, metadata_manager.py
- **Refaktoryzacja:** Optymalizacja algorytmu skanowania, lepsze streaming

### 6. `src/logic/filter_logic.py` 🔴🔴🔴
- **Funkcjonalność:** Filtrowanie wyników skanowania
- **Problem:** filter_file_pairs ma złożoność C, może spowalniać UI
- **Wpływ na wydajność:** ⚡ WYSOKI - filtrowanie w real-time
- **Zależności:** Używane przez gallerię, unpaired files
- **Refaktoryzacja:** Algorytmy filtrowania, caching wyników

### 7. `src/services/file_operations_service.py` 🔴🔴🔴
- **Funkcjonalność:** Operacje na plikach (kopiowanie, przenoszenie, usuwanie)
- **Problem:** bulk_move ma złożoność C, klasa ma złożoność B
- **Wpływ na wydajności:** ⚡ WYSOKI - operacje I/O, user experience
- **Zależności:** file_operations_controller.py, wszystkie UI operacje
- **Refaktoryzacja:** Optymalizacja bulk operations, lepsze error handling

---

## 🟡🟡 PRIORYTET ŚREDNI (Medium Priority)

### 8-15. KOMPONENTY TILE SYSTEM (8 plików)
- `src/ui/widgets/tile_cache_optimizer.py` 🟡🟡
- `src/ui/widgets/tile_resource_manager.py` 🟡🟡  
- `src/ui/widgets/tile_performance_monitor.py` 🟡🟡
- `src/ui/widgets/tile_event_bus.py` 🟡🟡
- `src/ui/widgets/tile_metadata_component.py` 🟡🟡
- `src/ui/widgets/tile_thumbnail_component.py` 🟡🟡
- `src/ui/widgets/tile_interaction_component.py` 🟡🟡
- `src/ui/widgets/tile_async_ui_manager.py` 🟡🟡

**Problem:** OVER-ENGINEERING - zbyt rozbudowana architektura dla prostych tile'ów  
**Wpływ na wydajność:** ⚡ ŚREDNI - każdy tile ma własne komponenty  
**Refaktoryzacja:** KONSOLIDACJA - połączenie w 2-3 klasy zamiast 8

### 16-20. METADATA SYSTEM (5 plików) 
- `src/logic/metadata/metadata_core.py` 🟡🟡
- `src/logic/metadata/metadata_operations.py` 🟡🟡  
- `src/logic/metadata/metadata_io.py` 🟡🟡
- `src/logic/metadata/metadata_validator.py` 🟡🟡
- `src/logic/metadata_manager.py` 🟡🟡

**Problem:** OVER-ENGINEERING - zbyt rozbudowany system metadanych  
**Wpływ na wydajność:** ⚡ ŚREDNI - I/O operations, caching  
**Refaktoryzacja:** KONSOLIDACJA - redukcja z 5 do 2 plików

---

## 🟢 PRIORYTET NISKI (Low Priority) 

### 21-30. DIRECTORY TREE SYSTEM (10 plików)
- `src/ui/directory_tree/*.py` (10 plików) 🟢

**Problem:** OVER-ENGINEERING - zbyt rozbudowana hierarchia dla directory tree  
**Wpływ na wydajność:** ⚡ NISKI - używane tylko w jednej karcie  
**Refaktoryzacja:** KONSOLIDACJA - redukcja liczby plików

### 31-40. MAIN WINDOW MANAGERS (15 plików)  
- `src/ui/main_window/*.py` (oprócz main_window.py) 🟢

**Problem:** OVER-ENGINEERING - zbyt dużo managerów  
**Wpływ na wydajność:** ⚡ NISKI - inicjalizacja, memory overhead  
**Refaktoryzacja:** KONSOLIDACJA - połączenie podobnych managerów

### 41-50. FILE OPERATIONS SYSTEM (7 plików)
- `src/ui/file_operations/*.py` 🟢

**Problem:** OVER-ENGINEERING - zbyt rozbudowany system operacji na plikach  
**Wpływ na wydajność:** ⚡ NISKI - używane sporadycznie  
**Refaktoryzacja:** KONSOLIDACJA - uproszczenie architektury

---

## 🗑️ DEAD CODE ZNALEZIONY (vulture)

### Nieużywane importy (90-100% confidence):
- `src/ui/directory_tree/delegates.py:7` - QPainter
- `src/ui/widgets/thumbnail_cache.py:8-9` - Q_ARG, QIcon
- `src/ui/widgets/tile_async_ui_manager.py:8` - concurrent  
- `src/ui/widgets/file_tile_widget.py:38` - with_resource_management (4 linie)

### Nieużywane zmienne (100% confidence):
- `src/ui/gallery_manager.py:598` - item_index
- `src/ui/main_window/worker_manager.py:338` - reset_tree
- Liczne nieużywane zmienne w UI components (w, h, checked)

---

## 📊 STATYSTYKI ZŁOŻONOŚCI (radon)

### Funkcje o złożoności C (Critical):
1. `src/config/config_io.py:61` - ConfigIO.load_config
2. `src/logic/scanner_core.py:325` - collect_files_streaming  
3. `src/logic/filter_logic.py:87` - filter_file_pairs
4. `src/controllers/statistics_controller.py:108` - _calculate_total_size
5. `src/ui/gallery_manager.py:295` - _update_visible_tiles

### Klasy o wysokiej złożoności (B+):
- Większość service i controller classes
- File operations workers  
- UI managers i components

---

## 🎯 PLAN KOLEJNOŚCI ANALIZY

### ETAP 1: CORE FIXES (Pliki ⚫⚫⚫⚫) 
1. `src/main.py` - Naprawa importów, error handling
2. `src/ui/main_window/main_window.py` - Konsolidacja importów  
3. `src/config/config_core.py` - Thread safety, optymalizacja

### ETAP 2: PERFORMANCE CRITICAL (Pliki 🔴🔴🔴)
4. `src/logic/scanner_core.py` - Optymalizacja skanowania
5. `src/logic/filter_logic.py` - Optymalizacja filtrowania  
6. `src/services/file_operations_service.py` - Bulk operations
7. `src/ui/widgets/file_tile_widget.py` - Dead code, events

### ETAP 3: ARCHITECTURE SIMPLIFICATION (Pliki 🟡🟡)
8-15. Tile system - Konsolidacja z 8 do 3 plików
16-20. Metadata system - Konsolidacja z 5 do 2 plików

### ETAP 4: DEAD CODE CLEANUP (Pliki 🟢)
21+. Usunięcie nieużywanych importów i zmiennych

---

## 🚀 SZACUNKI REFAKTORYZACJI

**Całkowity szacowany czas:** 4-5 dni intensywnej pracy  
**Krytyczne poprawki (Etap 1-2):** 2 dni  
**Konsolidacja architektury (Etap 3):** 2 dni  
**Cleanup (Etap 4):** 1 dzień  

**Oczekiwane korzyści:**
- ⚡ **Wydajność:** 20-30% szybszy start aplikacji  
- 🧹 **Clean Code:** Redukcja o ~30% linii kodu przez konsolidację
- 🛡️ **Stabilność:** Lepsza obsługa błędów, thread safety
- 🔧 **Maintainability:** Prostsze debugowanie i rozwój

---

## ⚠️ UWAGI BEZPIECZEŃSTWA REFAKTORYZACJI

1. **BACKUP OBLIGATORYJNY** - Każdy plik przed modyfikacją
2. **TESTY PRZED I PO** - Szczególnie dla core files  
3. **INCREMENTAL APPROACH** - Małe kroki, frequent testing
4. **NO BREAKING CHANGES** - 100% backward compatibility
5. **PERFORMANCE BASELINE** - Pomiary przed refaktoryzacją

---

**Status:** ✅ **MAPA GOTOWA DO REALIZACJI**  
**Następny krok:** Rozpoczęcie analizy szczegółowej od pliku `src/main.py`