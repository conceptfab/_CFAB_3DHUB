# PATCH-CODE DLA: run_app.py

**Powiązany plik z analizą:** `../corrections/run_app_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: USUNIĘCIE REDUNDANTNEGO FALLBACK

**Problem:** Redundantny `style_sheet or ""` gdy `_load_application_styles` już zwraca ""
**Rozwiązanie:** Bezpośrednie przekazanie wyniku z _load_application_styles

```python
def run() -> int:
    # ... kod przed linią 84 ...
    
    # Ładowanie stylów
    style_sheet = _load_application_styles(args, _PROJECT_ROOT)

    # Uruchomienie głównej funkcji aplikacji (z opóźnionym importem)
    from src.main import main

    try:
        return main(style_sheet=style_sheet)  # Usunięto "or ''"
    except Exception as e:
        logger.critical("Błąd przy uruchamianiu: %s", str(e))
        logger.debug("Szczegóły błędu:", exc_info=True)
        return EXIT_GENERAL_ERROR
    
    # ... reszta bez zmian ...
```

---

### PATCH 2: SECURITY CLEANUP - USUNIĘCIE WRAŻLIWYCH LOGÓW

**Problem:** `vars(args)` może zawierać wrażliwe dane w logach
**Rozwiązanie:** Usunięcie debug logu z pełnymi argumentami

```python
def _load_application_styles(args: argparse.Namespace, project_root: str) -> str:
    """
    Ładuje style aplikacji na podstawie argumentów CLI.
    """
    logger = logging.getLogger(__name__)

    if args.no_style:
        return ""

    try:
        style_path = get_style_path(project_root, args.style)
        if args.style:
            logger.info("Używanie niestandardowego stylu: %s", args.style)
            # Usunięto: logger.debug("Argumenty stylów: %s", vars(args))

        logger.info("Wczytywanie stylów z: %s", style_path)
        return load_styles(style_path, verbose=True)

    except Exception as e:
        logger.warning("Błąd podczas ładowania stylów: %s", str(e))
        logger.warning("Aplikacja zostanie uruchomiona bez stylów.")
        return ""
```

---

### PATCH 3: REDUKCJA VERBOSITY LOGÓW

**Problem:** Nadmiar debug logów spowalnia startup i zaśmieca logi
**Rozwiązanie:** Usunięcie niepotrzebnych debug logów

```python
def _load_application_styles(args: argparse.Namespace, project_root: str) -> str:
    """
    Ładuje style aplikacji na podstawie argumentów CLI.
    """
    logger = logging.getLogger(__name__)

    if args.no_style:
        return ""

    try:
        style_path = get_style_path(project_root, args.style)
        if args.style:
            logger.info("Używanie niestandardowego stylu: %s", args.style)

        # Usunięto niepotrzebne logi:
        # logger.info("Wczytywanie stylów z: %s", style_path)
        # logger.debug("Sprawdzanie istnienia pliku stylów: %s", os.path.exists(style_path))
        
        return load_styles(style_path, verbose=False)  # Zmieniło się na verbose=False

    except Exception as e:
        logger.warning("Błąd ładowania stylów: %s", str(e))
        logger.info("Uruchamianie bez stylów")  # Krótszy komunikat
        return ""
```

---

### PATCH 4: UPROSZCZENIE ERROR HANDLING

**Problem:** Duplicate error patterns, można uprościć
**Rozwiązanie:** Konsolidacja podobnych bloków try-catch

```python
def run() -> int:
    """
    Uruchamia aplikację z obsługą argumentów linii poleceń i obsługą błędów.
    """
    try:
        # Szybkie sprawdzenie opcji --version dla optymalizacji startu
        if "--version" in sys.argv:
            version = get_app_version()
            print(f"CFAB_3DHUB wersja {version}")
            return EXIT_SUCCESS

        # Parsowanie argumentów i konfiguracja logowania
        args = parse_args()
        setup_logging_from_args(args)
        logger = logging.getLogger(__name__)

        logger.info("Root projektu: %s", _PROJECT_ROOT)

        # Ładowanie stylów i uruchomienie aplikacji
        style_sheet = _load_application_styles(args, _PROJECT_ROOT)
        
        # Opóźniony import i uruchomienie
        from src.main import main
        return main(style_sheet=style_sheet)

    except KeyboardInterrupt:
        print("\nPrzerwano uruchamianie aplikacji.")
        return EXIT_KEYBOARD_INTERRUPT
    
    except Exception as e:
        # Skonsolidowany error handler dla wszystkich błędów
        # Sprawdź czy logger jest dostępny
        try:
            logger = logging.getLogger(__name__)
            logger.critical("Błąd aplikacji: %s", str(e))
            if __debug__:  # Tylko w debug mode
                logger.debug("Szczegóły błędu:", exc_info=True)
        except:
            # Logger niedostępny - fallback do print
            print(f"KRYTYCZNY BŁĄD: {str(e)}")
            if __debug__:
                traceback.print_exc()
        
        return EXIT_GENERAL_ERROR
```

---

### PATCH 5: DODATKOWA OPTYMALIZACJA - LAZY LOGGER

**Problem:** Logger tworzony nawet gdy nie jest potrzebny (np. przy --version)
**Rozwiązanie:** Jeszcze bardziej opóźnione tworzenie loggera

```python
def run() -> int:
    """
    Uruchamia aplikację z obsługą argumentów linii poleceń i obsługą błędów.
    """
    logger = None  # Lazy initialization
    
    try:
        # Szybkie sprawdzenie opcji --version (bez loggera)
        if "--version" in sys.argv:
            version = get_app_version()
            print(f"CFAB_3DHUB wersja {version}")
            return EXIT_SUCCESS

        # Dopiero teraz parsowanie i logging
        args = parse_args()
        setup_logging_from_args(args)
        logger = logging.getLogger(__name__)

        logger.info("Root projektu: %s", _PROJECT_ROOT)

        # Ładowanie stylów i uruchomienie aplikacji
        style_sheet = _load_application_styles(args, _PROJECT_ROOT)
        
        from src.main import main
        return main(style_sheet=style_sheet)

    except KeyboardInterrupt:
        print("\nPrzerwano uruchamianie aplikacji.")
        return EXIT_KEYBOARD_INTERRUPT
    
    except Exception as e:
        # Smart error handling z lazy logger
        if logger:
            logger.critical("Błąd aplikacji: %s", str(e))
            if __debug__:
                logger.debug("Szczegóły błędu:", exc_info=True)
        else:
            print(f"KRYTYCZNY BŁĄD: {str(e)}")
            if __debug__:
                traceback.print_exc()
        
        return EXIT_GENERAL_ERROR
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - aplikacja uruchamia się z wszystkimi argumentami CLI
- [ ] **API kompatybilność** - wszystkie argumenty działają identycznie (--version, --style, --no-style, --help)
- [ ] **Obsługa błędów** - error handling działa we wszystkich scenariuszach
- [ ] **Walidacja danych** - argumenty CLI poprawnie walidowane i przetwarzane
- [ ] **Logowanie** - logi działają bez spamowania, właściwe poziomy
- [ ] **Konfiguracja** - style loading działa z wszystkimi opcjami
- [ ] **Cache** - nie dotyczy run_app.py
- [ ] **Thread safety** - kod single-threaded na tym poziomie
- [ ] **Memory management** - brak memory leaks przy quick --version
- [ ] **Performance** - --version <100ms, pełny start nie wolniejszy

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - wszystkie src.utils importy działają
- [ ] **Zależności zewnętrzne** - stdlib (argparse, logging, os, sys, traceback)
- [ ] **Zależności wewnętrzne** - src.main import działa (lazy loading)
- [ ] **Cykl zależności** - brak (run_app.py to entry point)
- [ ] **Backward compatibility** - pełna kompatybilność CLI interface
- [ ] **Interface contracts** - CLI argumenty niezmienione
- [ ] **Event handling** - KeyboardInterrupt handling OK
- [ ] **Signal/slot connections** - nie dotyczy
- [ ] **File I/O** - style file loading działa

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - test każdej funkcji osobno
- [ ] **Test integracyjny** - pełny flow: CLI → styles → main()
- [ ] **Test regresyjny** - wszystkie kombinacje argumentów działają
- [ ] **Test wydajnościowy** - --version performance, startup time

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - wszystkie CLI scenarios muszą działać
- [ ] **PERFORMANCE BUDGET** - --version <100ms, startup nie wolniejszy
- [ ] **CLI COMPATIBILITY** - 100% backward compatibility dla użytkowników