"""
Widget zawierający kontrolki do zarządzania metadanymi pliku,
takimi jak ulubione, ocena w gwiazdkach i tag kolorystyczny.
"""

import logging
from collections import OrderedDict

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from src.models.file_pair import FilePair


class MetadataControlsWidget(QWidget):
    """
    Widget grupujący kontrolki metadanych: Ulubione, Gwiazdki, Kolor.
    Emituje sygnały po interakcji użytkownika.
    """

    # Sygnały emitowane przez ten widget po zmianie wartości przez użytkownika
    # Nie zawierają FilePair, tylko nową wartość.
    # FileTileWidget będzie odpowiedzialny za aktualizację FilePair.
    favorite_status_changed = pyqtSignal(bool)  # True if favorite, False otherwise
    stars_value_changed = pyqtSignal(int)  # new star count (0-5)
    color_tag_value_changed = pyqtSignal(str)  # new color hex string

    PREDEFINED_COLORS = OrderedDict(
        [
            ("Brak", ""),
            ("Czerwony", "#E53935"),
            ("Zielony", "#43A047"),
            ("Niebieski", "#1E88E5"),
            ("Żółty", "#FDD835"),
            ("Fioletowy", "#8E24AA"),
            ("Czarny", "#000000"),
        ]
    )

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._file_pair: FilePair | None = None
        self._init_ui()

    def _init_ui(self):
        """Inicjalizuje elementy interfejsu użytkownika kontrolek metadanych."""
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 5, 0, 0)  # Mały margines górny

        # --- Przycisk Ulubione ---
        self.favorite_button = QPushButton()
        self.favorite_button.setToolTip("Oznacz/Odznacz jako ulubione")
        self.favorite_button.clicked.connect(self._on_favorite_button_clicked)
        self.layout.addWidget(self.favorite_button)

        # --- Kontrolki gwiazdek ---
        self.stars_layout_widget = QWidget()
        self.stars_layout = QHBoxLayout(self.stars_layout_widget)
        self.stars_layout.setContentsMargins(0, 0, 0, 0)
        self.stars_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.star_buttons: list[QPushButton] = []
        for i in range(5):
            star_button = QPushButton("☆")
            star_button.setFlat(True)
            star_button.setFixedSize(25, 25)
            star_button.setStyleSheet(
                """
                QPushButton { border: none; font-size: 16px; }
                QPushButton:hover { color: #DAA520; }
                """
            )
            star_button.clicked.connect(
                lambda checked, idx=i: self._on_star_button_clicked(idx)
            )
            self.star_buttons.append(star_button)
            self.stars_layout.addWidget(star_button)
        self.layout.addWidget(self.stars_layout_widget)

        # --- ComboBox Kolorów ---
        self.color_tag_combo = QComboBox()
        self.color_tag_combo.setToolTip("Zmień tag kolorystyczny")
        for name, value in self.PREDEFINED_COLORS.items():
            self.color_tag_combo.addItem(name, userData=value)
        self.color_tag_combo.activated.connect(self._on_color_combo_activated)
        self.layout.addWidget(self.color_tag_combo)

    def set_file_pair(self, file_pair: FilePair | None):
        """Ustawia FilePair i aktualizuje stan kontrolek."""
        self._file_pair = file_pair
        if self._file_pair:
            self.update_favorite_display(self._file_pair.is_favorite_file())
            self.update_stars_display(self._file_pair.get_stars())
            self.update_color_tag_display(self._file_pair.get_color_tag())
        else:
            # Ustaw domyślne stany, jeśli nie ma FilePair
            self.update_favorite_display(False)
            self.update_stars_display(0)
            self.update_color_tag_display("")
            self.setEnabled(False)  # Wyłącz kontrolki, jeśli nie ma danych

    def update_favorite_display(self, is_favorite: bool):
        """Aktualizuje wygląd przycisku 'Ulubione'."""
        if is_favorite:
            self.favorite_button.setText("★")  # Krótszy tekst
            self.favorite_button.setStyleSheet(
                "background-color: #fffacd; color: #DAA520;"
            )
        else:
            self.favorite_button.setText("☆")  # Krótszy tekst
            self.favorite_button.setStyleSheet("")
        self.favorite_button.setToolTip(
            "Odznacz Ulubione" if is_favorite else "Oznacz Ulubione"
        )

    def _on_favorite_button_clicked(self):
        """Obsługuje kliknięcie przycisku ulubionych."""
        if not self._file_pair:
            return
        current_status = self._file_pair.is_favorite_file()
        new_status = not current_status
        # Aktualizacja UI jest celowo pomijana tutaj,
        # FileTileWidget zaktualizuje cały MetadataControlsWidget po zmianie FilePair
        self.favorite_status_changed.emit(new_status)
        logging.debug(
            f"MetadataControls: favorite_status_changed emitted: {new_status}"
        )

    def update_stars_display(self, star_count: int):
        """Aktualizuje wygląd przycisków gwiazdek."""
        for i, button in enumerate(self.star_buttons):
            button.setText("★" if i < star_count else "☆")

    def _on_star_button_clicked(self, star_index: int):
        """Obsługuje kliknięcie przycisku gwiazdki."""
        if not self._file_pair:
            return
        current_stars = self._file_pair.get_stars()
        new_star_count = star_index + 1
        if new_star_count == current_stars:
            new_star_count = 0  # Odznacz wszystko

        self.stars_value_changed.emit(new_star_count)
        logging.debug(
            f"MetadataControls: stars_value_changed emitted: {new_star_count}"
        )

    def update_color_tag_display(self, color_hex_string: str | None):
        """Aktualizuje QComboBox na podstawie tagu koloru."""
        color_to_select = color_hex_string if color_hex_string is not None else ""

        found_in_predefined = False
        for i in range(self.color_tag_combo.count()):
            if self.color_tag_combo.itemData(i) == color_to_select:
                if self.color_tag_combo.currentIndex() != i:
                    self.color_tag_combo.setCurrentIndex(i)
                found_in_predefined = True
                break

        if (
            not found_in_predefined
        ):  # Jeśli kolor nie jest predefiniowany (np. pusty lub niestandardowy)
            # Jeśli pusty, ustaw na "Brak"
            if not color_to_select:
                for i in range(self.color_tag_combo.count()):
                    if self.color_tag_combo.itemData(i) == "":  # Znajdź "Brak"
                        if self.color_tag_combo.currentIndex() != i:
                            self.color_tag_combo.setCurrentIndex(i)
                        break
            else:
                # Potencjalnie można dodać niestandardowy kolor do listy,
                # ale na razie ustawiamy na "Brak", jeśli nie pasuje.
                logging.warning(
                    f"Niestandardowy kolor '{color_to_select}' nie znaleziony w predefiniowanych. Ustawianie na 'Brak'."
                )
                for i in range(self.color_tag_combo.count()):
                    if self.color_tag_combo.itemData(i) == "":  # Znajdź "Brak"
                        if self.color_tag_combo.currentIndex() != i:
                            self.color_tag_combo.setCurrentIndex(i)
                        break

    def _on_color_combo_activated(self, index: int):
        """Obsługuje aktywację elementu w QComboBox dla kolorów."""
        if not self._file_pair:
            return
        tag_value = self.color_tag_combo.itemData(index)
        current_hex = self._file_pair.get_color_tag()

        if tag_value != current_hex:
            self.color_tag_value_changed.emit(tag_value)
            logging.debug(
                f"MetadataControls: color_tag_value_changed emitted: {tag_value}"
            )

    def setEnabled(self, enabled: bool):
        """Włącza lub wyłącza wszystkie kontrolki w widgecie."""
        super().setEnabled(enabled)
        self.favorite_button.setEnabled(enabled)
        for btn in self.star_buttons:
            btn.setEnabled(enabled)
        self.color_tag_combo.setEnabled(enabled)
        if not enabled:
            # Dodatkowo, można zresetować wygląd do stanu "pustego"
            self.update_favorite_display(False)
            self.update_stars_display(0)
            self.update_color_tag_display("")
