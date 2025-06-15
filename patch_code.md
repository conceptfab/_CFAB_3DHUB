# 🔧 PATCH CODE - KONKRETNE POPRAWKI KODU

## ETAP 2.1: Usunięcie duplikacji metadata_manager_old.py

### 🗑️ USUNIĘCIE PLIKU

**Plik do usunięcia:** `src/logic/metadata_manager_old.py`

**Uzasadnienie:**

- Plik zawiera 1012 linii nieużywanego kodu
- Brak importów w całym projekcie (zweryfikowane przez grep)
- Funkcjonalność w pełni zastąpiona przez nową architekturę w `src/logic/metadata/`
- Backward compatibility zapewniona przez wrapper w `src/logic/metadata_manager.py`

**Akcja:**

```bash
# Usunięcie pliku
rm src/logic/metadata_manager_old.py
```

**Weryfikacja po usunięciu:**

```bash
# Sprawdzenie czy aplikacja się uruchamia
python run_app.py --help

# Sprawdzenie importów (powinno zwrócić brak wyników)
grep -r "metadata_manager_old" src/
```

---

## ETAP 2.2: Refaktoryzacja directory_tree/manager.py

### 📊 ANALIZA STRUKTURY PLIKU (1159 linii)

**Plik główny:** `src/ui/directory_tree/manager.py`

**Identyfikowane komponenty do wydzielenia:**

#### 1. DirectoryTreeEventHandler (linie ~50-200)

```python
# Nowy plik: src/ui/directory_tree/event_handler.py
"""
Event handler dla drzewa katalogów.
Obsługuje zdarzenia Qt i interakcje użytkownika.
"""

class DirectoryTreeEventHandler:
    """Obsługa zdarzeń dla drzewa katalogów."""

    def __init__(self, manager):
        self.manager = manager

    def handle_item_clicked(self, item):
        """Obsługa kliknięcia w element drzewa."""
        # Kod z manager.py linie ~80-120
        pass

    def handle_item_expanded(self, item):
        """Obsługa rozwinięcia elementu."""
        # Kod z manager.py linie ~120-160
        pass

    def handle_context_menu(self, position):
        """Obsługa menu kontekstowego."""
        # Kod z manager.py linie ~160-200
        pass
```

#### 2. DirectoryTreeDataManager (linie ~200-400)

```python
# Nowy plik: src/ui/directory_tree/data_manager.py
"""
Manager danych dla drzewa katalogów.
Obsługuje ładowanie i cache'owanie danych katalogów.
"""

class DirectoryTreeDataManager:
    """Manager danych drzewa katalogów."""

    def __init__(self, cache, working_directory):
        self.cache = cache
        self.working_directory = working_directory

    def load_directory_data(self, path):
        """Ładuje dane katalogu z cache lub dysku."""
        # Kod z manager.py linie ~220-280
        pass

    def update_directory_stats(self, path):
        """Aktualizuje statystyki katalogu."""
        # Kod z manager.py linie ~280-340
        pass

    def refresh_directory(self, path):
        """Odświeża dane katalogu."""
        # Kod z manager.py linie ~340-400
        pass
```

#### 3. DirectoryTreeRenderer (linie ~400-600)

```python
# Nowy plik: src/ui/directory_tree/renderer.py
"""
Renderer dla drzewa katalogów.
Obsługuje wyświetlanie i formatowanie elementów drzewa.
"""

class DirectoryTreeRenderer:
    """Renderer elementów drzewa katalogów."""

    def __init__(self):
        self.icon_cache = {}

    def render_directory_item(self, item, directory_data):
        """Renderuje element katalogu w drzewie."""
        # Kod z manager.py linie ~420-480
        pass

    def update_item_appearance(self, item, stats):
        """Aktualizuje wygląd elementu na podstawie statystyk."""
        # Kod z manager.py linie ~480-540
        pass

    def get_directory_icon(self, path, has_files=False):
        """Zwraca ikonę dla katalogu."""
        # Kod z manager.py linie ~540-600
        pass
```

#### 4. DirectoryTreeWorkerCoordinator (linie ~600-800)

```python
# Nowy plik: src/ui/directory_tree/worker_coordinator.py
"""
Koordynator workerów dla drzewa katalogów.
Zarządza wątkami skanowania i aktualizacji.
"""

class DirectoryTreeWorkerCoordinator:
    """Koordynator workerów drzewa katalogów."""

    def __init__(self, scheduler):
        self.scheduler = scheduler
        self.active_workers = {}

    def start_directory_scan(self, path):
        """Rozpoczyna skanowanie katalogu w tle."""
        # Kod z manager.py linie ~620-680
        pass

    def handle_worker_finished(self, worker_id, result):
        """Obsługuje zakończenie pracy workera."""
        # Kod z manager.py linie ~680-740
        pass

    def cancel_all_workers(self):
        """Anuluje wszystkie aktywne workery."""
        # Kod z manager.py linie ~740-800
        pass
```

#### 5. DirectoryTreeManager (refaktoryzowany, linie ~800-1159)

```python
# Zmodyfikowany plik: src/ui/directory_tree/manager.py
"""
Główny manager drzewa katalogów - zrefaktoryzowany.
Koordynuje pracę wszystkich komponentów.
"""

from .event_handler import DirectoryTreeEventHandler
from .data_manager import DirectoryTreeDataManager
from .renderer import DirectoryTreeRenderer
from .worker_coordinator import DirectoryTreeWorkerCoordinator

class DirectoryTreeManager:
    """
    Główny manager drzewa katalogów.
    Koordynuje pracę wszystkich komponentów.
    """

    def __init__(self, tree_widget, working_directory):
        self.tree_widget = tree_widget
        self.working_directory = working_directory

        # Inicjalizacja komponentów
        self.event_handler = DirectoryTreeEventHandler(self)
        self.data_manager = DirectoryTreeDataManager(cache, working_directory)
        self.renderer = DirectoryTreeRenderer()
        self.worker_coordinator = DirectoryTreeWorkerCoordinator(scheduler)

        # Połączenie sygnałów
        self._connect_signals()

    def _connect_signals(self):
        """Łączy sygnały Qt z handlerami."""
        self.tree_widget.itemClicked.connect(self.event_handler.handle_item_clicked)
        self.tree_widget.itemExpanded.connect(self.event_handler.handle_item_expanded)
        # ... pozostałe połączenia

    def refresh_tree(self):
        """Odświeża całe drzewo katalogów."""
        # Uproszczona logika koordynująca komponenty
        pass

    def update_directory(self, path):
        """Aktualizuje konkretny katalog."""
        # Delegacja do odpowiednich komponentów
        data = self.data_manager.load_directory_data(path)
        self.renderer.render_directory_item(item, data)
        pass
```

### 🎯 PLAN IMPLEMENTACJI ETAPU 2.2

**Krok 1:** Utworzenie nowych plików komponentów
**Krok 2:** Przeniesienie kodu z manager.py do odpowiednich komponentów
**Krok 3:** Refaktoryzacja głównego managera
**Krok 4:** Aktualizacja importów w plikach używających managera
**Krok 5:** Testy funkcjonalności

---

## ETAP 2.3: Refaktoryzacja main_window/main_window.py

### 📊 ANALIZA STRUKTURY PLIKU (1070 linii)

**Plik główny:** `src/ui/main_window/main_window.py`

**Status:** ⏳ OCZEKUJE NA ANALIZĘ

**Przewidywane komponenty do wydzielenia:**

- MainWindowUI - interfejs użytkownika
- MainWindowLogic - logika biznesowa
- MainWindowEventHandler - obsługa zdarzeń
- MainWindowStateManager - zarządzanie stanem

---

## 📈 STATUS PATCH CODE

### Gotowe do implementacji:

- ✅ **ETAP 2.1** - Usunięcie metadata_manager_old.py
- 🔧 **ETAP 2.2** - Plan refaktoryzacji directory_tree/manager.py

---

## ETAP 2.5: Refaktoryzacja scanner_core.py

### 📊 ANALIZA STRUKTURY PLIKU (363 linie)

**Plik główny:** `src/logic/scanner_core.py`

**Identyfikowane komponenty do wydzielenia:**

#### 1. FileScanner (linie ~40-230)

```python
# Nowy plik: src/logic/scanning/file_scanner.py
"""
Główny skaner plików z optymalizacjami wydajności.
"""

class FileScanner:
    """Skaner plików z streaming i interrupt handling."""

    def __init__(self, interrupt_checker=None):
        self.interrupt_checker = interrupt_checker
        self.visited_dirs = set()

    def scan_directory_streaming(self, directory, max_depth=-1):
        """Skanuje katalog z streaming progress."""
        # Kod z collect_files_streaming
        pass

    def _walk_directory_recursive(self, current_dir, depth=0):
        """Rekursywne przechodzenie katalogów."""
        # Kod z _walk_directory_streaming
        pass
```

#### 2. ScanProgressTracker (nowy komponent)

```python
# Nowy plik: src/logic/scanning/progress_tracker.py
"""
Tracker postępu skanowania z inteligentnym raportowaniem.
"""

class ScanProgressTracker:
    """Zarządza postępem skanowania."""

    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.total_folders = 0
        self.total_files = 0

    def report_progress(self, current_folder, files_found):
        """Raportuje postęp skanowania."""
        pass

    def calculate_progress_percentage(self):
        """Oblicza procent postępu."""
        pass
```

### 🎯 PLAN IMPLEMENTACJI ETAPU 2.5

**Krok 1:** Utworzenie pakietu `src/logic/scanning/`
**Krok 2:** Wydzielenie FileScanner z głównej funkcji
**Krok 3:** Utworzenie ScanProgressTracker
**Krok 4:** Refaktoryzacja cache managera
**Krok 5:** Aktualizacja głównej funkcji scan_folder_for_pairs

---

## ETAP 2.6: Optymalizacja file_pairing.py

### 📊 ANALIZA STRUKTURY PLIKU (201 linii)

**Plik główny:** `src/logic/file_pairing.py`

**Status:** ✅ DOBRA STRUKTURA - Tylko drobne optymalizacje

#### Optymalizacje wydajności strategii "best_match":

```python
# Optymalizacja w src/logic/file_pairing.py
def create_file_pairs_optimized(
    file_map: Dict[str, List[str]],
    base_directory: str,
    pair_strategy: str = "best_match",
) -> Tuple[List[FilePair], Set[str]]:
    """
    Zoptymalizowana wersja tworzenia par plików.
    """

    if pair_strategy == "best_match":
        # OPTYMALIZACJA 1: Pre-compute wszystkich nazw bazowych
        archive_base_names = {}
        preview_base_names = {}

        # OPTYMALIZACJA 2: Równoległe przetwarzanie dla dużych folderów
        if len(file_map) > 1000:
            return _create_pairs_parallel(file_map, base_directory)

        # OPTYMALIZACJA 3: Lepszy algorytm dopasowania
        return _create_pairs_optimized_matching(file_map, base_directory)
```

### 🎯 PLAN IMPLEMENTACJI ETAPU 2.6

**Krok 1:** Dodanie testów jednostkowych
**Krok 2:** Optymalizacja algorytmu "best_match"
**Krok 3:** Dodanie równoległego przetwarzania
**Krok 4:** Optymalizacja zarządzania pamięcią

---

## 📈 STATUS PATCH CODE

### Gotowe do implementacji:

- ✅ **ETAP 2.1** - Usunięcie metadata_manager_old.py
- 🔧 **ETAP 2.2** - Plan refaktoryzacji directory_tree/manager.py
- 🔧 **ETAP 2.5** - Plan refaktoryzacji scanner_core.py
- 🔧 **ETAP 2.6** - Plan optymalizacji file_pairing.py

### W przygotowaniu:

- ⏳ **ETAP 2.3** - main_window/main_window.py
- ⏳ **ETAP 2.4** - file_operations_ui.py
