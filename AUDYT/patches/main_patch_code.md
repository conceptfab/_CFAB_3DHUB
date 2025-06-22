# PATCH-CODE DLA: main.py

**Powiązany plik z analizą:** `../corrections/main_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: USUNIĘCIE NIEUŻYWANEJ ZMIENNEJ WINDOW

**Problem:** Nieużywana zmienna `window` w linii 250 (pylint W0612) - potencjalny memory leak
**Rozwiązanie:** Użycie zmiennej window dla proper cleanup przy błędach

```python
def main(style_sheet: str = "") -> int:
    # ... kod przed linią 248 ...
    
    # 3. Tworzenie i uruchomienie aplikacji Qt
    try:
        app, window = _create_and_show_main_window(style_sheet)
        
        # Zapewnienie proper cleanup przy błędach
        try:
            # Uruchomienie głównej pętli aplikacji
            logging.info("Uruchamianie głównej pętli aplikacji")
            return app.exec()
        except Exception as e:
            # Cleanup okna przy błędach w głównej pętli
            logging.error("Błąd w głównej pętli aplikacji: %s", e)
            if window:
                window.close()
            raise
    
    except RuntimeError as e:
        logging.critical(str(e))
        _show_error_dialog("Błąd krytyczny", "Błąd startu aplikacji.", str(e))
        return EXIT_GENERAL_ERROR
```

---

### PATCH 2: POBRANIE WERSJI Z CONFIG

**Problem:** Hardcoded wersja "1.0.0" w linii 150 - TODO do zrealizowania
**Rozwiązanie:** Dodanie funkcji pobierającej wersję z config z fallback

```python
def _get_application_version() -> str:
    """
    Pobiera wersję aplikacji z konfiguracji z fallback na domyślną.
    
    Returns:
        str: Wersja aplikacji
    """
    try:
        from src.app_config import AppConfig
        config = AppConfig()
        return getattr(config, 'application_version', '1.0.0')
    except (ImportError, AttributeError):
        return '1.0.0'


def _create_qt_application(style_sheet: str = "") -> "QApplication":
    """
    Tworzy i konfiguruje aplikację Qt.
    """
    try:
        app = QApplication(sys.argv)

        # Ustawienie podstawowych właściwości aplikacji
        app.setApplicationName("CFAB_3DHUB")
        app.setApplicationVersion(_get_application_version())  # Pobieranie z config

        if style_sheet:
            log_msg = f"Stosowanie stylów (długość: {len(style_sheet)} znaków)"
            logging.info(log_msg)
            app.setStyleSheet(style_sheet)
        else:
            logging.debug("Uruchamianie bez niestandardowych stylów")

        return app
    
    # ... reszta kodu bez zmian ...
```

---

### PATCH 3: REDUKCJA VERBOSITY LOGÓW

**Problem:** Zbyt dużo debug logów może spowolnić startup
**Rozwiązanie:** Uproszczenie logowania do niezbędnego minimum

```python
def _setup_logging_safe() -> None:
    """
    Bezpieczna konfiguracja logowania z obsługą błędów.
    """
    try:
        from src.utils.logging_config import setup_logging
        setup_logging()
        logging.info("System logowania skonfigurowany")  # Usunięto "pomyślnie"
    except (OSError, PermissionError) as e:
        print(f"BŁĄD: Nie można skonfigurować logowania: {e}")
        raise RuntimeError(f"Błąd konfiguracji logowania: {e}")
    except Exception as e:
        print(f"KRYTYCZNY BŁĄD: Inicjalizacja logów: {e}")
        raise RuntimeError(f"Nieoczekiwany błąd logowania: {e}")


def _setup_worker_factory_safe() -> None:
    """
    Bezpieczna konfiguracja worker factory z obsługą błędów.
    """
    try:
        from src.factories.worker_factory import UIWorkerFactory
        from src.logic.file_ops_components import configure_worker_factory

        ui_factory = UIWorkerFactory()
        configure_worker_factory(ui_factory)
        # Usunięto debug logi - niepotrzebne przy każdym starcie
    except ImportError as e:
        logging.critical("Błąd importu worker factory: %s", e)
        raise RuntimeError(f"Nie można zaimportować worker factory: {e}")
    except Exception as e:
        logging.critical("Błąd konfiguracji worker factory: %s", e, exc_info=True)
        raise RuntimeError(f"Błąd worker factory: {e}")


def _create_and_show_main_window(style_sheet: str = "") -> tuple["QApplication", "MainWindow"]:
    """
    Tworzy aplikację Qt i główne okno.
    """
    try:
        app = _create_qt_application(style_sheet)
        window = _create_main_window()
        window.show()
        logging.info("Aplikacja gotowa")  # Uproszczony log
        return app, window
    
    # ... reszta bez zmian ...
```

---

### PATCH 4: UPROSZCZENIE ERROR HANDLING

**Problem:** Redundantne try-catch bloki zwiększają złożoność
**Rozwiązanie:** Merge podobnych bloków error handling

```python
def _create_qt_application(style_sheet: str = "") -> "QApplication":
    """
    Tworzy i konfiguruje aplikację Qt.
    """
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("CFAB_3DHUB")
        app.setApplicationVersion(_get_application_version())

        if style_sheet:
            logging.info("Stosowanie stylów (%d znaków)", len(style_sheet))
            app.setStyleSheet(style_sheet)

        return app

    except Exception as e:
        # Merge różnych typów błędów Qt w jeden handler
        logging.error("Błąd tworzenia aplikacji Qt: %s", e, exc_info=True)
        raise RuntimeError(f"Błąd tworzenia aplikacji Qt: {e}")
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - aplikacja się uruchamia i wyświetla główne okno
- [ ] **API kompatybilność** - funkcja main(style_sheet) działa identycznie
- [ ] **Obsługa błędów** - wszystkie error handlers działają poprawnie
- [ ] **Walidacja danych** - style_sheet parameter poprawnie przetwarzany
- [ ] **Logowanie** - logi są zapisywane bez spamowania
- [ ] **Konfiguracja** - wersja aplikacji pobierana z config z fallback
- [ ] **Cache** - nie dotyczy tego pliku
- [ ] **Thread safety** - kod głównego wątku aplikacji
- [ ] **Memory management** - proper cleanup okna przy błędach
- [ ] **Performance** - startup nie wolniejszy (powinien być szybszy)

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - wszystkie importy działają (logging_config, worker_factory, etc.)
- [ ] **Zależności zewnętrzne** - PyQt6 importy działają
- [ ] **Zależności wewnętrzne** - src.utils, src.factories, src.ui importy OK
- [ ] **Cykl zależności** - brak cykli (main.py jest entry point)
- [ ] **Backward compatibility** - pełna kompatybilność z run_app.py
- [ ] **Interface contracts** - main() signature niezmieniony
- [ ] **Event handling** - Qt event loop działa poprawnie
- [ ] **Signal/slot connections** - nie dotyczy bezpośrednio main.py
- [ ] **File I/O** - nie dotyczy bezpośrednio main.py

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - import main + wywołanie main() z różnymi parametrami
- [ ] **Test integracyjny** - test przez run_app.py - pełny workflow
- [ ] **Test regresyjny** - porównanie behavior przed i po zmianach
- [ ] **Test wydajnościowy** - pomiar startup time (powinien być lepszy)

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - aplikacja musi się uruchomić bez błędów
- [ ] **PERFORMANCE BUDGET** - startup time nie gorszy (lepiej jeśli szybszy)
- [ ] **CODE COVERAGE** - nie dotyczy (main.py to entry point, nie ma testów unit)