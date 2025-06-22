**⚠️ KRYTYCZNE: Przed rozpoczęciem pracy zapoznaj się z ogólnymi zasadami refaktoryzacji, poprawek i testowania opisanymi w pliku [refactoring_rules.md](../_BASE_/refactoring_rules.md).**

---

# 📋 ETAP 2: main.py - ANALIZA I REFAKTORYZACJA

**Data analizy:** 2024-12-22

### 📋 Identyfikacja

- **Plik główny:** `src/main.py`
- **Plik z kodem (patch):** `../patches/main_patch_code.md`
- **Priorytet:** ⚫⚫⚫⚫ KRYTYCZNY
- **Zależności:**
  - `src/utils/logging_config.py`
  - `src/factories/worker_factory.py`
  - `src/logic/file_ops_components.py`
  - `src/ui/main_window/main_window.py`
  - `src/utils/style_loader.py` (przypuszczalnie)

---

### 🔍 Analiza problemów

1. **Błędy krytyczne:**

   - **Nieużywana zmienna `window`** w linii 250 (pylint W0612) - potencjalny memory leak
   - **Brak proper cleanup** głównego okna przy zamykaniu
   - **Hardcoded wersja** w linii 150 - powinno być z configu

2. **Optymalizacje:**

   - **Opóźnione importy** - dobrze zaimplementowane, ale można jeszcze poprawić
   - **Exception handling** - zbyt szczegółowy, można uprościć
   - **Logging** - za dużo debug messages, może spowolnić startup

3. **Refaktoryzacja:**

   - **Podział odpowiedzialności** - funkcja main() robi za dużo (87 linii)
   - **Redundantne try-catch** - można zredukować poziomy zagnieżdżenia
   - **Uproszczenie error handling** - zbyt skomplikowane dla simple case

4. **Logowanie:**
   - **INFO vs DEBUG** - większość logów to DEBUG, ale używa INFO
   - **Nadmiar logów** - każdy krok ma osobny log, może spowolnić startup
   - **Critical vs Error** - inconsistent używanie poziomów

---

### 🛠️ PLAN REFAKTORYZACJI

**Typ refaktoryzacji:** Optymalizacja kodu + Cleanup

#### KROK 1: PRZYGOTOWANIE 🛡️

- [ ] **BACKUP UTWORZONY:** `main_backup_20241222.py` w folderze `AUDYT/backups/`
- [ ] **ANALIZA ZALEŻNOŚCI:** Sprawdzenie imports - wszystkie używane przez run_app.py
- [ ] **IDENTYFIKACJA API:** Publiczne API: `main()` - używane przez run_app.py
- [ ] **PLAN ETAPOWY:** 4 kroki - cleanup, optymalizacja, refactor, test

#### KROK 2: IMPLEMENTACJA 🔧

- [ ] **ZMIANA 1:** Usunięcie nieużywanej zmiennej `window` (linia 250)
- [ ] **ZMIANA 2:** Pobranie wersji z config zamiast hardcode
- [ ] **ZMIANA 3:** Redukcja debug logów do niezbędnego minimum
- [ ] **ZMIANA 4:** Uproszczenie error handling (merge podobnych bloków)
- [ ] **ZACHOWANIE API:** Publiczne API `main(style_sheet)` zachowane w 100%
- [ ] **BACKWARD COMPATIBILITY:** Pełna kompatybilność z run_app.py

#### KROK 3: WERYFIKACJA PO KAŻDEJ ZMIANIE 🧪

- [ ] **TESTY AUTOMATYCZNE:** Sprawdzenie czy import działa
- [ ] **URUCHOMIENIE APLIKACJI:** Test przez run_app.py
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI:** Sprawdzenie pełnego startup flow

#### KROK 4: INTEGRACJA FINALNA 🔗

- [ ] **TESTY INNYCH PLIKÓW:** Sprawdzenie run_app.py
- [ ] **TESTY INTEGRACYJNE:** Pełny test uruchomienia aplikacji
- [ ] **TESTY WYDAJNOŚCIOWE:** Pomiar czasu startup (powinien być szybszy)

#### KRYTERIA SUKCESU REFAKTORYZACJI ✅

- [ ] **WSZYSTKIE TESTY PASS** - aplikacja się uruchamia
- [ ] **APLIKACJA URUCHAMIA SIĘ** - bez żadnych błędów
- [ ] **FUNKCJONALNOŚĆ ZACHOWANA** - identyczny behavior jak przed zmianą
- [ ] **KOMPATYBILNOŚĆ WSTECZNA** - API main() niezmienione

---

### 🧪 PLAN TESTÓW AUTOMATYCZNYCH

**Test funkcjonalności podstawowej:**

- Import src.main bez błędów
- Wywołanie main() z pustym style_sheet
- Sprawdzenie zwracanych kodów wyjścia

**Test integracji:**

- Test przez run_app.py - pełny startup flow
- Test error handling - symulacja błędów w każdym kroku

**Test wydajności:**

- Pomiar czasu startup aplikacji (baseline vs po zmianach)
- Sprawdzenie czy nie ma dodatkowych memory leaks

---

### 📊 STATUS TRACKING

- [ ] Backup utworzony
- [ ] Plan refaktoryzacji przygotowany ✅
- [ ] Kod zaimplementowany (krok po kroku)
- [ ] Testy podstawowe przeprowadzone (PASS)
- [ ] Testy integracji przeprowadzone (PASS)
- [ ] **WERYFIKACJA FUNKCJONALNOŚCI** - ręczne sprawdzenie startup
- [ ] **WERYFIKACJA ZALEŻNOŚCI** - sprawdzenie czy run_app.py działa
- [ ] **WERYFIKACJA WYDAJNOŚCI** - startup time comparison
- [ ] Dokumentacja zaktualizowana (jeśli potrzebne)
- [ ] **Gotowe do wdrożenia**

---

### 📝 DODATKOWE UWAGI

**Pozytywne aspekty:**
- Bardzo dobry error handling
- Proper separation of concerns w funkcjach pomocniczych
- Dobrze zaimplementowane lazy loading
- Czytelny kod z dobrą dokumentacją

**Do poprawy:**
- Redukcja verbosity w logach
- Cleanup nieużywanych zmiennych
- Pobranie wersji z config