"""
Zakładka niesparowanych plików - wydzielona z main_window.py.
"""

import logging
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QSize, pyqtSignal, QEvent
from PyQt6.QtGui import QAction, QIcon, QPixmap
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
    QStyle,
    QFrame,
    QCheckBox,
    QHBoxLayout,
)

# Dodaj import stylów z FileTileWidget
from src.ui.widgets.tile_styles import TileStylesheet, TileColorScheme, TileSizeConstants
# Dodaj import PreviewDialog
from src.ui.widgets.preview_dialog import PreviewDialog

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class UnpairedPreviewTile(QWidget):
    """
    Uproszczony kafelek podglądu bez gwiazdek i tagów kolorów.
    Używa tej samej struktury co FileTileWidget ale bez MetadataControlsWidget.
    """
    
    # Dodaj sygnał jak w FileTileWidget
    preview_image_requested = pyqtSignal(str)  # ścieżka do pliku podglądu
    
    def __init__(self, preview_path: str, parent: QWidget = None):
        super().__init__(parent)
        self.preview_path = preview_path
        self.thumbnail_size = TileSizeConstants.DEFAULT_THUMBNAIL_SIZE
        
        # Referencje do widgetów
        self.thumbnail_frame = None
        self.thumbnail_label = None
        self.filename_label = None
        self.controls_container = None
        self.checkbox = None
        self.delete_button = None
        
        # NAPRAWKA: Używaj "FileTileWidget" dla odpowiedniej stylizacji tła
        self.setObjectName("FileTileWidget")
        self.setStyleSheet(TileStylesheet.get_file_tile_stylesheet())
        self.setFixedSize(self.thumbnail_size[0], self.thumbnail_size[1])
        
        # Włącz wsparcie dla stylowania tła widgetu
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        # Inicjalizacja UI
        self._init_ui()
        
    def _init_ui(self):
        """Inicjalizuje elementy interfejsu - identyczne z FileTileWidget."""
        # Główny layout - pionowy, z optymalnimi marginesami
        self.layout = QVBoxLayout(self)
        margins = TileSizeConstants.LAYOUT_MARGINS
        self.layout.setContentsMargins(margins[0], margins[1], margins[2], margins[3])
        self.layout.setSpacing(TileSizeConstants.LAYOUT_SPACING)

        # --- Frame - kontener na miniaturę z kolorową obwódką ---
        self.thumbnail_frame = QFrame(self)
        self.thumbnail_frame.setStyleSheet(TileStylesheet.get_thumbnail_frame_stylesheet())

        # Ustawienie layoutu dla thumbnail_frame - bez odstępów
        thumbnail_frame_layout = QVBoxLayout(self.thumbnail_frame)
        thumbnail_frame_layout.setContentsMargins(0, 0, 0, 0)
        thumbnail_frame_layout.setSpacing(0)

        # Label na miniaturę - umieszczona wewnątrz ramki
        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Konfiguracja miniatury aby była kwadratowa i skalowała się poprawnie
        self.thumbnail_label.setMinimumSize(
            TileSizeConstants.MIN_THUMBNAIL_WIDTH,
            TileSizeConstants.MIN_THUMBNAIL_HEIGHT,
        )

        # Obliczenie wymiarów dla miniatury kwadratowej
        thumb_size = min(
            self.thumbnail_size[0] - TileSizeConstants.TILE_PADDING * 2,
            self.thumbnail_size[1]
            - TileSizeConstants.FILENAME_MAX_HEIGHT
            - TileSizeConstants.METADATA_MAX_HEIGHT,
        )
        
        # Zabezpieczenie przed ujemnymi wymiarami
        thumb_size = max(thumb_size, TileSizeConstants.MIN_THUMBNAIL_WIDTH)
        
        self.thumbnail_label.setFixedSize(thumb_size, thumb_size)
        self.thumbnail_label.setScaledContents(True)
        self.thumbnail_label.setFrameShape(QFrame.Shape.NoFrame)

        # Zastosowanie centralnych stylów dla miniatury
        self.thumbnail_label.setStyleSheet(TileStylesheet.get_thumbnail_label_stylesheet())
        
        # Załaduj miniaturkę
        self._load_thumbnail()

        # Obsługa kliknięcia w miniaturkę
        self.thumbnail_label.setCursor(Qt.CursorShape.PointingHandCursor)
        # NAPRAWKA: Dodaj event filter jak w FileTileWidget dla poprawnej obsługi kliknięć
        self.thumbnail_label.installEventFilter(self)

        # Dodanie thumbnail_label do thumbnail_frame
        thumbnail_frame_layout.addWidget(self.thumbnail_label)

        # Dodanie ramki z miniaturą do głównego layoutu
        self.layout.addWidget(self.thumbnail_frame, 0, Qt.AlignmentFlag.AlignHCenter)

        # Etykieta na nazwę pliku
        file_name = os.path.basename(self.preview_path)
        self.filename_label = QLabel(
            file_name if len(file_name) < 25 else file_name[:20] + "...",
            self
        )
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filename_label.setWordWrap(True)
        self.filename_label.setMaximumHeight(TileSizeConstants.FILENAME_MAX_HEIGHT)
        self.filename_label.setToolTip(file_name)

        # Zastosowanie stylu z odpowiednim rozmiarem czcionki
        self._update_font_size()

        self.layout.addWidget(self.filename_label)

        # --- Kontrolki (checkbox + przycisk usuń) ---
        self.controls_container = QWidget(self)
        self.controls_container.setMaximumHeight(TileSizeConstants.METADATA_MAX_HEIGHT)
        controls_layout = QHBoxLayout(self.controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(5)

        # Checkbox do zaznaczania
        self.checkbox = QCheckBox()
        self.checkbox.setToolTip("Zaznacz ten podgląd do sparowania")
        controls_layout.addWidget(self.checkbox)

        # Elastyczna przestrzeń
        controls_layout.addStretch()

        # Przycisk do usuwania podglądu
        self.delete_button = QPushButton()
        self.delete_button.setToolTip("Usuń plik podglądu")
        self.delete_button.setFixedSize(QSize(24, 24))
        self.delete_button.setIconSize(QSize(16, 16))
        controls_layout.addWidget(self.delete_button)

        self.layout.addWidget(self.controls_container)
        
    def _load_thumbnail(self):
        """
        Ładuje miniaturkę do thumbnail_label.
        NAPRAWKA: Używa create_thumbnail_from_file() jak FileTileWidget dla identycznego formatowania!
        """
        from src.utils.image_utils import create_thumbnail_from_file
        
        # Użyj tej samej funkcji co FileTileWidget!
        width = height = self.thumbnail_label.width()
        pixmap = create_thumbnail_from_file(self.preview_path, width, height)
        
        if not pixmap.isNull():
            self.thumbnail_label.setPixmap(pixmap)
        else:
            self.thumbnail_label.setText("Nie można załadować podglądu")

    def _update_font_size(self):
        """Aktualizuje rozmiar czcionki w zależności od rozmiaru kafelka."""
        base_font_size = max(8, min(18, int(self.thumbnail_size[0] / 12)))
        self.filename_label.setStyleSheet(TileStylesheet.get_filename_label_stylesheet(base_font_size))

    def set_thumbnail_size(self, new_size: tuple[int, int]):
        """Ustawia nowy rozmiar kafelka i dostosowuje jego zawartość."""
        if self.thumbnail_size != new_size:
            self.thumbnail_size = new_size
            
            # Ustaw stały rozmiar całego widgetu kafelka
            self.setFixedSize(new_size[0], new_size[1])

            # Oblicz kwadratowy rozmiar dla samej miniatury
            thumb_dimension = min(
                new_size[0] - TileSizeConstants.TILE_PADDING * 2,
                new_size[1]
                - TileSizeConstants.FILENAME_MAX_HEIGHT
                - TileSizeConstants.METADATA_MAX_HEIGHT
                - TileSizeConstants.TILE_PADDING * 2,
            )

            # Zabezpieczenie przed ujemnymi wymiarami
            thumb_dimension = max(thumb_dimension, TileSizeConstants.MIN_THUMBNAIL_WIDTH)

            # Ustaw rozmiar etykiety miniatury
            self.thumbnail_label.setFixedSize(thumb_dimension, thumb_dimension)

            # Skalowanie czcionki w zależności od rozmiaru kafelka
            self._update_font_size()

            # Przeładuj miniaturkę w nowym rozmiarze
            self._load_thumbnail()

            # Aktualizuj layout
            self.updateGeometry()

    def eventFilter(self, obj, event):
        """
        NAPRAWKA: Obsługuje kliknięcia na etykiecie miniatury jak w FileTileWidget.
        """
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                if obj == self.thumbnail_label:
                    logging.debug(f"Kliknięcie w miniaturkę: {os.path.basename(self.preview_path)}")
                    # NAPRAWKA: Emituj sygnał zamiast bezpośredniego wywołania
                    self.preview_image_requested.emit(self.preview_path)
                    return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        """Obsługuje kliknięcie w kafelek - zachowana kompatybilność."""
        super().mousePressEvent(event)

    def thumbnail_clicked(self):
        """Obsługuje kliknięcie w miniaturkę - do przesłonięcia w klasie nadrzędnej."""
        pass


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
        self.preview_checkboxes = []
        # Przechowywanie referencji do kafelków dla skalowania
        self.preview_tile_widgets = []
        # Aktualny rozmiar miniaturek
        self.current_thumbnail_size = TileSizeConstants.DEFAULT_THUMBNAIL_SIZE

    def create_unpaired_files_tab(self) -> QWidget:
        """
        Tworzy zakładkę niesparowanych plików.

        Returns:
            Widget zakładki niesparowanych plików
        """
        logging.info("🏗️ CREATE_UNPAIRED_FILES_TAB - rozpoczynam tworzenie")
        
        self.unpaired_files_tab = QWidget()
        self.unpaired_files_layout = QVBoxLayout(self.unpaired_files_tab)
        self.unpaired_files_layout.setContentsMargins(5, 5, 5, 5)
        logging.info("✅ Utworzono podstawowy widget i layout")

        # Splitter dla dwóch list
        self.unpaired_splitter = QSplitter()
        logging.info("✅ Utworzono splitter")

        # Lista niesparowanych archiwów
        logging.info("🔧 Tworzę listę archiwów...")
        self._create_unpaired_archives_list()
        logging.info(f"✅ Lista archiwów utworzona. Widget: {hasattr(self, 'unpaired_archives_list_widget')}")
        if hasattr(self, 'unpaired_archives_list_widget'):
            logging.info(f"✅ Wartość widget archiwów: {self.unpaired_archives_list_widget}")

        # Lista niesparowanych podglądów
        logging.info("🔧 Tworzę listę podglądów...")
        self._create_unpaired_previews_list()
        logging.info(f"✅ Lista podglądów utworzona. Widget: {hasattr(self, 'unpaired_previews_list_widget')}")
        if hasattr(self, 'unpaired_previews_list_widget'):
            logging.info(f"✅ Wartość widget podglądów: {self.unpaired_previews_list_widget}")
        
        self.unpaired_files_layout.addWidget(self.unpaired_splitter)

        # Przycisk do ręcznego parowania
        self.pair_manually_button = QPushButton("Sparuj Wybrane")
        self.pair_manually_button.clicked.connect(self._handle_manual_pairing)
        self.pair_manually_button.setEnabled(False)
        self.unpaired_files_layout.addWidget(self.pair_manually_button)
        logging.debug("Przycisk parowania utworzony")

        logging.debug("UnpairedFilesTab utworzona")
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
        Używa uproszczonej wersji FileTileWidget bez gwiazdek i tagów kolorów.

        Args:
            preview_path: Ścieżka do pliku podglądu
        """
        # Upewnij się, że plik istnieje
        if not os.path.exists(preview_path):
            return

        # Utwórz kafelek podglądu
        preview_tile = UnpairedPreviewTile(preview_path, self.unpaired_previews_container)
        preview_tile.set_thumbnail_size(self.current_thumbnail_size)
        
        # NAPRAWKA: Podłącz sygnał preview_image_requested do metody wyświetlającej PreviewDialog
        preview_tile.preview_image_requested.connect(self._show_preview_dialog)
        preview_tile.checkbox.stateChanged.connect(
            lambda state, cb=preview_tile.checkbox, path=preview_path: self._on_preview_checkbox_changed(
                cb, path, state
            )
        )
        preview_tile.delete_button.clicked.connect(lambda: self._delete_preview_file(preview_path))
        
        # Ustaw ikonę dla przycisku usuń
        trash_icon = self.main_window.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        preview_tile.delete_button.setIcon(trash_icon)
        
        # Dodaj do listy checkboxów i kafelków
        self.preview_checkboxes.append(preview_tile.checkbox)
        self.preview_tile_widgets.append(preview_tile)

        # Dodaj do siatki - maksymalnie 3 miniaturki w rzędzie
        row, col = divmod(self.unpaired_previews_layout.count(), 3)
        self.unpaired_previews_layout.addWidget(preview_tile, row, col)

    def _show_preview_dialog(self, preview_path: str):
        """
        NAPRAWKA: Wyświetla okno dialogowe z podglądem obrazu jak w galerii.
        
        Args:
            preview_path: Ścieżka do pliku podglądu
        """
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

            # NAPRAWKA: Używaj PreviewDialog jak w galerii
            dialog = PreviewDialog(pixmap, self.main_window)
            dialog.exec()

        except Exception as e:
            error_message = f"Wystąpił błąd podczas ładowania podglądu: {e}"
            logging.error(error_message)
            QMessageBox.critical(self.main_window, "Błąd Podglądu", error_message)

    def _on_thumbnail_click(self, preview_path):
        """
        Obsługuje kliknięcie w miniaturkę - otwiera podgląd obrazu.
        DEPRECATED: Zastąpione przez _show_preview_dialog
        
        Args:
            preview_path: Ścieżka do pliku podglądu
        """
        self._show_preview_dialog(preview_path)

    def _on_preview_checkbox_changed(self, checkbox, preview_path, state):
        """
        Obsługuje zmianę stanu checkboxa, zapewniając wybór tylko jednego elementu.
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
            for i in range(self.unpaired_previews_list_widget.count()):
                item = self.unpaired_previews_list_widget.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == preview_path:
                    self.unpaired_previews_list_widget.setCurrentItem(item)
                    break
        else:
            # Odznacz element na liście, jeśli to on był zaznaczony
            current_item = self.unpaired_previews_list_widget.currentItem()
            if current_item and current_item.data(Qt.ItemDataRole.UserRole) == preview_path:
                self.unpaired_previews_list_widget.setCurrentItem(None)

        # Odblokuj sygnały
        checkbox.blockSignals(False)

        # Aktualizacja stanu przycisku jest wywoływana przez sygnał
        # itemSelectionChanged z unpaired_previews_list_widget

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
        # NAPRAWKA: Wyczyść również listę kafelków
        self.preview_tile_widgets.clear()
        logging.debug("Wyczyszczono listy niesparowanych plików w UI.")

    def update_unpaired_files_lists(self):
        """
        Aktualizuje listy niesparowanych plików w interfejsie użytkownika.
        """
        logging.debug("Aktualizacja unpaired files")
        
        # NAPRAWKA: Sprawdzamy tylko czy atrybut istnieje, nie jego wartość boolean
        if not hasattr(self, 'unpaired_archives_list_widget'):
            logging.error("❌ KRYTYCZNY BŁĄD: unpaired_archives_list_widget nie istnieje w managerie!")
            return

        if not hasattr(self, 'unpaired_previews_list_widget'):
            logging.error("❌ KRYTYCZNY BŁĄD: unpaired_previews_list_widget nie istnieje w managerie!")
            return

        if not hasattr(self, 'unpaired_previews_layout'):
            logging.error("❌ KRYTYCZNY BŁĄD: unpaired_previews_layout nie istnieje w managerie!")
            return

        # NAPRAWKA: Sprawdzamy czy widget jest None a nie czy jest "falsy"
        if self.unpaired_archives_list_widget is None:
            logging.error("❌ unpaired_archives_list_widget jest None!")
            return
            
        if self.unpaired_previews_list_widget is None:
            logging.error("❌ unpaired_previews_list_widget jest None!")
            return

        # DEBUG: Sprawdź stan w kontrolerze
        archives_count = len(self.main_window.controller.unpaired_archives)
        previews_count = len(self.main_window.controller.unpaired_previews)
        logging.debug(f"Unpaired: {archives_count} archiwów, {previews_count} podglądów")
        
        # Logi szczegółów plików tylko w trybie DEBUG
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            for i, archive in enumerate(self.main_window.controller.unpaired_archives[:3]):  # Tylko pierwsze 3
                logging.debug(f"Archive {i}: {os.path.basename(archive)}")
            if len(self.main_window.controller.unpaired_archives) > 3:
                logging.debug(f"... i {len(self.main_window.controller.unpaired_archives) - 3} więcej archiwów")

        # UŻYWAMY BEZPOŚREDNIO ATRYBUTÓW Z MANAGERA
        self.unpaired_archives_list_widget.clear()
        self.unpaired_previews_list_widget.clear()
        self.preview_checkboxes.clear()
        # NAPRAWKA: Wyczyść listę kafelków
        self.preview_tile_widgets.clear()

        # Wyczyść kontener miniaturek
        while self.unpaired_previews_layout.count():
            item_to_remove = self.unpaired_previews_layout.takeAt(0)
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

        # NAPRAWKA: Sortuj alfabetycznie przed wyświetleniem (dodatkowe zabezpieczenie)
        sorted_archives = sorted(self.main_window.controller.unpaired_archives, 
                                key=lambda x: os.path.basename(x).lower())
        sorted_previews = sorted(self.main_window.controller.unpaired_previews, 
                                key=lambda x: os.path.basename(x).lower())

        # Aktualizuj listę archiwów - stan z Controller (posortowany)
        for archive_path in sorted_archives:
            item = QListWidgetItem(os.path.basename(archive_path))
            item.setData(Qt.ItemDataRole.UserRole, archive_path)
            self.unpaired_archives_list_widget.addItem(item)
            # Spam logów wyeliminowany - każdy plik nie potrzebuje osobnego loga

        # Aktualizuj miniaturki podglądów - stan z Controller (posortowany)
        for preview_path in sorted_previews:
            # Dodaj do ukrytego QListWidget dla kompatybilności
            item = QListWidgetItem(os.path.basename(preview_path))
            item.setData(Qt.ItemDataRole.UserRole, preview_path)
            self.unpaired_previews_list_widget.addItem(item)

            # Dodaj miniaturkę
            preview_name = os.path.basename(preview_path)
            # Usunięto spam logów - progress raportowany przez progress bar
            self._add_preview_thumbnail(preview_path)

        logging.debug(f"Zakończono aktualizację unpaired: {archives_count} archiwów, {previews_count} podglądów")
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
            current_directory = self.main_window.controller.current_directory
            self.main_window.file_operations_ui.handle_manual_pairing(
                self.unpaired_archives_list_widget,
                self.unpaired_previews_list_widget,
                current_directory,
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

    def update_thumbnail_size(self, new_size: tuple):
        """
        Aktualizuje rozmiar miniaturek w zakładce unpaired files.
        
        Args:
            new_size: Nowa wielkość kafelka (width, height)
        """
        self.current_thumbnail_size = new_size
        
        # Aktualizuj wszystkie istniejące kafelki
        for preview_tile in self.preview_tile_widgets:
            if isinstance(preview_tile, UnpairedPreviewTile):
                preview_tile.set_thumbnail_size(new_size)
