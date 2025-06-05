## 🔍 ETAP 2: SZCZEGÓŁOWA ANALIZA I KOREKCJE

### ETAP 2.1: `requirements.txt`

#### 📋 Identyfikacja

- **Plik główny:** `requirements.txt`
- **Priorytet:** 🔴 WYSOKI
- **Zależności:** Brak bezpośrednich zależności plikowych w kodzie. Wpływa na całe środowisko uruchomieniowe projektu.

#### 🔍 Analiza problemów

1.  **Błędy krytyczne:**

    - **Brak wersjonowania zależności:** Plik `requirements.txt` listuje pakiety (`PyQt6`, `Pillow`, `patool`) bez określania ich konkretnych wersji. Powoduje to, że przy każdej nowej instalacji środowiska mogą zostać pobrane najnowsze dostępne wersje tych pakietów. Może to prowadzić do:
      - Problemów z kompatybilnością, jeśli nowsza wersja zależności wprowadzi zmiany niekompatybilne wstecz.
      - Trudności w odtworzeniu środowiska deweloperskiego lub produkcyjnego na innej maszynie lub w innym czasie, co jest kluczowe dla spójności i unikania błędów typu "u mnie działa".
      - Nieprzewidzianego zachowania aplikacji po aktualizacji zależności.

2.  **Optymalizacje:**

    - **Dodanie wersjonowania:** Należy określić konkretne, przetestowane wersje dla każdej zależności. Można użyć operatora `==` (np. `PyQt6==6.5.0`) dla ścisłego wersjonowania lub `>=` i `<` (np. `Pillow>=9.0.0,<10.0.0`) dla określenia kompatybilnego zakresu wersji.
      **Proponowana zawartość `requirements.txt`:**
      ```
      PyQt6==6.7.0
      Pillow==10.3.0
      patool==1.12
      ```
      _Uwaga: Powyższe numery wersji są aktualnymi stabilnymi w momencie analizy i powinny zostać dokładnie przetestowane pod kątem kompatybilności z projektem przed finalnym zatwierdzeniem._
    - **Rozważenie narzędzia do zarządzania zależnościami:** Dla bardziej zaawansowanego zarządzania zależnościami i środowiskami wirtualnymi, można rozważyć użycie narzędzi takich jak `pipenv` lub `Poetry`. Na obecnym etapie wystarczy jednak samo dodanie numerów wersji.

3.  **Refaktoryzacja:**
    - Nie dotyczy bezpośrednio tego pliku, poza dodaniem wersji.

#### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

1.  **Instalacja zależności ze zweryfikowanymi wersjami:** Po zaktualizowaniu `requirements.txt` o konkretne wersje, należy utworzyć czyste środowisko wirtualne i spróbować zainstalować zależności za pomocą `pip install -r requirements.txt`.
    - **Oczekiwany rezultat:** Wszystkie zależności instalują się poprawnie w określonych wersjach.
2.  **Uruchomienie aplikacji:** Po pomyślnej instalacji, uruchomić aplikację i przetestować jej kluczowe funkcjonalności (ładowanie interfejsu, przeglądanie folderów, wyświetlanie plików), aby upewnić się, że określone wersje zależności działają poprawnie z kodem aplikacji.
    - **Oczekiwany rezultat:** Aplikacja uruchamia się i działa stabilnie.

**Test integracji:**

- Nie dotyczy bezpośrednio tego pliku w izolacji. Testy integracyjne całej aplikacji potwierdzą, że zwersjonowane zależności współpracują ze sobą i z resztą kodu.

**Test wydajności:**

- Nie dotyczy bezpośrednio tego pliku.

#### 📊 Status tracking

- [ ] Kod zaimplementowany (wersje dodane do `requirements.txt`)
- [ ] Testy podstawowe przeprowadzone
- [ ] Testy integracji przeprowadzone (w ramach testów całej aplikacji)
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia

### ETAP 2.2: `src/ui/main_window.py`

#### 📋 Identyfikacja

- **Plik główny:** `src/ui/main_window.py`
- **Priorytet:** 🔴 WYSOKI
- **Zależności:** PyQt6, `logging`, `math`, `os`, `collections.OrderedDict`, `src.logic.file_operations`, `src.logic.metadata_manager`, `src.logic.filter_logic.filter_file_pairs`, `src.logic.scanner.scan_folder_for_pairs`, `src.models.file_pair.FilePair`, `src.ui.widgets.file_tile_widget.FileTileWidget`, `src.ui.widgets.preview_dialog.PreviewDialog`.
  - _Uwaga: Lista zależności na podstawie dostarczonego fragmentu kodu i analizy z Etapu 1._

#### 🔍 Analiza problemów

1.  **Błędy krytyczne / Główne problemy do weryfikacji:**

    - **Potencjalna duplikacja logiki obsługi drzewa folderów:**
      - **Problem:** W Etapie 1 zidentyfikowano zduplikowaną funkcję `folder_tree_item_clicked` pomiędzy `src/ui/main_window_tree_ops.py` a `src/ui/folder_tree_click_handler.py`. Plik `main_window.py` również zawiera metodę `_folder_tree_item_clicked` (widoczną w zarysie pliku).
      - **Do weryfikacji:** Należy sprawdzić, czy pliki `src/ui/main_window_tree_ops.py` i `src/ui/folder_tree_click_handler.py` są nadal aktywnie wykorzystywane i importowane. Jeśli tak, istnieje krytyczna potrzeba refaktoryzacji w celu usunięcia duplikacji i centralizacji logiki, np. w klasie `MainWindow`. Jeśli te pliki są przestarzałe, należy je usunąć.
      - **Propozycja (jeśli duplikacja istnieje):** Skonsolidować logikę obsługi zdarzeń i operacj na drzewie folderów w obrębie klasy `MainWindow` lub dedykowanej klasy pomocniczej, eliminując zewnętrzne, potencjalnie konfliktujące funkcje.
    - **Wydajność UI przy dużej liczbie plików i operacjach blokujących:**
      - **Problem:** Główne okno odpowiada za wyświetlanie galerii plików (`_update_gallery_view`), ładowanie miniatur, skanowanie folderów (`_select_working_directory` -> `scan_folder_for_pairs`). Operacje te, szczególnie na dużych zbiorach danych, mogą blokować główny wątek UI, prowadząc do zamrożenia aplikacji.
      - **Do weryfikacji (wymaga pełnego kodu metod):**
        - Czy `_update_gallery_view` efektywnie zarządza tworzeniem i usuwaniem widgetów `FileTileWidget`? Czy stosuje jakieś techniki optymalizacyjne (np. lazy loading, recykling widgetów, ograniczona liczba elementów naraz)?
        - Czy ładowanie miniatur (`FilePair.load_thumbnail()`) odbywa się w sposób nieblokujący (np. w tle) podczas aktualizacji galerii?
        - Czy `scan_folder_for_pairs` i inne potencjalnie długotrwałe operacje (np. odświeżanie po operacjach na folderach) są wykonywane w osobnym wątku?
      - **Propozycja:** Zastosować `QThread` dla długotrwałych operacji (skanowanie folderów, masowe ładowanie miniatur). Zoptymalizować tworzenie i aktualizację galerii, rozważyć implementację widoku wirtualnego lub stronicowania, jeśli standardowe podejście okaże się niewystarczające.

2.  **Optymalizacje:**

    - **Czytelność i struktura kodu:**
      - **Problem:** Klasa `MainWindow` jest bardzo długa (970 linii), co utrudnia zarządzanie kodem, jego zrozumienie i testowanie.
      - **Propozycja:** Rozważyć dekompozycję klasy `MainWindow` na mniejsze, bardziej spójne komponenty. Przykładowe obszary do wydzielenia:
        - Zarządzanie logiką drzewa folderów (jeśli nie jest już scentralizowane i wymaga uporządkowania).
        - Zarządzanie galerią kafelków (tworzenie, aktualizacja, filtrowanie widoku).
        - Obsługa paneli UI (panel filtrów, panel górny).
        - Można użyć klas pomocniczych lub kompozycji.
    - **Zarządzanie pamięcią:**
      - **Problem:** Przy dynamicznym tworzeniu i usuwaniu widgetów `FileTileWidget` oraz obiektów `FilePair` istnieje ryzyko wycieków pamięci, jeśli obiekty nie są poprawnie usuwane.
      - **Do weryfikacji:** Sprawdzić, czy mechanizmy Qt dotyczące usuwania obiektów (np. `deleteLater()`, właściwe ustawianie rodziców) są konsekwentnie stosowane w `_clear_gallery` i podczas aktualizacji widoków.
    - **Obsługa błędów:**
      - **Problem:** Wstępna analiza nie ujawnia szczegółowego, spójnego systemu informowania użytkownika o błędach z operacji plikowych, skanowania czy ładowania metadanych.
      - **Propozycja:** Wprowadzić spójny mechanizm obsługi błędów, wykorzystując np. `QMessageBox` do informowania użytkownika o problemach w sposób zrozumiały. Logowanie błędów powinno być kompleksowe.
    - **Konfiguracja i stałe:**
      - **Problem:** Wartości konfiguracyjne, takie jak rozmiary miniatur (`default_thumbnail_size`, `min_thumbnail_size`, `max_thumbnail_size`) są zakodowane bezpośrednio w `__init__`.
      - **Propozycja:** Przenieść takie konfiguracje do pliku `app_config.py` lub dedykowanej sekcji, aby ułatwić zarządzanie i modyfikacje.

3.  **Refaktoryzacja:**

    - **Redukcja złożoności metod:**
      - **Problem:** Długie metody (np. potencjalnie `_init_ui`, `_update_gallery_view`, `_folder_tree_item_clicked` w zależności od ich pełnej implementacji) mogą być trudne do zrozumienia i utrzymania.
      - **Propozycja:** Po pełnym przeglądzie kodu, zidentyfikować najdłuższe i najbardziej złożone metody, a następnie podzielić je na mniejsze, dobrze zdefiniowane funkcje prywatne.
    - **Użycie sygnałów i slotów:**
      - **Do weryfikacji:** Sprawdzić, czy komunikacja między `MainWindow` a widgetami (np. `FileTileWidget`) oraz innymi komponentami jest efektywnie realizowana za pomocą mechanizmu sygnałów i slotów Qt, minimalizując bezpośrednie wywołania metod tam, gdzie sygnały byłyby bardziej odpowiednie.

4.  **Nadmiarowy kod / Nieużywane importy:**
    - **Do weryfikacji:** Przeprowadzić analizę całego pliku pod kątem nieużywanych zmiennych, metod lub importów. (Na podstawie dostarczonego fragmentu nie można tego jednoznacznie stwierdzić).

#### 🧪 Plan testów

- **Testy jednostkowe (dla wydzielonych komponentów, jeśli nastąpi refaktoryzacja):**
  - Logika zarządzania stanem filtrów.
  - Logika pomocnicza do obsługi UI.
- **Testy integracyjne/UI (manualne lub z `pytest-qt`):**
  - Poprawne działanie wyboru folderu roboczego i inicjalizacji widoków.
  - Interakcja z drzewem folderów (rozwijanie, zaznaczanie, menu kontekstowe) i jej wpływ na galerię.
  - Dynamiczne tworzenie i wyświetlanie kafelków w galerii.
  - Poprawne działanie wszystkich filtrów (ulubione, gwiazdki, kolory) i ich kombinacji.
  - Zmiana rozmiaru miniatur za pomocą suwaka i jej odzwierciedlenie w galerii.
  - Obsługa wszystkich opcji z menu kontekstowych dla plików i folderów (tworzenie, zmiana nazwy, usuwanie, otwieranie archiwum, podgląd).
  - Odporność na błędy (np. próba operacji na nieistniejącym zasobie, brak uprawnień – mockowane lub w kontrolowanym środowisku).
  - Obsługa przeciągania i upuszczania (jeśli zaimplementowane – `dragEnterEvent`, `dropEvent`).
- **Testy wydajnościowe:**
  - Czas reakcji UI przy wyborze folderu zawierającego dużą liczbę plików (np. 100, 1000, 5000+) i podfolderów.
  - Płynność przewijania galerii z dużą liczbą załadowanych kafelków.
  - Czas potrzebny na zastosowanie filtrów i odświeżenie galerii.
  - Zużycie pamięci przez aplikację przy różnych scenariuszach użytkowania (np. po załadowaniu wielu folderów, długotrwałej pracy).
  - Czas uruchomienia aplikacji.

#### 📊 Status tracking

- [ ] Analiza kompletnego kodu pliku przeprowadzona
- [ ] Zidentyfikowane problemy udokumentowane (wersja wstępna powyżej)
- [ ] Propozycje korekt opisane (wersja wstępna powyżej)
- [ ] Plan testów przygotowany (wersja wstępna powyżej)
- [ ] Kod (proponowane zmiany) zaimplementowany w `corrections.md` (na razie opisy, szczegółowy kod do dodania po głębszej analizie)
- [ ] Testy przeprowadzone (po implementacji zmian w kodzie projektu)
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia (po implementacji i testach)

### ETAP 2.3: `src/ui/main_window_tree_ops.py`

#### 📋 Identyfikacja

- **Plik główny:** `src/ui/main_window_tree_ops.py`
- **Priorytet:** 🔴 WYSOKI (ze względu na krytyczny problem duplikacji/przestarzałości)
- **Zależności (deklarowane w pliku):** PyQt6, `logging`, `os`, `src.logic.file_operations`, `src.logic.metadata_manager`.

#### 🔍 Analiza problemów

1.  **Błędy krytyczne:**

    - **Masowa duplikacja kodu / Plik przestarzały:**
      - **Problem:** Wszystkie funkcje zdefiniowane w tym pliku (m.in. `init_directory_tree`, `show_folder_context_menu`, `create_folder`, `rename_folder`, `delete_folder`, `refresh_file_pairs_after_folder_operation`, `folder_tree_item_clicked` oraz funkcje operacji na plikach) są zduplikowane jako metody w klasie `MainWindow` (plik `src/ui/main_window.py`).
      - **Dowody:**
        1.  Porównanie sygnatur i funkcjonalności funkcji z `main_window_tree_ops.py` z metodami klasy `MainWindow` (na podstawie częściowego odczytu `main_window.py` i pełnego odczytu `main_window_tree_ops.py`).
        2.  Brak jakichkolwiek importów modułu `main_window_tree_ops` w innych plikach `.py` projektu (potwierdzone przez `grep_search`).
        3.  Znalezisko w `src/ui/integration_guide.txt` (linia 81: `# 5. Dodaj do klasy MainWindow wszystkie metody z pliku main_window_tree_ops.py:`), które wprost sugeruje, że funkcje te miały zostać przeniesione do `MainWindow`.
      - **Wniosek:** Plik `src/ui/main_window_tree_ops.py` jest przestarzały i stanowi martwy kod. Jego obecność w projekcie jest szkodliwa, ponieważ może prowadzić do pomyłek podczas rozwoju i utrudniać utrzymanie kodu.

2.  **Optymalizacje / Refaktoryzacja:**

    - **Główna propozycja: Usunięcie pliku.**
      - **Uzasadnienie:** Usunięcie tego pliku wyeliminuje zduplikowany, nieużywany kod, upraszczając strukturę projektu i zmniejszając ryzyko błędów.
      - **Kroki do wykonania (propozycja implementacji):**
        1.  Potwierdzić (poprzez pełną analizę `main_window.py`, jeśli to konieczne), że wszystkie niezbędne funkcjonalności są rzeczywiście obecne i działają poprawnie w `MainWindow`.
        2.  Usunąć plik `src/ui/main_window_tree_ops.py` z systemu kontroli wersji i systemu plików.
        3.  Opcjonalnie usunąć lub zaktualizować wpis w `src/ui/integration_guide.txt`, jeśli jest on nadal relevantny jako dokumentacja historyczna.

3.  **Nadmiarowy kod:** Cały plik jest nadmiarowy.

#### 🧪 Plan testów

- Po usunięciu pliku `src/ui/main_window_tree_ops.py`, należy przeprowadzić gruntowne testy regresji wszystkich funkcjonalności związanych z:
  - Inicjalizacją i wyświetlaniem drzewa katalogów.
  - Menu kontekstowym dla folderów w drzewie (tworzenie, zmiana nazwy, usuwanie).
  - Obsługą kliknięć elementów w drzewie katalogów i aktualizacją widoku galerii.
  - Menu kontekstowym dla plików w galerii (zmiana nazwy, usuwania – jeśli te funkcje również były w `main_window_tree_ops.py` i są teraz w `MainWindow`).
  - Odświeżaniem widoków po operacjach na plikach/folderach.
- Celem jest upewnienie się, że usunięcie pliku nie wpłynęło negatywnie na działanie aplikacji, co jest oczekiwane, jeśli cała logika jest poprawnie zaimplementowana w `MainWindow`. (Wiele z tych testów pokrywa się z planem testów dla `main_window.py`).

#### 📊 Status tracking

- [x] Analiza kompletnego kodu pliku przeprowadzona
- [x] Zidentyfikowane problemy udokumentowane
- [x] Propozycje korekt opisane (główna: usunięcie pliku)
- [ ] Kod (proponowane zmiany) zaimplementowany w `corrections.md` (w tym przypadku zmiana to usunięcie pliku, więc nie ma "kodu" do dodania, raczej opis akcji)
- [ ] Testy przeprowadzone (po implementacji zmian w kodzie projektu)
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy, np. `integration_guide.txt`)
- [ ] Gotowe do wdrożenia (po implementacji i testach)

### ETAP 2.4: `src/models/file_pair.py`

#### 📋 Identyfikacja

- **Plik główny:** `src/models/file_pair.py`
- **Priorytet:** 🔴 WYSOKI
- **Zależności:** `logging`, `os`, `shutil`, `PIL` (Pillow), `PyQt6.QtGui`, `src.utils.image_utils`.

#### 🔍 Analiza problemów

1.  **Błędy krytyczne / Główne problemy architektoniczne:**

    - **Naruszenie Zasady Pojedynczej Odpowiedzialności (SRP):**
      - **Problem:** Klasa `FilePair`, pełniąca rolę modelu danych, zawiera metody bezpośrednio wykonujące operacje modyfikujące system plików: `rename()`, `delete()` oraz `move()`. Zostało to potwierdzone przez analizę zarysu pełnego kodu pliku.
      - **Konsekwencje:**
        - **Mieszanie odpowiedzialności:** Klasa modelu staje się odpowiedzialna nie tylko za przechowywanie i zarządzanie swoim stanem, ale również za interakcje z systemem plików, co jest odrębną odpowiedzialnością.
        - **Utrudnione testowanie:** Testy jednostkowe klasy `FilePair` stają się bardziej skomplikowane, gdyż muszą uwzględniać lub mockować operacje na systemie plików. Idealnie, testy modelu powinny być odizolowane od takich zewnętrznych zależności.
        - **Mniejsza elastyczność i spójność:** Logika operacji na plikach powinna być scentralizowana (np. w `src/logic/file_operations.py`). Rozproszenie jej w klasach modeli utrudnia wprowadzanie zmian i może prowadzić do niespójności (np. różne sposoby obsługi błędów, walidacji).
        - **Ryzyko duplikacji kodu:** Jeśli moduł `src/logic/file_operations.py` już zawiera podobne funkcje (co jest prawdopodobne), istnieje ryzyko powielania logiki.
      - **Propozycja kluczowej korekty:**
        1.  **Ekstrakcja logiki operacji plikowych:** Metody `rename()`, `delete()` i `move()` wraz z ich logiką operującą na systemie plików (używającą `os`, `shutil`) powinny zostać usunięte z klasy `FilePair`.
        2.  **Centralizacja w `src/logic/file_operations.py`:** Odpowiednie funkcje realizujące te operacje powinny zostać zaimplementowane (lub rozbudowane, jeśli częściowo istnieją) w module `src/logic/file_operations.py`. Funkcje te mogłyby przyjmować jako argumenty ścieżki plików lub nawet instancję `FilePair` (aby uzyskać potrzebne ścieżki), ale nie byłyby metodami tej klasy. Na przykład:
            - `file_operations.rename_file_pair(old_archive_path, old_preview_path, new_base_name, working_dir) -> tuple(new_archive_path, new_preview_path) | None`
            - `file_operations.delete_file_pair(archive_path, preview_path) -> bool`
            - `file_operations.move_file_pair(archive_path, preview_path, new_target_dir_abs, working_dir) -> tuple(new_archive_path, new_preview_path) | None`
        3.  **Aktualizacja instancji `FilePair`:** Po pomyślnym wykonaniu operacji przez `file_operations`, komponent zarządzający (np. `MainWindow`) byłby odpowiedzialny za zaktualizowanie stanu odpowiedniej instancji `FilePair` (np. jej atrybutów `archive_path`, `preview_path`, `base_name`) lub za jej usunięcie z kolekcji.
        - **Weryfikacja:** Należy sprawdzić kod metod `rename`, `delete`, `move` w `FilePair` oraz istniejące funkcje w `file_operations.py`, aby zaplanować szczegółową implementację przeniesienia i uniknąć utraty funkcjonalności (np. specyficznej obsługi błędów, logowania).

2.  **Optymalizacje:**

    - **Ładowanie miniatur (`load_preview_thumbnail`):**
      - **Problem:** Metoda ta wykonuje operacje I/O (odczyt pliku) i potencjalnie czasochłonne przetwarzanie obrazu. Jeśli jest wywoływana synchronicznie dla wielu obiektów `FilePair` w głównym wątku UI (np. podczas wyświetlania galerii), może to prowadzić do zauważalnych opóźnień lub zamrożenia interfejsu.
      - **Propozycja (do rozważenia w kontekście całościowym):** Chociaż sama logika ładowania pojedynczej miniatury może pozostać w `FilePair`, mechanizm zarządzania masowym ładowaniem miniatur (np. dla całej galerii), ich cache'owaniem i obsługą w tle powinien być realizowany przez dedykowany komponent (np. w `MainWindow` lub specjalnej klasie pomocniczej), aby nie blokować UI.
    - **Import `shutil`:** Prawdopodobnie używany tylko w metodach `rename/delete/move`. Po ich przeniesieniu, import ten może stać się zbędny w tym pliku.

3.  **Refaktoryzacja (poza główną korektą SRP):**
    - Kod dotyczący zarządzania metadanymi i podstawowymi informacjami o pliku (rozmiar, miniatura) wydaje się być dobrze zorganizowany w ramach klasy.

#### 🧪 Plan testów

- **Testy jednostkowe dla `FilePair` (po refaktoryzacji – bez metod `rename/delete/move`):**
  - Weryfikacja konstruktora i poprawności przechowywanych atrybutów.
  - Testy dla metod `load_preview_thumbnail` (mockując zależności od systemu plików i Pillow, sprawdzając tworzenie placeholderów w różnych sytuacjach błędów).
  - Testy dla `get_archive_size` i `get_formatted_archive_size` (mockując `os.path.getsize`).
  - Testy dla metod zarządzających metadanymi (`is_favorite`, `stars`, `color_tag`).
- **Testy jednostkowe dla nowych/zmodyfikowanych funkcji w `src/logic/file_operations.py`:**
  - Dokładne testowanie logiki `rename_file_pair_paths` (lub odpowiednika), `delete_file_pair_paths`, `move_file_pair_paths`.
  - Testy powinny obejmować różne scenariusze: poprawne wykonanie, błędy (plik nie istnieje, brak uprawnień, konflikt nazw, próba przeniesienia na samego siebie itp.), poprawną obsługę pary plików (archiwum i podgląd).
  - Wymagane będzie mockowanie funkcji z modułów `os` i `shutil`.
- **Testy integracyjne (w `MainWindow` lub na poziomie wyższym):**
  - Weryfikacja, że operacje zmiany nazwy, usuwania i przenoszenia zainicjowane przez użytkownika w UI:
    1.  Poprawnie wywołują odpowiednie funkcje z `src/logic/file_operations.py`.
    2.  Po pomyślnym wykonaniu operacji, stan obiektów `FilePair` jest prawidłowo aktualizowany.
    3.  Widok użytkownika (galeria, drzewo folderów) jest poprawnie odświeżany.
    4.  Błędy operacji plikowych są odpowiednio obsługiwane i komunikowane użytkownikowi.

#### 📊 Status tracking

- [x] Analiza kompletnego kodu pliku przeprowadzona (na podstawie fragmentu i zarysu)
- [x] Zidentyfikowane problemy udokumentowane
- [x] Propozycje korekt opisane (szczegółowy plan implementacji metod `rename/delete/move`)
- [ ] Kod (proponowane zmiany, np. sygnatury funkcji w `file_operations.py` i usunięte metody z `FilePair`) zaimplementowany w `corrections.md` (do dodania po głębszej analizie implementacji metod `rename/delete/move`)
- [ ] Testy przeprowadzone (po implementacji zmian w kodzie projektu)
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia (po implementacji i testach)

### ETAP 2.5: `tests/unit/test_scanner.py`

#### 📋 Identyfikacja

- **Plik główny:** `tests/unit/test_scanner.py`
- **Priorytet:** 🔴 WYSOKI (ze względu na całkowity brak testów dla krytycznego modułu)
- **Główny moduł testowany:** `src/logic/scanner.py`
- **Kluczowa funkcja do testowania:** `scan_folder_for_pairs(folder_path: str) -> list[FilePair]`
- **Zależności (do napisania testów):** `pytest`, `tempfile`, `os`, `src.logic.scanner`, `src.models.file_pair`, `src.app_config` (dla konfiguracji rozszerzeń).

#### 🔍 Analiza problemów

1.  **Błędy krytyczne:**
    - **Całkowity brak testów jednostkowych:**
      - **Problem:** Plik `tests/unit/test_scanner.py` zawiera jedynie placeholder (`assert True`) i nie implementuje żadnych rzeczywistych testów weryfikujących działanie modułu `src/logic/scanner.py`.
      - **Konsekwencje:**
        - **Wysokie ryzyko regresji:** Wszelkie zmiany w logice skanowania lub w zależnościach (np. `app_config`) mogą wprowadzić błędy, które nie zostaną wykryte automatycznie.
        - **Brak pewności co do poprawności działania:** Aktualna implementacja skanera nie jest weryfikowana przez testy, co utrudnia potwierdzenie jej zgodności z wymaganiami w różnych scenariuszach.
        - **Utrudniony rozwój i refaktoryzacja:** Brak testów czyni modyfikacje kodu skanera ryzykownymi i czasochłonnymi.
      - **Propozycja kluczowej korekty:** Należy pilnie zaimplementować kompleksowy zestaw testów jednostkowych dla funkcji `scan_folder_for_pairs` z modułu `src/logic/scanner.py`.

#### Propozycja implementacji testów (do `tests/unit/test_scanner.py`)

Poniżej znajduje się lista kluczowych scenariuszy, które powinny zostać pokryte przez testy jednostkowe. Testy powinny wykorzystywać `pytest` oraz moduł `tempfile` do tworzenia tymczasowych struktur katalogów i plików na potrzeby każdego testu.

**Struktura testowa (ogólna koncepcja):**

```python
import os
import tempfile
import pytest
from src.logic.scanner import scan_folder_for_pairs
from src.models.file_pair import FilePair
# Mockowanie app_config może być potrzebne w niektórych testach
# from unittest.mock import patch

@pytest.fixture
def temp_scan_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

# Przykładowa funkcja pomocnicza do tworzenia plików
def create_file(path, content=""):
    with open(path, "w") as f:
        f.write(content)

# --- Scenariusze testowe ---
```

**Scenariusze do przetestowania:**

1.  **Skanowanie pustego katalogu:**

    - **Opis:** Wywołanie `scan_folder_for_pairs` na pustym katalogu.
    - **Oczekiwany rezultat:** Zwrócenie pustej listy `[]`.

2.  **Katalog bez pasujących par:**

    - **Opis:** Katalog zawierający pliki, które nie tworzą par (np. tylko pliki `.txt`, tylko archiwa bez podglądów o pasujących nazwach, tylko podglądy bez archiwów, pliki o nieobsługiwanych rozszerzeniach).
    - **Oczekiwany rezultat:** Zwrócenie pustej listy `[]`.

3.  **Proste, poprawne pary plików:**

    - **Opis:** Katalog z jedną lub kilkoma jednoznacznymi parami plików (np. `file1.zip`, `file1.jpg`; `another.rar`, `another.png`).
    - **Oczekiwany rezultat:** Lista zawierająca odpowiednią liczbę obiektów `FilePair`. Dla każdej pary zweryfikować:
      - Poprawność `archive_path` i `preview_path`.
      - Poprawność `base_name`.
      - Poprawność `working_directory`.

4.  **Archiwum bez pliku podglądu:**

    - **Opis:** Katalog zawierający plik archiwum (np. `data.zip`), ale brak odpowiadającego mu pliku podglądu.
    - **Oczekiwany rezultat:** Lista zawierająca jeden obiekt `FilePair`, gdzie `archive_path` jest poprawny, a `preview_path` jest `None`.

5.  **Plik podglądu bez odpowiadającego archiwum:**

    - **Opis:** Katalog zawierający plik podglądu (np. `image.jpg`), ale brak odpowiadającego mu pliku archiwum.
    - **Oczekiwany rezultat:** Zwrócenie pustej listy `[]` (plik podglądu bez archiwum nie tworzy pary).

6.  **Różne obsługiwane rozszerzenia:**

    - **Opis:** Testowanie z różnymi kombinacjami obsługiwanych rozszerzeń archiwów i podglądów (zgodnie z `app_config.SUPPORTED_ARCHIVE_EXTENSIONS` i `app_config.SUPPORTED_PREVIEW_EXTENSIONS`).
    - **Oczekiwany rezultat:** Poprawne identyfikowanie par dla wszystkich zdefiniowanych obsługiwanych rozszerzeń. (Może wymagać mockowania `app_config` lub tworzenia plików z wieloma różnymi rozszerzeniami).

7.  **Wielkość liter w nazwach plików i rozszerzeniach:**

    - **Opis:** Testowanie par, gdzie nazwy plików lub rozszerzenia różnią się wielkością liter (np. `MyFile.ZIP`, `myfile.jpg`; `Image.RAR`, `Image.PNG`).
    - **Oczekiwany rezultat:** Poprawne parowanie niezależnie od wielkości liter w nazwie bazowej i rozszerzeniu (lub zgodnie z zaimplementowaną logiką skanera – należy to zweryfikować i przetestować).

8.  **Pliki z kropkami w nazwie (poza rozszerzeniem):**

    - **Opis:** Testowanie par typu `archive.version1.0.zip`, `archive.version1.0.jpg`.
    - **Oczekiwany rezultat:** Poprawne wyodrębnienie `base_name` (`archive.version1.0`) i utworzenie pary.

9.  **Obsługa duplikatów plików podglądu (konflikty):**

    - **Opis:** Sytuacja, gdy dla jednego archiwum istnieje wiele potencjalnych plików podglądu (np. `file.zip`, `file.jpg`, `file.png`). Zgodnie z analizą z Etapu 1, skaner prawdopodobnie wybiera "pierwszy znaleziony".
    - **Oczekiwany rezultat:** Utworzenie jednej pary `FilePair` z archiwum i _jednym_ plikiem podglądu, zgodnie z logiką wyboru skanera (np. alfabetycznie pierwszy pasujący plik podglądu lub pierwszy napotkany przez `os.listdir`). Należy to dokładnie przetestować, aby zrozumieć i potwierdzić zachowanie.

10. **Rekursywne skanowanie podfolderów:**

    - **Opis:** Pary plików znajdujące się w bezpośrednich podfolderach skanowanego katalogu.
    - **Oczekiwany rezultat:** Poprawne odnalezienie par z podfolderów i utworzenie obiektów `FilePair` z poprawnymi, pełnymi ścieżkami.

11. **Ignorowanie nieobsługiwanych plików i folderów specjalnych:**

    - **Opis:** Katalog zawierający pliki o nieobsługiwanych rozszerzeniach oraz potencjalnie ukryte pliki/foldery (np. `.DS_Store`, `thumbs.db`), które nie powinny być brane pod uwagę.
    - **Oczekiwany rezultat:** Takie pliki i foldery są ignorowane i nie wpływają na wynik skanowania.

12. **Przypadki brzegowe nazw plików:**

    - Nazwy plików zaczynające się od kropki (poza specjalnymi plikami systemowymi).
    - Bardzo długie nazwy plików.

13. **Weryfikacja przekazania `working_directory`:**
    - **Opis:** Sprawdzenie, czy atrybut `working_directory` w obiektach `FilePair` jest poprawnie ustawiany na ścieżkę skanowanego folderu.

#### 🧪 Plan testów

- Implementacja wszystkich powyższych scenariuszy jako osobnych funkcji testowych w `tests/unit/test_scanner.py`.
- Każdy test powinien przygotować odpowiednią strukturę plików i folderów w tymczasowym katalogu (`temp_scan_dir`).
- Po wywołaniu `scan_folder_for_pairs`, należy przeprowadzić szczegółowe asercje na liście wynikowej:
  - Liczba znalezionych par.
  - Typ elementów listy (czy są to instancje `FilePair`).
  - Poprawność atrybutów każdej instancji `FilePair` (`archive_path`, `preview_path`, `base_name`, `working_directory`).

#### 📊 Status tracking

- [x] Analiza kompletnego kodu pliku przeprowadzona (plik jest niemal pusty)
- [x] Zidentyfikowane problemy udokumentowane (krytyczny brak testów)
- [x] Propozycje korekt opisane (szczegółowy plan implementacji testów)
- [ ] Kod (proponowane testy) zaimplementowany w `tests/unit/test_scanner.py` (to jest zadanie do wykonania)
- [ ] Testy przeprowadzone (po implementacji testów i ich uruchomieniu)
- [ ] Dokumentacja zaktualizowana (nie dotyczy)
- [ ] Gotowe do wdrożenia (po napisaniu i pomyślnym przejściu testów)

### ETAP 2.6: `tests/unit/test_file_operations.py` (Konsolidacja testów)

#### 📋 Identyfikacja

- **Plik główny:** `tests/unit/test_file_operations.py`
- **Priorytet:** 🔴 WYSOKI (ze względu na niekompletne pokrycie i niespójną organizację testów)
- **Moduł testowany:** `src/logic/file_operations.py`
- **Powiązany plik (do konsolidacji):** `tests/unit/test_folder_operations.py`

#### 🔍 Analiza problemów

1.  **Niekompletne pokrycie testami w dedykowanym pliku:**

    - **Problem:** Plik `tests/unit/test_file_operations.py` aktualnie zawiera jedynie testy dla funkcji `open_archive_externally` z modułu `src/logic/file_operations.py`. Pozostałe funkcje (`create_folder`, `rename_folder`, `delete_folder`) nie są testowane w tym pliku.
    - **Konsekwencje:** Utrudnia to ocenę pełnego pokrycia testami modułu `file_operations.py` oraz zarządzanie tymi testami.

2.  **Niespójna organizacja testów:**
    - **Problem:** Testy jednostkowe dla funkcji operujących na folderach (`create_folder`, `rename_folder`, `delete_folder`) z modułu `src/logic/file_operations.py` znajdują się w osobnym pliku: `tests/unit/test_folder_operations.py`.
    - **Konsekwencje:** Rozproszenie testów dla jednego modułu w kilku plikach jest nieintuicyjne, utrudnia ich odnalezienie, utrzymanie i zrozumienie zakresu testowania.

#### Propozycja kluczowej korekty: Konsolidacja testów

Celem jest zgromadzenie wszystkich testów jednostkowych dla modułu `src/logic/file_operations.py` w jednym pliku: `tests/unit/test_file_operations.py`.

**Kroki do wykonania:**

1.  **Przeniesienie istniejących testów:**

    - Zawartość pliku `tests/unit/test_folder_operations.py` (który zawiera testy dla `create_folder`, `rename_folder`, `delete_folder`, ocenione w Etapie 1 jako kompleksowe) powinna zostać przeniesiona do pliku `tests/unit/test_file_operations.py`.
    - Należy zadbać o poprawne przeniesienie wszystkich niezbędnych importów, fixture'ów (jeśli są specyficzne) oraz samych klas i metod testowych.
    - Struktura klas testowych w `tests/unit/test_file_operations.py` może wymagać dostosowania, aby pomieścić nowe testy w sposób logiczny (np. można zachować osobną klasę testową dla operacji na folderach lub zintegrować je z istniejącą `TestFileOperations`, jeśli struktura na to pozwala).

2.  **Weryfikacja kompletności pokrycia:**

    - Po przeniesieniu testów, należy upewnić się, że wszystkie publiczne funkcje z `src/logic/file_operations.py` (`open_archive_externally`, `create_folder`, `rename_folder`, `delete_folder`) są teraz pokryte testami w `tests/unit/test_file_operations.py`.

3.  **Usunięcie pliku `tests/unit/test_folder_operations.py`:**

    - Po pomyślnym przeniesieniu i weryfikacji testów, plik `tests/unit/test_folder_operations.py` stanie się zbędny i powinien zostać usunięty z projektu, aby uniknąć duplikacji i pomyłek.

4.  **Przegląd i czyszczenie importów:**
    - Po konsolidacji, przejrzeć importy w `tests/unit/test_file_operations.py` pod kątem ich poprawności i usunięcia ewentualnych duplikatów lub nieużywanych referencji.

**Uwaga dotycząca implementacji w `src/logic/file_operations.py`:**

- Podczas analizy `src/logic/file_operations.py` zauważono, że import `platform` wydaje się nie być używany (zamiast niego użyto `os.name == "nt"`). Warto to zweryfikować i ewentualnie usunąć nieużywany import, aby utrzymać czystość kodu. To drobna uwaga, niezwiązana bezpośrednio z organizacją testów, ale warta odnotowania.

#### 🧪 Plan testów

- Po konsolidacji, głównym zadaniem będzie **uruchomienie całego zestawu testów** w `tests/unit/test_file_operations.py` i upewnienie się, że wszystkie przechodzą pomyślnie.
- Przejrzenie przeniesionych testów (oryginalnie z `test_folder_operations.py`) pod kątem ich czytelności, kompletności i ewentualnych drobnych usprawnień w kontekście nowego, skonsolidowanego pliku.
- Jeśli podczas przeglądu okaże się, że brakuje jakichś istotnych scenariuszy testowych dla którejkolwiek z funkcji w `src/logic/file_operations.py`, należy je dopisać.

#### 📊 Status tracking

- [x] Analiza kompletnego kodu plików (`test_file_operations.py` i `file_operations.py`) przeprowadzona
- [x] Zidentyfikowane problemy udokumentowane (niekompletne pokrycie w dedykowanym pliku, niespójna organizacja)
- [x] Propozycje korekt opisane (konsolidacja testów, usunięcie zbędnego pliku)
- [ ] Kod (przeniesione i skonsolidowane testy) zaimplementowany w `tests/unit/test_file_operations.py` (to jest zadanie do wykonania)
- [ ] Plik `tests/unit/test_folder_operations.py` usunięty (po implementacji)
- [ ] Testy przeprowadzone (po implementacji i testach)
- [ ] Dokumentacja zaktualizowana (nie dotyczy)
- [ ] Gotowe do wdrożenia (po implementacji i testach)

### ETAP 2.7: `run_tests.bat`

#### 📋 Identyfikacja

- **Plik główny:** `run_tests.bat`
- **Priorytet:** 🟡 ŚREDNI
- **Zależności:** `pytest`, `pytest-cov`, środowisko Python skonfigurowane w PATH.

#### 🔍 Analiza problemów

1.  **Komentarz ze statyczną ścieżką (`filepath`):**

    - **Problem:** Komentarz `:: filepath: c:\_cloud\_CFAB_3DHUB\run_tests.bat` zawiera bezwzględną ścieżkę, która może być nieaktualna lub myląca, jeśli projekt zostanie przeniesiony lub skopiowany w inne miejsce.
    - **Propozycja:** Usunąć ten komentarz lub zastąpić go bardziej ogólnym opisem, jeśli jest potrzebny.

2.  **Brak jawnej obsługi błędów po wykonaniu testów:**

    - **Problem:** Skrypt nie sprawdza kodu wyjścia (`ERRORLEVEL`) poleceń `pytest`. W przypadku niepowodzenia testów, skrypt kontynuuje działanie i wyświetla komunikat "Gotowe", co może sugerować pomyślne zakończenie wszystkich operacji.
    - **Propozycja:** Dodać sprawdzanie wartości `%ERRORLEVEL%` po każdym wywołaniu `pytest`. Jeśli wystąpi błąd (kod wyjścia różny od 0), wyświetlić odpowiedni komunikat i ewentualnie zatrzymać dalsze wykonywanie skryptu lub zakończyć go z kodem błędu.

3.  **Format raportu pokrycia kodu:**
    - **Problem:** Raport pokrycia kodu jest generowany tylko w formie tekstowej do konsoli.
    - **Propozycja (opcjonalne ulepszenie):** Rozważyć dodanie generowania raportu pokrycia również w formacie HTML, który jest bardziej czytelny i interaktywny. Można to osiągnąć dodając opcję `--cov-report html:cov_html` do polecenia `pytest`.

#### Proponowane zmiany w kodzie

Poniżej znajdują się fragmenty kodu ilustrujące proponowane zmiany:

1.  **Usunięcie komentarza `filepath` i dodanie obsługi błędów:**

    ```batch
    @echo off

    echo === Uruchamianie testów jednostkowych ===
    python -m pytest tests/unit -v
    if errorlevel 1 (
        echo.
        echo ### BŁĄD: Testy jednostkowe nie powiodły się! ###
        pause
        exit /b 1
    )

    echo.
    echo === Uruchamianie testów z generowaniem raportu pokrycia kodu ===
    python -m pytest --cov=src tests/
    if errorlevel 1 (
        echo.
        echo ### BŁĄD: Testy z pokryciem kodu nie powiodły się! ###
        pause
        exit /b 1
    )

    echo.
    echo === Gotowe ===
    pause
    ```

2.  **Opcjonalne: Dodanie generowania raportu HTML dla pokrycia kodu (w połączeniu z obsługą błędów):**

    ```batch
    @echo off

    echo === Uruchamianie testów jednostkowych ===
    python -m pytest tests/unit -v
    if errorlevel 1 (
        echo.
        echo ### BŁĄD: Testy jednostkowe nie powiodły się! ###
        pause
        exit /b 1
    )

    echo.
    echo === Uruchamianie testów z generowaniem raportu pokrycia kodu (konsola + HTML) ===
    python -m pytest --cov=src --cov-report html:cov_html tests/
    if errorlevel 1 (
        echo.
        echo ### BŁĄD: Testy z pokryciem kodu nie powiodły się! ###
        pause
        exit /b 1
    )
    echo Raport HTML z pokryciem kodu został wygenerowany w folderze: cov_html

    echo.
    echo === Gotowe ===
    pause
    ```

#### 🧪 Plan testów

- Uruchomić zmodyfikowany skrypt `run_tests.bat`.
- **Scenariusz 1 (wszystkie testy przechodzą):**
  - Sprawdzić, czy oba zestawy testów (`tests/unit` i `tests/` z pokryciem) są wykonywane.
  - Sprawdzić, czy skrypt kończy się komunikatem "Gotowe".
  - (Jeśli zaimplementowano) Sprawdzić, czy raport HTML (`cov_html`) jest generowany poprawnie.
- **Scenariusz 2 (testy jednostkowe nie przechodzą):**
  - Sztucznie wprowadzić błąd w jednym z testów jednostkowych.
  - Uruchomić skrypt i sprawdzić, czy wyświetla komunikat o błędzie testów jednostkowych i zatrzymuje się lub kończy z kodem błędu.
- **Scenariusz 3 (testy z pokryciem nie przechodzą, ale jednostkowe tak):**
  - Sztucznie wprowadzić błąd w teście, który nie jest częścią `tests/unit` (jeśli takie istnieją) lub w kodzie `src/` tak, aby pokrycie nie było pełne i testy (jeśli są jakieś poza unit) mogły failować.
  - Uruchomić skrypt i sprawdzić, czy testy jednostkowe przechodzą, a następnie skrypt wyświetla komunikat o błędzie testów z pokryciem i zatrzymuje się lub kończy z kodem błędu.

#### 📊 Status tracking

- [x] Analiza kompletnego kodu pliku przeprowadzona
- [x] Zidentyfikowane problemy udokumentowane
- [x] Propozycje korekt opisane (wraz z przykładowym kodem)
- [ ] Kod (proponowane zmiany) zaimplementowany w `run_tests.bat`
- [ ] Testy przeprowadzone (zgodnie z planem testów)
- [ ] Dokumentacja zaktualizowana (nie dotyczy)
- [ ] Gotowe do wdrożenia (po implementacji i testach)

### ETAP 2.8: `src/ui/folder_tree_click_handler.py`

#### 📋 Identyfikacja

- **Plik główny:** `src/ui/folder_tree_click_handler.py`
- **Priorytet:** 🟡 ŚREDNI (ze względu na potencjalną przestarzałość i potrzebę uporządkowania kodu)
- **Zależności (deklarowane w pliku):** `logging`, `src.logic.metadata_manager`, `src.logic.scanner`.

#### 🔍 Analiza problemów

1.  **Plik przestarzały / Zduplikowana funkcjonalność:**

    - **Problem:** Plik zawiera jedną funkcję `folder_tree_item_clicked(self, index)`, która obsługuje logikę po kliknięciu elementu w drzewie folderów. Ta sama funkcjonalność jest najprawdopodobniej zaimplementowana jako metoda `_folder_tree_item_clicked(self, index)` w klasie `MainWindow` (`src/ui/main_window.py`).
    - **Dowody:**
      1.  Analiza kodu funkcji `folder_tree_item_clicked` wskazuje, że operuje ona na atrybutach i metodach typowych dla instancji `MainWindow`.
      2.  Obecność metody `_folder_tree_item_clicked` w klasie `MainWindow` (zidentyfikowana w Etapie 1 i potwierdzona w analizie `main_window.py`).
      3.  Brak jakichkolwiek importów modułu `folder_tree_click_handler` w innych plikach `.py` projektu (potwierdzone przez `grep_search`).
    - **Wniosek:** Plik `src/ui/folder_tree_click_handler.py` jest przestarzały i stanowi martwy kod. Jego funkcjonalność została prawdopodobnie przeniesiona bezpośrednio do klasy `MainWindow`.

2.  **Optymalizacje / Refaktoryzacja:**

    - **Główna propozycja: Usunięcie pliku.**
      - **Uzasadnienie:** Usunięcie tego pliku wyeliminuje nieużywany kod, upraszczając strukturę projektu i zmniejszając ryzyko pomyłek przy przyszłych modyfikacjach.
      - **Kroki do wykonania (propozycja implementacji):**
        1.  Ostatecznie potwierdzić (poprzez pełną analizę metody `_folder_tree_item_clicked` w `main_window.py`), że cała niezbędna funkcjonalność z `folder_tree_click_handler.py` jest rzeczywiście obecna i działa poprawnie w `MainWindow`. (Na podstawie dotychczasowej analizy jest to wysoce prawdopodobne).
        2.  Usunąć plik `src/ui/folder_tree_click_handler.py` z systemu kontroli wersji i systemu plików.

3.  **Nadmiarowy kod:** Cały plik jest nadmiarowy.

#### 🧪 Plan testów

- Po usunięciu pliku `src/ui/folder_tree_click_handler.py`, należy przeprowadzić testy regresji funkcjonalności klikania elementów w drzewie katalogów w `MainWindow`.
- Testy te powinny zweryfikować, czy:
  - Poprawnie skanowany jest wybrany folder.
  - Stosowane są metadane.
  - Aktualizowany jest widok galerii (`_update_gallery_view` lub `_clear_gallery` w zależności od zawartości folderu).
  - Panel kontroli rozmiaru (`size_control_panel`) jest odpowiednio pokazywany/ukrywany.
- Celem jest upewnienie się, że usunięcie pliku nie wpłynęło negatywnie na działanie aplikacji. (Wiele z tych testów pokrywa się z planem testów dla `main_window.py`).

#### 📊 Status tracking

- [x] Analiza kompletnego kodu pliku przeprowadzona
- [x] Zidentyfikowane problemy udokumentowane (plik przestarzały)
- [x] Propozycje korekt opisane (główna: usunięcie pliku)
- [ ] Kod (proponowane zmiany) zaimplementowany w `corrections.md` (w tym przypadku zmiana to usunięcie pliku)
- [ ] Testy przeprowadzone (po implementacji zmian w kodzie projektu)
- [ ] Dokumentacja zaktualizowana (nie dotyczy)
- [ ] Gotowe do wdrożenia (po implementacji i testach)

### ETAP 2.9: `src/ui/widgets/file_tile_widget.py`

#### 📋 Identyfikacja

- **Plik główny:** `src/ui/widgets/file_tile_widget.py`
- **Priorytet:** 🟡 ŚREDNI
- **Zależności:** `logging`, `collections.OrderedDict`, `PyQt6` (QtCore, QtGui, QtWidgets), `src.models.file_pair.FilePair`.

#### 🔍 Analiza problemów i obszary do weryfikacji (po pełnej analizie kodu)

Widget jest kluczowym elementem UI i generalnie jego struktura jest dobra. Poniżej zaktualizowane punkty:

1.  **Niekompletna implementacja Drag & Drop (KRYTYCZNY PROBLEM):**

    - **Problem:** Metoda `mouseMoveEvent` inicjuje obiekt `QDrag` i `QMimeData`, ale nie ustawia żadnych danych w `mime_data` (np. za pomocą `mime_data.setData()` lub `mime_data.setText()`) ani nie przekazuje `mime_data` do obiektu `drag` (`drag.setMimeData(mime_data)`), ani nie wykonuje operacji przeciągania (`drag.exec()`). Serializacja `file_id` jest przygotowana, ale nieużyta.
    - **Konsekwencje:** Funkcjonalność przeciągania i upuszczania kafelków prawdopodobnie nie działa lub działa niepoprawnie.

2.  **Duplikacja i niespójność definicji kolorów (`PREDEFINED_COLORS`):**

    - **Problem:** Widget definiuje `PREDEFINED_COLORS`. Klasa `MainWindow` (w `main_window.py`) definiuje bardzo podobną, ale nieidentyczną strukturę `PREDEFINED_COLORS_FILTER`. Prowadzi to do redundancji, potencjalnych niespójności i utrudnia zarządzanie kolorami.
    - **Propozycja:**
      1.  Ujednolicić obie listy kolorów.
      2.  Przenieść wspólną, ujednoliconą definicję `PREDEFINED_COLORS` (np. jako `OrderedDict` lub lista tupli) do centralnego modułu konfiguracyjnego, np. `src/app_config.py`.
      3.  Importować tę definicję zarówno w `FileTileWidget`, jak i w `MainWindow`.

3.  **Niewykorzystany/Nieaktualizowany `color_indicator_bar`:**

    - **Problem:** W `_init_ui` tworzony jest `self.color_indicator_bar` (`QFrame` o wysokości 5px, dodawany na górze widgetu). Jednak jego styl (kolor tła) nie jest aktualizowany w metodzie `update_color_tag_display`, która zmienia kolor ramki samej miniatury. Pasek pozostaje transparentny.
    - **Propozycja:**
      - **Opcja A (Wykorzystanie paska):** W metodzie `update_color_tag_display`, oprócz zmiany stylu `thumbnail_label`, aktualizować również styl `color_indicator_bar`, np. `self.color_indicator_bar.setStyleSheet(f"background-color: {color_hex_string};")` jeśli `color_hex_string` jest dostępny, lub na transparentny, gdy brak koloru.
      - **Opcja B (Usunięcie paska):** Jeśli pasek wskaźnika koloru nie jest zamierzony do użycia, usunąć jego tworzenie i dodawanie z metody `_init_ui`, aby uprościć kod.

4.  **Implementacja skalowania i wyświetlania miniatur (metoda `set_thumbnail_size` i użycie w `update_data`):**

    - **Status:** Zweryfikowano - implementacja jest **poprawna**. Używa `self.original_thumbnail` i `QPixmap.scaled()` z `Qt.AspectRatioMode.KeepAspectRatio` i `Qt.TransformationMode.SmoothTransformation`.

5.  **Logika obsługi zdarzeń (metody `eventFilter`, `mousePressEvent`):**

    - **Status:** Zweryfikowano - `eventFilter` dla kliknięć na etykietach jest **poprawny**. `mousePressEvent` poprawnie inicjuje `self.drag_start_position`.

6.  **Kompletność i efektywność metody `update_data(self, file_pair: FilePair)`:**

    - **Status:** Zweryfikowano - metoda jest **generalnie poprawna i kompletna** pod względem aktualizacji UI na podstawie `FilePair`.

7.  **Zarządzanie stanem kontrolek metadanych (gwiazdki, ulubione, kolor):**
    - **Status:** Zweryfikowano - logika aktualizacji UI i emitowania sygnałów dla gwiazdek, ulubionych i kolorów jest **poprawna i spójna**.

#### 🧪 Plan testów (pozostaje aktualny, z uwzględnieniem testów dla D&D)

Testowanie widgetów Qt najlepiej przeprowadzać za pomocą narzędzi do testów UI, takich jak `pytest-qt`.

- **Testy poprawnego wyświetlania danych:** (jak poprzednio)
- **Testy interakcji z kontrolkami metadanych:** (jak poprzednio)
- **Testy obsługi zdarzeń (kliknięcia, menu kontekstowe):** (jak poprzednio)
- **Testy Drag & Drop (NOWE/ROZSZERZONE):**
  - Po dokończeniu implementacji `mouseMoveEvent`, symulować operację przeciągania.
  - Weryfikować, czy `QDrag` jest inicjowany.
  - Sprawdzać zawartość i format danych w `QMimeData`.
  - Testować wykonanie `drag.exec()` (może wymagać bardziej zaawansowanych technik testowania UI).
- **Test zmiany rozmiaru miniatury:** (jak poprzednio)
- **Test aktualizacji `color_indicator_bar` (NOWE):** Jeśli zostanie zaimplementowana aktualizacja tego paska.

#### 📊 Status tracking

- [x] Analiza kompletnego kodu pliku przeprowadzona
- [x] Zidentyfikowane problemy udokumentowane (w tym krytyczny dla D&D i duplikacja kolorów)
- [x] Propozycje korekt opisane
- [ ] Kod (proponowane zmiany, np. dokończenie D&D, centralizacja kolorów) zaimplementowany w `corrections.md`
- [ ] Testy przeprowadzone (po implementacji zmian w kodzie projektu)
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia (po implementacji i testach)

### ETAP 2.10: `src/ui/widgets/preview_dialog.py`

#### 📋 Identyfikacja

- **Plik główny:** `src/ui/widgets/preview_dialog.py`
- **Priorytet:** 🟡 ŚREDNI
- **Zależności:** `PyQt6` (QtCore, QtGui, QtWidgets).

#### 🔍 Analiza problemów

Głównym problemem w tym pliku jest skomplikowana, powtarzalna i częściowo nieefektywna logika obliczania początkowego rozmiaru okna dialogowego w jego konstruktorze (`__init__`).

1.  **Powtarzalność kodu przy skalowaniu do limitów ekranu:**

    - **Problem:** Blok kodu odpowiedzialny za dopasowanie wymiarów obrazu (`dialog_w`, `dialog_h`) do maksymalnych dostępnych wymiarów ekranu (uwzględniając margines i proporcje obrazu) jest powtórzony trzykrotnie w metodzie `__init__`.
    - **Konsekwencje:** Utrudnia to czytanie, zrozumienie i modyfikację kodu. Zwiększa ryzyko wprowadzenia błędów przy zmianach.

2.  **Skomplikowana logika "upscalingu" do minimalnego rozmiaru:**

    - **Problem:** Sekcja kodu, która próbuje powiększyć obraz, jeśli jego wstępnie obliczone wymiary są mniejsze niż zdefiniowane minimalne wymiary okna dialogowego (`min_dialog_w`, `min_dialog_h`), również zawiera powtórzony blok skalowania do limitów ekranu. Sama logika obliczania `upscale_factor` i jego stosowania mogłaby być bardziej przejrzysta.

3.  **Martwy kod w obliczeniach `final_width` i `final_height`:**

    - **Problem:** W końcowej części logiki rozmiaru znajdują się złożone przypisania do zmiennych `final_width` i `final_height`, które są natychmiast nadpisywane przez `final_width = int(dialog_w)` i `final_height = int(dialog_h)`. Te pierwsze, bardziej skomplikowane obliczenia nie mają żadnego efektu.

4.  **Niespójność w stosowaniu minimalnych wymiarów okna:**
    - **Problem:** Po obliczeniu `dialog_w` i `dialog_h` (po próbach dopasowania do ekranu i ewentualnego upscalingu), kod modyfikuje zmienne `final_width` i `final_height`, aby zapewnić, że nie są mniejsze niż `min_dialog_w` i `min_dialog_h`. Jednak do faktycznego ustawienia rozmiaru okna (`self.resize()`) używane są wartości `dialog_w` i `dialog_h` sprzed tej ostatecznej korekty minimalnych wymiarów. Oznacza to, że okno dialogowe może zostać ustawione na rozmiar mniejszy niż zdefiniowane `min_dialog_w`/`min_dialog_h`.

#### Proponowane zmiany w kodzie

Zalecana jest refaktoryzacja sekcji obliczania rozmiaru w metodzie `__init__`.

1.  **Wydzielenie logiki dopasowania do ograniczeń:**
    Stworzyć prywatną metodę pomocniczą, np. `_adjust_to_constraints(self, width, height, aspect_ratio, max_width, max_height)`, która przyjmuje aktualne wymiary, proporcje oraz maksymalne dopuszczalne wymiary, a zwraca skorygowane wymiary. Ta metoda zastąpiłaby powtarzający się blok kodu.

    ```python
    # Propozycja metody pomocniczej:
    def _adjust_to_constraints(self, width: float, height: float, aspect_ratio: float, max_width: float, max_height: float) -> tuple[float, float]:
        # Dostosuj szerokość
        if width > max_width:
            width = max_width
            if aspect_ratio > 0: # Unikaj dzielenia przez zero jeśli aspect_ratio może być problematyczne
                height = width / aspect_ratio

        # Dostosuj wysokość (po ewentualnej korekcie szerokości)
        if height > max_height:
            height = max_height
            if aspect_ratio > 0: # aspect_ratio powinno być dodatnie; można dodać asercję
                 width = height * aspect_ratio

        # Ostateczne dostosowanie szerokości, jeśli korekta wysokości ją naruszyła
        if width > max_width: # Może się zdarzyć dla bardzo szerokich obrazów
            width = max_width
            if aspect_ratio > 0:
                height = width / aspect_ratio
        return width, height
    ```

2.  **Uproszczenie głównej logiki obliczania rozmiaru w `__init__`:**

    ```python
    # Fragment z __init__ po refaktoryzacji:
    # ... (pobranie pixmap_w, pixmap_h, screen_geometry, definicje stałych)

    if pixmap_h == 0 or pixmap_w == 0:
        self.image_label.setText("Błąd: Wymiary obrazu są zerowe.")
        self.resize(300, 200) # Rozmiar domyślny dla błędu
        return

    # Stałe (mogą być stałymi klasy lub przekazane argumentami)
    SCREEN_MARGIN = 50
    MIN_DIALOG_WIDTH = 200
    MIN_DIALOG_HEIGHT = 150

    image_aspect_ratio = float(pixmap_w) / pixmap_h

    available_width = float(screen_geometry.width() - SCREEN_MARGIN)
    available_height = float(screen_geometry.height() - SCREEN_MARGIN)

    # 1. Wstępne wymiary obrazu
    current_w = float(pixmap_w)
    current_h = float(pixmap_h)

    # 2. Dopasuj obraz do dostępnego miejsca na ekranie
    current_w, current_h = self._adjust_to_constraints(
        current_w, current_h, image_aspect_ratio, available_width, available_height
    )

    # 3. Logika "upscalingu", jeśli obraz jest mniejszy niż preferowane minimum,
    #    ale tylko jeśli powiększony obraz nadal mieści się na ekranie.
    #    To upraszcza oryginalną logikę `upscale_factor`.
    scaled_up_w = current_w
    scaled_up_h = current_h

    if current_w < MIN_DIALOG_WIDTH:
        scaled_up_w = float(MIN_DIALOG_WIDTH)
        scaled_up_h = scaled_up_w / image_aspect_ratio

    if scaled_up_h < MIN_DIALOG_HEIGHT: # Sprawdź po potencjalnej zmianie z MIN_DIALOG_WIDTH
        scaled_up_h = float(MIN_DIALOG_HEIGHT)
        scaled_up_w = scaled_up_h * image_aspect_ratio
        # Ponownie sprawdź szerokość, jeśli wysokość dominowała
        if scaled_up_w < MIN_DIALOG_WIDTH:
            scaled_up_w = float(MIN_DIALOG_WIDTH)
            scaled_up_h = scaled_up_w / image_aspect_ratio


    # Sprawdź, czy powiększone wymiary nadal mieszczą się na ekranie
    temp_w_after_upscale, temp_h_after_upscale = self._adjust_to_constraints(
        scaled_up_w, scaled_up_h, image_aspect_ratio, available_width, available_height
    )

    # Jeśli powiększony rozmiar (próbujący osiągnąć MIN_DIALOG_WIDTH/HEIGHT)
    # jest taki sam jak po ponownym ograniczeniu do ekranu, to go akceptujemy.
    # Oznacza to, że powiększenie do minimum było możliwe w ramach ekranu.
    if abs(temp_w_after_upscale - scaled_up_w) < 1 and abs(temp_h_after_upscale - scaled_up_h) < 1:
         current_w, current_h = scaled_up_w, scaled_up_h
    # W przeciwnym razie, trzymamy się wymiarów już dopasowanych do ekranu (z kroku 2),
    # ponieważ próba osiągnięcia MIN_DIALOG_WIDTH/HEIGHT przekroczyłaby ekran.

    # 4. Ostateczny rozmiar okna dialogowego: powinien być co najmniej MIN_DIALOG_WIDTH/HEIGHT
    #    i nie większy niż dostępna przestrzeń ekranu.
    #    Używamy `current_w` i `current_h` jako bazę dla zawartości obrazu.
    final_dialog_w = max(current_w, MIN_DIALOG_WIDTH)
    final_dialog_h = max(current_h, MIN_DIALOG_HEIGHT)

    # Upewnij się, że nawet te minimalne wymiary dialogu nie przekraczają ekranu
    final_dialog_w = min(final_dialog_w, available_width)
    final_dialog_h = min(final_dialog_h, available_height)

    self.resize(int(final_dialog_w), int(final_dialog_h))
    self._update_pixmap_scaled()
    ```

3.  **Usunięcie martwego kodu:** Wyeliminować nieużywane obliczenia `final_width` i `final_height` z oryginalnego kodu.

#### 🧪 Plan testów

- Testować dialog z obrazami o różnych rozmiarach i proporcjach:
  - Bardzo małe obrazy (mniejsze niż `MIN_DIALOG_WIDTH`/`MIN_DIALOG_HEIGHT`).
  - Obrazy średniej wielkości.
  - Obrazy bardzo duże (większe niż dostępne miejsce na ekranie).
  - Obrazy bardzo szerokie i bardzo wysokie.
- Weryfikować, czy:
  - Okno dialogowe nigdy nie jest większe niż dostępna przestrzeń ekranu (minus marginesy).
  - Okno dialogowe nigdy nie jest mniejsze niż `MIN_DIALOG_WIDTH` x `MIN_DIALOG_HEIGHT` (chyba że sam ekran jest mniejszy).
  - Wyświetlany obraz (`image_label`) zachowuje prawidłowe proporcje.
  - Poprawnie obsługiwane są przypadki zerowych wymiarów obrazu lub braku obrazu.
- Testować na różnych rozdzielczościach ekranu (jeśli to możliwe, symulując).

#### 📊 Status tracking

- [x] Analiza kompletnego kodu pliku przeprowadzona
- [x] Zidentyfikowane problemy udokumentowane (skomplikowana i powtarzalna logika rozmiaru)
- [x] Propozycje korekt opisane (refaktoryzacja logiki `__init__` z metodą pomocniczą)
- [ ] Kod (zrefaktoryzowana logika) zaimplementowany w `src/ui/widgets/preview_dialog.py`
- [ ] Testy przeprowadzone (po implementacji zmian w kodzie projektu)
- [ ] Dokumentacja zaktualizowana (nie dotyczy)
- [ ] Gotowe do wdrożenia (po implementacji i testach)

### ETAP 2.11: `src/utils/image_utils.py`

#### 📋 Identyfikacja

- **Plik główny:** `src/utils/image_utils.py`
- **Priorytet:** 🟡 ŚREDNI
- **Zależności:** `logging`, `io.BytesIO`, `PIL (Pillow)` (Image, ImageDraw, ImageFont), `PyQt6` (QtCore, QtGui).
- **Uwaga:** Wstępna analiza z Etapu 1 błędnie wskazywała na obecność funkcji `load_image_as_pixmap` i `resize_pixmap_to_label` w tym module. Analiza dotyczy funkcji faktycznie istniejących: `create_placeholder_pixmap` i `pillow_image_to_qpixmap`.

#### 🔍 Analiza problemów i Proponowane zmiany

##### 1. Funkcja `create_placeholder_pixmap`

- **Problem: Niedokładne centrowanie i renderowanie tekstu.**

  - **Opis:** Obecne obliczanie pozycji tekstu (`text_width = len(text) * 6`) jest bardzo przybliżone.
  - **Rekomendacja:** Zastosować metody Pillow do precyzyjnego określenia wymiarów tekstu (np. `ImageDraw.textbbox()` lub `ImageFont.getmask().size` + `ImageFont.getoffset()`) w celu dokładnego wyśrodkowania.
  - **Przykład (dla nowszych Pillow z `textbbox`):**

    ```python
    # ... wewnątrz create_placeholder_pixmap, po załadowaniu czcionki
    # text_anchor = "mm" # dla Pillow >= 8.0.0 dla idealnego środka
    # text_x = width / 2
    # text_y = height / 2
    # draw.text((text_x, text_y), text, fill="black", font=font, anchor=text_anchor)

    # Lub dla starszych wersji / alternatywnie:
    if hasattr(draw, 'textbbox'): # Pillow >= 8.0.0
        bbox = draw.textbbox((0,0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    elif hasattr(font, 'getsize'): # Starsze Pillow
        text_width, text_height = font.getsize(text) # Może być mniej dokładne dla niektórych czcionek
    else: # Fallback bardzo podstawowy
        text_width = len(text) * 6
        text_height = 10

    text_x = (width - text_width) / 2
    text_y = (height - text_height) / 2
    draw.text((text_x, text_y), text, fill="black", font=font)
    ```

- **Problem: Użycie domyślnej, potencjalnie niespójnej czcionki systemowej.**

  - **Opis:** `ImageFont.load_default()` może dawać różne wyniki na różnych systemach.
  - **Rekomendacja:** Dołączyć plik czcionki `.ttf` do zasobów aplikacji i ładować go przez `ImageFont.truetype("path/to/your/font.ttf", desired_size)`.

- **Problem: Brak obsługi zbyt długiego tekstu.**
  - **Opis:** Długi tekst może wychodzić poza granice placeholdera.
  - **Rekomendacja:** Dodać logikę obsługi długiego tekstu. Przykładowe strategie:
    1.  **Skracanie z wielokropkiem:** Jeśli obliczona szerokość tekstu przekracza dostępną przestrzeń, iteracyjnie skracaj tekst i dodawaj "..." aż się zmieści.
    2.  **Dynamiczne zmniejszanie czcionki:** Jeśli tekst jest za szeroki, spróbuj zmniejszyć rozmiar czcionki (wymaga ładowania czcionki z rozmiarem).
    3.  **Łamanie wierszy:** (Bardziej złożone) Podziel tekst na kilka linii.

##### 2. Funkcja `pillow_image_to_qpixmap`

- **Problem: Utrata przezroczystości i potencjalna utrata jakości z powodu formatu JPEG.**

  - **Opis:** Konwersja obrazów RGBA na RGB poprzez nałożenie na białe tło eliminuje przezroczystość. Zapis do bufora w formacie JPEG (stratnym, nieobsługującym alfa) dodatkowo pogarsza jakość i uniemożliwia zachowanie przezroczystości.
  - **Rekomendacja:**

    - **Format pośredni:** Zmienić format zapisu do bufora z "JPEG" na "PNG". PNG jest formatem bezstratnym i obsługuje kanał alfa.
      ```python
      # Zmiana w pillow_image_to_qpixmap:
      # pil_image.save(buffer, format="JPEG")  ->  pil_image.save(buffer, format="PNG")
      ```
    - **Zachowanie przezroczystości (dla RGBA):** Aby zachować przezroczystość z obrazu PIL (jeśli jest w trybie RGBA lub P z przezroczystością) do `QPixmap`, należy unikać konwersji na białe tło i przekonwertować dane bezpośrednio.

      ```python
      # Propozycja zmodyfikowanej konwersji dla RGBA:
      if pil_image.mode == "RGBA":
          # Bezpośrednia konwersja danych RGBA
          data = pil_image.tobytes("raw", "RGBA")
          q_image = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
          # Lub Format_ARGB32 w zależności od kolejności bajtów oczekiwanej przez system/Qt
          # Może być konieczne byteswap dla niektórych formatów ARGB32, np. q_image.rgbSwapped()
          return QPixmap.fromImage(q_image)
      elif pil_image.mode == "P" and 'transparency' in pil_image.info:
          pil_image = pil_image.convert("RGBA") # Najpierw konwertuj paletę z alfa na RGBA
          data = pil_image.tobytes("raw", "RGBA")
          q_image = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
          return QPixmap.fromImage(q_image)
      elif pil_image.mode != "RGB": # Dla innych trybów bez alfa
          pil_image = pil_image.convert("RGB")

      # Dla obrazów RGB (lub skonwertowanych do RGB) można użyć istniejącej logiki z buforem PNG
      buffer = BytesIO()
      pil_image.save(buffer, format="PNG") # Użyj PNG
      buffer.seek(0)
      q_image = QImage()
      q_image.loadFromData(buffer.getvalue())
      return QPixmap.fromImage(q_image)
      ```

##### 3. Potencjalne brakujące funkcje

- **Funkcja `qpixmap_to_pillow_image(qpixmap)`:**
  - **Opis:** Brak funkcji konwertującej w drugą stronę (`QPixmap` -> `PIL.Image`).
  - **Rekomendacja:** Jeśli w projekcie istnieje potrzeba takiej konwersji, należy ją zaimplementować. Konwersja polegałaby na zapisie `QPixmap` do `QBuffer` (np. w formacie PNG), a następnie odczycie tego bufora przez `PIL.Image.open()`.
- **Ogólna funkcja ładowania obrazu z pliku `load_image_advanced(path, size=None)`:**
  - **Opis:** Projekt może skorzystać na generycznej funkcji, która wczytuje obraz z ścieżki pliku używając Pillow (dla lepszej obsługi formatów i błędów) i opcjonalnie skaluje go, zwracając `QPixmap`.
  - **Rekomendacja:** Rozważyć implementację takiej funkcji, jeśli standardowe `QPixmap(path)` jest niewystarczające lub jeśli operacje takie jak wstępne skalowanie są często potrzebne.

#### 🧪 Plan testów

- **`create_placeholder_pixmap`:**
  - Testować z różnymi długościami tekstu, w tym bardzo długim.
  - Sprawdzać wizualnie dokładność centrowania tekstu po implementacji zmian.
  - Testować z dołączoną czcionką `.ttf`.
  - Weryfikować, czy placeholder jest poprawnie generowany dla różnych wymiarów.
- **`pillow_image_to_qpixmap`:**
  - Testować konwersję obrazów PIL w różnych trybach: "RGB", "RGBA", "L", "P" (z przezroczystością i bez).
  - Sprawdzać, czy przezroczystość jest poprawnie zachowywana (po zmianach w obsłudze RGBA).
  - Porównywać jakość obrazu po konwersji (szczególnie przy zmianie z JPEG na PNG).
  - Testować przypadki błędów (np. przekazanie niepoprawnego obiektu).
- **Nowe funkcje (jeśli zostaną dodane):**
  - Testować `qpixmap_to_pillow_image` z różnymi `QPixmap` (z przezroczystością i bez).
  - Testować `load_image_advanced` z różnymi formatami plików, ścieżkami, opcją skalowania.

#### 📊 Status tracking

- [x] Analiza kodu pliku przeprowadzona.
- [x] Zidentyfikowane problemy i sugestie udokumentowane.
- [x] Propozycje zmian w kodzie i dodania nowych funkcji opisane.
- [ ] Kod (sugerowane zmiany) zaimplementowany w `src/utils/image_utils.py`.
- [ ] Kod (nowe funkcje, jeśli zostaną zaakceptowane) zaimplementowany.
- [ ] Testy przeprowadzone.
- [ ] Dokumentacja zaktualizowana.
- [ ] Gotowe do wdrożenia.

### ETAP 2.12: `src/logic/scanner.py`

#### 📋 Identyfikacja

- **Plik główny:** `src/logic/scanner.py`
- **Priorytet:** 🟡 ŚREDNI
- **Zależności:** `logging`, `os`, `src.app_config` (SUPPORTED_ARCHIVE_EXTENSIONS, SUPPORTED_PREVIEW_EXTENSIONS), `src.models.file_pair.FilePair`.

#### 🔍 Analiza problemów i Proponowane zmiany

Moduł `scanner.py` jest kluczowy dla identyfikacji par plików. Głównym obszarem wymagającym uwagi jest sposób obsługi nazw plików, w szczególności wielkość liter.

1.  **Krytyczny: Wrażliwość na wielkość liter w nazwach bazowych plików przy parowaniu.**

    - **Problem:** Funkcja `scan_folder_for_pairs` używa nazwy bazowej pliku (uzyskanej z `os.path.splitext(file_name)[0]`) bezpośrednio jako klucza do identyfikacji potencjalnych par. Oznacza to, że pliki takie jak `MojeArchiwum.zip` i `mojearchiwum.jpg` nie zostaną sparowane, ponieważ "MojeArchiwum" i "mojearchiwum" są traktowane jako różne nazwy bazowe. Użytkownicy zazwyczaj oczekują, że parowanie będzie niezależne od wielkości liter.
    - **Rekomendacja:** Znormalizować nazwę bazową pliku do małych liter przed użyciem jej jako klucza w słowniku `potential_files`.
      ```python
      # W funkcji scan_folder_for_pairs:
      # Zamiast:
      # base_name, extension = os.path.splitext(file_name)
      # extension = extension.lower()
      # Proponowana zmiana:
      raw_base_name, extension = os.path.splitext(file_name)
      base_name = raw_base_name.lower() # Normalizacja nazwy bazowej
      extension = extension.lower()     # Rozszerzenie już było normalizowane
      ```
    - **Konsekwencje:** Ta zmiana zapewni, że pliki będą poprawnie parowane niezależnie od wielkości liter w ich nazwach bazowych, co jest bardziej intuicyjne i zgodne z oczekiwaniami użytkowników.

2.  **Reguła "pierwszy znaleziony wygrywa" dla duplikatów nazw bazowych.**

    - **Obserwacja:** Jeśli dla tej samej (znormalizowanej) nazwy bazowej istnieje wiele plików tego samego typu (np. dwa pliki archiwum `projekt.zip` w różnych podkatalogach, lub `projekt.jpg` i `projekt.png`), funkcja wybiera tylko pierwszy napotkany plik danego typu. Jest to udokumentowane ("W przypadku wielu podglądów do jednego archiwum, wybiera pierwszy pasujący").
    - **Uwaga:** To zachowanie jest akceptowalne, jeśli jest świadomą decyzją projektową. Należy jednak pamiętać, że kolejność przetwarzania plików przez `os.walk` może wpływać na to, który plik zostanie wybrany. Jeśli wymagana byłaby inna logika (np. preferowanie plików z płytszych katalogów, nowszych plików), wymagałoby to znaczących zmian. Na potrzeby tego audytu uznajemy to za istniejącą, udokumentowaną logikę.

3.  **Prawdopodobnie zbędna konwersja `file_name` na `str`.**

    - **Problem:** Linia `if not isinstance(file_name, str): file_name = str(file_name)` jest umieszczona w pętli przetwarzającej pliki. W Pythonie 3, `os.walk` powinien zwracać nazwy plików jako obiekty `str`.
    - **Rekomendacja:** Rozważyć usunięcie tej linii, jeśli nie ma udokumentowanego specyficznego przypadku, który by jej wymagał (np. obsługa bardzo starych lub niestandardowych systemów plików zwracających `bytes` w nietypowy sposób). Jej obecność nie jest szkodliwa, ale może być zbędna.

4.  **Blok `if __name__ == "__main__":`**
    - **Obserwacja:** Obecnie ten blok zawiera tylko instrukcję `pass`. Jeśli miał służyć do testów manualnych, warto albo go rozbudować o przykładowe użycie, albo usunąć, jeśli nie jest już potrzebny. W obecnej formie nie wnosi wartości.

#### 🧪 Plan testów (spójny z ETAP 2.5 dla `tests/unit/test_scanner.py`)

Implementacja testów jednostkowych dla tego modułu jest kluczowa i została szczegółowo zaplanowana w [ETAP 2.5: `tests/unit/test_scanner.py`](#etap-25-testsunitest_scannerpy). Po wprowadzeniu sugerowanej zmiany dotyczącej normalizacji wielkości liter w nazwach bazowych, testy powinny obejmować w szczególności:

- Parowanie plików z różną wielkością liter w nazwach bazowych (np. `Dokument.zip` + `dokument.jpg`).
- Poprawne działanie reguły "pierwszy znaleziony wygrywa" dla plików podglądu i archiwów.
- Obsługę różnych kombinacji rozszerzeń z `app_config`.
- Przypadki brzegowe: puste katalogi, katalogi tylko z plikami archiwów, katalogi tylko z plikami podglądów, brak pasujących par.
- Nazwy plików i katalogów zawierające znaki specjalne, Unicode.
- Pliki bez nazw bazowych (np. `.gitignore`) lub bez rozszerzeń.

#### 📊 Status tracking

- [x] Analiza kodu pliku przeprowadzona.
- [x] Zidentyfikowane problemy (głównie wielkość liter w nazwach bazowych) i sugestie udokumentowane.
- [x] Propozycja kluczowej zmiany w kodzie (normalizacja wielkości liter) opisana.
- [ ] Kod (sugerowane zmiany) zaimplementowany w `src/logic/scanner.py`.
- [x] Plan implementacji testów jednostkowych istnieje (ETAP 2.5) i jest spójny z analizą.
- [ ] Testy przeprowadzone (po implementacji zmian i testów).
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy).
- [ ] Gotowe do wdrożenia.

### ETAP 2.13: `src/logic/file_operations.py`

#### 📋 Identyfikacja

- **Plik główny:** `src/logic/file_operations.py`
- **Priorytet:** 🟡 ŚREDNI
- **Zależności:** `logging`, `os`, `shutil`, `PyQt6.QtCore` (QStandardPaths, QUrl), `PyQt6.QtGui` (QDesktopServices).
- **Uwaga:** Wstępna analiza (Etap 1) poprawnie zidentyfikowała potencjalnie nieużywany import `platform`.

#### 🔍 Analiza problemów i Proponowane zmiany

Moduł dostarcza podstawowych funkcji do operacji na plikach i folderach. Kod jest generalnie dobrze zorganizowany i czytelny.

1.  **Nieużywany import `platform`.**

    - **Problem:** Moduł importuje `platform`, ale nie wykorzystuje żadnej jego funkcjonalności.
    - **Rekomendacja:** Usunąć linię `import platform` z początku pliku.
      ```python
      # W src/logic/file_operations.py
      # Usunąć:
      # import platform
      ```

2.  **Podstawowa walidacja nazw folderów (w `create_folder` i `rename_folder`).**

    - **Obserwacja:** Funkcje te używają predefiniowanej listy `forbidden_chars` do walidacji nazw folderów. Jest to dobre podstawowe zabezpieczenie.
    - **Rekomendacja (niski priorytet, do rozważenia w przyszłości):** Dla bardziej zaawansowanej i wieloplatformowej walidacji nazw (np. obsługa maksymalnej długości, dodatkowych znaków specjalnych specyficznych dla OS, nazw zarezerwowanych), można by w przyszłości rozważyć integrację z dedykowaną biblioteką do walidacji ścieżek/nazw plików lub rozbudowę obecnej logiki. Na obecnym etapie istniejąca walidacja jest uznawana za wystarczającą dla podstawowych przypadków.

3.  **Implementacja funkcji:**

    - **`open_archive_externally`:** Solidna implementacja, wykorzystuje `QDesktopServices` z fallbackiem na `os.startfile` dla Windows. Poprawna obsługa błędów.
    - **`create_folder`:** Poprawnie używa `os.makedirs(exist_ok=True)`. Podstawowa walidacja nazwy.
    - **`rename_folder`:** Zawiera niezbędne sprawdzenia (istnienie folderu źródłowego, nieistnienie folderu docelowego o tej samej nazwie). Podstawowa walidacja nowej nazwy.
    - **`delete_folder`:** Poprawnie rozróżnia usuwanie pustego folderu (`os.rmdir`) od usuwania folderu z zawartością (`shutil.rmtree`). Logika obsługi przypadku, gdy folder nie istnieje, jest rozsądna.

4.  **Spójność z planem konsolidacji testów (ETAP 2.6):**
    - Analiza potwierdza, że funkcje `create_folder`, `rename_folder`, `delete_folder` (oraz `open_archive_externally`) są dobrze zdefiniowanymi operacjami, których testy powinny być skonsolidowane w `tests/unit/test_file_operations.py` zgodnie z planem z ETAP 2.6.

#### 🧪 Plan testów

Testy dla tego modułu powinny być zawarte w `tests/unit/test_file_operations.py` (zgodnie z planem konsolidacji). Powinny obejmować:

- **`open_archive_externally`:**
  - Próba otwarcia istniejącego pliku (trudne do automatycznej weryfikacji w teście jednostkowym, bardziej test manualny lub integracyjny; test jednostkowy może co najwyżej mockować `QDesktopServices.openUrl` i `os.startfile` i sprawdzać, czy są wołane z poprawnymi argumentami).
  - Próba otwarcia nieistniejącego pliku.
- **`create_folder`:**
  - Tworzenie nowego folderu.
  - Próba utworzenia folderu, który już istnieje (z `exist_ok=True` nie powinno być błędu).
  - Próba utworzenia folderu o nieprawidłowej nazwie (zawierającej `forbidden_chars` lub pustej).
  - Próba utworzenia folderu w nieistniejącym katalogu nadrzędnym.
- **`rename_folder`:**
  - Zmiana nazwy istniejącego folderu.
  - Próba zmiany nazwy nieistniejącego folderu.
  - Próba zmiany nazwy na nazwę, która już istnieje.
  - Próba zmiany nazwy na nieprawidłową nazwę.
- **`delete_folder`:**
  - Usuwanie pustego folderu (z `delete_content=False`).
  - Próba usunięcia niepustego folderu (z `delete_content=False` – oczekiwany błąd/`False`).
  - Usuwanie niepustego folderu (z `delete_content=True`).
  - Próba usunięcia nieistniejącego folderu (oczekiwane `True`).

#### 📊 Status tracking

- [x] Analiza kodu pliku przeprowadzona.
- [x] Zidentyfikowany nieużywany import (`platform`).
- [x] Funkcjonalność pozostałych elementów oceniona jako poprawna.
- [x] Plan konsolidacji testów (ETAP 2.6) jest spójny z zawartością tego modułu.
- [ ] Kod (usunięcie importu `platform`) zaimplementowany w `src/logic/file_operations.py`.
- [ ] Testy (w ramach `tests/unit/test_file_operations.py`) zaimplementowane/zaktualizowane.
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy).
- [ ] Gotowe do wdrożenia.

### ETAP 2.14: `src/logic/metadata_manager.py` (Analiza warunkowa)

#### 📋 Identyfikacja

- **Plik główny:** `src/logic/metadata_manager.py`
- **Priorytet:** 🟡 ŚREDNI
- **Zależności:** `json`, `logging`, `os`, `shutil`, `tempfile`, `typing`.
- **Uwaga:** Analiza jest częściowo warunkowa z powodu niemożności uzyskania pełnej zawartości pliku za pomocą dostępnych narzędzi (otrzymano linie 1-200 z 231). Dotyczy to w szczególności pełnej implementacji funkcji `apply_metadata_to_file_pairs` oraz ostatecznego potwierdzenia użycia `get_absolute_path` w kodzie produkcyjnym tego modułu.

#### 🔍 Analiza problemów i Proponowane zmiany (na podstawie dostępnego fragmentu)

Moduł odpowiada za zarządzanie metadanymi par plików, zapisując je w pliku `metadata.json` w podkatalogu `.app_metadata` folderu roboczego.

1.  **Implementacja kluczowych funkcji (widoczna część):**

    - `get_metadata_path()`: Poprawnie tworzy ścieżkę do pliku metadanych.
    - `get_relative_path()`: Poprawnie konwertuje ścieżki absolutne na względne, co jest kluczowe dla przenośności metadanych. Używana w `save_metadata` i na początku `apply_metadata_to_file_pairs`.
    - `load_metadata()`: Solidnie wczytuje dane JSON, obsługuje brak pliku (zwraca domyślną strukturę) i błędy parsowania.
    - `save_metadata()`: Implementuje bezpieczny, atomowy zapis (przez plik tymczasowy), co jest bardzo dobrą praktyką. Aktualizuje istniejące metadane, zamiast je całkowicie nadpisywać. Używa ścieżek względnych jako kluczy.

2.  **Funkcja `get_absolute_path(relative_path: str, base_path: str) -> str`**:

    - **Obserwacja:** Funkcja jest zdefiniowana w module i posiada odpowiadający jej test w `tests/unit/test_metadata_manager.py` (co potwierdziło wyszukiwanie `grep`).
    - **Użycie w kodzie produkcyjnym (warunkowe):** W dostępnym fragmencie kodu `metadata_manager.py` (linie 1-200) nie stwierdzono jej użycia. Wstępna analiza z Etapu 1 również sugerowała, że może być nieużywana w kodzie aplikacji.
    - **Rekomendacja (warunkowa):** Jeśli analiza pełnego kodu `apply_metadata_to_file_pairs` oraz pozostałej części projektu nie wykaże jej użycia w logice produkcyjnej, należy rozważyć jej usunięcie (wraz z testem), aby uniknąć utrzymywania potencjalnie martwego kodu. Jeśli jednak jest używana, należy udokumentować jej rolę.

3.  **Funkcja `apply_metadata_to_file_pairs` (analiza fragmentu i domniemania):**

    - **Logika:** Wczytuje metadane, a następnie (w brakującej części) powinna iterować po `file_pairs_list` i dla każdego obiektu `FilePair` próbować zastosować zapisane metadane (is_favorite, stars, color_tag).
    - **Rekomendacja (dla brakującej części kodu):** Kluczowe jest, aby podczas odczytywania wartości z załadowanego słownika metadanych (np. `pair_data = metadata['file_pairs'].get(relative_archive_path)`), dostęp do poszczególnych pól (np. `pair_data.get('stars', 0)`) odbywał się w sposób bezpieczny (np. z użyciem `dict.get(key, default_value)`). Zapobiegnie to błędom `KeyError`, jeśli plik metadanych jest niekompletny, pochodzi ze starszej wersji aplikacji lub został ręcznie zmodyfikowany.

4.  **Ogólna ocena (na podstawie fragmentu):**
    - Moduł wydaje się dobrze zaprojektowany pod kątem przechowywania metadanych w sposób przenośny (ścieżki względne).
    - Obsługa błędów w widocznych funkcjach jest na dobrym poziomie.
    - Zastosowanie atomowego zapisu jest istotnym plusem.

#### 🧪 Plan testów

Testy dla tego modułu (`tests/unit/test_metadata_manager.py`) zostały w Etapie 1 ocenione jako kompleksowe. Na podstawie obecnej analizy, testy powinny weryfikować (lub już weryfikują):

- Poprawne tworzenie ścieżek (`get_metadata_path`, `get_relative_path`, `get_absolute_path` - jeśli pozostaje).
- Logikę `load_metadata`: wczytywanie istniejącego pliku, tworzenie domyślnej struktury przy braku pliku, odporność na błędy JSON.
- Logikę `save_metadata`: tworzenie pliku i katalogu, poprawny zapis danych, aktualizacja istniejących wpisów, atomowość zapisu.
- Logikę `apply_metadata_to_file_pairs` (po uzyskaniu pełnego kodu): poprawne przypisywanie metadanych do obiektów `FilePair`, obsługa braku metadanych dla niektórych par, odporność na brakujące klucze w danych metadanych.
- Poprawną obsługę ścieżek względnych i absolutnych.

#### 📊 Status tracking

- [x] Analiza częściowa kodu pliku przeprowadzona.
- [ ] **Konieczne uzyskanie pełnego kodu `apply_metadata_to_file_pairs` do pełnej analizy.**
- [x] Problem potencjalnie nieużywanej funkcji `get_absolute_path` zidentyfikowany (wymaga ostatecznej weryfikacji).
- [x] Sugestie dotyczące bezpiecznego odczytu danych w `apply_metadata_to_file_pairs` sformułowane.
- [ ] Kod (ewentualne usunięcie `get_absolute_path` lub poprawki w `apply_metadata_to_file_pairs`) zaimplementowany.
- [ ] Testy zaktualizowane (jeśli zmiany w kodzie tego wymagają).
- [ ] Dokumentacja zaktualizowana.
- [ ] Gotowe do wdrożenia.

### ETAP 2.15: `src/logic/filter_logic.py`

#### 📋 Identyfikacja

- **Plik główny:** `src/logic/filter_logic.py`
- **Priorytet:** 🟡 ŚREDNI
- **Zależności:** `logging`, `typing`, `src.models.file_pair.FilePair`.

#### 🔍 Analiza problemów i Proponowane zmiany

Moduł zawiera funkcję `filter_file_pairs` odpowiedzialną za filtrowanie listy obiektów `FilePair` na podstawie zdefiniowanych kryteriów. Implementacja logiki filtrowania jest poprawna i czytelna.

1.  **Krytyczny: Brak dedykowanych testów jednostkowych.**

    - **Problem:** W projekcie brakuje testów jednostkowych dla logiki filtrowania zawartej w `filter_file_pairs`. Jest to kluczowa funkcjonalność z punktu widzenia użytkownika, a jej poprawne działanie w różnych scenariuszach powinno być weryfikowane automatycznie.
    - **Rekomendacja:** Stworzyć nowy plik testowy, np. `tests/unit/test_filter_logic.py`, i zaimplementować w nim kompleksowy zestaw testów dla funkcji `filter_file_pairs`. Testy powinny obejmować:
      - Przypadek z pustą listą `file_pairs_list`.
      - Przypadek z pustym słownikiem `filter_criteria` (oczekiwane zwrócenie oryginalnej listy).
      - Przypadek z niepełnym słownikiem `filter_criteria` (testowanie poprawnego użycia wartości domyślnych dla brakujących kluczy).
      - Testowanie każdego kryterium indywidualnie:
        - `show_favorites_only=True` (z listą zawierającą ulubione i nieulubione pary).
        - `show_favorites_only=False` (powinno działać jak brak filtra ulubionych).
        - `min_stars` z różnymi wartościami (np. 0, 1, 3, 5) i parami o różnej liczbie gwiazdek.
        - `required_color_tag` z wartościami:
          - `"ALL"` (brak filtra kolorów).
          - `"__NONE__"` (pary bez tagu kolorystycznego vs. pary z tagami).
          - Konkretny kod HEX (np. `"#FF0000"`) – testując dopasowanie (również niewrażliwe na wielkość liter i z dodatkowymi białymi znakami w tagu, np. `"#ff0000 "`) oraz brak dopasowania.
      - Testowanie kombinacji wielu aktywnych kryteriów (np. ulubione ORAZ `min_stars=3` ORAZ `required_color_tag="#1E88E5"`).
      - Weryfikacja, czy funkcja zwraca nową listę i nie modyfikuje oryginalnej `file_pairs_list`.
      - Testy z parami, gdzie niektóre atrybuty (np. `color_tag`) mogą być `None`.

2.  **Logowanie DEBUG w pętli.**

    - **Obserwacja:** Funkcja `filter_file_pairs` zawiera bardzo szczegółowe logowanie na poziomie DEBUG wewnątrz pętli iterującej po parach plików. Jest to bardzo pomocne przy diagnozowaniu, ale przy dużej liczbie plików i włączonym logowaniu DEBUG może mieć zauważalny wpływ na wydajność filtrowania.
    - **Rekomendacja:** To bardziej uwaga niż problem wymagający natychmiastowej zmiany. Logika jest poprawna. Warto jednak pamiętać, aby w środowisku produkcyjnym domyślny poziom logowania był ustawiony wyżej niż DEBUG (np. INFO lub WARNING), co jest standardową praktyką.

3.  **Potencjalne rozszerzenie: Filtr tekstowy (sugestia rozwojowa).**
    - **Obserwacja:** Obecne kryteria nie obejmują filtrowania po nazwie pliku (tekstowego).
    - **Rekomendacja (niski priorytet, sugestia na przyszłość):** Jeśli aplikacja miałaby zyskać funkcję wyszukiwania tekstowego, można by rozważyć rozszerzenie słownika `filter_criteria` o klucz np. `"text_query": str` i dodanie odpowiedniej logiki w funkcji `filter_file_pairs` do sprawdzania, czy `text_query` (np. w sposób niewrażliwy na wielkość liter) zawiera się w nazwie bazowej pary (`pair.get_base_name()`).

#### 🧪 Plan testów

Jak opisano w punkcie 1, należy stworzyć nowy plik testowy (np. `tests/unit/test_filter_logic.py`) i zaimplementować w nim scenariusze testowe pokrywające wszystkie aspekty działania funkcji `filter_file_pairs`. Przykładowe obiekty `FilePair` używane w testach powinny mieć zróżnicowane atrybuty (`is_favorite`, `stars`, `color_tag`, nazwa bazowa).

#### 📊 Status tracking

- [x] Analiza kodu pliku przeprowadzona.
- [x] Logika filtrowania oceniona jako poprawna i robustna dla zdefiniowanych kryteriów.
- [x] **Krytyczna potrzeba implementacji testów jednostkowych zidentyfikowana.**
- [ ] Nowy plik testowy (np. `tests/unit/test_filter_logic.py`) utworzony i testy zaimplementowane.
- [ ] Kod (ewentualne drobne poprawki, jeśli wynikną z pisania testów) zaktualizowany.
- [ ] Dokumentacja (głównie docstring funkcji `filter_file_pairs` jest już dobry) sprawdzona.
- [ ] Gotowe do wdrożenia (po implementacji i pomyślnym przejściu testów).

### ETAP 2.16: `tests/conftest.py`

#### 📋 Identyfikacja

- **Plik główny:** `tests/conftest.py`
- **Priorytet:** 🟢 NISKI
- **Zależności:** `pytest`.

#### 🔍 Analiza problemów i Proponowane zmiany

Plik `tests/conftest.py` służy do definiowania współdzielonych fixture'ów dla testów `pytest`.

1.  **Nieużywana fixture `sample_fixture`.**
    - **Problem:** Plik definiuje fixture `@pytest.fixture(scope='session') def sample_fixture(): return "sample data"`. Wyszukiwanie w projekcie wykazało, że ta fixture nie jest używana w żadnym teście.
    - **Konsekwencje:** Obecność nieużywanego kodu (martwy kod) zaciemnia obraz i może prowadzić do nieporozumień w przyszłości.
    - **Rekomendacja:** Usunąć całą definicję `sample_fixture` z pliku `tests/conftest.py`. Plik może pozostać pusty (jeśli nie ma innych współdzielonych fixture'ów) lub zawierać tylko niezbędne importy, jeśli w przyszłości zostaną dodane nowe, używane fixture'y.

#### 🧪 Plan testów

Nie dotyczy bezpośrednio, ponieważ zmiana polega na usunięciu nieużywanego kodu. Po usunięciu należy jedynie upewnić się, że wszystkie testy nadal przechodzą (co powinno mieć miejsce, skoro fixture nie była używana).

#### 📊 Status tracking

- [x] Analiza kodu pliku przeprowadzona.
- [x] Zidentyfikowano nieużywaną fixture.
- [x] Propozycja usunięcia sformułowana.
- [ ] Kod (usunięcie `sample_fixture`) zaimplementowany w `tests/conftest.py`.
- [ ] Testy (ponowne uruchomienie wszystkich testów) przeprowadzone w celu potwierdzenia braku regresji.
- [ ] Dokumentacja zaktualizowana (nie dotyczy).
- [ ] Gotowe do wdrożenia.

### ETAP 2.17: `src/app_config.py`

#### 📋 Identyfikacja

- **Plik główny:** `src/app_config.py`
- **Priorytet:** 🟢 NISKI (choć proponowana zmiana ma wpływ na spójność w innych modułach)
- **Zależności:** Obecnie brak, po zmianie: `collections.OrderedDict`.

#### 🔍 Analiza problemów i Proponowane zmiany

Plik `src/app_config.py` służy jako centralne miejsce dla konfiguracji aplikacji, takiej jak listy obsługiwanych rozszerzeń plików.

1.  **Styl inicjalizacji listy `SUPPORTED_PREVIEW_EXTENSIONS`.**

    - **Problem:** Lista `SUPPORTED_PREVIEW_EXTENSIONS` jest budowana poprzez wielokrotne wywołania metody `append()`, co jest mniej czytelne i bardziej rozwlekłe niż bezpośrednia definicja listy.
    - **Rekomendacja:** Zmienić sposób inicjalizacji na bezpośrednie przypisanie listy.
      ```python
      # W src/app_config.py
      # Zamiast:
      # SUPPORTED_PREVIEW_EXTENSIONS = []
      # SUPPORTED_PREVIEW_EXTENSIONS.append(".jpg")
      # SUPPORTED_PREVIEW_EXTENSIONS.append(".jpeg")
      # ... itd.
      # Proponowane:
      SUPPORTED_PREVIEW_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff"]
      ```

2.  **Centralizacja definicji predefiniowanych kolorów (Problem zidentyfikowany w ETAP 2.9).**

    - **Problem:** Definicje predefiniowanych kolorów używanych do tagowania i filtrowania są obecnie zduplikowane i nieznacznie niespójne w różnych modułach interfejsu użytkownika (głównie `src/ui/widgets/file_tile_widget.py` i `src/ui/main_window.py`). Utrudnia to zarządzanie paletą kolorów i może prowadzić do błędów.
    - **Rekomendacja:**

      1.  Dodać do `src/app_config.py` nową, centralną stałą przechowującą ujednoliconą definicję predefiniowanych tagów kolorystycznych. Zaleca się użycie `collections.OrderedDict` dla zachowania kolejności.

          ```python
          # Propozycja dodania do src/app_config.py:
          from collections import OrderedDict # Należy dodać ten import

          # ... (istniejące definicje rozszerzeń) ...

          UI_PREDEFINED_COLOR_TAGS = OrderedDict([
              ("Brak", ""),  # Standardowa reprezentacja braku tagu
              ("Czerwony", "#E53935"),
              ("Zielony", "#43A047"),
              ("Niebieski", "#1E88E5"),
              ("Żółty", "#FDD835"),
              ("Fioletowy", "#8E24AA"),
              ("Czarny", "#000000"),
              # Można tu w przyszłości łatwo dodawać/modyfikować kolory
          ])
          ```

      2.  Zmodyfikować `src/ui/widgets/file_tile_widget.py` (klasa `FileTileWidget`), aby importował i używał `UI_PREDEFINED_COLOR_TAGS` z `app_config` zamiast własnej, lokalnej definicji `PREDEFINED_COLORS`.
      3.  Zmodyfikować `src/ui/main_window.py` (w miejscu, gdzie definiowane są opcje filtra kolorów), aby również korzystał z `UI_PREDEFINED_COLOR_TAGS` z `app_config`. W przypadku filtra, `MainWindow` może dynamicznie dodać opcję "Wszystkie kolory" (z wartością np. "ALL") na początek listy generowanej na podstawie `UI_PREDEFINED_COLOR_TAGS`.

    - **Korzyści:** Utrzymanie spójności kolorów w całej aplikacji, łatwiejsze zarządzanie paletą (zmiana w jednym miejscu), redukcja redundancji kodu.

#### 🧪 Plan testów

- Po zmianie stylu inicjalizacji `SUPPORTED_PREVIEW_EXTENSIONS`, upewnić się, że lista nadal zawiera te same, poprawne wartości (testy funkcjonalne skanera powinny to wychwycić pośrednio).
- Po centralizacji `UI_PREDEFINED_COLOR_TAGS`:
  - Sprawdzić, czy `QComboBox` w `FileTileWidget` poprawnie wyświetla kolory w oczekiwanej kolejności.
  - Sprawdzić, czy filtr kolorów w `MainWindow` działa poprawnie i oferuje spójne opcje.
  - Testować przypisywanie i odczytywanie tagów kolorystycznych dla `FilePair`.

#### 📊 Status tracking

- [x] Analiza kodu pliku przeprowadzona.
- [x] Zidentyfikowano drobny problem stylistyczny oraz potrzebę centralizacji konfiguracji kolorów.
- [x] Propozycje zmian sformułowane.
- [ ] Kod (zmiany w `src/app_config.py` oraz w `file_tile_widget.py` i `main_window.py` w celu użycia nowej stałej) zaimplementowany.
- [ ] Testy (manualne UI oraz ewentualne testy jednostkowe logiki korzystającej z kolorów) przeprowadzone.
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy).
- [ ] Gotowe do wdrożenia.
