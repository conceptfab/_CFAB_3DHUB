# 🔧 PATCH CODE: src/main.py

**Plik:** `src/main.py`  
**Priorytet:** ⚫⚫⚫⚫  
**Data:** 2025-06-21

---

## 📋 SEKCJA 2.1: DODANIE TYPE HINTS I IMPORT

**Problem:** Brak type hints dla funkcji

**Obecny kod (linia 1-8):**
```python
"""
Główny moduł aplikacji CFAB_3DHUB.
Zawiera funkcję main() inicjalizującą i uruchamiającą aplikację.
"""

import logging
import sys
import traceback
```

**Poprawka:**
```python
"""
Główny moduł aplikacji CFAB_3DHUB.
Zawiera funkcję main() inicjalizującą i uruchamiającą aplikację.
"""

import logging
import sys
import traceback
from typing import Optional
```

---

## 📋 SEKCJA 2.2: TYPE HINTS DLA FUNKCJI

**Problem:** Brak type hints dla funkcji

**Obecny kod (linia 26):**
```python
def _show_error_dialog(title, message, details=None):
```

**Poprawka:**
```python
def _show_error_dialog(title: str, message: str, details: Optional[str] = None) -> bool:
```

**Obecny kod (linia 54):**
```python
def global_exception_handler(exc_type, exc_value, exc_traceback):
```

**Poprawka:**
```python
def global_exception_handler(exc_type: type, exc_value: BaseException, exc_traceback) -> None:
```

**Obecny kod (linia 69):**
```python
def _create_qt_application(style_sheet=""):
```

**Poprawka:**
```python
def _create_qt_application(style_sheet: str = "") -> 'QApplication':
```

**Obecny kod (linia 92):**
```python
def _create_main_window():
```

**Poprawka:**
```python
def _create_main_window() -> 'MainWindow':
```

**Obecny kod (linia 109):**
```python
def main(style_sheet=""):
```

**Poprawka:**
```python
def main(style_sheet: str = "") -> int:
```

---

## 📋 SEKCJA 2.3: OPTYMALIZACJA LOGOWANIA

**Problem:** Używanie f-string w logowaniu

**Obecny kod (linia 132):**
```python
        logging.critical(f"Błąd konfiguracji worker factory: {e}")
```

**Poprawka:**
```python
        logging.critical("Błąd konfiguracji worker factory: %s", e)
```

**Obecny kod (linia 85):**
```python
            logging.debug("Stosowanie stylów (długość: %d)", len(style_sheet))
```

**To pozostaje bez zmian - już jest zoptymalizowane**

---

## 📋 SEKCJA 2.4: DODANIE DEBUG LOGGING

**Problem:** Brak szczegółowego logowania dla diagnostyki

**Obecny kod (linia 127-133):**
```python
    # Konfiguracja centralnej worker factory
    try:
        ui_factory = UIWorkerFactory()
        configure_worker_factory(ui_factory)
        logging.debug("Worker factory skonfigurowana pomyślnie")
    except Exception as e:
        logging.critical("Błąd konfiguracji worker factory: %s", e)
        return EXIT_GENERAL_ERROR
```

**Poprawka:**
```python
    # Konfiguracja centralnej worker factory
    try:
        logging.debug("Inicjalizacja worker factory...")
        ui_factory = UIWorkerFactory()
        configure_worker_factory(ui_factory)
        logging.debug("Worker factory skonfigurowana pomyślnie")
    except Exception as e:
        logging.critical("Błąd konfiguracji worker factory: %s", e)
        logging.debug("Szczegóły błędu worker factory:", exc_info=True)
        return EXIT_GENERAL_ERROR
```

---

## 📋 SEKCJA 2.5: POPRAWA OBSŁUGI BŁĘDÓW QT

**Problem:** Brak szczegółowej diagnostyki błędów Qt

**Obecny kod (linia 135-141):**
```python
    # Tworzenie aplikacji Qt
    try:
        app = _create_qt_application(style_sheet)
    except RuntimeError as e:
        logging.critical(str(e))
        print(f"BŁĄD KRYTYCZNY: {e}")
        return EXIT_QT_ERROR
```

**Poprawka:**
```python
    # Tworzenie aplikacji Qt
    try:
        logging.debug("Tworzenie aplikacji Qt...")
        app = _create_qt_application(style_sheet)
        logging.debug("Aplikacja Qt utworzona pomyślnie")
    except RuntimeError as e:
        logging.critical("Błąd tworzenia aplikacji Qt: %s", str(e))
        logging.debug("Szczegóły błędu Qt:", exc_info=True)
        print(f"BŁĄD KRYTYCZNY: {e}")
        return EXIT_QT_ERROR
```

---

## ✅ CHECKLISTA FUNKCJONALNOŚCI I ZALEŻNOŚCI

### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - czy aplikacja nadal startuje poprawnie
- [ ] **API kompatybilność** - czy main() function signature pozostaje niezmienione dla run_app.py
- [ ] **Obsługa błędów** - czy mechanizmy obsługi błędów nadal działają
- [ ] **Walidacja danych** - czy setup aplikacji działa poprawnie
- [ ] **Logowanie** - czy system logowania działa bez spamowania
- [ ] **Konfiguracja** - czy worker factory i Qt są konfigurowane poprawnie
- [ ] **Memory management** - czy nie ma wycieków pamięci
- [ ] **Thread safety** - czy inicjalizacja jest bezpieczna
- [ ] **Performance** - czy wydajność nie została pogorszona

### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - czy wszystkie importy działają poprawnie
- [ ] **Zależności zewnętrzne** - czy PyQt6 jest używane prawidłowo
- [ ] **Zależności wewnętrzne** - czy src.* moduły są importowane poprawnie
- [ ] **Worker factory** - czy konfiguracja worker factory działa
- [ ] **Main window** - czy tworzenie głównego okna działa
- [ ] **Exception handling** - czy global exception handler działa
- [ ] **Qt integration** - czy integracja z Qt jest stabilna

### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - czy wszystkie funkcje działają w izolacji
- [ ] **Test integracyjny** - czy integracja z Qt i worker factory działa
- [ ] **Test regresyjny** - czy nie wprowadzono regresji
- [ ] **Test wydajnościowy** - czy wydajność jest akceptowalna
- [ ] **Test startu aplikacji** - czy aplikacja startuje bez błędów
- [ ] **Test obsługi błędów** - czy błędy są prawidłowo obsługiwane

### **KRYTERIA SUKCESU:**

- **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- **BRAK FAILED TESTS** - wszystkie testy muszą przejść
- **PERFORMANCE BUDGET** - wydajność nie może być pogorszona o więcej niż 5%
- **MEMORY USAGE** - użycie pamięci nie może wzrosnąć o więcej niż 10%
- **STARTUP TIME** - czas startu aplikacji nie może wzrosnąć o więcej niż 10%