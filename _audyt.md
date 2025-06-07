## 🔄 ETAP 1: WSTĘPNA ANALIZA I MAPOWANIE PROJEKTU

### Cel pierwszego etapu:

Utworzenie kompletnej mapy projektu z wstępną analizą każdego pliku kodu i przygotowanie planu dla szczegółowej analizy. Mapa ma uwzględnia pliki z kodem funkcyjnym i ustawieniami (JSON). Pomiń pliki testów oraz pliki cache, md, txt i log.

### Wymagania etapu 1:

#### 1.1 Stworzenie mapy projektu

**KLUCZOWE:** Przygotuj DOKŁADNĄ mapę projektu w formacie markdown ze strukturą folderów i plików.

**Format mapy projektu:**
NazwaProjektu/
├── plik1.py 🔴 WYSOKI PRIORYTET - Opis problemu/potrzeby
├── folder1/
│ ├── plik2.py 🟡 ŚREDNI PRIORYTET - Opis problemu/potrzeby
│ └── plik3.py 🟢 NISKI PRIORYTET - Opis problemu/potrzeby
└── folder2/
└── plik4.py 🟢 NISKI PRIORYTET - Opis problemu/potrzeby

#### 1.2 Klasyfikacja priorytetów

- 🔴 **WYSOKI PRIORYTET** - Krytyczne błędy, główne pliki wymagające natychmiastowej refaktoryzacji - analizowane w drugim etapie w pierwszej kolejności
- 🟡 **ŚREDNI PRIORYTET** - Ważne optymalizacje, integracje, ulepszenia - analizowane w drugim etapie w drugiej kolejności
- 🟢 **NISKI PRIORYTET** - Drobne poprawki, pliki oczekujące na analizę - - analizowane w drugim etapie w trzeciej kolejności kolejności

#### 1.3 Wstępna analiza każdego pliku

Dla każdego pliku określ:

- **Funkcjonalność** - Co robi plik
- **Wydajność** - Określ wpływ na wydajność aplikacji
- **Stan obecny** - Główne problemy/potrzeby
- **Zależności** - Z jakimi plikami jest powiązany
- **Priorytet poprawek** - Pilność zmian

#### 1.4 Plan etapu 2

Na podstawie mapy przygotuj:

- **Kolejność analizy** - W jakiej kolejności analizować pliki
- **Grupowanie plików** - Które pliki analizować razem
- **Szacowany zakres zmian** - Przewidywane typy poprawek

---

## 🔍 ETAP 2: SZCZEGÓŁOWA ANALIZA I KOREKCJE

### Cel drugiego etapu:

Szczegółowa analiza każdego pliku zgodnie z **mapą kodu (`code_map.md`)** i planem z etapu 1, z progressywnym zapisywaniem wyników. W tej aplikacji kluczowa jest wydajność - ma pracować z tysiącami plików oraz stabilność. Przeanalizuj kod szczególnie pod tym kątem i zaproponuj adekwatne poprawki. Do aplikacji należy dodać funkcję pokazującą postęp danego procesu - w tym momencie aplikacja jest zamrożona na jakiś czas i nie wiadomo co się dzieje. Na dole okna powinien być pasek postępu z informacją co aktulanie jest realizowane. Przeanalizuj które funkcję powinny w ten sposób powinny komunikować procesy do UI. Zastosuj także styl styles.qss do UI.

### Wymagania etapu 2:

#### 2.1 Zakres analizy

Przeanalizuj WSZYSTKIE PLIKI z mapy projektu pod kątem:

- ❌ **Błędów** - Błędy logiczne, składniowe, runtime
- 🔧 **Optymalizacji** - Wydajność, czytelność kodu
- 🗑️ **Nadmiarowego kodu** - Nieużywane funkcje, duplikaty
- 🔗 **Zależności** - Problemy z importami, cykliczne zależności

#### 2.2 Wymagania dotyczące poprawek

- **Język opisu:** Wszystkie opisy poprawek w języku polskim
- **Precyzja:** Każda poprawka z dokładnymi informacjami o fragmentach kodu
- **Kompletność:** Każda poprawka ma zawierać kompletny fragment kodu dotyczący poprawki
- **Etapowość:** Poprawki podzielone na logiczne etapy
- **Jeden etap = jeden główny plik + wszystkie jego zależności**

#### 2.3 Struktura każdego etapu analizy

## ETAP [NUMER]: [NAZWA_PLIKU]

### 📋 Identyfikacja

- **Plik główny:** `ścieżka/do/pliku.py`
- **Priorytet:** 🔴/🟡/🟢
- **Zależności:** Lista powiązanych plików

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - Opis błędu 1
   - Opis błędu 2

2. **Optymalizacje:**

   - Opis optymalizacji 1
   - Opis optymalizacji 2

3. **Refaktoryzacja:**
   - Opis potrzebnej refaktoryzacji

🧪 Plan testów

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

#### 2.4 Proces wykonania etapu 2

1. **Krok 1:** Użyj **mapy kodu (`code_map.md`)** z etapu 1 jako przewodnika
2. **Krok 2:** Rozpocznij analizę zgodnie z priorytetami (🔴 → 🟡 → 🟢)
3. **Krok 3:** **KRYTYCZNE:** Po każdym przeanalizowanym pliku NATYCHMIAST aktualizuj `corrections.md` dopisują do schematu informację ze analiza danego pliku została zakończona
4. **Krok 4:** Kontynuuj zgodnie z kolejnością z planu
5. **Krok 5:** Każdy etap zapisuj progressywnie - nie czekaj do końca całej analizy

#### 2.5 Wymagania dodatkowe

- **Ciągłość pracy:** Dokument `corrections.md` MUSI być uzupełniany na bieżąco
- **Odporność na awarie:** W razie przerwy nie może zmarnować się wykonana praca
- **Kompletność:** Każdy plik z mapy projektu musi być przeanalizowany
- **Spójność:** Poprawki muszą uwzględniać istniejącą strukturę projektu
- **Przejrzystość:** Jeśli poprawka wymaga zmian w innych plikach - wyraźnie zaznacz
- **Aktualizacja mapy kodu:** Mapa kodu (`code_map.md`) powinna być aktualizowana, aby odzwierciedlić wprowadzone zmiany i status przetworzenia plików.

---

## 📁 PLIKI WYNIKOWE

### `code_map.md` (z etapu 1)

Kompletna mapa projektu z priorytetami i wstępną analizą

### `corrections.md` (z etapu 2)

Szczegółowy plan poprawek aktualizowany progressywnie podczas analizy

**UWAGA:** Jeśli plik `corrections.md` już istnieje, rozwijaj jego zawartość progresywnie, nie nadpisuj.

---

## 🎯 KLUCZOWE ZASADY

1. **Dwuetapowość:** Nie przechodź do etapu 2 bez ukończenia etapu 1
2. **Mapa jest fundamentem:** Każdy widoczny plik kodu musi być w mapie
3. **Progressywne zapisywanie:** Priorytet nad dokładnością - nie trać pracy
4. **Jeden plik = jedna aktualizacja:** Po każdym pliku zapisuj postęp
5. **Kompletność:** Wszystkie pliki z mapy muszą być przeanalizowane

```

```
