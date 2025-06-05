"""
Główne okno aplikacji.
"""

import logging
import math
import os

from PyQt6.QtCore import QDir, QObject, Qt, QThread, QTimer, pyqtSignal
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


class DataProcessingWorker(QObject):
    """
    Worker do przetwarzania danych w tle. Odpowiedzialny za:
    1. Zastosowanie metadanych do par plików (operacja I/O).
    2. Emitowanie sygnałów do tworzenia kafelków w głównym wątku.
    """

    tile_data_ready = pyqtSignal(FilePair)
    finished = pyqtSignal()

    def __init__(self, working_directory: str, file_pairs: list[FilePair], parent=None):
        super().__init__(parent)
        self.working_directory = working_directory
        self.file_pairs = file_pairs

    def run(self):
        """Główna metoda workera."""
        try:
            # 1. Zastosuj metadane (ciężka operacja I/O)
            if self.file_pairs:
                logging.info("DataProcessingWorker: Rozpoczynam stosowanie metadanych.")
                metadata_manager.apply_metadata_to_file_pairs(
                    self.working_directory, self.file_pairs
                )
                logging.info("DataProcessingWorker: Zakończono stosowanie metadanych.")

            # 2. Emituj sygnały do tworzenia kafelków
            if self.file_pairs:
                logging.debug(
                    f"DataProcessingWorker: Rozpoczynam przygotowanie "
                    f"{len(self.file_pairs)} kafelków."
                )
                for file_pair in self.file_pairs:
                    self.tile_data_ready.emit(file_pair)
                    # Dajemy głównemu wątkowi szansę na przetworzenie zdarzeń
                    QThread.msleep(1)
            else:
                logging.debug("DataProcessingWorker: Brak par plików do przetworzenia.")

        except Exception as e:
            logging.error(f"Błąd w DataProcessingWorker: {e}")
        finally:
            self.finished.emit()


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

        # Wątek i worker do przetwarzania danych i ładowania kafelków
        self.data_processing_thread = None
        self.data_processing_worker = None

        # Timer do opóźnienia odświeżania galerii przy zmianie rozmiaru okna
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._update_gallery_view)

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
        # OPTYMALIZACJA: Aktualizuj galerię dopiero po puszczeniu suwaka
        self.size_slider.sliderReleased.connect(self._update_thumbnail_size)
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

    def _handle_scan_finished(self, found_pairs, unpaired_archives, unpaired_previews):
        """
        Obsługuje wyniki pomyślnie zakończonego skanowania folderu.
        Uruchamia workera do tworzenia kafelków w tle.
        """
        logging.info(
            f"Skanowanie folderu {self.current_working_directory} zakończone pomyślnie."
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

        # 2. Uruchom workera do zastosowania metadanych i tworzenia kafelków w tle
        if self.all_file_pairs:
            self._start_data_processing_worker(self.all_file_pairs)
        else:
            # Jeśli nie ma par, po prostu zaktualizuj UI
            self._on_tile_loading_finished()

    def _start_data_processing_worker(self, file_pairs: list[FilePair]):
        """Inicjalizuje i uruchamia workera do przetwarzania danych."""
        if self.data_processing_thread and self.data_processing_thread.isRunning():
            logging.warning(
                "Próba uruchomienia workera przetwarzania, gdy poprzedni jeszcze działa."
            )
            return

        self.data_processing_thread = QThread()
        self.data_processing_worker = DataProcessingWorker(
            self.current_working_directory, file_pairs
        )
        self.data_processing_worker.moveToThread(self.data_processing_thread)

        # Podłączenie sygnałów
        self.data_processing_worker.tile_data_ready.connect(
            self._create_tile_widget_for_pair
        )
        self.data_processing_worker.finished.connect(self._on_tile_loading_finished)
        self.data_processing_thread.started.connect(self.data_processing_worker.run)

        self.data_processing_thread.start()

    def _create_tile_widget_for_pair(self, file_pair: FilePair):
        """Tworzy pojedynczy kafelek. Ten slot jest wywoływany w głównym wątku."""
        try:
            # FIX: Przywrócenie `self` jako rodzica, co naprawia problem z ładowaniem galerii.
            # Reparenting do `tiles_container` nastąpi automatycznie po dodaniu do layoutu.
            tile = FileTileWidget(file_pair, self.current_thumbnail_size, self)
            tile.archive_open_requested.connect(self.open_archive)
            tile.preview_image_requested.connect(self._show_preview_dialog)
            tile.favorite_toggled.connect(self.toggle_favorite_status)
            tile.stars_changed.connect(self._handle_stars_changed)
            tile.color_tag_changed.connect(self._handle_color_tag_changed)
            tile.tile_context_menu_requested.connect(self._show_file_context_menu)

            # Ukryj na starcie, _update_gallery_view zdecyduje o widoczności
            tile.setVisible(False)
            self.gallery_tile_widgets[file_pair.get_archive_path()] = tile
        except Exception as e:
            logging.error(
                f"Błąd tworzenia kafelka " f"dla {file_pair.get_base_name()}: {e}"
            )

    def _on_tile_loading_finished(self):
        """
        Slot wywoływany po zakończeniu tworzenia wszystkich kafelków przez workera.
        """
        if self.data_processing_thread:
            self.data_processing_thread.quit()
            self.data_processing_thread.wait()
            self.data_processing_thread = None

        logging.info("Zakończono tworzenie wszystkich kafelków.")

        # Zastosuj filtry (początkowo domyślne) i odśwież widok
        self._apply_filters_and_update_view()
        self._update_unpaired_files_lists()

        # Pokaż panel filtrów i kontroli rozmiaru
        self.filter_panel.setVisible(True)
        is_gallery_populated = bool(self.file_pairs_list)
        self.size_control_panel.setVisible(is_gallery_populated)
        self.tab_widget.setTabVisible(
            1, bool(self.unpaired_archives or self.unpaired_previews)
        )

        # Inicjalizacja drzewa katalogów
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
            "Wystąpił błąd podczas skanowania folderu:\n" f"{error_message}",
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
        # OPTYMALIZACJA: Wyłącz aktualizacje na czas przebudowy layoutu
        self.tiles_container.setUpdatesEnabled(False)

        # 1. Usuń wszystkie widgety z layoutu (ale nie z pamięci/słownika)
        while self.tiles_layout.count():
            item = self.tiles_layout.takeAt(0)
            widget = item.widget()
            if widget:
                # FIX: Zamiast odrywać widget (setParent(None)), po prostu go ukrywamy.
                # To eliminuje problem mrugających okien.
                widget.setVisible(False)

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
                        f"Nie znaleziono widgetu kafelka dla "
                        f"{file_pair.get_archive_path()} w słowniku."
                    )

            # Ukryj widgety, które nie są na liście file_pairs_list
            # (te, które zostały odfiltrowane)
            for archive_path, tile_widget in self.gallery_tile_widgets.items():
                # Sprawdź, czy file_pair dla tego widgetu jest na liście do wyświetlenia
                is_on_list = any(
                    fp.get_archive_path() == archive_path for fp in self.file_pairs_list
                )
                if not is_on_list:
                    tile_widget.setVisible(False)
        finally:
            # OPTYMALIZACJA: Włącz aktualizacje i zaplanuj odświeżenie
            self.tiles_container.setUpdatesEnabled(True)
            self.tiles_container.update()

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

    def _update_thumbnail_size(self):
        """Aktualizuje rozmiar miniatur i przerenderowuje galerię. Wywoływane po puszczeniu suwaka."""
        # Pobierz aktualną wartość z suwaka
        value = self.size_slider.value()

        # Obliczenie nowego rozmiaru na podstawie wartości suwaka
        size_range = self.max_thumbnail_size[0] - self.min_thumbnail_size[0]
        new_width = self.min_thumbnail_size[0] + int((size_range * value) / 100)
        new_height = new_width  # Zachowujemy proporcje kwadratowe
        self.current_thumbnail_size = (new_width, new_height)

        logging.debug(
            f"Aktualizacja rozmiaru miniatur na: {self.current_thumbnail_size}"
        )

        # 1. Zapisz pozycję suwaka do konfiguracji
        slider_pos = self.size_slider.value()
        app_config.set_thumbnail_slider_position(slider_pos)

        # 2. Zaktualizuj rozmiar w kafelkach
        for tile in self.gallery_tile_widgets.values():
            tile.set_thumbnail_size(self.current_thumbnail_size)

        # 3. Przerenderuj galerię z nowymi rozmiarami
        self._update_gallery_view()

    def resizeEvent(self, event):
        # Opóźnienie przerenderowania galerii po zmianie rozmiaru okna
        # zamiast wywoływać _update_gallery_view() bezpośrednio.
        self.resize_timer.start(150)  # Czas w milisekundach
        super().resizeEvent(event)

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
        Wyświetla okno dialogowe z podglądem obrazu w wysokiej rozdzielczości.
        """
        # Sprawdzenie, czy ścieżka podglądu istnieje
        preview_path = file_pair.get_preview_path()
        if not preview_path or not os.path.exists(preview_path):
            QMessageBox.warning(
                self,
                "Brak Podglądu",
                "Plik podglądu dla tego elementu nie istnieje.",
            )
            return

        # Tworzenie i wyświetlanie dialogu
        try:
            # Tworzenie pixmapy z pliku
            pixmap = QPixmap(preview_path)
            if pixmap.isNull():
                raise ValueError("Nie udało się załadować obrazu do QPixmap.")

            dialog = PreviewDialog(pixmap, self)
            dialog.exec()  # Używamy exec() dla modalnego dialogu

        except Exception as e:
            error_message = f"Wystąpił błąd podczas ładowania podglądu: {e}"
            logging.error(error_message)
            QMessageBox.critical(self, "Błąd Podglądu", error_message)

    # MODIFICATION: Slot for favorite_toggled signal
    # This method might replace or be an update to an existing toggle_favorite_status method
    def toggle_favorite_status(self, file_pair: FilePair):
        """
        Przełącza status 'ulubione' dla danej pary plików.
        """
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
        """
        Obsługuje zmianę liczby gwiazdek dla pary plików.
        """
        if file_pair:
            file_pair.set_stars(new_star_count)
            # Aktualizacja UI nie jest tu konieczna, bo widget sam się zaktualizował
            logging.debug(
                f"Zmieniono liczbę gwiazdek dla "
                f"{file_pair.get_base_name()} na {new_star_count}."
            )

    def _handle_color_tag_changed(self, file_pair: FilePair, new_color_tag: str):
        """
        Obsługuje zmianę tagu koloru dla pary plików.
        """
        if file_pair:
            file_pair.set_color_tag(new_color_tag)
            logging.debug(
                f"Zmieniono tag koloru dla {file_pair.get_base_name()} "
                f"na {new_color_tag}."
            )

    def _init_directory_tree(self):
        """
        Inicjalizuje i konfiguruje model drzewa katalogów.
        """
        if not self.current_working_directory:
            return

        # Ustawienie ścieżki root i rozwinięcie pierwszego poziomu
        if self.current_working_directory:
            root_index = self.file_system_model.setRootPath(
                self.current_working_directory
            )
            self.folder_tree.setRootIndex(root_index)

            # Rozwinięcie tylko do pierwszego poziomu podkatalogów
            # self.folder_tree.expandToDepth(0) # 0 oznacza tylko root

            # Ukrycie nagłówków (np. 'Name', 'Size', 'Date Modified')
            self.folder_tree.setHeaderHidden(True)

            # Ukrycie wszystkich kolumn poza pierwszą (nazwa)
            for i in range(1, self.file_system_model.columnCount()):
                self.folder_tree.setColumnHidden(i, True)

            self.folder_tree.clicked.connect(self._folder_tree_item_clicked)
            logging.info(
                "Drzewo katalogów zainicjalizowane dla: "
                f"{self.current_working_directory}"
            )
        else:
            logging.warning(
                "Nie można zainicjalizować drzewa katalogów, " "brak folderu roboczego."
            )

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
        Obsługuje kliknięcie elementu w drzewie folderów, filtrując widok galerii.
        """
        # Pobranie ścieżki do folderu z modelu
        folder_path = self.file_system_model.filePath(index)
        logging.debug(f"Kliknięto folder w drzewie: {folder_path}")

        # Sprawdzenie, czy ścieżka jest prawidłowa
        if not folder_path or not os.path.isdir(folder_path):
            logging.warning(f"Nieprawidłowa ścieżka: {folder_path}")
            return

        # Normalizacja ścieżek dla spójności
        normalized_root = os.path.normpath(self.current_working_directory)
        normalized_clicked = os.path.normpath(folder_path)

        # Jeśli kliknięto główny folder roboczy, pokaż wszystko
        if normalized_clicked == normalized_root:
            logging.debug("Wybrano główny folder, resetowanie filtrów ścieżki.")
            # Resetuj kryteria filtrowania ścieżki i zastosuj ponownie wszystkie filtry
            if "path_prefix" in self.current_filter_criteria:
                del self.current_filter_criteria["path_prefix"]
            self._apply_filters_and_update_view()
            return

        # Filtrowanie na podstawie podfolderu
        # Przechowaj ten filtr, aby inne filtry (gwiazdki, ulubione) go uwzględniły
        logging.debug(
            f"Filtrowanie galerii, aby pokazać tylko pliki z: " f"{normalized_clicked}"
        )
        self.current_filter_criteria["path_prefix"] = normalized_clicked
        self._apply_filters_and_update_view()

    def _show_file_context_menu(self, file_pair: FilePair, widget: QWidget, position):
        """
        Wyświetla menu kontekstowe dla kafelka.
        """
        menu = QMenu(self)

        # --- Akcja zmiany nazwy ---
        rename_action = QAction("Zmień nazwę", self)
        rename_action.triggered.connect(
            lambda: self._rename_file_pair(file_pair, widget)
        )
        menu.addAction(rename_action)

        # --- Akcja usunięcia ---
        delete_action = QAction("Usuń", self)
        delete_action.triggered.connect(
            lambda: self._delete_file_pair(file_pair, widget)
        )
        menu.addAction(delete_action)

        # Wyświetlenie menu w odpowiedniej pozycji
        menu.exec(widget.mapToGlobal(position))

    def _rename_file_pair(self, file_pair: FilePair, widget: QWidget):
        """
        Rozpoczyna proces zmiany nazwy dla pary plików.
        Otwiera okno dialogowe do wprowadzenia nowej nazwy.
        """
        current_name = file_pair.get_base_name()
        new_name, ok = QInputDialog.getText(
            self,
            "Zmień nazwę",
            "Wprowadź nową nazwę (bez rozszerzenia):",
            text=current_name,
        )

        if ok and new_name and new_name != current_name:
            try:
                # Wywołanie logiki zmiany nazwy z file_operations
                new_file_pair = file_operations.rename_file_pair(file_pair, new_name)
                logging.info(f"Zmieniono nazwę {current_name} na {new_name}.")

                # --- Aktualizacja UI ---
                # 1. Zaktualizuj główną listę par
                self.all_file_pairs.remove(file_pair)
                self.all_file_pairs.append(new_file_pair)

                # 2. Zaktualizuj słownik widgetów
                # Usuń stary wpis
                old_archive_path = file_pair.get_archive_path()
                if old_archive_path in self.gallery_tile_widgets:
                    # Nie niszczymy widgetu, tylko go aktualizujemy i przekładamy w słowniku
                    tile = self.gallery_tile_widgets.pop(old_archive_path)
                    tile.update_data(new_file_pair)  # Zaktualizuj dane w kafelku
                    self.gallery_tile_widgets[new_file_pair.get_archive_path()] = tile
                else:
                    logging.warning(
                        f"Nie znaleziono kafelka dla {old_archive_path} "
                        f"podczas zmiany nazwy."
                    )

                # 3. Odśwież widok, aby odzwierciedlić zmiany
                # (np. sortowanie, jeśli jest zaimplementowane)
                self._apply_filters_and_update_view()
                # --- Koniec aktualizacji UI ---

            except FileExistsError as e:
                QMessageBox.critical(
                    self, "Błąd", f"Plik o nazwie '{new_name}' już istnieje."
                )
                logging.error(e)
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Błąd zmiany nazwy",
                    f"Wystąpił nieoczekiwany błąd: {e}",
                )
                logging.error(e)

    def _delete_file_pair(self, file_pair: FilePair, widget: QWidget):
        """
        Usuwa parę plików (archiwum i podgląd) po potwierdzeniu.
        """
        confirm = QMessageBox.question(
            self,
            "Potwierdź usunięcie",
            f"Czy na pewno chcesz usunąć pliki dla '{file_pair.get_base_name()}'?\n\n"
            f"Archiwum: {file_pair.get_archive_path()}\n"
            f"Podgląd: {file_pair.get_preview_path()}\n\n"
            "Ta operacja jest nieodwracalna.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            try:
                # Wywołanie logiki usuwania z file_operations
                file_operations.delete_file_pair(file_pair)
                logging.info(f"Usunięto pliki dla {file_pair.get_base_name()}.")

                # --- Aktualizacja UI ---
                # 1. Usuń z głównych list
                if file_pair in self.all_file_pairs:
                    self.all_file_pairs.remove(file_pair)

                # 2. Usuń widget z layoutu i słownika
                archive_path = file_pair.get_archive_path()
                if archive_path in self.gallery_tile_widgets:
                    tile = self.gallery_tile_widgets.pop(archive_path)
                    tile.setParent(None)
                    tile.deleteLater()  # Zaplanuj usunięcie widgetu

                # 3. Odśwież widok
                self._apply_filters_and_update_view()
                # --- Koniec aktualizacji UI ---

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Błąd usuwania",
                    f"Wystąpił błąd podczas usuwania plików: {e}",
                )
                logging.error(e)

    def dragEnterEvent(self, event):
        """
        Obsługa zdarzenia przeciągnięcia elementu nad okno aplikacji.
        """
        if event.mimeData().hasUrls():
            # Sprawdź, na jaki widget upuszczono pliki
            drop_widget = self.childAt(event.position().toPoint())

            # Sprawdzenie, czy upuszczono na drzewo folderów
            if self.folder_tree.isAncestorOf(drop_widget):
                # Znajdź element drzewa pod kursorem
                index = self.folder_tree.indexAt(
                    event.position().toPoint()
                    - self.folder_tree.mapToParent(self.folder_tree.pos())
                )
                if index.isValid():
                    target_folder_path = self.file_system_model.filePath(index)
                    self._handle_drop_on_folder(
                        event.mimeData().urls(), target_folder_path
                    )
            # Sprawdzenie, czy upuszczono na listę niesparowanych archiwów
            elif self.unpaired_archives_list_widget.isAncestorOf(drop_widget):
                self._handle_drop_on_unpaired_list(event.mimeData().urls(), "archive")
            # Sprawdzenie, czy upuszczono na listę niesparowanych podglądów
            elif self.unpaired_previews_list_widget.isAncestorOf(drop_widget):
                self._handle_drop_on_unpaired_list(event.mimeData().urls(), "preview")

            event.acceptProposedAction()
        else:
            event.ignore()

    def _handle_drop_on_folder(self, urls, target_folder_path):
        """Obsługuje upuszczenie plików na folder w drzewie."""
        file_paths = [url.toLocalFile() for url in urls]
        logging.debug(f"Upuszczono pliki {file_paths} na folder {target_folder_path}")

        reply = QMessageBox.question(
            self,
            "Przenoszenie plików",
            f"Czy chcesz przenieść {len(file_paths)} elementów "
            f"do folderu '{os.path.basename(target_folder_path)}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Tutaj logika przenoszenia plików
            # Po przeniesieniu, odśwież widok
            logging.info("Rozpoczynanie przenoszenia plików...")
            # UWAGA: Ta operacja może być długotrwała. W przyszłości
            # można ją przenieść do wątku.
            # ...
            # Po zakończeniu: self._refresh_file_pairs_after_folder_operation()
            pass

    def _handle_drop_on_unpaired_list(self, urls, list_type):
        """Obsługuje upuszczenie plików na listy niesparowanych."""
        # Ta funkcja jest przykładem. Należy ją zaimplementować.
        file_paths = [url.toLocalFile() for url in urls]
        logging.debug(f"Upuszczono pliki {file_paths} na listę '{list_type}'")
        # TODO: Implementacja logiki kopiowania/przenoszenia i odświeżania

    def _update_pair_button_state(self):
        """
        Aktualizuje stan przycisku do ręcznego parowania na podstawie zaznaczeń.
        """
        if (
            not hasattr(self, "unpaired_archives_list_widget")
            or not hasattr(self, "unpaired_previews_list_widget")
            or not hasattr(self, "pair_manually_button")
        ):
            return  # Widgety mogły jeszcze nie zostać zainicjowane

        selected_archives = self.unpaired_archives_list_widget.selectedItems()
        selected_previews = self.unpaired_previews_list_widget.selectedItems()
        self.pair_manually_button.setEnabled(
            len(selected_archives) == 1 and len(selected_previews) == 1
        )

    def _handle_manual_pairing(self):
        """
        Obsługuje logikę ręcznego parowania plików zaznaczonych na listach.
        """
        selected_archives = self.unpaired_archives_list_widget.selectedItems()
        selected_previews = self.unpaired_previews_list_widget.selectedItems()

        if not (len(selected_archives) == 1 and len(selected_previews) == 1):
            QMessageBox.warning(
                self,
                "Błąd parowania",
                "Proszę zaznaczyć dokładnie jeden plik archiwum i jeden plik podglądu.",
            )
            return

        archive_item = selected_archives[0]
        preview_item = selected_previews[0]

        archive_path = archive_item.data(Qt.ItemDataRole.UserRole)
        preview_path = preview_item.data(Qt.ItemDataRole.UserRole)

        try:
            # Wywołanie logiki parowania
            new_pair = file_operations.create_pair_from_files(
                archive_path, preview_path
            )
            logging.info(
                f"Ręcznie sparowano: {new_pair.get_archive_path()} "
                f"z {new_pair.get_preview_path()}"
            )

            # Aktualizacja UI
            self.all_file_pairs.append(new_pair)
            self.unpaired_archives.remove(archive_path)
            self.unpaired_previews.remove(preview_path)

            self._update_unpaired_files_lists()
            self._apply_filters_and_update_view()

            QMessageBox.information(
                self,
                "Sukces",
                f"Pomyślnie sparowano pliki dla '{new_pair.get_base_name()}'.",
            )

        except Exception as e:
            error_message = f"Błąd podczas ręcznego parowania: {e}"
            logging.error(error_message)
            QMessageBox.critical(self, "Błąd", error_message)

    def _show_unpaired_archive_context_menu(self, position):
        """
        Wyświetla menu kontekstowe dla niesparowanego pliku archiwum.
        """
        # Znajdź element pod kursorem
        item = self.unpaired_archives_list_widget.itemAt(position)
        if not item:
            return

        menu = QMenu()
        open_action = menu.addAction("Otwórz lokalizację pliku")
        action = menu.exec(self.unpaired_archives_list_widget.mapToGlobal(position))

        if action == open_action:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            # Logika otwierania folderu zawierającego plik
            file_operations.open_file_location(os.path.dirname(file_path))

    def _show_unpaired_preview_context_menu(self, position):
        """
        Wyświetla menu kontekstowe dla listy niesparowanych podglądów.
        """
        # Znajdź element pod kursorem
        item = self.unpaired_previews_list_widget.itemAt(position)
        if not item:
            return

        menu = QMenu()
        open_action = menu.addAction("Otwórz lokalizację pliku")
        action = menu.exec(self.unpaired_previews_list_widget.mapToGlobal(position))

        if action == open_action:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            file_operations.open_file_location(os.path.dirname(file_path))
