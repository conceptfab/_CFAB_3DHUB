# PATCH-CODE DLA: app_config.py

**Powiązany plik z analizą:** `../corrections/app_config_correction.md`
**Zasady ogólne:** `../refactoring_rules.md`

---

### PATCH 1: USUNIĘCIE NIEUŻYWANEGO IMPORTU

**Problem:** Nieużywany import `from typing import Any` (pylint F401)
**Rozwiązanie:** Usunięcie linii 14

```python
# src/app_config.py
"""
🚀 ETAP 2: Zrefaktoryzowany AppConfig - backward compatibility wrapper
Oryginalny plik został podzielony na komponenty w src/config/

Struktura komponentów:
- config_core.py - główna klasa AppConfig
- config_defaults.py - domyślne wartości
- config_validator.py - walidacja
- config_io.py - operacje I/O
- config_properties.py - właściwości i gettery/settery
"""

from typing import Dict, List  # Usunięto Any

# Import głównej klasy z nowego pakietu
from src.config import AppConfig

# ... reszta kodu bez zmian ...
```

---

### PATCH 2: OPTYMALIZACJA - CACHE CONFIG INSTANCE

**Problem:** `AppConfig.get_instance()` wywoływane wielokrotnie - performance overhead
**Rozwiązanie:** Cache instancji na poziomie modułu

```python
# Import głównej klasy z nowego pakietu
from src.config import AppConfig

# Cache instancji config dla lepszej wydajności
_config_instance = AppConfig.get_instance()

# --- Legacy global functions (backward compatibility) ---

def set_thumbnail_slider_position(position: int) -> bool:
    """Legacy function for backward compatibility."""
    return _config_instance.set_thumbnail_slider_position(position)


def get_supported_extensions(extension_type: str) -> List[str]:
    """Legacy function for backward compatibility."""
    return _config_instance.get_supported_extensions(extension_type)


def get_predefined_colors() -> Dict[str, str]:
    """Legacy function for backward compatibility."""
    return _config_instance.get_predefined_colors()


def set_predefined_colors(colors: Dict[str, str]) -> bool:
    """Legacy function for backward compatibility."""
    return _config_instance.set_predefined_colors(colors)


# --- Thumbnail format legacy functions ---

def get_thumbnail_format() -> str:
    """Legacy function for backward compatibility."""
    return _config_instance.get_thumbnail_format()


def set_thumbnail_format(format_name: str) -> bool:
    """Legacy function for backward compatibility."""
    return _config_instance.set_thumbnail_format(format_name)


def get_thumbnail_quality() -> int:
    """Legacy function for backward compatibility."""
    return _config_instance.get_thumbnail_quality()


def set_thumbnail_quality(quality: int) -> bool:
    """Legacy function for backward compatibility."""
    return _config_instance.set_thumbnail_quality(quality)
```

---

### PATCH 3: CONDITIONAL REMOVAL OF UNUSED CONSTANTS

**Problem:** MIN_THUMBNAIL_SIZE i MAX_THUMBNAIL_SIZE prawdopodobnie nieużywane (vulture 60%)
**Rozwiązanie:** Komentowanie z możliwością przywrócenia po weryfikacji

```python
# --- Legacy constants for backward compatibility ---
# Używanie cached instance
SUPPORTED_ARCHIVE_EXTENSIONS = _config_instance.supported_archive_extensions
SUPPORTED_PREVIEW_EXTENSIONS = _config_instance.supported_preview_extensions
PREDEFINED_COLORS_FILTER = _config_instance.predefined_colors_filter

# TODO: Weryfikacja czy te constants są używane (vulture 60% confidence unused)
# MIN_THUMBNAIL_SIZE = _config_instance.min_thumbnail_size
# MAX_THUMBNAIL_SIZE = _config_instance.max_thumbnail_size

DEFAULT_THUMBNAIL_SIZE = _config_instance.default_thumbnail_size

# Parametry cache dla skanera
SCANNER_MAX_CACHE_ENTRIES = _config_instance.scanner_max_cache_entries
SCANNER_MAX_CACHE_AGE_SECONDS = _config_instance.scanner_max_cache_age_seconds

# Parametry timerów - standaryzacja pattern
resize_timer_delay_ms = _config_instance.get("resize_timer_delay_ms", 150)
```

---

### PATCH 4: DODANIE DEPRECATION WARNINGS (OPCJONALNIE)

**Problem:** Legacy functions bez informacji o deprecation
**Rozwiązanie:** Dodanie optional deprecation warnings dla przyszłego cleanup

```python
import warnings
from typing import Dict, List

# Import głównej klasy z nowego pakietu
from src.config import AppConfig

# Cache instancji config dla lepszej wydajności
_config_instance = AppConfig.get_instance()

# --- Legacy global functions (backward compatibility) ---

def set_thumbnail_slider_position(position: int) -> bool:
    """
    Legacy function for backward compatibility.
    
    Note: Consider using AppConfig.get_instance().set_thumbnail_slider_position() directly.
    """
    # Opcjonalnie można dodać w przyszłości:
    # warnings.warn("set_thumbnail_slider_position is deprecated, use AppConfig directly", 
    #               DeprecationWarning, stacklevel=2)
    return _config_instance.set_thumbnail_slider_position(position)

# ... podobnie dla pozostałych legacy functions ...
```

---

### PATCH 5: BACKWARD COMPATIBILITY VALIDATOR (DEFENSIVE)

**Problem:** Brak weryfikacji czy legacy constants są faktycznie dostępne
**Rozwiązanie:** Defensive programming z fallback values

```python
# --- Legacy constants for backward compatibility ---
# Defensive programming - sprawdzenie dostępności atrybutów
try:
    SUPPORTED_ARCHIVE_EXTENSIONS = _config_instance.supported_archive_extensions
    SUPPORTED_PREVIEW_EXTENSIONS = _config_instance.supported_preview_extensions
    PREDEFINED_COLORS_FILTER = _config_instance.predefined_colors_filter
    DEFAULT_THUMBNAIL_SIZE = _config_instance.default_thumbnail_size
    SCANNER_MAX_CACHE_ENTRIES = _config_instance.scanner_max_cache_entries
    SCANNER_MAX_CACHE_AGE_SECONDS = _config_instance.scanner_max_cache_age_seconds
except AttributeError as e:
    # Fallback values jeśli config nie ma wymaganych atrybutów
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("Config attribute missing: %s, using fallback values", e)
    
    SUPPORTED_ARCHIVE_EXTENSIONS = ['.blend', '.zip', '.7z']
    SUPPORTED_PREVIEW_EXTENSIONS = ['.jpg', '.png', '.webp']
    PREDEFINED_COLORS_FILTER = {}
    DEFAULT_THUMBNAIL_SIZE = 150
    SCANNER_MAX_CACHE_ENTRIES = 1000
    SCANNER_MAX_CACHE_AGE_SECONDS = 3600

# Parametry timerów z error handling
try:
    resize_timer_delay_ms = _config_instance.get("resize_timer_delay_ms", 150)
except Exception:
    resize_timer_delay_ms = 150  # Safe fallback
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - wszystkie legacy functions działają identycznie
- [ ] **API kompatybilność** - każda legacy function zwraca te same wartości co wcześniej
- [ ] **Obsługa błędów** - error handling w legacy functions zachowany
- [ ] **Walidacja danych** - parametry legacy functions poprawnie walidowane
- [ ] **Logowanie** - brak logowania w legacy functions (zachowane zachowanie)
- [ ] **Konfiguracja** - inicjalizacja config instance działa poprawnie
- [ ] **Cache** - cache instancji działa i poprawia performance
- [ ] **Thread safety** - singleton pattern thread-safe (delegowane do AppConfig)
- [ ] **Memory management** - cache nie powoduje memory leaks
- [ ] **Performance** - lepszy performance dzięki cache

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - import src.config działa poprawnie
- [ ] **Zależności zewnętrzne** - typing imports OK
- [ ] **Zależności wewnętrzne** - wszystkie moduły importujące app_config działają
- [ ] **Cykl zależności** - brak cykli (app_config importowany przez wiele modułów)
- [ ] **Backward compatibility** - 100% kompatybilność dla legacy code
- [ ] **Interface contracts** - wszystkie legacy signatures zachowane
- [ ] **Event handling** - nie dotyczy bezpośrednio
- [ ] **Signal/slot connections** - nie dotyczy
- [ ] **File I/O** - delegowane do AppConfig

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - każda legacy function + każdy constant
- [ ] **Test integracyjny** - import przez inne moduły
- [ ] **Test regresyjny** - porównanie values przed/po zmianie
- [ ] **Test wydajności** - startup time + legacy function call time

#### **SPECJALNE TESTY DLA APP_CONFIG:**

- [ ] **Test cache performance** - wielokrotne wywołania legacy functions
- [ ] **Test constants availability** - wszystkie legacy constants dostępne
- [ ] **Test fallback behavior** - zachowanie przy błędach config
- [ ] **Test mixed usage** - kombinacja legacy functions + direct AppConfig usage

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- [ ] **BRAK FAILED TESTS** - wszystkie legacy functions muszą działać
- [ ] **PERFORMANCE BUDGET** - startup lepszy dzięki cache, legacy functions nie wolniejsze
- [ ] **BACKWARD COMPATIBILITY** - 100% zgodność z istniejącym kodem