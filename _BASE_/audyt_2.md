### **ETAP 1: WSTĘPNA ANALIZA I MAPOWANIE PROJEKTU**

Przeanalizuj WSZYSTKIE pliki kodu źródłowego.

Dla każdego pliku określ:

* **Funkcjonalność** - Co robi plik

* **Wydajność** - Określ wpływ na wydajność aplikacji

* **Stan obecny** - Główne problemy/potrzeby

* **Zależności** - Z jakimi plikami jest powiązany

* **Poziom logowania** - Weryfikacja czy kod nie spamuje logami

* **Potrzeba refaktoryzacji** - określ priorytet refaktoryzacji

* **Priorytet poprawek** - Pilność zmian

Na podstawie analizy, utwórz jeden plik code\_map.md. Musi on zawierać kompletną mapę projektu w formacie Markdown, z priorytetami (⚫⚫⚫⚫, 🔴🔴🔴, 🟡🟡, 🟢) i krótkim opisem problemu/potrzeby dla każdego pliku.

W pliku code\_map.md zamieść również plan informację o: kolejność analizy, grupowanie plików i szacowany zakres zmian.

Wygeneruj zawartość pliku code\_map.md

### ETAP 2: SZCZEGÓŁOWA ANALIZA I KOREKCJE

WAŻNE: Pracuj iteracyjnie. Po zakończeniu analizy każdego pojedynczego pliku, natychmiast generuj zaktualizowaną zawartość plików wynikowych.

Korzystaj z code\_map.md jako przewodnika. Rozpocznij analizę od plików z najwyższym priorytetem (⚫⚫⚫⚫ → 🔴🔴🔴 → 🟡🟡 → 🟢).

Zakres analizy

Przeanalizuj WSZYSTKIE PLIKI z mapy projektu pod kątem:

* ❌ **Błędów** - Błędy logiczne, składniowe, runtime

* ❌ **Nadmiarowe logowanie** - przeanalizuj czy szczegółowe logowanie jest potrzebne, jeśli to potrzebne podziel logowanie na poziomy INFO, DEBUG etc.

* 🔧 **Optymalizacji** - Wydajność, czytelność kodu

* 🗑️ **Nadmiarowego kodu** - Nieużywane funkcje, duplikaty

* 🔗 **Zależności** - Problemy z importami, cykliczne zależności



#### Wymagania dotyczące poprawek

* **Język opisu:** Wszystkie opisy poprawek w języku polskim

* **Precyzja:** Każda poprawka z dokładnymi informacjami o fragmentach kodu w pliku patch\_code.md

* Bezpieczeństwo: zrób kopię bezpieczeństwa każdego pliku na którym pracujesz!

* **Ostrożność i dokładność** - poprawki nie mogą ograniczyć funkcjonalności i stabilności aplikacji - analizuj kopie bezpieczeństwa by weryfikować poprawność zmian

* **Kompletność:** Każda poprawka ma zawierać kompletny fragment kodu dotyczący poprawki

* **Etapowość:** Poprawki podzielone na logiczne etapy

* **Jeden etap = jeden główny plik + wszystkie jego zależności + automatyczne testy**





#### Struktura każdego etapu analizy

## ETAP \[NUMER]: \[NAZWA\_PLIKU]

### 📋 Identyfikacja

* **Plik główny:** `ścieżka/do/pliku.py`

* **Priorytet:** ⚫⚫⚫⚫/🔴🔴🔴/🟡🟡/🟢

* **Zależności:** Lista powiązanych plików

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   * Opis błędu 1

   * Opis błędu 2

2. **Optymalizacje:**

   * Opis optymalizacji 1

   * Opis optymalizacji 2

3. **Refaktoryzacja:**

   * Opis potrzebnej refaktoryzacji

4. **Logowanie:**

   * Weryfikacja logowania, podzał logowania na INFO, DEBUG etc.

🧪 Plan testów automatycznych - każdy etpa poprawek musi zostać zakończony testami. Tylko pozytywne wyniki testów umożliwiają realizację kolejnych etapów

Test funkcjonalności podstawowej:

Opis testu 1
Opis testu 2

Test integracji:

Opis testu integracji

Test wydajności:

Opis testu wydajności

📊 Status tracking

Kod zaimplementowany
Testy podstawowe przeprowadzone
Testy integracji przeprowadzone
Dokumentacja zaktualizowana
Gotowe do wdrożenia



Podczas analizy, skup się szczególnie na:
Optymalizacji wydajności: Szukaj wąskich gardeł, niewydajnych pętli, złego zarządzania zasobami (np. nie zamykanie plików). Aplikacja musi obsłużyć tysiące plików.
Refaktoryzacji logowania: Przeanalizuj istniejące logi. Zidentyfikuj nadmiarowe komunikaty. Zaproponuj podział logów na poziomy (np. INFO dla kluczowych operacji, DEBUG dla szczegółowych informacji diagnostycznych). Logowanie w trybie DEBUG powinno być domyślnie wyłączone i możliwe do aktywacji np. za pomocą flagi lub zmiennej środowiskowej.
Eliminacji nadmiarowego kodu: Znajdź i oznacz nieużywane funkcje, zmienne, importy oraz zduplikowane fragmenty kodu.
Podziale dużych plików: Jeśli plik jest zbyt duży lub zawiera wiele niezwiązanych ze sobą funkcji, zaproponuj jego logiczny podział na mniejsze moduły.

Efektem prac mają być pliki correction\_*PRIORYTER\_POPRAWEK*.md, proponowane poprawki zapisz w odpowiednich plikach patch\_code\_*NAZWA\_PLIKU*.md do których ma być czytelne odwołanie w odpowiednich plikach correction\_\*.md Wszystkie pliki umieść w folderze *AUDYT*



Wszystkie proponowane fragmenty kodu do poprawek umieszczaj w osobnym pliku patch\_code.md. W pliku corrections.md odwołuj się do odpowiednich fragmentów z patch\_code.md.
Plan poprawek musi być etapowy: Każda poprawka (np. optymalizacja jednej funkcji) to osobny krok, który kończy się testem. To krytyczne dla stabilności wdrożenia. Zaznacz to wyraźnie w planie.
Po przeanalizowaniu każdego pliku, zaktualizuj code\_map.md, aby odzwierciedlić jego status (np. dodając znacznik ✅ \[PRZEANALIZOWANO]).



Język: Cała komunikacja oraz zawartość generowanych plików musi być w języku polskim.
Rozpoczynamy. Czekam na Twój pierwszy wynik: zawartość pliku code\_map.md.

