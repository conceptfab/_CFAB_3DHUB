"""
Główne okno aplikacji.
"""

import logging
import math
import os
from collections import OrderedDict

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.logic import file_operations, metadata_manager
from src.logic.filter_logic import filter_file_pairs
from src.logic.scanner import scan_folder_for_pairs
from src.models.file_pair import FilePair
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.ui.widgets.preview_dialog import PreviewDialog


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji CFAB_3DHUB.
    """

    PREDEFINED_COLORS_FILTER = OrderedDict(
        [
            ("Wszystkie kolory", "ALL"),
            ("Brak koloru", "__NONE__"),
            ("Czerwony", "#E53935"),
            ("Zielony", "#43A047"),
            ("Niebieski", "#1E88E5"),
            ("Żółty", "#FDD835"),
            ("Fioletowy", "#8E24AA"),
            ("Czarny", "#000000"),
        ]
    )

    def __init__(self):
        """
        Inicjalizuje główne okno aplikacji.
        """
        super().__init__()

        self.current_working_directory = None
        self.all_file_pairs: list[FilePair] = []
        self.file_pairs_list: list[FilePair] = []
        self.file_tile_widgets = []

        # Konfiguracja rozmiaru miniatur
        self.default_thumbnail_size = (150, 150)  # Domyślny rozmiar (px)
        self.min_thumbnail_size = (50, 50)  # Minimalny rozmiar (px)
        self.max_thumbnail_size = (300, 300)  # Maksymalny rozmiar (px)
        self.current_thumbnail_size = self.default_thumbnail_size  # Aktualny

        # Konfiguracja okna
        self.setWindowTitle("CFAB_3DHUB")
        self.setMinimumSize(800, 600)

        # Centralny widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Główny layout
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # Inicjalizacja interfejsu użytkownika
        self._init_ui()
        # Domyślne kryteria filtrowania (wszystko pokazane)
        self.current_filter_criteria = {
            "show_favorites_only": False,
            "min_stars": 0,
            "required_color_tag": "ALL",  # Domyślnie "Wszystkie"
        }

        logging.info("Główne okno aplikacji zostało zainicjalizowane")

    def _init_ui(self):
        """
        Inicjalizuje elementy interfejsu użytkownika.
        """
        # Panel górny
        self.top_panel = QWidget()
        self.top_layout = QHBoxLayout(self.top_panel)
        self.top_layout.setContentsMargins(0, 0, 0, 0)

        # Przycisk wyboru folderu
        self.select_folder_button = QPushButton("Wybierz Folder Roboczy")
        self.select_folder_button.clicked.connect(self._select_working_directory)
        self.top_layout.addWidget(self.select_folder_button)

        # Panel kontroli rozmiaru
        self.size_control_panel = QWidget()
        self.size_control_layout = QHBoxLayout(self.size_control_panel)
        self.size_control_layout.setContentsMargins(0, 0, 0, 0)

        # Label dla suwaka
        self.size_label = QLabel("Rozmiar miniatur:")
        self.size_control_layout.addWidget(self.size_label)

        # Suwak rozmiaru miniatur
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(0)
        self.size_slider.setMaximum(100)
        self.size_slider.setValue(50)  # Domyślna wartość (średnia)
        self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.size_slider.setTickInterval(20)
        self.size_slider.valueChanged.connect(self._update_thumbnail_size)
        self.size_control_layout.addWidget(self.size_slider)

        # Dodanie do panelu górnego
        self.top_layout.addStretch(1)  # Elastyczny odstęp
        self.top_layout.addWidget(self.size_control_panel)

        # Dodanie panelu górnego do głównego layoutu
        self.main_layout.addWidget(self.top_panel)

        # --- Panel Filtrowania ---
        self.filter_panel = QGroupBox("Filtry")
        self.filter_panel_layout = QHBoxLayout(self.filter_panel)
        self.filter_panel_layout.setContentsMargins(5, 5, 5, 5)
        self.filter_panel_layout.setSpacing(10)

        self.filter_fav_checkbox = QCheckBox("Tylko ulubione")
        self.filter_fav_checkbox.stateChanged.connect(
            self._apply_filters_and_update_view
        )
        self.filter_panel_layout.addWidget(self.filter_fav_checkbox)

        self.filter_stars_label = QLabel("Min. gwiazdki:")
        self.filter_panel_layout.addWidget(self.filter_stars_label)
        self.filter_stars_combo = QComboBox()
        for i in range(6):  # 0 do 5 gwiazdek
            self.filter_stars_combo.addItem(f"{i} gwiazdek", userData=i)
        self.filter_stars_combo.currentIndexChanged.connect(
            self._apply_filters_and_update_view
        )
        self.filter_panel_layout.addWidget(self.filter_stars_combo)

        self.filter_color_label = QLabel("Tag koloru:")
        self.filter_panel_layout.addWidget(self.filter_color_label)

        self.filter_color_combo = QComboBox()
        for name, value in self.PREDEFINED_COLORS_FILTER.items():
            self.filter_color_combo.addItem(name, userData=value)
        self.filter_color_combo.currentIndexChanged.connect(
            self._apply_filters_and_update_view
        )
        self.filter_panel_layout.addWidget(self.filter_color_combo)

        self.filter_panel_layout.addStretch(1)
        self.main_layout.addWidget(self.filter_panel)
        self.filter_panel.setVisible(False)  # Ukryty na starcie
        # --- Koniec Panelu Filtrowania ---

        # Separator poziomy
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.main_layout.addWidget(separator)

        # Panel przewijany dla kafelków
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        # Kontener dla kafelków
        self.tiles_container = QWidget()
        self.tiles_layout = QGridLayout(self.tiles_container)
        self.tiles_layout.setContentsMargins(10, 10, 10, 10)
        self.tiles_layout.setSpacing(15)
        self.tiles_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )

        # Dodanie kontenera do obszaru przewijanego
        self.scroll_area.setWidget(self.tiles_container)

        # Dodanie obszaru przewijanego do głównego layoutu
        self.main_layout.addWidget(self.scroll_area)

        # Na początku ukrywamy panel kontroli rozmiaru (nie ma miniatur)
        self.size_control_panel.setVisible(False)

    def _select_working_directory(self):
        """
        Otwiera dialog wyboru folderu i inicjuje skanowanie.
        """
        logging.debug("Dialog wyboru folderu roboczego.")
        if self.current_working_directory:
            initial_dir = self.current_working_directory
        else:
            initial_dir = os.path.expanduser("~")

        directory = QFileDialog.getExistingDirectory(
            self, "Wybierz Folder Roboczy", initial_dir
        )

        if directory:
            self.current_working_directory = directory
            logging.info(f"Wybrano folder: {self.current_working_directory}")
            base_folder_name = os.path.basename(self.current_working_directory)
            self.setWindowTitle(f"CFAB_3DHUB - {base_folder_name}")

            try:
                # 1. Wczytaj wszystkie pary
                self.all_file_pairs = scan_folder_for_pairs(
                    self.current_working_directory
                )
                logging.info(f"Wczytano {len(self.all_file_pairs)} par.")

                # 2. Zastosuj metadane do wszystkich par
                metadata_manager.apply_metadata_to_file_pairs(
                    self.current_working_directory, self.all_file_pairs
                )

                # 3. Zastosuj filtry (początkowo domyślne) i odśwież widok
                self._apply_filters_and_update_view()

                # Pokaż panel filtrów i kontroli rozmiaru
                self.filter_panel.setVisible(True)
                is_gallery_populated = bool(self.file_pairs_list)
                self.size_control_panel.setVisible(is_gallery_populated)

                logging.info(f"Wyświetlono po filtracji: {len(self.file_pairs_list)}.")
            except Exception as e:
                err_msg = (
                    f"Błąd skanowania/inicjalizacji widoku "
                    f"'{base_folder_name}': {e}"
                )
                logging.error(err_msg)
                self.all_file_pairs = []
                self.file_pairs_list = []
                self._update_gallery_view()  # Wyczyść galerię
                self.filter_panel.setVisible(False)
        else:
            logging.info("Anulowano wybór folderu.")

    def _apply_filters_and_update_view(self):
        """Zbiera kryteria, filtruje pary i aktualizuje galerię."""
        if not self.all_file_pairs and not self.current_working_directory:
            # Nic nie rób, jeśli nie ma załadowanego folderu
            self.file_pairs_list = []
            self._clear_gallery()
            self.size_control_panel.setVisible(False)
            return

        show_fav = self.filter_fav_checkbox.isChecked()
        min_stars = self.filter_stars_combo.currentData()  # Pobiera userData (int)
        if min_stars is None:
            min_stars = 0  # Fallback

        req_color = self.filter_color_combo.currentData()
        if req_color is None:  # Fallback
            req_color = "ALL"

        self.current_filter_criteria = {
            "show_favorites_only": show_fav,
            "min_stars": min_stars,
            "required_color_tag": req_color,
        }
        logging.debug(f"Filtry: {self.current_filter_criteria}")

        self.file_pairs_list = filter_file_pairs(
            self.all_file_pairs, self.current_filter_criteria
        )
        is_gallery_populated_after_filter = bool(self.file_pairs_list)
        self.size_control_panel.setVisible(is_gallery_populated_after_filter)
        self._update_gallery_view()

    def _update_gallery_view(self):
        """
        Aktualizuje widok galerii, tworząc kafelki dla każdej pary plików.
        """
        # Wyczyść istniejące kafelki
        self._clear_gallery()

        if not self.file_pairs_list:
            logging.debug("Lista par pusta, galeria pusta.")
            # Ukryj panel kontroli rozmiaru, jeśli nie ma miniatur
            self.size_control_panel.setVisible(False)
            return

        # Pokaż panel kontroli rozmiaru, jeśli są miniatury do wyświetlenia
        self.size_control_panel.setVisible(True)

        try:
            # Zapisujemy szerokość kontenera do obliczeń liczby kolumn
            container_width = self.tiles_container.width()

            # Obliczamy liczbę kolumn na podstawie rozmiaru miniatury i szerokości kontenera
            # Dodajemy margines 30px na kafelek
            tile_width = self.current_thumbnail_size[0] + 30
            cols = max(1, math.floor(container_width / tile_width))

            # Tworzymy kafelki dla każdej pary plików i dodajemy je do siatki
            for idx, file_pair in enumerate(self.file_pairs_list):
                try:
                    # Utwórz nowy kafelek
                    tile = FileTileWidget(file_pair, self.current_thumbnail_size, self)

                    # MODIFICATION: Connect signals from FileTileWidget to MainWindow slots
                    tile.archive_open_requested.connect(self.open_archive)
                    tile.preview_image_requested.connect(self._show_preview_dialog)
                    tile.favorite_toggled.connect(self.toggle_favorite_status)
                    # Podłączenie nowych sygnałów
                    tile.stars_changed.connect(self._handle_stars_changed)
                    tile.color_tag_changed.connect(self._handle_color_tag_changed)

                    # Zapisz referencję do kafelka
                    self.file_tile_widgets.append(tile)

                    # Oblicz pozycję w siatce (wiersz, kolumna)
                    row = idx // cols
                    col = idx % cols

                    # Dodaj kafelek do siatki
                    self.tiles_layout.addWidget(tile, row, col)

                except Exception as e:
                    logging.error(
                        f"Błąd tworzenia kafelka dla "
                        f"{file_pair.get_base_name()[:25]}..: {e}"
                    )

        except Exception as e:
            logging.error(f"Błąd aktualizacji galerii: {e}")

    def _clear_gallery(self):
        """
        Czyści galerię kafelków.
        """
        # Usuń wszystkie widgety z layoutu
        while self.tiles_layout.count():
            item = self.tiles_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Wyczyść listę referencji do kafelków
        self.file_tile_widgets = []

    def _update_thumbnail_size(self, value):
        """
        Aktualizuje rozmiar miniatur na podstawie wartości suwaka.

        Args:
            value (int): Wartość suwaka (0-100)
        """
        # Obliczamy nowy rozmiar miniatury na podstawie wartości suwaka (0-100)
        # gdzie 0 = minimalny rozmiar, 100 = maksymalny rozmiar
        width_range = self.max_thumbnail_size[0] - self.min_thumbnail_size[0]
        height_range = self.max_thumbnail_size[1] - self.min_thumbnail_size[1]

        new_width = self.min_thumbnail_size[0] + (width_range * value / 100)
        new_height = self.min_thumbnail_size[1] + (height_range * value / 100)

        self.current_thumbnail_size = (int(new_width), int(new_height))
        thumb_size_str = (
            f"{self.current_thumbnail_size[0]}x{self.current_thumbnail_size[1]}"
        )

        # Aktualizacja rozmiaru wszystkich kafelków
        for tile in self.file_tile_widgets:
            try:
                tile.set_thumbnail_size(self.current_thumbnail_size)
            except Exception as e:
                logging.error(f"Błąd aktualizacji rozmiaru kafelka: {e}")

        logging.debug(f"Zaktualizowano rozmiar miniatur: {thumb_size_str}")

    def resizeEvent(self, event):
        """
        Obsługuje zdarzenie zmiany rozmiaru okna.
        """
        super().resizeEvent(event)

        # Aktualizuje układ kafelków po zmianie rozmiaru okna
        if self.file_pairs_list:
            self._update_gallery_view()

    def _save_metadata(self):
        """Zapisuje metadane dla wszystkich (nieprzefiltrowanych) par plików."""
        if self.current_working_directory and self.all_file_pairs:
            if not metadata_manager.save_metadata(
                self.current_working_directory, self.all_file_pairs
            ):
                logging.error("Nie udało się zapisać metadanych.")
        else:
            logging.debug("Brak folderu roboczego lub par plików do zapisu metadanych.")

    # MODIFICATION: Slot for archive_open_requested signal
    # This method might replace or be an update to an existing open_archive method
    def open_archive(self, file_pair: FilePair):
        """
        Otwiera plik archiwum w domyślnym programie systemu.

        Args:
            file_pair (FilePair): Para plików, której archiwum ma zostać otwarte.
        """
        if file_pair and file_pair.archive_path:
            logging.info(f"Żądanie otwarcia archiwum dla: {file_pair.get_base_name()}")
            file_operations.open_archive_externally(file_pair.archive_path)
        else:
            logging.warning(
                "Próba otwarcia archiwum dla nieprawidłowego FilePair lub braku ścieżki."
            )

    # MODIFICATION: New slot for preview_image_requested signal
    def _show_preview_dialog(self, file_pair: FilePair):
        """
        Wyświetla dialog z większym podglądem obrazu.

        Args:
            file_pair (FilePair): Para plików, dla której ma być wyświetlony podgląd.
        """
        if file_pair and file_pair.preview_path:
            logging.info(f"Żądanie podglądu obrazu dla: {file_pair.get_base_name()}")
            try:
                # Załaduj pełny obraz, a nie miniaturę z FilePair.preview_thumbnail
                pixmap = QPixmap(file_pair.preview_path)
                if pixmap.isNull():
                    logging.error(
                        f"Nie można załadować QPixmap dla podglądu: "
                        f"{file_pair.preview_path}"
                    )
                    # TODO: Można by tu wyświetlić QMessageBox z informacją dla użytkownika
                    return

                dialog = PreviewDialog(pixmap, self)
                dialog.exec()  # Użyj exec() dla modalnego dialogu
            except Exception as e:
                logging.error(
                    f"Błąd QPixmap/dialogu podglądu dla {file_pair.preview_path}: {e}"
                )
                # TODO: Można by tu wyświetlić QMessageBox z informacją dla użytkownika
        else:
            logging.warning(
                "Próba podglądu dla nieprawidłowego FilePair lub braku ścieżki."
            )

    # MODIFICATION: Slot for favorite_toggled signal
    # This method might replace or be an update to an existing toggle_favorite_status method
    def toggle_favorite_status(self, file_pair: FilePair):
        """Przełącza ulubione, zapisuje i odświeża (jeśli trzeba)."""
        if file_pair in self.all_file_pairs:
            file_pair.toggle_favorite()
            self._save_metadata()
            # Jeśli filtr ulubionych jest aktywny, zmiana może wpłynąć na widok
            if self.current_filter_criteria.get("show_favorites_only"):
                self._apply_filters_and_update_view()
        else:
            logging.warning("Toggle fav dla nieznanej pary.")

    # Nowe sloty obsługujące zmiany z kafelków
    def _handle_stars_changed(self, file_pair: FilePair, new_star_count: int):
        """Obsługuje zmianę gwiazdek, zapisuje i odświeża (jeśli trzeba)."""
        if file_pair in self.all_file_pairs:
            fp_name = file_pair.get_base_name()[:15]
            logging.debug(f"Stars: {fp_name}.. -> {new_star_count}")
            self._save_metadata()
            # Zmiana gwiazdek może wpłynąć na widoczność przy aktywnym filtrze
            min_stars_filter = self.current_filter_criteria.get("min_stars", 0)
            if min_stars_filter > 0:
                self._apply_filters_and_update_view()
        else:
            logging.warning("Zmiana gwiazdek dla nieznanej pary.")

    def _handle_color_tag_changed(self, file_pair: FilePair, new_color_tag: str):
        """Obsługuje zmianę koloru, zapisuje i odświeża (jeśli trzeba)."""
        if file_pair in self.all_file_pairs:
            fp_name = file_pair.get_base_name()[:15]
            logging.debug(f"Color: {fp_name}.. -> {new_color_tag}")
            self._save_metadata()
            # Zmiana koloru może wpłynąć na widoczność przy aktywnym filtrze
            color_filter = self.current_filter_criteria.get("required_color_tag", "ALL")
            if color_filter != "ALL":  # Jeśli jakikolwiek filtr koloru jest aktywny
                self._apply_filters_and_update_view()
        else:
            logging.warning("Zmiana koloru dla nieznanej pary.")
