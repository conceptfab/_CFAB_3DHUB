# 🔧 PATCH CODE: main_window_orchestrator.py

## 📋 INFORMACJE PODSTAWOWE

- **Plik:** `src/ui/main_window/main_window_orchestrator.py`
- **Typ:** Krytyczna poprawka inicjalizacji rozmiaru miniaturek
- **Priorytet:** ⚫⚫⚫⚫ NATYCHMIASTOWA IMPLEMENTACJA
- **Data:** 2025-06-25

## 🎯 LOKALIZACJA ZMIAN

**Plik:** `src/ui/main_window/main_window_orchestrator.py`
**Metoda:** `_initialize_core_data()`
**Linie:** 98-99

## 📝 PATCH CODE

### Znajdź w metodzie `_initialize_core_data()`:

```python
# PRZED (BŁĘDNY KOD - linie 98-99):
self.main_window.thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
self.main_window.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
```

### Zamień na:

```python
# PO (POPRAWNY KOD):
# PRIORYTET: default_thumbnail_size z konfiguracji użytkownika
user_default_size = self.main_window.app_config.get("default_thumbnail_size")
if user_default_size is not None:
    try:
        validated_size = int(user_default_size)
        if 20 <= validated_size <= 2000:  # Walidacja zakresu
            self.main_window.thumbnail_size = validated_size
            self.main_window.current_thumbnail_size = validated_size
            self.logger.info(f"[THUMBNAIL INIT] Użyto default_thumbnail_size z konfiguracji: {validated_size}px")
        else:
            # Wartość poza zakresem - użyj domyślnej
            self.main_window.thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
            self.main_window.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
            self.logger.warning(f"[THUMBNAIL INIT] default_thumbnail_size poza zakresem ({validated_size}), użyto domyślnej: {app_config.DEFAULT_THUMBNAIL_SIZE}px")
    except (ValueError, TypeError) as e:
        # Błędna wartość - użyj domyślnej
        self.main_window.thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
        self.main_window.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
        self.logger.error(f"[THUMBNAIL INIT] Błędna wartość default_thumbnail_size: {user_default_size} ({e}), użyto domyślnej: {app_config.DEFAULT_THUMBNAIL_SIZE}px")
else:
    # Brak konfiguracji - użyj domyślnej (zachowanie wstecznie kompatybilne)
    self.main_window.thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
    self.main_window.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
    self.logger.info(f"[THUMBNAIL INIT] Brak default_thumbnail_size w konfiguracji, użyto domyślnej: {app_config.DEFAULT_THUMBNAIL_SIZE}px")
```

## 🔧 KOMPLETNY FRAGMENT METODY PO ZMIANACH

```python
def _initialize_core_data(self):
    """Inicjalizuje podstawowe dane aplikacji."""
    self.logger.debug("Inicjalizacja podstawowych danych...")

    # Dane aplikacji - przeniesione z _init_data
    self.main_window.current_directory = ""
    self.main_window.file_pairs = []
    self.main_window.gallery_tile_widgets = {}
    self.main_window.is_scanning = False
    
    # POPRAWIONA INICJALIZACJA ROZMIARU MINIATUREK
    # PRIORYTET: default_thumbnail_size z konfiguracji użytkownika
    user_default_size = self.main_window.app_config.get("default_thumbnail_size")
    if user_default_size is not None:
        try:
            validated_size = int(user_default_size)
            if 20 <= validated_size <= 2000:  # Walidacja zakresu
                self.main_window.thumbnail_size = validated_size
                self.main_window.current_thumbnail_size = validated_size
                self.logger.info(f"[THUMBNAIL INIT] Użyto default_thumbnail_size z konfiguracji: {validated_size}px")
            else:
                # Wartość poza zakresem - użyj domyślnej
                self.main_window.thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
                self.main_window.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
                self.logger.warning(f"[THUMBNAIL INIT] default_thumbnail_size poza zakresem ({validated_size}), użyto domyślnej: {app_config.DEFAULT_THUMBNAIL_SIZE}px")
        except (ValueError, TypeError) as e:
            # Błędna wartość - użyj domyślnej
            self.main_window.thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
            self.main_window.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
            self.logger.error(f"[THUMBNAIL INIT] Błędna wartość default_thumbnail_size: {user_default_size} ({e}), użyto domyślnej: {app_config.DEFAULT_THUMBNAIL_SIZE}px")
    else:
        # Brak konfiguracji - użyj domyślnej (zachowanie wstecznie kompatybilne)
        self.main_window.thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
        self.main_window.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
        self.logger.info(f"[THUMBNAIL INIT] Brak default_thumbnail_size w konfiguracji, użyto domyślnej: {app_config.DEFAULT_THUMBNAIL_SIZE}px")

    # Flags dla lazy loading
    self.main_window._managers_initialized = False
    self.main_window._core_managers_cache = {}

    self.logger.debug("✅ Podstawowe dane zainicjalizowane")
```

## ✅ WERYFIKACJA POPRAWKI

### Test 1: Sprawdzenie logów
Po uruchomieniu aplikacji sprawdź logi - powinien pojawić się jeden z komunikatów:
```
[THUMBNAIL INIT] Użyto default_thumbnail_size z konfiguracji: 136px
```

### Test 2: Sprawdzenie wartości
```python
# W debuggerze lub tymczasowym kodzie:
print(f"thumbnail_size: {main_window.thumbnail_size}")
print(f"current_thumbnail_size: {main_window.current_thumbnail_size}")
# Powinno pokazać 136 gdy default_thumbnail_size=136 w konfiguracji
```

## 🚨 KRYTYCZNE UWAGI

### ⚠️ Wymagana poprawka w config_core.py PIERWSZA!
- Ta poprawka wymaga poprawnego mapowania w `config_core.py`
- Zaimplementuj patch `config_core_patch_code.md` PRZED tym patchem

### ⚠️ Logi są kluczowe
- Logi pomagają zdiagnozować skąd pochodzi wartość
- Prefix `[THUMBNAIL INIT]` ułatwia znalezienie w logach

### ⚠️ Walidacja jest bezpieczna
- Sprawdza zakres 20-2000px (zgodnie z ThumbnailProperties)
- Ma fallback do domyślnej wartości przy błędach

## 📊 OCZEKIWANY REZULTAT

### Scenariusz 1: Prawidłowa konfiguracja
```json
{"default_thumbnail_size": 136}
```
**Rezultat:** `current_thumbnail_size = 136`

### Scenariusz 2: Brak konfiguracji
```json
{}
```
**Rezultat:** `current_thumbnail_size = 250` (DEFAULT_THUMBNAIL_SIZE)

### Scenariusz 3: Błędna wartość
```json
{"default_thumbnail_size": "invalid"}
```
**Rezultat:** `current_thumbnail_size = 250` + log błędu

## 🔄 KOLEJNOŚĆ IMPLEMENTACJI

1. ✅ **config_core.py** (zaimplementowany pierwszy)
2. 🔄 **main_window_orchestrator.py** (ten patch)
3. ⏳ **window_initialization_manager.py** (następny)

## 📈 BUSINESS IMPACT

- **Natychmiastowy efekt:** Aplikacja respektuje `default_thumbnail_size` od startu
- **Matematyka działa:** Gdy `default_thumbnail_size=136`, aplikacja startuje z 136px
- **Fallback bezpieczny:** Gdy błąd w konfiguracji, aplikacja działa normalnie