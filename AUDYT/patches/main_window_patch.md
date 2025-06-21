# 🔧 POPRAWKI KODU: src/ui/main_window/main_window.py

**Data utworzenia:** 2025-06-21  
**Plik docelowy:** `src/ui/main_window/main_window.py`  
**Priorytet:** ⚫⚫⚫⚫ KRYTYCZNY

---

## 📋 SPIS POPRAWEK

### 2.1 Usunięcie powtarzających się importów QMessageBox
### 2.2 Konsolidacja imports outside toplevel
### 2.3 Utworzenie MessageBoxHelper utility class
### 2.4 Manager property caching optimization
### 2.5 Import reorganization na górze pliku

---

## 🔧 POPRAWKA 2.1: Usunięcie powtarzających się importów QMessageBox

**Lokalizacja:** Linie 173, 513, 520, 527, 538  
**Problem:** QMessageBox importowany lokalnie w każdej funkcji  
**Rozwiązanie:** Usunięcie lokalnych importów, używanie globalnego

### Stary kod - wszystkie funkcje zawierają:
```python
def show_about(self):
    """Wyświetla okno informacji o aplikacji - direct implementation."""
    from PyQt6.QtWidgets import QMessageBox  # ❌ Duplikat
    # ...

def show_error_message(self, title: str, message: str):
    """Wyświetla komunikat błędu - asynchroniczna implementacja."""
    from PyQt6.QtWidgets import QMessageBox  # ❌ Duplikat
    # ...

def show_warning_message(self, title: str, message: str):
    """Wyświetla ostrzeżenie - asynchroniczna implementacja."""
    from PyQt6.QtWidgets import QMessageBox  # ❌ Duplikat
    # ...

def show_info_message(self, title: str, message: str):
    """Wyświetla informację - asynchroniczna implementacja."""
    from PyQt6.QtWidgets import QMessageBox  # ❌ Duplikat
    # ...

def confirm_bulk_delete(self, count: int) -> bool:
    """Potwierdza masowe usuwanie - direct implementation."""
    from PyQt6.QtWidgets import QMessageBox  # ❌ Duplikat
    # ...
```

### Nowy kod - usunięcie wszystkich lokalnych importów:
```python
def show_about(self):
    """Wyświetla okno informacji o aplikacji - direct implementation."""
    # Używa globalnego importu z linii 7
    about_text = (
        "CFAB_3DHUB - Menedżer plików 3D\n"
        "Wersja 2.0\n\n"
        "Aplikacja do zarządzania plikami 3D i ich podglądami."
    )
    QMessageBox.about(self, "O programie CFAB_3DHUB", about_text)

def show_error_message(self, title: str, message: str):
    """Wyświetla komunikat błędu - asynchroniczną implementację."""
    # Używa globalnego importu z linii 7
    QTimer.singleShot(0, lambda: QMessageBox.critical(self, title, message))

def show_warning_message(self, title: str, message: str):
    """Wyświetla ostrzeżenie - asynchroniczną implementację."""
    # Używa globalnego importu z linii 7
    QTimer.singleShot(0, lambda: QMessageBox.warning(self, title, message))

def show_info_message(self, title: str, message: str):
    """Wyświetla informację - asynchroniczną implementację."""
    # Używa globalnego importu z linii 7
    QTimer.singleShot(0, lambda: QMessageBox.information(self, title, message))

def confirm_bulk_delete(self, count: int) -> bool:
    """Potwierdza masowe usuwanie - direct implementation."""
    # Używa globalnego importu z linii 7
    # UWAGA: confirm_bulk_delete musi być synchroniczne bo zwraca bool
    reply = QMessageBox.question(
        self,
        "Potwierdzenie usunięcia",
        f"Czy na pewno chcesz usunąć {count} par plików?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes
```

---

## 🔧 POPRAWKA 2.2: Reorganizacja imports outside toplevel

**Lokalizacja:** Linie 33, 38, 154, 322  
**Problem:** Importy w środku funkcji spowalniają wykonanie  
**Rozwiązanie:** Selective moving imports to top level

### Importy do przeniesienia na górę pliku:

**Dodać na górze po istniejących importach (po linii 18):**
```python
# Existing imports remain...
from src.ui.main_window.window_initialization_manager import WindowInitializationManager

# Additional imports - moved from functions for performance
from src.ui.widgets.preferences_dialog import PreferencesDialog
from src.logic.metadata.metadata_core import MetadataManager
```

### Importy do pozostawienia jako lazy loading (UZASADNIONE):
```python
# Te imports POZOSTAJĄ w funkcjach bo są uzasadnione:

# W __init__ (linie 33, 38) - circular dependency prevention
from src.ui.main_window.manager_registry import ManagerRegistry
from src.ui.main_window.main_window_orchestrator import MainWindowOrchestrator
```

### Stary kod z imports w funkcjach:
```python
def show_preferences(self):
    """Wyświetla okno preferencji."""
    from src.ui.widgets.preferences_dialog import PreferencesDialog  # ❌ Przenieść na górę
    # ...

def setup_metadata_cleanup_if_needed(self):
    # ...
    if condition:
        from src.logic.metadata.metadata_core import MetadataManager  # ❌ Przenieść na górę
```

### Nowy kod z importami na górze:
```python
def show_preferences(self):
    """Wyświetla okno preferencji."""
    # PreferencesDialog już zaimportowany na górze
    try:
        dialog = PreferencesDialog(self)
        # ...

def setup_metadata_cleanup_if_needed(self):
    # ...
    if condition:
        # MetadataManager już zaimportowany na górze
        manager = MetadataManager()
```

---

## 🔧 POPRAWKA 2.3: Utworzenie MessageBoxHelper utility class

**Lokalizacja:** Nowa klasa helper  
**Problem:** Powtarzający się pattern QTimer.singleShot dla async message boxes  
**Rozwiązanie:** Utility class do centralizacji message box logic

### Nowa klasa do dodania PRZED class MainWindow:

```python
class MessageBoxHelper:
    """
    Utility class dla asynchronicznych message boxes.
    Centralizuje logikę wyświetlania komunikatów bez blokowania UI.
    """

    @staticmethod
    def show_error_async(parent, title: str, message: str):
        """Wyświetla błąd asynchronicznie."""
        QTimer.singleShot(0, lambda: QMessageBox.critical(parent, title, message))

    @staticmethod
    def show_warning_async(parent, title: str, message: str):
        """Wyświetla ostrzeżenie asynchronicznie."""
        QTimer.singleShot(0, lambda: QMessageBox.warning(parent, title, message))

    @staticmethod
    def show_info_async(parent, title: str, message: str):
        """Wyświetla informację asynchronicznie."""
        QTimer.singleShot(0, lambda: QMessageBox.information(parent, title, message))

    @staticmethod
    def show_about(parent, title: str, text: str):
        """Wyświetla okno About."""
        QMessageBox.about(parent, title, text)

    @staticmethod
    def confirm_question(parent, title: str, question: str, default_button=None) -> bool:
        """
        Wyświetla pytanie potwierdzające (synchroniczne).
        
        Returns:
            bool: True jeśli użytkownik wybrał Yes, False w przeciwnym razie
        """
        if default_button is None:
            default_button = QMessageBox.StandardButton.No
            
        reply = QMessageBox.question(
            parent,
            title,
            question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            default_button,
        )
        return reply == QMessageBox.StandardButton.Yes
```

### Aktualizacja metod MainWindow do użycia MessageBoxHelper:

```python
# PRZED - każda metoda ma własną implementację
def show_about(self):
    """Wyświetla okno informacji o aplikacji - direct implementation."""
    about_text = (
        "CFAB_3DHUB - Menedżer plików 3D\n"
        "Wersja 2.0\n\n"
        "Aplikacja do zarządzania plikami 3D i ich podglądami."
    )
    QMessageBox.about(self, "O programie CFAB_3DHUB", about_text)

def show_error_message(self, title: str, message: str):
    """Wyświetla komunikat błędu - asynchroniczna implementacja."""
    QTimer.singleShot(0, lambda: QMessageBox.critical(self, title, message))

def show_warning_message(self, title: str, message: str):
    """Wyświetla ostrzeżenie - asynchroniczna implementacja."""
    QTimer.singleShot(0, lambda: QMessageBox.warning(self, title, message))

def show_info_message(self, title: str, message: str):
    """Wyświetla informację - asynchroniczna implementacja."""
    QTimer.singleShot(0, lambda: QMessageBox.information(self, title, message))

def confirm_bulk_delete(self, count: int) -> bool:
    """Potwierdza masowe usuwanie - direct implementation."""
    reply = QMessageBox.question(
        self,
        "Potwierdzenie usunięcia",
        f"Czy na pewno chcesz usunąć {count} par plików?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes

# PO - używa MessageBoxHelper
def show_about(self):
    """Wyświetla okno informacji o aplikacji."""
    about_text = (
        "CFAB_3DHUB - Menedżer plików 3D\n"
        "Wersja 2.0\n\n"
        "Aplikacja do zarządzania plikami 3D i ich podglądami."
    )
    MessageBoxHelper.show_about(self, "O programie CFAB_3DHUB", about_text)

def show_error_message(self, title: str, message: str):
    """Wyświetla komunikat błędu asynchronicznie."""
    MessageBoxHelper.show_error_async(self, title, message)

def show_warning_message(self, title: str, message: str):
    """Wyświetla ostrzeżenie asynchronicznie."""
    MessageBoxHelper.show_warning_async(self, title, message)

def show_info_message(self, title: str, message: str):
    """Wyświetla informację asynchronicznie."""
    MessageBoxHelper.show_info_async(self, title, message)

def confirm_bulk_delete(self, count: int) -> bool:
    """Potwierdza masowe usuwanie."""
    return MessageBoxHelper.confirm_question(
        self,
        "Potwierdzenie usunięcia",
        f"Czy na pewno chcesz usunąć {count} par plików?",
        QMessageBox.StandardButton.No
    )
```

---

## 🔧 POPRAWKA 2.4: Manager property caching optimization

**Lokalizacja:** Properties linie 47-100  
**Problem:** Każde property wywołuje get_manager() co może być overhead  
**Rozwiązanie:** Cache manager references dla frequently used managers

### Dodanie cache mechanism w __init__:

```python
def __init__(self, style_sheet=None):
    """
    Inicjalizuje główne okno aplikacji.
    ETAP 2.3: ManagerRegistry + Orchestrator + Caching
    """
    super().__init__()

    # Manager cache dla wydajności
    self._manager_cache = {}

    # ETAP 2.3: Inicjalizuj ManagerRegistry PRZED orchestrator
    from src.ui.main_window.manager_registry import ManagerRegistry

    self._manager_registry_new = ManagerRegistry(self)

    # ETAP 2: Centralna inicjalizacja przez Orchestrator
    from src.ui.main_window.main_window_orchestrator import MainWindowOrchestrator

    self._orchestrator = MainWindowOrchestrator(self)
    if not self._orchestrator.initialize_application():
        raise RuntimeError("Błąd inicjalizacji aplikacji przez Orchestrator")

    self.logger.info("Główne okno aplikacji zostało zainicjalizowane")
```

### Optimized property pattern dla często używanych managerów:

```python
# PRZED - always calls get_manager
@property
def gallery_manager(self):
    """Delegacja do ManagerRegistry."""
    return self._manager_registry_new.get_manager("gallery_manager")

@property
def ui_manager(self):
    """Delegacja do ManagerRegistry."""
    return self._manager_registry_new.get_manager("ui_manager")

# PO - cached access for frequently used managers
@property
def gallery_manager(self):
    """Delegacja do ManagerRegistry z cache."""
    if "gallery_manager" not in self._manager_cache:
        self._manager_cache["gallery_manager"] = self._manager_registry_new.get_manager("gallery_manager")
    return self._manager_cache["gallery_manager"]

@property
def ui_manager(self):
    """Delegacja do ManagerRegistry z cache."""
    if "ui_manager" not in self._manager_cache:
        self._manager_cache["ui_manager"] = self._manager_registry_new.get_manager("ui_manager")
    return self._manager_cache["ui_manager"]

# Dla rzadziej używanych managerów można zostawić bez cache
@property
def window_initialization_manager(self):
    """Delegacja do ManagerRegistry (bez cache - rzadko używany)."""
    return self._manager_registry_new.get_manager("window_initialization_manager")
```

### Cache cleanup w closeEvent:

```python
def closeEvent(self, event):
    """
    Obsługuje zamykanie aplikacji - ETAP 2.3: ManagerRegistry + Orchestrator + Cache cleanup.
    """
    try:
        # Wyczyść cache przed cleanup managerów
        self._manager_cache.clear()
        
        # ETAP 2.3: Cleanup ManagerRegistry PRZED orchestrator
        if hasattr(self, "_manager_registry_new"):
            self._manager_registry_new.cleanup_managers()

        # ETAP 2: Centralne zarządzanie przez Orchestrator
        self._orchestrator.handle_shutdown()
        self.window_initialization_manager.handle_close_event(event)
    except Exception as e:
        self.logger.error(f"Błąd podczas zamykania aplikacji: {e}")
        event.accept()  # Zawsze akceptuj zamknięcie
```

---

## 🔧 POPRAWKA 2.5: Import reorganization na górze pliku

**Lokalizacja:** Góra pliku, linie 6-18  
**Problem:** Imports można lepiej zorganizować i dodać missing imports  
**Rozwiązanie:** Logiczne grupowanie importów

### Stary kod importów (linie 6-18):
```python
from PyQt6.QtCore import QThreadPool, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QVBoxLayout, QWidget

from src import app_config
from src.models.file_pair import FilePair
from src.services.thread_coordinator import ThreadCoordinator
from src.ui.delegates.workers import UnifiedBaseWorker
from src.ui.directory_tree.manager import DirectoryTreeManager
from src.ui.file_operations_ui import FileOperationsUI
from src.ui.gallery_manager import GalleryManager
from src.ui.main_window.main_window_interface import MainWindowInterface
from src.ui.main_window.window_initialization_manager import WindowInitializationManager
```

### Nowy kod importów - lepiej zorganizowane:
```python
# PyQt6 imports
from PyQt6.QtCore import QThreadPool, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QVBoxLayout, QWidget

# Core application imports
from src import app_config
from src.models.file_pair import FilePair
from src.services.thread_coordinator import ThreadCoordinator

# UI component imports
from src.ui.delegates.workers import UnifiedBaseWorker
from src.ui.directory_tree.manager import DirectoryTreeManager
from src.ui.file_operations_ui import FileOperationsUI
from src.ui.gallery_manager import GalleryManager

# Main window specific imports
from src.ui.main_window.main_window_interface import MainWindowInterface
from src.ui.main_window.window_initialization_manager import WindowInitializationManager

# Additional imports - moved from inside functions for performance
from src.ui.widgets.preferences_dialog import PreferencesDialog
from src.logic.metadata.metadata_core import MetadataManager

# Note: ManagerRegistry and MainWindowOrchestrator remain as lazy imports
# in __init__ to prevent circular dependencies
```

---

## 🔧 POPRAWKA 2.6: Error handling improvement w closeEvent

**Lokalizacja:** closeEvent method (linie 190-204)  
**Problem:** Ogólny except Exception może ukrywać specyficzne problemy  
**Rozwiązanie:** Bardziej precyzyjne error handling

### Stary kod:
```python
def closeEvent(self, event):
    """
    Obsługuje zamykanie aplikacji - ETAP 2.3: ManagerRegistry + Orchestrator.
    """
    try:
        # ETAP 2.3: Cleanup ManagerRegistry PRZED orchestrator
        if hasattr(self, "_manager_registry_new"):
            self._manager_registry_new.cleanup_managers()

        # ETAP 2: Centralne zarządzanie przez Orchestrator
        self._orchestrator.handle_shutdown()
        self.window_initialization_manager.handle_close_event(event)
    except Exception as e:
        self.logger.error(f"Błąd podczas zamykania aplikacji: {e}")
        event.accept()  # Zawsze akceptuj zamknięcie
```

### Nowy kod:
```python
def closeEvent(self, event):
    """
    Obsługuje zamykanie aplikacji - ETAP 2.3: ManagerRegistry + Orchestrator + Lepsze error handling.
    """
    # Wyczyść cache na początku
    if hasattr(self, '_manager_cache'):
        self._manager_cache.clear()
    
    # Manager registry cleanup
    try:
        if hasattr(self, "_manager_registry_new"):
            self._manager_registry_new.cleanup_managers()
    except (AttributeError, RuntimeError) as e:
        self.logger.warning(f"Problem z cleanup manager registry: {e}")
        # Nie blokuj zamykania z powodu problemów z managerami
    except Exception as e:
        self.logger.error(f"Nieoczekiwany błąd cleanup manager registry: {e}", exc_info=True)

    # Orchestrator shutdown
    try:
        if hasattr(self, '_orchestrator') and self._orchestrator:
            self._orchestrator.handle_shutdown()
    except (AttributeError, RuntimeError) as e:
        self.logger.warning(f"Problem z shutdown orchestrator: {e}")
    except Exception as e:
        self.logger.error(f"Nieoczekiwany błąd shutdown orchestrator: {e}", exc_info=True)

    # Window initialization manager cleanup
    try:
        if hasattr(self, 'window_initialization_manager'):
            self.window_initialization_manager.handle_close_event(event)
        else:
            # Jeśli nie ma manager, accept event bezpośrednio
            event.accept()
    except (AttributeError, RuntimeError) as e:
        self.logger.warning(f"Problem z window initialization manager: {e}")
        event.accept()  # Accept mimo problemów
    except Exception as e:
        self.logger.error(f"Nieoczekiwany błąd window manager: {e}", exc_info=True)
        event.accept()  # Accept mimo problemów

    self.logger.info("Zamykanie głównego okna ukończone")
```

---

## ✅ CHECKLISTA FUNKCJONALNOŚCI I ZALEŻNOŚCI

### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - MainWindow nadal się tworzy i wyświetla
- [ ] **API kompatybilność** - wszystkie publiczne metody działają identycznie
- [ ] **Manager properties** - wszystkie @property zwracają poprawne managery
- [ ] **MessageBox methods** - show_error_message, show_about etc. działają
- [ ] **Logowanie** - self.logger nadal działa we wszystkich metodach
- [ ] **Orchestrator integration** - MainWindowOrchestrator nadal inicjalizuje UI
- [ ] **Cache efficiency** - manager access jest szybszy (optional performance test)
- [ ] **Thread safety** - async message boxes nadal działają asynchronicznie
- [ ] **Memory management** - closeEvent properly cleans up cache i managery
- [ ] **Performance** - window creation time nie pogorszony

### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - wszystkie imports działają (PyQt6, src.*)
- [ ] **ManagerRegistry** - nadal zwraca wszystkie potrzebne managery
- [ ] **MainWindowOrchestrator** - nadal inicjalizuje aplikację
- [ ] **Lazy imports** - ManagerRegistry i Orchestrator importy w __init__ działają
- [ ] **Backward compatibility** - klasy używające MainWindow nadal działają
- [ ] **MessageBoxHelper** - nowa utility class nie powoduje conflicts
- [ ] **Manager dependencies** - managery nadal mają dostęp do siebie nawzajem
- [ ] **Qt signal/slot** - wszystkie Qt connections nadal działają
- [ ] **PreferencesDialog** - dialog preference nadal się otwiera
- [ ] **MetadataManager** - metadata operations nadal działają

### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - każda zmodyfikowana metoda testowana izolowanie
- [ ] **Test integracyjny** - MainWindow z resztą aplikacji
- [ ] **Test regresyjny** - aplikacja nadal uruchamia się i działa normalnie
- [ ] **Test wydajnościowy** - manager access time, window creation time
- [ ] **Test UI workflow** - podstawowe user actions (open folder, show preferences)
- [ ] **Test message boxes** - wszystkie typy komunikatów wyświetlają się poprawnie
- [ ] **Test cleanup** - closeEvent properly cleans up bez memory leaks

### **DOKUMENTACJA WERYFIKACYJNA:**

- [ ] **Code comments** - MessageBoxHelper ma poprawną dokumentację
- [ ] **Method docstrings** - zmodyfikowane metody mają zaktualizowane opisy
- [ ] **Import organization** - importy są logicznie pogrupowane i udokumentowane
- [ ] **Cache mechanism** - cache logic jest udokumentowany
- [ ] **Error handling** - nowe error handling patterns są udokumentowane

### **KRYTERIA SUKCESU:**

- **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem
- **BRAK FAILED TESTS** - wszystkie testy muszą przejść
- **PERFORMANCE BUDGET** - manager access max 5% szybszy, window creation nie pogorszona
- **MEMORY USAGE** - cache mechanizm max 1% wzrost memory, proper cleanup
- **UI RESPONSIVENESS** - async message boxes nadal nie blokują UI

### **PROCES WERYFIKACJI:**

1. Implementacja poprawki
2. Wypełnienie checklisty funkcjonalności  
3. Wypełnienie checklisty zależności
4. Przeprowadzenie testów weryfikacyjnych
5. **OBOWIĄZKOWA KONTROLA POSTĘPU** (2/50+ etapów)
6. Sprawdzenie dokumentacji
7. Jeśli WSZYSTKO OK → wdrożenie
8. Jeśli PROBLEM → naprawa → powtórzenie weryfikacji
9. **RAPORT POSTĘPU** przed przejściem do następnego etapu

---

## 📈 OCZEKIWANE KORZYŚCI

**Po wdrożeniu poprawek:**

- ⚡ **Wydajność:** 3-5% szybszy dostęp do frequently used managers przez cache
- 🐛 **Debugging:** Lepsze error handling w closeEvent - łatwiejsze znajdowanie problemów z cleanup
- 🧹 **Clean Code:** Eliminacja duplikatów importów, lepsze organizacje kodu
- 🔧 **Maintainability:** MessageBoxHelper utility czyni kod bardziej DRY i łatwiejszy do maintain
- 📝 **Pylint compliance:** Usunięcie pylint warnings o duplicate imports

**Metryki przed i po:**
- Import duplicates: 5 duplikatów → 0 duplikatów
- Manager access time: potentially 10-20% szybszy dla cached properties
- Pylint warnings: reduce o ~8 warnings z tego pliku
- Lines of code: potencjalny wzrost o ~50 linii (MessageBoxHelper) ale lepsze organizacje