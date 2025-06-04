"""
Kafelek wyświetlający miniaturę podglądu, nazwę i rozmiar pliku archiwum.
"""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from src.models.file_pair import FilePair


class FileTileWidget(QWidget):
    """
    Widget reprezentujący kafelek z miniaturą podglądu, nazwą pliku i rozmiarem archiwum.

    Kafelek wyświetla miniaturę podglądu, nazwę pliku (bez rozszerzenia) i rozmiar pliku
    archiwum. Wielkość miniatury może być modyfikowana.
    """

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
        self.name_label.setStyleSheet("font-weight: bold;")

        # Label na rozmiar pliku
        self.size_label = QLabel()
        self.size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Dodanie widgetów do głównego layoutu
        self.layout.addWidget(self.thumbnail_container)
        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.size_label)

        # Ustawiamy preferowany rozmiar całego widgetu
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumSize(self.thumbnail_size[0] + 20, self.thumbnail_size[1] + 60)

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
        self.setMinimumSize(
            size_wh[0] + 20, size_wh[1] + 60
        )  # +60 dla nazwy i rozmiaru

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
