# 🔧 PATCH CODE: src/ui/main_window/main_window.py

**Plik:** `src/ui/main_window/main_window.py`  
**Priorytet:** ⚫⚫⚫⚫ **OVER-ENGINEERED**  
**Data:** 2025-06-21  
**Rozmiar:** 617 linii → cel: ~200-250 linii  
**Problem:** Ekstremalne over-engineering z 20+ managerami

---

## 🚨 STRATEGIA REFAKTORYZACJI: RADYKALNE UPROSZCZENIE

### **FAZA 1: USUNIĘCIE OVER-ENGINEERING**

**USUNĄĆ KOMPLETNIE:**
1. ~~ManagerRegistry~~ - niepotrzebna abstrakcja
2. ~~20+ property delegacji~~ - bezużyteczny kod  
3. ~~Orchestrator~~ (częściowo) - uproszczenie inicjalizacji
4. ~~Większość "delegacji do Interface"~~ - bezpośrednia implementacja

**ZACHOWAĆ:**
- Podstawową funkcjonalność Qt
- Kluczowe metody UI
- Obsługę zdarzeń

---

## 📋 SEKCJA 3.1: NOWA UPROSZCZONA KLASA GŁÓWNA

**Problem:** 617 linii over-engineered kodu

**NOWA IMPLEMENTACJA (cel: ~200 linii):**

```python
"""
Główne okno aplikacji - UPROSZCZONA wersja po refaktoryzacji.
❌ USUNIĘTO: ManagerRegistry, Orchestrator, 20+ delegacji
✅ DODANO: Bezpośrednią implementację, prostotę, wydajność
"""

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QVBoxLayout, QWidget
from typing import Optional

from src.models.file_pair import FilePair


class MainWindow(QMainWindow):
    """Główne okno aplikacji CFAB_3DHUB - uproszczona wersja."""

    def __init__(self, style_sheet: Optional[str] = None):
        """Inicjalizuje główne okno aplikacji - uproszczone."""
        super().__init__()
        
        # Podstawowe atrybuty
        self.current_directory: Optional[str] = None
        self.current_file_pairs: list[FilePair] = []
        
        # Inicjalizacja UI
        self._init_ui()
        
        # Logowanie
        import logging
        self.logger = logging.getLogger(__name__)
        self.logger.info("Główne okno aplikacji zainicjalizowane")

    def _init_ui(self) -> None:
        """Inicjalizuje interfejs użytkownika - bezpośrednio."""
        self.setWindowTitle("CFAB_3DHUB")
        self.setMinimumSize(800, 600)
        
        # Główny widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Główny layout
        layout = QVBoxLayout(central_widget)
        
        # TODO: Dodać konkretne widgety UI
        # self._init_toolbar()
        # self._init_gallery()
        # self._init_file_tree()

    # Podstawowe metody UI
    def show_error_message(self, title: str, message: str) -> None:
        """Wyświetla komunikat błędu."""
        QMessageBox.critical(self, title, message)

    def show_warning_message(self, title: str, message: str) -> None:
        """Wyświetla ostrzeżenie."""
        QMessageBox.warning(self, title, message)

    def show_info_message(self, title: str, message: str) -> None:
        """Wyświetla informację."""
        QMessageBox.information(self, title, message)

    # Metody operacji na plikach - uproszczone
    def handle_file_operation(self, operation: str, file_pairs: list[FilePair]) -> None:
        """Obsługuje operacje na plikach - centralna metoda."""
        try:
            # TODO: Implementacja operacji
            self.logger.info(f"Wykonywanie operacji: {operation} na {len(file_pairs)} plikach")
        except Exception as e:
            self.logger.error(f"Błąd operacji {operation}: {e}")
            self.show_error_message("Błąd operacji", str(e))

    def closeEvent(self, event) -> None:
        """Obsługuje zamykanie aplikacji - uproszczone."""
        try:
            # Podstawowy cleanup
            if hasattr(self, 'current_file_pairs'):
                self.current_file_pairs.clear()
            
            self.logger.info("Aplikacja zamykana")
            event.accept()
        except Exception as e:
            self.logger.error(f"Błąd podczas zamykania: {e}")
            event.accept()  # Zawsze zamknij
```

---

## 📋 SEKCJA 3.2: USUNIĘCIE DELEGACJI PROPERTIES

**Problem:** 20+ niepotrzebnych property delegacji

**OBECNY KOD (linie 47-150) - DO USUNIĘCIA:**
```python
@property
def interface(self):
    """Delegacja do ManagerRegistry."""
    return self._manager_registry_new.get_manager("interface")

@property
def window_initialization_manager(self):
    """Delegacja do ManagerRegistry."""
    return self._manager_registry_new.get_manager("window_initialization_manager")

# ... 18+ podobnych property
```

**ZASTĄPIĆ PRZEZ:**
```python
# BEZPOŚREDNIE IMPLEMENTACJE - bez delegacji
def init_ui_components(self) -> None:
    """Inicjalizuje komponenty UI bezpośrednio."""
    # Implementacja zamiast delegacji
    pass

def handle_scanning(self, directory: str) -> None:
    """Obsługuje skanowanie katalogów bezpośrednio."""
    # Implementacja zamiast delegacji
    pass
```

---

## 📋 SEKCJA 3.3: KONSOLIDACJA METOD

**Problem:** Duplikacja logiki, zbędne metody

**OBECNE METODY (przykłady do konsolidacji):**

```python
# PRZED: 3 osobne metody
def _apply_filters_and_update_view(self):
def _update_gallery_view(self):  
def refresh_all_views(self, new_selection=None):

# PO: 1 metoda uniwersalna
def update_views(self, filter_updates: bool = True, 
                gallery_updates: bool = True,
                new_selection: Optional[FilePair] = None) -> None:
    """Uniwersalna metoda aktualizacji widoków."""
    try:
        if filter_updates:
            # Logika filtrów
            pass
        if gallery_updates:
            # Logika galerii  
            pass
        # Logika selekcji
    except Exception as e:
        self.logger.error(f"Błąd aktualizacji widoków: {e}")
```

---

## 📋 SEKCJA 3.4: USUNIĘCIE QTIMER.SINGLESHOT SPAM

**Problem:** Niepotrzebne opóźnienia wszędzie

**OBECNY KOD:**
```python
# Wykonaj asynchronicznie żeby nie blokować UI
QTimer.singleShot(0, _async_apply_filters)

# Asynchroniczne wyświetlenie żeby nie blokować UI  
QTimer.singleShot(0, lambda: QMessageBox.critical(self, title, message))

# Non-blocking message
QTimer.singleShot(0, lambda: QMessageBox.information(...))
```

**ZASTĄPIĆ PRZEZ:**
```python
# BEZPOŚREDNIE WYWOŁANIA - szybciej i prościej
def apply_filters(self) -> None:
    """Aplikuje filtry bezpośrednio."""
    # Implementacja bez QTimer.singleShot

def show_message(self, msg_type: str, title: str, message: str) -> None:
    """Uniwersalna metoda komunikatów."""
    if msg_type == "error":
        QMessageBox.critical(self, title, message)
    elif msg_type == "warning":
        QMessageBox.warning(self, title, message)
    else:
        QMessageBox.information(self, title, message)
```

---

## 📋 SEKCJA 3.5: OPTYMALIZACJA LOGOWANIA

**Problem:** Mixed f-string i lazy logging

**OBECNY KOD:**
```python
self.logger.info(f"🔥 _handle_stars_changed WYWOŁANY: {file_pair.get_base_name()} → {new_star_count} gwiazdek")
self.logger.error(f"Błąd podczas aplikacji filtrów: {e}")
```

**POPRAWKA:**
```python
self.logger.info("Stars changed: %s -> %d", file_pair.get_base_name(), new_star_count)
self.logger.error("Błąd aplikacji filtrów: %s", e)
```

---

## ✅ CHECKLISTA FUNKCJONALNOŚCI I ZALEŻNOŚCI

### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - czy główne okno nadal działa
- [ ] **Inicjalizacja aplikacji** - czy aplikacja startuje szybciej (10x)
- [ ] **Operacje na plikach** - czy podstawowe operacje działają
- [ ] **UI responsiveness** - czy UI jest bardziej responsywne
- [ ] **Memory usage** - czy używa 50% mniej pamięci
- [ ] **Obsługa błędów** - czy obsługa błędów nadal działa
- [ ] **Zamykanie aplikacji** - czy aplikacja się poprawnie zamyka

### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Usunięcie ManagerRegistry** - czy nie zepsuło innych części
- [ ] **Usunięcie Orchestrator** - czy inicjalizacja nadal działa  
- [ ] **Uproszczenie delegacji** - czy komunikacja między komponentami działa
- [ ] **Qt integration** - czy integracja z Qt jest stabilna
- [ ] **Import dependencies** - czy importy są zoptymalizowane

### **TESTY WERYFIKACYJNE:**

- [ ] **Test wydajnościowy KLUCZOWY** - startup time < 50% poprzedniego
- [ ] **Test pamięci KLUCZOWY** - memory usage < 70% poprzedniego  
- [ ] **Test funkcjonalności** - wszystkie podstawowe funkcje działają
- [ ] **Test regresyjny** - nie wprowadzono regresji w kluczowych funkcjach
- [ ] **Test UI responsiveness** - UI jest bardziej responsywne

### **KRYTERIA SUKCESU REFAKTORYZACJI:**

- **LINIE KODU** - redukcja z 617 do max 250 linii (60% redukcja)
- **STARTUP TIME** - poprawa o min 50%
- **MEMORY USAGE** - redukcja o min 30%
- **COMPLEXITY** - eliminacja 20+ managerów delegacji
- **MAINTAINABILITY** - kod 10x czytelniejszy i prostszy