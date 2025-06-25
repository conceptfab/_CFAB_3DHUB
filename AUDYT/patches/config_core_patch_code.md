# 🔧 PATCH CODE: config_core.py

## 📋 INFORMACJE PODSTAWOWE

- **Plik:** `src/config/config_core.py`
- **Typ:** Krytyczna poprawka mapowania konfiguracji
- **Priorytet:** ⚫⚫⚫⚫ NATYCHMIASTOWA IMPLEMENTACJA
- **Data:** 2025-06-25

## 🎯 LOKALIZACJA ZMIAN

**Plik:** `src/config/config_core.py`
**Linia:** 54

## 📝 PATCH CODE

### Zmiana 1: Poprawienie mapowania default_thumbnail_size

```python
# PRZED (BŁĘDNY KOD - linia 54):
"default_thumbnail_size": "thumbnail_size",

# PO (POPRAWNY KOD):
"default_thumbnail_size": "default_thumbnail_size",
```

## 🔧 KOMPLETNY FRAGMENT DO ZAMIANY

### Znajdź w pliku `config_core.py`:

```python
    # Property mapping jako class attribute (optymalizacja)
    _PROPERTY_MAP = {
        "min_thumbnail_size": "min_thumbnail_size",
        "max_thumbnail_size": "max_thumbnail_size",
        "scanner_max_cache_entries": "scanner_max_cache_entries",
        "scanner_max_cache_age_seconds": "scanner_max_cache_age_seconds",
        "thumbnail_cache_max_entries": "thumbnail_cache_max_entries",
        "thumbnail_cache_max_memory_mb": "thumbnail_cache_max_memory_mb",
        "thumbnail_cache_enable_disk": "thumbnail_cache_enable_disk",
        "thumbnail_cache_cleanup_threshold": ("thumbnail_cache_cleanup_threshold"),
        "window_min_width": "window_min_width",
        "window_min_height": "window_min_height",
        "resize_timer_delay_ms": "resize_timer_delay_ms",
        "progress_hide_delay_ms": "progress_hide_delay_ms",
        "thread_wait_timeout_ms": "thread_wait_timeout_ms",
        "preferences_status_display_ms": "preferences_status_display_ms",
        "supported_archive_extensions": "supported_archive_extensions",
        "supported_preview_extensions": "supported_preview_extensions",
        "default_thumbnail_size": "thumbnail_size",  # ← BŁĘDNA LINIA
    }
```

### Zamień na:

```python
    # Property mapping jako class attribute (optymalizacja)
    _PROPERTY_MAP = {
        "min_thumbnail_size": "min_thumbnail_size",
        "max_thumbnail_size": "max_thumbnail_size",
        "scanner_max_cache_entries": "scanner_max_cache_entries",
        "scanner_max_cache_age_seconds": "scanner_max_cache_age_seconds",
        "thumbnail_cache_max_entries": "thumbnail_cache_max_entries",
        "thumbnail_cache_max_memory_mb": "thumbnail_cache_max_memory_mb",
        "thumbnail_cache_enable_disk": "thumbnail_cache_enable_disk",
        "thumbnail_cache_cleanup_threshold": ("thumbnail_cache_cleanup_threshold"),
        "window_min_width": "window_min_width",
        "window_min_height": "window_min_height",
        "resize_timer_delay_ms": "resize_timer_delay_ms",
        "progress_hide_delay_ms": "progress_hide_delay_ms",
        "thread_wait_timeout_ms": "thread_wait_timeout_ms",
        "preferences_status_display_ms": "preferences_status_display_ms",
        "supported_archive_extensions": "supported_archive_extensions",
        "supported_preview_extensions": "supported_preview_extensions",
        "default_thumbnail_size": "default_thumbnail_size",  # ← POPRAWIONA LINIA
    }
```

## ✅ WERYFIKACJA POPRAWKI

### Test 1: Sprawdzenie dostępu do wartości
```python
# Kod testowy (dodać tymczasowo do testowania):
config = AppConfig.get_instance()
print(f"default_thumbnail_size: {config.default_thumbnail_size}")
# Powinno wypisać: default_thumbnail_size: 136 (lub inna wartość z konfiguracji)
```

### Test 2: Sprawdzenie logiki priorytetów
```python
# Test czy ThumbnailProperties może używać wartości:
thumbnail_props = config.thumbnail_properties
size = thumbnail_props.thumbnail_size
print(f"Thumbnail size from properties: {size}")
# Powinno uwzględnić default_thumbnail_size jeśli ustawione
```

## 🚨 KRYTYCZNE UWAGI

### ⚠️ To jest pojedyncza linia!
- Zmiana dotyczy TYLKO jednej linii w mapowaniu
- Nie zmieniaj innych części _PROPERTY_MAP
- Zachowaj dokładne formatowanie i przecinki

### ⚠️ Natychmiastowy efekt
- Po tej zmianie `config.default_thumbnail_size` będzie zwracać poprawną wartość
- Umożliwi to działanie logiki priorytetów w ThumbnailProperties

## 📊 OCZEKIWANY REZULTAT

### Przed zmianą:
```python
config.default_thumbnail_size  # Zwraca config.get("thumbnail_size") → błędna wartość
```

### Po zmianie:
```python
config.default_thumbnail_size  # Zwraca config.get("default_thumbnail_size") → 136
```

## 🔄 KOLEJNOŚĆ IMPLEMENTACJI

1. **PIERWSZY:** Zaimplementuj tę poprawkę
2. **DRUGI:** Zaimplementuj poprawki w main_window_orchestrator.py
3. **TRZECI:** Zaimplementuj poprawki w window_initialization_manager.py

Ta poprawka jest **fundamentalna** - bez niej kolejne poprawki nie będą działać poprawnie!