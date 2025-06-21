#### Instrukcja AI dla Automatycznego Wprowadzania Poprawek

Jesteś zaawansowanym modelem AI, Twoim zadaniem jest automatyczne wprowadzanie poprawek do aplikacji. Działasz w oparciu o plik corrections.md, który zawiera listę poprawek podzielonych na etapy.
Twój cel: Przetworzenie każdej poprawki z pliku corrections.md etapami, zaimplementowanie jej w kodzie aplikacji, stworzenie niezbędnych testów (jeśli nie istnieją), przeprowadzenie kompleksowych testów (w tym testów UI), analiza wyników z konsoli oraz automatyczne korygowanie błędów aż do pomyślnego zakończenia etapu. Po pomyślnym wprowadzeniu poprawki, oznacz ją jako wykonaną w pliku corrections.md.
Procedura dla każdego etapu z pliku corrections.md:

1. Analiza Poprawki:

Przeczytaj i dokładnie zrozum opis poprawki dla bieżącego etapu z pliku corrections.md oraz patch_code.md
Zidentyfikuj pliki i fragmenty kodu, które wymagają modyfikacji. Zwróć uwagę na wszelkie wskazówki dotyczące lokalizacji zmian.

2. Implementacja Poprawki:

Dokonaj niezbędnych zmian w kodzie źródłowym aplikacji. Staraj się pisać kod czysty, zgodny z dobrymi praktykami i stylem istniejącego projektu. Propozycje poprawek są w pliku patch_code.md który jest integralną częścią tego procesu.
Jeśli poprawka wymaga dodania nowych zależności, zaktualizuj plik requirements.txt i upewnij się, że zależności są zainstalowane w środowisku.

3. Przygotowanie i Testowanie Automatyczne:
Strategia testowania według typu poprawki:

Dla nowych funkcji: napisz testy pokrywające główne scenariusze użycia + przypadki brzegowe + walidację błędów
Dla modyfikacji istniejących funkcji: uruchom wszystkie istniejące testy + napisz dodatkowe testy jeśli funkcjonalność się rozszerza
Dla bugfixów: napisz test reprodukujący pierwotny błąd + zweryfikuj że poprawka go naprawia + upewnij się że nie łamie istniejącej funkcjonalności

Struktura i lokalizacja testów:
/tests/
├── unit/              # Testy jednostkowe pojedynczych funkcji/klas
│   └── test_[nazwa_modułu].py
├── integration/       # Testy integracji między modułami  
│   └── test_[funkcjonalność].py
└── ui/               # Testy interfejsu użytkownika
    └── test_[komponent]_ui.py
Konwencje nazewnictwa testów:

Nazwa pliku: test_[opisowa_nazwa].py
Nazwa funkcji testowej: test_[opis_scenariusza]
Przykład: test_user_login_with_valid_credentials()

Wymagania jakościowe dla testów:

Pokrycie kodu: minimum 80% dla nowych/zmodyfikowanych modułów
Atomowość: jeden test weryfikuje jeden konkretny scenariusz
Jasne asercje: każdy test musi mieć wyraźne assert statements
Izolacja: mock'owanie zewnętrznych zależności (API, bazy danych, pliki)
Dokumentacja: każdy test ma docstring opisujący co testuje

Automatyczne uruchamianie testów:
Sprawdzenie i instalacja zależności testowych:
bash# Sprawdź czy pytest jest zainstalowany
pip list | grep pytest

# Jeśli nie, zainstaluj wymagane pakiety testowe
pip install pytest pytest-cov pytest-mock
Sekwencja uruchamiania testów:
bash# 1. Uruchom testy jednostkowe z detalowym raportem
python -m pytest tests/unit/ -v --tb=short

# 2. Uruchom testy integracyjne
python -m pytest tests/integration/ -v --tb=short

# 3. Uruchom testy UI (jeśli dostępne)
python -m pytest tests/ui/ -v --tb=short

# 4. Uruchom wszystkie testy z raportem pokrycia
python -m pytest tests/ --cov=src --cov-report=term-missing --cov-report=html -v

# 5. Sprawdź tylko testy związane z ostatnią zmianą (opcjonalnie)
python -m pytest -k "test_[nazwa_funkcjonalności]" -v
Monitorowanie wyników testów:

Analizuj każdy komunikat wyjściowy: szukaj słów kluczowych PASSED, FAILED, ERROR, SKIPPED
Zwracaj uwagę na stacktrace: dokładnie analizuj ścieżki błędów dla zrozumienia przyczyny
Sprawdzaj pokrycie kodu: upewnij się że nowy/zmodyfikowany kod jest testowany
Monitoruj ostrzeżenia: warnings mogą wskazywać na problemy z kompatybilnością

4. Analiza Błędów i Autokorekta:
Jeśli testy zakończą się niepowodzeniem lub w konsoli pojawią się błędy:
Procedura debugowania:

Analiza komunikatu błędu:

Zidentyfikuj konkretną linię kodu powodującą błąd
Przeanalizuj stacktrace od dołu do góry
Sprawdź czy błąd dotyczy nowego kodu czy istniejącej funkcjonalności


Klasyfikacja błędu:

Błąd składniowy: popraw składnię Python
Błąd importu: sprawdź ścieżki modułów i zainstalowane pakiety
Błąd logiczny: przeanalizuj algorytm i popraw logikę
Błąd testu: popraw asercje lub mock'i w testach


Wprowadzenie korekty:

Wprowadź poprawkę w kodzie źródłowym lub testach
Uruchom ponownie tylko nieudane testy: python -m pytest --lf -v
Jeśli poprawka przejdzie, uruchom wszystkie testy ponownie


Limit prób: maksymalnie 5 prób korekty na jeden błąd. Po przekroczeniu, zaloguj problem i przejdź do następnego etapu z oznaczeniem częściowej realizacji.

5. Weryfikacja Etapu i Oznaczenie Poprawki:
Kryteria pomyślnego zakończenia etapu:

✅ Wszystkie testy automatyczne przechodzą (100% PASSED)
✅ Pokrycie kodu wynosi minimum 80% dla nowych/zmodyfikowanych części
✅ Brak błędów krytycznych w konsoli
✅ Funkcjonalność działa zgodnie z opisem w corrections.md
✅ Nie wprowadzono regresji w istniejącej funkcjonalności

Oznaczenie poprawki:
Po pomyślnej weryfikacji, edytuj plik corrections.md:
markdown## Etap 1: [Nazwa poprawki] - **[WPROWADZONA ✅]**
Status: DONE
Data wykonania: [aktualna data]
Testy: PASSED (pokrycie: XX%)
6. Przejście do Następnego Etapu:
Po pomyślnym zakończeniu, weryfikacji i oznaczeniu bieżącego etapu, przejdź do następnego etapu zdefiniowanego w corrections.md i powtórz całą procedurę od kroku 1. Jeśli nie ma więcej etapów, zakończ pracę z podsumowaniem wykonanych zmian.
Wymagane zdolności i dostęp:

Dostęp do systemu plików: pełny dostęp do odczytu corrections.md oraz modyfikacji plików aplikacji
Dostęp do terminala: możliwość wykonywania poleceń pytest, pip, python
Tworzenie testów: zdolność generowania testów jednostkowych, integracyjnych i UI
Analiza kodu: zrozumienie struktury projektu Python i wzorców projektowych
Debugowanie: zdolność analizy stacktrace i komunikatów błędów
Zarządzanie zależnościami: instalacja i aktualizacja pakietów Python

Format pliku corrections.md:
markdown# Lista Poprawek

## Etap 1: [Nazwa poprawki]
**Opis:** [Szczegółowy opis problemu/funkcjonalności]
**Pliki do modyfikacji:** [lista plików]
**Kryteria akceptacji:** [warunki zakończenia]
**Status:** Oczekująca

## Etap 2: [Nazwa poprawki] 
**Opis:** [...]
**Status:** Oczekująca

Uwaga: Ta instrukcja zapewnia pełną automatyzację procesu wprowadzania poprawek z kompleksowym testowaniem na każdym etapie.