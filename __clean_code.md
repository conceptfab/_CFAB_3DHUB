# Prompt do czyszczenia kodu z nieaktualnych komentarzy

## Zadanie
Przeskanuj podany kod cale go projektu i usuń wszystkie nieaktualne komentarze oraz zakomentowane fragmenty kodu, zachowując tylko aktualne i funkcjonalne komentarze dokumentacyjne. Zweryfikuj czy sa pliki nie używane - jeśli takie są, zmień ich rozszerzenie na py_del

## Instrukcje szczegółowe

### DO USUNIĘCIA:
1. **Zakomentowane linie kodu** - wszystkie linie poprzedzone `//`, `#`, `/* */`, `<!-- -->` itp., które zawierają kod
2. **Komentarze TODO/FIXME** - jeśli nie są aktualnie potrzebne
3. **Komentarze debugowe** - np. "console.log dla testów", "temporary fix"
4. **Historyczne komentarze** - odnoszące się do poprzednich wersji, zmian, dat
5. **Komentarze autorskie** - podpisy, daty modyfikacji, historie zmian
6. **Martwe komentarze** - opisujące kod który już nie istnieje
7. **Duplikaty komentarzy** - powtarzające się opisy tej samej funkcjonalności

### DO ZACHOWANIA:
1. **Komentarze dokumentacyjne** - opisujące działanie funkcji, klas, modułów
2. **Komentarze licencyjne** - nagłówki z informacjami o licencji
3. **Komentarze konfiguracyjne** - wyjaśniające ustawienia, parametry
4. **Komentarze bezpieczeństwa** - ostrzeżenia, ważne informacje
5. **Komentarze algorytmiczne** - wyjaśniające złożone logiki biznesowej

## Format odpowiedzi
Zwróć oczyszczony kod bez dodatkowych komentarzy na temat zmian.

## Kod do przeanalizowania:
[WKLEJ TUTAJ SWÓJ KOD]