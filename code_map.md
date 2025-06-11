# MAPA PROJEKTU CFAB_3DHUB

## ETAP 1: WSTĘPNA ANALIZA I MAPOWANIE PROJEKTU

**Data utworzenia:** Zgodnie z audytem w \_audyt.md  
**Status:** ETAP 1 ZAKOŃCZONY

---

## 📊 STRUKTURA PROJEKTU

### CFAB_3DHUB/

├── **run_app.py** 🔴 **WYSOKI PRIORYTET** - Główny plik uruchomieniowy, problemy z konfiguracją sys.path i obsługą błędów
├── **src/**
│ ├── **main.py** 🔴 **WYSOKI PRIORYTET** - Punkt wejścia aplikacji, nadmiarowa obsługa wyjątków, błędna logika uruchamiania
│ ├── **app_config.py** 🟡 **ŚREDNI PRIORYTET** - System konfiguracji, do optymalizacji walidacji i cache
│ ├── ****init**.py** 🟢 **NISKI PRIORYTET** - Podstawowy plik inicjalizacyjny
│ ├── **controllers/**
│ │ └── **main_window_controller.py** 🟡 **ŚREDNI PRIORYTET** - Kontroler głównego okna, wymagana implementacja wzorca MVC
│ ├── **logic/**
│ │ ├── **scanner.py** 🔴 **WYSOKI PRIORYTET** - Główny moduł skanowania, bardzo duży (916 linii), problemy z wydajnością cache
│ │ ├── **metadata_manager.py** 🟡 **ŚREDNI PRIORYTET** - Zarządzanie metadanymi, wymagana optymalizacja I/O
│ │ ├── **file_operations.py** 🟡 **ŚREDNI PRIORYTET** - Operacje na plikach, wymagana refaktoryzacja
│ │ ├── **filter_logic.py** 🟢 **NISKI PRIORYTET** - Logika filtrowania, analiza nieużywanego kodu
│ │ └── ****init**.py** 🟢 **NISKI PRIORYTET** - Plik inicjalizacyjny modułu
│ ├── **models/**
│ │ ├── **file_pair.py** 🟡 **ŚREDNI PRIORYTET** - Model danych par plików, optymalizacja struktury
│ │ └── ****init**.py** 🟢 **NISKI PRIORYTET** - Plik inicjalizacyjny modułu
│ ├── **services/**
│ │ ├── **scanning_service.py** 🟡 **ŚREDNI PRIORYTET** - Usługa skanowania, duplikacja z logic/scanner
│ │ ├── **file_operations_service.py** 🟡 **ŚREDNI PRIORYTET** - Usługa operacji na plikach, duplikacja funkcjonalności
│ │ ├── **thread_coordinator.py** 🟡 **ŚREDNI PRIORYTET** - Koordynacja wątków, wymagana optymalizacja
│ │ └── ****init**.py** 🟢 **NISKI PRIORYTET** - Plik inicjalizacyjny modułu
│ ├── **ui/**
│ │ ├── **main_window.py** 🔴 **WYSOKI PRIORYTET** - Główne okno UI (2010 linii), nadmiernie skomplikowane, wymagana refaktoryzacja
│ │ ├── **directory_tree_manager.py** 🔴 **WYSOKI PRIORYTET** - Manager drzewa katalogów (1687 linii), problemy z wydajnością
│ │ ├── **file_operations_ui.py** 🟡 **ŚREDNI PRIORYTET** - UI operacji na plikach, duplikacja logiki
│ │ ├── **gallery_manager.py** 🟡 **ŚREDNI PRIORYTET** - Manager galerii, wymagana optymalizacja
│ │ ├── **gallery_manager_fixed.py** 🟢 **NISKI PRIORYTET** - Duplikat gallery_manager.py, do usunięcia
│ │ ├── **fixed_folder_stats_worker.py** 🟢 **NISKI PRIORYTET** - Pusty plik, do usunięcia
│ │ ├── ****init**.py** 🟢 **NISKI PRIORYTET** - Plik inicjalizacyjny modułu
│ │ ├── **delegates/**
│ │ │ ├── **workers.py** 🔴 **WYSOKI PRIORYTET** - Workery do zadań w tle (2067 linii), bardzo skomplikowane, duplikacja kodu
│ │ │ ├── **scanner_worker.py** 🟡 **ŚREDNI PRIORYTET** - Worker skanowania, duplikacja z workers.py
│ │ │ └── ****init**.py** 🟢 **NISKI PRIORYTET** - Plik inicjalizacyjny modułu
│ │ └── **widgets/**
│ │ ├── **file_tile_widget.py** 🟡 **ŚREDNI PRIORYTET** - Widget kafelka pliku, optymalizacja renderowania
│ │ ├── **file_tile_widget.py.new** 🟢 **NISKI PRIORYTET** - Nowa wersja, do scalenia lub usunięcia
│ │ ├── **file_tile_widget.py.fixed** 🟢 **NISKI PRIORYTET** - Pusty plik, do usunięcia
│ │ ├── **preferences_dialog.py** 🟡 **ŚREDNI PRIORYTET** - Dialog preferencji, wymagana optymalizacja
│ │ ├── **thumbnail_cache.py** 🟡 **ŚREDNI PRIORYTET** - Cache miniaturek, problemy z zarządzaniem pamięcią
│ │ ├── **metadata_controls_widget.py** 🟢 **NISKI PRIORYTET** - Widget kontroli metadanych
│ │ ├── **preview_dialog.py** 🟢 **NISKI PRIORYTET** - Dialog podglądu
│ │ ├── **filter_panel.py** 🟢 **NISKI PRIORYTET** - Panel filtrów
│ │ ├── **tile_styles.py** 🟢 **NISKI PRIORYTET** - Style kafelków
│ │ └── ****init**.py** 🟢 **NISKI PRIORYTET** - Plik inicjalizacyjny modułu
│ ├── **utils/**
│ │ ├── **path_utils.py** 🟡 **ŚREDNI PRIORYTET** - Utility ścieżek, wymagana optymalizacja
│ │ ├── **image_utils.py** 🟢 **NISKI PRIORYTET** - Utility obrazów
│ │ ├── **logging_config.py** 🟢 **NISKI PRIORYTET** - Konfiguracja logowania
│ │ ├── **arg_parser.py** 🟢 **NISKI PRIORYTET** - Parser argumentów
│ │ ├── **style_loader.py** 🟢 **NISKI PRIORYTET** - Ładowacz stylów
│ │ └── ****init**.py** 🟢 **NISKI PRIORYTET** - Plik inicjalizacyjny modułu
│ └── **resources/**
│ └── **styles.qss** 🟢 **NISKI PRIORYTET** - Arkusz stylów Qt
├── **requirements.txt** 🟢 **NISKI PRIORYTET** - Zależności projektu
└── **pytest.ini** 🟢 **NISKI PRIORYTET** - Konfiguracja testów

---

## 🎯 WSTĘPNA ANALIZA PLIKÓW

### 🔴 WYSOKÍ PRIORYTET - Krytyczne problemy wydajności i struktury

#### **run_app.py**

- **Funkcjonalność:** Główny punkt wejścia aplikacji z obsługą argumentów CLI
- **Wydajność:** Niski wpływ, ale krytyczne dla działania całej aplikacji
- **Stan obecny:** Problemy z konfiguracją sys.path, nadmierna obsługa błędów, mieszanie logiki
- **Zależności:** src/main.py, src/utils/\*
- **Priorytet poprawek:** NATYCHMIASTOWY - podstawa działania aplikacji

#### **src/main.py**

- **Funkcjonalność:** Inicjalizacja aplikacji Qt, obsługa wyjątków globalnych
- **Wydajność:** Krytyczny wpływ na startowalność aplikacji
- **Stan obecny:** Nadmiarowa obsługa wyjątków, niepotrzebna logika uruchamiania bezpośredniego
- **Zależności:** PyQt6, src/ui/main_window.py, src/utils/logging_config.py
- **Priorytet poprawek:** NATYCHMIASTOWY - centralne miejsce startu aplikacji

#### **src/logic/scanner.py** (916 linii)

- **Funkcjonalność:** Skanowanie folderów, parowanie plików, cache wyników
- **Wydajność:** KRYTYCZNY wpływ - obsługuje tysiące plików, główna funkcjonalność
- **Stan obecny:** Bardzo duży plik, skomplikowany cache, problemy z wydajnością przy dużych zbiorach danych
- **Zależności:** src/models/file_pair.py, src/utils/path_utils.py, src/app_config.py
- **Priorytet poprawek:** NATYCHMIASTOWY - serce aplikacji

#### **src/ui/main_window.py** (2010 linii)

- **Funkcjonalność:** Główne okno aplikacji, zarządzanie UI i stanem
- **Wydajność:** Wysoki wpływ na responsywność interfejsu
- **Stan obecny:** Nadmiernie skomplikowane, za dużo odpowiedzialności, problemy z separacją logiki
- **Zależności:** PyQt6, wszystkie pozostałe moduły UI, services, logic
- **Priorytet poprawek:** NATYCHMIASTOWY - monolityczna struktura

#### **src/ui/directory_tree_manager.py** (1687 linii)

- **Funkcjonalność:** Zarządzanie drzewem katalogów, drag&drop, statystyki folderów
- **Wydajność:** Wysoki wpływ na nawigację po folderach
- **Stan obecny:** Bardzo duży plik, problemy z wydajnością przy dużych struktur folderów
- **Zależności:** PyQt6, src/logic/scanner.py, src/logic/file_operations.py
- **Priorytet poprawek:** NATYCHMIASTOWY - kluczowa funkcjonalność

#### **src/ui/delegates/workers.py** (2067 linii)

- **Funkcjonalność:** Wszystkie workery do zadań w tle (skanowanie, operacje na plikach)
- **Wydajność:** KRYTYCZNY wpływ na wszystkie operacje w tle
- **Stan obecny:** Największy plik, bardzo skomplikowany, duplikacja kodu między workerami
- **Zależności:** PyQt6, src/logic/_, src/models/_, src/utils/\*
- **Priorytet poprawek:** NATYCHMIASTOWY - refaktoryzacja i podział na mniejsze moduły

### 🟡 ŚREDNI PRIORYTET - Ważne optymalizacje i ulepszenia

#### **src/app_config.py**

- **Funkcjonalność:** Zarządzanie konfiguracją aplikacji, walidacja ustawień
- **Wydajność:** Średni wpływ, ładowanie przy starcie
- **Stan obecny:** Dobrze napisane, wymagana optymalizacja walidatorów i cache
- **Zależności:** json, src/utils/path_utils.py
- **Priorytet poprawek:** Średni - optymalizacja walidacji

#### **src/controllers/main_window_controller.py**

- **Funkcjonalność:** Kontroler wzorca MVC dla głównego okna
- **Wydajność:** Średni wpływ na organizację kodu
- **Stan obecny:** Wymaga pełnej implementacji wzorca MVC
- **Zależności:** src/ui/main_window.py
- **Priorytet poprawek:** Średni - implementacja architektury MVC

#### **src/logic/metadata_manager.py**

- **Funkcjonalność:** Zarządzanie metadanymi plików (gwiazdy, kolory, komentarze)
- **Wydajność:** Średni wpływ, operacje I/O na metadanych
- **Stan obecny:** Wymagana optymalizacja operacji I/O i cache
- **Zależności:** json, src/models/file_pair.py, src/utils/path_utils.py
- **Priorytet poprawek:** Średni - optymalizacja I/O

#### **src/services/** (wszystkie pliki)

- **Funkcjonalność:** Warstwa serwisowa aplikacji
- **Wydajność:** Średni wpływ, abstrakcja biznesowa
- **Stan obecny:** Duplikacja funkcjonalności z logic/, niejasna architektura
- **Zależności:** src/logic/_, src/models/_
- **Priorytet poprawek:** Średni - refaktoryzacja architektury

#### **src/models/file_pair.py**

- **Funkcjonalność:** Model danych reprezentujący parę plików (archiwum + podgląd)
- **Wydajność:** Średni wpływ, używany wszędzie
- **Stan obecny:** Dobrze napisane, wymagana optymalizacja struktury danych
- **Zależności:** src/utils/path_utils.py
- **Priorytet poprawek:** Średni - optymalizacja wydajności

#### **src/ui/widgets/** (główne pliki)

- **Funkcjonalność:** Komponenty interfejsu użytkownika
- **Wydajność:** Średni wpływ na wydajność renderowania
- **Stan obecny:** Wymagane optymalizacje renderowania i zarządzania pamięcią
- **Zależności:** PyQt6, src/models/\*
- **Priorytet poprawek:** Średni - optymalizacja UI

#### **src/utils/path_utils.py**

- **Funkcjonalność:** Utility do obsługi ścieżek plików
- **Wydajność:** Średni wpływ, używane wszędzie
- **Stan obecny:** Wymagana optymalizacja normalizacji ścieżek
- **Zależności:** os, pathlib
- **Priorytet poprawek:** Średni - optymalizacja funkcji

### 🟢 NISKI PRIORYTET - Drobne poprawki i czyszczenie

#### Pliki do usunięcia/scalenia:

- **src/ui/gallery_manager_fixed.py** - Duplikat gallery_manager.py
- **src/ui/fixed_folder_stats_worker.py** - Pusty plik
- **src/ui/widgets/file_tile_widget.py.fixed** - Pusty plik
- **src/ui/widgets/file_tile_widget.py.new** - Do scalenia z głównym plikiem

#### Pliki konfiguracyjne i pomocnicze:

- Wszystkie ****init**.py** - Sprawdzenie poprawności importów
- **requirements.txt** - Aktualizacja wersji zależności
- **pytest.ini** - Konfiguracja testów
- **src/resources/styles.qss** - Sprawdzenie nieużywanych stylów

---

## 📋 PLAN ETAPU 2

### Kolejność analizy (zgodnie z priorytetami):

1. **FAZA 1 - Krytyczne pliki (🔴)**

   - src/logic/scanner.py
   - src/ui/main_window.py
   - src/ui/directory_tree_manager.py
   - src/ui/delegates/workers.py
   - src/main.py
   - run_app.py

2. **FAZA 2 - Ważne optymalizacje (🟡)**

   - src/app_config.py
   - src/controllers/main_window_controller.py
   - src/logic/metadata_manager.py
   - src/services/\* (wszystkie)
   - src/models/file_pair.py
   - src/ui/widgets/\* (główne)
   - src/utils/path_utils.py

3. **FAZA 3 - Czyszczenie kodu (🟢)**
   - Usunięcie duplikatów i pustych plików
   - Sprawdzenie **init**.py
   - Aktualizacja plików konfiguracyjnych

### Grupowanie plików:

- **Grupa 1:** Scanner + Models (wydajność core)
- **Grupa 2:** UI + Workers (responsywność)
- **Grupa 3:** Services + Logic (architektura)
- **Grupa 4:** Utils + Config (fundament)

### Szacowany zakres zmian:

- **Refaktoryzacja:** 6 dużych plików (podział na mniejsze moduły)
- **Optymalizacja:** Cache, I/O, renderowanie UI
- **Usunięcie:** 4 niepotrzebne pliki
- **Architektura:** Implementacja MVC, usunięcie duplikacji

---

## 📊 STATYSTYKI PROJEKTU

- **Łączna liczba plików kodu:** 32
- **Pliki wysokiego priorytetu:** 6 (18,7%)
- **Pliki średniego priorytetu:** 14 (43,8%)
- **Pliki niskiego priorytetu:** 12 (37,5%)
- **Największe pliki:** workers.py (2067), main_window.py (2010), directory_tree_manager.py (1687), scanner.py (916)
- **Pliki do usunięcia:** 4
- **Szacowany czas analizy ETAPU 2:** 6-8 sesji roboczych

---

**Status ETAPU 1:** ✅ **ZAKOŃCZONY**  
**Gotowość do ETAPU 2:** ✅ **TAK** - Mapa kompletna, priorytety ustalone
