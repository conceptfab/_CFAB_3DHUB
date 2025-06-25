**⚠️ KRYTYCZNE: Przed rozpoczęciem pracy zapoznaj się z ogólnymi zasadami refaktoryzacji, poprawek i testowania opisanymi w pliku [refactoring_rules.md](refactoring_rules.md).**

# 🔧 KOREKTA: config_core.py

## 📋 INFORMACJE PODSTAWOWE

- **Plik:** `src/config/config_core.py`
- **Kategoria:** Krytyczna logika biznesowa - konfiguracja aplikacji
- **Priorytet:** ⚫⚫⚫⚫ KRYTYCZNE
- **Data analizy:** 2025-06-25

## 🚨 ZIDENTYFIKOWANE PROBLEMY

### Problem 1: Błędne mapowanie default_thumbnail_size (KRYTYCZNE)

**Lokalizacja:** Linia 54
```python
# BŁĘDNY KOD:
"default_thumbnail_size": "thumbnail_size",
```

**Opis problemu:**
- Mapowanie `default_thumbnail_size` na `thumbnail_size` powoduje że wartość z konfiguracji jest niedostępna
- `__getattr__` metoda nie może pobrać prawidłowej wartości `default_thumbnail_size`
- Powoduje to ignorowanie preferencji użytkownika dotyczących domyślnego rozmiaru miniaturek

**Wpływ biznesowy:**
- Użytkownicy nie mogą ustawić nadrzędnej wartości rozmiaru miniaturek
- Konfiguracja `"default_thumbnail_size": 136` jest całkowicie ignorowana
- Matematyka suwaka (50% = 136px, 100% = 272px) nie działa

**Kategoria:** Błąd logiczny w konfiguracji

## 🎯 WYMAGANE POPRAWKI

### Poprawka 1: Naprawienie mapowania (NATYCHMIASTOWA)

**Cel:** Poprawne mapowanie `default_thumbnail_size` na właściwy klucz konfiguracji

**Implementacja:**
```python
# POPRAWNY KOD:
"default_thumbnail_size": "default_thumbnail_size",
```

**Uzasadnienie:**
- Klucz powinien mapować na siebie samego, nie na inny klucz
- Pozwala na poprawne pobieranie wartości przez `__getattr__`
- Umożliwia wykorzystanie logiki priorytetów z `ThumbnailProperties`

## 📊 ANALIZA WPŁYWU

### Przed poprawką:
- `config.default_thumbnail_size` → pobiera `config.get("thumbnail_size")` → błędna wartość
- Logika priorytetów w `ThumbnailProperties` nie jest używana

### Po poprawce:
- `config.default_thumbnail_size` → pobiera `config.get("default_thumbnail_size")` → prawidłowa wartość
- Logika priorytetów w `ThumbnailProperties` może być wykorzystana

## ⚡ DODATKOWE ZALECENIA

### Zalecenie 1: Weryfikacja mapowania
Sprawdzić czy inne mapowania w `_PROPERTY_MAP` są poprawne

### Zalecenie 2: Testy regresyjne
Dodać testy sprawdzające czy `default_thumbnail_size` jest poprawnie dostępne

## 🚫 ZAGROŻENIA

### Ryzyko niskie:
- Zmiana nie wpływa na istniejące funkcjonalności
- Tylko poprawia dostęp do konfiguracji

### Backward compatibility:
- Zmiana jest wstecznie kompatybilna
- Nie zmienia API ani struktury danych

## ✅ KRYTERIA SUKCESU

1. `config.default_thumbnail_size` zwraca wartość z konfiguracji (136)
2. Logika priorytetów w `ThumbnailProperties` może używać tej wartości
3. Brak regresji w innych częściach systemu konfiguracji

## 📈 BUSINESS IMPACT

**Wysoki pozytywny wpływ:**
- Przywraca funkcjonalność konfiguracji rozmiaru miniaturek
- Umożliwia użytkownikom ustawienie preferowanego rozmiaru
- Naprawia matematykę suwaka zgodnie z wymaganiami (50% = 136px, 100% = 272px)