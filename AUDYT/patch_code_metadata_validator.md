# 🔧 FRAGMENTY KODU - METADATA_VALIDATOR PATCHES

## 1. KRYTYCZNE POPRAWKI

### 1.1 Dodanie walidacji zakresu wartości stars

```python
# DODAĆ PO LINII 86 i 134
def _validate_stars_range(self, stars_value: int) -> bool:
    """Sprawdza czy wartość stars jest w poprawnym zakresie 0-5."""
    if not (0 <= stars_value <= 5):
        logger.debug(f"Wartość 'stars' poza zakresem 0-5: {stars_value}")
        return False
    return True
```

### 1.2 Poprawa walidacji typu stars z kontrolą zakresu

```python
# ZAMIENIĆ LINIE 86-90
if not isinstance(pair_metadata["stars"], int) or not self._validate_stars_range(pair_metadata["stars"]):
    logger.debug(
        f"Wartość 'stars' dla '{relative_path}' nie jest poprawną liczbą całkowitą (0-5): {pair_metadata['stars']}"
    )
    return False
```

```python
# ZAMIENIĆ LINIE 134-138
if not isinstance(pair_metadata["stars"], int) or not self._validate_stars_range(pair_metadata["stars"]):
    logger.debug(
        f"Wartość 'stars' nie jest poprawną liczbą całkowitą (0-5): {pair_metadata['stars']}"
    )
    return False
```

### 1.3 Dodanie walidacji długości i znaków specjalnych w nazwach plików

```python
# DODAĆ JAKO NOWE METODY KLASY
@staticmethod
def _validate_filename_length(filename: str, max_length: int = 255) -> bool:
    """Sprawdza czy nazwa pliku nie przekracza maksymalnej długości."""
    if len(filename) > max_length:
        logger.debug(f"Nazwa pliku przekracza maksymalną długość {max_length}: {len(filename)} znaków")
        return False
    return True

@staticmethod  
def _validate_filename_characters(filename: str) -> bool:
    """Sprawdza czy nazwa pliku zawiera tylko dozwolone znaki."""
    import re
    # Znaki niedozwolone w większości systemów plików
    forbidden_chars = r'[<>:"|?*\x00-\x1f]'
    if re.search(forbidden_chars, filename):
        logger.debug(f"Nazwa pliku zawiera niedozwolone znaki: {filename}")
        return False
    return True
```

### 1.4 Zintegrowana walidacja nazw plików w głównej metodzie

```python
# DODAĆ PO LINII 70 (w pętli file_pairs)
# Walidacja nazwy pliku
if not self._validate_filename_length(relative_path) or not self._validate_filename_characters(relative_path):
    logger.debug(f"Niepoprawna nazwa pliku: {relative_path}")
    return False
```

### 1.5 Zmiana poziomu logowania z warning na debug

```python
# ZAMIENIĆ WSZYSTKIE logger.warning NA logger.debug W NASTĘPUJĄCYCH LINIACH:
# Linia 38: logger.debug(f"Brak wymaganego klucza '{key}' w metadanych.")
# Linia 45: logger.debug("Klucz 'has_special_folders' nie jest wartością logiczną (bool).")
# Linia 52: logger.debug("Klucz 'file_pairs' nie jest słownikiem.")
# Linia 56: logger.debug("Klucz 'unpaired_archives' nie jest listą.")
# Linia 60: logger.debug("Klucz 'unpaired_previews' nie jest listą.")
# Linia 68: logger.debug("Klucz '__metadata__' nie jest słownikiem.")
# Linia 74: logger.debug(f"Metadane dla '{relative_path}' nie są słownikiem: {pair_metadata}")
# Linia 80: logger.debug(f"Metadane dla '{relative_path}' nie zawierają wymaganych kluczy 'stars' lub 'color_tag'.")
# Linia 97: logger.debug(f"Wartość 'color_tag' dla '{relative_path}' nie jest ciągiem znaków ani None: {pair_metadata['color_tag']}")
# Linia 123: logger.debug(f"Metadane pary nie są słownikiem: {pair_metadata}")
# Linia 128: logger.debug("Metadane pary nie zawierają wymaganych kluczy 'stars' lub 'color_tag'.")
# Linia 144: logger.debug(f"Wartość 'color_tag' nie jest ciągiem znaków ani None: {pair_metadata['color_tag']}")
```

## 2. WYSOKIE POPRAWKI

### 2.1 Refaktoryzacja duplikacji kodu - wspólna metoda walidacji pary

```python
# DODAĆ JAKO NOWĄ METODĘ KLASY
@staticmethod
def _validate_pair_data_structure(pair_metadata: Dict[str, Any], context: str = "") -> bool:
    """
    Wspólna metoda walidacji struktury danych pary plików.
    
    Args:
        pair_metadata: Słownik metadanych pary plików
        context: Kontekst dla komunikatów błędów
    
    Returns:
        bool: True jeśli struktura jest poprawna
    """
    try:
        if not isinstance(pair_metadata, dict):
            logger.debug(f"Metadane pary nie są słownikiem{context}: {pair_metadata}")
            return False

        # Sprawdzenie wymaganych kluczy
        if "stars" not in pair_metadata or "color_tag" not in pair_metadata:
            logger.debug(f"Metadane pary nie zawierają wymaganych kluczy 'stars' lub 'color_tag'{context}")
            return False

        # Sprawdzenie typów i zakresów wartości
        if not isinstance(pair_metadata["stars"], int) or not (0 <= pair_metadata["stars"] <= 5):
            logger.debug(f"Wartość 'stars' nie jest poprawną liczbą całkowitą (0-5){context}: {pair_metadata['stars']}")
            return False

        if not (isinstance(pair_metadata["color_tag"], str) or pair_metadata["color_tag"] is None):
            logger.debug(f"Wartość 'color_tag' nie jest ciągiem znaków ani None{context}: {pair_metadata['color_tag']}")
            return False

        return True

    except Exception as e:
        logger.error(f"Błąd podczas walidacji metadanych pary{context}: {e}", exc_info=True)
        return False
```

### 2.2 Uproszczenie metody validate_metadata_structure z użyciem wspólnej metody

```python
# ZAMIENIĆ LINIE 78-100
# Sprawdzenie struktury file_pairs
for relative_path, pair_metadata in metadata["file_pairs"].items():
    # Specjalny klucz __metadata__ może zawierać inne dane
    if relative_path == "__metadata__":
        if not isinstance(pair_metadata, dict):
            logger.debug("Klucz '__metadata__' nie jest słownikiem.")
            return False
        continue

    # Walidacja nazwy pliku
    if not self._validate_filename_length(relative_path) or not self._validate_filename_characters(relative_path):
        logger.debug(f"Niepoprawna nazwa pliku: {relative_path}")
        return False

    # Walidacja struktury metadanych pary
    if not self._validate_pair_data_structure(pair_metadata, f" dla '{relative_path}'"):
        return False
```

### 2.3 Uproszczenie metody validate_file_pair_metadata

```python
# ZAMIENIĆ LINIE 121-153
@staticmethod
def validate_file_pair_metadata(pair_metadata: Dict[str, Any]) -> bool:
    """
    Waliduje metadane pojedynczej pary plików.

    Args:
        pair_metadata: Słownik metadanych pary plików

    Returns:
        bool: True jeśli metadane są poprawne
    """
    return MetadataValidator._validate_pair_data_structure(pair_metadata)
```

## 3. ŚREDNIE POPRAWKI

### 3.1 Konfigurowalność reguł walidacji

```python
# DODAĆ NA POCZĄTKU KLASY
class MetadataValidator:
    """
    Walidacja struktury metadanych.
    Sprawdza poprawność struktury i typów danych w metadanych.
    """
    
    # Domyślne reguły walidacji - konfigurowalne
    DEFAULT_RULES = {
        'required_keys': ['file_pairs', 'unpaired_archives', 'unpaired_previews'],
        'optional_keys': ['has_special_folders'],
        'stars_range': {'min': 0, 'max': 5},
        'filename_max_length': 255,
        'filename_forbidden_chars': r'[<>:"|?*\x00-\x1f]'
    }
    
    def __init__(self, validation_rules: Dict[str, Any] = None):
        """
        Inicjalizuje validator z opcjonalnymi regułami.
        
        Args:
            validation_rules: Niestandardowe reguły walidacji
        """
        self.rules = {**self.DEFAULT_RULES, **(validation_rules or {})}
```

### 3.2 Cache'owanie wyników walidacji

```python
# DODAĆ DO KLASY
from functools import lru_cache
import hashlib
import json

def _get_metadata_hash(self, metadata: Dict[str, Any]) -> str:
    """Generuje hash metadanych dla cache'owania."""
    return hashlib.md5(json.dumps(metadata, sort_keys=True).encode()).hexdigest()

@lru_cache(maxsize=1000)
def _cached_validate_structure(self, metadata_hash: str, metadata_str: str) -> bool:
    """Cache'owana walidacja struktury metadanych."""
    metadata = json.loads(metadata_str)
    return self._internal_validate_metadata_structure(metadata)
```

## 4. KOMPLETNA ZREFAKTORYZOWANA WERSJA

### 4.1 Nagłówek pliku z dodanymi importami

```python
"""
Komponent walidacji metadanych CFAB_3DHUB.
🚀 ETAP 4: Refaktoryzacja MetadataValidator - poprawa wydajności i funkcjonalności
"""

import logging
import re
import hashlib
import json
from typing import Any, Dict
from functools import lru_cache

logger = logging.getLogger(__name__)
```

### 4.2 Definicja klasy z konfiguracją

```python
class MetadataValidator:
    """
    Walidacja struktury metadanych z konfigurowalnymi regułami i cache'owaniem.
    Sprawdza poprawność struktury i typów danych w metadanych.
    """
    
    # Domyślne reguły walidacji
    DEFAULT_RULES = {
        'required_keys': ['file_pairs', 'unpaired_archives', 'unpaired_previews'],
        'optional_keys': ['has_special_folders'],
        'stars_range': {'min': 0, 'max': 5},
        'filename_max_length': 255,
        'filename_forbidden_chars': r'[<>:"|?*\x00-\x1f]'
    }
    
    def __init__(self, validation_rules: Dict[str, Any] = None):
        """
        Inicjalizuje validator z opcjonalnymi regułami.
        
        Args:
            validation_rules: Niestandardowe reguły walidacji
        """
        self.rules = {**self.DEFAULT_RULES, **(validation_rules or {})}
```

### 4.3 Metody pomocnicze

```python
def _validate_stars_range(self, stars_value: int) -> bool:
    """Sprawdza czy wartość stars jest w poprawnym zakresie."""
    min_stars = self.rules['stars_range']['min']
    max_stars = self.rules['stars_range']['max']
    if not (min_stars <= stars_value <= max_stars):
        logger.debug(f"Wartość 'stars' poza zakresem {min_stars}-{max_stars}: {stars_value}")
        return False
    return True

def _validate_filename_length(self, filename: str) -> bool:
    """Sprawdza czy nazwa pliku nie przekracza maksymalnej długości."""
    max_length = self.rules['filename_max_length']
    if len(filename) > max_length:
        logger.debug(f"Nazwa pliku przekracza maksymalną długość {max_length}: {len(filename)} znaków")
        return False
    return True

def _validate_filename_characters(self, filename: str) -> bool:
    """Sprawdza czy nazwa pliku zawiera tylko dozwolone znaki."""
    forbidden_chars = self.rules['filename_forbidden_chars']
    if re.search(forbidden_chars, filename):
        logger.debug(f"Nazwa pliku zawiera niedozwolone znaki: {filename}")
        return False
    return True

def _validate_pair_data_structure(self, pair_metadata: Dict[str, Any], context: str = "") -> bool:
    """Wspólna metoda walidacji struktury danych pary plików."""
    try:
        if not isinstance(pair_metadata, dict):
            logger.debug(f"Metadane pary nie są słownikiem{context}: {pair_metadata}")
            return False

        # Sprawdzenie wymaganych kluczy
        if "stars" not in pair_metadata or "color_tag" not in pair_metadata:
            logger.debug(f"Metadane pary nie zawierają wymaganych kluczy 'stars' lub 'color_tag'{context}")
            return False

        # Sprawdzenie typów i zakresów wartości
        if not isinstance(pair_metadata["stars"], int) or not self._validate_stars_range(pair_metadata["stars"]):
            logger.debug(f"Wartość 'stars' nie jest poprawną liczbą całkowitą{context}: {pair_metadata['stars']}")
            return False

        if not (isinstance(pair_metadata["color_tag"], str) or pair_metadata["color_tag"] is None):
            logger.debug(f"Wartość 'color_tag' nie jest ciągiem znaków ani None{context}: {pair_metadata['color_tag']}")
            return False

        return True

    except Exception as e:
        logger.error(f"Błąd podczas walidacji metadanych pary{context}: {e}", exc_info=True)
        return False
```