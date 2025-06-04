"""
Kafelek wyświetlający miniaturę podglądu, nazwę i rozmiar pliku archiwum.
"""

import logging
from collections import OrderedDict

from PyQt6.QtCore import QEvent, Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFrame,
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
    stars_changed = pyqtSignal(FilePair, int)  # file_pair, new_star_count
    color_tag_changed = pyqtSignal(FilePair, str)  # file_pair, new_color_tag_hex

    PREDEFINED_COLORS = OrderedDict(
        [
            ("Brak", ""),
            ("Czerwony", "#E53935"),  # Czerwony
            ("Zielony", "#43A047"),  # Zielony
            ("Niebieski", "#1E88E5"),  # Niebieski
            ("Żółty", "#FDD835"),  # Żółty
            ("Fioletowy", "#8E24AA"),  # Fioletowy
            ("Czarny", "#000000"),
            ("Niestandardowy...", "custom"),  # Otworzy QColorDialog
        ]
    )

    def __init__(
        self, file_pair: FilePair, default_thumbnail_size=(150, 150), parent=None
    ):
        """
        Inicjalizuje widget kafelka dla pary plików.

        Args:
            file_pair (FilePair): Obiekt pary plików.
            default_thumbnail_size (tuple): Rozmiar miniatury (szer., wys.)
                                          w px.
            parent (QWidget, optional): Widget nadrzędny.
        """
        super().__init__(parent)
        self.file_pair = file_pair
        self.thumbnail_size = default_thumbnail_size

        # Oryg. QPixmap dla wydajnego skalowania
        self.original_thumbnail = None
        # Przechowywanie bazowego stylesheetu
        self.base_style_sheet = (  # Przeniesione do wielu linii
            "FileTileWidget {\n"
            "    background-color: #f5f5f5;\n"
            "    border: 1px solid #cccccc;\n"
            "    border-radius: 5px;\n"
            "}\n"
            "FileTileWidget:hover {\n"
            "    border: 1px solid #aaaaaa;\n"
            "}\n"
        )

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

        # --- Pasek wskaźnika koloru ---
        self.color_indicator_bar = QFrame()
        self.color_indicator_bar.setFixedHeight(5)  # Stała wysokość paska
        self.color_indicator_bar.setAutoFillBackground(True)  # Aby tło było widoczne
        # Początkowo ukryty/transparentny, aż kolor zostanie ustawiony
        self.color_indicator_bar.setStyleSheet("background-color: transparent;")
        self.layout.addWidget(self.color_indicator_bar)  # Dodajemy na górze
        # --- Koniec paska wskaźnika koloru ---

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
        self.name_label.setStyleSheet(  # Przeniesione do wielu linii
            "QLabel {\n"
            "    font-weight: bold;\n"
            "}\n"
            "QLabel:hover {\n"
            "    color: #0078D4;\n"
            "    text-decoration: underline;\n"
            "}\n"
        )

        # Label na rozmiar pliku
        self.size_label = QLabel()
        self.size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- Kontrolki gwiazdek ---
        self.stars_layout_widget = QWidget()  # Kontener dla layoutu gwiazdek
        self.stars_layout = QHBoxLayout(self.stars_layout_widget)
        self.stars_layout.setContentsMargins(0, 0, 0, 0)
        self.stars_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.star_buttons: list[QPushButton] = []
        for i in range(5):
            star_button = QPushButton("☆")
            star_button.setFlat(True)  # Mniej "inwazyjny" wygląd
            star_button.setFixedSize(25, 25)  # Mały rozmiar dla gwiazdek
            star_button.setStyleSheet(
                """
                QPushButton {
                    border: none; 
                    font-size: 16px;
                }
                QPushButton:hover {
                    color: #DAA520; 
                }
                """
            )
            # Używamy lambda, aby przekazać indeks gwiazdki do slotu
            star_button.clicked.connect(
                lambda checked, idx=i: self._on_star_button_clicked(idx)
            )
            self.star_buttons.append(star_button)
            self.stars_layout.addWidget(star_button)
        # --- Koniec kontrolek gwiazdek ---

        # Dodanie widgetów do głównego layoutu
        self.layout.addWidget(self.thumbnail_container)
        self.layout.addWidget(self.name_label)
        self.layout.addWidget(self.size_label)
        self.layout.addWidget(self.stars_layout_widget)  # Dodajemy kontener gwiazdek

        # --- Kontrolki dolne (Ulubione, Kolor) ---
        self.bottom_controls_widget = QWidget()
        self.bottom_controls_layout = QHBoxLayout(self.bottom_controls_widget)
        self.bottom_controls_layout.setContentsMargins(
            0, 5, 0, 0
        )  # Mały margines górny

        self.favorite_button = QPushButton()  # Tekst ustawiany w update_favorite_status
        self.favorite_button.clicked.connect(self._emit_favorite_toggled_signal)
        self.bottom_controls_layout.addWidget(self.favorite_button)

        self.color_tag_combo = QComboBox()
        self.color_tag_combo.setToolTip("Zmień tag kolorystyczny")
        for name, value in self.PREDEFINED_COLORS.items():
            self.color_tag_combo.addItem(name, userData=value)

        # Zapisujemy indeks pozycji "Niestandardowy..." do późniejszego użytku
        self.custom_color_combo_index = -1
        for i in range(self.color_tag_combo.count()):
            if self.color_tag_combo.itemData(i) == "custom":
                self.custom_color_combo_index = i
                break

        self.color_tag_combo.activated.connect(self._on_color_combo_activated)
        self.bottom_controls_layout.addWidget(self.color_tag_combo)

        self.layout.addWidget(self.bottom_controls_widget)
        # --- Koniec kontrolek dolnych ---

        # Ustawiamy preferowany rozmiar całego widgetu
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # Dodatkowa wysokość dla nazwy, rozmiaru, gwiazdek i przycisku ulubione
        # + wysokość paska koloru
        additional_height = 120 + self.color_indicator_bar.height()
        min_height = self.thumbnail_size[1] + additional_height
        self.setMinimumSize(self.thumbnail_size[0] + 20, min_height)

        # Ustawienie tła i ramki dla wyróżnienia kafelków
        self.setStyleSheet(self.base_style_sheet)

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
            # MODIFICATION: Update stars display on data update
            self.update_stars_display(self.file_pair.get_stars())
            # MODIFICATION: Update color tag display on data update
            self.update_color_tag_display(self.file_pair.get_color_tag())

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
        # MODIFICATION: Adjust minimum size for the new button and stars
        # Dodatkowa wysokość dla nazwy, rozmiaru, gwiazdek i przycisku ulubione
        # + wysokość paska koloru
        additional_height_scaled = 120 + self.color_indicator_bar.height()
        min_height = size_wh[1] + additional_height_scaled
        self.setMinimumSize(size_wh[0] + 20, min_height)

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
            self.favorite_button.setStyleSheet("")  # Domyślny styl

    # MODIFICATION: New method to emit favorite_toggled signal
    def _emit_favorite_toggled_signal(self):
        """Emituje sygnał zmiany statusu ulubionego."""
        self.favorite_toggled.emit(self.file_pair)

    # MODIFICATION: New methods for stars
    def _on_star_button_clicked(self, star_index: int):
        """Obsługuje kliknięcie przycisku gwiazdki."""
        current_stars = self.file_pair.get_stars()
        new_star_count = star_index + 1

        # Kliknięcie tej samej gwiazdki (najwyższej zaznaczonej) zeruje ocenę.
        # W przeciwnym razie ustawia nową liczbę gwiazdek.
        if new_star_count == current_stars:
            new_star_count = 0  # Odznacz wszystko

        self.file_pair.set_stars(new_star_count)
        self.update_stars_display(new_star_count)
        self.stars_changed.emit(self.file_pair, new_star_count)
        logging.debug(
            f"Stars: {self.file_pair.get_base_name()[:20]} -> {new_star_count}"
        )

    def update_stars_display(self, star_count: int):
        """Aktualizuje wygląd przycisków gwiazdek."""
        for i, button in enumerate(self.star_buttons):
            if i < star_count:
                button.setText("★")  # Wypełniona gwiazdka
            else:
                button.setText("☆")  # Pusta gwiazdka

    # MODIFICATION: New methods for color tagging
    def _on_color_combo_activated(self, index: int):
        """Obsługuje aktywację elementu w QComboBox dla kolorów."""
        tag_value = self.color_tag_combo.itemData(index)
        current_hex = self.file_pair.get_color_tag()

        if tag_value == "custom":
            initial_color = QColor(current_hex) if current_hex else Qt.GlobalColor.white
            # Wywołanie QColorDialog w wielu liniach dla czytelności
            color = QColorDialog.getColor(
                initial_color, self, "Wybierz kolor niestandardowy"
            )

            if color.isValid():
                new_color_hex = color.name()  # Format #RRGGBB
                if new_color_hex != current_hex:
                    self.file_pair.set_color_tag(new_color_hex)
                    # Aktualizuj UI natychmiast
                    self.update_color_tag_display(new_color_hex)
                    self.color_tag_changed.emit(self.file_pair, new_color_hex)
                    fp_name = self.file_pair.get_base_name()[:15]
                    logging.debug(f"Custom color: {fp_name}.. -> {new_color_hex}")
            else:  # Anulowano QColorDialog, przywróć poprzednią wartość
                self.update_color_tag_display(current_hex)
                return
        else:  # Predefiniowany kolor (w tym "Brak" == "")
            new_color_hex = tag_value
            if new_color_hex != current_hex:
                self.file_pair.set_color_tag(new_color_hex)
                self.update_color_tag_display(new_color_hex)
                self.color_tag_changed.emit(self.file_pair, new_color_hex)
                fp_name = self.file_pair.get_base_name()[:15]
                logging.debug(f"Predef color: {fp_name}.. -> {new_color_hex}")

    def update_color_tag_display(self, color_hex_string: str):
        """Aktualizuje QComboBox i styl kafelka na podstawie tagu koloru."""
        logging.debug(
            f"Aktualizacja UI koloru dla {self.file_pair.get_base_name()[:20]} z kolorem '{color_hex_string}'"
        )
        # 1. Aktualizacja QComboBox
        found_in_predefined = False
        for i in range(self.color_tag_combo.count()):
            if self.color_tag_combo.itemData(i) == color_hex_string:
                if self.color_tag_combo.currentIndex() != i:
                    self.color_tag_combo.setCurrentIndex(i)
                found_in_predefined = True
                break

        if not found_in_predefined and color_hex_string:  # Niestandardowy kolor
            if self.custom_color_combo_index != -1:
                if self.color_tag_combo.currentIndex() != self.custom_color_combo_index:
                    self.color_tag_combo.setCurrentIndex(self.custom_color_combo_index)
            # Usunięto komentarz o zmianie tekstu "Niestandardowy..."
            else:  # Fallback, jeśli "Niestandardowy..." nie istnieje
                pass
        elif not color_hex_string:  # "Brak" koloru
            for i in range(self.color_tag_combo.count()):
                if self.color_tag_combo.itemData(i) == "":  # Znajdź "Brak"
                    if self.color_tag_combo.currentIndex() != i:
                        self.color_tag_combo.setCurrentIndex(i)
                    break

        # 2. Aktualizacja paska wskaźnika koloru
        if color_hex_string:
            self.color_indicator_bar.setStyleSheet(
                f"background-color: {color_hex_string};"
            )
            self.color_indicator_bar.setVisible(True)
        else:
            self.color_indicator_bar.setStyleSheet("background-color: transparent;")
            # Ukrywamy pasek, jeśli nie ma koloru (setVisible(False)).
            # Można też zostawić transparentny i widoczny.
            self.color_indicator_bar.setVisible(False)

        # 3. Ustawienie bazowego stylu dla całego widgetu (bez dynamicznej zmiany ramki)
        self.setStyleSheet(self.base_style_sheet)

    # MODIFICATION: New method to handle clicks on labels (event filter)
    def eventFilter(self, obj, event):
        """Obsługuje kliknięcia na etykietach miniatury i nazwy."""
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                if obj == self.thumbnail_label:
                    fp_name = self.file_pair.get_base_name()[:20]
                    logging.debug(f"Thumb: {fp_name}..")
                    self.preview_image_requested.emit(self.file_pair)
                    return True
                elif obj == self.name_label:
                    fp_name = self.file_pair.get_base_name()[:20]
                    logging.debug(f"Name: {fp_name}..")
                    self.archive_open_requested.emit(self.file_pair)
                    return True
        return super().eventFilter(obj, event)
