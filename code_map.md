# Mapa projektu CFAB_3DHUB

## Struktura projektu i priorytetyzacja

```
CFAB_3DHUB/
├── run_app.py 🟡 ŚREDNI PRIORYTET - Punkt wejściowy, potrzebne uporządkowanie konfiguracji uruchomienia
├── requirements.txt 🟢 NISKI PRIORYTET - Lista zależności, wymaga weryfikacji
├── run_tests.bat 🟡 ŚREDNI PRIORYTET - Skrypt testowy, potrzebna analiza pokrycia testami
├── src/
│   ├── __init__.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny pakietu
│   ├── app_config.py 🔴 WYSOKI PRIORYTET - Problemy z obsługą konfiguracji, błędne zarządzanie ścieżkami
│   ├── main.py 🟡 ŚREDNI PRIORYTET - Główna funkcja aplikacji, potrzebna refaktoryzacja logiki uruchomienia
│   ├── logic/
│   │   ├── __init__.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny modułu
│   │   ├── file_operations.py 🔴 WYSOKI PRIORYTET - Operacje na plikach, potencjalne błędy i nieefektywny kod
│   │   ├── filter_logic.py 🟡 ŚREDNI PRIORYTET - Logika filtrowania, wymaga optymalizacji
│   │   ├── metadata_manager.py 🔴 WYSOKI PRIORYTET - Zarządzanie metadanymi, problemy z synchronizacją
│   │   └── scanner.py 🔴 WYSOKI PRIORYTET - Skanowanie folderów, problemy wydajnościowe przy dużych katalogach
│   ├── models/
│   │   ├── __init__.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny modułu
│   │   └── file_pair.py 🟡 ŚREDNI PRIORYTET - Model pary plików, potrzeba lepszej walidacji danych
│   ├── ui/
│   │   ├── __init__.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny modułu
│   │   ├── main_window.py 🔴 WYSOKI PRIORYTET - Główne okno aplikacji, zbyt duży i złożony plik, wymaga podziału
│   │   ├── integration_guide.txt 🟢 NISKI PRIORYTET - Dokumentacja integracji UI
│   │   ├── delegates/
│   │   │   └── __init__.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny podmodułu
│   │   └── widgets/
│   │       ├── __init__.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny podmodułu
│   │       ├── file_tile_widget.py 🟡 ŚREDNI PRIORYTET - Widget kafelka pliku, problemy z wydajnością renderowania
│   │       └── preview_dialog.py 🟡 ŚREDNI PRIORYTET - Okno podglądu, problemy z obsługą dużych obrazów
│   └── utils/
│       ├── __init__.py 🟢 NISKI PRIORYTET - Plik inicjalizacyjny modułu
│       ├── image_utils.py 🟡 ŚREDNI PRIORYTET - Funkcje pomocnicze do obrazów, nieefektywna obsługa dużych plików
│       ├── logging_config.py 🟢 NISKI PRIORYTET - Konfiguracja logowania, wymaga standaryzacji
│       └── path_utils.py 🔴 WYSOKI PRIORYTET - Operacje na ścieżkach, problemy z kompatybilnością między platformami
```

## Wstępna analiza plików

### run_app.py 🟡 ŚREDNI PRIORYTET

- **Funkcjonalność**: Punkt wejściowy aplikacji, konfiguruje sys.path i uruchamia główną funkcję
- **Wydajność**: Niski wpływ na wydajność, głównie konfiguracja
- **Stan obecny**: Nieoptymalna konfiguracja sys.path, redundantne sprawdzanie argumentów
- **Zależności**: Zależy od src.main
- **Priorytet poprawek**: Średni - można zoptymalizować konfigurację uruchomienia

### requirements.txt 🟢 NISKI PRIORYTET

- **Funkcjonalność**: Lista wymaganych zależności
- **Wydajność**: Nie wpływa na wydajność, używany tylko w fazie instalacji
- **Stan obecny**: Może wymagać aktualizacji i weryfikacji wersji
- **Zależności**: Nie ma bezpośrednich zależności wewnątrz projektu
- **Priorytet poprawek**: Niski - warto zweryfikować aktualne wersje bibliotek

### run_tests.bat 🟡 ŚREDNI PRIORYTET

- **Funkcjonalność**: Uruchamia testy automatyczne
- **Wydajność**: Nie wpływa bezpośrednio na wydajność aplikacji
- **Stan obecny**: Brak informacji o pokryciu testami, potencjalnie niekompletne testy
- **Zależności**: Zależy od struktury testów (niewidocznej w obecnym zestawie plików)
- **Priorytet poprawek**: Średni - ważne dla zapewnienia jakości

### src/app_config.py 🔴 WYSOKI PRIORYTET

- **Funkcjonalność**: Zarządza konfiguracją aplikacji
- **Wydajność**: Krytyczna dla inicjalizacji aplikacji
- **Stan obecny**: Problemy z obsługą ścieżek, brak kompletnego mechanizmu obsługi błędów
- **Zależności**: Używany przez wiele modułów
- **Priorytet poprawek**: Wysoki - centralna konfiguracja wpływa na całą aplikację

### src/main.py 🟡 ŚREDNI PRIORYTET

- **Funkcjonalność**: Główna funkcja aplikacji
- **Wydajność**: Średni wpływ - inicjalizacja aplikacji
- **Stan obecny**: Wymaga refaktoryzacji logiki uruchomienia, lepszej obsługi błędów
- **Zależności**: Zależy od src.ui.main_window, src.utils.logging_config
- **Priorytet poprawek**: Średni - może zostać zoptymalizowany

### src/logic/file_operations.py 🔴 WYSOKI PRIORYTET

- **Funkcjonalność**: Operacje na plikach
- **Wydajność**: Wysoki wpływ - operacje I/O mogą wpływać na szybkość działania
- **Stan obecny**: Potencjalne błędy, brak obsługi wyjątków, nieefektywny kod
- **Zależności**: Używany przez wiele modułów
- **Priorytet poprawek**: Wysoki - krytyczne operacje I/O

### src/logic/filter_logic.py 🟡 ŚREDNI PRIORYTET

- **Funkcjonalność**: Logika filtrowania plików
- **Wydajność**: Średni wpływ - filtrowanie dużych zestawów danych
- **Stan obecny**: Wymaga optymalizacji algorytmów filtrowania
- **Zależności**: Używany przez interfejs użytkownika
- **Priorytet poprawek**: Średni - możliwa znacząca optymalizacja

### src/logic/metadata_manager.py 🔴 WYSOKI PRIORYTET

- **Funkcjonalność**: Zarządzanie metadanymi plików
- **Wydajność**: Wysoki wpływ - operacje na metadanych wpływają na responsywność
- **Stan obecny**: Problemy z synchronizacją, potencjalne wycieki pamięci
- **Zależności**: Używany przez moduł scanner i interfejs użytkownika
- **Priorytet poprawek**: Wysoki - kluczowy dla poprawnego działania aplikacji

### src/logic/scanner.py 🔴 WYSOKI PRIORYTET

- **Funkcjonalność**: Skanowanie folderów w poszukiwaniu plików
- **Wydajność**: Krytyczny wpływ - główne wąskie gardło przy obsłudze dużych katalogów
- **Stan obecny**: Nieefektywny algorytm skanowania, brak buforowania wyników
- **Zależności**: Używany przez interfejs użytkownika
- **Priorytet poprawek**: Wysoki - kluczowy dla wydajności aplikacji

### src/models/file_pair.py 🟡 ŚREDNI PRIORYTET

- **Funkcjonalność**: Model reprezentujący parę plików (archiwum i podgląd)
- **Wydajność**: Średni wpływ - używany w całej aplikacji
- **Stan obecny**: Potrzeba lepszej walidacji danych, potencjalne dublowanie funkcjonalności
- **Zależności**: Używany przez scanner, interfejs użytkownika
- **Priorytet poprawek**: Średni - można zwiększyć spójność danych

### src/ui/main_window.py 🔴 WYSOKI PRIORYTET

- **Funkcjonalność**: Główne okno aplikacji
- **Wydajność**: Wysoki wpływ - interfejs użytkownika, najczęściej używany komponent
- **Stan obecny**: Zbyt duży i złożony plik, mieszanie logiki biznesowej z UI, wymaga podziału
- **Zależności**: Zależy od większości modułów logiki
- **Priorytet poprawek**: Wysoki - refaktoryzacja konieczna dla utrzymywalności

### src/ui/widgets/file_tile_widget.py 🟡 ŚREDNI PRIORYTET

- **Funkcjonalność**: Widget wyświetlający kafelek pliku
- **Wydajność**: Średni wpływ - renderowanie wielu kafelków może obciążać UI
- **Stan obecny**: Problemy z wydajnością renderowania przy dużej liczbie plików
- **Zależności**: Używany przez main_window
- **Priorytet poprawek**: Średni - optymalizacja renderowania poprawi UX

### src/ui/widgets/preview_dialog.py 🟡 ŚREDNI PRIORYTET

- **Funkcjonalność**: Okno podglądu plików
- **Wydajność**: Średni wpływ - wyświetlanie dużych obrazów
- **Stan obecny**: Problemy z obsługą dużych obrazów, potencjalne zamrożenia UI
- **Zależności**: Używany przez main_window
- **Priorytet poprawek**: Średni - istotne dla doświadczenia użytkownika

### src/utils/image_utils.py 🟡 ŚREDNI PRIORYTET

- **Funkcjonalność**: Funkcje pomocnicze do operacji na obrazach
- **Wydajność**: Średni wpływ - przetwarzanie obrazów
- **Stan obecny**: Nieefektywna obsługa dużych plików, brak skalowania
- **Zależności**: Używany przez widgets i preview_dialog
- **Priorytet poprawek**: Średni - optymalizacja poprawi wydajność UI

### src/utils/path_utils.py 🔴 WYSOKI PRIORYTET

- **Funkcjonalność**: Operacje na ścieżkach plików
- **Wydajność**: Wysoki wpływ - używany w całej aplikacji do operacji na plikach
- **Stan obecny**: Problemy z kompatybilnością między platformami, niespójne normalizacje ścieżek
- **Zależności**: Używany przez większość modułów
- **Priorytet poprawek**: Wysoki - kluczowy dla poprawnego działania na różnych systemach

### src/utils/logging_config.py 🟢 NISKI PRIORYTET

- **Funkcjonalność**: Konfiguracja systemu logowania
- **Wydajność**: Niski wpływ - jednorazowa konfiguracja
- **Stan obecny**: Wymaga standaryzacji poziomów logowania
- **Zależności**: Używany przez main.py
- **Priorytet poprawek**: Niski - działa poprawnie, ale można zoptymalizować

## Plan etapu 2

### Kolejność analizy

1. **Wysokie priorytety (🔴):**

   - src/app_config.py - centralne zarządzanie konfiguracją
   - src/logic/scanner.py - kluczowe dla wydajności skanowania
   - src/logic/file_operations.py - krytyczne operacje na plikach
   - src/logic/metadata_manager.py - zarządzanie metadanymi
   - src/ui/main_window.py - główny komponent UI
   - src/utils/path_utils.py - kluczowe dla obsługi ścieżek

2. **Średnie priorytety (🟡):**

   - run_app.py - punkt wejściowy
   - src/main.py - główna funkcja aplikacji
   - src/logic/filter_logic.py - logika filtrowania
   - src/models/file_pair.py - model danych
   - src/ui/widgets/file_tile_widget.py - komponenty UI
   - src/ui/widgets/preview_dialog.py - okno podglądu
   - src/utils/image_utils.py - operacje na obrazach
   - run_tests.bat - testy automatyczne

3. **Niskie priorytety (🟢):**
   - requirements.txt - zależności
   - src/utils/logging_config.py - konfiguracja logowania
   - Pozostałe pliki inicjalizacyjne **init**.py

### Grupowanie plików

1. **Grupa konfiguracyjna:**

   - src/app_config.py
   - run_app.py
   - src/main.py
   - requirements.txt

2. **Grupa operacji na plikach:**

   - src/logic/file_operations.py
   - src/logic/scanner.py
   - src/utils/path_utils.py

3. **Grupa zarządzania danymi:**

   - src/logic/metadata_manager.py
   - src/models/file_pair.py
   - src/logic/filter_logic.py

4. **Grupa interfejsu użytkownika:**

   - src/ui/main_window.py
   - src/ui/widgets/file_tile_widget.py
   - src/ui/widgets/preview_dialog.py

5. **Grupa narzędzi pomocniczych:**
   - src/utils/image_utils.py
   - src/utils/logging_config.py

### Szacowany zakres zmian

1. **Refaktoryzacja kodu:**

   - Podział dużych plików (szczególnie main_window.py)
   - Wydzielenie logiki biznesowej z interfejsu użytkownika

2. **Optymalizacja wydajności:**

   - Poprawa algorytmów skanowania i filtrowania
   - Optymalizacja operacji I/O
   - Lepsze zarządzanie pamięcią dla obrazów

3. **Poprawa stabilności:**

   - Lepsza obsługa błędów i wyjątków
   - Ujednolicenie obsługi ścieżek między platformami

4. **Poprawki architektury:**
   - Centralizacja konfiguracji
   - Ujednolicenie API pomiędzy modułami
   - Wprowadzenie wzorców projektowych gdzie potrzebne
