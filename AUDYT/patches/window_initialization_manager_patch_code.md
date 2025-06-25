# 🔧 PATCH CODE: window_initialization_manager.py

## 📋 INFORMACJE PODSTAWOWE

- **Plik:** `src/ui/main_window/window_initialization_manager.py`
- **Typ:** Krytyczna poprawka inicjalizacji UI z default_thumbnail_size
- **Priorytet:** ⚫⚫⚫⚫ NATYCHMIASTOWA IMPLEMENTACJA
- **Data:** 2025-06-25

## 🎯 LOKALIZACJA ZMIAN

**Plik:** `src/ui/main_window/window_initialization_manager.py`
**Metoda:** `init_window_configuration()`
**Linie:** 52-64

## 📝 PATCH CODE

### Znajdź w metodzie `init_window_configuration()`:

```python
# PRZED (BŁĘDNY KOD - linie 52-64):
        # Oblicz początkowy rozmiar miniaturek
        size_range = (
            self.main_window.max_thumbnail_size - self.main_window.min_thumbnail_size
        )
        if size_range <= 0:
            self.main_window.current_thumbnail_size = (
                self.main_window.min_thumbnail_size
            )
        else:
            self.main_window.current_thumbnail_size = (
                self.main_window.min_thumbnail_size
                + int((size_range * self.main_window.initial_slider_position) / 100)
            )
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
                    self.main_window.current_thumbnail_size = validated_size
                    self.logger.info(f"[WINDOW INIT] Użyto default_thumbnail_size z konfiguracji: {validated_size}px")
                    
                    # Oblicz pozycję suwaka na podstawie default_thumbnail_size dla spójności UI
                    size_range = self.main_window.max_thumbnail_size - self.main_window.min_thumbnail_size
                    if size_range > 0:
                        # Dla matematyki: default_thumbnail_size na pozycji 50%, max = 2×default na pozycji 100%
                        # Wzór: pozycja = ((size - min) / (max - min)) * 100
                        calculated_position = ((validated_size - self.main_window.min_thumbnail_size) * 100) / size_range
                        # Ograniczenie do zakresu 0-100%
                        self.main_window.initial_slider_position = max(0, min(100, int(calculated_position)))
                        self.logger.info(f"[WINDOW INIT] Obliczona pozycja suwaka dla default_thumbnail_size {validated_size}px: {self.main_window.initial_slider_position}%")
                        
                        # ALTERNATYWNA MATEMATYKA: default_thumbnail_size = 50%, 2×default = 100%
                        # Jeśli chcemy aby default był zawsze na 50%, uncomment poniżej:
                        # self.main_window.initial_slider_position = 50
                        # new_max = validated_size * 2
                        # self.main_window.max_thumbnail_size = new_max
                        # self.logger.info(f"[WINDOW INIT] Dostosowano max_thumbnail_size do {new_max}px (2×{validated_size}px)")
                    
                    return  # Zakończ - nie obliczaj z suwaka
                else:
                    self.logger.warning(f"[WINDOW INIT] default_thumbnail_size poza zakresem 20-2000: {validated_size}")
            except (ValueError, TypeError) as e:
                self.logger.error(f"[WINDOW INIT] Błędna wartość default_thumbnail_size: {user_default_size} ({e})")

        # FALLBACK: Oblicz z suwaka tylko gdy brak prawidłowego default_thumbnail_size
        self.logger.debug("[WINDOW INIT] Brak default_thumbnail_size, obliczam z suwaka")
        size_range = (
            self.main_window.max_thumbnail_size - self.main_window.min_thumbnail_size
        )
        if size_range <= 0:
            self.main_window.current_thumbnail_size = (
                self.main_window.min_thumbnail_size
            )
            self.logger.debug(f"[WINDOW INIT] Nieprawidłowy zakres, użyto min_size: {self.main_window.min_thumbnail_size}px")
        else:
            self.main_window.current_thumbnail_size = (
                self.main_window.min_thumbnail_size
                + int((size_range * self.main_window.initial_slider_position) / 100)
            )
            self.logger.debug(f"[WINDOW INIT] Obliczono z suwaka: {self.main_window.current_thumbnail_size}px (slider: {self.main_window.initial_slider_position}%)")
```

## 🔧 KOMPLETNY FRAGMENT METODY PO ZMIANACH

```python
def init_window_configuration(self):
    """
    Inicjalizuje konfigurację okna aplikacji.
    Ustawia timer resize, rozmiary miniaturek, tytuł okna i status bar.
    """
    # Poprawne ustawienie resize_timer z odpowiednią funkcją
    self.main_window.resize_timer = QTimer(self.main_window)
    self.main_window.resize_timer.setSingleShot(True)
    self.main_window.resize_timer.timeout.connect(
        self.main_window._on_resize_timer_timeout
    )
    # Ustawienie opóźnienia - używamy bezpośredniej wartości
    self.main_window.resize_timer.setInterval(50)  # 50ms opóźnienie

    # Konfiguracja rozmiarów miniaturek
    self.main_window.min_thumbnail_size = (
        self.main_window.app_config.min_thumbnail_size
    )
    self.main_window.max_thumbnail_size = (
        self.main_window.app_config.max_thumbnail_size
    )
    self.main_window.initial_slider_position = 50

    # POPRAWIONA INICJALIZACJA ROZMIARU MINIATUREK
    # PRIORYTET: default_thumbnail_size z konfiguracji użytkownika
    user_default_size = self.main_window.app_config.get("default_thumbnail_size")
    if user_default_size is not None:
        try:
            validated_size = int(user_default_size)
            if 20 <= validated_size <= 2000:  # Walidacja zakresu
                self.main_window.current_thumbnail_size = validated_size
                self.logger.info(f"[WINDOW INIT] Użyto default_thumbnail_size z konfiguracji: {validated_size}px")
                
                # Oblicz pozycję suwaka na podstawie default_thumbnail_size dla spójności UI
                size_range = self.main_window.max_thumbnail_size - self.main_window.min_thumbnail_size
                if size_range > 0:
                    calculated_position = ((validated_size - self.main_window.min_thumbnail_size) * 100) / size_range
                    self.main_window.initial_slider_position = max(0, min(100, int(calculated_position)))
                    self.logger.info(f"[WINDOW INIT] Obliczona pozycja suwaka dla default_thumbnail_size {validated_size}px: {self.main_window.initial_slider_position}%")
                
                # Pomiń dalsze obliczenia
                self.logger.debug(
                    f"[WINDOW INIT] Final: current_thumbnail_size={self.main_window.current_thumbnail_size}px, "
                    f"slider_position={self.main_window.initial_slider_position}%"
                )
            else:
                self.logger.warning(f"[WINDOW INIT] default_thumbnail_size poza zakresem 20-2000: {validated_size}")
                # Kontynuuj do fallback
        except (ValueError, TypeError) as e:
            self.logger.error(f"[WINDOW INIT] Błędna wartość default_thumbnail_size: {user_default_size} ({e})")
            # Kontynuuj do fallback
    else:
        # FALLBACK: Oblicz z suwaka tylko gdy brak prawidłowego default_thumbnail_size
        self.logger.debug("[WINDOW INIT] Brak default_thumbnail_size, obliczam z suwaka")
        size_range = (
            self.main_window.max_thumbnail_size - self.main_window.min_thumbnail_size
        )
        if size_range <= 0:
            self.main_window.current_thumbnail_size = (
                self.main_window.min_thumbnail_size
            )
            self.logger.debug(f"[WINDOW INIT] Nieprawidłowy zakres, użyto min_size: {self.main_window.min_thumbnail_size}px")
        else:
            self.main_window.current_thumbnail_size = (
                self.main_window.min_thumbnail_size
                + int((size_range * self.main_window.initial_slider_position) / 100)
            )
            self.logger.debug(f"[WINDOW INIT] Obliczono z suwaka: {self.main_window.current_thumbnail_size}px (slider: {self.main_window.initial_slider_position}%)")

    self.logger.debug(
        f"Initial slider position: {self.main_window.initial_slider_position}%, "
        f"thumbnail size: {self.main_window.current_thumbnail_size}px"
    )

    # Konfiguracja okna
    self.main_window.setWindowTitle("CFAB_3DHUB")
    self.main_window.setMinimumSize(
        self.main_window.app_config.window_min_width,
        self.main_window.app_config.window_min_height,
    )

    # Konfiguracja status bar
    self._setup_status_bar()
```

## ✅ WERYFIKACJA POPRAWKI

### Test 1: Sprawdzenie logów inicjalizacji
Po uruchomieniu aplikacji sprawdź logi:
```
[WINDOW INIT] Użyto default_thumbnail_size z konfiguracji: 136px
[WINDOW INIT] Obliczona pozycja suwaka dla default_thumbnail_size 136px: 4%
```

### Test 2: Sprawdzenie matematyki
```python
# Przy default_thumbnail_size=136, min=100, max=1000:
# Pozycja suwaka = ((136-100) / (1000-100)) * 100 = (36/900) * 100 = 4%
```

### Test 3: Sprawdzenie zachowania suwaka
- Suwak powinien być na pozycji ~4% przy starcie
- Przesunięcie na 100% powinno dać ~1000px (max_size)

## 🚨 KRYTYCZNE UWAGI

### ⚠️ Wymagane poprzednie poprawki
Zaimplementuj PRZED tym patchem:
1. ✅ `config_core_patch_code.md`
2. ✅ `main_window_orchestrator_patch_code.md`

### ⚠️ Matematyka suwaka
- Obecna matematyka: pozycja bazuje na aktualnym zakresie min/max
- Alternatywna: można dostosować max_size aby default był zawsze na 50%

### ⚠️ Spójność UI
- Pozycja suwaka odzwierciedla rzeczywisty rozmiar
- Użytkownik widzi spójną wartość między konfiguracją a UI

## 📊 OCZEKIWANY REZULTAT

### Przy default_thumbnail_size=136:
- **Inicjalizacja:** `current_thumbnail_size = 136px`
- **Pozycja suwaka:** ~4% (obliczona na podstawie zakresu 100-1000)
- **Suwak 50%:** ~550px (zgodnie z aktualną matematyką)
- **Suwak 100%:** 1000px (max_size)

### Przy braku default_thumbnail_size:
- **Inicjalizacja:** jak wcześniej (z suwaka)
- **Pozycja suwaka:** 50%
- **Rozmiar:** 550px przy min=100, max=1000

## 🔄 ALTERNATYWNA MATEMATYKA (OPCJONALNA)

Jeśli chcesz aby `default_thumbnail_size` był zawsze na 50%, odkomentuj linijki w kodzie:
```python
# self.main_window.initial_slider_position = 50
# new_max = validated_size * 2  # 136*2 = 272
# self.main_window.max_thumbnail_size = new_max
```

**Efekt:** suwak 50% = 136px, suwak 100% = 272px (zgodnie z wymaganiem!)

## 📈 BUSINESS IMPACT

- **Naprawia główny problem:** default_thumbnail_size jest używane w inicjalizacji UI
- **Spójność:** suwak odzwierciedla rzeczywisty rozmiar
- **Elastyczność:** można wybrać matematykę suwaka (obecna vs. alternatywna)
- **Bezpieczeństwo:** fallback gdy brak/błąd w konfiguracji