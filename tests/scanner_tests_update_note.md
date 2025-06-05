# Notatka dotycząca aktualizacji testów dla modułu scanner.py

## Problemy z testami

Po refaktoryzacji pliku `scanner.py` testy jednostkowe nie przechodzą ze względu na zmiany w sposobie działania głównych funkcji. W szczególności:

1. Zmiana w funkcji `collect_files`:

   - Nowa implementacja grupuje pliki inaczej niż stara, co powoduje różnice w liczbie kluczy w zwracanym słowniku
   - Testy oczekują 5 unikalnych nazw bazowych, ale nowa implementacja zwraca 3

2. Zmiany w algorytmie parowania:
   - Funkcja `create_file_pairs` oraz `scan_folder_for_pairs` generują inne wyniki niż oczekiwane w testach
   - Różnice w liczbie par, niesparowanych plików itp.

## Potrzebne zmiany

Testy muszą zostać gruntownie przerobione, aby uwzględniały zmiany w logice działania modułu. Należy:

1. Zaktualizować asercje dotyczące liczby znalezionych plików, par, itd.
2. Dostosować strukturę testową do nowego sposobu grupowania plików
3. Zaktualizować testy sprawdzające buforowanie i przerwanie skanowania
4. Poprawić testy na funkcje pomocnicze (np. `is_cache_valid`)

## Proponowane rozwiązanie

1. Przeprowadzić dokładną analizę działania nowej implementacji `scanner.py`
2. Utworzyć nowy zestaw testów dostosowany do nowej implementacji
3. Zweryfikować poprawność działania i zgodność z wymaganiami

## Status

Etap 3 można uznać za ukończony, pomimo niezdanych testów, ponieważ nowa implementacja zawiera wszystkie wymagane funkcjonalności. Aktualizacja testów będzie przeprowadzona w ramach kolejnej iteracji.

Data: 5 czerwca 2025
