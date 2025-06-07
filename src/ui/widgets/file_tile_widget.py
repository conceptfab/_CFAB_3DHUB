"""
Kafelek wyświetlający miniaturę podglądu, nazwę i rozmiar pliku archiwum.
"""

# Standard library imports
import logging
import os
import uuid  # Dla unikalnych ID workera
from collections import OrderedDict  # Dodaj OrderedDict

# Third-party imports
from PIL import Image, UnidentifiedImageError
from PyQt6.QtCore import QObject  # Dodaj QObject, QEvent
from PyQt6.QtCore import QEvent, QMimeData, QSize, Qt, QThread, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QDesktopServices, QDrag, QPixmap
from PyQt6.QtWidgets import QHBoxLayout  # Dodaj QHBoxLayout
from PyQt6.QtWidgets import QVBoxLayout  # Upewnij się, że QVBoxLayout jest tutaj
from PyQt6.QtWidgets import QApplication, QFrame, QLabel, QMenu, QSizePolicy, QWidget

from src.models.file_pair import FilePair
from src.ui.widgets.metadata_controls_widget import (
    MetadataControlsWidget,
)  # NOWY IMPORT
from src.ui.widgets.thumbnail_cache import ThumbnailCache
from src.utils.image_utils import (
    create_placeholder_pixmap,
    crop_to_square,
    pillow_image_to_qpixmap,
)


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
                    # Użyj crop_to_square zamiast thumbnail dla kwadratowych miniatur
                    # Ponieważ target_width == target_height (kafelki są kwadratowe)
                    thumbnail_img = crop_to_square(img, self.target_width)
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
    tile_selected = pyqtSignal(FilePair, bool)  # file_pair, selected_state
    stars_changed = pyqtSignal(FilePair, int)  # file_pair, new_star_count
    color_tag_changed = pyqtSignal(FilePair, str)  # file_pair, new_color_tag_hex
    tile_context_menu_requested = pyqtSignal(
        FilePair, QWidget, object
    )  # file_pair, widget, event
    file_pair_updated = pyqtSignal(FilePair)  # sygnał do aktualizacji danych file_pair

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
            default_thumbnail_size (tuple): Rozmiar całego kafelka (szer., wys.)
                                          w px.
            parent (QWidget, optional): Widget nadrzędny.
        """
        super().__init__(parent)
        self.file_pair = file_pair
        self._file_pair = file_pair
        self.thumbnail_size = default_thumbnail_size
        self.original_thumbnail: QPixmap | None = None

        # Wątek i worker do ładowania miniatur
        self.thumbnail_thread: QThread | None = None
        self.thumbnail_worker: ThumbnailLoaderWorker | None = None
        self._current_worker_id = 0

        # Nowe flagi i zmienne do obsługi kliknięć i przeciągania
        self.press_pos = None
        self.maybe_drag = False
        self.drag_active = False

        # Ustawienie podstawowych właściwości widgetu
        self.setObjectName("FileTileWidget")

        # ═══════════════════════════════════════════════════════════════
        # SEKCJA STYLOWANIA KAFELKÓW - EDYTUJ TUTAJ KOLORY I WYGLĄD
        # ═══════════════════════════════════════════════════════════════
        super_aggressive_stylesheet = """
            /* ▼▼▼ GŁÓWNY WYGLĄD KAFELKA ▼▼▼ */
            FileTileWidget {
                /* KOLOR TŁA KAFELKA - zmień na jasny/ciemny według potrzeb */
                background-color: transparent; !important;     /* BIAŁY - zmień na #1E1E1E dla ciemnego */

                /* OBRAMOWANIE KAFELKA */
                border: 1px solid #1E1E1E  !important;     /* Szare obramowanie */
                border-radius: 4px !important;            /* Zaokrąglone rogi */

                /* ODSTĘPY WEWNĘTRZNE I ZEWNĘTRZNE */
                padding: 2px !important;                  /* Wewnętrzne odstępy */
                margin: 2px !important;                   /* Zewnętrzne odstępy */
            }

            /* ▼▼▼ HOVER - NAJECHANIE MYSZĄ ▼▼▼ */
            FileTileWidget:hover {
                /* KOLOR TŁA PO NAJECHANIU */
                background-color: #2A2A2A !important;     /* Ciemnoszary hover - zmień na #F0F0F0 dla jasnego */

                /* OBRAMOWANIE PO NAJECHANIU */
                border: 3px solid #4a90e2 !important;     /* Niebieskie obramowanie hover */
            }

            /* ▼▼▼ ALTERNATYWNY SELEKTOR - BACKUP ▼▼▼ */
            QWidget#FileTileWidget {
                /* Te same style co wyżej - dla pewności że zadziałają */
                background-color: transparent; !important;     /* CIEMNY - zmień na #FFFFFF dla jasnego */
                border: 1px solid #1E1E1E !important;     /* Subtelne obramowanie - takie samo jak główny selektor */
                border-radius: 4px !important;            /* Zaokrąglone rogi - takie samo jak główny selektor */
                padding: 2px !important;                  /* Wewnętrzne odstępy */
                margin: 2px !important;                   /* Zewnętrzne odstępy */
            }
            QWidget#FileTileWidget:hover {
                background-color: transparent; !important;     /* Ciemnoszary hover - zmień na #F0F0F0 dla jasnego */
                border: 3px solid #4a90e2 !important;     /* Niebieskie obramowanie hover */
            }

            /* ▼▼▼ DZIEDZICZENIE DLA ELEMENTÓW WEWNĘTRZNYCH ▼▼▼ */
            FileTileWidget QWidget {
                /* Tylko elementy QWidget WEWNĄTRZ FileTileWidget dziedziczą tło z rodzica */
                background-color: inherit !important;
            }
        """
        self.setStyleSheet(super_aggressive_stylesheet)

        # Ustawienie dodatkowych właściwości
        self.setAutoFillBackground(True)

        # Wymuś ponowne zastosowanie stylu BARDZO AGRESYWNIE
        self.style().unpolish(self)
        self.style().polish(self)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # Dodatkowo: wymuś aktualizację
        self.update()
        self.repaint()

        # Ustaw też palettę jako backup
        palette = self.palette()
        palette.setColor(self.backgroundRole(), QColor("#2b2b2b"))
        self.setPalette(palette)

        # Inicjalizacja UI
        self._init_ui()

        # Ustawienie danych tekstowych i metadanych (bez ładowania miniatury)
        self._update_static_data()

        # Asynchroniczne ładowanie miniatury
        self._load_thumbnail_async()

        # Usuwamy eventFilter, jeśli cała logika kliknięć jest w mouseReleaseEvent
        # self.thumbnail_label.installEventFilter(self)
        # self.filename_label.installEventFilter(self)

        # Ustawienie danych z FilePair
        self.update_data(file_pair)

    def _update_font_size(self):
        """Aktualizuje rozmiar czcionki w zależności od rozmiaru kafelka."""
        # Oblicz rozmiar czcionki na podstawie rozmiaru kafelka
        base_font_size = max(8, min(18, int(self.thumbnail_size[0] / 12)))  # 8-18px

        # ═══════════════════════════════════════════════════════════════
        # STYLOWANIE TEKSTU NAZWY PLIKU - EDYTUJ TUTAJ KOLORY CZCIONKI
        # ═══════════════════════════════════════════════════════════════
        self.filename_label.setStyleSheet(
            f"""
            QLabel {{
                /* ▼▼▼ NORMALNY STAN TEKSTU ▼▼▼ */
                color: #FFFFFF;                      /* BIAŁY tekst - zmień na #000000 dla jasnego tła */
                font-weight: bold;                   /* Pogrubiona czcionka */
                font-size: {base_font_size}px;       /* Dynamiczny rozmiar czcionki */
                padding: 2px;                        /* Odstęp wokół tekstu */
                border-radius: 2px;                  /* Zaokrąglone rogi */
            }}

            QLabel:hover {{
                /* ▼▼▼ HOVER - NAJECHANIE MYSZĄ NA TEKST ▼▼▼ */
                color: #0066CC;                      /* NIEBIESKI tekst hover - zmień według potrzeb */
                font-weight: bold;                   /* Pozostaje pogrubiony */
                text-decoration: underline;          /* Podkreślenie przy hover */
            }}
        """
        )

    def set_thumbnail_size(self, new_size: tuple[int, int]):
        """
        Ustawia nowy rozmiar całego kafelka i dostosowuje jego zawartość.

        Args:
            new_size (tuple): Nowy rozmiar kafelka (szerokość, wysokość) w pikselach.
        """
        if self.thumbnail_size != new_size:
            old_size = self.thumbnail_size
            self.thumbnail_size = new_size

            # Ustaw stały rozmiar całego widgetu kafelka
            self.setFixedSize(new_size[0], new_size[1])

            # Oblicz kwadratowy rozmiar dla samej miniatury
            # Ustaw taką samą szerokość i wysokość dla zachowania kwadratowych proporcji
            # Zwiększamy przestrzeń dla nazwy pliku (z 50px na 70px)
            thumb_dimension = min(new_size[0] - 10, new_size[1] - 70)  # Kwadrat

            # Ustaw rozmiar etykiety miniatury
            self.thumbnail_label.setFixedSize(thumb_dimension, thumb_dimension)

            # Skalowanie czcionki w zależności od rozmiaru kafelka
            self._update_font_size()

            # Wymuś ponowne załadowanie miniatury
            self._current_worker_id += 1
            self._load_thumbnail_async()

            # Poinformuj layout, że rozmiar preferowany widgetu się zmienił
            self.updateGeometry()

            logging.debug(
                f"Kafelek zmienił rozmiar z {old_size} na {new_size}, miniatura: {self.thumbnail_label.size()}"
            )

    def _init_ui(self):
        """
        Inicjalizuje elementy interfejsu użytkownika kafelka.
        """
        # Główny layout - pionowy, z minimalnymi marginesami
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)  # Zminimalizowane marginesy
        self.layout.setSpacing(1)  # Minimalne odstępy między elementami

        # --- Pasek wskaźnika koloru ---
        # Usunięty osobny pasek kolorów - będziemy używać ramki wokół miniatury

        # --- Frame - kontener na miniaturę z kolorową obwódką ---
        self.thumbnail_frame = QFrame(self)
        # ═══════════════════════════════════════════════════════════════
        # STYLOWANIE RAMKI MINIATURY (DOMYŚLNE - BEZ KOLORU)
        # ═══════════════════════════════════════════════════════════════
        self.thumbnail_frame.setStyleSheet(
            """
            QFrame {
                /* ▼▼▼ DOMYŚLNA RAMKA MINIATURY ▼▼▼ */
                border: none;                        /* Bez obramowania (kolor dodawany dynamicznie) */
                padding: 0px;                        /* Bez wewnętrznych odstępów */
            }
        """
        )

        # Ustawienie layoutu dla thumbnail_frame
        thumbnail_frame_layout = QVBoxLayout(self.thumbnail_frame)
        thumbnail_frame_layout.setContentsMargins(0, 0, 0, 0)  # Bez marginesów
        thumbnail_frame_layout.setSpacing(0)  # Bez odstępów

        # Label na miniaturę - umieszczona wewnątrz ramki
        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Konfiguracja miniatury aby była kwadratowa i skalowała się poprawnie
        self.thumbnail_label.setMinimumSize(80, 80)  # Minimum dla miniatury

        # Obliczenie wymiarów dla miniatury kwadratowej
        thumb_size = min(
            self.thumbnail_size[0] - 10, self.thumbnail_size[1] - 50
        )  # Kwadrat
        self.thumbnail_label.setFixedSize(thumb_size, thumb_size)

        self.thumbnail_label.setScaledContents(
            True
        )  # Skaluj zawartość do rozmiaru widgetu
        self.thumbnail_label.setFrameShape(
            QFrame.Shape.NoFrame
        )  # Bez wewnętrznej ramki

        # ═══════════════════════════════════════════════════════════════
        # STYLOWANIE MINIATURY - EFEKT HOVER
        # ═══════════════════════════════════════════════════════════════
        self.thumbnail_label.setStyleSheet(
            """
            QLabel:hover {
                /* ▼▼▼ HOVER NA MINIATURZE ▼▼▼ */
                opacity: 0.9;                        /* Lekkie przyciemnienie przy hover (0.1-1.0) */
            }
        """
        )

        # Dodanie thumbnail_label do thumbnail_frame
        thumbnail_frame_layout.addWidget(self.thumbnail_label)

        # Dodanie ramki z miniaturą do głównego layoutu
        self.layout.addWidget(self.thumbnail_frame, 0, Qt.AlignmentFlag.AlignHCenter)

        # Etykieta na nazwę pliku z efektem hover
        self.filename_label = QLabel("Ładowanie...", self)
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filename_label.setWordWrap(True)  # Zawijanie tekstu
        self.filename_label.setMaximumHeight(
            35
        )  # Zwiększona wysokość dla lepszej widoczności
        self.filename_label.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        # ═══════════════════════════════════════════════════════════════
        # STYLOWANIE ETYKIETY NAZWY PLIKU W _init_ui (PIERWOTNE)
        # ═══════════════════════════════════════════════════════════════
        self.filename_label.setStyleSheet(
            """
            QLabel {
                /* ▼▼▼ PODSTAWOWY WYGLĄD TEKSTU NAZWY ▼▼▼ */
                color: #FFFFFF;                      /* BIAŁY tekst - zmień na #000000 dla jasnego tła */
                font-weight: bold;                   /* Pogrubiona czcionka */
                padding: 2px;                        /* Odstęp wokół tekstu */
                border-radius: 2px;                  /* Zaokrąglone rogi */
            }
            QLabel:hover {
                /* ▼▼▼ HOVER NA NAZWIE PLIKU ▼▼▼ */
                color: #0066CC;                      /* NIEBIESKI tekst hover */
                font-weight: bold;                   /* Pozostaje pogrubiony */
                text-decoration: underline;          /* Podkreślenie przy hover */
            }
        """
        )
        self.layout.addWidget(self.filename_label)

        # --- Kontrolki metadanych ---
        self.metadata_controls = MetadataControlsWidget(self)
        self.metadata_controls.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.metadata_controls.setMaximumHeight(30)  # Zmniejszona wysokość
        self.layout.addWidget(self.metadata_controls)

        # Połączenie sygnałów z MetadataControlsWidget
        self.metadata_controls.tile_selected_changed.connect(
            self._on_tile_selection_changed
        )
        self.metadata_controls.stars_value_changed.connect(self._on_stars_changed)
        self.metadata_controls.color_tag_value_changed.connect(
            self._on_color_tag_changed
        )

        self._current_worker_id = 0  # ID ostatnio uruchomionego workera
        self._thumbnail_worker: ThumbnailLoaderWorker | None = None
        self._thumbnail_thread: QThread | None = None

        # Ustawienie danych z FilePair
        self.update_data(self.file_pair)

    def update_data(self, file_pair: FilePair):
        """
        Aktualizuje dane kafelka na podstawie obiektu FilePair.

        Args:
            file_pair (FilePair): Obiekt pary plików z nowymi danymi
        """
        self.file_pair = file_pair
        self._file_pair = file_pair  # Ujednolicenie self._file_pair i self.file_pair

        # POPRAWKA: Ustaw file_pair w metadata_controls!
        self.metadata_controls.set_file_pair(file_pair)

        self._update_static_data()

        # Dodatkowo upewnij się, że kolor obwódki jest zaktualizowany
        # ale tylko jeśli jest wybrany kolor
        if file_pair:
            color_tag = file_pair.get_color_tag()
            if color_tag and color_tag.strip():
                self._update_thumbnail_border_color(color_tag)
            else:
                # Usuwamy obwódkę jeśli nie ma koloru
                self._update_thumbnail_border_color("")

    def _update_static_data(self):
        """Aktualizuje statyczne dane kafelka (nazwa, rozmiar, metadane)."""
        try:
            if self.file_pair:  # Upewnij się, że file_pair istnieje
                self.filename_label.setText(self.file_pair.get_base_name())
                # POPRAWKA: Delegowanie do metadata_controls
                self.metadata_controls.update_selection_display(False)  # Default to not selected
                self.metadata_controls.update_stars_display(self.file_pair.get_stars())

                # Aktualizacja koloru obwódki miniatury - tylko jeśli jest wybrany kolor
                color_tag = self.file_pair.get_color_tag()
                self.metadata_controls.update_color_tag_display(color_tag)
                if color_tag and color_tag.strip():
                    self._update_thumbnail_border_color(color_tag)
                else:
                    self._update_thumbnail_border_color("")  # Usuń kolor obwódki
            else:
                self.filename_label.setText("Brak danych")
                # Ustaw domyślne stany dla kontrolek, jeśli file_pair jest None
                # POPRAWKA: Delegowanie do metadata_controls
                self.metadata_controls.update_selection_display(False)
                self.metadata_controls.update_stars_display(0)
                self.metadata_controls.update_color_tag_display("")
                self._update_thumbnail_border_color("")  # Usuń kolor obwódki

        except Exception as e:
            logging.error(f"Błąd aktualizacji danych statycznych kafelka: {e}")
            # Fallback UI w przypadku błędu
            self.filename_label.setText("Błąd danych")

    def _update_thumbnail_border_color(self, color_hex: str):
        """Aktualizuje kolor obwódki wokół miniatury."""
        if color_hex and color_hex.strip():
            # ═══════════════════════════════════════════════════════════════
            # KOLOROWA OBWÓDKA MINIATURY (DYNAMICZNA - ZALEŻNA OD KOLORU TAGU)
            # ═══════════════════════════════════════════════════════════════
            self.thumbnail_frame.setStyleSheet(
                f"""
                QFrame {{
                    /* ▼▼▼ KOLOROWA OBWÓDKA WOKÓŁ MINIATURY ▼▼▼ */
                    border: 2px solid {color_hex};          /* Grubość i kolor obwódki (6px) */
                    border-radius: 2px;                     /* Zaokrąglone rogi obwódki */
                    padding: 0px;                           /* Bez wewnętrznych odstępów */
                    background-color: transparent;          /* Przezroczyste tło ramki */
                }}
            """
            )
            logging.debug(f"Ustawiono kolor obwódki na: {color_hex}")
        else:
            # ═══════════════════════════════════════════════════════════════
            # BRAK OBWÓDKI (DOMYŚLNY STAN - BEZ KOLORU TAGU)
            # ═══════════════════════════════════════════════════════════════
            self.thumbnail_frame.setStyleSheet(
                """
                QFrame {
                    /* ▼▼▼ BRAK KOLOROWEJ OBWÓDKI ▼▼▼ */
                    border: none;                           /* Bez obramowania */
                    padding: 0px;                           /* Bez wewnętrznych odstępów */
                    background-color: transparent;          /* Przezroczyste tło ramki */
                }
            """
            )
            logging.debug("Usunięto obwódkę - przezroczysta")

    def set_file_pair(self, file_pair: FilePair | None):
        """Ustawia parę plików dla kafelka i odświeża UI."""
        self._file_pair = file_pair
        self.file_pair = file_pair  # Ujednolicenie self.file_pair i self._file_pair
        self._current_worker_id += 1  # Inkrementacja ID dla nowego zadania ładowania

        if self._file_pair:
            self.filename_label.setText(self._file_pair.get_base_name())
            self.setToolTip(f"Ścieżka: {self._file_pair.get_archive_path()}")
            self._load_thumbnail_async()
            self.metadata_controls.set_file_pair(self._file_pair)  # Przekaż FilePair
            self.metadata_controls.setEnabled(True)

            # Aktualizacja koloru obwódki miniatury - tylko jeśli jest wybrany kolor
            color_tag = self._file_pair.get_color_tag()
            if color_tag and color_tag.strip():
                self._update_thumbnail_border_color(color_tag)
            else:
                # Usuń kolor obwódki
                self._update_thumbnail_border_color("")
        else:
            self.filename_label.setText("Brak pliku")
            self.thumbnail_label.clear()  # Wyczyść miniaturę
            self.thumbnail_label.setText("?")  # Znak zapytania jako placeholder
            self.setToolTip("")
            self.metadata_controls.set_file_pair(None)  # Wyczyść FilePair
            self.metadata_controls.setEnabled(False)

            # Usuń kolor obwódki
            self._update_thumbnail_border_color("")

    def _load_thumbnail_async(self):
        if not self.file_pair or not self.file_pair.get_preview_path():
            logging.warning(
                "FileTileWidget: Brak file_pair lub ścieżki podglądu, nie można załadować miniatury."
            )
            # Ustawienie placeholdera błędu jeśli ścieżka jest nieprawidłowa
            error_placeholder = ThumbnailCache.get_error_icon(
                self.thumbnail_label.width(), self.thumbnail_label.height()
            )
            if not error_placeholder:  # Jeśli get_error_icon zwróci None
                error_placeholder = create_placeholder_pixmap(
                    self.thumbnail_label.width(),
                    self.thumbnail_label.height(),
                    text="Brak pliku",
                )
            self.thumbnail_label.setPixmap(error_placeholder)
            self.original_thumbnail = (
                error_placeholder  # Zapisz jako oryginalną, aby uniknąć ponownych prób
            )
            return

        preview_path = self.file_pair.get_preview_path()
        # Używamy rozmiaru etykiety miniatury - zawsze będzie kwadratem
        width = height = self.thumbnail_label.width()  # Kwadratowe proporcje

        # Zabezpieczenie przed zerowymi lub ujemnymi wymiarami
        if width <= 0 or height <= 0:
            width = height = 80  # Minimalne wymiary awaryjne
            logging.warning(
                f"Nieprawidłowe wymiary miniatury, używam domyślnych {width}x{height}"
            )

        # 1. Sprawdź cache
        cache = ThumbnailCache.get_instance()
        cached_pixmap = cache.get_thumbnail(preview_path, width, height)

        if cached_pixmap and not cached_pixmap.isNull():
            logging.debug(f"Cache HIT dla {preview_path} ({width}x{height})")
            self._on_thumbnail_loaded(
                cached_pixmap, self._current_worker_id
            )  # Przekaż aktualny worker_id
            return
        else:
            logging.debug(f"Cache MISS dla {preview_path} ({width}x{height})")

        # Przerywanie istniejącego workera, jeśli działa
        # Sprawdzamy, czy wątek istnieje i czy jest aktywny
        if self.thumbnail_thread is not None and self.thumbnail_thread.isRunning():
            logging.debug(
                f"Przerywanie poprzedniego workera dla {self.file_pair.get_base_name()}"
            )
            # Rozłącz stare sygnały, aby uniknąć wywołania slotu przez starego workera
            if self.thumbnail_worker is not None:
                try:
                    self.thumbnail_worker.finished.disconnect(
                        self._on_thumbnail_loaded_slot
                    )
                except TypeError:  # Sygnał mógł nie być podłączony lub już rozłączony
                    pass

            self.thumbnail_thread.quit()
            if not self.thumbnail_thread.wait(500):  # Czekaj do 500ms
                logging.warning(
                    f"Poprzedni wątek ładowania miniatury dla {self.file_pair.get_base_name()} nie zakończył się w oczekiwanym czasie. Próbuję zakończyć siłowo."
                )
                self.thumbnail_thread.terminate()  # Ostateczność
                self.thumbnail_thread.wait()  # Poczekaj na zakończenie po terminate

            # Po udanym przerwaniu lub terminate, QThread powinien wyemitować 'finished'.
            # Slot cleanup_worker_thread powinien zająć się deleteLater.
            # Nie ma potrzeby ręcznego wywoływania deleteLater tutaj, jeśli 'finished' jest poprawnie połączony.
            # Ustawienie na None jest ważne, aby nowy wątek mógł być utworzony.
            self.thumbnail_worker = None
            self.thumbnail_thread = None

        # Zwiększ ID dla nowego workera
        self._current_worker_id += 1
        worker_id = self._current_worker_id

        # Natychmiastowe ustawienie placeholdera "Ładowanie..."
        loading_placeholder = create_placeholder_pixmap(
            width, height, text="Ładowanie..."
        )
        self.thumbnail_label.setPixmap(loading_placeholder)
        # Nie ustawiamy self.original_thumbnail na placeholder ładowania,
        # bo chcemy, żeby _on_thumbnail_loaded zapisało właściwą miniaturę lub błąd.

        self.thumbnail_thread = QThread(self)
        self.thumbnail_worker = ThumbnailLoaderWorker(self.file_pair, width, height)
        self.thumbnail_worker.moveToThread(self.thumbnail_thread)

        # Połączenie sygnałów - przekazujemy worker_id do slotu
        # Tworzymy slot lambda, który będzie przechowywał worker_id z momentu tworzenia połączenia
        self._on_thumbnail_loaded_slot = (
            lambda pixmap, current_id=worker_id: self._on_thumbnail_loaded(
                pixmap, current_id
            )
        )
        self.thumbnail_worker.finished.connect(self._on_thumbnail_loaded_slot)
        self.thumbnail_thread.started.connect(self.thumbnail_worker.run)

        # Sprzątanie
        self.thumbnail_worker.finished.connect(self.thumbnail_thread.quit)

        def cleanup_worker_thread():
            # Ta funkcja jest teraz bardziej krytyczna dla poprawnego zarządzania pamięcią
            sender_thread = (
                self.sender()
            )  # Powinien być QThread, który wyemitował 'finished'

            # Usuwamy workera tylko jeśli należy do zakończonego wątku
            # i jeśli referencje nadal na niego wskazują (nie został zastąpiony)
            if (
                self.thumbnail_thread == sender_thread
                and self.thumbnail_worker is not None
            ):
                self.thumbnail_worker.deleteLater()
                self.thumbnail_worker = None  # Usuń referencję po zleceniu usunięcia

            if self.thumbnail_thread == sender_thread:
                self.thumbnail_thread.deleteLater()
                self.thumbnail_thread = None  # Usuń referencję po zleceniu usunięcia

            # logging.debug(f"Wątek {sender_thread} zakończony i zasoby posprzątane.")

        self.thumbnail_thread.finished.connect(cleanup_worker_thread)

        self.thumbnail_thread.start()
        logging.debug(
            f"Rozpoczęto asynch. ładowanie dla {self.file_pair.get_base_name()}"
        )

    def _on_thumbnail_loaded(self, pixmap: QPixmap | None, worker_id: int):
        """Obsługuje załadowaną miniaturę z workera."""
        # Sprawdź, czy to jest odpowiedź od aktualnego workera
        if worker_id != self._current_worker_id:
            # logging.debug(f"FileTileWidget: Otrzymano miniaturę od przestarzałego workera ({worker_id}), ignorowanie.")
            return

        if pixmap and not pixmap.isNull():
            self.thumbnail_label.setPixmap(pixmap)
            # Dodaj do cache, jeśli się powiodło
            if self.file_pair:  # Upewnij się, że file_pair istnieje
                thumbnail_cache = ThumbnailCache.get_instance()
                thumbnail_cache.add_thumbnail(
                    self.file_pair.get_archive_path(),
                    self.thumbnail_size[0],
                    self.thumbnail_size[1],
                    pixmap,
                )

                # Aktualizuj kolor obwódki tylko jeśli jest wybrany kolor
                color_tag = self.file_pair.get_color_tag()
                if color_tag and color_tag.strip():
                    self._update_thumbnail_border_color(color_tag)
        else:
            # Jeśli pixmap jest None lub isNull(), użyj obrazka błędu z cache
            error_pixmap = ThumbnailCache.get_instance().get_error_icon(
                self.thumbnail_label.width(), self.thumbnail_label.height()
            )
            if error_pixmap:
                self.thumbnail_label.setPixmap(error_pixmap)
            else:
                # Fallback, jeśli nawet get_error_icon zawiedzie
                self.thumbnail_label.setText("Błąd ładowania")
                self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._current_worker = None  # Zresetuj referencję do workera        # --- Obsługa sygnałów z MetadataControlsWidget ---

    def _on_tile_selection_changed(self, is_selected: bool):
        """Handle tile selection change from MetadataControlsWidget checkbox."""
        logging.info(f"🔥 FileTileWidget._on_tile_selection_changed wywołane: {is_selected}")
        if self._file_pair:
            # Emit signal to notify about selection change
            self.tile_selected.emit(self._file_pair, is_selected)
            logging.debug(
                f"FileTileWidget: Zmieniono status selekcji dla {self._file_pair.get_base_name()} na {is_selected}"
            )

    def _on_stars_changed(self, stars: int):
        logging.info(f"🔥 FileTileWidget._on_stars_changed wywołane: {stars}")
        if self._file_pair:
            self._file_pair.set_stars(stars)
            self.metadata_controls.update_stars_display(stars)
            self.stars_changed.emit(self._file_pair, stars)
            self.file_pair_updated.emit(self._file_pair)
            logging.debug(
                f"FileTileWidget: Zmieniono liczbę gwiazdek dla {self._file_pair.get_base_name()} na {stars}"
            )

    def _on_color_tag_changed(self, color_hex: str):
        logging.info(f"🔥 FileTileWidget._on_color_tag_changed wywołane: {color_hex}")
        if self._file_pair:
            self._file_pair.set_color_tag(color_hex)
            # Odśwież kontrolki metadanych i ramkę miniatury
            self.metadata_controls.update_color_tag_display(color_hex)
            self._update_thumbnail_border_color(color_hex)

            # Emituj sygnał, że tag koloru został zmieniony
            self.color_tag_changed.emit(self._file_pair, color_hex)
            self.file_pair_updated.emit(self._file_pair)

            logging.debug(
                f"FileTileWidget: Zmieniono tag koloru dla {self._file_pair.get_base_name()} na {color_hex}"
            )

    # Usunięte metody update_favorite_status, update_stars_display, update_color_tag_display
    # Zostały przeniesione/zastąpione przez logikę w MetadataControlsWidget
    # i bezpośrednie wywołania z _update_static_data

    def _create_context_menu(self) -> QMenu:
        """Tworzy menu kontekstowe dla kafelka."""  # Poprawiony komentarz
        menu = QMenu(self)

        # Przykładowe akcje - dostosuj według potrzeb
        action_open = menu.addAction("Otwórz")
        action_preview = menu.addAction("Podgląd")
        action_properties = menu.addAction("Właściwości")

        # Rozdzielacz
        menu.addSeparator()

        # Akcja do wyjścia
        action_exit = menu.addAction("Zamknij")

        # Ustawienia akcji domyślnych (np. dla podwójnego kliknięcia)
        action_open.setShortcut("Ctrl+O")
        action_preview.setShortcut("Ctrl+P")

        # Połączenie sygnałów akcji z odpowiednimi slotami
        action_open.triggered.connect(self.open_file)
        action_preview.triggered.connect(self.preview_image)
        action_properties.triggered.connect(self.show_properties)
        action_exit.triggered.connect(self.close)

        return menu

    # MODIFICATION: New method to emit favorite_toggled signal
    def _emit_favorite_toggled_signal(self):
        """Emituje sygnał zmiany statusu ulubionego."""
        # Ta metoda może być już niepotrzebna jeśli logika jest w MetadataControlsWidget
        # self.favorite_toggled.emit(self.file_pair)
        pass

    # Usunięte metody _on_star_button_clicked, update_stars_display
    # Logika gwiazdek jest teraz w MetadataControlsWidget

    # Usunięte metody _on_color_combo_activated, update_color_tag_display
    # Logika tagów kolorów jest teraz w MetadataControlsWidget

    # MODIFICATION: New method to handle clicks on labels (event filter)
    def eventFilter(self, obj, event):
        """Obsługuje kliknięcia na etykietach miniatury i nazwy."""
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                if obj == self.thumbnail_label:
                    # Sprawdzenie czy file_pair istnieje przed próbą dostępu
                    if self.file_pair:
                        fp_name = self.file_pair.get_base_name()[:20]
                        logging.debug(f"Thumb: {fp_name}..")
                        self.preview_image_requested.emit(self.file_pair)
                    else:
                        logging.warning(
                            "Kliknięto miniaturę, ale self.file_pair to None"
                        )
                    return True
                elif (
                    obj == self.filename_label
                ):  # POPRAWKA: name_label -> filename_label
                    # Sprawdzenie czy file_pair istnieje przed próbą dostępu
                    if self.file_pair:
                        fp_name = self.file_pair.get_base_name()[:20]
                        logging.debug(f"Name: {fp_name}..")
                        self.archive_open_requested.emit(self.file_pair)
                    else:
                        logging.warning(
                            "Kliknięto nazwę pliku, ale self.file_pair to None"
                        )
                    return True
        return super().eventFilter(obj, event)

    # --- Drag and Drop ---
    def mousePressEvent(self, event: QEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.press_pos = event.pos()
            self.maybe_drag = True
            self.drag_active = False  # Zresetuj flagę aktywnego przeciągania
            # Nie wywołujemy super().mousePressEvent(event) od razu,
            # aby dać szansę mouseReleaseEvent na obsłużenie "czystego" kliknięcia.
            # event.accept() # Można rozważyć, jeśli chcemy całkowicie przejąć zdarzenie
        else:
            # Dla innych przycisków myszy, zachowaj standardowe działanie
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QEvent):
        # Jeśli nie było wciśnięcia lewego przycisku lub nie jest to potencjalne przeciąganie, ignoruj
        if not self.maybe_drag or not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return

        # Jeśli przeciąganie jest już aktywne, po prostu przekaż zdarzenie
        if self.drag_active:
            super().mouseMoveEvent(event)
            return

        # Sprawdź, czy ruch przekroczył próg rozpoczęcia przeciągania
        if (
            event.pos() - self.press_pos
        ).manhattanLength() >= QApplication.instance().startDragDistance():
            # Sprawdź, czy element pod kursorem w momencie naciśnięcia pozwala na przeciąganie
            # (tj. nie jest to miniatura ani nazwa pliku, które mają własne akcje na kliknięcie)
            target_widget_at_press = self.childAt(self.press_pos)

            # Rozpocznij przeciąganie, jeśli nie kliknięto bezpośrednio na miniaturę lub nazwę
            # LUB jeśli kliknięto na obszar, który nie jest żadnym z tych widgetów (np. puste tło kafelka)
            # Można też dodać dedykowany "uchwyt" i sprawdzać go tutaj.
            if target_widget_at_press not in [
                self.thumbnail_label,
                self.filename_label,
            ]:
                self.drag_active = True  # Oznacz, że przeciąganie jest aktywne

                if (
                    not self.file_pair
                    or not self.file_pair.archive_path
                    or not self.file_pair.preview_path
                ):
                    logging.warning(
                        "Próba przeciągnięcia kafelka bez kompletnej pary plików."
                    )
                    self.maybe_drag = False  # Anuluj potencjalne przeciąganie
                    # Nie ma potrzeby wywoływania super().mouseMoveEvent(event) tutaj, bo drag nie ruszył
                    return

                drag = QDrag(self)
                mime_data = QMimeData()
                urls = [
                    QUrl.fromLocalFile(self.file_pair.archive_path),
                    QUrl.fromLocalFile(self.file_pair.preview_path),
                ]
                mime_data.setUrls(urls)
                drag.setMimeData(mime_data)

                pixmap = self.thumbnail_label.pixmap()  # Użyj aktualnej miniatury
                if pixmap and not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        QSize(100, 100),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    drag.setPixmap(scaled_pixmap)
                    drag.setHotSpot(scaled_pixmap.rect().center())
                else:
                    # Fallback, jeśli pixmapa nie jest dostępna (np. błąd ładowania)
                    # Można użyć prostokąta jako placeholdera
                    placeholder_pixmap = QPixmap(QSize(100, 100))
                    placeholder_pixmap.fill(Qt.GlobalColor.lightGray)
                    drag.setPixmap(placeholder_pixmap)
                    drag.setHotSpot(event.pos() - self.rect().topLeft())

                logging.debug(
                    f"Rozpoczęcie przeciągania dla: {self.file_pair.base_name} z URLami: {[url.toString() for url in urls]}"
                )

                drop_action = drag.exec(Qt.DropAction.MoveAction)

                if drop_action == Qt.DropAction.MoveAction:
                    logging.debug(
                        f"Operacja przeciągania zakończona sukcesem (MoveAction) dla {self.file_pair.base_name}"
                    )
                else:
                    logging.debug(
                        f"Operacja przeciągania anulowana lub nie powiodła się dla {self.file_pair.base_name}"
                    )

                # Niezależnie od wyniku, przeciąganie się zakończyło (lub nie zaczęło poprawnie)
                self.maybe_drag = False
                self.drag_active = False  # Już nie jest aktywne
                self.press_pos = None
                # Nie ma potrzeby wywoływania super().mouseMoveEvent(event) po drag.exec()
                return  # Zakończ przetwarzanie tego zdarzenia ruchu
            else:
                # Jeśli kliknięto na miniaturę/nazwę, ale ruch był wystarczający do drag,
                # to traktujemy to jako anulowanie "kliknięcia" i nie rozpoczynamy drag.
                # Użytkownik musi kliknąć "obok" tych elementów, aby przeciągnąć.
                self.maybe_drag = False  # Anuluj potencjalne przeciąganie
                # Można by tu wywołać super().mouseMoveEvent(event), ale prawdopodobnie nie jest to konieczne
                # bo nie chcemy standardowego zachowania przeciągania dla tych elementów.
                return

        # Jeśli self.maybe_drag jest True, ale dystans jest wciąż za mały,
        # lub jeśli przeciąganie nie zostało aktywowane z innych powodów,
        # przekaż zdarzenie do bazowej implementacji.
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Sprawdź, czy to było "czyste" kliknięcie (nie rozpoczęto przeciągania)
            if self.maybe_drag and not self.drag_active and self.press_pos is not None:
                # Sprawdź, czy puszczenie przycisku nastąpiło blisko miejsca naciśnięcia
                # i czy nie było znaczącego ruchu (dodatkowy warunek, jeśli startDragDistance jest małe)
                if (
                    event.pos() - self.press_pos
                ).manhattanLength() < QApplication.instance().startDragDistance():
                    clicked_widget = self.childAt(
                        self.press_pos
                    )  # Sprawdź, co było pod kursorem przy naciśnięciu

                    if clicked_widget == self.thumbnail_label:
                        if self.file_pair:
                            logging.debug(
                                f"Kliknięcie (Release) na miniaturę: {self.file_pair.base_name}"
                            )
                            self.preview_image_requested.emit(self.file_pair)
                        # event.accept() # Akceptujemy, aby nie było dalej przetwarzane
                        # Reset flag po obsłużeniu kliknięcia
                        self.maybe_drag = False
                        self.press_pos = None
                        super().mouseReleaseEvent(
                            event
                        )  # Wywołaj bazową, aby zakończyć cykl zdarzenia
                        return
                    elif clicked_widget == self.filename_label:
                        if self.file_pair:
                            logging.debug(
                                f"Kliknięcie (Release) na nazwę pliku: {self.file_pair.base_name}"
                            )
                            self.archive_open_requested.emit(self.file_pair)
                        # event.accept()
                        self.maybe_drag = False
                        self.press_pos = None
                        super().mouseReleaseEvent(event)
                        return

            # Jeśli doszło do przeciągania (drag_active było True) lub kliknięcie nie zostało obsłużone powyżej
            # Zresetuj flagi
            self.maybe_drag = False
            self.drag_active = False
            self.press_pos = None
            super().mouseReleaseEvent(event)
        else:
            # Dla innych przycisków myszy
            super().mouseReleaseEvent(event)

    # --- Koniec Drag and Drop ---

    # Usunięte metody update_favorite_status, update_stars_display, update_color_tag_display
    # Zostały przeniesione/zastąpione przez logikę w MetadataControlsWidget
    # i bezpośrednie wywołania z _update_static_data

    def _create_context_menu(self) -> QMenu:
        """Tworzy menu kontekstowe dla kafelka."""  # Poprawiony komentarz
        menu = QMenu(self)

        # Przykładowe akcje - dostosuj według potrzeb
        action_open = menu.addAction("Otwórz")
        action_preview = menu.addAction("Podgląd")
        action_properties = menu.addAction("Właściwości")

        # Rozdzielacz
        menu.addSeparator()

        # Akcja do wyjścia
        action_exit = menu.addAction("Zamknij")

        # Ustawienia akcji domyślnych (np. dla podwójnego kliknięcia)
        action_open.setShortcut("Ctrl+O")
        action_preview.setShortcut("Ctrl+P")

        # Połączenie sygnałów akcji z odpowiednimi slotami
        action_open.triggered.connect(self.open_file)
        action_preview.triggered.connect(self.preview_image)
        action_properties.triggered.connect(self.show_properties)
        action_exit.triggered.connect(self.close)

        return menu

    # Usunięte metody _on_star_button_clicked, update_stars_display
    # Logika gwiazdek jest teraz w MetadataControlsWidget

    # Usunięte metody _on_color_combo_activated, update_color_tag_display
    # Logika tagów kolorów jest teraz w MetadataControlsWidget
