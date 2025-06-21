"""
Widget do zarządzania siatką podglądów niesparowanych plików.
Wydzielone z unpaired_files_tab.py w ramach refaktoryzacji.
"""

import logging
import os
from typing import TYPE_CHECKING, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QGridLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.tile_styles import TileSizeConstants

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow
    from src.ui.widgets.unpaired_files_tab import UnpairedPreviewTile


class UnpairedPreviewsGrid(QWidget):
    """
    Widget odpowiedzialny za wyświetlanie i zarządzanie siatką podglądów niesparowanych plików.
    
    Funkcjonalności:
    - Wyświetlanie miniaturek w siatce
    - Zarządzanie checkboxami dla selekcji
    - Skalowanie miniaturek
    - Sygnały o zmianie selekcji
    """
    
    # Sygnały
    selection_changed = pyqtSignal()  # Emitowany gdy zmieni się selekcja
    preview_deleted = pyqtSignal(str)  # Emitowany gdy podgląd zostanie usunięty
    
    def __init__(self, main_window: "MainWindow", parent: QWidget = None):
        """
        Inicjalizuje widget siatki podglądów.
        
        Args:
            main_window: Referencja do głównego okna aplikacji
            parent: Widget nadrzędny
        """
        super().__init__(parent)
        self.main_window = main_window
        
        # Komponenty UI
        self.scroll_area = None
        self.container = None
        self.grid_layout = None
        self.hidden_list_widget = None  # Dla kompatybilności z istniejącym kodem
        
        # Stan
        self.preview_tile_widgets: List["UnpairedPreviewTile"] = []
        self.preview_checkboxes = []
        self.current_thumbnail_size = TileSizeConstants.DEFAULT_THUMBNAIL_SIZE
        
        self._init_ui()
        
    def _init_ui(self):
        """Inicjalizuje interfejs użytkownika."""
        layout = QVBoxLayout(self)
        
        # Etykieta
        label = QLabel("Niesparowane Podglądy:")
        layout.addWidget(label)
        
        # Panel przewijania dla miniaturek
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Kontener na miniaturki
        self.container = QWidget()
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setContentsMargins(5, 5, 5, 5)
        self.grid_layout.setSpacing(10)
        
        self.scroll_area.setWidget(self.container)
        layout.addWidget(self.scroll_area)
        
        # Ukryty QListWidget dla kompatybilności z istniejącym kodem
        self.hidden_list_widget = QListWidget()
        self.hidden_list_widget.setVisible(False)
        self.hidden_list_widget.itemSelectionChanged.connect(self._on_hidden_list_selection_changed)
        layout.addWidget(self.hidden_list_widget)
        
    def _on_hidden_list_selection_changed(self):
        """Obsługuje zmianę selekcji w ukrytej liście."""
        self.selection_changed.emit()
        
    def add_preview_tile(self, preview_path: str) -> "UnpairedPreviewTile":
        """
        Dodaje kafelek podglądu do siatki.
        
        Args:
            preview_path: Ścieżka do pliku podglądu
            
        Returns:
            Utworzony kafelek podglądu
        """
        # Import w metodzie, aby uniknąć cyklicznych importów
        from src.ui.widgets.unpaired_files_tab import UnpairedPreviewTile
        
        if not os.path.exists(preview_path):
            logging.warning(f"Plik podglądu nie istnieje: {preview_path}")
            return None
            
        # Utwórz kafelek podglądu
        preview_tile = UnpairedPreviewTile(preview_path, self.container)
        preview_tile.set_thumbnail_size(self.current_thumbnail_size)
        
        # Podłącz sygnały
        preview_tile.preview_image_requested.connect(self._on_preview_image_requested)
        preview_tile.checkbox.stateChanged.connect(
            lambda state, cb=preview_tile.checkbox, path=preview_path: 
            self._on_preview_checkbox_changed(cb, path, state)
        )
        preview_tile.delete_button.clicked.connect(
            lambda: self._on_delete_preview_requested(preview_path)
        )
        
        # Ustaw ikonę dla przycisku usuń
        from PyQt6.QtWidgets import QStyle
        trash_icon = self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        preview_tile.delete_button.setIcon(trash_icon)
        
        # Dodaj do list zarządzających
        self.preview_checkboxes.append(preview_tile.checkbox)
        self.preview_tile_widgets.append(preview_tile)
        
        # Dodaj do siatki - maksymalnie 3 miniaturki w rzędzie
        row, col = divmod(self.grid_layout.count(), 3)
        self.grid_layout.addWidget(preview_tile, row, col)
        
        # Dodaj do ukrytego QListWidget dla kompatybilności
        item = QListWidgetItem(os.path.basename(preview_path))
        item.setData(Qt.ItemDataRole.UserRole, preview_path)
        self.hidden_list_widget.addItem(item)
        
        return preview_tile
        
    def _on_preview_image_requested(self, preview_path: str):
        """
        Obsługuje żądanie wyświetlenia podglądu obrazu.
        
        Args:
            preview_path: Ścieżka do pliku podglądu
        """
        # Pokaż podgląd obrazu
        from PyQt6.QtGui import QPixmap
        from PyQt6.QtWidgets import QMessageBox
        from src.ui.widgets.preview_dialog import PreviewDialog
        
        if not preview_path or not os.path.exists(preview_path):
            QMessageBox.warning(
                self.main_window,
                "Brak Podglądu",
                "Plik podglądu nie istnieje.",
            )
            return
            
        try:
            pixmap = QPixmap(preview_path)
            if pixmap.isNull():
                raise ValueError("Nie udało się załadować obrazu do QPixmap.")
                
            # Używaj PreviewDialog jak w galerii
            dialog = PreviewDialog(pixmap, self.main_window)
            dialog.exec()
            
        except Exception as e:
            error_message = f"Wystąpił błąd podczas ładowania podglądu: {e}"
            logging.error(error_message)
            QMessageBox.critical(self.main_window, "Błąd Podglądu", error_message)
            
    def _on_preview_checkbox_changed(self, checkbox, preview_path: str, state: int):
        """
        Obsługuje zmianę stanu checkboxa, zapewniając wybór tylko jednego elementu.
        
        Args:
            checkbox: Checkbox, który się zmienił
            preview_path: Ścieżka do pliku podglądu
            state: Nowy stan checkboxa
        """
        # Zablokuj sygnały, aby uniknąć rekurencji
        checkbox.blockSignals(True)
        
        if state == Qt.CheckState.Checked.value:
            # Odznacz wszystkie inne checkboxy
            for cb in self.preview_checkboxes:
                if cb is not checkbox and cb.isChecked():
                    cb.blockSignals(True)
                    cb.setChecked(False)
                    cb.blockSignals(False)
                    
            # Zaznacz odpowiedni element na ukrytej liście
            for i in range(self.hidden_list_widget.count()):
                item = self.hidden_list_widget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == preview_path:
                    self.hidden_list_widget.setCurrentItem(item)
                    break
        else:
            # Odznacz element na liście, jeśli to on był zaznaczony
            current_item = self.hidden_list_widget.currentItem()
            if (current_item and 
                current_item.data(Qt.ItemDataRole.UserRole) == preview_path):
                self.hidden_list_widget.setCurrentItem(None)
                
        # Odblokuj sygnały
        checkbox.blockSignals(False)
        
    def _on_delete_preview_requested(self, preview_path: str):
        """
        Obsługuje żądanie usunięcia podglądu.
        
        Args:
            preview_path: Ścieżka do pliku podglądu
        """
        self.preview_deleted.emit(preview_path)
        
    def clear(self):
        """Czyści wszystkie podglądy z siatki."""
        # Wyczyść listę checkboxów i kafelków
        self.preview_checkboxes.clear()
        self.preview_tile_widgets.clear()
        
        # Wyczyść ukrytą listę
        if self.hidden_list_widget:
            self.hidden_list_widget.clear()
            
        # Wyczyść kontener siatki
        while self.grid_layout.count():
            item_to_remove = self.grid_layout.takeAt(0)
            if item_to_remove:
                widget_to_remove = item_to_remove.widget()
                if widget_to_remove:
                    widget_to_remove.setParent(None)
                    widget_to_remove.deleteLater()
                else:
                    # Jeśli to layout, wyczyść go rekurencyjnie
                    layout_to_remove = item_to_remove.layout()
                    if layout_to_remove:
                        while layout_to_remove.count():
                            child = layout_to_remove.takeAt(0)
                            if child.widget():
                                child.widget().setParent(None)
                                child.widget().deleteLater()
                                
    def update_previews(self, preview_paths: List[str]):
        """
        Aktualizuje całą siatkę podglądów.
        
        Args:
            preview_paths: Lista ścieżek do plików podglądów
        """
        self.clear()
        
        # Sortuj alfabetycznie
        sorted_previews = sorted(preview_paths, key=lambda x: os.path.basename(x).lower())
        
        for preview_path in sorted_previews:
            self.add_preview_tile(preview_path)
            
    def update_thumbnail_size(self, new_size):
        """
        Aktualizuje rozmiar miniaturek w siatce.
        
        Args:
            new_size: Nowy rozmiar kafelka (int lub tuple (width, height))
        """
        self.current_thumbnail_size = new_size
        
        # Aktualizuj wszystkie istniejące kafelki
        for preview_tile in self.preview_tile_widgets:
            preview_tile.set_thumbnail_size(new_size)
            
    def get_selected_items(self) -> List[QListWidgetItem]:
        """
        Zwraca listę zaznaczonych elementów z ukrytej listy.
        
        Returns:
            Lista zaznaczonych elementów
        """
        if not self.hidden_list_widget:
            return []
        return self.hidden_list_widget.selectedItems()
        
    def get_selected_preview_path(self) -> str | None:
        """
        Zwraca ścieżkę do zaznaczonego podglądu.
        
        Returns:
            Ścieżka do podglądu lub None jeśli nic nie zaznaczono
        """
        selected_items = self.get_selected_items()
        if not selected_items:
            return None
        return selected_items[0].data(Qt.ItemDataRole.UserRole)
        
    def get_all_preview_paths(self) -> List[str]:
        """
        Zwraca wszystkie ścieżki podglądów w siatce.
        
        Returns:
            Lista ścieżek do wszystkich podglądów
        """
        paths = []
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'preview_path'):
                    paths.append(widget.preview_path)
        return paths