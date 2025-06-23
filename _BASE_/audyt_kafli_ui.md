# 🎯 AUDYT KAFLI UI - TWORZENIE I RENDEROWANIE

> **WAŻNE! Wszystkie pliki wynikowe audytu (np. `business_logic_map_kafli.md`, `corrections_kafli.md`, `patch_code_kafli.md`, pliki z analizami i poprawkami) MUSZĄ być zapisywane wyłącznie w katalogu `AUDYT/KAFLI`. Tylko tam należy ich szukać!**

## 🎯 CEL

Kompleksowa analiza, optymalizacja i uproszczenie logiki biznesowej **procesu tworzenia i renderowania kafli w UI** aplikacji z naciskiem na wydajność renderowania, stabilność komponentów UI i eliminację over-engineering w warstwie prezentacji danych.

### 🏛️ TRZY FILARY AUDYTU KAFLI UI

Ten audyt opiera się na trzech kluczowych filarach, które stanowią najwyższe priorytety analizy procesu kafli:

#### 1️⃣ **WYDAJNOŚĆ RENDEROWANIA KAFLI** ⚡

- Optymalizacja czasu tworzenia kafli dla tysięcy elementów
- Redukcja zużycia pamięci przy renderowaniu dużych galerii
- Eliminacja wąskich gardeł w pipeline'ie renderowania kafli
- Usprawnienie cache'owania miniaturek i metadanych kafli
- Minimalizacja niepotrzebnych operacji w workflow tworzenia kafli

#### 2️⃣ **STABILNOŚĆ KOMPONENTÓW KAFLI** 🛡️

- Niezawodność procesu tworzenia i aktualizacji kafli
- Proper error handling w renderowaniu kafli
- Thread safety w operacjach UI kafli
- Eliminacja memory leaks w komponentach kafli
- Przewidywalność zachowania kafli przy różnych scenariuszach danych

#### 3️⃣ **WYELIMINOWANIE OVER-ENGINEERING KAFLI** 🎯

- Uproszczenie nadmiernie skomplikowanych algorytmów renderowania kafli
- Eliminacja niepotrzebnych abstrakcji w komponentach kafli
- Redukcja liczby warstw w architekturze kafli
- Konsolidacja rozproszonej logiki renderowania kafli
- Zastąpienie skomplikowanych wzorców prostszymi rozwiązaniami

### 🖼️ **KRYTYCZNY PROCES KAFLI W INTERFEJSIE UŻYTKOWNIKA**

**WAŻNE: Proces tworzenia i renderowania kafli jest KLUCZOWY dla wydajności i UX aplikacji!**

#### 🎯 **Dlaczego Kafelki to Krytyczna Logika Biznesowa**

- **Główny interfejs prezentacji danych** - kafelki wyświetlają wszystkie pary plików
- **Wydajność krytyczna** - renderowanie tysięcy kafli musi być płynne
- **Algorytmy cache'owania** - inteligentne zarządzanie pamięcią kafli
- **User Experience** - responsywność kafli decyduje o użyteczności aplikacji
- **Virtual scrolling** - renderowanie tylko widocznych kafli dla wydajności

#### 📊 **Wymagania Wydajnościowe Kafli**

- **Duże zbiory danych**: renderowanie tysięcy kafli jednocześnie
- **Czas ładowania**: szybkie tworzenie i wyświetlanie kafli
- **Płynne przewijanie**: bez lagów przy scrollowaniu przez tysiące kafli
- **Responsywność UI**: brak blokowania podczas batch creation kafli
- **Memory efficiency**: optymalne zarządzanie pamięcią dla kafli i miniaturek

#### 🔧 **Kluczowe Komponenty Logiki Kafli**

- **Tile creation** - tworzenie instancji kafli z danymi
- **Thumbnail generation** - asynchroniczne generowanie miniaturek
- **Lazy loading** - ładowanie kafli na żądanie
- **Virtual scrolling** - renderowanie tylko widocznych kafli
- **Cache management** - inteligentne cache'owanie kafli i miniaturek
- **Batch processing** - przetwarzanie kafli w grupach dla wydajności
- **Event handling** - obsługa interakcji użytkownika z kafli

### 🎨 **KRYTYCZNA ROLA KODU KAFLI W LOGICE BIZNESOWEJ**

**🚨 SZCZEGÓLNIE WAŻNE: Audyt i poprawki w plikach odpowiedzialnych za kafelki muszą być szczególnie precyzyjnie audytowane, poprawki muszą być bardzo dokładne, uwzględniające bardzo ważną rolę tego kodu.**

#### 🎯 **Dlaczego Kafelki to Logika Biznesowa**

- **Bezpośredni wpływ na UX** - każdy błąd w kafli natychmiast wpływa na użytkownika
- **Thread safety krytyczne** - kafle są tworzone asynchronicznie w worker threads
- **Memory management** - nieprawidłowe zarządzanie pamięcią kafli powoduje crashy
- **Event handling** - błędy w obsłudze zdarzeń kafli mogą zablokować galerię
- **Performance critical** - kafle muszą być responsywne przy tysiącach elementów

#### 🔧 **Szczególne Wymagania dla Audytu Kafli**

- **Precyzyjne analizy** - każdy widget kafla, każdy event handler
- **Thread safety verification** - sprawdzenie wszystkich operacji kafli w kontekście wątków
- **Memory leak detection** - szczególna uwaga na wycieki pamięci w kafli
- **Virtual scrolling analysis** - analiza wpływu na virtual scrolling
- **Signal-slot verification** - sprawdzenie poprawności połączeń signal-slot kafli
- **Resource cleanup** - weryfikacja prawidłowego zwalniania zasobów kafli

#### 🚨 **Krytyczne Obszary Kafli Wymagające Szczególnej Uwagi**

- **Główne komponenty kafli** - FileTileWidget, SpecialFolderTileWidget
- **Komponenty renderujące miniaturki** - thumbnail generation i cache'owanie
- **Komponenty cache'owania kafli** - tile cache optimizer, resource manager
- **Event handlers kafli** - obsługa kliknięć, drag&drop, metadata changes
- **Progress indicators** - feedback podczas batch creation kafli
- **Komponenty async** - asynchroniczne ładowanie kafli i miniaturek

#### ✅ **Standardy Jakości dla Poprawek Kafli**

- **Zero regressions** - poprawki nie mogą wprowadzać nowych błędów w kafli
- **Backward compatibility** - zachowanie istniejącego API kafli
- **Performance preservation** - poprawki nie mogą spowolnić renderowania kafli
- **Thread safety** - wszystkie operacje kafli muszą być thread-safe
- **Memory efficiency** - poprawki nie mogą zwiększać zużycia pamięci kafli
- **User experience** - poprawki muszą poprawiać UX kafli, nie pogarszać

### 📜 ZASADY I PROCEDURY

**Wszystkie szczegółowe zasady, procedury i checklisty zostały zebrane w pliku `_BASE_/refactoring_rules.md`. Należy się z nim zapoznać przed rozpoczęciem pracy.**

---

## 📊 ETAP 1: MAPOWANIE LOGIKI BIZNESOWEJ KAFLI

### 🗺️ DYNAMICZNE GENEROWANIE MAPY PLIKÓW LOGIKI KAFLI

**WAŻNE: Mapa NIE jest statyczna! Musi być generowana na podstawie aktualnego kodu za każdym razem.**

#### 📋 **PROCEDURA GENEROWANIA MAPY KAFLI**

**KROK 1: DYNAMICZNE ODKRYWANIE KOMPONENTÓW KAFLI**

Model MUSI dynamicznie przeanalizować wszystkie komponenty związane z kafli:

```bash
# Model MUSI wykonać te komendy aby odkryć komponenty kafli:
find src/ -name "*tile*" -type f | grep -v __pycache__     # Znajdź pliki tile
find src/ -name "*thumbnail*" -type f | grep -v __pycache__ # Znajdź pliki thumbnail
find src/ -name "*gallery*" -type f | grep -v __pycache__   # Znajdź pliki gallery
find src/ -name "*cache*" -type f | grep -v __pycache__     # Znajdź pliki cache
```

**Model NIE może polegać na sztywno wpisanych ścieżkach!**

**KROK 2: IDENTYFIKACJA KATALOGÓW Z LOGIKĄ KAFLI**

Model MUSI przeanalizować każdy katalog i określić czy zawiera logikę kafli:

**Model MUSI przeanalizować KAŻDY katalog i zadać pytania:**

- Czy ten katalog zawiera komponenty kafli?
- Czy są tu algorytmy renderowania kafli?
- Czy są tu komponenty cache'owania kafli?
- Czy są tu workery odpowiedzialne za tworzenie kafli?
- Czy są tu managery koordynujące procesy kafli?
- Czy są tu modele danych kafli?
- Czy są tu konfiguracje wpływające na procesy kafli?

**Model NIE może polegać na sztywno wpisanych nazwach katalogów!**

**Przykłady katalogów które MOGĄ zawierać logikę kafli (ale model MUSI sprawdzić):**

- `src/ui/widgets/` - główne komponenty kafli (FileTileWidget, tile\_\*)
- `src/ui/main_window/` - managery kafli (TileManager, etc.)
- `src/ui/delegates/workers/` - workery tworzące kafli
- `src/ui/gallery_manager.py` - zarządzanie galerią kafli
- `src/logic/` - logika biznesowa obsługująca kafle
- **ALE model MUSI sprawdzić każdy katalog indywidualnie!**

**KROK 3: IDENTYFIKACJA PLIKÓW LOGIKI KAFLI**

Dla każdego odkrytego katalogu z logiką kafli, model MUSI:

1. **Wylistować wszystkie pliki .py związane z kafli**
2. **Przeanalizować zawartość każdego pliku**
3. **Zidentyfikować funkcje odpowiedzialne za logikę kafli**
4. **Określić priorytet na podstawie analizy kodu kafli**

#### 🔍 **METODA ANALIZY FUNKCJI LOGIKI KAFLI**

**Dla każdego pliku .py model MUSI przeanalizować:**

**1. ANALIZA FUNKCJI I KLAS KAFLI:**

```python
# Przykład analizy:
def create_tile_widget():          # ⚫⚫⚫⚫ - główne tworzenie kafla
def render_thumbnail():            # ⚫⚫⚫⚫ - krytyczne renderowanie
def cache_tile_data():             # 🔴🔴🔴 - ważne cache'owanie
def update_tile_metadata():        # 🟡🟡 - aktualizacja metadanych
def tile_utility_function():       # 🟢 - funkcjonalność dodatkowa
```

**2. KRYTERIA LOGIKI KAFLI:**

- **Tworzenie kafli** - główne algorytmy tworzenia instancji kafli
- **Renderowanie miniaturek** - generowanie i cache'owanie thumbnails
- **Zarządzanie danymi kafli** - metadata, cache, modele
- **Event handling kafli** - obsługa interakcji użytkownika
- **Batch processing kafli** - przetwarzanie kafli w grupach
- **Virtual scrolling** - zarządzanie widocznymi kafli

**3. PYTANIA WERYFIKACYJNE KAFLI:**

- Czy ta funkcja/klasa implementuje logikę tworzenia kafli?
- Czy wpływa na wydajność renderowania kafli?
- Czy zarządza danymi kafli (miniaturki, metadata)?
- Czy jest częścią workflow tworzenia galerii kafli?
- Czy ma wpływ na UX w kontekście kafli?

**4. OKREŚLANIE PRIORYTETU KAFLI:**

**Model MUSI przeanalizować kod i określić priorytet na podstawie:**

**KRYTERIA ANALIZY PRIORYTETU KAFLI:**

**⚫⚫⚫⚫ KRYTYCZNE** - Jeśli funkcja/klasa:

- Implementuje główne algorytmy tworzenia kafli
- Jest odpowiedzialna za wydajność renderowania kafli
- Zarządza głównymi danymi kafli (miniaturki, cache)
- Jest częścią UI krytycznego dla UX kafli
- **Model MUSI przeanalizować kod aby to określić!**

**🔴🔴🔴 WYSOKIE** - Jeśli funkcja/klasa:

- Implementuje ważne operacje kafli
- Zarządza cache i optymalizacjami kafli
- Jest częścią serwisów kafli
- Wpływa na wydajność kafli ale nie jest krytyczna
- **Model MUSI przeanalizować kod aby to określić!**

**🟡🟡 ŚREDNIE** - Jeśli funkcja/klasa:

- Implementuje funkcjonalności pomocnicze kafli
- Jest częścią systemu kafli ale nie krytyczna
- Zarządza konfiguracją i walidacją kafli
- **Model MUSI przeanalizować kod aby to określić!**

**🟢 NISKIE** - Jeśli funkcja/klasa:

- Implementuje funkcjonalności dodatkowe kafli
- Jest odpowiedzialna za logowanie, narzędzia kafli
- Nie ma bezpośredniego wpływu na procesy kafli
- **Model MUSI przeanalizować kod aby to określić!**

#### 📋 **KONTEKST BIZNESOWY KAFLI**

**🚨 OBOWIĄZKOWE: Model MUSI zapoznać się z README.md w kontekście kafli!**

**Model MUSI przeanalizować pliki kontekstowe kafli:**

**Pliki do analizy kontekstu kafli:**

- `README.md` - **OBOWIĄZKOWY!** wymagania wydajnościowe kafli
- `src/main.py` - inicjalizacja komponentów kafli
- `src/ui/gallery_manager.py` - główny manager galerii kafli
- `src/ui/main_window/tile_manager.py` - manager kafli
- Pliki konfiguracyjne kafli - ustawienia kafli

**Pytania kontekstowe kafli (po zapoznaniu się z README.md):**

- Jaki jest główny cel procesu kafli w aplikacji?
- Jakie są kluczowe procesy tworzenia kafli?
- Jakie są główne funkcjonalności kafli?
- Jakie są wymagania wydajnościowe kafli (1000+ kafli)?
- Jakie są krytyczne komponenty kafli?
- Jakie są oczekiwane metryki wydajnościowe kafli?
- Jakie technologie są używane w kafli (PyQt6, QThread)?

#### 🎯 **DYNAMICZNE OKREŚLANIE PRIORYTETÓW KAFLI**

**Model MUSI przeanalizować każdy plik kafli i określić priorytet na podstawie:**

**1. ANALIZA FUNKCJI I KLAS KAFLI:**

```python
# Przykład analizy kafli:
def create_tile_batch():           # ⚫⚫⚫⚫ - główny algorytm batch kafli
def render_tile_thumbnail():       # ⚫⚫⚫⚫ - krytyczne renderowanie
def cache_tile_data():             # 🔴🔴🔴 - ważne cache'owanie
def update_tile_ui():              # 🟡🟡 - aktualizacja UI kafla
def tile_debug_function():         # 🟢 - funkcjonalność debug
```

**2. ANALIZA ZALEŻNOŚCI KAFLI:**

- Ile innych plików importuje komponenty kafli?
- Czy jest używany w głównych workflow'ach kafli?
- Czy jest częścią krytycznych ścieżek renderowania kafli?

**3. ANALIZA WYDAJNOŚCI KAFLI:**

- Czy wpływa na czas tworzenia kafli?
- Czy zarządza dużymi zbiorami danych kafli?
- Czy jest wywoływany często podczas renderowania?

**4. ANALIZA UX KAFLI:**

- Czy wpływa na responsywność kafli?
- Czy jest częścią głównych komponentów galerii?
- Czy użytkownik bezpośrednio z kafli korzysta?

#### 📊 **SZABLON MAPY KAFLI DO WYPEŁNIENIA**

**Model MUSI wypełnić ten szablon na podstawie analizy aktualnego kodu kafli:**

```markdown
### 🗺️ MAPA PLIKÓW FUNKCJONALNOŚCI KAFLI UI

**Wygenerowano na podstawie aktualnego kodu kafli: [DATA]**

**Odkryte katalogi z logiką kafli:**

- [KATALOG_1] - [OPIS ROLI W LOGICE KAFLI]
- [KATALOG_2] - [OPIS ROLI W LOGICE KAFLI]
- [KATALOG_3] - [OPIS ROLI W LOGICE KAFLI]

#### **[NAZWA_KATALOGU_1]** ([ŚCIEŻKA_KATALOGU])

[ŚCIEŻKA_KATALOGU]/
├── [nazwa_pliku_kafli].py [PRIORYTET] - [OPIS FUNKCJI KAFLI]
├── [nazwa_pliku_kafli].py [PRIORYTET] - [OPIS FUNKCJI KAFLI]
└── [nazwa_pliku_kafli].py [PRIORYTET] - [OPIS FUNKCJI KAFLI]

#### **[NAZWA_KATALOGU_2]** ([ŚCIEŻKA_KATALOGU])

[ŚCIEŻKA_KATALOGU]/
├── [nazwa_pliku_kafli].py [PRIORYTET] - [OPIS FUNKCJI KAFLI]
├── [nazwa_pliku_kafli].py [PRIORYTET] - [OPIS FUNKCJI KAFLI]
└── [nazwa_pliku_kafli].py [PRIORYTET] - [OPIS FUNKCJI KAFLI]

**Uwaga: Model MUSI dodać sekcje dla wszystkich odkrytych katalogów z logiką kafli!**
```

#### 🚨 **OBOWIĄZKOWE PYTANIA WERYFIKACYJNE KAFLI**

**Model MUSI zadać sobie te pytania dla każdego pliku kafli:**

1. **Czy plik zawiera funkcje odpowiedzialne za:**

   - Tworzenie instancji kafli?
   - Renderowanie kafli i miniaturek?
   - Cache'owanie danych kafli?
   - Zarządzanie metadanymi kafli?
   - Batch processing kafli?
   - Virtual scrolling kafli?
   - Event handling kafli?

2. **Czy funkcje w pliku:**

   - Implementują logikę biznesową kafli?
   - Zarządzają danymi kafli?
   - Wpływają na wydajność kafli?
   - Są częścią głównego workflow kafli?

3. **Czy plik jest odpowiedzialny za:**
   - Główne procesy kafli w aplikacji?
   - Krytyczne operacje renderowania kafli?
   - Wydajność systemu kafli?
   - User Experience kafli?

#### ✅ **WERYFIKACJA MAPY KAFLI**

**Po wygenerowaniu mapy kafli model MUSI sprawdzić:**

- ✅ Czy wszystkie pliki .py związane z kafli zostały przeanalizowane?
- ✅ Czy priorytety kafli są uzasadnione analizą kodu?
- ✅ Czy opisy funkcji kafli są dokładne?
- ✅ Czy nie pominięto krytycznych plików kafli?
- ✅ Czy mapa odzwierciedla aktualny stan kodu kafli?

#### 🔄 **AKTUALIZACJA MAPY KAFLI**

**Mapa kafli MUSI być aktualizowana:**

- Przy każdej nowej analizie kafli
- Po zmianach w strukturze komponentów kafli
- Po dodaniu/usunięciu plików kafli
- Po zmianie priorytetów kafli

**NIGDY nie używaj statycznej mapy z dokumentu!**

#### 📊 **SZABLON PRIORYTETÓW KAFLI DO WYPEŁNIENIA**

**Model MUSI wygenerować priorytety kafli na podstawie analizy:**

```markdown
### 🎯 DYNAMICZNE PRIORYTETY ANALIZY KAFLI

**Wygenerowano na podstawie analizy kodu i kontekstu kafli: [DATA]**

#### **⚫⚫⚫⚫ KRYTYCZNE** - Podstawowa funkcjonalność kafli

**Uzasadnienie:** [DLACZEGO TE ELEMENTY KAFLI SĄ KRYTYCZNE - na podstawie analizy kodu]

- [ELEMENT_KAFLI_1] - [OPIS DLACZEGO KRYTYCZNY DLA KAFLI]
- [ELEMENT_KAFLI_2] - [OPIS DLACZEGO KRYTYCZNY DLA KAFLI]
- [ELEMENT_KAFLI_3] - [OPIS DLACZEGO KRYTYCZNY DLA KAFLI]

#### **🔴🔴🔴 WYSOKIE** - Ważne operacje kafli

**Uzasadnienie:** [DLACZEGO TE ELEMENTY KAFLI SĄ WYSOKIE - na podstawie analizy kodu]

- [ELEMENT_KAFLI_1] - [OPIS DLACZEGO WYSOKI DLA KAFLI]
- [ELEMENT_KAFLI_2] - [OPIS DLACZEGO WYSOKI DLA KAFLI]
- [ELEMENT_KAFLI_3] - [OPIS DLACZEGO WYSOKI DLA KAFLI]

#### **🟡🟡 ŚREDNIE** - Funkcjonalności pomocnicze kafli

**Uzasadnienie:** [DLACZEGO TE ELEMENTY KAFLI SĄ ŚREDNIE - na podstawie analizy kodu]

- [ELEMENT_KAFLI_1] - [OPIS DLACZEGO ŚREDNI DLA KAFLI]
- [ELEMENT_KAFLI_2] - [OPIS DLACZEGO ŚREDNI DLA KAFLI]
- [ELEMENT_KAFLI_3] - [OPIS DLACZEGO ŚREDNI DLA KAFLI]

#### **🟢 NISKIE** - Funkcjonalności dodatkowe kafli

**Uzasadnienie:** [DLACZEGO TE ELEMENTY KAFLI SĄ NISKIE - na podstawie analizy kodu]

- [ELEMENT_KAFLI_1] - [OPIS DLACZEGO NISKI DLA KAFLI]
- [ELEMENT_KAFLI_2] - [OPIS DLACZEGO NISKI DLA KAFLI]
- [ELEMENT_KAFLI_3] - [OPIS DLACZEGO NISKI DLA KAFLI]

#### **📈 METRYKI PRIORYTETÓW KAFLI**

**Na podstawie analizy kodu kafli:**

- **Plików kafli krytycznych:** [LICZBA]
- **Plików kafli wysokich:** [LICZBA]
- **Plików kafli średnich:** [LICZBA]
- **Plików kafli niskich:** [LICZBA]
- **Łącznie przeanalizowanych plików kafli:** [LICZBA]

**Rozkład priorytetów kafli:** [PROCENTY]
```

**WAŻNE: Model MUSI przeanalizować kod aby określić priorytety kafli! NIE może używać sztywnych kategorii!**

### 📋 ZAKRES ANALIZY LOGIKI KAFLI

Przeanalizuj **WSZYSTKIE** pliki logiki kafli pod kątem:

## 🔍 Szukaj w Kafli

- ❌ **Błędów logicznych kafli** - Nieprawidłowe algorytmy tworzenia/renderowania kafli
- ❌ **Nieużywanych funkcji kafli** - Dead code w komponentach kafli
- ❌ **Duplikatów logiki kafli** - Powtarzające się algorytmy kafli
- ❌ **Memory leaks kafli** - Wycieki pamięci w komponentach kafli
- ❌ **Thread safety issues kafli** - Problemy z thread safety w kafli

## 🎯 Podstawowa Funkcjonalność Kafli

- **Co robi proces kafli** - Główna odpowiedzialność w kontekście kafli
- **Czy kafle działają poprawnie** - Testy funkcjonalności kafli
- **Edge cases kafli** - Krytyczne przypadki brzegowe w danych kafli
- **Data integrity kafli** - Spójność danych w operacjach kafli
- **Responsiveness kafli** - Responsywność kafli przy dużych zbiorach

## ⚡ Wydajność Kafli (praktyczna)

- **Bottlenecks w algorytmach kafli** - Wolne algorytmy tworzenia kafli
- **Bottlenecks w renderowaniu kafli** - Wolne ładowanie komponentów kafli
- **Memory usage kafli** - Zużycie pamięci przy tysiącach kafli
- **Thumbnail memory** - Zużycie pamięci przy miniaturkach kafli
- **I/O operations kafli** - Optymalizacja operacji kafli
- **Cache efficiency kafli** - Efektywność cache'owania kafli
- **Rendering performance kafli** - Wydajność renderowania kafli

## 🏗️ Architektura Kafli (keep it simple)

- **Zależności kafli** - Jak komponenty kafli się łączą
- **Single Responsibility kafli** - Czy każdy komponent kafli ma jedną odpowiedzialność
- **Separation of Concerns kafli** - Rozdzielenie logiki kafli
- **Dependency Injection kafli** - Czy zależności kafli są wstrzykiwane
- **Architecture kafli** - Architektura komponentów kafli

## 🔒 Bezpieczeństwo Kafli

- **Data validation kafli** - Walidacja danych wejściowych kafli
- **Error recovery kafli** - Odzyskiwanie po błędach w procesach kafli
- **Atomic operations kafli** - Atomowość operacji kafli
- **Error handling kafli** - Obsługa błędów w kafli

## 📊 Logowanie Kafli

- **Tile events** - Logowanie kluczowych zdarzeń kafli
- **Performance metrics kafli** - Metryki wydajności procesów kafli
- **Error tracking kafli** - Śledzenie błędów w logice kafli
- **Audit trail kafli** - Ślad audytowy operacji kafli

## 🧪 Testowanie Kafli

- **Unit tests kafli** - Testy jednostkowe logiki kafli
- **Integration tests kafli** - Testy integracyjne procesów kafli
- **Performance tests kafli** - Testy wydajnościowe kafli
- **Data validation tests kafli** - Testy walidacji danych kafli

## 📋 Stan i Działania Kafli

- **Stan obecny kafli** - Co faktycznie nie działa w procesach kafli
- **Priorytet poprawek kafli** - Critical/Fix Now/Can Wait/Nice to Have
- **Business impact kafli** - Wpływ na funkcjonalność kafli
- **Quick wins kafli** - Co można poprawić w kafli w <2h pracy

## 🚫 UNIKAJ W KAFLI

- ❌ Abstrakcji "na przyszłość" w logice kafli
- ❌ Wzorców projektowych bez konkretnej potrzeby w kafli
- ❌ Przedwczesnej optymalizacji algorytmów kafli
- ❌ Kompleksowych architektur dla prostych procesów kafli
- ❌ Refaktoryzacji działających kafli bez konkretnego powodu
- ❌ Zmian w kafli bez dokładnego testowania thread safety

## ✅ SKUP SIĘ NA KAFLI

- ✅ Rzeczywistych problemach w procesach kafli
- ✅ Bugach w algorytmach kafli (zidentyfikowanych przez analizę)
- ✅ **Bugach w wydajności kafli** (zidentyfikowanych przez analizę)
- ✅ Oczywistych code smells w logice kafli
- ✅ Rzeczach które faktycznie spowalniają kafle
- ✅ **Rzeczach które spowalniają renderowanie kafli** (zidentyfikowanych przez analizę)
- ✅ Bezpieczeństwie danych kafli
- ✅ **Thread safety w komponentach kafli**
- ✅ **Memory leaks w widgetach kafli**

## 🎯 Pytania Kontrolne Kafli

- **Czy to naprawdę problem kafli?** - Nie wymyślaj problemów kafli
- **Czy użytkownicy to odczują w kafli?** - Priorytet dla UX kafli
- **Ile czasu zajmie vs korzyść kafli?** - ROI każdej zmiany kafli
- **Czy można rozwiązać kafle prościej?** - KISS principle w logice kafli
- **Czy kafle będą responsywne?** - Krytyczne dla UX kafli
- **Czy poprawka nie zepsuje thread safety kafli?** - Krytyczne dla stabilności kafli
- **Czy kafle pozostaną responsywne?** - Krytyczne dla UX kafli
- **Czy algorytmy kafli będą wydajne?** - Krytyczne dla procesów kafli

### 📁 STRUKTURA PLIKÓW WYNIKOWYCH KAFLI I UŻYCIE SZABLONÓW

**Kluczem do spójności i efektywności audytu kafli jest używanie przygotowanych szablonów.** Zamiast tworzyć strukturę plików od zera, **należy kopiować i wypełniać** odpowiednie szablony.

**W folderze `_BASE_/` znajdują się szablony:**

- `refactoring_rules.md` - Główne zasady, do których linkują pozostałe dokumenty.
- `correction_template.md` - Szablon dla plików `*_correction_kafli.md`.
- `patch_code_template.md` - Szablon dla plików `*_patch_code_kafli.md`.

**Procedura tworzenia plików wynikowych kafli:**

1. **Dla każdego analizowanego pliku logiki kafli `[nazwa_pliku_kafli].py`:**
   - Skopiuj `_BASE_/correction_template.md` do `AUDYT/KAFLI/corrections/[nazwa_pliku]_correction_kafli.md`.
   - Wypełnij skopiowany plik zgodnie z wynikami analizy logiki kafli.
   - Skopiuj `_BASE_/patch_code_template.md` do `AUDYT/KAFLI/patches/[nazwa_pliku]_patch_code_kafli.md`.
   - Wypełnij plik patch fragmentami kodu z optymalizacjami logiki kafli.

### 🚫 ZASADA INDYWIDUALNEGO GENEROWANIA DOKUMENTÓW KAFLI

**GRUPOWANIE POPRAWEK DLA WIELU PLIKÓW KAFLI JEST NIEDOPUSZCZALNE!**

**OBOWIĄZKOWE ZASADY KAFLI:**

1. **Jeden plik kafli = jeden correction** - Każdy plik `.py` kafli ma SWÓJ plik `[nazwa]_correction_kafli.md`
2. **Jeden plik kafli = jeden patch** - Każdy plik `.py` kafli ma SWÓJ plik `[nazwa]_patch_code_kafli.md`
3. **Brak grupowania kafli** - NIGDY nie łącz analiz wielu plików kafli w jeden dokument
4. **Indywidualne nazwy kafli** - Każdy dokument ma nazwę bazującą na nazwie pliku źródłowego kafli

**PRZYKŁADY POPRAWNEJ STRUKTURY KAFLI:**

```
AUDYT/KAFLI/corrections/
├── file_tile_widget_correction_kafli.md        ✅ Jeden plik kafli
├── tile_manager_correction_kafli.md            ✅ Jeden plik kafli
├── thumbnail_cache_correction_kafli.md         ✅ Jeden plik kafli
└── gallery_manager_correction_kafli.md         ✅ Jeden plik kafli

AUDYT/KAFLI/patches/
├── file_tile_widget_patch_code_kafli.md        ✅ Jeden plik kafli
├── tile_manager_patch_code_kafli.md            ✅ Jeden plik kafli
├── thumbnail_cache_patch_code_kafli.md         ✅ Jeden plik kafli
└── gallery_manager_patch_code_kafli.md         ✅ Jeden plik kafli
```

### 📈 OBOWIĄZKOWA KONTROLA POSTĘPU KAFLI PO KAŻDYM ETAPIE

**🚨 KRYTYCZNE: MODEL MUSI PAMIĘTAĆ O UZUPEŁNIENIU BUSINESS_LOGIC_MAP_KAFLI.MD!**

**MODEL MUSI SPRAWDZIĆ I PODAĆ:**

- **Etapów kafli ukończonych:** X/Y
- **Procent ukończenia kafli:** X%
- **Następny etap kafli:** Nazwa pliku logiki kafli do analizy
- **Business impact kafli:** Wpływ na procesy kafli
- **✅ UZUPEŁNIONO BUSINESS_LOGIC_MAP_KAFLI.MD:** TAK/NIE

**OBOWIĄZKOWE KROKI PO KAŻDYM ETAPIE KAFLI:**

1. ✅ **Ukończ analizę pliku kafli** - utwórz correction_kafli.md i patch_code_kafli.md
2. ✅ **UZUPEŁNIJ business_logic_map_kafli.md** - dodaj status ukończenia kafli
3. ✅ **Sprawdź postęp kafli** - podaj procent ukończenia kafli
4. ✅ **Określ następny etap kafli** - nazwa kolejnego pliku kafli do analizy

**PRZYKŁAD RAPORTU POSTĘPU KAFLI:**

```
📊 POSTĘP AUDYTU LOGIKI KAFLI:
✅ Ukończone etapy kafli: 3/15 (20%)
🔄 Aktualny etap kafli: [NAZWA_PLIKU_KAFLI]
⏳ Pozostałe etapy kafli: 12
💼 Business impact kafli: [OPIS WPŁYWU NA PROCESY KAFLI]
✅ UZUPEŁNIONO BUSINESS_LOGIC_MAP_KAFLI.MD: TAK
```

**🚨 MODEL NIE MOŻE ZAPOMNIEĆ O UZUPEŁNIENIU MAPY KAFLI!**

### ✅ ZAZNACZANIE UKOŃCZONYCH ANALIZ KAFLI W BUSINESS_LOGIC_MAP_KAFLI.MD

**PO KAŻDEJ UKOŃCZONEJ ANALIZIE PLIKU LOGIKI KAFLI:**

1. **Otwórz plik** `AUDYT/KAFLI/business_logic_map_kafli.md`
2. **Znajdź sekcję** z analizowanym plikiem kafli
3. **Dodaj status ukończenia kafli** w formacie:

```markdown
### 📄 [NAZWA_PLIKU_KAFLI].PY

- **Status:** ✅ UKOŃCZONA ANALIZA KAFLI
- **Data ukończenia:** [DATA]
- **Business impact kafli:** [OPIS WPŁYWU NA PROCESY KAFLI]
- **Pliki wynikowe:**
  - `AUDYT/KAFLI/corrections/[nazwa_pliku]_correction_kafli.md`
  - `AUDYT/KAFLI/patches/[nazwa_pliku]_patch_code_kafli.md`
```

### 🚨 WAŻNE: ZASADY DOKUMENTACJI I COMMITÓW KAFLI

**DOKUMENTACJA KAFLI NIE JEST UZUPEŁNIANA W TRAKCIE PROCESU!**

- **CZEKAJ** na wyraźne polecenie użytkownika.
- **DOKUMENTUJ kafle** tylko po pozytywnych testach użytkownika.
- **Commituj kafle** z jasnym komunikatem po zakończeniu etapu.

#### **FORMAT COMMITÓW KAFLI:**

```
git commit -m "TILE UI AUDIT [NUMER]: [NAZWA_PLIKU_KAFLI] - [OPIS] - ZAKOŃCZONY"
```

---

## 🚀 ROZPOCZĘCIE AUDYTU KAFLI

**🚨 OBOWIĄZKOWE KROKI PRZED ROZPOCZĘCIEM AUDYTU KAFLI:**

1. **Zapoznaj się z README.md** - zawiera kluczowe informacje o wymaganiach wydajnościowych kafli (1000+ kafli)
2. **Przeanalizuj strukturę komponentów kafli** - dynamicznie odkryj komponenty kafli
3. **Wygeneruj mapę logiki kafli** - na podstawie analizy kodu i kontekstu kafli z README.md

**Czekam na Twój pierwszy wynik: zawartość pliku `business_logic_map_kafli.md` z mapą plików logiki kafli.**

**UWAGA: Mapa kafli musi być wygenerowana na podstawie analizy aktualnego kodu oraz kontekstu biznesowego kafli z README.md!**

#### **SZCZEGÓŁOWA ANALIZA FUNKCJI KAFLI**

**Dla każdego pliku kafli z priorytetem ⚫⚫⚫⚫ lub 🔴🔴🔴:**

**📄 [NAZWA_PLIKU_KAFLI].PY**

- **Główne funkcje kafli:**
  - `tile_function_name()` - [OPIS ROLI W LOGICE KAFLI]
  - `TileClass.method()` - [OPIS ROLI W LOGICE KAFLI]
- **Priorytet kafli:** [PRIORYTET]
- **Uzasadnienie kafli:** [DLACZEGO TEN PLIK KAFLI MA TAKI PRIORYTET]
- **Wpływ na biznes kafli:** [JAKI MA WPŁYW NA PROCESY KAFLI]

## 🚨 KRYTYCZNE ZASADY KAFLI - MODEL MUSI PAMIĘTAĆ!

### 📋 **OBOWIĄZKOWE UZUPEŁNIANIE BUSINESS_LOGIC_MAP_KAFLI.MD**

**🚨 MODEL MUSI PAMIĘTAĆ: Po każdej ukończonej analizie pliku logiki kafli OBOWIĄZKOWO uzupełnić plik `AUDYT/KAFLI/business_logic_map_kafli.md`!**

**OBOWIĄZKOWE KROKI PO KAŻDEJ ANALIZIE KAFLI:**

1. ✅ **Ukończ analizę pliku kafli** - utwórz correction_kafli.md i patch_code_kafli.md
2. ✅ **OTWÓRZ business_logic_map_kafli.md** - znajdź sekcję z analizowanym plikiem kafli
3. ✅ **DODAJ status ukończenia kafli** - zaznacz że analiza kafli została ukończona
4. ✅ **DODAJ datę ukończenia kafli** - aktualna data w formacie YYYY-MM-DD
5. ✅ **DODAJ business impact kafli** - opis wpływu na procesy kafli
6. ✅ **DODAJ ścieżki do plików wynikowych kafli** - correction_kafli.md i patch_code_kafli.md

**FORMAT UZUPEŁNIENIA W BUSINESS_LOGIC_MAP_KAFLI.MD:**

```markdown
### 📄 [NAZWA_PLIKU_KAFLI].PY

- **Status:** ✅ UKOŃCZONA ANALIZA KAFLI
- **Data ukończenia:** [DATA]
- **Business impact kafli:** [OPIS WPŁYWU NA PROCESY KAFLI]
- **Pliki wynikowe:**
  - `AUDYT/KAFLI/corrections/[nazwa_pliku]_correction_kafli.md`
  - `AUDYT/KAFLI/patches/[nazwa_pliku]_patch_code_kafli.md`
```

**🚨 MODEL NIE MOŻE ZAPOMNIEĆ O TYM KROKU KAFLI!**
