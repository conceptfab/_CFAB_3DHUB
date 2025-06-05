# Raport Wydajności Aplikacji

Data: 24.07.2024

## Problem

Interfejs użytkownika (UI) aplikacji staje się całkowicie nieresponsywny (ulega zamrożeniu) na czas ładowania galerii plików po wybraniu folderu roboczego. Czas blokady jest proporcjonalny do liczby plików w folderze i może trwać od kilku do kilkudziesięciu sekund, co drastycznie pogarsza użyteczność aplikacji.

## Diagnoza i Przyczyna

Problem został zlokalizowany w metodzie `_handle_scan_finished` w pliku `src/ui/main_window.py`.

Chociaż skanowanie folderu w poszukiwaniu plików odbywa się poprawnie w osobnym wątku (`ScanFolderWorker`), to przetwarzanie wyników — czyli tworzenie widżetów dla każdego znalezionego pliku — odbywa się już w **głównym wątku UI**.

**Kluczowy fragment kodu powodujący problem:**

_Lokalizacja: `src/ui/main_window.py`, metoda `_handle_scan_finished`_

```python
# ...
if self.all_file_pairs:
    for file_pair in self.all_file_pairs: # <--- PROBLEM: Pętla w głównym wątku UI
        try:
            # CIĘŻKA OPERACJA: Tworzenie widgetu, które prawdopodobnie
            # obejmuje odczyt pliku z dysku (miniaturka) i inne operacje.
            tile = FileTileWidget(file_pair, self.current_thumbnail_size, self)
            # ... reszta konfiguracji widgetu ...
            self.gallery_tile_widgets[file_pair.get_archive_path()] = tile
        except Exception as e:
            logging.error(f"Błąd tworzenia kafelka dla {file_pair.get_base_name()}: {e}")
# ...
```

Każde wywołanie `FileTileWidget(...)` wewnątrz tej pętli jest operacją blokującą. Jeśli w folderze jest 500 plików, konstruktor ten jest wywoływany 500 razy z rzędu w głównym wątku, uniemożliwiając mu obsługę jakichkolwiek innych zdarzeń (np. odświeżania okna, kliknięć myszą).

## Proponowane Rozwiązanie

Należy przenieść proces przygotowywania danych dla kafelków (zwłaszcza ładowanie miniaturek) do osobnego wątku roboczego. Tworzenie samych widżetów musi pozostać w głównym wątku, ale powinno być szybkie i oparte o już przygotowane dane.

### Krok 1: Stworzenie nowego workera `GalleryLoadWorker`

Należy utworzyć nową klasę dziedziczącą po `QObject`, która będzie odpowiedzialna za przygotowanie danych dla kafelków w tle.

- Worker ten powinien przyjmować listę `file_pairs`.
- W swojej metodzie `run()`, powinien iterować po tej liście.
- Dla każdego `file_pair` powinien wczytać z dysku miniaturkę i przygotować ją jako obiekt `QPixmap` lub `QImage`.
- Po przygotowaniu danych dla jednego kafelka, worker powinien wyemitować sygnał, np. `tileDataReady(file_pair, thumbnail_image)`.
- Na końcu pętli powinien wyemitować sygnał `finished()`.

### Krok 2: Modyfikacja `MainWindow`

1.  W `_handle_scan_finished`, zamiast pętli tworzącej `FileTileWidget`, należy stworzyć instancję nowego `GalleryLoadWorker`, przenieść go do nowego `QThread` i uruchomić.

2.  Należy utworzyć nowy slot w `MainWindow`, np. `_on_tile_data_ready(file_pair, thumbnail_image)`, który będzie połączony z sygnałem `tileDataReady` workera.

3.  Ten nowy slot będzie wykonywał lekkie operacje w głównym wątku UI:
    - Odbierze gotowe dane (`file_pair`, `thumbnail_image`).
    - Stworzy instancję `FileTileWidget`, przekazując mu już załadowaną miniaturkę.
    - Doda nowo utworzony kafelek do layoutu (lub do słownika `self.gallery_tile_widgets` w celu późniejszego wyświetlenia).

### Krok 3: Refaktoryzacja `FileTileWidget`

Konstruktor `FileTileWidget` musi zostać zmodyfikowany. Zamiast przyjmować `file_pair` i samemu ładować miniaturkę z dysku, powinien przyjmować `file_pair` oraz gotowy obiekt `QPixmap` lub `QImage` z miniaturką. Cała logika ładowania pliku z dysku musi zostać usunięta z konstruktora i przeniesiona do `GalleryLoadWorker`.

## Korzyści z proponowanego rozwiązania

- **Responsywność UI:** Interfejs pozostanie w pełni responsywny podczas ładowania galerii.
- **Lepsze wrażenia użytkownika (UX):** Użytkownik będzie widział, jak kafelki pojawiają się w galerii stopniowo (lub wszystkie naraz po krótkiej chwili), zamiast patrzeć na zamrożone okno.
- **Skalowalność:** Rozwiązanie będzie dobrze działać nawet dla folderów z tysiącami plików.
- **Wizualna informacja o postępie:** Możliwe staje się dodanie paska postępu, który będzie aktualizowany w miarę postępów `GalleryLoadWorker`.
