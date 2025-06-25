# 📋 AUDYT LOGIKI BIZNESOWEJ CFAB_3DHUB

> **WAŻNE! Wszystkie pliki wynikowe audytu (np. `business_logic_map.md`, `corrections.md`, `patch_code.md`, pliki z analizami i poprawkami) MUSZĄ być zapisywane wyłącznie w katalogu `AUDYT`. Tylko tam należy ich szukać!**

## 🎯 CEL

Zindetyfikuj i napraw nastepujace problemy:
- przy folderach z większą ilościa par błędnie rysowana jest galeria, kafle nachodzą na siebie, ilość kolumn nie odpowiada szerokości okna galerii
- przy folderach z większą ilością par rysowany jest na początku w galerii tylko jeden rząd kafli!!!
- po chuj jakaś virtualizacja w kodzie skoro jest wyłączona!!!!! 2025-06-25 12:59:41,781 - src.ui.gallery_manager - INFO - Gallery loaded: 0 active widgets, virtualization: False

- olbrzymim problemem jest wydajność a włąściwie jaj brak
- co to są za komunikaty?? 
2025-06-25 12:53:28,346 - src.logic.scanner_core - WARNING - CRITICAL_MEMORY: 1904MB - forcing immediate GC
2025-06-25 12:53:28,474 - src.logic.scanner_core - ERROR - [8497f3ed] CRITICAL_MEMORY: 1895MB at 207 files - system may be unstable
2025-06-25 12:53:28,475 - src.logic.scanner_core - WARNING - CRITICAL_MEMORY: 1899MB - forcing immediate GC
2025-06-25 12:53:28,597 - src.logic.scanner_core - ERROR - [8497f3ed] CRITICAL_MEMORY: 1888MB at 208 files - system may be unstable
skaner powinen zrealizowć swoje zadanie i po jego skończeniu dopiero mają być tworzone i rysowane kafle, to wyglada tak jakby wszystko było robione naraz! to jest niedopuszczalne!!! mam 128 GB RAM, ograniczenia pamięci mnie nie interesują!

### 🏛️ TRZY FILARY AUDYTU LOGIKI BIZNESOWEJ

Ten audyt opiera się na trzech kluczowych filarach, które stanowią najwyższe priorytety każdej analizy procesów biznesowych:

#### 1️⃣ **WYDAJNOŚĆ PROCESÓW** ⚡

- Optymalizacja czasu wykonania operacji biznesowych
- Redukcja zużycia pamięci przy przetwarzaniu dużych zbiorów danych
- Eliminacja wąskich gardeł w pipeline'ach przetwarzania
- Usprawnienie operacji I/O i cache'owania, unikanie timeoutów
- Minimalizacja niepotrzebnych operacji w workflow'ach

#### 2️⃣ **STABILNOŚĆ OPERACJI** 🛡️

- Niezawodność procesów biznesowych
- Proper error handling i recovery w operacjach krytycznych
- Thread safety w operacjach wielowątkowych
- Eliminacja memory leaks w długotrwałych procesach
- Przewidywalność zachowania przy różnych scenariuszach danych

#### 3️⃣ **WYELIMINOWANIE OVER-ENGINEERING** 🎯

- Uproszczenie nadmiernie skomplikowanych algorytmów
- Eliminacja niepotrzebnych abstrakcji w logice biznesowej
- Redukcja liczby warstw przetwarzania
- Konsolidacja rozproszonej logiki biznesowej
- Zastąpienie skomplikowanych wzorców prostszymi rozwiązaniami

### 🖼️ **KRYTYCZNY PROCES PREZENTACJI DANYCH W INTERFEJSIE UŻYTKOWNIKA**

**WAŻNE: Proces prezentacji danych w interfejsie użytkownika jest RÓWNIE WAŻNY jak główne procesy biznesowe!**

#### 🎯 **Dlaczego UI to Logika Biznesowa**

- **Główny interfejs użytkownika** - większość czasu użytkownik spędza w interfejsie
- **Wydajność krytyczna** - interfejs musi być responsywny nawet przy dużych zbiorach danych
- **Algorytmy biznesowe** - zarządzanie danymi, cache'owanie, filtrowanie, sortowanie
- **User Experience** - responsywność interfejsu decyduje o użyteczności aplikacji

#### 📊 **Wymagania Wydajnościowe UI**

- **Duże zbiory danych**: interfejs musi obsługiwać duże ilości danych
- **Czas ładowania**: szybkie ładowanie komponentów interfejsu
- **Płynne przewijanie**: bez lagów przy scrollowaniu
- **Responsywność UI**: brak blokowania interfejsu podczas operacji
- **Memory efficiency**: optymalne zarządzanie pamięcią dla interfejsu

#### 🔧 **Kluczowe Komponenty Logiki Prezentacji**

- **Data rendering** - renderowanie danych w interfejsie
- **Lazy loading** - ładowanie komponentów na żądanie
- **Virtual scrolling** - renderowanie tylko widocznych elementów (jeśli potrzebne)
- **Cache management** - inteligentne cache'owanie danych i komponentów
- **Filtering & sorting** - wydajne filtrowanie i sortowanie danych
- **Batch processing** - przetwarzanie wsadowe dla wydajności

### 🎨 **KRYTYCZNA ROLA KODU UI W LOGICE BIZNESOWEJ**

**🚨 SZCZEGÓLNIE WAŻNE: Audyt i poprawki w plikach odpowiedzialnych za UI i wyświetlanie elementów muszą być szczególnie precyzyjnie audytowane, poprawki muszą być bardzo dokładne, uwzględniające bardzo ważną rolę tego kodu.**

#### 🎯 **Dlaczego UI to Logika Biznesowa**

- **Bezpośredni wpływ na UX** - każdy błąd w UI natychmiast wpływa na użytkownika
- **Thread safety krytyczne** - UI framework wymaga ścisłego przestrzegania zasad thread safety
- **Memory management** - nieprawidłowe zarządzanie pamięcią w UI powoduje crashy aplikacji
- **Event handling** - błędy w obsłudze zdarzeń mogą zablokować całą aplikację
- **Performance critical** - UI musi być responsywne nawet przy dużych zbiorach danych

#### 🔧 **Szczególne Wymagania dla Audytu UI**

- **Precyzyjne analizy** - każdy widget, każdy event handler musi być przeanalizowany
- **Thread safety verification** - sprawdzenie wszystkich operacji UI w kontekście wątków
- **Memory leak detection** - szczególna uwaga na wycieki pamięci w widgetach
- **Event loop analysis** - analiza wpływu operacji na główną pętlę zdarzeń
- **Signal-slot verification** - sprawdzenie poprawności połączeń signal-slot
- **Resource cleanup** - weryfikacja prawidłowego zwalniania zasobów UI

#### 🚨 **Krytyczne Obszary UI Wymagające Szczególnej Uwagi**

- **Główne komponenty interfejsu** - główny interfejs użytkownika, krytyczny dla UX
- **Komponenty renderujące dane** - renderowanie dużych ilości danych, performance critical
- **Komponenty cache'owania** - generowanie i cache'owanie danych
- **Event handlers** - obsługa kliknięć, drag&drop, keyboard shortcuts
- **Progress indicators** - feedback dla użytkownika podczas operacji
- **Dialog boxes** - interakcje z użytkownikiem, validation

#### ✅ **Standardy Jakości dla Poprawek UI**

- **Zero regressions** - poprawki nie mogą wprowadzać nowych błędów
- **Backward compatibility** - zachowanie istniejącego API i zachowań
- **Performance preservation** - poprawki nie mogą spowolnić UI
- **Thread safety** - wszystkie operacje UI muszą być thread-safe
- **Memory efficiency** - poprawki nie mogą zwiększać zużycia pamięci
- **User experience** - poprawki muszą poprawiać UX, nie pogarszać

### 📜 ZASADY I PROCEDURY

**Wszystkie szczegółowe zasady, procedury i checklisty zostały zebrane w pliku `_BASE_/refactoring_rules.md`. Należy się z nim zapoznać przed rozpoczęciem pracy.**

---

## 📊 ETAP 1: MAPOWANIE LOGIKI BIZNESOWEJ

### 🗺️ DYNAMICZNE GENEROWANIE MAPY PLIKÓW LOGIKI BIZNESOWEJ

**WAŻNE: Mapa NIE jest statyczna! Musi być generowana na podstawie aktualnego kodu za każdym razem.**

#### 📋 **PROCEDURA GENEROWANIA MAPY**

**KROK 1: DYNAMICZNE ODKRYWANIE STRUKTURY PROJEKTU**

> \***\*KRTYCZNE! W celu szybszego zdiagnozowania problemów z UI zalecana jest analiza wsteczna kodu od okna galerii po proces tworzenia par w pliku metadata.json\*\***

Model MUSI dynamicznie przeanalizować strukturę projektu:

```bash
# Model MUSI wykonać te komendy aby odkryć aktualną strukturę:
find src/ -type d -name "*.py" | head -20  # Znajdź katalogi z plikami .py
ls -la src/                                # Sprawdź główne katalogi
tree src/ -I "__pycache__|*.pyc"           # Pełna struktura (jeśli dostępna)
```

**Model NIE może polegać na sztywno wpisanych ścieżkach!**

**KROK 2: IDENTYFIKACJA KATALOGÓW Z LOGIKĄ BIZNESOWĄ**

Model MUSI przeanalizować każdy katalog i określić czy zawiera logikę biznesową:

**Model MUSI przeanalizować KAŻDY katalog i zadać pytania:**

- Czy ten katalog zawiera pliki z logiką biznesową?
- Czy są tu algorytmy przetwarzania danych?
- Czy są tu komponenty UI odpowiedzialne za UX?
- Czy są tu workery lub serwisy biznesowe?
- Czy są tu kontrolery koordynujące procesy?
- Czy są tu modele danych biznesowych?
- Czy są tu konfiguracje wpływające na procesy biznesowe?

**Model NIE może polegać na sztywno wpisanych nazwach katalogów!**

**Przykłady katalogów które MOGĄ zawierać logikę biznesową (ale nie muszą):**

- `src/logic/` - często główna logika biznesowa
- `src/ui/widgets/` - często komponenty UI z logiką biznesową
- `src/services/` - często serwisy biznesowe
- `src/controllers/` - często kontrolery biznesowe
- `src/models/` - często modele danych biznesowych
- `src/ui/delegates/workers/` - często workery przetwarzania biznesowego
- `src/config/` - często konfiguracja biznesowa
- **ALE model MUSI sprawdzić każdy katalog indywidualnie!**

**KROK 3: IDENTYFIKACJA PLIKÓW LOGIKI BIZNESOWEJ**

Dla każdego odkrytego katalogu z logiką biznesową, model MUSI:

1. **Wylistować wszystkie pliki .py**
2. **Przeanalizować zawartość każdego pliku**
3. **Zidentyfikować funkcje odpowiedzialne za logikę biznesową**
4. **Określić priorytet na podstawie analizy kodu**

#### 🔍 **METODA ANALIZY FUNKCJI LOGIKI BIZNESOWEJ**

**Dla każdego pliku .py model MUSI przeanalizować:**

**1. ANALIZA FUNKCJI I KLAS:**

```python
# Przykład analizy:
def main_business_function():  # ⚫⚫⚫⚫ - główny algorytm biznesowy
def important_operation():     # 🔴🔴🔴 - ważna operacja ale nie krytyczna
def helper_function():         # 🟡🟡 - funkcjonalność pomocnicza
def utility_function():        # 🟢 - funkcjonalność dodatkowa
```

**2. KRYTERIA LOGIKI BIZNESOWEJ:**

- **Algorytmy przetwarzania** - główne algorytmy biznesowe aplikacji
- **Zarządzanie danymi** - cache, metadane, modele
- **Operacje na plikach** - I/O, operacje bulk
- **UI logika biznesowa** - komponenty interfejsu z logiką biznesową
- **Workery i serwisy** - przetwarzanie w tle
- **Kontrolery** - koordynacja procesów biznesowych

**3. PYTANIA WERYFIKACYJNE:**

- Czy ta funkcja/klasa implementuje algorytm biznesowy?
- Czy wpływa na wydajność procesów biznesowych?
- Czy zarządza danymi biznesowymi?
- Czy jest częścią głównego workflow aplikacji?
- Czy ma wpływ na UX w kontekście biznesowym?

**4. OKREŚLANIE PRIORYTETU:**

**Model MUSI przeanalizować kod i określić priorytet na podstawie:**

**KRYTERIA ANALIZY PRIORYTETU:**

**⚫⚫⚫⚫ KRYTYCZNE** - Jeśli funkcja/klasa:

- Implementuje główne algorytmy biznesowe aplikacji
- Jest odpowiedzialna za wydajność krytycznych procesów
- Zarządza głównymi danymi biznesowymi
- Jest częścią UI krytycznego dla UX
- **Model MUSI przeanalizować kod aby to określić!**

**🔴🔴🔴 WYSOKIE** - Jeśli funkcja/klasa:

- Implementuje ważne operacje biznesowe
- Zarządza cache i optymalizacjami
- Jest częścią serwisów biznesowych
- Wpływa na wydajność ale nie jest krytyczna
- **Model MUSI przeanalizować kod aby to określić!**

**🟡🟡 ŚREDNIE** - Jeśli funkcja/klasa:

- Implementuje funkcjonalności pomocnicze
- Jest częścią systemu ale nie krytyczna
- Zarządza konfiguracją i walidacją
- **Model MUSI przeanalizować kod aby to określić!**

**🟢 NISKIE** - Jeśli funkcja/klasa:

- Implementuje funkcjonalności dodatkowe
- Jest odpowiedzialna za logowanie, narzędzia
- Nie ma bezpośredniego wpływu na procesy biznesowe
- **Model MUSI przeanalizować kod aby to określić!**

#### 📋 **KONTEKST BIZNESOWY APLIKACJI**

**🚨 OBOWIĄZKOWE: Model MUSI zapoznać się z plikiem README.md przed rozpoczęciem audytu!**

**Plik README.md zawiera kluczowe informacje o:**

- Architekturze i logice biznesowej aplikacji
- Głównych komponentach i ich odpowiedzialnościach
- Krytycznych wymaganiach wydajnościowych
- Głównych procesach biznesowych
- Technologiach i zależnościach
- Metrykach wydajnościowych

**Model MUSI przeanalizować pliki kontekstowe aby zrozumieć cel aplikacji:**

**Pliki do analizy kontekstu biznesowego:**

- `README.md` - **OBOWIĄZKOWY!** opis funkcjonalności aplikacji, architektura, wymagania wydajnościowe
- `main.py` - główny punkt wejścia, importy
- Pliki konfiguracyjne aplikacji - konfiguracja aplikacji
- `requirements.txt` - zależności (jakie biblioteki)
- Pliki inicjalizacyjne - eksporty głównych modułów
- Inne pliki dokumentacji i konfiguracji

**Pytania kontekstowe (po zapoznaniu się z README.md):**

- Jaki jest główny cel aplikacji?
- Jakie są kluczowe procesy biznesowe?
- Jakie są główne funkcjonalności?
- Jakie są wymagania wydajnościowe?
- Jakie są krytyczne komponenty UI?
- Jakie są oczekiwane metryki wydajnościowe?
- Jakie technologie są używane w aplikacji?

#### 🎯 **DYNAMICZNE OKREŚLANIE PRIORYTETÓW**

**Model MUSI przeanalizować każdy plik i określić priorytet na podstawie:**

**1. ANALIZA FUNKCJI I KLAS:**

```python
# Przykład analizy:
def main_business_function():  # ⚫⚫⚫⚫ - główny algorytm biznesowy
def important_operation():     # 🔴🔴🔴 - ważna operacja ale nie krytyczna
def helper_function():         # 🟡🟡 - funkcjonalność pomocnicza
def utility_function():        # 🟢 - funkcjonalność dodatkowa
```

**2. ANALIZA ZALEŻNOŚCI:**

- Ile innych plików importuje ten plik?
- Czy jest używany w głównych workflow'ach?
- Czy jest częścią krytycznych ścieżek wykonania?

**3. ANALIZA WYDAJNOŚCI:**

- Czy wpływa na czas wykonania głównych operacji?
- Czy zarządza dużymi zbiorami danych?
- Czy jest wywoływany często?

**4. ANALIZA UX:**

- Czy wpływa na responsywność interfejsu?
- Czy jest częścią głównych komponentów UI?
- Czy użytkownik bezpośrednio z tego korzysta?

#### 📊 **SZABLON MAPY DO WYPEŁNIENIA**

**Model MUSI wypełnić ten szablon na podstawie analizy aktualnego kodu:**

```markdown
### 🗺️ MAPA PLIKÓW FUNKCJONALNOŚCI BIZNESOWEJ

**Wygenerowano na podstawie aktualnego kodu: [DATA]**

**Odkryte katalogi z logiką biznesową:**

- [KATALOG_1] - [OPIS ROLI W LOGICE BIZNESOWEJ]
- [KATALOG_2] - [OPIS ROLI W LOGICE BIZNESOWEJ]
- [KATALOG_3] - [OPIS ROLI W LOGICE BIZNESOWEJ]

#### **[NAZWA_KATALOGU_1]** ([ŚCIEŻKA_KATALOGU])
```

[ŚCIEŻKA_KATALOGU]/
├── [nazwa_pliku].py [PRIORYTET] - [OPIS FUNKCJI BIZNESOWEJ]
├── [nazwa_pliku].py [PRIORYTET] - [OPIS FUNKCJI BIZNESOWEJ]
└── [nazwa_pliku].py [PRIORYTET] - [OPIS FUNKCJI BIZNESOWEJ]

```

#### **[NAZWA_KATALOGU_2]** ([ŚCIEŻKA_KATALOGU])

```

[ŚCIEŻKA_KATALOGU]/
├── [nazwa_pliku].py [PRIORYTET] - [OPIS FUNKCJI BIZNESOWEJ]
├── [nazwa_pliku].py [PRIORYTET] - [OPIS FUNKCJI BIZNESOWEJ]
└── [nazwa_pliku].py [PRIORYTET] - [OPIS FUNKCJI BIZNESOWEJ]

```

#### **[NAZWA_KATALOGU_3]** ([ŚCIEŻKA_KATALOGU])

```

[ŚCIEŻKA_KATALOGU]/
├── [nazwa_pliku].py [PRIORYTET] - [OPIS FUNKCJI BIZNESOWEJ]
├── [nazwa_pliku].py [PRIORYTET] - [OPIS FUNKCJI BIZNESOWEJ]
└── [nazwa_pliku].py [PRIORYTET] - [OPIS FUNKCJI BIZNESOWEJ]

```

**Uwaga: Model MUSI dodać sekcje dla wszystkich odkrytych katalogów z logiką biznesową!**
```

#### 🚨 **OBOWIĄZKOWE PYTANIA WERYFIKACYJNE**

**Model MUSI zadać sobie te pytania dla każdego pliku:**

1. **Czy plik zawiera funkcje odpowiedzialne za:**

   - Główne algorytmy biznesowe aplikacji?
   - Przetwarzanie danych biznesowych?
   - Zarządzanie metadanymi?
   - Cache'owanie wyników?
   - Operacje na plikach?
   - Renderowanie interfejsu?
   - Generowanie komponentów UI?
   - Przetwarzanie w tle?

2. **Czy funkcje w pliku:**

   - Implementują logikę biznesową?
   - Zarządzają danymi biznesowymi?
   - Wpływają na wydajność?
   - Są częścią głównego workflow?

3. **Czy plik jest odpowiedzialny za:**
   - Główne procesy aplikacji?
   - Krytyczne operacje biznesowe?
   - Wydajność systemu?
   - User Experience?

#### ✅ **WERYFIKACJA MAPY**

**Po wygenerowaniu mapy model MUSI sprawdzić:**

- ✅ Czy wszystkie pliki .py zostały przeanalizowane?
- ✅ Czy priorytety są uzasadnione analizą kodu?
- ✅ Czy opisy funkcji biznesowych są dokładne?
- ✅ Czy nie pominięto krytycznych plików?
- ✅ Czy mapa odzwierciedla aktualny stan kodu?

#### 🔄 **AKTUALIZACJA MAPY**

**Mapa MUSI być aktualizowana:**

- Przy każdej nowej analizie
- Po zmianach w strukturze projektu
- Po dodaniu/usunięciu plików
- Po zmianie priorytetów

**NIGDY nie używaj statycznej mapy z dokumentu!**

#### 📊 **SZABLON PRIORYTETÓW DO WYPEŁNIENIA**

**Model MUSI wygenerować priorytety na podstawie analizy:**

```markdown
### 🎯 DYNAMICZNE PRIORYTETY ANALIZY

**Wygenerowano na podstawie analizy kodu i kontekstu biznesowego: [DATA]**

#### **⚫⚫⚫⚫ KRYTYCZNE** - Podstawowa funkcjonalność aplikacji

**Uzasadnienie:** [DLACZEGO TE ELEMENTY SĄ KRYTYCZNE - na podstawie analizy kodu]

- [ELEMENT_1] - [OPIS DLACZEGO KRYTYCZNY]
- [ELEMENT_2] - [OPIS DLACZEGO KRYTYCZNY]
- [ELEMENT_3] - [OPIS DLACZEGO KRYTYCZNY]

#### **🔴🔴🔴 WYSOKIE** - Ważne operacje biznesowe

**Uzasadnienie:** [DLACZEGO TE ELEMENTY SĄ WYSOKIE - na podstawie analizy kodu]

- [ELEMENT_1] - [OPIS DLACZEGO WYSOKI]
- [ELEMENT_2] - [OPIS DLACZEGO WYSOKI]
- [ELEMENT_3] - [OPIS DLACZEGO WYSOKI]

#### **🟡🟡 ŚREDNIE** - Funkcjonalności pomocnicze

**Uzasadnienie:** [DLACZEGO TE ELEMENTY SĄ ŚREDNIE - na podstawie analizy kodu]

- [ELEMENT_1] - [OPIS DLACZEGO ŚREDNI]
- [ELEMENT_2] - [OPIS DLACZEGO ŚREDNI]
- [ELEMENT_3] - [OPIS DLACZEGO ŚREDNI]

#### **🟢 NISKIE** - Funkcjonalności dodatkowe

**Uzasadnienie:** [DLACZEGO TE ELEMENTY SĄ NISKIE - na podstawie analizy kodu]

- [ELEMENT_1] - [OPIS DLACZEGO NISKI]
- [ELEMENT_2] - [OPIS DLACZEGO NISKI]
- [ELEMENT_3] - [OPIS DLACZEGO NISKI]

#### **📈 METRYKI PRIORYTETÓW**

**Na podstawie analizy kodu:**

- **Plików krytycznych:** [LICZBA]
- **Plików wysokich:** [LICZBA]
- **Plików średnich:** [LICZBA]
- **Plików niskich:** [LICZBA]
- **Łącznie przeanalizowanych:** [LICZBA]

**Rozkład priorytetów:** [PROCENTY]
```

**WAŻNE: Model MUSI przeanalizować kod aby określić priorytety! NIE może używać sztywnych kategorii!**

**UWAGA: Powyższe priorytety są generowane dynamicznie na podstawie analizy kodu. Model MUSI przeanalizować każdy plik i określić jego priorytet na podstawie rzeczywistej zawartości i roli w aplikacji.**

**UWAGA: Sekcja "PRIORYTETY ANALIZY" została usunięta - priorytety są teraz generowane dynamicznie na podstawie analizy kodu i kontekstu biznesowego aplikacji.**

### 📋 ZAKRES ANALIZY LOGIKI BIZNESOWEJ

Przeanalizuj **WSZYSTKIE** pliki logiki biznesowej pod kątem:

## 🔍 Szukaj

- ❌ **Błędów logicznych** - Nieprawidłowe algorytmy, edge cases
- ❌ **Nieużywanych funkcji** - Dead code w logice biznesowej
- ❌ **Duplikatów logiki** - Powtarzające się algorytmy
- ❌ **Memory leaks** - Wycieki pamięci w długotrwałych procesach
- ❌ **UI thread safety issues** - Problemy z thread safety w interfejsie (jeśli aplikacja ma UI)

## 🎯 Podstawowa Funkcjonalność Biznesowa

- **Co robi proces** - Główna odpowiedzialność w kontekście biznesowym
- **Czy działa poprawnie** - Testy funkcjonalności biznesowej
- **Edge cases** - Krytyczne przypadki brzegowe w danych biznesowych
- **Data integrity** - Spójność danych w operacjach biznesowych
- **UI responsiveness** - Responsywność interfejsu użytkownika (jeśli aplikacja ma UI)

## ⚡ Wydajność Procesów (praktyczna)

- **Bottlenecks w algorytmach** - Wolne algorytmy biznesowe (zidentyfikowane przez analizę)
- **Bottlenecks w UI** - Wolne ładowanie komponentów interfejsu (jeśli aplikacja ma UI)
- **Memory usage** - Zużycie pamięci przy dużych zbiorach danych
- **UI memory** - Zużycie pamięci przy komponentach interfejsu (jeśli aplikacja ma UI)
- **I/O operations** - Optymalizacja operacji na plikach
- **UI I/O** - Optymalizacja operacji interfejsu (jeśli aplikacja ma UI)
- **Cache efficiency** - Efektywność cache'owania wyników
- **UI cache** - Efektywność cache'owania komponentów (jeśli aplikacja ma UI)
- **UI rendering performance** - Wydajność renderowania interfejsu (jeśli aplikacja ma UI)

## 🏗️ Architektura Logiki (keep it simple)

- **Zależności biznesowe** - Jak procesy biznesowe się łączą
- **UI dependencies** - Zależności między interfejsem a logiką biznesową (jeśli aplikacja ma UI)
- **Single Responsibility** - Czy każdy moduł ma jedną odpowiedzialność
- **Separation of Concerns** - Rozdzielenie logiki biznesowej od UI
- **Dependency Injection** - Czy zależności są wstrzykiwane
- **UI architecture** - Architektura komponentów interfejsu (jeśli aplikacja ma UI)

## 🔒 Bezpieczeństwo Danych

- **Data validation** - Walidacja danych wejściowych
- **File operations safety** - Bezpieczeństwo operacji na plikach
- **Error recovery** - Odzyskiwanie po błędach w procesach biznesowych
- **Atomic operations** - Atomowość operacji biznesowych
- **UI error handling** - Obsługa błędów w interfejsie użytkownika (jeśli aplikacja ma UI)

## 📊 Logowanie Biznesowe

- **Business events** - Logowanie kluczowych zdarzeń biznesowych
- **UI events** - Logowanie wydarzeń interfejsu (jeśli aplikacja ma UI)
- **Performance metrics** - Metryki wydajności procesów
- **UI performance** - Metryki wydajności interfejsu (jeśli aplikacja ma UI)
- **Error tracking** - Śledzenie błędów w logice biznesowej
- **Audit trail** - Ślad audytowy operacji biznesowych
- **UI performance metrics** - Metryki wydajności interfejsu (jeśli aplikacja ma UI)

## 🧪 Testowanie Logiki

- **Unit tests** - Testy jednostkowe logiki biznesowej
- **Integration tests** - Testy integracyjne procesów
- **Performance tests** - Testy wydajnościowe
- **UI performance tests** - Testy wydajności interfejsu (jeśli aplikacja ma UI)
- **Data validation tests** - Testy walidacji danych
- **UI tests** - Testy interfejsu użytkownika (jeśli aplikacja ma UI)

## 📋 Stan i Działania

- **Stan obecny** - Co faktycznie nie działa w procesach biznesowych
- **UI state** - Stan wydajności interfejsu (jeśli aplikacja ma UI)
- **Priorytet poprawek** - Critical/Fix Now/Can Wait/Nice to Have
- **Business impact** - Wpływ na funkcjonalność biznesową
- **Quick wins** - Co można poprawić w <2h pracy
- **UI impact** - Wpływ na interfejs użytkownika (jeśli aplikacja ma UI)

## 🚫 UNIKAJ

- ❌ Abstrakcji "na przyszłość" w logice biznesowej
- ❌ Wzorców projektowych bez konkretnej potrzeby biznesowej
- ❌ Przedwczesnej optymalizacji algorytmów
- ❌ Kompleksowych architektur dla prostych procesów biznesowych
- ❌ Refaktoryzacji działającej logiki bez konkretnego powodu
- ❌ Zmian w UI bez dokładnego testowania thread safety (jeśli aplikacja ma UI)

## ✅ SKUP SIĘ NA

- ✅ Rzeczywistych problemach w procesach biznesowych
- ✅ Bugach w algorytmach biznesowych (zidentyfikowanych przez analizę)
- ✅ **Bugach w wydajności UI** (zidentyfikowanych przez analizę)
- ✅ Oczywistych code smells w logice biznesowej
- ✅ Rzeczach które faktycznie spowalniają procesy biznesowe
- ✅ **Rzeczach które spowalniają interfejs użytkownika** (zidentyfikowanych przez analizę)
- ✅ Bezpieczeństwie danych użytkowników
- ✅ **Thread safety w komponentach UI** (jeśli aplikacja ma UI)
- ✅ **Memory leaks w widgetach UI** (jeśli aplikacja ma komponenty UI)

## 🎯 Pytania Kontrolne

- **Czy to naprawdę problem biznesowy?** - Nie wymyślaj problemów
- **Czy użytkownicy to odczują?** - Priorytet dla UX procesów
- **Ile czasu zajmie vs korzyść biznesowa?** - ROI każdej zmiany
- **Czy można to rozwiązać prościej?** - KISS principle w logice
- **Czy interfejs będzie responsywny?** - Krytyczne dla UX (jeśli aplikacja ma UI)
- **Czy poprawka nie zepsuje thread safety?** - Krytyczne dla stabilności (jeśli aplikacja jest wielowątkowa)
- **Czy UI pozostanie responsywny?** - Krytyczne dla UX (jeśli aplikacja ma UI)
- **Czy algorytmy biznesowe będą wydajne?** - Krytyczne dla procesów biznesowych

### 📁 STRUKTURA PLIKÓW WYNIKOWYCH I UŻYCIE SZABLONÓW

**Kluczem do spójności i efektywności audytu jest używanie przygotowanych szablonów.** Zamiast tworzyć strukturę plików od zera, **należy kopiować i wypełniać** odpowiednie szablony.

**W folderze `_BASE_/` znajdują się szablony:**

- `refactoring_rules.md` - Główne zasady, do których linkują pozostałe dokumenty.
- `correction_template.md` - Szablon dla plików `*_correction.md`.
- `patch_code_template.md` - Szablon dla plików `*_patch_code.md`.

**Procedura tworzenia plików wynikowych:**

1.  **Dla każdego analizowanego pliku logiki biznesowej `[nazwa_pliku].py`:**
    - Skopiuj `_BASE_/correction_template.md` do `AUDYT/corrections/[nazwa_pliku]_correction.md`.
    - Wypełnij skopiowany plik zgodnie z wynikami analizy logiki biznesowej.
    - Skopiuj `_BASE_/patch_code_template.md` do `AUDYT/patches/[nazwa_pliku]_patch_code.md`.
    - Wypełnij plik patch fragmentami kodu z optymalizacjami logiki biznesowej.

### 🚫 ZASADA INDYWIDUALNEGO GENEROWANIA DOKUMENTÓW

**GRUPOWANIE POPRAWEK DLA WIELU PLIKÓW JEST NIEDOPUSZCZALNE!**

**OBOWIĄZKOWE ZASADY:**

1. **Jeden plik = jeden correction** - Każdy plik `.py` ma SWÓJ plik `[nazwa]_correction.md`
2. **Jeden plik = jeden patch** - Każdy plik `.py` ma SWÓJ plik `[nazwa]_patch_code.md`
3. **Brak grupowania** - NIGDY nie łącz analiz wielu plików w jeden dokument
4. **Indywidualne nazwy** - Każdy dokument ma nazwę bazującą na nazwie pliku źródłowego

**PRZYKŁADY POPRAWNEJ STRUKTURY:**

```
AUDYT/corrections/
├── [nazwa_pliku1]_correction.md        ✅ Jeden plik
├── [nazwa_pliku2]_correction.md        ✅ Jeden plik
├── [nazwa_pliku3]_correction.md        ✅ Jeden plik
└── [nazwa_pliku4]_correction.md        ✅ Jeden plik

AUDYT/patches/
├── [nazwa_pliku1]_patch_code.md        ✅ Jeden plik
├── [nazwa_pliku2]_patch_code.md        ✅ Jeden plik
├── [nazwa_pliku3]_patch_code.md        ✅ Jeden plik
└── [nazwa_pliku4]_patch_code.md        ✅ Jeden plik
```

**PRZYKŁADY NIEDOPUSZCZALNE:**

```
❌ AUDYT/corrections/business_logic_correction.md    # Grupowanie wielu plików
❌ AUDYT/patches/core_optimizations_patch.md         # Grupowanie wielu plików
❌ AUDYT/corrections/[plik1]_and_[plik2]_correction.md # Łączenie 2 plików
```

**KONSEKWENCJE NARUSZENIA:**

- ❌ Dokument zostanie odrzucony
- ❌ Analiza będzie musiała być powtórzona
- ❌ Postęp audytu zostanie wstrzymany
- ❌ Model będzie musiał podzielić dokument na indywidualne pliki

**WERYFIKACJA ZASADY:**

Przed utworzeniem dokumentu sprawdź:

- ✅ Czy dokument dotyczy TYLKO jednego pliku `.py`?
- ✅ Czy nazwa dokumentu zawiera nazwę tego pliku?
- ✅ Czy nie ma próby grupowania wielu plików?
- ✅ Czy każdy plik ma SWÓJ correction i SWÓJ patch?

### 📈 OBOWIĄZKOWA KONTROLA POSTĘPU PO KAŻDYM ETAPIE

**🚨 KRYTYCZNE: MODEL MUSI PAMIĘTAĆ O UZUPEŁNIENIU BUSINESS_LOGIC_MAP.MD!**

**MODEL MUSI SPRAWDZIĆ I PODAĆ:**

- **Etapów ukończonych:** X/Y
- **Procent ukończenia:** X%
- **Następny etap:** Nazwa pliku logiki biznesowej do analizy
- **Business impact:** Wpływ na procesy biznesowe
- **✅ UZUPEŁNIONO BUSINESS_LOGIC_MAP.MD:** TAK/NIE

**OBOWIĄZKOWE KROKI PO KAŻDYM ETAPIE:**

1. ✅ **Ukończ analizę pliku** - utwórz correction.md i patch_code.md
2. ✅ **UZUPEŁNIJ business_logic_map.md** - dodaj status ukończenia
3. ✅ **Sprawdź postęp** - podaj procent ukończenia
4. ✅ **Określ następny etap** - nazwa kolejnego pliku do analizy

**PRZYKŁAD RAPORTU POSTĘPU:**

```
📊 POSTĘP AUDYTU LOGIKI BIZNESOWEJ:
✅ Ukończone etapy: 3/15 (20%)
🔄 Aktualny etap: [NAZWA_PLIKU_LOGIKI_BIZNESOWEJ]
⏳ Pozostałe etapy: 12
💼 Business impact: [OPIS WPŁYWU NA PROCESY BIZNESOWE]
✅ UZUPEŁNIONO BUSINESS_LOGIC_MAP.MD: TAK
```

**🚨 MODEL NIE MOŻE ZAPOMNIEĆ O UZUPEŁNIENIU MAPY!**

### ✅ ZAZNACZANIE UKOŃCZONYCH ANALIZ W BUSINESS_LOGIC_MAP.MD

**PO KAŻDEJ UKOŃCZONEJ ANALIZIE PLIKU LOGIKI BIZNESOWEJ:**

1. **Otwórz plik** `AUDYT/business_logic_map.md`
2. **Znajdź sekcję** z analizowanym plikiem
3. **Dodaj status ukończenia** w formacie:

```markdown
### 📄 [NAZWA_PLIKU].PY

- **Status:** ✅ UKOŃCZONA ANALIZA
- **Data ukończenia:** [DATA]
- **Business impact:** [OPIS WPŁYWU NA PROCESY BIZNESOWE]
- **Pliki wynikowe:**
  - `AUDYT/corrections/[nazwa_pliku]_correction.md`
  - `AUDYT/patches/[nazwa_pliku]_patch_code.md`
```

**PRZYKŁAD ZAZNACZENIA:**

```markdown
### 📄 [NAZWA_PLIKU].PY

- **Status:** ✅ UKOŃCZONA ANALIZA
- **Data ukończenia:** [DATA]
- **Business impact:** [OPIS WPŁYWU NA PROCESY BIZNESOWE]
- **Pliki wynikowe:**
  - `AUDYT/corrections/[nazwa_pliku]_correction.md`
  - `AUDYT/patches/[nazwa_pliku]_patch_code.md`
```

**OBOWIĄZKOWE ZAZNACZENIA:**

- ✅ **Status ukończenia** - zawsze "✅ UKOŃCZONA ANALIZA"
- ✅ **Data ukończenia** - aktualna data w formacie YYYY-MM-DD
- ✅ **Business impact** - konkretny wpływ na procesy biznesowe
- ✅ **Pliki wynikowe** - ścieżki do utworzonych plików correction i patch

**KONTROLA SPÓJNOŚCI:**

- Sprawdź czy wszystkie ukończone pliki są zaznaczone w mapie
- Upewnij się że ścieżki do plików wynikowych są prawidłowe
- Zweryfikuj że business impact jest opisany konkretnie

**🚨 KRYTYCZNE: MODEL MUSI PAMIĘTAĆ O UZUPEŁNIENIU BUSINESS_LOGIC_MAP.MD PO KAŻDEJ ANALIZIE!**

**🚨 BEZ TEGO KROKU AUDYT NIE JEST UKOŃCZONY!**

### 🚨 WAŻNE: ZASADY DOKUMENTACJI I COMMITÓW

**DOKUMENTACJA NIE JEST UZUPEŁNIANA W TRAKCIE PROCESU!**

- **CZEKAJ** na wyraźne polecenie użytkownika.
- **DOKUMENTUJ** tylko po pozytywnych testach użytkownika.
- **Commituj** z jasnym komunikatem po zakończeniu etapu.

#### **FORMAT COMMITÓW:**

```
git commit -m "BUSINESS LOGIC AUDIT [NUMER]: [NAZWA_PLIKU] - [OPIS] - ZAKOŃCZONY"
```

---

## 🚀 ROZPOCZĘCIE

**🚨 OBOWIĄZKOWE KROKI PRZED ROZPOCZĘCIEM:**

1. **Zapoznaj się z README.md** - zawiera kluczowe informacje o architekturze, wymaganiach wydajnościowych i procesach biznesowych aplikacji
2. **Przeanalizuj strukturę projektu** - dynamicznie odkryj katalogi i pliki
3. **Wygeneruj mapę logiki biznesowej** - na podstawie analizy kodu i kontekstu z README.md

**Czekam na Twój pierwszy wynik: zawartość pliku `business_logic_map.md` z mapą plików logiki biznesowej.**

**UWAGA: Mapa musi być wygenerowana na podstawie analizy aktualnego kodu oraz kontekstu biznesowego z README.md!**

#### **SZCZEGÓŁOWA ANALIZA FUNKCJI BIZNESOWYCH**

**Dla każdego pliku z priorytetem ⚫⚫⚫⚫ lub 🔴🔴🔴:**

**📄 [NAZWA_PLIKU].PY**

- **Główne funkcje biznesowe:**
  - `function_name()` - [OPIS ROLI W LOGICE BIZNESOWEJ]
  - `class_name.method()` - [OPIS ROLI W LOGICE BIZNESOWEJ]
- **Priorytet:** [PRIORYTET]
- **Uzasadnienie:** [DLACZEGO TEN PLIK MA TAKI PRIORYTET]
- **Wpływ na biznes:** [JAKI MA WPŁYW NA PROCESY BIZNESOWE]

## 🚨 KRYTYCZNE ZASADY - MODEL MUSI PAMIĘTAĆ!

### 📋 **OBOWIĄZKOWE UZUPEŁNIANIE BUSINESS_LOGIC_MAP.MD**

**🚨 MODEL MUSI PAMIĘTAĆ: Po każdej ukończonej analizie pliku logiki biznesowej OBAWIĄZKOWO uzupełnić plik `AUDYT/business_logic_map.md`!**

**OBOWIĄZKOWE KROKI PO KAŻDEJ ANALIZIE:**

1. ✅ **Ukończ analizę pliku** - utwórz correction.md i patch_code.md
2. ✅ **OTWÓRZ business_logic_map.md** - znajdź sekcję z analizowanym plikiem
3. ✅ **DODAJ status ukończenia** - zaznacz że analiza została ukończona
4. ✅ **DODAJ datę ukończenia** - aktualna data w formacie YYYY-MM-DD
5. ✅ **DODAJ business impact** - opis wpływu na procesy biznesowe
6. ✅ **DODAJ ścieżki do plików wynikowych** - correction.md i patch_code.md

**FORMAT UZUPEŁNIENIA W BUSINESS_LOGIC_MAP.MD:**

```markdown
### 📄 [NAZWA_PLIKU].PY

- **Status:** ✅ UKOŃCZONA ANALIZA
- **Data ukończenia:** [DATA]
- **Business impact:** [OPIS WPŁYWU NA PROCESY BIZNESOWE]
- **Pliki wynikowe:**
  - `AUDYT/corrections/[nazwa_pliku]_correction.md`
  - `AUDYT/patches/[nazwa_pliku]_patch_code.md`
```

**🚨 MODEL NIE MOŻE ZAPOMNIEĆ O TYM KROKU!**
