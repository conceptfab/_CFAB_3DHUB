# Prompt: Analiza Over-Engineering w Projekcie Python

## Zadanie

Przeprowadź kompleksową analizę projektu Python pod kątem over-engineeringu. Wygeneruj szczegółowy raport refaktoryzacji w formacie Markdown, który poprowadzi przez proces usuwania nadmiarowego kodu przy zachowaniu funkcjonalności i stabilności aplikacji.

## Narzędzia i Technologie

### Narzędzia do analizy kodu:

- **radon** - analiza cyklomatycznej złożoności: `pip install radon`
- **vulture** - wykrywanie nieużywanego kodu: `pip install vulture`
- **bandit** - analiza bezpieczeństwa: `pip install bandit`
- **pylint** - kompleksowa analiza jakości kodu: `pip install pylint`
- **flake8** - sprawdzanie stylu kodu: `pip install flake8`
- **mypy** - sprawdzanie typów: `pip install mypy`

### Komendy do uruchomienia:

```bash
# Analiza złożoności cyklomatycznej
radon cc -s ./src --total-average

# Wykrywanie nieużywanego kodu
vulture ./src --min-confidence 80

# Sprawdzanie bezpieczeństwa
bandit -r ./src -f json -o security_report.json

# Kompleksowa analiza jakości
pylint ./src --output-format=json > pylint_report.json

# Sprawdzanie stylu
flake8 ./src --statistics --tee --output-file=flake8_report.txt
```

### Narzędzia Git do bezpiecznej refaktoryzacji:

```bash
# Utworzenie brancha refaktoryzacji
git checkout -b refactor-over-engineering

# Backup przed zmianami
git tag backup-before-refactor

# Sprawdzenie statusu
git status

# Commitowanie zmian krok po kroku
git add -p  # dodawanie wybiórcze
git commit -m "refactor: usuń nadmiarową abstrakcję w [nazwa_modułu]"
```

## Fazy Analizy

### FAZA 1: Inwentaryzacja i Mapowanie

1. **Stwórz mapę architektury projektu**

   - Lista wszystkich plików .py z ścieżkami
   - Opis odpowiedzialności każdego modułu
   - Wykaz klas, funkcji i metod w każdym pliku
   - Zależności między modułami (imports)
   - Identyfikacja warstw aplikacji (model, view, controller, services, utils)

2. **Analiza metryk kodu**
   - Cyklomatyczna złożoność funkcji
   - Długość klas i funkcji (LOC)
   - Głębokość dziedziczenia
   - Coupling między modułami
   - Duplikacja kodu

### FAZA 2: Identyfikacja Over-Engineering Patterns

Znajdź i udokumentuj następujące wzorce over-engineeringu:

1. **Nadmiarowe abstrakcje**

   - Klasy z jedną metodą (zastąp funkcją)
   - Interfejsy używane tylko raz
   - Fabryki dla prostych obiektów
   - Wzorce projektowe bez uzasadnienia

2. **Niepotrzebna złożoność**

   - Zagnieżdżone dziedziczenia bez powodu
   - Metody z wieloma parametrami
   - Złożone konfiguracje dla prostych zadań
   - Przesadne używanie dekoratorów

3. **Duplikacja kodu**

   - Identyczne lub podobne funkcje
   - Powtarzające się logiki biznesowe
   - Redundantne klasy pomocnicze

4. **Nieużywany kod**
   - Martwy kod (dead code)
   - Nieużywane importy
   - Porzucone funkcje/klasy

### FAZA 3: Plan Refaktoryzacji

Dla każdego zidentyfikowanego problemu:

1. **Opis problemu**

   - Lokalizacja (plik, linia)
   - Typ over-engineeringu
   - Wpływ na czytelność/wydajność

2. **Proponowane rozwiązanie**

   - Konkretne zmiany kodu
   - Uzasadnienie refaktoryzacji
   - Alternatywne podejścia

3. **Ocena ryzyka**
   - Poziom ryzyka (niski/średni/wysoki)
   - Potencjalne skutki uboczne
   - Zależności do sprawdzenia

## Wymagania Raportu

### Struktura Dokumentu MD

```markdown
# Raport Refaktoryzacji: [Nazwa Projektu]

## 1. Podsumowanie Wykonawcze

- Ogólny stan projektu
- Główne problemy over-engineeringu
- Szacowany czas refaktoryzacji
- Potencjalne korzyści

## 2. Mapa Architektury Projektu

### 2.1 Struktura Plików

### 2.2 Zależności Modułów

### 2.3 Warstwy Aplikacji

## 3. Analiza Over-Engineering

### 3.1 Nadmiarowe Abstrakcje

### 3.2 Niepotrzebna Złożoność

### 3.3 Duplikacja Kodu

### 3.4 Nieużywany Kod

## 4. Plan Refaktoryzacji

### UWAGA: Co BRAK w tym dokumencie szablonowym:

- ❌ **Konkretnej listy plików** projektu CFAB_3DHUB do analizy
- ❌ **Zidentyfikowanych problemów** w istniejącym kodzie
- ❌ **Priorytetyzacji plików** do refaktoryzacji
- ❌ **Szczegółowych rekomendacji** dla konkretnych plików

_Ten dokument to szablon/prompt do analizy - nie gotowy raport z konkretnymi zaleceniami._

### 4.1 Zmiany Wysokiego Priorytetu

### 4.2 Zmiany Średniego Priorytetu

### 4.3 Zmiany Niskiego Priorytetu

## 5. Strategia Bezpieczeństwa

### 5.1 Plan Backupów

### 5.2 Strategia Testowania

### 5.3 Procedura Wdrożenia

## 6. Harmonogram Implementacji
```

### Format Opisu Zmian

Dla każdej zmiany użyj tego formatu:

````markdown
#### Zmiana w pliku: `src/services/user_service.py`

**Funkcja/Klasa:** `UserManager.create_user_with_validation()`
**Problem:** Nadmiarowa abstrakcja - klasa z jedną metodą
**Priorytet:** Średni

**Kod do zmiany:**

```python
class UserManager:
    def create_user_with_validation(self, username, email):
        if not username or not email:
            raise ValueError("Username and email required")
        return User(username, email)
```
````

**Proponowany kod:**

```python
def create_user(username, email):
    if not username or not email:
        raise ValueError("Username and email required")
    return User(username, email)
```

**Uzasadnienie:** Eliminacja niepotrzebnej klasy zmniejsza złożoność bez utraty funkcjonalności.

**Ryzyko:** Niskie - brak zależności zewnętrznych.

**Testy do dodania:** Test funkcji create_user z różnymi parametrami.

## Procedury Bezpieczeństwa

### 1. Przed rozpoczęciem refaktoryzacji:

```bash
# Pełny backup projektu
cp -r ./projekt_backup ./projekt_backup_$(date +%Y%m%d_%H%M%S)

# Sprawdzenie aktualnych testów
python -m pytest tests/ -v

# Utworzenie dedykowanego brancha
git checkout -b refactor-over-engineering-$(date +%Y%m%d)
git push --set-upstream origin refactor-over-engineering-$(date +%Y%m%d)
```

### 2. Strategia testowania:

```bash
# Uruchomienie testów przed zmianami
python -m pytest tests/ --cov=./src --cov-report=html

# Testy jednostkowe dla nowej funkcjonalności
python -m pytest tests/test_refactored_module.py -v

# Testy integracyjne po zmianach
python -m pytest tests/integration/ -v

# Testy regresyjne
python -m pytest tests/ --lf  # tylko ostatnio failed
```

### 3. Procedura wdrożenia:

```bash
# Małe kroki z weryfikacją
git add [specific_files]
git commit -m "refactor: [opis_zmiany] - etap 1/N"

# Weryfikacja po każdym kroku
python -m pytest tests/
python -m flake8 ./src

# Code review workflow
git push origin refactor-over-engineering-$(date +%Y%m%d)
# Utwórz Pull Request w GitHub/GitLab
```

### 4. Procedury awaryjne:

```bash
# Powrót do poprzedniego stanu
git reset --hard HEAD~1

# Przywrócenie z tagu backup
git checkout backup-before-refactor

# Przywrócenie konkretnego pliku
git checkout HEAD~1 -- path/to/file.py
```

## Metryki Sukcesu

### Metryki ilościowe:

```bash
# Przed refaktoryzacją
radon cc ./src --total-average > metrics_before.txt
vulture ./src --min-confidence 80 > dead_code_before.txt
wc -l ./src/**/*.py > loc_before.txt

# Po refaktoryzacji
radon cc ./src --total-average > metrics_after.txt
vulture ./src --min-confidence 80 > dead_code_after.txt
wc -l ./src/**/*.py > loc_after.txt
```

### Cele do osiągnięcia:

- **Redukcja złożoności cyklomatycznej:** o 15-25%
- **Zmniejszenie LOC:** o 10-20%
- **Poprawa pokrycia testami:** do 80-90%
- **Redukcja czasu buildowania:** o 5-15%
- **Eliminacja dead code:** o 90-100%

### Monitoring postępu:

```bash
# Skrypt do monitorowania metryk
#!/bin/bash
echo "=== METRYKI REFAKTORYZACJI ==="
echo "Złożoność cyklomatyczna:"
radon cc ./src --total-average

echo "Nieużywany kod:"
vulture ./src --min-confidence 80 | wc -l

echo "Pokrycie testami:"
python -m pytest tests/ --cov=./src --cov-report=term-missing | grep "TOTAL"

echo "Czas buildowania:"
time python -m pytest tests/
```

## Dodatkowe Wytyczne

### Priorytetyzacja zmian:

1. **Wysokie ryzyko bezpieczeństwa** - natychmiast
2. **Krytyczne problemy wydajności** - w pierwszej kolejności
3. **Duplikacja kodu** - średni priorytet
4. **Kosmetyczne usprawnienia** - niski priorytet

### Zasady refaktoryzacji:

- **Zachowaj istniejące API** jeśli jest używane zewnętrznie
- **Dokumentuj każdą znaczącą zmianę** w CHANGELOG.md
- **Sprawdź wydajność** po refaktoryzacji
- **Jeden problem = jeden commit**
- **Testy muszą przechodzić** po każdej zmianie

### Checklist przed zakończeniem:

- [ ] Wszystkie testy przechodzą
- [ ] Metryki kodu uległy poprawie
- [ ] Dokumentacja została zaktualizowana
- [ ] Code review został przeprowadzony
- [ ] Performance tests pokazują poprawę lub brak regresu

---

**Rozpocznij analizę od stworzenia mapy projektu, a następnie systematycznie przejdź przez każdą fazę.**
