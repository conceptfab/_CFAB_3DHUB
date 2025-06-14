# Plan Refaktoryzacji CFAB_3DHUB

## 🎯 Cel Refaktoryzacji

Podział rozbudowanych plików na mniejsze, logiczne komponenty w celu:

- Poprawy czytelności i utrzymywalności kodu
- Ułatwienia testowania jednostkowego
- Zmniejszenia coupling między komponentami
- Zwiększenia reużywalności kodu
- Lepszej organizacji odpowiedzialności (Single Responsibility Principle)

## 📊 Analiza Obecnej Struktury

### Pliki wymagające refaktoryzacji (według rozmiaru i złożoności):

1. **src/ui/main_window.py** - 2250 linii ⚠️ KRYTYCZNY
2. **src/app_config.py** - 870 linii ⚠️ WYSOKI
3. **src/logic/metadata_manager.py** - 1012 linii ⚠️ WYSOKI
4. **src/ui/file_operations_ui.py** - 1002 linii ⚠️ WYSOKI
5. **src/ui/widgets/unpaired_files_tab.py** - 770 linii ⚠️ ŚREDNI
6. **src/ui/widgets/file_tile_widget.py** - 765 linii ⚠️ ŚREDNI
7. **src/ui/widgets/preferences_dialog.py** - 740 linii ⚠️ ŚREDNI
8. **src/ui/widgets/file_explorer_tab.py** - 587 linii ⚠️ ŚREDNI
9. **src/ui/widgets/duplicate_renamer_widget.py** - 565 linii ⚠️ ŚREDNI

## 🚀 Plan Refaktoryzacji - Podział na Etapy

---

## **ETAP 1: Refaktoryzacja MainWindow (KRYTYCZNY)**

_Priorytet: NAJWYŻSZY | Czas: 3-4 dni_

### 1.1 Analiza odpowiedzialności MainWindow

- **UI Management** - zarządzanie interfejsem
- **Event Handling** - obsługa zdarzeń
- **Worker Management** - zarządzanie wątkami
- **Data Processing** - przetwarzanie danych
- **File Operations** - operacje na plikach
- **Progress Management** - zarządzanie postępem
- **Menu & Toolbar** - menu i paski narzędzi

### 1.2 Podział MainWindow na komponenty:

#### `src/ui/main_window/main_window_core.py`

```python
class MainWindow(QMainWindow):
    """Główna klasa okna - tylko inicjalizacja i koordynacja"""
    # Tylko podstawowa inicjalizacja i delegowanie
```

#### `src/ui/main_window/ui_manager.py`

```python
class UIManager:
    """Zarządzanie elementami interfejsu użytkownika"""
    # - setup_menu_bar()
    # - _create_top_panel()
    # - _create_bulk_operations_panel()
    # - _init_ui()
```

#### `src/ui/main_window/event_handler.py`

```python
class EventHandler:
    """Obsługa zdarzeń i sygnałów"""
    # - resizeEvent()
    # - closeEvent()
    # - _handle_*() metody
```

#### `src/ui/main_window/worker_manager.py`

```python
class WorkerManager:
    """Zarządzanie workerami i wątkami"""
    # - _start_data_processing_worker()
    # - _setup_worker_connections()
    # - _cleanup_threads()
```

#### `src/ui/main_window/progress_manager.py`

```python
class ProgressManager:
    """Zarządzanie paskami postępu i statusem"""
    # - _show_progress()
    # - _hide_progress()
    # - _on_thumbnail_progress()
```

#### `src/ui/main_window/file_operations_coordinator.py`

```python
class FileOperationsCoordinator:
    """Koordynacja operacji na plikach"""
    # - _perform_bulk_delete()
    # - _perform_bulk_move()
    # - handle_file_drop_on_folder()
```

### 1.3 Rezultat ETAPU 1: ✅ UKOŃCZONY

- ✅ MainWindow zmniejszony z 2250 do 1724 linii (redukcja o 526 linii, ~23%)
- ✅ 6 nowych wyspecjalizowanych klas utworzonych:
  - `ui_manager.py` (382 linie) - zarządzanie interfejsem
  - `progress_manager.py` (160 linii) - zarządzanie postępem
  - `worker_manager.py` (197 linii) - zarządzanie wątkami
  - `event_handler.py` (175 linii) - obsługa zdarzeń
  - `file_operations_coordinator.py` (285 linii) - operacje na plikach
  - `main_window.py` (1724 linie) - główna klasa (zrefaktoryzowana)
- ✅ Aplikacja uruchamia się bez błędów
- ✅ Wszystkie funkcjonalności zachowane
- ✅ Struktura pakietu `src/ui/main_window/` utworzona z właściwym `__init__.py`

---

## **ETAP 2: Refaktoryzacja AppConfig**

_Priorytet: WYSOKI | Czas: 2 dni_

### 2.1 Podział AppConfig na komponenty:

#### `src/config/config_core.py`

```python
class AppConfig:
    """Główna klasa konfiguracji - singleton i podstawowe operacje"""
```

#### `src/config/config_validator.py`

```python
class ConfigValidator:
    """Walidacja konfiguracji - przeniesione z app_config.py"""
```

#### `src/config/config_defaults.py`

```python
class ConfigDefaults:
    """Domyślne wartości konfiguracji"""
    DEFAULT_CONFIG = {...}
```

#### `src/config/config_io.py`

```python
class ConfigIO:
    """Operacje I/O - ładowanie i zapisywanie"""
    # - _load_config()
    # - _save_config()
    # - _delayed_save()
```

#### `src/config/config_properties.py`

```python
class ConfigProperties:
    """Właściwości i gettery/settery"""
    # - get_thumbnail_format()
    # - set_thumbnail_quality()
    # - wszystkie property metody
```

### 2.2 Rezultat ETAPU 2:

- AppConfig zmniejszony z 870 do ~200 linii
- 5 wyspecjalizowanych modułów
- Lepsze testowanie walidacji
- Czytelniejsza organizacja

---

## **ETAP 3: Refaktoryzacja MetadataManager**

_Priorytet: WYSOKI | Czas: 2-3 dni_

### 3.1 Podział MetadataManager na komponenty:

#### `src/logic/metadata/metadata_core.py`

```python
class MetadataManager:
    """Główna klasa zarządzania metadanymi"""
```

#### `src/logic/metadata/metadata_io.py`

```python
class MetadataIO:
    """Operacje I/O metadanych"""
    # - _load_metadata_from_file()
    # - _save_metadata_to_file()
    # - _atomic_write()
```

#### `src/logic/metadata/metadata_cache.py`

```python
class MetadataCache:
    """Cache metadanych z TTL"""
    # - cache operations
    # - invalidation logic
```

#### `src/logic/metadata/metadata_validator.py`

```python
class MetadataValidator:
    """Walidacja struktury metadanych"""
    # - _validate_metadata_structure()
    # - validation rules
```

#### `src/logic/metadata/metadata_operations.py`

```python
class MetadataOperations:
    """Operacje na metadanych"""
    # - save_metadata()
    # - get_metadata()
    # - apply_metadata_to_file_pairs()
```

### 3.2 Rezultat ETAPU 3:

- MetadataManager zmniejszony z 1012 do ~300 linii
- 5 wyspecjalizowanych modułów
- Lepsze testowanie cache i walidacji
- Czytelniejsza logika biznesowa

---

## **ETAP 4: Refaktoryzacja FileOperationsUI**

_Priorytet: ŚREDNI | Czas: 2 dni_

### 4.1 Podział FileOperationsUI na komponenty:

#### `src/ui/file_operations/file_operations_core.py`

```python
class FileOperationsUI:
    """Główna klasa operacji na plikach"""
```

#### `src/ui/file_operations/pairing_operations.py`

```python
class PairingOperations:
    """Operacje parowania plików"""
    # - start_manual_pairing()
    # - _handle_manual_pairing_finished()
```

#### `src/ui/file_operations/rename_operations.py`

```python
class RenameOperations:
    """Operacje zmiany nazw"""
    # - start_rename_operation()
    # - _handle_rename_finished()
```

#### `src/ui/file_operations/delete_operations.py`

```python
class DeleteOperations:
    """Operacje usuwania"""
    # - start_delete_operation()
    # - _handle_delete_finished()
```

#### `src/ui/file_operations/move_operations.py`

```python
class MoveOperations:
    """Operacje przenoszenia"""
    # - start_move_operation()
    # - _handle_move_finished()
```

### 4.2 Rezultat ETAPU 4:

- FileOperationsUI zmniejszony z 1002 do ~250 linii
- 5 wyspecjalizowanych klas operacji
- Lepsze testowanie każdej operacji
- Czytelniejsza logika operacji

---

## **ETAP 5: Refaktoryzacja Widget'ów**

_Priorytet: ŚREDNI | Czas: 3-4 dni_

### 5.1 UnpairedFilesTab (770 linii)

#### `src/ui/widgets/unpaired_files/unpaired_files_core.py`

```python
class UnpairedFilesTab:
    """Główna klasa zakładki nieparowanych plików"""
```

#### `src/ui/widgets/unpaired_files/unpaired_preview_tile.py`

```python
class UnpairedPreviewTile(QWidget):
    """Widget pojedynczego kafelka podglądu"""
```

#### `src/ui/widgets/unpaired_files/unpaired_list_manager.py`

```python
class UnpairedListManager:
    """Zarządzanie listami nieparowanych plików"""
```

### 5.2 FileTileWidget (765 linii)

#### `src/ui/widgets/tiles/file_tile_core.py`

```python
class FileTileWidget(QWidget):
    """Główny widget kafelka pliku"""
```

#### `src/ui/widgets/tiles/tile_ui_manager.py`

```python
class TileUIManager:
    """Zarządzanie UI kafelka"""
```

#### `src/ui/widgets/tiles/tile_event_handler.py`

```python
class TileEventHandler:
    """Obsługa zdarzeń kafelka"""
```

### 5.3 PreferencesDialog (740 linii)

#### `src/ui/dialogs/preferences/preferences_core.py`

```python
class PreferencesDialog(QDialog):
    """Główne okno preferencji"""
```

#### `src/ui/dialogs/preferences/preferences_tabs.py`

```python
class PreferencesTabs:
    """Zarządzanie zakładkami preferencji"""
```

#### `src/ui/dialogs/preferences/preferences_validation.py`

```python
class PreferencesValidation:
    """Walidacja ustawień preferencji"""
```

### 5.4 Rezultat ETAPU 5:

- 3 duże widget'y podzielone na mniejsze komponenty
- Każdy widget zmniejszony o ~60-70%
- Lepsze testowanie UI komponentów
- Czytelniejsza struktura widget'ów

---

## **ETAP 6: Optymalizacja Struktury Katalogów**

_Priorytet: NISKI | Czas: 1 dzień_

### 6.1 Nowa struktura katalogów:

```
src/
├── config/                     # NOWE - konfiguracja
│   ├── config_core.py
│   ├── config_validator.py
│   ├── config_defaults.py
│   ├── config_io.py
│   └── config_properties.py
├── logic/
│   ├── metadata/               # NOWE - metadane
│   │   ├── metadata_core.py
│   │   ├── metadata_io.py
│   │   ├── metadata_cache.py
│   │   ├── metadata_validator.py
│   │   └── metadata_operations.py
│   └── ... (pozostałe)
├── ui/
│   ├── main_window/            # NOWE - główne okno
│   │   ├── main_window_core.py
│   │   ├── ui_manager.py
│   │   ├── event_handler.py
│   │   ├── worker_manager.py
│   │   ├── progress_manager.py
│   │   └── file_operations_coordinator.py
│   ├── file_operations/        # NOWE - operacje na plikach
│   │   ├── file_operations_core.py
│   │   ├── pairing_operations.py
│   │   ├── rename_operations.py
│   │   ├── delete_operations.py
│   │   └── move_operations.py
│   ├── widgets/
│   │   ├── unpaired_files/     # NOWE - nieparowane pliki
│   │   ├── tiles/              # NOWE - kafelki
│   │   ├── dialogs/            # NOWE - dialogi
│   │   └── ... (pozostałe)
│   └── ... (pozostałe)
└── ... (pozostałe)
```

---

## **ETAP 7: Testy i Walidacja**

_Priorytet: WYSOKI | Czas: 2 dni_

### 7.1 Testy jednostkowe dla nowych komponentów:

- Testy dla każdego nowego modułu
- Testy integracyjne dla współpracy komponentów
- Testy regresyjne dla istniejącej funkcjonalności

### 7.2 Walidacja refaktoryzacji:

- Sprawdzenie czy wszystkie funkcje działają
- Testy wydajnościowe
- Sprawdzenie memory leaks
- Walidacja UI/UX

---

## 📋 Harmonogram Realizacji

| Etap                        | Czas    | Priorytet | Status       |
| --------------------------- | ------- | --------- | ------------ |
| ETAP 1: MainWindow          | 3-4 dni | NAJWYŻSZY | ✅ UKOŃCZONY |
| ETAP 2: AppConfig           | 2 dni   | WYSOKI    | ⏳ Planowany |
| ETAP 3: MetadataManager     | 2-3 dni | WYSOKI    | ⏳ Planowany |
| ETAP 4: FileOperationsUI    | 2 dni   | ŚREDNI    | ⏳ Planowany |
| ETAP 5: Widget'y            | 3-4 dni | ŚREDNI    | ⏳ Planowany |
| ETAP 6: Struktura katalogów | 1 dzień | NISKI     | ⏳ Planowany |
| ETAP 7: Testy i walidacja   | 2 dni   | WYSOKI    | ⏳ Planowany |

**Całkowity czas: 15-20 dni roboczych**

---

## 🎯 Oczekiwane Korzyści

### Krótkoterminowe:

- ✅ Lepsze zrozumienie kodu
- ✅ Łatwiejsze debugowanie
- ✅ Szybsze dodawanie nowych funkcji
- ✅ Lepsze testowanie jednostkowe

### Długoterminowe:

- ✅ Łatwiejsza konserwacja
- ✅ Mniejsze ryzyko błędów
- ✅ Lepsza skalowalność
- ✅ Ułatwiona współpraca zespołowa
- ✅ Możliwość reużycia komponentów

---

## ⚠️ Ryzyka i Mitygacja

### Ryzyka:

1. **Wprowadzenie nowych błędów** - Mitygacja: Obszerne testy regresyjne
2. **Czasowe pogorszenie wydajności** - Mitygacja: Benchmarki przed i po
3. **Złamanie istniejącej funkcjonalności** - Mitygacja: Stopniowa refaktoryzacja
4. **Zwiększona złożoność struktury** - Mitygacja: Dobra dokumentacja

### Plan awaryjny:

- Każdy etap w osobnej gałęzi Git
- Możliwość rollback po każdym etapie
- Backup przed rozpoczęciem każdego etapu

---

## 📝 Notatki Implementacyjne

### Zasady refaktoryzacji:

1. **Single Responsibility Principle** - jedna klasa = jedna odpowiedzialność
2. **Don't Repeat Yourself** - eliminacja duplikacji kodu
3. **Keep It Simple** - prostota ponad złożoność
4. **Backward Compatibility** - zachowanie istniejących API gdzie możliwe

### Konwencje nazewnictwa:

- `*_core.py` - główne klasy modułu
- `*_manager.py` - klasy zarządzające
- `*_operations.py` - klasy operacyjne
- `*_handler.py` - klasy obsługi zdarzeń
- `*_validator.py` - klasy walidacji

---

_Plan utworzony: 2024_
_Wersja: 1.0_
_Status: Gotowy do implementacji_
