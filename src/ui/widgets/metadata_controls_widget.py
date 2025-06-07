"""
Widget zawierający kontrolki do zarządzania metadanymi pliku,
takimi jak checkbox do selekcji, ocena w gwiazdkach i tag kolorystyczny.
"""

import logging
from collections import OrderedDict

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from src.models.file_pair import FilePair


class MetadataControlsWidget(QWidget):
    """
    Widget grupujący kontrolki metadanych: Checkbox selekcji, Gwiazdki, Kolor.
    Emituje sygnały po interakcji użytkownika.
    """

    # Sygnały emitowane przez ten widget po zmianie wartości przez użytkownika
    # Nie zawierają FilePair, tylko nową wartość.
    # FileTileWidget będzie odpowiedzialny za aktualizację FilePair.
    tile_selected_changed = pyqtSignal(bool)  # True if selected, False otherwise
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

        # --- Checkbox do selekcji kafli ---
        self.selection_checkbox = QCheckBox()
        self.selection_checkbox.setToolTip(
            "Zaznacz/Odznacz kafelek do operacji grupowych"
        )

        # ═══════════════════════════════════════════════════════════════
        # STYLOWANIE CHECKBOXA SELEKCJI - EDYTUJ TUTAJ KOLORY
        # ═══════════════════════════════════════════════════════════════
        self.selection_checkbox.setStyleSheet(
            """
            QCheckBox {
                /* ▼▼▼ CHECKBOX SELEKCJI - NORMALNY STAN ▼▼▼ */
                border: none;                           /* Bez obramowania */
                color: #666666;                         /* SZARY kolor - zmień na #CCCCCC dla ciemnego tła */
                background-color: transparent;          /* Przezroczyste tło */
                spacing: 0px;                           /* Brak odstępu między checkboxem a tekstem */
            }
            QCheckBox::indicator {
                /* ▼▼▼ WSKAŹNIK CHECKBOXA ▼▼▼ */
                width: 16px;                           /* Szerokość checkboxa */
                height: 16px;                          /* Wysokość checkboxa */
                background-color: #2A2A2A;             /* Ciemne tło - zmień na #FFFFFF dla jasnego */
                border: 1px solid #666666;             /* Szare obramowanie */
                border-radius: 3px;                    /* Zaokrąglone rogi */
            }
            QCheckBox::indicator:hover {
                /* ▼▼▼ HOVER NA CHECKBOXIE ▼▼▼ */
                border: 1px solid #4a90e2;            /* NIEBIESKIE obramowanie hover */
                background-color: #3A3A3A;            /* Jaśniejsze tło hover */
            }
            QCheckBox::indicator:checked {
                /* ▼▼▼ ZAZNACZONY CHECKBOX ▼▼▼ */
                background-color: #4a90e2;            /* NIEBIESKI kolor zaznaczenia */
                border: 1px solid #4a90e2;            /* NIEBIESKI border zaznaczenia */
            }
            QCheckBox::indicator:checked:hover {
                /* ▼▼▼ ZAZNACZONY CHECKBOX HOVER ▼▼▼ */
                background-color: #5ba0f2;            /* Jaśniejszy niebieski hover */
            }
            """
        )
        self.selection_checkbox.stateChanged.connect(
            self._on_selection_checkbox_changed
        )
        self.layout.addWidget(self.selection_checkbox)

        # --- Kontrolki gwiazdek ---
        self.stars_layout_widget = QWidget()
        self.stars_layout = QHBoxLayout(self.stars_layout_widget)
        self.stars_layout.setContentsMargins(0, 0, 0, 0)
        self.stars_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.star_buttons: list[QPushButton] = []
        for i in range(5):
            star_button = QPushButton("☆")
            star_button.setFlat(True)
            star_button.setFixedSize(
                25, 25
            )  # ═══════════════════════════════════════════════════════════════
            # STYLOWANIE PRZYCISKÓW GWIAZDEK - EDYTUJ TUTAJ KOLORY
            # ═══════════════════════════════════════════════════════════════
            star_button.setStyleSheet(
                """
                QPushButton { 
                    /* ▼▼▼ PRZYCISKI GWIAZDEK - NORMALNY STAN ▼▼▼ */
                    border: none;                       /* Bez obramowania */
                    font-size: 16px;                   /* Rozmiar ikony gwiazdki */
                    color: #666666;                     /* SZARY kolor - zmień na #CCCCCC dla ciemnego tła */
                    background-color: transparent;      /* Przezroczyste tło */
                }
                QPushButton:hover { 
                    /* ▼▼▼ HOVER NA GWIAZDKACH ▼▼▼ */
                    color: #DAA520;                     /* ZŁOTY hover - zmień według potrzeb */
                }
                """
            )
            star_button.clicked.connect(
                lambda checked, idx=i: self._on_star_button_clicked(idx)
            )
            self.star_buttons.append(star_button)
            self.stars_layout.addWidget(star_button)
        self.layout.addWidget(self.stars_layout_widget)  # --- ComboBox Kolorów ---
        self.color_tag_combo = QComboBox()
        self.color_tag_combo.setToolTip(
            "Zmień tag kolorystyczny"
        )  # ═══════════════════════════════════════════════════════════════
        # STYLOWANIE COMBOBOX KOLORÓW - EDYTUJ TUTAJ WYGLĄD LISTY
        # ═══════════════════════════════════════════════════════════════
        self.color_tag_combo.setStyleSheet(
            """
            QComboBox {
                /* ▼▼▼ LISTA ROZWIJANA KOLORÓW - NORMALNY STAN ▼▼▼ */
                color: #FFFFFF;                         /* CZARNY tekst - zmień na #FFFFFF dla ciemnego tła */
                background-color: #1E1E1E;              /* JASNOSZARE tło - zmień na #2A2A2A dla ciemnego */
                border: 1px solid #000000;              /* Szare obramowanie */
                border-radius: 3px;                     /* Zaokrąglone rogi */
                padding: 2px 18px 2px 3px;              /* Odstępy wewnętrzne */
                min-width: 60px;                        /* Minimalna szerokość */
            }
            QComboBox:hover {
                /* ▼▼▼ HOVER NA LIŚCIE KOLORÓW ▼▼▼ */
                border: 1px solid #4a90e2;              /* NIEBIESKIE obramowanie hover */
            }
            QComboBox::drop-down {
                /* ▼▼▼ PRZYCISK ROZWIJANIA LISTY ▼▼▼ */
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;                            /* Szerokość przycisku strzałki */
                border-left-width: 1px;
                border-left-color: #CCCCCC;             /* Kolor separatora */
                border-left-style: solid;
                border-top-right-radius: 3px;                border-bottom-right-radius: 3px;
            }
            """
        )
        for name, value in self.PREDEFINED_COLORS.items():
            self.color_tag_combo.addItem(name, userData=value)
        self.color_tag_combo.activated.connect(self._on_color_combo_activated)
        self.layout.addWidget(self.color_tag_combo)

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
        self.selection_checkbox.setEnabled(enabled)
        for btn in self.star_buttons:
            btn.setEnabled(enabled)
        self.color_tag_combo.setEnabled(enabled)
        if not enabled:
            # Dodatkowo, można zresetować wygląd do stanu "pustego"
            self.update_selection_display(False)
            self.update_stars_display(0)
            self.update_color_tag_display("")
