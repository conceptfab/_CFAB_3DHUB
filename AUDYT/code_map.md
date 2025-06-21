# 🗺️ Mapa Kodu Projektu CFAB_3DHUB

## 📝 Legenda Priorytetów

- ⚫⚫⚫⚫ **Krytyczny:** Wymaga natychmiastowej uwagi. Błędy, wąskie gardła wydajności, poważne problemy architektoniczne.
- 🔴🔴🔴 **Wysoki:** Ważne problemy do rozwiązania. Duże pliki, skomplikowany kod, potencjalne błędy.
- 🟡🟡 **Średni:** Możliwe optymalizacje. Refaktoryzacja dla czytelności, drobne poprawki.
- 🟢 **Niski:** Drobne zmiany. Poprawki kosmetyczne, aktualizacja dokumentacji.

---

## 🚀 Plan Kolejności Analizy

Analiza będzie przeprowadzana zgodnie z priorytetami, od ⚫⚫⚫⚫ do 🟢. W ramach tego samego priorytetu, kolejność będzie następująca:

1.  **Core Logic & Config:** (`config/`, `logic/`, `services/`) - fundamenty aplikacji.
2.  **Controllers & Models:** (`controllers/`, `models/`) - warstwa pośrednicząca i struktury danych.
3.  **UI Layer:** (`ui/`) - najobszerniejsza i najbardziej złożona część, wymagająca podziału na mniejsze etapy.
4.  **Utilities & Root:** (`utils/`, pliki w `src/`) - narzędzia pomocnicze i pliki startowe.

---

## 📂 Mapa Modułów

### 📁 `src/` (Główne pliki aplikacji)

| Plik            | Priorytet | Opis problemu/potrzeby                                                                        | Zależności                                   | Szacowany Zakres |
| --------------- | --------- | --------------------------------------------------------------------------------------------- | -------------------------------------------- | ---------------- |
| `main.py`       | 🟢        | Plik startowy aplikacji. Raczej stabilny.                                                     | `app_config`, `MainWindow`, `logging_config` | Niski            |
| `run_app.py`    | 🟢        | Skrypt do uruchamiania aplikacji. Minimalna logika.                                           | `main`                                       | Niski            |
| `app_config.py` | 🟡🟡      | Globalny dostęp do konfiguracji. Może być uproszczony, zależności mogą być lepiej zarządzane. | `config.config_core`                         | Średni           |
| `qt_imports.py` | 🟢        | Centralizacja importów Qt. Dobra praktyka, nie wymaga zmian.                                  | `PyQt6`                                      | Niski            |

### 📁 `src/config/` (Zarządzanie konfiguracją)

| Plik                   | Priorytet | Opis problemu/potrzeby                                                                       | Zależności                                  | Szacowany Zakres |
| ---------------------- | --------- | -------------------------------------------------------------------------------------------- | ------------------------------------------- | ---------------- |
| `config_core.py`       | 🔴🔴🔴    | [Zrefaktoryzowano] Skomplikowany singleton. Nadal może być uproszczony.                      | `threading`, `config_io`, `config_defaults` | Średni           |
| `config_defaults.py`   | 🟢        | Domyślne wartości konfiguracji. Przejrzysty.                                                 | `pathlib`                                   | Niski            |
| `config_io.py`         | 🟡🟡      | Operacje I/O na pliku konfiguracyjnym. Obsługa błędów może być poprawiona.                   | `json`, `os`                                | Średni           |
| `config_properties.py` | 🔴🔴🔴    | [Zrefaktoryzowano] "God class" dla właściwości. Podzielony, ale interakcje mogą być złożone. | `config_core`                               | Wysoki           |
| `config_validator.py`  | 🟡🟡      | Walidacja ustawień. Może być zintegrowany z properties.                                      | `config_core`                               | Średni           |
| `properties/*`         | 🔴🔴🔴    | [Nowe] Wynik refaktoryzacji `config_properties`. Należy zweryfikować spójność.               | `config_core`                               | Wysoki           |

### 📁 `src/controllers/` (Kontrolery)

| Plik                            | Priorytet | Opis problemu/potrzeby                                                             | Zależności                    | Szacowany Zakres |
| ------------------------------- | --------- | ---------------------------------------------------------------------------------- | ----------------------------- | ---------------- |
| `main_window_controller.py`     | ⚫⚫⚫⚫  | [Częściowo zrefaktoryzowany] Kluczowy kontroler, nadal skomplikowany. Dużo logiki. | `models`, `logic`, `ui`       | Bardzo Wysoki    |
| `file_operations_controller.py` | 🔴🔴🔴    | Zarządzanie operacjami na plikach. Dużo delegacji.                                 | `logic.file_operations`, `ui` | Wysoki           |
| `gallery_controller.py`         | 🔴🔴🔴    | Logika galerii. Ściśle powiązany z `gallery_manager`.                              | `ui.gallery_manager`          | Wysoki           |
| `scan_result_processor.py`      | 🟡🟡      | [Nowy] Przetwarzanie wyników skanowania. Dobry kandydat do uproszczenia.           | `models`                      | Średni           |
| `selection_manager.py`          | 🟡🟡      | [Nowy] Zarządzanie selekcją. Może być częścią `gallery_manager`.                   | `FilePair`                    | Średni           |
| `special_folders_manager.py`    | 🟢        | [Nowy] Prosta logika, dobrze wydzielona.                                           | `models`                      | Niski            |
| `statistics_controller.py`      | 🟡🟡      | Zarządzanie statystykami. Zależny od workerów.                                     | `ui.directory_tree.workers`   | Średni           |

### 📁 `src/logic/` (Logika biznesowa)

| Plik                              | Priorytet | Opis problemu/potrzeby                                                                                                              | Zależności               | Szacowany Zakres |
| --------------------------------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------ | ---------------- |
| `file_operations.py`              | ⚫⚫⚫⚫  | ✅ [PRZEANALIZOWANO] [2024-01-15] Fasada operacji na plikach, globalne singleton'y, problemy thread safety.                         | `shutil`, `os`           | Wysoki           |
| `file_pairing.py`                 | 🔴🔴🔴    | Kluczowy algorytm parowania plików. Wydajność jest krytyczna.                                                                       | `os`, `app_config`       | Wysoki           |
| `filter_logic.py`                 | 🟡🟡      | Logika filtrowania w galerii.                                                                                                       | `FilePair`               | Średni           |
| `metadata_manager.py`             | ⚫⚫⚫⚫  | [Zrefaktoryzowano] Był `metadata_manager_old.py`. Nowa implementacja z `metadata_core` wymaga weryfikacji.                          | `metadata.metadata_core` | Wysoki           |
| `scanner.py`                      | ⚫⚫⚫⚫  | [W TRAKCIE ANALIZY] Skanowanie folderów, wydajność, thread safety.                                                                  | `os`, `file_pairing`     | Wysoki           |
| `scanner_core.py`                 | 🔴🔴🔴    | Rdzeń skanera. Powiązany z `scanner.py`.                                                                                            | `os`, `app_config`       | Wysoki           |
| `cache_monitor.py`                | 🟢        | Monitorowanie cache. Prosta logika.                                                                                                 | -                        | Niski            |
| `scanner_cache.py`                | 🟡🟡      | Cache dla skanera. Może być uproszczony.                                                                                            | `json`                   | Średni           |
| `metadata/metadata_core.py`       | ⚫⚫⚫⚫  | ✅ [PRZEANALIZOWANO] [2024-01-15] - **POPRAWKI WPROWADZONE** ✅ Rdzeń systemu metadanych. Thread safety, memory leaks, performance. | `threading`, `weakref`   | Bardzo Wysoki    |
| `metadata/metadata_io.py`         | ⚫⚫⚫⚫  | ✅ [PRZEANALIZOWANO] [2024-01-15] - **POPRAWKI WPROWADZONE** ✅ Operacje I/O metadanych, atomic write, walidacja.                   | `filelock`, `json`       | Bardzo Wysoki    |
| `metadata/metadata_operations.py` | ⚫⚫⚫⚫  | ✅ [PRZEANALIZOWANO] [2024-01-15] - **POPRAWKI WPROWADZONE** ✅ Operacje biznesowe na metadanych, batch, path logic.                | `os`, `path_utils`       | Bardzo Wysoki    |
| `metadata/metadata_validator.py`  | ⚫⚫⚫⚫  | ✅ [PRZEANALIZOWANO] [2024-01-15] - **POPRAWKI WPROWADZONE** ✅ Walidacja metadanych, brak walidacji zakresów, nadmierne logowanie. | `logging`, `typing`      | Bardzo Wysoki    |

### 📁 `src/ui/` (Interfejs użytkownika)

| Plik                            | Priorytet | Opis problemu/potrzeby                                                                                           | Zależności                      | Szacowany Zakres |
| ------------------------------- | --------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------- | ---------------- |
| `main_window/main_window.py`    | ⚫⚫⚫⚫  | [W TRAKCIE ANALIZY] Główny plik UI, złożoność, sygnały, wydajność.                                               | _Praktycznie wszystko_          | Bardzo Wysoki    |
| `gallery_manager.py`            | ⚫⚫⚫⚫  | [W TRAKCIE ANALIZY] Zarządzanie siatką galerii, batch, powiązania z main_window.                                 | `FileTileWidget`, `main_window` | Bardzo Wysoki    |
| `directory_tree/manager.py`     | ⚫⚫⚫⚫  | [W TRAKCIE ANALIZY] Komponent drzewa katalogów, podział, wydajność, batch.                                       | `os`, `PyQt6`                   | Wysoki           |
| `file_operations_ui.py`         | ⚫⚫⚫⚫  | [W TRAKCIE ANALIZY] Operacje na plikach z UI, batch, delegacja do kontrolerów.                                   | `main_window`, `logic`          | Bardzo Wysoki    |
| `widgets/file_tile_widget.py`   | ⚫⚫⚫⚫  | [W TRAKCIE ANALIZY] Kafelek pliku w galerii, wydajność, eventy, batch.                                           | `FilePair`, `PyQt6`             | Bardzo Wysoki    |
| `widgets/unpaired_files_tab.py` | 🔴🔴🔴    | Zakładka z niepowiązanymi plikami. Dużo logiki, duplikacja kodu z galerii.                                       | `main_window`, `PyQt6`          | Wysoki           |
| `widgets/file_explorer_tab.py`  | 🔴🔴🔴    | Zakładka eksploratora plików. Nowa funkcja, ale już rozbudowana.                                                 | `QFileSystemModel`              | Wysoki           |
| `delegates/workers/*`           | 🔴🔴🔴    | Wszystkie workery. Logika działająca w tle. Kluczowe dla responsywności UI, ale też źródło błędów thread-safety. | `PyQt6.QtCore`                  | Wysoki           |
| `directory_tree/*`              | ⚫⚫⚫⚫  | [W TRAKCIE ANALIZY] Komponenty drzewa katalogów, podział, wydajność, batch.                                      | `PyQt6`                         | Wysoki           |
| Pozostałe pliki w `ui/`         | 🟡🟡      | Różne mniejsze komponenty UI, dialogi, widgety. Wymagają przeglądu pod kątem spójności.                          | `PyQt6`                         | Średni           |

---

## 📊 Status Analizy

### ✅ Przeanalizowane pliki:

1. **`src/logic/metadata/metadata_core.py`** - ✅ [PRZEANALIZOWANO] [2024-01-15] - **POPRAWKI WPROWADZONE** ✅
2. **`src/logic/metadata/metadata_io.py`** - ✅ [PRZEANALIZOWANO] [2024-01-15] - **POPRAWKI WPROWADZONE** ✅
3. **`src/logic/metadata/metadata_operations.py`** - ✅ [PRZEANALIZOWANO] [2024-01-15] - **POPRAWKI WPROWADZONE** ✅
4. **`src/logic/metadata/metadata_validator.py`** - ✅ [PRZEANALIZOWANO] [2024-01-15] - **POPRAWKI WPROWADZONE** ✅
5. **`src/logic/scanner.py`** - ✅ [PRZEANALIZOWANO] [2024-01-15]
6. **`src/logic/file_operations.py`** - ✅ [PRZEANALIZOWANO] [2024-01-15]

### 🔄 W trakcie analizy:

7. **`src/ui/main_window/main_window.py`** - 🔄 [W TRAKCIE ANALIZY]
8. **`src/ui/gallery_manager.py`** - 🔄 [W TRAKCIE ANALIZY]
9. **`src/ui/directory_tree/manager.py`** - 🔄 [W TRAKCIE ANALIZY]
10. **`src/ui/file_operations_ui.py`** - 🔄 [W TRAKCIE ANALIZY]
11. **`src/ui/widgets/file_tile_widget.py`** - 🔄 [W TRAKCIE ANALIZY]

### ⏳ Oczekujące na analizę:

- Pozostałe pliki zgodnie z mapą kodu i priorytetami

---

## 🎯 Następne kroki

- Kontynuacja szczegółowej analizy i przygotowanie poprawek dla kolejnych plików krytycznych (⚫⚫⚫⚫)
- Po zakończeniu analizy każdego pliku - aktualizacja statusu i dokumentacji
