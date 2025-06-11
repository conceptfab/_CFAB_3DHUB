"""
Zakładka niesparowanych plików - wydzielona z main_window.py.
"""

import logging
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import (
    QGridLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class UnpairedFilesTab:
    """
    Zarządza zakładką niesparowanych plików z archiwami i podglądami.
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Inicjalizuje zakładkę niesparowanych plików.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window
        self.unpaired_files_tab = None
        self.unpaired_files_layout = None
        self.unpaired_splitter = None
        self.unpaired_archives_panel = None
        self.unpaired_archives_list_widget = None
        self.unpaired_previews_panel = None
        self.unpaired_previews_scroll_area = None
        self.unpaired_previews_container = None
        self.unpaired_previews_layout = None
        self.unpaired_previews_list_widget = None
        self.pair_manually_button = None

    def create_unpaired_files_tab(self) -> QWidget:
        """
        Tworzy zakładkę niesparowanych plików.

        Returns:
            Widget zakładki niesparowanych plików
        """
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

        # Przycisk do ręcznego parowania
        self.pair_manually_button = QPushButton("Sparuj Wybrane")
        self.pair_manually_button.clicked.connect(self._handle_manual_pairing)
        self.pair_manually_button.setEnabled(False)
        self.unpaired_files_layout.addWidget(self.pair_manually_button)

        return self.unpaired_files_tab

    def _create_unpaired_archives_list(self):
        """
        Tworzy listę niesparowanych archiwów z menu kontekstowym.
        """
        self.unpaired_archives_panel = QWidget()
        layout = QVBoxLayout(self.unpaired_archives_panel)

        label = QLabel("Niesparowane Archiwa:")
        layout.addWidget(label)

        self.unpaired_archives_list_widget = QListWidget()
        # Włącz menu kontekstowe
        self.unpaired_archives_list_widget.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.unpaired_archives_list_widget.customContextMenuRequested.connect(
            self._show_archive_context_menu
        )
        self.unpaired_archives_list_widget.itemSelectionChanged.connect(
            self._update_pair_button_state
        )
        layout.addWidget(self.unpaired_archives_list_widget)

        self.unpaired_splitter.addWidget(self.unpaired_archives_panel)

    def _show_archive_context_menu(self, position):
        """
        Wyświetla menu kontekstowe dla archiwów.
        """
        # Pobierz zaznaczony element
        item = self.unpaired_archives_list_widget.itemAt(position)
        if not item:
            return

        # Utwórz menu kontekstowe
        context_menu = QMenu()

        # Akcja do otwierania archiwum w zewnętrznym programie
        open_action = QAction("Otwórz w domyślnym programie", self.main_window)
        open_action.triggered.connect(lambda: self._open_archive_externally(item))
        context_menu.addAction(open_action)

        # Wyświetl menu
        context_menu.exec(self.unpaired_archives_list_widget.mapToGlobal(position))

    def _open_archive_externally(self, item):
        """
        Otwiera archiwum w domyślnym programie zewnętrznym.
        """
        archive_path = item.data(Qt.ItemDataRole.UserRole)
        if not os.path.exists(archive_path):
            QMessageBox.warning(
                self.main_window,
                "Plik nie istnieje",
                f"Plik {archive_path} nie istnieje.",
            )
            return

        # Otwórz archiwum w domyślnym programie
        try:
            os.startfile(archive_path)
        except Exception as e:
            QMessageBox.warning(
                self.main_window,
                "Błąd otwierania",
                f"Nie udało się otworzyć pliku {archive_path}.\n\n" f"Błąd: {str(e)}",
            )

    def _create_unpaired_previews_list(self):
        """
        Tworzy panel niesparowanych podglądów z miniaturkami.
        """
        self.unpaired_previews_panel = QWidget()
        layout = QVBoxLayout(self.unpaired_previews_panel)

        label = QLabel("Niesparowane Podglądy:")
        layout.addWidget(label)

        # Panel przewijania dla miniaturek
        self.unpaired_previews_scroll_area = QScrollArea()
        self.unpaired_previews_scroll_area.setWidgetResizable(True)
        self.unpaired_previews_scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.unpaired_previews_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        # Kontener na miniaturki
        self.unpaired_previews_container = QWidget()
        self.unpaired_previews_layout = QGridLayout(self.unpaired_previews_container)
        self.unpaired_previews_layout.setContentsMargins(5, 5, 5, 5)
        self.unpaired_previews_layout.setSpacing(10)

        self.unpaired_previews_scroll_area.setWidget(self.unpaired_previews_container)
        layout.addWidget(self.unpaired_previews_scroll_area)

        # Zachowaj QListWidget dla kompatybilności z istniejącym kodem
        # ale ukryj go - będzie używany tylko do przechowywania danych
        self.unpaired_previews_list_widget = QListWidget()
        self.unpaired_previews_list_widget.setVisible(False)
        self.unpaired_previews_list_widget.itemSelectionChanged.connect(
            self._update_pair_button_state
        )
        layout.addWidget(self.unpaired_previews_list_widget)

        self.unpaired_splitter.addWidget(self.unpaired_previews_panel)

    def _add_preview_thumbnail(self, preview_path):
        """
        Dodaje miniaturkę podglądu do kontenera podglądów.

        Args:
            preview_path: Ścieżka do pliku podglądu
        """
        # Upewnij się, że plik istnieje
        if not os.path.exists(preview_path):
            return

        # Utwórz kontener na miniaturkę i przyciski
        thumbnail_widget = QWidget()
        thumbnail_layout = QVBoxLayout(thumbnail_widget)
        thumbnail_layout.setContentsMargins(5, 5, 5, 5)
        thumbnail_layout.setSpacing(5)

        # Utwórz etykietę na miniaturkę
        thumbnail_label = QLabel()
        thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumbnail_label.setStyleSheet(
            "background-color: #f0f0f0; border: 1px solid #ddd;"
        )

        # Załaduj i ustaw miniaturkę
        pixmap = QPixmap(preview_path)
        if not pixmap.isNull():
            # Skaluj do rozsądnego rozmiaru
            pixmap = pixmap.scaled(
                150,
                150,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            thumbnail_label.setPixmap(pixmap)
        else:
            # Wyświetl tekst, jeśli nie można załadować obrazu
            thumbnail_label.setText("Nie można załadować podglądu")

        thumbnail_label.setFixedSize(150, 150)
        thumbnail_layout.addWidget(thumbnail_label)

        # Dodaj nazwę pliku
        file_name = os.path.basename(preview_path)
        name_label = QLabel(
            file_name if len(file_name) < 25 else file_name[:20] + "..."
        )
        name_label.setToolTip(file_name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumbnail_layout.addWidget(name_label)

        # Przycisk do usuwania podglądu
        delete_button = QPushButton("Usuń")
        delete_button.clicked.connect(lambda: self._delete_preview_file(preview_path))
        thumbnail_layout.addWidget(delete_button)

        # Przechowuj ścieżkę pliku w danych widgetu
        thumbnail_widget.setProperty("file_path", preview_path)

        # Dodaj do siatki
        row = self.unpaired_previews_layout.rowCount()
        col = self.unpaired_previews_layout.columnCount()
        if col == 0:
            col = 0
        else:
            # Umieść maksymalnie 3 miniaturki w rzędzie
            row, col = divmod(self.unpaired_previews_layout.count(), 3)

        self.unpaired_previews_layout.addWidget(thumbnail_widget, row, col)

        # Zaznacz ten podgląd do parowania, gdy zostanie kliknięty
        thumbnail_widget.mousePressEvent = (
            lambda event: self._select_preview_for_pairing(preview_path)
        )

    def _select_preview_for_pairing(self, preview_path):
        """
        Zaznacza podgląd do parowania.

        Args:
            preview_path: Ścieżka do pliku podglądu
        """
        # Znajdź i zaznacz odpowiedni element w ukrytym QListWidget
        for i in range(self.unpaired_previews_list_widget.count()):
            item = self.unpaired_previews_list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == preview_path:
                self.unpaired_previews_list_widget.setCurrentItem(item)
                break

    def _delete_preview_file(self, preview_path):
        """
        Usuwa plik podglądu z systemu plików i odświeża widok.

        Args:
            preview_path: Ścieżka do pliku podglądu
        """
        if not os.path.exists(preview_path):
            QMessageBox.warning(
                self.main_window,
                "Plik nie istnieje",
                f"Plik {preview_path} nie istnieje.",
            )
            return

        # Potwierdź usunięcie
        reply = QMessageBox.question(
            self.main_window,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć plik " f"{os.path.basename(preview_path)}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(preview_path)
                # Odśwież widok
                self._refresh_unpaired_files()
                QMessageBox.information(
                    self.main_window,
                    "Sukces",
                    f"Plik {os.path.basename(preview_path)} został " f"usunięty.",
                )
            except Exception as e:
                QMessageBox.warning(
                    self.main_window,
                    "Błąd usuwania",
                    f"Nie udało się usunąć pliku.\n\nBłąd: {str(e)}",
                )

    def clear_unpaired_files_lists(self):
        """
        Czyści listy niesparowanych plików w interfejsie użytkownika.
        """
        if self.unpaired_archives_list_widget:
            self.unpaired_archives_list_widget.clear()
        if self.unpaired_previews_list_widget:
            self.unpaired_previews_list_widget.clear()
        logging.debug("Wyczyszczono listy niesparowanych plików w UI.")

    def update_unpaired_files_lists(self):
        """
        Aktualizuje listy niesparowanych plików w interfejsie użytkownika.
        """
        if not self.unpaired_archives_list_widget:
            return

        self.unpaired_archives_list_widget.clear()
        self.unpaired_previews_list_widget.clear()

        # Wyczyść kontener miniaturek
        while self.unpaired_previews_layout.count():
            widget_to_remove = self.unpaired_previews_layout.itemAt(0).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)
                self.unpaired_previews_layout.removeWidget(widget_to_remove)

        # Aktualizuj listę archiwów - stan z Controller
        for archive_path in self.main_window.controller.unpaired_archives:
            item = QListWidgetItem(os.path.basename(archive_path))
            item.setData(Qt.ItemDataRole.UserRole, archive_path)
            self.unpaired_archives_list_widget.addItem(item)

        # Aktualizuj miniaturki podglądów - stan z Controller
        for preview_path in self.main_window.controller.unpaired_previews:
            # Dodaj do ukrytego QListWidget dla kompatybilności
            item = QListWidgetItem(os.path.basename(preview_path))
            item.setData(Qt.ItemDataRole.UserRole, preview_path)
            self.unpaired_previews_list_widget.addItem(item)

            # Dodaj miniaturkę
            self._add_preview_thumbnail(preview_path)

        logging.debug(
            f"Zaktualizowano listy niesparowanych: "
            f"{len(self.main_window.controller.unpaired_archives)} archiwów, "
            f"{len(self.main_window.controller.unpaired_previews)} podglądów."
        )
        self._update_pair_button_state()

    def _update_pair_button_state(self):
        """
        Aktualizuje stan przycisku do ręcznego parowania.
        """
        if not self.pair_manually_button:
            return

        selected_archives = self.unpaired_archives_list_widget.selectedItems()
        selected_previews = self.unpaired_previews_list_widget.selectedItems()
        self.pair_manually_button.setEnabled(
            len(selected_archives) == 1 and len(selected_previews) == 1
        )

    def update_pair_button_state(self):
        """
        Publiczna metoda do aktualizacji stanu przycisku parowania.
        """
        self._update_pair_button_state()

    def _handle_manual_pairing(self):
        """
        Obsługuje logikę ręcznego parowania plików.
        """
        # Deleguj obsługę do FileOperationsUI
        if hasattr(self.main_window, "file_operations_ui"):
            self.main_window.file_operations_ui.handle_manual_pairing(
                self.unpaired_archives_list_widget, self.unpaired_previews_list_widget
            )

    def _refresh_unpaired_files(self):
        """
        Odświeża widok niesparowanych plików po operacjach takich jak usuwanie.
        """
        # Ponowne skanowanie folderu
        current_folder = self.main_window.controller.current_directory
        if current_folder and os.path.isdir(current_folder):
            # Deleguj do głównego okna
            if hasattr(self.main_window, "force_full_refresh"):
                self.main_window.force_full_refresh()
        else:
            logging.error(
                "Nie można odświeżyć widoku - brak poprawnego folderu roboczego"
            )

    def get_widgets_for_main_window(self):
        """
        Zwraca referencje do widgetów potrzebnych w main_window.

        Returns:
            Dict z referencjami do widgetów
        """
        return {
            "unpaired_files_tab": self.unpaired_files_tab,
            "unpaired_archives_list_widget": self.unpaired_archives_list_widget,
            "unpaired_previews_list_widget": self.unpaired_previews_list_widget,
            "unpaired_previews_layout": self.unpaired_previews_layout,
            "pair_manually_button": self.pair_manually_button,
        }
