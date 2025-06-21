"""
Zakładka niesparowanych plików - wydzielona z main_window.py.
"""

import logging
import os
from typing import TYPE_CHECKING

from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from src.ui.delegates.workers.file_list_workers import BulkDeleteFilesWorker
from src.ui.widgets.preview_dialog import PreviewDialog
from src.ui.widgets.unpaired_archives_list import UnpairedArchivesList
from src.ui.widgets.unpaired_previews_grid import UnpairedPreviewsGrid

# Dodaj import stylów z FileTileWidget
from src.ui.widgets.tile_styles import TileSizeConstants, TileStylesheet

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

        self.setObjectName("FileTileWidget")
        self.setStyleSheet(TileStylesheet.get_file_tile_stylesheet())
        
        # Obsługa różnych formatów thumbnail_size
        if isinstance(self.thumbnail_size, int):
            size_tuple = (self.thumbnail_size, self.thumbnail_size)
        else:
            size_tuple = self.thumbnail_size
        self.setFixedSize(size_tuple[0], size_tuple[1])

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
        self.thumbnail_frame.setStyleSheet(
            TileStylesheet.get_thumbnail_frame_stylesheet()
        )

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
        # Obsługa różnych formatów thumbnail_size
        if isinstance(self.thumbnail_size, int):
            thumb_width = self.thumbnail_size
            thumb_height = self.thumbnail_size
        else:
            thumb_width = self.thumbnail_size[0]
            thumb_height = self.thumbnail_size[1]
            
        thumb_size = min(
            thumb_width - TileSizeConstants.TILE_PADDING * 2,
            thumb_height
            - TileSizeConstants.FILENAME_MAX_HEIGHT
            - TileSizeConstants.METADATA_MAX_HEIGHT,
        )

        # Zabezpieczenie przed ujemnymi wymiarami
        thumb_size = max(thumb_size, TileSizeConstants.MIN_THUMBNAIL_WIDTH)

        self.thumbnail_label.setFixedSize(thumb_size, thumb_size)
        self.thumbnail_label.setScaledContents(True)
        self.thumbnail_label.setFrameShape(QFrame.Shape.NoFrame)

        # Zastosowanie centralnych stylów dla miniatury
        self.thumbnail_label.setStyleSheet(
            TileStylesheet.get_thumbnail_label_stylesheet()
        )

        # Załaduj miniaturkę
        self._load_thumbnail()

        # Obsługa kliknięcia w miniaturkę
        self.thumbnail_label.setCursor(Qt.CursorShape.PointingHandCursor)
        # Dodaj event filter dla obsługi kliknięć
        self.thumbnail_label.installEventFilter(self)

        # Dodanie thumbnail_label do thumbnail_frame
        thumbnail_frame_layout.addWidget(self.thumbnail_label)

        # Dodanie ramki z miniaturą do głównego layoutu
        self.layout.addWidget(self.thumbnail_frame, 0, Qt.AlignmentFlag.AlignHCenter)

        # Etykieta na nazwę pliku
        file_name = os.path.basename(self.preview_path)
        self.filename_label = QLabel(
            file_name if len(file_name) < 25 else file_name[:20] + "...", self
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
        Używa create_thumbnail_from_file() dla identycznego formatowania.
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
        # Uzyskaj szerokość z thumbnail_size (może być int lub tuple)
        if isinstance(self.thumbnail_size, int):
            width = self.thumbnail_size
        else:
            width = self.thumbnail_size[0]
        
        base_font_size = max(8, min(18, int(width / 12)))
        self.filename_label.setStyleSheet(
            TileStylesheet.get_filename_label_stylesheet(base_font_size)
        )

    def set_thumbnail_size(self, new_size):
        """Ustawia nowy rozmiar kafelka i dostosowuje jego zawartość."""
        if self.thumbnail_size != new_size:
            self.thumbnail_size = new_size

            # Przekształć na krotkę jeśli otrzymano pojedynczą wartość
            if isinstance(new_size, int):
                size_tuple = (new_size, new_size)
            else:
                size_tuple = new_size

            # Ustaw stały rozmiar całego widgetu kafelka
            self.setFixedSize(size_tuple[0], size_tuple[1])

            # Oblicz kwadratowy rozmiar dla samej miniatury
            thumb_dimension = min(
                size_tuple[0] - TileSizeConstants.TILE_PADDING * 2,
                size_tuple[1]
                - TileSizeConstants.FILENAME_MAX_HEIGHT
                - TileSizeConstants.METADATA_MAX_HEIGHT
                - TileSizeConstants.TILE_PADDING * 2,
            )

            # Zabezpieczenie przed ujemnymi wymiarami
            thumb_dimension = max(
                thumb_dimension, TileSizeConstants.MIN_THUMBNAIL_WIDTH
            )

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
        Obsługuje kliknięcia na etykiecie miniatury.
        """
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                if obj == self.thumbnail_label:
                    logging.debug(
                        f"Kliknięcie w miniaturkę: {os.path.basename(self.preview_path)}"
                    )
                    # Emituj sygnał zamiast bezpośredniego wywołania
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
        # Nowy widget do zarządzania archiwami
        self.unpaired_archives_list = None
        # Nowy widget do zarządzania podglądami
        self.unpaired_previews_grid = None
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
        logging.debug("Creating unpaired files tab")

        self.unpaired_files_tab = QWidget()
        self.unpaired_files_layout = QVBoxLayout(self.unpaired_files_tab)
        self.unpaired_files_layout.setContentsMargins(5, 5, 5, 5)
        logging.debug("Basic widget and layout created")

        # Splitter dla dwóch list
        self.unpaired_splitter = QSplitter()
        logging.debug("Splitter created")

        # Lista niesparowanych archiwów
        logging.debug("Creating archives list")
        self._create_unpaired_archives_list()
        logging.debug("Archives list created successfully")

        # Lista niesparowanych podglądów
        logging.debug("Creating previews list")
        self._create_unpaired_previews_list()
        logging.debug("Previews list created successfully")

        self.unpaired_files_layout.addWidget(self.unpaired_splitter)

        # Panel przycisków
        buttons_panel = QWidget()
        buttons_panel.setFixedHeight(35)
        buttons_layout = QHBoxLayout(buttons_panel)
        buttons_layout.setContentsMargins(5, 2, 5, 2)
        buttons_layout.setSpacing(10)

        # Przycisk do ręcznego parowania
        self.pair_manually_button = QPushButton("✅ Sparuj manualnie")
        self.pair_manually_button.setToolTip(
            "Sparuj zaznaczone archiwum z zaznaczonym podglądem"
        )
        self.pair_manually_button.setMinimumHeight(40)
        self.pair_manually_button.clicked.connect(self._handle_manual_pairing)
        self.pair_manually_button.setEnabled(False)
        buttons_layout.addWidget(self.pair_manually_button)

        # Przycisk do usuwania wszystkich nieparowanych podglądów
        self.delete_unpaired_previews_button = QPushButton("🗑️ Usuń podglądy bez pary")
        self.delete_unpaired_previews_button.setToolTip(
            "Usuwa z dysku wszystkie pliki podglądów z tej listy"
        )
        self.delete_unpaired_previews_button.setMinimumHeight(40)
        self.delete_unpaired_previews_button.clicked.connect(
            self._handle_delete_unpaired_previews
        )
        buttons_layout.addWidget(self.delete_unpaired_previews_button)

        # Przycisk do przenoszenia niesparowanych archiwów
        self.move_unpaired_button = QPushButton("🚚 Przenieś archiwa")
        self.move_unpaired_button.setToolTip(
            "Przenosi wszystkie pliki archiwum bez pary do folderu '_bez_pary_'"
        )
        self.move_unpaired_button.setMinimumHeight(40)
        self.move_unpaired_button.clicked.connect(self._handle_move_unpaired_archives)
        buttons_layout.addWidget(self.move_unpaired_button)

        self.unpaired_files_layout.addWidget(buttons_panel)
        logging.debug("Przyciski parowania i przenoszenia utworzone")

        logging.debug("UnpairedFilesTab utworzona")
        return self.unpaired_files_tab

    def _create_unpaired_archives_list(self):
        """
        Tworzy listę niesparowanych archiwów używając dedykowanego widget'a.
        """
        # Utwórz nowy widget do zarządzania archiwami
        self.unpaired_archives_list = UnpairedArchivesList(self.main_window)
        
        # Podłącz sygnały
        self.unpaired_archives_list.selection_changed.connect(self._update_pair_button_state)
        
        # Zachowaj kompatybilność z istniejącym kodem
        self.unpaired_archives_list_widget = self.unpaired_archives_list.list_widget
        
        # Dodaj do splitter'a
        self.unpaired_splitter.addWidget(self.unpaired_archives_list)


    def _create_unpaired_previews_list(self):
        """
        Tworzy panel niesparowanych podglądów używając dedykowanego widget'a.
        """
        # Utwórz nowy widget do zarządzania podglądami
        self.unpaired_previews_grid = UnpairedPreviewsGrid(self.main_window)
        
        # Podłącz sygnały
        self.unpaired_previews_grid.selection_changed.connect(self._update_pair_button_state)
        self.unpaired_previews_grid.preview_deleted.connect(self._delete_preview_file)
        
        # Zachowaj kompatybilność z istniejącym kodem
        self.unpaired_previews_list_widget = self.unpaired_previews_grid.hidden_list_widget
        self.unpaired_previews_layout = self.unpaired_previews_grid.grid_layout
        self.unpaired_previews_container = self.unpaired_previews_grid.container
        
        # Dodaj do splitter'a
        self.unpaired_splitter.addWidget(self.unpaired_previews_grid)

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
        preview_tile = UnpairedPreviewTile(
            preview_path, self.unpaired_previews_container
        )
        preview_tile.set_thumbnail_size(self.current_thumbnail_size)

        # Podłącz sygnał preview_image_requested do metody wyświetlającej PreviewDialog
        preview_tile.preview_image_requested.connect(self._show_preview_dialog)
        preview_tile.checkbox.stateChanged.connect(
            lambda state, cb=preview_tile.checkbox, path=preview_path: self._on_preview_checkbox_changed(
                cb, path, state
            )
        )
        preview_tile.delete_button.clicked.connect(
            lambda: self._delete_preview_file(preview_path)
        )

        # Ustaw ikonę dla przycisku usuń
        trash_icon = self.main_window.style().standardIcon(
            QStyle.StandardPixmap.SP_TrashIcon
        )
        preview_tile.delete_button.setIcon(trash_icon)

        # Dodaj do listy checkboxów i kafelków
        self.preview_checkboxes.append(preview_tile.checkbox)
        self.preview_tile_widgets.append(preview_tile)

        # Dodaj do siatki - maksymalnie 3 miniaturki w rzędzie
        row, col = divmod(self.unpaired_previews_layout.count(), 3)
        self.unpaired_previews_layout.addWidget(preview_tile, row, col)

    def _show_preview_dialog(self, preview_path: str):
        """
        Wyświetla okno dialogowe z podglądem obrazu.

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

            # Używaj PreviewDialog jak w galerii
            dialog = PreviewDialog(pixmap, self.main_window)
            dialog.exec()

        except Exception as e:
            error_message = f"Wystąpił błąd podczas ładowania podglądu: {e}"
            logging.error(error_message)
            QMessageBox.critical(self.main_window, "Błąd Podglądu", error_message)


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
            if (
                current_item
                and current_item.data(Qt.ItemDataRole.UserRole) == preview_path
            ):
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
            f"Czy na pewno chcesz trwale usunąć plik "
            f"{os.path.basename(preview_path)}?",
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
        # Wyczyść nowy widget archiwów
        if self.unpaired_archives_list:
            self.unpaired_archives_list.clear()
        # Zachowaj kompatybilność z starym kodem
        elif self.unpaired_archives_list_widget:
            self.unpaired_archives_list_widget.clear()
            
        # Wyczyść nowy widget podglądów
        if self.unpaired_previews_grid:
            self.unpaired_previews_grid.clear()
        # Zachowaj kompatybilność z starym kodem
        elif self.unpaired_previews_list_widget:
            self.unpaired_previews_list_widget.clear()
        # Wyczyść również listę kafelków
        self.preview_tile_widgets.clear()
        logging.debug("Wyczyszczono listy niesparowanych plików w UI.")

    def update_unpaired_files_lists(self):
        """
        Aktualizuje listy niesparowanych plików w interfejsie użytkownika.
        """
        logging.debug("Aktualizacja unpaired files")

        # Sprawdzamy tylko czy atrybut istnieje, nie jego wartość boolean
        if not hasattr(self, "unpaired_archives_list_widget") and not hasattr(self, "unpaired_archives_list"):
            logging.error(
                "CRITICAL ERROR: Brak widget'a do zarządzania archiwami!"
            )
            return

        if not hasattr(self, "unpaired_previews_list_widget") and not hasattr(self, "unpaired_previews_grid"):
            logging.error(
                "CRITICAL ERROR: Brak widget'a do zarządzania podglądami!"
            )
            return

        if not hasattr(self, "unpaired_previews_layout") and not hasattr(self, "unpaired_previews_grid"):
            logging.error(
                "CRITICAL ERROR: Brak widget'a/layoutu do zarządzania podglądami!"
            )
            return

        # Sprawdzamy czy widget jest None a nie czy jest "falsy"
        if (self.unpaired_archives_list_widget is None and 
            self.unpaired_archives_list is None):
            logging.error("Brak widget'a do zarządzania archiwami!")
            return

        if (self.unpaired_previews_list_widget is None and 
            self.unpaired_previews_grid is None):
            logging.error("Brak widget'a do zarządzania podglądami!")
            return

        archives_count = len(self.main_window.controller.unpaired_archives)
        previews_count = len(self.main_window.controller.unpaired_previews)
        logging.debug(
            f"Unpaired: {archives_count} archiwów, {previews_count} podglądów"
        )

        if logging.getLogger().isEnabledFor(logging.DEBUG):
            for i, archive in enumerate(
                self.main_window.controller.unpaired_archives[:3]
            ):
                logging.debug(f"Archive {i}: {os.path.basename(archive)}")
            if len(self.main_window.controller.unpaired_archives) > 3:
                logging.debug(
                    f"... i {len(self.main_window.controller.unpaired_archives) - 3} więcej archiwów"
                )

        # WYCZYŚĆ UŻYWAJĄC NOWYCH WIDGET'ÓW
        # Wyczyść nowy widget archiwów
        if self.unpaired_archives_list:
            self.unpaired_archives_list.clear()
        # Fallback dla starego kodu
        elif self.unpaired_archives_list_widget:
            self.unpaired_archives_list_widget.clear()
            
        # Wyczyść nowy widget podglądów  
        if self.unpaired_previews_grid:
            self.unpaired_previews_grid.clear()
        # Fallback dla starego kodu
        elif self.unpaired_previews_list_widget:
            self.unpaired_previews_list_widget.clear()
            
        # Wyczyść stare listy pomocnicze
        self.preview_checkboxes.clear()
        self.preview_tile_widgets.clear()

        # Sortuj alfabetycznie przed wyświetleniem (dodatkowe zabezpieczenie)
        sorted_archives = sorted(
            self.main_window.controller.unpaired_archives,
            key=lambda x: os.path.basename(x).lower(),
        )
        sorted_previews = sorted(
            self.main_window.controller.unpaired_previews,
            key=lambda x: os.path.basename(x).lower(),
        )

        # Aktualizuj listę archiwów używając nowego widget'a
        if self.unpaired_archives_list:
            self.unpaired_archives_list.update_archives(sorted_archives)

        # Aktualizuj miniaturki podglądów używając nowego widget'a
        if self.unpaired_previews_grid:
            self.unpaired_previews_grid.update_previews(sorted_previews)

        logging.debug(
            f"Zakończono aktualizację unpaired: {archives_count} archiwów, {previews_count} podglądów"
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
            current_directory = self.main_window.controller.current_directory
            self.main_window.file_operations_ui.handle_manual_pairing(
                self.unpaired_archives_list_widget,
                self.unpaired_previews_list_widget,
                current_directory,
            )

    def _handle_move_unpaired_archives(self):
        """
        Przenosi wszystkie pliki archiwum bez pary do folderu '_bez_pary_'.
        """
        current_directory = self.main_window.controller.current_directory
        if not current_directory:
            QMessageBox.warning(
                self.main_window,
                "Brak folderu roboczego",
                "Nie wybrano folderu roboczego.",
            )
            return

        # Pobierz listę niesparowanych archiwów
        unpaired_archives = self.main_window.controller.unpaired_archives
        if not unpaired_archives:
            QMessageBox.information(
                self.main_window,
                "Brak plików",
                "Nie ma plików archiwum bez pary do przeniesienia.",
            )
            return

        # Pokaż dialog potwierdzenia
        reply = QMessageBox.question(
            self.main_window,
            "Potwierdzenie przeniesienia",
            f"Czy na pewno chcesz przenieść {len(unpaired_archives)} plików archiwum bez pary "
            f"do folderu '_bez_pary_'?\n\n"
            f"Ta operacja jest nieodwracalna.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Utwórz folder '_bez_pary_' jeśli nie istnieje
        target_folder = os.path.join(current_directory, "_bez_pary_")
        try:
            os.makedirs(target_folder, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(
                self.main_window,
                "Błąd tworzenia folderu",
                f"Nie udało się utworzyć folderu '_bez_pary_':\n{str(e)}",
            )
            return

        # Uruchom worker do przenoszenia plików
        self._start_move_unpaired_worker(unpaired_archives, target_folder)

    def _start_move_unpaired_worker(self, unpaired_archives: list, target_folder: str):
        """Uruchamia workera do przenoszenia niesparowanych plików w tle."""
        if not hasattr(self.main_window, "worker_manager"):
            self.logger.error("Brak dostępu do WorkerManagera.")
            QMessageBox.critical(self, "Błąd", "Brak dostępu do menedżera zadań.")
            return

        self.main_window.worker_manager.run_worker(
            BulkMoveFilesWorker,
            files_to_move=unpaired_archives,
            destination_folder=target_folder,
            source_folder=self.main_window.controller.current_directory,
        )

    def _on_move_unpaired_finished(self, result):
        """
        Obsługuje zakończenie przenoszenia plików bez pary.
        """
        try:
            moved_files = result.get("moved_files", [])
            detailed_errors = result.get("detailed_errors", [])
            summary = result.get("summary", {})

            # Ukryj pasek postępu
            self.main_window._hide_progress()

            # Pokaż raport
            self._show_move_unpaired_report(moved_files, detailed_errors, summary)

            # Odśwież widok
            self._refresh_unpaired_files()

        except Exception as e:
            logging.error(f"Błąd podczas obsługi zakończenia przenoszenia: {e}")
            QMessageBox.critical(
                self.main_window,
                "Błąd",
                f"Wystąpił błąd podczas obsługi wyników przenoszenia:\n{str(e)}",
            )

    def _on_move_unpaired_error(self, error_message: str):
        """
        Obsługuje błędy podczas przenoszenia plików bez pary.
        """
        self.main_window._hide_progress()
        QMessageBox.critical(
            self.main_window,
            "Błąd przenoszenia",
            f"Wystąpił błąd podczas przenoszenia plików:\n{error_message}",
        )

    def _show_move_unpaired_report(
        self, moved_files: list, detailed_errors: list, summary: dict
    ):
        """
        Wyświetla raport z przenoszenia plików bez pary.
        """
        total_requested = summary.get("total_requested", 0)
        successfully_moved = summary.get("successfully_moved", 0)
        errors = summary.get("errors", 0)

        # Podstawowy komunikat
        if errors == 0:
            QMessageBox.information(
                self.main_window,
                "Przenoszenie zakończone",
                f"Pomyślnie przeniesiono {successfully_moved} z {total_requested} plików archiwum bez pary do folderu '_bez_pary_'.",
            )
        else:
            # Szczegółowy raport z błędami
            report_lines = [
                f"Przenoszenie zakończone z błędami:",
                f"• Pomyślnie przeniesiono: {successfully_moved}",
                f"• Błędy: {errors}",
                f"• Łącznie przetworzono: {total_requested}",
                "",
            ]

            if detailed_errors:
                report_lines.append("Szczegóły błędów:")
                for error in detailed_errors[:5]:  # Pokaż maksymalnie 5 błędów
                    file_name = os.path.basename(error.get("file_path", "Nieznany"))
                    error_type = error.get("error_type", "NIEZNANY")
                    report_lines.append(f"• {file_name}: {error_type}")

                if len(detailed_errors) > 5:
                    report_lines.append(
                        f"... i {len(detailed_errors) - 5} więcej błędów"
                    )

            QMessageBox.warning(
                self.main_window,
                "Przenoszenie zakończone z błędami",
                "\n".join(report_lines),
            )

    def _refresh_unpaired_files(self):
        """
        Odświeża widok niesparowanych plików po operacjach takich jak usuwanie.
        """
        # Ponowne skanowanie folderu
        current_folder = self.main_window.controller.current_directory
        if current_folder and os.path.isdir(current_folder):
            # Użyj inteligentnego odświeżenia zamiast force_full_refresh
            # aby uniknąć resetowania drzewa katalogów
            if hasattr(self.main_window, "refresh_all_views"):
                self.main_window.refresh_all_views()
            else:
                # Fallback - ale uniknij force_full_refresh!
                logging.warning(
                    "Brak metody refresh_all_views - używam podstawowego odświeżenia bez resetu drzewa"
                )
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

    def update_thumbnail_size(self, new_size):
        """
        Aktualizuje rozmiar miniaturek w zakładce unpaired files.

        Args:
            new_size: Nowa wielkość kafelka (int lub tuple (width, height))
        """
        self.current_thumbnail_size = new_size

        # Aktualizuj rozmiar w nowym widget'u podglądów
        if self.unpaired_previews_grid:
            self.unpaired_previews_grid.update_thumbnail_size(new_size)
        else:
            # Fallback dla starych kafelków
            for preview_tile in self.preview_tile_widgets:
                if isinstance(preview_tile, UnpairedPreviewTile):
                    preview_tile.set_thumbnail_size(new_size)

    def _handle_delete_unpaired_previews(self):
        """
        Obsługuje usuwanie wszystkich nieparowanych plików podglądu.
        """
        # Pobierz wszystkie ścieżki podglądów z nowego widget'a
        if self.unpaired_previews_grid:
            unpaired_previews = self.unpaired_previews_grid.get_all_preview_paths()
        else:
            # Fallback dla starego kodu
            unpaired_previews = [
                self.unpaired_previews_layout.itemAt(i).widget().preview_path
                for i in range(self.unpaired_previews_layout.count())
                if self.unpaired_previews_layout.itemAt(i).widget()
            ]

        if not unpaired_previews:
            QMessageBox.information(
                self.main_window,
                "Informacja",
                "Brak nieparowanych podglądów do usunięcia.",
            )
            return

        reply = QMessageBox.question(
            self.main_window,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz trwale usunąć {len(unpaired_previews)} "
            f"plików podglądu z dysku?\n\nTej operacji nie można cofnąć.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            logging.info(
                f"Rozpoczynanie usuwania {len(unpaired_previews)} "
                "nieparowanych podglądów."
            )
            self._start_delete_unpaired_previews_worker(unpaired_previews)

    def _start_delete_unpaired_previews_worker(self, previews_to_delete: list[str]):
        """
        Uruchamia workera do usuwania nieparowanych podglądów.
        """
        # Użyj uniwersalnej metody run_worker z WorkerManager
        self.main_window.worker_manager.run_worker(
            BulkDeleteFilesWorker,  # Użyj nowego, dedykowanego workera
            on_finished=self._on_delete_unpaired_previews_finished,
            on_error=self._on_delete_unpaired_previews_error,
            show_progress=True,
            files_to_delete=previews_to_delete,  # Przekaż listę ścieżek
        )

    def _on_delete_unpaired_previews_finished(self, result: dict):
        """
        Obsługuje pomyślne zakończenie usuwania nieparowanych podglądów.
        """
        deleted_files = result.get("deleted_files", [])
        errors = result.get("errors", [])
        self.main_window.progress_manager.hide_progress()
        QMessageBox.information(
            self.main_window,
            "Operacja zakończona",
            f"Usunięto {len(deleted_files)} z {len(deleted_files) + len(errors)} "
            f"plików podglądu.\nLiczba błędów: {len(errors)}.",
        )
        # Odśwież widok, aby usunąć kafelki
        self._refresh_unpaired_files()

    def _on_delete_unpaired_previews_error(self, error_message: str):
        """
        Obsługuje błędy podczas usuwania nieparowanych podglądów.
        """
        self.main_window.progress_manager.hide_progress()
        QMessageBox.critical(
            self.main_window,
            "Błąd usuwania",
            f"Wystąpił błąd podczas usuwania plików: {error_message}",
        )
        self._refresh_unpaired_files()
