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
from PyQt6.QtGui import QAction, QDesktopServices, QDrag, QPixmap
from PyQt6.QtWidgets import QHBoxLayout  # Dodaj QHBoxLayout
from PyQt6.QtWidgets import QVBoxLayout  # Upewnij się, że QVBoxLayout jest tutaj
from PyQt6.QtWidgets import QApplication, QFrame, QLabel, QMenu, QSizePolicy, QWidget

from src.models.file_pair import FilePair
from src.ui.widgets.metadata_controls_widget import (
    MetadataControlsWidget,
)  # NOWY IMPORT
from src.ui.widgets.thumbnail_cache import ThumbnailCache
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
        self._file_pair = file_pair  # Dodanie _file_pair jako alias dla file_pair
        self.thumbnail_size = default_thumbnail_size
        self.original_thumbnail: QPixmap | None = None

        # Wątek i worker do ładowania miniatur
        self.thumbnail_thread: QThread | None = None
        self.thumbnail_worker: ThumbnailLoaderWorker | None = None
        self._current_worker_id = 0  # Dodajemy identyfikator bieżącego workera

        # Ustawienie podstawowych właściwości widgetu
        self.setObjectName("FileTileWidget")
        self.setStyleSheet(
            """
            #FileTileWidget {
                background-color: #ffffff;
                border: 2px solid #999999;
                border-radius: 8px;
                padding: 0px;
            }
            #FileTileWidget:hover {
                background-color: #f0f7ff;
                border: 2px solid #4a90e2;
            }
        """
        )

        # Ustaw stały rozmiar całego kafelka
        self.setFixedSize(self.thumbnail_size[0], self.thumbnail_size[1])

        # Inicjalizacja UI
        self._init_ui()

        # Ustawienie danych tekstowych i metadanych (bez ładowania miniatury)
        self._update_static_data()

        # Asynchroniczne ładowanie miniatury
        self._load_thumbnail_async()

        # MODIFICATION: Install event filters for clickable labels
        self.thumbnail_label.installEventFilter(self)
        self.filename_label.installEventFilter(
            self
        )  # POPRAWKA: name_label -> filename_label

        # Ustawienie danych z FilePair
        self.update_data(file_pair)

    def _update_font_size(self):
        """Aktualizuje rozmiar czcionki w zależności od rozmiaru kafelka."""
        # Oblicz rozmiar czcionki na podstawie rozmiaru kafelka
        base_font_size = max(8, min(18, int(self.thumbnail_size[0] / 12)))  # 8-18px

        # Ustaw nowy stylesheet z dynamicznym rozmiarem czcionki
        # Używamy jasno szarego koloru dla dobrej widoczności na ciemnym tle
        self.filename_label.setStyleSheet(
            f"""
            QLabel {{
                color: #E0E0E0;
                font-weight: bold;
                font-size: {base_font_size}px;
                padding: 2px;
                border-radius: 2px;
                background-color: transparent;
            }}
            QLabel:hover {{
                color: #FFFFFF;
                font-weight: bold;
                text-decoration: underline;
                background-color: transparent;
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
        self.thumbnail_frame.setStyleSheet(
            """
            QFrame {
                border: none;
                padding: 0px;
                background-color: transparent;
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

        # Dodanie efektu hover dla miniatury
        self.thumbnail_label.setStyleSheet(
            """
            QLabel {
                background-color: transparent;
            }
            QLabel:hover {
                opacity: 0.9;
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
        # Dodanie stylu dla efektu hover - wyraźniejszy
        # Używamy jasno szarego koloru dla dobrej widoczności na ciemnym tle
        self.filename_label.setStyleSheet(
            """
            QLabel {
                color: #E0E0E0;
                font-weight: bold;
                padding: 2px;
                border-radius: 2px;
                background-color: transparent;
            }
            QLabel:hover {
                color: #FFFFFF;
                font-weight: bold;
                text-decoration: underline;
                background-color: transparent;
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
        self.metadata_controls.favorite_status_changed.connect(
            self._on_favorite_changed
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
                self.metadata_controls.update_favorite_display(
                    self.file_pair.is_favorite_file()
                )
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
                self.metadata_controls.update_favorite_display(False)
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
            # Widoczna kolorowa obwódka tylko gdy wybrany kolor
            self.thumbnail_frame.setStyleSheet(
                f"""
                QFrame {{
                    border: 6px solid {color_hex};
                    border-radius: 6px;
                    padding: 0px;
                    background-color: transparent;
                }}
            """
            )
            logging.debug(f"Ustawiono kolor obwódki na: {color_hex}")
        else:
            # Brak kolorowej obwódki - całkowicie przezroczysta
            self.thumbnail_frame.setStyleSheet(
                """
                QFrame {
                    border: none;
                    padding: 0px;
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
            self.filename_label.setText(self._file_pair.get_display_name())
            self.setToolTip(f"Ścieżka: {self._file_pair.get_primary_file_path()}")
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

        self._current_worker = None  # Zresetuj referencję do workera

    # --- Obsługa sygnałów z MetadataControlsWidget ---
    def _on_favorite_changed(self, is_favorite: bool):
        if self._file_pair:
            self._file_pair.set_favorite_file(is_favorite)
            # Odśwież tylko kontrolki metadanych, aby uniknąć ponownego ładowania miniatury
            self.metadata_controls.update_favorite_display(is_favorite)
            self.file_pair_updated.emit(self._file_pair)
            logging.debug(
                f"FileTileWidget: Zmieniono status ulubionych dla {self._file_pair.get_display_name()} na {is_favorite}"
            )

    def _on_stars_changed(self, stars: int):
        if self._file_pair:
            self._file_pair.set_stars(stars)
            self.metadata_controls.update_stars_display(stars)
            self.file_pair_updated.emit(self._file_pair)
            logging.debug(
                f"FileTileWidget: Zmieniono liczbę gwiazdek dla {self._file_pair.get_display_name()} na {stars}"
            )

    def _on_color_tag_changed(self, color_hex: str):
        if self._file_pair:
            self._file_pair.set_color_tag(color_hex)
            # Odśwież kontrolki metadanych i ramkę miniatury
            self.metadata_controls.update_color_tag_display(color_hex)
            self._update_thumbnail_border_color(color_hex)

            # Emituj sygnał, że tag koloru został zmieniony
            self.color_tag_changed.emit(self._file_pair, color_hex)
            self.file_pair_updated.emit(self._file_pair)

            logging.debug(
                f"FileTileWidget: Zmieniono tag koloru dla {self._file_pair.get_display_name()} na {color_hex}"
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
        action_favorite = menu.addAction("Dodaj do ulubionych")
        action_remove_favorite = menu.addAction("Usuń z ulubionych")
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
        action_favorite.triggered.connect(self.add_to_favorites)
        action_remove_favorite.triggered.connect(self.remove_from_favorites)
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
