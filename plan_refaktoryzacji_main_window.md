# Plan refaktoryzacji src/ui/main_window.py

## Analiza problemu

`main_window.py` to największy plik w projekcie (2010 linii), zawierający monolityczną klasę `MainWindow` z 65 metodami. Klasa łamie zasady czystego kodu, mieszając różne odpowiedzialności:

- Konstrukcja interfejsu użytkownika (UI)
- Logika biznesowa
- Zarządzanie wątkami i asynchronicznością
- Obsługa stanu aplikacji
- Operacje na plikach
- Obsługa dialogów i komunikatów

Plik wymaga głębokiej refaktoryzacji zgodnie z zasadami Single Responsibility Principle i wzorcem MVC.

## Cele refaktoryzacji

1. **Podział monolitycznej klasy** na mniejsze, specjalistyczne moduły
2. **Implementacja prawdziwego MVC** z separacją widoku, kontrolera i modelu
3. **Eliminacja legacy serwisów** i konsolidacja logiki w kontrolerze
4. **Centralizacja zarządzania stanem** aplikacji
5. **Poprawa wydajności** inicjalizacji i odświeżania interfejsu
6. **Implementacja nowych funkcjonalności UI** w zakładce parowania plików

## Plan działania

Refaktoryzacja zostanie podzielona na 3 główne etapy, każdy o czasie trwania około tygodnia:

### Etap 1: Podstawowy podział - struktura plików i katalogów

#### 1.1 Utworzenie struktury katalogów (0.5 dnia)

```
src/ui/main_window/
├── __init__.py                    # Eksport MainWindow dla kompatybilności
├── main_window.py                 # Główna klasa koordynacyjna
├── views/                         # Moduły widoków
│   ├── __init__.py
│   ├── main_window_view.py        # Bazowa struktura UI
│   ├── gallery_view.py            # Zakładka galerii
│   ├── unpaired_files_view.py     # Zakładka niesparowanych plików
│   └── toolbar_view.py            # Toolbary i panele kontrolne
├── dialogs/                       # Moduły dialogów
│   ├── __init__.py
│   ├── dialog_manager.py          # Zarządzanie dialogami
│   └── message_dialogs.py         # Komunikaty i potwierdzenia
└── actions/                       # Moduły akcji UI
    ├── __init__.py
    ├── ui_actions.py              # Akcje interfejsu
    └── view_updater.py            # Aktualizacja widoków
```

#### 1.2 Wyodrębnienie bazowej klasy widoku (1 dzień)

```python
# main_window_view.py
class MainWindowView(QMainWindow):
    """Bazowa klasa widoku odpowiedzialna za podstawowe UI."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self._init_window()
        self._init_ui()

    def _init_window(self):
        # Konfiguracja okna (tytuł, rozmiar, itp.)

    def _init_ui(self):
        # Podstawowe elementy UI (menu, pasek statusu, główny layout)
```

#### 1.3 Implementacja klasy koordynacyjnej (1 dzień)

```python
# main_window.py
class MainWindow(QMainWindow):
    """Główna klasa koordynacyjna - fasada aplikacji."""

    def __init__(self):
        super().__init__()
        # Inicjalizacja kontrolera i stanu
        self.state = MainWindowState()
        self.controller = MainWindowController(self)

        # Inicjalizacja widoków
        self.main_view = MainWindowView(self.controller)
        self.setCentralWidget(self.main_view)

        # Auto-ładowanie ostatniego folderu
        self._auto_load_last_folder()
```

#### 1.4 Implementacja klasy dialogów (1 dzień)

```python
# dialog_manager.py
class DialogManager:
    """Zarządzanie dialogami aplikacji."""

    def __init__(self, parent):
        self.parent = parent

    def show_preferences(self):
        # Implementacja dialogu preferencji

    def show_about(self):
        # Implementacja dialogu o aplikacji

    def show_error_message(self, title, message):
        # Wyświetlanie komunikatów błędów
```

#### 1.5 Zachowanie kompatybilności importów (0.5 dnia)

```python
# __init__.py w src/ui/main_window
from .main_window import MainWindow

# Dla zachowania kompatybilności z istniejącym kodem
__all__ = ['MainWindow']
```

### Etap 2: Separacja widoków specjalistycznych

#### 2.1 Implementacja widoku galerii (1.5 dnia)

```python
# gallery_view.py
class GalleryView(QWidget):
    """Widok zakładki galerii."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self._init_ui()

    def _init_ui(self):
        # Implementacja UI galerii
        self._create_folder_tree()
        self._create_tiles_area()

    def _create_folder_tree(self):
        # Implementacja drzewa folderów

    def _create_tiles_area(self):
        # Implementacja obszaru kafelków
```

#### 2.2 Implementacja widoku niesparowanych plików z nowymi funkcjonalnościami (2.5 dnia)

```python
# unpaired_files_view.py
class UnpairedFilesView(QWidget):
    """Widok zakładki niesparowanych plików."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self._selected_preview = None
        self._checkboxes = {}
        self._init_ui()

    def _init_ui(self):
        # Implementacja UI niesparowanych plików
        self._create_archives_list()
        self._create_previews_grid()  # Nowa implementacja siatki z kafelkami

    def _create_preview_tile(self, preview_path):
        # Tworzenie kafelka z podglądem
        tile = QWidget()
        layout = QGridLayout(tile)

        # Checkbox w lewym górnym rogu (exclusive selection)
        checkbox = QCheckBox()
        checkbox.clicked.connect(lambda: self._on_preview_checkbox_clicked(checkbox, preview_path))
        self._checkboxes[preview_path] = checkbox

        # Miniatura podobna do galerii
        thumbnail = QLabel()
        thumbnail.setPixmap(self.controller.get_thumbnail(preview_path))

        # Ikona kosza w prawym górnym rogu
        delete_button = QPushButton()
        delete_button.setIcon(QIcon(":/icons/trash.png"))
        delete_button.setToolTip("Usuń plik")
        delete_button.clicked.connect(lambda: self._on_delete_icon_clicked(preview_path))

        # Dodanie elementów do layoutu
        layout.addWidget(checkbox, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(delete_button, 0, 1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        layout.addWidget(thumbnail, 1, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

        return tile
```

#### 2.3 Implementacja akcji UI (2 dni)

```python
# ui_actions.py
class UIActions:
    """Akcje interfejsu użytkownika."""

    def __init__(self, controller, main_view):
        self.controller = controller
        self.main_view = main_view

    def handle_directory_changed(self, directory):
        # Obsługa zmiany katalogu

    def handle_filter_changed(self):
        # Obsługa zmiany filtrów

    def update_selection_visibility(self):
        # Aktualizacja widoczności elementów na podstawie selekcji
```

### Etap 3: Integracja z MVC i system zdarzeń

#### 3.1 Implementacja menedżera stanu (1 dzień)

```python
# main_window_state.py
class MainWindowState:
    """Centralny zarządca stanu aplikacji."""

    def __init__(self):
        # Stan aplikacji
        self.current_directory = None
        self.file_pairs = []
        self.selected_tiles = set()
        self.unpaired_archives = []
        self.unpaired_previews = []

        # Stany UI
        self.is_scanning = False
        self.is_processing = False
```

#### 3.2 Implementacja Event Busa (1.5 dnia)

```python
# event_bus.py
class EventBus:
    """Magistrala zdarzeń dla komunikacji między komponentami."""

    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, callback):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)

    def publish(self, event_type, data=None):
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                callback(data)
```

#### 3.3 Integracja timeoutów dla wątków (1 dzień)

```python
# thread_manager.py
class ThreadManager:
    """Zarządzanie wątkami aplikacji."""

    def __init__(self):
        self.active_threads = {}

    def start_thread(self, thread_id, thread, worker):
        # Uruchamianie wątku z rejestracją

    def cleanup_threads(self, timeout_ms=3000):
        # Bezpieczne zamykanie wątków z timeoutem
```

#### 3.4 Testy integracji (1.5 dnia)

Implementacja testów integracyjnych dla:

- Inicjalizacji głównego okna
- Wyboru folderu roboczego
- Współpracy między kontrolerem a widokami
- Zamykania aplikacji z aktywnymi wątkami

## Harmonogram implementacji

### Tydzień 1: Etap 1 - Podstawowy podział

- Dzień 1-2: Zadania 1.1 - 1.2
- Dzień 3-4: Zadania 1.3 - 1.4
- Dzień 5: Zadanie 1.5 + testy bazowej funkcjonalności

### Tydzień 2: Etap 2 - Separacja widoków

- Dzień 1-2: Zadanie 2.1
- Dzień 3-5: Zadania 2.2 - 2.3

### Tydzień 3: Etap 3 - Integracja z MVC

- Dzień 1-2: Zadania 3.1 - 3.2
- Dzień 3: Zadanie 3.3
- Dzień 4-5: Zadanie 3.4 + testy końcowe

## Szczegóły implementacji nowych funkcjonalności UI

### Zakładka "Parowanie plików" - nowe wymagania UI

#### 1. Miniaturki podobne do galerii

- Wykorzystanie tego samego layoutu kafelkowego
- Spójny wygląd między zakładkami
- Wykorzystanie thumbnail_cache

#### 2. Ikona kosza zamiast przycisku "Usuń"

- Elegancka ikona w prawym górnym rogu kafelka
- Tooltip "Usuń plik" przy najechaniu
- Dialog potwierdzenia przed faktycznym usunięciem

#### 3. System checkboxów do parowania

- Checkbox w lewym górnym rogu kafelka
- Zachowanie "radio button" - tylko jeden checkbox zaznaczony
- Visual feedback dla zaznaczonego kafelka (podświetlenie ramki)

#### 4. Ulepszona funkcjonalność parowania

- Button "Sparuj zaznaczone" aktywny tylko przy spełnieniu warunków:
  - Zaznaczony jeden plik podglądu
  - Wybrany plik archiwum z listy
- Po sparowaniu automatyczne usunięcie plików z list

## Korzyści refaktoryzacji

- **Maintainable files** - żaden plik nie przekracza 600 linii
- **Clear separation** - rozdzielenie widoku, logiki biznesowej i stanu
- **Testability** - możliwość niezależnego testowania komponentów
- **Team collaboration** - praca równoległa na różnych komponentach
- **Import optimization** - każdy moduł importuje tylko potrzebne zależności

## Potencjalne ryzyka

1. **Kompatybilność wsteczna** - istniejący kod może oczekiwać określonej struktury `MainWindow`
2. **Wydajność** - podzielony kod może wprowadzić overhead komunikacyjny
3. **Spójność** - ryzyko niekonsekwencji w implementacji między modułami

## Plan minimalizacji ryzyk

1. Zachowanie publicznego API `MainWindow` dla zewnętrznych modułów
2. Monitorowanie wydajności podczas refaktoryzacji
3. Jasna dokumentacja API i konwencji pomiędzy modułami
4. Stopniowa migracja z testowaniem każdego kroku
