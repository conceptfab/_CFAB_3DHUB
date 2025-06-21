"""
Wydzielony kafelek podglądu z unpaired_files_tab.py
"""

import os

from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.tile_styles import TileSizeConstants, TileStylesheet


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
            # Fallback - ikona domyślna
            self.thumbnail_label.setText("🖼️")
            self.thumbnail_label.setStyleSheet(
                "QLabel { color: #888; font-size: 24px; }"
            )

    def _update_font_size(self):
        """Aktualizuje rozmiar czcionki na podstawie rozmiaru kafelka."""
        # Oblicz rozmiar czcionki na podstawie rozmiaru kafelka
        if isinstance(self.thumbnail_size, int):
            base_size = self.thumbnail_size
        else:
            base_size = min(self.thumbnail_size)

        font_size = max(8, min(12, base_size // 12))

        self.filename_label.setStyleSheet(
            f"QLabel {{ font-size: {font_size}px; color: #FFFFFF; }}"
        )

    def set_thumbnail_size(self, new_size):
        """
        Ustawia nowy rozmiar kafelka i aktualizuje wszystkie komponenty.
        """
        self.thumbnail_size = new_size

        # Obsługa różnych formatów thumbnail_size
        if isinstance(self.thumbnail_size, int):
            size_tuple = (self.thumbnail_size, self.thumbnail_size)
        else:
            size_tuple = self.thumbnail_size

        self.setFixedSize(size_tuple[0], size_tuple[1])

        # Przelicz rozmiar miniatury
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

        # Przeładuj miniaturkę z nowym rozmiarem
        self._load_thumbnail()

        # Aktualizuj rozmiar czcionki
        self._update_font_size()

    def eventFilter(self, obj, event):
        """Obsługuje zdarzenia kliknięcia w miniaturkę."""
        if obj == self.thumbnail_label and event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.thumbnail_clicked()
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        """Obsługuje kliknięcie w kafelek."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.thumbnail_clicked()

    def thumbnail_clicked(self):
        """Emituje sygnał kliknięcia w miniaturkę."""
        self.preview_image_requested.emit(self.preview_path)
