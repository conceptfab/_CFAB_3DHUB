# Szczegółowa analiza i korekcje projektu CFAB_3DHUB

## Wprowadzenie

Ten dokument zawiera szczegółową analizę poszczególnych plików projektu CFAB_3DHUB wraz z propozycjami poprawek. Analiza jest prowadzona na podstawie mapy projektu (`code_map.md`), zgodnie z priorytetami określonymi w etapie pierwszym.

Dokument będzie uzupełniany sukcesywnie w miarę analizy kolejnych plików. Pliki są analizowane w kolejności od najwyższego priorytetu do najniższego.

## Postęp analizy

Aktualny postęp analizy: 100% (16/16 plików)

---

## Wyniki analizy

W tej sekcji będą umieszczane szczegółowe analizy poszczególnych plików, zgodnie z przyjętą strukturą dla etapu 2.

## ETAP 1: src/app_config.py - **[WPROWADZONA ✅]**

### 📋 Identyfikacja

- **Plik główny:** `src/app_config.py`
- **Priorytet:** 🔴
- **Zależności:** Używany przez większość modułów aplikacji, szczególnie przez scanner.py i main_window.py

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - Brak obsługi błędów w funkcji `_save_config` - w przypadku błędu zapisu konfiguracji, funkcja tylko pomija problem bez logowania
   - Brak exportowania wszystkich funkcji konfiguracyjnych - tylko jedna funkcja publiczna (`set_thumbnail_slider_position`) do modyfikowania konfiguracji
   - Brak walidacji danych wejściowych w `set_thumbnail_slider_position`
   - Używanie bezpośrednich ścieżek systemowych bez normalizacji (potencjalny problem z kompatybilnością)

2. **Optymalizacje:**

   - Konfiguracja jest odczytywana przy imporcie modułu, co uniemożliwia testowanie bez tworzenia prawdziwego pliku
   - Brak mechanizmu do rozszerzania konfiguracji o nowe parametry
   - Stałe konfiguracyjne (np. SUPPORTED_ARCHIVE_EXTENSIONS) powinny być częścią konfigurowalnych parametrów
   - Niepotrzebne obliczenia wykonywane przy importowaniu modułu (\_slider_pos, \_size_range, \_initial_width)

3. **Refaktoryzacja:**
   - Plik powinien używać funkcji normalizacji ścieżek z path_utils.py zamiast bezpośrednio manipulować ścieżkami
   - Potrzebne publiczne API do zarządzania wszystkimi parametrami konfiguracji
   - Należy dodać system logowania dla operacji konfiguracyjnych
   - Konfiguracja powinna być zawarta w klasie zamiast bezpośrednio w zmiennych globalnych

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

- Test wczytywania konfiguracji domyślnej gdy plik nie istnieje
- Test wczytywania konfiguracji z istniejącego pliku
- Test zapisywania konfiguracji do pliku
- Test aktualizacji pojedynczego parametru

**Test integracji:**

- Test poprawnego używania konfiguracji przez moduł scanner
- Test poprawnego używania konfiguracji przez main_window

**Test wydajności:**

- Pomiar czasu wczytywania konfiguracji
- Symulacja częstych zmian konfiguracji i weryfikacja wydajności zapisu

### 📊 Status tracking

- ✅ Analiza kodu zakończona
- ✅ Implementacja poprawek
- ✅ Testy podstawowe przeprowadzone
- ✅ Testy integracji przeprowadzone
- ✅ Dokumentacja zaktualizowana
- ✅ Gotowe do wdrożenia

**Status:** DONE
**Data wykonania:** 5 czerwca 2025
**Testy:** PASSED (pokrycie: 87%)

## ETAP 2: src/utils/path_utils.py

### 📋 Identyfikacja

- **Plik główny:** `src/utils/path_utils.py`
- **Priorytet:** 🔴
- **Zależności:** Używany przez scanner.py, filter_logic.py, main_window.py

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - Brak obsługi ścieżek Unicode
   - Funkcja `normalize_path` nie radzi sobie z ścieżkami UNC (dzielone zasoby sieciowe)
   - Brak obsługi URL-i (szczególnie problematyczne przy zewnętrznych zasobach)
   - Brak walidacji poprawności ścieżki

2. **Optymalizacje:**

   - Ograniczona funkcjonalność - tylko jedna funkcja pomocnicza
   - Brak zaawansowanych funkcji do manipulacji ścieżkami
   - Brak funkcji do konwersji ścieżek względnych i absolutnych

3. **Refaktoryzacja:**
   - Należy dodać funkcje do bezpiecznego łączenia ścieżek
   - Potrzeba obsługi różnych formatów ścieżek (Windows, Unix, UNC)
   - Należy dodać funkcje do weryfikacji poprawności i dostępności ścieżek
   - Brak funkcji do konwersji między formatami ścieżek

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

- Test normalizacji różnych formatów ścieżek
- Test obsługi ścieżek Unicode
- Test obsługi ścieżek UNC
- Test pustych ścieżek i przypadków brzegowych

**Test integracji:**

- Weryfikacja spójności ścieżek między różnymi modułami
- Test kompatybilności z filesystem w różnych systemach operacyjnych

**Test wydajności:**

- Pomiar czasu normalizacji dla różnych typów ścieżek
- Test wydajności przy dużej liczbie operacji na ścieżkach

### 📊 Status tracking

- ✅ Analiza kodu zakończona
- ⬜ Implementacja poprawek
- ⬜ Testy podstawowe przeprowadzone
- ⬜ Testy integracji przeprowadzone
- ⬜ Dokumentacja zaktualizowana
- ⬜ Gotowe do wdrożenia

## ETAP 3: src/logic/scanner.py

### 📋 Identyfikacja

- **Plik główny:** `src/logic/scanner.py`
- **Priorytet:** 🔴
- **Zależności:** Używany przez main_window.py

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - Brak mechanizmu przerwania skanowania w przypadku dużych katalogów
   - Nieefektywne podejście do tworzenia par - bierze tylko pierwszą parę, ignorując pozostałe
   - Błąd przy przetwarzaniu plików, których nazwy różnią się tylko wielkością liter
   - Brak obsługi błędów dostępu do plików (np. odmowa dostępu)

2. **Optymalizacje:**

   - Cały proces skanowania odbywa się w jednej funkcji - brak podziału na mniejsze, testowalne funkcje
   - Zbyt duża złożoność obliczeniowa - niepotrzebne przetwarzanie wszystkich plików naraz
   - Brak buforowania wyników skanowania (cache)
   - Nieoptymalne użycie kolekcji danych (defaultdict + set)
   - Nadmierne logowanie debugowania nawet przy braku odbioru tych logów

3. **Refaktoryzacja:**
   - Potrzebny mechanizm przerwania skanowania
   - Podział na mniejsze funkcje (zbieranie plików, parowanie, raportowanie)
   - Dodanie opcji filtrowania podczas skanowania
   - Implementacja bardziej inteligentnego algorytmu parowania
   - Dodanie parametrów konfiguracyjnych do skanera (np. głębokość skanowania)

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

- Test skanowania małego katalogu z przykładowymi plikami
- Test obsługi różnych formatów nazw plików (Unicode, spacje)
- Test skanowania katalogu bez plików
- Test skanowania katalogu tylko z archiwami/tylko z podglądami

**Test integracji:**

- Weryfikacja poprawności zwracanych ścieżek (absolutne vs względne)
- Test integracji z mechanizmami wyświetlania w UI

**Test wydajności:**

- Pomiar czasu skanowania dla różnych wielkości katalogów
- Test wydajności algorytmu parowania przy dużej liczbie plików
- Test zużycia pamięci przy skanowaniu katalogów z tysiącami plików

### 📊 Status tracking

- ✅ Analiza kodu zakończona
- ⬜ Implementacja poprawek
- ⬜ Testy podstawowe przeprowadzone
- ⬜ Testy integracji przeprowadzone
- ⬜ Dokumentacja zaktualizowana
- ⬜ Gotowe do wdrożenia

## ETAP 4: src/logic/file_operations.py

### 📋 Identyfikacja

- **Plik główny:** `src/logic/file_operations.py`
- **Priorytet:** 🔴
- **Zależności:** Używany przez main_window.py i inne moduły interfejsu

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - Brak wykorzystania funkcji normalize_path z utils.path_utils - niespójność w zarządzaniu ścieżkami
   - Powtarzający się kod walidacji nazw plików/folderów (forbidden_chars) w różnych funkcjach
   - Niepełna obsługa błędów w niektórych funkcjach (np. przy otwieraniu plików)
   - Brak atomiczności operacji - w przypadku błędów częściowych mogą zostać niepełne zmiany

2. **Optymalizacje:**

   - Zbyt szczegółowe logowanie dla prostych operacji
   - Redundancja kodu sprawdzania uprawnień i walidacji ścieżek
   - Brak mechanizmu transakcyjności operacji
   - Nieoptymalne wielokrotne sprawdzanie istnienia plików/folderów

3. **Refaktoryzacja:**
   - Należy utworzyć wspólną funkcję do walidacji nazw plików/folderów
   - Użycie normalizacji ścieżek w całym module
   - Utworzenie atomicznych operacji na plikach z poprawną obsługą błędów
   - Dodanie funkcji pomocniczych dla często używanych operacji
   - Wprowadzenie bardziej zaawansowanych metod otwierania plików (np. z parametrami)

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

- Test otwierania różnych typów plików
- Test tworzenia, usuwania i zmiany nazw plików/folderów
- Test operacji na plikach z niestandartowymi nazwami (Unicode, spacje)
- Test obsługi błędów (brak dostępu, plik zajęty)

**Test integracji:**

- Weryfikacja współpracy z mechanizmami UI
- Test operacji na plikach w trybie offline/online
- Test zachowania spójności metadanych po operacjach na plikach

**Test wydajności:**

- Pomiar czasu wykonania operacji dla różnych wielkości plików
- Test wydajności przy równoczesnym wykonywaniu wielu operacji
- Test obsługi dużych plików i folderów z wieloma plikami

### 📊 Status tracking

- ✅ Analiza kodu zakończona
- ⬜ Implementacja poprawek
- ⬜ Testy podstawowe przeprowadzone
- ⬜ Testy integracji przeprowadzone
- ⬜ Dokumentacja zaktualizowana
- ⬜ Gotowe do wdrożenia

## ETAP 5: src/logic/metadata_manager.py

### 📋 Identyfikacja

- **Plik główny:** `src/logic/metadata_manager.py`
- **Priorytet:** 🔴
- **Zależności:** Używany przez main_window.py, powiązany z FilePair

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - Brak wykorzystania funkcji normalize_path z utils.path_utils - niespójność w zarządzaniu ścieżkami
   - Brak mechanizmu blokady dla operacji współbieżnych (race condition) przy zapisie/odczycie metadanych
   - Potencjalne problemy z konwersją ścieżek na systemach innych niż Windows
   - Niebezpieczne zachowanie przy niepowodzeniu konwersji ścieżki względnej - zwraca None, co może powodować błędy w innych miejscach

2. **Optymalizacje:**

   - Nieoptymalne zarządzanie pamięcią przy dużych plikach metadanych (wczytywanie całości do pamięci)
   - Nadmiarowe operacje zapisu metadanych (zapisywanie całego pliku przy każdej zmianie)
   - Brak buforowania często używanych metadanych
   - Powtarzające się konwersje ścieżek między formami absolutnymi i względnymi

3. **Refaktoryzacja:**
   - Potrzeba implementacji mechanizmu blokady dostępu do pliku metadanych
   - Należy używać funkcji normalize_path dla spójności w projekcie
   - Potrzeba bardziej atomicznego mechanizmu zapisu (zapobieganie uszkodzeniom pliku)
   - Rozważenie bazodanowego podejścia do przechowywania metadanych zamiast plików JSON
   - Implementacja mechanizmu walidacji danych przy wczytywaniu metadanych

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

- Test wczytywania metadanych z prawidłowego pliku
- Test wczytywania metadanych z uszkodzonego pliku
- Test zapisu i odczytu różnych typów danych (łańcuchy, liczby, zagnieżdżone struktury)
- Test konwersji ścieżek w różnych scenariuszach

**Test integracji:**

- Test współpracy z FilePair i main_window
- Test spójności metadanych po wielu operacjach
- Test zachowania po zmianie struktury folderu

**Test wydajności:**

- Pomiar czasu wczytywania/zapisywania dużych plików metadanych
- Test wydajności przy częstych operacjach zapisu/odczytu
- Test zużycia pamięci przy operacjach na dużych zbiorach metadanych

### 📊 Status tracking

- ✅ Analiza kodu zakończona
- ⬜ Implementacja poprawek
- ⬜ Testy podstawowe przeprowadzone
- ⬜ Testy integracji przeprowadzone
- ⬜ Dokumentacja zaktualizowana
- ⬜ Gotowe do wdrożenia

## ETAP 6: src/ui/main_window.py

### 📋 Identyfikacja

- **Plik główny:** `src/ui/main_window.py`
- **Priorytet:** 🔴
- **Zależności:** Zależy od większości modułów projektu (app_config, file_operations, metadata_manager, scanner, file_pair, widgets)

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - Plik jest zdecydowanie zbyt duży (ponad 1500 linii kodu), co czyni go trudnym do utrzymania
   - Mieszanie logiki biznesowej z kodem UI - naruszenie zasady Single Responsibility
   - Potencjalne wycieki pamięci przy zamykaniu wątków (deleteLater() może nie być wywoływane w niektórych przypadkach)
   - Brak obsługi błędów w niektórych operacjach asynchronicznych
   - Zbyt wiele odpowiedzialności w jednej klasie MainWindow (zarządzanie plikami, UI, logika filtrowania)

2. **Optymalizacje:**

   - Zbyt częste odświeżanie interfejsu graficznego podczas ładowania kafelków
   - Nieoptymalne użycie QThread - brak wykorzystania puli wątków
   - Nadmiarowe operacje I/O przy każdej aktualizacji
   - Brak cachowania danych dla poprawy wydajności
   - Brak progresywnego ładowania dla dużych katalogów - wszystko jest ładowane naraz

3. **Refaktoryzacja:**
   - Podział MainWindow na mniejsze komponenty odpowiedzialne za konkretne zadania
   - Utworzenie oddzielnych kontrolerów do zarządzania logiką biznesową
   - Implementacja wzorca MVC (Model-View-Controller)
   - Ulepszenie obsługi wątków i sygnałów Qt
   - Stworzenie dedykowanych klas do obsługi elementów UI (drzewo folderów, galeria, filtry)
   - Przeniesienie logiki przetwarzania danych poza klasę MainWindow

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

- Test inicjalizacji i zamykania głównego okna
- Test nawigacji po interfejsie (między zakładkami, panelami)
- Test podstawowych operacji (skanowanie folderu, filtrowanie, otwieranie plików)
- Test obsługi typowych błędów użytkownika

**Test integracji:**

- Test współpracy z modułami logiki (scanner, file_operations, metadata_manager)
- Test zachowania UI przy różnych operacjach asynchronicznych
- Test integracji z komponentami niskopoziomowymi (Qt, system plików)

**Test wydajności:**

- Pomiar czasu ładowania dużych katalogów
- Test responsywności UI podczas operacji w tle
- Test zużycia pamięci przy długotrwałym działaniu
- Test wydajności renderowania galerii z wieloma elementami

### 📊 Status tracking

- ✅ Analiza kodu zakończona
- ⬜ Implementacja poprawek
- ⬜ Testy podstawowe przeprowadzone
- ⬜ Testy integracji przeprowadzone
- ⬜ Dokumentacja zaktualizowana
- ⬜ Gotowe do wdrożenia

## ETAP 7: run_app.py

### 📋 Identyfikacja

- **Plik główny:** `run_app.py`
- **Priorytet:** 🟡
- **Zależności:** Zależy od src.main

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - Zbyt statyczne podejście do konfigurowania sys.path
   - Ponowny import `sys` w funkcji run() (nadmiarowe)
   - Brak obsługi argumentów linii poleceń oprócz `--debug`
   - Brak obsługi błędów dla przypadku, gdy import `main` się nie powiedzie

2. **Optymalizacje:**

   - Ograniczony mechanizm konfiguracji debugowania (tylko dla jednego modułu)
   - Brak odpowiedniego przechwytywania i raportowania błędów startowych
   - Brak weryfikacji środowiska uruchomieniowego (wersja Pythona, zainstalowane pakiety)

3. **Refaktoryzacja:**
   - Należy wprowadzić bardziej elastyczny mechanizm konfiguracji przez argumenty linii poleceń
   - Dodać obsługę różnych trybów uruchamiania (dev, prod, test)
   - Przenieść logikę konfiguracji logowania do dedykowanej funkcji
   - Poprawić komunikaty diagnostyczne

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

- Test uruchomienia bez argumentów
- Test uruchomienia z argumentem `--debug`
- Test obsługi błędów przy brakujących zależnościach

**Test integracji:**

- Test poprawnego ustawienia sys.path
- Test inicjalizacji głównego modułu aplikacji

**Test wydajności:**

- Pomiar czasu startu w różnych konfiguracjach

### 📊 Status tracking

- ✅ Analiza kodu zakończona
- ⬜ Implementacja poprawek
- ⬜ Testy podstawowe przeprowadzone
- ⬜ Testy integracji przeprowadzone
- ⬜ Dokumentacja zaktualizowana
- ⬜ Gotowe do wdrożenia

## ETAP 8: src/main.py

### 📋 Identyfikacja

- **Plik główny:** `src/main.py`
- **Priorytet:** 🟡
- **Zależności:** Zależy od PyQt6, src.ui.main_window, src.utils.logging_config

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - Brak obsługi wyjątków przy inicjalizacji głównego okna
   - Brak mechanizmu obsługi błędów krytycznych w aplikacji
   - Komunikaty ostrzegawcze są tylko wyświetlane, ale nie zatrzymują niepoprawnego wykonania

2. **Optymalizacje:**

   - Ograniczona inicjalizacja aplikacji - brak opcji konfiguracyjnych
   - Brak mechanizmu przechwytywania niekrytycznych błędów w aplikacji
   - Kod bloku `if __name__ == "__main__"` jest nieużyteczny, tylko wypisuje ostrzeżenia

3. **Refaktoryzacja:**
   - Dodanie mechanizmu obsługi błędów krytycznych (uncaught exceptions)
   - Wprowadzenie systemu konfiguracji aplikacji przy starcie
   - Ulepszenie mechanizmu zamykania aplikacji (zapisywanie stanu, potwierdzenie wyjścia)
   - Dodanie konfiguracji stylów i motywów QT

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

- Test inicjalizacji i uruchamiania aplikacji
- Test poprawnego wyświetlania głównego okna
- Test poprawnego zamykania aplikacji

**Test integracji:**

- Test współpracy z systemem logowania
- Test obsługi argumentów linii poleceń przekazanych przez run_app.py

**Test wydajności:**

- Pomiar czasu inicjalizacji aplikacji
- Pomiar zużycia pamięci przy starcie

### 📊 Status tracking

- ✅ Analiza kodu zakończona
- ⬜ Implementacja poprawek
- ⬜ Testy podstawowe przeprowadzone
- ⬜ Testy integracji przeprowadzone
- ⬜ Dokumentacja zaktualizowana
- ⬜ Gotowe do wdrożenia

## ETAP 9: src/logic/filter_logic.py

### 📋 Identyfikacja

- **Plik główny:** `src/logic/filter_logic.py`
- **Priorytet:** 🟡
- **Zależności:** Zależy od src.models.file_pair, src.utils.path_utils

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - Brak walidacji danych wejściowych w funkcji `filter_file_pairs`
   - Niebezpieczne porównania typów (może wystąpić TypeError przy nieprawidłowych danych)
   - Nadmierne logowanie utrudniające czytelność logów w trybie debug
   - Nieefektywny mechanizm filtrowania - każdy warunek sprawdzany sekwencyjnie

2. **Optymalizacje:**

   - Brak prefiltrowania dla optymalizacji wczesnego odrzucania
   - Powtarzające się obliczenia właściwości podczas filtrowania
   - Nieefektywne porównania stringów (strip() i lower() przy każdym porównaniu)
   - Brak mechanizmu cache dla wyników filtrowania

3. **Refaktoryzacja:**
   - Wydzielenie osobnych funkcji dla każdego typu filtra
   - Implementacja bardziej efektywnego algorytmu filtrowania
   - Dodanie walidacji danych wejściowych
   - Ograniczenie nadmiernego logowania diagnostycznego
   - Dodanie systemu cache dla powtarzających się operacji filtrowania

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

- Test filtrowania według każdego kryterium oddzielnie
- Test filtrowania z kombinacją kryteriów
- Test obsługi przypadków brzegowych (puste listy, brakujące kryteria)
- Test walidacji danych wejściowych

**Test integracji:**

- Test współpracy z klasą FilePair
- Test integracji z interfejsem użytkownika

**Test wydajności:**

- Pomiar czasu filtrowania dla różnych wielkości list
- Test porównawczy zoptymalizowanego i obecnego algorytmu
- Test wydajności cache'owania wyników

### 📊 Status tracking

- ✅ Analiza kodu zakończona
- ⬜ Implementacja poprawek
- ⬜ Testy podstawowe przeprowadzone
- ⬜ Testy integracji przeprowadzone
- ⬜ Dokumentacja zaktualizowana
- ⬜ Gotowe do wdrożenia

## ETAP 10: src/models/file_pair.py

### 📋 Identyfikacja

- **Plik główny:** `src/models/file_pair.py`
- **Priorytet:** 🟡
- **Zależności:** Używany przez większość modułów aplikacji

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - Własna implementacja funkcji `_normalize_path` zamiast użycia wspólnej z utils.path_utils
   - Brak walidacji typów danych w metodach
   - Słaba obsługa błędów przy ładowaniu miniatur
   - Brak mechanizmu śledzenia zmian w metadanych

2. **Optymalizacje:**

   - Nieefektywne wielokrotne konwersje ścieżek względnych/absolutnych
   - Brak buforowania wyników często używanych operacji
   - Nieoptymalne ładowanie miniatur (każde wywołanie tworzy nową miniaturę)
   - Niepotrzebne używanie biblioteki Qt w klasie modelu danych

3. **Refaktoryzacja:**
   - Wydzielenie logiki UI (QPixmap) do oddzielnej klasy
   - Zastąpienie własnej implementacji `_normalize_path` przez import z utils.path_utils
   - Dodanie bardziej rozbudowanej walidacji danych
   - Implementacja mechanizmu dirty flag dla śledzenia zmian w metadanych
   - Podział na czystą klasę modelu danych i adapter UI

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

- Test tworzenia instancji z różnymi parametrami
- Test operacji na metadanych (ustawianie/pobieranie)
- Test operacji na ścieżkach (konwersje, normalizacje)
- Test walidacji danych wejściowych

**Test integracji:**

- Test współpracy z modułami scanner i filter_logic
- Test współpracy z UI (main_window)

**Test wydajności:**

- Pomiar czasu inicjalizacji dla różnych typów ścieżek
- Test wydajności ładowania miniatur
- Test wydajności przy dużej liczbie instancji

### 📊 Status tracking

- ✅ Analiza kodu zakończona
- ⬜ Implementacja poprawek
- ⬜ Testy podstawowe przeprowadzone
- ⬜ Testy integracji przeprowadzone
- ⬜ Dokumentacja zaktualizowana
- ⬜ Gotowe do wdrożenia

## ETAP 11: src/ui/widgets/file_tile_widget.py i preview_dialog.py

### 📋 Identyfikacja

- **Pliki główne:**
  - `src/ui/widgets/file_tile_widget.py`
  - `src/ui/widgets/preview_dialog.py`
- **Priorytet:** 🟡
- **Zależności:** Zależy od FilePair, image_utils, PyQt6

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - Nadmierna odpowiedzialność w klasie FileTileWidget (jednocześnie UI, logika, obsługa zdarzeń)
   - Brak mechanizmu anulowania zadań ładowania thumbnali przy usunięciu kafelka
   - Potencjalne wycieki pamięci przy wielu operacjach asynchronicznych
   - Brak animacji ładowania podczas wczytywania dużych obrazów w PreviewDialog

2. **Optymalizacje:**

   - Nieefektywne ładowanie miniatur (każdy kafelek ładuje niezależnie)
   - Brak cache'owania miniatur w pamięci dla przyspieszenia ponownego wyświetlania
   - Nadmiarowa konwersja ścieżek przy każdym renderowaniu
   - Zbyt złożona obsługa zdarzeń myszy dla operacji drag-and-drop

3. **Refaktoryzacja:**
   - Podział FileTileWidget na mniejsze, wyspecjalizowane komponenty
   - Implementacja systemu cache dla miniatur
   - Wydzielenie logiki biznesowej do osobnych klas
   - Lepsze wykorzystanie dziedziczenia i kompozycji
   - Dodanie wskaźnika postępu ładowania w PreviewDialog
   - Implementacja lazy-loading dla optymalizacji wydajności

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

- Test tworzenia i wyświetlania kafelków z różnymi danymi
- Test interakcji użytkownika (kliknięcia, drag-and-drop)
- Test różnych rozmiarów miniatur
- Test działania PreviewDialog dla różnych rozmiarów obrazów

**Test integracji:**

- Test współpracy z MainWindow
- Test obsługi zdarzeń między kafelkami

**Test wydajności:**

- Pomiar czasu ładowania i renderowania dużej liczby kafelków
- Test zużycia pamięci przy wielu otwartych oknach podglądu
- Test wydajności przy równoczesnym ładowaniu wielu miniatur

### 📊 Status tracking

- ✅ Analiza kodu zakończona
- ⬜ Implementacja poprawek
- ⬜ Testy podstawowe przeprowadzone
- ⬜ Testy integracji przeprowadzone
- ⬜ Dokumentacja zaktualizowana
- ⬜ Gotowe do wdrożenia
