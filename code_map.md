# 🗺️ MAPA PROJEKTU CFAB_3DHUB

## Struktura projektu z priorytetami analizy

### CFAB_3DHUB/

├── **run_app.py** 🟡 ŚREDNI PRIORYTET - Punkt wejścia aplikacji, wymaga optymalizacji obsługi błędów
├── **src/**
│ ├── **main.py** 🟡 ŚREDNI PRIORYTET - Główna logika uruchamiania, nadmiarowa obsługa wyjątków
│ ├── **app_config.py** 🔴 WYSOKI PRIORYTET - Krytyczny plik konfiguracji, 643 linie, wymaga refaktoryzacji
│ ├── ****init**.py** 🟢 NISKI PRIORYTET - Standardowy plik inicjalizacyjny
│ ├── **controllers/**
│ │ └── **main_window_controller.py** 🔴 WYSOKI PRIORYTET - Główny kontroler MVC, 378 linii, kluczowy dla architektury
│ ├── **logic/**
│ │ ├── **metadata_manager.py** 🔴 WYSOKI PRIORYTET - Największy plik (798 linii), zarządza metadanymi, krytyczny dla wydajności
│ │ ├── **file_operations.py** 🟡 ŚREDNI PRIORYTET - Operacje na plikach, 374 linie, wymaga optymalizacji
│ │ ├── **scanner_core.py** 🟡 ŚREDNI PRIORYTET - Rdzeń skanowania, 354 linie, wydajność krytyczna
│ │ ├── **scanner_cache.py** 🟡 ŚREDNI PRIORYTET - Cache skanera, 257 linii, optymalizacja pamięci
│ │ ├── **scanner.py** 🟡 ŚREDNI PRIORYTET - Główny skaner, 222 linie, duplikacja z scanner.py.new
│ │ ├── **scanner.py.new** 🟢 NISKI PRIORYTET - Nowa wersja skanera, 142 linie, do weryfikacji
│ │ ├── **file_pairing.py** 🟡 ŚREDNI PRIORYTET - Logika parowania plików, 198 linii
│ │ ├── **filter_logic.py** 🟡 ŚREDNI PRIORYTET - Logika filtrowania, 164 linie
│ │ └── ****init**.py** 🟢 NISKI PRIORYTET - Plik inicjalizacyjny z importami
│ ├── **models/**
│ │ ├── **file_pair.py** 🟡 ŚREDNI PRIORYTET - Model danych, 284 linie, podstawa aplikacji
│ │ └── ****init**.py** 🟢 NISKI PRIORYTET - Standardowy plik inicjalizacyjny
│ ├── **services/**
│ │ ├── **file_operations_service.py** 🟡 ŚREDNI PRIORYTET - Serwis operacji na plikach, 200 linii
│ │ ├── **scanning_service.py** 🟡 ŚREDNI PRIORYTET - Serwis skanowania, 209 linii
│ │ ├── **thread_coordinator.py** 🟡 ŚREDNI PRIORYTET - Koordynacja wątków, 173 linie, krytyczne dla wydajności
│ │ └── ****init**.py** 🟢 NISKI PRIORYTET - Plik inicjalizacyjny
│ ├── **ui/**
│ │ ├── **main_window.py** 🔴 WYSOKI PRIORYTET - Główne okno UI, 1707 linii, największy plik UI, wymaga refaktoryzacji
│ │ ├── **directory_tree_manager.py** 🔴 WYSOKI PRIORYTET - Manager drzewa katalogów, 1795 linii, największy plik projektu
│ │ ├── **file_operations_ui.py** 🟡 ŚREDNI PRIORYTET - UI operacji na plikach, 802 linie
│ │ ├── **directory_tree_manager_refactored.py** 🟢 NISKI PRIORYTET - Zrefaktoryzowana wersja, 419 linii, do weryfikacji
│ │ ├── **gallery_manager.py** 🟡 ŚREDNI PRIORYTET - Manager galerii, 289 linii
│ │ ├── **gallery_manager_fixed.py** 🟢 NISKI PRIORYTET - Poprawiona wersja galerii, duplikacja
│ │ ├── **folder_operations_manager.py** 🟡 ŚREDNI PRIORYTET - Manager operacji folderów, 282 linie
│ │ ├── **folder_statistics_manager.py** 🟡 ŚREDNI PRIORYTET - Statystyki folderów, 277 linii
│ │ ├── **fixed_folder_stats_worker.py** 🟢 NISKI PRIORYTET - Pusty plik, do usunięcia
│ │ ├── ****init**.py** 🟢 NISKI PRIORYTET - Plik inicjalizacyjny
│ │ ├── **widgets/**
│ │ │ ├── **file_tile_widget.py** 🟡 ŚREDNI PRIORYTET - Widget kafelka pliku, 758 linii, kluczowy dla UI
│ │ │ ├── **preferences_dialog.py** 🟡 ŚREDNI PRIORYTET - Dialog preferencji, 740 linii
│ │ │ ├── **unpaired_files_tab.py** 🟡 ŚREDNI PRIORYTET - Zakładka niesparowanych plików, 568 linii
│ │ │ ├── **thumbnail_cache.py** 🟡 ŚREDNI PRIORYTET - Cache miniaturek, 375 linii, wydajność
│ │ │ ├── **metadata_controls_widget.py** 🟡 ŚREDNI PRIORYTET - Kontrolki metadanych, 292 linie
│ │ │ ├── **gallery_tab.py** 🟡 ŚREDNI PRIORYTET - Zakładka galerii, 247 linii
│ │ │ ├── **tile_styles.py** 🟢 NISKI PRIORYTET - Style kafelków, 160 linii
│ │ │ ├── **preview_dialog.py** 🟢 NISKI PRIORYTET - Dialog podglądu, 148 linii
│ │ │ ├── **filter_panel.py** 🟢 NISKI PRIORYTET - Panel filtrów, 72 linie
│ │ │ └── ****init**.py** 🟢 NISKI PRIORYTET - Plik inicjalizacyjny z importami
│ │ └── **delegates/**
│ │ ├── **scanner_worker.py** 🟡 ŚREDNI PRIORYTET - Worker skanera, 139 linii
│ │ ├── **workers.py** 🟢 NISKI PRIORYTET - Podstawowe workery, 49 linii
│ │ ├── ****init**.py** 🟢 NISKI PRIORYTET - Plik inicjalizacyjny
│ │ └── **workers/**
│ │ ├── **file_workers.py** 🟡 ŚREDNI PRIORYTET - Workery plików, 488 linii
│ │ ├── **processing_workers.py** 🟡 ŚREDNI PRIORYTET - Workery przetwarzania, 478 linii
│ │ ├── **base_workers.py** 🟡 ŚREDNI PRIORYTET - Bazowe workery, 361 linia
│ │ ├── **worker_factory.py** 🟡 ŚREDNI PRIORYTET - Fabryka workerów, 329 linii
│ │ ├── **bulk_workers.py** 🟡 ŚREDNI PRIORYTET - Workery operacji masowych, 327 linii
│ │ ├── **folder_workers.py** 🟡 ŚREDNI PRIORYTET - Workery folderów, 213 linii
│ │ ├── **scan_workers.py** 🟢 NISKI PRIORYTET - Workery skanowania, 90 linii
│ │ └── ****init**.py** 🟢 NISKI PRIORYTET - Plik inicjalizacyjny z importami
│ ├── **utils/**
│ │ ├── **path_utils.py** 🟡 ŚREDNI PRIORYTET - Narzędzia ścieżek, 379 linii, używane wszędzie
│ │ ├── **image_utils.py** 🟡 ŚREDNI PRIORYTET - Narzędzia obrazów, 201 linia
│ │ ├── **arg_parser.py** 🟢 NISKI PRIORYTET - Parser argumentów, 109 linii
│ │ ├── **style_loader.py** 🟢 NISKI PRIORYTET - Ładowacz stylów, 95 linii
│ │ ├── **logging_config.py** 🟢 NISKI PRIORYTET - Konfiguracja logowania, 53 linie
│ │ └── ****init**.py** 🟢 NISKI PRIORYTET - Plik inicjalizacyjny
│ └── **resources/**
│ └── **styles.qss** 🟢 NISKI PRIORYTET - Style QSS, 281 linii
└── **random_name.py** 🟢 NISKI PRIORYTET - Pomocniczy skrypt, 124 linie

## 📊 Podsumowanie analizy

### Statystyki projektu:

- **Łączna liczba plików kodu:** 47 plików Python + 1 plik QSS
- **Największe pliki wymagające refaktoryzacji:**
  1. `src/ui/directory_tree_manager.py` - 1795 linii
  2. `src/ui/main_window.py` - 1707 linii
  3. `src/logic/metadata_manager.py` - 798 linii
  4. `src/app_config.py` - 643 linie

### Identyfikowane problemy:

- **Duplikacja kodu:** scanner.py vs scanner.py.new, gallery_manager.py vs gallery_manager_fixed.py
- **Pusty plik:** fixed_folder_stats_worker.py (0 linii)
- **Nadmierne rozmiary plików:** Kilka plików przekracza 500 linii
- **Potencjalne problemy wydajności:** Duże pliki UI i logiki zarządzania metadanymi

### Priorytety refaktoryzacji:

- 🔴 **WYSOKI PRIORYTET:** 4 pliki (krytyczne dla architektury i wydajności)
- 🟡 **ŚREDNI PRIORYTET:** 25 plików (optymalizacje i ulepszenia)
- 🟢 **NISKI PRIORYTET:** 19 plików (drobne poprawki)

## 📋 Plan etapu 2

### Kolejność analizy (zgodnie z priorytetami):

#### Faza 1 - Krytyczne pliki architektury (🔴):

1. `src/ui/directory_tree_manager.py` - Największy plik, zarządzanie drzewem katalogów
2. `src/ui/main_window.py` - Główne okno aplikacji, centrum UI
3. `src/logic/metadata_manager.py` - Zarządzanie metadanymi, wydajność
4. `src/app_config.py` - Konfiguracja aplikacji, używana wszędzie
5. `src/controllers/main_window_controller.py` - Kontroler MVC

#### Faza 2 - Logika biznesowa i serwisy (🟡):

6. `src/logic/file_operations.py` - Operacje na plikach
7. `src/logic/scanner_core.py` - Rdzeń skanowania
8. `src/logic/scanner_cache.py` - Cache skanera
9. `src/logic/scanner.py` - Główny skaner
10. `src/services/thread_coordinator.py` - Koordynacja wątków
11. Pozostałe pliki logiki i serwisów

#### Faza 3 - UI i narzędzia (🟡 + 🟢):

12. Widgety UI (file_tile_widget.py, preferences_dialog.py, itp.)
13. Workery i delegaty
14. Narzędzia (utils)
15. Pliki pomocnicze i konfiguracyjne

### Szacowany zakres zmian:

- **Refaktoryzacja:** Podział dużych plików na mniejsze moduły
- **Optymalizacja:** Poprawa wydajności cache'owania i zarządzania pamięcią
- **Czyszczenie:** Usunięcie duplikatów i nieużywanego kodu
- **Dokumentacja:** Aktualizacja komentarzy i docstringów
- **Testy:** Identyfikacja miejsc wymagających testów jednostkowych
