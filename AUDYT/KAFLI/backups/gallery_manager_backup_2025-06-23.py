"""
Manager galerii - zarządzanie wyświetlaniem kafelków.
"""

import logging
import math
import os
import threading
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QApplication, QGridLayout, QSizePolicy, QWidget

from src import app_config
from src.controllers.gallery_controller import GalleryController
from src.models.file_pair import FilePair
from src.models.special_folder import SpecialFolder
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.ui.widgets.special_folder_tile_widget import SpecialFolderTileWidget
from src.ui.widgets.tile_resource_manager import get_resource_manager

logger = logging.getLogger(__name__)


class LayoutGeometry:
    """Klasa pomocnicza do obliczeń geometrii layoutu."""

    def __init__(self, scroll_area, tiles_layout):
        self.scroll_area = scroll_area
        self.tiles_layout = tiles_layout
        self._cache = {}
        self._cache_lock = threading.Lock()

    def get_layout_params(self, thumbnail_size):
        """Zwraca parametry layoutu dla danego rozmiaru miniatur."""
        with self._cache_lock:
            cache_key = (
                self.scroll_area.width(),
                self.scroll_area.height(),
                thumbnail_size,
            )

            if cache_key in self._cache:
                return self._cache[cache_key]

            container_width = (
                self.scroll_area.width() - self.scroll_area.verticalScrollBar().width()
            )
            tile_width_spacing = thumbnail_size + self.tiles_layout.spacing() + 10
            tile_height_spacing = thumbnail_size + self.tiles_layout.spacing() + 40
            cols = max(1, math.ceil(container_width / tile_width_spacing))

            params = {
                "container_width": container_width,
                "cols": cols,
                "tile_width_spacing": tile_width_spacing,
                "tile_height_spacing": tile_height_spacing,
            }

            self._cache[cache_key] = params
            return params

    def get_visible_range(self, thumbnail_size, total_items):
        """Oblicza zakres widocznych elementów."""
        params = self.get_layout_params(thumbnail_size)

        viewport_height = self.scroll_area.viewport().height()
        scroll_y = self.scroll_area.verticalScrollBar().value()

        buffer = viewport_height
        visible_start_y = max(0, scroll_y - buffer)
        visible_end_y = scroll_y + viewport_height + buffer

        first_visible_row = max(
            0, math.floor(visible_start_y / params["tile_height_spacing"])
        )
        last_visible_row = math.ceil(visible_end_y / params["tile_height_spacing"])

        first_visible_item = first_visible_row * params["cols"]
        last_visible_item = min((last_visible_row + 1) * params["cols"], total_items)

        return first_visible_item, last_visible_item, params


class GalleryManager:
    """
    Klasa zarządzająca galerią kafelków z thread safety.
    """

    VIRTUALIZATION_UPDATE_DELAY = 50  # ms, opóźnienie dla aktualizacji wirtualizacji

    # Flaga do włączania diagnostyki
    DIAGNOSTIC_LOGGING = os.getenv("GALLERY_DIAGNOSTIC", "false").lower() == "true"

    def __init__(
        self,
        main_window,
        tiles_container: QWidget,
        tiles_layout: QGridLayout,
        scroll_area: QWidget,
    ):
        self.main_window = main_window
        self.tiles_container = tiles_container
        self.tiles_layout = tiles_layout
        self.scroll_area = scroll_area  # Potrzebne do wirtualizacji
        self.controller = GalleryController()
        self.gallery_tile_widgets: Dict[str, FileTileWidget] = {}
        self.special_folder_widgets: Dict[str, SpecialFolderTileWidget] = {}
        self.file_pairs_list: List[FilePair] = []
        self.special_folders_list: List[SpecialFolder] = []
        # Inicjalizuj current_thumbnail_size jako int, zgodnie z app_config
        self.current_thumbnail_size = app_config.DEFAULT_THUMBNAIL_SIZE
        # Zapisz krotkę rozmiaru dla spójności interfejsu
        self._current_size_tuple = (
            self.current_thumbnail_size,
            self.current_thumbnail_size,
        )

        # Thread safety
        self._widgets_lock = threading.RLock()
        self._geometry_cache_lock = threading.Lock()

        # Cache dla obliczeń geometrii
        self._geometry_cache = {
            "container_width": 0,
            "cols": 0,
            "tile_width_spacing": 0,
            "tile_height_spacing": 0,
            "last_thumbnail_size": 0,
        }

        # Flaga dla pending size update
        self._pending_size_update = False

        # Klasa pomocnicza do geometrii
        self._geometry = LayoutGeometry(self.scroll_area, self.tiles_layout)

        # Timer do opóźnionej aktualizacji wirtualizacji
        self._virtualization_timer = QTimer()
        self._virtualization_timer.setSingleShot(True)
        self._virtualization_timer.timeout.connect(self._update_visible_tiles)

        # NAPRAWKA: Podłącz scroll event do wirtualizacji
        if hasattr(self.scroll_area, "verticalScrollBar"):
            self.scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

        # NAPRAWKA KRYTYCZNA: Inicjalizacja flagi wirtualizacji
        self._virtualization_enabled = True  # Domyślnie włączona wirtualizacja

    def _log_diagnostic(self, message: str):
        """Logowanie diagnostyczne - tylko gdy włączone."""
        if self.DIAGNOSTIC_LOGGING:
            logger.debug(f"GALLERY_DIAGNOSTIC: {message}")

    def _get_cached_geometry(self):
        """Zwraca cache'owane obliczenia geometrii lub oblicza nowe."""
        with self._geometry_cache_lock:
            container_width = (
                self.scroll_area.width() - self.scroll_area.verticalScrollBar().width()
            )

            # Sprawdź czy cache jest aktualny
            if (
                self._geometry_cache["container_width"] == container_width
                and self._geometry_cache["last_thumbnail_size"]
                == self.current_thumbnail_size
            ):
                return self._geometry_cache

            # Oblicz nowe wartości
            tile_width_spacing = (
                self.current_thumbnail_size + self.tiles_layout.spacing() + 10
            )
            tile_height_spacing = (
                self.current_thumbnail_size + self.tiles_layout.spacing() + 40
            )
            cols = max(1, math.ceil(container_width / tile_width_spacing))

            # Zaktualizuj cache
            self._geometry_cache.update(
                {
                    "container_width": container_width,
                    "cols": cols,
                    "tile_width_spacing": tile_width_spacing,
                    "tile_height_spacing": tile_height_spacing,
                    "last_thumbnail_size": self.current_thumbnail_size,
                }
            )

            return self._geometry_cache

    def _on_scroll(self, value):
        """Wywołuje opóźnioną aktualizację widocznych kafelków."""
        self._virtualization_timer.start(self.VIRTUALIZATION_UPDATE_DELAY)

    def clear_gallery(self):
        """
        Czyści galerię kafelków - usuwa wszystkie widgety z pamięci.
        """
        self.tiles_container.setUpdatesEnabled(False)
        try:
            # Usuń wszystkie widgety z layoutu
            while self.tiles_layout.count():
                item = self.tiles_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    # Usuń widget z layoutu, ale nie z pamięci, jeśli
                    # jest w `gallery_tile_widgets` lub
                    # `special_folder_widgets`
                    widget.setVisible(False)
                    self.tiles_layout.removeWidget(widget)  # Jawne usunięcie

            # Thread-safe czyszczenie słowników
            with self._widgets_lock:
                # Usuń widgety par plików ze słownika i pamięci
                for archive_path in list(
                    self.gallery_tile_widgets.keys()
                ):  # Iteruj po kopii kluczy
                    tile = self.gallery_tile_widgets.pop(archive_path)
                    tile.setParent(None)
                    tile.deleteLater()
                self.gallery_tile_widgets.clear()

                # Usuń widgety folderów ze słownika i pamięci
                for folder_path in list(
                    self.special_folder_widgets.keys()
                ):  # Iteruj po kopii kluczy
                    folder_widget = self.special_folder_widgets.pop(folder_path)
                    folder_widget.setParent(None)
                    folder_widget.deleteLater()
                self.special_folder_widgets.clear()
        finally:
            self.tiles_container.setUpdatesEnabled(True)
            self.tiles_container.update()

    def create_tile_widget_for_pair(self, file_pair: FilePair, parent_widget):
        """
        Tworzy pojedynczy kafelek dla pary plików - thread safe.
        """
        try:
            # Przekaż _current_size_tuple jako krotkę (width, height)
            tile = FileTileWidget(
                file_pair,
                self._current_size_tuple,
                parent_widget,
                skip_resource_registration=True,
            )
            # Ukryj na starcie, update_gallery_view zdecyduje o widoczności
            tile.setVisible(False)

            # Thread-safe dodanie do słownika
            with self._widgets_lock:
                self.gallery_tile_widgets[file_pair.get_archive_path()] = tile

            return tile
        except Exception as e:
            logging.error(
                f"Błąd tworzenia kafelka dla {file_pair.get_base_name()}: {e}"
            )
            return None

    def update_gallery_view(self):
        """
        Aktualizuje widok galerii z WIRTUALIZACJĄ.
        NAPRAWKA: Przywrócona wirtualizacja z poprawionym obliczaniem kolumn.
        """
        # DEBUG: Sprawdź czy funkcja jest wywoływana
        total_items = len(self.special_folders_list) + len(self.file_pairs_list)
        logging.info(
            f"GalleryManager.update_gallery_view() called - items: {total_items}"
        )

        # NAPRAWKA KRYTYCZNA: Zmniejszono próg z 1500 na 200 - duże foldery MUSZĄ używać asynchronicznego DataProcessingWorker!
        if total_items <= 200:  # Tylko małe foldery używają synchronicznego force_create_all_tiles
            logging.info(f"Using force_create_all_tiles for {total_items} items")
            self.force_create_all_tiles()
            # NAPRAWKA: Wyłącz wirtualizację po force_create_all_tiles
            self._virtualization_enabled = False
            logging.info("Virtualization disabled after force_create_all_tiles")
            return
        
        # NAPRAWKA KRYTYCZNA: Dla folderów >200 kafelków używaj wirtualizacji - DataProcessingWorker już działa!
        logging.info(f"Large folder ({total_items} items) - DataProcessingWorker already running, proceeding with virtualization layout")
        
        # NAPRAWKA: NIE uruchamiaj dodatkowego DataProcessingWorker - jeden już działa z scan_results_handler!

        # Dla dużych folderów używaj wirtualizacji
        logging.info(f"Using virtualization for {total_items} items")
        
        # NAPRAWKA: Sprawdź stan danych przed wirtualizacją
        logging.info(f"🔍 DEBUG DATA: special_folders_list={len(self.special_folders_list)}, file_pairs_list={len(self.file_pairs_list)}")
        if len(self.file_pairs_list) > 0:
            logging.info(f"🔍 First file_pair: {self.file_pairs_list[0].get_archive_path()}")
        
        self.tiles_container.setUpdatesEnabled(False)
        try:
            # 1. Wyczyść stare widgety z layoutu, ale ZACHOWAJ je w pamięci
            while self.tiles_layout.count() > 0:
                item = self.tiles_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

            # 2. Oblicz wymiary wirtualnego layoutu
            container_width = (
                self.scroll_area.width() - self.scroll_area.verticalScrollBar().width()
            )
            tile_width_with_spacing = (
                self.current_thumbnail_size + self.tiles_layout.spacing() + 10
            )
            cols = max(1, math.ceil(container_width / tile_width_with_spacing))

            if total_items == 0:
                self.tiles_container.setMinimumHeight(0)
                return

            total_rows = math.ceil(total_items / cols)
            tile_height_with_spacing = (
                self.current_thumbnail_size + self.tiles_layout.spacing() + 40
            )
            total_height = total_rows * tile_height_with_spacing

            # 3. Ustaw rozmiar kontenera, aby scrollbary działały poprawnie
            self.tiles_container.setMinimumHeight(total_height)
            self.tiles_container.adjustSize()
            self.tiles_container.updateGeometry()
            self.scroll_area.ensureVisible(0, 0)
            self.scroll_area.viewport().updateGeometry()

            # NAPRAWKA KRYTYCZNA: Włącz wirtualizację!
            self._virtualization_enabled = True
            logging.info("Virtualization enabled for large folder")

            # 4. NAPRAWKA: Wymuś pierwsze wywołanie _update_visible_tiles()
            logging.info("Forcing first _update_visible_tiles() call")
            try:
                self._update_visible_tiles()
                logging.info("✅ _update_visible_tiles() completed successfully")
            except Exception as e:
                logging.error(f"🚨 CRITICAL ERROR in _update_visible_tiles(): {e}")
                import traceback
                logging.error(f"🚨 TRACEBACK: {traceback.format_exc()}")

        finally:
            self.tiles_container.setUpdatesEnabled(True)

    def _update_visible_tiles(self):
        """Tworzy/usuwa kafelki w zależności od tego, czy są widoczne."""

        # NAPRAWKA: Wyłącz wirtualizację jeśli jest wyłączona
        if not self._virtualization_enabled:
            logging.info("Virtualization disabled - skipping _update_visible_tiles")
            return

        # NAPRAWKA: Agresywne debugging
        logging.info(f"🚀 _update_visible_tiles() START - virtualization_enabled={self._virtualization_enabled}")
        
        # Sprawdź czy mamy dane
        total_items = len(self.special_folders_list) + len(self.file_pairs_list)
        if total_items == 0:
            logging.warning("🚨 No items to display in _update_visible_tiles")
            return
            
        logging.info(f"🔍 Processing {total_items} items (special_folders={len(self.special_folders_list)}, file_pairs={len(self.file_pairs_list)})")

        # Użyj cache'owanych obliczeń geometrii
        geometry = self._get_cached_geometry()
        cols = geometry["cols"]
        tile_height_spacing = geometry["tile_height_spacing"]

        logging.info(f"🏗️ Layout: cols={cols}, tile_height_spacing={tile_height_spacing}")

        # Określ widoczny obszar
        viewport_height = self.scroll_area.viewport().height()
        scroll_y = self.scroll_area.verticalScrollBar().value()
        scroll_max = self.scroll_area.verticalScrollBar().maximum()
        container_height = self.tiles_container.minimumHeight()

        # DEBUG: Sprawdź wymiary
        logging.info(
            f"🔧 DEBUG: viewport_height={viewport_height}, scroll_y={scroll_y}, "
            f"scroll_max={scroll_max}, container_height={container_height}"
        )

        # Dodaj bufor (np. jeden ekran w górę i w dół)
        buffer = viewport_height
        visible_start_y = max(0, scroll_y - buffer)
        visible_end_y = scroll_y + viewport_height + buffer

        first_visible_row = max(0, math.floor(visible_start_y / tile_height_spacing))
        last_visible_row = math.ceil(visible_end_y / tile_height_spacing)

        # NAPRAWKA: Poprawne obliczanie indeksów widocznych itemów
        first_visible_item_idx = first_visible_row * cols
        last_visible_item_idx = min(
            (last_visible_row + 1) * cols,
            len(self.special_folders_list) + len(self.file_pairs_list),
        )

        all_items = self.special_folders_list + self.file_pairs_list
        visible_items_set = set()

        # Debug logging
        logging.info(
            f"🎯 Virtualization: items={len(all_items)}, visible_range=[{first_visible_item_idx}-{last_visible_item_idx}], cols={cols}, scroll_y={scroll_y}"
        )

        # NAPRAWKA: Sprawdź czy zakres jest poprawny
        if first_visible_item_idx >= len(all_items):
            logging.error(f"🚨 ERROR: first_visible_item_idx ({first_visible_item_idx}) >= total_items ({len(all_items)})")
            return
            
        if last_visible_item_idx <= first_visible_item_idx:
            logging.error(f"🚨 ERROR: Invalid range: last_visible_item_idx ({last_visible_item_idx}) <= first_visible_item_idx ({first_visible_item_idx})")
            return

        # Dodaj widoczne kafelki
        created_in_this_update = 0
        for i in range(first_visible_item_idx, last_visible_item_idx):
            if i >= len(all_items):
                break
                
            item = all_items[i]
            logging.info(f"🔨 Creating tile {i+1}/{len(all_items)}: {type(item).__name__}")

            if isinstance(item, SpecialFolder):
                path = item.get_folder_path()
                widget = self.special_folder_widgets.get(path)
                if not widget:
                    logging.info(f"📁 Creating new special folder widget for {path}")
                    widget = self.create_folder_widget(item)
                    if not widget:
                        logging.error(f"🚨 Failed to create special folder widget for {path}")
                        continue
                visible_items_set.add(path)
            else:  # FilePair
                path = item.get_archive_path()
                widget = self.gallery_tile_widgets.get(path)
                if not widget:
                    logging.info(f"🖼️ Creating new tile widget for {path}")
                    widget = self.create_tile_widget_for_pair(
                        item, self.tiles_container
                    )
                    if not widget:
                        logging.error(f"🚨 Failed to create tile widget for {path}")
                        continue
                visible_items_set.add(path)

            row = i // cols
            col = i % cols

            logging.info(f"🎯 Placing widget at position ({row}, {col})")

            # NAPRAWKA: Dodaj numer do kafelka dla diagnostyki
            if hasattr(widget, "set_tile_number"):
                widget.set_tile_number(i + 1, len(all_items))
            elif hasattr(widget, "setToolTip"):
                current_tooltip = widget.toolTip() or ""
                widget.setToolTip(f"[{i+1}/{len(all_items)}] {current_tooltip}")

            # Sprawdź czy pozycja jest pusta lub zawiera inny widget
            current_item = self.tiles_layout.itemAtPosition(row, col)
            if current_item is None or current_item.widget() != widget:
                # Jeśli pozycja zajęta przez inny widget, usuń go najpierw
                if current_item is not None:
                    old_widget = current_item.widget()
                    if old_widget != widget:
                        self.tiles_layout.removeWidget(old_widget)
                        old_widget.setVisible(False)
                self.tiles_layout.addWidget(widget, row, col)
                created_in_this_update += 1
                logging.info(f"✅ Widget added to layout at ({row}, {col})")

            if not widget.isVisible():
                widget.setVisible(True)
                logging.info(f"👁️ Widget made visible")

        logging.info(f"🎉 Created {created_in_this_update} widgets in this update")

    def apply_filters_and_update_view(
        self, all_file_pairs: List[FilePair], filter_criteria: dict
    ):
        """
        Aplikuje filtry i aktualizuje widok galerii.

        Args:
            all_file_pairs: Lista wszystkich par plików do przefiltrowania
            filter_criteria: Kryteria filtrowania
        """
        try:
            from src.logic.filter_logic import filter_file_pairs

            # Przefiltruj pliki
            filtered_pairs = filter_file_pairs(all_file_pairs, filter_criteria)

            # NAPRAWKA KRYTYCZNA: Ustaw file_pairs_list PRZED wywołaniem update_gallery_view()!
            self.file_pairs_list = filtered_pairs
            logging.info(f"🔧 NAPRAWKA: Ustawiono file_pairs_list na {len(filtered_pairs)} par przed update_gallery_view()")

            # Aktualizuj widok
            self.update_gallery_view()

            logging.info(
                f"Zastosowano filtry: {len(all_file_pairs)} → {len(filtered_pairs)} par"
            )

        except Exception as e:
            logging.error(f"Błąd podczas aplikowania filtrów: {e}")
            # Fallback: pokaż wszystkie pliki
            self.file_pairs_list = all_file_pairs
            logging.info(f"🔧 FALLBACK: Ustawiono file_pairs_list na {len(all_file_pairs)} par (wszystkie)")
            self.update_gallery_view()

    def update_thumbnail_size(self, new_size):
        """
        Aktualizuje rozmiar miniatur i przerenderowuje galerię.
        new_size może być int lub tuple (width, height).

        Zoptymalizowana wersja - aktualizuje tylko widoczne kafelki.
        """
        # Obsługa różnych formatów new_size
        if isinstance(new_size, int):
            self.current_thumbnail_size = new_size
            self._current_size_tuple = (new_size, new_size)
        else:
            # current_thumbnail_size w GalleryManager powinien być int (szerokość)
            # Zakładamy, że new_size[0] to nowa szerokość
            self.current_thumbnail_size = new_size[0]
            self._current_size_tuple = new_size

        logging.debug(
            f"GalleryManager: Ustawianie nowego rozmiaru: {self._current_size_tuple}"
        )

        # Zaktualizuj rozmiar tylko dla widocznych kafelków + cache nowego rozmiaru dla pozostałych
        with self._widgets_lock:
            # Natychmiast zaktualizuj widoczne kafelki
            for tile in self.gallery_tile_widgets.values():
                if tile.isVisible():
                    tile.set_thumbnail_size(self._current_size_tuple)

            for folder_widget in self.special_folder_widgets.values():
                if folder_widget.isVisible():
                    folder_widget.set_thumbnail_size(self._current_size_tuple)

        # Zaznacz, że niewidoczne kafelki potrzebują aktualizacji
        self._pending_size_update = True

        # Invalidate geometry cache
        with self._geometry_cache_lock:
            self._geometry_cache["last_thumbnail_size"] = 0

        # Przerenderuj galerię z nowymi rozmiarami
        self.update_gallery_view()

        logging.debug(
            f"GalleryManager: Zaktualizowano rozmiar {len(self.gallery_tile_widgets)} kafli"
        )

    def get_all_tile_widgets(self) -> List[FileTileWidget]:
        """
        Zwraca listę wszystkich widgetów kafelków w galerii.
        Używane do operacji zbiorczych (zaznaczanie wszystkich, operacje na zaznaczonych).

        Returns:
            List[FileTileWidget]: Lista wszystkich widgetów kafelków
        """
        return list(self.gallery_tile_widgets.values())

    def get_visible_tile_widgets(self) -> List[FileTileWidget]:
        """
        Zwraca listę tylko widocznych widgetów kafelków.
        Optymalizacja dla operacji na widocznych kafelkach.

        Returns:
            List[FileTileWidget]: Lista widocznych widgetów kafelków
        """
        return [tile for tile in self.gallery_tile_widgets.values() if tile.isVisible()]

    def get_tile_for_path(self, archive_path: str) -> FileTileWidget:
        """
        Pobiera kafelek dla określonej ścieżki archiwum.
        Zwraca None, jeśli kafelek nie istnieje.

        Args:
            archive_path: Ścieżka do pliku archiwum

        Returns:
            FileTileWidget: Znaleziony widget kafelka lub None
        """
        return self.gallery_tile_widgets.get(archive_path)

    def create_folder_widget(self, special_folder: SpecialFolder):
        """
        Tworzy widget dla folderu specjalnego.
        """
        try:
            folder_name = special_folder.get_folder_name()
            folder_path = special_folder.get_folder_path()
            is_virtual = special_folder.is_virtual

            self._log_diagnostic(
                f"Próba utworzenia widgetu dla {folder_path} (wirtualny: {is_virtual})"
            )

            # Sprawdź, czy folder fizycznie istnieje, TYLKO jeśli nie jest wirtualny
            if not is_virtual and not os.path.exists(folder_path):
                self._log_diagnostic(
                    f"Fizyczny folder specjalny nie istnieje i nie zostanie utworzony: {folder_path}"
                )
                return None

            folder_widget = SpecialFolderTileWidget(
                folder_name, folder_path, self.tiles_container
            )
            folder_widget.set_thumbnail_size(self.current_thumbnail_size)

            # Podłącz sygnał kliknięcia
            folder_widget.folder_clicked.connect(self._on_folder_clicked)

            # Thread-safe dodanie do słownika
            with self._widgets_lock:
                self.special_folder_widgets[folder_path] = folder_widget

            logging.debug(f"Utworzono widget folderu: {folder_name}")
            return folder_widget
        except Exception as e:
            logging.error(f"Błąd tworzenia widgetu folderu: {e}", exc_info=True)
            return None

    def _on_folder_clicked(self, folder_path: str):
        """
        Obsługuje kliknięcie na kafelek folderu specjalnego.
        Otwiera folder w eksploratorze plików systemu.

        Args:
            folder_path (str): Ścieżka do folderu do otwarcia.
        """
        if not folder_path or not os.path.exists(folder_path):
            logging.warning(f"Próba otwarcia nieistniejącego folderu: {folder_path}")
            return

        logging.info(f"Otwieranie folderu w eksploratorze: {folder_path}")
        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
        except Exception as e:
            logging.error(f"Nie udało się otworzyć folderu {folder_path}: {e}")

    def prepare_special_folders(self, special_folders: List[SpecialFolder]):
        """
        Przygotowuje widgety dla folderów specjalnych przed aktualizacją widoku.
        """
        self._log_diagnostic(f"Otrzymano {len(special_folders)} folderów")

        self.special_folders_list = special_folders

        # Wyczyść poprzednie widgety folderów
        with self._widgets_lock:
            for folder_path in list(self.special_folder_widgets.keys()):
                folder_widget = self.special_folder_widgets.pop(folder_path)
                self._log_diagnostic(f"Usuwam stary widget folderu: {folder_path}")
                folder_widget.setParent(None)
                folder_widget.deleteLater()
            self.special_folder_widgets.clear()

        # Utwórz nowe widgety dla folderów
        for special_folder in special_folders:
            widget = self.create_folder_widget(special_folder)
            self._log_diagnostic(
                f"Utworzono nowy widget: {special_folder.get_folder_path()} -> {widget is not None}"
            )

        logging.info(
            f"Przygotowano {len(self.special_folder_widgets)} widgetów folderów specjalnych."
        )

    def set_special_folders(self, special_folders: List[SpecialFolder]):
        """
        Ustawia listę specjalnych folderów i OD RAZU odświeża widok.
        """
        # Krok 1: Przygotuj widgety w tle
        self.prepare_special_folders(special_folders)

        # Krok 2: Wymuś aktualizację widoku, aby pokazać nowe foldery
        self.update_gallery_view()

        logging.info(
            f"Ustawiono i wyświetlono {len(special_folders)} specjalnych folderów"
        )

        # Diagnostyczne logowanie zawartości słownika widgetów folderów
        logging.debug(
            f"DEBUG: Po ustawieniu folderów, mamy {len(self.special_folder_widgets)} widgetów folderów"
        )
        for path, widget in self.special_folder_widgets.items():
            logging.debug(
                f"DEBUG: Widget folderu: {path} (widoczny: {widget.isVisible()})"
            )

    def _ensure_widget_created(self, item, item_index):
        """Zapewnia że widget jest utworzony i ma poprawny rozmiar."""
        if isinstance(item, SpecialFolder):
            path = item.get_folder_path()
            widget = self.special_folder_widgets.get(path)
            if not widget:
                widget = self.create_folder_widget(item)
                if not widget:
                    return None

            # Sprawdź czy widget ma aktualny rozmiar
            if hasattr(self, "_pending_size_update") and self._pending_size_update:
                widget.set_thumbnail_size(self._current_size_tuple)

        else:  # FilePair
            path = item.get_archive_path()
            widget = self.gallery_tile_widgets.get(path)
            if not widget:
                widget = self.create_tile_widget_for_pair(item, self.tiles_container)
                if not widget:
                    return None

            # Sprawdź czy widget ma aktualny rozmiar
            if hasattr(self, "_pending_size_update") and self._pending_size_update:
                widget.set_thumbnail_size(self._current_size_tuple)

        return widget

    def _on_tile_double_clicked(self, file_pair):
        """Obsługuje podwójne kliknięcie na kafelek pary plików."""
        # ... existing code ...

    def force_create_all_tiles(self):
        """
        Wymusza tworzenie wszystkich kafelków bez wirtualizacji.
        Używane gdy wirtualizacja nie działa poprawnie.
        """
        import traceback

        from PyQt6.QtWidgets import QApplication

        # DEBUG: Sprawdź czy funkcja jest wywoływana
        logging.info(f"GalleryManager.force_create_all_tiles() called")

        # NAPRAWKA: Wyłącz limit TileResourceManager dla force_create_all_tiles
        original_max_tiles = get_resource_manager().limits.max_tiles
        get_resource_manager().limits.max_tiles = 10000  # Tymczasowo zwiększ limit

        # NAPRAWKA: Wyczyść stare kafelki przed tworzeniem nowych
        self.clear_gallery()

        self.tiles_container.setUpdatesEnabled(False)
        try:
            # Wyczyść layout
            while self.tiles_layout.count() > 0:
                item = self.tiles_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)

            all_items = self.special_folders_list + self.file_pairs_list
            geometry = self._get_cached_geometry()
            cols = geometry["cols"]

            if self.DIAGNOSTIC_LOGGING:
                self._log_diagnostic(
                    f"Force creating all tiles: {len(all_items)} items, {cols} cols"
                )

            # Twórz kafelki w batchach - NAPRAWKA: większe batche dla szybkości
            batch_size = 100  # Zwiększono z 20 na 100 dla szybkości SBSAR
            total_batches = (len(all_items) + batch_size - 1) // batch_size

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(all_items))

                logging.info(
                    f"Processing batch {batch_num + 1}: items {start_idx}-{end_idx - 1}"
                )

                for i in range(start_idx, end_idx):
                    if i < len(self.special_folders_list):
                        # Twórz kafelki folderów specjalnych
                        folder = self.special_folders_list[i]
                        widget = SpecialFolderTileWidget(folder)
                        # NAPRAWKA: Dodaj numerację kafelków
                        tooltip = f"[{i + 1}/{len(self.special_folders_list)}] {folder.folder_name}"
                        widget.setToolTip(tooltip)
                        widget.setObjectName(f"SpecialFolderTile_{i + 1}")
                        self.special_folder_widgets[folder.path] = widget
                        self.tiles_layout.addWidget(widget, i // cols, i % cols)
                    else:
                        # Twórz kafelki par plików
                        file_pair_idx = i - len(self.special_folders_list)
                        file_pair = self.file_pairs_list[file_pair_idx]
                        # OPTYMALIZACJA WYDAJNOŚCI: Używaj prostego widgetu-placeholder zamiast pełnego FileTileWidget
                        widget = self._create_fast_placeholder_widget(file_pair)
                        
                        # NAPRAWKA: Podłącz sygnały do kafelka (jak w tile_manager.py)
                        widget.archive_open_requested.connect(self.main_window.open_archive)
                        widget.preview_image_requested.connect(self.main_window._show_preview_dialog)
                        widget.tile_selected.connect(self.main_window._handle_tile_selection_changed)
                        widget.stars_changed.connect(self.main_window._handle_stars_changed)
                        widget.color_tag_changed.connect(self.main_window._handle_color_tag_changed)
                        widget.tile_context_menu_requested.connect(self.main_window._show_file_context_menu)
                        
                        if hasattr(widget, "set_tile_number"):
                            widget.set_tile_number(i + 1, len(self.file_pairs_list))
                        widget.setObjectName(f"FileTile_{i + 1}")
                        self.gallery_tile_widgets[file_pair.archive_path] = widget
                        self.tiles_layout.addWidget(widget, i // cols, i % cols)

                logging.info(f"Batch {batch_num + 1} complete: {end_idx} tiles created so far")

                # NAPRAWKA: Rzadsze processEvents - tylko co 5 batchów zamiast każdy
                if (batch_num + 1) % 5 == 0:  # Co 5 batchów zamiast każdy
                    try:
                        from PyQt6.QtWidgets import QApplication
                        QApplication.processEvents()
                    except Exception:
                        pass

            # Ustaw wysokość kontenera
            total_rows = math.ceil(len(all_items) / cols)
            tile_height_spacing = geometry["tile_height_spacing"]
            total_height = total_rows * tile_height_spacing
            self.tiles_container.setMinimumHeight(total_height)
            self.tiles_container.adjustSize()
            self.tiles_container.updateGeometry()
            self.scroll_area.updateGeometry()
            if hasattr(self.scroll_area, "verticalScrollBar"):
                self.scroll_area.verticalScrollBar().setValue(0)

            # NAPRAWKA: Wymuś pełny relayout i popraw polityki rozmiaru
            self.tiles_layout.invalidate()
            self.tiles_container.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
            )
            self.tiles_container.adjustSize()
            self.tiles_container.updateGeometry()
            if hasattr(self.scroll_area, "widget"):
                self.scroll_area.widget().adjustSize()
            self.scroll_area.updateGeometry()

            if self.DIAGNOSTIC_LOGGING:
                self._log_diagnostic(
                    f"Force create complete: {len(self.gallery_tile_widgets)} tiles created, "
                    f"cols={cols}, rows={total_rows}"
                )

        except Exception as e:
            logging.error(f"Error in force_create_all_tiles: {e}")
            logging.error(traceback.format_exc())
        finally:
            self.tiles_container.setUpdatesEnabled(True)
            self.tiles_container.update()

            # NAPRAWKA: Przywróć limit TileResourceManager
            get_resource_manager().limits.max_tiles = original_max_tiles

    def _create_fast_placeholder_widget(self, file_pair: FilePair):
        """
        OPTYMALIZACJA: Tworzy szybki placeholder widget zamiast pełnego FileTileWidget.
        Używane w force_create_all_tiles() dla wydajności.
        """
        from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QPixmap
        
        # Prosty widget z podstawowym UI
        widget = QWidget(self.tiles_container)
        widget.setFixedSize(*self._current_size_tuple)
        widget.setObjectName("FileTileWidget")  # Dla CSS
        
        # Prosty layout
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Placeholder miniaturka
        thumbnail_label = QLabel(widget)
        thumbnail_label.setText("Ładowanie...")
        thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumbnail_label.setMinimumSize(200, 200)
        thumbnail_label.setStyleSheet("background-color: #2D2D30; border: 1px solid #3F3F46; border-radius: 6px;")
        
        # Nazwa pliku
        filename_label = QLabel(f"[{file_pair.get_base_name()}]", widget)
        filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        filename_label.setWordWrap(True)
        filename_label.setMaximumHeight(35)
        filename_label.setStyleSheet("color: #CCCCCC; font-size: 11px;")
        
        layout.addWidget(thumbnail_label)
        layout.addWidget(filename_label)
        
        # Zapisz referencję do FilePair
        widget._file_pair = file_pair
        widget._is_placeholder = True
        
        return widget
