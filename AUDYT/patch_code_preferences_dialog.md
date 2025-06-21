# 🛠️ FRAGMENTY KODU - PREFERENCES DIALOG REFACTORING

**Plik źródłowy:** `src/ui/widgets/preferences_dialog.py`  
**Data:** 2025-01-21  
**Typ refaktoryzacji:** Podział monolitycznej klasy na komponenty

---

## 1.1 NOWA KLASA BAZOWA - PreferencesTabBase

**Lokalizacja:** `src/ui/widgets/preferences/tab_base.py` (NOWY PLIK)

```python
"""
Klasa bazowa dla zakładek okna preferencji.
Implementuje common interface i utility methods.
"""

from abc import ABC, abstractmethod
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget
from src.app_config import AppConfig


class PreferencesTabBase(QWidget, ABC):
    """Abstrakcyjna klasa bazowa dla wszystkich zakładek preferencji."""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, app_config: AppConfig, parent=None):
        """
        Inicjalizuje bazową zakładkę.
        
        Args:
            app_config: Instancja konfiguracji aplikacji
            parent: Parent widget
        """
        super().__init__(parent)
        self.app_config = app_config
        self.changes_made = False
        
        self._setup_ui()
        self._load_settings()
        self._connect_signals()
    
    @abstractmethod
    def _setup_ui(self) -> None:
        """Tworzy interfejs użytkownika zakładki. MUSI być implementowane."""
        pass
    
    @abstractmethod
    def _load_settings(self) -> None:
        """Ładuje ustawienia z app_config. MUSI być implementowane."""
        pass
    
    @abstractmethod
    def _save_settings(self) -> None:
        """Zapisuje ustawienia do app_config. MUSI być implementowane."""
        pass
    
    @abstractmethod
    def _connect_signals(self) -> None:
        """Podłącza sygnały kontrolek. MUSI być implementowane."""
        pass
    
    def _mark_changed(self) -> None:
        """Oznacza że ustawienia zostały zmienione."""
        self.changes_made = True
        self.settings_changed.emit()
    
    def reset_to_defaults(self) -> None:
        """Resetuje zakładkę do wartości domyślnych."""
        self._load_settings()
        self.changes_made = False
    
    def apply_settings(self) -> bool:
        """
        Stosuje ustawienia.
        
        Returns:
            bool: True jeśli sukces, False jeśli błąd
        """
        try:
            self._save_settings()
            self.changes_made = False
            return True
        except Exception as e:
            # Log error but don't raise - let parent handle
            import logging
            logging.error("Błąd zapisywania ustawień w %s: %s", 
                         self.__class__.__name__, str(e))
            return False
    
    def has_changes(self) -> bool:
        """Zwraca True jeśli są niezapisane zmiany."""
        return self.changes_made
```

---

## 1.2 ZAKŁADKA OGÓLNA - GeneralPreferencesTab

**Lokalizacja:** `src/ui/widgets/preferences/general_tab.py` (NOWY PLIK)

```python
"""
Zakładka ogólnych ustawień aplikacji.
Wydzielona z preferences_dialog.py (linie 72-137).
"""

import logging
from PyQt6.QtWidgets import (
    QVBoxLayout, QGroupBox, QGridLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QFileDialog, QMessageBox
)

from .tab_base import PreferencesTabBase


class GeneralPreferencesTab(PreferencesTabBase):
    """Zakładka ogólnych ustawień: ścieżki, automatyzacja, powiadomienia."""
    
    def _setup_ui(self) -> None:
        """Tworzy interfejs zakładki ogólnej."""
        layout = QVBoxLayout(self)
        
        # Grupa: Domyślne ścieżki
        self._create_paths_group(layout)
        
        # Grupa: Automatyzacja  
        self._create_automation_group(layout)
        
        # Grupa: Powiadomienia
        self._create_notifications_group(layout)
        
        layout.addStretch()
    
    def _create_paths_group(self, parent_layout: QVBoxLayout) -> None:
        """Tworzy grupę ustawień ścieżek."""
        paths_group = QGroupBox("Domyślne ścieżki")
        paths_layout = QGridLayout(paths_group)
        
        # Domyślny folder roboczy
        paths_layout.addWidget(QLabel("Domyślny folder roboczy:"), 0, 0)
        self.default_folder_edit = QLineEdit()
        self.default_folder_browse = QPushButton("Przeglądaj...")
        self.default_folder_browse.clicked.connect(self._browse_default_folder)
        paths_layout.addWidget(self.default_folder_edit, 0, 1)
        paths_layout.addWidget(self.default_folder_browse, 0, 2)
        
        # Folder dla eksportu
        paths_layout.addWidget(QLabel("Folder eksportu:"), 1, 0)
        self.export_folder_edit = QLineEdit()
        self.export_folder_browse = QPushButton("Przeglądaj...")
        self.export_folder_browse.clicked.connect(self._browse_export_folder)
        paths_layout.addWidget(self.export_folder_edit, 1, 1)
        paths_layout.addWidget(self.export_folder_browse, 1, 2)
        
        # Przycisk do ustawienia aktualnego folderu jako domyślny
        self.set_current_as_default_btn = QPushButton(
            "🔒 Ustaw aktualny folder jako domyślny"
        )
        self.set_current_as_default_btn.clicked.connect(self._set_current_as_default)
        paths_layout.addWidget(self.set_current_as_default_btn, 2, 0, 1, 3)
        
        parent_layout.addWidget(paths_group)
    
    def _create_automation_group(self, parent_layout: QVBoxLayout) -> None:
        """Tworzy grupę ustawień automatyzacji."""
        automation_group = QGroupBox("Automatyzacja")
        automation_layout = QVBoxLayout(automation_group)
        
        self.auto_save_metadata = QCheckBox("Automatycznie zapisuj metadane")
        self.auto_load_last_folder = QCheckBox("Załaduj ostatni folder przy starcie")
        self.auto_backup_metadata = QCheckBox("Twórz kopie zapasowe metadanych")
        
        automation_layout.addWidget(self.auto_save_metadata)
        automation_layout.addWidget(self.auto_load_last_folder)
        automation_layout.addWidget(self.auto_backup_metadata)
        
        parent_layout.addWidget(automation_group)
    
    def _create_notifications_group(self, parent_layout: QVBoxLayout) -> None:
        """Tworzy grupę ustawień powiadomień."""
        notifications_group = QGroupBox("Powiadomienia")
        notifications_layout = QVBoxLayout(notifications_group)
        
        self.show_completion_messages = QCheckBox(
            "Pokaż komunikaty o zakończeniu operacji"
        )
        self.show_error_details = QCheckBox("Pokaż szczegóły błędów")
        self.confirm_delete_operations = QCheckBox("Potwierdź operacje usuwania")
        
        notifications_layout.addWidget(self.show_completion_messages)
        notifications_layout.addWidget(self.show_error_details)
        notifications_layout.addWidget(self.confirm_delete_operations)
        
        parent_layout.addWidget(notifications_group)
    
    def _load_settings(self) -> None:
        """Ładuje ustawienia ogólne z konfiguracji."""
        # Ścieżki
        self.default_folder_edit.setText(
            self.app_config.get("default_working_directory", "")
        )
        self.export_folder_edit.setText(
            self.app_config.get("default_export_directory", "")
        )
        
        # Automatyzacja
        self.auto_save_metadata.setChecked(
            self.app_config.get("auto_save_metadata", True)
        )
        self.auto_load_last_folder.setChecked(
            self.app_config.get("auto_load_last_folder", True)
        )
        self.auto_backup_metadata.setChecked(
            self.app_config.get("auto_backup_metadata", False)
        )
        
        # Powiadomienia
        self.show_completion_messages.setChecked(
            self.app_config.get("show_completion_messages", True)
        )
        self.show_error_details.setChecked(
            self.app_config.get("show_error_details", True)
        )
        self.confirm_delete_operations.setChecked(
            self.app_config.get("confirm_delete_operations", True)
        )
    
    def _save_settings(self) -> None:
        """Zapisuje ustawienia ogólne do konfiguracji."""
        # Ścieżki
        self.app_config.set("default_working_directory", self.default_folder_edit.text())
        self.app_config.set("default_export_directory", self.export_folder_edit.text())
        
        # Automatyzacja
        self.app_config.set("auto_save_metadata", self.auto_save_metadata.isChecked())
        self.app_config.set("auto_load_last_folder", self.auto_load_last_folder.isChecked())
        self.app_config.set("auto_backup_metadata", self.auto_backup_metadata.isChecked())
        
        # Powiadomienia
        self.app_config.set("show_completion_messages", self.show_completion_messages.isChecked())
        self.app_config.set("show_error_details", self.show_error_details.isChecked())
        self.app_config.set("confirm_delete_operations", self.confirm_delete_operations.isChecked())
    
    def _connect_signals(self) -> None:
        """Podłącza sygnały kontrolek ogólnych."""
        # Ścieżki
        self.default_folder_edit.textChanged.connect(self._mark_changed)
        self.export_folder_edit.textChanged.connect(self._mark_changed)
        
        # Automatyzacja
        self.auto_save_metadata.toggled.connect(self._mark_changed)
        self.auto_load_last_folder.toggled.connect(self._mark_changed)
        self.auto_backup_metadata.toggled.connect(self._mark_changed)
        
        # Powiadomienia
        self.show_completion_messages.toggled.connect(self._mark_changed)
        self.show_error_details.toggled.connect(self._mark_changed)
        self.confirm_delete_operations.toggled.connect(self._mark_changed)
    
    def _browse_default_folder(self) -> None:
        """Otwiera dialog wyboru domyślnego folderu."""
        folder = QFileDialog.getExistingDirectory(
            self, "Wybierz domyślny folder roboczy"
        )
        if folder:
            self.default_folder_edit.setText(folder)
    
    def _browse_export_folder(self) -> None:
        """Otwiera dialog wyboru folderu eksportu."""
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder eksportu")
        if folder:
            self.export_folder_edit.setText(folder)
    
    def _set_current_as_default(self) -> None:
        """Ustawia aktualny folder głównego okna jako domyślny."""
        # Find main window through parent chain
        main_window = self._find_main_window()
        
        if (main_window and hasattr(main_window, "controller") 
            and main_window.controller.current_directory):
            current_folder = main_window.controller.current_directory
            self.default_folder_edit.setText(current_folder)
            self._mark_changed()
            
            # Use proper logging level and format
            logging.debug("Ustawienie domyślnego folderu na: %s", current_folder)
        else:
            QMessageBox.information(
                self, "Informacja", "Nie ma otwartego folderu do ustawienia!"
            )
    
    def _find_main_window(self):
        """Znajduje główne okno przez łańcuch parent widgets."""
        widget = self.parent()
        while widget:
            if hasattr(widget, "controller"):
                return widget
            widget = widget.parent()
        return None
```

---

## 1.3 FACTORY PATTERN - PreferencesTabFactory

**Lokalizacja:** `src/ui/widgets/preferences/tab_factory.py` (NOWY PLIK)

```python
"""
Factory dla tworzenia zakładek preferencji.
Implementuje lazy loading i dependency injection.
"""

from typing import Dict, Type, Optional
from src.app_config import AppConfig

from .tab_base import PreferencesTabBase
from .general_tab import GeneralPreferencesTab
from .scanning_tab import ScanningPreferencesTab
from .ui_tab import UIPreferencesTab
from .advanced_tab import AdvancedPreferencesTab


class PreferencesTabFactory:
    """Factory do tworzenia zakładek preferencji z lazy loading."""
    
    def __init__(self, app_config: AppConfig):
        """
        Inicjalizuje factory.
        
        Args:
            app_config: Instancja konfiguracji aplikacji
        """
        self.app_config = app_config
        self._tab_registry: Dict[str, Type[PreferencesTabBase]] = {
            "general": GeneralPreferencesTab,
            "scanning": ScanningPreferencesTab,
            "ui": UIPreferencesTab,
            "advanced": AdvancedPreferencesTab,
        }
        self._created_tabs: Dict[str, PreferencesTabBase] = {}
    
    def create_tab(self, tab_type: str, parent=None) -> Optional[PreferencesTabBase]:
        """
        Tworzy zakładkę danego typu (lazy loading).
        
        Args:
            tab_type: Typ zakładki ("general", "scanning", "ui", "advanced")
            parent: Parent widget
            
        Returns:
            PreferencesTabBase: Instancja zakładki lub None jeśli błąd
        """
        if tab_type in self._created_tabs:
            return self._created_tabs[tab_type]
        
        if tab_type not in self._tab_registry:
            import logging
            logging.error("Nieznany typ zakładki preferencji: %s", tab_type)
            return None
        
        try:
            tab_class = self._tab_registry[tab_type]
            tab_instance = tab_class(self.app_config, parent)
            self._created_tabs[tab_type] = tab_instance
            return tab_instance
        except Exception as e:
            import logging
            logging.error("Błąd tworzenia zakładki %s: %s", tab_type, str(e))
            return None
    
    def get_tab_info(self) -> Dict[str, str]:
        """
        Zwraca informacje o dostępnych zakładkach.
        
        Returns:
            Dict mapujący typ zakładki na jej nazwę wyświetlaną
        """
        return {
            "general": "Ogólne",
            "scanning": "Skanowanie", 
            "ui": "Interfejs",
            "advanced": "Zaawansowane"
        }
    
    def register_tab_type(self, tab_type: str, tab_class: Type[PreferencesTabBase]) -> None:
        """
        Rejestruje nowy typ zakładki (extensibility).
        
        Args:
            tab_type: Identyfikator typu zakładki
            tab_class: Klasa implementująca PreferencesTabBase
        """
        self._tab_registry[tab_type] = tab_class
    
    def clear_cache(self) -> None:
        """Czyści cache utworzonych zakładek."""
        self._created_tabs.clear()
    
    def get_created_tabs(self) -> Dict[str, PreferencesTabBase]:
        """Zwraca słownik już utworzonych zakładek."""
        return self._created_tabs.copy()
```

---

## 1.4 ZREFAKTORYZOWANA GŁÓWNA KLASA - PreferencesDialog

**Lokalizacja:** `src/ui/widgets/preferences_dialog.py` (NADPISANIE ISTNIEJĄCEGO)

```python
"""
Dialog preferencji aplikacji CFAB_3DHUB - zrefaktoryzowana wersja.
ETAP 2.1: Podział na komponenty z zachowaniem backward compatibility.
"""

import logging
from typing import Dict, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, 
    QWidget, QMessageBox
)

from src.app_config import AppConfig
from .preferences.tab_factory import PreferencesTabFactory
from .preferences.tab_base import PreferencesTabBase


class PreferencesDialog(QDialog):
    """
    Dialog preferencji aplikacji - facade pattern.
    Zachowuje backward compatibility, deleguje pracę do komponentów.
    """

    preferences_changed = pyqtSignal()  # PUBLIC API - zachowane

    def __init__(self, parent=None):
        """
        Inicjalizuje dialog preferencji.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.app_config = AppConfig()
        self._tab_factory = PreferencesTabFactory(self.app_config)
        self._tabs: Dict[str, PreferencesTabBase] = {}
        
        # UI setup
        self.setWindowTitle("Preferencje - CFAB_3DHUB")
        self.setModal(True)
        self.resize(600, 500)
        
        # Flagi do śledzenia zmian (backward compatibility)
        self.changes_made = False
        
        self._setup_ui()
        self._load_tabs()
        self._connect_tab_signals()

    def _setup_ui(self) -> None:
        """Tworzy podstawowy interfejs użytkownika."""
        layout = QVBoxLayout(self)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Przyciski na dole
        self._create_button_box()
        layout.addWidget(self.button_box)

    def _load_tabs(self) -> None:
        """Ładuje wszystkie zakładki przez factory (lazy loading)."""
        tab_info = self._tab_factory.get_tab_info()
        
        for tab_type, tab_title in tab_info.items():
            tab = self._tab_factory.create_tab(tab_type, self)
            if tab:
                self._tabs[tab_type] = tab
                self.tab_widget.addTab(tab, tab_title)
            else:
                logging.warning("Nie udało się utworzyć zakładki: %s", tab_type)

    def _create_button_box(self) -> None:
        """Tworzy przyciski na dole okna."""
        self.button_box = QWidget()
        layout = QHBoxLayout(self.button_box)
        
        # Przycisk Resetuj
        self.reset_btn = QPushButton("Resetuj")
        self.reset_btn.clicked.connect(self._reset_current_tab)
        layout.addWidget(self.reset_btn)
        
        layout.addStretch()
        
        # Przyciski OK, Anuluj, Zastosuj
        self.apply_btn = QPushButton("Zastosuj")
        self.apply_btn.clicked.connect(self._apply_settings)
        self.apply_btn.setEnabled(False)
        layout.addWidget(self.apply_btn)
        
        self.cancel_btn = QPushButton("Anuluj")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)
        
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self._accept_and_apply)
        self.ok_btn.setDefault(True)
        layout.addWidget(self.ok_btn)

    def _connect_tab_signals(self) -> None:
        """Podłącza sygnały od wszystkich zakładek."""
        for tab in self._tabs.values():
            tab.settings_changed.connect(self._on_tab_changed)

    def _on_tab_changed(self) -> None:
        """Obsługuje zmiany w zakładkach."""
        self.changes_made = True
        self.apply_btn.setEnabled(True)

    def _reset_current_tab(self) -> None:
        """Resetuje ustawienia bieżącej zakładki."""
        current_index = self.tab_widget.currentIndex()
        if current_index < 0:
            return
            
        tab_name = self.tab_widget.tabText(current_index)
        
        reply = QMessageBox.question(
            self,
            "Potwierdź",
            f"Czy na pewno chcesz zresetować ustawienia zakładki '{tab_name}'?",
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Find the tab by index
            tab_types = list(self._tabs.keys())
            if current_index < len(tab_types):
                tab_type = tab_types[current_index]
                if tab_type in self._tabs:
                    self._tabs[tab_type].reset_to_defaults()

    def _apply_settings(self) -> None:
        """Stosuje ustawienia bez zamykania okna."""
        try:
            success = self._save_all_settings()
            if success:
                self.preferences_changed.emit()
                self.changes_made = False
                self.apply_btn.setEnabled(False)
                QMessageBox.information(self, "Sukces", "Ustawienia zostały zastosowane.")
            else:
                QMessageBox.warning(self, "Ostrzeżenie", "Niektóre ustawienia nie zostały zapisane.")
        except Exception as e:
            logging.error("Błąd stosowania ustawień: %s", str(e))
            QMessageBox.critical(self, "Błąd", f"Nie można zastosować ustawień: {e}")

    def _accept_and_apply(self) -> None:
        """Stosuje ustawienia i zamyka okno."""
        if self.changes_made:
            try:
                success = self._save_all_settings()
                if success:
                    self.preferences_changed.emit()
                else:
                    QMessageBox.warning(self, "Ostrzeżenie", "Niektóre ustawienia nie zostały zapisane.")
                    return
            except Exception as e:
                logging.error("Błąd zapisywania ustawień: %s", str(e))
                QMessageBox.critical(self, "Błąd", f"Nie można zapisać ustawień: {e}")
                return
        self.accept()

    def _save_all_settings(self) -> bool:
        """
        Zapisuje ustawienia ze wszystkich zakładek.
        
        Returns:
            bool: True jeśli wszystkie zakładki zapisane pomyślnie
        """
        success = True
        for tab_type, tab in self._tabs.items():
            if not tab.apply_settings():
                logging.error("Błąd zapisywania ustawień w zakładce: %s", tab_type)
                success = False
        
        if success:
            # Save to file only if all tabs succeeded
            try:
                self.app_config.save()
            except Exception as e:
                logging.error("Błąd zapisywania konfiguracji do pliku: %s", str(e))
                return False
        
        return success

    def closeEvent(self, event) -> None:
        """Obsługuje zamykanie okna z sprawdzeniem niezapisanych zmian."""
        if self.changes_made:
            reply = QMessageBox.question(
                self,
                "Niezapisane zmiany",
                "Masz niezapisane zmiany. Czy chcesz je zapisać?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )

            if reply == QMessageBox.StandardButton.Save:
                try:
                    success = self._save_all_settings()
                    if success:
                        self.preferences_changed.emit()
                        event.accept()
                    else:
                        QMessageBox.warning(self, "Ostrzeżenie", "Nie udało się zapisać wszystkich ustawień.")
                        event.ignore()
                except Exception as e:
                    logging.error("Błąd zapisywania przy zamykaniu: %s", str(e))
                    QMessageBox.critical(self, "Błąd", f"Nie można zapisać ustawień: {e}")
                    event.ignore()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    # BACKWARD COMPATIBILITY METHODS
    # Zachowane publiczne metody dla kompatybilności z istniejącym kodem
    
    def _load_current_settings(self) -> None:
        """
        Backward compatibility method.
        Deleguje do zakładek.
        """
        for tab in self._tabs.values():
            tab.reset_to_defaults()

    def _clear_thumbnail_cache(self) -> None:
        """
        Backward compatibility method dla advanced tab.
        """
        if "advanced" in self._tabs:
            advanced_tab = self._tabs["advanced"]
            if hasattr(advanced_tab, '_clear_thumbnail_cache'):
                advanced_tab._clear_thumbnail_cache()

    def _reset_all_settings(self) -> None:
        """
        Backward compatibility method dla advanced tab.
        """
        if "advanced" in self._tabs:
            advanced_tab = self._tabs["advanced"]
            if hasattr(advanced_tab, '_reset_all_settings'):
                advanced_tab._reset_all_settings()
```

---

## 1.5 AKTUALIZACJA __INIT__.PY

**Lokalizacja:** `src/ui/widgets/preferences/__init__.py` (NOWY PLIK)

```python
"""
Preferences module for CFAB_3DHUB.
Zawiera zrefaktoryzowane komponenty dialogu preferencji.
"""

from .tab_base import PreferencesTabBase
from .tab_factory import PreferencesTabFactory
from .general_tab import GeneralPreferencesTab

# Only expose what's needed for imports
__all__ = [
    'PreferencesTabBase',
    'PreferencesTabFactory', 
    'GeneralPreferencesTab',
]
```

---

## 1.6 PRZYKŁAD TESTÓW JEDNOSTKOWYCH

**Lokalizacja:** `tests/test_preferences_refactored.py` (NOWY PLIK)

```python
"""
Testy jednostkowe dla zrefaktoryzowanego dialogu preferencji.
"""

import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
import sys

# Ensure QApplication exists for widget tests
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.app_config import AppConfig
from src.ui.widgets.preferences.general_tab import GeneralPreferencesTab
from src.ui.widgets.preferences.tab_factory import PreferencesTabFactory
from src.ui.widgets.preferences_dialog import PreferencesDialog


class TestGeneralPreferencesTab(unittest.TestCase):
    """Testy dla zakładki ogólnej."""
    
    def setUp(self):
        """Setup przed każdym testem."""
        self.app_config = MagicMock(spec=AppConfig)
        self.tab = GeneralPreferencesTab(self.app_config)
    
    def test_initialization(self):
        """Test poprawnej inicjalizacji zakładki."""
        self.assertIsNotNone(self.tab.default_folder_edit)
        self.assertIsNotNone(self.tab.export_folder_edit)
        self.assertIsNotNone(self.tab.auto_save_metadata)
    
    def test_load_settings(self):
        """Test ładowania ustawień."""
        self.app_config.get.side_effect = lambda key, default: {
            "default_working_directory": "/test/path",
            "auto_save_metadata": True,
        }.get(key, default)
        
        self.tab._load_settings()
        
        self.assertEqual(self.tab.default_folder_edit.text(), "/test/path")
        self.assertTrue(self.tab.auto_save_metadata.isChecked())
    
    def test_save_settings(self):
        """Test zapisywania ustawień."""
        self.tab.default_folder_edit.setText("/new/path")
        self.tab.auto_save_metadata.setChecked(False)
        
        self.tab._save_settings()
        
        self.app_config.set.assert_any_call("default_working_directory", "/new/path")
        self.app_config.set.assert_any_call("auto_save_metadata", False)
    
    def test_changes_tracking(self):
        """Test śledzenia zmian."""
        self.assertFalse(self.tab.has_changes())
        
        self.tab.default_folder_edit.setText("changed")
        
        self.assertTrue(self.tab.has_changes())


class TestPreferencesTabFactory(unittest.TestCase):
    """Testy dla factory zakładek."""
    
    def setUp(self):
        """Setup przed każdym testem."""
        self.app_config = MagicMock(spec=AppConfig)
        self.factory = PreferencesTabFactory(self.app_config)
    
    def test_create_general_tab(self):
        """Test tworzenia zakładki ogólnej."""
        tab = self.factory.create_tab("general")
        
        self.assertIsInstance(tab, GeneralPreferencesTab)
        self.assertEqual(tab.app_config, self.app_config)
    
    def test_lazy_loading(self):
        """Test lazy loading - ta sama instancja przy drugim wywołaniu."""
        tab1 = self.factory.create_tab("general")
        tab2 = self.factory.create_tab("general")
        
        self.assertIs(tab1, tab2)
    
    def test_invalid_tab_type(self):
        """Test obsługi niepoprawnego typu zakładki."""
        tab = self.factory.create_tab("nonexistent")
        
        self.assertIsNone(tab)
    
    def test_get_tab_info(self):
        """Test zwracania informacji o zakładkach."""
        info = self.factory.get_tab_info()
        
        self.assertIn("general", info)
        self.assertEqual(info["general"], "Ogólne")


class TestPreferencesDialog(unittest.TestCase):
    """Testy dla głównego dialogu preferencji."""
    
    def setUp(self):
        """Setup przed każdym testem."""
        with patch('src.ui.widgets.preferences_dialog.AppConfig'):
            self.dialog = PreferencesDialog()
    
    def test_initialization(self):
        """Test poprawnej inicjalizacji dialogu."""
        self.assertIsNotNone(self.dialog.tab_widget)
        self.assertIsNotNone(self.dialog.button_box)
        self.assertEqual(self.dialog.windowTitle(), "Preferencje - CFAB_3DHUB")
    
    def test_backward_compatibility_signal(self):
        """Test zachowania sygnału preferences_changed."""
        self.assertTrue(hasattr(self.dialog, 'preferences_changed'))
    
    def test_tabs_creation(self):
        """Test czy wszystkie zakładki zostały utworzone."""
        # Dialog should have created tabs in _load_tabs
        self.assertGreater(self.dialog.tab_widget.count(), 0)
    
    @patch('src.ui.widgets.preferences_dialog.QMessageBox')
    def test_apply_settings(self, mock_msgbox):
        """Test stosowania ustawień."""
        self.dialog.changes_made = True
        
        with patch.object(self.dialog, '_save_all_settings', return_value=True):
            self.dialog._apply_settings()
        
        self.assertFalse(self.dialog.changes_made)
        self.assertFalse(self.dialog.apply_btn.isEnabled())


if __name__ == '__main__':
    unittest.main()
```

---

## 🎯 INSTRUKCJE IMPLEMENTACJI

### **KOLEJNOŚĆ WDRAŻANIA:**

1. **Utworzenie struktura katalogów:**
   ```bash
   mkdir -p src/ui/widgets/preferences
   ```

2. **Utworzenie plików bazowych:**
   - `src/ui/widgets/preferences/__init__.py`
   - `src/ui/widgets/preferences/tab_base.py`
   - `src/ui/widgets/preferences/tab_factory.py`

3. **Utworzenie pierwszej zakładki:**
   - `src/ui/widgets/preferences/general_tab.py`

4. **Backup istniejącego pliku:**
   ```bash
   cp src/ui/widgets/preferences_dialog.py AUDYT/backups/preferences_dialog_backup_2025-01-21.py
   ```

5. **Zrefaktoryzowanie głównej klasy:**
   - Nadpisanie `src/ui/widgets/preferences_dialog.py`

6. **Implementacja pozostałych zakładek:**
   - `scanning_tab.py`, `ui_tab.py`, `advanced_tab.py`

7. **Testy i weryfikacja:**
   - Utworzenie `tests/test_preferences_refactored.py`
   - Uruchomienie testów aplikacji

### **PUNKTY WERYFIKACJI:**

- [ ] **Import test:** `from src.ui.widgets.preferences_dialog import PreferencesDialog`
- [ ] **Dialog creation:** `dialog = PreferencesDialog()`
- [ ] **Dialog opening:** `dialog.show()`
- [ ] **Settings loading:** Sprawdzenie czy ustawienia się ładują
- [ ] **Settings saving:** Sprawdzenie czy ustawienia się zapisują
- [ ] **Signal emission:** Sprawdzenie czy `preferences_changed` jest emitowane

### **ROLLBACK PLAN:**

Jeśli wystąpią problemy:
```bash
cp AUDYT/backups/preferences_dialog_backup_2025-01-21.py src/ui/widgets/preferences_dialog.py
rm -rf src/ui/widgets/preferences/
```