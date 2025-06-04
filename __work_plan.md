# Plan Implementacji Projektu "CFAB_3DHUB"

**Wersja Planu:** 1.0
**Data:** 2023-10-27
**Na podstawie:** PRD Wersja 1.0, DATA.md Wersja 1.0

---

## 0. Wstęp i Cel Planu

Niniejszy dokument stanowi szczegółowy plan implementacji aplikacji "CFAB_3DHUB". Jego celem jest kierowanie procesem rozwoju, etap po etapie, z wyraźnym zdefiniowaniem zadań, oczekiwanych rezultatów, plików do modyfikacji/utworzenia, zależności, wymagań testowych i dokumentacyjnych. Każdy etap wymaga potwierdzenia przed przejściem do następnego.

---

## 1. Sugerowany Schemat Projektu (Struktura Folderów i Plików)

CFAB_3DHUB/
├── .venv/ # Wirtualne środowisko Pythona
├── src/ # Główny kod źródłowy aplikacji
│ ├── init.py
│ ├── main.py # Główny plik uruchomieniowy aplikacji
│ ├── app_config.py # Konfiguracje, stałe (np. obsługiwane rozszerzenia)
│ │
│ ├── models/ # Modele danych
│ │ ├── init.py
│ │ └── file_pair.py # Definicja klasy FilePair
│ │
│ ├── logic/ # Logika biznesowa
│ │ ├── init.py
│ │ ├── scanner.py # Skanowanie folderów, parowanie plików
│ │ ├── file_operations.py # Operacje na plikach (zmiana nazwy, usuwanie, etc.)
│ │ └── metadata_manager.py# Zarządzanie metadanymi (JSON, później może SQLite)
│ │
│ ├── ui/ # Komponenty interfejsu użytkownika
│ │ ├── init.py
│ │ ├── main_window.py # Główna klasa okna aplikacji (QMainWindow)
│ │ ├── widgets/ # Niestandardowe widgety
│ │ │ ├── init.py
│ │ │ ├── file_tile_widget.py # Widget reprezentujący kafelek
│ │ │ └── preview_dialog.py # Dialog do wyświetlania większego podglądu
│ │ └── delegates/ # Niestandardowi delegaci (np. dla QListView)
│ │ └── init.py
│ │
│ └── utils/ # Narzędzia pomocnicze
│ ├── init.py
│ ├── image_utils.py # Funkcje do obsługi obrazów (ładowanie, miniatury)
│ └── logging_config.py # Konfiguracja systemu logowania
│
├── tests/ # Testy
│ ├── init.py
│ ├── unit/ # Testy jednostkowe
│ │ ├── init.py
│ │ ├── test_file_pair.py
│ │ ├── test_scanner.py
│ │ └── # ... inne testy jednostkowe
│ └── integration/ # Testy integracyjne
│ ├── init.py
│ └── # ... testy integracyjne
│
├── ui_files/ # Opcjonalnie, pliki .ui z Qt Designer
│
├── .gitignore # Plik ignorowanych plików dla Git
├── README.md # Opis projektu, instrukcje
└── requirements.txt # Zależności projektu

---

## Etapy Implementacji

### Etap 0: Przygotowanie Środowiska i Fundamenty

- **Status:** `[x] Zakończony`
- **Cel Etapu:** Stworzenie podstawowej struktury projektu, konfiguracja środowiska, inicjalizacja głównego okna aplikacji i podstawowego logowania. Zdefiniowanie szkieletu klasy `FilePair`.
- **Wymagane Funkcjonalności:**
  1.  Utworzenie struktury folderów projektu zgodnie z powyższym schematem.
  2.  Inicjalizacja wirtualnego środowiska Pythona (`.venv`).
  3.  Utworzenie pliku `requirements.txt` i dodanie `PyQt6`, `Pillow`, `patool`.
  4.  Instalacja zależności z `requirements.txt`.
  5.  Stworzenie `src/main.py` z kodem inicjalizującym i wyświetlającym puste `QMainWindow` z `src/ui/main_window.py`.
  6.  Stworzenie `src/models/file_pair.py` z początkowym szkieletem klasy `FilePair` (przechowującej tylko ścieżki do plików).
  7.  Stworzenie `src/utils/logging_config.py` i podstawowa konfiguracja logowania (np. do konsoli i pliku). Wywołanie konfiguracji w `main.py`.
  8.  Stworzenie `README.md` z podstawowym opisem i instrukcją uruchomienia pustego okna.
  9.  Inicjalizacja repozytorium Git i stworzenie pliku `.gitignore`.
- **Nowe/Modyfikowane Pliki:**
  - `Cała struktura folderów`
  - `.venv/` (utworzone przez `python -m venv .venv`)
  - `src/__init__.py`
  - `src/main.py`
  - `src/ui/__init__.py`
  - `src/ui/main_window.py`
  - `src/models/__init__.py`
  - `src/models/file_pair.py`
  - `src/utils/__init__.py`
  - `src/utils/logging_config.py`
  - `tests/` (pusta struktura na razie)
  - `.gitignore`
  - `README.md`
  - `requirements.txt`
- **Zależności:** Brak.
- **Wymagane Testy:**
  - Manualne: Uruchomienie `python src/main.py` powinno wyświetlić puste okno aplikacji bez błędów.
  - Manualne: Sprawdzenie, czy logi pojawiają się w konsoli/pliku.
- **Podsumowanie Testów:** `[x] Wykonane` - Puste okno aplikacji wyświetla się poprawnie, logi są zapisywane do konsoli i pliku.
- **Dokumentacja:**
  - `[x] Zakończone`: `README.md` - instrukcja instalacji i uruchomienia.
  - `[x] Zakończone`: Podstawowe komentarze i docstringi w utworzonych plikach.
- **Potwierdzenie Zakończenia Etapu:** `[x] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

## **PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU.**

### Etap 1.A: Logika Biznesowa - Skanowanie Folderu i Parowanie Plików

- **Status:** `[x] Implementacja kodu zakończona`
- **Cel Etapu:** Implementacja logiki wyboru folderu roboczego, rekursywnego skanowania folderu, parowania plików na podstawie nazw i rozszerzeń oraz rozbudowa klasy `FilePair`.
- **Wymagane Funkcjonalności:**
  1.  **`src/app_config.py`**: Zdefiniowanie list obsługiwanych rozszerzeń archiwów (np. `.rar`, `.zip`) i podglądów (np. `.jpg`, `.jpeg`, `.png`).
  2.  **`src/logic/scanner.py`**:
      - Implementacja funkcji `scan_folder_for_pairs(directory_path)`:
        - Rekursywnie przeszukuje `directory_path` i podfoldery.
        - Identyfikuje pliki archiwów i podglądów na podstawie rozszerzeń z `app_config.py`.
        - Paruje pliki, jeśli mają identyczną nazwę (bez rozszerzenia). W przypadku wielu podglądów do jednego archiwum, wybiera pierwszy pasujący.
        - Zwraca listę obiektów `FilePair`.
  3.  **`src/models/file_pair.py`**:
      - Rozbudowa klasy `FilePair`:
        - Konstruktor przyjmujący ścieżkę do pliku archiwum i ścieżkę do pliku podglądu.
        - Przechowywanie tych ścieżek jako atrybuty.
        - Metoda `get_base_name()` zwracająca nazwę pliku bez rozszerzenia.
        - Metoda `get_archive_path()` i `get_preview_path()`.
- **Nowe/Modyfikowane Pliki:**
  - `src/app_config.py` (nowy)
  - `src/logic/scanner.py` (nowy)
  - `src/logic/__init__.py` (modyfikacja)
  - `src/models/file_pair.py` (modyfikacja)
- **Zależności:** Etap 0.
- **Wymagane Testy:**
  - **Jednostkowe (`tests/unit/test_scanner.py`):**
    - Test dla `scan_folder_for_pairs` z folderem zawierającym pasujące pary.
    - Test z folderem bez pasujących par.
    - Test z folderem zawierającym tylko archiwa lub tylko podglądy.
    - Test z folderem, gdzie jedno archiwum ma wiele potencjalnych podglądów (upewnić się, że wybierany jest jeden).
    - Test z pustym folderem.
    - Test z różnymi kombinacjami rozszerzeń.
  - **Jednostkowe (`tests/unit/test_file_pair.py`):**
    - Test konstruktora `FilePair`.
    - Test metod `get_base_name()`, `get_archive_path()`, `get_preview_path()`.
- **Podsumowanie Testów:** `[x] Wykonane`
- **Dokumentacja:**
  - `[x] Zakończone`: Docstringi dla funkcji w `scanner.py` i metod w `FilePair`.
  - `[x] Zakończone`: Komentarze wyjaśniające logikę parowania w `scanner.py`.
- **Potwierdzenie Zakończenia Etapu:** `[x] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

**ZAKTUALIZUJ STATUS ZAKOŃCZONEGO ZADANIA!**
**PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU.**

---

### Etap 1.B: Interfejs Użytkownika - Wybór Folderu i Wyświetlanie Listy Nazw

- **Status:** `[x] Implementacja kodu zakończona`
- **Cel Etapu:** Dodanie do UI przycisku wyboru folderu roboczego i wyświetlenie listy nazw sparowanych plików.
- **Wymagane Funkcjonalności:**
  1.  **`src/ui/main_window.py`**:
      - Dodanie przycisku "Wybierz Folder Roboczy" (`QPushButton`).
      - Dodanie `QListWidget` do wyświetlania nazw sparowanych plików.
      - Po kliknięciu przycisku:
        - Użycie `QFileDialog.getExistingDirectory()` do wyboru folderu przez użytkownika.
        - Jeśli folder został wybrany, wywołanie funkcji `scan_folder_for_pairs` z `src/logic/scanner.py`.
        - Wyczyszczenie `QListWidget` i zapełnienie go nazwami bazowymi (`file_pair.get_base_name()`) znalezionych par.
        - Przechowanie listy obiektów `FilePair` w atrybucie instancji `MainWindow`.
      - Obsługa sytuacji, gdy użytkownik anuluje wybór folderu.
- **Nowe/Modyfikowane Pliki:**
  - `src/ui/main_window.py` (modyfikacja)
- **Zależności:** Etap 0, Etap 1.A.
- **Wymagane Testy:**
  - **Manualne UI:**
    - Sprawdzenie, czy przycisk "Wybierz Folder Roboczy" jest widoczny i działa.
    - Sprawdzenie, czy dialog wyboru folderu pojawia się poprawnie.
    - Sprawdzenie, czy po wybraniu folderu z testowymi danymi, `QListWidget` jest poprawnie zapełniany nazwami sparowanych plików.
    - Sprawdzenie, czy wybranie innego folderu aktualizuje listę.
    - Sprawdzenie, czy anulowanie wyboru folderu nie powoduje błędu i lista pozostaje pusta/niezmieniona.
- **Podsumowanie Testów:** `[x] Wykonane`
- **Dokumentacja:**
  - `[x] Zakończone`: Docstringi dla nowych metod w `main_window.py`.
  - `[x] Zakończone`: Komentarze w UI dotyczące obsługi zdarzeń.
- **Potwierdzenie Zakończenia Etapu:** `[x] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

**ZAKTUALIZUJ STATUS ZAKOŃCZONEGO ZADANIA!**
**PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU.**

---

### Etap 2.A: Logika Biznesowa - Miniatury i Rozmiar Pliku

- **Status:** `[ ] Oczekujący`
- **Cel Etapu:** Rozbudowa `FilePair` o przechowywanie miniatury podglądu i rozmiaru pliku archiwum. Implementacja funkcji do ich pozyskiwania.
- **Wymagane Funkcjonalności:**
  1.  **`src/models/file_pair.py`**:
      - Rozbudowa klasy `FilePair`:
        - Dodanie atrybutów `preview_thumbnail` (początkowo `None`) i `archive_size_bytes` (początkowo `None`).
        - Metoda `load_preview_thumbnail(target_size_wh)`:
          - Przyjmuje krotkę `(width, height)` dla docelowego rozmiaru miniatury.
          - Używa `Pillow` do wczytania obrazu z `self.preview_path`.
          - Skaluje obraz do `target_size_wh` zachowując proporcje (np. `thumbnail` z Pillow).
          - Konwertuje obiekt `Pillow.Image` na `QPixmap` i przechowuje w `self.preview_thumbnail`.
          - Obsługuje błędy wczytywania obrazu (np. zwraca domyślną ikonę błędu jako `QPixmap`).
        - Metoda `get_archive_size()`:
          - Używa `os.path.getsize()` do pobrania rozmiaru pliku `self.archive_path`.
          - Przechowuje wynik w `self.archive_size_bytes`.
          - Zwraca rozmiar w bajtach.
        - Metoda `get_formatted_archive_size()`:
          - Formatuje `self.archive_size_bytes` do czytelnej postaci (KB, MB, GB).
  2.  **`src/utils/image_utils.py`**:
      - Można tu przenieść logikę tworzenia `QPixmap` z `Pillow.Image` jeśli będzie reużywana.
      - Funkcja `create_placeholder_pixmap(width, height, color, text)` do tworzenia domyślnych/błędnych miniatur.
- **Nowe/Modyfikowane Pliki:**
  - `src/models/file_pair.py` (modyfikacja)
  - `src/utils/image_utils.py` (modyfikacja/utworzenie, jeśli przenosimy logikę)
- **Zależności:** Etap 0, `Pillow`, `PyQt6`.
- **Wymagane Testy:**
  - **Jednostkowe (`tests/unit/test_file_pair.py`):**
    - Test dla `load_preview_thumbnail()`:
      - Z poprawnym plikiem obrazu.
      - Z nieistniejącym plikiem obrazu lub uszkodzonym (sprawdzić, czy zwraca domyślną miniaturę/obsługuje błąd).
      - Sprawdzenie rozmiaru wygenerowanej miniatury.
    - Test dla `get_archive_size()`:
      - Z istniejącym plikiem.
      - Z nieistniejącym plikiem (powinien obsłużyć błąd, np. zwrócić 0 lub None).
    - Test dla `get_formatted_archive_size()` dla różnych rozmiarów (bajty, KB, MB, GB).
  - **Jednostkowe (`tests/unit/test_image_utils.py` - jeśli utworzony):**
    - Test dla `create_placeholder_pixmap`.
- **Podsumowanie Testów:** `[ ] Do wykonania`
- **Dokumentacja:**
  - `[ ] Do uzupełnienia`: Docstringi dla nowych metod w `FilePair` i funkcji w `image_utils.py`.
- **Potwierdzenie Zakończenia Etapu:** `[ ] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

**ZAKTUALIZUJ STATUS ZAKOŃCZONEGO ZADANIA!**
**PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU.**

---

### Etap 2.B: Interfejs Użytkownika - Galeria Kafelków i Skalowanie

- **Status:** `[ ] Oczekujący`
- **Cel Etapu:** Zmiana sposobu wyświetlania na galerię kafelków. Każdy kafelek wyświetla miniaturę, nazwę, rozmiar archiwum. Dodanie suwaka do skalowania kafelków.
- **Wymagane Funkcjonalności:**
  1.  **`src/ui/widgets/file_tile_widget.py` (nowy):**
      - Stworzenie niestandardowego widgetu `FileTileWidget(QWidget)`:
        - Przyjmuje obiekt `FilePair` w konstruktorze.
        - Wyświetla:
          - Miniaturę (`QLabel` dla `QPixmap` z `file_pair.preview_thumbnail`).
          - Nazwę pliku bez rozszerzenia (`QLabel` dla `file_pair.get_base_name()`).
          - Rozmiar pliku archiwum (`QLabel` dla `file_pair.get_formatted_archive_size()`).
        - Metoda `update_data(file_pair)` do odświeżenia danych.
        - Metoda `set_thumbnail_size(size_wh)` do ustawiania rozmiaru wyświetlanej miniatury (i potencjalnie całego kafelka).
  2.  **`src/ui/main_window.py`**:
      - Zastąpienie `QListWidget` przez `QListWidget` (w trybie `IconMode`) lub `QListView` z niestandardowym delegatem, albo `QScrollArea` z `QVBoxLayout`/`QGridLayout` dynamicznie wypełnianym widgetami `FileTileWidget`. **Rekomendacja: `QScrollArea` z dynamicznie dodawanymi `FileTileWidget` do layoutu dla większej kontroli nad wyglądem kafelka.**
      - Po wybraniu folderu roboczego i zeskanowaniu plików:
        - Dla każdego obiektu `FilePair` z listy:
          - Wywołaj `file_pair.load_preview_thumbnail(default_thumbnail_size)`.
          - Wywołaj `file_pair.get_archive_size()`.
          - Stwórz instancję `FileTileWidget` i przekaż jej `file_pair`.
          - Dodaj `FileTileWidget` do layoutu w `QScrollArea`.
      - Dodanie `QSlider` do UI.
      - Połączenie sygnału `valueChanged` suwaka ze slotem, który:
        - Pobiera nową wartość suwaka (np. reprezentującą procent rozmiaru kafelka).
        - Przelicza ją na docelowy rozmiar miniatury/kafelka.
        - Iteruje po wszystkich `FileTileWidget` i wywołuje ich metodę `set_thumbnail_size()` oraz potencjalnie `file_pair.load_preview_thumbnail()` z nowym rozmiarem, jeśli miniatury mają być dynamicznie regenerowane (uwaga na wydajność, cache'owanie oryginalnych `QPixmap` lub regeneracja z `Pillow.Image` może być potrzebna).
      - **Rozważenie asynchronicznego ładowania miniatur, aby UI nie blokowało się przy dużej liczbie plików.** (Można odłożyć do Etapu 6/7 jeśli zbyt skomplikowane teraz, ale warto mieć na uwadze).
- **Nowe/Modyfikowane Pliki:**
  - `src/ui/widgets/file_tile_widget.py` (nowy)
  - `src/ui/widgets/__init__.py` (modyfikacja)
  - `src/ui/main_window.py` (znaczna modyfikacja)
- **Zależności:** Etap 1.B, Etap 2.A.
- **Wymagane Testy:**
  - **Manualne UI:**
    - Sprawdzenie, czy po wybraniu folderu kafelki są poprawnie wyświetlane (miniatura, nazwa, rozmiar).
    - Sprawdzenie, czy suwak skalowania jest widoczny i działa.
    - Sprawdzenie, czy zmiana wartości suwaka dynamicznie zmienia rozmiar kafelków/miniatur.
    - Test z folderem zawierającym obrazy, których nie da się wczytać (sprawdzić, czy wyświetlana jest domyślna/błędna miniatura).
    - Obserwacja responsywności UI podczas ładowania i skalowania.
- **Podsumowanie Testów:** `[ ] Do wykonania`
- **Dokumentacja:**
  - `[ ] Do uzupełnienia`: Docstringi dla klasy `FileTileWidget` i jej metod.
  - `[ ] Do uzupełnienia`: Aktualizacja docstringów i komentarzy w `main_window.py`.
  - `[ ] Do uzupełnienia`: Opis mechanizmu wyświetlania kafelków.
- **Potwierdzenie Zakończenia Etapu:** `[ ] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

**ZAKTUALIZUJ STATUS ZAKOŃCZONEGO ZADANIA!**
**PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU.**

---

### Etap 3.A: Logika Biznesowa - Otwieranie Archiwum, Tag "Ulubione", Zapis/Odczyt Metadanych (JSON)

- **Status:** `[ ] Oczekujący`
- **Cel Etapu:** Implementacja funkcji otwierania archiwum, dodanie atrybutu "ulubione" do `FilePair` oraz mechanizmu zapisu/odczytu metadanych (w tym "ulubione") do pliku JSON w folderze `.app_metadata`.
- **Wymagane Funkcjonalności:**
  1.  **`src/logic/file_operations.py` (nowy lub rozbudowa):**
      - Funkcja `open_archive_externally(archive_path)`:
        - Używa `os.startfile()` (Windows) lub `QDesktopServices.openUrl(QUrl.fromLocalFile(archive_path))` (multiplatformowe PyQt) do otwarcia pliku w domyślnym programie.
  2.  **`src/models/file_pair.py`**:
      - Dodanie atrybutu `is_favorite` (boolean, domyślnie `False`).
      - Metoda `toggle_favorite()` zmieniająca stan `is_favorite`.
  3.  **`src/logic/metadata_manager.py` (nowy):**
      - Stała `METADATA_DIR_NAME = ".app_metadata"`
      - Stała `METADATA_FILE_NAME = "metadata.json"`
      - Funkcja `get_metadata_path(working_directory)` zwracająca pełną ścieżkę do pliku `metadata.json`.
      - Funkcja `load_metadata(working_directory)`:
        - Sprawdza, czy folder `.app_metadata` i plik `metadata.json` istnieją w `working_directory`.
        - Jeśli tak, wczytuje dane z JSON.
        - Zwraca słownik z metadanymi (np. `{ "file_pairs": { "relative_archive_path": {"is_favorite": true, ...}}}`).
        - Obsługuje błędy (np. brak pliku, uszkodzony JSON - zwraca pusty słownik).
      - Funkcja `save_metadata(working_directory, file_pairs_list)`:
        - Tworzy folder `.app_metadata`, jeśli nie istnieje.
        - Przygotowuje dane do zapisu: słownik, gdzie kluczem jest _względna ścieżka pliku archiwum_ (względem `working_directory`), a wartością jest słownik atrybutów `FilePair` do zapisania (np. `is_favorite`, później gwiazdki, kolory). **Nie zapisujemy miniatur w JSON.**
        - Zapisuje dane do pliku `metadata.json` (używając techniki "zapisz do tymczasowego, potem zamień" dla bezpieczeństwa).
        - Ścieżki w JSON powinny być względne do folderu roboczego.
  4.  **`src/ui/main_window.py` (modyfikacja):**
      - Przy wyborze folderu roboczego, po zeskanowaniu plików, wywołaj `metadata_manager.load_metadata()` i zaktualizuj status `is_favorite` dla wczytanych obiektów `FilePair` na podstawie danych z JSON.
      - Kluczem do dopasowania `FilePair` do danych z JSON będzie względna ścieżka pliku archiwum.
- **Nowe/Modyfikowane Pliki:**
  - `src/logic/file_operations.py` (nowy/modyfikacja)
  - `src/models/file_pair.py` (modyfikacja)
  - `src/logic/metadata_manager.py` (nowy)
  - `src/ui/main_window.py` (modyfikacja)
  - `src/app_config.py` (może być potrzebne dodanie ścieżek relatywnych)
- **Zależności:** Etap 2.B, `DATA.md` (strategia JSON).
- **Wymagane Testy:**
  - **Jednostkowe (`tests/unit/test_file_operations.py`):**
    - Test dla `open_archive_externally` (trudny do pełnej automatyzacji, można sprawdzić, czy nie rzuca wyjątku dla istniejącego pliku).
  - **Jednostkowe (`tests/unit/test_file_pair.py`):**
    - Test dla `toggle_favorite()`.
  - **Jednostkowe (`tests/unit/test_metadata_manager.py`):**
    - Test `load_metadata` dla:
      - Nieistniejącego pliku metadanych.
      - Istniejącego, poprawnego pliku metadanych.
      - Pustego pliku metadanych.
      - Uszkodzonego pliku JSON.
    - Test `save_metadata`:
      - Zapis metadanych dla kilku `FilePair`. Sprawdzenie zawartości pliku JSON.
      - Sprawdzenie tworzenia folderu `.app_metadata`.
      - Sprawdzenie użycia ścieżek względnych.
    - Testy cyklu zapisz -> wczytaj -> sprawdź spójność.
- **Podsumowanie Testów:** `[ ] Do wykonania`
- **Dokumentacja:**
  - `[ ] Do uzupełnienia`: Docstringi dla nowych funkcji/metod w `file_operations.py`, `file_pair.py`, `metadata_manager.py`.
  - `[ ] Do uzupełnienia`: Opis formatu pliku `metadata.json`.
  - `[ ] Do uzupełnienia`: Opis mechanizmu zapisu/odczytu metadanych i synchronizacji z obiektami `FilePair`.
- **Potwierdzenie Zakończenia Etapu:** `[ ] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

**ZAKTUALIZUJ STATUS ZAKOŃCZONEGO ZADANIA!**
**PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU.**

---

### Etap 3.B: Interfejs Użytkownika - Interakcje z Kafelkami (Otwieranie, Duży Podgląd, Tagowanie "Ulubione")

- **Status:** `[ ] Oczekujący`
- **Cel Etapu:** Implementacja reakcji na kliknięcia na kafelku: otwarcie archiwum, wyświetlenie większego podglądu obrazu, dodanie ikony "Ulubione" i obsługa jej przełączania.
- **Wymagane Funkcjonalności:**
  1.  **`src/ui/widgets/file_tile_widget.py`**:
      - Dodanie przycisku/ikony "Ulubione" (np. `QPushButton` z ikoną gwiazdki).
      - Emisja niestandardowego sygnału np. `archive_open_requested(file_pair_object)` po kliknięciu na nazwę pliku.
      - Emisja niestandardowego sygnału np. `preview_image_requested(file_pair_object)` po kliknięciu na miniaturę.
      - Emisja niestandardowego sygnału np. `favorite_toggled(file_pair_object)` po kliknięciu przycisku "Ulubione".
      - Metoda `update_favorite_status(is_favorite)` do zmiany wyglądu ikony "Ulubione" (np. inna ikona, inny kolor tła).
  2.  **`src/ui/widgets/preview_dialog.py` (nowy):**
      - Stworzenie `QDialog` wyświetlającego większy obraz podglądu.
      - Przyjmuje `QPixmap` (lub ścieżkę do oryginalnego obrazu i ładuje go w pełnej rozdzielczości) i wyświetla go w `QLabel`.
      - Możliwość skalowania okna dialogowego wraz z obrazem.
  3.  **`src/ui/main_window.py`**:
      - Podczas tworzenia `FileTileWidget`, podłączanie jego sygnałów do odpowiednich slotów w `MainWindow`:
        - Slot dla `archive_open_requested`: wywołuje `file_operations.open_archive_externally()`.
        - Slot dla `preview_image_requested`:
          - Tworzy i wyświetla `PreviewDialog` z oryginalnym obrazem podglądu (nie miniaturą) z `file_pair.preview_path`.
        - Slot dla `favorite_toggled`:
          - Wywołuje `file_pair.toggle_favorite()`.
          - Aktualizuje wygląd ikony na kafelku (`file_tile_widget.update_favorite_status()`).
          - Wywołuje `metadata_manager.save_metadata()` aby zapisać zmianę.
      - Podczas inicjalizacji kafelka (lub jego aktualizacji), ustawienie odpowiedniego statusu ikony "Ulubione" na podstawie `file_pair.is_favorite`.
- **Nowe/Modyfikowane Pliki:**
  - `src/ui/widgets/file_tile_widget.py` (modyfikacja)
  - `src/ui/widgets/preview_dialog.py` (nowy)
  - `src/ui/main_window.py` (modyfikacja)
- **Zależności:** Etap 2.B, Etap 3.A.
- **Wymagane Testy:**
  - **Manualne UI:**
    - Kliknięcie nazwy pliku na kafelku powinno próbować otworzyć archiwum.
    - Kliknięcie miniatury na kafelku powinno otworzyć okno z większym podglądem. Sprawdzić jakość obrazu, skalowanie okna.
    - Kliknięcie ikony "Ulubione" powinno zmieniać jej wygląd i status `is_favorite` (sprawdzić, czy zmiana jest zapisywana i odczytywana po ponownym załadowaniu aplikacji/folderu).
    - Sprawdzenie, czy status "Ulubione" jest poprawnie wczytywany przy starcie.
- **Podsumowanie Testów:** `[ ] Do wykonania`
- **Dokumentacja:**
  - `[ ] Do uzupełnienia`: Docstringi dla `PreviewDialog` i nowych/zmodyfikowanych metod/sygnałów w `FileTileWidget` i `MainWindow`.
  - `[ ] Do uzupełnienia`: Opis interakcji użytkownika z kafelkami.
- **Potwierdzenie Zakończenia Etapu:** `[ ] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

**ZAKTUALIZUJ STATUS ZAKOŃCZONEGO ZADANIA!**
**PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU.**

---

### Etap 4.A: Logika Biznesowa - Zaawansowane Tagowanie i Logika Filtrowania

- **Status:** `[ ] Oczekujący`
- **Cel Etapu:** Rozbudowa `FilePair` o atrybuty dla gwiazdek i tagu kolorystycznego. Aktualizacja mechanizmu zapisu/odczytu metadanych. Implementacja logiki filtrowania listy `FilePair`.
- **Wymagane Funkcjonalności:**
  1.  **`src/models/file_pair.py`**:
      - Dodanie atrybutów:
        - `stars` (integer, np. 0-5, domyślnie 0).
        - `color_tag` (string, np. nazwa koloru lub kod hex, domyślnie `None` lub pusty string).
      - Metody `set_stars(num_stars)` i `set_color_tag(color)`.
  2.  **`src/logic/metadata_manager.py`**:
      - Modyfikacja `save_metadata()`:
        - Dołączanie `stars` i `color_tag` do danych zapisywanych w JSON dla każdej pary plików.
      - Modyfikacja `load_metadata()`:
        - Odczytywanie `stars` i `color_tag` z JSON i przypisywanie ich do odpowiednich obiektów `FilePair` podczas ładowania. Obsługa braku tych kluczy w starszych plikach metadanych (ustawianie wartości domyślnych).
  3.  **`src/logic/scanner.py` (lub nowy moduł np. `src/logic/filter_logic.py`):**
      - Funkcja `filter_file_pairs(file_pairs_list, filter_criteria)`:
        - `file_pairs_list`: lista wszystkich obiektów `FilePair`.
        - `filter_criteria`: słownik określający kryteria filtrowania, np.:
          ```python
          {
              "show_favorites_only": True, # boolean
              "min_stars": 3,             # integer 0-5, 0 oznacza brak filtra gwiazdek
              "required_color_tag": "red" # string, None lub pusty oznacza brak filtra koloru
          }
          ```
        - Zwraca nową listę obiektów `FilePair` spełniających kryteria.
        - Logika powinna obsługiwać kombinacje filtrów (AND).
- **Nowe/Modyfikowane Pliki:**
  - `src/models/file_pair.py` (modyfikacja)
  - `src/logic/metadata_manager.py` (modyfikacja)
  - `src/logic/scanner.py` (modyfikacja) lub `src/logic/filter_logic.py` (nowy)
- **Zależności:** Etap 3.A.
- **Wymagane Testy:**
  - **Jednostkowe (`tests/unit/test_file_pair.py`):**
    - Testy dla `set_stars()` i `set_color_tag()`.
  - **Jednostkowe (`tests/unit/test_metadata_manager.py`):**
    - Testy zapisu/odczytu metadanych z nowymi polami (`stars`, `color_tag`).
    - Testy kompatybilności wstecznej (ładowanie metadanych bez nowych pól).
  - **Jednostkowe (`tests/unit/test_filter_logic.py` lub `test_scanner.py`):**
    - Testy dla `filter_file_pairs` z różnymi kombinacjami kryteriów:
      - Tylko ulubione.
      - Minimalna liczba gwiazdek.
      - Określony kolor.
      - Kombinacje (np. ulubione z >= 4 gwiazdkami i czerwonym tagiem).
      - Brak kryteriów (powinien zwrócić wszystkie pary).
- **Podsumowanie Testów:** `[ ] Do wykonania`
- **Dokumentacja:**
  - `[ ] Do uzupełnienia`: Aktualizacja docstringów w `FilePair` i `MetadataManager`.
  - `[ ] Do uzupełnienia`: Dokumentacja funkcji `filter_file_pairs` i formatu `filter_criteria`.
- **Potwierdzenie Zakończenia Etapu:** `[ ] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

**ZAKTUALIZUJ STATUS ZAKOŃCZONEGO ZADANIA!**

## **PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU.**

### Etap 4.B: Interfejs Użytkownika - Kontrolki Tagowania i Panel Filtrowania

- **Status:** `[ ] Oczekujący`
- **Cel Etapu:** Dodanie kontrolek na kafelkach lub w menu kontekstowym do przypisywania gwiazdek i kolorów. Dodanie panelu filtrowania i aktualizacja widoku kafelków w odpowiedzi na zmiany filtrów.
- **Wymagane Funkcjonalności:**
  1.  **`src/ui/widgets/file_tile_widget.py`**:
      - Dodanie elementów UI do ustawiania gwiazdek (np. 5 klikalnych `QPushButton` z ikonami gwiazdek pustych/pełnych, lub bardziej zaawansowany widget).
      - Dodanie elementu UI do wyboru koloru etykiety (np. `QPushButton` otwierający `QColorDialog`, lub menu z predefiniowaną paletą kolorów).
      - Emisja sygnałów np. `stars_changed(file_pair_object, new_star_count)` i `color_tag_changed(file_pair_object, new_color_tag)`.
      - Wizualne odzwierciedlenie ustawionych gwiazdek i koloru na kafelku (np. tło, ramka, ikona).
      - Metody `update_stars_display(star_count)` i `update_color_tag_display(color_tag)`.
  2.  **`src/ui/main_window.py`**:
      - Dodanie panelu filtrowania (np. `QGroupBox` lub `QDockWidget`) zawierającego:
        - `QCheckBox` "Pokaż tylko ulubione".
        - Widget do wyboru minimalnej liczby gwiazdek (np. `QComboBox` 0-5 lub `QSpinBox`).
        - Widget do wyboru koloru etykiety do filtrowania (np. `QComboBox` z predefiniowanymi kolorami i opcją "Wszystkie").
      - Sloty podłączone do sygnałów `stars_changed` i `color_tag_changed` z `FileTileWidget`:
        - Aktualizują odpowiednie atrybuty w obiekcie `FilePair`.
        - Wywołują `metadata_manager.save_metadata()`.
        - Aktualizują wygląd kafelka.
      - Slot podłączony do zmian w panelu filtrowania:
        - Zbiera aktualne kryteria filtrowania.
        - Wywołuje `logic.filter_file_pairs()` na pełnej liście wczytanych `FilePair`.
        - Czyści i ponownie zapełnia obszar kafelków tylko tymi, które pasują do filtrów.
      - Przy inicjalizacji/aktualizacji kafelków, ustawienie ich wyglądu (gwiazdki, kolor) na podstawie danych z `FilePair`.
- **Nowe/Modyfikowane Pliki:**
  - `src/ui/widgets/file_tile_widget.py` (modyfikacja)
  - `src/ui/main_window.py` (modyfikacja)
- **Zależności:** Etap 3.B, Etap 4.A.
- **Wymagane Testy:**
  - **Manualne UI:**
    - Sprawdzenie, czy można ustawiać gwiazdki i kolory na kafelkach.
    - Sprawdzenie, czy zmiany są wizualnie odzwierciedlane na kafelkach.
    - Sprawdzenie, czy zmiany tagów są zapisywane i poprawnie odczytywane po restarcie.
    - Sprawdzenie działania panelu filtrowania:
      - Filtrowanie po ulubionych.
      - Filtrowanie po gwiazdkach.
      - Filtrowanie po kolorach.
      - Kombinacje filtrów.
      - Resetowanie filtrów (powinno pokazać wszystkie kafelki).
    - Sprawdzenie, czy widok kafelków aktualizuje się poprawnie po zmianie filtrów.
- **Podsumowanie Testów:** `[ ] Do wykonania`
- **Dokumentacja:**
  - `[ ] Do uzupełnienia`: Aktualizacja dokumentacji `FileTileWidget` i `MainWindow`.
  - `[ ] Do uzupełnienia`: Opis działania panelu filtrowania i kontrolek tagowania.
- **Potwierdzenie Zakończenia Etapu:** `[ ] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

**ZAKTUALIZUJ STATUS ZAKOŃCZONEGO ZADANIA!**

## **PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU.**

### Etap 5.A: Logika Biznesowa - Operacje na Plikach i Folderach

- **Status:** `[ ] Oczekujący`
- **Cel Etapu:** Rozbudowa `FilePair` o metody do zmiany nazwy, usuwania, przenoszenia. Implementacja funkcji do tworzenia, usuwania i zmiany nazwy folderów.
- **Wymagane Funkcjonalności:**
  1.  **`src/models/file_pair.py`**:
      - Metoda `rename(new_base_name, working_directory)`:
        - Zmienia nazwę pliku archiwum i pliku podglądu, zachowując ich oryginalne rozszerzenia.
        - Aktualizuje wewnętrzne ścieżki (`self.archive_path`, `self.preview_path`).
        - Używa `os.rename`. Wymaga ostrożności przy aktualizacji ścieżek, zwłaszcza jeśli są względne.
        - Zwraca `True` w przypadku sukcesu, `False` w przypadku błędu (i loguje błąd).
      - Metoda `delete()`:
        - Usuwa plik archiwum i plik podglądu.
        - Używa `os.remove`.
        - Zwraca `True` w przypadku sukcesu (obu usunięć), `False` w przypadku błędu.
      - Metoda `move(new_directory_path, working_directory)`:
        - Przenosi plik archiwum i plik podglądu do `new_directory_path` (ścieżka absolutna lub względna do `working_directory`).
        - Aktualizuje wewnętrzne ścieżki.
        - Używa `shutil.move`.
        - Zwraca `True` w przypadku sukcesu, `False` w przypadku błędu.
  2.  **`src/logic/file_operations.py`**:
      - Funkcja `create_folder(parent_directory, folder_name)`:
        - Tworzy nowy folder. Używa `os.makedirs(exist_ok=True)`.
      - Funkcja `rename_folder(folder_path, new_folder_name)`:
        - Zmienia nazwę folderu. Używa `os.rename`.
      - Funkcja `delete_folder(folder_path)`:
        - Usuwa folder (i jego zawartość, jeśli to wymagane - `shutil.rmtree`). **Ostrożnie z tą funkcją! Wymaga potwierdzenia od użytkownika w UI.**
- **Nowe/Modyfikowane Pliki:**
  - `src/models/file_pair.py` (modyfikacja)
  - `src/logic/file_operations.py` (modyfikacja)
- **Zależności:** Etap 0. Wymaga `shutil`.
- **Wymagane Testy:**
  - **Jednostkowe (`tests/unit/test_file_pair.py`):**
    - Test dla `rename()`: sprawdzenie zmiany nazw obu plików, aktualizacji ścieżek. Test z konfliktami nazw.
    - Test dla `delete()`: sprawdzenie usunięcia obu plików. Test z nieistniejącymi plikami.
    - Test dla `move()`: sprawdzenie przeniesienia obu plików, aktualizacji ścieżek. Test przenoszenia do nieistniejącego folderu (czy tworzy?).
  - **Jednostkowe (`tests/unit/test_file_operations.py`):**
    - Test dla `create_folder`.
    - Test dla `rename_folder`.
    - Test dla `delete_folder` (na folderze testowym, nie produkcyjnym!).
- **Podsumowanie Testów:** `[ ] Do wykonania`
- **Dokumentacja:**
  - `[ ] Do uzupełnienia`: Szczegółowe docstringi dla nowych metod w `FilePair` i funkcji w `file_operations.py`.
  - `[ ] Do uzupełnienia`: Opis obsługi błędów i potencjalnych problemów (np. uprawnienia).
- **Potwierdzenie Zakończenia Etapu:** `[ ] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

**ZAKTUALIZUJ STATUS ZAKOŃCZONEGO ZADANIA!**

## **PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU.**

### Etap 5.B: Interfejs Użytkownika - Widok Drzewa Katalogów, Drag & Drop, Operacje Plikowe

- **Status:** `[ ] Oczekujący`
- **Cel Etapu:** Dodanie widoku drzewa katalogów, implementacja D&D dla Par Plików do folderów w drzewie, oraz opcji w menu kontekstowym do operacji na plikach/folderach.
- **Wymagane Funkcjonalności:**
  1.  **`src/ui/main_window.py`**:
      - Dodanie `QTreeView` do UI.
      - Użycie `QFileSystemModel` do wyświetlenia struktury folderu roboczego w `QTreeView`.
        - Ustawienie `setRootPath()` dla `QFileSystemModel` na wybrany folder roboczy.
        - Filtrowanie, aby pokazywać tylko foldery (opcjonalnie).
      - Implementacja Drag & Drop:
        - Kafelki (`FileTileWidget`) powinny być źródłem przeciągania (`QDrag`).
        - `QTreeView` (lub jego elementy folderów) powinny akceptować upuszczanie (`acceptDrops = True`, reimplementacja `dragEnterEvent`, `dragMoveEvent`, `dropEvent`).
        - Podczas upuszczania kafelka na folder w drzewie:
          - Pobierz obiekt `FilePair` powiązany z przeciąganym kafelkiem.
          - Pobierz ścieżkę do folderu docelowego z `QTreeView`.
          - Wywołaj metodę `file_pair.move(target_folder_path, self.working_directory)`.
          - Jeśli operacja się powiedzie, usuń kafelek z jego oryginalnego miejsca i zaktualizuj `metadata_manager.save_metadata()` (bo ścieżki się zmieniły, więc klucze w JSON też). Odśwież widok kafelków (lub przynajmniej usuń stary).
          - **Uwaga:** Zmiana ścieżek w `FilePair` i metadanych jest kluczowa.
      - Dodanie menu kontekstowego (`contextMenuPolicy`, `customContextMenuRequested`):
        - Dla `QTreeView` (na elementach folderów):
          - Opcje: "Nowy Folder", "Zmień Nazwę", "Usuń Folder" (z potwierdzeniem!).
          - Wywołanie odpowiednich funkcji z `logic.file_operations.py`. Po operacji odśwież model `QFileSystemModel`.
        - Dla `FileTileWidget` (lub obszaru kafelków):
          - Opcje: "Zmień Nazwę Pary", "Usuń Parę" (z potwierdzeniem!).
          - Wywołanie odpowiednich metod z obiektu `FilePair`. Po operacji usuń kafelek i zaktualizuj metadane.
      - Implementacja dialogów do wprowadzania nowej nazwy (np. `QInputDialog`).
      - Aktualizacja metadanych po każdej operacji modyfikującej pliki/foldery.
- **Nowe/Modyfikowane Pliki:**
  - `src/ui/main_window.py` (znaczna modyfikacja)
  - `src/ui/widgets/file_tile_widget.py` (dodanie obsługi D&D jako źródła)
- **Zależności:** Etap 4.B, Etap 5.A.
- **Wymagane Testy:**
  - **Manualne UI:**
    - Sprawdzenie, czy drzewo katalogów poprawnie wyświetla strukturę folderu roboczego.
    - Testowanie D&D:
      - Przeciąganie kafelka na folder w drzewie – sprawdzenie, czy pliki są przenoszone i kafelek znika/aktualizuje się. Sprawdzić, czy metadane są aktualizowane.
    - Testowanie menu kontekstowego dla folderów:
      - Tworzenie folderu.
      - Zmiana nazwy folderu.
      - Usuwanie folderu (z potwierdzeniem i bez).
    - Testowanie menu kontekstowego dla kafelków:
      - Zmiana nazwy pary plików.
      - Usuwanie pary plików (z potwierdzeniem i bez).
    - Sprawdzenie, czy wszystkie operacje poprawnie aktualizują system plików, widok UI i metadane (JSON).
- **Podsumowanie Testów:** `[ ] Do wykonania`
- **Dokumentacja:**
  - `[ ] Do uzupełnienia`: Opis implementacji drzewa katalogów, D&D, menu kontekstowych.
  - `[ ] Do uzupełnienia`: Szczegóły dotyczące aktualizacji metadanych po operacjach plikowych.
- **Potwierdzenie Zakończenia Etapu:** `[ ] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

**ZAKTUALIZUJ STATUS ZAKOŃCZONEGO ZADANIA!**

## **PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU.**

### Etap 6.A: Logika Biznesowa - Obsługa Plików Niesparowanych, Ręczne Parowanie

- **Status:** `[ ] Oczekujący`
- **Cel Etapu:** Modyfikacja skanowania folderu w celu identyfikacji plików niesparowanych. Implementacja mechanizmu ręcznego parowania. Wstępna analiza wydajności.
- **Wymagane Funkcjonalności:**
  1.  **`src/logic/scanner.py`**:
      - Modyfikacja `scan_folder_for_pairs` (lub nowa funkcja `scan_folder_detailed`):
        - Oprócz listy sparowanych `FilePair`, powinna zwracać dwie dodatkowe listy:
          - Listę ścieżek do plików archiwów, które nie mają pasującego podglądu.
          - Listę ścieżek do plików podglądów, które nie mają pasującego archiwum.
  2.  **`src/logic/metadata_manager.py`**:
      - Modyfikacja `save_metadata()` i `load_metadata()` aby obsługiwały zapis i odczyt list plików niesparowanych w pliku `metadata.json` (np. pod kluczami `unpaired_archives` i `unpaired_previews`). Zgodnie z `DATA.md`.
  3.  **`src/logic/file_operations.py` (lub `scanner.py`):**
      - Funkcja `manually_pair_files(archive_path, preview_path, working_directory)`:
        - Przyjmuje ścieżki do wybranego archiwum i podglądu.
        - Sprawdza, czy mają różne nazwy bazowe. Jeśli tak, może zapytać użytkownika, którą nazwę zachować, lub automatycznie zmienić nazwę jednego z plików (np. podglądu), aby pasowała do archiwum. (Decyzja projektowa: na razie załóżmy, że podgląd dostosowuje nazwę do archiwum).
        - Jeśli konieczna jest zmiana nazwy, używa `os.rename`.
        - Tworzy i zwraca nowy obiekt `FilePair`.
        - Usuwa pliki z list niesparowanych w metadanych.
  4.  **Analiza wydajności (teoretyczna na tym etapie):**
      - Zidentyfikować potencjalne wąskie gardła: skanowanie dużych folderów, ładowanie wielu miniatur, operacje na JSON dla tysięcy wpisów.
- **Nowe/Modyfikowane Pliki:**
  - `src/logic/scanner.py` (modyfikacja)
  - `src/logic/metadata_manager.py` (modyfikacja)
  - `src/logic/file_operations.py` (modyfikacja lub `scanner.py`)
- **Zależności:** Etap 1.A, Etap 3.A.
- **Wymagane Testy:**
  - **Jednostkowe (`tests/unit/test_scanner.py`):**
    - Test dla zmodyfikowanej funkcji skanującej, sprawdzający poprawność zwracanych list plików niesparowanych dla różnych scenariuszy.
  - **Jednostkowe (`tests/unit/test_metadata_manager.py`):**
    - Test zapisu/odczytu list plików niesparowanych w JSON.
  - **Jednostkowe (`tests/unit/test_file_operations.py` lub `test_scanner.py`):**
    - Test dla `manually_pair_files`:
      - Parowanie plików o tej samej nazwie bazowej.
      - Parowanie plików o różnych nazwach bazowych (sprawdzenie zmiany nazwy).
      - Sprawdzenie, czy zwracany jest poprawny obiekt `FilePair`.
- **Podsumowanie Testów:** `[ ] Do wykonania`
- **Dokumentacja:**
  - `[ ] Do uzupełnienia`: Aktualizacja dokumentacji `scanner.py` i `metadata_manager.py`.
  - `[ ] Do uzupełnienia`: Opis logiki ręcznego parowania i obsługi zmiany nazw.
  - `[ ] Do uzupełnienia`: Notatki z analizy potencjalnych problemów wydajnościowych.
- **Potwierdzenie Zakończenia Etapu:** `[ ] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

**ZAKTUALIZUJ STATUS ZAKOŃCZONEGO ZADANIA!**

## **PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU.**

### Etap 6.B: Interfejs Użytkownika - Wyświetlanie Niesparowanych, Ręczne Parowanie

- **Status:** `[ ] Oczekujący`
- **Cel Etapu:** Dodanie widoku/listy plików niesparowanych oraz interfejsu do ich ręcznego parowania.
- **Wymagane Funkcjonalności:**
  1.  **`src/ui/main_window.py`**:
      - Dodanie nowego obszaru w UI (np. osobna zakładka `QTabWidget`, lub dedykowany `QDockWidget`) do wyświetlania plików niesparowanych.
      - W tym obszarze, dwie listy (`QListWidget`): jedna dla niesparowanych archiwów, druga dla niesparowanych podglądów.
      - Po zeskanowaniu folderu (i załadowaniu metadanych), zapełnienie tych list odpowiednimi ścieżkami plików.
      - Dodanie przycisku "Sparuj Wybrane".
      - Logika przycisku "Sparuj Wybrane":
        - Sprawdza, czy dokładnie jeden element jest wybrany na liście archiwów i jeden na liście podglądów.
        - Jeśli tak, pobiera ich ścieżki.
        - Wywołuje `logic.manually_pair_files()`.
        - Jeśli parowanie się powiedzie:
          - Dodaje nowy kafelek dla nowo utworzonej pary do głównego widoku.
          - Usuwa sparowane pliki z list niesparowanych (w UI i w metadanych poprzez `MetadataManager`).
          - Zapisuje zaktualizowane metadane (w tym usunięte pliki niesparowane i dodaną nową parę, jeśli jej jeszcze nie było).
        - Wyświetla komunikat o sukcesie lub błędzie.
- **Nowe/Modyfikowane Pliki:**
  - `src/ui/main_window.py` (znaczna modyfikacja)
- **Zależności:** Etap 5.B, Etap 6.A.
- **Wymagane Testy:**
  - **Manualne UI:**
    - Sprawdzenie, czy listy niesparowanych plików są poprawnie wypełniane po wybraniu folderu testowego.
    - Testowanie funkcji ręcznego parowania:
      - Wybranie archiwum i podglądu, kliknięcie "Sparuj".
      - Sprawdzenie, czy nowy kafelek pojawia się w głównym widoku.
      - Sprawdzenie, czy pliki znikają z list niesparowanych.
      - Sprawdzenie, czy metadane są poprawnie aktualizowane (w tym `metadata.json`).
      - Testowanie przypadków brzegowych (np. nic nie wybrane, wybrane dwa archiwa itp.).
- **Podsumowanie Testów:** `[ ] Do wykonania`
- **Dokumentacja:**
  - `[ ] Do uzupełnienia`: Aktualizacja dokumentacji `MainWindow` o nowy panel i logikę ręcznego parowania.
- **Potwierdzenie Zakończenia Etapu:** `[ ] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

**ZAKTUALIZUJ STATUS ZAKOŃCZONEGO ZADANIA!**

## **PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU.**

### Etap 7: Refaktoryzacja, Optymalizacja i Finalizacja

- **Status:** `[ ] Oczekujący`
- **Cel Etapu:** Przegląd i poprawa jakości kodu, dalsza optymalizacja wydajności, finalne testy i przygotowanie aplikacji. Ten etap jest bardziej holistyczny i może wymagać iteracji.
- **Podetapy i Wymagane Funkcjonalności:**

  **7.A: Refaktoryzacja Kodu**

  - Przegląd całego kodu pod kątem:
    - Czytelności, spójności nazw.
    - Modularności (ścisłe oddzielenie UI od logiki, SRP dla klas/funkcji).
    - Eliminacji powtórzeń kodu (DRY).
    - Poprawności obsługi błędów i wyjątków.
    - Zgodności z PEP 8.
  - Użycie narzędzi do analizy statycznej (np. `flake8`, `pylint`).

  **7.B: Optymalizacja Wydajności**

  - Na podstawie analizy z Etapu 6.A i obserwacji:
    - **Asynchroniczne ładowanie miniatur:** Jeśli ładowanie kafelków jest wolne, zaimplementować ładowanie miniatur w tle (np. przy użyciu `QThreadPool` lub `QtConcurrent`), aby nie blokować UI. Miniatury mogą pojawiać się stopniowo.
    - **Cache'owanie miniaturek na dysku:**
      - W folderze `.app_metadata/thumbnails/` (zgodnie z `DATA.md`).
      - `FilePair` może przechowywać ścieżkę do zcache'owanej miniatury.
      - `load_preview_thumbnail` najpierw sprawdza cache, potem generuje i zapisuje do cache'u.
      - Nazewnictwo plików cache: np. hash ścieżki oryginalnego podglądu + rozmiar.
    - **Optymalizacja skanowania folderów:** Jeśli jest wolne, rozważyć bardziej efektywne metody listowania plików lub indeksowanie w tle.
    - **Przejście na SQLite dla metadanych (jeśli JSON jest wąskim gardłem):**
      - Zgodnie z rekomendacją w `DATA.md`.
      - Implementacja nowej wersji `MetadataManager` używającej `sqlite3`.
      - Definicja schematu bazy danych (`file_pairs`, `unpaired_files`).
      - Utworzenie skryptu/funkcji do migracji danych z `metadata.json` do `metadata.sqlite`.
      - Użycie transakcji dla operacji zapisu.
      - Indeksowanie odpowiednich kolumn (`archive_path`, tagi).
    - Profilowanie aplikacji (np. `cProfile`, `py-spy`) w celu znalezienia konkretnych wąskich gardeł.

  **7.C: Finalne Testowanie**

  - Kompleksowe testy regresji (manualne i automatyczne, jeśli istnieją).
  - Testy wydajnościowe na bardzo dużych folderach (np. >1TB, dziesiątki tysięcy plików - można symulować strukturę z mniejszą liczbą rzeczywistych danych, ale dużą liczbą wpisów). Mierzenie czasu:
    - Pierwszego skanowania folderu.
    - Kolejnego otwarcia aplikacji z tym samym folderem (ładowanie metadanych i cache'u).
    - Filtrowania.
    - Operacji plikowych.
  - Testy użyteczności (manualne, być może z udziałem potencjalnych użytkowników).
  - Testy na różnych konfiguracjach (jeśli możliwe, np. różne wersje Windows).

  **7.D: Finalizacja Dokumentacji**

  - Przegląd i uzupełnienie wszystkich komentarzy w kodzie i docstringów.
  - Finalizacja `README.md` (pełna instrukcja instalacji, konfiguracji, użytkowania, znane problemy).
  - Przygotowanie dokumentacji architektury (jeśli nie została w pełni pokryta w `README` lub komentarzach).
  - Rozważenie przygotowania prostego przewodnika użytkownika (np. lista kluczowych funkcji).

- **Nowe/Modyfikowane Pliki:** Potencjalnie wszystkie pliki w `src/`. Nowy skrypt migracji danych (jeśli SQLite).
- **Zależności:** Wszystkie poprzednie etapy.
- **Wymagane Testy:** Jak opisano w 7.C.
- **Podsumowanie Testów:** `[ ] Do wykonania`
- **Dokumentacja:**
  - `[ ] Do uzupełnienia`: Wszystkie aspekty dokumentacji projektu.
- **Potwierdzenie Zakończenia Etapu:** `[ ] Potwierdzam zakończenie etapu. Można przejść dalej.`

---

## **PROSZĘ CZEKAĆ NA POTWIERDZENIE ZANIM PRZEJDZIESZ DO NASTĘPNEGO ETAPU (ZAKOŃCZENIE PROJEKTU W RAMACH TEGO PLANU).**
