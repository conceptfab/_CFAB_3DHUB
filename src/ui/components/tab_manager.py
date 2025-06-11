"""
Tab Manager - zarządzanie zakładkami i ich zawartością.
Refaktoryzacja MainWindow ETAP 2 - wydzielenie logiki zakładek.
"""

import logging
import os
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class TabManager:
    """
    Manager odpowiedzialny za tworzenie i zarządzanie zakładkami.
    Wydzielony z MainWindow dla lepszej organizacji kodu.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje Tab Manager.
        
        Args:
            main_window: Główne okno aplikacji (MainWindow)
        """
        self.main_window = main_window
        self.app_config = main_window.app_config
        
    def create_gallery_tab(self) -> QWidget:
        """
        Tworzy zakładkę galerii z drzewem folderów i kafelkami.
        
        Returns:
            QWidget: Zakładka galerii
        """
        gallery_tab = QWidget()
        layout = QVBoxLayout(gallery_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter dla drzewa i kafelków
        splitter = QSplitter()
        
        # Drzewo folderów
        folder_tree = self._create_folder_tree()
        splitter.addWidget(folder_tree)
        
        # Obszar kafelków
        tiles_area = self._create_tiles_area()
        splitter.addWidget(tiles_area)
        
        # Ustaw proporcje splitter
        splitter.setSizes([350, 650])
        splitter.setCollapsible(0, False)  # Nie pozwól na zwijanie drzewa
        splitter.setCollapsible(1, False)  # Nie pozwól na zwijanie galerii
        
        layout.addWidget(splitter)
        
        # Zapisz referencje w main_window
        self.main_window.gallery_tab = gallery_tab
        self.main_window.splitter = splitter
        
        return gallery_tab
        
    def _create_folder_tree(self) -> QWidget:
        """
        Tworzy drzewo folderów z kontrolkami expand/collapse.
        
        Returns:
            QWidget: Kontener z drzewem folderów
        """
        folder_tree_container = QWidget()
        layout = QVBoxLayout(folder_tree_container)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Etykieta
        tree_label = QLabel("Drzewo folderów:")
        layout.addWidget(tree_label)
        
        # Drzewo folderów
        folder_tree = QTreeView()
        folder_tree.setHeaderHidden(True)
        layout.addWidget(folder_tree)
        
        # Zapisz referencje w main_window
        self.main_window.folder_tree_container = folder_tree_container
        self.main_window.folder_tree = folder_tree
        
        return folder_tree_container
        
    def _create_tiles_area(self) -> QScrollArea:
        """
        Tworzy obszar przewijania dla kafelków galerii.
        
        Returns:
            QScrollArea: Obszar przewijania z kafelkami
        """
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        # Kontener na kafelki
        tiles_container = QWidget()
        tiles_layout = QGridLayout(tiles_container)
        tiles_layout.setContentsMargins(10, 10, 10, 10)
        tiles_layout.setSpacing(15)
        
        scroll_area.setWidget(tiles_container)
        
        # Zapisz referencje w main_window
        self.main_window.scroll_area = scroll_area
        self.main_window.tiles_container = tiles_container
        self.main_window.tiles_layout = tiles_layout
        
        return scroll_area
        
    def create_unpaired_files_tab(self) -> QWidget:
        """
        Tworzy zakładkę niesparowanych plików.
        
        Returns:
            QWidget: Zakładka niesparowanych plików
        """
        unpaired_tab = QWidget()
        layout = QVBoxLayout(unpaired_tab)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Splitter dla dwóch list
        splitter = QSplitter()
        
        # Lista niesparowanych archiwów
        archives_panel = self._create_unpaired_archives_list()
        splitter.addWidget(archives_panel)
        
        # Lista niesparowanych podglądów
        previews_panel = self._create_unpaired_previews_list()
        splitter.addWidget(previews_panel)
        
        layout.addWidget(splitter)
        
        # Przycisk do ręcznego parowania
        pair_button = QPushButton("Sparuj Wybrane")
        pair_button.clicked.connect(self.main_window._handle_manual_pairing)
        pair_button.setEnabled(False)
        layout.addWidget(pair_button)
        
        # Zapisz referencje w main_window
        self.main_window.unpaired_files_tab = unpaired_tab
        self.main_window.unpaired_splitter = splitter
        self.main_window.pair_manually_button = pair_button
        
        return unpaired_tab
        
    def _create_unpaired_archives_list(self) -> QWidget:
        """
        Tworzy panel niesparowanych archiwów z menu kontekstowym.
        
        Returns:
            QWidget: Panel archiwów
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Etykieta
        label = QLabel("Niesparowane Archiwa:")
        layout.addWidget(label)
        
        # Lista
        list_widget = QListWidget()
        list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        list_widget.customContextMenuRequested.connect(self._show_archive_context_menu)
        list_widget.itemSelectionChanged.connect(self.main_window._update_pair_button_state)
        layout.addWidget(list_widget)
        
        # Zapisz referencje w main_window
        self.main_window.unpaired_archives_panel = panel
        self.main_window.unpaired_archives_list_widget = list_widget
        
        return panel
        
    def _create_unpaired_previews_list(self) -> QWidget:
        """
        Tworzy panel niesparowanych podglądów z miniaturkami.
        
        Returns:
            QWidget: Panel podglądów
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Etykieta
        label = QLabel("Niesparowane Podglądy:")
        layout.addWidget(label)
        
        # Scroll area dla miniaturek
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Kontener na miniaturki
        container = QWidget()
        grid_layout = QGridLayout(container)
        grid_layout.setContentsMargins(5, 5, 5, 5)
        grid_layout.setSpacing(10)
        
        scroll_area.setWidget(container)
        layout.addWidget(scroll_area)
        
        # Ukryty QListWidget dla kompatybilności
        hidden_list = QListWidget()
        hidden_list.setVisible(False)
        hidden_list.itemSelectionChanged.connect(self.main_window._update_pair_button_state)
        layout.addWidget(hidden_list)
        
        # Zapisz referencje w main_window
        self.main_window.unpaired_previews_panel = panel
        self.main_window.unpaired_previews_scroll_area = scroll_area
        self.main_window.unpaired_previews_container = container
        self.main_window.unpaired_previews_layout = grid_layout
        self.main_window.unpaired_previews_list_widget = hidden_list
        
        return panel
        
    def _show_archive_context_menu(self, position):
        """
        Wyświetla menu kontekstowe dla archiwów.
        
        Args:
            position: Pozycja kliknięcia
        """
        if not hasattr(self.main_window, 'unpaired_archives_list_widget'):
            return
            
        item = self.main_window.unpaired_archives_list_widget.itemAt(position)
        if not item:
            return
            
        menu = QMenu(self.main_window)
        
        # Akcja otwarcia zewnętrznego
        open_action = menu.addAction("Otwórz plik")
        open_action.triggered.connect(lambda: self._open_archive_externally(item))
        
        # Wyświetl menu
        global_pos = self.main_window.unpaired_archives_list_widget.mapToGlobal(position)
        menu.exec(global_pos)
        
    def _open_archive_externally(self, item):
        """
        Otwiera archiwum w domyślnym programie zewnętrznym.
        
        Args:
            item: Element listy
        """
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and os.path.exists(file_path):
            try:
                os.startfile(file_path)  # Windows
            except AttributeError:
                import subprocess
                subprocess.call(['open', file_path])  # macOS
            except Exception as e:
                logging.error(f"Nie można otworzyć pliku {file_path}: {e}")
                
    def add_preview_thumbnail(self, preview_path: str):
        """
        Dodaje miniaturkę podglądu do siatki.
        
        Args:
            preview_path: Ścieżka do pliku podglądu
        """
        if not hasattr(self.main_window, 'unpaired_previews_layout'):
            return
            
        # Kontener na miniaturkę
        thumbnail_widget = QWidget()
        thumbnail_widget.setFixedSize(120, 140)
        thumbnail_layout = QVBoxLayout(thumbnail_widget)
        thumbnail_layout.setContentsMargins(2, 2, 2, 2)
        
        # Miniaturka obrazka
        thumbnail_label = QLabel()
        thumbnail_label.setFixedSize(100, 100)
        thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumbnail_label.setStyleSheet("border: 1px solid gray;")
        
        # Załaduj miniaturkę
        if os.path.exists(preview_path):
            pixmap = QPixmap(preview_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
                thumbnail_label.setPixmap(scaled_pixmap)
            else:
                thumbnail_label.setText("Brak\npodglądu")
        else:
            thumbnail_label.setText("Plik\nnie istnieje")
            
        thumbnail_layout.addWidget(thumbnail_label)
        
        # Nazwa pliku
        file_name = os.path.basename(preview_path)
        name_label = QLabel(file_name if len(file_name) < 25 else file_name[:20] + "...")
        name_label.setToolTip(file_name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumbnail_layout.addWidget(name_label)
        
        # Przycisk usuwania
        delete_button = QPushButton("Usuń")
        delete_button.clicked.connect(lambda: self._delete_preview_file(preview_path))
        thumbnail_layout.addWidget(delete_button)
        
        # Przechowaj ścieżkę pliku
        thumbnail_widget.setProperty("file_path", preview_path)
        
        # Dodaj do siatki (max 3 kolumny)
        row = self.main_window.unpaired_previews_layout.rowCount()
        col = 0
        if self.main_window.unpaired_previews_layout.count() > 0:
            row, col = divmod(self.main_window.unpaired_previews_layout.count(), 3)
            
        self.main_window.unpaired_previews_layout.addWidget(thumbnail_widget, row, col)
        
        # Kliknięcie wybiera podgląd do parowania
        thumbnail_widget.mousePressEvent = lambda event: self._select_preview_for_pairing(preview_path)
        
    def _select_preview_for_pairing(self, preview_path: str):
        """
        Zaznacza podgląd do parowania.
        
        Args:
            preview_path: Ścieżka do podglądu
        """
        if hasattr(self.main_window, 'unpaired_previews_list_widget'):
            # Znajdź odpowiedni element w ukrytej liście
            for i in range(self.main_window.unpaired_previews_list_widget.count()):
                item = self.main_window.unpaired_previews_list_widget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == preview_path:
                    item.setSelected(True)
                    break
                    
    def _delete_preview_file(self, preview_path: str):
        """
        Usuwa plik podglądu po potwierdzeniu.
        
        Args:
            preview_path: Ścieżka do pliku
        """
        from PyQt6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self.main_window,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć plik?\n\n{os.path.basename(preview_path)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                os.remove(preview_path)
                # Odśwież widok
                self.main_window._refresh_unpaired_files()
                QMessageBox.information(
                    self.main_window,
                    "Sukces",
                    f"Plik {os.path.basename(preview_path)} został usunięty.",
                )
            except Exception as e:
                QMessageBox.warning(
                    self.main_window,
                    "Błąd usuwania",
                    f"Nie udało się usunąć pliku.\n\nBłąd: {str(e)}",
                )
                
    def update_unpaired_files_lists(self):
        """
        Aktualizuje listy niesparowanych plików w interfejsie użytkownika.
        """
        if not hasattr(self.main_window, 'unpaired_archives_list_widget'):
            return
            
        # Wyczyść listy
        self.main_window.unpaired_archives_list_widget.clear()
        self.main_window.unpaired_previews_list_widget.clear()
        
        # Wyczyść kontener miniaturek
        while self.main_window.unpaired_previews_layout.count():
            widget_to_remove = self.main_window.unpaired_previews_layout.itemAt(0).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)
                self.main_window.unpaired_previews_layout.removeWidget(widget_to_remove)
                
        # Aktualizuj listę archiwów
        for archive_path in self.main_window.unpaired_archives:
            item = QListWidgetItem(os.path.basename(archive_path))
            item.setData(Qt.ItemDataRole.UserRole, archive_path)
            self.main_window.unpaired_archives_list_widget.addItem(item)
            
        # Aktualizuj miniaturki podglądów
        for preview_path in self.main_window.unpaired_previews:
            # Dodaj do ukrytego QListWidget dla kompatybilności
            item = QListWidgetItem(os.path.basename(preview_path))
            item.setData(Qt.ItemDataRole.UserRole, preview_path)
            self.main_window.unpaired_previews_list_widget.addItem(item)
            
            # Dodaj miniaturkę
            self.add_preview_thumbnail(preview_path)
            
        # Aktualizuj stan przycisku parowania
        self.main_window._update_pair_button_state()
        
        logging.debug(
            f"Zaktualizowano listy niesparowanych: "
            f"{len(self.main_window.unpaired_archives)} archiwów, "
            f"{len(self.main_window.unpaired_previews)} podglądów."
        )
