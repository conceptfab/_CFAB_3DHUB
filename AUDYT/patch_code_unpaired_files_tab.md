# 📝 FRAGMENTY KODU DO POPRAWEK - unpaired_files_tab.py

## 🎯 ETAP 1.1: ELIMINACJA DUPLIKACJI KODU

### **1.1.1 USUNIĘCIE KLASY UnpairedPreviewTile**

**PLIK:** `src/ui/widgets/unpaired_files_tab.py`  
**LINIE:** 41-282  
**AKCJA:** USUŃ CAŁĄ KLASĘ

```python
# USUŃ CAŁĄ KLASĘ UnpairedPreviewTile (linie 41-282)
# Zastąp użyciem FileTileWidget z flagą show_metadata=False
```

### **1.1.2 DODANIE METODY W FileTileWidget**

**PLIK:** `src/ui/widgets/file_tile_widget.py`  
**LINIE:** Po metodzie `__init__`  
**AKCJA:** DODAJ METODĘ

```python
@classmethod
def create_simple_tile(cls, file_pair, parent=None, show_metadata=False):
    """
    Tworzy uproszczony kafelek bez metadanych.

    Args:
        file_pair: Obiekt FilePair
        parent: Widget nadrzędny
        show_metadata: Czy pokazywać metadane (gwiazdki, tagi)

    Returns:
        FileTileWidget z ukrytymi metadanymi
    """
    tile = cls(file_pair, parent=parent)
    if not show_metadata:
        tile._metadata_component.hide()
    return tile
```

## 🎯 ETAP 1.2: UPROSZCZENIE LOGIKI CHECKBOXÓW

### **1.2.1 UPROSZCZENIE METODY \_on_preview_checkbox_changed**

**PLIK:** `src/ui/widgets/unpaired_files_tab.py`  
**LINIE:** 498-533  
**AKCJA:** ZASTĄP

```python
def _on_preview_checkbox_changed(self, checkbox, preview_path, state):
    """
    Obsługuje zmianę stanu checkboxa - uproszczona wersja.
    """
    if state == Qt.CheckState.Checked.value:
        # Znajdź i zaznacz element w liście
        for i in range(self.unpaired_previews_list_widget.count()):
            item = self.unpaired_previews_list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == preview_path:
                self.unpaired_previews_list_widget.setCurrentItem(item)
                break
    else:
        # Odznacz element w liście
        current_item = self.unpaired_previews_list_widget.currentItem()
        if (current_item and
            current_item.data(Qt.ItemDataRole.UserRole) == preview_path):
            self.unpaired_previews_list_widget.setCurrentItem(None)

    # Aktualizuj stan przycisku
    self._update_pair_button_state()
```

## 🎯 ETAP 1.3: OPTYMALIZACJA LOGOWANIA

### **1.3.1 ZMIANA POZIOMÓW LOGÓW**

**PLIK:** `src/ui/widgets/unpaired_files_tab.py`  
**LINIE:** 316, 325, 330, 335, 340, 345, 350, 355, 360, 365, 370, 375, 380, 385  
**AKCJA:** ZMIEŃ INFO → DEBUG

```python
# ZMIEŃ WSZYSTKIE logging.debug() NA logging.debug()
# USUŃ NADMIAROWE LOGI DLA OPERACJI UI

def create_unpaired_files_tab(self) -> QWidget:
    """Tworzy zakładkę niesparowanych plików."""
    # USUŃ: logging.debug("Creating unpaired files tab")

    self.unpaired_files_tab = QWidget()
    self.unpaired_files_layout = QVBoxLayout(self.unpaired_files_tab)
    self.unpaired_files_layout.setContentsMargins(5, 5, 5, 5)
    # USUŃ: logging.debug("Basic widget and layout created")

    # Splitter dla dwóch list
    self.unpaired_splitter = QSplitter()
    # USUŃ: logging.debug("Splitter created")

    # Lista niesparowanych archiwów
    # USUŃ: logging.debug("Creating archives list")
    self._create_unpaired_archives_list()
    # USUŃ: logging.debug("Archives list created successfully")

    # Lista niesparowanych podglądów
    # USUŃ: logging.debug("Creating previews list")
    self._create_unpaired_previews_list()
    # USUŃ: logging.debug("Previews list created successfully")

    # ... reszta kodu bez logów
```

### **1.3.2 KONSOLIDACJA KOMUNIKATÓW BŁĘDÓW**

**PLIK:** `src/ui/widgets/unpaired_files_tab.py`  
**LINIE:** 468-497  
**AKCJA:** UPROŚĆ

```python
def _show_preview_dialog(self, preview_path: str):
    """Wyświetla okno dialogowe z podglądem obrazu."""
    if not preview_path or not os.path.exists(preview_path):
        QMessageBox.warning(
            self.main_window, "Brak Podglądu", "Plik podglądu nie istnieje."
        )
        return

    try:
        pixmap = QPixmap(preview_path)
        if pixmap.isNull():
            raise ValueError("Nie udało się załadować obrazu.")

        dialog = PreviewDialog(pixmap, self.main_window)
        dialog.exec()

    except Exception as e:
        logging.error(f"Błąd ładowania podglądu: {e}")
        QMessageBox.critical(
            self.main_window, "Błąd Podglądu", f"Nie udało się załadować podglądu: {e}"
        )
```

## 🎯 ETAP 1.4: ELIMINACJA FALLBACK CODE

### **1.4.1 UPROSZCZENIE METODY update_unpaired_files_lists**

**PLIK:** `src/ui/widgets/unpaired_files_tab.py`  
**LINIE:** 610-703  
**AKCJA:** ZASTĄP

```python
def update_unpaired_files_lists(self):
    """Aktualizuje listy niesparowanych plików w interfejsie użytkownika."""
    # Sprawdź czy widgety istnieją
    if not self.unpaired_archives_list or not self.unpaired_previews_grid:
        logging.error("Brak wymaganych widgetów do zarządzania plikami")
        return

    archives_count = len(self.main_window.controller.unpaired_archives)
    previews_count = len(self.main_window.controller.unpaired_previews)

    # Wyczyść widgety
    self.unpaired_archives_list.clear()
    self.unpaired_previews_grid.clear()

    # Wyczyść listy pomocnicze
    self.preview_checkboxes.clear()
    self.preview_tile_widgets.clear()

    # Sortuj alfabetycznie
    sorted_archives = sorted(
        self.main_window.controller.unpaired_archives,
        key=lambda x: os.path.basename(x).lower(),
    )
    sorted_previews = sorted(
        self.main_window.controller.unpaired_previews,
        key=lambda x: os.path.basename(x).lower(),
    )

    # Aktualizuj widgety
    self.unpaired_archives_list.update_archives(sorted_archives)
    self.unpaired_previews_grid.update_previews(sorted_previews)

    self._update_pair_button_state()
```

### **1.4.2 UPROSZCZENIE METODY clear_unpaired_files_lists**

**PLIK:** `src/ui/widgets/unpaired_files_tab.py`  
**LINIE:** 589-609  
**AKCJA:** ZASTĄP

```python
def clear_unpaired_files_lists(self):
    """Czyści listy niesparowanych plików w interfejsie użytkownika."""
    if self.unpaired_archives_list:
        self.unpaired_archives_list.clear()
    if self.unpaired_previews_grid:
        self.unpaired_previews_grid.clear()

    self.preview_checkboxes.clear()
    self.preview_tile_widgets.clear()
```

## 🎯 ETAP 1.5: KONSOLIDACJA OPERACJI

### **1.5.1 WSPÓLNA METODA DO RAPORTOWANIA**

**PLIK:** `src/ui/widgets/unpaired_files_tab.py`  
**LINIE:** Po metodzie `__init__`  
**AKCJA:** DODAJ METODĘ

```python
def _show_operation_report(self, operation_name: str, result: dict, success_message: str):
    """
    Wspólna metoda do wyświetlania raportów z operacji.

    Args:
        operation_name: Nazwa operacji
        result: Wynik operacji
        success_message: Komunikat sukcesu
    """
    total_requested = result.get("total_requested", 0)
    successfully_processed = result.get("successfully_processed", 0)
    errors = result.get("errors", 0)

    if errors == 0:
        QMessageBox.information(
            self.main_window, f"{operation_name} zakończone", success_message
        )
    else:
        report_lines = [
            f"{operation_name} zakończone z błędami:",
            f"• Pomyślnie przetworzono: {successfully_processed}",
            f"• Błędy: {errors}",
            f"• Łącznie: {total_requested}",
        ]

        detailed_errors = result.get("detailed_errors", [])
        if detailed_errors:
            report_lines.append("")
            report_lines.append("Szczegóły błędów:")
            for error in detailed_errors[:5]:
                file_name = os.path.basename(error.get("file_path", "Nieznany"))
                error_type = error.get("error_type", "NIEZNANY")
                report_lines.append(f"• {file_name}: {error_type}")

            if len(detailed_errors) > 5:
                report_lines.append(f"... i {len(detailed_errors) - 5} więcej błędów")

        QMessageBox.warning(
            self.main_window, f"{operation_name} zakończone z błędami", "\n".join(report_lines)
        )
```

### **1.5.2 UPROSZCZENIE METOD RAPORTOWANIA**

**PLIK:** `src/ui/widgets/unpaired_files_tab.py`  
**LINIE:** 839-883  
**AKCJA:** ZASTĄP

```python
def _show_move_unpaired_report(self, moved_files: list, detailed_errors: list, summary: dict):
    """Wyświetla raport z przenoszenia plików bez pary."""
    result = {
        "total_requested": summary.get("total_requested", 0),
        "successfully_processed": summary.get("successfully_moved", 0),
        "errors": summary.get("errors", 0),
        "detailed_errors": detailed_errors
    }

    self._show_operation_report(
        "Przenoszenie",
        result,
        f"Pomyślnie przeniesiono {result['successfully_processed']} z {result['total_requested']} plików archiwum bez pary do folderu '_bez_pary_'."
    )
```

## 🎯 ETAP 1.6: NOWA STRUKTURA PLIKÓW

### **1.6.1 NOWY PLIK: unpaired_files_tab_core.py**

**PLIK:** `src/ui/widgets/unpaired_files_tab_core.py`  
**AKCJA:** UTWÓRZ NOWY PLIK

```python
"""
Główna logika zakładki niesparowanych plików - wydzielona z unpaired_files_tab.py.
"""

import logging
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class UnpairedFilesTabCore:
    """Główna logika zakładki niesparowanych plików."""

    def __init__(self, main_window: "MainWindow"):
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def update_lists(self, archives_list, previews_grid):
        """Aktualizuje listy niesparowanych plików."""
        if not archives_list or not previews_grid:
            self.logger.error("Brak wymaganych widgetów")
            return

        archives = self.main_window.controller.unpaired_archives
        previews = self.main_window.controller.unpaired_previews

        # Sortuj alfabetycznie
        sorted_archives = sorted(archives, key=lambda x: os.path.basename(x).lower())
        sorted_previews = sorted(previews, key=lambda x: os.path.basename(x).lower())

        # Aktualizuj widgety
        archives_list.update_archives(sorted_archives)
        previews_grid.update_previews(sorted_previews)

    def clear_lists(self, archives_list, previews_grid):
        """Czyści listy niesparowanych plików."""
        if archives_list:
            archives_list.clear()
        if previews_grid:
            previews_grid.clear()

    def show_operation_report(self, operation_name: str, result: dict, success_message: str):
        """Wyświetla raport z operacji."""
        total = result.get("total_requested", 0)
        success = result.get("successfully_processed", 0)
        errors = result.get("errors", 0)

        if errors == 0:
            QMessageBox.information(self.main_window, f"{operation_name} zakończone", success_message)
        else:
            report = [
                f"{operation_name} zakończone z błędami:",
                f"• Pomyślnie: {success}",
                f"• Błędy: {errors}",
                f"• Łącznie: {total}",
            ]
            QMessageBox.warning(self.main_window, f"{operation_name} zakończone z błędami", "\n".join(report))
```

### **1.6.2 NOWY PLIK: unpaired_files_operations.py**

**PLIK:** `src/ui/widgets/unpaired_files_operations.py`  
**AKCJA:** UTWÓRZ NOWY PLIK

```python
"""
Operacje na niesparowanych plikach - wydzielone z unpaired_files_tab.py.
"""

import logging
import os
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QMessageBox

from src.ui.delegates.workers.file_list_workers import BulkDeleteFilesWorker

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class UnpairedFilesOperations:
    """Operacje na niesparowanych plikach."""

    def __init__(self, main_window: "MainWindow"):
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

    def handle_manual_pairing(self, archives_list_widget, previews_list_widget):
        """Obsługuje ręczne parowanie plików."""
        if hasattr(self.main_window, "file_operations_ui"):
            current_directory = self.main_window.controller.current_directory
            self.main_window.file_operations_ui.handle_manual_pairing(
                archives_list_widget,
                previews_list_widget,
                current_directory,
            )

    def handle_move_unpaired_archives(self, unpaired_archives: list):
        """Obsługuje przenoszenie niesparowanych archiwów."""
        current_directory = self.main_window.controller.current_directory
        if not current_directory:
            QMessageBox.warning(self.main_window, "Brak folderu roboczego", "Nie wybrano folderu roboczego.")
            return

        if not unpaired_archives:
            QMessageBox.information(self.main_window, "Brak plików", "Nie ma plików archiwum bez pary do przeniesienia.")
            return

        reply = QMessageBox.question(
            self.main_window,
            "Potwierdzenie przeniesienia",
            f"Czy na pewno chcesz przenieść {len(unpaired_archives)} plików archiwum bez pary do folderu '_bez_pary_'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        target_folder = os.path.join(current_directory, "_bez_pary_")
        try:
            os.makedirs(target_folder, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self.main_window, "Błąd tworzenia folderu", f"Nie udało się utworzyć folderu '_bez_pary_': {e}")
            return

        self._start_move_worker(unpaired_archives, target_folder)

    def handle_delete_unpaired_previews(self, unpaired_previews: list):
        """Obsługuje usuwanie niesparowanych podglądów."""
        if not unpaired_previews:
            QMessageBox.information(self.main_window, "Informacja", "Brak nieparowanych podglądów do usunięcia.")
            return

        reply = QMessageBox.question(
            self.main_window,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz trwale usunąć {len(unpaired_previews)} plików podglądu z dysku?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._start_delete_worker(unpaired_previews)

    def _start_move_worker(self, files_to_move: list, target_folder: str):
        """Uruchamia workera do przenoszenia plików."""
        self.main_window.worker_manager.run_worker(
            BulkMoveFilesWorker,
            files_to_move=files_to_move,
            destination_folder=target_folder,
            source_folder=self.main_window.controller.current_directory,
        )

    def _start_delete_worker(self, files_to_delete: list):
        """Uruchamia workera do usuwania plików."""
        self.main_window.worker_manager.run_worker(
            BulkDeleteFilesWorker,
            on_finished=self._on_delete_finished,
            on_error=self._on_delete_error,
            show_progress=True,
            files_to_delete=files_to_delete,
        )

    def _on_delete_finished(self, result: dict):
        """Obsługuje zakończenie usuwania."""
        deleted_files = result.get("deleted_files", [])
        errors = result.get("errors", [])
        self.main_window.progress_manager.hide_progress()

        QMessageBox.information(
            self.main_window,
            "Operacja zakończona",
            f"Usunięto {len(deleted_files)} z {len(deleted_files) + len(errors)} plików podglądu.\nLiczba błędów: {len(errors)}.",
        )

    def _on_delete_error(self, error_message: str):
        """Obsługuje błędy podczas usuwania."""
        self.main_window.progress_manager.hide_progress()
        QMessageBox.critical(self.main_window, "Błąd usuwania", f"Wystąpił błąd podczas usuwania plików: {error_message}")
```

### **1.6.3 NOWY PLIK: unpaired_files_tab.py (REFACTORED)**

**PLIK:** `src/ui/widgets/unpaired_files_tab.py`  
**AKCJA:** ZASTĄP CAŁY PLIK

```python
"""
Zakładka niesparowanych plików - zrefaktoryzowana wersja.
"""

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.unpaired_archives_list import UnpairedArchivesList
from src.ui.widgets.unpaired_previews_grid import UnpairedPreviewsGrid
from src.ui.widgets.unpaired_files_tab_core import UnpairedFilesTabCore
from src.ui.widgets.unpaired_files_operations import UnpairedFilesOperations

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class UnpairedFilesTab:
    """Zarządza zakładką niesparowanych plików - zrefaktoryzowana wersja."""

    def __init__(self, main_window: "MainWindow"):
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

        # Komponenty
        self.core = UnpairedFilesTabCore(main_window)
        self.operations = UnpairedFilesOperations(main_window)

        # Widgety
        self.unpaired_files_tab = None
        self.unpaired_files_layout = None
        self.unpaired_splitter = None
        self.unpaired_archives_list = None
        self.unpaired_previews_grid = None
        self.pair_manually_button = None
        self.delete_unpaired_previews_button = None
        self.move_unpaired_button = None

    def create_unpaired_files_tab(self) -> QWidget:
        """Tworzy zakładkę niesparowanych plików."""
        self.unpaired_files_tab = QWidget()
        self.unpaired_files_layout = QVBoxLayout(self.unpaired_files_tab)
        self.unpaired_files_layout.setContentsMargins(5, 5, 5, 5)

        # Splitter dla dwóch list
        self.unpaired_splitter = QSplitter()

        # Lista niesparowanych archiwów
        self._create_unpaired_archives_list()

        # Lista niesparowanych podglądów
        self._create_unpaired_previews_list()

        self.unpaired_files_layout.addWidget(self.unpaired_splitter)

        # Panel przycisków
        self._create_buttons_panel()

        return self.unpaired_files_tab

    def _create_unpaired_archives_list(self):
        """Tworzy listę niesparowanych archiwów."""
        self.unpaired_archives_list = UnpairedArchivesList(self.main_window)
        self.unpaired_archives_list.selection_changed.connect(self._update_pair_button_state)
        self.unpaired_splitter.addWidget(self.unpaired_archives_list)

    def _create_unpaired_previews_list(self):
        """Tworzy panel niesparowanych podglądów."""
        self.unpaired_previews_grid = UnpairedPreviewsGrid(self.main_window)
        self.unpaired_previews_grid.selection_changed.connect(self._update_pair_button_state)
        self.unpaired_splitter.addWidget(self.unpaired_previews_grid)

    def _create_buttons_panel(self):
        """Tworzy panel przycisków."""
        buttons_panel = QWidget()
        buttons_panel.setFixedHeight(35)
        buttons_layout = QHBoxLayout(buttons_panel)
        buttons_layout.setContentsMargins(5, 2, 5, 2)
        buttons_layout.setSpacing(10)

        # Przycisk do ręcznego parowania
        self.pair_manually_button = QPushButton("✅ Sparuj manualnie")
        self.pair_manually_button.setToolTip("Sparuj zaznaczone archiwum z zaznaczonym podglądem")
        self.pair_manually_button.setMinimumHeight(40)
        self.pair_manually_button.clicked.connect(self._handle_manual_pairing)
        self.pair_manually_button.setEnabled(False)
        buttons_layout.addWidget(self.pair_manually_button)

        # Przycisk do usuwania podglądów
        self.delete_unpaired_previews_button = QPushButton("🗑️ Usuń podglądy bez pary")
        self.delete_unpaired_previews_button.setToolTip("Usuwa z dysku wszystkie pliki podglądów z tej listy")
        self.delete_unpaired_previews_button.setMinimumHeight(40)
        self.delete_unpaired_previews_button.clicked.connect(self._handle_delete_unpaired_previews)
        buttons_layout.addWidget(self.delete_unpaired_previews_button)

        # Przycisk do przenoszenia archiwów
        self.move_unpaired_button = QPushButton("🚚 Przenieś archiwa")
        self.move_unpaired_button.setToolTip("Przenosi wszystkie pliki archiwum bez pary do folderu '_bez_pary_'")
        self.move_unpaired_button.setMinimumHeight(40)
        self.move_unpaired_button.clicked.connect(self._handle_move_unpaired_archives)
        buttons_layout.addWidget(self.move_unpaired_button)

        self.unpaired_files_layout.addWidget(buttons_panel)

    def _update_pair_button_state(self):
        """Aktualizuje stan przycisku do ręcznego parowania."""
        if not self.pair_manually_button:
            return

        selected_archives = self.unpaired_archives_list.list_widget.selectedItems()
        selected_previews = self.unpaired_previews_grid.hidden_list_widget.selectedItems()

        self.pair_manually_button.setEnabled(
            len(selected_archives) == 1 and len(selected_previews) == 1
        )

    def _handle_manual_pairing(self):
        """Obsługuje logikę ręcznego parowania plików."""
        self.operations.handle_manual_pairing(
            self.unpaired_archives_list.list_widget,
            self.unpaired_previews_grid.hidden_list_widget
        )

    def _handle_move_unpaired_archives(self):
        """Obsługuje przenoszenie niesparowanych archiwów."""
        unpaired_archives = self.main_window.controller.unpaired_archives
        self.operations.handle_move_unpaired_archives(unpaired_archives)

    def _handle_delete_unpaired_previews(self):
        """Obsługuje usuwanie niesparowanych podglądów."""
        unpaired_previews = self.unpaired_previews_grid.get_all_preview_paths()
        self.operations.handle_delete_unpaired_previews(unpaired_previews)

    def clear_unpaired_files_lists(self):
        """Czyści listy niesparowanych plików."""
        self.core.clear_lists(self.unpaired_archives_list, self.unpaired_previews_grid)

    def update_unpaired_files_lists(self):
        """Aktualizuje listy niesparowanych plików."""
        self.core.update_lists(self.unpaired_archives_list, self.unpaired_previews_grid)
        self._update_pair_button_state()

    def update_thumbnail_size(self, new_size):
        """Aktualizuje rozmiar miniaturek."""
        if self.unpaired_previews_grid:
            self.unpaired_previews_grid.update_thumbnail_size(new_size)

    def get_widgets_for_main_window(self):
        """Zwraca referencje do widgetów potrzebnych w main_window."""
        return {
            "unpaired_files_tab": self.unpaired_files_tab,
            "unpaired_archives_list_widget": self.unpaired_archives_list.list_widget,
            "unpaired_previews_list_widget": self.unpaired_previews_grid.hidden_list_widget,
            "unpaired_previews_layout": self.unpaired_previews_grid.grid_layout,
            "pair_manually_button": self.pair_manually_button,
        }
```

---

## ✅ CHECKLISTA IMPLEMENTACJI

### **ETAP 1.1: Podział na komponenty**

- [ ] Utworzenie `unpaired_files_tab_core.py`
- [ ] Utworzenie `unpaired_files_operations.py`
- [ ] Refaktoryzacja `unpaired_files_tab.py`

### **ETAP 1.2: Eliminacja duplikacji**

- [ ] Usunięcie klasy `UnpairedPreviewTile`
- [ ] Dodanie metody `create_simple_tile()` w `FileTileWidget`
- [ ] Uproszczenie logiki checkboxów

### **ETAP 1.3: Optymalizacja logowania**

- [ ] Zmiana INFO → DEBUG dla operacji rutynowych
- [ ] Usunięcie nadmiarowych logów
- [ ] Konsolidacja komunikatów błędów

### **ETAP 1.4: Uproszczenie architektury**

- [ ] Eliminacja fallback code
- [ ] Redukcja sprawdzeń hasattr()
- [ ] Uproszczenie metod pomocniczych

### **ETAP 1.5: Testy**

- [ ] Test funkcjonalności podstawowej
- [ ] Test integracji
- [ ] Test wydajności
- [ ] Test regresyjny

---

**STATUS:** 🔄 **GOTOWY DO IMPLEMENTACJI** - Wszystkie fragmenty kodu przygotowane.
