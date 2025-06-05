# Raport Wydajności Aplikacji CFAB_3DHUB

Data analizy: 2025-06-05

## 1. Wprowadzenie

Niniejszy raport przedstawia analizę wydajności aplikacji CFAB_3DHUB, ze szczególnym naciskiem na problemy związane z interfejsem użytkownika (UI) podczas ładowania i interakcji z galerią plików. Użytkownicy zgłaszają, że przy załadowanej galerii UI staje się praktycznie nieużywalne, co uniemożliwia skalowanie i inne interakcje. Celem raportu jest zidentyfikowanie głównych wąskich gardeł wydajnościowych oraz zarekomendowanie konkretnych działań optymalizacyjnych.

## 2. Analiza Obecnego Stanu (Główne Wąskie Gardła)

Na podstawie analizy kodu oraz dostępnej dokumentacji (w tym `TODO.md`, `corrections.md`, `PRD.md`) zidentyfikowano następujące obszary jako główne przyczyny problemów z wydajnością:

### 2.1. Ładowanie i Wyświetlanie Galerii (`MainWindow._update_gallery_view`, `FileTileWidget`)

- **Blokowanie Głównego Wątku UI przez Miniatury:**

  - Mimo istnienia `ThumbnailLoaderWorker` w `FileTileWidget` do asynchronicznego ładowania miniatur, inicjalne ładowanie dużej liczby kafelków lub zmiana ich rozmiaru może nadal prowadzić do problemów. Należy zweryfikować, czy proces tworzenia instancji `FileTileWidget` i inicjowania ładowania miniatur nie odbywa się w sposób, który sumarycznie blokuje UI, zanim wątki robocze podejmą pracę.
  - Samo wywołanie `_load_thumbnail_async` dla setek kafelków, nawet jeśli rozpoczyna pracę w tle, może generować narzut w głównym wątku.

- **Zarządzanie Widgetami Kafelków:**

  - Metoda `_update_gallery_view` w `MainWindow` usuwa wszystkie widgety z layoutu (`self.tiles_layout.takeAt(0)`) i potencjalnie dodaje je na nowo. Chociaż widgety nie są usuwane z pamięci (`deleteLater()`) od razu, operacje na layoucie dla dużej liczby elementów są kosztowne.
  - Komentarze w kodzie (`_update_gallery_view`) wskazują na świadomość nieefektywności niektórych podejść (np. iterowanie po `self.gallery_tile_widgets.items()` w celu ukrycia widgetów, które nie są na liście `self.file_pairs_list`).
  - Brak mechanizmu recyklingu widgetów – dla każdej pary plików (nawet tej samej, jeśli widok jest odświeżany) może być tworzony nowy widget lub przynajmniej intensywnie rekonfigurowany.

- **Aktualizacja Widoku przy Filtrowaniu/Zmianie Rozmiaru:**

  - Zmiana filtrów lub rozmiaru miniatur (`_update_thumbnail_size` wywołujące `_apply_filters_and_update_view`, a następnie `_update_gallery_view`) prawdopodobnie prowadzi do pełnego przebudowania layoutu galerii, co jest nieefektywne przy dużej liczbie elementów.

- **Renderowanie Dużej Liczby Elementów w `QGridLayout`:**
  - Nawet przy asynchronicznym ładowaniu danych, samo zarządzanie i renderowanie setek lub tysięcy indywidualnych widgetów (`FileTileWidget`) w `QGridLayout` może stanowić wąskie gardło. `QGridLayout` jest elastyczny, ale niekoniecznie zoptymalizowany pod kątem wirtualizacji czy obsługi ogromnej liczby dynamicznych elementów.

### 2.2. Skanowanie Folderów (`scan_folder_for_pairs`, `MainWindow._select_working_directory`)

- **Potencjalne Blokowanie UI Mimo `ScanFolderWorker`:**
  - Klasa `ScanFolderWorker` służy do skanowania folderu w osobnym wątku. Kluczowe jest, aby cała operacja skanowania, włącznie z identyfikacją par i plików niesparowanych, odbywała się w tym wątku.
  - Po zakończeniu skanowania (`_handle_scan_finished`), następuje przetwarzanie wyników i inicjalizacja/aktualizacja UI. Jeśli `found_pairs` jest bardzo dużą listą, operacje takie jak tworzenie `FileTileWidget` dla każdej pary (nawet jeśli tylko inicjalizacja) lub wstępne przetwarzanie tej listy w głównym wątku mogą być czasochłonne.

### 2.3. Operacje na Plikach i Metadanych (`file_operations`, `metadata_manager`)

- **Dostęp do Dysku w Głównym Wątku:**

  - Operacje takie jak zmiana nazwy (`_rename_file_pair`), usuwanie (`_delete_file_pair`), przenoszenie (obsługa `dropEvent`) angażują moduł `file_operations`. Jeśli te operacje są synchroniczne i blokujące, będą powodować "zamrożenie" UI.
  - Zapis i odczyt metadanych (`_save_metadata`, `metadata_manager.apply_metadata_to_file_pairs`) również wiążą się z operacjami I/O. Częste lub długotrwałe operacje na pliku metadanych (np. duży plik JSON) w głównym wątku będą problematyczne.

- **Naruszenie Zasady Pojedynczej Odpowiedzialności (SRP) w Modelu Danych:**

  - Analiza pliku `src/models/file_pair.py` wykazała, że klasa modelu `FilePair` zawiera logikę bezpośrednio modyfikującą system plików (metody `rename`, `delete`, `move`). Mieszanie odpowiedzialności modelu danych z operacjami plikowymi utrudnia testowanie, centralizację logiki i może prowadzić do niespójności. Logika ta powinna znajdować się w module `src/logic/file_operations.py`.

- **Częste Zapisy Metadanych:**
  - Metadane są zapisywane po różnych akcjach (np. zmiana gwiazdek `_handle_stars_changed`, zmiana koloru `_handle_color_tag_changed`, ręczne parowanie `_handle_manual_pairing`, usuwanie pary). Jeśli te akcje są wykonywane często, prowadzi to do wielokrotnych, potencjalnie blokujących zapisów na dysku.

### 2.4. Ogólna Struktura i Zarządzanie Stanem w `MainWindow`

- **Monolityczna Klasa `MainWindow`:**

  - Jak wskazano w `code_map.md` i `corrections.md`, klasa `MainWindow` jest bardzo duża. Utrudnia to rozumienie przepływu danych, zarządzanie stanem i izolowanie problemów wydajnościowych. Poszczególne funkcjonalności (zarządzanie galerią, filtrowanie, obsługa drzewa folderów, operacje na plikach) są mocno splecione.

- **Przestarzały, Nieużywany Kod:**

  - Zidentyfikowano istnienie pliku `src/ui/main_window_tree_ops.py`, który jest przestarzały i stanowi martwy kod. Jego funkcjonalność została w pełni zintegrowana z klasą `MainWindow`. Obecność takiego pliku komplikuje strukturę projektu i może prowadzić do błędów w utrzymaniu.

- **Przepływ Danych i Aktualizacje UI:**
  - Zmiany w danych (np. `self.all_file_pairs`, `self.file_pairs_list`) wywołują aktualizacje UI. Często prowadzi to do pełnego odświeżenia galerii (`_update_gallery_view`) zamiast bardziej granularnych, celowanych aktualizacji. Na przykład, zmiana tagu dla jednego pliku nie powinna wymagać pełnego przeliczenia layoutu dla wszystkich kafelków.

## 3. Zalecenia dotyczące Optymalizacji

### 3.1. Wielowątkowość i Operacje Asynchroniczne

- **Kluczowe Operacje do Przeniesienia do Wątków Roboczych:**

  - **Ładowanie Miniatur:** Upewnić się, że `ThumbnailLoaderWorker` jest efektywnie wykorzystywany. Rozważyć użycie `QThreadPool` do zarządzania pulą wątków dla ładowania miniatur, co może lepiej zarządzać zasobami przy dużej liczbie jednoczesnych żądań.
  - **Skanowanie Folderów:** Kontynuować użycie `ScanFolderWorker`, ale zoptymalizować przetwarzanie wyników po zakończeniu skanowania, aby zminimalizować pracę w głównym wątku.
  - **Operacje Plikowe:** Wszystkie operacje z modułu `file_operations` (tworzenie, zmiana nazwy, usuwanie, przenoszenie plików) powinny być wykonywane asynchronicznie, z odpowiednim powiadamianiem UI o postępie i wyniku.
  - **Zapis/Odczyt Metadanych:** Długotrwałe operacje na plikach metadanych również powinny trafić do osobnego wątku.

- **Komunikacja z Głównym Wątkiem:** Konsekwentnie używać sygnałów i slotów Qt do bezpiecznej komunikacji między wątkami roboczymi a głównym wątkiem UI. Aktualizacje widgetów muszą następować wyłącznie w głównym wątku.

### 3.2. Optymalizacja Renderowania i Zarządzania Galerią

- **Wirtualizacja / Lazy Loading / Stronicowanie:**

  - **Rozważyć `QListView` lub `QTableView` z Własnym Modelem i Delegatem:** Dla bardzo dużych zbiorów danych, te komponenty Qt są znacznie bardziej wydajne, ponieważ renderują tylko widoczne elementy. Wymaga to zaimplementowania własnego modelu danych (dziedziczącego po `QAbstractListModel` lub `QAbstractTableModel`) oraz delegata (dziedziczącego po `QStyledItemDelegate`) do rysowania kafelków. To najbardziej fundamentalna zmiana, ale dająca największe korzyści przy skalowalności.
  - **Jeśli `QGridLayout` pozostaje:** Zaimplementować "lazy loading" widgetów. Tworzyć `FileTileWidget` tylko wtedy, gdy stają się widoczne (np. podczas przewijania). To wymagałoby bardziej zaawansowanego zarządzania scrollem i layoutem.

- **Recykling Widgetów:**

  - Zamiast niszczyć i tworzyć widgety kafelków na nowo, utrzymywać pulę istniejących widgetów i ponownie ich używać, aktualizując tylko ich zawartość. To redukuje narzut związany z tworzeniem obiektów i zarządzaniem pamięcią.

- **Efektywniejsze Aktualizacje Layoutu:**

  - Przy filtrowaniu: Zamiast usuwać i dodawać widgety do layoutu, po prostu zmieniać ich widoczność (`setVisible(True/False)`). `QGridLayout` powinien sobie z tym poradzić, ale nadal może być to kosztowne przy dużej liczbie elementów.
  - Minimalizować liczbę operacji modyfikujących layout. Jeśli to możliwe, grupować zmiany.

- **Debouncing/Throttling dla Interakcji:**
  - Dla operacji takich jak zmiana rozmiaru miniatur suwakiem, zastosować technikę "debouncing" (opóźnienie wykonania akcji do momentu, gdy użytkownik przestanie wchodzić w interakcję przez krótki czas) lub "throttling" (ograniczenie częstotliwości wykonywania akcji). To zapobiegnie wielokrotnym, kosztownym aktualizacjom galerii podczas przeciągania suwaka.

### 3.3. Zarządzanie i Cache'owanie Miniatur

- **Cache'owanie Miniatur na Dysku:**

  - Implementacja systemu cache'owania wygenerowanych miniatur na dysku (np. w podfolderze `.cache/.thumbnails` w katalogu roboczym lub w katalogu aplikacji użytkownika). Kluczem do cache'u może być ścieżka do pliku i rozmiar miniatury. To znacząco przyspieszy ładowanie galerii przy kolejnych uruchomieniach lub ponownym otwarciu folderu (zgodnie z sugestią w `DATA.md`).

- **Dynamiczne Ładowanie Miniatur o Odpowiedniej Jakości:**
  - Podczas zmiany rozmiaru kafelków (`_update_thumbnail_size`), `FileTileWidget` powinien żądać wygenerowania (lub pobrania z cache'u) miniatury o nowym, odpowiednim rozmiarze. To zapobiegnie skalowaniu niskiej jakości małych miniatur do dużych rozmiarów i poprawi wrażenia wizualne (zgodnie z `TODO.md`).

### 3.4. Optymalizacja Operacji Plikowych i Metadanych

- **Asynchroniczne Operacje Plikowe:** Jak wspomniano w 3.1, przenieść do wątków.
- **Wsadowy Zapis Metadanych / Zapis w Tle:**
  - Zamiast zapisywać metadane po każdej pojedynczej zmianie, rozważyć mechanizm "brudnej flagi" i zapisywać zmiany zbiorczo po pewnym czasie nieaktywności lub przed zamknięciem aplikacji.
  - Alternatywnie, sam zapis metadanych może odbywać się w tle, nie blokując UI.
- **Refaktoryzacja Modelu `FilePair`:** Zgodnie z Zasadą Pojedynczej Odpowiedzialności, należy przenieść logikę operacji na plikach (`rename`, `delete`, `move`) z klasy modelu `src/models/file_pair.py` do scentralizowanego modułu `src/logic/file_operations.py`.

### 3.5. Refaktoryzacja Kodu

- **Podział `MainWindow`:**

  - Wydzielić logikę zarządzania galerią (tworzenie kafelków, aktualizacja layoutu, obsługa przewijania) do osobnej klasy pomocniczej.
  - Wydzielić logikę filtrowania i sortowania.
  - Rozważyć model MVVM (Model-View-ViewModel) lub podobny wzorzec architektoniczny, aby lepiej oddzielić logikę od prezentacji.

- **Usunięcie Martwego Kodu:** Należy usunąć przestarzały plik `src/ui/main_window_tree_ops.py`, którego funkcjonalność jest już zintegrowana z `MainWindow`. Uprości to strukturę projektu.

- **Usprawnienie Zarządzania Stanem:**
  - Zapewnić klarowny i efektywny sposób propagacji zmian stanu (np. zmiana filtrów, aktualizacja listy plików) do odpowiednich komponentów UI, minimalizując pełne przebudowy.

## 4. Proponowane Kroki Implementacyjne (Priorytety)

1.  **Krok 1: Podstawowa Wielowątkowość dla Najbardziej Blokujących Operacji:**

    - **Priorytet:** Najwyższy.
    - Upewnić się, że **skanowanie folderów** (`ScanFolderWorker`) jest w pełni asynchroniczne i nie blokuje UI podczas inicjalizacji ani przetwarzania wyników.
    - Zapewnić, że **ładowanie miniatur** (`ThumbnailLoaderWorker`) działa poprawnie i rozważyć `QThreadPool` dla lepszego zarządzania.
    - Przenieść najbardziej krytyczne **operacje plikowe** (np. usuwanie, zmiana nazwy wielu plików, jeśli taka funkcjonalność istnieje lub jest planowana) do wątków.

2.  **Krok 2: Kluczowe Refaktoryzacje Strukturalne:**

    - **Priorytet:** Wysoki.
    - **Status:** ✅ **Zakończone**
    - **Cel:** Poprawa struktury kodu i usunięcie długu technicznego przed dalszymi optymalizacjami.
    - **Zadania:**
      - **Refaktoryzacja `FilePair` (SRP):** Przeniesienie logiki operacji plikowych (`rename`, `delete`, `move`) z modelu do modułu `file_operations`.
      - **Usunięcie Martwego Kodu:** Usunięcie przestarzałego pliku `src/ui/main_window_tree_ops.py`.

3.  **Krok 3: Optymalizacja Aktualizacji Galerii (bez zmiany na `QListView`):**

    - **Priorytet:** Wysoki.
    - Zaimplementować **debouncing/throttling** dla suwaka zmiany rozmiaru miniatur.
    - Zoptymalizować `_update_gallery_view` tak, aby przy filtrowaniu **jedynie ukrywała/pokazywała** istniejące widgety (`setVisible`), zamiast usuwać je z layoutu i dodawać na nowo.
    - Zoptymalizować sposób, w jaki widgety są dodawane/usuwane z `self.gallery_tile_widgets`.

4.  **Krok 4: Cache'owanie Miniatur na Dysku:**

    - **Priorytet:** Wysoki.
    - Implementacja mechanizmu zapisywania i odczytywania miniatur z dyskowego cache'u.

5.  **Krok 5: Refaktoryzacja `MainWindow` (początkowy etap):**

    - **Priorytet:** Średni.
    - Wydzielenie logiki zarządzania samą galerią (bezpośrednie manipulacje `tiles_layout` i `gallery_tile_widgets`) do osobnej klasy pomocniczej.

6.  **Krok 6: Zaawansowana Optymalizacja Galerii (Wirtualizacja):**

    - **Priorytet:** Średni (ale kluczowy dla długoterminowej skalowalności).
    - Rozważenie i potencjalna implementacja galerii opartej na **`QListView`/`QTableView` z modelem i delegatem**. To największa zmiana, ale zapewni najlepszą wydajność dla bardzo dużych zbiorów.

7.  **Krok 7: Pełna Asynchroniczność Operacji Plikowych i Metadanych:**

    - **Priorytet:** Średni.
    - Przeniesienie wszystkich pozostałych operacji plikowych i operacji na metadanych do wątków.
    - Implementacja wsadowego/asynchronicznego zapisu metadanych.

8.  **Krok 8: Dalsza Refaktoryzacja i Profilowanie:**
    - **Priorytet:** Ciągły.
    - Stopniowa refaktoryzacja pozostałych części `MainWindow`.
    - Regularne profilowanie aplikacji (np. przy użyciu `cProfile` lub specjalistycznych narzędzi Qt) w celu identyfikacji nowych wąskich gardeł.

## 5. Podsumowanie

Problemy z wydajnością w aplikacji CFAB_3DHUB, szczególnie w kontekście galerii, są znaczące, ale możliwe do zaadresowania poprzez kombinację wielowątkowości, optymalizacji algorytmów zarządzania UI, cache'owania oraz refaktoryzacji kodu. Kluczowe jest odciążenie głównego wątku UI od długotrwałych operacji oraz zaimplementowanie bardziej efektywnych strategii renderowania i aktualizacji dużej liczby elementów graficznych. Rozpoczęcie od najbardziej krytycznych obszarów, takich jak asynchroniczne ładowanie danych i optymalizacja aktualizacji galerii, powinno przynieść szybką poprawę responsywności aplikacji.
