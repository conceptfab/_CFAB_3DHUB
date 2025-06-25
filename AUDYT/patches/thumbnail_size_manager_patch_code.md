# 🔧 PATCH CODE: thumbnail_size_manager.py

## 📋 INFORMACJE PODSTAWOWE

- **Plik:** `src/ui/main_window/thumbnail_size_manager.py`
- **Typ:** Poprawka zarządzania suwakiem z uwzględnieniem default_thumbnail_size
- **Priorytet:** 🔴🔴🔴 WYSOKIE (po krytycznych poprawkach)
- **Data:** 2025-06-25

## 🎯 LOKALIZACJA ZMIAN

**Plik:** `src/ui/main_window/thumbnail_size_manager.py`
**Metoda:** `update_thumbnail_size()`
**Linie:** 47-50

## 📝 PATCH CODE

### Znajdź w metodzie `update_thumbnail_size()`:

```python
# PRZED (linie 47-50):
                    # Oblicz rozmiar proporcjonalnie do pozycji suwaka (0-100%)
                    self.main_window.current_thumbnail_size = (
                        self.main_window.min_thumbnail_size
                        + int((size_range * slider_value) / 100)
                    )
```

### Zamień na:

```python
                    # SPRAWDŹ CZY UŻYTKOWNIK MA USTAWIONY default_thumbnail_size
                    user_default_size = self.main_window.app_config.get("default_thumbnail_size")
                    if user_default_size is not None and slider_value == 50:
                        # Gdy suwak na 50% i user ma default_thumbnail_size - użyj tej wartości
                        try:
                            validated_size = int(user_default_size)
                            if 20 <= validated_size <= 2000:
                                self.main_window.current_thumbnail_size = validated_size
                                self.logger.debug(f"[THUMBNAIL MANAGER] Suwak 50%: użyto default_thumbnail_size = {validated_size}px")
                            else:
                                # Oblicz normalnie jeśli default poza zakresem
                                self.main_window.current_thumbnail_size = (
                                    self.main_window.min_thumbnail_size
                                    + int((size_range * slider_value) / 100)
                                )
                                self.logger.debug(f"[THUMBNAIL MANAGER] default_thumbnail_size poza zakresem, obliczono: {self.main_window.current_thumbnail_size}px")
                        except (ValueError, TypeError):
                            # Oblicz normalnie jeśli błąd w default
                            self.main_window.current_thumbnail_size = (
                                self.main_window.min_thumbnail_size
                                + int((size_range * slider_value) / 100)
                            )
                            self.logger.debug(f"[THUMBNAIL MANAGER] Błąd w default_thumbnail_size, obliczono: {self.main_window.current_thumbnail_size}px")
                    else:
                        # Oblicz rozmiar proporcjonalnie do pozycji suwaka (0-100%)
                        self.main_window.current_thumbnail_size = (
                            self.main_window.min_thumbnail_size
                            + int((size_range * slider_value) / 100)
                        )
                        self.logger.debug(f"[THUMBNAIL MANAGER] Obliczono z suwaka: {self.main_window.current_thumbnail_size}px (slider: {slider_value}%)")
```

## 🔧 KOMPLETNY FRAGMENT METODY PO ZMIANACH

```python
def update_thumbnail_size(self):
    """
    Aktualizuje rozmiar miniatur w galerii na podstawie suwaka.
    """
    self.logger.debug("Aktualizacja rozmiaru miniatur z suwaka")
    try:
        # Pobierz wartość z suwaka
        if hasattr(self.main_window, "size_slider"):
            slider_value = self.main_window.size_slider.value()

            # Oblicz nowy rozmiar na podstawie wartości suwaka
            size_range = (
                self.main_window.max_thumbnail_size
                - self.main_window.min_thumbnail_size
            )
            if size_range <= 0:
                self.main_window.current_thumbnail_size = (
                    self.main_window.min_thumbnail_size
                )
            else:
                # SPRAWDŹ CZY UŻYTKOWNIK MA USTAWIONY default_thumbnail_size
                user_default_size = self.main_window.app_config.get("default_thumbnail_size")
                if user_default_size is not None and slider_value == 50:
                    # Gdy suwak na 50% i user ma default_thumbnail_size - użyj tej wartości
                    try:
                        validated_size = int(user_default_size)
                        if 20 <= validated_size <= 2000:
                            self.main_window.current_thumbnail_size = validated_size
                            self.logger.debug(f"[THUMBNAIL MANAGER] Suwak 50%: użyto default_thumbnail_size = {validated_size}px")
                        else:
                            # Oblicz normalnie jeśli default poza zakresem
                            self.main_window.current_thumbnail_size = (
                                self.main_window.min_thumbnail_size
                                + int((size_range * slider_value) / 100)
                            )
                            self.logger.debug(f"[THUMBNAIL MANAGER] default_thumbnail_size poza zakresem, obliczono: {self.main_window.current_thumbnail_size}px")
                    except (ValueError, TypeError):
                        # Oblicz normalnie jeśli błąd w default
                        self.main_window.current_thumbnail_size = (
                            self.main_window.min_thumbnail_size
                            + int((size_range * slider_value) / 100)
                        )
                        self.logger.debug(f"[THUMBNAIL MANAGER] Błąd w default_thumbnail_size, obliczono: {self.main_window.current_thumbnail_size}px")
                else:
                    # Oblicz rozmiar proporcjonalnie do pozycji suwaka (0-100%)
                    self.main_window.current_thumbnail_size = (
                        self.main_window.min_thumbnail_size
                        + int((size_range * slider_value) / 100)
                    )
                    self.logger.debug(f"[THUMBNAIL MANAGER] Obliczono z suwaka: {self.main_window.current_thumbnail_size}px (slider: {slider_value}%)")

            # Zapisz pozycję suwaka do konfiguracji
            if hasattr(self.main_window, "app_config"):
                self.main_window.app_config.set_thumbnail_slider_position(
                    slider_value
                )

            # Uruchom timer do aktualizacji rozmiaru
            if hasattr(self.main_window, "resize_timer"):
                self.main_window.resize_timer.start()

            self.logger.debug(f"[THUMBNAIL SIZE] min={self.main_window.min_thumbnail_size}, max={self.main_window.max_thumbnail_size}, slider={slider_value}%, current={self.main_window.current_thumbnail_size}px")
            self.logger.debug(
                f"Zakres rozmiarów: {self.main_window.min_thumbnail_size}-"
                f"{self.main_window.max_thumbnail_size}px"
            )
    except Exception as e:
        self.logger.error(f"Błąd obliczania rozmiaru miniatur: {e}", exc_info=True)
```

## ✅ WERYFIKACJA POPRAWKI

### Test 1: Sprawdzenie logiki suwaka 50%
```
1. Ustaw w konfiguracji: "default_thumbnail_size": 136
2. Przesuń suwak na 50%
3. Sprawdź logi: "[THUMBNAIL MANAGER] Suwak 50%: użyto default_thumbnail_size = 136px"
```

### Test 2: Sprawdzenie innych pozycji suwaka
```
1. Przesuń suwak na 30%
2. Sprawdź logi: "[THUMBNAIL MANAGER] Obliczono z suwaka: XXXpx (slider: 30%)"
```

## 🚨 KRYTYCZNE UWAGI

### ⚠️ Opcjonalna poprawka
- Ta poprawka jest **opcjonalna** - aplikacja będzie działać bez niej
- Główne problemy rozwiązują poprzednie 3 poprawki

### ⚠️ Specjalne zachowanie dla 50%
- Logika aktywuje się tylko gdy suwak jest dokładnie na 50%
- Dla innych pozycji używa standardowych obliczeń

### ⚠️ Bezpieczeństwo
- Ma walidację i fallback na standardowe obliczenia
- Nie wpływa na stabilność aplikacji

## 📊 OCZEKIWANY REZULTAT

### Przy default_thumbnail_size=136:

**Suwak 50%:**
- Zamiast: 550px (obliczone)
- Teraz: 136px (z konfiguracji)

**Suwak 100%:**
- Jak wcześniej: 1000px (max_size)

**Suwak 30%:**
- Jak wcześniej: obliczone proporcjonalnie

## 🔄 KOLEJNOŚĆ IMPLEMENTACJI

1. ✅ `config_core.py`
2. ✅ `main_window_orchestrator.py`  
3. ✅ `window_initialization_manager.py`
4. 🔄 `thumbnail_size_manager.py` (ten patch - opcjonalny)

## 📈 BUSINESS IMPACT

**Średni pozytywny wpływ:**
- Zapewnia spójność gdy użytkownik używa suwaka
- Pozycja 50% daje wartość z konfiguracji (136px)
- Inne pozycje działają normalnie

**Alternatywa:**
Jeśli nie chcesz tej logiki, poprzednie poprawki i tak rozwiążą główny problem!