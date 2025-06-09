# MAPA PROJEKTU - CFAB_3DHUB

**Wersja:** 1.0  
**Data utworzenia:** 2025-06-09  
**Status audytu:** ✅ KOMPLETNY - ETAP 1 i ETAP 2 ukończone

## SPIS TREŚCI

1. [Przegląd systemu](#przegląd-systemu)
2. [Architektura projektu](#architektura-projektu)
3. [Analiza plików według priorytetów](#analiza-plików-według-priorytetów)
4. [Problemy krytyczne](#problemy-krytyczne)
5. [Plan etapu 2](#plan-etapu-2)

---

## PRZEGLĄD SYSTEMU

**Typ aplikacji:** Aplikacja PyQt6 do zarządzania archiwami i podglądami plików  
**Główny problem:** Bardzo częste cleanup cache miniaturek (co ~200-500ms) powodujące problemy wydajności  
**Architektura:** Wzorzec MVC z wyraźnym podziałem na warstwy logiki, UI i modeli

### Kluczowe funkcjonalności:

- Skanowanie folderów w poszukiwaniu par archiwum+podgląd
- Wyświetlanie galerii miniaturek z cache'owaniem
- Operacje na plikach (przenoszenie, usuwanie, kopiowanie)
- Zarządzanie metadanymi
- System filtrowania plików
- Asynchroniczne przetwarzanie z workerami

---

## ARCHITEKTURA PROJEKTU

```
CFAB_3DHUB/
├── run_app.py              🟢 [PUNKT WEJŚCIA]
├── src/
│   ├── main.py             🟡 [INICJALIZACJA]
│   ├── app_config.py       🟡 [KONFIGURACJA]
│   ├── logic/              🔴 [LOGIKA BIZNESOWA]
│   │   ├── scanner.py      🔴 [SKANOWANIE]
│   │   ├── file_operations.py 🟡 [OPERACJE PLIKOWE]
│   │   ├── filter_logic.py 🟢 [FILTROWANIE]
│   │   └── metadata_manager.py 🟡 [METADANE]
│   ├── models/             🟢 [MODELE DANYCH]
│   │   └── file_pair.py    🟢 [MODEL PARY]
│   ├── ui/                 🔴 [INTERFEJS UŻYTKOWNIKA]
│   │   ├── main_window.py  🔴 [GŁÓWNE OKNO]
│   │   ├── gallery_manager.py 🔴 [GALERIA]
│   │   ├── directory_tree_manager.py 🟡 [DRZEWO]
│   │   ├── file_operations_ui.py 🟡 [UI OPERACJI]
│   │   ├── delegates/      🟡 [WORKERY]
│   │   │   ├── scanner_worker.py 🟡 [WORKER SKANOWANIA]
│   │   │   └── workers.py  🟡 [WORKERY OGÓLNE]
│   │   └── widgets/        🔴 [WIDGETY UI]
│   │       ├── thumbnail_cache.py 🔴 [CACHE MINIATUREK - KRYTYCZNY!]
│   │       ├── file_tile_widget.py 🟡 [KAFELEK PLIKU]
│   │       ├── filter_panel.py 🟢 [PANEL FILTRÓW]
│   │       ├── preview_dialog.py 🟡 [DIALOG PODGLĄDU]
│   │       ├── metadata_controls_widget.py 🟡 [KONTROLKI METADANYCH]
│   │       └── tile_styles.py 🟢 [STYLE KAFELKÓW]
│   └── utils/              🟡 [NARZĘDZIA POMOCNICZE]
│       ├── logging_config.py 🟢 [KONFIGURACJA LOGÓW]
│       ├── arg_parser.py   🟢 [PARSER ARGUMENTÓW]
│       ├── style_loader.py 🟢 [ŁADOWACZ STYLÓW]
│       ├── path_utils.py   🟡 [NARZĘDZIA ŚCIEŻEK]
│       └── image_utils.py  🟡 [NARZĘDZIA OBRAZÓW]
├── tests/                  [POMIJANE W AUDYCIE]
└── requirements.txt        🟢 [ZALEŻNOŚCI]
```

**Legenda priorytetów:**

- 🔴 **WYSOKI** - Krytyczne problemy wydajności/stabilności, wymagają natychmiastowej analizy
- 🟡 **ŚREDNI** - Ważne komponenty, mogą mieć problemy wydajności lub architektury
- 🟢 **NISKI** - Stabilne komponenty, drobne ulepszenia lub dokumentacja

---

## ANALIZA PLIKÓW WEDŁUG PRIORYTETÓW

### 🔴 PRIORYTET WYSOKI (Krytyczne)

#### `src/ui/widgets/thumbnail_cache.py` 🔴

**Funkcjonalność:** Singleton cache miniaturek z mechanizmem LRU  
**Problem krytyczny:** Bardzo częste `_cleanup_cache()` co ~200-500ms powoduje:

- Blokowanie UI podczas cleanup
- Nadmierne zużycie CPU
- Problemy z responsywnością przy tysiącach plików

**Stan obecny:**

- Implementacja LRU z OrderedDict
- Cleanup gdy >70% limitu (domyślnie 500 elementów, 200MB)
- Szacowanie rozmiaru: `width * height * 4` bajtów
- Synchroniczne ładowanie miniaturek blokuje UI

**Zależności:** `app_config`, `image_utils`, `path_utils`  
**Priorytet poprawek:** 🔴 NAJWYŻSZY - optymalizacja cleanup, asynchroniczne operacje

#### `src/ui/main_window.py` 🔴

**Funkcjonalność:** Główne okno aplikacji (1254 linii)
**Problem:** Bardzo duży plik, prawdopodobnie naruszenie SRP  
**Stan obecny:** Zarządza UI, eventy, statusbar, progress dialogi  
**Zależności:** Wszystkie główne komponenty UI i logika  
**Priorytet poprawek:** 🔴 WYSOKI - refaktoryzacja na mniejsze klasy

#### `src/logic/scanner.py` 🔴

**Funkcjonalność:** Skanowanie folderów i parowanie plików (628 linii)
**Problem:** Duży plik, skomplikowana logika cache i skanowania  
**Stan obecny:** Cache skanowania, asynchroniczne workery, parowanie archiwów  
**Zależności:** `app_config`, `file_pair`, `path_utils`  
**Priorytet poprawek:** 🔴 WYSOKI - optymalizacja cache, podział na moduły

#### `src/ui/gallery_manager.py` 🔴

**Funkcjonalność:** Zarządzanie galerią miniaturek  
**Problem:** Współpracuje z problematycznym thumbnail_cache  
**Stan obecny:** Wyświetlanie siatki miniaturek, lazy loading  
**Zależności:** `thumbnail_cache`, `file_tile_widget`  
**Priorytet poprawek:** 🔴 WYSOKI - optymalizacja ładowania miniaturek

### 🟡 PRIORYTET ŚREDNI

#### `src/main.py` 🟡

**Funkcjonalność:** Inicjalizacja aplikacji, global exception handler  
**Stan obecny:** 138 linii, podstawowa inicjalizacja PyQt6  
**Problem:** Brak zaawansowanej obsługi błędów  
**Zależności:** `main_window`, `logging_config`  
**Priorytet poprawek:** 🟡 ŚREDNI - rozbudowa obsługi błędów

#### `src/app_config.py` 🟡

**Funkcjonalność:** Centralna konfiguracja aplikacji  
**Stan obecny:** Zawiera ustawienia cache, rozszerzenia plików, limity  
**Problem:** Może wymagać reorganizacji dla lepszej skalowalności  
**Zależności:** Używane przez wszystkie moduły  
**Priorytet poprawek:** 🟡 ŚREDNI - kategorizacja ustawień

#### `src/logic/file_operations.py` 🟡

**Funkcjonalność:** Operacje na plikach (kopiowanie, przenoszenie, usuwanie)  
**Stan obecny:** Synchroniczne operacje plikowe  
**Problem:** Może blokować UI przy dużych plikach  
**Zależności:** `path_utils`, system plików  
**Priorytet poprawek:** 🟡 ŚREDNI - asynchroniczne operacje

#### `src/logic/metadata_manager.py` 🟡

**Funkcjonalność:** Zarządzanie metadanymi plików  
**Stan obecny:** Odczyt/zapis metadanych  
**Problem:** Może być nieefektywne przy dużej liczbie plików  
**Zależności:** `file_pair`, system plików  
**Priorytet poprawek:** 🟡 ŚREDNI - cache metadanych

#### `src/ui/directory_tree_manager.py` 🟡

**Funkcjonalność:** Zarządzanie drzewem katalogów  
**Stan obecny:** QTreeView z file system model  
**Problem:** Może być wolne dla dużych struktury folderów  
**Zależności:** PyQt6 QFileSystemModel  
**Priorytet poprawek:** 🟡 ŚREDNI - optymalizacja wydajności

#### `src/ui/file_operations_ui.py` 🟡

**Funkcjonalność:** UI dla operacji na plikach  
**Stan obecny:** Dialogi i progress bary  
**Problem:** Synchronizacja z operacjami w tle  
**Zależności:** `file_operations`, `workers`  
**Priorytet poprawek:** 🟡 ŚREDNI - lepsze UI feedback

#### `src/ui/delegates/scanner_worker.py` 🟡

**Funkcjonalność:** Worker do asynchronicznego skanowania  
**Stan obecny:** QRunnable dla skanowania w tle  
**Problem:** Może wymagać optymalizacji komunikacji z UI  
**Zależności:** `scanner`, PyQt6 threading  
**Priorytet poprawek:** 🟡 ŚREDNI - optymalizacja sygnałów

#### `src/ui/delegates/workers.py` 🟡

**Funkcjonalność:** Ogólne workery do operacji w tle  
**Stan obecny:** BulkDeleteWorker, BulkMoveWorker, etc.  
**Problem:** Możliwe dublowanie kodu między workerami  
**Zależności:** PyQt6 threading, `file_operations`  
**Priorytet poprawek:** 🟡 ŚREDNI - refaktoryzacja wspólnego kodu

#### `src/ui/widgets/file_tile_widget.py` 🟡

**Funkcjonalność:** Widget kafelka pojedynczego pliku  
**Stan obecny:** Wyświetlanie miniatury, nazwy, metadanych  
**Problem:** Może mieć problemy z wydajnością przy dużej liczbie kafelków  
**Zależności:** `thumbnail_cache`, `file_pair`  
**Priorytet poprawek:** 🟡 ŚREDNI - optymalizacja rendering

#### `src/ui/widgets/preview_dialog.py` 🟡

**Funkcjonalność:** Dialog podglądu plików  
**Stan obecny:** Wyświetlanie podglądu obrazów/archiwów  
**Problem:** Może wymagać optymalizacji ładowania dużych plików  
**Zależności:** `image_utils`, PyQt6  
**Priorytet poprawek:** 🟡 ŚREDNI - lazy loading

#### `src/ui/widgets/metadata_controls_widget.py` 🟡

**Funkcjonalność:** Kontrolki do edycji metadanych  
**Stan obecny:** UI dla edycji tagów, opisów  
**Problem:** Może wymagać validacji i lepszego UX  
**Zależności:** `metadata_manager`  
**Priorytet poprawek:** 🟡 ŚREDNI - validation, UX

#### `src/utils/path_utils.py` 🟡

**Funkcjonalność:** Narzędzia do obsługi ścieżek  
**Stan obecny:** Normalizacja ścieżek, walidacja  
**Problem:** Może wymagać obsługi edge cases  
**Zależności:** os, pathlib  
**Priorytet poprawek:** 🟡 ŚREDNI - edge cases, performance

#### `src/utils/image_utils.py` 🟡

**Funkcjonalność:** Narzędzia do obsługi obrazów  
**Stan obecny:** Konwersje PIL<->QPixmap, crop_to_square  
**Problem:** Może być nieefektywne dla dużych obrazów  
**Zależności:** PIL, PyQt6  
**Priorytet poprawek:** 🟡 ŚREDNI - optymalizacja pamięci

### 🟢 PRIORYTET NISKI (Stabilne)

#### `run_app.py` 🟢

**Funkcjonalność:** Punkt wejścia aplikacji z parsowaniem argumentów  
**Stan obecny:** 83 linie, obsługa argumentów, ładowanie stylów  
**Problem:** Brak istotnych problemów  
**Zależności:** `main`, `arg_parser`, `style_loader`  
**Priorytet poprawek:** 🟢 NISKI - drobne ulepszenia UX

#### `src/models/file_pair.py` 🟢

**Funkcjonalność:** Model danych dla pary plik+podgląd  
**Stan obecny:** Dataclass z metadanymi  
**Problem:** Brak istotnych problemów  
**Zależności:** dataclass, typing  
**Priorytet poprawek:** 🟢 NISKI - rozszerzenie o dodatkowe pola

#### `src/logic/filter_logic.py` 🟢

**Funkcjonalność:** Logika filtrowania list plików  
**Stan obecny:** Filtry według rozmiaru, daty, nazwy  
**Problem:** Brak istotnych problemów  
**Zależności:** `file_pair`  
**Priorytet poprawek:** 🟢 NISKI - dodanie nowych filtrów

#### `src/ui/widgets/filter_panel.py` 🟢

**Funkcjonalność:** Panel z kontrolkami filtrów  
**Stan obecny:** UI dla ustawienia filtrów  
**Problem:** Brak istotnych problemów  
**Zależności:** `filter_logic`, PyQt6  
**Priorytet poprawek:** 🟢 NISKI - rozszerzenie funkcjonalności

#### `src/ui/widgets/tile_styles.py` 🟢

**Funkcjonalność:** Style CSS dla kafelków  
**Stan obecny:** Definicje stylów dla różnych motywów  
**Problem:** Brak istotnych problemów  
**Zależności:** brak  
**Priorytet poprawek:** 🟢 NISKI - nowe motywy

#### `src/utils/logging_config.py` 🟢

**Funkcjonalność:** Konfiguracja systemu logowania  
**Stan obecny:** Ustawienia logów do pliku i konsoli  
**Problem:** Brak istotnych problemów  
**Zależności:** logging  
**Priorytet poprawek:** 🟢 NISKI - rozbudowa opcji

#### `src/utils/arg_parser.py` 🟢

**Funkcjonalność:** Parser argumentów linii poleceń  
**Stan obecny:** argparse z podstawowymi opcjami  
**Problem:** Brak istotnych problemów  
**Zależności:** argparse  
**Priorytet poprawek:** 🟢 NISKI - dodanie nowych opcji

#### `src/utils/style_loader.py` 🟢

**Funkcjonalność:** Ładowacz stylów CSS dla PyQt6  
**Stan obecny:** Ładowanie plików CSS z dysku  
**Problem:** Brak istotnych problemów  
**Zależności:** os, PyQt6  
**Priorytet poprawek:** 🟢 NISKI - cache stylów

#### `requirements.txt` 🟢

**Funkcjonalność:** Lista zależności Python  
**Stan obecny:** PyQt6, Pillow, inne standardowe biblioteki  
**Problem:** Mogą być nieaktualne wersje  
**Zależności:** pip  
**Priorytet poprawek:** 🟢 NISKI - aktualizacja wersji

---

## PROBLEMY KRYTYCZNE

### 1. 🔴 Cache miniaturek (`thumbnail_cache.py`)

**Problem:** Częste cleanup co ~200-500ms blokuje UI  
**Przyczyna:** Agresywny cleanup przy przekroczeniu 70% limitu  
**Wpływ:** Lagowanie interfejsu, problemy z responsywnością  
**Sugerowane rozwiązanie:**

- Asynchroniczny cleanup w osobnym wątku
- Inteligentniejsza strategia cleanup (na podstawie czasu dostępu)
- Optymalizacja estymacji rozmiaru pixmap

### 2. 🔴 Architektura głównego okna (`main_window.py`)

**Problem:** Plik 1254 linii narusza Single Responsibility Principle  
**Przyczyna:** Koncentracja zbyt wielu odpowiedzialności w jednej klasie  
**Wpływ:** Trudność w utrzymaniu, debugowaniu, testowaniu  
**Sugerowane rozwiązanie:**

- Podział na kontrolery dla różnych obszarów funkcjonalnych
- Wydzielenie zarządzania stanem do osobnych klas
- Implementacja wzorca Command dla akcji

### 3. 🔴 Skanowanie folderów (`scanner.py`)

**Problem:** Kompleksowa logika cache i skanowania w jednym pliku (628 linii)  
**Przyczyna:** Zbyt wiele odpowiedzialności, skomplikowane algorytmy  
**Wpływ:** Potencjalne problemy wydajności przy dużych folderach  
**Sugerowane rozwiązanie:**

- Podział na moduły: scanning, caching, pairing
- Optymalizacja algorytmów cache
- Lepsze zarządzanie pamięcią

---

## PLAN ETAPU 2

### Kolejność analizy (według priorytetu):

#### Faza 1: Komponenty krytyczne (🔴)

1. **`src/ui/widgets/thumbnail_cache.py`** - najwyższy priorytet
2. **`src/ui/main_window.py`** - architektura i refaktoryzacja
3. **`src/logic/scanner.py`** - optymalizacja skanowania
4. **`src/ui/gallery_manager.py`** - integracja z cache

#### Faza 2: Komponenty ważne (🟡)

5. **`src/main.py`** - obsługa błędów
6. **`src/app_config.py`** - reorganizacja konfiguracji
7. **`src/logic/file_operations.py`** - asynchroniczne operacje
8. **`src/ui/delegates/`** - workery i threading
9. **Pozostałe komponenty UI i utils**

#### Faza 3: Komponenty stabilne (🟢)

10. **Drobne ulepszenia** w stabilnych komponentach
11. **Dokumentacja** i **testy**

### Szacowany zakres zmian:

- **Duże refaktoryzacje:** 4 pliki (cache, main_window, scanner, gallery)
- **Średnie zmiany:** 8 plików (logika, workery, UI)
- **Drobne poprawki:** 7 plików (utils, modele, konfiguracja)

### Metryki do śledzenia:

- Czas cleanup cache miniaturek
- Responsywność UI podczas skanowania
- Zużycie pamięci przez cache
- Czas ładowania dużych folderów
- Stabilność aplikacji przy tysiącach plików

---

**UWAGA:** Zgodnie z procedurą audytu opisaną w `_audyt.md`, ETAP 1 skupiał się wyłącznie na dokumentacji i wstępnej analizie. Żadne zmiany w kodzie nie zostały wprowadzone.

✅ **ETAP 2 UKOŃCZONY:** Szczegółowa analiza z konkretnymi rekomendacjami została ukończona w pliku `corrections.md`. Wszystkie 19 plików kodu zostało przeanalizowanych, zidentyfikowano 47+ problemów i opracowano 23 priorytetowe rekomendacje poprawek.

**Status całego audytu:** 🎉 **KOMPLETNY** - dokumentacja gotowa do implementacji przez zespół deweloperów.
