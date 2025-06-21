📋 AUDYT I REFAKTORYZACJA PROJEKTU
🎯 CEL
Kompleksowa analiza, optymalizacja i uproszczenie kodu aplikacji naciskiem na poprawę jakości, wydajności i bezpieczeństwa, przy jednoczesnej eliminacji over-engineeringu i zbędnej złożoności.
✨ KLUCZOWE ZASADY PROCESU
Iteracja: Pracuj w małych, kontrolowanych krokach (jeden moduł/plik na raz).
Testy są Królem: Żadna zmiana nie trafia do bazy kodu bez automatycznych testów. Testy piszemy przed lub w trakcie refaktoryzacji, nie po fakcie.
Prostota ponad wszystko (KISS & YAGNI): Zawsze wybieraj najprostsze działające rozwiązanie. Nie implementuj funkcjonalności na zapas ("You Ain't Gonna Need It").
Bezpieczeństwo od początku: Aktywnie szukaj i eliminuj potencjalne luki bezpieczeństwa.
Git jako siatka bezpieczeństwa: Cała praca odbywa się na osobnych gałęziach (branches). main/develop jest aktualizowany tylko przez Pull Request po pomyślnej weryfikacji.
📊 ETAP 1: WSTĘPNA ANALIZA I MAPOWANIE PROJEKTU
🛠️ ZALECANE NARZĘDZIA
JAKOŚĆ I STYL KODU:
ruff - Niezwykle szybki linter i formater, który zastępuje flake8, isort, autoflake i wiele wtyczek pylint. Rekomendowany jako narzędzie pierwszego wyboru.
black - Automatyczne, bezkompromisowe formatowanie kodu.
mypy - Statyczna analiza typów.
ANALIZA BEZPIECZEŃSTWA:
bandit - Skaner w poszukiwaniu typowych luk bezpieczeństwa w kodzie Python.
ANALIZA ZŁOŻONOŚCI I "MARTWEGO KODU":
radon - Analiza złożoności cyklomatycznej.
vulture - Wykrywanie nieużywanego kodu (dead code).
ANALIZA WYDAJNOŚCI:
cProfile / py-spy - Profilowanie czasu wykonania i identyfikacja "wąskich gardeł".
memory_profiler - Analiza zużycia pamięci.
AUTOMATYZACJA:
pre-commit hooks - Automatyczne uruchamianie narzędzi (np. ruff, black, bandit) przed każdym commitem.
🚀 REKOMENDACJA: Skonfiguruj pre-commit z ruff i black. Następnie uruchom bandit, vulture i radon na całym projekcie, aby uzyskać obiektywną ocenę stanu kodu przed rozpoczęciem pracy manualnej.
📋 ZAKRES WSTĘPNEJ ANALIZY
Dla KAŻDEGO pliku/modułu w projekcie zidentyfikuj:
Cel: Co robi dany moduł/plik? Jaka jest jego główna odpowiedzialność?
Zależności: Z jakimi innymi modułami współpracuje?
Stan obecny: Główne problemy (niska czytelność, złożoność, podejrzenie o niską wydajność, brak testów).
Potencjalne ryzyka: Czy przetwarza dane wejściowe? Czy wykonuje operacje na systemie plików? Czy ma luki bezpieczeństwa?
Priorytet refaktoryzacji: Jak pilna jest interwencja? (Krytyczny, Wysoki, Średni, Niski).
Proponowane działanie: Wstępny pomysł na poprawki (np. "Uprościć logikę", "Podzielić na mniejsze funkcje", "Dodać testy jednostkowe", "Zabezpieczyć parsowanie XML").
📄 WYNIK ETAPU 1
Utwórz plik audit/code_map.md, który będzie stanowił mapę drogową całego procesu. Plik powinien zawierać tabelę z wynikami powyższej analizy dla każdego pliku w projekcie.
🔍 ETAP 2: SZCZEGÓŁOWA REFAKTORYZACJA I TESTOWANIE
⚙️ WORKFLOW I KONTROLA WERSJI (GIT)
Wybierz zadanie: Z code_map.md wybierz plik/moduł o najwyższym priorytecie.
Stwórz gałąź: Utwórz nową gałąź dedykowaną dla tego zadania, np. git checkout -b refactor/user-auth-module.
Testuj przed poprawką (opcjonalnie, ale zalecane): Jeśli identyfikujesz konkretny błąd, napisz test, który go replikuje i upewnij się, że test nie przechodzi.
Implementuj zmiany: Dokonaj refaktoryzacji, optymalizacji i poprawek bezpieczeństwa. Pisz/aktualizuj testy jednostkowe i integracyjne równolegle ze zmianami w kodzie.
Weryfikuj lokalnie: Uruchom wszystkie testy (jednostkowe, integracyjne, wydajnościowe) i lintery. Upewnij się, że wszystko działa i jest zgodne ze standardami.
Dokumentuj proces: Zaktualizuj plik audit/audit_log.md, opisując wprowadzone zmiany, problemy i wyniki testów dla danego modułu.
Commit: Twórz małe, atomowe commity z jasnymi komunikatami, np. refactor(UserAuth): Upraszcza logikę walidacji hasła.
Pull Request (PR): Gdy praca na gałęzi jest zakończona, utwórz Pull Request do głównej gałęzi (develop lub main). PR musi zawierać link do odpowiedniej sekcji w audit_log.md.
Code Review: PR musi zostać sprawdzony przez innego członka zespołu (jeśli to możliwe).
Merge: Po zatwierdzeniu PR i pomyślnym przejściu testów w CI/CD, gałąź jest włączana do głównej linii rozwoju.
🎯 ZAKRES ANALIZY I POPRAWEK W KAŻDYM MODULE
Czytelność i prostota (KISS): Czy kod jest łatwy do zrozumienia? Czy funkcje są krótkie i robią jedną rzecz? Usuń niepotrzebne komentarze, popraw nazewnictwo.
Eliminacja "martwego" i zduplikowanego kodu (DRY): Użyj vulture do znalezienia nieużywanego kodu. Aktywnie szukaj powtarzających się fragmentów i wydziel je do osobnych funkcji.
Optymalizacja wydajności: Szukaj niewydajnych pętli, nadmiarowych operacji I/O, nieefektywnych struktur danych. Profiluj kod, jeśli to konieczne.
Bezpieczeństwo:
Walidacja danych wejściowych: Nigdy nie ufaj danym pochodzącym od użytkownika lub z zewnętrznych systemów.
Unikanie podatności: Sprawdź pod kątem OWASP Top 10 (np. SQL Injection, XSS, niebezpieczna deserializacja). Użyj bandit.
Zarządzanie sekretami: Upewnij się, że hasła, klucze API itp. nie są zapisane w kodzie.
Logowanie: Logi muszą być użyteczne, a nie "hałaśliwe".
INFO: Kluczowe zdarzenia w aplikacji (np. "Użytkownik X zalogowany").
DEBUG: Szczegółowe informacje do diagnostyki, domyślnie wyłączone w środowisku produkcyjnym.
WARNING/ERROR/CRITICAL: Problemy wymagające uwagi.
Obsługa błędów: Czy błędy są poprawnie przechwytywane i obsługiwane? Czy użytkownik dostaje zrozumiały komunikat?
🧪 KRYTYCZNY WYMÓG: AUTOMATYCZNE TESTY
BRAK TESTÓW = BRAK MERGE'A. Każda zmiana musi być poparta dowodem w postaci działających testów.
Testy jednostkowe (pytest): Weryfikują pojedyncze funkcje/klasy w izolacji. Pokrycie kodu dla modyfikowanych i nowych fragmentów powinno dążyć do > 85%.
Testy integracyjne: Sprawdzają, czy moduły poprawnie ze sobą współpracują po zmianach.
Testy wydajności (pytest-benchmark): Mierzą, czy refaktoryzacja nie spowodowała nieakceptowalnego spadku wydajności.
📝 DOKUMENTACJA PROCESU AUDYTU
Cały proces jest dokumentowany w jednym, centralnym pliku, aktualizowanym progresywnie.
Lokalizacja pliku: audit/audit_log.md
STRUKTURA WPISU DLA KAŻDEGO MODUŁU
Generated markdown

---

## ETAP [NUMER]: Refaktoryzacja modułu [NAZWA_MODUŁU]

- **Plik(i):** `sciezka/do/pliku.py`
- **Gałąź Git:** `refactor/nazwa-modulu`
- **Priorytet:** Wysoki
- **Status:** [ ] Oczekuje / [ ] W trakcie / [x] Ukończono / [ ] Zablokowano

### 🔍 Identyfikowane problemy

- **Problem 1 (Złożoność):** Funkcja `process_data` ma złożoność cyklomatyczną 25, co utrudnia jej analizę i testowanie.
- **Problem 2 (Bezpieczeństwo):** Plik XML od użytkownika jest parsowany za pomocą `xml.etree.ElementTree` bez zabezpieczeń przed atakami typu "Billion Laughs".
- **Problem 3 (Wydajność):** Dane są wczytywane do pamięci linia po linii w pętli, co jest nieefektywne dla dużych plików.

### 🛠️ Wprowadzone zmiany

1.  **Refaktoryzacja `process_data`:** Funkcja została podzielona na 3 mniejsze, prywatne metody: `_validate_input`, `_parse_data` i `_generate_output`. Złożoność każdej z nich nie przekracza 8.
2.  **Zabezpieczenie parsera XML:** Zmieniono parser na `lxml` i zastosowano `XMLParser` z opcjami `resolve_entities=False` w celu ochrony przed atakami XXE.
3.  **Optymalizacja wczytywania:** Zmieniono logikę na przetwarzanie strumieniowe, co znacząco zmniejszyło zużycie pamięci.

### 🧪 Wyniki testów

- **Testy jednostkowe:** Dodano 8 nowych testów dla rozbitych funkcji. Pokrycie kodu dla modułu wzrosło z 30% do 92%. Wszystkie testy **PASS**.
- **Testy integracyjne:** Test weryfikujący cały przepływ danych przez moduł **PASS**.
- **Testy wydajności:** Czas przetwarzania pliku 1GB spadł o 40%. Zużycie pamięci maksymalne spadło o 85%.
- **Analiza statyczna:** `ruff` i `bandit` nie zgłaszają żadnych błędów.

### 📄 Fragmenty kodu (Przed i Po)

<details>
<summary>Zobacz zmiany w kodzie</summary>

**Przed refaktoryzacją (`process_data`):**

```python
# Stary, skomplikowany kod...
Use code with caution.
Markdown
Po refaktoryzacji (_parse_data):
Generated python
# Nowy, czysty i bezpieczny kod...
Use code with caution.
Python
</details>
Generated code
### 🌐 JĘZYK

Cała komunikacja oraz zawartość generowanych plików w języku polskim.

### 🚀 ROZPOCZĘCIE

**Czekam na Twój pierwszy wynik: zawartość pliku `audit/code_map.md`.**
```
