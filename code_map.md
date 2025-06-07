\_CFAB_3DHUB/
├── run_app.py 🟡 ŚREDNI PRIORYTET - Główny skrypt uruchomieniowy aplikacji. Wymaga analizy pod kątem inicjalizacji i zależności.
│ - **Funkcjonalność:** Uruchamia aplikację Qt.
│ - **Wydajność:** Niska bezpośrednia, ale inicjuje kluczowe komponenty.
│ - **Stan obecny:** Wymaga weryfikacji poprawnej inicjalizacji i obsługi wyjątków na starcie.
│ - **Zależności:** `src/main.py`, `src/app_config.py`, `styles.qss`.
│ - **Priorytet poprawek:** Średni.
├── styles.qss 🟢 NISKI PRIORYTET - Arkusz stylów Qt. Wymaga sprawdzenia poprawności składni i ewentualnej optymalizacji oraz integracji z aplikacją.
│ - **Funkcjonalność:** Definiuje wygląd komponentów UI.
│ - **Wydajność:** Zazwyczaj niska, chyba że bardzo złożone selektory/reguły.
│ - **Stan obecny:** Do weryfikacji i zastosowania w `main_window.py` lub globalnie.
│ - **Zależności:** Wszystkie komponenty UI.
│ - **Priorytet poprawek:** Niski (ale ważny dla wyglądu).
├── src/
│ ├── **init**.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny pakietu src.
│ │ - **Funkcjonalność:** Oznacza folder jako pakiet Python.
│ │ - **Wydajność:** Brak wpływu.
│ │ - **Stan obecny:** Zazwyczaj OK.
│ │ - **Zależności:** -
│ │ - **Priorytet poprawek:** Niski.
│ ├── app_config.py 🟡 ŚREDNI PRIORYTET - Konfiguracja aplikacji.
│ │ - **Funkcjonalność:** Zarządza ustawieniami aplikacji (np. ścieżki, preferencje).
│ │ - **Wydajność:** Może wpływać, jeśli odczyt/zapis jest częsty lub nieefektywny.
│ │ - **Stan obecny:** Analiza sposobu ładowania, dostępu i zapisu konfiguracji. Potencjalna walidacja.
│ │ - **Zależności:** Wiele komponentów aplikacji.
│ │ - **Priorytet poprawek:** Średni.
│ ├── main.py 🔴 WYSOKI PRIORYTET - Główny plik aplikacji, prawdopodobnie zawiera logikę startową i główne okno.
│ │ - **Funkcjonalność:** Inicjalizacja aplikacji, tworzenie głównego okna, zarządzanie główną pętlą zdarzeń.
│ │ - **Wydajność:** Wysoki wpływ na start aplikacji i ogólną responsywność.
│ │ - **Stan obecny:** Kluczowy do analizy pod kątem struktury, inicjalizacji komponentów, obsługi sygnałów i slotów, integracji paska postępu.
│ │ - **Zależności:** `src/ui/main_window.py`, `src/logic/*`, `src/app_config.py`, `run_app.py`.
│ │ - **Priorytet poprawek:** Wysoki.
│ ├── logic/
│ │ ├── **init**.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny pakietu logic.
│ │ ├── file_operations.py 🔴 WYSOKI PRIORYTET - Operacje na plikach.
│ │ │ - **Funkcjonalność:** Kopiowanie, przenoszenie, usuwanie plików/folderów.
│ │ │ - **Wydajność:** Bardzo wysoki wpływ, zwłaszcza przy masowych operacjach. Potencjalne blokowanie UI.
│ │ │ - **Stan obecny:** Wymaga szczegółowej analizy pod kątem optymalizacji I/O, obsługi błędów, użycia wątków (`workers.py`) i raportowania postępu.
│ │ │ - **Zależności:** `src/ui/file_operations_ui.py`, `src/models/file_pair.py`, `src/ui/delegates/workers.py`.
│ │ │ - **Priorytet poprawek:** Wysoki.
│ │ ├── filter_logic.py 🟡 ŚREDNI PRIORYTET - Logika filtrowania.
│ │ │ - **Funkcjonalność:** Filtrowanie listy plików/elementów na podstawie kryteriów.
│ │ │ - **Wydajność:** Może być wąskim gardłem przy dużych zbiorach danych i złożonych filtrach.
│ │ │ - **Stan obecny:** Analiza algorytmów filtrowania, optymalizacja.
│ │ │ - **Zależności:** `src/ui/widgets/filter_panel.py`, modele danych.
│ │ │ - **Priorytet poprawek:** Średni.
│ │ ├── metadata_manager.py 🔴 WYSOKI PRIORYTET - Zarządzanie metadanymi.
│ │ │ - **Funkcjonalność:** Odczyt, zapis, edycja metadanych plików (np. EXIF, tagi).
│ │ │ - **Wydajność:** Wysoki wpływ, operacje na metadanych mogą być kosztowne. Potencjalne blokowanie UI.
│ │ │ - **Stan obecny:** Analiza sposobu przechowywania, odczytu i zapisu metadanych. Użycie wątków i raportowanie postępu.
│ │ │ - **Zależności:** `src/models/*`, `src/ui/widgets/metadata_controls_widget.py`, `src/ui/delegates/workers.py`.
│ │ │ - **Priorytet poprawek:** Wysoki.
│ │ └── scanner.py 🔴 WYSOKI PRIORYTET - Skanowanie plików/folderów.
│ │ - **Funkcjonalność:** Przeszukiwanie systemu plików w poszukiwaniu określonych typów plików, budowanie listy plików.
│ │ - **Wydajność:** Bardzo wysoki wpływ, szczególnie na starcie i przy odświeżaniu. Kluczowe dla paska postępu.
│ │ - **Stan obecny:** Analiza efektywności skanowania, rekursji, filtrowania podczas skanowania. Użycie wątków (`workers.py`) i raportowanie postępu.
│ │ - **Zależności:** `src/logic/file_operations.py` (pośrednio), `src/models/file_pair.py`, `src/ui/delegates/workers.py`.
│ │ - **Priorytet poprawek:** Wysoki.
│ ├── models/
│ │ ├── **init**.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny pakietu models.
│ │ └── file_pair.py 🟡 ŚREDNI PRIORYTET - Model danych dla par plików lub pojedynczych plików z metadanymi.
│ │ - **Funkcjonalność:** Reprezentacja struktury danych pliku, jego ścieżki, metadanych itp.
│ │ - **Wydajność:** Niska bezpośrednia, ale wpływa na sposób przetwarzania danych w logice i UI.
│ │ - **Stan obecny:** Analiza struktury danych, kompletności, metod dostępowych.
│ │ - **Zależności:** Wiele komponentów logicznych i UI.
│ │ - **Priorytet poprawek:** Średni.
│ ├── ui/
│ │ ├── **init**.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny pakietu ui.
│ │ ├── directory_tree_manager.py 🟡 ŚREDNI PRIORYTET - Zarządzanie drzewem katalogów w UI.
│ │ │ - **Funkcjonalność:** Wyświetlanie i nawigacja po strukturze folderów.
│ │ │ - **Wydajność:** Może wpływać na responsywność UI przy bardzo dużych strukturach katalogów.
│ │ │ - **Stan obecny:** Analiza sposobu ładowania danych (potencjalnie leniwe ładowanie), aktualizacji i renderowania drzewa.
│ │ │ - **Zależności:** `src/logic/scanner.py` (pośrednio do pobierania danych).
│ │ │ - **Priorytet poprawek:** Średni.
│ │ ├── file_operations_ui.py 🟡 ŚREDNI PRIORYTET - Interfejs użytkownika dla operacji na plikach.
│ │ │ - **Funkcjonalność:** Przyciski, dialogi związane z kopiowaniem, przenoszeniem, usuwaniem plików.
│ │ │ - **Wydajność:** Zależna od logiki w `logic/file_operations.py`. Ważne raportowanie postępu.
│ │ │ - **Stan obecny:** Analiza interakcji z użytkownikiem, wywoływania operacji w tle, aktualizacji UI po operacjach.
│ │ │ - **Zależności:** `src/logic/file_operations.py`, `src/ui/main_window.py`.
│ │ │ - **Priorytet poprawek:** Średni.
│ │ ├── gallery_manager.py 🔴 WYSOKI PRIORYTET - Zarządzanie galerią w UI.
│ │ │ - **Funkcjonalność:** Wyświetlanie siatki/listy plików (miniaturek), obsługa zaznaczenia, sortowania.
│ │ │ - **Wydajność:** Wysoki wpływ, renderowanie wielu elementów, ładowanie miniaturek, paginacja/wirtualizacja.
│ │ │ - **Stan obecny:** Kluczowy do analizy pod kątem wydajności renderowania, efektywnego ładowania danych i miniaturek (z `thumbnail_cache.py`), obsługi dużych ilości plików.
│ │ │ - **Zależności:** `src/ui/widgets/file_tile_widget.py`, `src/ui/widgets/thumbnail_cache.py`, `src/logic/*`, `src/models/file_pair.py`.
│ │ │ - **Priorytet poprawek:** Wysoki.
│ │ ├── main_window.py 🔴 WYSOKI PRIORYTET - Główne okno aplikacji.
│ │ │ - **Funkcjonalność:** Główny kontener dla wszystkich elementów UI, menu, paski narzędzi, pasek stanu (dla postępu).
│ │ │ - **Wydajność:** Wysoki wpływ, agreguje wiele komponentów, zarządza layoutem.
│ │ │ - **Stan obecny:** Analiza struktury, layoutu, integracji komponentów, implementacji globalnego paska postępu, zastosowania stylów z `styles.qss`.
│ │ │ - **Zależności:** `src/main.py`, wszystkie główne komponenty UI (`gallery_manager.py`, `directory_tree_manager.py`, etc.) i logiki (pośrednio).
│ │ │ - **Priorytet poprawek:** Wysoki.
│ │ ├── delegates/
│ │ │ ├── **init**.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny pakietu delegates.
│ │ │ └── workers.py 🔴 WYSOKI PRIORYTET - Wątki robocze dla operacji w tle.
│ │ │ - **Funkcjonalność:** Wykonywanie długotrwałych zadań (skanowanie, I/O, przetwarzanie) bez blokowania głównego wątku UI.
│ │ │ - **Wydajność:** Kluczowy dla responsywności UI i ogólnej wydajności aplikacji.
│ │ │ - **Stan obecny:** Analiza implementacji QThread/QRunnable, komunikacji z głównym wątkiem (sygnały/sloty) do aktualizacji UI (w tym paska postępu), obsługi błędów w wątkach.
│ │ │ - **Zależności:** `src/logic/scanner.py`, `src/logic/file_operations.py`, `src/logic/metadata_manager.py`, `src/utils/image_utils.py` (dla generowania miniaturek w tle).
│ │ │ - **Priorytet poprawek:** Wysoki.
│ │ ├── widgets/
│ │ │ ├── **init**.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny pakietu widgets.
│ │ │ ├── file_tile_widget.py 🟡 ŚREDNI PRIORYTET - Widget kafelka pliku w galerii.
│ │ │ │ - **Funkcjonalność:** Reprezentuje pojedynczy plik w galerii (miniaturka, nazwa, metadane).
│ │ │ │ - **Wydajność:** Wpływa na ogólną wydajność galerii, zwłaszcza przy dużej liczbie kafelków. Optymalizacja rysowania.
│ │ │ │ - **Stan obecny:** Analiza renderowania, efektywności, obsługi zdarzeń (np. kliknięcie).
│ │ │ │ - **Zależności:** `src/ui/gallery_manager.py`, `src/models/file_pair.py`, `src/ui/widgets/tile_styles.py`.
│ │ │ │ - **Priorytet poprawek:** Średni.
│ │ │ ├── filter_panel.py 🟡 ŚREDNI PRIORYTET - Panel filtrowania w UI.
│ │ │ │ - **Funkcjonalność:** Elementy UI do definiowania kryteriów filtrowania.
│ │ │ │ - **Wydajność:** Zależna od `logic/filter_logic.py` i częstotliwości aktualizacji.
│ │ │ │ - **Stan obecny:** Analiza interakcji, przekazywania kryteriów do logiki filtrowania.
│ │ │ │ - **Zależności:** `src/logic/filter_logic.py`, `src/ui/main_window.py`.
│ │ │ │ - **Priorytet poprawek:** Średni.
│ │ │ ├── metadata_controls_widget.py 🟡 ŚREDNI PRIORYTET - Widget kontrolek metadanych.
│ │ │ │ - **Funkcjonalność:** Pola edycyjne i przyciski do zarządzania metadanymi wybranego pliku/plików.
│ │ │ │ - **Wydajność:** Zależna od `logic/metadata_manager.py`.
│ │ │ │ - **Stan obecny:** Analiza interakcji, walidacji wprowadzanych danych, komunikacji z logiką.
│ │ │ │ - **Zależności:** `src/logic/metadata_manager.py`, `src/ui/main_window.py`.
│ │ │ │ - **Priorytet poprawek:** Średni.
│ │ │ ├── preview_dialog.py 🟡 ŚREDNI PRIORYTET - Dialog podglądu pliku.
│ │ │ │ - **Funkcjonalność:** Wyświetla większy podgląd obrazu lub zawartość innego pliku.
│ │ │ │ - **Wydajność:** Może wpływać, jeśli ładowanie podglądu jest wolne lub zasobożerne.
│ │ │ │ - **Stan obecny:** Analiza ładowania treści, potencjalne użycie `image_utils.py` lub innych narzędzi.
│ │ │ │ - **Zależności:** `src/utils/image_utils.py`, `src/models/file_pair.py`.
│ │ │ │ - **Priorytet poprawek:** Średni.
│ │ │ ├── thumbnail_cache.py 🔴 WYSOKI PRIORYTET - Cache miniaturek.
│ │ │ │ - **Funkcjonalność:** Przechowuje wygenerowane miniaturki, aby uniknąć ich ponownego tworzenia.
│ │ │ │ - **Wydajność:** Krytyczny dla szybkiego wyświetlania galerii i responsywności UI.
│ │ │ │ - **Stan obecny:** Analiza strategii cache'owania (pamięć vs dysk), rozmiaru cache, mechanizmów czyszczenia, efektywności dostępu. Potencjalna integracja z `workers.py` do generowania w tle.
│ │ │ │ - **Zależności:** `src/ui/gallery_manager.py`, `src/utils/image_utils.py`, `src/ui/delegates/workers.py`.
│ │ │ │ - **Priorytet poprawek:** Wysoki.
│ │ │ └── tile_styles.py 🟢 NISKI PRIORYTET - Style dla kafelków.
│ │ │ - **Funkcjonalność:** Definiuje wygląd kafelków (np. ramki, tło, czcionki).
│ │ │ - **Wydajność:** Niska.
│ │ │ - **Stan obecny:** Do weryfikacji i ewentualnej integracji z `file_tile_widget.py`.
│ │ │ - **Zależności:** `src/ui/widgets/file_tile_widget.py`.
│ │ │ - **Priorytet poprawek:** Niski.
│ └── utils/
│ ├── **init**.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny pakietu utils.
│ ├── image_utils.py 🟡 ŚREDNI PRIORYTET - Narzędzia do obsługi obrazów.
│ │ - **Funkcjonalność:** Tworzenie miniaturek, odczyt właściwości obrazu, konwersje formatów.
│ │ - **Wydajność:** Może być wąskim gardłem, zwłaszcza przy przetwarzaniu dużych obrazów lub wielu plików. Potencjalne użycie `workers.py`.
│ │ - **Stan obecny:** Analiza używanych bibliotek (np. Pillow), optymalizacja algorytmów, obsługa błędów.
│ │ - **Zależności:** `src/ui/widgets/thumbnail_cache.py`, `src/ui/widgets/preview_dialog.py`, `src/ui/delegates/workers.py`.
│ │ - **Priorytet poprawek:** Średni.
│ ├── logging_config.py 🟢 NISKI PRIORYTET - Konfiguracja logowania.
│ │ - **Funkcjonalność:** Ustawienia dla systemu logowania aplikacji.
│ │ - **Wydajność:** Niska, chyba że logowanie jest bardzo intensywne i nieefektywne.
│ │ - **Stan obecny:** Weryfikacja konfiguracji, poziomów logowania, formatu.
│ │ - **Zależności:** Wiele komponentów (do importu i użycia loggera).
│ │ - **Priorytet poprawek:** Niski.
│ └── path_utils.py 🟢 NISKI PRIORYTET - Narzędzia do operacji na ścieżkach.
│ - **Funkcjonalność:** Normalizacja ścieżek, łączenie, sprawdzanie istnienia itp.
│ - **Wydajność:** Zazwyczaj niska.
│ - **Stan obecny:** Weryfikacja poprawności i kompletności funkcji.
│ - **Zależności:** Wiele komponentów operujących na ścieżkach plików.
│ - **Priorytet poprawek:** Niski.

---

## 🔄 ETAP 1: WSTĘPNA ANALIZA I MAPOWANIE PROJEKTU - ZAKOŃCZONY

### Plan etapu 2:

- **Kolejność analizy (zgodnie z priorytetami):**
  1.  🔴 **WYSOKI PRIORYTET:**
      - `src/logic/scanner.py`
      - `src/logic/file_operations.py`
      - `src/logic/metadata_manager.py`
      - `src/ui/widgets/thumbnail_cache.py`
      - `src/ui/delegates/workers.py` (kluczowy dla paska postępu)
      - `src/ui/gallery_manager.py`
      - `src/ui/main_window.py` (integracja paska postępu, style)
      - `src/main.py`
  2.  🟡 **ŚREDNI PRIORYTET:**
      - `run_app.py`
      - `src/app_config.py`
      - `src/logic/filter_logic.py`
      - `src/models/file_pair.py`
      - `src/ui/directory_tree_manager.py`
      - `src/ui/file_operations_ui.py`
      - `src/ui/widgets/file_tile_widget.py`
      - `src/ui/widgets/filter_panel.py`
      - `src/ui/widgets/metadata_controls_widget.py`
      - `src/ui/widgets/preview_dialog.py`
      - `src/utils/image_utils.py`
  3.  🟢 **NISKI PRIORYTET:**
      - `styles.qss` (zastosowanie do UI)
      - Pozostałe pliki `__init__.py`
      - `src/utils/logging_config.py`
      - `src/utils/path_utils.py`
      - `src/ui/widgets/tile_styles.py`
- **Grupowanie plików (przykładowe, może być dostosowane):**
  - Grupa 1 (Rdzeń logiki i danych): `scanner.py`, `file_operations.py`, `metadata_manager.py`, `file_pair.py`
  - Grupa 2 (UI - Galeria i Miniaturki): `gallery_manager.py`, `thumbnail_cache.py`, `file_tile_widget.py`, `image_utils.py`
  - Grupa 3 (UI - Główne Okno i Wątki): `main_window.py`, `workers.py`, `main.py`, `run_app.py` (integracja paska postępu, style)
  - Grupa 4 (UI - Pozostałe komponenty): `directory_tree_manager.py`, `file_operations_ui.py`, `filter_panel.py`, `metadata_controls_widget.py`, `preview_dialog.py`
  - Grupa 5 (Konfiguracja i Style): `app_config.py`, `styles.qss`
  - Grupa 6 (Narzędzia i inicjalizatory): `logging_config.py`, `path_utils.py`, `__init__.py`
- **Szacowany zakres zmian:**
  - **Wydajność:** Optymalizacja algorytmów, operacji I/O, intensywne wykorzystanie `src/ui/delegates/workers.py` dla długotrwałych operacji (skanowanie, ładowanie danych, operacje na plikach, generowanie miniaturek).
  - **Stabilność:** Lepsza obsługa błędów, walidacja danych, testy jednostkowe (poza zakresem tego audytu, ale jako rekomendacja).
  - **UI:** Implementacja paska postępu w `src/ui/main_window.py` i jego aktualizacja z `src/ui/delegates/workers.py` lub innych odpowiednich miejsc. Zastosowanie stylów z `styles.qss` do `src/ui/main_window.py` i jego komponentów.
  - **Refaktoryzacja:** Poprawa czytelności, usunięcie duplikacji, lepsze zarządzanie zależnościami, spójność nazewnictwa. Wprowadzenie typowania (type hints) dla lepszej analizy statycznej i czytelności.
