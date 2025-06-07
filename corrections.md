# Analiza i Korekcje Kodu - 3DHUB

## 🔴 WYSOKI PRIORYTET

### 1. `src/logic/scanner.py`

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
    - **Przeniesienie do wątków roboczych:** Cała logika skanowania (`scan_folder_for_pairs` i funkcje pomocnicze) powinna być hermetyzowana w klasie dziedziczącej po `QRunnable` (lub podobnej) i zarządzana przez `src.ui.delegates.workers.QThreadPool`. To pozwoli na asynchroniczne wykonywanie skanowania i efektywne raportowanie postępu/wyników do UI za pomocą sygnałów.
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

### 2. `src/logic/file_operations.py`

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
    - Wykonaj wszystkie operacje na plikach/folderach/par z poziomu UI.
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

### 3. `src/logic/metadata_manager.py`

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
    - **Wydajność przy dużej bazie danych:** Brak odpowiednich indeksów na często przeszukiwanych kolumnach (np. `file_path`, `archive_path`, tagi) może prowadzić to znacznego spowolnienia zapytań.
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

### 4. `src/ui/widgets/thumbnail_cache.py`

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
    - **Implementacja strategii LRU dla cache:** Ograniczyć maksymalną liczbę przechowywanych miniaturek lub całkowity rozmiar pamięci zajmowanej przez cache. Po przekroceniu limitu, najdawniej używane elementy powinny być usuwane.
    - **Cache na dysku (opcjonalnie):** Dla bardzo dużych zbiorów danych lub potrzeby utrwalenia cache między sesjami, można rozważyć dodatkowy cache na dysku (np. w folderze danych aplikacji).
    - **Optymalizacja `pillow_image_to_qpixmap` i `crop_to_square`:** Upewnić się, że te funkcje są tak wydajne, jak to możliwe.
    - **Współdzielenie `QPixmap`:** Jeśli ten sam obraz (ta sama ścieżka) jest potrzebny w różnych rozmiarach, można rozważyć przechowywanie oryginalnego `QPixmap` (lub `QImage`) i skalowanie go na żądanie, zamiast przechowywania wielu wersji rozmiarowych tego samego obrazu. Może to jednak wpłynąć na wydajność skalowania w locie.

3.  **Refaktoryzacja:**
    - **Usunięcie/Przemyślenie Singletona:** Rozważyć przekazywanie instancji `ThumbnailCache` przez wstrzykiwanie zależności zamiast globalnego dostępu, co ułatwi testowanie i zarządzanie cyklem życia.
    - **Uproszczenie `get_error_icon`:** Załadować ikonę błędu z pliku zasobów (`.qrc`) lub użyć prostszej, predefiniowanej ikony.
    - **Interfejs dla asynchronicznego pobierania:** Zmodyfikować `get_thumbnail` tak, aby mógł inicjować ładowanie w tle, jeśli miniaturki nie ma w cache, i powiadamiać o jej dostępności (np. przez `QFuture` lub sygnały).
    - **Normalizacja ścieżek:** Zapewnić, że wszystkie ścieżki używane jako klucze są znormalizowane (np. `os.path.normpath` i `os.path.normcase` lub odpowiednie z `pathlib`).

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

- [ ] Kod zaimplementany
- [ ] Testy podstawowe przeprowadzone
- [ ] Testy integracji przeprowadzone
- [ ] Testy wydajności przeprowadzone
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia

---

_Analiza pliku `src/ui/widgets/thumbnail_cache.py` zakończona._

### 5. `src/ui/delegates/workers.py`

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

### 6. `src/ui/gallery_manager.py`

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

- [ ] Kod zaimplementany
- [ ] Testy podstawowe przeprowadzone
- [ ] Testy integracji przeprowadzone
- [ ] Testy wydajności przeprowadzone
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia

---

_Analiza pliku `src/ui/gallery_manager.py` zakończona._

### 7. `src/ui/main_window.py`

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

- [ ] Kod zaimplementany
- [ ] Testy podstawowe przeprowadzone
- [ ] Testy integracji przeprowadzone
- [ ] Testy wydajności przeprowadzone
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
- [ ] Gotowe do wdrożenia

---

_Analiza pliku `src/ui/main_window.py` zakończona._

### 8. `src/main.py`

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

## 🟡 ŚREDNI PRIORYTET

### 9. `run_app.py`

### 📋 Identyfikacja

- **Plik główny:** `run_app.py`
- **Priorytet:** 🟡 ŚREDNI
- **Zależności:**
  - `src.main` (moduł projektu)

### 🔍 Analiza problemów

Plik `run_app.py` jest prostym skryptem uruchomieniowym, który importuje i wywołuje funkcję `main()` z modułu `src.main`. Jest to zalecany sposób uruchamiania aplikacji.

_Analiza pliku `run_app.py` zakończona._

### 10. `src/app_config.py`

### Identyfikacja

- **Ścieżka**: `src/app_config.py`
- **Priorytet**: Wysoki
- **Opis**: Zarządza konfiguracją aplikacji, w tym odczytem, zapisem i walidacją parametrów. Obsługuje domyślne wartości i aktualizacje konfiguracji.

### Analiza Problemu

#### Krytyczne Błędy i Problemy ze Stabilnością:

1.  **Brak obsługi błędów przy tworzeniu katalogu konfiguracyjnego**: W `_save_config`, `os.makedirs(self._app_data_dir, exist_ok=True)` może zgłosić wyjątek (np. `PermissionError`), który nie jest przechwytywany. Może to prowadzić do nieoczekiwanego zakończenia działania aplikacji lub niemożności zapisania konfiguracji.
2.  **Potencjalne nadpisanie konfiguracji przy błędzie odczytu**: Jeśli plik konfiguracyjny istnieje, ale jest uszkodzony (np. nieprawidłowy JSON), metoda `_load_config` zwraca `DEFAULT_CONFIG`. Jeśli następnie aplikacja spróbuje zapisać konfigurację (np. przez `set`), uszkodzony plik zostanie nadpisany domyślnymi wartościami, co może prowadzić do utraty wcześniejszych ustawień użytkownika.

#### Optymalizacje i Wydajność:

1.  **Wielokrotny zapis do pliku przy zmianie wielu parametrów**: Metoda `set_thumbnail_size_range` wywołuje `self.set` dwukrotnie, co prowadzi do dwukrotnego zapisu całego pliku konfiguracyjnego. W przypadku częstych zmian lub większej liczby parametrów ustawianych jednocześnie, bardziej efektywne byłoby zebranie zmian i zapisanie pliku raz.
2.  **Obliczanie `_thumbnail_size`**: Wartość `_thumbnail_size` jest obliczana w `_update_derived_values` i przechowywana jako atrybut instancji. Jest to dobre, ale metoda `_update_derived_values` jest wywoływana po każdym pomyślnym zapisie konfiguracji (`set` -> `_save_config` -> `_update_derived_values`). Jeśli konfiguracja jest zapisywana często, a inne wartości pochodne nie są tak często używane, można rozważyć leniwe obliczanie lub bardziej selektywne aktualizacje.

#### Refaktoryzacja i Czytelność Kodu:

1.  **Walidacja typów i wartości**: Metody walidacyjne (`_validate_int`, `_validate_str`, etc.) są statyczne i dobrze zdefiniowane. Można by rozważyć użycie bardziej zaawansowanych bibliotek do walidacji (np. Pydantic), jeśli konfiguracja stanie się bardziej złożona, co mogłoby uprościć kod i zapewnić lepsze komunikaty o błędach.
2.  **Powtarzające się bloki `try-except` w `_load_config`**: Bloki `except json.JSONDecodeError` i `except IOError` mają identyczną logikę (logowanie błędu i zwracanie `DEFAULT_CONFIG`). Można je połączyć w jeden blok `except (json.JSONDecodeError, IOError) as e:`.
3.  **Eksport dla kompatybilności wstecznej**: Sekcja na końcu pliku (`# --- Eksport funkcji i stałych dla kompatybilności wstecznej ---`) jest dobrym rozwiązaniem tymczasowym, ale docelowo kod korzystający z tych eksportowanych elementów powinien zostać zrefaktoryzowany, aby bezpośrednio korzystać z instancji `config` i jej metod/właściwości. Zmniejszy to globalny stan i poprawi enkapsulację.
4.  **Nazewnictwo**: `predefined_colors_filter` jako właściwość zwracająca `OrderedDict` z `predefined_colors` jest nieco myląca. Nazwa sugeruje, że może to być jakiś mechanizm filtrowania, a nie tylko uporządkowana wersja słownika. Może `ordered_predefined_colors` byłoby jaśniejsze.
5.  **Typowanie**: Plik używa type hints, co jest dobrą praktyką. Należy zapewnić ich spójność i kompletność.
6.  **Stałe dla kryteriów specjalnych**: Wartości stringowe jak `"ALL"` i `"__NONE__` dla `required_color_tag` mogłyby być zdefiniowane jako stałe (np. `COLOR_FILTER_ALL = "ALL"`, `COLOR_FILTER_NONE = "__NONE__"`) dla lepszej czytelności i uniknięcia literówek.
7.  **Domyślna instancja `config`**: Tworzenie globalnej instancji `config = AppConfig()` na poziomie modułu jest powszechną praktyką, ale może utrudniać testowanie i prowadzić do problemów, jeśli różne części aplikacji potrzebowałyby różnych konfiguracji (choć w tym przypadku wydaje się to mało prawdopodobne). Wstrzykiwanie zależności (dependency injection) mogłoby być alternatywą w bardziej złożonych systemach.

#### Sugestie dotyczące UI (jeśli dotyczy):

- Nie dotyczy bezpośrednio, ale zmiany w konfiguracji (np. `thumbnail_size`) powinny być odzwierciedlane w UI w czasie rzeczywistym lub po ponownym załadowaniu odpowiednich komponentów.

### Plan Testów

1.  **Testy jednostkowe dla `AppConfig`:**

    - **Inicjalizacja**:
      - Sprawdzenie, czy `AppConfig` poprawnie tworzy domyślny plik konfiguracyjny, jeśli nie istnieje.
      - Sprawdzenie, czy `AppConfig` poprawnie wczytuje istniejący plik konfiguracyjny.
      - Sprawdzenie, czy `AppConfig` używa domyślnych wartości, gdy plik konfiguracyjny jest uszkodzony (nieprawidłowy JSON).
      - Sprawdzenie, czy `AppConfig` używa domyślnych wartości, gdy nie ma uprawnień do odczytu pliku konfiguracyjnego (może wymagać mockowania `os.path.exists` lub `open`).
      - Sprawdzenie, czy `AppConfig` poprawnie uzupełnia brakujące klucze w istniejącym pliku konfiguracyjnym wartościami domyślnymi i zapisuje zaktualizowaną konfigurację.
    - **Odczyt i Zapis (`get`, `set`)**:
      - Test `get` dla istniejących i nieistniejących kluczy (z wartością domyślną i bez).
      - Test `set` dla różnych typów danych i sprawdzenie, czy konfiguracja jest poprawnie zapisywana do pliku.
      - Test `set` i sprawdzenie, czy `_update_derived_values` jest wywoływana (np. przez sprawdzenie zmiany `_thumbnail_size`).
    - **Walidacja (`_validate_*` metody)**:
      - Testy dla każdej metody walidacyjnej z poprawnymi i niepoprawnymi danymi (różne typy, wartości poza zakresem).
    - **Metody specyficzne dla parametrów**:
      - `set_thumbnail_slider_position`: test z poprawnymi i niepoprawnymi wartościami (poza zakresem 0-100).
      - `get_thumbnail_slider_position`: test odczytu wartości.
      - `set_thumbnail_size_range`: test z poprawnymi i niepoprawnymi wartościami (np. min > max).
      - `get_supported_extensions`: test dla "archive", "preview" i nieznanego typu.
      - `set_supported_extensions`: test z listą stringów, normalizacją (dodawanie kropki), dla "archive", "preview" i nieznanego typu.
      - `get_predefined_colors`, `set_predefined_colors`: test odczytu i zapisu słownika.
    - **Właściwości**:
      - Test odczytu wszystkich właściwości (`thumbnail_size`, `min_thumbnail_size`, `max_thumbnail_size`, `supported_archive_extensions`, `supported_preview_extensions`, `predefined_colors_filter`).
      - Sprawdzenie, czy `thumbnail_size` jest poprawnie obliczane na podstawie `thumbnail_slider_position`, `min_thumbnail_size`, `max_thumbnail_size`.
    - **Obsługa błędów zapisu**:
      - Symulacja `IOError` podczas zapisu w `_save_config` (np. przez mockowanie `open` aby zgłaszało wyjątek) i sprawdzenie, czy metoda `set` zwraca `False` oraz czy błąd jest logowany.
      - Symulacja `PermissionError` podczas `os.makedirs` w `_save_config`.
    - **Zachowanie przy uszkodzonym pliku konfiguracyjnym**:
      - Utworzenie pliku `config.json` z nieprawidłową składnią JSON. Sprawdzenie, czy `_load_config` zwraca `DEFAULT_CONFIG` i loguje błąd.
      - Utworzenie pliku `config.json`, który jest prawidłowym JSON-em, ale zawiera wartości niekompatybilne z oczekiwaniami (np. string zamiast int dla `thumbnail_size`). Obecna implementacja nie waliduje typów przy odczycie, jedynie przy ustawianiu przez dedykowane metody. To może być obszar do poprawy – walidacja przy wczytywaniu konfiguracji.

2.  **Testy integracyjne (jeśli dotyczy)**:
    - Sprawdzenie, czy zmiany w konfiguracji (np. rozmiar miniatur, obsługiwane rozszerzenia) są poprawnie odzwierciedlane w innych częściach aplikacji (np. w UI galerii, w logice skanowania plików).
    - Testowanie ścieżki użytkownika: zmiana ustawienia w UI (jeśli jest taka opcja), zapis konfiguracji, ponowne uruchomienie aplikacji i sprawdzenie, czy nowe ustawienie jest aktywne.

### Śledzenie Postępów

- [ ] **Analiza**: Ukończono.
- [ ] **Implementacja Poprawek**:
  - [ ] Obsługa błędów w `_save_config` (np. `PermissionError` przy `os.makedirs`).
  - [ ] Rozważenie strategii dla uszkodzonego pliku konfiguracyjnego, aby uniknąć nadpisania przez domyślne wartości przy błędzie odczytu (np. przez utworzenie backupu przed próbą zapisu nowej konfiguracji, jeśli ostatni odczyt był z domyślnych wartości z powodu błędu).
  - [ ] Optymalizacja zapisu w `set_thumbnail_size_range` (jeden zapis na końcu).
  - [ ] Połączenie bloków `try-except` w `_load_config`.
  - [ ] Dodanie pełnego typowania do klasy `AppConfig` i jej metod.
  - [ ] (Opcjonalnie) Refaktoryzacja kodu używającego eksportowanych stałych/funkcji, aby korzystał bezpośrednio z instancji `config`.
  - [ ] (Opcjonalnie) Zmiana nazwy właściwości `predefined_colors_filter`.
  - [ ] (Opcjonalnie, długoterminowo) Rozważenie walidacji typów/wartości podczas wczytywania konfiguracji z pliku, a nie tylko przy ich ustawianiu.
- [ ] **Testowanie**:
  - [ ] Napisanie testów jednostkowych dla `AppConfig`.
  - [ ] Przeprowadzenie testów integracyjnych.
- [ ] **Dokumentacja**: Zaktualizowano `corrections.md`.

---

### 11. `src/logic/filter_logic.py`

### Identyfikacja

- **Ścieżka**: `src/logic/filter_logic.py`
- **Priorytet**: Średni
- **Opis:** Moduł odpowiedzialny za logikę filtrowania listy obiektów `FilePair` na podstawie różnych kryteriów, takich jak ocena gwiazdkowa, tagi kolorystyczne i prefiks ścieżki.

### Analiza Problemu

#### Krytyczne Błędy i Problemy ze Stabilnością:

1.  **Brak walidacji typów kryteriów**: Funkcja `filter_file_pairs` pobiera `filter_criteria` jako słownik, ale nie ma jawnej walidacji typów wartości w tym słowniku (np. czy `min_stars` jest int, czy `required_color_tag` jest stringiem). Nieprawidłowe typy mogą prowadzić do `TypeError` lub nieoczekiwanego zachowania podczas porównań.
2.  **Potencjalne `TypeError` przy porównywaniu tagów kolorów**: W linii `pair_color_tag.strip().lower() == required_color_tag.strip().lower()`, jeśli `pair_color_tag` jest `None` (co jest możliwe, jeśli `get_color_tag()` zwraca `None`), wywołanie `.strip()` spowoduje `AttributeError`. Chociaż warunek `isinstance(pair_color_tag, str)` częściowo to pokrywa, warto rozważyć bardziej bezpośrednią obsługę `None`.

#### Optymalizacje i Wydajność:

1.  **Logowanie w pętli**: Intensywne logowanie wewnątrz pętli (`logging.debug`) dla każdego sprawdzanego elementu może znacząco spowolnić filtrowanie przy bardzo dużych listach `file_pairs_list`. Chociaż jest to przydatne do debugowania, w środowisku produkcyjnym logowanie na poziomie DEBUG powinno być domyślnie wyłączone lub mniej szczegółowe.
2.  **Wielokrotne wywołania `normalize_path`**: W pętli, `normalize_path(path_prefix)` jest wywoływane dla każdego elementu, mimo że `path_prefix` się nie zmienia. Można to zoptymalizować, normalizując `path_prefix` raz przed pętlą.
3.  **Porównywanie ścieżek**: `pair_path.startswith(prefix)` jest używane do filtrowania po ścieżce. Jest to generalnie wydajne. Należy upewnić się, że normalizacja ścieżek (zarówno `pair_path` jak i `prefix`) jest spójna i poprawnie obsługuje różne separatory systemowe, wielkość liter (jeśli system plików jest niewrażliwy na wielkość liter, a porównanie ma być wrażliwe lub odwrotnie).

#### Refaktoryzacja i Czytelność Kodu:

1.  **Złożoność warunku filtrowania kolorów**: Logika sprawdzania `required_color_tag` (`"ALL"`, `"__NONE__"`, konkretny kolor) jest nieco rozbudowana. Można by ją uprościć lub uczynić bardziej czytelną, np. przez wydzielenie do osobnej funkcji pomocniczej.
2.  **Typowanie**: Plik używa type hints, co jest dobrą praktyką. Należy zapewnić ich spójność i kompletność.
3.  **Stałe dla kryteriów specjalnych**: Wartości stringowe jak `"ALL"` i `"__NONE__` dla `required_color_tag` mogłyby być zdefiniowane jako stałe (np. `COLOR_FILTER_ALL = "ALL"`, `COLOR_FILTER_NONE = "__NONE__"`) dla lepszej czytelności i uniknięcia literówek.
4.  **Obsługa `None` w `pair_color_tag`**: Jak wspomniano, bezpośrednie sprawdzenie `if pair_color_tag is None:` przed próbą użycia metod stringowych byłoby bezpieczniejsze.

#### Sugestie dotyczące UI (jeśli dotyczy):

- Wyniki filtrowania bezpośrednio wpływają na to, co jest wyświetlane w galerii. Wydajność tej funkcji jest kluczowa dla responsywności UI przy zmianie filtrów.

### Plan Testów

1.  **Testy jednostkowe dla `filter_file_pairs`**:

    - **Pusta lista wejściowa**: Sprawdzenie, czy zwraca pustą listę.
    - **Puste kryteria filtrowania**: Sprawdzenie, czy zwraca oryginalną listę.
    - **Filtrowanie po `min_stars`**:
      - Test z `min_stars = 0` (powinno zwrócić wszystko, co pasuje do innych kryteriów).
      - Test z `min_stars = 3` (powinno zwrócić tylko pary z >= 3 gwiazdkami).
      - Test z `min_stars` większym niż maksymalna liczba gwiazdek w danych (powinno zwrócić pustą listę).
    - **Filtrowanie po `required_color_tag`**:
      - Test z `required_color_tag = "ALL"` (powinno zwrócić wszystko, co pasuje do innych kryteriów).
      - Test z `required_color_tag = "__NONE__"` (powinno zwrócić tylko pary z pustym/None tagiem koloru).
      - Test z konkretnym kolorem (np. `"#FF0000"`), sprawdzając dopasowanie (również niewrażliwe na wielkość liter i z białymi znakami).
      - Test z kolorem, którego nie ma żadna para.
    - **Filtrowanie po `path_prefix`**:
      - Test z prefiksem pasującym do niektórych par.
      - Test z prefiksem niepasującym do żadnej pary.
      - Test z prefiksem będącą całą ścieżką do archiwum.
      - Test z normalizacją ścieżek (różne separatory, wielkość liter, jeśli to istotne).
    - **Kombinacja kryteriów**:
      - Test z `min_stars` i `required_color_tag`.
      - Test z `min_stars` i `path_prefix`.
      - Test z `required_color_tag` i `path_prefix`.
      - Test ze wszystkimi trzema kryteriami.
    - **Przypadki brzegowe dla tagów kolorów**:
      - `pair_color_tag` jest `None`, `required_color_tag` jest `"__NONE__"`.
      - `pair_color_tag` jest `None`, `required_color_tag` jest konkretnym kolorem.
      - `pair_color_tag` jest pustym stringiem, `required_color_tag` jest `"__NONE__"`.
    - **Nieprawidłowe typy w `filter_criteria`** (jeśli nie ma walidacji na wejściu, jak funkcja się zachowa – idealnie powinna zgłosić błąd lub zignorować nieprawidłowe kryterium).

2.  **Testy integracyjne**:
    - Sprawdzenie, czy zmiana filtrów w UI (jeśli w `FilterPanel`) poprawnie wywołuje `filter_file_pairs` i czy `GalleryManager` aktualizuje widok zgodnie z wynikami filtrowania.
    - Testowanie responsywności UI podczas filtrowania dużej liczby elementów.

### Śledzenie postępów

- [ ] **Analiza**: Ukończono.
- [ ] **Implementacja Poprawek**:
  - [ ] Dodanie walidacji typów dla wartości w `filter_criteria` lub zapewnienie odporności na nieprawidłowe typy.
  - [ ] Poprawa obsługi `None` dla `pair_color_tag` przed wywołaniem metod stringowych.
  - [ ] Optymalizacja logowania (np. możliwość wyłączenia szczegółowego logowania w pętli).
  - [ ] Optymalizacja `normalize_path(path_prefix)` (wywołanie raz przed pętlą).
  - [ ] (Opcjonalnie) Refaktoryzacja logiki filtrowania kolorów dla czytelności.
  - [ ] (Opcjonalnie) Zdefiniowanie stałych dla `"ALL"` i `"__NONE__"`.
- [ ] **Testowanie**:
  - [ ] Napisanie testów jednostkowych dla `filter_file_pairs`.
  - [ ] Przeprowadzenie testów integracyjnych z UI.
- [ ] **Dokumentacja**: Zaktualizowano `corrections.md`.

---

### 12. `src/models/file_pair.py`

### 📋 Identyfikacja

- **Plik główny:** `src/models/file_pair.py`
- **Priorytet:** 🟡 ŚREDNI
- **Zależności:**
  - `logging`
  - `os`
  - `PyQt6.QtCore.Qt`
  - `PyQt6.QtGui.QPixmap`

### 🔍 Analiza problemów

1.  **Błędy krytyczne/Potencjalne problemy:**

    - **Walidacja ścieżek w `__init__`**: Poprawnie używa `_normalize_path` i `os.path.isabs`, rzucając `ValueError` dla niepoprawnych ścieżek. To jest dobre.
    - **Ładowanie miniatury (`load_preview_thumbnail`):**
      - Oryginalny `QPixmap` jest ładowany w całości przed skalowaniem. Dla ekstremalnie dużych plików podglądu (choć mało prawdopodobne) mogłoby to zużyć dużo pamięci. W praktyce dla typowych podglądów powinno być akceptowalne.
      - `Qt.TransformationMode.SmoothTransformation` jest używane dla jakości, ale `FastTransformation` mogłoby być szybsze dla miniaturek, gdzie wydajność jest kluczowa. Można rozważyć uczynienie tego konfigurowalnym lub zmianę na `FastTransformation`.
      - Tworzenie placeholdera `QPixmap` jest dobrym fallbackiem.
    - **Pobieranie rozmiaru archiwum (`get_archive_size`):**
      - Jeśli plik nie istnieje, `self.archive_size_bytes` jest ustawiane na `0`. Może to być mylące, gdyż `0` może oznaczać pusty plik. Lepszym rozwiązaniem byłoby pozostawienie `None` lub użycie dedykowanej wartości oznaczającej błąd/brak pliku, chociaż obecne logowanie ostrzeżenia jest pomocne.

2.  **Optymalizacje:**

    - **Normalizacja ścieżek (`_normalize_path`):** Funkcja jest globalna w module. Mogłaby być metodą statyczną klasy `FilePair` lub, jeśli jest używana szerzej, przeniesiona do `src/utils/path_utils.py`.
    - **Wydajność metod `get_relative_*_path`:** `os.path.relpath` jest wywoływane za każdym razem. Jeśli te ścieżki są często odpytywane, a `working_directory` i ścieżki absolutne się nie zmieniają, można by je obliczyć raz i przechować. Jednak dla obiektu danych obecne podejście jest akceptowalne.
    - **Formatowanie rozmiaru (`get_formatted_archive_size`):** Logika jest wystarczająca dla obecnych potrzeb. Dla bardziej zaawansowanych formatowań można by rozważyć bibliotekę `humanize`.

3.  **Refaktoryzacja:**
    - **Zależność od Qt w modelu danych:** `FilePair` bezpośrednio używa `QPixmap`, co tworzy zależność modelu danych od biblioteki UI. Idealnie, modele danych powinny być niezależne od UI. Miniaturka mogłaby być przechowywana jako surowe dane (`bytes`) lub ścieżka, a konwersja do `QPixmap` odbywałaby się bliżej warstwy UI. Jest to jednak znacząca zmiana architektoniczna i obecny kompromis może być akceptowalny w projekcie silnie opartym na Qt.
    - **Przechowywanie metadanych:** Obecnie `stars` i `color_tag` są atrybutami. Dla większej liczby metadanych można by rozważyć osobną klasę `Metadata`.

### 🧪 Plan testów

1.  **Testy inicjalizacji `FilePair`:**
    - Poprawne ścieżki absolutne (archiwum i podgląd; tylko archiwum).
    - Niepoprawne ścieżki (względne) – sprawdzenie rzucania `ValueError`.
    - Normalizacja ścieżek (różne separatory).
    - Poprawne ustawienie `base_name`.
    - Domyślne wartości metadanych (`preview_thumbnail=None`, `archive_size_bytes=None`, `stars=0`, `color_tag=None`).
2.  **Testy metod `get_*_path` i `get_relative_*_path`:**
    - Sprawdzenie poprawności zwracanych ścieżek.
    - Obsługa `preview_path = None`.
3.  **Testy ładowania miniatury (`load_preview_thumbnail`, `get_preview_thumbnail`):**
    - Ładowanie z istniejącego, poprawnego pliku podglądu (sprawdzenie rozmiaru, typu `QPixmap`).
    - Próba ładowania z nieistniejącego pliku (powinien powstać placeholder).
    - Próba ładowania z uszkodzonego pliku (placeholder, logowanie błędu).
    - Sprawdzenie skalowania (różne `size` na wejściu).
4.  **Testy rozmiaru archiwum (`get_archive_size`, `get_formatted_archive_size`):**
    - Pobieranie rozmiaru dla istniejącego i nieistniejącego pliku.
    - Formatowanie rozmiaru dla różnych wielkości (B, KB, MB, GB) i dla wartości 0/`None` ("N/A").
5.  **Testy metadanych (`set_stars`, `get_stars`, `set_color_tag`, `get_color_tag`):**
    - Ustawianie i pobieranie poprawnej liczby gwiazdek (0-5).
    - Próba ustawienia niepoprawnej liczby gwiazdek (np. -1, 6, string) – sprawdzenie logowania i ustawienia na 0.
    - Ustawianie i pobieranie tagu koloru (string, `None`).
6.  **Test `__repr__`:**
    - Sprawdzenie poprawności i czytelności reprezentacji stringowej.

### 📊 Status tracking

- [ ] Kod zaimplementowany (analiza istniejącego kodu)
- [ ] Testy podstawowe (do napisania i przeprowadzenia)
- [ ] Testy integracji (w kontekście użycia `FilePair` w innych modułach)
- [ ] Testy wydajności (np. ładowanie wielu miniaturek, jeśli `FilePair` jest za to odpowiedzialny bezpośrednio)
- [ ] Dokumentacja zaktualizowana
- [ ] Gotowe do wdrożenia (po ewentualnych poprawkach i testach)

---

<details>
<summary>Analiza pliku `src/models/file_pair.py` - Średni priorytet</summary>

### Identyfikacja

- **Nazwa pliku:** `file_pair.py`
- **Priorytet:** Średni
- **Opis:** Model danych dla par plików lub pojedynczych plików z metadanymi.
- **Kluczowe funkcjonalności:** Reprezentacja struktury danych pliku, jego ścieżki, metadanych, potencjalnie powiązanych plików (np. RAW + JPG).
- **Zależności:** Wiele komponentów logicznych i UI, które operują na plikach i ich właściwościach.

### Analiza problemów

- **Błędy krytyczne (potencjalne):**
  - Niespójność danych, jeśli obiekt `FilePair` jest modyfikowany z wielu miejsc bez odpowiedniej synchronizacji lub mechanizmów walidacji.
  - Błędy przy serializacji/deserializacji obiektu, jeśli jest taka potrzeba (np. do zapisu stanu).
- **Obszary do optymalizacji:**
  - Upewnienie się, że model jest jak najbardziej "lekki" i zawiera tylko niezbędne dane, aby nie spowalniać operacji na dużych listach obiektów.
  - Rozważenie użycia `__slots__` dla optymalizacji zużycia pamięci, jeśli tworzonych jest bardzo dużo instancji `FilePair`.
  - Zapewnienie metod do łatwego dostępu i modyfikacji atrybutów, z ewentualną walidacją.
  - Jeśli model ma obsługiwać różne typy "par" (np. plik główny + plik pomocniczy, plik przed + plik po), upewnienie się, że struktura jest wystarczająco elastyczna.
- **Refaktoryzacja:**
  - Zastosowanie typowania (type hints) dla wszystkich atrybutów i metod.
  - Przejrzyste nazewnictwo atrybutów i metod.
  - Jeśli klasa staje się zbyt rozbudowana, rozważenie podziału na mniejsze, bardziej wyspecjalizowane klasy lub użycie kompozycji.
  - Dokumentacja (docstrings) dla klasy i jej publicznych metod.

### Plan testów

- **Testy jednostkowe:**
  - Testowanie tworzenia instancji `FilePair` z różnymi danymi wejściowymi.
  - Testowanie metod dostępowych (gettery/settery), jeśli istnieją.
  - Testowanie logiki biznesowej zawartej w modelu (np. metody porównujące, metody zwracające przetworzone dane).
  - Testowanie obsługi przypadków brzegowych (np. brakujące dane, niepoprawne typy danych).
- **Testy integracyjne:**
  - Sprawdzenie, jak model `FilePair` jest używany przez inne komponenty (np. `scanner.py`, `gallery_manager.py`) and czy integracja jest poprawna.
- **Testy UI (manualne lub zautomatyzowane):**
  - Pośrednio, poprzez testowanie komponentów UI, które wyświetlają dane z obiektów `FilePair`.

### Śledzenie postępów

- [x] Analiza kodu zakończona.
- [x] Zidentyfikowane problemy i sugestie zapisane.
- [x] Plan testów przygotowany.
- [ ] (Opcjonalnie) Utworzone zadania w systemie śledzenia błędów/zadań.
</details>

<details>
<summary>Analiza <code>src/ui/widgets/file_tile_widget.py</code></summary>

**Identyfikacja pliku:**
Plik `src/ui/widgets/file_tile_widget.py` jest odpowiedzialny za renderowanie pojedynczego kafelka pliku w widoku galerii. Powinien wyświetlać miniaturkę, nazwę pliku i potencjalnie inne istotne metadane. Jest to kluczowy komponent wizualny dla `GalleryManager`, wpływający na interakcję użytkownika z listą plików.

**Potencjalne problemy:**

1.  **Krytyczne błędy:**
    - Niespójność danych, jeśli obiekt `FileTileWidget` jest modyfikowany z wielu miejsc bez odpowiedniej synchronizacji lub mechanizmów walidacji.
    - Błędy przy serializacji/deserializacji obiektu, jeśli jest taka potrzeba (np. do zapisu stanu).
2.  **Obszary do optymalizacji:**
    - **Wydajność renderowania:** Metoda odpowiedzialna za rysowanie widgetu (np. `paintEvent` w Qt) może wymagać optymalizacji, aby zapewnić płynne przewijanie galerii z dużą liczbą kafelków. Należy unikać skomplikowanych operacji rysowania w głównym wątku.
    - **Zarządzanie zasobami:** Efektywne wykorzystanie miniaturek z `ThumbnailCache` w celu unikania ich wielokrotnego generowania. Rozważenie leniwego ładowania danych lub elementów wizualnych, które nie są od razu widoczne.
    - **Responsywność UI:** Zapewnienie, że interakcje użytkownika z kafelkiem (np. kliknięcie, zaznaczenie, najechanie myszą) są obsługiwane szybko i nie blokują interfejsu.
    - **Aktualizacja danych:** Mechanizm aktualizacji wyglądu kafelka w odpowiedzi na zmiany w danych bazowych (np. zmiana metadanych pliku) powinien być efektywny.
3.  **Potrzeba refaktoryzacji:**
    - **Separacja odpowiedzialności (SoC):** Logika pobierania i formatowania danych powinna być oddzielona od logiki stricte prezentacyjnej (rysowania). Model danych (`FilePair`) powinien dostarczać widgetowi gotowe lub łatwo przetwarzalne informacje.
    - **Stylizacja:** Zastosowanie zewnętrznych stylów (np. z `styles.qss` lub dedykowanego `tile_styles.py`) zamiast hardcodowania wartości stylów (kolory, czcionki, marginesy) bezpośrednio w kodzie widgetu. Umożliwi to łatwiejszą zmianę wyglądu i spójność.
    - **Czytelność i konserwacja kodu:** Wprowadzenie lub uzupełnienie type hintów, dodanie klarownych komentarzy wyjaśniających bardziej złożone fragmenty kodu oraz poprawa nazewnictwa zmiennych i metod.
    - **Obsługa zdarzeń:** Ustandaryzowanie i uproszczenie obsługi zdarzeń myszy (np. pojedyncze kliknięcie, podwójne kliknięcie, menu kontekstowe), potencjalnie przez emitowanie sygnałów do `GalleryManager`.

**Plan testów:**

1.  **Testy jednostkowe (jeśli widget ma własną logikę):**
    - Testowanie tworzenia widgetu z różnymi typami danych wejściowymi (prawidłowe, niekompletne, błędne dane z `FilePair`).
    - Testowanie metod dostępowych (gettery/settery), jeśli istnieją.
    - Testowanie logiki biznesowej zawartej w modelu (np. metody porównujące, metody zwracające przetworzone dane).
    - Testowanie obsługi przypadków brzegowych (np. brakujące dane, niepoprawne typy danych).
2.  **Testy integracyjne (z `GalleryManager` i `ThumbnailCache` po refaktoryzacji):**
    - Sprawdzenie, czy widget poprawnie wyświetla miniaturki dostarczane przez `ThumbnailCache`.
    - Testowanie poprawnego renderowania widgetu w kontekście siatki lub listy w `GalleryManager`.
    - Weryfikacja, czy interakcje z widgetem (np. kliknięcie) poprawnie wywołują odpowiednie akcje lub sygnały obsługiwane przez `GalleryManager`.
3.  **Testy wydajnościowe:**
    - Analiza czasu renderowania pojedynczego kafelka.
    - Testowanie wydajności przy wyświetlaniu i przewijaniu galerii z bardzo dużą liczbą kafelków (np. setki, tysiące).
    - Monitorowanie zużycia pamięci przez widgety, szczególnie przy dynamicznym dodawaniu/usuwaniu.
4.  **Testy UI (manualne):**
    - Wizualna weryfikacja poprawności wyświetlania kafelków w różnych stanach i z różnymi danymi.
    - Testowanie responsywności na interakcje użytkownika (kliknięcia, zaznaczanie).
    - Testowanie wyglądu przy różnych rozdzielczościach i ustawieniach systemowych (jeśli dotyczy).

---

### Analiza pliku: `src/ui/widgets/filter_panel.py`

**Identyfikacja pliku:**
Plik `src/ui/widgets/filter_panel.py` definiuje widget `FilterPanel`, który jest używany w interfejsie użytkownika do filtrowania elementów wyświetlanych w galerii. Umożliwia filtrowanie na podstawie minimalnej liczby gwiazdek oraz tagu koloru.

**Potencjalne problemy:**

1.  **Krytyczne błędy:**

    - Brak bezpośrednich krytycznych błędów widocznych w kodzie. Widget jest stosunkowo prosty.
    - Potencjalny problem mógłby wystąpić, gdyby `app_config.PREDEFINED_COLORS_FILTER` było puste lub miało nieprawidłową strukturę, ale zakłada się, że `app_config` dostarcza poprawne dane.

2.  **Obszary do optymalizacji:**

    - **Wydajność:** Dla obecnej liczby opcji filtrowania, wydajność nie powinna stanowić problemu. Jeśli liczba filtrów lub opcji w filtrach znacznie by wzrosła, sposób ich tworzenia i zarządzania mógłby wymagać optymalizacji.
    - **Rozszerzalność:** Dodawanie nowych typów filtrów (np. filtr po dacie, po nazwie pliku) wymagałoby modyfikacji metody `_init_ui` oraz `get_filter_criteria`. Można by rozważyć bardziej dynamiczny sposób tworzenia filtrów, np. na podstawie konfiguracji.

3.  **Potrzeba refaktoryzacji:**
    - **Stałe wartości:** Wysokość panelu (`self.setFixedHeight(60)`) jest zahardcodowana. Można by ją przenieść do stałej lub umożliwić jej konfigurację, jeśli byłaby taka potrzeba.
    - **Logika `get_filter_criteria`:** Wartości domyślne (`min_stars = 0`, `req_color = "ALL"`) są przypisywane, jeśli `currentData()` zwróci `None`. Jest to bezpieczne, ale można by rozważyć inicjalizację QComboBox tak, aby zawsze miały wybraną poprawną wartość domyślną, eliminując potrzebę sprawdzania `None`.
    - **Stylizacja:** Zastosowanie zewnętrznych stylów (np. z `styles.qss` lub dedykowanego `tile_styles.py`) zamiast hardcodowania wartości stylów (kolory, czcionki, marginesy) bezpośrednio w kodzie widgetu. Umożliwi to łatwiejszą zmianę wyglądu i spójność.
    - **Typowanie:** Plik używa type hints, co jest dobrą praktyką. Należy utrzymać ich spójność.

**Plan testów:**

1.  **Testy funkcjonalności podstawowej:**

    - **Inicjalizacja:** Sprawdzenie, czy widget i wszystkie jego kontrolki są poprawnie tworzone i wyświetlane.
    - **`update_controls`:**
      - Test z `file_pair = None` (kontrolki powinny być wyłączone, pola puste/domyślne).
      - Test z poprawnym obiektem `FilePair` (sprawdzenie, czy nazwa, gwiazdki, tag koloru są poprawnie wyświetlane).
    - **Interakcja z kontrolkami:**
      - Edycja nazwy pliku w `base_name_edit`.
      - Kliknięcie przycisków gwiazdki (sprawdzenie wizualnej zmiany i wewnętrznego stanu `_current_stars`).
      - Zmiana wyboru w `color_tag_combo`.
    - **`_apply_changes`:**
      - Sprawdzenie, czy zmiany z UI (nazwa, gwiazdki, kolor) są poprawnie odzwierciedlane w obiekcie `FilePair` po kliknięciu "Zastosuj".
      - Sprawdzenie, czy sygnał `metadata_changed` jest emitowany z poprawnym `FilePair`.
    - **`_revert_changes`:**
      - Sprawdzenie, czy zmiany w UI są cofane do stanu z `_current_file_pair` po kliknięciu "Anuluj".

2.  **Testy obsługi błędów i przypadków brzegowych:**

    - Przekazanie niepoprawnego typu zamiast `FilePair` do `set_file_pair` (jak widget zareaguje – idealnie powinien zalogować błąd lub zignorować).
    - Test `update_color_tag_display` z niestandardowym `color_hex_string` (sprawdzenie logu i ustawienia na "Brak").
    - Test `update_color_tag_display` z `color_hex_string = None` i `color_hex_string = ""_STRING_`.

3.  **Testy integracyjne (z `FileTileWidget` i `ThumbnailCache` po refaktoryzacji):**
    - Sprawdzenie, czy widget poprawnie wyświetla miniaturki dostarczane przez `ThumbnailCache`.
    - Testowanie poprawnego renderowania widgetu w kontekście siatki lub listy w `GalleryManager`.
    - Weryfikacja, czy interakcje z widgetem (np. kliknięcie) poprawnie wywołują odpowiednie akcje lub sygnały obsługiwane przez `GalleryManager`.
4.  **Testy wydajnościowe:**
    - Wizualna ocena płynności animacji i przejść.
    - Testowanie responsywności na różne interakcje użytkownika (kliknięcia, przeciąganie).
    - Testowanie działania przy różnych rozdzielczościach i skalowaniu UI.

### 13. `src/ui/widgets/preview_dialog.py`

#### 📋 Identyfikacja

- **Ścieżka Pliku:** `src/ui/widgets/preview_dialog.py`
- **Priorytet:** 🟡 ŚREDNI
- **Opis:** Dialog podglądu pliku, wyświetlający większy podgląd obrazu lub zawartość innego pliku.

### 14. `src/ui/file_operations_ui.py`

#### 📋 Identyfikacja

- **Ścieżka Pliku:** `src/ui/file_operations_ui.py`
- **Priorytet:** 🟡 ŚREDNI
- **Opis:** Interfejs użytkownika dla operacji na plikach (kopiowanie, przenoszenie, usuwanie).

### 15. `src/utils/image_utils.py`

#### 📋 Identyfikacja

- **Ścieżka Pliku:** `src/utils/image_utils.py`
- **Priorytet:** 🟡 ŚREDNI
- **Opis:** Narzędzia do obsługi obrazów, tworzenia miniaturek, odczytu właściwości obrazów.

### 16. `src/ui/widgets/metadata_controls_widget.py`

#### 📋 Identyfikacja

- **Ścieżka Pliku:** `src/ui/widgets/metadata_controls_widget.py`
- **Priorytet:** 🟡 ŚREDNI
- **Opis:** Widget kontrolek metadanych zawierający pola edycyjne i przyciski do zarządzania metadanymi.

### 21. `src/ui/directory_tree_manager.py`

#### 📋 Identyfikacja

- **Ścieżka Pliku:** `src/ui/directory_tree_manager.py`
- **Priorytet:** 🟡 ŚREDNI
- **Opis:** Zarządzanie drzewem katalogów w interfejsie użytkownika.

### 22. `src/ui/widgets/file_tile_widget.py`

#### 📋 Identyfikacja

- **Ścieżka Pliku:** `src/ui/widgets/file_tile_widget.py`
- **Priorytet:** 🟡 ŚREDNI
- **Opis:** Widget kafelka pliku wyświetlający pojedynczy plik w widoku galerii.

### 23. `src/ui/widgets/filter_panel.py`

#### 📋 Identyfikacja

- **Ścieżka Pliku:** `src/ui/widgets/filter_panel.py`
- **Priorytet:** 🟡 ŚREDNI
- **Opis:** Panel filtrów do filtrowania galerii.

---

## 🟢 NISKI PRIORYTET

### 17. `styles.qss`

### 1. Identyfikacja

- **Ścieżka Pliku:** `styles.qss`
- **Priorytet:** Niski (zgodnie z `code_map.md`)
- **Opis:** Arkusz stylów Qt (QSS) definiujący wygląd komponentów UI aplikacji.
- **Zależności:** Wszystkie komponenty UI, które mają być stylizowane; `main_window.py` lub `main.py` do załadowania stylów.

### 2. Analiza Problemów

- **Błędy Krytyczne:**
  - Błędy składni QSS uniemożliwiające wczytanie lub poprawne zastosowanie stylów.
  - Nieprawidłowe selektory, które nie pasują do żadnych widgetów lub pasują do zbyt wielu, powodując nieoczekiwany wygląd.
- **Potencjalne Problemy:**
  - Niespójność stylów między różnymi częściami aplikacji.
  - Zbyt skomplikowane lub nadmiarowe reguły, które mogą wpływać na wydajność renderowania (choć zazwyczaj niewielki wpływ).
  - Brak komentarzy utrudniający zrozumienie i konserwację.
  - Użycie "hardcoded" wartości (np. kolory, rozmiary czcionek), które powinny być zdefiniowane jako zmienne (jeśli QSS to wspiera lub poprzez preprocessing).
  - Brak obsługi różnych stanów widgetów (np. `:hover`, `:disabled`, `:checked`).
  - Niezaładowanie pliku stylów lub załadowanie go w nieprawidłowym momencie cyklu życia aplikacji.
- **Optymalizacje:**
  - Uproszczenie selektorów dla lepszej wydajności i czytelności.
  - Grupowanie wspólnych stylów.
  - Wykorzystanie dziedziczenia stylów tam, gdzie to możliwe.
  - Organizacja pliku QSS w logiczne sekcje za pomocą komentarzy.
  - Zastosowanie właściwości `qproperty-` do ustawiania niestandardowych właściwości, które mogą być używane w QSS.
- **Refaktoryzacja:**
  - Wprowadzenie zmiennych dla kolorów, czcionek, itp., poprzez komentarze i konwencję, a następnie zastępowane skryptem lub ręcznie, lub użycie mechanizmów Qt, jeśli dostępne (np. palety).
  - Podział na mniejsze, zarządzalne pliki QSS, jeśli arkusz jest bardzo duży (choć dla pojedynczego `styles.qss` może to nie być konieczne, chyba że stanie się bardzo rozbudowany).
  - Upewnienie się, że style są ładowane centralnie i tylko raz, np. w `main_window.py` lub `main.py`.

### 3. Plan Testów

- **Testy Funkcjonalne:**
  - Weryfikacja, czy widgety kafelków poprawnie przyjmują i wyświetlają style.
  - Testowanie wyglądu w różnych stanach widgetów (aktywny, nieaktywny, najechany myszką, zaznaczony, wyłączony itp.).
  - Sprawdzenie, czy zmiany w pliku `styles.qss` są odzwierciedlane w aplikacji (najlepiej po ponownym uruchomieniu lub zaimplementowaniu mechanizmu przeładowywania stylów na żywo, jeśli to możliwe).
- **Testy Wizualne:**
  - Porównanie wyglądu UI z makietami lub oczekiwanym designem.
  - Sprawdzenie spójności wizualnej pomiędzy różnymi oknami i dialogami aplikacji.
- \*\*Testy Międzyplatformowe (jeśli dotyczy):
  - Sprawdzenie, czy style wyglądają spójnie i poprawnie na różnych systemach operacyjnych, na których aplikacja ma działać, biorąc pod uwagę możliwe różnice w renderowaniu Qt.

### 4. Śledzenie Postępów

- [ ] Analiza zakończona
- [ ] Identyfikacja problemów zakończona
- [ ] Plan naprawczy zdefiniowany
- [ ] Implementacja poprawek (jeśli dotyczy)
- [ ] Testowanie wykonane
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)

---

### 18. `src/utils/logging_config.py`

#### 📋 Identyfikacja

- **Ścieżka Pliku:** `src/utils/logging_config.py`
- **Priorytet:** 🟢 Niski
- **Opis:** Moduł konfigurujący system logowania aplikacji.

### 19. `src/utils/path_utils.py`

#### 📋 Identyfikacja

- **Ścieżka Pliku:** `src/utils/path_utils.py`
- **Priorytet:** 🟢 Niski
- **Opis:** Moduł z narzędziami pomocniczymi do operacji na ścieżkach.

### 20. `src/ui/widgets/tile_styles.py`

#### 📋 Identyfikacja

- **Ścieżka Pliku:** `src/ui/widgets/tile_styles.py`
- **Priorytet:** Niski (jeśli plik jest pusty, może być pozostałością lub miejscem na przyszłe style)
- **Opis:** Prawdopodobnie moduł przeznaczony do definiowania stylów (QSS lub stałych Pythona) specyficznych dla widgetów kafelków (np. `FileTileWidget`). Obecnie plik jest pusty.
- **Zależności:** Potencjalnie `FileTileWidget` lub inne widgety, które miałyby używać tych stylów. `styles.qss` jeśli style miałyby być tam przeniesione lub zintegrowane.

### 2. Analiza Problemów

- **Błędy Krytyczne:**
  - Brak, ponieważ plik jest pusty.
- **Potencjalne Problemy:**
  - Jeśli plik jest importowany, a miał zawierać definicje, jego pusty stan może prowadzić do `ImportError` lub `AttributeError`, jeśli oczekiwane są konkretne stałe/funkcje.
  - Niejasny cel pliku, jeśli nie jest używany. Może to być "martwy kod" lub pozostałość po refaktoryzacji.
  - Jeśli style dla kafelków są zdefiniowane gdzie indziej (np. w głównym `styles.qss` lub bezpośrednio w kodzie widgetu), ten plik może być zbędny i wprowadzać zamieszanie.
- **Optymalizacje:**
  - Jeśli plik nie jest i nie będzie używany, powinien zostać usunięty, aby uprościć strukturę projektu.
  - Jeśli jest przeznaczony na przyszłe style, można dodać komentarz wyjaśniający jego cel.
  - Jeśli style kafelków są rozproszone, ten plik mógłby stać się centralnym miejscem do ich definiowania, poprawiając organizację.
- **Refaktoryzacja:**
  - Jeśli style są zdefiniowane w `FileTileWidget` lub innym miejscu, a ten plik miał je grupować, należy przenieść odpowiednie definicje stylów tutaj.
  - Jeśli style są w `styles.qss`, a ten plik miałby zawierać dynamicznie generowane style lub stałe Pythona używane do stylizacji, należy to zaimplementować.
  - Decyzja: Czy ten plik jest potrzebny? Jeśli tak, jaka jest jego dokładna rola (przechowywanie stringów QSS, stałych kolorów, dynamiczne generowanie stylów)?

### 3. Plan Testów

- **Testy Funkcjonalne:**
  - Jeśli plik zostanie wypełniony stylami: Sprawdzić, czy widgety kafelków poprawnie przyjmują i wyświetlają te style.
  - Jeśli plik jest importowany: Upewnić się, że jego pusty stan nie powoduje błędów podczas importu lub działania aplikacji.
- **Przegląd Kodu:**
  - Sprawdzić, czy `tile_styles.py` jest gdziekolwiek importowany w projekcie.
  - Jeśli nie jest importowany i nie ma planów na jego użycie, rozważyć usunięcie.
  - Jeśli jest importowany, zrozumieć, w jakim celu i czy jego pusty stan jest problemem.

### 4. Śledzenie Statusu

- [ ] Analiza zakończona
- [ ] Identyfikacja problemów zakończona
- [ ] Plan naprawczy zdefiniowany
- [ ] Implementacja poprawek (jeśli dotyczy)
- [ ] Testowanie wykonane
- [ ] Dokumentacja zaktualizowana (jeśli dotyczy)
</details>
