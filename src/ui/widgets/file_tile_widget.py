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
from PyQt6.QtCore import (
    QEvent,
    QMimeData,
    QSize,
    Qt,
    QThreadPool,
    QTimer,
    QUrl,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QColor, QDesktopServices, QDrag, QPixmap
from PyQt6.QtWidgets import QHBoxLayout  # Dodaj QHBoxLayout
from PyQt6.QtWidgets import QVBoxLayout  # Upewnij się, że QVBoxLayout jest tutaj
from PyQt6.QtWidgets import QApplication, QFrame, QLabel, QMenu, QSizePolicy, QWidget

from src.models.file_pair import FilePair
from src.ui.delegates.workers import ThumbnailGenerationWorker
from src.ui.widgets.metadata_controls_widget import (
    MetadataControlsWidget,
)  # NOWY IMPORT
from src.ui.widgets.thumbnail_cache import ThumbnailCache
from src.utils.image_utils import (
    create_placeholder_pixmap,
    crop_to_square,
    pillow_image_to_qpixmap,
)

# Definicja Workera - teraz używamy ThumbnailGenerationWorker z workers.py


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

        # Worker do ładowania miniatur
        self._current_worker_id = 0
        self._current_thumbnail_worker = None

        # Nowe flagi i zmienne do obsługi kliknięć i przeciągania
        self.press_pos = None
        self.maybe_drag = False
        self.drag_active = False

        # Ustawienie podstawowych właściwości widgetu
        self.setObjectName("FileTileWidget")

        # ═══════════════════════════════════════════════════════════════
        # SEKCJA STYLOWANIA KAFELKÓW - CIEMNY SCHEMAT, PROFESJONALNY
        # ═══════════════════════════════════════════════════════════════
        dark_professional_stylesheet = """
            /* ▼▼▼ PROFESJONALNE CIEMNE KAFELKI ▼▼▼ */
            FileTileWidget {
                /* CIEMNE TŁO PASUJĄCE DO SCHEMATU */
                background-color: #2D2D2D !important;

                /* SUBTELNE CIEMNE OBRAMOWANIE */
                border: 1px solid #404040 !important;
                border-radius: 6px !important;
                
                /* PRZERWY MIĘDZY KAFELKAMI */
                margin: 6px !important;
                padding: 8px !important;
                
                /* MINIMALNE WYMIARY */
                min-width: 150px !important;
                min-height: 190px !important;
            }

            /* ▼▼▼ HOVER - SUBTELNY EFEKT ▼▼▼ */
            FileTileWidget:hover {
                background-color: #353535 !important;
                border: 1px solid #5A9FD4 !important;
            }

            /* ▼▼▼ ALTERNATYWNY SELEKTOR ▼▼▼ */
            QWidget#FileTileWidget {
                background-color: #2D2D2D !important;
                border: 1px solid #404040 !important;
                border-radius: 6px !important;
                margin: 6px !important;
                padding: 8px !important;
                min-width: 150px !important;
                min-height: 190px !important;
            }
            
            QWidget#FileTileWidget:hover {
                background-color: #353535 !important;
                border: 1px solid #5A9FD4 !important;
            }

            /* ▼▼▼ PRZEZROCZYSTE ELEMENTY WEWNĘTRZNE ▼▼▼ */
            FileTileWidget QWidget {
                background-color: transparent !important;
            }
            
            FileTileWidget QFrame {
                background-color: transparent !important;
                border: none !important;
            }
        """
        self.setStyleSheet(dark_professional_stylesheet)

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
        # STYLOWANIE TEKSTU NAZWY PLIKU - CIEMNY SCHEMAT
        # ═══════════════════════════════════════════════════════════════
        self.filename_label.setStyleSheet(
            f"""
            QLabel {{
                /* ▼▼▼ JASNY TEKST NA CIEMNYM TLE ▼▼▼ */
                color: #E0E0E0;                      /* Jasny szary tekst */
                font-weight: 400;                    /* Normal weight */
                font-size: {base_font_size}px;       /* Dynamiczny rozmiar czcionki */
                font-family: "Segoe UI", Arial, sans-serif; /* Czytelna czcionka */
                padding: 4px 2px;                    /* Minimalne odstępy */
                border-radius: 0px;                  /* Bez zaokrąglenia */
                background-color: transparent;       /* Przezroczyste tło */
                text-align: center;                  /* Wyśrodkowany tekst */
                border: none;                        /* Bez obramowania */
            }}

            QLabel:hover {{
                /* ▼▼▼ SUBTELNY HOVER NA TEKŚCIE ▼▼▼ */
                color: #5A9FD4;                      /* Niebieski hover */
                font-weight: 400;                    /* Pozostaje normal */
                background-color: transparent;       /* Bez tła */
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
        # Główny layout - pionowy, z prawidłowymi marginesami
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 12, 8, 8)  # Większy górny i dolny margines
        self.layout.setSpacing(4)  # Większe odstępy między elementami

        # --- Pasek wskaźnika koloru ---
        # Usunięty osobny pasek kolorów - będziemy używać ramki wokół miniatury

        # --- Frame - kontener na miniaturę z kolorową obwódką ---
        self.thumbnail_frame = QFrame(self)
        # Stylowanie ramki miniatury - bez odstępów od miniatury
        self.thumbnail_frame.setStyleSheet(
            """
            QFrame {
                border: none;
                border-radius: 4px;
                padding: 0px;
                margin: 0px;
                background-color: transparent;
            }
        """
        )

        # Ustawienie layoutu dla thumbnail_frame - bez odstępów
        thumbnail_frame_layout = QVBoxLayout(self.thumbnail_frame)
        thumbnail_frame_layout.setContentsMargins(0, 0, 0, 0)
        thumbnail_frame_layout.setSpacing(0)

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
        # STYLOWANIE MINIATURY - CIEMNY SCHEMAT, MINIMALNE
        # ═══════════════════════════════════════════════════════════════
        self.thumbnail_label.setStyleSheet(
            """
            QLabel {
                /* ▼▼▼ MINIMALNA MINIATURA ▼▼▼ */
                border-radius: 3px;                 /* Subtelne zaokrąglenie */
                background-color: transparent;      /* Przezroczyste tło */
                border: none;                       /* Bez obramowania */
            }
            QLabel:hover {
                /* ▼▼▼ SUBTELNY HOVER NA MINIATURZE ▼▼▼ */
                background-color: rgba(90, 159, 212, 0.1); /* Bardzo subtelne tło */
                border: none;                       /* Bez obramowania */
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
        # STYLOWANIE ETYKIETY NAZWY PLIKU - CIEMNY SCHEMAT
        # ═══════════════════════════════════════════════════════════════
        self.filename_label.setStyleSheet(
            """
            QLabel {
                /* ▼▼▼ JASNY TEKST NA CIEMNYM TLE ▼▼▼ */
                color: #E0E0E0;                      /* Jasny szary tekst */
                font-weight: 400;                    /* Normal weight */
                font-family: "Segoe UI", Arial, sans-serif; /* Czytelna czcionka */
                padding: 4px 2px;                    /* Minimalne odstępy */
                border-radius: 0px;                  /* Bez zaokrąglenia */
                background-color: transparent;       /* Przezroczyste tło */
                text-align: center;                  /* Wyśrodkowany tekst */
                border: none;                        /* Bez obramowania */
            }
            QLabel:hover {
                /* ▼▼▼ SUBTELNY HOVER NA NAZWIE PLIKU ▼▼▼ */
                color: #5A9FD4;                      /* Niebieski hover */
                font-weight: 400;                    /* Pozostaje normal */
                background-color: transparent;       /* Bez tła */
            }
        """
        )
        self.layout.addWidget(self.filename_label)

        # --- Kontrolki metadanych ---
        self.metadata_controls = MetadataControlsWidget(self)
        self.metadata_controls.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.metadata_controls.setMaximumHeight(24)  # Kompaktowa wysokość
        self.metadata_controls.setContentsMargins(0, 0, 0, 0)
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
                self.metadata_controls.update_selection_display(
                    False
                )  # Default to not selected
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
            # Kolorowa obwódka miniatury - bezpośrednio wokół obrazka
            self.thumbnail_frame.setStyleSheet(
                f"""
                QFrame {{
                    border: 2px solid {color_hex};
                    border-radius: 4px;
                    padding: 0px;
                    margin: 0px;
                    background-color: transparent;
                }}
            """
            )
            logging.debug(f"Ustawiono kolor obwódki na: {color_hex}")
        else:
            # Brak kolorowej obwódki - przezroczysta ramka
            self.thumbnail_frame.setStyleSheet(
                """
                QFrame {
                    border: none;
                    border-radius: 4px;
                    padding: 0px;
                    margin: 0px;
                    background-color: transparent;
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
        """Ładuje miniaturę asynchronicznie używając ThumbnailGenerationWorker i QThreadPool."""
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
            self.original_thumbnail = error_placeholder
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
            self._on_thumbnail_loaded(cached_pixmap, preview_path, width, height)
            return
        else:
            logging.debug(f"Cache MISS dla {preview_path} ({width}x{height})")

        # Zwiększ ID dla nowego workera
        self._current_worker_id += 1
        worker_id = self._current_worker_id

        # Natychmiastowe ustawienie placeholdera "Ładowanie..."
        loading_placeholder = create_placeholder_pixmap(
            width, height, text="Ładowanie..."
        )
        self.thumbnail_label.setPixmap(loading_placeholder)

        # Przerwij poprzedni worker jeśli istnieje
        if (
            hasattr(self, "_current_thumbnail_worker")
            and self._current_thumbnail_worker
        ):
            self._current_thumbnail_worker.interrupt()

        # Utwórz nowy worker
        worker = ThumbnailGenerationWorker(preview_path, width, height)
        self._current_thumbnail_worker = worker

        # Podłącz sygnały
        worker.signals.finished.connect(
            lambda pixmap, path, w, h: (
                self._on_thumbnail_loaded(pixmap, path, w, h)
                if self._current_thumbnail_worker == worker
                else None
            )
        )
        worker.signals.error.connect(
            lambda error_msg, path, w, h: (
                self._on_thumbnail_error(error_msg, path, w, h)
                if self._current_thumbnail_worker == worker
                else None
            )
        )

        # Uruchom w thread pool
        QThreadPool.globalInstance().start(worker)

        logging.debug(
            f"Rozpoczęto asynch. ładowanie dla {self.file_pair.get_base_name()} (worker_id: {worker_id})"
        )

    def _on_thumbnail_loaded(self, pixmap: QPixmap, path: str, width: int, height: int):
        """Obsługuje załadowaną miniaturę z ThumbnailGenerationWorker."""
        logging.debug(
            f"FileTileWidget: Otrzymano miniaturę dla {path} ({width}x{height})"
        )

        if pixmap and not pixmap.isNull():
            self.thumbnail_label.setPixmap(pixmap)
            self.original_thumbnail = pixmap

            # Aktualizuj kolor obwódki tylko jeśli jest wybrany kolor
            if self.file_pair:
                color_tag = self.file_pair.get_color_tag()
                if color_tag and color_tag.strip():
                    self._update_thumbnail_border_color(color_tag)
        else:
            # Fallback na ikonę błędu
            self._on_thumbnail_error("Otrzymano pustą miniaturę", path, width, height)

    def _on_thumbnail_error(self, error_msg: str, path: str, width: int, height: int):
        """Obsługuje błędy ładowania miniaturek."""
        logging.warning(f"FileTileWidget: Błąd ładowania miniatury {path}: {error_msg}")

        # Użyj ikony błędu z cache
        error_pixmap = ThumbnailCache.get_error_icon(width, height)
        if error_pixmap:
            self.thumbnail_label.setPixmap(error_pixmap)
            self.original_thumbnail = error_pixmap
        else:
            # Ostateczny fallback - tekst
            self.thumbnail_label.setText("Błąd ładowania")
            self.thumbnail_label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )  # --- Obsługa sygnałów z MetadataControlsWidget ---

    def _on_tile_selection_changed(self, is_selected: bool):
        """Handle tile selection change from MetadataControlsWidget checkbox."""
        logging.info(
            f"🔥 FileTileWidget._on_tile_selection_changed wywołane: {is_selected}"
        )
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
