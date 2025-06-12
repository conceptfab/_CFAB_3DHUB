1. Weryfikacja i optymalizacja logowania - logowanie ma przyjmować ustawienia wg ustwien w preferencjach - INFO, DEBUG itp. Oto log startowy który jest zdecydowanie za długi i budzi wątpliwości:
   Root in path: c:\_cloud_CFAB_3DHUB
   2025-06-13 00:31:46,360 - root - INFO - System logowania zainicjalizowany
   Wczytywanie stylów z: c:\_cloud_CFAB_3DHUB\src\resources\styles.qss
   Załadowano 7902 bajtów stylów (UTF-8)
   2025-06-13 00:31:46,361 - root - INFO - Załadowano style z: c:\_cloud_CFAB_3DHUB\src\resources\styles.qss
   2025-06-13 00:31:46,364 - root - INFO - System logowania zainicjalizowany
   2025-06-13 00:31:46,432 - root - INFO - Stosowanie arkusza stylów (7902 bajtów)
   2025-06-13 00:31:46,437 - src.app_config - INFO - Konfiguracja wczytana z: C:/Users/micz/.CFAB_3DHUB/config.json
   2025-06-13 00:31:46,438 - root - INFO - Initial slider position: 50%, thumbnail size: 175px
   2025-06-13 00:31:46,927 - root - INFO - 🏗️ CREATE_UNPAIRED_FILES_TAB - rozpoczynam tworzenie
   2025-06-13 00:31:46,928 - root - INFO - ✅ Utworzono podstawowy widget i layout
   2025-06-13 00:31:46,929 - root - INFO - ✅ Utworzono splitter
   2025-06-13 00:31:46,930 - root - INFO - 🔧 Tworzę listę archiwów...
   2025-06-13 00:31:46,939 - root - INFO - ✅ Lista archiwów utworzona. Widget: True
   2025-06-13 00:31:46,940 - root - INFO - ✅ Wartość widget archiwów: <PyQt6.QtWidgets.QListWidget object at 0x0000015C57454FF0>
   2025-06-13 00:31:46,941 - root - INFO - 🔧 Tworzę listę podglądów...
   2025-06-13 00:31:46,949 - root - INFO - ✅ Lista podglądów utworzona. Widget: True
   2025-06-13 00:31:46,951 - root - INFO - ✅ Wartość widget podglądów: <PyQt6.QtWidgets.QListWidget object at 0x0000015C57455450>
   2025-06-13 00:31:46,959 - root - INFO - ✅ Przycisk parowania utworzony
   2025-06-13 00:31:46,960 - root - INFO - 🎉 CREATE_UNPAIRED_FILES_TAB - zakończono pomyślnie
   2025-06-13 00:31:46,968 - root - INFO - ThreadCoordinator zainicjalizowany
   2025-06-13 00:31:47,012 - src.ui.directory_tree_manager - INFO - DirectoryTreeManager: Utworzono StatsProxyModel
   2025-06-13 00:31:47,019 - src.ui.directory_tree_manager - INFO - Drag and drop handlers skonfigurowane
   2025-06-13 00:31:47,023 - root - INFO - 🎛️ PREFERENCJE WCZYTANE POMYŚLNIE!
   2025-06-13 00:31:47,027 - root - INFO - 📏 Thumbnail slider: 87%
   2025-06-13 00:31:47,029 - root - INFO - 🗂️ Auto-load folder: True
   2025-06-13 00:31:47,030 - root - INFO - 📁 Ostatni folder: C:/\_cloud/**_TEST_FOLDER/
   2025-06-13 00:31:47,031 - root - INFO - 💾 Cache miniaturek: 500 szt.
   2025-06-13 00:31:47,032 - root - INFO - 🧠 Pamięć cache: 100MB
   2025-06-13 00:31:47,034 - root - INFO - 🔄 Auto-loading ostatniego folderu: C:/\_cloud/_**TEST_FOLDER/
   2025-06-13 00:31:47,036 - root - INFO - 🔄 Auto-loading z domyślnego folderu
   2025-06-13 00:31:47,037 - root - INFO - Wybrano folder roboczy: C:/\_cloud/**_TEST_FOLDER
   2025-06-13 00:31:47,040 - src.services.scanning_service - INFO - Rozpoczynam skanowanie: C:/\_cloud/_**TEST_FOLDER
   2025-06-13 00:31:47,042 - src.logic.scanner_core - INFO - Rozpoczęto skanowanie katalogu: C:/\_cloud/**_TEST_FOLDER ze strategią first_match
   2025-06-13 00:31:47,044 - src.logic.scanner_core - INFO - Rozpoczęto streaming zbieranie plików z katalogu: C:/\_cloud/_**TEST_FOLDER
   2025-06-13 00:31:47,046 - src.logic.scanner_core - INFO - Zakończono streaming zbieranie plików. Przeskanowano 1 folderów, znaleziono 0 plików w czasie 0.00s
   2025-06-13 00:31:47,048 - src.logic.scanner_core - INFO - Zakończono skanowanie 'C:/\_cloud/**_TEST_FOLDER' w czasie 0.01s. Znaleziono 0 par, 0 niesparowanych archiwów i 0 niesparowanych podglądów.
   2025-06-13 00:31:47,050 - src.services.scanning_service - INFO - Skanowanie zakończone: 0 par, 0 niesparowanych archiwów, 0 niesparowanych podglądów
   2025-06-13 00:31:47,051 - root - INFO - Zakończono tworzenie wszystkich kafelków.  
   2025-06-13 00:31:47,052 - root - INFO - 🔍 UPDATE_UNPAIRED_FILES_LISTS wywołane  
   2025-06-13 00:31:47,053 - root - INFO - 📊 Controller unpaired_archives: 0
   2025-06-13 00:31:47,054 - root - INFO - 📊 Controller unpaired_previews: 0
   2025-06-13 00:31:47,055 - root - INFO - ✅ ZAKOŃCZONO aktualizację listy niesparowanych: 0 archiwów, 0 podglądów.
   2025-06-13 00:31:47,056 - root - INFO - DEBUG: current_working_directory = 'C:/\_cloud/_**TEST_FOLDER'
   2025-06-13 00:31:47,057 - root - INFO - DEBUG: Wywołuję init_directory_tree...
   2025-06-13 00:31:47,058 - src.ui.directory_tree_manager - INFO - INIT_DIRECTORY_TREE wywołane dla: C:/\_cloud/**_TEST_FOLDER
   2025-06-13 00:31:47,067 - root - INFO - Znaleziono 5 folderów z plikami w: C:/\_cloud/_**TEST_FOLDER
   2025-06-13 00:31:47,076 - root - INFO - Drzewo katalogów zainicjalizowane - główny folder: C:/\_cloud/**_TEST_FOLDER, foldery z plikami: 5
   2025-06-13 00:31:47,082 - root - INFO - Zaznaczono aktualny folder w drzewie: C:/\_cloud/_**TEST_FOLDER
   2025-06-13 00:31:47,083 - root - INFO - DEBUG: init_directory_tree zakończone
   2025-06-13 00:31:47,086 - root - INFO - Widok zaktualizowany. Wyświetlono po filtracji: 0.
   2025-06-13 00:31:47,088 - src.controllers.main_window_controller - INFO - Skanowanie ukończone: 0 par, 0 archiwów, 0 podglądów
   2025-06-13 00:31:47,089 - root - INFO - Controller scan SUCCESS: C:/\_cloud/**_TEST_FOLDER
   2025-06-13 00:31:47,090 - src.ui.delegates.workers.base_workers - INFO - SaveMetadataWorker: Rozpoczęto wykonywanie (priorytet: 2)
   2025-06-13 00:31:47,091 - root - INFO - Główne okno aplikacji zostało zainicjalizowane
   2025-06-13 00:31:48,895 - root - INFO - Aplikacja CFAB_3DHUB uruchomiona poprzez main()
   2025-06-13 00:31:48,897 - src.logic.metadata_manager - INFO - Rozpoczęcie zapisu metadanych dla katalogu: C:/\_cloud/_**TEST_FOLDER
   2025-06-13 00:31:48,916 - src.logic.metadata_manager - INFO - Pomyślnie zapisano metadane do C:/\_cloud/**_TEST_FOLDER/.app_metadata/metadata.json
   2025-06-13 00:31:48,917 - src.ui.delegates.workers.base_workers - INFO - SaveMetadataWorker: Zakończono pomyślnie w 1.83s
   2025-06-13 00:31:48,952 - src.ui.directory_tree_manager - INFO - Znaleziono 6 widocznych folderów do obliczenia statystyk
   2025-06-13 00:31:48,979 - src.logic.scanner_core - INFO - Rozpoczęto skanowanie katalogu: C:/\_cloud/_**TEST_FOLDER/Vehicle/motors ze strategią first_match
   2025-06-13 00:31:48,981 - src.logic.scanner_core - INFO - Rozpoczęto skanowanie katalogu: C:/\_cloud/**_TEST_FOLDER/test ze strategią first_match
   2025-06-13 00:31:48,983 - src.logic.scanner_core - INFO - Rozpoczęto streaming zbieranie plików z katalogu: C:/\_cloud/_**TEST_FOLDER/test
   2025-06-13 00:31:48,984 - src.logic.scanner_core - INFO - Rozpoczęto streaming zbieranie plików z katalogu: C:/\_cloud/**_TEST_FOLDER/Vehicle/motors
   2025-06-13 00:31:48,990 - src.logic.scanner_core - INFO - Zakończono streaming zbieranie plików. Przeskanowano 1 folderów, znaleziono 38 plików w czasie 0.01s
   2025-06-13 00:31:48,990 - src.logic.scanner_core - INFO - Zakończono streaming zbieranie plików. Przeskanowano 1 folderów, znaleziono 14 plików w czasie 0.00s
   2025-06-13 00:31:48,994 - src.logic.scanner_core - INFO - Rozpoczęto skanowanie katalogu: C:/\_cloud/_**TEST_FOLDER/Vehicle/bikes ze strategią first_match
   2025-06-13 00:31:48,996 - src.logic.scanner_core - INFO - Rozpoczęto streaming zbieranie plików z katalogu: C:/\_cloud/**_TEST_FOLDER/Vehicle/bikes
   2025-06-13 00:31:48,997 - src.logic.scanner_core - INFO - Zakończono skanowanie 'C:/\_cloud/_**TEST_FOLDER/Vehicle/motors' w czasie 0.02s. Znaleziono 7 par, 0 niesparowanych archiwów i 0 niesparowanych podglądów.
   2025-06-13 00:31:49,000 - src.logic.scanner_core - INFO - Zakończono skanowanie 'C:/\_cloud/**_TEST_FOLDER/test' w czasie 0.02s. Znaleziono 19 par, 0 niesparowanych archiwów i 0 niesparowanych podglądów.
   2025-06-13 00:31:49,003 - src.logic.scanner_core - INFO - Zakończono streaming zbieranie plików. Przeskanowano 1 folderów, znaleziono 46 plików w czasie 0.01s
   2025-06-13 00:31:49,005 - src.logic.scanner_core - INFO - CACHE HIT: Używam buforowanych wyników dla C:/\_cloud/_**TEST_FOLDER/Vehicle/motors ze strategią first_match
   2025-06-13 00:31:49,008 - src.ui.delegates.workers.base_workers - INFO - FolderStatisticsWorker: Zakończono pomyślnie
   2025-06-13 00:31:49,009 - src.logic.scanner_core - INFO - CACHE HIT: Używam buforowanych wyników dla C:/\_cloud/**_TEST_FOLDER/test ze strategią first_match
   2025-06-13 00:31:49,010 - src.ui.delegates.workers.base_workers - INFO - FolderStatisticsWorker: Zakończono pomyślnie
   2025-06-13 00:31:49,012 - src.logic.scanner_core - INFO - Zakończono skanowanie 'C:/\_cloud/_**TEST_FOLDER/Vehicle/bikes' w czasie 0.02s. Znaleziono 23 par, 0 niesparowanych archiwów i 0 niesparowanych podglądów.
   2025-06-13 00:31:49,016 - src.logic.scanner_core - INFO - CACHE HIT: Używam buforowanych wyników dla C:/\_cloud/**_TEST_FOLDER/Vehicle/bikes ze strategią first_match
   2025-06-13 00:31:49,018 - src.ui.delegates.workers.base_workers - INFO - FolderStatisticsWorker: Zakończono pomyślnie
   2025-06-13 00:31:49,464 - src.logic.scanner_core - INFO - Rozpoczęto skanowanie katalogu: C:/\_cloud/_**TEST_FOLDER/Vehicle ze strategią first_match
   2025-06-13 00:31:49,465 - src.logic.scanner_core - INFO - Rozpoczęto streaming zbieranie plików z katalogu: C:/\_cloud/**_TEST_FOLDER/Vehicle
   2025-06-13 00:31:49,471 - src.logic.scanner_core - INFO - Zakończono streaming zbieranie plików. Przeskanowano 1 folderów, znaleziono 128 plików w czasie 0.01s
   2025-06-13 00:31:49,477 - src.logic.scanner_core - INFO - Zakończono skanowanie 'C:/\_cloud/_**TEST_FOLDER/Vehicle' w czasie 0.01s. Znaleziono 60 par, 7 niesparowanych archiwów i 1 niesparowanych podglądów.
   2025-06-13 00:31:49,481 - src.logic.scanner_core - INFO - CACHE HIT: Używam buforowanych wyników dla C:/\_cloud/**_TEST_FOLDER/Vehicle ze strategią first_match
   2025-06-13 00:31:49,482 - src.ui.delegates.workers.base_workers - INFO - FolderStatisticsWorker: Zakończono pomyślnie
   2025-06-13 00:31:49,489 - src.logic.scanner_core - INFO - Rozpoczęto skanowanie katalogu: C:/\_cloud/_**TEST_FOLDER/\_test ze strategią first_match
   2025-06-13 00:31:49,490 - src.logic.scanner_core - INFO - Rozpoczęto streaming zbieranie plików z katalogu: C:/\_cloud/**_TEST_FOLDER/\_test
   2025-06-13 00:31:49,499 - src.logic.scanner_core - INFO - Zakończono streaming zbieranie plików. Przeskanowano 1 folderów, znaleziono 322 plików w czasie 0.01s
   2025-06-13 00:31:49,508 - src.logic.scanner_core - INFO - Zakończono skanowanie 'C:/\_cloud/_**TEST_FOLDER/\_test' w czasie 0.02s. Znaleziono 156 par, 2 niesparowanych archiwów i 8 niesparowanych podglądów.
   2025-06-13 00:31:49,514 - src.logic.scanner_core - INFO - CACHE HIT: Używam buforowanych wyników dla C:/\_cloud/**_TEST_FOLDER/\_test ze strategią first_match
   2025-06-13 00:31:49,515 - src.ui.delegates.workers.base_workers - INFO - FolderStatisticsWorker: Zakończono pomyślnie
   2025-06-13 00:31:49,524 - src.logic.scanner_core - INFO - Rozpoczęto skanowanie katalogu: C:/\_cloud/_**TEST_FOLDER ze strategią first_match
   2025-06-13 00:31:49,527 - src.logic.scanner_core - INFO - Rozpoczęto streaming zbieranie plików z katalogu: C:/\_cloud/**_TEST_FOLDER
   2025-06-13 00:31:49,529 - src.logic.scanner_core - INFO - Zakończono streaming zbieranie plików. Przeskanowano 1 folderów, znaleziono 0 plików w czasie 0.00s
   2025-06-13 00:31:49,531 - src.logic.scanner_core - INFO - Zakończono skanowanie 'C:/\_cloud/_**TEST_FOLDER' w czasie 0.01s. Znaleziono 0 par, 0 niesparowanych archiwów i 0 niesparowanych podglądów.
   2025-06-13 00:31:49,534 - src.logic.scanner_core - INFO - CACHE HIT: Używam buforowanych wyników dla C:/\_cloud/\_\_\_TEST_FOLDER ze strategią first_match
   2025-06-13 00:31:49,535 - src.ui.delegates.workers.base_workers - INFO - FolderStatisticsWorker: Zakończono pomyślnie
   2025-06-13 00:31:49,553 - root - INFO - ✅ Metadane zapisane pomyślnie.
   2025-06-13 00:31:52,387 - root - INFO - Czyszczenie wszystkich wątków...
   2025-06-13 00:31:52,388 - root - INFO - Wszystkie wątki wyczyszczone

2. Dodanie 3 zakładki z podglądem danego folderu w stylu eksploratora - widoczne maja być wszystkie plik
3. Dodanie do 3 zakładki toola - random_name.py
