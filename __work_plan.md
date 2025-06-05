# Plan Implementacji Projektu "CFAB_3DHUB" - Aktualne Zadania

**Wersja Planu:** 2.0
**Data:** 2023-10-28
**Na podstawie:** Wnioski z analizy plików PRD Wersja 1.0, DATA.md Wersja 1.0, \_work_plan.md Wersja 1.0 (dla definicji pozostałych zadań), code_map.md, corrections.md, TODO.md

---

## 0. Wstęp i Cel Planu

Niniejszy dokument stanowi zaktualizowany i skondensowany plan implementacji **pozostałych zadań** dla aplikacji "CFAB_3DHUB". Koncentruje się na etapach, które nie zostały jeszcze zrealizowane lub wymagają znaczących poprawek. Jego celem jest kierowanie dalszym procesem rozwoju, etap po etapie, z wyraźnym zdefiniowaniem zadań, oczekiwanych rezultatów, plików do modyfikacji/utworzenia, zależności, wymagań testowych i dokumentacyjnych.

---

## Sugerowany Schemat Projektu (Struktura Docelowa)

CFAB_3DHUB/
├── .venv/
├── src/
│ ├── **init**.py
│ ├── main.py
│ ├── app_config.py
│ │
│ ├── models/
│ │ ├── **init**.py
│ │ └── file_pair.py
│ │
│ ├── logic/
│ │ ├── **init**.py
│ │ ├── scanner.py
│ │ ├── file_operations.py
│ │ ├── metadata_manager.py
│ │ └── filter_logic.py
│ │
│ ├── ui/
│ │ ├── **init**.py
│ │ ├── main_window.py
│ │ ├── widgets/
│ │ │ ├── **init**.py
│ │ │ ├── file_tile_widget.py
│ │ │ └── preview_dialog.py
│ │ └── delegates/ # Do weryfikacji użycia, potencjalnie do usunięcia
│ │ └── **init**.py
│ │
│ └── utils/
│ ├── **init**.py
│ ├── image_utils.py
│ └── logging_config.py
│
├── tests/
│ ├── **init**.py
│ ├── conftest.py
│ ├── unit/
│ │ ├── **init**.py
│ │ ├── test_file_pair.py
│ │ ├── test_scanner.py
│ │ ├── test_file_operations.py # Skonsolidowane
│ │ ├── test_metadata_manager.py
│ │ ├── test_image_utils.py
│ │ ├── test_filter_logic.py
│ │ ├── test_file_pair_operations.py # Do weryfikacji/konsolidacji z test_file_operations lub test_file_pair
│ │ ├── test_file_pair_favorite.py # Do weryfikacji/konsolidacji z test_file_pair
│ │ └── test_unicode_filenames.py
│ └── integration/
│ ├── **init**.py
│ └── test_main.py
│
├── .gitignore
├── README.md
└── requirements.txt

Etapy Implementacji (Pozostałe Zadania)
Etap 1: Logika Biznesowa - Obsługa Plików Niesparowanych, Ręczne Parowanie
Status: [ ] Do wykonania
Cel Etapu: Modyfikacja skanowania folderu w celu identyfikacji plików niesparowanych. Implementacja mechanizmu ręcznego parowania. Wstępna analiza wydajności.
Wymagane Funkcjonalności:
src/logic/scanner.py:
Modyfikacja scan_folder_for_pairs (lub nowa funkcja scan_folder_detailed):
Zwracanie dodatkowych list: unpaired_archives (ścieżki do niesparowanych archiwów) i unpaired_previews (ścieżki do niesparowanych podglądów).
Zastosowanie normalizacji wielkości liter w nazwach bazowych przy parowaniu (zgodnie z corrections.md Etap 2.12).
src/logic/metadata_manager.py:
Modyfikacja save_metadata() i load_metadata() do obsługi zapisu/odczytu list plików niesparowanych (jako ścieżki względne) w metadata.json (zgodnie z DATA.md i corrections.md Etap 2.14).
src/logic/file_operations.py:
Implementacja funkcji manually_pair_files(archive_path: str, preview_path: str, working_directory: str) -> FilePair | None:
Przyjmuje ścieżki, sprawdza różnice w nazwach bazowych.
Zmienia nazwę pliku podglądu, aby pasowała do nazwy archiwum (zachowując rozszerzenie).
Tworzy i zwraca nowy obiekt FilePair lub None w przypadku błędu.
Nowe/Modyfikowane Pliki:
src/logic/scanner.py
src/logic/metadata_manager.py
src/logic/file_operations.py
Zależności Koncepcyjne: Podstawowa logika skanowania i zarządzania metadanymi.
Wymagane Testy:
Jednostkowe (tests/unit/test_scanner.py): Sprawdzenie zwracania list plików niesparowanych.
Jednostkowe (tests/unit/test_metadata_manager.py): Test zapisu/odczytu list niesparowanych; aktualizacji po ręcznym sparowaniu.
Jednostkowe (tests/unit/test_file_operations.py): Test dla manually_pair_files (różne nazwy, zmiana nazwy, błędy).
Dokumentacja:
Aktualizacja docstringów i opisów dla zmodyfikowanych/nowych funkcji.
Notatki z analizy potencjalnych problemów wydajnościowych.
Etap 2: Interfejs Użytkownika - Wyświetlanie Niesparowanych, Ręczne Parowanie
Status: [ ] Do wykonania
Cel Etapu: Dodanie widoku/listy plików niesparowanych oraz interfejsu do ich ręcznego parowania.
Wymagane Funkcjonalności:
src/ui/main_window.py:
Dodanie panelu/zakładki "Niesparowane Pliki" z dwiema listami (QListWidget): unpaired_archives_list_widget i unpaired_previews_list_widget.
Zapełnianie list po zeskanowaniu folderu i załadowaniu metadanych.
Dodanie przycisku "Sparuj Wybrane" (QPushButton).
Logika przycisku "Sparuj Wybrane":
Weryfikacja zaznaczenia (1 archiwum, 1 podgląd).
Wywołanie logic.file_operations.manually_pair_files().
Po sukcesie: dodanie nowego FilePair do self.file_pairs, odświeżenie galerii, usunięcie plików z list niesparowanych w UI, aktualizacja metadanych (listy niesparowanych i nowa para) przez metadata_manager.save_metadata().
Wyświetlanie komunikatów (QMessageBox).
Czyszczenie i ponowne ładowanie list przy zmianie folderu roboczego.
Nowe/Modyfikowane Pliki:
src/ui/main_window.py
src/logic/metadata_manager.py (potencjalna modyfikacja sygnatury save_metadata do przyjmowania list niesparowanych).
Zależności Koncepcyjne: Etap 1 (Logika niesparowanych plików).
Wymagane Testy:
Manualne UI: Poprawność wyświetlania panelu, list, działania parowania, aktualizacji UI i metadata.json, obsługi błędów, zmiany folderu.
Dokumentacja:
Aktualizacja dokumentacji MainWindow i ewentualnie metadata_manager.py.
Etap 3: Refaktoryzacja, Implementacja Testów, Optymalizacja i Finalizacja
Status: [ ] Do wykonania
Cel Etapu: Poprawa jakości kodu, implementacja brakujących testów, optymalizacja wydajności, implementacja zadań z TODO.md, finalne testy i przygotowanie aplikacji.
Podetapy:
3.A: Refaktoryzacja Kodu i Poprawki Strukturalne
Zadania:
Implementacja wszystkich zaleceń dotyczących refaktoryzacji i poprawek strukturalnych z pliku corrections.md. Kluczowe obszary obejmują:
Modele (src/models/file_pair.py): Ekstrakcja operacji plikowych.
UI Widgets (src/ui/widgets/): Finalizacja D&D (FileTileWidget), centralizacja definicji kolorów, refaktoryzacja logiki rozmiaru (PreviewDialog).
Logika (src/logic/): Poprawki w scanner.py, file_operations.py, metadata_manager.py.
Utils (src/utils/image_utils.py): Ulepszenia funkcji obrazów.
Konfiguracja (src/app_config.py): Centralizacja konfiguracji (np. kolorów).
Struktura UI: Usunięcie przestarzałych plików (main_window_tree_ops.py, folder_tree_click_handler.py).
Testy (tests/conftest.py): Porządki.
Przegląd kodu pod kątem PEP 8, DRY, SRP. Użycie flake8/pylint.
3.B: Implementacja i Uzupełnienie Testów Jednostkowych i Integracyjnych
Zadania:
Stworzenie brakujących testów jednostkowych zgodnie z corrections.md i code_map.md:
tests/unit/test_scanner.py
tests/unit/test_filter_logic.py
Konsolidacja i uzupełnienie:
tests/unit/test_file_operations.py (wchłonięcie test_folder_operations.py).
tests/unit/test_file_pair.py (testy metadanych, operacji jeśli zostaną tu częściowo).
tests/unit/test_image_utils.py.
Stworzenie rzeczywistych testów integracyjnych w tests/integration/test_main.py.
Dążenie do wysokiego pokrycia kodu.
3.C: Optymalizacja Wydajności
Zadania:
Implementacja asynchronicznego ładowania miniatur (np. QThreadPool).
Implementacja cache'owania miniaturek na dysku (.app_metadata/thumbnails/).
Rozważenie optymalizacji skanowania dużych folderów.
Warunkowo: Przejście na SQLite dla metadanych, jeśli metadata.json okaże się wąskim gardłem (zgodnie z DATA.md). Wymagałoby to stworzenia nowej wersji MetadataManager i skryptu migracji.
Profilowanie aplikacji w celu identyfikacji wąskich gardeł.
Lepsze zarządzanie pamięcią dla miniatur (z TODO.md).
3.D: Implementacja Zadań z TODO.md
Kluczowe Funkcjonalności:
Wyszukiwanie pełnotekstowe w nazwach plików.
Sortowanie kafelków.
Grupowe operacje na plikach (wymaga modyfikacji UI do wielokrotnego zaznaczania).
Ulepszenia UI/UX:
Wyświetlanie długich nazw plików na kafelkach (elide).
Wskaźnik postępu dla długotrwałych operacji (QProgressDialog).
Konfigurowalny rozmiar czcionki na kafelkach.
Przycisk "Odśwież".
Zapamiętywanie ostatnio otwartego folderu (QSettings).
Przegląd i ewentualna poprawa ikon.
Ulepszenia Logiki/Konfiguracji:
Konfigurowalna ścieżka do .app_metadata (QSettings).
Definiowanie przez użytkownika własnych rozszerzeń (QSettings).
Potencjalne Przyszłe Funkcjonalności:
Internacjonalizacja (i18n) - wstępne przygotowanie.
3.E: Finalne Testowanie Systemowe
Zadania:
Przeprowadzenie kompleksowych testów regresji (manualnych i automatycznych).
Testy wydajnościowe na dużych zbiorach danych.
Testy użyteczności.
3.F: Finalizacja Dokumentacji i Zależności Projektu
Zadania:
Aktualizacja wszystkich komentarzy w kodzie i docstringów.
Finalizacja README.md (instrukcje, opis funkcji, znane problemy).
Aktualizacja requirements.txt o konkretne, przetestowane wersje bibliotek (zgodnie z corrections.md Etap 2.1), np.:
PyQt6==6.7.0
Pillow==10.3.0
patool==1.12

# Dla deweloperów (można rozważyć osobny requirements-dev.txt):

# pytest

# pytest-cov

# flake8

# pylint

Use code with caution.
Weryfikacja i aktualizacja skryptów pomocniczych (np. run_tests.bat zgodnie z corrections.md Etap 2.7).
Ostateczna weryfikacja, czy biblioteka patool jest faktycznie używana, i ewentualne usunięcie jej z requirements.txt, jeśli nie.
Nowe/Modyfikowane Pliki: Potencjalnie wszystkie pliki w src/ i tests/. Nowy skrypt migracji danych (jeśli SQLite). Zaktualizowane requirements.txt, skrypty .bat, README.md.
Zależności Koncepcyjne: Wszystkie poprzednie etapy i ukończone zadania.
Wymagane Testy: Zdefiniowane w podetapach 3.B i 3.E.
Dokumentacja: Kompleksowa aktualizacja dokumentacji projektu.
PROSZĘ O POTWIERDZENIE PRZED ROZPOCZĘCIEM IMPLEMENTACJI POWYŻSZYCH ETAPÓW.
