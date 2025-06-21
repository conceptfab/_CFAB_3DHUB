### PEŁNA I KOMPLETNA WERSJA: AUDYT KODU: METODOLOGIA INŻYNIERII WSTECZNEJ (Wersja 2.2)

Ta wersja dokumentu została wzbogacona o dodatkowe etapy i techniki, aby zwiększyć jej skuteczność, precyzję oraz zapewnić długofalowe korzyści z przeprowadzonego audytu. Wersja 2.2 wprowadza rygorystyczną zasadę progresywnego dokumentowania poprawek, a także dodaje dedykowany etap analizy wizualnej architektury kodu, aby uzyskać pełny obraz systemu.
🚀 ETAP 0: USTALENIE CELÓW BIZNESOWYCH I STRATEGII
Główna koncepcja: Każdy techniczny wysiłek na dużą skalę musi mieć jasne uzasadnienie biznesowe. Ten etap zapewnia, że audyt jest ukierunkowany na rozwiązanie realnych problemów, a nie tylko na techniczne "sprzątanie".
Cel: Zdefiniowanie mierzalnych celów audytu i zapewnienie poparcia interesariuszy.
Zadania:
Zorganizuj spotkanie "kick-off" z kluczowymi interesariuszami (Product Owner, managerowie, architekci, liderzy techniczni).
Odpowiedz na pytanie "DLACZEGO?": Wspólnie zdefiniujcie, co audyt ma osiągnąć. Czy celem jest:
Redukcja kosztów utrzymania?
Przyspieszenie dostarczania nowych funkcjonalności (Time to Market)?
Zwiększenie stabilności i redukcja liczby krytycznych błędów?
Poprawa wydajności aplikacji?
Ułatwienie wdrożenia nowych członków zespołu?
Ustal mierzalne wskaźniki sukcesu (KPI): np. "skrócenie czasu ładowania głównego okna o 20%", "zmniejszenie liczby błędów krytycznych o 50% w ciągu 3 miesięcy".
Format dokumentacji:
Generated markdown

## CELE BIZNESOWE AUDYTU

**Główny cel:** [np. Zwiększenie stabilności aplikacji i przyspieszenie rozwoju]
**Interesariusze:** [Lista osób/ról]
**Mierzalne wskaźniki sukcesu (KPI):**

- **KPI 1:** [np. Redukcja błędów typu `Crash` o 40% w Q3]
- **KPI 2:** [np. Czas wdrożenia nowej prostej funkcji skrócony z 5 dni do 2]
  **Uzasadnienie biznesowe:** [Krótki opis, dlaczego ten wysiłek jest ważny dla firmy]
  Use code with caution.
  Markdown
  📖 ZAŁOŻENIA METODOLOGII
  Główna koncepcja: Audyt rozpoczynamy od punktów wejścia aplikacji (interfejsu użytkownika, endpointów API, zadań CRON) i poruszamy się "wstecz" - analizujemy tylko rzeczywiście używane komponenty, funkcje i zależności. To pozwala na skuteczne wykrycie martwego kodu i nadmiarowych funkcjonalności.
  Zalety podejścia:
  Eliminacja analizy nieużywanego kodu.
  Fokus na rzeczywistych ścieżkach wykonania.
  Naturalne wykrycie martwego kodu.
  Efektywność czasowa audytu.
  🎯 ETAP 1: IDENTYFIKACJA PUNKTÓW WEJŚCIA I OTOCZENIA
  1.1 Lokalizacja głównego pliku i konfiguracji
  Cel: Znalezienie wszystkich punktów startowych aplikacji oraz zrozumienie jej otoczenia konfiguracyjnego.
  Zadania:
  Zidentyfikuj główne pliki startowe aplikacji (np. main.py, app.py, **main**.py).
  Zidentyfikuj interfejsy (np. GUI, API, CLI).
  Określ kluczowe frameworki (np. PyQt, FastAPI, Click).
  Zidentyfikuj i przeanalizuj pliki konfiguracyjne, zmienne środowiskowe i systemy feature flags.
  1.2 Mapa Interfejsu Użytkownika (dla aplikacji GUI)
  Stwórz wizualną mapę głównego okna:
  Generated markdown

## MAPA GŁÓWNEGO INTERFEJSU

GŁÓWNE OKNO
├── Menu górne
│ ├── Plik → [funkcje związane z plikami]
│ └── Pomoc → [funkcje pomocy]
├── Panel boczny
│ ├── Drzewo plików → [funkcje nawigacji]
└── Obszar główny
├── Edytor → [funkcje edycji]
Use code with caution.
Markdown
🔍 ETAP 2: ANALIZA ŚCIEŻEK WYKONANIA
2.1 Metodologia "Follow the Code"
Zasada: Śledź każdą funkcjonalność od interfejsu (lub innego punktu wejścia) do najgłębszej implementacji.
Proces:
Identyfikacja akcji użytkownika / wywołania endpointu - Każdy przycisk, menu, żądanie HTTP.
Śledzenie handlera - Funkcja obsługująca zdarzenie.
Analiza łańcucha wywołań - Wszystkie funkcje w ścieżce wykonania.
Dokumentacja zależności - Jakie moduły/pliki są rzeczywiście używane.
🗺️ ETAP 3: ANALIZA ARCHITEKTONICZNA I WIZUALIZACJA ZALEŻNOŚCI
Cel: Stworzenie wizualnej mapy zależności kodu, aby zrozumieć ogólną architekturę, zidentyfikować kluczowe komponenty oraz potencjalne problemy strukturalne.
3.1 Generowanie Mapy Zależności
Zadanie: Użyj zautomatyzowanego narzędzia do wygenerowania grafu zależności importów.
Narzędzia (dla Python): pydeps, pyan.
Przykład wykonania:
Generated bash

# Instalacja narzędzia

pip install pydeps

# Generowanie grafu dla folderu 'src' i zapisanie go do pliku SVG

pydeps --show-deps src --output audit_results/dependency_map.svg
Use code with caution.
Bash
Wynik: Plik dependency_map.svg dodany do dokumentacji audytu.
3.2 Analiza Wizualnej Mapy Kodu
Zadanie: Przeanalizuj wygenerowany graf pod kątem typowych wzorców i antywzorców architektonicznych.
Szukaj:
📍 Huby ("God Objects"): Moduły z nadmierną liczbą połączeń. Zmiany w nich niosą wysokie ryzyko.
🏝️ Wyspy (Islands): Izolowane moduły bez połączeń. Prawie pewny martwy kod.
🔗 Zależności cykliczne: Poważny problem architektoniczny (moduł A → B → A).
Wnioski: Użyj tych informacji do weryfikacji oceny ryzyka w kolejnych etapach oraz do identyfikacji poprawek architektonicznych.
🕵️ ETAP 4: IDENTYFIKACJA I PROGRESYWNA DOKUMENTACJA POPRAWEK
Główna koncepcja: W momencie identyfikacji problemu (martwy kod, bug, duplikat, problem architektoniczny), natychmiast dokumentuj go w plikach corrections.md i code_patch.md. Nie czekaj do końca analizy. To zapobiega utracie postępów i tworzy listę zadań na bieżąco.
[WAŻNE] 4.1 Template identyfikacji poprawki w corrections.md
Gdy tylko zidentyfikujesz problem, dodaj nowy wpis do pliku corrections.md.
Generated markdown

## Etap [Numer]: [Nazwa poprawki]

**Identyfikator:** REFACT-[YYYY-MM-DD]-[Numer_kolejny]
**Opis:** [Szczegółowy opis problemu, np. "Funkcja `calculate_old_tax` nie jest nigdzie wywoływana"]
**Pliki do modyfikacji:** [`path/to/file.py`]
**Patch ID:** REFACT-[YYYY-MM-DD]-[Numer_kolejny] (patrz `code_patch.md`)
**Ryzyko:** [🚨 WYSOKIE / ⚠️ ŚREDNIE / ✅ NISKIE]
**Status:** Oczekująca
Use code with caution.
Markdown
[WAŻNE] 4.2 Template definicji kodu w code_patch.md
Równocześnie z utworzeniem wpisu w corrections.md, zdefiniuj konkretną zmianę w kodzie w pliku code_patch.md.
Generated markdown

## PATCH: REFACT-[YYYY-MM-DD]-[Numer_kolejny]

### Plik: `path/to/file.py`

### Linie: [np. 45-58]

### Typ: USUŃ / MODYFIKUJ / DODAJ

**Kod PRZED zmianą:**

```python
# stary, problematyczny kod
def calculate_old_tax(amount):
    # ...
    return complex_calculation
```

Kod PO zmianie:

```python
# W przypadku usunięcia, ten blok pozostaje pusty lub zawiera komentarz
# KOD USUNIĘTY
```

Uzasadnienie: [np. "Funkcja jest martwym kodem. Potwierdzono brak odwołań w przeanalizowanych ścieżkach wykonania oraz na mapie zależności."]

### **📊 ETAP 5: KLASYFIKACJA PRIORYTETÓW I OCENA RYZYKA**

**Cel:** Po zgromadzeniu listy poprawek w `corrections.md`, przeprowadź ich priorytetyzację, uwzględniając analizę architektoniczną z Etapu 3.

**5.1 System priorytetów**

- **⚫⚫⚫⚫ KRYTYCZNY:** Błędy blokujące, luki bezpieczeństwa, problemy architektoniczne (np. cykle).
- **🔴🔴🔴 WYSOKI:** Duży martwy kod (>1000 linii), krytyczne duplikaty.
- **🟡🟡 ŚREDNI:** Mniejszy martwy kod (100-1000 linii), duplikaty pomocnicze.
- **🟢 NISKI:** Drobny martwy kod (<100 linii), poprawki kosmetyczne.

**5.2 Ocena ryzyka refaktoryzacji** (zweryfikowana przez mapę zależności)

- **🚨 WYSOKIE RYZYKO:** Modyfikacje w "hubach", zmiany w funkcjach używanych w wielu miejscach.
- **⚠️ ŚREDNIE RYZYKO:** Konsolidacja duplikatów, modyfikacje funkcji pomocniczych.
- **✅ NISKIE RYZYKO:** Usunięcie martwego kodu ("wysp"), nieużywanych importów, komentarzy.

**5.3 Matrix priorytet-ryzyko**
Użyj macierzy, aby zdecydować, co robić najpierw. Zawsze zaczynaj od zadań o najwyższym priorytecie i najniższym ryzyku.

```markdown
## MATRIX PRIORYTET-RYZYKO

| Priorytet / Ryzyko | 🚨 Wysokie       | ⚠️ Średnie        | ✅ Niskie            |
| ------------------ | ---------------- | ----------------- | -------------------- |
| ⚫⚫⚫⚫ Krytyczny | Planuj ostrożnie | Wykonaj z testami | Wykonaj natychmiast  |
| 🔴🔴🔴 Wysoki      | Planuj ostrożnie | Wykonaj z testami | Wykonaj w kolejności |
| 🟡🟡 Średni        | Po krytycznych   | Rutynowo          | Grupuj z innymi      |
| 🟢 Niski           | Ostatecznie      | Grupuj            | Wykonuj zbiorowo     |
```

🛠️ ETAP 6: MASTER PLAN REFAKTORYZACJI
Cel: Stworzenie głównego planu wykonawczego opartego na pliku corrections.md i code_patch.md. Ten etap polega na uporządkowaniu już udokumentowanych poprawek.
6.1 Hierarchia poprawek
Podziel zadania z corrections.md na fazy:
Faza I - Bezpieczne czyszczenie (Ryzyko: ✅ Niskie): Wszystkie poprawki o niskim ryzyku.
Faza II - Refaktoryzacja główna (Ryzyko: ⚠️ Średnie): Poprawki o średnim ryzyku.
Faza III - Optymalizacje zaawansowane (Ryzyko: 🚨 Wysokie): Poprawki o wysokim ryzyku.
6.2 Główny plan wykonawczy (refactoring_master_plan.md)

```markdown
## MASTER PLAN REFAKTORYZACJI

### Faza I: Bezpieczne Czyszczenie

- **Cel:** Szybkie usunięcie długu technicznego bez ryzyka regresji.
- **Pakiety do wykonania (wg ID z `corrections.md`):**
  - REFACT-XXX-001
  - REFACT-XXX-003
  - ...

### Faza II: Główna Refaktoryzacja

- **Cel:** Konsolidacja kodu, poprawa struktury.
- **Pakiety do wykonania:**
  - REFACT-XXX-002
  - ...
```

📁 STRUKTURA PLIKÓW WYNIKOWYCH AUDYTU
corrections.md [PLIK KLUCZOWY]
Cel: Główna, dynamicznie aktualizowana lista wszystkich zidentyfikowanych poprawek (zadań do wykonania). Służy jako centralny rejestr pracy dla autonomicznego agenta AI.
Struktura: Każdy wpis zawiera ID, opis, pliki do modyfikacji, ryzyko i odniesienie do Patch ID w code_patch.md.
code_patch.md [PLIK KLUCZOWY]
Cel: Techniczny "magazyn" fragmentów kodu. Zawiera wszystkie konkretne zmiany "przed" i "po" dla każdej poprawki z corrections.md.
Struktura: Każdy wpis jest oznaczony unikalnym PATCH ID, co pozwala na łatwe odnalezienie go z poziomu corrections.md.
Inne pliki analityczne:
00_business_goals.md: Cele biznesowe i KPI.
01_entry_point_analysis.md: Analiza punktu wejścia i mapy UI.
03_architectural_analysis.md: Mapa zależności dependency_map.svg i wnioski z jej analizy.
05_priority_risk_matrix.md: Macierz priorytetów i ryzyka.
06_refactoring_master_plan.md: Plan wykonawczy podzielony na fazy.
🎯 KLUCZOWE ZASADY METODOLOGII

1. [NAJWAŻNIEJSZE] DOKUMENTUJ NATYCHMIAST, DZIAŁAJ PÓŹNIEJ: Gdy tylko znajdziesz problem, natychmiast utwórz wpisy w corrections.md i code_patch.md. Nie odkładaj tego.
2. Od biznesu do kodu - zacznij od zrozumienia celu biznesowego.
3. Od użytkownika do implementacji - zawsze śledź ścieżkę od interfejsu.
4. Małe pakiety poprawek - łatwiejsze testowanie i rollback.
5. Testowanie na każdym etapie - każda poprawka to pełen cykl testów.
6. Weryfikacja przed usunięciem - nigdy nie usuwaj bez 100% pewności.
7. Dokumentacja decyzji - każda poprawka ma uzasadnienie w code_patch.md.
8. Kontrola zależności - sprawdzaj wpływ na inne moduły.

## 1. Analiza struktury projektu

### 1.1 Struktura katalogów

```
src/
├── logic/           # Logika biznesowa
├── models/          # Modele danych
├── services/        # Serwisy
├── ui/             # Interfejs użytkownika
└── utils/          # Narzędzia pomocnicze
```

### 1.2 Zależności

- Python 3.8+
- PyQt6
- Pillow
- pytest

## 2. Analiza kodu

### 2.1 Logika biznesowa

- Parowanie plików
- Skanowanie katalogów
- Zarządzanie metadanymi

### 2.2 Interfejs użytkownika

- Galeria
- Drzewo katalogów
- Panel filtrów

### 2.3 Serwisy

- Skanowanie
- Operacje na plikach
- Cache miniaturek

## 3. Rekomendacje

### 3.1 Optymalizacje

- Cache miniaturek
- Asynchroniczne operacje
- Thread safety

### 3.2 Refaktoryzacja

- Podział na moduły
- Wzorce projektowe
- Testy jednostkowe

```

</rewritten_file>
```
