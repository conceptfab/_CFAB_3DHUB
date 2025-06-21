"""
Widget do zarządzania listą niesparowanych archiwów.
Wydzielone z unpaired_files_tab.py w ramach refaktoryzacji.
"""

import logging
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class UnpairedArchivesList(QWidget):
    """
    Widget odpowiedzialny za wyświetlanie i zarządzanie listą niesparowanych archiwów.

    Funkcjonalności:
    - Wyświetlanie listy niesparowanych archiwów
    - Menu kontekstowe z opcją otwierania w zewnętrznym programie
    - Sygnały o zmianie selekcji
    """

    # Sygnały
    selection_changed = pyqtSignal()  # Emitowany gdy zmieni się selekcja

    def __init__(self, main_window: "MainWindow", parent: QWidget = None):
        """
        Inicjalizuje widget listy niesparowanych archiwów.

        Args:
            main_window: Referencja do głównego okna aplikacji
            parent: Widget nadrzędny
        """
        super().__init__(parent)
        self.main_window = main_window
        self.list_widget = None
        self._init_ui()

    def _init_ui(self):
        """Inicjalizuje interfejs użytkownika."""
        layout = QVBoxLayout(self)

        # Etykieta
        label = QLabel("Niesparowane Archiwa:")
        layout.addWidget(label)

        # Lista archiwów
        self.list_widget = QListWidget()
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.list_widget)

    def _show_context_menu(self, position):
        """
        Wyświetla menu kontekstowe dla archiwów.

        Args:
            position: Pozycja kliknięcia
        """
        item = self.list_widget.itemAt(position)
        if not item:
            return

        context_menu = QMenu()

        # Akcja do otwierania archiwum w zewnętrznym programie
        open_action = QAction("Otwórz w domyślnym programie", self.main_window)
        open_action.triggered.connect(lambda: self._open_archive_externally(item))
        context_menu.addAction(open_action)

        # Wyświetl menu
        context_menu.exec(self.list_widget.mapToGlobal(position))

    def _open_archive_externally(self, item: QListWidgetItem):
        """
        Otwiera archiwum w domyślnym programie zewnętrznym.

        Args:
            item: Element listy zawierający ścieżkę do archiwum
        """
        archive_path = item.data(Qt.ItemDataRole.UserRole)
        if not os.path.exists(archive_path):
            QMessageBox.warning(
                self.main_window,
                "Plik nie istnieje",
                f"Plik {archive_path} nie istnieje.",
            )
            return

        try:
            os.startfile(archive_path)
        except Exception as e:
            QMessageBox.warning(
                self.main_window,
                "Błąd otwierania",
                f"Nie udało się otworzyć pliku {archive_path}.\n\nBłąd: {str(e)}",
            )

    def _on_selection_changed(self):
        """Obsługuje zmianę selekcji w liście."""
        self.selection_changed.emit()

    def clear(self):
        """Czyści listę archiwów."""
        if self.list_widget is not None:
            self.list_widget.clear()

    def add_archive(self, archive_path: str):
        """
        Dodaje archiwum do listy.

        Args:
            archive_path: Ścieżka do pliku archiwum
        """
        if self.list_widget is None:
            logging.warning(f"Widget archiwów nie jest zainicjalizowany")
            return
        item = QListWidgetItem(os.path.basename(archive_path))
        item.setData(Qt.ItemDataRole.UserRole, archive_path)
        self.list_widget.addItem(item)

    def update_archives(self, archive_paths: list[str]):
        """
        Aktualizuje całą listę archiwów.

        Args:
            archive_paths: Lista ścieżek do archiwów
        """
        self.clear()

        # Sortuj alfabetycznie
        sorted_archives = sorted(
            archive_paths, key=lambda x: os.path.basename(x).lower()
        )

        for archive_path in sorted_archives:
            self.add_archive(archive_path)

    def get_selected_items(self) -> list[QListWidgetItem]:
        """
        Zwraca listę zaznaczonych elementów.

        Returns:
            Lista zaznaczonych elementów
        """
        if not self.list_widget:
            return []
        return self.list_widget.selectedItems()

    def get_selected_archive_path(self) -> str | None:
        """
        Zwraca ścieżkę do zaznaczonego archiwum.

        Returns:
            Ścieżka do archiwum lub None jeśli nic nie zaznaczono
        """
        selected_items = self.get_selected_items()
        if not selected_items:
            return None
        return selected_items[0].data(Qt.ItemDataRole.UserRole)
