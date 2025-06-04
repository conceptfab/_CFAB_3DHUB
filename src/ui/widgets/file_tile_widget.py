"""
Kafelek wyświetlający miniaturę podglądu, nazwę i rozmiar pliku archiwum.
"""

import logging

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.models.file_pair import FilePair


class FileTileWidget(QWidget):
    """
    Widget reprezentujący kafelek z miniaturą podglądu, nazwą pliku i rozmiarem archiwum.

    Kafelek wyświetla miniaturę podglądu, nazwę pliku (bez rozszerzenia) i rozmiar pliku
    archiwum. Wielkość miniatury może być modyfikowana.
    """

    # MODIFICATION: Define custom signals
    archive_open_requested = pyqtSignal(FilePair)
    preview_image_requested = pyqtSignal(FilePair)
    favorite_toggled = pyqtSignal(FilePair)

    def __init__(
        self, file_pair: FilePair, default_thumbnail_size=(150, 150), parent=None
    ):
        """
        Inicjalizuje widget kafelka dla pary plików.

        Args:
            file_pair (FilePair): Obiekt pary plików do wyświetlenia
            default_thumbnail_size (tuple): Domyślny rozmiar miniatury (szerokość, wysokość) w pikselach
            parent (QWidget, optional): Widget nadrzędny
        """
        super().__init__(parent)
        self.file_pair = file_pair
        self.thumbnail_size = default_thumbnail_size

        # Zapisywanie oryginalnego QPixmap (niekonwertowanego) do wydajnego skalowania
        # (skalujemy tylko przy wyświetlaniu, a nie tworzymy nowego za każdym razem)
        self.original_thumbnail = None

        # Inicjalizacja UI
        self._init_ui()

        # MODIFICATION: Install event filters for clickable labels
        self.thumbnail_label.installEventFilter(self)
        self.name_label.installEventFilter(self)

        # Ustawienie danych z FilePair
        self.update_data(file_pair)

    def _init_ui(self):
        """
        Inicjalizuje elementy interfejsu użytkownika kafelka.
        """
        # Główny layout - pionowy
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)

        # Kontener miniatury - centrowanie
        self.thumbnail_container = QWidget()
        self.thumbnail_layout = QHBoxLayout(self.thumbnail_container)
        self.thumbnail_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Label na miniaturę
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setMinimumSize(
            self.thumbnail_size[0], self.thumbnail_size[1]
        )
        self.thumbnail_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.thumbnail_layout.addWidget(self.thumbnail_label)

        # Label na nazwę pliku
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setStyleSheet(
            """
            QLabel {
                font-weight: bold;
            }
            QLabel:hover {
                color: #0078D4; /* Standard blue for links/hover */
                text-decoration: underline;
            }
        """
        )

        # Label na rozmiar pliku
        self.size_label = QLabel()
        self.size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Dodanie widgetów do głównego layoutu
        self.layout.addWidget(self.thumbnail_container)
        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.size_label)

        # MODIFICATION: Add favorite button
        self.favorite_button = QPushButton()  # Text set in update_favorite_status
        self.favorite_button.clicked.connect(self._emit_favorite_toggled_signal)
        self.layout.addWidget(self.favorite_button)

        # Ustawiamy preferowany rozmiar całego widgetu
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # MODIFICATION: Adjust minimum size for the new button
        self.setMinimumSize(self.thumbnail_size[0] + 20, self.thumbnail_size[1] + 90)

        # Ustawienie tła i ramki dla wyróżnienia kafelków
        self.setStyleSheet(
            """
            FileTileWidget {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
        """
        )

    def update_data(self, file_pair: FilePair):
        """
        Aktualizuje dane kafelka na podstawie obiektu FilePair.

        Args:
            file_pair (FilePair): Obiekt pary plików z nowymi danymi
        """
        self.file_pair = file_pair

        try:
            # Wczytujemy miniaturę jeśli nie była jeszcze wczytana
            if not self.original_thumbnail:
                thumbnail = self.file_pair.load_preview_thumbnail(self.thumbnail_size)
                if thumbnail and not thumbnail.isNull():
                    self.original_thumbnail = thumbnail
                    self.thumbnail_label.setPixmap(thumbnail)

            # Ustawiamy nazwę (bez rozszerzenia)
            self.name_label.setText(self.file_pair.get_base_name())

            # Ustawiamy rozmiar pliku
            self.size_label.setText(self.file_pair.get_formatted_archive_size())

            # MODIFICATION: Update favorite status on data update
            self.update_favorite_status(self.file_pair.is_favorite_file())

        except Exception as e:
            logging.error(f"Błąd aktualizacji kafelka: {e}")
            # W przypadku błędu, wyświetlamy przynajmniej nazwę jeśli jest dostępna
            try:
                self.name_label.setText(self.file_pair.get_base_name())
                self.size_label.setText("Błąd danych")
            except:
                self.name_label.setText("Błąd")
                self.size_label.setText("")

    def set_thumbnail_size(self, size_wh):
        """
        Ustawia nowy rozmiar miniatury i skaluje ją odpowiednio.

        Args:
            size_wh (tuple): Nowy rozmiar miniatury (szerokość, wysokość) w pikselach
        """
        self.thumbnail_size = size_wh

        # Aktualizacja rozmiaru labela miniatury
        self.thumbnail_label.setMinimumSize(size_wh[0], size_wh[1])

        # Aktualizacja preferowanego rozmiaru całego widgetu
        # MODIFICATION: Adjust minimum size for the new button
        self.setMinimumSize(
            size_wh[0] + 20, size_wh[1] + 90
        )  # +90 dla nazwy, rozmiaru i przycisku ulubione

        # Skalowanie miniatury, jeśli jest dostępna
        if self.original_thumbnail and not self.original_thumbnail.isNull():
            # Skalujemy oryginalną miniaturę (zachowując proporcje)
            scaled_pixmap = self.original_thumbnail.scaled(
                size_wh[0],
                size_wh[1],
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.thumbnail_label.setPixmap(scaled_pixmap)
        else:
            # Jeśli nie ma miniatury, regenerujemy placeholder
            try:
                new_thumbnail = self.file_pair.load_preview_thumbnail(size_wh)
                if new_thumbnail and not new_thumbnail.isNull():
                    self.original_thumbnail = new_thumbnail
                    self.thumbnail_label.setPixmap(new_thumbnail)
            except Exception as e:
                logging.error(f"Błąd reskalowania miniatury: {e}")

    # MODIFICATION: New method to update favorite button appearance
    def update_favorite_status(self, is_favorite: bool):
        """Aktualizuje wygląd przycisku 'Ulubione'."""
        if is_favorite:
            self.favorite_button.setText("★ Odznacz Ulubione")
            self.favorite_button.setStyleSheet(
                "background-color: #fffacd; color: #DAA520;"
            )
        else:
            self.favorite_button.setText("☆ Oznacz Ulubione")
            self.favorite_button.setStyleSheet("")

    # MODIFICATION: New method to emit favorite_toggled signal
    def _emit_favorite_toggled_signal(self):
        """Emituje sygnał zmiany statusu ulubionego."""
        self.favorite_toggled.emit(self.file_pair)

    # MODIFICATION: New method to handle clicks on labels (event filter)
    def eventFilter(self, obj, event):
        """Obsługuje zdarzenia kliknięcia na etykietach miniatury i nazwy."""
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                if obj == self.thumbnail_label:
                    logging.debug(
                        f"Kliknięto miniaturę dla: {self.file_pair.get_base_name()}"
                    )
                    self.preview_image_requested.emit(self.file_pair)
                    return True  # Event handled
                elif obj == self.name_label:
                    logging.debug(
                        f"Kliknięto nazwę dla: {self.file_pair.get_base_name()}"
                    )
                    self.archive_open_requested.emit(self.file_pair)
                    return True  # Event handled
        return super().eventFilter(obj, event)
