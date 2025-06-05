"""
Główne okno aplikacji.
"""

import logging
import math
import os

from PyQt6.QtCore import QDir, QObject, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QFileSystemModel, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QTabWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from src import app_config
from src.logic import file_operations, metadata_manager
from src.logic.filter_logic import filter_file_pairs
from src.logic.scanner import scan_folder_for_pairs
from src.models.file_pair import FilePair
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.ui.widgets.preview_dialog import PreviewDialog


class ScanFolderWorker(QObject):
    """
    Worker do skanowania folderu w osobnym wątku.
    """

    # Sygnał emitowany po zakończeniu:
    # found_pairs, unpaired_archives, unpaired_previews
    finished = pyqtSignal(list, list, list)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.directory_to_scan = None

    def run(self):
        """
        Wykonuje skanowanie folderu.
        """
        if not self.directory_to_scan:
            self.error.emit("Nie określono folderu do skanowania.")
            return

        try:
            logging.debug(
                f"Rozpoczynanie skanowania folderu: "
                f"{self.directory_to_scan} w wątku."
            )
            found_pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
                self.directory_to_scan
            )
            self.finished.emit(found_pairs, unpaired_archives, unpaired_previews)
        except Exception as e:
            err_msg = (
                f"Błąd podczas skanowania folderu "
                f"'{self.directory_to_scan}' w wątku: {e}"
            )
            logging.error(err_msg)
            self.error.emit(err_msg)


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji CFAB_3DHUB.
    """

    def __init__(self):
        """
        Inicjalizuje główne okno aplikacji.
        """
        super().__init__()

        self.current_working_directory = None
        self.all_file_pairs: list[FilePair] = []
        self.unpaired_archives: list[str] = []
        self.unpaired_previews: list[str] = []
        self.file_pairs_list: list[FilePair] = []
        self.gallery_tile_widgets: dict[str, FileTileWidget] = {}

        # Wątek skanowania
        self.scan_thread = None
        self.scan_worker = None

        # Konfiguracja rozmiaru miniatur - teraz z app_config
        self.min_thumbnail_size = app_config.MIN_THUMBNAIL_SIZE
        self.max_thumbnail_size = app_config.MAX_THUMBNAIL_SIZE
        self.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE

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
        self.top_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
        self.top_layout = QHBoxLayout(self.top_panel)
        self.top_layout.setContentsMargins(0, 0, 0, 0)

        # Przycisk wyboru folderu
        self.select_folder_button = QPushButton("Wybierz Folder Roboczy")
        self.select_folder_button.clicked.connect(self._select_working_directory)
        self.top_layout.addWidget(self.select_folder_button)

        # Panel kontroli rozmiaru
        self.size_control_panel = QWidget()
        self.size_control_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
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
        self.top_layout.addWidget(
            self.size_control_panel
        )  # Dodanie panelu górnego do głównego layoutu
        self.main_layout.addWidget(self.top_panel)
        self.top_panel.setMaximumHeight(
            self.top_panel.sizeHint().height()
        )  # --- Panel Filtrowania ---
        self.filter_panel = QGroupBox("Filtry")
        self.filter_panel.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )
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
        # Użycie PREDEFINED_COLORS_FILTER z app_config
        for name, value in app_config.PREDEFINED_COLORS_FILTER.items():
            self.filter_color_combo.addItem(name, userData=value)
        self.filter_color_combo.currentIndexChanged.connect(
            self._apply_filters_and_update_view
        )
        self.filter_panel_layout.addWidget(self.filter_color_combo)
        self.filter_panel_layout.addStretch(1)
        self.main_layout.addWidget(self.filter_panel)
        self.filter_panel.setMaximumHeight(self.filter_panel.sizeHint().height())
        self.filter_panel.setVisible(False)  # Ukryty na starcie
        # --- Koniec Panelu Filtrowania ---

        # --- TabWidget jako główny kontener widoków ---
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # === Zakładka 1: Galeria ===
        self.gallery_tab = QWidget()
        self.gallery_tab_layout = QVBoxLayout(self.gallery_tab)
        self.gallery_tab_layout.setContentsMargins(
            0, 0, 0, 0
        )  # Bez marginesów wew. zakładki

        # Istniejący splitter dla drzewa i kafelków
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.folder_tree = QTreeView()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setMinimumWidth(200)
        self.folder_tree.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(
            self._show_folder_context_menu
        )
        self.file_system_model = QFileSystemModel()
        self.file_system_model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot)
        self.folder_tree.setModel(self.file_system_model)
        self.folder_tree.clicked.connect(self._folder_tree_item_clicked)
        for col in range(1, 4):
            self.folder_tree.setColumnHidden(col, True)
        self.splitter.addWidget(self.folder_tree)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.tiles_container = QWidget()
        self.tiles_layout = QGridLayout(self.tiles_container)
        self.tiles_layout.setContentsMargins(10, 10, 10, 10)
        self.tiles_layout.setSpacing(15)
        self.tiles_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.scroll_area.setWidget(self.tiles_container)
        self.splitter.addWidget(self.scroll_area)
        self.splitter.setSizes([300, 700])

        self.gallery_tab_layout.addWidget(
            self.splitter
        )  # Dodanie splittera do layoutu zakładki
        self.tab_widget.addTab(self.gallery_tab, "Galeria")

        # === Zakładka 2: Niesparowane Pliki ===
        self.unpaired_files_tab = QWidget()
        self.unpaired_files_layout = QVBoxLayout(self.unpaired_files_tab)
        self.unpaired_files_layout.setContentsMargins(5, 5, 5, 5)

        # Splitter dla dwóch list
        self.unpaired_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Panel dla listy niesparowanych archiwów
        self.unpaired_archives_panel = QWidget()
        self.unpaired_archives_panel_layout = QVBoxLayout(self.unpaired_archives_panel)
        self.unpaired_archives_label = QLabel("Niesparowane Archiwa:")
        self.unpaired_archives_list_widget = QListWidget()
        self.unpaired_archives_list_widget.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )
        self.unpaired_archives_panel_layout.addWidget(self.unpaired_archives_label)
        self.unpaired_archives_panel_layout.addWidget(
            self.unpaired_archives_list_widget
        )
        self.unpaired_splitter.addWidget(self.unpaired_archives_panel)

        # Panel dla listy niesparowanych podglądów
        self.unpaired_previews_panel = QWidget()
        self.unpaired_previews_panel_layout = QVBoxLayout(self.unpaired_previews_panel)
        self.unpaired_previews_label = QLabel("Niesparowane Podglądy:")
        self.unpaired_previews_list_widget = QListWidget()
        self.unpaired_previews_list_widget.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )
        self.unpaired_previews_panel_layout.addWidget(self.unpaired_previews_label)
        self.unpaired_previews_panel_layout.addWidget(
            self.unpaired_previews_list_widget
        )
        self.unpaired_splitter.addWidget(self.unpaired_previews_panel)

        self.unpaired_files_layout.addWidget(self.unpaired_splitter)

        # Przycisk do ręcznego parowania
        self.pair_manually_button = QPushButton("Sparuj Wybrane")
        self.pair_manually_button.clicked.connect(self._handle_manual_pairing)
        self.pair_manually_button.setEnabled(False)
        self.unpaired_files_layout.addWidget(
            self.pair_manually_button, alignment=Qt.AlignmentFlag.AlignCenter
        )

        # Podłączenie sygnałów zmiany zaznaczenia na listach
        self.unpaired_archives_list_widget.itemSelectionChanged.connect(
            self._update_pair_button_state
        )
        self.unpaired_previews_list_widget.itemSelectionChanged.connect(
            self._update_pair_button_state
        )

        self.tab_widget.addTab(self.unpaired_files_tab, "Niesparowane Pliki")
        self.tab_widget.setTabVisible(1, False)

    def _select_working_directory(self):
        """
        Otwiera dialog wyboru folderu i inicjuje asynchroniczne skanowanie.
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

            # Wyłącz przycisk i zmień tekst na czas skanowania
            self.select_folder_button.setEnabled(False)
            self.select_folder_button.setText("Skanowanie...")
            # Wyczyść poprzednie dane przed nowym skanowaniem
            self._clear_all_data_and_views()

            # Przygotowanie i uruchomienie wątku skanującego
            if self.scan_thread and self.scan_thread.isRunning():
                logging.warning("Poprzedni wątek skanowania wciąż aktywny. Czekanie...")
                self.select_folder_button.setText("Wybierz Folder Roboczy")
                self.select_folder_button.setEnabled(True)
                QMessageBox.warning(
                    self,
                    "Skanowanie w toku",
                    "Poprzednia operacja skanowania folderu jeszcze się nie zakończyła.",
                )
                return

            self.scan_thread = QThread(self)
            self.scan_worker = ScanFolderWorker()
            self.scan_worker.directory_to_scan = self.current_working_directory
            self.scan_worker.moveToThread(self.scan_thread)

            # Połączenie sygnałów
            self.scan_worker.finished.connect(self._handle_scan_finished)
            self.scan_worker.error.connect(self._handle_scan_error)
            self.scan_thread.started.connect(self.scan_worker.run)
            # Sprzątanie po zakończeniu wątku
            self.scan_worker.finished.connect(self.scan_thread.quit)
            self.scan_worker.error.connect(self.scan_thread.quit)
            self.scan_thread.finished.connect(self.scan_thread.deleteLater)
            self.scan_worker.finished.connect(
                self.scan_worker.deleteLater
            )  # Worker też
            self.scan_worker.error.connect(self.scan_worker.deleteLater)  # Worker też

            self.scan_thread.start()
            logging.info(
                f"Uruchomiono wątek skanowania dla: {self.current_working_directory}"
            )

        else:
            logging.info("Anulowano wybór folderu.")

    def _clear_all_data_and_views(self):
        """Czyści wszystkie dane plików i odpowiednie widoki, w tym galerię."""
        self.all_file_pairs = []
        self.unpaired_archives = []
        self.unpaired_previews = []
        self.file_pairs_list = []
        self._clear_gallery()
        self._clear_unpaired_files_lists()
        self.filter_panel.setVisible(False)
        self.tab_widget.setTabVisible(1, False)  # Ukryj zakładkę niesparowanych
        self.setWindowTitle("CFAB_3DHUB")  # Reset tytułu okna

    def _clear_unpaired_files_lists(self):
        """Czyści listy niesparowanych plików w interfejsie użytkownika."""
        self.unpaired_archives_list_widget.clear()
        self.unpaired_previews_list_widget.clear()
        logging.debug("Wyczyszczono listy niesparowanych plików w UI.")

    def _handle_scan_finished(self, found_pairs, unpaired_archives, unpaired_previews):
        """
        Obsługuje wyniki pomyślnie zakończonego skanowania folderu.
        Tworzy wszystkie widgety kafelków, ale ich nie wyświetla.
        """
        logging.info(
            f"Skanowanie folderu {self.current_working_directory} "
            f"zakończone pomyślnie."
        )
        self.all_file_pairs = found_pairs
        self.unpaired_archives = unpaired_archives
        self.unpaired_previews = unpaired_previews

        logging.info(f"Wczytano {len(self.all_file_pairs)} sparowanych plików.")
        logging.info(
            f"Niesparowane: {len(self.unpaired_archives)} archiwów, "
            f"{len(self.unpaired_previews)} podglądów."
        )

        # 1. Wyczyść poprzednie widgety kafelków całkowicie
        self._clear_gallery()

        # 2. Stwórz nowe widgety kafelków dla wszystkich znalezionych par
        #    ale nie dodawaj ich jeszcze do layoutu i ustaw jako niewidoczne.
        if self.all_file_pairs:
            for file_pair in self.all_file_pairs:
                try:
                    tile = FileTileWidget(file_pair, self.current_thumbnail_size, self)
                    # Podłączanie sygnałów dla nowo utworzonego kafelka
                    tile.archive_open_requested.connect(self.open_archive)
                    tile.preview_image_requested.connect(self._show_preview_dialog)
                    tile.favorite_toggled.connect(self.toggle_favorite_status)
                    tile.stars_changed.connect(self._handle_stars_changed)
                    tile.color_tag_changed.connect(self._handle_color_tag_changed)
                    tile.tile_context_menu_requested.connect(
                        self._show_file_context_menu
                    )

                    tile.setVisible(False)  # Ukryj na starcie
                    self.gallery_tile_widgets[file_pair.get_archive_path()] = tile
                except Exception as e:
                    logging.error(
                        f"Błąd tworzenia kafelka dla {file_pair.get_base_name()}: {e}"
                    )

        # 3. Zastosuj metadane do wszystkich sparowanych par
        if self.all_file_pairs:
                metadata_manager.apply_metadata_to_file_pairs(
                    self.current_working_directory, self.all_file_pairs
                )

        # 4. Zastosuj filtry (początkowo domyślne) i odśwież widok (teraz tylko pokaże/ukryje)
                self._apply_filters_and_update_view()
        self._update_unpaired_files_lists()

                # Pokaż panel filtrów i kontroli rozmiaru
                self.filter_panel.setVisible(True)
                is_gallery_populated = bool(self.file_pairs_list)
                self.size_control_panel.setVisible(is_gallery_populated)
        self.tab_widget.setTabVisible(
            1, bool(self.unpaired_archives or self.unpaired_previews)
        )

        # Inicjalizacja drzewa katalogów - powinna być tutaj, po załadowaniu danych
        self._init_directory_tree()

        # Przywróć przycisk
        self.select_folder_button.setText("Wybierz Folder Roboczy")
        self.select_folder_button.setEnabled(True)

        # Zapisz metadane
        self._save_metadata()

        logging.info(
            f"Widok zaktualizowany. Wyświetlono po filtracji: "
            f"{len(self.file_pairs_list)}."
        )

    def _handle_scan_error(self, error_message: str):
        """
        Obsługuje błędy występujące podczas skanowania folderu.
        """
        logging.error(f"Błąd skanowania: {error_message}")
        QMessageBox.critical(
            self,
            "Błąd Skanowania",
            f"Wystąpił błąd podczas skanowania folderu:\n{error_message}",
        )

        self._clear_all_data_and_views()  # Wyczyść dane i widoki

        # Przywróć przycisk
        self.select_folder_button.setText("Wybierz Folder Roboczy")
        self.select_folder_button.setEnabled(True)
        # Ukryj panel filtrów
                self.filter_panel.setVisible(False)

    def _apply_filters_and_update_view(self):
        """Zbiera kryteria, filtruje pary i aktualizuje galerię (pokazuje/ukrywa kafelki)."""
        if not self.current_working_directory:
            # Jeśli nie ma folderu, upewnij się, że wszystko jest czyste
            self.file_pairs_list = []
            # _update_gallery_view sobie poradzi z pustą listą
            self._update_gallery_view()
            self.size_control_panel.setVisible(False)
            self.filter_panel.setVisible(False)
            return

        # Jeśli self.all_file_pairs jest puste, ale mamy folder (np. pusty folder)
        # również chcemy poprawnie zaktualizować UI
        if not self.all_file_pairs:
            self.file_pairs_list = []
            self._update_gallery_view()
            self.size_control_panel.setVisible(False)
            # Panel filtrów może pozostać, jeśli jest sens (np. użytkownik wybrał pusty folder)
            # self.filter_panel.setVisible(True lub False w zależności od logiki)
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
        Aktualizuje widok galerii, pokazując/ukrywając istniejące kafelki
        i rozmieszczając je w siatce.
        """
        # 1. Usuń wszystkie widgety z layoutu (ale nie z pamięci/słownika)
        while self.tiles_layout.count():
            item = self.tiles_layout.takeAt(0)
            widget = item.widget()
            if widget:  # Widget może być None, jeśli to był QSpacerItem
                # Nie usuwamy widgetu (deleteLater), tylko zdejmujemy z layoutu
                widget.setParent(None)

        if not self.file_pairs_list:  # file_pairs_list to przefiltrowane pary
            logging.debug("Lista par (po filtracji) pusta, galeria pusta.")
            self.size_control_panel.setVisible(False)
            return

        self.size_control_panel.setVisible(True)

        try:
            container_width = self.tiles_container.width()
            tile_width_with_spacing = (
                self.current_thumbnail_size[0] + self.tiles_layout.spacing() + 10
            )  # Dodatkowy bufor
            cols = max(1, math.floor(container_width / tile_width_with_spacing))

            row, col = 0, 0
            for (
                file_pair
            ) in self.file_pairs_list:  # Iterujemy po przefiltrowanej liście
                tile = self.gallery_tile_widgets.get(file_pair.get_archive_path())
                if tile:
                    tile.setVisible(True)  # Upewnij się, że jest widoczny
                    self.tiles_layout.addWidget(tile, row, col)
                    col += 1
                    if col >= cols:
                        col = 0
                        row += 1
                else:
                    logging.warning(
                        f"Nie znaleziono widgetu kafelka dla {file_pair.get_archive_path()} w słowniku."
                    )

            # Ukryj widgety, które nie są na liście file_pairs_list
            # (te, które zostały odfiltrowane)
            # To jest mniej wydajne niż wcześniejsze ukrycie wszystkich
            # i pokazanie tylko potrzebnych, ale bardziej bezpośrednie.
            # Lepsze podejście: na początku _update_gallery_view ukryć wszystkie, potem pokazać te z file_pairs_list.
            # Zmienimy to w kolejnym kroku jeśli będzie taka potrzeba.
            # Na razie, dla bezpieczeństwa, iterujemy po wszystkich przechowywanych.
            for archive_path, tile_widget in self.gallery_tile_widgets.items():
                # Sprawdź, czy file_pair dla tego widgetu jest na liście do wyświetlenia
                # To wymaga znalezienia file_pair po archive_path w self.file_pairs_list
                # To jest nieefektywne. Prostsze: jeśli tile nie został dodany w pętli powyżej, to ukryj.
                # Zakładając, że layout prawidłowo zarządza widgetami, które nie zostały dodane,
                # wystarczy ustawić setVisible(False) dla tych, które nie są w self.file_pairs_list
                # Lepsze: if tile_widget.file_pair not in self.file_pairs_list: tile_widget.setVisible(False)

                # Bardziej bezpośrednie podejście: jeśli widget nie był w pętli powyżej, a jest widoczny, ukryj.
                # LUB: Ustawiamy wszystkie na False, a potem te z file_pairs_list na True.
                # Zostawiam obecną logikę, gdzie dodajemy tylko te co trzeba.
                # Te, które nie zostały dodane do layoutu, a były wcześniej, zostały usunięte z layoutu na początku.
                # Musimy tylko upewnić się, że są `setVisible(False)` jeśli nie są w `file_pairs_list`.
                # Poniższa pętla to robi.
                is_visible_pair = any(
                    fp.get_archive_path() == archive_path for fp in self.file_pairs_list
                )
                if not is_visible_pair and tile_widget.isVisible():
                    tile_widget.setVisible(False)
                elif (
                    is_visible_pair and not tile_widget.isVisible()
                ):  # Na wypadek gdyby był ukryty
                    tile_widget.setVisible(True)

        except Exception as e:
            logging.error(f"Błąd aktualizacji widoku galerii: {e}")

    def _clear_gallery(self):
        """
        Czyści galerię kafelków - usuwa wszystkie widgety z pamięci.
        """
        # Usuń wszystkie widgety z layoutu
        while self.tiles_layout.count():
            item = self.tiles_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)  # Usuń rodzica przed deleteLater
                widget.deleteLater()

        # Usuń pozostałe widgety ze słownika, jeśli jakieś nie były w layoucie
        for tile in self.gallery_tile_widgets.values():
            tile.deleteLater()
        self.gallery_tile_widgets.clear()

    def _update_thumbnail_size(self, value):
        """
        Aktualizuje rozmiar miniatur na podstawie wartości suwaka.
        """
        # Użycie MIN_THUMBNAIL_SIZE i MAX_THUMBNAIL_SIZE z app_config
        # (poprzez self.min_thumbnail_size i self.max_thumbnail_size)
        width_range = self.max_thumbnail_size[0] - self.min_thumbnail_size[0]
        height_range = self.max_thumbnail_size[1] - self.min_thumbnail_size[1]

        new_width = self.min_thumbnail_size[0] + (width_range * value / 100)
        new_height = self.min_thumbnail_size[1] + (height_range * value / 100)

        self.current_thumbnail_size = (int(new_width), int(new_height))
        thumb_size_str = (
            f"{self.current_thumbnail_size[0]}x{self.current_thumbnail_size[1]}"
        )

        # Aktualizacja rozmiaru wszystkich istniejących kafelków
        # Iterujemy po wartościach słownika gallery_tile_widgets
        for tile in self.gallery_tile_widgets.values():
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
        """Zapisuje metadane dla wszystkich (nieprzefiltrowanych) par plików oraz listy niesparowanych."""
        if (
            self.current_working_directory
        ):  # Sprawdzamy tylko folder, bo mogą być tylko niesparowane
            if not metadata_manager.save_metadata(
                self.current_working_directory,
                self.all_file_pairs,
                self.unpaired_archives,
                self.unpaired_previews,
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
                "Próba otwarcia archiwum dla nieprawidłowego FilePair "
                "lub braku ścieżki."
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

    def _init_directory_tree(self):
        """
        Inicjalizuje drzewo katalogów po wyborze folderu roboczego.
        """
        if not self.current_working_directory:
            return

        # Ustaw root dla QFileSystemModel na wybrany folder
        self.file_system_model.setRootPath(self.current_working_directory)

        # Ustaw widoczny folder dla QTreeView
        root_index = self.file_system_model.index(self.current_working_directory)
        self.folder_tree.setRootIndex(root_index)

        # Rozwiń pierwszy poziom drzewa
        self.folder_tree.expandToDepth(0)

        # Włącz akceptowanie drop dla drzewa
        self.folder_tree.setAcceptDrops(True)
        self.folder_tree.setDragDropMode(QTreeView.DragDropMode.DropOnly)

    def _show_folder_context_menu(self, position):
        """
        Wyświetla menu kontekstowe dla drzewa folderów.
        """
        # Pobierz indeks wybranego elementu
        index = self.folder_tree.indexAt(position)
        if not index.isValid():
            return

        # Pobierz ścieżkę do wybranego folderu
        folder_path = self.file_system_model.filePath(index)

        # Tworzenie menu kontekstowego
        context_menu = QMenu()

        # Dodanie akcji do menu
        create_folder_action = QAction("Nowy folder", self)
        rename_folder_action = QAction("Zmień nazwę", self)
        delete_folder_action = QAction("Usuń folder", self)

        # Dodanie akcji do menu
        context_menu.addAction(create_folder_action)
        context_menu.addAction(rename_folder_action)
        context_menu.addSeparator()
        context_menu.addAction(delete_folder_action)

        # Połączenie akcji z metodami
        create_folder_action.triggered.connect(lambda: self._create_folder(folder_path))
        rename_folder_action.triggered.connect(lambda: self._rename_folder(folder_path))
        delete_folder_action.triggered.connect(lambda: self._delete_folder(folder_path))

        # Wyświetlenie menu
        context_menu.exec(self.folder_tree.mapToGlobal(position))

    def _create_folder(self, parent_folder_path):
        """
        Tworzy nowy folder w wybranej lokalizacji.
        """
        folder_name, ok = QInputDialog.getText(
            self, "Nowy folder", "Podaj nazwę folderu:"
        )

        if ok and folder_name:
            created_path = file_operations.create_folder(
                parent_folder_path, folder_name
            )
            if created_path:
                logging.info(f"Utworzono folder: {created_path}")
                # Odświeżenie widoku drzewa
                self.file_system_model.refresh()
            else:
                QMessageBox.warning(
                    self,
                    "Błąd tworzenia folderu",
                    f"Nie udało się utworzyć folderu '{folder_name}' w '{parent_folder_path}'.",
                    QMessageBox.StandardButton.Ok,
                )

    def _rename_folder(self, folder_path):
        """
        Zmienia nazwę wybranego folderu.
        """
        old_name = os.path.basename(folder_path)
        new_name, ok = QInputDialog.getText(
            self, "Zmień nazwę folderu", "Podaj nową nazwę folderu:", text=old_name
        )

        if ok and new_name and new_name != old_name:
            new_path = file_operations.rename_folder(folder_path, new_name)
            if new_path:
                logging.info(
                    f"Zmieniono nazwę folderu z '{folder_path}' na '{new_path}'"
                )
                # Odświeżenie widoku drzewa
                self.file_system_model.refresh()
            else:
                QMessageBox.warning(
                    self,
                    "Błąd zmiany nazwy",
                    f"Nie udało się zmienić nazwy folderu '{old_name}' na '{new_name}'.",
                    QMessageBox.StandardButton.Ok,
                )

    def _delete_folder(self, folder_path):
        """
        Usuwa wybrany folder po potwierdzeniu przez użytkownika.
        """
        folder_name = os.path.basename(folder_path)

        # Sprawdź czy folder nie jest folderem roboczym
        if os.path.samefile(folder_path, self.current_working_directory):
            QMessageBox.warning(
                self,
                "Nie można usunąć folderu",
                "Nie można usunąć głównego folderu roboczego.",
                QMessageBox.StandardButton.Ok,
            )
            return

        # Pobierz listę plików w folderze
        try:
            has_content = len(os.listdir(folder_path)) > 0
        except Exception:
            has_content = True  # W przypadku błędu, zakładamy, że folder ma zawartość

        # Treść komunikatu potwierdzenia
        if has_content:
            message = (
                f"Czy na pewno chcesz usunąć folder '{folder_name}' i całą jego zawartość?\n"
                "Ta operacja jest nieodwracalna!"
            )
            delete_content = True
        else:
            message = f"Czy na pewno chcesz usunąć pusty folder '{folder_name}'?"
            delete_content = False

        # Potwierdzenie od użytkownika
        reply = QMessageBox.question(
            self,
            "Potwierdź usunięcie",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            success = file_operations.delete_folder(folder_path, delete_content)
            if success:
                logging.info(f"Usunięto folder: {folder_path}")
                # Odświeżenie widoku drzewa
                self.file_system_model.refresh()

                # Jeśli usunęliśmy folder, który miał pliki w naszej kolekcji,
                # należy zaktualizować wszystkie pary i widok
                self._refresh_file_pairs_after_folder_operation()
            else:
                QMessageBox.warning(
                    self,
                    "Błąd usuwania folderu",
                    f"Nie udało się usunąć folderu '{folder_name}'.",
                    QMessageBox.StandardButton.Ok,
                )

    def _refresh_file_pairs_after_folder_operation(self):
        """
        Odświeża listę par plików po operacjach na folderach.
        """
        if not self.current_working_directory:
            logging.warning("Brak bieżącego folderu roboczego do odświeżenia.")
            return

        # Zapisz aktualne ustawienia filtrów
        current_filters = (
            self.current_filter_criteria.copy()
            if hasattr(self, "current_filter_criteria")
            else {}
        )

        # Skanuj folder na nowo
        found_pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
            self.current_working_directory
        )
        self.all_file_pairs = found_pairs
        self.unpaired_archives = unpaired_archives
        self.unpaired_previews = unpaired_previews

        logging.info(f"Odświeżono: {len(self.all_file_pairs)} sparowanych plików.")
        logging.info(
            f"Niesparowane: {len(self.unpaired_archives)} archiwów, "
            f"{len(self.unpaired_previews)} podglądów."
        )

        # Załaduj metadane
        if self.all_file_pairs:
        metadata_manager.apply_metadata_to_file_pairs(
            self.current_working_directory, self.all_file_pairs
        )

        # Zastosuj filtry i zaktualizuj widok
        if current_filters:
            self.current_filter_criteria = current_filters
            self.file_pairs_list = filter_file_pairs(
                self.all_file_pairs, self.current_filter_criteria
            )
            self._update_gallery_view()
        else:
            self._apply_filters_and_update_view()

    def _folder_tree_item_clicked(self, index):
        """
        Obsługuje kliknięcie folderu w drzewie katalogów.
        Ustawia kliknięty folder jako nowy folder roboczy i odświeża stan aplikacji.
        """
        if not index.isValid():
            return

        folder_path = self.file_system_model.filePath(index)

        if folder_path == self.current_working_directory:
            logging.debug(f"Kliknięto ten sam folder: {folder_path}. Nie odświeżam.")
            return

        logging.info(f"Wybrano folder z drzewa: {folder_path}")

        # Ustaw nowy folder roboczy i wykonaj pełne odświeżenie
        # (tak jak w _select_working_directory)
        self.current_working_directory = folder_path
        base_folder_name = os.path.basename(self.current_working_directory)
        self.setWindowTitle(f"CFAB_3DHUB - {base_folder_name}")

        try:
            # Nie ma potrzeby ponownie inicjalizować drzewa, jeśli już istnieje
            # self._init_directory_tree() # Można rozważyć, jeśli drzewo ma się zmieniać dynamicznie

            # Wczytaj wszystkie pary i niesparowane pliki
            found_pairs, unpaired_archives, unpaired_previews = scan_folder_for_pairs(
                self.current_working_directory
            )
            self.all_file_pairs = found_pairs
            self.unpaired_archives = unpaired_archives
            self.unpaired_previews = unpaired_previews

            logging.info(
                f"Wczytano {len(self.all_file_pairs)} sparowanych plików z drzewa."
            )
            logging.info(
                f"Niesparowane (drzewo): {len(self.unpaired_archives)} archiwów, "
                f"{len(self.unpaired_previews)} podglądów."
            )

            # Zastosuj metadane do wszystkich sparowanych par
            if self.all_file_pairs:
                metadata_manager.apply_metadata_to_file_pairs(
                    self.current_working_directory, self.all_file_pairs
                )

            # Zastosuj filtry i odśwież widok
            self._apply_filters_and_update_view()

            # Pokaż panel filtrów i kontroli rozmiaru
            self.filter_panel.setVisible(True)
            is_gallery_populated = bool(self.file_pairs_list)
            self.size_control_panel.setVisible(is_gallery_populated)

            logging.info(
                f"Wyświetlono po filtracji (z drzewa): {len(self.file_pairs_list)}."
            )

        except Exception as e:
            err_msg = (
                f"Błąd skanowania/inicjalizacji widoku "
                f"po kliknięciu w drzewie '{base_folder_name}': {e}"
            )
            logging.error(err_msg)
            self.all_file_pairs = []
            self.unpaired_archives = []
            self.unpaired_previews = []
            self.file_pairs_list = []
            self._update_gallery_view()  # Wyczyść galerię
            self.filter_panel.setVisible(False)
            self.size_control_panel.setVisible(False)

    def _show_file_context_menu(self, file_pair, widget, position):
        """
        Wyświetla menu kontekstowe dla kafelka pliku.
        """
        context_menu = QMenu()

        # Dodanie akcji do menu
        rename_action = QAction("Zmień nazwę", self)
        delete_action = QAction("Usuń parę plików", self)

        # Dodanie akcji do menu
        context_menu.addAction(rename_action)
        context_menu.addSeparator()
        context_menu.addAction(delete_action)

        # Połączenie akcji z metodami
        rename_action.triggered.connect(
            lambda: self._rename_file_pair(file_pair, widget)
        )
        delete_action.triggered.connect(
            lambda: self._delete_file_pair(file_pair, widget)
        )

        # Wyświetlenie menu
        context_menu.exec(widget.mapToGlobal(position))

    def _rename_file_pair(self, file_pair, widget):
        """
        Zmienia nazwę pary plików.
        """
        old_name = file_pair.get_base_name()
        new_name, ok = QInputDialog.getText(
            self,
            "Zmień nazwę pliku",
            "Podaj nową nazwę dla pary plików (bez rozszerzenia):",
            text=old_name,
        )

        if ok and new_name and new_name != old_name:
            # Pobieramy ścieżki absolutne dla funkcji operacyjnej
            old_archive_path = os.path.join(
                self.current_working_directory, file_pair.get_relative_archive_path()
            )
            old_preview_path = None
            if file_pair.get_relative_preview_path():
                old_preview_path = os.path.join(
                    self.current_working_directory,
                    file_pair.get_relative_preview_path(),
                )

            result = file_operations.rename_file_pair(
                old_archive_path, old_preview_path, new_name
            )

            if result:
                new_archive_path, new_preview_path = result
                logging.info(
                    f"Zmieniono nazwę pary plików z '{old_name}' na '{new_name}'"
                )

                # Aktualizujemy obiekt FilePair o nowe dane
                file_pair.base_name = new_name
                file_pair.archive_path = os.path.relpath(
                    new_archive_path, self.current_working_directory
                )
                if new_preview_path:
                    file_pair.preview_path = os.path.relpath(
                        new_preview_path, self.current_working_directory
                    )
                else:
                    file_pair.preview_path = None

                # Zaktualizuj metadane
                self._save_metadata()

                # Zaktualizuj widget
                widget.update_data(file_pair)
            else:
                QMessageBox.warning(
                    self,
                    "Błąd zmiany nazwy",
                    f"Nie udało się zmienić nazwy pary plików '{old_name}' na '{new_name}'.",
                    QMessageBox.StandardButton.Ok,
                )

    def _delete_file_pair(self, file_pair, widget):
        """
        Usuwa parę plików po potwierdzeniu przez użytkownika.
        """
        file_name = file_pair.get_base_name()
        reply = QMessageBox.question(
            self,
            "Potwierdź usunięcie",
            f"Czy na pewno chcesz usunąć parę plików '{file_name}'?\nTa operacja jest nieodwracalna!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            archive_path_to_delete = file_pair.get_archive_path()  # klucz do słownika

            # Pobieramy ścieżki absolutne
            abs_archive_path = os.path.join(
                self.current_working_directory, file_pair.get_relative_archive_path()
            )
            abs_preview_path = None
            if file_pair.get_relative_preview_path():
                abs_preview_path = os.path.join(
                    self.current_working_directory,
                    file_pair.get_relative_preview_path(),
                )

            if file_operations.delete_file_pair(abs_archive_path, abs_preview_path):
                logging.info(f"Usunięto parę plików: {file_name}")

                # Usuń parę z listy głównej
                    self.all_file_pairs.remove(file_pair)

                # Zaktualizuj metadane (przed usunięciem z UI)
                self._save_metadata()

                # Usuń widget ze słownika i layoutu
                tile_to_delete = self.gallery_tile_widgets.pop(
                    archive_path_to_delete, None
                )
                if tile_to_delete:
                    if self.tiles_layout.indexOf(tile_to_delete) > -1:
                        self.tiles_layout.removeWidget(tile_to_delete)
                    tile_to_delete.deleteLater()

                self._apply_filters_and_update_view()
            else:
                QMessageBox.warning(
                    self,
                    "Błąd usuwania plików",
                    f"Nie udało się usunąć pary plików '{file_name}'.",
                    QMessageBox.StandardButton.Ok,
                )

    def dragEnterEvent(self, event):
        """
        Obsługa zdarzenia przeciągnięcia elementu nad okno aplikacji.
        """
        # Akceptuj dane MIME tylko z naszych kafelków plików
        if event.mimeData().hasText() or event.mimeData().hasFormat(
            "application/x-filepair"
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """
        Obsługa zdarzenia upuszczenia (przeciągnij i upuść).
        """
        if not event.mimeData().hasFormat("application/x-filepair"):
            event.ignore()
            return

        # Pobierz informacje o przeciąganej parze plików
        file_id = bytes(event.mimeData().data("application/x-filepair")).decode("utf-8")

        try:
            # Rozdziel identyfikator na ścieżki archiwum i podglądu
            archive_rel_path, preview_rel_path = file_id.split("|")
            # preview_rel_path może być pustym stringiem
            if not preview_rel_path:
                preview_rel_path = None

            # Znajdź odpowiedni obiekt FilePair na podstawie ścieżki względnej
            target_file_pair = None
            for fp in self.all_file_pairs:
                # Normalizujemy ścieżki przed porównaniem
                fp_archive_rel = fp.get_relative_archive_path().replace("\\\\", "/")
                if fp_archive_rel == archive_rel_path.replace("\\\\", "/"):
                    target_file_pair = fp
                    break

            if not target_file_pair:
                logging.warning(
                    f"Nie znaleziono przeciąganego pliku: {archive_rel_path}"
                )
                event.ignore()
                return

            # Określ folder docelowy
            drop_widget = QApplication.widgetAt(event.globalPosition().toPoint())
            target_folder_path = None

            # Sprawdź, czy upuszczono na drzewo folderów
            if isinstance(drop_widget, QTreeView) or isinstance(
                drop_widget.parent(), QTreeView
            ):
                tree_view = (
                    drop_widget
                    if isinstance(drop_widget, QTreeView)
                    else drop_widget.parent()
                )
                pos_in_tree = tree_view.viewport().mapFromGlobal(
                    event.globalPosition().toPoint()
                )
                index = tree_view.indexAt(pos_in_tree)
                if index.isValid():
                    target_folder_path = self.file_system_model.filePath(index)

            if not target_folder_path or not os.path.isdir(target_folder_path):
                logging.debug("Upuszczono poza prawidłowym folderem w drzewie.")
                event.ignore()
                return

            # Ścieżki absolutne do przeniesienia
            old_abs_archive_path = os.path.join(
                self.current_working_directory,
                target_file_pair.get_relative_archive_path(),
            )
            old_abs_preview_path = None
            if target_file_pair.get_relative_preview_path():
                old_abs_preview_path = os.path.join(
                    self.current_working_directory,
                    target_file_pair.get_relative_preview_path(),
                )

            # Przeniesienie plików za pomocą nowej funkcji
            result = file_operations.move_file_pair(
                old_abs_archive_path, old_abs_preview_path, target_folder_path
            )

            if result:
                new_archive_path, new_preview_path = result
                logging.info(
                    f"Przeniesiono parę plików '{target_file_pair.get_base_name()}' do '{target_folder_path}'"
                )

                # Aktualizacja obiektu FilePair
                target_file_pair.archive_path = os.path.relpath(
                    new_archive_path, self.current_working_directory
                )
                if new_preview_path:
                    target_file_pair.preview_path = os.path.relpath(
                        new_preview_path, self.current_working_directory
                    )
                else:
                    target_file_pair.preview_path = None

                # Zaktualizuj metadane i odśwież widok
                self._save_metadata()
                self._refresh_file_pairs_after_folder_operation()  # Ta metoda powinna przeładować wszystko
                event.acceptProposedAction()
            else:
                logging.warning(
                    f"Przenoszenie pary plików {target_file_pair.get_base_name()} nie powiodło się."
                )
                event.ignore()

        except Exception as e:
            logging.error(f"Błąd podczas obsługi przeciągnij i upuść: {e}")
            event.ignore()

    def _update_pair_button_state(self):
        """Aktualizuje stan przycisku 'Sparuj Wybrane' na podstawie zaznaczeń na listach."""
        if (
            not hasattr(self, "unpaired_archives_list_widget")
            or not hasattr(self, "unpaired_previews_list_widget")
            or not hasattr(self, "pair_manually_button")
        ):
            return  # Widgety mogły jeszcze nie zostać zainicjowane

        selected_archives = self.unpaired_archives_list_widget.selectedItems()
        selected_previews = self.unpaired_previews_list_widget.selectedItems()

        can_pair = len(selected_archives) == 1 and len(selected_previews) == 1
        self.pair_manually_button.setEnabled(can_pair)

    def _handle_manual_pairing(self):
        """Obsługuje logikę ręcznego parowania plików wybranych z list."""
        selected_archive_items = self.unpaired_archives_list_widget.selectedItems()
        selected_preview_items = self.unpaired_previews_list_widget.selectedItems()

        if not (len(selected_archive_items) == 1 and len(selected_preview_items) == 1):
            QMessageBox.warning(
                self,
                "Błąd Parowania",
                "Musisz wybrać dokładnie jedno archiwum i jeden podgląd do sparowania.",
            )
            return

        archive_path = selected_archive_items[0].data(Qt.ItemDataRole.UserRole)
        preview_path = selected_preview_items[0].data(Qt.ItemDataRole.UserRole)

        logging.info(
            f"Próba ręcznego sparowania: Archiwum='{archive_path}', Podgląd='{preview_path}'"
        )

        new_pair = file_operations.manually_pair_files(
            archive_path, preview_path, self.current_working_directory
        )

        if new_pair:
            logging.info(f"Pomyślnie sparowano: {new_pair.get_base_name()}")
            # 1. Dodaj do głównej listy par
            self.all_file_pairs.append(new_pair)

            # 2. Usuń z list niesparowanych (wewnętrznych list stringów)
            if archive_path in self.unpaired_archives:
                self.unpaired_archives.remove(archive_path)
            if preview_path in self.unpaired_previews:
                self.unpaired_previews.remove(preview_path)

            # 3. Odśwież UI: listy niesparowanych i galerię
            self._update_unpaired_files_lists()
            self._apply_filters_and_update_view()  # To odświeży galerię z nową parą

            # 4. Zapisz metadane (w tym zaktualizowane listy niesparowanych i nową parę)
            self._save_metadata()

            QMessageBox.information(
                self,
                "Sukces",
                f"Pomyślnie sparowano '{os.path.basename(archive_path)}' z '{os.path.basename(preview_path)}'.\n"
                f"Podgląd został zmieniony na: '{os.path.basename(new_pair.preview_path)}'",
            )
        else:
            logging.error(f"Nie udało się sparować plików.")
            QMessageBox.critical(
                self,
                "Błąd Parowania",
                "Nie udało się sparować wybranych plików. Sprawdź logi po więcej informacji.",
            )

        # Zaktualizuj stan przycisku po operacji (zaznaczenia prawdopodobnie znikną lub się zmienią)
        self._update_pair_button_state()

    def _update_unpaired_files_lists(self):
        """Aktualizuje listy niesparowanych plików w interfejsie użytkownika."""
        if not hasattr(self, "unpaired_archives_list_widget"):
            return  # UI not ready

        self.unpaired_archives_list_widget.clear()
        self.unpaired_previews_list_widget.clear()

        for archive_path in self.unpaired_archives:
            item = QListWidgetItem(os.path.basename(archive_path))
            item.setData(Qt.ItemDataRole.UserRole, archive_path)
            self.unpaired_archives_list_widget.addItem(item)

        for preview_path in self.unpaired_previews:
            item = QListWidgetItem(os.path.basename(preview_path))
            item.setData(Qt.ItemDataRole.UserRole, preview_path)
            self.unpaired_previews_list_widget.addItem(item)

        logging.debug(
            f"Zaktualizowano listy niesparowanych: {len(self.unpaired_archives)} archiwów, "
            f"{len(self.unpaired_previews)} podglądów."
        )
        self._update_pair_button_state()
