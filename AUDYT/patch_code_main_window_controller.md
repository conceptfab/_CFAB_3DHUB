# 🔧 PATCH CODE: src/controllers/main_window_controller.py

**Plik:** `src/controllers/main_window_controller.py`  
**Priorytet:** ⚫⚫⚫⚫  
**Data:** 2025-06-21  
**Status:** DOBRA ARCHITEKTURA - tylko drobne optymalizacje potrzebne

---

## 📋 SEKCJA 4.1: SPRAWDZENIE NIEUŻYWANYCH METOD

**Problem:** Vulture raportuje 2 potencjalnie nieużywane metody

**METODY DO SPRAWDZENIA:**
1. `handle_bulk_move()` (linia 159) - 60% confidence
2. `handle_metadata_change()` (linia 282) - 60% confidence

**AKCJA:** Sprawdzić w całym projekcie czy te metody są rzeczywiście używane

---

## 📋 SEKCJA 4.2: DODANIE TYPE HINTS

**Problem:** Niektóre metody nie mają pełnych type hints

**OBECNY KOD (linia 282):**
```python
def handle_metadata_change(self, file_pair: FilePair, field: str, value):
```

**POPRAWKA:**
```python
from typing import Any

def handle_metadata_change(self, file_pair: FilePair, field: str, value: Any) -> None:
```

**OBECNY KOD (linia 332):**
```python
def _show_operation_errors(self, operation_name: str, errors: List[str]):
```

**POPRAWKA:**
```python
def _show_operation_errors(self, operation_name: str, errors: List[str]) -> None:
```

---

## 📋 SEKCJA 4.3: DODANIE DEBUG LOGGING

**Problem:** Można dodać więcej debug informacji dla lepszej diagnostyki

**OBECNY KOD (linia 53-71):**
```python
def handle_folder_selection(self, directory_path: str):
    """
    Obsługuje wybór folderu roboczego przez uruchomienie asynchronicznego skanowania.
    """
    try:
        errors = self.scan_service.validate_directory_path(directory_path)
        if errors:
            error_msg = "Błędy walidacji folderu:\n" + "\n".join(errors)
            self.view.show_error_message("Błąd folderu", error_msg)
            return

        self.view.worker_manager.start_directory_scan_worker(directory_path)

    except Exception as e:
        error_msg = f"Nieoczekiwany błąd podczas uruchamiania skanowania: {str(e)}"
        self.logger.error(error_msg, exc_info=True)
        self.view.show_error_message("Błąd Krytyczny", error_msg)
        self.view._hide_progress()
```

**POPRAWKA:**
```python
def handle_folder_selection(self, directory_path: str) -> None:
    """
    Obsługuje wybór folderu roboczego przez uruchomienie asynchronicznego skanowania.
    """
    try:
        self.logger.debug("Rozpoczęcie skanowania folderu: %s", directory_path)
        
        errors = self.scan_service.validate_directory_path(directory_path)
        if errors:
            error_msg = "Błędy walidacji folderu:\n" + "\n".join(errors)
            self.logger.warning("Walidacja folderu nie powiodła się: %s", error_msg)
            self.view.show_error_message("Błąd folderu", error_msg)
            return

        self.logger.debug("Walidacja folderu zakończona pomyślnie, uruchamianie workera")
        self.view.worker_manager.start_directory_scan_worker(directory_path)

    except Exception as e:
        error_msg = f"Nieoczekiwany błąd podczas uruchamiania skanowania: {str(e)}"
        self.logger.error(error_msg, exc_info=True)
        self.view.show_error_message("Błąd Krytyczny", error_msg)
        self.view._hide_progress()
```

---

## 📋 SEKCJA 4.4: OPTYMALIZACJA OBSŁUGI BŁĘDÓW

**Problem:** Metoda `_show_operation_errors` mogłaby być bardziej elastyczna

**OBECNY KOD (linia 332-346):**
```python
def _show_operation_errors(self, operation_name: str, errors: List[str]):
    """Pokazuje błędy operacji użytkownikowi."""
    if not errors:
        return

    error_msg = f"Błędy podczas {operation_name}:\n\n"

    # Pokaż maksymalnie 5 błędów
    shown_errors = errors[:5]
    error_msg += "\n".join(shown_errors)

    if len(errors) > 5:
        error_msg += f"\n\n... i {len(errors) - 5} więcej błędów"

    self.view.show_warning_message(f"Błędy {operation_name}", error_msg)
```

**POPRAWKA:**
```python
def _show_operation_errors(self, operation_name: str, errors: List[str], max_errors: int = 5) -> None:
    """
    Pokazuje błędy operacji użytkownikowi.
    
    Args:
        operation_name: Nazwa operacji
        errors: Lista błędów
        max_errors: Maksymalna liczba błędów do wyświetlenia
    """
    if not errors:
        return

    self.logger.warning("Operacja %s zakończona z %d błędami", operation_name, len(errors))
    
    error_msg = f"Błędy podczas {operation_name}:\n\n"

    # Pokaż maksymalnie określoną liczbę błędów
    shown_errors = errors[:max_errors]
    error_msg += "\n".join(shown_errors)

    if len(errors) > max_errors:
        remaining = len(errors) - max_errors
        error_msg += f"\n\n... i {remaining} więcej błędów"

    self.view.show_warning_message(f"Błędy {operation_name}", error_msg)
```

---

## 📋 SEKCJA 4.5: KONSOLIDACJA PODOBNYCH METOD (OPCJONALNA)

**Problem:** Metody `handle_bulk_delete` i `handle_bulk_move` mają podobną strukturę

**MOŻLIWA OPTYMALIZACJA (zaawansowana):**
```python
def _handle_bulk_operation(
    self, 
    selected_pairs: List[FilePair], 
    operation: str,
    operation_func: callable,
    *args, **kwargs
) -> bool:
    """Uniwersalna metoda dla operacji masowych."""
    if not selected_pairs:
        self.view.show_info_message("Info", f"Nie wybrano plików do {operation}")
        return False

    try:
        self.view._show_progress(0, f"{operation.capitalize()} {len(selected_pairs)} par plików...")
        
        # Wykonaj operację
        processed_pairs, errors = operation_func(selected_pairs, *args, **kwargs)
        
        # Aktualizuj stan
        self._remove_pairs_from_state(processed_pairs)
        
        # Powiadom UI
        self.view.update_after_bulk_operation(processed_pairs, operation)
        self.view._show_progress(100, f"{operation.capitalize()} {len(processed_pairs)} par plików")
        
        # Pokaż błędy jeśli były
        if errors:
            self._show_operation_errors(operation, errors)
            
        self.logger.info("Bulk %s: przetworzono %d par", operation, len(processed_pairs))
        return True
        
    except Exception as e:
        error_msg = f"Błąd masowego {operation}: {str(e)}"
        self.logger.error(error_msg)
        self.view.show_error_message(f"Błąd {operation}", error_msg)
        self.view._hide_progress()
        return False
```

**UWAGA:** Ta optymalizacja jest opcjonalna - obecny kod jest czytelny i nie wymaga konsolidacji.

---

## ✅ CHECKLISTA FUNKCJONALNOŚCI I ZALEŻNOŚCI

### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - czy controller nadal koordynuje logikę biznesową
- [ ] **MVC pattern** - czy separacja View-Controller-Model działa
- [ ] **Handle methods** - czy wszystkie metody handle_* działają poprawnie
- [ ] **State management** - czy zarządzanie stanem aplikacji działa
- [ ] **Error handling** - czy obsługa błędów jest prawidłowa
- [ ] **Bulk operations** - czy operacje masowe działają wydajnie
- [ ] **Scan coordination** - czy koordynacja skanowania działa

### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Managers integration** - czy integracja z SelectionManager, SpecialFoldersManager działa
- [ ] **Services communication** - czy komunikacja z FileOperationsService, ScanningService działa
- [ ] **View communication** - czy komunikacja z MainWindow działa
- [ ] **Processor integration** - czy integracja z ScanResultProcessor działa
- [ ] **Model updates** - czy aktualizacje FilePair działają poprawnie

### **TESTY WERYFIKACYJNE:**

- [ ] **Test MVC pattern** - czy wzorzec MVC jest prawidłowo implementowany
- [ ] **Test handle operations** - czy wszystkie operacje handle_* działają
- [ ] **Test state consistency** - czy stan aplikacji jest spójny
- [ ] **Test error scenarios** - czy błędy są prawidłowo obsługiwane
- [ ] **Test integration** - czy integracja z innymi komponentami działa

### **KRYTERIA SUKCESU:**

- **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- **BRAK FAILED TESTS** - wszystkie testy muszą przejść
- **ARCHITECTURE QUALITY** - MVC pattern musi być zachowany
- **PERFORMANCE** - operacje masowe muszą działać wydajnie
- **CODE QUALITY** - czytelność i maintainability zachowane

---

## 🏆 WNIOSEK

Ten plik to **PRZYKŁAD DOBREJ ARCHITEKTURY**:
- ✅ Prawidłowy MVC pattern
- ✅ Separacja odpowiedzialności
- ✅ Czytelny kod
- ✅ Dobra organizacja metod
- ✅ Prawidłowe error handling

**Potrzebne tylko drobne optymalizacje** - nie wymaga refaktoryzacji jak main_window.py!