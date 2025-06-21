"""
Widget zawierający kontrolki do zarządzania metadanymi pliku,
takimi jak checkbox do selekcji, ocena w gwiazdkach i tag kolorystyczny.
"""

import logging
from collections import OrderedDict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QPushButton, QWidget

from src.models.file_pair import FilePair


class MetadataControlsWidget(QWidget):
    """
    Widget grupujący kontrolki metadanych: Checkbox selekcji, Gwiazdki, Kolor.
    Emituje sygnały po interakcji użytkownika.
    """

    # Sygnały emitowane przez ten widget po zmianie wartości przez użytkownika
    # Nie zawierają FilePair, tylko nową wartość.
    # FileTileWidget będzie odpowiedzialny za aktualizację FilePair.
    tile_selected_changed = pyqtSignal(bool)  # True/False selection state
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
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)  # Minimalne marginesy
        layout.setSpacing(4)  # Małe odstępy między elementami

        # --- Checkbox do selekcji kafli ---
        self.selection_checkbox = QCheckBox()
        self.selection_checkbox.setToolTip(
            "Zaznacz/Odznacz kafelek do operacji grupowych"
        )

        # Stylowanie checkboxa - ciemny schemat, kompaktowy
        self.selection_checkbox.setStyleSheet(
            """
            QCheckBox {
                border: none;
                color: #CCCCCC;
                background-color: transparent;
                spacing: 0px;
                max-width: 14px;
                max-height: 14px;
            }
            QCheckBox::indicator {
                width: 12px;
                height: 12px;
                background-color: #3A3A3A;
                border: 1px solid #666666;
                border-radius: 2px;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #5A9FD4;
                background-color: #4A4A4A;
            }
            QCheckBox::indicator:checked {
                background-color: #5A9FD4;
                border: 1px solid #5A9FD4;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #6AAFF4;
            }
            """
        )
        self.selection_checkbox.stateChanged.connect(
            self._on_selection_checkbox_changed
        )
        layout.addWidget(self.selection_checkbox)

        # --- Kontrolki gwiazdek ---
        self.stars_layout_widget = QWidget()
        self.stars_layout = QHBoxLayout(self.stars_layout_widget)
        self.stars_layout.setContentsMargins(0, 0, 0, 0)
        self.stars_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.star_buttons: list[QPushButton] = []
        for i in range(5):
            star_button = QPushButton("☆")
            star_button.setFlat(True)
            star_button.setFixedSize(16, 16)  # Mniejsze gwiazdki
            # Stylowanie gwiazdek - ciemny schemat, kompaktowe
            star_button.setStyleSheet(
                """
                QPushButton { 
                    border: none;
                    font-size: 14px;
                    color: #888888;
                    background-color: transparent;
                    padding: 0px;
                    margin: 0px;
                }
                QPushButton:hover { 
                    color: #FFD700;
                }
                """
            )
            star_button.clicked.connect(
                lambda checked, idx=i: self._on_star_button_clicked(idx)
            )
            self.star_buttons.append(star_button)
            self.stars_layout.addWidget(star_button)
        layout.addWidget(self.stars_layout_widget)

        # --- ComboBox Kolorów ---
        self.color_tag_combo = QComboBox()
        self.color_tag_combo.setToolTip("Zmień tag kolorystyczny")
        self.color_tag_combo.setFixedHeight(20)  # Kompaktowa wysokość
        # Stylowanie combobox - ciemny schemat, kompaktowy
        self.color_tag_combo.setStyleSheet(
            """
            QComboBox {
                color: #CCCCCC;
                background-color: #3A3A3A;
                border: 1px solid #666666;
                border-radius: 2px;
                padding: 1px 16px 1px 2px;
                min-width: 50px;
                max-height: 18px;
            }
            QComboBox:hover {
                border: 1px solid #5A9FD4;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 14px;
                border-left-width: 1px;
                border-left-color: #666666;
                border-left-style: solid;
                border-top-right-radius: 2px;
                border-bottom-right-radius: 2px;
                background-color: #4A4A4A;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 4px solid #CCCCCC;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #3A3A3A;
                color: #CCCCCC;
                border: 1px solid #666666;
                selection-background-color: #5A9FD4;
            }
            """
        )
        for name, value in self.PREDEFINED_COLORS.items():
            self.color_tag_combo.addItem(name, userData=value)
        self.color_tag_combo.activated.connect(self._on_color_combo_activated)
        layout.addWidget(self.color_tag_combo)

    def set_file_pair(self, file_pair: FilePair | None):
        """Ustawia FilePair i aktualizuje stan kontrolek."""
        self._file_pair = file_pair
        if self._file_pair:
            self.update_selection_display(False)  # Domyślnie nie zaznaczony
            self.update_stars_display(self._file_pair.get_stars())
            self.update_color_tag_display(self._file_pair.get_color_tag())
        else:
            # Ustaw domyślne stany, jeśli nie ma FilePair
            self.update_selection_display(False)
            self.update_stars_display(0)
            self.update_color_tag_display("")
            self.setEnabled(False)  # Wyłącz kontrolki, jeśli nie ma danych

    def update_selection_display(self, is_selected: bool):
        """Aktualizuje stan checkboxa selekcji."""
        self.selection_checkbox.setChecked(is_selected)
        self.selection_checkbox.setToolTip(
            "Odznacz kafelek"
            if is_selected
            else "Zaznacz kafelek do operacji grupowych"
        )

    def _on_selection_checkbox_changed(self, state: int):
        """Obsługuje zmianę stanu checkboxa selekcji."""
        is_selected = state == Qt.CheckState.Checked.value
        # Emituj sygnał zmiany selekcji
        self.tile_selected_changed.emit(is_selected)
        logging.debug(f"MetadataControls: tile_selected_changed emitted: {is_selected}")

    def update_stars_display(self, star_count: int):
        """Aktualizuje wygląd przycisków gwiazdek."""
        for i, button in enumerate(self.star_buttons):
            button.setText("★" if i < star_count else "☆")

    def _on_star_button_clicked(self, star_index: int):
        """Obsługuje kliknięcie przycisku gwiazdki."""
        if not self._file_pair:
            logging.warning("Brak file_pair - nie mogę zmienić gwiazdek")
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

        if not found_in_predefined:
            # Jeśli kolor nie jest predefiniowany
            if not color_to_select:
                for i in range(self.color_tag_combo.count()):
                    if self.color_tag_combo.itemData(i) == "":
                        if self.color_tag_combo.currentIndex() != i:
                            self.color_tag_combo.setCurrentIndex(i)
                        break
            else:
                # Potencjalnie można dodać niestandardowy kolor do listy,
                # ale na razie ustawiamy na "Brak", jeśli nie pasuje.
                logging.warning(
                    f"Niestandardowy kolor '{color_to_select}' nie znaleziony "
                    f"w predefiniowanych. Ustawianie na 'Brak'."
                )
                for i in range(self.color_tag_combo.count()):
                    if self.color_tag_combo.itemData(i) == "":
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
        self.selection_checkbox.setEnabled(enabled)
        for btn in self.star_buttons:
            btn.setEnabled(enabled)
        self.color_tag_combo.setEnabled(enabled)
        if not enabled:
            # Dodatkowo, można zresetować wygląd do stanu "pustego"
            self.update_selection_display(False)
            self.update_stars_display(0)
            self.update_color_tag_display("")
