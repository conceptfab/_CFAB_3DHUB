"""
Główne okno aplikacji - zrefaktoryzowana wersja.
"""

import logging
import os

from PyQt6.QtCore import QDir, Qt, QThread, QTimer
from PyQt6.QtGui import QFileSystemModel, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
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
from src.models.file_pair import FilePair
from src.ui.delegates.workers import DataProcessingWorker, ScanFolderWorker
from src.ui.directory_tree_manager import DirectoryTreeManager
from src.ui.file_operations_ui import FileOperationsUI
from src.ui.gallery_manager import GalleryManager
from src.ui.widgets.filter_panel import FilterPanel
from src.ui.widgets.preview_dialog import PreviewDialog
from src.utils.path_utils import normalize_path


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji CFAB_3DHUB - zrefaktoryzowana wersja.
    """

    def __init__(self):
        """
        Inicjalizuje główne okno aplikacji.
        """
        super().__init__()
        self._init_data()
        self._init_window()
        self._init_ui()
        self._init_managers()
        logging.info("Główne okno aplikacji zostało zainicjalizowane")

    def _init_data(self):
        """Inicjalizuje dane aplikacji."""
        self.current_working_directory = None
        self.all_file_pairs: list[FilePair] = []
        self.unpaired_archives: list[str] = []
        self.unpaired_previews: list[str] = []

        # Wątki
        self.scan_thread = None
        self.scan_worker = None
        self.data_processing_thread = None
        self.data_processing_worker = None

    def _init_window(self):
        """Inicjalizuje okno aplikacji."""
        # Timer do opóźnienia odświeżania galerii
        self.resize_timer = QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._update_gallery_view)

        # Konfiguracja rozmiaru miniatur
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

    def _init_ui(self):
        """
        Inicjalizuje elementy interfejsu użytkownika.
        """
        # Panel górny
        self._create_top_panel()

        # Panel filtrów
        self.filter_panel = FilterPanel()
        self.filter_panel.setVisible(True)  # Zawsze widoczny
        self.filter_panel.setEnabled(False)  # Ale zablokowany na start
        self.filter_panel.connect_signals(self._apply_filters_and_update_view)
        self.main_layout.addWidget(self.filter_panel)

        # TabWidget jako główny kontener widoków
        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # Zakładka galerii
        self._create_gallery_tab()

        # Zakładka niesparowanych plików
        self._create_unpaired_files_tab()

    def _create_top_panel(self):
        """
        Tworzy panel górny z przyciskami i kontrolkami.
        """
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

        # Przycisk czyszczenia cache
        self.clear_cache_button = QPushButton("Odśwież (Wyczyść Cache)")
        self.clear_cache_button.clicked.connect(self._force_refresh)
        self.clear_cache_button.setVisible(False)
        self.top_layout.addWidget(self.clear_cache_button)

        # Panel kontroli rozmiaru
        self._create_size_control_panel()

        self.main_layout.addWidget(self.top_panel)

    def _create_size_control_panel(self):
        """
        Tworzy panel kontroli rozmiaru miniatur.
        """
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
        self.size_slider = QSlider()
        self.size_slider.setOrientation(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(0)
        self.size_slider.setMaximum(100)
        self.size_slider.setValue(50)
        self.size_slider.sliderReleased.connect(self._update_thumbnail_size)
        self.size_control_layout.addWidget(self.size_slider)

        self.top_layout.addStretch(1)
        self.top_layout.addWidget(self.size_control_panel)

    def _create_gallery_tab(self):
        """
        Tworzy zakładkę galerii.
        """
        self.gallery_tab = QWidget()
        self.gallery_tab_layout = QVBoxLayout(self.gallery_tab)
        self.gallery_tab_layout.setContentsMargins(0, 0, 0, 0)

        # Splitter dla drzewa i kafelków
        self.splitter = QSplitter()

        # Drzewo folderów
        self._create_folder_tree()

        # Scroll area dla kafelków
        self._create_tiles_area()

        self.splitter.setSizes([300, 700])
        self.gallery_tab_layout.addWidget(self.splitter)
        self.tab_widget.addTab(self.gallery_tab, "Galeria")

    def _create_folder_tree(self):
        """
        Tworzy drzewo folderów.
        """
        self.folder_tree = QTreeView()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setMinimumWidth(200)
        self.folder_tree.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )

        self.file_system_model = QFileSystemModel()
        # Pokaż tylko foldery (bez plików)
        self.file_system_model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot)
        self.folder_tree.setModel(self.file_system_model)

        # Ukryj wszystkie kolumny poza pierwszą
        for col in range(1, 4):
            self.folder_tree.setColumnHidden(col, True)

        self.splitter.addWidget(self.folder_tree)

    def _create_tiles_area(self):
        """
        Tworzy obszar dla kafelków galerii.
        """
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)

        self.tiles_container = QWidget()
        self.tiles_layout = QGridLayout(self.tiles_container)
        self.tiles_layout.setContentsMargins(10, 10, 10, 10)
        self.tiles_layout.setSpacing(15)

        self.scroll_area.setWidget(self.tiles_container)
        self.splitter.addWidget(self.scroll_area)

    def _create_unpaired_files_tab(self):
        """
        Tworzy zakładkę niesparowanych plików.
        """
        self.unpaired_files_tab = QWidget()
        self.unpaired_files_layout = QVBoxLayout(self.unpaired_files_tab)
        self.unpaired_files_layout.setContentsMargins(5, 5, 5, 5)

        # Splitter dla dwóch list
        self.unpaired_splitter = QSplitter()

        # Lista niesparowanych archiwów
        self._create_unpaired_archives_list()

        # Lista niesparowanych podglądów
        self._create_unpaired_previews_list()

        self.unpaired_files_layout.addWidget(self.unpaired_splitter)

        # Przycisk do ręcznego parowania
        self.pair_manually_button = QPushButton("Sparuj Wybrane")
        self.pair_manually_button.clicked.connect(self._handle_manual_pairing)
        self.pair_manually_button.setEnabled(False)
        self.unpaired_files_layout.addWidget(self.pair_manually_button)

        self.tab_widget.addTab(self.unpaired_files_tab, "Parowanie Plików")
        # Zakładka parowania zawsze widoczna

    def _create_unpaired_archives_list(self):
        """
        Tworzy listę niesparowanych archiwów.
        """
        self.unpaired_archives_panel = QWidget()
        layout = QVBoxLayout(self.unpaired_archives_panel)

        label = QLabel("Niesparowane Archiwa:")
        layout.addWidget(label)

        self.unpaired_archives_list_widget = QListWidget()
        self.unpaired_archives_list_widget.itemSelectionChanged.connect(
            self._update_pair_button_state
        )
        layout.addWidget(self.unpaired_archives_list_widget)

        self.unpaired_splitter.addWidget(self.unpaired_archives_panel)

    def _create_unpaired_previews_list(self):
        """
        Tworzy listę niesparowanych podglądów.
        """
        self.unpaired_previews_panel = QWidget()
        layout = QVBoxLayout(self.unpaired_previews_panel)

        label = QLabel("Niesparowane Podglądy:")
        layout.addWidget(label)

        self.unpaired_previews_list_widget = QListWidget()
        self.unpaired_previews_list_widget.itemSelectionChanged.connect(
            self._update_pair_button_state
        )
        layout.addWidget(self.unpaired_previews_list_widget)

        self.unpaired_splitter.addWidget(self.unpaired_previews_panel)

    def _init_managers(self):
        """
        Inicjalizuje managery.
        """
        # Gallery Manager
        self.gallery_manager = GalleryManager(self.tiles_container, self.tiles_layout)

        # Directory Tree Manager
        self.directory_tree_manager = DirectoryTreeManager(
            self.folder_tree, self.file_system_model, self
        )

        # File Operations UI
        self.file_operations_ui = FileOperationsUI(self)

        # Podłącz sygnały
        self.folder_tree.clicked.connect(self._folder_tree_item_clicked)

    def closeEvent(self, event):
        """
        Obsługuje zamykanie aplikacji - kończy wszystkie wątki.
        """
        self._cleanup_threads()
        event.accept()

    def _cleanup_threads(self):
        """
        Czyści wszystkie aktywne wątki.
        """
        # Zakończ wątek skanowania jeśli jest aktywny
        if self.scan_thread and self.scan_thread.isRunning():
            logging.info("Kończenie wątku skanowania przy zamykaniu aplikacji...")
            self.scan_thread.quit()
            if not self.scan_thread.wait(1000):
                logging.warning("Wątek skanowania nie zakończył się, wymuszam...")
                self.scan_thread.terminate()
                self.scan_thread.wait()

        # Zakończ wątek przetwarzania danych jeśli jest aktywny
        if self.data_processing_thread and self.data_processing_thread.isRunning():
            logging.info("Kończenie wątku przetwarzania przy zamykaniu aplikacji...")
            self.data_processing_thread.quit()
            if not self.data_processing_thread.wait(1000):
                logging.warning("Wątek przetwarzania nie zakończył się, wymuszam...")
                self.data_processing_thread.terminate()
                self.data_processing_thread.wait()

    def _select_working_directory(self, directory_path=None):
        """
        Otwiera dialog wyboru folderu lub używa podanej ścieżki.
        """
        # Przerwanie poprzedniego skanowania jeśli aktywne
        self._stop_current_scanning()

        if directory_path:
            path = directory_path
        else:
            path = QFileDialog.getExistingDirectory(self, "Wybierz Folder Roboczy")

        if not path:
            logging.debug("Nie wybrano folderu.")
            return

        # Ustaw nowy folder roboczy
        self.current_working_directory = normalize_path(path)
        base_folder_name = os.path.basename(self.current_working_directory)
        self.setWindowTitle(f"CFAB_3DHUB - {base_folder_name}")

        logging.info("Wybrano folder roboczy: %s", self.current_working_directory)

        # Wyczyść dane i rozpocznij skanowanie
        self._clear_all_data_and_views()
        self._start_folder_scanning()

    def _stop_current_scanning(self):
        """
        Przerywa aktualnie działające skanowanie.
        """
        if self.scan_thread and self.scan_thread.isRunning():
            logging.warning(
                "Nowe skanowanie żądane, gdy poprzednie jest aktywne. "
                "Przerywam stary wątek i uruchamiam nowy."
            )
            if self.scan_worker:
                self.scan_worker.stop()
            try:
                self.scan_worker.finished.disconnect()
                self.scan_worker.error.disconnect()
            except (TypeError, AttributeError):
                logging.debug("Nie można było odłączyć sygnałów od starego workera.")
            self.scan_thread.quit()
            self.scan_thread.wait(500)

    def _start_folder_scanning(self):
        """
        Rozpoczyna skanowanie folderu w osobnym wątku.
        """
        # Wyczyść cache skanowania
        from src.logic.scanner import clear_cache

        clear_cache()

        # Rozpocznij skanowanie w tle
        self.select_folder_button.setText("Skanowanie...")
        self.select_folder_button.setEnabled(False)

        # Uruchom workera skanowania
        self.scan_thread = QThread()
        self.scan_worker = ScanFolderWorker()
        self.scan_worker.directory_to_scan = self.current_working_directory
        self.scan_worker.moveToThread(self.scan_thread)

        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.finished.connect(self._handle_scan_finished)
        self.scan_worker.finished.connect(self.scan_thread.quit)
        self.scan_worker.error.connect(self._handle_scan_error)
        self.scan_worker.error.connect(self.scan_thread.quit)
        self.scan_thread.finished.connect(self._on_scan_thread_finished)

        self.scan_thread.start()
        logging.info(
            f"Uruchomiono wątek skanowania dla: " f"{self.current_working_directory}"
        )

    def _on_scan_thread_finished(self):
        """
        Slot wywoływany po zakończeniu pracy wątku skanującego.
        """
        # Przywróć przycisk skanowania
        self.select_folder_button.setText("Wybierz Folder")
        self.select_folder_button.setEnabled(True)

        # Wyczyść referencje do wątku
        if self.scan_thread:
            self.scan_thread.deleteLater()
            self.scan_thread = None
        if self.scan_worker:
            self.scan_worker.deleteLater()
            self.scan_worker = None
        logging.debug("Wątek skanujący i worker zostały bezpiecznie wyczyszczone.")

    def _force_refresh(self):
        """
        Wymusza ponowne skanowanie poprzez czyszczenie cache.
        """
        if self.current_working_directory:
            from src.logic.scanner import clear_cache

            clear_cache()
            logging.info("Cache wyczyszczony - wymuszono ponowne skanowanie")
            self._select_working_directory(self.current_working_directory)

    def _clear_all_data_and_views(self):
        """
        Czyści wszystkie dane plików i odpowiednie widoki.
        """
        self.all_file_pairs = []
        self.unpaired_archives = []
        self.unpaired_previews = []

        self.gallery_manager.clear_gallery()
        self._clear_unpaired_files_lists()

        self.filter_panel.setEnabled(False)  # Zablokuj zamiast ukryć
        # Zakładka parowania zawsze widoczna - nie ukrywamy!
        self.setWindowTitle("CFAB_3DHUB")

    def _clear_unpaired_files_lists(self):
        """
        Czyści listy niesparowanych plików w interfejsie użytkownika.
        """
        self.unpaired_archives_list_widget.clear()
        self.unpaired_previews_list_widget.clear()
        logging.debug("Wyczyszczono listy niesparowanych plików w UI.")

    def _update_unpaired_files_lists(self):
        """
        Aktualizuje listy niesparowanych plików w interfejsie użytkownika.
        """
        self.unpaired_archives_list_widget.clear()
        self.unpaired_previews_list_widget.clear()

        for archive_path in self.unpaired_archives:
            item = QListWidgetItem(os.path.basename(archive_path))
            item.setData(0x0100, archive_path)  # Qt.ItemDataRole.UserRole
            self.unpaired_archives_list_widget.addItem(item)

        for preview_path in self.unpaired_previews:
            item = QListWidgetItem(os.path.basename(preview_path))
            item.setData(0x0100, preview_path)  # Qt.ItemDataRole.UserRole
            self.unpaired_previews_list_widget.addItem(item)

        logging.debug(
            f"Zaktualizowano listy niesparowanych: "
            f"{len(self.unpaired_archives)} archiwów, "
            f"{len(self.unpaired_previews)} podglądów."
        )
        self._update_pair_button_state()

    def _handle_scan_finished(self, found_pairs, unpaired_archives, unpaired_previews):
        """
        Obsługuje wyniki pomyślnie zakończonego skanowania folderu.
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

        # Wyczyść poprzednie widgety kafelków
        self.gallery_manager.clear_gallery()

        # Uruchom workera do tworzenia kafelków w tle
        if self.all_file_pairs:
            self._start_data_processing_worker(self.all_file_pairs)
        else:
            self._on_tile_loading_finished()

    def _start_data_processing_worker(self, file_pairs: list[FilePair]):
        """
        Inicjalizuje i uruchamia workera do przetwarzania danych.
        """
        if self.data_processing_thread and self.data_processing_thread.isRunning():
            logging.warning(
                "Próba uruchomienia workera przetwarzania, "
                "gdy poprzedni jeszcze działa."
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
        """
        Tworzy pojedynczy kafelek dla pary plików.
        """
        tile = self.gallery_manager.create_tile_widget_for_pair(file_pair, self)
        if tile:
            # Podłącz sygnały kafelka
            tile.archive_open_requested.connect(self.open_archive)
            tile.preview_image_requested.connect(self._show_preview_dialog)
            tile.favorite_toggled.connect(self.toggle_favorite_status)
            tile.stars_changed.connect(self._handle_stars_changed)
            tile.color_tag_changed.connect(self._handle_color_tag_changed)
            tile.tile_context_menu_requested.connect(self._show_file_context_menu)

    def _on_tile_loading_finished(self):
        """
        Slot wywoływany po zakończeniu tworzenia wszystkich kafelków.
        """
        if self.data_processing_thread:
            self.data_processing_thread.quit()
            self.data_processing_thread.wait()
            self.data_processing_thread = None

        logging.info("Zakończono tworzenie wszystkich kafelków.")

        # Zastosuj filtry i odśwież widok
        self._apply_filters_and_update_view()
        self._update_unpaired_files_lists()

        # Pokaż interfejs
        self.filter_panel.setEnabled(True)  # Odblokuj panel filtrów
        is_gallery_populated = bool(self.gallery_manager.file_pairs_list)
        self.size_control_panel.setVisible(is_gallery_populated)
        # Zakładka parowania zawsze widoczna

        # Inicjalizacja drzewa katalogów
        self.directory_tree_manager.init_directory_tree(self.current_working_directory)

        # Przywróć przycisk
        self.select_folder_button.setText("Wybierz Folder Roboczy")
        self.select_folder_button.setEnabled(True)

        # Pokaż przycisk odświeżania cache
        self.clear_cache_button.setVisible(True)

        # Zapisz metadane
        self._save_metadata()

        logging.info(
            f"Widok zaktualizowany. Wyświetlono po filtracji: "
            f"{len(self.gallery_manager.file_pairs_list)}."
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

        self._clear_all_data_and_views()

        # Przywróć przycisk
        self.select_folder_button.setText("Wybierz Folder Roboczy")
        self.select_folder_button.setEnabled(True)
        self.filter_panel.setEnabled(False)  # Zablokuj przy błędzie

    def _apply_filters_and_update_view(self):
        """
        Zbiera kryteria, filtruje pary i aktualizuje galerię.
        """
        if not self.current_working_directory:
            self.gallery_manager.file_pairs_list = []
            self._update_gallery_view()
            self.size_control_panel.setVisible(False)
            self.filter_panel.setEnabled(False)  # Zablokuj zamiast ukryć
            return

        if not self.all_file_pairs:
            self.gallery_manager.file_pairs_list = []
            self._update_gallery_view()
            self.size_control_panel.setVisible(False)
            return

        # Pobierz kryteria filtrowania z panelu
        filter_criteria = self.filter_panel.get_filter_criteria()

        # Zastosuj filtry
        self.gallery_manager.apply_filters_and_update_view(
            self.all_file_pairs, filter_criteria
        )

        is_gallery_populated = bool(self.gallery_manager.file_pairs_list)
        self.size_control_panel.setVisible(is_gallery_populated)

    def _update_gallery_view(self):
        """
        Aktualizuje widok galerii.
        """
        self.gallery_manager.update_gallery_view()

    def _update_thumbnail_size(self):
        """
        Aktualizuje rozmiar miniatur i przerenderowuje galerię.
        """
        # Pobierz wartość z suwaka
        value = self.size_slider.value()

        # Oblicz nowy rozmiar
        size_range = self.max_thumbnail_size[0] - self.min_thumbnail_size[0]
        new_width = self.min_thumbnail_size[0] + int((size_range * value) / 100)
        new_height = new_width
        new_size = (new_width, new_height)

        logging.debug(f"Aktualizacja rozmiaru miniatur na: {new_size}")

        # Zapisz pozycję suwaka do konfiguracji
        app_config.set_thumbnail_slider_position(value)

        # Zaktualizuj rozmiar w gallery managerze
        self.gallery_manager.update_thumbnail_size(new_size)

    def resizeEvent(self, event):
        """
        Obsługuje zmianę rozmiaru okna.
        """
        # Opóźnienie przerenderowania galerii
        self.resize_timer.start(150)
        super().resizeEvent(event)

    def _save_metadata(self):
        """
        Zapisuje metadane dla wszystkich par plików.
        """
        if self.current_working_directory:
            if not metadata_manager.save_metadata(
                self.current_working_directory,
                self.all_file_pairs,
                self.unpaired_archives,
                self.unpaired_previews,
            ):
                logging.error("Nie udało się zapisać metadanych.")
        else:
            logging.debug("Brak folderu roboczego lub par plików do zapisu metadanych.")

    def open_archive(self, file_pair: FilePair):
        """
        Otwiera plik archiwum w domyślnym programie systemu.
        """
        if file_pair and file_pair.archive_path:
            logging.info(f"Żądanie otwarcia archiwum dla: {file_pair.get_base_name()}")
            file_operations.open_archive_externally(file_pair.archive_path)
        else:
            logging.warning(
                "Próba otwarcia archiwum dla nieprawidłowego FilePair "
                "lub braku ścieżki."
            )

    def _show_preview_dialog(self, file_pair: FilePair):
        """
        Wyświetla okno dialogowe z podglądem obrazu.
        """
        preview_path = file_pair.get_preview_path()
        if not preview_path or not os.path.exists(preview_path):
            QMessageBox.warning(
                self,
                "Brak Podglądu",
                "Plik podglądu dla tego elementu nie istnieje.",
            )
            return

        try:
            pixmap = QPixmap(preview_path)
            if pixmap.isNull():
                raise ValueError("Nie udało się załadować obrazu do QPixmap.")

            dialog = PreviewDialog(pixmap, self)
            dialog.exec()

        except Exception as e:
            error_message = f"Wystąpił błąd podczas ładowania podglądu: {e}"
            logging.error(error_message)
            QMessageBox.critical(self, "Błąd Podglądu", error_message)

    def toggle_favorite_status(self, file_pair: FilePair):
        """
        Przełącza status 'ulubione' dla danej pary plików.
        """
        if file_pair in self.all_file_pairs:
            file_pair.toggle_favorite()
            self._save_metadata()
            # Jeśli filtr ulubionych jest aktywny, zmiana może wpłynąć na widok
            filter_criteria = self.filter_panel.get_filter_criteria()
            if filter_criteria.get("show_favorites_only"):
                self._apply_filters_and_update_view()
        else:
            logging.warning("Toggle fav dla nieznanej pary.")

    def _handle_stars_changed(self, file_pair: FilePair, new_star_count: int):
        """
        Obsługuje zmianę liczby gwiazdek dla pary plików.
        """
        if file_pair:
            file_pair.set_stars(new_star_count)
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

    def _folder_tree_item_clicked(self, index):
        """
        Obsługuje kliknięcie elementu w drzewie folderów.
        """
        folder_path = self.directory_tree_manager.folder_tree_item_clicked(
            index, self.current_working_directory
        )
        if folder_path:
            self._select_working_directory(folder_path)

    def _show_file_context_menu(self, file_pair: FilePair, widget: QWidget, position):
        """
        Wyświetla menu kontekstowe dla kafelka.
        """
        self.file_operations_ui.show_file_context_menu(file_pair, widget, position)

    def _update_pair_button_state(self):
        """
        Aktualizuje stan przycisku do ręcznego parowania.
        """
        selected_archives = self.unpaired_archives_list_widget.selectedItems()
        selected_previews = self.unpaired_previews_list_widget.selectedItems()
        self.pair_manually_button.setEnabled(
            len(selected_archives) == 1 and len(selected_previews) == 1
        )

    def _handle_manual_pairing(self):
        """
        Obsługuje logikę ręcznego parowania plików.
        """
        new_pair = self.file_operations_ui.handle_manual_pairing(
            self.unpaired_archives_list_widget, self.unpaired_previews_list_widget
        )

        if new_pair:
            # Aktualizuj dane aplikacji
            self.all_file_pairs.append(new_pair)

            # Usuń z list niesparowanych
            archive_path = new_pair.get_archive_path()
            preview_path = new_pair.get_preview_path()

            if archive_path in self.unpaired_archives:
                self.unpaired_archives.remove(archive_path)
            if preview_path in self.unpaired_previews:
                self.unpaired_previews.remove(preview_path)

            # Odśwież UI
            self._update_unpaired_files_lists()
            self._apply_filters_and_update_view()
