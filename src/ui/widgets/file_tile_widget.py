"""
Kafelek wyświetlający miniaturę podglądu, nazwę i rozmiar pliku archiwum.
"""

import logging
import os
from collections import OrderedDict

from PIL import Image, UnidentifiedImageError
from PyQt6.QtCore import QEvent, QMimeData, QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QDrag, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
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
from src.utils.image_utils import create_placeholder_pixmap, pillow_image_to_qpixmap


# Definicja Workera
class ThumbnailLoaderWorker(QObject):
    finished = pyqtSignal(QPixmap)

    def __init__(
        self, file_pair: FilePair, target_width: int, target_height: int, parent=None
    ):
        super().__init__(parent)
        self.file_pair = file_pair
        self.target_width = target_width
        self.target_height = target_height

    def run(self):
        preview_path = self.file_pair.get_preview_path()
        pixmap = None

        if not preview_path or not os.path.exists(preview_path):
            log_msg = (
                f"Asynch. worker: Plik podglądu nie istnieje: {preview_path}. "
                f"Tworzenie placeholdera."
            )
            logging.warning(log_msg)
            pixmap = create_placeholder_pixmap(
                self.target_width, self.target_height, text="Brak podglądu"
            )
        else:
            try:
                with Image.open(preview_path) as img:
                    thumbnail_img = img.copy()
                    thumbnail_img.thumbnail(
                        (self.target_width, self.target_height), Image.LANCZOS
                    )
                    pixmap = pillow_image_to_qpixmap(thumbnail_img)
                    if pixmap.isNull():
                        # Krótszy komunikat błędu
                        raise ValueError("Worker: Konwersja QPixmap dała pusty wynik")
            except FileNotFoundError:
                logging.error(f"Asynch. worker: Nie znaleziono pliku: {preview_path}")
                pixmap = create_placeholder_pixmap(
                    self.target_width, self.target_height, text="Brak pliku"
                )
            except UnidentifiedImageError:
                logging.error(f"Asynch. worker: Nieprawidłowy format: {preview_path}")
                pixmap = create_placeholder_pixmap(
                    self.target_width, self.target_height, text="Błąd formatu"
                )
            except Exception as e:
                log_msg = (
                    f"Asynch. worker: Błąd wczytywania podglądu " f"{preview_path}: {e}"
                )
                logging.error(log_msg)
                pixmap = create_placeholder_pixmap(
                    self.target_width, self.target_height, text="Błąd"
                )

        if pixmap is None:  # Ostateczny fallback
            pixmap = create_placeholder_pixmap(
                self.target_width, self.target_height, text="Błąd krytyczny"
            )

        self.finished.emit(pixmap)


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
    tile_context_menu_requested = pyqtSignal(
        FilePair, QWidget, object
    )  # file_pair, widget, event

    PREDEFINED_COLORS = OrderedDict(
        [
            ("Brak", ""),
            ("Czerwony", "#E53935"),  # Czerwony
            ("Zielony", "#43A047"),  # Zielony
            ("Niebieski", "#1E88E5"),  # Niebieski
            ("Żółty", "#FDD835"),  # Żółty
            ("Fioletowy", "#8E24AA"),  # Fioletowy
            ("Czarny", "#000000"),
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
        self.original_thumbnail: QPixmap | None = None

        # Wątek i worker do ładowania miniatur
        self.thumbnail_thread: QThread | None = None
        self.thumbnail_worker: ThumbnailLoaderWorker | None = None

        # Ustawienie podstawowych właściwości widgetu
        self.setObjectName("FileTileWidget")
        self.setStyleSheet(
            """
            #FileTileWidget {
                background-color: #f5f5f5;
                border: 3px solid #cccccc;
                border-radius: 5px;
                padding: 2px;
            }
            #FileTileWidget:hover {
                border: 3px solid #aaaaaa;
            }
        """
        )

        # Inicjalizacja UI
        self._init_ui()

        # Ustawienie danych tekstowych i metadanych (bez ładowania miniatury)
        self._update_static_data()

        # Asynchroniczne ładowanie miniatury
        self._load_thumbnail_async()

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

    def update_data(self, file_pair: FilePair):
        """
        Aktualizuje dane kafelka na podstawie obiektu FilePair.

        Args:
            file_pair (FilePair): Obiekt pary plików z nowymi danymi
        """
        self.file_pair = file_pair
        self._update_static_data()

    def _update_static_data(self):
        """Aktualizuje statyczne dane kafelka (nazwa, rozmiar, metadane)."""
        try:
            if self.file_pair:  # Upewnij się, że file_pair istnieje
                self.name_label.setText(self.file_pair.get_base_name())
                self.size_label.setText(self.file_pair.get_formatted_archive_size())
                self.update_favorite_status(self.file_pair.is_favorite_file())
                self.update_stars_display(self.file_pair.get_stars())
                self.update_color_tag_display(self.file_pair.get_color_tag())
            else:
                self.name_label.setText("Brak danych")
                self.size_label.setText("-")
                # Ustaw domyślne stany dla kontrolek, jeśli file_pair jest None
                self.update_favorite_status(False)
                self.update_stars_display(0)
                self.update_color_tag_display("")

        except Exception as e:
            logging.error(f"Błąd aktualizacji danych statycznych kafelka: {e}")
            # Fallback UI w przypadku błędu
            self.name_label.setText("Błąd danych")
            self.size_label.setText("Błąd")

    def _load_thumbnail_async(self):
        if self.thumbnail_thread and self.thumbnail_thread.isRunning():
            logging.debug(
                f"Ładowanie miniatury dla {self.file_pair.get_base_name()} już w toku."
            )
            return

        # Natychmiastowe ustawienie placeholdera
        placeholder = create_placeholder_pixmap(
            self.thumbnail_size[0], self.thumbnail_size[1], text="Ładowanie..."
        )
        self.thumbnail_label.setPixmap(placeholder)

        self.thumbnail_thread = QThread(self)
        self.thumbnail_worker = ThumbnailLoaderWorker(
            self.file_pair, self.thumbnail_size[0], self.thumbnail_size[1]
        )
        self.thumbnail_worker.moveToThread(self.thumbnail_thread)

        # Połączenie sygnałów
        self.thumbnail_worker.finished.connect(self._on_thumbnail_loaded)
        self.thumbnail_thread.started.connect(self.thumbnail_worker.run)

        # Sprzątanie: Worker emituje finished -> Thread się zatrzymuje (quit)
        self.thumbnail_worker.finished.connect(self.thumbnail_thread.quit)
        # Thread emituje finished -> Worker i Thread są usuwane
        self.thumbnail_thread.finished.connect(self.thumbnail_worker.deleteLater)
        self.thumbnail_thread.finished.connect(self.thumbnail_thread.deleteLater)
        # Rozłącz sygnały, aby uniknąć podwójnego wywołania slotów,
        # jeśli _load_thumbnail_async jest wywoływane wielokrotnie
        # (chociaż obecna logika na to nie pozwala, jeśli wątek działa).
        # To bardziej zabezpieczenie na przyszłość.
        self.thumbnail_thread.finished.connect(
            lambda: setattr(self, "thumbnail_worker", None)
        )
        self.thumbnail_thread.finished.connect(
            lambda: setattr(self, "thumbnail_thread", None)
        )

        self.thumbnail_thread.start()
        logging.debug(
            f"Rozpoczęto asynch. ładowanie dla {self.file_pair.get_base_name()}"
        )

    def _on_thumbnail_loaded(self, pixmap: QPixmap):
        log_msg = (
            f"Miniatura załadowana dla {self.file_pair.get_base_name()}, "
            f"isNull: {pixmap.isNull()}"
        )
        logging.debug(log_msg)
        self.original_thumbnail = pixmap
        self.set_thumbnail_size(self.thumbnail_size)

        # Atrybuty thumbnail_worker i thumbnail_thread zostaną ustawione na None przez
        # połączenia z self.thumbnail_thread.finished.

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
        else:  # Jeśli nie ma miniatury, regenerujemy placeholder
            try:
                width, height = size_wh
                new_thumbnail = self.file_pair.load_preview_thumbnail(width, height)
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

        if tag_value != current_hex:
            self.file_pair.set_color_tag(tag_value)
            self.update_color_tag_display(tag_value)
            self.color_tag_changed.emit(self.file_pair, tag_value)
            fp_name = self.file_pair.get_base_name()[:15]
            logging.debug(f"Color: {fp_name}.. -> {tag_value}")

    def update_color_tag_display(self, color_hex_string: str):
        """Aktualizuje QComboBox i styl miniaturki na podstawie tagu koloru."""
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
            pass
        elif not color_hex_string:  # "Brak" koloru
            for i in range(self.color_tag_combo.count()):
                if self.color_tag_combo.itemData(i) == "":  # Znajdź "Brak"
                    if self.color_tag_combo.currentIndex() != i:
                        self.color_tag_combo.setCurrentIndex(i)
                    break

        # 2. Ustawienie stylu tylko na miniaturce
        if color_hex_string:
            border_color = color_hex_string
            self.thumbnail_label.setStyleSheet(
                f"""
                background-color: {border_color};
                border: 6px solid {border_color};
                border-radius: 7px;
                padding: 0px;
            """
            )
            logging.debug(f"Ustawiono ramkę miniaturki: {border_color}")
        else:
            self.thumbnail_label.setStyleSheet(
                f"""
                border: 0;
                border-radius: 7px;
                padding: 2px;
            """
            )
            logging.debug("Usunięto ramkę miniaturki (brak koloru)")

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

    # MODIFICATION: Add drag support
    def mousePressEvent(self, event):
        """
        Obsługuje zdarzenie naciśnięcia przycisku myszy.
        Przygotowuje możliwe rozpoczęcie operacji drag & drop.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # Zapisz pozycję początkową dla porównania przy mouseMoveEvent
            self.drag_start_position = event.position()

        # Wywołaj domyślną implementację, aby zachować standardową funkcjonalność
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Obsługuje zdarzenie ruchu myszy.
        Inicjuje operację drag & drop jeśli spełnione są warunki.
        """
        # Sprawdź czy lewy przycisk myszy jest wciśnięty
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        # Sprawdź, czy przesunięcie jest wystarczająco duże, aby rozpocząć przeciąganie
        if not hasattr(self, "drag_start_position"):
            return

        # Oblicz odległość od początku kliknięcia
        # Jeśli jest większa niż minimalny dystans, rozpocznij drag
        distance = (event.position() - self.drag_start_position).manhattanLength()
        if distance < QApplication.startDragDistance():
            return

        # Stwórz i skonfiguruj obiekt do przeciągania
        drag = QDrag(self)
        mime_data = QMimeData()

        # Serializuj identyfikator obiektu FilePair do formy, która może być przekazana
        file_id = (
            f"{self.file_pair.get_archive_path()}|{self.file_pair.get_preview_path()}"
        )
