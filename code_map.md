\_CFAB_3DHUB/
├── **work_plan.md ⚪ PLIK DOKUMENTACYJNY - Poza zakresem analizy kodu
├── TODO.md ⚪ PLIK DOKUMENTACYJNY - Poza zakresem analizy kodu
├── \_audyt.md ⚪ PLIK PROCESOWY/WYTYCZNE - Poza zakresem analizy kodu
├── run_operation_tests.py 🟢 NISKI PRIORYTET - Skrypt uruchamiający wybrane testy jednostkowe (operacje na plikach/folderach, nazwy Unicode) za pomocą pytest. Zależny od pytest i plików testowych w tests/unit/.
├── run_tests_with_unicode.bat 🟢 NISKI PRIORYTET - Skrypt .bat dla Windows, ustawia kodowanie konsoli na UTF-8 i uruchamia run_operation_tests.py. Przydatny do testów z nazwami plików Unicode. Zależny od run_operation_tests.py i środowiska Python.
├── run_tests_operations.bat 🟢 NISKI PRIORYTET - Skrypt .bat dla Windows, uruchamia testy operacji na plikach i folderach (pytest), zapisując wyniki do test_results_operations.txt. Zależny od pytest i konkretnych plików testowych w tests/unit/.
├── run_tests.bat 🟡 ŚREDNI PRIORYTET - Skrypt .bat dla Windows, uruchamia testy jednostkowe oraz testy z raportem pokrycia kodu dla katalogu src/. Zależny od pytest, pytest-cov i struktury projektu. Zawiera nieaktualny komentarz.
├── requirements.txt 🔴 WYSOKI PRIORYTET - Definiuje zależności projektu (PyQt6, Pillow, patool). Kluczowy problem: brak wersjonowania zależności, co zagraża stabilności i odtwarzalności środowiska.
├── run_app.py 🟢 NISKI PRIORYTET - Główny skrypt uruchomieniowy aplikacji. Modyfikuje sys.path w celu poprawnego importu modułów z src/ i wywołuje funkcję main() z src.main. Zależny od src.main.
├── pytest.ini 🟢 NISKI PRIORYTET - Plik konfiguracyjny dla pytest. Definiuje ścieżki testów (tests/) oraz markery 'unit' i 'integration'. Dobra konfiguracja podstawowa.
├── \_auto_correct.md ⚪ PLIK PROCESOWY/WYTYCZNE - Poza zakresem analizy kodu
├── PRD.md ⚪ PLIK DOKUMENTACYJNY - Poza zakresem analizy kodu
├── README.md ⚪ PLIK DOKUMENTACYJNY - Poza zakresem analizy kodu
├── **clean_code.md ⚪ PLIK DOKUMENTACYJNY - Poza zakresem analizy kodu
├── .gitignore 🟢 NISKI PRIORYTET - Definiuje pliki i katalogi ignorowane przez Git. Kompleksowy, zawiera standardowe wzorce dla Pythona, IDE, OS oraz sekcję na reguły specyficzne dla projektu.
├── DATA.md ⚪ PLIK DOKUMENTACYJNY - Poza zakresem analizy kodu
├── src/
│ ├── main.py 🟢 NISKI PRIORYTET - Główny moduł aplikacji. Inicjalizuje logowanie, QApplication i MainWindow. Zawiera ostrzeżenie o poprawnym sposobie uruchamiania. Zależny od PyQt6, src.ui.main_window, src.utils.logging_config.
│ ├── app_config.py 🟢 NISKI PRIORYTET - Przechowuje konfigurację aplikacji (listy obsługiwanych rozszerzeń plików archiwów i podglądów). Sugerowana drobna refaktoryzacja inicjalizacji listy SUPPORTED_PREVIEW_EXTENSIONS dla czytelności.
│ ├── **init**.py 🟢 NISKI PRIORYTET - Pusty plik **init**.py, oznaczający katalog src jako pakiet Pythona. Standardowe i akceptowalne.
│ ├── ui/
│ │ ├── main_window.py 🔴 WYSOKI PRIORYTET - Główny komponent UI aplikacji (klasa MainWindow). Odpowiada za wyświetlanie drzewa katalogów, galerii kafelków plików, filtrowanie, obsługę miniatur i interakcje użytkownika. Ze względu na rozmiar i złożoność, wymaga szczegółowej analizy pod kątem wydajności, zarządzania pamięcią i czytelności. Zależny od PyQt6, logiki aplikacji (src.logic) i widgetów (src.ui.widgets).
│ │ ├── folder_tree_click_handler.py 🟡 ŚREDNI PRIORYTET - Zawiera funkcję obsługującą kliknięcie folderu w drzewie katalogów (w MainWindow). Skanuje folder, stosuje metadane, aktualizuje widok. Kwestia do rozważenia: umiejscowienie tej funkcji (czy nie powinna być metodą MainWindow) oraz obsługa potencjalnie długotrwałych operacji (np. w tle). Zależny od src.logic (scanner, metadata_manager) i MainWindow.
│ │ ├── main_window_tree_ops.py 🔴 WYSOKI PRIORYTET - Zawiera funkcje obsługujące operacje na drzewie katalogów (inicjalizacja, menu kontekstowe, tworzenie/zmiana nazwy/usuwanie folderów) oraz prawdopodobnie menu kontekstowe dla plików. KRYTYCZNY PROBLEM: Zawiera zduplikowaną funkcję folder_tree_item_clicked z pliku folder_tree_click_handler.py. Należy rozwiązać duplikację. Kwestie wydajnościowe (odświeżanie modelu, ponowne skanowanie) i architektura (funkcje jako metody vs. w osobnym module) do przeglądu. Zależny od PyQt6, src.logic (file_operations, metadata_manager) i MainWindow.
│ │ ├── integration_guide.txt ⚪ PLIK DOKUMENTACYJNY - Poza zakresem analizy kodu
│ │ ├── **init**.py 🟢 NISKI PRIORYTET - Pusty plik **init**.py, oznaczający katalog src/ui jako subpakiet Pythona. Standardowe i akceptowalne.
│ │ ├── widgets/
│ │ │ ├── file_tile_widget.py 🟡 ŚREDNI PRIORYTET - Widget (kafelek) wyświetlający informacje o parze plików (miniatura, nazwa, rozmiar, gwiazdki, ulubione, tag koloru). Emituje sygnały do obsługi interakcji. Ważny dla UI. Do analizy: wydajność ładowania/skalowania miniatur, obsługa zdarzeń, zarządzanie pamięcią. Zależny od PyQt6 i src.models.file_pair.
│ │ │ ├── preview_dialog.py 🟡 ŚREDNI PRIORYTET - Dialog wyświetlający podgląd obrazu (QPixmap). Automatycznie dostosowuje rozmiar do obrazu i ekranu. Główny problem: skomplikowana i powtarzalna logika obliczania początkowego rozmiaru w konstruktorze wymaga refaktoryzacji. Zależny od PyQt6.
│ │ │ └── **init**.py 🟢 NISKI PRIORYTET - Inicjalizuje pakiet widgets. Eksportuje FileTileWidget przez **all**. Do rozważenia: czy PreviewDialog również powinien być w **all**.
│ │ └── delegates/
│ │ └── **init**.py 🟢 NISKI PRIORYTET - Pusty plik **init**.py, oznaczający katalog src/ui/delegates jako subpakiet Pythona. Standardowe i akceptowalne.
│ ├── utils/
│ │ ├── logging_config.py 🟢 NISKI PRIORYTET - Konfiguruje system logowania aplikacji (poziom, konsola, plik z rotacją). Dobrze zorganizowany i elastyczny. Zależny od logging, os.
│ │ ├── image_utils.py 🟡 ŚREDNI PRIORYTET - Zawiera funkcje pomocnicze do tworzenia placeholderów QPixmap (create_placeholder_pixmap) i konwersji obrazów PIL na QPixmap (pillow_image_to_qpixmap). Sugestie: poprawa centrowania tekstu w placeholderze, przegląd formatu pośredniego (JPEG) przy konwersji PIL->QPixmap. Zależny od PIL, PyQt6.
│ │ └── **init**.py 🟢 NISKI PRIORYTET - Pusty plik **init**.py, oznaczający katalog src/utils jako subpakiet Pythona. Standardowe i akceptowalne.
│ ├── models/
│ │ ├── file_pair.py 🔴 WYSOKI PRIORYTET - Definiuje klasę FilePair, kluczowy model danych reprezentujący parę plików (archiwum, podgląd) wraz z metadanymi (ulubione, gwiazdki, kolor). Odpowiada za ładowanie miniatur, pobieranie rozmiaru i zarządzanie metadanymi. Prawdopodobnie wykonuje też operacje na plikach (zmiana nazwy, usuwanie, przenoszenie) - do szczegółowej weryfikacji. Zależny od PIL, PyQt6, src.utils.image_utils, os, logging.
│ │ └── **init**.py 🟢 NISKI PRIORYTET - Pusty plik **init**.py, oznaczający katalog src/models jako subpakiet. Do rozważenia: wyeksportowanie klasy FilePair dla ułatwienia importu.
│ └── logic/
│ ├── scanner.py 🟡 ŚREDNI PRIORYTET - Odpowiada za rekursywne skanowanie folderów w poszukiwaniu par plików (archiwum + podgląd) na podstawie ich nazw i rozszerzeń. Logika parowania i obsługi duplikatów (pierwszy znaleziony) do ewentualnego przeglądu pod kątem specyficznych wymagań. Zależny od src.app_config, src.models.file_pair, os, logging.
│ ├── file_operations.py 🟡 ŚREDNI PRIORYTET - Zestaw funkcji do operacji na plikach/folderach (otwieranie zewnętrzne, tworzenie, zmiana nazwy, usuwanie). Solidna implementacja z podstawową walidacją i obsługą błędów. Nieużywany import 'platform'. Zależny od PyQt6, os, shutil, logging.
│ ├── metadata_manager.py 🟡 ŚREDNI PRIORYTET - Zarządza metadanymi (ulubione, gwiazdki, kolory) dla par plików, przechowując je w pliku JSON w folderze .app_metadata. Solidna implementacja z bezpiecznym zapisem. Nieużywana funkcja get_absolute_path. Zależny od json, os, shutil, logging i modelu FilePair.
│ ├── filter_logic.py 🟡 ŚREDNI PRIORYTET - Implementuje logikę filtrowania listy obiektów FilePair na podstawie kryteriów (ulubione, gwiazdki, tag koloru). Solidna implementacja z bardzo szczegółowym logowaniem DEBUG. Zależny od src.models.file_pair, logging.
│ └── **init**.py 🟢 NISKI PRIORYTET - Inicjalizuje pakiet logic. Eksportuje funkcje scan_folder_for_pairs i filter_file_pairs przez **all**. Do rozważenia: czy inne komponenty z src.logic powinny być również eksportowane.
└── tests/
├── conftest.py 🟢 NISKI PRIORYTET - Definiuje współdzielone fixture'y Pytest. Zawiera przykładową fixture 'sample_fixture'. Do weryfikacji, czy fixture jest używana. Zależny od pytest.
├── **init**.py 🟢 NISKI PRIORYTET - Pusty plik **init**.py, oznaczający katalog tests jako pakiet Pythona. Standardowe i niezbędne dla poprawnego działania Pytest.
├── unit/
│ ├── test_unicode_filenames.py 🟢 NISKI PRIORYTET - Testy jednostkowe dla obsługi nazw plików i folderów z znakami Unicode (np. Cyrylica) w operacjach na FilePair, folderach i skanerze. Dobrze zorganizowane. Zależne od pytest, PIL, logiki aplikacji i modeli.
│ ├── test_file_pair.py 🟡 ŚREDNI PRIORYTET - Testy jednostkowe dla klasy FilePair. Pokrywają podstawową inicjalizację, rozmiar, ładowanie miniatur (z mockowaniem konwersji do QPixmap). Brakuje testów dla metadanych (ulubione, gwiazdki, kolory) i potencjalnych operacji na plikach. Zależne od pytest, PIL, unittest.mock.
│ ├── test_folder_operations.py 🟢 NISKI PRIORYTET - Testy jednostkowe dla funkcji create_folder, rename_folder, delete_folder z src.logic.file_operations. Kompleksowe, pokrywają różne scenariusze pomyślne i błędne, w tym walidację nazw i błędy uprawnień (mockowane). Zależne od pytest, unittest.mock.
│ ├── test_file_pair_operations.py 🟢 NISKI PRIORYTET - Testy jednostkowe dla metod rename, delete, move w klasie FilePair. Dobrze zorganizowane, pokrywają scenariusze pomyślne i błędne (konflikty, nieistniejące ścieżki). Zależne od pytest, PIL.
│ ├── test_image_utils.py 🟡 ŚREDNI PRIORYTET - Testy jednostkowe dla create_placeholder_pixmap i pillow_image_to_qpixmap. Pokrywają podstawowe scenariusze. Brakuje testów dla różnych trybów obrazów, renderowania tekstu/koloru w placeholderze oraz obsługi błędów. Zbędne użycie tempfile w jednym teście. Zależne od pytest, PIL, PyQt6.
│ ├── test_metadata_manager.py 🟢 NISKI PRIORYTET - Testy jednostkowe dla src.logic.metadata_manager. Pokrywają generowanie ścieżek, konwersje ścieżek, ładowanie (różne scenariusze pliku), zapisywanie i aplikowanie metadanych (głównie is_favorite). Nieużywany import patch. Zależne od pytest, src.models.file_pair.
│ ├── test_scanner.py 🔴 WYSOKI PRIORYTET - Aktualnie zawiera tylko placeholder (assert True). Brak rzeczywistych testów jednostkowych dla logiki src.logic.scanner.py. Wymaga pilnego uzupełnienia o kompleksowe testy (różne struktury folderów, typy plików, przypadki brzegowe).
│ ├── test_file_operations.py 🔴 WYSOKI PRIORYTET - Testuje tylko funkcję open_archive_externally z src.logic.file_operations (z użyciem mocków dla OS i Qt). Krytyczny brak testów dla create_folder, rename_folder, delete_folder w tym pliku (są w test_folder_operations.py). Nieużywany import MagicMock. Zależny od pytest, unittest.mock.
│ ├── test_file_pair_favorite.py 🟢 NISKI PRIORYTET - Testy jednostkowe dla funkcjonalności 'Ulubione' w klasie FilePair (domyślny stan, przełączanie, ustawianie). Dobre, skoncentrowane testy. Zależne od pytest.
│ └── **init**.py 🟢 NISKI PRIORYTET - Pusty plik **init**.py, oznaczający katalog tests/unit jako subpakiet Pythona. Standardowe i niezbędne dla poprawnego działania Pytest.
└── integration/
├── test_main.py 🔴 WYSOKI PRIORYTET - Aktualnie zawiera tylko placeholder (assert True). Brak rzeczywistych testów integracyjnych. Wymaga pilnego uzupełnienia o testy sprawdzające współpracę komponentów aplikacji.
└── **init**.py 🟢 NISKI PRIORYTET - Pusty plik **init**.py, oznaczający katalog tests/integration jako subpakiet Pythona. Standardowe i niezbędne dla poprawnego działania Pytest.
