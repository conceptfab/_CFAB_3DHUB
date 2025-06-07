## ETAP 1: src/logic/scanner.py

### 📋 Identyfikacja

- **Plik główny:** `src/logic/scanner.py`
- **Priorytet:** 🔴 WYSOKI PRIORYTET
- **Zależności:**
  - `src/app_config.py` (dla definicji rozszerzeń)
  - `src/models/file_pair.py` (dla tworzenia obiektów FilePair)
  - `src/utils/path_utils.py` (dla operacji na ścieżkach)
  - `src/ui/delegates/workers.py` (pośrednio, do wywołania w tle i raportowania postępu - nie jest bezpośrednio importowany, ale logika skanowania powinna być tam przeniesiona lub wykorzystywać sygnały do komunikacji z UI)

### 🔍 Analiza problemów

1.  **Błędy krytyczne:**

    - Brak bezpośredniej obsługi błędów I/O w `get_directory_modification_time` wewnątrz pętli `os.scandir` - błąd dla jednego pliku może przerwać sprawdzanie reszty.
    - Potencjalne problemy z wydajnością przy bardzo dużej liczbie plików/folderów z powodu rekurencyjnego charakteru `_walk_directory` i braku jawnego raportowania postępu do UI, co może sprawiać wrażenie "zamrożenia" aplikacji.
    - Cache `_scan_cache` i `_files_cache` są globalnymi zmiennymi, co może prowadzić do problemów w środowiskach wielowątkowych, jeśli nie są odpowiednio synchronizowane (choć w obecnej strukturze wydaje się, że operacje na nich są wykonywane w jednym wątku skanującym).
    - Funkcja `_cleanup_old_cache_entries` iteruje po `list(_files_cache.items())` i usuwa elementy z `_files_cache`. Chociaż tworzenie listy elementów powinno zapobiec problemom z modyfikacją podczas iteracji, warto to dokładnie zweryfikować pod kątem bezpieczeństwa wątków, jeśli cache miałby być dostępny z wielu wątków.

2.  **Optymalizacje:**

    - **Raportowanie postępu:** Kluczowa funkcjonalność do dodania. Skanowanie (zwłaszcza `collect_files` i `_walk_directory`) powinno emitować sygnały o postępie (np. liczba przeskanowanych folderów/plików, aktualnie skanowany folder), które mogą być przechwytywane przez UI do aktualizacji paska postępu i etykiety statusu. To wymaga integracji z systemem wątków (np. `QRunnable` w `workers.py`) i mechanizmem sygnałów/slotów Qt.
    - **Przerwanie skanowania:** Mechanizm `interrupt_check` jest obecny, ale jego integracja z UI (np. przycisk "Anuluj") musi być zapewniona. Sygnał przerwania powinien być efektywnie propagowany.
    - **Cache:**
      - Strategia czyszczenia cache (`_cleanup_old_cache_entries`) jest oparta na liczbie wpisów i wieku. Można rozważyć bardziej zaawansowane strategie (np. LRU - Least Recently Used), choć obecna może być wystarczająca.
      - W `collect_files`, jeśli cache jest nieaktualny (`not is_cache_valid`), stary wpis jest usuwany. To dobre, ale warto upewnić się, że `get_directory_modification_time` jest wystarczająco szybkie, aby nie spowalniać tego procesu.
      - Rozważyć serializację cache na dysk przy zamykaniu aplikacji i odczyt przy starcie, aby przyspieszyć pierwsze skanowanie po uruchomieniu (jeśli to pożądane).
    - **Operacje na ścieżkach:** Użycie `pathlib.Path` może w niektórych miejscach uprościć kod i poprawić czytelność operacji na ścieżkach, chociaż obecne użycie `os.path` jest również poprawne.
    - **Parowanie plików:** Strategia `"best_match"` w `create_file_pairs` jest zaznaczona jako TODO. Jeśli jest to ważna funkcjonalność, należy ją zaimplementować. Obecnie działa jak `"first_match"`.
    - **Zbieranie plików:** W `_walk_directory` najpierw przetwarzane są pliki, a potem foldery. To standardowe podejście. Można by rozważyć przetwarzanie plików i folderów w jednej pętli po `os.scandir`, jeśli miałoby to przynieść korzyści (np. minimalnie mniejszy narzut na iterację), ale obecne rozwiązanie jest czytelne.

3.  **Refaktoryzacja:**
    - **Przeniesienie do wątku roboczego:** Cała logika skanowania (`scan_folder_for_pairs` i funkcje pomocnicze) powinna być hermetyzowana w klasie dziedziczącej po `QRunnable` (lub podobnej) i zarządzana przez `src.ui.delegates.workers.QThreadPool`. To pozwoli na asynchroniczne wykonywanie skanowania i efektywne raportowanie postępu/wyników do UI za pomocą sygnałów.
      - Klasa Workera powinna przyjmować parametry skanowania (ścieżka, głębokość, strategia, etc.) w konstruktorze.
      - Powinna emitować sygnały: `progress_updated(int percent, str message)`, `scan_finished(list_file_pairs, list_unpaired_archives, list_unpaired_previews)`, `scan_error(str error_message)`, `scan_interrupted()`.
    - **Typowanie:** Plik już używa type hints, co jest bardzo dobre. Należy utrzymać i weryfikować ich poprawność.
    - **Logowanie:** Logowanie jest używane, co jest dobre. Należy upewnić się, że poziomy logów są odpowiednie i dostarczają wystarczających informacji diagnostycznych.
    - **Konfiguracja cache:** Parametry `MAX_CACHE_ENTRIES` i `MAX_CACHE_AGE_SECONDS` są globalne. Można rozważyć ich przeniesienie do `app_config.py`, aby były konfigurowalne centralnie.
    - **Obsługa wyjątków:** W `_walk_directory` wyjątki `PermissionError` i `OSError` są łapane i logowane, co pozwala na kontynuację skanowania innych części systemu plików. To dobre podejście.

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

1.  **Skanowanie prostego folderu:**
    - Utwórz folder z kilkoma plikami archiwów (np. `.zip`, `.rar`) i odpowiadającymi im plikami podglądów (np. `.jpg`, `.png`) o takich samych nazwach bazowych.
    - Uruchom `scan_folder_for_pairs` ze strategią `first_match`.
    - Sprawdź, czy wszystkie pary zostały poprawnie zidentyfikowane.
    - Sprawdź, czy nie ma niesparowanych plików.
2.  **Skanowanie z niesparowanymi plikami:**
    - Dodaj do folderu testowego pliki archiwów bez podglądów i pliki podglądów bez archiwów.
    - Uruchom `scan_folder_for_pairs`.
    - Sprawdź, czy sparowane pliki są poprawne, a niesparowane archiwa i podglądy są poprawnie zidentyfikowane w odpowiednich listach.
3.  **Skanowanie z różnymi strategiami parowania:**
    - Utwórz folder, gdzie jedno archiwum ma wiele pasujących podglądów (np. `plik.zip`, `plik.jpg`, `plik.png`).
    - Przetestuj strategię `first_match` (powinna sparować z pierwszym znalezionym podglądem).
    - Przetestuj strategię `all_combinations` (powinna utworzyć pary ze wszystkimi podglądami).
4.  **Skanowanie z rekursją (max_depth):**
    - Utwórz strukturę podfolderów z plikami do sparowania.
    - Przetestuj `scan_folder_for_pairs` z `max_depth = 0` (tylko bieżący folder), `max_depth = 1` (bieżący i jeden poziom w głąb) oraz `max_depth = -1` (pełna rekursja).
    - Sprawdź poprawność wyników dla każdej głębokości.
5.  **Obsługa błędów (np. brak dostępu):**
    - Utwórz folder/plik, do którego program nie ma uprawnień odczytu.
    - Uruchom skanowanie nadrzędnego folderu.
    - Sprawdź, czy błąd jest logowany i czy skanowanie kontynuuje dla dostępnych części.
6.  **Test przerwania skanowania:**
    - Przygotuj duże drzewo katalogów do skanowania.
    - Zaimplementuj prostą funkcję `interrupt_check`, która po kilku sekundach zwraca `True`.
    - Uruchom `scan_folder_for_pairs` i sprawdź, czy wyjątek `ScanningInterrupted` jest rzucany i czy skanowanie faktycznie się zatrzymuje.

**Test integracji:**

1.  **Integracja z UI (po refaktoryzacji do wątku):**
    - Uruchom skanowanie z poziomu UI.
    - Sprawdź, czy pasek postępu i etykieta statusu są aktualizowane na bieżąco.
    - Sprawdź, czy przycisk "Anuluj" poprawnie przerywa skanowanie.
    - Sprawdź, czy wyniki (listy par i niesparowanych plików) są poprawnie przekazywane i wyświetlane w UI.
2.  **Integracja z cache:**
    - Uruchom skanowanie folderu. Sprawdź czas wykonania.
    - Uruchom skanowanie tego samego folderu ponownie (z `use_cache=True` i bez zmian w folderze). Sprawdź, czy czas wykonania jest znacznie krótszy (cache hit).
    - Zmodyfikuj plik w folderze (zmień czas modyfikacji).
    - Uruchom skanowanie ponownie. Sprawdź, czy cache jest odświeżany (cache miss, pełne skanowanie).
    - Przetestuj czyszczenie cache (`clear_cache()`) i jego wpływ na kolejne skanowanie.

**Test wydajności:**

1.  **Skanowanie dużego folderu:**
    - Przygotuj folder z tysiącami plików i wieloma podfolderami.
    - Zmierz czas wykonania `scan_folder_for_pairs` (bez cache i z cache).
    - Monitoruj użycie CPU i pamięci podczas skanowania.
    - Zidentyfikuj potencjalne wąskie gardła.
2.  **Wpływ głębokości skanowania:**
    - Zmierz czas skanowania dla różnych wartości `max_depth` na tym samym dużym folderze.
3.  **Wpływ strategii parowania:**
    - Zmierz czas skanowania dla różnych strategii parowania na folderze z wieloma możliwymi kombinacjami.

### 📊 Status tracking

- [ ] Kod zaimplementowany (zmiany dotyczące wątków, paska postępu, itp.)
- [ ] Testy podstawowe przeprowadzone
- [ ] Testy integracji przeprowadzone
- [ ] Testy wydajności przeprowadzone
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia (po implementacji i testach)

---

_Analiza pliku `src/logic/scanner.py` zakończona._

## ETAP 2: src/logic/file_operations.py

### 📋 Identyfikacja

- **Plik główny:** `src/logic/file_operations.py`
- **Priorytet:** 🔴 WYSOKI PRIORYTET
- **Zależności:**
  - `src/models/file_pair.py` (dla operacji na parach plików)
  - `src/utils/path_utils.py` (dla walidacji nazw, normalizacji ścieżek)
  - `PyQt6.QtCore.QUrl`, `PyQt6.QtGui.QDesktopServices` (do otwierania plików)
  - `src/ui/delegates/workers.py` (pośrednio, dla operacji w tle i raportowania postępu - nie jest bezpośrednio importowany, ale operacje I/O powinny być tam przeniesione lub wykorzystywać sygnały do komunikacji z UI)

### 🔍 Analiza problemów

1.  **Błędy krytyczne:**

    - **Blokowanie UI:** Wszystkie operacje na plikach (tworzenie, zmiana nazwy, usuwanie folderów/plików, parowanie, przenoszenie) są synchroniczne. Przy operacjach na dużych plikach, wolnych nośnikach lub dużej liczbie plików, będą blokować główny wątek aplikacji, prowadząc do "zamrożenia" interfejsu użytkownika.
    - **Transakcyjność operacji:** W funkcjach `rename_file_pair` i `move_file_pair` istnieje próba implementacji mechanizmu rollback w przypadku błędu po wykonaniu części operacji (np. zmiana nazwy archiwum się udała, ale podglądu już nie). Jednakże, w przypadku krytycznego błędu podczas samego rollbacku (np. `os.rename` lub `shutil.move` rzuci wyjątek podczas próby przywrócenia), stan plików może pozostać niespójny, a logowany jest `CRITICAL ERROR`. Chociaż jest to rzadkie, warto rozważyć bardziej zaawansowane strategie obsługi takich sytuacji, jeśli to możliwe (np. tymczasowe kopie przed operacjami krytycznymi).
    - W `manually_pair_files`, jeśli `new_preview_path.lower() == preview_path.lower()`, a plik `new_preview_path` istnieje, to uznawane jest to za sytuację, gdzie plik podglądu ma już docelową nazwę (możliwe różnice wielkości liter). Jednakże, jeśli system plików jest case-sensitive, a pliki `preview_path` i `new_preview_path` to dwa różne pliki, których nazwy różnią się tylko wielkością liter, to `os.path.exists(new_preview_path)` będzie `True`, ale `new_preview_path.lower() == preview_path.lower()` może nie być wystarczające do stwierdzenia, że to ten sam plik. To skrajny przypadek, ale warto mieć na uwadze.

2.  **Optymalizacje:**

    - **Asynchroniczność i raportowanie postępu:** Podobnie jak w `scanner.py`, wszystkie operacje I/O powinny być wykonywane w osobnych wątkach roboczych (`QRunnable` zarządzane przez `QThreadPool` z `workers.py`).
      - Każda operacja (np. kopiowanie, usuwanie wielu plików, przenoszenie) powinna emitować sygnały o postępie (np. `progress_updated(int percent, str message_details)`), które UI może wykorzystać do aktualizacji paska postępu i etykiety statusu.
      - Powinny być emitowane sygnały o zakończeniu operacji (`operation_successful(str message)`, `operation_failed(str error_message)`).
      - Należy zapewnić możliwość przerwania długotrwałych operacji przez użytkownika (np. przycisk "Anuluj").
    - **Operacje wsadowe (Batch operations):** Jeśli aplikacja pozwala na operacje na wielu plikach/parach jednocześnie (np. usuwanie wielu zaznaczonych par), logika powinna być zoptymalizowana pod kątem takich operacji, minimalizując liczbę wywołań funkcji i efektywnie raportując zbiorczy postęp.
    - **Obsługa błędów:** Obecnie funkcje zwracają `True/False` lub `None` w przypadku błędu i logują problem. Dla operacji wykonywanych w tle, lepszym podejściem jest rzucanie wyjątków, które są łapane w wątku roboczym, a następnie emitowanie sygnału błędu z odpowiednią informacją do UI. To pozwala na bardziej elastyczne informowanie użytkownika.
      - W `move_file_pair` rzucany jest `FileExistsError` - to dobry wzorzec, który można by zastosować szerzej.
    - **Walidacja:** Użycie `is_valid_filename` jest dobre. Należy upewnić się, że wszystkie dane wejściowe od użytkownika (np. nowe nazwy) są odpowiednio walidowane przed próbą wykonania operacji na systemie plików.

3.  **Refaktoryzacja:**
    - **Przeniesienie do wątków roboczych:** Jak wspomniano, kluczowa refaktoryzacja to adaptacja funkcji do pracy w tle. Można stworzyć dedykowane klasy `QRunnable` dla różnych typów operacji (np. `RenameFileWorker`, `DeleteFileWorker`, `MoveFileWorker`) lub bardziej generyczną klasę workera, która przyjmuje funkcję operacji i jej argumenty.
    - **Ujednolicenie obsługi błędów:** Zamiast zwracania `bool` lub `None`, funkcje operujące na plikach (po refaktoryzacji do wątków) powinny rzucać specyficzne wyjątki (np. `FileNotFoundError`, `PermissionError`, `FileOperationFailedError`), które worker może złapać i przekazać do UI przez sygnał.
    - **Funkcja `open_archive_externally`:** Używa `QDesktopServices.openUrl`, co jest dobrym podejściem. Fallback na `os.startfile` dla Windows jest rozsądny. Można rozważyć dodanie logowania, jeśli `QUrl.fromLocalFile` zwróci niepoprawny URL dla jakiejś ścieżki.
    - **Funkcje dotyczące folderów (`create_folder`, `rename_folder`, `delete_folder`):** Są stosunkowo proste. Główna zmiana to ich adaptacja do pracy asynchronicznej, jeśli mogą być wywoływane na potencjalnie wolnych zasobach lub w kontekście operacji, które użytkownik może chcieć anulować.
    - **Funkcja `manually_pair_files`:** Logika zmiany nazwy pliku podglądu jest dość złożona. Należy ją dokładnie przetestować, zwłaszcza przypadki brzegowe (różnice wielkości liter, istnienie plików). Przeniesienie do wątków jest tu również istotne, ponieważ zmiana nazwy to operacja I/O.
    - **Funkcje przeniesione z `FilePair` (`rename_file_pair`, `delete_file_pair`, `move_file_pair`):** Te funkcje operują na parach i mają logikę rollbacku. Przeniesienie ich do wątków z zachowaniem (lub ulepszeniem) tej logiki będzie kluczowe. `move_file_pair` już rzuca `FileExistsError`, co jest dobrym kierunkiem.

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

1.  **Otwieranie archiwum:**
    - Przetestuj `open_archive_externally` z poprawną ścieżką do pliku archiwum (np. `.zip`, `.rar`). Sprawdź, czy domyślny program się uruchamia.
    - Przetestuj z nieistniejącą ścieżką (powinien zwrócić `False` i zalogować błąd).
2.  **Operacje na folderach:**
    - `create_folder`: Utwórz nowy folder, utwórz folder, który już istnieje (`exist_ok=True`), spróbuj utworzyć z nieprawidłową nazwą.
    - `rename_folder`: Zmień nazwę folderu, spróbuj zmienić na nazwę, która już istnieje, spróbuj zmienić nazwę nieistniejącego folderu.
    - `delete_folder`: Usuń pusty folder, spróbuj usunąć niepusty folder (z `delete_content=False` - powinien zwrócić błąd), usuń niepusty folder (z `delete_content=True`).
3.  **Ręczne parowanie (`manually_pair_files`):**
    - Sparuj pliki o takich samych nazwach bazowych.
    - Sparuj pliki o różnych nazwach bazowych (podgląd powinien zmienić nazwę).
    - Sparuj, gdy docelowa nazwa podglądu już istnieje (powinien być błąd).
    - Sparuj, gdy nazwy różnią się tylko wielkością liter (powinno zadziałać poprawnie).
    - Przetestuj z nieistniejącymi plikami archiwum lub podglądu.
4.  **Operacje na parach plików (`rename_file_pair`, `delete_file_pair`, `move_file_pair`):**
    - `rename_file_pair`:
      - Zmień nazwę pary (archiwum i podgląd).
      - Spróbuj zmienić nazwę, gdy nowe nazwy plików już istnieją.
      - Przetestuj przypadek, gdy zmiana nazwy archiwum się powiedzie, a podglądu nie (powinien nastąpić rollback).
      - Zmień nazwę tylko archiwum (gdy `old_preview_path` jest `None`).
    - `delete_file_pair`:
      - Usuń parę (archiwum i podgląd).
      - Usuń, gdy podgląd nie istnieje.
      - Usuń, gdy archiwum nie istnieje (a podgląd tak).
      - Spróbuj usunąć nieistniejące pliki.
    - `move_file_pair`:
      - Przenieś parę do innego folderu.
      - Spróbuj przenieść do nieistniejącego folderu docelowego.
      - Spróbuj przenieść, gdy pliki o tych nazwach już istnieją w folderze docelowym (powinien być `FileExistsError`).
      - Przetestuj rollback, jeśli przeniesienie archiwum się powiedzie, a podglądu nie.

**Test integracji (po refaktoryzacji do wątków):**

1.  **Operacje z UI:**
    - Wykonaj wszystkie operacje na plikach/folderach/parach z poziomu UI.
    - Sprawdź, czy pasek postępu (jeśli dotyczy długich operacji) i komunikaty o statusie są poprawnie wyświetlane.
    - Sprawdź, czy UI pozostaje responsywne podczas operacji.
    - Przetestuj anulowanie długotrwałych operacji.
2.  **Obsługa błędów w UI:**
    - Spowodź błędy (np. brak uprawnień, plik zajęty, nieistniejąca ścieżka, próba nadpisania istniejącego pliku bez potwierdzenia) i sprawdź, czy są one czytelnie komunikowane użytkownikowi.

**Test wydajności:**

1.  **Operacje na dużej liczbie plików/dużych plikach:**
    - Przetestuj usuwanie/przenoszenia folderu z tysiącami małych plików.
    - Przetestuj przenoszenie/kopiowanie bardzo dużych plików (kilka GB).
    - Monitoruj czas operacji, użycie CPU/pamięci oraz responsywność UI.

### 📊 Status tracking

- [ ] Kod zaimplementowany (zmiany dotyczące wątków, paska postępu, obsługi błędów, itp.)
- [ ] Testy podstawowe przeprowadzone
- [ ] Testy integracji przeprowadzone
- [ ] Testy wydajności przeprowadzone
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia (po implementacji i testach)

---

_Analiza pliku `src/logic/file_operations.py` zakończona._

## ETAP 3: src/logic/metadata_manager.py

### 📋 Identyfikacja

- **Plik główny:** `src/logic/metadata_manager.py`
- **Priorytet:** 🟡 ŚREDNI (może wzrosnąć w zależności od wpływu na wydajność i stabilność)
- **Zależności:**
  - `sqlite3` (do obsługi bazy danych)
  - `json` (do serializacji/deserializacji niektórych pól, np. tagów)
  - `logging` (do logowania)
  - `src/models/file_pair.py` (prawdopodobnie do powiązania metadanych z obiektami `FilePair`)
  - `src/app_config.py` (potencjalnie dla ścieżki do bazy danych lub innych konfiguracji)

### 🔍 Analiza problemów

1.  **Błędy krytyczne/Potencjalne problemy:**

    - **Bezpieczeństwo wątków:** Dostęp do bazy danych SQLite z wielu wątków bez odpowiedniej serializacji lub użycia trybu WAL (Write-Ahead Logging) może prowadzić do błędów `OperationalError: database is locked` lub uszkodzenia danych. Jeśli operacje na metadanych będą wywoływane z wątków roboczych (np. po skanowaniu, podczas operacji na plikach), musi to być rozwiązane.
    - **Obsługa błędów SQL:** Należy dokładnie sprawdzić, czy wszystkie operacje na bazie danych (SELECT, INSERT, UPDATE, DELETE) mają odpowiednią obsługę wyjątków (`sqlite3.Error` i jego podklasy). Błędy SQL powinny być logowane, a aplikacja powinna sobie z nimi radzić w sposób przewidywalny.
    - **Iniekcja SQL:** Jeśli zapytania SQL są budowane przez konkatenację stringów z danymi wejściowymi, istnieje ryzyko iniekcji SQL. Należy bezwzględnie używać parametryzowanych zapytań (placeholdery `?`).
    - **Wydajność przy dużej bazie danych:** Brak odpowiednich indeksów na często przeszukiwanych kolumnach (np. `file_path`, `archive_path`, tagi) może prowadzić do znacznego spowolnienia zapytań.
    - **Schema migration:** Brak mechanizmu migracji schematu bazy danych w przypadku przyszłych zmian struktury.

2.  **Optymalizacje:**

    - **Indeksowanie:** Zidentyfikować i utworzyć indeksy na kolumnach używanych w klauzulach `WHERE`, `JOIN` i `ORDER BY`.
    - **Transakcje:** Operacje modyfikujące wiele rekordów lub wykonujące wiele powiązanych kroków powinny być opakowane w transakcje (`BEGIN TRANSACTION`, `COMMIT`/`ROLLBACK`).
    - **Zarządzanie połączeniem z bazą danych:** Ustandaryzować sposób zarządzania połączeniem (np. jedno połączenie per wątek lub globalne z odpowiednią synchronizacją).
    - **Asynchroniczność:** Czasochłonne interakcje z bazą danych powinny być wykonywane asynchronicznie w wątkach roboczych.
    - **Przechowywanie tagów/słów kluczowych:** Rozważyć użycie tabeli łączącej (many-to-many) dla tagów zamiast przechowywania ich jako JSON w jednej kolumnie, aby usprawnić wyszukiwanie.
    - **Optymalizacja bazy danych:** Rozważyć okresowe użycie komendy `VACUUM` (z ostrożnością).

3.  **Refaktoryzacja:**
    - **Warstwa abstrakcji (ORM Lite):** Rozważyć wprowadzenie lekkiej warstwy abstrakcji nad surowymi zapytaniami SQL.
    - **Struktura klasy `MetadataManager`:** Zapewnić dobrą organizację i jasno zdefiniowane odpowiedzialności metod.
    - **Konfiguracja ścieżki bazy danych:** Przenieść konfigurację ścieżki do `app_config.py` i zapewnić przechowywanie bazy w odpowiednim miejscu (np. folder danych aplikacji użytkownika).
    - **Logowanie:** Rozszerzyć logowanie operacji na bazie danych, błędów i problemów z wydajnością.

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

1.  **Inicjalizacja bazy danych:** Poprawność tworzenia, struktura tabel.
2.  **Dodawanie metadanych:** Zapis, obsługa duplikatów.
3.  **Pobieranie metadanych:** Dla istniejących i nieistniejących plików.
4.  **Aktualizacja metadanych:** Poprawność modyfikacji.
5.  **Usuwanie metadanych:** Poprawność usuwania.
6.  **Wyszukiwanie/Filtrowanie:** Po różnych kryteriach, obsługa braku wyników.

**Test obsługi błędów i przypadków brzegowych:**

1.  **Błędy SQL:** Obsługa wyjątków, stabilność aplikacji.
2.  **Problem z plikiem bazy danych:** Uszkodzenie, tryb tylko do odczytu, niedostępność.
3.  **Iniekcja SQL:** Testy bezpieczeństwa (jeśli zapytania nie są w pełni sparametryzowane).
4.  **Duże ilości danych:** Testy z dużą liczbą rekordów.

**Test integracji (po refaktoryzacji do wątków):**

1.  **Integracja z operacjami na plikach:** Aktualizacja metadanych po `rename`, `move`, `delete`.
2.  **Integracja z UI:** Wyświetlanie, zapisywanie metadanych z UI, responsywność przy operacjach asynchronicznych.

**Test wydajności:**

1.  **Czas odpowiedzi zapytań:** Na dużej bazie danych, identyfikacja wolnych zapytań, wpływ indeksów.
2.  **Wpływ na start aplikacji:** Czy operacje na bazie przy starcie nie opóźniają znacząco uruchomienia.

### 📊 Status tracking

- [ ] Kod zaimplementowany
- [ ] Testy podstawowe przeprowadzone
- [ ] Testy integracji przeprowadzone
- [ ] Testy wydajności przeprowadzone
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia

---

_Analiza pliku `src/logic/metadata_manager.py` zakończona._

## ETAP 4: src/ui/widgets/thumbnail_cache.py

### 📋 Identyfikacja

- **Plik główny:** `src/ui/widgets/thumbnail_cache.py`
- **Priorytet:** 🔴 WYSOKI
- **Zależności:**
  - `logging`
  - `PIL (Pillow)` (do operacji na obrazach)
  - `PyQt6.QtCore`, `PyQt6.QtGui` (do obsługi obrazów w Qt)
  - `src/utils/image_utils.py` (dla funkcji pomocniczych do obrazów)

### 🔍 Analiza problemów

1.  **Błędy krytyczne/Potencjalne problemy:**

    - **Singleton i stan globalny:** Użycie wzorca Singleton (`_instance`) może utrudniać testowanie i prowadzić do nieoczekiwanych interakcji, jeśli stan nie jest prawidłowo zarządzany, zwłaszcza w kontekście wielowątkowym.
    - **Brak limitu rozmiaru cache:** Słownik `_cache` rośnie nieograniczenie, co może prowadzić do wyczerpania pamięci przy dużej liczbie miniaturek. Konieczny jest mechanizm ograniczania rozmiaru (np. LRU - Least Recently Used).
    - **Generowanie miniaturek w głównym wątku:** Metoda `load_pixmap_from_path` wykonuje operacje I/O (odczyt pliku) i przetwarzanie obrazu (zmiana rozmiaru, przycinanie). Jeśli jest wywoływana z głównego wątku UI dla wielu plików lub dużych obrazów, zablokuje UI.
    - **Obsługa błędów ładowania ikon:** `get_error_icon` ma skomplikowaną i nie do końca działającą logikę ładowania standardowej ikony błędu. Powinna być uproszczona lub korzystać z zasobów aplikacji.
    - **Klucz cache:** Klucz `(path, width, height)` jest poprawny, ale należy upewnić się, że ścieżki są zawsze znormalizowane, aby uniknąć duplikatów dla tej samej lokalizacji pliku (np. `C:/plik.jpg` vs `c:/plik.jpg`).

2.  **Optymalizacje:**

    - **Asynchroniczne ładowanie/generowanie miniaturek:** Przenieść operacje `load_pixmap_from_path` do wątków roboczych (`src/ui/delegates/workers.py`). Główny wątek powinien zlecać zadanie i otrzymywać gotową miniaturkę przez sygnał.
    - **Implementacja strategii LRU dla cache:** Ograniczyć maksymalną liczbę przechowywanych miniaturek lub całkowity rozmiar pamięci zajmowanej przez cache. Po przekroczeniu limitu, najdawniej używane elementy powinny być usuwane.
    - **Cache na dysku (opcjonalnie):** Dla bardzo dużych zbiorów danych lub potrzeby utrwalenia cache między sesjami, można rozważyć dodatkowy cache na dysku (np. w folderze danych aplikacji).
    - **Optymalizacja `pillow_image_to_qpixmap` i `crop_to_square`:** Upewnić się, że te funkcje są tak wydajne, jak to możliwe.
    - **Współdzielenie `QPixmap`:** Jeśli ten sam obraz (ta sama ścieżka) jest potrzebny w różnych rozmiarach, można rozważyć przechowywanie oryginalnego `QPixmap` (lub `QImage`) i skalowanie go na żądanie, zamiast przechowywania wielu wersji rozmiarowych tego samego obrazu. Może to jednak wpłynąć na wydajność skalowania w locie.

3.  **Refaktoryzacja:**
    - **Usunięcie/Przemyślenie Singletona:** Rozważyć przekazywanie instancji `ThumbnailCache` przez wstrzykiwanie zależności zamiast globalnego dostępu, co ułatwi testowanie i zarządzanie cyklem życia.
    - **Uproszczenie `get_error_icon`:** Załadować ikonę błędu z pliku zasobów (`.qrc`) lub użyć prostszej, predefiniowanej ikony.
    - **Interfejs dla asynchronicznego pobierania:** Zmodyfikować `get_thumbnail` tak, aby mógł inicjować ładowanie w tle, jeśli miniaturki nie ma w cache, i powiadamiać o jej dostępności (np. przez `QFuture` lub sygnały).
    - **Normalizacja ścieżek:** Zapewnić, że wszystkie ścieżki używane jako klucze są znormalizowane (np. `os.path.normpath` i `os.path.normcase` lub odpowiedniki z `pathlib`).

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

1.  **Dodawanie i pobieranie:** Poprawność dodawania i odzyskiwania miniaturek z cache.
2.  **Ładowanie z dysku:** Poprawność generowania miniaturek dla różnych formatów obrazów, obsługa błędnych/uszkodzonych plików.
3.  **Generowanie ikony błędu:** Poprawność zwracania ikony błędu.
4.  **Czyszczenie cache:** `clear_cache`, `remove_thumbnail`.

**Test obsługi błędów i przypadków brzegowych:**

1.  **Nieistniejące pliki:** Poprawne zachowanie przy próbie załadowania miniatury dla nieistniejącego pliku.
2.  **Uszkodzone pliki obrazów:** Zwracanie ikony błędu lub `None`.
3.  **Puste ścieżki:** Obsługa pustych ścieżek.

**Test wydajności i zarządzania pamięcią (po implementacji LRU i asynchroniczności):**

1.  **Limit cache:** Weryfikacja, czy mechanizm LRU działa poprawnie i cache nie przekracza zdefiniowanego limitu.
2.  **Szybkość ładowania (asynchroniczne):** UI pozostaje responsywne podczas ładowania wielu miniaturek.
3.  **Wycieki pamięci:** Monitorowanie użycia pamięci przy długotrwałym działaniu i wielu operacjach na cache.

**Test integracji (z galerią i wątkami roboczymi):**

1.  **Wyświetlanie w galerii:** Poprawne wyświetlanie miniaturek (lub ikon błędów) w komponencie galerii.
2.  **Aktualizacja UI:** Poprawna aktualizacja UI po asynchronicznym załadowaniu miniaturki.

### 📊 Status tracking

- [ ] Kod zaimplementowany
- [ ] Testy podstawowe przeprowadzone
- [ ] Testy integracji przeprowadzone
- [ ] Testy wydajności przeprowadzone
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia

---

_Analiza pliku `src/ui/widgets/thumbnail_cache.py` zakończona._

## ETAP 5: src/ui/delegates/workers.py

### 📋 Identyfikacja

- **Plik główny:** `src/ui/delegates/workers.py`
- **Priorytet:** 🔴 WYSOKI
- **Zależności:**
  - `logging`
  - `PyQt6.QtCore` (dla `QObject`, `pyqtSignal`)
  - `src.logic.scanner` (dla `scan_folder_for_pairs`)
  - `src.logic.metadata_manager` (dla `apply_metadata_to_file_pairs`)
  - `src.models.file_pair` (dla `FilePair`)

### 🔍 Analiza problemów

1.  **Błędy krytyczne/Potencjalne problemy:**

    - **Brak obsługi postępu:** Żaden z workerów nie emituje sygnałów informujących o postępie operacji (np. procent ukończenia, liczba przetworzonych elementów). Jest to kluczowe dla implementacji paska postępu w UI.
    - **Potencjalne blokowanie w `DataProcessingWorker`:** `apply_metadata_to_file_pairs` jest wywoływane jako pojedyncza, potencjalnie długa operacja. Jeśli przetwarza wiele plików, może to zająć dużo czasu bez informacji zwrotnej o postępie.
    - **Zatrzymywanie `ScanFolderWorker`:** Flaga `_should_stop` jest sprawdzana tylko na początku i po zakończeniu `scan_folder_for_pairs`. Jeśli samo skanowanie jest długotrwałe i blokujące wewnątrz tej funkcji, worker nie zareaguje na żądanie zatrzymania aż do jej ukończenia.
    - **Brak szczegółowych informacji o błędach:** Sygnał `error` w `ScanFolderWorker` emituje tylko string. Lepsze byłoby emitowanie obiektu błędu lub bardziej ustrukturyzowanych danych.
    - **Brak workerów dla innych operacji:** Obecnie istnieją workery tylko dla skanowania i ogólnego "przetwarzania danych". Brakuje dedykowanych workerów dla operacji na plikach (`file_operations.py`) czy generowania miniaturek (`thumbnail_cache.py`), które również powinny działać w tle.

2.  **Optymalizacje:**

    - **Implementacja sygnałów postępu:** Dodać sygnały `progressUpdated(int percent, str message)` do wszystkich workerów. Powinny być emitowane regularnie podczas długotrwałych operacji.
    - **Granularność w `DataProcessingWorker`:** Jeśli `apply_metadata_to_file_pairs` można podzielić na mniejsze kroki (np. per plik), worker powinien iterować i emitować postęp po każdym kroku.
    - **Ulepszone zatrzymywanie `ScanFolderWorker`:** Funkcja `scan_folder_for_pairs` powinna przyjmować flagę lub callback do sprawdzania warunku zatrzymania w trakcie swojego działania (np. po przetworzeniu każdego katalogu).
    - **Rozszerzenie `ScanFolderWorker`:** Mógłby przyjmować parametry skanowania (głębokość, strategia) dynamicznie, zamiast mieć je zahardcodowane.

3.  **Refaktoryzacja:**
    - **Stworzenie bazowego workera:** Utworzyć klasę bazową `BaseWorker(QObject)` z wspólną logiką dla sygnałów `finished`, `error`, `progressUpdated` oraz metodą `stop()` i flagą `_should_stop`.
    - **Dedykowane workery:**
      - `FileOperationWorker` dla operacji kopiowania, przenoszenia, usuwania (z `src/logic/file_operations.py`).
      - `ThumbnailGenerationWorker` dla generowania pojedynczej lub wielu miniaturek (z `src/ui/widgets/thumbnail_cache.py` i `src/utils/image_utils.py`).
    - **Użycie `QRunnable` i `QThreadPool`:** Dla zadań, które nie wymagają bezpośredniej interakcji z obiektami Qt (poza sygnałami na końcu), `QRunnable` uruchamiany w globalnym `QThreadPool.globalInstance()` może być lżejszą alternatywą dla pełnych `QThread` (choć obecna implementacja z `moveToThread` jest poprawna).
    - **Zarządzanie cyklem życia workerów:** Upewnić się, że workery są poprawnie tworzone, uruchamiane i usuwane, aby uniknąć wycieków pamięci lub problemów z wątkami zombie.
    - **Przekazywanie parametrów:** Ustandaryzować sposób przekazywania parametrów do workerów (np. przez konstruktor lub dedykowane metody `set_params`).

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

1.  **Poprawne wykonanie zadania:** Każdy worker wykonuje swoje zadanie i emituje sygnał `finished` po pomyślnym zakończeniu.
2.  **Emisja danych wynikowych:** Poprawność danych emitowanych przez sygnał `finished` (np. listy plików).
3.  **Emisja sygnałów postępu:** Regularne emitowanie sygnału `progressUpdated` z poprawnymi wartościami.
4.  **Obsługa błędów:** Poprawne emitowanie sygnału `error` w przypadku wystąpienia wyjątku.
5.  **Zatrzymywanie workera:** Możliwość przerwania pracy workera za pomocą metody `stop()` i poprawne zakończenie jego działania.

**Test obsługi błędów i przypadków brzegowych:**

1.  **Brak parametrów wejściowych:** Np. `ScanFolderWorker` bez `directory_to_scan`.
2.  **Błędy w logice wewnętrznej:** Symulacja błędów w funkcjach wywoływanych przez workery (np. błąd odczytu pliku, błąd sieciowy).
3.  **Szybkie, wielokrotne uruchamianie i zatrzymywanie:** Stabilność workerów.

**Test integracji (z głównym wątkiem UI):**

1.  **Poprawne podłączenie sygnałów i slotów:** Reakcja UI na sygnały `finished`, `error`, `progressUpdated`.
2.  **Aktualizacja paska postępu:** Pasek postępu w UI odzwierciedla postęp raportowany przez workery.
3.  **Responsywność UI:** UI pozostaje responsywne podczas pracy workerów.

### 📊 Status tracking

- [ ] Kod zaimplementowany
- [ ] Testy podstawowe przeprowadzone
- [ ] Testy integracji przeprowadzone
- [ ] Testy wydajności przeprowadzone
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia

---

_Analiza pliku `src/ui/delegates/workers.py` zakończona._

## ETAP 6: src/ui/gallery_manager.py

### 📋 Identyfikacja

- **Plik główny:** `src/ui/gallery_manager.py`
- **Priorytet:** 🔴 WYSOKI
- **Zależności:**
  - `logging`
  - `math`
  - `typing`
  - `PyQt6.QtCore`, `PyQt6.QtWidgets`
  - `src.app_config`
  - `src.logic.filter_logic`
  - `src.models.file_pair`
  - `src.ui.widgets.file_tile_widget`

### 🔍 Analiza problemów

1.  **Błędy krytyczne/Potencjalne problemy:**

    - **Wydajność przy dużej liczbie kafelków:**
      - `clear_gallery()`: Usuwanie widgetów pojedynczo w pętli może być wolne. Lepsze może być usunięcie i odtworzenie layoutu.
      - `update_gallery_view()`: Podobnie, usuwanie i dodawanie widgetów pojedynczo w pętlach przy każdej aktualizacji (nawet filtrowaniu) jest nieefektywne dla tysięcy elementów. Może to prowadzić do zamrożenia UI.
      - Iterowanie po `self.gallery_tile_widgets.values()` i `self.file_pairs_list` wielokrotnie w `update_gallery_view()`.
    - **Brak wirtualizacji/paginacji:** Galeria próbuje renderować wszystkie pasujące kafelki naraz. Dla tysięcy plików doprowadzi to do ogromnego zużycia pamięci i drastycznego spadku wydajności.
    - **Tworzenie `FileTileWidget` w głównym wątku:** `create_tile_widget_for_pair` jest wywoływane synchronicznie. Jeśli tworzenie kafelka (w tym inicjalne ładowanie miniatury, nawet jeśli z cache) zajmuje czas, spowolni to dodawanie elementów.
    - **Klucz słownika `gallery_tile_widgets`:** Użycie `file_pair.get_archive_path()` jako klucza jest generalnie OK, ale należy zapewnić jego unikalność i spójność (normalizacja ścieżek).

2.  **Optymalizacje:**

    - **Implementacja wirtualnego przewijania (Virtual Scrolling) / Paginacji:** Zamiast tworzyć wszystkie widgety `FileTileWidget` naraz, tworzyć tylko te, które są aktualnie widoczne (plus niewielki bufor). Wymaga to bardziej zaawansowanego zarządzania modelem danych i widokiem (np. `QAbstractItemView` z własnym modelem i delegatem, lub uproszczona logika ręczna).
    - **Leniwe tworzenie kafelków:** Tworzyć widgety `FileTileWidget` tylko wtedy, gdy mają stać się widoczne.
    - **Efektywniejsze aktualizacje layoutu:** Zamiast usuwać i dodawać wszystko, próbować minimalizować zmiany w layoucie. Jeśli jednak stosowana jest wirtualizacja, problem ten częściowo znika, bo operuje się na mniejszej liczbie widgetów.
    - **Asynchroniczne ładowanie danych dla kafelków:** `FileTileWidget` powinien być w stanie załadować swoją miniaturkę i dane asynchronicznie, aktualizując swój wygląd po zakończeniu (integracja z `ThumbnailCache` i `workers.py`).
    - **Optymalizacja obliczania liczby kolumn:** `container_width / tile_width_with_spacing` powinno być wykonywane rzadziej, np. tylko przy zmianie rozmiaru kontenera.

3.  **Refaktoryzacja:**
    - **Oddzielenie logiki danych od prezentacji:** `GalleryManager` mocno miesza zarządzanie danymi (`file_pairs_list`) z logiką UI (tworzenie i zarządzanie widgetami). Rozważyć model danych (np. `QAbstractListModel`) i widok/delegata (`QListView`/`QTableView` z `QStyledItemDelegate`) dla lepszej separacji i wydajności.
    - **Zarządzanie stanem zaznaczenia:** Obecnie brak logiki do obsługi zaznaczania kafelków, co będzie potrzebne do operacji na plikach.
    - **Użycie `setUpdatesEnabled(False/True)`:** Jest używane poprawnie, ale przy bardzo dużych zmianach może nie wystarczyć.

### 🧪 Plan testów

**Test funkcjonalności podstawowej (po refaktoryzacji i optymalizacjach):**

1.  **Wyświetlanie kafelków:** Poprawne wyświetlanie kafelków dla załadowanych danych.
2.  **Filtrowanie:** Poprawne działanie filtrowania i aktualizacja widoku.
3.  **Zmiana rozmiaru miniaturek:** Poprawna aktualizacja galerii po zmianie rozmiaru.
4.  **Czyszczenie galerii:** Poprawne usuwanie wszystkich elementów.

**Test wydajności i obsługi dużej liczby elementów (kluczowe):**

1.  **Ładowanie dużej liczby plików:** Czas ładowania i responsywność UI podczas wyświetlania tysięcy kafelków (z wirtualizacją).
2.  **Przewijanie:** Płynność przewijania przy dużej liczbie elementów.
3.  **Filtrowanie dużego zbioru:** Szybkość reakcji na zmiany filtrów.
4.  **Zużycie pamięci:** Monitorowanie zużycia pamięci, szczególnie przy wirtualizacji.

**Test obsługi błędów i przypadków brzegowych:**

1.  **Brak plików do wyświetlenia:** Poprawne zachowanie (pusta galeria).
2.  **Błędy podczas tworzenia pojedynczych kafelków:** Aplikacja nie powinna się zawieszać; błąd powinien być zalogowany.

**Test integracji:**

1.  **Integracja z `ThumbnailCache`:** Poprawne asynchroniczne ładowanie miniaturek.
2.  **Integracja z logiką zaznaczania i operacji na plikach.**

### 📊 Status tracking

- [ ] Kod zaimplementowany
- [ ] Testy podstawowe przeprowadzone
- [ ] Testy integracji przeprowadzone
- [ ] Testy wydajności przeprowadzone
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia

---

_Analiza pliku `src/ui/gallery_manager.py` zakończona._

## ETAP 7: src/ui/main_window.py

### 📋 Identyfikacja

- **Plik główny:** `src/ui/main_window.py`
- **Priorytet:** 🔴 WYSOKI
- **Zależności:**
  - `logging`, `os`, `typing`
  - `PyQt6.QtCore`, `PyQt6.QtGui`, `PyQt6.QtWidgets`
  - `src.app_config`
  - `src.logic.file_operations`, `src.logic.metadata_manager`
  - `src.models.file_pair`
  - `src.ui.delegates.workers`
  - `src.ui.directory_tree_manager`
  - `src.ui.file_operations_ui`
  - `src.ui.gallery_manager`
  - `src.ui.widgets.filter_panel`, `src.ui.widgets.preview_dialog`
  - `src.utils.path_utils`

### 🔍 Analiza problemów

1.  **Błędy krytyczne/Potencjalne problemy:**

    - **Brak globalnego paska postępu:** Kluczowy element wymagany w audycie. Obecnie brak implementacji `QProgressBar` i mechanizmów jego aktualizacji przez operacje długotrwałe (skanowanie, przetwarzanie danych, operacje na plikach).
    - **Operacje blokujące UI:**
      - Masowe operacje na plikach (`_perform_bulk_delete`, `_perform_bulk_move`) wykonują operacje I/O (`os.remove`, `shutil.move`) bezpośrednio w głównym wątku. Dla dużej liczby plików spowoduje to zamrożenie interfejsu.
      - Zapis metadanych (`_save_metadata`) jest operacją synchroniczną i potencjalnie długotrwałą.
    - **Złożoność klasy (`God Object`):** `MainWindow` jest bardzo duża (ponad 1000 linii) i zarządza zbyt wieloma aspektami aplikacji (stan danych, logika UI, wątki, interakcje z wieloma managerami). Utrudnia to konserwację, testowanie i zrozumienie kodu.
    - **Niepełne zastosowanie `styles.qss`:** Globalny arkusz stylów nie jest systematycznie aplikowany do całego okna i jego komponentów. Widoczne są style inline (np. `bulk_operations_panel`).
    - **Potencjalna nieefektywność przy tworzeniu kafelków:** Mimo że `DataProcessingWorker` przygotowuje dane w tle, slot `_create_tile_widget_for_pair` (który tworzy widget i łączy sygnały) jest wykonywany w głównym wątku dla każdego kafelka. Przy tysiącach kafelków może to prowadzić do spowolnienia UI podczas fazy zapełniania galerii.
    - **Zarządzanie wątkami:** Użycie `terminate()` w `_cleanup_threads` jako fallback jest ryzykowne i może prowadzić do niestabilności lub wycieków zasobów.

2.  **Optymalizacje:**

    - **Implementacja `QProgressBar`:** Dodać `QProgressBar` do layoutu (np. w pasku stanu lub dedykowanym panelu). Workery powinny emitować sygnały postępu (np. `progress(int percent, str message)`), które `MainWindow` będzie przechwytywać i aktualizować pasek.
    - **Przeniesienie operacji blokujących do wątków:**
      - Operacje masowego usuwania i przenoszenia plików powinny być realizowane przez dedykowane workery (np. `FileOperationWorker` dziedziczący po `BaseWorker` z `workers.py`).
      - Zapis metadanych (`_save_metadata`) również powinien być operacją asynchroniczną w tle.
    - **Optymalizacja tworzenia i aktualizacji galerii:** Ściślejsza współpraca z `GalleryManager` w celu implementacji wirtualizacji lub paginacji, aby unikać tworzenia i zarządzania tysiącami widgetów jednocześnie.
    - **Lepsze zarządzanie stanem UI:** Używać bardziej deklaratywnego podejścia do aktualizacji UI zamiast bezpośrednich manipulacji wieloma widgetami w różnych funkcjach.

3.  **Refaktoryzacja:**
    - **Podział `MainWindow`:** Wydzielić logikę do mniejszych, bardziej wyspecjalizowanych klas/managerów (np. manager stanu aplikacji, manager operacji masowych, dedykowane kontrolery dla poszczególnych sekcji UI).
    - **Ujednolicenie operacji na plikach:** Wszystkie operacje na plikach powinny być obsługiwane przez `src.logic.file_operations` i wykonywane w tle przez odpowiednie workery, a `FileOperationsUI` powinno być centralnym punktem interakcji użytkownika z tymi operacjami.
    - **Globalne zastosowanie `styles.qss`:** Załadować i zastosować `styles.qss` do całej aplikacji na poziomie `QApplication` lub `MainWindow`.
    - **Ulepszenie cyklu życia wątków:** Zapewnić bezpieczne kończenie wątków, preferując mechanizmy kooperatywnego anulowania (`_should_stop` flag) i unikanie `terminate()`.
    - **Centralizacja zarządzania stanem zaznaczenia:** Logika `selected_tiles` i aktualizacja UI z tym związana mogłaby być zarządzana przez dedykowany model lub manager.

### 🧪 Plan testów

**Testy funkcjonalne:**

1.  **Wybór folderu roboczego:** Poprawne skanowanie, wyświetlanie danych.
2.  **Działanie filtrów:** Poprawna aktualizacja galerii.
3.  **Zmiana rozmiaru miniaturek:** Płynna zmiana i aktualizacja widoku.
4.  **Operacje masowe (po przeniesieniu do wątków):** Zaznaczanie, usuwanie, przenoszenie wielu plików – poprawność działania i aktualizacja UI.
5.  **Ręczne parowanie plików:** Sprawdzenie funkcjonalności (jeśli zaimplementowane).
6.  **Pasek postępu:** Poprawne wyświetlanie postępu dla skanowania, przetwarzania danych, operacji na plikach.
7.  **Zastosowanie stylów:** Weryfikacja wyglądu aplikacji po globalnym zastosowaniu `styles.qss`.

**Testy wydajności i responsywności:**

1.  **Responsywność UI:** Interfejs użytkownika pozostaje płynny podczas długotrwałych operacji w tle.
2.  **Czas reakcji na akcje użytkownika:** Szybkość odpowiedzi aplikacji.

**Testy stabilności:**

1.  **Wielokrotne operacje:** Wykonywanie wielu operacji pod rząd (np. skanowanie, filtrowanie, zmiana folderu).
2.  **Zamykanie aplikacji:** Bezpieczne zamykanie aplikacji, gdy wątki są aktywne.
3.  **Obsługa błędów:** Poprawne raportowanie i obsługa błędów z operacji w tle.

### 📊 Status tracking

- [ ] Kod zaimplementowany
- [ ] Testy podstawowe przeprowadzone
- [ ] Testy integracji przeprowadzone
- [ ] Testy wydajności przeprowadzone
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia

---

_Analiza pliku `src/ui/main_window.py` zakończona._

## ETAP 8: src/main.py

### 📋 Identyfikacja

- **Plik główny:** `src/main.py`
- **Priorytet:** 🟡 ŚREDNI (główny punkt wejścia, ale prosta logika)
- **Zależności:**
  - `logging` (standardowa biblioteka)
  - `sys` (standardowa biblioteka)
  - `PyQt6.QtWidgets.QApplication` (biblioteka zewnętrzna)
  - `src.ui.main_window.MainWindow` (moduł projektu)
  - `src.utils.logging_config.setup_logging` (moduł projektu)

### 🔍 Analiza problemów

1.  **Błędy krytyczne/Potencjalne problemy:**

    - **Minimalna obsługa błędów globalnych:** Funkcja `main()` nie posiada globalnego bloku `try...except` do przechwytywania nieoczekiwanych wyjątków, które mogłyby wystąpić podczas inicjalizacji `QApplication`, `MainWindow` lub w trakcie `app.exec()`. Chociaż Qt ma własne mechanizmy obsługi zdarzeń, krytyczny błąd na wczesnym etapie mógłby zakończyć aplikację bez czytelnego logu lub komunikatu dla użytkownika.
    - **Blok `if __name__ == "__main__":`**: Poprawnie ostrzega przed bezpośrednim uruchomieniem, ale nie zapobiega mu całkowicie. Jeśli `run_app.py` jest jedynym zalecanym sposobem uruchomienia, można by rozważyć bardziej rygorystyczne podejście (np. podniesienie wyjątku lub natychmiastowe zakończenie z kodem błędu), choć obecne ostrzeżenie jest akceptowalne.

2.  **Optymalizacje:**

    - **Rozszerzone logowanie:** Można dodać bardziej szczegółowe logi na początku i końcu funkcji `main()`, np. logowanie wersji aplikacji, systemu operacyjnego, czy argumentów linii poleceń (jeśli są istotne).
    - **Struktura importów:** Importy są już podzielone na standardowe/zewnętrzne i lokalne, co jest dobrą praktyką.
    - **Konfiguracja aplikacji Qt:** Można rozważyć ustawienie niektórych atrybutów aplikacji Qt globalnie, jeśli jest taka potrzeba (np. `QApplication.setApplicationName()`, `QApplication.setOrganizationName()`, `QApplication.setApplicationVersion()`), co może być przydatne dla integracji z systemem operacyjnym lub ustawień.

3.  **Refaktoryzacja:**

    - **Globalny try-except:** Zaleca się opakowanie głównej logiki w `main()` w blok `try...except Exception as e:` w celu logowania wszelkich nieprzechwyconych wyjątków i ewentualnego wyświetlenia komunikatu błędu użytkownikowi przed zamknięciem aplikacji. To zwiększa stabilność i ułatwia diagnozowanie problemów.
    - **Komentarze:** Komentarze są jasne i adekwatne. Docstring dla `main()` dobrze opisuje jej rolę.

4.  **Zgodność z `styles.qss`:**
    - Nie dotyczy bezpośrednio tego pliku, ponieważ `main.py` nie tworzy ani nie stylizuje elementów UI. Odpowiedzialność za ładowanie i aplikowanie stylów spoczywa na `MainWindow` lub na poziomie `QApplication`, jeśli style mają być globalne od samego początku.

5.  **Pasek postępu:**
    - Nie dotyczy bezpośrednio tego pliku. Pasek postępu jest elementem UI zarządzanym przez `MainWindow`.

6.  **Wydajność:**
    - Plik nie zawiera operacji intensywnych obliczeniowo ani I/O, więc nie ma bezpośrednich problemów z wydajnością. Jego rola to inicjalizacja.

7.  **Stabilność:**
    - Jak wspomniano, dodanie globalnej obsługi wyjątków w `main()` znacząco poprawiłoby stabilność aplikacji w przypadku nieoczekiwanych błędów podczas uruchamiania.

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

1.  **Uruchomienie przez `run_app.py`:**
    - Zweryfikuj, czy aplikacja uruchamia się poprawnie, wywołując `src.main.main()`.
    - Sprawdź, czy główne okno (`MainWindow`) jest tworzone i wyświetlane.
    - Upewnij się, że system logowania (`setup_logging()`) jest inicjalizowany i logi są zapisywane zgodnie z konfiguracją.
2.  **Bezpośrednie uruchomienie `src/main.py`:**
    - Uruchom `python src/main.py`.
    - Sprawdź, czy na konsoli pojawia się ostrzeżenie o konieczności uruchomienia przez `run_app.py`.

**Test obsługi błędów (po implementacji globalnego try-except):**

1.  **Błąd inicjalizacji `QApplication`:**
    - Symuluj błąd (np. przez przekazanie nieprawidłowych argumentów do `QApplication` lub modyfikację środowiska tak, aby Qt nie mogło się zainicjalizować).
    - Sprawdź, czy błąd jest logowany i aplikacja kończy działanie w kontrolowany sposób.
2.  **Błąd inicjalizacji `MainWindow`:**
    - Wprowadź tymczasowy błąd w konstruktorze `MainWindow` (np. `raise Exception("Test init error")`).
    - Uruchom aplikację.
    - Sprawdź, czy wyjątek jest przechwytywany przez globalny handler w `main()`, logowany, i czy aplikacja informuje o błędzie/kończy działanie.
3.  **Błąd podczas `app.exec()`:**
    - (Trudniejsze do symulacji bez modyfikacji wewnętrznej logiki Qt lub `MainWindow`) Rozważ scenariusze, gdzie pętla zdarzeń mogłaby zakończyć się nieoczekiwanym błędem.

### 📊 Status tracking

- [ ] Kod zaimplementowany (np. globalny try-except)
- [ ] Testy podstawowe przeprowadzone
- [ ] Testy integracji (z `run_app.py` i `MainWindow`) przeprowadzone
- [ ] Testy obsługi błędów przeprowadzone
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia

---

_Analiza pliku `src/main.py` zakończona._

## ETAP 9: run_app.py

### 📋 Identyfikacja

- **Plik główny:** `run_app.py`
- **Priorytet:** 🟡 ŚREDNI (główny skrypt uruchomieniowy, ale prosta logika)
- **Zależności:**
  - `os` (standardowa biblioteka)
  - `sys` (standardowa biblioteka)
  - `logging` (standardowa biblioteka, używana warunkowo)
  - `src.main.main` (moduł projektu)

### 🔍 Analiza problemów

1.  **Błędy krytyczne/Potencjalne problemy:**

    - **Modyfikacja `sys.path`:** Skrypt poprawnie modyfikuje `sys.path`, aby umożliwić importy z katalogu `src`. Jest to kluczowe dla działania aplikacji i wydaje się być zaimplementowane prawidłowo. Należy jednak upewnić się, że `os.path.abspath(__file__)` zawsze zwraca oczekiwaną ścieżkę, niezależnie od sposobu uruchomienia skryptu (np. z innego katalogu roboczego).
    - **Obsługa wyjątków przy starcie:** Podobnie jak w `src/main.py`, brakuje globalnego bloku `try...except` wokół wywołania `main()` w funkcji `run()`. Błąd podczas inicjalizacji `src.main.main` (np. problem z importem wewnątrz `src.main` lub błąd w `setup_logging`) mógłby zakończyć działanie skryptu bez czytelnego komunikatu.

2.  **Optymalizacje:**

    - **Obsługa argumentów linii poleceń:** Skrypt obsługuje argument `--debug` do włączania szczegółowego logowania dla modułu `src.logic.scanner`. Można rozważyć użycie modułu `argparse` dla bardziej zaawansowanego i elastycznego parsowania argumentów, jeśli w przyszłości pojawi się potrzeba dodania innych opcji uruchomieniowych.
    - **Logowanie:** Komunikat `print(f"Root in path: {_PROJECT_ROOT}")` jest przydatny do debugowania problemów ze ścieżkami. Można go przenieść do standardowego systemu logowania (np. z poziomem INFO lub DEBUG), aby był spójny z resztą logów aplikacji.
    - **Kolejność importów:** Import `src.main import main` jest oznaczony `# noqa: E402` z powodu umieszczenia go po modyfikacji `sys.path`. Jest to akceptowalne i powszechnie stosowane obejście dla E402 w takich przypadkach.

3.  **Refaktoryzacja:**
    - **Globalny try-except w `run()`:** Zaleca się opakowanie wywołania `main()` w funkcji `run()` w blok `try...except Exception as e:` w celu logowania wszelkich nieprzechwyconych wyjątków i ewentualnego wyświetlenia komunikatu błędu użytkownikowi. To zwiększyłoby odporność skryptu uruchomieniowego.
    - **Struktura funkcji `run()`:** Obecna struktura jest czytelna. Warunkowe ustawianie poziomu logowania jest jasno zaimplementowane.

### 🧪 Plan testów

**Test funkcjonalności podstawowej:**

1.  **Standardowe uruchomienie:**
    - Uruchom `python run_app.py`.
    - Sprawdź, czy aplikacja (`src.main.main()`) uruchamia się poprawnie.
    - Zweryfikuj, czy komunikat `Root in path: ...` jest wyświetlany.
    - Sprawdź, czy domyślny poziom logowania jest stosowany (np. INFO).
2.  **Uruchomienie z opcją `--debug`:**
    - Uruchom `python run_app.py --debug`.
    - Sprawdź, czy komunikat `TRYB DEBUGOWANIA WŁĄCZONY...` jest wyświetlany.
    - Zweryfikuj (np. poprzez sprawdzenie logów lub zachowania aplikacji), czy poziom logowania dla `src.logic.scanner` został ustawiony na `DEBUG`.
3.  **Uruchomienie z innego katalogu roboczego:**
    - Zmień bieżący katalog na inny niż katalog projektu (np. `cd ..`).
    - Uruchom skrypt używając pełnej lub względnej ścieżki (np. `python _CFAB_3DHUB/run_app.py`).
    - Sprawdź, czy aplikacja nadal uruchamia się poprawnie (testuje to poprawność modyfikacji `sys.path`).

**Test obsługi błędów (po implementacji globalnego try-except w `run()`):**

1.  **Błąd importu `src.main`:**
    - Tymczasowo zmień nazwę pliku `src/main.py` lub wprowadź w nim błąd składniowy uniemożliwiający import.
    - Uruchom `python run_app.py`.
    - Sprawdź, czy błąd `ImportError` (lub podobny) jest przechwytywany, logowany, i czy skrypt kończy działanie w kontrolowany sposób.
2.  **Błąd wykonania `main()` z `src.main`:**
    - Wprowadź tymczasowy błąd (np. `raise Exception("Error in main()")`) na początku funkcji `main()` w pliku `src/main.py`.
    - Uruchom `python run_app.py`.
    - Sprawdź, czy wyjątek jest przechwytywany przez handler w `run_app.py`, logowany, i czy skrypt informuje o błędzie/kończy działanie.

### 📊 Status tracking

- [ ] Kod zaimplementowany (np. globalny try-except w `run()`)
- [ ] Testy podstawowe przeprowadzone
- [ ] Testy obsługi błędów przeprowadzone
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia

---

_Analiza pliku `run_app.py` zakończona._
