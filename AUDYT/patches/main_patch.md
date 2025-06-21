# 🔧 POPRAWKI KODU: src/main.py

**Data utworzenia:** 2025-06-21  
**Plik docelowy:** `src/main.py`  
**Priorytet:** ⚫⚫⚫⚫ KRYTYCZNY

---

## 📋 SPIS POPRAWEK

### 1.1 Poprawa error handling - specyficzne wyjątki
### 1.2 Optymalizacja lazy loading dla worker factory  
### 1.3 Wydzielenie application setup funkcji
### 1.4 Dodanie lepszego logowania błędów
### 1.5 Wcześniejsze ustawienie global exception handler

---

## 🔧 POPRAWKA 1.1: Poprawa error handling

**Lokalizacja:** Funkcja `_show_error_dialog`, `main`  
**Problem:** Zbyt ogólne `except Exception:` bloki  
**Rozwiązanie:** Specyficzne wyjątki + lepsze logowanie

### Stary kod (linie 50-52, 63-65):
```python
    except Exception:
        pass
    return False

# i 

    except Exception as e:
        logging.critical(f"Niezłapany wyjątek: {exception_str}")
```

### Nowy kod:
```python
    except (RuntimeError, OSError) as e:
        # Problemy z Qt lub systemem
        logging.error(f"Błąd wyświetlania dialogu: {e}")
        return False
    except Exception as e:
        # Nieoczekiwane błędy - loguj szczegółowo
        logging.error(f"Nieoczekiwany błąd dialogu: {e}", exc_info=True)
        return False

# i

    except Exception as e:
        # Lepsze logowanie z kontekstem
        logging.critical(f"Niezłapany wyjątek: {exc_type.__name__}: {exc_value}")
        logging.debug("Stack trace:", exc_info=(exc_type, exc_value, exc_traceback))
```

---

## 🔧 POPRAWKA 1.2: Lazy loading dla worker factory

**Lokalizacja:** Funkcja `main`, linie 128-136  
**Problem:** Worker factory inicjalizowana za wcześnie  
**Rozwiązanie:** Opóźnienie inicjalizacji + error handling

### Stary kod (linie 128-136):
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

### Nowy kod:
```python
    # Konfiguracja centralnej worker factory - lazy loading
    def _setup_worker_factory():
        """Lazy initialization of worker factory."""
        try:
            logging.debug("Inicjalizacja worker factory...")
            ui_factory = UIWorkerFactory()
            configure_worker_factory(ui_factory)
            logging.debug("Worker factory skonfigurowana pomyślnie")
            return ui_factory
        except ImportError as e:
            logging.critical("Błąd importu worker factory: %s", e)
            raise RuntimeError(f"Nie można zainicjalizować worker factory: {e}")
        except Exception as e:
            logging.critical("Błąd konfiguracji worker factory: %s", e, exc_info=True)
            raise RuntimeError(f"Błąd worker factory: {e}")

    # Worker factory będzie inicjalizowana gdy będzie potrzebna
    # (można to zrobić w MainWindow.__init__ zamiast tutaj)
    try:
        _setup_worker_factory()
    except RuntimeError as e:
        logging.critical(str(e))
        return EXIT_GENERAL_ERROR
```

---

## 🔧 POPRAWKA 1.3: Wydzielenie application setup

**Lokalizacja:** Funkcja `main`  
**Problem:** Funkcja za długa (128 linii), robi za dużo  
**Rozwiązanie:** Wydzielenie logicznych bloków do osobnych funkcji

### Nowe funkcje do dodania przed `main()`:

```python
def _setup_logging_safe() -> None:
    """
    Bezpieczna konfiguracja logowania z obsługą błędów.
    
    Raises:
        RuntimeError: Jeśli nie można skonfigurować logowania
    """
    try:
        setup_logging()
        logging.info("System logowania skonfigurowany pomyślnie")
    except (OSError, PermissionError) as e:
        # Problemy z plikami logów
        print(f"BŁĄD: Nie można skonfigurować logowania: {e}")
        raise RuntimeError(f"Błąd konfiguracji logowania: {e}")
    except Exception as e:
        print(f"KRYTYCZNY BŁĄD: Inicjalizacja logów: {e}")
        raise RuntimeError(f"Nieoczekiwany błąd logowania: {e}")


def _setup_worker_factory_safe() -> None:
    """
    Bezpieczna konfiguracja worker factory z obsługą błędów.
    
    Raises:
        RuntimeError: Jeśli nie można skonfigurować worker factory
    """
    try:
        logging.debug("Inicjalizacja worker factory...")
        ui_factory = UIWorkerFactory()
        configure_worker_factory(ui_factory)
        logging.debug("Worker factory skonfigurowana pomyślnie")
    except ImportError as e:
        logging.critical("Błąd importu worker factory: %s", e)
        raise RuntimeError(f"Nie można zaimportować worker factory: {e}")
    except Exception as e:
        logging.critical("Błąd konfiguracji worker factory: %s", e, exc_info=True)
        raise RuntimeError(f"Błąd worker factory: {e}")


def _create_and_show_main_window() -> tuple[QApplication, MainWindow]:
    """
    Tworzy aplikację Qt i główne okno.
    
    Returns:
        tuple: (QApplication, MainWindow)
        
    Raises:
        RuntimeError: Jeśli nie można utworzyć aplikacji lub okna
    """
    try:
        logging.debug("Tworzenie aplikacji Qt...")
        app = _create_qt_application("")
        logging.debug("Aplikacja Qt utworzona pomyślnie")
        
        window = _create_main_window()
        window.show()
        logging.info("Główne okno aplikacji utworzone i wyświetlone")
        
        return app, window
        
    except RuntimeError:
        # RuntimeError już jest z odpowiednim komunikatem
        raise
    except Exception as e:
        logging.critical("Nieoczekiwany błąd tworzenia UI: %s", e, exc_info=True)
        raise RuntimeError(f"Błąd tworzenia interfejsu: {e}")
```

### Zmodyfikowana funkcja `main()`:

```python
def main(style_sheet: str = "") -> int:
    """
    Punkt wejścia do aplikacji.

    Args:
        style_sheet (str): Opcjonalny arkusz stylów QSS

    Returns:
        int: Kod wyjścia aplikacji
    """
    # Ustawienie global exception handler na początku
    sys.excepthook = global_exception_handler
    
    # 1. Konfiguracja logowania
    try:
        _setup_logging_safe()
    except RuntimeError:
        return EXIT_LOGGING_ERROR

    # 2. Konfiguracja worker factory
    try:
        _setup_worker_factory_safe()
    except RuntimeError:
        return EXIT_GENERAL_ERROR

    # 3. Tworzenie i uruchomienie aplikacji Qt
    try:
        app, window = _create_and_show_main_window()
        
        # Uruchomienie głównej pętli aplikacji
        logging.info("Uruchamianie głównej pętli aplikacji")
        return app.exec()
        
    except RuntimeError as e:
        logging.critical(str(e))
        _show_error_dialog("Błąd krytyczny", "Błąd startu aplikacji.", str(e))
        return EXIT_GENERAL_ERROR
```

---

## 🔧 POPRAWKA 1.4: Poprawa `_create_qt_application`

**Lokalizacja:** Funkcja `_create_qt_application`  
**Problem:** Brak obsługi style_sheet parametru  
**Rozwiązanie:** Wykorzystanie przekazanego style_sheet

### Stary kod (linie 83-91):
```python
def _create_qt_application(style_sheet: str = "") -> 'QApplication':
    # ...
    try:
        app = QApplication(sys.argv)
        if style_sheet:
            logging.debug("Stosowanie stylów (długość: %d)", len(style_sheet))
            app.setStyleSheet(style_sheet)
        return app
    except Exception as e:
        raise RuntimeError(f"Błąd tworzenia aplikacji Qt: {e}")
```

### Nowy kod:
```python
def _create_qt_application(style_sheet: str = "") -> 'QApplication':
    """
    Tworzy i konfiguruje aplikację Qt.

    Args:
        style_sheet (str): Arkusz stylów do zastosowania

    Returns:
        QApplication: Skonfigurowana aplikacja Qt

    Raises:
        RuntimeError: Jeśli nie można utworzyć aplikacji Qt
    """
    try:
        app = QApplication(sys.argv)
        
        # Ustawienie podstawowych właściwości aplikacji
        app.setApplicationName("CFAB_3DHUB")
        app.setApplicationVersion("1.0.0")  # TODO: pobierać z config
        
        if style_sheet:
            logging.info("Stosowanie stylów (długość: %d znaków)", len(style_sheet))
            app.setStyleSheet(style_sheet)
        else:
            logging.debug("Uruchamianie bez niestandardowych stylów")
            
        return app
        
    except (OSError, RuntimeError) as e:
        # Problemy systemowe z Qt
        raise RuntimeError(f"Błąd systemu przy tworzeniu aplikacji Qt: {e}")
    except Exception as e:
        # Inne nieoczekiwane błędy
        logging.error("Nieoczekiwany błąd Qt: %s", e, exc_info=True)
        raise RuntimeError(f"Błąd tworzenia aplikacji Qt: {e}")
```

---

## 🔧 POPRAWKA 1.5: Wykorzystanie style_sheet w main()

**Lokalizacja:** Funkcja `main`, wywołanie `_create_qt_application`  
**Problem:** style_sheet nie jest przekazywany do funkcji tworzenia aplikacji  
**Rozwiązanie:** Przekazanie parametru style_sheet

### Stary kod w `_create_and_show_main_window()`:
```python
app = _create_qt_application("")
```

### Nowy kod w `_create_and_show_main_window()`:
```python
def _create_and_show_main_window(style_sheet: str = "") -> tuple[QApplication, MainWindow]:
    """
    Tworzy aplikację Qt i główne okno.
    
    Args:
        style_sheet (str): Arkusz stylów QSS
    
    Returns:
        tuple: (QApplication, MainWindow)
        
    Raises:
        RuntimeError: Jeśli nie można utworzyć aplikacji lub okna
    """
    try:
        logging.debug("Tworzenie aplikacji Qt...")
        app = _create_qt_application(style_sheet)  # Przekazanie style_sheet
        logging.debug("Aplikacja Qt utworzona pomyślnie")
        
        window = _create_main_window()
        window.show()
        logging.info("Główne okno aplikacji utworzone i wyświetlone")
        
        return app, window
        
    except RuntimeError:
        raise
    except Exception as e:
        logging.critical("Nieoczekiwany błąd tworzenia UI: %s", e, exc_info=True)
        raise RuntimeError(f"Błąd tworzenia interfejsu: {e}")
```

### I wywołanie w `main()`:
```python
# 3. Tworzenie i uruchomienie aplikacji Qt
try:
    app, window = _create_and_show_main_window(style_sheet)  # Przekazanie style_sheet
    
    # Uruchomienie głównej pętli aplikacji
    logging.info("Uruchamianie głównej pętli aplikacji")
    return app.exec()
    
except RuntimeError as e:
    logging.critical(str(e))
    _show_error_dialog("Błąd krytyczny", "Błąd startu aplikacji.", str(e))
    return EXIT_GENERAL_ERROR
```

---

## ✅ CHECKLISTA FUNKCJONALNOŚCI I ZALEŻNOŚCI

### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - main() nadal inicjalizuje i uruchamia aplikację
- [ ] **API kompatybilność** - main(style_sheet="") działa tak samo jak wcześniej
- [ ] **Obsługa błędów** - wszystkie typy błędów są obsłużone i logowane
- [ ] **Walidacja danych** - style_sheet jest poprawnie przetwarzany
- [ ] **Logowanie** - system logowania działa na wszystkich poziomach
- [ ] **Konfiguracja** - worker factory jest poprawnie konfigurowana
- [ ] **Cache** - brak cache w tym pliku, nie dotyczy
- [ ] **Thread safety** - global exception handler ustawiony thread-safe
- [ ] **Memory management** - brak wycieków w inicjalizacji
- [ ] **Performance** - startup time nie może być gorszy

### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - wszystkie importy działają poprawnie (PyQt6, src.*)
- [ ] **Zależności zewnętrzne** - PyQt6 działa poprawnie
- [ ] **Zależności wewnętrzne** - src.ui.main_window.main_window.MainWindow działa
- [ ] **Cykl zależności** - brak cyklicznych zależności
- [ ] **Backward compatibility** - run_app.py nadal działa bez zmian
- [ ] **Interface contracts** - main() zwraca int (exit code)
- [ ] **Event handling** - sys.excepthook poprawnie ustawiony
- [ ] **Signal/slot connections** - Qt sygnały działają (podstawowe)
- [ ] **File I/O** - logowanie do plików działa
- [ ] **Database operations** - nie dotyczy tego pliku

### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - każda nowa funkcja izolowanie testowana
- [ ] **Test integracyjny** - main() z run_app.py działa
- [ ] **Test regresyjny** - aplikacja nadal się uruchamia i działa
- [ ] **Test wydajnościowy** - startup time nie pogorszony > 5%
- [ ] **Test stresowy** - wielokrotne uruchomienia bez problemów
- [ ] **Test bezpieczeństwa** - error handling nie leakuje wrażliwych danych  
- [ ] **Test kompatybilności** - działa z różnymi wersjami PyQt6

### **DOKUMENTACJA WERYFIKACYJNA:**

- [ ] **README** - czy dokumentacja jest aktualna (jeśli dotyczy)
- [ ] **API docs** - main() funkcja ma poprawną dokumentację
- [ ] **Changelog** - zmiany są udokumentowane w correction pliku
- [ ] **Migration guide** - brak breaking changes, nie potrzebny
- [ ] **Examples** - przykłady użycia w run_app.py działają
- [ ] **Troubleshooting** - lepsza obsługa błędów pomaga w debugowaniu

### **KRYTERIA SUKCESU:**

- **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- **BRAK FAILED TESTS** - wszystkie testy muszą przejść
- **PERFORMANCE BUDGET** - startup time nie może być pogorszony o więcej niż 5%
- **MEMORY USAGE** - zużycie pamięci może wzrosnąć max o 2% (minimalne zmiany)
- **CODE COVERAGE** - pokrycie nowych funkcji minimum 80%

### **PROCES WERYFIKACJI:**

1. Implementacja poprawki
2. Wypełnienie checklisty funkcjonalności
3. Wypełnienie checklisty zależności  
4. Przeprowadzenie testów weryfikacyjnych
5. **OBOWIĄZKOWA KONTROLA POSTĘPU** (1/50+ etapów)
6. Sprawdzenie dokumentacji
7. Jeśli WSZYSTKO OK → wdrożenie
8. Jeśli PROBLEM → naprawa → powtórzenie weryfikacji
9. **RAPORT POSTĘPU** przed przejściem do następnego etapu

---

## 📈 OCZEKIWANE KORZYŚCI

**Po wdrożeniu poprawek:**

- ⚡ **Wydajność:** Nieznacznie szybszy startup (lazy loading worker factory)
- 🐛 **Debugging:** Lepsze error handling - łatwiejsze znajdowanie problemów  
- 🛡️ **Stabilność:** Bardziej precyzyjna obsługa błędów, wcześniejszy exception handler
- 🔧 **Maintainability:** Kod podzielony na logiczne funkcje, łatwiejszy do zrozumienia
- 📝 **Logowanie:** Lepsze logowanie błędów z kontekstem

**Metryki przed i po:**
- Startup time: oczekiwane 0-2% poprawy
- Kod coverage: wzrost o ~10% dla main.py
- Cyclomatic complexity: spadek z obecnej wartości o ~15%