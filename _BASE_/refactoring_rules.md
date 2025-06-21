# 📜 ZASADY REFAKTORYZACJI, POPRAWEK I TESTOWANIA PROJEKTU CFAB_3DHUB

**Ten dokument zawiera kluczowe zasady, których należy bezwzględnie przestrzegać podczas wszelkich prac refaktoryzacyjnych, wprowadzania poprawek oraz testowania w projekcie. Każdy plik `*_correction.md` musi zawierać odniesienie do tego dokumentu.**

---

## 🏛️ FILARY PRAC

Prace opierają się na trzech kluczowych filarach:

1.  **WYDAJNOŚĆ** ⚡: Optymalizacja czasu, redukcja zużycia pamięci, eliminacja wąskich gardeł.
2.  **STABILNOŚĆ** 🛡️: Niezawodność, proper error handling, thread safety, eliminacja memory leaks i deadlocków.
3.  **WYELIMINOWANIE OVER-ENGINEERING** 🎯: Upraszczanie kodu, eliminacja zbędnych abstrakcji, redukcja zależności, konsolidacja funkcjonalności.

---

## 🛡️ BEZPIECZEŃSTWO REFAKTORYZACJI

**REFAKTORING MUSI BYĆ WYKONANY MAKSYMALNIE BEZPIECZNIE!**

- **BACKUP PRZED KAŻDĄ ZMIANĄ**: Kopia bezpieczeństwa wszystkich modyfikowanych plików w `AUDYT/backups/`.
- **INKREMENTALNE ZMIANY**: Małe, weryfikowalne kroki. Jedna logiczna zmiana = jeden commit.
- **ZACHOWANIE FUNKCJONALNOŚCI**: 100% backward compatibility, zero breaking changes.
- **TESTY NA KAŻDYM ETAPIE**: Obowiązkowe testy automatyczne po każdej zmianie.
- **ROLLBACK PLAN**: Musi istnieć możliwość cofnięcia każdej zmiany.
- **WERYFIKACJA INTEGRACJI**: Sprawdzenie, że zmiana nie psuje innych części systemu.

**Czerwone linie (CZEGO NIE WOLNO ROBIĆ):**

- **NIE USUWAJ** funkcjonalności bez pewności, że jest nieużywana.
- **NIE ZMIENIAJ** publicznych API bez absolutnej konieczności.
- **NIE WPROWADZAJ** breaking changes.
- **NIE REFAKTORYZUJ** bez pełnego zrozumienia kodu.
- **NIE OPTYMALIZUJ** kosztem czytelności i maintainability.
- **NIE ŁĄCZ** wielu zmian w jednym commit.
- **NIE POMIJAJ** testów po każdej zmianie.

---

## 🧪 KRYTYCZNY WYMÓG: AUTOMATYCZNE TESTY

**KAŻDA POPRAWKA MUSI BYĆ PRZETESTOWANA! BRAK TESTÓW = BRAK WDROŻENIA.**

**Proces testowania:**

1.  Implementacja poprawki.
2.  Uruchomienie testów automatycznych (`pytest`).
3.  Analiza wyników (PASS/FAIL). Jeśli FAIL, napraw błędy i powtórz.
4.  Weryfikacja funkcjonalności i zależności.
5.  Dopiero po uzyskaniu PASS można przejść do następnego etapu.

**Wymagane rodzaje testów:**

1.  **Test funkcjonalności podstawowej**: Czy funkcja działa poprawnie.
2.  **Test integracji**: Czy zmiana nie psuje innych części systemu.
3.  **Test wydajności**: Czy zmiana nie spowalnia aplikacji.

**Kryteria sukcesu testów:**

- Wszystkie testy **PASS** (0 FAIL).
- Pokrycie kodu **>80%** dla nowych funkcji.
- Brak regresji w istniejących testach.
- Wydajność nie pogorszona o więcej niż 5%.

---

## 📋 PROCEDURA PRACY NAD ETAPEM

### KROK 1: PRZYGOTOWANIE

- Utwórz backup pliku.
- Przeanalizuj wszystkie zależności (imports, calls).
- Zidentyfikuj publiczne API.
- Przygotuj plan refaktoryzacji z podziałem na małe, weryfikowalne kroki.

### KROK 2: IMPLEMENTACJA

- Implementuj **JEDNĄ** zmianę na raz.
- Zachowaj wszystkie publiczne metody i ich sygnatury (lub dodaj `DeprecationWarning`).
- Zachowaj 100% kompatybilność wsteczną.

### KROK 3: WERYFIKACJA

- Uruchom testy automatyczne po każdej małej zmianie.
- Sprawdź, czy aplikacja się uruchamia i działa poprawnie.
- Sprawdź, czy nie ma błędów importów.
- Sprawdź, czy inne pliki zależne działają.
- Uruchom testy integracyjne i wydajnościowe.

---

## ✅ CHECKLISTA WERYFIKACYJNA

**Każdy plik `patch.md` musi zawierać poniższą checklistę do weryfikacji przed oznaczeniem etapu jako ukończony.**

- **Funkcjonalności:** Podstawowa funkcjonalność, kompatybilność API, obsługa błędów, walidacja, logowanie, cache, thread safety, wydajność.
- **Zależności:** Importy, zależności zewnętrzne i wewnętrzne, brak cyklicznych zależności, kompatybilność wsteczna.
- **Testy:** Jednostkowe, integracyjne, regresyjne, wydajnościowe.
- **Dokumentacja:** Aktualność README, API docs, changelog.

---

## 📊 DOKUMENTACJA I KONTROLA POSTĘPU

- **PROGRESYWNE UZUPEŁNIANIE**: Po każdej analizie pliku **NATYCHMIAST** aktualizuj pliki wynikowe (`code_map.md`, `*_correction.md`, `*_patch.md`).
- **OSOBNE PLIKI**: Każdy analizowany plik musi mieć swój własny `_correction.md` i `_patch.md`.
- **KONTROLA POSTĘPU**: Po każdym etapie raportuj postęp (X/Y ukończonych, %, następny etap).
- **COMMITY**: Commity wykonuj dopiero po pozytywnych testach użytkownika, z jasnym komunikatem, np. `ETAP X: [NAZWA_PLIKU] - [OPIS] - ZAKOŃCZONY`.

**Pamiętaj: Żaden etap nie może być pominięty. Wszystkie etapy muszą być wykonywane sekwencyjnie.**
